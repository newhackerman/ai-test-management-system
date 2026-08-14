"""
仪表板实时推送服务

实现仪表板模块的WebSocket连接管理、事件订阅和数据推送功能
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Callable
from enum import Enum
import gzip
import time

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.websocket_connection import WebSocketConnection, ConnectionStatus, EventType, ClientType
from ..models.dashboard_config import RoleType
from ..core.database import get_db
from ..services.dashboard_service import DashboardService
from ..services.data_aggregation_service import DataAggregationService
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class DashboardEventType(Enum):
    """仪表板事件类型"""
    DASHBOARD_DATA_UPDATE = "DASHBOARD_DATA_UPDATE"  # 仪表板数据更新
    WIDGET_DATA_UPDATE = "WIDGET_DATA_UPDATE"  # 组件数据更新
    LAYOUT_CHANGED = "LAYOUT_CHANGED"  # 布局变更
    USER_ACTIVITY = "USER_ACTIVITY"  # 用户活动
    SYSTEM_ALERT = "SYSTEM_ALERT"  # 系统告警
    PERFORMANCE_METRICS = "PERFORMANCE_METRICS"  # 性能指标
    CONNECTION_STATUS = "CONNECTION_STATUS"  # 连接状态
    HEARTBEAT = "HEARTBEAT"  # 心跳检测
    ERROR = "ERROR"  # 错误消息


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class RealtimeMessage:
    """实时消息类"""
    
    def __init__(
        self,
        event_type: DashboardEventType,
        data: Dict[str, Any],
        target_user_ids: Optional[List[int]] = None,
        target_roles: Optional[List[str]] = None,
        target_projects: Optional[List[int]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        compress: bool = False
    ):
        self.message_id = f"{event_type.value}_{uuid.uuid4().hex[:12]}"
        self.event_type = event_type
        self.data = data
        self.target_user_ids = target_user_ids or []
        self.target_roles = target_roles or []
        self.target_projects = target_projects or []
        self.priority = priority
        self.compress = compress
        self.timestamp = datetime.utcnow()
        self.created_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'message_id': self.message_id,
            'type': self.event_type.value,
            'data': self.data,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'created_at': self.created_at
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def get_compressed_data(self) -> bytes:
        """获取压缩后的数据"""
        json_data = self.to_json()
        return gzip.compress(json_data.encode('utf-8'))


class ConnectionInfo:
    """连接信息类"""
    
    def __init__(
        self,
        websocket: WebSocket,
        user_id: int,
        role_type: str,
        connection_id: str,
        client_type: ClientType = ClientType.WEB_BROWSER
    ):
        self.websocket = websocket
        self.user_id = user_id
        self.role_type = role_type
        self.connection_id = connection_id
        self.client_type = client_type
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.subscribed_events: Set[DashboardEventType] = set()
        self.subscribed_projects: Set[int] = set()
        self.message_count = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.last_activity = datetime.utcnow()
        self.is_active = True
        self.client_info = {}
    
    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = datetime.utcnow()
        self.last_activity = datetime.utcnow()
    
    def is_connection_alive(self, timeout_minutes: int = 5) -> bool:
        """检查连接是否存活"""
        if not self.is_active:
            return False
        
        timeout = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        return self.last_heartbeat > timeout
    
    def record_message(self, bytes_count: int, is_sent: bool = True):
        """记录消息统计"""
        self.message_count += 1
        if is_sent:
            self.bytes_sent += bytes_count
        else:
            self.bytes_received += bytes_count
        self.last_activity = datetime.utcnow()


class DashboardRealtimeService:
    """仪表板实时推送服务"""
    
    def __init__(
        self,
        dashboard_service: DashboardService,
        data_aggregation_service: DataAggregationService
    ):
        self.dashboard_service = dashboard_service
        self.data_aggregation_service = data_aggregation_service
        
        # 连接管理
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.user_connections: Dict[int, Set[str]] = {}  # user_id -> connection_ids
        self.role_connections: Dict[str, Set[str]] = {}  # role -> connection_ids
        self.project_connections: Dict[int, Set[str]] = {}  # project_id -> connection_ids
        
        # 消息队列
        self.message_queues: Dict[int, List[RealtimeMessage]] = {}  # user_id -> messages
        self.priority_queues: Dict[MessagePriority, List[RealtimeMessage]] = {
            priority: [] for priority in MessagePriority
        }
        
        # 性能监控
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'errors': 0,
            'heartbeats': 0
        }
        
        # 配置
        self.heartbeat_interval = 30  # 心跳间隔(秒)
        self.connection_timeout = 300  # 连接超时(秒)
        self.max_queue_size = 100  # 最大队列长度
        self.compression_threshold = 1024  # 压缩阈值(字节)
        
        # 后台任务
        self.background_tasks: Set[asyncio.Task] = set()
        
        # Redis客户端
        self.redis_client = get_redis_client()
        
        # 启动后台任务
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 在没有运行事件循环的上下文中构造时（例如同步依赖解析），
        # asyncio.create_task 会抛出 RuntimeError。此处做防御性处理，
        # 后台任务会在首次进入异步上下文时按需启动。
        if not self._has_running_event_loop():
            logger.debug("No running event loop; deferring background task startup.")
            return

        # 心跳检测任务
        heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        self.background_tasks.add(heartbeat_task)
        heartbeat_task.add_done_callback(self.background_tasks.discard)

        # 消息处理任务
        message_task = asyncio.create_task(self._message_processor())
        self.background_tasks.add(message_task)
        message_task.add_done_callback(self.background_tasks.discard)

        # 连接清理任务
        cleanup_task = asyncio.create_task(self._connection_cleanup())
        self.background_tasks.add(cleanup_task)
        cleanup_task.add_done_callback(self.background_tasks.discard)

    @staticmethod
    def _has_running_event_loop() -> bool:
        try:
            asyncio.get_running_loop()
            return True
        except RuntimeError:
            return False
    
    async def connect_user(
        self,
        websocket: WebSocket,
        user_id: int,
        role_type: str,
        client_type: ClientType = ClientType.WEB_BROWSER,
        client_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        建立用户WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
            role_type: 用户角色
            client_type: 客户端类型
            client_info: 客户端信息
            
        Returns:
            str: 连接ID
        """
        try:
            # 接受连接
            await websocket.accept()
            
            # 生成连接ID
            connection_id = f"dashboard_{user_id}_{role_type}_{uuid.uuid4().hex[:8]}"
            
            # 创建连接信息
            connection_info = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                role_type=role_type,
                connection_id=connection_id,
                client_type=client_type
            )
            
            if client_info:
                connection_info.client_info = client_info
            
            # 存储连接信息
            self.active_connections[connection_id] = connection_info
            
            # 更新用户连接映射
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
            # 更新角色连接映射
            if role_type not in self.role_connections:
                self.role_connections[role_type] = set()
            self.role_connections[role_type].add(connection_id)
            
            # 更新统计
            self.stats['total_connections'] += 1
            self.stats['active_connections'] = len(self.active_connections)
            
            # 保存到数据库
            await self._save_connection_to_db(connection_info)
            
            # 发送连接确认消息
            await self._send_connection_status(connection_id, "connected")
            
            # 发送离线消息队列
            await self._send_queued_messages(user_id)
            
            # 发送初始数据
            await self._send_initial_dashboard_data(connection_id)
            
            logger.info(f"Dashboard WebSocket connection established: {connection_id}")
            return connection_id
            
        except Exception as e:
            logger.error(f"Failed to establish dashboard WebSocket connection: {e}")
            raise
    
    async def disconnect_user(self, connection_id: str, reason: Optional[str] = None):
        """
        断开用户连接
        
        Args:
            connection_id: 连接ID
            reason: 断开原因
        """
        try:
            if connection_id not in self.active_connections:
                return
            
            connection_info = self.active_connections[connection_id]
            user_id = connection_info.user_id
            role_type = connection_info.role_type
            
            # 标记连接为非活跃
            connection_info.is_active = False
            
            # 关闭WebSocket连接
            try:
                await connection_info.websocket.close()
            except Exception:
                pass  # 连接可能已经关闭
            
            # 从连接映射中移除
            self.active_connections.pop(connection_id, None)
            
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            if role_type in self.role_connections:
                self.role_connections[role_type].discard(connection_id)
                if not self.role_connections[role_type]:
                    del self.role_connections[role_type]
            
            # 从项目订阅中移除
            for project_connections in self.project_connections.values():
                project_connections.discard(connection_id)
            
            # 更新统计
            self.stats['active_connections'] = len(self.active_connections)
            
            # 更新数据库记录
            await self._update_connection_in_db(connection_id, ConnectionStatus.DISCONNECTED, reason)
            
            logger.info(f"Dashboard WebSocket connection closed: {connection_id}, reason: {reason}")
            
        except Exception as e:
            logger.error(f"Error during dashboard WebSocket disconnect: {e}")
    
    async def subscribe_to_events(
        self,
        connection_id: str,
        event_types: List[DashboardEventType]
    ):
        """
        订阅事件类型
        
        Args:
            connection_id: 连接ID
            event_types: 事件类型列表
        """
        if connection_id not in self.active_connections:
            return
        
        connection_info = self.active_connections[connection_id]
        connection_info.subscribed_events.update(event_types)
        
        logger.debug(f"Connection {connection_id} subscribed to events: {[e.value for e in event_types]}")
    
    async def unsubscribe_from_events(
        self,
        connection_id: str,
        event_types: List[DashboardEventType]
    ):
        """
        取消订阅事件类型
        
        Args:
            connection_id: 连接ID
            event_types: 事件类型列表
        """
        if connection_id not in self.active_connections:
            return
        
        connection_info = self.active_connections[connection_id]
        for event_type in event_types:
            connection_info.subscribed_events.discard(event_type)
        
        logger.debug(f"Connection {connection_id} unsubscribed from events: {[e.value for e in event_types]}")
    
    async def subscribe_to_projects(
        self,
        connection_id: str,
        project_ids: List[int]
    ):
        """
        订阅项目数据
        
        Args:
            connection_id: 连接ID
            project_ids: 项目ID列表
        """
        if connection_id not in self.active_connections:
            return
        
        connection_info = self.active_connections[connection_id]
        connection_info.subscribed_projects.update(project_ids)
        
        # 更新项目连接映射
        for project_id in project_ids:
            if project_id not in self.project_connections:
                self.project_connections[project_id] = set()
            self.project_connections[project_id].add(connection_id)
        
        logger.debug(f"Connection {connection_id} subscribed to projects: {project_ids}")
    
    async def unsubscribe_from_projects(
        self,
        connection_id: str,
        project_ids: List[int]
    ):
        """
        取消订阅项目数据
        
        Args:
            connection_id: 连接ID
            project_ids: 项目ID列表
        """
        if connection_id not in self.active_connections:
            return
        
        connection_info = self.active_connections[connection_id]
        for project_id in project_ids:
            connection_info.subscribed_projects.discard(project_id)
            
            # 从项目连接映射中移除
            if project_id in self.project_connections:
                self.project_connections[project_id].discard(connection_id)
                if not self.project_connections[project_id]:
                    del self.project_connections[project_id]
        
        logger.debug(f"Connection {connection_id} unsubscribed from projects: {project_ids}")
    
    async def send_message_to_user(
        self,
        user_id: int,
        message: RealtimeMessage
    ) -> bool:
        """
        向指定用户发送消息
        
        Args:
            user_id: 用户ID
            message: 实时消息
            
        Returns:
            bool: 是否发送成功
        """
        try:
            if user_id not in self.user_connections:
                # 用户不在线，加入消息队列
                await self._queue_message(user_id, message)
                return False
            
            success_count = 0
            connection_ids = self.user_connections[user_id].copy()
            
            for connection_id in connection_ids:
                if await self._send_message_to_connection(connection_id, message):
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            return False
    
    async def send_message_to_role(
        self,
        role_type: str,
        message: RealtimeMessage,
        exclude_user_id: Optional[int] = None
    ) -> int:
        """
        向指定角色发送消息
        
        Args:
            role_type: 角色类型
            message: 实时消息
            exclude_user_id: 排除的用户ID
            
        Returns:
            int: 成功发送的连接数
        """
        try:
            if role_type not in self.role_connections:
                return 0
            
            success_count = 0
            connection_ids = self.role_connections[role_type].copy()
            
            for connection_id in connection_ids:
                connection_info = self.active_connections.get(connection_id)
                if not connection_info:
                    continue
                
                if exclude_user_id and connection_info.user_id == exclude_user_id:
                    continue
                
                if await self._send_message_to_connection(connection_id, message):
                    success_count += 1
            
            return success_count
            
        except Exception as e:
            logger.error(f"Error sending message to role {role_type}: {e}")
            return 0
    
    async def send_message_to_project(
        self,
        project_id: int,
        message: RealtimeMessage,
        exclude_user_id: Optional[int] = None
    ) -> int:
        """
        向项目订阅者发送消息
        
        Args:
            project_id: 项目ID
            message: 实时消息
            exclude_user_id: 排除的用户ID
            
        Returns:
            int: 成功发送的连接数
        """
        try:
            if project_id not in self.project_connections:
                return 0
            
            success_count = 0
            connection_ids = self.project_connections[project_id].copy()
            
            for connection_id in connection_ids:
                connection_info = self.active_connections.get(connection_id)
                if not connection_info:
                    continue
                
                if exclude_user_id and connection_info.user_id == exclude_user_id:
                    continue
                
                if await self._send_message_to_connection(connection_id, message):
                    success_count += 1
            
            return success_count
            
        except Exception as e:
            logger.error(f"Error sending message to project {project_id}: {e}")
            return 0
    
    async def broadcast_message(
        self,
        message: RealtimeMessage,
        target_roles: Optional[List[str]] = None,
        target_projects: Optional[List[int]] = None
    ) -> int:
        """
        广播消息
        
        Args:
            message: 实时消息
            target_roles: 目标角色列表
            target_projects: 目标项目列表
            
        Returns:
            int: 成功发送的连接数
        """
        try:
            target_connections = set()
            
            # 根据角色筛选连接
            if target_roles:
                for role in target_roles:
                    if role in self.role_connections:
                        target_connections.update(self.role_connections[role])
            
            # 根据项目筛选连接
            if target_projects:
                for project_id in target_projects:
                    if project_id in self.project_connections:
                        target_connections.update(self.project_connections[project_id])
            
            # 如果没有指定目标，则广播给所有连接
            if not target_roles and not target_projects:
                target_connections = set(self.active_connections.keys())
            
            success_count = 0
            for connection_id in target_connections:
                if await self._send_message_to_connection(connection_id, message):
                    success_count += 1
            
            return success_count
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return 0
    
    async def send_dashboard_data_update(
        self,
        user_id: int,
        dashboard_data: Dict[str, Any]
    ):
        """
        发送仪表板数据更新
        
        Args:
            user_id: 用户ID
            dashboard_data: 仪表板数据
        """
        message = RealtimeMessage(
            event_type=DashboardEventType.DASHBOARD_DATA_UPDATE,
            data=dashboard_data,
            target_user_ids=[user_id],
            priority=MessagePriority.NORMAL
        )
        
        await self.send_message_to_user(user_id, message)
    
    async def send_widget_data_update(
        self,
        widget_type: str,
        widget_data: Dict[str, Any],
        target_user_ids: Optional[List[int]] = None,
        target_roles: Optional[List[str]] = None,
        target_projects: Optional[List[int]] = None
    ):
        """
        发送组件数据更新
        
        Args:
            widget_type: 组件类型
            widget_data: 组件数据
            target_user_ids: 目标用户ID列表
            target_roles: 目标角色列表
            target_projects: 目标项目列表
        """
        message = RealtimeMessage(
            event_type=DashboardEventType.WIDGET_DATA_UPDATE,
            data={
                'widget_type': widget_type,
                'data': widget_data
            },
            target_user_ids=target_user_ids,
            target_roles=target_roles,
            target_projects=target_projects,
            priority=MessagePriority.NORMAL
        )
        
        if target_user_ids:
            for user_id in target_user_ids:
                await self.send_message_to_user(user_id, message)
        else:
            await self.broadcast_message(message, target_roles, target_projects)
    
    async def send_system_alert(
        self,
        alert_type: str,
        alert_data: Dict[str, Any],
        target_roles: Optional[List[str]] = None,
        priority: MessagePriority = MessagePriority.HIGH
    ):
        """
        发送系统告警
        
        Args:
            alert_type: 告警类型
            alert_data: 告警数据
            target_roles: 目标角色列表
            priority: 消息优先级
        """
        message = RealtimeMessage(
            event_type=DashboardEventType.SYSTEM_ALERT,
            data={
                'alert_type': alert_type,
                'data': alert_data
            },
            target_roles=target_roles,
            priority=priority
        )
        
        await self.broadcast_message(message, target_roles)
    
    async def handle_websocket_message(
        self,
        connection_id: str,
        message_data: str
    ):
        """
        处理WebSocket消息
        
        Args:
            connection_id: 连接ID
            message_data: 消息数据
        """
        try:
            if connection_id not in self.active_connections:
                return
            
            connection_info = self.active_connections[connection_id]
            
            # 更新接收统计
            connection_info.record_message(len(message_data.encode('utf-8')), is_sent=False)
            self.stats['messages_received'] += 1
            
            # 解析消息
            message = json.loads(message_data)
            message_type = message.get('type')
            
            if message_type == 'heartbeat':
                await self._handle_heartbeat(connection_id, message)
            elif message_type == 'subscribe_events':
                await self._handle_subscribe_events(connection_id, message)
            elif message_type == 'unsubscribe_events':
                await self._handle_unsubscribe_events(connection_id, message)
            elif message_type == 'subscribe_projects':
                await self._handle_subscribe_projects(connection_id, message)
            elif message_type == 'unsubscribe_projects':
                await self._handle_unsubscribe_projects(connection_id, message)
            elif message_type == 'request_data':
                await self._handle_data_request(connection_id, message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self._send_error_message(connection_id, str(e))
    
    async def _send_message_to_connection(
        self,
        connection_id: str,
        message: RealtimeMessage
    ) -> bool:
        """
        向指定连接发送消息
        
        Args:
            connection_id: 连接ID
            message: 实时消息
            
        Returns:
            bool: 是否发送成功
        """
        try:
            if connection_id not in self.active_connections:
                return False
            
            connection_info = self.active_connections[connection_id]
            
            # 检查连接是否存活
            if not connection_info.is_connection_alive():
                await self.disconnect_user(connection_id, "Connection timeout")
                return False
            
            # 检查事件订阅
            if (message.event_type not in connection_info.subscribed_events and
                message.event_type not in [DashboardEventType.CONNECTION_STATUS, DashboardEventType.HEARTBEAT]):
                return False
            
            # 准备消息数据
            message_json = message.to_json()
            message_bytes = len(message_json.encode('utf-8'))
            
            # 检查是否需要压缩
            if message_bytes > self.compression_threshold and message.compress:
                compressed_data = message.get_compressed_data()
                await connection_info.websocket.send_bytes(compressed_data)
            else:
                await connection_info.websocket.send_text(message_json)
            
            # 更新统计
            connection_info.record_message(message_bytes, is_sent=True)
            self.stats['messages_sent'] += 1
            self.stats['bytes_sent'] += message_bytes
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {e}")
            await self.disconnect_user(connection_id, f"Send error: {str(e)}")
            return False
    
    async def _queue_message(self, user_id: int, message: RealtimeMessage):
        """
        将消息加入离线队列
        
        Args:
            user_id: 用户ID
            message: 实时消息
        """
        if user_id not in self.message_queues:
            self.message_queues[user_id] = []
        
        # 限制队列长度
        if len(self.message_queues[user_id]) >= self.max_queue_size:
            self.message_queues[user_id].pop(0)  # 移除最旧的消息
        
        self.message_queues[user_id].append(message)
        
        # 同时存储到Redis
        await self._cache_offline_message(user_id, message)
    
    async def _send_queued_messages(self, user_id: int):
        """
        发送离线消息队列
        
        Args:
            user_id: 用户ID
        """
        # 从内存队列发送
        if user_id in self.message_queues:
            messages = self.message_queues[user_id]
            self.message_queues[user_id] = []
            
            for message in messages:
                await self.send_message_to_user(user_id, message)
        
        # 从Redis缓存发送
        await self._send_cached_offline_messages(user_id)
    
    async def _send_connection_status(self, connection_id: str, status: str):
        """
        发送连接状态消息
        
        Args:
            connection_id: 连接ID
            status: 连接状态
        """
        message = RealtimeMessage(
            event_type=DashboardEventType.CONNECTION_STATUS,
            data={
                'status': status,
                'connection_id': connection_id,
                'timestamp': datetime.utcnow().isoformat()
            },
            priority=MessagePriority.HIGH
        )
        
        await self._send_message_to_connection(connection_id, message)
    
    async def _send_initial_dashboard_data(self, connection_id: str):
        """
        发送初始仪表板数据
        
        Args:
            connection_id: 连接ID
        """
        try:
            if connection_id not in self.active_connections:
                return
            
            connection_info = self.active_connections[connection_id]
            user_id = connection_info.user_id
            role_type = connection_info.role_type
            
            # 获取仪表板配置
            dashboard_config = await self.dashboard_service.get_role_dashboard(user_id, role_type)
            
            # 获取初始数据
            initial_data = await self.data_aggregation_service.get_dashboard_initial_data(
                user_id, role_type
            )
            
            message = RealtimeMessage(
                event_type=DashboardEventType.DASHBOARD_DATA_UPDATE,
                data={
                    'config': dashboard_config.to_dict() if dashboard_config else None,
                    'data': initial_data
                },
                priority=MessagePriority.HIGH
            )
            
            await self._send_message_to_connection(connection_id, message)
            
        except Exception as e:
            logger.error(f"Error sending initial dashboard data: {e}")
    
    async def _send_error_message(self, connection_id: str, error_message: str):
        """
        发送错误消息
        
        Args:
            connection_id: 连接ID
            error_message: 错误消息
        """
        message = RealtimeMessage(
            event_type=DashboardEventType.ERROR,
            data={
                'error': error_message,
                'timestamp': datetime.utcnow().isoformat()
            },
            priority=MessagePriority.HIGH
        )
        
        await self._send_message_to_connection(connection_id, message)
    
    async def _handle_heartbeat(self, connection_id: str, message: Dict[str, Any]):
        """
        处理心跳消息
        
        Args:
            connection_id: 连接ID
            message: 消息数据
        """
        if connection_id in self.active_connections:
            connection_info = self.active_connections[connection_id]
            connection_info.update_heartbeat()
            self.stats['heartbeats'] += 1
            
            # 发送心跳响应
            response = RealtimeMessage(
                event_type=DashboardEventType.HEARTBEAT,
                data={
                    'timestamp': datetime.utcnow().isoformat(),
                    'server_time': time.time()
                },
                priority=MessagePriority.LOW
            )
            
            await self._send_message_to_connection(connection_id, response)
    
    async def _handle_subscribe_events(self, connection_id: str, message: Dict[str, Any]):
        """
        处理事件订阅消息
        
        Args:
            connection_id: 连接ID
            message: 消息数据
        """
        event_types_str = message.get('data', {}).get('event_types', [])
        event_types = []
        
        for event_type_str in event_types_str:
            try:
                event_type = DashboardEventType(event_type_str)
                event_types.append(event_type)
            except ValueError:
                logger.warning(f"Invalid event type: {event_type_str}")
        
        if event_types:
            await self.subscribe_to_events(connection_id, event_types)
    
    async def _handle_unsubscribe_events(self, connection_id: str, message: Dict[str, Any]):
        """
        处理取消事件订阅消息
        
        Args:
            connection_id: 连接ID
            message: 消息数据
        """
        event_types_str = message.get('data', {}).get('event_types', [])
        event_types = []
        
        for event_type_str in event_types_str:
            try:
                event_type = DashboardEventType(event_type_str)
                event_types.append(event_type)
            except ValueError:
                logger.warning(f"Invalid event type: {event_type_str}")
        
        if event_types:
            await self.unsubscribe_from_events(connection_id, event_types)
    
    async def _handle_subscribe_projects(self, connection_id: str, message: Dict[str, Any]):
        """
        处理项目订阅消息
        
        Args:
            connection_id: 连接ID
            message: 消息数据
        """
        project_ids = message.get('data', {}).get('project_ids', [])
        if project_ids:
            await self.subscribe_to_projects(connection_id, project_ids)
    
    async def _handle_unsubscribe_projects(self, connection_id: str, message: Dict[str, Any]):
        """
        处理取消项目订阅消息
        
        Args:
            connection_id: 连接ID
            message: 消息数据
        """
        project_ids = message.get('data', {}).get('project_ids', [])
        if project_ids:
            await self.unsubscribe_from_projects(connection_id, project_ids)
    
    async def _handle_data_request(self, connection_id: str, message: Dict[str, Any]):
        """
        处理数据请求消息
        
        Args:
            connection_id: 连接ID
            message: 消息数据
        """
        try:
            if connection_id not in self.active_connections:
                return
            
            connection_info = self.active_connections[connection_id]
            data_type = message.get('data', {}).get('data_type')
            widget_type = message.get('data', {}).get('widget_type')
            
            if data_type == 'widget_data' and widget_type:
                # 获取组件数据
                widget_data = await self.data_aggregation_service.get_widget_data(
                    connection_info.user_id,
                    connection_info.role_type,
                    widget_type
                )
                
                response = RealtimeMessage(
                    event_type=DashboardEventType.WIDGET_DATA_UPDATE,
                    data={
                        'widget_type': widget_type,
                        'data': widget_data
                    },
                    priority=MessagePriority.NORMAL
                )
                
                await self._send_message_to_connection(connection_id, response)
            
        except Exception as e:
            logger.error(f"Error handling data request: {e}")
            await self._send_error_message(connection_id, str(e))
    
    async def _heartbeat_monitor(self):
        """心跳监控后台任务"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # 检查所有连接的心跳状态
                expired_connections = []
                
                for connection_id, connection_info in self.active_connections.items():
                    if not connection_info.is_connection_alive():
                        expired_connections.append(connection_id)
                
                # 清理过期连接
                for connection_id in expired_connections:
                    await self.disconnect_user(connection_id, "Heartbeat timeout")
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
    
    async def _message_processor(self):
        """消息处理后台任务"""
        while True:
            try:
                await asyncio.sleep(1)  # 每秒处理一次
                
                # 处理优先级队列中的消息
                for priority in [MessagePriority.CRITICAL, MessagePriority.HIGH, MessagePriority.NORMAL, MessagePriority.LOW]:
                    if self.priority_queues[priority]:
                        messages = self.priority_queues[priority][:10]  # 每次处理10条消息
                        self.priority_queues[priority] = self.priority_queues[priority][10:]
                        
                        for message in messages:
                            await self._process_priority_message(message)
                
            except Exception as e:
                logger.error(f"Error in message processor: {e}")
    
    async def _connection_cleanup(self):
        """连接清理后台任务"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                
                # 清理空的映射
                empty_user_connections = [
                    user_id for user_id, connections in self.user_connections.items()
                    if not connections
                ]
                for user_id in empty_user_connections:
                    del self.user_connections[user_id]
                
                empty_role_connections = [
                    role for role, connections in self.role_connections.items()
                    if not connections
                ]
                for role in empty_role_connections:
                    del self.role_connections[role]
                
                empty_project_connections = [
                    project_id for project_id, connections in self.project_connections.items()
                    if not connections
                ]
                for project_id in empty_project_connections:
                    del self.project_connections[project_id]
                
                # 清理过期的离线消息
                await self._cleanup_expired_messages()
                
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")
    
    async def _process_priority_message(self, message: RealtimeMessage):
        """
        处理优先级消息
        
        Args:
            message: 实时消息
        """
        try:
            if message.target_user_ids:
                for user_id in message.target_user_ids:
                    await self.send_message_to_user(user_id, message)
            else:
                await self.broadcast_message(message, message.target_roles, message.target_projects)
        except Exception as e:
            logger.error(f"Error processing priority message: {e}")
    
    async def _cleanup_expired_messages(self):
        """清理过期的离线消息"""
        try:
            current_time = time.time()
            expired_threshold = current_time - (24 * 3600)  # 24小时过期
            
            for user_id, messages in list(self.message_queues.items()):
                # 过滤掉过期的消息
                valid_messages = [
                    msg for msg in messages
                    if msg.created_at > expired_threshold
                ]
                
                if len(valid_messages) != len(messages):
                    self.message_queues[user_id] = valid_messages
                    if not valid_messages:
                        del self.message_queues[user_id]
            
            # 清理Redis中的过期消息
            await self._cleanup_redis_messages()
            
        except Exception as e:
            logger.error(f"Error cleaning up expired messages: {e}")
    
    async def _save_connection_to_db(self, connection_info: ConnectionInfo):
        """
        保存连接信息到数据库
        
        Args:
            connection_info: 连接信息
        """
        try:
            db = next(get_db())
            
            db_connection = WebSocketConnection.create_connection(
                user_id=connection_info.user_id,
                role_type=connection_info.role_type,
                client_type=connection_info.client_type,
                client_info=connection_info.client_info
            )
            db_connection.connection_id = connection_info.connection_id
            db_connection.status = ConnectionStatus.CONNECTED
            
            db.add(db_connection)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving connection to database: {e}")
    
    async def _update_connection_in_db(
        self,
        connection_id: str,
        status: ConnectionStatus,
        error_message: Optional[str] = None
    ):
        """
        更新数据库中的连接状态
        
        Args:
            connection_id: 连接ID
            status: 连接状态
            error_message: 错误消息
        """
        try:
            db = next(get_db())
            
            db_connection = db.query(WebSocketConnection).filter(
                WebSocketConnection.connection_id == connection_id
            ).first()
            
            if db_connection:
                db_connection.status = status
                if status == ConnectionStatus.DISCONNECTED:
                    db_connection.disconnect_time = datetime.utcnow()
                if error_message:
                    db_connection.last_error = error_message
                    db_connection.error_count += 1
                
                db.commit()
            
        except Exception as e:
            logger.error(f"Error updating connection in database: {e}")
    
    async def _cache_offline_message(self, user_id: int, message: RealtimeMessage):
        """
        缓存离线消息到Redis
        
        Args:
            user_id: 用户ID
            message: 实时消息
        """
        try:
            if self.redis_client:
                key = f"dashboard:offline_messages:{user_id}"
                message_data = message.to_dict()
                
                await self.redis_client.lpush(key, json.dumps(message_data))
                await self.redis_client.ltrim(key, 0, self.max_queue_size - 1)  # 限制队列长度
                await self.redis_client.expire(key, 86400)  # 24小时过期
                
        except Exception as e:
            logger.error(f"Error caching offline message: {e}")
    
    async def _send_cached_offline_messages(self, user_id: int):
        """
        发送Redis缓存的离线消息
        
        Args:
            user_id: 用户ID
        """
        try:
            if self.redis_client:
                key = f"dashboard:offline_messages:{user_id}"
                
                # 获取所有离线消息
                cached_messages = await self.redis_client.lrange(key, 0, -1)
                
                for message_json in reversed(cached_messages):  # 按时间顺序发送
                    try:
                        message_data = json.loads(message_json)
                        message = RealtimeMessage(
                            event_type=DashboardEventType(message_data['type']),
                            data=message_data['data'],
                            priority=MessagePriority(message_data['priority'])
                        )
                        message.message_id = message_data['message_id']
                        message.timestamp = datetime.fromisoformat(message_data['timestamp'])
                        
                        await self.send_message_to_user(user_id, message)
                        
                    except Exception as e:
                        logger.error(f"Error processing cached message: {e}")
                
                # 清理已发送的消息
                await self.redis_client.delete(key)
                
        except Exception as e:
            logger.error(f"Error sending cached offline messages: {e}")
    
    async def _cleanup_redis_messages(self):
        """清理Redis中的过期消息"""
        try:
            if self.redis_client:
                # 获取所有离线消息键
                pattern = "dashboard:offline_messages:*"
                keys = await self.redis_client.keys(pattern)
                
                for key in keys:
                    # 检查键的TTL，如果已过期则删除
                    ttl = await self.redis_client.ttl(key)
                    if ttl == -1:  # 没有设置过期时间
                        await self.redis_client.expire(key, 86400)  # 设置24小时过期
                    elif ttl == -2:  # 键不存在
                        continue
                        
        except Exception as e:
            logger.error(f"Error cleaning up Redis messages: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            'active_connections_detail': {
                'total': len(self.active_connections),
                'by_role': {
                    role: len(connections) 
                    for role, connections in self.role_connections.items()
                },
                'by_project': {
                    str(project_id): len(connections)
                    for project_id, connections in self.project_connections.items()
                }
            },
            'message_queues': {
                'total_users': len(self.message_queues),
                'total_messages': sum(len(queue) for queue in self.message_queues.values())
            },
            'background_tasks': len(self.background_tasks)
        }
    
    def is_user_online(self, user_id: int) -> bool:
        """
        检查用户是否在线
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否在线
        """
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0
    
    def get_user_connection_count(self, user_id: int) -> int:
        """
        获取用户连接数
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 连接数
        """
        return len(self.user_connections.get(user_id, set()))
    
    async def shutdown(self):
        """关闭服务"""
        try:
            # 取消所有后台任务
            for task in self.background_tasks:
                task.cancel()
            
            # 等待任务完成
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # 关闭所有连接
            connection_ids = list(self.active_connections.keys())
            for connection_id in connection_ids:
                await self.disconnect_user(connection_id, "Service shutdown")
            
            logger.info("Dashboard realtime service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {e}")


# 全局实例
dashboard_realtime_service: Optional[DashboardRealtimeService] = None


def get_dashboard_realtime_service() -> DashboardRealtimeService:
    """获取仪表板实时服务实例"""
    global dashboard_realtime_service
    
    if dashboard_realtime_service is None:
        from .dashboard_service import get_dashboard_service
        from .data_aggregation_service import get_data_aggregation_service
        
        dashboard_realtime_service = DashboardRealtimeService(
            dashboard_service=get_dashboard_service(),
            data_aggregation_service=get_data_aggregation_service()
        )
    
    return dashboard_realtime_service