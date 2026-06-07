"""
需求统计分析服务

本模块实现需求管理的统计分析功能，包括：
- 需求指标计算功能
- 趋势分析算法
- 质量评估功能
- 多维度统计分析
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
import json
from dataclasses import dataclass, asdict
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text, case
from sqlalchemy.orm import selectinload, joinedload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError
from ..models.requirement import (
    Requirement, RequirementStatus, RequirementType, Priority, BusinessValue, Complexity,
    RequirementStatusHistory, RequirementDependency, RequirementReview, RequirementChangeRequest,
    RequirementReviewComment, DependencyType, ReviewStatus, ChangeStatus
)
from ..models.project import Project
from ..models.user import User

logger = logging.getLogger(__name__)


@dataclass
class RequirementMetrics:
    """需求指标数据"""
    project_id: Optional[int]
    
    # 基础统计
    total_requirements: int
    status_distribution: Dict[str, int]
    type_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    complexity_distribution: Dict[str, int]
    
    # 进度指标
    completion_rate: float
    approval_rate: float
    review_pass_rate: float
    
    # 质量指标
    avg_quality_score: float
    avg_completeness_score: float
    quality_distribution: Dict[str, int]
    
    # 工作量指标
    total_estimated_effort: float
    total_actual_effort: float
    effort_variance: float
    avg_effort_per_requirement: float
    
    # 时间指标
    avg_cycle_time: float  # 从创建到完成的平均时间
    avg_review_time: float  # 平均评审时间
    avg_development_time: float  # 平均开发时间
    
    # 变更指标
    change_request_count: int
    change_approval_rate: float
    avg_change_impact: float
    
    # 依赖指标
    dependency_count: int
    dependency_complexity: float
    circular_dependencies: int
    
    # 协作指标
    review_participation_rate: float
    avg_comments_per_review: float
    
    # 计算时间
    calculated_at: datetime


@dataclass
class RequirementTrendAnalysis:
    """需求趋势分析数据"""
    metric_name: str
    project_id: Optional[int]
    time_period: Tuple[date, date]
    
    # 时间序列数据
    time_series_data: List[Dict[str, Any]]
    
    # 趋势分析
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: float  # 0-1
    growth_rate: float  # 增长率
    
    # 预测数据
    prediction: Dict[str, Any]
    confidence_level: float
    
    # 季节性分析
    seasonality: Dict[str, Any]
    
    # 异常检测
    anomalies: List[Dict[str, Any]]
    
    # 分析时间
    analyzed_at: datetime


@dataclass
class RequirementQualityAssessment:
    """需求质量评估数据"""
    project_id: Optional[int]
    
    # 整体质量评分
    overall_quality_score: float
    
    # 质量维度评分
    completeness_score: float
    consistency_score: float
    clarity_score: float
    testability_score: float
    traceability_score: float
    
    # 质量问题统计
    quality_issues: Dict[str, int]
    
    # 改进建议
    improvement_suggestions: List[str]
    
    # 质量趋势
    quality_trend: str
    
    # 基准对比
    benchmark_comparison: Dict[str, float]
    
    # 评估时间
    assessed_at: datetime


@dataclass
class RequirementPerformanceMetrics:
    """需求绩效指标"""
    project_id: Optional[int]
    user_id: Optional[int]
    time_period: Tuple[date, date]
    
    # 效率指标
    requirements_created: int
    requirements_completed: int
    avg_completion_time: float
    productivity_score: float
    
    # 质量指标
    avg_requirement_quality: float
    review_success_rate: float
    change_request_rate: float
    
    # 协作指标
    reviews_participated: int
    comments_provided: int
    collaboration_score: float
    
    # 综合评分
    overall_performance_score: float
    
    # 排名信息
    team_ranking: Optional[int]
    percentile: Optional[float]
    
    # 计算时间
    calculated_at: datetime


class RequirementAnalyticsService:
    """需求统计分析服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_requirement_metrics(self, project_id: Optional[int] = None) -> RequirementMetrics:
        """
        计算需求指标
        
        Args:
            project_id: 项目ID，为None时计算全局指标
            
        Returns:
            需求指标数据
        """
        # 构建基础查询
        base_query = select(Requirement)
        if project_id:
            base_query = base_query.where(Requirement.project_id == project_id)
        
        # 获取所有需求
        result = await self.db.execute(base_query)
        requirements = result.scalars().all()
        
        if not requirements:
            return self._create_empty_metrics(project_id)
        
        # 计算基础统计
        total_requirements = len(requirements)
        status_distribution = self._calculate_status_distribution(requirements)
        type_distribution = self._calculate_type_distribution(requirements)
        priority_distribution = self._calculate_priority_distribution(requirements)
        complexity_distribution = self._calculate_complexity_distribution(requirements)
        
        # 计算进度指标
        completion_rate = self._calculate_completion_rate(requirements)
        approval_rate = self._calculate_approval_rate(requirements)
        review_pass_rate = await self._calculate_review_pass_rate(project_id)
        
        # 计算质量指标
        avg_quality_score = self._calculate_avg_quality_score(requirements)
        avg_completeness_score = self._calculate_avg_completeness_score(requirements)
        quality_distribution = self._calculate_quality_distribution(requirements)
        
        # 计算工作量指标
        effort_metrics = self._calculate_effort_metrics(requirements)
        
        # 计算时间指标
        time_metrics = await self._calculate_time_metrics(requirements)
        
        # 计算变更指标
        change_metrics = await self._calculate_change_metrics(project_id)
        
        # 计算依赖指标
        dependency_metrics = await self._calculate_dependency_metrics(project_id)
        
        # 计算协作指标
        collaboration_metrics = await self._calculate_collaboration_metrics(project_id)
        
        return RequirementMetrics(
            project_id=project_id,
            total_requirements=total_requirements,
            status_distribution=status_distribution,
            type_distribution=type_distribution,
            priority_distribution=priority_distribution,
            complexity_distribution=complexity_distribution,
            completion_rate=completion_rate,
            approval_rate=approval_rate,
            review_pass_rate=review_pass_rate,
            avg_quality_score=avg_quality_score,
            avg_completeness_score=avg_completeness_score,
            quality_distribution=quality_distribution,
            total_estimated_effort=effort_metrics['total_estimated'],
            total_actual_effort=effort_metrics['total_actual'],
            effort_variance=effort_metrics['variance'],
            avg_effort_per_requirement=effort_metrics['avg_per_requirement'],
            avg_cycle_time=time_metrics['avg_cycle_time'],
            avg_review_time=time_metrics['avg_review_time'],
            avg_development_time=time_metrics['avg_development_time'],
            change_request_count=change_metrics['count'],
            change_approval_rate=change_metrics['approval_rate'],
            avg_change_impact=change_metrics['avg_impact'],
            dependency_count=dependency_metrics['count'],
            dependency_complexity=dependency_metrics['complexity'],
            circular_dependencies=dependency_metrics['circular'],
            review_participation_rate=collaboration_metrics['participation_rate'],
            avg_comments_per_review=collaboration_metrics['avg_comments'],
            calculated_at=datetime.utcnow()
        )
    
    def _create_empty_metrics(self, project_id: Optional[int]) -> RequirementMetrics:
        """创建空的指标数据"""
        return RequirementMetrics(
            project_id=project_id,
            total_requirements=0,
            status_distribution={},
            type_distribution={},
            priority_distribution={},
            complexity_distribution={},
            completion_rate=0.0,
            approval_rate=0.0,
            review_pass_rate=0.0,
            avg_quality_score=0.0,
            avg_completeness_score=0.0,
            quality_distribution={},
            total_estimated_effort=0.0,
            total_actual_effort=0.0,
            effort_variance=0.0,
            avg_effort_per_requirement=0.0,
            avg_cycle_time=0.0,
            avg_review_time=0.0,
            avg_development_time=0.0,
            change_request_count=0,
            change_approval_rate=0.0,
            avg_change_impact=0.0,
            dependency_count=0,
            dependency_complexity=0.0,
            circular_dependencies=0,
            review_participation_rate=0.0,
            avg_comments_per_review=0.0,
            calculated_at=datetime.utcnow()
        )
    
    def _calculate_status_distribution(self, requirements: List[Requirement]) -> Dict[str, int]:
        """计算状态分布"""
        distribution = defaultdict(int)
        for req in requirements:
            status = req.status.value if req.status else 'UNKNOWN'
            distribution[status] += 1
        return dict(distribution)
    
    def _calculate_type_distribution(self, requirements: List[Requirement]) -> Dict[str, int]:
        """计算类型分布"""
        distribution = defaultdict(int)
        for req in requirements:
            req_type = req.requirement_type.value if req.requirement_type else 'UNKNOWN'
            distribution[req_type] += 1
        return dict(distribution)
    
    def _calculate_priority_distribution(self, requirements: List[Requirement]) -> Dict[str, int]:
        """计算优先级分布"""
        distribution = defaultdict(int)
        for req in requirements:
            priority = req.priority.value if req.priority else 'UNKNOWN'
            distribution[priority] += 1
        return dict(distribution)
    
    def _calculate_complexity_distribution(self, requirements: List[Requirement]) -> Dict[str, int]:
        """计算复杂度分布"""
        distribution = defaultdict(int)
        for req in requirements:
            complexity = req.complexity.value if req.complexity else 'UNKNOWN'
            distribution[complexity] += 1
        return dict(distribution)
    
    def _calculate_completion_rate(self, requirements: List[Requirement]) -> float:
        """计算完成率"""
        if not requirements:
            return 0.0
        
        completed_statuses = {RequirementStatus.COMPLETED, RequirementStatus.DEPLOYED, RequirementStatus.CLOSED}
        completed_count = sum(1 for req in requirements if req.status in completed_statuses)
        
        return completed_count / len(requirements)
    
    def _calculate_approval_rate(self, requirements: List[Requirement]) -> float:
        """计算批准率"""
        if not requirements:
            return 0.0
        
        # 只考虑已经过评审的需求
        reviewed_requirements = [req for req in requirements if req.status not in {RequirementStatus.DRAFT}]
        if not reviewed_requirements:
            return 0.0
        
        approved_statuses = {
            RequirementStatus.APPROVED, RequirementStatus.IN_DEVELOPMENT, 
            RequirementStatus.TESTING, RequirementStatus.COMPLETED, 
            RequirementStatus.DEPLOYED, RequirementStatus.CLOSED
        }
        approved_count = sum(1 for req in reviewed_requirements if req.status in approved_statuses)
        
        return approved_count / len(reviewed_requirements)
    
    async def _calculate_review_pass_rate(self, project_id: Optional[int]) -> float:
        """计算评审通过率"""
        query = select(RequirementReview)
        if project_id:
            query = query.join(Requirement).where(Requirement.project_id == project_id)
        
        query = query.where(RequirementReview.review_status == ReviewStatus.COMPLETED)
        
        result = await self.db.execute(query)
        reviews = result.scalars().all()
        
        if not reviews:
            return 0.0
        
        passed_reviews = sum(1 for review in reviews if review.decision in ['APPROVED', 'APPROVED_WITH_MINOR_CHANGES'])
        return passed_reviews / len(reviews)
    
    def _calculate_avg_quality_score(self, requirements: List[Requirement]) -> float:
        """计算平均质量评分"""
        quality_scores = [float(req.quality_score) for req in requirements if req.quality_score is not None]
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    
    def _calculate_avg_completeness_score(self, requirements: List[Requirement]) -> float:
        """计算平均完整性评分"""
        completeness_scores = [float(req.completeness_score) for req in requirements if req.completeness_score is not None]
        return sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
    
    def _calculate_quality_distribution(self, requirements: List[Requirement]) -> Dict[str, int]:
        """计算质量分布"""
        distribution = {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0, 'unknown': 0}
        
        for req in requirements:
            if req.quality_score is None:
                distribution['unknown'] += 1
            else:
                score = float(req.quality_score)
                if score >= 8.0:
                    distribution['excellent'] += 1
                elif score >= 6.0:
                    distribution['good'] += 1
                elif score >= 4.0:
                    distribution['fair'] += 1
                else:
                    distribution['poor'] += 1
        
        return distribution
    
    def _calculate_effort_metrics(self, requirements: List[Requirement]) -> Dict[str, float]:
        """计算工作量指标"""
        estimated_efforts = [float(req.estimated_effort) for req in requirements if req.estimated_effort is not None]
        actual_efforts = [float(req.actual_effort) for req in requirements if req.actual_effort is not None]
        
        total_estimated = sum(estimated_efforts)
        total_actual = sum(actual_efforts)
        
        # 计算偏差
        variance = 0.0
        if estimated_efforts and actual_efforts:
            # 只计算同时有预估和实际工作量的需求的偏差
            paired_efforts = []
            for req in requirements:
                if req.estimated_effort is not None and req.actual_effort is not None:
                    estimated = float(req.estimated_effort)
                    actual = float(req.actual_effort)
                    if estimated > 0:
                        variance_pct = abs(actual - estimated) / estimated
                        paired_efforts.append(variance_pct)
            
            variance = sum(paired_efforts) / len(paired_efforts) if paired_efforts else 0.0
        
        avg_per_requirement = total_estimated / len(requirements) if requirements else 0.0
        
        return {
            'total_estimated': total_estimated,
            'total_actual': total_actual,
            'variance': variance,
            'avg_per_requirement': avg_per_requirement
        }
    
    async def _calculate_time_metrics(self, requirements: List[Requirement]) -> Dict[str, float]:
        """计算时间指标"""
        # 计算平均周期时间（从创建到完成）
        cycle_times = []
        for req in requirements:
            if req.actual_end_date and req.created_at:
                cycle_time = (req.actual_end_date - req.created_at.date()).days
                cycle_times.append(cycle_time)
        
        avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0.0
        
        # 计算平均评审时间
        review_times = []
        for req in requirements:
            if hasattr(req, 'reviews') and req.reviews:
                for review in req.reviews:
                    if review.started_at and review.completed_at:
                        review_time = (review.completed_at - review.started_at).total_seconds() / 3600  # 小时
                        review_times.append(review_time)
        
        avg_review_time = sum(review_times) / len(review_times) if review_times else 0.0
        
        # 计算平均开发时间（从批准到测试完成）
        development_times = []
        for req in requirements:
            if req.actual_start_date and req.actual_end_date:
                dev_time = (req.actual_end_date - req.actual_start_date).days
                development_times.append(dev_time)
        
        avg_development_time = sum(development_times) / len(development_times) if development_times else 0.0
        
        return {
            'avg_cycle_time': avg_cycle_time,
            'avg_review_time': avg_review_time,
            'avg_development_time': avg_development_time
        }
    
    async def _calculate_change_metrics(self, project_id: Optional[int]) -> Dict[str, Any]:
        """计算变更指标"""
        query = select(RequirementChangeRequest)
        if project_id:
            query = query.join(Requirement).where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        change_requests = result.scalars().all()
        
        if not change_requests:
            return {'count': 0, 'approval_rate': 0.0, 'avg_impact': 0.0}
        
        count = len(change_requests)
        approved_count = sum(1 for cr in change_requests if cr.status == ChangeStatus.APPROVED)
        approval_rate = approved_count / count if count > 0 else 0.0
        
        # 计算平均影响（基于工作量估算）
        impact_scores = [float(cr.effort_estimate) for cr in change_requests if cr.effort_estimate is not None]
        avg_impact = sum(impact_scores) / len(impact_scores) if impact_scores else 0.0
        
        return {
            'count': count,
            'approval_rate': approval_rate,
            'avg_impact': avg_impact
        }
    
    async def _calculate_dependency_metrics(self, project_id: Optional[int]) -> Dict[str, Any]:
        """计算依赖指标"""
        query = select(RequirementDependency)
        if project_id:
            query = query.join(Requirement, RequirementDependency.source_requirement_id == Requirement.id)\
                         .where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        dependencies = result.scalars().all()
        
        count = len(dependencies)
        
        # 计算依赖复杂度（基于依赖类型权重）
        complexity_weights = {
            DependencyType.DEPENDS_ON: 1.0,
            DependencyType.BLOCKS: 1.2,
            DependencyType.CONFLICTS_WITH: 1.5,
            DependencyType.RELATES_TO: 0.5,
            DependencyType.DUPLICATES: 0.8,
            DependencyType.REPLACES: 1.1
        }
        
        total_complexity = sum(complexity_weights.get(dep.dependency_type, 1.0) for dep in dependencies)
        avg_complexity = total_complexity / count if count > 0 else 0.0
        
        # 检测循环依赖（简化版本）
        circular_dependencies = await self._detect_circular_dependencies(project_id)
        
        return {
            'count': count,
            'complexity': avg_complexity,
            'circular': circular_dependencies
        }
    
    async def _detect_circular_dependencies(self, project_id: Optional[int]) -> int:
        """检测循环依赖"""
        # 这里实现简化的循环依赖检测
        # 实际应用中需要更复杂的图算法
        return 0  # 暂时返回0
    
    async def _calculate_collaboration_metrics(self, project_id: Optional[int]) -> Dict[str, float]:
        """计算协作指标"""
        # 获取评审数据
        query = select(RequirementReview)
        if project_id:
            query = query.join(Requirement).where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        reviews = result.scalars().all()
        
        if not reviews:
            return {'participation_rate': 0.0, 'avg_comments': 0.0}
        
        # 计算参与率（有评审人员的评审比例）
        reviews_with_participants = sum(1 for review in reviews if review.reviewers)
        participation_rate = reviews_with_participants / len(reviews) if reviews else 0.0
        
        # 计算平均评论数
        comment_query = select(RequirementReviewComment)
        if project_id:
            comment_query = comment_query.join(RequirementReview)\
                                       .join(Requirement)\
                                       .where(Requirement.project_id == project_id)
        
        comment_result = await self.db.execute(comment_query)
        comments = comment_result.scalars().all()
        
        avg_comments = len(comments) / len(reviews) if reviews else 0.0
        
        return {
            'participation_rate': participation_rate,
            'avg_comments': avg_comments
        }
    
    async def calculate_trend_analysis(self, metric_name: str, project_id: Optional[int] = None,
                                     days: int = 30) -> RequirementTrendAnalysis:
        """
        计算需求趋势分析
        
        Args:
            metric_name: 指标名称
            project_id: 项目ID
            days: 分析天数
            
        Returns:
            趋势分析数据
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 获取历史数据
        time_series_data = await self._get_historical_requirement_data(
            metric_name, project_id, start_date, end_date
        )
        
        if len(time_series_data) < 2:
            return RequirementTrendAnalysis(
                metric_name=metric_name,
                project_id=project_id,
                time_period=(start_date, end_date),
                time_series_data=time_series_data,
                trend_direction='stable',
                trend_strength=0.0,
                growth_rate=0.0,
                prediction={},
                confidence_level=0.0,
                seasonality={},
                anomalies=[],
                analyzed_at=datetime.utcnow()
            )
        
        # 分析趋势
        values = [item['value'] for item in time_series_data]
        trend_direction, trend_strength = self._analyze_trend(values)
        growth_rate = self._calculate_growth_rate(values)
        
        # 预测
        prediction = self._predict_future_values(values, days=7)
        
        # 季节性分析
        seasonality = self._analyze_seasonality(time_series_data)
        
        # 异常检测
        anomalies = self._detect_anomalies(time_series_data)
        
        return RequirementTrendAnalysis(
            metric_name=metric_name,
            project_id=project_id,
            time_period=(start_date, end_date),
            time_series_data=time_series_data,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            growth_rate=growth_rate,
            prediction=prediction,
            confidence_level=0.75,
            seasonality=seasonality,
            anomalies=anomalies,
            analyzed_at=datetime.utcnow()
        )
    
    async def _get_historical_requirement_data(self, metric_name: str, project_id: Optional[int],
                                             start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """获取历史需求数据"""
        data = []
        current_date = start_date
        
        while current_date <= end_date:
            # 获取当天的指标值
            value = await self._get_daily_metric_value(metric_name, project_id, current_date)
            data.append({
                'date': current_date.isoformat(),
                'value': value,
                'metric_name': metric_name
            })
            current_date += timedelta(days=1)
        
        return data
    
    async def _get_daily_metric_value(self, metric_name: str, project_id: Optional[int], 
                                    target_date: date) -> float:
        """获取指定日期的指标值"""
        # 构建查询，获取指定日期之前创建的需求
        query = select(Requirement).where(func.date(Requirement.created_at) <= target_date)
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        requirements = result.scalars().all()
        
        if metric_name == 'total_requirements':
            return len(requirements)
        elif metric_name == 'completion_rate':
            return self._calculate_completion_rate(requirements)
        elif metric_name == 'avg_quality_score':
            return self._calculate_avg_quality_score(requirements)
        elif metric_name == 'approval_rate':
            return self._calculate_approval_rate(requirements)
        else:
            return 0.0
    
    def _analyze_trend(self, values: List[float]) -> Tuple[str, float]:
        """分析趋势方向和强度"""
        if len(values) < 2:
            return 'stable', 0.0
        
        # 计算线性回归斜率
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return 'stable', 0.0
        
        slope = (n * xy_sum - x_sum * y_sum) / denominator
        
        # 判断趋势方向
        if slope > 0.1:
            direction = 'increasing'
        elif slope < -0.1:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        # 趋势强度（斜率的绝对值，归一化到0-1）
        strength = min(1.0, abs(slope) / 10)
        
        return direction, strength
    
    def _calculate_growth_rate(self, values: List[float]) -> float:
        """计算增长率"""
        if len(values) < 2:
            return 0.0
        
        first_value = values[0]
        last_value = values[-1]
        
        if first_value == 0:
            return 0.0 if last_value == 0 else 1.0
        
        return (last_value - first_value) / first_value
    
    def _predict_future_values(self, values: List[float], days: int = 7) -> Dict[str, Any]:
        """预测未来值"""
        if len(values) < 2:
            return {'predicted_values': [], 'method': 'insufficient_data'}
        
        # 简单的线性预测
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return {'predicted_values': [], 'method': 'no_trend'}
        
        slope = (n * xy_sum - x_sum * y_sum) / denominator
        intercept = (y_sum - slope * x_sum) / n
        
        predicted_values = []
        for i in range(days):
            predicted_value = slope * (n + i) + intercept
            predicted_values.append({
                'day': i + 1,
                'predicted_value': max(0, predicted_value)  # 确保非负
            })
        
        return {
            'predicted_values': predicted_values,
            'method': 'linear_regression',
            'slope': slope,
            'intercept': intercept
        }
    
    def _analyze_seasonality(self, time_series_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析季节性"""
        if len(time_series_data) < 7:
            return {'has_seasonality': False, 'pattern': 'insufficient_data'}
        
        # 简化的季节性分析 - 按星期几分组
        weekday_values = defaultdict(list)
        for item in time_series_data:
            date_obj = datetime.fromisoformat(item['date']).date()
            weekday = date_obj.weekday()  # 0=Monday, 6=Sunday
            weekday_values[weekday].append(item['value'])
        
        # 计算每个星期几的平均值
        weekday_averages = {}
        for weekday, values in weekday_values.items():
            weekday_averages[weekday] = sum(values) / len(values) if values else 0
        
        # 检查是否有明显的季节性模式
        if len(weekday_averages) >= 5:  # 至少有5天的数据
            avg_values = list(weekday_averages.values())
            max_val = max(avg_values)
            min_val = min(avg_values)
            variation = (max_val - min_val) / max_val if max_val > 0 else 0
            
            has_seasonality = variation > 0.2  # 20%以上的变化认为有季节性
            
            return {
                'has_seasonality': has_seasonality,
                'pattern': 'weekly' if has_seasonality else 'none',
                'weekday_averages': weekday_averages,
                'variation_coefficient': variation
            }
        
        return {'has_seasonality': False, 'pattern': 'insufficient_data'}
    
    def _detect_anomalies(self, time_series_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测异常值"""
        if len(time_series_data) < 5:
            return []
        
        values = [item['value'] for item in time_series_data]
        
        # 计算统计指标
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        # 使用3σ规则检测异常
        anomalies = []
        threshold = 3 * std_dev
        
        for i, item in enumerate(time_series_data):
            value = item['value']
            if abs(value - mean_val) > threshold:
                anomalies.append({
                    'date': item['date'],
                    'value': value,
                    'expected_range': [mean_val - threshold, mean_val + threshold],
                    'deviation': abs(value - mean_val),
                    'severity': 'high' if abs(value - mean_val) > 2 * threshold else 'medium'
                })
        
        return anomalies
    
    async def assess_requirement_quality(self, project_id: Optional[int] = None) -> RequirementQualityAssessment:
        """
        评估需求质量
        
        Args:
            project_id: 项目ID
            
        Returns:
            需求质量评估数据
        """
        # 获取需求数据
        base_query = select(Requirement)
        if project_id:
            base_query = base_query.where(Requirement.project_id == project_id)
        
        result = await self.db.execute(base_query)
        requirements = result.scalars().all()
        
        if not requirements:
            return RequirementQualityAssessment(
                project_id=project_id,
                overall_quality_score=0.0,
                completeness_score=0.0,
                consistency_score=0.0,
                clarity_score=0.0,
                testability_score=0.0,
                traceability_score=0.0,
                quality_issues={},
                improvement_suggestions=[],
                quality_trend='stable',
                benchmark_comparison={},
                assessed_at=datetime.utcnow()
            )
        
        # 计算各维度质量评分
        completeness_score = await self._assess_completeness(requirements)
        consistency_score = await self._assess_consistency(requirements)
        clarity_score = await self._assess_clarity(requirements)
        testability_score = await self._assess_testability(requirements)
        traceability_score = await self._assess_traceability(requirements, project_id)
        
        # 计算整体质量评分
        overall_quality_score = (
            completeness_score * 0.25 +
            consistency_score * 0.20 +
            clarity_score * 0.20 +
            testability_score * 0.20 +
            traceability_score * 0.15
        )
        
        # 识别质量问题
        quality_issues = await self._identify_quality_issues(requirements)
        
        # 生成改进建议
        improvement_suggestions = self._generate_improvement_suggestions(
            completeness_score, consistency_score, clarity_score, 
            testability_score, traceability_score, quality_issues
        )
        
        # 分析质量趋势
        quality_trend = await self._analyze_quality_trend(project_id)
        
        # 基准对比
        benchmark_comparison = await self._compare_with_benchmark(
            overall_quality_score, completeness_score, consistency_score,
            clarity_score, testability_score, traceability_score
        )
        
        return RequirementQualityAssessment(
            project_id=project_id,
            overall_quality_score=overall_quality_score,
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            clarity_score=clarity_score,
            testability_score=testability_score,
            traceability_score=traceability_score,
            quality_issues=quality_issues,
            improvement_suggestions=improvement_suggestions,
            quality_trend=quality_trend,
            benchmark_comparison=benchmark_comparison,
            assessed_at=datetime.utcnow()
        )
    
    async def _assess_completeness(self, requirements: List[Requirement]) -> float:
        """评估完整性"""
        if not requirements:
            return 0.0
        
        total_score = 0
        for req in requirements:
            score = 0
            max_score = 5
            
            # 检查必填字段
            if req.title and req.title.strip():
                score += 1
            if req.description and req.description.strip():
                score += 1
            if req.acceptance_criteria and req.acceptance_criteria.strip():
                score += 1
            if req.priority:
                score += 1
            if req.requirement_type:
                score += 1
            
            total_score += score / max_score
        
        return total_score / len(requirements)
    
    async def _assess_consistency(self, requirements: List[Requirement]) -> float:
        """评估一致性"""
        if not requirements:
            return 0.0
        
        # 检查命名一致性、格式一致性等
        # 这里实现简化版本
        consistent_count = 0
        
        for req in requirements:
            is_consistent = True
            
            # 检查编码格式一致性
            if req.requirement_code and not req.requirement_code.startswith('REQ-'):
                is_consistent = False
            
            # 检查标题格式一致性（长度合理）
            if req.title and (len(req.title) < 5 or len(req.title) > 200):
                is_consistent = False
            
            if is_consistent:
                consistent_count += 1
        
        return consistent_count / len(requirements)
    
    async def _assess_clarity(self, requirements: List[Requirement]) -> float:
        """评估清晰度"""
        if not requirements:
            return 0.0
        
        clear_count = 0
        
        for req in requirements:
            is_clear = True
            
            # 检查描述长度（太短或太长都不好）
            if req.description:
                desc_len = len(req.description.strip())
                if desc_len < 20 or desc_len > 2000:
                    is_clear = False
            else:
                is_clear = False
            
            # 检查验收标准是否存在
            if not req.acceptance_criteria or len(req.acceptance_criteria.strip()) < 10:
                is_clear = False
            
            if is_clear:
                clear_count += 1
        
        return clear_count / len(requirements)
    
    async def _assess_testability(self, requirements: List[Requirement]) -> float:
        """评估可测试性"""
        if not requirements:
            return 0.0
        
        testable_count = 0
        
        for req in requirements:
            is_testable = True
            
            # 检查是否有验收标准
            if not req.acceptance_criteria:
                is_testable = False
            
            # 检查是否有明确的成功标准
            if req.acceptance_criteria and 'should' not in req.acceptance_criteria.lower():
                # 简化检查：包含明确的行为描述
                pass
            
            if is_testable:
                testable_count += 1
        
        return testable_count / len(requirements)
    
    async def _assess_traceability(self, requirements: List[Requirement], project_id: Optional[int]) -> float:
        """评估可追溯性"""
        if not requirements:
            return 0.0
        
        # 检查依赖关系和追溯链接
        dependency_query = select(RequirementDependency)
        if project_id:
            dependency_query = dependency_query.join(Requirement, RequirementDependency.source_requirement_id == Requirement.id)\
                                             .where(Requirement.project_id == project_id)
        
        dep_result = await self.db.execute(dependency_query)
        dependencies = dep_result.scalars().all()
        
        # 简化评估：有依赖关系的需求认为可追溯性更好
        req_with_deps = set()
        for dep in dependencies:
            req_with_deps.add(dep.source_requirement_id)
            req_with_deps.add(dep.target_requirement_id)
        
        traceable_count = len(req_with_deps)
        return min(1.0, traceable_count / len(requirements))
    
    async def _identify_quality_issues(self, requirements: List[Requirement]) -> Dict[str, int]:
        """识别质量问题"""
        issues = {
            'missing_description': 0,
            'missing_acceptance_criteria': 0,
            'unclear_priority': 0,
            'incomplete_information': 0,
            'inconsistent_format': 0
        }
        
        for req in requirements:
            if not req.description or len(req.description.strip()) < 10:
                issues['missing_description'] += 1
            
            if not req.acceptance_criteria or len(req.acceptance_criteria.strip()) < 10:
                issues['missing_acceptance_criteria'] += 1
            
            if not req.priority:
                issues['unclear_priority'] += 1
            
            # 检查信息完整性
            required_fields = [req.title, req.description, req.requirement_type]
            if not all(required_fields):
                issues['incomplete_information'] += 1
            
            # 检查格式一致性
            if req.requirement_code and not req.requirement_code.startswith('REQ-'):
                issues['inconsistent_format'] += 1
        
        return issues
    
    def _generate_improvement_suggestions(self, completeness: float, consistency: float, 
                                        clarity: float, testability: float, traceability: float,
                                        quality_issues: Dict[str, int]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if completeness < 0.8:
            suggestions.append("完善需求的基本信息，确保标题、描述、验收标准等关键字段完整")
        
        if consistency < 0.8:
            suggestions.append("统一需求编码格式和命名规范，保持文档风格一致")
        
        if clarity < 0.8:
            suggestions.append("改进需求描述的清晰度，使用简洁明了的语言表达")
        
        if testability < 0.8:
            suggestions.append("为每个需求定义明确的验收标准和测试条件")
        
        if traceability < 0.8:
            suggestions.append("建立需求间的依赖关系和追溯链接")
        
        # 基于具体问题的建议
        if quality_issues.get('missing_description', 0) > 0:
            suggestions.append(f"有{quality_issues['missing_description']}个需求缺少详细描述")
        
        if quality_issues.get('missing_acceptance_criteria', 0) > 0:
            suggestions.append(f"有{quality_issues['missing_acceptance_criteria']}个需求缺少验收标准")
        
        return suggestions
    
    async def _analyze_quality_trend(self, project_id: Optional[int]) -> str:
        """分析质量趋势"""
        # 简化实现：基于最近的质量评分变化
        # 实际应用中需要历史数据
        return 'stable'
    
    async def _compare_with_benchmark(self, overall: float, completeness: float, 
                                    consistency: float, clarity: float, 
                                    testability: float, traceability: float) -> Dict[str, float]:
        """与基准对比"""
        # 行业基准值（示例）
        benchmarks = {
            'overall_quality': 0.75,
            'completeness': 0.80,
            'consistency': 0.85,
            'clarity': 0.70,
            'testability': 0.75,
            'traceability': 0.65
        }
        
        return {
            'overall_quality_vs_benchmark': overall - benchmarks['overall_quality'],
            'completeness_vs_benchmark': completeness - benchmarks['completeness'],
            'consistency_vs_benchmark': consistency - benchmarks['consistency'],
            'clarity_vs_benchmark': clarity - benchmarks['clarity'],
            'testability_vs_benchmark': testability - benchmarks['testability'],
            'traceability_vs_benchmark': traceability - benchmarks['traceability']
        }
    
    async def calculate_performance_metrics(self, user_id: Optional[int] = None, 
                                          project_id: Optional[int] = None,
                                          start_date: Optional[date] = None,
                                          end_date: Optional[date] = None) -> RequirementPerformanceMetrics:
        """
        计算需求绩效指标
        
        Args:
            user_id: 用户ID
            project_id: 项目ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            需求绩效指标
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        # 构建查询
        query = select(Requirement).where(
            and_(
                func.date(Requirement.created_at) >= start_date,
                func.date(Requirement.created_at) <= end_date
            )
        )
        
        if user_id:
            query = query.where(Requirement.creator_id == user_id)
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        requirements = result.scalars().all()
        
        # 计算效率指标
        requirements_created = len(requirements)
        completed_requirements = [req for req in requirements if req.status in {
            RequirementStatus.COMPLETED, RequirementStatus.DEPLOYED, RequirementStatus.CLOSED
        }]
        requirements_completed = len(completed_requirements)
        
        # 计算平均完成时间
        completion_times = []
        for req in completed_requirements:
            if req.actual_end_date and req.created_at:
                completion_time = (req.actual_end_date - req.created_at.date()).days
                completion_times.append(completion_time)
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0.0
        
        # 计算生产力评分
        productivity_score = self._calculate_productivity_score(
            requirements_created, requirements_completed, avg_completion_time
        )
        
        # 计算质量指标
        avg_requirement_quality = self._calculate_avg_quality_score(requirements)
        
        # 计算评审成功率
        review_success_rate = await self._calculate_user_review_success_rate(user_id, project_id, start_date, end_date)
        
        # 计算变更请求率
        change_request_rate = await self._calculate_change_request_rate(user_id, project_id, start_date, end_date)
        
        # 计算协作指标
        collaboration_metrics = await self._calculate_user_collaboration_metrics(user_id, project_id, start_date, end_date)
        
        # 计算综合评分
        overall_performance_score = self._calculate_overall_performance_score(
            productivity_score, avg_requirement_quality, review_success_rate, 
            change_request_rate, collaboration_metrics['collaboration_score']
        )
        
        return RequirementPerformanceMetrics(
            project_id=project_id,
            user_id=user_id,
            time_period=(start_date, end_date),
            requirements_created=requirements_created,
            requirements_completed=requirements_completed,
            avg_completion_time=avg_completion_time,
            productivity_score=productivity_score,
            avg_requirement_quality=avg_requirement_quality,
            review_success_rate=review_success_rate,
            change_request_rate=change_request_rate,
            reviews_participated=collaboration_metrics['reviews_participated'],
            comments_provided=collaboration_metrics['comments_provided'],
            collaboration_score=collaboration_metrics['collaboration_score'],
            overall_performance_score=overall_performance_score,
            team_ranking=None,  # 需要额外计算
            percentile=None,    # 需要额外计算
            calculated_at=datetime.utcnow()
        )
    
    def _calculate_productivity_score(self, created: int, completed: int, avg_time: float) -> float:
        """计算生产力评分"""
        if created == 0:
            return 0.0
        
        completion_rate = completed / created
        time_efficiency = max(0, 1 - (avg_time / 30))  # 30天为基准
        
        return (completion_rate * 0.7 + time_efficiency * 0.3)
    
    async def _calculate_user_review_success_rate(self, user_id: Optional[int], project_id: Optional[int],
                                                start_date: date, end_date: date) -> float:
        """计算用户评审成功率"""
        if not user_id:
            return 0.0
        
        # 获取用户参与的评审
        query = select(RequirementReview).where(
            and_(
                func.date(RequirementReview.created_at) >= start_date,
                func.date(RequirementReview.created_at) <= end_date,
                RequirementReview.moderator_id == user_id
            )
        )
        
        if project_id:
            query = query.join(Requirement).where(Requirement.project_id == project_id)
        
        result = await self.db.execute(query)
        reviews = result.scalars().all()
        
        if not reviews:
            return 0.0
        
        successful_reviews = sum(1 for review in reviews if review.decision in ['APPROVED', 'APPROVED_WITH_MINOR_CHANGES'])
        return successful_reviews / len(reviews)
    
    async def _calculate_change_request_rate(self, user_id: Optional[int], project_id: Optional[int],
                                           start_date: date, end_date: date) -> float:
        """计算变更请求率"""
        if not user_id:
            return 0.0
        
        # 获取用户创建的需求
        req_query = select(Requirement).where(
            and_(
                func.date(Requirement.created_at) >= start_date,
                func.date(Requirement.created_at) <= end_date,
                Requirement.creator_id == user_id
            )
        )
        
        if project_id:
            req_query = req_query.where(Requirement.project_id == project_id)
        
        req_result = await self.db.execute(req_query)
        requirements = req_result.scalars().all()
        
        if not requirements:
            return 0.0
        
        # 获取这些需求的变更请求
        req_ids = [req.id for req in requirements]
        change_query = select(RequirementChangeRequest).where(
            RequirementChangeRequest.requirement_id.in_(req_ids)
        )
        
        change_result = await self.db.execute(change_query)
        change_requests = change_result.scalars().all()
        
        return len(change_requests) / len(requirements)
    
    async def _calculate_user_collaboration_metrics(self, user_id: Optional[int], project_id: Optional[int],
                                                  start_date: date, end_date: date) -> Dict[str, Any]:
        """计算用户协作指标"""
        if not user_id:
            return {'reviews_participated': 0, 'comments_provided': 0, 'collaboration_score': 0.0}
        
        # 获取参与的评审
        review_query = select(RequirementReview).where(
            and_(
                func.date(RequirementReview.created_at) >= start_date,
                func.date(RequirementReview.created_at) <= end_date
            )
        )
        
        if project_id:
            review_query = review_query.join(Requirement).where(Requirement.project_id == project_id)
        
        review_result = await self.db.execute(review_query)
        all_reviews = review_result.scalars().all()
        
        # 计算参与的评审数量（作为评审人员）
        participated_reviews = 0
        for review in all_reviews:
            if review.reviewers and user_id in review.reviewers:
                participated_reviews += 1
        
        # 获取提供的评论
        comment_query = select(RequirementReviewComment).where(
            and_(
                func.date(RequirementReviewComment.created_at) >= start_date,
                func.date(RequirementReviewComment.created_at) <= end_date,
                RequirementReviewComment.reviewer_id == user_id
            )
        )
        
        if project_id:
            comment_query = comment_query.join(RequirementReview).join(Requirement)\
                                       .where(Requirement.project_id == project_id)
        
        comment_result = await self.db.execute(comment_query)
        comments = comment_result.scalars().all()
        
        comments_provided = len(comments)
        
        # 计算协作评分
        collaboration_score = min(1.0, (participated_reviews * 0.6 + comments_provided * 0.4) / 10)
        
        return {
            'reviews_participated': participated_reviews,
            'comments_provided': comments_provided,
            'collaboration_score': collaboration_score
        }
    
    def _calculate_overall_performance_score(self, productivity: float, quality: float, 
                                           review_success: float, change_rate: float, 
                                           collaboration: float) -> float:
        """计算综合绩效评分"""
        # 变更请求率越低越好，所以要反转
        change_score = max(0, 1 - change_rate)
        
        overall_score = (
            productivity * 0.3 +
            quality * 0.25 +
            review_success * 0.2 +
            change_score * 0.15 +
            collaboration * 0.1
        )
        
        return min(1.0, max(0.0, overall_score))