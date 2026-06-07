"""
会议与项目管理模块集成服务

提供会议与项目管理系统的集成功能，包括：
- 项目会议关联管理
- 项目权限继承
- 会议任务创建
- 项目成员自动邀请
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models.meeting import Meeting, MeetingParticipant
from ..models.project import Project, ProjectMember, Task
from ..models.user import User
from ..core.exceptions import ValidationError, PermissionError


class MeetingProjectIntegrationService:
    """会议项目集成服务"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def get_project_meetings(self, project_id: int) -> List[Meeting]:
        """获取项目相关的会议列表"""
        query = select(Meeting).where(Meeting.project_id == project_id)
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
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
