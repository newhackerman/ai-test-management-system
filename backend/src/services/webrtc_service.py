"""
WebRTC信令服务

本模块实现WebRTC实时通信的核心功能，包括：
- WebRTC房间管理
- 参与者会话管理
- WebRTC信令处理
- 音视频流控制
- 屏幕共享管理
- WebSocket消息处理
- 媒体服务器集成
- 网络质量监控
"""
import asyncio
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text, update, delete
from sqlalchemy.orm import selectinload, joinedload
from fastapi import Depends

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.meeting import Meeting, MeetingParticipant, ParticipantRole
from ..models.user import User
from ..services.permission_service import PermissionService
from .websocket_service import ConnectionManager

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信令类型"""
    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice-candidate"
    MEDIA_CONTROL = "media-control"
    SCREEN_SHARE = "screen-share"
    CHAT_MESSAGE = "chat-message"
    PARTICIPANT_UPDATE = "participant-update"
    ROOM_UPDATE = "room-update"


class MediaType(Enum):
    """媒体类型"""
    AUDIO = "audio"
    VIDEO = "video"
    SCREEN = "screen"


class ConnectionState(Enum):
    """连接状态"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    RECONNECTING = "reconnecting"


class NetworkQuality(Enum):
    """网络质量等级"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"           # 良好
    FAIR = "fair"           # 一般
    POOR = "poor"           # 较差
    VERY_POOR = "very_poor" # 很差


@dataclass
class ICEServer:
    """ICE服务器配置"""
    urls: str
    username: Optional[str] = None
    credential: Optional[str] = None


@dataclass
class MediaStreamConfig:
    """媒体流配置"""
    audio_enabled: bool = True
    video_enabled: bool = True
    audio_codec: str = "OPUS"
    video_codec: str = "VP8"
    video_resolution: str = "720p"
    video_framerate: int = 30
    audio_bitrate: int = 128  # kbps
    video_bitrate: int = 1000  # kbps


@dataclass
class ParticipantSession:
    """参与者会话信息"""
    session_id: str
    user_id: int
    room_id: str
    peer_connection_id: Optional[str] = None
    media_streams: Dict[str, Any] = field(default_factory=dict)
    ice_config: Dict[str, Any] = field(default_factory=dict)
    join_time: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    connection_state: ConnectionState = ConnectionState.CONNECTING
    network_quality: NetworkQuality = NetworkQuality.GOOD
    device_info: Dict[str, Any] = field(default_factory=dict)
    permissions: Dict[str, bool] = field(default_factory=dict)


@dataclass
class RoomInfo:
    """会议室信息"""
    room_id: str
    meeting_id: int
    media_server_id: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    participants: Dict[int, ParticipantSession] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_recording: bool = False
    screen_share_session: Optional[str] = None
    room_state: str = "active"


@dataclass
class ScreenShareInfo:
    """屏幕共享信息"""
    share_id: str
    user_id: int
    room_id: str
    session_id: str
    stream_config: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"


@dataclass
class NetworkStats:
    """网络统计信息"""
    session_id: str
    timestamp: datetime
    bytes_sent: int = 0
    bytes_received: int = 0
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    rtt: float = 0.0  # Round Trip Time (ms)
    jitter: float = 0.0  # ms
    bandwidth_up: float = 0.0  # kbps
    bandwidth_down: float = 0.0  # kbps


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}  # session_id -> websocket
        self.user_sessions: Dict[int, Set[str]] = {}  # user_id -> session_ids
        self.room_sessions: Dict[str, Set[str]] = {}  # room_id -> session_ids
        
    async def add_connection(self, session_id: str, websocket: Any, user_id: int, room_id: str):
        """添加WebSocket连接"""
        self.connections[session_id] = websocket
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        if room_id not in self.room_sessions:
            self.room_sessions[room_id] = set()
        self.room_sessions[room_id].add(session_id)
        
        logger.info(f"Added WebSocket connection for session {session_id}")
    
    async def remove_connection(self, session_id: str):
        """移除WebSocket连接"""
        if session_id in self.connections:
            del self.connections[session_id]
            
            # 从用户会话中移除
            for user_id, sessions in self.user_sessions.items():
                if session_id in sessions:
                    sessions.remove(session_id)
                    if not sessions:
                        del self.user_sessions[user_id]
                    break
            
            # 从房间会话中移除
            for room_id, sessions in self.room_sessions.items():
                if session_id in sessions:
                    sessions.remove(session_id)
                    if not sessions:
                        del self.room_sessions[room_id]
                    break
            
            logger.info(f"Removed WebSocket connection for session {session_id}")
    
    async def send_to_session(self, session_id: str, message: Dict[str, Any]) -> bool:
        """发送消息到指定会话"""
        if session_id in self.connections:
            try:
                websocket = self.connections[session_id]
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {str(e)}")
                await self.remove_connection(session_id)
        return False
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]) -> int:
        """发送消息到用户的所有会话"""
        sent_count = 0
        if user_id in self.user_sessions:
            for session_id in list(self.user_sessions[user_id]):
                if await self.send_to_session(session_id, message):
                    sent_count += 1
        return sent_count
    
    async def send_to_room(self, room_id: str, message: Dict[str, Any], exclude_session: Optional[str] = None) -> int:
        """发送消息到房间的所有会话"""
        sent_count = 0
        if room_id in self.room_sessions:
            for session_id in list(self.room_sessions[room_id]):
                if session_id != exclude_session:
                    if await self.send_to_session(session_id, message):
                        sent_count += 1
        return sent_count
    
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """广播消息到所有连接"""
        sent_count = 0
        for session_id in list(self.connections.keys()):
            if await self.send_to_session(session_id, message):
                sent_count += 1
        return sent_count


class WebRTCService:
    """WebRTC实时通信服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.permission_service = PermissionService(db)
        self.websocket_manager = WebSocketManager()
        
        # 活跃房间管理
        self.active_rooms: Dict[str, RoomInfo] = {}
        
        # 网络质量监控
        self.network_stats: Dict[str, List[NetworkStats]] = {}
        
        # ICE服务器配置
        self.ice_servers = [
            ICEServer(urls="stun:stun.l.google.com:19302"),
            ICEServer(urls="stun:stun1.l.google.com:19302"),
            # TURN服务器配置应该从环境变量读取
            # ICEServer(
            #     urls="turn:your-turn-server.com:3478",
            #     username="turn_username",
            #     credential="turn_password"
            # )
        ]
        
        # 媒体服务器配置
        self.media_server_config = {
            "type": "jitsi",  # 或 "agora", "custom"
            "server_url": "https://meet.jit.si",
            "api_key": None,  # 从环境变量读取
            "app_id": None    # 从环境变量读取
        }
    
    # 3.1 WebRTC房间管理
    
    async def create_room(self, meeting_id: int, room_config: Dict[str, Any]) -> RoomInfo:
        """
        创建会议室
        
        Args:
            meeting_id: 会议ID
            room_config: 房间配置
            
        Returns:
            房间信息对象
            
        Raises:
            NotFoundError: 会议不存在
            ValidationError: 配置无效
        """
        # 1. 验证会议存在
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 生成房间ID
        room_id = f"meeting_{meeting_id}_{int(time.time())}"
        
        # 3. 验证房间配置
        validated_config = await self._validate_room_config(room_config)
        
        # 4. 创建媒体服务器房间
        media_server_id = await self._create_media_server_room(room_id, validated_config)
        
        # 5. 创建房间信息
        room_info = RoomInfo(
            room_id=room_id,
            meeting_id=meeting_id,
            media_server_id=media_server_id,
            settings=validated_config,
            participants={},
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            is_recording=validated_config.get('recording_enabled', False),
            room_state="active"
        )
        
        # 6. 存储房间信息
        self.active_rooms[room_id] = room_info
        
        logger.info(f"Created WebRTC room {room_id} for meeting {meeting_id}")
        return room_info
    
    async def get_room_info(self, room_id: str) -> Optional[RoomInfo]:
        """获取房间信息"""
        return self.active_rooms.get(room_id)
    
    async def update_room_config(self, room_id: str, config_updates: Dict[str, Any], user_id: int) -> RoomInfo:
        """
        更新房间配置
        
        Args:
            room_id: 房间ID
            config_updates: 配置更新
            user_id: 操作用户ID
            
        Returns:
            更新后的房间信息
            
        Raises:
            NotFoundError: 房间不存在
            PermissionError: 权限不足
        """
        # 1. 获取房间信息
        room_info = self.active_rooms.get(room_id)
        if not room_info:
            raise NotFoundError("房间不存在")
        
        # 2. 验证权限
        await self._validate_room_management_permission(room_info.meeting_id, user_id)
        
        # 3. 验证配置更新
        validated_updates = await self._validate_room_config(config_updates)
        
        # 4. 更新房间配置
        room_info.settings.update(validated_updates)
        room_info.last_activity = datetime.utcnow()
        
        # 5. 通知房间内所有参与者
        await self._notify_room_config_update(room_id, validated_updates)
        
        logger.info(f"Updated room {room_id} config by user {user_id}")
        return room_info
    
    async def close_room(self, room_id: str, user_id: int) -> bool:
        """
        关闭房间
        
        Args:
            room_id: 房间ID
            user_id: 操作用户ID
            
        Returns:
            关闭是否成功
        """
        # 1. 获取房间信息
        room_info = self.active_rooms.get(room_id)
        if not room_info:
            return True  # 房间已不存在，视为成功
        
        # 2. 验证权限
        await self._validate_room_management_permission(room_info.meeting_id, user_id)
        
        # 3. 通知所有参与者房间即将关闭
        await self._notify_room_closing(room_id)
        
        # 4. 断开所有参与者连接
        for session in room_info.participants.values():
            await self._disconnect_participant_session(session.session_id)
        
        # 5. 清理媒体服务器房间
        if room_info.media_server_id:
            await self._cleanup_media_server_room(room_info.media_server_id)
        
        # 6. 移除房间
        room_info.room_state = "closed"
        del self.active_rooms[room_id]
        
        logger.info(f"Closed room {room_id} by user {user_id}")
        return True
    
    # 3.2 参与者会话管理
    
    async def join_room(self, room_id: str, user_id: int, join_config: Dict[str, Any]) -> ParticipantSession:
        """
        加入会议室
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            join_config: 加入配置
            
        Returns:
            参与者会话对象
            
        Raises:
            NotFoundError: 房间不存在
            PermissionError: 权限不足
            ValidationError: 房间已满或其他限制
        """
        # 1. 验证房间存在
        room_info = self.active_rooms.get(room_id)
        if not room_info:
            raise NotFoundError("房间不存在")
        
        # 2. 验证加入权限
        await self._validate_join_room_permission(room_info.meeting_id, user_id)
        
        # 3. 检查房间容量
        max_participants = room_info.settings.get('max_participants', 100)
        if len(room_info.participants) >= max_participants:
            raise ValidationError("房间已满")
        
        # 4. 检查用户是否已在房间中
        if user_id in room_info.participants:
            # 返回现有会话
            return room_info.participants[user_id]
        
        # 5. 生成会话ID和ICE配置
        session_id = f"session_{user_id}_{room_id}_{int(time.time())}"
        ice_config = await self._generate_ice_config()
        
        # 6. 获取用户权限
        permissions = await self._get_user_room_permissions(room_info.meeting_id, user_id)
        
        # 7. 创建参与者会话
        session = ParticipantSession(
            session_id=session_id,
            user_id=user_id,
            room_id=room_id,
            ice_config=ice_config,
            join_time=datetime.utcnow(),
            last_heartbeat=datetime.utcnow(),
            connection_state=ConnectionState.CONNECTING,
            device_info=join_config.get('device_info', {}),
            permissions=permissions
        )
        
        # 8. 添加到房间
        room_info.participants[user_id] = session
        room_info.last_activity = datetime.utcnow()
        
        # 9. 通知其他参与者
        await self._notify_participant_joined(room_id, user_id, session)
        
        logger.info(f"User {user_id} joined room {room_id} with session {session_id}")
        return session
    
    async def leave_room(self, room_id: str, user_id: int) -> bool:
        """
        离开会议室
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            离开是否成功
        """
        # 1. 获取房间信息
        room_info = self.active_rooms.get(room_id)
        if not room_info or user_id not in room_info.participants:
            return True  # 用户已不在房间中
        
        # 2. 获取会话信息
        session = room_info.participants[user_id]
        
        # 3. 断开会话连接
        await self._disconnect_participant_session(session.session_id)
        
        # 4. 从房间中移除
        del room_info.participants[user_id]
        room_info.last_activity = datetime.utcnow()
        
        # 5. 通知其他参与者
        await self._notify_participant_left(room_id, user_id)
        
        # 6. 如果是屏幕共享者，停止屏幕共享
        if room_info.screen_share_session == session.session_id:
            await self._stop_screen_share_internal(room_id, user_id)
        
        # 7. 如果房间为空，考虑清理
        if not room_info.participants:
            await self._schedule_room_cleanup(room_id)
        
        logger.info(f"User {user_id} left room {room_id}")
        return True
    
    async def get_participant_session(self, room_id: str, user_id: int) -> Optional[ParticipantSession]:
        """获取参与者会话信息"""
        room_info = self.active_rooms.get(room_id)
        if room_info:
            return room_info.participants.get(user_id)
        return None
    
    async def update_session_heartbeat(self, session_id: str) -> bool:
        """更新会话心跳"""
        for room_info in self.active_rooms.values():
            for session in room_info.participants.values():
                if session.session_id == session_id:
                    session.last_heartbeat = datetime.utcnow()
                    return True
        return False
    
    # 3.3 WebRTC信令处理
    
    async def handle_webrtc_signal(self, session_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理WebRTC信令
        
        Args:
            session_id: 会话ID
            signal_data: 信令数据
            
        Returns:
            处理结果
        """
        try:
            signal_type = SignalType(signal_data.get('type'))
            
            if signal_type == SignalType.OFFER:
                return await self._handle_offer(session_id, signal_data)
            elif signal_type == SignalType.ANSWER:
                return await self._handle_answer(session_id, signal_data)
            elif signal_type == SignalType.ICE_CANDIDATE:
                return await self._handle_ice_candidate(session_id, signal_data)
            elif signal_type == SignalType.MEDIA_CONTROL:
                return await self._handle_media_control(session_id, signal_data)
            else:
                raise ValidationError(f"不支持的信令类型: {signal_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebRTC signal for session {session_id}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _handle_offer(self, session_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理SDP Offer"""
        session = await self._get_session_by_id(session_id)
        if not session:
            return {"success": False, "error": "会话不存在"}
        
        # 1. 验证SDP格式
        sdp = signal_data.get('sdp')
        if not sdp:
            return {"success": False, "error": "缺少SDP数据"}
        
        # 2. 存储offer信息
        session.media_streams['offer'] = {
            'sdp': sdp,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 3. 转发给目标参与者
        target_user_id = signal_data.get('target_user_id')
        if target_user_id:
            await self._forward_signal_to_user(session.room_id, target_user_id, {
                'type': 'offer',
                'from_user_id': session.user_id,
                'session_id': session_id,
                'sdp': sdp
            })
        
        return {"success": True, "message": "Offer处理成功"}
    
    async def _handle_answer(self, session_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理SDP Answer"""
        session = await self._get_session_by_id(session_id)
        if not session:
            return {"success": False, "error": "会话不存在"}
        
        # 1. 验证SDP格式
        sdp = signal_data.get('sdp')
        if not sdp:
            return {"success": False, "error": "缺少SDP数据"}
        
        # 2. 存储answer信息
        session.media_streams['answer'] = {
            'sdp': sdp,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 3. 转发给目标参与者
        target_user_id = signal_data.get('target_user_id')
        if target_user_id:
            await self._forward_signal_to_user(session.room_id, target_user_id, {
                'type': 'answer',
                'from_user_id': session.user_id,
                'session_id': session_id,
                'sdp': sdp
            })
        
        # 4. 更新连接状态
        session.connection_state = ConnectionState.CONNECTED
        
        return {"success": True, "message": "Answer处理成功"}
    
    async def _handle_ice_candidate(self, session_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理ICE候选"""
        session = await self._get_session_by_id(session_id)
        if not session:
            return {"success": False, "error": "会话不存在"}
        
        # 1. 验证ICE候选格式
        candidate = signal_data.get('candidate')
        if not candidate:
            return {"success": False, "error": "缺少ICE候选数据"}
        
        # 2. 存储ICE候选
        if 'ice_candidates' not in session.media_streams:
            session.media_streams['ice_candidates'] = []
        
        session.media_streams['ice_candidates'].append({
            'candidate': candidate,
            'sdpMid': signal_data.get('sdpMid'),
            'sdpMLineIndex': signal_data.get('sdpMLineIndex'),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # 3. 转发给目标参与者
        target_user_id = signal_data.get('target_user_id')
        if target_user_id:
            await self._forward_signal_to_user(session.room_id, target_user_id, {
                'type': 'ice-candidate',
                'from_user_id': session.user_id,
                'session_id': session_id,
                'candidate': candidate,
                'sdpMid': signal_data.get('sdpMid'),
                'sdpMLineIndex': signal_data.get('sdpMLineIndex')
            })
        
        return {"success": True, "message": "ICE候选处理成功"}
    
    # 3.4 音视频流控制
    
    async def _handle_media_control(self, session_id: str, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理媒体控制信令"""
        session = await self._get_session_by_id(session_id)
        if not session:
            return {"success": False, "error": "会话不存在"}
        
        control_type = signal_data.get('control_type')
        
        if control_type == 'mute_audio':
            return await self._mute_audio(session, signal_data.get('muted', True))
        elif control_type == 'mute_video':
            return await self._mute_video(session, signal_data.get('muted', True))
        elif control_type == 'change_quality':
            return await self._change_media_quality(session, signal_data.get('quality_config', {}))
        else:
            return {"success": False, "error": f"不支持的媒体控制类型: {control_type}"}
    
    async def _mute_audio(self, session: ParticipantSession, muted: bool) -> Dict[str, Any]:
        """音频静音/取消静音"""
        # 1. 检查权限
        if not session.permissions.get('can_use_audio', True):
            return {"success": False, "error": "无音频权限"}
        
        # 2. 更新会话状态
        if 'media_state' not in session.media_streams:
            session.media_streams['media_state'] = {}
        
        session.media_streams['media_state']['audio_muted'] = muted
        session.media_streams['media_state']['audio_muted_at'] = datetime.utcnow().isoformat()
        
        # 3. 通知房间内其他参与者
        await self._notify_media_state_change(session.room_id, session.user_id, {
            'type': 'audio_mute',
            'muted': muted,
            'user_id': session.user_id
        })
        
        logger.info(f"User {session.user_id} audio {'muted' if muted else 'unmuted'} in room {session.room_id}")
        return {"success": True, "muted": muted}
    
    async def _mute_video(self, session: ParticipantSession, muted: bool) -> Dict[str, Any]:
        """视频静音/取消静音"""
        # 1. 检查权限
        if not session.permissions.get('can_use_video', True):
            return {"success": False, "error": "无视频权限"}
        
        # 2. 更新会话状态
        if 'media_state' not in session.media_streams:
            session.media_streams['media_state'] = {}
        
        session.media_streams['media_state']['video_muted'] = muted
        session.media_streams['media_state']['video_muted_at'] = datetime.utcnow().isoformat()
        
        # 3. 通知房间内其他参与者
        await self._notify_media_state_change(session.room_id, session.user_id, {
            'type': 'video_mute',
            'muted': muted,
            'user_id': session.user_id
        })
        
        logger.info(f"User {session.user_id} video {'muted' if muted else 'unmuted'} in room {session.room_id}")
        return {"success": True, "muted": muted}
    
    async def _change_media_quality(self, session: ParticipantSession, quality_config: Dict[str, Any]) -> Dict[str, Any]:
        """调整音视频质量"""
        # 1. 验证质量配置
        validated_config = await self._validate_quality_config(quality_config)
        
        # 2. 更新会话配置
        if 'quality_config' not in session.media_streams:
            session.media_streams['quality_config'] = {}
        
        session.media_streams['quality_config'].update(validated_config)
        session.media_streams['quality_config']['updated_at'] = datetime.utcnow().isoformat()
        
        # 3. 应用质量调整
        await self._apply_quality_adjustment(session, validated_config)
        
        logger.info(f"Updated media quality for user {session.user_id} in room {session.room_id}")
        return {"success": True, "quality_config": validated_config}
    
    # 3.5 屏幕共享管理
    
    async def start_screen_share(self, room_id: str, user_id: int, stream_config: Dict[str, Any]) -> ScreenShareInfo:
        """
        开始屏幕共享
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            stream_config: 流配置
            
        Returns:
            屏幕共享信息
            
        Raises:
            NotFoundError: 房间或会话不存在
            PermissionError: 权限不足
            ValidationError: 已有其他用户在共享屏幕
        """
        # 1. 获取房间和会话信息
        room_info = self.active_rooms.get(room_id)
        if not room_info:
            raise NotFoundError("房间不存在")
        
        session = room_info.participants.get(user_id)
        if not session:
            raise NotFoundError("用户未在房间中")
        
        # 2. 检查屏幕共享权限
        if not session.permissions.get('can_share_screen', False):
            raise PermissionError("无屏幕共享权限")
        
        # 3. 检查是否已有其他用户在共享屏幕
        if room_info.screen_share_session and room_info.screen_share_session != session.session_id:
            raise ValidationError("已有其他用户在共享屏幕")
        
        # 4. 创建屏幕共享信息
        share_id = f"screen_{user_id}_{room_id}_{int(time.time())}"
        screen_share = ScreenShareInfo(
            share_id=share_id,
            user_id=user_id,
            room_id=room_id,
            session_id=session.session_id,
            stream_config=stream_config,
            started_at=datetime.utcnow(),
            status="active"
        )
        
        # 5. 更新房间状态
        room_info.screen_share_session = session.session_id
        
        # 6. 更新会话状态
        session.media_streams['screen_share'] = {
            'share_id': share_id,
            'config': stream_config,
            'started_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        # 7. 通知房间内所有参与者
        await self._notify_screen_share_started(room_id, user_id, screen_share)
        
        logger.info(f"User {user_id} started screen sharing in room {room_id}")
        return screen_share
    
    async def stop_screen_share(self, room_id: str, user_id: int) -> bool:
        """
        停止屏幕共享
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            停止是否成功
        """
        return await self._stop_screen_share_internal(room_id, user_id)
    
    async def _stop_screen_share_internal(self, room_id: str, user_id: int) -> bool:
        """内部停止屏幕共享方法"""
        # 1. 获取房间信息
        room_info = self.active_rooms.get(room_id)
        if not room_info:
            return True
        
        session = room_info.participants.get(user_id)
        if not session:
            return True
        
        # 2. 检查是否在共享屏幕
        if room_info.screen_share_session != session.session_id:
            return True
        
        # 3. 更新房间状态
        room_info.screen_share_session = None
        
        # 4. 更新会话状态
        if 'screen_share' in session.media_streams:
            session.media_streams['screen_share']['status'] = 'stopped'
            session.media_streams['screen_share']['stopped_at'] = datetime.utcnow().isoformat()
        
        # 5. 通知房间内所有参与者
        await self._notify_screen_share_stopped(room_id, user_id)
        
        logger.info(f"User {user_id} stopped screen sharing in room {room_id}")
        return True
    
    # 3.6 WebSocket消息处理 (已在WebSocketManager中实现)
    
    # 3.7 媒体服务器集成
    
    async def _create_media_server_room(self, room_id: str, room_config: Dict[str, Any]) -> Optional[str]:
        """创建媒体服务器房间"""
        server_type = self.media_server_config.get('type', 'jitsi')
        
        if server_type == 'jitsi':
            return await self._create_jitsi_room(room_id, room_config)
        elif server_type == 'agora':
            return await self._create_agora_room(room_id, room_config)
        else:
            # 自研媒体服务器
            return await self._create_custom_room(room_id, room_config)
    
    async def _create_jitsi_room(self, room_id: str, room_config: Dict[str, Any]) -> str:
        """创建Jitsi Meet房间"""
        # 这里应该调用Jitsi Meet API创建房间
        # 暂时返回模拟的房间ID
        jitsi_room_id = f"jitsi_{room_id}"
        logger.info(f"Created Jitsi room: {jitsi_room_id}")
        return jitsi_room_id
    
    async def _create_agora_room(self, room_id: str, room_config: Dict[str, Any]) -> str:
        """创建Agora.io房间"""
        # 这里应该调用Agora.io API创建房间
        # 暂时返回模拟的房间ID
        agora_room_id = f"agora_{room_id}"
        logger.info(f"Created Agora room: {agora_room_id}")
        return agora_room_id
    
    async def _create_custom_room(self, room_id: str, room_config: Dict[str, Any]) -> str:
        """创建自研媒体服务器房间"""
        # 这里应该调用自研媒体服务器API创建房间
        custom_room_id = f"custom_{room_id}"
        logger.info(f"Created custom media server room: {custom_room_id}")
        return custom_room_id
    
    async def _cleanup_media_server_room(self, media_server_id: str) -> bool:
        """清理媒体服务器房间"""
        try:
            # 根据媒体服务器类型调用相应的清理API
            if media_server_id.startswith('jitsi_'):
                await self._cleanup_jitsi_room(media_server_id)
            elif media_server_id.startswith('agora_'):
                await self._cleanup_agora_room(media_server_id)
            elif media_server_id.startswith('custom_'):
                await self._cleanup_custom_room(media_server_id)
            
            logger.info(f"Cleaned up media server room: {media_server_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup media server room {media_server_id}: {str(e)}")
            return False
    
    # 3.8 网络质量监控
    
    async def update_network_stats(self, session_id: str, stats: Dict[str, Any]) -> bool:
        """
        更新网络统计信息
        
        Args:
            session_id: 会话ID
            stats: 统计数据
            
        Returns:
            更新是否成功
        """
        try:
            # 1. 创建网络统计对象
            network_stats = NetworkStats(
                session_id=session_id,
                timestamp=datetime.utcnow(),
                bytes_sent=stats.get('bytes_sent', 0),
                bytes_received=stats.get('bytes_received', 0),
                packets_sent=stats.get('packets_sent', 0),
                packets_received=stats.get('packets_received', 0),
                packets_lost=stats.get('packets_lost', 0),
                rtt=stats.get('rtt', 0.0),
                jitter=stats.get('jitter', 0.0),
                bandwidth_up=stats.get('bandwidth_up', 0.0),
                bandwidth_down=stats.get('bandwidth_down', 0.0)
            )
            
            # 2. 存储统计信息
            if session_id not in self.network_stats:
                self.network_stats[session_id] = []
            
            self.network_stats[session_id].append(network_stats)
            
            # 3. 保持最近100条记录
            if len(self.network_stats[session_id]) > 100:
                self.network_stats[session_id] = self.network_stats[session_id][-100:]
            
            # 4. 评估网络质量
            quality = await self._evaluate_network_quality(network_stats)
            
            # 5. 更新会话的网络质量
            session = await self._get_session_by_id(session_id)
            if session:
                old_quality = session.network_quality
                session.network_quality = quality
                
                # 如果质量发生显著变化，通知用户
                if self._is_quality_change_significant(old_quality, quality):
                    await self._notify_network_quality_change(session, quality)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update network stats for session {session_id}: {str(e)}")
            return False
    
    async def _evaluate_network_quality(self, stats: NetworkStats) -> NetworkQuality:
        """评估网络质量"""
        # 基于RTT、丢包率、抖动等指标评估网络质量
        rtt = stats.rtt
        packet_loss_rate = stats.packets_lost / max(stats.packets_sent, 1) * 100
        jitter = stats.jitter
        
        # 质量评估算法
        if rtt < 50 and packet_loss_rate < 1 and jitter < 10:
            return NetworkQuality.EXCELLENT
        elif rtt < 100 and packet_loss_rate < 3 and jitter < 20:
            return NetworkQuality.GOOD
        elif rtt < 200 and packet_loss_rate < 5 and jitter < 40:
            return NetworkQuality.FAIR
        elif rtt < 400 and packet_loss_rate < 10 and jitter < 80:
            return NetworkQuality.POOR
        else:
            return NetworkQuality.VERY_POOR
    
    async def get_network_quality_report(self, room_id: str) -> Dict[str, Any]:
        """获取房间网络质量报告"""
        room_info = self.active_rooms.get(room_id)
        if not room_info:
            return {"error": "房间不存在"}
        
        quality_report = {
            "room_id": room_id,
            "timestamp": datetime.utcnow().isoformat(),
            "participants": []
        }
        
        for user_id, session in room_info.participants.items():
            participant_stats = {
                "user_id": user_id,
                "session_id": session.session_id,
                "network_quality": session.network_quality.value,
                "connection_state": session.connection_state.value,
                "join_time": session.join_time.isoformat(),
                "last_heartbeat": session.last_heartbeat.isoformat()
            }
            
            # 添加最新的网络统计
            if session.session_id in self.network_stats:
                recent_stats = self.network_stats[session.session_id][-1]
                participant_stats["latest_stats"] = {
                    "rtt": recent_stats.rtt,
                    "packet_loss_rate": recent_stats.packets_lost / max(recent_stats.packets_sent, 1) * 100,
                    "jitter": recent_stats.jitter,
                    "bandwidth_up": recent_stats.bandwidth_up,
                    "bandwidth_down": recent_stats.bandwidth_down
                }
            
            quality_report["participants"].append(participant_stats)
        
        return quality_report
    
    # 辅助方法
    
    async def _get_meeting_by_id(self, meeting_id: int) -> Meeting:
        """根据ID获取会议"""
        query = select(Meeting).where(
            and_(Meeting.id == meeting_id, Meeting.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError("会议不存在")
        
        return meeting
    
    async def _get_session_by_id(self, session_id: str) -> Optional[ParticipantSession]:
        """根据会话ID获取会话"""
        for room_info in self.active_rooms.values():
            for session in room_info.participants.values():
                if session.session_id == session_id:
                    return session
        return None
    
    async def _validate_room_config(self, room_config: Dict[str, Any]) -> Dict[str, Any]:
        """验证房间配置"""
        validated_config = {
            'max_participants': min(max(room_config.get('max_participants', 100), 1), 1000),
            'video_codec': room_config.get('video_codec', 'VP8'),
            'audio_codec': room_config.get('audio_codec', 'OPUS'),
            'recording_enabled': room_config.get('recording_enabled', False),
            'screen_share_enabled': room_config.get('screen_share_enabled', True),
            'chat_enabled': room_config.get('chat_enabled', True),
            'whiteboard_enabled': room_config.get('whiteboard_enabled', True),
            'bitrate_limits': room_config.get('bitrate_limits', {
                'video': {'min': 150, 'max': 2000},
                'audio': {'min': 32, 'max': 128}
            })
        }
        
        return validated_config
    
    async def _validate_room_management_permission(self, meeting_id: int, user_id: int) -> None:
        """验证房间管理权限"""
        # 获取会议信息
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 组织者可以管理
        if meeting.organizer_id == user_id:
            return
        
        # 检查参与者角色
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        participant = result.scalar_one_or_none()
        
        if participant and participant.participant_role in [ParticipantRole.MODERATOR]:
            return
        
        raise PermissionError("无权限管理房间")
    
    async def _validate_join_room_permission(self, meeting_id: int, user_id: int) -> None:
        """验证加入房间权限"""
        # 检查是否是会议参与者
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise PermissionError("您未被邀请参加此会议")
    
    async def _get_user_room_permissions(self, meeting_id: int, user_id: int) -> Dict[str, bool]:
        """获取用户在房间中的权限"""
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            return {}
        
        return {
            'can_share_screen': participant.can_share_screen,
            'can_use_chat': participant.can_use_chat,
            'can_use_whiteboard': participant.can_use_whiteboard,
            'can_record': participant.can_record,
            'can_use_audio': True,  # 默认都有音频权限
            'can_use_video': True   # 默认都有视频权限
        }
    
    async def _generate_ice_config(self) -> Dict[str, Any]:
        """生成ICE配置"""
        return {
            'iceServers': [
                {'urls': server.urls, 'username': server.username, 'credential': server.credential}
                if server.username else {'urls': server.urls}
                for server in self.ice_servers
            ],
            'iceCandidatePoolSize': 10,
            'bundlePolicy': 'balanced',
            'rtcpMuxPolicy': 'require'
        }
    
    async def _validate_quality_config(self, quality_config: Dict[str, Any]) -> Dict[str, Any]:
        """验证质量配置"""
        validated_config = {}
        
        if 'video_bitrate' in quality_config:
            validated_config['video_bitrate'] = min(max(quality_config['video_bitrate'], 150), 5000)
        
        if 'audio_bitrate' in quality_config:
            validated_config['audio_bitrate'] = min(max(quality_config['audio_bitrate'], 32), 320)
        
        if 'video_resolution' in quality_config:
            valid_resolutions = ['240p', '360p', '480p', '720p', '1080p']
            if quality_config['video_resolution'] in valid_resolutions:
                validated_config['video_resolution'] = quality_config['video_resolution']
        
        if 'video_framerate' in quality_config:
            validated_config['video_framerate'] = min(max(quality_config['video_framerate'], 15), 60)
        
        return validated_config
    
    async def _apply_quality_adjustment(self, session: ParticipantSession, quality_config: Dict[str, Any]) -> None:
        """应用质量调整"""
        # 这里应该调用WebRTC API调整媒体质量
        # 暂时只记录日志
        logger.info(f"Applied quality adjustment for session {session.session_id}: {quality_config}")
    
    async def _disconnect_participant_session(self, session_id: str) -> None:
        """断开参与者会话"""
        # 移除WebSocket连接
        await self.websocket_manager.remove_connection(session_id)
        
        # 清理网络统计
        if session_id in self.network_stats:
            del self.network_stats[session_id]
    
    async def _schedule_room_cleanup(self, room_id: str) -> None:
        """安排房间清理"""
        # 延迟5分钟后清理空房间
        async def cleanup_task():
            await asyncio.sleep(300)  # 5分钟
            room_info = self.active_rooms.get(room_id)
            if room_info and not room_info.participants:
                await self.close_room(room_id, 0)  # 系统自动清理
        
        asyncio.create_task(cleanup_task())
    
    async def _forward_signal_to_user(self, room_id: str, user_id: int, signal_data: Dict[str, Any]) -> bool:
        """转发信令给指定用户"""
        return await self.websocket_manager.send_to_user(user_id, {
            'type': 'webrtc_signal',
            'room_id': room_id,
            'data': signal_data,
            'timestamp': datetime.utcnow().isoformat()
        }) > 0
    
    async def _is_quality_change_significant(self, old_quality: NetworkQuality, new_quality: NetworkQuality) -> bool:
        """判断网络质量变化是否显著"""
        quality_levels = {
            NetworkQuality.EXCELLENT: 5,
            NetworkQuality.GOOD: 4,
            NetworkQuality.FAIR: 3,
            NetworkQuality.POOR: 2,
            NetworkQuality.VERY_POOR: 1
        }
        
        old_level = quality_levels.get(old_quality, 3)
        new_level = quality_levels.get(new_quality, 3)
        
        # 质量变化超过1个等级认为是显著变化
        return abs(old_level - new_level) >= 1
    
    # 通知方法
    
    async def _notify_participant_joined(self, room_id: str, user_id: int, session: ParticipantSession) -> None:
        """通知参与者加入"""
        await self.websocket_manager.send_to_room(room_id, {
            'type': 'participant_joined',
            'room_id': room_id,
            'user_id': user_id,
            'session_id': session.session_id,
            'permissions': session.permissions,
            'timestamp': datetime.utcnow().isoformat()
        }, exclude_session=session.session_id)
    
    async def _notify_participant_left(self, room_id: str, user_id: int) -> None:
        """通知参与者离开"""
        await self.websocket_manager.send_to_room(room_id, {
            'type': 'participant_left',
            'room_id': room_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _notify_room_config_update(self, room_id: str, config_updates: Dict[str, Any]) -> None:
        """通知房间配置更新"""
        await self.websocket_manager.send_to_room(room_id, {
            'type': 'room_config_updated',
            'room_id': room_id,
            'config_updates': config_updates,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _notify_room_closing(self, room_id: str) -> None:
        """通知房间即将关闭"""
        await self.websocket_manager.send_to_room(room_id, {
            'type': 'room_closing',
            'room_id': room_id,
            'message': '会议室即将关闭，请保存重要信息',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _notify_media_state_change(self, room_id: str, user_id: int, media_change: Dict[str, Any]) -> None:
        """通知媒体状态变化"""
        await self.websocket_manager.send_to_room(room_id, {
            'type': 'media_state_changed',
            'room_id': room_id,
            'user_id': user_id,
            'change': media_change,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _notify_screen_share_started(self, room_id: str, user_id: int, screen_share: ScreenShareInfo) -> None:
        """通知屏幕共享开始"""
        await self.websocket_manager.send_to_room(room_id, {
            'type': 'screen_share_started',
            'room_id': room_id,
            'user_id': user_id,
            'share_id': screen_share.share_id,
            'config': screen_share.stream_config,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _notify_screen_share_stopped(self, room_id: str, user_id: int) -> None:
        """通知屏幕共享停止"""
        await self.websocket_manager.send_to_room(room_id, {
            'type': 'screen_share_stopped',
            'room_id': room_id,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _notify_network_quality_change(self, session: ParticipantSession, quality: NetworkQuality) -> None:
        """通知网络质量变化"""
        await self.websocket_manager.send_to_user(session.user_id, {
            'type': 'network_quality_changed',
            'room_id': session.room_id,
            'session_id': session.session_id,
            'quality': quality.value,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # 媒体服务器清理方法
    
    async def _cleanup_jitsi_room(self, media_server_id: str) -> None:
        """清理Jitsi房间"""
        # 调用Jitsi API清理房间
        logger.info(f"Cleaning up Jitsi room: {media_server_id}")
    
    async def _cleanup_agora_room(self, media_server_id: str) -> None:
        """清理Agora房间"""
        # 调用Agora API清理房间
        logger.info(f"Cleaning up Agora room: {media_server_id}")
    
    async def _cleanup_custom_room(self, media_server_id: str) -> None:
        """清理自研媒体服务器房间"""
        # 调用自研API清理房间
        logger.info(f"Cleaning up custom room: {media_server_id}")

def get_webrtc_service(db: AsyncSession = Depends(get_async_session)) -> WebRTCService:
    """
    获取WebRTC服务实例
    
    Args:
        db: 数据库会话（通过依赖注入）
        
    Returns:
        WebRTCService: WebRTC服务实例
    """
    return WebRTCService(db)