"""
需求管理通知API端点
提供通知设置、历史查询、状态管理等接口
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from ...core.auth import get_current_user
from ...core.dependencies import get_db
from ...services.requirement_notification_service import (
    requirement_notification_service,
    NotificationPreference,
    NotificationChannel,
    NotificationType,
    NotificationPriority,
    NotificationRecord
)
from ...models.user import User


logger = logging.getLogger(__name__)
router = APIRouter()


class NotificationPreferenceRequest(BaseModel):
    """通知偏好设置请求"""
    notification_type: NotificationType
    channels: List[NotificationChannel]
    enabled: bool = True
    quiet_hours_start: Optional[str] = Field(None, description="免打扰开始时间，格式：HH:MM")
    quiet_hours_end: Optional[str] = Field(None, description="免打扰结束时间，格式：HH:MM")
    frequency: str = Field("immediate", description="通知频率：immediate, hourly, daily, weekly")


class NotificationPreferenceResponse(BaseModel):
    """通知偏好设置响应"""
    user_id: int
    notification_type: NotificationType
    channels: List[NotificationChannel]
    enabled: bool
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    frequency: str


class SendNotificationRequest(BaseModel):
    """发送通知请求"""
    user_ids: List[int]
    notification_type: NotificationType
    title: str
    content: str
    data: Optional[dict] = None
    priority: NotificationPriority = NotificationPriority.MEDIUM
    scheduled_at: Optional[datetime] = None


class NotificationResponse(BaseModel):
    """通知响应"""
    id: Optional[int]
    notification_type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority
    title: str
    content: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime]
    read_at: Optional[datetime]


@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
async def get_notification_preferences(
    current_user: User = Depends(get_current_user)
):
    """
    获取用户通知偏好设置
    
    Returns:
        List[NotificationPreferenceResponse]: 通知偏好列表
    """
    try:
        preferences = await requirement_notification_service.get_user_preferences(current_user.id)
        
        response = []
        for pref in preferences:
            response.append(NotificationPreferenceResponse(
                user_id=pref.user_id,
                notification_type=pref.notification_type,
                channels=pref.channels,
                enabled=pref.enabled,
                quiet_hours_start=pref.quiet_hours_start,
                quiet_hours_end=pref.quiet_hours_end,
                frequency=pref.frequency
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting notification preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification preferences"
        )


@router.put("/preferences")
async def update_notification_preferences(
    preferences: List[NotificationPreferenceRequest],
    current_user: User = Depends(get_current_user)
):
    """
    更新用户通知偏好设置
    
    Args:
        preferences: 通知偏好设置列表
    """
    try:
        # 转换为服务层对象
        service_preferences = []
        for pref in preferences:
            service_pref = NotificationPreference(
                user_id=current_user.id,
                notification_type=pref.notification_type,
                channels=pref.channels,
                enabled=pref.enabled,
                quiet_hours_start=pref.quiet_hours_start,
                quiet_hours_end=pref.quiet_hours_end,
                frequency=pref.frequency
            )
            service_preferences.append(service_pref)
        
        await requirement_notification_service.set_user_preferences(
            current_user.id, 
            service_preferences
        )
        
        return {"message": "Notification preferences updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences"
        )


@router.get("/history", response_model=List[NotificationResponse])
async def get_notification_history(
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户通知历史
    
    Args:
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        List[NotificationResponse]: 通知历史列表
    """
    try:
        notifications = await requirement_notification_service.get_user_notifications(
            current_user.id, limit, offset
        )
        
        response = []
        for notification in notifications:
            response.append(NotificationResponse(
                id=notification.id,
                notification_type=notification.notification_type,
                channel=notification.channel,
                priority=notification.priority,
                title=notification.title,
                content=notification.content,
                status=notification.status,
                created_at=notification.created_at,
                sent_at=notification.sent_at,
                read_at=notification.read_at
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification history"
        )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user)
):
    """
    获取用户未读通知数量
    
    Returns:
        Dict: 未读通知数量
    """
    try:
        count = await requirement_notification_service.get_unread_count(current_user.id)
        
        return {
            "unread_count": count,
            "user_id": current_user.id
        }
        
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get unread count"
        )


