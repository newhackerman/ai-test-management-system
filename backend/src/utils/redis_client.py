"""
Redis客户端工具

本模块提供Redis连接和操作的工具函数，用于缓存管理和数据同步。
支持连接池管理、异步操作和错误处理。
"""
import asyncio
import json
import logging
from datetime import datetime, date
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 全局Redis连接池
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


class DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime对象"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class MockRedisClient:
    """Mock Redis客户端，用于测试环境或Redis不可用时"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
    
    async def get(self, key: str) -> Optional[str]:
        """获取键值"""
        import time
        current_time = time.time()
        
        if key in self._expiry and current_time > self._expiry[key]:
            # 键已过期
            del self._data[key]
            del self._expiry[key]
            return None
        
        return self._data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """设置键值"""
        self._data[key] = value
        
        if ex:
            import time
            self._expiry[key] = time.time() + ex
        
        return True
    
    async def setex(self, key: str, time: int, value: str) -> bool:
        """设置键值并指定过期时间"""
        return await self.set(key, value, ex=time)
    
    async def delete(self, *keys: str) -> int:
        """删除键"""
        deleted_count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                deleted_count += 1
            if key in self._expiry:
                del self._expiry[key]
        
        return deleted_count
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        result = await self.get(key)
        return result is not None
    
    async def keys(self, pattern: str) -> List[str]:
        """获取匹配模式的键列表"""
        import fnmatch
        return [key for key in self._data.keys() if fnmatch.fnmatch(key, pattern)]
    
    async def publish(self, channel: str, message: str) -> int:
        """发布消息（Mock实现）"""
        logger.debug(f"Mock Redis publish: {channel} -> {message}")
        return 1
    
    async def close(self):
        """关闭连接（Mock实现）"""
        pass


async def get_redis_client() -> redis.Redis:
    """
    获取Redis客户端实例
    
    Returns:
        redis.Redis: Redis客户端实例
    """
    global _redis_client, _redis_pool
    
    if _redis_client is not None:
        return _redis_client
    
    # 检查Redis是否可用
    if not REDIS_AVAILABLE:
        logger.warning("Redis库未安装，使用Mock客户端")
        _redis_client = MockRedisClient()
        return _redis_client
    
    try:
        # 从配置获取Redis连接信息
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
        redis_port = getattr(settings, 'REDIS_PORT', 6379)
        redis_db = getattr(settings, 'REDIS_DB', 0)
        redis_password = getattr(settings, 'REDIS_PASSWORD', None)
        
        # 创建连接池
        if redis_url and redis_url != 'redis://localhost:6379/0':
            _redis_pool = redis.ConnectionPool.from_url(
                redis_url,
                decode_responses=True,
                max_connections=20
            )
        else:
            _redis_pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                max_connections=20
            )
        
        # 创建Redis客户端
        _redis_client = redis.Redis(connection_pool=_redis_pool)
        
        # 测试连接
        await _redis_client.ping()
        logger.info("Redis连接成功")
        
        return _redis_client
        
    except Exception as e:
        logger.warning(f"Redis连接失败，使用Mock客户端: {e}")
        _redis_client = MockRedisClient()
        return _redis_client


async def close_redis_client():
    """关闭Redis客户端连接"""
    global _redis_client, _redis_pool
    
    if _redis_client:
        try:
            await _redis_client.close()
            logger.info("Redis客户端连接已关闭")
        except Exception as e:
            logger.warning(f"关闭Redis客户端时出错: {e}")
        finally:
            _redis_client = None
    
    if _redis_pool:
        try:
            await _redis_pool.disconnect()
            logger.info("Redis连接池已关闭")
        except Exception as e:
            logger.warning(f"关闭Redis连接池时出错: {e}")
        finally:
            _redis_pool = None


@asynccontextmanager
async def redis_client():
    """Redis客户端上下文管理器"""
    client = await get_redis_client()
    try:
        yield client
    finally:
        # 不在这里关闭客户端，因为它是全局共享的
        pass


class RedisCache:
    """Redis缓存工具类"""
    
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self._client = None
    
    async def _get_client(self):
        """获取Redis客户端"""
        if self._client is None:
            self._client = await get_redis_client()
        return self._client
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的键名"""
        return f"{self.prefix}:{key}" if self.prefix else key
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            Any: 缓存值或默认值
        """
        try:
            client = await self._get_client()
            value = await client.get(self._make_key(key))
            
            if value is None:
                return default
            
            # 尝试JSON解析
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return default
    
    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None, ex: Optional[int] = None
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            ex: 过期时间（秒），redis-py 风格的别名——调用方多处用
                ex=（recording_service、dashboard_integration 等）；
                此前本方法只认 ttl，传 ex= 会 TypeError，开始录制
                因此恒 500（第 14 项补用例时发现的真缺陷）。

        Returns:
            bool: 是否设置成功
        """
        if ex is not None:
            ttl = ex
        try:
            client = await self._get_client()
            
            # 序列化值
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, ensure_ascii=False, cls=DateTimeEncoder)
            else:
                serialized_value = str(value)
            
            if ttl:
                return await client.setex(self._make_key(key), ttl, serialized_value)
            else:
                return await client.set(self._make_key(key), serialized_value)
                
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """
        删除缓存键
        
        Args:
            keys: 要删除的键列表
            
        Returns:
            int: 删除的键数量
        """
        try:
            client = await self._get_client()
            prefixed_keys = [self._make_key(key) for key in keys]
            return await client.delete(*prefixed_keys)
            
        except Exception as e:
            logger.error(f"删除缓存失败 {keys}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 键是否存在
        """
        try:
            client = await self._get_client()
            return await client.exists(self._make_key(key))
            
        except Exception as e:
            logger.error(f"检查缓存存在性失败 {key}: {e}")
            return False
    
    async def keys(self, pattern: str) -> List[str]:
        """
        获取匹配模式的键列表
        
        Args:
            pattern: 匹配模式
            
        Returns:
            List[str]: 匹配的键列表
        """
        try:
            client = await self._get_client()
            full_pattern = self._make_key(pattern)
            keys = await client.keys(full_pattern)
            
            # 移除前缀
            if self.prefix:
                prefix_len = len(self.prefix) + 1
                return [key[prefix_len:] for key in keys]
            else:
                return keys
                
        except Exception as e:
            logger.error(f"获取缓存键列表失败 {pattern}: {e}")
            return []
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的所有键
        
        Args:
            pattern: 匹配模式
            
        Returns:
            int: 删除的键数量
        """
        try:
            keys = await self.keys(pattern)
            if keys:
                return await self.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"清除缓存模式失败 {pattern}: {e}")
            return 0


