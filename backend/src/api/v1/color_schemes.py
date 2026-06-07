"""
配色方案管理API

提供配色方案的CRUD操作、预览、应用和分享功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging

from ...core.database import get_db
from ...services.color_scheme_service import ColorSchemeService
from ...services.auth import get_current_user
from ...models.user import User
from ...models.color_scheme import ColorScheme, UserColorPreference, SchemeType, SchemeCategory
from ...decorators.dashboard_permissions import (
    require_color_scheme_permission,
    require_dashboard_permission,
    get_user_dashboard_permissions
)
from ...services.dashboard_permission_service import DashboardPermissionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/color-schemes", tags=["配色方案管理"])

# Pydantic模型定义

class ColorSchemeResponse(BaseModel):
    """配色方案响应模型"""
    id: int
    scheme_name: str
    scheme_type: str
    scheme_category: Optional[str] = None
    color_palette: List[str]
    description: Optional[str] = None
    preview_image: Optional[str] = None
    is_default: bool
    is_public: bool
    usage_count: int
    rating: float
    created_by: Optional[int] = None
    organization_id: Optional[int] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class CreateColorSchemeRequest(BaseModel):
    """创建配色方案请求模型"""
    scheme_name: str = Field(..., min_length=1, max_length=100, description="方案名称")
    scheme_category: Optional[str] = Field(None, description="方案分类")
    color_palette: List[str] = Field(..., min_items=2, max_items=16, description="颜色数组")
    description: Optional[str] = Field(None, max_length=500, description="方案描述")
    is_public: bool = Field(False, description="是否公开")

    @validator('color_palette')
    def validate_colors(cls, v):
        """验证颜色格式"""
        for color in v:
            if not ColorScheme.validate_color_format(color):
                raise ValueError(f"Invalid color format: {color}")
        return v

    @validator('scheme_category')
    def validate_category(cls, v):
        """验证分类"""
        if v is not None:
            try:
                SchemeCategory(v)
            except ValueError:
                raise ValueError(f"Invalid scheme category: {v}")
        return v

class UpdateColorSchemeRequest(BaseModel):
    """更新配色方案请求模型"""
    scheme_name: Optional[str] = Field(None, min_length=1, max_length=100)
    scheme_category: Optional[str] = None
    color_palette: Optional[List[str]] = Field(None, min_items=2, max_items=16)
    description: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None

    @validator('color_palette')
    def validate_colors(cls, v):
        """验证颜色格式"""
        if v is not None:
            for color in v:
                if not ColorScheme.validate_color_format(color):
                    raise ValueError(f"Invalid color format: {color}")
        return v

class ApplySchemeRequest(BaseModel):
    """应用配色方案请求模型"""
    apply_to_charts: bool = Field(True, description="是否应用到图表")
    apply_to_widgets: bool = Field(True, description="是否应用到组件")
    apply_to_theme: bool = Field(False, description="是否应用到整体主题")

class PreviewSchemeRequest(BaseModel):
    """预览配色方案请求模型"""
    color_palette: List[str] = Field(..., min_items=2, max_items=16, description="颜色数组")

    @validator('color_palette')
    def validate_colors(cls, v):
        """验证颜色格式"""
        for color in v:
            if not ColorScheme.validate_color_format(color):
                raise ValueError(f"Invalid color format: {color}")
        return v

class RateSchemeRequest(BaseModel):
    """评价配色方案请求模型"""
    rating: float = Field(..., ge=0, le=5, description="评分 (0-5)")

class UserColorPreferenceResponse(BaseModel):
    """用户配色偏好响应模型"""
    id: int
    user_id: int
    color_scheme_id: Optional[int] = None
    custom_colors: Optional[List[str]] = None
    auto_switch_dark_mode: bool
    accessibility_mode: bool
    high_contrast: bool
    apply_to_charts: bool
    apply_to_widgets: bool
    apply_to_theme: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# 依赖注入

def get_color_scheme_service(db: Session = Depends(get_db)) -> ColorSchemeService:
    """获取配色方案服务实例"""
    return ColorSchemeService(db)

# API端点

@router.get("/", response_model=List[ColorSchemeResponse])
@require_dashboard_permission(DashboardPermissionType.COLOR_SCHEME_VIEW)
async def get_color_schemes(
    scheme_type: Optional[str] = Query(None, description="方案类型过滤"),
    category: Optional[str] = Query(None, description="分类过滤"),
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service),
    db: Session = Depends(get_db)
):
    """
    获取配色方案列表
    
    - **scheme_type**: 方案类型 (SYSTEM, ENTERPRISE, USER_CUSTOM)
    - **category**: 方案分类 (BUSINESS, TECHNOLOGY, FRESH, etc.)
    """
    try:
        schemes = await service.get_available_schemes(
            current_user.id, scheme_type, category
        )
        
        return [
            ColorSchemeResponse(
                id=scheme.id,
                scheme_name=scheme.scheme_name,
                scheme_type=scheme.scheme_type.value,
                scheme_category=scheme.scheme_category.value if scheme.scheme_category else None,
                color_palette=scheme.color_palette,
                description=scheme.description,
                preview_image=scheme.preview_image,
                is_default=scheme.is_default,
                is_public=scheme.is_public,
                usage_count=scheme.usage_count,
                rating=float(scheme.rating) if scheme.rating else 0.0,
                created_by=scheme.created_by,
                organization_id=scheme.organization_id,
                created_at=scheme.created_at.isoformat() if scheme.created_at else "",
                updated_at=scheme.updated_at.isoformat() if scheme.updated_at else ""
            )
            for scheme in schemes
        ]
        
    except Exception as e:
        logger.error(f"Error getting color schemes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取配色方案失败"
        )

@router.post("/", response_model=ColorSchemeResponse)
@require_color_scheme_permission("create")
async def create_color_scheme(
    request: CreateColorSchemeRequest,
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service),
    db: Session = Depends(get_db)
):
    """
    创建自定义配色方案
    
    - **scheme_name**: 方案名称
    - **color_palette**: 颜色数组 (2-16个颜色)
    - **scheme_category**: 方案分类 (可选)
    - **description**: 方案描述 (可选)
    - **is_public**: 是否公开 (默认false)
    """
    try:
        scheme = await service.create_custom_scheme(
            user_id=current_user.id,
            scheme_name=request.scheme_name,
            color_palette=request.color_palette,
            scheme_category=request.scheme_category,
            description=request.description,
            is_public=request.is_public
        )
        
        return ColorSchemeResponse(
            id=scheme.id,
            scheme_name=scheme.scheme_name,
            scheme_type=scheme.scheme_type.value,
            scheme_category=scheme.scheme_category.value if scheme.scheme_category else None,
            color_palette=scheme.color_palette,
            description=scheme.description,
            preview_image=scheme.preview_image,
            is_default=scheme.is_default,
            is_public=scheme.is_public,
            usage_count=scheme.usage_count,
            rating=float(scheme.rating) if scheme.rating else 0.0,
            created_by=scheme.created_by,
            organization_id=scheme.organization_id,
            created_at=scheme.created_at.isoformat() if scheme.created_at else "",
            updated_at=scheme.updated_at.isoformat() if scheme.updated_at else ""
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating color scheme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建配色方案失败"
        )

@router.get("/{scheme_id}", response_model=ColorSchemeResponse)
async def get_color_scheme(
    scheme_id: int,
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """获取指定配色方案详情"""
    try:
        # 获取所有可用方案并查找指定ID
        schemes = await service.get_available_schemes(current_user.id)
        scheme = next((s for s in schemes if s.id == scheme_id), None)
        
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="配色方案不存在或无权限访问"
            )
        
        return ColorSchemeResponse(
            id=scheme.id,
            scheme_name=scheme.scheme_name,
            scheme_type=scheme.scheme_type.value,
            scheme_category=scheme.scheme_category.value if scheme.scheme_category else None,
            color_palette=scheme.color_palette,
            description=scheme.description,
            preview_image=scheme.preview_image,
            is_default=scheme.is_default,
            is_public=scheme.is_public,
            usage_count=scheme.usage_count,
            rating=float(scheme.rating) if scheme.rating else 0.0,
            created_by=scheme.created_by,
            organization_id=scheme.organization_id,
            created_at=scheme.created_at.isoformat() if scheme.created_at else "",
            updated_at=scheme.updated_at.isoformat() if scheme.updated_at else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting color scheme {scheme_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取配色方案失败"
        )

@router.post("/{scheme_id}/apply")
async def apply_color_scheme(
    scheme_id: int,
    request: ApplySchemeRequest,
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """
    应用配色方案到用户
    
    - **apply_to_charts**: 是否应用到图表
    - **apply_to_widgets**: 是否应用到组件
    - **apply_to_theme**: 是否应用到整体主题
    """
    try:
        preference = await service.apply_scheme_to_user(
            user_id=current_user.id,
            scheme_id=scheme_id,
            apply_to_charts=request.apply_to_charts,
            apply_to_widgets=request.apply_to_widgets,
            apply_to_theme=request.apply_to_theme
        )
        
        return {
            "message": "配色方案应用成功",
            "preference_id": preference.id
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error applying color scheme {scheme_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="应用配色方案失败"
        )

@router.post("/preview")
async def preview_color_scheme(
    request: PreviewSchemeRequest,
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """
    预览配色方案效果
    
    - **color_palette**: 颜色数组
    """
    try:
        preview_data = await service.preview_scheme(request.color_palette)
        
        return {
            "color_palette": preview_data["color_palette"],
            "preview_image": preview_data["preview_image"],
            "accessibility": preview_data["accessibility"],
            "analysis": preview_data["analysis"],
            "recommendations": preview_data["recommendations"]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error previewing color scheme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="预览配色方案失败"
        )

@router.post("/{scheme_id}/share")
async def share_color_scheme(
    scheme_id: int,
    make_public: bool = Query(True, description="是否设为公开"),
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """
    分享配色方案
    
    - **make_public**: 是否设为公开
    """
    try:
        success = await service.share_scheme(
            user_id=current_user.id,
            scheme_id=scheme_id,
            make_public=make_public
        )
        
        if success:
            return {
                "message": f"配色方案已{'公开' if make_public else '设为私有'}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="分享配色方案失败"
            )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error sharing color scheme {scheme_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="分享配色方案失败"
        )

@router.post("/{scheme_id}/rate")
async def rate_color_scheme(
    scheme_id: int,
    request: RateSchemeRequest,
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """
    评价配色方案
    
    - **rating**: 评分 (0-5)
    """
    try:
        success = await service.rate_scheme(
            user_id=current_user.id,
            scheme_id=scheme_id,
            rating=request.rating
        )
        
        if success:
            return {
                "message": "评价提交成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="评价提交失败"
            )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error rating color scheme {scheme_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="评价提交失败"
        )

@router.delete("/{scheme_id}")
async def delete_color_scheme(
    scheme_id: int,
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """删除自定义配色方案"""
    try:
        success = await service.delete_custom_scheme(
            user_id=current_user.id,
            scheme_id=scheme_id
        )
        
        if success:
            return {
                "message": "配色方案删除成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="删除配色方案失败"
            )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting color scheme {scheme_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除配色方案失败"
        )

@router.get("/user/preference", response_model=UserColorPreferenceResponse)
async def get_user_color_preference(
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """获取用户配色偏好"""
    try:
        preference = await service.get_user_preference(current_user.id)
        
        if not preference:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户配色偏好不存在"
            )
        
        return UserColorPreferenceResponse(
            id=preference.id,
            user_id=preference.user_id,
            color_scheme_id=preference.color_scheme_id,
            custom_colors=preference.custom_colors,
            auto_switch_dark_mode=preference.auto_switch_dark_mode,
            accessibility_mode=preference.accessibility_mode,
            high_contrast=preference.high_contrast,
            apply_to_charts=preference.apply_to_charts,
            apply_to_widgets=preference.apply_to_widgets,
            apply_to_theme=preference.apply_to_theme,
            created_at=preference.created_at.isoformat() if preference.created_at else "",
            updated_at=preference.updated_at.isoformat() if preference.updated_at else ""
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user color preference: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户配色偏好失败"
        )

@router.get("/user/effective-colors")
async def get_effective_colors(
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """获取用户的有效配色方案"""
    try:
        colors = await service.get_effective_colors(current_user.id)
        
        return {
            "colors": colors,
            "count": len(colors)
        }
        
    except Exception as e:
        logger.error(f"Error getting effective colors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取有效配色失败"
        )

@router.post("/initialize-system")
async def initialize_system_schemes(
    current_user: User = Depends(get_current_user),
    service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """初始化系统预设配色方案 (仅管理员)"""
    try:
        # 检查管理员权限
        if not hasattr(current_user, 'role') or current_user.role != 'ADMIN':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="仅管理员可以初始化系统配色方案"
            )
        
        success = await service.initialize_system_schemes()
        
        if success:
            return {
                "message": "系统配色方案初始化成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="系统配色方案初始化失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing system schemes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="初始化系统配色方案失败"
        )

@router.get("/permissions")
async def get_user_permissions(
    permissions: Dict[str, bool] = Depends(get_user_dashboard_permissions)
):
    """获取当前用户的仪表板权限"""
    return {
        "permissions": permissions,
        "timestamp": datetime.utcnow().isoformat()
    }