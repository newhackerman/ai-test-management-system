"""
AI助手WebSocket连接管理服务

专门为AI助手模块提供WebSocket连接管理功能，包括：
1. AI对话的实时WebSocket连接管理
2. 流式AI响应的实时推送
3. 连接状态监控和自动重连
4. 多用户并发连接支持
5. 消息队列和缓存管理
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Set, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis

from ..core.config import get_settings
from ..models.ai_chat_session import AIChatSession
from ..models.ai_chat_message import AIChatMessage, MessageRole
from .websocket_state_manager import websocket_state_manager, ConnectionState, ReconnectConfig

logger = logging.getLogger(__name__)
settings = get_settings()


class ConnectionStatus(Enum):
    """连接状态枚举"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class MessageType(Enum):
    """WebSocket消息类型"""
    # 连接管理
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_ERROR = "connection_error"
    HEARTBEAT = "heartbeat"
    
    # AI对话
    AI_RESPONSE_START = "ai_response_start"
    AI_RESPONSE_CHUNK = "ai_response_chunk"
    AI_RESPONSE_COMPLETE = "ai_response_complete"
    AI_RESPONSE_ERROR = "ai_response_error"
    
    # 状态更新
    TYPING_INDICATOR = "typing_indicator"
    MESSAGE_STATUS = "message_status"
    CONVERSATION_STATUS = "conversation_status"
    
    # 用户操作
    USER_MESSAGE = "user_message"
    USER_TYPING = "user_typing"
    USER_STOP_TYPING = "user_stop_typing"
    
    # 系统通知
    SYSTEM_NOTIFICATION = "system_notification"
    ERROR = "error"


@dataclass
class WebSocketConnection:
    """WebSocket连接对象"""
    connection_id: str
    user_id: int
    websocket: WebSocket
    status: ConnectionStatus = ConnectionStatus.CONNECTING
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    subscribed_conversations: Set[int] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "connected_at": self.connected_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "subscribed_conversations": list(self.subscribed_conversations),
            "metadata": self.metadata
        }


@dataclass
class WebSocketMessage:
    """WebSocket消息对象"""
    type: MessageType
    data: Any
    conversation_id: Optional[int] = None
    message_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat()
        }, ensure_ascii=False)


