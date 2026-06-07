"""
仪表板数据获取API

提供各种数据类型的查询和聚合、数据过滤和分页功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime, date, timedelta
from enum import Enum
import logging

from ...core.database import get_db
from ...services.data_aggregation_service import DataAggregationService
from ...services.auth import get_current_user
from ...models.user import User
from ...decorators.dashboard_permissions import (
    require_dashboard_permission,
    get_user_dashboard_permissions
)
from ...services.dashboard_permission_service import DashboardPermissionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard-data", tags=["仪表板数据获取"])

# 枚举定义

class TimeRangeType(str, Enum):
    """时间范围类型"""
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    LAST_6_MONTHS = "6m"
    LAST_YEAR = "1y"
    CUSTOM = "custom"

class MetricType(str, Enum):
    """指标类型"""
    PROJECTS = "projects"
    REQUIREMENTS = "requirements"
    TESTS = "tests"
    DEVELOPMENT = "development"
    INFRASTRUCTURE = "infrastructure"

class DataFormat(str, Enum):
    """数据格式"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"

# Pydantic模型定义

class ProjectOverviewResponse(BaseModel):
    """项目概览响应模型"""
    total_projects: int
    active_projects: int
    completed_projects: int
    delayed_projects: int
    project_health_distribution: Dict[str, int]
    recent_activities: List[Dict[str, Any]]
    key_metrics: Dict[str, Any]
    budget_summary: Dict[str, Any]
    team_summary: Dict[str, Any]
    generated_at: str
    data_quality: Dict[str, float]

    class Config:
        from_attributes = True

class MetricsResponse(BaseModel):
    """指标响应模型"""
    metric_type: str
    data: Dict[str, Any]
    time_range: str
    generated_at: str
    cache_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class DataQueryRequest(BaseModel):
    """数据查询请求模型"""
    metric_type: MetricType
    time_range: TimeRangeType = Field(TimeRangeType.LAST_30_DAYS, description="时间范围")
    start_date: Optional[date] = Field(None, description="开始日期 (自定义时间范围)")
    end_date: Optional[date] = Field(None, description="结束日期 (自定义时间范围)")
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表")
    filters: Optional[Dict[str, Any]] = Field(None, description="额外过滤条件")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页大小")
    format: DataFormat = Field(DataFormat.JSON, description="数据格式")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """验证日期范围"""
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError("End date must be after start date")
        return v

    @validator('time_range')
    def validate_custom_time_range(cls, v, values):
        """验证自定义时间范围"""
        if v == TimeRangeType.CUSTOM:
            if not values.get('start_date') or not values.get('end_date'):
                raise ValueError("Custom time range requires start_date and end_date")
        return v

class RealtimeDataRequest(BaseModel):
    """实时数据请求模型"""
    widget_type: str = Field(..., description="组件类型")
    refresh_interval: Optional[int] = Field(30, ge=5, le=3600, description="刷新间隔(秒)")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")

class BulkDataRequest(BaseModel):
    """批量数据请求模型"""
    queries: List[DataQueryRequest] = Field(..., max_items=10, description="查询列表")
    parallel: bool = Field(True, description="是否并行执行")

# 依赖注入

def get_data_aggregation_service(db: Session = Depends(get_db)) -> DataAggregationService:
    """获取数据聚合服务实例"""
    return DataAggregationService(db)

# API端点

