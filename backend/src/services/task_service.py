"""
任务管理核心服务

本模块实现任务管理的核心业务逻辑，包括：
- 任务CRUD操作
- 任务状态管理
- 任务分配和跟踪
- 任务依赖关系管理
- 任务进度计算
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload
from fastapi import Depends

from ..core.database import get_async_session, get_async_session_ctx
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.project import Task, Project, ProjectMember
from ..models.user import User
from ..schemas.task import (
    CreateTaskRequest, UpdateTaskRequest, TaskQueryParams,
    TaskResponse, TaskListResponse, TaskSummaryResponse,
    TaskStatusUpdateRequest, TaskAssignmentRequest, TaskProgressUpdateRequest,
    TaskDependencyRequest, TaskStatisticsResponse, TaskStatus, TaskType, TaskPriority
)
from ..services.project_data_sync_service import notify_project_change, SyncEventType
from ..services.system_notification_service import SystemNotificationService
from ..services.task_dependency_service import TaskDependencyService

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.dependency_service = TaskDependencyService(db)
    
    async def create_task(self, request: CreateTaskRequest, creator_id: int) -> Task:
        """
        创建任务
        
        Args:
            request: 创建任务请求
            creator_id: 创建者ID
            
        Returns:
            创建的任务对象
            
        Raises:
            ValidationError: 数据验证失败
            PermissionError: 权限不足
            NotFoundError: 项目不存在
        """
        # 1. 验证项目存在和权限
        project = await self._validate_project_access(request.project_id, creator_id)
        
        # 2. 验证任务数据
        await self._validate_task_data(request)
        
        # 3. 验证依赖关系
        if request.dependency_tasks:
            await self._validate_task_dependencies(request.dependency_tasks, request.project_id)
        
        # 4. 验证人员分配
        assignee_ids = self._normalize_assignee_ids(request.assignee_id, request.assignee_ids)
        for assignee_id in assignee_ids:
            await self._validate_task_assignee(assignee_id, request.project_id)
        
        # 5. 生成任务编码
        task_code = await self._generate_task_code(request.project_id)
        
        # 6. 创建任务实体
        task = Task(
            project_id=request.project_id,
            task_code=task_code,
            task_name=request.task_name,
            description=request.description,
            task_type=request.task_type,
            priority=request.priority,
            status=request.status,
            assignee_id=assignee_ids[0] if assignee_ids else None,
            assignee_ids=assignee_ids or None,
            reporter_id=request.reporter_id or creator_id,
            reviewer_id=request.reviewer_id,
            planned_start_date=request.planned_start_date,
            planned_end_date=request.planned_end_date,
            estimated_hours=request.estimated_hours,
            parent_task_id=request.parent_task_id,
            dependency_tasks=request.dependency_tasks,
            acceptance_criteria=request.acceptance_criteria,
            tags=request.tags,
            attachments=request.attachments,
            created_by=creator_id
        )
        await self._handle_task_status_change(task, TaskStatus.TODO, request.status)
        
        # 7. 保存任务
        self.db.add(task)
        await self.db.flush()  # 获取任务ID
        
        # 8. 更新项目任务计数
        await self._update_project_task_count(request.project_id)
        await self._update_project_progress(request.project_id)
        
        # 9. 提交事务
        await self.db.commit()
        await self.db.refresh(task)
        
        # 10. 通知数据同步服务
        await notify_project_change(
            SyncEventType.TASK_CREATED,
            task.project_id,
            task.id,
            task.to_dict(),
            creator_id
        )
        
        logger.info(f"任务创建成功: {task.task_code} - {task.task_name}")
        return task
    
    async def get_task_by_id(self, task_id: int, user_id: int) -> Optional[Task]:
        """
        根据ID获取任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            任务对象或None
            
        Raises:
            PermissionError: 权限不足
        """
        # 查询任务
        result = await self.db.execute(
            select(Task)
            .options(selectinload(Task.project))
            .where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        # 检查访问权限
        await self._validate_task_access(task, user_id)
        
        return task
    
    async def get_tasks_list(
        self, 
        params: TaskQueryParams, 
        user_id: int
    ) -> Tuple[List[Task], int]:
        """
        获取任务列表
        
        Args:
            params: 查询参数
            user_id: 用户ID
            
        Returns:
            (任务列表, 总数)
        """
        # 构建基础查询
        query = select(Task).options(selectinload(Task.project))
        count_query = select(func.count(Task.id))
        
        # 应用过滤条件
        filters = []
        
        # 项目过滤
        if params.project_id:
            filters.append(Task.project_id == params.project_id)
        
        # 状态过滤
        if params.status:
            filters.append(Task.status.in_(params.status))
        
        # 类型过滤
        if params.task_type:
            filters.append(Task.task_type.in_(params.task_type))
        
        # 优先级过滤
        if params.priority:
            filters.append(Task.priority.in_(params.priority))
        
        # 人员过滤
        if params.assignee_id:
            filters.append(Task.assignee_id == params.assignee_id)
        if params.reporter_id:
            filters.append(Task.reporter_id == params.reporter_id)
        if params.parent_task_id:
            filters.append(Task.parent_task_id == params.parent_task_id)
        
        # 日期范围过滤
        if params.planned_start_date_from:
            filters.append(Task.planned_start_date >= params.planned_start_date_from)
        if params.planned_start_date_to:
            filters.append(Task.planned_start_date <= params.planned_start_date_to)
        if params.planned_end_date_from:
            filters.append(Task.planned_end_date >= params.planned_end_date_from)
        if params.planned_end_date_to:
            filters.append(Task.planned_end_date <= params.planned_end_date_to)
        
        # 搜索过滤
        if params.search:
            search_term = f"%{params.search}%"
            filters.append(
                or_(
                    Task.task_name.ilike(search_term),
                    Task.task_code.ilike(search_term),
                    Task.description.ilike(search_term)
                )
            )
        
        # 应用权限过滤
        permission_filter = await self._build_task_permission_filter(user_id)
        if permission_filter is not None:
            filters.append(permission_filter)
        
        # 应用所有过滤条件
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # 排序
        sort_column = getattr(Task, params.sort_by, Task.updated_at)
        if params.sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # 分页
        offset = (params.page - 1) * params.size
        query = query.offset(offset).limit(params.size)
        
        # 执行查询
        result = await self.db.execute(query)
        tasks = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return list(tasks), total
    
    async def update_task(
        self, 
        task_id: int, 
        request: UpdateTaskRequest, 
        user_id: int
    ) -> Task:
        """
        更新任务
        
        Args:
            task_id: 任务ID
            request: 更新请求
            user_id: 用户ID
            
        Returns:
            更新后的任务对象
            
        Raises:
            NotFoundError: 任务不存在
            PermissionError: 权限不足
            ValidationError: 数据验证失败
        """
        # 1. 获取任务
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            raise NotFoundError(f"任务 {task_id} 不存在")
        
        # 2. 检查更新权限
        await self._validate_task_update_permission(task, user_id)
        
        # 3. 验证更新数据
        await self._validate_task_update_data(request, task)
        
        # 4. 记录原始数据用于审计
        original_data = task.to_dict()
        
        # 5. 更新任务字段
        update_fields = request.dict(exclude_unset=True)
        if update_fields.get("status") is None:
            update_fields.pop("status", None)
        for field, value in update_fields.items():
            if hasattr(task, field):
                setattr(task, field, value)
        
        # 6. 设置更新信息
        task.updated_by = user_id
        task.updated_at = datetime.utcnow()
        
        # 7. 处理状态变更的特殊逻辑
        if 'status' in update_fields:
            await self._handle_task_status_change(task, original_data['status'], request.status)
        
        # 8. 更新剩余工时
        if 'actual_hours' in update_fields or 'estimated_hours' in update_fields:
            await self._update_remaining_hours(task)
        
        # 9. 保存更改
        await self.db.commit()
        await self.db.refresh(task)
        
        # 10. 更新项目进度
        await self._update_project_progress(task.project_id)
        
        # 11. 通知数据同步服务
        await notify_project_change(
            SyncEventType.TASK_UPDATED,
            task.project_id,
            task.id,
            task.to_dict(),
            user_id
        )
        
        logger.info(f"任务更新成功: {task.task_code} - {task.task_name}")
        return task
    
    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            是否删除成功
            
        Raises:
            NotFoundError: 任务不存在
            PermissionError: 权限不足
            ValidationError: 不能删除
        """
        # 1. 获取任务
        task = await self.get_task_by_id(task_id, user_id)
        if not task:
            raise NotFoundError(f"任务 {task_id} 不存在")
        
        # 2. 检查删除权限
        await self._validate_task_delete_permission(task, user_id)
        
        # 3. 检查是否可以删除
        await self._validate_can_delete_task(task)
        
        # 4. 删除任务
        await self.db.delete(task)
        
        # 5. 更新项目任务计数
        await self._update_project_task_count(task.project_id)
        
        # 6. 保存更改
        await self.db.commit()
        
        # 7. 通知数据同步服务
        await notify_project_change(
            SyncEventType.TASK_DELETED,
            task.project_id,
            task.id,
            task.to_dict(),
            user_id
        )
        
        logger.info(f"任务删除成功: {task.task_code} - {task.task_name}")
        return True
    
    async def update_task_status(
        self, 
        task_id: int, 
        request: TaskStatusUpdateRequest, 
        user_id: int
    ) -> Task:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            request: 状态更新请求
            user_id: 用户ID
            
        Returns:
            更新后的任务对象
        """
        update_request = UpdateTaskRequest(status=request.status)
        return await self.update_task(task_id, update_request, user_id)
    
    async def assign_task(
        self, 
        task_id: int, 
        request: TaskAssignmentRequest, 
        user_id: int
    ) -> Task:
        """
        分配任务
        
        Args:
            task_id: 任务ID
            request: 分配请求
            user_id: 用户ID
            
        Returns:
            更新后的任务对象
        """
        assignee_ids = self._normalize_assignee_ids(request.assignee_id, request.assignee_ids)

        # 验证被分配人权限
        task = await self.get_task_by_id(task_id, user_id)
        if task:
            for assignee_id in assignee_ids:
                await self._validate_task_assignee(assignee_id, task.project_id)
        
        update_fields = {
            "assignee_id": assignee_ids[0] if assignee_ids else None,
            "assignee_ids": assignee_ids or None,
        }
        if task and task.status == TaskStatus.TODO:
            update_fields["status"] = TaskStatus.ASSIGNED

        update_request = UpdateTaskRequest(**update_fields)
        updated_task = await self.update_task(task_id, update_request, user_id)
        await self._send_task_assignment_notifications(updated_task, assignee_ids, user_id)
        return updated_task
    
    async def update_task_progress(
        self, 
        task_id: int, 
        request: TaskProgressUpdateRequest, 
        user_id: int
    ) -> Task:
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            request: 进度更新请求
            user_id: 用户ID
            
        Returns:
            更新后的任务对象
        """
        update_request = UpdateTaskRequest(
            actual_hours=request.actual_hours,
            remaining_hours=request.remaining_hours
        )
        return await self.update_task(task_id, update_request, user_id)
    
    async def set_task_dependencies(
        self, 
        task_id: int, 
        request: TaskDependencyRequest, 
        user_id: int
    ) -> Task:
        """
        设置任务依赖关系
        
        Args:
            task_id: 任务ID
            request: 依赖关系请求
            user_id: 用户ID
            
        Returns:
            更新后的任务对象
        """
        # 验证依赖关系
        task = await self.get_task_by_id(task_id, user_id)
        if task:
            await self.dependency_service.validate_dependencies(
                task_id, request.dependency_tasks, task.project_id
            )
        
        update_request = UpdateTaskRequest(dependency_tasks=request.dependency_tasks)
        return await self.update_task(task_id, update_request, user_id)
    
    async def get_task_statistics(self, project_id: int, user_id: int) -> TaskStatisticsResponse:
        """
        获取任务统计信息
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            
        Returns:
            任务统计信息
        """
        # 验证项目访问权限
        await self._validate_project_access(project_id, user_id)
        
        # 查询任务统计
        result = await self.db.execute(
            select(Task).where(Task.project_id == project_id)
        )
        tasks = result.scalars().all()
        
        # 计算统计信息
        total_tasks = len(tasks)
        tasks_by_status = {}
        tasks_by_type = {}
        tasks_by_priority = {}
        overdue_tasks = 0
        completed_on_time = 0
        completion_times = []
        
        for task in tasks:
            # 按状态统计
            status = task.status if task.status else 'UNKNOWN'
            tasks_by_status[status] = tasks_by_status.get(status, 0) + 1
            
            # 按类型统计
            task_type = task.task_type if task.task_type else 'UNKNOWN'
            tasks_by_type[task_type] = tasks_by_type.get(task_type, 0) + 1
            
            # 按优先级统计
            priority = task.priority if task.priority else 'UNKNOWN'
            tasks_by_priority[priority] = tasks_by_priority.get(priority, 0) + 1
            
            # 逾期任务统计
            if (task.planned_end_date and 
                task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED] and
                task.planned_end_date < date.today()):
                overdue_tasks += 1
            
            # 按时完成统计
            if (task.status == TaskStatus.COMPLETED and 
                task.actual_end_date and task.planned_end_date and
                task.actual_end_date <= task.planned_end_date):
                completed_on_time += 1
                
                # 计算完成时间
                if task.actual_start_date:
                    completion_time = (task.actual_end_date - task.actual_start_date).days
                    completion_times.append(completion_time)
        
        # 计算平均完成时间
        average_completion_time = None
        if completion_times:
            average_completion_time = sum(completion_times) / len(completion_times)
        
        return TaskStatisticsResponse(
            project_id=project_id,
            total_tasks=total_tasks,
            tasks_by_status=tasks_by_status,
            tasks_by_type=tasks_by_type,
            tasks_by_priority=tasks_by_priority,
            overdue_tasks=overdue_tasks,
            completed_on_time=completed_on_time,
            average_completion_time=average_completion_time
        )
    
    # 私有方法
    async def _validate_project_access(self, project_id: int, user_id: int) -> Project:
        """验证项目访问权限"""
        result = await self.db.execute(
            select(Project).where(
                and_(Project.id == project_id, Project.deleted_at.is_(None))
            )
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")
        
        # 超级用户绕过项目成员/经理校验，与 project_service 行为一致
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.is_superuser:
            return project

        # 检查是否是项目成员或项目经理
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
        
        if not member and project.project_manager_id != user_id:
            raise PermissionError("没有访问该项目的权限")
        
        return project
    
    async def _validate_task_data(self, request: CreateTaskRequest):
        """验证任务数据"""
        # 验证日期逻辑
        if (request.planned_end_date and request.planned_start_date and 
            request.planned_end_date <= request.planned_start_date):
            raise ValidationError("计划结束日期必须晚于计划开始日期")
        
        # 验证工时
        if request.estimated_hours is not None and request.estimated_hours < 0:
            raise ValidationError("预估工时不能为负数")

    def _normalize_assignee_ids(self, assignee_id: Optional[int], assignee_ids: Optional[List[int]]) -> List[int]:
        """合并单人和多人执行人字段，保留顺序并去重"""
        normalized: List[int] = []
        if assignee_ids:
            normalized.extend(int(item) for item in assignee_ids if item)
        if assignee_id:
            normalized.insert(0, int(assignee_id))

        result: List[int] = []
        for item in normalized:
            if item not in result:
                result.append(item)
        return result

    async def _send_task_assignment_notifications(self, task: Task, assignee_ids: List[int], sender_id: int) -> None:
        """Create unread in-app notifications for task assignees."""
        if not assignee_ids:
            return

        try:
            project_name_result = await self.db.execute(
                select(Project.project_name).where(Project.id == task.project_id)
            )
            project_name = project_name_result.scalar_one_or_none() or f"项目#{task.project_id}"
            service = SystemNotificationService(self.db)
            await service.create_notifications(
                assignee_ids,
                title="你有新的任务分配",
                content=f"任务“{task.task_name}”已分配给你，所属项目：{project_name}。",
                category="task_assignment",
                sender_id=sender_id,
                related_type="task",
                related_id=task.id,
                payload={
                    "task_id": task.id,
                    "task_name": task.task_name,
                    "task_code": task.task_code,
                    "project_id": task.project_id,
                    "project_name": project_name,
                },
            )
        except Exception as exc:
            await self.db.rollback()
            logger.warning(f"创建任务分配通知失败: {exc}")
    
    async def _validate_task_dependencies(self, dependency_tasks: List[int], project_id: int, exclude_task_id: Optional[int] = None):
        """验证任务依赖关系（简化版，用于新任务创建）"""
        if not dependency_tasks:
            return
        
        # 检查依赖任务是否存在且属于同一项目
        result = await self.db.execute(
            select(Task).where(
                and_(
                    Task.id.in_(dependency_tasks),
                    Task.project_id == project_id
                )
            )
        )
        existing_tasks = result.scalars().all()
        
        if len(existing_tasks) != len(dependency_tasks):
            raise ValidationError("部分依赖任务不存在或不属于同一项目")
        
        # 检查循环依赖
        if exclude_task_id and exclude_task_id in dependency_tasks:
            raise ValidationError("任务不能依赖自己")
    
    async def _validate_task_assignee(self, assignee_id: int, project_id: int):
        """验证任务执行人"""
        # 检查用户是否存在
        result = await self.db.execute(
            select(User).where(User.id == assignee_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValidationError(f"用户 {assignee_id} 不存在")
        
        if getattr(user, "is_active", True) is False:
            raise ValidationError(f"用户 {assignee_id} 已停用，不能分配任务")
    
    async def _generate_task_code(self, project_id: int) -> str:
        """生成任务编码"""
        # 获取项目编码
        result = await self.db.execute(
            select(Project.project_code).where(Project.id == project_id)
        )
        project_code = result.scalar()
        
        # 查询项目下的任务数量
        result = await self.db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
        count = result.scalar() or 0
        
        # 生成任务编码
        return f"{project_code}-T{count + 1:03d}"
    
    async def _validate_task_access(self, task: Task, user_id: int):
        """验证任务访问权限"""
        await self._validate_project_access(task.project_id, user_id)
    
    async def _build_task_permission_filter(self, user_id: int):
        """构建任务权限过滤条件"""
        # 超级用户可查看所有任务，与项目访问校验行为一致
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.is_superuser:
            return None

        # 用户可以查看自己参与项目的任务
        subquery = select(ProjectMember.project_id).where(
            and_(
                ProjectMember.user_id == user_id,
                ProjectMember.status == "ACTIVE"
            )
        )
        
        return or_(
            Task.project_id.in_(subquery),
            Task.assignee_id == user_id,
            Task.reporter_id == user_id
        )
    
    async def _validate_task_update_permission(self, task: Task, user_id: int):
        """验证任务更新权限"""
        # 项目经理、任务执行人、报告人可以更新任务
        project = await self._validate_project_access(task.project_id, user_id)
        
        # 超级用户绕过细化权限校验
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.is_superuser:
            return

        if (project.project_manager_id != user_id and 
            task.assignee_id != user_id and 
            task.reporter_id != user_id):
            raise PermissionError("没有更新该任务的权限")
    
    async def _validate_task_update_data(self, request: UpdateTaskRequest, task: Task):
        """验证任务更新数据"""
        # 验证日期逻辑
        start_date = request.planned_start_date or task.planned_start_date
        end_date = request.planned_end_date or task.planned_end_date
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("计划结束日期必须晚于计划开始日期")

        assignee_ids = self._normalize_assignee_ids(request.assignee_id, request.assignee_ids)
        for assignee_id in assignee_ids:
            await self._validate_task_assignee(assignee_id, task.project_id)
    
    async def _handle_task_status_change(self, task: Task, old_status: str, new_status: str):
        """处理任务状态变更的特殊逻辑"""
        if old_status == new_status:
            return
        
        # 设置实际开始时间
        if new_status == TaskStatus.IN_PROGRESS and not task.actual_start_date:
            task.actual_start_date = date.today()
        
        # 设置实际结束时间
        if new_status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED] and not task.actual_end_date:
            task.actual_end_date = date.today()
    
    async def _update_remaining_hours(self, task: Task):
        """更新剩余工时"""
        if task.estimated_hours and task.actual_hours:
            task.remaining_hours = max(task.estimated_hours - task.actual_hours, Decimal('0'))
    
    async def _update_project_task_count(self, project_id: int):
        """更新项目任务计数"""
        # 查询项目任务总数
        total_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
        total = total_result.scalar()
        
        # 查询已完成任务数
        completed_result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(Task.project_id == project_id, Task.status == TaskStatus.COMPLETED)
            )
        )
        completed = completed_result.scalar()
        
        # 更新项目统计
        await self.db.execute(
            text("UPDATE projects SET task_count = :total, completed_task_count = :completed WHERE id = :project_id"),
            {"total": total, "completed": completed, "project_id": project_id}
        )
    
    async def _update_project_progress(self, project_id: int):
        """更新项目进度"""
        # 查询项目任务总数
        total_result = await self.db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
        total = total_result.scalar()
        
        if total > 0:
            # 查询已完成任务数
            completed_result = await self.db.execute(
                select(func.count(Task.id)).where(
                    and_(Task.project_id == project_id, Task.status == TaskStatus.COMPLETED)
                )
            )
            completed = completed_result.scalar()
            
            # 计算进度
            progress = (completed / total) * 100
            await self.db.execute(
                text("UPDATE projects SET progress_percentage = :progress WHERE id = :project_id"),
                {"progress": progress, "project_id": project_id}
            )
    
    async def _validate_task_delete_permission(self, task: Task, user_id: int):
        """验证任务删除权限"""
        # 只有项目经理和任务创建者可以删除任务
        project = await self._validate_project_access(task.project_id, user_id)
        
        # 超级用户绕过细化权限校验
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.is_superuser:
            return

        if project.project_manager_id != user_id and task.created_by != user_id:
            raise PermissionError("只有项目经理和任务创建者可以删除任务")
    
    async def _validate_can_delete_task(self, task: Task):
        """验证是否可以删除任务"""
        # 检查任务状态
        if task.status == TaskStatus.IN_PROGRESS:
            raise ValidationError("进行中的任务不能删除，请先暂停或完成任务")
        
        # 检查是否有子任务
        result = await self.db.execute(
            select(func.count(Task.id)).where(Task.parent_task_id == task.id)
        )
        child_count = result.scalar()
        
        if child_count > 0:
            raise ValidationError("有子任务的任务不能删除，请先删除子任务")


# 依赖注入函数
async def get_task_service(db: AsyncSession = Depends(get_async_session)):
    """获取任务服务实例"""
    if db is None:
        async with get_async_session_ctx() as session:
            return TaskService(session)
    return TaskService(db)
