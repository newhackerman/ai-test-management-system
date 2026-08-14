"""
实时服务

提供WebSocket实时推送功能的通用接口
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import Depends
from sqlalchemy.orm import Session

from .dashboard_realtime_service import DashboardRealtimeService, get_dashboard_realtime_service
from ..core.database import get_db

logger = logging.getLogger(__name__)


class RealtimeService:
    """实时服务 - 包装仪表板实时服务"""

    def __init__(self, db: Session = None):
        self.db = db
        self.dashboard_realtime_service = get_dashboard_realtime_service()

    async def connect_user(self, websocket, user_id: int, role_type: str):
        """连接用户到WebSocket"""
        return await self.dashboard_realtime_service.connect_user(websocket, user_id, role_type)

    async def disconnect_user(self, user_id: int):
        """断开用户WebSocket连接"""
        return await self.dashboard_realtime_service.disconnect_user(user_id)

    async def send_to_user(self, user_id: int, message: Dict[str, Any]):
        """发送消息给特定用户"""
        return await self.dashboard_realtime_service.send_to_user(user_id, message)

    async def send_to_role(self, role_type: str, message: Dict[str, Any]):
        """发送消息给特定角色的所有用户"""
        return await self.dashboard_realtime_service.send_to_role(role_type, message)

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接的用户"""
        return await self.dashboard_realtime_service.broadcast(message)

    async def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        stats = self.dashboard_realtime_service.get_connection_stats()
        return {
            "total_connections": stats.get("total_connections", 0),
            "active_connections": stats.get("active_connections", 0),
            "connections_by_role": stats.get("active_connections_detail", {}).get("by_role", {}),
        }

    def get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.utcnow().isoformat()


def get_realtime_service(db: Session = Depends(get_db)) -> RealtimeService:
    """
    获取实时服务实例
    
    Args:
        db: 数据库会话（通过依赖注入）
        
    Returns:
        RealtimeService: 实时服务实例
    """
    return RealtimeService(db)