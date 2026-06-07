"""
协作功能相关的Pydantic模型

本模块定义了会议协作功能API的请求和响应数据模型，包括：
- 聊天消息的请求和响应模型
- 文件共享的请求和响应模型
- 白板协作等功能模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.meeting import MessageType, FileShareStatus


class MessageTypeEnum(str, Enum):
    """消息类型枚举"""
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILE = "FILE"
    SYSTEM = "SYSTEM"
    EMOJI = "EMOJI"


class FileShareStatusEnum(str, Enum):
    """文件共享状态枚举"""
    UPLOADING = "UPLOADING"
    AVAILABLE = "AVAILABLE"
    PROCESSING = "PROCESSING"
    FAILED = "FAILED"
    DELETED = "DELETED"


class SendChatMessageRequest(BaseModel):
    """发送聊天消息请求模型"""
    content: str = Field(..., description="消息内容", min_length=1, max_length=2000)
    message_type: MessageTypeEnum = Field(MessageTypeEnum.TEXT, description="消息类型")
    is_private: bool = Field(False, description="是否私聊")
    recipient_id: Optional[int] = Field(None, description="接收者ID(私聊时使用)")
    reply_to_id: Optional[int] = Field(None, description="回复消息ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")

    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('消息内容不能为空')
        return v.strip()

    @validator('recipient_id')
    def validate_recipient(cls, v, values):
        if values.get('is_private') and not v:
            raise ValueError('私聊消息必须指定接收者')
        return v


class ChatMessageResponse(BaseModel):
    """聊天消息响应模型"""
    id: int = Field(..., description="消息ID")
    meeting_id: int = Field(..., description="会议ID")
    sender_id: int = Field(..., description="发送者ID")
    message_type: str = Field(..., description="消息类型")
    content: str = Field(..., description="消息内容")
    is_private: bool = Field(..., description="是否私聊")
    recipient_id: Optional[int] = Field(None, description="接收者ID")
    reply_to_id: Optional[int] = Field(None, description="回复消息ID")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")
    sent_at: datetime = Field(..., description="发送时间")
    created_at: datetime = Field(..., description="创建时间")
    
    # 发送者信息
    sender_name: Optional[str] = Field(None, description="发送者姓名")
    sender_avatar: Optional[str] = Field(None, description="发送者头像")
    
    # 回复消息信息
    reply_to_content: Optional[str] = Field(None, description="回复的消息内容")
    reply_to_sender: Optional[str] = Field(None, description="回复的消息发送者")

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """聊天历史响应模型"""
    messages: List[ChatMessageResponse] = Field(..., description="消息列表")
    total: int = Field(..., description="总消息数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(50, description="每页数量")
    has_more: bool = Field(False, description="是否有更多消息")

    class Config:
        from_attributes = True


class SendChatMessageResponse(BaseModel):
    """发送聊天消息响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("消息发送成功", description="响应消息")
    data: ChatMessageResponse = Field(..., description="消息数据")

    class Config:
        from_attributes = True


class ChatQueryParams(BaseModel):
    """聊天查询参数模型"""
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(50, description="每页数量", ge=1, le=200)
    message_type: Optional[MessageTypeEnum] = Field(None, description="消息类型筛选")
    sender_id: Optional[int] = Field(None, description="发送者ID筛选")
    start_time: Optional[datetime] = Field(None, description="开始时间筛选")
    end_time: Optional[datetime] = Field(None, description="结束时间筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索", max_length=100)
    include_private: bool = Field(False, description="是否包含私聊消息")


class UploadFileRequest(BaseModel):
    """上传文件请求模型"""
    file_name: str = Field(..., description="文件名", max_length=255)
    file_size: int = Field(..., description="文件大小(字节)", ge=1)
    file_type: str = Field(..., description="文件类型", max_length=100)
    mime_type: Optional[str] = Field(None, description="MIME类型", max_length=100)
    description: Optional[str] = Field(None, description="文件描述", max_length=1000)
    is_public: bool = Field(True, description="是否公开")
    chunk_size: Optional[int] = Field(None, description="分块大小(字节)")
    total_chunks: Optional[int] = Field(None, description="总分块数")

    @validator('file_name')
    def validate_file_name(cls, v):
        if not v.strip():
            raise ValueError('文件名不能为空')
        # 检查文件名中的非法字符
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        if any(char in v for char in invalid_chars):
            raise ValueError('文件名包含非法字符')
        return v.strip()

    @validator('file_size')
    def validate_file_size(cls, v):
        # 限制文件大小为500MB
        max_size = 500 * 1024 * 1024
        if v > max_size:
            raise ValueError(f'文件大小不能超过{max_size // (1024*1024)}MB')
        return v


