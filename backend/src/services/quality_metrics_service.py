"""
质量度量和评估服务

本模块实现了测试质量指标的计算、监控、趋势分析和改进建议功能，包括：
- 测试质量指标的计算和监控
- 质量趋势分析和预测
- 质量改进建议和最佳实践
- 质量基线和目标管理
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict
import statistics
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from ..models.test_case import TestCase, TestExecution, Defect
from ..models.test_plan import TestPlan
from ..models.project import Project
from ..schemas.test_analysis import (
    TestMetrics, QualityAlert, AlertSeverity, BenchmarkData, 
    BenchmarkAnalysis, PredictionResult, ReportInsight
)
from ..core.exceptions import ValidationError
from ..utils.redis_client import RedisClient

logger = logging.getLogger(__name__)

class QualityMetricsService:
    """质量度量和评估服务"""
    
    def __init__(self, db: Session, redis_client: RedisClient):
        self.db = db
        self.redis = redis_client
        
        # 质量指标定义
        self.quality_metrics = {
            'test_coverage': {
                'name': '测试覆盖率',
                'description': '已执行测试用例占总用例的比例',
                'unit': '%',
                'target': 0.85,
                'threshold_warning': 0.70,
                'threshold_critical': 0.50,
                'is_higher_better': True
            },
            'pass_rate': {
                'name': '测试通过率',
                'description': '通过的测试用例占已执行用例的比例',
                'unit': '%',
                'target': 0.95,
                'threshold_warning': 0.85,
                'threshold_critical': 0.70,
                'is_higher_better': True
            },
            'defect_density': {
                'name': '缺陷密度',
                'description': '每个测试用例发现的缺陷数量',
                'unit': '个/用例',
                'target': 0.1,
                'threshold_warning': 0.3,
                'threshold_critical': 0.5,
                'is_higher_better': False
            },
            'defect_escape_rate': {
                'name': '缺陷逃逸率',
                'description': '生产环境发现的缺陷占总缺陷的比例',
                'unit': '%',
                'target': 0.05,
                'threshold_warning': 0.10,
                'threshold_critical': 0.20,
                'is_higher_better': False
            },
            'test_efficiency': {
                'name': '测试效率',
                'description': '单位时间内完成的测试用例数量',
                'unit': '用例/小时',
                'target': 5.0,
                'threshold_warning': 3.0,
                'threshold_critical': 2.0,
                'is_higher_better': True
            },
            'defect_resolution_time': {
                'name': '缺陷解决时间',
                'description': '缺陷从发现到解决的平均时间',
                'unit': '小时',
                'target': 24.0,
                'threshold_warning': 48.0,
                'threshold_critical': 72.0,
                'is_higher_better': False
            },
            'test_automation_rate': {
                'name': '测试自动化率',
                'description': '自动化测试用例占总用例的比例',
                'unit': '%',
                'target': 0.70,
                'threshold_warning': 0.50,
                'threshold_critical': 0.30,
                'is_higher_better': True
            },
            'requirement_coverage': {
                'name': '需求覆盖率',
                'description': '被测试覆盖的需求占总需求的比例',
                'unit': '%',
                'target': 0.90,
                'threshold_warning': 0.80,
                'threshold_critical': 0.60,
                'is_higher_better': True
            }
        }
    
    async def calculate_quality_metrics(self, project_id: Optional[int] = None,
                                      date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, float]:
        """计算质量指标"""
        try:
            logger.info(f"开始计算质量指标: 项目{project_id}")
            
            # 1. 获取基础数据
            test_data = await self._get_test_data(project_id, date_range)
            
            # 2. 计算各项指标
            metrics = {}
            
            # 测试覆盖率
            metrics['test_coverage'] = await self._calculate_test_coverage(test_data)
            
            # 测试通过率
            metrics['pass_rate'] = await self._calculate_pass_rate(test_data)
            
            # 缺陷密度
            metrics['defect_density'] = await self._calculate_defect_density(test_data)
            
            # 缺陷逃逸率
            metrics['defect_escape_rate'] = await self._calculate_defect_escape_rate(test_data)
            
            # 测试效率
            metrics['test_efficiency'] = await self._calculate_test_efficiency(test_data)
            
            # 缺陷解决时间
            metrics['defect_resolution_time'] = await self._calculate_defect_resolution_time(test_data)
            
            # 测试自动化率
            metrics['test_automation_rate'] = await self._calculate_automation_rate(test_data)
            
            # 需求覆盖率
            metrics['requirement_coverage'] = await self._calculate_requirement_coverage(test_data)
            
            # 3. 缓存结果
            await self._cache_quality_metrics(project_id, metrics)
            
            logger.info(f"质量指标计算完成: 项目{project_id}, 指标数量{len(metrics)}")
            return metrics
            
        except Exception as e:
            logger.error(f"计算质量指标失败: {str(e)}")
            raise ValidationError(f"计算质量指标失败: {str(e)}")
    
    async def monitor_quality_metrics(self, project_id: Optional[int] = None) -> List[QualityAlert]:
        """监控质量指标并生成告警"""
        try:
            logger.info(f"开始监控质量指标: 项目{project_id}")
            
            # 1. 获取当前指标
            current_metrics = await self.calculate_quality_metrics(project_id)
            
            # 2. 检查阈值并生成告警
            alerts = []
            
            for metric_name, value in current_metrics.items():
                if metric_name not in self.quality_metrics:
                    continue
                
                metric_config = self.quality_metrics[metric_name]
                alert = await self._check_metric_threshold(
                    metric_name, value, metric_config, project_id
                )
                
                if alert:
                    alerts.append(alert)
            
            # 3. 检查趋势告警
            trend_alerts = await self._check_trend_alerts(project_id, current_metrics)
            alerts.extend(trend_alerts)
            
            # 4. 保存告警记录
            await self._save_quality_alerts(alerts)
            
            logger.info(f"质量监控完成: 项目{project_id}, 生成告警{len(alerts)}个")
            return alerts
            
        except Exception as e:
            logger.error(f"监控质量指标失败: {str(e)}")
            raise ValidationError(f"监控质量指标失败: {str(e)}")
    
    async def analyze_quality_trends(self, project_id: Optional[int] = None,
                                   days: int = 30) -> Dict[str, Any]:
        """分析质量趋势"""
        try:
            logger.info(f"开始分析质量趋势: 项目{project_id}, 天数{days}")
            
            # 1. 获取历史数据
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            historical_metrics = await self._get_historical_metrics(
                project_id, start_date, end_date
            )
            
            # 2. 计算趋势
            trends = {}
            
            for metric_name in self.quality_metrics.keys():
                if metric_name in historical_metrics:
                    trend_data = historical_metrics[metric_name]
                    trends[metric_name] = await self._calculate_metric_trend(
                        metric_name, trend_data
                    )
            
            # 3. 生成趋势预测
            predictions = await self._generate_trend_predictions(trends, days=7)
            
            # 4. 识别趋势异常
            anomalies = await self._detect_trend_anomalies(trends)
            
            result = {
                'trends': trends,
                'predictions': predictions,
                'anomalies': anomalies,
                'analysis_period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'days': days
                },
                'analyzed_at': datetime.utcnow()
            }
            
            logger.info(f"质量趋势分析完成: 项目{project_id}")
            return result
            
        except Exception as e:
            logger.error(f"分析质量趋势失败: {str(e)}")
            raise ValidationError(f"分析质量趋势失败: {str(e)}")
    
    async def generate_improvement_suggestions(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """生成质量改进建议"""
        try:
            logger.info(f"开始生成改进建议: 项目{project_id}")
            
            # 1. 获取当前指标和趋势
            current_metrics = await self.calculate_quality_metrics(project_id)
            trends = await self.analyze_quality_trends(project_id, days=30)
            
            # 2. 分析问题领域
            problem_areas = await self._identify_problem_areas(current_metrics, trends)
            
            # 3. 生成改进建议
            suggestions = []
            
            for area in problem_areas:
                area_suggestions = await self._generate_area_suggestions(area, current_metrics)
                suggestions.extend(area_suggestions)
            
            # 4. 添加最佳实践建议
            best_practices = await self._get_best_practices(current_metrics)
            suggestions.extend(best_practices)
            
            # 5. 按优先级排序
            suggestions.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
            
            logger.info(f"改进建议生成完成: 项目{project_id}, 建议数量{len(suggestions)}")
            return suggestions
            
        except Exception as e:
            logger.error(f"生成改进建议失败: {str(e)}")
            raise ValidationError(f"生成改进建议失败: {str(e)}")
    
    async def manage_quality_baselines(self, project_id: int, action: str, 
                                     baseline_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """管理质量基线"""
        try:
            logger.info(f"管理质量基线: 项目{project_id}, 操作{action}")
            
            if action == "create":
                return await self._create_quality_baseline(project_id, baseline_data)
            elif action == "update":
                return await self._update_quality_baseline(project_id, baseline_data)
            elif action == "get":
                return await self._get_quality_baseline(project_id)
            elif action == "compare":
                return await self._compare_with_baseline(project_id)
            else:
                raise ValidationError(f"不支持的操作: {action}")
                
        except Exception as e:
            logger.error(f"管理质量基线失败: {str(e)}")
            raise ValidationError(f"管理质量基线失败: {str(e)}")
    
    async def set_quality_targets(self, project_id: int, targets: Dict[str, float]) -> Dict[str, Any]:
        """设置质量目标"""
        try:
            logger.info(f"设置质量目标: 项目{project_id}")
            
            # 1. 验证目标值
            validated_targets = await self._validate_quality_targets(targets)
            
            # 2. 保存目标设置
            target_config = {
                'project_id': project_id,
                'targets': validated_targets,
                'set_at': datetime.utcnow(),
                'set_by': 'system'  # 实际应该从上下文获取用户ID
            }
            
            await self._save_quality_targets(project_id, target_config)
            
            # 3. 更新监控阈值
            await self._update_monitoring_thresholds(project_id, validated_targets)
            
            logger.info(f"质量目标设置完成: 项目{project_id}")
            return target_config
            
        except Exception as e:
            logger.error(f"设置质量目标失败: {str(e)}")
            raise ValidationError(f"设置质量目标失败: {str(e)}")
    
    async def benchmark_quality_metrics(self, project_id: Optional[int] = None) -> BenchmarkAnalysis:
        """基准对比分析"""
        try:
            logger.info(f"开始基准对比分析: 项目{project_id}")
            
            # 1. 获取当前指标
            current_metrics = await self.calculate_quality_metrics(project_id)
            
            # 2. 获取行业基准数据
            industry_benchmarks = await self._get_industry_benchmarks()
            
            # 3. 进行基准对比
            benchmarks = []
            
            for metric_name, current_value in current_metrics.items():
                if metric_name in industry_benchmarks:
                    benchmark = await self._create_benchmark_comparison(
                        metric_name, current_value, industry_benchmarks[metric_name]
                    )
                    benchmarks.append(benchmark)
            
            # 4. 计算整体评分
            overall_score = await self._calculate_overall_benchmark_score(benchmarks)
            
            # 5. 识别优势和改进领域
            strengths, improvement_areas = await self._analyze_benchmark_results(benchmarks)
            
            analysis = BenchmarkAnalysis(
                project_id=project_id,
                benchmarks=benchmarks,
                overall_score=overall_score,
                strengths=strengths,
                improvement_areas=improvement_areas
            )
            
            logger.info(f"基准对比分析完成: 项目{project_id}, 整体评分{overall_score}")
            return analysis
            
        except Exception as e:
            logger.error(f"基准对比分析失败: {str(e)}")
            raise ValidationError(f"基准对比分析失败: {str(e)}")
    
    # 私有方法实现
    async def _get_test_data(self, project_id: Optional[int], 
                           date_range: Optional[Dict[str, datetime]]) -> Dict[str, Any]:
        """获取测试数据"""
        data = {
            'test_cases': [],
            'test_executions': [],
            'defects': [],
            'test_plans': [],
            'requirements': []
        }
        
        # 构建查询条件
        filters = []
        if project_id:
            filters.append(f"project_id = {project_id}")
        if date_range:
            filters.append(f"created_at >= '{date_range['start']}'")
            filters.append(f"created_at <= '{date_range['end']}'")
        
        # 获取测试用例
        test_cases_query = self.db.query(TestCase)
        if project_id:
            # 这里需要通过test_plan关联到project
            pass
        data['test_cases'] = test_cases_query.all()
        
        # 获取测试执行
        executions_query = self.db.query(TestExecution)
        if date_range:
            executions_query = executions_query.filter(
                TestExecution.executed_at >= date_range['start'],
                TestExecution.executed_at <= date_range['end']
            )
        data['test_executions'] = executions_query.all()
        
        # 获取缺陷
        defects_query = self.db.query(Defect)
        if date_range:
            defects_query = defects_query.filter(
                Defect.created_at >= date_range['start'],
                Defect.created_at <= date_range['end']
            )
        data['defects'] = defects_query.all()
        
        # 获取测试计划
        plans_query = self.db.query(TestPlan)
        if project_id:
            plans_query = plans_query.filter(TestPlan.project_id == project_id)
        data['test_plans'] = plans_query.all()
        
        return data
    
    async def _calculate_test_coverage(self, test_data: Dict[str, Any]) -> float:
        """计算测试覆盖率"""
        test_cases = test_data['test_cases']
        test_executions = test_data['test_executions']
        
        if not test_cases:
            return 0.0
        
        executed_case_ids = set(exec.test_case_id for exec in test_executions)
        total_cases = len(test_cases)
        executed_cases = len(executed_case_ids)
        
        return executed_cases / total_cases if total_cases > 0 else 0.0
    
    async def _calculate_pass_rate(self, test_data: Dict[str, Any]) -> float:
        """计算测试通过率"""
        test_executions = test_data['test_executions']
        
        if not test_executions:
            return 0.0
        
        passed_executions = len([
            exec for exec in test_executions
            if str(getattr(exec, "execution_status", "")).replace("ExecutionStatus.", "").upper() == "PASSED"
            or getattr(exec, "result", None) == "PASSED"
        ])
        total_executions = len(test_executions)
        
        return passed_executions / total_executions if total_executions > 0 else 0.0
    
    async def _calculate_defect_density(self, test_data: Dict[str, Any]) -> float:
        """计算缺陷密度"""
        test_cases = test_data['test_cases']
        defects = test_data['defects']
        
        if not test_cases:
            return 0.0
        
        total_defects = len(defects)
        total_cases = len(test_cases)
        
        return total_defects / total_cases if total_cases > 0 else 0.0
    
    async def _calculate_defect_escape_rate(self, test_data: Dict[str, Any]) -> float:
        """计算缺陷逃逸率"""
        defects = test_data['defects']
        
        if not defects:
            return 0.0
        
        # 假设有字段标识缺陷是否在生产环境发现
        production_defects = len([d for d in defects if getattr(d, 'found_in_production', False)])
        total_defects = len(defects)
        
        return production_defects / total_defects if total_defects > 0 else 0.0
    
    async def _calculate_test_efficiency(self, test_data: Dict[str, Any]) -> float:
        """计算测试效率"""
        test_executions = test_data['test_executions']
        
        if not test_executions:
            return 0.0
        
        # 计算平均每小时执行的用例数
        total_duration = sum(exec.duration or 0 for exec in test_executions)  # 秒
        total_executions = len(test_executions)
        
        if total_duration == 0:
            return 0.0
        
        hours = total_duration / 3600  # 转换为小时
        return total_executions / hours if hours > 0 else 0.0
    
    async def _calculate_defect_resolution_time(self, test_data: Dict[str, Any]) -> float:
        """计算缺陷解决时间"""
        defects = test_data['defects']
        
        if not defects:
            return 0.0
        
        resolution_times = []
        for defect in defects:
            if defect.resolved_at and defect.created_at:
                resolution_time = (defect.resolved_at - defect.created_at).total_seconds() / 3600  # 小时
                resolution_times.append(resolution_time)
        
        return statistics.mean(resolution_times) if resolution_times else 0.0
    
    async def _calculate_automation_rate(self, test_data: Dict[str, Any]) -> float:
        """计算测试自动化率"""
        test_cases = test_data['test_cases']
        
        if not test_cases:
            return 0.0
        
        automated_cases = len([case for case in test_cases 
                             if getattr(case, 'automation_level', 'MANUAL') in ['SEMI_AUTO', 'FULL_AUTO']])
        total_cases = len(test_cases)
        
        return automated_cases / total_cases if total_cases > 0 else 0.0
    
    async def _calculate_requirement_coverage(self, test_data: Dict[str, Any]) -> float:
        """计算需求覆盖率"""
        test_cases = test_data['test_cases']
        
        if not test_cases:
            return 0.0
        
        # 获取被测试覆盖的需求ID
        covered_requirements = set()
        for case in test_cases:
            if hasattr(case, 'requirement_id') and case.requirement_id:
                covered_requirements.add(case.requirement_id)
        
        # 这里需要获取项目的总需求数，简化处理
        total_requirements = len(covered_requirements) * 1.2  # 假设覆盖了80%的需求
        
        return len(covered_requirements) / total_requirements if total_requirements > 0 else 0.0
    
    async def _check_metric_threshold(self, metric_name: str, value: float, 
                                    metric_config: Dict[str, Any], 
                                    project_id: Optional[int]) -> Optional[QualityAlert]:
        """检查指标阈值"""
        is_higher_better = metric_config['is_higher_better']
        warning_threshold = metric_config['threshold_warning']
        critical_threshold = metric_config['threshold_critical']
        
        severity = None
        message = ""
        
        if is_higher_better:
            if value < critical_threshold:
                severity = AlertSeverity.CRITICAL
                message = f"{metric_config['name']}过低: {value:.2%} < {critical_threshold:.2%}"
            elif value < warning_threshold:
                severity = AlertSeverity.HIGH
                message = f"{metric_config['name']}偏低: {value:.2%} < {warning_threshold:.2%}"
        else:
            if value > critical_threshold:
                severity = AlertSeverity.CRITICAL
                message = f"{metric_config['name']}过高: {value:.2%} > {critical_threshold:.2%}"
            elif value > warning_threshold:
                severity = AlertSeverity.HIGH
                message = f"{metric_config['name']}偏高: {value:.2%} > {warning_threshold:.2%}"
        
        if severity:
            return QualityAlert(
                id=f"metric_{metric_name}_{int(datetime.utcnow().timestamp())}",
                type="threshold",
                message=message,
                severity=severity,
                metric_name=metric_name,
                current_value=value,
                threshold_value=warning_threshold if severity == AlertSeverity.HIGH else critical_threshold,
                project_id=project_id
            )
        
        return None
    
    async def _check_trend_alerts(self, project_id: Optional[int], 
                                current_metrics: Dict[str, float]) -> List[QualityAlert]:
        """检查趋势告警"""
        alerts = []
        
        # 获取历史数据进行趋势分析
        try:
            trends = await self.analyze_quality_trends(project_id, days=7)
            
            for metric_name, trend_data in trends['trends'].items():
                if trend_data.get('trend_direction') == 'declining':
                    decline_rate = abs(trend_data.get('growth_rate', 0))
                    
                    if decline_rate > 0.1:  # 下降超过10%
                        alert = QualityAlert(
                            id=f"trend_{metric_name}_{int(datetime.utcnow().timestamp())}",
                            type="trend",
                            message=f"{self.quality_metrics[metric_name]['name']}呈下降趋势，下降幅度{decline_rate:.1%}",
                            severity=AlertSeverity.MEDIUM,
                            metric_name=metric_name,
                            current_value=current_metrics.get(metric_name, 0),
                            threshold_value=decline_rate,
                            project_id=project_id
                        )
                        alerts.append(alert)
        
        except Exception as e:
            logger.warning(f"检查趋势告警失败: {str(e)}")
        
        return alerts
    
    async def _get_historical_metrics(self, project_id: Optional[int], 
                                    start_date: datetime, end_date: datetime) -> Dict[str, List[Dict[str, Any]]]:
        """获取历史指标数据"""
        # 这里应该从数据库或缓存中获取历史指标数据
        # 简化实现，返回模拟数据
        historical_data = {}
        
        for metric_name in self.quality_metrics.keys():
            # 生成模拟的历史数据点
            data_points = []
            current_date = start_date
            
            while current_date <= end_date:
                # 模拟数据，实际应该从数据库查询
                value = 0.8 + (hash(f"{metric_name}_{current_date.date()}") % 100) / 500
                data_points.append({
                    'date': current_date,
                    'value': value,
                    'metric_name': metric_name
                })
                current_date += timedelta(days=1)
            
            historical_data[metric_name] = data_points
        
        return historical_data
    
    async def _calculate_metric_trend(self, metric_name: str, 
                                    trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算指标趋势"""
        if len(trend_data) < 2:
            return {
                'trend_direction': 'stable',
                'growth_rate': 0.0,
                'data_points': trend_data
            }
        
        values = [point['value'] for point in trend_data]
        
        # 计算线性趋势
        x = np.arange(len(values))
        y = np.array(values)
        
        # 简单线性回归
        slope = float(np.polyfit(x, y, 1)[0])
        
        # 确定趋势方向
        if abs(slope) < 0.01:
            trend_direction = 'stable'
        elif slope > 0:
            trend_direction = 'improving' if self.quality_metrics[metric_name]['is_higher_better'] else 'declining'
        else:
            trend_direction = 'declining' if self.quality_metrics[metric_name]['is_higher_better'] else 'improving'
        
        return {
            'trend_direction': trend_direction,
            'growth_rate': float(slope),
            'data_points': trend_data,
            'slope': float(slope)
        }
    
    async def _generate_trend_predictions(self, trends: Dict[str, Any], days: int = 7) -> Dict[str, Any]:
        """生成趋势预测"""
        predictions = {}
        
        for metric_name, trend_data in trends.items():
            slope = trend_data.get('slope', 0)
            current_value = trend_data['data_points'][-1]['value'] if trend_data['data_points'] else 0
            
            # 简单线性预测
            predicted_value = current_value + slope * days
            
            predictions[metric_name] = {
                'predicted_value': max(0, min(1, predicted_value)),  # 限制在0-1之间
                'confidence': 0.7,  # 简化的置信度
                'prediction_horizon': days
            }
        
        return predictions
    
    async def _detect_trend_anomalies(self, trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测趋势异常"""
        anomalies = []
        
        for metric_name, trend_data in trends.items():
            data_points = trend_data['data_points']
            
            if len(data_points) < 7:  # 需要足够的数据点
                continue
            
            values = [point['value'] for point in data_points]
            
            # 使用标准差检测异常值
            mean_value = statistics.mean(values)
            std_value = statistics.stdev(values) if len(values) > 1 else 0
            
            for i, point in enumerate(data_points):
                if abs(point['value'] - mean_value) > 2 * std_value:
                    anomalies.append({
                        'metric_name': metric_name,
                        'date': point['date'],
                        'value': point['value'],
                        'expected_range': {
                            'min': mean_value - 2 * std_value,
                            'max': mean_value + 2 * std_value
                        },
                        'severity_score': abs(point['value'] - mean_value) / std_value if std_value > 0 else 0,
                        'anomaly_type': 'outlier'
                    })
        
        return anomalies
    
    async def _identify_problem_areas(self, current_metrics: Dict[str, float], 
                                    trends: Dict[str, Any]) -> List[str]:
        """识别问题领域"""
        problem_areas = []
        
        for metric_name, value in current_metrics.items():
            if metric_name not in self.quality_metrics:
                continue
            
            metric_config = self.quality_metrics[metric_name]
            is_higher_better = metric_config['is_higher_better']
            warning_threshold = metric_config['threshold_warning']
            
            # 检查当前值是否低于阈值
            if is_higher_better and value < warning_threshold:
                problem_areas.append(metric_name)
            elif not is_higher_better and value > warning_threshold:
                problem_areas.append(metric_name)
            
            # 检查趋势是否恶化
            trend_data = trends.get('trends', {}).get(metric_name, {})
            if trend_data.get('trend_direction') == 'declining':
                if metric_name not in problem_areas:
                    problem_areas.append(metric_name)
        
        return problem_areas
    
    async def _generate_area_suggestions(self, area: str, 
                                       current_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """为特定领域生成改进建议"""
        suggestions = []
        
        if area == 'test_coverage':
            suggestions.append({
                'category': 'coverage',
                'title': '提高测试覆盖率',
                'description': '增加测试用例数量，确保所有功能模块都有相应的测试用例',
                'priority_score': 8.0,
                'actions': [
                    '分析未覆盖的功能模块',
                    '编写缺失的测试用例',
                    '定期审查测试覆盖率报告'
                ],
                'expected_impact': '提高测试覆盖率至85%以上'
            })
        
        elif area == 'pass_rate':
            suggestions.append({
                'category': 'quality',
                'title': '提高测试通过率',
                'description': '分析失败用例的根本原因，改进代码质量和测试用例设计',
                'priority_score': 9.0,
                'actions': [
                    '分析失败用例的根本原因',
                    '改进代码质量和开发流程',
                    '优化测试用例设计',
                    '加强代码审查'
                ],
                'expected_impact': '提高测试通过率至95%以上'
            })
        
        elif area == 'defect_density':
            suggestions.append({
                'category': 'quality',
                'title': '降低缺陷密度',
                'description': '通过改进开发流程和加强质量控制来减少缺陷数量',
                'priority_score': 8.5,
                'actions': [
                    '实施代码审查制度',
                    '加强单元测试',
                    '改进需求分析和设计',
                    '引入静态代码分析工具'
                ],
                'expected_impact': '将缺陷密度降低至0.1以下'
            })
        
        elif area == 'test_automation_rate':
            suggestions.append({
                'category': 'efficiency',
                'title': '提高测试自动化率',
                'description': '识别适合自动化的测试用例，逐步提高自动化覆盖率',
                'priority_score': 7.0,
                'actions': [
                    '识别适合自动化的测试用例',
                    '建立自动化测试框架',
                    '培训团队自动化测试技能',
                    '制定自动化测试策略'
                ],
                'expected_impact': '提高自动化率至70%以上'
            })
        
        return suggestions
    
    async def _get_best_practices(self, current_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """获取最佳实践建议"""
        best_practices = [
            {
                'category': 'process',
                'title': '建立持续集成流程',
                'description': '实施CI/CD流程，确保每次代码提交都能触发自动化测试',
                'priority_score': 6.0,
                'actions': [
                    '配置CI/CD管道',
                    '集成自动化测试',
                    '设置质量门禁',
                    '建立快速反馈机制'
                ],
                'expected_impact': '提高测试效率和代码质量'
            },
            {
                'category': 'metrics',
                'title': '建立质量度量体系',
                'description': '定期监控和分析质量指标，建立数据驱动的质量改进流程',
                'priority_score': 5.5,
                'actions': [
                    '定义关键质量指标',
                    '建立监控仪表板',
                    '定期质量评审',
                    '制定改进计划'
                ],
                'expected_impact': '建立可持续的质量改进机制'
            },
            {
                'category': 'team',
                'title': '加强团队质量意识',
                'description': '通过培训和文化建设提高团队的质量意识和技能',
                'priority_score': 5.0,
                'actions': [
                    '开展质量培训',
                    '分享最佳实践',
                    '建立质量文化',
                    '激励质量改进'
                ],
                'expected_impact': '提升团队整体质量水平'
            }
        ]
        
        return best_practices
    
    async def _create_quality_baseline(self, project_id: int, 
                                     baseline_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """创建质量基线"""
        if baseline_data:
            # 使用提供的基线数据
            baseline_metrics = baseline_data.get('metrics', {})
        else:
            # 使用当前指标作为基线
            baseline_metrics = await self.calculate_quality_metrics(project_id)
        
        baseline = {
            'project_id': project_id,
            'baseline_metrics': baseline_metrics,
            'created_at': datetime.utcnow(),
            'description': baseline_data.get('description', '项目质量基线') if baseline_data else '项目质量基线',
            'version': '1.0'
        }
        
        # 保存基线数据
        await self._save_quality_baseline(project_id, baseline)
        
        return baseline
    
    async def _update_quality_baseline(self, project_id: int, 
                                     baseline_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新质量基线"""
        existing_baseline = await self._get_quality_baseline(project_id)
        
        if not existing_baseline:
            return await self._create_quality_baseline(project_id, baseline_data)
        
        # 更新基线数据
        existing_baseline.update({
            'baseline_metrics': baseline_data.get('metrics', existing_baseline['baseline_metrics']),
            'updated_at': datetime.utcnow(),
            'description': baseline_data.get('description', existing_baseline['description']),
            'version': str(float(existing_baseline.get('version', '1.0')) + 0.1)
        })
        
        await self._save_quality_baseline(project_id, existing_baseline)
        
        return existing_baseline
    
    async def _get_quality_baseline(self, project_id: int) -> Optional[Dict[str, Any]]:
        """获取质量基线"""
        try:
            cache_key = f"quality_baseline:{project_id}"
            cached_baseline = await self.redis.get(cache_key)
            
            if cached_baseline:
                import json
                return json.loads(cached_baseline)
            
            # 从数据库获取（这里简化处理）
            return None
            
        except Exception as e:
            logger.warning(f"获取质量基线失败: {str(e)}")
            return None
    
    async def _compare_with_baseline(self, project_id: int) -> Dict[str, Any]:
        """与基线对比"""
        baseline = await self._get_quality_baseline(project_id)
        if not baseline:
            raise ValidationError("项目尚未设置质量基线")
        
        current_metrics = await self.calculate_quality_metrics(project_id)
        baseline_metrics = baseline['baseline_metrics']
        
        comparison = {
            'project_id': project_id,
            'baseline_version': baseline.get('version', '1.0'),
            'comparison_date': datetime.utcnow(),
            'metrics_comparison': {},
            'overall_improvement': 0.0,
            'improved_metrics': [],
            'declined_metrics': []
        }
        
        total_change = 0.0
        metric_count = 0
        
        for metric_name, current_value in current_metrics.items():
            if metric_name in baseline_metrics:
                baseline_value = baseline_metrics[metric_name]
                change = current_value - baseline_value
                change_percent = (change / baseline_value * 100) if baseline_value != 0 else 0
                
                comparison['metrics_comparison'][metric_name] = {
                    'current_value': current_value,
                    'baseline_value': baseline_value,
                    'change': change,
                    'change_percent': change_percent
                }
                
                # 根据指标特性判断改进或下降
                is_higher_better = self.quality_metrics[metric_name]['is_higher_better']
                if (is_higher_better and change > 0) or (not is_higher_better and change < 0):
                    comparison['improved_metrics'].append(metric_name)
                    total_change += abs(change_percent)
                elif (is_higher_better and change < 0) or (not is_higher_better and change > 0):
                    comparison['declined_metrics'].append(metric_name)
                    total_change -= abs(change_percent)
                
                metric_count += 1
        
        comparison['overall_improvement'] = total_change / metric_count if metric_count > 0 else 0.0
        
        return comparison
    
    async def _validate_quality_targets(self, targets: Dict[str, float]) -> Dict[str, float]:
        """验证质量目标"""
        validated_targets = {}
        
        for metric_name, target_value in targets.items():
            if metric_name not in self.quality_metrics:
                logger.warning(f"未知的质量指标: {metric_name}")
                continue
            
            # 验证目标值的合理性
            if target_value < 0 or target_value > 1:
                logger.warning(f"质量目标值超出合理范围: {metric_name}={target_value}")
                continue
            
            validated_targets[metric_name] = target_value
        
        return validated_targets
    
    async def _get_industry_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """获取行业基准数据"""
        # 这里应该从外部数据源获取行业基准数据
        # 简化实现，返回模拟的行业基准
        return {
            'test_coverage': {
                'industry_average': 0.75,
                'best_practice': 0.90,
                'percentile_75': 0.80,
                'percentile_90': 0.85
            },
            'pass_rate': {
                'industry_average': 0.85,
                'best_practice': 0.95,
                'percentile_75': 0.88,
                'percentile_90': 0.92
            },
            'defect_density': {
                'industry_average': 0.25,
                'best_practice': 0.10,
                'percentile_75': 0.20,
                'percentile_90': 0.15
            },
            'test_automation_rate': {
                'industry_average': 0.60,
                'best_practice': 0.80,
                'percentile_75': 0.65,
                'percentile_90': 0.75
            }
        }
    
    async def _create_benchmark_comparison(self, metric_name: str, current_value: float,
                                         benchmark_data: Dict[str, float]) -> BenchmarkData:
        """创建基准对比"""
        industry_average = benchmark_data.get('industry_average', 0)
        best_practice = benchmark_data.get('best_practice', 0)
        
        # 计算百分位排名
        percentile_rank = 50.0  # 简化计算
        if current_value > industry_average:
            percentile_rank = 75.0
        if current_value > benchmark_data.get('percentile_75', industry_average):
            percentile_rank = 85.0
        if current_value > benchmark_data.get('percentile_90', industry_average):
            percentile_rank = 95.0
        
        # 确定对比结果
        if current_value >= best_practice:
            comparison_result = "excellent"
        elif current_value >= benchmark_data.get('percentile_75', industry_average):
            comparison_result = "above_average"
        elif current_value >= industry_average:
            comparison_result = "average"
        else:
            comparison_result = "needs_improvement"
        
        return BenchmarkData(
            metric_name=metric_name,
            industry_average=industry_average,
            best_practice=best_practice,
            current_value=current_value,
            percentile_rank=percentile_rank,
            comparison_result=comparison_result
        )
    
    async def _calculate_overall_benchmark_score(self, benchmarks: List[BenchmarkData]) -> float:
        """计算整体基准评分"""
        if not benchmarks:
            return 0.0
        
        total_score = 0.0
        for benchmark in benchmarks:
            # 根据对比结果给分
            if benchmark.comparison_result == "excellent":
                score = 100.0
            elif benchmark.comparison_result == "above_average":
                score = 80.0
            elif benchmark.comparison_result == "average":
                score = 60.0
            else:
                score = 40.0
            
            total_score += score
        
        return total_score / len(benchmarks)
    
    async def _analyze_benchmark_results(self, benchmarks: List[BenchmarkData]) -> Tuple[List[str], List[str]]:
        """分析基准对比结果"""
        strengths = []
        improvement_areas = []
        
        for benchmark in benchmarks:
            metric_display_name = self.quality_metrics[benchmark.metric_name]['name']
            
            if benchmark.comparison_result in ["excellent", "above_average"]:
                strengths.append(f"{metric_display_name}表现优秀，超过行业平均水平")
            elif benchmark.comparison_result == "needs_improvement":
                improvement_areas.append(f"{metric_display_name}需要改进，低于行业平均水平")
        
        return strengths, improvement_areas
    
    # 缓存和持久化方法
    async def _cache_quality_metrics(self, project_id: Optional[int], metrics: Dict[str, float]):
        """缓存质量指标"""
        try:
            cache_key = f"quality_metrics:{project_id or 'all'}"
            cache_data = {
                'metrics': metrics,
                'calculated_at': datetime.utcnow().isoformat()
            }
            await self.redis.setex(cache_key, 1800, str(cache_data))  # 缓存30分钟
        except Exception as e:
            logger.warning(f"缓存质量指标失败: {str(e)}")
    
    async def _save_quality_alerts(self, alerts: List[QualityAlert]):
        """保存质量告警"""
        try:
            for alert in alerts:
                cache_key = f"quality_alert:{alert.id}"
                await self.redis.setex(cache_key, 86400, alert.json())  # 缓存24小时
        except Exception as e:
            logger.warning(f"保存质量告警失败: {str(e)}")
    
    async def _save_quality_targets(self, project_id: int, target_config: Dict[str, Any]):
        """保存质量目标"""
        try:
            cache_key = f"quality_targets:{project_id}"
            await self.redis.set(cache_key, str(target_config))
        except Exception as e:
            logger.warning(f"保存质量目标失败: {str(e)}")
    
    async def _save_quality_baseline(self, project_id: int, baseline: Dict[str, Any]):
        """保存质量基线"""
        try:
            cache_key = f"quality_baseline:{project_id}"
            await self.redis.set(cache_key, str(baseline))
        except Exception as e:
            logger.warning(f"保存质量基线失败: {str(e)}")
    
    async def _update_monitoring_thresholds(self, project_id: int, targets: Dict[str, float]):
        """更新监控阈值"""
        try:
            # 根据目标值调整监控阈值
            for metric_name, target_value in targets.items():
                if metric_name in self.quality_metrics:
                    # 调整阈值为目标值的80%和60%
                    self.quality_metrics[metric_name]['threshold_warning'] = target_value * 0.8
                    self.quality_metrics[metric_name]['threshold_critical'] = target_value * 0.6
            
            logger.info(f"监控阈值更新完成: 项目{project_id}")
        except Exception as e:
            logger.warning(f"更新监控阈值失败: {str(e)}")