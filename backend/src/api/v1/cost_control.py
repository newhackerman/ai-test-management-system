"""
成本控制API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from ...core.database import get_async_session
from ...core.auth import get_current_user
from ...services.cost_control_service import (
    CostControlService, BudgetPeriod, AlertLevel, 
    CostBudget, UsageQuota, CostAlert
)
from ...schemas.base import ApiResponse
from ...models.user import User

router = APIRouter()


@router.get("/summary", response_model=ApiResponse)
async def get_cost_summary(
    period: str = Query("daily", description="统计周期: daily, weekly, monthly, yearly"),
    provider: Optional[str] = Query(None, description="特定AI提供商"),
    user_id: Optional[int] = Query(None, description="特定用户ID"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取成本摘要"""
    try:
        cost_control = CostControlService(db)
        
        # 转换周期枚举
        period_enum = {
            "daily": BudgetPeriod.DAILY,
            "weekly": BudgetPeriod.WEEKLY,
            "monthly": BudgetPeriod.MONTHLY,
            "yearly": BudgetPeriod.YEARLY
        }.get(period, BudgetPeriod.DAILY)
        
        # 权限检查：普通用户只能查看自己的数据
        if not current_user.is_admin and user_id != current_user.id:
            user_id = current_user.id
        
        summary = await cost_control.get_cost_summary(period_enum, provider, user_id)
        
        return ApiResponse(
            success=True,
            data=summary,
            message="成本摘要获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取成本摘要失败: {str(e)}")


