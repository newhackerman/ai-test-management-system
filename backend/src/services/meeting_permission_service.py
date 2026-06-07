"""
会议权限管理服务

本模块提供会议相关的权限管理功能，包括：
- 会议权限与RBAC角色的映射
- 细粒度的会议功能权限控制
- 动态权限分配和管理
- 权限继承和覆盖
"""
import logging
import json
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.user import User
from ..models.meeting import Meeting
from ..models.meeting_participant import MeetingParticipant
from ..models.role import Role
from ..models.user_role import UserRole
from ..models.permission import Permission
from ..models.role_permission import RolePermission
from ..services.permission_service import PermissionService
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# 会议权限映射配置
MEETING_PERMISSIONS = {
    # 基础权限
    "meeting.view": {
        "name": "查看会议",
        "description": "查看会议基本信息和详情",
        "module": "meeting",
        "category": "basic"
    },
    "meeting.create": {
        "name": "创建会议",
        "description": "创建新的会议",
        "module": "meeting",
        "category": "basic"
    },
    "meeting.update": {
        "name": "更新会议",
        "description": "修改会议信息和设置",
        "module": "meeting",
        "category": "basic"
    },
    "meeting.delete": {
        "name": "删除会议",
        "description": "删除会议",
        "module": "meeting",
        "category": "basic"
    },
    
    # 参与权限
    "meeting.join": {
        "name": "加入会议",
        "description": "加入会议房间",
        "module": "meeting",
        "category": "participation"
    },
    "meeting.leave": {
        "name": "离开会议",
        "description": "离开会议房间",
        "module": "meeting",
        "category": "participation"
    },
    
    # 参与者管理权限
    "meeting.manage_participants": {
        "name": "管理参与者",
        "description": "添加、移除、管理会议参与者",
        "module": "meeting",
        "category": "management"
    },
    "meeting.invite_participants": {
        "name": "邀请参与者",
        "description": "邀请用户参加会议",
        "module": "meeting",
        "category": "management"
    },
    "meeting.kick_participants": {
        "name": "踢出参与者",
        "description": "将参与者踢出会议",
        "module": "meeting",
        "category": "management"
    },
    
    # 会议控制权限
    "meeting.control": {
        "name": "控制会议",
        "description": "开始、暂停、结束会议",
        "module": "meeting",
        "category": "control"
    },
    "meeting.mute_participants": {
        "name": "静音参与者",
        "description": "静音或取消静音参与者",
        "module": "meeting",
        "category": "control"
    },
    "meeting.lock_meeting": {
        "name": "锁定会议",
        "description": "锁定或解锁会议房间",
        "module": "meeting",
        "category": "control"
    },
    
    # 媒体权限
    "meeting.share_screen": {
        "name": "共享屏幕",
        "description": "共享屏幕内容",
        "module": "meeting",
        "category": "media"
    },
    "meeting.share_audio": {
        "name": "共享音频",
        "description": "开启麦克风共享音频",
        "module": "meeting",
        "category": "media"
    },
    "meeting.share_video": {
        "name": "共享视频",
        "description": "开启摄像头共享视频",
        "module": "meeting",
        "category": "media"
    },
    
    # 聊天权限
    "meeting.chat": {
        "name": "使用聊天",
        "description": "发送和接收聊天消息",
        "module": "meeting",
        "category": "communication"
    },
    "meeting.private_chat": {
        "name": "私聊",
        "description": "发送私人聊天消息",
        "module": "meeting",
        "category": "communication"
    },
    
    # 文件权限
    "meeting.upload_files": {
        "name": "上传文件",
        "description": "上传和共享文件",
        "module": "meeting",
        "category": "files"
    },
    "meeting.download_files": {
        "name": "下载文件",
        "description": "下载共享的文件",
        "module": "meeting",
        "category": "files"
    },
    "meeting.manage_files": {
        "name": "管理文件",
        "description": "删除和管理共享文件",
        "module": "meeting",
        "category": "files"
    },
    
    # 录制权限
    "meeting.start_recording": {
        "name": "开始录制",
        "description": "开始录制会议",
        "module": "meeting",
        "category": "recording"
    },
    "meeting.stop_recording": {
        "name": "停止录制",
        "description": "停止录制会议",
        "module": "meeting",
        "category": "recording"
    },
    "meeting.view_recordings": {
        "name": "查看录制",
        "description": "查看会议录制内容",
        "module": "meeting",
        "category": "recording"
    },
    "meeting.download_recordings": {
        "name": "下载录制",
        "description": "下载会议录制文件",
        "module": "meeting",
        "category": "recording"
    },
    "meeting.delete_recordings": {
        "name": "删除录制",
        "description": "删除会议录制文件",
        "module": "meeting",
        "category": "recording"
    },
    
    # AI分析权限
    "meeting.generate_ai_analysis": {
        "name": "生成AI分析",
        "description": "生成会议AI分析报告",
        "module": "meeting",
        "category": "ai"
    },
    "meeting.view_ai_analysis": {
        "name": "查看AI分析",
        "description": "查看会议AI分析结果",
        "module": "meeting",
        "category": "ai"
    },
    "meeting.export_ai_analysis": {
        "name": "导出AI分析",
        "description": "导出AI分析报告",
        "module": "meeting",
        "category": "ai"
    }
}

