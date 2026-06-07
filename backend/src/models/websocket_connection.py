"""
WebSocket连接管理模型

实现WebSocketConnection SQLAlchemy模型，管理实时连接状态和事件订阅
"""

from sqlalchemy import Column, BigInteger, String, Text, Enum, DateTime, JSON, Integer, Boolean, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from enum import Enum as PyEnum
from typing import Dict, List, Any, Optional, Set
import uuid
import json

Base = declarative_base()

class ConnectionStatus(PyEnum):
    """连接状态枚举"""
    CONNECTING = "CONNECTING"  # 连接中
    CONNECTED = "CONNECTED"  # 已连接
    DISCONNECTED = "DISCONNECTED"  # 已断开
    RECONNECTING = "RECONNECTING"  # 重连中
    ERROR = "ERROR"  # 错误状态

class EventType(PyEnum):
    """事件类型枚举"""
    PROJECT_UPDATE = "PROJECT_UPDATE"  # 项目更新
    REQUIREMENT_UPDATE = "REQUIREMENT_UPDATE"  # 需求更新
    TEST_UPDATE = "TEST_UPDATE"  # 测试更新
    SYSTEM_ALERT = "SYSTEM_ALERT"  # 系统告警
    USER_ACTIVITY = "USER_ACTIVITY"  # 用户活动
    DATA_REFRESH = "DATA_REFRESH"  # 数据刷新
    NOTIFICATION = "NOTIFICATION"  # 通知消息
    HEARTBEAT = "HEARTBEAT"  # 心跳检测
    CUSTOM_EVENT = "CUSTOM_EVENT"  # 自定义事件

class ClientType(PyEnum):
    """客户端类型枚举"""
    WEB_BROWSER = "WEB_BROWSER"  # 网页浏览器
    MOBILE_APP = "MOBILE_APP"  # 移动应用
    DESKTOP_APP = "DESKTOP_APP"  # 桌面应用
    API_CLIENT = "API_CLIENT"  # API客户端

