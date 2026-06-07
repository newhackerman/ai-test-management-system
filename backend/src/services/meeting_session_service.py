"""
会议用户会话管理服务

本模块提供会议相关的用户会话管理功能，包括：
- 用户会话的创建和管理
- 会议访问权限验证
- 会话状态同步
- 多设备会话管理
"""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.user import User
from ..models.meeting import Meeting
from ..models.meeting_participant import MeetingParticipant
from ..utils.redis_client import get_redis_client
from ..utils.jwt import jwt_service

logger = logging.getLogger(__name__)

# 会话配置
SESSION_CONFIG = {
    "meeting_session_ttl": 7200,  # 会议会话2小时
    "user_session_ttl": 3600,  # 用户会话1小时
    "device_session_ttl": 86400,  # 设备会话24小时
    "max_concurrent_sessions": 5,  # 最大并发会话数
}


class MeetingSessionService:
    """会议会话管理服务"""
    
    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self.redis_client = redis_client
    
    async def create_meeting_session(
        self,
        user_id: int,
        meeting_id: int,
        device_info: Dict[str, Any],
        client_ip: str
    ) -> Dict[str, Any]:
        """
        创建会议会话
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            device_info: 设备信息
            client_ip: 客户端IP
            
        Returns:
            Dict: 会话信息
        """
        try:
            # 验证用户和会议
            user = await self._get_user(user_id)
            meeting = await self._get_meeting(meeting_id)
            
            # 检查会议访问权限
            await self._check_meeting_access(user_id, meeting_id)
            
            # 生成会话ID
            import uuid
            session_id = str(uuid.uuid4())
            
            # 创建会话数据
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "meeting_id": meeting_id,
                "device_info": device_info,
                "client_ip": client_ip,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "status": "active",
                "permissions": await self._get_user_meeting_permissions(user_id, meeting_id)
            }
            
            # 检查并发会话限制
            await self._check_concurrent_sessions(user_id, meeting_id)
            
            # 缓存会话数据
            session_key = f"meeting_session:{session_id}"
            await self.redis_client.setex(
                session_key,
                SESSION_CONFIG["meeting_session_ttl"],
                json.dumps(session_data)
            )
            
            # 添加到用户会话列表
            user_sessions_key = f"user_meeting_sessions:{user_id}"
            await self.redis_client.sadd(user_sessions_key, session_id)
            await self.redis_client.expire(user_sessions_key, SESSION_CONFIG["user_session_ttl"])
            
            # 添加到会议会话列表
            meeting_sessions_key = f"meeting_sessions:{meeting_id}"
            await self.redis_client.sadd(meeting_sessions_key, session_id)
            await self.redis_client.expire(meeting_sessions_key, SESSION_CONFIG["meeting_session_ttl"])
            
            # 记录会话创建日志
            logger.info(f"创建会议会话: 用户 {user_id}, 会议 {meeting_id}, 会话 {session_id}")
            
            return {
                "session_id": session_id,
                "user_id": user_id,
                "meeting_id": meeting_id,
                "permissions": session_data["permissions"],
                "expires_at": (datetime.utcnow() + timedelta(seconds=SESSION_CONFIG["meeting_session_ttl"])).isoformat()
            }
            
        except Exception as e:
            logger.error(f"创建会议会话失败: {e}")
            raise
    
    async def get_meeting_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会议会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict]: 会话信息
        """
        try:
            session_key = f"meeting_session:{session_id}"
            session_data_str = await self.redis_client.get(session_key)
            
            if not session_data_str:
                return None
            
            session_data = json.loads(session_data_str)
            
            # 更新最后活动时间
            session_data["last_activity"] = datetime.utcnow().isoformat()
            await self.redis_client.setex(
                session_key,
                SESSION_CONFIG["meeting_session_ttl"],
                json.dumps(session_data)
            )
            
            return session_data
            
        except Exception as e:
            logger.error(f"获取会议会话失败: {e}")
            return None
    
    async def update_session_activity(self, session_id: str) -> bool:
        """
        更新会话活动时间
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            session_data = await self.get_meeting_session(session_id)
            
            if not session_data:
                return False
            
            # 会话数据已在get_meeting_session中更新
            return True
            
        except Exception as e:
            logger.error(f"更新会话活动时间失败: {e}")
            return False
    
    async def terminate_meeting_session(self, session_id: str, reason: str = "user_logout") -> bool:
        """
        终止会议会话
        
        Args:
            session_id: 会话ID
            reason: 终止原因
            
        Returns:
            bool: 终止是否成功
        """
        try:
            # 获取会话数据
            session_data = await self.get_meeting_session(session_id)
            
            if not session_data:
                return False
            
            user_id = session_data["user_id"]
            meeting_id = session_data["meeting_id"]
            
            # 删除会话缓存
            session_key = f"meeting_session:{session_id}"
            await self.redis_client.delete(session_key)
            
            # 从用户会话列表中移除
            user_sessions_key = f"user_meeting_sessions:{user_id}"
            await self.redis_client.srem(user_sessions_key, session_id)
            
            # 从会议会话列表中移除
            meeting_sessions_key = f"meeting_sessions:{meeting_id}"
            await self.redis_client.srem(meeting_sessions_key, session_id)
            
            # 记录会话终止日志
            logger.info(f"终止会议会话: 会话 {session_id}, 原因: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"终止会议会话失败: {e}")
            return False
    
    async def get_user_meeting_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户的所有会议会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict]: 会话列表
        """
        try:
            user_sessions_key = f"user_meeting_sessions:{user_id}"
            session_ids = await self.redis_client.smembers(user_sessions_key)
            
            sessions = []
            for session_id in session_ids:
                session_data = await self.get_meeting_session(session_id)
                if session_data:
                    sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            logger.error(f"获取用户会议会话失败: {e}")
            return []
    
    async def get_meeting_active_sessions(self, meeting_id: int) -> List[Dict[str, Any]]:
        """
        获取会议的所有活跃会话
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            List[Dict]: 会话列表
        """
        try:
            meeting_sessions_key = f"meeting_sessions:{meeting_id}"
            session_ids = await self.redis_client.smembers(meeting_sessions_key)
            
            sessions = []
            for session_id in session_ids:
                session_data = await self.get_meeting_session(session_id)
                if session_data:
                    sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            logger.error(f"获取会议活跃会话失败: {e}")
            return []
    
    async def terminate_user_sessions(self, user_id: int, exclude_session: Optional[str] = None) -> int:
        """
        终止用户的所有会话
        
        Args:
            user_id: 用户ID
            exclude_session: 排除的会话ID
            
        Returns:
            int: 终止的会话数量
        """
        try:
            sessions = await self.get_user_meeting_sessions(user_id)
            terminated_count = 0
            
            for session in sessions:
                session_id = session["session_id"]
                
                if exclude_session and session_id == exclude_session:
                    continue
                
                success = await self.terminate_meeting_session(session_id, "admin_terminate")
                if success:
                    terminated_count += 1
            
            logger.info(f"终止用户 {user_id} 的 {terminated_count} 个会话")
            return terminated_count
            
        except Exception as e:
            logger.error(f"终止用户会话失败: {e}")
            return 0
    
    async def validate_session_permissions(
        self,
        session_id: str,
        required_permission: str
    ) -> bool:
        """
        验证会话权限
        
        Args:
            session_id: 会话ID
            required_permission: 所需权限
            
        Returns:
            bool: 是否有权限
        """
        try:
            session_data = await self.get_meeting_session(session_id)
            
            if not session_data:
                return False
            
            permissions = session_data.get("permissions", [])
            return required_permission in permissions
            
        except Exception as e:
            logger.error(f"验证会话权限失败: {e}")
            return False
    
    async def sync_session_permissions(self, session_id: str) -> bool:
        """
        同步会话权限
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 同步是否成功
        """
        try:
            session_data = await self.get_meeting_session(session_id)
            
            if not session_data:
                return False
            
            user_id = session_data["user_id"]
            meeting_id = session_data["meeting_id"]
            
            # 重新获取用户权限
            new_permissions = await self._get_user_meeting_permissions(user_id, meeting_id)
            
            # 更新会话权限
            session_data["permissions"] = new_permissions
            session_data["permissions_updated_at"] = datetime.utcnow().isoformat()
            
            # 更新缓存
            session_key = f"meeting_session:{session_id}"
            await self.redis_client.setex(
                session_key,
                SESSION_CONFIG["meeting_session_ttl"],
                json.dumps(session_data)
            )
            
            logger.info(f"同步会话权限: 会话 {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"同步会话权限失败: {e}")
            return False
    
    async def _get_user(self, user_id: int) -> User:
        """获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError(f"用户不存在: {user_id}")
        
        if not user.is_active:
            raise ValidationError("用户账户已禁用")
        
        return user
    
    async def _get_meeting(self, meeting_id: int) -> Meeting:
        """获取会议"""
        stmt = select(Meeting).where(Meeting.id == meeting_id)
        result = await self.session.execute(stmt)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError(f"会议不存在: {meeting_id}")
        
        return meeting
    
    async def _check_meeting_access(self, user_id: int, meeting_id: int):
        """检查会议访问权限"""
        # 检查用户是否为会议参与者
        stmt = select(MeetingParticipant).where(
            MeetingParticipant.user_id == user_id,
            MeetingParticipant.meeting_id == meeting_id
        )
        result = await self.session.execute(stmt)
        participant = result.scalar_one_or_none()
        
        if not participant:
            # 检查是否为会议组织者
            stmt = select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.organizer_id == user_id
            )
            result = await self.session.execute(stmt)
            meeting = result.scalar_one_or_none()
            
            if not meeting:
                raise PermissionError("无权限访问此会议")
    
    async def _get_user_meeting_permissions(self, user_id: int, meeting_id: int) -> List[str]:
        """获取用户在会议中的权限"""
        permissions = []
        
        try:
            # 检查是否为会议组织者
            stmt = select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.organizer_id == user_id
            )
            result = await self.session.execute(stmt)
            meeting = result.scalar_one_or_none()
            
            if meeting:
                # 组织者拥有所有权限
                permissions = [
                    "view_meeting", "update_meeting", "delete_meeting",
                    "manage_participants", "control_meeting", "share_screen",
                    "use_chat", "upload_files", "start_recording", "stop_recording",
                    "view_recordings", "delete_recordings", "generate_ai_analysis",
                    "view_ai_analysis"
                ]
            else:
                # 检查参与者权限
                stmt = select(MeetingParticipant).where(
                    MeetingParticipant.user_id == user_id,
                    MeetingParticipant.meeting_id == meeting_id
                )
                result = await self.session.execute(stmt)
                participant = result.scalar_one_or_none()
                
                if participant:
                    # 根据参与者角色分配权限
                    if participant.participant_role == "MODERATOR":
                        permissions = [
                            "view_meeting", "manage_participants", "control_meeting",
                            "share_screen", "use_chat", "upload_files", "start_recording",
                            "stop_recording", "view_recordings", "view_ai_analysis"
                        ]
                    elif participant.participant_role == "PRESENTER":
                        permissions = [
                            "view_meeting", "share_screen", "use_chat", "upload_files",
                            "view_recordings", "view_ai_analysis"
                        ]
                    else:  # PARTICIPANT
                        permissions = [
                            "view_meeting", "use_chat", "view_ai_analysis"
                        ]
                    
                    # 添加自定义权限
                    if participant.permissions:
                        custom_permissions = json.loads(participant.permissions)
                        permissions.extend(custom_permissions.get("additional_permissions", []))
            
            return permissions
            
        except Exception as e:
            logger.error(f"获取用户会议权限失败: {e}")
            return ["view_meeting"]  # 默认只有查看权限
    
    async def _check_concurrent_sessions(self, user_id: int, meeting_id: int):
        """检查并发会话限制"""
        try:
            sessions = await self.get_user_meeting_sessions(user_id)
            
            # 过滤同一会议的会话
            meeting_sessions = [s for s in sessions if s["meeting_id"] == meeting_id]
            
            if len(meeting_sessions) >= SESSION_CONFIG["max_concurrent_sessions"]:
                # 终止最旧的会话
                oldest_session = min(meeting_sessions, key=lambda x: x["created_at"])
                await self.terminate_meeting_session(
                    oldest_session["session_id"],
                    "concurrent_limit_exceeded"
                )
                
                logger.info(f"超出并发会话限制，终止最旧会话: {oldest_session['session_id']}")
            
        except Exception as e:
            logger.error(f"检查并发会话限制失败: {e}")


async def get_meeting_session_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client = Depends(get_redis_client)
) -> MeetingSessionService:
    """获取会议会话服务实例"""
    return MeetingSessionService(session, redis_client)