@router.post("/mark-read/{notification_id}")
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    标记通知为已读
    
    Args:
        notification_id: 通知ID
    """
    try:
        await requirement_notification_service.mark_notification_as_read(
            notification_id, 
            current_user.id
        )
        
        return {
            "message": "Notification marked as read",
            "notification_id": notification_id
        }
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )


@router.post("/send")
async def send_notification(
    request: SendNotificationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    发送通知（管理员功能）
    
    Args:
        request: 发送通知请求
    """
    try:
        # 检查权限（只有管理员可以发送通知）
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can send notifications"
            )
        
        # 构建通知数据
        data = request.data or {}
        data.update({
            "title": request.title,
            "content": request.content,
            "sender_id": current_user.id,
            "sender_name": current_user.username
        })
        
        await requirement_notification_service.send_notification(
            user_ids=request.user_ids,
            notification_type=request.notification_type,
            data=data,
            priority=request.priority,
            scheduled_at=request.scheduled_at
        )
        
        return {
            "message": "Notification sent successfully",
            "recipient_count": len(request.user_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send notification"
        )


@router.get("/stats")
async def get_notification_stats(
    current_user: User = Depends(get_current_user)
):
    """
    获取通知统计信息（管理员功能）
    
    Returns:
        Dict: 通知统计信息
    """
    try:
        # 检查权限（只有管理员可以查看统计信息）
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view notification statistics"
            )
        
        stats = requirement_notification_service.get_notification_stats()
        
        return {
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification statistics"
        )


@router.get("/channels")
async def get_notification_channels():
    """
    获取可用的通知渠道
    
    Returns:
        List: 通知渠道列表
    """
    try:
        channels = [
            {
                "value": channel.value,
                "label": channel.value.replace("_", " ").title(),
                "description": _get_channel_description(channel)
            }
            for channel in NotificationChannel
        ]
        
        return {"channels": channels}
        
    except Exception as e:
        logger.error(f"Error getting notification channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification channels"
        )


@router.get("/types")
async def get_notification_types():
    """
    获取可用的通知类型
    
    Returns:
        List: 通知类型列表
    """
    try:
        types = [
            {
                "value": ntype.value,
                "label": ntype.value.replace("_", " ").title(),
                "description": _get_type_description(ntype),
                "category": _get_type_category(ntype)
            }
            for ntype in NotificationType
        ]
        
        return {"types": types}
        
    except Exception as e:
        logger.error(f"Error getting notification types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification types"
        )


def _get_channel_description(channel: NotificationChannel) -> str:
    """获取渠道描述"""
    descriptions = {
        NotificationChannel.WEBSOCKET: "实时WebSocket通知",
        NotificationChannel.EMAIL: "邮件通知",
        NotificationChannel.SMS: "短信通知",
        NotificationChannel.IN_APP: "应用内通知",
        NotificationChannel.WEBHOOK: "Webhook通知"
    }
    return descriptions.get(channel, "")


def _get_type_description(ntype: NotificationType) -> str:
    """获取类型描述"""
    descriptions = {
        NotificationType.REQUIREMENT_CREATED: "需求创建时通知",
        NotificationType.REQUIREMENT_UPDATED: "需求更新时通知",
        NotificationType.REQUIREMENT_STATUS_CHANGED: "需求状态变更时通知",
        NotificationType.REQUIREMENT_ASSIGNED: "需求分配时通知",
        NotificationType.REQUIREMENT_DUE_SOON: "需求即将到期时通知",
        NotificationType.REQUIREMENT_OVERDUE: "需求逾期时通知",
        NotificationType.REVIEW_ASSIGNED: "评审任务分配时通知",
        NotificationType.REVIEW_STARTED: "评审开始时通知",
        NotificationType.REVIEW_COMMENT_ADDED: "评审意见添加时通知",
        NotificationType.REVIEW_COMPLETED: "评审完成时通知",
        NotificationType.REVIEW_DUE_SOON: "评审即将到期时通知",
        NotificationType.REVIEW_OVERDUE: "评审逾期时通知",
        NotificationType.CHANGE_REQUEST_CREATED: "变更请求创建时通知",
        NotificationType.CHANGE_REQUEST_APPROVED: "变更请求批准时通知",
        NotificationType.CHANGE_REQUEST_REJECTED: "变更请求拒绝时通知",
        NotificationType.CHANGE_REQUEST_IMPLEMENTED: "变更请求实施时通知",
        NotificationType.SYSTEM_MAINTENANCE: "系统维护通知",
        NotificationType.SYSTEM_UPDATE: "系统更新通知",
        NotificationType.DAILY_SUMMARY: "每日摘要通知",
        NotificationType.WEEKLY_REPORT: "每周报告通知",
        NotificationType.DEADLINE_REMINDER: "截止日期提醒通知"
    }
    return descriptions.get(ntype, "")


def _get_type_category(ntype: NotificationType) -> str:
    """获取类型分类"""
    if ntype.value.startswith("requirement_"):
        return "需求相关"
    elif ntype.value.startswith("review_"):
        return "评审相关"
    elif ntype.value.startswith("change_"):
        return "变更相关"
    elif ntype.value.startswith("system_"):
        return "系统相关"
    else:
        return "其他"