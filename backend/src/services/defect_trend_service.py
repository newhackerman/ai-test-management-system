"""
缺陷趋势分析服务

本模块实现了缺陷趋势分析和预测功能，包括：
- 缺陷统计分析和趋势图表
- 多维度缺陷分布分析
- AI驱动的缺陷趋势预测
- 质量风险评估和改进建议
"""
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any, Tuple
from collections import Counter, defaultdict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import IntegrityError

from ..models.test_case import Defect, DefectStatus, DefectSeverity, DefectType, TestCasePriority
from ..models.project import Project
from ..schemas.defect import (
    DefectTrendAnalysis, DefectTrendData, DefectStatistics, DefectMetrics
)
from ..core.exceptions import ValidationError
from ..utils.redis_client import RedisClient
from .ai_assistant_service import AIAssistantService

logger = logging.getLogger(__name__)

class DefectTrendService:
    """缺陷趋势分析服务"""
    
    def __init__(self, db: Session, redis_client: RedisClient, ai_service: AIAssistantService):
        self.db = db
        self.redis = redis_client
        self.ai_service = ai_service
    
    async def analyze_defect_trends(self, project_id: Optional[int] = None, 
                                   time_range: str = "30d") -> DefectTrendAnalysis:
        """分析缺陷趋势"""
        try:
            # 1. 获取时间范围
            start_date, end_date = self._parse_time_range(time_range)
            
            # 2. 获取缺陷数据
            defects = await self._get_defects_for_trend_analysis(project_id, start_date, end_date)
            
            # 3. 生成趋势数据
            trend_data = self._generate_trend_data(defects, start_date, end_date)
            
            # 4. 计算统计指标
            statistics = await self._calculate_trend_statistics(defects)
            
            # 5. AI预测分析
            predictions = await self._predict_defect_trends(historical_trend, prediction_days)
            
            # 6. 生成改进建议
            suggestions = await self._generate_improvement_suggestions(statistics, predictions)
            
            # 7. 构建分析结果
            analysis = DefectTrendAnalysis(
                project_id=project_id or 0,
                time_range=time_range,
                trend_data=trend_data,
                statistics=statistics,
                predictions=predictions,
                suggestions=suggestions,
                generated_at=datetime.utcnow()
            )
            
            # 8. 缓存分析结果
            await self._cache_trend_analysis(project_id, time_range, analysis)
            
            logger.info(f"缺陷趋势分析完成: 项目{project_id}, 时间范围{time_range}, 共分析{len(defects)}个缺陷")
            return analysis
            
        except Exception as e:
            logger.error(f"缺陷趋势分析失败: {str(e)}")
            raise ValidationError(f"缺陷趋势分析失败: {str(e)}")
    
    async def get_defect_distribution_analysis(self, project_id: Optional[int] = None,
                                             time_range: str = "30d") -> Dict[str, Any]:
        """获取缺陷分布分析"""
        try:
            # 1. 获取时间范围
            start_date, end_date = self._parse_time_range(time_range)
            
            # 2. 获取缺陷数据
            defects = await self._get_defects_for_trend_analysis(project_id, start_date, end_date)
            
            # 3. 多维度分布分析
            distribution_analysis = {
                'by_type': self._analyze_type_distribution(defects),
                'by_severity': self._analyze_severity_distribution(defects),
                'by_status': self._analyze_status_distribution(defects),
                'by_priority': self._analyze_priority_distribution(defects),
                'by_module': self._analyze_module_distribution(defects),
                'by_reporter': self._analyze_reporter_distribution(defects),
                'by_assignee': self._analyze_assignee_distribution(defects),
                'by_time_of_day': self._analyze_time_of_day_distribution(defects),
                'by_day_of_week': self._analyze_day_of_week_distribution(defects),
                'by_resolution_time': self._analyze_resolution_time_distribution(defects)
            }
            
            # 4. 生成分布洞察
            insights = await self._generate_distribution_insights(distribution_analysis)
            distribution_analysis['insights'] = insights
            
            # 5. 缓存分析结果
            await self._cache_distribution_analysis(project_id, time_range, distribution_analysis)
            
            logger.info(f"缺陷分布分析完成: 项目{project_id}, 时间范围{time_range}")
            return distribution_analysis
            
        except Exception as e:
            logger.error(f"缺陷分布分析失败: {str(e)}")
            raise ValidationError(f"缺陷分布分析失败: {str(e)}")
    
    async def calculate_defect_metrics(self, project_id: Optional[int] = None,
                                     time_range: str = "30d") -> DefectMetrics:
        """计算缺陷度量指标"""
        try:
            # 1. 获取时间范围
            start_date, end_date = self._parse_time_range(time_range)
            
            # 2. 获取缺陷数据
            defects = await self._get_defects_for_trend_analysis(project_id, start_date, end_date)
            
            # 3. 计算各项指标
            metrics = DefectMetrics()
            
            # 缺陷发现率
            metrics.defect_discovery_rate = await self._calculate_defect_discovery_rate(defects, project_id)
            
            # 缺陷逃逸率
            metrics.defect_escape_rate = await self._calculate_defect_escape_rate(defects, project_id)
            
            # 缺陷移除效率
            metrics.defect_removal_efficiency = await self._calculate_defect_removal_efficiency(defects)
            
            # 平均解决时间
            metrics.mean_time_to_resolution = self._calculate_mean_time_to_resolution(defects)
            
            # 缺陷年龄分布
            metrics.defect_age_distribution = self._calculate_defect_age_distribution(defects)
            
            # 缺陷注入率
            metrics.defect_injection_rate = await self._calculate_defect_injection_rate(defects, project_id)
            
            # 4. 缓存度量结果
            await self._cache_defect_metrics(project_id, time_range, metrics)
            
            logger.info(f"缺陷度量计算完成: 项目{project_id}, 时间范围{time_range}")
            return metrics
            
        except Exception as e:
            logger.error(f"缺陷度量计算失败: {str(e)}")
            raise ValidationError(f"缺陷度量计算失败: {str(e)}")
    
    async def predict_defect_trends(self, project_id: Optional[int] = None, 
                                   prediction_days: int = 30) -> Dict[str, Any]:
        """预测缺陷趋势"""
        try:
            # 1. 获取历史数据（过去90天）
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=90)
            
            historical_defects = await self._get_defects_for_trend_analysis(project_id, start_date, end_date)
            
            # 2. 生成历史趋势数据
            historical_trend = self._generate_trend_data(historical_defects, start_date, end_date)
            
            # 3. 使用AI进行趋势预测
            ai_predictions = await self._ai_predict_trend_patterns(historical_trend, prediction_days)
            
            # 4. 使用统计方法进行趋势预测
            statistical_predictions = self._statistical_predict_trends(historical_trend, prediction_days)
            
            # 5. 合并预测结果
            combined_predictions = self._combine_predictions(ai_predictions, statistical_predictions)
            
            # 6. 生成预测洞察
            prediction_insights = await self._generate_prediction_insights(
                historical_trend, combined_predictions
            )
            
            prediction_result = {
                'project_id': project_id or 0,
                'prediction_period': f"{prediction_days}天",
                'historical_data': [trend.dict() for trend in historical_trend],
                'predictions': combined_predictions,
                'insights': prediction_insights,
                'confidence_level': self._calculate_prediction_confidence(historical_trend),
                'generated_at': datetime.utcnow()
            }
            
            # 7. 缓存预测结果
            await self._cache_prediction_result(project_id, prediction_days, prediction_result)
            
            logger.info(f"缺陷趋势预测完成: 项目{project_id}, 预测{prediction_days}天")
            return prediction_result
            
        except Exception as e:
            logger.error(f"缺陷趋势预测失败: {str(e)}")
            raise ValidationError(f"缺陷趋势预测失败: {str(e)}")
    
    async def assess_quality_risk(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """评估质量风险"""
        try:
            # 1. 获取最近30天的缺陷数据
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            recent_defects = await self._get_defects_for_trend_analysis(project_id, start_date, end_date)
            
            # 2. 计算风险指标
            risk_indicators = {
                'critical_defect_rate': self._calculate_critical_defect_rate(recent_defects),
                'defect_growth_rate': await self._calculate_defect_growth_rate(recent_defects),
                'resolution_delay_rate': self._calculate_resolution_delay_rate(recent_defects),
                'reopen_rate': self._calculate_reopen_rate(recent_defects),
                'test_coverage_gap': await self._calculate_test_coverage_gap(project_id),
                'defect_density': await self._calculate_current_defect_density(project_id)
            }
            
            # 3. 计算综合风险评分
            risk_score = self._calculate_overall_risk_score(risk_indicators)
            
            # 4. 确定风险等级
            risk_level = self._determine_risk_level(risk_score)
            
            # 5. 生成风险评估报告
            risk_assessment = {
                'project_id': project_id,
                'risk_score': risk_score,
                'risk_level': risk_level,
                'risk_indicators': risk_indicators,
                'risk_factors': self._identify_risk_factors(risk_indicators),
                'mitigation_recommendations': await self._generate_mitigation_recommendations(risk_indicators),
                'assessment_date': datetime.utcnow()
            }
            
            # 6. 缓存风险评估结果
            await self._cache_risk_assessment(project_id, risk_assessment)
            
            logger.info(f"质量风险评估完成: 项目{project_id}, 风险等级{risk_level}")
            return risk_assessment
            
        except Exception as e:
            logger.error(f"质量风险评估失败: {str(e)}")
            raise ValidationError(f"质量风险评估失败: {str(e)}")
    
    # 私有方法实现
    def _parse_time_range(self, time_range: str) -> Tuple[datetime, datetime]:
        """解析时间范围"""
        end_date = datetime.utcnow()
        
        if time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_range == "90d":
            start_date = end_date - timedelta(days=90)
        elif time_range == "180d":
            start_date = end_date - timedelta(days=180)
        elif time_range == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            # 默认30天
            start_date = end_date - timedelta(days=30)
        
        return start_date, end_date
    
    async def _get_defects_for_trend_analysis(self, project_id: Optional[int], 
                                            start_date: datetime, end_date: datetime) -> List[Defect]:
        """获取用于趋势分析的缺陷数据"""
        query = self.db.query(Defect).filter(
            Defect.created_at >= start_date,
            Defect.created_at <= end_date
        )
        
        if project_id:
            # 通过关联的测试用例获取项目缺陷
            from ..models.test_case import TestCase
            query = query.join(TestCase, Defect.test_case_id == TestCase.id).filter(
                TestCase.project_id == project_id
            )
        
        return query.order_by(Defect.created_at).all()
    
    def _generate_trend_data(self, defects: List[Defect], start_date: datetime, 
                           end_date: datetime) -> List[DefectTrendData]:
        """生成趋势数据"""
        # 按日期分组统计
        daily_stats = defaultdict(lambda: {
            'new_count': 0,
            'resolved_count': 0,
            'closed_count': 0,
            'total_count': 0
        })
        
        # 统计每日新增缺陷
        for defect in defects:
            date_key = defect.created_at.date()
            daily_stats[date_key]['new_count'] += 1
        
        # 统计每日解决缺陷
        for defect in defects:
            if defect.resolved_at:
                date_key = defect.resolved_at.date()
                daily_stats[date_key]['resolved_count'] += 1
        
        # 统计每日关闭缺陷
        for defect in defects:
            if defect.status == DefectStatus.CLOSED and defect.verified_at:
                date_key = defect.verified_at.date()
                daily_stats[date_key]['closed_count'] += 1
        
        # 生成趋势数据
        trend_data = []
        current_date = start_date.date()
        cumulative_total = 0
        
        while current_date <= end_date.date():
            stats = daily_stats[current_date]
            cumulative_total += max(0, stats['new_count'] - stats['closed_count'])
            
            trend_data.append(DefectTrendData(
                date=current_date,
                new_count=stats['new_count'],
                resolved_count=stats['resolved_count'],
                closed_count=stats['closed_count'],
                total_count=max(0, cumulative_total)
            ))
            
            current_date += timedelta(days=1)
        
        return trend_data
    
    async def _calculate_trend_statistics(self, defects: List[Defect]) -> DefectStatistics:
        """计算趋势统计"""
        stats = DefectStatistics()
        stats.total_defects = len(defects)
        
        # 按状态统计
        status_counts = Counter(defect.status for defect in defects)
        stats.new_defects = status_counts.get(DefectStatus.NEW, 0)
        stats.assigned_defects = status_counts.get(DefectStatus.ASSIGNED, 0)
        stats.in_progress_defects = status_counts.get(DefectStatus.IN_PROGRESS, 0)
        stats.resolved_defects = status_counts.get(DefectStatus.RESOLVED, 0)
        stats.closed_defects = status_counts.get(DefectStatus.CLOSED, 0)
        stats.reopened_defects = status_counts.get(DefectStatus.REOPENED, 0)
        
        # 按严重程度统计
        severity_counts = Counter(defect.severity for defect in defects)
        stats.critical_defects = severity_counts.get(DefectSeverity.CRITICAL, 0)
        stats.high_defects = severity_counts.get(DefectSeverity.HIGH, 0)
        stats.medium_defects = severity_counts.get(DefectSeverity.MEDIUM, 0)
        stats.low_defects = severity_counts.get(DefectSeverity.LOW, 0)
        
        # 按类型统计
        type_counts = Counter(defect.defect_type for defect in defects)
        stats.functional_defects = type_counts.get(DefectType.FUNCTIONAL, 0)
        stats.performance_defects = type_counts.get(DefectType.PERFORMANCE, 0)
        stats.security_defects = type_counts.get(DefectType.SECURITY, 0)
        stats.usability_defects = type_counts.get(DefectType.USABILITY, 0)
        
        # 计算质量指标
        if stats.total_defects > 0:
            stats.resolution_rate = (stats.resolved_defects + stats.closed_defects) / stats.total_defects
            stats.reopen_rate = stats.reopened_defects / stats.total_defects
        
        # 计算平均解决时间
        resolved_defects = [d for d in defects if d.resolved_at and d.reported_at]
        if resolved_defects:
            total_resolution_time = sum(
                (d.resolved_at - d.reported_at).total_seconds() / 3600 
                for d in resolved_defects
            )
            stats.avg_resolution_time = total_resolution_time / len(resolved_defects)
        
        return stats
    
    # 分布分析方法
    def _analyze_type_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析类型分布"""
        type_counts = Counter(defect.defect_type.value for defect in defects)
        total = len(defects)
        
        return {
            'counts': dict(type_counts),
            'percentages': {k: (v/total)*100 for k, v in type_counts.items()} if total > 0 else {},
            'total': total
        }
    
    def _analyze_severity_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析严重程度分布"""
        severity_counts = Counter(defect.severity.value for defect in defects)
        total = len(defects)
        
        return {
            'counts': dict(severity_counts),
            'percentages': {k: (v/total)*100 for k, v in severity_counts.items()} if total > 0 else {},
            'total': total
        }
    
    def _analyze_status_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析状态分布"""
        status_counts = Counter(defect.status.value for defect in defects)
        total = len(defects)
        
        return {
            'counts': dict(status_counts),
            'percentages': {k: (v/total)*100 for k, v in status_counts.items()} if total > 0 else {},
            'total': total
        }
    
    def _analyze_priority_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析优先级分布"""
        priority_counts = Counter(defect.priority.value for defect in defects)
        total = len(defects)
        
        return {
            'counts': dict(priority_counts),
            'percentages': {k: (v/total)*100 for k, v in priority_counts.items()} if total > 0 else {},
            'total': total
        }
    
    def _analyze_module_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析模块分布"""
        module_counts = defaultdict(int)
        
        for defect in defects:
            if defect.test_case and defect.test_case.module:
                module_counts[defect.test_case.module] += 1
            else:
                module_counts['未知模块'] += 1
        
        total = len(defects)
        
        return {
            'counts': dict(module_counts),
            'percentages': {k: (v/total)*100 for k, v in module_counts.items()} if total > 0 else {},
            'total': total
        }
    
    def _analyze_reporter_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析报告人分布"""
        reporter_counts = Counter(str(defect.reporter_id) for defect in defects)
        total = len(defects)
        
        return {
            'counts': dict(reporter_counts),
            'percentages': {k: (v/total)*100 for k, v in reporter_counts.items()} if total > 0 else {},
            'top_reporters': reporter_counts.most_common(5),
            'total': total
        }
    
    def _analyze_assignee_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析分配人分布"""
        assignee_counts = Counter(
            str(defect.assignee_id) if defect.assignee_id else '未分配' 
            for defect in defects
        )
        total = len(defects)
        
        return {
            'counts': dict(assignee_counts),
            'percentages': {k: (v/total)*100 for k, v in assignee_counts.items()} if total > 0 else {},
            'top_assignees': assignee_counts.most_common(5),
            'total': total
        }
    
    def _analyze_time_of_day_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析一天中的时间分布"""
        hour_counts = Counter(defect.created_at.hour for defect in defects)
        total = len(defects)
        
        # 按时间段分组
        time_periods = {
            '早晨(6-12)': sum(hour_counts[h] for h in range(6, 12)),
            '下午(12-18)': sum(hour_counts[h] for h in range(12, 18)),
            '晚上(18-24)': sum(hour_counts[h] for h in range(18, 24)),
            '深夜(0-6)': sum(hour_counts[h] for h in range(0, 6))
        }
        
        return {
            'hourly_counts': dict(hour_counts),
            'period_counts': time_periods,
            'percentages': {k: (v/total)*100 for k, v in time_periods.items()} if total > 0 else {},
            'total': total
        }
    
    def _analyze_day_of_week_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析星期分布"""
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday_counts = Counter(defect.created_at.weekday() for defect in defects)
        
        weekday_distribution = {
            weekday_names[day]: weekday_counts[day] for day in range(7)
        }
        
        total = len(defects)
        
        # 工作日vs周末
        weekdays = sum(weekday_counts[d] for d in range(5))
        weekends = sum(weekday_counts[d] for d in range(5, 7))
        
        return {
            'counts': weekday_distribution,
            'percentages': {k: (v/total)*100 for k, v in weekday_distribution.items()} if total > 0 else {},
            'workday_vs_weekend': {
                '工作日': weekdays,
                '周末': weekends
            },
            'total': total
        }
    
    def _analyze_resolution_time_distribution(self, defects: List[Defect]) -> Dict[str, Any]:
        """分析解决时间分布"""
        resolution_times = []
        
        for defect in defects:
            if defect.resolved_at and defect.reported_at:
                resolution_time = (defect.resolved_at - defect.reported_at).total_seconds() / 3600
                resolution_times.append(resolution_time)
        
        if not resolution_times:
            return {
                'counts': {},
                'percentages': {},
                'total': 0
            }
        
        # 按时间段分组
        time_ranges = {
            '1小时内': len([t for t in resolution_times if t <= 1]),
            '1-8小时': len([t for t in resolution_times if 1 < t <= 8]),
            '8-24小时': len([t for t in resolution_times if 8 < t <= 24]),
            '1-3天': len([t for t in resolution_times if 24 < t <= 72]),
            '3-7天': len([t for t in resolution_times if 72 < t <= 168]),
            '7天以上': len([t for t in resolution_times if t > 168])
        }
        
        total = len(resolution_times)
        
        return {
            'counts': time_ranges,
            'percentages': {k: (v/total)*100 for k, v in time_ranges.items()},
            'average_hours': sum(resolution_times) / total,
            'median_hours': sorted(resolution_times)[total // 2] if total > 0 else 0,
            'total': total
        }
    
    # 度量计算方法
    async def _calculate_defect_discovery_rate(self, defects: List[Defect], project_id: Optional[int]) -> float:
        """计算缺陷发现率"""
        # 简化实现：测试阶段发现的缺陷 / 总缺陷
        test_phase_defects = len([d for d in defects if d.test_execution_id])
        total_defects = len(defects)
        return test_phase_defects / total_defects if total_defects > 0 else 0
    
    async def _calculate_defect_escape_rate(self, defects: List[Defect], project_id: Optional[int]) -> float:
        """计算缺陷逃逸率"""
        # 简化实现：生产环境发现的缺陷 / 总缺陷
        production_defects = len([d for d in defects if 'production' in (d.test_environment or '').lower()])
        total_defects = len(defects)
        return production_defects / total_defects if total_defects > 0 else 0
    
    async def _calculate_defect_removal_efficiency(self, defects: List[Defect]) -> float:
        """计算缺陷移除效率"""
        resolved_defects = len([d for d in defects if d.status in [DefectStatus.RESOLVED, DefectStatus.CLOSED]])
        total_defects = len(defects)
        return resolved_defects / total_defects if total_defects > 0 else 0
    
    def _calculate_mean_time_to_resolution(self, defects: List[Defect]) -> float:
        """计算平均解决时间"""
        resolution_times = []
        
        for defect in defects:
            if defect.resolved_at and defect.reported_at:
                resolution_time = (defect.resolved_at - defect.reported_at).total_seconds() / 3600
                resolution_times.append(resolution_time)
        
        return sum(resolution_times) / len(resolution_times) if resolution_times else 0
    
    def _calculate_defect_age_distribution(self, defects: List[Defect]) -> Dict[str, int]:
        """计算缺陷年龄分布"""
        now = datetime.utcnow()
        age_distribution = {
            '1天内': 0,
            '1-7天': 0,
            '7-30天': 0,
            '30天以上': 0
        }
        
        for defect in defects:
            if defect.status not in [DefectStatus.RESOLVED, DefectStatus.CLOSED]:
                age_days = (now - defect.created_at).days
                if age_days <= 1:
                    age_distribution['1天内'] += 1
                elif age_days <= 7:
                    age_distribution['1-7天'] += 1
                elif age_days <= 30:
                    age_distribution['7-30天'] += 1
                else:
                    age_distribution['30天以上'] += 1
        
        return age_distribution
    
    async def _calculate_defect_injection_rate(self, defects: List[Defect], project_id: Optional[int]) -> float:
        """计算缺陷注入率"""
        # 简化实现：缺陷数 / 代码行数 * 1000
        total_defects = len(defects)
        # 这里需要获取项目的代码行数，简化为固定值
        lines_of_code = 10000  # 假设值
        return (total_defects / lines_of_code) * 1000
    
    # 风险评估方法
    def _calculate_critical_defect_rate(self, defects: List[Defect]) -> float:
        """计算严重缺陷率"""
        critical_defects = len([d for d in defects if d.severity == DefectSeverity.CRITICAL])
        total_defects = len(defects)
        return critical_defects / total_defects if total_defects > 0 else 0
    
    async def _calculate_defect_growth_rate(self, defects: List[Defect]) -> float:
        """计算缺陷增长率"""
        # 简化实现：比较最近15天和之前15天的缺陷数量
        now = datetime.utcnow()
        recent_15_days = now - timedelta(days=15)
        previous_15_days = now - timedelta(days=30)
        
        recent_count = len([d for d in defects if d.created_at >= recent_15_days])
        previous_count = len([d for d in defects if previous_15_days <= d.created_at < recent_15_days])
        
        if previous_count == 0:
            return 1.0 if recent_count > 0 else 0.0
        
        return (recent_count - previous_count) / previous_count
    
    def _calculate_resolution_delay_rate(self, defects: List[Defect]) -> float:
        """计算解决延迟率"""
        delayed_defects = 0
        total_resolved = 0
        
        for defect in defects:
            if defect.resolved_at and defect.assigned_at:
                total_resolved += 1
                resolution_time = (defect.resolved_at - defect.assigned_at).days
                # 假设超过3天为延迟
                if resolution_time > 3:
                    delayed_defects += 1
        
        return delayed_defects / total_resolved if total_resolved > 0 else 0
    
    def _calculate_reopen_rate(self, defects: List[Defect]) -> float:
        """计算重开率"""
        reopened_defects = len([d for d in defects if d.status == DefectStatus.REOPENED])
        total_defects = len(defects)
        return reopened_defects / total_defects if total_defects > 0 else 0
    
    async def _calculate_test_coverage_gap(self, project_id: Optional[int]) -> float:
        """计算测试覆盖率缺口"""
        # 简化实现，返回固定值
        return 0.2  # 20%的覆盖率缺口
    
    async def _calculate_current_defect_density(self, project_id: Optional[int]) -> float:
        """计算当前缺陷密度"""
        # 简化实现
        return 2.5  # 每千行代码2.5个缺陷
    
    def _calculate_overall_risk_score(self, risk_indicators: Dict[str, float]) -> float:
        """计算综合风险评分"""
        # 加权计算风险评分
        weights = {
            'critical_defect_rate': 0.25,
            'defect_growth_rate': 0.20,
            'resolution_delay_rate': 0.15,
            'reopen_rate': 0.15,
            'test_coverage_gap': 0.15,
            'defect_density': 0.10
        }
        
        risk_score = 0
        for indicator, value in risk_indicators.items():
            weight = weights.get(indicator, 0)
            risk_score += value * weight
        
        return min(1.0, risk_score)  # 限制在0-1之间
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """确定风险等级"""
        if risk_score >= 0.8:
            return "高风险"
        elif risk_score >= 0.6:
            return "中风险"
        elif risk_score >= 0.4:
            return "低风险"
        else:
            return "极低风险"
    
    def _identify_risk_factors(self, risk_indicators: Dict[str, float]) -> List[str]:
        """识别风险因素"""
        risk_factors = []
        
        if risk_indicators.get('critical_defect_rate', 0) > 0.1:
            risk_factors.append("严重缺陷比例过高")
        
        if risk_indicators.get('defect_growth_rate', 0) > 0.2:
            risk_factors.append("缺陷增长率过快")
        
        if risk_indicators.get('resolution_delay_rate', 0) > 0.3:
            risk_factors.append("缺陷解决延迟严重")
        
        if risk_indicators.get('reopen_rate', 0) > 0.15:
            risk_factors.append("缺陷重开率较高")
        
        if risk_indicators.get('test_coverage_gap', 0) > 0.2:
            risk_factors.append("测试覆盖率不足")
        
        return risk_factors
    
    async def _generate_mitigation_recommendations(self, risk_indicators: Dict[str, float]) -> List[str]:
        """生成缓解建议"""
        recommendations = []
        
        if risk_indicators.get('critical_defect_rate', 0) > 0.1:
            recommendations.append("加强代码审查和单元测试")
        
        if risk_indicators.get('defect_growth_rate', 0) > 0.2:
            recommendations.append("增加测试资源投入")
        
        if risk_indicators.get('resolution_delay_rate', 0) > 0.3:
            recommendations.append("优化缺陷处理流程和资源分配")
        
        if risk_indicators.get('reopen_rate', 0) > 0.15:
            recommendations.append("提高修复质量和验证标准")
        
        if risk_indicators.get('test_coverage_gap', 0) > 0.2:
            recommendations.append("扩大测试覆盖范围")
        
        return recommendations
    
    async def _generate_improvement_suggestions(self, statistics: DefectStatistics, 
                                              predictions: Optional[Dict[str, Any]]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 基于统计数据的建议
        if statistics.critical_defects > statistics.total_defects * 0.1:
            suggestions.append("严重缺陷比例较高，建议加强代码审查和单元测试")
        
        if statistics.avg_resolution_time > 72:  # 超过3天
            suggestions.append("缺陷解决时间较长，建议优化处理流程和资源分配")
        
        if statistics.reopen_rate > 0.15:  # 重开率超过15%
            suggestions.append("缺陷重开率较高，建议提高修复质量和验证标准")
        
        if statistics.functional_defects > statistics.total_defects * 0.6:
            suggestions.append("功能缺陷占比较高，建议加强需求分析和设计评审")
        
        # 基于预测数据的建议
        if predictions:
            trend_direction = predictions.get('trend_direction')
            if trend_direction == '上升':
                suggestions.append("预测缺陷数量将上升，建议提前准备测试资源")
            elif trend_direction == '下降':
                suggestions.append("预测缺陷数量将下降，当前改进措施有效")
        
        # 通用建议
        if not suggestions:
            suggestions.append("继续保持当前的质量管理水平")
        
        return suggestions
    
    # AI预测相关方法
    async def _ai_predict_trend_patterns(self, historical_trend: List[DefectTrendData], 
                                        prediction_days: int) -> Dict[str, Any]:
        """使用AI预测趋势模式"""
        try:
            # 构建预测提示词
            prediction_prompt = f"""
            基于以下缺陷趋势数据，请预测未来30天的缺陷趋势：
            
            趋势摘要：
            {self._summarize_trend_data(historical_trend)}
            
            缺陷模式：
            {self._analyze_defect_patterns(defects)}
            
            请提供：
            1. 未来30天预计新增缺陷数量
            2. 预计解决缺陷数量
            3. 趋势变化方向（上升/下降/稳定）
            4. 主要风险因素
            5. 置信度（0-1）
            
            请以JSON格式返回结果。
            """
            
            # 调用AI服务
            ai_response = await self.ai_service.analyze_text(prediction_prompt)
            
            # 解析AI响应
            return self._parse_prediction_response(ai_response)
            
        except Exception as e:
            logger.warning(f"AI预测失败: {str(e)}")
            return None
    
    def _statistical_predict_trends(self, historical_trend: List[DefectTrendData], 
                                   prediction_days: int) -> Dict[str, Any]:
        """使用统计方法进行趋势预测"""
        if len(historical_trend) < 7:
            return {'error': '历史数据不足'}
        
        # 提取新增缺陷数据
        new_counts = [trend.new_count for trend in historical_trend]
        
        # 简单移动平均预测
        window_size = min(7, len(new_counts))
        recent_average = sum(new_counts[-window_size:]) / window_size
        
        # 计算趋势
        if len(new_counts) >= 14:
            recent_avg = sum(new_counts[-7:]) / 7
            previous_avg = sum(new_counts[-14:-7]) / 7
            trend_direction = "上升" if recent_avg > previous_avg else "下降" if recent_avg < previous_avg else "稳定"
        else:
            trend_direction = "稳定"
        
        return {
            'predicted_daily_new': recent_average,
            'predicted_total_new': recent_average * prediction_days,
            'trend_direction': trend_direction,
            'confidence': 0.6
        }
    
    def _combine_predictions(self, ai_predictions: Optional[Dict[str, Any]], 
                           statistical_predictions: Dict[str, Any]) -> Dict[str, Any]:
        """合并预测结果"""
        if not ai_predictions:
            return statistical_predictions
        
        # 简单合并策略
        combined = statistical_predictions.copy()
        
        # 如果AI预测可用，取平均值
        if 'predicted_total_new' in ai_predictions:
            ai_total = ai_predictions['predicted_total_new']
            stat_total = statistical_predictions.get('predicted_total_new', ai_total)
            combined['predicted_total_new'] = (ai_total + stat_total) / 2
        
        # 置信度取较高者
        ai_confidence = ai_predictions.get('confidence', 0)
        stat_confidence = statistical_predictions.get('confidence', 0)
        combined['confidence'] = max(ai_confidence, stat_confidence)
        
        return combined
    
    async def _generate_prediction_insights(self, historical_trend: List[DefectTrendData],
                                          predictions: Dict[str, Any]) -> List[str]:
        """生成预测洞察"""
        insights = []
        
        if predictions.get('trend_direction') == '上升':
            insights.append("缺陷趋势呈上升态势，需要加强质量控制")
        elif predictions.get('trend_direction') == '下降':
            insights.append("缺陷趋势呈下降态势，质量改进措施见效")
        else:
            insights.append("缺陷趋势相对稳定")
        
        # 基于历史数据的洞察
        if len(historical_trend) > 0:
            avg_new = sum(t.new_count for t in historical_trend) / len(historical_trend)
            if avg_new > 5:
                insights.append("日均新增缺陷较多，建议关注测试效率")
        
        return insights
    
    def _calculate_prediction_confidence(self, historical_trend: List[DefectTrendData]) -> float:
        """计算预测置信度"""
        if len(historical_trend) < 7:
            return 0.3
        elif len(historical_trend) < 30:
            return 0.6
        else:
            return 0.8
    
    # 缓存相关方法
    async def _cache_trend_analysis(self, project_id: Optional[int], time_range: str, 
                                   analysis: DefectTrendAnalysis):
        """缓存趋势分析结果"""
        try:
            cache_key = f"defect_trend_analysis:{project_id or 'all'}:{time_range}"
            await self.redis.setex(cache_key, 3600, analysis.json())
        except Exception as e:
            logger.warning(f"缓存趋势分析失败: {str(e)}")
    
    async def _cache_distribution_analysis(self, project_id: Optional[int], time_range: str,
                                         analysis: Dict[str, Any]):
        """缓存分布分析结果"""
        try:
            cache_key = f"defect_distribution_analysis:{project_id or 'all'}:{time_range}"
            import json
            await self.redis.setex(cache_key, 3600, json.dumps(analysis, default=str))
        except Exception as e:
            logger.warning(f"缓存分布分析失败: {str(e)}")
    
    async def _cache_defect_metrics(self, project_id: Optional[int], time_range: str,
                                   metrics: DefectMetrics):
        """缓存度量结果"""
        try:
            cache_key = f"defect_metrics:{project_id or 'all'}:{time_range}"
            await self.redis.setex(cache_key, 3600, metrics.json())
        except Exception as e:
            logger.warning(f"缓存度量结果失败: {str(e)}")
    
    async def _cache_prediction_result(self, project_id: Optional[int], prediction_days: int,
                                     result: Dict[str, Any]):
        """缓存预测结果"""
        try:
            cache_key = f"defect_prediction:{project_id or 'all'}:{prediction_days}"
            import json
            await self.redis.setex(cache_key, 7200, json.dumps(result, default=str))
        except Exception as e:
            logger.warning(f"缓存预测结果失败: {str(e)}")
    
    async def _cache_risk_assessment(self, project_id: Optional[int], assessment: Dict[str, Any]):
        """缓存风险评估结果"""
        try:
            cache_key = f"quality_risk_assessment:{project_id or 'all'}"
            import json
            await self.redis.setex(cache_key, 3600, json.dumps(assessment, default=str))
        except Exception as e:
            logger.warning(f"缓存风险评估失败: {str(e)}")
    
    # 辅助方法
    def _summarize_trend_data(self, trend_data: List[DefectTrendData]) -> str:
        """总结趋势数据"""
        if not trend_data:
            return "无趋势数据"
        
        total_new = sum(t.new_count for t in trend_data)
        total_resolved = sum(t.resolved_count for t in trend_data)
        avg_new = total_new / len(trend_data)
        
        return f"总新增: {total_new}, 总解决: {total_resolved}, 日均新增: {avg_new:.1f}"
    
    def _analyze_defect_patterns(self, defects: List[Defect]) -> str:
        """分析缺陷模式"""
        if not defects:
            return "无缺陷数据"
        
        # 简化的模式分析
        type_counts = Counter(d.defect_type.value for d in defects)
        severity_counts = Counter(d.severity.value for d in defects)
        
        most_common_type = type_counts.most_common(1)[0] if type_counts else ("未知", 0)
        most_common_severity = severity_counts.most_common(1)[0] if severity_counts else ("未知", 0)
        
        return f"主要类型: {most_common_type[0]}, 主要严重程度: {most_common_severity[0]}"
    
    def _parse_prediction_response(self, ai_response: str) -> Dict[str, Any]:
        """解析预测响应"""
        try:
            import json
            if ai_response.strip().startswith('{'):
                return json.loads(ai_response)
        except:
            pass
        
        # 简化解析
        return {
            'predicted_total_new': 10,
            'trend_direction': '稳定',
            'confidence': 0.5
        }
    
    async def _generate_distribution_insights(self, distribution_analysis: Dict[str, Any]) -> List[str]:
        """生成分布洞察"""
        insights = []
        
        # 分析缺陷类型分布
        type_dist = distribution_analysis.get('by_type', {}).get('counts', {})
        if type_dist:
            max_type = max(type_dist.keys(), key=lambda x: type_dist[x])
            total = sum(type_dist.values())
            percentage = (type_dist[max_type] / total) * 100 if total > 0 else 0
            insights.append(f"最常见的缺陷类型是{max_type}，占比{percentage:.1f}%")
        
        # 分析严重程度分布
        severity_dist = distribution_analysis.get('by_severity', {}).get('counts', {})
        if severity_dist:
            critical_count = severity_dist.get('CRITICAL', 0)
            total = sum(severity_dist.values())
            if critical_count > 0 and total > 0:
                critical_percentage = (critical_count / total) * 100
                if critical_percentage > 10:
                    insights.append(f"严重缺陷占比{critical_percentage:.1f}%，需要重点关注")
        
        return insights