"""
会议录制相关的Pydantic模型

本模块定义了会议录制管理API的请求和响应数据模型，包括：
- 录制启动、停止、分享的请求模型
- 录制详情、列表、播放信息的响应模型
- 录制类型、状态等枚举模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class RecordingTypeEnum(str, Enum):
    """录制类型枚举"""
    FULL_MEETING = "FULL_MEETING"
    SCREEN_SHARE = "SCREEN_SHARE"
    AUDIO_ONLY = "AUDIO_ONLY"
    HIGHLIGHTS = "HIGHLIGHTS"


class RecordingStatusEnum(str, Enum):
    """录制状态枚举"""
    RECORDING = "RECORDING"
    PAUSED = "PAUSED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DELETED = "DELETED"


class FileFormatEnum(str, Enum):
    """文件格式枚举"""
    MP4 = "MP4"
    WEBM = "WEBM"
    MP3 = "MP3"
    M4A = "M4A"


class StartRecordingRequest(BaseModel):
    """开始录制请求模型"""
    recording_name: Optional[str] = Field(None, description="录制名称", max_length=200)
    recording_type: RecordingTypeEnum = Field(RecordingTypeEnum.FULL_MEETING, description="录制类型")
    file_format: FileFormatEnum = Field(FileFormatEnum.MP4, description="文件格式")
    quality: str = Field("standard", description="录制质量", pattern="^(low|standard|high)$")
    auto_transcription: bool = Field(True, description="是否自动转录")
    include_chat: bool = Field(True, description="是否包含聊天记录")
    include_whiteboard: bool = Field(True, description="是否包含白板内容")


class StopRecordingRequest(BaseModel):
    """停止录制请求模型"""
    reason: Optional[str] = Field(None, description="停止原因", max_length=500)


class RecordingResponse(BaseModel):
    """录制响应模型"""
    id: int = Field(..., description="录制ID")
    meeting_id: int = Field(..., description="会议ID")
    recording_name: str = Field(..., description="录制名称")
    recording_type: str = Field(..., description="录制类型")
    file_format: str = Field(..., description="文件格式")
    file_path: str = Field(..., description="文件路径")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    duration_seconds: Optional[int] = Field(None, description="录制时长(秒)")
    resolution: Optional[str] = Field(None, description="视频分辨率")
    recording_status: str = Field(..., description="录制状态")
    processing_progress: Optional[int] = Field(None, description="处理进度(百分比)")
    start_time: datetime = Field(..., description="录制开始时间")
    end_time: Optional[datetime] = Field(None, description="录制结束时间")
    is_public: Optional[bool] = Field(None, description="是否公开")
    access_password: Optional[str] = Field(None, description="访问密码")
    download_count: Optional[int] = Field(None, description="下载次数")
    view_count: Optional[int] = Field(None, description="观看次数")
    created_by: int = Field(..., description="创建者ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class RecordingListResponse(BaseModel):
    """录制列表响应模型"""
    recordings: List[RecordingResponse] = Field(..., description="录制列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")

    class Config:
        from_attributes = True


class PlaybackInfoResponse(BaseModel):
    """播放信息响应模型"""
    recording_id: int = Field(..., description="录制ID")
    playback_url: str = Field(..., description="播放URL")
    playback_token: str = Field(..., description="播放令牌")
    duration_seconds: int = Field(..., description="时长(秒)")
    resolution: Optional[str] = Field(None, description="分辨率")
    file_format: str = Field(..., description="文件格式")
    subtitles: Optional[List[Dict[str, Any]]] = Field(None, description="字幕信息")
    chapters: Optional[List[Dict[str, Any]]] = Field(None, description="章节信息")
    expires_at: datetime = Field(..., description="令牌过期时间")

    class Config:
        from_attributes = True


class RecordingShareRequest(BaseModel):
    """录制分享请求模型"""
    is_public: bool = Field(False, description="是否公开")
    access_password: Optional[str] = Field(None, description="访问密码", max_length=100)
    expires_at: Optional[datetime] = Field(None, description="分享过期时间")
    allow_download: bool = Field(True, description="是否允许下载")
    custom_message: Optional[str] = Field(None, description="自定义分享消息", max_length=500)

    @validator('access_password')
    def validate_password(cls, v, values):
        if not values.get('is_public') and not v:
            raise ValueError('非公开分享必须设置访问密码')
        return v
class RecordingQueryParams(BaseModel):
    """录制查询参数模型"""
    meeting_id: Optional[int] = Field(None, description="会议ID")
    recording_type: Optional[RecordingTypeEnum] = Field(None, description="录制类型")
    status: Optional[RecordingStatusEnum] = Field(None, description="录制状态")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    keyword: Optional[str] = Field(None, description="关键词搜索", max_length=100)
    sort_by: str = Field("start_time", description="排序字段")
    sort_order: str = Field("desc", description="排序方向", pattern="^(asc|desc)$")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页大小", ge=1, le=100)
    include_deleted: bool = Field(False, description="是否包含已删除")


class StartRecordingResponse(BaseModel):
    """开始录制响应模型"""
    success: bool = Field(..., description="是否成功")
    recording_id: Optional[int] = Field(None, description="录制ID")
    message: str = Field(..., description="响应消息")


class PauseRecordingResponse(BaseModel):
    """暂停/恢复录制响应模型：data 为更新后的录制记录"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: RecordingResponse = Field(..., description="更新后的录制记录")


class StopRecordingResponse(BaseModel):
    """停止录制响应模型"""
    success: bool = Field(..., description="是否成功")
    recording_id: int = Field(..., description="录制ID")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    duration: Optional[int] = Field(None, description="录制时长(秒)")
    message: str = Field(..., description="响应消息")


class DeleteRecordingResponse(BaseModel):
    """删除录制响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")


class RecordingShareResponse(BaseModel):
    """录制分享响应模型"""
    success: bool = Field(..., description="是否成功")
    share_url: Optional[str] = Field(None, description="分享链接")
    message: str = Field(..., description="响应消息")


class RecordingStatistics(BaseModel):
    """录制统计模型"""
    total_recordings: int = Field(..., description="总录制数")
    active_recordings: int = Field(..., description="进行中录制数")
    completed_recordings: int = Field(..., description="已完成录制数")
    failed_recordings: int = Field(..., description="失败录制数")
    total_duration_minutes: int = Field(..., description="总录制时长(分钟)")
    total_file_size_mb: float = Field(..., description="总文件大小(MB)")
    by_type: Dict[str, int] = Field(..., description="按类型统计")
    by_format: Dict[str, int] = Field(..., description="按格式统计")