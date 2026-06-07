"""
仪表板管理API模块
"""
from fastapi import APIRouter
from .dashboard_config import router as config_router
from .dashboard_data import router as data_router
from .widget_management import router as widget_router
from .color_schemes import router as color_router
from .websocket_api import router as websocket_router
from .report_export import router as report_router

# 创建仪表板主路由
router = APIRouter()

# 注册子路由
router.include_router(config_router, prefix="/config", tags=["仪表板配置"])
router.include_router(data_router, prefix="/data", tags=["仪表板数据"])
router.include_router(widget_router, prefix="/widgets", tags=["组件管理"])
router.include_router(color_router, prefix="/color-schemes", tags=["配色方案"])
router.include_router(websocket_router, prefix="/ws", tags=["实时推送"])
router.include_router(report_router, prefix="/reports", tags=["报告导出"])

# 仪表板模块健康检查
@router.get("/health")
async def dashboard_health_check():
    """仪表板模块健康检查"""
    return {
        "status": "healthy",
        "module": "dashboard-management",
        "version": "1.0.0",
        "message": "仪表板管理模块运行正常"
    }