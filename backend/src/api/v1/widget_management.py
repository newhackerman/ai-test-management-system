"""
组件管理API

提供组件定义的CRUD操作、配置和权限验证、数据源绑定接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum
import logging

from ...core.database import get_db
from ...services.widget_service import WidgetService
from ...services.auth import get_current_user
from ...models.user import User
from ...models.widget_definition import WidgetDefinition, WidgetCategory, DataSourceType
from ...models.dashboard_config import RoleType
from ...decorators.dashboard_permissions import (
    require_dashboard_permission,
    get_user_dashboard_permissions
)
from ...services.dashboard_permission_service import DashboardPermissionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/widget-management", tags=["组件管理"])

# Pydantic模型定义

class WidgetDefinitionResponse(BaseModel):
    """组件定义响应模型"""
    id: int
    widget_type: str
    widget_name: str
    description: Optional[str] = None
    category: str
    default_config: Optional[Dict[str, Any]] = None
    data_source_config: Optional[Dict[str, Any]] = None
    supported_roles: Optional[List[str]] = None
    min_width: int
    min_height: int
    max_width: int
    max_height: int
    is_resizable: bool
    is_movable: bool
    requires_data: bool
    refresh_interval: int
    is_active: bool
    version: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class CreateWidgetRequest(BaseModel):
    """创建组件请求模型"""
    widget_type: str = Field(..., min_length=1, max_length=50, description="组件类型标识")
    widget_name: str = Field(..., min_length=1, max_length=100, description="组件显示名称")
    description: Optional[str] = Field(None, max_length=500, description="组件描述")
    category: str = Field(..., description="组件分类")
    default_config: Optional[Dict[str, Any]] = Field(None, description="默认配置")
    data_source_config: Optional[Dict[str, Any]] = Field(None, description="数据源配置")
    supported_roles: Optional[List[str]] = Field(None, description="支持的角色列表")
    min_width: int = Field(2, ge=1, le=12, description="最小宽度")
    min_height: int = Field(2, ge=1, le=12, description="最小高度")
    max_width: int = Field(12, ge=1, le=12, description="最大宽度")
    max_height: int = Field(12, ge=1, le=12, description="最大高度")
    is_resizable: bool = Field(True, description="是否可调整大小")
    is_movable: bool = Field(True, description="是否可移动")
    requires_data: bool = Field(True, description="是否需要数据源")
    refresh_interval: int = Field(30, ge=5, le=3600, description="默认刷新间隔(秒)")
    version: str = Field("1.0.0", description="组件版本")

    @validator('category')
    def validate_category(cls, v):
        """验证组件分类"""
        try:
            WidgetCategory(v)
        except ValueError:
            raise ValueError(f"Invalid widget category: {v}")
        return v

    @validator('supported_roles')
    def validate_supported_roles(cls, v):
        """验证支持的角色"""
        if v is not None:
            for role in v:
                try:
                    RoleType(role)
                except ValueError:
                    raise ValueError(f"Invalid role type: {role}")
        return v

    @validator('max_width')
    def validate_width_range(cls, v, values):
        """验证宽度范围"""
        if 'min_width' in values and v < values['min_width']:
            raise ValueError("max_width must be greater than or equal to min_width")
        return v

    @validator('max_height')
    def validate_height_range(cls, v, values):
        """验证高度范围"""
        if 'min_height' in values and v < values['min_height']:
            raise ValueError("max_height must be greater than or equal to min_height")
        return v

class UpdateWidgetRequest(BaseModel):
    """更新组件请求模型"""
    widget_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_config: Optional[Dict[str, Any]] = None
    data_source_config: Optional[Dict[str, Any]] = None
    supported_roles: Optional[List[str]] = None
    min_width: Optional[int] = Field(None, ge=1, le=12)
    min_height: Optional[int] = Field(None, ge=1, le=12)
    max_width: Optional[int] = Field(None, ge=1, le=12)
    max_height: Optional[int] = Field(None, ge=1, le=12)
    is_resizable: Optional[bool] = None
    is_movable: Optional[bool] = None
    requires_data: Optional[bool] = None
    refresh_interval: Optional[int] = Field(None, ge=5, le=3600)
    is_active: Optional[bool] = None
    version: Optional[str] = None

    @validator('supported_roles')
    def validate_supported_roles(cls, v):
        """验证支持的角色"""
        if v is not None:
            for role in v:
                try:
                    RoleType(role)
                except ValueError:
                    raise ValueError(f"Invalid role type: {role}")
        return v

class ValidateWidgetConfigRequest(BaseModel):
    """验证组件配置请求模型"""
    widget_type: str = Field(..., description="组件类型")
    instance_config: Dict[str, Any] = Field(..., description="实例配置")

class WidgetConfigValidationResponse(BaseModel):
    """组件配置验证响应模型"""
    valid: bool
    errors: List[str]
    config: Optional[Dict[str, Any]] = None

class DataSourceInfoResponse(BaseModel):
    """数据源信息响应模型"""
    widget_type: str
    requires_data: bool
    refresh_interval: int
    data_source_type: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    cache_ttl: Optional[int] = None

# 依赖注入

def get_widget_service(db: Session = Depends(get_db)) -> WidgetService:
    """获取组件服务实例"""
    return WidgetService(db)

# API端点

@router.get("/", response_model=List[WidgetDefinitionResponse])
@require_dashboard_permission(DashboardPermissionType.WIDGET_VIEW)
async def get_available_widgets(
    role_type: Optional[str] = Query(None, description="角色类型过滤"),
    category: Optional[str] = Query(None, description="分类过滤"),
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    获取可用组件列表
    
    - **role_type**: 角色类型过滤 (可选)
    - **category**: 分类过滤 (可选)
    """
    try:
        if role_type:
            widgets = await service.get_available_widgets(current_user.id, role_type)
        elif category:
            widgets = await service.get_widgets_by_category(category, role_type)
        else:
            # 获取用户的默认角色或所有可用组件
            widgets = await service.get_available_widgets(current_user.id, "ADMIN")  # 默认使用ADMIN角色
        
        return [
            WidgetDefinitionResponse(
                id=widget.id,
                widget_type=widget.widget_type,
                widget_name=widget.widget_name,
                description=widget.description,
                category=widget.category.value,
                default_config=widget.default_config,
                data_source_config=widget.data_source_config,
                supported_roles=widget.supported_roles,
                min_width=widget.min_width,
                min_height=widget.min_height,
                max_width=widget.max_width,
                max_height=widget.max_height,
                is_resizable=widget.is_resizable,
                is_movable=widget.is_movable,
                requires_data=widget.requires_data,
                refresh_interval=widget.refresh_interval,
                is_active=widget.is_active,
                version=widget.version,
                created_at=widget.created_at.isoformat() if widget.created_at else "",
                updated_at=widget.updated_at.isoformat() if widget.updated_at else ""
            )
            for widget in widgets
        ]
        
    except Exception as e:
        logger.error(f"Error getting available widgets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取可用组件失败"
        )

