"""
Redis连接和操作工具
"""
import json
import redis
from typing import Any, Optional, Union
from .config import settings


class RedisService:
    """Redis服务类"""
    
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # 测试连接
            self.redis_client.ping()
        except Exception as e:
            print(f"Redis连接失败: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """检查Redis连接状态"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置键值"""
        if not self.is_connected():
            return False
        
        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)
            
            result = self.redis_client.set(key, value, ex=expire)
            return bool(result)
        except Exception as e:
            print(f"Redis设置失败: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取键值"""
        if not self.is_connected():
            return None
        
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            print(f"Redis获取失败: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """删除键"""
        if not self.is_connected():
            return False
        
        try:
            result = self.redis_client.delete(key)
            return bool(result)
        except Exception as e:
            print(f"Redis删除失败: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.is_connected():
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"Redis检查存在失败: {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """设置键过期时间"""
        if not self.is_connected():
            return False
        
        try:
            result = self.redis_client.expire(key, seconds)
            return bool(result)
        except Exception as e:
            print(f"Redis设置过期时间失败: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """获取键剩余过期时间"""
        if not self.is_connected():
            return -1
        
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            print(f"Redis获取TTL失败: {e}")
            return -1
    
    def keys(self, pattern: str = "*") -> list:
        """获取匹配模式的所有键"""
        if not self.is_connected():
            return []
        
        try:
            return self.redis_client.keys(pattern)
        except Exception as e:
            print(f"Redis获取键列表失败: {e}")
            return []
    
    def flushdb(self) -> bool:
        """清空当前数据库"""
        if not self.is_connected():
            return False
        
        try:
            result = self.redis_client.flushdb()
            return bool(result)
        except Exception as e:
            print(f"Redis清空数据库失败: {e}")
            return False
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增键值"""
        if not self.is_connected():
            return None
        
        try:
            return self.redis_client.incr(key, amount)
        except Exception as e:
            print(f"Redis递增失败: {e}")
            return None
    
    def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """递减键值"""
        if not self.is_connected():
            return None
        
        try:
            return self.redis_client.decr(key, amount)
        except Exception as e:
            print(f"Redis递减失败: {e}")
            return None
    
    def hset(self, name: str, key: str, value: Any) -> bool:
        """设置哈希字段"""
        if not self.is_connected():
            return False
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)
            
            result = self.redis_client.hset(name, key, value)
            return bool(result)
        except Exception as e:
            print(f"Redis哈希设置失败: {e}")
            return False
    
    def hget(self, name: str, key: str) -> Optional[Any]:
        """获取哈希字段"""
        if not self.is_connected():
            return None
        
        try:
            value = self.redis_client.hget(name, key)
            if value is None:
                return None
            
            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            print(f"Redis哈希获取失败: {e}")
            return None
    
    def hdel(self, name: str, key: str) -> bool:
        """删除哈希字段"""
        if not self.is_connected():
            return False
        
        try:
            result = self.redis_client.hdel(name, key)
            return bool(result)
        except Exception as e:
            print(f"Redis哈希删除失败: {e}")
            return False
    
    def hgetall(self, name: str) -> dict:
        """获取所有哈希字段"""
        if not self.is_connected():
            return {}
        
        try:
            result = self.redis_client.hgetall(name)
            # 尝试反序列化JSON值
            for key, value in result.items():
                try:
                    result[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
            return result
        except Exception as e:
            print(f"Redis获取所有哈希字段失败: {e}")
            return {}


# 创建Redis服务实例
redis_service = RedisService()


async def get_redis_client():
    """获取Redis客户端（异步版本）"""
    import redis.asyncio as redis_async
    
    try:
        client = redis_async.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        # 测试连接
        await client.ping()
        return client
    except Exception as e:
        print(f"异步Redis连接失败: {e}")
        return None