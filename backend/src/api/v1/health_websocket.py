"""
健康监控WebSocket API - 实时健康状态推送
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...decorators.permission import get_current_user_from_token
from ...services.simple_health_check_service import EnhancedHealthCheckService

router = APIRouter()
logger = logging.getLogger(__name__)

# WebSocket连接管理
class HealthWebSocketManager:
    """健康监控WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃的WebSocket连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 存储用户订阅的配置ID
        self.user_subscriptions: Dict[str, Set[int]] = {}
        # 健康检查服务实例
        self.health_service: Optional[EnhancedHealthCheckService] = None
        
    async def connect(self, websocket: WebSocket, user_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_subscriptions[user_id] = set()
        logger.info(f"Health monitoring WebSocket connected for user {user_id}")
        
    def disconnect(self, user_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_subscriptions:
            del self.user_subscriptions[user_id]
        logger.info(f"Health monitoring WebSocket disconnected for user {user_id}")
        
    async def send_personal_message(self, message: dict, user_id: str):
        """发送个人消息"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {str(e)}")
                # 连接可能已断开，清理连接
                self.disconnect(user_id)
                
    async def broadcast_health_update(self, config_id: int, health_data: dict):
        """广播健康状态更新"""
        message = {
            "type": "health_update",
            "config_id": config_id,
            "data": health_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 发送给订阅了该配置的用户
        disconnected_users = []
        for user_id, subscriptions in self.user_subscriptions.items():
            if config_id in subscriptions:
                try:
                    await self.send_personal_message(message, user_id)
                except Exception as e:
                    logger.error(f"Failed to send health update to user {user_id}: {str(e)}")
                    disconnected_users.append(user_id)
        
        # 清理断开的连接
        for user_id in disconnected_users:
            self.disconnect(user_id)
    
    async def initialize_health_service(self, db: AsyncSession):
        """初始化健康检查服务"""
        if not self.health_service:
            self.health_service = EnhancedHealthCheckService(db)
    
    async def start_health_monitoring(self, config_id: int, user_id: str):
        """开始监控指定配置的健康状态"""
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].add(config_id)
            logger.info(f"User {user_id} subscribed to health monitoring for config {config_id}")
    
    async def stop_health_monitoring(self, config_id: int, user_id: str):
        """停止监控指定配置的健康状态"""
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(config_id)
            logger.info(f"User {user_id} unsubscribed from health monitoring for config {config_id}")

# 全局WebSocket管理器实例
health_ws_manager = HealthWebSocketManager()

@router.websocket("/health-monitor")
async def health_monitor_websocket(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """健康监控WebSocket端点"""
    try:
        # 验证用户身份
        current_user = await get_current_user_from_token(token, db)
        if not current_user:
            await websocket.close(code=4001, reason="Unauthorized")
            return
        
        user_id = str(current_user.id)
        
        # 初始化健康检查服务
        await health_ws_manager.initialize_health_service(db)
        
        # 建立WebSocket连接
        await health_ws_manager.connect(websocket, user_id)
        
        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "subscribe":
                    # 订阅健康监控
                    config_id = message.get("config_id")
                    if config_id:
                        await health_ws_manager.start_health_monitoring(config_id, user_id)
                        
                        # 发送当前健康状态
                        if health_ws_manager.health_service:
                            health_status = await health_ws_manager.health_service.check_ai_service_health(config_id)
                            await health_ws_manager.send_personal_message({
                                "type": "health_status",
                                "config_id": config_id,
                                "data": health_status,
                                "timestamp": datetime.utcnow().isoformat()
                            }, user_id)
                
                elif message_type == "unsubscribe":
                    # 取消订阅
                    config_id = message.get("config_id")
                    if config_id:
                        await health_ws_manager.stop_health_monitoring(config_id, user_id)
                
                elif message_type == "ping":
                    # 心跳检测
                    await health_ws_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }, user_id)
                
                elif message_type == "get_all_status":
                    # 获取所有订阅配置的健康状态
                    if user_id in health_ws_manager.user_subscriptions:
                        subscriptions = health_ws_manager.user_subscriptions[user_id]
                        for config_id in subscriptions:
                            if health_ws_manager.health_service:
                                health_status = await health_ws_manager.health_service.check_ai_service_health(config_id)
                                await health_ws_manager.send_personal_message({
                                    "type": "health_status",
                                    "config_id": config_id,
                                    "data": health_status,
                                    "timestamp": datetime.utcnow().isoformat()
                                }, user_id)
                
        except WebSocketDisconnect:
            logger.info(f"Health monitoring WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"Error in health monitoring WebSocket for user {user_id}: {str(e)}")
            await websocket.close(code=1011, reason="Internal server error")
        finally:
            health_ws_manager.disconnect(user_id)
            
    except Exception as e:
        logger.error(f"Failed to establish health monitoring WebSocket connection: {str(e)}")
        await websocket.close(code=1011, reason="Connection failed")

@router.post("/health-check/{config_id}")
async def trigger_health_check(
    config_id: int,
    current_user = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
):
    """手动触发健康检查"""
    try:
        # 初始化健康检查服务
        await health_ws_manager.initialize_health_service(db)
        
        if not health_ws_manager.health_service:
            raise HTTPException(status_code=500, detail="Health service not available")
        
        # 执行健康检查
        health_status = await health_ws_manager.health_service.check_ai_service_health(config_id)
        
        # 广播健康状态更新
        await health_ws_manager.broadcast_health_update(config_id, health_status)
        
        return {
            "success": True,
            "data": health_status,
            "message": "Health check completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger health check for config {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/health-status/{config_id}")
async def get_health_status(
    config_id: int,
    current_user = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
):
    """获取指定配置的健康状态"""
    try:
        # 初始化健康检查服务
        await health_ws_manager.initialize_health_service(db)
        
        if not health_ws_manager.health_service:
            raise HTTPException(status_code=500, detail="Health service not available")
        
        # 获取健康状态
        health_status = await health_ws_manager.health_service.check_ai_service_health(config_id)
        
        return {
            "success": True,
            "data": health_status,
            "message": "Health status retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get health status for config {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get health status: {str(e)}")

# 后台任务：定期健康检查
async def periodic_health_check():
    """定期执行健康检查的后台任务"""
    while True:
        try:
            # 等待5分钟
            await asyncio.sleep(300)
            
            if not health_ws_manager.health_service:
                continue
            
            # 获取所有被订阅的配置ID
            subscribed_configs = set()
            for subscriptions in health_ws_manager.user_subscriptions.values():
                subscribed_configs.update(subscriptions)
            
            # 对每个被订阅的配置执行健康检查
            for config_id in subscribed_configs:
                try:
                    health_status = await health_ws_manager.health_service.check_ai_service_health(config_id)
                    await health_ws_manager.broadcast_health_update(config_id, health_status)
                except Exception as e:
                    logger.error(f"Periodic health check failed for config {config_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error in periodic health check: {str(e)}")

# 启动后台健康检查任务 - 移动到应用启动时
# asyncio.create_task(periodic_health_check())