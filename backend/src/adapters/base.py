"""
AI适配器基础类和通用数据结构

定义了所有AI服务提供商适配器的统一接口和数据结构，
确保不同AI服务的调用方式保持一致。
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
import uuid

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """AI服务提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BAIDU_WENXIN = "baidu_wenxin"
    ALIYUN_TONGYI = "aliyun_tongyi"
    GOOGLE_GEMINI = "google_gemini"
    ZHIPU_CHATGLM = "zhipu_chatglm"
    XUNFEI_XINGHUO = "xunfei_xinghuo"
    CUSTOM = "custom"


class MessageRole(Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class ResponseFormat(Enum):
    """响应格式枚举"""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    CODE = "code"


@dataclass
class ChatMessage:
    """聊天消息对象"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "role": self.role.value,
            "content": self.content
        }
        if self.name:
            result["name"] = self.name
        if self.function_call:
            result["function_call"] = self.function_call
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatMessage':
        """从字典创建消息对象"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            name=data.get("name"),
            function_call=data.get("function_call"),
            metadata=data.get("metadata", {})
        )


@dataclass
class AIRequest:
    """AI请求对象 - 统一的请求格式"""
    
    # 基本信息
    messages: List[ChatMessage]
    user_id: Optional[int] = None
    conversation_id: Optional[str] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # 模型参数
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None
    
    # 功能参数
    stream: bool = False
    response_format: ResponseFormat = ResponseFormat.TEXT
    functions: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    
    # 上下文和元数据
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间戳
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """后处理初始化"""
        if not self.messages:
            raise ValueError("Messages cannot be empty")
        
        # 确保至少有一条用户消息
        has_user_message = any(msg.role == MessageRole.USER for msg in self.messages)
        if not has_user_message:
            raise ValueError("At least one user message is required")
    
    def get_last_user_message(self) -> Optional[ChatMessage]:
        """获取最后一条用户消息"""
        for msg in reversed(self.messages):
            if msg.role == MessageRole.USER:
                return msg
        return None
    
    def get_system_message(self) -> Optional[ChatMessage]:
        """获取系统消息"""
        for msg in self.messages:
            if msg.role == MessageRole.SYSTEM:
                return msg
        return None
    
    def add_message(self, role: MessageRole, content: str, **kwargs):
        """添加消息"""
        message = ChatMessage(role=role, content=content, **kwargs)
        self.messages.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "request_id": self.request_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stop": self.stop,
            "stream": self.stream,
            "response_format": self.response_format.value,
            "functions": self.functions,
            "function_call": self.function_call,
            "context": self.context,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class TokenUsage:
    """Token使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class AIResponse:
    """AI响应对象 - 统一的响应格式"""
    
    # 基本信息
    request_id: str
    provider: AIProvider
    model: str
    content: str
    
    # 状态信息
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # 使用统计
    usage: Optional[TokenUsage] = None
    response_time: float = 0.0
    
    # 质量指标
    confidence_score: Optional[float] = None
    finish_reason: Optional[str] = None
    
    # 功能调用
    function_call: Optional[Dict[str, Any]] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 时间戳
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "request_id": self.request_id,
            "provider": self.provider.value,
            "model": self.model,
            "content": self.content,
            "success": self.success,
            "response_time": self.response_time,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.error_code:
            result["error_code"] = self.error_code
        if self.error_message:
            result["error_message"] = self.error_message
        if self.usage:
            result["usage"] = {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
                "total_tokens": self.usage.total_tokens
            }
        if self.confidence_score is not None:
            result["confidence_score"] = self.confidence_score
        if self.finish_reason:
            result["finish_reason"] = self.finish_reason
        if self.function_call:
            result["function_call"] = self.function_call
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result
    
    @classmethod
    def create_error_response(cls, request_id: str, provider: AIProvider, 
                            error_code: str, error_message: str, 
                            model: str = "unknown") -> 'AIResponse':
        """创建错误响应"""
        return cls(
            request_id=request_id,
            provider=provider,
            model=model,
            content="",
            success=False,
            error_code=error_code,
            error_message=error_message
        )


@dataclass
class StreamChunk:
    """流式响应数据块"""
    request_id: str
    provider: AIProvider
    content: str
    is_final: bool = False
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "request_id": self.request_id,
            "provider": self.provider.value,
            "content": self.content,
            "is_final": self.is_final,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AdapterConfig:
    """适配器配置"""
    provider: AIProvider
    api_key: str
    api_endpoint: Optional[str] = None
    api_version: Optional[str] = None
    default_model: Optional[str] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    max_concurrent_requests: int = 10
    rate_limit_per_minute: int = 60
    enabled: bool = True
    
    # 成本控制
    cost_per_token: Optional[float] = None
    daily_token_limit: Optional[int] = None
    monthly_token_limit: Optional[int] = None
    
    # 质量控制
    min_confidence_score: float = 0.0
    content_filter_enabled: bool = True
    
    # 自定义配置
    custom_headers: Dict[str, str] = field(default_factory=dict)
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """验证配置有效性"""
        if not self.api_key:
            logger.error(f"API key is required for {self.provider.value}")
            return False
        
        if self.max_retries < 0:
            logger.error("max_retries must be non-negative")
            return False
        
        if self.timeout <= 0:
            logger.error("timeout must be positive")
            return False
        
        if self.max_concurrent_requests <= 0:
            logger.error("max_concurrent_requests must be positive")
            return False
        
        return True


class BaseAIAdapter(ABC):
    """
    AI适配器基础类
    
    定义了所有AI服务提供商适配器必须实现的接口，
    确保不同AI服务的调用方式保持一致。
    """
    
    def __init__(self, config: AdapterConfig):
        """
        初始化适配器
        
        Args:
            config: 适配器配置
        """
        if not config.validate():
            raise ValueError(f"Invalid configuration for {config.provider.value}")
        
        self.config = config
        self.provider = config.provider
        self.logger = logging.getLogger(f"{__name__}.{self.provider.value}")
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_response_time": 0.0,
            "last_request_time": None
        }
        
        # 并发控制
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self._rate_limiter = asyncio.Semaphore(config.rate_limit_per_minute)
        
        # 健康状态
        self.is_healthy = True
        self.last_health_check = datetime.now(timezone.utc)
        self.consecutive_failures = 0
        
        self.logger.info(f"Initialized {self.provider.value} adapter")
    
    @abstractmethod
    async def chat_completion(self, request: AIRequest) -> AIResponse:
        """
        聊天完成接口
        
        Args:
            request: AI请求对象
            
        Returns:
            AIResponse: AI响应对象
        """
        pass
    
    @abstractmethod
    async def stream_chat_completion(self, request: AIRequest) -> AsyncGenerator[StreamChunk, None]:
        """
        流式聊天完成接口
        
        Args:
            request: AI请求对象
            
        Yields:
            StreamChunk: 流式响应数据块
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            List[str]: 模型名称列表
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 是否健康
        """
        pass
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """
        处理请求的通用方法，包含重试、限流、监控等逻辑
        
        Args:
            request: AI请求对象
            
        Returns:
            AIResponse: AI响应对象
        """
        if not self.config.enabled:
            return AIResponse.create_error_response(
                request.request_id, self.provider, 
                "ADAPTER_DISABLED", "Adapter is disabled"
            )
        
        # 并发控制
        async with self._semaphore:
            # 速率限制
            async with self._rate_limiter:
                return await self._execute_with_retry(request)
    
    async def _execute_with_retry(self, request: AIRequest) -> AIResponse:
        """
        带重试的执行请求
        
        Args:
            request: AI请求对象
            
        Returns:
            AIResponse: AI响应对象
        """
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                
                # 执行实际请求
                if request.stream:
                    # 流式请求需要特殊处理
                    response = await self._handle_stream_request(request)
                else:
                    response = await self.chat_completion(request)
                
                # 计算响应时间
                response.response_time = time.time() - start_time
                
                # 更新统计信息
                await self._update_stats(response, True)
                
                # 重置连续失败计数
                self.consecutive_failures = 0
                self.is_healthy = True
                
                return response
                
            except Exception as e:
                last_error = e
                self.consecutive_failures += 1
                
                self.logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.config.max_retries + 1}): {str(e)}"
                )
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))  # 指数退避
                else:
                    # 所有重试都失败了
                    await self._update_stats(None, False)
                    
                    # 检查是否需要标记为不健康
                    if self.consecutive_failures >= 5:
                        self.is_healthy = False
                    
                    return AIResponse.create_error_response(
                        request.request_id, self.provider,
                        "REQUEST_FAILED", str(last_error)
                    )
        
        # 理论上不会到达这里
        return AIResponse.create_error_response(
            request.request_id, self.provider,
            "UNKNOWN_ERROR", "Unknown error occurred"
        )
    
    async def _handle_stream_request(self, request: AIRequest) -> AIResponse:
        """
        处理流式请求
        
        Args:
            request: AI请求对象
            
        Returns:
            AIResponse: 聚合的响应对象
        """
        content_parts = []
        chunk_count = 0
        
        async for chunk in self.stream_chat_completion(request):
            content_parts.append(chunk.content)
            chunk_count += 1
            
            if chunk.is_final:
                break
        
        # 聚合所有内容
        full_content = "".join(content_parts)
        
        return AIResponse(
            request_id=request.request_id,
            provider=self.provider,
            model=request.model or self.config.default_model or "unknown",
            content=full_content,
            metadata={"stream_chunks": chunk_count}
        )
    
    async def _update_stats(self, response: Optional[AIResponse], success: bool):
        """
        更新统计信息
        
        Args:
            response: AI响应对象
            success: 是否成功
        """
        self.stats["total_requests"] += 1
        self.stats["last_request_time"] = datetime.now(timezone.utc)
        
        if success and response:
            self.stats["successful_requests"] += 1
            
            # 更新平均响应时间
            total_requests = self.stats["total_requests"]
            current_avg = self.stats["avg_response_time"]
            self.stats["avg_response_time"] = (
                (current_avg * (total_requests - 1) + response.response_time) / total_requests
            )
            
            # 更新Token统计
            if response.usage:
                self.stats["total_tokens"] += response.usage.total_tokens
                
                # 计算成本
                if self.config.cost_per_token:
                    cost = response.usage.total_tokens * self.config.cost_per_token
                    self.stats["total_cost"] += cost
        else:
            self.stats["failed_requests"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取适配器统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            "provider": self.provider.value,
            "is_healthy": self.is_healthy,
            "consecutive_failures": self.consecutive_failures,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "config": {
                "enabled": self.config.enabled,
                "max_concurrent_requests": self.config.max_concurrent_requests,
                "rate_limit_per_minute": self.config.rate_limit_per_minute,
                "timeout": self.config.timeout
            }
        }
    
    async def shutdown(self):
        """
        关闭适配器，清理资源
        """
        self.logger.info(f"Shutting down {self.provider.value} adapter")
        # 子类可以重写此方法来清理特定资源
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(provider={self.provider.value}, healthy={self.is_healthy})>"