"""
会议管理相关的Pydantic模型

本模块定义了会议管理API的请求和响应数据模型，包括：
- 会议创建、更新、查询的请求模型
- 会议详情、列表的响应模型
- 会议状态、类型等枚举模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.meeting import MeetingType, MeetingStatus


class MeetingTypeEnum(str, Enum):
    """会议类型枚举"""
    PROJECT_KICKOFF = "PROJECT_KICKOFF"
    REQUIREMENT_REVIEW = "REQUIREMENT_REVIEW"
    DESIGN_REVIEW = "DESIGN_REVIEW"
    CODE_REVIEW = "CODE_REVIEW"
    TEST_REVIEW = "TEST_REVIEW"
    PROGRESS_SYNC = "PROGRESS_SYNC"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"
    PROJECT_SUMMARY = "PROJECT_SUMMARY"
    TRAINING = "TRAINING"
    OTHER = "OTHER"


class MeetingStatusEnum(str, Enum):
    """会议状态枚举"""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    POSTPONED = "POSTPONED"


class AgendaItem(BaseModel):
    """议程项目模型"""
    title: str = Field(..., description="议程标题", max_length=200)
    description: Optional[str] = Field(None, description="议程描述")
    duration_minutes: int = Field(30, description="预计时长(分钟)", ge=5, le=480)
    presenter: Optional[str] = Field(None, description="主讲人")
    order: int = Field(1, description="议程顺序", ge=1)


class MeetingSettings(BaseModel):
    """会议设置模型"""
    auto_record: bool = Field(False, description="自动录制")
    mute_on_join: bool = Field(True, description="加入时静音")
    video_on_join: bool = Field(False, description="加入时开启视频")
    allow_screen_share: bool = Field(True, description="允许屏幕共享")
    allow_chat: bool = Field(True, description="允许聊天")
    allow_file_share: bool = Field(True, description="允许文件共享")
    waiting_room_enabled: bool = Field(True, description="启用等候室")
    password_required: bool = Field(False, description="需要密码")
    recording_auto_start: bool = Field(False, description="自动开始录制")


class CreateMeetingRequest(BaseModel):
    """创建会议请求模型"""
    title: str = Field(..., description="会议标题", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="会议描述", max_length=2000)
    meeting_type: MeetingTypeEnum = Field(..., description="会议类型")
    scheduled_start_time: datetime = Field(..., description="计划开始时间")
    scheduled_end_time: datetime = Field(..., description="计划结束时间")
    timezone: str = Field("UTC", description="时区")
    max_participants: int = Field(100, description="最大参与人数", ge=2, le=1000)
    project_id: Optional[int] = Field(None, description="关联项目ID")
    agenda: Optional[List[AgendaItem]] = Field(None, description="会议议程")
    meeting_settings: Optional[MeetingSettings] = Field(None, description="会议设置")
    is_recording_enabled: bool = Field(False, description="是否启用录制")
    is_waiting_room_enabled: bool = Field(True, description="是否启用等候室")
    is_password_protected: bool = Field(False, description="是否需要会议密码")
    meeting_password: Optional[str] = Field(None, description="会议密码", max_length=100)
    participant_ids: Optional[List[int]] = Field(None, description="参与者用户ID列表")
    auto_schedule: bool = Field(False, description="智能调度")
    preferred_time_range: Optional[Dict[str, Any]] = Field(None, description="偏好时间范围")

    @validator('scheduled_end_time')
    def validate_end_time(cls, v, values):
        if 'scheduled_start_time' in values and v <= values['scheduled_start_time']:
            raise ValueError('结束时间必须晚于开始时间')
        return v

    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('会议标题不能为空')
        return v.strip()


class UpdateMeetingRequest(BaseModel):
    """更新会议请求模型"""
    title: Optional[str] = Field(None, description="会议标题", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="会议描述", max_length=2000)
    meeting_type: Optional[MeetingTypeEnum] = Field(None, description="会议类型")
    scheduled_start_time: Optional[datetime] = Field(None, description="计划开始时间")
    scheduled_end_time: Optional[datetime] = Field(None, description="计划结束时间")
    timezone: Optional[str] = Field(None, description="时区")
    max_participants: Optional[int] = Field(None, description="最大参与人数", ge=2, le=1000)
    agenda: Optional[List[AgendaItem]] = Field(None, description="会议议程")
    meeting_settings: Optional[MeetingSettings] = Field(None, description="会议设置")
    is_recording_enabled: Optional[bool] = Field(None, description="是否启用录制")
    is_waiting_room_enabled: Optional[bool] = Field(None, description="是否启用等候室")
    is_password_protected: Optional[bool] = Field(None, description="是否需要会议密码")
    meeting_password: Optional[str] = Field(None, description="会议密码", max_length=100)

    @validator('title')
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('会议标题不能为空')
        return v.strip() if v else v


class MeetingQueryParams(BaseModel):
    """会议查询参数模型"""
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页数量", ge=1, le=100)
    meeting_type: Optional[MeetingTypeEnum] = Field(None, description="会议类型筛选")
    status: Optional[MeetingStatusEnum] = Field(None, description="会议状态筛选")
    project_id: Optional[int] = Field(None, description="项目ID筛选")
    organizer_id: Optional[int] = Field(None, description="组织者ID筛选")
    start_date: Optional[datetime] = Field(None, description="开始日期筛选")
    end_date: Optional[datetime] = Field(None, description="结束日期筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索", max_length=100)
    sort_by: str = Field("scheduled_start_time", description="排序字段")
    sort_order: str = Field("desc", description="排序方向", pattern="^(asc|desc)$")


class MeetingResponse(BaseModel):
    """会议响应模型"""
    id: int = Field(..., description="会议ID")
    meeting_code: str = Field(..., description="会议编码")
    title: str = Field(..., description="会议标题")
    description: Optional[str] = Field(None, description="会议描述")
    meeting_type: str = Field(..., description="会议类型")
    status: str = Field(..., description="会议状态")
    scheduled_start_time: datetime = Field(..., description="计划开始时间")
    scheduled_end_time: datetime = Field(..., description="计划结束时间")
    actual_start_time: Optional[datetime] = Field(None, description="实际开始时间")
    actual_end_time: Optional[datetime] = Field(None, description="实际结束时间")
    timezone: str = Field(..., description="时区")
    max_participants: int = Field(..., description="最大参与人数")
    is_recording_enabled: bool = Field(..., description="是否启用录制")
    is_waiting_room_enabled: bool = Field(..., description="是否启用等候室")
    is_password_protected: bool = Field(..., description="是否密码保护")
    project_id: Optional[int] = Field(None, description="关联项目ID")
    organizer_id: int = Field(..., description="组织者ID")
    agenda: Optional[List[Dict[str, Any]]] = Field(None, description="会议议程")
    meeting_settings: Optional[Dict[str, Any]] = Field(None, description="会议设置")
    participant_count: int = Field(..., description="参与人数")
    duration_minutes: int = Field(..., description="会议时长(分钟)")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: Optional[int] = Field(None, description="创建者ID")
    updated_by: Optional[int] = Field(None, description="更新者ID")

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """会议列表响应模型"""
    meetings: List[MeetingResponse] = Field(..., description="会议列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")

    class Config:
        from_attributes = True


class CreateMeetingResponse(BaseModel):
    """创建会议响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("会议创建成功", description="响应消息")
    data: MeetingResponse = Field(..., description="会议数据")

    class Config:
        from_attributes = True


