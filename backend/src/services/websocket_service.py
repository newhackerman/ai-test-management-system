"""
WebSocket实时通信服务
支持AI助手模块的实时消息推送和状态同步
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any, Callable
from enum import Enum
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..schemas.ai_assistant_api import WSMessage, WSMessageType, ConnectionStatus


logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接：user_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        
        # 连接元数据：WebSocket -> ConnectionInfo
        self.connection_info: Dict[WebSocket, 'ConnectionInfo'] = {}
        
        # 订阅管理：message_type -> Set[user_id]
        self.subscriptions: Dict[WSMessageType, Set[int]] = {}
        
        # 房间管理：room_id -> Set[user_id]
        self.rooms: Dict[str, Set[int]] = {}
        
        # 消息队列：user_id -> List[WSMessage]
        self.message_queues: Dict[int, List[WSMessage]] = {}
        
        # 心跳管理
        self.heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}
        
        # 统计信息
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0
        }
    
    async def connect(self, websocket: WebSocket, user_id: int, session_id: Optional[str] = None) -> bool:
        """
        建立WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
            session_id: 会话ID（可选）
            
        Returns:
            bool: 连接是否成功建立
        """
        try:
            await websocket.accept()
            
            # 添加到活跃连接
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            
            # 保存连接信息
            connection_info = ConnectionInfo(
                user_id=user_id,
                session_id=session_id,
                connected_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow()
            )
            self.connection_info[websocket] = connection_info
            
            # 启动心跳任务
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))
            self.heartbeat_tasks[websocket] = heartbeat_task
            
            # 更新统计
            self.stats["total_connections"] += 1
            self.stats["active_connections"] = len(self.connection_info)
            
            # 发送连接确认消息
            await self.send_to_user(user_id, WSMessage(
                type=WSMessageType.CONNECTION_STATUS,
                data={"status": "connected", "timestamp": datetime.utcnow().isoformat()},
                timestamp=datetime.utcnow().isoformat()
            ))
            
            # 发送离线消息队列
            await self._send_queued_messages(user_id)
            
            logger.info(f"WebSocket connection established for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection for user {user_id}: {e}")
            return False
    
    async def disconnect(self, websocket: WebSocket):
        """
        断开WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
        """
        try:
            connection_info = self.connection_info.get(websocket)
            if not connection_info:
                return
            
            user_id = connection_info.user_id
            
            # 从活跃连接中移除
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # 清理连接信息
            del self.connection_info[websocket]
            
            # 停止心跳任务
            if websocket in self.heartbeat_tasks:
                self.heartbeat_tasks[websocket].cancel()
                del self.heartbeat_tasks[websocket]
            
            # 从所有房间中移除
            for room_users in self.rooms.values():
                room_users.discard(user_id)
            
            # 更新统计
            self.stats["active_connections"] = len(self.connection_info)
            
            logger.info(f"WebSocket connection closed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def send_to_user(self, user_id: int, message: WSMessage) -> bool:
        """
        向指定用户发送消息
        
        Args:
            user_id: 用户ID
            message: 消息对象
            
        Returns:
            bool: 是否发送成功
        """
        try:
            if user_id not in self.active_connections:
                # 用户不在线，加入消息队列
                await self._queue_message(user_id, message)
                return False
            
            # 向用户的所有连接发送消息
            connections = self.active_connections[user_id].copy()
            success_count = 0
            
            for websocket in connections:
                try:
                    await websocket.send_text(message.json())
                    success_count += 1
                    self.stats["messages_sent"] += 1
                except Exception as e:
                    logger.warning(f"Failed to send message to user {user_id}: {e}")
                    # 连接可能已断开，清理连接
                    await self.disconnect(websocket)
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            return False
    
    async def send_to_room(self, room_id: str, message: WSMessage, exclude_user: Optional[int] = None) -> int:
        """
        向房间内所有用户发送消息
        
        Args:
            room_id: 房间ID
            message: 消息对象
            exclude_user: 排除的用户ID
            
        Returns:
            int: 成功发送的用户数量
        """
        try:
            if room_id not in self.rooms:
                return 0
            
            success_count = 0
            for user_id in self.rooms[room_id]:
                if exclude_user and user_id == exclude_user:
                    continue
                
                if await self.send_to_user(user_id, message):
                    success_count += 1
            
            return success_count
            
        except Exception as e:
            logger.error(f"Error sending message to room {room_id}: {e}")
            return 0
    
    async def broadcast(self, message: WSMessage, message_type: Optional[WSMessageType] = None) -> int:
        """
        广播消息给所有连接或订阅了特定类型的用户
        
        Args:
            message: 消息对象
            message_type: 消息类型（可选，用于订阅过滤）
            
        Returns:
            int: 成功发送的用户数量
        """
        try:
            target_users = set()
            
            if message_type and message_type in self.subscriptions:
                # 只发送给订阅了该类型消息的用户
                target_users = self.subscriptions[message_type]
            else:
                # 发送给所有在线用户
                target_users = set(self.active_connections.keys())
            
            success_count = 0
            for user_id in target_users:
                if await self.send_to_user(user_id, message):
                    success_count += 1
            
            return success_count
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return 0
    
    async def join_room(self, user_id: int, room_id: str):
        """
        用户加入房间
        
        Args:
            user_id: 用户ID
            room_id: 房间ID
        """
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        
        self.rooms[room_id].add(user_id)
        logger.debug(f"User {user_id} joined room {room_id}")
    
    async def leave_room(self, user_id: int, room_id: str):
        """
        用户离开房间
        
        Args:
            user_id: 用户ID
            room_id: 房间ID
        """
        if room_id in self.rooms:
            self.rooms[room_id].discard(user_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        
        logger.debug(f"User {user_id} left room {room_id}")
    
    async def subscribe(self, user_id: int, message_type: WSMessageType):
        """
        用户订阅消息类型
        
        Args:
            user_id: 用户ID
            message_type: 消息类型
        """
        if message_type not in self.subscriptions:
            self.subscriptions[message_type] = set()
        
        self.subscriptions[message_type].add(user_id)
        logger.debug(f"User {user_id} subscribed to {message_type}")
    
    async def unsubscribe(self, user_id: int, message_type: WSMessageType):
        """
        用户取消订阅消息类型
        
        Args:
            user_id: 用户ID
            message_type: 消息类型
        """
        if message_type in self.subscriptions:
            self.subscriptions[message_type].discard(user_id)
            if not self.subscriptions[message_type]:
                del self.subscriptions[message_type]
        
        logger.debug(f"User {user_id} unsubscribed from {message_type}")
    
    async def _queue_message(self, user_id: int, message: WSMessage):
        """
        将消息加入离线队列
        
        Args:
            user_id: 用户ID
            message: 消息对象
        """
        if user_id not in self.message_queues:
            self.message_queues[user_id] = []
        
        # 限制队列长度，避免内存溢出
        max_queue_size = 100
        if len(self.message_queues[user_id]) >= max_queue_size:
            self.message_queues[user_id].pop(0)  # 移除最旧的消息
        
        self.message_queues[user_id].append(message)
        logger.debug(f"Message queued for offline user {user_id}")
    
    async def _send_queued_messages(self, user_id: int):
        """
        发送离线消息队列
        
        Args:
            user_id: 用户ID
        """
        if user_id not in self.message_queues:
            return
        
        messages = self.message_queues[user_id]
        self.message_queues[user_id] = []
        
        for message in messages:
            await self.send_to_user(user_id, message)
        
        logger.debug(f"Sent {len(messages)} queued messages to user {user_id}")
    
    async def _heartbeat_loop(self, websocket: WebSocket):
        """
        心跳循环
        
        Args:
            websocket: WebSocket连接对象
        """
        try:
            while True:
                await asyncio.sleep(30)  # 30秒心跳间隔
                
                connection_info = self.connection_info.get(websocket)
                if not connection_info:
                    break
                
                # 发送心跳消息
                heartbeat_message = WSMessage(
                    type=WSMessageType.HEARTBEAT,
                    data={"timestamp": datetime.utcnow().isoformat()},
                    timestamp=datetime.utcnow().isoformat()
                )
                
                try:
                    await websocket.send_text(heartbeat_message.json())
                    connection_info.last_heartbeat = datetime.utcnow()
                except Exception:
                    # 连接已断开
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            "rooms_count": len(self.rooms),
            "subscriptions_count": len(self.subscriptions),
            "queued_messages": sum(len(queue) for queue in self.message_queues.values())
        }
    
    def get_user_connections(self, user_id: int) -> int:
        """
        获取用户连接数
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 连接数
        """
        return len(self.active_connections.get(user_id, set()))
    
    def is_user_online(self, user_id: int) -> bool:
        """
        检查用户是否在线
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否在线
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


