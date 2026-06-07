"""
WebSocket实时推送API
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Dict, Any
import json
import logging

from ....core.security import verify_token
from ....services.realtime_service import RealtimeService, get_realtime_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/{role_type}")
async def websocket_endpoint(
    websocket: WebSocket,
    role_type: str,
    token: str = Query(...),
    realtime_service: RealtimeService = Depends(get_realtime_service)
):
    """WebSocket实时数据推送"""
    connection_id = None
    
    try:
        # 1. 验证token
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        user_id = int(payload.get("sub"))
        if not user_id:
            await websocket.close(code=4001, reason="Invalid user")
            return
        
        # 2. 建立连接
        connection_id = await realtime_service.connect_user(
            websocket, user_id, role_type.upper()
        )
        
        logger.info(f"WebSocket连接建立: user_id={user_id}, role={role_type}, connection_id={connection_id}")
        
        # 3. 处理消息
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get('type')
                
                if message_type == 'subscribe':
                    # 订阅事件
                    event_types = message.get('events', [])
                    await realtime_service.subscribe_to_events(connection_id, event_types)
                    
                    await websocket.send_json({
                        'type': 'subscription_confirmed',
                        'events': event_types,
                        'timestamp': realtime_service.get_current_timestamp()
                    })
                
                elif message_type == 'unsubscribe':
                    # 取消订阅
                    event_types = message.get('events', [])
                    await realtime_service.unsubscribe_from_events(connection_id, event_types)
                    
                    await websocket.send_json({
                        'type': 'unsubscription_confirmed',
                        'events': event_types,
                        'timestamp': realtime_service.get_current_timestamp()
                    })
                
                elif message_type == 'heartbeat':
                    # 心跳响应
                    await realtime_service.update_heartbeat(connection_id)
                    
                    await websocket.send_json({
                        'type': 'heartbeat_ack',
                        'timestamp': realtime_service.get_current_timestamp()
                    })
                
                elif message_type == 'request_data':
                    # 请求特定数据
                    widget_type = message.get('widget_type')
                    if widget_type:
                        widget_data = await realtime_service.get_widget_data(
                            connection_id, widget_type
                        )
                        await realtime_service.send_data_update(
                            connection_id, widget_type, widget_data
                        )
                
                else:
                    logger.warning(f"未知消息类型: {message_type}")
            
            except WebSocketDisconnect:
                logger.info(f"WebSocket连接断开: connection_id={connection_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    'type': 'error',
                    'message': '无效的JSON格式'
                })
            except Exception as e:
                logger.error(f"处理WebSocket消息失败: {e}")
                await websocket.send_json({
                    'type': 'error',
                    'message': str(e)
                })
    
    except Exception as e:
        logger.error(f"WebSocket连接失败: {e}")
        try:
            await websocket.close(code=4000, reason=str(e))
        except:
            pass
    
    finally:
        # 清理连接
        if connection_id:
            try:
                await realtime_service.disconnect_user(connection_id)
                logger.info(f"WebSocket连接清理完成: connection_id={connection_id}")
            except Exception as e:
                logger.error(f"清理WebSocket连接失败: {e}")

@router.get("/connections/status")
async def get_connection_status(
    realtime_service: RealtimeService = Depends(get_realtime_service)
):
    """获取连接状态"""
    try:
        status = await realtime_service.get_connection_status()
        return {
            "total_connections": status.get("total_connections", 0),
            "active_connections": status.get("active_connections", 0),
            "connections_by_role": status.get("connections_by_role", {}),
            "timestamp": realtime_service.get_current_timestamp()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取连接状态失败: {str(e)}")