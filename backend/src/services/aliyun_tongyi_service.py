"""
阿里通义千问服务

本模块提供阿里通义千问的高级服务功能，包括：
1. 智能聊天对话
2. 模型推荐和选择
3. 中文内容优化
4. 使用统计和成本分析
5. 健康状态监控

主要特性：
- 多模型支持和智能推荐
- 中文内容优化和文化适配
- 成本控制和使用监控
- 流式响应和实时交互
- 企业级安全和合规
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, AsyncGenerator
import json

from ..adapters.tongyi_adapter import TongyiAdapter, TongyiAdapterError
from ..adapters.base import AIRequest, AIResponse, ChatMessage, MessageRole, AdapterConfig, AIProvider, StreamChunk
from ..config.aliyun_tongyi_config import (
    TongyiConfig, TongyiModel, TaskComplexity, ModelRecommendation,
    create_tongyi_config_from_env, ChineseOptimizationConfig
)

logger = logging.getLogger(__name__)


class AliyunTongyiService:
    """阿里通义千问服务类"""
    
    def __init__(self, config: TongyiConfig):
        self.config = config
        self.adapter: Optional[TongyiAdapter] = None
        self.chinese_optimization = config.chinese_optimization.to_dict()
        self.model_configs = config.model_configs
        
        # 使用统计
        self.usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_response_time": 0.0,
            "model_usage": {},
            "last_request_time": None
        }
        
        logger.info("Aliyun Tongyi service initialized")
    
    async def initialize(self):
        """初始化服务"""
        try:
            # 创建适配器配置
            adapter_config = AdapterConfig(
                provider=AIProvider.ALIYUN_TONGYI,
                api_key=self.config.api_config.api_key,
                api_endpoint=self.config.api_config.api_endpoint,
                default_model="qwen-turbo",
                max_retries=self.config.api_config.max_retries,
                timeout=self.config.api_config.timeout,
                max_concurrent_requests=self.config.api_config.max_concurrent_requests,
                enabled=True
            )
            
            # 创建适配器
            self.adapter = TongyiAdapter(adapter_config, self.config)
            
            # 测试连接
            if await self.adapter.health_check():
                logger.info("Aliyun Tongyi service initialized successfully")
                return True
            else:
                logger.error("Aliyun Tongyi service health check failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Aliyun Tongyi service: {e}")
            return False
    
    def _analyze_task_complexity(self, content: str) -> TaskComplexity:
        """分析任务复杂度"""
        content_length = len(content)
        
        # 复杂度关键词
        complex_keywords = [
            "分析", "设计", "架构", "算法", "优化", "策略", "方案", "研究",
            "评估", "比较", "总结", "报告", "论文", "代码", "编程", "开发"
        ]
        
        simple_keywords = [
            "你好", "介绍", "是什么", "怎么样", "简单", "基础", "入门"
        ]
        
        # 基于长度判断
        if content_length < 20:
            base_complexity = TaskComplexity.SIMPLE
        elif content_length < 100:
            base_complexity = TaskComplexity.MEDIUM
        elif content_length < 500:
            base_complexity = TaskComplexity.COMPLEX
        else:
            base_complexity = TaskComplexity.VERY_COMPLEX
        
        # 基于关键词调整
        complex_count = sum(1 for keyword in complex_keywords if keyword in content)
        simple_count = sum(1 for keyword in simple_keywords if keyword in content)
        
        if simple_count > complex_count and base_complexity != TaskComplexity.SIMPLE:
            # 降低一个复杂度等级
            complexity_levels = [TaskComplexity.SIMPLE, TaskComplexity.MEDIUM, 
                               TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]
            current_index = complexity_levels.index(base_complexity)
            if current_index > 0:
                return complexity_levels[current_index - 1]
        
        elif complex_count > simple_count and base_complexity != TaskComplexity.VERY_COMPLEX:
            # 提高一个复杂度等级
            complexity_levels = [TaskComplexity.SIMPLE, TaskComplexity.MEDIUM, 
                               TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]
            current_index = complexity_levels.index(base_complexity)
            if current_index < len(complexity_levels) - 1:
                return complexity_levels[current_index + 1]
        
        return base_complexity
    
    async def get_model_recommendations(self, task_description: str, 
                                     cost_priority: bool = False) -> List[ModelRecommendation]:
        """获取模型推荐"""
        try:
            complexity = self._analyze_task_complexity(task_description)
            
            # 获取推荐模型
            primary_model = self.config.get_recommended_model(complexity, cost_priority)
            
            recommendations = []
            
            # 主推荐
            primary_config = self.config.get_model_info(primary_model)
            estimated_tokens = min(len(task_description) * 2, 1000)  # 估算Token数
            estimated_cost = (estimated_tokens / 1000) * primary_config.get("cost_per_1k_tokens", 0.02)
            
            recommendations.append(ModelRecommendation(
                recommended_model=primary_model,
                confidence=0.9,
                reasoning=f"基于任务复杂度({complexity.value})和{'成本优先' if cost_priority else '质量优先'}策略推荐",
                estimated_cost=estimated_cost,
                estimated_time=primary_config.get("avg_response_time", 2.0),
                alternative_models=[]
            ))
            
            # 备选推荐
            all_models = [TongyiModel.QWEN_TURBO, TongyiModel.QWEN_PLUS, 
                         TongyiModel.QWEN_MAX, TongyiModel.QWEN_MAX_1201]
            
            for model in all_models:
                if model != primary_model:
                    config = self.config.get_model_info(model)
                    cost = (estimated_tokens / 1000) * config.get("cost_per_1k_tokens", 0.02)
                    
                    confidence = 0.7 if model in [TongyiModel.QWEN_PLUS, TongyiModel.QWEN_MAX] else 0.5
                    
                    recommendations.append(ModelRecommendation(
                        recommended_model=model,
                        confidence=confidence,
                        reasoning=f"备选方案 - {config.get('strengths', ['通用能力'])[0]}",
                        estimated_cost=cost,
                        estimated_time=config.get("avg_response_time", 2.0),
                        alternative_models=[]
                    ))
            
            # 按置信度排序
            recommendations.sort(key=lambda x: x.confidence, reverse=True)
            
            return recommendations[:3]  # 返回前3个推荐
            
        except Exception as e:
            logger.error(f"Model recommendation error: {e}")
            # 返回默认推荐
            return [ModelRecommendation(
                recommended_model=TongyiModel.QWEN_TURBO,
                confidence=0.5,
                reasoning="默认推荐 - 平衡性能和成本",
                estimated_cost=0.02,
                estimated_time=1.5,
                alternative_models=[]
            )]
    
    async def chat_completion(self, messages: List[ChatMessage], 
                            user_id: int,
                            conversation_id: Optional[str] = None,
                            model: Optional[str] = None,
                            temperature: Optional[float] = None,
                            max_tokens: Optional[int] = None,
                            top_p: Optional[float] = None,
                            priority: str = "balanced",
                            max_cost_per_request: Optional[float] = None) -> AIResponse:
        """聊天完成"""
        if not self.adapter:
            raise TongyiAdapterError("Tongyi service not initialized")
        
        try:
            # 自动选择模型
            if not model:
                last_user_message = next((msg.content for msg in reversed(messages) 
                                        if msg.role == MessageRole.USER), "")
                recommendations = await self.get_model_recommendations(
                    last_user_message, 
                    cost_priority=(priority == "speed")
                )
                model = recommendations[0].recommended_model.value if recommendations else "qwen-turbo"
            
            # 构建请求
            request = AIRequest(
                messages=messages,
                user_id=user_id,
                conversation_id=conversation_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=False
            )
            
            # 执行请求
            response = await self.adapter.process_request(request)
            
            # 更新统计
            await self._update_usage_stats(response, model)
            
            return response
            
        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            await self._update_usage_stats(None, model, success=False)
            raise TongyiAdapterError(f"Chat completion failed: {str(e)}")
    
    async def stream_chat_completion(self, messages: List[ChatMessage],
                                   user_id: int,
                                   conversation_id: Optional[str] = None,
                                   model: Optional[str] = None,
                                   temperature: Optional[float] = None,
                                   max_tokens: Optional[int] = None,
                                   top_p: Optional[float] = None,
                                   priority: str = "balanced",
                                   max_cost_per_request: Optional[float] = None) -> AsyncGenerator[StreamChunk, None]:
        """流式聊天完成"""
        if not self.adapter:
            raise TongyiAdapterError("Tongyi service not initialized")
        
        try:
            # 自动选择模型
            if not model:
                last_user_message = next((msg.content for msg in reversed(messages) 
                                        if msg.role == MessageRole.USER), "")
                recommendations = await self.get_model_recommendations(
                    last_user_message, 
                    cost_priority=(priority == "speed")
                )
                model = recommendations[0].recommended_model.value if recommendations else "qwen-turbo"
            
            # 构建请求
            request = AIRequest(
                messages=messages,
                user_id=user_id,
                conversation_id=conversation_id,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=True
            )
            
            # 执行流式请求
            async for chunk in self.adapter.stream_chat_completion(request):
                yield chunk
                
                # 如果是最后一个chunk，更新统计
                if chunk.is_final:
                    # 创建模拟响应用于统计
                    mock_response = AIResponse(
                        request_id=chunk.request_id,
                        provider=AIProvider.ALIYUN_TONGYI,
                        model=model,
                        content="",  # 流式响应不需要完整内容
                        success=not chunk.metadata.get("error")
                    )
                    await self._update_usage_stats(mock_response, model)
            
        except Exception as e:
            logger.error(f"Stream chat completion error: {e}")
            await self._update_usage_stats(None, model, success=False)
            raise TongyiAdapterError(f"Stream chat completion failed: {str(e)}")
    
    async def _update_usage_stats(self, response: Optional[AIResponse], 
                                model: Optional[str], success: bool = None):
        """更新使用统计"""
        self.usage_stats["total_requests"] += 1
        self.usage_stats["last_request_time"] = datetime.now(timezone.utc)
        
        if success is None:
            success = response and response.success
        
        if success:
            self.usage_stats["successful_requests"] += 1
            
            if response:
                # 更新响应时间
                total_requests = self.usage_stats["total_requests"]
                current_avg = self.usage_stats["avg_response_time"]
                self.usage_stats["avg_response_time"] = (
                    (current_avg * (total_requests - 1) + response.response_time) / total_requests
                )
                
                # 更新Token统计
                if response.usage:
                    self.usage_stats["total_tokens"] += response.usage.total_tokens
                    
                    # 计算成本
                    model_config = self.config.get_model_info(
                        self.adapter.model_mapping.get(model, TongyiModel.QWEN_TURBO)
                    )
                    cost_per_1k = model_config.get("cost_per_1k_tokens", 0.02)
                    cost = (response.usage.total_tokens / 1000) * cost_per_1k
                    self.usage_stats["total_cost"] += cost
        else:
            self.usage_stats["failed_requests"] += 1
        
        # 更新模型使用统计
        if model:
            if model not in self.usage_stats["model_usage"]:
                self.usage_stats["model_usage"][model] = 0
            self.usage_stats["model_usage"][model] += 1
    
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        stats = self.usage_stats.copy()
        
        # 计算成功率
        total = stats["total_requests"]
        if total > 0:
            stats["success_rate"] = stats["successful_requests"] / total
            stats["cost_per_request"] = stats["total_cost"] / total
        else:
            stats["success_rate"] = 0.0
            stats["cost_per_request"] = 0.0
        
        # 添加适配器统计
        if self.adapter:
            adapter_stats = self.adapter.get_stats()
            stats["adapter_stats"] = adapter_stats
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health_info = {
                "healthy": False,
                "adapter_stats": {},
                "usage_stats": {},
                "available_models": [],
                "error": None
            }
            
            if not self.adapter:
                health_info["error"] = "Adapter not initialized"
                return health_info
            
            # 检查适配器健康状态
            adapter_healthy = await self.adapter.health_check()
            
            health_info.update({
                "healthy": adapter_healthy,
                "adapter_stats": self.adapter.get_stats(),
                "usage_stats": await self.get_usage_statistics(),
                "available_models": await self.adapter.get_available_models()
            })
            
            return health_info
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {
                "healthy": False,
                "adapter_stats": {},
                "usage_stats": {},
                "available_models": [],
                "error": str(e)
            }
    
    async def shutdown(self):
        """关闭服务"""
        if self.adapter:
            await self.adapter.shutdown()
        
        logger.info("Aliyun Tongyi service shutdown complete")


# 全局服务实例
_tongyi_service: Optional[AliyunTongyiService] = None


async def initialize_tongyi_service(api_key: str, 
                                  api_endpoint: Optional[str] = None) -> AliyunTongyiService:
    """初始化通义千问服务"""
    global _tongyi_service
    
    try:
        # 创建配置
        config = create_tongyi_config_from_env()
        
        # 覆盖API密钥
        config.api_config.api_key = api_key
        if api_endpoint:
            config.api_config.api_endpoint = api_endpoint
        
        # 创建服务
        _tongyi_service = AliyunTongyiService(config)
        
        # 初始化服务
        if await _tongyi_service.initialize():
            logger.info("Aliyun Tongyi service initialized successfully")
            return _tongyi_service
        else:
            raise Exception("Service initialization failed")
            
    except Exception as e:
        logger.error(f"Failed to initialize Aliyun Tongyi service: {e}")
        raise


async def get_tongyi_service() -> AliyunTongyiService:
    """获取通义千问服务实例"""
    if _tongyi_service is None:
        raise Exception("Aliyun Tongyi service not initialized. Call initialize_tongyi_service() first.")
    
    return _tongyi_service


async def shutdown_tongyi_service():
    """关闭通义千问服务"""
    global _tongyi_service
    
    if _tongyi_service:
        await _tongyi_service.shutdown()
        _tongyi_service = None
        logger.info("Aliyun Tongyi service shutdown complete")