class ConnectionInfo(BaseModel):
    """连接信息"""
    user_id: int
    session_id: Optional[str] = None
    connected_at: datetime
    last_heartbeat: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WebSocketService:
    """WebSocket服务"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.message_handlers: Dict[WSMessageType, Callable] = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """设置默认消息处理器"""
        self.message_handlers[WSMessageType.HEARTBEAT] = self._handle_heartbeat
        self.message_handlers[WSMessageType.SUBSCRIBE] = self._handle_subscribe
        self.message_handlers[WSMessageType.UNSUBSCRIBE] = self._handle_unsubscribe
        self.message_handlers[WSMessageType.JOIN_ROOM] = self._handle_join_room
        self.message_handlers[WSMessageType.LEAVE_ROOM] = self._handle_leave_room
    
    async def handle_websocket(self, websocket: WebSocket, user_id: int, session_id: Optional[str] = None):
        """
        处理WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
            session_id: 会话ID（可选）
        """
        # 建立连接
        if not await self.connection_manager.connect(websocket, user_id, session_id):
            return
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                await self._handle_message(websocket, data)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            # 清理连接
            await self.connection_manager.disconnect(websocket)
    
    async def _handle_message(self, websocket: WebSocket, data: str):
        """
        处理接收到的消息
        
        Args:
            websocket: WebSocket连接对象
            data: 消息数据
        """
        try:
            message_data = json.loads(data)
            message = WSMessage(**message_data)
            
            # 更新统计
            self.connection_manager.stats["messages_received"] += 1
            
            # 调用对应的处理器
            if message.type in self.message_handlers:
                await self.message_handlers[message.type](websocket, message)
            else:
                logger.warning(f"No handler for message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            
            # 发送错误响应
            error_message = WSMessage(
                type=WSMessageType.ERROR,
                data={"error": "Invalid message format", "details": str(e)},
                timestamp=datetime.utcnow().isoformat()
            )
            
            try:
                await websocket.send_text(error_message.json())
            except Exception:
                pass  # 连接可能已断开
    
    async def _handle_heartbeat(self, websocket: WebSocket, message: WSMessage):
        """处理心跳消息"""
        connection_info = self.connection_manager.connection_info.get(websocket)
        if connection_info:
            connection_info.last_heartbeat = datetime.utcnow()
    
    async def _handle_subscribe(self, websocket: WebSocket, message: WSMessage):
        """处理订阅消息"""
        connection_info = self.connection_manager.connection_info.get(websocket)
        if not connection_info:
            return
        
        message_type = message.data.get("message_type")
        if message_type:
            try:
                msg_type = WSMessageType(message_type)
                await self.connection_manager.subscribe(connection_info.user_id, msg_type)
            except ValueError:
                logger.warning(f"Invalid message type for subscription: {message_type}")
    
    async def _handle_unsubscribe(self, websocket: WebSocket, message: WSMessage):
        """处理取消订阅消息"""
        connection_info = self.connection_manager.connection_info.get(websocket)
        if not connection_info:
            return
        
        message_type = message.data.get("message_type")
        if message_type:
            try:
                msg_type = WSMessageType(message_type)
                await self.connection_manager.unsubscribe(connection_info.user_id, msg_type)
            except ValueError:
                logger.warning(f"Invalid message type for unsubscription: {message_type}")
    
    async def _handle_join_room(self, websocket: WebSocket, message: WSMessage):
        """处理加入房间消息"""
        connection_info = self.connection_manager.connection_info.get(websocket)
        if not connection_info:
            return
        
        room_id = message.data.get("room_id")
        if room_id:
            await self.connection_manager.join_room(connection_info.user_id, room_id)
    
    async def _handle_leave_room(self, websocket: WebSocket, message: WSMessage):
        """处理离开房间消息"""
        connection_info = self.connection_manager.connection_info.get(websocket)
        if not connection_info:
            return
        
        room_id = message.data.get("room_id")
        if room_id:
            await self.connection_manager.leave_room(connection_info.user_id, room_id)
    
    def register_handler(self, message_type: WSMessageType, handler: Callable):
        """
        注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理器函数
        """
        self.message_handlers[message_type] = handler
    
    async def send_ai_response(self, user_id: int, conversation_id: int, response: str, metadata: Optional[Dict] = None):
        """
        发送AI响应消息
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID
            response: AI响应内容
            metadata: 元数据
        """
        message = WSMessage(
            type=WSMessageType.AI_RESPONSE,
            data={
                "conversation_id": conversation_id,
                "response": response,
                "metadata": metadata or {}
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.connection_manager.send_to_user(user_id, message)
    
    async def send_suggestion_update(self, user_id: int, suggestion_id: int, status: str, metadata: Optional[Dict] = None):
        """
        发送建议状态更新消息
        
        Args:
            user_id: 用户ID
            suggestion_id: 建议ID
            status: 新状态
            metadata: 元数据
        """
        message = WSMessage(
            type=WSMessageType.SUGGESTION_UPDATE,
            data={
                "suggestion_id": suggestion_id,
                "status": status,
                "metadata": metadata or {}
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.connection_manager.send_to_user(user_id, message)
    
    async def send_analysis_progress(self, user_id: int, analysis_id: str, progress: float, status: str):
        """
        发送分析进度更新
        
        Args:
            user_id: 用户ID
            analysis_id: 分析ID
            progress: 进度（0-1）
            status: 状态
        """
        message = WSMessage(
            type=WSMessageType.ANALYSIS_PROGRESS,
            data={
                "analysis_id": analysis_id,
                "progress": progress,
                "status": status
            },
            timestamp=datetime.utcnow().isoformat()
        )
        
        await self.connection_manager.send_to_user(user_id, message)


# 全局WebSocket服务实例
websocket_service = WebSocketService()