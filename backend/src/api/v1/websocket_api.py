"""
WebSocket API接口

提供WebSocket连接建立、事件订阅、实时数据推送和消息路由功能
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field, validator
from datetime import datetime, timedelta
from enum import Enum
import json
import asyncio
import logging
import uuid

from ...core.database import get_db
from ...services.dashboard_realtime_service import RealtimeService
from ...services.data_aggregation_service import DataAggregationService
from ...services.auth import verify_websocket_token, get_current_user
from ...models.user import User
from ...models.dashboard_config import RoleType
from ...decorators.dashboard_permissions import (
    require_dashboard_permission,
    get_user_dashboard_permissions
)
from ...services.dashboard_permission_service import DashboardPermissionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/websocket", tags=["WebSocket实时通信"])

# 枚举定义

class MessageType(str, Enum):
    """消息类型"""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    HEARTBEAT = "heartbeat"
    DATA_UPDATE = "data_update"
    EVENT = "event"
    ERROR = "error"
    REQUEST_DATA = "request_data"
    BROADCAST = "broadcast"

class EventType(str, Enum):
    """事件类型"""
    PROJECT_UPDATE = "project_update"
    REQUIREMENT_UPDATE = "requirement_update"
    TEST_UPDATE = "test_update"
    SYSTEM_ALERT = "system_alert"
    USER_ACTIVITY = "user_activity"
    DASHBOARD_CONFIG_CHANGE = "dashboard_config_change"
    WIDGET_DATA_REFRESH = "widget_data_refresh"

class ConnectionStatus(str, Enum):
    """连接状态"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"

# Pydantic模型定义

class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: MessageType
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    message_id: Optional[str] = None

    class Config:
        use_enum_values = True

class SubscribeRequest(BaseModel):
    """订阅请求模型"""
    events: List[EventType] = Field(..., description="要订阅的事件类型列表")
    project_ids: Optional[List[int]] = Field(None, description="项目ID过滤")
    widget_types: Optional[List[str]] = Field(None, description="组件类型过滤")

    class Config:
        use_enum_values = True

class DataRequest(BaseModel):
    """数据请求模型"""
    widget_type: str = Field(..., description="组件类型")
    parameters: Optional[Dict[str, Any]] = Field(None, description="请求参数")
    force_refresh: bool = Field(False, description="是否强制刷新")

class BroadcastMessage(BaseModel):
    """广播消息模型"""
    event_type: EventType
    data: Dict[str, Any]
    target_roles: Optional[List[str]] = Field(None, description="目标角色")
    target_users: Optional[List[int]] = Field(None, description="目标用户")
    project_ids: Optional[List[int]] = Field(None, description="项目范围")

    class Config:
        use_enum_values = True

class ConnectionInfo(BaseModel):
    """连接信息模型"""
    connection_id: str
    user_id: int
    role_type: str
    connected_at: str
    last_heartbeat: str
    subscriptions: List[str]
    status: ConnectionStatus

    class Config:
        use_enum_values = True

# 全局连接管理器
class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.user_connections: Dict[int, Set[str]] = {}
        self.role_connections: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: int, role_type: str):
        """建立连接"""
        await websocket.accept()
        
        connection_info = {
            'websocket': websocket,
            'user_id': user_id,
            'role_type': role_type,
            'connected_at': datetime.utcnow(),
            'last_heartbeat': datetime.utcnow(),
            'subscriptions': set(),
            'status': ConnectionStatus.CONNECTED
        }
        
        self.active_connections[connection_id] = connection_info
        
        # 更新用户连接映射
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # 更新角色连接映射
        if role_type not in self.role_connections:
            self.role_connections[role_type] = set()
        self.role_connections[role_type].add(connection_id)
        
        logger.info(f"WebSocket connection established: {connection_id}")
    
    async def disconnect(self, connection_id: str):
        """断开连接"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            user_id = connection['user_id']
            role_type = connection['role_type']
            
            # 关闭WebSocket连接
            try:
                await connection['websocket'].close()
            except:
                pass
            
            # 清理连接映射
            del self.active_connections[connection_id]
            
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            
            if role_type in self.role_connections:
                self.role_connections[role_type].discard(connection_id)
                if not self.role_connections[role_type]:
                    del self.role_connections[role_type]
            
            logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """发送消息到指定连接"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            try:
                await connection['websocket'].send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {str(e)}")
                await self.disconnect(connection_id)
                return False
        return False
    
    async def broadcast_to_role(self, role_type: str, message: Dict[str, Any]):
        """向指定角色广播消息"""
        if role_type in self.role_connections:
            connection_ids = list(self.role_connections[role_type])
            for connection_id in connection_ids:
                await self.send_message(connection_id, message)
    
    async def broadcast_to_user(self, user_id: int, message: Dict[str, Any]):
        """向指定用户的所有连接广播消息"""
        if user_id in self.user_connections:
            connection_ids = list(self.user_connections[user_id])
            for connection_id in connection_ids:
                await self.send_message(connection_id, message)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """向所有连接广播消息"""
        connection_ids = list(self.active_connections.keys())
        for connection_id in connection_ids:
            await self.send_message(connection_id, message)
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        return self.active_connections.get(connection_id)
    
    def get_user_connections(self, user_id: int) -> List[str]:
        """获取用户的所有连接"""
        return list(self.user_connections.get(user_id, set()))
    
    def get_active_connections_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)

