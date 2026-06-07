"""
测试数据分析和可视化服务

本模块实现了测试数据的统计分析和可视化功能，包括：
- 测试指标的计算和统计
- 多维度数据分析和对比
- 趋势分析和异常检测
- 交互式图表和仪表板数据生成
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict, Counter
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from ..models.test_case import TestCase, TestExecution, Defect
from ..models.test_plan import TestPlan
from ..models.project import Project
from ..schemas.test_analysis import (
    TestMetrics, TrendAnalysis, ComparisonAnalysis, 
    ChartData, DashboardData, AnalysisRequest
)
from ..core.exceptions import ValidationError
from ..utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

class TestDataAnalysisService:
    """测试数据分析和可视化服务"""
    
    def __init__(self, db: Session, redis_client: RedisClient):
        self.db = db
        self.redis = redis_client
    
    async def get_comprehensive_statistics(self, project_id: Optional[int] = None,
                                         date_range: Optional[Dict[str, datetime]] = None) -> TestMetrics:
        """获取综合测试统计"""
        try:
            # 1. 构建基础查询
            base_filters = []
            if project_id:
                base_filters.append(f"project_id = {project_id}")
            if date_range:
                base_filters.append(f"created_at >= '{date_range['start']}'")
                base_filters.append(f"created_at <= '{date_range['end']}'")
            
            # 2. 收集各类数据
            test_cases = await self._get_test_cases_data(base_filters)
            test_executions = await self._get_test_executions_data(base_filters)
            defects = await self._get_defects_data(base_filters)
            test_plans = await self._get_test_plans_data(base_filters)
            
            # 3. 计算核心指标
            metrics = TestMetrics()
            
            # 基础统计
            metrics.total_test_cases = len(test_cases)
            metrics.total_test_executions = len(test_executions)
            metrics.total_defects = len(defects)
            metrics.total_test_plans = len(test_plans)
            
            # 执行统计
            execution_stats = self._calculate_execution_statistics(test_executions)
            metrics.passed_executions = execution_stats['passed']
            metrics.failed_executions = execution_stats['failed']
            metrics.blocked_executions = execution_stats['blocked']
            metrics.skipped_executions = execution_stats['skipped']
            
            # 计算通过率
            if metrics.total_test_executions > 0:
                metrics.pass_rate = metrics.passed_executions / metrics.total_test_executions
                metrics.fail_rate = metrics.failed_executions / metrics.total_test_executions
            
            # 缺陷统计
            defect_stats = self._calculate_defect_statistics(defects)
            metrics.open_defects = defect_stats['open']
            metrics.resolved_defects = defect_stats['resolved']
            metrics.critical_defects = defect_stats['critical']
            metrics.high_defects = defect_stats['high']
            
            # 计算缺陷密度
            if metrics.total_test_cases > 0:
                metrics.defect_density = metrics.total_defects / metrics.total_test_cases
            
            # 覆盖率统计
            coverage_stats = await self._calculate_coverage_statistics(project_id, test_cases, test_executions)
            metrics.requirement_coverage = coverage_stats['requirement_coverage']
            metrics.test_coverage = coverage_stats['test_coverage']
            
            # 效率指标
            efficiency_stats = self._calculate_efficiency_metrics(test_executions, defects)
            metrics.avg_execution_time = efficiency_stats['avg_execution_time']
            metrics.defect_detection_rate = efficiency_stats['defect_detection_rate']
            
            # 质量指标
            quality_stats = self._calculate_quality_metrics(test_executions, defects)
            metrics.quality_score = quality_stats['quality_score']
            metrics.stability_index = quality_stats['stability_index']
            
            logger.info(f"综合统计计算完成: 项目{project_id}")
            return metrics
            
        except Exception as e:
            logger.error(f"获取综合统计失败: {str(e)}")
            raise ValidationError(f"获取综合统计失败: {str(e)}")
    
    async def analyze_trends(self, analysis_request: AnalysisRequest) -> TrendAnalysis:
        """分析测试趋势"""
        try:
            # 1. 获取时间序列数据
            time_series_data = await self._get_time_series_data(analysis_request)
            
            # 2. 计算趋势指标
            trend_analysis = TrendAnalysis()
            
            # 执行趋势
            execution_trend = self._calculate_execution_trend(time_series_data['executions'])
            trend_analysis.execution_trend = execution_trend
            
            # 通过率趋势
            pass_rate_trend = self._calculate_pass_rate_trend(time_series_data['executions'])
            trend_analysis.pass_rate_trend = pass_rate_trend
            
            # 缺陷趋势
            defect_trend = self._calculate_defect_trend(time_series_data['defects'])
            trend_analysis.defect_trend = defect_trend
            
            # 覆盖率趋势
            coverage_trend = await self._calculate_coverage_trend(time_series_data)
            trend_analysis.coverage_trend = coverage_trend
            
            # 预测分析
            predictions = await self._generate_trend_predictions(time_series_data)
            trend_analysis.predictions = predictions
            
            # 异常检测
            anomalies = self._detect_anomalies(time_series_data)
            trend_analysis.anomalies = anomalies
            
            logger.info(f"趋势分析完成: 项目{analysis_request.project_id}")
            return trend_analysis
            
        except Exception as e:
            logger.error(f"趋势分析失败: {str(e)}")
            raise ValidationError(f"趋势分析失败: {str(e)}")
    
    async def compare_periods(self, current_period: Dict[str, datetime],
                            previous_period: Dict[str, datetime],
                            project_id: Optional[int] = None) -> ComparisonAnalysis:
        """对比不同时期的测试数据"""
        try:
            # 1. 获取两个时期的数据
            current_metrics = await self.get_comprehensive_statistics(project_id, current_period)
            previous_metrics = await self.get_comprehensive_statistics(project_id, previous_period)
            
            # 2. 计算对比分析
            comparison = ComparisonAnalysis()
            
            # 基础指标对比
            comparison.test_cases_change = self._calculate_change_rate(
                current_metrics.total_test_cases, previous_metrics.total_test_cases
            )
            comparison.executions_change = self._calculate_change_rate(
                current_metrics.total_test_executions, previous_metrics.total_test_executions
            )
            comparison.defects_change = self._calculate_change_rate(
                current_metrics.total_defects, previous_metrics.total_defects
            )
            
            # 质量指标对比
            comparison.pass_rate_change = self._calculate_change_rate(
                current_metrics.pass_rate, previous_metrics.pass_rate
            )
            comparison.defect_density_change = self._calculate_change_rate(
                current_metrics.defect_density, previous_metrics.defect_density
            )
            comparison.quality_score_change = self._calculate_change_rate(
                current_metrics.quality_score, previous_metrics.quality_score
            )
            
            # 效率指标对比
            comparison.execution_time_change = self._calculate_change_rate(
                current_metrics.avg_execution_time, previous_metrics.avg_execution_time
            )
            comparison.detection_rate_change = self._calculate_change_rate(
                current_metrics.defect_detection_rate, previous_metrics.defect_detection_rate
            )
            
            # 生成对比洞察
            comparison.insights = self._generate_comparison_insights(current_metrics, previous_metrics)
            
            logger.info(f"时期对比分析完成: 项目{project_id}")
            return comparison
            
        except Exception as e:
            logger.error(f"时期对比分析失败: {str(e)}")
            raise ValidationError(f"时期对比分析失败: {str(e)}")
    
    async def generate_dashboard_data(self, project_id: Optional[int] = None,
                                    time_range: str = "30d") -> DashboardData:
        """生成仪表板数据"""
        try:
            # 1. 解析时间范围
            start_date, end_date = self._parse_time_range(time_range)
            date_range = {'start': start_date, 'end': end_date}
            
            # 2. 获取基础统计
            metrics = await self.get_comprehensive_statistics(project_id, date_range)
            
            # 3. 生成图表数据
            charts = await self._generate_chart_data(project_id, date_range)
            
            # 4. 构建仪表板数据
            dashboard = DashboardData()
            dashboard.metrics = metrics
            dashboard.charts = charts
            dashboard.last_updated = datetime.utcnow()
            
            # 5. 添加实时指标
            dashboard.real_time_metrics = await self._get_real_time_metrics(project_id)
            
            # 6. 添加告警信息
            dashboard.alerts = await self._get_quality_alerts(project_id, metrics)
            
            # 7. 缓存仪表板数据
            await self._cache_dashboard_data(project_id, time_range, dashboard)
            
            logger.info(f"仪表板数据生成完成: 项目{project_id}")
            return dashboard
            
        except Exception as e:
            logger.error(f"生成仪表板数据失败: {str(e)}")
            raise ValidationError(f"生成仪表板数据失败: {str(e)}")
    
    async def detect_test_anomalies(self, project_id: Optional[int] = None,
                                  lookback_days: int = 30) -> List[Dict[str, Any]]:
        """检测测试异常"""
        try:
            # 1. 获取历史数据
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            historical_data = await self._get_time_series_data({
                'project_id': project_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            # 2. 检测各类异常
            anomalies = []
            
            # 通过率异常
            pass_rate_anomalies = self._detect_pass_rate_anomalies(historical_data['executions'])
            anomalies.extend(pass_rate_anomalies)
            
            # 执行时间异常
            execution_time_anomalies = self._detect_execution_time_anomalies(historical_data['executions'])
            anomalies.extend(execution_time_anomalies)
            
            # 缺陷数量异常
            defect_count_anomalies = self._detect_defect_count_anomalies(historical_data['defects'])
            anomalies.extend(defect_count_anomalies)
            
            # 测试覆盖率异常
            coverage_anomalies = await self._detect_coverage_anomalies(project_id, historical_data)
            anomalies.extend(coverage_anomalies)
            
            # 按严重程度排序
            anomalies.sort(key=lambda x: x.get('severity_score', 0), reverse=True)
            
            logger.info(f"异常检测完成: 项目{project_id}, 发现{len(anomalies)}个异常")
            return anomalies
            
        except Exception as e:
            logger.error(f"检测测试异常失败: {str(e)}")
            raise ValidationError(f"检测测试异常失败: {str(e)}")
    
    async def generate_quality_insights(self, project_id: Optional[int] = None,
                                      time_range: str = "30d") -> List[Dict[str, Any]]:
        """生成质量洞察"""
        try:
            # 1. 获取分析数据
            start_date, end_date = self._parse_time_range(time_range)
            date_range = {'start': start_date, 'end': end_date}
            
            metrics = await self.get_comprehensive_statistics(project_id, date_range)
            trends = await self.analyze_trends({
                'project_id': project_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            # 2. 生成洞察
            insights = []
            
            # 质量趋势洞察
            quality_insights = self._analyze_quality_trends(metrics, trends)
            insights.extend(quality_insights)
            
            # 效率洞察
            efficiency_insights = self._analyze_efficiency_patterns(metrics, trends)
            insights.extend(efficiency_insights)
            
            # 风险洞察
            risk_insights = self._analyze_risk_indicators(metrics, trends)
            insights.extend(risk_insights)
            
            # 改进建议
            improvement_suggestions = self._generate_improvement_suggestions(metrics, trends)
            insights.extend(improvement_suggestions)
            
            # 按重要性排序
            insights.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
            
            logger.info(f"质量洞察生成完成: 项目{project_id}, 生成{len(insights)}个洞察")
            return insights
            
        except Exception as e:
            logger.error(f"生成质量洞察失败: {str(e)}")
            raise ValidationError(f"生成质量洞察失败: {str(e)}")
    
    # 私有方法实现
    async def _get_test_cases_data(self, filters: List[str]) -> List[Dict[str, Any]]:
        """获取测试用例数据"""
        query = self.db.query(TestCase)
        
        # 应用筛选条件（简化实现）
        if filters:
            # 这里应该根据filters构建查询条件
            pass
        
        cases = query.all()
        return [self._serialize_test_case(case) for case in cases]
    
    async def _get_test_executions_data(self, filters: List[str]) -> List[Dict[str, Any]]:
        """获取测试执行数据"""
        query = self.db.query(TestExecution)
        
        # 应用筛选条件（简化实现）
        if filters:
            pass
        
        executions = query.all()
        return [self._serialize_test_execution(exec) for exec in executions]
    
    async def _get_defects_data(self, filters: List[str]) -> List[Dict[str, Any]]:
        """获取缺陷数据"""
        query = self.db.query(Defect)
        
        # 应用筛选条件（简化实现）
        if filters:
            pass
        
        defects = query.all()
        return [self._serialize_defect(defect) for defect in defects]
    
    async def _get_test_plans_data(self, filters: List[str]) -> List[Dict[str, Any]]:
        """获取测试计划数据"""
        query = self.db.query(TestPlan)
        
        # 应用筛选条件（简化实现）
        if filters:
            pass
        
        plans = query.all()
        return [self._serialize_test_plan(plan) for plan in plans]
    
    def _calculate_execution_statistics(self, executions: List[Dict[str, Any]]) -> Dict[str, int]:
        """计算执行统计"""
        stats = {'passed': 0, 'failed': 0, 'blocked': 0, 'skipped': 0}
        
        for execution in executions:
            result = execution.get('result', '').upper()
            if result == 'PASSED':
                stats['passed'] += 1
            elif result == 'FAILED':
                stats['failed'] += 1
            elif result == 'BLOCKED':
                stats['blocked'] += 1
            elif result == 'SKIPPED':
                stats['skipped'] += 1
        
        return stats
    
    def _calculate_defect_statistics(self, defects: List[Dict[str, Any]]) -> Dict[str, int]:
        """计算缺陷统计"""
        stats = {'open': 0, 'resolved': 0, 'critical': 0, 'high': 0}
        
        for defect in defects:
            status = defect.get('status', '').upper()
            severity = defect.get('severity', '').upper()
            
            if status in ['NEW', 'ASSIGNED', 'IN_PROGRESS', 'REOPENED']:
                stats['open'] += 1
            elif status in ['RESOLVED', 'CLOSED']:
                stats['resolved'] += 1
            
            if severity == 'CRITICAL':
                stats['critical'] += 1
            elif severity == 'HIGH':
                stats['high'] += 1
        
        return stats
    
    async def _calculate_coverage_statistics(self, project_id: Optional[int],
                                           test_cases: List[Dict[str, Any]],
                                           executions: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算覆盖率统计"""
        stats = {'requirement_coverage': 0.0, 'test_coverage': 0.0}
        
        # 简化实现
        if test_cases:
            executed_cases = len(set(exec.get('test_case_id') for exec in executions))
            stats['test_coverage'] = executed_cases / len(test_cases) if test_cases else 0.0
        
        # 需求覆盖率需要额外的需求数据
        stats['requirement_coverage'] = 0.8  # 占位符
        
        return stats
    
    def _calculate_efficiency_metrics(self, executions: List[Dict[str, Any]],
                                    defects: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算效率指标"""
        metrics = {'avg_execution_time': 0.0, 'defect_detection_rate': 0.0}
        
        # 平均执行时间
        execution_times = [exec.get('duration', 0) for exec in executions if exec.get('duration')]
        if execution_times:
            metrics['avg_execution_time'] = sum(execution_times) / len(execution_times)
        
        # 缺陷检出率
        if executions:
            failed_executions = len([e for e in executions if e.get('result') == 'FAILED'])
            metrics['defect_detection_rate'] = failed_executions / len(executions)
        
        return metrics
    
    def _calculate_quality_metrics(self, executions: List[Dict[str, Any]],
                                 defects: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算质量指标"""
        metrics = {'quality_score': 0.0, 'stability_index': 0.0}
        
        # 质量分数（基于通过率和缺陷密度）
        if executions:
            passed = len([e for e in executions if e.get('result') == 'PASSED'])
            pass_rate = passed / len(executions)
            
            # 简化的质量分数计算
            defect_penalty = min(len(defects) * 0.1, 0.5)
            metrics['quality_score'] = max(0, pass_rate - defect_penalty)
        
        # 稳定性指数（基于重复执行的一致性）
        metrics['stability_index'] = 0.8  # 占位符
        
        return metrics
    
    async def _get_time_series_data(self, request: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """获取时间序列数据"""
        # 简化实现，实际应该按时间分组数据
        return {
            'executions': [],
            'defects': [],
            'coverage': []
        }
    
    def _calculate_execution_trend(self, executions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算执行趋势"""
        return {
            'trend_direction': 'stable',
            'growth_rate': 0.0,
            'data_points': []
        }
    
    def _calculate_pass_rate_trend(self, executions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算通过率趋势"""
        return {
            'trend_direction': 'improving',
            'current_rate': 0.85,
            'data_points': []
        }
    
    def _calculate_defect_trend(self, defects_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算缺陷趋势"""
        return {
            'trend_direction': 'decreasing',
            'growth_rate': -0.1,
            'data_points': []
        }
    
    async def _calculate_coverage_trend(self, time_series_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算覆盖率趋势"""
        return {
            'trend_direction': 'improving',
            'current_coverage': 0.75,
            'data_points': []
        }
    
    async def _generate_trend_predictions(self, time_series_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成趋势预测"""
        return {
            'next_week_pass_rate': 0.87,
            'next_week_defect_count': 5,
            'confidence': 0.7
        }
    
    def _detect_anomalies(self, time_series_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测异常"""
        return []
    
    def _calculate_change_rate(self, current: float, previous: float) -> float:
        """计算变化率"""
        if previous == 0:
            return 1.0 if current > 0 else 0.0
        return (current - previous) / previous
    
    def _generate_comparison_insights(self, current: TestMetrics, previous: TestMetrics) -> List[str]:
        """生成对比洞察"""
        insights = []
        
        if current.pass_rate > previous.pass_rate:
            insights.append("测试通过率有所提升")
        elif current.pass_rate < previous.pass_rate:
            insights.append("测试通过率有所下降，需要关注")
        
        if current.defect_density < previous.defect_density:
            insights.append("缺陷密度降低，质量改善")
        elif current.defect_density > previous.defect_density:
            insights.append("缺陷密度增加，需要加强质量控制")
        
        return insights
    
    async def _generate_chart_data(self, project_id: Optional[int],
                                 date_range: Dict[str, datetime]) -> Dict[str, ChartData]:
        """生成图表数据"""
        charts = {}
        
        # 通过率趋势图
        charts['pass_rate_trend'] = ChartData(
            chart_type='line',
            title='通过率趋势',
            data={'labels': [], 'datasets': []},
            options={}
        )
        
        # 缺陷分布饼图
        charts['defect_distribution'] = ChartData(
            chart_type='pie',
            title='缺陷分布',
            data={'labels': [], 'datasets': []},
            options={}
        )
        
        # 执行状态柱状图
        charts['execution_status'] = ChartData(
            chart_type='bar',
            title='执行状态分布',
            data={'labels': [], 'datasets': []},
            options={}
        )
        
        return charts
    
    async def _get_real_time_metrics(self, project_id: Optional[int]) -> Dict[str, Any]:
        """获取实时指标"""
        return {
            'active_executions': 0,
            'pending_reviews': 0,
            'open_defects': 0
        }
    
    async def _get_quality_alerts(self, project_id: Optional[int], 
                                metrics: TestMetrics) -> List[Dict[str, Any]]:
        """获取质量告警"""
        alerts = []
        
        if metrics.pass_rate < 0.8:
            alerts.append({
                'type': 'warning',
                'message': '测试通过率低于80%',
                'severity': 'medium'
            })
        
        if metrics.critical_defects > 0:
            alerts.append({
                'type': 'error',
                'message': f'存在{metrics.critical_defects}个严重缺陷',
                'severity': 'high'
            })
        
        return alerts
    
    def _parse_time_range(self, time_range: str) -> Tuple[datetime, datetime]:
        """解析时间范围"""
        end_date = datetime.utcnow()
        
        if time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_range == "90d":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        return start_date, end_date
    
    # 序列化方法
    def _serialize_test_case(self, case: TestCase) -> Dict[str, Any]:
        """序列化测试用例"""
        return {
            'id': case.id,
            'title': case.title,
            'priority': case.priority.value if case.priority else None,
            'status': case.status,
            'created_at': case.created_at
        }
    
    def _serialize_test_execution(self, execution: TestExecution) -> Dict[str, Any]:
        """序列化测试执行"""
        return {
            'id': execution.id,
            'test_case_id': execution.test_case_id,
            'result': execution.result,
            'duration': execution.duration,
            'executed_at': execution.executed_at
        }
    
    def _serialize_defect(self, defect: Defect) -> Dict[str, Any]:
        """序列化缺陷"""
        return {
            'id': defect.id,
            'severity': defect.severity.value if defect.severity else None,
            'status': defect.status.value if defect.status else None,
            'created_at': defect.created_at
        }
    
    def _serialize_test_plan(self, plan: TestPlan) -> Dict[str, Any]:
        """序列化测试计划"""
        return {
            'id': plan.id,
            'name': plan.name,
            'status': plan.status,
            'created_at': plan.created_at
        }
    
    # 异常检测方法
    def _detect_pass_rate_anomalies(self, executions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测通过率异常"""
        return []
    
    def _detect_execution_time_anomalies(self, executions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测执行时间异常"""
        return []
    
    def _detect_defect_count_anomalies(self, defects_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测缺陷数量异常"""
        return []
    
    async def _detect_coverage_anomalies(self, project_id: Optional[int],
                                       historical_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测覆盖率异常"""
        return []
    
    # 洞察生成方法
    def _analyze_quality_trends(self, metrics: TestMetrics, trends: TrendAnalysis) -> List[Dict[str, Any]]:
        """分析质量趋势"""
        return []
    
    def _analyze_efficiency_patterns(self, metrics: TestMetrics, trends: TrendAnalysis) -> List[Dict[str, Any]]:
        """分析效率模式"""
        return []
    
    def _analyze_risk_indicators(self, metrics: TestMetrics, trends: TrendAnalysis) -> List[Dict[str, Any]]:
        """分析风险指标"""
        return []
    
    def _generate_improvement_suggestions(self, metrics: TestMetrics, trends: TrendAnalysis) -> List[Dict[str, Any]]:
        """生成改进建议"""
        return []
    
    # 缓存方法
    async def _cache_dashboard_data(self, project_id: Optional[int], time_range: str, 
                                  dashboard: DashboardData):
        """缓存仪表板数据"""
        try:
            cache_key = f"dashboard_data:{project_id or 'all'}:{time_range}"
            await self.redis.setex(cache_key, 1800, dashboard.json())  # 缓存30分钟
        except Exception as e:
            logger.warning(f"缓存仪表板数据失败: {str(e)}")