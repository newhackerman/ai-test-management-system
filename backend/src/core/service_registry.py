"""
服务注册模块 - 统一管理所有服务的注册和配置

本模块负责：
1. 注册所有AI助手相关服务
2. 配置服务依赖关系
3. 管理服务生命周期
4. 提供服务发现功能
"""

import logging
from typing import Type, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from .container import ServiceContainer, ServiceLifetime, get_container
from ..services.ai_assistant_service import AIAssistantService
from ..services.ai_router_service import AIRouterService
from ..services.conversation_service import ConversationService
from ..services.ai_permission_init_service import AIPermissionInitService

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    服务注册表
    
    负责管理所有服务的注册、配置和生命周期管理。
    提供统一的服务注册接口和配置管理功能。
    """
    
    def __init__(self, container: Optional[ServiceContainer] = None):
        self.container = container or get_container()
        self._registered_services: Dict[str, Type] = {}
        self._service_configs: Dict[Type, Dict[str, Any]] = {}
    
    def register_core_services(self) -> 'ServiceRegistry':
        """
        注册核心服务
        
        注册系统核心服务，包括数据库、缓存、配置等基础服务。
        
        Returns:
            ServiceRegistry: 注册表实例，支持链式调用
        """
        logger.info("Registering core services...")
        
        # 注册数据库会话（瞬态服务，每次请求都创建新实例）
        # 注意：在实际部署时应该使用作用域服务
        self.container.register_factory(
            AsyncSession,
            self._create_database_session,
            ServiceLifetime.TRANSIENT
        )
        
        logger.info("Core services registered successfully")
        return self
    
    def register_ai_services(self) -> 'ServiceRegistry':
        """
        注册AI相关服务
        
        注册所有AI助手相关的服务，包括AI助手服务、路由服务、对话服务等。
        
        Returns:
            ServiceRegistry: 注册表实例，支持链式调用
        """
        logger.info("Registering AI services...")
        
        # 注册AI路由服务（单例）
        self.container.register_singleton(AIRouterService)
        self._registered_services['ai_router'] = AIRouterService
        
        # 注册对话服务（单例）
        self.container.register_singleton(ConversationService)
        self._registered_services['conversation'] = ConversationService
        
        # 注册AI助手核心服务（单例）
        self.container.register_singleton(AIAssistantService)
        self._registered_services['ai_assistant'] = AIAssistantService
        
        # 配置服务依赖关系
        self._configure_ai_service_dependencies()
        
        logger.info("AI services registered successfully")
        return self
    
    def register_business_services(self) -> 'ServiceRegistry':
        """
        注册业务服务
        
        注册业务逻辑相关的服务，如用户服务、项目服务、需求服务等。
        
        Returns:
            ServiceRegistry: 注册表实例，支持链式调用
        """
        logger.info("Registering business services...")
        
        # TODO: 在后续任务中注册具体的业务服务
        # 这里预留接口，后续可以注册：
        # - UserService
        # - ProjectService
        # - RequirementService
        # - TestCaseService
        # 等业务服务
        
        logger.info("Business services registered successfully")
        return self
    
    def register_infrastructure_services(self) -> 'ServiceRegistry':
        """
        注册基础设施服务
        
        注册基础设施相关的服务，如缓存、消息队列、文件存储等。
        
        Returns:
            ServiceRegistry: 注册表实例，支持链式调用
        """
        logger.info("Registering infrastructure services...")
        
        # TODO: 在后续任务中注册具体的基础设施服务
        # 这里预留接口，后续可以注册：
        # - CacheService
        # - MessageQueueService
        # - FileStorageService
        # - EmailService
        # 等基础设施服务
        
        logger.info("Infrastructure services registered successfully")
        return self
    
    def _configure_ai_service_dependencies(self):
        """配置AI服务依赖关系"""
        # 配置AI助手服务的依赖
        ai_assistant_config = {
            'dependencies': [AIRouterService, ConversationService],
            'initialization_order': 3,
            'health_check_enabled': True
        }
        self._service_configs[AIAssistantService] = ai_assistant_config
        
        # 配置AI路由服务的依赖
        ai_router_config = {
            'dependencies': [AsyncSession],
            'initialization_order': 1,
            'health_check_enabled': True
        }
        self._service_configs[AIRouterService] = ai_router_config
        
        # 配置对话服务的依赖
        conversation_config = {
            'dependencies': [AsyncSession],
            'initialization_order': 2,
            'health_check_enabled': True
        }
        self._service_configs[ConversationService] = conversation_config
    
    def _create_database_session(self) -> AsyncSession:
        """
        创建数据库会话
        
        工厂函数，用于创建数据库会话实例。
        
        Returns:
            AsyncSession: 数据库会话实例
        """
        # 这里应该从数据库连接池获取会话
        # 实际实现需要与现有的数据库配置集成
        # 由于当前数据库配置是同步的，这里返回一个模拟的异步会话
        # 在实际部署时需要配置真正的异步数据库会话
        
        # 临时解决方案：返回None，让服务自己处理数据库连接
        return None
    
    async def initialize_services(self) -> bool:
        """
        初始化所有已注册的服务
        
        按照依赖顺序初始化所有服务，确保依赖关系正确。
        
        Returns:
            bool: 初始化是否成功
        """
        logger.info("Initializing registered services...")
        
        try:
            # 按初始化顺序排序服务
            services_to_init = []
            for service_type, config in self._service_configs.items():
                order = config.get('initialization_order', 999)
                services_to_init.append((order, service_type))
            
            services_to_init.sort(key=lambda x: x[0])
            
            # 首先初始化AI权限
            try:
                logger.info("Initializing AI permissions...")
                ai_permission_result = await AIPermissionInitService.ensure_ai_permissions()
                if ai_permission_result["success"]:
                    logger.info(f"AI permissions initialized: {ai_permission_result['message']}")
                else:
                    logger.warning(f"AI permissions initialization issue: {ai_permission_result['message']}")
            except Exception as e:
                logger.error(f"Failed to initialize AI permissions: {str(e)}")
                # 不阻止系统启动，只记录错误
            
            # 逐个初始化服务
            for order, service_type in services_to_init:
                try:
                    logger.debug(f"Initializing service: {service_type.__name__}")
                    
                    # 获取服务实例
                    service_instance = await self.container.get_service_async(service_type)
                    
                    # 如果服务有初始化方法，调用它
                    if hasattr(service_instance, 'initialize'):
                        await service_instance.initialize()
                    
                    logger.debug(f"Service {service_type.__name__} initialized successfully")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize service {service_type.__name__}: {str(e)}")
                    return False
            
            logger.info("All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Service initialization failed: {str(e)}")
            return False
    
    async def health_check_services(self) -> Dict[str, bool]:
        """
        检查所有服务的健康状态
        
        Returns:
            Dict[str, bool]: 服务名称到健康状态的映射
        """
        health_status = {}
        
        for service_name, service_type in self._registered_services.items():
            try:
                config = self._service_configs.get(service_type, {})
                if not config.get('health_check_enabled', False):
                    continue
                
                # 获取服务实例
                service_instance = await self.container.get_service_async(service_type)
                
                # 检查健康状态
                if hasattr(service_instance, 'health_check'):
                    is_healthy = await service_instance.health_check()
                    health_status[service_name] = is_healthy
                else:
                    # 如果没有健康检查方法，认为服务健康
                    health_status[service_name] = True
                
            except Exception as e:
                logger.error(f"Health check failed for service {service_name}: {str(e)}")
                health_status[service_name] = False
        
        return health_status
    
    def get_service_info(self, service_type: Type) -> Optional[Dict[str, Any]]:
        """
        获取服务信息
        
        Args:
            service_type: 服务类型
            
        Returns:
            Optional[Dict[str, Any]]: 服务信息，如果服务未注册则返回None
        """
        if not self.container.is_registered(service_type):
            return None
        
        descriptor = self.container.get_service_descriptor(service_type)
        config = self._service_configs.get(service_type, {})
        
        return {
            'service_type': service_type.__name__,
            'lifetime': descriptor.lifetime.value if descriptor else 'unknown',
            'dependencies': [dep.__name__ for dep in config.get('dependencies', [])],
            'initialization_order': config.get('initialization_order', 999),
            'health_check_enabled': config.get('health_check_enabled', False),
            'is_registered': True
        }
    
    def get_all_services_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有服务信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 服务名称到服务信息的映射
        """
        services_info = {}
        
        for service_name, service_type in self._registered_services.items():
            info = self.get_service_info(service_type)
            if info:
                services_info[service_name] = info
        
        return services_info
    
    def validate_service_registrations(self) -> Dict[str, Any]:
        """
        验证服务注册
        
        检查所有服务的注册是否正确，依赖关系是否满足。
        
        Returns:
            Dict[str, Any]: 验证结果
        """
        logger.info("Validating service registrations...")
        
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'services_count': len(self._registered_services),
            'validated_services': []
        }
        
        try:
            # 使用容器的验证功能
            container_errors = self.container.validate_registrations()
            validation_result['errors'].extend(container_errors)
            
            # 检查服务配置
            for service_name, service_type in self._registered_services.items():
                service_validation = {
                    'name': service_name,
                    'type': service_type.__name__,
                    'is_valid': True,
                    'issues': []
                }
                
                # 检查依赖关系
                config = self._service_configs.get(service_type, {})
                dependencies = config.get('dependencies', [])
                
                for dep_type in dependencies:
                    if not self.container.is_registered(dep_type):
                        issue = f"Dependency {dep_type.__name__} is not registered"
                        service_validation['issues'].append(issue)
                        service_validation['is_valid'] = False
                        validation_result['errors'].append(f"{service_name}: {issue}")
                
                # 检查初始化顺序
                init_order = config.get('initialization_order', 999)
                if init_order == 999:
                    warning = f"Service {service_name} has no explicit initialization order"
                    service_validation['issues'].append(warning)
                    validation_result['warnings'].append(warning)
                
                validation_result['validated_services'].append(service_validation)
                
                if not service_validation['is_valid']:
                    validation_result['is_valid'] = False
            
            if validation_result['is_valid']:
                logger.info("Service registration validation passed")
            else:
                logger.warning(f"Service registration validation failed with {len(validation_result['errors'])} errors")
            
        except Exception as e:
            logger.error(f"Service registration validation error: {str(e)}")
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result


# 全局服务注册表实例
_global_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """获取全局服务注册表实例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ServiceRegistry()
    return _global_registry


def configure_services() -> ServiceRegistry:
    """
    配置所有服务
    
    这是服务配置的入口点，负责注册所有必要的服务。
    
    Returns:
        ServiceRegistry: 配置完成的服务注册表
    """
    logger.info("Configuring application services...")
    
    registry = get_service_registry()
    
    # 按顺序注册各类服务
    registry.register_core_services()
    registry.register_infrastructure_services()
    registry.register_business_services()
    registry.register_ai_services()
    
    # 验证服务注册
    validation_result = registry.validate_service_registrations()
    if not validation_result['is_valid']:
        logger.error("Service configuration validation failed")
        for error in validation_result['errors']:
            logger.error(f"  - {error}")
        raise RuntimeError("Service configuration is invalid")
    
    logger.info("Application services configured successfully")
    return registry


async def initialize_application_services() -> bool:
    """
    初始化应用程序服务
    
    Returns:
        bool: 初始化是否成功
    """
    try:
        registry = get_service_registry()
        return await registry.initialize_services()
    except Exception as e:
        logger.error(f"Failed to initialize application services: {str(e)}")
        return False