"""
视频会议管理器

本模块实现视频会议协作功能的核心管理，包括：
- 视频会议SDK集成管理
- 会议创建、加入、录制功能
- 屏幕共享和协作功能
- 第三方视频会议服务集成
- 会议状态和生命周期管理
"""
import asyncio
import json
import logging
import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.meeting import Meeting, MeetingParticipant, MeetingStatus, ParticipantRole
from ..models.user import User

logger = logging.getLogger(__name__)


class VideoSDKType(Enum):
    """视频会议SDK类型"""
    TENCENT_MEETING = "tencent_meeting"
    AGORA = "agora"
    JITSI = "jitsi"
    WEBRTC_NATIVE = "webrtc_native"
    ZOOM = "zoom"
    TEAMS = "teams"


class MeetingAction(Enum):
    """会议操作类型"""
    CREATE = "create"
    JOIN = "join"
    LEAVE = "leave"
    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    START_SCREEN_SHARE = "start_screen_share"
    STOP_SCREEN_SHARE = "stop_screen_share"
    MUTE_AUDIO = "mute_audio"
    UNMUTE_AUDIO = "unmute_audio"
    MUTE_VIDEO = "mute_video"
    UNMUTE_VIDEO = "unmute_video"


class CollaborationFeature(Enum):
    """协作功能类型"""
    SCREEN_SHARE = "screen_share"
    WHITEBOARD = "whiteboard"
    FILE_SHARE = "file_share"
    CHAT = "chat"
    RECORDING = "recording"
    BREAKOUT_ROOMS = "breakout_rooms"


@dataclass
class VideoSDKConfig:
    """视频SDK配置"""
    sdk_type: VideoSDKType
    app_id: str
    app_key: str
    secret_key: Optional[str] = None
    server_url: Optional[str] = None
    region: str = "global"
    features: List[CollaborationFeature] = field(default_factory=list)
    max_participants: int = 100
    recording_enabled: bool = True
    screen_share_enabled: bool = True
    chat_enabled: bool = True
    whiteboard_enabled: bool = False
    breakout_rooms_enabled: bool = False


@dataclass
class MeetingRoom:
    """会议室信息"""
    room_id: str
    meeting_id: int
    sdk_type: VideoSDKType
    sdk_room_id: str
    access_token: Optional[str] = None
    join_url: Optional[str] = None
    recording_id: Optional[str] = None
    screen_share_user_id: Optional[int] = None
    participants: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborationSession:
    """协作会话信息"""
    session_id: str
    user_id: int
    room_id: str
    features: List[CollaborationFeature]
    permissions: Dict[str, bool] = field(default_factory=dict)
    device_info: Dict[str, Any] = field(default_factory=dict)
    join_time: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"


