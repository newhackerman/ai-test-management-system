"""
会议通知服务

本模块实现了会议相关的通知功能，包括：
- 会议邀请通知发送
- 会议提醒通知（15分钟前、1小时前等）
- 会议变更通知
- 多渠道通知支持（WebSocket、邮件、短信等）
- 个性化通知设置
- 通知历史管理
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ..models.meeting import Meeting, MeetingParticipant, MeetingType, MeetingStatus, ParticipantRole, InvitationStatus
from ..models.user import User
from ..models.project import Project
from .websocket_service import websocket_service, WSMessage, WSMessageType
from .email_service import EmailService, EmailConfig
from .system_notification_service import SystemNotificationService
from ..core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """通知渠道"""
    WEBSOCKET = "websocket"      # WebSocket实时通知
    EMAIL = "email"              # 邮件通知
    SMS = "sms"                  # 短信通知
    IN_APP = "in_app"           # 应用内通知
    PUSH = "push"               # 推送通知


class MeetingNotificationType(str, Enum):
    """会议通知类型"""
    # 邀请相关
    MEETING_INVITATION = "meeting_invitation"
    INVITATION_RESPONSE = "invitation_response"
    
    # 提醒相关
    MEETING_REMINDER_15MIN = "meeting_reminder_15min"
    MEETING_REMINDER_1HOUR = "meeting_reminder_1hour"
    MEETING_REMINDER_1DAY = "meeting_reminder_1day"
    
    # 状态变更
    MEETING_STARTED = "meeting_started"
    MEETING_ENDED = "meeting_ended"
    MEETING_CANCELLED = "meeting_cancelled"
    MEETING_POSTPONED = "meeting_postponed"
    
    # 会议变更
    MEETING_UPDATED = "meeting_updated"
    MEETING_TIME_CHANGED = "meeting_time_changed"
    PARTICIPANT_ADDED = "participant_added"
    PARTICIPANT_REMOVED = "participant_removed"
    ROLE_CHANGED = "role_changed"
    
    # 会议进行中
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    
    # 会后通知
    MEETING_SUMMARY_READY = "meeting_summary_ready"
    MEETING_RECORDING_READY = "meeting_recording_ready"
    ACTION_ITEMS_ASSIGNED = "action_items_assigned"


class NotificationPriority(str, Enum):
    """通知优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationPreference(BaseModel):
    """通知偏好设置"""
    user_id: int
    notification_type: MeetingNotificationType
    channels: List[NotificationChannel] = Field(default_factory=list)
    enabled: bool = True
    advance_minutes: Optional[int] = None  # 提前通知时间（分钟）
    quiet_hours_start: Optional[str] = None  # 免打扰开始时间，格式：HH:MM
    quiet_hours_end: Optional[str] = None    # 免打扰结束时间，格式：HH:MM
    
    class Config:
        use_enum_values = True


