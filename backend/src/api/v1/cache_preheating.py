"""
缓存预热管理API

本模块提供缓存预热管理的API接口，包括：
1. 预热状态查询
2. 手动预热触发
3. 预热策略配置
4. 预热效果监控
5. 访问模式分析

主要功能：
- 查看预热服务状态
- 手动触发预热任务
- 配置预热策略
- 监控预热效果
- 分析访问模式
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ...services.cache_preheating_service import (
    get_cache_preheating_service,
    start_cache_preheating,
    manual_cache_preheat,
    get_preheating_status,
    PreheatingStrategy,
    PreheatingPriority
)
from ...services.auth import get_current_user
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic模型定义
class PreheatingStatusResponse(BaseModel):
    """预热状态响应模型"""
    enabled: bool
    running_tasks: int
    queued_tasks: int
    completed_tasks: int
    access_patterns: int
    statistics: Dict[str, Any]
    last_analysis: str


class ManualPreheatingRequest(BaseModel):
    """手动预热请求模型"""
    data_source: str = Field(..., description="数据源类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="预热参数")
    priority: str = Field(default="medium", description="优先级")


class ManualPreheatingResponse(BaseModel):
    """手动预热响应模型"""
    success: bool
    task_id: str
    message: str


class PreheatingConfigRequest(BaseModel):
    """预热配置请求模型"""
    enabled: bool = Field(default=True, description="是否启用预热")
    max_concurrent_tasks: int = Field(default=5, ge=1, le=20, description="最大并发任务数")
    preheating_interval: int = Field(default=3600, ge=300, le=86400, description="预热间隔(秒)")
    hot_data_threshold: int = Field(default=10, ge=1, le=100, description="热点数据阈值")


class AccessPatternResponse(BaseModel):
    """访问模式响应模型"""
    resource_type: str
    resource_id: str
    access_count: int
    last_access: str
    access_frequency: float
    peak_hours: List[int]
    user_count: int
    avg_response_time: float


@router.get("/status", response_model=PreheatingStatusResponse, summary="获取预热状态")
async def get_preheating_status_api(
    current_user: User = Depends(get_current_user)
):
    """
    获取缓存预热服务状态
    
    包括运行状态、任务统计、访问模式数量等信息。
    """
    try:
        status = await get_preheating_status()
        
        return PreheatingStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"获取预热状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取预热状态失败")


@router.post("/start", summary="启动预热服务")
async def start_preheating_service(
    current_user: User = Depends(get_current_user)
):
    """
    启动缓存预热服务
    
    启动后台预热工作进程，开始自动分析访问模式和预热缓存。
    """
    try:
        await start_cache_preheating()
        
        return {
            "success": True,
            "message": "缓存预热服务已启动",
            "started_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"启动预热服务失败: {e}")
        raise HTTPException(status_code=500, detail="启动预热服务失败")


@router.post("/stop", summary="停止预热服务")
async def stop_preheating_service(
    current_user: User = Depends(get_current_user),
    preheating_service = Depends(get_cache_preheating_service)
):
    """
    停止缓存预热服务
    
    停止后台预热工作进程，保存当前状态和统计数据。
    """
    try:
        await preheating_service.stop_preheating()
        
        return {
            "success": True,
            "message": "缓存预热服务已停止",
            "stopped_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"停止预热服务失败: {e}")
        raise HTTPException(status_code=500, detail="停止预热服务失败")


@router.post("/manual", response_model=ManualPreheatingResponse, summary="手动预热")
async def manual_preheating(
    request: ManualPreheatingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    手动触发缓存预热
    
    支持的数据源类型：
    - ai_chat_sessions: AI会话数据
    - ai_chat_messages: AI消息数据
    - ai_suggestions: AI建议数据
    - ai_model_configs: AI模型配置
    - user_preferences: 用户偏好设置
    """
    try:
        # 验证数据源类型
        valid_sources = [
            "ai_chat_sessions", "ai_chat_messages", "ai_suggestions",
            "ai_model_configs", "user_preferences"
        ]
        
        if request.data_source not in valid_sources:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的数据源类型: {request.data_source}"
            )
        
        # 验证必要参数
        if request.data_source in ["ai_chat_sessions", "ai_suggestions", "user_preferences"]:
            if "user_id" not in request.parameters:
                raise HTTPException(status_code=400, detail="缺少user_id参数")
        
        if request.data_source == "ai_chat_messages":
            if "session_id" not in request.parameters:
                raise HTTPException(status_code=400, detail="缺少session_id参数")
        
        # 执行手动预热
        task_id = await manual_cache_preheat(request.data_source, **request.parameters)
        
        return ManualPreheatingResponse(
            success=True,
            task_id=task_id,
            message=f"预热任务已创建: {task_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动预热失败: {e}")
        raise HTTPException(status_code=500, detail="手动预热失败")


