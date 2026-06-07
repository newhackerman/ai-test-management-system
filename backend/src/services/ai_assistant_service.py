"""
AI助手核心服务类 - 提供AI对话、智能建议、上下文管理等核心功能

本模块实现了AI助手的核心功能，包括：
1. 智能查询处理和AI服务路由
2. 业务上下文分析和智能建议生成
3. 问题分析和解决方案推荐
4. 依赖注入和服务管理
5. 用户权限集成和访问控制
6. 操作日志记录和审计

技术特性：
- 异步编程模式，支持高并发
- 多AI服务提供商智能路由
- 上下文感知的智能分析
- 可扩展的建议引擎架构
- 与主系统用户权限无缝集成
- 全面的操作日志记录和监控
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Protocol
from enum import Enum
from abc import ABC, abstractmethod

import aiohttp
from dotenv import dotenv_values
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.container import get_container
from ..core.exceptions import PermissionError, ValidationError
from ..models.base import BaseModel
from ..services.ai_permission_service import AIPermissionService
from ..services.project_data_sync_service import get_project_sync_service, get_project_context
from ..services.ai_operation_log_service import get_ai_operation_log_service
from ..services.multilingual_response_service import get_multilingual_response_service, MultilingualResponseService
from ..models.ai_operation_log import AIOperationType, AIOperationResult, AIOperationPriority
from ..decorators.ai_operation_logger import (
    log_ai_model_call, log_conversation_activity, log_suggestion_activity
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_openai_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    """Prefer project .env OpenAI settings over inherited machine env vars."""
    backend_dir = Path(__file__).resolve().parents[2]
    project_dir = backend_dir.parent
    for env_file in (backend_dir / ".env", project_dir / ".env"):
        if env_file.exists():
            value = dotenv_values(env_file).get(name)
            if value:
                return value

    return os.getenv(name) or getattr(settings, name, default) or default


# 依赖注入接口定义
class IAIRouter(Protocol):
    """AI路由服务接口"""
    async def route_request(self, request: Any) -> Any: ...


class IConversationManager(Protocol):
    """对话管理服务接口"""
    async def create_conversation(self, user_id: int, title: str) -> Any: ...
    async def add_message(self, conversation_id: int, message: Any) -> Any: ...


class IContextAnalyzer(Protocol):
    """上下文分析服务接口"""
    async def analyze_context(self, context: Any) -> Any: ...


class ISuggestionEngine(Protocol):
    """建议引擎接口"""
    async def generate_suggestions(self, context: Any) -> List[Any]: ...


class AIProvider(Enum):
    """AI服务提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BAIDU_WENXIN = "baidu_wenxin"
    ALIYUN_TONGYI = "aliyun_tongyi"
    GOOGLE_GEMINI = "google_gemini"


class TaskType(Enum):
    """任务类型枚举"""
    SIMPLE_QUERY = "simple_query"
    COMPLEX_ANALYSIS = "complex_analysis"
    CHINESE_CONTENT = "chinese_content"
    CODE_GENERATION = "code_generation"
    TEST_CASE_GENERATION = "test_case_generation"
    DOCUMENT_WRITING = "document_writing"
    GENERAL_TASK = "general_task"


class UserQuery:
    """用户查询对象"""
    def __init__(self, content: str, user_id: int, conversation_id: Optional[int] = None, 
                 context: Optional[Dict[str, Any]] = None):
        self.content = content
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.context = context or {}
        self.timestamp = datetime.utcnow()


