"""
对话上下文管理器

负责管理AI对话的上下文，包括：
1. 上下文构建和维护
2. 智能压缩和截断
3. 重要信息提取和保留
4. 跨模型上下文适配
5. 上下文恢复和摘要
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.orm import Session
from ..models.ai_chat_message import AIChatMessage, MessageRole, ContentType
from ..models.ai_chat_session import AIChatSession
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CompressionStrategy(str, Enum):
    """压缩策略枚举"""
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    INTELLIGENT_TRUNCATION = "intelligent_truncation"  # 智能截断
    SUMMARY_COMPRESSION = "summary_compression"  # 摘要压缩
    HIERARCHICAL_STORAGE = "hierarchical_storage"  # 分层存储
    TEMPLATE_COMPRESSION = "template_compression"  # 模板压缩


class ContextPriority(str, Enum):
    """上下文优先级"""
    CRITICAL = "critical"  # 关键信息，必须保留
    HIGH = "high"  # 高优先级
    MEDIUM = "medium"  # 中等优先级
    LOW = "low"  # 低优先级
    TEMPORARY = "temporary"  # 临时信息，可随时删除


@dataclass
class ContextMessage:
    """上下文消息"""
    id: int
    role: MessageRole
    content: str
    content_type: ContentType
    timestamp: datetime
    tokens: int
    priority: ContextPriority
    is_bookmarked: bool
    metadata: Dict[str, Any]


@dataclass
class ContextWindow:
    """上下文窗口"""
    messages: List[ContextMessage]
    total_tokens: int
    max_tokens: int
    compression_strategy: CompressionStrategy
    summary: Optional[str] = None
    compressed_content: Optional[str] = None


@dataclass
class ModelContextLimits:
    """模型上下文限制"""
    model_name: str
    max_tokens: int
    recommended_tokens: int
    compression_strategy: CompressionStrategy
    supports_long_context: bool


class ContextManager:
    """对话上下文管理器"""
    
    # 模型上下文限制配置
    MODEL_LIMITS = {
        "gpt-4": ModelContextLimits(
            model_name="gpt-4",
            max_tokens=8000,
            recommended_tokens=6000,
            compression_strategy=CompressionStrategy.INTELLIGENT_TRUNCATION,
            supports_long_context=False
        ),
        "gpt-4-turbo": ModelContextLimits(
            model_name="gpt-4-turbo",
            max_tokens=128000,
            recommended_tokens=100000,
            compression_strategy=CompressionStrategy.HIERARCHICAL_STORAGE,
            supports_long_context=True
        ),
        "gpt-3.5-turbo": ModelContextLimits(
            model_name="gpt-3.5-turbo",
            max_tokens=4000,
            recommended_tokens=3000,
            compression_strategy=CompressionStrategy.SLIDING_WINDOW,
            supports_long_context=False
        ),
        "claude-3-opus": ModelContextLimits(
            model_name="claude-3-opus",
            max_tokens=200000,
            recommended_tokens=150000,
            compression_strategy=CompressionStrategy.HIERARCHICAL_STORAGE,
            supports_long_context=True
        ),
        "claude-3-sonnet": ModelContextLimits(
            model_name="claude-3-sonnet",
            max_tokens=200000,
            recommended_tokens=150000,
            compression_strategy=CompressionStrategy.HIERARCHICAL_STORAGE,
            supports_long_context=True
        ),
        "claude-3-haiku": ModelContextLimits(
            model_name="claude-3-haiku",
            max_tokens=200000,
            recommended_tokens=150000,
            compression_strategy=CompressionStrategy.HIERARCHICAL_STORAGE,
            supports_long_context=True
        ),
        "gemini-pro": ModelContextLimits(
            model_name="gemini-pro",
            max_tokens=32000,
            recommended_tokens=25000,
            compression_strategy=CompressionStrategy.INTELLIGENT_TRUNCATION,
            supports_long_context=True
        ),
        "wenxin-4": ModelContextLimits(
            model_name="wenxin-4",
            max_tokens=8000,
            recommended_tokens=6000,
            compression_strategy=CompressionStrategy.TEMPLATE_COMPRESSION,
            supports_long_context=False
        ),
        "tongyi-max": ModelContextLimits(
            model_name="tongyi-max",
            max_tokens=8000,
            recommended_tokens=6000,
            compression_strategy=CompressionStrategy.TEMPLATE_COMPRESSION,
            supports_long_context=False
        )
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def get_conversation_context(self, conversation_id: int, 
                               ai_model: str = None,
                               max_messages: int = None,
                               include_system_prompt: bool = True) -> ContextWindow:
        """
        获取对话上下文
        
        Args:
            conversation_id: 对话ID
            ai_model: AI模型名称，用于确定上下文限制
            max_messages: 最大消息数量限制
            include_system_prompt: 是否包含系统提示词
            
        Returns:
            ContextWindow: 构建的上下文窗口
        """
        try:
            self.logger.info(f"Building context for conversation {conversation_id}, model: {ai_model}")
            
            # 获取对话信息
            conversation = self.db.query(AIChatSession).filter(
                AIChatSession.id == conversation_id
            ).first()
            
            if not conversation:
                raise ValueError(f"对话 {conversation_id} 不存在")
            
            # 确定使用的AI模型
            model_name = ai_model or conversation.ai_model or "gpt-3.5-turbo"
            model_limits = self.MODEL_LIMITS.get(model_name, self.MODEL_LIMITS["gpt-3.5-turbo"])
            
            # 获取对话消息
            messages_query = self.db.query(AIChatMessage).filter(
                AIChatMessage.session_id == conversation_id
            ).order_by(AIChatMessage.created_at)
            
            if max_messages:
                # 获取最近的消息
                messages_query = messages_query.limit(max_messages)
            
            raw_messages = messages_query.all()
            
            # 转换为上下文消息
            context_messages = []
            for msg in raw_messages:
                context_msg = self._convert_to_context_message(msg)
                context_messages.append(context_msg)
            
            # 添加系统提示词（如果需要）
            if include_system_prompt and conversation.system_prompt:
                system_msg = ContextMessage(
                    id=0,
                    role=MessageRole.SYSTEM,
                    content=conversation.system_prompt,
                    content_type=ContentType.TEXT,
                    timestamp=conversation.created_at,
                    tokens=self._estimate_tokens(conversation.system_prompt),
                    priority=ContextPriority.CRITICAL,
                    is_bookmarked=False,
                    metadata={"type": "system_prompt"}
                )
                context_messages.insert(0, system_msg)
            
            # 计算总Token数
            total_tokens = sum(msg.tokens for msg in context_messages)
            
            # 构建上下文窗口
            context_window = ContextWindow(
                messages=context_messages,
                total_tokens=total_tokens,
                max_tokens=model_limits.max_tokens,
                compression_strategy=model_limits.compression_strategy
            )
            
            # 如果超出限制，进行压缩
            if total_tokens > model_limits.recommended_tokens:
                context_window = self._compress_context(context_window, model_limits)
            
            self.logger.info(f"Built context with {len(context_window.messages)} messages, "
                           f"{context_window.total_tokens} tokens")
            
            return context_window
            
        except Exception as e:
            self.logger.error(f"Error building context for conversation {conversation_id}: {str(e)}")
            raise
    
    def _convert_to_context_message(self, message: AIChatMessage) -> ContextMessage:
        """将数据库消息转换为上下文消息"""
        # 解析元数据
        metadata = {}
        if message.message_metadata:
            try:
                metadata = json.loads(message.message_metadata)
            except json.JSONDecodeError:
                pass
        
        # 确定优先级
        priority = self._determine_message_priority(message, metadata)
        
        # 估算Token数
        tokens = self._estimate_tokens(message.content)
        
        return ContextMessage(
            id=message.id,
            role=message.role,
            content=message.content,
            content_type=message.content_type,
            timestamp=message.created_at,
            tokens=tokens,
            priority=priority,
            is_bookmarked=message.is_bookmarked,
            metadata=metadata
        )
    
    def _determine_message_priority(self, message: AIChatMessage, 
                                  metadata: Dict[str, Any]) -> ContextPriority:
        """确定消息优先级"""
        # 收藏的消息优先级高
        if message.is_bookmarked:
            return ContextPriority.CRITICAL
        
        # 系统消息优先级高
        if message.role == MessageRole.SYSTEM:
            return ContextPriority.CRITICAL
        
        # 错误消息优先级低
        if message.is_error:
            return ContextPriority.LOW
        
        # 根据用户评分确定优先级
        if message.user_rating:
            if message.user_rating >= 4:
                return ContextPriority.HIGH
            elif message.user_rating <= 2:
                return ContextPriority.LOW
        
        # 根据消息长度和内容类型确定优先级
        if message.content_type == ContentType.CODE:
            return ContextPriority.HIGH
        
        if len(message.content) > 1000:
            return ContextPriority.MEDIUM
        
        # 最近的消息优先级较高
        if message.created_at > datetime.utcnow() - timedelta(hours=1):
            return ContextPriority.HIGH
        elif message.created_at > datetime.utcnow() - timedelta(days=1):
            return ContextPriority.MEDIUM
        
        return ContextPriority.LOW
    
    def _estimate_tokens(self, text: str) -> int:
        """估算文本的Token数量"""
        # 简单的Token估算：英文约4字符/token，中文约1.5字符/token
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        english_chars = len(text) - chinese_chars
        
        estimated_tokens = int(chinese_chars / 1.5 + english_chars / 4)
        return max(1, estimated_tokens)  # 至少1个token
    
    def _compress_context(self, context_window: ContextWindow, 
                         model_limits: ModelContextLimits) -> ContextWindow:
        """压缩上下文"""
        strategy = context_window.compression_strategy
        
        if strategy == CompressionStrategy.SLIDING_WINDOW:
            return self._sliding_window_compression(context_window, model_limits)
        elif strategy == CompressionStrategy.INTELLIGENT_TRUNCATION:
            return self._intelligent_truncation(context_window, model_limits)
        elif strategy == CompressionStrategy.SUMMARY_COMPRESSION:
            return self._summary_compression(context_window, model_limits)
        elif strategy == CompressionStrategy.HIERARCHICAL_STORAGE:
            return self._hierarchical_storage(context_window, model_limits)
        elif strategy == CompressionStrategy.TEMPLATE_COMPRESSION:
            return self._template_compression(context_window, model_limits)
        else:
            # 默认使用滑动窗口
            return self._sliding_window_compression(context_window, model_limits)
    
    def _sliding_window_compression(self, context_window: ContextWindow,
                                  model_limits: ModelContextLimits) -> ContextWindow:
        """滑动窗口压缩策略"""
        target_tokens = model_limits.recommended_tokens
        messages = context_window.messages.copy()
        
        # 保留系统消息和关键消息
        critical_messages = [msg for msg in messages if msg.priority == ContextPriority.CRITICAL]
        other_messages = [msg for msg in messages if msg.priority != ContextPriority.CRITICAL]
        
        # 从最新消息开始保留
        other_messages.reverse()
        
        selected_messages = critical_messages.copy()
        current_tokens = sum(msg.tokens for msg in critical_messages)
        
        for msg in other_messages:
            if current_tokens + msg.tokens <= target_tokens:
                selected_messages.append(msg)
                current_tokens += msg.tokens
            else:
                break
        
        # 按时间排序
        selected_messages.sort(key=lambda x: x.timestamp)
        
        return ContextWindow(
            messages=selected_messages,
            total_tokens=current_tokens,
            max_tokens=model_limits.max_tokens,
            compression_strategy=CompressionStrategy.SLIDING_WINDOW
        )
    
    def _intelligent_truncation(self, context_window: ContextWindow,
                              model_limits: ModelContextLimits) -> ContextWindow:
        """智能截断策略"""
        target_tokens = model_limits.recommended_tokens
        messages = context_window.messages.copy()
        
        # 按优先级分组
        priority_groups = {
            ContextPriority.CRITICAL: [],
            ContextPriority.HIGH: [],
            ContextPriority.MEDIUM: [],
            ContextPriority.LOW: [],
            ContextPriority.TEMPORARY: []
        }
        
        for msg in messages:
            priority_groups[msg.priority].append(msg)
        
        # 按优先级选择消息
        selected_messages = []
        current_tokens = 0
        
        for priority in [ContextPriority.CRITICAL, ContextPriority.HIGH, 
                        ContextPriority.MEDIUM, ContextPriority.LOW, 
                        ContextPriority.TEMPORARY]:
            
            group_messages = priority_groups[priority]
            # 对于非关键消息，优先选择最新的
            if priority != ContextPriority.CRITICAL:
                group_messages.sort(key=lambda x: x.timestamp, reverse=True)
            
            for msg in group_messages:
                if current_tokens + msg.tokens <= target_tokens:
                    selected_messages.append(msg)
                    current_tokens += msg.tokens
                elif priority == ContextPriority.CRITICAL:
                    # 关键消息必须保留，即使超出限制
                    selected_messages.append(msg)
                    current_tokens += msg.tokens
        
        # 按时间排序
        selected_messages.sort(key=lambda x: x.timestamp)
        
        return ContextWindow(
            messages=selected_messages,
            total_tokens=current_tokens,
            max_tokens=model_limits.max_tokens,
            compression_strategy=CompressionStrategy.INTELLIGENT_TRUNCATION
        )
    
    def _summary_compression(self, context_window: ContextWindow,
                           model_limits: ModelContextLimits) -> ContextWindow:
        """摘要压缩策略"""
        # 这里应该调用AI服务生成摘要，暂时使用简化实现
        target_tokens = model_limits.recommended_tokens
        messages = context_window.messages.copy()
        
        # 保留关键消息和最近消息
        critical_messages = [msg for msg in messages if msg.priority == ContextPriority.CRITICAL]
        recent_messages = messages[-10:]  # 最近10条消息
        
        # 生成摘要（简化实现）
        old_messages = [msg for msg in messages if msg not in critical_messages and msg not in recent_messages]
        
        summary_content = ""
        if old_messages:
            summary_content = f"[对话摘要] 之前的对话包含 {len(old_messages)} 条消息，主要讨论了相关话题。"
        
        # 构建压缩后的消息列表
        compressed_messages = critical_messages.copy()
        
        if summary_content:
            summary_msg = ContextMessage(
                id=-1,
                role=MessageRole.SYSTEM,
                content=summary_content,
                content_type=ContentType.TEXT,
                timestamp=old_messages[0].timestamp if old_messages else datetime.utcnow(),
                tokens=self._estimate_tokens(summary_content),
                priority=ContextPriority.HIGH,
                is_bookmarked=False,
                metadata={"type": "summary", "compressed_messages": len(old_messages)}
            )
            compressed_messages.append(summary_msg)
        
        compressed_messages.extend(recent_messages)
        
        # 按时间排序
        compressed_messages.sort(key=lambda x: x.timestamp)
        
        current_tokens = sum(msg.tokens for msg in compressed_messages)
        
        return ContextWindow(
            messages=compressed_messages,
            total_tokens=current_tokens,
            max_tokens=model_limits.max_tokens,
            compression_strategy=CompressionStrategy.SUMMARY_COMPRESSION,
            summary=summary_content
        )
    
    def _hierarchical_storage(self, context_window: ContextWindow,
                            model_limits: ModelContextLimits) -> ContextWindow:
        """分层存储策略（适用于长上下文模型）"""
        # 对于支持长上下文的模型，可以保留更多信息
        if model_limits.supports_long_context:
            # 直接返回，只做轻微裁剪
            if context_window.total_tokens <= model_limits.max_tokens:
                return context_window
            
            # 只移除临时信息
            filtered_messages = [
                msg for msg in context_window.messages 
                if msg.priority != ContextPriority.TEMPORARY
            ]
            
            current_tokens = sum(msg.tokens for msg in filtered_messages)
            
            return ContextWindow(
                messages=filtered_messages,
                total_tokens=current_tokens,
                max_tokens=model_limits.max_tokens,
                compression_strategy=CompressionStrategy.HIERARCHICAL_STORAGE
            )
        else:
            # 回退到智能截断
            return self._intelligent_truncation(context_window, model_limits)
    
    def _template_compression(self, context_window: ContextWindow,
                            model_limits: ModelContextLimits) -> ContextWindow:
        """模板压缩策略（适用于国产模型）"""
        target_tokens = model_limits.recommended_tokens
        messages = context_window.messages.copy()
        
        # 使用模板化的方式压缩对话
        # 保留系统消息、最新用户消息和最新AI回复
        system_messages = [msg for msg in messages if msg.role == MessageRole.SYSTEM]
        user_messages = [msg for msg in messages if msg.role == MessageRole.USER]
        assistant_messages = [msg for msg in messages if msg.role == MessageRole.ASSISTANT]
        
        # 构建模板化上下文
        template_messages = system_messages.copy()
        
        # 添加最近的对话对
        if user_messages and assistant_messages:
            # 最近的用户消息
            template_messages.append(user_messages[-1])
            # 对应的AI回复
            for ai_msg in reversed(assistant_messages):
                if ai_msg.timestamp > user_messages[-1].timestamp:
                    template_messages.append(ai_msg)
                    break
        
        # 如果还有空间，添加更多历史消息
        remaining_tokens = target_tokens - sum(msg.tokens for msg in template_messages)
        
        for msg in reversed(messages):
            if msg not in template_messages and remaining_tokens > msg.tokens:
                template_messages.append(msg)
                remaining_tokens -= msg.tokens
        
        # 按时间排序
        template_messages.sort(key=lambda x: x.timestamp)
        
        current_tokens = sum(msg.tokens for msg in template_messages)
        
        return ContextWindow(
            messages=template_messages,
            total_tokens=current_tokens,
            max_tokens=model_limits.max_tokens,
            compression_strategy=CompressionStrategy.TEMPLATE_COMPRESSION
        )
    
    def update_context(self, conversation_id: int, new_message: AIChatMessage) -> None:
        """更新对话上下文（添加新消息后的处理）"""
        try:
            self.logger.debug(f"Updating context for conversation {conversation_id} with new message {new_message.id}")
            
            # 这里可以添加上下文更新的逻辑，比如：
            # 1. 更新消息优先级
            # 2. 触发上下文压缩
            # 3. 更新上下文缓存
            
            # 暂时只记录日志
            self.logger.debug(f"Context updated for conversation {conversation_id}")
            
        except Exception as e:
            self.logger.error(f"Error updating context: {str(e)}")
    
    def get_context_summary(self, conversation_id: int) -> Optional[str]:
        """获取对话上下文摘要"""
        try:
            context_window = self.get_conversation_context(conversation_id)
            
            if context_window.summary:
                return context_window.summary
            
            # 生成简单摘要
            message_count = len(context_window.messages)
            total_tokens = context_window.total_tokens
            
            user_messages = [msg for msg in context_window.messages if msg.role == MessageRole.USER]
            ai_messages = [msg for msg in context_window.messages if msg.role == MessageRole.ASSISTANT]
            
            summary = f"对话包含 {message_count} 条消息（{len(user_messages)} 条用户消息，{len(ai_messages)} 条AI回复），总计 {total_tokens} tokens。"
            
            if context_window.messages:
                last_activity = context_window.messages[-1].timestamp
                summary += f" 最后活动时间：{last_activity.strftime('%Y-%m-%d %H:%M:%S')}。"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating context summary: {str(e)}")
            return None
    
    def format_context_for_ai(self, context_window: ContextWindow, 
                             ai_model: str = None) -> List[Dict[str, Any]]:
        """将上下文格式化为AI模型可接受的格式"""
        try:
            formatted_messages = []
            
            for msg in context_window.messages:
                # 转换角色名称
                role_mapping = {
                    MessageRole.USER: "user",
                    MessageRole.ASSISTANT: "assistant", 
                    MessageRole.SYSTEM: "system"
                }
                
                formatted_msg = {
                    "role": role_mapping.get(msg.role, "user"),
                    "content": msg.content
                }
                
                # 添加时间戳（如果AI模型支持）
                if ai_model and "claude" in ai_model.lower():
                    formatted_msg["timestamp"] = msg.timestamp.isoformat()
                
                formatted_messages.append(formatted_msg)
            
            return formatted_messages
            
        except Exception as e:
            self.logger.error(f"Error formatting context for AI: {str(e)}")
            return []
    
    def mark_message_important(self, message_id: int) -> bool:
        """标记消息为重要（影响上下文优先级）"""
        try:
            message = self.db.query(AIChatMessage).filter(
                AIChatMessage.id == message_id
            ).first()
            
            if not message:
                return False
            
            # 设置收藏标志
            message.is_bookmarked = True
            
            # 更新元数据
            metadata = {}
            if message.message_metadata:
                try:
                    metadata = json.loads(message.message_metadata)
                except json.JSONDecodeError:
                    pass
            
            metadata["marked_important"] = True
            metadata["marked_at"] = datetime.utcnow().isoformat()
            
            message.message_metadata = json.dumps(metadata)
            
            self.db.commit()
            
            self.logger.info(f"Marked message {message_id} as important")
            return True
            
        except Exception as e:
            self.logger.error(f"Error marking message as important: {str(e)}")
            self.db.rollback()
            return False
    
    def get_context_statistics(self, conversation_id: int) -> Dict[str, Any]:
        """获取上下文统计信息"""
        try:
            context_window = self.get_conversation_context(conversation_id)
            
            # 按角色统计
            role_stats = {}
            for role in MessageRole:
                role_messages = [msg for msg in context_window.messages if msg.role == role]
                role_stats[role.value] = {
                    "count": len(role_messages),
                    "tokens": sum(msg.tokens for msg in role_messages)
                }
            
            # 按优先级统计
            priority_stats = {}
            for priority in ContextPriority:
                priority_messages = [msg for msg in context_window.messages if msg.priority == priority]
                priority_stats[priority.value] = {
                    "count": len(priority_messages),
                    "tokens": sum(msg.tokens for msg in priority_messages)
                }
            
            # 按内容类型统计
            content_type_stats = {}
            for content_type in ContentType:
                type_messages = [msg for msg in context_window.messages if msg.content_type == content_type]
                content_type_stats[content_type.value] = {
                    "count": len(type_messages),
                    "tokens": sum(msg.tokens for msg in type_messages)
                }
            
            return {
                "total_messages": len(context_window.messages),
                "total_tokens": context_window.total_tokens,
                "max_tokens": context_window.max_tokens,
                "compression_strategy": context_window.compression_strategy.value,
                "role_distribution": role_stats,
                "priority_distribution": priority_stats,
                "content_type_distribution": content_type_stats,
                "has_summary": bool(context_window.summary),
                "bookmarked_messages": len([msg for msg in context_window.messages if msg.is_bookmarked])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting context statistics: {str(e)}")
            return {}