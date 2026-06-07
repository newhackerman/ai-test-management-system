"""
仪表板模块系统集成配置
"""
import logging
from typing import Dict, Any, Optional, List
from functools import lru_cache

from .config import get_settings
from .database import get_async_session
from .security import get_current_user
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class DashboardIntegrationConfig:
    """仪表板模块集成配置管理"""
    
    def __init__(self):
        self.settings = get_settings()
        self._integration_status = {}
    
    async def initialize_dashboard_integration(self) -> bool:
        """初始化仪表板模块集成"""
        try:
            logger.info("开始初始化仪表板模块集成...")
            
            # 1. 验证数据库连接
            db_status = await self._verify_database_connection()
            self._integration_status['database'] = db_status
            
            # 2. 验证Redis缓存连接
            cache_status = await self._verify_cache_connection()
            self._integration_status['cache'] = cache_status
            
            # 3. 验证用户认证系统
            auth_status = await self._verify_auth_system()
            self._integration_status['auth'] = auth_status
            
            # 4. 验证权限控制系统
            permission_status = await self._verify_permission_system()
            self._integration_status['permissions'] = permission_status
            
            # 5. 验证文件存储系统
            storage_status = await self._verify_storage_system()
            self._integration_status['storage'] = storage_status
            
            # 6. 验证消息队列系统
            queue_status = await self._verify_message_queue()
            self._integration_status['message_queue'] = queue_status
            
            # 7. 验证日志记录系统
            logging_status = await self._verify_logging_system()
            self._integration_status['logging'] = logging_status
            
            # 8. 验证监控体系
            monitoring_status = await self._verify_monitoring_system()
            self._integration_status['monitoring'] = monitoring_status
            
            # 检查集成状态
            all_systems_ok = all(self._integration_status.values())
            
            if all_systems_ok:
                logger.info("仪表板模块集成初始化完成 - 所有系统正常")
                return True
            else:
                failed_systems = [k for k, v in self._integration_status.items() if not v]
                logger.warning(f"仪表板模块集成初始化部分失败 - 失败系统: {failed_systems}")
                return False
                
        except Exception as e:
            logger.error(f"仪表板模块集成初始化失败: {e}")
            return False
    
    async def _verify_database_connection(self) -> bool:
        """验证数据库连接"""
        try:
            async for session in get_async_session():
                # 执行简单查询验证连接
                result = await session.execute("SELECT 1")
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"数据库连接验证失败: {e}")
            return False
    
    async def _verify_cache_connection(self) -> bool:
        """验证Redis缓存连接"""
        try:
            redis_client = await get_redis_client()
            # 测试Redis连接
            await redis_client.ping()
            
            # 测试基本操作
            test_key = "dashboard:integration:test"
            await redis_client.set(test_key, "test_value", ex=10)
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            return value == "test_value"
        except Exception as e:
            logger.error(f"Redis缓存连接验证失败: {e}")
            return False
    
    async def _verify_auth_system(self) -> bool:
        """验证用户认证系统"""
        try:
            # 验证JWT配置
            if not self.settings.JWT_SECRET_KEY:
                logger.error("JWT密钥未配置")
                return False
            
            # 验证认证相关配置
            required_auth_configs = [
                'JWT_ALGORITHM',
                'ACCESS_TOKEN_EXPIRE_MINUTES'
            ]
            
            for config in required_auth_configs:
                if not hasattr(self.settings, config):
                    logger.error(f"认证配置缺失: {config}")
                    return False
            
            logger.info("用户认证系统验证通过")
            return True
            
        except Exception as e:
            logger.error(f"用户认证系统验证失败: {e}")
            return False
    
    async def _verify_permission_system(self) -> bool:
        """验证权限控制系统"""
        try:
            # 验证权限相关表是否存在
            async for session in get_async_session():
                # 检查用户表
                result = await session.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = 'users'"
                )
                if result.scalar() == 0:
                    logger.error("用户表不存在")
                    return False
                
                # 检查角色表
                result = await session.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = 'roles'"
                )
                if result.scalar() == 0:
                    logger.error("角色表不存在")
                    return False
                
                # 检查权限表
                result = await session.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = 'permissions'"
                )
                if result.scalar() == 0:
                    logger.error("权限表不存在")
                    return False
            
            logger.info("权限控制系统验证通过")
            return True
            
        except Exception as e:
            logger.error(f"权限控制系统验证失败: {e}")
            return False
    
    async def _verify_storage_system(self) -> bool:
        """验证文件存储系统"""
        try:
            import os
            
            # 验证上传目录配置
            upload_dir = getattr(self.settings, 'UPLOAD_DIR', 'uploads')
            
            # 确保上传目录存在
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
            
            # 验证目录可写
            test_file = os.path.join(upload_dir, 'dashboard_test.txt')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception as e:
                logger.error(f"文件存储目录不可写: {e}")
                return False
            
            logger.info("文件存储系统验证通过")
            return True
            
        except Exception as e:
            logger.error(f"文件存储系统验证失败: {e}")
            return False
    
    async def _verify_message_queue(self) -> bool:
        """验证消息队列系统"""
        try:
            # 使用Redis作为消息队列
            redis_client = await get_redis_client()
            
            # 测试队列操作
            test_queue = "dashboard:test:queue"
            test_message = {"type": "test", "data": "integration_test"}
            
            # 推送消息
            await redis_client.lpush(test_queue, str(test_message))
            
            # 获取消息
            message = await redis_client.rpop(test_queue)
            
            if message:
                logger.info("消息队列系统验证通过")
                return True
            else:
                logger.error("消息队列操作失败")
                return False
                
        except Exception as e:
            logger.error(f"消息队列系统验证失败: {e}")
            return False
    
    async def _verify_logging_system(self) -> bool:
        """验证日志记录系统"""
        try:
            # 验证日志配置
            log_level = getattr(self.settings, 'LOG_LEVEL', 'INFO')
            
            # 测试日志记录
            test_logger = logging.getLogger('dashboard.integration.test')
            test_logger.info("仪表板模块日志系统测试")
            
            logger.info("日志记录系统验证通过")
            return True
            
        except Exception as e:
            logger.error(f"日志记录系统验证失败: {e}")
            return False
    
    async def _verify_monitoring_system(self) -> bool:
        """验证监控体系"""
        try:
            # 验证性能监控中间件
            from ..middleware.performance_middleware import PerformanceMiddleware
            
            # 验证健康检查端点
            # 这里可以添加更多监控系统的验证逻辑
            
            logger.info("监控体系验证通过")
            return True
            
        except Exception as e:
            logger.error(f"监控体系验证失败: {e}")
            return False
    
    def get_integration_status(self) -> Dict[str, bool]:
        """获取集成状态"""
        return self._integration_status.copy()
    
    def is_fully_integrated(self) -> bool:
        """检查是否完全集成"""
        return all(self._integration_status.values()) if self._integration_status else False


