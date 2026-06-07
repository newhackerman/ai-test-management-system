"""
性能监控中间件 - 监控API响应时间并确保90%请求在5秒内完成

本模块实现了性能监控中间件，用于：
1. 监控所有API请求的响应时间
2. 记录性能指标和统计数据
3. 识别慢请求并发出告警
4. 提供性能分析和报告功能
5. 确保90%的请求在5秒内完成

技术特性：
- 实时性能监控
- 统计分析和报告
- 自动告警机制
- 性能优化建议
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """性能等级"""
    EXCELLENT = "excellent"  # < 1秒
    GOOD = "good"           # 1-2秒
    ACCEPTABLE = "acceptable"  # 2-5秒
    SLOW = "slow"           # 5-10秒
    CRITICAL = "critical"   # > 10秒


@dataclass
class RequestMetrics:
    """请求性能指标"""
    path: str
    method: str
    status_code: int
    response_time: float
    timestamp: datetime
    user_id: Optional[int] = None
    request_size: int = 0
    response_size: int = 0
    performance_level: PerformanceLevel = PerformanceLevel.GOOD
    
    def __post_init__(self):
        """计算性能等级"""
        if self.response_time < 1.0:
            self.performance_level = PerformanceLevel.EXCELLENT
        elif self.response_time < 2.0:
            self.performance_level = PerformanceLevel.GOOD
        elif self.response_time < 5.0:
            self.performance_level = PerformanceLevel.ACCEPTABLE
        elif self.response_time < 10.0:
            self.performance_level = PerformanceLevel.SLOW
        else:
            self.performance_level = PerformanceLevel.CRITICAL


@dataclass
class PerformanceStats:
    """性能统计数据"""
    total_requests: int = 0
    avg_response_time: float = 0.0
    median_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = 0.0
    
    # 性能等级分布
    excellent_count: int = 0
    good_count: int = 0
    acceptable_count: int = 0
    slow_count: int = 0
    critical_count: int = 0
    
    # 5秒内完成的请求比例
    within_5s_count: int = 0
    within_5s_percentage: float = 0.0
    
    # 错误统计
    error_count: int = 0
    error_rate: float = 0.0
    
    # 时间窗口
    window_start: datetime = field(default_factory=datetime.utcnow)
    window_end: datetime = field(default_factory=datetime.utcnow)
    
    def calculate_percentages(self):
        """计算百分比"""
        if self.total_requests > 0:
            self.within_5s_percentage = (self.within_5s_count / self.total_requests) * 100
            self.error_rate = (self.error_count / self.total_requests) * 100


@dataclass
class PerformanceAlert:
    """性能告警"""
    alert_type: str
    message: str
    severity: str  # low, medium, high, critical
    timestamp: datetime
    metrics: Dict[str, Any]
    threshold_value: float
    actual_value: float


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history_size: int = 10000, alert_threshold_5s: float = 90.0):
        """
        初始化性能监控器
        
        Args:
            max_history_size: 最大历史记录数量
            alert_threshold_5s: 5秒内完成请求的告警阈值（百分比）
        """
        self.max_history_size = max_history_size
        self.alert_threshold_5s = alert_threshold_5s
        
        # 请求历史记录（使用deque实现固定大小的环形缓冲区）
        self.request_history: deque = deque(maxlen=max_history_size)
        
        # 按路径分组的性能统计
        self.path_stats: Dict[str, List[RequestMetrics]] = defaultdict(list)
        
        # 实时统计数据
        self.current_stats = PerformanceStats()
        
        # 告警历史
        self.alert_history: List[PerformanceAlert] = []
        
        # 性能阈值配置
        self.thresholds = {
            "response_time_warning": 3.0,  # 3秒警告
            "response_time_critical": 5.0,  # 5秒严重
            "response_time_emergency": 10.0,  # 10秒紧急
            "error_rate_warning": 5.0,  # 5%错误率警告
            "error_rate_critical": 10.0,  # 10%错误率严重
            "within_5s_threshold": alert_threshold_5s,  # 5秒内完成阈值
        }
        
        # 告警回调函数
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # 统计更新锁
        self._stats_lock = asyncio.Lock()
        
        logger.info(f"Performance monitor initialized with max_history_size={max_history_size}, "
                   f"alert_threshold_5s={alert_threshold_5s}%")
    
    async def record_request(self, metrics: RequestMetrics):
        """
        记录请求性能指标
        
        Args:
            metrics: 请求性能指标
        """
        async with self._stats_lock:
            # 添加到历史记录
            self.request_history.append(metrics)
            
            # 添加到路径统计
            path_key = f"{metrics.method} {metrics.path}"
            self.path_stats[path_key].append(metrics)
            
            # 限制每个路径的历史记录数量
            if len(self.path_stats[path_key]) > 1000:
                self.path_stats[path_key] = self.path_stats[path_key][-1000:]
            
            # 更新实时统计
            await self._update_current_stats(metrics)
            
            # 检查告警条件
            await self._check_alerts(metrics)
    
    async def _update_current_stats(self, new_metrics: RequestMetrics):
        """
        更新当前统计数据
        
        Args:
            new_metrics: 新的请求指标
        """
        stats = self.current_stats
        
        # 更新基础统计
        stats.total_requests += 1
        
        # 更新响应时间统计
        response_times = [m.response_time for m in self.request_history]
        if response_times:
            stats.avg_response_time = statistics.mean(response_times)
            stats.median_response_time = statistics.median(response_times)
            stats.max_response_time = max(response_times)
            stats.min_response_time = min(response_times)
        else:
            # 如果没有历史数据，重置为0
            stats.min_response_time = 0.0
            
            # 计算百分位数
            sorted_times = sorted(response_times)
            stats.p95_response_time = self._calculate_percentile(sorted_times, 95)
            stats.p99_response_time = self._calculate_percentile(sorted_times, 99)
        
        # 更新性能等级统计
        if new_metrics.performance_level == PerformanceLevel.EXCELLENT:
            stats.excellent_count += 1
        elif new_metrics.performance_level == PerformanceLevel.GOOD:
            stats.good_count += 1
        elif new_metrics.performance_level == PerformanceLevel.ACCEPTABLE:
            stats.acceptable_count += 1
        elif new_metrics.performance_level == PerformanceLevel.SLOW:
            stats.slow_count += 1
        elif new_metrics.performance_level == PerformanceLevel.CRITICAL:
            stats.critical_count += 1
        
        # 更新5秒内完成统计
        if new_metrics.response_time <= 5.0:
            stats.within_5s_count += 1
        
        # 更新错误统计
        if new_metrics.status_code >= 400:
            stats.error_count += 1
        
        # 计算百分比
        stats.calculate_percentages()
        
        # 更新时间窗口
        if self.request_history:
            stats.window_start = min(m.timestamp for m in self.request_history)
            stats.window_end = max(m.timestamp for m in self.request_history)
    
    def _calculate_percentile(self, sorted_values: List[float], percentile: int) -> float:
        """
        计算百分位数
        
        Args:
            sorted_values: 已排序的数值列表
            percentile: 百分位数（0-100）
            
        Returns:
            float: 百分位数值
        """
        if not sorted_values:
            return 0.0
        
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)
        
        if lower_index == upper_index:
            return sorted_values[lower_index]
        
        # 线性插值
        weight = index - lower_index
        return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
    
    async def _check_alerts(self, metrics: RequestMetrics):
        """
        检查告警条件
        
        Args:
            metrics: 请求性能指标
        """
        alerts = []
        
        # 检查单个请求响应时间告警
        if metrics.response_time >= self.thresholds["response_time_emergency"]:
            alerts.append(PerformanceAlert(
                alert_type="response_time_emergency",
                message=f"紧急：请求响应时间过长 {metrics.path} ({metrics.response_time:.2f}s)",
                severity="critical",
                timestamp=datetime.utcnow(),
                metrics={"path": metrics.path, "method": metrics.method},
                threshold_value=self.thresholds["response_time_emergency"],
                actual_value=metrics.response_time
            ))
        elif metrics.response_time >= self.thresholds["response_time_critical"]:
            alerts.append(PerformanceAlert(
                alert_type="response_time_critical",
                message=f"严重：请求响应时间过长 {metrics.path} ({metrics.response_time:.2f}s)",
                severity="high",
                timestamp=datetime.utcnow(),
                metrics={"path": metrics.path, "method": metrics.method},
                threshold_value=self.thresholds["response_time_critical"],
                actual_value=metrics.response_time
            ))
        elif metrics.response_time >= self.thresholds["response_time_warning"]:
            alerts.append(PerformanceAlert(
                alert_type="response_time_warning",
                message=f"警告：请求响应时间较长 {metrics.path} ({metrics.response_time:.2f}s)",
                severity="medium",
                timestamp=datetime.utcnow(),
                metrics={"path": metrics.path, "method": metrics.method},
                threshold_value=self.thresholds["response_time_warning"],
                actual_value=metrics.response_time
            ))
        
        # 检查5秒内完成率告警（每100个请求检查一次）
        if self.current_stats.total_requests % 100 == 0:
            within_5s_percentage = self.current_stats.within_5s_percentage
            if within_5s_percentage < self.thresholds["within_5s_threshold"]:
                alerts.append(PerformanceAlert(
                    alert_type="within_5s_threshold",
                    message=f"严重：5秒内完成请求比例过低 ({within_5s_percentage:.1f}%)",
                    severity="critical",
                    timestamp=datetime.utcnow(),
                    metrics={"total_requests": self.current_stats.total_requests},
                    threshold_value=self.thresholds["within_5s_threshold"],
                    actual_value=within_5s_percentage
                ))
        
        # 检查错误率告警
        if self.current_stats.total_requests % 50 == 0:  # 每50个请求检查一次
            error_rate = self.current_stats.error_rate
            if error_rate >= self.thresholds["error_rate_critical"]:
                alerts.append(PerformanceAlert(
                    alert_type="error_rate_critical",
                    message=f"严重：错误率过高 ({error_rate:.1f}%)",
                    severity="critical",
                    timestamp=datetime.utcnow(),
                    metrics={"total_requests": self.current_stats.total_requests},
                    threshold_value=self.thresholds["error_rate_critical"],
                    actual_value=error_rate
                ))
            elif error_rate >= self.thresholds["error_rate_warning"]:
                alerts.append(PerformanceAlert(
                    alert_type="error_rate_warning",
                    message=f"警告：错误率较高 ({error_rate:.1f}%)",
                    severity="medium",
                    timestamp=datetime.utcnow(),
                    metrics={"total_requests": self.current_stats.total_requests},
                    threshold_value=self.thresholds["error_rate_warning"],
                    actual_value=error_rate
                ))
        
        # 处理告警
        for alert in alerts:
            await self._handle_alert(alert)
    
    async def _handle_alert(self, alert: PerformanceAlert):
        """
        处理告警
        
        Args:
            alert: 性能告警
        """
        # 添加到告警历史
        self.alert_history.append(alert)
        
        # 限制告警历史数量
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # 记录日志
        log_level = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL
        }.get(alert.severity, logging.WARNING)
        
        logger.log(log_level, f"Performance Alert: {alert.message}")
        
        # 调用告警回调函数
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """
        添加告警回调函数
        
        Args:
            callback: 告警回调函数
        """
        self.alert_callbacks.append(callback)
    
    def get_current_stats(self) -> PerformanceStats:
        """获取当前统计数据"""
        return self.current_stats
    
    def get_path_stats(self, path: str = None) -> Dict[str, Any]:
        """
        获取路径性能统计
        
        Args:
            path: 指定路径，如果为None则返回所有路径统计
            
        Returns:
            Dict[str, Any]: 路径性能统计
        """
        if path:
            metrics_list = self.path_stats.get(path, [])
            if not metrics_list:
                return {}
            
            response_times = [m.response_time for m in metrics_list]
            return {
                "path": path,
                "total_requests": len(metrics_list),
                "avg_response_time": statistics.mean(response_times),
                "median_response_time": statistics.median(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times),
                "within_5s_count": sum(1 for m in metrics_list if m.response_time <= 5.0),
                "within_5s_percentage": (sum(1 for m in metrics_list if m.response_time <= 5.0) / len(metrics_list)) * 100,
                "error_count": sum(1 for m in metrics_list if m.status_code >= 400),
                "error_rate": (sum(1 for m in metrics_list if m.status_code >= 400) / len(metrics_list)) * 100
            }
        else:
            # 返回所有路径的统计摘要
            path_summaries = {}
            for path_key, metrics_list in self.path_stats.items():
                if metrics_list:
                    response_times = [m.response_time for m in metrics_list]
                    path_summaries[path_key] = {
                        "total_requests": len(metrics_list),
                        "avg_response_time": statistics.mean(response_times),
                        "within_5s_percentage": (sum(1 for m in metrics_list if m.response_time <= 5.0) / len(metrics_list)) * 100,
                        "error_rate": (sum(1 for m in metrics_list if m.status_code >= 400) / len(metrics_list)) * 100
                    }
            
            return path_summaries
    
    def get_recent_alerts(self, hours: int = 24) -> List[PerformanceAlert]:
        """
        获取最近的告警
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            List[PerformanceAlert]: 最近的告警列表
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        生成性能报告
        
        Returns:
            Dict[str, Any]: 性能报告
        """
        stats = self.current_stats
        
        # 计算性能等级分布
        total_requests = stats.total_requests
        performance_distribution = {}
        if total_requests > 0:
            performance_distribution = {
                "excellent": (stats.excellent_count / total_requests) * 100,
                "good": (stats.good_count / total_requests) * 100,
                "acceptable": (stats.acceptable_count / total_requests) * 100,
                "slow": (stats.slow_count / total_requests) * 100,
                "critical": (stats.critical_count / total_requests) * 100
            }
        
        # 获取最慢的路径
        slowest_paths = []
        for path_key, metrics_list in self.path_stats.items():
            if metrics_list:
                avg_time = statistics.mean([m.response_time for m in metrics_list])
                slowest_paths.append({
                    "path": path_key,
                    "avg_response_time": avg_time,
                    "total_requests": len(metrics_list)
                })
        
        slowest_paths.sort(key=lambda x: x["avg_response_time"], reverse=True)
        slowest_paths = slowest_paths[:10]  # 取前10个最慢的路径
        
        # 获取最近的告警
        recent_alerts = self.get_recent_alerts(24)
        
        return {
            "summary": {
                "total_requests": stats.total_requests,
                "avg_response_time": stats.avg_response_time,
                "median_response_time": stats.median_response_time,
                "p95_response_time": stats.p95_response_time,
                "p99_response_time": stats.p99_response_time,
                "within_5s_percentage": stats.within_5s_percentage,
                "error_rate": stats.error_rate,
                "window_duration": (stats.window_end - stats.window_start).total_seconds() if stats.window_end > stats.window_start else 0
            },
            "performance_distribution": performance_distribution,
            "slowest_paths": slowest_paths,
            "recent_alerts": [
                {
                    "type": alert.alert_type,
                    "message": alert.message,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                    "threshold": alert.threshold_value,
                    "actual": alert.actual_value
                }
                for alert in recent_alerts
            ],
            "thresholds": self.thresholds,
            "generated_at": datetime.utcnow().isoformat()
        }


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""
    
    def __init__(self, app: ASGIApp, monitor: PerformanceMonitor = None):
        """
        初始化性能监控中间件
        
        Args:
            app: ASGI应用
            monitor: 性能监控器实例，如果为None则创建默认实例
        """
        super().__init__(app)
        self.monitor = monitor or PerformanceMonitor()
        
        # 排除的路径（不进行性能监控）
        self.excluded_paths = {
            "/health",
            "/metrics",
            "/favicon.ico",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
        
        logger.info("Performance monitoring middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求并记录性能指标
        
        Args:
            request: HTTP请求
            call_next: 下一个中间件或应用
            
        Returns:
            Response: HTTP响应
        """
        # 检查是否需要排除此路径
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取请求大小
        request_size = self._get_request_size(request)
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 获取响应大小
            response_size = self._get_response_size(response)
            
            # 创建性能指标
            metrics = RequestMetrics(
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=response_time,
                timestamp=datetime.utcnow(),
                user_id=self._get_user_id(request),
                request_size=request_size,
                response_size=response_size
            )
            
            # 记录性能指标
            await self.monitor.record_request(metrics)
            
            # 添加性能头信息
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"
            response.headers["X-Performance-Level"] = metrics.performance_level.value
            
            return response
            
        except Exception as e:
            # 计算响应时间（即使出错也要记录）
            response_time = time.time() - start_time
            
            # 创建错误指标
            metrics = RequestMetrics(
                path=request.url.path,
                method=request.method,
                status_code=500,
                response_time=response_time,
                timestamp=datetime.utcnow(),
                user_id=self._get_user_id(request),
                request_size=request_size,
                response_size=0
            )
            
            # 记录性能指标
            await self.monitor.record_request(metrics)
            
            # 重新抛出异常
            raise e
    
    def _should_exclude_path(self, path: str) -> bool:
        """
        检查是否应该排除此路径
        
        Args:
            path: 请求路径
            
        Returns:
            bool: 是否排除
        """
        # 精确匹配
        if path in self.excluded_paths:
            return True
        
        # 前缀匹配
        excluded_prefixes = ["/docs", "/redoc", "/static", "/assets"]
        for prefix in excluded_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _get_request_size(self, request: Request) -> int:
        """
        获取请求大小
        
        Args:
            request: HTTP请求
            
        Returns:
            int: 请求大小（字节）
        """
        try:
            content_length = request.headers.get("content-length")
            if content_length:
                return int(content_length)
        except (ValueError, TypeError):
            pass
        
        return 0
    
    def _get_response_size(self, response: Response) -> int:
        """
        获取响应大小
        
        Args:
            response: HTTP响应
            
        Returns:
            int: 响应大小（字节）
        """
        try:
            content_length = response.headers.get("content-length")
            if content_length:
                return int(content_length)
        except (ValueError, TypeError):
            pass
        
        return 0
    
    def _get_user_id(self, request: Request) -> Optional[int]:
        """
        从请求中获取用户ID
        
        Args:
            request: HTTP请求
            
        Returns:
            Optional[int]: 用户ID
        """
        try:
            # 尝试从请求状态中获取用户信息
            if hasattr(request.state, 'user') and hasattr(request.state.user, 'id'):
                return request.state.user.id
            
            # 尝试从JWT token中获取用户ID（简化实现）
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # 这里应该解析JWT token获取用户ID
                # 为了简化，暂时返回None
                pass
        except Exception:
            pass
        
        return None


# 全局性能监控器实例
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def setup_performance_monitoring(app: FastAPI, monitor: PerformanceMonitor = None) -> PerformanceMonitor:
    """
    设置性能监控
    
    Args:
        app: FastAPI应用实例
        monitor: 性能监控器实例，如果为None则使用全局实例
        
    Returns:
        PerformanceMonitor: 性能监控器实例
    """
    if monitor is None:
        monitor = get_performance_monitor()
    
    # 添加性能监控中间件
    app.add_middleware(PerformanceMiddleware, monitor=monitor)
    
    # 添加性能监控API端点
    @app.get("/api/v1/performance/stats")
    async def get_performance_stats():
        """获取性能统计"""
        return monitor.get_current_stats()
    
    @app.get("/api/v1/performance/report")
    async def get_performance_report():
        """获取性能报告"""
        return monitor.get_performance_report()
    
    @app.get("/api/v1/performance/alerts")
    async def get_performance_alerts(hours: int = 24):
        """获取性能告警"""
        return monitor.get_recent_alerts(hours)
    
    @app.get("/api/v1/performance/paths")
    async def get_path_performance(path: str = None):
        """获取路径性能统计"""
        return monitor.get_path_stats(path)
    
    logger.info("Performance monitoring setup completed")
    return monitor