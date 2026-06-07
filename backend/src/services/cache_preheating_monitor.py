"""
缓存预热监控服务

本模块提供缓存预热机制的监控功能，包括：
1. 性能指标监控
2. 告警管理
3. 健康状态检查
4. 统计报告生成
5. 异常检测和处理

主要功能：
- 实时监控预热效果
- 自动检测异常情况
- 生成性能报告
- 发送告警通知
- 优化建议生成
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..config.cache_preheating_config import (
    MONITORING_CONFIG,
    PreheatingConfig,
    get_preheating_config
)
from ..utils.redis_client import RedisCache, get_redis_client
from ..services.cache_preheating_service import get_cache_preheating_service

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """指标类型"""
    CACHE_HIT_RATE = "cache_hit_rate"
    RESPONSE_TIME = "response_time"
    TASK_SUCCESS_RATE = "task_success_rate"
    MEMORY_USAGE = "memory_usage"
    QUEUE_SIZE = "queue_size"
    ACTIVE_PATTERNS = "active_patterns"


@dataclass
class MetricValue:
    """指标值"""
    metric_type: MetricType
    value: float
    timestamp: datetime
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    
    def get_severity(self) -> AlertSeverity:
        """获取告警严重程度"""
        if self.threshold_critical and self.value >= self.threshold_critical:
            return AlertSeverity.CRITICAL
        elif self.threshold_warning and self.value >= self.threshold_warning:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO


@dataclass
class Alert:
    """告警信息"""
    alert_id: str
    metric_type: MetricType
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class HealthStatus:
    """健康状态"""
    overall_health: str  # excellent, good, fair, poor
    health_score: int    # 0-100
    issues: List[str]
    recommendations: List[str]
    last_check: datetime


class CachePreheatingMonitor:
    """缓存预热监控服务"""
    
    def __init__(self, config: Optional[PreheatingConfig] = None):
        self.config = config or get_preheating_config()
        self.cache = RedisCache("preheating_monitor")
        self.redis_client = None
        
        # 监控状态
        self.monitoring_enabled = True
        self.check_interval = 300  # 5分钟
        
        # 指标存储
        self.metrics_history = {}  # 指标历史数据
        self.active_alerts = {}    # 活跃告警
        self.alert_history = []    # 告警历史
        
        # 告警限流
        self.alert_rate_limits = {}  # 告警频率限制
        
        # 性能基线
        self.performance_baseline = {
            "cache_hit_rate": 0.8,
            "response_time": 0.5,
            "task_success_rate": 0.9
        }
    
    async def initialize(self):
        """初始化监控服务"""
        try:
            self.redis_client = await get_redis_client()
            
            # 加载历史数据
            await self._load_monitoring_data()
            
            logger.info("缓存预热监控服务初始化成功")
            
        except Exception as e:
            logger.error(f"缓存预热监控服务初始化失败: {e}")
            raise
    
    async def start_monitoring(self):
        """启动监控"""
        if not self.monitoring_enabled:
            logger.info("缓存预热监控已禁用")
            return
        
        logger.info("启动缓存预热监控")
        
        # 启动监控任务
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._alert_processor())
        asyncio.create_task(self._health_checker())
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.monitoring_enabled:
            try:
                # 收集指标
                await self._collect_metrics()
                
                # 检查阈值
                await self._check_thresholds()
                
                # 等待下一个检查周期
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟
    
    async def _collect_metrics(self):
        """收集监控指标"""
        try:
            current_time = datetime.utcnow()
            
            # 收集缓存命中率
            cache_hit_rate = await self._get_cache_hit_rate()
            await self._record_metric(MetricType.CACHE_HIT_RATE, cache_hit_rate, current_time)
            
            # 收集响应时间
            response_time = await self._get_average_response_time()
            await self._record_metric(MetricType.RESPONSE_TIME, response_time, current_time)
            
            # 收集任务成功率
            task_success_rate = await self._get_task_success_rate()
            await self._record_metric(MetricType.TASK_SUCCESS_RATE, task_success_rate, current_time)
            
            # 收集内存使用率
            memory_usage = await self._get_memory_usage()
            await self._record_metric(MetricType.MEMORY_USAGE, memory_usage, current_time)
            
            # 收集队列大小
            queue_size = await self._get_queue_size()
            await self._record_metric(MetricType.QUEUE_SIZE, queue_size, current_time)
            
            # 收集活跃模式数量
            active_patterns = await self._get_active_patterns_count()
            await self._record_metric(MetricType.ACTIVE_PATTERNS, active_patterns, current_time)
            
        except Exception as e:
            logger.error(f"收集监控指标失败: {e}")
    
    async def _get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        try:
            info = await self.redis_client.info('stats')
            hits = int(info.get('keyspace_hits', 0))
            misses = int(info.get('keyspace_misses', 0))
            total = hits + misses
            
            return hits / total if total > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"获取缓存命中率失败: {e}")
            return 0.0
    
    async def _get_average_response_time(self) -> float:
        """获取平均响应时间"""
        try:
            # 从预热服务获取响应时间统计
            preheating_service = await get_cache_preheating_service()
            
            # 计算最近完成任务的平均执行时间
            recent_tasks = preheating_service.completed_tasks[-10:]  # 最近10个任务
            
            if not recent_tasks:
                return 0.0
            
            total_time = 0
            count = 0
            
            for task in recent_tasks:
                if task.completed_at and task.created_at:
                    execution_time = (task.completed_at - task.created_at).total_seconds()
                    total_time += execution_time
                    count += 1
            
            return total_time / count if count > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"获取平均响应时间失败: {e}")
            return 0.0
    
    async def _get_task_success_rate(self) -> float:
        """获取任务成功率"""
        try:
            preheating_service = await get_cache_preheating_service()
            stats = preheating_service.stats
            
            total_tasks = stats.get("total_tasks", 0)
            successful_tasks = stats.get("successful_tasks", 0)
            
            return successful_tasks / total_tasks if total_tasks > 0 else 1.0
            
        except Exception as e:
            logger.warning(f"获取任务成功率失败: {e}")
            return 0.0
    
    async def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            import psutil
            
            # 获取当前进程内存使用
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # 计算使用率（相对于配置的最大内存）
            max_memory = self.config.max_memory_usage_mb
            usage_rate = memory_mb / max_memory
            
            return min(usage_rate, 1.0)  # 限制在1.0以内
            
        except Exception as e:
            logger.warning(f"获取内存使用率失败: {e}")
            return 0.0
    
    async def _get_queue_size(self) -> float:
        """获取队列大小"""
        try:
            preheating_service = await get_cache_preheating_service()
            return float(preheating_service.task_queue.qsize())
            
        except Exception as e:
            logger.warning(f"获取队列大小失败: {e}")
            return 0.0
    
    async def _get_active_patterns_count(self) -> float:
        """获取活跃模式数量"""
        try:
            preheating_service = await get_cache_preheating_service()
            return float(len(preheating_service.access_patterns))
            
        except Exception as e:
            logger.warning(f"获取活跃模式数量失败: {e}")
            return 0.0
    
    async def _record_metric(self, metric_type: MetricType, value: float, timestamp: datetime):
        """记录指标值"""
        # 获取阈值配置
        metric_config = MONITORING_CONFIG["metrics"].get(metric_type.value, {})
        
        metric_value = MetricValue(
            metric_type=metric_type,
            value=value,
            timestamp=timestamp,
            threshold_warning=metric_config.get("threshold_warning"),
            threshold_critical=metric_config.get("threshold_critical")
        )
        
        # 存储到历史记录
        if metric_type not in self.metrics_history:
            self.metrics_history[metric_type] = []
        
        self.metrics_history[metric_type].append(metric_value)
        
        # 限制历史记录数量
        max_history = 1000
        if len(self.metrics_history[metric_type]) > max_history:
            self.metrics_history[metric_type] = self.metrics_history[metric_type][-max_history:]
    
    async def _check_thresholds(self):
        """检查阈值告警"""
        for metric_type, metrics in self.metrics_history.items():
            if not metrics:
                continue
            
            latest_metric = metrics[-1]
            severity = latest_metric.get_severity()
            
            # 检查是否需要发送告警
            if severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]:
                await self._create_alert(latest_metric, severity)
            else:
                # 检查是否需要解决告警
                await self._resolve_alert(metric_type)
    
    async def _create_alert(self, metric: MetricValue, severity: AlertSeverity):
        """创建告警"""
        alert_key = f"{metric.metric_type.value}_{severity.value}"
        
        # 检查告警频率限制
        if not await self._check_alert_rate_limit(alert_key):
            return
        
        # 检查是否已有相同告警
        if alert_key in self.active_alerts:
            return
        
        # 创建告警
        alert = Alert(
            alert_id=f"{alert_key}_{int(time.time())}",
            metric_type=metric.metric_type,
            severity=severity,
            message=self._generate_alert_message(metric, severity),
            value=metric.value,
            threshold=metric.threshold_critical if severity == AlertSeverity.CRITICAL else metric.threshold_warning,
            timestamp=metric.timestamp
        )
        
        # 存储告警
        self.active_alerts[alert_key] = alert
        self.alert_history.append(alert)
        
        # 发送告警通知
        await self._send_alert_notification(alert)
        
        logger.warning(f"创建告警: {alert.message}")
    
    async def _resolve_alert(self, metric_type: MetricType):
        """解决告警"""
        # 查找相关的活跃告警
        keys_to_remove = []
        for alert_key, alert in self.active_alerts.items():
            if alert.metric_type == metric_type and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                keys_to_remove.append(alert_key)
                
                logger.info(f"告警已解决: {alert.message}")
        
        # 移除已解决的告警
        for key in keys_to_remove:
            del self.active_alerts[key]
    
    async def _check_alert_rate_limit(self, alert_key: str) -> bool:
        """检查告警频率限制"""
        rate_limit = MONITORING_CONFIG["alerts"]["rate_limit"]
        current_time = time.time()
        
        if alert_key in self.alert_rate_limits:
            last_alert_time = self.alert_rate_limits[alert_key]
            if current_time - last_alert_time < rate_limit:
                return False
        
        self.alert_rate_limits[alert_key] = current_time
        return True
    
    def _generate_alert_message(self, metric: MetricValue, severity: AlertSeverity) -> str:
        """生成告警消息"""
        metric_names = {
            MetricType.CACHE_HIT_RATE: "缓存命中率",
            MetricType.RESPONSE_TIME: "响应时间",
            MetricType.TASK_SUCCESS_RATE: "任务成功率",
            MetricType.MEMORY_USAGE: "内存使用率",
            MetricType.QUEUE_SIZE: "队列大小",
            MetricType.ACTIVE_PATTERNS: "活跃模式数量"
        }
        
        metric_name = metric_names.get(metric.metric_type, metric.metric_type.value)
        threshold = metric.threshold_critical if severity == AlertSeverity.CRITICAL else metric.threshold_warning
        
        if metric.metric_type == MetricType.CACHE_HIT_RATE:
            return f"{metric_name}过低: {metric.value:.2%} (阈值: {threshold:.2%})"
        elif metric.metric_type == MetricType.RESPONSE_TIME:
            return f"{metric_name}过高: {metric.value:.2f}秒 (阈值: {threshold:.2f}秒)"
        elif metric.metric_type == MetricType.TASK_SUCCESS_RATE:
            return f"{metric_name}过低: {metric.value:.2%} (阈值: {threshold:.2%})"
        elif metric.metric_type == MetricType.MEMORY_USAGE:
            return f"{metric_name}过高: {metric.value:.2%} (阈值: {threshold:.2%})"
        else:
            return f"{metric_name}异常: {metric.value} (阈值: {threshold})"
    
    async def _send_alert_notification(self, alert: Alert):
        """发送告警通知"""
        try:
            # 记录到日志
            log_level = {
                AlertSeverity.INFO: logging.INFO,
                AlertSeverity.WARNING: logging.WARNING,
                AlertSeverity.ERROR: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL
            }.get(alert.severity, logging.WARNING)
            
            logger.log(log_level, f"缓存预热告警: {alert.message}")
            
            # 存储到Redis（供其他服务查询）
            alert_data = asdict(alert)
            alert_data["timestamp"] = alert.timestamp.isoformat()
            if alert.resolved_at:
                alert_data["resolved_at"] = alert.resolved_at.isoformat()
            
            await self.cache.set(
                f"alert:{alert.alert_id}",
                alert_data,
                3600  # 1小时过期
            )
            
        except Exception as e:
            logger.error(f"发送告警通知失败: {e}")
    
    async def _alert_processor(self):
        """告警处理器"""
        while self.monitoring_enabled:
            try:
                # 清理过期告警
                await self._cleanup_expired_alerts()
                
                # 等待下一个处理周期
                await asyncio.sleep(300)  # 5分钟
                
            except Exception as e:
                logger.error(f"告警处理器异常: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired_alerts(self):
        """清理过期告警"""
        try:
            current_time = datetime.utcnow()
            expired_threshold = current_time - timedelta(hours=24)  # 24小时过期
            
            # 清理告警历史
            self.alert_history = [
                alert for alert in self.alert_history
                if alert.timestamp > expired_threshold
            ]
            
            # 限制告警历史数量
            max_history = 1000
            if len(self.alert_history) > max_history:
                self.alert_history = self.alert_history[-max_history:]
            
        except Exception as e:
            logger.warning(f"清理过期告警失败: {e}")
    
    async def _health_checker(self):
        """健康检查器"""
        while self.monitoring_enabled:
            try:
                # 执行健康检查
                health_status = await self.get_health_status()
                
                # 存储健康状态
                await self.cache.set("health_status", asdict(health_status), 300)
                
                # 等待下一个检查周期
                await asyncio.sleep(600)  # 10分钟
                
            except Exception as e:
                logger.error(f"健康检查器异常: {e}")
                await asyncio.sleep(300)
    
    async def get_health_status(self) -> HealthStatus:
        """获取健康状态"""
        try:
            health_score = 100
            issues = []
            recommendations = []
            
            # 检查缓存命中率
            cache_hit_rate = await self._get_cache_hit_rate()
            if cache_hit_rate < 0.5:
                health_score -= 30
                issues.append(f"缓存命中率过低: {cache_hit_rate:.2%}")
                recommendations.append("增加预热频率或优化缓存策略")
            elif cache_hit_rate < 0.7:
                health_score -= 15
                issues.append(f"缓存命中率较低: {cache_hit_rate:.2%}")
                recommendations.append("考虑调整预热策略")
            
            # 检查任务成功率
            task_success_rate = await self._get_task_success_rate()
            if task_success_rate < 0.6:
                health_score -= 25
                issues.append(f"任务成功率过低: {task_success_rate:.2%}")
                recommendations.append("检查预热任务配置和系统资源")
            elif task_success_rate < 0.8:
                health_score -= 10
                issues.append(f"任务成功率较低: {task_success_rate:.2%}")
                recommendations.append("优化任务执行逻辑")
            
            # 检查响应时间
            response_time = await self._get_average_response_time()
            if response_time > 3.0:
                health_score -= 20
                issues.append(f"响应时间过长: {response_time:.2f}秒")
                recommendations.append("优化查询性能或增加缓存")
            elif response_time > 1.0:
                health_score -= 10
                issues.append(f"响应时间较长: {response_time:.2f}秒")
                recommendations.append("考虑优化数据库查询")
            
            # 检查内存使用
            memory_usage = await self._get_memory_usage()
            if memory_usage > 0.9:
                health_score -= 15
                issues.append(f"内存使用率过高: {memory_usage:.2%}")
                recommendations.append("增加内存限制或优化内存使用")
            elif memory_usage > 0.8:
                health_score -= 5
                issues.append(f"内存使用率较高: {memory_usage:.2%}")
                recommendations.append("监控内存使用趋势")
            
            # 检查活跃告警
            active_alert_count = len(self.active_alerts)
            if active_alert_count > 5:
                health_score -= 20
                issues.append(f"活跃告警过多: {active_alert_count}个")
                recommendations.append("处理活跃告警")
            elif active_alert_count > 0:
                health_score -= 5
                issues.append(f"存在活跃告警: {active_alert_count}个")
            
            # 确定健康等级
            if health_score >= 90:
                overall_health = "excellent"
            elif health_score >= 70:
                overall_health = "good"
            elif health_score >= 50:
                overall_health = "fair"
            else:
                overall_health = "poor"
            
            return HealthStatus(
                overall_health=overall_health,
                health_score=max(0, health_score),
                issues=issues,
                recommendations=recommendations,
                last_check=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"健康状态检查失败: {e}")
            return HealthStatus(
                overall_health="unknown",
                health_score=0,
                issues=[f"健康检查失败: {str(e)}"],
                recommendations=["检查监控服务状态"],
                last_check=datetime.utcnow()
            )
    
    async def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取指标摘要"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            summary = {}
            
            for metric_type, metrics in self.metrics_history.items():
                # 过滤时间范围内的指标
                filtered_metrics = [
                    m for m in metrics
                    if m.timestamp >= start_time
                ]
                
                if not filtered_metrics:
                    continue
                
                values = [m.value for m in filtered_metrics]
                
                summary[metric_type.value] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "latest": values[-1],
                    "trend": self._calculate_trend(values)
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取指标摘要失败: {e}")
            return {}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "stable"
        
        # 简单的趋势计算：比较前半部分和后半部分的平均值
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid
        second_half_avg = sum(values[mid:]) / (len(values) - mid)
        
        diff_ratio = (second_half_avg - first_half_avg) / first_half_avg
        
        if diff_ratio > 0.1:
            return "increasing"
        elif diff_ratio < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        alerts = []
        for alert in self.active_alerts.values():
            alert_data = asdict(alert)
            alert_data["timestamp"] = alert.timestamp.isoformat()
            if alert.resolved_at:
                alert_data["resolved_at"] = alert.resolved_at.isoformat()
            alerts.append(alert_data)
        
        return alerts
    
    async def _load_monitoring_data(self):
        """加载监控数据"""
        try:
            # 加载告警历史
            alert_data = await self.cache.get("alert_history")
            if alert_data:
                # 重建告警对象
                for data in alert_data:
                    alert = Alert(**data)
                    self.alert_history.append(alert)
            
            logger.debug("监控数据加载完成")
            
        except Exception as e:
            logger.warning(f"加载监控数据失败: {e}")
    
    async def _save_monitoring_data(self):
        """保存监控数据"""
        try:
            # 保存告警历史
            alert_data = []
            for alert in self.alert_history[-100:]:  # 只保存最近100条
                data = asdict(alert)
                data["timestamp"] = alert.timestamp.isoformat()
                if alert.resolved_at:
                    data["resolved_at"] = alert.resolved_at.isoformat()
                alert_data.append(data)
            
            await self.cache.set("alert_history", alert_data, 86400)  # 24小时
            
            logger.debug("监控数据保存完成")
            
        except Exception as e:
            logger.warning(f"保存监控数据失败: {e}")
    
    async def stop_monitoring(self):
        """停止监控"""
        self.monitoring_enabled = False
        
        # 保存监控数据
        await self._save_monitoring_data()
        
        logger.info("缓存预热监控已停止")


# 全局监控服务实例
_monitor_service = None

async def get_cache_preheating_monitor() -> CachePreheatingMonitor:
    """获取缓存预热监控服务实例"""
    global _monitor_service
    
    if _monitor_service is None:
        _monitor_service = CachePreheatingMonitor()
        await _monitor_service.initialize()
    
    return _monitor_service


async def start_cache_preheating_monitoring():
    """启动缓存预热监控"""
    monitor = await get_cache_preheating_monitor()
    await monitor.start_monitoring()


async def stop_cache_preheating_monitoring():
    """停止缓存预热监控"""
    global _monitor_service
    if _monitor_service:
        await _monitor_service.stop_monitoring()