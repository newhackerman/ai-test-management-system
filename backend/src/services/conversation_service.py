"""
对话管理服务 - 管理AI对话会话和消息
"""
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, update, delete
from sqlalchemy.orm import selectinload

from ..models.ai_chat_session import AIChatSession, SessionStatus
from ..models.ai_chat_message import AIChatMessage, MessageRole, ContentType
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ContextCompressionStrategy(str, Enum):
    """上下文压缩策略"""
    SMART_TRUNCATE = "smart_truncate"  # 智能截断
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    FULL_RETAIN = "full_retain"  # 完整保留
    ADAPTIVE = "adaptive"  # 自适应
    SUMMARY_COMPRESS = "summary_compress"  # 摘要压缩
    KEY_INFO_EXTRACT = "key_info_extract"  # 关键信息提取
    LAYERED_STORAGE = "layered_storage"  # 分层存储
    TEMPLATE_COMPRESS = "template_compress"  # 模板压缩


class ConversationGroup(str, Enum):
    """会话分组"""
    WORK = "work"  # 工作
    STUDY = "study"  # 学习
    PROJECT = "project"  # 项目
    PERSONAL = "personal"  # 个人
    RESEARCH = "research"  # 研究
    DEVELOPMENT = "development"  # 开发
    TESTING = "testing"  # 测试
    OTHER = "other"  # 其他


class ConversationContext:
    """对话上下文对象"""
    def __init__(self, conversation_id: int, messages: List[AIChatMessage],
                 business_context: Optional[Dict] = None,
                 user_preferences: Optional[Dict] = None,
                 summary: Optional[str] = None,
                 compression_strategy: Optional[str] = None,
                 token_count: Optional[int] = None):
        self.conversation_id = conversation_id
        self.messages = messages
        self.business_context = business_context or {}
        self.user_preferences = user_preferences or {}
        self.summary = summary
        self.compression_strategy = compression_strategy
        self.token_count = token_count or sum(msg.tokens_used or 0 for msg in messages)
        
    def get_context_for_model(self, model_name: str) -> str:
        """获取适合特定模型的上下文字符串"""
        context_parts = []
        
        # 添加摘要（如果有）
        if self.summary:
            context_parts.append(f"对话摘要: {self.summary}")
        
        # 添加业务上下文
        if self.business_context:
            context_parts.append(f"业务上下文: {json.dumps(self.business_context, ensure_ascii=False)}")
        
        # 添加消息历史
        for msg in self.messages:
            role_prefix = {"USER": "用户", "ASSISTANT": "助手", "SYSTEM": "系统"}.get(msg.role, msg.role)
            context_parts.append(f"{role_prefix}: {msg.content}")
        
        return "\n\n".join(context_parts)
    
    def get_important_messages(self) -> List[AIChatMessage]:
        """获取重要消息"""
        return [msg for msg in self.messages if msg.is_bookmarked or (msg.user_rating and msg.user_rating >= 4)]
    
    def get_recent_messages(self, count: int = 10) -> List[AIChatMessage]:
        """获取最近的消息"""
        return self.messages[-count:] if len(self.messages) > count else self.messages


class Message:
    """消息对象"""
    def __init__(self, role: MessageRole, content: str, 
                 content_type: ContentType = ContentType.TEXT,
                 metadata: Optional[Dict] = None):
        self.role = role
        self.content = content
        self.content_type = content_type
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()


