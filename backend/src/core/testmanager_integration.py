"""
测试管理模块系统集成配置

集成现有系统的用户认证、权限控制、数据库连接、Redis缓存、文件存储和日志记录等功能
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings, get_route_config
from .database import get_async_session
from .redis import redis_service, get_redis_client
from .auth import get_current_user
from .dependencies import get_di_container
from ..services.permission_service import PermissionService
from ..services.ai_file_storage_service import AIFileStorageService
from ..utils.logger import logger

# 测试管理模块权限定义
TESTMANAGER_PERMISSIONS = {
    # 测试计划权限
    "testplan.create": "创建测试计划",
    "testplan.read": "查看测试计划", 
    "testplan.update": "更新测试计划",
    "testplan.delete": "删除测试计划",
    "testplan.execute": "执行测试计划",
    "testplan.approve": "审批测试计划",
    
    # 测试用例权限
    "testcase.create": "创建测试用例",
    "testcase.read": "查看测试用例",
    "testcase.update": "更新测试用例", 
    "testcase.delete": "删除测试用例",
    "testcase.execute": "执行测试用例",
    "testcase.review": "评审测试用例",
    "testcase.generate": "AI生成测试用例",
    
    # 测试执行权限
    "execution.create": "创建测试执行",
    "execution.read": "查看测试执行",
    "execution.update": "更新测试执行",
    "execution.delete": "删除测试执行",
    "execution.monitor": "监控测试执行",
    "execution.automation": "自动化测试执行",
    
    # 缺陷管理权限
    "defect.create": "创建缺陷",
    "defect.read": "查看缺陷",
    "defect.update": "更新缺陷",
    "defect.delete": "删除缺陷",
    "defect.assign": "分配缺陷",
    "defect.resolve": "解决缺陷",
    "defect.close": "关闭缺陷",
    
    # 测试报告权限
    "report.create": "创建测试报告",
    "report.read": "查看测试报告",
    "report.update": "更新测试报告",
    "report.delete": "删除测试报告",
    "report.export": "导出测试报告",
    "report.share": "分享测试报告",
    
    # 专项测试权限
    "performance.test": "性能测试",
    "security.test": "安全测试",
    "automation.manage": "自动化管理",
    
    # 管理权限
    "testmanager.admin": "测试管理员",
    "testmanager.config": "测试配置管理"
}

# 测试管理模块角色定义
TESTMANAGER_ROLES = {
    "test_manager": {
        "name": "测试经理",
        "description": "测试团队负责人，拥有测试管理的完整权限",
        "permissions": [
            "testplan.create", "testplan.read", "testplan.update", "testplan.delete", 
            "testplan.execute", "testplan.approve",
            "testcase.create", "testcase.read", "testcase.update", "testcase.delete",
            "testcase.execute", "testcase.review", "testcase.generate",
            "execution.create", "execution.read", "execution.update", "execution.delete",
            "execution.monitor", "execution.automation",
            "defect.create", "defect.read", "defect.update", "defect.delete",
            "defect.assign", "defect.resolve", "defect.close",
            "report.create", "report.read", "report.update", "report.delete",
            "report.export", "report.share",
            "performance.test", "security.test", "automation.manage",
            "testmanager.admin", "testmanager.config"
        ]
    },
    "test_lead": {
        "name": "测试主管",
        "description": "测试团队主管，拥有测试执行和管理权限",
        "permissions": [
            "testplan.create", "testplan.read", "testplan.update", "testplan.execute",
            "testcase.create", "testcase.read", "testcase.update", "testcase.execute",
            "testcase.review", "testcase.generate",
            "execution.create", "execution.read", "execution.update", "execution.monitor",
            "execution.automation",
            "defect.create", "defect.read", "defect.update", "defect.assign",
            "defect.resolve", "defect.close",
            "report.create", "report.read", "report.update", "report.export",
            "performance.test", "security.test", "automation.manage"
        ]
    },
    "test_engineer": {
        "name": "测试工程师",
        "description": "测试工程师，拥有测试用例和执行权限",
        "permissions": [
            "testplan.read", "testplan.execute",
            "testcase.create", "testcase.read", "testcase.update", "testcase.execute",
            "testcase.generate",
            "execution.create", "execution.read", "execution.update", "execution.monitor",
            "defect.create", "defect.read", "defect.update",
            "report.read", "report.export",
            "automation.manage"
        ]
    },
    "automation_engineer": {
        "name": "自动化测试工程师", 
        "description": "自动化测试工程师，专注于自动化测试",
        "permissions": [
            "testplan.read", "testplan.execute",
            "testcase.read", "testcase.execute", "testcase.generate",
            "execution.create", "execution.read", "execution.update", "execution.monitor",
            "execution.automation",
            "defect.create", "defect.read", "defect.update",
            "report.read", "report.export",
            "performance.test", "security.test", "automation.manage"
        ]
    },
    "test_viewer": {
        "name": "测试查看者",
        "description": "只读权限，可查看测试相关信息",
        "permissions": [
            "testplan.read", "testcase.read", "execution.read",
            "defect.read", "report.read"
        ]
    }
}


class TestManagerIntegration:
    """测试管理模块集成服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志记录"""
        # 使用现有系统的日志配置
        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        
        # 如果没有处理器，添加控制台处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def get_route_config(self) -> Dict[str, Dict[str, str]]:
        """获取测试管理模块的路由配置"""
        return {
            "test_plans": {
                "prefix": "/test-plans",
                "tags": ["测试计划管理"]
            },
            "test_cases": {
                "prefix": "/test-cases", 
                "tags": ["测试用例管理"]
            },
            "test_executions": {
                "prefix": "/test-executions",
                "tags": ["测试执行管理"]
            },
            "defects": {
                "prefix": "/defects",
                "tags": ["缺陷管理"]
            },
            "test_reports": {
                "prefix": "/test-reports",
                "tags": ["测试报告管理"]
            },
            "performance_tests": {
                "prefix": "/performance-tests",
                "tags": ["性能测试"]
            },
            "security_tests": {
                "prefix": "/security-tests",
                "tags": ["安全测试"]
            }
        }
    
    async def get_permission_service(self, db: AsyncSession) -> PermissionService:
        """获取权限服务实例"""
        return PermissionService(db)
    
    async def get_file_storage_service(self, db: AsyncSession) -> AIFileStorageService:
        """获取文件存储服务实例"""
        return AIFileStorageService(db)
    
    async def check_permission(
        self, 
        user: Dict[str, Any], 
        permission: str,
        db: AsyncSession
    ) -> bool:
        """检查用户权限"""
        try:
            permission_service = await self.get_permission_service(db)
            return await permission_service.check_permission(user["id"], permission)
        except Exception as e:
            self.logger.error(f"权限检查失败: {e}")
            return False
    
    def get_cache_key(self, module: str, key: str, *args) -> str:
        """生成缓存键"""
        base_key = f"testmanager:{module}:{key}"
        if args:
            base_key += ":" + ":".join(str(arg) for arg in args)
        return base_key
    
    async def get_cache(self, key: str) -> Any:
        """获取缓存数据"""
        try:
            return redis_service.get(key)
        except Exception as e:
            self.logger.error(f"获取缓存失败: {e}")
            return None
    
    async def set_cache(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置缓存数据"""
        try:
            return redis_service.set(key, value, expire or settings.CACHE_TTL)
        except Exception as e:
            self.logger.error(f"设置缓存失败: {e}")
            return False
    
    async def delete_cache(self, key: str) -> bool:
        """删除缓存数据"""
        try:
            return redis_service.delete(key)
        except Exception as e:
            self.logger.error(f"删除缓存失败: {e}")
            return False
    
    async def clear_cache_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            keys = redis_service.keys(pattern)
            count = 0
            for key in keys:
                if redis_service.delete(key):
                    count += 1
            return count
        except Exception as e:
            self.logger.error(f"清除缓存失败: {e}")
            return 0
    
    def log_operation(
        self, 
        user_id: int, 
        operation: str, 
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录操作日志"""
        try:
            log_data = {
                "user_id": user_id,
                "operation": operation,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "timestamp": logger.info.__name__  # 使用当前时间
            }
            self.logger.info(f"操作日志: {log_data}")
        except Exception as e:
            self.logger.error(f"记录操作日志失败: {e}")


# 全局集成实例
testmanager_integration = TestManagerIntegration()


# 依赖注入函数

async def get_testmanager_integration() -> TestManagerIntegration:
    """获取测试管理集成服务"""
    return testmanager_integration


async def get_current_user_with_permissions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """获取当前用户及其权限信息"""
    try:
        permission_service = PermissionService(db)
        user_permissions = await permission_service.get_user_permissions(current_user["id"])
        
        # 合并用户信息和权限信息
        current_user.update({
            "permissions": user_permissions.get("all_permissions", []),
            "permission_codes": user_permissions.get("permission_codes", set()),
            "roles": user_permissions.get("roles", [])
        })
        
        return current_user
    except Exception as e:
        logger.error(f"获取用户权限失败: {e}")
        # 返回基本用户信息，权限为空
        current_user.update({
            "permissions": [],
            "permission_codes": set(),
            "roles": []
        })
        return current_user


def require_testmanager_permission(permission: str):
    """测试管理权限装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user和db
            current_user = kwargs.get("current_user")
            db = kwargs.get("db")
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="认证信息不完整"
                )
            
            # 检查权限
            has_permission = await testmanager_integration.check_permission(
                current_user, permission, db
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"缺少权限: {permission}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def get_testmanager_file_storage(
    db: AsyncSession = Depends(get_async_session)
) -> AIFileStorageService:
    """获取测试管理文件存储服务"""
    return AIFileStorageService(db)


