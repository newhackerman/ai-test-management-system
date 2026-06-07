"""
配色方案管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ....core.security import get_current_user
from ....services.color_scheme_service import ColorSchemeService, get_color_scheme_service

router = APIRouter()

class ColorSchemeResponse(BaseModel):
    """配色方案响应模型"""
    id: int
    scheme_name: str
    scheme_type: str
    scheme_category: Optional[str]
    color_palette: List[str]
    description: Optional[str]
    is_default: bool
    is_public: bool
    usage_count: int
    rating: float

@router.get("/", response_model=List[ColorSchemeResponse])
async def get_color_schemes(
    scheme_type: Optional[str] = None,
    category: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    color_service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """获取配色方案列表"""
    try:
        schemes = await color_service.get_available_schemes(
            current_user["id"], scheme_type, category
        )
        return [ColorSchemeResponse.model_validate(scheme.__dict__) for scheme in schemes]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配色方案失败: {str(e)}")

@router.post("/{scheme_id}/apply")
async def apply_color_scheme(
    scheme_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    color_service: ColorSchemeService = Depends(get_color_scheme_service)
):
    """应用配色方案"""
    try:
        await color_service.apply_scheme_to_user(scheme_id, current_user["id"])
        return {"message": "配色方案应用成功"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用配色方案失败: {str(e)}")