"""
OpenAI适配器实现

支持OpenAI的GPT系列模型，包括GPT-4、GPT-3.5-turbo等。
提供完整的聊天完成、流式响应、函数调用等功能。

使用官方OpenAI Python客户端，提供更好的稳定性和功能支持。
"""

import asyncio
import json
import logging
import time
from typing import List, Dict, Any, AsyncGenerator, Optional

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from .base import (
    BaseAIAdapter, AIRequest, AIResponse, StreamChunk, 
    AdapterConfig, AIProvider, MessageRole, TokenUsage
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAIAdapter):
    """OpenAI API适配器 - 使用官方OpenAI Python客户端"""
    
    def __init__(self, config: AdapterConfig):
        """
        初始化OpenAI适配器
        
        Args:
            config: 适配器配置
        """
        super().__init__(config)
        
        # OpenAI API配置
        self.api_endpoint = config.api_endpoint or "https://api.openai.com/v1"
        self.api_key = config.api_key
        
        # 默认模型
        self.default_model = config.default_model or "gpt-3.5-turbo"
        
        # 支持的模型列表 - 更新到最新的模型
        self.supported_models = [
            # GPT-4 系列
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview", 
            "gpt-4-0125-preview",
            "gpt-4-1106-preview",
            "gpt-4-0613",
            "gpt-4-32k",
            "gpt-4-32k-0613",
            
            # GPT-3.5 系列
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
            
            # 最新模型
            "gpt-4o",
            "gpt-4o-mini"
        ]
        
        # 创建OpenAI客户端
        self._client: Optional[AsyncOpenAI] = None
        self._create_client()
    
    def _create_client(self):
        """创建OpenAI客户端"""
        try:
            client_kwargs = {
                "api_key": self.api_key,
                "timeout": self.config.timeout,
                "max_retries": 0,  # 我们自己处理重试
            }
            
            # 如果有自定义端点，设置base_url
            if self.api_endpoint != "https://api.openai.com/v1":
                client_kwargs["base_url"] = self.api_endpoint
            
            # 添加自定义头部
            if self.config.custom_headers:
                client_kwargs["default_headers"] = self.config.custom_headers
            
            self._client = AsyncOpenAI(**client_kwargs)
            
            self.logger.info(f"OpenAI client created with endpoint: {self.api_endpoint}")
            
        except Exception as e:
            self.logger.error(f"Failed to create OpenAI client: {str(e)}")
            raise
    
    def _get_client(self) -> AsyncOpenAI:
        """获取OpenAI客户端"""
        if self._client is None:
            self._create_client()
        return self._client
    
    async def chat_completion(self, request: AIRequest) -> AIResponse:
        """
        OpenAI聊天完成实现
        
        Args:
            request: AI请求对象
            
        Returns:
            AIResponse: AI响应对象
        """
        try:
            # 构建OpenAI API请求参数
            api_params = self._build_api_params(request)
            
            # 获取客户端
            client = self._get_client()
            
            start_time = time.time()
            
            # 调用OpenAI API
            completion = await client.chat.completions.create(**api_params)
            
            response_time = time.time() - start_time
            
            # 解析响应
            return self._parse_completion_response(request, completion, response_time)
                    
        except openai.APITimeoutError:
            self.logger.error("OpenAI API request timeout")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "TIMEOUT", "Request timeout"
            )
        except openai.RateLimitError as e:
            self.logger.error(f"OpenAI API rate limit exceeded: {str(e)}")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "RATE_LIMIT", str(e)
            )
        except openai.AuthenticationError as e:
            self.logger.error(f"OpenAI API authentication error: {str(e)}")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "AUTH_ERROR", str(e)
            )
        except openai.BadRequestError as e:
            self.logger.error(f"OpenAI API bad request: {str(e)}")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "BAD_REQUEST", str(e)
            )
        except openai.APIError as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "API_ERROR", str(e)
            )
        except Exception as e:
            self.logger.error(f"OpenAI request failed: {str(e)}")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "REQUEST_FAILED", str(e)
            )
    
    async def stream_chat_completion(self, request: AIRequest) -> AsyncGenerator[StreamChunk, None]:
        """
        OpenAI流式聊天完成实现
        
        Args:
            request: AI请求对象
            
        Yields:
            StreamChunk: 流式响应数据块
        """
        try:
            # 构建流式请求参数
            api_params = self._build_api_params(request, stream=True)
            
            # 获取客户端
            client = self._get_client()
            
            chunk_index = 0
            
            # 创建流式请求
            stream = await client.chat.completions.create(**api_params)
            
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    # 提取内容
                    content = delta.content if delta.content else ""
                    finish_reason = choice.finish_reason
                    
                    # 检查是否为最终块
                    is_final = finish_reason is not None
                    
                    yield StreamChunk(
                        request_id=request.request_id,
                        provider=self.provider,
                        content=content,
                        is_final=is_final,
                        chunk_index=chunk_index,
                        metadata={
                            "finish_reason": finish_reason,
                            "model": chunk.model,
                            "id": chunk.id
                        }
                    )
                    
                    chunk_index += 1
                    
                    if is_final:
                        break
                        
        except openai.APITimeoutError:
            self.logger.error("OpenAI streaming API timeout")
            yield StreamChunk(
                request_id=request.request_id,
                provider=self.provider,
                content="",
                is_final=True,
                chunk_index=0,
                metadata={"error": "Request timeout"}
            )
        except openai.APIError as e:
            self.logger.error(f"OpenAI streaming API error: {str(e)}")
            yield StreamChunk(
                request_id=request.request_id,
                provider=self.provider,
                content="",
                is_final=True,
                chunk_index=0,
                metadata={"error": str(e)}
            )
        except Exception as e:
            self.logger.error(f"OpenAI streaming request failed: {str(e)}")
            yield StreamChunk(
                request_id=request.request_id,
                provider=self.provider,
                content="",
                is_final=True,
                chunk_index=0,
                metadata={"error": str(e)}
            )
    
    def _build_api_params(self, request: AIRequest, stream: bool = False) -> Dict[str, Any]:
        """
        构建OpenAI API请求参数
        
        Args:
            request: AI请求对象
            stream: 是否为流式请求
            
        Returns:
            Dict[str, Any]: API请求参数
        """
        # 转换消息格式
        messages = []
        for msg in request.messages:
            openai_msg = {
                "role": msg.role.value,
                "content": msg.content
            }
            if msg.name:
                openai_msg["name"] = msg.name
            if msg.function_call:
                openai_msg["function_call"] = msg.function_call
            messages.append(openai_msg)
        
        # 构建基础参数
        api_params = {
            "model": request.model or self.default_model,
            "messages": messages,
            "stream": stream
        }
        
        # 添加可选参数
        if request.max_tokens is not None:
            api_params["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            api_params["temperature"] = request.temperature
        if request.top_p is not None:
            api_params["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            api_params["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            api_params["presence_penalty"] = request.presence_penalty
        if request.stop is not None:
            api_params["stop"] = request.stop
        
        # 函数调用支持 (新版本使用tools)
        if request.functions:
            # 转换为新的tools格式
            tools = []
            for func in request.functions:
                tools.append({
                    "type": "function",
                    "function": func
                })
            api_params["tools"] = tools
            
            # 处理function_call参数
            if request.function_call:
                if isinstance(request.function_call, str):
                    if request.function_call == "auto":
                        api_params["tool_choice"] = "auto"
                    elif request.function_call == "none":
                        api_params["tool_choice"] = "none"
                elif isinstance(request.function_call, dict):
                    # 转换为新格式
                    api_params["tool_choice"] = {
                        "type": "function",
                        "function": {"name": request.function_call.get("name")}
                    }
        
        # 响应格式
        if request.response_format.value == "json":
            api_params["response_format"] = {"type": "json_object"}
        
        # 添加自定义参数
        api_params.update(self.config.custom_params)
        
        return api_params
    
    def _parse_completion_response(self, request: AIRequest, completion: ChatCompletion, response_time: float) -> AIResponse:
        """
        解析OpenAI ChatCompletion响应
        
        Args:
            request: 原始请求
            completion: OpenAI ChatCompletion对象
            response_time: 响应时间
            
        Returns:
            AIResponse: 解析后的响应对象
        """
        try:
            # 提取基本信息
            if not completion.choices:
                return AIResponse.create_error_response(
                    request.request_id, self.provider,
                    "NO_CHOICES", "No choices in response"
                )
            
            choice = completion.choices[0]
            message = choice.message
            content = message.content or ""
            
            # 提取使用统计
            usage = None
            if completion.usage:
                usage = TokenUsage(
                    prompt_tokens=completion.usage.prompt_tokens,
                    completion_tokens=completion.usage.completion_tokens,
                    total_tokens=completion.usage.total_tokens
                )
            
            # 提取工具调用 (新版本)
            tool_calls = None
            function_call = None
            if message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    if tool_call.type == "function":
                        tool_calls.append({
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        })
                        
                        # 为了向后兼容，设置function_call
                        if not function_call:
                            function_call = {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
            
            # 构建响应
            response = AIResponse(
                request_id=request.request_id,
                provider=self.provider,
                model=completion.model,
                content=content,
                usage=usage,
                response_time=response_time,
                finish_reason=choice.finish_reason,
                function_call=function_call,
                metadata={
                    "id": completion.id,
                    "object": completion.object,
                    "created": completion.created,
                    "system_fingerprint": completion.system_fingerprint,
                    "tool_calls": tool_calls
                }
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to parse OpenAI completion response: {str(e)}")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "PARSE_ERROR", f"Failed to parse response: {str(e)}"
            )
    
    async def get_available_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            List[str]: 模型名称列表
        """
        try:
            client = self._get_client()
            
            # 获取模型列表
            models_response = await client.models.list()
            
            # 提取模型ID并过滤聊天模型
            all_models = [model.id for model in models_response.data]
            chat_models = [
                m for m in all_models 
                if any(prefix in m for prefix in ['gpt-3.5', 'gpt-4', 'gpt-4o'])
            ]
            
            return sorted(chat_models)
                    
        except openai.APIError as e:
            self.logger.error(f"OpenAI API error getting models: {str(e)}")
            return self.supported_models
        except Exception as e:
            self.logger.error(f"Error getting available models: {str(e)}")
            return self.supported_models
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 是否健康
        """
        try:
            client = self._get_client()
            
            # 尝试获取模型列表作为健康检查
            await client.models.list()
            
            self.is_healthy = True
            self.last_health_check = time.time()
            return True
                
        except openai.AuthenticationError:
            self.logger.error("Health check failed: Authentication error")
            self.is_healthy = False
            return False
        except openai.APIError as e:
            self.logger.error(f"Health check failed: OpenAI API error: {str(e)}")
            self.is_healthy = False
            return False
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            self.is_healthy = False
            return False
    
    async def shutdown(self):
        """关闭适配器"""
        await super().shutdown()
        if self._client:
            await self._client.close()
            self._client = None