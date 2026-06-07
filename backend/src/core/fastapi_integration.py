"""
FastAPI依赖注入集成 - 将依赖注入容器与FastAPI框架集成

本模块提供：
1. FastAPI依赖提供者
2. 请求作用域管理
3. 依赖注入装饰器
4. 中间件集成
"""

import asyncio
import logging
from typing import Type, TypeVar, Callable, Any, Optional
from functools import wraps
from contextlib import asynccontextmanager

from fastapi import Depends, Request, HTTPException
from fastapi.dependencies.utils import get_dependant
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .container import ServiceContainer, get_container, ServiceResolutionError
from .service_registry import get_service_registry

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DIMiddleware(BaseHTTPMiddleware):
    """
    依赖注入中间件
    
    为每个HTTP请求创建服务作用域，确保作用域服务在请求期间保持单例。
    """
    
    def __init__(self, app, container: Optional[ServiceContainer] = None):
        super().__init__(app)
        self.container = container or get_container()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理HTTP请求，创建服务作用域"""
        # 为请求创建唯一的作用域ID
        scope_id = f"request_{id(request)}"
        
        async with self.container.create_scope(scope_id):
            # 将容器添加到请求状态中，供依赖注入使用
            request.state.di_container = self.container
            request.state.di_scope_id = scope_id
            
            try:
                response = await call_next(request)
                return response
            except Exception as e:
                logger.error(f"Error in request processing: {str(e)}")
                raise


def get_di_container(request: Request) -> ServiceContainer:
    """
    获取当前请求的依赖注入容器
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        ServiceContainer: 依赖注入容器
    """
    if hasattr(request.state, 'di_container'):
        return request.state.di_container
    else:
        # 如果没有中间件设置容器，使用全局容器
        return get_container()


def inject_service(service_type: Type[T]) -> Callable[[], T]:
    """
    创建FastAPI依赖注入函数
    
    Args:
        service_type: 要注入的服务类型
        
    Returns:
        Callable: FastAPI依赖函数
    """
    async def dependency(request: Request) -> T:
        try:
            container = get_di_container(request)
            return await container.get_service_async(service_type)
        except ServiceResolutionError as e:
            logger.error(f"Failed to resolve service {service_type.__name__}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Service resolution error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error resolving service {service_type.__name__}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error"
            )
    
    return dependency


def Inject(service_type: Type[T]) -> T:
    """
    FastAPI依赖注入装饰器
    
    用法:
    @app.get("/api/test")
    async def test_endpoint(ai_service: AIAssistantService = Inject(AIAssistantService)):
        return await ai_service.process_query(...)
    
    Args:
        service_type: 要注入的服务类型
        
    Returns:
        T: 依赖注入的服务实例
    """
    return Depends(inject_service(service_type))


class ServiceProvider:
    """
    服务提供者类
    
    提供便捷的服务获取方法，可以在路由处理函数中使用。
    """
    
    def __init__(self, container: ServiceContainer):
        self.container = container
    
    async def get_service(self, service_type: Type[T]) -> T:
        """获取服务实例"""
        return await self.container.get_service_async(service_type)
    
    def get_service_sync(self, service_type: Type[T]) -> T:
        """同步获取服务实例"""
        return self.container.get_service(service_type)


def get_service_provider(request: Request) -> ServiceProvider:
    """
    获取服务提供者
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        ServiceProvider: 服务提供者实例
    """
    container = get_di_container(request)
    return ServiceProvider(container)


# FastAPI依赖函数
ServiceProviderDep = Depends(get_service_provider)


def with_services(*service_types: Type) -> Callable:
    """
    路由装饰器，自动注入多个服务
    
    用法:
    @app.get("/api/test")
    @with_services(AIAssistantService, AIRouterService)
    async def test_endpoint(services: dict):
        ai_service = services[AIAssistantService]
        router_service = services[AIRouterService]
        # 使用服务...
    
    Args:
        *service_types: 要注入的服务类型列表
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 查找请求对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # 从kwargs中查找
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                raise RuntimeError("Request object not found in function arguments")
            
            # 解析服务
            container = get_di_container(request)
            services = {}
            
            for service_type in service_types:
                try:
                    service_instance = await container.get_service_async(service_type)
                    services[service_type] = service_instance
                except Exception as e:
                    logger.error(f"Failed to resolve service {service_type.__name__}: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Service resolution error: {str(e)}"
                    )
            
            # 将services添加到kwargs中
            kwargs['services'] = services
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class DIHealthCheck:
    """依赖注入健康检查"""
    
    def __init__(self, container: Optional[ServiceContainer] = None):
        self.container = container or get_container()
    
    async def check_services_health(self) -> dict:
        """检查所有服务的健康状态"""
        registry = get_service_registry()
        health_status = await registry.health_check_services()
        
        return {
            'status': 'healthy' if all(health_status.values()) else 'unhealthy',
            'services': health_status,
            'total_services': len(health_status),
            'healthy_services': sum(1 for status in health_status.values() if status),
            'unhealthy_services': sum(1 for status in health_status.values() if not status)
        }
    
    async def get_container_info(self) -> dict:
        """获取容器信息"""
        registered_services = self.container.get_registered_services()
        
        return {
            'registered_services_count': len(registered_services),
            'registered_services': [service.__name__ for service in registered_services],
            'container_type': type(self.container).__name__
        }


