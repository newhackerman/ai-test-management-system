"""
审计日志模型
"""
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Text, Enum, JSON, DateTime
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .base import Base, BaseModel


class AuditAction(PyEnum):
    """审计操作类型"""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    EXPORT = "export"
    IMPORT = "import"
    BATCH_OPERATION = "batch_operation"
    PERMISSION_CHANGE = "permission_change"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLE = "mfa_enable"
    MFA_DISABLE = "mfa_disable"


class AuditResult(PyEnum):
    """审计结果"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"


class AuditLog(BaseModel):
    """审计日志模型"""
    __tablename__ = "audit_logs"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    action = Column(Enum(AuditAction), nullable=False, comment="操作类型")
    resource_type = Column(String(50), nullable=False, comment="资源类型")
    resource_id = Column(String(100), nullable=True, comment="资源ID")
    old_values = Column(JSON, nullable=True, comment="变更前值")
    new_values = Column(JSON, nullable=True, comment="变更后值")
    ip_address = Column(String(45), nullable=True, comment="IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    result = Column(Enum(AuditResult), nullable=False, comment="操作结果")
    error_message = Column(Text, nullable=True, comment="错误信息")
    extra_data = Column(JSON, nullable=True, comment="额外数据")
    
    # 关系
    user = relationship("User", foreign_keys=[user_id])


class SecurityEvent(Base):
    """安全事件模型

    注意：此前定义在 services/audit_service.py（服务文件里建模型），
    导致该表只在服务被 import 时才注册进元数据，建库脚本
    rebuild_db.py 不经过它，表从未被建出来（get_security_events
    一查就 500）。第 11 项收敛时把它移入模型层，建库与启动建表
    两条路径都能覆盖。"""
    """安全事件模型"""
    __tablename__ = 'security_events'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='安全事件ID')
    
    # 事件基本信息
    event_type = Column(String(50), nullable=False, comment='事件类型')
    severity = Column(String(20), default='LOW', comment='严重程度')
    status = Column(String(20), default='OPEN', comment='事件状态')
    
    # 用户信息
    user_id = Column(BigInteger, comment='用户ID')
    username = Column(String(100), comment='用户名')
    user_ip = Column(String(45), comment='用户IP地址')
    
    # 事件详情
    description = Column(Text, comment='事件描述')
    details = Column(JSON, comment='事件详情')
    risk_score = Column(Integer, default=0, comment='风险评分')
    
    # 处理信息
    handled_by = Column(Integer, comment='处理人ID')
    handled_at = Column(DateTime, comment='处理时间')
    resolution = Column(Text, comment='处理结果')
    
    # 时间信息
    timestamp = Column(DateTime, default=datetime.utcnow, comment='事件时间')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'severity': self.severity,
            'status': self.status,
            'user_id': self.user_id,
            'username': self.username,
            'user_ip': self.user_ip,
            'description': self.description,
            'details': self.details,
            'risk_score': self.risk_score,
            'handled_by': self.handled_by,
            'handled_at': self.handled_at.isoformat() if self.handled_at else None,
            'resolution': self.resolution,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
