"""
Persistent in-app notifications.
"""
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text

from .base import BaseModel


class SystemNotification(BaseModel):
    """User-scoped in-app notification."""

    __tablename__ = "system_notifications"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="接收用户ID")
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="发送用户ID")
    category = Column(String(40), nullable=False, index=True, comment="通知分类")
    title = Column(String(200), nullable=False, comment="标题")
    content = Column(Text, nullable=True, comment="内容")
    related_type = Column(String(40), nullable=True, index=True, comment="关联对象类型")
    related_id = Column(Integer, nullable=True, index=True, comment="关联对象ID")
    payload = Column(JSON, nullable=True, comment="附加数据")
    is_read = Column(Boolean, default=False, nullable=False, index=True, comment="是否已读")
    read_at = Column(DateTime, nullable=True, comment="已读时间")
    is_deleted = Column(Boolean, default=False, nullable=False, index=True, comment="是否逻辑删除")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")

    __table_args__ = (
        Index("idx_system_notifications_user_read", "user_id", "is_read", "created_at"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    def mark_read(self) -> None:
        self.is_read = True
        self.read_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sender_id": self.sender_id,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "related_type": self.related_type,
            "related_id": self.related_id,
            "payload": self.payload,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