async def get_testmanager_cache_service():
    """获取测试管理缓存服务"""
    return redis_service


# 缓存工具函数

class TestManagerCache:
    """测试管理缓存工具类"""
    
    @staticmethod
    def get_test_plan_key(plan_id: int) -> str:
        """获取测试计划缓存键"""
        return testmanager_integration.get_cache_key("testplan", "info", plan_id)
    
    @staticmethod
    def get_test_case_key(case_id: int) -> str:
        """获取测试用例缓存键"""
        return testmanager_integration.get_cache_key("testcase", "info", case_id)
    
    @staticmethod
    def get_execution_key(execution_id: int) -> str:
        """获取测试执行缓存键"""
        return testmanager_integration.get_cache_key("execution", "info", execution_id)
    
    @staticmethod
    def get_defect_key(defect_id: int) -> str:
        """获取缺陷缓存键"""
        return testmanager_integration.get_cache_key("defect", "info", defect_id)
    
    @staticmethod
    def get_report_key(report_id: int) -> str:
        """获取报告缓存键"""
        return testmanager_integration.get_cache_key("report", "info", report_id)
    
    @staticmethod
    def get_user_test_plans_key(user_id: int) -> str:
        """获取用户测试计划列表缓存键"""
        return testmanager_integration.get_cache_key("user", "testplans", user_id)
    
    @staticmethod
    def get_project_test_stats_key(project_id: int) -> str:
        """获取项目测试统计缓存键"""
        return testmanager_integration.get_cache_key("project", "stats", project_id)
    
    @staticmethod
    async def invalidate_test_plan_cache(plan_id: int):
        """清除测试计划相关缓存"""
        keys_to_delete = [
            TestManagerCache.get_test_plan_key(plan_id),
            testmanager_integration.get_cache_key("testplan", "cases", plan_id),
            testmanager_integration.get_cache_key("testplan", "progress", plan_id)
        ]
        
        for key in keys_to_delete:
            await testmanager_integration.delete_cache(key)
    
    @staticmethod
    async def invalidate_test_case_cache(case_id: int):
        """清除测试用例相关缓存"""
        keys_to_delete = [
            TestManagerCache.get_test_case_key(case_id),
            testmanager_integration.get_cache_key("testcase", "executions", case_id)
        ]
        
        for key in keys_to_delete:
            await testmanager_integration.delete_cache(key)
    
    @staticmethod
    async def invalidate_user_cache(user_id: int):
        """清除用户相关缓存"""
        pattern = testmanager_integration.get_cache_key("user", "*", user_id)
        await testmanager_integration.clear_cache_pattern(pattern)
    
    @staticmethod
    async def invalidate_project_cache(project_id: int):
        """清除项目相关缓存"""
        pattern = testmanager_integration.get_cache_key("project", "*", project_id)
        await testmanager_integration.clear_cache_pattern(pattern)


