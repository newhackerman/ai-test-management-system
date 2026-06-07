"""
AI告警配置相关的Pydantic模式
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.ai_alert_config import AlertType, AlertLevel, AlertStatus, NotificationChannel


class AlertConfigBase(BaseModel):
    """告警配置基础模式"""
    name: str = Field(..., min_length=1, max_length=200, description="告警名称")
    description: Optional[str] = Field(None, max_length=1000, description="告警描述")
    alert_type: AlertType = Field(..., description="告警类型")
    alert_level: AlertLevel = Field(AlertLevel.WARNING, description="告警级别")
    status: AlertStatus = Field(AlertStatus.ACTIVE, description="告警状态")
    
    # 触发条件
    threshold_value: Optional[float] = Field(None, description="阈值")
    threshold_operator: str = Field(">=", pattern="^(>=|<=|==|!=|>|<)$", description="阈值操作符")
    threshold_unit: Optional[str] = Field(None, max_length=50, description="阈值单位")
    
    # 时间窗口
    time_window_minutes: int = Field(5, ge=1, le=1440, description="时间窗口(分钟)")
    evaluation_frequency_minutes: int = Field(1, ge=1, le=60, description="评估频率(分钟)")
    
    # 适用范围
    target_providers: Optional[List[str]] = Field(None, description="目标AI提供商列表")
    target_models: Optional[List[str]] = Field(None, description="目标模型列表")
    target_users: Optional[List[int]] = Field(None, description="目标用户列表")
    target_departments: Optional[List[str]] = Field(None, description="目标部门列表")
    
    # 通知配置
    notification_channels: Optional[List[NotificationChannel]] = Field(None, description="通知渠道")
    notification_recipients: Optional[List[str]] = Field(None, description="通知接收者")
    notification_template: Optional[str] = Field(None, description="通知模板")
    
    # 抑制配置
    suppress_duration_minutes: int = Field(60, ge=1, le=10080, description="抑制时长(分钟)")
    max_alerts_per_hour: int = Field(10, ge=1, le=1000, description="每小时最大告警数")
    
    # 自动处理
    auto_resolve: bool = Field(False, description="是否自动解决")
    auto_resolve_threshold: Optional[float] = Field(None, description="自动解决阈值")
    auto_action: Optional[Dict[str, Any]] = Field(None, description="自动处理动作配置")

    @validator('threshold_value')
    def validate_threshold_value(cls, v, values):
        """验证阈值"""
        alert_type = values.get('alert_type')
        if alert_type in [AlertType.COST_BUDGET, AlertType.TOKEN_QUOTA, AlertType.REQUEST_QUOTA]:
            if v is None or v <= 0:
                raise ValueError(f"{alert_type} 类型的告警必须设置正数阈值")
        return v

    @validator('auto_resolve_threshold')
    def validate_auto_resolve_threshold(cls, v, values):
        """验证自动解决阈值"""
        if values.get('auto_resolve') and v is None:
            raise ValueError("启用自动解决时必须设置自动解决阈值")
        return v


class AlertConfigCreate(AlertConfigBase):
    """创建告警配置"""
    pass


class AlertConfigUpdate(BaseModel):
    """更新告警配置"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="告警名称")
    description: Optional[str] = Field(None, max_length=1000, description="告警描述")
    alert_level: Optional[AlertLevel] = Field(None, description="告警级别")
    status: Optional[AlertStatus] = Field(None, description="告警状态")
    
    # 触发条件
    threshold_value: Optional[float] = Field(None, description="阈值")
    threshold_operator: Optional[str] = Field(None, pattern="^(>=|<=|==|!=|>|<)$", description="阈值操作符")
    threshold_unit: Optional[str] = Field(None, max_length=50, description="阈值单位")
    
    # 时间窗口
    time_window_minutes: Optional[int] = Field(None, ge=1, le=1440, description="时间窗口(分钟)")
    evaluation_frequency_minutes: Optional[int] = Field(None, ge=1, le=60, description="评估频率(分钟)")
    
    # 适用范围
    target_providers: Optional[List[str]] = Field(None, description="目标AI提供商列表")
    target_models: Optional[List[str]] = Field(None, description="目标模型列表")
    target_users: Optional[List[int]] = Field(None, description="目标用户列表")
    target_departments: Optional[List[str]] = Field(None, description="目标部门列表")
    
    # 通知配置
    notification_channels: Optional[List[NotificationChannel]] = Field(None, description="通知渠道")
    notification_recipients: Optional[List[str]] = Field(None, description="通知接收者")
    notification_template: Optional[str] = Field(None, description="通知模板")
    
    # 抑制配置
    suppress_duration_minutes: Optional[int] = Field(None, ge=1, le=10080, description="抑制时长(分钟)")
    max_alerts_per_hour: Optional[int] = Field(None, ge=1, le=1000, description="每小时最大告警数")
    
    # 自动处理
    auto_resolve: Optional[bool] = Field(None, description="是否自动解决")
    auto_resolve_threshold: Optional[float] = Field(None, description="自动解决阈值")
    auto_action: Optional[Dict[str, Any]] = Field(None, description="自动处理动作配置")