# 预定义的缓存实例
project_cache = RedisCache("project")
ai_cache = RedisCache("ai")
session_cache = RedisCache("session")


async def test_redis_connection() -> bool:
    """
    测试Redis连接
    
    Returns:
        bool: 连接是否成功
    """
    try:
        client = await get_redis_client()
        
        # 测试基本操作
        test_key = "test:connection"
        test_value = "test_value"
        
        # 设置值
        await client.set(test_key, test_value, ex=10)
        
        # 获取值
        result = await client.get(test_key)
        
        # 删除测试键
        await client.delete(test_key)
        
        # 验证结果
        success = result == test_value
        
        if success:
            logger.info("Redis连接测试成功")
        else:
            logger.warning("Redis连接测试失败：值不匹配")
        
        return success
        
    except Exception as e:
        logger.error(f"Redis连接测试失败: {e}")
        return False


# 启动时的初始化函数
async def init_redis():
    """初始化Redis连接"""
    try:
        client = await get_redis_client()
        logger.info("Redis客户端初始化成功")
        return client
    except Exception as e:
        logger.error(f"Redis客户端初始化失败: {e}")
        raise


# 清理函数
async def cleanup_redis():
    """清理Redis连接"""
    await close_redis_client()
# Alias for backward compatibility
RedisClient = RedisCache

# Export commonly used classes and functions
__all__ = [
    'get_redis_client',
    'close_redis_client', 
    'redis_client',
    'RedisCache',
    'RedisClient',  # Alias for RedisCache
    'MockRedisClient',
    'project_cache',
    'ai_cache', 
    'session_cache',
    'test_redis_connection',
    'init_redis',
    'cleanup_redis'
]