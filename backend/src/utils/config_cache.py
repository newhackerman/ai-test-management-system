"""
配置缓存服务
"""
import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from enum import Enum
import redis
import asyncio
import logging
from ..core.redis import redis_service
from ..models.config import Environment, ConfigType

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "L1_MEMORY"     # 应用内存缓存
    L2_REDIS = "L2_REDIS"       # Redis缓存
    DATABASE = "DATABASE"        # 数据库


class NotificationType(Enum):
    """通知类型"""
    CONFIG_CREATED = "CONFIG_CREATED"
    CONFIG_UPDATED = "CONFIG_UPDATED"
    CONFIG_DELETED = "CONFIG_DELETED"
    CONFIG_ENABLED = "CONFIG_ENABLED"
    CONFIG_DISABLED = "CONFIG_DISABLED"
    CACHE_CLEAR = "CACHE_CLEAR"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"


class ConfigCacheService:
    """配置缓存服务"""
    
    # 缓存键前缀
    CACHE_PREFIXES = {
        'config': 'config',
        'config_group': 'config_group',
        'config_list': 'config_list',
        'permission': 'permission',
        'session': 'session',
        'stats': 'stats',
        'notification': 'notification'
    }
    
    # 缓存过期时间（秒）
    CACHE_TTL = {
        'config': 3600,          # 配置项1小时
        'config_group': 7200,    # 配置分组2小时
        'config_list': 1800,     # 配置列表30分钟
        'permission': 1800,      # 权限30分钟
        'session': 7200,         # 会话2小时
        'stats': 300,            # 统计5分钟
        'notification': 86400    # 通知24小时
    }
    
    # 发布订阅频道
    PUBSUB_CHANNELS = {
        'config_change': 'config:change',
        'config_change_env': 'config:change:{}',  # 环境特定
        'config_change_global': 'config:change:global',
        'audit_status_change': 'audit:status:change',
        'audit_new_request': 'audit:new:request',
        'system_cache_clear': 'system:cache:clear',
        'system_maintenance': 'system:maintenance:mode'
    }
    
    def __init__(self):
        self.redis = redis_service
        self._l1_cache: Dict[str, Tuple[Any, float]] = {}  # 内存缓存 (值, 过期时间)
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'evictions': 0
        }
        self._subscribers: Dict[str, List[Callable]] = {}
        self._max_l1_size = 1000  # L1缓存最大条目数
    
    def _make_cache_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    def _hash_key(self, data: str) -> str:
        """生成数据哈希"""
        return hashlib.md5(data.encode()).hexdigest()[:8]
    
    def _is_l1_expired(self, expire_time: float) -> bool:
        """检查L1缓存是否过期"""
        return time.time() > expire_time
    
    def _evict_l1_cache(self):
        """清理L1缓存"""
        if len(self._l1_cache) <= self._max_l1_size:
            return
        
        # 删除过期的条目
        current_time = time.time()
        expired_keys = [
            key for key, (_, expire_time) in self._l1_cache.items()
            if current_time > expire_time
        ]
        
        for key in expired_keys:
            del self._l1_cache[key]
            self._cache_stats['evictions'] += 1
        
        # 如果还是太多，删除最旧的条目
        if len(self._l1_cache) > self._max_l1_size:
            sorted_items = sorted(
                self._l1_cache.items(),
                key=lambda x: x[1][1]  # 按过期时间排序
            )
            
            to_remove = len(self._l1_cache) - self._max_l1_size + 100
            for key, _ in sorted_items[:to_remove]:
                del self._l1_cache[key]
                self._cache_stats['evictions'] += 1
    
    # === 配置缓存操作 ===
    
    def get_config(self, config_key: str, environment: Environment = Environment.PROD) -> Optional[Any]:
        """
        获取配置值（多级缓存）
        
        Args:
            config_key: 配置键
            environment: 环境
            
        Returns:
            配置值
        """
        cache_key = self._make_cache_key(
            self.CACHE_PREFIXES['config'], 
            environment.value, 
            config_key
        )
        
        # L1缓存查询
        if cache_key in self._l1_cache:
            value, expire_time = self._l1_cache[cache_key]
            if not self._is_l1_expired(expire_time):
                self._cache_stats['hits'] += 1
                self._cache_stats['l1_hits'] += 1
                logger.debug(f"L1缓存命中: {cache_key}")
                return value
            else:
                # 过期，删除
                del self._l1_cache[cache_key]
        
        # L2缓存查询
        l2_value = self.redis.get(cache_key)
        if l2_value is not None:
            # 回填L1缓存
            expire_time = time.time() + 60  # L1缓存1分钟
            self._l1_cache[cache_key] = (l2_value, expire_time)
            self._evict_l1_cache()
            
            self._cache_stats['hits'] += 1
            self._cache_stats['l2_hits'] += 1
            logger.debug(f"L2缓存命中: {cache_key}")
            return l2_value
        
        self._cache_stats['misses'] += 1
        logger.debug(f"缓存未命中: {cache_key}")
        return None
    
    def set_config(self, config_key: str, value: Any, environment: Environment = Environment.PROD,
                   ttl: Optional[int] = None) -> bool:
        """
        设置配置值（多级缓存）
        
        Args:
            config_key: 配置键
            value: 配置值
            environment: 环境
            ttl: 过期时间（秒）
            
        Returns:
            是否设置成功
        """
        cache_key = self._make_cache_key(
            self.CACHE_PREFIXES['config'], 
            environment.value, 
            config_key
        )
        
        if ttl is None:
            ttl = self.CACHE_TTL['config']
        
        # 设置L2缓存
        success = self.redis.set(cache_key, value, expire=ttl)
        
        if success:
            # 更新L1缓存
            expire_time = time.time() + min(ttl, 60)  # L1缓存最多1分钟
            self._l1_cache[cache_key] = (value, expire_time)
            self._evict_l1_cache()
            
            logger.debug(f"缓存设置成功: {cache_key}")
        
        return success
    
    def delete_config(self, config_key: str, environment: Environment = Environment.PROD) -> bool:
        """
        删除配置缓存
        
        Args:
            config_key: 配置键
            environment: 环境
            
        Returns:
            是否删除成功
        """
        cache_key = self._make_cache_key(
            self.CACHE_PREFIXES['config'], 
            environment.value, 
            config_key
        )
        
        # 删除L1缓存
        if cache_key in self._l1_cache:
            del self._l1_cache[cache_key]
        
        # 删除L2缓存
        success = self.redis.delete(cache_key)
        logger.debug(f"缓存删除: {cache_key}, 成功: {success}")
        return success
    
    def get_config_list(self, environment: Environment = Environment.PROD, 
                       group_id: Optional[int] = None, 
                       page: int = 1, size: int = 20) -> Optional[Dict]:
        """
        获取配置列表缓存
        
        Args:
            environment: 环境
            group_id: 分组ID
            page: 页码
            size: 页大小
            
        Returns:
            配置列表
        """
        # 生成缓存键的哈希
        key_data = f"{environment.value}:{group_id}:{page}:{size}"
        key_hash = self._hash_key(key_data)
        
        cache_key = self._make_cache_key(
            self.CACHE_PREFIXES['config_list'], 
            environment.value,
            key_hash
        )
        
        return self.redis.get(cache_key)
    
    def set_config_list(self, config_list: Dict, environment: Environment = Environment.PROD,
                       group_id: Optional[int] = None, page: int = 1, size: int = 20) -> bool:
        """
        设置配置列表缓存
        
        Args:
            config_list: 配置列表
            environment: 环境
            group_id: 分组ID
            page: 页码
            size: 页大小
            
        Returns:
            是否设置成功
        """
        key_data = f"{environment.value}:{group_id}:{page}:{size}"
        key_hash = self._hash_key(key_data)
        
        cache_key = self._make_cache_key(
            self.CACHE_PREFIXES['config_list'], 
            environment.value,
            key_hash
        )
        
        return self.redis.set(cache_key, config_list, expire=self.CACHE_TTL['config_list'])
    
    # === 分组缓存操作 ===
    
    def get_config_group(self, group_id: int) -> Optional[Dict]:
        """获取配置分组缓存"""
        cache_key = self._make_cache_key(self.CACHE_PREFIXES['config_group'], group_id)
        return self.redis.get(cache_key)
    
    def set_config_group(self, group_id: int, group_data: Dict) -> bool:
        """设置配置分组缓存"""
        cache_key = self._make_cache_key(self.CACHE_PREFIXES['config_group'], group_id)
        return self.redis.set(cache_key, group_data, expire=self.CACHE_TTL['config_group'])
    
    def delete_config_group(self, group_id: int) -> bool:
        """删除配置分组缓存"""
        cache_key = self._make_cache_key(self.CACHE_PREFIXES['config_group'], group_id)
        return self.redis.delete(cache_key)
    
    # === 环境缓存管理 ===
    
    def clear_environment_cache(self) -> bool:
        """
        清理所有环境相关的缓存
        
        Returns:
            是否清理成功
        """
        try:
            # 清理L1缓存中的环境数据
            env_keys = [key for key in self._l1_cache.keys() if 'env' in key.lower()]
            for key in env_keys:
                del self._l1_cache[key]
            
            # 清理L2缓存中的环境数据
            pattern = f"{self.CACHE_PREFIXES['config']}:*:env:*"
            env_cache_keys = self.redis.keys(pattern)
            
            if env_cache_keys:
                for key in env_cache_keys:
                    self.redis.delete(key)
            
            logger.debug(f"清理环境缓存完成，清理了{len(env_keys)}个L1条目，{len(env_cache_keys)}个L2条目")
            return True
            
        except Exception as e:
            logger.error(f"清理环境缓存失败: {e}")
            return False
    
    def get_config_list(self, environment: Environment, group_id: Optional[int] = None,
                       page: int = 1, size: int = 20) -> Optional[Any]:
        """
        获取配置列表缓存
        
        Args:
            environment: 环境
            group_id: 分组ID
            page: 页码
            size: 页大小
            
        Returns:
            配置列表
        """
        cache_key = self._make_cache_key(
            self.CACHE_PREFIXES['config_list'],
            environment.value,
            group_id or 'all',
            page,
            size
        )
        
        return self.redis.get(cache_key)
    
    def set_config_list(self, config_list: Any, environment: Environment,
                       group_id: Optional[int] = None, page: int = 1, size: int = 20) -> bool:
        """
        设置配置列表缓存
        
        Args:
            config_list: 配置列表
            environment: 环境
            group_id: 分组ID
            page: 页码
            size: 页大小
            
        Returns:
            是否设置成功
        """
        cache_key = self._make_cache_key(
            self.CACHE_PREFIXES['config_list'],
            environment.value,
            group_id or 'all',
            page,
            size
        )
        
        return self.redis.set(cache_key, config_list, expire=self.CACHE_TTL['config_list'])
    
    def publish_environment_sync(self, source_env: Environment, target_env: Environment,
                               sync_result: Dict) -> bool:
        """
        发布环境同步事件
        
        Args:
            source_env: 源环境
            target_env: 目标环境
            sync_result: 同步结果
            
        Returns:
            是否发布成功
        """
        try:
            message = {
                'type': 'ENVIRONMENT_SYNC',
                'source_env': source_env.value,
                'target_env': target_env.value,
                'result': sync_result,
                'timestamp': time.time()
            }
            
            channel = 'env:sync'
            return self.redis.redis_client.publish(channel, json.dumps(message, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"发布环境同步事件失败: {e}")
            return False
    
    # === 权限缓存操作 ===
    
    def get_user_permissions(self, user_id: int, environment: Optional[Environment] = None) -> Optional[Dict]:
        """获取用户权限缓存"""
        env_suffix = f":{environment.value}" if environment else ""
        cache_key = self._make_cache_key(self.CACHE_PREFIXES['permission'], f"user:{user_id}{env_suffix}")
        return self.redis.get(cache_key)
    
    def set_user_permissions(self, user_id: int, permissions: Dict, 
                           environment: Optional[Environment] = None) -> bool:
        """设置用户权限缓存"""
        env_suffix = f":{environment.value}" if environment else ""
        cache_key = self._make_cache_key(self.CACHE_PREFIXES['permission'], f"user:{user_id}{env_suffix}")
        return self.redis.set(cache_key, permissions, expire=self.CACHE_TTL['permission'])
    
    def delete_user_permissions(self, user_id: int) -> bool:
        """删除用户权限缓存"""
        pattern = f"{self.CACHE_PREFIXES['permission']}:user:{user_id}*"
        keys = self.redis.keys(pattern)
        
        success = True
        for key in keys:
            if not self.redis.delete(key):
                success = False
        
        return success
    
    # === 缓存管理操作 ===
    
    def clear_config_cache(self, environment: Optional[Environment] = None, 
                          config_key: Optional[str] = None) -> bool:
        """
        清理配置缓存
        
        Args:
            environment: 指定环境，None表示所有环境
            config_key: 指定配置键，None表示所有配置
            
        Returns:
            是否清理成功
        """
        if config_key and environment:
            # 清理特定配置
            return self.delete_config(config_key, environment)
        
        # 构建匹配模式
        if environment:
            pattern = f"{self.CACHE_PREFIXES['config']}:{environment.value}:*"
        else:
            pattern = f"{self.CACHE_PREFIXES['config']}:*"
        
        if config_key:
            pattern += f":*{config_key}*"
        
        # 获取匹配的键
        keys = self.redis.keys(pattern)
        
        # 删除缓存
        success = True
        for key in keys:
            if not self.redis.delete(key):
                success = False
        
        # 清理L1缓存
        if not config_key and not environment:
            self._l1_cache.clear()
        else:
            # 清理匹配的L1缓存
            to_remove = []
            for cache_key in self._l1_cache:
                if environment and not cache_key.startswith(f"{self.CACHE_PREFIXES['config']}:{environment.value}:"):
                    continue
                if config_key and config_key not in cache_key:
                    continue
                to_remove.append(cache_key)
            
            for key in to_remove:
                del self._l1_cache[key]
        
        logger.info(f"清理缓存: 环境={environment}, 配置键={config_key}, 清理键数={len(keys)}")
        return success
    
    def clear_all_cache(self) -> bool:
        """清理所有配置相关缓存"""
        try:
            # 清理L1缓存
            self._l1_cache.clear()
            
            # 清理L2缓存
            patterns = [
                f"{prefix}:*" for prefix in self.CACHE_PREFIXES.values()
            ]
            
            total_cleared = 0
            for pattern in patterns:
                keys = self.redis.keys(pattern)
                for key in keys:
                    self.redis.delete(key)
                total_cleared += len(keys)
            
            logger.info(f"清理所有缓存完成: 清理键数={total_cleared}")
            return True
            
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return False
    
    def warm_up_cache(self, environment: Environment = Environment.PROD) -> bool:
        """
        缓存预热
        
        Args:
            environment: 环境
            
        Returns:
            是否预热成功
        """
        try:
            # 这里应该从数据库加载常用配置到缓存
            # 具体实现需要在后续的配置服务中完成
            logger.info(f"开始缓存预热: 环境={environment}")
            
            # 预热逻辑将在ConfigService中实现
            return True
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")
            return False
    
    # === 统计信息 ===
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        hit_rate = 0
        if self._cache_stats['hits'] + self._cache_stats['misses'] > 0:
            hit_rate = self._cache_stats['hits'] / (self._cache_stats['hits'] + self._cache_stats['misses'])
        
        return {
            'hit_rate': round(hit_rate * 100, 2),
            'total_requests': self._cache_stats['hits'] + self._cache_stats['misses'],
            'l1_cache_size': len(self._l1_cache),
            'l1_hit_rate': round(self._cache_stats['l1_hits'] / max(1, self._cache_stats['hits']) * 100, 2),
            'l2_hit_rate': round(self._cache_stats['l2_hits'] / max(1, self._cache_stats['hits']) * 100, 2),
            'evictions': self._cache_stats['evictions'],
            **self._cache_stats
        }
    
    def reset_cache_stats(self):
        """重置缓存统计"""
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'evictions': 0
        }
    
    # === 发布订阅机制 ===
    
    def publish_config_change(self, config_key: str, environment: Environment,
                            change_type: NotificationType, data: Optional[Dict] = None) -> bool:
        """
        发布配置变更事件
        
        Args:
            config_key: 配置键
            environment: 环境
            change_type: 变更类型
            data: 附加数据
            
        Returns:
            是否发布成功
        """
        try:
            message = {
                'config_key': config_key,
                'environment': environment.value,
                'change_type': change_type.value,
                'timestamp': time.time(),
                'data': data or {}
            }
            
            # 发布到环境特定频道
            env_channel = self.PUBSUB_CHANNELS['config_change_env'].format(environment.value)
            self.redis.redis_client.publish(env_channel, json.dumps(message, ensure_ascii=False))
            
            # 发布到全局频道
            global_channel = self.PUBSUB_CHANNELS['config_change_global']
            self.redis.redis_client.publish(global_channel, json.dumps(message, ensure_ascii=False))
            
            logger.info(f"配置变更事件发布: {config_key} in {environment.value}")
            return True
            
        except Exception as e:
            logger.error(f"发布配置变更事件失败: {e}")
            return False
    
    def subscribe_config_changes(self, callback: Callable, environment: Optional[Environment] = None):
        """
        订阅配置变更事件
        
        Args:
            callback: 回调函数
            environment: 环境，None表示订阅全局
        """
        if environment:
            channel = self.PUBSUB_CHANNELS['config_change_env'].format(environment.value)
        else:
            channel = self.PUBSUB_CHANNELS['config_change_global']
        
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        
        self._subscribers[channel].append(callback)
        logger.info(f"订阅配置变更: 频道={channel}")
    
    def unsubscribe_config_changes(self, callback: Callable, environment: Optional[Environment] = None):
        """取消订阅配置变更事件"""
        if environment:
            channel = self.PUBSUB_CHANNELS['config_change_env'].format(environment.value)
        else:
            channel = self.PUBSUB_CHANNELS['config_change_global']
        
        if channel in self._subscribers:
            try:
                self._subscribers[channel].remove(callback)
                if not self._subscribers[channel]:
                    del self._subscribers[channel]
                logger.info(f"取消订阅配置变更: 频道={channel}")
            except ValueError:
                pass
    
    def publish_system_event(self, event_type: NotificationType, data: Optional[Dict] = None) -> bool:
        """发布系统事件"""
        try:
            message = {
                'event_type': event_type.value,
                'timestamp': time.time(),
                'data': data or {}
            }
            
            if event_type == NotificationType.CACHE_CLEAR:
                channel = self.PUBSUB_CHANNELS['system_cache_clear']
            elif event_type == NotificationType.MAINTENANCE_MODE:
                channel = self.PUBSUB_CHANNELS['system_maintenance']
            else:
                return False
            
            self.redis.redis_client.publish(channel, json.dumps(message, ensure_ascii=False))
            logger.info(f"系统事件发布: {event_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"发布系统事件失败: {e}")
            return False


# 全局配置缓存服务实例
config_cache_service = ConfigCacheService()


# 便捷函数
def get_cached_config(config_key: str, environment: Environment = Environment.PROD) -> Optional[Any]:
    """获取缓存配置的便捷函数"""
    return config_cache_service.get_config(config_key, environment)


def set_cached_config(config_key: str, value: Any, environment: Environment = Environment.PROD) -> bool:
    """设置缓存配置的便捷函数"""
    return config_cache_service.set_config(config_key, value, environment)


def clear_config_cache(environment: Optional[Environment] = None, config_key: Optional[str] = None) -> bool:
    """清理配置缓存的便捷函数"""
    return config_cache_service.clear_config_cache(environment, config_key)


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计的便捷函数"""
    return config_cache_service.get_cache_stats()