# 全局连接管理器实例
connection_manager = ConnectionManager()

# 依赖注入

def get_realtime_service(db: Session = Depends(get_db)) -> RealtimeService:
    """获取实时服务实例"""
    return RealtimeService(db, connection_manager)

def get_data_service(db: Session = Depends(get_db)) -> DataAggregationService:
    """获取数据聚合服务实例"""
    return DataAggregationService(db)

# WebSocket端点

@router.websocket("/dashboard/{role_type}")
async def websocket_dashboard_endpoint(
    websocket: WebSocket,
    role_type: str,
    token: str = Query(..., description="认证令牌"),
    db: Session = Depends(get_db),
    realtime_service: RealtimeService = Depends(get_realtime_service),
    data_service: DataAggregationService = Depends(get_data_service)
):
    """
    仪表板WebSocket连接端点
    
    - **role_type**: 角色类型
    - **token**: 认证令牌
    """
    connection_id = None
    
    try:
        # 验证token
        user = await verify_websocket_token(token)
        if not user:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # 验证角色权限
        try:
            role_enum = RoleType(role_type)
        except ValueError:
            await websocket.close(code=4002, reason="Invalid role type")
            return
        
        # 生成连接ID
        connection_id = f"{user.id}_{role_type}_{uuid.uuid4().hex[:8]}"
        
        # 建立连接
        await connection_manager.connect(websocket, connection_id, user.id, role_type)
        
        # 发送连接成功消息
        await connection_manager.send_message(connection_id, {
            "type": MessageType.CONNECT.value,
            "data": {
                "connection_id": connection_id,
                "user_id": user.id,
                "role_type": role_type,
                "connected_at": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # 发送初始数据
        try:
            initial_data = await data_service.get_project_overview_data(user.id, role_type)
            await connection_manager.send_message(connection_id, {
                "type": MessageType.DATA_UPDATE.value,
                "data": {
                    "widget_type": "initial_data",
                    "data": initial_data
                },
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error sending initial data: {str(e)}")
        
        # 启动心跳监控
        heartbeat_task = asyncio.create_task(_heartbeat_monitor(connection_id))
        
        # 处理消息循环
        while True:
            try:
                # 接收消息
                message_data = await websocket.receive_json()
                message = WebSocketMessage(**message_data)
                
                # 处理不同类型的消息
                await _handle_websocket_message(
                    connection_id, message, user, realtime_service, data_service
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {str(e)}")
                await connection_manager.send_message(connection_id, {
                    "type": MessageType.ERROR.value,
                    "data": {"error": str(e)},
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        if connection_id:
            await connection_manager.send_message(connection_id, {
                "type": MessageType.ERROR.value,
                "data": {"error": str(e)},
                "timestamp": datetime.utcnow().isoformat()
            })
    
    finally:
        # 清理连接
        if connection_id:
            # 取消心跳任务
            if 'heartbeat_task' in locals():
                heartbeat_task.cancel()
            
            await connection_manager.disconnect(connection_id)

# REST API端点

@router.get("/connections", response_model=List[ConnectionInfo])
@require_dashboard_permission(DashboardPermissionType.WEBSOCKET_VIEW)
async def get_active_connections(
    current_user: User = Depends(get_current_user)
):
    """获取活跃WebSocket连接列表"""
    try:
        connections = []
        
        for connection_id, connection in connection_manager.active_connections.items():
            connections.append(ConnectionInfo(
                connection_id=connection_id,
                user_id=connection['user_id'],
                role_type=connection['role_type'],
                connected_at=connection['connected_at'].isoformat(),
                last_heartbeat=connection['last_heartbeat'].isoformat(),
                subscriptions=list(connection['subscriptions']),
                status=connection['status']
            ))
        
        return connections
        
    except Exception as e:
        logger.error(f"Error getting active connections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取活跃连接失败"
        )

@router.get("/connections/stats")
async def get_connection_stats(
    current_user: User = Depends(get_current_user)
):
    """获取连接统计信息"""
    try:
        total_connections = connection_manager.get_active_connections_count()
        
        # 按角色统计
        role_stats = {}
        for role_type, connection_ids in connection_manager.role_connections.items():
            role_stats[role_type] = len(connection_ids)
        
        # 按用户统计
        user_stats = {}
        for user_id, connection_ids in connection_manager.user_connections.items():
            user_stats[str(user_id)] = len(connection_ids)
        
        return {
            "total_connections": total_connections,
            "role_distribution": role_stats,
            "user_distribution": user_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting connection stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取连接统计失败"
        )

@router.post("/broadcast")
@require_dashboard_permission(DashboardPermissionType.WEBSOCKET_BROADCAST)
async def broadcast_message(
    message: BroadcastMessage,
    current_user: User = Depends(get_current_user)
):
    """广播消息到WebSocket连接"""
    try:
        broadcast_data = {
            "type": MessageType.BROADCAST.value,
            "data": {
                "event_type": message.event_type.value,
                "data": message.data,
                "sender_id": current_user.id
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 根据目标进行广播
        if message.target_users:
            # 广播到指定用户
            for user_id in message.target_users:
                await connection_manager.broadcast_to_user(user_id, broadcast_data)
        elif message.target_roles:
            # 广播到指定角色
            for role_type in message.target_roles:
                await connection_manager.broadcast_to_role(role_type, broadcast_data)
        else:
            # 广播到所有连接
            await connection_manager.broadcast_to_all(broadcast_data)
        
        return {
            "message": "广播消息发送成功",
            "event_type": message.event_type.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error broadcasting message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="广播消息失败"
        )

@router.delete("/connections/{connection_id}")
@require_dashboard_permission(DashboardPermissionType.WEBSOCKET_MANAGE)
async def disconnect_connection(
    connection_id: str,
    current_user: User = Depends(get_current_user)
):
    """强制断开指定连接"""
    try:
        connection_info = connection_manager.get_connection_info(connection_id)
        
        if not connection_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection {connection_id} not found"
            )
        
        await connection_manager.disconnect(connection_id)
        
        return {
            "message": f"Connection {connection_id} disconnected successfully",
            "connection_id": connection_id,
            "disconnected_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting connection {connection_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="断开连接失败"
        )

# 辅助函数

async def _handle_websocket_message(
    connection_id: str,
    message: WebSocketMessage,
    user: User,
    realtime_service: RealtimeService,
    data_service: DataAggregationService
):
    """处理WebSocket消息"""
    try:
        if message.type == MessageType.SUBSCRIBE:
            # 处理订阅请求
            if message.data:
                subscribe_request = SubscribeRequest(**message.data)
                await _handle_subscribe(connection_id, subscribe_request)
        
        elif message.type == MessageType.UNSUBSCRIBE:
            # 处理取消订阅请求
            if message.data:
                events = message.data.get('events', [])
                await _handle_unsubscribe(connection_id, events)
        
        elif message.type == MessageType.HEARTBEAT:
            # 处理心跳消息
            await _handle_heartbeat(connection_id)
        
        elif message.type == MessageType.REQUEST_DATA:
            # 处理数据请求
            if message.data:
                data_request = DataRequest(**message.data)
                await _handle_data_request(connection_id, data_request, user, data_service)
        
        else:
            logger.warning(f"Unknown message type: {message.type}")
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {str(e)}")
        await connection_manager.send_message(connection_id, {
            "type": MessageType.ERROR.value,
            "data": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat()
        })

async def _handle_subscribe(connection_id: str, subscribe_request: SubscribeRequest):
    """处理订阅请求"""
    connection = connection_manager.get_connection_info(connection_id)
    if connection:
        # 添加订阅事件
        for event in subscribe_request.events:
            connection['subscriptions'].add(event.value)
        
        # 发送订阅确认
        await connection_manager.send_message(connection_id, {
            "type": MessageType.SUBSCRIBE.value,
            "data": {
                "subscribed_events": [event.value for event in subscribe_request.events],
                "total_subscriptions": len(connection['subscriptions'])
            },
            "timestamp": datetime.utcnow().isoformat()
        })

async def _handle_unsubscribe(connection_id: str, events: List[str]):
    """处理取消订阅请求"""
    connection = connection_manager.get_connection_info(connection_id)
    if connection:
        # 移除订阅事件
        for event in events:
            connection['subscriptions'].discard(event)
        
        # 发送取消订阅确认
        await connection_manager.send_message(connection_id, {
            "type": MessageType.UNSUBSCRIBE.value,
            "data": {
                "unsubscribed_events": events,
                "remaining_subscriptions": list(connection['subscriptions'])
            },
            "timestamp": datetime.utcnow().isoformat()
        })

async def _handle_heartbeat(connection_id: str):
    """处理心跳消息"""
    connection = connection_manager.get_connection_info(connection_id)
    if connection:
        connection['last_heartbeat'] = datetime.utcnow()
        
        # 发送心跳响应
        await connection_manager.send_message(connection_id, {
            "type": MessageType.HEARTBEAT.value,
            "data": {"status": "alive"},
            "timestamp": datetime.utcnow().isoformat()
        })

async def _handle_data_request(
    connection_id: str,
    data_request: DataRequest,
    user: User,
    data_service: DataAggregationService
):
    """处理数据请求"""
    try:
        # 根据组件类型获取数据
        if data_request.widget_type == "project_overview":
            data = await data_service.get_project_overview_data(user.id, "ADMIN")
        elif data_request.widget_type == "requirement_metrics":
            project_ids = data_request.parameters.get('project_ids', []) if data_request.parameters else []
            data = await data_service.get_requirement_metrics(project_ids)
        elif data_request.widget_type == "test_metrics":
            project_ids = data_request.parameters.get('project_ids', []) if data_request.parameters else []
            data = await data_service.get_test_metrics(project_ids)
        else:
            data = {"message": f"No data available for widget type: {data_request.widget_type}"}
        
        # 发送数据响应
        await connection_manager.send_message(connection_id, {
            "type": MessageType.DATA_UPDATE.value,
            "data": {
                "widget_type": data_request.widget_type,
                "data": data,
                "force_refresh": data_request.force_refresh
            },
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error handling data request: {str(e)}")
        await connection_manager.send_message(connection_id, {
            "type": MessageType.ERROR.value,
            "data": {"error": f"Failed to get data for {data_request.widget_type}"},
            "timestamp": datetime.utcnow().isoformat()
        })

async def _heartbeat_monitor(connection_id: str):
    """心跳监控任务"""
    try:
        while connection_id in connection_manager.active_connections:
            connection = connection_manager.get_connection_info(connection_id)
            if not connection:
                break
            
            # 检查心跳超时
            last_heartbeat = connection['last_heartbeat']
            if datetime.utcnow() - last_heartbeat > timedelta(minutes=5):
                logger.warning(f"Connection {connection_id} heartbeat timeout")
                await connection_manager.disconnect(connection_id)
                break
            
            # 发送心跳检测
            await connection_manager.send_message(connection_id, {
                "type": MessageType.HEARTBEAT.value,
                "data": {"ping": True},
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 等待30秒
            await asyncio.sleep(30)
    
    except asyncio.CancelledError:
        logger.info(f"Heartbeat monitor cancelled for connection {connection_id}")
    except Exception as e:
        logger.error(f"Error in heartbeat monitor for {connection_id}: {str(e)}")
        await connection_manager.disconnect(connection_id)