"""
上下文缓存服务

负责管理对话上下文的缓存，提高上下文构建性能：
1. Redis缓存管理
2. 上下文预加载
3. 缓存失效策略
4. 压缩上下文缓存
"""

import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict

import redis
from ..core.config import get_settings
from .context_manager import ContextWindow, ContextMessage, CompressionStrategy

logger = logging.getLogger(__name__)
settings = get_settings()


class ContextCache:
    """上下文缓存服务"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        初始化上下文缓存
        
        Args:
            redis_client: Redis客户端实例，如果为None则创建新实例
        """
        if redis_client:
            self.redis = redis_client
        else:
            # 从配置创建Redis客户端
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            self.redis = redis.from_url(redis_url, decode_responses=False)
        
        self.logger = logging.getLogger(__name__)
        
        # 缓存配置
        self.cache_prefix = "ai_context:"
        self.default_ttl = 3600  # 1小时
        self.compressed_ttl = 7200  # 2小时
        self.summary_ttl = 86400  # 24小时
    
    def get_context_cache_key(self, conversation_id: int, ai_model: str = None) -> str:
        """生成上下文缓存键"""
        if ai_model:
            return f"{self.cache_prefix}conv:{conversation_id}:model:{ai_model}"
        else:
            return f"{self.cache_prefix}conv:{conversation_id}"
    
    def get_summary_cache_key(self, conversation_id: int) -> str:
        """生成摘要缓存键"""
        return f"{self.cache_prefix}summary:{conversation_id}"
    
    def get_stats_cache_key(self, conversation_id: int) -> str:
        """生成统计缓存键"""
        return f"{self.cache_prefix}stats:{conversation_id}"
    
    def cache_context_window(self, conversation_id: int, context_window: ContextWindow,
                           ai_model: str = None, ttl: int = None) -> bool:
        """
        缓存上下文窗口
        
        Args:
            conversation_id: 对话ID
            context_window: 上下文窗口对象
            ai_model: AI模型名称
            ttl: 缓存过期时间（秒）
            
        Returns:
            bool: 是否缓存成功
        """
        try:
            cache_key = self.get_context_cache_key(conversation_id, ai_model)
            
            # 序列化上下文窗口
            cache_data = self._serialize_context_window(context_window)
            
            # 设置缓存
            cache_ttl = ttl or self.default_ttl
            success = self.redis.setex(cache_key, cache_ttl, cache_data)
            
            if success:
                self.logger.debug(f"Cached context for conversation {conversation_id}, model: {ai_model}")
                
                # 同时缓存元数据
                metadata_key = f"{cache_key}:meta"
                metadata = {
                    "conversation_id": conversation_id,
                    "ai_model": ai_model,
                    "message_count": len(context_window.messages),
                    "total_tokens": context_window.total_tokens,
                    "compression_strategy": context_window.compression_strategy.value,
                    "cached_at": datetime.utcnow().isoformat(),
                    "has_summary": bool(context_window.summary)
                }
                self.redis.setex(metadata_key, cache_ttl, json.dumps(metadata))
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error caching context window: {str(e)}")
            return False
    
    def get_cached_context_window(self, conversation_id: int, 
                                ai_model: str = None) -> Optional[ContextWindow]:
        """
        获取缓存的上下文窗口
        
        Args:
            conversation_id: 对话ID
            ai_model: AI模型名称
            
        Returns:
            Optional[ContextWindow]: 缓存的上下文窗口，如果不存在则返回None
        """
        try:
            cache_key = self.get_context_cache_key(conversation_id, ai_model)
            
            # 获取缓存数据
            cached_data = self.redis.get(cache_key)
            if not cached_data:
                return None
            
            # 反序列化上下文窗口
            context_window = self._deserialize_context_window(cached_data)
            
            if context_window:
                self.logger.debug(f"Retrieved cached context for conversation {conversation_id}, model: {ai_model}")
            
            return context_window
            
        except Exception as e:
            self.logger.error(f"Error getting cached context window: {str(e)}")
            return None
    
    def cache_context_summary(self, conversation_id: int, summary: str, 
                            ttl: int = None) -> bool:
        """
        缓存对话摘要
        
        Args:
            conversation_id: 对话ID
            summary: 对话摘要
            ttl: 缓存过期时间（秒）
            
        Returns:
            bool: 是否缓存成功
        """
        try:
            cache_key = self.get_summary_cache_key(conversation_id)
            
            summary_data = {
                "summary": summary,
                "conversation_id": conversation_id,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            cache_ttl = ttl or self.summary_ttl
            success = self.redis.setex(cache_key, cache_ttl, json.dumps(summary_data))
            
            if success:
                self.logger.debug(f"Cached summary for conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error caching context summary: {str(e)}")
            return False
    
    def get_cached_summary(self, conversation_id: int) -> Optional[str]:
        """
        获取缓存的对话摘要
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Optional[str]: 缓存的摘要，如果不存在则返回None
        """
        try:
            cache_key = self.get_summary_cache_key(conversation_id)
            
            cached_data = self.redis.get(cache_key)
            if not cached_data:
                return None
            
            summary_data = json.loads(cached_data)
            return summary_data.get("summary")
            
        except Exception as e:
            self.logger.error(f"Error getting cached summary: {str(e)}")
            return None
    
    def cache_context_stats(self, conversation_id: int, stats: Dict[str, Any],
                          ttl: int = None) -> bool:
        """
        缓存上下文统计信息
        
        Args:
            conversation_id: 对话ID
            stats: 统计信息
            ttl: 缓存过期时间（秒）
            
        Returns:
            bool: 是否缓存成功
        """
        try:
            cache_key = self.get_stats_cache_key(conversation_id)
            
            stats_data = {
                "stats": stats,
                "conversation_id": conversation_id,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            cache_ttl = ttl or self.default_ttl
            success = self.redis.setex(cache_key, cache_ttl, json.dumps(stats_data))
            
            if success:
                self.logger.debug(f"Cached stats for conversation {conversation_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error caching context stats: {str(e)}")
            return False
    
    def get_cached_stats(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        获取缓存的上下文统计信息
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Optional[Dict[str, Any]]: 缓存的统计信息，如果不存在则返回None
        """
        try:
            cache_key = self.get_stats_cache_key(conversation_id)
            
            cached_data = self.redis.get(cache_key)
            if not cached_data:
                return None
            
            stats_data = json.loads(cached_data)
            return stats_data.get("stats")
            
        except Exception as e:
            self.logger.error(f"Error getting cached stats: {str(e)}")
            return None
    
    def invalidate_conversation_cache(self, conversation_id: int) -> bool:
        """
        使对话相关的所有缓存失效
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取所有相关的缓存键
            pattern = f"{self.cache_prefix}*{conversation_id}*"
            keys = self.redis.keys(pattern)
            
            if keys:
                deleted_count = self.redis.delete(*keys)
                self.logger.debug(f"Invalidated {deleted_count} cache entries for conversation {conversation_id}")
                return deleted_count > 0
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error invalidating conversation cache: {str(e)}")
            return False
    
    def preload_context(self, conversation_id: int, ai_models: List[str] = None) -> bool:
        """
        预加载对话上下文到缓存
        
        Args:
            conversation_id: 对话ID
            ai_models: 要预加载的AI模型列表
            
        Returns:
            bool: 是否成功
        """
        try:
            # 这里应该调用ContextManager来构建上下文并缓存
            # 暂时只记录日志
            self.logger.info(f"Preloading context for conversation {conversation_id}")
            
            # TODO: 实现预加载逻辑
            # 1. 调用ContextManager.get_conversation_context()
            # 2. 为每个AI模型构建上下文
            # 3. 缓存结果
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error preloading context: {str(e)}")
            return False
    
    def get_cache_info(self, conversation_id: int) -> Dict[str, Any]:
        """
        获取对话的缓存信息
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Dict[str, Any]: 缓存信息
        """
        try:
            cache_info = {
                "conversation_id": conversation_id,
                "cached_contexts": [],
                "has_summary": False,
                "has_stats": False,
                "cache_keys": []
            }
            
            # 查找所有相关的缓存键
            pattern = f"{self.cache_prefix}*{conversation_id}*"
            keys = self.redis.keys(pattern)
            
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                cache_info["cache_keys"].append(key_str)
                
                # 检查缓存类型
                if ":meta" in key_str:
                    # 获取元数据
                    metadata_raw = self.redis.get(key)
                    if metadata_raw:
                        try:
                            metadata = json.loads(metadata_raw)
                            cache_info["cached_contexts"].append(metadata)
                        except json.JSONDecodeError:
                            pass
                elif "summary:" in key_str:
                    cache_info["has_summary"] = True
                elif "stats:" in key_str:
                    cache_info["has_stats"] = True
            
            return cache_info
            
        except Exception as e:
            self.logger.error(f"Error getting cache info: {str(e)}")
            return {"conversation_id": conversation_id, "error": str(e)}
    
    def cleanup_expired_cache(self) -> int:
        """
        清理过期的缓存条目
        
        Returns:
            int: 清理的条目数量
        """
        try:
            # Redis会自动清理过期的键，这里主要是统计和日志
            pattern = f"{self.cache_prefix}*"
            keys = self.redis.keys(pattern)
            
            active_keys = 0
            for key in keys:
                ttl = self.redis.ttl(key)
                if ttl > 0:  # 键存在且未过期
                    active_keys += 1
            
            self.logger.info(f"Context cache cleanup: {active_keys} active keys found")
            return len(keys) - active_keys
            
        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {str(e)}")
            return 0
    
    def _serialize_context_window(self, context_window: ContextWindow) -> bytes:
        """序列化上下文窗口"""
        try:
            # 将ContextWindow转换为可序列化的字典
            data = {
                "messages": [self._serialize_context_message(msg) for msg in context_window.messages],
                "total_tokens": context_window.total_tokens,
                "max_tokens": context_window.max_tokens,
                "compression_strategy": context_window.compression_strategy.value,
                "summary": context_window.summary,
                "compressed_content": context_window.compressed_content
            }
            
            # 使用pickle序列化
            return pickle.dumps(data)
            
        except Exception as e:
            self.logger.error(f"Error serializing context window: {str(e)}")
            raise
    
    def _deserialize_context_window(self, data: bytes) -> Optional[ContextWindow]:
        """反序列化上下文窗口"""
        try:
            # 使用pickle反序列化
            raw_data = pickle.loads(data)
            
            # 重建ContextMessage对象
            messages = [self._deserialize_context_message(msg_data) for msg_data in raw_data["messages"]]
            
            # 重建ContextWindow对象
            context_window = ContextWindow(
                messages=messages,
                total_tokens=raw_data["total_tokens"],
                max_tokens=raw_data["max_tokens"],
                compression_strategy=CompressionStrategy(raw_data["compression_strategy"]),
                summary=raw_data.get("summary"),
                compressed_content=raw_data.get("compressed_content")
            )
            
            return context_window
            
        except Exception as e:
            self.logger.error(f"Error deserializing context window: {str(e)}")
            return None
    
    def _serialize_context_message(self, message: ContextMessage) -> Dict[str, Any]:
        """序列化上下文消息"""
        return {
            "id": message.id,
            "role": message.role.value,
            "content": message.content,
            "content_type": message.content_type.value,
            "timestamp": message.timestamp.isoformat(),
            "tokens": message.tokens,
            "priority": message.priority.value,
            "is_bookmarked": message.is_bookmarked,
            "metadata": message.metadata
        }
    
    def _deserialize_context_message(self, data: Dict[str, Any]) -> ContextMessage:
        """反序列化上下文消息"""
        from ..models.ai_chat_message import MessageRole, ContentType
        from .context_manager import ContextPriority
        
        return ContextMessage(
            id=data["id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            content_type=ContentType(data["content_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tokens=data["tokens"],
            priority=ContextPriority(data["priority"]),
            is_bookmarked=data["is_bookmarked"],
            metadata=data["metadata"]
        )
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            pattern = f"{self.cache_prefix}*"
            keys = self.redis.keys(pattern)
            
            stats = {
                "total_keys": len(keys),
                "context_keys": 0,
                "summary_keys": 0,
                "stats_keys": 0,
                "meta_keys": 0,
                "memory_usage": 0
            }
            
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                
                if ":meta" in key_str:
                    stats["meta_keys"] += 1
                elif "summary:" in key_str:
                    stats["summary_keys"] += 1
                elif "stats:" in key_str:
                    stats["stats_keys"] += 1
                elif "conv:" in key_str:
                    stats["context_keys"] += 1
                
                # 获取键的内存使用量
                try:
                    memory = self.redis.memory_usage(key)
                    if memory:
                        stats["memory_usage"] += memory
                except:
                    pass  # 某些Redis版本可能不支持MEMORY USAGE命令
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting cache statistics: {str(e)}")
            return {"error": str(e)}