class AlertConfigResponse(AlertConfigBase):
    """告警配置响应"""
    id: int
    
    # 统计信息
    trigger_count: int = Field(0, description="触发次数")
    last_triggered_at: Optional[datetime] = Field(None, description="最后触发时间")
    last_resolved_at: Optional[datetime] = Field(None, description="最后解决时间")
    
    # 创建者信息
    created_by: Optional[int] = Field(None, description="创建者用户ID")
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlertConfigList(BaseModel):
    """告警配置列表"""
    items: List[AlertConfigResponse]
    total: int
    skip: int
    limit: int


class AlertHistoryResponse(BaseModel):
    """告警历史响应"""
    id: int
    alert_config_id: int
    alert_level: AlertLevel
    alert_message: str
    alert_details: Optional[Dict[str, Any]] = None
    
    # 触发信息
    triggered_value: Optional[float] = None
    threshold_value: Optional[float] = None
    trigger_context: Optional[Dict[str, Any]] = None
    
    # 状态信息
    status: AlertStatus
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_note: Optional[str] = None
    
    # 通知信息
    notification_sent: bool = False
    notification_channels_used: Optional[List[str]] = None
    notification_failures: Optional[Dict[str, Any]] = None
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlertHistoryList(BaseModel):
    """告警历史列表"""
    items: List[AlertHistoryResponse]
    total: int
    skip: int
    limit: int


class AlertSuppressionCreate(BaseModel):
    """创建告警抑制"""
    alert_config_id: int = Field(..., description="告警配置ID")
    suppression_reason: str = Field(..., min_length=1, max_length=500, description="抑制原因")
    suppress_duration_minutes: int = Field(..., ge=1, le=10080, description="抑制时长(分钟)")


class AlertSuppressionResponse(BaseModel):
    """告警抑制响应"""
    id: int
    alert_config_id: int
    suppression_reason: str
    suppressed_until: datetime
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlertTestRequest(BaseModel):
    """告警测试请求"""
    test_value: float = Field(..., description="测试值")
    test_context: Optional[Dict[str, Any]] = Field(None, description="测试上下文")


class AlertTestResponse(BaseModel):
    """告警测试响应"""
    would_trigger: bool = Field(..., description="是否会触发告警")
    alert_message: str = Field(..., description="告警消息")
    alert_level: AlertLevel = Field(..., description="告警级别")
    test_details: Dict[str, Any] = Field(..., description="测试详情")
    tested_at: datetime = Field(default_factory=datetime.utcnow, description="测试时间")


class AlertStatsResponse(BaseModel):
    """告警统计响应"""
    total_configs: int = Field(0, description="总配置数")
    active_configs: int = Field(0, description="激活配置数")
    triggered_today: int = Field(0, description="今日触发数")
    resolved_today: int = Field(0, description="今日解决数")
    
    # 按类型统计
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    by_level: Dict[str, int] = Field(default_factory=dict, description="按级别统计")
    by_status: Dict[str, int] = Field(default_factory=dict, description="按状态统计")
    
    # 趋势数据
    daily_triggers: List[Dict[str, Any]] = Field(default_factory=list, description="每日触发趋势")
    top_triggered_configs: List[Dict[str, Any]] = Field(default_factory=list, description="触发最多的配置")


class NotificationChannelConfig(BaseModel):
    """通知渠道配置"""
    channel: NotificationChannel = Field(..., description="通知渠道")
    enabled: bool = Field(True, description="是否启用")
    config: Dict[str, Any] = Field(default_factory=dict, description="渠道配置")
    
    class Config:
        # 示例配置
        json_schema_extra = {
            "examples": [
                {
                    "channel": "email",
                    "enabled": True,
                    "config": {
                        "smtp_server": "smtp.example.com",
                        "smtp_port": 587,
                        "username": "alerts@example.com",
                        "password": "password",
                        "use_tls": True
                    }
                },
                {
                    "channel": "webhook",
                    "enabled": True,
                    "config": {
                        "url": "https://hooks.slack.com/services/...",
                        "method": "POST",
                        "headers": {"Content-Type": "application/json"},
                        "timeout": 30
                    }
                }
            ]
        }


class AlertTemplateVariable(BaseModel):
    """告警模板变量"""
    name: str = Field(..., description="变量名")
    description: str = Field(..., description="变量描述")
    example: str = Field(..., description="示例值")


class AlertTemplateResponse(BaseModel):
    """告警模板响应"""
    alert_type: AlertType = Field(..., description="告警类型")
    default_template: str = Field(..., description="默认模板")
    available_variables: List[AlertTemplateVariable] = Field(..., description="可用变量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_type": "cost_budget",
                "default_template": "告警: {alert_name} 触发\n当前值: {current_value} {unit}\n阈值: {threshold_value} {unit}\n触发时间: {triggered_at}",
                "available_variables": [
                    {"name": "alert_name", "description": "告警名称", "example": "系统成本预算告警"},
                    {"name": "current_value", "description": "当前值", "example": "85.5"},
                    {"name": "threshold_value", "description": "阈值", "example": "80.0"},
                    {"name": "unit", "description": "单位", "example": "USD"},
                    {"name": "triggered_at", "description": "触发时间", "example": "2024-01-15 10:30:00"}
                ]
            }
        }