"""
缓存优化API接口

提供缓存管理、性能监控和优化功能的REST API接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from ...core.database import get_async_session
from ...core.auth import get_current_user
from ...services.data_cache_optimization_service import (
    get_data_cache_optimization_service,
    RefreshStrategy,
    PreloadConfig
)
from ...services.data_aggregation_service import DataAggregationService
from ...models.user import User

router = APIRouter(prefix="/api/v1/cache", tags=["缓存优化"])


class CacheStatsResponse(BaseModel):
    """缓存统计响应模型"""
    overall_metrics: Dict[str, Any]
    l1_cache: Dict[str, Any]
    l2_cache: Dict[str, Any]
    data_quality: Dict[str, Any]
    performance: Dict[str, Any]
    error_summary: Dict[str, Any]
    cache_health: Dict[str, Any]


class CacheOptimizationResponse(BaseModel):
    """缓存优化响应模型"""
    l1_cleanup: int
    l2_optimization: bool
    preload_optimization: int
    quality_improvement: int
    optimization_timestamp: str


class PreloadRequest(BaseModel):
    """预加载请求模型"""
    cache_types: List[str] = Field(..., description="要预加载的缓存类型")
    user_id: Optional[int] = Field(None, description="用户ID")
    role_type: Optional[str] = Field(None, description="角色类型")
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表")


class RefreshRequest(BaseModel):
    """刷新请求模型"""
    key_type: str = Field(..., description="缓存键类型")
    strategy: str = Field("lazy", description="刷新策略")
    force_refresh: bool = Field(False, description="是否强制刷新")
    user_id: Optional[int] = Field(None, description="用户ID")
    role_type: Optional[str] = Field(None, description="角色类型")
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表")


class InvalidateRequest(BaseModel):
    """失效请求模型"""
    key_type: Optional[str] = Field(None, description="缓存键类型")
    pattern: Optional[str] = Field(None, description="失效模式")
    user_id: Optional[int] = Field(None, description="用户ID")
    role_type: Optional[str] = Field(None, description="角色类型")
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表")


@router.get("/statistics", response_model=CacheStatsResponse)
async def get_cache_statistics(
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    获取缓存统计信息
    
    返回详细的缓存性能指标、数据质量和健康状况
    """
    try:
        cache_service = await get_data_cache_optimization_service(db)
        stats = await cache_service.get_cache_statistics()
        
        return CacheStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败: {str(e)}")


