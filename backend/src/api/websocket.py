"""
WebSocket服务 - 配置变更实时推送
"""
import json
import asyncio
import redis.asyncio as redis
from typing import Dict, Set, List, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends
from fastapi.routing import APIRouter
import logging
from datetime import datetime

from ..core.auth import get_current_user
from ..models.user import User
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储所有活跃连接: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
        # 存储连接对应的用户信息: {connection_id: user_info}
        self.connection_users: Dict[str, dict] = {}
        # 存储用户订阅的频道: {user_id: set(channels)}
        self.user_subscriptions: Dict[int, Set[str]] = {}
        # Redis连接
        self.redis_client: Optional[redis.Redis] = None
        # 订阅任务
        self.subscription_task: Optional[asyncio.Task] = None
        
    async def init_redis(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # 测试连接
            await self.redis_client.ping()
            logger.info("WebSocket Redis连接初始化成功")
            
            # 启动订阅任务
            self.subscription_task = asyncio.create_task(self._listen_redis_channels())
            
        except Exception as e:
            logger.error(f"WebSocket Redis连接初始化失败: {e}")
            
    async def close_redis(self):
        """关闭Redis连接"""
        if self.subscription_task:
            self.subscription_task.cancel()
            try:
                await self.subscription_task
            except asyncio.CancelledError:
                pass
                
        if self.redis_client:
            await self.redis_client.close()
            logger.info("WebSocket Redis连接已关闭")

    async def connect(self, websocket: WebSocket, user: User, connection_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        
        # 存储连接
        user_id = user.id
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][connection_id] = websocket
        self.connection_users[connection_id] = {
            'user_id': user_id,
            'username': user.username,
            'email': user.email,
            'connected_at': datetime.now().isoformat()
        }
        
        # 初始化用户订阅
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
            
        logger.info(f"用户 {user.username} WebSocket连接建立: {connection_id}")
        
        # 发送连接成功消息
        await self.send_personal_message({
            'type': 'connection_established',
            'message': 'WebSocket连接建立成功',
            'connection_id': connection_id,
            'timestamp': datetime.now().isoformat()
        }, user_id)

    async def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        if connection_id in self.connection_users:
            user_info = self.connection_users[connection_id]
            user_id = user_info['user_id']
            
            # 移除连接
            if user_id in self.active_connections:
                self.active_connections[user_id].pop(connection_id, None)
                
                # 如果用户没有其他连接，清理订阅
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    self.user_subscriptions.pop(user_id, None)
            
            del self.connection_users[connection_id]
            
            logger.info(f"用户 {user_info['username']} WebSocket连接断开: {connection_id}")

    async def send_personal_message(self, message: dict, user_id: int):
        """发送个人消息"""
        if user_id in self.active_connections:
            message_str = json.dumps(message, ensure_ascii=False)
            
            # 发送给用户的所有连接
            disconnected_connections = []
            for connection_id, websocket in self.active_connections[user_id].items():
                try:
                    await websocket.send_text(message_str)
                except Exception as e:
                    logger.error(f"发送消息失败 {connection_id}: {e}")
                    disconnected_connections.append(connection_id)
            
            # 清理断开的连接
            for connection_id in disconnected_connections:
                await self.disconnect(connection_id)

    async def broadcast_to_users(self, message: dict, user_ids: List[int]):
        """向指定用户列表广播消息"""
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)

    async def broadcast_to_all(self, message: dict):
        """向所有连接的用户广播消息"""
        user_ids = list(self.active_connections.keys())
        await self.broadcast_to_users(message, user_ids)

    async def subscribe_channel(self, user_id: int, channel: str):
        """用户订阅频道"""
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        
        self.user_subscriptions[user_id].add(channel)
        logger.info(f"用户 {user_id} 订阅频道: {channel}")

    async def unsubscribe_channel(self, user_id: int, channel: str):
        """用户取消订阅频道"""
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(channel)

    async def _listen_redis_channels(self):
        """监听Redis发布订阅频道"""
        if not self.redis_client:
            return
            
        try:
            # 订阅配置变更相关频道
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(
                'config:change:*',  # 配置变更通知
                'audit:status:*',   # 审核状态变更
                'audit:new:*',      # 新审核请求
                'system:*'          # 系统通知
            )
            
            logger.info("开始监听Redis发布订阅频道")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    await self._handle_redis_message(message)
                    
        except asyncio.CancelledError:
            logger.info("Redis频道监听任务已取消")
        except Exception as e:
            logger.error(f"监听Redis频道出错: {e}")

    async def _handle_redis_message(self, message):
        """处理Redis消息"""
        try:
            channel = message['channel']
            data = json.loads(message['data'])
            
            # 构造WebSocket消息
            ws_message = {
                'type': 'redis_notification',
                'channel': channel,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            
            # 根据频道类型决定推送范围
            if channel.startswith('config:change'):
                # 配置变更通知 - 推送给所有连接的用户
                ws_message['type'] = 'config_change'
                await self.broadcast_to_all(ws_message)
                
            elif channel.startswith('audit:status'):
                # 审核状态变更 - 推送给相关用户
                ws_message['type'] = 'audit_status_change'
                # 根据审核数据确定推送用户
                target_users = self._get_audit_notification_users(data)
                await self.broadcast_to_users(ws_message, target_users)
                
            elif channel.startswith('audit:new'):
                # 新审核请求 - 推送给有审核权限的用户
                ws_message['type'] = 'new_audit_request'
                # 推送给所有有审核权限的用户（简化处理）
                await self.broadcast_to_all(ws_message)
                
            elif channel.startswith('system'):
                # 系统通知 - 推送给所有用户
                ws_message['type'] = 'system_notification'
                await self.broadcast_to_all(ws_message)
            
        except Exception as e:
            logger.error(f"处理Redis消息失败: {e}")

    def _get_audit_notification_users(self, audit_data: dict) -> List[int]:
        """获取需要接收审核通知的用户ID列表"""
        # 简化实现：返回所有在线用户
        # 在实际项目中，应该根据审核权限和相关性确定推送用户
        return list(self.active_connections.keys())

    def get_connection_stats(self) -> dict:
        """获取连接统计信息"""
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        return {
            'total_users': len(self.active_connections),
            'total_connections': total_connections,
            'active_users': list(self.active_connections.keys()),
            'connection_details': self.connection_users
        }


# 创建全局连接管理器
manager = ConnectionManager()


@router.on_event("startup")
async def startup_event():
    """应用启动时初始化WebSocket服务"""
    await manager.init_redis()


@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理WebSocket服务"""
    await manager.close_redis()


@router.websocket("/ws/config-updates")
async def websocket_config_updates(websocket: WebSocket):
    """配置更新WebSocket端点"""
    connection_id = f"ws_{datetime.now().timestamp()}"
    user = None
    
    try:
        # 获取用户信息（这里简化处理，实际应该从token验证）
        # user = await get_current_user_websocket(websocket)
        # 暂时使用模拟用户
        from ..models.user import User
        user = User(id=1, username="admin", email="admin@example.com")
        
        await manager.connect(websocket, user, connection_id)
        
        # 订阅默认频道
        user_id = user.id
        await manager.subscribe_channel(user_id, 'config:change')
        await manager.subscribe_channel(user_id, 'audit:status')
        
        while True:
            # 接收客户端消息
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                await handle_client_message(data, user_id, connection_id)
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    'type': 'error',
                    'message': '消息格式错误',
                    'timestamp': datetime.now().isoformat()
                }, user_id)
            
    except WebSocketDisconnect:
        if user:
            await manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        if user:
            await manager.disconnect(connection_id)


@router.websocket("/ws/audit-notifications")
async def websocket_audit_notifications(websocket: WebSocket):
    """审核通知WebSocket端点"""
    connection_id = f"audit_ws_{datetime.now().timestamp()}"
    user = None
    
    try:
        # 获取用户信息
        from ..models.user import User
        user = User(id=1, username="admin", email="admin@example.com")
        
        await manager.connect(websocket, user, connection_id)
        
        # 订阅审核相关频道
        user_id = user.id
        await manager.subscribe_channel(user_id, 'audit:status')
        await manager.subscribe_channel(user_id, 'audit:new')
        
        while True:
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                await handle_audit_message(data, user_id, connection_id)
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    'type': 'error',
                    'message': '消息格式错误',
                    'timestamp': datetime.now().isoformat()
                }, user_id)
            
    except WebSocketDisconnect:
        if user:
            await manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"审核WebSocket连接异常: {e}")
        if user:
            await manager.disconnect(connection_id)


async def handle_client_message(data: dict, user_id: int, connection_id: str):
    """处理客户端消息"""
    message_type = data.get('type')
    
    if message_type == 'ping':
        # 心跳检测
        await manager.send_personal_message({
            'type': 'pong',
            'timestamp': datetime.now().isoformat()
        }, user_id)
        
    elif message_type == 'subscribe':
        # 订阅频道
        channel = data.get('channel')
        if channel:
            await manager.subscribe_channel(user_id, channel)
            await manager.send_personal_message({
                'type': 'subscribed',
                'channel': channel,
                'message': f'已订阅频道: {channel}',
                'timestamp': datetime.now().isoformat()
            }, user_id)
            
    elif message_type == 'unsubscribe':
        # 取消订阅频道
        channel = data.get('channel')
        if channel:
            await manager.unsubscribe_channel(user_id, channel)
            await manager.send_personal_message({
                'type': 'unsubscribed',
                'channel': channel,
                'message': f'已取消订阅频道: {channel}',
                'timestamp': datetime.now().isoformat()
            }, user_id)
            
    elif message_type == 'get_stats':
        # 获取连接统计信息
        stats = manager.get_connection_stats()
        await manager.send_personal_message({
            'type': 'connection_stats',
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }, user_id)


async def handle_audit_message(data: dict, user_id: int, connection_id: str):
    """处理审核相关消息"""
    message_type = data.get('type')
    
    if message_type == 'join_audit_room':
        # 加入审核房间
        audit_id = data.get('audit_id')
        if audit_id:
            channel = f'audit:room:{audit_id}'
            await manager.subscribe_channel(user_id, channel)
            await manager.send_personal_message({
                'type': 'joined_audit_room',
                'audit_id': audit_id,
                'message': f'已加入审核房间: {audit_id}',
                'timestamp': datetime.now().isoformat()
            }, user_id)
            
    elif message_type == 'leave_audit_room':
        # 离开审核房间
        audit_id = data.get('audit_id')
        if audit_id:
            channel = f'audit:room:{audit_id}'
            await manager.unsubscribe_channel(user_id, channel)
            await manager.send_personal_message({
                'type': 'left_audit_room',
                'audit_id': audit_id,
                'message': f'已离开审核房间: {audit_id}',
                'timestamp': datetime.now().isoformat()
            }, user_id)


# 工具函数：发布配置变更事件
async def publish_config_change(config_key: str, environment: str, change_type: str, user_id: int):
    """发布配置变更事件到Redis"""
    try:
        if manager.redis_client:
            event_data = {
                'config_key': config_key,
                'environment': environment,
                'change_type': change_type,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # 发布到通用频道
            await manager.redis_client.publish(
                'config:change:global',
                json.dumps(event_data, ensure_ascii=False)
            )
            
            # 发布到环境特定频道
            await manager.redis_client.publish(
                f'config:change:{environment}',
                json.dumps(event_data, ensure_ascii=False)
            )
            
    except Exception as e:
        logger.error(f"发布配置变更事件失败: {e}")


# 工具函数：发布审核状态变更事件
async def publish_audit_status_change(audit_id: int, old_status: str, new_status: str, user_id: int):
    """发布审核状态变更事件到Redis"""
    try:
        if manager.redis_client:
            event_data = {
                'audit_id': audit_id,
                'old_status': old_status,
                'new_status': new_status,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
            
            await manager.redis_client.publish(
                'audit:status:change',
                json.dumps(event_data, ensure_ascii=False)
            )
            
    except Exception as e:
        logger.error(f"发布审核状态变更事件失败: {e}")


# 工具函数：发布新审核请求事件
async def publish_new_audit_request(audit_id: int, config_key: str, environment: str, user_id: int):
    """发布新审核请求事件到Redis"""
    try:
        if manager.redis_client:
            event_data = {
                'audit_id': audit_id,
                'config_key': config_key,
                'environment': environment,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }
            
            await manager.redis_client.publish(
                'audit:new:request',
                json.dumps(event_data, ensure_ascii=False)
            )
            
    except Exception as e:
        logger.error(f"发布新审核请求事件失败: {e}")