"""
仪表板数据获取API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta

from ....core.security import get_current_user
from ....services.data_aggregation_service import DataAggregationService, get_data_aggregation_service
from ....models.dashboard import RoleType

router = APIRouter()

class DataRequest(BaseModel):
    """数据请求模型"""
    widget_type: str
    project_ids: Optional[List[int]] = None
    time_range: Optional[str] = "7d"  # 7d, 30d, 90d, 1y
    filters: Optional[Dict[str, Any]] = None

class MetricsResponse(BaseModel):
    """指标响应模型"""
    metric_type: str
    data: Dict[str, Any]
    timestamp: datetime
    cache_hit: bool = False

@router.get("/overview")
async def get_overview_data(
    role_type: str = Query(..., description="角色类型"),
    project_ids: Optional[List[int]] = Query(None, description="项目ID列表"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """获取概览数据"""
    try:
        # 验证角色类型
        if role_type.upper() not in [role.value for role in RoleType]:
            raise HTTPException(status_code=400, detail="无效的角色类型")
        
        data = await data_service.get_project_overview_data(
            user_id=current_user["id"],
            role_type=role_type.upper(),
            project_ids=project_ids
        )
        
        return {
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user["id"],
            "role_type": role_type.upper()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概览数据失败: {str(e)}")

@router.get("/metrics/{metric_type}", response_model=MetricsResponse)
async def get_metrics_data(
    metric_type: str,
    project_ids: Optional[List[int]] = Query(None, description="项目ID列表"),
    time_range: Optional[str] = Query("7d", description="时间范围"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """获取指标数据"""
    try:
        # 支持的指标类型
        supported_metrics = [
            "projects", "requirements", "tests", "development", 
            "operations", "quality", "performance", "risks"
        ]
        
        if metric_type not in supported_metrics:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的指标类型。支持的类型: {', '.join(supported_metrics)}"
            )
        
        # 根据指标类型获取数据
        if metric_type == "projects":
            data = await data_service.get_project_metrics(project_ids or [])
        elif metric_type == "requirements":
            data = await data_service.get_requirement_metrics(project_ids or [])
        elif metric_type == "tests":
            data = await data_service.get_test_metrics(project_ids or [])
        elif metric_type == "development":
            data = await data_service.get_development_metrics(project_ids or [])
        elif metric_type == "operations":
            data = await data_service.get_operations_metrics(project_ids or [])
        elif metric_type == "quality":
            data = await data_service.get_quality_metrics(project_ids or [])
        elif metric_type == "performance":
            data = await data_service.get_performance_metrics(project_ids or [])
        elif metric_type == "risks":
            data = await data_service.get_risk_metrics(project_ids or [])
        else:
            raise HTTPException(status_code=400, detail="未实现的指标类型")
        
        return MetricsResponse(
            metric_type=metric_type,
            data=data,
            timestamp=datetime.utcnow()
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取指标数据失败: {str(e)}")

@router.post("/widget-data")
async def get_widget_data(
    request: DataRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """获取组件数据"""
    try:
        data = await data_service.get_widget_data(
            widget_type=request.widget_type,
            user_id=current_user["id"],
            project_ids=request.project_ids,
            time_range=request.time_range,
            filters=request.filters
        )
        
        return {
            "widget_type": request.widget_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_info": data.get("_cache_info", {})
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取组件数据失败: {str(e)}")

@router.get("/real-time/{data_type}")
async def get_real_time_data(
    data_type: str,
    project_ids: Optional[List[int]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """获取实时数据"""
    try:
        # 支持的实时数据类型
        supported_types = [
            "system_status", "active_users", "current_builds", 
            "test_executions", "alerts", "performance"
        ]
        
        if data_type not in supported_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的实时数据类型。支持的类型: {', '.join(supported_types)}"
            )
        
        data = await data_service.get_real_time_data(
            data_type=data_type,
            user_id=current_user["id"],
            project_ids=project_ids
        )
        
        return {
            "data_type": data_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "is_real_time": True
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时数据失败: {str(e)}")

@router.get("/trends/{trend_type}")
async def get_trend_data(
    trend_type: str,
    time_range: str = Query("30d", description="时间范围"),
    project_ids: Optional[List[int]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """获取趋势数据"""
    try:
        # 支持的趋势类型
        supported_trends = [
            "project_progress", "requirement_completion", "test_pass_rate",
            "defect_density", "team_velocity", "code_quality"
        ]
        
        if trend_type not in supported_trends:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的趋势类型。支持的类型: {', '.join(supported_trends)}"
            )
        
        # 解析时间范围
        time_delta = _parse_time_range(time_range)
        start_date = datetime.utcnow() - time_delta
        
        data = await data_service.get_trend_data(
            trend_type=trend_type,
            start_date=start_date,
            end_date=datetime.utcnow(),
            project_ids=project_ids,
            user_id=current_user["id"]
        )
        
        return {
            "trend_type": trend_type,
            "time_range": time_range,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取趋势数据失败: {str(e)}")

@router.get("/statistics/summary")
async def get_statistics_summary(
    role_type: str = Query(...),
    project_ids: Optional[List[int]] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """获取统计摘要"""
    try:
        # 验证角色类型
        if role_type.upper() not in [role.value for role in RoleType]:
            raise HTTPException(status_code=400, detail="无效的角色类型")
        
        summary = await data_service.get_statistics_summary(
            user_id=current_user["id"],
            role_type=role_type.upper(),
            project_ids=project_ids
        )
        
        return {
            "role_type": role_type.upper(),
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat(),
            "generated_for": current_user["id"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计摘要失败: {str(e)}")

@router.post("/refresh-cache")
async def refresh_data_cache(
    data_types: List[str],
    project_ids: Optional[List[int]] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    data_service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """刷新数据缓存"""
    try:
        result = await data_service.refresh_cache(
            data_types=data_types,
            user_id=current_user["id"],
            project_ids=project_ids
        )
        
        return {
            "message": "缓存刷新完成",
            "refreshed_types": data_types,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新缓存失败: {str(e)}")

def _parse_time_range(time_range: str) -> timedelta:
    """解析时间范围字符串"""
    time_map = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }
    
    if time_range not in time_map:
        raise ValueError(f"不支持的时间范围: {time_range}")
    
    return time_map[time_range]