class MeetingManager:
    """视频会议管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.active_rooms: Dict[str, MeetingRoom] = {}
        self.collaboration_sessions: Dict[str, CollaborationSession] = {}
        
        # 从环境变量加载SDK配置
        self.sdk_configs = self._load_sdk_configs()
        self.default_sdk = self._get_default_sdk()
        
        logger.info(f"MeetingManager initialized with {len(self.sdk_configs)} SDK configurations")
    
    def _load_sdk_configs(self) -> Dict[VideoSDKType, VideoSDKConfig]:
        """从环境变量加载SDK配置"""
        configs = {}
        
        # 腾讯会议配置
        if os.getenv('TENCENT_MEETING_APP_ID'):
            configs[VideoSDKType.TENCENT_MEETING] = VideoSDKConfig(
                sdk_type=VideoSDKType.TENCENT_MEETING,
                app_id=os.getenv('TENCENT_MEETING_APP_ID'),
                app_key=os.getenv('TENCENT_MEETING_APP_KEY'),
                secret_key=os.getenv('TENCENT_MEETING_SECRET_KEY'),
                server_url=os.getenv('TENCENT_MEETING_SERVER_URL', 'https://meeting.tencent.com'),
                features=[
                    CollaborationFeature.SCREEN_SHARE,
                    CollaborationFeature.CHAT,
                    CollaborationFeature.RECORDING,
                    CollaborationFeature.FILE_SHARE
                ]
            )
        
        # Agora配置
        if os.getenv('AGORA_APP_ID'):
            configs[VideoSDKType.AGORA] = VideoSDKConfig(
                sdk_type=VideoSDKType.AGORA,
                app_id=os.getenv('AGORA_APP_ID'),
                app_key=os.getenv('AGORA_APP_CERTIFICATE'),
                features=[
                    CollaborationFeature.SCREEN_SHARE,
                    CollaborationFeature.CHAT,
                    CollaborationFeature.RECORDING
                ]
            )
        
        # Jitsi配置
        if os.getenv('JITSI_SERVER_URL'):
            configs[VideoSDKType.JITSI] = VideoSDKConfig(
                sdk_type=VideoSDKType.JITSI,
                app_id=os.getenv('JITSI_APP_ID', 'jitsi-meet'),
                app_key=os.getenv('JITSI_APP_KEY', ''),
                server_url=os.getenv('JITSI_SERVER_URL', 'https://meet.jit.si'),
                features=[
                    CollaborationFeature.SCREEN_SHARE,
                    CollaborationFeature.CHAT,
                    CollaborationFeature.RECORDING,
                    CollaborationFeature.WHITEBOARD
                ]
            )
        
        # 原生WebRTC配置（默认）
        configs[VideoSDKType.WEBRTC_NATIVE] = VideoSDKConfig(
            sdk_type=VideoSDKType.WEBRTC_NATIVE,
            app_id='webrtc-native',
            app_key='native-key',
            features=[
                CollaborationFeature.SCREEN_SHARE,
                CollaborationFeature.CHAT,
                CollaborationFeature.FILE_SHARE
            ]
        )
        
        return configs
    
    def _get_default_sdk(self) -> VideoSDKType:
        """获取默认SDK类型"""
        # 优先级：腾讯会议 > Agora > Jitsi > 原生WebRTC
        priority_order = [
            VideoSDKType.TENCENT_MEETING,
            VideoSDKType.AGORA,
            VideoSDKType.JITSI,
            VideoSDKType.WEBRTC_NATIVE
        ]
        
        for sdk_type in priority_order:
            if sdk_type in self.sdk_configs:
                return sdk_type
        
        return VideoSDKType.WEBRTC_NATIVE
    
    async def create_meeting_room(self, meeting_id: int, sdk_type: Optional[VideoSDKType] = None, 
                                room_config: Optional[Dict[str, Any]] = None) -> MeetingRoom:
        """
        创建会议室
        
        Args:
            meeting_id: 会议ID
            sdk_type: 指定的SDK类型，如果为None则使用默认SDK
            room_config: 房间配置
            
        Returns:
            会议室信息
            
        Raises:
            NotFoundError: 会议不存在
            ValidationError: 配置无效
        """
        # 1. 验证会议存在
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 确定使用的SDK
        if sdk_type is None:
            sdk_type = self._get_optimal_sdk_for_meeting(meeting)
        
        if sdk_type not in self.sdk_configs:
            raise ValidationError(f"不支持的SDK类型: {sdk_type}")
        
        sdk_config = self.sdk_configs[sdk_type]
        
        # 3. 生成房间ID
        room_id = f"room_{meeting_id}_{int(datetime.utcnow().timestamp())}"
        
        # 4. 根据SDK类型创建房间
        if sdk_type == VideoSDKType.TENCENT_MEETING:
            sdk_room_info = await self._create_tencent_meeting_room(meeting, sdk_config, room_config)
        elif sdk_type == VideoSDKType.AGORA:
            sdk_room_info = await self._create_agora_room(meeting, sdk_config, room_config)
        elif sdk_type == VideoSDKType.JITSI:
            sdk_room_info = await self._create_jitsi_room(meeting, sdk_config, room_config)
        else:
            sdk_room_info = await self._create_webrtc_room(meeting, sdk_config, room_config)
        
        # 5. 创建会议室对象
        meeting_room = MeetingRoom(
            room_id=room_id,
            meeting_id=meeting_id,
            sdk_type=sdk_type,
            sdk_room_id=sdk_room_info['room_id'],
            access_token=sdk_room_info.get('access_token'),
            join_url=sdk_room_info.get('join_url'),
            created_at=datetime.utcnow(),
            status="active",
            settings=room_config or {}
        )
        
        # 6. 存储房间信息
        self.active_rooms[room_id] = meeting_room
        
        logger.info(f"Created meeting room {room_id} for meeting {meeting_id} using {sdk_type}")
        return meeting_room
    
    async def join_meeting(self, room_id: str, user_id: int, join_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        加入会议
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            join_options: 加入选项
            
        Returns:
            加入结果信息
            
        Raises:
            NotFoundError: 房间不存在
            PermissionError: 权限不足
        """
        # 1. 获取房间信息
        room = self.active_rooms.get(room_id)
        if not room:
            raise NotFoundError("会议室不存在")
        
        # 2. 验证加入权限
        await self._validate_join_permission(room.meeting_id, user_id)
        
        # 3. 检查房间容量
        sdk_config = self.sdk_configs[room.sdk_type]
        if len(room.participants) >= sdk_config.max_participants:
            raise ValidationError("会议室已满")
        
        # 4. 获取用户信息和权限
        user = await self._get_user_by_id(user_id)
        participant = await self._get_meeting_participant(room.meeting_id, user_id)
        
        # 5. 根据SDK类型生成加入信息
        if room.sdk_type == VideoSDKType.TENCENT_MEETING:
            join_info = await self._generate_tencent_join_info(room, user, participant, join_options)
        elif room.sdk_type == VideoSDKType.AGORA:
            join_info = await self._generate_agora_join_info(room, user, participant, join_options)
        elif room.sdk_type == VideoSDKType.JITSI:
            join_info = await self._generate_jitsi_join_info(room, user, participant, join_options)
        else:
            join_info = await self._generate_webrtc_join_info(room, user, participant, join_options)
        
        # 6. 添加参与者到房间
        room.participants[user_id] = {
            'user_id': user_id,
            'username': user.username,
            'role': participant.participant_role.value if participant else 'participant',
            'join_time': datetime.utcnow().isoformat(),
            'permissions': self._get_participant_permissions(participant),
            'device_info': join_options.get('device_info', {}) if join_options else {}
        }
        
        # 7. 创建协作会话
        session_id = await self._create_collaboration_session(room_id, user_id, participant)
        
        logger.info(f"User {user_id} joined meeting room {room_id}")
        
        return {
            'success': True,
            'room_id': room_id,
            'session_id': session_id,
            'sdk_type': room.sdk_type.value,
            'join_info': join_info,
            'collaboration_features': self._get_available_features(room.sdk_type),
            'participant_info': room.participants[user_id]
        }
    
    async def start_recording(self, room_id: str, user_id: int, recording_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        开始录制
        
        Args:
            room_id: 房间ID
            user_id: 操作用户ID
            recording_config: 录制配置
            
        Returns:
            录制信息
            
        Raises:
            NotFoundError: 房间不存在
            PermissionError: 权限不足
        """
        # 1. 获取房间信息
        room = self.active_rooms.get(room_id)
        if not room:
            raise NotFoundError("会议室不存在")
        
        # 2. 验证录制权限
        await self._validate_recording_permission(room.meeting_id, user_id)
        
        # 3. 检查是否已在录制
        if room.recording_id:
            raise ValidationError("会议已在录制中")
        
        # 4. 根据SDK类型开始录制
        if room.sdk_type == VideoSDKType.TENCENT_MEETING:
            recording_info = await self._start_tencent_recording(room, recording_config)
        elif room.sdk_type == VideoSDKType.AGORA:
            recording_info = await self._start_agora_recording(room, recording_config)
        elif room.sdk_type == VideoSDKType.JITSI:
            recording_info = await self._start_jitsi_recording(room, recording_config)
        else:
            recording_info = await self._start_webrtc_recording(room, recording_config)
        
        # 5. 更新房间录制状态
        room.recording_id = recording_info['recording_id']
        
        logger.info(f"Started recording for room {room_id} by user {user_id}")
        
        return {
            'success': True,
            'recording_id': recording_info['recording_id'],
            'recording_url': recording_info.get('recording_url'),
            'started_at': datetime.utcnow().isoformat()
        }
    
    async def stop_recording(self, room_id: str, user_id: int) -> Dict[str, Any]:
        """
        停止录制
        
        Args:
            room_id: 房间ID
            user_id: 操作用户ID
            
        Returns:
            录制结果信息
        """
        # 1. 获取房间信息
        room = self.active_rooms.get(room_id)
        if not room:
            raise NotFoundError("会议室不存在")
        
        # 2. 验证录制权限
        await self._validate_recording_permission(room.meeting_id, user_id)
        
        # 3. 检查是否在录制
        if not room.recording_id:
            raise ValidationError("会议未在录制")
        
        # 4. 根据SDK类型停止录制
        if room.sdk_type == VideoSDKType.TENCENT_MEETING:
            recording_result = await self._stop_tencent_recording(room)
        elif room.sdk_type == VideoSDKType.AGORA:
            recording_result = await self._stop_agora_recording(room)
        elif room.sdk_type == VideoSDKType.JITSI:
            recording_result = await self._stop_jitsi_recording(room)
        else:
            recording_result = await self._stop_webrtc_recording(room)
        
        # 5. 清除房间录制状态
        recording_id = room.recording_id
        room.recording_id = None
        
        logger.info(f"Stopped recording {recording_id} for room {room_id} by user {user_id}")
        
        return {
            'success': True,
            'recording_id': recording_id,
            'recording_url': recording_result.get('recording_url'),
            'file_size': recording_result.get('file_size'),
            'duration': recording_result.get('duration'),
            'stopped_at': datetime.utcnow().isoformat()
        }
    
    async def start_screen_share(self, room_id: str, user_id: int, share_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        开始屏幕共享
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            share_config: 共享配置
            
        Returns:
            屏幕共享信息
        """
        # 1. 获取房间信息
        room = self.active_rooms.get(room_id)
        if not room:
            raise NotFoundError("会议室不存在")
        
        # 2. 验证屏幕共享权限
        await self._validate_screen_share_permission(room.meeting_id, user_id)
        
        # 3. 检查是否已有人在共享屏幕
        if room.screen_share_user_id and room.screen_share_user_id != user_id:
            raise ValidationError("已有其他用户在共享屏幕")
        
        # 4. 根据SDK类型开始屏幕共享
        if room.sdk_type == VideoSDKType.TENCENT_MEETING:
            share_info = await self._start_tencent_screen_share(room, user_id, share_config)
        elif room.sdk_type == VideoSDKType.AGORA:
            share_info = await self._start_agora_screen_share(room, user_id, share_config)
        elif room.sdk_type == VideoSDKType.JITSI:
            share_info = await self._start_jitsi_screen_share(room, user_id, share_config)
        else:
            share_info = await self._start_webrtc_screen_share(room, user_id, share_config)
        
        # 5. 更新房间屏幕共享状态
        room.screen_share_user_id = user_id
        
        logger.info(f"User {user_id} started screen sharing in room {room_id}")
        
        return {
            'success': True,
            'share_id': share_info['share_id'],
            'share_url': share_info.get('share_url'),
            'started_at': datetime.utcnow().isoformat()
        }
    
    async def stop_screen_share(self, room_id: str, user_id: int) -> Dict[str, Any]:
        """
        停止屏幕共享
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            停止结果
        """
        # 1. 获取房间信息
        room = self.active_rooms.get(room_id)
        if not room:
            raise NotFoundError("会议室不存在")
        
        # 2. 检查是否在共享屏幕
        if room.screen_share_user_id != user_id:
            raise ValidationError("您未在共享屏幕")
        
        # 3. 根据SDK类型停止屏幕共享
        if room.sdk_type == VideoSDKType.TENCENT_MEETING:
            await self._stop_tencent_screen_share(room, user_id)
        elif room.sdk_type == VideoSDKType.AGORA:
            await self._stop_agora_screen_share(room, user_id)
        elif room.sdk_type == VideoSDKType.JITSI:
            await self._stop_jitsi_screen_share(room, user_id)
        else:
            await self._stop_webrtc_screen_share(room, user_id)
        
        # 4. 清除房间屏幕共享状态
        room.screen_share_user_id = None
        
        logger.info(f"User {user_id} stopped screen sharing in room {room_id}")
        
        return {
            'success': True,
            'stopped_at': datetime.utcnow().isoformat()
        }
    
    async def leave_meeting(self, room_id: str, user_id: int) -> Dict[str, Any]:
        """
        离开会议
        
        Args:
            room_id: 房间ID
            user_id: 用户ID
            
        Returns:
            离开结果
        """
        # 1. 获取房间信息
        room = self.active_rooms.get(room_id)
        if not room or user_id not in room.participants:
            return {'success': True, 'message': '用户已不在会议中'}
        
        # 2. 如果用户在共享屏幕，先停止共享
        if room.screen_share_user_id == user_id:
            await self.stop_screen_share(room_id, user_id)
        
        # 3. 移除参与者
        participant_info = room.participants.pop(user_id, {})
        
        # 4. 清理协作会话
        await self._cleanup_collaboration_session(room_id, user_id)
        
        # 5. 如果房间为空，考虑清理房间
        if not room.participants:
            await self._schedule_room_cleanup(room_id)
        
        logger.info(f"User {user_id} left meeting room {room_id}")
        
        return {
            'success': True,
            'left_at': datetime.utcnow().isoformat(),
            'session_duration': self._calculate_session_duration(participant_info.get('join_time'))
        }
    
    async def get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取房间信息"""
        room = self.active_rooms.get(room_id)
        if not room:
            return None
        
        return {
            'room_id': room.room_id,
            'meeting_id': room.meeting_id,
            'sdk_type': room.sdk_type.value,
            'participant_count': len(room.participants),
            'participants': list(room.participants.values()),
            'is_recording': bool(room.recording_id),
            'screen_share_user_id': room.screen_share_user_id,
            'created_at': room.created_at.isoformat(),
            'status': room.status,
            'available_features': self._get_available_features(room.sdk_type)
        }
    
    # 私有辅助方法
    
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
    
    async def _get_user_by_id(self, user_id: int) -> User:
        """根据ID获取用户"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("用户不存在")
        
        return user
    
    async def _get_meeting_participant(self, meeting_id: int, user_id: int) -> Optional[MeetingParticipant]:
        """获取会议参与者信息"""
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    def _get_optimal_sdk_for_meeting(self, meeting: Meeting) -> VideoSDKType:
        """为会议选择最优的SDK"""
        # 根据会议类型、参与者数量等因素选择最优SDK
        participant_count = getattr(meeting, 'participant_count', 0)
        
        if participant_count > 50:
            # 大型会议优先使用腾讯会议或Agora
            if VideoSDKType.TENCENT_MEETING in self.sdk_configs:
                return VideoSDKType.TENCENT_MEETING
            elif VideoSDKType.AGORA in self.sdk_configs:
                return VideoSDKType.AGORA
        
        return self.default_sdk
    
    def _get_available_features(self, sdk_type: VideoSDKType) -> List[str]:
        """获取SDK支持的功能列表"""
        if sdk_type in self.sdk_configs:
            return [feature.value for feature in self.sdk_configs[sdk_type].features]
        return []
    
    def _get_participant_permissions(self, participant: Optional[MeetingParticipant]) -> Dict[str, bool]:
        """获取参与者权限"""
        if not participant:
            return {
                'can_share_screen': False,
                'can_record': False,
                'can_use_chat': True,
                'can_use_whiteboard': False
            }
        
        return {
            'can_share_screen': participant.can_share_screen,
            'can_record': participant.can_record,
            'can_use_chat': participant.can_use_chat,
            'can_use_whiteboard': participant.can_use_whiteboard
        }
    
    async def _validate_join_permission(self, meeting_id: int, user_id: int) -> None:
        """验证加入权限"""
        participant = await self._get_meeting_participant(meeting_id, user_id)
        if not participant:
            raise PermissionError("您未被邀请参加此会议")
    
    async def _validate_recording_permission(self, meeting_id: int, user_id: int) -> None:
        """验证录制权限"""
        participant = await self._get_meeting_participant(meeting_id, user_id)
        if not participant or not participant.can_record:
            raise PermissionError("无录制权限")
    
    async def _validate_screen_share_permission(self, meeting_id: int, user_id: int) -> None:
        """验证屏幕共享权限"""
        participant = await self._get_meeting_participant(meeting_id, user_id)
        if not participant or not participant.can_share_screen:
            raise PermissionError("无屏幕共享权限")
    
    async def _create_collaboration_session(self, room_id: str, user_id: int, 
                                          participant: Optional[MeetingParticipant]) -> str:
        """创建协作会话"""
        session_id = f"collab_{user_id}_{room_id}_{int(datetime.utcnow().timestamp())}"
        
        # 确定可用的协作功能
        room = self.active_rooms[room_id]
        available_features = []
        
        for feature in self.sdk_configs[room.sdk_type].features:
            if self._check_feature_permission(feature, participant):
                available_features.append(feature)
        
        session = CollaborationSession(
            session_id=session_id,
            user_id=user_id,
            room_id=room_id,
            features=available_features,
            permissions=self._get_participant_permissions(participant),
            join_time=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            status="active"
        )
        
        self.collaboration_sessions[session_id] = session
        return session_id
    
    def _check_feature_permission(self, feature: CollaborationFeature, 
                                participant: Optional[MeetingParticipant]) -> bool:
        """检查功能权限"""
        if not participant:
            return feature in [CollaborationFeature.CHAT]
        
        if feature == CollaborationFeature.SCREEN_SHARE:
            return participant.can_share_screen
        elif feature == CollaborationFeature.RECORDING:
            return participant.can_record
        elif feature == CollaborationFeature.CHAT:
            return participant.can_use_chat
        elif feature == CollaborationFeature.WHITEBOARD:
            return participant.can_use_whiteboard
        
        return True
    
    async def _cleanup_collaboration_session(self, room_id: str, user_id: int) -> None:
        """清理协作会话"""
        sessions_to_remove = []
        for session_id, session in self.collaboration_sessions.items():
            if session.room_id == room_id and session.user_id == user_id:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.collaboration_sessions[session_id]
    
    def _calculate_session_duration(self, join_time_str: Optional[str]) -> Optional[int]:
        """计算会话时长（分钟）"""
        if not join_time_str:
            return None
        
        try:
            join_time = datetime.fromisoformat(join_time_str.replace('Z', '+00:00'))
            duration = datetime.utcnow() - join_time
            return int(duration.total_seconds() / 60)
        except:
            return None
    
    async def _schedule_room_cleanup(self, room_id: str) -> None:
        """安排房间清理"""
        # 延迟5分钟后清理空房间
        await asyncio.sleep(300)
        
        room = self.active_rooms.get(room_id)
        if room and not room.participants:
            room.status = "inactive"
            # 可以选择立即删除或标记为非活跃状态
            logger.info(f"Scheduled cleanup for empty room {room_id}")
    
    # SDK特定的实现方法（这些方法需要根据具体SDK的API来实现）
    
    async def _create_tencent_meeting_room(self, meeting: Meeting, sdk_config: VideoSDKConfig, 
                                         room_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """创建腾讯会议房间"""
        # 这里应该调用腾讯会议API创建会议
        # 暂时返回模拟数据
        return {
            'room_id': f"tencent_{meeting.id}_{secrets.token_hex(8)}",
            'join_url': f"https://meeting.tencent.com/join/{meeting.meeting_code}",
            'access_token': secrets.token_hex(32)
        }
    
    async def _create_agora_room(self, meeting: Meeting, sdk_config: VideoSDKConfig, 
                               room_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """创建Agora房间"""
        # 这里应该调用Agora API创建频道
        return {
            'room_id': f"agora_{meeting.id}_{secrets.token_hex(8)}",
            'access_token': secrets.token_hex(32)
        }
    
    async def _create_jitsi_room(self, meeting: Meeting, sdk_config: VideoSDKConfig, 
                               room_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """创建Jitsi房间"""
        room_name = f"meeting_{meeting.id}_{secrets.token_hex(4)}"
        return {
            'room_id': room_name,
            'join_url': f"{sdk_config.server_url}/{room_name}"
        }
    
    async def _create_webrtc_room(self, meeting: Meeting, sdk_config: VideoSDKConfig, 
                                room_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """创建原生WebRTC房间"""
        return {
            'room_id': f"webrtc_{meeting.id}_{secrets.token_hex(8)}"
        }
    
    # 加入会议的SDK特定实现
    
    async def _generate_tencent_join_info(self, room: MeetingRoom, user: User, 
                                        participant: Optional[MeetingParticipant], 
                                        join_options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """生成腾讯会议加入信息"""
        return {
            'join_url': room.join_url,
            'access_token': room.access_token,
            'user_id': str(user.id),
            'username': user.username,
            'role': participant.participant_role.value if participant else 'participant'
        }
    
    async def _generate_agora_join_info(self, room: MeetingRoom, user: User, 
                                      participant: Optional[MeetingParticipant], 
                                      join_options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """生成Agora加入信息"""
        return {
            'channel_name': room.sdk_room_id,
            'access_token': room.access_token,
            'user_id': user.id,
            'username': user.username
        }
    
    async def _generate_jitsi_join_info(self, room: MeetingRoom, user: User, 
                                      participant: Optional[MeetingParticipant], 
                                      join_options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """生成Jitsi加入信息"""
        return {
            'join_url': room.join_url,
            'room_name': room.sdk_room_id,
            'display_name': user.username
        }
    
    async def _generate_webrtc_join_info(self, room: MeetingRoom, user: User, 
                                       participant: Optional[MeetingParticipant], 
                                       join_options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """生成原生WebRTC加入信息"""
        return {
            'room_id': room.sdk_room_id,
            'user_id': user.id,
            'username': user.username,
            'ice_servers': [
                {'urls': 'stun:stun.l.google.com:19302'},
                {'urls': 'stun:stun1.l.google.com:19302'}
            ]
        }
    
    # 录制功能的SDK特定实现
    
    async def _start_tencent_recording(self, room: MeetingRoom, 
                                     recording_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """开始腾讯会议录制"""
        recording_id = f"tencent_rec_{secrets.token_hex(8)}"
        return {
            'recording_id': recording_id,
            'recording_url': f"https://meeting.tencent.com/recording/{recording_id}"
        }
    
    async def _start_agora_recording(self, room: MeetingRoom, 
                                   recording_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """开始Agora录制"""
        recording_id = f"agora_rec_{secrets.token_hex(8)}"
        return {
            'recording_id': recording_id
        }
    
    async def _start_jitsi_recording(self, room: MeetingRoom, 
                                   recording_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """开始Jitsi录制"""
        recording_id = f"jitsi_rec_{secrets.token_hex(8)}"
        return {
            'recording_id': recording_id
        }
    
    async def _start_webrtc_recording(self, room: MeetingRoom, 
                                    recording_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """开始WebRTC录制"""
        recording_id = f"webrtc_rec_{secrets.token_hex(8)}"
        return {
            'recording_id': recording_id
        }
    
    # 停止录制的SDK特定实现
    
    async def _stop_tencent_recording(self, room: MeetingRoom) -> Dict[str, Any]:
        """停止腾讯会议录制"""
        return {
            'recording_url': f"https://meeting.tencent.com/recording/{room.recording_id}",
            'file_size': 1024 * 1024 * 100,  # 100MB
            'duration': 3600  # 1小时
        }
    
    async def _stop_agora_recording(self, room: MeetingRoom) -> Dict[str, Any]:
        """停止Agora录制"""
        return {
            'file_size': 1024 * 1024 * 80,
            'duration': 3000
        }
    
    async def _stop_jitsi_recording(self, room: MeetingRoom) -> Dict[str, Any]:
        """停止Jitsi录制"""
        return {
            'recording_url': f"https://meet.jit.si/recording/{room.recording_id}",
            'file_size': 1024 * 1024 * 90,
            'duration': 3300
        }
    
    async def _stop_webrtc_recording(self, room: MeetingRoom) -> Dict[str, Any]:
        """停止WebRTC录制"""
        return {
            'file_size': 1024 * 1024 * 70,
            'duration': 2800
        }
    
    # 屏幕共享的SDK特定实现
    
    async def _start_tencent_screen_share(self, room: MeetingRoom, user_id: int, 
                                        share_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """开始腾讯会议屏幕共享"""
        share_id = f"tencent_share_{secrets.token_hex(8)}"
        return {
            'share_id': share_id,
            'share_url': f"https://meeting.tencent.com/share/{share_id}"
        }
    
    async def _start_agora_screen_share(self, room: MeetingRoom, user_id: int, 
                                      share_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """开始Agora屏幕共享"""
        share_id = f"agora_share_{secrets.token_hex(8)}"
        return {
            'share_id': share_id
        }
    
    async def _start_jitsi_screen_share(self, room: MeetingRoom, user_id: int, 
                                      share_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """开始Jitsi屏幕共享"""
        share_id = f"jitsi_share_{secrets.token_hex(8)}"
        return {
            'share_id': share_id
        }
    
    async def _start_webrtc_screen_share(self, room: MeetingRoom, user_id: int, 
                                       share_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """开始WebRTC屏幕共享"""
        share_id = f"webrtc_share_{secrets.token_hex(8)}"
        return {
            'share_id': share_id
        }
    
    # 停止屏幕共享的SDK特定实现
    
    async def _stop_tencent_screen_share(self, room: MeetingRoom, user_id: int) -> None:
        """停止腾讯会议屏幕共享"""
        logger.info(f"Stopped Tencent screen share for user {user_id} in room {room.room_id}")
    
    async def _stop_agora_screen_share(self, room: MeetingRoom, user_id: int) -> None:
        """停止Agora屏幕共享"""
        logger.info(f"Stopped Agora screen share for user {user_id} in room {room.room_id}")
    
    async def _stop_jitsi_screen_share(self, room: MeetingRoom, user_id: int) -> None:
        """停止Jitsi屏幕共享"""
        logger.info(f"Stopped Jitsi screen share for user {user_id} in room {room.room_id}")
    
    async def _stop_webrtc_screen_share(self, room: MeetingRoom, user_id: int) -> None:
        """停止WebRTC屏幕共享"""
        logger.info(f"Stopped WebRTC screen share for user {user_id} in room {room.room_id}")