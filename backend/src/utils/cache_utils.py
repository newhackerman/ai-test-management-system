"""
缓存工具函数

提供缓存操作的通用工具函数和装饰器
"""

import json
import pickle
import gzip
import time
import hashlib
from typing import Any, Optional, Dict, List, Callable, Union
from functools import wraps
from datetime import datetime, timedelta
import redis
import asyncio
# NOTE (round 5 / U2): the old code imported `aioredis` here. aioredis 2.0.1
# (last release, 2021) cannot be imported on Python 3.12 at all:
# without setuptools it raises ModuleNotFoundError (distutils removed);
# with setuptools it raises TypeError (duplicate base class TimeoutError),
# which the old ImportError-only guard did not catch, so importing this
# module crashed backend startup (verified in a fresh venv, exit 1).
# aioredis was merged into redis-py as `redis.asyncio` — the official
# successor, shipped with the already-declared `redis` package — so the
# async client now comes from there and `aioredis` is deliberately NOT
# listed in requirements.txt.
try:
    import redis.asyncio as aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    AIOREDIS_AVAILABLE = False
from ..core.cache_config import DashboardCacheConfig, CacheStrategy, CacheMonitoring

class CacheClient:
    """缓存客户端封装"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[aioredis.Redis] = None
        self.config = DashboardCacheConfig()
        self.strategy = CacheStrategy()
        self.monitoring = CacheMonitoring()
        
        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
    
    @property
    def sync_client(self) -> redis.Redis:
        """获取同步Redis客户端"""
        if self._sync_client is None:
            self._sync_client = redis.from_url(self.redis_url, decode_responses=True)
        return self._sync_client
    
    @property
    async def async_client(self):
        """获取异步Redis客户端"""
        if self._async_client is None:
            if AIOREDIS_AVAILABLE:
                self._async_client = aioredis.from_url(self.redis_url, decode_responses=True)
            else:
                # 使用同步客户端作为fallback
                self._async_client = self.sync_client
        return self._async_client
    
    def _serialize_data(self, data: Any, compression: bool = False) -> str:
        """序列化数据"""
        try:
            # JSON序列化
            json_data = json.dumps(data, ensure_ascii=False, default=str)
            
            if compression:
                # GZIP压缩
                compressed_data = gzip.compress(json_data.encode('utf-8'))
                return f"gzip:{compressed_data.hex()}"
            
            return f"json:{json_data}"
            
        except Exception as e:
            # 降级到pickle序列化
            try:
                pickle_data = pickle.dumps(data)
                if compression:
                    compressed_data = gzip.compress(pickle_data)
                    return f"gzip_pickle:{compressed_data.hex()}"
                return f"pickle:{pickle_data.hex()}"
            except Exception:
                raise ValueError(f"Failed to serialize data: {e}")
    
    def _deserialize_data(self, serialized_data: str) -> Any:
        """反序列化数据"""
        try:
            if serialized_data.startswith("gzip:"):
                # GZIP解压缩JSON
                hex_data = serialized_data[5:]
                compressed_data = bytes.fromhex(hex_data)
                json_data = gzip.decompress(compressed_data).decode('utf-8')
                return json.loads(json_data)
            
            elif serialized_data.startswith("gzip_pickle:"):
                # GZIP解压缩Pickle
                hex_data = serialized_data[12:]
                compressed_data = bytes.fromhex(hex_data)
                pickle_data = gzip.decompress(compressed_data)
                return pickle.loads(pickle_data)
            
            elif serialized_data.startswith("json:"):
                # JSON反序列化
                json_data = serialized_data[5:]
                return json.loads(json_data)
            
            elif serialized_data.startswith("pickle:"):
                # Pickle反序列化
                hex_data = serialized_data[7:]
                pickle_data = bytes.fromhex(hex_data)
                return pickle.loads(pickle_data)
            
            else:
                # 尝试直接JSON解析
                return json.loads(serialized_data)
                
        except Exception as e:
            raise ValueError(f"Failed to deserialize data: {e}")
    
    def get(self, key_type: str, **kwargs) -> Optional[Any]:
        """获取缓存数据（同步）"""
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            
            start_time = time.time()
            serialized_data = self.sync_client.get(cache_key)
            response_time = (time.time() - start_time) * 1000
            
            if serialized_data:
                self.stats["hits"] += 1
                data = self._deserialize_data(serialized_data)
                
                # 记录监控指标
                self._record_metric("response_time", response_time)
                
                return data
            else:
                self.stats["misses"] += 1
                return None
                
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache get error: {e}")
            return None
    
    async def aget(self, key_type: str, **kwargs) -> Optional[Any]:
        """获取缓存数据（异步）"""
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            client = await self.async_client
            
            start_time = time.time()
            serialized_data = await client.get(cache_key)
            response_time = (time.time() - start_time) * 1000
            
            if serialized_data:
                self.stats["hits"] += 1
                data = self._deserialize_data(serialized_data)
                
                # 记录监控指标
                self._record_metric("response_time", response_time)
                
                return data
            else:
                self.stats["misses"] += 1
                return None
                
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache aget error: {e}")
            return None
    
    def set(self, key_type: str, data: Any, ttl: Optional[int] = None, **kwargs) -> bool:
        """设置缓存数据（同步）"""
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            
            if ttl is None:
                ttl = self.config.get_ttl(key_type)
            
            compression = self.config.should_compress(key_type)
            serialized_data = self._serialize_data(data, compression)
            
            if ttl > 0:
                result = self.sync_client.setex(cache_key, ttl, serialized_data)
            else:
                result = self.sync_client.set(cache_key, serialized_data)
            
            if result:
                self.stats["sets"] += 1
                return True
            
            return False
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache set error: {e}")
            return False
    
    async def aset(self, key_type: str, data: Any, ttl: Optional[int] = None, **kwargs) -> bool:
        """设置缓存数据（异步）"""
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            client = await self.async_client
            
            if ttl is None:
                ttl = self.config.get_ttl(key_type)
            
            compression = self.config.should_compress(key_type)
            serialized_data = self._serialize_data(data, compression)
            
            if ttl > 0:
                result = await client.setex(cache_key, ttl, serialized_data)
            else:
                result = await client.set(cache_key, serialized_data)
            
            if result:
                self.stats["sets"] += 1
                return True
            
            return False
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache aset error: {e}")
            return False
    
    def delete(self, key_type: str, **kwargs) -> bool:
        """删除缓存数据（同步）"""
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            result = self.sync_client.delete(cache_key)
            
            if result:
                self.stats["deletes"] += 1
                return True
            
            return False
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache delete error: {e}")
            return False
    
    async def adelete(self, key_type: str, **kwargs) -> bool:
        """删除缓存数据（异步）"""
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            client = await self.async_client
            result = await client.delete(cache_key)
            
            if result:
                self.stats["deletes"] += 1
                return True
            
            return False
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache adelete error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """根据模式批量删除缓存"""
        try:
            keys = self.sync_client.keys(pattern)
            if keys:
                result = self.sync_client.delete(*keys)
                self.stats["deletes"] += result
                return result
            return 0
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache invalidate_pattern error: {e}")
            return 0
    
    async def ainvalidate_pattern(self, pattern: str) -> int:
        """根据模式批量删除缓存（异步）"""
        try:
            client = await self.async_client
            keys = await client.keys(pattern)
            if keys:
                result = await client.delete(*keys)
                self.stats["deletes"] += result
                return result
            return 0
            
        except Exception as e:
            self.stats["errors"] += 1
            print(f"Cache ainvalidate_pattern error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "deletes": self.stats["deletes"],
            "errors": self.stats["errors"],
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 2),
            "miss_rate": round(100 - hit_rate, 2)
        }
    
    def _record_metric(self, metric_name: str, value: float):
        """记录监控指标"""
        # 检查告警条件
        alert = self.monitoring.check_alert_condition(metric_name, value)
        if alert:
            print(f"Cache Alert: {alert['message']} (value: {value})")
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            start_time = time.time()
            self.sync_client.ping()
            response_time = (time.time() - start_time) * 1000
            
            info = self.sync_client.info()
            memory_usage = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            memory_usage_percent = (memory_usage / max_memory * 100) if max_memory > 0 else 0
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "memory_usage_bytes": memory_usage,
                "memory_usage_percent": round(memory_usage_percent, 2),
                "connected_clients": info.get('connected_clients', 0),
                "total_commands_processed": info.get('total_commands_processed', 0)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# 全局缓存客户端实例
cache_client = CacheClient()

def cache_result(key_type: str, ttl: Optional[int] = None, **cache_kwargs):
    """缓存函数结果的装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键参数
            cache_params = cache_kwargs.copy()
            
            # 如果函数有特定参数，添加到缓存键中
            if 'user_id' in kwargs:
                cache_params['user_id'] = kwargs['user_id']
            if 'project_id' in kwargs:
                cache_params['project_id'] = kwargs['project_id']
            
            # 尝试从缓存获取
            cached_result = cache_client.get(key_type, **cache_params)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            if result is not None:
                cache_client.set(key_type, result, ttl, **cache_params)
            
            return result
        
        return wrapper
    return decorator

