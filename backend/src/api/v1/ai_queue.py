"""
AI请求队列管理API
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

from ...core.database import get_async_session
from ...services.ai_router_service import AIRouterService
from ...services.request_queue_service import RequestPriority, RequestStatus
from ...core.fastapi_integration import with_services

router = APIRouter()


class QueueRequestModel(BaseModel):
    """队列请求模型"""
    content: str
    priority: str = "normal"
    timeout_seconds: int = 300
    context: Optional[Dict[str, Any]] = None


class QueueStatusResponse(BaseModel):
    """队列状态响应模型"""
    request_id: str
    status: str
    priority: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_time: Optional[float] = None
    assigned_provider: Optional[str] = None
    error_message: Optional[str] = None


@router.post("/queue", summary="添加请求到队列")
@with_services(AIRouterService)
async def queue_ai_request(
    request: QueueRequestModel,
    services: dict,
    user_id: int = 1  # 在实际应用中应该从认证中获取
) -> Dict[str, Any]:
    """
    将AI请求添加到队列
    
    Args:
        request: 请求数据
        user_id: 用户ID
        
    Returns:
        Dict[str, Any]: 包含请求ID和队列信息的响应
    """
    try:
        router_service = services[AIRouterService]
        
        # 添加请求到队列
        request_id = await router_service.queue_request(
            user_id=user_id,
            content=request.content,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            context=request.context
        )
        
        # 获取队列状态
        queue_status = await router_service.get_queue_status()
        
        return {
            "success": True,
            "request_id": request_id,
            "message": "请求已成功添加到队列",
            "queue_info": {
                "position": queue_status["queue_metrics"]["pending_requests"],
                "estimated_wait_time": "根据当前队列长度估算",
                "priority": request.priority
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加请求到队列失败: {str(e)}")


@router.post("/queue/failover", summary="添加请求到队列（启用故障转移）")
@with_services(AIRouterService)
async def queue_ai_request_with_failover(
    request: QueueRequestModel,
    services: dict,
    user_id: int = 1
) -> Dict[str, Any]:
    """
    将AI请求添加到队列并启用故障转移功能
    
    Args:
        request: 请求数据
        user_id: 用户ID
        
    Returns:
        Dict[str, Any]: 包含请求ID和队列信息的响应
    """
    try:
        router_service = services[AIRouterService]
        
        # 添加请求到队列（启用故障转移）
        request_id = await router_service.queue_request_with_failover(
            user_id=user_id,
            content=request.content,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            context=request.context
        )
        
        # 获取队列状态和故障转移统计
        queue_status = await router_service.get_queue_status()
        failover_stats = await router_service.get_failover_statistics()
        
        return {
            "success": True,
            "request_id": request_id,
            "message": "请求已成功添加到队列（故障转移已启用）",
            "queue_info": {
                "position": queue_status["queue_metrics"]["pending_requests"],
                "estimated_wait_time": "根据当前队列长度估算",
                "priority": request.priority,
                "failover_enabled": True
            },
            "failover_info": {
                "available_providers": failover_stats["available_providers"],
                "total_providers": failover_stats["total_providers"],
                "availability_rate": f"{failover_stats['availability_rate']:.1%}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加故障转移请求到队列失败: {str(e)}")


@router.get("/queue/{request_id}/status", summary="获取请求状态")
@with_services(AIRouterService)
async def get_request_status(
    request_id: str,
    services: dict
) -> QueueStatusResponse:
    """
    获取队列中请求的状态
    
    Args:
        request_id: 请求ID
        
    Returns:
        QueueStatusResponse: 请求状态信息
    """
    try:
        router_service = services[AIRouterService]
        
        # 获取请求状态
        status = await router_service.request_queue.get_request_status(request_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="请求未找到")
        
        return QueueStatusResponse(**status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取请求状态失败: {str(e)}")


@router.delete("/queue/{request_id}", summary="取消队列请求")
@with_services(AIRouterService)
async def cancel_request(
    request_id: str,
    services: dict
) -> Dict[str, Any]:
    """
    取消队列中的请求
    
    Args:
        request_id: 请求ID
        
    Returns:
        Dict[str, Any]: 取消结果
    """
    try:
        router_service = services[AIRouterService]
        
        # 取消请求
        cancelled = await router_service.request_queue.cancel_request(request_id)
        
        if not cancelled:
            raise HTTPException(status_code=400, detail="无法取消请求，请求可能已完成或不存在")
        
        return {
            "success": True,
            "message": "请求已成功取消",
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消请求失败: {str(e)}")


@router.get("/queue/metrics", summary="获取队列指标")
@with_services(AIRouterService)
async def get_queue_metrics(services: dict) -> Dict[str, Any]:
    """
    获取队列性能指标和统计信息
    
    Returns:
        Dict[str, Any]: 队列指标数据
    """
    try:
        router_service = services[AIRouterService]
        
        # 获取队列状态和负载均衡统计
        queue_status = await router_service.get_queue_status()
        lb_stats = await router_service.get_load_balancing_stats()
        
        return {
            "success": True,
            "data": {
                "queue_metrics": queue_status["queue_metrics"],
                "provider_loads": queue_status["provider_loads"],
                "load_balancing_stats": lb_stats,
                "timestamp": lb_stats["timestamp"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取队列指标失败: {str(e)}")


@router.post("/queue/process/{provider_id}", summary="处理队列请求")
@with_services(AIRouterService)
async def process_queue_request(
    provider_id: str,
    services: dict,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    从队列中取出并处理请求（模拟AI提供商处理）
    
    Args:
        provider_id: 提供商ID
        background_tasks: 后台任务
        
    Returns:
        Dict[str, Any]: 处理结果
    """
    try:
        router_service = services[AIRouterService]
        
        # 从队列中获取请求
        request_info = await router_service.process_queued_request(provider_id)
        
        if not request_info:
            return {
                "success": True,
                "message": "当前没有可处理的请求",
                "provider_id": provider_id
            }
        
        # 模拟异步处理
        async def simulate_processing():
            import asyncio
            # 模拟处理时间
            await asyncio.sleep(2)
            
            # 完成请求
            await router_service.complete_queued_request(
                request_info['request_id'],
                result=f"由 {provider_id} 成功处理: {request_info['ai_request'].content[:50]}..."
            )
        
        # 添加到后台任务
        background_tasks.add_task(simulate_processing)
        
        return {
            "success": True,
            "message": "请求已开始处理",
            "request_id": request_info['request_id'],
            "provider_id": provider_id,
            "priority": request_info['priority'],
            "content_preview": request_info['ai_request'].content[:100] + "..." if len(request_info['ai_request'].content) > 100 else request_info['ai_request'].content
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理队列请求失败: {str(e)}")


@router.get("/providers/load", summary="获取提供商负载状态")
@with_services(AIRouterService)
async def get_provider_loads(services: dict) -> Dict[str, Any]:
    """
    获取所有AI提供商的负载状态
    
    Returns:
        Dict[str, Any]: 提供商负载信息
    """
    try:
        router_service = services[AIRouterService]
        
        # 获取负载分布
        load_distribution = router_service.get_current_load_distribution()
        
        return {
            "success": True,
            "data": load_distribution
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商负载失败: {str(e)}")


@router.post("/providers/{provider_id}/capacity", summary="设置提供商容量")
@with_services(AIRouterService)
async def set_provider_capacity(
    provider_id: str,
    capacity: int,
    services: dict
) -> Dict[str, Any]:
    """
    设置AI提供商的并发处理容量
    
    Args:
        provider_id: 提供商ID
        capacity: 最大并发容量
        
    Returns:
        Dict[str, Any]: 设置结果
    """
    try:
        if capacity <= 0:
            raise HTTPException(status_code=400, detail="容量必须大于0")
        
        router_service = services[AIRouterService]
        
        # 设置提供商容量
        await router_service.request_queue.set_provider_capacity(provider_id, capacity)
        
        return {
            "success": True,
            "message": f"提供商 {provider_id} 容量已设置为 {capacity}",
            "provider_id": provider_id,
            "capacity": capacity
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置提供商容量失败: {str(e)}")


@router.get("/demo", summary="队列功能演示")
@with_services(AIRouterService)
async def queue_demo(services: dict) -> Dict[str, Any]:
    """
    队列功能演示 - 添加一些示例请求并展示队列状态
    
    Returns:
        Dict[str, Any]: 演示结果
    """
    try:
        router_service = services[AIRouterService]
        
        # 添加一些示例请求
        demo_requests = [
            {"content": "请帮我生成一个Python排序算法", "priority": "high"},
            {"content": "分析这段代码的时间复杂度", "priority": "normal"},
            {"content": "生成单元测试用例", "priority": "urgent"},
            {"content": "优化数据库查询性能", "priority": "low"},
            {"content": "设计RESTful API接口", "priority": "normal"}
        ]
        
        added_requests = []
        for i, req in enumerate(demo_requests):
            request_id = await router_service.queue_request(
                user_id=i + 1,
                content=req["content"],
                priority=req["priority"]
            )
            added_requests.append({
                "request_id": request_id,
                "content": req["content"],
                "priority": req["priority"]
            })
        
        # 获取队列状态
        queue_status = await router_service.get_queue_status()
        
        return {
            "success": True,
            "message": "队列演示完成",
            "demo_data": {
                "added_requests": added_requests,
                "queue_metrics": queue_status["queue_metrics"],
                "instructions": {
                    "next_steps": [
                        "使用 POST /queue/process/{provider_id} 来处理队列中的请求",
                        "使用 GET /queue/{request_id}/status 来查看请求状态",
                        "使用 GET /queue/metrics 来查看详细的队列指标"
                    ],
                    "available_providers": ["openai", "anthropic", "baidu_wenxin", "aliyun_tongyi"]
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"队列演示失败: {str(e)}")


@router.get("/failover/health", summary="获取提供商健康状态")
@with_services(AIRouterService)
async def get_provider_health(services: dict) -> Dict[str, Any]:
    """
    获取所有AI提供商的健康状态
    
    Returns:
        Dict[str, Any]: 提供商健康状态信息
    """
    try:
        router_service = services[AIRouterService]
        
        health_status = await router_service.get_provider_health_status()
        failover_stats = await router_service.get_failover_statistics()
        
        return {
            "success": True,
            "data": {
                "provider_health": health_status,
                "failover_statistics": failover_stats,
                "summary": {
                    "total_providers": len(health_status),
                    "available_providers": sum(1 for h in health_status.values() if h["is_available"]),
                    "average_success_rate": failover_stats["average_success_rate"],
                    "average_response_time": failover_stats["average_response_time"]
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商健康状态失败: {str(e)}")


@router.post("/failover/provider/{provider_id}/status", summary="手动设置提供商状态")
@with_services(AIRouterService)
async def set_provider_status(
    provider_id: str,
    is_available: bool,
    reason: str = "",
    services: dict = None
) -> Dict[str, Any]:
    """
    手动设置AI提供商的可用状态
    
    Args:
        provider_id: 提供商ID
        is_available: 是否可用
        reason: 设置原因
        
    Returns:
        Dict[str, Any]: 设置结果
    """
    try:
        router_service = services[AIRouterService]
        
        # 查找对应的提供商枚举
        from ...services.ai_router_service import AIProvider
        provider_enum = None
        for provider in AIProvider:
            if provider.value == provider_id:
                provider_enum = provider
                break
        
        if not provider_enum:
            raise HTTPException(status_code=400, detail=f"未知的提供商ID: {provider_id}")
        
        # 设置提供商状态
        await router_service.manually_mark_provider_status(provider_enum, is_available, reason)
        
        # 获取更新后的健康状态
        health_status = await router_service.get_provider_health_status()
        provider_health = health_status.get(provider_id, {})
        
        return {
            "success": True,
            "message": f"提供商 {provider_id} 状态已设置为 {'可用' if is_available else '不可用'}",
            "provider_id": provider_id,
            "new_status": {
                "is_available": provider_health.get("is_available", is_available),
                "success_rate": provider_health.get("success_rate", 0.0),
                "error_count": provider_health.get("error_count", 0),
                "reason": reason
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置提供商状态失败: {str(e)}")


@router.post("/failover/test", summary="故障转移功能测试")
@with_services(AIRouterService)
async def test_failover_functionality(
    services: dict,
    simulate_failures: bool = True,
    test_requests_count: int = 5
) -> Dict[str, Any]:
    """
    测试故障转移功能
    
    Args:
        simulate_failures: 是否模拟提供商故障
        test_requests_count: 测试请求数量
        
    Returns:
        Dict[str, Any]: 测试结果
    """
    try:
        router_service = services[AIRouterService]
        
        test_results = {
            "test_started_at": datetime.utcnow().isoformat(),
            "simulate_failures": simulate_failures,
            "test_requests_count": test_requests_count,
            "requests": [],
            "failover_events": [],
            "summary": {}
        }
        
        # 如果启用故障模拟，随机标记一些提供商为不可用
        if simulate_failures:
            from ...services.ai_router_service import AIProvider
            import random
            
            providers_to_fail = random.sample(
                list(AIProvider), 
                min(2, len(list(AIProvider)) - 1)  # 至少保留一个可用提供商
            )
            
            for provider in providers_to_fail:
                if provider != AIProvider.CUSTOM:
                    await router_service.manually_mark_provider_status(
                        provider, False, "Simulated failure for testing"
                    )
                    test_results["failover_events"].append({
                        "event": "provider_marked_unavailable",
                        "provider": provider.value,
                        "reason": "Simulated failure for testing",
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        # 发送测试请求
        test_requests = [
            "请生成一个Python排序算法",
            "分析这段代码的性能问题",
            "创建一个RESTful API设计",
            "编写单元测试用例",
            "优化数据库查询性能"
        ]
        
        successful_requests = 0
        failed_requests = 0
        
        for i in range(test_requests_count):
            request_content = test_requests[i % len(test_requests)]
            
            try:
                # 使用故障转移功能处理请求
                request_id = await router_service.queue_request_with_failover(
                    user_id=999,  # 测试用户ID
                    content=f"[测试 {i+1}] {request_content}",
                    priority="normal"
                )
                
                # 模拟处理请求
                request_info = await router_service.process_queued_request_with_failover("test_provider")
                
                if request_info:
                    successful_requests += 1
                    test_results["requests"].append({
                        "request_id": request_id,
                        "content": request_content,
                        "status": "success",
                        "selected_provider": request_info["routing_decision"].selected_provider.value,
                        "confidence": request_info["routing_decision"].confidence,
                        "failover_attempts": len(request_info.get("failover_attempts", []))
                    })
                else:
                    failed_requests += 1
                    test_results["requests"].append({
                        "request_id": request_id,
                        "content": request_content,
                        "status": "failed",
                        "error": "No available providers"
                    })
                    
            except Exception as e:
                failed_requests += 1
                test_results["requests"].append({
                    "request_id": f"failed_{i}",
                    "content": request_content,
                    "status": "error",
                    "error": str(e)
                })
        
        # 恢复提供商状态
        if simulate_failures:
            from ...services.ai_router_service import AIProvider
            for provider in AIProvider:
                if provider != AIProvider.CUSTOM:
                    await router_service.manually_mark_provider_status(
                        provider, True, "Restored after testing"
                    )
                    test_results["failover_events"].append({
                        "event": "provider_restored",
                        "provider": provider.value,
                        "reason": "Restored after testing",
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        # 生成测试摘要
        test_results["summary"] = {
            "total_requests": test_requests_count,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": f"{(successful_requests / test_requests_count * 100):.1f}%",
            "failover_events_count": len(test_results["failover_events"]),
            "test_completed_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "message": "故障转移功能测试完成",
            "test_results": test_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"故障转移测试失败: {str(e)}")


@router.get("/failover/statistics", summary="获取故障转移统计")
@with_services(AIRouterService)
async def get_failover_statistics(services: dict) -> Dict[str, Any]:
    """
    获取详细的故障转移统计信息
    
    Returns:
        Dict[str, Any]: 故障转移统计数据
    """
    try:
        router_service = services[AIRouterService]
        
        failover_stats = await router_service.get_failover_statistics()
        health_status = await router_service.get_provider_health_status()
        
        # 计算额外的统计信息
        provider_performance = {}
        for provider_id, health in health_status.items():
            provider_performance[provider_id] = {
                "availability_score": health["success_rate"] if health["is_available"] else 0.0,
                "reliability_grade": "A" if health["success_rate"] > 0.9 else 
                                   "B" if health["success_rate"] > 0.8 else
                                   "C" if health["success_rate"] > 0.7 else "D",
                "status": "healthy" if health["is_available"] and health["success_rate"] > 0.8 else
                         "degraded" if health["is_available"] else "unavailable"
            }
        
        return {
            "success": True,
            "data": {
                "failover_statistics": failover_stats,
                "provider_performance": provider_performance,
                "system_resilience": {
                    "redundancy_level": "high" if failover_stats["available_providers"] >= 3 else
                                       "medium" if failover_stats["available_providers"] >= 2 else "low",
                    "fault_tolerance": f"{failover_stats['availability_rate']:.1%}",
                    "recovery_capability": "automatic" if failover_stats["available_providers"] > 1 else "manual"
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取故障转移统计失败: {str(e)}")