@router.get("/patterns", response_model=List[AccessPatternResponse], summary="获取访问模式")
async def get_access_patterns(
    resource_type: Optional[str] = Query(None, description="资源类型过滤"),
    min_frequency: Optional[float] = Query(None, ge=0, description="最小访问频率"),
    current_user: User = Depends(get_current_user),
    preheating_service = Depends(get_cache_preheating_service)
):
    """
    获取访问模式分析结果
    
    返回系统分析的用户访问模式，用于优化预热策略。
    """
    try:
        patterns = []
        
        for key, pattern in preheating_service.access_patterns.items():
            # 应用过滤条件
            if resource_type and pattern.resource_type != resource_type:
                continue
            
            if min_frequency and pattern.access_frequency < min_frequency:
                continue
            
            patterns.append(AccessPatternResponse(
                resource_type=pattern.resource_type,
                resource_id=pattern.resource_id,
                access_count=pattern.access_count,
                last_access=pattern.last_access.isoformat(),
                access_frequency=pattern.access_frequency,
                peak_hours=pattern.peak_hours,
                user_count=pattern.user_count,
                avg_response_time=pattern.avg_response_time
            ))
        
        # 按访问频率排序
        patterns.sort(key=lambda x: x.access_frequency, reverse=True)
        
        return patterns
        
    except Exception as e:
        logger.error(f"获取访问模式失败: {e}")
        raise HTTPException(status_code=500, detail="获取访问模式失败")


@router.post("/analyze", summary="触发访问模式分析")
async def trigger_pattern_analysis(
    current_user: User = Depends(get_current_user),
    preheating_service = Depends(get_cache_preheating_service)
):
    """
    手动触发访问模式分析
    
    立即分析用户访问模式，更新预热策略。
    """
    try:
        await preheating_service.analyze_access_patterns()
        
        return {
            "success": True,
            "message": "访问模式分析已完成",
            "analyzed_at": datetime.utcnow().isoformat(),
            "patterns_count": len(preheating_service.access_patterns)
        }
        
    except Exception as e:
        logger.error(f"访问模式分析失败: {e}")
        raise HTTPException(status_code=500, detail="访问模式分析失败")


@router.get("/tasks", summary="获取预热任务列表")
async def get_preheating_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    current_user: User = Depends(get_current_user),
    preheating_service = Depends(get_cache_preheating_service)
):
    """
    获取预热任务列表
    
    返回最近的预热任务执行情况，用于监控预热效果。
    """
    try:
        tasks = preheating_service.completed_tasks[-limit:]
        
        # 应用状态过滤
        if status:
            if status == "success":
                tasks = [task for task in tasks if task.success]
            elif status == "failed":
                tasks = [task for task in tasks if not task.success]
        
        # 转换为响应格式
        task_list = []
        for task in tasks:
            task_info = {
                "task_id": task.task_id,
                "strategy": task.strategy.value,
                "priority": task.priority.value,
                "data_source": task.data_source,
                "parameters": task.parameters,
                "success": task.success,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "error_message": task.error_message
            }
            
            if task.completed_at and task.created_at:
                execution_time = (task.completed_at - task.created_at).total_seconds()
                task_info["execution_time"] = execution_time
            
            task_list.append(task_info)
        
        return {
            "tasks": task_list,
            "total_count": len(task_list),
            "running_tasks": len(preheating_service.running_tasks),
            "queued_tasks": preheating_service.task_queue.qsize()
        }
        
    except Exception as e:
        logger.error(f"获取预热任务失败: {e}")
        raise HTTPException(status_code=500, detail="获取预热任务失败")


