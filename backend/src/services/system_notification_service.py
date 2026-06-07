"""
Persistent in-app notification service.
"""
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.system_notification import SystemNotification


class SystemNotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        *,
        user_id: int,
        title: str,
        content: Optional[str] = None,
        category: str = "system",
        sender_id: Optional[int] = None,
        related_type: Optional[str] = None,
        related_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> SystemNotification:
        notification = SystemNotification(
            user_id=user_id,
            sender_id=sender_id,
            category=category,
            title=title,
            content=content,
            related_type=related_type,
            related_id=related_id,
            payload=payload,
        )
        self.db.add(notification)
        try:
            if commit:
                await self.db.commit()
                await self.db.refresh(notification)
            else:
                await self.db.flush()
        except Exception:
            await self.db.rollback()
            raise
        return notification

    async def create_notifications(
        self,
        user_ids: Iterable[int],
        *,
        title: str,
        content: Optional[str] = None,
        category: str = "system",
        sender_id: Optional[int] = None,
        related_type: Optional[str] = None,
        related_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
        commit: bool = True,
    ) -> List[SystemNotification]:
        unique_user_ids = []
        for user_id in user_ids:
            if user_id and int(user_id) not in unique_user_ids:
                unique_user_ids.append(int(user_id))

        notifications = [
            SystemNotification(
                user_id=user_id,
                sender_id=sender_id,
                category=category,
                title=title,
                content=content,
                related_type=related_type,
                related_id=related_id,
                payload=payload,
            )
            for user_id in unique_user_ids
        ]
        if not notifications:
            return []

        self.db.add_all(notifications)
        try:
            if commit:
                await self.db.commit()
                for notification in notifications:
                    await self.db.refresh(notification)
            else:
                await self.db.flush()
        except Exception:
            await self.db.rollback()
            raise
        return notifications

    async def list_notifications(
        self,
        user_id: int,
        *,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[SystemNotification]:
        query = select(SystemNotification).where(SystemNotification.user_id == user_id)
        if unread_only:
            query = query.where(SystemNotification.is_read.is_(False))
        query = query.order_by(desc(SystemNotification.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def unread_count(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count(SystemNotification.id)).where(
                SystemNotification.user_id == user_id,
                SystemNotification.is_read.is_(False),
            )
        )
        return int(result.scalar() or 0)

    async def mark_read(self, user_id: int, notification_id: int) -> Optional[SystemNotification]:
        result = await self.db.execute(
            select(SystemNotification).where(
                SystemNotification.id == notification_id,
                SystemNotification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return None
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: int) -> int:
        result = await self.db.execute(
            update(SystemNotification)
            .where(SystemNotification.user_id == user_id, SystemNotification.is_read.is_(False))
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.db.commit()
        return int(result.rowcount or 0)