class ConversationService:
    """对话管理服务"""
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # 上下文管理配置
        self.max_context_messages = 50  # 最大上下文消息数
        self.context_token_limit = 8000  # 上下文Token限制
        
        # 模型特定的上下文策略
        self.model_context_strategies = {
            "gpt-4": {
                "max_tokens": 8000,
                "strategy": ContextCompressionStrategy.SMART_TRUNCATE,
                "compression": ContextCompressionStrategy.SUMMARY_COMPRESS
            },
            "gpt-3.5-turbo": {
                "max_tokens": 4000,
                "strategy": ContextCompressionStrategy.SLIDING_WINDOW,
                "compression": ContextCompressionStrategy.KEY_INFO_EXTRACT
            },
            "claude-3": {
                "max_tokens": 100000,
                "strategy": ContextCompressionStrategy.FULL_RETAIN,
                "compression": ContextCompressionStrategy.LAYERED_STORAGE
            },
            "default": {
                "max_tokens": 2000,
                "strategy": ContextCompressionStrategy.ADAPTIVE,
                "compression": ContextCompressionStrategy.TEMPLATE_COMPRESS
            }
        }
        
    async def create_conversation(self, user_id: int, title: str = None,
                                ai_provider: str = None, ai_model: str = None,
                                system_prompt: str = None, template_type: str = None,
                                group: ConversationGroup = None, tags: List[str] = None,
                                goal: str = None) -> AIChatSession:
        """
        创建对话会话
        
        Args:
            user_id: 用户ID
            title: 对话标题
            ai_provider: AI服务提供商
            ai_model: AI模型
            system_prompt: 系统提示词
            template_type: 会话模板类型（通用对话、代码助手、测试专家等）
            group: 会话分组
            tags: 会话标签
            goal: 会话目标
            
        Returns:
            AIChatSession: 创建的对话会话
        """
        try:
            self.logger.info(f"Creating conversation for user {user_id}")
            
            # 如果没有提供标题，生成智能标题
            if not title:
                title = await self._generate_intelligent_title(template_type, goal)
            
            # 根据模板类型选择合适的AI模型
            if not ai_model and template_type:
                ai_model = await self._select_model_for_template(template_type)
            
            # 根据模板类型设置系统提示词
            if not system_prompt and template_type:
                system_prompt = await self._get_template_system_prompt(template_type)
            
            # 准备会话元数据
            session_metadata = {
                "template_type": template_type,
                "goal": goal,
                "group": group.value if group else None,
                "creation_context": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_agent": None,  # 可以从请求中获取
                    "ip_address": None   # 可以从请求中获取
                }
            }
            
            # 创建会话
            conversation = AIChatSession(
                title=title,
                user_id=user_id,
                status=SessionStatus.ACTIVE,
                ai_provider=ai_provider,
                ai_model=ai_model,
                system_prompt=system_prompt,
                message_count=0,
                total_tokens=0,
                last_activity_at=datetime.utcnow(),
                tags=json.dumps(tags) if tags else None,
                session_metadata=json.dumps(session_metadata),
                created_by=user_id
            )
            
            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)
            
            self.logger.info(f"Created conversation {conversation.id} for user {user_id}")
            return conversation
            
        except Exception as e:
            self.logger.error(f"Error creating conversation: {str(e)}")
            await self.db.rollback()
            raise
    
    async def _generate_intelligent_title(self, template_type: str = None, goal: str = None) -> str:
        """生成智能标题"""
        if template_type:
            template_titles = {
                "general": "通用对话",
                "code_assistant": "代码助手",
                "test_expert": "测试专家",
                "document_writer": "文档写作",
                "data_analyst": "数据分析",
                "creative_design": "创意设计",
                "academic_research": "学术研究",
                "project_management": "项目管理"
            }
            base_title = template_titles.get(template_type, "AI对话")
        else:
            base_title = "AI对话"
        
        # 添加时间戳
        timestamp = datetime.utcnow().strftime('%m-%d %H:%M')
        
        if goal:
            return f"{base_title} - {goal[:20]}... ({timestamp})"
        else:
            return f"{base_title} ({timestamp})"
    
    async def _select_model_for_template(self, template_type: str) -> str:
        """根据模板类型选择合适的AI模型"""
        model_mapping = {
            "code_assistant": "gpt-4",
            "test_expert": "gpt-4-turbo",
            "document_writer": "claude-3-opus",
            "data_analyst": "gpt-4-turbo",
            "creative_design": "gpt-4",
            "academic_research": "claude-3-opus",
            "project_management": "gpt-3.5-turbo",
            "general": "gpt-3.5-turbo"
        }
        return model_mapping.get(template_type, "gpt-3.5-turbo")
    
    async def _get_template_system_prompt(self, template_type: str) -> str:
        """获取模板系统提示词"""
        prompts = {
            "code_assistant": "你是一个专业的编程助手，擅长代码生成、调试和优化。请提供准确、高效的代码解决方案。",
            "test_expert": "你是一个测试专家，专门帮助用户设计测试用例、分析测试策略和优化测试流程。",
            "document_writer": "你是一个专业的技术文档写作助手，擅长创建清晰、结构化的文档。",
            "data_analyst": "你是一个数据分析专家，擅长数据处理、统计分析和可视化建议。",
            "creative_design": "你是一个创意设计助手，擅长方案设计、创意思考和多角度分析。",
            "academic_research": "你是一个学术研究助手，擅长深度分析、严谨推理和学术写作。",
            "project_management": "你是一个项目管理助手，擅长项目规划、风险管理和团队协作。",
            "general": "你是一个友好、有帮助的AI助手，可以回答各种问题并提供有用的建议。"
        }
        return prompts.get(template_type, prompts["general"])
    
    async def get_conversation(self, conversation_id: int, user_id: int = None) -> Optional[AIChatSession]:
        """
        获取对话会话
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限检查）
            
        Returns:
            Optional[AIChatSession]: 对话会话
        """
        try:
            query = select(AIChatSession).where(AIChatSession.id == conversation_id)
            
            # 如果提供了用户ID，添加权限检查
            if user_id:
                query = query.where(AIChatSession.user_id == user_id)
            
            result = await self.db.execute(query)
            conversation = result.scalar_one_or_none()
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
            return None
    
    async def get_user_conversations(self, user_id: int, status: SessionStatus = None,
                                   group: ConversationGroup = None, tags: List[str] = None,
                                   sort_by: str = "last_activity", sort_order: str = "desc",
                                   page: int = 1, size: int = 20) -> Tuple[List[AIChatSession], int]:
        """
        获取用户的对话列表
        
        Args:
            user_id: 用户ID
            status: 会话状态过滤
            group: 会话分组过滤
            tags: 标签过滤
            sort_by: 排序字段（last_activity, created_at, title, message_count, total_tokens）
            sort_order: 排序方向（asc, desc）
            page: 页码
            size: 每页大小
            
        Returns:
            Tuple[List[AIChatSession], int]: (对话列表, 总数)
        """
        try:
            query = select(AIChatSession).where(AIChatSession.user_id == user_id)
            
            # 状态过滤
            if status:
                query = query.where(AIChatSession.status == status)
            
            # 分组过滤
            if group:
                query = query.where(AIChatSession.session_metadata.contains(f'"group": "{group.value}"'))
            
            # 标签过滤
            if tags:
                for tag in tags:
                    query = query.where(AIChatSession.tags.contains(tag))
            
            # 排序
            sort_column = getattr(AIChatSession, sort_by, AIChatSession.last_activity_at)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
            
            # 获取总数
            count_query = select(func.count(AIChatSession.id)).where(AIChatSession.user_id == user_id)
            if status:
                count_query = count_query.where(AIChatSession.status == status)
            if group:
                count_query = count_query.where(AIChatSession.session_metadata.contains(f'"group": "{group.value}"'))
            if tags:
                for tag in tags:
                    count_query = count_query.where(AIChatSession.tags.contains(tag))
            
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar() or 0
            
            # 分页
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)
            
            result = await self.db.execute(query)
            conversations = result.scalars().all()
            
            return list(conversations), total_count
            
        except Exception as e:
            self.logger.error(f"Error getting user conversations: {str(e)}")
            return [], 0
    
    async def add_message(self, conversation_id: int, message: Message,
                         ai_provider: str = None, ai_model: str = None,
                         tokens_used: int = 0, confidence_score: float = None) -> AIChatMessage:
        """
        添加消息到对话
        
        Args:
            conversation_id: 对话ID
            message: 消息对象
            ai_provider: AI服务提供商
            ai_model: AI模型
            tokens_used: 使用的Token数
            confidence_score: 置信度分数
            
        Returns:
            AIChatMessage: 保存的消息
        """
        try:
            # 验证对话存在
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"对话 {conversation_id} 不存在")
            
            # 创建消息
            chat_message = AIChatMessage(
                session_id=conversation_id,
                role=message.role,
                content=message.content,
                content_type=message.content_type,
                ai_provider=ai_provider,
                ai_model=ai_model,
                tokens_used=tokens_used,
                confidence_score=confidence_score,
                message_metadata=json.dumps(message.metadata) if message.metadata else None,
                created_by=conversation.user_id
            )
            
            self.db.add(chat_message)
            
            # 更新对话统计
            conversation.message_count += 1
            conversation.total_tokens += tokens_used
            conversation.last_activity_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(chat_message)
            
            self.logger.debug(f"Added message to conversation {conversation_id}")
            return chat_message
            
        except Exception as e:
            self.logger.error(f"Error adding message: {str(e)}")
            await self.db.rollback()
            raise
    
    async def get_messages(self, conversation_id: int, limit: int = 50,
                          offset: int = 0) -> List[AIChatMessage]:
        """
        获取对话消息
        
        Args:
            conversation_id: 对话ID
            limit: 消息数量限制
            offset: 偏移量
            
        Returns:
            List[AIChatMessage]: 消息列表
        """
        try:
            query = select(AIChatMessage).where(
                AIChatMessage.session_id == conversation_id
            ).order_by(AIChatMessage.created_at).offset(offset).limit(limit)
            
            result = await self.db.execute(query)
            messages = result.scalars().all()
            
            return list(messages)
            
        except Exception as e:
            self.logger.error(f"Error getting messages: {str(e)}")
            return []
    
    async def get_conversation_context(self, conversation_id: int,
                                     max_messages: int = None, ai_model: str = None,
                                     include_important_only: bool = False) -> ConversationContext:
        """
        获取对话上下文
        
        Args:
            conversation_id: 对话ID
            max_messages: 最大消息数
            ai_model: AI模型（用于选择上下文策略）
            include_important_only: 是否只包含重要消息
            
        Returns:
            ConversationContext: 对话上下文
        """
        try:
            # 获取会话信息
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return ConversationContext(conversation_id, [])
            
            # 确定使用的AI模型
            model = ai_model or conversation.ai_model or "default"
            
            # 获取模型特定的上下文策略
            strategy_config = self.model_context_strategies.get(model, self.model_context_strategies["default"])
            
            # 获取消息
            if include_important_only:
                messages = await self._get_important_messages(conversation_id, strategy_config["max_tokens"])
            else:
                messages = await self._get_context_messages(conversation_id, max_messages, strategy_config)
            
            # 智能压缩上下文
            compressed_messages = await self._compress_context(messages, strategy_config)
            
            # 获取业务上下文
            business_context = await self._get_business_context(conversation_id)
            
            # 获取用户偏好
            user_preferences = await self._get_user_preferences(conversation_id)
            
            # 生成上下文摘要（如果需要）
            context_summary = await self._generate_context_summary(compressed_messages, strategy_config)
            
            context = ConversationContext(
                conversation_id=conversation_id,
                messages=compressed_messages,
                business_context=business_context,
                user_preferences=user_preferences
            )
            
            # 添加上下文摘要
            if context_summary:
                context.summary = context_summary
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {str(e)}")
            return ConversationContext(conversation_id, [])
    
    async def _get_context_messages(self, conversation_id: int, max_messages: int = None, 
                                  strategy_config: Dict = None) -> List[AIChatMessage]:
        """获取上下文消息"""
        limit = max_messages or self.max_context_messages
        
        # 根据策略调整获取数量
        if strategy_config:
            if strategy_config["strategy"] == ContextCompressionStrategy.FULL_RETAIN:
                limit = 1000  # 大量获取
            elif strategy_config["strategy"] == ContextCompressionStrategy.SLIDING_WINDOW:
                limit = min(limit, 20)  # 限制数量
        
        return await self.get_messages(conversation_id, limit=limit)
    
    async def _get_important_messages(self, conversation_id: int, max_tokens: int) -> List[AIChatMessage]:
        """获取重要消息"""
        # 获取被收藏的消息
        bookmarked_query = select(AIChatMessage).where(
            and_(
                AIChatMessage.session_id == conversation_id,
                AIChatMessage.is_bookmarked == True
            )
        ).order_by(AIChatMessage.created_at)
        
        bookmarked_result = await self.db.execute(bookmarked_query)
        bookmarked_messages = list(bookmarked_result.scalars().all())
        
        # 获取高评分消息
        high_rated_query = select(AIChatMessage).where(
            and_(
                AIChatMessage.session_id == conversation_id,
                AIChatMessage.user_rating >= 4
            )
        ).order_by(desc(AIChatMessage.user_rating), AIChatMessage.created_at)
        
        high_rated_result = await self.db.execute(high_rated_query)
        high_rated_messages = list(high_rated_result.scalars().all())
        
        # 合并并去重
        important_messages = []
        seen_ids = set()
        
        for msg in bookmarked_messages + high_rated_messages:
            if msg.id not in seen_ids:
                important_messages.append(msg)
                seen_ids.add(msg.id)
        
        # 按时间排序
        important_messages.sort(key=lambda x: x.created_at)
        
        return important_messages
    
    async def _compress_context(self, messages: List[AIChatMessage], 
                              strategy_config: Dict) -> List[AIChatMessage]:
        """压缩上下文"""
        if not messages:
            return messages
        
        strategy = strategy_config.get("strategy", ContextCompressionStrategy.ADAPTIVE)
        max_tokens = strategy_config.get("max_tokens", self.context_token_limit)
        
        # 计算当前Token数（简化计算）
        current_tokens = sum(len(msg.content.split()) * 1.3 for msg in messages)  # 粗略估算
        
        if current_tokens <= max_tokens:
            return messages
        
        # 根据策略压缩
        if strategy == ContextCompressionStrategy.SLIDING_WINDOW:
            return await self._sliding_window_compress(messages, max_tokens)
        elif strategy == ContextCompressionStrategy.SMART_TRUNCATE:
            return await self._smart_truncate_compress(messages, max_tokens)
        elif strategy == ContextCompressionStrategy.KEY_INFO_EXTRACT:
            return await self._key_info_extract_compress(messages, max_tokens)
        else:
            # 默认策略：保留最近的消息
            return messages[-int(max_tokens / 100):]
    
    async def _sliding_window_compress(self, messages: List[AIChatMessage], 
                                     max_tokens: int) -> List[AIChatMessage]:
        """滑动窗口压缩"""
        # 保留最近的消息，直到达到Token限制
        compressed = []
        current_tokens = 0
        
        for msg in reversed(messages):
            msg_tokens = len(msg.content.split()) * 1.3
            if current_tokens + msg_tokens <= max_tokens:
                compressed.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        return compressed
    
    async def _smart_truncate_compress(self, messages: List[AIChatMessage], 
                                     max_tokens: int) -> List[AIChatMessage]:
        """智能截断压缩"""
        # 保留系统消息、重要消息和最近消息
        system_messages = [msg for msg in messages if msg.role == MessageRole.SYSTEM]
        important_messages = [msg for msg in messages if msg.is_bookmarked or (msg.user_rating and msg.user_rating >= 4)]
        recent_messages = messages[-10:]  # 最近10条消息
        
        # 合并并去重
        compressed = []
        seen_ids = set()
        
        for msg_list in [system_messages, important_messages, recent_messages]:
            for msg in msg_list:
                if msg.id not in seen_ids:
                    compressed.append(msg)
                    seen_ids.add(msg.id)
        
        # 按时间排序
        compressed.sort(key=lambda x: x.created_at)
        
        # 如果还是太多，进一步截断
        if len(compressed) > max_tokens / 100:
            compressed = compressed[-int(max_tokens / 100):]
        
        return compressed
    
    async def _key_info_extract_compress(self, messages: List[AIChatMessage], 
                                       max_tokens: int) -> List[AIChatMessage]:
        """关键信息提取压缩"""
        # 这里可以使用AI来提取关键信息，简化实现
        # 保留包含关键词的消息
        keywords = ["错误", "问题", "解决", "重要", "关键", "注意", "警告", "成功", "完成"]
        
        important_messages = []
        for msg in messages:
            if any(keyword in msg.content for keyword in keywords):
                important_messages.append(msg)
        
        # 如果重要消息太少，补充最近的消息
        if len(important_messages) < 5:
            recent_messages = messages[-10:]
            for msg in recent_messages:
                if msg not in important_messages:
                    important_messages.append(msg)
        
        # 按时间排序并限制数量
        important_messages.sort(key=lambda x: x.created_at)
        return important_messages[-int(max_tokens / 100):]
    
    async def _generate_context_summary(self, messages: List[AIChatMessage], 
                                      strategy_config: Dict) -> Optional[str]:
        """生成上下文摘要"""
        if not messages or len(messages) < 5:
            return None
        
        # 简化实现：生成基本摘要
        total_messages = len(messages)
        user_messages = len([msg for msg in messages if msg.role == MessageRole.USER])
        assistant_messages = len([msg for msg in messages if msg.role == MessageRole.ASSISTANT])
        
        summary = f"对话包含{total_messages}条消息，其中用户消息{user_messages}条，AI回复{assistant_messages}条。"
        
        # 添加主要话题（基于关键词频率）
        all_content = " ".join([msg.content for msg in messages])
        # 这里可以添加更复杂的主题提取逻辑
        
        return summary
    
    async def update_conversation(self, conversation_id: int, **updates) -> bool:
        """
        更新对话信息
        
        Args:
            conversation_id: 对话ID
            **updates: 更新字段
            
        Returns:
            bool: 是否成功
        """
        try:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return False
            
            # 更新字段
            for key, value in updates.items():
                if hasattr(conversation, key):
                    setattr(conversation, key, value)
            
            conversation.updated_at = datetime.utcnow()
            
            await self.db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating conversation: {str(e)}")
            await self.db.rollback()
            return False
    
    async def archive_conversation(self, conversation_id: int, user_id: int) -> bool:
        """
        归档对话
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        return await self.update_conversation(
            conversation_id,
            status=SessionStatus.ARCHIVED,
            updated_by=user_id
        )
    
    async def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """
        删除对话（软删除）
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        return await self.update_conversation(
            conversation_id,
            status=SessionStatus.DELETED,
            updated_by=user_id
        )
    
    async def search_conversations(self, user_id: int, query: str,
                                 page: int = 1, size: int = 20) -> List[AIChatSession]:
        """
        搜索对话
        
        Args:
            user_id: 用户ID
            query: 搜索关键词
            page: 页码
            size: 每页大小
            
        Returns:
            List[AIChatSession]: 搜索结果
        """
        try:
            # 搜索标题和消息内容
            search_query = select(AIChatSession).where(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status != SessionStatus.DELETED,
                    or_(
                        AIChatSession.title.contains(query),
                        AIChatSession.id.in_(
                            select(AIChatMessage.session_id).where(
                                AIChatMessage.content.contains(query)
                            )
                        )
                    )
                )
            ).order_by(desc(AIChatSession.last_activity_at))
            
            # 分页
            offset = (page - 1) * size
            search_query = search_query.offset(offset).limit(size)
            
            result = await self.db.execute(search_query)
            conversations = result.scalars().all()
            
            return list(conversations)
            
        except Exception as e:
            self.logger.error(f"Error searching conversations: {str(e)}")
            return []
    
    async def get_conversation_stats(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户对话统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 总对话数
            total_query = select(func.count(AIChatSession.id)).where(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status != SessionStatus.DELETED
                )
            )
            total_result = await self.db.execute(total_query)
            total_conversations = total_result.scalar() or 0
            
            # 活跃对话数
            active_query = select(func.count(AIChatSession.id)).where(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status == SessionStatus.ACTIVE
                )
            )
            active_result = await self.db.execute(active_query)
            active_conversations = active_result.scalar() or 0
            
            # 总消息数
            message_query = select(func.count(AIChatMessage.id)).where(
                AIChatMessage.session_id.in_(
                    select(AIChatSession.id).where(AIChatSession.user_id == user_id)
                )
            )
            message_result = await self.db.execute(message_query)
            total_messages = message_result.scalar() or 0
            
            # 总Token数
            token_query = select(func.sum(AIChatSession.total_tokens)).where(
                AIChatSession.user_id == user_id
            )
            token_result = await self.db.execute(token_query)
            total_tokens = token_result.scalar() or 0
            
            return {
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "archived_conversations": total_conversations - active_conversations,
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "avg_messages_per_conversation": total_messages / total_conversations if total_conversations > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting conversation stats: {str(e)}")
            return {}
    
    async def _get_business_context(self, conversation_id: int) -> Dict[str, Any]:
        """获取业务上下文"""
        # 这里可以扩展获取项目、需求等业务上下文
        return {}
    
    async def _get_user_preferences(self, conversation_id: int) -> Dict[str, Any]:
        """获取用户偏好"""
        # 这里可以扩展获取用户的AI使用偏好
        return {}
    
    async def branch_conversation(self, conversation_id: int, from_message_id: int,
                                user_id: int, new_title: str = None) -> AIChatSession:
        """
        从指定消息点创建分支对话
        
        Args:
            conversation_id: 原对话ID
            from_message_id: 分支起点消息ID
            user_id: 用户ID
            new_title: 新对话标题
            
        Returns:
            AIChatSession: 新的分支对话
        """
        try:
            # 获取原对话
            original_conversation = await self.get_conversation(conversation_id, user_id)
            if not original_conversation:
                raise ValueError("原对话不存在")
            
            # 获取分支点之前的消息
            messages_query = select(AIChatMessage).where(
                and_(
                    AIChatMessage.session_id == conversation_id,
                    AIChatMessage.id <= from_message_id
                )
            ).order_by(AIChatMessage.created_at)
            
            messages_result = await self.db.execute(messages_query)
            messages_to_copy = list(messages_result.scalars().all())
            
            # 生成新标题
            if not new_title:
                new_title = f"{original_conversation.title} - 分支 {datetime.utcnow().strftime('%m-%d %H:%M')}"
            
            # 创建新对话
            new_conversation = AIChatSession(
                title=new_title,
                user_id=user_id,
                status=SessionStatus.ACTIVE,
                ai_provider=original_conversation.ai_provider,
                ai_model=original_conversation.ai_model,
                system_prompt=original_conversation.system_prompt,
                message_count=len(messages_to_copy),
                total_tokens=sum(msg.tokens_used or 0 for msg in messages_to_copy),
                last_activity_at=datetime.utcnow(),
                tags=original_conversation.tags,
                session_metadata=json.dumps({
                    **json.loads(original_conversation.session_metadata or "{}"),
                    "branched_from": conversation_id,
                    "branch_point": from_message_id,
                    "branch_created_at": datetime.utcnow().isoformat()
                }),
                created_by=user_id
            )
            
            self.db.add(new_conversation)
            await self.db.flush()  # 获取新对话ID
            
            # 复制消息
            for original_msg in messages_to_copy:
                new_message = AIChatMessage(
                    session_id=new_conversation.id,
                    role=original_msg.role,
                    content=original_msg.content,
                    content_type=original_msg.content_type,
                    ai_provider=original_msg.ai_provider,
                    ai_model=original_msg.ai_model,
                    tokens_used=original_msg.tokens_used,
                    confidence_score=original_msg.confidence_score,
                    message_metadata=original_msg.message_metadata,
                    created_by=user_id
                )
                self.db.add(new_message)
            
            await self.db.commit()
            await self.db.refresh(new_conversation)
            
            self.logger.info(f"Created branch conversation {new_conversation.id} from {conversation_id}")
            return new_conversation
            
        except Exception as e:
            self.logger.error(f"Error branching conversation: {str(e)}")
            await self.db.rollback()
            raise
    
    async def merge_conversations(self, target_conversation_id: int, source_conversation_ids: List[int],
                                user_id: int, new_title: str = None) -> AIChatSession:
        """
        合并多个对话
        
        Args:
            target_conversation_id: 目标对话ID
            source_conversation_ids: 源对话ID列表
            user_id: 用户ID
            new_title: 新标题
            
        Returns:
            AIChatSession: 合并后的对话
        """
        try:
            # 获取目标对话
            target_conversation = await self.get_conversation(target_conversation_id, user_id)
            if not target_conversation:
                raise ValueError("目标对话不存在")
            
            # 获取所有源对话
            source_conversations = []
            for source_id in source_conversation_ids:
                source_conv = await self.get_conversation(source_id, user_id)
                if source_conv:
                    source_conversations.append(source_conv)
            
            if not source_conversations:
                raise ValueError("没有有效的源对话")
            
            # 获取所有消息并按时间排序
            all_messages = []
            
            # 目标对话的消息
            target_messages = await self.get_messages(target_conversation_id, limit=1000)
            for msg in target_messages:
                msg.merge_source = "target"
                all_messages.append(msg)
            
            # 源对话的消息
            for source_conv in source_conversations:
                source_messages = await self.get_messages(source_conv.id, limit=1000)
                for msg in source_messages:
                    msg.merge_source = f"source_{source_conv.id}"
                    all_messages.append(msg)
            
            # 按时间排序
            all_messages.sort(key=lambda x: x.created_at)
            
            # 更新目标对话
            if new_title:
                target_conversation.title = new_title
            
            # 更新统计信息
            target_conversation.message_count = len(all_messages)
            target_conversation.total_tokens = sum(msg.tokens_used or 0 for msg in all_messages)
            target_conversation.last_activity_at = datetime.utcnow()
            
            # 更新元数据
            merge_metadata = {
                **json.loads(target_conversation.session_metadata or "{}"),
                "merged_conversations": source_conversation_ids,
                "merge_created_at": datetime.utcnow().isoformat()
            }
            target_conversation.session_metadata = json.dumps(merge_metadata)
            
            # 删除原有消息并重新插入排序后的消息
            await self.db.execute(
                delete(AIChatMessage).where(AIChatMessage.session_id == target_conversation_id)
            )
            
            for msg in all_messages:
                new_message = AIChatMessage(
                    session_id=target_conversation_id,
                    role=msg.role,
                    content=msg.content,
                    content_type=msg.content_type,
                    ai_provider=msg.ai_provider,
                    ai_model=msg.ai_model,
                    tokens_used=msg.tokens_used,
                    confidence_score=msg.confidence_score,
                    message_metadata=json.dumps({
                        **json.loads(msg.message_metadata or "{}"),
                        "merge_source": getattr(msg, 'merge_source', 'unknown')
                    }),
                    created_at=msg.created_at,
                    created_by=user_id
                )
                self.db.add(new_message)
            
            # 归档源对话
            for source_conv in source_conversations:
                source_conv.status = SessionStatus.ARCHIVED
                source_conv.updated_at = datetime.utcnow()
                source_conv.updated_by = user_id
            
            await self.db.commit()
            
            self.logger.info(f"Merged conversations {source_conversation_ids} into {target_conversation_id}")
            return target_conversation
            
        except Exception as e:
            self.logger.error(f"Error merging conversations: {str(e)}")
            await self.db.rollback()
            raise
    
    async def generate_share_link(self, conversation_id: int, user_id: int,
                                expires_in_hours: int = 24, permissions: List[str] = None) -> str:
        """
        生成对话分享链接
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            expires_in_hours: 过期时间（小时）
            permissions: 权限列表（view, comment, copy等）
            
        Returns:
            str: 分享链接token
        """
        try:
            # 验证对话存在
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                raise ValueError("对话不存在")
            
            # 生成分享token
            share_data = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "expires_at": (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat(),
                "permissions": permissions or ["view"],
                "created_at": datetime.utcnow().isoformat()
            }
            
            # 使用简单的hash生成token（实际应用中应该使用更安全的方法）
            share_token = hashlib.sha256(
                f"{conversation_id}_{user_id}_{datetime.utcnow().timestamp()}".encode()
            ).hexdigest()[:32]
            
            # 存储分享信息（这里简化存储在会话元数据中）
            metadata = json.loads(conversation.session_metadata or "{}")
            if "shares" not in metadata:
                metadata["shares"] = {}
            
            metadata["shares"][share_token] = share_data
            conversation.session_metadata = json.dumps(metadata)
            
            await self.db.commit()
            
            self.logger.info(f"Generated share link for conversation {conversation_id}")
            return share_token
            
        except Exception as e:
            self.logger.error(f"Error generating share link: {str(e)}")
            raise
    
    async def export_conversation(self, conversation_id: int, user_id: int,
                                format: str = "markdown") -> str:
        """
        导出对话
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            format: 导出格式（markdown, json, txt）
            
        Returns:
            str: 导出内容
        """
        try:
            # 获取对话和消息
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                raise ValueError("对话不存在")
            
            messages = await self.get_messages(conversation_id, limit=1000)
            
            if format.lower() == "markdown":
                return await self._export_to_markdown(conversation, messages)
            elif format.lower() == "json":
                return await self._export_to_json(conversation, messages)
            elif format.lower() == "txt":
                return await self._export_to_txt(conversation, messages)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
                
        except Exception as e:
            self.logger.error(f"Error exporting conversation: {str(e)}")
            raise
    
    async def _export_to_markdown(self, conversation: AIChatSession, 
                                messages: List[AIChatMessage]) -> str:
        """导出为Markdown格式"""
        content = f"# {conversation.title}\n\n"
        content += f"**创建时间**: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"**AI模型**: {conversation.ai_model or 'Unknown'}\n"
        content += f"**消息数量**: {len(messages)}\n"
        content += f"**总Token数**: {conversation.total_tokens}\n\n"
        content += "---\n\n"
        
        for msg in messages:
            role_name = {"USER": "用户", "ASSISTANT": "AI助手", "SYSTEM": "系统"}.get(msg.role, msg.role)
            content += f"## {role_name}\n\n"
            content += f"**时间**: {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += f"{msg.content}\n\n"
            
            if msg.tokens_used:
                content += f"*Token使用: {msg.tokens_used}*\n\n"
            
            content += "---\n\n"
        
        return content
    
    async def _export_to_json(self, conversation: AIChatSession, 
                            messages: List[AIChatMessage]) -> str:
        """导出为JSON格式"""
        data = {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "ai_provider": conversation.ai_provider,
                "ai_model": conversation.ai_model,
                "message_count": len(messages),
                "total_tokens": conversation.total_tokens
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "content_type": msg.content_type,
                    "created_at": msg.created_at.isoformat(),
                    "tokens_used": msg.tokens_used,
                    "confidence_score": msg.confidence_score
                }
                for msg in messages
            ]
        }
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    async def _export_to_txt(self, conversation: AIChatSession, 
                           messages: List[AIChatMessage]) -> str:
        """导出为纯文本格式"""
        content = f"{conversation.title}\n"
        content += f"创建时间: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"AI模型: {conversation.ai_model or 'Unknown'}\n"
        content += f"消息数量: {len(messages)}\n"
        content += f"总Token数: {conversation.total_tokens}\n"
        content += "=" * 50 + "\n\n"
        
        for msg in messages:
            role_name = {"USER": "用户", "ASSISTANT": "AI助手", "SYSTEM": "系统"}.get(msg.role, msg.role)
            content += f"[{msg.created_at.strftime('%H:%M:%S')}] {role_name}:\n"
            content += f"{msg.content}\n\n"
        
        return content
    
    async def add_conversation_tags(self, conversation_id: int, user_id: int, 
                                  tags: List[str]) -> bool:
        """
        添加对话标签
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            tags: 标签列表
            
        Returns:
            bool: 是否成功
        """
        try:
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return False
            
            # 获取现有标签
            existing_tags = json.loads(conversation.tags or "[]")
            
            # 合并标签并去重
            all_tags = list(set(existing_tags + tags))
            
            # 更新标签
            conversation.tags = json.dumps(all_tags)
            conversation.updated_at = datetime.utcnow()
            
            await self.db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding conversation tags: {str(e)}")
            await self.db.rollback()
            return False
    
    async def remove_conversation_tags(self, conversation_id: int, user_id: int, 
                                     tags: List[str]) -> bool:
        """
        移除对话标签
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            tags: 要移除的标签列表
            
        Returns:
            bool: 是否成功
        """
        try:
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return False
            
            # 获取现有标签
            existing_tags = json.loads(conversation.tags or "[]")
            
            # 移除指定标签
            remaining_tags = [tag for tag in existing_tags if tag not in tags]
            
            # 更新标签
            conversation.tags = json.dumps(remaining_tags)
            conversation.updated_at = datetime.utcnow()
            
            await self.db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing conversation tags: {str(e)}")
            await self.db.rollback()
            return False
    
    async def cleanup_old_conversations(self, days: int = 30) -> int:
        """
        清理旧对话
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的对话数
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 查找需要清理的对话
            query = select(AIChatSession).where(
                and_(
                    AIChatSession.status == SessionStatus.DELETED,
                    AIChatSession.updated_at < cutoff_date
                )
            )
            result = await self.db.execute(query)
            old_conversations = result.scalars().all()
            
            # 删除对话及其消息
            count = 0
            for conversation in old_conversations:
                # 删除消息
                await self.db.execute(
                    delete(AIChatMessage).where(AIChatMessage.session_id == conversation.id)
                )
                
                # 删除对话
                await self.db.delete(conversation)
                count += 1
            
            await self.db.commit()
            
            self.logger.info(f"Cleaned up {count} old conversations")
            return count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up conversations: {str(e)}")
            await self.db.rollback()
            return 0