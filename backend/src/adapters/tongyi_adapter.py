"""
阿里通义千问适配器实现

本模块实现了阿里通义千问API的适配器，提供统一的AI服务接口。
支持多种模型、流式响应、中文优化等功能。
"""

import asyncio
import json
import logging
import time
from typing import List, AsyncGenerator, Dict, Any, Optional
import aiohttp
from datetime import datetime, timezone

from .base import BaseAIAdapter, AIRequest, AIResponse, StreamChunk, AdapterConfig, AIProvider, TokenUsage, MessageRole
from ..config.aliyun_tongyi_config import TongyiModel, TongyiConfig

logger = logging.getLogger(__name__)


class TongyiAdapterError(Exception):
    """通义千问适配器异常"""
    def __init__(self, message: str, error_code: str = None, status_code: int = None):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


class TongyiAdapter(BaseAIAdapter):
    """阿里通义千问API适配器"""
    
    def __init__(self, config: AdapterConfig, tongyi_config: TongyiConfig):
        super().__init__(config)
        self.tongyi_config = tongyi_config
        self.api_key = tongyi_config.api_config.api_key
        self.api_endpoint = tongyi_config.api_config.api_endpoint
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 模型映射
        self.model_mapping = {
            "qwen-max": TongyiModel.QWEN_MAX,
            "qwen-max-1201": TongyiModel.QWEN_MAX_1201,
            "qwen-plus": TongyiModel.QWEN_PLUS,
            "qwen-turbo": TongyiModel.QWEN_TURBO,
            "qwen-long": TongyiModel.QWEN_LONG,
            "qwen-vl-plus": TongyiModel.QWEN_VL_PLUS,
            "qwen-vl-max": TongyiModel.QWEN_VL_MAX
        }
        
        self.logger.info("Tongyi Qianwen adapter initialized")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            headers.update(self.config.custom_headers)
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
        
        return self.session
    
    def _convert_messages(self, messages: List) -> List[Dict[str, Any]]:
        """转换消息格式为通义千问API格式"""
        converted_messages = []
        
        for msg in messages:
            role = msg.role.value if hasattr(msg.role, 'value') else msg.role
            
            # 通义千问API角色映射
            if role == "system":
                api_role = "system"
            elif role == "user":
                api_role = "user"
            elif role == "assistant":
                api_role = "assistant"
            else:
                api_role = "user"  # 默认为用户角色
            
            converted_messages.append({
                "role": api_role,
                "content": msg.content
            })
        
        return converted_messages
    
    def _apply_chinese_optimization(self, content: str) -> str:
        """应用中文内容优化"""
        if not self.tongyi_config.chinese_optimization:
            return content
        
        optimized_content = content
        
        # 中文标点符号优化
        if self.tongyi_config.chinese_optimization.use_chinese_punctuation:
            optimized_content = optimized_content.replace(".", "。")
            optimized_content = optimized_content.replace(",", "，")
            optimized_content = optimized_content.replace("?", "？")
            optimized_content = optimized_content.replace("!", "！")
            optimized_content = optimized_content.replace(";", "；")
            optimized_content = optimized_content.replace(":", "：")
        
        # 礼貌用语增强
        if self.tongyi_config.chinese_optimization.enhance_politeness:
            if not any(word in optimized_content for word in ["您好", "请", "谢谢", "不好意思"]):
                if optimized_content and not optimized_content.startswith(("您好", "请")):
                    optimized_content = "您好！" + optimized_content
        
        return optimized_content
    
    def _build_request_payload(self, request: AIRequest) -> Dict[str, Any]:
        """构建请求载荷"""
        messages = self._convert_messages(request.messages)
        
        # 应用中文优化到用户消息
        if self.tongyi_config.chinese_optimization.enable_context_enhancement:
            for msg in messages:
                if msg["role"] == "user":
                    msg["content"] = self._apply_chinese_optimization(msg["content"])
        
        payload = {
            "model": request.model or self.config.default_model or "qwen-turbo",
            "input": {
                "messages": messages
            },
            "parameters": {}
        }
        
        # 添加可选参数
        if request.max_tokens:
            payload["parameters"]["max_tokens"] = request.max_tokens
        
        if request.temperature is not None:
            payload["parameters"]["temperature"] = request.temperature
        
        if request.top_p is not None:
            payload["parameters"]["top_p"] = request.top_p
        
        # 流式响应
        if request.stream:
            payload["parameters"]["incremental_output"] = True
        
        return payload
    
    async def chat_completion(self, request: AIRequest) -> AIResponse:
        """聊天完成"""
        start_time = time.time()
        
        try:
            session = await self._get_session()
            payload = self._build_request_payload(request)
            
            self.logger.debug(f"Sending request to Tongyi API: {json.dumps(payload, ensure_ascii=False)}")
            
            async with session.post(self.api_endpoint, json=payload) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    error_message = response_data.get("message", f"HTTP {response.status}")
                    error_code = response_data.get("code", str(response.status))
                    
                    return AIResponse.create_error_response(
                        request.request_id, self.provider,
                        error_code, error_message,
                        request.model or "unknown"
                    )
                
                # 解析响应
                output = response_data.get("output", {})
                usage_data = response_data.get("usage", {})
                
                content = output.get("text", "")
                
                # 应用中文优化到响应内容
                if self.tongyi_config.chinese_optimization.optimize_for_chinese_culture:
                    content = self._apply_chinese_optimization(content)
                
                # 构建Token使用统计
                usage = TokenUsage(
                    prompt_tokens=usage_data.get("input_tokens", 0),
                    completion_tokens=usage_data.get("output_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0)
                )
                
                response_time = time.time() - start_time
                
                return AIResponse(
                    request_id=request.request_id,
                    provider=self.provider,
                    model=request.model or "qwen-turbo",
                    content=content,
                    usage=usage,
                    response_time=response_time,
                    finish_reason=output.get("finish_reason"),
                    metadata={
                        "request_id": response_data.get("request_id"),
                        "chinese_optimized": True
                    }
                )
                
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "HTTP_ERROR", str(e),
                request.model or "unknown"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return AIResponse.create_error_response(
                request.request_id, self.provider,
                "UNKNOWN_ERROR", str(e),
                request.model or "unknown"
            )
    
    async def stream_chat_completion(self, request: AIRequest) -> AsyncGenerator[StreamChunk, None]:
        """流式聊天完成"""
        try:
            session = await self._get_session()
            payload = self._build_request_payload(request)
            payload["parameters"]["incremental_output"] = True
            
            self.logger.debug(f"Sending stream request to Tongyi API")
            
            async with session.post(self.api_endpoint, json=payload) as response:
                if response.status != 200:
                    error_data = await response.json()
                    error_message = error_data.get("message", f"HTTP {response.status}")
                    
                    yield StreamChunk(
                        request_id=request.request_id,
                        provider=self.provider,
                        content="",
                        is_final=True,
                        metadata={"error": error_message}
                    )
                    return
                
                chunk_index = 0
                full_content = ""
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line or not line.startswith('data:'):
                        continue
                    
                    try:
                        # 解析SSE数据
                        json_str = line[5:].strip()  # 移除 'data:' 前缀
                        
                        if json_str == '[DONE]':
                            yield StreamChunk(
                                request_id=request.request_id,
                                provider=self.provider,
                                content="",
                                is_final=True,
                                chunk_index=chunk_index,
                                metadata={"full_content": full_content}
                            )
                            break
                        
                        chunk_data = json.loads(json_str)
                        output = chunk_data.get("output", {})
                        
                        # 获取增量内容
                        chunk_content = output.get("text", "")
                        
                        if chunk_content:
                            # 应用中文优化
                            if self.tongyi_config.chinese_optimization.optimize_for_chinese_culture:
                                chunk_content = self._apply_chinese_optimization(chunk_content)
                            
                            full_content += chunk_content
                            
                            yield StreamChunk(
                                request_id=request.request_id,
                                provider=self.provider,
                                content=chunk_content,
                                is_final=False,
                                chunk_index=chunk_index,
                                metadata={
                                    "model": request.model or "qwen-turbo",
                                    "finish_reason": output.get("finish_reason")
                                }
                            )
                            
                            chunk_index += 1
                    
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse chunk JSON: {e}")
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing chunk: {e}")
                        continue
                
        except Exception as e:
            self.logger.error(f"Stream completion error: {e}")
            yield StreamChunk(
                request_id=request.request_id,
                provider=self.provider,
                content="",
                is_final=True,
                metadata={"error": str(e)}
            )
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return list(self.model_mapping.keys())
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型详细信息"""
        tongyi_model = self.model_mapping.get(model)
        if not tongyi_model:
            return {}
        
        return self.tongyi_config.get_model_info(tongyi_model)
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 发送简单的测试请求
            test_request = AIRequest(
                messages=[{"role": MessageRole.USER, "content": "你好"}],
                model="qwen-turbo",
                max_tokens=10
            )
            
            response = await self.chat_completion(test_request)
            return response.success
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def shutdown(self):
        """关闭适配器"""
        if self.session and not self.session.closed:
            await self.session.close()
        
        await super().shutdown()
        self.logger.info("Tongyi adapter shutdown complete")
    
    def __repr__(self):
        return f"<TongyiAdapter(healthy={self.is_healthy}, models={len(self.model_mapping)})>"