"""
AI助手Redis缓存策略服务

本模块实现了AI助手模块的完整缓存策略，包括：
1. 对话上下文缓存 - 快速恢复对话状态
2. AI响应缓存 - 避免重复调用AI服务
3. 用户偏好缓存 - 提升个性化体验
4. 模型配置缓存 - 快速获取AI模型配置
5. 会话状态缓存 - 实时同步会话状态
6. 智能建议缓存 - 缓存生成的建议结果

技术特性：
- 多级缓存策略（L1内存 + L2Redis）
- 智能TTL管理和缓存失效
- 缓存预热和批量操作
- 缓存命中率监控和优化
- 数据一致性保证
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from ..core.redis import redis_service
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "l1_memory"      # L1内存缓存
    L2_REDIS = "l2_redis"        # L2Redis缓存
    BOTH = "both"                # 双级缓存


class CacheStrategy(Enum):
    """缓存策略"""
    WRITE_THROUGH = "write_through"      # 写穿透
    WRITE_BACK = "write_back"           # 写回
    WRITE_AROUND = "write_around"       # 写绕过
    READ_THROUGH = "read_through"       # 读穿透
    CACHE_ASIDE = "cache_aside"         # 缓存旁路


class CacheKeyType(Enum):
    """缓存键类型"""
    CONVERSATION_CONTEXT = "conv_ctx"    # 对话上下文
    AI_RESPONSE = "ai_resp"             # AI响应
    USER_PREFERENCES = "user_pref"       # 用户偏好
    MODEL_CONFIG = "model_cfg"          # 模型配置
    SESSION_STATE = "sess_state"        # 会话状态
    SUGGESTIONS = "suggestions"          # 智能建议
    TEMPLATE = "template"               # 提示词模板
    USAGE_STATS = "usage_stats"         # 使用统计
    HEALTH_CHECK = "health_check"       # 健康检查


@dataclass
class CacheConfig:
    """缓存配置"""
    ttl: int                            # 生存时间（秒）
    max_size: Optional[int] = None      # 最大大小
    compression: bool = False           # 是否压缩
    encryption: bool = False            # 是否加密
    strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE
    level: CacheLevel = CacheLevel.L2_REDIS
    auto_refresh: bool = False          # 自动刷新
    batch_size: int = 100              # 批量操作大小


@dataclass
class CacheMetrics:
    """缓存指标"""
    hits: int = 0                      # 命中次数
    misses: int = 0                    # 未命中次数
    sets: int = 0                      # 设置次数
    deletes: int = 0                   # 删除次数
    evictions: int = 0                 # 驱逐次数
    total_size: int = 0                # 总大小
    avg_access_time: float = 0.0       # 平均访问时间
    
    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """未命中率"""
        return 1.0 - self.hit_rate


class CacheKeyGenerator:
    """缓存键生成器"""
    
    @staticmethod
    def generate_key(key_type: CacheKeyType, *args, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            key_type: 缓存键类型
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            str: 生成的缓存键
        """
        # 基础前缀
        prefix = f"ai_assistant:{key_type.value}"
        
        # 构建键组件
        key_parts = [prefix]
        
        # 添加位置参数
        for arg in args:
            if isinstance(arg, (int, str)):
                key_parts.append(str(arg))
            else:
                # 对复杂对象进行哈希
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # 添加关键字参数（按键排序确保一致性）
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = "&".join(f"{k}={v}" for k, v in sorted_kwargs)
            key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])
        
        return ":".join(key_parts)
    
    @staticmethod
    def generate_pattern(key_type: CacheKeyType, pattern: str = "*") -> str:
        """
        生成缓存键模式
        
        Args:
            key_type: 缓存键类型
            pattern: 匹配模式
            
        Returns:
            str: 缓存键模式
        """
        return f"ai_assistant:{key_type.value}:{pattern}"