class WebSocketConnection(Base):
    """
    WebSocket连接管理表
    
    管理用户的WebSocket连接状态和事件订阅
    """
    __tablename__ = 'websocket_connections'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='连接ID')
    connection_id = Column(String(255), unique=True, nullable=False, comment='连接标识')
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment='用户ID')
    role_type = Column(String(50), nullable=False, comment='角色类型')
    
    # 连接信息
    status = Column(Enum(ConnectionStatus), default=ConnectionStatus.CONNECTING, comment='连接状态')
    client_type = Column(Enum(ClientType), default=ClientType.WEB_BROWSER, comment='客户端类型')
    client_info = Column(JSON, comment='客户端信息JSON')
    
    # 订阅信息
    subscribed_events = Column(JSON, comment='订阅的事件类型JSON')
    project_ids = Column(JSON, comment='订阅的项目ID列表JSON')
    
    # 连接管理
    connect_time = Column(DateTime, default=datetime.utcnow, comment='连接时间')
    last_heartbeat = Column(DateTime, default=datetime.utcnow, comment='最后心跳时间')
    disconnect_time = Column(DateTime, comment='断开时间')
    
    # 性能统计
    message_count = Column(Integer, default=0, comment='消息数量')
    bytes_sent = Column(BigInteger, default=0, comment='发送字节数')
    bytes_received = Column(BigInteger, default=0, comment='接收字节数')
    
    # 错误信息
    last_error = Column(Text, comment='最后错误信息')
    error_count = Column(Integer, default=0, comment='错误次数')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引优化
    __table_args__ = (
        Index('idx_connection_id', 'connection_id'),
        Index('idx_user_id', 'user_id'),
        Index('idx_status', 'status'),
        Index('idx_role_type', 'role_type'),
        Index('idx_last_heartbeat', 'last_heartbeat'),
        Index('idx_user_status', 'user_id', 'status'),
        {'comment': 'WebSocket连接管理表'}
    )
    
    def __repr__(self):
        return f"<WebSocketConnection(id={self.id}, connection_id='{self.connection_id}', user_id={self.user_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'role_type': self.role_type,
            'status': self.status.value if self.status else None,
            'client_type': self.client_type.value if self.client_type else None,
            'client_info': self.client_info,
            'subscribed_events': self.subscribed_events,
            'project_ids': self.project_ids,
            'connect_time': self.connect_time.isoformat() if self.connect_time else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'disconnect_time': self.disconnect_time.isoformat() if self.disconnect_time else None,
            'message_count': self.message_count,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'last_error': self.last_error,
            'error_count': self.error_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_connection(
        cls,
        user_id: int,
        role_type: str,
        client_type: ClientType = ClientType.WEB_BROWSER,
        client_info: Optional[Dict[str, Any]] = None
    ) -> 'WebSocketConnection':
        """创建新的WebSocket连接"""
        connection_id = f"{user_id}_{role_type}_{uuid.uuid4().hex[:8]}"
        
        return cls(
            connection_id=connection_id,
            user_id=user_id,
            role_type=role_type,
            status=ConnectionStatus.CONNECTING,
            client_type=client_type,
            client_info=client_info or {},
            subscribed_events=[],
            project_ids=[]
        )
    
    def is_active(self) -> bool:
        """检查连接是否活跃"""
        if self.status != ConnectionStatus.CONNECTED:
            return False
        
        # 检查心跳超时（5分钟）
        if self.last_heartbeat:
            timeout = datetime.utcnow() - timedelta(minutes=5)
            return self.last_heartbeat > timeout
        
        return False
    
    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = datetime.utcnow()
        if self.status == ConnectionStatus.CONNECTING:
            self.status = ConnectionStatus.CONNECTED
    
    def subscribe_to_events(self, event_types: List[str]):
        """订阅事件类型"""
        if not self.subscribed_events:
            self.subscribed_events = []
        
        # 验证事件类型
        valid_events = [e.value for e in EventType]
        new_events = [e for e in event_types if e in valid_events]
        
        # 合并事件列表
        current_events = set(self.subscribed_events)
        current_events.update(new_events)
        self.subscribed_events = list(current_events)
    
    def unsubscribe_from_events(self, event_types: List[str]):
        """取消订阅事件类型"""
        if not self.subscribed_events:
            return
        
        current_events = set(self.subscribed_events)
        for event_type in event_types:
            current_events.discard(event_type)
        
        self.subscribed_events = list(current_events)
    
    def subscribe_to_projects(self, project_ids: List[int]):
        """订阅项目"""
        if not self.project_ids:
            self.project_ids = []
        
        current_projects = set(self.project_ids)
        current_projects.update(project_ids)
        self.project_ids = list(current_projects)
    
    def unsubscribe_from_projects(self, project_ids: List[int]):
        """取消订阅项目"""
        if not self.project_ids:
            return
        
        current_projects = set(self.project_ids)
        for project_id in project_ids:
            current_projects.discard(project_id)
        
        self.project_ids = list(current_projects)
    
    def is_subscribed_to_event(self, event_type: str) -> bool:
        """检查是否订阅了特定事件"""
        return event_type in (self.subscribed_events or [])
    
    def is_subscribed_to_project(self, project_id: int) -> bool:
        """检查是否订阅了特定项目"""
        return project_id in (self.project_ids or [])
    
    def record_message(self, bytes_count: int, is_sent: bool = True):
        """记录消息统计"""
        self.message_count += 1
        if is_sent:
            self.bytes_sent += bytes_count
        else:
            self.bytes_received += bytes_count
    
    def record_error(self, error_message: str):
        """记录错误信息"""
        self.last_error = error_message
        self.error_count += 1
        self.status = ConnectionStatus.ERROR
    
    def disconnect(self, error_message: Optional[str] = None):
        """断开连接"""
        self.status = ConnectionStatus.DISCONNECTED
        self.disconnect_time = datetime.utcnow()
        if error_message:
            self.record_error(error_message)
    
    def get_connection_duration(self) -> timedelta:
        """获取连接持续时间"""
        end_time = self.disconnect_time or datetime.utcnow()
        return end_time - self.connect_time
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        duration = self.get_connection_duration()
        
        return {
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'status': self.status.value,
            'duration_seconds': duration.total_seconds(),
            'message_count': self.message_count,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'error_count': self.error_count,
            'is_active': self.is_active(),
            'subscribed_events_count': len(self.subscribed_events or []),
            'subscribed_projects_count': len(self.project_ids or [])
        }