@router.get("/statistics", summary="获取预热统计")
async def get_preheating_statistics(
    current_user: User = Depends(get_current_user),
    preheating_service = Depends(get_cache_preheating_service)
):
    """
    获取缓存预热统计信息
    
    包括任务执行统计、性能改善指标等。
    """
    try:
        stats = preheating_service.stats.copy()
        
        # 计算成功率
        total_tasks = stats.get("total_tasks", 0)
        successful_tasks = stats.get("successful_tasks", 0)
        success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # 添加计算指标
        stats["success_rate"] = round(success_rate, 2)
        stats["current_patterns"] = len(preheating_service.access_patterns)
        stats["active_tasks"] = len(preheating_service.running_tasks)
        
        return {
            "statistics": stats,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取预热统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取预热统计失败")


@router.post("/config", summary="更新预热配置")
async def update_preheating_config(
    config: PreheatingConfigRequest,
    current_user: User = Depends(get_current_user),
    preheating_service = Depends(get_cache_preheating_service)
):
    """
    更新缓存预热配置
    
    允许管理员调整预热服务的运行参数。
    """
    try:
        # 更新配置
        preheating_service.preheating_enabled = config.enabled
        preheating_service.max_concurrent_tasks = config.max_concurrent_tasks
        preheating_service.preheating_interval = config.preheating_interval
        preheating_service.hot_data_threshold = config.hot_data_threshold
        
        return {
            "success": True,
            "message": "预热配置已更新",
            "config": {
                "enabled": config.enabled,
                "max_concurrent_tasks": config.max_concurrent_tasks,
                "preheating_interval": config.preheating_interval,
                "hot_data_threshold": config.hot_data_threshold
            },
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新预热配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新预热配置失败")


@router.get("/health", summary="预热服务健康检查")
async def preheating_health_check(
    current_user: User = Depends(get_current_user),
    preheating_service = Depends(get_cache_preheating_service)
):
    """
    预热服务健康检查
    
    检查预热服务的运行状态和健康指标。
    """
    try:
        status = await preheating_service.get_preheating_status()
        
        # 健康状态评估
        health_score = 100
        issues = []
        
        # 检查服务是否启用
        if not status["enabled"]:
            health_score -= 50
            issues.append("预热服务未启用")
        
        # 检查任务执行情况
        total_tasks = status["statistics"].get("total_tasks", 0)
        failed_tasks = status["statistics"].get("failed_tasks", 0)
        
        if total_tasks > 0:
            failure_rate = failed_tasks / total_tasks
            if failure_rate > 0.2:  # 失败率超过20%
                health_score -= 30
                issues.append(f"任务失败率过高: {failure_rate:.1%}")
            elif failure_rate > 0.1:  # 失败率超过10%
                health_score -= 15
                issues.append(f"任务失败率较高: {failure_rate:.1%}")
        
        # 检查访问模式数量
        if status["access_patterns"] == 0:
            health_score -= 20
            issues.append("未检测到访问模式")
        
        # 确定健康状态
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 70:
            health_status = "good"
        elif health_score >= 50:
            health_status = "fair"
        else:
            health_status = "poor"
        
        return {
            "health_status": health_status,
            "health_score": health_score,
            "issues": issues,
            "service_status": status,
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"预热服务健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="预热服务健康检查失败")