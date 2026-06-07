"""
请求队列服务 - 管理AI请求的排队、优先级和负载均衡
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
import heapq
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    """请求优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class RequestStatus(Enum):
    """请求状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class QueuedRequest:
    """队列中的请求对象"""
    request_id: str
    user_id: int
    content: str
    priority: RequestPriority
    created_at: datetime
    timeout_seconds: int = 300  # 5分钟默认超时
    max_retries: int = 3
    retry_count: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None
    
    # 内部状态
    status: RequestStatus = RequestStatus.PENDING
    assigned_provider: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if not self.request_id:
            self.request_id = str(uuid.uuid4())
    
    def __lt__(self, other):
        """用于优先级队列排序 - 优先级高的先处理"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        # 同优先级按创建时间排序
        return self.created_at < other.created_at
    
    @property
    def is_expired(self) -> bool:
        """检查请求是否已超时"""
        if self.status in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.CANCELLED]:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.timeout_seconds
    
    @property
    def processing_time(self) -> Optional[float]:
        """获取处理时间（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None


@dataclass
class QueueMetrics:
    """队列指标"""
    total_requests: int = 0
    pending_requests: int = 0
    processing_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    cancelled_requests: int = 0
    timeout_requests: int = 0
    
    average_wait_time: float = 0.0
    average_processing_time: float = 0.0
    throughput_per_minute: float = 0.0
    
    queue_length_by_priority: Dict[RequestPriority, int] = field(default_factory=dict)
    provider_load_distribution: Dict[str, int] = field(default_factory=dict)


class RequestQueueService:
    """请求队列服务"""
    
    def __init__(self, db: AsyncSession = None, max_concurrent_requests: int = 50):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # 队列配置
        self.max_concurrent_requests = max_concurrent_requests
        self.max_queue_size = 1000
        self.cleanup_interval = 300  # 5分钟清理一次过期请求
        
        # 优先级队列 - 使用堆实现
        self._priority_queue: List[QueuedRequest] = []
        self._queue_lock = asyncio.Lock()
        
        # 请求映射 - 快速查找
        self._request_map: Dict[str, QueuedRequest] = {}
        
        # 正在处理的请求
        self._processing_requests: Dict[str, QueuedRequest] = {}
        
        # 已完成的请求历史（用于统计）
        self._completed_requests: deque = deque(maxlen=1000)
        
        # 队列指标
        self._metrics = QueueMetrics()
        
        # 负载均衡状态
        self._provider_loads: Dict[str, int] = {}
        self._provider_capacities: Dict[str, int] = {}
        
        # 后台任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        
        # 事件回调
        self._event_callbacks: Dict[str, List[Callable]] = {
            'request_queued': [],
            'request_started': [],
            'request_completed': [],
            'request_failed': [],
            'queue_full': [],
            'provider_overloaded': []
        }
    
    async def start(self):
        """启动队列服务"""
        self.logger.info("Starting request queue service")
        
        # 启动后台清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_requests())
        
        # 启动指标更新任务
        self._metrics_task = asyncio.create_task(self._update_metrics_periodically())
        
        self.logger.info("Request queue service started")
    
    async def stop(self):
        """停止队列服务"""
        self.logger.info("Stopping request queue service")
        
        # 取消后台任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        
        # 取消所有待处理的请求
        async with self._queue_lock:
            for request in self._priority_queue:
                request.status = RequestStatus.CANCELLED
                await self._notify_request_event('request_failed', request)
            
            self._priority_queue.clear()
            self._request_map.clear()
        
        self.logger.info("Request queue service stopped")
    
    async def enqueue_request(self, 
                            user_id: int,
                            content: str,
                            priority: RequestPriority = RequestPriority.NORMAL,
                            timeout_seconds: int = 300,
                            max_retries: int = 3,
                            context: Optional[Dict[str, Any]] = None,
                            callback: Optional[Callable] = None) -> str:
        """
        将请求加入队列
        
        Args:
            user_id: 用户ID
            content: 请求内容
            priority: 请求优先级
            timeout_seconds: 超时时间（秒）
            max_retries: 最大重试次数
            context: 请求上下文
            callback: 完成回调函数
            
        Returns:
            str: 请求ID
            
        Raises:
            ValueError: 队列已满或参数无效
        """
        async with self._queue_lock:
            # 检查队列是否已满
            if len(self._priority_queue) >= self.max_queue_size:
                await self._notify_queue_full()
                raise ValueError(f"Queue is full (max size: {self.max_queue_size})")
            
            # 创建请求对象
            request = QueuedRequest(
                request_id=str(uuid.uuid4()),
                user_id=user_id,
                content=content,
                priority=priority,
                created_at=datetime.utcnow(),
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                context=context or {},
                callback=callback
            )
            
            # 添加到队列和映射
            heapq.heappush(self._priority_queue, request)
            self._request_map[request.request_id] = request
            
            # 更新指标
            self._metrics.total_requests += 1
            self._metrics.pending_requests += 1
            
            # 通知事件
            await self._notify_request_event('request_queued', request)
            
            self.logger.info(f"Request {request.request_id} queued with priority {priority.name}")
            return request.request_id
    
    async def dequeue_request(self, provider_id: str) -> Optional[QueuedRequest]:
        """
        从队列中取出下一个请求进行处理
        
        Args:
            provider_id: 处理提供商ID
            
        Returns:
            Optional[QueuedRequest]: 下一个要处理的请求，如果队列为空则返回None
        """
        async with self._queue_lock:
            # 检查提供商负载
            current_load = self._provider_loads.get(provider_id, 0)
            max_capacity = self._provider_capacities.get(provider_id, 10)
            
            if current_load >= max_capacity:
                self.logger.debug(f"Provider {provider_id} is at capacity ({current_load}/{max_capacity})")
                await self._notify_provider_overloaded(provider_id)
                return None
            
            # 检查全局并发限制
            if len(self._processing_requests) >= self.max_concurrent_requests:
                self.logger.debug(f"Global concurrent limit reached ({len(self._processing_requests)}/{self.max_concurrent_requests})")
                return None
            
            # 从优先级队列中取出请求
            while self._priority_queue:
                request = heapq.heappop(self._priority_queue)
                
                # 检查请求是否仍然有效
                if request.request_id not in self._request_map:
                    continue
                
                # 检查请求是否已超时
                if request.is_expired:
                    await self._handle_timeout_request(request)
                    continue
                
                # 标记请求为处理中
                request.status = RequestStatus.PROCESSING
                request.assigned_provider = provider_id
                request.started_at = datetime.utcnow()
                
                # 移动到处理中队列
                self._processing_requests[request.request_id] = request
                
                # 更新负载和指标
                self._provider_loads[provider_id] = current_load + 1
                self._metrics.pending_requests -= 1
                self._metrics.processing_requests += 1
                
                # 通知事件
                await self._notify_request_event('request_started', request)
                
                self.logger.info(f"Request {request.request_id} assigned to provider {provider_id}")
                return request
            
            return None
    
    async def complete_request(self, request_id: str, result: Any = None, error: Optional[str] = None):
        """
        标记请求为完成
        
        Args:
            request_id: 请求ID
            result: 处理结果
            error: 错误信息（如果有）
        """
        async with self._queue_lock:
            request = self._processing_requests.get(request_id)
            if not request:
                self.logger.warning(f"Request {request_id} not found in processing queue")
                return
            
            # 更新请求状态
            request.completed_at = datetime.utcnow()
            
            if error:
                request.status = RequestStatus.FAILED
                request.error_message = error
                
                # 检查是否需要重试
                if request.retry_count < request.max_retries:
                    await self._retry_request(request)
                    return
                
                self._metrics.failed_requests += 1
                await self._notify_request_event('request_failed', request)
            else:
                request.status = RequestStatus.COMPLETED
                self._metrics.completed_requests += 1
                await self._notify_request_event('request_completed', request)
            
            # 从处理队列中移除
            del self._processing_requests[request_id]
            del self._request_map[request_id]
            
            # 更新负载
            if request.assigned_provider:
                current_load = self._provider_loads.get(request.assigned_provider, 0)
                self._provider_loads[request.assigned_provider] = max(0, current_load - 1)
            
            # 更新指标
            self._metrics.processing_requests -= 1
            
            # 添加到完成历史
            self._completed_requests.append(request)
            
            # 执行回调
            if request.callback:
                try:
                    if asyncio.iscoroutinefunction(request.callback):
                        await request.callback(request, result, error)
                    else:
                        request.callback(request, result, error)
                except Exception as e:
                    self.logger.error(f"Error executing callback for request {request_id}: {str(e)}")
            
            self.logger.info(f"Request {request_id} completed with status {request.status.value}")
    
    async def cancel_request(self, request_id: str) -> bool:
        """
        取消请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            bool: 是否成功取消
        """
        async with self._queue_lock:
            request = self._request_map.get(request_id)
            if not request:
                return False
            
            if request.status == RequestStatus.PROCESSING:
                # 正在处理的请求需要特殊处理
                request.status = RequestStatus.CANCELLED
                if request_id in self._processing_requests:
                    del self._processing_requests[request_id]
                    self._metrics.processing_requests -= 1
                    
                    # 更新负载
                    if request.assigned_provider:
                        current_load = self._provider_loads.get(request.assigned_provider, 0)
                        self._provider_loads[request.assigned_provider] = max(0, current_load - 1)
            
            elif request.status == RequestStatus.PENDING:
                # 从队列中移除
                request.status = RequestStatus.CANCELLED
                # 重建堆（移除已取消的请求）
                self._priority_queue = [r for r in self._priority_queue if r.request_id != request_id]
                heapq.heapify(self._priority_queue)
                self._metrics.pending_requests -= 1
            
            else:
                # 已完成或已失败的请求无法取消
                return False
            
            # 清理映射
            del self._request_map[request_id]
            self._metrics.cancelled_requests += 1
            
            await self._notify_request_event('request_failed', request)
            
            self.logger.info(f"Request {request_id} cancelled")
            return True
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        获取请求状态
        
        Args:
            request_id: 请求ID
            
        Returns:
            Optional[Dict[str, Any]]: 请求状态信息
        """
        request = self._request_map.get(request_id)
        if not request:
            # 检查完成历史
            for completed_request in self._completed_requests:
                if completed_request.request_id == request_id:
                    request = completed_request
                    break
            
            if not request:
                return None
        
        return {
            'request_id': request.request_id,
            'user_id': request.user_id,
            'status': request.status.value,
            'priority': request.priority.name,
            'created_at': request.created_at.isoformat(),
            'started_at': request.started_at.isoformat() if request.started_at else None,
            'completed_at': request.completed_at.isoformat() if request.completed_at else None,
            'processing_time': request.processing_time,
            'assigned_provider': request.assigned_provider,
            'retry_count': request.retry_count,
            'error_message': request.error_message,
            'is_expired': request.is_expired
        }
    
    async def get_queue_metrics(self) -> QueueMetrics:
        """获取队列指标"""
        async with self._queue_lock:
            # 更新优先级分布
            priority_counts = {}
            for request in self._priority_queue:
                priority = request.priority
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            self._metrics.queue_length_by_priority = priority_counts
            self._metrics.provider_load_distribution = dict(self._provider_loads)
            
            return self._metrics
    
    async def set_provider_capacity(self, provider_id: str, capacity: int):
        """
        设置提供商容量
        
        Args:
            provider_id: 提供商ID
            capacity: 最大并发容量
        """
        self._provider_capacities[provider_id] = capacity
        if provider_id not in self._provider_loads:
            self._provider_loads[provider_id] = 0
        
        self.logger.info(f"Set provider {provider_id} capacity to {capacity}")
    
    async def get_provider_load(self, provider_id: str) -> Tuple[int, int]:
        """
        获取提供商负载
        
        Args:
            provider_id: 提供商ID
            
        Returns:
            Tuple[int, int]: (当前负载, 最大容量)
        """
        current_load = self._provider_loads.get(provider_id, 0)
        max_capacity = self._provider_capacities.get(provider_id, 10)
        return current_load, max_capacity
    
    def register_event_callback(self, event_type: str, callback: Callable):
        """
        注册事件回调
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self._event_callbacks:
            self._event_callbacks[event_type].append(callback)
    
    async def _retry_request(self, request: QueuedRequest):
        """重试请求"""
        request.retry_count += 1
        request.status = RequestStatus.PENDING
        request.assigned_provider = None
        request.started_at = None
        request.error_message = None
        
        # 重新加入队列
        heapq.heappush(self._priority_queue, request)
        
        # 从处理队列移除
        if request.request_id in self._processing_requests:
            del self._processing_requests[request.request_id]
        
        # 更新指标
        self._metrics.processing_requests -= 1
        self._metrics.pending_requests += 1
        
        self.logger.info(f"Request {request.request_id} queued for retry (attempt {request.retry_count})")
    
    async def _handle_timeout_request(self, request: QueuedRequest):
        """处理超时请求"""
        request.status = RequestStatus.TIMEOUT
        request.error_message = "Request timeout"
        
        # 从映射中移除
        if request.request_id in self._request_map:
            del self._request_map[request.request_id]
        
        # 更新指标
        self._metrics.timeout_requests += 1
        self._metrics.pending_requests -= 1
        
        await self._notify_request_event('request_failed', request)
        
        self.logger.warning(f"Request {request.request_id} timed out")
    
    async def _cleanup_expired_requests(self):
        """清理过期请求的后台任务"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                async with self._queue_lock:
                    expired_requests = []
                    
                    # 检查队列中的过期请求
                    for request in self._priority_queue:
                        if request.is_expired:
                            expired_requests.append(request)
                    
                    # 处理过期请求
                    for request in expired_requests:
                        await self._handle_timeout_request(request)
                    
                    # 重建堆（移除过期请求）
                    if expired_requests:
                        self._priority_queue = [r for r in self._priority_queue if not r.is_expired]
                        heapq.heapify(self._priority_queue)
                
                if expired_requests:
                    self.logger.info(f"Cleaned up {len(expired_requests)} expired requests")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {str(e)}")
    
    async def _update_metrics_periodically(self):
        """定期更新指标的后台任务"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟更新一次
                await self._calculate_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error updating metrics: {str(e)}")
    
    async def _calculate_metrics(self):
        """计算队列指标"""
        async with self._queue_lock:
            # 计算平均等待时间
            if self._completed_requests:
                wait_times = []
                processing_times = []
                
                for request in self._completed_requests:
                    if request.started_at and request.created_at:
                        wait_time = (request.started_at - request.created_at).total_seconds()
                        wait_times.append(wait_time)
                    
                    if request.processing_time:
                        processing_times.append(request.processing_time)
                
                self._metrics.average_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0.0
                self._metrics.average_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
            
            # 计算吞吐量（每分钟完成的请求数）
            now = datetime.utcnow()
            one_minute_ago = now - timedelta(minutes=1)
            
            recent_completions = [
                r for r in self._completed_requests 
                if r.completed_at and r.completed_at >= one_minute_ago
            ]
            
            self._metrics.throughput_per_minute = len(recent_completions)
    
    async def _notify_request_event(self, event_type: str, request: QueuedRequest):
        """通知请求事件"""
        callbacks = self._event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(request)
                else:
                    callback(request)
            except Exception as e:
                self.logger.error(f"Error in event callback {event_type}: {str(e)}")
    
    async def _notify_queue_full(self):
        """通知队列已满"""
        callbacks = self._event_callbacks.get('queue_full', [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                self.logger.error(f"Error in queue_full callback: {str(e)}")
    
    async def _notify_provider_overloaded(self, provider_id: str):
        """通知提供商过载"""
        callbacks = self._event_callbacks.get('provider_overloaded', [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(provider_id)
                else:
                    callback(provider_id)
            except Exception as e:
                self.logger.error(f"Error in provider_overloaded callback: {str(e)}")