"""
百度文心一言适配器实现

本模块实现百度文心一言API的完整集成，包括：
1. 标准聊天完成接口
2. 流式响应支持
3. 多模型支持
4. 错误处理和重试
5. Token使用统计
6. 中文内容优化

支持的模型：
- ERNIE-4.0-8K: 文心大模型4.0版本
- ERNIE-3.5-8K: 文心大模型3.5版本  
- ERNIE-Turbo-8K: 文心大模型Turbo版本
- ERNIE-Speed-8K: 文心大模型Speed版本
"""

import asyncio
import json
import logging
import time
from typing import List, AsyncGenerator, Dict, Any, Optional
import aiohttp
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timezone

from .base import (
    BaseAIAdapter, AIRequest, AIResponse, StreamChunk, 
    AdapterConfig, AIProvider, TokenUsage, MessageRole, ChatMessage
)

logger = logging.getLogger(__name__)


class BaiduWenxinError(Exception):
    """百度文心一言API错误"""
    
    def __init__(self, error_code: str, error_msg: str, request_id: Optional[str] = None):
        self.error_code = error_code
        self.error_msg = error_msg
        self.request_id = request_id
        super().__init__(f"Baidu Wenxin Error [{error_code}]: {error_msg}")


class BaiduAdapter(BaseAIAdapter):
    """百度文心一言API适配器"""
    
    # 模型映射表
    MODEL_MAPPING = {
        "ernie-4.0": "completions_pro",
        "ernie-4.0-8k": "completions_pro", 
        "ernie-3.5": "completions",
        "ernie-3.5-8k": "completions",
        "ernie-turbo": "eb-instant",
        "ernie-turbo-8k": "eb-instant",
        "ernie-speed": "ernie_speed",
        "ernie-speed-8k": "ernie_speed",
        "wenxin-4.0": "completions_pro",  # 兼容旧命名
        "wenxin-3.5": "completions",
        "wenxin-turbo": "eb-instant"
    }
    
    # 默认API端点
    DEFAULT_BASE_URL = "https://aip.baidubce.com"
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        
        # 验证必要配置
        if not config.api_key:
            raise ValueError("Baidu API Key is required")
        
        # 解析API Key (格式: api_key:secret_key)
        if ':' in config.api_key:
            self.api_key, self.secret_key = config.api_key.split(':', 1)
        else:
            raise ValueError("Baidu API Key format should be 'api_key:secret_key'")
        
        # 设置基础URL
        self.base_url = config.api_endpoint or self.DEFAULT_BASE_URL
        
        # 访问令牌缓存
        self.access_token = None
        self.token_expires_at = None
        
        # HTTP会话
        self.session = None
        
        self.logger.info("Baidu Wenxin adapter initialized successfully")
    
    async def _ensure_session(self):
        """确保HTTP会话存在"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "AI-Test-Management-System/1.0"
                }
            )
    
    async def _get_access_token(self) -> str:
        """获取访问令牌"""
        # 检查缓存的令牌是否有效
        if (self.access_token and self.token_expires_at and 
            datetime.now(timezone.utc) < self.token_expires_at):
            return self.access_token
        
        await self._ensure_session()
        
        # 获取新的访问令牌
        token_url = f"{self.base_url}/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            async with self.session.get(token_url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise BaiduWenxinError(
                        "TOKEN_ERROR", 
                        f"Failed to get access token: {error_text}"
                    )
                
                data = await response.json()
                
                if "error" in data:
                    raise BaiduWenxinError(
                        data.get("error", "UNKNOWN_ERROR"),
                        data.get("error_description", "Unknown error")
                    )
                
                self.access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)  # 默认1小时
                
                # 设置过期时间（提前5分钟刷新）
                self.token_expires_at = datetime.now(timezone.utc).timestamp() + expires_in - 300
                
                self.logger.debug("Successfully obtained Baidu access token")
                return self.access_token
                
        except aiohttp.ClientError as e:
            raise BaiduWenxinError("NETWORK_ERROR", f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise BaiduWenxinError("PARSE_ERROR", f"Failed to parse token response: {str(e)}")
    
    def _get_model_endpoint(self, model: str) -> str:
        """获取模型对应的API端点"""
        model_lower = model.lower()
        endpoint_name = self.MODEL_MAPPING.get(model_lower)
        
        if not endpoint_name:
            # 如果没有找到映射，使用默认的completions
            endpoint_name = "completions"
            self.logger.warning(f"Unknown model {model}, using default endpoint")
        
        return f"/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{endpoint_name}"
    
    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """转换消息格式为百度API格式"""
        converted = []
        
        for msg in messages:
            # 百度API支持的角色
            if msg.role == MessageRole.SYSTEM:
                # 系统消息转换为用户消息的前缀
                if converted and converted[-1]["role"] == "user":
                    # 如果上一条是用户消息，合并系统消息
                    converted[-1]["content"] = f"{msg.content}\n\n{converted[-1]['content']}"
                else:
                    # 否则作为独立的用户消息
                    converted.append({
                        "role": "user",
                        "content": f"[系统指令] {msg.content}"
                    })
            elif msg.role == MessageRole.USER:
                converted.append({
                    "role": "user", 
                    "content": msg.content
                })
            elif msg.role == MessageRole.ASSISTANT:
                converted.append({
                    "role": "assistant",
                    "content": msg.content
                })
        
        # 确保消息数量为奇数（以用户消息结尾）
        if len(converted) % 2 == 0:
            # 如果是偶数，最后一条应该是助手消息，需要添加一个用户消息
            if converted and converted[-1]["role"] == "assistant":
                converted.append({
                    "role": "user",
                    "content": "请继续。"
                })
        
        return converted
    
    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """构建请求载荷"""
        payload = {
            "messages": self._convert_messages(request.messages),
            "stream": request.stream
        }
        
        # 添加可选参数
        if request.temperature is not None:
            payload["temperature"] = max(0.01, min(1.0, request.temperature))
        
        if request.top_p is not None:
            payload["top_p"] = max(0.01, min(1.0, request.top_p))
        
        if request.max_tokens is not None:
            payload["max_output_tokens"] = min(request.max_tokens, 8192)
        
        # 百度特有参数
        if "penalty_score" in request.metadata:
            payload["penalty_score"] = request.metadata["penalty_score"]
        
        if "system" in request.metadata:
            payload["system"] = request.metadata["system"]
        
        return payload
    
    async def chat_completion(self, request: AIRequest) -> AIResponse:
        """聊天完成接口"""
        start_time = time.time()
        
        try:
            # 获取访问令牌
            access_token = await self._get_access_token()
            
            # 确定模型和端点
            model = request.model or self.config.default_model or "ernie-3.5-8k"
            endpoint = self._get_model_endpoint(model)
            
            # 构建请求
            url = f"{self.base_url}{endpoint}?access_token={access_token}"
            payload = self._build_request_payload(request)
            payload["stream"] = False  # 非流式请求
            
            await self._ensure_session()
            
            # 发送请求
            async with self.session.post(url, json=payload) as response:
                response_text = await response.text()
                
                if response.status != 200:
                    raise BaiduWenxinError(
                        f"HTTP_{response.status}",
                        f"HTTP error: {response_text}"
                    )
                
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise BaiduWenxinError("PARSE_ERROR", f"Invalid JSON response: {str(e)}")
                
                # 检查API错误
                if "error_code" in data:
                    raise BaiduWenxinError(
                        str(data["error_code"]),
                        data.get("error_msg", "Unknown API error")
                    )
                
                # 解析响应
                content = data.get("result", "")
                usage_data = data.get("usage", {})
                
                # 构建Token使用统计
                usage = TokenUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0)
                )
                
                response_time = time.time() - start_time
                
                return AIResponse(
                    request_id=request.request_id,
                    provider=self.provider,
                    model=model,
                    content=content,
                    usage=usage,
                    response_time=response_time,
                    finish_reason=data.get("finish_reason"),
                    metadata={
                        "id": data.get("id"),
                        "created": data.get("created"),
                        "sentence_id": data.get("sentence_id"),
                        "is_truncated": data.get("is_truncated", False),
                        "need_clear_history": data.get("need_clear_history", False)
                    }
                )
                
        except BaiduWenxinError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in chat_completion: {str(e)}")
            raise BaiduWenxinError("INTERNAL_ERROR", str(e))
    
    async def stream_chat_completion(self, request: AIRequest) -> AsyncGenerator[StreamChunk, None]:
        """流式聊天完成接口"""
        try:
            # 获取访问令牌
            access_token = await self._get_access_token()
            
            # 确定模型和端点
            model = request.model or self.config.default_model or "ernie-3.5-8k"
            endpoint = self._get_model_endpoint(model)
            
            # 构建请求
            url = f"{self.base_url}{endpoint}?access_token={access_token}"
            payload = self._build_request_payload(request)
            payload["stream"] = True  # 流式请求
            
            await self._ensure_session()
            
            chunk_index = 0
            
            # 发送流式请求
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise BaiduWenxinError(
                        f"HTTP_{response.status}",
                        f"HTTP error: {error_text}"
                    )
                
                # 处理流式响应
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line or not line.startswith('data: '):
                        continue
                    
                    # 移除 'data: ' 前缀
                    json_str = line[6:]
                    
                    if json_str == '[DONE]':
                        # 流式响应结束
                        yield StreamChunk(
                            request_id=request.request_id,
                            provider=self.provider,
                            content="",
                            is_final=True,
                            chunk_index=chunk_index,
                            metadata={"model": model}
                        )
                        break
                    
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
                    
                    # 检查错误
                    if "error_code" in data:
                        raise BaiduWenxinError(
                            str(data["error_code"]),
                            data.get("error_msg", "Unknown API error")
                        )
                    
                    # 提取内容
                    content = data.get("result", "")
                    is_final = data.get("is_end", False)
                    
                    if content or is_final:
                        yield StreamChunk(
                            request_id=request.request_id,
                            provider=self.provider,
                            content=content,
                            is_final=is_final,
                            chunk_index=chunk_index,
                            metadata={
                                "model": model,
                                "sentence_id": data.get("sentence_id"),
                                "is_truncated": data.get("is_truncated", False)
                            }
                        )
                        chunk_index += 1
                        
                        if is_final:
                            break
                            
        except BaiduWenxinError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in stream_chat_completion: {str(e)}")
            raise BaiduWenxinError("INTERNAL_ERROR", str(e))
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "ernie-4.0-8k",      # 文心大模型4.0
            "ernie-3.5-8k",      # 文心大模型3.5  
            "ernie-turbo-8k",    # 文心大模型Turbo
            "ernie-speed-8k",    # 文心大模型Speed
            "wenxin-4.0",        # 兼容命名
            "wenxin-3.5",        # 兼容命名
            "wenxin-turbo"       # 兼容命名
        ]
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 尝试获取访问令牌
            await self._get_access_token()
            
            # 发送简单的测试请求
            test_request = AIRequest(
                messages=[
                    ChatMessage(role=MessageRole.USER, content="你好")
                ],
                model="ernie-speed-8k",  # 使用最快的模型进行健康检查
                max_tokens=10
            )
            
            response = await self.chat_completion(test_request)
            return response.success
            
        except Exception as e:
            self.logger.warning(f"Health check failed: {str(e)}")
            return False
    
    async def shutdown(self):
        """关闭适配器，清理资源"""
        if self.session and not self.session.closed:
            await self.session.close()
        
        self.access_token = None
        self.token_expires_at = None
        
        await super().shutdown()
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        model_info = {
            "ernie-4.0-8k": {
                "name": "ERNIE-4.0-8K",
                "description": "文心大模型4.0版本，具有更强的理解和生成能力",
                "max_tokens": 8192,
                "context_window": 8192,
                "cost_per_1k_tokens": 0.12,
                "strengths": ["推理能力强", "中文理解优秀", "创意写作"]
            },
            "ernie-3.5-8k": {
                "name": "ERNIE-3.5-8K", 
                "description": "文心大模型3.5版本，平衡性能和成本",
                "max_tokens": 8192,
                "context_window": 8192,
                "cost_per_1k_tokens": 0.08,
                "strengths": ["通用对话", "文本生成", "知识问答"]
            },
            "ernie-turbo-8k": {
                "name": "ERNIE-Turbo-8K",
                "description": "文心大模型Turbo版本，响应速度快",
                "max_tokens": 8192,
                "context_window": 8192,
                "cost_per_1k_tokens": 0.04,
                "strengths": ["快速响应", "实时对话", "简单任务"]
            },
            "ernie-speed-8k": {
                "name": "ERNIE-Speed-8K",
                "description": "文心大模型Speed版本，极速响应",
                "max_tokens": 8192,
                "context_window": 8192,
                "cost_per_1k_tokens": 0.02,
                "strengths": ["极速响应", "高并发", "基础对话"]
            }
        }
        
        return model_info.get(model.lower(), {
            "name": model,
            "description": "未知模型",
            "max_tokens": 8192,
            "context_window": 8192,
            "cost_per_1k_tokens": 0.08,
            "strengths": []
        })
    
    def __repr__(self):
        return f"<BaiduAdapter(healthy={self.is_healthy}, token_valid={self.access_token is not None})>"