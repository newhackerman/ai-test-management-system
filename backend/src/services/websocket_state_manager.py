"""
WebSocket连接状态管理器

提供WebSocket连接的状态管理功能，包括：
1. 连接状态跟踪和监控
2. 自动重连机制
3. 连接健康检查
4. 状态持久化和恢复
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

import redis.asyncio as redis
from fastapi import WebSocket

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ConnectionState(Enum):
    """连接状态枚举"""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    SUSPENDED = "suspended"


class ReconnectStrategy(Enum):
    """重连策略枚举"""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    NO_RECONNECT = "no_reconnect"


@dataclass
class ConnectionStateInfo:
    """连接状态信息"""
    connection_id: str
    user_id: int
    state: ConnectionState
    created_at: datetime
    last_state_change: datetime
    reconnect_attempts: int = 0
    max_reconnect_attempts: int = 5
    reconnect_strategy: ReconnectStrategy = ReconnectStrategy.EXPONENTIAL_BACKOFF
    last_heartbeat: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "last_state_change": self.last_state_change.isoformat(),
            "reconnect_attempts": self.reconnect_attempts,
            "max_reconnect_attempts": self.max_reconnect_attempts,
            "reconnect_strategy": self.reconnect_strategy.value,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectionStateInfo':
        """从字典创建实例"""
        return cls(
            connection_id=data["connection_id"],
            user_id=data["user_id"],
            state=ConnectionState(data["state"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_state_change=datetime.fromisoformat(data["last_state_change"]),
            reconnect_attempts=data.get("reconnect_attempts", 0),
            max_reconnect_attempts=data.get("max_reconnect_attempts", 5),
            reconnect_strategy=ReconnectStrategy(data.get("reconnect_strategy", "exponential_backoff")),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]) if data.get("last_heartbeat") else None,
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {})
        )


@dataclass
class ReconnectConfig:
    """重连配置"""
    strategy: ReconnectStrategy = ReconnectStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 5
    initial_delay: float = 1.0  # 初始延迟（秒）
    max_delay: float = 60.0  # 最大延迟（秒）
    backoff_multiplier: float = 2.0  # 退避倍数
    jitter: bool = True  # 是否添加随机抖动


class WebSocketStateManager:
    """WebSocket连接状态管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 连接状态存储
        self.connection_states: Dict[str, ConnectionStateInfo] = {}
        
        # 用户连接映射
        self.user_connections: Dict[int, Set[str]] = {}
        
        # 重连任务管理
        self.reconnect_tasks: Dict[str, asyncio.Task] = {}
        
        # Redis客户端用于状态持久化
        self.redis_client: Optional[redis.Redis] = None
        
        # 状态变更回调
        self.state_change_callbacks: List[Callable] = []
        
        # 配置参数
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.state_persistence_enabled = True  # 是否启用状态持久化
        self.cleanup_interval = 300  # 清理间隔（秒）
        self.max_inactive_time = 3600  # 最大非活跃时间（秒）
        
        # 默认重连配置
        self.default_reconnect_config = ReconnectConfig()
        
        # 统计信息
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "reconnect_attempts": 0,
            "successful_reconnects": 0,
            "failed_reconnects": 0,
            "state_changes": 0
        }
    
    async def initialize(self):
        """初始化状态管理器"""
        try:
            # 初始化Redis连接
            if self.state_persistence_enabled:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                
                # 恢复持久化的状态
                await self._restore_persisted_states()
            
            # 启动后台任务
            asyncio.create_task(self._state_monitor_task())
            asyncio.create_task(self._cleanup_task())
            
            self.logger.info("WebSocket State Manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebSocket State Manager: {e}")
            raise
    
    async def register_connection(self, connection_id: str, user_id: int, 
                                metadata: Optional[Dict[str, Any]] = None,
                                reconnect_config: Optional[ReconnectConfig] = None) -> ConnectionStateInfo:
        """
        注册新连接
        
        Args:
            connection_id: 连接ID
            user_id: 用户ID
            metadata: 连接元数据
            reconnect_config: 重连配置
            
        Returns:
            ConnectionStateInfo: 连接状态信息
        """
        try:
            now = datetime.now(timezone.utc)
            
            # 创建连接状态信息
            state_info = ConnectionStateInfo(
                connection_id=connection_id,
                user_id=user_id,
                state=ConnectionState.INITIALIZING,
                created_at=now,
                last_state_change=now,
                metadata=metadata or {}
            )
            
            # 设置重连配置
            if reconnect_config:
                state_info.reconnect_strategy = reconnect_config.strategy
                state_info.max_reconnect_attempts = reconnect_config.max_attempts
            
            # 存储状态信息
            self.connection_states[connection_id] = state_info
            
            # 更新用户连接映射
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
            # 持久化状态
            await self._persist_state(state_info)
            
            # 更新统计
            self.stats["total_connections"] += 1
            
            self.logger.info(f"Registered connection {connection_id} for user {user_id}")
            return state_info
            
        except Exception as e:
            self.logger.error(f"Error registering connection {connection_id}: {e}")
            raise
    
    async def update_connection_state(self, connection_id: str, new_state: ConnectionState,
                                    error_message: Optional[str] = None,
                                    metadata_update: Optional[Dict[str, Any]] = None):
        """
        更新连接状态
        
        Args:
            connection_id: 连接ID
            new_state: 新状态
            error_message: 错误消息（如果有）
            metadata_update: 元数据更新
        """
        try:
            if connection_id not in self.connection_states:
                self.logger.warning(f"Connection {connection_id} not found for state update")
                return
            
            state_info = self.connection_states[connection_id]
            old_state = state_info.state
            
            # 更新状态
            state_info.state = new_state
            state_info.last_state_change = datetime.now(timezone.utc)
            
            if error_message:
                state_info.error_message = error_message
            
            if metadata_update:
                state_info.metadata.update(metadata_update)
            
            # 更新统计
            self.stats["state_changes"] += 1
            
            if new_state == ConnectionState.CONNECTED:
                self.stats["active_connections"] += 1
                if old_state == ConnectionState.RECONNECTING:
                    self.stats["successful_reconnects"] += 1
            elif old_state == ConnectionState.CONNECTED:
                self.stats["active_connections"] -= 1
            
            # 持久化状态
            await self._persist_state(state_info)
            
            # 触发状态变更回调
            await self._trigger_state_change_callbacks(connection_id, old_state, new_state)
            
            # 处理特殊状态
            if new_state == ConnectionState.ERROR:
                await self._handle_connection_error(connection_id)
            elif new_state == ConnectionState.DISCONNECTED:
                await self._handle_disconnection(connection_id)
            
            self.logger.info(f"Connection {connection_id} state changed: {old_state.value} -> {new_state.value}")
            
        except Exception as e:
            self.logger.error(f"Error updating connection state for {connection_id}: {e}")
    
    async def update_heartbeat(self, connection_id: str):
        """
        更新连接心跳时间
        
        Args:
            connection_id: 连接ID
        """
        if connection_id in self.connection_states:
            self.connection_states[connection_id].last_heartbeat = datetime.now(timezone.utc)
            await self._persist_state(self.connection_states[connection_id])
    
    async def unregister_connection(self, connection_id: str):
        """
        注销连接
        
        Args:
            connection_id: 连接ID
        """
        try:
            if connection_id not in self.connection_states:
                return
            
            state_info = self.connection_states[connection_id]
            user_id = state_info.user_id
            
            # 取消重连任务
            if connection_id in self.reconnect_tasks:
                self.reconnect_tasks[connection_id].cancel()
                del self.reconnect_tasks[connection_id]
            
            # 从用户连接映射中移除
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # 移除状态信息
            del self.connection_states[connection_id]
            
            # 清理持久化状态
            await self._remove_persisted_state(connection_id)
            
            # 更新统计
            if state_info.state == ConnectionState.CONNECTED:
                self.stats["active_connections"] -= 1
            
            self.logger.info(f"Unregistered connection {connection_id}")
            
        except Exception as e:
            self.logger.error(f"Error unregistering connection {connection_id}: {e}")
    
    async def start_reconnect(self, connection_id: str):
        """
        启动重连流程
        
        Args:
            connection_id: 连接ID
        """
        try:
            if connection_id not in self.connection_states:
                return
            
            state_info = self.connection_states[connection_id]
            
            # 检查是否已达到最大重连次数
            if state_info.reconnect_attempts >= state_info.max_reconnect_attempts:
                self.logger.warning(f"Connection {connection_id} reached max reconnect attempts")
                await self.update_connection_state(connection_id, ConnectionState.ERROR, 
                                                 "Max reconnect attempts reached")
                return
            
            # 更新状态为重连中
            await self.update_connection_state(connection_id, ConnectionState.RECONNECTING)
            
            # 启动重连任务
            if connection_id not in self.reconnect_tasks:
                self.reconnect_tasks[connection_id] = asyncio.create_task(
                    self._reconnect_task(connection_id)
                )
            
        except Exception as e:
            self.logger.error(f"Error starting reconnect for {connection_id}: {e}")
    
    async def _reconnect_task(self, connection_id: str):
        """重连任务"""
        try:
            state_info = self.connection_states.get(connection_id)
            if not state_info:
                return
            
            # 计算重连延迟
            delay = self._calculate_reconnect_delay(state_info)
            
            self.logger.info(f"Reconnecting {connection_id} in {delay:.2f} seconds (attempt {state_info.reconnect_attempts + 1})")
            
            # 等待延迟
            await asyncio.sleep(delay)
            
            # 增加重连次数
            state_info.reconnect_attempts += 1
            self.stats["reconnect_attempts"] += 1
            
            # 这里应该触发实际的重连逻辑
            # 由于WebSocket重连需要客户端配合，这里只是更新状态
            # 实际的重连逻辑应该在WebSocket管理器中实现
            
            # 触发重连事件
            await self._trigger_reconnect_event(connection_id)
            
        except asyncio.CancelledError:
            self.logger.info(f"Reconnect task for {connection_id} was cancelled")
        except Exception as e:
            self.logger.error(f"Error in reconnect task for {connection_id}: {e}")
            await self.update_connection_state(connection_id, ConnectionState.ERROR, str(e))
        finally:
            # 清理重连任务
            self.reconnect_tasks.pop(connection_id, None)
    
    def _calculate_reconnect_delay(self, state_info: ConnectionStateInfo) -> float:
        """计算重连延迟"""
        config = self.default_reconnect_config
        
        if state_info.reconnect_strategy == ReconnectStrategy.IMMEDIATE:
            return 0.0
        elif state_info.reconnect_strategy == ReconnectStrategy.FIXED_INTERVAL:
            delay = config.initial_delay
        elif state_info.reconnect_strategy == ReconnectStrategy.LINEAR_BACKOFF:
            delay = config.initial_delay * (state_info.reconnect_attempts + 1)
        elif state_info.reconnect_strategy == ReconnectStrategy.EXPONENTIAL_BACKOFF:
            delay = config.initial_delay * (config.backoff_multiplier ** state_info.reconnect_attempts)
        else:
            delay = config.initial_delay
        
        # 限制最大延迟
        delay = min(delay, config.max_delay)
        
        # 添加随机抖动
        if config.jitter:
            import random
            jitter_range = delay * 0.1  # 10%的抖动
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.0, delay)
    
    async def _handle_connection_error(self, connection_id: str):
        """处理连接错误"""
        state_info = self.connection_states.get(connection_id)
        if not state_info:
            return
        
        # 根据重连策略决定是否启动重连
        if state_info.reconnect_strategy != ReconnectStrategy.NO_RECONNECT:
            await self.start_reconnect(connection_id)
        else:
            self.stats["failed_reconnects"] += 1
    
    async def _handle_disconnection(self, connection_id: str):
        """处理连接断开"""
        state_info = self.connection_states.get(connection_id)
        if not state_info:
            return
        
        # 如果是意外断开，启动重连
        if state_info.reconnect_strategy != ReconnectStrategy.NO_RECONNECT:
            await self.start_reconnect(connection_id)
    
    async def _trigger_reconnect_event(self, connection_id: str):
        """触发重连事件"""
        # 这里可以通知WebSocket管理器进行实际的重连操作
        # 或者发送重连指令给客户端
        pass
    
    async def _persist_state(self, state_info: ConnectionStateInfo):
        """持久化连接状态"""
        if not self.redis_client or not self.state_persistence_enabled:
            return
        
        try:
            key = f"ws_state:{state_info.connection_id}"
            value = json.dumps(state_info.to_dict())
            
            # 设置过期时间（24小时）
            await self.redis_client.setex(key, 86400, value)
            
        except Exception as e:
            self.logger.warning(f"Failed to persist state for {state_info.connection_id}: {e}")
    
    async def _remove_persisted_state(self, connection_id: str):
        """移除持久化状态"""
        if not self.redis_client:
            return
        
        try:
            key = f"ws_state:{connection_id}"
            await self.redis_client.delete(key)
            
        except Exception as e:
            self.logger.warning(f"Failed to remove persisted state for {connection_id}: {e}")
    
    async def _restore_persisted_states(self):
        """恢复持久化的状态"""
        if not self.redis_client:
            return
        
        try:
            # 获取所有持久化的状态
            keys = await self.redis_client.keys("ws_state:*")
            
            for key in keys:
                try:
                    value = await self.redis_client.get(key)
                    if value:
                        state_data = json.loads(value)
                        state_info = ConnectionStateInfo.from_dict(state_data)
                        
                        # 恢复状态（但标记为断开）
                        state_info.state = ConnectionState.DISCONNECTED
                        
                        self.connection_states[state_info.connection_id] = state_info
                        
                        # 更新用户连接映射
                        if state_info.user_id not in self.user_connections:
                            self.user_connections[state_info.user_id] = set()
                        self.user_connections[state_info.user_id].add(state_info.connection_id)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to restore state from {key}: {e}")
            
            self.logger.info(f"Restored {len(keys)} persisted connection states")
            
        except Exception as e:
            self.logger.error(f"Error restoring persisted states: {e}")
    
    async def _state_monitor_task(self):
        """状态监控后台任务"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = datetime.now(timezone.utc)
                stale_connections = []
                
                # 检查心跳超时的连接
                for connection_id, state_info in self.connection_states.items():
                    if (state_info.last_heartbeat and 
                        (current_time - state_info.last_heartbeat).total_seconds() > self.heartbeat_interval * 2):
                        
                        if state_info.state == ConnectionState.CONNECTED:
                            stale_connections.append(connection_id)
                
                # 处理超时连接
                for connection_id in stale_connections:
                    self.logger.warning(f"Connection {connection_id} heartbeat timeout")
                    await self.update_connection_state(connection_id, ConnectionState.ERROR, 
                                                     "Heartbeat timeout")
                
            except Exception as e:
                self.logger.error(f"Error in state monitor task: {e}")
    
    async def _cleanup_task(self):
        """清理后台任务"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = datetime.now(timezone.utc)
                expired_connections = []
                
                # 查找过期的连接
                for connection_id, state_info in self.connection_states.items():
                    time_since_change = (current_time - state_info.last_state_change).total_seconds()
                    
                    if (time_since_change > self.max_inactive_time and 
                        state_info.state in [ConnectionState.DISCONNECTED, ConnectionState.ERROR]):
                        expired_connections.append(connection_id)
                
                # 清理过期连接
                for connection_id in expired_connections:
                    self.logger.info(f"Cleaning up expired connection {connection_id}")
                    await self.unregister_connection(connection_id)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
    
    def add_state_change_callback(self, callback: Callable):
        """添加状态变更回调"""
        self.state_change_callbacks.append(callback)
    
    async def _trigger_state_change_callbacks(self, connection_id: str, 
                                            old_state: ConnectionState, 
                                            new_state: ConnectionState):
        """触发状态变更回调"""
        for callback in self.state_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(connection_id, old_state, new_state)
                else:
                    callback(connection_id, old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {e}")
    
    def get_connection_state(self, connection_id: str) -> Optional[ConnectionStateInfo]:
        """获取连接状态"""
        return self.connection_states.get(connection_id)
    
    def get_user_connections_states(self, user_id: int) -> List[ConnectionStateInfo]:
        """获取用户的所有连接状态"""
        if user_id not in self.user_connections:
            return []
        
        return [
            self.connection_states[conn_id] 
            for conn_id in self.user_connections[user_id]
            if conn_id in self.connection_states
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "total_registered_connections": len(self.connection_states),
            "users_with_connections": len(self.user_connections),
            "active_reconnect_tasks": len(self.reconnect_tasks)
        }
    
    async def close(self):
        """关闭状态管理器"""
        try:
            # 取消所有重连任务
            for task in self.reconnect_tasks.values():
                task.cancel()
            
            # 等待任务完成
            if self.reconnect_tasks:
                await asyncio.gather(*self.reconnect_tasks.values(), return_exceptions=True)
            
            # 关闭Redis连接
            if self.redis_client:
                await self.redis_client.close()
            
            self.logger.info("WebSocket State Manager closed")
            
        except Exception as e:
            self.logger.error(f"Error closing WebSocket State Manager: {e}")


# 全局状态管理器实例
websocket_state_manager = WebSocketStateManager()