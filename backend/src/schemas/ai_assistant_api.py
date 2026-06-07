"""
AI助手模块前后端接口规范定义
统一的API响应格式和数据模型
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# 基础响应格式
# ============================================================================

class APIResponse(BaseModel):
    """统一的API响应格式"""
    success: bool = Field(..., description="请求是否成功")
    data: Optional[Any] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[Dict[str, str]] = Field(None, description="错误信息")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="错误代码")
    details: str = Field(..., description="错误详情")
    field: Optional[str] = Field(None, description="相关字段")


# ============================================================================
# 对话相关数据结构
# ============================================================================

class MessageRole(str, Enum):
    """消息角色"""
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class ContentType(str, Enum):
    """内容类型"""
    TEXT = "TEXT"
    MARKDOWN = "MARKDOWN"
    CODE = "CODE"
    JSON = "JSON"


class ChatMessage(BaseModel):
    """对话消息数据结构"""
    id: int = Field(..., description="消息ID")
    conversation_id: int = Field(..., description="对话ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    content_type: ContentType = Field(default=ContentType.TEXT, description="内容类型")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    tokens_used: Optional[int] = Field(None, description="使用的Token数量")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度分数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class ConversationStatus(str, Enum):
    """对话状态"""
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class Conversation(BaseModel):
    """对话数据结构"""
    id: int = Field(..., description="对话ID")
    user_id: int = Field(..., description="用户ID")
    title: str = Field(..., description="对话标题")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="对话状态")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型")
    message_count: int = Field(default=0, description="消息数量")
    total_tokens: int = Field(default=0, description="总Token数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_message_at: Optional[datetime] = Field(None, description="最后消息时间")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


# ============================================================================
# 建议相关数据结构
# ============================================================================

class SuggestionType(str, Enum):
    """建议类型"""
    OPTIMIZATION = "OPTIMIZATION"
    IMPROVEMENT = "IMPROVEMENT"
    RISK_MITIGATION = "RISK_MITIGATION"
    QUALITY_ENHANCEMENT = "QUALITY_ENHANCEMENT"
    PROCESS_IMPROVEMENT = "PROCESS_IMPROVEMENT"


class SuggestionStatus(str, Enum):
    """建议状态"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"
    CANCELLED = "CANCELLED"