class NotificationTemplate(BaseModel):
    """通知模板"""
    notification_type: MeetingNotificationType
    channel: NotificationChannel
    title_template: str
    content_template: str
    variables: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class NotificationRecord(BaseModel):
    """通知记录"""
    id: Optional[str] = None
    user_id: int
    meeting_id: int
    notification_type: MeetingNotificationType
    channel: NotificationChannel
    priority: NotificationPriority
    title: str
    content: str
    data: Optional[Dict[str, Any]] = None
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class MeetingNotificationService:
    """会议通知服务"""
    
    def __init__(self, db: AsyncSession, email_service: Optional[EmailService] = None):
        self.db = db
        self.email_service = email_service
        self.notification_preferences: Dict[int, Dict[MeetingNotificationType, NotificationPreference]] = {}
        self.notification_templates: Dict[tuple, NotificationTemplate] = {}
        self.notification_queue: List[NotificationRecord] = []
        self.notification_history: List[NotificationRecord] = []
        
        # 初始化默认模板
        self._init_default_templates()
    
    def _init_default_templates(self):
        """初始化默认通知模板"""
        templates = [
            # 邀请相关模板
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_INVITATION,
                channel=NotificationChannel.WEBSOCKET,
                title_template="会议邀请: {meeting_title}",
                content_template="您被邀请参加会议 '{meeting_title}'，时间：{start_time}",
                variables=["meeting_title", "meeting_code", "start_time", "organizer_name", "meeting_type"]
            ),
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_INVITATION,
                channel=NotificationChannel.EMAIL,
                title_template="会议邀请: {meeting_title}",
                content_template="""
                <h3>会议邀请</h3>
                <p>尊敬的 {participant_name}，</p>
                <p>您被邀请参加以下会议：</p>
                <ul>
                    <li><strong>会议标题:</strong> {meeting_title}</li>
                    <li><strong>会议编码:</strong> {meeting_code}</li>
                    <li><strong>会议类型:</strong> {meeting_type}</li>
                    <li><strong>开始时间:</strong> {start_time}</li>
                    <li><strong>结束时间:</strong> {end_time}</li>
                    <li><strong>组织者:</strong> {organizer_name}</li>
                    <li><strong>会议描述:</strong> {description}</li>
                </ul>
                <p><strong>会议议程:</strong></p>
                <div>{agenda}</div>
                <p>请点击以下链接加入会议：</p>
                <p><a href="{meeting_url}">加入会议</a></p>
                <p>此致<br>会议管理系统</p>
                """,
                variables=["participant_name", "meeting_title", "meeting_code", "meeting_type", 
                          "start_time", "end_time", "organizer_name", "description", "agenda", "meeting_url"]
            ),
            
            # 提醒相关模板
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_REMINDER_15MIN,
                channel=NotificationChannel.WEBSOCKET,
                title_template="会议提醒: {meeting_title}",
                content_template="会议 '{meeting_title}' 将在15分钟后开始",
                variables=["meeting_title", "meeting_code", "start_time"]
            ),
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_REMINDER_1HOUR,
                channel=NotificationChannel.WEBSOCKET,
                title_template="会议提醒: {meeting_title}",
                content_template="会议 '{meeting_title}' 将在1小时后开始",
                variables=["meeting_title", "meeting_code", "start_time"]
            ),
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_REMINDER_1DAY,
                channel=NotificationChannel.EMAIL,
                title_template="会议提醒: {meeting_title} - 明天开始",
                content_template="""
                <h3>会议提醒</h3>
                <p>尊敬的 {participant_name}，</p>
                <p>提醒您明天有以下会议：</p>
                <ul>
                    <li><strong>会议标题:</strong> {meeting_title}</li>
                    <li><strong>会议编码:</strong> {meeting_code}</li>
                    <li><strong>开始时间:</strong> {start_time}</li>
                    <li><strong>会议室:</strong> {meeting_url}</li>
                </ul>
                <p>请提前做好准备。</p>
                <p>此致<br>会议管理系统</p>
                """,
                variables=["participant_name", "meeting_title", "meeting_code", "start_time", "meeting_url"]
            ),
            
            # 状态变更模板
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_STARTED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="会议已开始: {meeting_title}",
                content_template="会议 '{meeting_title}' 已开始，点击加入",
                variables=["meeting_title", "meeting_code", "meeting_url"]
            ),
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_CANCELLED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="会议已取消: {meeting_title}",
                content_template="会议 '{meeting_title}' 已被取消。取消原因：{reason}",
                variables=["meeting_title", "meeting_code", "reason", "cancelled_by"]
            ),
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_POSTPONED,
                channel=NotificationChannel.EMAIL,
                title_template="会议延期通知: {meeting_title}",
                content_template="""
                <h3>会议延期通知</h3>
                <p>尊敬的 {participant_name}，</p>
                <p>会议 '{meeting_title}' 已延期：</p>
                <ul>
                    <li><strong>原定时间:</strong> {original_start_time}</li>
                    <li><strong>新的时间:</strong> {new_start_time}</li>
                    <li><strong>延期原因:</strong> {reason}</li>
                </ul>
                <p>请注意时间变更。</p>
                <p>此致<br>会议管理系统</p>
                """,
                variables=["participant_name", "meeting_title", "original_start_time", "new_start_time", "reason"]
            ),
            
            # 变更通知模板
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_UPDATED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="会议信息更新: {meeting_title}",
                content_template="会议 '{meeting_title}' 的信息已更新，请查看最新详情",
                variables=["meeting_title", "meeting_code", "changes"]
            ),
            NotificationTemplate(
                notification_type=MeetingNotificationType.PARTICIPANT_ADDED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="新参与者加入: {meeting_title}",
                content_template="{participant_name} 已被添加到会议 '{meeting_title}'",
                variables=["meeting_title", "participant_name", "added_by"]
            ),
            
            # 会后通知模板
            NotificationTemplate(
                notification_type=MeetingNotificationType.MEETING_SUMMARY_READY,
                channel=NotificationChannel.EMAIL,
                title_template="会议纪要已生成: {meeting_title}",
                content_template="""
                <h3>会议纪要通知</h3>
                <p>尊敬的 {participant_name}，</p>
                <p>会议 '{meeting_title}' 的纪要已生成：</p>
                <ul>
                    <li><strong>会议时间:</strong> {meeting_date}</li>
                    <li><strong>会议时长:</strong> {duration} 分钟</li>
                    <li><strong>参与人数:</strong> {participant_count} 人</li>
                </ul>
                <p>请点击以下链接查看详细纪要：</p>
                <p><a href="{summary_url}">查看会议纪要</a></p>
                <p>此致<br>会议管理系统</p>
                """,
                variables=["participant_name", "meeting_title", "meeting_date", "duration", "participant_count", "summary_url"]
            )
        ]
        
        for template in templates:
            key = (template.notification_type, template.channel)
            self.notification_templates[key] = template
    
    async def send_meeting_invitation(self, meeting: Meeting, participants: List[MeetingParticipant]):
        """
        发送会议邀请通知
        
        Args:
            meeting: 会议对象
            participants: 参与者列表
        """
        try:
            # 获取组织者信息
            organizer = await self._get_user_by_id(meeting.organizer_id)
            organizer_name = organizer.username if organizer else "未知用户"
            
            # 构建通知数据
            notification_data = {
                "meeting_id": meeting.id,
                "meeting_code": meeting.meeting_code,
                "meeting_title": meeting.title,
                "meeting_type": meeting.meeting_type.value,
                "description": meeting.description or "",
                "start_time": meeting.scheduled_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": meeting.scheduled_end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "organizer_name": organizer_name,
                "agenda": self._format_agenda(meeting.agenda),
                "meeting_url": f"/meetings/{meeting.meeting_code}/join"
            }
            
            # 为每个参与者发送邀请通知（含组织者，组织者作为参与人也需要收到通知）
            for participant in participants:
                user = await self._get_user_by_id(participant.user_id)
                if user:
                        participant_data = {
                            **notification_data,
                            "participant_name": user.username,
                            "participant_role": participant.participant_role.value
                        }

                        await SystemNotificationService(self.db).create_notification(
                            user_id=participant.user_id,
                            sender_id=meeting.organizer_id,
                            category="meeting_invitation",
                            title="你有新的会议邀请",
                            content=f"会议“{meeting.title}”邀请你参加，开始时间：{notification_data['start_time']}。",
                            related_type="meeting",
                            related_id=meeting.id,
                            payload=participant_data,
                        )
                        
                        await self._send_notification(
                            user_id=participant.user_id,
                            meeting_id=meeting.id,
                            notification_type=MeetingNotificationType.MEETING_INVITATION,
                            data=participant_data,
                            priority=NotificationPriority.HIGH
                        )
            
            logger.info(f"Meeting invitation notifications sent for meeting {meeting.meeting_code}")
            
        except Exception as e:
            logger.error(f"Failed to send meeting invitation notifications: {str(e)}")
    
    async def send_meeting_reminder(self, meeting: Meeting, reminder_type: MeetingNotificationType):
        """
        发送会议提醒通知
        
        Args:
            meeting: 会议对象
            reminder_type: 提醒类型（15分钟前、1小时前等）
        """
        try:
            # 获取参与者列表
            participants = await self._get_meeting_participants(meeting.id)
            
            # 构建通知数据
            notification_data = {
                "meeting_id": meeting.id,
                "meeting_code": meeting.meeting_code,
                "meeting_title": meeting.title,
                "start_time": meeting.scheduled_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "meeting_url": f"/meetings/{meeting.meeting_code}/join"
            }
            
            # 确定优先级
            priority_map = {
                MeetingNotificationType.MEETING_REMINDER_15MIN: NotificationPriority.URGENT,
                MeetingNotificationType.MEETING_REMINDER_1HOUR: NotificationPriority.HIGH,
                MeetingNotificationType.MEETING_REMINDER_1DAY: NotificationPriority.MEDIUM
            }
            priority = priority_map.get(reminder_type, NotificationPriority.MEDIUM)
            
            # 为每个参与者发送提醒
            for participant in participants:
                if participant.invitation_status == InvitationStatus.ACCEPTED:
                    user = await self._get_user_by_id(participant.user_id)
                    if user:
                        participant_data = {
                            **notification_data,
                            "participant_name": user.username
                        }
                        
                        await self._send_notification(
                            user_id=participant.user_id,
                            meeting_id=meeting.id,
                            notification_type=reminder_type,
                            data=participant_data,
                            priority=priority
                        )
            
            logger.info(f"Meeting reminder notifications sent for meeting {meeting.meeting_code} ({reminder_type})")
            
        except Exception as e:
            logger.error(f"Failed to send meeting reminder notifications: {str(e)}")
    
    async def send_meeting_change_notification(self, meeting: Meeting, changes: Dict[str, Any]):
        """
        发送会议变更通知
        
        Args:
            meeting: 会议对象
            changes: 变更内容
        """
        try:
            # 获取参与者列表
            participants = await self._get_meeting_participants(meeting.id)
            
            # 构建通知数据
            notification_data = {
                "meeting_id": meeting.id,
                "meeting_code": meeting.meeting_code,
                "meeting_title": meeting.title,
                "changes": changes
            }
            
            # 确定通知类型
            notification_type = MeetingNotificationType.MEETING_UPDATED
            if 'scheduled_start_time' in changes or 'scheduled_end_time' in changes:
                notification_type = MeetingNotificationType.MEETING_TIME_CHANGED
            
            # 为每个参与者发送变更通知
            for participant in participants:
                user = await self._get_user_by_id(participant.user_id)
                if user:
                    participant_data = {
                        **notification_data,
                        "participant_name": user.username
                    }
                    
                    await self._send_notification(
                        user_id=participant.user_id,
                        meeting_id=meeting.id,
                        notification_type=notification_type,
                        data=participant_data,
                        priority=NotificationPriority.HIGH
                    )
            
            logger.info(f"Meeting change notifications sent for meeting {meeting.meeting_code}")
            
        except Exception as e:
            logger.error(f"Failed to send meeting change notifications: {str(e)}")
    
    async def send_meeting_cancellation_notification(self, meeting: Meeting, reason: str = None):
        """
        发送会议取消通知
        
        Args:
            meeting: 会议对象
            reason: 取消原因
        """
        try:
            # 获取参与者列表
            participants = await self._get_meeting_participants(meeting.id)
            
            # 获取取消操作者信息
            cancelled_by_user = await self._get_user_by_id(meeting.updated_by) if meeting.updated_by else None
            cancelled_by_name = cancelled_by_user.username if cancelled_by_user else "系统"
            
            # 构建通知数据
            notification_data = {
                "meeting_id": meeting.id,
                "meeting_code": meeting.meeting_code,
                "meeting_title": meeting.title,
                "reason": reason or "未提供取消原因",
                "cancelled_by": cancelled_by_name,
                "original_start_time": meeting.scheduled_start_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 为每个参与者发送取消通知
            for participant in participants:
                user = await self._get_user_by_id(participant.user_id)
                if user:
                    participant_data = {
                        **notification_data,
                        "participant_name": user.username
                    }
                    
                    await self._send_notification(
                        user_id=participant.user_id,
                        meeting_id=meeting.id,
                        notification_type=MeetingNotificationType.MEETING_CANCELLED,
                        data=participant_data,
                        priority=NotificationPriority.URGENT
                    )
            
            logger.info(f"Meeting cancellation notifications sent for meeting {meeting.meeting_code}")
            
        except Exception as e:
            logger.error(f"Failed to send meeting cancellation notifications: {str(e)}")
    
    async def send_meeting_postponement_notification(self, meeting: Meeting, postponement_info: Dict[str, Any]):
        """
        发送会议延期通知
        
        Args:
            meeting: 会议对象
            postponement_info: 延期信息
        """
        try:
            # 获取参与者列表
            participants = await self._get_meeting_participants(meeting.id)
            
            # 构建通知数据
            notification_data = {
                "meeting_id": meeting.id,
                "meeting_code": meeting.meeting_code,
                "meeting_title": meeting.title,
                "original_start_time": postponement_info.get("original_start_time", ""),
                "new_start_time": postponement_info.get("new_start_time", ""),
                "reason": postponement_info.get("reason", "未提供延期原因")
            }
            
            # 为每个参与者发送延期通知
            for participant in participants:
                user = await self._get_user_by_id(participant.user_id)
                if user:
                    participant_data = {
                        **notification_data,
                        "participant_name": user.username
                    }
                    
                    await self._send_notification(
                        user_id=participant.user_id,
                        meeting_id=meeting.id,
                        notification_type=MeetingNotificationType.MEETING_POSTPONED,
                        data=participant_data,
                        priority=NotificationPriority.HIGH
                    )
            
            logger.info(f"Meeting postponement notifications sent for meeting {meeting.meeting_code}")
            
        except Exception as e:
            logger.error(f"Failed to send meeting postponement notifications: {str(e)}")
    
    async def send_meeting_started_notification(self, meeting: Meeting):
        """
        发送会议开始通知
        
        Args:
            meeting: 会议对象
        """
        try:
            # 获取参与者列表
            participants = await self._get_meeting_participants(meeting.id)
            
            # 构建通知数据
            notification_data = {
                "meeting_id": meeting.id,
                "meeting_code": meeting.meeting_code,
                "meeting_title": meeting.title,
                "meeting_url": f"/meetings/{meeting.meeting_code}/join"
            }
            
            # 为每个参与者发送开始通知
            for participant in participants:
                if participant.invitation_status == InvitationStatus.ACCEPTED:
                    await self._send_notification(
                        user_id=participant.user_id,
                        meeting_id=meeting.id,
                        notification_type=MeetingNotificationType.MEETING_STARTED,
                        data=notification_data,
                        priority=NotificationPriority.HIGH
                    )
            
            logger.info(f"Meeting started notifications sent for meeting {meeting.meeting_code}")
            
        except Exception as e:
            logger.error(f"Failed to send meeting started notifications: {str(e)}")
    
    async def send_meeting_ended_notification(self, meeting: Meeting):
        """
        发送会议结束通知
        
        Args:
            meeting: 会议对象
        """
        try:
            # 获取参与者列表
            participants = await self._get_meeting_participants(meeting.id)
            
            # 构建通知数据
            notification_data = {
                "meeting_id": meeting.id,
                "meeting_code": meeting.meeting_code,
                "meeting_title": meeting.title,
                "duration": meeting.duration_minutes or 0,
                "participant_count": len([p for p in participants if p.attendance_status.value == "JOINED"])
            }
            
            # 为每个参与者发送结束通知
            for participant in participants:
                if participant.attendance_status.value == "JOINED":
                    await self._send_notification(
                        user_id=participant.user_id,
                        meeting_id=meeting.id,
                        notification_type=MeetingNotificationType.MEETING_ENDED,
                        data=notification_data,
                        priority=NotificationPriority.MEDIUM
                    )
            
            logger.info(f"Meeting ended notifications sent for meeting {meeting.meeting_code}")
            
        except Exception as e:
            logger.error(f"Failed to send meeting ended notifications: {str(e)}")
    
    async def schedule_meeting_reminders(self, meeting: Meeting):
        """
        安排会议提醒通知
        
        Args:
            meeting: 会议对象
        """
        try:
            now = datetime.utcnow()
            start_time = meeting.scheduled_start_time
            
            # 安排不同时间的提醒
            reminder_schedules = [
                (MeetingNotificationType.MEETING_REMINDER_1DAY, timedelta(days=1)),
                (MeetingNotificationType.MEETING_REMINDER_1HOUR, timedelta(hours=1)),
                (MeetingNotificationType.MEETING_REMINDER_15MIN, timedelta(minutes=15))
            ]
            
            for reminder_type, advance_time in reminder_schedules:
                reminder_time = start_time - advance_time
                
                # 只安排未来的提醒
                if reminder_time > now:
                    # 这里可以集成任务调度系统（如Celery）来安排定时任务
                    # 暂时记录到队列中，实际应用中应该使用专门的任务调度器
                    logger.info(f"Scheduled {reminder_type} for meeting {meeting.meeting_code} at {reminder_time}")
            
        except Exception as e:
            logger.error(f"Failed to schedule meeting reminders: {str(e)}")
    
    async def _send_notification(self, user_id: int, meeting_id: int, 
                               notification_type: MeetingNotificationType,
                               data: Dict[str, Any], priority: NotificationPriority = NotificationPriority.MEDIUM,
                               scheduled_at: Optional[datetime] = None):
        """
        发送通知
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            notification_type: 通知类型
            data: 通知数据
            priority: 优先级
            scheduled_at: 计划发送时间
        """
        try:
            # 获取用户偏好
            preferences = await self._get_user_preferences(user_id, notification_type)
            
            if not preferences.enabled:
                return
            
            # 检查免打扰时间
            if self._is_quiet_hours(preferences):
                scheduled_at = self._calculate_next_send_time(preferences)
            
            # 为每个渠道创建通知记录
            for channel in preferences.channels:
                await self._create_notification_record(
                    user_id=user_id,
                    meeting_id=meeting_id,
                    notification_type=notification_type,
                    channel=channel,
                    priority=priority,
                    data=data,
                    scheduled_at=scheduled_at or datetime.utcnow()
                )
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def _create_notification_record(self, user_id: int, meeting_id: int,
                                        notification_type: MeetingNotificationType,
                                        channel: NotificationChannel,
                                        priority: NotificationPriority,
                                        data: Dict[str, Any],
                                        scheduled_at: datetime):
        """
        创建通知记录
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            notification_type: 通知类型
            channel: 通知渠道
            priority: 优先级
            data: 通知数据
            scheduled_at: 计划发送时间
        """
        try:
            # 获取模板
            template = self._get_template(notification_type, channel)
            if not template:
                logger.warning(f"No template found for {notification_type} on {channel}")
                return
            
            # 渲染通知内容
            title = self._render_template(template.title_template, data)
            content = self._render_template(template.content_template, data)
            
            # 创建通知记录
            notification = NotificationRecord(
                id=f"{user_id}_{meeting_id}_{notification_type}_{channel}_{int(datetime.utcnow().timestamp())}",
                user_id=user_id,
                meeting_id=meeting_id,
                notification_type=notification_type,
                channel=channel,
                priority=priority,
                title=title,
                content=content,
                data=data,
                scheduled_at=scheduled_at
            )
            
            # 添加到队列
            self.notification_queue.append(notification)
            
            # 如果是立即发送，直接处理
            if scheduled_at <= datetime.utcnow():
                await self._process_notification(notification)
            
            logger.debug(f"Created notification for user {user_id}: {notification_type} via {channel}")
            
        except Exception as e:
            logger.error(f"Error creating notification record: {e}")
    
    async def _process_notification(self, notification: NotificationRecord):
        """
        处理通知
        
        Args:
            notification: 通知记录
        """
        try:
            if notification.channel == NotificationChannel.WEBSOCKET:
                await self._send_websocket_notification(notification)
            elif notification.channel == NotificationChannel.EMAIL:
                await self._send_email_notification(notification)
            elif notification.channel == NotificationChannel.SMS:
                await self._send_sms_notification(notification)
            elif notification.channel == NotificationChannel.IN_APP:
                await self._send_in_app_notification(notification)
            elif notification.channel == NotificationChannel.PUSH:
                await self._send_push_notification(notification)
            
            # 更新状态
            notification.sent_at = datetime.utcnow()
            
            # 添加到历史记录
            self.notification_history.append(notification)
            
            # 从队列中移除
            if notification in self.notification_queue:
                self.notification_queue.remove(notification)
            
            logger.debug(f"Processed notification {notification.id} for user {notification.user_id}")
            
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            
            # 更新错误状态
            notification.error_message = str(e)
            notification.retry_count += 1
            
            # 如果还有重试次数，重新加入队列
            if notification.retry_count < notification.max_retries:
                notification.scheduled_at = datetime.utcnow() + timedelta(minutes=5 * notification.retry_count)
                if notification not in self.notification_queue:
                    self.notification_queue.append(notification)
    
    async def _send_websocket_notification(self, notification: NotificationRecord):
        """发送WebSocket通知"""
        try:
            # 构建WebSocket消息
            message = WSMessage(
                type=WSMessageType.NOTIFICATION,
                data={
                    "notification_id": notification.id,
                    "meeting_id": notification.meeting_id,
                    "notification_type": notification.notification_type,
                    "title": notification.title,
                    "content": notification.content,
                    "priority": notification.priority,
                    "data": notification.data or {}
                },
                timestamp=datetime.utcnow().isoformat()
            )
            
            await websocket_service.connection_manager.send_to_user(notification.user_id, message)
            
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")
            raise
    
    async def _send_email_notification(self, notification: NotificationRecord):
        """发送邮件通知"""
        try:
            if not self.email_service:
                logger.warning("Email service not configured")
                return
            
            # 获取用户邮箱
            user = await self._get_user_by_id(notification.user_id)
            if not user or not user.email:
                logger.warning(f"No email address for user {notification.user_id}")
                return
            
            # 发送邮件
            success = await self.email_service.send_email(
                to=[user.email],
                subject=notification.title,
                body=notification.content,
                is_html=True
            )
            
            if not success:
                raise Exception("Email sending failed")
            
            logger.info(f"Email notification sent to user {notification.user_id}: {notification.title}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            raise
    
    async def _send_sms_notification(self, notification: NotificationRecord):
        """发送短信通知"""
        try:
            # TODO: 实现短信发送逻辑
            # 这里可以集成短信服务，如阿里云短信、腾讯云短信等
            logger.info(f"SMS notification sent to user {notification.user_id}: {notification.title}")
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
            raise
    
    async def _send_in_app_notification(self, notification: NotificationRecord):
        """发送应用内通知"""
        try:
            # TODO: 实现应用内通知逻辑
            # 这里可以将通知保存到数据库，供前端查询
            logger.info(f"In-app notification sent to user {notification.user_id}: {notification.title}")
            
        except Exception as e:
            logger.error(f"Error sending in-app notification: {e}")
            raise
    
    async def _send_push_notification(self, notification: NotificationRecord):
        """发送推送通知"""
        try:
            # TODO: 实现推送通知逻辑
            # 这里可以集成推送服务，如Firebase、极光推送等
            logger.info(f"Push notification sent to user {notification.user_id}: {notification.title}")
            
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            raise
    
    def _get_template(self, notification_type: MeetingNotificationType, 
                     channel: NotificationChannel) -> Optional[NotificationTemplate]:
        """获取通知模板"""
        key = (notification_type, channel)
        return self.notification_templates.get(key)
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            return template.format(**data)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return template
    
    async def _get_user_preferences(self, user_id: int, 
                                  notification_type: MeetingNotificationType) -> NotificationPreference:
        """获取用户通知偏好"""
        if user_id in self.notification_preferences:
            user_prefs = self.notification_preferences[user_id]
            if notification_type in user_prefs:
                return user_prefs[notification_type]
        
        # 返回默认偏好
        return self._get_default_preference(user_id, notification_type)
    
    def _get_default_preference(self, user_id: int, 
                              notification_type: MeetingNotificationType) -> NotificationPreference:
        """获取默认通知偏好"""
        # 根据通知类型设置默认渠道
        if notification_type in [
            MeetingNotificationType.MEETING_INVITATION,
            MeetingNotificationType.MEETING_REMINDER_1DAY,
            MeetingNotificationType.MEETING_POSTPONED,
            MeetingNotificationType.MEETING_CANCELLED
        ]:
            # 重要通知使用多渠道
            channels = [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL]
        elif notification_type in [
            MeetingNotificationType.MEETING_REMINDER_15MIN,
            MeetingNotificationType.MEETING_REMINDER_1HOUR,
            MeetingNotificationType.MEETING_STARTED
        ]:
            # 紧急提醒使用实时通知
            channels = [NotificationChannel.WEBSOCKET, NotificationChannel.PUSH]
        else:
            # 一般通知只使用WebSocket
            channels = [NotificationChannel.WEBSOCKET]
        
        return NotificationPreference(
            user_id=user_id,
            notification_type=notification_type,
            channels=channels,
            enabled=True
        )
    
    def _is_quiet_hours(self, preference: NotificationPreference) -> bool:
        """检查是否在免打扰时间"""
        if not preference.quiet_hours_start or not preference.quiet_hours_end:
            return False
        
        try:
            now = datetime.now().time()
            start_time = datetime.strptime(preference.quiet_hours_start, "%H:%M").time()
            end_time = datetime.strptime(preference.quiet_hours_end, "%H:%M").time()
            
            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                # 跨天的情况
                return now >= start_time or now <= end_time
                
        except Exception as e:
            logger.error(f"Error checking quiet hours: {e}")
            return False
    
    def _calculate_next_send_time(self, preference: NotificationPreference) -> datetime:
        """计算下次发送时间"""
        try:
            if not preference.quiet_hours_end:
                return datetime.utcnow()
            
            end_time = datetime.strptime(preference.quiet_hours_end, "%H:%M").time()
            now = datetime.now()
            
            # 计算今天的免打扰结束时间
            next_send = datetime.combine(now.date(), end_time)
            
            # 如果已经过了今天的结束时间，设置为明天的结束时间
            if next_send <= now:
                next_send += timedelta(days=1)
            
            return next_send
            
        except Exception as e:
            logger.error(f"Error calculating next send time: {e}")
            return datetime.utcnow()
    
    def _format_agenda(self, agenda: Optional[Dict[str, Any]]) -> str:
        """格式化会议议程"""
        if not agenda:
            return "无议程"
        
        try:
            if isinstance(agenda, dict) and 'items' in agenda:
                items = agenda['items']
                if isinstance(items, list):
                    formatted_items = []
                    for i, item in enumerate(items, 1):
                        if isinstance(item, dict):
                            title = item.get('title', f'议程项目 {i}')
                            duration = item.get('duration', '')
                            if duration:
                                formatted_items.append(f"{i}. {title} ({duration}分钟)")
                            else:
                                formatted_items.append(f"{i}. {title}")
                        else:
                            formatted_items.append(f"{i}. {item}")
                    return "<ol><li>" + "</li><li>".join(formatted_items) + "</li></ol>"
            
            return str(agenda)
            
        except Exception as e:
            logger.error(f"Error formatting agenda: {e}")
            return "议程格式错误"
    
    async def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by id {user_id}: {e}")
            return None
    
    async def _get_meeting_participants(self, meeting_id: int) -> List[MeetingParticipant]:
        """获取会议参与者列表"""
        try:
            query = select(MeetingParticipant).where(MeetingParticipant.meeting_id == meeting_id)
            result = await self.db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting meeting participants for meeting {meeting_id}: {e}")
            return []
    
    # 公共接口方法
    async def set_user_notification_preferences(self, user_id: int, 
                                              preferences: List[NotificationPreference]):
        """设置用户通知偏好"""
        try:
            if user_id not in self.notification_preferences:
                self.notification_preferences[user_id] = {}
            
            for pref in preferences:
                self.notification_preferences[user_id][pref.notification_type] = pref
            
            logger.info(f"Updated notification preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error setting user preferences: {e}")
    
    async def get_user_notification_preferences(self, user_id: int) -> List[NotificationPreference]:
        """获取用户通知偏好"""
        try:
            if user_id not in self.notification_preferences:
                # 返回默认偏好
                default_prefs = []
                for notification_type in MeetingNotificationType:
                    default_prefs.append(self._get_default_preference(user_id, notification_type))
                return default_prefs
            
            return list(self.notification_preferences[user_id].values())
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return []
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """获取通知统计信息"""
        try:
            total_notifications = len(self.notification_history)
            pending_notifications = len(self.notification_queue)
            
            # 按类型统计
            type_stats = {}
            for notification in self.notification_history:
                notification_type = notification.notification_type
                if notification_type not in type_stats:
                    type_stats[notification_type] = 0
                type_stats[notification_type] += 1
            
            # 按渠道统计
            channel_stats = {}
            for notification in self.notification_history:
                channel = notification.channel
                if channel not in channel_stats:
                    channel_stats[channel] = 0
                channel_stats[channel] += 1
            
            return {
                "total_notifications": total_notifications,
                "pending_notifications": pending_notifications,
                "type_stats": type_stats,
                "channel_stats": channel_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {}
