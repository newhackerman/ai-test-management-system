"""
成本控制服务 - AI服务成本监控和控制
"""
import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.orm import selectinload

from ..models.ai_model_config import AIModelConfig
from ..models.ai_usage_stats import AIUsageStats, AISystemStats
from ..core.config import get_settings
from ..core.exceptions import QuotaExceededException, BudgetExceededException

logger = logging.getLogger(__name__)
settings = get_settings()


class BudgetPeriod(Enum):
    """预算周期枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class CostBudget:
    """成本预算配置"""
    budget_id: str
    name: str
    period: BudgetPeriod
    amount: Decimal
    currency: str = "USD"
    providers: List[str] = None  # 适用的AI提供商，None表示所有
    users: List[int] = None      # 适用的用户，None表示所有
    departments: List[str] = None # 适用的部门，None表示所有
    
    # 告警阈值
    warning_threshold: float = 0.8   # 80%时告警
    critical_threshold: float = 0.9  # 90%时严重告警
    
    # 控制策略
    auto_disable_on_exceed: bool = True  # 超预算时自动禁用
    allow_overage: bool = False          # 是否允许超支
    overage_limit: float = 0.1           # 允许超支比例
    
    def __post_init__(self):
        if self.providers is None:
            self.providers = []
        if self.users is None:
            self.users = []
        if self.departments is None:
            self.departments = []


@dataclass
class UsageQuota:
    """使用配额配置"""
    quota_id: str
    name: str
    period: BudgetPeriod
    
    # Token配额
    token_limit: int = None
    request_limit: int = None
    
    # 适用范围
    providers: List[str] = None
    users: List[int] = None
    departments: List[str] = None
    
    # 控制策略
    auto_reset: bool = True
    grace_period_minutes: int = 60  # 宽限期
    
    def __post_init__(self):
        if self.providers is None:
            self.providers = []
        if self.users is None:
            self.users = []
        if self.departments is None:
            self.departments = []


@dataclass
class CostAlert:
    """成本告警"""
    alert_id: str
    level: AlertLevel
    message: str
    budget_id: str = None
    quota_id: str = None
    provider: str = None
    user_id: int = None
    current_usage: Decimal = None
    limit: Decimal = None
    percentage: float = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class CostUsage:
    """成本使用情况"""
    period_start: datetime
    period_end: datetime
    total_cost: Decimal
    total_tokens: int
    total_requests: int
    provider_breakdown: Dict[str, Decimal]
    user_breakdown: Dict[int, Decimal]
    daily_breakdown: Dict[date, Decimal]


class CostControlService:
    """成本控制服务"""
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # 预算配置缓存
        self.budgets: Dict[str, CostBudget] = {}
        self.quotas: Dict[str, UsageQuota] = {}
        
        # 告警历史
        self.alert_history: List[CostAlert] = []
        
        # 成本缓存
        self.cost_cache: Dict[str, CostUsage] = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        # 初始化默认预算和配额
        self._initialize_default_budgets()
        self._initialize_default_quotas()
    
    def _initialize_default_budgets(self):
        """初始化默认预算配置"""
        # 系统级月度预算
        self.budgets["system_monthly"] = CostBudget(
            budget_id="system_monthly",
            name="系统月度预算",
            period=BudgetPeriod.MONTHLY,
            amount=Decimal("1000.00"),
            warning_threshold=0.8,
            critical_threshold=0.9,
            auto_disable_on_exceed=True
        )
        
        # 系统级日预算
        self.budgets["system_daily"] = CostBudget(
            budget_id="system_daily",
            name="系统日预算",
            period=BudgetPeriod.DAILY,
            amount=Decimal("50.00"),
            warning_threshold=0.8,
            critical_threshold=0.9,
            auto_disable_on_exceed=False,
            allow_overage=True,
            overage_limit=0.2
        )
        
        # 用户级日预算
        self.budgets["user_daily"] = CostBudget(
            budget_id="user_daily",
            name="用户日预算",
            period=BudgetPeriod.DAILY,
            amount=Decimal("5.00"),
            warning_threshold=0.8,
            critical_threshold=0.9,
            auto_disable_on_exceed=True
        )
    
    def _initialize_default_quotas(self):
        """初始化默认配额配置"""
        # 系统级日配额
        self.quotas["system_daily"] = UsageQuota(
            quota_id="system_daily",
            name="系统日配额",
            period=BudgetPeriod.DAILY,
            token_limit=1000000,  # 100万tokens
            request_limit=10000,   # 1万请求
            auto_reset=True
        )
        
        # 用户级日配额
        self.quotas["user_daily"] = UsageQuota(
            quota_id="user_daily",
            name="用户日配额",
            period=BudgetPeriod.DAILY,
            token_limit=50000,    # 5万tokens
            request_limit=500,    # 500请求
            auto_reset=True
        )
        
        # 高级用户配额
        self.quotas["premium_user_daily"] = UsageQuota(
            quota_id="premium_user_daily",
            name="高级用户日配额",
            period=BudgetPeriod.DAILY,
            token_limit=200000,   # 20万tokens
            request_limit=2000,   # 2000请求
            auto_reset=True
        )
    
    async def check_budget_limits(self, provider: str, user_id: int, 
                                 estimated_cost: Decimal) -> Tuple[bool, List[CostAlert]]:
        """
        检查预算限制
        
        Args:
            provider: AI服务提供商
            user_id: 用户ID
            estimated_cost: 预估成本
            
        Returns:
            Tuple[bool, List[CostAlert]]: (是否允许请求, 告警列表)
        """
        alerts = []
        allow_request = True
        
        try:
            # 检查系统级预算
            system_alerts, system_allow = await self._check_system_budget(
                provider, estimated_cost
            )
            alerts.extend(system_alerts)
            if not system_allow:
                allow_request = False
            
            # 检查用户级预算
            user_alerts, user_allow = await self._check_user_budget(
                provider, user_id, estimated_cost
            )
            alerts.extend(user_alerts)
            if not user_allow:
                allow_request = False
            
            # 检查提供商级预算
            provider_alerts, provider_allow = await self._check_provider_budget(
                provider, estimated_cost
            )
            alerts.extend(provider_alerts)
            if not provider_allow:
                allow_request = False
            
            return allow_request, alerts
            
        except Exception as e:
            self.logger.error(f"Error checking budget limits: {str(e)}")
            # 出错时采用保守策略，允许请求但记录告警
            error_alert = CostAlert(
                alert_id=f"budget_check_error_{int(datetime.utcnow().timestamp())}",
                level=AlertLevel.WARNING,
                message=f"预算检查出错: {str(e)}",
                provider=provider,
                user_id=user_id
            )
            return True, [error_alert]
    
    async def _check_system_budget(self, provider: str, 
                                  estimated_cost: Decimal) -> Tuple[List[CostAlert], bool]:
        """检查系统级预算"""
        alerts = []
        allow_request = True
        
        for budget_id, budget in self.budgets.items():
            if not budget_id.startswith("system_"):
                continue
            
            if budget.providers and provider not in budget.providers:
                continue
            
            # 获取当前使用情况
            current_usage = await self._get_budget_usage(budget)
            usage_percentage = float(current_usage.total_cost / budget.amount)
            
            # 检查是否会超预算
            projected_usage = current_usage.total_cost + estimated_cost
            projected_percentage = float(projected_usage / budget.amount)
            
            # 生成告警
            if projected_percentage >= budget.critical_threshold:
                alert = CostAlert(
                    alert_id=f"system_budget_critical_{budget_id}_{int(datetime.utcnow().timestamp())}",
                    level=AlertLevel.CRITICAL,
                    message=f"系统预算即将超限: {projected_percentage:.1%} (限制: {budget.critical_threshold:.1%})",
                    budget_id=budget_id,
                    provider=provider,
                    current_usage=projected_usage,
                    limit=budget.amount,
                    percentage=projected_percentage
                )
                alerts.append(alert)
                
                if budget.auto_disable_on_exceed and projected_percentage >= 1.0:
                    if not budget.allow_overage or projected_percentage > (1.0 + budget.overage_limit):
                        allow_request = False
            
            elif projected_percentage >= budget.warning_threshold:
                alert = CostAlert(
                    alert_id=f"system_budget_warning_{budget_id}_{int(datetime.utcnow().timestamp())}",
                    level=AlertLevel.WARNING,
                    message=f"系统预算使用率较高: {projected_percentage:.1%} (警告阈值: {budget.warning_threshold:.1%})",
                    budget_id=budget_id,
                    provider=provider,
                    current_usage=projected_usage,
                    limit=budget.amount,
                    percentage=projected_percentage
                )
                alerts.append(alert)
        
        return alerts, allow_request
    
    async def _check_user_budget(self, provider: str, user_id: int, 
                                estimated_cost: Decimal) -> Tuple[List[CostAlert], bool]:
        """检查用户级预算"""
        alerts = []
        allow_request = True
        
        for budget_id, budget in self.budgets.items():
            if not budget_id.startswith("user_"):
                continue
            
            if budget.providers and provider not in budget.providers:
                continue
            
            if budget.users and user_id not in budget.users:
                continue
            
            # 获取用户当前使用情况
            current_usage = await self._get_user_budget_usage(budget, user_id)
            
            # 检查是否会超预算
            projected_usage = current_usage.total_cost + estimated_cost
            projected_percentage = float(projected_usage / budget.amount)
            
            # 生成告警
            if projected_percentage >= budget.critical_threshold:
                alert = CostAlert(
                    alert_id=f"user_budget_critical_{budget_id}_{user_id}_{int(datetime.utcnow().timestamp())}",
                    level=AlertLevel.CRITICAL,
                    message=f"用户预算即将超限: {projected_percentage:.1%} (限制: {budget.critical_threshold:.1%})",
                    budget_id=budget_id,
                    provider=provider,
                    user_id=user_id,
                    current_usage=projected_usage,
                    limit=budget.amount,
                    percentage=projected_percentage
                )
                alerts.append(alert)
                
                if budget.auto_disable_on_exceed and projected_percentage >= 1.0:
                    if not budget.allow_overage or projected_percentage > (1.0 + budget.overage_limit):
                        allow_request = False
            
            elif projected_percentage >= budget.warning_threshold:
                alert = CostAlert(
                    alert_id=f"user_budget_warning_{budget_id}_{user_id}_{int(datetime.utcnow().timestamp())}",
                    level=AlertLevel.WARNING,
                    message=f"用户预算使用率较高: {projected_percentage:.1%} (警告阈值: {budget.warning_threshold:.1%})",
                    budget_id=budget_id,
                    provider=provider,
                    user_id=user_id,
                    current_usage=projected_usage,
                    limit=budget.amount,
                    percentage=projected_percentage
                )
                alerts.append(alert)
        
        return alerts, allow_request
    
    async def _check_provider_budget(self, provider: str, 
                                   estimated_cost: Decimal) -> Tuple[List[CostAlert], bool]:
        """检查提供商级预算"""
        alerts = []
        allow_request = True
        
        # 检查提供商特定预算
        provider_budget_id = f"provider_{provider}_daily"
        if provider_budget_id in self.budgets:
            budget = self.budgets[provider_budget_id]
            
            # 获取提供商当前使用情况
            current_usage = await self._get_provider_budget_usage(budget, provider)
            
            # 检查是否会超预算
            projected_usage = current_usage.total_cost + estimated_cost
            projected_percentage = float(projected_usage / budget.amount)
            
            # 生成告警
            if projected_percentage >= budget.critical_threshold:
                alert = CostAlert(
                    alert_id=f"provider_budget_critical_{provider}_{int(datetime.utcnow().timestamp())}",
                    level=AlertLevel.CRITICAL,
                    message=f"提供商 {provider} 预算即将超限: {projected_percentage:.1%}",
                    budget_id=provider_budget_id,
                    provider=provider,
                    current_usage=projected_usage,
                    limit=budget.amount,
                    percentage=projected_percentage
                )
                alerts.append(alert)
                
                if budget.auto_disable_on_exceed and projected_percentage >= 1.0:
                    allow_request = False
        
        return alerts, allow_request
    
    async def check_usage_quotas(self, provider: str, user_id: int, 
                               estimated_tokens: int) -> Tuple[bool, List[CostAlert]]:
        """
        检查使用配额
        
        Args:
            provider: AI服务提供商
            user_id: 用户ID
            estimated_tokens: 预估token数
            
        Returns:
            Tuple[bool, List[CostAlert]]: (是否允许请求, 告警列表)
        """
        alerts = []
        allow_request = True
        
        try:
            # 检查系统级配额
            system_alerts, system_allow = await self._check_system_quota(
                provider, estimated_tokens
            )
            alerts.extend(system_alerts)
            if not system_allow:
                allow_request = False
            
            # 检查用户级配额
            user_alerts, user_allow = await self._check_user_quota(
                provider, user_id, estimated_tokens
            )
            alerts.extend(user_alerts)
            if not user_allow:
                allow_request = False
            
            return allow_request, alerts
            
        except Exception as e:
            self.logger.error(f"Error checking usage quotas: {str(e)}")
            # 出错时采用保守策略
            error_alert = CostAlert(
                alert_id=f"quota_check_error_{int(datetime.utcnow().timestamp())}",
                level=AlertLevel.WARNING,
                message=f"配额检查出错: {str(e)}",
                provider=provider,
                user_id=user_id
            )
            return True, [error_alert]
    
    async def _check_system_quota(self, provider: str, 
                                 estimated_tokens: int) -> Tuple[List[CostAlert], bool]:
        """检查系统级配额"""
        alerts = []
        allow_request = True
        
        for quota_id, quota in self.quotas.items():
            if not quota_id.startswith("system_"):
                continue
            
            if quota.providers and provider not in quota.providers:
                continue
            
            # 获取当前使用情况
            current_usage = await self._get_quota_usage(quota)
            
            # 检查token配额
            if quota.token_limit:
                projected_tokens = current_usage.total_tokens + estimated_tokens
                if projected_tokens > quota.token_limit:
                    alert = CostAlert(
                        alert_id=f"system_token_quota_exceeded_{quota_id}_{int(datetime.utcnow().timestamp())}",
                        level=AlertLevel.CRITICAL,
                        message=f"系统token配额即将超限: {projected_tokens}/{quota.token_limit}",
                        quota_id=quota_id,
                        provider=provider,
                        current_usage=Decimal(projected_tokens),
                        limit=Decimal(quota.token_limit),
                        percentage=projected_tokens / quota.token_limit
                    )
                    alerts.append(alert)
                    allow_request = False
            
            # 检查请求配额
            if quota.request_limit:
                projected_requests = current_usage.total_requests + 1
                if projected_requests > quota.request_limit:
                    alert = CostAlert(
                        alert_id=f"system_request_quota_exceeded_{quota_id}_{int(datetime.utcnow().timestamp())}",
                        level=AlertLevel.CRITICAL,
                        message=f"系统请求配额即将超限: {projected_requests}/{quota.request_limit}",
                        quota_id=quota_id,
                        provider=provider,
                        current_usage=Decimal(projected_requests),
                        limit=Decimal(quota.request_limit),
                        percentage=projected_requests / quota.request_limit
                    )
                    alerts.append(alert)
                    allow_request = False
        
        return alerts, allow_request
    
    async def _check_user_quota(self, provider: str, user_id: int, 
                               estimated_tokens: int) -> Tuple[List[CostAlert], bool]:
        """检查用户级配额"""
        alerts = []
        allow_request = True
        
        # 确定用户配额类型（普通用户或高级用户）
        user_quota_id = await self._get_user_quota_type(user_id)
        
        if user_quota_id in self.quotas:
            quota = self.quotas[user_quota_id]
            
            if quota.providers and provider not in quota.providers:
                return alerts, allow_request
            
            # 获取用户当前使用情况
            current_usage = await self._get_user_quota_usage(quota, user_id)
            
            # 检查token配额
            if quota.token_limit:
                projected_tokens = current_usage.total_tokens + estimated_tokens
                if projected_tokens > quota.token_limit:
                    alert = CostAlert(
                        alert_id=f"user_token_quota_exceeded_{user_id}_{int(datetime.utcnow().timestamp())}",
                        level=AlertLevel.CRITICAL,
                        message=f"用户token配额即将超限: {projected_tokens}/{quota.token_limit}",
                        quota_id=user_quota_id,
                        provider=provider,
                        user_id=user_id,
                        current_usage=Decimal(projected_tokens),
                        limit=Decimal(quota.token_limit),
                        percentage=projected_tokens / quota.token_limit
                    )
                    alerts.append(alert)
                    allow_request = False
            
            # 检查请求配额
            if quota.request_limit:
                projected_requests = current_usage.total_requests + 1
                if projected_requests > quota.request_limit:
                    alert = CostAlert(
                        alert_id=f"user_request_quota_exceeded_{user_id}_{int(datetime.utcnow().timestamp())}",
                        level=AlertLevel.CRITICAL,
                        message=f"用户请求配额即将超限: {projected_requests}/{quota.request_limit}",
                        quota_id=user_quota_id,
                        provider=provider,
                        user_id=user_id,
                        current_usage=Decimal(projected_requests),
                        limit=Decimal(quota.request_limit),
                        percentage=projected_requests / quota.request_limit
                    )
                    alerts.append(alert)
                    allow_request = False
        
        return alerts, allow_request
    
    async def _get_user_quota_type(self, user_id: int) -> str:
        """获取用户配额类型"""
        # TODO: 从用户表或权限表查询用户类型
        # 这里简化处理，假设所有用户都是普通用户
        return "user_daily"
    
    async def record_usage(self, provider: str, user_id: int, 
                          input_tokens: int, output_tokens: int, 
                          cost: Decimal, response_time: float,
                          success: bool = True) -> None:
        """
        记录使用情况
        
        Args:
            provider: AI服务提供商
            user_id: 用户ID
            input_tokens: 输入token数
            output_tokens: 输出token数
            cost: 实际成本
            response_time: 响应时间
            success: 是否成功
        """
        try:
            today = date.today()
            total_tokens = input_tokens + output_tokens
            
            # 查询或创建使用统计记录
            query = select(AIUsageStats).where(
                and_(
                    AIUsageStats.user_id == user_id,
                    AIUsageStats.ai_provider == provider,
                    AIUsageStats.date == today
                )
            )
            result = await self.db.execute(query)
            usage_stats = result.scalar_one_or_none()
            
            if usage_stats is None:
                # 创建新记录
                usage_stats = AIUsageStats(
                    user_id=user_id,
                    ai_provider=provider,
                    ai_model="unknown",  # TODO: 从请求中获取具体模型
                    date=today,
                    request_count=1,
                    success_count=1 if success else 0,
                    error_count=0 if success else 1,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    total_cost=float(cost),
                    avg_response_time=response_time,
                    min_response_time=response_time,
                    max_response_time=response_time
                )
                self.db.add(usage_stats)
            else:
                # 更新现有记录
                usage_stats.request_count += 1
                if success:
                    usage_stats.success_count += 1
                else:
                    usage_stats.error_count += 1
                
                usage_stats.input_tokens += input_tokens
                usage_stats.output_tokens += output_tokens
                usage_stats.total_tokens += total_tokens
                usage_stats.total_cost += float(cost)
                
                # 更新响应时间统计
                total_requests = usage_stats.request_count
                usage_stats.avg_response_time = (
                    (usage_stats.avg_response_time * (total_requests - 1) + response_time) / total_requests
                )
                usage_stats.min_response_time = min(usage_stats.min_response_time or response_time, response_time)
                usage_stats.max_response_time = max(usage_stats.max_response_time or response_time, response_time)
            
            await self.db.commit()
            
            # 清除相关缓存
            self._clear_usage_cache(provider, user_id)
            
        except Exception as e:
            self.logger.error(f"Error recording usage: {str(e)}")
            await self.db.rollback()
    
    def _clear_usage_cache(self, provider: str = None, user_id: int = None):
        """清除使用情况缓存"""
        keys_to_remove = []
        for key in self.cost_cache.keys():
            if provider and provider in key:
                keys_to_remove.append(key)
            elif user_id and str(user_id) in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cost_cache[key]
    
    async def _get_budget_usage(self, budget: CostBudget) -> CostUsage:
        """获取预算使用情况"""
        cache_key = f"budget_{budget.budget_id}_{budget.period.value}"
        
        # 检查缓存
        if cache_key in self.cost_cache:
            cached_usage = self.cost_cache[cache_key]
            if (datetime.utcnow() - cached_usage.period_end).seconds < self.cache_ttl:
                return cached_usage
        
        # 计算时间范围
        period_start, period_end = self._get_period_range(budget.period)
        
        # 查询使用情况
        query = select(
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.sum(AIUsageStats.total_tokens).label('total_tokens'),
            func.sum(AIUsageStats.request_count).label('total_requests')
        ).where(
            and_(
                AIUsageStats.date >= period_start.date(),
                AIUsageStats.date <= period_end.date()
            )
        )
        
        # 添加提供商过滤
        if budget.providers:
            query = query.where(AIUsageStats.ai_provider.in_(budget.providers))
        
        # 添加用户过滤
        if budget.users:
            query = query.where(AIUsageStats.user_id.in_(budget.users))
        
        result = await self.db.execute(query)
        row = result.first()
        
        total_cost = Decimal(str(row.total_cost or 0))
        total_tokens = row.total_tokens or 0
        total_requests = row.total_requests or 0
        
        # 获取提供商分解
        provider_breakdown = await self._get_provider_breakdown(
            period_start, period_end, budget.providers, budget.users
        )
        
        # 获取用户分解
        user_breakdown = await self._get_user_breakdown(
            period_start, period_end, budget.providers, budget.users
        )
        
        # 获取日期分解
        daily_breakdown = await self._get_daily_breakdown(
            period_start, period_end, budget.providers, budget.users
        )
        
        usage = CostUsage(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_requests=total_requests,
            provider_breakdown=provider_breakdown,
            user_breakdown=user_breakdown,
            daily_breakdown=daily_breakdown
        )
        
        # 缓存结果
        self.cost_cache[cache_key] = usage
        
        return usage
    
    async def _get_user_budget_usage(self, budget: CostBudget, user_id: int) -> CostUsage:
        """获取用户预算使用情况"""
        cache_key = f"user_budget_{budget.budget_id}_{user_id}_{budget.period.value}"
        
        # 检查缓存
        if cache_key in self.cost_cache:
            cached_usage = self.cost_cache[cache_key]
            if (datetime.utcnow() - cached_usage.period_end).seconds < self.cache_ttl:
                return cached_usage
        
        # 计算时间范围
        period_start, period_end = self._get_period_range(budget.period)
        
        # 查询用户使用情况
        query = select(
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.sum(AIUsageStats.total_tokens).label('total_tokens'),
            func.sum(AIUsageStats.request_count).label('total_requests')
        ).where(
            and_(
                AIUsageStats.user_id == user_id,
                AIUsageStats.date >= period_start.date(),
                AIUsageStats.date <= period_end.date()
            )
        )
        
        # 添加提供商过滤
        if budget.providers:
            query = query.where(AIUsageStats.ai_provider.in_(budget.providers))
        
        result = await self.db.execute(query)
        row = result.first()
        
        total_cost = Decimal(str(row.total_cost or 0))
        total_tokens = row.total_tokens or 0
        total_requests = row.total_requests or 0
        
        usage = CostUsage(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_requests=total_requests,
            provider_breakdown={},
            user_breakdown={user_id: total_cost},
            daily_breakdown={}
        )
        
        # 缓存结果
        self.cost_cache[cache_key] = usage
        
        return usage
    
    async def _get_provider_budget_usage(self, budget: CostBudget, provider: str) -> CostUsage:
        """获取提供商预算使用情况"""
        cache_key = f"provider_budget_{budget.budget_id}_{provider}_{budget.period.value}"
        
        # 检查缓存
        if cache_key in self.cost_cache:
            cached_usage = self.cost_cache[cache_key]
            if (datetime.utcnow() - cached_usage.period_end).seconds < self.cache_ttl:
                return cached_usage
        
        # 计算时间范围
        period_start, period_end = self._get_period_range(budget.period)
        
        # 查询提供商使用情况
        query = select(
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.sum(AIUsageStats.total_tokens).label('total_tokens'),
            func.sum(AIUsageStats.request_count).label('total_requests')
        ).where(
            and_(
                AIUsageStats.ai_provider == provider,
                AIUsageStats.date >= period_start.date(),
                AIUsageStats.date <= period_end.date()
            )
        )
        
        result = await self.db.execute(query)
        row = result.first()
        
        total_cost = Decimal(str(row.total_cost or 0))
        total_tokens = row.total_tokens or 0
        total_requests = row.total_requests or 0
        
        usage = CostUsage(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_requests=total_requests,
            provider_breakdown={provider: total_cost},
            user_breakdown={},
            daily_breakdown={}
        )
        
        # 缓存结果
        self.cost_cache[cache_key] = usage
        
        return usage
    
    async def _get_quota_usage(self, quota: UsageQuota) -> CostUsage:
        """获取配额使用情况"""
        cache_key = f"quota_{quota.quota_id}_{quota.period.value}"
        
        # 检查缓存
        if cache_key in self.cost_cache:
            cached_usage = self.cost_cache[cache_key]
            if (datetime.utcnow() - cached_usage.period_end).seconds < self.cache_ttl:
                return cached_usage
        
        # 计算时间范围
        period_start, period_end = self._get_period_range(quota.period)
        
        # 查询使用情况
        query = select(
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.sum(AIUsageStats.total_tokens).label('total_tokens'),
            func.sum(AIUsageStats.request_count).label('total_requests')
        ).where(
            and_(
                AIUsageStats.date >= period_start.date(),
                AIUsageStats.date <= period_end.date()
            )
        )
        
        # 添加过滤条件
        if quota.providers:
            query = query.where(AIUsageStats.ai_provider.in_(quota.providers))
        
        if quota.users:
            query = query.where(AIUsageStats.user_id.in_(quota.users))
        
        result = await self.db.execute(query)
        row = result.first()
        
        total_cost = Decimal(str(row.total_cost or 0))
        total_tokens = row.total_tokens or 0
        total_requests = row.total_requests or 0
        
        usage = CostUsage(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_requests=total_requests,
            provider_breakdown={},
            user_breakdown={},
            daily_breakdown={}
        )
        
        # 缓存结果
        self.cost_cache[cache_key] = usage
        
        return usage
    
    async def _get_user_quota_usage(self, quota: UsageQuota, user_id: int) -> CostUsage:
        """获取用户配额使用情况"""
        cache_key = f"user_quota_{quota.quota_id}_{user_id}_{quota.period.value}"
        
        # 检查缓存
        if cache_key in self.cost_cache:
            cached_usage = self.cost_cache[cache_key]
            if (datetime.utcnow() - cached_usage.period_end).seconds < self.cache_ttl:
                return cached_usage
        
        # 计算时间范围
        period_start, period_end = self._get_period_range(quota.period)
        
        # 查询用户配额使用情况
        query = select(
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.sum(AIUsageStats.total_tokens).label('total_tokens'),
            func.sum(AIUsageStats.request_count).label('total_requests')
        ).where(
            and_(
                AIUsageStats.user_id == user_id,
                AIUsageStats.date >= period_start.date(),
                AIUsageStats.date <= period_end.date()
            )
        )
        
        # 添加提供商过滤
        if quota.providers:
            query = query.where(AIUsageStats.ai_provider.in_(quota.providers))
        
        result = await self.db.execute(query)
        row = result.first()
        
        total_cost = Decimal(str(row.total_cost or 0))
        total_tokens = row.total_tokens or 0
        total_requests = row.total_requests or 0
        
        usage = CostUsage(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_requests=total_requests,
            provider_breakdown={},
            user_breakdown={user_id: total_cost},
            daily_breakdown={}
        )
        
        # 缓存结果
        self.cost_cache[cache_key] = usage
        
        return usage
    
    def _get_period_range(self, period: BudgetPeriod) -> Tuple[datetime, datetime]:
        """获取周期时间范围"""
        now = datetime.utcnow()
        
        if period == BudgetPeriod.DAILY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
        elif period == BudgetPeriod.WEEKLY:
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7) - timedelta(microseconds=1)
        elif period == BudgetPeriod.MONTHLY:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1) - timedelta(microseconds=1)
            else:
                end = start.replace(month=now.month + 1) - timedelta(microseconds=1)
        elif period == BudgetPeriod.YEARLY:
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=now.year + 1) - timedelta(microseconds=1)
        else:
            # 默认为日周期
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
        
        return start, end
    
    async def _get_provider_breakdown(self, start: datetime, end: datetime, 
                                    providers: List[str] = None, 
                                    users: List[int] = None) -> Dict[str, Decimal]:
        """获取提供商成本分解"""
        query = select(
            AIUsageStats.ai_provider,
            func.sum(AIUsageStats.total_cost).label('total_cost')
        ).where(
            and_(
                AIUsageStats.date >= start.date(),
                AIUsageStats.date <= end.date()
            )
        ).group_by(AIUsageStats.ai_provider)
        
        if providers:
            query = query.where(AIUsageStats.ai_provider.in_(providers))
        
        if users:
            query = query.where(AIUsageStats.user_id.in_(users))
        
        result = await self.db.execute(query)
        
        breakdown = {}
        for row in result:
            breakdown[row.ai_provider] = Decimal(str(row.total_cost or 0))
        
        return breakdown
    
    async def _get_user_breakdown(self, start: datetime, end: datetime, 
                                providers: List[str] = None, 
                                users: List[int] = None) -> Dict[int, Decimal]:
        """获取用户成本分解"""
        query = select(
            AIUsageStats.user_id,
            func.sum(AIUsageStats.total_cost).label('total_cost')
        ).where(
            and_(
                AIUsageStats.date >= start.date(),
                AIUsageStats.date <= end.date()
            )
        ).group_by(AIUsageStats.user_id)
        
        if providers:
            query = query.where(AIUsageStats.ai_provider.in_(providers))
        
        if users:
            query = query.where(AIUsageStats.user_id.in_(users))
        
        result = await self.db.execute(query)
        
        breakdown = {}
        for row in result:
            breakdown[row.user_id] = Decimal(str(row.total_cost or 0))
        
        return breakdown
    
    async def _get_daily_breakdown(self, start: datetime, end: datetime, 
                                 providers: List[str] = None, 
                                 users: List[int] = None) -> Dict[date, Decimal]:
        """获取日期成本分解"""
        query = select(
            AIUsageStats.date,
            func.sum(AIUsageStats.total_cost).label('total_cost')
        ).where(
            and_(
                AIUsageStats.date >= start.date(),
                AIUsageStats.date <= end.date()
            )
        ).group_by(AIUsageStats.date)
        
        if providers:
            query = query.where(AIUsageStats.ai_provider.in_(providers))
        
        if users:
            query = query.where(AIUsageStats.user_id.in_(users))
        
        result = await self.db.execute(query)
        
        breakdown = {}
        for row in result:
            breakdown[row.date] = Decimal(str(row.total_cost or 0))
        
        return breakdown
    
    async def get_cost_summary(self, period: BudgetPeriod = BudgetPeriod.DAILY, 
                              provider: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        获取成本摘要
        
        Args:
            period: 统计周期
            provider: 特定提供商（可选）
            user_id: 特定用户（可选）
            
        Returns:
            Dict[str, Any]: 成本摘要信息
        """
        try:
            period_start, period_end = self._get_period_range(period)
            
            # 构建查询
            query = select(
                func.sum(AIUsageStats.total_cost).label('total_cost'),
                func.sum(AIUsageStats.total_tokens).label('total_tokens'),
                func.sum(AIUsageStats.request_count).label('total_requests'),
                func.avg(AIUsageStats.avg_response_time).label('avg_response_time')
            ).where(
                and_(
                    AIUsageStats.date >= period_start.date(),
                    AIUsageStats.date <= period_end.date()
                )
            )
            
            if provider:
                query = query.where(AIUsageStats.ai_provider == provider)
            
            if user_id:
                query = query.where(AIUsageStats.user_id == user_id)
            
            result = await self.db.execute(query)
            row = result.first()
            
            total_cost = Decimal(str(row.total_cost or 0))
            total_tokens = row.total_tokens or 0
            total_requests = row.total_requests or 0
            avg_response_time = row.avg_response_time or 0
            
            # 获取预算信息
            budget_info = {}
            for budget_id, budget in self.budgets.items():
                if budget.period == period:
                    usage = await self._get_budget_usage(budget)
                    budget_info[budget_id] = {
                        "name": budget.name,
                        "limit": float(budget.amount),
                        "used": float(usage.total_cost),
                        "percentage": float(usage.total_cost / budget.amount) if budget.amount > 0 else 0,
                        "remaining": float(budget.amount - usage.total_cost)
                    }
            
            # 获取配额信息
            quota_info = {}
            for quota_id, quota in self.quotas.items():
                if quota.period == period:
                    usage = await self._get_quota_usage(quota)
                    quota_info[quota_id] = {
                        "name": quota.name,
                        "token_limit": quota.token_limit,
                        "token_used": usage.total_tokens,
                        "token_percentage": (usage.total_tokens / quota.token_limit) if quota.token_limit else 0,
                        "request_limit": quota.request_limit,
                        "request_used": usage.total_requests,
                        "request_percentage": (usage.total_requests / quota.request_limit) if quota.request_limit else 0
                    }
            
            return {
                "period": period.value,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "summary": {
                    "total_cost": float(total_cost),
                    "total_tokens": total_tokens,
                    "total_requests": total_requests,
                    "avg_response_time": avg_response_time,
                    "cost_per_token": float(total_cost / total_tokens) if total_tokens > 0 else 0,
                    "cost_per_request": float(total_cost / total_requests) if total_requests > 0 else 0
                },
                "budgets": budget_info,
                "quotas": quota_info,
                "provider_breakdown": await self._get_provider_breakdown(period_start, period_end),
                "user_breakdown": await self._get_user_breakdown(period_start, period_end) if not user_id else {},
                "daily_breakdown": await self._get_daily_breakdown(period_start, period_end)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cost summary: {str(e)}")
            return {
                "error": str(e),
                "period": period.value,
                "summary": {
                    "total_cost": 0,
                    "total_tokens": 0,
                    "total_requests": 0,
                    "avg_response_time": 0
                }
            }
    
    def add_budget(self, budget: CostBudget) -> None:
        """添加预算配置"""
        self.budgets[budget.budget_id] = budget
        self.logger.info(f"Added budget: {budget.name} ({budget.budget_id})")
    
    def add_quota(self, quota: UsageQuota) -> None:
        """添加配额配置"""
        self.quotas[quota.quota_id] = quota
        self.logger.info(f"Added quota: {quota.name} ({quota.quota_id})")
    
    def remove_budget(self, budget_id: str) -> bool:
        """移除预算配置"""
        if budget_id in self.budgets:
            del self.budgets[budget_id]
            self.logger.info(f"Removed budget: {budget_id}")
            return True
        return False
    
    def remove_quota(self, quota_id: str) -> bool:
        """移除配额配置"""
        if quota_id in self.quotas:
            del self.quotas[quota_id]
            self.logger.info(f"Removed quota: {quota_id}")
            return True
        return False
    
    def get_alerts(self, level: AlertLevel = None, 
                  limit: int = 100) -> List[CostAlert]:
        """获取告警列表"""
        alerts = self.alert_history
        
        if level:
            alerts = [alert for alert in alerts if alert.level == level]
        
        # 按时间倒序排序
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def clear_alerts(self, before: datetime = None) -> int:
        """清除告警历史"""
        if before is None:
            before = datetime.utcnow()
        
        original_count = len(self.alert_history)
        self.alert_history = [
            alert for alert in self.alert_history 
            if alert.timestamp > before
        ]
        
        cleared_count = original_count - len(self.alert_history)
        self.logger.info(f"Cleared {cleared_count} alerts before {before}")
        
        return cleared_count
    
    async def get_dashboard_data(self, period: BudgetPeriod, user_id: int, is_admin: bool) -> Dict[str, Any]:
        """获取成本监控仪表板数据"""
        try:
            dashboard_data = {}
            
            # 获取总体成本摘要
            cost_summary = await self.get_cost_summary(period, None, user_id if not is_admin else None)
            dashboard_data["cost_summary"] = cost_summary
            
            # 获取预算使用情况
            budget_usage = await self.get_budget_usage_data(None, user_id, is_admin)
            dashboard_data["budget_usage"] = budget_usage
            
            # 获取配额使用情况
            quota_usage = await self.get_quota_usage_data(None, user_id, is_admin)
            dashboard_data["quota_usage"] = quota_usage
            
            # 获取告警信息
            recent_alerts = self.get_alerts(None, 10)
            dashboard_data["recent_alerts"] = [
                {
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "message": alert.message,
                    "provider": alert.provider,
                    "user_id": alert.user_id,
                    "percentage": alert.percentage,
                    "timestamp": alert.timestamp.isoformat() if alert.timestamp else None
                }
                for alert in recent_alerts
                if is_admin or not alert.user_id or alert.user_id == user_id
            ]
            
            # 获取提供商统计
            provider_stats = await self._get_provider_statistics(period, user_id if not is_admin else None)
            dashboard_data["provider_stats"] = provider_stats
            
            # 获取用户统计（仅管理员）
            if is_admin:
                user_stats = await self._get_user_statistics(period)
                dashboard_data["user_stats"] = user_stats
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {str(e)}")
            raise
    
    async def get_cost_summary(self, period: BudgetPeriod, provider: str = None, user_id: int = None) -> Dict[str, Any]:
        """获取成本摘要"""
        try:
            period_start, period_end = self._get_period_range(period)
            
            # 构建查询
            query = select(
                func.sum(AIUsageStats.total_cost).label('total_cost'),
                func.sum(AIUsageStats.total_tokens).label('total_tokens'),
                func.sum(AIUsageStats.request_count).label('total_requests'),
                func.avg(AIUsageStats.avg_response_time).label('avg_response_time'),
                func.sum(AIUsageStats.success_count).label('success_count'),
                func.sum(AIUsageStats.error_count).label('error_count')
            ).where(
                and_(
                    AIUsageStats.date >= period_start.date(),
                    AIUsageStats.date <= period_end.date()
                )
            )
            
            # 添加过滤条件
            if provider:
                query = query.where(AIUsageStats.ai_provider == provider)
            if user_id:
                query = query.where(AIUsageStats.user_id == user_id)
            
            result = await self.db.execute(query)
            row = result.first()
            
            total_cost = float(row.total_cost or 0)
            total_tokens = row.total_tokens or 0
            total_requests = row.total_requests or 0
            avg_response_time = float(row.avg_response_time or 0)
            success_count = row.success_count or 0
            error_count = row.error_count or 0
            
            # 计算成功率
            success_rate = (success_count / total_requests) if total_requests > 0 else 0
            
            return {
                "period": period.value,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "total_requests": total_requests,
                "avg_response_time": avg_response_time,
                "success_rate": success_rate,
                "error_count": error_count
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cost summary: {str(e)}")
            raise
    
    async def get_cost_trends(self, days: int, provider: str = None, user_id: int = None) -> Dict[str, Any]:
        """获取成本趋势数据"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # 查询每日成本数据
            query = select(
                AIUsageStats.date,
                func.sum(AIUsageStats.total_cost).label('daily_cost'),
                func.sum(AIUsageStats.total_tokens).label('daily_tokens'),
                func.sum(AIUsageStats.request_count).label('daily_requests')
            ).where(
                and_(
                    AIUsageStats.date >= start_date,
                    AIUsageStats.date <= end_date
                )
            ).group_by(AIUsageStats.date).order_by(AIUsageStats.date)
            
            # 添加过滤条件
            if provider:
                query = query.where(AIUsageStats.ai_provider == provider)
            if user_id:
                query = query.where(AIUsageStats.user_id == user_id)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            # 构建趋势数据
            trends = []
            for row in rows:
                trends.append({
                    "date": row.date.isoformat(),
                    "cost": float(row.daily_cost or 0),
                    "tokens": row.daily_tokens or 0,
                    "requests": row.daily_requests or 0
                })
            
            # 计算总计和平均值
            total_cost = sum(item["cost"] for item in trends)
            total_tokens = sum(item["tokens"] for item in trends)
            total_requests = sum(item["requests"] for item in trends)
            
            avg_daily_cost = total_cost / len(trends) if trends else 0
            avg_daily_tokens = total_tokens / len(trends) if trends else 0
            avg_daily_requests = total_requests / len(trends) if trends else 0
            
            return {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "trends": trends,
                "summary": {
                    "total_cost": total_cost,
                    "total_tokens": total_tokens,
                    "total_requests": total_requests,
                    "avg_daily_cost": avg_daily_cost,
                    "avg_daily_tokens": avg_daily_tokens,
                    "avg_daily_requests": avg_daily_requests
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting cost trends: {str(e)}")
            raise
    
    async def get_usage_statistics(self, period: BudgetPeriod, group_by: str, user_id: int, is_admin: bool) -> Dict[str, Any]:
        """获取使用统计数据"""
        try:
            period_start, period_end = self._get_period_range(period)
            
            if group_by == "provider":
                return await self._get_provider_statistics(period, user_id if not is_admin else None)
            elif group_by == "user" and is_admin:
                return await self._get_user_statistics(period)
            elif group_by == "model":
                return await self._get_model_statistics(period, user_id if not is_admin else None)
            else:
                raise ValueError(f"Unsupported group_by: {group_by}")
                
        except Exception as e:
            self.logger.error(f"Error getting usage statistics: {str(e)}")
            raise
    
    async def _get_provider_statistics(self, period: BudgetPeriod, user_id: int = None) -> Dict[str, Any]:
        """获取按提供商分组的统计数据"""
        period_start, period_end = self._get_period_range(period)
        
        query = select(
            AIUsageStats.ai_provider,
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.sum(AIUsageStats.total_tokens).label('total_tokens'),
            func.sum(AIUsageStats.request_count).label('total_requests'),
            func.avg(AIUsageStats.avg_response_time).label('avg_response_time'),
            func.sum(AIUsageStats.success_count).label('success_count'),
            func.sum(AIUsageStats.error_count).label('error_count')
        ).where(
            and_(
                AIUsageStats.date >= period_start.date(),
                AIUsageStats.date <= period_end.date()
            )
        ).group_by(AIUsageStats.ai_provider)
        
        if user_id:
            query = query.where(AIUsageStats.user_id == user_id)
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        statistics = []
        for row in rows:
            total_requests = row.total_requests or 0
            success_rate = (row.success_count / total_requests) if total_requests > 0 else 0
            
            statistics.append({
                "provider": row.ai_provider,
                "total_cost": float(row.total_cost or 0),
                "total_tokens": row.total_tokens or 0,
                "total_requests": total_requests,
                "avg_response_time": float(row.avg_response_time or 0),
                "success_rate": success_rate,
                "error_count": row.error_count or 0
            })
        
        return {
            "group_by": "provider",
            "period": period.value,
            "statistics": statistics
        }
    
    async def _get_user_statistics(self, period: BudgetPeriod) -> Dict[str, Any]:
        """获取按用户分组的统计数据"""
        period_start, period_end = self._get_period_range(period)
        
        query = select(
            AIUsageStats.user_id,
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.sum(AIUsageStats.total_tokens).label('total_tokens'),
            func.sum(AIUsageStats.request_count).label('total_requests'),
            func.avg(AIUsageStats.avg_response_time).label('avg_response_time'),
            func.sum(AIUsageStats.success_count).label('success_count'),
            func.sum(AIUsageStats.error_count).label('error_count')
        ).where(
            and_(
                AIUsageStats.date >= period_start.date(),
                AIUsageStats.date <= period_end.date()
            )
        ).group_by(AIUsageStats.user_id)
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        statistics = []
        for row in rows:
            total_requests = row.total_requests or 0
            success_rate = (row.success_count / total_requests) if total_requests > 0 else 0
            
            statistics.append({
                "user_id": row.user_id,
                "total_cost": float(row.total_cost or 0),
                "total_tokens": row.total_tokens or 0,
                "total_requests": total_requests,
                "avg_response_time": float(row.avg_response_time or 0),
                "success_rate": success_rate,
                "error_count": row.error_count or 0
            })
        
        return {
            "group_by": "user",
            "period": period.value,
            "statistics": statistics
        }
    
    async def _get_model_statistics(self, period: BudgetPeriod, user_id: int = None) -> Dict[str, Any]:
        """获取按模型分组的统计数据"""
        period_start, period_end = self._get_period_range(period)
        
        query = select(
            AIUsageStats.ai_model,
            AIUsageStats.ai_provider,
            func.sum(AIUsageStats.total_cost).label('total_cost'),
            func.sum(AIUsageStats.total_tokens).label('total_tokens'),
            func.sum(AIUsageStats.request_count).label('total_requests'),
            func.avg(AIUsageStats.avg_response_time).label('avg_response_time'),
            func.sum(AIUsageStats.success_count).label('success_count'),
            func.sum(AIUsageStats.error_count).label('error_count')
        ).where(
            and_(
                AIUsageStats.date >= period_start.date(),
                AIUsageStats.date <= period_end.date()
            )
        ).group_by(AIUsageStats.ai_model, AIUsageStats.ai_provider)
        
        if user_id:
            query = query.where(AIUsageStats.user_id == user_id)
        
        result = await self.db.execute(query)
        rows = result.fetchall()
        
        statistics = []
        for row in rows:
            total_requests = row.total_requests or 0
            success_rate = (row.success_count / total_requests) if total_requests > 0 else 0
            
            statistics.append({
                "model": row.ai_model,
                "provider": row.ai_provider,
                "total_cost": float(row.total_cost or 0),
                "total_tokens": row.total_tokens or 0,
                "total_requests": total_requests,
                "avg_response_time": float(row.avg_response_time or 0),
                "success_rate": success_rate,
                "error_count": row.error_count or 0
            })
        
        return {
            "group_by": "model",
            "period": period.value,
            "statistics": statistics
        }
    
    async def get_budget_usage_data(self, budget_id: str = None, user_id: int = None, is_admin: bool = False) -> Dict[str, Any]:
        """获取预算使用情况数据"""
        try:
            budget_usage_list = []
            
            budgets_to_check = []
            if budget_id:
                if budget_id in self.budgets:
                    budgets_to_check = [self.budgets[budget_id]]
            else:
                budgets_to_check = list(self.budgets.values())
            
            for budget in budgets_to_check:
                # 权限检查：普通用户只能看到适用于自己的预算
                if not is_admin and budget.users and user_id not in budget.users:
                    continue
                
                usage = await self._get_budget_usage(budget)
                usage_percentage = float(usage.total_cost / budget.amount) if budget.amount > 0 else 0
                
                budget_data = {
                    "budget_id": budget.budget_id,
                    "name": budget.name,
                    "period": budget.period.value,
                    "amount": float(budget.amount),
                    "currency": budget.currency,
                    "current_usage": float(usage.total_cost),
                    "usage_percentage": usage_percentage,
                    "remaining": float(budget.amount - usage.total_cost),
                    "warning_threshold": budget.warning_threshold,
                    "critical_threshold": budget.critical_threshold,
                    "status": self._get_budget_status(usage_percentage, budget),
                    "period_start": usage.period_start.isoformat(),
                    "period_end": usage.period_end.isoformat()
                }
                
                budget_usage_list.append(budget_data)
            
            return {
                "budgets": budget_usage_list,
                "total_budgets": len(budget_usage_list)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting budget usage data: {str(e)}")
            raise
    
    async def get_quota_usage_data(self, quota_id: str = None, user_id: int = None, is_admin: bool = False) -> Dict[str, Any]:
        """获取配额使用情况数据"""
        try:
            quota_usage_list = []
            
            quotas_to_check = []
            if quota_id:
                if quota_id in self.quotas:
                    quotas_to_check = [self.quotas[quota_id]]
            else:
                quotas_to_check = list(self.quotas.values())
            
            for quota in quotas_to_check:
                # 权限检查：普通用户只能看到适用于自己的配额
                if not is_admin and quota.users and user_id not in quota.users:
                    continue
                
                usage = await self._get_quota_usage(quota)
                
                # 计算使用百分比
                token_percentage = (usage.total_tokens / quota.token_limit) if quota.token_limit else 0
                request_percentage = (usage.total_requests / quota.request_limit) if quota.request_limit else 0
                
                quota_data = {
                    "quota_id": quota.quota_id,
                    "name": quota.name,
                    "period": quota.period.value,
                    "token_limit": quota.token_limit,
                    "request_limit": quota.request_limit,
                    "current_tokens": usage.total_tokens,
                    "current_requests": usage.total_requests,
                    "token_percentage": token_percentage,
                    "request_percentage": request_percentage,
                    "remaining_tokens": (quota.token_limit - usage.total_tokens) if quota.token_limit else None,
                    "remaining_requests": (quota.request_limit - usage.total_requests) if quota.request_limit else None,
                    "status": self._get_quota_status(token_percentage, request_percentage),
                    "period_start": usage.period_start.isoformat(),
                    "period_end": usage.period_end.isoformat()
                }
                
                quota_usage_list.append(quota_data)
            
            return {
                "quotas": quota_usage_list,
                "total_quotas": len(quota_usage_list)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting quota usage data: {str(e)}")
            raise
    
    def _get_budget_status(self, usage_percentage: float, budget: CostBudget) -> str:
        """获取预算状态"""
        if usage_percentage >= 1.0:
            return "exceeded"
        elif usage_percentage >= budget.critical_threshold:
            return "critical"
        elif usage_percentage >= budget.warning_threshold:
            return "warning"
        else:
            return "normal"
    
    def _get_quota_status(self, token_percentage: float, request_percentage: float) -> str:
        """获取配额状态"""
        max_percentage = max(token_percentage, request_percentage)
        
        if max_percentage >= 1.0:
            return "exceeded"
        elif max_percentage >= 0.9:
            return "critical"
        elif max_percentage >= 0.8:
            return "warning"
        else:
            return "normal"