class SuggestionPriority(str, Enum):
    """建议优先级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Suggestion(BaseModel):
    """建议数据结构"""
    id: int = Field(..., description="建议ID")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    type: SuggestionType = Field(..., description="建议类型")
    status: SuggestionStatus = Field(default=SuggestionStatus.PENDING, description="建议状态")
    priority: SuggestionPriority = Field(..., description="建议优先级")
    
    user_id: int = Field(..., description="用户ID")
    project_id: Optional[int] = Field(None, description="项目ID")
    conversation_id: Optional[int] = Field(None, description="对话ID")
    
    action_items: Optional[List[str]] = Field(default_factory=list, description="行动项列表")
    expected_benefit: Optional[str] = Field(None, description="预期收益")
    estimated_effort: Optional[str] = Field(None, description="预估工作量")
    implementation_notes: Optional[str] = Field(None, description="实施说明")
    
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型名称")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度分数")
    
    user_rating: Optional[int] = Field(None, ge=1, le=5, description="用户评分")
    user_feedback: Optional[str] = Field(None, description="用户反馈")
    
    implemented_at: Optional[datetime] = Field(None, description="实施时间")
    implemented_by: Optional[int] = Field(None, description="实施人ID")
    implementation_result: Optional[str] = Field(None, description="实施结果")
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    # 客户端状态管理字段（不存储到数据库）
    syncing: Optional[bool] = Field(default=False, description="是否正在同步")
    last_synced: Optional[datetime] = Field(None, description="最后同步时间")
    local_changes: Optional[bool] = Field(default=False, description="是否有本地更改")


# ============================================================================
# 需求分析相关数据结构
# ============================================================================

class RequirementIssue(BaseModel):
    """需求问题"""
    requirement_id: Union[int, str] = Field(..., description="需求ID")
    requirement_title: str = Field(..., description="需求标题")
    issue_type: str = Field(..., description="问题类型")
    description: str = Field(..., description="问题描述")
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="严重程度")
    suggestions: List[str] = Field(default_factory=list, description="改进建议")


class QualityMetrics(BaseModel):
    """质量指标"""
    completeness_score: float = Field(..., ge=0.0, le=1.0, description="完整性得分")
    clarity_score: float = Field(..., ge=0.0, le=1.0, description="清晰度得分")
    consistency_score: float = Field(..., ge=0.0, le=1.0, description="一致性得分")
    testability_score: float = Field(..., ge=0.0, le=1.0, description="可测试性得分")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="总体得分")


class RequirementsAnalysisResult(BaseModel):
    """需求分析结果"""
    analysis_id: str = Field(..., description="分析ID")
    project_id: int = Field(..., description="项目ID")
    total_requirements: int = Field(..., description="需求总数")
    quality_metrics: QualityMetrics = Field(..., description="质量指标")
    issues: List[RequirementIssue] = Field(default_factory=list, description="问题列表")
    suggestions: List[Dict[str, Any]] = Field(default_factory=list, description="改进建议")
    analysis_summary: str = Field(..., description="分析摘要")
    created_at: datetime = Field(..., description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


# ============================================================================
# 分析进度相关数据结构
# ============================================================================

class AnalysisStatus(str, Enum):
    """分析状态"""
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AnalysisProgress(BaseModel):
    """分析进度"""
    analysis_id: str = Field(..., description="分析ID")
    project_id: int = Field(..., description="项目ID")
    status: AnalysisStatus = Field(..., description="分析状态")
    progress: int = Field(..., ge=0, le=100, description="进度百分比")
    current_step: str = Field(..., description="当前步骤")
    estimated_time_remaining: int = Field(..., description="预估剩余时间(秒)")
    completed_steps: List[str] = Field(default_factory=list, description="已完成步骤")
    total_steps: int = Field(..., description="总步骤数")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


# ============================================================================
# WebSocket消息格式
# ============================================================================

class WSMessageType(str, Enum):
    """WebSocket消息类型"""
    MESSAGE = "message"
    TYPING = "typing"
    STATUS = "status"
    ERROR = "error"
    ANALYSIS_PROGRESS = "analysis_progress"
    ANALYSIS_RESULT = "analysis_result"
    ANALYSIS_ERROR = "analysis_error"
    SUGGESTION_UPDATE = "suggestion_update"
    HEARTBEAT = "heartbeat"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"


class WSMessage(BaseModel):
    """WebSocket消息格式"""
    type: WSMessageType = Field(..., description="消息类型")
    conversation_id: Optional[int] = Field(None, description="对话ID")
    data: Any = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    user_id: Optional[int] = Field(None, description="用户ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


# ============================================================================
# 状态同步相关数据结构
# ============================================================================

class ConnectionStatus(str, Enum):
    """连接状态"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"


class SyncStatus(str, Enum):
    """同步状态"""
    SYNCED = "synced"
    SYNCING = "syncing"
    ERROR = "error"
    OFFLINE = "offline"


class ChatState(BaseModel):
    """聊天状态"""
    conversations: List[Conversation] = Field(default_factory=list, description="对话列表")
    current_conversation: Optional[Conversation] = Field(None, description="当前对话")
    messages: List[ChatMessage] = Field(default_factory=list, description="消息列表")
    loading: bool = Field(default=False, description="是否加载中")
    connection_status: ConnectionStatus = Field(default=ConnectionStatus.DISCONNECTED, description="连接状态")
    sync_status: SyncStatus = Field(default=SyncStatus.SYNCED, description="同步状态")
    typing_users: List[int] = Field(default_factory=list, description="正在输入的用户")


