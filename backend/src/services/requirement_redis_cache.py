"""
需求管理Redis缓存服务

提供需求管理模块的Redis缓存功能，包括：
- 热点数据缓存
- 缓存失效策略
- 分布式缓存同步
- 缓存性能监控
"""
import json
import logging
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from functools import wraps
import asyncio

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError

from ..models.requirement import Requirement, RequirementStatus, RequirementType, Priority
from ..core.exceptions import CacheError, ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """缓存配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30


@dataclass
class CacheStats:
    """缓存统计信息"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_errors: int = 0
    avg_response_time: float = 0.0
    last_updated: datetime = None
    
    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        """缓存未命中率"""
        return 1.0 - self.hit_rate
    
    @property
    def error_rate(self) -> float:
        """缓存错误率"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_errors / self.total_requests


class RequirementRedisCache:
    """需求管理Redis缓存服务"""
    
    # 缓存键前缀
    KEY_PREFIX = "req_mgmt"
    
    # 缓存键模式
    CACHE_KEYS = {
        'requirement': f"{KEY_PREFIX}:requirement:{{id}}",
        'project_requirements': f"{KEY_PREFIX}:project:{{project_id}}:requirements",
        'requirement_stats': f"{KEY_PREFIX}:project:{{project_id}}:stats",
        'user_requirements': f"{KEY_PREFIX}:user:{{user_id}}:requirements",
        'requirement_search': f"{KEY_PREFIX}:search:{{hash}}",
        'requirement_dependencies': f"{KEY_PREFIX}:requirement:{{id}}:dependencies",
        'requirement_reviews': f"{KEY_PREFIX}:requirement:{{id}}:reviews",
        'global_stats': f"{KEY_PREFIX}:global:stats",
        'hot_requirements': f"{KEY_PREFIX}:hot:requirements",
        'recent_activities': f"{KEY_PREFIX}:activities:recent"
    }
    
    # 默认TTL（秒）
    DEFAULT_TTL = {
        'requirement': 3600,  # 1小时
        'project_requirements': 1800,  # 30分钟
        'requirement_stats': 900,  # 15分钟
        'user_requirements': 1800,  # 30分钟
        'requirement_search': 600,  # 10分钟
        'requirement_dependencies': 3600,  # 1小时
        'requirement_reviews': 1800,  # 30分钟
        'global_stats': 300,  # 5分钟
        'hot_requirements': 300,  # 5分钟
        'recent_activities': 180  # 3分钟
    }
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_client: Optional[Redis] = None
        self.stats = CacheStats()
        self._connection_pool = None
        self._is_connected = False
        
        # 缓存失效策略配置
        self.invalidation_patterns = {
            'requirement_update': [
                'requirement:{id}',
                'project:{project_id}:requirements',
                'project:{project_id}:stats',
                'user:{assignee_id}:requirements',
                'user:{creator_id}:requirements',
                'global:stats'
            ],
            'requirement_create': [
                'project:{project_id}:requirements',
                'project:{project_id}:stats',
                'user:{creator_id}:requirements',
                'global:stats'
            ],
            'requirement_delete': [
                'requirement:{id}',
                'project:{project_id}:requirements',
                'project:{project_id}:stats',
                'user:{assignee_id}:requirements',
                'user:{creator_id}:requirements',
                'global:stats'
            ],
            'requirement_status_change': [
                'requirement:{id}',
                'project:{project_id}:requirements',
                'project:{project_id}:stats',
                'user:{assignee_id}:requirements',
                'global:stats'
            ]
        }
    
    async def connect(self) -> bool:
        """连接Redis服务器"""
        try:
            # 创建连接池
            self._connection_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval
            )
            
            # 创建Redis客户端
            self.redis_client = Redis(connection_pool=self._connection_pool)
            
            # 测试连接
            await self.redis_client.ping()
            self._is_connected = True
            
            logger.info(f"Redis缓存服务连接成功: {self.config.host}:{self.config.port}")
            return True
            
        except Exception as e:
            logger.error(f"Redis缓存服务连接失败: {str(e)}")
            self._is_connected = False
            return False
    
    async def disconnect(self):
        """断开Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            self._is_connected = False
            logger.info("Redis缓存服务连接已断开")
    
    async def is_healthy(self) -> bool:
        """检查Redis连接健康状态"""
        if not self._is_connected or not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            self._is_connected = False
            return False
    
    def _generate_cache_key(self, key_pattern: str, **kwargs) -> str:
        """生成缓存键"""
        return key_pattern.format(**kwargs)
    
    def _serialize_data(self, data: Any) -> str:
        """序列化数据"""
        if isinstance(data, Requirement):
            return json.dumps(data.to_dict(), ensure_ascii=False, default=str)
        elif isinstance(data, (list, dict)):
            return json.dumps(data, ensure_ascii=False, default=str)
        else:
            return json.dumps(data, ensure_ascii=False, default=str)
    
    def _deserialize_data(self, data: str) -> Any:
        """反序列化数据"""
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"数据反序列化失败: {str(e)}")
            return None
    
    def _generate_search_hash(self, search_params: Dict[str, Any]) -> str:
        """生成搜索参数哈希"""
        # 排序参数以确保一致的哈希
        sorted_params = json.dumps(search_params, sort_keys=True, default=str)
        return hashlib.md5(sorted_params.encode()).hexdigest()
    
    async def _record_cache_operation(self, operation: str, hit: bool = False, 
                                    error: bool = False, response_time: float = 0.0):
        """记录缓存操作统计"""
        self.stats.total_requests += 1
        
        if hit:
            self.stats.cache_hits += 1
        else:
            self.stats.cache_misses += 1
        
        if error:
            self.stats.cache_errors += 1
        
        # 更新平均响应时间
        if self.stats.total_requests == 1:
            self.stats.avg_response_time = response_time
        else:
            self.stats.avg_response_time = (
                (self.stats.avg_response_time * (self.stats.total_requests - 1) + response_time) /
                self.stats.total_requests
            )
        
        self.stats.last_updated = datetime.now()
    
    async def get(self, key_pattern: str, ttl_key: str = None, **kwargs) -> Optional[Any]:
        """获取缓存数据"""
        if not await self.is_healthy():
            return None
        
        start_time = datetime.now()
        cache_key = self._generate_cache_key(self.CACHE_KEYS[key_pattern], **kwargs)
        
        try:
            data = await self.redis_client.get(cache_key)
            response_time = (datetime.now() - start_time).total_seconds()
            
            if data:
                await self._record_cache_operation('get', hit=True, response_time=response_time)
                return self._deserialize_data(data)
            else:
                await self._record_cache_operation('get', hit=False, response_time=response_time)
                return None
                
        except RedisError as e:
            response_time = (datetime.now() - start_time).total_seconds()
            await self._record_cache_operation('get', error=True, response_time=response_time)
            logger.error(f"Redis获取数据失败: {str(e)}")
            return None
    
    async def set(self, key_pattern: str, data: Any, ttl_key: str = None, 
                  custom_ttl: int = None, **kwargs) -> bool:
        """设置缓存数据"""
        if not await self.is_healthy():
            return False
        
        start_time = datetime.now()
        cache_key = self._generate_cache_key(self.CACHE_KEYS[key_pattern], **kwargs)
        
        try:
            serialized_data = self._serialize_data(data)
            
            # 确定TTL
            ttl = custom_ttl or self.DEFAULT_TTL.get(ttl_key or key_pattern, 3600)
            
            await self.redis_client.setex(cache_key, ttl, serialized_data)
            
            response_time = (datetime.now() - start_time).total_seconds()
            await self._record_cache_operation('set', response_time=response_time)
            
            return True
            
        except RedisError as e:
            response_time = (datetime.now() - start_time).total_seconds()
            await self._record_cache_operation('set', error=True, response_time=response_time)
            logger.error(f"Redis设置数据失败: {str(e)}")
            return False
    
    async def delete(self, key_pattern: str, **kwargs) -> bool:
        """删除缓存数据"""
        if not await self.is_healthy():
            return False
        
        cache_key = self._generate_cache_key(self.CACHE_KEYS[key_pattern], **kwargs)
        
        try:
            result = await self.redis_client.delete(cache_key)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Redis删除数据失败: {str(e)}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存数据"""
        if not await self.is_healthy():
            return 0
        
        try:
            # 获取匹配的键
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
            
        except RedisError as e:
            logger.error(f"Redis按模式删除数据失败: {str(e)}")
            return 0
    
    async def exists(self, key_pattern: str, **kwargs) -> bool:
        """检查缓存键是否存在"""
        if not await self.is_healthy():
            return False
        
        cache_key = self._generate_cache_key(self.CACHE_KEYS[key_pattern], **kwargs)
        
        try:
            result = await self.redis_client.exists(cache_key)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Redis检查键存在失败: {str(e)}")
            return False
    
    async def expire(self, key_pattern: str, ttl: int, **kwargs) -> bool:
        """设置缓存过期时间"""
        if not await self.is_healthy():
            return False
        
        cache_key = self._generate_cache_key(self.CACHE_KEYS[key_pattern], **kwargs)
        
        try:
            result = await self.redis_client.expire(cache_key, ttl)
            return result
            
        except RedisError as e:
            logger.error(f"Redis设置过期时间失败: {str(e)}")
            return False
    
    # 需求相关缓存方法
    
    async def cache_requirement(self, requirement: Requirement, ttl: int = None) -> bool:
        """缓存单个需求"""
        return await self.set(
            'requirement', 
            requirement, 
            ttl_key='requirement',
            custom_ttl=ttl,
            id=requirement.id
        )
    
    async def get_cached_requirement(self, requirement_id: int) -> Optional[Dict[str, Any]]:
        """获取缓存的需求"""
        return await self.get('requirement', id=requirement_id)
    
    async def cache_project_requirements(self, project_id: int, requirements: List[Dict[str, Any]], 
                                       ttl: int = None) -> bool:
        """缓存项目需求列表"""
        return await self.set(
            'project_requirements',
            requirements,
            ttl_key='project_requirements',
            custom_ttl=ttl,
            project_id=project_id
        )
    
    async def get_cached_project_requirements(self, project_id: int) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的项目需求列表"""
        return await self.get('project_requirements', project_id=project_id)
    
    async def cache_requirement_stats(self, project_id: int, stats: Dict[str, Any], 
                                    ttl: int = None) -> bool:
        """缓存需求统计信息"""
        return await self.set(
            'requirement_stats',
            stats,
            ttl_key='requirement_stats',
            custom_ttl=ttl,
            project_id=project_id
        )
    
    async def get_cached_requirement_stats(self, project_id: int) -> Optional[Dict[str, Any]]:
        """获取缓存的需求统计信息"""
        return await self.get('requirement_stats', project_id=project_id)
    
    async def cache_search_results(self, search_params: Dict[str, Any], 
                                 results: List[Dict[str, Any]], ttl: int = None) -> bool:
        """缓存搜索结果"""
        search_hash = self._generate_search_hash(search_params)
        return await self.set(
            'requirement_search',
            results,
            ttl_key='requirement_search',
            custom_ttl=ttl,
            hash=search_hash
        )
    
    async def get_cached_search_results(self, search_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的搜索结果"""
        search_hash = self._generate_search_hash(search_params)
        return await self.get('requirement_search', hash=search_hash)
    
    async def cache_user_requirements(self, user_id: int, requirements: List[Dict[str, Any]], 
                                    ttl: int = None) -> bool:
        """缓存用户需求列表"""
        return await self.set(
            'user_requirements',
            requirements,
            ttl_key='user_requirements',
            custom_ttl=ttl,
            user_id=user_id
        )
    
    async def get_cached_user_requirements(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的用户需求列表"""
        return await self.get('user_requirements', user_id=user_id)
    
    # 缓存失效方法
    
    async def invalidate_requirement_cache(self, requirement_id: int, requirement_data: Dict[str, Any]):
        """使需求相关缓存失效"""
        invalidation_keys = []
        
        # 根据操作类型确定失效模式
        operation = requirement_data.get('operation', 'requirement_update')
        patterns = self.invalidation_patterns.get(operation, [])
        
        for pattern in patterns:
            # 替换占位符
            key_pattern = pattern.format(
                id=requirement_id,
                project_id=requirement_data.get('project_id'),
                assignee_id=requirement_data.get('assignee_id'),
                creator_id=requirement_data.get('creator_id')
            )
            invalidation_keys.append(f"{self.KEY_PREFIX}:{key_pattern}")
        
        # 批量删除缓存
        deleted_count = 0
        for key in invalidation_keys:
            if '*' in key:
                # 模式匹配删除
                deleted_count += await self.delete_pattern(key)
            else:
                # 精确删除
                if await self.redis_client.delete(key):
                    deleted_count += 1
        
        logger.info(f"需求 {requirement_id} 相关缓存失效，删除 {deleted_count} 个缓存项")
        return deleted_count
    
    async def invalidate_project_cache(self, project_id: int):
        """使项目相关缓存失效"""
        pattern = f"{self.KEY_PREFIX}:project:{project_id}:*"
        deleted_count = await self.delete_pattern(pattern)
        logger.info(f"项目 {project_id} 相关缓存失效，删除 {deleted_count} 个缓存项")
        return deleted_count
    
    async def invalidate_user_cache(self, user_id: int):
        """使用户相关缓存失效"""
        pattern = f"{self.KEY_PREFIX}:user:{user_id}:*"
        deleted_count = await self.delete_pattern(pattern)
        logger.info(f"用户 {user_id} 相关缓存失效，删除 {deleted_count} 个缓存项")
        return deleted_count
    
    async def invalidate_search_cache(self):
        """使搜索缓存失效"""
        pattern = f"{self.KEY_PREFIX}:search:*"
        deleted_count = await self.delete_pattern(pattern)
        logger.info(f"搜索缓存失效，删除 {deleted_count} 个缓存项")
        return deleted_count
    
    # 热点数据管理
    
    async def add_to_hot_requirements(self, requirement_id: int, score: float = 1.0):
        """添加到热点需求"""
        if not await self.is_healthy():
            return False
        
        try:
            key = self.CACHE_KEYS['hot_requirements']
            await self.redis_client.zadd(key, {str(requirement_id): score})
            await self.redis_client.expire(key, self.DEFAULT_TTL['hot_requirements'])
            return True
            
        except RedisError as e:
            logger.error(f"添加热点需求失败: {str(e)}")
            return False
    
    async def get_hot_requirements(self, limit: int = 10) -> List[int]:
        """获取热点需求列表"""
        if not await self.is_healthy():
            return []
        
        try:
            key = self.CACHE_KEYS['hot_requirements']
            # 按分数降序获取
            hot_ids = await self.redis_client.zrevrange(key, 0, limit - 1)
            return [int(req_id) for req_id in hot_ids]
            
        except RedisError as e:
            logger.error(f"获取热点需求失败: {str(e)}")
            return []
    
    async def increment_requirement_access(self, requirement_id: int):
        """增加需求访问计数"""
        await self.add_to_hot_requirements(requirement_id, 1.0)
    
    # 分布式锁
    
    async def acquire_lock(self, lock_key: str, timeout: int = 10, 
                          blocking_timeout: int = 5) -> Optional[str]:
        """获取分布式锁"""
        if not await self.is_healthy():
            return None
        
        try:
            lock_name = f"{self.KEY_PREFIX}:lock:{lock_key}"
            lock_value = f"{datetime.now().timestamp()}"
            
            # 尝试获取锁
            result = await self.redis_client.set(
                lock_name, lock_value, nx=True, ex=timeout
            )
            
            if result:
                return lock_value
            
            # 如果设置了阻塞超时，等待锁释放
            if blocking_timeout > 0:
                end_time = datetime.now() + timedelta(seconds=blocking_timeout)
                while datetime.now() < end_time:
                    await asyncio.sleep(0.1)
                    result = await self.redis_client.set(
                        lock_name, lock_value, nx=True, ex=timeout
                    )
                    if result:
                        return lock_value
            
            return None
            
        except RedisError as e:
            logger.error(f"获取分布式锁失败: {str(e)}")
            return None
    
    async def release_lock(self, lock_key: str, lock_value: str) -> bool:
        """释放分布式锁"""
        if not await self.is_healthy():
            return False
        
        try:
            lock_name = f"{self.KEY_PREFIX}:lock:{lock_key}"
            
            # Lua脚本确保原子性
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis_client.eval(lua_script, 1, lock_name, lock_value)
            return result == 1
            
        except RedisError as e:
            logger.error(f"释放分布式锁失败: {str(e)}")
            return False
    
    # 缓存统计和监控
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        if not await self.is_healthy():
            return {'status': 'disconnected'}
        
        try:
            info = await self.redis_client.info()
            memory_info = await self.redis_client.info('memory')
            
            return {
                'status': 'connected',
                'redis_version': info.get('redis_version'),
                'connected_clients': info.get('connected_clients'),
                'used_memory': memory_info.get('used_memory_human'),
                'used_memory_peak': memory_info.get('used_memory_peak_human'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'stats': asdict(self.stats)
            }
            
        except RedisError as e:
            logger.error(f"获取缓存信息失败: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    async def get_cache_keys_count(self) -> Dict[str, int]:
        """获取各类缓存键的数量"""
        if not await self.is_healthy():
            return {}
        
        try:
            counts = {}
            for key_type in self.CACHE_KEYS.keys():
                pattern = f"{self.KEY_PREFIX}:{key_type}:*"
                keys = await self.redis_client.keys(pattern)
                counts[key_type] = len(keys)
            
            return counts
            
        except RedisError as e:
            logger.error(f"获取缓存键数量失败: {str(e)}")
            return {}
    
    async def clear_all_cache(self) -> bool:
        """清空所有缓存"""
        if not await self.is_healthy():
            return False
        
        try:
            pattern = f"{self.KEY_PREFIX}:*"
            deleted_count = await self.delete_pattern(pattern)
            logger.info(f"清空所有缓存，删除 {deleted_count} 个缓存项")
            return True
            
        except RedisError as e:
            logger.error(f"清空缓存失败: {str(e)}")
            return False
    
    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        return self.stats
    
    def reset_stats(self):
        """重置缓存统计信息"""
        self.stats = CacheStats()


def cache_result(key_pattern: str, ttl_key: str = None, ttl: int = None, 
                 invalidate_on_error: bool = True):
    """缓存结果装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取缓存实例（假设第一个参数是包含cache属性的对象）
            if args and hasattr(args[0], 'cache') and isinstance(args[0].cache, RequirementRedisCache):
                cache = args[0].cache
                
                # 生成缓存键参数
                cache_kwargs = {}
                if 'requirement_id' in kwargs:
                    cache_kwargs['id'] = kwargs['requirement_id']
                if 'project_id' in kwargs:
                    cache_kwargs['project_id'] = kwargs['project_id']
                if 'user_id' in kwargs:
                    cache_kwargs['user_id'] = kwargs['user_id']
                
                # 尝试从缓存获取
                cached_result = await cache.get(key_pattern, ttl_key, **cache_kwargs)
                if cached_result is not None:
                    return cached_result
                
                # 执行原函数
                try:
                    result = await func(*args, **kwargs)
                    
                    # 缓存结果
                    if result is not None:
                        await cache.set(key_pattern, result, ttl_key, ttl, **cache_kwargs)
                    
                    return result
                    
                except Exception as e:
                    if invalidate_on_error:
                        # 发生错误时使相关缓存失效
                        await cache.delete(key_pattern, **cache_kwargs)
                    raise e
            else:
                # 没有缓存实例，直接执行原函数
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator