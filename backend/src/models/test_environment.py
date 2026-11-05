"""
测试环境相关数据模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Boolean, JSON, Index, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum

from .base import BaseModel


class EnvironmentStatus(PyEnum):
    """环境状态枚举"""
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    MAINTENANCE = "MAINTENANCE"
    UNAVAILABLE = "UNAVAILABLE"


class EnvironmentType(PyEnum):
    """环境类型枚举"""
    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    INTEGRATION = "INTEGRATION"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"


class ReservationStatus(PyEnum):
    """预约状态枚举"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TestEnvironment(BaseModel):
    """测试环境模型"""
    __tablename__ = 'test_environments'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='环境ID')
    environment_name = Column(String(100), nullable=False, comment='环境名称')
    environment_code = Column(String(50), unique=True, nullable=False, comment='环境编码')
    environment_type = Column(Enum(EnvironmentType), nullable=False, comment='环境类型')
    
    # 基本信息
    description = Column(Text, comment='环境描述')
    status = Column(Enum(EnvironmentStatus), default=EnvironmentStatus.AVAILABLE, comment='环境状态')
    
    # 配置信息
    configuration = Column(JSON, comment='环境配置')
    connection_info = Column(JSON, comment='连接信息')
    
    # 容量信息
    max_concurrent_users = Column(BigInteger, default=1, comment='最大并发用户数')
    current_users = Column(BigInteger, default=0, comment='当前用户数')
    
    # 管理信息
    owner_id = Column(Integer, ForeignKey('users.id'), comment='环境负责人ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), comment='所属项目ID')
    
    # 状态管理
    is_active = Column(Boolean, default=True, comment='是否激活')
    is_public = Column(Boolean, default=False, comment='是否公开')
    
    # 维护信息
    last_maintenance_at = Column(DateTime, comment='最后维护时间')
    next_maintenance_at = Column(DateTime, comment='下次维护时间')
    maintenance_notes = Column(Text, comment='维护备注')
    
    # 监控信息
    health_check_url = Column(String(500), comment='健康检查URL')
    last_health_check_at = Column(DateTime, comment='最后健康检查时间')
    health_status = Column(String(20), default='UNKNOWN', comment='健康状态')
    
    # 关联关系
    owner = relationship("User", foreign_keys=[owner_id])
    project = relationship("Project", foreign_keys=[project_id])
    reservations = relationship("EnvironmentReservation", back_populates="environment", cascade="all, delete-orphan")
    deployments = relationship("EnvironmentDeployment", back_populates="environment", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_test_environments_code', 'environment_code'),
        Index('idx_test_environments_type', 'environment_type'),
        Index('idx_test_environments_status', 'status'),
        Index('idx_test_environments_owner', 'owner_id'),
        Index('idx_test_environments_project', 'project_id'),
        Index('idx_test_environments_active', 'is_active'),
    )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'environment_name': self.environment_name,
            'environment_code': self.environment_code,
            'environment_type': self.environment_type.value if self.environment_type else None,
            'description': self.description,
            'status': self.status.value if self.status else None,
            'configuration': self.configuration,
            'connection_info': self.connection_info,
            'max_concurrent_users': self.max_concurrent_users,
            'current_users': self.current_users,
            'owner_id': self.owner_id,
            'project_id': self.project_id,
            'is_active': self.is_active,
            'is_public': self.is_public,
            'last_maintenance_at': self.last_maintenance_at.isoformat() if self.last_maintenance_at else None,
            'next_maintenance_at': self.next_maintenance_at.isoformat() if self.next_maintenance_at else None,
            'maintenance_notes': self.maintenance_notes,
            'health_check_url': self.health_check_url,
            'last_health_check_at': self.last_health_check_at.isoformat() if self.last_health_check_at else None,
            'health_status': self.health_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EnvironmentReservation(BaseModel):
    """环境预约模型"""
    __tablename__ = 'environment_reservations'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='预约ID')
    reservation_code = Column(String(50), unique=True, nullable=False, comment='预约编码')
    environment_id = Column(BigInteger, ForeignKey('test_environments.id'), nullable=False, comment='环境ID')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    
    # 预约信息
    reserved_from = Column(DateTime, nullable=False, comment='预约开始时间')
    reserved_until = Column(DateTime, nullable=False, comment='预约结束时间')
    purpose = Column(String(200), nullable=False, comment='使用目的')
    notes = Column(Text, comment='备注')
    
    # 状态管理
    status = Column(Enum(ReservationStatus), default=ReservationStatus.PENDING, comment='预约状态')
    
    # 审批信息
    approved_by = Column(Integer, ForeignKey('users.id'), comment='审批人ID')
    approved_at = Column(DateTime, comment='审批时间')
    approval_notes = Column(Text, comment='审批备注')
    
    # 使用信息
    actual_start_time = Column(DateTime, comment='实际开始时间')
    actual_end_time = Column(DateTime, comment='实际结束时间')
    usage_notes = Column(Text, comment='使用备注')
    
    # 关联关系
    environment = relationship("TestEnvironment", back_populates="reservations")
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    
    # 索引
    __table_args__ = (
        Index('idx_environment_reservations_code', 'reservation_code'),
        Index('idx_environment_reservations_env', 'environment_id'),
        Index('idx_environment_reservations_user', 'user_id'),
        Index('idx_environment_reservations_status', 'status'),
        Index('idx_environment_reservations_time', 'reserved_from', 'reserved_until'),
    )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'reservation_code': self.reservation_code,
            'environment_id': self.environment_id,
            'user_id': self.user_id,
            'reserved_from': self.reserved_from.isoformat() if self.reserved_from else None,
            'reserved_until': self.reserved_until.isoformat() if self.reserved_until else None,
            'purpose': self.purpose,
            'notes': self.notes,
            'status': self.status.value if self.status else None,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approval_notes': self.approval_notes,
            'actual_start_time': self.actual_start_time.isoformat() if self.actual_start_time else None,
            'actual_end_time': self.actual_end_time.isoformat() if self.actual_end_time else None,
            'usage_notes': self.usage_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class EnvironmentDeployment(BaseModel):
    """环境部署模型"""
    __tablename__ = 'environment_deployments'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='部署ID')
    deployment_code = Column(String(50), unique=True, nullable=False, comment='部署编码')
    environment_id = Column(BigInteger, ForeignKey('test_environments.id'), nullable=False, comment='环境ID')
    
    # 部署信息
    deployment_type = Column(String(50), nullable=False, comment='部署类型')
    version = Column(String(100), comment='版本号')
    branch = Column(String(100), comment='分支名称')
    commit_hash = Column(String(100), comment='提交哈希')
    
    # 部署配置
    deployment_config = Column(JSON, comment='部署配置')
    environment_variables = Column(JSON, comment='环境变量')
    
    # 状态管理
    status = Column(String(20), default='PENDING', comment='部署状态')
    
    # 时间信息
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    duration = Column(BigInteger, comment='部署时长(秒)')
    
    # 人员信息
    deployed_by = Column(Integer, ForeignKey('users.id'), nullable=False, comment='部署人ID')
    
    # 结果信息
    deployment_logs = Column(Text, comment='部署日志')
    error_message = Column(Text, comment='错误信息')
    
    # 关联关系
    environment = relationship("TestEnvironment", back_populates="deployments")
    deployer = relationship("User", foreign_keys=[deployed_by])
    
    # 索引
    __table_args__ = (
        Index('idx_environment_deployments_code', 'deployment_code'),
        Index('idx_environment_deployments_env', 'environment_id'),
        Index('idx_environment_deployments_status', 'status'),
        Index('idx_environment_deployments_deployer', 'deployed_by'),
        Index('idx_environment_deployments_time', 'started_at'),
    )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'deployment_code': self.deployment_code,
            'environment_id': self.environment_id,
            'deployment_type': self.deployment_type,
            'version': self.version,
            'branch': self.branch,
            'commit_hash': self.commit_hash,
            'deployment_config': self.deployment_config,
            'environment_variables': self.environment_variables,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'deployed_by': self.deployed_by,
            'deployment_logs': self.deployment_logs,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TestData(BaseModel):
    """测试数据模型"""
    __tablename__ = 'test_data'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='测试数据ID')
    data_name = Column(String(100), nullable=False, comment='数据名称')
    data_type = Column(String(50), nullable=False, comment='数据类型')
    environment_id = Column(BigInteger, ForeignKey('test_environments.id'), comment='关联环境ID')
    
    # 数据内容
    data_content = Column(JSON, comment='数据内容')
    data_file_path = Column(String(500), comment='数据文件路径')
    
    # 数据配置
    is_sensitive = Column(Boolean, default=False, comment='是否敏感数据')
    is_reusable = Column(Boolean, default=True, comment='是否可重用')
    auto_cleanup = Column(Boolean, default=True, comment='是否自动清理')
    
    # 生命周期
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False, comment='创建人ID')
    expires_at = Column(DateTime, comment='过期时间')
    
    # 使用统计
    usage_count = Column(BigInteger, default=0, comment='使用次数')
    last_used_at = Column(DateTime, comment='最后使用时间')
    
    # 关联关系
    environment = relationship("TestEnvironment", foreign_keys=[environment_id])
    creator = relationship("User", foreign_keys=[created_by])
    
    # 索引
    __table_args__ = (
        Index('idx_test_data_name', 'data_name'),
        Index('idx_test_data_type', 'data_type'),
        Index('idx_test_data_env', 'environment_id'),
        Index('idx_test_data_creator', 'created_by'),
        Index('idx_test_data_expires', 'expires_at'),
    )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'data_name': self.data_name,
            'data_type': self.data_type,
            'environment_id': self.environment_id,
            'data_content': self.data_content if not self.is_sensitive else None,
            'data_file_path': self.data_file_path,
            'is_sensitive': self.is_sensitive,
            'is_reusable': self.is_reusable,
            'auto_cleanup': self.auto_cleanup,
            'created_by': self.created_by,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }