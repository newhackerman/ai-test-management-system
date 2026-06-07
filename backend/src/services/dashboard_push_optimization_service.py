"""
仪表板数据推送优化服务

实现数据变更检测、增量推送、压缩优化和流量控制功能
"""

import asyncio
import json
import gzip
import zlib
import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Callable, Union
from enum import Enum
import pickle
from dataclasses import dataclass, asdict

from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class CompressionType(Enum):
    """压缩类型"""
    NONE = "NONE"
    GZIP = "GZIP"
    ZLIB = "ZLIB"
    BROTLI = "BROTLI"


class DataChangeType(Enum):
    """数据变更类型"""
    CREATE = "CREATE"  # 创建
    UPDATE = "UPDATE"  # 更新
    DELETE = "DELETE"  # 删除
    BATCH = "BATCH"  # 批量操作


class PushStrategy(Enum):
    """推送策略"""
    IMMEDIATE = "IMMEDIATE"  # 立即推送
    BATCHED = "BATCHED"  # 批量推送
    THROTTLED = "THROTTLED"  # 限流推送
    ADAPTIVE = "ADAPTIVE"  # 自适应推送


class FlowControlMode(Enum):
    """流量控制模式"""
    NONE = "NONE"  # 无控制
    TOKEN_BUCKET = "TOKEN_BUCKET"  # 令牌桶
    SLIDING_WINDOW = "SLIDING_WINDOW"  # 滑动窗口
    ADAPTIVE_RATE = "ADAPTIVE_RATE"  # 自适应速率


@dataclass
class DataSnapshot:
    """数据快照"""
    data_id: str
    data_type: str
    content: Any
    checksum: str
    timestamp: float
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataSnapshot':
        """从字典创建"""
        return cls(**data)


@dataclass
class DataDelta:
    """数据增量"""
    data_id: str
    change_type: DataChangeType
    old_checksum: Optional[str]
    new_checksum: str
    changes: Dict[str, Any]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['change_type'] = self.change_type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataDelta':
        """从字典创建"""
        data['change_type'] = DataChangeType(data['change_type'])
        return cls(**data)


class CompressionManager:
    """压缩管理器"""
    
    def __init__(self):
        self.compression_stats = {
            CompressionType.NONE: {'count': 0, 'original_size': 0, 'compressed_size': 0},
            CompressionType.GZIP: {'count': 0, 'original_size': 0, 'compressed_size': 0},
            CompressionType.ZLIB: {'count': 0, 'original_size': 0, 'compressed_size': 0}
        }
    
    def compress_data(
        self,
        data: Union[str, bytes, Dict[str, Any]],
        compression_type: CompressionType = CompressionType.GZIP,
        compression_threshold: int = 1024
    ) -> tuple[bytes, CompressionType]:
        """
        压缩数据
        
        Args:
            data: 要压缩的数据
            compression_type: 压缩类型
            compression_threshold: 压缩阈值(字节)
            
        Returns:
            tuple[bytes, CompressionType]: 压缩后的数据和实际使用的压缩类型
        """
        # 转换数据为字节
        if isinstance(data, dict):
            data_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        original_size = len(data_bytes)
        
        # 如果数据太小，不进行压缩
        if original_size < compression_threshold:
            self._update_stats(CompressionType.NONE, original_size, original_size)
            return data_bytes, CompressionType.NONE
        
        # 根据压缩类型进行压缩
        if compression_type == CompressionType.GZIP:
            compressed_data = gzip.compress(data_bytes, compresslevel=6)
        elif compression_type == CompressionType.ZLIB:
            compressed_data = zlib.compress(data_bytes, level=6)
        else:
            compressed_data = data_bytes
            compression_type = CompressionType.NONE
        
        compressed_size = len(compressed_data)
        
        # 如果压缩后反而更大，则不使用压缩
        if compressed_size >= original_size:
            self._update_stats(CompressionType.NONE, original_size, original_size)
            return data_bytes, CompressionType.NONE
        
        self._update_stats(compression_type, original_size, compressed_size)
        return compressed_data, compression_type
    
    def decompress_data(
        self,
        compressed_data: bytes,
        compression_type: CompressionType
    ) -> bytes:
        """
        解压数据
        
        Args:
            compressed_data: 压缩的数据
            compression_type: 压缩类型
            
        Returns:
            bytes: 解压后的数据
        """
        if compression_type == CompressionType.GZIP:
            return gzip.decompress(compressed_data)
        elif compression_type == CompressionType.ZLIB:
            return zlib.decompress(compressed_data)
        else:
            return compressed_data
    
    def _update_stats(
        self,
        compression_type: CompressionType,
        original_size: int,
        compressed_size: int
    ):
        """更新压缩统计"""
        stats = self.compression_stats[compression_type]
        stats['count'] += 1
        stats['original_size'] += original_size
        stats['compressed_size'] += compressed_size
    
    def get_compression_ratio(self, compression_type: CompressionType) -> float:
        """获取压缩比"""
        stats = self.compression_stats[compression_type]
        if stats['original_size'] == 0:
            return 0.0
        return stats['compressed_size'] / stats['original_size']
    
    def get_stats(self) -> Dict[str, Any]:
        """获取压缩统计"""
        result = {}
        for comp_type, stats in self.compression_stats.items():
            result[comp_type.value] = {
                **stats,
                'compression_ratio': self.get_compression_ratio(comp_type)
            }
        return result


