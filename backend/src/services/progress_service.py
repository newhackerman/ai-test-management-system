"""
进度跟踪服务

本模块实现项目进度跟踪的核心业务逻辑，包括：
- 多维度进度计算
- 实时进度更新
- 进度预警和通知
- 进度趋势分析
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.project import Project, Task, Milestone, WorkLog, ProjectRisk
from ..models.user import User
from ..schemas.progress import (
    ProgressResponse, TimeProgressResponse, TaskProgressResponse,
    QualityProgressResponse, MilestoneProgressResponse, ProgressAlert,
    ProgressWeightsConfig, ProgressThresholds, AlertType, AlertSeverity,
    ProgressTrendAnalysis, ProgressTrend, ProgressUpdateResponse
)

logger = logging.getLogger(__name__)


@dataclass
class ProgressWeights:
    """进度权重配置"""
    time: float = 0.25
    task: float = 0.35
    quality: float = 0.25
    milestone: float = 0.15


@dataclass
class ProgressCalculationResult:
    """进度计算结果"""
    time_progress: TimeProgressResponse
    task_progress: TaskProgressResponse
    quality_progress: QualityProgressResponse
    milestone_progress: MilestoneProgressResponse
    overall_progress: Decimal
    health_score: int
    risk_level: str


class ProgressService:
    """进度跟踪服务"""


class ProgressService:
    """进度跟踪服务"""
    
    def __init__(self):
        self.weights = ProgressWeights()
        # Initialize with default thresholds
        self.thresholds = {
            'time_deviation_warning': 0.10,
            'time_deviation_critical': 0.20,
            'quality_score_warning': 0.80,
            'quality_score_critical': 0.70,
            'milestone_overdue_warning': 1,
            'milestone_overdue_critical': 3
        }
    
    async def calculate_project_progress(
        self, 
        project_id: int, 
        session: AsyncSession,
        weights: Optional[ProgressWeightsConfig] = None
    ) -> ProgressResponse:
        """
        计算项目多维度进度
        
        Args:
            project_id: 项目ID
            session: 数据库会话
            weights: 自定义权重配置
            
        Returns:
            ProgressResponse: 综合进度响应
        """
        try:
            # 获取项目基本信息
            project = await self._get_project_with_relations(project_id, session)
            if not project:
                raise NotFoundError(f"项目 {project_id} 不存在")
            
            # 使用自定义权重或默认权重
            if weights:
                self.weights.time = float(weights.time_weight)
                self.weights.task = float(weights.task_weight)
                self.weights.quality = float(weights.quality_weight)
                self.weights.milestone = float(weights.milestone_weight)
            
            # 计算各维度进度
            time_progress = await self._calculate_time_progress(project, session)
            task_progress = await self._calculate_task_progress(project, session)
            quality_progress = await self._calculate_quality_progress(project, session)
            milestone_progress = await self._calculate_milestone_progress(project, session)
            
            # 计算综合进度
            overall_progress = self._calculate_overall_progress(
                time_progress, task_progress, quality_progress, milestone_progress
            )
            
            # 计算健康度和风险等级
            health_score, risk_level = self._calculate_health_metrics(
                time_progress, task_progress, quality_progress, milestone_progress
            )
            
            # 构建响应
            progress_response = ProgressResponse(
                project_id=project_id,
                overall_progress=overall_progress,
                time_progress=time_progress,
                task_progress=task_progress,
                quality_progress=quality_progress,
                milestone_progress=milestone_progress,
                weights={
                    "time": Decimal(str(self.weights.time)),
                    "task": Decimal(str(self.weights.task)),
                    "quality": Decimal(str(self.weights.quality)),
                    "milestone": Decimal(str(self.weights.milestone))
                },
                health_score=health_score,
                risk_level=risk_level,
                calculated_at=datetime.utcnow()
            )
            
            # 更新项目进度字段
            await self._update_project_progress_fields(project, overall_progress, session)
            
            logger.info(f"项目 {project_id} 进度计算完成，综合进度: {overall_progress:.2%}")
            return progress_response
            
        except Exception as e:
            logger.error(f"计算项目 {project_id} 进度失败: {str(e)}")
            raise
    
    async def _get_project_with_relations(self, project_id: int, session: AsyncSession) -> Optional[Project]:
        """获取项目及其关联数据"""
        stmt = select(Project).options(
            selectinload(Project.tasks),
            selectinload(Project.milestones),
            selectinload(Project.work_logs),
            selectinload(Project.risks)
        ).where(Project.id == project_id)
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _calculate_time_progress(self, project: Project, session: AsyncSession) -> TimeProgressResponse:
        """计算时间进度"""
        now = datetime.now().date()
        
        # 获取计划时间
        planned_start = project.planned_start_date
        planned_end = project.planned_end_date
        actual_start = project.actual_start_date
        
        if not planned_start or not planned_end:
            # 如果没有计划时间，返回默认值
            return TimeProgressResponse(
                project_id=project.id,
                progress_rate=Decimal('0'),
                elapsed_days=0,
                total_days=1,
                remaining_days=0,
                deviation=Decimal('0'),
                is_on_schedule=True,
                calculated_at=datetime.utcnow()
            )
        
        # 计算时间指标
        total_days = (planned_end - planned_start).days
        if total_days <= 0:
            total_days = 1
        
        # 使用实际开始时间或计划开始时间
        start_date = actual_start if actual_start else planned_start
        elapsed_days = max(0, (now - start_date).days)
        remaining_days = (planned_end - now).days
        
        # 计算时间进度率
        progress_rate = min(Decimal(str(elapsed_days / total_days)), Decimal('1'))
        
        # 计算偏差（实际进度 vs 计划进度）
        planned_progress_rate = min(Decimal(str((now - planned_start).days / total_days)), Decimal('1'))
        deviation = progress_rate - planned_progress_rate
        
        # 判断是否按计划进行（偏差在10%以内）
        is_on_schedule = abs(deviation) <= Decimal('0.1')
        
        return TimeProgressResponse(
            project_id=project.id,
            progress_rate=progress_rate,
            elapsed_days=elapsed_days,
            total_days=total_days,
            remaining_days=remaining_days,
            deviation=deviation,
            is_on_schedule=is_on_schedule,
            calculated_at=datetime.utcnow()
        )
    
    async def _calculate_task_progress(self, project: Project, session: AsyncSession) -> TaskProgressResponse:
        """计算任务进度"""
        tasks = project.tasks
        
        if not tasks:
            return TaskProgressResponse(
                project_id=project.id,
                progress_rate=Decimal('0'),
                total_tasks=0,
                completed_tasks=0,
                in_progress_tasks=0,
                blocked_tasks=0,
                weighted_progress=Decimal('0'),
                calculated_at=datetime.utcnow()
            )
        
        # 统计任务状态
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == 'COMPLETED'])
        in_progress_tasks = len([t for t in tasks if t.status == 'IN_PROGRESS'])
        blocked_tasks = len([t for t in tasks if t.status == 'BLOCKED'])
        
        # 计算加权进度
        weighted_progress = Decimal('0')
        total_weight = Decimal('0')
        
        for task in tasks:
            # 任务权重基于预估工时，默认为1
            weight = Decimal(str(task.estimated_hours)) if task.estimated_hours else Decimal('1')
            total_weight += weight
            
            # 根据任务状态计算完成度
            if task.status == 'COMPLETED':
                completion_rate = Decimal('1')
            elif task.status == 'IN_PROGRESS':
                # 基于工时进度估算完成度
                if task.estimated_hours and task.actual_hours:
                    completion_rate = min(
                        Decimal(str(task.actual_hours)) / Decimal(str(task.estimated_hours)),
                        Decimal('0.9')  # 进行中任务最多算90%
                    )
                else:
                    completion_rate = Decimal('0.5')  # 默认50%
            else:
                completion_rate = Decimal('0')
            
            weighted_progress += weight * completion_rate
        
        # 计算进度率
        progress_rate = weighted_progress / total_weight if total_weight > 0 else Decimal('0')
        
        return TaskProgressResponse(
            project_id=project.id,
            progress_rate=progress_rate,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            blocked_tasks=blocked_tasks,
            weighted_progress=weighted_progress,
            calculated_at=datetime.utcnow()
        )
    
    async def _calculate_quality_progress(self, project: Project, session: AsyncSession) -> QualityProgressResponse:
        """计算质量进度"""
        # 获取质量指标
        test_case_count = project.test_case_count or 0
        passed_test_count = project.passed_test_count or 0
        defect_count = project.defect_count or 0
        
        # 计算测试覆盖率（这里简化处理，实际应该基于需求覆盖）
        test_coverage = Decimal('0')
        if test_case_count > 0:
            # 假设每个测试用例覆盖一定的功能点
            test_coverage = min(Decimal(str(test_case_count / 100)), Decimal('1'))  # 简化计算
        
        # 计算测试通过率
        pass_rate = Decimal('0')
        if test_case_count > 0:
            pass_rate = Decimal(str(passed_test_count / test_case_count))
        
        # 计算缺陷密度（每千行代码缺陷数，这里简化为每个功能点缺陷数）
        defect_density = Decimal(str(defect_count))
        if test_case_count > 0:
            defect_density = Decimal(str(defect_count / test_case_count))
        
        # 计算质量评分（0-100）
        quality_score = self._calculate_quality_score(test_coverage, pass_rate, defect_density)
        
        # 质量进度率基于质量评分
        progress_rate = quality_score / Decimal('100')
        
        return QualityProgressResponse(
            project_id=project.id,
            progress_rate=progress_rate,
            test_coverage=test_coverage,
            pass_rate=pass_rate,
            defect_density=defect_density,
            quality_score=quality_score,
            calculated_at=datetime.utcnow()
        )
    
    async def _calculate_milestone_progress(self, project: Project, session: AsyncSession) -> MilestoneProgressResponse:
        """计算里程碑进度"""
        milestones = project.milestones
        
        if not milestones:
            return MilestoneProgressResponse(
                project_id=project.id,
                progress_rate=Decimal('0'),
                total_milestones=0,
                completed_milestones=0,
                overdue_milestones=0,
                upcoming_milestones=0,
                calculated_at=datetime.utcnow()
            )
        
        now = datetime.now().date()
        
        # 统计里程碑状态
        total_milestones = len(milestones)
        completed_milestones = len([m for m in milestones if m.status == 'COMPLETED'])
        overdue_milestones = len([
            m for m in milestones 
            if m.status != 'COMPLETED' and m.planned_date < now
        ])
        upcoming_milestones = len([
            m for m in milestones 
            if m.status != 'COMPLETED' and m.planned_date <= now + timedelta(days=7)
        ])
        
        # 计算里程碑进度率
        progress_rate = Decimal(str(completed_milestones / total_milestones)) if total_milestones > 0 else Decimal('0')
        
        return MilestoneProgressResponse(
            project_id=project.id,
            progress_rate=progress_rate,
            total_milestones=total_milestones,
            completed_milestones=completed_milestones,
            overdue_milestones=overdue_milestones,
            upcoming_milestones=upcoming_milestones,
            calculated_at=datetime.utcnow()
        )
    
    def _calculate_overall_progress(
        self,
        time_progress: TimeProgressResponse,
        task_progress: TaskProgressResponse,
        quality_progress: QualityProgressResponse,
        milestone_progress: MilestoneProgressResponse
    ) -> Decimal:
        """计算综合进度"""
        overall_progress = (
            time_progress.progress_rate * Decimal(str(self.weights.time)) +
            task_progress.progress_rate * Decimal(str(self.weights.task)) +
            quality_progress.progress_rate * Decimal(str(self.weights.quality)) +
            milestone_progress.progress_rate * Decimal(str(self.weights.milestone))
        )
        
        return min(overall_progress, Decimal('1'))
    
    def _calculate_health_metrics(
        self,
        time_progress: TimeProgressResponse,
        task_progress: TaskProgressResponse,
        quality_progress: QualityProgressResponse,
        milestone_progress: MilestoneProgressResponse
    ) -> Tuple[int, str]:
        """计算健康度和风险等级"""
        # 健康度评分（0-100）
        health_score = 100
        
        # 时间偏差影响
        if abs(time_progress.deviation) > Decimal('0.2'):
            health_score -= 30
        elif abs(time_progress.deviation) > Decimal('0.1'):
            health_score -= 15
        
        # 任务阻塞影响
        if task_progress.blocked_tasks > 0:
            health_score -= min(task_progress.blocked_tasks * 10, 25)
        
        # 质量影响
        if quality_progress.quality_score < 70:
            health_score -= 25
        elif quality_progress.quality_score < 80:
            health_score -= 10
        
        # 里程碑逾期影响
        if milestone_progress.overdue_milestones > 0:
            health_score -= min(milestone_progress.overdue_milestones * 15, 30)
        
        health_score = max(0, health_score)
        
        # 风险等级评估
        if health_score >= 80:
            risk_level = "LOW"
        elif health_score >= 60:
            risk_level = "MEDIUM"
        elif health_score >= 40:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        return health_score, risk_level
    
    def _calculate_quality_score(
        self, 
        test_coverage: Decimal, 
        pass_rate: Decimal, 
        defect_density: Decimal
    ) -> Decimal:
        """计算质量评分"""
        # 基础分数
        score = Decimal('100')
        
        # 测试覆盖率影响（权重40%）
        coverage_score = test_coverage * Decimal('40')
        
        # 测试通过率影响（权重40%）
        pass_score = pass_rate * Decimal('40')
        
        # 缺陷密度影响（权重20%）
        defect_penalty = min(defect_density * Decimal('10'), Decimal('20'))
        defect_score = Decimal('20') - defect_penalty
        
        total_score = coverage_score + pass_score + defect_score
        return max(Decimal('0'), min(total_score, Decimal('100')))
    
    async def _update_project_progress_fields(
        self, 
        project: Project, 
        overall_progress: Decimal, 
        session: AsyncSession
    ):
        """更新项目进度相关字段"""
        project.progress_percentage = overall_progress * Decimal('100')
        project.updated_at = datetime.utcnow()
        
        # 更新任务统计
        if project.tasks:
            project.task_count = len(project.tasks)
            project.completed_task_count = len([t for t in project.tasks if t.status == 'COMPLETED'])
        
        await session.commit()
    
    async def generate_progress_alerts(
        self, 
        project_id: int, 
        progress: ProgressResponse,
        session: AsyncSession
    ) -> List[ProgressAlert]:
        """生成进度预警"""
        alerts = []
        now = datetime.utcnow()
        
        # 时间偏差预警
        if abs(progress.time_progress.deviation) > Decimal('0.15'):
            severity = AlertSeverity.HIGH if abs(progress.time_progress.deviation) > Decimal('0.25') else AlertSeverity.MEDIUM
            alerts.append(ProgressAlert(
                project_id=project_id,
                alert_type=AlertType.TIME_DEVIATION,
                severity=severity,
                title="项目时间进度偏差",
                message=f"项目时间进度偏差 {progress.time_progress.deviation:.1%}",
                recommendation="建议调整资源分配或优化任务安排",
                current_value=progress.time_progress.deviation,
                threshold_value=Decimal('0.15'),
                deviation=progress.time_progress.deviation,
                triggered_at=now
            ))
        
        # 质量风险预警
        if progress.quality_progress.quality_score < 80:
            severity = AlertSeverity.HIGH if progress.quality_progress.quality_score < 70 else AlertSeverity.MEDIUM
            alerts.append(ProgressAlert(
                project_id=project_id,
                alert_type=AlertType.QUALITY_RISK,
                severity=severity,
                title="项目质量风险",
                message=f"项目质量评分 {progress.quality_progress.quality_score:.1f} 低于预期",
                recommendation="建议增加测试资源或提升测试覆盖率",
                current_value=progress.quality_progress.quality_score,
                threshold_value=Decimal('80'),
                triggered_at=now
            ))
        
        # 里程碑逾期预警
        if progress.milestone_progress.overdue_milestones > 0:
            alerts.append(ProgressAlert(
                project_id=project_id,
                alert_type=AlertType.MILESTONE_OVERDUE,
                severity=AlertSeverity.CRITICAL,
                title="里程碑逾期",
                message=f"有 {progress.milestone_progress.overdue_milestones} 个里程碑已逾期",
                recommendation="立即评估影响并制定应对措施",
                current_value=Decimal(str(progress.milestone_progress.overdue_milestones)),
                threshold_value=Decimal('0'),
                triggered_at=now
            ))
        
        # 任务阻塞预警
        if progress.task_progress.blocked_tasks > 0:
            alerts.append(ProgressAlert(
                project_id=project_id,
                alert_type=AlertType.TASK_BLOCKED,
                severity=AlertSeverity.HIGH,
                title="任务阻塞",
                message=f"有 {progress.task_progress.blocked_tasks} 个任务被阻塞",
                recommendation="尽快解决阻塞问题，确保项目进度",
                current_value=Decimal(str(progress.task_progress.blocked_tasks)),
                threshold_value=Decimal('0'),
                triggered_at=now
            ))
        
        return alerts
    
    async def update_project_progress(
        self, 
        project_id: int, 
        force_recalculate: bool = False,
        notify_stakeholders: bool = True
    ) -> ProgressUpdateResponse:
        """更新项目进度"""
        async with get_async_session() as session:
            try:
                # 计算最新进度
                progress = await self.calculate_project_progress(project_id, session)
                
                # 生成预警
                alerts = await self.generate_progress_alerts(project_id, progress, session)
                
                # TODO: 如果需要通知干系人，这里可以添加通知逻辑
                if notify_stakeholders and alerts:
                    await self._notify_stakeholders(project_id, alerts, session)
                
                return ProgressUpdateResponse(
                    success=True,
                    message="项目进度更新成功",
                    progress=progress,
                    alerts=alerts
                )
                
            except Exception as e:
                logger.error(f"更新项目 {project_id} 进度失败: {str(e)}")
                return ProgressUpdateResponse(
                    success=False,
                    message=f"进度更新失败: {str(e)}",
                    progress=None,
                    alerts=[]
                )
    
    async def _notify_stakeholders(
        self, 
        project_id: int, 
        alerts: List[ProgressAlert], 
        session: AsyncSession
    ):
        """通知项目干系人"""
        # TODO: 实现通知逻辑
        # 这里可以集成邮件、短信、系统通知等
        logger.info(f"项目 {project_id} 生成了 {len(alerts)} 个预警，需要通知干系人")
        pass