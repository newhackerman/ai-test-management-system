"""
仪表板管理核心服务
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..core.database import get_async_session
from ..models.dashboard import DashboardConfig, RoleType
from ..services.dashboard_data_integration_service import get_dashboard_data_integration_service
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class DashboardService:
    """仪表板管理服务"""
    
    def __init__(self):
        self.cache_prefix = "dashboard:config:"
        self.cache_ttl = 300  # 5分钟缓存
    
    async def get_role_dashboard(self, user_id: int, role_type: str) -> DashboardConfig:
        """获取角色化仪表板配置"""
        try:
            async for session in get_async_session():
                # 1. 尝试获取用户自定义配置
                user_config_query = select(DashboardConfig).where(
                    and_(
                        DashboardConfig.user_id == user_id,
                        DashboardConfig.role_type == RoleType(role_type),
                        DashboardConfig.is_active == True
                    )
                )
                result = await session.execute(user_config_query)
                user_config = result.scalar_one_or_none()
                
                if user_config:
                    return user_config
                
                # 2. 获取角色默认配置
                default_config_query = select(DashboardConfig).where(
                    and_(
                        DashboardConfig.role_type == RoleType(role_type),
                        DashboardConfig.is_default == True,
                        DashboardConfig.is_active == True
                    )
                )
                result = await session.execute(default_config_query)
                default_config = result.scalar_one_or_none()
                
                if default_config:
                    # 为用户创建基于默认配置的个人配置
                    user_config = DashboardConfig(
                        user_id=user_id,
                        role_type=RoleType(role_type),
                        dashboard_name=f"{role_type}_dashboard",
                        layout_config=default_config.layout_config,
                        widget_configs=default_config.widget_configs,
                        theme_config=default_config.theme_config,
                        refresh_interval=default_config.refresh_interval,
                        is_default=False
                    )
                    session.add(user_config)
                    await session.commit()
                    await session.refresh(user_config)
                    return user_config
                
                # 3. 创建默认配置
                default_config = await self._create_default_dashboard(session, role_type)
                
                # 为用户创建个人配置
                user_config = DashboardConfig(
                    user_id=user_id,
                    role_type=RoleType(role_type),
                    dashboard_name=f"{role_type}_dashboard",
                    layout_config=default_config.layout_config,
                    widget_configs=default_config.widget_configs,
                    theme_config=default_config.theme_config,
                    refresh_interval=default_config.refresh_interval,
                    is_default=False
                )
                session.add(user_config)
                await session.commit()
                await session.refresh(user_config)
                return user_config
                
        except Exception as e:
            logger.error(f"获取角色仪表板配置失败: {e}")
            raise
    
    async def save_dashboard_layout(
        self,
        user_id: int,
        role_type: str,
        layout_config: Dict[str, Any],
        widget_configs: List[Dict[str, Any]] = None,
        theme_config: Dict[str, Any] = None,
        refresh_interval: int = 30
    ) -> DashboardConfig:
        """保存仪表板布局配置"""
        try:
            # 验证布局配置
            await self._validate_layout_config(layout_config)
            
            async for session in get_async_session():
                # 获取或创建用户配置
                config_query = select(DashboardConfig).where(
                    and_(
                        DashboardConfig.user_id == user_id,
                        DashboardConfig.role_type == RoleType(role_type),
                        DashboardConfig.is_active == True
                    )
                )
                result = await session.execute(config_query)
                config = result.scalar_one_or_none()
                
                if not config:
                    config = DashboardConfig(
                        user_id=user_id,
                        role_type=RoleType(role_type),
                        dashboard_name=f"{role_type}_dashboard",
                        is_default=False
                    )
                    session.add(config)
                
                # 更新配置
                config.layout_config = layout_config
                if widget_configs is not None:
                    config.widget_configs = widget_configs
                if theme_config is not None:
                    config.theme_config = theme_config
                config.refresh_interval = refresh_interval
                config.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(config)
                
                # 清除缓存
                await self._clear_user_cache(user_id, role_type)
                
                return config
                
        except Exception as e:
            logger.error(f"保存仪表板布局失败: {e}")
            raise
    
    async def reset_to_default(self, user_id: int, role_type: str) -> bool:
        """重置仪表板为默认配置"""
        try:
            async for session in get_async_session():
                # 删除用户自定义配置
                config_query = select(DashboardConfig).where(
                    and_(
                        DashboardConfig.user_id == user_id,
                        DashboardConfig.role_type == RoleType(role_type),
                        DashboardConfig.is_active == True
                    )
                )
                result = await session.execute(config_query)
                config = result.scalar_one_or_none()
                
                if config:
                    await session.delete(config)
                    await session.commit()
                
                # 清除缓存
                await self._clear_user_cache(user_id, role_type)
                
                return True
                
        except Exception as e:
            logger.error(f"重置仪表板配置失败: {e}")
            return False
    
    async def get_user_dashboards(self, user_id: int) -> List[DashboardConfig]:
        """获取用户所有仪表板配置"""
        try:
            async for session in get_async_session():
                query = select(DashboardConfig).where(
                    and_(
                        DashboardConfig.user_id == user_id,
                        DashboardConfig.is_active == True
                    )
                ).order_by(DashboardConfig.updated_at.desc())
                
                result = await session.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"获取用户仪表板配置失败: {e}")
            return []
    
    async def create_dashboard(
        self,
        user_id: int,
        dashboard_name: str,
        role_type: str,
        layout_config: Dict[str, Any] = None,
        widget_configs: List[Dict[str, Any]] = None,
        theme_config: Dict[str, Any] = None,
        refresh_interval: int = 30
    ) -> DashboardConfig:
        """创建新的仪表板配置"""
        try:
            async for session in get_async_session():
                config = DashboardConfig(
                    user_id=user_id,
                    role_type=RoleType(role_type),
                    dashboard_name=dashboard_name,
                    layout_config=layout_config or {},
                    widget_configs=widget_configs or [],
                    theme_config=theme_config or {},
                    refresh_interval=refresh_interval,
                    is_default=False
                )
                
                session.add(config)
                await session.commit()
                await session.refresh(config)
                
                return config
                
        except Exception as e:
            logger.error(f"创建仪表板配置失败: {e}")
            raise
    
    async def delete_dashboard(self, config_id: int, user_id: int) -> bool:
        """删除仪表板配置"""
        try:
            async for session in get_async_session():
                config_query = select(DashboardConfig).where(
                    and_(
                        DashboardConfig.id == config_id,
                        DashboardConfig.user_id == user_id
                    )
                )
                result = await session.execute(config_query)
                config = result.scalar_one_or_none()
                
                if not config:
                    raise ValueError("仪表板配置不存在或无权限删除")
                
                await session.delete(config)
                await session.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"删除仪表板配置失败: {e}")
            raise
    
    async def export_dashboard_config(self, config_id: int, user_id: int) -> Dict[str, Any]:
        """导出仪表板配置"""
        try:
            async for session in get_async_session():
                config_query = select(DashboardConfig).where(
                    and_(
                        DashboardConfig.id == config_id,
                        DashboardConfig.user_id == user_id
                    )
                )
                result = await session.execute(config_query)
                config = result.scalar_one_or_none()
                
                if not config:
                    raise ValueError("仪表板配置不存在或无权限访问")
                
                return {
                    "dashboard_name": config.dashboard_name,
                    "role_type": config.role_type.value,
                    "layout_config": config.layout_config,
                    "widget_configs": config.widget_configs,
                    "theme_config": config.theme_config,
                    "refresh_interval": config.refresh_interval,
                    "exported_at": datetime.utcnow().isoformat(),
                    "version": "1.0"
                }
                
        except Exception as e:
            logger.error(f"导出仪表板配置失败: {e}")
            raise
    
    async def import_dashboard_config(self, config_data: Dict[str, Any], user_id: int) -> DashboardConfig:
        """导入仪表板配置"""
        try:
            # 验证配置数据
            required_fields = ["dashboard_name", "role_type"]
            for field in required_fields:
                if field not in config_data:
                    raise ValueError(f"缺少必需字段: {field}")
            
            async for session in get_async_session():
                config = DashboardConfig(
                    user_id=user_id,
                    role_type=RoleType(config_data["role_type"]),
                    dashboard_name=config_data["dashboard_name"],
                    layout_config=config_data.get("layout_config", {}),
                    widget_configs=config_data.get("widget_configs", []),
                    theme_config=config_data.get("theme_config", {}),
                    refresh_interval=config_data.get("refresh_interval", 30),
                    is_default=False
                )
                
                session.add(config)
                await session.commit()
                await session.refresh(config)
                
                return config
                
        except Exception as e:
            logger.error(f"导入仪表板配置失败: {e}")
            raise
    
    async def _create_default_dashboard(self, session: AsyncSession, role_type: str) -> DashboardConfig:
        """创建默认仪表板配置"""
        default_layouts = {
            "ADMIN": {
                "layout": [
                    {"i": "system-overview", "x": 0, "y": 0, "w": 6, "h": 4},
                    {"i": "user-statistics", "x": 6, "y": 0, "w": 6, "h": 4},
                    {"i": "performance-metrics", "x": 0, "y": 4, "w": 12, "h": 6}
                ],
                "widgets": [
                    {"id": "system-overview", "type": "stat_card", "title": "系统概览"},
                    {"id": "user-statistics", "type": "chart", "title": "用户统计"},
                    {"id": "performance-metrics", "type": "trend_chart", "title": "性能指标"}
                ]
            },
            "PROJECT_MANAGER": {
                "layout": [
                    {"i": "project-overview", "x": 0, "y": 0, "w": 8, "h": 4},
                    {"i": "team-status", "x": 8, "y": 0, "w": 4, "h": 4},
                    {"i": "progress-chart", "x": 0, "y": 4, "w": 6, "h": 6},
                    {"i": "milestone-timeline", "x": 6, "y": 4, "w": 6, "h": 6}
                ],
                "widgets": [
                    {"id": "project-overview", "type": "stat_card", "title": "项目概览"},
                    {"id": "team-status", "type": "status_panel", "title": "团队状态"},
                    {"id": "progress-chart", "type": "progress_chart", "title": "项目进度"},
                    {"id": "milestone-timeline", "type": "timeline", "title": "里程碑时间线"}
                ]
            },
            "DEVELOPER": {
                "layout": [
                    {"i": "my-tasks", "x": 0, "y": 0, "w": 6, "h": 4},
                    {"i": "code-quality", "x": 6, "y": 0, "w": 6, "h": 4},
                    {"i": "commit-activity", "x": 0, "y": 4, "w": 12, "h": 6}
                ],
                "widgets": [
                    {"id": "my-tasks", "type": "task_list", "title": "我的任务"},
                    {"id": "code-quality", "type": "quality_metrics", "title": "代码质量"},
                    {"id": "commit-activity", "type": "activity_chart", "title": "提交活动"}
                ]
            },
            "TESTER": {
                "layout": [
                    {"i": "test-execution", "x": 0, "y": 0, "w": 6, "h": 4},
                    {"i": "defect-summary", "x": 6, "y": 0, "w": 6, "h": 4},
                    {"i": "test-coverage", "x": 0, "y": 4, "w": 12, "h": 6}
                ],
                "widgets": [
                    {"id": "test-execution", "type": "execution_stats", "title": "测试执行"},
                    {"id": "defect-summary", "type": "defect_chart", "title": "缺陷统计"},
                    {"id": "test-coverage", "type": "coverage_chart", "title": "测试覆盖率"}
                ]
            }
        }
        
        layout_config = default_layouts.get(role_type, default_layouts["ADMIN"])
        
        config = DashboardConfig(
            user_id=0,  # 系统默认配置
            role_type=RoleType(role_type),
            dashboard_name=f"默认{role_type}仪表板",
            layout_config=layout_config["layout"],
            widget_configs=layout_config["widgets"],
            theme_config={"colorScheme": "default"},
            refresh_interval=30,
            is_default=True
        )
        
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        return config
    
    async def _validate_layout_config(self, layout_config: Dict[str, Any]) -> bool:
        """验证布局配置"""
        if not isinstance(layout_config, (dict, list)):
            raise ValueError("布局配置格式无效")
        
        # 这里可以添加更多的验证逻辑
        return True
    
    async def _clear_user_cache(self, user_id: int, role_type: str):
        """清除用户缓存"""
        try:
            redis_client = await get_redis_client()
            cache_key = f"{self.cache_prefix}{user_id}:{role_type}"
            await redis_client.delete(cache_key)
        except Exception as e:
            logger.warning(f"清除用户缓存失败: {e}")


# 依赖注入
_dashboard_service = None

async def get_dashboard_service() -> DashboardService:
    """获取仪表板服务实例"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    return _dashboard_service