# 初始化函数

async def init_testmanager_permissions(db: AsyncSession):
    """初始化测试管理模块权限"""
    try:
        permission_service = PermissionService(db)
        
        # 创建测试管理模块权限
        for perm_code, perm_name in TESTMANAGER_PERMISSIONS.items():
            try:
                module, action = perm_code.split(".", 1)
                
                permission_data = {
                    "code": perm_code,
                    "name": perm_name,
                    "description": f"测试管理模块 - {perm_name}",
                    "module": f"testmanager.{module}",
                    "action": action,
                    "resource": module,
                    "permission_type": "api",
                    "level": 1,
                    "sort_order": 0,
                    "effect": "allow",
                    "is_system_permission": True
                }
                
                await permission_service.create_permission(permission_data)
                logger.info(f"创建权限: {perm_code}")
                
            except Exception as e:
                logger.warning(f"权限 {perm_code} 可能已存在: {e}")
        
        logger.info("测试管理模块权限初始化完成")
        
    except Exception as e:
        logger.error(f"初始化测试管理模块权限失败: {e}")


async def setup_testmanager_integration():
    """设置测试管理模块集成"""
    try:
        # 更新系统配置，添加测试管理模块路由
        route_configs = testmanager_integration.get_route_config()
        
        # 将路由配置添加到系统配置中
        for route_name, config in route_configs.items():
            settings.API_ROUTES[route_name] = config
        
        logger.info("测试管理模块集成设置完成")
        
    except Exception as e:
        logger.error(f"设置测试管理模块集成失败: {e}")