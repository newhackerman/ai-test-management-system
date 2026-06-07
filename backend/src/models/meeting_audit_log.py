"""
会议审计日志模型

记录会议相关的所有操作和访问日志，用于安全审计和合规管理
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from src.models.base import Base


class MeetingAuditLog(Base):
    """会议审计日志模型"""
    
    __tablename__ = 'meeting_audit_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey('meetings.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)  # 可为空，支持系统操作
    action = Column(String(100), nullable=False, index=True)  # 操作类型
    ip_address = Column(String(45), nullable=True)  # 支持IPv6
    user_agent = Column(Text, nullable=True)  # 用户代理字符串
    additional_data = Column(JSON, nullable=True)  # 额外的操作数据
    timestamp = Column(DateTime, nullable=False, default=datetime.now, index=True)
    
    # 关联关系
    meeting = relationship("Meeting", back_populates="audit_logs")
    user = relationship("User", back_populates="meeting_audit_logs")
    
    def __repr__(self):
        return f"<MeetingAuditLog(id={self.id}, meeting_id={self.meeting_id}, action='{self.action}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'user_id': self.user_id,
            'action': self.action,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'additional_data': self.additional_data,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def create_log(
        cls,
        meeting_id: int,
        action: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> 'MeetingAuditLog':
        """创建审计日志记录"""
        return cls(
            meeting_id=meeting_id,
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data=additional_data or {},
            timestamp=datetime.now()
        )