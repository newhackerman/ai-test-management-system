"""
会议用户个人资料集成服务

本模块提供会议相关的用户个人资料集成功能，包括：
- 在会议中显示用户头像、姓名等信息
- 集成用户时区设置，实现智能时间显示
- 集成用户通知偏好设置
- 实现用户会议历史和统计信息
"""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import pytz

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError
from ..models.user import User
from ..models.meeting import Meeting
from ..models.meeting_participant import MeetingParticipant
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# 默认用户偏好设置
DEFAULT_USER_PREFERENCES = {
    "timezone": "UTC",
    "language": "zh-CN",
    "date_format": "YYYY-MM-DD",
    "time_format": "24h",
    "notifications": {
        "email_enabled": True,
        "sms_enabled": False,
        "push_enabled": True,
        "meeting_reminders": True,
        "meeting_invitations": True,
        "meeting_updates": True,
        "reminder_times": [15, 5]  # 提前15分钟和5分钟提醒
    },
    "meeting_preferences": {
        "auto_join_audio": True,
        "auto_join_video": False,
        "default_mute": True,
        "show_participant_names": True,
        "enable_chat_notifications": True,
        "enable_screen_share_notifications": True
    },
    "privacy": {
        "show_online_status": True,
        "allow_direct_messages": True,
        "show_meeting_history": True
    }
}


