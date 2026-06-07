"""
需求协作讨论相关的Pydantic模式定义

定义需求协作讨论API的请求和响应模式
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class DiscussionStatusEnum(str, Enum):
    """讨论状态枚举"""
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class MessageTypeEnum(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    CODE = "code"
    SUMMARY = "summary"
    DECISION = "decision"
    ACTION_ITEM = "action_item"


# 请求模式

class CreateDiscussionRequest(BaseModel):
    """创建讨论请求"""
    requirement_id: int = Field(..., description="需求ID")
    topic: str = Field(..., min_length=3, max_length=200, description="讨论主题")
    description: Optional[str] = Field(None, max_length=2000, description="讨论描述")
    participants: Optional[List[int]] = Field(default_factory=list, description="参与者ID列表")
    is_private: bool = Field(False, description="是否私有讨论")
    tags: Optional[List[str]] = Field(default_factory=list, description="讨论标签")

    @validator('topic')
    def validate_topic(cls, v):
        if not v.strip():
            raise ValueError("讨论主题不能为空")
        return v.strip()


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    discussion_id: int = Field(..., description="讨论ID")
    content: str = Field(..., min_length=1, max_length=5000, description="消息内容")
    message_type: MessageTypeEnum = Field(MessageTypeEnum.TEXT, description="消息类型")
    attachments: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="附件列表")
    reply_to_id: Optional[int] = Field(None, description="回复的消息ID")
    mentions: Optional[List[int]] = Field(default_factory=list, description="@提及的用户ID列表")

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError("消息内容不能为空")
        return v.strip()


class UpdateMessageRequest(BaseModel):
    """更新消息请求"""
    content: str = Field(..., min_length=1, max_length=5000, description="新的消息内容")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")


class AddParticipantRequest(BaseModel):
    """添加参与者请求"""
    participant_id: int = Field(..., description="参与者ID")
    role: Optional[str] = Field("participant", description="参与者角色")


class RemoveParticipantRequest(BaseModel):
    """移除参与者请求"""
    participant_id: int = Field(..., description="参与者ID")
    reason: Optional[str] = Field(None, max_length=200, description="移除原因")


class CloseDiscussionRequest(BaseModel):
    """关闭讨论请求"""
    summary: str = Field(..., min_length=10, max_length=2000, description="讨论总结")
    action_items: Optional[List[str]] = Field(default_factory=list, description="行动项列表")
    decisions: Optional[List[str]] = Field(default_factory=list, description="决策列表")
    archive_to_knowledge_base: bool = Field(True, description="是否归档到知识库")


class ReopenDiscussionRequest(BaseModel):
    """重新打开讨论请求"""
    reason: str = Field(..., min_length=5, max_length=500, description="重新打开原因")


# 响应模式

class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    discussion_id: int
    sender_id: int
    message_type: MessageTypeEnum
    content: str
    attachments: List[Dict[str, Any]]
    reply_to_id: Optional[int]
    mentions: List[int]
    is_edited: bool = False
    edited_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiscussionResponse(BaseModel):
    """讨论响应"""
    id: int
    requirement_id: int
    topic: str
    description: Optional[str]
    creator_id: int
    participants: List[int]
    status: DiscussionStatusEnum
    is_private: bool
    tags: List[str]
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiscussionWithMessagesResponse(BaseModel):
    """带消息的讨论响应"""
    discussion: DiscussionResponse
    messages: List[MessageResponse]
    participants_info: Dict[int, Dict[str, Any]]  # 参与者信息
    statistics: Dict[str, Any]


class DiscussionListResponse(BaseModel):
    """讨论列表响应"""
    discussions: List[DiscussionResponse]
    total: int
    skip: int
    limit: int


class MessageListResponse(BaseModel):
    """消息列表响应"""
    messages: List[MessageResponse]
    total: int
    skip: int
    limit: int
    has_more: bool


class DiscussionStatisticsResponse(BaseModel):
    """讨论统计响应"""
    total_discussions: int
    active_discussions: int
    closed_discussions: int
    total_messages: int
    average_messages_per_discussion: float
    most_active_discussions: List[Dict[str, Any]]
    generated_at: str


# 查询参数模式

class DiscussionQueryParams(BaseModel):
    """讨论查询参数"""
    requirement_id: Optional[int] = Field(None, description="需求ID")
    project_id: Optional[int] = Field(None, description="项目ID")
    status: Optional[DiscussionStatusEnum] = Field(None, description="讨论状态")
    creator_id: Optional[int] = Field(None, description="创建者ID")
    participant_id: Optional[int] = Field(None, description="参与者ID")
    keyword: Optional[str] = Field(None, min_length=2, description="关键词搜索")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(20, ge=1, le=100, description="限制数量")
    sort_by: str = Field("updated_at", pattern="^(created_at|updated_at|message_count)$", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序顺序")


class MessageQueryParams(BaseModel):
    """消息查询参数"""
    discussion_id: int = Field(..., description="讨论ID")
    sender_id: Optional[int] = Field(None, description="发送者ID")
    message_type: Optional[MessageTypeEnum] = Field(None, description="消息类型")
    keyword: Optional[str] = Field(None, min_length=2, description="关键词搜索")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(50, ge=1, le=100, description="限制数量")
    include_replies: bool = Field(True, description="是否包含回复")


# 实时通信模式

class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: str = Field(..., description="消息类型")
    discussion_id: Optional[int] = Field(None, description="讨论ID")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")


class TypingIndicator(BaseModel):
    """输入指示器"""
    discussion_id: int = Field(..., description="讨论ID")
    user_id: int = Field(..., description="用户ID")
    is_typing: bool = Field(..., description="是否正在输入")


class OnlineStatus(BaseModel):
    """在线状态"""
    user_id: int = Field(..., description="用户ID")
    is_online: bool = Field(..., description="是否在线")
    last_seen: Optional[datetime] = Field(None, description="最后在线时间")


# 知识管理模式

class DiscussionSummaryRequest(BaseModel):
    """讨论总结请求"""
    discussion_id: int = Field(..., description="讨论ID")
    include_decisions: bool = Field(True, description="是否包含决策")
    include_action_items: bool = Field(True, description="是否包含行动项")
    include_key_points: bool = Field(True, description="是否包含关键点")


class DiscussionSummaryResponse(BaseModel):
    """讨论总结响应"""
    discussion_id: int
    summary: str
    key_decisions: List[str]
    action_items: List[str]
    key_points: List[str]
    participants_contribution: Dict[int, Dict[str, Any]]
    generated_at: datetime


class KnowledgeEntryRequest(BaseModel):
    """知识条目请求"""
    discussion_id: int = Field(..., description="讨论ID")
    title: str = Field(..., min_length=3, max_length=200, description="知识条目标题")
    category: str = Field(..., min_length=2, max_length=50, description="知识分类")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")
    is_public: bool = Field(True, description="是否公开")


class KnowledgeEntryResponse(BaseModel):
    """知识条目响应"""
    id: int
    discussion_id: int
    title: str
    category: str
    content: str
    tags: List[str]
    is_public: bool
    creator_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 导出和报告模式

class DiscussionExportRequest(BaseModel):
    """讨论导出请求"""
    discussion_ids: Optional[List[int]] = Field(None, description="讨论ID列表")
    requirement_id: Optional[int] = Field(None, description="需求ID")
    project_id: Optional[int] = Field(None, description="项目ID")
    export_format: str = Field("pdf", pattern="^(pdf|word|html|json)$", description="导出格式")
    include_messages: bool = Field(True, description="是否包含消息")
    include_attachments: bool = Field(False, description="是否包含附件")
    date_range: Optional[Dict[str, datetime]] = Field(None, description="日期范围")


class DiscussionReportRequest(BaseModel):
    """讨论报告请求"""
    project_id: Optional[int] = Field(None, description="项目ID")
    requirement_ids: Optional[List[int]] = Field(None, description="需求ID列表")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    report_type: str = Field("summary", pattern="^(summary|detailed|analytics)$", description="报告类型")
    include_statistics: bool = Field(True, description="是否包含统计信息")


class DiscussionReportResponse(BaseModel):
    """讨论报告响应"""
    report_type: str
    project_id: Optional[int]
    date_range: Dict[str, Optional[datetime]]
    statistics: Dict[str, Any]
    discussions_summary: List[Dict[str, Any]]
    insights: Dict[str, Any]
    generated_at: datetime


# 通知和提醒模式

class DiscussionNotificationRequest(BaseModel):
    """讨论通知请求"""
    discussion_id: int = Field(..., description="讨论ID")
    notification_type: str = Field(..., pattern="^(invitation|mention|summary|reminder)$", description="通知类型")
    recipients: Optional[List[int]] = Field(None, description="接收人ID列表")
    message: Optional[str] = Field(None, max_length=500, description="自定义消息")
    schedule_time: Optional[datetime] = Field(None, description="定时发送时间")


class DiscussionReminderRequest(BaseModel):
    """讨论提醒请求"""
    discussion_id: int = Field(..., description="讨论ID")
    reminder_type: str = Field(..., pattern="^(follow_up|deadline|inactive)$", description="提醒类型")
    reminder_time: datetime = Field(..., description="提醒时间")
    message: Optional[str] = Field(None, max_length=200, description="提醒消息")
    recipients: Optional[List[int]] = Field(None, description="接收人ID列表")


# 搜索和过滤模式

class DiscussionSearchRequest(BaseModel):
    """讨论搜索请求"""
    query: str = Field(..., min_length=2, max_length=200, description="搜索查询")
    search_in: List[str] = Field(["topic", "description", "messages"], description="搜索范围")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    sort_by: str = Field("relevance", description="排序方式")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(20, ge=1, le=100, description="限制数量")


class DiscussionSearchResponse(BaseModel):
    """讨论搜索响应"""
    query: str
    results: List[DiscussionResponse]
    total: int
    search_time: float
    suggestions: List[str]


# 模板和配置模式

class DiscussionTemplateRequest(BaseModel):
    """讨论模板请求"""
    name: str = Field(..., min_length=3, max_length=100, description="模板名称")
    description: str = Field(..., min_length=10, max_length=500, description="模板描述")
    topic_template: str = Field(..., min_length=3, max_length=200, description="主题模板")
    initial_message: Optional[str] = Field(None, max_length=1000, description="初始消息")
    suggested_participants: Optional[List[str]] = Field(None, description="建议参与者角色")
    tags: Optional[List[str]] = Field(default_factory=list, description="默认标签")
    is_public: bool = Field(True, description="是否公开模板")


class DiscussionTemplateResponse(BaseModel):
    """讨论模板响应"""
    id: int
    name: str
    description: str
    topic_template: str
    initial_message: Optional[str]
    suggested_participants: List[str]
    tags: List[str]
    is_public: bool
    usage_count: int
    creator_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True