@router.post("/optimize", response_model=CacheOptimizationResponse)
async def optimize_cache_performance(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    优化缓存性能
    
    执行缓存清理、性能优化和数据质量改进
    """
    try:
        cache_service = await get_data_cache_optimization_service(db)
        
        # 在后台执行优化任务
        async def run_optimization():
            return await cache_service.optimize_cache_performance()
        
        # 立即执行优化（也可以放到后台任务中）
        results = await run_optimization()
        
        return CacheOptimizationResponse(
            **results,
            optimization_timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"缓存性能优化失败: {str(e)}")


@router.post("/preload")
async def preload_cache(
    request: PreloadRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    预加载缓存数据
    
    根据指定的缓存类型和参数预加载数据到缓存中
    """
    try:
        cache_service = await get_data_cache_optimization_service(db)
        data_service = DataAggregationService(db)
        
        # 构建预加载配置
        preload_configs = []
        
        for cache_type in request.cache_types:
            if cache_type == "project_overview":
                if request.user_id and request.role_type:
                    config = PreloadConfig(
                        key_type="project_overview",
                        data_generator=lambda: data_service._generate_project_overview_data(
                            request.user_id, request.role_type
                        ),
                        params={"user_id": request.user_id, "role_type": request.role_type},
                        priority=10
                    )
                    preload_configs.append(config)
                    
            elif cache_type == "requirement_metrics":
                if request.project_ids:
                    config = PreloadConfig(
                        key_type="requirement_metrics",
                        data_generator=lambda: data_service._generate_requirement_metrics_data(
                            request.project_ids, request.user_id
                        ),
                        params={"project_ids": request.project_ids, "user_id": request.user_id},
                        priority=8
                    )
                    preload_configs.append(config)
        
        if not preload_configs:
            raise HTTPException(status_code=400, detail="没有有效的预加载配置")
        
        # 在后台执行预加载
        async def run_preload():
            return await cache_service.preload_cache(preload_configs)
        
        background_tasks.add_task(run_preload)
        
        return {
            "message": "缓存预加载任务已启动",
            "cache_types": request.cache_types,
            "config_count": len(preload_configs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预加载缓存失败: {str(e)}")


@router.post("/refresh")
async def refresh_cache(
    request: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    刷新缓存数据
    
    根据指定的策略刷新缓存数据
    """
    try:
        cache_service = await get_data_cache_optimization_service(db)
        
        # 解析刷新策略
        strategy_mapping = {
            "immediate": RefreshStrategy.IMMEDIATE,
            "lazy": RefreshStrategy.LAZY,
            "scheduled": RefreshStrategy.SCHEDULED,
            "event_driven": RefreshStrategy.EVENT_DRIVEN
        }
        
        strategy = strategy_mapping.get(request.strategy, RefreshStrategy.LAZY)
        
        # 构建缓存键参数
        cache_params = {}
        if request.user_id:
            cache_params["user_id"] = request.user_id
        if request.role_type:
            cache_params["role_type"] = request.role_type
        if request.project_ids:
            cache_params["project_ids"] = request.project_ids
        
        if request.force_refresh:
            # 强制刷新：直接失效缓存
            invalidated_count = await cache_service.invalidate_cache(
                request.key_type, 
                **cache_params
            )
            
            return {
                "message": "缓存强制刷新完成",
                "key_type": request.key_type,
                "strategy": "force_refresh",
                "invalidated_count": invalidated_count
            }
        else:
            # 智能刷新
            success = await cache_service.intelligent_refresh(
                request.key_type,
                strategy,
                **cache_params
            )
            
            return {
                "message": "缓存智能刷新完成" if success else "缓存刷新失败",
                "key_type": request.key_type,
                "strategy": request.strategy,
                "success": success
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新缓存失败: {str(e)}")


@router.post("/invalidate")
async def invalidate_cache(
    request: InvalidateRequest,
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    失效缓存数据
    
    根据键类型或模式失效缓存数据
    """
    try:
        cache_service = await get_data_cache_optimization_service(db)
        
        # 构建缓存键参数
        cache_params = {}
        if request.user_id:
            cache_params["user_id"] = request.user_id
        if request.role_type:
            cache_params["role_type"] = request.role_type
        if request.project_ids:
            cache_params["project_ids"] = request.project_ids
        
        if request.pattern:
            # 模式匹配失效
            invalidated_count = await cache_service.invalidate_cache(
                request.key_type or "unknown",
                pattern=request.pattern
            )
        elif request.key_type:
            # 单个键失效
            invalidated_count = await cache_service.invalidate_cache(
                request.key_type,
                **cache_params
            )
        else:
            raise HTTPException(status_code=400, detail="必须指定key_type或pattern")
        
        return {
            "message": "缓存失效完成",
            "key_type": request.key_type,
            "pattern": request.pattern,
            "invalidated_count": invalidated_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"失效缓存失败: {str(e)}")


@router.get("/health")
async def get_cache_health(
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    获取缓存健康状况
    
    返回缓存系统的健康评估和建议
    """
    try:
        cache_service = await get_data_cache_optimization_service(db)
        stats = await cache_service.get_cache_statistics()
        
        health_info = stats.get("cache_health", {})
        
        return {
            "health_status": health_info.get("health_level", "unknown"),
            "overall_hit_rate": health_info.get("overall_hit_rate", 0),
            "error_rate": health_info.get("error_rate", 0),
            "total_requests": health_info.get("total_requests", 0),
            "l1_cache_usage": health_info.get("l1_cache_usage", 0),
            "recommendations": health_info.get("recommendations", []),
            "check_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存健康状况失败: {str(e)}")


@router.get("/quality/{key_type}")
async def get_data_quality(
    key_type: str,
    user_id: Optional[int] = Query(None, description="用户ID"),
    role_type: Optional[str] = Query(None, description="角色类型"),
    project_ids: Optional[List[int]] = Query(None, description="项目ID列表"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    获取数据质量报告
    
    返回指定缓存类型的数据质量指标和建议
    """
    try:
        data_service = DataAggregationService(db)
        
        # 构建参数
        params = {}
        if user_id:
            params["user_id"] = user_id
        if role_type:
            params["role_type"] = role_type
        if project_ids:
            params["project_ids"] = project_ids
        
        # 监控数据质量
        quality_report = await data_service.monitor_data_quality(key_type, **params)
        
        return quality_report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据质量报告失败: {str(e)}")


@router.get("/performance")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    获取缓存性能指标
    
    返回详细的缓存性能监控数据
    """
    try:
        data_service = DataAggregationService(db)
        
        # 获取缓存性能指标
        performance_metrics = await data_service.get_cache_performance_metrics()
        
        return performance_metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存性能指标失败: {str(e)}")


@router.post("/performance/optimize")
async def optimize_performance(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    优化数据聚合性能
    
    执行数据聚合服务的性能优化
    """
    try:
        data_service = DataAggregationService(db)
        
        # 在后台执行性能优化
        async def run_performance_optimization():
            return await data_service.optimize_data_aggregation_performance()
        
        background_tasks.add_task(run_performance_optimization)
        
        return {
            "message": "数据聚合性能优化任务已启动",
            "optimization_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"优化数据聚合性能失败: {str(e)}")


@router.post("/dashboard/preload")
async def preload_dashboard_cache(
    user_id: int = Query(..., description="用户ID"),
    role_type: str = Query(..., description="角色类型"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db = Depends(get_async_session)
):
    """
    预加载仪表板缓存
    
    为指定用户和角色预加载仪表板相关的缓存数据
    """
    try:
        data_service = DataAggregationService(db)
        
        # 在后台执行仪表板缓存预加载
        async def run_dashboard_preload():
            return await data_service.preload_dashboard_cache(user_id, role_type)
        
        background_tasks.add_task(run_dashboard_preload)
        
        return {
            "message": "仪表板缓存预加载任务已启动",
            "user_id": user_id,
            "role_type": role_type,
            "preload_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预加载仪表板缓存失败: {str(e)}")


@router.get("/config")
async def get_cache_config(
    current_user: User = Depends(get_current_user)
):
    """
    获取缓存配置信息
    
    返回当前的缓存配置和策略
    """
    try:
        from ...core.cache_config import DashboardCacheConfig, CacheStrategy, CacheMonitoring
        
        config = DashboardCacheConfig()
        strategy = CacheStrategy()
        monitoring = CacheMonitoring()
        
        return {
            "cache_configs": {
                key: {
                    "namespace": cfg.namespace.value,
                    "ttl": cfg.ttl.value,
                    "description": cfg.description,
                    "pattern": cfg.pattern,
                    "compression": cfg.compression
                }
                for key, cfg in config.CACHE_CONFIGS.items()
            },
            "strategies": strategy.STRATEGIES,
            "type_strategy_mapping": strategy.TYPE_STRATEGY_MAPPING,
            "monitoring_metrics": monitoring.METRICS,
            "alerts": monitoring.ALERTS
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存配置失败: {str(e)}")