"""
百度文心一言集成服务

本模块提供百度文心一言的高级集成功能，包括：
1. 模型管理和配置
2. 中文内容优化
3. 成本控制和监控
4. 性能优化
5. 错误处理和重试

主要功能：
- 智能模型选择
- 中文提示词优化
- 对话上下文管理
- 使用统计和成本分析
- 质量评估和优化建议
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from ..adapters.baidu_adapter import BaiduAdapter, BaiduWenxinError
from ..adapters.base import (
    AIRequest, AIResponse, ChatMessage, MessageRole, 
    AdapterConfig, AIProvider, TokenUsage
)
from ..core.config import get_settings
from ..utils.redis_client import RedisCache

logger = logging.getLogger(__name__)
settings = get_settings()


class WenxinModel(Enum):
    """文心一言模型枚举"""
    ERNIE_4_0 = "ernie-4.0-8k"
    ERNIE_3_5 = "ernie-3.5-8k"
    ERNIE_TURBO = "ernie-turbo-8k"
    ERNIE_SPEED = "ernie-speed-8k"


class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"      # 简单问答、基础对话
    MEDIUM = "medium"      # 一般分析、内容生成
    COMPLEX = "complex"    # 复杂推理、创意写作
    CRITICAL = "critical"  # 关键业务、高质量要求


@dataclass
class WenxinUsageStats:
    """文心一言使用统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time: float = 0.0
    model_usage: Dict[str, int] = None
    
    def __post_init__(self):
        if self.model_usage is None:
            self.model_usage = {}


@dataclass
class ModelRecommendation:
    """模型推荐结果"""
    recommended_model: WenxinModel
    confidence: float
    reasoning: str
    estimated_cost: float
    estimated_time: float