class FileShareResponse(BaseModel):
    """文件共享响应模型"""
    id: int = Field(..., description="文件ID")
    meeting_id: int = Field(..., description="会议ID")
    uploader_id: int = Field(..., description="上传者ID")
    file_name: str = Field(..., description="文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小(字节)")
    file_type: str = Field(..., description="文件类型")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    status: str = Field(..., description="文件状态")
    is_public: bool = Field(..., description="是否公开")
    download_count: int = Field(..., description="下载次数")
    description: Optional[str] = Field(None, description="文件描述")
    file_metadata: Optional[Dict[str, Any]] = Field(None, description="文件元数据")
    uploaded_at: datetime = Field(..., description="上传时间")
    created_at: datetime = Field(..., description="创建时间")
    
    # 扩展信息
    file_size_mb: Optional[float] = Field(None, description="文件大小(MB)")
    download_url: Optional[str] = Field(None, description="下载链接")
    preview_url: Optional[str] = Field(None, description="预览链接")
    uploader_name: Optional[str] = Field(None, description="上传者姓名")

    class Config:
        from_attributes = True


class UploadFileResponse(BaseModel):
    """上传文件响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("文件上传成功", description="响应消息")
    data: FileShareResponse = Field(..., description="文件数据")
    upload_url: Optional[str] = Field(None, description="上传链接")
    upload_token: Optional[str] = Field(None, description="上传令牌")

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """文件列表响应模型"""
    files: List[FileShareResponse] = Field(..., description="文件列表")
    total: int = Field(..., description="总文件数")
    total_size_mb: float = Field(0, description="总文件大小(MB)")

    class Config:
        from_attributes = True


class FileQueryParams(BaseModel):
    """文件查询参数模型"""
    file_type: Optional[str] = Field(None, description="文件类型筛选")
    status: Optional[FileShareStatusEnum] = Field(None, description="文件状态筛选")
    uploader_id: Optional[int] = Field(None, description="上传者ID筛选")
    start_date: Optional[datetime] = Field(None, description="开始日期筛选")
    end_date: Optional[datetime] = Field(None, description="结束日期筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索", max_length=100)
    include_deleted: bool = Field(False, description="是否包含已删除文件")


class WhiteboardAction(BaseModel):
    """白板操作模型"""
    action_type: str = Field(..., description="操作类型")  # draw, erase, clear, undo, redo
    user_id: int = Field(..., description="操作用户ID")
    data: Dict[str, Any] = Field(..., description="操作数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="操作时间")


class WhiteboardState(BaseModel):
    """白板状态模型"""
    whiteboard_id: str = Field(..., description="白板ID")
    meeting_id: int = Field(..., description="会议ID")
    content: Dict[str, Any] = Field(..., description="白板内容")
    version: int = Field(..., description="版本号")
    last_modified: datetime = Field(..., description="最后修改时间")
    last_modified_by: int = Field(..., description="最后修改者ID")

    class Config:
        from_attributes = True


class PollOption(BaseModel):
    """投票选项模型"""
    option_id: str = Field(..., description="选项ID")
    text: str = Field(..., description="选项文本", max_length=200)
    votes: int = Field(0, description="票数")


class CreatePollRequest(BaseModel):
    """创建投票请求模型"""
    question: str = Field(..., description="投票问题", min_length=1, max_length=500)
    options: List[PollOption] = Field(..., description="投票选项", min_items=2, max_items=10)
    multiple_choice: bool = Field(False, description="是否多选")
    anonymous: bool = Field(True, description="是否匿名")
    duration_minutes: Optional[int] = Field(None, description="投票时长(分钟)", ge=1, le=1440)

    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError('投票问题不能为空')
        return v.strip()


class PollResponse(BaseModel):
    """投票响应模型"""
    poll_id: str = Field(..., description="投票ID")
    meeting_id: int = Field(..., description="会议ID")
    question: str = Field(..., description="投票问题")
    options: List[PollOption] = Field(..., description="投票选项")
    multiple_choice: bool = Field(..., description="是否多选")
    anonymous: bool = Field(..., description="是否匿名")
    status: str = Field(..., description="投票状态")  # active, closed, cancelled
    total_votes: int = Field(..., description="总票数")
    created_by: int = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    class Config:
        from_attributes = True


class VotePollRequest(BaseModel):
    """投票请求模型"""
    poll_id: str = Field(..., description="投票ID")
    selected_options: List[str] = Field(..., description="选中的选项ID列表", min_items=1)

    @validator('selected_options')
    def validate_options(cls, v):
        if not v:
            raise ValueError('必须选择至少一个选项')
        return v