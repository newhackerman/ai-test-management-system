"""
API v1 路由注册
"""
from fastapi import APIRouter
from .user_role_management import router as user_role_management_router
from .reports import router as reports_router
from .auto_recovery import router as auto_recovery_router
# from .performance import router as performance_router  # Temporarily disabled due to import issues
# from .test_reports import router as test_reports_router  # Temporarily disabled due to import issues

# 创建v1 API路由器
v1_router = APIRouter(prefix="/v1")

# 注册各个模块的路由
v1_router.include_router(user_role_management_router, tags=["用户角色权限管理"])
v1_router.include_router(reports_router, tags=["多格式报告管理"])
v1_router.include_router(auto_recovery_router, tags=["自动恢复服务"])
# v1_router.include_router(performance_router, tags=["性能监控"])  # Temporarily disabled
# v1_router.include_router(test_reports_router, tags=["测试报告"])  # Temporarily disabled

# 导出路由器
__all__ = ["v1_router"]