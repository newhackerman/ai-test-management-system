"""
健康监控相关的Pydantic模式
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class HealthStatusEnum(str, Enum):
    """健康状态枚举"""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class AlertSeverityEnum(str, Enum):
    """告警严重程度枚举"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertTypeEnum(str, Enum):
    """告警类型枚举"""
    CONSECUTIVE_FAILURES = "CONSECUTIVE_FAILURES"
    HIGH_RESPONSE_TIME = "HIGH_RESPONSE_TIME"
    LOW_SUCCESS_RATE = "LOW_SUCCESS_RATE"
    LOW_AVAILABILITY = "LOW_AVAILABILITY"
    API_ERROR = "API_ERROR"
    TIMEOUT = "TIMEOUT"


class ModelStatusInfo(BaseModel):
    """模型状态信息"""
    config_id: int = Field(..., description="配置ID")
    provider: str = Field(..., description="服务提供商")
    model_name: str = Field(..., description="模型名称")
    display_name: str = Field(..., description="显示名称")
    status: HealthStatusEnum = Field(..., description="健康状态")
    last_check: Optional[datetime] = Field(None, description="最后检查时间")
    response_time: Optional[float] = Field(None, description="响应时间（秒）")
    success_rate: Optional[float] = Field(None, description="成功率")
    consecutive_failures: int = Field(0, description="连续失败次数")


class HealthDashboardResponse(BaseModel):
    """健康监控仪表板响应"""
    total_models: int = Field(..., description="总模型数")
    healthy_models: int = Field(..., description="健康模型数")
    unhealthy_models: int = Field(..., description="不健康模型数")
    unknown_models: int = Field(..., description="未知状态模型数")
    system_health_score: float = Field(..., description="系统健康分数（0-100）")
    model_status: List[ModelStatusInfo] = Field(..., description="模型状态列表")
    last_updated: datetime = Field(..., description="最后更新时间")


class HealthMetricsResponse(BaseModel):
    """健康指标响应"""
    config_id: int = Field(..., description="配置ID")
    provider: str = Field(..., description="服务提供商")
    model_name: str = Field(..., description="模型名称")
    display_name: str = Field(..., description="显示名称")
    response_time: float = Field(..., description="平均响应时间（秒）")
    success_rate: float = Field(..., description="成功率")
    error_rate: float = Field(..., description="错误率")
    availability: float = Field(..., description="可用性")
    throughput: float = Field(..., description="吞吐量（请求/分钟）")
    consecutive_failures: int = Field(..., description="连续失败次数")
    total_checks: int = Field(..., description="总检查次数")
    successful_checks: int = Field(..., description="成功检查次数")
    failed_checks: int = Field(..., description="失败检查次数")
    last_check: datetime = Field(..., description="最后检查时间")
    is_healthy: bool = Field(..., description="是否健康")


class HealthAlertResponse(BaseModel):
    """健康告警响应"""
    config_id: int = Field(..., description="配置ID")
    provider: str = Field(..., description="服务提供商")
    model_name: str = Field(..., description="模型名称")
    display_name: str = Field(..., description="显示名称")
    alert_type: AlertTypeEnum = Field(..., description="告警类型")
    severity: AlertSeverityEnum = Field(..., description="严重程度")
    message: str = Field(..., description="告警消息")
    value: Optional[float] = Field(None, description="相关数值")
    created_at: datetime = Field(..., description="创建时间")
    is_active: bool = Field(True, description="是否活跃")


class HealthDataPoint(BaseModel):
    """健康数据点"""
    timestamp: datetime = Field(..., description="时间戳")
    response_time: float = Field(..., description="响应时间（秒）")
    success_rate: float = Field(..., description="成功率")
    availability: float = Field(..., description="可用性")
    error_rate: float = Field(..., description="错误率")


