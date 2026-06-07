"""
仪表板多设备同步服务

实现多设备连接管理、状态同步、冲突处理和一致性保证功能
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict

from ..models.websocket_connection import ClientType
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """设备类型"""
    DESKTOP = "DESKTOP"  # 桌面端
    MOBILE = "MOBILE"  # 移动端
    TABLET = "TABLET"  # 平板端
    WEB = "WEB"  # 网页端


class DeviceStatus(Enum):
    """设备状态"""
    ONLINE = "ONLINE"  # 在线
    OFFLINE = "OFFLINE"  # 离线
    SYNCING = "SYNCING"  # 同步中
    CONFLICT = "CONFLICT"  # 冲突状态


class SyncOperation(Enum):
    """同步操作类型"""
    CREATE = "CREATE"  # 创建
    UPDATE = "UPDATE"  # 更新
    DELETE = "DELETE"  # 删除
    MERGE = "MERGE"  # 合并


class ConflictResolution(Enum):
    """冲突解决策略"""
    LAST_WRITE_WINS = "LAST_WRITE_WINS"  # 最后写入获胜
    FIRST_WRITE_WINS = "FIRST_WRITE_WINS"  # 首次写入获胜
    MANUAL_RESOLVE = "MANUAL_RESOLVE"  # 手动解决
    DEVICE_PRIORITY = "DEVICE_PRIORITY"  # 设备优先级
    USER_CHOICE = "USER_CHOICE"  # 用户选择


@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    user_id: int
    device_type: DeviceType
    device_name: str
    platform: str
    browser: Optional[str] = None
    version: Optional[str] = None
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    last_seen: Optional[datetime] = None
    is_primary: bool = False
    priority: int = 1  # 1-10, 数字越大优先级越高
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['device_type'] = self.device_type.value
        if self.last_seen:
            result['last_seen'] = self.last_seen.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        """从字典创建"""
        if 'device_type' in data:
            data['device_type'] = DeviceType(data['device_type'])
        if 'last_seen' in data and data['last_seen']:
            data['last_seen'] = datetime.fromisoformat(data['last_seen'])
        return cls(**data)


@dataclass
class SyncState:
    """同步状态"""
    state_id: str
    user_id: int
    data_type: str
    data_content: Any
    version: int
    timestamp: float
    device_id: str
    checksum: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncState':
        """从字典创建"""
        return cls(**data)


@dataclass
class SyncConflict:
    """同步冲突"""
    conflict_id: str
    user_id: int
    data_type: str
    state_id: str
    conflicting_states: List[SyncState]
    resolution_strategy: ConflictResolution
    resolved: bool = False
    resolution_result: Optional[SyncState] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['resolution_strategy'] = self.resolution_strategy.value
        result['conflicting_states'] = [state.to_dict() for state in self.conflicting_states]
        if self.resolution_result:
            result['resolution_result'] = self.resolution_result.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncConflict':
        """从字典创建"""
        data['resolution_strategy'] = ConflictResolution(data['resolution_strategy'])
        data['conflicting_states'] = [
            SyncState.from_dict(state) for state in data['conflicting_states']
        ]
        if data.get('resolution_result'):
            data['resolution_result'] = SyncState.from_dict(data['resolution_result'])
        return cls(**data)


class DeviceManager:
    """设备管理器"""
    
    def __init__(self):
        self.devices: Dict[str, DeviceInfo] = {}  # device_id -> DeviceInfo
        self.user_devices: Dict[int, Set[str]] = {}  # user_id -> device_ids
        self.online_devices: Set[str] = set()
        self.device_connections: Dict[str, str] = {}  # device_id -> connection_id
    
    def register_device(
        self,
        device_id: str,
        user_id: int,
        device_type: DeviceType,
        device_name: str,
        platform: str,
        connection_id: str,
        **kwargs
    ) -> DeviceInfo:
        """
        注册设备
        
        Args:
            device_id: 设备ID
            user_id: 用户ID
            device_type: 设备类型
            device_name: 设备名称
            platform: 平台信息
            connection_id: 连接ID
            **kwargs: 其他设备信息
            
        Returns:
            DeviceInfo: 设备信息
        """
        device_info = DeviceInfo(
            device_id=device_id,
            user_id=user_id,
            device_type=device_type,
            device_name=device_name,
            platform=platform,
            last_seen=datetime.utcnow(),
            **kwargs
        )
        
        # 如果是用户的第一个设备，设为主设备
        if user_id not in self.user_devices or not self.user_devices[user_id]:
            device_info.is_primary = True
            device_info.priority = 10
        
        # 存储设备信息
        self.devices[device_id] = device_info
        
        # 更新用户设备映射
        if user_id not in self.user_devices:
            self.user_devices[user_id] = set()
        self.user_devices[user_id].add(device_id)
        
        # 标记为在线
        self.online_devices.add(device_id)
        self.device_connections[device_id] = connection_id
        
        logger.info(f"Registered device: {device_id} for user {user_id}")
        return device_info
    
    def unregister_device(self, device_id: str):
        """
        注销设备
        
        Args:
            device_id: 设备ID
        """
        if device_id not in self.devices:
            return
        
        device_info = self.devices[device_id]
        user_id = device_info.user_id
        
        # 从映射中移除
        del self.devices[device_id]
        self.online_devices.discard(device_id)
        self.device_connections.pop(device_id, None)
        
        if user_id in self.user_devices:
            self.user_devices[user_id].discard(device_id)
            if not self.user_devices[user_id]:
                del self.user_devices[user_id]
        
        logger.info(f"Unregistered device: {device_id}")
    
    def set_device_offline(self, device_id: str):
        """
        设置设备离线
        
        Args:
            device_id: 设备ID
        """
        if device_id in self.devices:
            self.devices[device_id].last_seen = datetime.utcnow()
        
        self.online_devices.discard(device_id)
        self.device_connections.pop(device_id, None)
    
    def get_user_devices(self, user_id: int, online_only: bool = False) -> List[DeviceInfo]:
        """
        获取用户设备列表
        
        Args:
            user_id: 用户ID
            online_only: 是否只返回在线设备
            
        Returns:
            List[DeviceInfo]: 设备列表
        """
        if user_id not in self.user_devices:
            return []
        
        devices = []
        for device_id in self.user_devices[user_id]:
            if device_id in self.devices:
                device = self.devices[device_id]
                if not online_only or device_id in self.online_devices:
                    devices.append(device)
        
        # 按优先级排序
        devices.sort(key=lambda d: (d.priority, d.is_primary), reverse=True)
        return devices
    
    def get_primary_device(self, user_id: int) -> Optional[DeviceInfo]:
        """
        获取用户主设备
        
        Args:
            user_id: 用户ID
            
        Returns:
            Optional[DeviceInfo]: 主设备信息
        """
        devices = self.get_user_devices(user_id, online_only=True)
        for device in devices:
            if device.is_primary:
                return device
        
        # 如果没有主设备，返回优先级最高的在线设备
        return devices[0] if devices else None
    
    def set_primary_device(self, user_id: int, device_id: str) -> bool:
        """
        设置主设备
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            
        Returns:
            bool: 是否设置成功
        """
        if device_id not in self.devices or self.devices[device_id].user_id != user_id:
            return False
        
        # 清除其他设备的主设备标记
        for dev_id in self.user_devices.get(user_id, set()):
            if dev_id in self.devices:
                self.devices[dev_id].is_primary = False
        
        # 设置新的主设备
        self.devices[device_id].is_primary = True
        self.devices[device_id].priority = max(self.devices[device_id].priority, 8)
        
        return True
    
    def is_device_online(self, device_id: str) -> bool:
        """
        检查设备是否在线
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 是否在线
        """
        return device_id in self.online_devices
    
    def get_connection_id(self, device_id: str) -> Optional[str]:
        """
        获取设备连接ID
        
        Args:
            device_id: 设备ID
            
        Returns:
            Optional[str]: 连接ID
        """
        return self.device_connections.get(device_id)


class StateManager:
    """状态管理器"""
    
    def __init__(self):
        self.states: Dict[str, SyncState] = {}  # state_id -> SyncState
        self.user_states: Dict[int, Dict[str, str]] = {}  # user_id -> {data_type: state_id}
        self.version_history: Dict[str, List[SyncState]] = {}  # state_id -> versions
        self.max_history_size = 50
    
    def create_state(
        self,
        user_id: int,
        data_type: str,
        data_content: Any,
        device_id: str
    ) -> SyncState:
        """
        创建同步状态
        
        Args:
            user_id: 用户ID
            data_type: 数据类型
            data_content: 数据内容
            device_id: 设备ID
            
        Returns:
            SyncState: 同步状态
        """
        state_id = f"{user_id}:{data_type}"
        checksum = self._calculate_checksum(data_content)
        
        # 获取当前版本号
        current_version = 1
        if state_id in self.states:
            current_version = self.states[state_id].version + 1
        
        # 创建新状态
        state = SyncState(
            state_id=state_id,
            user_id=user_id,
            data_type=data_type,
            data_content=data_content,
            version=current_version,
            timestamp=time.time(),
            device_id=device_id,
            checksum=checksum
        )
        
        # 保存历史版本
        if state_id in self.states:
            if state_id not in self.version_history:
                self.version_history[state_id] = []
            
            self.version_history[state_id].append(self.states[state_id])
            
            # 限制历史版本数量
            if len(self.version_history[state_id]) > self.max_history_size:
                self.version_history[state_id].pop(0)
        
        # 更新当前状态
        self.states[state_id] = state
        
        # 更新用户状态映射
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        self.user_states[user_id][data_type] = state_id
        
        return state
    
    def get_state(self, user_id: int, data_type: str) -> Optional[SyncState]:
        """
        获取同步状态
        
        Args:
            user_id: 用户ID
            data_type: 数据类型
            
        Returns:
            Optional[SyncState]: 同步状态
        """
        state_id = f"{user_id}:{data_type}"
        return self.states.get(state_id)
    
    def get_state_history(self, user_id: int, data_type: str) -> List[SyncState]:
        """
        获取状态历史
        
        Args:
            user_id: 用户ID
            data_type: 数据类型
            
        Returns:
            List[SyncState]: 状态历史
        """
        state_id = f"{user_id}:{data_type}"
        history = self.version_history.get(state_id, [])
        
        # 包含当前状态
        if state_id in self.states:
            history = history + [self.states[state_id]]
        
        return sorted(history, key=lambda s: s.version)
    
    def has_conflict(self, user_id: int, data_type: str, new_state: SyncState) -> bool:
        """
        检查是否存在冲突
        
        Args:
            user_id: 用户ID
            data_type: 数据类型
            new_state: 新状态
            
        Returns:
            bool: 是否存在冲突
        """
        current_state = self.get_state(user_id, data_type)
        
        if not current_state:
            return False
        
        # 检查版本冲突
        if (new_state.version <= current_state.version and 
            new_state.checksum != current_state.checksum):
            return True
        
        # 检查时间戳冲突 (同时修改)
        time_diff = abs(new_state.timestamp - current_state.timestamp)
        if time_diff < 1.0 and new_state.device_id != current_state.device_id:
            return True
        
        return False
    
    def _calculate_checksum(self, content: Any) -> str:
        """计算校验和"""
        import hashlib
        
        if isinstance(content, dict):
            content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        elif isinstance(content, (list, tuple)):
            content_str = json.dumps(list(content), ensure_ascii=False)
        else:
            content_str = str(content)
        
        return hashlib.md5(content_str.encode('utf-8')).hexdigest()


class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self.conflicts: Dict[str, SyncConflict] = {}  # conflict_id -> SyncConflict
        self.resolution_callbacks: Dict[str, Callable] = {}
    
    def create_conflict(
        self,
        user_id: int,
        data_type: str,
        state_id: str,
        conflicting_states: List[SyncState],
        resolution_strategy: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    ) -> SyncConflict:
        """
        创建冲突
        
        Args:
            user_id: 用户ID
            data_type: 数据类型
            state_id: 状态ID
            conflicting_states: 冲突状态列表
            resolution_strategy: 解决策略
            
        Returns:
            SyncConflict: 同步冲突
        """
        conflict_id = f"conflict_{user_id}_{data_type}_{int(time.time())}"
        
        conflict = SyncConflict(
            conflict_id=conflict_id,
            user_id=user_id,
            data_type=data_type,
            state_id=state_id,
            conflicting_states=conflicting_states,
            resolution_strategy=resolution_strategy
        )
        
        self.conflicts[conflict_id] = conflict
        
        logger.warning(f"Created conflict: {conflict_id} for user {user_id}")
        return conflict
    
    async def resolve_conflict(self, conflict_id: str) -> Optional[SyncState]:
        """
        解决冲突
        
        Args:
            conflict_id: 冲突ID
            
        Returns:
            Optional[SyncState]: 解决结果状态
        """
        if conflict_id not in self.conflicts:
            return None
        
        conflict = self.conflicts[conflict_id]
        
        if conflict.resolved:
            return conflict.resolution_result
        
        # 根据策略解决冲突
        if conflict.resolution_strategy == ConflictResolution.LAST_WRITE_WINS:
            result = self._resolve_last_write_wins(conflict)
        elif conflict.resolution_strategy == ConflictResolution.FIRST_WRITE_WINS:
            result = self._resolve_first_write_wins(conflict)
        elif conflict.resolution_strategy == ConflictResolution.DEVICE_PRIORITY:
            result = self._resolve_device_priority(conflict)
        elif conflict.resolution_strategy == ConflictResolution.MANUAL_RESOLVE:
            result = await self._resolve_manual(conflict)
        elif conflict.resolution_strategy == ConflictResolution.USER_CHOICE:
            result = await self._resolve_user_choice(conflict)
        else:
            result = self._resolve_last_write_wins(conflict)  # 默认策略
        
        # 标记为已解决
        conflict.resolved = True
        conflict.resolution_result = result
        
        # 调用解决回调
        if conflict_id in self.resolution_callbacks:
            try:
                callback = self.resolution_callbacks[conflict_id]
                if asyncio.iscoroutinefunction(callback):
                    await callback(conflict, result)
                else:
                    callback(conflict, result)
            except Exception as e:
                logger.error(f"Error in conflict resolution callback: {e}")
        
        logger.info(f"Resolved conflict: {conflict_id}")
        return result
    
    def _resolve_last_write_wins(self, conflict: SyncConflict) -> SyncState:
        """最后写入获胜策略"""
        return max(conflict.conflicting_states, key=lambda s: s.timestamp)
    
    def _resolve_first_write_wins(self, conflict: SyncConflict) -> SyncState:
        """首次写入获胜策略"""
        return min(conflict.conflicting_states, key=lambda s: s.timestamp)
    
    def _resolve_device_priority(self, conflict: SyncConflict) -> SyncState:
        """设备优先级策略"""
        # 按设备优先级排序
        states_with_priority = []
        
        for state in conflict.conflicting_states:
            device_id = state.device_id
            device_info = self.device_manager.devices.get(device_id)
            priority = device_info.priority if device_info else 0
            is_primary = device_info.is_primary if device_info else False
            
            states_with_priority.append((state, priority, is_primary))
        
        # 按优先级和主设备标记排序
        states_with_priority.sort(key=lambda x: (x[2], x[1]), reverse=True)
        
        return states_with_priority[0][0]
    
    async def _resolve_manual(self, conflict: SyncConflict) -> SyncState:
        """手动解决策略"""
        # 这里应该通知用户进行手动解决
        # 目前返回最后写入的状态作为临时解决方案
        logger.info(f"Manual resolution required for conflict: {conflict.conflict_id}")
        return self._resolve_last_write_wins(conflict)
    
    async def _resolve_user_choice(self, conflict: SyncConflict) -> SyncState:
        """用户选择策略"""
        # 这里应该向用户展示选择界面
        # 目前返回设备优先级策略的结果
        logger.info(f"User choice required for conflict: {conflict.conflict_id}")
        return self._resolve_device_priority(conflict)
    
    def register_resolution_callback(
        self,
        conflict_id: str,
        callback: Callable[[SyncConflict, SyncState], None]
    ):
        """
        注册解决回调
        
        Args:
            conflict_id: 冲突ID
            callback: 回调函数
        """
        self.resolution_callbacks[conflict_id] = callback
    
    def get_pending_conflicts(self, user_id: int) -> List[SyncConflict]:
        """
        获取待解决冲突
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[SyncConflict]: 冲突列表
        """
        return [
            conflict for conflict in self.conflicts.values()
            if conflict.user_id == user_id and not conflict.resolved
        ]


class DashboardMultiDeviceService:
    """仪表板多设备同步服务"""
    
    def __init__(self):
        # 核心组件
        self.device_manager = DeviceManager()
        self.state_manager = StateManager()
        self.conflict_resolver = ConflictResolver(self.device_manager)
        
        # 同步回调
        self.sync_callbacks: Dict[str, List[Callable]] = {}  # data_type -> callbacks
        
        # 后台任务
        self.background_tasks: Set[asyncio.Task] = set()
        
        # 统计信息
        self.stats = {
            'total_devices': 0,
            'online_devices': 0,
            'sync_operations': 0,
            'conflicts_created': 0,
            'conflicts_resolved': 0,
            'sync_errors': 0
        }
        
        # Redis客户端
        self.redis_client = get_redis_client()
        
        # 启动后台任务
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 设备状态监控任务
        monitor_task = asyncio.create_task(self._device_monitor())
        self.background_tasks.add(monitor_task)
        monitor_task.add_done_callback(self.background_tasks.discard)
        
        # 冲突自动解决任务
        conflict_task = asyncio.create_task(self._conflict_resolver_task())
        self.background_tasks.add(conflict_task)
        conflict_task.add_done_callback(self.background_tasks.discard)
        
        # 状态同步任务
        sync_task = asyncio.create_task(self._state_sync_task())
        self.background_tasks.add(sync_task)
        sync_task.add_done_callback(self.background_tasks.discard)
    
    async def register_device(
        self,
        user_id: int,
        connection_id: str,
        device_info: Dict[str, Any]
    ) -> str:
        """
        注册设备
        
        Args:
            user_id: 用户ID
            connection_id: 连接ID
            device_info: 设备信息
            
        Returns:
            str: 设备ID
        """
        # 生成设备ID
        device_id = device_info.get('device_id')
        if not device_id:
            device_id = f"device_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # 解析设备类型
        device_type_str = device_info.get('device_type', 'WEB')
        try:
            device_type = DeviceType(device_type_str)
        except ValueError:
            device_type = DeviceType.WEB
        
        # 注册设备
        device = self.device_manager.register_device(
            device_id=device_id,
            user_id=user_id,
            device_type=device_type,
            device_name=device_info.get('device_name', f'{device_type.value} Device'),
            platform=device_info.get('platform', 'Unknown'),
            connection_id=connection_id,
            browser=device_info.get('browser'),
            version=device_info.get('version'),
            screen_resolution=device_info.get('screen_resolution'),
            timezone=device_info.get('timezone')
        )
        
        # 更新统计
        self.stats['total_devices'] = len(self.device_manager.devices)
        self.stats['online_devices'] = len(self.device_manager.online_devices)
        
        # 同步设备状态
        await self._sync_device_state(device_id)
        
        logger.info(f"Registered device {device_id} for user {user_id}")
        return device_id
    
    async def unregister_device(self, device_id: str):
        """
        注销设备
        
        Args:
            device_id: 设备ID
        """
        self.device_manager.unregister_device(device_id)
        
        # 更新统计
        self.stats['total_devices'] = len(self.device_manager.devices)
        self.stats['online_devices'] = len(self.device_manager.online_devices)
        
        logger.info(f"Unregistered device: {device_id}")
    
    async def sync_state(
        self,
        user_id: int,
        device_id: str,
        data_type: str,
        data_content: Any,
        force_sync: bool = False
    ) -> bool:
        """
        同步状态
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            data_type: 数据类型
            data_content: 数据内容
            force_sync: 是否强制同步
            
        Returns:
            bool: 是否同步成功
        """
        try:
            # 创建新状态
            new_state = SyncState(
                state_id=f"{user_id}:{data_type}",
                user_id=user_id,
                data_type=data_type,
                data_content=data_content,
                version=1,  # 临时版本号
                timestamp=time.time(),
                device_id=device_id,
                checksum=self.state_manager._calculate_checksum(data_content)
            )
            
            # 检查冲突
            if not force_sync and self.state_manager.has_conflict(user_id, data_type, new_state):
                # 创建冲突
                current_state = self.state_manager.get_state(user_id, data_type)
                conflict = self.conflict_resolver.create_conflict(
                    user_id=user_id,
                    data_type=data_type,
                    state_id=new_state.state_id,
                    conflicting_states=[current_state, new_state]
                )
                
                self.stats['conflicts_created'] += 1
                
                # 尝试自动解决冲突
                resolved_state = await self.conflict_resolver.resolve_conflict(conflict.conflict_id)
                if resolved_state:
                    new_state = resolved_state
                    self.stats['conflicts_resolved'] += 1
                else:
                    logger.warning(f"Failed to resolve conflict for {data_type}")
                    return False
            
            # 更新状态
            final_state = self.state_manager.create_state(
                user_id=user_id,
                data_type=data_type,
                data_content=new_state.data_content,
                device_id=device_id
            )
            
            # 同步到其他设备
            await self._broadcast_state_change(final_state, exclude_device=device_id)
            
            # 缓存到Redis
            await self._cache_state(final_state)
            
            # 调用同步回调
            await self._call_sync_callbacks(data_type, final_state)
            
            self.stats['sync_operations'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Error syncing state: {e}")
            self.stats['sync_errors'] += 1
            return False
    
    async def get_state(self, user_id: int, data_type: str) -> Optional[Dict[str, Any]]:
        """
        获取状态
        
        Args:
            user_id: 用户ID
            data_type: 数据类型
            
        Returns:
            Optional[Dict[str, Any]]: 状态数据
        """
        state = self.state_manager.get_state(user_id, data_type)
        if state:
            return state.to_dict()
        
        # 尝试从Redis获取
        cached_state = await self._get_cached_state(user_id, data_type)
        if cached_state:
            return cached_state
        
        return None
    
    async def get_device_list(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取设备列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 设备列表
        """
        devices = self.device_manager.get_user_devices(user_id)
        return [device.to_dict() for device in devices]
    
    async def set_primary_device(self, user_id: int, device_id: str) -> bool:
        """
        设置主设备
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            
        Returns:
            bool: 是否设置成功
        """
        success = self.device_manager.set_primary_device(user_id, device_id)
        
        if success:
            # 通知所有设备主设备变更
            await self._broadcast_primary_device_change(user_id, device_id)
        
        return success
    
    async def get_conflicts(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取冲突列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict[str, Any]]: 冲突列表
        """
        conflicts = self.conflict_resolver.get_pending_conflicts(user_id)
        return [conflict.to_dict() for conflict in conflicts]
    
    async def resolve_conflict_manually(
        self,
        conflict_id: str,
        chosen_state_index: int
    ) -> bool:
        """
        手动解决冲突
        
        Args:
            conflict_id: 冲突ID
            chosen_state_index: 选择的状态索引
            
        Returns:
            bool: 是否解决成功
        """
        if conflict_id not in self.conflict_resolver.conflicts:
            return False
        
        conflict = self.conflict_resolver.conflicts[conflict_id]
        
        if (chosen_state_index < 0 or 
            chosen_state_index >= len(conflict.conflicting_states)):
            return False
        
        # 选择指定的状态作为解决结果
        chosen_state = conflict.conflicting_states[chosen_state_index]
        
        # 更新状态管理器
        final_state = self.state_manager.create_state(
            user_id=conflict.user_id,
            data_type=conflict.data_type,
            data_content=chosen_state.data_content,
            device_id=chosen_state.device_id
        )
        
        # 标记冲突为已解决
        conflict.resolved = True
        conflict.resolution_result = final_state
        
        # 同步到所有设备
        await self._broadcast_state_change(final_state)
        
        self.stats['conflicts_resolved'] += 1
        return True
    
    def register_sync_callback(
        self,
        data_type: str,
        callback: Callable[[SyncState], None]
    ):
        """
        注册同步回调
        
        Args:
            data_type: 数据类型
            callback: 回调函数
        """
        if data_type not in self.sync_callbacks:
            self.sync_callbacks[data_type] = []
        
        self.sync_callbacks[data_type].append(callback)
    
    async def _sync_device_state(self, device_id: str):
        """
        同步设备状态
        
        Args:
            device_id: 设备ID
        """
        if device_id not in self.device_manager.devices:
            return
        
        device_info = self.device_manager.devices[device_id]
        user_id = device_info.user_id
        
        # 获取用户的所有状态
        if user_id in self.state_manager.user_states:
            for data_type, state_id in self.state_manager.user_states[user_id].items():
                if state_id in self.state_manager.states:
                    state = self.state_manager.states[state_id]
                    await self._send_state_to_device(device_id, state)
    
    async def _broadcast_state_change(
        self,
        state: SyncState,
        exclude_device: Optional[str] = None
    ):
        """
        广播状态变更
        
        Args:
            state: 同步状态
            exclude_device: 排除的设备ID
        """
        user_devices = self.device_manager.get_user_devices(state.user_id, online_only=True)
        
        for device in user_devices:
            if device.device_id != exclude_device:
                await self._send_state_to_device(device.device_id, state)
    
    async def _broadcast_primary_device_change(self, user_id: int, new_primary_device_id: str):
        """
        广播主设备变更
        
        Args:
            user_id: 用户ID
            new_primary_device_id: 新主设备ID
        """
        user_devices = self.device_manager.get_user_devices(user_id, online_only=True)
        
        for device in user_devices:
            await self._send_primary_device_notification(device.device_id, new_primary_device_id)
    
    async def _send_state_to_device(self, device_id: str, state: SyncState):
        """
        发送状态到设备
        
        Args:
            device_id: 设备ID
            state: 同步状态
        """
        # 这里应该调用实际的WebSocket发送逻辑
        # 目前只是记录日志
        logger.debug(f"Sending state {state.data_type} to device {device_id}")
    
    async def _send_primary_device_notification(
        self,
        device_id: str,
        new_primary_device_id: str
    ):
        """
        发送主设备变更通知
        
        Args:
            device_id: 设备ID
            new_primary_device_id: 新主设备ID
        """
        logger.debug(f"Notifying device {device_id} of primary device change to {new_primary_device_id}")
    
    async def _cache_state(self, state: SyncState):
        """
        缓存状态到Redis
        
        Args:
            state: 同步状态
        """
        try:
            if self.redis_client:
                key = f"dashboard:multidevice:state:{state.state_id}"
                await self.redis_client.setex(
                    key,
                    3600,  # 1小时过期
                    json.dumps(state.to_dict(), ensure_ascii=False)
                )
        except Exception as e:
            logger.error(f"Error caching state: {e}")
    
    async def _get_cached_state(self, user_id: int, data_type: str) -> Optional[Dict[str, Any]]:
        """
        从Redis获取缓存状态
        
        Args:
            user_id: 用户ID
            data_type: 数据类型
            
        Returns:
            Optional[Dict[str, Any]]: 缓存状态
        """
        try:
            if self.redis_client:
                state_id = f"{user_id}:{data_type}"
                key = f"dashboard:multidevice:state:{state_id}"
                
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error getting cached state: {e}")
        
        return None
    
    async def _call_sync_callbacks(self, data_type: str, state: SyncState):
        """
        调用同步回调
        
        Args:
            data_type: 数据类型
            state: 同步状态
        """
        if data_type in self.sync_callbacks:
            for callback in self.sync_callbacks[data_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(state)
                    else:
                        callback(state)
                except Exception as e:
                    logger.error(f"Error in sync callback: {e}")
    
    async def _device_monitor(self):
        """设备状态监控任务"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                current_time = datetime.utcnow()
                offline_threshold = current_time - timedelta(minutes=5)
                
                # 检查离线设备
                offline_devices = []
                for device_id, device_info in self.device_manager.devices.items():
                    if (device_info.last_seen and 
                        device_info.last_seen < offline_threshold and
                        device_id in self.device_manager.online_devices):
                        offline_devices.append(device_id)
                
                # 设置设备为离线
                for device_id in offline_devices:
                    self.device_manager.set_device_offline(device_id)
                
                # 更新统计
                self.stats['online_devices'] = len(self.device_manager.online_devices)
                
            except Exception as e:
                logger.error(f"Error in device monitor: {e}")
    
    async def _conflict_resolver_task(self):
        """冲突自动解决任务"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                # 获取所有未解决的冲突
                pending_conflicts = [
                    conflict for conflict in self.conflict_resolver.conflicts.values()
                    if not conflict.resolved
                ]
                
                # 尝试自动解决冲突
                for conflict in pending_conflicts:
                    if conflict.resolution_strategy != ConflictResolution.MANUAL_RESOLVE:
                        await self.conflict_resolver.resolve_conflict(conflict.conflict_id)
                
            except Exception as e:
                logger.error(f"Error in conflict resolver task: {e}")
    
    async def _state_sync_task(self):
        """状态同步任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟同步一次
                
                # 同步所有在线设备的状态到Redis
                for device_id in self.device_manager.online_devices:
                    if device_id in self.device_manager.devices:
                        device_info = self.device_manager.devices[device_id]
                        user_id = device_info.user_id
                        
                        # 缓存设备信息
                        key = f"dashboard:multidevice:device:{device_id}"
                        await self.redis_client.setex(
                            key,
                            600,  # 10分钟过期
                            json.dumps(device_info.to_dict(), ensure_ascii=False)
                        )
                
            except Exception as e:
                logger.error(f"Error in state sync task: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'device_types': {
                device_type.value: sum(
                    1 for device in self.device_manager.devices.values()
                    if device.device_type == device_type
                )
                for device_type in DeviceType
            },
            'pending_conflicts': len([
                c for c in self.conflict_resolver.conflicts.values()
                if not c.resolved
            ]),
            'background_tasks': len(self.background_tasks)
        }
    
    async def shutdown(self):
        """关闭服务"""
        try:
            # 取消所有后台任务
            for task in self.background_tasks:
                task.cancel()
            
            # 等待任务完成
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # 清理数据
            self.device_manager.devices.clear()
            self.device_manager.user_devices.clear()
            self.device_manager.online_devices.clear()
            self.state_manager.states.clear()
            self.conflict_resolver.conflicts.clear()
            
            logger.info("Dashboard multi-device service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during multi-device service shutdown: {e}")


# 全局实例
dashboard_multidevice_service: Optional[DashboardMultiDeviceService] = None


def get_dashboard_multidevice_service() -> DashboardMultiDeviceService:
    """获取仪表板多设备同步服务实例"""
    global dashboard_multidevice_service
    
    if dashboard_multidevice_service is None:
        dashboard_multidevice_service = DashboardMultiDeviceService()
    
    return dashboard_multidevice_service