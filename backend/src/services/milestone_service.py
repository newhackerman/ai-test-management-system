"""
里程碑管理服务

本模块实现里程碑管理的核心业务逻辑，包括：
- 里程碑CRUD操作
- 里程碑状态流转管理
- 里程碑依赖关系管理
- 里程碑影响分析
- 里程碑进度跟踪
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.project import Project, Milestone, Task
from ..models.user import User
from ..schemas.milestone import (
    CreateMilestoneRequest, UpdateMilestoneRequest, MilestoneQueryParams,
    MilestoneResponse, MilestoneListResponse, MilestoneSummaryResponse,
    CreateMilestoneResponse, UpdateMilestoneResponse, DeleteMilestoneResponse,
    MilestoneDependencyAnalysis, MilestoneImpactAnalysis, MilestoneStatistics,
    MilestoneTimeline, MilestoneTimelineItem, MilestoneStatus, MilestoneType,
    Deliverable, MilestoneDependency
)

logger = logging.getLogger(__name__)


class MilestoneService:
    """里程碑管理服务"""
    
    def __init__(self):
        pass
    
    async def create_milestone(
        self, 
        project_id: int,
        milestone_data: CreateMilestoneRequest, 
        creator_id: int,
        session: AsyncSession
    ) -> CreateMilestoneResponse:
        """
        创建里程碑
        
        Args:
            project_id: 项目ID
            milestone_data: 里程碑数据
            creator_id: 创建人ID
            session: 数据库会话
            
        Returns:
            CreateMilestoneResponse: 创建结果
        """
        try:
            # 验证项目存在
            project = await self._get_project(project_id, session)
            if not project:
                raise NotFoundError(f"项目 {project_id} 不存在")
            
            # 验证里程碑名称唯一性
            await self._validate_milestone_name_unique(
                project_id, milestone_data.milestone_name, session
            )
            
            # 验证依赖关系
            await self._validate_milestone_dependencies(
                project_id, milestone_data.dependencies, session
            )
            
            # 创建里程碑实体
            milestone = Milestone(
                project_id=project_id,
                milestone_name=milestone_data.milestone_name,
                description=milestone_data.description,
                milestone_type=milestone_data.milestone_type.value,
                planned_date=milestone_data.planned_date,
                owner_id=milestone_data.owner_id,
                deliverables=[d.dict() for d in milestone_data.deliverables],
                acceptance_criteria=milestone_data.acceptance_criteria,
                dependency_milestones=[d.dict() for d in milestone_data.dependencies],
                created_by=creator_id
            )
            
            # 保存里程碑
            session.add(milestone)
            await session.flush()
            await session.refresh(milestone)
            
            # 转换为响应模式
            milestone_response = await self._convert_to_response(milestone, session)
            
            await session.commit()
            
            logger.info(f"用户 {creator_id} 在项目 {project_id} 中创建里程碑 {milestone.id}")
            
            return CreateMilestoneResponse(
                success=True,
                message="里程碑创建成功",
                milestone=milestone_response
            )
            
        except Exception as e:
            await session.rollback()
            logger.error(f"创建里程碑失败: {str(e)}")
            raise
    
    async def update_milestone(
        self,
        milestone_id: int,
        milestone_data: UpdateMilestoneRequest,
        updater_id: int,
        session: AsyncSession
    ) -> UpdateMilestoneResponse:
        """
        更新里程碑
        
        Args:
            milestone_id: 里程碑ID
            milestone_data: 更新数据
            updater_id: 更新人ID
            session: 数据库会话
            
        Returns:
            UpdateMilestoneResponse: 更新结果
        """
        try:
            # 获取里程碑
            milestone = await self._get_milestone(milestone_id, session)
            if not milestone:
                raise NotFoundError(f"里程碑 {milestone_id} 不存在")
            
            # 验证状态流转
            if milestone_data.status:
                await self._validate_status_transition(
                    milestone, milestone_data.status, session
                )
            
            # 更新字段
            update_data = milestone_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field == 'deliverables' and value is not None:
                    setattr(milestone, field, [d.dict() if hasattr(d, 'dict') else d for d in value])
                elif field == 'dependencies' and value is not None:
                    setattr(milestone, 'dependency_milestones', [d.dict() if hasattr(d, 'dict') else d for d in value])
                elif field == 'status' and value is not None:
                    setattr(milestone, field, value.value)
                elif field == 'milestone_type' and value is not None:
                    setattr(milestone, field, value.value)
                elif hasattr(milestone, field):
                    setattr(milestone, field, value)
            
            milestone.updated_by = updater_id
            milestone.updated_at = datetime.utcnow()
            
            # 如果状态变为完成，设置实际完成日期
            if milestone_data.status == MilestoneStatus.COMPLETED and not milestone.actual_date:
                milestone.actual_date = date.today()
            
            # 转换为响应模式
            milestone_response = await self._convert_to_response(milestone, session)
            
            await session.commit()
            
            logger.info(f"用户 {updater_id} 更新里程碑 {milestone_id}")
            
            return UpdateMilestoneResponse(
                success=True,
                message="里程碑更新成功",
                milestone=milestone_response
            )
            
        except Exception as e:
            await session.rollback()
            logger.error(f"更新里程碑 {milestone_id} 失败: {str(e)}")
            raise
    
    async def get_milestone(
        self,
        milestone_id: int,
        session: AsyncSession
    ) -> Optional[MilestoneResponse]:
        """
        获取里程碑详情
        
        Args:
            milestone_id: 里程碑ID
            session: 数据库会话
            
        Returns:
            MilestoneResponse: 里程碑详情
        """
        milestone = await self._get_milestone(milestone_id, session)
        if not milestone:
            return None
        
        return await self._convert_to_response(milestone, session)
    
    async def list_milestones(
        self,
        project_id: int,
        params: MilestoneQueryParams,
        session: AsyncSession
    ) -> MilestoneListResponse:
        """
        获取里程碑列表
        
        Args:
            project_id: 项目ID
            params: 查询参数
            session: 数据库会话
            
        Returns:
            MilestoneListResponse: 里程碑列表
        """
        # 构建查询条件
        conditions = [Milestone.project_id == project_id]
        
        # 状态过滤
        if params.status:
            status_values = [s.value for s in params.status]
            conditions.append(Milestone.status.in_(status_values))
        
        # 类型过滤
        if params.milestone_type:
            type_values = [t.value for t in params.milestone_type]
            conditions.append(Milestone.milestone_type.in_(type_values))
        
        # 负责人过滤
        if params.owner_id:
            conditions.append(Milestone.owner_id == params.owner_id)
        
        # 日期范围过滤
        if params.date_from:
            conditions.append(Milestone.planned_date >= params.date_from)
        if params.date_to:
            conditions.append(Milestone.planned_date <= params.date_to)
        
        # 逾期过滤
        if params.overdue_only:
            today = date.today()
            conditions.append(
                and_(
                    Milestone.status != MilestoneStatus.COMPLETED.value,
                    Milestone.planned_date < today
                )
            )
        
        # 即将到期过滤
        if params.upcoming_days:
            future_date = date.today() + timedelta(days=params.upcoming_days)
            conditions.append(
                and_(
                    Milestone.status != MilestoneStatus.COMPLETED.value,
                    Milestone.planned_date <= future_date,
                    Milestone.planned_date >= date.today()
                )
            )
        
        # 搜索过滤
        if params.search:
            search_term = f"%{params.search}%"
            conditions.append(
                or_(
                    Milestone.milestone_name.ilike(search_term),
                    Milestone.description.ilike(search_term)
                )
            )
        
        # 构建查询
        query = select(Milestone).where(and_(*conditions))
        
        # 排序
        if params.sort_by == "planned_date":
            order_col = Milestone.planned_date
        elif params.sort_by == "status":
            order_col = Milestone.status
        elif params.sort_by == "milestone_type":
            order_col = Milestone.milestone_type
        else:
            order_col = Milestone.planned_date
        
        if params.sort_order == "desc":
            query = query.order_by(desc(order_col))
        else:
            query = query.order_by(asc(order_col))
        
        # 获取总数
        count_query = select(func.count()).select_from(
            select(Milestone).where(and_(*conditions)).subquery()
        )
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (params.page - 1) * params.size
        query = query.offset(offset).limit(params.size)
        
        # 执行查询
        result = await session.execute(query)
        milestones = result.scalars().all()
        
        # 转换为响应模式
        milestone_responses = []
        for milestone in milestones:
            milestone_response = await self._convert_to_response(milestone, session)
            milestone_responses.append(milestone_response)
        
        total_pages = (total + params.size - 1) // params.size
        
        return MilestoneListResponse(
            milestones=milestone_responses,
            total=total,
            page=params.page,
            size=params.size,
            total_pages=total_pages
        )
    
    async def delete_milestone(
        self,
        milestone_id: int,
        deleter_id: int,
        session: AsyncSession
    ) -> DeleteMilestoneResponse:
        """
        删除里程碑
        
        Args:
            milestone_id: 里程碑ID
            deleter_id: 删除人ID
            session: 数据库会话
            
        Returns:
            DeleteMilestoneResponse: 删除结果
        """
        try:
            # 获取里程碑
            milestone = await self._get_milestone(milestone_id, session)
            if not milestone:
                raise NotFoundError(f"里程碑 {milestone_id} 不存在")
            
            # 检查依赖关系
            await self._check_milestone_dependencies_before_delete(milestone_id, session)
            
            # 软删除
            milestone.deleted_at = datetime.utcnow()
            milestone.updated_by = deleter_id
            
            await session.commit()
            
            logger.info(f"用户 {deleter_id} 删除里程碑 {milestone_id}")
            
            return DeleteMilestoneResponse(
                success=True,
                message="里程碑删除成功",
                milestone_id=milestone_id,
                deleted_at=milestone.deleted_at
            )
            
        except Exception as e:
            await session.rollback()
            logger.error(f"删除里程碑 {milestone_id} 失败: {str(e)}")
            raise
    
    async def analyze_milestone_dependencies(
        self,
        milestone_id: int,
        session: AsyncSession
    ) -> MilestoneDependencyAnalysis:
        """
        分析里程碑依赖关系
        
        Args:
            milestone_id: 里程碑ID
            session: 数据库会话
            
        Returns:
            MilestoneDependencyAnalysis: 依赖分析结果
        """
        milestone = await self._get_milestone(milestone_id, session)
        if not milestone:
            raise NotFoundError(f"里程碑 {milestone_id} 不存在")
        
        # 获取依赖的里程碑
        dependencies = []
        if milestone.dependency_milestones:
            dependency_ids = [dep['milestone_id'] for dep in milestone.dependency_milestones]
            if dependency_ids:
                dep_query = select(Milestone).where(Milestone.id.in_(dependency_ids))
                dep_result = await session.execute(dep_query)
                dep_milestones = dep_result.scalars().all()
                
                for dep_milestone in dep_milestones:
                    dependencies.append(await self._convert_to_response(dep_milestone, session))
        
        # 获取依赖此里程碑的其他里程碑
        dependents = []
        dependent_query = select(Milestone).where(
            and_(
                Milestone.project_id == milestone.project_id,
                Milestone.dependency_milestones.contains([{'milestone_id': milestone_id}])
            )
        )
        dependent_result = await session.execute(dependent_query)
        dependent_milestones = dependent_result.scalars().all()
        
        for dependent_milestone in dependent_milestones:
            dependents.append(await self._convert_to_response(dependent_milestone, session))
        
        # 关键路径分析
        is_on_critical_path, critical_path_position = await self._analyze_critical_path(
            milestone, session
        )
        
        # 延期影响分析
        delay_impact = await self._analyze_delay_impact(milestone, session)
        
        # 风险等级评估
        risk_level = self._calculate_milestone_risk_level(milestone, dependencies, dependents)
        
        return MilestoneDependencyAnalysis(
            milestone_id=milestone_id,
            milestone_name=milestone.milestone_name,
            dependencies=dependencies,
            dependents=dependents,
            is_on_critical_path=is_on_critical_path,
            critical_path_position=critical_path_position,
            delay_impact=delay_impact,
            risk_level=risk_level,
            analyzed_at=datetime.utcnow()
        )
    
    async def analyze_milestone_impact(
        self,
        milestone_id: int,
        delay_days: int,
        session: AsyncSession
    ) -> MilestoneImpactAnalysis:
        """
        分析里程碑延期影响
        
        Args:
            milestone_id: 里程碑ID
            delay_days: 延期天数
            session: 数据库会话
            
        Returns:
            MilestoneImpactAnalysis: 影响分析结果
        """
        milestone = await self._get_milestone(milestone_id, session)
        if not milestone:
            raise NotFoundError(f"里程碑 {milestone_id} 不存在")
        
        # 分析受影响的里程碑
        affected_milestones = await self._find_affected_milestones(
            milestone_id, delay_days, session
        )
        
        # 分析受影响的任务
        affected_tasks = await self._find_affected_tasks(
            milestone_id, delay_days, session
        )
        
        # 计算总延期天数
        total_delay_days = delay_days
        project_delay_days = await self._calculate_project_delay(
            milestone, delay_days, session
        )
        
        # 估算成本影响
        estimated_cost_impact = await self._estimate_cost_impact(
            milestone, delay_days, session
        )
        
        # 风险评分
        risk_score = self._calculate_impact_risk_score(
            delay_days, len(affected_milestones), len(affected_tasks)
        )
        
        # 缓解建议
        mitigation_suggestions = self._generate_mitigation_suggestions(
            milestone, delay_days, affected_milestones, affected_tasks
        )
        
        return MilestoneImpactAnalysis(
            milestone_id=milestone_id,
            milestone_name=milestone.milestone_name,
            affected_milestones=affected_milestones,
            affected_tasks=affected_tasks,
            total_delay_days=total_delay_days,
            project_delay_days=project_delay_days,
            estimated_cost_impact=estimated_cost_impact,
            risk_score=risk_score,
            mitigation_suggestions=mitigation_suggestions,
            analyzed_at=datetime.utcnow()
        )
    
    async def get_milestone_statistics(
        self,
        project_id: int,
        session: AsyncSession
    ) -> MilestoneStatistics:
        """
        获取里程碑统计信息
        
        Args:
            project_id: 项目ID
            session: 数据库会话
            
        Returns:
            MilestoneStatistics: 统计信息
        """
        # 获取所有里程碑
        query = select(Milestone).where(
            and_(
                Milestone.project_id == project_id,
                Milestone.deleted_at.is_(None)
            )
        )
        result = await session.execute(query)
        milestones = result.scalars().all()
        
        total_milestones = len(milestones)
        completed_milestones = len([m for m in milestones if m.status == MilestoneStatus.COMPLETED.value])
        cancelled_milestones = len([m for m in milestones if m.status == MilestoneStatus.CANCELLED.value])
        
        # 逾期里程碑
        today = date.today()
        overdue_milestones = len([
            m for m in milestones 
            if m.status != MilestoneStatus.COMPLETED.value and m.planned_date < today
        ])
        
        # 即将到期里程碑（7天内）
        upcoming_date = today + timedelta(days=7)
        upcoming_milestones = len([
            m for m in milestones 
            if m.status != MilestoneStatus.COMPLETED.value and today <= m.planned_date <= upcoming_date
        ])
        
        # 按类型统计
        milestones_by_type = {}
        for milestone_type in MilestoneType:
            count = len([m for m in milestones if m.milestone_type == milestone_type.value])
            milestones_by_type[milestone_type.value] = count
        
        # 按状态统计
        milestones_by_status = {}
        for milestone_status in MilestoneStatus:
            count = len([m for m in milestones if m.status == milestone_status.value])
            milestones_by_status[milestone_status.value] = count
        
        # 完成率
        completion_rate = Decimal(str(completed_milestones / total_milestones)) if total_milestones > 0 else Decimal('0')
        
        # 按时完成率
        on_time_completed = len([
            m for m in milestones 
            if m.status == MilestoneStatus.COMPLETED.value and m.actual_date and m.actual_date <= m.planned_date
        ])
        on_time_completion_rate = Decimal(str(on_time_completed / completed_milestones)) if completed_milestones > 0 else Decimal('0')
        
        # 平均完成天数
        completed_with_dates = [
            m for m in milestones 
            if m.status == MilestoneStatus.COMPLETED.value and m.actual_date
        ]
        if completed_with_dates:
            total_completion_days = sum([
                (m.actual_date - m.planned_date).days for m in completed_with_dates
            ])
            average_completion_days = Decimal(str(total_completion_days / len(completed_with_dates)))
        else:
            average_completion_days = None
        
        # 平均延期天数
        delayed_milestones = [
            m for m in completed_with_dates 
            if m.actual_date > m.planned_date
        ]
        if delayed_milestones:
            total_delay_days = sum([
                (m.actual_date - m.planned_date).days for m in delayed_milestones
            ])
            average_delay_days = Decimal(str(total_delay_days / len(delayed_milestones)))
        else:
            average_delay_days = None
        
        return MilestoneStatistics(
            project_id=project_id,
            total_milestones=total_milestones,
            completed_milestones=completed_milestones,
            overdue_milestones=overdue_milestones,
            upcoming_milestones=upcoming_milestones,
            cancelled_milestones=cancelled_milestones,
            milestones_by_type=milestones_by_type,
            milestones_by_status=milestones_by_status,
            completion_rate=completion_rate,
            on_time_completion_rate=on_time_completion_rate,
            average_completion_days=average_completion_days,
            average_delay_days=average_delay_days,
            calculated_at=datetime.utcnow()
        )
    
    async def get_milestone_timeline(
        self,
        project_id: int,
        session: AsyncSession
    ) -> MilestoneTimeline:
        """
        获取里程碑时间轴
        
        Args:
            project_id: 项目ID
            session: 数据库会话
            
        Returns:
            MilestoneTimeline: 时间轴
        """
        # 获取所有里程碑，按计划日期排序
        query = select(Milestone).where(
            and_(
                Milestone.project_id == project_id,
                Milestone.deleted_at.is_(None)
            )
        ).order_by(Milestone.planned_date)
        
        result = await session.execute(query)
        milestones = result.scalars().all()
        
        if not milestones:
            return MilestoneTimeline(
                project_id=project_id,
                timeline_items=[],
                start_date=date.today(),
                end_date=date.today(),
                critical_path=[],
                generated_at=datetime.utcnow()
            )
        
        # 构建时间轴项目
        timeline_items = []
        for milestone in milestones:
            completion_percentage = await self._calculate_milestone_completion(milestone, session)
            is_critical = await self._is_milestone_critical(milestone, session)
            
            timeline_items.append(MilestoneTimelineItem(
                milestone_id=milestone.id,
                milestone_name=milestone.milestone_name,
                milestone_type=MilestoneType(milestone.milestone_type),
                status=MilestoneStatus(milestone.status),
                planned_date=milestone.planned_date,
                actual_date=milestone.actual_date,
                completion_percentage=completion_percentage,
                is_critical=is_critical
            ))
        
        # 计算关键路径
        critical_path = await self._calculate_critical_path(milestones, session)
        
        start_date = min(m.planned_date for m in milestones)
        end_date = max(m.planned_date for m in milestones)
        
        return MilestoneTimeline(
            project_id=project_id,
            timeline_items=timeline_items,
            start_date=start_date,
            end_date=end_date,
            critical_path=critical_path,
            generated_at=datetime.utcnow()
        )
    
    # 私有辅助方法
    async def _get_project(self, project_id: int, session: AsyncSession) -> Optional[Project]:
        """获取项目"""
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_milestone(self, milestone_id: int, session: AsyncSession) -> Optional[Milestone]:
        """获取里程碑"""
        query = select(Milestone).where(
            and_(
                Milestone.id == milestone_id,
                Milestone.deleted_at.is_(None)
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def _validate_milestone_name_unique(
        self, 
        project_id: int, 
        milestone_name: str, 
        session: AsyncSession,
        exclude_id: Optional[int] = None
    ):
        """验证里程碑名称唯一性"""
        conditions = [
            Milestone.project_id == project_id,
            Milestone.milestone_name == milestone_name,
            Milestone.deleted_at.is_(None)
        ]
        
        if exclude_id:
            conditions.append(Milestone.id != exclude_id)
        
        query = select(Milestone).where(and_(*conditions))
        result = await session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValidationError(f"里程碑名称 '{milestone_name}' 已存在")
    
    async def _validate_milestone_dependencies(
        self,
        project_id: int,
        dependencies: List[MilestoneDependency],
        session: AsyncSession
    ):
        """验证里程碑依赖关系"""
        if not dependencies:
            return
        
        dependency_ids = [dep.milestone_id for dep in dependencies]
        
        # 检查依赖的里程碑是否存在且属于同一项目
        query = select(Milestone).where(
            and_(
                Milestone.id.in_(dependency_ids),
                Milestone.project_id == project_id,
                Milestone.deleted_at.is_(None)
            )
        )
        result = await session.execute(query)
        existing_milestones = result.scalars().all()
        existing_ids = [m.id for m in existing_milestones]
        
        missing_ids = set(dependency_ids) - set(existing_ids)
        if missing_ids:
            raise ValidationError(f"依赖的里程碑不存在: {missing_ids}")
    
    async def _validate_status_transition(
        self,
        milestone: Milestone,
        new_status: MilestoneStatus,
        session: AsyncSession
    ):
        """验证状态流转"""
        current_status = MilestoneStatus(milestone.status)
        
        # 定义允许的状态流转
        allowed_transitions = {
            MilestoneStatus.PENDING: [MilestoneStatus.IN_PROGRESS, MilestoneStatus.CANCELLED],
            MilestoneStatus.IN_PROGRESS: [MilestoneStatus.COMPLETED, MilestoneStatus.OVERDUE, MilestoneStatus.CANCELLED],
            MilestoneStatus.OVERDUE: [MilestoneStatus.COMPLETED, MilestoneStatus.CANCELLED],
            MilestoneStatus.COMPLETED: [MilestoneStatus.IN_PROGRESS],  # 允许重新打开
            MilestoneStatus.CANCELLED: [MilestoneStatus.PENDING]  # 允许重新激活
        }
        
        if new_status not in allowed_transitions.get(current_status, []):
            raise ValidationError(f"不能从 {current_status.value} 状态转换到 {new_status.value} 状态")
    
    async def _convert_to_response(
        self, 
        milestone: Milestone, 
        session: AsyncSession
    ) -> MilestoneResponse:
        """转换为响应模式"""
        # 计算完成百分比
        completion_percentage = await self._calculate_milestone_completion(milestone, session)
        
        # 计算天数信息
        today = date.today()
        days_overdue = None
        days_remaining = None
        
        if milestone.status != MilestoneStatus.COMPLETED.value:
            if milestone.planned_date < today:
                days_overdue = (today - milestone.planned_date).days
            else:
                days_remaining = (milestone.planned_date - today).days
        
        # 转换交付物
        deliverables = []
        if milestone.deliverables:
            for d in milestone.deliverables:
                if isinstance(d, dict):
                    deliverables.append(Deliverable(**d))
                else:
                    deliverables.append(d)
        
        # 转换依赖关系
        dependencies = []
        if milestone.dependency_milestones:
            for d in milestone.dependency_milestones:
                if isinstance(d, dict):
                    dependencies.append(MilestoneDependency(**d))
                else:
                    dependencies.append(d)
        
        return MilestoneResponse(
            id=milestone.id,
            project_id=milestone.project_id,
            milestone_name=milestone.milestone_name,
            description=milestone.description,
            milestone_type=MilestoneType(milestone.milestone_type),
            status=MilestoneStatus(milestone.status),
            planned_date=milestone.planned_date,
            actual_date=milestone.actual_date,
            owner_id=milestone.owner_id,
            deliverables=deliverables,
            acceptance_criteria=milestone.acceptance_criteria,
            dependencies=dependencies,
            completion_percentage=completion_percentage,
            days_overdue=days_overdue,
            days_remaining=days_remaining,
            tags=None,  # TODO: 实现标签功能
            custom_fields=None,  # TODO: 实现自定义字段
            created_by=milestone.created_by,
            updated_by=milestone.updated_by,
            created_at=milestone.created_at,
            updated_at=milestone.updated_at
        )
    
    async def _calculate_milestone_completion(
        self, 
        milestone: Milestone, 
        session: AsyncSession
    ) -> Decimal:
        """计算里程碑完成百分比"""
        if milestone.status == MilestoneStatus.COMPLETED.value:
            return Decimal('100')
        elif milestone.status == MilestoneStatus.CANCELLED.value:
            return Decimal('0')
        
        # 基于交付物完成情况计算
        if milestone.deliverables:
            total_deliverables = len(milestone.deliverables)
            completed_deliverables = len([
                d for d in milestone.deliverables 
                if d.get('status') in ['COMPLETED', 'REVIEWED', 'APPROVED']
            ])
            return Decimal(str(completed_deliverables / total_deliverables * 100))
        
        # 如果没有交付物，基于状态估算
        if milestone.status == MilestoneStatus.IN_PROGRESS.value:
            return Decimal('50')
        else:
            return Decimal('0')
    
    async def _check_milestone_dependencies_before_delete(
        self, 
        milestone_id: int, 
        session: AsyncSession
    ):
        """检查删除前的依赖关系"""
        # 检查是否有其他里程碑依赖此里程碑
        query = select(Milestone).where(
            and_(
                Milestone.dependency_milestones.contains([{'milestone_id': milestone_id}]),
                Milestone.deleted_at.is_(None)
            )
        )
        result = await session.execute(query)
        dependent_milestones = result.scalars().all()
        
        if dependent_milestones:
            milestone_names = [m.milestone_name for m in dependent_milestones]
            raise ValidationError(f"无法删除，以下里程碑依赖此里程碑: {', '.join(milestone_names)}")
    
    # 分析相关的私有方法（简化实现）
    async def _analyze_critical_path(
        self, 
        milestone: Milestone, 
        session: AsyncSession
    ) -> Tuple[bool, Optional[int]]:
        """分析关键路径"""
        # 简化实现：假设所有里程碑都在关键路径上
        return True, 1
    
    async def _analyze_delay_impact(
        self, 
        milestone: Milestone, 
        session: AsyncSession
    ) -> Dict[str, Any]:
        """分析延期影响"""
        return {
            "affected_milestones_count": 0,
            "affected_tasks_count": 0,
            "estimated_delay_days": 0
        }
    
    def _calculate_milestone_risk_level(
        self, 
        milestone: Milestone, 
        dependencies: List[MilestoneResponse], 
        dependents: List[MilestoneResponse]
    ) -> str:
        """计算里程碑风险等级"""
        risk_score = 0
        
        # 依赖数量影响风险
        risk_score += len(dependencies) * 10
        
        # 被依赖数量影响风险
        risk_score += len(dependents) * 15
        
        # 逾期影响风险
        if milestone.planned_date < date.today() and milestone.status != MilestoneStatus.COMPLETED.value:
            risk_score += 30
        
        if risk_score >= 50:
            return "HIGH"
        elif risk_score >= 25:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _find_affected_milestones(
        self, 
        milestone_id: int, 
        delay_days: int, 
        session: AsyncSession
    ) -> List[MilestoneSummaryResponse]:
        """查找受影响的里程碑"""
        # 简化实现
        return []
    
    async def _find_affected_tasks(
        self, 
        milestone_id: int, 
        delay_days: int, 
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """查找受影响的任务"""
        # 简化实现
        return []
    
    async def _calculate_project_delay(
        self, 
        milestone: Milestone, 
        delay_days: int, 
        session: AsyncSession
    ) -> int:
        """计算项目延期天数"""
        # 简化实现
        return delay_days
    
    async def _estimate_cost_impact(
        self, 
        milestone: Milestone, 
        delay_days: int, 
        session: AsyncSession
    ) -> Optional[Decimal]:
        """估算成本影响"""
        # 简化实现
        return None
    
    def _calculate_impact_risk_score(
        self, 
        delay_days: int, 
        affected_milestones_count: int, 
        affected_tasks_count: int
    ) -> Decimal:
        """计算影响风险评分"""
        score = delay_days * 2 + affected_milestones_count * 5 + affected_tasks_count * 1
        return min(Decimal(str(score)), Decimal('100'))
    
    def _generate_mitigation_suggestions(
        self, 
        milestone: Milestone, 
        delay_days: int, 
        affected_milestones: List[MilestoneSummaryResponse], 
        affected_tasks: List[Dict[str, Any]]
    ) -> List[str]:
        """生成缓解建议"""
        suggestions = []
        
        if delay_days > 7:
            suggestions.append("考虑增加资源投入以缩短延期时间")
        
        if len(affected_milestones) > 0:
            suggestions.append("重新评估后续里程碑的时间安排")
        
        if len(affected_tasks) > 0:
            suggestions.append("优化任务执行顺序，减少依赖影响")
        
        suggestions.append("加强项目监控和风险管理")
        
        return suggestions
    
    async def _is_milestone_critical(
        self, 
        milestone: Milestone, 
        session: AsyncSession
    ) -> bool:
        """判断里程碑是否关键"""
        # 简化实现：基于依赖数量判断
        if milestone.dependency_milestones:
            return len(milestone.dependency_milestones) > 0
        return False
    
    async def _calculate_critical_path(
        self, 
        milestones: List[Milestone], 
        session: AsyncSession
    ) -> List[int]:
        """计算关键路径"""
        # 简化实现：返回所有里程碑ID
        return [m.id for m in milestones]