def async_cache_result(key_type: str, ttl: Optional[int] = None, **cache_kwargs):
    """缓存异步函数结果的装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键参数
            cache_params = cache_kwargs.copy()
            
            # 如果函数有特定参数，添加到缓存键中
            if 'user_id' in kwargs:
                cache_params['user_id'] = kwargs['user_id']
            if 'project_id' in kwargs:
                cache_params['project_id'] = kwargs['project_id']
            
            # 尝试从缓存获取
            cached_result = await cache_client.aget(key_type, **cache_params)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            if result is not None:
                await cache_client.aset(key_type, result, ttl, **cache_params)
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache(key_type: str, **cache_kwargs):
    """缓存失效装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 执行成功后使缓存失效
            cache_params = cache_kwargs.copy()
            if 'user_id' in kwargs:
                cache_params['user_id'] = kwargs['user_id']
            if 'project_id' in kwargs:
                cache_params['project_id'] = kwargs['project_id']
            
            cache_client.delete(key_type, **cache_params)
            
            return result
        
        return wrapper
    return decorator

def batch_cache_get(key_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """批量获取缓存数据"""
    results = {}
    
    for config in key_configs:
        key_type = config['key_type']
        params = config.get('params', {})
        alias = config.get('alias', key_type)
        
        result = cache_client.get(key_type, **params)
        results[alias] = result
    
    return results

async def async_batch_cache_get(key_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """批量获取缓存数据（异步）"""
    results = {}
    
    tasks = []
    for config in key_configs:
        key_type = config['key_type']
        params = config.get('params', {})
        alias = config.get('alias', key_type)
        
        task = cache_client.aget(key_type, **params)
        tasks.append((alias, task))
    
    # 并发执行所有缓存获取
    for alias, task in tasks:
        result = await task
        results[alias] = result
    
    return results

def warm_up_cache(warm_up_configs: List[Dict[str, Any]]):
    """缓存预热"""
    for config in warm_up_configs:
        key_type = config['key_type']
        data_generator = config['data_generator']
        params = config.get('params', {})
        ttl = config.get('ttl')
        
        try:
            # 生成数据
            data = data_generator()
            
            # 设置缓存
            cache_client.set(key_type, data, ttl, **params)
            
            print(f"Cache warmed up: {key_type}")
            
        except Exception as e:
            print(f"Cache warm up failed for {key_type}: {e}")

def cache_key_generator(key_type: str, **kwargs) -> str:
    """生成缓存键"""
    return cache_client.config.get_cache_key(key_type, **kwargs)

def serialize_for_cache(data: Any, compression: bool = False) -> str:
    """序列化数据用于缓存"""
    return cache_client._serialize_data(data, compression)

def deserialize_from_cache(serialized_data: str) -> Any:
    """从缓存反序列化数据"""
    return cache_client._deserialize_data(serialized_data)

def get_cache_info() -> Dict[str, Any]:
    """获取缓存信息"""
    stats = cache_client.get_stats()
    health = cache_client.health_check()
    
    return {
        "statistics": stats,
        "health": health,
        "config": {
            "total_key_types": len(cache_client.config.CACHE_CONFIGS),
            "namespaces": [ns.value for ns in cache_client.config.CacheNamespace],
            "ttl_strategies": [ttl.name for ttl in cache_client.config.CacheTTL]
        }
    }