class UpdateMeetingResponse(BaseModel):
    """更新会议响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("会议更新成功", description="响应消息")
    data: MeetingResponse = Field(..., description="会议数据")

    class Config:
        from_attributes = True


class DeleteMeetingResponse(BaseModel):
    """删除会议响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("会议删除成功", description="响应消息")

    class Config:
        from_attributes = True


class MeetingJoinRequest(BaseModel):
    """加入会议请求模型"""
    meeting_code: str = Field(..., description="会议编码", min_length=1, max_length=50)
    password: Optional[str] = Field(None, description="会议密码", max_length=100)
    device_info: Optional[Dict[str, Any]] = Field(None, description="设备信息")
    join_options: Optional[Dict[str, Any]] = Field(None, description="加入选项")


class MeetingJoinResponse(BaseModel):
    """加入会议响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    status: str = Field(..., description="加入状态")  # SUCCESS, WAITING_ROOM, FAILED
    access_token: Optional[str] = Field(None, description="访问令牌")
    meeting_config: Optional[Dict[str, Any]] = Field(None, description="会议配置")
    webrtc_config: Optional[Dict[str, Any]] = Field(None, description="WebRTC配置")

    class Config:
        from_attributes = True


class MeetingControlRequest(BaseModel):
    """会议控制请求模型"""
    action: str = Field(..., description="控制动作")  # start, end, pause, resume
    reason: Optional[str] = Field(None, description="操作原因", max_length=500)
    minutes_title: Optional[str] = Field(None, description="会议纪要标题", max_length=200)
    minutes_content: Optional[str] = Field(None, description="会议纪要内容", max_length=10000)
    minutes_summary: Optional[str] = Field(None, description="会议摘要", max_length=2000)
    key_points: Optional[List[str]] = Field(None, description="关键要点")
    decisions: Optional[List[Dict[str, Any]]] = Field(None, description="决策事项")
    action_items: Optional[List[Dict[str, Any]]] = Field(None, description="行动项")


class MeetingControlResponse(BaseModel):
    """会议控制响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    meeting_status: str = Field(..., description="会议状态")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")

    class Config:
        from_attributes = True


class MeetingStatusResponse(BaseModel):
    """会议状态响应模型"""
    meeting_id: int = Field(..., description="会议ID")
    status: str = Field(..., description="会议状态")
    participant_count: int = Field(..., description="当前参与人数")
    is_recording: bool = Field(..., description="是否正在录制")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    duration_minutes: int = Field(..., description="已进行时长(分钟)")
    network_quality: Optional[Dict[str, Any]] = Field(None, description="网络质量")

    class Config:
        from_attributes = True