# 角色权限映射
ROLE_PERMISSION_MAPPING = {
    "meeting_organizer": [
        "meeting.view", "meeting.create", "meeting.update", "meeting.delete",
        "meeting.join", "meeting.leave", "meeting.manage_participants",
        "meeting.invite_participants", "meeting.kick_participants",
        "meeting.control", "meeting.mute_participants", "meeting.lock_meeting",
        "meeting.share_screen", "meeting.share_audio", "meeting.share_video",
        "meeting.chat", "meeting.private_chat", "meeting.upload_files",
        "meeting.download_files", "meeting.manage_files",
        "meeting.start_recording", "meeting.stop_recording",
        "meeting.view_recordings", "meeting.download_recordings",
        "meeting.delete_recordings", "meeting.generate_ai_analysis",
        "meeting.view_ai_analysis", "meeting.export_ai_analysis"
    ],
    "meeting_moderator": [
        "meeting.view", "meeting.join", "meeting.leave",
        "meeting.manage_participants", "meeting.invite_participants",
        "meeting.kick_participants", "meeting.control", "meeting.mute_participants",
        "meeting.share_screen", "meeting.share_audio", "meeting.share_video",
        "meeting.chat", "meeting.private_chat", "meeting.upload_files",
        "meeting.download_files", "meeting.start_recording", "meeting.stop_recording",
        "meeting.view_recordings", "meeting.view_ai_analysis"
    ],
    "meeting_presenter": [
        "meeting.view", "meeting.join", "meeting.leave",
        "meeting.share_screen", "meeting.share_audio", "meeting.share_video",
        "meeting.chat", "meeting.upload_files", "meeting.download_files",
        "meeting.view_recordings", "meeting.view_ai_analysis"
    ],
    "meeting_participant": [
        "meeting.view", "meeting.join", "meeting.leave",
        "meeting.share_audio", "meeting.share_video", "meeting.chat",
        "meeting.download_files", "meeting.view_ai_analysis"
    ],
    "meeting_observer": [
        "meeting.view", "meeting.join", "meeting.leave",
        "meeting.chat", "meeting.download_files", "meeting.view_ai_analysis"
    ]
}