class BaiduWenxinService:
    """百度文心一言集成服务"""
    
    def __init__(self):
        self.cache = RedisCache("wenxin_service")
        self.adapter = None
        self.usage_stats = WenxinUsageStats()
        
        # 模型性能配置
        self.model_configs = {
            WenxinModel.ERNIE_4_0: {
                "cost_per_1k_tokens": 0.12,
                "avg_response_time": 3.5,
                "quality_score": 0.95,
                "complexity_threshold": TaskComplexity.COMPLEX,
                "max_concurrent": 5
            },
            WenxinModel.ERNIE_3_5: {
                "cost_per_1k_tokens": 0.08,
                "avg_response_time": 2.8,
                "quality_score": 0.85,
                "complexity_threshold": TaskComplexity.MEDIUM,
                "max_concurrent": 10
            },
            WenxinModel.ERNIE_TURBO: {
                "cost_per_1k_tokens": 0.04,
                "avg_response_time": 1.5,
                "quality_score": 0.75,
                "complexity_threshold": TaskComplexity.SIMPLE,
                "max_concurrent": 20
            },
            WenxinModel.ERNIE_SPEED: {
                "cost_per_1k_tokens": 0.02,
                "avg_response_time": 0.8,
                "quality_score": 0.65,
                "complexity_threshold": TaskComplexity.SIMPLE,
                "max_concurrent": 50
            }
        }
        
        # 中文优化配置
        self.chinese_optimization = {
            "enable_context_enhancement": True,
            "use_chinese_punctuation": True,
            "optimize_for_chinese_culture": True,
            "enable_idiom_usage": True
        }
    
    async def initialize(self, api_key: str, secret_key: str, 
                        api_endpoint: Optional[str] = None):
        """初始化服务"""
        try:
            # 创建适配器配置
            config = AdapterConfig(
                provider=AIProvider.BAIDU_WENXIN,
                api_key=f"{api_key}:{secret_key}",
                api_endpoint=api_endpoint,
                default_model=WenxinModel.ERNIE_3_5.value,
                max_retries=3,
                timeout=30.0,
                max_concurrent_requests=20
            )
            
            # 初始化适配器
            self.adapter = BaiduAdapter(config)
            
            # 加载使用统计
            await self._load_usage_stats()
            
            logger.info("百度文心一言服务初始化成功")
            
        except Exception as e:
            logger.error(f"百度文心一言服务初始化失败: {e}")
            raise
    
    async def chat_completion(self, messages: List[ChatMessage], 
                            user_id: Optional[int] = None,
                            conversation_id: Optional[str] = None,
                            **kwargs) -> AIResponse:
        """智能聊天完成"""
        if not self.adapter:
            raise RuntimeError("Service not initialized")
        
        try:
            # 分析任务复杂度
            complexity = await self._analyze_task_complexity(messages)
            
            # 推荐最佳模型
            recommendation = await self._recommend_model(messages, complexity, **kwargs)
            
            # 优化中文内容
            optimized_messages = await self._optimize_chinese_content(messages)
            
            # 构建请求
            request = AIRequest(
                messages=optimized_messages,
                user_id=user_id,
                conversation_id=conversation_id,
                model=recommendation.recommended_model.value,
                **kwargs
            )
            
            # 执行请求
            response = await self.adapter.process_request(request)
            
            # 更新统计
            await self._update_usage_stats(request, response, recommendation)
            
            # 后处理响应
            response = await self._post_process_response(response)
            
            return response
            
        except Exception as e:
            logger.error(f"聊天完成失败: {e}")
            raise
    
    async def stream_chat_completion(self, messages: List[ChatMessage],
                                   user_id: Optional[int] = None,
                                   conversation_id: Optional[str] = None,
                                   **kwargs):
        """流式聊天完成"""
        if not self.adapter:
            raise RuntimeError("Service not initialized")
        
        try:
            # 分析和优化（同非流式）
            complexity = await self._analyze_task_complexity(messages)
            recommendation = await self._recommend_model(messages, complexity, **kwargs)
            optimized_messages = await self._optimize_chinese_content(messages)
            
            # 构建流式请求
            request = AIRequest(
                messages=optimized_messages,
                user_id=user_id,
                conversation_id=conversation_id,
                model=recommendation.recommended_model.value,
                stream=True,
                **kwargs
            )
            
            # 执行流式请求
            async for chunk in self.adapter.stream_chat_completion(request):
                # 可以在这里对流式内容进行实时处理
                yield chunk
            
        except Exception as e:
            logger.error(f"流式聊天完成失败: {e}")
            raise
    
    async def _analyze_task_complexity(self, messages: List[ChatMessage]) -> TaskComplexity:
        """分析任务复杂度"""
        try:
            # 获取最后一条用户消息
            last_user_message = None
            for msg in reversed(messages):
                if msg.role == MessageRole.USER:
                    last_user_message = msg
                    break
            
            if not last_user_message:
                return TaskComplexity.SIMPLE
            
            content = last_user_message.content.lower()
            
            # 复杂度关键词
            complex_keywords = [
                "分析", "设计", "架构", "算法", "优化", "策略", "方案", 
                "评估", "比较", "推理", "逻辑", "创作", "写作", "编程"
            ]
            
            medium_keywords = [
                "解释", "说明", "介绍", "总结", "整理", "列举", 
                "描述", "概述", "对比", "区别"
            ]
            
            # 检查复杂度指标
            complexity_score = 0
            
            # 关键词匹配
            for keyword in complex_keywords:
                if keyword in content:
                    complexity_score += 2
            
            for keyword in medium_keywords:
                if keyword in content:
                    complexity_score += 1
            
            # 文本长度
            if len(content) > 500:
                complexity_score += 2
            elif len(content) > 200:
                complexity_score += 1
            
            # 问号数量（多个问题通常更复杂）
            question_count = content.count('?') + content.count('？')
            if question_count > 2:
                complexity_score += 2
            elif question_count > 1:
                complexity_score += 1
            
            # 上下文长度
            if len(messages) > 10:
                complexity_score += 1
            
            # 判断复杂度
            if complexity_score >= 6:
                return TaskComplexity.COMPLEX
            elif complexity_score >= 3:
                return TaskComplexity.MEDIUM
            else:
                return TaskComplexity.SIMPLE
                
        except Exception as e:
            logger.warning(f"任务复杂度分析失败: {e}")
            return TaskComplexity.MEDIUM
    
    async def _recommend_model(self, messages: List[ChatMessage], 
                             complexity: TaskComplexity,
                             **kwargs) -> ModelRecommendation:
        """推荐最佳模型"""
        try:
            # 用户指定模型
            if "model" in kwargs and kwargs["model"]:
                specified_model = kwargs["model"]
                for model in WenxinModel:
                    if model.value == specified_model:
                        config = self.model_configs[model]
                        return ModelRecommendation(
                            recommended_model=model,
                            confidence=1.0,
                            reasoning="用户指定模型",
                            estimated_cost=config["cost_per_1k_tokens"] * 2,  # 估算2K tokens
                            estimated_time=config["avg_response_time"]
                        )
            
            # 基于复杂度推荐
            if complexity == TaskComplexity.COMPLEX:
                recommended = WenxinModel.ERNIE_4_0
                confidence = 0.9
                reasoning = "复杂任务需要高质量模型"
            elif complexity == TaskComplexity.MEDIUM:
                recommended = WenxinModel.ERNIE_3_5
                confidence = 0.85
                reasoning = "中等复杂度任务的平衡选择"
            else:
                # 简单任务根据响应时间要求选择
                if kwargs.get("priority") == "speed":
                    recommended = WenxinModel.ERNIE_SPEED
                    reasoning = "优先响应速度"
                else:
                    recommended = WenxinModel.ERNIE_TURBO
                    reasoning = "简单任务的经济选择"
                confidence = 0.8
            
            # 考虑成本限制
            if kwargs.get("max_cost_per_request"):
                max_cost = kwargs["max_cost_per_request"]
                for model in [WenxinModel.ERNIE_SPEED, WenxinModel.ERNIE_TURBO, 
                             WenxinModel.ERNIE_3_5, WenxinModel.ERNIE_4_0]:
                    config = self.model_configs[model]
                    estimated_cost = config["cost_per_1k_tokens"] * 2
                    if estimated_cost <= max_cost:
                        recommended = model
                        reasoning += f"，符合成本限制({max_cost}元)"
                        break
            
            config = self.model_configs[recommended]
            
            return ModelRecommendation(
                recommended_model=recommended,
                confidence=confidence,
                reasoning=reasoning,
                estimated_cost=config["cost_per_1k_tokens"] * 2,
                estimated_time=config["avg_response_time"]
            )
            
        except Exception as e:
            logger.warning(f"模型推荐失败: {e}")
            # 默认推荐
            return ModelRecommendation(
                recommended_model=WenxinModel.ERNIE_3_5,
                confidence=0.5,
                reasoning="默认推荐",
                estimated_cost=0.16,
                estimated_time=2.8
            )
    
    async def _optimize_chinese_content(self, messages: List[ChatMessage]) -> List[ChatMessage]:
        """优化中文内容"""
        if not self.chinese_optimization["enable_context_enhancement"]:
            return messages
        
        optimized_messages = []
        
        for msg in messages:
            content = msg.content
            
            # 中文标点优化
            if self.chinese_optimization["use_chinese_punctuation"]:
                content = self._optimize_chinese_punctuation(content)
            
            # 文化背景优化
            if self.chinese_optimization["optimize_for_chinese_culture"]:
                content = self._add_chinese_context(content, msg.role)
            
            optimized_messages.append(ChatMessage(
                role=msg.role,
                content=content,
                name=msg.name,
                function_call=msg.function_call,
                metadata=msg.metadata
            ))
        
        return optimized_messages
    
    def _optimize_chinese_punctuation(self, content: str) -> str:
        """优化中文标点符号"""
        # 替换英文标点为中文标点
        replacements = {
            ',': '，',
            '.': '。',
            '?': '？',
            '!': '！',
            ':': '：',
            ';': '；'
        }
        
        for en_punct, zh_punct in replacements.items():
            # 只替换中文上下文中的英文标点
            content = content.replace(en_punct + ' ', zh_punct)
            # 处理句末标点
            if content.endswith(en_punct):
                content = content[:-1] + zh_punct
        
        return content
    
    def _add_chinese_context(self, content: str, role: MessageRole) -> str:
        """添加中文文化背景"""
        if role == MessageRole.SYSTEM:
            # 为系统消息添加中文文化背景
            if "请" not in content and "您" not in content:
                content = f"请以中文文化背景和思维方式来理解和回应。{content}"
        
        elif role == MessageRole.USER:
            # 检查是否需要添加礼貌用语
            polite_words = ["请", "您", "谢谢", "麻烦"]
            if not any(word in content for word in polite_words):
                if content.endswith(('?', '？')):
                    content = f"请{content}"
                else:
                    content = f"{content}，谢谢。"
        
        return content
    
    async def _post_process_response(self, response: AIResponse) -> AIResponse:
        """后处理响应"""
        if not response.success:
            return response
        
        # 优化中文输出格式
        content = response.content
        
        # 确保中文标点符号
        if self.chinese_optimization["use_chinese_punctuation"]:
            content = self._optimize_chinese_punctuation(content)
        
        # 添加质量评分
        quality_score = await self._evaluate_response_quality(content)
        response.confidence_score = quality_score
        
        # 更新内容
        response.content = content
        
        return response
    
    async def _evaluate_response_quality(self, content: str) -> float:
        """评估响应质量"""
        try:
            quality_score = 0.5  # 基础分数
            
            # 长度合理性
            if 50 <= len(content) <= 2000:
                quality_score += 0.1
            
            # 中文内容比例
            chinese_chars = sum(1 for char in content if '\u4e00' <= char <= '\u9fff')
            if chinese_chars / len(content) > 0.7:
                quality_score += 0.1
            
            # 结构完整性
            if content.strip().endswith(('。', '！', '？', '.')):
                quality_score += 0.1
            
            # 避免重复内容
            sentences = content.split('。')
            if len(set(sentences)) / len(sentences) > 0.8:
                quality_score += 0.1
            
            # 专业术语使用
            professional_terms = ["分析", "建议", "方案", "策略", "优化", "实现"]
            if any(term in content for term in professional_terms):
                quality_score += 0.1
            
            return min(1.0, quality_score)
            
        except Exception as e:
            logger.warning(f"质量评估失败: {e}")
            return 0.7
    
    async def _update_usage_stats(self, request: AIRequest, response: AIResponse,
                                recommendation: ModelRecommendation):
        """更新使用统计"""
        try:
            self.usage_stats.total_requests += 1
            
            if response.success:
                self.usage_stats.successful_requests += 1
                
                if response.usage:
                    self.usage_stats.total_tokens += response.usage.total_tokens
                    
                    # 计算实际成本
                    model_config = self.model_configs.get(recommendation.recommended_model, {})
                    cost_per_1k = model_config.get("cost_per_1k_tokens", 0.08)
                    actual_cost = (response.usage.total_tokens / 1000) * cost_per_1k
                    self.usage_stats.total_cost += actual_cost
                
                # 更新平均响应时间
                total_requests = self.usage_stats.successful_requests
                current_avg = self.usage_stats.avg_response_time
                self.usage_stats.avg_response_time = (
                    (current_avg * (total_requests - 1) + response.response_time) / total_requests
                )
                
                # 更新模型使用统计
                model = recommendation.recommended_model.value
                self.usage_stats.model_usage[model] = self.usage_stats.model_usage.get(model, 0) + 1
            else:
                self.usage_stats.failed_requests += 1
            
            # 定期保存统计数据
            if self.usage_stats.total_requests % 10 == 0:
                await self._save_usage_stats()
                
        except Exception as e:
            logger.warning(f"更新使用统计失败: {e}")
    
    async def _load_usage_stats(self):
        """加载使用统计"""
        try:
            stats_data = await self.cache.get("usage_stats")
            if stats_data:
                self.usage_stats = WenxinUsageStats(**stats_data)
                logger.debug("已加载文心一言使用统计")
        except Exception as e:
            logger.warning(f"加载使用统计失败: {e}")
    
    async def _save_usage_stats(self):
        """保存使用统计"""
        try:
            stats_data = {
                "total_requests": self.usage_stats.total_requests,
                "successful_requests": self.usage_stats.successful_requests,
                "failed_requests": self.usage_stats.failed_requests,
                "total_tokens": self.usage_stats.total_tokens,
                "total_cost": self.usage_stats.total_cost,
                "avg_response_time": self.usage_stats.avg_response_time,
                "model_usage": self.usage_stats.model_usage
            }
            await self.cache.set("usage_stats", stats_data, 86400)  # 24小时
            logger.debug("已保存文心一言使用统计")
        except Exception as e:
            logger.warning(f"保存使用统计失败: {e}")
    
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        success_rate = 0
        if self.usage_stats.total_requests > 0:
            success_rate = self.usage_stats.successful_requests / self.usage_stats.total_requests
        
        return {
            "total_requests": self.usage_stats.total_requests,
            "successful_requests": self.usage_stats.successful_requests,
            "failed_requests": self.usage_stats.failed_requests,
            "success_rate": success_rate,
            "total_tokens": self.usage_stats.total_tokens,
            "total_cost": self.usage_stats.total_cost,
            "avg_response_time": self.usage_stats.avg_response_time,
            "model_usage": self.usage_stats.model_usage,
            "cost_per_request": (
                self.usage_stats.total_cost / self.usage_stats.successful_requests
                if self.usage_stats.successful_requests > 0 else 0
            )
        }
    
    async def get_model_recommendations(self, task_description: str) -> List[ModelRecommendation]:
        """获取模型推荐"""
        # 创建临时消息进行分析
        messages = [ChatMessage(role=MessageRole.USER, content=task_description)]
        complexity = await self._analyze_task_complexity(messages)
        
        recommendations = []
        
        # 为每个模型生成推荐
        for model in WenxinModel:
            config = self.model_configs[model]
            
            # 计算适合度分数
            suitability_score = 0.5
            
            if complexity == TaskComplexity.COMPLEX and model == WenxinModel.ERNIE_4_0:
                suitability_score = 0.95
            elif complexity == TaskComplexity.MEDIUM and model == WenxinModel.ERNIE_3_5:
                suitability_score = 0.9
            elif complexity == TaskComplexity.SIMPLE and model in [WenxinModel.ERNIE_TURBO, WenxinModel.ERNIE_SPEED]:
                suitability_score = 0.85
            
            recommendations.append(ModelRecommendation(
                recommended_model=model,
                confidence=suitability_score,
                reasoning=f"基于任务复杂度({complexity.value})的推荐",
                estimated_cost=config["cost_per_1k_tokens"] * 2,
                estimated_time=config["avg_response_time"]
            ))
        
        # 按适合度排序
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return recommendations
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if not self.adapter:
            return {
                "healthy": False,
                "error": "Service not initialized"
            }
        
        try:
            is_healthy = await self.adapter.health_check()
            
            return {
                "healthy": is_healthy,
                "adapter_stats": self.adapter.get_stats(),
                "usage_stats": await self.get_usage_statistics(),
                "available_models": await self.adapter.get_available_models()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def shutdown(self):
        """关闭服务"""
        if self.adapter:
            await self.adapter.shutdown()
        
        await self._save_usage_stats()
        logger.info("百度文心一言服务已关闭")


# 全局服务实例
_wenxin_service = None

async def get_wenxin_service() -> BaiduWenxinService:
    """获取文心一言服务实例"""
    global _wenxin_service
    
    if _wenxin_service is None:
        _wenxin_service = BaiduWenxinService()
    
    return _wenxin_service


async def initialize_wenxin_service(api_key: str, secret_key: str, 
                                  api_endpoint: Optional[str] = None):
    """初始化文心一言服务"""
    service = await get_wenxin_service()
    await service.initialize(api_key, secret_key, api_endpoint)
    return service