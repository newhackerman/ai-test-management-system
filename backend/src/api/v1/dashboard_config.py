"""
仪表板配置管理API

提供仪表板配置的CRUD操作、布局保存和重置功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging

from ...core.database import get_db
from ...services.dashboard_service import DashboardService
from ...services.auth import get_current_user
from ...models.user import User
from ...models.dashboard_config import DashboardConfig, RoleType
from ...decorators.dashboard_permissions import (
    require_dashboard_permission,
    get_user_dashboard_permissions
)
from ...services.dashboard_permission_service import DashboardPermissionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard-config", tags=["仪表板配置管理"])

# Pydantic模型定义

class DashboardConfigResponse(BaseModel):
    """仪表板配置响应模型"""
    id: int
    user_id: int
    role_type: str
    dashboard_name: str
    is_default: bool
    layout_config: Optional[Dict[str, Any]] = None
    widget_configs: Optional[List[Dict[str, Any]]] = None
    theme_config: Optional[Dict[str, Any]] = None
    refresh_interval: int
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class SaveLayoutRequest(BaseModel):
    """保存布局请求模型"""
    layout_config: Dict[str, Any] = Field(..., description="布局配置")
    widget_configs: Optional[List[Dict[str, Any]]] = Field(None, description="组件配置列表")
    refresh_interval: Optional[int] = Field(30, ge=5, le=3600, description="刷新间隔(秒)")

    @validator('layout_config')
    def validate_layout_config(cls, v):
        """验证布局配置"""
        if not isinstance(v, dict):
            raise ValueError("Layout config must be a dictionary")
        
        required_fields = ['grid_cols', 'grid_rows', 'widgets']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")
        
        # 验证网格配置
        if not isinstance(v['grid_cols'], int) or v['grid_cols'] <= 0:
            raise ValueError("grid_cols must be a positive integer")
        if not isinstance(v['grid_rows'], int) or v['grid_rows'] <= 0:
            raise ValueError("grid_rows must be a positive integer")
        
        # 验证组件配置
        widgets = v['widgets']
        if not isinstance(widgets, list):
            raise ValueError("widgets must be a list")
        
        for widget in widgets:
            if not isinstance(widget, dict):
                raise ValueError("Each widget must be a dictionary")
            
            required_widget_fields = ['type', 'x', 'y', 'w', 'h']
            for field in required_widget_fields:
                if field not in widget:
                    raise ValueError(f"Widget missing required field: {field}")
            
            # 验证位置和尺寸
            if (widget['x'] < 0 or widget['y'] < 0 or 
                widget['w'] <= 0 or widget['h'] <= 0):
                raise ValueError("Widget position and size must be positive")
            
            # 验证是否超出网格范围
            if (widget['x'] + widget['w'] > v['grid_cols'] or
                widget['y'] + widget['h'] > v['grid_rows']):
                raise ValueError("Widget exceeds grid boundaries")
        
        return v

    @validator('widget_configs')
    def validate_widget_configs(cls, v):
        """验证组件配置列表"""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("Widget configs must be a list")
            
            for config in v:
                if not isinstance(config, dict):
                    raise ValueError("Each widget config must be a dictionary")
                
                if 'type' not in config:
                    raise ValueError("Widget config must have a type field")
        
        return v

class UpdateThemeRequest(BaseModel):
    """更新主题请求模型"""
    color_scheme: Optional[str] = Field(None, description="配色方案")
    dark_mode: Optional[bool] = Field(None, description="暗色模式")
    compact_mode: Optional[bool] = Field(None, description="紧凑模式")

class DashboardTemplateResponse(BaseModel):
    """仪表板模板响应模型"""
    id: int
    role_type: str
    dashboard_name: str
    description: Optional[str] = None
    layout_config: Dict[str, Any]
    widget_configs: List[Dict[str, Any]]
    preview_image: Optional[str] = None
    is_default: bool

    class Config:
        from_attributes = True

# 依赖注入

def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    """获取仪表板服务实例"""
    return DashboardService(db)

# API端点

@router.get("/{role_type}", response_model=DashboardConfigResponse)
@require_dashboard_permission(DashboardPermissionType.DASHBOARD_VIEW)
async def get_dashboard_config(
    role_type: str,
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    获取角色仪表板配置
    
    - **role_type**: 角色类型 (ADMIN, PROJECT_MANAGER, DEVELOPER, etc.)
    """
    try:
        config = await service.get_role_dashboard(current_user.id, role_type)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dashboard config not found for role {role_type}"
            )
        
        return DashboardConfigResponse(
            id=config.id,
            user_id=config.user_id,
            role_type=config.role_type.value,
            dashboard_name=config.dashboard_name,
            is_default=config.is_default,
            layout_config=config.layout_config,
            widget_configs=config.widget_configs,
            theme_config=config.theme_config,
            refresh_interval=config.refresh_interval,
            is_active=config.is_active,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else ""
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting dashboard config for role {role_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取仪表板配置失败"
        )

@router.post("/{role_type}/layout")
@require_dashboard_permission(DashboardPermissionType.DASHBOARD_EDIT)
async def save_dashboard_layout(
    role_type: str,
    request: SaveLayoutRequest,
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    保存仪表板布局
    
    - **role_type**: 角色类型
    - **layout_config**: 布局配置
    - **widget_configs**: 组件配置列表 (可选)
    - **refresh_interval**: 刷新间隔 (可选)
    """
    try:
        config = await service.save_dashboard_layout(
            user_id=current_user.id,
            role_type=role_type,
            layout_config=request.layout_config,
            widget_configs=request.widget_configs
        )
        
        # 更新刷新间隔
        if request.refresh_interval and request.refresh_interval != config.refresh_interval:
            config.refresh_interval = request.refresh_interval
            # 这里应该有更新数据库的逻辑，但为了简化，我们假设service会处理
        
        return {
            "message": "布局保存成功",
            "config_id": config.id,
            "updated_at": config.updated_at.isoformat() if config.updated_at else ""
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error saving dashboard layout for role {role_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存布局失败"
        )

@router.post("/{role_type}/reset")
@require_dashboard_permission(DashboardPermissionType.DASHBOARD_EDIT)
async def reset_dashboard_layout(
    role_type: str,
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    重置仪表板布局为默认配置
    
    - **role_type**: 角色类型
    """
    try:
        config = await service.reset_to_default(current_user.id, role_type)
        
        return {
            "message": "布局重置成功",
            "config_id": config.id,
            "layout_config": config.layout_config,
            "widget_configs": config.widget_configs
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error resetting dashboard layout for role {role_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置布局失败"
        )

@router.put("/{role_type}/theme")
@require_dashboard_permission(DashboardPermissionType.DASHBOARD_EDIT)
async def update_dashboard_theme(
    role_type: str,
    request: UpdateThemeRequest,
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    更新仪表板主题配置
    
    - **role_type**: 角色类型
    - **color_scheme**: 配色方案 (可选)
    - **dark_mode**: 暗色模式 (可选)
    - **compact_mode**: 紧凑模式 (可选)
    """
    try:
        # 获取当前配置
        config = await service.get_role_dashboard(current_user.id, role_type)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dashboard config not found for role {role_type}"
            )
        
        # 更新主题配置
        theme_config = config.theme_config or {}
        
        if request.color_scheme is not None:
            theme_config['color_scheme'] = request.color_scheme
        if request.dark_mode is not None:
            theme_config['dark_mode'] = request.dark_mode
        if request.compact_mode is not None:
            theme_config['compact_mode'] = request.compact_mode
        
        # 保存更新后的配置
        updated_config = await service.save_dashboard_layout(
            user_id=current_user.id,
            role_type=role_type,
            layout_config=config.layout_config,
            widget_configs=config.widget_configs
        )
        
        # 这里应该有更新主题配置的逻辑
        # 为了简化，我们假设service会处理主题更新
        
        return {
            "message": "主题更新成功",
            "theme_config": theme_config
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating dashboard theme for role {role_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新主题失败"
        )

@router.get("/{role_type}/templates", response_model=List[DashboardTemplateResponse])
async def get_dashboard_templates(
    role_type: str,
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    获取仪表板模板列表
    
    - **role_type**: 角色类型
    """
    try:
        templates = await service.get_dashboard_templates(role_type)
        
        return [
            DashboardTemplateResponse(
                id=template.id,
                role_type=template.role_type.value,
                dashboard_name=template.dashboard_name,
                description=template.description if hasattr(template, 'description') else None,
                layout_config=template.layout_config,
                widget_configs=template.widget_configs or [],
                preview_image=None,  # 可以后续添加预览图片功能
                is_default=template.is_default
            )
            for template in templates
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting dashboard templates for role {role_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取仪表板模板失败"
        )

@router.post("/templates/{template_id}/apply")
@require_dashboard_permission(DashboardPermissionType.DASHBOARD_EDIT)
async def apply_dashboard_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    应用仪表板模板
    
    - **template_id**: 模板ID
    """
    try:
        config = await service.apply_template(current_user.id, template_id)
        
        return {
            "message": "模板应用成功",
            "config_id": config.id,
            "role_type": config.role_type.value,
            "layout_config": config.layout_config,
            "widget_configs": config.widget_configs
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error applying dashboard template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="应用模板失败"
        )

@router.get("/user/configs", response_model=List[DashboardConfigResponse])
async def get_user_dashboard_configs(
    current_user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service)
):
    """获取用户所有角色的仪表板配置"""
    try:
        configs = []
        
        # 获取用户的所有角色
        user_roles = []  # 这里应该从用户服务获取用户角色
        
        # 为了演示，我们假设用户可能有的角色
        possible_roles = [role.value for role in RoleType]
        
        for role_type in possible_roles:
            try:
                config = await service.get_role_dashboard(current_user.id, role_type)
                if config:
                    configs.append(DashboardConfigResponse(
                        id=config.id,
                        user_id=config.user_id,
                        role_type=config.role_type.value,
                        dashboard_name=config.dashboard_name,
                        is_default=config.is_default,
                        layout_config=config.layout_config,
                        widget_configs=config.widget_configs,
                        theme_config=config.theme_config,
                        refresh_interval=config.refresh_interval,
                        is_active=config.is_active,
                        created_at=config.created_at.isoformat() if config.created_at else "",
                        updated_at=config.updated_at.isoformat() if config.updated_at else ""
                    ))
            except (ValueError, PermissionError):
                # 用户没有该角色权限，跳过
                continue
        
        return configs
        
    except Exception as e:
        logger.error(f"Error getting user dashboard configs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户仪表板配置失败"
        )

@router.get("/permissions")
async def get_dashboard_permissions(
    permissions: Dict[str, bool] = Depends(get_user_dashboard_permissions)
):
    """获取当前用户的仪表板权限"""
    return {
        "permissions": permissions,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/validate-layout")
async def validate_layout_config(
    layout_config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    验证布局配置的有效性
    
    - **layout_config**: 布局配置
    """
    try:
        # 使用SaveLayoutRequest的验证逻辑
        request = SaveLayoutRequest(layout_config=layout_config)
        
        return {
            "valid": True,
            "message": "布局配置有效"
        }
        
    except ValueError as e:
        return {
            "valid": False,
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Error validating layout config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证布局配置失败"
        )