"""
依赖注入容器 - 服务依赖注入框架核心实现

本模块实现了一个完整的依赖注入容器，支持：
1. 服务注册和解析
2. 单例和瞬态生命周期管理
3. 构造函数依赖注入
4. 接口和实现的绑定
5. 循环依赖检测
6. 服务装饰器和中间件
"""

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Union, 
    Callable, Protocol, runtime_checkable, get_type_hints
)
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceLifetime(Enum):
    """服务生命周期枚举"""
    SINGLETON = "singleton"      # 单例：整个应用生命周期内只创建一次
    SCOPED = "scoped"           # 作用域：在特定作用域内单例（如请求作用域）
    TRANSIENT = "transient"     # 瞬态：每次请求都创建新实例


@runtime_checkable
class IServiceProvider(Protocol):
    """服务提供者接口"""
    
    def get_service(self, service_type: Type[T]) -> T:
        """获取服务实例"""
        ...
    
    async def get_service_async(self, service_type: Type[T]) -> T:
        """异步获取服务实例"""
        ...


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    service_type: Type                          # 服务类型（接口或抽象类）
    implementation_type: Optional[Type] = None  # 实现类型
    factory: Optional[Callable] = None          # 工厂函数
    instance: Optional[Any] = None              # 预创建的实例
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    dependencies: List[Type] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """后初始化处理"""
        if not any([self.implementation_type, self.factory, self.instance]):
            # 如果没有指定实现，尝试使用服务类型本身
            if not inspect.isabstract(self.service_type):
                self.implementation_type = self.service_type
            else:
                raise ValueError(f"Abstract service {self.service_type} requires implementation")


class ServiceResolutionError(Exception):
    """服务解析异常"""
    pass


class CircularDependencyError(ServiceResolutionError):
    """循环依赖异常"""
    pass


