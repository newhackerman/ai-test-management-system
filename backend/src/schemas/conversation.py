"""
对话管理相关的Pydantic模式
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

from ..models.ai_chat_session import SessionStatus
from ..models.ai_chat_message import MessageRole, ContentType


class ConversationGroupEnum(str, Enum):
    """会话分组枚举"""
    WORK = "work"
    STUDY = "study"
    PROJECT = "project"
    PERSONAL = "personal"
    RESEARCH = "research"
    DEVELOPMENT = "development"
    TESTING = "testing"
    OTHER = "other"


class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    title: Optional[str] = Field(None, description="对话标题", max_length=200)
    ai_provider: Optional[str] = Field(None, description="AI服务提供商", max_length=50)
    ai_model: Optional[str] = Field(None, description="AI模型名称", max_length=100)
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    template_type: Optional[str] = Field(None, description="会话模板类型")
    group: Optional[ConversationGroupEnum] = Field(None, description="会话分组")
    tags: Optional[List[str]] = Field(None, description="会话标签")
    goal: Optional[str] = Field(None, description="会话目标", max_length=500)


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int = Field(..., description="对话ID")
    title: str = Field(..., description="对话标题")
    user_id: int = Field(..., description="用户ID")
    status: SessionStatus = Field(..., description="会话状态")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型名称")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    message_count: int = Field(..., description="消息数量")
    total_tokens: int = Field(..., description="总Token数")
    last_activity_at: datetime = Field(..., description="最后活动时间")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    session_metadata: Optional[Dict[str, Any]] = Field(None, description="会话元数据")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    success: bool = Field(..., description="是否成功")
    conversations: List[ConversationResponse] = Field(..., description="对话列表")
    total_count: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")


class UpdateConversationRequest(BaseModel):
    """更新对话请求"""
    title: Optional[str] = Field(None, description="对话标题", max_length=200)
    ai_provider: Optional[str] = Field(None, description="AI服务提供商", max_length=50)
    ai_model: Optional[str] = Field(None, description="AI模型名称", max_length=100)
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    tags: Optional[List[str]] = Field(None, description="会话标签")
    status: Optional[SessionStatus] = Field(None, description="会话状态")


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., description="消息内容", min_length=1, max_length=50000)
    content_type: ContentType = Field(ContentType.TEXT, description="内容类型")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")


class MessageResponse(BaseModel):
    """消息响应"""
    id: int = Field(..., description="消息ID")
    session_id: int = Field(..., description="会话ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    content_type: ContentType = Field(..., description="内容类型")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型名称")
    tokens_used: int = Field(..., description="使用的Token数")
    confidence_score: Optional[float] = Field(None, description="置信度分数")
    is_streaming: bool = Field(..., description="是否为流式消息")
    is_error: bool = Field(..., description="是否为错误消息")
    error_message: Optional[str] = Field(None, description="错误信息")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")
    parent_message_id: Optional[int] = Field(None, description="父消息ID")
    user_rating: Optional[int] = Field(None, description="用户评分")
    user_feedback: Optional[str] = Field(None, description="用户反馈")
    is_bookmarked: bool = Field(..., description="是否收藏")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """消息列表响应"""
    success: bool = Field(..., description="是否成功")
    messages: List[MessageResponse] = Field(..., description="消息列表")
    total_count: int = Field(..., description="总数量")
    conversation_id: int = Field(..., description="对话ID")


class ConversationStatsResponse(BaseModel):
    """对话统计响应"""
    total_conversations: int = Field(..., description="总对话数")
    active_conversations: int = Field(..., description="活跃对话数")
    archived_conversations: int = Field(..., description="已归档对话数")
    total_messages: int = Field(..., description="总消息数")
    total_tokens: int = Field(..., description="总Token数")
    avg_messages_per_conversation: float = Field(..., description="平均每对话消息数")
    most_used_provider: Optional[str] = Field(None, description="最常用的AI提供商")
    most_used_model: Optional[str] = Field(None, description="最常用的AI模型")


class SearchConversationsRequest(BaseModel):
    """搜索对话请求"""
    query: str = Field(..., description="搜索关键词", min_length=1, max_length=200)
    status: Optional[SessionStatus] = Field(None, description="状态过滤")
    group: Optional[ConversationGroupEnum] = Field(None, description="分组过滤")
    tags: Optional[List[str]] = Field(None, description="标签过滤")
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(20, description="每页大小", ge=1, le=100)


class ConversationContextResponse(BaseModel):
    """对话上下文响应"""
    conversation_id: int = Field(..., description="对话ID")
    messages: List[MessageResponse] = Field(..., description="上下文消息")
    summary: Optional[str] = Field(None, description="对话摘要")
    business_context: Optional[Dict[str, Any]] = Field(None, description="业务上下文")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="用户偏好")
    token_count: int = Field(..., description="上下文Token数")
    compression_strategy: Optional[str] = Field(None, description="压缩策略")