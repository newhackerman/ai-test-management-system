"""
会议与项目管理模块集成服务

提供会议与项目管理系统的集成功能，包括：
- 项目会议关联管理
- 项目权限继承
- 会议任务创建
- 项目成员自动邀请
"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ..models.meeting import Meeting, MeetingParticipant, MeetingTask, ParticipantRole, InvitationStatus
from ..models.project import Project, ProjectMember, Task, Milestone
from ..models.user import User
from ..core.exceptions import ValidationError, PermissionError, NotFoundError

# 任务类型 / 状态取值的白名单（与 Task 模型的 Enum 列一致）
VALID_TASK_TYPES = frozenset({
    "REQUIREMENT_ANALYSIS", "TEST_DESIGN", "TEST_EXECUTION",
    "AUTOMATION_DEVELOPMENT", "PERFORMANCE_TEST", "SECURITY_TEST",
    "ENVIRONMENT_SETUP", "DOCUMENTATION",
})
VALID_TASK_STATUSES = frozenset({
    "TODO", "ASSIGNED", "IN_PROGRESS", "ON_HOLD", "BLOCKED",
    "PENDING_REVIEW", "COMPLETED", "CANCELLED",
})


class MeetingProjectIntegrationService:
    """会议项目集成服务"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def _get_meeting_or_404(self, meeting_id: int) -> Meeting:
        """取会议，不存在或已软删除时抛 NotFoundError（路由层转 404）。"""
        meeting = await self.db_session.get(Meeting, meeting_id)
        if not meeting or meeting.deleted_at is not None:
            raise NotFoundError(f"会议不存在: {meeting_id}")
        return meeting

    async def _get_task_or_404(self, task_id: int) -> Task:
        """取任务，不存在时抛 NotFoundError（路由层转 404）。"""
        task = await self.db_session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"任务不存在: {task_id}")
        return task

    async def _require_meeting_access(self, meeting: Meeting, user_id: int) -> None:
        """会议访问权限：超管放行；否则须是会议组织者或所属项目的
        ACTIVE 成员，否则抛 PermissionError（路由层转 403）。"""
        user = await self.db_session.get(User, user_id)
        if user is not None and getattr(user, "is_superuser", False):
            return
        if meeting.organizer_id == user_id:
            return
        if meeting.project_id:
            member_query = select(ProjectMember).where(and_(
                ProjectMember.project_id == meeting.project_id,
                ProjectMember.user_id == user_id,
                ProjectMember.status == "ACTIVE",
            ))
            member_result = await self.db_session.execute(member_query)
            if member_result.scalar_one_or_none() is not None:
                return
        raise PermissionError("没有访问该会议的权限")

    async def _generate_task_code(self, project_id: int) -> str:
        """生成任务编码（与 TaskService._generate_task_code 同规则：
        {project_code}-T{count+1:03d}）。"""
        result = await self.db_session.execute(
            select(Project.project_code).where(Project.id == project_id)
        )
        project_code = result.scalar()
        result = await self.db_session.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
        count = result.scalar() or 0
        return f"{project_code}-T{count + 1:03d}"

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """把配置里的 ISO 字符串解析为 datetime；已是 datetime 则原样返回。"""
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        return None

    async def get_project_meetings(
        self,
        project_id: int,
        user_id: Optional[int] = None,
        meeting_type: Optional[str] = None,
        status: Optional[str] = None,
        date_range=None
    ) -> List[Meeting]:
        """获取项目相关的会议列表（支持按用户/类型/状态/日期范围过滤）。"""
        from sqlalchemy.orm import selectinload
        query = select(Meeting).options(selectinload(Meeting.project)).where(Meeting.project_id == project_id)
        if meeting_type is not None:
            query = query.where(Meeting.meeting_type == meeting_type)
        if status is not None:
            query = query.where(Meeting.status == status)
        if date_range:
            # 兼容 tuple/list 形式 (start, end) 或 dict 形式
            if isinstance(date_range, dict):
                start = date_range.get("start") or date_range.get("start_date")
                end = date_range.get("end") or date_range.get("end_date")
            elif isinstance(date_range, (tuple, list)) and len(date_range) >= 2:
                start, end = date_range[0], date_range[1]
            else:
                start = end = None
            if start:
                query = query.where(Meeting.scheduled_start_time >= start)
            if end:
                query = query.where(Meeting.scheduled_start_time <= end)
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def create_project_meeting(
        self,
        project_id: int,
        meeting_data: Dict[str, Any],
        creator_id: int,
        auto_invite_team: bool = True,
    ) -> Meeting:
        """为项目创建会议。

        路由曾调用本方法但服务类中并不存在（AttributeError -> 500），
        导致 POST /projects/{id}/meetings 整体不可用。实现委托给
        已有的 MeetingService.create_meeting（负责校验、生成会议
        编码与创建会议实体），再按需自动邀请项目成员。
        """
        from ..services.meeting_service import MeetingService

        project = await self.db_session.get(Project, project_id)
        if not project:
            raise NotFoundError("项目不存在")

        data = {**meeting_data, "project_id": project_id}
        meeting_service = MeetingService(self.db_session)
        meeting = await meeting_service.create_meeting(data, creator_id)

        if auto_invite_team:
            await self.auto_invite_project_members(
                meeting.id, project_id, creator_id
            )
            await self.db_session.flush()

        return meeting

    async def sync_project_team_to_meeting(
        self,
        meeting_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """同步项目团队成员到会议。

        会议不存在抛 NotFoundError；会议未关联项目抛 ValidationError；
        调用者须有会议访问权限（组织者 / 项目成员 / 超管）。
        幂等：已是参与者的成员不再重复邀请。
        返回 TeamSyncResult 所需的三个计数字段。
        """
        meeting = await self._get_meeting_or_404(meeting_id)
        await self._require_meeting_access(meeting, user_id)
        if not meeting.project_id:
            raise ValidationError("会议未关联项目")

        total_result = await self.db_session.execute(
            select(func.count(ProjectMember.id)).where(
                ProjectMember.project_id == meeting.project_id
            )
        )
        total_project_members = total_result.scalar() or 0

        existing_result = await self.db_session.execute(
            select(func.count(MeetingParticipant.id)).where(
                MeetingParticipant.meeting_id == meeting_id
            )
        )
        existing_participants = existing_result.scalar() or 0

        added = await self.auto_invite_project_members(
            meeting.id, meeting.project_id, meeting.organizer_id
        )

        return {
            "total_project_members": total_project_members,
            "existing_participants": existing_participants,
            "added_participants": len(added),
        }

    async def create_milestone_review_meeting(
        self,
        milestone_id: int,
        creator_id: int,
        meeting_config: Optional[Dict[str, Any]] = None,
    ) -> Meeting:
        """为里程碑创建评审会议。

        里程碑不存在抛 NotFoundError。会议默认取里程碑名 + “评审会议”
        作标题、里程碑计划日期 10:00 作开始时间、时长 1 小时、
        类型 PROGRESS_SYNC（会议类型枚举无里程碑评审专属值）；
        meeting_config 可覆盖 title / meeting_type /
        scheduled_start_time / scheduled_end_time / description /
        max_participants / auto_invite_team 等字段。
        创建委托给 create_project_meeting（复用 MeetingService 的
        校验、编码生成与自动邀请逻辑）。
        """
        milestone = await self.db_session.get(Milestone, milestone_id)
        if not milestone or milestone.deleted_at is not None:
            raise NotFoundError(f"里程碑不存在: {milestone_id}")

        config = meeting_config or {}
        start = self._parse_datetime(config.get("scheduled_start_time"))
        if start is None:
            start = datetime.combine(milestone.planned_date, time(10, 0))
        end = self._parse_datetime(config.get("scheduled_end_time"))
        if end is None:
            end = start + timedelta(hours=1)

        meeting_data = {
            "title": config.get("title") or f"{milestone.milestone_name}评审会议",
            "description": config.get("description", milestone.description),
            "meeting_type": config.get("meeting_type") or "PROGRESS_SYNC",
            "scheduled_start_time": start,
            "scheduled_end_time": end,
            "max_participants": config.get("max_participants", 100),
            "is_recording_enabled": config.get("is_recording_enabled", False),
            "is_waiting_room_enabled": config.get("is_waiting_room_enabled", True),
            "agenda": config.get("agenda"),
            "meeting_settings": config.get("meeting_settings", {}),
        }
        return await self.create_project_meeting(
            milestone.project_id,
            meeting_data,
            creator_id,
            config.get("auto_invite_team", True),
        )

    async def link_meeting_decisions_to_tasks(
        self,
        meeting_id: int,
        decisions: List[Dict[str, Any]],
        user_id: int,
    ) -> List[int]:
        """将会议决策转换为项目任务。

        仅处理 create_task 为真的决策；每条决策按 Task 模型的真实列
        建任务（task_name / task_type / priority / status / assignee_id /
        reporter_id / planned_start_date / planned_end_date /
        estimated_hours / acceptance_criteria / created_by），并在
        meeting_tasks 表中登记会议-任务关联。任务编码与
        TaskService 同规则。返回新建任务的 id 列表。
        """
        meeting = await self._get_meeting_or_404(meeting_id)
        await self._require_meeting_access(meeting, user_id)
        if not meeting.project_id:
            raise ValidationError("会议未关联项目")

        created_task_ids: List[int] = []
        for decision in decisions or []:
            if not decision.get("create_task"):
                continue
            title = (decision.get("title") or "").strip()
            if not title:
                raise ValidationError("决策标题不能为空")
            task_type = decision.get("task_type") or "REQUIREMENT_ANALYSIS"
            if task_type not in VALID_TASK_TYPES:
                raise ValidationError(f"无效的任务类型: {task_type}")
            priority = str(decision.get("priority") or "MEDIUM").upper()
            if priority not in ("LOW", "MEDIUM", "HIGH", "URGENT"):
                priority = "MEDIUM"
            assignee_id = decision.get("assignee_id")
            if assignee_id is not None:
                assignee = await self.db_session.get(User, assignee_id)
                if not assignee:
                    raise ValidationError(f"指定的负责人不存在: {assignee_id}")

            task = Task(
                project_id=meeting.project_id,
                task_code=await self._generate_task_code(meeting.project_id),
                task_name=title,
                description=decision.get("description"),
                task_type=task_type,
                priority=priority,
                status="TODO",
                assignee_id=assignee_id,
                reporter_id=user_id,
                planned_start_date=decision.get("start_date"),
                planned_end_date=decision.get("due_date"),
                estimated_hours=decision.get("estimated_hours"),
                acceptance_criteria=decision.get("acceptance_criteria"),
                created_by=user_id,
            )
            self.db_session.add(task)
            await self.db_session.flush()
            self.db_session.add(MeetingTask(
                meeting_id=meeting_id,
                task_id=task.id,
                linked_by=user_id,
            ))
            created_task_ids.append(task.id)

        await self.db_session.flush()
        return created_task_ids

    async def sync_meeting_tasks_with_project(
        self,
        meeting_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """同步会议任务与项目任务系统。

        校验会议已关联的全部任务：逐个确认任务存在且属于该会议所属
        项目；项目不一致的任务迁回该项目（计数为 moved_tasks）。
        关联关系以 meeting_tasks 表为准。返回 linked_tasks 等计数。
        """
        meeting = await self._get_meeting_or_404(meeting_id)
        await self._require_meeting_access(meeting, user_id)
        if not meeting.project_id:
            raise ValidationError("会议未关联项目")

        link_result = await self.db_session.execute(
            select(MeetingTask).where(MeetingTask.meeting_id == meeting_id)
        )
        links = link_result.scalars().all()

        linked_tasks = 0
        moved_tasks = 0
        for link in links:
            task = await self.db_session.get(Task, link.task_id)
            if task is None:
                continue
            linked_tasks += 1
            if task.project_id != meeting.project_id:
                task.project_id = meeting.project_id
                task.updated_by = user_id
                moved_tasks += 1

        await self.db_session.flush()
        return {
            "meeting_id": meeting_id,
            "project_id": meeting.project_id,
            "linked_tasks": linked_tasks,
            "synced_tasks": linked_tasks,
            "moved_tasks": moved_tasks,
        }

    async def link_existing_task_to_meeting(
        self,
        meeting_id: int,
        task_id: int,
        user_id: int,
    ) -> Task:
        """将现有任务关联到会议。

        任务须存在且属于该会议所属项目（会议未关联项目时不校验归属）；
        已关联时直接返回任务（幂等，不重复建关联行）。
        """
        meeting = await self._get_meeting_or_404(meeting_id)
        await self._require_meeting_access(meeting, user_id)
        task = await self._get_task_or_404(task_id)
        if meeting.project_id and task.project_id != meeting.project_id:
            raise ValidationError("任务不属于该会议所属项目")

        existing_result = await self.db_session.execute(
            select(MeetingTask).where(and_(
                MeetingTask.meeting_id == meeting_id,
                MeetingTask.task_id == task_id,
            ))
        )
        if existing_result.scalar_one_or_none() is None:
            self.db_session.add(MeetingTask(
                meeting_id=meeting_id,
                task_id=task_id,
                linked_by=user_id,
            ))
            await self.db_session.flush()
        return task

    async def update_task_from_meeting_progress(
        self,
        meeting_id: int,
        task_updates: List[Dict[str, Any]],
        user_id: int,
    ) -> List[Task]:
        """根据会议进展更新任务状态。

        每条更新须含 task_id（或 id）且任务已关联到该会议；
        可更新 status（须为 Task 状态枚举值）与 actual_hours；
        未显式给 status 但给了 progress_percentage 时按进度推导状态
       （100 → COMPLETED，>0 → IN_PROGRESS，0 → TODO）。
        Task 模型没有 progress_percentage 列，进度只用于推导状态，
        不做存储。
        """
        meeting = await self._get_meeting_or_404(meeting_id)
        await self._require_meeting_access(meeting, user_id)

        updated_tasks: List[Task] = []
        for item in task_updates or []:
            task_id = item.get("task_id") or item.get("id")
            if not task_id:
                raise ValidationError("任务更新缺少 task_id")
            task = await self._get_task_or_404(task_id)
            link_result = await self.db_session.execute(
                select(MeetingTask).where(and_(
                    MeetingTask.meeting_id == meeting_id,
                    MeetingTask.task_id == task_id,
                ))
            )
            if link_result.scalar_one_or_none() is None:
                raise ValidationError(f"任务 {task_id} 未关联到该会议")

            if item.get("status") is not None:
                status = str(item["status"]).upper()
                if status not in VALID_TASK_STATUSES:
                    raise ValidationError(f"无效的任务状态: {item['status']}")
                task.status = status
            elif item.get("progress_percentage") is not None:
                progress = item["progress_percentage"]
                if progress >= 100:
                    task.status = "COMPLETED"
                elif progress > 0:
                    task.status = "IN_PROGRESS"
                else:
                    task.status = "TODO"
            if item.get("actual_hours") is not None:
                task.actual_hours = item["actual_hours"]
            task.updated_by = user_id
            updated_tasks.append(task)

        await self.db_session.flush()
        return updated_tasks

    async def generate_project_meeting_schedule(
        self,
        project_id: int,
        user_id: Optional[int] = None,
        schedule_config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成项目会议计划（返回建议的会议计划项列表）。

        返回的字典键需与 MeetingScheduleItem 模型字段匹配：
        type, title, scheduled_date, duration, priority, auto_create, recurring。
        """
        config = schedule_config or {}
        meeting_types = config.get("meeting_types") or [
            "PROJECT_KICKOFF", "REQUIREMENT_REVIEW", "DESIGN_REVIEW",
            "CODE_REVIEW", "TEST_REVIEW", "PROGRESS_SYNC", "PROJECT_SUMMARY"
        ]
        schedule: List[Dict[str, Any]] = []
        # 以当前日期为基准，为每个计划项分配一个具体日期（依次顺延一天），
        # 以满足响应模型 MeetingScheduleItem.scheduled_date 的非空约束。
        base_date = date.today()
        for index, meeting_type in enumerate(meeting_types):
            schedule.append({
                "type": meeting_type,
                "title": f"{meeting_type} 会议",
                "scheduled_date": base_date + timedelta(days=index),
                "duration": 60,
                "priority": "medium",
                "auto_create": False,
                "recurring": False,
            })
        return schedule
    
    async def auto_invite_project_members(
        self,
        meeting_id: int,
        project_id: int,
        organizer_id: int
    ) -> List[MeetingParticipant]:
        """自动邀请项目成员参加会议。

        注意旧实现与真实模型不符（访问了不存在的 member.role /
        member.permissions 属性、向 MeetingParticipant 传了不存在的
        role 参数、用小写字符串作 invitation_status），且项目已有
        其他成员时必定崩溃；此处按真实列名修正：角色取
        role_in_project（英文编码），可共享屏幕按角色判定，已是
        参与者的成员跳过（meeting_participants 有唯一约束）。
        """
        # 获取项目成员
        members_query = select(ProjectMember).where(
            ProjectMember.project_id == project_id
        )
        members_result = await self.db_session.execute(members_query)
        project_members = members_result.scalars().all()

        # 已是参与者的成员不再重复邀请
        existing_query = select(MeetingParticipant.user_id).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        existing_result = await self.db_session.execute(existing_query)
        existing_user_ids = set(existing_result.scalars().all())

        participants = []
        for member in project_members:
            # 跳过组织者（已经是会议创建者）与已邀请的成员
            if member.user_id == organizer_id or member.user_id in existing_user_ids:
                continue

            participant = MeetingParticipant(
                meeting_id=meeting_id,
                user_id=member.user_id,
                participant_role=self._map_project_role_to_meeting_role(member.role_in_project),
                can_share_screen=member.role_in_project in ("PROJECT_MANAGER", "ARCHITECT"),
                can_use_chat=True,
                invitation_status=InvitationStatus.PENDING,
                invited_at=datetime.now()
            )

            self.db_session.add(participant)
            participants.append(participant)

        await self.db_session.flush()
        return participants

    def _map_project_role_to_meeting_role(self, project_role: str) -> ParticipantRole:
        """将项目角色（role_in_project 英文编码）映射到会议角色。

        旧实现按中文角色名（'项目经理' 等）映射且返回小写字符串，
        与 ParticipantRole 枚举（ORGANIZER / MODERATOR / PRESENTER /
        PARTICIPANT / OBSERVER）完全对不上；此处按真实枚举修正。
        """
        role_mapping = {
            'PROJECT_MANAGER': ParticipantRole.MODERATOR,
            'ARCHITECT': ParticipantRole.PRESENTER,
            'DESIGNER': ParticipantRole.PRESENTER,
            'REQUIREMENT_MANAGER': ParticipantRole.PRESENTER,
        }

        return role_mapping.get((project_role or "").upper(), ParticipantRole.PARTICIPANT)
    
    async def check_project_meeting_permission(
        self,
        user_id: int,
        meeting_id: int,
        permission: str
    ) -> bool:
        """检查用户在项目会议中的权限"""
        # 获取会议信息
        meeting_query = select(Meeting).where(Meeting.id == meeting_id)
        meeting_result = await self.db_session.execute(meeting_query)
        meeting = meeting_result.scalar_one_or_none()
        
        if not meeting or not meeting.project_id:
            return False
        
        # 检查用户是否是项目成员
        member_query = select(ProjectMember).where(
            and_(
                ProjectMember.project_id == meeting.project_id,
                ProjectMember.user_id == user_id
            )
        )
        member_result = await self.db_session.execute(member_query)
        project_member = member_result.scalar_one_or_none()
        
        if not project_member:
            return False
        
        # 根据权限类型检查
        permission_mapping = {
            'join_meeting': ['view_project'],
            'manage_meeting': ['manage_project', 'manage_meetings'],
            'share_screen': ['manage_meetings'],
            'record_meeting': ['manage_meetings'],
            'invite_participants': ['manage_meetings']
        }
        
        required_permissions = permission_mapping.get(permission, [])
        return any(perm in project_member.permissions for perm in required_permissions)

    async def get_meeting_related_tasks(
        self,
        meeting_id: int,
        user_id: Optional[int] = None
    ) -> List[Task]:
        """获取会议相关的任务列表。

        关联关系以 meeting_tasks 表为准（Task 模型本身没有
        meeting_id 列）。会议不存在时抛出 NotFoundError（由路由层
        转为 404）。
        """
        # 验证会议存在
        meeting_query = select(Meeting).where(Meeting.id == meeting_id)
        meeting_result = await self.db_session.execute(meeting_query)
        meeting = meeting_result.scalar_one_or_none()

        if not meeting:
            raise NotFoundError(f"会议不存在: {meeting_id}")

        # 访问权限：组织者 / 项目成员 / 超管（与 6 个写方法同规则；
        # user_id 为 None 时跳过校验，保持内部调用兼容）
        if user_id is not None:
            await self._require_meeting_access(meeting, user_id)

        link_query = select(MeetingTask.task_id).where(
            MeetingTask.meeting_id == meeting_id
        ).order_by(MeetingTask.id)
        link_result = await self.db_session.execute(link_query)
        task_ids = link_result.scalars().all()
        if not task_ids:
            return []

        task_query = select(Task).where(Task.id.in_(task_ids)).order_by(Task.id)
        task_result = await self.db_session.execute(task_query)
        return list(task_result.scalars().all())

    async def get_meeting_task_progress_summary(
        self,
        meeting_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取会议任务进度摘要。

        会议不存在时抛出 NotFoundError（由路由层转为 404）；
        会议存在但无关联任务时返回全零的进度摘要。
        """
        # 复用任务列表查询，其中会校验会议存在并抛出 NotFoundError
        tasks = await self.get_meeting_related_tasks(meeting_id, user_id)

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if getattr(t, 'status', None) == 'COMPLETED'])
        in_progress_tasks = len([t for t in tasks if getattr(t, 'status', None) == 'IN_PROGRESS'])
        pending_tasks = len([t for t in tasks if getattr(t, 'status', None) in ('TODO', 'ASSIGNED')])
        blocked_tasks = len([t for t in tasks if getattr(t, 'status', None) == 'BLOCKED'])

        overall_progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

        return {
            'meeting_id': meeting_id,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'pending_tasks': pending_tasks,
            'blocked_tasks': blocked_tasks,
            'overall_progress': round(overall_progress, 2),
        }
