"""
WebRTC信令相关的Pydantic模型

本模块定义了WebRTC信令API的请求和响应数据模型，包括：
- WebRTC连接、信令的请求模型
- 音视频控制的响应模型
- 网络质量等状态模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SignalType(str, Enum):
    """信令类型枚举"""
    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice-candidate"
    MEDIA_CONTROL = "media-control"
    ROOM_EVENT = "room-event"


class MediaType(str, Enum):
    """媒体类型枚举"""
    AUDIO = "audio"
    VIDEO = "video"
    SCREEN = "screen"


class WebRTCSignalRequest(BaseModel):
    """WebRTC信令请求模型"""
    signal_type: SignalType = Field(..., description="信令类型")
    session_id: str = Field(..., description="会话ID")
    target_user_id: Optional[int] = Field(None, description="目标用户ID")
    signal_data: Dict[str, Any] = Field(..., description="信令数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")


class WebRTCOfferRequest(BaseModel):
    """WebRTC Offer请求模型"""
    session_id: str = Field(..., description="会话ID")
    sdp: str = Field(..., description="SDP描述")
    media_constraints: Optional[Dict[str, Any]] = Field(None, description="媒体约束")


class WebRTCAnswerRequest(BaseModel):
    """WebRTC Answer请求模型"""
    session_id: str = Field(..., description="会话ID")
    sdp: str = Field(..., description="SDP描述")


class ICECandidateRequest(BaseModel):
    """ICE候选请求模型"""
    session_id: str = Field(..., description="会话ID")
    candidate: str = Field(..., description="ICE候选")
    sdp_mid: Optional[str] = Field(None, description="SDP MID")
    sdp_m_line_index: Optional[int] = Field(None, description="SDP M-Line索引")


class MediaControlRequest(BaseModel):
    """媒体控制请求模型"""
    session_id: str = Field(..., description="会话ID")
    media_type: MediaType = Field(..., description="媒体类型")
    action: str = Field(..., description="控制动作")  # mute, unmute, enable, disable
    target_user_id: Optional[int] = Field(None, description="目标用户ID")


class WebRTCConfigResponse(BaseModel):
    """WebRTC配置响应模型"""
    ice_servers: List[Dict[str, Any]] = Field(..., description="ICE服务器配置")
    media_constraints: Dict[str, Any] = Field(..., description="媒体约束")
    room_config: Dict[str, Any] = Field(..., description="房间配置")
    session_config: Dict[str, Any] = Field(..., description="会话配置")

    class Config:
        from_attributes = True


class WebRTCSignalResponse(BaseModel):
    """WebRTC信令响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("信令处理成功", description="响应消息")
    signal_id: Optional[str] = Field(None, description="信令ID")
    response_data: Optional[Dict[str, Any]] = Field(None, description="响应数据")

    class Config:
        from_attributes = True


class ParticipantSession(BaseModel):
    """参与者会话模型"""
    session_id: str = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    room_id: str = Field(..., description="房间ID")
    connection_status: str = Field(..., description="连接状态")
    media_status: Dict[str, Any] = Field(..., description="媒体状态")
    network_quality: Dict[str, Any] = Field(..., description="网络质量")
    join_time: datetime = Field(..., description="加入时间")
    last_activity: datetime = Field(..., description="最后活动时间")

    class Config:
        from_attributes = True


class RoomInfo(BaseModel):
    """房间信息模型"""
    room_id: str = Field(..., description="房间ID")
    meeting_id: int = Field(..., description="会议ID")
    participant_count: int = Field(..., description="参与者数量")
    max_participants: int = Field(..., description="最大参与者数量")
    room_status: str = Field(..., description="房间状态")
    created_at: datetime = Field(..., description="创建时间")
    settings: Dict[str, Any] = Field(..., description="房间设置")

    class Config:
        from_attributes = True


class NetworkQuality(BaseModel):
    """网络质量模型"""
    user_id: int = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    upload_bandwidth: float = Field(..., description="上传带宽(kbps)")
    download_bandwidth: float = Field(..., description="下载带宽(kbps)")
    latency: int = Field(..., description="延迟(ms)")
    packet_loss: float = Field(..., description="丢包率(%)")
    jitter: float = Field(..., description="抖动(ms)")
    quality_score: int = Field(..., description="质量评分(1-5)")
    timestamp: datetime = Field(..., description="测量时间")

    class Config:
        from_attributes = True


class MediaStreamInfo(BaseModel):
    """媒体流信息模型"""
    stream_id: str = Field(..., description="流ID")
    user_id: int = Field(..., description="用户ID")
    media_type: MediaType = Field(..., description="媒体类型")
    is_active: bool = Field(..., description="是否活跃")
    resolution: Optional[str] = Field(None, description="分辨率")
    bitrate: Optional[int] = Field(None, description="比特率")
    frame_rate: Optional[int] = Field(None, description="帧率")
    codec: Optional[str] = Field(None, description="编解码器")

    class Config:
        from_attributes = True


class ScreenShareRequest(BaseModel):
    """屏幕共享请求模型"""
    session_id: str = Field(..., description="会话ID")
    share_type: str = Field("screen", description="共享类型")  # screen, window, tab
    audio_enabled: bool = Field(False, description="是否包含音频")
    resolution: Optional[str] = Field(None, description="分辨率")


class ScreenShareResponse(BaseModel):
    """屏幕共享响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("屏幕共享开始成功", description="响应消息")
    share_id: str = Field(..., description="共享ID")
    stream_info: MediaStreamInfo = Field(..., description="流信息")

    class Config:
        from_attributes = True


class StopScreenShareRequest(BaseModel):
    """停止屏幕共享请求模型"""
    session_id: str = Field(..., description="会话ID")
    share_id: str = Field(..., description="共享ID")


class StopScreenShareResponse(BaseModel):
    """停止屏幕共享响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("屏幕共享停止成功", description="响应消息")

    class Config:
        from_attributes = True