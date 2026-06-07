"""
AI助手WebSocket API端点

提供AI助手专用的WebSocket连接端点，包括：
1. AI对话的实时WebSocket连接
2. 流式AI响应接收
3. 实时状态同步
4. 连接管理和监控
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ...core.fastapi_integration import Inject
from ...services.ai_websocket_manager import (
    ai_websocket_manager, 
    WebSocketMessage, 
    MessageType,
    AIMessageType
)
from ...services.ai_assistant_service import AIAssistantService
from ...services.conversation_service import ConversationService
from ...core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# 请求/响应模型
class WebSocketConnectionRequest(BaseModel):
    """WebSocket连接请求"""
    conversation_id: Optional[int] = Field(None, description="要订阅的对话ID")
    auto_subscribe: bool = Field(True, description="是否自动订阅对话")
    metadata: Optional[Dict[str, Any]] = Field(None, description="连接元数据")


class WebSocketStatsResponse(BaseModel):
    """WebSocket统计响应"""
    success: bool = Field(..., description="是否成功")
    stats: Dict[str, Any] = Field(..., description="统计信息")
    timestamp: str = Field(..., description="时间戳")


class UserConnectionsResponse(BaseModel):
    """用户连接响应"""
    success: bool = Field(..., description="是否成功")
    user_id: int = Field(..., description="用户ID")
    connections: list = Field(..., description="连接列表")
    total_connections: int = Field(..., description="连接总数")


class ConversationSubscribersResponse(BaseModel):
    """对话订阅者响应"""
    success: bool = Field(..., description="是否成功")
    conversation_id: int = Field(..., description="对话ID")
    subscribers: list = Field(..., description="订阅者列表")
    total_subscribers: int = Field(..., description="订阅者总数")


@router.websocket("/ws/ai-assistant")
async def ai_assistant_websocket(
    websocket: WebSocket,
    conversation_id: Optional[int] = Query(None, description="要订阅的对话ID"),
    auto_subscribe: bool = Query(True, description="是否自动订阅对话")
):
    """
    AI助手WebSocket连接端点
    
    提供AI助手的实时WebSocket连接，支持：
    1. 实时AI响应接收
    2. 对话状态同步
    3. 输入状态指示
    4. 连接状态管理
    
    连接参数：
    - conversation_id: 可选，要自动订阅的对话ID
    - auto_subscribe: 是否自动订阅指定的对话
    
    WebSocket消息格式：
    {
        "type": "message_type",
        "data": {...},
        "conversation_id": 123,
        "message_id": "uuid",
        "timestamp": "2024-01-01T00:00:00Z"
    }
    """
    # TODO: 从WebSocket连接中获取用户认证信息
    # 这里简化处理，实际应该从JWT token或session中获取
    user_id = 1
    
    connection_id = None
    
    try:
        logger.info(f"AI Assistant WebSocket connection attempt for user {user_id}")
        
        # 建立WebSocket连接
        connection_metadata = {
            "conversation_id": conversation_id,
            "auto_subscribe": auto_subscribe,
            "user_agent": websocket.headers.get("user-agent"),
            "client_ip": websocket.client.host if websocket.client else None
        }
        
        connection_id = await ai_websocket_manager.connect_user(
            websocket=websocket,
            user_id=user_id,
            metadata=connection_metadata
        )
        
        # 自动订阅对话（如果指定）
        if auto_subscribe and conversation_id:
            await ai_websocket_manager.subscribe_to_conversation(user_id, conversation_id)
        
        logger.info(f"AI Assistant WebSocket connected: user={user_id}, connection={connection_id}")
        
        # 消息处理循环
        while True:
            try:
                # 接收客户端消息
                message_text = await websocket.receive_text()
                
                try:
                    message_data = json.loads(message_text)
                    await ai_websocket_manager.handle_user_message(connection_id, message_data)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message from connection {connection_id}: {message_text}")
                    await _send_error_to_connection(websocket, "Invalid JSON format")
                    
                except Exception as e:
                    logger.error(f"Error handling message from connection {connection_id}: {e}")
                    await _send_error_to_connection(websocket, str(e))
                    
            except WebSocketDisconnect:
                logger.info(f"AI Assistant WebSocket disconnected: user={user_id}, connection={connection_id}")
                break
                
            except Exception as e:
                logger.error(f"Error in WebSocket message loop for connection {connection_id}: {e}")
                break
    
    except Exception as e:
        logger.error(f"Error in AI Assistant WebSocket connection: {e}")
        
    finally:
        # 清理连接
        if connection_id:
            await ai_websocket_manager.disconnect_user(connection_id)


@router.websocket("/ws/ai-assistant/{conversation_id}")
async def ai_conversation_websocket(
    websocket: WebSocket,
    conversation_id: int
):
    """
    AI对话专用WebSocket连接端点
    
    为特定对话提供专用的WebSocket连接，自动订阅指定对话。
    适合单对话页面使用。
    """
    # TODO: 从WebSocket连接中获取用户认证信息
    user_id = 1
    
    connection_id = None
    
    try:
        logger.info(f"AI Conversation WebSocket connection for conversation {conversation_id}, user {user_id}")
        
        # 验证对话存在和权限
        # 这里应该添加对话存在性和权限检查
        
        # 建立WebSocket连接
        connection_metadata = {
            "conversation_id": conversation_id,
            "connection_type": "conversation_specific",
            "user_agent": websocket.headers.get("user-agent"),
            "client_ip": websocket.client.host if websocket.client else None
        }
        
        connection_id = await ai_websocket_manager.connect_user(
            websocket=websocket,
            user_id=user_id,
            metadata=connection_metadata
        )
        
        # 自动订阅对话
        await ai_websocket_manager.subscribe_to_conversation(user_id, conversation_id)
        
        logger.info(f"AI Conversation WebSocket connected: conversation={conversation_id}, user={user_id}, connection={connection_id}")
        
        # 消息处理循环
        while True:
            try:
                message_text = await websocket.receive_text()
                
                try:
                    message_data = json.loads(message_text)
                    # 自动设置conversation_id
                    message_data["conversation_id"] = conversation_id
                    
                    await ai_websocket_manager.handle_user_message(connection_id, message_data)
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message from connection {connection_id}")
                    await _send_error_to_connection(websocket, "Invalid JSON format")
                    
                except Exception as e:
                    logger.error(f"Error handling conversation message: {e}")
                    await _send_error_to_connection(websocket, str(e))
                    
            except WebSocketDisconnect:
                logger.info(f"AI Conversation WebSocket disconnected: conversation={conversation_id}")
                break
                
            except Exception as e:
                logger.error(f"Error in conversation WebSocket loop: {e}")
                break
    
    except Exception as e:
        logger.error(f"Error in AI Conversation WebSocket: {e}")
        
    finally:
        if connection_id:
            await ai_websocket_manager.disconnect_user(connection_id)


async def _send_error_to_connection(websocket: WebSocket, error_message: str):
    """向WebSocket连接发送错误消息"""
    try:
        error_msg = WebSocketMessage(
            type=MessageType.ERROR,
            data={
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        await websocket.send_text(error_msg.to_json())
        
    except Exception as e:
        logger.error(f"Failed to send error message to WebSocket: {e}")


@router.get("/ws/stats", response_model=WebSocketStatsResponse, summary="获取WebSocket统计信息")
async def get_websocket_stats():
    """
    获取WebSocket连接统计信息
    
    返回当前WebSocket连接的统计数据，包括：
    - 活跃用户数
    - 活跃连接数
    - 活跃对话数
    - 消息统计
    - 离线消息队列统计
    """
    try:
        stats = ai_websocket_manager.get_stats()
        
        response = WebSocketStatsResponse(
            success=True,
            stats=stats,
            timestamp=datetime.utcnow().isoformat()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取WebSocket统计信息失败: {str(e)}"
        )


@router.get("/ws/users/{user_id}/connections", response_model=UserConnectionsResponse, summary="获取用户连接信息")
async def get_user_connections(user_id: int):
    """
    获取指定用户的WebSocket连接信息
    
    返回用户当前的所有WebSocket连接详情。
    """
    try:
        connections = ai_websocket_manager.get_user_connections(user_id)
        
        response = UserConnectionsResponse(
            success=True,
            user_id=user_id,
            connections=connections,
            total_connections=len(connections)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting user connections for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户连接信息失败: {str(e)}"
        )


@router.get("/ws/conversations/{conversation_id}/subscribers", response_model=ConversationSubscribersResponse, summary="获取对话订阅者")
async def get_conversation_subscribers(conversation_id: int):
    """
    获取指定对话的订阅者列表
    
    返回当前订阅该对话的所有用户ID。
    """
    try:
        subscribers = ai_websocket_manager.get_conversation_subscribers(conversation_id)
        
        response = ConversationSubscribersResponse(
            success=True,
            conversation_id=conversation_id,
            subscribers=subscribers,
            total_subscribers=len(subscribers)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting conversation subscribers for conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话订阅者失败: {str(e)}"
        )


@router.post("/ws/conversations/{conversation_id}/notify", summary="向对话发送通知")
async def notify_conversation(
    conversation_id: int,
    message_type: str,
    data: Dict[str, Any]
):
    """
    向指定对话的所有订阅者发送通知
    
    用于系统或管理员向对话发送通知消息。
    """
    try:
        # 验证消息类型
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的消息类型: {message_type}"
            )
        
        # 创建通知消息
        notification = WebSocketMessage(
            type=msg_type,
            conversation_id=conversation_id,
            data=data
        )
        
        # 发送通知
        await ai_websocket_manager.send_to_conversation(conversation_id, notification)
        
        return {
            "success": True,
            "message": f"通知已发送到对话 {conversation_id}",
            "conversation_id": conversation_id,
            "message_type": message_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification to conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送通知失败: {str(e)}"
        )


@router.post("/ws/users/{user_id}/notify", summary="向用户发送通知")
async def notify_user(
    user_id: int,
    message_type: str,
    data: Dict[str, Any],
    conversation_id: Optional[int] = None
):
    """
    向指定用户发送通知
    
    用于系统或管理员向用户发送通知消息。
    """
    try:
        # 验证消息类型
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的消息类型: {message_type}"
            )
        
        # 创建通知消息
        notification = WebSocketMessage(
            type=msg_type,
            conversation_id=conversation_id,
            data=data
        )
        
        # 发送通知
        await ai_websocket_manager.send_to_user(user_id, notification)
        
        return {
            "success": True,
            "message": f"通知已发送到用户 {user_id}",
            "user_id": user_id,
            "message_type": message_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送通知失败: {str(e)}"
        )


@router.post("/ws/broadcast", summary="广播通知")
async def broadcast_notification(
    message_type: str,
    data: Dict[str, Any]
):
    """
    向所有连接的用户广播通知
    
    用于系统维护通知、重要公告等场景。
    """
    try:
        # 验证消息类型
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的消息类型: {message_type}"
            )
        
        # 创建广播消息
        broadcast_msg = WebSocketMessage(
            type=msg_type,
            data=data
        )
        
        # 广播消息
        await ai_websocket_manager.broadcast_to_all(broadcast_msg)
        
        stats = ai_websocket_manager.get_stats()
        
        return {
            "success": True,
            "message": "广播通知已发送",
            "message_type": message_type,
            "recipients": stats.get("active_users", 0),
            "total_connections": stats.get("active_connections", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error broadcasting notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"广播通知失败: {str(e)}"
        )


@router.delete("/ws/users/{user_id}/connections/{connection_id}", summary="断开用户连接")
async def disconnect_user_connection(user_id: int, connection_id: str):
    """
    断开指定用户的WebSocket连接
    
    用于管理员强制断开用户连接。
    """
    try:
        # 验证连接存在
        connections = ai_websocket_manager.get_user_connections(user_id)
        connection_exists = any(conn["connection_id"] == connection_id for conn in connections)
        
        if not connection_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="连接不存在"
            )
        
        # 断开连接
        await ai_websocket_manager.disconnect_user(connection_id)
        
        return {
            "success": True,
            "message": f"连接 {connection_id} 已断开",
            "user_id": user_id,
            "connection_id": connection_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting user connection {connection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"断开连接失败: {str(e)}"
        )


# 初始化WebSocket管理器
@router.on_event("startup")
async def startup_websocket_manager():
    """启动时初始化WebSocket管理器"""
    await ai_websocket_manager.initialize()


@router.on_event("shutdown")
async def shutdown_websocket_manager():
    """关闭时清理WebSocket管理器"""
    await ai_websocket_manager.close()


# 辅助函数：集成AI助手服务
async def integrate_with_ai_assistant():
    """集成AI助手服务的WebSocket功能"""
    
    async def on_ai_response_chunk(data: Dict[str, Any]):
        """AI响应数据块事件处理"""
        conversation_id = data.get("conversation_id")
        if conversation_id:
            from ...services.ai_websocket_manager import send_ai_response_chunk
            await send_ai_response_chunk(conversation_id, data)
    
    async def on_ai_response_complete(data: Dict[str, Any]):
        """AI响应完成事件处理"""
        conversation_id = data.get("conversation_id")
        if conversation_id:
            from ...services.ai_websocket_manager import send_ai_response_complete
            await send_ai_response_complete(conversation_id, data)
    
    async def on_ai_response_error(data: Dict[str, Any]):
        """AI响应错误事件处理"""
        conversation_id = data.get("conversation_id")
        error_message = data.get("error", "Unknown error")
        if conversation_id:
            from ...services.ai_websocket_manager import send_ai_response_error
            await send_ai_response_error(conversation_id, error_message)
    
    # 注册事件处理器
    ai_websocket_manager.add_event_handler("ai_response_chunk", on_ai_response_chunk)
    ai_websocket_manager.add_event_handler("ai_response_complete", on_ai_response_complete)
    ai_websocket_manager.add_event_handler("ai_response_error", on_ai_response_error)


# 在启动时集成AI助手服务
@router.on_event("startup")
async def startup_ai_integration():
    """启动时集成AI助手服务"""
    await integrate_with_ai_assistant()