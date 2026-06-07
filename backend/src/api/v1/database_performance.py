"""
数据库性能监控API

本模块提供数据库性能监控和优化的API接口，包括：
1. 查询性能分析
2. 索引优化建议
3. 缓存管理
4. 连接池监控
5. 慢查询分析

主要功能：
- 实时性能监控
- 优化建议生成
- 缓存统计查看
- 性能报告导出
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ...services.database_optimization_service import (
    get_database_optimization_service,
    get_performance_report,
    clear_all_cache
)
from ...services.auth import get_current_user
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic模型定义
class PerformanceReportResponse(BaseModel):
    """性能报告响应模型"""
    performance_grade: str
    total_queries: int
    slow_queries: int
    slow_query_rate: float
    avg_execution_time: float
    cache_hit_rate: float
    cache_hits: int
    cache_misses: int
    recent_slow_queries: List[Dict[str, Any]]


class IndexRecommendationResponse(BaseModel):
    """索引建议响应模型"""
    table_name: str
    columns: List[str]
    index_type: str
    estimated_improvement: float
    priority: str
    reason: str


class CacheStatisticsResponse(BaseModel):
    """缓存统计响应模型"""
    cache_hits: int
    cache_misses: int
    hit_rate: float
    total_requests: int


class ConnectionOptimizationResponse(BaseModel):
    """连接优化响应模型"""
    pool_status: Dict[str, Any]
    active_connections: int
    lock_waits: int
    optimization_suggestions: List[str]
    status: str


class BatchOperationRequest(BaseModel):
    """批量操作请求模型"""
    operations: List[Dict[str, Any]] = Field(..., description="批量操作列表")


class BatchOperationResponse(BaseModel):
    """批量操作响应模型"""
    success: bool
    execution_time: float
    operations_count: int
    results: List[Dict[str, Any]]


@router.get("/performance/report", response_model=PerformanceReportResponse, summary="获取性能报告")
async def get_performance_report_api(
    current_user: User = Depends(get_current_user)
):
    """
    获取数据库查询性能报告
    
    包括查询统计、慢查询分析、缓存命中率等关键性能指标。
    """
    try:
        report = await get_performance_report()
        
        if report.get("status") == "no_data":
            return PerformanceReportResponse(
                performance_grade="N/A",
                total_queries=0,
                slow_queries=0,
                slow_query_rate=0.0,
                avg_execution_time=0.0,
                cache_hit_rate=0.0,
                cache_hits=0,
                cache_misses=0,
                recent_slow_queries=[]
            )
        
        return PerformanceReportResponse(**report)
        
    except Exception as e:
        logger.error(f"获取性能报告失败: {e}")
        raise HTTPException(status_code=500, detail="获取性能报告失败")


@router.get("/performance/indexes/recommendations", 
           response_model=List[IndexRecommendationResponse], 
           summary="获取索引优化建议")
async def get_index_recommendations(
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    获取数据库索引优化建议
    
    基于慢查询分析生成索引优化建议，帮助提升查询性能。
    """
    try:
        recommendations = await optimization_service.generate_index_recommendations()
        
        return [
            IndexRecommendationResponse(
                table_name=rec.table_name,
                columns=rec.columns,
                index_type=rec.index_type,
                estimated_improvement=rec.estimated_improvement,
                priority=rec.priority,
                reason=rec.reason
            )
            for rec in recommendations
        ]
        
    except Exception as e:
        logger.error(f"获取索引建议失败: {e}")
        raise HTTPException(status_code=500, detail="获取索引建议失败")


@router.get("/performance/cache/statistics", 
           response_model=CacheStatisticsResponse, 
           summary="获取缓存统计")
async def get_cache_statistics(
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    获取查询缓存统计信息
    
    包括缓存命中率、缓存请求数等统计数据。
    """
    try:
        stats = await optimization_service.get_cache_statistics()
        
        return CacheStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取缓存统计失败")


@router.post("/performance/cache/clear", summary="清除查询缓存")
async def clear_query_cache(
    pattern: Optional[str] = Query(None, description="缓存键模式，为空则清除所有"),
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    清除查询缓存
    
    可以清除所有缓存或指定模式的缓存。
    """
    try:
        cleared_count = await optimization_service.clear_query_cache(pattern)
        
        return {
            "success": True,
            "message": f"已清除{cleared_count}个缓存项",
            "cleared_count": cleared_count,
            "pattern": pattern or "所有缓存"
        }
        
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail="清除缓存失败")


@router.get("/performance/connections", 
           response_model=ConnectionOptimizationResponse, 
           summary="获取连接优化信息")
