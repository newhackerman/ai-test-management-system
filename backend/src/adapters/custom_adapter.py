"""
自定义适配器实现 (占位符)
"""

import asyncio
import logging
from typing import List, AsyncGenerator

from .base import BaseAIAdapter, AIRequest, AIResponse, StreamChunk, AdapterConfig, AIProvider, TokenUsage

logger = logging.getLogger(__name__)


class CustomAdapter(BaseAIAdapter):
    """自定义API适配器 (占位符实现)"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.logger.info("Custom adapter initialized (placeholder)")
    
    async def chat_completion(self, request: AIRequest) -> AIResponse:
        """聊天完成 (模拟实现)"""
        await asyncio.sleep(1.0)
        
        return AIResponse(
            request_id=request.request_id,
            provider=self.provider,
            model="custom-model",
            content="这是来自自定义适配器的模拟响应。可以根据具体需求实现私有部署或特殊需求的AI服务。",
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            response_time=1.0
        )
    
    async def stream_chat_completion(self, request: AIRequest) -> AsyncGenerator[StreamChunk, None]:
        """流式聊天完成 (模拟实现)"""
        content_parts = [
            "这是", "来自", "自定义", "适配器", "的", "模拟", "流式", "响应", "。",
            "可以", "根据", "具体", "需求", "实现", "私有", "部署", "或",
            "特殊", "需求的", "AI服务", "。"
        ]
        
        for i, part in enumerate(content_parts):
            await asyncio.sleep(0.1)
            
            yield StreamChunk(
                request_id=request.request_id,
                provider=self.provider,
                content=part,
                is_final=(i == len(content_parts) - 1),
                chunk_index=i,
                metadata={"model": "custom-model"}
            )
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return ["custom-model", "custom-model-v2"]
    
    async def health_check(self) -> bool:
        """健康检查 (模拟实现)"""
        await asyncio.sleep(0.1)
        return True