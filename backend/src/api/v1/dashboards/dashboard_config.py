"""
仪表板配置管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from ....core.security import get_current_user
from ....services.dashboard_service import DashboardService, get_dashboard_service
from ....models.dashboard import RoleType

router = APIRouter()

class DashboardConfigResponse(BaseModel):
    """仪表板配置响应模型"""
    id: int
    user_id: int
    role_type: str
    dashboard_name: str
    is_default: bool
    layout_config: Optional[Dict[str, Any]]
    widget_configs: Optional[List[Dict[str, Any]]]
    theme_config: Optional[Dict[str, Any]]
    refresh_interval: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class SaveLayoutRequest(BaseModel):
    """保存布局请求模型"""
    layout_config: Dict[str, Any]
    widget_configs: List[Dict[str, Any]]
    refresh_interval: Optional[int] = 30
    theme_config: Optional[Dict[str, Any]] = None

class CreateDashboardRequest(BaseModel):
    """创建仪表板请求模型"""
    dashboard_name: str
    role_type: str
    layout_config: Optional[Dict[str, Any]] = None
    widget_configs: Optional[List[Dict[str, Any]]] = None
    theme_config: Optional[Dict[str, Any]] = None
    refresh_interval: int = 30

@router.get("/list", response_model=List[DashboardConfigResponse])
async def get_user_dashboards(
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """获取用户所有仪表板配置"""
    try:
        configs = await dashboard_service.get_user_dashboards(current_user["id"])
        return [DashboardConfigResponse.model_validate(config.__dict__) for config in configs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表板配置失败: {str(e)}")

@router.get("/{role_type}", response_model=DashboardConfigResponse)
async def get_dashboard_config(
    role_type: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """获取角色仪表板配置"""
    try:
        # 验证角色类型
        if role_type.upper() not in [role.value for role in RoleType]:
            raise HTTPException(status_code=400, detail="无效的角色类型")
        
        config = await dashboard_service.get_role_dashboard(current_user["id"], role_type.upper())
        return DashboardConfigResponse.model_validate(config.__dict__)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表板配置失败: {str(e)}")

@router.post("/{role_type}/layout")
async def save_dashboard_layout(
    role_type: str,
    request: SaveLayoutRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """保存仪表板布局"""
    try:
        # 验证角色类型
        if role_type.upper() not in [role.value for role in RoleType]:
            raise HTTPException(status_code=400, detail="无效的角色类型")
        
        config = await dashboard_service.save_dashboard_layout(
            user_id=current_user["id"],
            role_type=role_type.upper(),
            layout_config=request.layout_config,
            widget_configs=request.widget_configs,
            theme_config=request.theme_config,
            refresh_interval=request.refresh_interval
        )
        
        return {
            "message": "布局保存成功",
            "config_id": config.id,
            "updated_at": config.updated_at.isoformat()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存布局失败: {str(e)}")

@router.post("/{role_type}/reset")
async def reset_dashboard_layout(
    role_type: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """重置仪表板布局"""
    try:
        # 验证角色类型
        if role_type.upper() not in [role.value for role in RoleType]:
            raise HTTPException(status_code=400, detail="无效的角色类型")
        
        await dashboard_service.reset_to_default(current_user["id"], role_type.upper())
        
        return {
            "message": "布局重置成功",
            "reset_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置布局失败: {str(e)}")

@router.post("/create", response_model=DashboardConfigResponse)
async def create_dashboard(
    request: CreateDashboardRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """创建新的仪表板配置"""
    try:
        # 验证角色类型
        if request.role_type.upper() not in [role.value for role in RoleType]:
            raise HTTPException(status_code=400, detail="无效的角色类型")
        
        config = await dashboard_service.create_dashboard(
            user_id=current_user["id"],
            dashboard_name=request.dashboard_name,
            role_type=request.role_type.upper(),
            layout_config=request.layout_config,
            widget_configs=request.widget_configs,
            theme_config=request.theme_config,
            refresh_interval=request.refresh_interval
        )
        
        return DashboardConfigResponse.model_validate(config.__dict__)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建仪表板失败: {str(e)}")

@router.delete("/{config_id}")
async def delete_dashboard(
    config_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """删除仪表板配置"""
    try:
        await dashboard_service.delete_dashboard(config_id, current_user["id"])
        
        return {
            "message": "仪表板删除成功",
            "deleted_at": datetime.utcnow().isoformat()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除仪表板失败: {str(e)}")

@router.get("/{config_id}/export")
async def export_dashboard_config(
    config_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """导出仪表板配置"""
    try:
        config_data = await dashboard_service.export_dashboard_config(config_id, current_user["id"])
        
        return {
            "message": "配置导出成功",
            "config_data": config_data,
            "exported_at": datetime.utcnow().isoformat()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出配置失败: {str(e)}")

@router.post("/import")
async def import_dashboard_config(
    config_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """导入仪表板配置"""
    try:
        config = await dashboard_service.import_dashboard_config(config_data, current_user["id"])
        
        return {
            "message": "配置导入成功",
            "config_id": config.id,
            "imported_at": datetime.utcnow().isoformat()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入配置失败: {str(e)}")