"""
需求管理通知服务
支持多渠道通知、个性化设置、通知历史管理等功能
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Union
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..models.requirement import Requirement
from ..models.requirement import RequirementReview
from ..models.requirement import RequirementChangeRequest
from ..models.user import User
from .requirement_websocket_service import requirement_websocket_service, RequirementWSMessageType
from .websocket_service import websocket_service, WSMessage


logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """通知渠道"""
    WEBSOCKET = "websocket"      # WebSocket实时通知
    EMAIL = "email"              # 邮件通知
    SMS = "sms"                  # 短信通知
    IN_APP = "in_app"           # 应用内通知
    WEBHOOK = "webhook"          # Webhook通知


class NotificationType(str, Enum):
    """通知类型"""
    # 需求相关
    REQUIREMENT_CREATED = "requirement_created"
    REQUIREMENT_UPDATED = "requirement_updated"
    REQUIREMENT_STATUS_CHANGED = "requirement_status_changed"
    REQUIREMENT_ASSIGNED = "requirement_assigned"
    REQUIREMENT_DUE_SOON = "requirement_due_soon"
    REQUIREMENT_OVERDUE = "requirement_overdue"
    
    # 评审相关
    REVIEW_ASSIGNED = "review_assigned"
    REVIEW_STARTED = "review_started"
    REVIEW_COMMENT_ADDED = "review_comment_added"
    REVIEW_COMPLETED = "review_completed"
    REVIEW_DUE_SOON = "review_due_soon"
    REVIEW_OVERDUE = "review_overdue"
    
    # 变更相关
    CHANGE_REQUEST_CREATED = "change_request_created"
    CHANGE_REQUEST_APPROVED = "change_request_approved"
    CHANGE_REQUEST_REJECTED = "change_request_rejected"
    CHANGE_REQUEST_IMPLEMENTED = "change_request_implemented"
    
    # 系统相关
    SYSTEM_MAINTENANCE = "system_maintenance"
    SYSTEM_UPDATE = "system_update"
    
    # 提醒相关
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_REPORT = "weekly_report"
    DEADLINE_REMINDER = "deadline_reminder"


class NotificationPriority(str, Enum):
    """通知优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"      # 待发送
    SENT = "sent"           # 已发送
    DELIVERED = "delivered"  # 已送达
    READ = "read"           # 已读
    FAILED = "failed"       # 发送失败
    CANCELLED = "cancelled"  # 已取消


class NotificationPreference(BaseModel):
    """通知偏好设置"""
    user_id: int
    notification_type: NotificationType
    channels: List[NotificationChannel] = Field(default_factory=list)
    enabled: bool = True
    quiet_hours_start: Optional[str] = None  # 免打扰开始时间，格式：HH:MM
    quiet_hours_end: Optional[str] = None    # 免打扰结束时间，格式：HH:MM
    frequency: str = "immediate"  # immediate, hourly, daily, weekly
    
    class Config:
        use_enum_values = True