class ServiceContainer:
    """
    依赖注入容器
    
    提供完整的依赖注入功能，包括服务注册、解析、生命周期管理等。
    支持构造函数注入、接口绑定、循环依赖检测等高级特性。
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._resolution_stack: List[Type] = []
        self._middleware: List[Callable] = []
        self._interceptors: Dict[Type, List[Callable]] = {}
        self._current_scope: Optional[str] = None
        
        # 注册容器自身
        self.register_instance(ServiceContainer, self)
        self.register_instance(IServiceProvider, self)
    
    def register_transient(self, service_type: Type[T], 
                          implementation_type: Optional[Type[T]] = None) -> 'ServiceContainer':
        """
        注册瞬态服务
        
        Args:
            service_type: 服务类型（接口）
            implementation_type: 实现类型
            
        Returns:
            ServiceContainer: 容器实例，支持链式调用
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.TRANSIENT
        )
        self._services[service_type] = descriptor
        logger.debug(f"Registered transient service: {service_type.__name__}")
        return self
    
    def register_singleton(self, service_type: Type[T], 
                          implementation_type: Optional[Type[T]] = None) -> 'ServiceContainer':
        """
        注册单例服务
        
        Args:
            service_type: 服务类型（接口）
            implementation_type: 实现类型
            
        Returns:
            ServiceContainer: 容器实例，支持链式调用
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._services[service_type] = descriptor
        logger.debug(f"Registered singleton service: {service_type.__name__}")
        return self
    
    def register_scoped(self, service_type: Type[T], 
                       implementation_type: Optional[Type[T]] = None) -> 'ServiceContainer':
        """
        注册作用域服务
        
        Args:
            service_type: 服务类型（接口）
            implementation_type: 实现类型
            
        Returns:
            ServiceContainer: 容器实例，支持链式调用
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type or service_type,
            lifetime=ServiceLifetime.SCOPED
        )
        self._services[service_type] = descriptor
        logger.debug(f"Registered scoped service: {service_type.__name__}")
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainer':
        """
        注册服务实例
        
        Args:
            service_type: 服务类型
            instance: 服务实例
            
        Returns:
            ServiceContainer: 容器实例，支持链式调用
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )
        self._services[service_type] = descriptor
        self._singletons[service_type] = instance
        logger.debug(f"Registered instance: {service_type.__name__}")
        return self
    
    def register_factory(self, service_type: Type[T], factory: Callable[..., T], 
                        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> 'ServiceContainer':
        """
        注册工厂函数
        
        Args:
            service_type: 服务类型
            factory: 工厂函数
            lifetime: 服务生命周期
            
        Returns:
            ServiceContainer: 容器实例，支持链式调用
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=lifetime
        )
        self._services[service_type] = descriptor
        logger.debug(f"Registered factory for: {service_type.__name__}")
        return self
    
    def get_service(self, service_type: Type[T]) -> T:
        """
        获取服务实例（同步）
        
        Args:
            service_type: 服务类型
            
        Returns:
            T: 服务实例
            
        Raises:
            ServiceResolutionError: 服务解析失败
            CircularDependencyError: 循环依赖
        """
        try:
            return self._resolve_service(service_type)
        except Exception as e:
            logger.error(f"Failed to resolve service {service_type.__name__}: {str(e)}")
            raise ServiceResolutionError(f"Cannot resolve service {service_type.__name__}: {str(e)}")
    
    async def get_service_async(self, service_type: Type[T]) -> T:
        """
        获取服务实例（异步）
        
        Args:
            service_type: 服务类型
            
        Returns:
            T: 服务实例
            
        Raises:
            ServiceResolutionError: 服务解析失败
            CircularDependencyError: 循环依赖
        """
        try:
            return await self._resolve_service_async(service_type)
        except Exception as e:
            logger.error(f"Failed to resolve service {service_type.__name__}: {str(e)}")
            raise ServiceResolutionError(f"Cannot resolve service {service_type.__name__}: {str(e)}")
    
    def _resolve_service(self, service_type: Type[T]) -> T:
        """解析服务实例（同步）"""
        # 检查循环依赖
        if service_type in self._resolution_stack:
            cycle = " -> ".join([t.__name__ for t in self._resolution_stack] + [service_type.__name__])
            raise CircularDependencyError(f"Circular dependency detected: {cycle}")
        
        # 检查是否已注册
        if service_type not in self._services:
            raise ServiceResolutionError(f"Service {service_type.__name__} is not registered")
        
        descriptor = self._services[service_type]
        
        # 处理不同生命周期
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]
            
            instance = self._create_instance(descriptor)
            self._singletons[service_type] = instance
            return instance
        
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if not self._current_scope:
                raise ServiceResolutionError("No active scope for scoped service")
            
            scope_instances = self._scoped_instances.get(self._current_scope, {})
            if service_type in scope_instances:
                return scope_instances[service_type]
            
            instance = self._create_instance(descriptor)
            if self._current_scope not in self._scoped_instances:
                self._scoped_instances[self._current_scope] = {}
            self._scoped_instances[self._current_scope][service_type] = instance
            return instance
        
        else:  # TRANSIENT
            return self._create_instance(descriptor)
    
    async def _resolve_service_async(self, service_type: Type[T]) -> T:
        """解析服务实例（异步）"""
        # 检查循环依赖
        if service_type in self._resolution_stack:
            cycle = " -> ".join([t.__name__ for t in self._resolution_stack] + [service_type.__name__])
            raise CircularDependencyError(f"Circular dependency detected: {cycle}")
        
        # 检查是否已注册
        if service_type not in self._services:
            raise ServiceResolutionError(f"Service {service_type.__name__} is not registered")
        
        descriptor = self._services[service_type]
        
        # 处理不同生命周期
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if service_type in self._singletons:
                return self._singletons[service_type]
            
            instance = await self._create_instance_async(descriptor)
            self._singletons[service_type] = instance
            return instance
        
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if not self._current_scope:
                raise ServiceResolutionError("No active scope for scoped service")
            
            scope_instances = self._scoped_instances.get(self._current_scope, {})
            if service_type in scope_instances:
                return scope_instances[service_type]
            
            instance = await self._create_instance_async(descriptor)
            if self._current_scope not in self._scoped_instances:
                self._scoped_instances[self._current_scope] = {}
            self._scoped_instances[self._current_scope][service_type] = instance
            return instance
        
        else:  # TRANSIENT
            return await self._create_instance_async(descriptor)
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建服务实例（同步）"""
        # 如果有预创建的实例，直接返回
        if descriptor.instance is not None:
            return descriptor.instance
        
        # 如果有工厂函数，使用工厂创建
        if descriptor.factory is not None:
            return self._invoke_factory(descriptor.factory)
        
        # 使用构造函数创建
        if descriptor.implementation_type is None:
            raise ServiceResolutionError("No implementation type or factory provided")
        
        return self._create_instance_with_dependencies(descriptor.implementation_type)
    
    async def _create_instance_async(self, descriptor: ServiceDescriptor) -> Any:
        """创建服务实例（异步）"""
        # 如果有预创建的实例，直接返回
        if descriptor.instance is not None:
            return descriptor.instance
        
        # 如果有工厂函数，使用工厂创建
        if descriptor.factory is not None:
            return await self._invoke_factory_async(descriptor.factory)
        
        # 使用构造函数创建
        if descriptor.implementation_type is None:
            raise ServiceResolutionError("No implementation type or factory provided")
        
        return await self._create_instance_with_dependencies_async(descriptor.implementation_type)
    
    def _create_instance_with_dependencies(self, implementation_type: Type) -> Any:
        """使用依赖注入创建实例（同步）"""
        self._resolution_stack.append(implementation_type)
        
        try:
            # 获取构造函数签名
            constructor = implementation_type.__init__
            sig = inspect.signature(constructor)
            
            # 解析构造函数参数
            args = []
            kwargs = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # 获取参数类型
                param_type = param.annotation
                if param_type == inspect.Parameter.empty:
                    # 如果没有类型注解，尝试从类型提示获取
                    type_hints = get_type_hints(constructor)
                    param_type = type_hints.get(param_name)
                
                if param_type and param_type != inspect.Parameter.empty:
                    # 解析依赖
                    dependency = self._resolve_service(param_type)
                    if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                        args.append(dependency)
                    else:
                        kwargs[param_name] = dependency
                elif param.default != inspect.Parameter.empty:
                    # 有默认值，跳过
                    continue
                else:
                    logger.warning(f"Cannot resolve parameter {param_name} for {implementation_type.__name__}")
            
            # 创建实例
            instance = implementation_type(*args, **kwargs)
            
            # 应用拦截器
            instance = self._apply_interceptors(implementation_type, instance)
            
            return instance
            
        finally:
            self._resolution_stack.pop()
    
    async def _create_instance_with_dependencies_async(self, implementation_type: Type) -> Any:
        """使用依赖注入创建实例（异步）"""
        self._resolution_stack.append(implementation_type)
        
        try:
            # 获取构造函数签名
            constructor = implementation_type.__init__
            sig = inspect.signature(constructor)
            
            # 解析构造函数参数
            args = []
            kwargs = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # 获取参数类型
                param_type = param.annotation
                if param_type == inspect.Parameter.empty:
                    # 如果没有类型注解，尝试从类型提示获取
                    type_hints = get_type_hints(constructor)
                    param_type = type_hints.get(param_name)
                
                if param_type and param_type != inspect.Parameter.empty:
                    # 解析依赖
                    dependency = await self._resolve_service_async(param_type)
                    if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                        args.append(dependency)
                    else:
                        kwargs[param_name] = dependency
                elif param.default != inspect.Parameter.empty:
                    # 有默认值，跳过
                    continue
                else:
                    logger.warning(f"Cannot resolve parameter {param_name} for {implementation_type.__name__}")
            
            # 创建实例
            instance = implementation_type(*args, **kwargs)
            
            # 应用拦截器
            instance = self._apply_interceptors(implementation_type, instance)
            
            return instance
            
        finally:
            self._resolution_stack.pop()
    
    def _invoke_factory(self, factory: Callable) -> Any:
        """调用工厂函数（同步）"""
        sig = inspect.signature(factory)
        args = []
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            param_type = param.annotation
            if param_type and param_type != inspect.Parameter.empty:
                dependency = self._resolve_service(param_type)
                if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                    args.append(dependency)
                else:
                    kwargs[param_name] = dependency
        
        return factory(*args, **kwargs)
    
    async def _invoke_factory_async(self, factory: Callable) -> Any:
        """调用工厂函数（异步）"""
        sig = inspect.signature(factory)
        args = []
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            param_type = param.annotation
            if param_type and param_type != inspect.Parameter.empty:
                dependency = await self._resolve_service_async(param_type)
                if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                    args.append(dependency)
                else:
                    kwargs[param_name] = dependency
        
        result = factory(*args, **kwargs)
        
        # 如果工厂返回协程，等待它
        if asyncio.iscoroutine(result):
            result = await result
        
        return result
    
    def _apply_interceptors(self, service_type: Type, instance: Any) -> Any:
        """应用服务拦截器"""
        interceptors = self._interceptors.get(service_type, [])
        for interceptor in interceptors:
            instance = interceptor(instance)
        return instance
    
    def add_interceptor(self, service_type: Type, interceptor: Callable[[Any], Any]) -> 'ServiceContainer':
        """
        添加服务拦截器
        
        Args:
            service_type: 服务类型
            interceptor: 拦截器函数
            
        Returns:
            ServiceContainer: 容器实例，支持链式调用
        """
        if service_type not in self._interceptors:
            self._interceptors[service_type] = []
        self._interceptors[service_type].append(interceptor)
        return self
    
    @asynccontextmanager
    async def create_scope(self, scope_id: Optional[str] = None):
        """
        创建服务作用域
        
        Args:
            scope_id: 作用域ID，如果不提供则自动生成
        """
        if scope_id is None:
            scope_id = f"scope_{id(self)}_{len(self._scoped_instances)}"
        
        old_scope = self._current_scope
        self._current_scope = scope_id
        
        try:
            yield self
        finally:
            # 清理作用域实例
            if scope_id in self._scoped_instances:
                del self._scoped_instances[scope_id]
            self._current_scope = old_scope
    
    def is_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._services
    
    def get_registered_services(self) -> List[Type]:
        """获取所有已注册的服务类型"""
        return list(self._services.keys())
    
    def get_service_descriptor(self, service_type: Type) -> Optional[ServiceDescriptor]:
        """获取服务描述符"""
        return self._services.get(service_type)
    
    def clear(self):
        """清空容器"""
        self._services.clear()
        self._singletons.clear()
        self._scoped_instances.clear()
        self._resolution_stack.clear()
        self._interceptors.clear()
        
        # 重新注册容器自身
        self.register_instance(ServiceContainer, self)
        self.register_instance(IServiceProvider, self)
    
    def validate_registrations(self) -> List[str]:
        """
        验证服务注册
        
        Returns:
            List[str]: 验证错误列表
        """
        errors = []
        
        for service_type, descriptor in self._services.items():
            try:
                # 检查实现类型是否存在
                if descriptor.implementation_type and not inspect.isclass(descriptor.implementation_type):
                    errors.append(f"Implementation type for {service_type.__name__} is not a class")
                
                # 检查工厂函数是否可调用
                if descriptor.factory and not callable(descriptor.factory):
                    errors.append(f"Factory for {service_type.__name__} is not callable")
                
                # 检查构造函数依赖是否可解析
                if descriptor.implementation_type:
                    constructor = descriptor.implementation_type.__init__
                    sig = inspect.signature(constructor)
                    
                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                        
                        param_type = param.annotation
                        if param_type and param_type != inspect.Parameter.empty:
                            if not self.is_registered(param_type) and param.default == inspect.Parameter.empty:
                                errors.append(
                                    f"Dependency {param_type.__name__} for {service_type.__name__} is not registered"
                                )
                
            except Exception as e:
                errors.append(f"Error validating {service_type.__name__}: {str(e)}")
        
        return errors


# 全局容器实例
_global_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """获取全局容器实例"""
    global _global_container
    if _global_container is None:
        _global_container = ServiceContainer()
    return _global_container


def set_container(container: ServiceContainer):
    """设置全局容器实例"""
    global _global_container
    _global_container = container


# 装饰器支持
def injectable(lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
    """
    可注入服务装饰器
    
    Args:
        lifetime: 服务生命周期
    """
    def decorator(cls):
        # 自动注册到全局容器
        container = get_container()
        if lifetime == ServiceLifetime.SINGLETON:
            container.register_singleton(cls)
        elif lifetime == ServiceLifetime.SCOPED:
            container.register_scoped(cls)
        else:
            container.register_transient(cls)
        
        return cls
    
    return decorator


def inject(service_type: Type[T]) -> T:
    """
    依赖注入装饰器（用于函数参数）
    
    Args:
        service_type: 服务类型
        
    Returns:
        T: 服务实例
    """
    container = get_container()
    return container.get_service(service_type)


async def inject_async(service_type: Type[T]) -> T:
    """
    异步依赖注入
    
    Args:
        service_type: 服务类型
        
    Returns:
        T: 服务实例
    """
    container = get_container()
    return await container.get_service_async(service_type)