class HealthTrendResponse(BaseModel):
    """健康趋势响应"""
    config_id: int = Field(..., description="配置ID")
    provider: str = Field(..., description="服务提供商")
    model_name: str = Field(..., description="模型名称")
    display_name: str = Field(..., description="显示名称")
    data_points: List[HealthDataPoint] = Field(..., description="数据点列表")
    period_hours: int = Field(..., description="时间周期（小时）")


class ProviderHealthStats(BaseModel):
    """提供商健康统计"""
    total: int = Field(..., description="总数")
    healthy: int = Field(..., description="健康数")
    unhealthy: int = Field(..., description="不健康数")


class SystemHealthResponse(BaseModel):
    """系统健康响应"""
    system_status: HealthStatusEnum = Field(..., description="系统状态")
    health_score: float = Field(..., description="健康分数（0-100）")
    total_models: int = Field(..., description="总模型数")
    enabled_models: int = Field(..., description="启用模型数")
    healthy_models: int = Field(..., description="健康模型数")
    unhealthy_models: int = Field(..., description="不健康模型数")
    avg_response_time: float = Field(..., description="平均响应时间（秒）")
    avg_success_rate: float = Field(..., description="平均成功率")
    avg_availability: float = Field(..., description="平均可用性")
    provider_stats: Dict[str, ProviderHealthStats] = Field(..., description="提供商统计")
    last_updated: datetime = Field(..., description="最后更新时间")


class HealthCheckScheduleRequest(BaseModel):
    """健康检查调度请求"""
    config_ids: Optional[List[int]] = Field(None, description="指定的配置ID列表，为空则检查所有")
    immediate: bool = Field(True, description="是否立即执行")
    notify_on_completion: bool = Field(False, description="完成时是否通知")


class HealthCheckScheduleResponse(BaseModel):
    """健康检查调度响应"""
    scheduled: bool = Field(..., description="是否已调度")
    config_ids: Optional[List[int]] = Field(None, description="调度的配置ID列表")
    scheduled_at: datetime = Field(..., description="调度时间")
    message: str = Field(..., description="调度消息")


class HealthConfigurationRequest(BaseModel):
    """健康监控配置请求"""
    check_interval: Optional[int] = Field(None, ge=60, le=3600, description="检查间隔（秒）")
    timeout: Optional[float] = Field(None, ge=5.0, le=120.0, description="超时时间（秒）")
    max_retries: Optional[int] = Field(None, ge=1, le=10, description="最大重试次数")
    failure_threshold: Optional[int] = Field(None, ge=1, le=10, description="失败阈值")
    warning_response_time: Optional[float] = Field(None, ge=1.0, le=30.0, description="警告响应时间阈值")
    critical_response_time: Optional[float] = Field(None, ge=5.0, le=60.0, description="严重响应时间阈值")
    enable_alerts: Optional[bool] = Field(None, description="是否启用告警")


class HealthConfigurationResponse(BaseModel):
    """健康监控配置响应"""
    check_interval: int = Field(..., description="检查间隔（秒）")
    timeout: float = Field(..., description="超时时间（秒）")
    max_retries: int = Field(..., description="最大重试次数")
    failure_threshold: int = Field(..., description="失败阈值")
    warning_response_time: float = Field(..., description="警告响应时间阈值")
    critical_response_time: float = Field(..., description="严重响应时间阈值")
    enable_alerts: bool = Field(..., description="是否启用告警")
    updated_at: datetime = Field(..., description="更新时间")


class HealthReportRequest(BaseModel):
    """健康报告请求"""
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    config_ids: Optional[List[int]] = Field(None, description="指定的配置ID列表")
    providers: Optional[List[str]] = Field(None, description="指定的提供商列表")
    include_trends: bool = Field(True, description="是否包含趋势数据")
    include_alerts: bool = Field(True, description="是否包含告警数据")
    format: str = Field("json", description="报告格式（json/pdf/excel）")


class HealthReportResponse(BaseModel):
    """健康报告响应"""
    report_id: str = Field(..., description="报告ID")
    status: str = Field(..., description="报告状态")
    download_url: Optional[str] = Field(None, description="下载链接")
    created_at: datetime = Field(..., description="创建时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")