async def get_connection_optimization(
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    获取数据库连接优化信息
    
    包括连接池状态、活跃连接数、锁等待情况等。
    """
    try:
        optimization_info = await optimization_service.optimize_database_connections()
        
        if optimization_info.get("status") == "error":
            raise HTTPException(status_code=500, detail=optimization_info.get("error"))
        
        return ConnectionOptimizationResponse(**optimization_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取连接优化信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取连接优化信息失败")


@router.post("/performance/batch-operations", 
            response_model=BatchOperationResponse, 
            summary="执行批量操作")
async def execute_batch_operations(
    request: BatchOperationRequest,
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    执行批量数据库操作
    
    支持批量插入、更新、删除操作，提升大量数据处理的性能。
    """
    try:
        if not request.operations:
            raise HTTPException(status_code=400, detail="操作列表不能为空")
        
        if len(request.operations) > 1000:
            raise HTTPException(status_code=400, detail="批量操作数量不能超过1000")
        
        result = await optimization_service.execute_batch_operations(request.operations)
        
        return BatchOperationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行批量操作失败: {e}")
        raise HTTPException(status_code=500, detail="执行批量操作失败")


@router.get("/performance/slow-queries", summary="获取慢查询列表")
async def get_slow_queries(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    获取慢查询列表
    
    返回最近检测到的慢查询信息，用于性能分析和优化。
    """
    try:
        report = await optimization_service.analyze_query_performance()
        
        slow_queries = report.get("recent_slow_queries", [])
        
        # 限制返回数量
        limited_queries = slow_queries[-limit:] if slow_queries else []
        
        return {
            "slow_queries": limited_queries,
            "total_count": len(slow_queries),
            "returned_count": len(limited_queries),
            "slow_query_threshold": optimization_service.slow_query_threshold
        }
        
    except Exception as e:
        logger.error(f"获取慢查询列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取慢查询列表失败")


@router.get("/performance/ai-sessions/optimized", summary="优化的AI会话查询")
async def get_ai_sessions_optimized(
    user_id: int = Query(..., description="用户ID"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    使用优化查询获取AI会话列表
    
    演示优化查询的使用方法和性能提升效果。
    """
    try:
        start_time = datetime.utcnow()
        
        sessions = await optimization_service.get_ai_chat_sessions_optimized(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "sessions": [session.to_dict() if hasattr(session, 'to_dict') else session for session in sessions],
            "count": len(sessions),
            "execution_time": round(execution_time, 3),
            "optimized": True
        }
        
    except Exception as e:
        logger.error(f"优化AI会话查询失败: {e}")
        raise HTTPException(status_code=500, detail="优化AI会话查询失败")


@router.get("/performance/ai-messages/optimized", summary="优化的AI消息查询")
async def get_ai_messages_optimized(
    session_id: int = Query(..., description="会话ID"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    使用优化查询获取AI消息列表
    
    演示优化查询的使用方法和性能提升效果。
    """
    try:
        start_time = datetime.utcnow()
        
        messages = await optimization_service.get_ai_chat_messages_optimized(
            session_id=session_id,
            limit=limit
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "messages": [msg.to_dict() if hasattr(msg, 'to_dict') else msg for msg in messages],
            "count": len(messages),
            "execution_time": round(execution_time, 3),
            "optimized": True
        }
        
    except Exception as e:
        logger.error(f"优化AI消息查询失败: {e}")
        raise HTTPException(status_code=500, detail="优化AI消息查询失败")


@router.get("/performance/ai-suggestions/optimized", summary="优化的AI建议查询")
async def get_ai_suggestions_optimized(
    user_id: int = Query(..., description="用户ID"),
    project_id: Optional[int] = Query(None, description="项目ID"),
    status: Optional[str] = Query(None, description="建议状态"),
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    使用优化查询获取AI建议列表
    
    演示优化查询的使用方法和性能提升效果。
    """
    try:
        start_time = datetime.utcnow()
        
        suggestions = await optimization_service.get_ai_suggestions_optimized(
            user_id=user_id,
            project_id=project_id,
            status=status
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "suggestions": [sug.to_dict() if hasattr(sug, 'to_dict') else sug for sug in suggestions],
            "count": len(suggestions),
            "execution_time": round(execution_time, 3),
            "optimized": True,
            "filters": {
                "user_id": user_id,
                "project_id": project_id,
                "status": status
            }
        }
        
    except Exception as e:
        logger.error(f"优化AI建议查询失败: {e}")
        raise HTTPException(status_code=500, detail="优化AI建议查询失败")


@router.get("/performance/summary", summary="获取性能优化摘要")
async def get_performance_summary(
    current_user: User = Depends(get_current_user),
    optimization_service = Depends(get_database_optimization_service)
):
    """
    获取数据库性能优化摘要
    
    包括整体性能状况、优化建议数量、缓存效果等关键信息。
    """
    try:
        # 获取性能报告
        performance_report = await optimization_service.analyze_query_performance()
        
        # 获取索引建议
        index_recommendations = await optimization_service.generate_index_recommendations()
        
        # 获取缓存统计
        cache_stats = await optimization_service.get_cache_statistics()
        
        # 获取连接优化信息
        connection_info = await optimization_service.optimize_database_connections()
        
        return {
            "performance": {
                "grade": performance_report.get("performance_grade", "N/A"),
                "total_queries": performance_report.get("total_queries", 0),
                "slow_query_rate": performance_report.get("slow_query_rate", 0),
                "avg_execution_time": performance_report.get("avg_execution_time", 0)
            },
            "cache": {
                "hit_rate": cache_stats.get("hit_rate", 0),
                "total_requests": cache_stats.get("total_requests", 0)
            },
            "optimization": {
                "index_recommendations_count": len(index_recommendations),
                "high_priority_recommendations": len([
                    rec for rec in index_recommendations if rec.priority == "HIGH"
                ])
            },
            "connections": {
                "status": connection_info.get("status", "unknown"),
                "active_connections": connection_info.get("active_connections", 0),
                "suggestions_count": len(connection_info.get("optimization_suggestions", []))
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取性能优化摘要失败: {e}")
        raise HTTPException(status_code=500, detail="获取性能优化摘要失败")