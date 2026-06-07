"""
In-app notification API.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.auth import get_current_user
from ...core.database import get_async_session
from ...models.user import User
from ...services.system_notification_service import SystemNotificationService


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    sender_id: int | None = None
    category: str
    title: str
    content: str | None = None
    related_type: str | None = None
    related_id: int | None = None
    payload: dict | None = None
    is_read: bool
    read_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class NotificationListResponse(BaseModel):
    success: bool = True
    notifications: List[NotificationResponse] = Field(default_factory=list)
    unread_count: int = 0


class UnreadCountResponse(BaseModel):
    success: bool = True
    count: int = 0


class MarkReadResponse(BaseModel):
    success: bool = True
    count: int = 0


router = APIRouter()


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = SystemNotificationService(db)
    notifications = await service.list_notifications(
        current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    unread_count = await service.unread_count(current_user.id)
    return NotificationListResponse(
        notifications=[NotificationResponse(**item.to_dict()) for item in notifications],
        unread_count=unread_count,
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = SystemNotificationService(db)
    return UnreadCountResponse(count=await service.unread_count(current_user.id))


@router.patch("/notifications/{notification_id}/read", response_model=MarkReadResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = SystemNotificationService(db)
    notification = await service.mark_read(current_user.id, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    return MarkReadResponse(count=1)


@router.patch("/notifications/read-all", response_model=MarkReadResponse)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    service = SystemNotificationService(db)
    return MarkReadResponse(count=await service.mark_all_read(current_user.id))