class AICacheService:
    """AI助手缓存服务"""
    
    def __init__(self):
        self.redis = redis_service
        self.metrics: Dict[str, CacheMetrics] = {}
        self.l1_cache: Dict[str, Any] = {}  # L1内存缓存
        self.l1_cache_timestamps: Dict[str, datetime] = {}
        
        # 缓存配置
        self.cache_configs = self._initialize_cache_configs()
        
        # 初始化指标
        for key_type in CacheKeyType:
            self.metrics[key_type.value] = CacheMetrics()
    
    def _initialize_cache_configs(self) -> Dict[CacheKeyType, CacheConfig]:
        """初始化缓存配置"""
        return {
            # 对话上下文缓存 - 高频访问，中等TTL
            CacheKeyType.CONVERSATION_CONTEXT: CacheConfig(
                ttl=3600,  # 1小时
                max_size=1000,
                compression=True,
                strategy=CacheStrategy.WRITE_THROUGH,
                level=CacheLevel.BOTH,
                auto_refresh=True
            ),
            
            # AI响应缓存 - 长期缓存，避免重复调用
            CacheKeyType.AI_RESPONSE: CacheConfig(
                ttl=86400,  # 24小时
                max_size=5000,
                compression=True,
                strategy=CacheStrategy.CACHE_ASIDE,
                level=CacheLevel.L2_REDIS
            ),
            
            # 用户偏好缓存 - 长期缓存，低频更新
            CacheKeyType.USER_PREFERENCES: CacheConfig(
                ttl=7200,  # 2小时
                max_size=10000,
                strategy=CacheStrategy.WRITE_THROUGH,
                level=CacheLevel.BOTH
            ),
            
            # 模型配置缓存 - 长期缓存，很少更新
            CacheKeyType.MODEL_CONFIG: CacheConfig(
                ttl=43200,  # 12小时
                strategy=CacheStrategy.WRITE_THROUGH,
                level=CacheLevel.BOTH,
                auto_refresh=True
            ),
            
            # 会话状态缓存 - 短期缓存，高频更新
            CacheKeyType.SESSION_STATE: CacheConfig(
                ttl=1800,  # 30分钟
                strategy=CacheStrategy.WRITE_THROUGH,
                level=CacheLevel.BOTH
            ),
            
            # 智能建议缓存 - 中期缓存，计算成本高
            CacheKeyType.SUGGESTIONS: CacheConfig(
                ttl=7200,  # 2小时
                max_size=2000,
                compression=True,
                strategy=CacheStrategy.CACHE_ASIDE,
                level=CacheLevel.L2_REDIS
            ),
            
            # 提示词模板缓存 - 长期缓存，很少更新
            CacheKeyType.TEMPLATE: CacheConfig(
                ttl=86400,  # 24小时
                strategy=CacheStrategy.WRITE_THROUGH,
                level=CacheLevel.BOTH
            ),
            
            # 使用统计缓存 - 短期缓存，频繁更新
            CacheKeyType.USAGE_STATS: CacheConfig(
                ttl=300,  # 5分钟
                strategy=CacheStrategy.WRITE_BACK,
                level=CacheLevel.L2_REDIS
            ),
            
            # 健康检查缓存 - 极短期缓存
            CacheKeyType.HEALTH_CHECK: CacheConfig(
                ttl=60,  # 1分钟
                strategy=CacheStrategy.CACHE_ASIDE,
                level=CacheLevel.L2_REDIS
            )
        }
    
    async def get(self, key_type: CacheKeyType, *args, **kwargs) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key_type: 缓存键类型
            *args: 键参数
            **kwargs: 键参数
            
        Returns:
            Optional[Any]: 缓存的数据，如果不存在返回None
        """
        start_time = datetime.utcnow()
        cache_key = CacheKeyGenerator.generate_key(key_type, *args, **kwargs)
        config = self.cache_configs[key_type]
        
        try:
            # L1缓存查找
            if config.level in [CacheLevel.L1_MEMORY, CacheLevel.BOTH]:
                if cache_key in self.l1_cache:
                    # 检查L1缓存是否过期
                    if self._is_l1_cache_valid(cache_key, config.ttl):
                        self._update_metrics(key_type, "hit", start_time)
                        logger.debug(f"L1 cache hit for key: {cache_key}")
                        return self.l1_cache[cache_key]
                    else:
                        # L1缓存过期，删除
                        del self.l1_cache[cache_key]
                        del self.l1_cache_timestamps[cache_key]
            
            # L2 Redis缓存查找
            if config.level in [CacheLevel.L2_REDIS, CacheLevel.BOTH]:
                cached_data = self.redis.get(cache_key)
                if cached_data is not None:
                    # 如果配置了双级缓存，更新L1缓存
                    if config.level == CacheLevel.BOTH:
                        self.l1_cache[cache_key] = cached_data
                        self.l1_cache_timestamps[cache_key] = datetime.utcnow()
                    
                    self._update_metrics(key_type, "hit", start_time)
                    logger.debug(f"L2 cache hit for key: {cache_key}")
                    return cached_data
            
            # 缓存未命中
            self._update_metrics(key_type, "miss", start_time)
            logger.debug(f"Cache miss for key: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache for key {cache_key}: {str(e)}")
            self._update_metrics(key_type, "miss", start_time)
            return None
    
    async def set(self, key_type: CacheKeyType, value: Any, *args, 
                  ttl: Optional[int] = None, **kwargs) -> bool:
        """
        设置缓存数据
        
        Args:
            key_type: 缓存键类型
            value: 要缓存的数据
            *args: 键参数
            ttl: 自定义TTL，如果不提供则使用配置的TTL
            **kwargs: 键参数
            
        Returns:
            bool: 是否设置成功
        """
        start_time = datetime.utcnow()
        cache_key = CacheKeyGenerator.generate_key(key_type, *args, **kwargs)
        config = self.cache_configs[key_type]
        effective_ttl = ttl or config.ttl
        
        try:
            success = True
            
            # L1缓存设置
            if config.level in [CacheLevel.L1_MEMORY, CacheLevel.BOTH]:
                self.l1_cache[cache_key] = value
                self.l1_cache_timestamps[cache_key] = datetime.utcnow()
                
                # L1缓存大小控制
                if config.max_size and len(self.l1_cache) > config.max_size:
                    self._evict_l1_cache(key_type)
            
            # L2 Redis缓存设置
            if config.level in [CacheLevel.L2_REDIS, CacheLevel.BOTH]:
                redis_success = self.redis.set(cache_key, value, expire=effective_ttl)
                success = success and redis_success
            
            if success:
                self._update_metrics(key_type, "set", start_time)
                logger.debug(f"Cache set for key: {cache_key}, TTL: {effective_ttl}s")
            else:
                logger.warning(f"Failed to set cache for key: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting cache for key {cache_key}: {str(e)}")
            return False
    
    async def delete(self, key_type: CacheKeyType, *args, **kwargs) -> bool:
        """
        删除缓存数据
        
        Args:
            key_type: 缓存键类型
            *args: 键参数
            **kwargs: 键参数
            
        Returns:
            bool: 是否删除成功
        """
        start_time = datetime.utcnow()
        cache_key = CacheKeyGenerator.generate_key(key_type, *args, **kwargs)
        config = self.cache_configs[key_type]
        
        try:
            success = True
            
            # L1缓存删除
            if config.level in [CacheLevel.L1_MEMORY, CacheLevel.BOTH]:
                if cache_key in self.l1_cache:
                    del self.l1_cache[cache_key]
                    del self.l1_cache_timestamps[cache_key]
            
            # L2 Redis缓存删除
            if config.level in [CacheLevel.L2_REDIS, CacheLevel.BOTH]:
                redis_success = self.redis.delete(cache_key)
                success = success and redis_success
            
            if success:
                self._update_metrics(key_type, "delete", start_time)
                logger.debug(f"Cache deleted for key: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting cache for key {cache_key}: {str(e)}")
            return False
    
    async def clear_pattern(self, key_type: CacheKeyType, pattern: str = "*") -> int:
        """
        按模式清除缓存
        
        Args:
            key_type: 缓存键类型
            pattern: 匹配模式
            
        Returns:
            int: 清除的键数量
        """
        try:
            cache_pattern = CacheKeyGenerator.generate_pattern(key_type, pattern)
            
            # 获取匹配的键
            keys = self.redis.keys(cache_pattern)
            if not keys:
                return 0
            
            # 批量删除Redis缓存
            deleted_count = 0
            for key in keys:
                if self.redis.delete(key):
                    deleted_count += 1
            
            # 清除L1缓存中匹配的键
            l1_keys_to_delete = []
            for l1_key in self.l1_cache.keys():
                if l1_key.startswith(f"ai_assistant:{key_type.value}:"):
                    l1_keys_to_delete.append(l1_key)
            
            for l1_key in l1_keys_to_delete:
                del self.l1_cache[l1_key]
                if l1_key in self.l1_cache_timestamps:
                    del self.l1_cache_timestamps[l1_key]
            
            logger.info(f"Cleared {deleted_count} cache entries for pattern: {cache_pattern}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing cache pattern {cache_pattern}: {str(e)}")
            return 0
    
    async def get_or_set(self, key_type: CacheKeyType, factory_func, *args, 
                        ttl: Optional[int] = None, **kwargs) -> Any:
        """
        获取缓存数据，如果不存在则通过工厂函数生成并缓存
        
        Args:
            key_type: 缓存键类型
            factory_func: 数据生成函数
            *args: 键参数
            ttl: 自定义TTL
            **kwargs: 键参数
            
        Returns:
            Any: 缓存的数据或新生成的数据
        """
        # 先尝试获取缓存
        cached_data = await self.get(key_type, *args, **kwargs)
        if cached_data is not None:
            return cached_data
        
        # 缓存未命中，生成新数据
        try:
            if asyncio.iscoroutinefunction(factory_func):
                new_data = await factory_func()
            else:
                new_data = factory_func()
            
            # 缓存新数据
            await self.set(key_type, new_data, *args, ttl=ttl, **kwargs)
            return new_data
            
        except Exception as e:
            logger.error(f"Error in factory function for cache key {key_type}: {str(e)}")
            raise
    
    async def batch_get(self, key_type: CacheKeyType, 
                       key_args_list: List[Tuple]) -> Dict[str, Any]:
        """
        批量获取缓存数据
        
        Args:
            key_type: 缓存键类型
            key_args_list: 键参数列表
            
        Returns:
            Dict[str, Any]: 键值对字典
        """
        results = {}
        
        try:
            # 生成所有缓存键
            cache_keys = []
            key_mapping = {}
            
            for key_args in key_args_list:
                if isinstance(key_args, tuple):
                    # 格式: (arg1, arg2, ...)
                    cache_key = CacheKeyGenerator.generate_key(key_type, *key_args)
                else:
                    # 单个参数
                    cache_key = CacheKeyGenerator.generate_key(key_type, key_args)
                
                cache_keys.append(cache_key)
                key_mapping[cache_key] = key_args
            
            # 批量获取Redis缓存
            config = self.cache_configs[key_type]
            if config.level in [CacheLevel.L2_REDIS, CacheLevel.BOTH]:
                for cache_key in cache_keys:
                    cached_data = self.redis.get(cache_key)
                    if cached_data is not None:
                        results[cache_key] = cached_data
            
            logger.debug(f"Batch get returned {len(results)} items for {len(cache_keys)} keys")
            return results
            
        except Exception as e:
            logger.error(f"Error in batch get for key type {key_type}: {str(e)}")
            return {}
    
    async def batch_set(self, key_type: CacheKeyType, 
                       data_dict: Dict[Tuple, Any], ttl: Optional[int] = None) -> int:
        """
        批量设置缓存数据
        
        Args:
            key_type: 缓存键类型
            data_dict: 数据字典，键为参数元组，值为要缓存的数据
            ttl: 自定义TTL
            
        Returns:
            int: 成功设置的数量
        """
        success_count = 0
        
        try:
            for key_args, value in data_dict.items():
                if isinstance(key_args, tuple):
                    # 格式: (arg1, arg2, ...)
                    if await self.set(key_type, value, *key_args, ttl=ttl):
                        success_count += 1
                else:
                    # 单个参数
                    if await self.set(key_type, value, key_args, ttl=ttl):
                        success_count += 1
            
            logger.debug(f"Batch set completed: {success_count}/{len(data_dict)} items")
            return success_count
            
        except Exception as e:
            logger.error(f"Error in batch set for key type {key_type}: {str(e)}")
            return success_count
    
    def _is_l1_cache_valid(self, cache_key: str, ttl: int) -> bool:
        """检查L1缓存是否有效"""
        if cache_key not in self.l1_cache_timestamps:
            return False
        
        timestamp = self.l1_cache_timestamps[cache_key]
        return (datetime.utcnow() - timestamp).total_seconds() < ttl
    
    def _evict_l1_cache(self, key_type: CacheKeyType):
        """L1缓存驱逐策略（LRU）"""
        try:
            # 找到最旧的缓存项
            prefix = f"ai_assistant:{key_type.value}:"
            oldest_key = None
            oldest_time = datetime.utcnow()
            
            for cache_key, timestamp in self.l1_cache_timestamps.items():
                if cache_key.startswith(prefix) and timestamp < oldest_time:
                    oldest_time = timestamp
                    oldest_key = cache_key
            
            # 删除最旧的缓存项
            if oldest_key:
                del self.l1_cache[oldest_key]
                del self.l1_cache_timestamps[oldest_key]
                self.metrics[key_type.value].evictions += 1
                logger.debug(f"Evicted L1 cache key: {oldest_key}")
                
        except Exception as e:
            logger.error(f"Error evicting L1 cache: {str(e)}")
    
    def _update_metrics(self, key_type: CacheKeyType, operation: str, start_time: datetime):
        """更新缓存指标"""
        try:
            metrics = self.metrics[key_type.value]
            access_time = (datetime.utcnow() - start_time).total_seconds()
            
            if operation == "hit":
                metrics.hits += 1
            elif operation == "miss":
                metrics.misses += 1
            elif operation == "set":
                metrics.sets += 1
            elif operation == "delete":
                metrics.deletes += 1
            
            # 更新平均访问时间
            total_operations = metrics.hits + metrics.misses + metrics.sets + metrics.deletes
            if total_operations > 1:
                metrics.avg_access_time = (
                    (metrics.avg_access_time * (total_operations - 1) + access_time) / total_operations
                )
            else:
                metrics.avg_access_time = access_time
                
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
    
    def get_metrics(self, key_type: Optional[CacheKeyType] = None) -> Dict[str, CacheMetrics]:
        """
        获取缓存指标
        
        Args:
            key_type: 特定的缓存键类型，如果不提供则返回所有指标
            
        Returns:
            Dict[str, CacheMetrics]: 缓存指标字典
        """
        if key_type:
            return {key_type.value: self.metrics[key_type.value]}
        return self.metrics.copy()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        total_l1_size = len(self.l1_cache)
        
        info = {
            "l1_cache_size": total_l1_size,
            "l1_cache_keys": list(self.l1_cache.keys())[:10],  # 只显示前10个键
            "redis_connected": self.redis.is_connected(),
            "cache_configs": {k.value: asdict(v) for k, v in self.cache_configs.items()},
            "metrics_summary": {
                k: {
                    "hit_rate": v.hit_rate,
                    "total_operations": v.hits + v.misses + v.sets + v.deletes,
                    "avg_access_time": v.avg_access_time
                }
                for k, v in self.metrics.items()
            }
        }
        
        return info
    
    async def warm_up_cache(self, key_type: CacheKeyType, data_loader_func) -> int:
        """
        缓存预热
        
        Args:
            key_type: 缓存键类型
            data_loader_func: 数据加载函数
            
        Returns:
            int: 预热的数据条数
        """
        try:
            logger.info(f"Starting cache warm-up for {key_type.value}")
            
            # 调用数据加载函数获取预热数据
            if asyncio.iscoroutinefunction(data_loader_func):
                warm_up_data = await data_loader_func()
            else:
                warm_up_data = data_loader_func()
            
            if not isinstance(warm_up_data, dict):
                logger.warning(f"Warm-up data should be a dict, got {type(warm_up_data)}")
                return 0
            
            # 批量设置缓存
            success_count = await self.batch_set(key_type, warm_up_data)
            
            logger.info(f"Cache warm-up completed for {key_type.value}: {success_count} items")
            return success_count
            
        except Exception as e:
            logger.error(f"Error warming up cache for {key_type.value}: {str(e)}")
            return 0
    
    async def cleanup_expired_cache(self) -> Dict[str, int]:
        """清理过期缓存"""
        cleanup_stats = {}
        
        try:
            # 清理L1缓存中的过期项
            current_time = datetime.utcnow()
            expired_l1_keys = []
            
            for cache_key, timestamp in self.l1_cache_timestamps.items():
                # 根据键类型获取TTL
                key_type_str = cache_key.split(":")[1] if ":" in cache_key else "unknown"
                key_type = None
                
                for kt in CacheKeyType:
                    if kt.value == key_type_str:
                        key_type = kt
                        break
                
                if key_type and key_type in self.cache_configs:
                    ttl = self.cache_configs[key_type].ttl
                    if (current_time - timestamp).total_seconds() > ttl:
                        expired_l1_keys.append(cache_key)
            
            # 删除过期的L1缓存项
            for key in expired_l1_keys:
                del self.l1_cache[key]
                del self.l1_cache_timestamps[key]
            
            cleanup_stats["l1_expired"] = len(expired_l1_keys)
            
            # Redis缓存由Redis自动处理TTL，这里只记录统计
            cleanup_stats["l2_auto_handled"] = True
            
            if expired_l1_keys:
                logger.info(f"Cleaned up {len(expired_l1_keys)} expired L1 cache entries")
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {str(e)}")
            return {"error": str(e)}


# 创建全局缓存服务实例
ai_cache_service = AICacheService()


# 缓存装饰器
def cache_result(key_type: CacheKeyType, ttl: Optional[int] = None, 
                key_func: Optional[callable] = None):
    """
    缓存结果装饰器
    
    Args:
        key_type: 缓存键类型
        ttl: 自定义TTL
        key_func: 自定义键生成函数
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键参数
            if key_func:
                cache_args = key_func(*args, **kwargs)
            else:
                cache_args = args
            
            # 尝试从缓存获取
            cached_result = await ai_cache_service.get(key_type, *cache_args)
            if cached_result is not None:
                return cached_result
            
            # 执行原函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 缓存结果
            await ai_cache_service.set(key_type, result, *cache_args, ttl=ttl)
            return result
        
        return wrapper
    return decorator


# 导入asyncio用于异步操作
import asyncio