class BatchOperationStatus(str, Enum):
    """批量操作状态"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"


class BatchProgress(BaseModel):
    """批量操作进度"""
    operation_id: str = Field(..., description="操作ID")
    status: BatchOperationStatus = Field(..., description="操作状态")
    total_items: int = Field(..., description="总项目数")
    processed_items: int = Field(..., description="已处理项目数")
    successful_items: int = Field(..., description="成功项目数")
    failed_items: int = Field(..., description="失败项目数")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="进度百分比")
    error_messages: List[str] = Field(default_factory=list, description="错误信息列表")
    started_at: datetime = Field(..., description="开始时间")
    updated_at: datetime = Field(..., description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


# ============================================================================
# 请求和响应模式
# ============================================================================

class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    title: Optional[str] = Field(None, description="对话标题")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型")
    initial_message: Optional[str] = Field(None, description="初始消息")


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., min_length=1, description="消息内容")
    content_type: ContentType = Field(default=ContentType.TEXT, description="内容类型")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class UpdateSuggestionRequest(BaseModel):
    """更新建议请求"""
    status: Optional[SuggestionStatus] = Field(None, description="建议状态")
    user_rating: Optional[int] = Field(None, ge=1, le=5, description="用户评分")
    user_feedback: Optional[str] = Field(None, description="用户反馈")
    implementation_notes: Optional[str] = Field(None, description="实施说明")


class BatchUpdateSuggestionsRequest(BaseModel):
    """批量更新建议请求"""
    suggestion_ids: List[int] = Field(..., min_items=1, description="建议ID列表")
    updates: UpdateSuggestionRequest = Field(..., description="更新内容")
    operation_reason: Optional[str] = Field(None, description="操作原因")


class StartAnalysisRequest(BaseModel):
    """开始分析请求"""
    project_id: int = Field(..., description="项目ID")
    requirements: List[Dict[str, Any]] = Field(..., min_items=1, description="需求列表")
    analysis_options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="分析选项")
    include_ai_analysis: bool = Field(default=True, description="是否包含AI分析")


# ============================================================================
# 分页和过滤
# ============================================================================

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="每页大小")


class SuggestionFilters(BaseModel):
    """建议过滤器"""
    status: Optional[List[SuggestionStatus]] = Field(None, description="状态过滤")
    type: Optional[List[SuggestionType]] = Field(None, description="类型过滤")
    priority: Optional[List[SuggestionPriority]] = Field(None, description="优先级过滤")
    project_id: Optional[int] = Field(None, description="项目ID过滤")
    date_from: Optional[datetime] = Field(None, description="开始日期")
    date_to: Optional[datetime] = Field(None, description="结束日期")
    search_text: Optional[str] = Field(None, description="搜索文本")


class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[Any] = Field(..., description="数据项列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


# ============================================================================
# 导出所有模型
# ============================================================================

__all__ = [
    # 基础响应
    "APIResponse",
    "ErrorDetail",
    
    # 对话相关
    "MessageRole",
    "ContentType", 
    "ChatMessage",
    "ConversationStatus",
    "Conversation",
    
    # 建议相关
    "SuggestionType",
    "SuggestionStatus", 
    "SuggestionPriority",
    "Suggestion",
    
    # 需求分析相关
    "RequirementIssue",
    "QualityMetrics",
    "RequirementsAnalysisResult",
    
    # 分析进度相关
    "AnalysisStatus",
    "AnalysisProgress",
    
    # WebSocket相关
    "WSMessageType",
    "WSMessage",
    
    # 状态同步相关
    "ConnectionStatus",
    "SyncStatus",
    "ChatState",
    "BatchOperationStatus",
    "BatchProgress",
    
    # 请求响应相关
    "CreateConversationRequest",
    "SendMessageRequest",
    "UpdateSuggestionRequest",
    "BatchUpdateSuggestionsRequest",
    "StartAnalysisRequest",
    
    # 分页过滤相关
    "PaginationParams",
    "SuggestionFilters",
    "PaginatedResponse"
]