class MeetingUserProfileService:
    """会议用户个人资料服务"""
    
    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self.redis_client = redis_client
    
    async def get_user_profile_for_meeting(
        self,
        user_id: int,
        meeting_id: Optional[int] = None,
        include_preferences: bool = True,
        include_statistics: bool = False
    ) -> Dict[str, Any]:
        """
        获取用户在会议中的个人资料信息
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID（可选）
            include_preferences: 是否包含偏好设置
            include_statistics: 是否包含统计信息
            
        Returns:
            Dict: 用户个人资料信息
        """
        try:
            # 获取用户基本信息
            user = await self._get_user(user_id)
            
            profile = {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "nickname": user.nickname or user.username,
                "full_name": user.full_name,
                "avatar": user.avatar,
                "is_online": await self._get_user_online_status(user_id),
                "last_seen": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat(),
                "is_verified": user.is_verified
            }
            
            # 添加偏好设置
            if include_preferences:
                preferences = await self.get_user_preferences(user_id)
                profile["preferences"] = preferences
                
                # 添加时区信息
                profile["timezone_info"] = await self._get_timezone_info(preferences.get("timezone", "UTC"))
            
            # 添加会议相关信息
            if meeting_id:
                meeting_info = await self._get_user_meeting_info(user_id, meeting_id)
                profile["meeting_info"] = meeting_info
            
            # 添加统计信息
            if include_statistics:
                statistics = await self.get_user_meeting_statistics(user_id)
                profile["statistics"] = statistics
            
            return profile
            
        except Exception as e:
            logger.error(f"获取用户会议个人资料失败: {e}")
            raise
    
    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户偏好设置
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户偏好设置
        """
        try:
            # 尝试从缓存获取
            cache_key = f"user_preferences:{user_id}"
            if self.redis_client:
                cached_preferences = await self.redis_client.get(cache_key)
                if cached_preferences:
                    return json.loads(cached_preferences)
            
            # 从数据库获取用户信息
            user = await self._get_user(user_id)
            
            # 解析用户偏好设置
            preferences = DEFAULT_USER_PREFERENCES.copy()
            if user.preferences:
                user_prefs = json.loads(user.preferences)
                preferences.update(user_prefs)
            
            # 缓存偏好设置
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key,
                    3600,  # 缓存1小时
                    json.dumps(preferences)
                )
            
            return preferences
            
        except Exception as e:
            logger.error(f"获取用户偏好设置失败: {e}")
            return DEFAULT_USER_PREFERENCES.copy()
    
    async def update_user_preferences(
        self,
        user_id: int,
        preferences: Dict[str, Any]
    ) -> bool:
        """
        更新用户偏好设置
        
        Args:
            user_id: 用户ID
            preferences: 偏好设置
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取当前偏好设置
            current_preferences = await self.get_user_preferences(user_id)
            
            # 合并新的偏好设置
            current_preferences.update(preferences)
            
            # 更新数据库
            stmt = update(User).where(User.id == user_id).values(
                preferences=json.dumps(current_preferences),
                updated_at=datetime.utcnow()
            )
            
            await self.session.execute(stmt)
            await self.session.commit()
            
            # 清除缓存
            cache_key = f"user_preferences:{user_id}"
            if self.redis_client:
                await self.redis_client.delete(cache_key)
            
            logger.info(f"更新用户 {user_id} 偏好设置成功")
            return True
            
        except Exception as e:
            logger.error(f"更新用户偏好设置失败: {e}")
            await self.session.rollback()
            return False
    
    async def get_user_meeting_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户会议统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 统计信息
        """
        try:
            # 缓存键
            cache_key = f"user_meeting_stats:{user_id}"
            
            # 尝试从缓存获取
            if self.redis_client:
                cached_stats = await self.redis_client.get(cache_key)
                if cached_stats:
                    return json.loads(cached_stats)
            
            # 计算统计信息
            stats = {}
            
            # 总会议数（作为组织者）
            organizer_count_stmt = select(func.count(Meeting.id)).where(Meeting.organizer_id == user_id)
            organizer_result = await self.session.execute(organizer_count_stmt)
            stats["meetings_organized"] = organizer_result.scalar() or 0
            
            # 总参与会议数
            participant_count_stmt = select(func.count(MeetingParticipant.id)).where(
                MeetingParticipant.user_id == user_id
            )
            participant_result = await self.session.execute(participant_count_stmt)
            stats["meetings_participated"] = participant_result.scalar() or 0
            
            # 本月会议数
            current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_organizer_stmt = select(func.count(Meeting.id)).where(
                and_(
                    Meeting.organizer_id == user_id,
                    Meeting.created_at >= current_month_start
                )
            )
            monthly_organizer_result = await self.session.execute(monthly_organizer_stmt)
            stats["meetings_this_month"] = monthly_organizer_result.scalar() or 0
            
            # 平均会议时长（作为组织者的会议）
            avg_duration_stmt = select(func.avg(Meeting.actual_duration)).where(
                and_(
                    Meeting.organizer_id == user_id,
                    Meeting.actual_duration.isnot(None)
                )
            )
            avg_duration_result = await self.session.execute(avg_duration_stmt)
            avg_duration = avg_duration_result.scalar()
            stats["average_meeting_duration"] = int(avg_duration) if avg_duration else 0
            
            # 最近参与的会议
            recent_meetings_stmt = select(Meeting).join(MeetingParticipant).where(
                MeetingParticipant.user_id == user_id
            ).order_by(Meeting.scheduled_start_time.desc()).limit(5)
            
            recent_meetings_result = await self.session.execute(recent_meetings_stmt)
            recent_meetings = recent_meetings_result.scalars().all()
            
            stats["recent_meetings"] = [
                {
                    "id": meeting.id,
                    "title": meeting.title,
                    "scheduled_start_time": meeting.scheduled_start_time.isoformat(),
                    "status": meeting.status
                }
                for meeting in recent_meetings
            ]
            
            # 会议角色分布
            role_distribution_stmt = select(
                MeetingParticipant.participant_role,
                func.count(MeetingParticipant.id)
            ).where(
                MeetingParticipant.user_id == user_id
            ).group_by(MeetingParticipant.participant_role)
            
            role_distribution_result = await self.session.execute(role_distribution_stmt)
            role_distribution = dict(role_distribution_result.fetchall())
            stats["role_distribution"] = role_distribution
            
            # 缓存统计信息
            if self.redis_client:
                await self.redis_client.setex(
                    cache_key,
                    1800,  # 缓存30分钟
                    json.dumps(stats, default=str)
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"获取用户会议统计失败: {e}")
            return {}
    
    async def get_user_timezone_info(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户时区信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 时区信息
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            timezone_name = preferences.get("timezone", "UTC")
            
            return await self._get_timezone_info(timezone_name)
            
        except Exception as e:
            logger.error(f"获取用户时区信息失败: {e}")
            return await self._get_timezone_info("UTC")
    
    async def format_time_for_user(
        self,
        user_id: int,
        dt: datetime,
        format_type: str = "datetime"
    ) -> str:
        """
        为用户格式化时间显示
        
        Args:
            user_id: 用户ID
            dt: 时间对象
            format_type: 格式类型（datetime, date, time）
            
        Returns:
            str: 格式化后的时间字符串
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            timezone_name = preferences.get("timezone", "UTC")
            date_format = preferences.get("date_format", "YYYY-MM-DD")
            time_format = preferences.get("time_format", "24h")
            
            # 转换时区
            user_tz = pytz.timezone(timezone_name)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            
            local_dt = dt.astimezone(user_tz)
            
            # 格式化时间
            if format_type == "date":
                if date_format == "MM/DD/YYYY":
                    return local_dt.strftime("%m/%d/%Y")
                elif date_format == "DD/MM/YYYY":
                    return local_dt.strftime("%d/%m/%Y")
                else:  # YYYY-MM-DD
                    return local_dt.strftime("%Y-%m-%d")
            
            elif format_type == "time":
                if time_format == "12h":
                    return local_dt.strftime("%I:%M %p")
                else:  # 24h
                    return local_dt.strftime("%H:%M")
            
            else:  # datetime
                date_str = await self.format_time_for_user(user_id, dt, "date")
                time_str = await self.format_time_for_user(user_id, dt, "time")
                return f"{date_str} {time_str}"
            
        except Exception as e:
            logger.error(f"格式化用户时间失败: {e}")
            return dt.strftime("%Y-%m-%d %H:%M")
    
    async def get_user_notification_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户通知偏好设置
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 通知偏好设置
        """
        try:
            preferences = await self.get_user_preferences(user_id)
            return preferences.get("notifications", DEFAULT_USER_PREFERENCES["notifications"])
            
        except Exception as e:
            logger.error(f"获取用户通知偏好失败: {e}")
            return DEFAULT_USER_PREFERENCES["notifications"]
    
    async def should_send_notification(
        self,
        user_id: int,
        notification_type: str
    ) -> bool:
        """
        检查是否应该发送通知
        
        Args:
            user_id: 用户ID
            notification_type: 通知类型
            
        Returns:
            bool: 是否应该发送
        """
        try:
            notification_prefs = await self.get_user_notification_preferences(user_id)
            
            # 检查通知类型是否启用
            if notification_type in notification_prefs:
                return notification_prefs[notification_type]
            
            # 默认启用
            return True
            
        except Exception as e:
            logger.error(f"检查通知设置失败: {e}")
            return True
    
    async def get_meeting_participants_profiles(
        self,
        meeting_id: int,
        include_offline: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取会议参与者的个人资料列表
        
        Args:
            meeting_id: 会议ID
            include_offline: 是否包含离线用户
            
        Returns:
            List[Dict]: 参与者个人资料列表
        """
        try:
            # 获取会议参与者
            stmt = select(MeetingParticipant).options(
                selectinload(MeetingParticipant.user)
            ).where(MeetingParticipant.meeting_id == meeting_id)
            
            result = await self.session.execute(stmt)
            participants = result.scalars().all()
            
            profiles = []
            for participant in participants:
                user = participant.user
                
                # 获取在线状态
                is_online = await self._get_user_online_status(user.id)
                
                # 如果不包含离线用户且用户离线，跳过
                if not include_offline and not is_online:
                    continue
                
                profile = {
                    "user_id": user.id,
                    "username": user.username,
                    "nickname": user.nickname or user.username,
                    "full_name": user.full_name,
                    "avatar": user.avatar,
                    "is_online": is_online,
                    "participant_role": participant.participant_role,
                    "joined_at": participant.joined_at.isoformat() if participant.joined_at else None,
                    "left_at": participant.left_at.isoformat() if participant.left_at else None,
                    "attendance_status": participant.attendance_status
                }
                
                profiles.append(profile)
            
            return profiles
            
        except Exception as e:
            logger.error(f"获取会议参与者个人资料失败: {e}")
            return []
    
    # 辅助方法
    async def _get_user(self, user_id: int) -> User:
        """获取用户"""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError(f"用户不存在: {user_id}")
        
        return user
    
    async def _get_user_online_status(self, user_id: int) -> bool:
        """获取用户在线状态"""
        if not self.redis_client:
            return False
        
        try:
            # 检查用户会话
            session_key = f"user_session:{user_id}"
            session_exists = await self.redis_client.exists(session_key)
            
            if session_exists:
                return True
            
            # 检查最近活动
            activity_key = f"user_activity:{user_id}"
            last_activity = await self.redis_client.get(activity_key)
            
            if last_activity:
                last_activity_time = datetime.fromisoformat(last_activity)
                # 如果5分钟内有活动，认为在线
                return (datetime.utcnow() - last_activity_time).total_seconds() < 300
            
            return False
            
        except Exception as e:
            logger.error(f"获取用户在线状态失败: {e}")
            return False
    
    async def _get_timezone_info(self, timezone_name: str) -> Dict[str, Any]:
        """获取时区信息"""
        try:
            tz = pytz.timezone(timezone_name)
            now = datetime.utcnow()
            local_now = tz.localize(now.replace(tzinfo=None))
            
            return {
                "timezone": timezone_name,
                "offset": local_now.strftime("%z"),
                "offset_hours": local_now.utcoffset().total_seconds() / 3600,
                "is_dst": local_now.dst() != timedelta(0),
                "current_time": local_now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取时区信息失败: {e}")
            # 返回UTC作为默认值
            utc_now = pytz.utc.localize(datetime.utcnow())
            return {
                "timezone": "UTC",
                "offset": "+0000",
                "offset_hours": 0,
                "is_dst": False,
                "current_time": utc_now.isoformat()
            }
    
    async def _get_user_meeting_info(self, user_id: int, meeting_id: int) -> Dict[str, Any]:
        """获取用户在特定会议中的信息"""
        try:
            # 获取参与者信息
            stmt = select(MeetingParticipant).where(
                and_(
                    MeetingParticipant.user_id == user_id,
                    MeetingParticipant.meeting_id == meeting_id
                )
            )
            result = await self.session.execute(stmt)
            participant = result.scalar_one_or_none()
            
            if participant:
                return {
                    "participant_role": participant.participant_role,
                    "invitation_status": participant.invitation_status,
                    "attendance_status": participant.attendance_status,
                    "joined_at": participant.joined_at.isoformat() if participant.joined_at else None,
                    "left_at": participant.left_at.isoformat() if participant.left_at else None,
                    "permissions": json.loads(participant.permissions) if participant.permissions else {}
                }
            
            # 检查是否为会议组织者
            stmt = select(Meeting).where(
                and_(
                    Meeting.id == meeting_id,
                    Meeting.organizer_id == user_id
                )
            )
            result = await self.session.execute(stmt)
            meeting = result.scalar_one_or_none()
            
            if meeting:
                return {
                    "participant_role": "ORGANIZER",
                    "invitation_status": "ACCEPTED",
                    "attendance_status": "PRESENT",
                    "is_organizer": True
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"获取用户会议信息失败: {e}")
            return {}


async def get_meeting_user_profile_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client = Depends(get_redis_client)
) -> MeetingUserProfileService:
    """获取会议用户个人资料服务实例"""
    return MeetingUserProfileService(session, redis_client)