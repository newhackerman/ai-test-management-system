"""
AI告警配置模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from enum import Enum

from .base import BaseModel


class AlertType(str, Enum):
    """告警类型枚举"""
    COST_BUDGET = "cost_budget"           # 成本预算告警
    TOKEN_QUOTA = "token_quota"           # Token配额告警
    REQUEST_QUOTA = "request_quota"       # 请求配额告警
    RESPONSE_TIME = "response_time"       # 响应时间告警
    ERROR_RATE = "error_rate"             # 错误率告警
    MODEL_HEALTH = "model_health"         # 模型健康状态告警
    CONCURRENT_LIMIT = "concurrent_limit" # 并发限制告警
    SYSTEM_RESOURCE = "system_resource"   # 系统资源告警


class AlertLevel(str, Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    """告警状态枚举"""
    ACTIVE = "active"       # 激活
    INACTIVE = "inactive"   # 未激活
    TRIGGERED = "triggered" # 已触发
    RESOLVED = "resolved"   # 已解决
    DISABLED = "disabled"   # 已禁用


class NotificationChannel(str, Enum):
    """通知渠道枚举"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    SYSTEM_NOTIFICATION = "system_notification"


class AIAlertConfig(BaseModel):
    """AI告警配置模型"""
    __tablename__ = "ai_alert_configs"
    
    # 基本信息
    name = Column(String(200), nullable=False, comment="告警名称")
    description = Column(Text, nullable=True, comment="告警描述")
    alert_type = Column(SQLEnum(AlertType), nullable=False, comment="告警类型")
    alert_level = Column(SQLEnum(AlertLevel), nullable=False, default=AlertLevel.WARNING, comment="告警级别")
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE, comment="告警状态")
    
    # 触发条件
    threshold_value = Column(Float, nullable=True, comment="阈值")
    threshold_operator = Column(String(10), nullable=True, default=">=", comment="阈值操作符 (>=, <=, ==, !=)")
    threshold_unit = Column(String(50), nullable=True, comment="阈值单位")
    
    # 时间窗口
    time_window_minutes = Column(Integer, nullable=True, default=5, comment="时间窗口(分钟)")
    evaluation_frequency_minutes = Column(Integer, nullable=True, default=1, comment="评估频率(分钟)")
    
    # 适用范围
    target_providers = Column(JSON, nullable=True, comment="目标AI提供商列表")
    target_models = Column(JSON, nullable=True, comment="目标模型列表")
    target_users = Column(JSON, nullable=True, comment="目标用户列表")
    target_departments = Column(JSON, nullable=True, comment="目标部门列表")
    
    # 通知配置
    notification_channels = Column(JSON, nullable=True, comment="通知渠道配置")
    notification_recipients = Column(JSON, nullable=True, comment="通知接收者")
    notification_template = Column(Text, nullable=True, comment="通知模板")
    
    # 抑制配置
    suppress_duration_minutes = Column(Integer, nullable=True, default=60, comment="抑制时长(分钟)")
    max_alerts_per_hour = Column(Integer, nullable=True, default=10, comment="每小时最大告警数")
    
    # 自动处理
    auto_resolve = Column(Boolean, default=False, comment="是否自动解决")
    auto_resolve_threshold = Column(Float, nullable=True, comment="自动解决阈值")
    auto_action = Column(JSON, nullable=True, comment="自动处理动作配置")
    
    # 统计信息
    trigger_count = Column(Integer, default=0, comment="触发次数")
    last_triggered_at = Column(DateTime, nullable=True, comment="最后触发时间")
    last_resolved_at = Column(DateTime, nullable=True, comment="最后解决时间")
    
    # 创建者信息
    created_by = Column(Integer, nullable=True, comment="创建者用户ID")
    
    def __repr__(self):
        return f"<AIAlertConfig(id={self.id}, name='{self.name}', type='{self.alert_type}')>"


class AIAlertHistory(BaseModel):
    """AI告警历史记录模型"""
    __tablename__ = "ai_alert_history"
    
    # 关联告警配置
    alert_config_id = Column(Integer, nullable=False, comment="告警配置ID")
    
    # 告警信息
    alert_level = Column(SQLEnum(AlertLevel), nullable=False, comment="告警级别")
    alert_message = Column(Text, nullable=False, comment="告警消息")
    alert_details = Column(JSON, nullable=True, comment="告警详细信息")
    
    # 触发信息
    triggered_value = Column(Float, nullable=True, comment="触发时的值")
    threshold_value = Column(Float, nullable=True, comment="阈值")
    trigger_context = Column(JSON, nullable=True, comment="触发上下文")
    
    # 状态信息
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.TRIGGERED, comment="告警状态")
    resolved_at = Column(DateTime, nullable=True, comment="解决时间")
    resolved_by = Column(Integer, nullable=True, comment="解决者用户ID")
    resolution_note = Column(Text, nullable=True, comment="解决备注")
    
    # 通知信息
    notification_sent = Column(Boolean, default=False, comment="是否已发送通知")
    notification_channels_used = Column(JSON, nullable=True, comment="使用的通知渠道")
    notification_failures = Column(JSON, nullable=True, comment="通知失败信息")
    
    def __repr__(self):
        return f"<AIAlertHistory(id={self.id}, config_id={self.alert_config_id}, level='{self.alert_level}')>"


class AIAlertSuppression(BaseModel):
    """AI告警抑制记录模型"""
    __tablename__ = "ai_alert_suppressions"
    
    # 关联告警配置
    alert_config_id = Column(Integer, nullable=False, comment="告警配置ID")
    
    # 抑制信息
    suppression_reason = Column(String(500), nullable=False, comment="抑制原因")
    suppressed_until = Column(DateTime, nullable=False, comment="抑制到期时间")
    
    # 创建者信息
    created_by = Column(Integer, nullable=False, comment="创建者用户ID")
    
    def __repr__(self):
        return f"<AIAlertSuppression(id={self.id}, config_id={self.alert_config_id})>"