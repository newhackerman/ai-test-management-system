"""
会议与项目管理模块集成服务

提供会议与项目管理系统的集成功能，包括：
- 项目会议关联管理
- 项目权限继承
- 会议任务创建
- 项目成员自动邀请
"""
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models.meeting import Meeting, MeetingParticipant
from ..models.project import Project, ProjectMember, Task
from ..models.user import User
from ..core.exceptions import ValidationError, PermissionError, NotFoundError


class MeetingProjectIntegrationService:
    """会议项目集成服务"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
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
    
    async def create_tasks_from_meeting(
        self,
        meeting_id: int,
        action_items: List[Dict[str, Any]],
        creator_id: int
    ) -> List[Task]:
        """从会议行动项目创建项目任务"""
        # 获取会议信息
        meeting_query = select(Meeting).where(Meeting.id == meeting_id)
        meeting_result = await self.db_session.execute(meeting_query)
        meeting = meeting_result.scalar_one_or_none()
        
        if not meeting:
            raise ValidationError("会议不存在")
        
        if not meeting.project_id:
            raise ValidationError("会议未关联项目")
        
        tasks = []
        for item in action_items:
            task = Task(
                title=item['title'],
                description=item.get('description', ''),
                project_id=meeting.project_id,
                meeting_id=meeting_id,
                assignee_id=item.get('assignee_id'),
                creator_id=creator_id,
                due_date=item.get('due_date'),
                priority=item.get('priority', 'medium'),
                status='todo',
                created_at=datetime.now()
            )
            
            self.db_session.add(task)
            tasks.append(task)
        
        await self.db_session.flush()
        return tasks
    
    async def auto_invite_project_members(
        self,
        meeting_id: int,
        project_id: int,
        organizer_id: int
    ) -> List[MeetingParticipant]:
        """自动邀请项目成员参加会议"""
        # 获取项目成员
        members_query = select(ProjectMember).where(
            ProjectMember.project_id == project_id
        )
        members_result = await self.db_session.execute(members_query)
        project_members = members_result.scalars().all()
        
        participants = []
        for member in project_members:
            # 跳过组织者（已经是会议创建者）
            if member.user_id == organizer_id:
                continue
            
            # 根据项目角色确定会议权限
            meeting_role = self._map_project_role_to_meeting_role(member.role)
            can_share_screen = 'manage_meetings' in member.permissions
            can_use_chat = True
            
            participant = MeetingParticipant(
                meeting_id=meeting_id,
                user_id=member.user_id,
                role=meeting_role,
                can_share_screen=can_share_screen,
                can_use_chat=can_use_chat,
                invitation_status='pending',
                invited_at=datetime.now()
            )
            
            self.db_session.add(participant)
            participants.append(participant)
        
        await self.db_session.flush()
        return participants
    
    def _map_project_role_to_meeting_role(self, project_role: str) -> str:
        """将项目角色映射到会议角色"""
        role_mapping = {
            '项目经理': 'moderator',
            '技术负责人': 'presenter',
            '开发人员': 'attendee',
            '测试人员': 'attendee',
            '产品经理': 'presenter',
            '设计师': 'presenter'
        }
        
        return role_mapping.get(project_role, 'attendee')
    
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

        Task 模型当前没有 meeting_id 列，因此无关联任务时返回空列表。
        会议不存在时抛出 NotFoundError（由路由层转为 404）。
        """
        # 验证会议存在
        meeting_query = select(Meeting).where(Meeting.id == meeting_id)
        meeting_result = await self.db_session.execute(meeting_query)
        meeting = meeting_result.scalar_one_or_none()

        if not meeting:
            raise NotFoundError(f"会议不存在: {meeting_id}")

        # Task 模型暂无 meeting_id 关联，返回空列表
        return []

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
