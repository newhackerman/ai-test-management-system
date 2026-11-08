"""
AI聊天消息模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from .base import BaseModel


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class ContentType(str, Enum):
    """内容类型枚举"""
    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"
    CODE = "CODE"
    IMAGE = "IMAGE"
    FILE = "FILE"


class AIChatMessage(BaseModel):
    """AI聊天消息模型"""
    __tablename__ = "ai_chat_messages"
    
    # 基本信息
    session_id = Column(BigInteger, ForeignKey("ai_chat_sessions.id"), nullable=False, comment="会话ID")
    role = Column(SQLEnum(MessageRole), nullable=False, comment="消息角色")
    content = Column(Text, nullable=False, comment="消息内容")
    content_type = Column(SQLEnum(ContentType), default=ContentType.TEXT, comment="内容类型")
    
    # AI相关信息
    ai_provider = Column(String(50), nullable=True, comment="AI服务提供商")
    ai_model = Column(String(100), nullable=True, comment="AI模型名称")
    tokens_used = Column(Integer, default=0, comment="使用的Token数")
    confidence_score = Column(Float, nullable=True, comment="置信度分数")
    
    # 消息状态
    is_streaming = Column(Boolean, default=False, comment="是否为流式消息")
    is_error = Column(Boolean, default=False, comment="是否为错误消息")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 消息元数据
    message_metadata = Column(Text, nullable=True, comment="元数据（JSON格式）")
    parent_message_id = Column(BigInteger, ForeignKey("ai_chat_messages.id"), nullable=True, comment="父消息ID")
    
    # 用户交互
    user_rating = Column(Integer, nullable=True, comment="用户评分（1-5）")
    user_feedback = Column(Text, nullable=True, comment="用户反馈")
    is_bookmarked = Column(Boolean, default=False, comment="是否收藏")
    
    # 关联关系
    session = relationship("AIChatSession", back_populates="messages")
    parent_message = relationship("AIChatMessage", remote_side="AIChatMessage.id", backref="child_messages")
    attachments = relationship("AIFileStorage", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AIChatMessage(id={self.id}, session_id={self.session_id}, role='{self.role}')>"