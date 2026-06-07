"""
审计日志模型
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .base import BaseModel


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

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
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