"""
监控和告警配置模块

提供应用监控、健康检查、告警配置等功能。
支持Prometheus指标收集、健康状态检查、告警规则配置等。
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import Field, ConfigDict

# Handle BaseSettings import for different Pydantic versions
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        # Fallback for older versions or missing pydantic-settings
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AlertSeverity(str, Enum):
    """告警严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class HealthStatus(str, Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class AlertRule:
    """告警规则配置"""
    name: str
    condition: str
    severity: AlertSeverity
    description: str
    threshold: float
    duration: int  # 持续时间(秒)
    enabled: bool = True

@dataclass
class HealthCheck:
    """健康检查配置"""
    name: str
    endpoint: str
    timeout: int
    interval: int
    retries: int
    expected_status: int = 200

class MonitoringSettings(BaseSettings):
    """监控配置类"""
    
    # 基础监控配置
    monitoring_enabled: bool = Field(default=True, description="启用监控")
    metrics_enabled: bool = Field(default=True, description="启用指标收集")
    prometheus_enabled: bool = Field(default=True, description="启用Prometheus")
    prometheus_port: int = Field(default=9090, description="Prometheus端口")
    
    # 健康检查配置
    health_check_enabled: bool = Field(default=True, description="启用健康检查")
    health_check_interval: int = Field(default=30, description="健康检查间隔(秒)")
    health_check_timeout: int = Field(default=10, description="健康检查超时(秒)")
    health_check_retries: int = Field(default=3, description="健康检查重试次数")
    
    # 告警配置
    alerting_enabled: bool = Field(default=True, description="启用告警")
    alert_webhook_url: Optional[str] = Field(default=None, description="告警Webhook URL")
    alert_email_enabled: bool = Field(default=False, description="启用邮件告警")
    alert_email_recipients: List[str] = Field(default_factory=list, description="告警邮件收件人")
    
    # 性能监控阈值
    cpu_threshold: float = Field(default=80.0, description="CPU使用率告警阈值(%)")
    memory_threshold: float = Field(default=85.0, description="内存使用率告警阈值(%)")
    disk_threshold: float = Field(default=90.0, description="磁盘使用率告警阈值(%)")
    
    # API监控阈值
    api_response_time_threshold: float = Field(default=5.0, description="API响应时间告警阈值(秒)")
    api_error_rate_threshold: float = Field(default=5.0, description="API错误率告警阈值(%)")
    api_request_rate_threshold: int = Field(default=1000, description="API请求速率告警阈值(req/min)")
    
    # AI服务监控阈值
    ai_cost_daily_threshold: float = Field(default=1000.0, description="AI每日成本告警阈值")
    ai_cost_monthly_threshold: float = Field(default=30000.0, description="AI每月成本告警阈值")
    ai_response_time_threshold: float = Field(default=10.0, description="AI响应时间告警阈值(秒)")
    ai_error_rate_threshold: float = Field(default=10.0, description="AI错误率告警阈值(%)")
    
    model_config = ConfigDict(
        env_prefix="MONITORING_",
        extra="ignore"  # Ignore extra environment variables
    )

# 默认监控配置实例
monitoring_settings = MonitoringSettings()

# 默认告警规则配置
DEFAULT_ALERT_RULES = [
    AlertRule(
        name="high_cpu_usage",
        condition="cpu_usage > threshold",
        severity=AlertSeverity.HIGH,
        description="CPU使用率过高",
        threshold=80.0,
        duration=300  # 5分钟
    ),
    AlertRule(
        name="high_memory_usage", 
        condition="memory_usage > threshold",
        severity=AlertSeverity.HIGH,
        description="内存使用率过高",
        threshold=85.0,
        duration=300
    ),
    AlertRule(
        name="high_disk_usage",
        condition="disk_usage > threshold", 
        severity=AlertSeverity.CRITICAL,
        description="磁盘使用率过高",
        threshold=90.0,
        duration=60
    ),
    AlertRule(
        name="api_slow_response",
        condition="api_response_time > threshold",
        severity=AlertSeverity.MEDIUM,
        description="API响应时间过慢",
        threshold=5.0,
        duration=120
    ),
    AlertRule(
        name="api_high_error_rate",
        condition="api_error_rate > threshold",
        severity=AlertSeverity.HIGH,
        description="API错误率过高", 
        threshold=5.0,
        duration=180
    ),
    AlertRule(
        name="ai_cost_exceeded",
        condition="ai_daily_cost > threshold",
        severity=AlertSeverity.CRITICAL,
        description="AI服务每日成本超限",
        threshold=1000.0,
        duration=0
    ),
    AlertRule(
        name="database_connection_failed",
        condition="database_connection_status != healthy",
        severity=AlertSeverity.CRITICAL,
        description="数据库连接失败",
        threshold=0,
        duration=30
    ),
    AlertRule(
        name="redis_connection_failed",
        condition="redis_connection_status != healthy",
        severity=AlertSeverity.HIGH,
        description="Redis连接失败",
        threshold=0,
        duration=60
    )
]

# 默认健康检查配置
DEFAULT_HEALTH_CHECKS = [
    HealthCheck(
        name="api_health",
        endpoint="/health",
        timeout=10,
        interval=30,
        retries=3
    ),
    HealthCheck(
        name="database_health",
        endpoint="/health/database",
        timeout=15,
        interval=60,
        retries=3
    ),
    HealthCheck(
        name="redis_health",
        endpoint="/health/redis",
        timeout=10,
        interval=60,
        retries=3
    ),
    HealthCheck(
        name="ai_service_health",
        endpoint="/health/ai-services",
        timeout=20,
        interval=120,
        retries=2
    )
]

# Prometheus指标配置
PROMETHEUS_METRICS = {
    # HTTP请求指标
    'http_requests_total': {
        'name': 'http_requests_total',
        'description': 'Total number of HTTP requests',
        'type': 'counter',
        'labels': ['method', 'endpoint', 'status']
    },
    'http_request_duration_seconds': {
        'name': 'http_request_duration_seconds',
        'description': 'HTTP request duration in seconds',
        'type': 'histogram',
        'labels': ['method', 'endpoint']
    },
    
    # 系统资源指标
    'system_cpu_usage': {
        'name': 'system_cpu_usage',
        'description': 'System CPU usage percentage',
        'type': 'gauge'
    },
    'system_memory_usage': {
        'name': 'system_memory_usage',
        'description': 'System memory usage percentage', 
        'type': 'gauge'
    },
    'system_disk_usage': {
        'name': 'system_disk_usage',
        'description': 'System disk usage percentage',
        'type': 'gauge'
    },
    
    # AI服务指标
    'ai_requests_total': {
        'name': 'ai_requests_total',
        'description': 'Total number of AI service requests',
        'type': 'counter',
        'labels': ['provider', 'model', 'status']
    },
    'ai_request_duration_seconds': {
        'name': 'ai_request_duration_seconds',
        'description': 'AI service request duration in seconds',
        'type': 'histogram',
        'labels': ['provider', 'model']
    },
    'ai_cost_total': {
        'name': 'ai_cost_total',
        'description': 'Total AI service cost in USD',
        'type': 'counter',
        'labels': ['provider', 'model']
    },
    
    # 数据库指标
    'database_connections_active': {
        'name': 'database_connections_active',
        'description': 'Number of active database connections',
        'type': 'gauge'
    },
    'database_query_duration_seconds': {
        'name': 'database_query_duration_seconds',
        'description': 'Database query duration in seconds',
        'type': 'histogram'
    },
    
    # 缓存指标
    'cache_hits_total': {
        'name': 'cache_hits_total',
        'description': 'Total number of cache hits',
        'type': 'counter'
    },
    'cache_misses_total': {
        'name': 'cache_misses_total',
        'description': 'Total number of cache misses',
        'type': 'counter'
    }
}

def get_monitoring_settings() -> MonitoringSettings:
    """获取监控配置"""
    return monitoring_settings

def get_alert_rules() -> List[AlertRule]:
    """获取告警规则"""
    return DEFAULT_ALERT_RULES

def get_health_checks() -> List[HealthCheck]:
    """获取健康检查配置"""
    return DEFAULT_HEALTH_CHECKS

def get_prometheus_metrics() -> Dict[str, Any]:
    """获取Prometheus指标配置"""
    return PROMETHEUS_METRICS