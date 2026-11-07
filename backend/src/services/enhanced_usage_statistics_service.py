"""
增强使用统计服务 - 提供详细的AI服务使用统计和分析
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, or_, text
from sqlalchemy.orm import selectinload

from ..models.ai_usage_stats import AIUsageStats, AISystemStats
from ..models.user import User
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""
    timestamp: datetime
    requests: int
    tokens: int
    cost: float
    response_time: float
    success_rate: float
    concurrent_users: int
    error_count: int


@dataclass
class ModelUsageMetrics:
    """模型使用指标"""
    model: str
    provider: str
    requests: int
    tokens: int
    cost: float
    avg_response_time: float
    success_rate: float
    popularity_score: float
    avg_tokens_per_request: float
    peak_hour: int
    error_rate: float


@dataclass
class UserActivityMetrics:
    """用户活动指标"""
    user_id: int
    username: str
    department: Optional[str]
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_session_duration: float
    most_used_model: str
    activity_score: float
    last_active: datetime
    favorite_providers: List[str]


@dataclass
class PerformanceMetrics:
    """性能指标"""
    period: str
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float
    error_rate: float
    availability: float
    peak_concurrent_users: int
    total_uptime: float


@dataclass
class UsagePattern:
    """使用模式"""
    pattern_type: str  # hourly, daily, weekly
    peak_hours: List[int]
    low_usage_hours: List[int]
    usage_distribution: Dict[str, float]
    seasonal_trends: Dict[str, float]


class EnhancedUsageStatisticsService:
    """增强使用统计服务"""
    
    def __init__(self, db: AsyncSession, _owns_session: bool = False):
        self.db = db
        self._owns_session = _owns_session
        self.logger = logging.getLogger(__name__)

    async def aclose(self) -> None:
        """关闭自有会话（工厂创建的短生命周期会话：回滚并关闭）。

        调用方传入的会话（_owns_session=False）不由本服务关闭。
        """
        if not self._owns_session or self.db is None:
            return
        try:
            await self.db.rollback()
        finally:
            await self.db.close()
            self.db = None
    
    async def get_time_series_data(
        self, 
        time_range: str = "24h",
        granularity: str = "hour",
        provider: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[TimeSeriesPoint]:
        """
        获取时间序列数据
        
        Args:
            time_range: 时间范围 (24h, 7d, 30d, 90d)
            granularity: 时间粒度 (hour, day, week)
            provider: 特定提供商
            user_id: 特定用户
            
        Returns:
            List[TimeSeriesPoint]: 时间序列数据点列表
        """
        try:
            # 计算时间范围
            end_time = datetime.utcnow()
            if time_range == "24h":
                start_time = end_time - timedelta(hours=24)
            elif time_range == "7d":
                start_time = end_time - timedelta(days=7)
            elif time_range == "30d":
                start_time = end_time - timedelta(days=30)
            elif time_range == "90d":
                start_time = end_time - timedelta(days=90)
            else:
                start_time = end_time - timedelta(hours=24)
            
            # 构建查询
            if granularity == "hour":
                time_format = "%Y-%m-%d %H:00:00"
                time_group = func.date_format(AIUsageStats.created_at, '%Y-%m-%d %H')
            elif granularity == "day":
                time_format = "%Y-%m-%d"
                time_group = func.date(AIUsageStats.created_at)
            else:
                time_format = "%Y-%m-%d"
                time_group = func.date(AIUsageStats.created_at)
            
            query = select(
                time_group.label('time_period'),
                func.sum(AIUsageStats.request_count).label('total_requests'),
                func.sum(AIUsageStats.total_tokens).label('total_tokens'),
                func.sum(AIUsageStats.total_cost).label('total_cost'),
                func.avg(AIUsageStats.avg_response_time).label('avg_response_time'),
                func.avg(AIUsageStats.success_count / AIUsageStats.request_count).label('success_rate'),
                func.sum(AIUsageStats.error_count).label('error_count'),
                func.count(func.distinct(AIUsageStats.user_id)).label('concurrent_users')
            ).where(
                AIUsageStats.created_at >= start_time
            ).group_by(time_group).order_by(time_group)
            
            # 添加过滤条件
            if provider:
                query = query.where(AIUsageStats.ai_provider == provider)
            if user_id:
                query = query.where(AIUsageStats.user_id == user_id)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            # 转换为时间序列数据点
            time_series = []
            for row in rows:
                if granularity == "hour":
                    timestamp = datetime.strptime(f"{row.time_period}:00:00", "%Y-%m-%d %H:%M:%S")
                else:
                    timestamp = datetime.strptime(str(row.time_period), "%Y-%m-%d")
                
                point = TimeSeriesPoint(
                    timestamp=timestamp,
                    requests=row.total_requests or 0,
                    tokens=row.total_tokens or 0,
                    cost=float(row.total_cost or 0),
                    response_time=float(row.avg_response_time or 0),
                    success_rate=float(row.success_rate or 0),
                    concurrent_users=row.concurrent_users or 0,
                    error_count=row.error_count or 0
                )
                time_series.append(point)
            
            return time_series
            
        except Exception as e:
            self.logger.error(f"Error getting time series data: {str(e)}")
            return []
    
    async def get_model_usage_metrics(
        self,
        period: str = "daily",
        limit: int = 20
    ) -> List[ModelUsageMetrics]:
        """
        获取模型使用指标
        
        Args:
            period: 统计周期 (daily, weekly, monthly)
            limit: 返回数量限制
            
        Returns:
            List[ModelUsageMetrics]: 模型使用指标列表
        """
        try:
            # 计算时间范围
            end_date = date.today()
            if period == "daily":
                start_date = end_date - timedelta(days=1)
            elif period == "weekly":
                start_date = end_date - timedelta(days=7)
            elif period == "monthly":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=1)
            
            # 查询模型使用统计
            query = select(
                AIUsageStats.ai_model,
                AIUsageStats.ai_provider,
                func.sum(AIUsageStats.request_count).label('total_requests'),
                func.sum(AIUsageStats.total_tokens).label('total_tokens'),
                func.sum(AIUsageStats.total_cost).label('total_cost'),
                func.avg(AIUsageStats.avg_response_time).label('avg_response_time'),
                func.avg(AIUsageStats.success_count / AIUsageStats.request_count).label('success_rate'),
                func.avg(AIUsageStats.total_tokens / AIUsageStats.request_count).label('avg_tokens_per_request'),
                func.sum(AIUsageStats.error_count).label('error_count')
            ).where(
                AIUsageStats.date >= start_date
            ).group_by(
                AIUsageStats.ai_model, AIUsageStats.ai_provider
            ).order_by(
                desc(func.sum(AIUsageStats.request_count))
            ).limit(limit)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            # 计算总请求数用于计算受欢迎度
            total_requests_query = select(
                func.sum(AIUsageStats.request_count)
            ).where(AIUsageStats.date >= start_date)
            total_result = await self.db.execute(total_requests_query)
            total_requests = total_result.scalar() or 1
            
            # 转换为模型指标
            model_metrics = []
            for row in rows:
                # 计算受欢迎度分数 (基于请求数占比)
                popularity_score = float(row.total_requests) / float(total_requests)
                
                # 计算错误率
                error_rate = float(row.error_count or 0) / float(row.total_requests or 1)
                
                # 获取峰值小时 (简化处理，实际应该查询小时级数据)
                peak_hour = await self._get_model_peak_hour(
                    row.ai_model, row.ai_provider, start_date
                )
                
                metrics = ModelUsageMetrics(
                    model=row.ai_model,
                    provider=row.ai_provider,
                    requests=row.total_requests or 0,
                    tokens=row.total_tokens or 0,
                    cost=float(row.total_cost or 0),
                    avg_response_time=float(row.avg_response_time or 0),
                    success_rate=float(row.success_rate or 0),
                    popularity_score=popularity_score,
                    avg_tokens_per_request=float(row.avg_tokens_per_request or 0),
                    peak_hour=peak_hour,
                    error_rate=error_rate
                )
                model_metrics.append(metrics)
            
            return model_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting model usage metrics: {str(e)}")
            return []
    
    async def get_user_activity_metrics(
        self,
        period: str = "daily",
        limit: int = 50
    ) -> List[UserActivityMetrics]:
        """
        获取用户活动指标
        
        Args:
            period: 统计周期 (daily, weekly, monthly)
            limit: 返回数量限制
            
        Returns:
            List[UserActivityMetrics]: 用户活动指标列表
        """
        try:
            # 计算时间范围
            end_date = date.today()
            if period == "daily":
                start_date = end_date - timedelta(days=1)
            elif period == "weekly":
                start_date = end_date - timedelta(days=7)
            elif period == "monthly":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=1)
            
            # 查询用户使用统计
            query = select(
                AIUsageStats.user_id,
                func.sum(AIUsageStats.request_count).label('total_requests'),
                func.sum(AIUsageStats.total_tokens).label('total_tokens'),
                func.sum(AIUsageStats.total_cost).label('total_cost'),
                func.max(AIUsageStats.created_at).label('last_active')
            ).where(
                AIUsageStats.date >= start_date
            ).group_by(
                AIUsageStats.user_id
            ).order_by(
                desc(func.sum(AIUsageStats.request_count))
            ).limit(limit)
            
            result = await self.db.execute(query)
            rows = result.fetchall()
            
            # 获取用户信息
            user_ids = [row.user_id for row in rows]
            users_query = select(User).where(User.id.in_(user_ids))
            users_result = await self.db.execute(users_query)
            users = {user.id: user for user in users_result.scalars().all()}
            
            # 计算总活动分数基准
            max_requests = max([row.total_requests for row in rows]) if rows else 1
            
            # 转换为用户活动指标
            user_metrics = []
            for row in rows:
                user = users.get(row.user_id)
                if not user:
                    continue
                
                # 计算活动分数 (基于请求数)
                activity_score = float(row.total_requests) / float(max_requests)
                
                # 获取最常用模型
                most_used_model = await self._get_user_most_used_model(
                    row.user_id, start_date
                )
                
                # 获取偏好提供商
                favorite_providers = await self._get_user_favorite_providers(
                    row.user_id, start_date
                )
                
                # 计算平均会话时长 (简化处理)
                avg_session_duration = await self._calculate_avg_session_duration(
                    row.user_id, start_date
                )
                
                metrics = UserActivityMetrics(
                    user_id=row.user_id,
                    username=user.username,
                    department=getattr(user, 'department', None),
                    total_requests=row.total_requests or 0,
                    total_tokens=row.total_tokens or 0,
                    total_cost=float(row.total_cost or 0),
                    avg_session_duration=avg_session_duration,
                    most_used_model=most_used_model,
                    activity_score=activity_score,
                    last_active=row.last_active,
                    favorite_providers=favorite_providers
                )
                user_metrics.append(metrics)
            
            return user_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting user activity metrics: {str(e)}")
            return []
    
    async def get_performance_metrics(
        self,
        period: str = "daily"
    ) -> PerformanceMetrics:
        """
        获取性能指标
        
        Args:
            period: 统计周期 (daily, weekly, monthly)
            
        Returns:
            PerformanceMetrics: 性能指标
        """
        try:
            # 计算时间范围
            end_date = date.today()
            if period == "daily":
                start_date = end_date - timedelta(days=1)
            elif period == "weekly":
                start_date = end_date - timedelta(days=7)
            elif period == "monthly":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=1)
            
            # 查询基础性能数据
            base_query = select(
                func.avg(AIUsageStats.avg_response_time).label('avg_response_time'),
                func.sum(AIUsageStats.request_count).label('total_requests'),
                func.sum(AIUsageStats.success_count).label('total_success'),
                func.sum(AIUsageStats.error_count).label('total_errors'),
                func.max(AIUsageStats.max_response_time).label('max_response_time'),
                func.min(AIUsageStats.min_response_time).label('min_response_time')
            ).where(AIUsageStats.date >= start_date)
            
            result = await self.db.execute(base_query)
            row = result.first()
            
            if not row or not row.total_requests:
                return PerformanceMetrics(
                    period=period,
                    avg_response_time=0.0,
                    p50_response_time=0.0,
                    p95_response_time=0.0,
                    p99_response_time=0.0,
                    throughput=0.0,
                    error_rate=0.0,
                    availability=1.0,
                    peak_concurrent_users=0,
                    total_uptime=100.0
                )
            
            # 计算基础指标
            avg_response_time = float(row.avg_response_time or 0)
            total_requests = row.total_requests or 0
            total_success = row.total_success or 0
            total_errors = row.total_errors or 0
            
            # 计算错误率和可用性
            error_rate = float(total_errors) / float(total_requests) if total_requests > 0 else 0
            availability = float(total_success) / float(total_requests) if total_requests > 0 else 1.0
            
            # 计算吞吐量 (请求/分钟)
            period_hours = (end_date - start_date).days * 24 + (end_date - start_date).seconds / 3600
            throughput = float(total_requests) / (period_hours * 60) if period_hours > 0 else 0
            
            # 获取百分位响应时间 (简化处理，实际应该使用更精确的计算)
            percentile_query = select(
                AIUsageStats.avg_response_time
            ).where(
                AIUsageStats.date >= start_date
            ).order_by(AIUsageStats.avg_response_time)
            
            percentile_result = await self.db.execute(percentile_query)
            response_times = [float(rt) for rt in percentile_result.scalars().all() if rt]
            
            if response_times:
                p50_index = int(len(response_times) * 0.5)
                p95_index = int(len(response_times) * 0.95)
                p99_index = int(len(response_times) * 0.99)
                
                p50_response_time = response_times[p50_index] if p50_index < len(response_times) else avg_response_time
                p95_response_time = response_times[p95_index] if p95_index < len(response_times) else avg_response_time
                p99_response_time = response_times[p99_index] if p99_index < len(response_times) else avg_response_time
            else:
                p50_response_time = p95_response_time = p99_response_time = avg_response_time
            
            # 获取峰值并发用户数
            peak_concurrent_users = await self._get_peak_concurrent_users(start_date)
            
            # 计算总正常运行时间 (简化处理)
            total_uptime = availability * 100
            
            return PerformanceMetrics(
                period=period,
                avg_response_time=avg_response_time,
                p50_response_time=p50_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                throughput=throughput,
                error_rate=error_rate,
                availability=availability,
                peak_concurrent_users=peak_concurrent_users,
                total_uptime=total_uptime
            )
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {str(e)}")
            return PerformanceMetrics(
                period=period,
                avg_response_time=0.0,
                p50_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                throughput=0.0,
                error_rate=0.0,
                availability=1.0,
                peak_concurrent_users=0,
                total_uptime=100.0
            )
    
    async def get_usage_patterns(
        self,
        pattern_type: str = "hourly",
        period: str = "weekly"
    ) -> UsagePattern:
        """
        获取使用模式分析
        
        Args:
            pattern_type: 模式类型 (hourly, daily, weekly)
            period: 分析周期 (weekly, monthly, quarterly)
            
        Returns:
            UsagePattern: 使用模式分析结果
        """
        try:
            # 计算时间范围
            end_date = date.today()
            if period == "weekly":
                start_date = end_date - timedelta(days=7)
            elif period == "monthly":
                start_date = end_date - timedelta(days=30)
            elif period == "quarterly":
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=7)
            
            if pattern_type == "hourly":
                # 分析小时级使用模式
                query = select(
                    func.hour(AIUsageStats.created_at).label('hour'),
                    func.sum(AIUsageStats.request_count).label('requests')
                ).where(
                    AIUsageStats.date >= start_date
                ).group_by(
                    func.hour(AIUsageStats.created_at)
                ).order_by('hour')
                
                result = await self.db.execute(query)
                hourly_data = {row.hour: row.requests for row in result.fetchall()}
                
                # 找出峰值和低谷时段
                max_requests = max(hourly_data.values()) if hourly_data else 0
                min_requests = min(hourly_data.values()) if hourly_data else 0
                
                peak_hours = [hour for hour, requests in hourly_data.items() 
                             if requests >= max_requests * 0.8]
                low_usage_hours = [hour for hour, requests in hourly_data.items() 
                                  if requests <= min_requests * 1.2]
                
                # 计算使用分布
                total_requests = sum(hourly_data.values())
                usage_distribution = {
                    str(hour): float(requests) / float(total_requests) 
                    for hour, requests in hourly_data.items()
                } if total_requests > 0 else {}
                
                return UsagePattern(
                    pattern_type=pattern_type,
                    peak_hours=peak_hours,
                    low_usage_hours=low_usage_hours,
                    usage_distribution=usage_distribution,
                    seasonal_trends={}
                )
            
            # 其他模式类型的处理...
            return UsagePattern(
                pattern_type=pattern_type,
                peak_hours=[],
                low_usage_hours=[],
                usage_distribution={},
                seasonal_trends={}
            )
            
        except Exception as e:
            self.logger.error(f"Error getting usage patterns: {str(e)}")
            return UsagePattern(
                pattern_type=pattern_type,
                peak_hours=[],
                low_usage_hours=[],
                usage_distribution={},
                seasonal_trends={}
            )
    
    async def export_usage_data(
        self,
        format_type: str = "csv",
        period: str = "monthly",
        include_details: bool = True
    ) -> Dict[str, Any]:
        """
        导出使用数据
        
        Args:
            format_type: 导出格式 (csv, json, excel)
            period: 导出周期 (daily, weekly, monthly)
            include_details: 是否包含详细数据
            
        Returns:
            Dict[str, Any]: 导出数据和元信息
        """
        try:
            # 获取各种统计数据
            time_series = await self.get_time_series_data(
                time_range="30d" if period == "monthly" else "7d",
                granularity="day"
            )
            
            model_metrics = await self.get_model_usage_metrics(period=period)
            user_metrics = await self.get_user_activity_metrics(period=period)
            performance_metrics = await self.get_performance_metrics(period=period)
            
            export_data = {
                "export_info": {
                    "format": format_type,
                    "period": period,
                    "generated_at": datetime.utcnow().isoformat(),
                    "include_details": include_details
                },
                "summary": {
                    "total_requests": sum(point.requests for point in time_series),
                    "total_tokens": sum(point.tokens for point in time_series),
                    "total_cost": sum(point.cost for point in time_series),
                    "avg_response_time": performance_metrics.avg_response_time,
                    "error_rate": performance_metrics.error_rate,
                    "availability": performance_metrics.availability
                },
                "time_series": [
                    {
                        "timestamp": point.timestamp.isoformat(),
                        "requests": point.requests,
                        "tokens": point.tokens,
                        "cost": point.cost,
                        "response_time": point.response_time,
                        "success_rate": point.success_rate
                    } for point in time_series
                ] if include_details else [],
                "model_metrics": [
                    {
                        "model": metric.model,
                        "provider": metric.provider,
                        "requests": metric.requests,
                        "tokens": metric.tokens,
                        "cost": metric.cost,
                        "avg_response_time": metric.avg_response_time,
                        "success_rate": metric.success_rate,
                        "popularity_score": metric.popularity_score
                    } for metric in model_metrics
                ],
                "user_metrics": [
                    {
                        "user_id": metric.user_id,
                        "username": metric.username,
                        "department": metric.department,
                        "total_requests": metric.total_requests,
                        "total_tokens": metric.total_tokens,
                        "total_cost": metric.total_cost,
                        "activity_score": metric.activity_score,
                        "most_used_model": metric.most_used_model
                    } for metric in user_metrics
                ] if include_details else [],
                "performance_metrics": {
                    "avg_response_time": performance_metrics.avg_response_time,
                    "p95_response_time": performance_metrics.p95_response_time,
                    "p99_response_time": performance_metrics.p99_response_time,
                    "throughput": performance_metrics.throughput,
                    "error_rate": performance_metrics.error_rate,
                    "availability": performance_metrics.availability
                }
            }
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Error exporting usage data: {str(e)}")
            return {"error": str(e)}
    
    # 辅助方法
    async def _get_model_peak_hour(self, model: str, provider: str, start_date: date) -> int:
        """获取模型的峰值使用小时"""
        try:
            query = select(
                func.hour(AIUsageStats.created_at).label('hour'),
                func.sum(AIUsageStats.request_count).label('requests')
            ).where(
                and_(
                    AIUsageStats.ai_model == model,
                    AIUsageStats.ai_provider == provider,
                    AIUsageStats.date >= start_date
                )
            ).group_by(
                func.hour(AIUsageStats.created_at)
            ).order_by(
                desc(func.sum(AIUsageStats.request_count))
            ).limit(1)
            
            result = await self.db.execute(query)
            row = result.first()
            return row.hour if row else 12  # 默认返回12点
            
        except Exception:
            return 12
    
    async def _get_user_most_used_model(self, user_id: int, start_date: date) -> str:
        """获取用户最常用的模型"""
        try:
            query = select(
                AIUsageStats.ai_model,
                func.sum(AIUsageStats.request_count).label('requests')
            ).where(
                and_(
                    AIUsageStats.user_id == user_id,
                    AIUsageStats.date >= start_date
                )
            ).group_by(
                AIUsageStats.ai_model
            ).order_by(
                desc(func.sum(AIUsageStats.request_count))
            ).limit(1)
            
            result = await self.db.execute(query)
            row = result.first()
            return row.ai_model if row else "unknown"
            
        except Exception:
            return "unknown"
    
    async def _get_user_favorite_providers(self, user_id: int, start_date: date) -> List[str]:
        """获取用户偏好的提供商"""
        try:
            query = select(
                AIUsageStats.ai_provider,
                func.sum(AIUsageStats.request_count).label('requests')
            ).where(
                and_(
                    AIUsageStats.user_id == user_id,
                    AIUsageStats.date >= start_date
                )
            ).group_by(
                AIUsageStats.ai_provider
            ).order_by(
                desc(func.sum(AIUsageStats.request_count))
            ).limit(3)
            
            result = await self.db.execute(query)
            return [row.ai_provider for row in result.fetchall()]
            
        except Exception:
            return []
    
    async def _calculate_avg_session_duration(self, user_id: int, start_date: date) -> float:
        """计算用户平均会话时长"""
        try:
            # 简化处理：基于请求数估算会话时长
            query = select(
                func.count(func.distinct(AIUsageStats.date)).label('active_days'),
                func.sum(AIUsageStats.request_count).label('total_requests')
            ).where(
                and_(
                    AIUsageStats.user_id == user_id,
                    AIUsageStats.date >= start_date
                )
            )
            
            result = await self.db.execute(query)
            row = result.first()
            
            if row and row.active_days and row.total_requests:
                # 假设每个会话平均5个请求，每个请求间隔2分钟
                avg_requests_per_day = float(row.total_requests) / float(row.active_days)
                estimated_sessions_per_day = avg_requests_per_day / 5
                return estimated_sessions_per_day * 10  # 假设每个会话10分钟
            
            return 15.0  # 默认15分钟
            
        except Exception:
            return 15.0
    
    async def _get_peak_concurrent_users(self, start_date: date) -> int:
        """获取峰值并发用户数"""
        try:
            # 简化处理：查询单日最大活跃用户数
            query = select(
                func.count(func.distinct(AIUsageStats.user_id)).label('daily_users')
            ).where(
                AIUsageStats.date >= start_date
            ).group_by(
                AIUsageStats.date
            ).order_by(
                desc(func.count(func.distinct(AIUsageStats.user_id)))
            ).limit(1)
            
            result = await self.db.execute(query)
            row = result.first()
            return row.daily_users if row else 0
            
        except Exception:
            return 0

    async def get_system_overview(self, period: str = "daily") -> Dict[str, Any]:
        """系统总览：聚合模型使用、用户活跃与性能指标。

        Called by the cache-preheating scheduler (``_preheat_system_stats``)
        to warm the statistics cache. Aggregates the existing metric
        methods; no new queries are introduced here.
        """
        models = await self.get_model_usage_metrics(period=period, limit=20)
        users = await self.get_user_activity_metrics(period=period, limit=50)
        performance = await self.get_performance_metrics(period=period)
        return {
            "period": period,
            "total_requests": sum(m.requests for m in models),
            "total_tokens": sum(m.tokens for m in models),
            "total_cost": round(sum(m.cost for m in models), 4),
            "active_users": len(users),
            "avg_response_time": performance.avg_response_time,
            "error_rate": performance.error_rate,
            "availability": performance.availability,
            "models": [asdict(m) for m in models],
            "top_users": [asdict(u) for u in users[:10]],
            "performance": asdict(performance),
        }


async def get_usage_statistics_service(
    db: AsyncSession = None,
) -> EnhancedUsageStatisticsService:
    """获取增强使用统计服务实例（供缓存预热等后台任务使用）。

    短生命周期会话（根因修复）：无显式会话时每次调用新建一个会话，
    调用方用完须 ``await service.aclose()``（回滚并关闭）。不再返回
    进程级单例——单例会话的首个读会隐式开启事务并挂在进程生命周期
    内，阻塞 recover.sh 的建库步骤（2026-11-07 14:20 看护重建卡约
    4 分钟即因此）。显式传入会话时调用方拥有该会话（行为不变）。
    """
    if db is not None:
        return EnhancedUsageStatisticsService(db)
    from ..core.database import AsyncSessionLocal

    if AsyncSessionLocal is None:
        raise RuntimeError("Async database engine not available")
    return EnhancedUsageStatisticsService(AsyncSessionLocal(), _owns_session=True)