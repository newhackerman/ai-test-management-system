"""
AI聊天会话模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from .base import BaseModel


class SessionStatus(str, Enum):
    """会话状态枚举"""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class AIChatSession(BaseModel):
    """AI聊天会话模型"""
    __tablename__ = "ai_chat_sessions"
    
    # 基本信息
    title = Column(String(200), nullable=False, comment="会话标题")
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="用户ID")
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, comment="会话状态")
    
    # 会话配置
    ai_provider = Column(String(50), nullable=True, comment="AI服务提供商")
    ai_model = Column(String(100), nullable=True, comment="AI模型名称")
    system_prompt = Column(Text, nullable=True, comment="系统提示词")
    
    # 统计信息
    message_count = Column(Integer, default=0, comment="消息数量")
    total_tokens = Column(Integer, default=0, comment="总Token数")
    last_activity_at = Column(DateTime, default=func.now(), comment="最后活动时间")
    
    # 会话元数据
    tags = Column(Text, nullable=True, comment="标签（JSON格式）")
    session_metadata = Column(Text, nullable=True, comment="元数据（JSON格式）")
    
    # 关联关系
    # user = relationship("User", back_populates="ai_chat_sessions")
    messages = relationship("AIChatMessage", back_populates="session", cascade="all, delete-orphan")
    suggestions = relationship("AISuggestion", back_populates="session", cascade="all, delete-orphan")
    requirements_analyses = relationship("AIRequirementsAnalysis", back_populates="session", cascade="all, delete-orphan")
    files = relationship("AIFileStorage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AIChatSession(id={self.id}, title='{self.title}', user_id={self.user_id})>"