@router.get("/alerts", response_model=ApiResponse)
async def get_cost_alerts(
    level: Optional[str] = Query(None, description="告警级别: info, warning, critical, emergency"),
    limit: int = Query(100, description="返回数量限制"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取成本告警"""
    try:
        cost_control = CostControlService(db)
        
        # 转换告警级别
        level_enum = None
        if level:
            level_enum = {
                "info": AlertLevel.INFO,
                "warning": AlertLevel.WARNING,
                "critical": AlertLevel.CRITICAL,
                "emergency": AlertLevel.EMERGENCY
            }.get(level.lower())
        
        alerts = cost_control.get_alerts(level_enum, limit)
        
        # 转换为字典格式并过滤用户权限
        alert_data = []
        for alert in alerts:
            # 普通用户只能看到自己的告警
            if not current_user.is_admin and alert.user_id and alert.user_id != current_user.id:
                continue
                
            alert_data.append({
                "alert_id": alert.alert_id,
                "level": alert.level.value,
                "message": alert.message,
                "budget_id": alert.budget_id,
                "quota_id": alert.quota_id,
                "provider": alert.provider,
                "user_id": alert.user_id,
                "current_usage": float(alert.current_usage) if alert.current_usage else None,
                "limit": float(alert.limit) if alert.limit else None,
                "percentage": alert.percentage,
                "timestamp": alert.timestamp.isoformat() if alert.timestamp else None
            })
        
        return ApiResponse(
            success=True,
            data=alert_data,
            message="成本告警获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取成本告警失败: {str(e)}")


@router.post("/budgets", response_model=ApiResponse)
async def create_budget(
    budget_data: Dict[str, Any],
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """创建预算配置（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足")
        
        cost_control = CostControlService(db)
        
        # 创建预算对象
        budget = CostBudget(
            budget_id=budget_data["budget_id"],
            name=budget_data["name"],
            period=BudgetPeriod(budget_data["period"]),
            amount=Decimal(str(budget_data["amount"])),
            currency=budget_data.get("currency", "USD"),
            providers=budget_data.get("providers", []),
            users=budget_data.get("users", []),
            departments=budget_data.get("departments", []),
            warning_threshold=budget_data.get("warning_threshold", 0.8),
            critical_threshold=budget_data.get("critical_threshold", 0.9),
            auto_disable_on_exceed=budget_data.get("auto_disable_on_exceed", True),
            allow_overage=budget_data.get("allow_overage", False),
            overage_limit=budget_data.get("overage_limit", 0.1)
        )
        
        cost_control.add_budget(budget)
        
        return ApiResponse(
            success=True,
            data={"budget_id": budget.budget_id},
            message="预算配置创建成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建预算配置失败: {str(e)}")


@router.post("/quotas", response_model=ApiResponse)
async def create_quota(
    quota_data: Dict[str, Any],
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """创建配额配置（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足")
        
        cost_control = CostControlService(db)
        
        # 创建配额对象
        quota = UsageQuota(
            quota_id=quota_data["quota_id"],
            name=quota_data["name"],
            period=BudgetPeriod(quota_data["period"]),
            token_limit=quota_data.get("token_limit"),
            request_limit=quota_data.get("request_limit"),
            providers=quota_data.get("providers", []),
            users=quota_data.get("users", []),
            departments=quota_data.get("departments", []),
            auto_reset=quota_data.get("auto_reset", True),
            grace_period_minutes=quota_data.get("grace_period_minutes", 60)
        )
        
        cost_control.add_quota(quota)
        
        return ApiResponse(
            success=True,
            data={"quota_id": quota.quota_id},
            message="配额配置创建成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建配额配置失败: {str(e)}")


@router.delete("/budgets/{budget_id}", response_model=ApiResponse)
async def delete_budget(
    budget_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """删除预算配置（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足")
        
        cost_control = CostControlService(db)
        
        success = cost_control.remove_budget(budget_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="预算配置不存在")
        
        return ApiResponse(
            success=True,
            data={"budget_id": budget_id},
            message="预算配置删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除预算配置失败: {str(e)}")


@router.delete("/quotas/{quota_id}", response_model=ApiResponse)
async def delete_quota(
    quota_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """删除配额配置（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足")
        
        cost_control = CostControlService(db)
        
        success = cost_control.remove_quota(quota_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="配额配置不存在")
        
        return ApiResponse(
            success=True,
            data={"quota_id": quota_id},
            message="配额配置删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除配额配置失败: {str(e)}")


@router.post("/check", response_model=ApiResponse)
async def check_cost_limits(
    check_data: Dict[str, Any],
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """检查成本和配额限制"""
    try:
        cost_control = CostControlService(db)
        
        provider = check_data["provider"]
        estimated_cost = Decimal(str(check_data["estimated_cost"]))
        estimated_tokens = check_data.get("estimated_tokens", 1000)
        user_id = check_data.get("user_id", current_user.id)
        
        # 权限检查：普通用户只能检查自己的限制
        if not current_user.is_admin and user_id != current_user.id:
            user_id = current_user.id
        
        # 检查预算限制
        budget_allowed, budget_alerts = await cost_control.check_budget_limits(
            provider, user_id, estimated_cost
        )
        
        # 检查配额限制
        quota_allowed, quota_alerts = await cost_control.check_usage_quotas(
            provider, user_id, estimated_tokens
        )
        
        all_alerts = budget_alerts + quota_alerts
        allowed = budget_allowed and quota_allowed
        
        # 转换告警为字典格式
        alert_data = []
        for alert in all_alerts:
            alert_data.append({
                "alert_id": alert.alert_id,
                "level": alert.level.value,
                "message": alert.message,
                "budget_id": alert.budget_id,
                "quota_id": alert.quota_id,
                "provider": alert.provider,
                "user_id": alert.user_id,
                "current_usage": float(alert.current_usage) if alert.current_usage else None,
                "limit": float(alert.limit) if alert.limit else None,
                "percentage": alert.percentage,
                "timestamp": alert.timestamp.isoformat() if alert.timestamp else None
            })
        
        return ApiResponse(
            success=True,
            data={
                "allowed": allowed,
                "budget_allowed": budget_allowed,
                "quota_allowed": quota_allowed,
                "alerts": alert_data
            },
            message="成本限制检查完成"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查成本限制失败: {str(e)}")


@router.post("/usage", response_model=ApiResponse)
async def record_usage(
    usage_data: Dict[str, Any],
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """记录使用情况"""
    try:
        cost_control = CostControlService(db)
        
        provider = usage_data["provider"]
        user_id = usage_data.get("user_id", current_user.id)
        input_tokens = usage_data["input_tokens"]
        output_tokens = usage_data["output_tokens"]
        cost = Decimal(str(usage_data["cost"]))
        response_time = usage_data["response_time"]
        success = usage_data.get("success", True)
        
        # 权限检查：普通用户只能记录自己的使用情况
        if not current_user.is_admin and user_id != current_user.id:
            user_id = current_user.id
        
        await cost_control.record_usage(
            provider, user_id, input_tokens, output_tokens,
            cost, response_time, success
        )
        
        return ApiResponse(
            success=True,
            data={"recorded": True},
            message="使用情况记录成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录使用情况失败: {str(e)}")


@router.delete("/alerts", response_model=ApiResponse)
async def clear_alerts(
    before: Optional[str] = Query(None, description="清除此时间之前的告警 (ISO格式)"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """清除告警历史（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足")
        
        cost_control = CostControlService(db)
        
        before_datetime = None
        if before:
            before_datetime = datetime.fromisoformat(before.replace('Z', '+00:00'))
        
        cleared_count = cost_control.clear_alerts(before_datetime)
        
        return ApiResponse(
            success=True,
            data={"cleared_count": cleared_count},
            message=f"成功清除 {cleared_count} 条告警记录"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除告警失败: {str(e)}")


@router.get("/budgets", response_model=ApiResponse)
async def list_budgets(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取预算配置列表（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足")
        
        cost_control = CostControlService(db)
        
        budgets_data = []
        for budget_id, budget in cost_control.budgets.items():
            budgets_data.append({
                "budget_id": budget.budget_id,
                "name": budget.name,
                "period": budget.period.value,
                "amount": float(budget.amount),
                "currency": budget.currency,
                "providers": budget.providers,
                "users": budget.users,
                "departments": budget.departments,
                "warning_threshold": budget.warning_threshold,
                "critical_threshold": budget.critical_threshold,
                "auto_disable_on_exceed": budget.auto_disable_on_exceed,
                "allow_overage": budget.allow_overage,
                "overage_limit": budget.overage_limit
            })
        
        return ApiResponse(
            success=True,
            data=budgets_data,
            message="预算配置列表获取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预算配置列表失败: {str(e)}")


@router.get("/quotas", response_model=ApiResponse)
async def list_quotas(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取配额配置列表（仅管理员）"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足")
        
        cost_control = CostControlService(db)
        
        quotas_data = []
        for quota_id, quota in cost_control.quotas.items():
            quotas_data.append({
                "quota_id": quota.quota_id,
                "name": quota.name,
                "period": quota.period.value,
                "token_limit": quota.token_limit,
                "request_limit": quota.request_limit,
                "providers": quota.providers,
                "users": quota.users,
                "departments": quota.departments,
                "auto_reset": quota.auto_reset,
                "grace_period_minutes": quota.grace_period_minutes
            })
        
        return ApiResponse(
            success=True,
            data=quotas_data,
            message="配额配置列表获取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配额配置列表失败: {str(e)}")


@router.get("/dashboard", response_model=ApiResponse)
async def get_cost_dashboard(
    period: str = Query("daily", description="统计周期: daily, weekly, monthly"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取成本监控仪表板数据"""
    try:
        cost_control = CostControlService(db)
        
        # 转换周期枚举
        period_enum = {
            "daily": BudgetPeriod.DAILY,
            "weekly": BudgetPeriod.WEEKLY,
            "monthly": BudgetPeriod.MONTHLY,
            "yearly": BudgetPeriod.YEARLY
        }.get(period, BudgetPeriod.DAILY)
        
        # 获取仪表板数据
        dashboard_data = await cost_control.get_dashboard_data(period_enum, current_user.id, current_user.is_admin)
        
        return ApiResponse(
            success=True,
            data=dashboard_data,
            message="成本监控仪表板数据获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表板数据失败: {str(e)}")


@router.get("/trends", response_model=ApiResponse)
async def get_cost_trends(
    days: int = Query(30, description="统计天数"),
    provider: Optional[str] = Query(None, description="特定AI提供商"),
    user_id: Optional[int] = Query(None, description="特定用户ID"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取成本趋势数据"""
    try:
        cost_control = CostControlService(db)
        
        # 权限检查：普通用户只能查看自己的数据
        if not current_user.is_admin and user_id != current_user.id:
            user_id = current_user.id
        
        trends_data = await cost_control.get_cost_trends(days, provider, user_id)
        
        return ApiResponse(
            success=True,
            data=trends_data,
            message="成本趋势数据获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取成本趋势失败: {str(e)}")


@router.get("/statistics", response_model=ApiResponse)
async def get_usage_statistics(
    period: str = Query("daily", description="统计周期: daily, weekly, monthly"),
    group_by: str = Query("provider", description="分组方式: provider, user, model"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取使用统计数据"""
    try:
        cost_control = CostControlService(db)
        
        # 转换周期枚举
        period_enum = {
            "daily": BudgetPeriod.DAILY,
            "weekly": BudgetPeriod.WEEKLY,
            "monthly": BudgetPeriod.MONTHLY,
            "yearly": BudgetPeriod.YEARLY
        }.get(period, BudgetPeriod.DAILY)
        
        statistics_data = await cost_control.get_usage_statistics(
            period_enum, group_by, current_user.id, current_user.is_admin
        )
        
        return ApiResponse(
            success=True,
            data=statistics_data,
            message="使用统计数据获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取使用统计失败: {str(e)}")


@router.get("/budget-usage", response_model=ApiResponse)
async def get_budget_usage(
    budget_id: Optional[str] = Query(None, description="特定预算ID"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取预算使用情况"""
    try:
        cost_control = CostControlService(db)
        
        budget_usage_data = await cost_control.get_budget_usage_data(
            budget_id, current_user.id, current_user.is_admin
        )
        
        return ApiResponse(
            success=True,
            data=budget_usage_data,
            message="预算使用情况获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取预算使用情况失败: {str(e)}")


@router.get("/quota-usage", response_model=ApiResponse)
async def get_quota_usage(
    quota_id: Optional[str] = Query(None, description="特定配额ID"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取配额使用情况"""
    try:
        cost_control = CostControlService(db)
        
        quota_usage_data = await cost_control.get_quota_usage_data(
            quota_id, current_user.id, current_user.is_admin
        )
        
        return ApiResponse(
            success=True,
            data=quota_usage_data,
            message="配额使用情况获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配额使用情况失败: {str(e)}")


@router.get("/enhanced-statistics/time-series", response_model=ApiResponse)
async def get_time_series_statistics(
    time_range: str = Query("24h", description="时间范围: 24h, 7d, 30d, 90d"),
    granularity: str = Query("hour", description="时间粒度: hour, day, week"),
    provider: Optional[str] = Query(None, description="特定AI提供商"),
    user_id: Optional[int] = Query(None, description="特定用户ID"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取时间序列使用统计"""
    try:
        from ...services.enhanced_usage_statistics_service import EnhancedUsageStatisticsService
        
        # 权限检查：普通用户只能查看自己的数据
        if not current_user.is_admin and user_id and user_id != current_user.id:
            user_id = current_user.id
        elif not current_user.is_admin and not user_id:
            user_id = current_user.id
        
        stats_service = EnhancedUsageStatisticsService(db)
        time_series_data = await stats_service.get_time_series_data(
            time_range=time_range,
            granularity=granularity,
            provider=provider,
            user_id=user_id
        )
        
        # 转换为字典格式
        result_data = []
        for point in time_series_data:
            result_data.append({
                "timestamp": point.timestamp.isoformat(),
                "requests": point.requests,
                "tokens": point.tokens,
                "cost": point.cost,
                "response_time": point.response_time,
                "success_rate": point.success_rate,
                "concurrent_users": point.concurrent_users,
                "error_count": point.error_count
            })
        
        return ApiResponse(
            success=True,
            data={
                "time_range": time_range,
                "granularity": granularity,
                "data_points": len(result_data),
                "time_series": result_data
            },
            message="时间序列统计获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取时间序列统计失败: {str(e)}")


@router.get("/enhanced-statistics/model-metrics", response_model=ApiResponse)
async def get_model_usage_metrics(
    period: str = Query("daily", description="统计周期: daily, weekly, monthly"),
    limit: int = Query(20, description="返回数量限制"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取模型使用指标"""
    try:
        from ...services.enhanced_usage_statistics_service import EnhancedUsageStatisticsService
        
        stats_service = EnhancedUsageStatisticsService(db)
        model_metrics = await stats_service.get_model_usage_metrics(
            period=period,
            limit=limit
        )
        
        # 转换为字典格式
        result_data = []
        for metric in model_metrics:
            result_data.append({
                "model": metric.model,
                "provider": metric.provider,
                "requests": metric.requests,
                "tokens": metric.tokens,
                "cost": metric.cost,
                "avg_response_time": metric.avg_response_time,
                "success_rate": metric.success_rate,
                "popularity_score": metric.popularity_score,
                "avg_tokens_per_request": metric.avg_tokens_per_request,
                "peak_hour": metric.peak_hour,
                "error_rate": metric.error_rate
            })
        
        return ApiResponse(
            success=True,
            data={
                "period": period,
                "total_models": len(result_data),
                "model_metrics": result_data
            },
            message="模型使用指标获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型使用指标失败: {str(e)}")


@router.get("/enhanced-statistics/user-activity", response_model=ApiResponse)
async def get_user_activity_metrics(
    period: str = Query("daily", description="统计周期: daily, weekly, monthly"),
    limit: int = Query(50, description="返回数量限制"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取用户活动指标"""
    try:
        from ...services.enhanced_usage_statistics_service import EnhancedUsageStatisticsService
        
        # 权限检查：普通用户只能查看自己的数据
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="权限不足，只有管理员可以查看用户活动统计")
        
        stats_service = EnhancedUsageStatisticsService(db)
        user_metrics = await stats_service.get_user_activity_metrics(
            period=period,
            limit=limit
        )
        
        # 转换为字典格式
        result_data = []
        for metric in user_metrics:
            result_data.append({
                "user_id": metric.user_id,
                "username": metric.username,
                "department": metric.department,
                "total_requests": metric.total_requests,
                "total_tokens": metric.total_tokens,
                "total_cost": metric.total_cost,
                "avg_session_duration": metric.avg_session_duration,
                "most_used_model": metric.most_used_model,
                "activity_score": metric.activity_score,
                "last_active": metric.last_active.isoformat() if metric.last_active else None,
                "favorite_providers": metric.favorite_providers
            })
        
        return ApiResponse(
            success=True,
            data={
                "period": period,
                "total_users": len(result_data),
                "user_metrics": result_data
            },
            message="用户活动指标获取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户活动指标失败: {str(e)}")


@router.get("/enhanced-statistics/performance", response_model=ApiResponse)
async def get_performance_metrics(
    period: str = Query("daily", description="统计周期: daily, weekly, monthly"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取性能指标"""
    try:
        from ...services.enhanced_usage_statistics_service import EnhancedUsageStatisticsService
        
        stats_service = EnhancedUsageStatisticsService(db)
        performance_metrics = await stats_service.get_performance_metrics(period=period)
        
        result_data = {
            "period": performance_metrics.period,
            "avg_response_time": performance_metrics.avg_response_time,
            "p50_response_time": performance_metrics.p50_response_time,
            "p95_response_time": performance_metrics.p95_response_time,
            "p99_response_time": performance_metrics.p99_response_time,
            "throughput": performance_metrics.throughput,
            "error_rate": performance_metrics.error_rate,
            "availability": performance_metrics.availability,
            "peak_concurrent_users": performance_metrics.peak_concurrent_users,
            "total_uptime": performance_metrics.total_uptime
        }
        
        return ApiResponse(
            success=True,
            data=result_data,
            message="性能指标获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")


@router.get("/enhanced-statistics/usage-patterns", response_model=ApiResponse)
async def get_usage_patterns(
    pattern_type: str = Query("hourly", description="模式类型: hourly, daily, weekly"),
    period: str = Query("weekly", description="分析周期: weekly, monthly, quarterly"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """获取使用模式分析"""
    try:
        from ...services.enhanced_usage_statistics_service import EnhancedUsageStatisticsService
        
        stats_service = EnhancedUsageStatisticsService(db)
        usage_pattern = await stats_service.get_usage_patterns(
            pattern_type=pattern_type,
            period=period
        )
        
        result_data = {
            "pattern_type": usage_pattern.pattern_type,
            "peak_hours": usage_pattern.peak_hours,
            "low_usage_hours": usage_pattern.low_usage_hours,
            "usage_distribution": usage_pattern.usage_distribution,
            "seasonal_trends": usage_pattern.seasonal_trends
        }
        
        return ApiResponse(
            success=True,
            data=result_data,
            message="使用模式分析获取成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取使用模式分析失败: {str(e)}")


@router.post("/enhanced-statistics/export", response_model=ApiResponse)
async def export_usage_statistics(
    export_request: Dict[str, Any],
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """导出使用统计数据"""
    try:
        from ...services.enhanced_usage_statistics_service import EnhancedUsageStatisticsService
        
        format_type = export_request.get("format", "json")
        period = export_request.get("period", "monthly")
        include_details = export_request.get("include_details", True)
        
        # 权限检查：普通用户只能导出自己的数据
        if not current_user.is_admin and include_details:
            include_details = False
        
        stats_service = EnhancedUsageStatisticsService(db)
        export_data = await stats_service.export_usage_data(
            format_type=format_type,
            period=period,
            include_details=include_details
        )
        
        return ApiResponse(
            success=True,
            data=export_data,
            message="使用统计数据导出成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出使用统计数据失败: {str(e)}")