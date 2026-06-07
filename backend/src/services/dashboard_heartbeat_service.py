"""
仪表板心跳检测和重连服务

实现WebSocket连接的心跳检测、连接质量监控和自动重连功能
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Callable
from enum import Enum
import statistics

from ..models.websocket_connection import ConnectionStatus
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class ConnectionQuality(Enum):
    """连接质量等级"""
    EXCELLENT = "EXCELLENT"  # 优秀 (延迟 < 50ms, 丢包率 < 1%)
    GOOD = "GOOD"  # 良好 (延迟 < 100ms, 丢包率 < 3%)
    FAIR = "FAIR"  # 一般 (延迟 < 200ms, 丢包率 < 5%)
    POOR = "POOR"  # 较差 (延迟 < 500ms, 丢包率 < 10%)
    BAD = "BAD"  # 很差 (延迟 >= 500ms 或 丢包率 >= 10%)


class HeartbeatStatus(Enum):
    """心跳状态"""
    ACTIVE = "ACTIVE"  # 活跃
    SLOW = "SLOW"  # 缓慢
    TIMEOUT = "TIMEOUT"  # 超时
    FAILED = "FAILED"  # 失败


class ReconnectionStrategy(Enum):
    """重连策略"""
    IMMEDIATE = "IMMEDIATE"  # 立即重连
    LINEAR = "LINEAR"  # 线性退避
    EXPONENTIAL = "EXPONENTIAL"  # 指数退避
    FIXED_INTERVAL = "FIXED_INTERVAL"  # 固定间隔


class HeartbeatMetrics:
    """心跳指标类"""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.start_time = time.time()
        self.last_heartbeat_time = time.time()
        self.heartbeat_count = 0
        self.missed_heartbeats = 0
        self.total_heartbeats = 0
        
        # 延迟统计
        self.latency_samples: List[float] = []
        self.max_latency_samples = 100
        self.average_latency = 0.0
        self.min_latency = float('inf')
        self.max_latency = 0.0
        
        # 连接质量
        self.connection_quality = ConnectionQuality.GOOD
        self.quality_history: List[ConnectionQuality] = []
        self.max_quality_history = 50
        
        # 错误统计
        self.error_count = 0
        self.last_error_time = None
        self.consecutive_errors = 0
        
        # 重连统计
        self.reconnection_count = 0
        self.last_reconnection_time = None
        self.reconnection_success_rate = 1.0
    
    def record_heartbeat(self, latency: float):
        """记录心跳"""
        current_time = time.time()
        self.last_heartbeat_time = current_time
        self.heartbeat_count += 1
        self.total_heartbeats += 1
        self.consecutive_errors = 0
        
        # 记录延迟
        self.latency_samples.append(latency)
        if len(self.latency_samples) > self.max_latency_samples:
            self.latency_samples.pop(0)
        
        # 更新延迟统计
        self.average_latency = statistics.mean(self.latency_samples)
        self.min_latency = min(self.min_latency, latency)
        self.max_latency = max(self.max_latency, latency)
        
        # 更新连接质量
        self._update_connection_quality()
    
    def record_missed_heartbeat(self):
        """记录丢失的心跳"""
        self.missed_heartbeats += 1
        self.total_heartbeats += 1
        self.consecutive_errors += 1
        
        # 更新连接质量
        self._update_connection_quality()
    
    def record_error(self, error_message: str):
        """记录错误"""
        self.error_count += 1
        self.last_error_time = time.time()
        self.consecutive_errors += 1
        
        # 更新连接质量
        self._update_connection_quality()
    
    def record_reconnection(self, success: bool):
        """记录重连"""
        self.reconnection_count += 1
        self.last_reconnection_time = time.time()
        
        # 更新重连成功率
        if self.reconnection_count == 1:
            self.reconnection_success_rate = 1.0 if success else 0.0
        else:
            # 使用指数移动平均
            alpha = 0.1
            self.reconnection_success_rate = (
                alpha * (1.0 if success else 0.0) + 
                (1 - alpha) * self.reconnection_success_rate
            )
    
    def get_packet_loss_rate(self) -> float:
        """获取丢包率"""
        if self.total_heartbeats == 0:
            return 0.0
        return self.missed_heartbeats / self.total_heartbeats
    
    def get_uptime(self) -> float:
        """获取连接时长(秒)"""
        return time.time() - self.start_time
    
    def is_healthy(self) -> bool:
        """检查连接是否健康"""
        return (
            self.connection_quality in [ConnectionQuality.EXCELLENT, ConnectionQuality.GOOD] and
            self.consecutive_errors < 3 and
            self.get_packet_loss_rate() < 0.05
        )
    
    def get_heartbeat_status(self, timeout_seconds: int = 60) -> HeartbeatStatus:
        """获取心跳状态"""
        current_time = time.time()
        time_since_last = current_time - self.last_heartbeat_time
        
        if time_since_last > timeout_seconds * 2:
            return HeartbeatStatus.FAILED
        elif time_since_last > timeout_seconds:
            return HeartbeatStatus.TIMEOUT
        elif time_since_last > timeout_seconds * 0.5:
            return HeartbeatStatus.SLOW
        else:
            return HeartbeatStatus.ACTIVE
    
    def _update_connection_quality(self):
        """更新连接质量"""
        packet_loss_rate = self.get_packet_loss_rate()
        
        # 根据延迟和丢包率确定质量
        if self.average_latency < 50 and packet_loss_rate < 0.01:
            quality = ConnectionQuality.EXCELLENT
        elif self.average_latency < 100 and packet_loss_rate < 0.03:
            quality = ConnectionQuality.GOOD
        elif self.average_latency < 200 and packet_loss_rate < 0.05:
            quality = ConnectionQuality.FAIR
        elif self.average_latency < 500 and packet_loss_rate < 0.10:
            quality = ConnectionQuality.POOR
        else:
            quality = ConnectionQuality.BAD
        
        self.connection_quality = quality
        
        # 记录质量历史
        self.quality_history.append(quality)
        if len(self.quality_history) > self.max_quality_history:
            self.quality_history.pop(0)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'connection_id': self.connection_id,
            'uptime': self.get_uptime(),
            'heartbeat_count': self.heartbeat_count,
            'missed_heartbeats': self.missed_heartbeats,
            'total_heartbeats': self.total_heartbeats,
            'packet_loss_rate': self.get_packet_loss_rate(),
            'average_latency': self.average_latency,
            'min_latency': self.min_latency,
            'max_latency': self.max_latency,
            'connection_quality': self.connection_quality.value,
            'heartbeat_status': self.get_heartbeat_status().value,
            'error_count': self.error_count,
            'consecutive_errors': self.consecutive_errors,
            'reconnection_count': self.reconnection_count,
            'reconnection_success_rate': self.reconnection_success_rate,
            'is_healthy': self.is_healthy()
        }


class ReconnectionManager:
    """重连管理器"""
    
    def __init__(
        self,
        strategy: ReconnectionStrategy = ReconnectionStrategy.EXPONENTIAL,
        max_attempts: int = 10,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        self.strategy = strategy
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        
        # 重连状态
        self.reconnection_attempts: Dict[str, int] = {}
        self.last_attempt_time: Dict[str, float] = {}
        self.reconnection_callbacks: Dict[str, Callable] = {}
    
    def register_reconnection_callback(
        self,
        connection_id: str,
        callback: Callable[[str], None]
    ):
        """
        注册重连回调
        
        Args:
            connection_id: 连接ID
            callback: 重连回调函数
        """
        self.reconnection_callbacks[connection_id] = callback
    
    def unregister_reconnection_callback(self, connection_id: str):
        """
        取消注册重连回调
        
        Args:
            connection_id: 连接ID
        """
        self.reconnection_callbacks.pop(connection_id, None)
        self.reconnection_attempts.pop(connection_id, None)
        self.last_attempt_time.pop(connection_id, None)
    
    async def attempt_reconnection(self, connection_id: str) -> bool:
        """
        尝试重连
        
        Args:
            connection_id: 连接ID
            
        Returns:
            bool: 是否应该尝试重连
        """
        current_time = time.time()
        
        # 检查重连次数限制
        attempts = self.reconnection_attempts.get(connection_id, 0)
        if attempts >= self.max_attempts:
            logger.warning(f"Connection {connection_id} exceeded max reconnection attempts")
            return False
        
        # 计算重连延迟
        delay = self._calculate_delay(attempts)
        
        # 检查是否到了重连时间
        last_attempt = self.last_attempt_time.get(connection_id, 0)
        if current_time - last_attempt < delay:
            return False
        
        # 更新重连状态
        self.reconnection_attempts[connection_id] = attempts + 1
        self.last_attempt_time[connection_id] = current_time
        
        # 执行重连回调
        if connection_id in self.reconnection_callbacks:
            try:
                callback = self.reconnection_callbacks[connection_id]
                if asyncio.iscoroutinefunction(callback):
                    await callback(connection_id)
                else:
                    callback(connection_id)
                
                logger.info(f"Reconnection attempt {attempts + 1} for connection {connection_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error in reconnection callback: {e}")
                return False
        
        return False
    
    def reset_reconnection_state(self, connection_id: str):
        """
        重置重连状态
        
        Args:
            connection_id: 连接ID
        """
        self.reconnection_attempts.pop(connection_id, None)
        self.last_attempt_time.pop(connection_id, None)
    
    def _calculate_delay(self, attempts: int) -> float:
        """
        计算重连延迟
        
        Args:
            attempts: 重连次数
            
        Returns:
            float: 延迟时间(秒)
        """
        if self.strategy == ReconnectionStrategy.IMMEDIATE:
            return 0.0
        
        elif self.strategy == ReconnectionStrategy.LINEAR:
            delay = self.base_delay * (attempts + 1)
        
        elif self.strategy == ReconnectionStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempts)
        
        elif self.strategy == ReconnectionStrategy.FIXED_INTERVAL:
            delay = self.base_delay
        
        else:
            delay = self.base_delay
        
        return min(delay, self.max_delay)


class DashboardHeartbeatService:
    """仪表板心跳检测服务"""
    
    def __init__(
        self,
        heartbeat_interval: int = 30,
        timeout_threshold: int = 60,
        quality_check_interval: int = 300
    ):
        self.heartbeat_interval = heartbeat_interval
        self.timeout_threshold = timeout_threshold
        self.quality_check_interval = quality_check_interval
        
        # 心跳管理
        self.heartbeat_metrics: Dict[str, HeartbeatMetrics] = {}
        self.pending_heartbeats: Dict[str, Dict[str, float]] = {}  # connection_id -> {heartbeat_id: timestamp}
        
        # 重连管理
        self.reconnection_manager = ReconnectionManager()
        
        # 回调函数
        self.heartbeat_callbacks: Dict[str, Callable] = {}
        self.timeout_callbacks: Dict[str, Callable] = {}
        self.quality_change_callbacks: Dict[str, Callable] = {}
        
        # 后台任务
        self.background_tasks: Set[asyncio.Task] = set()
        
        # 统计信息
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'healthy_connections': 0,
            'total_heartbeats': 0,
            'missed_heartbeats': 0,
            'timeouts': 0,
            'reconnections': 0
        }
        
        # Redis客户端
        self.redis_client = get_redis_client()
        
        # 启动后台任务
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 心跳监控任务
        monitor_task = asyncio.create_task(self._heartbeat_monitor())
        self.background_tasks.add(monitor_task)
        monitor_task.add_done_callback(self.background_tasks.discard)
        
        # 连接质量检查任务
        quality_task = asyncio.create_task(self._quality_monitor())
        self.background_tasks.add(quality_task)
        quality_task.add_done_callback(self.background_tasks.discard)
        
        # 统计更新任务
        stats_task = asyncio.create_task(self._stats_updater())
        self.background_tasks.add(stats_task)
        stats_task.add_done_callback(self.background_tasks.discard)
    
    def register_connection(self, connection_id: str):
        """
        注册连接
        
        Args:
            connection_id: 连接ID
        """
        if connection_id not in self.heartbeat_metrics:
            self.heartbeat_metrics[connection_id] = HeartbeatMetrics(connection_id)
            self.pending_heartbeats[connection_id] = {}
            
            self.stats['total_connections'] += 1
            self.stats['active_connections'] = len(self.heartbeat_metrics)
            
            logger.info(f"Registered heartbeat monitoring for connection: {connection_id}")
    
    def unregister_connection(self, connection_id: str):
        """
        取消注册连接
        
        Args:
            connection_id: 连接ID
        """
        if connection_id in self.heartbeat_metrics:
            del self.heartbeat_metrics[connection_id]
            del self.pending_heartbeats[connection_id]
            
            # 清理回调
            self.heartbeat_callbacks.pop(connection_id, None)
            self.timeout_callbacks.pop(connection_id, None)
            self.quality_change_callbacks.pop(connection_id, None)
            
            # 清理重连管理
            self.reconnection_manager.unregister_reconnection_callback(connection_id)
            
            self.stats['active_connections'] = len(self.heartbeat_metrics)
            
            logger.info(f"Unregistered heartbeat monitoring for connection: {connection_id}")
    
    async def send_heartbeat(self, connection_id: str) -> str:
        """
        发送心跳
        
        Args:
            connection_id: 连接ID
            
        Returns:
            str: 心跳ID
        """
        if connection_id not in self.heartbeat_metrics:
            raise ValueError(f"Connection {connection_id} not registered")
        
        heartbeat_id = f"hb_{connection_id}_{int(time.time() * 1000)}"
        timestamp = time.time()
        
        # 记录待确认的心跳
        self.pending_heartbeats[connection_id][heartbeat_id] = timestamp
        
        # 清理过期的待确认心跳
        cutoff_time = timestamp - self.timeout_threshold
        expired_heartbeats = [
            hb_id for hb_id, hb_time in self.pending_heartbeats[connection_id].items()
            if hb_time < cutoff_time
        ]
        
        for hb_id in expired_heartbeats:
            del self.pending_heartbeats[connection_id][hb_id]
            # 记录丢失的心跳
            self.heartbeat_metrics[connection_id].record_missed_heartbeat()
            self.stats['missed_heartbeats'] += 1
        
        return heartbeat_id
    
    async def receive_heartbeat_response(
        self,
        connection_id: str,
        heartbeat_id: str
    ) -> bool:
        """
        接收心跳响应
        
        Args:
            connection_id: 连接ID
            heartbeat_id: 心跳ID
            
        Returns:
            bool: 是否成功处理
        """
        if connection_id not in self.heartbeat_metrics:
            return False
        
        if heartbeat_id not in self.pending_heartbeats[connection_id]:
            return False
        
        # 计算延迟
        sent_time = self.pending_heartbeats[connection_id][heartbeat_id]
        current_time = time.time()
        latency = (current_time - sent_time) * 1000  # 转换为毫秒
        
        # 记录心跳
        self.heartbeat_metrics[connection_id].record_heartbeat(latency)
        
        # 移除待确认心跳
        del self.pending_heartbeats[connection_id][heartbeat_id]
        
        # 更新统计
        self.stats['total_heartbeats'] += 1
        
        # 调用心跳回调
        if connection_id in self.heartbeat_callbacks:
            try:
                callback = self.heartbeat_callbacks[connection_id]
                if asyncio.iscoroutinefunction(callback):
                    await callback(connection_id, latency)
                else:
                    callback(connection_id, latency)
            except Exception as e:
                logger.error(f"Error in heartbeat callback: {e}")
        
        # 重置重连状态
        self.reconnection_manager.reset_reconnection_state(connection_id)
        
        return True
    
    def record_connection_error(self, connection_id: str, error_message: str):
        """
        记录连接错误
        
        Args:
            connection_id: 连接ID
            error_message: 错误消息
        """
        if connection_id in self.heartbeat_metrics:
            self.heartbeat_metrics[connection_id].record_error(error_message)
    
    def get_connection_metrics(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        获取连接指标
        
        Args:
            connection_id: 连接ID
            
        Returns:
            Optional[Dict[str, Any]]: 连接指标
        """
        if connection_id not in self.heartbeat_metrics:
            return None
        
        return self.heartbeat_metrics[connection_id].to_dict()
    
    def get_all_connection_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有连接指标
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有连接指标
        """
        return {
            connection_id: metrics.to_dict()
            for connection_id, metrics in self.heartbeat_metrics.items()
        }
    
    def is_connection_healthy(self, connection_id: str) -> bool:
        """
        检查连接是否健康
        
        Args:
            connection_id: 连接ID
            
        Returns:
            bool: 是否健康
        """
        if connection_id not in self.heartbeat_metrics:
            return False
        
        return self.heartbeat_metrics[connection_id].is_healthy()
    
    def get_connection_quality(self, connection_id: str) -> Optional[ConnectionQuality]:
        """
        获取连接质量
        
        Args:
            connection_id: 连接ID
            
        Returns:
            Optional[ConnectionQuality]: 连接质量
        """
        if connection_id not in self.heartbeat_metrics:
            return None
        
        return self.heartbeat_metrics[connection_id].connection_quality
    
    def register_heartbeat_callback(
        self,
        connection_id: str,
        callback: Callable[[str, float], None]
    ):
        """
        注册心跳回调
        
        Args:
            connection_id: 连接ID
            callback: 回调函数
        """
        self.heartbeat_callbacks[connection_id] = callback
    
    def register_timeout_callback(
        self,
        connection_id: str,
        callback: Callable[[str], None]
    ):
        """
        注册超时回调
        
        Args:
            connection_id: 连接ID
            callback: 回调函数
        """
        self.timeout_callbacks[connection_id] = callback
    
    def register_quality_change_callback(
        self,
        connection_id: str,
        callback: Callable[[str, ConnectionQuality, ConnectionQuality], None]
    ):
        """
        注册质量变化回调
        
        Args:
            connection_id: 连接ID
            callback: 回调函数
        """
        self.quality_change_callbacks[connection_id] = callback
    
    def register_reconnection_callback(
        self,
        connection_id: str,
        callback: Callable[[str], None]
    ):
        """
        注册重连回调
        
        Args:
            connection_id: 连接ID
            callback: 回调函数
        """
        self.reconnection_manager.register_reconnection_callback(connection_id, callback)
    
    async def _heartbeat_monitor(self):
        """心跳监控后台任务"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = time.time()
                timeout_connections = []
                
                # 检查所有连接的心跳状态
                for connection_id, metrics in self.heartbeat_metrics.items():
                    heartbeat_status = metrics.get_heartbeat_status(self.timeout_threshold)
                    
                    if heartbeat_status in [HeartbeatStatus.TIMEOUT, HeartbeatStatus.FAILED]:
                        timeout_connections.append(connection_id)
                        
                        # 调用超时回调
                        if connection_id in self.timeout_callbacks:
                            try:
                                callback = self.timeout_callbacks[connection_id]
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(connection_id)
                                else:
                                    callback(connection_id)
                            except Exception as e:
                                logger.error(f"Error in timeout callback: {e}")
                        
                        # 尝试重连
                        if await self.reconnection_manager.attempt_reconnection(connection_id):
                            self.stats['reconnections'] += 1
                
                # 更新超时统计
                if timeout_connections:
                    self.stats['timeouts'] += len(timeout_connections)
                    logger.warning(f"Detected {len(timeout_connections)} timeout connections")
                
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
    
    async def _quality_monitor(self):
        """连接质量监控后台任务"""
        while True:
            try:
                await asyncio.sleep(self.quality_check_interval)
                
                healthy_count = 0
                
                # 检查所有连接的质量变化
                for connection_id, metrics in self.heartbeat_metrics.items():
                    if metrics.is_healthy():
                        healthy_count += 1
                    
                    # 检查质量是否发生变化
                    if len(metrics.quality_history) >= 2:
                        current_quality = metrics.quality_history[-1]
                        previous_quality = metrics.quality_history[-2]
                        
                        if current_quality != previous_quality:
                            # 调用质量变化回调
                            if connection_id in self.quality_change_callbacks:
                                try:
                                    callback = self.quality_change_callbacks[connection_id]
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(connection_id, previous_quality, current_quality)
                                    else:
                                        callback(connection_id, previous_quality, current_quality)
                                except Exception as e:
                                    logger.error(f"Error in quality change callback: {e}")
                
                # 更新健康连接统计
                self.stats['healthy_connections'] = healthy_count
                
                # 缓存质量统计到Redis
                await self._cache_quality_stats()
                
            except Exception as e:
                logger.error(f"Error in quality monitor: {e}")
    
    async def _stats_updater(self):
        """统计更新后台任务"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟更新一次
                
                # 计算总体统计
                total_latency = 0
                total_samples = 0
                quality_distribution = {quality: 0 for quality in ConnectionQuality}
                
                for metrics in self.heartbeat_metrics.values():
                    if metrics.latency_samples:
                        total_latency += sum(metrics.latency_samples)
                        total_samples += len(metrics.latency_samples)
                    
                    quality_distribution[metrics.connection_quality] += 1
                
                # 更新统计信息
                self.stats.update({
                    'average_latency': total_latency / total_samples if total_samples > 0 else 0,
                    'quality_distribution': {
                        quality.value: count for quality, count in quality_distribution.items()
                    }
                })
                
                # 缓存统计到Redis
                await self._cache_stats()
                
            except Exception as e:
                logger.error(f"Error in stats updater: {e}")
    
    async def _cache_quality_stats(self):
        """缓存质量统计到Redis"""
        try:
            if self.redis_client:
                quality_stats = {}
                
                for connection_id, metrics in self.heartbeat_metrics.items():
                    quality_stats[connection_id] = {
                        'quality': metrics.connection_quality.value,
                        'latency': metrics.average_latency,
                        'packet_loss': metrics.get_packet_loss_rate(),
                        'is_healthy': metrics.is_healthy()
                    }
                
                key = "dashboard:heartbeat:quality_stats"
                await self.redis_client.setex(
                    key,
                    300,  # 5分钟过期
                    json.dumps(quality_stats, ensure_ascii=False)
                )
                
        except Exception as e:
            logger.error(f"Error caching quality stats: {e}")
    
    async def _cache_stats(self):
        """缓存统计信息到Redis"""
        try:
            if self.redis_client:
                key = "dashboard:heartbeat:stats"
                await self.redis_client.setex(
                    key,
                    300,  # 5分钟过期
                    json.dumps(self.stats, ensure_ascii=False)
                )
                
        except Exception as e:
            logger.error(f"Error caching stats: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            'heartbeat_interval': self.heartbeat_interval,
            'timeout_threshold': self.timeout_threshold,
            'quality_check_interval': self.quality_check_interval,
            'background_tasks': len(self.background_tasks),
            'pending_heartbeats': {
                connection_id: len(heartbeats)
                for connection_id, heartbeats in self.pending_heartbeats.items()
            }
        }
    
    def get_connection_summary(self) -> Dict[str, Any]:
        """
        获取连接摘要
        
        Returns:
            Dict[str, Any]: 连接摘要
        """
        quality_counts = {quality: 0 for quality in ConnectionQuality}
        status_counts = {status: 0 for status in HeartbeatStatus}
        
        for metrics in self.heartbeat_metrics.values():
            quality_counts[metrics.connection_quality] += 1
            status_counts[metrics.get_heartbeat_status(self.timeout_threshold)] += 1
        
        return {
            'total_connections': len(self.heartbeat_metrics),
            'quality_distribution': {
                quality.value: count for quality, count in quality_counts.items()
            },
            'status_distribution': {
                status.value: count for status, count in status_counts.items()
            },
            'healthy_connections': sum(
                1 for metrics in self.heartbeat_metrics.values() if metrics.is_healthy()
            )
        }
    
    async def force_reconnection(self, connection_id: str) -> bool:
        """
        强制重连
        
        Args:
            connection_id: 连接ID
            
        Returns:
            bool: 是否成功触发重连
        """
        if connection_id not in self.heartbeat_metrics:
            return False
        
        # 重置重连状态并立即尝试重连
        self.reconnection_manager.reset_reconnection_state(connection_id)
        return await self.reconnection_manager.attempt_reconnection(connection_id)
    
    async def shutdown(self):
        """关闭服务"""
        try:
            # 取消所有后台任务
            for task in self.background_tasks:
                task.cancel()
            
            # 等待任务完成
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # 清理数据
            self.heartbeat_metrics.clear()
            self.pending_heartbeats.clear()
            self.heartbeat_callbacks.clear()
            self.timeout_callbacks.clear()
            self.quality_change_callbacks.clear()
            
            logger.info("Dashboard heartbeat service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during heartbeat service shutdown: {e}")


# 全局实例
dashboard_heartbeat_service: Optional[DashboardHeartbeatService] = None


def get_dashboard_heartbeat_service() -> DashboardHeartbeatService:
    """获取仪表板心跳服务实例"""
    global dashboard_heartbeat_service
    
    if dashboard_heartbeat_service is None:
        dashboard_heartbeat_service = DashboardHeartbeatService()
    
    return dashboard_heartbeat_service