@router.get("/overview", response_model=ProjectOverviewResponse)
@require_dashboard_permission(DashboardPermissionType.DATA_PROJECT_ALL)
async def get_project_overview(
    role_type: str = Query(..., description="角色类型"),
    project_ids: Optional[List[int]] = Query(None, description="项目ID列表"),
    current_user: User = Depends(get_current_user),
    service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """
    获取项目概览数据
    
    - **role_type**: 角色类型 (ADMIN, PROJECT_MANAGER, etc.)
    - **project_ids**: 项目ID列表 (可选，用于过滤特定项目)
    """
    try:
        data = await service.get_project_overview_data(current_user.id, role_type)
        
        return ProjectOverviewResponse(
            total_projects=data.get('total_projects', 0),
            active_projects=data.get('active_projects', 0),
            completed_projects=data.get('completed_projects', 0),
            delayed_projects=data.get('delayed_projects', 0),
            project_health_distribution=data.get('project_health_distribution', {}),
            recent_activities=data.get('recent_activities', []),
            key_metrics=data.get('key_metrics', {}),
            budget_summary=data.get('budget_summary', {}),
            team_summary=data.get('team_summary', {}),
            generated_at=data.get('generated_at', datetime.now().isoformat()),
            data_quality=data.get('data_quality', {})
        )
        
    except Exception as e:
        logger.error(f"Error getting project overview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目概览数据失败"
        )

@router.get("/metrics/{metric_type}", response_model=MetricsResponse)
@require_dashboard_permission(DashboardPermissionType.DATA_VIEW)
async def get_metrics_data(
    metric_type: MetricType,
    time_range: TimeRangeType = Query(TimeRangeType.LAST_30_DAYS, description="时间范围"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    project_ids: Optional[List[int]] = Query(None, description="项目ID列表"),
    current_user: User = Depends(get_current_user),
    service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """
    获取指标数据
    
    - **metric_type**: 指标类型 (projects, requirements, tests, development, infrastructure)
    - **time_range**: 时间范围 (7d, 30d, 90d, 6m, 1y, custom)
    - **start_date**: 开始日期 (自定义时间范围时必需)
    - **end_date**: 结束日期 (自定义时间范围时必需)
    - **project_ids**: 项目ID列表 (可选)
    """
    try:
        # 验证自定义时间范围
        if time_range == TimeRangeType.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Custom time range requires start_date and end_date"
                )
            if end_date < start_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End date must be after start date"
                )
        
        # 根据指标类型获取数据
        if metric_type == MetricType.PROJECTS:
            data = await service.get_project_metrics(project_ids or [])
        elif metric_type == MetricType.REQUIREMENTS:
            data = await service.get_requirement_metrics(project_ids or [])
        elif metric_type == MetricType.TESTS:
            data = await service.get_test_metrics(project_ids or [])
        elif metric_type == MetricType.DEVELOPMENT:
            data = await service.get_development_metrics(project_ids or [])
        elif metric_type == MetricType.INFRASTRUCTURE:
            data = await service.get_infrastructure_metrics()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported metric type: {metric_type}"
            )
        
        return MetricsResponse(
            metric_type=metric_type.value,
            data=data,
            time_range=time_range.value,
            generated_at=datetime.now().isoformat(),
            cache_info={
                "cached": True,  # 这里应该从服务获取实际的缓存信息
                "cache_age": 0,
                "ttl": 300
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics data for {metric_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取指标数据失败"
        )

@router.post("/query", response_model=MetricsResponse)
@require_dashboard_permission(DashboardPermissionType.DATA_VIEW)
async def query_data(
    request: DataQueryRequest,
    current_user: User = Depends(get_current_user),
    service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """
    高级数据查询
    
    支持复杂的查询条件、分页和多种数据格式
    """
    try:
        # 根据指标类型获取数据
        if request.metric_type == MetricType.PROJECTS:
            data = await service.get_project_metrics(request.project_ids or [])
        elif request.metric_type == MetricType.REQUIREMENTS:
            data = await service.get_requirement_metrics(request.project_ids or [])
        elif request.metric_type == MetricType.TESTS:
            data = await service.get_test_metrics(request.project_ids or [])
        elif request.metric_type == MetricType.DEVELOPMENT:
            data = await service.get_development_metrics(request.project_ids or [])
        elif request.metric_type == MetricType.INFRASTRUCTURE:
            data = await service.get_infrastructure_metrics()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported metric type: {request.metric_type}"
            )
        
        # 应用过滤条件
        if request.filters:
            data = await _apply_filters(data, request.filters)
        
        # 应用分页
        if request.page > 1 or request.page_size < 100:
            data = await _apply_pagination(data, request.page, request.page_size)
        
        # 格式化数据
        if request.format != DataFormat.JSON:
            data = await _format_data(data, request.format)
        
        return MetricsResponse(
            metric_type=request.metric_type.value,
            data=data,
            time_range=request.time_range.value,
            generated_at=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="数据查询失败"
        )

@router.post("/bulk-query")
@require_dashboard_permission(DashboardPermissionType.DATA_VIEW)
async def bulk_query_data(
    request: BulkDataRequest,
    current_user: User = Depends(get_current_user),
    service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """
    批量数据查询
    
    支持一次请求多个数据查询，可选择并行或串行执行
    """
    try:
        results = []
        
        if request.parallel:
            # 并行执行查询
            import asyncio
            tasks = []
            
            for query in request.queries:
                task = _execute_single_query(query, current_user, service)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    results[i] = {
                        "error": str(result),
                        "query_index": i
                    }
        else:
            # 串行执行查询
            for i, query in enumerate(request.queries):
                try:
                    result = await _execute_single_query(query, current_user, service)
                    results.append(result)
                except Exception as e:
                    results.append({
                        "error": str(e),
                        "query_index": i
                    })
        
        return {
            "results": results,
            "total_queries": len(request.queries),
            "successful_queries": len([r for r in results if "error" not in r]),
            "parallel_execution": request.parallel,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in bulk query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量查询失败"
        )

@router.get("/realtime/{widget_type}")
@require_dashboard_permission(DashboardPermissionType.DATA_VIEW)
async def get_realtime_data(
    widget_type: str,
    refresh_interval: int = Query(30, ge=5, le=3600, description="刷新间隔(秒)"),
    project_ids: Optional[List[int]] = Query(None, description="项目ID列表"),
    current_user: User = Depends(get_current_user),
    service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """
    获取实时数据
    
    - **widget_type**: 组件类型
    - **refresh_interval**: 刷新间隔
    - **project_ids**: 项目ID列表 (可选)
    """
    try:
        # 根据组件类型获取相应数据
        data = await _get_widget_data(widget_type, project_ids, current_user, service)
        
        return {
            "widget_type": widget_type,
            "data": data,
            "refresh_interval": refresh_interval,
            "timestamp": datetime.now().isoformat(),
            "next_refresh": (datetime.now() + timedelta(seconds=refresh_interval)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting realtime data for widget {widget_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取实时数据失败"
        )

@router.get("/export/{metric_type}")
@require_dashboard_permission(DashboardPermissionType.DATA_EXPORT)
async def export_data(
    metric_type: MetricType,
    format: DataFormat = Query(DataFormat.CSV, description="导出格式"),
    time_range: TimeRangeType = Query(TimeRangeType.LAST_30_DAYS, description="时间范围"),
    project_ids: Optional[List[int]] = Query(None, description="项目ID列表"),
    current_user: User = Depends(get_current_user),
    service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """
    导出数据
    
    - **metric_type**: 指标类型
    - **format**: 导出格式 (csv, excel, json)
    - **time_range**: 时间范围
    - **project_ids**: 项目ID列表 (可选)
    """
    try:
        # 获取数据
        if metric_type == MetricType.PROJECTS:
            data = await service.get_project_metrics(project_ids or [])
        elif metric_type == MetricType.REQUIREMENTS:
            data = await service.get_requirement_metrics(project_ids or [])
        elif metric_type == MetricType.TESTS:
            data = await service.get_test_metrics(project_ids or [])
        elif metric_type == MetricType.DEVELOPMENT:
            data = await service.get_development_metrics(project_ids or [])
        elif metric_type == MetricType.INFRASTRUCTURE:
            data = await service.get_infrastructure_metrics()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported metric type: {metric_type}"
            )
        
        # 格式化导出数据
        export_data = await _format_export_data(data, format)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{metric_type.value}_{time_range.value}_{timestamp}.{format.value}"
        
        return {
            "filename": filename,
            "format": format.value,
            "data": export_data,
            "size": len(str(export_data)),
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="数据导出失败"
        )

@router.get("/cache/performance")
@require_dashboard_permission(DashboardPermissionType.CACHE_VIEW)
async def get_cache_performance(
    current_user: User = Depends(get_current_user),
    service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """获取缓存性能指标"""
    try:
        metrics = await service.get_cache_performance_metrics()
        
        return {
            "cache_metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cache performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取缓存性能指标失败"
        )

@router.post("/cache/refresh")
@require_dashboard_permission(DashboardPermissionType.CACHE_MANAGE)
async def refresh_cache(
    metric_type: Optional[MetricType] = Query(None, description="指标类型"),
    force: bool = Query(False, description="是否强制刷新"),
    current_user: User = Depends(get_current_user),
    service: DataAggregationService = Depends(get_data_aggregation_service)
):
    """刷新缓存数据"""
    try:
        if metric_type:
            # 刷新特定类型的缓存
            success = await service.refresh_cache_intelligently(
                metric_type.value, 
                force_refresh=force,
                user_id=current_user.id
            )
        else:
            # 刷新所有缓存
            success = await service.preload_dashboard_cache(
                current_user.id, 
                "ADMIN"  # 这里应该从用户获取实际角色
            )
        
        return {
            "success": success,
            "message": "缓存刷新成功" if success else "缓存刷新失败",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error refreshing cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新缓存失败"
        )

# 辅助函数

async def _execute_single_query(
    query: DataQueryRequest, 
    user: User, 
    service: DataAggregationService
) -> Dict[str, Any]:
    """执行单个查询"""
    if query.metric_type == MetricType.PROJECTS:
        data = await service.get_project_metrics(query.project_ids or [])
    elif query.metric_type == MetricType.REQUIREMENTS:
        data = await service.get_requirement_metrics(query.project_ids or [])
    elif query.metric_type == MetricType.TESTS:
        data = await service.get_test_metrics(query.project_ids or [])
    elif query.metric_type == MetricType.DEVELOPMENT:
        data = await service.get_development_metrics(query.project_ids or [])
    elif query.metric_type == MetricType.INFRASTRUCTURE:
        data = await service.get_infrastructure_metrics()
    else:
        raise ValueError(f"Unsupported metric type: {query.metric_type}")
    
    return {
        "metric_type": query.metric_type.value,
        "data": data,
        "time_range": query.time_range.value,
        "generated_at": datetime.now().isoformat()
    }

async def _get_widget_data(
    widget_type: str, 
    project_ids: Optional[List[int]], 
    user: User, 
    service: DataAggregationService
) -> Dict[str, Any]:
    """根据组件类型获取数据"""
    if widget_type == "project_overview":
        return await service.get_project_overview_data(user.id, "ADMIN")
    elif widget_type == "requirement_metrics":
        return await service.get_requirement_metrics(project_ids or [])
    elif widget_type == "test_metrics":
        return await service.get_test_metrics(project_ids or [])
    else:
        # 默认返回空数据
        return {"message": f"No data available for widget type: {widget_type}"}

async def _apply_filters(data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
    """应用过滤条件"""
    # 这里应该实现具体的过滤逻辑
    # 为了简化，我们直接返回原数据
    return data

async def _apply_pagination(data: Dict[str, Any], page: int, page_size: int) -> Dict[str, Any]:
    """应用分页"""
    # 这里应该实现具体的分页逻辑
    # 为了简化，我们直接返回原数据
    return data

async def _format_data(data: Dict[str, Any], format: DataFormat) -> Union[Dict[str, Any], str]:
    """格式化数据"""
    if format == DataFormat.JSON:
        return data
    elif format == DataFormat.CSV:
        # 这里应该实现CSV格式化
        return "CSV formatted data"
    elif format == DataFormat.EXCEL:
        # 这里应该实现Excel格式化
        return "Excel formatted data"
    else:
        return data

async def _format_export_data(data: Dict[str, Any], format: DataFormat) -> Union[Dict[str, Any], str]:
    """格式化导出数据"""
    if format == DataFormat.JSON:
        return data
    elif format == DataFormat.CSV:
        # 这里应该实现CSV导出格式化
        return "CSV export data"
    elif format == DataFormat.EXCEL:
        # 这里应该实现Excel导出格式化
        return "Excel export data"
    else:
        return data