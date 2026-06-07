"""
组件管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ....core.security import get_current_user
from ....services.widget_service import WidgetService, get_widget_service

router = APIRouter()

class WidgetDefinitionResponse(BaseModel):
    """组件定义响应模型"""
    id: int
    widget_type: str
    widget_name: str
    description: Optional[str]
    category: str
    default_config: Optional[Dict[str, Any]]
    supported_roles: Optional[List[str]]
    min_width: int
    min_height: int
    max_width: int
    max_height: int
    is_active: bool

@router.get("/definitions", response_model=List[WidgetDefinitionResponse])
async def get_widget_definitions(
    category: Optional[str] = None,
    role_type: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """获取组件定义列表"""
    try:
        definitions = await widget_service.get_available_widgets(
            user_id=current_user["id"],
            category=category,
            role_type=role_type
        )
        
        return [WidgetDefinitionResponse.model_validate(d.__dict__) for d in definitions]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取组件定义失败: {str(e)}")

@router.get("/categories")
async def get_widget_categories(
    current_user: Dict[str, Any] = Depends(get_current_user),
    widget_service: WidgetService = Depends(get_widget_service)
):
    """获取组件分类列表"""
    try:
        categories = await widget_service.get_widget_categories()
        return {"categories": categories}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取组件分类失败: {str(e)}")