class FlowController:
    """流量控制器"""
    
    def __init__(
        self,
        mode: FlowControlMode = FlowControlMode.TOKEN_BUCKET,
        max_rate: float = 100.0,  # 每秒最大请求数
        burst_size: int = 10,  # 突发大小
        window_size: int = 60  # 窗口大小(秒)
    ):
        self.mode = mode
        self.max_rate = max_rate
        self.burst_size = burst_size
        self.window_size = window_size
        
        # 令牌桶参数
        self.tokens = burst_size
        self.last_refill = time.time()
        
        # 滑动窗口参数
        self.request_times: List[float] = []
        
        # 自适应速率参数
        self.current_rate = max_rate
        self.success_count = 0
        self.failure_count = 0
        self.last_adjustment = time.time()
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'allowed_requests': 0,
            'rejected_requests': 0,
            'current_rate': max_rate
        }
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        获取令牌
        
        Args:
            tokens: 需要的令牌数
            
        Returns:
            bool: 是否获取成功
        """
        self.stats['total_requests'] += 1
        
        if self.mode == FlowControlMode.NONE:
            self.stats['allowed_requests'] += 1
            return True
        
        elif self.mode == FlowControlMode.TOKEN_BUCKET:
            allowed = await self._token_bucket_acquire(tokens)
        
        elif self.mode == FlowControlMode.SLIDING_WINDOW:
            allowed = await self._sliding_window_acquire()
        
        elif self.mode == FlowControlMode.ADAPTIVE_RATE:
            allowed = await self._adaptive_rate_acquire()
        
        else:
            allowed = True
        
        if allowed:
            self.stats['allowed_requests'] += 1
        else:
            self.stats['rejected_requests'] += 1
        
        return allowed
    
    async def _token_bucket_acquire(self, tokens: int) -> bool:
        """令牌桶算法"""
        current_time = time.time()
        
        # 补充令牌
        time_passed = current_time - self.last_refill
        new_tokens = time_passed * self.max_rate
        self.tokens = min(self.burst_size, self.tokens + new_tokens)
        self.last_refill = current_time
        
        # 检查是否有足够的令牌
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    async def _sliding_window_acquire(self) -> bool:
        """滑动窗口算法"""
        current_time = time.time()
        
        # 清理过期的请求
        cutoff_time = current_time - self.window_size
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        
        # 检查是否超过速率限制
        if len(self.request_times) < self.max_rate * self.window_size:
            self.request_times.append(current_time)
            return True
        
        return False
    
    async def _adaptive_rate_acquire(self) -> bool:
        """自适应速率算法"""
        current_time = time.time()
        
        # 定期调整速率
        if current_time - self.last_adjustment > 10:  # 每10秒调整一次
            self._adjust_rate()
            self.last_adjustment = current_time
        
        # 使用当前速率进行令牌桶控制
        time_passed = current_time - self.last_refill
        new_tokens = time_passed * self.current_rate
        self.tokens = min(self.burst_size, self.tokens + new_tokens)
        self.last_refill = current_time
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        
        return False
    
    def _adjust_rate(self):
        """调整自适应速率"""
        total_requests = self.success_count + self.failure_count
        
        if total_requests > 0:
            success_rate = self.success_count / total_requests
            
            if success_rate > 0.95:  # 成功率高，增加速率
                self.current_rate = min(self.max_rate * 2, self.current_rate * 1.1)
            elif success_rate < 0.8:  # 成功率低，降低速率
                self.current_rate = max(self.max_rate * 0.1, self.current_rate * 0.9)
        
        # 重置计数器
        self.success_count = 0
        self.failure_count = 0
        self.stats['current_rate'] = self.current_rate
    
    def record_success(self):
        """记录成功"""
        self.success_count += 1
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'mode': self.mode.value,
            'max_rate': self.max_rate,
            'current_tokens': self.tokens,
            'window_requests': len(self.request_times) if self.mode == FlowControlMode.SLIDING_WINDOW else 0
        }


class DataChangeDetector:
    """数据变更检测器"""
    
    def __init__(self):
        self.snapshots: Dict[str, DataSnapshot] = {}
        self.change_callbacks: Dict[str, List[Callable]] = {}
    
    def register_data(
        self,
        data_id: str,
        data_type: str,
        content: Any
    ) -> DataSnapshot:
        """
        注册数据
        
        Args:
            data_id: 数据ID
            data_type: 数据类型
            content: 数据内容
            
        Returns:
            DataSnapshot: 数据快照
        """
        checksum = self._calculate_checksum(content)
        snapshot = DataSnapshot(
            data_id=data_id,
            data_type=data_type,
            content=content,
            checksum=checksum,
            timestamp=time.time()
        )
        
        self.snapshots[data_id] = snapshot
        return snapshot
    
    def detect_changes(
        self,
        data_id: str,
        new_content: Any
    ) -> Optional[DataDelta]:
        """
        检测数据变更
        
        Args:
            data_id: 数据ID
            new_content: 新数据内容
            
        Returns:
            Optional[DataDelta]: 数据增量，如果没有变更则返回None
        """
        if data_id not in self.snapshots:
            # 新数据
            snapshot = self.register_data(data_id, "unknown", new_content)
            return DataDelta(
                data_id=data_id,
                change_type=DataChangeType.CREATE,
                old_checksum=None,
                new_checksum=snapshot.checksum,
                changes={'content': new_content},
                timestamp=time.time()
            )
        
        old_snapshot = self.snapshots[data_id]
        new_checksum = self._calculate_checksum(new_content)
        
        # 检查是否有变更
        if old_snapshot.checksum == new_checksum:
            return None
        
        # 计算具体变更
        changes = self._calculate_changes(old_snapshot.content, new_content)
        
        # 更新快照
        old_snapshot.content = new_content
        old_snapshot.checksum = new_checksum
        old_snapshot.timestamp = time.time()
        old_snapshot.version += 1
        
        return DataDelta(
            data_id=data_id,
            change_type=DataChangeType.UPDATE,
            old_checksum=old_snapshot.checksum,
            new_checksum=new_checksum,
            changes=changes,
            timestamp=time.time()
        )
    
    def remove_data(self, data_id: str) -> Optional[DataDelta]:
        """
        移除数据
        
        Args:
            data_id: 数据ID
            
        Returns:
            Optional[DataDelta]: 删除增量
        """
        if data_id not in self.snapshots:
            return None
        
        old_snapshot = self.snapshots[data_id]
        del self.snapshots[data_id]
        
        return DataDelta(
            data_id=data_id,
            change_type=DataChangeType.DELETE,
            old_checksum=old_snapshot.checksum,
            new_checksum="",
            changes={'deleted': True},
            timestamp=time.time()
        )
    
    def register_change_callback(
        self,
        data_type: str,
        callback: Callable[[DataDelta], None]
    ):
        """
        注册变更回调
        
        Args:
            data_type: 数据类型
            callback: 回调函数
        """
        if data_type not in self.change_callbacks:
            self.change_callbacks[data_type] = []
        
        self.change_callbacks[data_type].append(callback)
    
    def _calculate_checksum(self, content: Any) -> str:
        """计算校验和"""
        if isinstance(content, dict):
            content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        elif isinstance(content, (list, tuple)):
            content_str = json.dumps(list(content), ensure_ascii=False)
        else:
            content_str = str(content)
        
        return hashlib.md5(content_str.encode('utf-8')).hexdigest()
    
    def _calculate_changes(self, old_content: Any, new_content: Any) -> Dict[str, Any]:
        """计算具体变更"""
        if isinstance(old_content, dict) and isinstance(new_content, dict):
            return self._calculate_dict_changes(old_content, new_content)
        elif isinstance(old_content, list) and isinstance(new_content, list):
            return self._calculate_list_changes(old_content, new_content)
        else:
            return {'old_value': old_content, 'new_value': new_content}
    
    def _calculate_dict_changes(self, old_dict: Dict, new_dict: Dict) -> Dict[str, Any]:
        """计算字典变更"""
        changes = {}
        
        # 检查修改和新增
        for key, new_value in new_dict.items():
            if key not in old_dict:
                changes[f"added.{key}"] = new_value
            elif old_dict[key] != new_value:
                changes[f"modified.{key}"] = {
                    'old': old_dict[key],
                    'new': new_value
                }
        
        # 检查删除
        for key in old_dict:
            if key not in new_dict:
                changes[f"removed.{key}"] = old_dict[key]
        
        return changes
    
    def _calculate_list_changes(self, old_list: List, new_list: List) -> Dict[str, Any]:
        """计算列表变更"""
        changes = {}
        
        # 简单的列表比较
        if len(old_list) != len(new_list):
            changes['length_changed'] = {
                'old_length': len(old_list),
                'new_length': len(new_list)
            }
        
        # 检查元素变更
        min_length = min(len(old_list), len(new_list))
        for i in range(min_length):
            if old_list[i] != new_list[i]:
                changes[f"index_{i}"] = {
                    'old': old_list[i],
                    'new': new_list[i]
                }
        
        # 检查新增元素
        if len(new_list) > len(old_list):
            changes['added_items'] = new_list[len(old_list):]
        
        # 检查删除元素
        if len(old_list) > len(new_list):
            changes['removed_items'] = old_list[len(new_list):]
        
        return changes


class DashboardPushOptimizationService:
    """仪表板数据推送优化服务"""
    
    def __init__(
        self,
        compression_threshold: int = 1024,
        batch_size: int = 10,
        batch_timeout: float = 1.0,
        max_queue_size: int = 1000
    ):
        self.compression_threshold = compression_threshold
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_queue_size = max_queue_size
        
        # 核心组件
        self.compression_manager = CompressionManager()
        self.flow_controller = FlowController()
        self.change_detector = DataChangeDetector()
        
        # 推送队列
        self.push_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.batch_queue: List[Dict[str, Any]] = []
        self.last_batch_time = time.time()
        
        # 连接管理
        self.connection_configs: Dict[str, Dict[str, Any]] = {}
        self.connection_stats: Dict[str, Dict[str, Any]] = {}
        
        # 后台任务
        self.background_tasks: Set[asyncio.Task] = set()
        
        # 统计信息
        self.stats = {
            'total_pushes': 0,
            'successful_pushes': 0,
            'failed_pushes': 0,
            'bytes_sent': 0,
            'bytes_saved_by_compression': 0,
            'incremental_pushes': 0,
            'full_pushes': 0,
            'batched_pushes': 0
        }
        
        # Redis客户端
        self.redis_client = get_redis_client()
        
        # 启动后台任务
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """启动后台任务"""
        # 推送处理任务
        push_task = asyncio.create_task(self._push_processor())
        self.background_tasks.add(push_task)
        push_task.add_done_callback(self.background_tasks.discard)
        
        # 批量处理任务
        batch_task = asyncio.create_task(self._batch_processor())
        self.background_tasks.add(batch_task)
        batch_task.add_done_callback(self.background_tasks.discard)
        
        # 统计更新任务
        stats_task = asyncio.create_task(self._stats_updater())
        self.background_tasks.add(stats_task)
        stats_task.add_done_callback(self.background_tasks.discard)
    
    def configure_connection(
        self,
        connection_id: str,
        push_strategy: PushStrategy = PushStrategy.ADAPTIVE,
        compression_type: CompressionType = CompressionType.GZIP,
        flow_control_mode: FlowControlMode = FlowControlMode.TOKEN_BUCKET,
        max_rate: float = 50.0,
        enable_incremental: bool = True
    ):
        """
        配置连接推送参数
        
        Args:
            connection_id: 连接ID
            push_strategy: 推送策略
            compression_type: 压缩类型
            flow_control_mode: 流量控制模式
            max_rate: 最大推送速率
            enable_incremental: 是否启用增量推送
        """
        self.connection_configs[connection_id] = {
            'push_strategy': push_strategy,
            'compression_type': compression_type,
            'flow_control_mode': flow_control_mode,
            'max_rate': max_rate,
            'enable_incremental': enable_incremental,
            'flow_controller': FlowController(flow_control_mode, max_rate)
        }
        
        self.connection_stats[connection_id] = {
            'pushes_sent': 0,
            'bytes_sent': 0,
            'compression_ratio': 0.0,
            'last_push_time': 0,
            'average_latency': 0.0
        }
        
        logger.info(f"Configured push optimization for connection: {connection_id}")
    
    def remove_connection(self, connection_id: str):
        """
        移除连接配置
        
        Args:
            connection_id: 连接ID
        """
        self.connection_configs.pop(connection_id, None)
        self.connection_stats.pop(connection_id, None)
        
        logger.info(f"Removed push optimization for connection: {connection_id}")
    
    async def push_data(
        self,
        connection_id: str,
        data_type: str,
        data_content: Any,
        priority: int = 1,
        force_full: bool = False
    ) -> bool:
        """
        推送数据
        
        Args:
            connection_id: 连接ID
            data_type: 数据类型
            data_content: 数据内容
            priority: 优先级 (1-10, 数字越大优先级越高)
            force_full: 是否强制全量推送
            
        Returns:
            bool: 是否成功加入推送队列
        """
        if connection_id not in self.connection_configs:
            logger.warning(f"Connection {connection_id} not configured for push optimization")
            return False
        
        config = self.connection_configs[connection_id]
        
        # 检测数据变更
        data_id = f"{connection_id}:{data_type}"
        delta = None
        
        if config['enable_incremental'] and not force_full:
            delta = self.change_detector.detect_changes(data_id, data_content)
            if delta is None:
                # 没有变更，不需要推送
                return True
        
        # 创建推送任务
        push_task = {
            'connection_id': connection_id,
            'data_type': data_type,
            'data_content': data_content,
            'delta': delta,
            'priority': priority,
            'timestamp': time.time(),
            'force_full': force_full
        }
        
        try:
            # 根据策略处理推送
            strategy = config['push_strategy']
            
            if strategy == PushStrategy.IMMEDIATE:
                await self._immediate_push(push_task)
            elif strategy == PushStrategy.BATCHED:
                await self._batched_push(push_task)
            elif strategy == PushStrategy.THROTTLED:
                await self._throttled_push(push_task)
            elif strategy == PushStrategy.ADAPTIVE:
                await self._adaptive_push(push_task)
            
            return True
            
        except asyncio.QueueFull:
            logger.warning(f"Push queue full for connection {connection_id}")
            return False
        except Exception as e:
            logger.error(f"Error pushing data: {e}")
            return False
    
    async def _immediate_push(self, push_task: Dict[str, Any]):
        """立即推送"""
        await self.push_queue.put(push_task)
    
    async def _batched_push(self, push_task: Dict[str, Any]):
        """批量推送"""
        self.batch_queue.append(push_task)
        
        # 检查是否需要立即发送批次
        if (len(self.batch_queue) >= self.batch_size or
            time.time() - self.last_batch_time > self.batch_timeout):
            await self._flush_batch()
    
    async def _throttled_push(self, push_task: Dict[str, Any]):
        """限流推送"""
        connection_id = push_task['connection_id']
        config = self.connection_configs[connection_id]
        flow_controller = config['flow_controller']
        
        # 检查流量控制
        if await flow_controller.acquire():
            await self.push_queue.put(push_task)
        else:
            # 流量受限，延迟推送
            await asyncio.sleep(0.1)
            await self.push_queue.put(push_task)
    
    async def _adaptive_push(self, push_task: Dict[str, Any]):
        """自适应推送"""
        connection_id = push_task['connection_id']
        stats = self.connection_stats[connection_id]
        
        # 根据连接状态选择策略
        if stats['average_latency'] > 200:  # 高延迟，使用批量推送
            await self._batched_push(push_task)
        elif stats['pushes_sent'] > 100:  # 高频推送，使用限流
            await self._throttled_push(push_task)
        else:  # 正常情况，立即推送
            await self._immediate_push(push_task)
    
    async def _flush_batch(self):
        """刷新批次"""
        if not self.batch_queue:
            return
        
        # 按连接分组
        connection_batches = {}
        for task in self.batch_queue:
            connection_id = task['connection_id']
            if connection_id not in connection_batches:
                connection_batches[connection_id] = []
            connection_batches[connection_id].append(task)
        
        # 为每个连接创建批量推送任务
        for connection_id, tasks in connection_batches.items():
            batch_task = {
                'connection_id': connection_id,
                'batch_tasks': tasks,
                'timestamp': time.time(),
                'is_batch': True
            }
            await self.push_queue.put(batch_task)
        
        # 清空批次队列
        self.batch_queue.clear()
        self.last_batch_time = time.time()
    
    async def _push_processor(self):
        """推送处理器"""
        while True:
            try:
                # 获取推送任务
                push_task = await self.push_queue.get()
                
                # 处理推送任务
                await self._process_push_task(push_task)
                
            except Exception as e:
                logger.error(f"Error in push processor: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_push_task(self, push_task: Dict[str, Any]):
        """
        处理推送任务
        
        Args:
            push_task: 推送任务
        """
        try:
            connection_id = push_task['connection_id']
            
            if connection_id not in self.connection_configs:
                return
            
            config = self.connection_configs[connection_id]
            stats = self.connection_stats[connection_id]
            
            start_time = time.time()
            
            # 处理批量任务
            if push_task.get('is_batch'):
                await self._process_batch_task(push_task, config, stats)
            else:
                await self._process_single_task(push_task, config, stats)
            
            # 更新延迟统计
            latency = (time.time() - start_time) * 1000
            stats['average_latency'] = (
                stats['average_latency'] * 0.9 + latency * 0.1
            )
            
            # 记录成功
            config['flow_controller'].record_success()
            self.stats['successful_pushes'] += 1
            
        except Exception as e:
            logger.error(f"Error processing push task: {e}")
            
            # 记录失败
            if 'connection_id' in push_task:
                connection_id = push_task['connection_id']
                if connection_id in self.connection_configs:
                    self.connection_configs[connection_id]['flow_controller'].record_failure()
            
            self.stats['failed_pushes'] += 1
    
    async def _process_single_task(
        self,
        push_task: Dict[str, Any],
        config: Dict[str, Any],
        stats: Dict[str, Any]
    ):
        """处理单个推送任务"""
        connection_id = push_task['connection_id']
        data_type = push_task['data_type']
        data_content = push_task['data_content']
        delta = push_task.get('delta')
        
        # 准备推送数据
        if delta and not push_task.get('force_full'):
            # 增量推送
            push_data = {
                'type': 'incremental_update',
                'data_type': data_type,
                'delta': delta.to_dict(),
                'timestamp': push_task['timestamp']
            }
            self.stats['incremental_pushes'] += 1
        else:
            # 全量推送
            push_data = {
                'type': 'full_update',
                'data_type': data_type,
                'content': data_content,
                'timestamp': push_task['timestamp']
            }
            self.stats['full_pushes'] += 1
        
        # 压缩数据
        compressed_data, compression_type = self.compression_manager.compress_data(
            push_data,
            config['compression_type'],
            self.compression_threshold
        )
        
        # 模拟发送数据 (实际实现中会调用WebSocket发送)
        await self._simulate_send(connection_id, compressed_data, compression_type)
        
        # 更新统计
        stats['pushes_sent'] += 1
        stats['bytes_sent'] += len(compressed_data)
        stats['last_push_time'] = time.time()
        
        self.stats['total_pushes'] += 1
        self.stats['bytes_sent'] += len(compressed_data)
    
    async def _process_batch_task(
        self,
        batch_task: Dict[str, Any],
        config: Dict[str, Any],
        stats: Dict[str, Any]
    ):
        """处理批量推送任务"""
        connection_id = batch_task['connection_id']
        tasks = batch_task['batch_tasks']
        
        # 合并批量数据
        batch_data = {
            'type': 'batch_update',
            'updates': [],
            'timestamp': batch_task['timestamp']
        }
        
        for task in tasks:
            delta = task.get('delta')
            if delta and not task.get('force_full'):
                update = {
                    'type': 'incremental',
                    'data_type': task['data_type'],
                    'delta': delta.to_dict()
                }
            else:
                update = {
                    'type': 'full',
                    'data_type': task['data_type'],
                    'content': task['data_content']
                }
            
            batch_data['updates'].append(update)
        
        # 压缩批量数据
        compressed_data, compression_type = self.compression_manager.compress_data(
            batch_data,
            config['compression_type'],
            self.compression_threshold
        )
        
        # 模拟发送数据
        await self._simulate_send(connection_id, compressed_data, compression_type)
        
        # 更新统计
        stats['pushes_sent'] += 1
        stats['bytes_sent'] += len(compressed_data)
        stats['last_push_time'] = time.time()
        
        self.stats['total_pushes'] += 1
        self.stats['bytes_sent'] += len(compressed_data)
        self.stats['batched_pushes'] += 1
    
    async def _simulate_send(
        self,
        connection_id: str,
        data: bytes,
        compression_type: CompressionType
    ):
        """
        模拟发送数据 (实际实现中会调用WebSocket发送)
        
        Args:
            connection_id: 连接ID
            data: 数据
            compression_type: 压缩类型
        """
        # 这里应该调用实际的WebSocket发送逻辑
        # 目前只是模拟延迟
        await asyncio.sleep(0.001)  # 模拟1ms网络延迟
        
        logger.debug(
            f"Sent {len(data)} bytes to {connection_id} "
            f"(compression: {compression_type.value})"
        )
    
    async def _batch_processor(self):
        """批量处理器"""
        while True:
            try:
                await asyncio.sleep(self.batch_timeout)
                
                # 检查是否需要刷新批次
                if (self.batch_queue and 
                    time.time() - self.last_batch_time > self.batch_timeout):
                    await self._flush_batch()
                
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
    
    async def _stats_updater(self):
        """统计更新器"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟更新一次
                
                # 缓存统计到Redis
                await self._cache_stats()
                
            except Exception as e:
                logger.error(f"Error in stats updater: {e}")
    
    async def _cache_stats(self):
        """缓存统计到Redis"""
        try:
            if self.redis_client:
                # 缓存全局统计
                global_stats = self.get_stats()
                await self.redis_client.setex(
                    "dashboard:push_optimization:stats",
                    300,  # 5分钟过期
                    json.dumps(global_stats, ensure_ascii=False)
                )
                
                # 缓存连接统计
                for connection_id, stats in self.connection_stats.items():
                    key = f"dashboard:push_optimization:connection:{connection_id}"
                    await self.redis_client.setex(
                        key,
                        300,
                        json.dumps(stats, ensure_ascii=False)
                    )
                
        except Exception as e:
            logger.error(f"Error caching stats: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'compression_stats': self.compression_manager.get_stats(),
            'flow_control_stats': self.flow_controller.get_stats(),
            'queue_size': self.push_queue.qsize(),
            'batch_queue_size': len(self.batch_queue),
            'active_connections': len(self.connection_configs),
            'background_tasks': len(self.background_tasks)
        }
    
    def get_connection_stats(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接统计"""
        if connection_id not in self.connection_stats:
            return None
        
        stats = self.connection_stats[connection_id].copy()
        
        if connection_id in self.connection_configs:
            config = self.connection_configs[connection_id]
            stats['flow_control'] = config['flow_controller'].get_stats()
            stats['configuration'] = {
                'push_strategy': config['push_strategy'].value,
                'compression_type': config['compression_type'].value,
                'flow_control_mode': config['flow_control_mode'].value,
                'max_rate': config['max_rate'],
                'enable_incremental': config['enable_incremental']
            }
        
        return stats
    
    async def force_flush_all(self):
        """强制刷新所有待处理数据"""
        await self._flush_batch()
    
    async def shutdown(self):
        """关闭服务"""
        try:
            # 刷新所有待处理数据
            await self.force_flush_all()
            
            # 取消所有后台任务
            for task in self.background_tasks:
                task.cancel()
            
            # 等待任务完成
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # 清理数据
            self.connection_configs.clear()
            self.connection_stats.clear()
            self.batch_queue.clear()
            
            logger.info("Dashboard push optimization service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during push optimization service shutdown: {e}")


# 全局实例
dashboard_push_optimization_service: Optional[DashboardPushOptimizationService] = None


def get_dashboard_push_optimization_service() -> DashboardPushOptimizationService:
    """获取仪表板推送优化服务实例"""
    global dashboard_push_optimization_service
    
    if dashboard_push_optimization_service is None:
        dashboard_push_optimization_service = DashboardPushOptimizationService()
    
    return dashboard_push_optimization_service