def create_health_check_endpoint():
    """创建健康检查端点"""
    health_checker = DIHealthCheck()
    
    async def health_check():
        """健康检查端点"""
        try:
            services_health = await health_checker.check_services_health()
            container_info = await health_checker.get_container_info()
            
            return {
                'status': 'ok',
                'dependency_injection': {
                    'status': 'healthy',
                    'container': container_info,
                    'services': services_health
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'status': 'error',
                'dependency_injection': {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            }
    
    return health_check


def setup_dependency_injection(app, container: Optional[ServiceContainer] = None):
    """
    设置FastAPI应用的依赖注入
    
    Args:
        app: FastAPI应用实例
        container: 依赖注入容器（可选）
    """
    container = container or get_container()
    
    # 添加依赖注入中间件
    app.add_middleware(DIMiddleware, container=container)
    
    # 添加健康检查端点
    health_check_func = create_health_check_endpoint()
    app.get("/health/di")(health_check_func)
    
    logger.info("Dependency injection setup completed for FastAPI application")


# 便捷的服务注入函数
async def resolve_service(service_type: Type[T], request: Request) -> T:
    """
    在路由处理函数中直接解析服务
    
    Args:
        service_type: 服务类型
        request: 请求对象
        
    Returns:
        T: 服务实例
    """
    container = get_di_container(request)
    return await container.get_service_async(service_type)


def create_service_dependency(service_type: Type[T]) -> Callable:
    """
    创建服务依赖函数（用于复杂的依赖场景）
    
    Args:
        service_type: 服务类型
        
    Returns:
        Callable: 依赖函数
    """
    async def dependency(
        request: Request,
        service_provider: ServiceProvider = ServiceProviderDep
    ) -> T:
        return await service_provider.get_service(service_type)
    
    return dependency


# 预定义的常用服务依赖
def get_ai_assistant_service(request: Request) -> Callable:
    """获取AI助手服务依赖"""
    from ..services.ai_assistant_service import AIAssistantService
    return inject_service(AIAssistantService)


async def get_ai_router_service(request: Request) -> 'AIRouterService':
    """获取AI路由服务依赖"""
    from ..services.ai_router_service import AIRouterService
    container = get_di_container(request)
    return await container.get_service_async(AIRouterService)


def get_conversation_service(request: Request) -> Callable:
    """获取对话服务依赖"""
    from ..services.conversation_service import ConversationService
    return inject_service(ConversationService)


# 常用依赖的快捷方式
AIAssistantServiceDep = Depends(get_ai_assistant_service)
AIRouterServiceDep = Depends(get_ai_router_service)
ConversationServiceDep = Depends(get_conversation_service)