class AIWebSocketManager:
    """AI助手WebSocket连接管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 连接管理
        # {user_id: {connection_id: WebSocketConnection}}
        self.user_connections: Dict[int, Dict[str, WebSocketConnection]] = {}
        
        # 对话订阅管理
        # {conversation_id: {user_ids}}
        self.conversation_subscribers: Dict[int, Set[int]] = {}
        
        # 消息队列 - 用于离线消息缓存
        # {user_id: [messages]}
        self.offline_message_queue: Dict[int, List[WebSocketMessage]] = {}
        
        # Redis客户端用于跨实例通信
        self.redis_client: Optional[redis.Redis] = None
        
        # 配置参数
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.connection_timeout = 300  # 连接超时（秒）
        self.max_offline_messages = 100  # 最大离线消息数
        self.max_connections_per_user = 5  # 每用户最大连接数
        
        # 统计信息
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages_sent": 0,
            "total_messages_received": 0,
            "connection_errors": 0
        }
        
        # 事件回调
        self.event_handlers: Dict[str, List[Callable]] = {}
        
    async def initialize(self):
        """初始化WebSocket管理器"""
        try:
            # 初始化Redis连接
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            
            # 初始化状态管理器
            await websocket_state_manager.initialize()
            
            # 启动后台任务
            asyncio.create_task(self._heartbeat_monitor())
            asyncio.create_task(self._cleanup_expired_connections())
            
            self.logger.info("AI WebSocket Manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI WebSocket Manager: {e}")
            raise
    
    async def connect_user(self, websocket: WebSocket, user_id: int, 
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        建立用户WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
            metadata: 连接元数据
            
        Returns:
            str: 连接ID
        """
        connection_id = str(uuid.uuid4())
        
        try:
            # 检查用户连接数限制
            if user_id in self.user_connections:
                if len(self.user_connections[user_id]) >= self.max_connections_per_user:
                    # 关闭最旧的连接
                    oldest_connection = min(
                        self.user_connections[user_id].values(),
                        key=lambda c: c.connected_at
                    )
                    await self._disconnect_connection(oldest_connection.connection_id)
            
            # 接受WebSocket连接
            await websocket.accept()
            
            # 注册到状态管理器
            await websocket_state_manager.register_connection(
                connection_id=connection_id,
                user_id=user_id,
                metadata=metadata,
                reconnect_config=ReconnectConfig(max_attempts=3)
            )
            
            # 创建连接对象
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=user_id,
                websocket=websocket,
                status=ConnectionStatus.CONNECTED,
                metadata=metadata or {}
            )
            
            # 存储连接
            if user_id not in self.user_connections:
                self.user_connections[user_id] = {}
            
            self.user_connections[user_id][connection_id] = connection
            
            # 更新状态管理器
            await websocket_state_manager.update_connection_state(connection_id, ConnectionState.CONNECTED)
            
            # 更新统计
            self.stats["total_connections"] += 1
            self.stats["active_connections"] += 1
            
            # 发送连接建立消息
            await self._send_to_connection(connection_id, WebSocketMessage(
                type=MessageType.CONNECTION_ESTABLISHED,
                data={
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "server_time": datetime.now(timezone.utc).isoformat(),
                    "heartbeat_interval": self.heartbeat_interval
                }
            ))
            
            # 发送离线消息
            await self._send_offline_messages(user_id, connection_id)
            
            # 触发连接事件
            await self._trigger_event("user_connected", {
                "user_id": user_id,
                "connection_id": connection_id,
                "metadata": metadata
            })
            
            self.logger.info(f"User {user_id} connected with connection {connection_id}")
            return connection_id
            
        except Exception as e:
            self.logger.error(f"Error connecting user {user_id}: {e}")
            self.stats["connection_errors"] += 1
            raise
    
    async def disconnect_user(self, connection_id: str):
        """
        断开用户WebSocket连接
        
        Args:
            connection_id: 连接ID
        """
        await self._disconnect_connection(connection_id)
    
    async def _disconnect_connection(self, connection_id: str):
        """内部断开连接方法"""
        connection = self._find_connection(connection_id)
        if not connection:
            return
        
        try:
            user_id = connection.user_id
            
            # 从订阅中移除
            for conversation_id in connection.subscribed_conversations.copy():
                await self._unsubscribe_from_conversation(user_id, conversation_id)
            
            # 关闭WebSocket连接
            try:
                await connection.websocket.close()
            except:
                pass
            
            # 移除连接记录
            if user_id in self.user_connections:
                self.user_connections[user_id].pop(connection_id, None)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            # 更新统计
            self.stats["active_connections"] -= 1
            
            # 更新状态管理器
            await websocket_state_manager.update_connection_state(connection_id, ConnectionState.DISCONNECTED)
            await websocket_state_manager.unregister_connection(connection_id)
            
            # 触发断开事件
            await self._trigger_event("user_disconnected", {
                "user_id": user_id,
                "connection_id": connection_id
            })
            
            self.logger.info(f"User {user_id} disconnected, connection {connection_id}")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting connection {connection_id}: {e}")
    
    async def subscribe_to_conversation(self, user_id: int, conversation_id: int):
        """
        订阅对话
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
        """
        try:
            # 添加到对话订阅者列表
            if conversation_id not in self.conversation_subscribers:
                self.conversation_subscribers[conversation_id] = set()
            
            self.conversation_subscribers[conversation_id].add(user_id)
            
            # 更新用户连接的订阅列表
            if user_id in self.user_connections:
                for connection in self.user_connections[user_id].values():
                    connection.subscribed_conversations.add(conversation_id)
            
            # 发送订阅确认
            await self.send_to_user(user_id, WebSocketMessage(
                type=MessageType.CONVERSATION_STATUS,
                conversation_id=conversation_id,
                data={
                    "action": "subscribed",
                    "conversation_id": conversation_id,
                    "message": f"已订阅对话 {conversation_id}"
                }
            ))
            
            self.logger.info(f"User {user_id} subscribed to conversation {conversation_id}")
            
        except Exception as e:
            self.logger.error(f"Error subscribing user {user_id} to conversation {conversation_id}: {e}")
    
    async def unsubscribe_from_conversation(self, user_id: int, conversation_id: int):
        """
        取消订阅对话
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
        """
        await self._unsubscribe_from_conversation(user_id, conversation_id)
    
    async def _unsubscribe_from_conversation(self, user_id: int, conversation_id: int):
        """内部取消订阅方法"""
        try:
            # 从对话订阅者列表移除
            if conversation_id in self.conversation_subscribers:
                self.conversation_subscribers[conversation_id].discard(user_id)
                if not self.conversation_subscribers[conversation_id]:
                    del self.conversation_subscribers[conversation_id]
            
            # 更新用户连接的订阅列表
            if user_id in self.user_connections:
                for connection in self.user_connections[user_id].values():
                    connection.subscribed_conversations.discard(conversation_id)
            
            self.logger.info(f"User {user_id} unsubscribed from conversation {conversation_id}")
            
        except Exception as e:
            self.logger.error(f"Error unsubscribing user {user_id} from conversation {conversation_id}: {e}")
    
    async def send_to_user(self, user_id: int, message: WebSocketMessage):
        """
        向指定用户发送消息
        
        Args:
            user_id: 用户ID
            message: WebSocket消息
        """
        try:
            if user_id in self.user_connections:
                # 向用户的所有连接发送消息
                disconnected_connections = []
                
                for connection_id, connection in self.user_connections[user_id].items():
                    try:
                        await self._send_to_connection(connection_id, message)
                    except Exception as e:
                        self.logger.warning(f"Failed to send message to connection {connection_id}: {e}")
                        disconnected_connections.append(connection_id)
                
                # 清理断开的连接
                for connection_id in disconnected_connections:
                    await self._disconnect_connection(connection_id)
            else:
                # 用户不在线，缓存消息
                await self._cache_offline_message(user_id, message)
            
        except Exception as e:
            self.logger.error(f"Error sending message to user {user_id}: {e}")
    
    async def send_to_conversation(self, conversation_id: int, message: WebSocketMessage):
        """
        向对话的所有订阅者发送消息
        
        Args:
            conversation_id: 对话ID
            message: WebSocket消息
        """
        try:
            if conversation_id in self.conversation_subscribers:
                subscribers = self.conversation_subscribers[conversation_id].copy()
                
                for user_id in subscribers:
                    await self.send_to_user(user_id, message)
            
        except Exception as e:
            self.logger.error(f"Error sending message to conversation {conversation_id}: {e}")
    
    async def broadcast_to_all(self, message: WebSocketMessage):
        """
        向所有连接的用户广播消息
        
        Args:
            message: WebSocket消息
        """
        try:
            all_users = list(self.user_connections.keys())
            
            for user_id in all_users:
                await self.send_to_user(user_id, message)
            
        except Exception as e:
            self.logger.error(f"Error broadcasting message: {e}")
    
    async def handle_user_message(self, connection_id: str, message_data: Dict[str, Any]):
        """
        处理用户发送的WebSocket消息
        
        Args:
            connection_id: 连接ID
            message_data: 消息数据
        """
        connection = self._find_connection(connection_id)
        if not connection:
            return
        
        try:
            message_type = message_data.get("type")
            data = message_data.get("data", {})
            conversation_id = message_data.get("conversation_id")
            
            # 更新心跳时间
            connection.last_heartbeat = datetime.now(timezone.utc)
            
            if message_type == "heartbeat":
                await self._handle_heartbeat(connection_id)
                
            elif message_type == "subscribe_conversation":
                conversation_id = data.get("conversation_id")
                if conversation_id:
                    await self.subscribe_to_conversation(connection.user_id, conversation_id)
                    
            elif message_type == "unsubscribe_conversation":
                conversation_id = data.get("conversation_id")
                if conversation_id:
                    await self.unsubscribe_from_conversation(connection.user_id, conversation_id)
                    
            elif message_type == "user_typing":
                if conversation_id:
                    await self._handle_user_typing(connection.user_id, conversation_id, True)
                    
            elif message_type == "user_stop_typing":
                if conversation_id:
                    await self._handle_user_typing(connection.user_id, conversation_id, False)
                    
            elif message_type == "get_connection_info":
                await self._send_connection_info(connection_id)
                
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
            
            self.stats["total_messages_received"] += 1
            
        except Exception as e:
            self.logger.error(f"Error handling user message from {connection_id}: {e}")
            await self._send_error_message(connection_id, str(e))
    
    async def _send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """向指定连接发送消息"""
        connection = self._find_connection(connection_id)
        if not connection:
            return
        
        try:
            await connection.websocket.send_text(message.to_json())
            self.stats["total_messages_sent"] += 1
            
        except Exception as e:
            self.logger.warning(f"Failed to send message to connection {connection_id}: {e}")
            # 标记连接为错误状态
            connection.status = ConnectionStatus.ERROR
            raise
    
    async def _handle_heartbeat(self, connection_id: str):
        """处理心跳消息"""
        connection = self._find_connection(connection_id)
        if connection:
            connection.last_heartbeat = datetime.now(timezone.utc)
            
            # 更新状态管理器的心跳时间
            await websocket_state_manager.update_heartbeat(connection_id)
            
            await self._send_to_connection(connection_id, WebSocketMessage(
                type=MessageType.HEARTBEAT,
                data={
                    "server_time": datetime.now(timezone.utc).isoformat(),
                    "connection_status": "healthy"
                }
            ))
    
    async def _handle_user_typing(self, user_id: int, conversation_id: int, is_typing: bool):
        """处理用户输入状态"""
        message = WebSocketMessage(
            type=MessageType.TYPING_INDICATOR,
            conversation_id=conversation_id,
            data={
                "user_id": user_id,
                "is_typing": is_typing,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # 向对话的其他订阅者发送输入状态（排除发送者）
        if conversation_id in self.conversation_subscribers:
            subscribers = self.conversation_subscribers[conversation_id].copy()
            subscribers.discard(user_id)  # 排除发送者
            
            for subscriber_id in subscribers:
                await self.send_to_user(subscriber_id, message)
    
    async def _send_connection_info(self, connection_id: str):
        """发送连接信息"""
        connection = self._find_connection(connection_id)
        if not connection:
            return
        
        info = {
            "connection_id": connection_id,
            "user_id": connection.user_id,
            "status": connection.status.value,
            "connected_at": connection.connected_at.isoformat(),
            "subscribed_conversations": list(connection.subscribed_conversations),
            "server_stats": self.get_stats()
        }
        
        await self._send_to_connection(connection_id, WebSocketMessage(
            type=MessageType.SYSTEM_NOTIFICATION,
            data=info
        ))
    
    async def _send_error_message(self, connection_id: str, error_message: str):
        """发送错误消息"""
        await self._send_to_connection(connection_id, WebSocketMessage(
            type=MessageType.ERROR,
            data={
                "error": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ))
    
    async def _cache_offline_message(self, user_id: int, message: WebSocketMessage):
        """缓存离线消息"""
        if user_id not in self.offline_message_queue:
            self.offline_message_queue[user_id] = []
        
        # 限制离线消息数量
        if len(self.offline_message_queue[user_id]) >= self.max_offline_messages:
            self.offline_message_queue[user_id].pop(0)  # 移除最旧的消息
        
        self.offline_message_queue[user_id].append(message)
        
        # 缓存到Redis（可选）
        if self.redis_client:
            try:
                await self.redis_client.lpush(
                    f"offline_messages:{user_id}",
                    message.to_json()
                )
                await self.redis_client.ltrim(f"offline_messages:{user_id}", 0, self.max_offline_messages - 1)
            except Exception as e:
                self.logger.warning(f"Failed to cache offline message to Redis: {e}")
    
    async def _send_offline_messages(self, user_id: int, connection_id: str):
        """发送离线消息"""
        try:
            # 从内存获取离线消息
            messages = self.offline_message_queue.get(user_id, [])
            
            # 从Redis获取离线消息（如果有）
            if self.redis_client:
                try:
                    redis_messages = await self.redis_client.lrange(f"offline_messages:{user_id}", 0, -1)
                    for msg_json in reversed(redis_messages):  # 按时间顺序发送
                        try:
                            msg_data = json.loads(msg_json)
                            message = WebSocketMessage(
                                type=MessageType(msg_data["type"]),
                                data=msg_data["data"],
                                conversation_id=msg_data.get("conversation_id"),
                                message_id=msg_data.get("message_id"),
                                timestamp=datetime.fromisoformat(msg_data["timestamp"])
                            )
                            messages.append(message)
                        except Exception as e:
                            self.logger.warning(f"Failed to parse offline message: {e}")
                    
                    # 清理Redis中的离线消息
                    await self.redis_client.delete(f"offline_messages:{user_id}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to retrieve offline messages from Redis: {e}")
            
            # 发送离线消息
            for message in messages:
                await self._send_to_connection(connection_id, message)
            
            # 清理内存中的离线消息
            self.offline_message_queue.pop(user_id, None)
            
            if messages:
                self.logger.info(f"Sent {len(messages)} offline messages to user {user_id}")
                
        except Exception as e:
            self.logger.error(f"Error sending offline messages to user {user_id}: {e}")
    
    def _find_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """查找连接对象"""
        for user_connections in self.user_connections.values():
            if connection_id in user_connections:
                return user_connections[connection_id]
        return None
    
    async def _heartbeat_monitor(self):
        """心跳监控后台任务"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = datetime.now(timezone.utc)
                expired_connections = []
                
                # 检查所有连接的心跳状态
                for user_id, connections in self.user_connections.items():
                    for connection_id, connection in connections.items():
                        time_since_heartbeat = (current_time - connection.last_heartbeat).total_seconds()
                        
                        if time_since_heartbeat > self.connection_timeout:
                            expired_connections.append(connection_id)
                
                # 断开过期连接
                for connection_id in expired_connections:
                    self.logger.info(f"Disconnecting expired connection: {connection_id}")
                    await self._disconnect_connection(connection_id)
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {e}")
    
    async def _cleanup_expired_connections(self):
        """清理过期连接后台任务"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                
                # 清理空的用户连接字典
                empty_users = [
                    user_id for user_id, connections in self.user_connections.items()
                    if not connections
                ]
                
                for user_id in empty_users:
                    del self.user_connections[user_id]
                
                # 清理空的对话订阅
                empty_conversations = [
                    conv_id for conv_id, subscribers in self.conversation_subscribers.items()
                    if not subscribers
                ]
                
                for conv_id in empty_conversations:
                    del self.conversation_subscribers[conv_id]
                
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
    
    def add_event_handler(self, event_name: str, handler: Callable):
        """添加事件处理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        
        self.event_handlers[event_name].append(handler)
    
    async def _trigger_event(self, event_name: str, data: Dict[str, Any]):
        """触发事件"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        active_users = len(self.user_connections)
        active_connections = sum(len(conns) for conns in self.user_connections.values())
        active_conversations = len(self.conversation_subscribers)
        
        return {
            **self.stats,
            "active_users": active_users,
            "active_connections": active_connections,
            "active_conversations": active_conversations,
            "offline_message_queues": len(self.offline_message_queue),
            "total_offline_messages": sum(len(msgs) for msgs in self.offline_message_queue.values())
        }
    
    def get_user_connections(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的连接信息"""
        if user_id not in self.user_connections:
            return []
        
        return [conn.to_dict() for conn in self.user_connections[user_id].values()]
    
    def get_conversation_subscribers(self, conversation_id: int) -> List[int]:
        """获取对话的订阅者列表"""
        return list(self.conversation_subscribers.get(conversation_id, set()))
    
    async def close(self):
        """关闭WebSocket管理器"""
        try:
            # 断开所有连接
            all_connections = []
            for user_connections in self.user_connections.values():
                all_connections.extend(user_connections.keys())
            
            for connection_id in all_connections:
                await self._disconnect_connection(connection_id)
            
            # 关闭Redis连接
            if self.redis_client:
                await self.redis_client.close()
            
            self.logger.info("AI WebSocket Manager closed")
            
        except Exception as e:
            self.logger.error(f"Error closing AI WebSocket Manager: {e}")


# 全局WebSocket管理器实例
ai_websocket_manager = AIWebSocketManager()


# AI助手专用的WebSocket消息类型
class AIMessageType(Enum):
    """AI助手专用消息类型"""
    # AI响应流式传输
    AI_STREAM_START = "ai_stream_start"
    AI_STREAM_CHUNK = "ai_stream_chunk"
    AI_STREAM_END = "ai_stream_end"
    AI_STREAM_ERROR = "ai_stream_error"
    
    # AI状态更新
    AI_THINKING = "ai_thinking"
    AI_PROCESSING = "ai_processing"
    AI_READY = "ai_ready"
    
    # 对话管理
    CONVERSATION_CREATED = "conversation_created"
    CONVERSATION_UPDATED = "conversation_updated"
    CONVERSATION_DELETED = "conversation_deleted"
    
    # 消息管理
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_UPDATED = "message_updated"
    MESSAGE_DELETED = "message_deleted"


async def send_ai_response_chunk(conversation_id: int, chunk_data: Dict[str, Any]):
    """发送AI响应数据块"""
    message = WebSocketMessage(
        type=MessageType.AI_RESPONSE_CHUNK,
        conversation_id=conversation_id,
        data=chunk_data
    )
    
    await ai_websocket_manager.send_to_conversation(conversation_id, message)


async def send_ai_response_complete(conversation_id: int, response_data: Dict[str, Any]):
    """发送AI响应完成通知"""
    message = WebSocketMessage(
        type=MessageType.AI_RESPONSE_COMPLETE,
        conversation_id=conversation_id,
        data=response_data
    )
    
    await ai_websocket_manager.send_to_conversation(conversation_id, message)


async def send_ai_response_error(conversation_id: int, error_message: str):
    """发送AI响应错误通知"""
    message = WebSocketMessage(
        type=MessageType.AI_RESPONSE_ERROR,
        conversation_id=conversation_id,
        data={
            "error": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    
    await ai_websocket_manager.send_to_conversation(conversation_id, message)


async def notify_conversation_update(conversation_id: int, update_data: Dict[str, Any]):
    """通知对话更新"""
    message = WebSocketMessage(
        type=MessageType.CONVERSATION_STATUS,
        conversation_id=conversation_id,
        data=update_data
    )
    
    await ai_websocket_manager.send_to_conversation(conversation_id, message)


async def notify_message_status(conversation_id: int, message_id: str, status_data: Dict[str, Any]):
    """通知消息状态更新"""
    message = WebSocketMessage(
        type=MessageType.MESSAGE_STATUS,
        conversation_id=conversation_id,
        message_id=message_id,
        data=status_data
    )
    
    await ai_websocket_manager.send_to_conversation(conversation_id, message)