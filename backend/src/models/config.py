"""
系统配置模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime, BigInteger, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
import enum
from .base import BaseModel


class ConfigType(enum.Enum):
    """配置类型枚举"""
    STRING = "STRING"       # 字符串
    TEXT = "TEXT"           # 长文本
    INTEGER = "INTEGER"     # 整数
    FLOAT = "FLOAT"         # 浮点数
    BOOLEAN = "BOOLEAN"     # 布尔值
    JSON = "JSON"          # JSON对象
    ARRAY = "ARRAY"         # 数组
    EMAIL = "EMAIL"         # 邮箱地址
    URL = "URL"            # 网址
    ENUM = "ENUM"           # 枚举值
    PASSWORD = "PASSWORD"   # 密码（加密存储）
    FILE = "FILE"           # 文件路径
    COLOR = "COLOR"         # 颜色值
    DATE = "DATE"           # 日期
    TIME = "TIME"           # 时间


class Environment(enum.Enum):
    """环境类型枚举"""
    DEV = "dev"           # 开发环境
    TEST = "test"         # 测试环境
    STAGING = "staging"   # 预发环境
    PROD = "prod"         # 生产环境
    DEMO = "demo"         # 演示环境
    PERF = "perf"         # 性能测试环境


class PermissionType(enum.Enum):
    """权限类型枚举"""
    CONFIG = "CONFIG"         # 对单个配置的权限
    GROUP = "GROUP"           # 对配置分组的权限
    ENVIRONMENT = "ENVIRONMENT" # 对环境的权限
    GLOBAL = "GLOBAL"         # 全局权限


class PermissionAction(enum.Enum):
    """权限操作枚举"""
    READ = "READ"     # 读取
    WRITE = "WRITE"   # 写入
    DELETE = "DELETE" # 删除
    AUDIT = "AUDIT"   # 审核


class SystemConfig(BaseModel):
    """系统配置表"""
    __tablename__ = 'sys_config'
    
    # 基础字段
    config_key = Column(String(200), nullable=False, comment='配置键名')
    config_value = Column(Text, comment='配置值')
    config_type = Column(SQLEnum(ConfigType), default=ConfigType.STRING, nullable=False, comment='配置类型')
    
    # 分组和环境
    group_id = Column(BigInteger, ForeignKey('sys_config_group.id', ondelete='SET NULL'), comment='分组ID')
    environment = Column(SQLEnum(Environment), default=Environment.PROD, nullable=False, comment='环境标识')
    
    # 配置属性
    description = Column(Text, comment='配置描述')
    default_value = Column(Text, comment='默认值')
    example_value = Column(Text, comment='示例值')
    validation_rule = Column(JSON, comment='验证规则')
    
    # 配置标识
    is_core = Column(Boolean, default=False, nullable=False, comment='是否核心配置')
    is_enabled = Column(Boolean, default=True, nullable=False, comment='是否启用')
    is_encrypted = Column(Boolean, default=False, nullable=False, comment='是否加密存储')
    is_required = Column(Boolean, default=False, nullable=False, comment='是否必填')
    
    # 扩展字段
    tags = Column(JSON, comment='配置标签')
    sort_order = Column(Integer, default=0, comment='排序序号')
    
    # 软删除
    deleted_at = Column(DateTime, comment='删除时间')
    
    # 关系
    group = relationship("ConfigGroup", back_populates="configs")
    
    def __repr__(self):
        return f"<SystemConfig(key={self.config_key}, type={self.config_type}, env={self.environment})>"
    
    @property
    def is_deleted(self):
        """是否已删除"""
        return self.deleted_at is not None
    
    def soft_delete(self):
        """软删除"""
        self.deleted_at = func.now()
        self.is_enabled = False
    
    def restore(self):
        """恢复删除"""
        self.deleted_at = None
        self.is_enabled = True


class ConfigGroup(BaseModel):
    """配置分组表"""
    __tablename__ = 'sys_config_group'
    
    group_name = Column(String(100), nullable=False, comment='分组名称')
    group_code = Column(String(100), nullable=False, unique=True, comment='分组代码')
    parent_id = Column(BigInteger, default=0, comment='父分组ID')
    level = Column(Integer, default=1, comment='分组层级')
    path = Column(String(500), comment='分组路径')
    sort_order = Column(Integer, default=0, comment='排序序号')
    description = Column(Text, comment='分组描述')
    icon = Column(String(100), comment='分组图标')
    color = Column(String(20), comment='分组颜色')
    is_system = Column(Boolean, default=False, nullable=False, comment='是否系统分组')
    is_enabled = Column(Boolean, default=True, nullable=False, comment='是否启用')
    
    # 关系
    configs = relationship("SystemConfig", back_populates="group")
    
    def __repr__(self):
        return f"<ConfigGroup(name={self.group_name}, code={self.group_code}, level={self.level})>"


class ConfigHistory(BaseModel):
    """配置变更历史表"""
    __tablename__ = 'sys_config_history'
    
    config_id = Column(BigInteger, ForeignKey('sys_config.id', ondelete='CASCADE'), nullable=False, comment='配置ID')
    config_key = Column(String(200), nullable=False, comment='配置键名')
    environment = Column(SQLEnum(Environment), nullable=False, comment='环境标识')
    
    # 变更信息
    old_value = Column(Text, comment='变更前值')
    new_value = Column(Text, comment='变更后值')
    change_type = Column(SQLEnum(enum.Enum('ChangeType', 'CREATE UPDATE DELETE ROLLBACK')), 
                        nullable=False, comment='变更类型')
    change_reason = Column(Text, comment='变更原因')
    change_summary = Column(String(500), comment='变更摘要')
    impact_scope = Column(JSON, comment='影响范围')
    
    # 操作信息
    operator_id = Column(BigInteger, comment='操作人ID')
    operator_ip = Column(String(45), comment='操作IP')
    user_agent = Column(Text, comment='用户代理')
    audit_id = Column(BigInteger, comment='关联审核ID')
    
    def __repr__(self):
        return f"<ConfigHistory(config_key={self.config_key}, type={self.change_type}, env={self.environment})>"


class ConfigAudit(BaseModel):
    """配置审核表"""
    __tablename__ = 'sys_config_audit'
    
    audit_code = Column(String(50), nullable=False, unique=True, comment='审核编号')
    config_id = Column(BigInteger, ForeignKey('sys_config.id', ondelete='SET NULL'), comment='配置ID')
    config_key = Column(String(200), nullable=False, comment='配置键名')
    environment = Column(SQLEnum(Environment), nullable=False, comment='环境标识')
    
    # 变更信息
    old_value = Column(Text, comment='变更前值')
    new_value = Column(Text, comment='变更后值')
    change_type = Column(SQLEnum(enum.Enum('ChangeType', 'CREATE UPDATE DELETE')), 
                        nullable=False, comment='变更类型')
    
    # 审核状态
    audit_status = Column(SQLEnum(enum.Enum('AuditStatus', 'PENDING IN_REVIEW APPROVED REJECTED CANCELLED')), 
                         default='PENDING', comment='审核状态')
    priority = Column(SQLEnum(enum.Enum('Priority', 'LOW MEDIUM HIGH URGENT')), 
                     default='MEDIUM', comment='优先级')
    
    # 审核人员
    apply_user_id = Column(BigInteger, nullable=False, comment='申请人ID')
    audit_user_id = Column(BigInteger, comment='审核人ID')
    
    # 审核内容
    apply_reason = Column(Text, comment='申请原因')
    audit_reason = Column(Text, comment='审核意见')
    impact_assessment = Column(JSON, comment='影响评估')
    risk_level = Column(SQLEnum(enum.Enum('RiskLevel', 'LOW MEDIUM HIGH CRITICAL')), comment='风险等级')
    estimated_downtime = Column(Integer, comment='预估停机时间(分钟)')
    rollback_plan = Column(Text, comment='回滚计划')
    
    # 时间字段
    applied_at = Column(DateTime, default=func.now(), comment='申请时间')
    audited_at = Column(DateTime, comment='审核时间')
    executed_at = Column(DateTime, comment='执行时间')
    expires_at = Column(DateTime, comment='过期时间')
    
    def __repr__(self):
        return f"<ConfigAudit(code={self.audit_code}, status={self.audit_status}, key={self.config_key})>"


class SystemEnvironment(BaseModel):
    """环境管理表"""
    __tablename__ = 'sys_environment'
    
    env_name = Column(String(100), nullable=False, comment='环境名称')
    env_code = Column(SQLEnum(Environment), nullable=False, unique=True, comment='环境代码')
    description = Column(Text, comment='环境描述')
    base_url = Column(String(500), comment='环境基础URL')
    database_config = Column(JSON, comment='数据库配置')
    
    # 环境状态
    is_active = Column(Boolean, default=True, nullable=False, comment='是否激活')
    is_default = Column(Boolean, default=False, nullable=False, comment='是否默认环境')
    sort_order = Column(Integer, default=0, comment='排序序号')
    
    def __repr__(self):
        return f"<SystemEnvironment(name={self.env_name}, code={self.env_code}, active={self.is_active})>"


class ConfigPermission(BaseModel):
    """配置权限表"""
    __tablename__ = 'sys_config_permission'
    
    user_id = Column(BigInteger, nullable=False, comment='用户ID')
    permission_type = Column(SQLEnum(PermissionType), nullable=False, comment='权限类型')
    
    # 权限目标（互斥）
    config_id = Column(BigInteger, ForeignKey('sys_config.id', ondelete='CASCADE'), comment='配置ID')
    group_id = Column(BigInteger, ForeignKey('sys_config_group.id', ondelete='CASCADE'), comment='分组ID')
    environment = Column(SQLEnum(Environment), comment='环境标识')
    
    # 权限操作列表
    actions = Column(JSON, nullable=False, comment='允许的操作列表')
    
    # 授权信息
    granted_by = Column(BigInteger, comment='授权人ID')
    granted_at = Column(DateTime, default=func.now(), comment='授权时间')
    expires_at = Column(DateTime, comment='过期时间')
    
    # 软删除
    deleted_at = Column(DateTime, comment='删除时间')
    
    def __repr__(self):
        return f"<ConfigPermission(user_id={self.user_id}, type={self.permission_type}, env={self.environment})>"
    
    @property
    def is_expired(self):
        """是否已过期"""
        if self.expires_at is None:
            return False
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_deleted(self):
        """是否已删除"""
        return self.deleted_at is not None
    
    def soft_delete(self):
        """软删除"""
        self.deleted_at = func.now()