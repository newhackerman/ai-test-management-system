"""
仪表板WebSocket API接口

集成实时推送、事件管理、心跳检测和多设备同步功能
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.security import HTTPBearer

from ...services.dashboard_realtime_service import (
    get_dashboard_realtime_service,
    DashboardEventType,
    MessagePriority
)
from ...services.dashboard_event_service import (
    get_dashboard_event_service,
    EventFilter,
    EventCategory,
    EventScope
)
from ...services.dashboard_heartbeat_service import (
    get_dashboard_heartbeat_service,
    ConnectionQuality
)
from ...services.dashboard_push_optimization_service import (
    get_dashboard_push_optimization_service,
    PushStrategy,
    CompressionType,
    FlowControlMode
)
from ...services.dashboard_multidevice_service import (
    get_dashboard_multidevice_service,
    DeviceType
)
from ...services.auth import get_current_user_from_token
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard/ws", tags=["仪表板WebSocket"])
security = HTTPBearer()


async def verify_websocket_token(token: str) -> Optional[User]:
    """验证WebSocket令牌"""
    try:
        user = await get_current_user_from_token(token)
        return user
    except Exception as e:
        logger.error(f"WebSocket token verification failed: {e}")
        return None


@router.websocket("/realtime/{role_type}")
async def dashboard_websocket_endpoint(
    websocket: WebSocket,
    role_type: str,
    token: str = Query(..., description="认证令牌"),
    device_id: Optional[str] = Query(None, description="设备ID"),
    device_type: str = Query("WEB", description="设备类型"),
    device_name: Optional[str] = Query(None, description="设备名称"),
    compression: bool = Query(True, description="是否启用压缩"),
    push_strategy: str = Query("ADAPTIVE", description="推送策略")
):
    """
    仪表板实时WebSocket连接
    
    Args:
        websocket: WebSocket连接
        role_type: 用户角色类型
        token: 认证令牌
        device_id: 设备ID
        device_type: 设备类型
        device_name: 设备名称
        compression: 是否启用压缩
        push_strategy: 推送策略
    """
    # 验证用户身份
    user = await verify_websocket_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # 获取服务实例
    realtime_service = get_dashboard_realtime_service()
    event_service = get_dashboard_event_service()
    heartbeat_service = get_dashboard_heartbeat_service()
    push_service = get_dashboard_push_optimization_service()
    multidevice_service = get_dashboard_multidevice_service()
    
    connection_id = None
    registered_device_id = None
    
    try:
        # 建立实时连接
        connection_id = await realtime_service.connect_user(
            websocket=websocket,
            user_id=user.id,
            role_type=role_type,
            client_type=_parse_device_type(device_type),
            client_info={
                'device_id': device_id,
                'device_name': device_name,
                'device_type': device_type,
                'user_agent': websocket.headers.get('user-agent', ''),
                'ip_address': websocket.client.host if websocket.client else None
            }
        )
        
        # 注册设备
        registered_device_id = await multidevice_service.register_device(
            user_id=user.id,
            connection_id=connection_id,
            device_info={
                'device_id': device_id,
                'device_type': device_type,
                'device_name': device_name or f"{device_type} Device",
                'platform': websocket.headers.get('user-agent', 'Unknown')
            }
        )
        
        # 注册心跳监控
        heartbeat_service.register_connection(connection_id)
        
        # 配置推送优化
        push_service.configure_connection(
            connection_id=connection_id,
            push_strategy=_parse_push_strategy(push_strategy),
            compression_type=CompressionType.GZIP if compression else CompressionType.NONE,
            flow_control_mode=FlowControlMode.ADAPTIVE_RATE,
            max_rate=50.0,
            enable_incremental=True
        )
        
        # 设置回调函数
        await _setup_connection_callbacks(
            connection_id,
            registered_device_id,
            user.id,
            role_type,
            realtime_service,
            event_service,
            heartbeat_service,
            multidevice_service
        )
        
        # 订阅默认事件
        await _subscribe_default_events(connection_id, role_type, realtime_service)
        
        logger.info(f"Dashboard WebSocket connected: {connection_id} for user {user.id}")
        
        # 消息处理循环
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                await _handle_websocket_message(
                    connection_id,
                    registered_device_id,
                    user.id,
                    role_type,
                    data,
                    realtime_service,
                    event_service,
                    heartbeat_service,
                    push_service,
                    multidevice_service
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await _send_error_message(websocket, str(e))
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=4000, reason=str(e))
        except:
            pass
    
    finally:
        # 清理连接
        if connection_id:
            await realtime_service.disconnect_user(connection_id, "Connection closed")
            heartbeat_service.unregister_connection(connection_id)
            push_service.remove_connection(connection_id)
        
        if registered_device_id:
            await multidevice_service.unregister_device(registered_device_id)


async def _handle_websocket_message(
    connection_id: str,
    device_id: str,
    user_id: int,
    role_type: str,
    message_data: str,
    realtime_service,
    event_service,
    heartbeat_service,
    push_service,
    multidevice_service
):
    """
    处理WebSocket消息
    
    Args:
        connection_id: 连接ID
        device_id: 设备ID
        user_id: 用户ID
        role_type: 角色类型
        message_data: 消息数据
        realtime_service: 实时服务
        event_service: 事件服务
        heartbeat_service: 心跳服务
        push_service: 推送服务
        multidevice_service: 多设备服务
    """
    try:
        message = json.loads(message_data)
        message_type = message.get('type')
        data = message.get('data', {})
        
        if message_type == 'heartbeat':
            await _handle_heartbeat(connection_id, message, heartbeat_service)
        
        elif message_type == 'subscribe_events':
            await _handle_subscribe_events(connection_id, data, realtime_service)
        
        elif message_type == 'unsubscribe_events':
            await _handle_unsubscribe_events(connection_id, data, realtime_service)
        
        elif message_type == 'subscribe_projects':
            await _handle_subscribe_projects(connection_id, data, realtime_service)
        
        elif message_type == 'request_data':
            await _handle_data_request(connection_id, user_id, role_type, data, push_service)
        
        elif message_type == 'sync_state':
            await _handle_sync_state(user_id, device_id, data, multidevice_service)
        
        elif message_type == 'get_device_list':
            await _handle_get_device_list(connection_id, user_id, multidevice_service, realtime_service)
        
        elif message_type == 'set_primary_device':
            await _handle_set_primary_device(user_id, data, multidevice_service)
        
        elif message_type == 'resolve_conflict':
            await _handle_resolve_conflict(data, multidevice_service)
        
        elif message_type == 'publish_event':
            await _handle_publish_event(user_id, data, event_service)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON message received")
    except Exception as e:
        logger.error(f"Error processing message: {e}")


async def _handle_heartbeat(connection_id: str, message: Dict[str, Any], heartbeat_service):
    """处理心跳消息"""
    heartbeat_id = message.get('data', {}).get('heartbeat_id')
    if heartbeat_id:
        await heartbeat_service.receive_heartbeat_response(connection_id, heartbeat_id)


async def _handle_subscribe_events(connection_id: str, data: Dict[str, Any], realtime_service):
    """处理事件订阅"""
    event_types_str = data.get('event_types', [])
    event_types = []
    
    for event_type_str in event_types_str:
        try:
            event_type = DashboardEventType(event_type_str)
            event_types.append(event_type)
        except ValueError:
            logger.warning(f"Invalid event type: {event_type_str}")
    
    if event_types:
        await realtime_service.subscribe_to_events(connection_id, event_types)


async def _handle_unsubscribe_events(connection_id: str, data: Dict[str, Any], realtime_service):
    """处理取消事件订阅"""
    event_types_str = data.get('event_types', [])
    event_types = []
    
    for event_type_str in event_types_str:
        try:
            event_type = DashboardEventType(event_type_str)
            event_types.append(event_type)
        except ValueError:
            logger.warning(f"Invalid event type: {event_type_str}")
    
    if event_types:
        await realtime_service.unsubscribe_from_events(connection_id, event_types)


async def _handle_subscribe_projects(connection_id: str, data: Dict[str, Any], realtime_service):
    """处理项目订阅"""
    project_ids = data.get('project_ids', [])
    if project_ids:
        await realtime_service.subscribe_to_projects(connection_id, project_ids)


async def _handle_data_request(
    connection_id: str,
    user_id: int,
    role_type: str,
    data: Dict[str, Any],
    push_service
):
    """处理数据请求"""
    data_type = data.get('data_type')
    widget_type = data.get('widget_type')
    
    if data_type and widget_type:
        # 模拟获取数据 (实际实现中会调用数据聚合服务)
        mock_data = {
            'widget_type': widget_type,
            'data': {'value': 100, 'trend': 'up'},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await push_service.push_data(
            connection_id=connection_id,
            data_type=data_type,
            data_content=mock_data,
            priority=2
        )


async def _handle_sync_state(
    user_id: int,
    device_id: str,
    data: Dict[str, Any],
    multidevice_service
):
    """处理状态同步"""
    data_type = data.get('data_type')
    data_content = data.get('data_content')
    force_sync = data.get('force_sync', False)
    
    if data_type and data_content is not None:
        await multidevice_service.sync_state(
            user_id=user_id,
            device_id=device_id,
            data_type=data_type,
            data_content=data_content,
            force_sync=force_sync
        )


async def _handle_get_device_list(
    connection_id: str,
    user_id: int,
    multidevice_service,
    realtime_service
):
    """处理获取设备列表"""
    devices = await multidevice_service.get_device_list(user_id)
    
    # 发送设备列表
    message = {
        'type': 'device_list',
        'data': {'devices': devices},
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # 这里应该通过realtime_service发送消息
    logger.debug(f"Sending device list to {connection_id}: {len(devices)} devices")


async def _handle_set_primary_device(
    user_id: int,
    data: Dict[str, Any],
    multidevice_service
):
    """处理设置主设备"""
    device_id = data.get('device_id')
    if device_id:
        await multidevice_service.set_primary_device(user_id, device_id)


async def _handle_resolve_conflict(data: Dict[str, Any], multidevice_service):
    """处理解决冲突"""
    conflict_id = data.get('conflict_id')
    chosen_state_index = data.get('chosen_state_index')
    
    if conflict_id is not None and chosen_state_index is not None:
        await multidevice_service.resolve_conflict_manually(conflict_id, chosen_state_index)


async def _handle_publish_event(user_id: int, data: Dict[str, Any], event_service):
    """处理发布事件"""
    event_type_str = data.get('event_type')
    event_data = data.get('event_data', {})
    
    if event_type_str:
        try:
            event_type = DashboardEventType(event_type_str)
            
            # 创建事件 (这里简化处理，实际应该根据事件类型创建相应的事件)
            from ...services.dashboard_event_service import DashboardEvent
            
            event = DashboardEvent(
                event_type=event_type,
                category=EventCategory.USER,
                scope=EventScope.USER,
                data=event_data,
                source_user_id=user_id
            )
            
            await event_service.publish_event(event)
            
        except ValueError:
            logger.warning(f"Invalid event type: {event_type_str}")


async def _setup_connection_callbacks(
    connection_id: str,
    device_id: str,
    user_id: int,
    role_type: str,
    realtime_service,
    event_service,
    heartbeat_service,
    multidevice_service
):
    """设置连接回调函数"""
    
    # 心跳回调
    def heartbeat_callback(conn_id: str, latency: float):
        logger.debug(f"Heartbeat received from {conn_id}, latency: {latency}ms")
    
    # 超时回调
    async def timeout_callback(conn_id: str):
        logger.warning(f"Connection timeout: {conn_id}")
        await realtime_service.disconnect_user(conn_id, "Heartbeat timeout")
    
    # 质量变化回调
    def quality_change_callback(conn_id: str, old_quality: ConnectionQuality, new_quality: ConnectionQuality):
        logger.info(f"Connection quality changed for {conn_id}: {old_quality.value} -> {new_quality.value}")
    
    # 重连回调
    async def reconnection_callback(conn_id: str):
        logger.info(f"Attempting reconnection for {conn_id}")
        # 这里可以实现重连逻辑
    
    # 注册回调
    heartbeat_service.register_heartbeat_callback(connection_id, heartbeat_callback)
    heartbeat_service.register_timeout_callback(connection_id, timeout_callback)
    heartbeat_service.register_quality_change_callback(connection_id, quality_change_callback)
    heartbeat_service.register_reconnection_callback(connection_id, reconnection_callback)


async def _subscribe_default_events(connection_id: str, role_type: str, realtime_service):
    """订阅默认事件"""
    default_events = [
        DashboardEventType.DASHBOARD_DATA_UPDATE,
        DashboardEventType.WIDGET_DATA_UPDATE,
        DashboardEventType.SYSTEM_ALERT,
        DashboardEventType.CONNECTION_STATUS,
        DashboardEventType.HEARTBEAT
    ]
    
    # 根据角色添加特定事件
    if role_type in ['ADMIN', 'PROJECT_MANAGER']:
        default_events.extend([
            DashboardEventType.USER_ACTIVITY,
            DashboardEventType.PERFORMANCE_METRICS
        ])
    
    await realtime_service.subscribe_to_events(connection_id, default_events)


async def _send_error_message(websocket: WebSocket, error_message: str):
    """发送错误消息"""
    try:
        error_msg = {
            'type': 'error',
            'data': {'error': error_message},
            'timestamp': datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_msg))
    except Exception:
        pass  # 连接可能已经关闭


def _parse_device_type(device_type_str: str) -> DeviceType:
    """解析设备类型"""
    try:
        return DeviceType(device_type_str.upper())
    except ValueError:
        return DeviceType.WEB


def _parse_push_strategy(strategy_str: str) -> PushStrategy:
    """解析推送策略"""
    try:
        return PushStrategy(strategy_str.upper())
    except ValueError:
        return PushStrategy.ADAPTIVE


# 统计信息接口
@router.get("/stats")
async def get_websocket_stats(
    current_user: User = Depends(get_current_user_from_token)
):
    """
    获取WebSocket统计信息
    
    Returns:
        Dict[str, Any]: 统计信息
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    realtime_service = get_dashboard_realtime_service()
    event_service = get_dashboard_event_service()
    heartbeat_service = get_dashboard_heartbeat_service()
    push_service = get_dashboard_push_optimization_service()
    multidevice_service = get_dashboard_multidevice_service()
    
    return {
        'realtime': realtime_service.get_connection_stats(),
        'events': event_service.get_stats(),
        'heartbeat': heartbeat_service.get_stats(),
        'push_optimization': push_service.get_stats(),
        'multidevice': multidevice_service.get_stats(),
        'timestamp': datetime.utcnow().isoformat()
    }


