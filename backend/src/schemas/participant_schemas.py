"""
会议参与者相关的Pydantic模型

本模块定义了会议参与者管理API的请求和响应数据模型，包括：
- 参与者添加、更新、邀请的请求模型
- 参与者详情、列表的响应模型
- 参与者角色、状态等枚举模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ParticipantRoleEnum(str, Enum):
    """参与者角色枚举"""
    ORGANIZER = "ORGANIZER"
    MODERATOR = "MODERATOR"
    PRESENTER = "PRESENTER"
    PARTICIPANT = "PARTICIPANT"
    OBSERVER = "OBSERVER"


class InvitationStatusEnum(str, Enum):
    """邀请状态枚举"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    TENTATIVE = "TENTATIVE"


class AttendanceStatusEnum(str, Enum):
    """出席状态枚举"""
    NOT_JOINED = "NOT_JOINED"
    JOINED = "JOINED"
    LEFT = "LEFT"
    KICKED_OUT = "KICKED_OUT"


class AddParticipantRequest(BaseModel):
    """添加参与者请求模型"""
    user_id: int = Field(..., description="用户ID", gt=0)
    participant_role: ParticipantRoleEnum = Field(ParticipantRoleEnum.PARTICIPANT, description="参与者角色")
    can_share_screen: bool = Field(True, description="是否可以共享屏幕")
    can_use_chat: bool = Field(True, description="是否可以使用聊天")
    can_use_whiteboard: bool = Field(True, description="是否可以使用白板")
    can_record: bool = Field(False, description="是否可以录制")


class AddParticipantsRequest(BaseModel):
    """批量添加参与者请求模型"""
    participants: List[AddParticipantRequest] = Field(..., description="参与者列表", min_items=1)
    send_notification: bool = Field(True, description="是否发送通知")


class UpdateParticipantRequest(BaseModel):
    """更新参与者请求模型"""
    participant_role: Optional[ParticipantRoleEnum] = Field(None, description="参与者角色")
    can_share_screen: Optional[bool] = Field(None, description="是否可以共享屏幕")
    can_use_chat: Optional[bool] = Field(None, description="是否可以使用聊天")
    can_use_whiteboard: Optional[bool] = Field(None, description="是否可以使用白板")
    can_record: Optional[bool] = Field(None, description="是否可以录制")


class InviteParticipantRequest(BaseModel):
    """邀请参与者请求模型"""
    user_ids: List[int] = Field(..., description="用户ID列表", min_items=1)
    participant_role: ParticipantRoleEnum = Field(ParticipantRoleEnum.PARTICIPANT, description="参与者角色")
    custom_message: Optional[str] = Field(None, description="自定义邀请消息", max_length=500)
    send_email: bool = Field(True, description="是否发送邮件邀请")
    send_notification: bool = Field(True, description="是否发送系统通知")


class ParticipantResponse(BaseModel):
    """参与者响应模型"""
    id: int = Field(..., description="参与记录ID")
    meeting_id: int = Field(..., description="会议ID")
    user_id: int = Field(..., description="用户ID")
    user_name: Optional[str] = Field(None, description="用户姓名")
    user_email: Optional[str] = Field(None, description="用户邮箱")
    participant_role: str = Field(..., description="参与者角色")
    invitation_status: str = Field(..., description="邀请状态")
    attendance_status: str = Field(..., description="出席状态")
    can_share_screen: bool = Field(..., description="是否可以共享屏幕")
    can_use_chat: bool = Field(..., description="是否可以使用聊天")
    can_use_whiteboard: bool = Field(..., description="是否可以使用白板")
    can_record: bool = Field(..., description="是否可以录制")
    join_time: Optional[datetime] = Field(None, description="加入时间")
    leave_time: Optional[datetime] = Field(None, description="离开时间")
    total_duration_minutes: int = Field(..., description="总参与时长(分钟)")
    speak_duration_minutes: int = Field(..., description="发言时长(分钟)")
    interaction_count: int = Field(..., description="互动次数")
    device_info: Optional[Dict[str, Any]] = Field(None, description="设备信息")
    network_quality: Optional[Dict[str, Any]] = Field(None, description="网络质量信息")
    invited_at: datetime = Field(..., description="邀请时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class ParticipantListResponse(BaseModel):
    """参与者列表响应模型"""
    participants: List[ParticipantResponse] = Field(..., description="参与者列表")
    total: int = Field(..., description="总数量")
    meeting_id: int = Field(..., description="会议ID")

    class Config:
        from_attributes = True

class ParticipantInviteRequest(BaseModel):
    """参与者邀请请求模型 - 别名"""
    user_ids: List[int] = Field(..., description="用户ID列表", min_items=1)
    participant_role: ParticipantRoleEnum = Field(ParticipantRoleEnum.PARTICIPANT, description="参与者角色")
    custom_message: Optional[str] = Field(None, description="自定义邀请消息", max_length=500)
    send_email: bool = Field(True, description="是否发送邮件邀请")
    send_notification: bool = Field(True, description="是否发送系统通知")


class ParticipantQueryParams(BaseModel):
    """参与者查询参数模型"""
    meeting_id: Optional[int] = Field(None, description="会议ID")
    user_id: Optional[int] = Field(None, description="用户ID")
    participant_role: Optional[ParticipantRoleEnum] = Field(None, description="参与者角色")
    invitation_status: Optional[InvitationStatusEnum] = Field(None, description="邀请状态")
    attendance_status: Optional[AttendanceStatusEnum] = Field(None, description="出席状态")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页大小", ge=1, le=100)


class KickParticipantRequest(BaseModel):
    """踢出参与者请求模型"""
    reason: Optional[str] = Field(None, description="踢出原因", max_length=200)
    ban_duration_minutes: Optional[int] = Field(None, description="禁止重新加入时长(分钟)", ge=0)


class AddParticipantResponse(BaseModel):
    """添加参与者响应模型"""
    success: bool = Field(..., description="是否成功")
    participant: Optional[ParticipantResponse] = Field(None, description="参与者信息")
    message: str = Field(..., description="响应消息")


class AddParticipantsResponse(BaseModel):
    """批量添加参与者响应模型"""
    success: bool = Field(..., description="是否成功")
    added_count: int = Field(..., description="成功添加数量")
    failed_count: int = Field(..., description="失败数量")
    participants: List[ParticipantResponse] = Field(..., description="添加的参与者列表")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")


class UpdateParticipantResponse(BaseModel):
    """更新参与者响应模型"""
    success: bool = Field(..., description="是否成功")
    participant: Optional[ParticipantResponse] = Field(None, description="更新后的参与者信息")
    message: str = Field(..., description="响应消息")


class RemoveParticipantResponse(BaseModel):
    """移除参与者响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")


class InviteParticipantResponse(BaseModel):
    """邀请参与者响应模型"""
    success: bool = Field(..., description="是否成功")
    invited_count: int = Field(..., description="邀请数量")
    message: str = Field(..., description="响应消息")


class KickParticipantResponse(BaseModel):
    """踢出参与者响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")


class ParticipantStatistics(BaseModel):
    """参与者统计模型"""
    total_participants: int = Field(..., description="总参与者数")
    active_participants: int = Field(..., description="活跃参与者数")
    by_role: Dict[str, int] = Field(..., description="按角色统计")
    by_status: Dict[str, int] = Field(..., description="按状态统计")
    average_duration_minutes: float = Field(..., description="平均参与时长(分钟)")
    total_interaction_count: int = Field(..., description="总互动次数")