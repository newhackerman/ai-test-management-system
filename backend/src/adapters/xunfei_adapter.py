"""
科大讯飞星火适配器实现 (占位符)
"""

import asyncio
import logging
from typing import List, AsyncGenerator

from .base import BaseAIAdapter, AIRequest, AIResponse, StreamChunk, AdapterConfig, AIProvider, TokenUsage

logger = logging.getLogger(__name__)


class XunfeiAdapter(BaseAIAdapter):
    """科大讯飞星火API适配器 (占位符实现)"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.logger.info("Xunfei Xinghuo adapter initialized (placeholder)")
    
    async def chat_completion(self, request: AIRequest) -> AIResponse:
        """聊天完成 (模拟实现)"""
        await asyncio.sleep(0.6)
        
        return AIResponse(
            request_id=request.request_id,
            provider=self.provider,
            model="xinghuo-3.5",
            content="这是来自讯飞星火的模拟响应。我在语言理解方面表现优秀，适合教育培训和语言学习场景。",
            usage=TokenUsage(prompt_tokens=75, completion_tokens=38, total_tokens=113),
            response_time=0.6
        )
    
    async def stream_chat_completion(self, request: AIRequest) -> AsyncGenerator[StreamChunk, None]:
        """流式聊天完成 (模拟实现)"""
        content_parts = [
            "这是", "来自", "讯飞星火", "的", "模拟", "流式", "响应", "。",
            "我在", "语言", "理解", "方面", "表现", "优秀", "，", "适合",
            "教育", "培训", "和", "语言", "学习", "场景", "。"
        ]
        
        for i, part in enumerate(content_parts):
            await asyncio.sleep(0.05)
            
            yield StreamChunk(
                request_id=request.request_id,
                provider=self.provider,
                content=part,
                is_final=(i == len(content_parts) - 1),
                chunk_index=i,
                metadata={"model": "xinghuo-3.5"}
            )
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return ["xinghuo-3.5", "xinghuo-3.0", "xinghuo-lite"]
    
    async def health_check(self) -> bool:
        """健康检查 (模拟实现)"""
        await asyncio.sleep(0.1)
        return True