"""
健康状态监控API
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from ...core.database import get_db
from ...decorators.permission import require_permission
from ...services.ai_model_config_service import AIModelConfigService
from ...services.simple_health_check_service import EnhancedHealthCheckService, HealthCheckConfig
from ...schemas.ai_model_config import AIProviderEnum
from ...schemas.health_monitoring import (
    HealthDashboardResponse,
    HealthMetricsResponse,
    HealthAlertResponse,
    HealthTrendResponse,
    SystemHealthResponse,
    HealthCheckScheduleRequest,
    HealthCheckScheduleResponse
)

router = APIRouter()

# 全局健康检查服务实例
health_service = EnhancedHealthCheckService()


def get_ai_model_config_service() -> AIModelConfigService:
    """获取AI模型配置服务实例"""
    from ...services.simple_health_check_service import HealthCheckService
    simple_health_service = HealthCheckService()
    return AIModelConfigService(simple_health_service)


@router.get("/dashboard", response_model=HealthDashboardResponse)
async def get_health_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    获取健康监控仪表板数据
    
    需要权限: ai_config_view
    """
    try:
        # 获取所有模型配置
        configs = await service.get_model_configs(db, enabled_only=True)
        
        # 获取健康指标
        all_metrics = health_service.get_all_metrics()
        
        # 统计健康状态
        total_models = len(configs.items)
        healthy_models = 0
        unhealthy_models = 0
        unknown_models = 0
        
        model_status = []
        
        for config in configs.items:
            metrics = all_metrics.get(config.id)
            
            if metrics:
                is_healthy = health_service.is_model_healthy(config.id)
                if is_healthy:
                    status = "HEALTHY"
                    healthy_models += 1
                else:
                    status = "UNHEALTHY"
                    unhealthy_models += 1
            else:
                status = "UNKNOWN"
                unknown_models += 1
            
            model_status.append({
                "config_id": config.id,
                "provider": config.provider,
                "model_name": config.model_name,
                "display_name": config.display_name,
                "status": status,
                "last_check": metrics.last_check if metrics else None,
                "response_time": metrics.response_time if metrics else None,
                "success_rate": metrics.success_rate if metrics else None,
                "consecutive_failures": metrics.consecutive_failures if metrics else 0
            })
        
        # 计算系统整体健康度
        if total_models > 0:
            system_health_score = (healthy_models / total_models) * 100
        else:
            system_health_score = 0
        
        return HealthDashboardResponse(
            total_models=total_models,
            healthy_models=healthy_models,
            unhealthy_models=unhealthy_models,
            unknown_models=unknown_models,
            system_health_score=system_health_score,
            model_status=model_status,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取健康监控仪表板失败: {str(e)}")


@router.get("/metrics/{config_id}", response_model=HealthMetricsResponse)
async def get_model_health_metrics(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_view")),
    service: AIModelConfigService = Depends(get_ai_model_config_service)
):
    """
    获取特定模型的健康指标
    
    需要权限: ai_config_view
    """
    try:
        # 验证模型配置存在
        config = await service.get_model_config(db, config_id)
        
        # 获取健康指标
        metrics = health_service.get_health_metrics(config_id)
        
        if not metrics:
            # 如果没有指标，执行一次健康检查
            from ...models.ai_model_config import AIModelConfig
            from sqlalchemy import select
            
            query = select(AIModelConfig).where(AIModelConfig.id == config_id)
            result = await db.execute(query)
            model_config = result.scalar_one_or_none()
            
            if model_config:
                await health_service.check_ai_model_health(model_config)
                metrics = health_service.get_health_metrics(config_id)
        
        if not metrics:
            raise HTTPException(status_code=404, detail="健康指标不存在")
        
        return HealthMetricsResponse(
            config_id=config_id,
            provider=config.provider,
            model_name=config.model_name,
            display_name=config.display_name,
            response_time=metrics.response_time,
            success_rate=metrics.success_rate,
            error_rate=metrics.error_rate,
            availability=metrics.availability,
            throughput=metrics.throughput,
            consecutive_failures=metrics.consecutive_failures,
            total_checks=metrics.total_checks,
            successful_checks=metrics.successful_checks,
            failed_checks=metrics.failed_checks,
            last_check=metrics.last_check,
            is_healthy=health_service.is_model_healthy(config_id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取健康指标失败: {str(e)}")


@router.get("/alerts", response_model=List[HealthAlertResponse])
async def get_health_alerts(
    severity: Optional[str] = Query(None, description="告警严重程度"),
    provider: Optional[AIProviderEnum] = Query(None, description="服务提供商"),
    limit: int = Query(50, ge=1, le=200, description="限制数量"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_view"))
):
    """
    获取健康告警列表
    
    需要权限: ai_config_view
    """
    try:
        alerts = []
        all_metrics = health_service.get_all_metrics()
        
        # 获取所有模型配置用于匹配
        from ...models.ai_model_config import AIModelConfig
        from sqlalchemy import select
        
        query = select(AIModelConfig)
        if provider:
            query = query.where(AIModelConfig.provider == provider.value)
        
        result = await db.execute(query)
        configs = result.scalars().all()
        
        config_map = {config.id: config for config in configs}
        
        for config_id, metrics in all_metrics.items():
            config = config_map.get(config_id)
            if not config:
                continue
            
            # 检查各种告警条件
            alert_conditions = []
            
            # 连续失败告警
            if metrics.consecutive_failures >= 3:
                alert_conditions.append({
                    "type": "CONSECUTIVE_FAILURES",
                    "severity": "CRITICAL" if metrics.consecutive_failures >= 5 else "WARNING",
                    "message": f"连续失败 {metrics.consecutive_failures} 次",
                    "value": metrics.consecutive_failures
                })
            
            # 响应时间告警
            if metrics.response_time > 10.0:
                alert_conditions.append({
                    "type": "HIGH_RESPONSE_TIME",
                    "severity": "CRITICAL",
                    "message": f"响应时间过长: {metrics.response_time:.2f}秒",
                    "value": metrics.response_time
                })
            elif metrics.response_time > 5.0:
                alert_conditions.append({
                    "type": "HIGH_RESPONSE_TIME",
                    "severity": "WARNING",
                    "message": f"响应时间较长: {metrics.response_time:.2f}秒",
                    "value": metrics.response_time
                })
            
            # 成功率告警
            if metrics.success_rate < 0.5:
                alert_conditions.append({
                    "type": "LOW_SUCCESS_RATE",
                    "severity": "CRITICAL",
                    "message": f"成功率过低: {metrics.success_rate:.1%}",
                    "value": metrics.success_rate
                })
            elif metrics.success_rate < 0.8:
                alert_conditions.append({
                    "type": "LOW_SUCCESS_RATE",
                    "severity": "WARNING",
                    "message": f"成功率较低: {metrics.success_rate:.1%}",
                    "value": metrics.success_rate
                })
            
            # 可用性告警
            if metrics.availability < 0.7:
                alert_conditions.append({
                    "type": "LOW_AVAILABILITY",
                    "severity": "CRITICAL",
                    "message": f"可用性过低: {metrics.availability:.1%}",
                    "value": metrics.availability
                })
            elif metrics.availability < 0.9:
                alert_conditions.append({
                    "type": "LOW_AVAILABILITY",
                    "severity": "WARNING",
                    "message": f"可用性较低: {metrics.availability:.1%}",
                    "value": metrics.availability
                })
            
            # 创建告警记录
            for condition in alert_conditions:
                if severity and condition["severity"] != severity.upper():
                    continue
                
                alerts.append(HealthAlertResponse(
                    config_id=config_id,
                    provider=config.provider,
                    model_name=config.model_name,
                    display_name=config.display_name,
                    alert_type=condition["type"],
                    severity=condition["severity"],
                    message=condition["message"],
                    value=condition["value"],
                    created_at=metrics.last_check,
                    is_active=True
                ))
        
        # 按严重程度和时间排序
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        alerts.sort(key=lambda x: (severity_order.get(x.severity, 3), x.created_at), reverse=True)
        
        return alerts[:limit]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取健康告警失败: {str(e)}")


@router.get("/trends", response_model=List[HealthTrendResponse])
async def get_health_trends(
    config_id: Optional[int] = Query(None, description="模型配置ID"),
    provider: Optional[AIProviderEnum] = Query(None, description="服务提供商"),
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_view"))
):
    """
    获取健康趋势数据
    
    需要权限: ai_config_view
    """
    try:
        # 这里应该从数据库或时序数据库中获取历史数据
        # 为了演示，我们生成一些模拟数据
        
        trends = []
        current_time = datetime.utcnow()
        
        # 如果指定了config_id，只返回该模型的趋势
        if config_id:
            config_ids = [config_id]
        else:
            # 获取所有模型配置
            from ...models.ai_model_config import AIModelConfig
            from sqlalchemy import select
            
            query = select(AIModelConfig.id, AIModelConfig.provider, AIModelConfig.model_name, AIModelConfig.display_name)
            if provider:
                query = query.where(AIModelConfig.provider == provider.value)
            
            result = await db.execute(query)
            configs = result.all()
            config_ids = [config.id for config in configs]
        
        # 为每个配置生成趋势数据
        for cid in config_ids:
            metrics = health_service.get_health_metrics(cid)
            
            # 生成过去几小时的模拟数据点
            data_points = []
            for i in range(hours):
                timestamp = current_time - timedelta(hours=hours-i)
                
                # 基于当前指标生成历史数据（模拟）
                if metrics:
                    base_response_time = metrics.response_time
                    base_success_rate = metrics.success_rate
                    base_availability = metrics.availability
                else:
                    base_response_time = 2.0
                    base_success_rate = 0.95
                    base_availability = 0.98
                
                # 添加一些随机变化
                import random
                response_time = max(0.1, base_response_time + random.uniform(-0.5, 0.5))
                success_rate = max(0.0, min(1.0, base_success_rate + random.uniform(-0.1, 0.1)))
                availability = max(0.0, min(1.0, base_availability + random.uniform(-0.05, 0.05)))
                
                data_points.append({
                    "timestamp": timestamp,
                    "response_time": response_time,
                    "success_rate": success_rate,
                    "availability": availability,
                    "error_rate": 1.0 - success_rate
                })
            
            # 获取配置信息
            from ...models.ai_model_config import AIModelConfig
            from sqlalchemy import select
            
            query = select(AIModelConfig).where(AIModelConfig.id == cid)
            result = await db.execute(query)
            config = result.scalar_one_or_none()
            
            if config:
                trends.append(HealthTrendResponse(
                    config_id=cid,
                    provider=config.provider,
                    model_name=config.model_name,
                    display_name=config.display_name,
                    data_points=data_points,
                    period_hours=hours
                ))
        
        return trends
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取健康趋势失败: {str(e)}")


@router.get("/system", response_model=SystemHealthResponse)
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_view"))
):
    """
    获取系统整体健康状态
    
    需要权限: ai_config_view
    """
    try:
        # 获取所有启用的模型配置
        from ...models.ai_model_config import AIModelConfig
        from sqlalchemy import select, func
        
        # 统计模型配置
        total_query = select(func.count(AIModelConfig.id))
        enabled_query = select(func.count(AIModelConfig.id)).where(AIModelConfig.is_enabled == True)
        
        total_result = await db.execute(total_query)
        enabled_result = await db.execute(enabled_query)
        
        total_models = total_result.scalar()
        enabled_models = enabled_result.scalar()
        
        # 获取健康指标
        all_metrics = health_service.get_all_metrics()
        
        healthy_count = 0
        unhealthy_count = 0
        total_response_time = 0.0
        total_success_rate = 0.0
        total_availability = 0.0
        metrics_count = 0
        
        for config_id, metrics in all_metrics.items():
            if health_service.is_model_healthy(config_id):
                healthy_count += 1
            else:
                unhealthy_count += 1
            
            total_response_time += metrics.response_time
            total_success_rate += metrics.success_rate
            total_availability += metrics.availability
            metrics_count += 1
        
        # 计算平均值
        avg_response_time = total_response_time / metrics_count if metrics_count > 0 else 0.0
        avg_success_rate = total_success_rate / metrics_count if metrics_count > 0 else 0.0
        avg_availability = total_availability / metrics_count if metrics_count > 0 else 0.0
        
        # 计算系统健康分数
        if enabled_models > 0:
            health_score = (healthy_count / enabled_models) * 100
        else:
            health_score = 0.0
        
        # 确定系统状态
        if health_score >= 90:
            system_status = "HEALTHY"
        elif health_score >= 70:
            system_status = "WARNING"
        else:
            system_status = "CRITICAL"
        
        # 统计各提供商状态
        provider_stats = {}
        
        query = select(AIModelConfig).where(AIModelConfig.is_enabled == True)
        result = await db.execute(query)
        configs = result.scalars().all()
        
        for config in configs:
            provider = config.provider
            if provider not in provider_stats:
                provider_stats[provider] = {
                    "total": 0,
                    "healthy": 0,
                    "unhealthy": 0
                }
            
            provider_stats[provider]["total"] += 1
            
            if health_service.is_model_healthy(config.id):
                provider_stats[provider]["healthy"] += 1
            else:
                provider_stats[provider]["unhealthy"] += 1
        
        return SystemHealthResponse(
            system_status=system_status,
            health_score=health_score,
            total_models=total_models,
            enabled_models=enabled_models,
            healthy_models=healthy_count,
            unhealthy_models=unhealthy_count,
            avg_response_time=avg_response_time,
            avg_success_rate=avg_success_rate,
            avg_availability=avg_availability,
            provider_stats=provider_stats,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统健康状态失败: {str(e)}")


@router.post("/schedule", response_model=HealthCheckScheduleResponse)
async def schedule_health_check(
    schedule_request: HealthCheckScheduleRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_config_manage"))
):
    """
    调度健康检查任务
    
    需要权限: ai_config_manage
    """
    try:
        # 在后台任务中执行健康检查
        if schedule_request.config_ids:
            # 检查指定的模型
            for config_id in schedule_request.config_ids:
                background_tasks.add_task(_perform_scheduled_health_check, db, config_id)
        else:
            # 检查所有启用的模型
            background_tasks.add_task(_perform_batch_health_check, db)
        
        return HealthCheckScheduleResponse(
            scheduled=True,
            config_ids=schedule_request.config_ids,
            scheduled_at=datetime.utcnow(),
            message="健康检查任务已调度"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调度健康检查失败: {str(e)}")


async def _perform_scheduled_health_check(db: AsyncSession, config_id: int):
    """执行调度的健康检查"""
    try:
        from ...models.ai_model_config import AIModelConfig
        from sqlalchemy import select
        
        query = select(AIModelConfig).where(AIModelConfig.id == config_id)
        result = await db.execute(query)
        config = result.scalar_one_or_none()
        
        if config:
            await health_service.check_ai_model_health(config)
            
    except Exception as e:
        logger.error(f"Scheduled health check failed for config {config_id}: {str(e)}")


async def _perform_batch_health_check(db: AsyncSession):
    """执行批量健康检查"""
    try:
        from ...models.ai_model_config import AIModelConfig
        from sqlalchemy import select
        
        query = select(AIModelConfig).where(AIModelConfig.is_enabled == True)
        result = await db.execute(query)
        configs = result.scalars().all()
        
        for config in configs:
            try:
                await health_service.check_ai_model_health(config)
            except Exception as e:
                logger.error(f"Health check failed for config {config.id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Batch health check failed: {str(e)}")


# 启动健康监控服务
@router.on_event("startup")
async def startup_health_monitoring():
    """启动时初始化健康监控"""
    await health_service.start_monitoring()


@router.on_event("shutdown")
async def shutdown_health_monitoring():
    """关闭时停止健康监控"""
    await health_service.stop_monitoring()