class WebSocketEvent(Base):
    """
    WebSocket事件记录表
    
    记录通过WebSocket发送的事件消息
    """
    __tablename__ = 'websocket_events'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='事件ID')
    event_id = Column(String(255), unique=True, nullable=False, comment='事件标识')
    event_type = Column(Enum(EventType), nullable=False, comment='事件类型')
    
    # 事件内容
    event_data = Column(JSON, comment='事件数据JSON')
    message_size = Column(Integer, comment='消息大小(字节)')
    
    # 目标信息
    target_user_ids = Column(JSON, comment='目标用户ID列表JSON')
    target_roles = Column(JSON, comment='目标角色列表JSON')
    target_projects = Column(JSON, comment='目标项目ID列表JSON')
    
    # 发送统计
    total_recipients = Column(Integer, default=0, comment='总接收者数量')
    successful_sends = Column(Integer, default=0, comment='成功发送数量')
    failed_sends = Column(Integer, default=0, comment='失败发送数量')
    
    # 性能指标
    processing_time_ms = Column(Integer, comment='处理耗时(毫秒)')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 索引优化
    __table_args__ = (
        Index('idx_event_id', 'event_id'),
        Index('idx_event_type', 'event_type'),
        Index('idx_created_at', 'created_at'),
        Index('idx_type_created', 'event_type', 'created_at'),
        {'comment': 'WebSocket事件记录表'}
    )
    
    def __repr__(self):
        return f"<WebSocketEvent(id={self.id}, event_id='{self.event_id}', type='{self.event_type.value}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'event_type': self.event_type.value if self.event_type else None,
            'event_data': self.event_data,
            'message_size': self.message_size,
            'target_user_ids': self.target_user_ids,
            'target_roles': self.target_roles,
            'target_projects': self.target_projects,
            'total_recipients': self.total_recipients,
            'successful_sends': self.successful_sends,
            'failed_sends': self.failed_sends,
            'processing_time_ms': self.processing_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def create_event(
        cls,
        event_type: EventType,
        event_data: Dict[str, Any],
        target_user_ids: Optional[List[int]] = None,
        target_roles: Optional[List[str]] = None,
        target_projects: Optional[List[int]] = None
    ) -> 'WebSocketEvent':
        """创建WebSocket事件"""
        event_id = f"{event_type.value}_{uuid.uuid4().hex[:12]}"
        
        # 计算消息大小
        message_json = json.dumps(event_data, ensure_ascii=False)
        message_size = len(message_json.encode('utf-8'))
        
        return cls(
            event_id=event_id,
            event_type=event_type,
            event_data=event_data,
            message_size=message_size,
            target_user_ids=target_user_ids or [],
            target_roles=target_roles or [],
            target_projects=target_projects or []
        )
    
    def record_send_result(self, successful: int, failed: int):
        """记录发送结果"""
        self.successful_sends = successful
        self.failed_sends = failed
        self.total_recipients = successful + failed
    
    def get_success_rate(self) -> float:
        """获取发送成功率"""
        if self.total_recipients == 0:
            return 0.0
        return (self.successful_sends / self.total_recipients) * 100


class ConnectionPool(Base):
    """
    连接池管理表
    
    管理WebSocket连接池的状态和配置
    """
    __tablename__ = 'connection_pools'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='连接池ID')
    pool_name = Column(String(100), unique=True, nullable=False, comment='连接池名称')
    
    # 连接池配置
    max_connections = Column(Integer, default=1000, comment='最大连接数')
    current_connections = Column(Integer, default=0, comment='当前连接数')
    
    # 性能配置
    heartbeat_interval = Column(Integer, default=30, comment='心跳间隔(秒)')
    connection_timeout = Column(Integer, default=300, comment='连接超时(秒)')
    message_queue_size = Column(Integer, default=100, comment='消息队列大小')
    
    # 统计信息
    total_connections = Column(BigInteger, default=0, comment='总连接数')
    total_messages = Column(BigInteger, default=0, comment='总消息数')
    total_errors = Column(BigInteger, default=0, comment='总错误数')
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment='是否激活')
    
    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 索引优化
    __table_args__ = (
        Index('idx_pool_name', 'pool_name'),
        Index('idx_is_active', 'is_active'),
        {'comment': '连接池管理表'}
    )
    
    def __repr__(self):
        return f"<ConnectionPool(id={self.id}, name='{self.pool_name}', connections={self.current_connections})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'pool_name': self.pool_name,
            'max_connections': self.max_connections,
            'current_connections': self.current_connections,
            'heartbeat_interval': self.heartbeat_interval,
            'connection_timeout': self.connection_timeout,
            'message_queue_size': self.message_queue_size,
            'total_connections': self.total_connections,
            'total_messages': self.total_messages,
            'total_errors': self.total_errors,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_full(self) -> bool:
        """检查连接池是否已满"""
        return self.current_connections >= self.max_connections
    
    def get_utilization_rate(self) -> float:
        """获取连接池利用率"""
        if self.max_connections == 0:
            return 0.0
        return (self.current_connections / self.max_connections) * 100
    
    def increment_connection(self):
        """增加连接数"""
        if not self.is_full():
            self.current_connections += 1
            self.total_connections += 1
    
    def decrement_connection(self):
        """减少连接数"""
        if self.current_connections > 0:
            self.current_connections -= 1
    
    def record_message(self):
        """记录消息统计"""
        self.total_messages += 1
    
    def record_error(self):
        """记录错误统计"""
        self.total_errors += 1