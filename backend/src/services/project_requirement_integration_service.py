"""
项目需求集成服务

本模块实现项目管理系统与需求管理系统的集成功能，包括：
- 项目与需求的数据同步
- 任务关联管理功能
- 进度同步机制
- 状态变更联动
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text, update
from sqlalchemy.orm import selectinload, joinedload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.project import Project, Task, ProjectMember
from ..models.requirement import Requirement, RequirementStatus, RequirementTraceabilityLink, TraceabilityLinkType
from ..services.project_service import ProjectService
from ..services.requirement_service import RequirementService

logger = logging.getLogger(__name__)


class ProjectRequirementIntegrationService:
    """项目需求集成服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_service = ProjectService(db)
        self.requirement_service = RequirementService(db)
    
    async def sync_project_requirements(self, project_id: int, user_id: int) -> Dict[str, Any]:
        """
        同步项目需求数据
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            
        Returns:
            同步结果统计
        """
        logger.info(f"开始同步项目 {project_id} 的需求数据")
        
        # 1. 获取项目信息
        project = await self.project_service.get_project_by_id(project_id, user_id)
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")
        
        # 2. 获取项目所有需求
        requirements = await self._get_project_requirements(project_id)
        
        # 3. 同步需求统计到项目
        sync_result = await self._sync_requirement_statistics(project, requirements)
        
        # 4. 同步需求进度到项目进度
        await self._sync_requirement_progress_to_project(project, requirements)
        
        # 5. 同步需求状态变更影响
        await self._sync_requirement_status_impact(project, requirements)
        
        # 6. 保存项目更新
        await self.db.commit()
        
        logger.info(f"项目 {project_id} 需求数据同步完成")
        return sync_result
    
    async def create_task_from_requirement(
        self, 
        requirement_id: int, 
        task_data: Dict[str, Any], 
        user_id: int
    ) -> Task:
        """
        从需求创建任务
        
        Args:
            requirement_id: 需求ID
            task_data: 任务数据
            user_id: 用户ID
            
        Returns:
            创建的任务对象
        """
        # 1. 获取需求信息
        requirement = await self._get_requirement_by_id(requirement_id)
        if not requirement:
            raise NotFoundError(f"需求 {requirement_id} 不存在")
        
        # 2. 验证权限
        await self._validate_task_creation_permission(requirement.project_id, user_id)
        
        # 3. 生成任务编码
        task_code = await self._generate_task_code(requirement.project_id)
        
        # 4. 创建任务
        task = Task(
            project_id=requirement.project_id,
            task_code=task_code,
            task_name=task_data.get('task_name', f"实现需求: {requirement.title}"),
            description=task_data.get('description', requirement.description),
            task_type=task_data.get('task_type', 'REQUIREMENT_ANALYSIS'),
            priority=self._map_requirement_priority_to_task(requirement.priority),
            assignee_id=task_data.get('assignee_id', requirement.assignee_id),
            reporter_id=user_id,
            planned_start_date=task_data.get('planned_start_date', requirement.planned_start_date),
            planned_end_date=task_data.get('planned_end_date', requirement.planned_end_date),
            estimated_hours=task_data.get('estimated_hours', self._estimate_hours_from_effort(requirement.estimated_effort)),
            acceptance_criteria=requirement.acceptance_criteria,
            tags=task_data.get('tags', requirement.tags),
            created_by=user_id
        )
        
        # 5. 保存任务
        self.db.add(task)
        await self.db.flush()
        
        # 6. 创建需求-任务追溯链接
        await self._create_requirement_task_traceability(requirement_id, task.id, user_id)
        
        # 7. 更新需求状态为开发中（如果当前是已批准状态）
        if requirement.status == RequirementStatus.APPROVED:
            await self.requirement_service.update_requirement_status(
                requirement_id, RequirementStatus.IN_DEVELOPMENT, user_id, "创建开发任务"
            )
        
        await self.db.commit()
        
        logger.info(f"从需求 {requirement_id} 创建任务 {task.id} 成功")
        return task
    
    async def sync_task_progress_to_requirement(self, task_id: int, user_id: int) -> bool:
        """
        同步任务进度到需求
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            是否同步成功
        """
        # 1. 获取任务信息
        task = await self._get_task_by_id(task_id)
        if not task:
            raise NotFoundError(f"任务 {task_id} 不存在")
        
        # 2. 获取关联的需求
        requirements = await self._get_requirements_by_task(task_id)
        
        # 3. 同步任务状态到需求状态
        for requirement in requirements:
            new_status = self._map_task_status_to_requirement(task.status)
            if new_status and requirement.status != new_status:
                await self.requirement_service.update_requirement_status(
                    requirement.id, new_status, user_id, f"任务 {task.task_code} 状态变更"
                )
        
        # 4. 同步工时信息
        for requirement in requirements:
            if task.actual_hours and task.actual_hours > 0:
                # 将任务实际工时转换为需求实际工作量（天）
                actual_effort_days = float(task.actual_hours) / 8  # 假设每天8小时
                requirement.actual_effort = Decimal(str(actual_effort_days))
        
        await self.db.commit()
        
        logger.info(f"任务 {task_id} 进度同步到需求完成")
        return True
    
    async def get_project_requirement_summary(self, project_id: int, user_id: int) -> Dict[str, Any]:
        """
        获取项目需求汇总信息
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            
        Returns:
            需求汇总信息
        """
        # 1. 验证项目访问权限
        project = await self.project_service.get_project_by_id(project_id, user_id)
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")
        
        # 2. 获取需求统计
        requirements_stats = await self._get_requirements_statistics(project_id)
        
        # 3. 获取任务统计
        tasks_stats = await self._get_tasks_statistics(project_id)
        
        # 4. 获取追溯覆盖率
        traceability_coverage = await self._get_traceability_coverage(project_id)
        
        # 5. 计算进度指标
        progress_metrics = await self._calculate_progress_metrics(project_id)
        
        return {
            'project_id': project_id,
            'project_name': project.project_name,
            'requirements_stats': requirements_stats,
            'tasks_stats': tasks_stats,
            'traceability_coverage': traceability_coverage,
            'progress_metrics': progress_metrics,
            'last_sync_time': datetime.utcnow().isoformat()
        }
    
    async def sync_requirement_status_to_tasks(self, requirement_id: int, user_id: int) -> List[int]:
        """
        同步需求状态变更到关联任务
        
        Args:
            requirement_id: 需求ID
            user_id: 用户ID
            
        Returns:
            受影响的任务ID列表
        """
        # 1. 获取需求信息
        requirement = await self._get_requirement_by_id(requirement_id)
        if not requirement:
            raise NotFoundError(f"需求 {requirement_id} 不存在")
        
        # 2. 获取关联的任务
        tasks = await self._get_tasks_by_requirement(requirement_id)
        
        # 3. 根据需求状态更新任务状态
        updated_task_ids = []
        for task in tasks:
            new_task_status = self._map_requirement_status_to_task(requirement.status)
            if new_task_status and task.status != new_task_status:
                task.status = new_task_status
                task.updated_by = user_id
                task.updated_at = datetime.utcnow()
                updated_task_ids.append(task.id)
        
        await self.db.commit()
        
        logger.info(f"需求 {requirement_id} 状态同步到 {len(updated_task_ids)} 个任务")
        return updated_task_ids
    
    # 私有方法
    async def _get_project_requirements(self, project_id: int) -> List[Requirement]:
        """获取项目所有需求"""
        result = await self.db.execute(
            select(Requirement).where(Requirement.project_id == project_id)
        )
        return list(result.scalars().all())
    
    async def _sync_requirement_statistics(self, project: Project, requirements: List[Requirement]) -> Dict[str, Any]:
        """同步需求统计到项目"""
        total_requirements = len(requirements)
        completed_requirements = len([r for r in requirements if r.status in [
            RequirementStatus.COMPLETED, RequirementStatus.DEPLOYED, RequirementStatus.CLOSED
        ]])
        
        # 更新项目统计
        project.task_count = total_requirements  # 这里用需求数量作为任务数量的基础
        project.completed_task_count = completed_requirements
        
        # 计算完成百分比
        if total_requirements > 0:
            project.progress_percentage = Decimal(str((completed_requirements / total_requirements) * 100))
        else:
            project.progress_percentage = Decimal('0.00')
        
        return {
            'total_requirements': total_requirements,
            'completed_requirements': completed_requirements,
            'progress_percentage': float(project.progress_percentage)
        }
    
    async def _sync_requirement_progress_to_project(self, project: Project, requirements: List[Requirement]):
        """同步需求进度到项目进度"""
        if not requirements:
            return
        
        # 计算总体进度
        total_weight = 0
        completed_weight = 0
        
        for req in requirements:
            # 根据优先级设置权重
            weight = self._get_requirement_weight(req.priority)
            total_weight += weight
            
            # 根据状态计算完成度
            completion_rate = self._get_requirement_completion_rate(req.status)
            completed_weight += weight * completion_rate
        
        if total_weight > 0:
            project.progress_percentage = Decimal(str((completed_weight / total_weight) * 100))
    
    async def _sync_requirement_status_impact(self, project: Project, requirements: List[Requirement]):
        """同步需求状态变更影响"""
        # 检查是否有阻塞的需求
        blocked_requirements = [r for r in requirements if r.status == RequirementStatus.PAUSED]
        
        # 检查是否有失败的需求
        failed_requirements = [r for r in requirements if r.status == RequirementStatus.TEST_FAILED]
        
        # 更新项目健康度
        if blocked_requirements or failed_requirements:
            # 降低健康度
            impact_score = len(blocked_requirements) * 10 + len(failed_requirements) * 15
            project.health_score = max(0, project.health_score - impact_score)
        
        # 更新风险等级
        if len(failed_requirements) > len(requirements) * 0.2:  # 超过20%的需求测试失败
            project.risk_level = 'HIGH'
        elif len(blocked_requirements) > len(requirements) * 0.1:  # 超过10%的需求被阻塞
            project.risk_level = 'MEDIUM'
    
    async def _get_requirement_by_id(self, requirement_id: int) -> Optional[Requirement]:
        """获取需求信息"""
        result = await self.db.execute(
            select(Requirement).where(Requirement.id == requirement_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_task_by_id(self, task_id: int) -> Optional[Task]:
        """获取任务信息"""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def _validate_task_creation_permission(self, project_id: int, user_id: int):
        """验证任务创建权限"""
        # 检查用户是否是项目成员
        result = await self.db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.status == "ACTIVE"
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            raise PermissionError("没有在该项目中创建任务的权限")
    
    async def _generate_task_code(self, project_id: int) -> str:
        """生成任务编码"""
        # 获取项目信息
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")
        
        # 获取项目今日任务数量
        today = datetime.now().strftime("%Y%m%d")
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.project_id == project_id,
                    Task.task_code.like(f"TASK-{project.project_code}-{today}-%")
                )
            )
        )
        count = result.scalar() or 0
        
        return f"TASK-{project.project_code}-{today}-{count + 1:03d}"
    
    async def _create_requirement_task_traceability(self, requirement_id: int, task_id: int, user_id: int):
        """创建需求-任务追溯链接"""
        link = RequirementTraceabilityLink(
            source_type='requirement',
            source_id=requirement_id,
            target_type='task',
            target_id=task_id,
            link_type=TraceabilityLinkType.IMPLEMENTS,
            description=f"需求 {requirement_id} 由任务 {task_id} 实现",
            created_by=user_id
        )
        self.db.add(link)
    
    async def _get_requirements_by_task(self, task_id: int) -> List[Requirement]:
        """获取任务关联的需求"""
        result = await self.db.execute(
            select(Requirement).join(
                RequirementTraceabilityLink,
                and_(
                    RequirementTraceabilityLink.source_type == 'requirement',
                    RequirementTraceabilityLink.source_id == Requirement.id,
                    RequirementTraceabilityLink.target_type == 'task',
                    RequirementTraceabilityLink.target_id == task_id
                )
            )
        )
        return list(result.scalars().all())
    
    async def _get_tasks_by_requirement(self, requirement_id: int) -> List[Task]:
        """获取需求关联的任务"""
        result = await self.db.execute(
            select(Task).join(
                RequirementTraceabilityLink,
                and_(
                    RequirementTraceabilityLink.source_type == 'requirement',
                    RequirementTraceabilityLink.source_id == requirement_id,
                    RequirementTraceabilityLink.target_type == 'task',
                    RequirementTraceabilityLink.target_id == Task.id
                )
            )
        )
        return list(result.scalars().all())
    
    async def _get_requirements_statistics(self, project_id: int) -> Dict[str, Any]:
        """获取需求统计"""
        result = await self.db.execute(
            select(
                func.count(Requirement.id).label('total'),
                func.sum(func.case([(Requirement.status.in_([
                    RequirementStatus.COMPLETED, 
                    RequirementStatus.DEPLOYED, 
                    RequirementStatus.CLOSED
                ]), 1)], else_=0)).label('completed'),
                func.sum(func.case([(Requirement.status == RequirementStatus.IN_DEVELOPMENT, 1)], else_=0)).label('in_development'),
                func.sum(func.case([(Requirement.status == RequirementStatus.TESTING, 1)], else_=0)).label('testing'),
                func.sum(func.case([(Requirement.status == RequirementStatus.PAUSED, 1)], else_=0)).label('blocked')
            ).where(Requirement.project_id == project_id)
        )
        stats = result.first()
        
        return {
            'total': stats.total or 0,
            'completed': stats.completed or 0,
            'in_development': stats.in_development or 0,
            'testing': stats.testing or 0,
            'blocked': stats.blocked or 0
        }
    
    async def _get_tasks_statistics(self, project_id: int) -> Dict[str, Any]:
        """获取任务统计"""
        result = await self.db.execute(
            select(
                func.count(Task.id).label('total'),
                func.sum(func.case([(Task.status == 'COMPLETED', 1)], else_=0)).label('completed'),
                func.sum(func.case([(Task.status == 'IN_PROGRESS', 1)], else_=0)).label('in_progress'),
                func.sum(func.case([(Task.status == 'BLOCKED', 1)], else_=0)).label('blocked')
            ).where(Task.project_id == project_id)
        )
        stats = result.first()
        
        return {
            'total': stats.total or 0,
            'completed': stats.completed or 0,
            'in_progress': stats.in_progress or 0,
            'blocked': stats.blocked or 0
        }
    
    async def _get_traceability_coverage(self, project_id: int) -> Dict[str, Any]:
        """获取追溯覆盖率"""
        # 获取项目需求总数
        req_result = await self.db.execute(
            select(func.count(Requirement.id)).where(Requirement.project_id == project_id)
        )
        total_requirements = req_result.scalar() or 0
        
        # 获取有追溯链接的需求数
        traced_result = await self.db.execute(
            select(func.count(func.distinct(RequirementTraceabilityLink.source_id))).where(
                and_(
                    RequirementTraceabilityLink.source_type == 'requirement',
                    RequirementTraceabilityLink.source_id.in_(
                        select(Requirement.id).where(Requirement.project_id == project_id)
                    )
                )
            )
        )
        traced_requirements = traced_result.scalar() or 0
        
        coverage_rate = (traced_requirements / total_requirements * 100) if total_requirements > 0 else 0
        
        return {
            'total_requirements': total_requirements,
            'traced_requirements': traced_requirements,
            'coverage_rate': round(coverage_rate, 2)
        }
    
    async def _calculate_progress_metrics(self, project_id: int) -> Dict[str, Any]:
        """计算进度指标"""
        # 获取项目信息
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return {}
        
        # 计算进度偏差
        planned_progress = 0
        if project.planned_start_date and project.planned_end_date:
            total_days = (project.planned_end_date - project.planned_start_date).days
            elapsed_days = (date.today() - project.planned_start_date).days
            if total_days > 0:
                planned_progress = min(100, max(0, (elapsed_days / total_days) * 100))
        
        actual_progress = float(project.progress_percentage or 0)
        progress_variance = actual_progress - planned_progress
        
        return {
            'planned_progress': round(planned_progress, 2),
            'actual_progress': actual_progress,
            'progress_variance': round(progress_variance, 2),
            'health_score': project.health_score,
            'risk_level': project.risk_level
        }
    
    def _map_requirement_priority_to_task(self, requirement_priority) -> str:
        """映射需求优先级到任务优先级"""
        mapping = {
            'CRITICAL': 'URGENT',
            'HIGH': 'HIGH',
            'MEDIUM': 'MEDIUM',
            'LOW': 'LOW',
            'OPTIONAL': 'LOW'
        }
        return mapping.get(requirement_priority.value if requirement_priority else 'MEDIUM', 'MEDIUM')
    
    def _map_task_status_to_requirement(self, task_status: str) -> Optional[RequirementStatus]:
        """映射任务状态到需求状态"""
        mapping = {
            'IN_PROGRESS': RequirementStatus.IN_DEVELOPMENT,
            'COMPLETED': RequirementStatus.COMPLETED,
            'BLOCKED': RequirementStatus.PAUSED,
            'CANCELLED': RequirementStatus.CANCELLED
        }
        return mapping.get(task_status)
    
    def _map_requirement_status_to_task(self, requirement_status: RequirementStatus) -> Optional[str]:
        """映射需求状态到任务状态"""
        mapping = {
            RequirementStatus.APPROVED: 'ASSIGNED',
            RequirementStatus.IN_DEVELOPMENT: 'IN_PROGRESS',
            RequirementStatus.PAUSED: 'ON_HOLD',
            RequirementStatus.COMPLETED: 'COMPLETED',
            RequirementStatus.CANCELLED: 'CANCELLED'
        }
        return mapping.get(requirement_status)
    
    def _estimate_hours_from_effort(self, effort_days: Optional[Decimal]) -> Optional[Decimal]:
        """从工作量（天）估算工时"""
        if effort_days:
            return effort_days * 8  # 假设每天8小时
        return None
    
    def _get_requirement_weight(self, priority) -> float:
        """获取需求权重"""
        weights = {
            'CRITICAL': 5.0,
            'HIGH': 3.0,
            'MEDIUM': 2.0,
            'LOW': 1.0,
            'OPTIONAL': 0.5
        }
        return weights.get(priority.value if priority else 'MEDIUM', 2.0)
    
    def _get_requirement_completion_rate(self, status: RequirementStatus) -> float:
        """获取需求完成率"""
        rates = {
            RequirementStatus.DRAFT: 0.0,
            RequirementStatus.PENDING_REVIEW: 0.1,
            RequirementStatus.REVIEWING: 0.2,
            RequirementStatus.NEEDS_REVISION: 0.15,
            RequirementStatus.APPROVED: 0.3,
            RequirementStatus.IN_DEVELOPMENT: 0.6,
            RequirementStatus.PAUSED: 0.4,
            RequirementStatus.TESTING: 0.8,
            RequirementStatus.TEST_FAILED: 0.7,
            RequirementStatus.COMPLETED: 1.0,
            RequirementStatus.DEPLOYED: 1.0,
            RequirementStatus.CLOSED: 1.0,
            RequirementStatus.CANCELLED: 0.0
        }
        return rates.get(status, 0.0)


# 依赖注入函数
async def get_project_requirement_integration_service(db: AsyncSession = None) -> ProjectRequirementIntegrationService:
    """获取项目需求集成服务实例"""
    if db is None:
        async with get_async_session() as session:
            return ProjectRequirementIntegrationService(session)
    return ProjectRequirementIntegrationService(db)