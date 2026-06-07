"""
AI对话上下文缓存服务

专门处理AI对话上下文的缓存策略，包括：
1. 对话历史缓存 - 快速恢复对话状态
2. 上下文压缩缓存 - 智能压缩长对话
3. 用户会话状态缓存 - 实时同步会话状态
4. 上下文摘要缓存 - 缓存对话摘要
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .ai_cache_service import ai_cache_service, CacheKeyType, cache_result
from ..models.ai_chat_session import AIChatSession
from ..models.ai_chat_message import AIChatMessage

logger = logging.getLogger(__name__)


@dataclass
class ConversationContextCache:
    """对话上下文缓存对象"""
    conversation_id: int
    messages: List[Dict[str, Any]]  # 序列化的消息列表
    summary: Optional[str] = None
    token_count: int = 0
    last_updated: str = None
    compression_applied: bool = False
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat()


class AIContextCacheService:
    """AI上下文缓存服务"""
    
    def __init__(self):
        self.cache = ai_cache_service
        self.max_context_length = 8000  # 最大上下文长度
        self.compression_threshold = 6000  # 压缩阈值
    
    async def get_conversation_context(self, conversation_id: int, 
                                     user_id: int) -> Optional[ConversationContextCache]:
        """
        获取对话上下文缓存
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            
        Returns:
            Optional[ConversationContextCache]: 缓存的对话上下文
        """
        try:
            cached_data = await self.cache.get(
                CacheKeyType.CONVERSATION_CONTEXT,
                conversation_id,
                user_id
            )
            
            if cached_data:
                logger.debug(f"Retrieved conversation context from cache: {conversation_id}")
                return ConversationContextCache(**cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting conversation context cache: {str(e)}")
            return None
    
    async def set_conversation_context(self, context: ConversationContextCache,
                                     user_id: int, ttl: Optional[int] = None) -> bool:
        """
        设置对话上下文缓存
        
        Args:
            context: 对话上下文对象
            user_id: 用户ID
            ttl: 自定义TTL
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 更新时间戳
            context.last_updated = datetime.utcnow().isoformat()
            
            # 转换为字典
            context_dict = {
                "conversation_id": context.conversation_id,
                "messages": context.messages,
                "summary": context.summary,
                "token_count": context.token_count,
                "last_updated": context.last_updated,
                "compression_applied": context.compression_applied
            }
            
            success = await self.cache.set(
                CacheKeyType.CONVERSATION_CONTEXT,
                context_dict,
                context.conversation_id,
                user_id,
                ttl=ttl
            )
            
            if success:
                logger.debug(f"Cached conversation context: {context.conversation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting conversation context cache: {str(e)}")
            return False
    
    async def update_conversation_context(self, conversation_id: int, user_id: int,
                                        new_message: Dict[str, Any]) -> bool:
        """
        更新对话上下文缓存（添加新消息）
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            new_message: 新消息
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 获取现有上下文
            context = await self.get_conversation_context(conversation_id, user_id)
            
            if context is None:
                # 创建新的上下文
                context = ConversationContextCache(
                    conversation_id=conversation_id,
                    messages=[new_message],
                    token_count=new_message.get('tokens_used', 0)
                )
            else:
                # 添加新消息
                context.messages.append(new_message)
                context.token_count += new_message.get('tokens_used', 0)
                
                # 检查是否需要压缩
                if context.token_count > self.compression_threshold:
                    context = await self._compress_context(context)
            
            # 更新缓存
            return await self.set_conversation_context(context, user_id)
            
        except Exception as e:
            logger.error(f"Error updating conversation context: {str(e)}")
            return False
    
    async def get_context_for_ai(self, conversation_id: int, user_id: int,
                               max_tokens: int = 4000) -> str:
        """
        获取适合AI模型的上下文字符串
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            max_tokens: 最大token数
            
        Returns:
            str: 格式化的上下文字符串
        """
        try:
            context = await self.get_conversation_context(conversation_id, user_id)
            
            if not context:
                return ""
            
            context_parts = []
            
            # 添加摘要（如果有）
            if context.summary:
                context_parts.append(f"对话摘要: {context.summary}")
            
            # 添加消息历史（从最新开始，控制token数量）
            current_tokens = 0
            messages_to_include = []
            
            for message in reversed(context.messages):
                message_tokens = message.get('tokens_used', len(message.get('content', '')) // 4)
                if current_tokens + message_tokens > max_tokens:
                    break
                
                messages_to_include.insert(0, message)
                current_tokens += message_tokens
            
            # 格式化消息
            for message in messages_to_include:
                role = message.get('role', 'USER')
                content = message.get('content', '')
                role_prefix = {"USER": "用户", "ASSISTANT": "助手", "SYSTEM": "系统"}.get(role, role)
                context_parts.append(f"{role_prefix}: {content}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting context for AI: {str(e)}")
            return ""
    
    async def _compress_context(self, context: ConversationContextCache) -> ConversationContextCache:
        """
        压缩对话上下文
        
        Args:
            context: 原始上下文
            
        Returns:
            ConversationContextCache: 压缩后的上下文
        """
        try:
            # 创建新的上下文对象，避免修改原始对象
            import copy
            compressed_context = copy.deepcopy(context)
            
            if compressed_context.compression_applied:
                # 已经压缩过，只保留最近的消息
                recent_messages = compressed_context.messages[-10:]  # 保留最近10条消息
                compressed_context.messages = recent_messages
                compressed_context.token_count = sum(msg.get('tokens_used', 0) for msg in recent_messages)
                return compressed_context
            
            # 生成对话摘要
            summary = await self._generate_conversation_summary(compressed_context.messages)
            
            # 保留重要消息和最近消息
            important_messages = [
                msg for msg in compressed_context.messages 
                if msg.get('is_bookmarked') or (msg.get('user_rating', 0) >= 4)
            ]
            recent_messages = compressed_context.messages[-5:]  # 最近5条消息
            
            # 合并去重
            compressed_messages = []
            seen_ids = set()
            
            for msg in important_messages + recent_messages:
                msg_id = msg.get('id')
                if msg_id and msg_id not in seen_ids:
                    compressed_messages.append(msg)
                    seen_ids.add(msg_id)
                elif not msg_id:  # 没有ID的消息直接添加
                    compressed_messages.append(msg)
            
            # 如果没有重要消息，确保至少保留最近的消息
            if not compressed_messages:
                compressed_messages = recent_messages
            
            # 如果压缩后消息数量没有减少，强制保留最近的一半消息
            if len(compressed_messages) >= len(compressed_context.messages):
                max_messages = max(5, len(compressed_context.messages) // 2)
                compressed_messages = compressed_context.messages[-max_messages:]
            
            # 按时间排序
            compressed_messages.sort(key=lambda x: x.get('created_at', ''))
            
            # 更新压缩后的上下文
            compressed_context.messages = compressed_messages
            compressed_context.summary = summary
            compressed_context.token_count = sum(msg.get('tokens_used', 0) for msg in compressed_messages)
            compressed_context.compression_applied = True
            
            logger.info(f"Compressed context for conversation {compressed_context.conversation_id}: "
                       f"from {len(context.messages)} to {len(compressed_context.messages)} messages, "
                       f"{compressed_context.token_count} tokens")
            
            return compressed_context
            
        except Exception as e:
            logger.error(f"Error compressing context: {str(e)}")
            return context
    
    async def _generate_conversation_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        生成对话摘要
        
        Args:
            messages: 消息列表
            
        Returns:
            str: 对话摘要
        """
        try:
            if not messages:
                return ""
            
            # 简单的摘要生成（实际应该调用AI服务）
            total_messages = len(messages)
            user_messages = len([msg for msg in messages if msg.get('role') == 'USER'])
            assistant_messages = len([msg for msg in messages if msg.get('role') == 'ASSISTANT'])
            
            # 提取关键词
            all_content = " ".join([msg.get('content', '') for msg in messages])
            keywords = self._extract_keywords(all_content)
            
            summary = f"对话包含{total_messages}条消息（用户{user_messages}条，助手{assistant_messages}条）。"
            if keywords:
                summary += f" 主要话题：{', '.join(keywords[:5])}"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {str(e)}")
            return "对话摘要生成失败"
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        提取关键词（简单实现）
        
        Args:
            text: 文本内容
            max_keywords: 最大关键词数
            
        Returns:
            List[str]: 关键词列表
        """
        try:
            # 简单的关键词提取
            import re
            from collections import Counter
            
            # 清理文本
            text = re.sub(r'[^\w\s]', ' ', text.lower())
            words = text.split()
            
            # 过滤停用词
            stop_words = {'的', '了', '在', '是', '我', '你', '他', '她', '它', '们', 
                         '这', '那', '有', '和', '与', '或', '但', '如果', '因为', '所以'}
            
            filtered_words = [word for word in words if len(word) > 1 and word not in stop_words]
            
            # 统计词频
            word_counts = Counter(filtered_words)
            
            # 返回最常见的词
            return [word for word, count in word_counts.most_common(max_keywords)]
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []
    
    async def clear_conversation_context(self, conversation_id: int, user_id: int) -> bool:
        """
        清除对话上下文缓存
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            
        Returns:
            bool: 是否清除成功
        """
        try:
            success = await self.cache.delete(
                CacheKeyType.CONVERSATION_CONTEXT,
                conversation_id,
                user_id
            )
            
            if success:
                logger.debug(f"Cleared conversation context cache: {conversation_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error clearing conversation context: {str(e)}")
            return False
    
    async def get_user_active_conversations(self, user_id: int) -> List[int]:
        """
        获取用户活跃对话列表（从缓存）
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[int]: 活跃对话ID列表
        """
        try:
            cached_data = await self.cache.get(
                CacheKeyType.SESSION_STATE,
                "active_conversations",
                user_id
            )
            
            return cached_data or []
            
        except Exception as e:
            logger.error(f"Error getting active conversations: {str(e)}")
            return []
    
    async def set_user_active_conversations(self, user_id: int, 
                                          conversation_ids: List[int]) -> bool:
        """
        设置用户活跃对话列表
        
        Args:
            user_id: 用户ID
            conversation_ids: 对话ID列表
            
        Returns:
            bool: 是否设置成功
        """
        try:
            success = await self.cache.set(
                CacheKeyType.SESSION_STATE,
                conversation_ids,
                "active_conversations",
                user_id,
                ttl=1800  # 30分钟
            )
            
            if success:
                logger.debug(f"Cached active conversations for user {user_id}: {len(conversation_ids)}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting active conversations: {str(e)}")
            return False
    
    async def get_context_statistics(self) -> Dict[str, Any]:
        """获取上下文缓存统计信息"""
        try:
            metrics = self.cache.get_metrics(CacheKeyType.CONVERSATION_CONTEXT)
            
            stats = {
                "context_cache_metrics": metrics,
                "compression_threshold": self.compression_threshold,
                "max_context_length": self.max_context_length,
                "cache_config": self.cache.cache_configs[CacheKeyType.CONVERSATION_CONTEXT]
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting context statistics: {str(e)}")
            return {}


# 创建全局上下文缓存服务实例
ai_context_cache = AIContextCacheService()