@router.get("/connections")
async def get_active_connections(
    current_user: User = Depends(get_current_user_from_token)
):
    """
    获取活跃连接信息
    
    Returns:
        Dict[str, Any]: 连接信息
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    realtime_service = get_dashboard_realtime_service()
    heartbeat_service = get_dashboard_heartbeat_service()
    
    return {
        'active_connections': len(realtime_service.active_connections),
        'connection_summary': heartbeat_service.get_connection_summary(),
        'connection_metrics': heartbeat_service.get_all_connection_metrics(),
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/broadcast")
async def broadcast_message(
    message_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_from_token)
):
    """
    广播消息到所有连接
    
    Args:
        message_data: 消息数据
        
    Returns:
        Dict[str, Any]: 广播结果
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    realtime_service = get_dashboard_realtime_service()
    
    # 创建广播消息
    from ...services.dashboard_realtime_service import RealtimeMessage
    
    message = RealtimeMessage(
        event_type=DashboardEventType.SYSTEM_ALERT,
        data=message_data,
        priority=MessagePriority.HIGH
    )
    
    # 广播消息
    sent_count = await realtime_service.broadcast_message(message)
    
    return {
        'message': 'Message broadcasted successfully',
        'sent_to_connections': sent_count,
        'timestamp': datetime.utcnow().isoformat()
    }