@router.get("/{widget_type}", response_model=WidgetDefinitionResponse)
async def get_widget_definition(
    widget_type: str,
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    获取组件定义详情
    
    - **widget_type**: 组件类型
    """
    try:
        widget = await service.get_widget_by_type(widget_type)
        
        if not widget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Widget type '{widget_type}' not found"
            )
        
        return WidgetDefinitionResponse(
            id=widget.id,
            widget_type=widget.widget_type,
            widget_name=widget.widget_name,
            description=widget.description,
            category=widget.category.value,
            default_config=widget.default_config,
            data_source_config=widget.data_source_config,
            supported_roles=widget.supported_roles,
            min_width=widget.min_width,
            min_height=widget.min_height,
            max_width=widget.max_width,
            max_height=widget.max_height,
            is_resizable=widget.is_resizable,
            is_movable=widget.is_movable,
            requires_data=widget.requires_data,
            refresh_interval=widget.refresh_interval,
            is_active=widget.is_active,
            version=widget.version,
            created_at=widget.created_at.isoformat() if widget.created_at else "",
            updated_at=widget.updated_at.isoformat() if widget.updated_at else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting widget definition for {widget_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取组件定义失败"
        )

@router.post("/", response_model=WidgetDefinitionResponse)
@require_dashboard_permission(DashboardPermissionType.WIDGET_CREATE)
async def create_widget_definition(
    request: CreateWidgetRequest,
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    创建组件定义
    
    - **widget_type**: 组件类型标识 (唯一)
    - **widget_name**: 组件显示名称
    - **category**: 组件分类
    - **description**: 组件描述 (可选)
    - **default_config**: 默认配置 (可选)
    - **data_source_config**: 数据源配置 (可选)
    - **supported_roles**: 支持的角色列表 (可选)
    """
    try:
        widget_data = request.dict()
        widget = await service.register_widget(widget_data)
        
        return WidgetDefinitionResponse(
            id=widget.id,
            widget_type=widget.widget_type,
            widget_name=widget.widget_name,
            description=widget.description,
            category=widget.category.value,
            default_config=widget.default_config,
            data_source_config=widget.data_source_config,
            supported_roles=widget.supported_roles,
            min_width=widget.min_width,
            min_height=widget.min_height,
            max_width=widget.max_width,
            max_height=widget.max_height,
            is_resizable=widget.is_resizable,
            is_movable=widget.is_movable,
            requires_data=widget.requires_data,
            refresh_interval=widget.refresh_interval,
            is_active=widget.is_active,
            version=widget.version,
            created_at=widget.created_at.isoformat() if widget.created_at else "",
            updated_at=widget.updated_at.isoformat() if widget.updated_at else ""
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating widget definition: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建组件定义失败"
        )

@router.put("/{widget_type}", response_model=WidgetDefinitionResponse)
@require_dashboard_permission(DashboardPermissionType.WIDGET_MODIFY)
async def update_widget_definition(
    widget_type: str,
    request: UpdateWidgetRequest,
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    更新组件定义
    
    - **widget_type**: 组件类型
    - 其他字段为可选更新字段
    """
    try:
        # 过滤掉None值
        config_updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not config_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        widget = await service.update_widget_config(widget_type, config_updates)
        
        return WidgetDefinitionResponse(
            id=widget.id,
            widget_type=widget.widget_type,
            widget_name=widget.widget_name,
            description=widget.description,
            category=widget.category.value,
            default_config=widget.default_config,
            data_source_config=widget.data_source_config,
            supported_roles=widget.supported_roles,
            min_width=widget.min_width,
            min_height=widget.min_height,
            max_width=widget.max_width,
            max_height=widget.max_height,
            is_resizable=widget.is_resizable,
            is_movable=widget.is_movable,
            requires_data=widget.requires_data,
            refresh_interval=widget.refresh_interval,
            is_active=widget.is_active,
            version=widget.version,
            created_at=widget.created_at.isoformat() if widget.created_at else "",
            updated_at=widget.updated_at.isoformat() if widget.updated_at else ""
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating widget definition {widget_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新组件定义失败"
        )

@router.delete("/{widget_type}")
@require_dashboard_permission(DashboardPermissionType.WIDGET_DELETE)
async def delete_widget_definition(
    widget_type: str,
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    删除组件定义 (软删除，设置为非激活状态)
    
    - **widget_type**: 组件类型
    """
    try:
        # 软删除：设置为非激活状态
        config_updates = {"is_active": False}
        widget = await service.update_widget_config(widget_type, config_updates)
        
        return {
            "message": f"Widget '{widget_type}' has been deactivated",
            "widget_type": widget_type,
            "deactivated_at": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting widget definition {widget_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除组件定义失败"
        )

@router.get("/categories/{category}", response_model=List[WidgetDefinitionResponse])
async def get_widgets_by_category(
    category: str,
    role_type: Optional[str] = Query(None, description="角色类型过滤"),
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    根据分类获取组件列表
    
    - **category**: 组件分类
    - **role_type**: 角色类型过滤 (可选)
    """
    try:
        widgets = await service.get_widgets_by_category(category, role_type)
        
        return [
            WidgetDefinitionResponse(
                id=widget.id,
                widget_type=widget.widget_type,
                widget_name=widget.widget_name,
                description=widget.description,
                category=widget.category.value,
                default_config=widget.default_config,
                data_source_config=widget.data_source_config,
                supported_roles=widget.supported_roles,
                min_width=widget.min_width,
                min_height=widget.min_height,
                max_width=widget.max_width,
                max_height=widget.max_height,
                is_resizable=widget.is_resizable,
                is_movable=widget.is_movable,
                requires_data=widget.requires_data,
                refresh_interval=widget.refresh_interval,
                is_active=widget.is_active,
                version=widget.version,
                created_at=widget.created_at.isoformat() if widget.created_at else "",
                updated_at=widget.updated_at.isoformat() if widget.updated_at else ""
            )
            for widget in widgets
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting widgets by category {category}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取分类组件失败"
        )

@router.post("/validate-config", response_model=WidgetConfigValidationResponse)
async def validate_widget_config(
    request: ValidateWidgetConfigRequest,
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    验证组件实例配置
    
    - **widget_type**: 组件类型
    - **instance_config**: 实例配置
    """
    try:
        validation_result = await service.validate_widget_instance_config(
            request.widget_type, 
            request.instance_config
        )
        
        return WidgetConfigValidationResponse(
            valid=validation_result['valid'],
            errors=validation_result['errors'],
            config=validation_result['config']
        )
        
    except Exception as e:
        logger.error(f"Error validating widget config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证组件配置失败"
        )

@router.get("/{widget_type}/data-source", response_model=DataSourceInfoResponse)
async def get_widget_data_source_info(
    widget_type: str,
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    获取组件数据源信息
    
    - **widget_type**: 组件类型
    """
    try:
        data_source_info = await service.get_widget_data_source_info(widget_type)
        
        if not data_source_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data source info not found for widget type '{widget_type}'"
            )
        
        return DataSourceInfoResponse(
            widget_type=data_source_info['widget_type'],
            requires_data=data_source_info['requires_data'],
            refresh_interval=data_source_info['refresh_interval'],
            data_source_type=data_source_info.get('type'),
            endpoint=data_source_info.get('endpoint'),
            method=data_source_info.get('method'),
            parameters=data_source_info.get('params'),
            cache_ttl=data_source_info.get('cache_ttl')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting data source info for {widget_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据源信息失败"
        )

@router.post("/initialize-builtin")
@require_dashboard_permission(DashboardPermissionType.WIDGET_CREATE)
async def initialize_builtin_widgets(
    current_user: User = Depends(get_current_user),
    service: WidgetService = Depends(get_widget_service)
):
    """
    初始化内置组件定义 (仅管理员)
    """
    try:
        # 检查管理员权限
        if not hasattr(current_user, 'role') or current_user.role != 'ADMIN':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅管理员可以初始化内置组件"
            )
        
        created_widgets = await service.initialize_builtin_widgets()
        
        return {
            "message": f"Successfully initialized {len(created_widgets)} builtin widgets",
            "created_widgets": [widget.widget_type for widget in created_widgets],
            "total_count": len(created_widgets),
            "initialized_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing builtin widgets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="初始化内置组件失败"
        )

@router.get("/categories")
async def get_widget_categories():
    """获取所有组件分类"""
    try:
        categories = [
            {
                "value": category.value,
                "name": category.name,
                "description": _get_category_description(category)
            }
            for category in WidgetCategory
        ]
        
        return {
            "categories": categories,
            "total_count": len(categories)
        }
        
    except Exception as e:
        logger.error(f"Error getting widget categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取组件分类失败"
        )

@router.get("/data-source-types")
async def get_data_source_types():
    """获取所有数据源类型"""
    try:
        data_source_types = [
            {
                "value": ds_type.value,
                "name": ds_type.name,
                "description": _get_data_source_description(ds_type)
            }
            for ds_type in DataSourceType
        ]
        
        return {
            "data_source_types": data_source_types,
            "total_count": len(data_source_types)
        }
        
    except Exception as e:
        logger.error(f"Error getting data source types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取数据源类型失败"
        )

# 辅助函数

def _get_category_description(category: WidgetCategory) -> str:
    """获取分类描述"""
    descriptions = {
        WidgetCategory.STATISTICS: "统计类组件，用于显示数值统计信息",
        WidgetCategory.CHARTS: "图表类组件，用于数据可视化展示",
        WidgetCategory.PROGRESS: "进度类组件，用于显示任务或项目进度",
        WidgetCategory.STATUS: "状态类组件，用于显示系统或服务状态",
        WidgetCategory.RANKING: "排行类组件，用于显示排序数据",
        WidgetCategory.CALENDAR: "日历类组件，用于显示时间相关信息",
        WidgetCategory.MAP: "地图类组件，用于显示地理位置数据",
        WidgetCategory.TABLE: "表格类组件，用于显示结构化数据",
        WidgetCategory.CUSTOM: "自定义组件，用于特殊需求"
    }
    return descriptions.get(category, "未知分类")

def _get_data_source_description(ds_type: DataSourceType) -> str:
    """获取数据源类型描述"""
    descriptions = {
        DataSourceType.API: "REST API数据源，通过HTTP请求获取数据",
        DataSourceType.DATABASE: "数据库数据源，直接查询数据库获取数据",
        DataSourceType.WEBSOCKET: "WebSocket数据源，实时推送数据",
        DataSourceType.CACHE: "缓存数据源，从缓存中获取数据",
        DataSourceType.STATIC: "静态数据源，使用预定义的静态数据"
    }
    return descriptions.get(ds_type, "未知数据源类型")