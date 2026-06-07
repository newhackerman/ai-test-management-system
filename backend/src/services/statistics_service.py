"""
项目统计分析服务

本模块实现项目统计分析的核心业务逻辑，包括：
- 多维度统计分析
- 性能指标和KPI跟踪
- 趋势分析和预测建模
- 绩效评估系统
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text, case
from sqlalchemy.orm import selectinload, joinedload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError
from ..models.project import Project, ProjectMember, Task, Milestone, WorkLog, ProjectRisk
from ..models.user import User

logger = logging.getLogger(__name__)


@dataclass
class ProjectStatistics:
    """项目统计数据"""
    project_id: int
    
    # 进度统计
    time_progress: Dict[str, Any]
    task_progress: Dict[str, Any] 
    quality_progress: Dict[str, Any]
    milestone_progress: Dict[str, Any]
    overall_progress: float
    
    # 效率统计
    efficiency_metrics: Dict[str, Any]
    
    # 成本统计
    cost_metrics: Dict[str, Any]
    
    # 风险统计
    risk_metrics: Dict[str, Any]
    
    # 协作统计
    collaboration_metrics: Dict[str, Any]
    
    # 计算时间
    calculated_at: datetime


@dataclass
class PerformanceEvaluation:
    """绩效评估数据"""
    user_id: int
    project_id: Optional[int]
    evaluation_period: Tuple[date, date]
    
    # 工作效率
    efficiency_score: float
    
    # 工作质量
    quality_score: float
    
    # 协作能力
    collaboration_score: float
    
    # 技能成长
    skill_growth_score: float
    
    # 创新贡献
    innovation_score: float
    
    # 综合评分
    overall_score: float
    
    # 详细指标
    detailed_metrics: Dict[str, Any]
    
    # 改进建议
    improvement_suggestions: List[str]
    
    # 评估时间
    evaluated_at: datetime


@dataclass
class TrendAnalysis:
    """趋势分析数据"""
    metric_name: str
    time_series_data: List[Dict[str, Any]]
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: float  # 0-1
    prediction: Dict[str, Any]
    confidence_level: float
    analyzed_at: datetime


class StatisticsService:
    """统计分析服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_project_statistics(self, project_id: int) -> ProjectStatistics:
        """
        计算项目统计数据
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目统计数据
        """
        # 获取项目基本信息
        project = await self._get_project_by_id(project_id)
        
        # 计算各维度统计
        time_progress = await self._calculate_time_progress(project)
        task_progress = await self._calculate_task_progress(project_id)
        quality_progress = await self._calculate_quality_progress(project_id)
        milestone_progress = await self._calculate_milestone_progress(project_id)
        
        # 计算综合进度
        overall_progress = self._calculate_overall_progress(
            time_progress, task_progress, quality_progress, milestone_progress
        )
        
        # 计算效率指标
        efficiency_metrics = await self._calculate_efficiency_metrics(project_id)
        
        # 计算成本指标
        cost_metrics = await self._calculate_cost_metrics(project)
        
        # 计算风险指标
        risk_metrics = await self._calculate_risk_metrics(project_id)
        
        # 计算协作指标
        collaboration_metrics = await self._calculate_collaboration_metrics(project_id)
        
        return ProjectStatistics(
            project_id=project_id,
            time_progress=time_progress,
            task_progress=task_progress,
            quality_progress=quality_progress,
            milestone_progress=milestone_progress,
            overall_progress=overall_progress,
            efficiency_metrics=efficiency_metrics,
            cost_metrics=cost_metrics,
            risk_metrics=risk_metrics,
            collaboration_metrics=collaboration_metrics,
            calculated_at=datetime.utcnow()
        )
    
    async def _calculate_time_progress(self, project: Project) -> Dict[str, Any]:
        """计算时间进度"""
        if not project.planned_start_date or not project.planned_end_date:
            return {
                'progress_rate': 0.0,
                'deviation': 0.0,
                'days_elapsed': 0,
                'days_remaining': 0,
                'is_on_schedule': True
            }
        
        today = date.today()
        planned_duration = (project.planned_end_date - project.planned_start_date).days
        
        if today < project.planned_start_date:
            # 项目还未开始
            days_elapsed = 0
            days_remaining = planned_duration
        elif today > project.planned_end_date:
            # 项目已超期
            days_elapsed = (today - project.planned_start_date).days
            days_remaining = 0
        else:
            # 项目进行中
            days_elapsed = (today - project.planned_start_date).days
            days_remaining = (project.planned_end_date - today).days
        
        progress_rate = days_elapsed / planned_duration if planned_duration > 0 else 0
        
        # 计算偏差（实际进度 vs 时间进度）
        actual_progress = float(project.progress_percentage or 0) / 100
        deviation = actual_progress - progress_rate
        
        return {
            'progress_rate': progress_rate,
            'deviation': deviation,
            'days_elapsed': days_elapsed,
            'days_remaining': days_remaining,
            'planned_duration': planned_duration,
            'is_on_schedule': abs(deviation) <= 0.1  # 偏差在10%以内认为正常
        }
    
    async def _calculate_task_progress(self, project_id: int) -> Dict[str, Any]:
        """计算任务进度"""
        # 获取项目所有任务
        query = select(Task).where(Task.project_id == project_id)
        result = await self.db.execute(query)
        tasks = result.scalars().all()
        
        if not tasks:
            return {
                'progress_rate': 0.0,
                'total_tasks': 0,
                'completed_tasks': 0,
                'in_progress_tasks': 0,
                'blocked_tasks': 0,
                'overdue_tasks': 0,
                'task_distribution': {}
            }
        
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == 'COMPLETED'])
        in_progress_tasks = len([t for t in tasks if t.status == 'IN_PROGRESS'])
        blocked_tasks = len([t for t in tasks if t.status == 'BLOCKED'])
        
        # 计算逾期任务
        today = date.today()
        overdue_tasks = len([
            t for t in tasks 
            if t.planned_end_date and t.planned_end_date < today and t.status not in ['COMPLETED', 'CANCELLED']
        ])
        
        # 加权进度计算
        weighted_progress = 0
        total_weight = 0
        
        for task in tasks:
            weight = self._get_task_weight(task)
            total_weight += weight
            
            if task.status == 'COMPLETED':
                weighted_progress += weight
            elif task.status == 'IN_PROGRESS':
                # 根据工时进度估算任务完成度
                if task.estimated_hours and task.actual_hours:
                    completion_rate = min(float(task.actual_hours) / float(task.estimated_hours), 0.9)
                    weighted_progress += weight * completion_rate
        
        progress_rate = weighted_progress / total_weight if total_weight > 0 else 0
        
        # 任务类型分布
        task_distribution = {}
        for task in tasks:
            task_type = task.task_type
            if task_type not in task_distribution:
                task_distribution[task_type] = {'total': 0, 'completed': 0}
            task_distribution[task_type]['total'] += 1
            if task.status == 'COMPLETED':
                task_distribution[task_type]['completed'] += 1
        
        return {
            'progress_rate': progress_rate,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'blocked_tasks': blocked_tasks,
            'overdue_tasks': overdue_tasks,
            'task_distribution': task_distribution
        }
    
    def _get_task_weight(self, task: Task) -> float:
        """获取任务权重"""
        # 基础权重
        base_weight = 1.0
        
        # 根据任务类型调整权重
        type_weights = {
            'REQUIREMENT_ANALYSIS': 1.2,
            'TEST_DESIGN': 1.1,
            'TEST_EXECUTION': 1.0,
            'AUTOMATION_DEVELOPMENT': 1.3,
            'PERFORMANCE_TEST': 1.2,
            'SECURITY_TEST': 1.2,
            'ENVIRONMENT_SETUP': 0.8,
            'DOCUMENTATION': 0.7
        }
        
        weight = base_weight * type_weights.get(task.task_type, 1.0)
        
        # 根据优先级调整权重
        priority_weights = {
            'LOW': 0.8,
            'MEDIUM': 1.0,
            'HIGH': 1.2,
            'URGENT': 1.5
        }
        
        weight *= priority_weights.get(task.priority, 1.0)
        
        # 根据预估工时调整权重
        if task.estimated_hours:
            hours = float(task.estimated_hours)
            if hours > 40:
                weight *= 1.3  # 大任务权重更高
            elif hours < 8:
                weight *= 0.8  # 小任务权重较低
        
        return weight
    
    async def _calculate_quality_progress(self, project_id: int) -> Dict[str, Any]:
        """计算质量进度"""
        # 获取项目信息
        project = await self._get_project_by_id(project_id)
        
        # 测试用例相关指标
        test_case_count = project.test_case_count or 0
        passed_test_count = project.passed_test_count or 0
        defect_count = project.defect_count or 0
        
        # 计算测试通过率
        test_pass_rate = passed_test_count / test_case_count if test_case_count > 0 else 0
        
        # 计算缺陷密度（每千行代码缺陷数，这里用任务数估算）
        task_count = project.task_count or 1
        defect_density = defect_count / task_count
        
        # 获取缺陷详细信息
        defect_details = await self._get_defect_details(project_id)
        
        # 质量评分计算
        quality_score = self._calculate_quality_score(
            test_pass_rate, defect_density, defect_details
        )
        
        return {
            'progress_rate': quality_score,
            'test_case_count': test_case_count,
            'passed_test_count': passed_test_count,
            'test_pass_rate': test_pass_rate,
            'defect_count': defect_count,
            'defect_density': defect_density,
            'defect_details': defect_details,
            'quality_score': quality_score
        }
    
    def _calculate_quality_score(self, test_pass_rate: float, defect_density: float, 
                                defect_details: Dict[str, Any]) -> float:
        """计算质量评分"""
        # 基础分数
        base_score = 100
        
        # 测试通过率影响（权重40%）
        test_score = test_pass_rate * 40
        
        # 缺陷密度影响（权重30%）
        # 缺陷密度越低，分数越高
        defect_score = max(0, 30 - defect_density * 10)
        
        # 严重缺陷影响（权重30%）
        critical_defects = defect_details.get('critical_count', 0)
        high_defects = defect_details.get('high_count', 0)
        severity_penalty = critical_defects * 5 + high_defects * 2
        severity_score = max(0, 30 - severity_penalty)
        
        total_score = test_score + defect_score + severity_score
        return min(100, max(0, total_score)) / 100  # 转换为0-1范围
    
    async def _get_defect_details(self, project_id: int) -> Dict[str, Any]:
        """获取缺陷详细信息"""
        # 这里需要根据实际的缺陷模型来实现
        # 暂时返回模拟数据
        return {
            'critical_count': 0,
            'high_count': 1,
            'medium_count': 3,
            'low_count': 2,
            'open_count': 4,
            'resolved_count': 2,
            'avg_resolution_time': 2.5  # 天
        }
    
    async def _calculate_milestone_progress(self, project_id: int) -> Dict[str, Any]:
        """计算里程碑进度"""
        # 获取项目里程碑
        query = select(Milestone).where(Milestone.project_id == project_id)
        result = await self.db.execute(query)
        milestones = result.scalars().all()
        
        if not milestones:
            return {
                'progress_rate': 0.0,
                'total_milestones': 0,
                'completed_milestones': 0,
                'overdue_milestones': 0,
                'upcoming_milestones': 0
            }
        
        total_milestones = len(milestones)
        completed_milestones = len([m for m in milestones if m.status == 'COMPLETED'])
        
        # 计算逾期里程碑
        today = date.today()
        overdue_milestones = len([
            m for m in milestones 
            if m.planned_date < today and m.status not in ['COMPLETED', 'CANCELLED']
        ])
        
        # 计算即将到期的里程碑（7天内）
        upcoming_date = today + timedelta(days=7)
        upcoming_milestones = len([
            m for m in milestones 
            if today <= m.planned_date <= upcoming_date and m.status not in ['COMPLETED', 'CANCELLED']
        ])
        
        progress_rate = completed_milestones / total_milestones if total_milestones > 0 else 0
        
        return {
            'progress_rate': progress_rate,
            'total_milestones': total_milestones,
            'completed_milestones': completed_milestones,
            'overdue_milestones': overdue_milestones,
            'upcoming_milestones': upcoming_milestones
        }
    
    def _calculate_overall_progress(self, time_progress: Dict[str, Any], 
                                  task_progress: Dict[str, Any],
                                  quality_progress: Dict[str, Any], 
                                  milestone_progress: Dict[str, Any]) -> float:
        """计算综合进度"""
        # 权重配置
        weights = {
            'time': 0.25,
            'task': 0.35,
            'quality': 0.25,
            'milestone': 0.15
        }
        
        overall_progress = (
            time_progress['progress_rate'] * weights['time'] +
            task_progress['progress_rate'] * weights['task'] +
            quality_progress['progress_rate'] * weights['quality'] +
            milestone_progress['progress_rate'] * weights['milestone']
        )
        
        return min(1.0, max(0.0, overall_progress))
    
    async def _calculate_efficiency_metrics(self, project_id: int) -> Dict[str, Any]:
        """计算效率指标"""
        # 获取工作日志
        query = select(WorkLog).where(WorkLog.project_id == project_id)
        result = await self.db.execute(query)
        work_logs = result.scalars().all()
        
        if not work_logs:
            return {
                'productivity_rate': 0.0,
                'avg_hours_per_day': 0.0,
                'efficiency_trend': 'stable',
                'work_type_distribution': {}
            }
        
        # 计算生产率指标
        total_hours = sum(float(log.hours_worked) for log in work_logs)
        work_days = len(set(log.work_date for log in work_logs))
        avg_hours_per_day = total_hours / work_days if work_days > 0 else 0
        
        # 工作类型分布
        work_type_distribution = {}
        for log in work_logs:
            work_type = log.work_type
            if work_type not in work_type_distribution:
                work_type_distribution[work_type] = 0
            work_type_distribution[work_type] += float(log.hours_worked)
        
        # 计算生产率（完成任务数/总工时）
        completed_tasks = await self._get_completed_task_count(project_id)
        productivity_rate = completed_tasks / total_hours if total_hours > 0 else 0
        
        return {
            'productivity_rate': productivity_rate,
            'avg_hours_per_day': avg_hours_per_day,
            'total_hours': total_hours,
            'work_days': work_days,
            'efficiency_trend': 'stable',  # 需要历史数据分析
            'work_type_distribution': work_type_distribution
        }
    
    async def _calculate_cost_metrics(self, project: Project) -> Dict[str, Any]:
        """计算成本指标"""
        budget = float(project.budget) if project.budget else 0
        actual_cost = float(project.actual_cost) if project.actual_cost else 0
        
        # 计算成本偏差
        cost_variance = actual_cost - budget if budget > 0 else 0
        cost_variance_percentage = cost_variance / budget if budget > 0 else 0
        
        # 计算成本绩效指数（CPI）
        earned_value = budget * (float(project.progress_percentage or 0) / 100)
        cpi = earned_value / actual_cost if actual_cost > 0 else 1.0
        
        # 预测最终成本
        estimated_final_cost = budget / cpi if cpi > 0 else budget
        
        return {
            'budget': budget,
            'actual_cost': actual_cost,
            'cost_variance': cost_variance,
            'cost_variance_percentage': cost_variance_percentage,
            'cost_performance_index': cpi,
            'estimated_final_cost': estimated_final_cost,
            'is_over_budget': actual_cost > budget
        }
    
    async def _calculate_risk_metrics(self, project_id: int) -> Dict[str, Any]:
        """计算风险指标"""
        # 获取项目风险
        query = select(ProjectRisk).where(ProjectRisk.project_id == project_id)
        result = await self.db.execute(query)
        risks = result.scalars().all()
        
        if not risks:
            return {
                'total_risks': 0,
                'high_risks': 0,
                'open_risks': 0,
                'avg_risk_score': 0.0,
                'risk_distribution': {}
            }
        
        total_risks = len(risks)
        high_risks = len([r for r in risks if r.risk_level in ['HIGH', 'CRITICAL']])
        open_risks = len([r for r in risks if r.status not in ['CLOSED']])
        
        # 计算平均风险评分
        avg_risk_score = sum(float(r.risk_score or 0) for r in risks) / total_risks
        
        # 风险分布
        risk_distribution = {}
        for risk in risks:
            category = risk.risk_category
            if category not in risk_distribution:
                risk_distribution[category] = {'count': 0, 'avg_score': 0}
            risk_distribution[category]['count'] += 1
        
        # 计算各类别平均评分
        for category in risk_distribution:
            category_risks = [r for r in risks if r.risk_category == category]
            avg_score = sum(float(r.risk_score or 0) for r in category_risks) / len(category_risks)
            risk_distribution[category]['avg_score'] = avg_score
        
        return {
            'total_risks': total_risks,
            'high_risks': high_risks,
            'open_risks': open_risks,
            'avg_risk_score': avg_risk_score,
            'risk_distribution': risk_distribution
        }
    
    async def _calculate_collaboration_metrics(self, project_id: int) -> Dict[str, Any]:
        """计算协作指标"""
        # 获取项目成员
        query = select(ProjectMember).where(
            and_(ProjectMember.project_id == project_id, ProjectMember.status == 'ACTIVE')
        )
        result = await self.db.execute(query)
        members = result.scalars().all()
        
        if not members:
            return {
                'team_size': 0,
                'avg_allocation': 0.0,
                'role_distribution': {},
                'collaboration_score': 0.0
            }
        
        team_size = len(members)
        avg_allocation = sum(float(m.allocation_percentage or 0) for m in members) / team_size
        
        # 角色分布
        role_distribution = {}
        for member in members:
            role = member.role_in_project
            if role not in role_distribution:
                role_distribution[role] = 0
            role_distribution[role] += 1
        
        # 协作评分（基于团队规模、角色多样性等）
        role_diversity = len(role_distribution) / team_size if team_size > 0 else 0
        collaboration_score = min(1.0, (role_diversity + avg_allocation / 100) / 2)
        
        return {
            'team_size': team_size,
            'avg_allocation': avg_allocation,
            'role_distribution': role_distribution,
            'collaboration_score': collaboration_score
        }
    
    async def _get_project_by_id(self, project_id: int) -> Project:
        """根据ID获取项目"""
        query = select(Project).where(Project.id == project_id)
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"项目不存在: {project_id}")
        
        return project
    
    async def _get_completed_task_count(self, project_id: int) -> int:
        """获取已完成任务数量"""
        query = select(func.count(Task.id)).where(
            and_(Task.project_id == project_id, Task.status == 'COMPLETED')
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def calculate_trend_analysis(self, project_id: int, metric_name: str, 
                                     days: int = 30) -> TrendAnalysis:
        """
        计算趋势分析
        
        Args:
            project_id: 项目ID
            metric_name: 指标名称
            days: 分析天数
            
        Returns:
            趋势分析数据
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 获取历史数据（这里需要根据实际需求实现）
        time_series_data = await self._get_historical_metric_data(
            project_id, metric_name, start_date, end_date
        )
        
        if len(time_series_data) < 2:
            return TrendAnalysis(
                metric_name=metric_name,
                time_series_data=time_series_data,
                trend_direction='stable',
                trend_strength=0.0,
                prediction={},
                confidence_level=0.0,
                analyzed_at=datetime.utcnow()
            )
        
        # 简单的趋势分析
        values = [item['value'] for item in time_series_data]
        trend_direction, trend_strength = self._analyze_trend(values)
        
        # 简单的预测（线性回归）
        prediction = self._predict_next_values(values, days=7)
        
        return TrendAnalysis(
            metric_name=metric_name,
            time_series_data=time_series_data,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            prediction=prediction,
            confidence_level=0.7,  # 简化的置信度
            analyzed_at=datetime.utcnow()
        )
    
    async def _get_historical_metric_data(self, project_id: int, metric_name: str,
                                        start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """获取历史指标数据"""
        # 这里需要根据实际的历史数据存储来实现
        # 暂时返回模拟数据
        data = []
        current_date = start_date
        base_value = 50.0
        
        while current_date <= end_date:
            # 模拟数据，实际应该从数据库获取
            value = base_value + (current_date - start_date).days * 0.5
            data.append({
                'date': current_date.isoformat(),
                'value': value,
                'metric_name': metric_name
            })
            current_date += timedelta(days=1)
        
        return data
    
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
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        
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
    
    def _predict_next_values(self, values: List[float], days: int = 7) -> Dict[str, Any]:
        """预测未来值"""
        if len(values) < 2:
            return {'predicted_values': [], 'method': 'insufficient_data'}
        
        # 简单的线性预测
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
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