class AIResponse:
    """AI响应对象"""
    def __init__(self, content: str, provider: AIProvider, model: str, 
                 tokens_used: int = 0, confidence_score: float = 0.0,
                 metadata: Optional[Dict[str, Any]] = None):
        self.content = content
        self.provider = provider
        self.model = model
        self.tokens_used = tokens_used
        self.confidence_score = confidence_score
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class StreamingChunk:
    """流式响应块对象"""
    def __init__(self, chunk_type: str, content: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.type = chunk_type  # 'content', 'metadata', 'error', 'complete'
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()


class BusinessContext:
    """业务上下文对象"""
    def __init__(self, project_data: Optional[Dict] = None, 
                 requirements_data: Optional[Dict] = None,
                 test_data: Optional[Dict] = None,
                 quality_data: Optional[Dict] = None):
        self.project_data = project_data
        self.requirements_data = requirements_data
        self.test_data = test_data
        self.quality_data = quality_data


class ContextAnalysis:
    """上下文分析结果"""
    def __init__(self):
        self.project_health: Optional[float] = None
        self.team_capacity: Optional[Dict] = None
        self.timeline_status: Optional[str] = None
        self.requirements_quality: Optional[float] = None
        self.requirements_coverage: Optional[float] = None
        self.requirements_traceability: Optional[float] = None
        self.test_coverage: Optional[float] = None
        self.test_effectiveness: Optional[float] = None
        self.test_automation_rate: Optional[float] = None
        self.defect_trends: Optional[Dict] = None
        self.quality_metrics: Optional[Dict] = None


class Suggestion:
    """建议对象"""
    def __init__(self, title: str, description: str, category: str, 
                 priority: str, action_items: List[str], 
                 expected_benefit: str, estimated_effort: str):
        self.title = title
        self.description = description
        self.category = category
        self.priority = priority
        self.action_items = action_items
        self.expected_benefit = expected_benefit
        self.estimated_effort = estimated_effort
        self.created_at = datetime.utcnow()


class ServiceContainer:
    """依赖注入容器"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register(self, service_name: str, service_factory, singleton: bool = True):
        """注册服务"""
        self._services[service_name] = {
            'factory': service_factory,
            'singleton': singleton
        }
    
    def get(self, service_name: str):
        """获取服务实例"""
        if service_name not in self._services:
            raise ValueError(f"Service {service_name} not registered")
        
        service_config = self._services[service_name]
        
        if service_config['singleton']:
            if service_name not in self._singletons:
                self._singletons[service_name] = service_config['factory']()
            return self._singletons[service_name]
        else:
            return service_config['factory']()


class AIAssistantService:
    """
    AI助手核心服务类
    
    作为AI助手模块的核心服务，提供以下主要功能：
    1. 智能查询处理 - 分析用户查询意图，选择最适合的AI服务
    2. 业务上下文分析 - 深度分析项目、需求、测试等业务数据
    3. 智能建议生成 - 基于上下文分析生成可行的改进建议
    4. 问题诊断分析 - 分析问题根因并提供解决方案
    5. 服务状态监控 - 监控AI服务健康状态和使用情况
    
    技术架构：
    - 采用依赖注入模式，支持服务解耦和测试
    - 异步编程模式，支持高并发处理
    - 多AI服务提供商智能路由
    - 可扩展的插件化架构
    """
    
    def __init__(self, db: AsyncSession = None):
        """
        初始化AI助手服务
        
        Args:
            db: 数据库会话
            container: 依赖注入容器
        """
        self.db = db
        self.container = get_container()
        
        # 权限服务集成
        self.permission_service = AIPermissionService(db) if db else None
        
        # 项目数据同步服务
        self.project_sync_service = None
        
        # 操作日志服务
        self.log_service = None
        
        # 多语言响应服务
        self.multilingual_service: Optional[MultilingualResponseService] = None
        
        # 注入的服务依赖（将在后续任务中实现具体服务）
        self.ai_router: Optional[IAIRouter] = None
        self.conversation_manager: Optional[IConversationManager] = None
        self.context_analyzer: Optional[IContextAnalyzer] = None
        self.suggestion_engine: Optional[ISuggestionEngine] = None
        
        # 配置日志
        self.logger = logging.getLogger(__name__)
        
        # 服务状态
        self.is_initialized = False
        self.service_version = "1.0.0"
        self.startup_time = datetime.utcnow()
        
        # 初始化AI服务配置
        self.ai_configs = {
            AIProvider.OPENAI: {
                "enabled": True,
                "api_key": _get_openai_setting("OPENAI_API_KEY", ""),
                "api_endpoint": (
                    _get_openai_setting("OPENAI_BASE_URL")
                    or _get_openai_setting("OPENAI_API_ENDPOINT")
                    or "https://api.openai.com/v1"
                ),
                "auth_scheme": (
                    _get_openai_setting("OPENAI_AUTH_SCHEME", "bearer")
                    or "bearer"
                ),
                "models": [
                    _get_openai_setting("OPENAI_MODEL")
                    or _get_openai_setting("OPENAI_DEFAULT_MODEL", "gpt-4")
                    or "gpt-4"
                ],
                "max_tokens": 4000,
                "temperature": 0.7,
                "cost_per_1k_tokens": 0.03,
                "accuracy_score": 0.95
            },
            AIProvider.ANTHROPIC: {
                "enabled": True,
                "api_key": getattr(settings, "CLAUDE_API_KEY", ""),
                "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                "max_tokens": 4000,
                "temperature": 0.7,
                "cost_per_1k_tokens": 0.015,
                "accuracy_score": 0.93
            },
            AIProvider.BAIDU_WENXIN: {
                "enabled": True,
                "api_key": getattr(settings, "BAIDU_API_KEY", ""),
                "models": ["wenxin-4.0", "wenxin-3.5"],
                "max_tokens": 2000,
                "temperature": 0.7,
                "cost_per_1k_tokens": 0.008,
                "accuracy_score": 0.88
            },
            AIProvider.ALIYUN_TONGYI: {
                "enabled": True,
                "api_key": getattr(settings, "ALIYUN_API_KEY", ""),
                "models": ["qwen-max", "qwen-plus"],
                "max_tokens": 2000,
                "temperature": 0.7,
                "cost_per_1k_tokens": 0.01,
                "accuracy_score": 0.85
            },
            AIProvider.GOOGLE_GEMINI: {
                "enabled": True,
                "api_key": getattr(settings, "GOOGLE_API_KEY", ""),
                "models": ["gemini-pro", "gemini-ultra"],
                "max_tokens": 4000,
                "temperature": 0.7,
                "cost_per_1k_tokens": 0.02,
                "accuracy_score": 0.90
            }
        }
        
        # 性能监控指标
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_response_time": 0.0,
            "total_tokens_used": 0,
            "total_cost": 0.0
        }
    
    async def initialize(self):
        """
        初始化服务
        
        执行服务启动时的初始化操作，包括：
        1. 注册依赖服务
        2. 验证AI服务配置
        3. 初始化监控指标
        """
        try:
            self.logger.info("Initializing AI Assistant Service...")
            
            # 注册依赖服务（实际实现将在后续任务中完成）
            await self._register_dependencies()
            
            # 验证AI服务配置
            await self._validate_ai_configs()
            
            # 初始化监控
            await self._initialize_monitoring()
            
            self.is_initialized = True
            self.logger.info("AI Assistant Service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Assistant Service: {str(e)}")
            raise
    
    async def _register_dependencies(self):
        """注册依赖服务"""
        # 初始化项目数据同步服务
        try:
            self.project_sync_service = await get_project_sync_service()
            self.logger.info("项目数据同步服务已注册")
        except Exception as e:
            self.logger.warning(f"项目数据同步服务注册失败: {e}")
        
        # 初始化操作日志服务
        try:
            self.log_service = await get_ai_operation_log_service(self.db)
            self.logger.info("AI操作日志服务已注册")
        except Exception as e:
            self.logger.warning(f"AI操作日志服务注册失败: {e}")
        
        # 初始化多语言响应服务
        try:
            self.multilingual_service = await get_multilingual_response_service(self.db)
            self.logger.info("多语言响应服务已注册")
        except Exception as e:
            self.logger.warning(f"多语言响应服务注册失败: {e}")
        
        # 这里将在后续任务中实现其他具体的服务注册
        self.logger.debug("Registering service dependencies...")
    
    async def _validate_ai_configs(self):
        """验证AI服务配置"""
        valid_providers = []
        for provider, config in self.ai_configs.items():
            if config.get("enabled") and config.get("api_key"):
                valid_providers.append(provider.value)
        
        self.logger.info(f"Valid AI providers: {valid_providers}")
        
        if not valid_providers:
            self.logger.warning("No valid AI providers configured")
    
    async def _initialize_monitoring(self):
        """初始化监控"""
        self.metrics["service_start_time"] = self.startup_time.isoformat()
        self.logger.debug("Monitoring initialized")
    
    @log_ai_model_call(
        operation_name="process_user_query",
        extract_user_id="user_id",
        extract_session_id="query.conversation_id",
        log_args=False,
        log_result=False
    )
    async def process_user_query(self, query: UserQuery, user_id: Optional[int] = None) -> AIResponse:
        """
        处理用户查询的核心方法
        
        这是AI助手服务的核心方法，负责：
        1. 分析查询意图和复杂度
        2. 智能选择最适合的AI服务提供商
        3. 构建上下文感知的提示词
        4. 调用AI服务并处理响应
        5. 记录性能指标和使用统计
        
        Args:
            query: 用户查询对象，包含查询内容、用户ID、上下文等信息
            
        Returns:
            AIResponse: AI响应对象，包含回答内容、使用的模型、Token消耗等信息
            
        Raises:
            ValueError: 当查询参数无效时
            RuntimeError: 当AI服务不可用时
        """
        start_time = datetime.utcnow()
        
        try:
            # 权限检查
            if user_id and self.permission_service:
                await self.permission_service.validate_ai_operation_permission(
                    user_id, "chat_basic"
                )
            
            # 更新查询计数
            self.metrics["total_queries"] += 1
            
            self.logger.info(f"Processing user query from user {query.user_id}, "
                           f"content length: {len(query.content)}")
            
            # 参数验证
            if not query.content or not query.content.strip():
                raise ValueError("查询内容不能为空")
            
            if len(query.content) > 10000:
                raise ValueError("查询内容过长，请控制在10000字符以内")
            
            # 1. 分析查询意图和上下文
            task_type = self._analyze_task_type(query)
            self.logger.debug(f"Detected task type: {task_type.value}")
            
            # 2. 选择最适合的AI服务
            selected_provider = await self._select_ai_provider(query, task_type, user_id)
            self.logger.debug(f"Selected AI provider: {selected_provider.value}")
            
            # 检查模型使用权限
            if user_id and self.permission_service:
                await self.permission_service.validate_ai_operation_permission(
                    user_id, "model_use", model_provider=selected_provider.value
                )
            
            # 3. 构建提示词和上下文
            enhanced_prompt = await self._build_enhanced_prompt(query, task_type)
            self.logger.debug(f"Enhanced prompt length: {len(enhanced_prompt)}")
            
            # 4. 调用AI服务获取回答
            ai_response = await self._call_ai_service(enhanced_prompt, selected_provider, query.context)
            
            # 5. 后处理和格式化结果
            processed_response = await self._post_process_response(ai_response, query)
            
            # 6. 多语言响应处理
            if self.multilingual_service:
                try:
                    # 检测用户输入语言并适配响应
                    multilingual_response = await self.multilingual_service.process_response(
                        content=processed_response.content,
                        user_id=user_id or query.user_id,
                        context_info={
                            "task_type": task_type.value,
                            "ai_provider": selected_provider.value,
                            "is_technical_content": task_type in [TaskType.CODE_GENERATION, TaskType.TEST_CASE_GENERATION],
                            "is_formal_document": task_type == TaskType.DOCUMENT_WRITING,
                            "conversation_id": query.conversation_id
                        }
                    )
                    
                    # 更新响应内容为多语言适配后的内容
                    processed_response.content = multilingual_response.adapted_content
                    processed_response.metadata.update({
                        "multilingual_adaptation": {
                            "target_language": multilingual_response.target_language.value,
                            "adaptation_applied": multilingual_response.adaptation_applied,
                            "quality_score": multilingual_response.quality_score,
                            "cultural_adaptations": multilingual_response.cultural_adaptations,
                            "language_enhancements": multilingual_response.language_enhancements,
                            "processing_time": multilingual_response.processing_time
                        }
                    })
                    
                    self.logger.debug(
                        f"Multilingual adaptation applied: {multilingual_response.target_language.value}, "
                        f"quality: {multilingual_response.quality_score:.2f}"
                    )
                    
                except Exception as e:
                    self.logger.warning(f"Multilingual processing failed, using original response: {e}")
                    # 如果多语言处理失败，继续使用原始响应
            
            # 7. 更新性能指标
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await self._update_metrics(processing_time, ai_response.tokens_used, True)
            
            # 8. 记录AI模型调用日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id or query.user_id,
                    ai_provider=selected_provider.value,
                    ai_model=self.ai_configs[selected_provider]["models"][0],
                    tokens_used=ai_response.tokens_used,
                    processing_time=processing_time,
                    result=AIOperationResult.SUCCESS,
                    cost_amount=self._calculate_cost(ai_response.tokens_used, selected_provider),
                    confidence_score=ai_response.confidence_score,
                    session_id=query.conversation_id,
                    business_context={
                        "task_type": task_type.value,
                        "query_length": len(query.content),
                        "response_length": len(processed_response.content)
                    }
                )
            
            self.logger.info(f"Successfully processed query for user {query.user_id}, "
                           f"processing time: {processing_time:.2f}s, "
                           f"tokens used: {ai_response.tokens_used}")
            
            return processed_response
            
        except ValueError as e:
            self.logger.warning(f"Invalid query parameters: {str(e)}")
            self.metrics["failed_queries"] += 1
            
            return AIResponse(
                content=f"请求参数错误：{str(e)}",
                provider=AIProvider.OPENAI,
                model="error",
                confidence_score=0.0,
                metadata={"error": str(e), "error_type": "validation"}
            )
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await self._update_metrics(processing_time, 0, False)
            
            # 记录错误日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id or query.user_id,
                    ai_provider=selected_provider.value if 'selected_provider' in locals() else "unknown",
                    ai_model="error",
                    tokens_used=0,
                    processing_time=processing_time,
                    result=AIOperationResult.FAILURE,
                    error_details=str(e),
                    session_id=query.conversation_id,
                    business_context={
                        "task_type": task_type.value if 'task_type' in locals() else "unknown",
                        "query_length": len(query.content),
                        "error_type": type(e).__name__
                    }
                )
            
            self.logger.error(f"Error processing user query: {str(e)}", exc_info=True)
            self.metrics["failed_queries"] += 1
            
            # 返回用户友好的错误响应
            return AIResponse(
                content="抱歉，AI助手暂时无法处理您的请求，请稍后重试。如果问题持续存在，请联系技术支持。",
                provider=AIProvider.OPENAI,
                model="error",
                confidence_score=0.0,
                metadata={
                    "error": str(e),
                    "error_type": "system",
                    "processing_time": processing_time,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    @log_suggestion_activity(
        activity_type="generate",
        operation_name="generate_suggestions",
        extract_user_id="user_id",
        log_args=False,
        log_result=False
    )
    async def generate_suggestions(self, context: BusinessContext, user_id: Optional[int] = None) -> List[Suggestion]:
        """
        生成智能建议
        
        基于业务上下文深度分析，生成可行的改进建议。分析维度包括：
        1. 项目健康度和团队能力
        2. 需求质量和覆盖度
        3. 测试覆盖率和自动化程度
        4. 质量指标和缺陷趋势
        
        Args:
            context: 业务上下文对象，包含项目、需求、测试、质量等数据
            
        Returns:
            List[Suggestion]: 按优先级排序的建议列表
            
        Raises:
            ValueError: 当上下文数据无效时
        """
        start_time = datetime.utcnow()
        
        try:
            # 权限检查
            if user_id and self.permission_service:
                await self.permission_service.validate_ai_operation_permission(
                    user_id, "suggestion_generate"
                )
            
            self.logger.info("Generating intelligent suggestions")
            
            # 验证输入参数
            if not context:
                raise ValueError("业务上下文不能为空")
            
            # 1. 分析业务上下文
            self.logger.debug("Analyzing business context...")
            context_analysis = await self._analyze_business_context(context)
            
            # 2. 识别可优化点
            self.logger.debug("Identifying optimization points...")
            optimization_points = await self._identify_optimization_points(context_analysis)
            
            if not optimization_points:
                self.logger.info("No optimization points identified")
                return []
            
            # 3. 生成改进建议
            self.logger.debug(f"Generating suggestions for {len(optimization_points)} optimization points")
            suggestions = []
            
            for point in optimization_points:
                try:
                    suggestion = await self._generate_improvement_suggestion(point, context)
                    if suggestion:
                        suggestions.append(suggestion)
                        self.logger.debug(f"Generated suggestion for {point}: {suggestion.title}")
                except Exception as e:
                    self.logger.warning(f"Failed to generate suggestion for {point}: {str(e)}")
                    continue
            
            # 4. 评估建议可行性和优先级
            self.logger.debug("Evaluating suggestion feasibility...")
            evaluated_suggestions = await self._evaluate_suggestion_feasibility(suggestions, context)
            
            # 5. 记录生成统计
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(f"Generated {len(evaluated_suggestions)} suggestions in {generation_time:.2f}s")
            
            # 记录建议生成指标
            if not hasattr(self.metrics, "suggestions_generated"):
                self.metrics["suggestions_generated"] = 0
            self.metrics["suggestions_generated"] += len(evaluated_suggestions)
            
            # 记录建议生成日志
            if self.log_service:
                await self.log_service.log_suggestion_activity(
                    user_id=user_id,
                    suggestion_id="batch_generation",
                    activity_type="generate",
                    result=AIOperationResult.SUCCESS,
                    processing_time=generation_time,
                    business_context={
                        "suggestions_count": len(evaluated_suggestions),
                        "optimization_points": len(optimization_points),
                        "context_type": type(context).__name__
                    },
                    metadata={
                        "generation_time": generation_time,
                        "suggestions_generated": len(evaluated_suggestions)
                    }
                )
            
            return evaluated_suggestions
            
        except ValueError as e:
            self.logger.warning(f"Invalid context for suggestion generation: {str(e)}")
            return []
            
        except Exception as e:
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"Error generating suggestions after {generation_time:.2f}s: {str(e)}", 
                            exc_info=True)
            return []
    
    async def stream_user_query(self, query: UserQuery, user_id: Optional[int] = None):
        """
        流式处理用户查询
        
        提供实时流式响应，逐步返回AI生成的内容。
        
        Args:
            query: 用户查询对象
            
        Yields:
            StreamingChunk: 流式响应块，包含内容增量、元数据等
        """
        start_time = datetime.utcnow()
        
        try:
            # 权限检查
            if user_id and self.permission_service:
                try:
                    await self.permission_service.validate_ai_operation_permission(
                        user_id, "chat_basic"
                    )
                except PermissionError as e:
                    yield StreamingChunk("error", "", {"error": str(e)})
                    return
            
            self.logger.info(f"Starting streaming query for user {query.user_id}")
            
            # 参数验证
            if not query.content or not query.content.strip():
                yield StreamingChunk("error", "", {"error": "查询内容不能为空"})
                return
            
            # 1. 分析查询意图
            task_type = self._analyze_task_type(query)
            
            # 2. 选择AI服务
            selected_provider = await self._select_ai_provider(query, task_type, user_id)
            
            # 检查模型使用权限
            if user_id and self.permission_service:
                try:
                    await self.permission_service.validate_ai_operation_permission(
                        user_id, "model_use", model_provider=selected_provider.value
                    )
                except PermissionError as e:
                    yield StreamingChunk("error", "", {"error": str(e)})
                    return
            
            # 发送开始信号
            yield StreamingChunk("metadata", "", {
                "provider": selected_provider.value,
                "model": self.ai_configs[selected_provider]["models"][0],
                "task_type": task_type.value
            })
            
            # 3. 构建提示词
            enhanced_prompt = await self._build_enhanced_prompt(query, task_type)
            
            # 4. 流式调用AI服务
            try:
                # 模拟流式AI响应（实际实现中会调用真实的AI API）
                full_response = await self._call_ai_service(enhanced_prompt, selected_provider)
                
                # 将完整响应分块流式返回
                words = full_response.content.split()
                current_content = ""
                
                for i, word in enumerate(words):
                    current_content += word + " "
                    
                    # 每几个词发送一次增量内容
                    if i % 3 == 0 or i == len(words) - 1:
                        yield StreamingChunk("content", word + " ", {
                            "total_content": current_content.strip(),
                            "progress": (i + 1) / len(words)
                        })
                        
                        # 添加延迟模拟真实流式响应
                        await asyncio.sleep(0.1)
                
                # 发送完成信号
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                yield StreamingChunk("complete", "", {
                    "provider": full_response.provider.value,
                    "model": full_response.model,
                    "tokens_used": full_response.tokens_used,
                    "confidence_score": full_response.confidence_score,
                    "processing_time": processing_time
                })
                
                # 更新指标
                await self._update_metrics(processing_time, full_response.tokens_used, True)
                
            except Exception as ai_error:
                self.logger.error(f"AI service error during streaming: {str(ai_error)}")
                yield StreamingChunk("error", "", {
                    "error": str(ai_error),
                    "error_type": "ai_service"
                })
                
        except Exception as e:
            self.logger.error(f"Error in streaming query: {str(e)}")
            yield StreamingChunk("error", "", {
                "error": str(e),
                "error_type": "system"
            })
    
    async def _update_metrics(self, processing_time: float, tokens_used: int, success: bool):
        """
        更新性能指标
        
        Args:
            processing_time: 处理时间（秒）
            tokens_used: 使用的Token数
            success: 是否成功
        """
        try:
            if success:
                self.metrics["successful_queries"] += 1
            
            # 更新平均响应时间（移动平均）
            total_queries = self.metrics["total_queries"]
            if total_queries > 1:
                current_avg = self.metrics["avg_response_time"]
                self.metrics["avg_response_time"] = (
                    (current_avg * (total_queries - 1) + processing_time) / total_queries
                )
            else:
                self.metrics["avg_response_time"] = processing_time
            
            # 更新Token使用统计
            self.metrics["total_tokens_used"] += tokens_used
            
            # 估算成本（基于平均成本）
            avg_cost_per_1k_tokens = 0.02  # 平均成本
            cost = (tokens_used / 1000) * avg_cost_per_1k_tokens
            self.metrics["total_cost"] += cost
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {str(e)}")
    
    def _calculate_cost(self, tokens_used: int, provider: AIProvider) -> float:
        """
        计算AI服务调用成本
        
        Args:
            tokens_used: 使用的Token数
            provider: AI服务提供商
            
        Returns:
            float: 成本金额
        """
        try:
            config = self.ai_configs.get(provider, {})
            cost_per_1k_tokens = config.get("cost_per_1k_tokens", 0.02)
            return (tokens_used / 1000) * cost_per_1k_tokens
        except Exception as e:
            self.logger.warning(f"计算成本失败: {e}")
            return 0.0
    
    def _analyze_task_type(self, query: UserQuery) -> TaskType:
        """
        分析任务类型
        
        Args:
            query: 用户查询对象
            
        Returns:
            TaskType: 任务类型
        """
        content = query.content.lower()
        content_length = len(query.content)
        
        # 首先检查长度，长内容优先判断为复杂分析
        if content_length > 2000:
            return TaskType.COMPLEX_ANALYSIS
        
        # 然后检查关键词，关键词优先级高于语言判断
        elif any(keyword in content for keyword in ["测试", "用例", "test", "case"]):
            return TaskType.TEST_CASE_GENERATION
        elif any(keyword in content for keyword in ["代码", "编程", "code", "program", "函数", "python", "java", "javascript"]):
            return TaskType.CODE_GENERATION
        elif any(keyword in content for keyword in ["文档", "报告", "document", "report"]):
            return TaskType.DOCUMENT_WRITING
        elif any(keyword in content for keyword in ["需求", "分析", "requirement", "analysis"]):
            return TaskType.COMPLEX_ANALYSIS
        
        # 检查是否明确要求中文回答
        elif "中文" in content or "用中文" in content:
            return TaskType.CHINESE_CONTENT
        
        # 简短内容判断为简单查询
        elif content_length < 100:
            return TaskType.SIMPLE_QUERY
        
        # 中等长度内容，如果中文字符占比很高，判断为中文内容
        elif len([c for c in content if '\u4e00' <= c <= '\u9fff']) > len(content) * 0.7:
            return TaskType.CHINESE_CONTENT
        
        else:
            return TaskType.GENERAL_TASK
    
    async def _select_ai_provider(self, query: UserQuery, task_type: TaskType, user_id: Optional[int] = None) -> AIProvider:
        """
        选择最适合的AI服务提供商
        
        Args:
            query: 用户查询对象
            task_type: 任务类型
            
        Returns:
            AIProvider: 选择的AI服务提供商
        """
        # 基于任务类型选择最适合的AI服务
        provider_preferences = {
            TaskType.COMPLEX_ANALYSIS: [AIProvider.OPENAI, AIProvider.ANTHROPIC],
            TaskType.CODE_GENERATION: [AIProvider.OPENAI, AIProvider.ANTHROPIC],
            TaskType.TEST_CASE_GENERATION: [AIProvider.OPENAI, AIProvider.ANTHROPIC],
            TaskType.DOCUMENT_WRITING: [AIProvider.ANTHROPIC, AIProvider.BAIDU_WENXIN],
            TaskType.CHINESE_CONTENT: [AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI],
            TaskType.SIMPLE_QUERY: [AIProvider.OPENAI, AIProvider.BAIDU_WENXIN],
            TaskType.GENERAL_TASK: [AIProvider.OPENAI, AIProvider.ANTHROPIC]
        }
        
        preferred_providers = provider_preferences.get(task_type, [AIProvider.OPENAI])
        
        # 选择第一个可用且有权限的提供商
        for provider in preferred_providers:
            if await self._is_provider_available(provider):
                # 检查用户是否有使用该模型的权限
                if user_id and self.permission_service:
                    has_permission, _ = await self.permission_service.check_ai_model_permission(
                        user_id, provider.value
                    )
                    if has_permission:
                        return provider
                else:
                    return provider
        
        # 如果首选提供商都不可用或无权限，尝试找一个有权限的默认提供商
        if user_id and self.permission_service:
            for provider in [AIProvider.OPENAI, AIProvider.BAIDU_WENXIN, AIProvider.ANTHROPIC]:
                if await self._is_provider_available(provider):
                    has_permission, _ = await self.permission_service.check_ai_model_permission(
                        user_id, provider.value
                    )
                    if has_permission:
                        return provider
        
        # 如果都没有权限，返回默认提供商（后续权限检查会拦截）
        return AIProvider.OPENAI
    
    async def _is_provider_available(self, provider: AIProvider) -> bool:
        """
        检查AI服务提供商是否可用
        
        Args:
            provider: AI服务提供商
            
        Returns:
            bool: 是否可用
        """
        if provider != AIProvider.OPENAI:
            return False

        config = self.ai_configs.get(provider)
        if not config:
            return False
        
        # 检查是否启用
        if not config.get("enabled", False):
            return False
        
        # 检查API密钥是否配置
        if not config.get("api_key"):
            return False
        
        # TODO: 在后续任务中添加实际的健康检查
        return True
    
    async def _build_enhanced_prompt(self, query: UserQuery, task_type: TaskType) -> str:
        """
        构建增强的提示词
        
        Args:
            query: 用户查询对象
            task_type: 任务类型
            
        Returns:
            str: 增强的提示词
        """
        base_prompt = query.content
        
        # 根据任务类型添加上下文信息
        context_prompts = {
            TaskType.TEST_CASE_GENERATION: (
                "请作为资深测试专家，基于以下需求生成可落地的测试设计。"
                "请覆盖正常路径、边界值、异常路径、数据准备、前置条件、预期结果和优先级。\n\n"
            ),
            TaskType.CODE_GENERATION: (
                "请作为资深开发工程师回答。若涉及代码，请给出关键实现、错误处理、测试建议和集成注意事项。\n\n"
            ),
            TaskType.DOCUMENT_WRITING: (
                "请作为测试管理文档专家，输出结构清晰、可直接用于团队协作的文档内容。\n\n"
            ),
            TaskType.COMPLEX_ANALYSIS: (
                "请进行深入分析，先给结论，再给依据、风险、建议动作和验证方法。\n\n"
            ),
            TaskType.CHINESE_CONTENT: "请用简体中文回答，表达准确、具体、可执行。\n\n",
            TaskType.GENERAL_TASK: "请结合 AI 测试管理系统的业务语境，给出具体、可执行的回答。\n\n",
            TaskType.SIMPLE_QUERY: "请直接回答用户问题，必要时补充测试管理相关建议。\n\n",
        }
        
        context_prefix = context_prompts.get(task_type, "")
        enhanced_prompt = context_prefix + base_prompt
        
        # 添加用户上下文信息
        if query.context:
            context_parts = []
            conversation_history = query.context.get("conversation_history")
            if conversation_history:
                formatted_history = self._format_conversation_history(conversation_history)
                if formatted_history:
                    context_parts.append(formatted_history)

            if query.context.get("is_continuation_request"):
                latest_assistant_message = str(query.context.get("latest_assistant_message") or "").strip()
                continuation_part = (
                    "当前请求是继续上一轮未完成回答。必须承接最近一条 AI 回复的主题、结构、编号和语气，"
                    "从中断位置继续输出，不要重新分析新主题，不要重复已经完整输出的内容。"
                )
                if latest_assistant_message:
                    continuation_part += (
                        "\n\n最近一条 AI 回复原文（用于判断继续位置）：\n"
                        f"{self._truncate_context_text(latest_assistant_message, 5000)}"
                    )
                context_parts.append(continuation_part)

            normal_context_lines = []
            skip_keys = {
                "conversation_history",
                "is_continuation_request",
                "latest_assistant_message",
                "continuation_instruction",
                "attachments",
            }
            for key, value in query.context.items():
                if key in skip_keys or value in (None, "", [], {}):
                    continue
                normal_context_lines.append(f"- {key}: {self._format_context_value(value)}")

            if normal_context_lines:
                context_parts.append("业务上下文信息：\n" + "\n".join(normal_context_lines))

            if context_parts:
                enhanced_prompt += "\n\n" + "\n\n".join(context_parts)
        
        return enhanced_prompt

    def _format_conversation_history(self, history: Any) -> str:
        """Format recent chat history into a stable prompt section."""
        if not isinstance(history, list):
            return ""

        role_labels = {
            "user": "用户",
            "assistant": "AI助手",
            "system": "系统",
            "USER": "用户",
            "ASSISTANT": "AI助手",
            "SYSTEM": "系统",
        }
        lines = ["最近对话上下文（按时间顺序）："]
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = role_labels.get(str(item.get("role") or ""), str(item.get("role") or "消息"))
            content = self._truncate_context_text(str(item.get("content") or "").strip(), 3000)
            if not content:
                continue
            lines.append(f"{role}：\n{content}")

        return "\n\n".join(lines) if len(lines) > 1 else ""

    def _truncate_context_text(self, value: str, limit: int) -> str:
        text = value.strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit].rstrip()}\n[上下文过长，已截断]"

    def _format_context_value(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            try:
                return self._truncate_context_text(json.dumps(value, ensure_ascii=False), 2000)
            except TypeError:
                return self._truncate_context_text(str(value), 2000)
        return self._truncate_context_text(str(value), 2000)
    
    async def _call_ai_service(self, prompt: str, provider: AIProvider, context: Optional[Dict[str, Any]] = None) -> AIResponse:
        """
        调用AI服务
        
        Args:
            prompt: 提示词
            provider: AI服务提供商
            
        Returns:
            AIResponse: AI响应
        """
        if provider != AIProvider.OPENAI:
            raise RuntimeError(f"{provider.value} 真实调用尚未实现，请配置 OpenAI 兼容服务")

        return await self._call_openai_compatible_service(prompt, provider, context)

    async def _call_openai_compatible_service(
        self,
        prompt: str,
        provider: AIProvider,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIResponse:
        """调用 OpenAI 兼容的 Chat Completions 接口。"""
        config = self.ai_configs.get(provider, {})
        api_key = config.get("api_key")
        if not api_key:
            raise RuntimeError("OpenAI API key 未配置")

        endpoint = (config.get("api_endpoint") or "https://api.openai.com/v1").rstrip("/")
        model = (config.get("models") or ["gpt-4"])[0]
        timeout_seconds = float(getattr(settings, "OPENAI_TIMEOUT", 90.0) or 90.0)
        max_tokens = int(os.getenv("AI_MAX_TOKENS") or getattr(settings, "OPENAI_MAX_TOKENS", 4000) or 4000)
        temperature = float(os.getenv("AI_TEMPERATURE") or getattr(settings, "OPENAI_TEMPERATURE", 0.7) or 0.7)

        user_content: Any = prompt
        image_attachments = [
            attachment
            for attachment in ((context or {}).get("attachments") or [])
            if isinstance(attachment, dict) and attachment.get("image_data_url")
        ]
        if image_attachments:
            user_content = [{"type": "text", "text": prompt}]
            for attachment in image_attachments[:4]:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": attachment["image_data_url"]},
                })

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 AI 测试管理系统中的真实 AI 助手，不得声称自己是模拟响应。"
                        "你擅长需求分析、测试设计、缺陷定位、项目风险识别和测试管理改进。"
                        "回答必须具体、可执行，缺少上下文时说明假设和需要补充的信息。"
                    ),
                },
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        auth_scheme = str(config.get("auth_scheme") or "bearer").strip().lower()
        headers = {"Content-Type": "application/json"}
        if auth_scheme == "raw":
            headers["Authorization"] = api_key
        elif auth_scheme == "x-api-key":
            headers["x-api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"

        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{endpoint}/chat/completions", headers=headers, json=payload) as response:
                response_text = await response.text()
                if response.status >= 400:
                    detail = response_text[:500]
                    try:
                        error_data = json.loads(response_text)
                        detail = (
                            error_data.get("error", {}).get("message")
                            or error_data.get("message")
                            or detail
                        )
                    except json.JSONDecodeError:
                        pass

                    if response.status == 401:
                        raise RuntimeError(
                            "OpenAI 兼容服务鉴权失败：API Key 无效或已过期，请更新后端 OPENAI_API_KEY 后重启服务。"
                        )
                    if response.status == 403:
                        raise RuntimeError(
                            f"OpenAI 兼容服务拒绝访问：请检查 API Key 权限、账户余额或模型权限。详情：{detail}"
                        )
                    raise RuntimeError(f"OpenAI 兼容服务调用失败: HTTP {response.status} {response_text[:500]}")

                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"OpenAI 兼容服务返回非 JSON 响应: {response_text[:200]}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenAI 兼容服务未返回 choices")

        message = choices[0].get("message") or {}
        response_content = (message.get("content") or "").strip()
        if not response_content:
            raise RuntimeError("OpenAI 兼容服务返回空内容")

        usage = data.get("usage") or {}
        tokens_used = usage.get("total_tokens")
        if tokens_used is None:
            tokens_used = max(1, (len(prompt) + len(response_content)) // 4)

        return AIResponse(
            content=response_content,
            provider=provider,
            model=data.get("model") or model,
            tokens_used=int(tokens_used),
            confidence_score=0.9,
            metadata={
                "simulated": False,
                "api_endpoint": endpoint,
                "finish_reason": choices[0].get("finish_reason"),
                "image_attachments": len(image_attachments),
            },
        )
    
    async def _post_process_response(self, ai_response: AIResponse, query: UserQuery) -> AIResponse:
        """
        后处理AI响应
        
        Args:
            ai_response: 原始AI响应
            query: 用户查询
            
        Returns:
            AIResponse: 处理后的AI响应
        """
        # 添加查询相关的元数据
        ai_response.metadata.update({
            "user_id": query.user_id,
            "conversation_id": query.conversation_id,
            "query_timestamp": query.timestamp.isoformat(),
            "processing_timestamp": datetime.utcnow().isoformat()
        })
        
        # TODO: 在后续任务中添加内容安全检查、格式化等处理
        
        return ai_response
    
    async def _analyze_business_context(self, context: BusinessContext) -> ContextAnalysis:
        """
        分析业务上下文
        
        Args:
            context: 业务上下文
            
        Returns:
            ContextAnalysis: 上下文分析结果
        """
        analysis = ContextAnalysis()
        
        try:
            # 项目基本信息分析
            if context.project_data:
                analysis.project_health = await self._assess_project_health(context.project_data)
                analysis.team_capacity = await self._analyze_team_capacity(context.project_data)
                analysis.timeline_status = await self._evaluate_timeline_status(context.project_data)
            
            # 需求分析
            if context.requirements_data:
                analysis.requirements_quality = await self._analyze_requirements_quality(context.requirements_data)
                analysis.requirements_coverage = await self._assess_requirements_coverage(context.requirements_data)
                analysis.requirements_traceability = await self._check_requirements_traceability(context.requirements_data)
            
            # 测试分析
            if context.test_data:
                analysis.test_coverage = await self._calculate_test_coverage(context.test_data)
                analysis.test_effectiveness = await self._evaluate_test_effectiveness(context.test_data)
                analysis.test_automation_rate = await self._assess_automation_rate(context.test_data)
            
            # 质量分析
            if context.quality_data:
                analysis.defect_trends = await self._analyze_defect_trends(context.quality_data)
                analysis.quality_metrics = await self._evaluate_quality_metrics(context.quality_data)
        
        except Exception as e:
            self.logger.error(f"Error analyzing business context: {str(e)}")
        
        return analysis
    
    async def _assess_project_health(self, project_data: Dict) -> float:
        """评估项目健康度"""
        # 模拟项目健康度评估
        return 0.75  # 75%的健康度
    
    async def _analyze_team_capacity(self, project_data: Dict) -> Dict:
        """分析团队能力"""
        return {
            "total_members": project_data.get("team_size", 5),
            "available_capacity": 0.8,
            "skill_distribution": {"frontend": 0.3, "backend": 0.4, "testing": 0.3}
        }
    
    async def _evaluate_timeline_status(self, project_data: Dict) -> str:
        """评估时间线状态"""
        return "on_track"  # 按计划进行
    
    async def _analyze_requirements_quality(self, requirements_data: Dict) -> float:
        """分析需求质量"""
        # 模拟需求质量分析
        return 0.68  # 68%的质量分数
    
    async def _assess_requirements_coverage(self, requirements_data: Dict) -> float:
        """评估需求覆盖度"""
        return 0.82  # 82%的覆盖度
    
    async def _check_requirements_traceability(self, requirements_data: Dict) -> float:
        """检查需求可追溯性"""
        return 0.75  # 75%的可追溯性
    
    async def _calculate_test_coverage(self, test_data: Dict) -> float:
        """计算测试覆盖率"""
        return 0.65  # 65%的测试覆盖率
    
    async def _evaluate_test_effectiveness(self, test_data: Dict) -> float:
        """评估测试有效性"""
        return 0.72  # 72%的测试有效性
    
    async def _assess_automation_rate(self, test_data: Dict) -> float:
        """评估自动化率"""
        return 0.45  # 45%的自动化率
    
    async def _analyze_defect_trends(self, quality_data: Dict) -> Dict:
        """分析缺陷趋势"""
        return {
            "total_defects": quality_data.get("total_defects", 0),
            "open_defects": quality_data.get("open_defects", 0),
            "trend": "decreasing"
        }
    
    async def _evaluate_quality_metrics(self, quality_data: Dict) -> Dict:
        """评估质量指标"""
        return {
            "code_quality_score": 0.78,
            "maintainability_index": 0.82,
            "technical_debt_ratio": 0.15
        }
    
    async def _identify_optimization_points(self, analysis: ContextAnalysis) -> List[str]:
        """识别可优化点"""
        optimization_points = []
        
        # 基于分析结果识别优化点
        if analysis.requirements_quality and analysis.requirements_quality < 0.7:
            optimization_points.append("requirements_quality")
        
        if analysis.test_coverage and analysis.test_coverage < 0.8:
            optimization_points.append("test_coverage")
        
        if analysis.test_automation_rate and analysis.test_automation_rate < 0.6:
            optimization_points.append("test_automation")
        
        if analysis.project_health and analysis.project_health < 0.8:
            optimization_points.append("project_health")
        
        return optimization_points
    
    async def _generate_improvement_suggestion(self, optimization_point: str, context: BusinessContext) -> Optional[Suggestion]:
        """生成改进建议"""
        suggestions_map = {
            "requirements_quality": Suggestion(
                title="提升需求质量",
                description="当前需求质量较低，建议完善需求描述和验收标准",
                category="QUALITY_IMPROVEMENT",
                priority="HIGH",
                action_items=[
                    "组织需求评审会议",
                    "完善需求文档模板",
                    "建立需求质量检查清单",
                    "培训团队需求编写技能"
                ],
                expected_benefit="提高开发效率，减少返工",
                estimated_effort="2-3天"
            ),
            "test_coverage": Suggestion(
                title="提高测试覆盖率",
                description="当前测试覆盖率不足，建议增加测试用例",
                category="TEST_IMPROVEMENT",
                priority="MEDIUM",
                action_items=[
                    "分析未覆盖的代码路径",
                    "编写缺失的测试用例",
                    "建立测试覆盖率监控",
                    "设定测试覆盖率目标"
                ],
                expected_benefit="提高代码质量，减少生产缺陷",
                estimated_effort="3-5天"
            ),
            "test_automation": Suggestion(
                title="提升测试自动化率",
                description="当前自动化测试比例较低，建议增加自动化测试",
                category="AUTOMATION_IMPROVEMENT",
                priority="MEDIUM",
                action_items=[
                    "识别适合自动化的测试场景",
                    "选择合适的自动化测试工具",
                    "编写自动化测试脚本",
                    "建立持续集成流水线"
                ],
                expected_benefit="提高测试效率，缩短发布周期",
                estimated_effort="1-2周"
            ),
            "project_health": Suggestion(
                title="改善项目健康状况",
                description="项目健康度需要改善，建议优化项目管理流程",
                category="PROJECT_MANAGEMENT",
                priority="HIGH",
                action_items=[
                    "分析项目风险点",
                    "优化团队协作流程",
                    "加强项目监控",
                    "定期举行项目回顾会议"
                ],
                expected_benefit="提高项目成功率，确保按时交付",
                estimated_effort="持续改进"
            )
        }
        
        return suggestions_map.get(optimization_point)
    
    async def _evaluate_suggestion_feasibility(self, suggestions: List[Suggestion], context: BusinessContext) -> List[Suggestion]:
        """评估建议可行性"""
        # 按优先级排序
        priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        
        return sorted(suggestions, key=lambda s: priority_order.get(s.priority, 0), reverse=True)
    
    async def analyze_problem(self, problem_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        问题分析方法
        
        提供全面的问题诊断和解决方案推荐，包括：
        1. 问题理解和分类
        2. 根本原因分析
        3. 解决方案生成
        4. 最佳实践推荐
        5. 风险评估和预防措施
        
        Args:
            problem_description: 问题描述，应包含具体的问题现象和影响
            context: 问题上下文，可包含环境信息、相关系统、时间等
            
        Returns:
            Dict[str, Any]: 包含完整问题分析结果的字典
            
        Raises:
            ValueError: 当问题描述为空或过短时
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Analyzing problem: {problem_description[:100]}...")
            
            # 参数验证
            if not problem_description or len(problem_description.strip()) < 10:
                raise ValueError("问题描述过于简短，请提供更详细的问题信息")
            
            # 1. 理解问题描述和上下文
            self.logger.debug("Understanding problem context...")
            problem_understanding = await self._understand_problem_context(problem_description, context)
            
            # 2. 分析可能的根本原因
            self.logger.debug("Analyzing root causes...")
            root_causes = await self._analyze_root_causes(problem_description, problem_understanding)
            
            # 3. 生成针对性解决方案
            self.logger.debug("Generating solutions...")
            solutions = await self._generate_solutions(problem_description, root_causes)
            
            # 4. 推荐最佳实践和预防措施
            self.logger.debug("Recommending best practices...")
            best_practices = await self._recommend_best_practices(problem_description, solutions)
            
            # 5. 评估分析置信度
            confidence_score = await self._calculate_analysis_confidence(
                problem_description, root_causes, solutions
            )
            
            # 6. 生成风险评估
            risk_assessment = await self._assess_problem_risks(problem_understanding, root_causes)
            
            analysis_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                "problem_understanding": problem_understanding,
                "root_causes": root_causes,
                "solutions": solutions,
                "best_practices": best_practices,
                "risk_assessment": risk_assessment,
                "confidence_score": confidence_score,
                "analysis_duration": analysis_time,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "analyzer_version": self.service_version
            }
            
            self.logger.info(f"Problem analysis completed in {analysis_time:.2f}s, "
                           f"confidence: {confidence_score:.2f}")
            
            return result
            
        except ValueError as e:
            self.logger.warning(f"Invalid problem description: {str(e)}")
            return {
                "error": str(e),
                "error_type": "validation",
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            analysis_time = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"Error analyzing problem after {analysis_time:.2f}s: {str(e)}", 
                            exc_info=True)
            return {
                "error": "问题分析过程中出现系统错误，请稍后重试",
                "error_type": "system",
                "analysis_duration": analysis_time,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    async def _calculate_analysis_confidence(self, problem_description: str, 
                                           root_causes: List[str], solutions: List[Dict]) -> float:
        """
        计算分析置信度
        
        Args:
            problem_description: 问题描述
            root_causes: 根本原因列表
            solutions: 解决方案列表
            
        Returns:
            float: 置信度分数 (0.0-1.0)
        """
        try:
            confidence_factors = []
            
            # 问题描述详细程度
            desc_length = len(problem_description)
            if desc_length > 200:
                confidence_factors.append(0.9)
            elif desc_length > 100:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)
            
            # 根本原因数量合理性
            if 2 <= len(root_causes) <= 5:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.6)
            
            # 解决方案数量
            if 1 <= len(solutions) <= 4:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.6)
            
            # 计算平均置信度
            return sum(confidence_factors) / len(confidence_factors)
            
        except Exception as e:
            self.logger.warning(f"Error calculating confidence: {str(e)}")
            return 0.5
    
    async def _assess_problem_risks(self, understanding: Dict, root_causes: List[str]) -> Dict[str, Any]:
        """
        评估问题风险
        
        Args:
            understanding: 问题理解结果
            root_causes: 根本原因列表
            
        Returns:
            Dict[str, Any]: 风险评估结果
        """
        try:
            severity = understanding.get("severity", "medium")
            problem_type = understanding.get("problem_type", "general")
            
            # 基于问题类型和严重程度评估风险
            risk_level = "low"
            if severity == "high" or problem_type == "technical":
                risk_level = "high"
            elif severity == "medium":
                risk_level = "medium"
            
            # 影响范围评估
            impact_scope = "limited"
            if any("系统" in cause or "服务" in cause for cause in root_causes):
                impact_scope = "system-wide"
            elif any("用户" in cause or "数据" in cause for cause in root_causes):
                impact_scope = "user-facing"
            
            return {
                "risk_level": risk_level,
                "impact_scope": impact_scope,
                "urgency": severity,
                "recommended_action": "immediate" if risk_level == "high" else "scheduled"
            }
            
        except Exception as e:
            self.logger.warning(f"Error assessing risks: {str(e)}")
            return {"risk_level": "unknown", "impact_scope": "unknown"}
    
    async def _understand_problem_context(self, problem_description: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """理解问题上下文"""
        return {
            "problem_type": "technical" if any(keyword in problem_description.lower() 
                                            for keyword in ["bug", "error", "exception", "fail"]) else "process",
            "severity": "high" if any(keyword in problem_description.lower() 
                                    for keyword in ["critical", "urgent", "blocking"]) else "medium",
            "domain": "testing" if "test" in problem_description.lower() else "general"
        }
    
    async def _analyze_root_causes(self, problem_description: str, understanding: Dict) -> List[str]:
        """分析根本原因"""
        potential_causes = []
        
        if understanding["problem_type"] == "technical":
            potential_causes.extend([
                "代码逻辑错误",
                "环境配置问题",
                "依赖版本冲突",
                "数据格式不匹配"
            ])
        else:
            potential_causes.extend([
                "流程不清晰",
                "沟通不充分",
                "资源不足",
                "培训缺失"
            ])
        
        return potential_causes[:3]  # 返回前3个最可能的原因
    
    async def _generate_solutions(self, problem_description: str, root_causes: List[str]) -> List[Dict[str, Any]]:
        """生成解决方案"""
        solutions = []
        
        for cause in root_causes:
            if "代码" in cause:
                solutions.append({
                    "title": "代码审查和修复",
                    "description": "进行详细的代码审查，识别和修复逻辑错误",
                    "steps": ["代码静态分析", "单元测试", "集成测试", "代码重构"],
                    "effort": "中等"
                })
            elif "环境" in cause:
                solutions.append({
                    "title": "环境配置标准化",
                    "description": "建立标准化的环境配置和部署流程",
                    "steps": ["环境配置文档化", "自动化部署", "配置验证", "环境监控"],
                    "effort": "高"
                })
            elif "流程" in cause:
                solutions.append({
                    "title": "流程优化",
                    "description": "梳理和优化现有工作流程",
                    "steps": ["流程梳理", "瓶颈识别", "流程重设计", "培训推广"],
                    "effort": "中等"
                })
        
        return solutions
    
    async def _recommend_best_practices(self, problem_description: str, solutions: List[Dict]) -> List[str]:
        """推荐最佳实践"""
        return [
            "建立完善的测试体系",
            "实施持续集成和持续部署",
            "定期进行代码审查",
            "建立知识分享机制",
            "实施风险管理流程"
        ]
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        
        提供AI助手服务的完整状态信息，包括：
        1. 服务基本信息和运行状态
        2. AI服务提供商可用性
        3. 性能指标和使用统计
        4. 系统健康度评估
        
        Returns:
            Dict[str, Any]: 包含完整服务状态的字典
        """
        try:
            current_time = datetime.utcnow()
            uptime = (current_time - self.startup_time).total_seconds()
            
            # 检查AI服务提供商状态
            provider_status = {}
            available_providers = 0
            
            for provider in AIProvider:
                is_available = await self._is_provider_available(provider)
                config = self.ai_configs.get(provider, {})
                
                provider_status[provider.value] = {
                    "available": is_available,
                    "enabled": config.get("enabled", False),
                    "has_api_key": bool(config.get("api_key")),
                    "models": config.get("models", []),
                    "accuracy_score": config.get("accuracy_score", 0.0),
                    "cost_per_1k_tokens": config.get("cost_per_1k_tokens", 0.0)
                }
                
                if is_available:
                    available_providers += 1
            
            # 计算服务健康度
            health_score = await self._calculate_service_health(available_providers)
            
            # 计算成功率
            total_queries = self.metrics.get("total_queries", 0)
            successful_queries = self.metrics.get("successful_queries", 0)
            success_rate = (successful_queries / total_queries) if total_queries > 0 else 0.0
            
            # 服务状态判断
            service_status = "healthy"
            if health_score < 0.5:
                service_status = "unhealthy"
            elif health_score < 0.8:
                service_status = "degraded"
            
            return {
                # 基本信息
                "service_name": "AIAssistantService",
                "status": service_status,
                "version": self.service_version,
                "initialized": self.is_initialized,
                "uptime_seconds": uptime,
                "startup_time": self.startup_time.isoformat(),
                
                # AI服务提供商状态
                "ai_providers": provider_status,
                "available_providers_count": available_providers,
                "total_providers_count": len(AIProvider),
                
                # 性能指标
                "metrics": {
                    "total_queries": self.metrics.get("total_queries", 0),
                    "successful_queries": successful_queries,
                    "failed_queries": self.metrics.get("failed_queries", 0),
                    "success_rate": round(success_rate, 3),
                    "avg_response_time": round(self.metrics.get("avg_response_time", 0.0), 3),
                    "total_tokens_used": self.metrics.get("total_tokens_used", 0),
                    "estimated_total_cost": round(self.metrics.get("total_cost", 0.0), 4),
                    "suggestions_generated": self.metrics.get("suggestions_generated", 0)
                },
                
                # 健康度评估
                "health": {
                    "overall_score": round(health_score, 3),
                    "status": service_status,
                    "issues": await self._identify_health_issues(available_providers, success_rate)
                },
                
                # 系统信息
                "system": {
                    "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
                    "memory_usage": await self._get_memory_usage(),
                    "database_connected": self.db is not None
                },
                
                "last_check": current_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting service status: {str(e)}")
            return {
                "service_name": "AIAssistantService",
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _calculate_service_health(self, available_providers: int) -> float:
        """
        计算服务健康度
        
        Args:
            available_providers: 可用的AI服务提供商数量
            
        Returns:
            float: 健康度分数 (0.0-1.0)
        """
        try:
            health_factors = []
            
            # AI服务可用性 (40%权重)
            provider_ratio = available_providers / len(AIProvider)
            health_factors.append(provider_ratio * 0.4)
            
            # 查询成功率 (30%权重)
            total_queries = self.metrics.get("total_queries", 0)
            if total_queries > 0:
                success_rate = self.metrics.get("successful_queries", 0) / total_queries
                health_factors.append(success_rate * 0.3)
            else:
                health_factors.append(0.3)  # 没有查询时给予中等分数
            
            # 响应时间 (20%权重)
            avg_response_time = self.metrics.get("avg_response_time", 0.0)
            if avg_response_time > 0:
                # 响应时间越短越好，5秒以内为满分
                time_score = max(0, min(1, (5.0 - avg_response_time) / 5.0))
                health_factors.append(time_score * 0.2)
            else:
                health_factors.append(0.2)
            
            # 服务初始化状态 (10%权重)
            init_score = 1.0 if self.is_initialized else 0.0
            health_factors.append(init_score * 0.1)
            
            return sum(health_factors)
            
        except Exception as e:
            self.logger.warning(f"Error calculating health score: {str(e)}")
            return 0.5
    
    async def _identify_health_issues(self, available_providers: int, success_rate: float) -> List[str]:
        """
        识别健康问题
        
        Args:
            available_providers: 可用提供商数量
            success_rate: 成功率
            
        Returns:
            List[str]: 健康问题列表
        """
        issues = []
        
        try:
            if not self.is_initialized:
                issues.append("服务未完全初始化")
            
            if available_providers == 0:
                issues.append("所有AI服务提供商不可用")
            elif available_providers < len(AIProvider) / 2:
                issues.append("超过一半的AI服务提供商不可用")
            
            if success_rate < 0.8:
                issues.append(f"查询成功率较低: {success_rate:.1%}")
            
            avg_response_time = self.metrics.get("avg_response_time", 0.0)
            if avg_response_time > 10.0:
                issues.append(f"平均响应时间过长: {avg_response_time:.1f}秒")
            
            return issues
            
        except Exception as e:
            self.logger.warning(f"Error identifying health issues: {str(e)}")
            return ["健康检查异常"]
    
    async def _get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== 项目数据集成方法 ====================
    
    async def generate_project_suggestions(self, project_id: int, user_id: Optional[int] = None) -> List[Suggestion]:
        """
        为指定项目生成智能建议
        
        基于项目的当前状况，包括需求、测试用例、缺陷等数据，
        生成针对性的改进建议。
        
        Args:
            project_id: 项目ID
            user_id: 用户ID（用于权限检查）
            
        Returns:
            List[Suggestion]: 建议列表
        """
        try:
            # 权限检查
            if user_id and self.permission_service:
                await self.permission_service.validate_ai_operation_permission(
                    user_id, "suggestion_generate"
                )
            
            # 获取项目上下文数据
            if not self.project_sync_service:
                self.logger.warning("项目数据同步服务未初始化，尝试重新初始化")
                self.project_sync_service = await get_project_sync_service()
            
            project_context = await get_project_context(project_id)
            if not project_context:
                raise ValueError(f"项目{project_id}不存在或无法访问")
            
            # 分析项目状况
            analysis = await self._analyze_project_context(project_context)
            
            # 生成建议
            suggestions = await self._generate_suggestions_from_analysis(analysis, project_context)
            
            self.logger.info(f"为项目{project_id}生成了{len(suggestions)}条建议")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"生成项目{project_id}建议失败: {e}")
            raise
    
    async def analyze_requirements_quality(self, project_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        分析项目需求质量
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 需求质量分析结果
        """
        try:
            # 权限检查
            if user_id and self.permission_service:
                await self.permission_service.validate_ai_operation_permission(
                    user_id, "analysis_generate"
                )
            
            # 获取项目上下文
            project_context = await get_project_context(project_id)
            if not project_context:
                raise ValueError(f"项目{project_id}不存在")
            
            # 分析需求质量
            requirements = project_context.requirements
            
            if not requirements:
                return {
                    "overall_score": 0.0,
                    "completeness_score": 0.0,
                    "clarity_score": 0.0,
                    "consistency_score": 0.0,
                    "testability_score": 0.0,
                    "total_requirements": 0,
                    "problematic_requirements": [],
                    "recommendations": ["项目暂无需求，建议先添加需求"]
                }
            
            # 计算各项质量指标
            completeness_scores = []
            clarity_scores = []
            testability_scores = []
            problematic_requirements = []
            
            for req in requirements:
                # 完整性评分
                completeness = self._calculate_requirement_completeness(req)
                completeness_scores.append(completeness)
                
                # 清晰度评分
                clarity = self._calculate_requirement_clarity(req)
                clarity_scores.append(clarity)
                
                # 可测试性评分
                testability = self._calculate_requirement_testability(req)
                testability_scores.append(testability)
                
                # 识别问题需求
                if completeness < 0.6 or clarity < 0.6 or testability < 0.6:
                    issues = []
                    if completeness < 0.6:
                        issues.append("完整性不足")
                    if clarity < 0.6:
                        issues.append("描述不够清晰")
                    if testability < 0.6:
                        issues.append("可测试性差")
                    
                    problematic_requirements.append({
                        "requirement_id": req["id"],
                        "title": req["title"],
                        "issues": issues,
                        "completeness_score": completeness,
                        "clarity_score": clarity,
                        "testability_score": testability
                    })
            
            # 计算总体评分
            overall_completeness = sum(completeness_scores) / len(completeness_scores)
            overall_clarity = sum(clarity_scores) / len(clarity_scores)
            overall_testability = sum(testability_scores) / len(testability_scores)
            overall_score = (overall_completeness + overall_clarity + overall_testability) / 3
            
            # 生成改进建议
            recommendations = self._generate_requirements_recommendations(
                overall_completeness, overall_clarity, overall_testability, problematic_requirements
            )
            
            return {
                "overall_score": round(overall_score, 2),
                "completeness_score": round(overall_completeness, 2),
                "clarity_score": round(overall_clarity, 2),
                "consistency_score": round(overall_clarity, 2),  # 简化实现
                "testability_score": round(overall_testability, 2),
                "total_requirements": len(requirements),
                "problematic_requirements": problematic_requirements,
                "recommendations": recommendations
            }
            
        except Exception as e:
            self.logger.error(f"分析项目{project_id}需求质量失败: {e}")
            raise
    
    async def _analyze_project_context(self, project_context) -> Dict[str, Any]:
        """分析项目上下文"""
        project = project_context.project
        requirements = project_context.requirements
        test_cases = project_context.test_cases
        defects = project_context.defects
        metrics = project_context.metrics
        
        analysis = {
            "project_health": self._assess_project_health_detailed(project, requirements, test_cases, defects),
            "requirements_analysis": self._analyze_requirements_status(requirements),
            "testing_analysis": self._analyze_testing_status(test_cases),
            "quality_analysis": self._analyze_quality_status(defects),
            "metrics_analysis": metrics
        }
        
        return analysis
    
    def _assess_project_health_detailed(self, project, requirements, test_cases, defects) -> Dict[str, Any]:
        """评估项目健康状况（详细版本）"""
        total_requirements = len(requirements)
        completed_requirements = len([req for req in requirements if req.get("status") == "IMPLEMENTED"])
        
        total_test_cases = len(test_cases)
        passed_test_cases = len([tc for tc in test_cases if tc.get("pass_count", 0) > 0])
        
        total_defects = len(defects)
        open_defects = len([defect for defect in defects if defect.get("status") not in ["RESOLVED", "CLOSED"]])
        
        # 计算健康评分
        requirement_completion_rate = completed_requirements / total_requirements if total_requirements > 0 else 0
        test_pass_rate = passed_test_cases / total_test_cases if total_test_cases > 0 else 0
        defect_resolution_rate = (total_defects - open_defects) / total_defects if total_defects > 0 else 1
        
        health_score = (requirement_completion_rate + test_pass_rate + defect_resolution_rate) / 3
        
        return {
            "health_score": round(health_score, 2),
            "requirement_completion_rate": round(requirement_completion_rate, 2),
            "test_pass_rate": round(test_pass_rate, 2),
            "defect_resolution_rate": round(defect_resolution_rate, 2),
            "status": "健康" if health_score > 0.8 else "一般" if health_score > 0.6 else "需要关注"
        }
    
    def _analyze_requirements_status(self, requirements) -> Dict[str, Any]:
        """分析需求状态"""
        if not requirements:
            return {"status": "无需求", "recommendations": ["建议添加项目需求"]}
        
        status_counts = {}
        for req in requirements:
            status = req.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total": len(requirements),
            "status_distribution": status_counts,
            "completion_rate": status_counts.get("IMPLEMENTED", 0) / len(requirements)
        }
    
    def _analyze_testing_status(self, test_cases) -> Dict[str, Any]:
        """分析测试状态"""
        if not test_cases:
            return {"status": "无测试用例", "recommendations": ["建议添加测试用例"]}
        
        total_cases = len(test_cases)
        automated_cases = len([tc for tc in test_cases if tc.get("is_automated", False)])
        executed_cases = len([tc for tc in test_cases if tc.get("execution_count", 0) > 0])
        passed_cases = len([tc for tc in test_cases if tc.get("pass_count", 0) > 0])
        
        return {
            "total": total_cases,
            "automated": automated_cases,
            "executed": executed_cases,
            "passed": passed_cases,
            "automation_rate": automated_cases / total_cases,
            "execution_rate": executed_cases / total_cases,
            "pass_rate": passed_cases / executed_cases if executed_cases > 0 else 0
        }
    
    def _analyze_quality_status(self, defects) -> Dict[str, Any]:
        """分析质量状态"""
        if not defects:
            return {"status": "无缺陷记录", "quality_level": "优秀"}
        
        severity_counts = {}
        status_counts = {}
        
        for defect in defects:
            severity = defect.get("severity", "UNKNOWN")
            status = defect.get("status", "UNKNOWN")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1
        
        critical_defects = severity_counts.get("CRITICAL", 0)
        open_defects = len([d for d in defects if d.get("status") not in ["RESOLVED", "CLOSED"]])
        
        quality_level = "需要改进" if critical_defects > 0 or open_defects > len(defects) * 0.3 else "良好"
        
        return {
            "total": len(defects),
            "severity_distribution": severity_counts,
            "status_distribution": status_counts,
            "critical_defects": critical_defects,
            "open_defects": open_defects,
            "quality_level": quality_level
        }
    
    async def _generate_suggestions_from_analysis(self, analysis, project_context) -> List[Suggestion]:
        """基于分析结果生成建议"""
        suggestions = []
        
        # 基于项目健康状况生成建议
        health = analysis["project_health"]
        if health["health_score"] < 0.7:
            suggestions.append(Suggestion(
                title="改善项目整体健康状况",
                description=f"项目健康评分为{health['health_score']}，建议重点关注需求完成度、测试通过率和缺陷解决率",
                category="项目管理",
                priority="HIGH",
                action_items=[
                    "加快需求实现进度",
                    "提高测试用例通过率",
                    "及时解决未处理缺陷"
                ],
                expected_benefit="提升项目整体质量和进度",
                estimated_effort="2-3周"
            ))
        
        # 基于需求分析生成建议
        req_analysis = analysis["requirements_analysis"]
        if req_analysis.get("completion_rate", 0) < 0.5:
            suggestions.append(Suggestion(
                title="加快需求实现进度",
                description=f"需求完成率仅为{req_analysis.get('completion_rate', 0):.1%}，建议优化开发流程",
                category="需求管理",
                priority="HIGH",
                action_items=[
                    "重新评估需求优先级",
                    "增加开发资源投入",
                    "优化开发流程"
                ],
                expected_benefit="提高项目交付效率",
                estimated_effort="1-2周"
            ))
        
        # 基于测试分析生成建议
        test_analysis = analysis["testing_analysis"]
        if test_analysis.get("automation_rate", 0) < 0.3:
            suggestions.append(Suggestion(
                title="提升测试自动化率",
                description=f"当前自动化率为{test_analysis.get('automation_rate', 0):.1%}，建议增加自动化测试",
                category="测试管理",
                priority="MEDIUM",
                action_items=[
                    "识别适合自动化的测试用例",
                    "选择合适的自动化测试框架",
                    "编写自动化测试脚本"
                ],
                expected_benefit="提高测试效率和覆盖率",
                estimated_effort="3-4周"
            ))
        
        # 基于质量分析生成建议
        quality_analysis = analysis["quality_analysis"]
        if quality_analysis.get("critical_defects", 0) > 0:
            suggestions.append(Suggestion(
                title="优先处理严重缺陷",
                description=f"发现{quality_analysis.get('critical_defects', 0)}个严重缺陷，需要立即处理",
                category="质量管理",
                priority="CRITICAL",
                action_items=[
                    "立即分析严重缺陷根因",
                    "制定缺陷修复计划",
                    "加强代码审查流程"
                ],
                expected_benefit="降低项目风险，提升产品质量",
                estimated_effort="1周"
            ))
        
        return suggestions
    
    def _calculate_requirement_completeness(self, requirement) -> float:
        """计算需求完整性评分"""
        score = 0.0
        total_factors = 6
        
        # 检查各个完整性因素
        if requirement.get("description") and len(requirement["description"].strip()) > 10:
            score += 1
        if requirement.get("acceptance_criteria"):
            score += 1
        if requirement.get("priority"):
            score += 1
        if requirement.get("business_value"):
            score += 1
        if requirement.get("stakeholder"):
            score += 1
        if requirement.get("dependencies") is not None:
            score += 1
        
        return score / total_factors
    
    def _calculate_requirement_clarity(self, requirement) -> float:
        """计算需求清晰度评分"""
        # 简化实现：基于描述长度和关键词
        description = requirement.get("description", "")
        
        if not description:
            return 0.0
        
        score = 0.5  # 基础分
        
        # 描述长度适中
        if 50 <= len(description) <= 500:
            score += 0.2
        
        # 包含具体的动词
        action_words = ["应该", "必须", "能够", "支持", "提供", "实现", "处理"]
        if any(word in description for word in action_words):
            score += 0.2
        
        # 避免模糊词汇
        vague_words = ["合适的", "足够的", "适当的", "相关的", "等等"]
        if not any(word in description for word in vague_words):
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_requirement_testability(self, requirement) -> float:
        """计算需求可测试性评分"""
        score = 0.0
        
        # 有验收标准
        if requirement.get("acceptance_criteria"):
            score += 0.4
        
        # 描述中包含可量化的标准
        description = requirement.get("description", "")
        quantifiable_words = ["数量", "时间", "百分比", "秒", "分钟", "个", "次"]
        if any(word in description for word in quantifiable_words):
            score += 0.3
        
        # 有明确的输入输出描述
        io_words = ["输入", "输出", "返回", "显示", "结果"]
        if any(word in description for word in io_words):
            score += 0.3
        
        return min(score, 1.0)
    
    def _generate_requirements_recommendations(self, completeness, clarity, testability, problematic_reqs) -> List[str]:
        """生成需求改进建议"""
        recommendations = []
        
        if completeness < 0.7:
            recommendations.append("完善需求描述，确保包含验收标准、优先级、业务价值等关键信息")
        
        if clarity < 0.7:
            recommendations.append("使用更明确的表述，避免模糊词汇，增加具体的操作描述")
        
        if testability < 0.6:
            recommendations.append("为需求定义可量化的验收标准，明确输入条件和预期输出")
        
        if len(problematic_reqs) > 0:
            recommendations.append(f"优先处理{len(problematic_reqs)}个问题需求，提升整体需求质量")
        
        if not recommendations:
            recommendations.append("需求质量良好，建议继续保持当前标准")
        
        return recommendations