class NotificationTemplate(BaseModel):
    """通知模板"""
    notification_type: NotificationType
    channel: NotificationChannel
    title_template: str
    content_template: str
    variables: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class NotificationRecord(BaseModel):
    """通知记录"""
    id: Optional[int] = None
    user_id: int
    notification_type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority
    title: str
    content: str
    data: Optional[Dict[str, Any]] = None
    status: NotificationStatus = NotificationStatus.PENDING
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class RequirementNotificationService:
    """需求通知服务"""
    
    def __init__(self):
        self.notification_preferences: Dict[int, Dict[NotificationType, NotificationPreference]] = {}
        self.notification_templates: Dict[tuple, NotificationTemplate] = {}
        self.notification_queue: List[NotificationRecord] = []
        self.notification_history: List[NotificationRecord] = []
        
        # 初始化默认模板
        self._init_default_templates()
        
        # 启动后台任务
        self._background_tasks = []
        self._start_background_tasks()
    
    def _init_default_templates(self):
        """初始化默认通知模板"""
        templates = [
            # 需求相关模板
            NotificationTemplate(
                notification_type=NotificationType.REQUIREMENT_CREATED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="新需求创建",
                content_template="需求 {requirement_code} - {title} 已创建",
                variables=["requirement_code", "title", "creator_name"]
            ),
            NotificationTemplate(
                notification_type=NotificationType.REQUIREMENT_STATUS_CHANGED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="需求状态变更",
                content_template="需求 {requirement_code} 状态从 {old_status} 变更为 {new_status}",
                variables=["requirement_code", "old_status", "new_status", "changed_by"]
            ),
            NotificationTemplate(
                notification_type=NotificationType.REQUIREMENT_ASSIGNED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="需求分配",
                content_template="需求 {requirement_code} - {title} 已分配给您",
                variables=["requirement_code", "title", "assigned_by"]
            ),
            NotificationTemplate(
                notification_type=NotificationType.REQUIREMENT_DUE_SOON,
                channel=NotificationChannel.WEBSOCKET,
                title_template="需求即将到期",
                content_template="需求 {requirement_code} 将在 {days_left} 天后到期",
                variables=["requirement_code", "title", "due_date", "days_left"]
            ),
            
            # 评审相关模板
            NotificationTemplate(
                notification_type=NotificationType.REVIEW_ASSIGNED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="评审任务分配",
                content_template="您被指定为需求 {requirement_code} 的评审人",
                variables=["requirement_code", "review_title", "moderator_name"]
            ),
            NotificationTemplate(
                notification_type=NotificationType.REVIEW_STARTED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="评审开始",
                content_template="需求 {requirement_code} 的评审已开始",
                variables=["requirement_code", "review_title", "moderator_name"]
            ),
            NotificationTemplate(
                notification_type=NotificationType.REVIEW_COMMENT_ADDED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="新评审意见",
                content_template="需求 {requirement_code} 收到新的评审意见",
                variables=["requirement_code", "reviewer_name", "comment_type"]
            ),
            
            # 变更相关模板
            NotificationTemplate(
                notification_type=NotificationType.CHANGE_REQUEST_CREATED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="变更请求创建",
                content_template="需求 {requirement_code} 创建了新的变更请求",
                variables=["requirement_code", "change_title", "requestor_name"]
            ),
            NotificationTemplate(
                notification_type=NotificationType.CHANGE_REQUEST_APPROVED,
                channel=NotificationChannel.WEBSOCKET,
                title_template="变更请求批准",
                content_template="变更请求 {change_code} 已被批准",
                variables=["change_code", "change_title", "approver_name"]
            ),
            
            # 邮件模板
            NotificationTemplate(
                notification_type=NotificationType.REQUIREMENT_ASSIGNED,
                channel=NotificationChannel.EMAIL,
                title_template="需求分配通知 - {requirement_code}",
                content_template="""
                尊敬的 {assignee_name}，
                
                您好！需求 {requirement_code} - {title} 已分配给您。
                
                需求详情：
                - 需求编码：{requirement_code}
                - 需求标题：{title}
                - 优先级：{priority}
                - 计划完成时间：{planned_end_date}
                - 分配人：{assigned_by}
                
                请及时查看并处理该需求。
                
                此致
                需求管理系统
                """,
                variables=["assignee_name", "requirement_code", "title", "priority", "planned_end_date", "assigned_by"]
            )
        ]
        
        for template in templates:
            key = (template.notification_type, template.channel)
            self.notification_templates[key] = template
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 这里可以启动定时任务，如发送队列中的通知、清理过期通知等
        pass
    
    async def set_user_preferences(self, user_id: int, preferences: List[NotificationPreference]):
        """设置用户通知偏好"""
        try:
            if user_id not in self.notification_preferences:
                self.notification_preferences[user_id] = {}
            
            for pref in preferences:
                self.notification_preferences[user_id][pref.notification_type] = pref
            
            logger.info(f"Updated notification preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error setting user preferences: {e}")
    
    async def get_user_preferences(self, user_id: int) -> List[NotificationPreference]:
        """获取用户通知偏好"""
        try:
            if user_id not in self.notification_preferences:
                return self._get_default_preferences(user_id)
            
            return list(self.notification_preferences[user_id].values())
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return []
    
    def _get_default_preferences(self, user_id: int) -> List[NotificationPreference]:
        """获取默认通知偏好"""
        default_preferences = []
        
        # 为每种通知类型创建默认偏好
        for notification_type in NotificationType:
            # 根据通知类型设置默认渠道
            if notification_type in [
                NotificationType.REQUIREMENT_ASSIGNED,
                NotificationType.REVIEW_ASSIGNED,
                NotificationType.CHANGE_REQUEST_APPROVED
            ]:
                # 重要通知使用多渠道
                channels = [NotificationChannel.WEBSOCKET, NotificationChannel.IN_APP]
            else:
                # 一般通知只使用WebSocket
                channels = [NotificationChannel.WEBSOCKET]
            
            pref = NotificationPreference(
                user_id=user_id,
                notification_type=notification_type,
                channels=channels,
                enabled=True,
                frequency="immediate"
            )
            default_preferences.append(pref)
        
        return default_preferences
    
    async def send_notification(
        self,
        user_ids: Union[int, List[int]],
        notification_type: NotificationType,
        data: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        scheduled_at: Optional[datetime] = None
    ):
        """发送通知"""
        try:
            if isinstance(user_ids, int):
                user_ids = [user_ids]
            
            for user_id in user_ids:
                # 获取用户偏好
                preferences = await self.get_user_preferences(user_id)
                user_pref = None
                
                for pref in preferences:
                    if pref.notification_type == notification_type:
                        user_pref = pref
                        break
                
                if not user_pref or not user_pref.enabled:
                    continue
                
                # 检查免打扰时间
                if self._is_quiet_hours(user_pref):
                    # 延迟到免打扰时间结束后发送
                    scheduled_at = self._calculate_next_send_time(user_pref)
                
                # 为每个渠道创建通知记录
                for channel in user_pref.channels:
                    await self._create_notification_record(
                        user_id, notification_type, channel, priority, data, scheduled_at
                    )
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def _create_notification_record(
        self,
        user_id: int,
        notification_type: NotificationType,
        channel: NotificationChannel,
        priority: NotificationPriority,
        data: Dict[str, Any],
        scheduled_at: Optional[datetime] = None
    ):
        """创建通知记录"""
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
                user_id=user_id,
                notification_type=notification_type,
                channel=channel,
                priority=priority,
                title=title,
                content=content,
                data=data,
                scheduled_at=scheduled_at or datetime.utcnow()
            )
            
            # 添加到队列
            self.notification_queue.append(notification)
            
            # 如果是立即发送，直接处理
            if not scheduled_at or scheduled_at <= datetime.utcnow():
                await self._process_notification(notification)
            
            logger.debug(f"Created notification for user {user_id}: {notification_type} via {channel}")
            
        except Exception as e:
            logger.error(f"Error creating notification record: {e}")
    
    def _get_template(self, notification_type: NotificationType, channel: NotificationChannel) -> Optional[NotificationTemplate]:
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
    
    async def _process_notification(self, notification: NotificationRecord):
        """处理通知"""
        try:
            if notification.channel == NotificationChannel.WEBSOCKET:
                await self._send_websocket_notification(notification)
            elif notification.channel == NotificationChannel.EMAIL:
                await self._send_email_notification(notification)
            elif notification.channel == NotificationChannel.SMS:
                await self._send_sms_notification(notification)
            elif notification.channel == NotificationChannel.IN_APP:
                await self._send_in_app_notification(notification)
            elif notification.channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_notification(notification)
            
            # 更新状态
            notification.status = NotificationStatus.SENT
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
            notification.status = NotificationStatus.FAILED
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
            # 转换为WebSocket消息类型
            ws_message_type = self._get_websocket_message_type(notification.notification_type)
            if not ws_message_type:
                ws_message_type = RequirementWSMessageType.NOTIFICATION
            
            # 发送WebSocket消息
            message = WSMessage(
                type=ws_message_type,
                data={
                    "notification_id": notification.id,
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
            # TODO: 实现邮件发送逻辑
            # 这里可以集成邮件服务，如SMTP、SendGrid等
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
    
    async def _send_webhook_notification(self, notification: NotificationRecord):
        """发送Webhook通知"""
        try:
            # TODO: 实现Webhook通知逻辑
            # 这里可以向指定的URL发送HTTP请求
            logger.info(f"Webhook notification sent to user {notification.user_id}: {notification.title}")
            
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            raise
    
    def _get_websocket_message_type(self, notification_type: NotificationType) -> Optional[RequirementWSMessageType]:
        """获取对应的WebSocket消息类型"""
        mapping = {
            NotificationType.REQUIREMENT_CREATED: RequirementWSMessageType.REQUIREMENT_CREATED,
            NotificationType.REQUIREMENT_UPDATED: RequirementWSMessageType.REQUIREMENT_UPDATED,
            NotificationType.REQUIREMENT_STATUS_CHANGED: RequirementWSMessageType.REQUIREMENT_STATUS_CHANGED,
            NotificationType.REVIEW_STARTED: RequirementWSMessageType.REVIEW_STARTED,
            NotificationType.REVIEW_COMMENT_ADDED: RequirementWSMessageType.REVIEW_COMMENT_ADDED,
            NotificationType.REVIEW_COMPLETED: RequirementWSMessageType.REVIEW_COMPLETED,
            NotificationType.CHANGE_REQUEST_CREATED: RequirementWSMessageType.CHANGE_REQUEST_CREATED,
            NotificationType.CHANGE_REQUEST_APPROVED: RequirementWSMessageType.CHANGE_REQUEST_APPROVED,
        }
        return mapping.get(notification_type)
    
    async def send_requirement_notification(self, requirement: Requirement, notification_type: NotificationType, additional_data: Optional[Dict] = None):
        """发送需求相关通知"""
        try:
            data = {
                "requirement_id": requirement.id,
                "requirement_code": requirement.requirement_code,
                "title": requirement.title,
                "status": requirement.status.value,
                "priority": requirement.priority.value,
                "project_id": requirement.project_id,
                **(additional_data or {})
            }
            
            # 确定通知接收者
            recipients = []
            
            if notification_type == NotificationType.REQUIREMENT_ASSIGNED and requirement.assignee_id:
                recipients.append(requirement.assignee_id)
            elif notification_type in [NotificationType.REQUIREMENT_CREATED, NotificationType.REQUIREMENT_UPDATED]:
                # 通知项目相关人员
                # TODO: 从项目中获取相关人员列表
                recipients = [requirement.creator_id]
                if requirement.assignee_id:
                    recipients.append(requirement.assignee_id)
            
            if recipients:
                await self.send_notification(recipients, notification_type, data)
            
        except Exception as e:
            logger.error(f"Error sending requirement notification: {e}")
    
    async def send_review_notification(self, review: RequirementReview, notification_type: NotificationType, additional_data: Optional[Dict] = None):
        """发送评审相关通知"""
        try:
            data = {
                "review_id": review.id,
                "requirement_id": review.requirement_id,
                "review_title": review.title,
                "review_type": review.review_type.value,
                "review_status": review.review_status.value,
                "moderator_id": review.moderator_id,
                **(additional_data or {})
            }
            
            # 确定通知接收者
            recipients = []
            
            if notification_type == NotificationType.REVIEW_ASSIGNED:
                recipients = review.reviewers or []
            elif notification_type in [NotificationType.REVIEW_STARTED, NotificationType.REVIEW_COMPLETED]:
                recipients = [review.moderator_id] + (review.reviewers or [])
            elif notification_type == NotificationType.REVIEW_COMMENT_ADDED:
                # 通知除评论者外的所有参与者
                all_participants = [review.moderator_id] + (review.reviewers or [])
                comment_author = additional_data.get("comment_author_id") if additional_data else None
                recipients = [uid for uid in all_participants if uid != comment_author]
            
            if recipients:
                await self.send_notification(recipients, notification_type, data)
            
        except Exception as e:
            logger.error(f"Error sending review notification: {e}")
    
    async def send_change_request_notification(self, change_request: RequirementChangeRequest, notification_type: NotificationType, additional_data: Optional[Dict] = None):
        """发送变更请求相关通知"""
        try:
            data = {
                "change_request_id": change_request.id,
                "change_request_code": change_request.change_request_code,
                "requirement_id": change_request.requirement_id,
                "change_title": change_request.title,
                "change_type": change_request.change_type.value,
                "change_status": change_request.status.value,
                "requestor_id": change_request.requestor_id,
                **(additional_data or {})
            }
            
            # 确定通知接收者
            recipients = []
            
            if notification_type == NotificationType.CHANGE_REQUEST_CREATED:
                # 通知审批人
                if change_request.approver_id:
                    recipients.append(change_request.approver_id)
            elif notification_type in [NotificationType.CHANGE_REQUEST_APPROVED, NotificationType.CHANGE_REQUEST_REJECTED]:
                # 通知申请人
                recipients.append(change_request.requestor_id)
                # 通知实施人
                if change_request.implementer_id:
                    recipients.append(change_request.implementer_id)
            
            if recipients:
                await self.send_notification(recipients, notification_type, data)
            
        except Exception as e:
            logger.error(f"Error sending change request notification: {e}")
    
    async def send_reminder_notifications(self):
        """发送提醒通知"""
        try:
            # TODO: 实现定期提醒逻辑
            # 1. 检查即将到期的需求
            # 2. 检查逾期的需求
            # 3. 检查即将到期的评审
            # 4. 发送每日/每周摘要
            
            logger.info("Reminder notifications sent")
            
        except Exception as e:
            logger.error(f"Error sending reminder notifications: {e}")
    
    async def mark_notification_as_read(self, notification_id: int, user_id: int):
        """标记通知为已读"""
        try:
            for notification in self.notification_history:
                if notification.id == notification_id and notification.user_id == user_id:
                    notification.status = NotificationStatus.READ
                    notification.read_at = datetime.utcnow()
                    break
            
            logger.debug(f"Marked notification {notification_id} as read for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
    
    async def get_user_notifications(self, user_id: int, limit: int = 50, offset: int = 0) -> List[NotificationRecord]:
        """获取用户通知历史"""
        try:
            user_notifications = [
                n for n in self.notification_history 
                if n.user_id == user_id
            ]
            
            # 按时间倒序排列
            user_notifications.sort(key=lambda x: x.created_at, reverse=True)
            
            return user_notifications[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []
    
    async def get_unread_count(self, user_id: int) -> int:
        """获取用户未读通知数量"""
        try:
            count = sum(
                1 for n in self.notification_history
                if n.user_id == user_id and n.status != NotificationStatus.READ
            )
            return count
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """获取通知统计信息"""
        try:
            total_notifications = len(self.notification_history)
            pending_notifications = len(self.notification_queue)
            
            status_counts = {}
            channel_counts = {}
            type_counts = {}
            
            for notification in self.notification_history:
                # 统计状态
                status = notification.status
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # 统计渠道
                channel = notification.channel
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
                
                # 统计类型
                ntype = notification.notification_type
                type_counts[ntype] = type_counts.get(ntype, 0) + 1
            
            return {
                "total_notifications": total_notifications,
                "pending_notifications": pending_notifications,
                "status_distribution": status_counts,
                "channel_distribution": channel_counts,
                "type_distribution": type_counts,
                "active_users": len(self.notification_preferences)
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {}


# 全局通知服务实例
requirement_notification_service = RequirementNotificationService()