"""
对话管理服务 - 同步版本，用于与现有系统兼容
"""
import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, desc, update, delete

from ..models.ai_chat_session import AIChatSession, SessionStatus
from ..models.ai_chat_message import AIChatMessage, MessageRole, ContentType
from ..core.config import get_settings
from .context_manager import ContextManager
from .context_cache import ContextCache

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversationGroup(str, Enum):
    """会话分组"""
    WORK = "work"
    STUDY = "study"
    PROJECT = "project"
    PERSONAL = "personal"
    RESEARCH = "research"
    DEVELOPMENT = "development"
    TESTING = "testing"
    OTHER = "other"


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


class ConversationServiceSync:
    """对话管理服务 - 同步版本"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.context_manager = ContextManager(db)
        self.context_cache = ContextCache()
    
    def create_conversation(self, user_id: int, title: str = None,
                           ai_provider: str = None, ai_model: str = None,
                           system_prompt: str = None, template_type: str = None,
                           group: ConversationGroup = None, tags: List[str] = None,
                           goal: str = None) -> AIChatSession:
        """创建对话会话"""
        try:
            self.logger.info(f"Creating conversation for user {user_id}")
            
            # 如果没有提供标题，生成智能标题
            if not title:
                title = self._generate_intelligent_title(template_type, goal)
            
            # 根据模板类型选择合适的AI模型
            if not ai_model and template_type:
                ai_model = self._select_model_for_template(template_type)
            
            # 根据模板类型设置系统提示词
            if not system_prompt and template_type:
                system_prompt = self._get_template_system_prompt(template_type)
            
            # 准备会话元数据
            session_metadata = {
                "template_type": template_type,
                "goal": goal,
                "group": group.value if group else None,
                "creation_context": {
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_agent": None,
                    "ip_address": None
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
            self.db.commit()
            self.db.refresh(conversation)
            
            self.logger.info(f"Created conversation {conversation.id} for user {user_id}")
            return conversation
            
        except Exception as e:
            self.logger.error(f"Error creating conversation: {str(e)}")
            self.db.rollback()
            raise
    
    def _generate_intelligent_title(self, template_type: str = None, goal: str = None) -> str:
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
    
    def _select_model_for_template(self, template_type: str) -> str:
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
    
    def _get_template_system_prompt(self, template_type: str) -> str:
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
    
    def get_conversation(self, conversation_id: int, user_id: int = None) -> Optional[AIChatSession]:
        """获取对话会话"""
        try:
            query = self.db.query(AIChatSession).filter(AIChatSession.id == conversation_id)
            
            # 如果提供了用户ID，添加权限检查
            if user_id:
                query = query.filter(AIChatSession.user_id == user_id)
            
            conversation = query.first()
            return conversation
            
        except Exception as e:
            self.logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
            return None
    
    def get_user_conversations(self, user_id: int, status: SessionStatus = None,
                              group: ConversationGroup = None, tags: List[str] = None,
                              sort_by: str = "last_activity_at", sort_order: str = "desc",
                              page: int = 1, size: int = 20) -> Tuple[List[AIChatSession], int]:
        """获取用户的对话列表"""
        try:
            query = self.db.query(AIChatSession).filter(AIChatSession.user_id == user_id)
            
            # 状态过滤
            if status:
                query = query.filter(AIChatSession.status == status)
            
            # 分组过滤
            if group:
                query = query.filter(AIChatSession.session_metadata.contains(f'"group": "{group.value}"'))
            
            # 标签过滤
            if tags:
                for tag in tags:
                    query = query.filter(AIChatSession.tags.contains(tag))
            
            # 获取总数
            total_count = query.count()
            
            # 排序
            sort_column = getattr(AIChatSession, sort_by, AIChatSession.last_activity_at)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
            
            # 分页
            offset = (page - 1) * size
            conversations = query.offset(offset).limit(size).all()
            
            return conversations, total_count
            
        except Exception as e:
            self.logger.error(f"Error getting user conversations: {str(e)}")
            return [], 0
    
    def add_message(self, conversation_id: int, message: Message,
                   ai_provider: str = None, ai_model: str = None,
                   tokens_used: int = 0, confidence_score: float = None) -> AIChatMessage:
        """添加消息到对话"""
        try:
            # 验证对话存在
            conversation = self.get_conversation(conversation_id)
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
            
            self.db.commit()
            self.db.refresh(chat_message)
            
            # 更新上下文
            self.context_manager.update_context(conversation_id, chat_message)
            
            # 使相关缓存失效
            self.context_cache.invalidate_conversation_cache(conversation_id)
            
            self.logger.debug(f"Added message to conversation {conversation_id}")
            return chat_message
            
        except Exception as e:
            self.logger.error(f"Error adding message: {str(e)}")
            self.db.rollback()
            raise
    
    def get_messages(self, conversation_id: int, limit: int = 50,
                    offset: int = 0) -> List[AIChatMessage]:
        """获取对话消息"""
        try:
            messages = self.db.query(AIChatMessage).filter(
                AIChatMessage.session_id == conversation_id
            ).order_by(AIChatMessage.created_at).offset(offset).limit(limit).all()
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error getting messages: {str(e)}")
            return []
    
    def get_message_count(self, conversation_id: int) -> int:
        """获取对话消息总数"""
        try:
            count = self.db.query(AIChatMessage).filter(
                AIChatMessage.session_id == conversation_id
            ).count()
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error getting message count: {str(e)}")
            return 0
    
    def get_latest_message(self, conversation_id: int, role: MessageRole = None) -> Optional[AIChatMessage]:
        """获取最新消息"""
        try:
            query = self.db.query(AIChatMessage).filter(
                AIChatMessage.session_id == conversation_id
            )
            
            if role:
                query = query.filter(AIChatMessage.role == role)
            
            message = query.order_by(desc(AIChatMessage.created_at)).first()
            return message
            
        except Exception as e:
            self.logger.error(f"Error getting latest message: {str(e)}")
            return None
    
    def get_message_by_id(self, message_id: int) -> Optional[AIChatMessage]:
        """根据ID获取消息"""
        try:
            message = self.db.query(AIChatMessage).filter(
                AIChatMessage.id == message_id
            ).first()
            
            return message
            
        except Exception as e:
            self.logger.error(f"Error getting message by ID {message_id}: {str(e)}")
            return None
    
    def get_messages_before(self, conversation_id: int, message_id: int) -> List[AIChatMessage]:
        """获取指定消息之前的所有消息"""
        try:
            # 先获取指定消息的创建时间
            target_message = self.get_message_by_id(message_id)
            if not target_message:
                return []
            
            messages = self.db.query(AIChatMessage).filter(
                and_(
                    AIChatMessage.session_id == conversation_id,
                    AIChatMessage.created_at < target_message.created_at
                )
            ).order_by(AIChatMessage.created_at).all()
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error getting messages before {message_id}: {str(e)}")
            return []
    
    def update_conversation(self, conversation_id: int, **updates) -> bool:
        """更新对话信息"""
        try:
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                return False
            
            # 更新字段
            for key, value in updates.items():
                if hasattr(conversation, key):
                    setattr(conversation, key, value)
            
            conversation.updated_at = datetime.utcnow()
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating conversation: {str(e)}")
            self.db.rollback()
            return False
    
    def archive_conversation(self, conversation_id: int, user_id: int) -> bool:
        """归档对话"""
        return self.update_conversation(
            conversation_id,
            status=SessionStatus.ARCHIVED,
            updated_by=user_id
        )
    
    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """删除对话（软删除）"""
        return self.update_conversation(
            conversation_id,
            status=SessionStatus.DELETED,
            updated_by=user_id
        )
    
    def search_conversations(self, user_id: int, query: str,
                           page: int = 1, size: int = 20) -> List[AIChatSession]:
        """搜索对话"""
        try:
            # 搜索标题和消息内容
            search_query = self.db.query(AIChatSession).filter(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status != SessionStatus.DELETED,
                    or_(
                        AIChatSession.title.contains(query),
                        AIChatSession.id.in_(
                            self.db.query(AIChatMessage.session_id).filter(
                                AIChatMessage.content.contains(query)
                            )
                        )
                    )
                )
            ).order_by(desc(AIChatSession.last_activity_at))
            
            # 分页
            offset = (page - 1) * size
            conversations = search_query.offset(offset).limit(size).all()
            
            return conversations
            
        except Exception as e:
            self.logger.error(f"Error searching conversations: {str(e)}")
            return []
    
    def get_conversation_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户对话统计"""
        try:
            # 总对话数
            total_conversations = self.db.query(AIChatSession).filter(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status != SessionStatus.DELETED
                )
            ).count()
            
            # 活跃对话数
            active_conversations = self.db.query(AIChatSession).filter(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status == SessionStatus.ACTIVE
                )
            ).count()
            
            # 已归档对话数
            archived_conversations = self.db.query(AIChatSession).filter(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status == SessionStatus.ARCHIVED
                )
            ).count()
            
            # 总消息数和Token数
            stats_query = self.db.query(
                func.sum(AIChatSession.message_count).label('total_messages'),
                func.sum(AIChatSession.total_tokens).label('total_tokens')
            ).filter(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status != SessionStatus.DELETED
                )
            ).first()
            
            total_messages = stats_query.total_messages or 0
            total_tokens = stats_query.total_tokens or 0
            
            # 平均每对话消息数
            avg_messages_per_conversation = (
                total_messages / total_conversations if total_conversations > 0 else 0.0
            )
            
            # 最常用的AI提供商和模型
            provider_stats = self.db.query(
                AIChatSession.ai_provider,
                func.count(AIChatSession.id).label('count')
            ).filter(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status != SessionStatus.DELETED,
                    AIChatSession.ai_provider.isnot(None)
                )
            ).group_by(AIChatSession.ai_provider).order_by(desc('count')).first()
            
            model_stats = self.db.query(
                AIChatSession.ai_model,
                func.count(AIChatSession.id).label('count')
            ).filter(
                and_(
                    AIChatSession.user_id == user_id,
                    AIChatSession.status != SessionStatus.DELETED,
                    AIChatSession.ai_model.isnot(None)
                )
            ).group_by(AIChatSession.ai_model).order_by(desc('count')).first()
            
            return {
                'total_conversations': total_conversations,
                'active_conversations': active_conversations,
                'archived_conversations': archived_conversations,
                'total_messages': total_messages,
                'total_tokens': total_tokens,
                'avg_messages_per_conversation': avg_messages_per_conversation,
                'most_used_provider': provider_stats.ai_provider if provider_stats else None,
                'most_used_model': model_stats.ai_model if model_stats else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting conversation stats: {str(e)}")
            return {
                'total_conversations': 0,
                'active_conversations': 0,
                'archived_conversations': 0,
                'total_messages': 0,
                'total_tokens': 0,
                'avg_messages_per_conversation': 0.0,
                'most_used_provider': None,
                'most_used_model': None
            }
    
    def get_conversation_context(self, conversation_id: int, ai_model: str = None,
                               max_messages: int = None, include_system_prompt: bool = True):
        """获取对话上下文"""
        try:
            # 先尝试从缓存获取
            cached_context = self.context_cache.get_cached_context_window(conversation_id, ai_model)
            if cached_context:
                self.logger.debug(f"Retrieved context from cache for conversation {conversation_id}")
                return cached_context
            
            # 从数据库构建上下文
            context_window = self.context_manager.get_conversation_context(
                conversation_id=conversation_id,
                ai_model=ai_model,
                max_messages=max_messages,
                include_system_prompt=include_system_prompt
            )
            
            # 缓存结果
            self.context_cache.cache_context_window(conversation_id, context_window, ai_model)
            
            return context_window
            
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {str(e)}")
            return None
    
    def get_context_summary(self, conversation_id: int) -> Optional[str]:
        """获取对话上下文摘要"""
        try:
            # 先尝试从缓存获取
            cached_summary = self.context_cache.get_cached_summary(conversation_id)
            if cached_summary:
                return cached_summary
            
            # 生成摘要
            summary = self.context_manager.get_context_summary(conversation_id)
            
            # 缓存摘要
            if summary:
                self.context_cache.cache_context_summary(conversation_id, summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting context summary: {str(e)}")
            return None
    
    def get_context_statistics(self, conversation_id: int) -> Dict[str, Any]:
        """获取上下文统计信息"""
        try:
            # 先尝试从缓存获取
            cached_stats = self.context_cache.get_cached_stats(conversation_id)
            if cached_stats:
                return cached_stats
            
            # 生成统计信息
            stats = self.context_manager.get_context_statistics(conversation_id)
            
            # 缓存统计信息
            if stats:
                self.context_cache.cache_context_stats(conversation_id, stats)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting context statistics: {str(e)}")
            return {}
    
    def mark_message_important(self, message_id: int) -> bool:
        """标记消息为重要"""
        try:
            success = self.context_manager.mark_message_important(message_id)
            
            if success:
                # 获取消息所属的对话ID
                message = self.get_message_by_id(message_id)
                if message:
                    # 使对话缓存失效
                    self.context_cache.invalidate_conversation_cache(message.session_id)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error marking message as important: {str(e)}")
            return False
    
    def format_context_for_ai(self, conversation_id: int, ai_model: str = None) -> List[Dict[str, Any]]:
        """将上下文格式化为AI模型可接受的格式"""
        try:
            context_window = self.get_conversation_context(conversation_id, ai_model)
            if not context_window:
                return []
            
            return self.context_manager.format_context_for_ai(context_window, ai_model)
            
        except Exception as e:
            self.logger.error(f"Error formatting context for AI: {str(e)}")
            return []
    
    def preload_context_cache(self, conversation_id: int, ai_models: List[str] = None) -> bool:
        """预加载对话上下文到缓存"""
        try:
            return self.context_cache.preload_context(conversation_id, ai_models)
            
        except Exception as e:
            self.logger.error(f"Error preloading context cache: {str(e)}")
            return False
    
    def get_cache_info(self, conversation_id: int) -> Dict[str, Any]:
        """获取对话的缓存信息"""
        try:
            return self.context_cache.get_cache_info(conversation_id)
            
        except Exception as e:
            self.logger.error(f"Error getting cache info: {str(e)}")
            return {"conversation_id": conversation_id, "error": str(e)}