class MeetingPermissionService:
    """会议权限管理服务"""
    
    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self.redis_client = redis_client
        self.permission_service = PermissionService(session)
    
    async def initialize_meeting_permissions(self) -> bool:
        """初始化会议权限"""
        try:
            logger.info("开始初始化会议权限...")
            
            # 创建会议权限
            for permission_code, permission_info in MEETING_PERMISSIONS.items():
                await self._create_permission_if_not_exists(permission_code, permission_info)
            
            # 创建会议角色
            for role_code, permission_codes in ROLE_PERMISSION_MAPPING.items():
                await self._create_role_if_not_exists(role_code, permission_codes)
            
            logger.info("会议权限初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化会议权限失败: {e}")
            return False
    
    async def check_meeting_permission(
        self,
        user_id: int,
        meeting_id: int,
        permission: str
    ) -> bool:
        """
        检查用户在特定会议中的权限
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            permission: 权限代码
            
        Returns:
            bool: 是否有权限
        """
        try:
            # 缓存键
            cache_key = f"meeting_permission:{user_id}:{meeting_id}:{permission}"
            
            # 尝试从缓存获取
            if self.redis_client:
                cached_result = await self.redis_client.get(cache_key)
                if cached_result is not None:
                    return cached_result == "1"
            
            # 检查权限
            has_permission = await self._check_permission_internal(user_id, meeting_id, permission)
            
            # 缓存结果
            if self.redis_client:
                await self.redis_client.setex(cache_key, 300, "1" if has_permission else "0")  # 缓存5分钟
            
            return has_permission
            
        except Exception as e:
            logger.error(f"检查会议权限失败: {e}")
            return False
    
    async def _check_permission_internal(
        self,
        user_id: int,
        meeting_id: int,
        permission: str
    ) -> bool:
        """内部权限检查逻辑"""
        try:
            # 1. 检查是否为超级管理员
            user = await self._get_user(user_id)
            if user.is_superuser:
                return True
            
            # 2. 检查是否为会议组织者
            meeting = await self._get_meeting(meeting_id)
            if meeting.organizer_id == user_id:
                # 组织者拥有所有权限
                return True
            
            # 3. 检查参与者权限
            participant = await self._get_meeting_participant(user_id, meeting_id)
            if participant:
                # 检查参与者角色权限
                role_permissions = await self._get_role_permissions(participant.participant_role)
                if permission in role_permissions:
                    return True
                
                # 检查自定义权限
                if participant.permissions:
                    custom_permissions = json.loads(participant.permissions)
                    if permission in custom_permissions.get("granted", []):
                        return True
                    if permission in custom_permissions.get("denied", []):
                        return False
            
            # 4. 检查用户全局角色权限
            user_roles = await self._get_user_roles(user_id)
            for role in user_roles:
                role_permissions = await self._get_role_permissions(role.role_code)
                if permission in role_permissions:
                    return True
            
            # 5. 检查直接分配的权限
            direct_permissions = await self._get_user_direct_permissions(user_id)
            if permission in direct_permissions:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"内部权限检查失败: {e}")
            return False
    
    async def get_user_meeting_permissions(
        self,
        user_id: int,
        meeting_id: int
    ) -> List[str]:
        """
        获取用户在特定会议中的所有权限
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            
        Returns:
            List[str]: 权限列表
        """
        try:
            permissions = set()
            
            # 检查是否为超级管理员
            user = await self._get_user(user_id)
            if user.is_superuser:
                return list(MEETING_PERMISSIONS.keys())
            
            # 检查是否为会议组织者
            meeting = await self._get_meeting(meeting_id)
            if meeting.organizer_id == user_id:
                return ROLE_PERMISSION_MAPPING["meeting_organizer"]
            
            # 检查参与者权限
            participant = await self._get_meeting_participant(user_id, meeting_id)
            if participant:
                # 添加角色权限
                role_permissions = await self._get_role_permissions(participant.participant_role)
                permissions.update(role_permissions)
                
                # 添加自定义权限
                if participant.permissions:
                    custom_permissions = json.loads(participant.permissions)
                    permissions.update(custom_permissions.get("granted", []))
                    # 移除被拒绝的权限
                    permissions -= set(custom_permissions.get("denied", []))
            
            # 添加用户全局角色权限
            user_roles = await self._get_user_roles(user_id)
            for role in user_roles:
                role_permissions = await self._get_role_permissions(role.role_code)
                permissions.update(role_permissions)
            
            # 添加直接分配的权限
            direct_permissions = await self._get_user_direct_permissions(user_id)
            permissions.update(direct_permissions)
            
            return list(permissions)
            
        except Exception as e:
            logger.error(f"获取用户会议权限失败: {e}")
            return []
    
    async def assign_meeting_role(
        self,
        user_id: int,
        meeting_id: int,
        role: str,
        assigned_by: int
    ) -> bool:
        """
        为用户分配会议角色
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            role: 角色代码
            assigned_by: 分配者ID
            
        Returns:
            bool: 分配是否成功
        """
        try:
            # 验证角色是否存在
            if role not in ROLE_PERMISSION_MAPPING:
                raise ValidationError(f"无效的会议角色: {role}")
            
            # 检查参与者是否存在
            participant = await self._get_meeting_participant(user_id, meeting_id)
            if not participant:
                raise NotFoundError("用户不是会议参与者")
            
            # 更新参与者角色
            stmt = update(MeetingParticipant).where(
                and_(
                    MeetingParticipant.user_id == user_id,
                    MeetingParticipant.meeting_id == meeting_id
                )
            ).values(
                participant_role=role,
                updated_at=datetime.utcnow()
            )
            
            await self.session.execute(stmt)
            await self.session.commit()
            
            # 清除权限缓存
            await self._clear_user_meeting_permission_cache(user_id, meeting_id)
            
            logger.info(f"为用户 {user_id} 分配会议 {meeting_id} 角色: {role}")
            return True
            
        except Exception as e:
            logger.error(f"分配会议角色失败: {e}")
            await self.session.rollback()
            return False
    
    async def grant_meeting_permission(
        self,
        user_id: int,
        meeting_id: int,
        permission: str,
        granted_by: int,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        授予用户特定会议权限
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            permission: 权限代码
            granted_by: 授予者ID
            expires_at: 过期时间
            
        Returns:
            bool: 授予是否成功
        """
        try:
            # 验证权限是否存在
            if permission not in MEETING_PERMISSIONS:
                raise ValidationError(f"无效的会议权限: {permission}")
            
            # 获取参与者
            participant = await self._get_meeting_participant(user_id, meeting_id)
            if not participant:
                raise NotFoundError("用户不是会议参与者")
            
            # 更新自定义权限
            current_permissions = {}
            if participant.permissions:
                current_permissions = json.loads(participant.permissions)
            
            granted_permissions = current_permissions.get("granted", [])
            if permission not in granted_permissions:
                granted_permissions.append(permission)
            
            # 从拒绝列表中移除（如果存在）
            denied_permissions = current_permissions.get("denied", [])
            if permission in denied_permissions:
                denied_permissions.remove(permission)
            
            current_permissions["granted"] = granted_permissions
            current_permissions["denied"] = denied_permissions
            
            # 更新数据库
            stmt = update(MeetingParticipant).where(
                and_(
                    MeetingParticipant.user_id == user_id,
                    MeetingParticipant.meeting_id == meeting_id
                )
            ).values(
                permissions=json.dumps(current_permissions),
                updated_at=datetime.utcnow()
            )
            
            await self.session.execute(stmt)
            await self.session.commit()
            
            # 清除权限缓存
            await self._clear_user_meeting_permission_cache(user_id, meeting_id)
            
            logger.info(f"授予用户 {user_id} 会议 {meeting_id} 权限: {permission}")
            return True
            
        except Exception as e:
            logger.error(f"授予会议权限失败: {e}")
            await self.session.rollback()
            return False
    
    async def revoke_meeting_permission(
        self,
        user_id: int,
        meeting_id: int,
        permission: str,
        revoked_by: int
    ) -> bool:
        """
        撤销用户特定会议权限
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            permission: 权限代码
            revoked_by: 撤销者ID
            
        Returns:
            bool: 撤销是否成功
        """
        try:
            # 获取参与者
            participant = await self._get_meeting_participant(user_id, meeting_id)
            if not participant:
                raise NotFoundError("用户不是会议参与者")
            
            # 更新自定义权限
            current_permissions = {}
            if participant.permissions:
                current_permissions = json.loads(participant.permissions)
            
            # 从授予列表中移除
            granted_permissions = current_permissions.get("granted", [])
            if permission in granted_permissions:
                granted_permissions.remove(permission)
            
            # 添加到拒绝列表
            denied_permissions = current_permissions.get("denied", [])
            if permission not in denied_permissions:
                denied_permissions.append(permission)
            
            current_permissions["granted"] = granted_permissions
            current_permissions["denied"] = denied_permissions
            
            # 更新数据库
            stmt = update(MeetingParticipant).where(
                and_(
                    MeetingParticipant.user_id == user_id,
                    MeetingParticipant.meeting_id == meeting_id
                )
            ).values(
                permissions=json.dumps(current_permissions),
                updated_at=datetime.utcnow()
            )
            
            await self.session.execute(stmt)
            await self.session.commit()
            
            # 清除权限缓存
            await self._clear_user_meeting_permission_cache(user_id, meeting_id)
            
            logger.info(f"撤销用户 {user_id} 会议 {meeting_id} 权限: {permission}")
            return True
            
        except Exception as e:
            logger.error(f"撤销会议权限失败: {e}")
            await self.session.rollback()
            return False
    
    async def check_meeting_access(self, user_id: int, meeting_id: int) -> bool:
        """检查用户是否有访问会议的基本权限"""
        return await self.check_meeting_permission(user_id, meeting_id, "meeting.view")
    
    async def get_meeting_security_settings(self, meeting_id: int) -> Dict[str, Any]:
        """获取会议安全设置"""
        try:
            meeting = await self._get_meeting(meeting_id)
            
            settings = {}
            if meeting.meeting_settings:
                settings = json.loads(meeting.meeting_settings)
            
            return {
                "is_password_protected": settings.get("password_protected", False),
                "is_waiting_room_enabled": settings.get("waiting_room_enabled", False),
                "is_locked": settings.get("is_locked", False),
                "allow_anonymous": settings.get("allow_anonymous", False),
                "require_approval": settings.get("require_approval", False)
            }
            
        except Exception as e:
            logger.error(f"获取会议安全设置失败: {e}")
            return {}
    
    async def verify_meeting_password(self, meeting_id: int, password: str) -> bool:
        """验证会议密码"""
        try:
            meeting = await self._get_meeting(meeting_id)
            
            if not meeting.meeting_settings:
                return True
            
            settings = json.loads(meeting.meeting_settings)
            meeting_password = settings.get("password")
            
            if not meeting_password:
                return True
            
            # TODO: 使用加密比较
            return password == meeting_password
            
        except Exception as e:
            logger.error(f"验证会议密码失败: {e}")
            return False
    
    # 辅助方法
    async def _get_user(self, user_id: int) -> User:
        """获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError(f"用户不存在: {user_id}")
        
        return user
    
    async def _get_meeting(self, meeting_id: int) -> Meeting:
        """获取会议"""
        stmt = select(Meeting).where(Meeting.id == meeting_id)
        result = await self.session.execute(stmt)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError(f"会议不存在: {meeting_id}")
        
        return meeting
    
    async def _get_meeting_participant(self, user_id: int, meeting_id: int) -> Optional[MeetingParticipant]:
        """获取会议参与者"""
        stmt = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.meeting_id == meeting_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_user_roles(self, user_id: int) -> List[Role]:
        """获取用户角色"""
        stmt = select(Role).join(UserRole).where(UserRole.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def _get_role_permissions(self, role_code: str) -> List[str]:
        """获取角色权限"""
        # 首先检查预定义的角色权限映射
        if role_code in ROLE_PERMISSION_MAPPING:
            return ROLE_PERMISSION_MAPPING[role_code]
        
        # 从数据库查询
        stmt = select(Permission.permission_code).join(RolePermission).join(Role).where(
            Role.role_code == role_code
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.fetchall()]
    
    async def _get_user_direct_permissions(self, user_id: int) -> List[str]:
        """获取用户直接分配的权限"""
        # TODO: 实现用户直接权限查询
        return []
    
    async def _create_permission_if_not_exists(self, permission_code: str, permission_info: Dict[str, Any]):
        """创建权限（如果不存在）"""
        try:
            # 检查权限是否已存在
            stmt = select(Permission).where(Permission.permission_code == permission_code)
            result = await self.session.execute(stmt)
            existing_permission = result.scalar_one_or_none()
            
            if not existing_permission:
                # 创建新权限
                permission_data = {
                    "permission_code": permission_code,
                    "permission_name": permission_info["name"],
                    "description": permission_info["description"],
                    "module": permission_info["module"],
                    "category": permission_info.get("category", "general")
                }
                
                await self.permission_service.create_permission(permission_data)
                logger.info(f"创建会议权限: {permission_code}")
            
        except Exception as e:
            logger.error(f"创建权限失败: {permission_code}, {e}")
    
    async def _create_role_if_not_exists(self, role_code: str, permission_codes: List[str]):
        """创建角色（如果不存在）"""
        try:
            # 检查角色是否已存在
            stmt = select(Role).where(Role.role_code == role_code)
            result = await self.session.execute(stmt)
            existing_role = result.scalar_one_or_none()
            
            if not existing_role:
                # 创建新角色
                role_name = role_code.replace("_", " ").title()
                role_data = {
                    "role_code": role_code,
                    "role_name": role_name,
                    "description": f"会议{role_name}角色",
                    "is_system": True
                }
                
                # TODO: 实现角色创建和权限分配
                logger.info(f"创建会议角色: {role_code}")
            
        except Exception as e:
            logger.error(f"创建角色失败: {role_code}, {e}")
    
    async def _clear_user_meeting_permission_cache(self, user_id: int, meeting_id: int):
        """清除用户会议权限缓存"""
        if not self.redis_client:
            return
        
        try:
            # 清除所有相关的权限缓存
            pattern = f"meeting_permission:{user_id}:{meeting_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.debug(f"清除用户 {user_id} 会议 {meeting_id} 权限缓存")
            
        except Exception as e:
            logger.error(f"清除权限缓存失败: {e}")


async def get_meeting_permission_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client = Depends(get_redis_client)
) -> MeetingPermissionService:
    """获取会议权限服务实例"""
    return MeetingPermissionService(session, redis_client)