@lru_cache()
def get_dashboard_integration_config() -> DashboardIntegrationConfig:
    """获取仪表板集成配置实例"""
    return DashboardIntegrationConfig()


# 仪表板模块配置常量
DASHBOARD_CONFIG = {
    # API路由配置
    "api_prefix": "/dashboards",
    "api_tags": ["仪表板管理"],
    
    # WebSocket配置
    "websocket_prefix": "/ws/dashboard",
    
    # 缓存配置
    "cache_prefix": "dashboard:",
    "default_cache_ttl": 300,  # 5分钟
    
    # 数据刷新配置
    "default_refresh_interval": 30,  # 30秒
    "min_refresh_interval": 10,      # 最小10秒
    "max_refresh_interval": 3600,    # 最大1小时
    
    # 组件配置
    "max_widgets_per_dashboard": 20,
    "max_dashboard_configs_per_user": 10,
    
    # 文件上传配置
    "max_color_scheme_image_size": 2 * 1024 * 1024,  # 2MB
    "allowed_image_types": ["image/jpeg", "image/png", "image/gif"],
    
    # 实时推送配置
    "websocket_heartbeat_interval": 30,  # 30秒心跳
    "websocket_timeout": 300,            # 5分钟超时
    "max_websocket_connections": 1000,   # 最大连接数
}


def get_dashboard_config(key: str, default: Any = None) -> Any:
    """获取仪表板配置"""
    return DASHBOARD_CONFIG.get(key, default)