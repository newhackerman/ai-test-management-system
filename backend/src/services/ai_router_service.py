"""
AI路由服务 - 智能选择和调度AI服务提供商
"""
import asyncio
import logging
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from ..models.ai_model_config import AIModelConfig
from ..models.ai_usage_stats import AIUsageStats
from ..core.config import get_settings
from .cost_control_service import CostControlService
from .request_queue_service import RequestQueueService, RequestPriority, QueuedRequest
from .chinese_content_router import ChineseContentRouter, ChineseContentAnalysis, ChineseRoutingDecision

logger = logging.getLogger(__name__)
settings = get_settings()


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


class TaskType(Enum):
    """任务类型枚举"""
    SIMPLE_QUERY = "simple_query"
    COMPLEX_ANALYSIS = "complex_analysis"
    CHINESE_CONTENT = "chinese_content"
    CODE_GENERATION = "code_generation"
    TEST_CASE_GENERATION = "test_case_generation"
    DOCUMENT_WRITING = "document_writing"
    CREATIVE_WRITING = "creative_writing"
    DATA_ANALYSIS = "data_analysis"
    TRANSLATION = "translation"
    GENERAL_TASK = "general_task"


class RoutingStrategy(Enum):
    """路由策略枚举"""
    ACCURACY_FIRST = "accuracy_first"
    COST_FIRST = "cost_first"
    SPEED_FIRST = "speed_first"
    BALANCED = "balanced"
    LOAD_BALANCED = "load_balanced"


@dataclass
class AIRequest:
    """AI请求对象"""
    content: str
    user_id: int
    task_type: Optional[TaskType] = None
    context: Optional[Dict[str, Any]] = None
    preferred_provider: Optional[AIProvider] = None
    routing_strategy: Optional[RoutingStrategy] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    priority: str = "normal"  # low, normal, high, urgent
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        self.timestamp = datetime.utcnow()
        self.request_id = f"{self.user_id}_{int(time.time() * 1000)}"


@dataclass
class ProviderHealth:
    """服务提供商健康状态"""
    provider: AIProvider
    is_available: bool = True
    response_time: float = 0.0
    success_rate: float = 1.0
    last_check: datetime = None
    error_count: int = 0
    quota_remaining: int = 100
    current_load: int = 0
    max_concurrent: int = 10
    cost_per_token: float = 0.0
    
    def __post_init__(self):
        if self.last_check is None:
            self.last_check = datetime.utcnow()


@dataclass
class RoutingDecision:
    """路由决策结果"""
    selected_provider: AIProvider
    confidence: float
    reasoning: str
    fallback_providers: List[AIProvider]
    estimated_cost: float
    estimated_time: float
    routing_strategy_used: RoutingStrategy


class AIRouterService:
    """AI服务路由器 - 智能选择和调度AI服务提供商"""
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # 成本控制服务
        self.cost_control = CostControlService(db)
        
        # 请求队列服务
        self.request_queue = RequestQueueService(db, max_concurrent_requests=100)
        
        # 中文内容路由器
        self.chinese_router = ChineseContentRouter()
        
        # 服务提供商健康状态缓存
        self.provider_health: Dict[AIProvider, ProviderHealth] = {}
        
        # 负载均衡状态
        self.load_balancer_state: Dict[AIProvider, int] = {}
        
        # 路由策略配置 - 更详细的配置
        self.routing_strategies = {
            TaskType.COMPLEX_ANALYSIS: {
                "strategy": RoutingStrategy.ACCURACY_FIRST,
                "preferred_providers": [AIProvider.OPENAI, AIProvider.ANTHROPIC, AIProvider.GOOGLE_GEMINI],
                "min_accuracy": 0.9,
                "max_cost_per_token": 0.05,
                "timeout": 30.0
            },
            TaskType.SIMPLE_QUERY: {
                "strategy": RoutingStrategy.COST_FIRST,
                "preferred_providers": [AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI, AIProvider.OPENAI],
                "min_accuracy": 0.7,
                "max_cost_per_token": 0.01,
                "timeout": 10.0
            },
            TaskType.CHINESE_CONTENT: {
                "strategy": RoutingStrategy.ACCURACY_FIRST,
                "preferred_providers": [AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI, AIProvider.ZHIPU_CHATGLM],
                "min_accuracy": 0.85,
                "max_cost_per_token": 0.03,
                "timeout": 20.0
            },
            TaskType.CODE_GENERATION: {
                "strategy": RoutingStrategy.ACCURACY_FIRST,
                "preferred_providers": [AIProvider.OPENAI, AIProvider.ANTHROPIC, AIProvider.GOOGLE_GEMINI],
                "min_accuracy": 0.9,
                "max_cost_per_token": 0.04,
                "timeout": 25.0
            },
            TaskType.TEST_CASE_GENERATION: {
                "strategy": RoutingStrategy.BALANCED,
                "preferred_providers": [AIProvider.OPENAI, AIProvider.ANTHROPIC, AIProvider.BAIDU_WENXIN],
                "min_accuracy": 0.85,
                "max_cost_per_token": 0.03,
                "timeout": 20.0
            },
            TaskType.DOCUMENT_WRITING: {
                "strategy": RoutingStrategy.BALANCED,
                "preferred_providers": [AIProvider.ANTHROPIC, AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI],
                "min_accuracy": 0.8,
                "max_cost_per_token": 0.025,
                "timeout": 25.0
            },
            TaskType.CREATIVE_WRITING: {
                "strategy": RoutingStrategy.ACCURACY_FIRST,
                "preferred_providers": [AIProvider.ANTHROPIC, AIProvider.OPENAI, AIProvider.BAIDU_WENXIN],
                "min_accuracy": 0.85,
                "max_cost_per_token": 0.04,
                "timeout": 30.0
            },
            TaskType.DATA_ANALYSIS: {
                "strategy": RoutingStrategy.ACCURACY_FIRST,
                "preferred_providers": [AIProvider.OPENAI, AIProvider.GOOGLE_GEMINI, AIProvider.ANTHROPIC],
                "min_accuracy": 0.9,
                "max_cost_per_token": 0.05,
                "timeout": 35.0
            },
            TaskType.TRANSLATION: {
                "strategy": RoutingStrategy.BALANCED,
                "preferred_providers": [AIProvider.GOOGLE_GEMINI, AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI],
                "min_accuracy": 0.8,
                "max_cost_per_token": 0.02,
                "timeout": 15.0
            }
        }
        
        # 模型能力评分 (基于历史表现和基准测试)
        self.provider_capabilities = {
            AIProvider.OPENAI: {
                "accuracy": 0.95,
                "speed": 0.8,
                "cost_efficiency": 0.6,
                "chinese_support": 0.7,
                "code_generation": 0.95,
                "creative_writing": 0.9,
                "reasoning": 0.95
            },
            AIProvider.ANTHROPIC: {
                "accuracy": 0.93,
                "speed": 0.75,
                "cost_efficiency": 0.5,
                "chinese_support": 0.6,
                "code_generation": 0.9,
                "creative_writing": 0.95,
                "reasoning": 0.93
            },
            AIProvider.GOOGLE_GEMINI: {
                "accuracy": 0.9,
                "speed": 0.85,
                "cost_efficiency": 0.7,
                "chinese_support": 0.75,
                "code_generation": 0.85,
                "creative_writing": 0.8,
                "reasoning": 0.88
            },
            AIProvider.BAIDU_WENXIN: {
                "accuracy": 0.88,
                "speed": 0.9,
                "cost_efficiency": 0.9,
                "chinese_support": 0.95,
                "code_generation": 0.8,
                "creative_writing": 0.85,
                "reasoning": 0.82
            },
            AIProvider.ALIYUN_TONGYI: {
                "accuracy": 0.85,
                "speed": 0.88,
                "cost_efficiency": 0.85,
                "chinese_support": 0.9,
                "code_generation": 0.75,
                "creative_writing": 0.8,
                "reasoning": 0.8
            },
            AIProvider.ZHIPU_CHATGLM: {
                "accuracy": 0.82,
                "speed": 0.85,
                "cost_efficiency": 0.95,
                "chinese_support": 0.9,
                "code_generation": 0.7,
                "creative_writing": 0.75,
                "reasoning": 0.78
            },
            AIProvider.XUNFEI_XINGHUO: {
                "accuracy": 0.8,
                "speed": 0.9,
                "cost_efficiency": 0.9,
                "chinese_support": 0.88,
                "code_generation": 0.65,
                "creative_writing": 0.7,
                "reasoning": 0.75
            }
        }
        
        # 初始化健康状态和负载均衡状态
        for provider in AIProvider:
            if provider != AIProvider.CUSTOM:  # 自定义提供商需要单独配置
                self.provider_health[provider] = ProviderHealth(provider=provider)
                self.load_balancer_state[provider] = 0
        
        # 健康检查任务
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = 60  # 60秒检查一次
        
        # 故障转移配置
        self.failover_config = {
            "max_retries": 3,
            "retry_delay_base": 1.0,  # 基础重试延迟（秒）
            "retry_delay_max": 10.0,  # 最大重试延迟（秒）
            "health_check_timeout": 5.0,  # 健康检查超时（秒）
            "recovery_threshold": 3,  # 连续成功次数后恢复
            "failure_threshold": 5,  # 连续失败次数后标记不可用
        }
    
    async def route_request(self, request: AIRequest) -> RoutingDecision:
        """
        智能路由AI请求
        
        Args:
            request: AI请求对象
            
        Returns:
            RoutingDecision: 路由决策结果
        """
        try:
            self.logger.info(f"Routing AI request {request.request_id} for user {request.user_id}")
            
            # 1. 分析请求类型和复杂度
            if not request.task_type:
                request.task_type = self._analyze_task_type(request)
            
            # 2. 获取可用的服务提供商
            available_providers = await self._get_available_providers(request)
            
            if not available_providers:
                self.logger.warning("No available AI providers")
                return RoutingDecision(
                    selected_provider=AIProvider.OPENAI,
                    confidence=0.1,
                    reasoning="No providers available, using default",
                    fallback_providers=[],
                    estimated_cost=0.0,
                    estimated_time=0.0,
                    routing_strategy_used=RoutingStrategy.BALANCED
                )
            
            # 3. 根据任务类型和策略选择最优提供商
            routing_decision = await self._make_routing_decision(request, available_providers)
            
            # 4. 成本控制检查
            cost_check_result = await self._perform_cost_control_check(
                routing_decision.selected_provider, request, routing_decision.estimated_cost
            )
            
            if not cost_check_result["allowed"]:
                # 如果成本控制不允许，尝试选择更便宜的提供商
                alternative_decision = await self._find_cost_effective_alternative(
                    request, available_providers, cost_check_result["alerts"]
                )
                if alternative_decision:
                    routing_decision = alternative_decision
                else:
                    # 如果没有替代方案，返回拒绝决策
                    return RoutingDecision(
                        selected_provider=routing_decision.selected_provider,
                        confidence=0.0,
                        reasoning=f"Request blocked by cost control: {cost_check_result['reason']}",
                        fallback_providers=[],
                        estimated_cost=routing_decision.estimated_cost,
                        estimated_time=0.0,
                        routing_strategy_used=RoutingStrategy.COST_FIRST
                    )
            
            # 5. 更新负载均衡状态
            await self._update_load_balancer(routing_decision.selected_provider)
            
            self.logger.info(
                f"Selected provider: {routing_decision.selected_provider.value} "
                f"(confidence: {routing_decision.confidence:.2f}, "
                f"strategy: {routing_decision.routing_strategy_used.value}, "
                f"estimated_cost: ${routing_decision.estimated_cost:.4f})"
            )
            
            return routing_decision
            
        except Exception as e:
            self.logger.error(f"Error routing AI request {request.request_id}: {str(e)}")
            return RoutingDecision(
                selected_provider=AIProvider.OPENAI,
                confidence=0.1,
                reasoning=f"Error in routing: {str(e)}",
                fallback_providers=[],
                estimated_cost=0.0,
                estimated_time=0.0,
                routing_strategy_used=RoutingStrategy.BALANCED
            )
    
    async def route_request_with_failover(self, request: AIRequest, max_retries: int = 3) -> RoutingDecision:
        """
        带故障转移的智能路由AI请求
        
        Args:
            request: AI请求对象
            max_retries: 最大重试次数
            
        Returns:
            RoutingDecision: 路由决策结果
        """
        original_request_id = request.request_id
        retry_count = 0
        last_error = None
        failed_providers = set()
        
        while retry_count <= max_retries:
            try:
                # 获取路由决策
                routing_decision = await self.route_request(request)
                
                # 如果选择的提供商已经失败过，尝试故障转移
                if routing_decision.selected_provider in failed_providers:
                    self.logger.warning(
                        f"Provider {routing_decision.selected_provider.value} previously failed, "
                        f"attempting failover for request {original_request_id}"
                    )
                    
                    # 尝试故障转移
                    failover_decision = await self._attempt_failover(
                        request, routing_decision, failed_providers
                    )
                    
                    if failover_decision:
                        routing_decision = failover_decision
                    else:
                        # 如果故障转移失败，记录错误并继续
                        self.logger.error(
                            f"Failover failed for request {original_request_id}, "
                            f"no alternative providers available"
                        )
                        break
                
                # 模拟AI服务调用（在实际实现中，这里会调用真实的AI服务）
                success = await self._simulate_ai_service_call(
                    routing_decision.selected_provider, request
                )
                
                if success:
                    # 成功处理，更新提供商健康状态
                    await self._update_provider_health_on_success(routing_decision.selected_provider)
                    
                    routing_decision.reasoning += f" (Completed after {retry_count} retries)"
                    self.logger.info(
                        f"Request {original_request_id} successfully processed by "
                        f"{routing_decision.selected_provider.value} after {retry_count} retries"
                    )
                    return routing_decision
                else:
                    # 处理失败，标记提供商为失败状态
                    failed_providers.add(routing_decision.selected_provider)
                    await self._update_provider_health_on_failure(
                        routing_decision.selected_provider, "Service call failed"
                    )
                    
                    last_error = f"Provider {routing_decision.selected_provider.value} failed to process request"
                    self.logger.warning(
                        f"Provider {routing_decision.selected_provider.value} failed for request "
                        f"{original_request_id}, retry {retry_count + 1}/{max_retries + 1}"
                    )
                
            except Exception as e:
                last_error = str(e)
                self.logger.error(
                    f"Error in failover routing for request {original_request_id}, "
                    f"retry {retry_count + 1}/{max_retries + 1}: {str(e)}"
                )
            
            retry_count += 1
            
            # 在重试之间添加延迟
            if retry_count <= max_retries:
                delay = min(2 ** retry_count, 10)  # 指数退避，最大10秒
                await asyncio.sleep(delay)
        
        # 所有重试都失败了，返回失败决策
        self.logger.error(
            f"All failover attempts failed for request {original_request_id} "
            f"after {retry_count} retries. Failed providers: {failed_providers}"
        )
        
        return RoutingDecision(
            selected_provider=AIProvider.OPENAI,  # 默认提供商
            confidence=0.0,
            reasoning=f"All failover attempts failed: {last_error}. Failed providers: {list(failed_providers)}",
            fallback_providers=[],
            estimated_cost=0.0,
            estimated_time=0.0,
            routing_strategy_used=RoutingStrategy.BALANCED
        )
    
    async def _attempt_failover(self, request: AIRequest, 
                               original_decision: RoutingDecision,
                               failed_providers: set) -> Optional[RoutingDecision]:
        """
        尝试故障转移到备用提供商
        
        Args:
            request: AI请求对象
            original_decision: 原始路由决策
            failed_providers: 已失败的提供商集合
            
        Returns:
            Optional[RoutingDecision]: 故障转移决策，如果没有可用的备用提供商则返回None
        """
        self.logger.info(
            f"Attempting failover for request {request.request_id}, "
            f"original provider: {original_decision.selected_provider.value}"
        )
        
        # 1. 从fallback_providers中选择可用的提供商
        available_fallbacks = [
            provider for provider in original_decision.fallback_providers
            if provider not in failed_providers
        ]
        
        if available_fallbacks:
            # 选择第一个可用的备用提供商
            fallback_provider = available_fallbacks[0]
            
            # 检查备用提供商的可用性
            if await self._check_provider_availability(fallback_provider, request):
                self.logger.info(
                    f"Failover to {fallback_provider.value} for request {request.request_id}"
                )
                
                # 创建新的路由决策
                estimated_cost = await self._estimate_cost(fallback_provider, request)
                estimated_time = await self._estimate_response_time(fallback_provider, request)
                
                return RoutingDecision(
                    selected_provider=fallback_provider,
                    confidence=original_decision.confidence * 0.8,  # 降低置信度
                    reasoning=f"Failover from {original_decision.selected_provider.value} to {fallback_provider.value}",
                    fallback_providers=available_fallbacks[1:],  # 剩余的备用提供商
                    estimated_cost=estimated_cost,
                    estimated_time=estimated_time,
                    routing_strategy_used=original_decision.routing_strategy_used
                )
        
        # 2. 如果没有可用的备用提供商，重新进行路由决策，排除失败的提供商
        self.logger.info(
            f"No available fallback providers, attempting re-routing for request {request.request_id}"
        )
        
        available_providers = await self._get_available_providers(request)
        available_providers = [
            provider for provider in available_providers
            if provider not in failed_providers
        ]
        
        if not available_providers:
            self.logger.warning(
                f"No available providers for failover, request {request.request_id}"
            )
            return None
        
        # 重新进行路由决策
        try:
            failover_decision = await self._make_routing_decision(request, available_providers)
            failover_decision.reasoning = f"Failover re-routing: {failover_decision.reasoning}"
            
            self.logger.info(
                f"Re-routing failover selected {failover_decision.selected_provider.value} "
                f"for request {request.request_id}"
            )
            
            return failover_decision
            
        except Exception as e:
            self.logger.error(f"Error in failover re-routing: {str(e)}")
            return None
    
    async def _simulate_ai_service_call(self, provider: AIProvider, request: AIRequest) -> bool:
        """
        模拟AI服务调用（在实际实现中，这里会调用真实的AI服务）
        
        Args:
            provider: AI服务提供商
            request: AI请求对象
            
        Returns:
            bool: 是否成功
        """
        # 模拟不同提供商的成功率
        import random
        
        health = self.provider_health.get(provider)
        if not health:
            return False
        
        # 基于提供商健康状态模拟成功率
        success_probability = health.success_rate
        
        # 添加一些随机性来模拟真实的网络和服务波动
        random_factor = random.uniform(0.8, 1.2)
        adjusted_probability = min(success_probability * random_factor, 1.0)
        
        # 模拟处理时间
        processing_time = random.uniform(0.5, 3.0)
        await asyncio.sleep(processing_time / 10)  # 缩短模拟时间
        
        success = random.random() < adjusted_probability
        
        self.logger.debug(
            f"Simulated AI call to {provider.value}: "
            f"success={success}, probability={adjusted_probability:.2f}"
        )
        
        return success
    
    async def _update_provider_health_on_success(self, provider: AIProvider):
        """
        在成功处理后更新提供商健康状态
        
        Args:
            provider: AI服务提供商
        """
        health = self.provider_health.get(provider)
        if health:
            # 提高成功率（使用指数移动平均）
            health.success_rate = min(health.success_rate * 0.9 + 0.1, 1.0)
            
            # 重置错误计数
            health.error_count = max(health.error_count - 1, 0)
            
            # 标记为可用
            health.is_available = True
            
            # 更新最后检查时间
            health.last_check = datetime.utcnow()
            
            self.logger.debug(
                f"Updated {provider.value} health on success: "
                f"success_rate={health.success_rate:.3f}, error_count={health.error_count}"
            )
    
    async def _update_provider_health_on_failure(self, provider: AIProvider, error_message: str):
        """
        在处理失败后更新提供商健康状态
        
        Args:
            provider: AI服务提供商
            error_message: 错误信息
        """
        health = self.provider_health.get(provider)
        if health:
            # 降低成功率
            health.success_rate = max(health.success_rate * 0.8, 0.1)
            
            # 增加错误计数
            health.error_count += 1
            
            # 如果错误过多，标记为不可用
            if health.error_count >= 5:
                health.is_available = False
                self.logger.warning(
                    f"Provider {provider.value} marked as unavailable due to high error count: "
                    f"{health.error_count}"
                )
            
            # 更新最后检查时间
            health.last_check = datetime.utcnow()
            
            self.logger.warning(
                f"Updated {provider.value} health on failure: "
                f"success_rate={health.success_rate:.3f}, error_count={health.error_count}, "
                f"available={health.is_available}, error='{error_message}'"
            )
    
    async def start_health_monitoring(self):
        """启动提供商健康监控"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self.logger.info("Started provider health monitoring")
    
    async def stop_health_monitoring(self):
        """停止提供商健康监控"""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self.logger.info("Stopped provider health monitoring")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {str(e)}")
    
    async def _perform_health_checks(self):
        """执行所有提供商的健康检查"""
        self.logger.debug("Performing provider health checks")
        
        # 并发检查所有提供商
        tasks = []
        for provider in self.provider_health.keys():
            task = asyncio.create_task(self._check_provider_health(provider))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_provider_health(self, provider: AIProvider):
        """
        检查单个提供商的健康状态
        
        Args:
            provider: AI服务提供商
        """
        health = self.provider_health.get(provider)
        if not health:
            return
        
        try:
            # 模拟健康检查（在实际实现中，这里会发送ping请求到AI服务）
            is_healthy = await self._ping_provider(provider)
            
            if is_healthy:
                # 提供商健康，更新状态
                if not health.is_available:
                    # 如果之前不可用，现在恢复了
                    health.is_available = True
                    health.error_count = 0
                    health.success_rate = min(health.success_rate + 0.1, 1.0)
                    
                    self.logger.info(
                        f"Provider {provider.value} recovered and is now available"
                    )
                
                # 更新响应时间（模拟）
                health.response_time = random.uniform(0.5, 2.0)
                
            else:
                # 提供商不健康
                health.error_count += 1
                health.success_rate = max(health.success_rate - 0.1, 0.0)
                
                # 如果错误次数超过阈值，标记为不可用
                if health.error_count >= self.failover_config["failure_threshold"]:
                    if health.is_available:
                        health.is_available = False
                        self.logger.warning(
                            f"Provider {provider.value} marked as unavailable due to "
                            f"health check failures: {health.error_count}"
                        )
            
            # 更新最后检查时间
            health.last_check = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error checking health for provider {provider.value}: {str(e)}")
            
            # 健康检查异常也算作失败
            health.error_count += 1
            if health.error_count >= self.failover_config["failure_threshold"]:
                health.is_available = False
    
    async def _ping_provider(self, provider: AIProvider) -> bool:
        """
        Ping提供商检查可用性（模拟实现）
        
        Args:
            provider: AI服务提供商
            
        Returns:
            bool: 是否可用
        """
        try:
            # 模拟网络延迟和服务响应
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            # 模拟不同提供商的可用性
            availability_rates = {
                AIProvider.OPENAI: 0.95,
                AIProvider.ANTHROPIC: 0.93,
                AIProvider.GOOGLE_GEMINI: 0.90,
                AIProvider.BAIDU_WENXIN: 0.88,
                AIProvider.ALIYUN_TONGYI: 0.85,
                AIProvider.ZHIPU_CHATGLM: 0.82,
                AIProvider.XUNFEI_XINGHUO: 0.80,
            }
            
            base_availability = availability_rates.get(provider, 0.85)
            
            # 添加一些随机波动
            current_availability = base_availability + random.uniform(-0.1, 0.1)
            current_availability = max(0.0, min(current_availability, 1.0))
            
            return random.random() < current_availability
            
        except Exception as e:
            self.logger.error(f"Error pinging provider {provider.value}: {str(e)}")
            return False
    
    async def get_provider_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有提供商的健康状态
        
        Returns:
            Dict[str, Dict[str, Any]]: 提供商健康状态信息
        """
        health_status = {}
        
        for provider, health in self.provider_health.items():
            health_status[provider.value] = {
                "is_available": health.is_available,
                "success_rate": health.success_rate,
                "error_count": health.error_count,
                "response_time": health.response_time,
                "current_load": health.current_load,
                "max_concurrent": health.max_concurrent,
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "quota_remaining": health.quota_remaining,
                "cost_per_token": health.cost_per_token
            }
        
        return health_status
    
    async def manually_mark_provider_status(self, provider: AIProvider, 
                                          is_available: bool, reason: str = ""):
        """
        手动标记提供商状态
        
        Args:
            provider: AI服务提供商
            is_available: 是否可用
            reason: 标记原因
        """
        health = self.provider_health.get(provider)
        if health:
            old_status = health.is_available
            health.is_available = is_available
            
            if is_available:
                health.error_count = 0
                health.success_rate = min(health.success_rate + 0.2, 1.0)
            else:
                health.error_count = self.failover_config["failure_threshold"]
                health.success_rate = max(health.success_rate - 0.3, 0.0)
            
            health.last_check = datetime.utcnow()
            
            self.logger.info(
                f"Manually marked provider {provider.value} as "
                f"{'available' if is_available else 'unavailable'} "
                f"(was {'available' if old_status else 'unavailable'}). Reason: {reason}"
            )
    
    async def get_failover_statistics(self) -> Dict[str, Any]:
        """
        获取故障转移统计信息
        
        Returns:
            Dict[str, Any]: 故障转移统计
        """
        total_providers = len(self.provider_health)
        available_providers = sum(1 for h in self.provider_health.values() if h.is_available)
        unavailable_providers = total_providers - available_providers
        
        # 计算平均成功率
        success_rates = [h.success_rate for h in self.provider_health.values()]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
        
        # 计算平均响应时间
        response_times = [h.response_time for h in self.provider_health.values() if h.response_time > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        # 获取错误最多的提供商
        most_errors_provider = None
        max_errors = 0
        for provider, health in self.provider_health.items():
            if health.error_count > max_errors:
                max_errors = health.error_count
                most_errors_provider = provider.value
        
        return {
            "total_providers": total_providers,
            "available_providers": available_providers,
            "unavailable_providers": unavailable_providers,
            "availability_rate": available_providers / total_providers if total_providers > 0 else 0.0,
            "average_success_rate": avg_success_rate,
            "average_response_time": avg_response_time,
            "most_errors_provider": most_errors_provider,
            "max_error_count": max_errors,
            "health_check_interval": self._health_check_interval,
            "failover_config": self.failover_config,
            "last_health_check": max(
                (h.last_check for h in self.provider_health.values() if h.last_check),
                default=None
            )
        }
    
    async def queue_request_with_failover(self, user_id: int, content: str, 
                                        priority: str = "normal", 
                                        timeout_seconds: int = 300,
                                        context: Optional[Dict[str, Any]] = None) -> str:
        """
        将请求加入队列并启用故障转移
        
        Args:
            user_id: 用户ID
            content: 请求内容
            priority: 优先级
            timeout_seconds: 超时时间
            context: 上下文信息
            
        Returns:
            str: 请求ID
        """
        # 转换优先级
        priority_map = {
            "low": RequestPriority.LOW,
            "normal": RequestPriority.NORMAL,
            "high": RequestPriority.HIGH,
            "urgent": RequestPriority.URGENT,
            "critical": RequestPriority.CRITICAL
        }
        
        queue_priority = priority_map.get(priority.lower(), RequestPriority.NORMAL)
        
        # 添加故障转移标记到上下文
        if context is None:
            context = {}
        context["failover_enabled"] = True
        context["max_retries"] = self.failover_config["max_retries"]
        
        # 注册故障转移回调
        async def failover_callback(request: QueuedRequest, result: Any, error: Optional[str]):
            if error and context.get("failover_enabled"):
                # 如果处理失败且启用了故障转移，尝试重新路由
                await self._handle_request_failure_with_failover(request, error)
        
        # 将请求加入队列
        request_id = await self.request_queue.enqueue_request(
            user_id=user_id,
            content=content,
            priority=queue_priority,
            timeout_seconds=timeout_seconds,
            context=context,
            callback=failover_callback
        )
        
        self.logger.info(
            f"Queued request {request_id} with failover enabled, priority: {priority}"
        )
        
        return request_id
    
    async def _handle_request_failure_with_failover(self, request: QueuedRequest, error: str):
        """
        处理请求失败并尝试故障转移
        
        Args:
            request: 失败的请求
            error: 错误信息
        """
        self.logger.warning(
            f"Handling request failure with failover for request {request.request_id}: {error}"
        )
        
        # 检查是否还有重试机会
        if request.retry_count >= request.max_retries:
            self.logger.error(
                f"Request {request.request_id} exceeded max retries ({request.max_retries}), "
                f"failover aborted"
            )
            return
        
        # 标记当前分配的提供商为有问题的
        if request.assigned_provider:
            provider_enum = None
            for p in AIProvider:
                if p.value == request.assigned_provider:
                    provider_enum = p
                    break
            
            if provider_enum:
                await self._update_provider_health_on_failure(provider_enum, error)
        
        # 重新将请求加入队列进行故障转移
        try:
            # 增加重试计数
            request.retry_count += 1
            request.status = RequestStatus.PENDING
            request.assigned_provider = None
            request.started_at = None
            request.error_message = None
            
            # 添加故障转移信息到上下文
            if "failover_attempts" not in request.context:
                request.context["failover_attempts"] = []
            
            request.context["failover_attempts"].append({
                "failed_provider": request.assigned_provider,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
                "retry_count": request.retry_count
            })
            
            # 重新加入队列
            await self.request_queue.enqueue_request(
                user_id=request.user_id,
                content=request.content,
                priority=request.priority,
                timeout_seconds=request.timeout_seconds,
                max_retries=request.max_retries,
                context=request.context
            )
            
            self.logger.info(
                f"Request {request.request_id} re-queued for failover, "
                f"retry {request.retry_count}/{request.max_retries}"
            )
            
        except Exception as e:
            self.logger.error(
                f"Error re-queueing request {request.request_id} for failover: {str(e)}"
            )
    
    async def process_queued_request_with_failover(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        从队列中处理请求并支持故障转移
        
        Args:
            provider_id: 提供商ID
            
        Returns:
            Optional[Dict[str, Any]]: 处理的请求信息
        """
        # 检查提供商是否可用
        provider_enum = None
        for p in AIProvider:
            if p.value == provider_id:
                provider_enum = p
                break
        
        if provider_enum:
            health = self.provider_health.get(provider_enum)
            if health and not health.is_available:
                self.logger.warning(
                    f"Provider {provider_id} is marked as unavailable, skipping queue processing"
                )
                return None
        
        # 从队列中获取请求
        request = await self.request_queue.dequeue_request(provider_id)
        if not request:
            return None
        
        # 创建AI请求对象
        ai_request = AIRequest(
            content=request.content,
            user_id=request.user_id,
            context=request.context,
            priority=request.priority.name.lower()
        )
        
        try:
            # 使用故障转移路由处理请求
            routing_decision = await self.route_request_with_failover(
                ai_request, 
                max_retries=request.context.get("max_retries", self.failover_config["max_retries"])
            )
            
            if routing_decision.confidence > 0:
                # 处理成功
                await self.request_queue.complete_request(
                    request.request_id,
                    result={
                        "provider": routing_decision.selected_provider.value,
                        "confidence": routing_decision.confidence,
                        "reasoning": routing_decision.reasoning,
                        "estimated_cost": routing_decision.estimated_cost
                    }
                )
                
                self.logger.info(
                    f"Successfully processed queued request {request.request_id} "
                    f"with provider {routing_decision.selected_provider.value}"
                )
                
                return {
                    "request_id": request.request_id,
                    "ai_request": ai_request,
                    "routing_decision": routing_decision,
                    "priority": request.priority.name,
                    "failover_attempts": request.context.get("failover_attempts", [])
                }
            else:
                # 处理失败
                error_msg = f"Failover routing failed: {routing_decision.reasoning}"
                await self.request_queue.complete_request(
                    request.request_id,
                    error=error_msg
                )
                
                self.logger.error(
                    f"Failed to process queued request {request.request_id}: {error_msg}"
                )
                
                return None
                
        except Exception as e:
            error_msg = f"Error processing queued request: {str(e)}"
            await self.request_queue.complete_request(request.request_id, error=error_msg)
            
            self.logger.error(
                f"Exception processing queued request {request.request_id}: {str(e)}"
            )
            
            return None
    
    def _analyze_task_type(self, request: AIRequest) -> TaskType:
        """
        分析任务类型 - 使用更智能的分析算法，集成中文内容优化
        
        Args:
            request: AI请求对象
            
        Returns:
            TaskType: 任务类型
        """
        content = request.content.lower()
        content_length = len(request.content)
        
        # 1. 首先检查是否为中文内容
        is_chinese = self.chinese_router.is_chinese_content(request.content, threshold=0.3)
        
        if is_chinese:
            # 对中文内容进行详细分析
            chinese_analysis = self.chinese_router.analyze_chinese_content(request.content)
            
            # 根据中文内容分析结果确定任务类型
            if chinese_analysis.domain == "软件开发":
                return TaskType.CODE_GENERATION
            elif chinese_analysis.domain == "测试管理":
                return TaskType.TEST_CASE_GENERATION
            elif chinese_analysis.content_type.value in ["technical_chinese", "business_chinese"]:
                return TaskType.DOCUMENT_WRITING
            elif chinese_analysis.content_type.value == "literary_chinese":
                return TaskType.CREATIVE_WRITING
            elif len(chinese_analysis.technical_terms) > 5:
                return TaskType.COMPLEX_ANALYSIS
            else:
                return TaskType.CHINESE_CONTENT
        
        # 2. 非中文内容的传统分析方法
        # 关键词权重分析
        keyword_scores = {
            TaskType.TEST_CASE_GENERATION: self._calculate_keyword_score(content, [
                "测试", "用例", "test", "case", "验证", "检查", "场景", "步骤", "预期", "断言"
            ]),
            TaskType.CODE_GENERATION: self._calculate_keyword_score(content, [
                "代码", "编程", "code", "program", "函数", "方法", "class", "def", "function", "算法", "python", "java", "javascript"
            ]),
            TaskType.DOCUMENT_WRITING: self._calculate_keyword_score(content, [
                "文档", "报告", "document", "report", "说明", "手册", "指南", "总结", "记录"
            ]),
            TaskType.DATA_ANALYSIS: self._calculate_keyword_score(content, [
                "数据", "分析", "统计", "图表", "data", "analysis", "chart", "统计", "趋势"
            ]),
            TaskType.CREATIVE_WRITING: self._calculate_keyword_score(content, [
                "创作", "写作", "故事", "小说", "诗歌", "创意", "想象", "文学", "narrative"
            ]),
            TaskType.TRANSLATION: self._calculate_keyword_score(content, [
                "翻译", "translate", "转换", "语言", "英文", "中文", "日文", "韩文"
            ])
        }
        
        # 特殊模式检测
        if "def " in content or "function" in content or "class " in content or "```" in content:
            keyword_scores[TaskType.CODE_GENERATION] += 0.5
        
        # 基于内容长度的初步判断
        if content_length > 3000:
            base_type = TaskType.COMPLEX_ANALYSIS
        elif content_length < 50:
            base_type = TaskType.SIMPLE_QUERY
        else:
            base_type = TaskType.GENERAL_TASK
        
        # 找到得分最高的任务类型
        max_score = max(keyword_scores.values()) if keyword_scores else 0
        if max_score > 0.3:  # 阈值
            for task_type, score in keyword_scores.items():
                if score == max_score:
                    return task_type
        
        return base_type
    
    async def _perform_cost_control_check(self, provider: AIProvider, request: AIRequest, estimated_cost: float) -> Dict[str, Any]:
        """
        执行成本控制检查
        
        Args:
            provider: AI服务提供商
            request: AI请求对象
            estimated_cost: 预估成本
            
        Returns:
            Dict[str, Any]: 成本控制检查结果
        """
        try:
            # 使用成本控制服务检查
            estimated_tokens = len(request.content) // 4  # 粗略估算token数
            quota_allowed, alerts = await self.cost_control.check_usage_quotas(
                provider.value, request.user_id, estimated_tokens
            )
            
            budget_allowed, budget_alerts = await self.cost_control.check_budget_limits(
                provider.value, request.user_id, estimated_cost
            )
            
            allowed = quota_allowed and budget_allowed
            all_alerts = alerts + budget_alerts
            
            return {
                "allowed": allowed,
                "alerts": all_alerts,
                "reason": "; ".join(all_alerts) if all_alerts else "Cost control passed"
            }
            
        except Exception as e:
            self.logger.error(f"Error in cost control check: {str(e)}")
            return {
                "allowed": True,  # 默认允许，避免因成本控制错误阻塞请求
                "alerts": [],
                "reason": f"Cost control check failed: {str(e)}"
            }
    
    async def _find_cost_effective_alternative(self, request: AIRequest, 
                                             available_providers: List[AIProvider],
                                             cost_alerts: List[str]) -> Optional[RoutingDecision]:
        """
        寻找成本效益更好的替代提供商
        
        Args:
            request: AI请求对象
            available_providers: 可用的提供商列表
            cost_alerts: 成本告警信息
            
        Returns:
            Optional[RoutingDecision]: 替代路由决策
        """
        # 按成本从低到高排序提供商
        provider_costs = []
        for provider in available_providers:
            cost = await self._estimate_cost(provider, request)
            provider_costs.append((provider, cost))
        
        provider_costs.sort(key=lambda x: x[1])  # 按成本排序
        
        # 尝试找到成本可接受的提供商
        for provider, cost in provider_costs:
            cost_check = await self._perform_cost_control_check(provider, request, cost)
            if cost_check["allowed"]:
                # 找到可接受的替代方案
                estimated_time = await self._estimate_response_time(provider, request)
                
                return RoutingDecision(
                    selected_provider=provider,
                    confidence=0.7,  # 降低置信度，因为不是最优选择
                    reasoning=f"Cost-effective alternative due to budget constraints: {'; '.join(cost_alerts)}",
                    fallback_providers=[p for p, _ in provider_costs if p != provider][:2],
                    estimated_cost=cost,
                    estimated_time=estimated_time,
                    routing_strategy_used=RoutingStrategy.COST_FIRST
                )
        
        return None
    
    async def _update_load_balancer(self, provider: AIProvider):
        """
        更新负载均衡状态
        
        Args:
            provider: AI服务提供商
        """
        # 增加提供商负载计数
        self.load_balancer_state[provider] = self.load_balancer_state.get(provider, 0) + 1
        
        # 更新健康状态中的当前负载
        health = self.provider_health.get(provider)
        if health:
            health.current_load += 1
        
        self.logger.debug(f"Updated load for provider {provider.value}: {self.load_balancer_state[provider]}")
    
    def _create_fallback_decision(self, reason: str) -> RoutingDecision:
        """
        创建后备路由决策
        
        Args:
            reason: 后备原因
            
        Returns:
            RoutingDecision: 后备路由决策
        """
        return RoutingDecision(
            selected_provider=AIProvider.OPENAI,  # 默认提供商
            confidence=0.1,
            reasoning=f"Fallback decision: {reason}",
            fallback_providers=[],
            estimated_cost=0.0,
            estimated_time=0.0,
            routing_strategy_used=RoutingStrategy.BALANCED
        )
    
    async def _estimate_cost(self, provider: AIProvider, request: AIRequest) -> float:
        """
        估算请求成本
        
        Args:
            provider: AI服务提供商
            request: AI请求对象
            
        Returns:
            float: 预估成本（美元）
        """
        # 估算token数量
        estimated_tokens = len(request.content) // 4  # 粗略估算
        if request.max_tokens:
            estimated_tokens += request.max_tokens
        else:
            estimated_tokens += 1000  # 默认输出token数
        
        # 获取提供商成本
        health = self.provider_health.get(provider)
        cost_per_token = health.cost_per_token if health else 0.001
        
        return estimated_tokens * cost_per_token
    
    async def _estimate_response_time(self, provider: AIProvider, request: AIRequest) -> float:
        """
        估算响应时间
        
        Args:
            provider: AI服务提供商
            request: AI请求对象
            
        Returns:
            float: 预估响应时间（秒）
        """
        # 基础响应时间
        health = self.provider_health.get(provider)
        base_time = health.response_time if health else 2.0
        
        # 根据内容长度调整
        content_factor = min(len(request.content) / 1000, 2.0)  # 最多增加2倍
        
        # 根据当前负载调整
        load_factor = 1.0
        if health:
            load_ratio = health.current_load / health.max_concurrent
            load_factor = 1.0 + load_ratio * 0.5  # 负载越高，时间越长
        
        return base_time * (1.0 + content_factor) * load_factor
    
    def _get_provider_max_tokens(self, provider: AIProvider) -> int:
        """
        获取提供商最大token限制
        
        Args:
            provider: AI服务提供商
            
        Returns:
            int: 最大token数
        """
        max_tokens_map = {
            AIProvider.OPENAI: 8000,
            AIProvider.ANTHROPIC: 100000,
            AIProvider.GOOGLE_GEMINI: 32000,
            AIProvider.BAIDU_WENXIN: 8000,
            AIProvider.ALIYUN_TONGYI: 6000,
            AIProvider.ZHIPU_CHATGLM: 8000,
            AIProvider.XUNFEI_XINGHUO: 4000,
        }
        return max_tokens_map.get(provider, 4000)
    
    def _is_task_supported(self, provider: AIProvider, task_type: TaskType) -> bool:
        """
        检查提供商是否支持特定任务类型
        
        Args:
            provider: AI服务提供商
            task_type: 任务类型
            
        Returns:
            bool: 是否支持
        """
        # 所有提供商都支持基本任务类型
        basic_tasks = {
            TaskType.SIMPLE_QUERY, TaskType.GENERAL_TASK, 
            TaskType.CHINESE_CONTENT, TaskType.DOCUMENT_WRITING
        }
        
        if task_type in basic_tasks:
            return True
        
        # 特定任务类型的支持情况
        task_support = {
            TaskType.CODE_GENERATION: {
                AIProvider.OPENAI, AIProvider.ANTHROPIC, AIProvider.GOOGLE_GEMINI
            },
            TaskType.COMPLEX_ANALYSIS: {
                AIProvider.OPENAI, AIProvider.ANTHROPIC, AIProvider.GOOGLE_GEMINI
            },
            TaskType.DATA_ANALYSIS: {
                AIProvider.OPENAI, AIProvider.GOOGLE_GEMINI, AIProvider.ANTHROPIC
            }
        }
        
        supported_providers = task_support.get(task_type, set(AIProvider))
        return provider in supported_providers
    
    def _requires_chinese_support(self, request: AIRequest) -> bool:
        """
        检查请求是否需要中文支持
        
        Args:
            request: AI请求对象
            
        Returns:
            bool: 是否需要中文支持
        """
        chinese_chars = len([c for c in request.content if '\u4e00' <= c <= '\u9fff'])
        chinese_ratio = chinese_chars / len(request.content) if len(request.content) > 0 else 0
        return chinese_ratio > 0.3
    
    def _get_task_specific_score(self, provider: AIProvider, task_type: TaskType) -> float:
        """
        获取提供商针对特定任务类型的能力得分
        
        Args:
            provider: AI服务提供商
            task_type: 任务类型
            
        Returns:
            float: 能力得分 (0.0-1.0)
        """
        capabilities = self.provider_capabilities.get(provider, {})
        
        # 任务类型到能力维度的映射
        task_capability_map = {
            TaskType.CODE_GENERATION: "code_generation",
            TaskType.CREATIVE_WRITING: "creative_writing",
            TaskType.CHINESE_CONTENT: "chinese_support",
            TaskType.COMPLEX_ANALYSIS: "reasoning",
            TaskType.DATA_ANALYSIS: "reasoning",
            TaskType.DOCUMENT_WRITING: "creative_writing",
            TaskType.TEST_CASE_GENERATION: "reasoning",
            TaskType.TRANSLATION: "chinese_support"
        }
        
        capability_key = task_capability_map.get(task_type, "accuracy")
        return capabilities.get(capability_key, 0.5)
    
    def _calculate_content_complexity(self, content: str) -> float:
        """
        计算内容复杂度
        
        Args:
            content: 内容文本
            
        Returns:
            float: 复杂度得分 (0.0-1.0)
        """
        # 基于长度的复杂度
        length_factor = min(len(content) / 2000, 1.0)
        
        # 基于特殊字符和结构的复杂度
        special_chars = len([c for c in content if not c.isalnum() and not c.isspace()])
        special_factor = min(special_chars / len(content), 0.3) if len(content) > 0 else 0
        
        # 基于代码块的复杂度
        code_blocks = content.count('```') // 2
        code_factor = min(code_blocks * 0.2, 0.3)
        
        return min(length_factor + special_factor + code_factor, 1.0)
    
    def _get_complexity_adjustment(self, provider: AIProvider, complexity: float) -> float:
        """
        根据复杂度调整提供商得分
        
        Args:
            provider: AI服务提供商
            complexity: 复杂度
            
        Returns:
            float: 调整后的得分
        """
        capabilities = self.provider_capabilities.get(provider, {})
        base_accuracy = capabilities.get("accuracy", 0.5)
        
        # 高复杂度任务更依赖准确性
        if complexity > 0.7:
            return base_accuracy
        elif complexity > 0.3:
            return base_accuracy * 0.9 + 0.1
        else:
            return base_accuracy * 0.8 + 0.2
    
    def _get_context_length_adjustment(self, provider: AIProvider, context_length: int) -> float:
        """
        根据上下文长度调整提供商得分
        
        Args:
            provider: AI服务提供商
            context_length: 上下文长度
            
        Returns:
            float: 调整后的得分
        """
        max_tokens = self._get_provider_max_tokens(provider)
        
        if context_length > max_tokens * 0.8:
            return 0.6  # 接近限制，降低得分
        elif context_length > max_tokens * 0.5:
            return 0.8  # 中等长度
        else:
            return 1.0  # 短上下文，满分
    
    def _get_priority_adjustment(self, provider: AIProvider, priority: str) -> float:
        """
        根据优先级调整提供商得分
        
        Args:
            provider: AI服务提供商
            priority: 优先级
            
        Returns:
            float: 调整后的得分
        """
        health = self.provider_health.get(provider)
        if not health:
            return 0.5
        
        # 高优先级任务更看重可靠性
        if priority in ["urgent", "critical"]:
            return health.success_rate
        elif priority == "high":
            return health.success_rate * 0.9 + 0.1
        else:
            return health.success_rate * 0.7 + 0.3
    
    def _get_strategy_weights(self, strategy: RoutingStrategy, request: AIRequest) -> Dict[str, float]:
        """
        根据路由策略获取权重配置
        
        Args:
            strategy: 路由策略
            request: AI请求对象
            
        Returns:
            Dict[str, float]: 权重配置
        """
        if strategy == RoutingStrategy.ACCURACY_FIRST:
            return {"task": 0.6, "performance": 0.3, "cost": 0.1}
        elif strategy == RoutingStrategy.COST_FIRST:
            return {"task": 0.2, "performance": 0.2, "cost": 0.6}
        elif strategy == RoutingStrategy.SPEED_FIRST:
            return {"task": 0.3, "performance": 0.6, "cost": 0.1}
        elif strategy == RoutingStrategy.LOAD_BALANCED:
            return {"task": 0.3, "performance": 0.5, "cost": 0.2}
        else:  # BALANCED
            return {"task": 0.4, "performance": 0.4, "cost": 0.2}
    
    def _generate_enhanced_reasoning(self, selected_provider: AIProvider, 
                                   request: AIRequest, strategy: RoutingStrategy,
                                   confidence: float, task_scores: Dict[AIProvider, float],
                                   performance_scores: Dict[AIProvider, float],
                                   cost_scores: Dict[AIProvider, float]) -> str:
        """
        生成详细的路由决策理由
        
        Args:
            selected_provider: 选择的提供商
            request: AI请求对象
            strategy: 路由策略
            confidence: 置信度
            task_scores: 任务能力得分
            performance_scores: 性能得分
            cost_scores: 成本得分
            
        Returns:
            str: 决策理由
        """
        task_score = task_scores.get(selected_provider, 0.0)
        perf_score = performance_scores.get(selected_provider, 0.0)
        cost_score = cost_scores.get(selected_provider, 0.0)
        
        reasoning_parts = [
            f"Selected {selected_provider.value} for {request.task_type.value if request.task_type else 'general'} task",
            f"Strategy: {strategy.value}",
            f"Scores - Task: {task_score:.2f}, Performance: {perf_score:.2f}, Cost: {cost_score:.2f}",
            f"Overall confidence: {confidence:.2f}"
        ]
        
        # 添加特定的决策因素
        if strategy == RoutingStrategy.ACCURACY_FIRST:
            reasoning_parts.append("Prioritized accuracy and task-specific capabilities")
        elif strategy == RoutingStrategy.COST_FIRST:
            reasoning_parts.append("Prioritized cost-effectiveness")
        elif strategy == RoutingStrategy.SPEED_FIRST:
            reasoning_parts.append("Prioritized response speed and low latency")
        
        # 添加健康状态信息
        health = self.provider_health.get(selected_provider)
        if health:
            reasoning_parts.append(
                f"Provider health: {health.success_rate:.2f} success rate, "
                f"{health.current_load}/{health.max_concurrent} load"
            )
        
        return "; ".join(reasoning_parts)
    
    # Add missing methods that are referenced in the existing code
    async def start_queue_service(self):
        """启动队列服务"""
        if hasattr(self, 'request_queue') and self.request_queue:
            await self.request_queue.start()
        await self.start_health_monitoring()
        self.logger.info("AI Router queue service started")
    
    async def stop_queue_service(self):
        """停止队列服务"""
        if hasattr(self, 'request_queue') and self.request_queue:
            await self.request_queue.stop()
        await self.stop_health_monitoring()
        self.logger.info("AI Router queue service stopped")
    
    async def queue_request(self, user_id: int, content: str, priority: str = "normal", 
                          timeout_seconds: int = 300, context: Optional[Dict[str, Any]] = None) -> str:
        """将请求加入队列（兼容性方法）"""
        return await self.queue_request_with_failover(user_id, content, priority, timeout_seconds, context)
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        if not hasattr(self, 'request_queue') or not self.request_queue:
            return {
                "queue_metrics": {"pending_requests": 0, "processing_requests": 0},
                "provider_loads": {}
            }
        
        metrics = await self.request_queue.get_queue_metrics()
        
        return {
            "queue_metrics": {
                "total_requests": metrics.total_requests,
                "pending_requests": metrics.pending_requests,
                "processing_requests": metrics.processing_requests,
                "completed_requests": metrics.completed_requests,
                "failed_requests": metrics.failed_requests,
                "cancelled_requests": metrics.cancelled_requests,
                "timeout_requests": metrics.timeout_requests,
                "average_wait_time": metrics.average_wait_time,
                "average_processing_time": metrics.average_processing_time,
                "throughput_per_minute": metrics.throughput_per_minute
            },
            "provider_loads": {
                provider_id: {
                    "current_load": await self.request_queue.get_provider_load(provider_id)
                } for provider_id in ["openai", "anthropic", "baidu_wenxin", "aliyun_tongyi"]
            }
        }
    
    async def process_queued_request(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """处理队列请求（兼容性方法）"""
        return await self.process_queued_request_with_failover(provider_id)
    
    async def complete_queued_request(self, request_id: str, result: Any = None, error: Optional[str] = None):
        """完成队列请求"""
        if hasattr(self, 'request_queue') and self.request_queue:
            await self.request_queue.complete_request(request_id, result, error)
    
    async def route_request_with_queue(self, request: AIRequest) -> Dict[str, Any]:
        """路由请求并加入队列"""
        # 先进行路由决策
        routing_decision = await self.route_request_with_failover(request)
        
        # 将请求加入队列
        request_id = await self.queue_request_with_failover(
            user_id=request.user_id,
            content=request.content,
            priority=request.priority,
            context=request.context
        )
        
        return {
            "request_id": request_id,
            "routing_decision": {
                "selected_provider": routing_decision.selected_provider.value,
                "confidence": routing_decision.confidence,
                "reasoning": routing_decision.reasoning,
                "estimated_cost": routing_decision.estimated_cost,
                "estimated_time": routing_decision.estimated_time
            }
        }
    
    async def get_load_balancing_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计"""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "providers": {}
        }
        
        for provider, health in self.provider_health.items():
            current_load, max_capacity = 0, 10
            if hasattr(self, 'request_queue') and self.request_queue:
                current_load, max_capacity = await self.request_queue.get_provider_load(provider.value)
            
            stats["providers"][provider.value] = {
                "load_status": {
                    "current_load": current_load,
                    "max_capacity": max_capacity,
                    "utilization_rate": (current_load / max_capacity * 100) if max_capacity > 0 else 0
                },
                "health_status": {
                    "is_available": health.is_available,
                    "success_rate": health.success_rate,
                    "error_count": health.error_count,
                    "response_time": health.response_time
                },
                "performance_score": health.success_rate * (1.0 - current_load / max_capacity) if max_capacity > 0 else health.success_rate
            }
        
        return stats
    
    def get_current_load_distribution(self) -> Dict[str, Any]:
        """获取当前负载分布"""
        distribution = {}
        
        for provider, health in self.provider_health.items():
            distribution[provider.value] = {
                "current_load": health.current_load,
                "max_concurrent": health.max_concurrent,
                "utilization_rate": (health.current_load / health.max_concurrent * 100) if health.max_concurrent > 0 else 0,
                "is_available": health.is_available,
                "success_rate": health.success_rate
            }
        
        return distribution
    
    def _calculate_keyword_score(self, content: str, keywords: List[str]) -> float:
        """计算关键词匹配得分"""
        matches = sum(1 for keyword in keywords if keyword in content)
        return matches / len(keywords) if keywords else 0.0
    
    async def _get_available_providers(self, request: AIRequest) -> List[AIProvider]:
        """
        获取可用的AI服务提供商
        
        Args:
            request: AI请求对象
            
        Returns:
            List[AIProvider]: 可用的提供商列表
        """
        available = []
        
        # 如果用户指定了首选提供商，优先检查
        if request.preferred_provider:
            if await self._check_provider_availability(request.preferred_provider, request):
                available.append(request.preferred_provider)
        
        # 检查所有其他提供商
        for provider in AIProvider:
            if provider != request.preferred_provider and provider != AIProvider.CUSTOM:
                if await self._check_provider_availability(provider, request):
                    available.append(provider)
        
        return available
    
    async def _check_provider_availability(self, provider: AIProvider, request: AIRequest) -> bool:
        """
        检查服务提供商可用性
        
        Args:
            provider: AI服务提供商
            request: AI请求对象
            
        Returns:
            bool: 是否可用
        """
        try:
            # 从数据库获取配置
            query = select(AIModelConfig).where(
                and_(
                    AIModelConfig.provider == provider.value,
                    AIModelConfig.is_enabled == True
                )
            )
            result = await self.db.execute(query)
            configs = result.scalars().all()
            
            if not configs:
                self.logger.debug(f"No enabled configs found for provider {provider.value}")
                return False
            
            # 检查健康状态
            health = self.provider_health.get(provider)
            if not health or not health.is_available:
                self.logger.debug(f"Provider {provider.value} is not healthy")
                return False
            
            # 检查负载
            if health.current_load >= health.max_concurrent:
                self.logger.debug(f"Provider {provider.value} is at max capacity")
                return False
            
            # 检查配额
            if await self._is_quota_exceeded(provider, request.user_id):
                self.logger.debug(f"Quota exceeded for provider {provider.value}")
                return False
            
            # 检查优先级限制
            if request.priority == "urgent" and health.success_rate < 0.9:
                self.logger.debug(f"Provider {provider.value} success rate too low for urgent request")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking provider availability for {provider.value}: {str(e)}")
            return False
    
    async def _is_quota_exceeded(self, provider: AIProvider, user_id: int = None) -> bool:
        """
        检查配额是否超限 - 使用新的成本控制服务
        
        Args:
            provider: AI服务提供商
            user_id: 用户ID（可选，用于检查用户级配额）
            
        Returns:
            bool: 是否超限
        """
        try:
            # 使用成本控制服务检查配额
            estimated_tokens = 1000  # 默认估算值，用于配额检查
            quota_allowed, _ = await self.cost_control.check_usage_quotas(
                provider.value, user_id or 0, estimated_tokens
            )
            
            return not quota_allowed
            
        except Exception as e:
            self.logger.error(f"Error checking quota for {provider.value}: {str(e)}")
            return False
    
    async def _make_routing_decision(self, request: AIRequest, 
                                   available_providers: List[AIProvider]) -> RoutingDecision:
        """
        制定智能路由决策 - 增强版算法，集成中文内容优化
        
        使用多层决策算法：
        1. 中文内容检测：优先使用中文优化路由
        2. 基础过滤：可用性、配额、健康状态
        3. 任务匹配：基于任务类型的能力匹配
        4. 性能评估：响应时间、成功率、负载
        5. 成本优化：基于预算和成本效益
        6. 智能权衡：多目标优化决策
        
        Args:
            request: AI请求对象
            available_providers: 可用的提供商列表
            
        Returns:
            RoutingDecision: 路由决策结果
        """
        if not available_providers:
            return self._create_fallback_decision("No providers available")
        
        # 特殊处理：中文内容优化路由
        if request.task_type == TaskType.CHINESE_CONTENT or \
           self.chinese_router.is_chinese_content(request.content, threshold=0.3):
            
            self.logger.info(f"Applying Chinese content optimization routing for request {request.request_id}")
            
            # 使用中文内容路由器
            available_provider_names = [provider.value for provider in available_providers]
            chinese_decision = self.chinese_router.route_chinese_content(
                request.content, 
                available_provider_names,
                priority="quality" if request.routing_strategy == RoutingStrategy.ACCURACY_FIRST else "cost"
            )
            
            # 转换中文路由决策为标准路由决策
            try:
                selected_provider = AIProvider(chinese_decision.recommended_provider)
                if selected_provider in available_providers:
                    
                    # 估算成本和时间
                    estimated_cost = await self._estimate_cost(selected_provider, request)
                    estimated_time = await self._estimate_response_time(selected_provider, request)
                    
                    # 获取备选提供商
                    fallback_providers = [p for p in available_providers if p != selected_provider]
                    
                    return RoutingDecision(
                        selected_provider=selected_provider,
                        confidence=chinese_decision.confidence,
                        reasoning=f"Chinese content optimization: {chinese_decision.reasoning}",
                        fallback_providers=fallback_providers[:3],  # 最多3个备选
                        estimated_cost=estimated_cost,
                        estimated_time=estimated_time,
                        routing_strategy_used=RoutingStrategy.ACCURACY_FIRST
                    )
            except ValueError:
                self.logger.warning(f"Chinese router recommended unavailable provider: {chinese_decision.recommended_provider}")
        
        # 获取任务类型的路由策略
        task_strategy = self.routing_strategies.get(request.task_type, {})
        routing_strategy = request.routing_strategy or task_strategy.get("strategy", RoutingStrategy.BALANCED)
        
        # 第一层：基础适配性评估
        candidate_providers = await self._evaluate_basic_compatibility(available_providers, request)
        
        if not candidate_providers:
            return self._create_fallback_decision("No compatible providers found")
        
        # 第二层：任务特定能力评估
        task_scores = await self._evaluate_task_specific_capabilities(candidate_providers, request)
        
        # 第三层：性能和可靠性评估
        performance_scores = await self._evaluate_performance_metrics(candidate_providers, request)
        
        # 第四层：成本效益评估
        cost_scores = await self._evaluate_cost_effectiveness(candidate_providers, request)
        
        # 第五层：智能综合决策
        final_decision = await self._make_intelligent_decision(
            candidate_providers, task_scores, performance_scores, cost_scores, 
            request, routing_strategy
        )
        
        return final_decision
    
    async def _evaluate_basic_compatibility(self, providers: List[AIProvider], 
                                          request: AIRequest) -> List[AIProvider]:
        """评估基础兼容性"""
        compatible = []
        
        for provider in providers:
            # 检查模型能力是否满足请求要求
            capabilities = self.provider_capabilities.get(provider, {})
            
            # 检查最大token限制
            if request.max_tokens:
                provider_max_tokens = self._get_provider_max_tokens(provider)
                if request.max_tokens > provider_max_tokens:
                    self.logger.debug(f"Provider {provider.value} max tokens insufficient")
                    continue
            
            # 检查任务类型支持
            if not self._is_task_supported(provider, request.task_type):
                self.logger.debug(f"Provider {provider.value} doesn't support task type {request.task_type}")
                continue
            
            # 检查语言支持
            if self._requires_chinese_support(request) and capabilities.get("chinese_support", 0) < 0.6:
                self.logger.debug(f"Provider {provider.value} has insufficient Chinese support")
                continue
            
            compatible.append(provider)
        
        return compatible
    
    async def _evaluate_task_specific_capabilities(self, providers: List[AIProvider], 
                                                 request: AIRequest) -> Dict[AIProvider, float]:
        """评估任务特定能力"""
        scores = {}
        
        for provider in providers:
            capabilities = self.provider_capabilities.get(provider, {})
            
            # 基础任务能力得分
            base_score = self._get_task_specific_score(provider, request.task_type)
            
            # 内容复杂度调整
            complexity_factor = self._calculate_content_complexity(request.content)
            complexity_adjustment = self._get_complexity_adjustment(provider, complexity_factor)
            
            # 上下文长度调整
            context_length = len(request.content) + len(str(request.context))
            context_adjustment = self._get_context_length_adjustment(provider, context_length)
            
            # 优先级调整
            priority_adjustment = self._get_priority_adjustment(provider, request.priority)
            
            # 综合任务能力得分
            task_score = (base_score * 0.5 + 
                         complexity_adjustment * 0.2 + 
                         context_adjustment * 0.2 + 
                         priority_adjustment * 0.1)
            
            scores[provider] = min(max(task_score, 0.0), 1.0)
        
        return scores
    
    async def _evaluate_performance_metrics(self, providers: List[AIProvider], 
                                          request: AIRequest) -> Dict[AIProvider, float]:
        """评估性能指标"""
        scores = {}
        
        for provider in providers:
            health = self.provider_health.get(provider)
            if not health:
                scores[provider] = 0.0
                continue
            
            # 响应时间得分 (越快越好)
            response_time_score = max(0.0, 1.0 - (health.response_time / 30.0))
            
            # 成功率得分
            success_rate_score = health.success_rate
            
            # 负载得分 (负载越低越好)
            load_score = 1.0 - (health.current_load / health.max_concurrent)
            
            # 可用性得分
            availability_score = 1.0 if health.is_available else 0.0
            
            # 错误率得分
            error_rate_score = max(0.0, 1.0 - (health.error_count / 100.0))
            
            # 综合性能得分
            performance_score = (response_time_score * 0.25 + 
                               success_rate_score * 0.3 + 
                               load_score * 0.2 + 
                               availability_score * 0.15 + 
                               error_rate_score * 0.1)
            
            scores[provider] = performance_score
        
        return scores
    
    async def _evaluate_cost_effectiveness(self, providers: List[AIProvider], 
                                         request: AIRequest) -> Dict[AIProvider, float]:
        """评估成本效益"""
        scores = {}
        
        # 计算所有提供商的预估成本
        provider_costs = {}
        for provider in providers:
            cost = await self._estimate_cost(provider, request)
            provider_costs[provider] = cost
        
        # 找到最低和最高成本
        if provider_costs:
            min_cost = min(provider_costs.values())
            max_cost = max(provider_costs.values())
            cost_range = max_cost - min_cost if max_cost > min_cost else 1.0
        else:
            min_cost = 0.0
            cost_range = 1.0
        
        for provider in providers:
            cost = provider_costs.get(provider, 0.0)
            capabilities = self.provider_capabilities.get(provider, {})
            
            # 成本得分 (成本越低得分越高)
            if cost_range > 0:
                cost_score = 1.0 - ((cost - min_cost) / cost_range)
            else:
                cost_score = 1.0
            
            # 性价比得分 (准确性/成本)
            accuracy = capabilities.get("accuracy", 0.5)
            value_score = accuracy / (cost + 0.001)  # 避免除零
            
            # 配额利用率得分
            health = self.provider_health.get(provider)
            quota_score = (health.quota_remaining / 100.0) if health else 0.5
            
            # 综合成本效益得分
            cost_effectiveness = (cost_score * 0.4 + 
                                value_score * 0.4 + 
                                quota_score * 0.2)
            
            scores[provider] = min(max(cost_effectiveness, 0.0), 1.0)
        
        return scores
    
    async def _make_intelligent_decision(self, providers: List[AIProvider],
                                       task_scores: Dict[AIProvider, float],
                                       performance_scores: Dict[AIProvider, float],
                                       cost_scores: Dict[AIProvider, float],
                                       request: AIRequest,
                                       strategy: RoutingStrategy) -> RoutingDecision:
        """智能综合决策"""
        
        # 根据策略调整权重
        weights = self._get_strategy_weights(strategy, request)
        
        # 计算综合得分
        final_scores = {}
        for provider in providers:
            task_score = task_scores.get(provider, 0.0)
            perf_score = performance_scores.get(provider, 0.0)
            cost_score = cost_scores.get(provider, 0.0)
            
            # 加入随机因子避免总是选择同一个提供商
            randomness_factor = 0.95 + (hash(f"{provider.value}_{request.request_id}") % 100) / 1000.0
            
            final_score = (task_score * weights['task'] + 
                          perf_score * weights['performance'] + 
                          cost_score * weights['cost']) * randomness_factor
            
            final_scores[provider] = final_score
        
        # 按得分排序
        sorted_providers = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_providers:
            return self._create_fallback_decision("No valid scores calculated")
        
        # 选择最佳提供商
        selected_provider = sorted_providers[0][0]
        confidence = sorted_providers[0][1]
        fallback_providers = [p[0] for p in sorted_providers[1:3]]
        
        # 估算成本和时间
        estimated_cost = await self._estimate_cost(selected_provider, request)
        estimated_time = await self._estimate_response_time(selected_provider, request)
        
        # 生成详细的决策理由
        reasoning = self._generate_enhanced_reasoning(
            selected_provider, request, strategy, confidence,
            task_scores, performance_scores, cost_scores
        )
        
        return RoutingDecision(
            selected_provider=selected_provider,
            confidence=confidence,
            reasoning=reasoning,
            fallback_providers=fallback_providers,
            estimated_cost=estimated_cost,
            estimated_time=estimated_time,
            routing_strategy_used=strategy
        )
    
    def _create_fallback_decision(self, reason: str) -> RoutingDecision:
        """创建后备决策"""
        return RoutingDecision(
            selected_provider=AIProvider.OPENAI,
            confidence=0.1,
            reasoning=f"Fallback decision: {reason}",
            fallback_providers=[],
            estimated_cost=0.0,
            estimated_time=0.0,
            routing_strategy_used=RoutingStrategy.BALANCED
        )
    
    async def _calculate_provider_score(self, provider: AIProvider, request: AIRequest, 
                                      strategy: RoutingStrategy) -> float:
        """
        计算提供商综合得分
        
        Args:
            provider: AI服务提供商
            request: AI请求对象
            strategy: 路由策略
            
        Returns:
            float: 综合得分 (0-1)
        """
        capabilities = self.provider_capabilities.get(provider, {})
        health = self.provider_health.get(provider)
        
        if not health:
            return 0.0
        
        # 基础能力得分
        accuracy_score = capabilities.get("accuracy", 0.5)
        speed_score = capabilities.get("speed", 0.5)
        cost_score = capabilities.get("cost_efficiency", 0.5)
        
        # 任务特定得分
        task_specific_score = self._get_task_specific_score(provider, request.task_type)
        
        # 健康状态得分
        health_score = (health.success_rate * 0.6 + 
                       (1 - min(health.response_time / 10.0, 1.0)) * 0.3 +
                       (1 - health.current_load / health.max_concurrent) * 0.1)
        
        # 根据策略调整权重
        if strategy == RoutingStrategy.ACCURACY_FIRST:
            final_score = (accuracy_score * 0.4 + task_specific_score * 0.3 + 
                          health_score * 0.2 + speed_score * 0.1)
        elif strategy == RoutingStrategy.COST_FIRST:
            final_score = (cost_score * 0.4 + health_score * 0.3 + 
                          accuracy_score * 0.2 + task_specific_score * 0.1)
        elif strategy == RoutingStrategy.SPEED_FIRST:
            final_score = (speed_score * 0.4 + health_score * 0.3 + 
                          accuracy_score * 0.2 + cost_score * 0.1)
        elif strategy == RoutingStrategy.LOAD_BALANCED:
            # 负载均衡策略：优先选择负载较低的提供商
            load_factor = 1 - (health.current_load / health.max_concurrent)
            final_score = (load_factor * 0.4 + accuracy_score * 0.3 + 
                          health_score * 0.2 + task_specific_score * 0.1)
        else:  # BALANCED
            final_score = (accuracy_score * 0.25 + speed_score * 0.25 + 
                          cost_score * 0.25 + health_score * 0.25)
        
        return min(max(final_score, 0.0), 1.0)
    
    def _get_provider_max_tokens(self, provider: AIProvider) -> int:
        """获取提供商最大token限制"""
        token_limits = {
            AIProvider.OPENAI: 8000,
            AIProvider.ANTHROPIC: 100000,
            AIProvider.GOOGLE_GEMINI: 32000,
            AIProvider.BAIDU_WENXIN: 4000,
            AIProvider.ALIYUN_TONGYI: 6000,
            AIProvider.ZHIPU_CHATGLM: 8000,
            AIProvider.XUNFEI_XINGHUO: 4000
        }
        return token_limits.get(provider, 4000)
    
    def _is_task_supported(self, provider: AIProvider, task_type: TaskType) -> bool:
        """检查提供商是否支持特定任务类型"""
        # 所有提供商都支持基础任务
        basic_tasks = {TaskType.SIMPLE_QUERY, TaskType.GENERAL_TASK, TaskType.CHINESE_CONTENT}
        if task_type in basic_tasks:
            return True
        
        # 高级任务的支持情况
        advanced_support = {
            AIProvider.OPENAI: {TaskType.CODE_GENERATION, TaskType.COMPLEX_ANALYSIS, TaskType.DATA_ANALYSIS},
            AIProvider.ANTHROPIC: {TaskType.CODE_GENERATION, TaskType.CREATIVE_WRITING, TaskType.DOCUMENT_WRITING},
            AIProvider.GOOGLE_GEMINI: {TaskType.DATA_ANALYSIS, TaskType.TRANSLATION, TaskType.COMPLEX_ANALYSIS},
            AIProvider.BAIDU_WENXIN: {TaskType.CHINESE_CONTENT, TaskType.CREATIVE_WRITING, TaskType.DOCUMENT_WRITING},
            AIProvider.ALIYUN_TONGYI: {TaskType.CHINESE_CONTENT, TaskType.DOCUMENT_WRITING},
            AIProvider.ZHIPU_CHATGLM: {TaskType.CHINESE_CONTENT, TaskType.CODE_GENERATION},
            AIProvider.XUNFEI_XINGHUO: {TaskType.CHINESE_CONTENT, TaskType.TRANSLATION}
        }
        
        supported_tasks = advanced_support.get(provider, set())
        return task_type in supported_tasks
    
    def _requires_chinese_support(self, request: AIRequest) -> bool:
        """检查请求是否需要中文支持"""
        chinese_chars = len([c for c in request.content if '\u4e00' <= c <= '\u9fff'])
        chinese_ratio = chinese_chars / len(request.content) if len(request.content) > 0 else 0
        return chinese_ratio > 0.3 or request.task_type == TaskType.CHINESE_CONTENT
    
    def _calculate_content_complexity(self, content: str) -> float:
        """计算内容复杂度"""
        # 基于多个因素计算复杂度
        length_factor = min(len(content) / 2000.0, 1.0)
        
        # 技术词汇密度
        tech_keywords = ['算法', '数据结构', '架构', '设计模式', '性能优化', 'API', '数据库', '缓存']
        tech_count = sum(1 for keyword in tech_keywords if keyword in content)
        tech_factor = min(tech_count / 5.0, 1.0)
        
        # 句子复杂度（基于标点符号）
        punctuation_count = len([c for c in content if c in '，。；：？！,.:;?!'])
        sentence_factor = min(punctuation_count / 20.0, 1.0)
        
        # 综合复杂度
        complexity = (length_factor * 0.4 + tech_factor * 0.4 + sentence_factor * 0.2)
        return min(max(complexity, 0.0), 1.0)
    
    def _get_complexity_adjustment(self, provider: AIProvider, complexity: float) -> float:
        """获取复杂度调整因子"""
        # 不同提供商对复杂任务的处理能力不同
        complexity_handling = {
            AIProvider.OPENAI: 0.95,
            AIProvider.ANTHROPIC: 0.93,
            AIProvider.GOOGLE_GEMINI: 0.88,
            AIProvider.BAIDU_WENXIN: 0.82,
            AIProvider.ALIYUN_TONGYI: 0.80,
            AIProvider.ZHIPU_CHATGLM: 0.75,
            AIProvider.XUNFEI_XINGHUO: 0.70
        }
        
        base_capability = complexity_handling.get(provider, 0.7)
        # 复杂度越高，对能力要求越高
        adjustment = base_capability * (1.0 - complexity * 0.3)
        return min(max(adjustment, 0.0), 1.0)
    
    def _get_context_length_adjustment(self, provider: AIProvider, context_length: int) -> float:
        """获取上下文长度调整因子"""
        max_tokens = self._get_provider_max_tokens(provider)
        
        # 计算上下文使用率
        usage_ratio = context_length / max_tokens
        
        if usage_ratio <= 0.5:
            return 1.0  # 低使用率，无惩罚
        elif usage_ratio <= 0.8:
            return 0.9  # 中等使用率，轻微惩罚
        elif usage_ratio <= 0.95:
            return 0.7  # 高使用率，明显惩罚
        else:
            return 0.3  # 超高使用率，严重惩罚
    
    def _get_priority_adjustment(self, provider: AIProvider, priority: str) -> float:
        """获取优先级调整因子"""
        # 不同提供商对不同优先级请求的适配性
        priority_weights = {
            "low": 1.0,
            "normal": 1.0,
            "high": 0.9,  # 高优先级需要更可靠的提供商
            "urgent": 0.8  # 紧急请求需要最可靠的提供商
        }
        
        base_weight = priority_weights.get(priority, 1.0)
        
        # 高优先级请求偏向高可靠性提供商
        if priority in ["high", "urgent"]:
            reliability_scores = {
                AIProvider.OPENAI: 0.95,
                AIProvider.ANTHROPIC: 0.93,
                AIProvider.GOOGLE_GEMINI: 0.88,
                AIProvider.BAIDU_WENXIN: 0.85,
                AIProvider.ALIYUN_TONGYI: 0.82,
                AIProvider.ZHIPU_CHATGLM: 0.78,
                AIProvider.XUNFEI_XINGHUO: 0.75
            }
            reliability = reliability_scores.get(provider, 0.7)
            return base_weight * reliability
        
        return base_weight
    
    def _get_strategy_weights(self, strategy: RoutingStrategy, request: AIRequest) -> Dict[str, float]:
        """获取策略权重"""
        if strategy == RoutingStrategy.ACCURACY_FIRST:
            return {"task": 0.5, "performance": 0.3, "cost": 0.2}
        elif strategy == RoutingStrategy.COST_FIRST:
            return {"task": 0.2, "performance": 0.3, "cost": 0.5}
        elif strategy == RoutingStrategy.SPEED_FIRST:
            return {"task": 0.3, "performance": 0.5, "cost": 0.2}
        elif strategy == RoutingStrategy.LOAD_BALANCED:
            return {"task": 0.25, "performance": 0.5, "cost": 0.25}
        else:  # BALANCED
            return {"task": 0.33, "performance": 0.34, "cost": 0.33}
    
    def _generate_enhanced_reasoning(self, provider: AIProvider, request: AIRequest,
                                   strategy: RoutingStrategy, confidence: float,
                                   task_scores: Dict[AIProvider, float],
                                   performance_scores: Dict[AIProvider, float],
                                   cost_scores: Dict[AIProvider, float]) -> str:
        """生成增强的决策理由"""
        reasons = []
        
        # 基础选择理由
        if request.preferred_provider == provider:
            reasons.append("✓ 用户指定的首选提供商")
        
        # 策略相关理由
        strategy_reasons = {
            RoutingStrategy.ACCURACY_FIRST: f"准确性优先策略，{provider.value}任务能力得分: {task_scores.get(provider, 0):.2f}",
            RoutingStrategy.COST_FIRST: f"成本优先策略，{provider.value}成本效益得分: {cost_scores.get(provider, 0):.2f}",
            RoutingStrategy.SPEED_FIRST: f"速度优先策略，{provider.value}性能得分: {performance_scores.get(provider, 0):.2f}",
            RoutingStrategy.LOAD_BALANCED: f"负载均衡策略，{provider.value}综合负载最优",
            RoutingStrategy.BALANCED: f"平衡策略，{provider.value}综合评估最优"
        }
        reasons.append(strategy_reasons.get(strategy, f"综合评估选择{provider.value}"))
        
        # 任务匹配理由
        task_score = task_scores.get(provider, 0)
        if task_score > 0.8:
            reasons.append(f"✓ 高度匹配任务类型 ({request.task_type.value})")
        elif task_score > 0.6:
            reasons.append(f"○ 适配任务类型 ({request.task_type.value})")
        
        # 性能理由
        perf_score = performance_scores.get(provider, 0)
        if perf_score > 0.8:
            reasons.append("✓ 优秀的性能表现")
        elif perf_score > 0.6:
            reasons.append("○ 良好的性能表现")
        
        # 成本理由
        cost_score = cost_scores.get(provider, 0)
        if cost_score > 0.8:
            reasons.append("✓ 优秀的成本效益")
        elif cost_score > 0.6:
            reasons.append("○ 合理的成本效益")
        
        # 置信度理由
        if confidence > 0.8:
            reasons.append("✓ 高置信度选择")
        elif confidence > 0.6:
            reasons.append("○ 中等置信度选择")
        else:
            reasons.append("⚠ 低置信度选择，建议监控结果")
        
        return " | ".join(reasons)
    
    def _get_task_specific_score(self, provider: AIProvider, task_type: TaskType) -> float:
        """获取任务特定得分"""
        capabilities = self.provider_capabilities.get(provider, {})
        
        task_capability_map = {
            TaskType.CHINESE_CONTENT: "chinese_support",
            TaskType.CODE_GENERATION: "code_generation", 
            TaskType.CREATIVE_WRITING: "creative_writing",
            TaskType.COMPLEX_ANALYSIS: "reasoning",
            TaskType.DATA_ANALYSIS: "reasoning"
        }
        
        capability_key = task_capability_map.get(task_type, "accuracy")
        return capabilities.get(capability_key, 0.5)
    
    async def _estimate_cost(self, provider: AIProvider, request: AIRequest) -> float:
        """估算请求成本 - 增强版本"""
        try:
            # 从数据库获取成本配置
            query = select(
                AIModelConfig.cost_per_input_token,
                AIModelConfig.cost_per_output_token,
                AIModelConfig.cost_per_request
            ).where(
                and_(
                    AIModelConfig.provider == provider.value,
                    AIModelConfig.is_enabled == True
                )
            ).limit(1)
            result = await self.db.execute(query)
            row = result.first()
            
            if row:
                cost_per_input_token = row.cost_per_input_token or 0.001
                cost_per_output_token = row.cost_per_output_token or 0.002
                cost_per_request = row.cost_per_request or 0.0
            else:
                # 默认成本配置
                cost_per_input_token = 0.001
                cost_per_output_token = 0.002
                cost_per_request = 0.0
            
            # 估算输入和输出token数量
            input_tokens = len(request.content) // 4  # 输入token估算
            output_tokens = request.max_tokens or 1000  # 输出token估算
            
            # 计算总成本
            input_cost = input_tokens * cost_per_input_token
            output_cost = output_tokens * cost_per_output_token
            request_cost = cost_per_request
            
            total_cost = input_cost + output_cost + request_cost
            
            # 根据任务复杂度调整成本估算
            complexity_factor = self._get_complexity_cost_factor(request)
            total_cost *= complexity_factor
            
            return total_cost
            
        except Exception as e:
            self.logger.error(f"Error estimating cost: {str(e)}")
            return 0.001  # 返回最小成本避免除零错误
    
    def _get_complexity_cost_factor(self, request: AIRequest) -> float:
        """根据任务复杂度获取成本调整因子"""
        try:
            # 基础因子
            factor = 1.0
            
            # 根据任务类型调整
            task_factors = {
                TaskType.SIMPLE_QUERY: 0.8,
                TaskType.COMPLEX_ANALYSIS: 1.5,
                TaskType.CODE_GENERATION: 1.3,
                TaskType.TEST_CASE_GENERATION: 1.2,
                TaskType.DOCUMENT_WRITING: 1.1,
                TaskType.CREATIVE_WRITING: 1.2,
                TaskType.DATA_ANALYSIS: 1.4,
                TaskType.TRANSLATION: 0.9,
                TaskType.CHINESE_CONTENT: 1.0,
                TaskType.GENERAL_TASK: 1.0
            }
            
            factor *= task_factors.get(request.task_type, 1.0)
            
            # 根据内容长度调整
            content_length = len(request.content)
            if content_length > 5000:
                factor *= 1.3
            elif content_length > 2000:
                factor *= 1.1
            elif content_length < 100:
                factor *= 0.9
            
            # 根据优先级调整
            priority_factors = {
                "low": 0.9,
                "normal": 1.0,
                "high": 1.1,
                "urgent": 1.2
            }
            factor *= priority_factors.get(request.priority, 1.0)
            
            return max(0.5, min(2.0, factor))  # 限制在0.5-2.0之间
            
        except Exception as e:
            self.logger.error(f"Error calculating complexity factor: {str(e)}")
            return 1.0
    
    async def _estimate_response_time(self, provider: AIProvider, request: AIRequest) -> float:
        """估算响应时间"""
        health = self.provider_health.get(provider)
        if not health:
            return 10.0  # 默认估算
        
        # 基于历史响应时间和当前负载调整
        base_time = health.response_time
        load_factor = 1 + (health.current_load / health.max_concurrent) * 0.5
        content_factor = 1 + (len(request.content) / 1000) * 0.2
        
        return base_time * load_factor * content_factor
    
    async def _perform_cost_control_check(self, provider: AIProvider, request: AIRequest, 
                                         estimated_cost: float) -> Dict[str, Any]:
        """
        执行成本控制检查
        
        Args:
            provider: 选择的AI提供商
            request: AI请求对象
            estimated_cost: 预估成本
            
        Returns:
            Dict[str, Any]: 检查结果
        """
        try:
            from decimal import Decimal
            
            # 估算token数量
            estimated_tokens = len(request.content) // 4 + (request.max_tokens or 1000)
            
            # 检查预算限制
            budget_allowed, budget_alerts = await self.cost_control.check_budget_limits(
                provider.value, request.user_id, Decimal(str(estimated_cost))
            )
            
            # 检查配额限制
            quota_allowed, quota_alerts = await self.cost_control.check_usage_quotas(
                provider.value, request.user_id, estimated_tokens
            )
            
            all_alerts = budget_alerts + quota_alerts
            allowed = budget_allowed and quota_allowed
            
            # 生成拒绝原因
            reason = ""
            if not budget_allowed:
                reason += "预算超限; "
            if not quota_allowed:
                reason += "配额超限; "
            
            return {
                "allowed": allowed,
                "reason": reason.rstrip("; "),
                "alerts": all_alerts,
                "budget_allowed": budget_allowed,
                "quota_allowed": quota_allowed
            }
            
        except Exception as e:
            self.logger.error(f"Error in cost control check: {str(e)}")
            # 出错时采用保守策略，允许请求
            return {
                "allowed": True,
                "reason": f"Cost control check failed: {str(e)}",
                "alerts": [],
                "budget_allowed": True,
                "quota_allowed": True
            }
    
    async def _find_cost_effective_alternative(self, request: AIRequest, 
                                             available_providers: List[AIProvider],
                                             alerts: List) -> Optional[RoutingDecision]:
        """
        寻找成本效益更好的替代方案
        
        Args:
            request: AI请求对象
            available_providers: 可用提供商列表
            alerts: 成本告警列表
            
        Returns:
            Optional[RoutingDecision]: 替代路由决策
        """
        try:
            # 按成本从低到高排序提供商
            provider_costs = []
            for provider in available_providers:
                cost = await self._estimate_cost(provider, request)
                provider_costs.append((provider, cost))
            
            # 按成本排序
            provider_costs.sort(key=lambda x: x[1])
            
            # 尝试每个提供商，直到找到符合成本控制的
            for provider, cost in provider_costs:
                cost_check = await self._perform_cost_control_check(provider, request, cost)
                
                if cost_check["allowed"]:
                    # 生成替代决策
                    estimated_time = await self._estimate_response_time(provider, request)
                    
                    return RoutingDecision(
                        selected_provider=provider,
                        confidence=0.7,  # 降低置信度，因为这是成本驱动的选择
                        reasoning=f"Cost-effective alternative selected due to budget/quota constraints. Original alerts: {len(alerts)}",
                        fallback_providers=[p for p, _ in provider_costs if p != provider][:2],
                        estimated_cost=cost,
                        estimated_time=estimated_time,
                        routing_strategy_used=RoutingStrategy.COST_FIRST
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding cost-effective alternative: {str(e)}")
            return None
    
    async def record_actual_usage(self, provider: AIProvider, user_id: int,
                                 input_tokens: int, output_tokens: int,
                                 actual_cost: float, response_time: float,
                                 success: bool = True) -> None:
        """
        记录实际使用情况
        
        Args:
            provider: AI服务提供商
            user_id: 用户ID
            input_tokens: 输入token数
            output_tokens: 输出token数
            actual_cost: 实际成本
            response_time: 响应时间
            success: 是否成功
        """
        try:
            from decimal import Decimal
            
            # 记录到成本控制服务
            await self.cost_control.record_usage(
                provider.value, user_id, input_tokens, output_tokens,
                Decimal(str(actual_cost)), response_time, success
            )
            
            # 更新提供商健康状态
            await self._update_provider_health(provider, response_time, success)
            
        except Exception as e:
            self.logger.error(f"Error recording actual usage: {str(e)}")
    
    async def _update_provider_health(self, provider: AIProvider, 
                                    response_time: float, success: bool) -> None:
        """更新提供商健康状态"""
        try:
            health = self.provider_health.get(provider)
            if not health:
                health = ProviderHealth(provider=provider)
                self.provider_health[provider] = health
            
            # 更新响应时间（使用指数移动平均）
            alpha = 0.1  # 平滑因子
            if health.response_time > 0:
                health.response_time = (1 - alpha) * health.response_time + alpha * response_time
            else:
                health.response_time = response_time
            
            # 更新成功率（使用滑动窗口）
            if success:
                health.success_rate = min(1.0, health.success_rate + 0.01)
                health.error_count = max(0, health.error_count - 1)
            else:
                health.success_rate = max(0.0, health.success_rate - 0.05)
                health.error_count += 1
            
            # 更新最后检查时间
            health.last_check = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error updating provider health: {str(e)}")
    
    async def get_cost_summary(self, period: str = "daily", 
                              provider: str = None, user_id: int = None) -> Dict[str, Any]:
        """
        获取成本摘要
        
        Args:
            period: 统计周期 (daily, weekly, monthly, yearly)
            provider: 特定提供商（可选）
            user_id: 特定用户（可选）
            
        Returns:
            Dict[str, Any]: 成本摘要
        """
        try:
            from .cost_control_service import BudgetPeriod
            
            # 转换周期枚举
            period_enum = {
                "daily": BudgetPeriod.DAILY,
                "weekly": BudgetPeriod.WEEKLY,
                "monthly": BudgetPeriod.MONTHLY,
                "yearly": BudgetPeriod.YEARLY
            }.get(period, BudgetPeriod.DAILY)
            
            return await self.cost_control.get_cost_summary(period_enum, provider, user_id)
            
        except Exception as e:
            self.logger.error(f"Error getting cost summary: {str(e)}")
            return {"error": str(e)}
    
    def get_cost_alerts(self, level: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取成本告警
        
        Args:
            level: 告警级别 (info, warning, critical, emergency)
            limit: 返回数量限制
            
        Returns:
            List[Dict[str, Any]]: 告警列表
        """
        try:
            from .cost_control_service import AlertLevel
            
            # 转换告警级别
            level_enum = None
            if level:
                level_enum = {
                    "info": AlertLevel.INFO,
                    "warning": AlertLevel.WARNING,
                    "critical": AlertLevel.CRITICAL,
                    "emergency": AlertLevel.EMERGENCY
                }.get(level.lower())
            
            alerts = self.cost_control.get_alerts(level_enum, limit)
            
            # 转换为字典格式
            return [
                {
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "message": alert.message,
                    "budget_id": alert.budget_id,
                    "quota_id": alert.quota_id,
                    "provider": alert.provider,
                    "user_id": alert.user_id,
                    "current_usage": float(alert.current_usage) if alert.current_usage else None,
                    "limit": float(alert.limit) if alert.limit else None,
                    "percentage": alert.percentage,
                    "timestamp": alert.timestamp.isoformat() if alert.timestamp else None
                }
                for alert in alerts
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting cost alerts: {str(e)}")
            return []
    
    def _generate_routing_reasoning(self, provider: AIProvider, request: AIRequest, 
                                  strategy: RoutingStrategy, confidence: float) -> str:
        """生成路由决策理由"""
        reasons = []
        
        if request.preferred_provider == provider:
            reasons.append("用户指定的首选提供商")
        
        if strategy == RoutingStrategy.ACCURACY_FIRST:
            reasons.append(f"基于准确性优先策略选择，{provider.value}在该任务类型上表现优秀")
        elif strategy == RoutingStrategy.COST_FIRST:
            reasons.append(f"基于成本优先策略选择，{provider.value}具有较好的成本效益")
        elif strategy == RoutingStrategy.SPEED_FIRST:
            reasons.append(f"基于速度优先策略选择，{provider.value}响应速度较快")
        elif strategy == RoutingStrategy.LOAD_BALANCED:
            reasons.append(f"基于负载均衡策略选择，{provider.value}当前负载较低")
        else:
            reasons.append(f"基于综合评估选择，{provider.value}在多个维度表现均衡")
        
        if confidence > 0.8:
            reasons.append("高置信度选择")
        elif confidence > 0.6:
            reasons.append("中等置信度选择")
        else:
            reasons.append("低置信度选择，建议监控结果")
        
        return "；".join(reasons)
    
    async def _update_load_balancer(self, provider: AIProvider):
        """更新负载均衡状态"""
        health = self.provider_health.get(provider)
        if health:
            health.current_load += 1
            self.load_balancer_state[provider] = self.load_balancer_state.get(provider, 0) + 1
    
    def _select_best_accuracy_provider(self, providers: List[AIProvider]) -> AIProvider:
        """选择准确性最好的提供商"""
        # 基于历史成功率选择
        accuracy_ranking = {
            AIProvider.OPENAI: 0.95,
            AIProvider.ANTHROPIC: 0.93,
            AIProvider.GOOGLE_GEMINI: 0.90,
            AIProvider.BAIDU_WENXIN: 0.88,
            AIProvider.ALIYUN_TONGYI: 0.85
        }
        
        best_provider = max(providers, key=lambda p: accuracy_ranking.get(p, 0.5))
        return best_provider
    
    def _select_best_cost_provider(self, providers: List[AIProvider]) -> AIProvider:
        """选择成本最低的提供商"""
        # 基于成本排序（成本越低越好）
        cost_ranking = {
            AIProvider.BAIDU_WENXIN: 0.1,
            AIProvider.ALIYUN_TONGYI: 0.15,
            AIProvider.OPENAI: 0.3,
            AIProvider.GOOGLE_GEMINI: 0.25,
            AIProvider.ANTHROPIC: 0.4
        }
        
        best_provider = min(providers, key=lambda p: cost_ranking.get(p, 1.0))
        return best_provider
    
    def _select_balanced_provider(self, providers: List[AIProvider]) -> AIProvider:
        """选择平衡性最好的提供商"""
        # 综合考虑准确性和成本
        balance_score = {
            AIProvider.OPENAI: 0.85,
            AIProvider.BAIDU_WENXIN: 0.80,
            AIProvider.ANTHROPIC: 0.75,
            AIProvider.GOOGLE_GEMINI: 0.78,
            AIProvider.ALIYUN_TONGYI: 0.70
        }
        
        best_provider = max(providers, key=lambda p: balance_score.get(p, 0.5))
        return best_provider
    
    async def update_provider_health(self, provider: AIProvider, 
                                   response_time: float, success: bool):
        """
        更新服务提供商健康状态
        
        Args:
            provider: AI服务提供商
            response_time: 响应时间
            success: 是否成功
        """
        health = self.provider_health.get(provider)
        if not health:
            health = ProviderHealth(provider)
            self.provider_health[provider] = health
        
        # 更新响应时间（移动平均）
        health.response_time = (health.response_time * 0.8) + (response_time * 0.2)
        
        # 更新成功率（移动平均）
        if success:
            health.success_rate = (health.success_rate * 0.9) + (1.0 * 0.1)
            health.error_count = max(0, health.error_count - 1)
        else:
            health.success_rate = (health.success_rate * 0.9) + (0.0 * 0.1)
            health.error_count += 1
        
        # 更新可用性状态
        health.is_available = health.success_rate > 0.5 and health.error_count < 10
        health.last_check = datetime.utcnow()
        
        # 减少当前负载
        if health.current_load > 0:
            health.current_load -= 1
    
    async def get_routing_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        stats = {
            "provider_health": {},
            "load_balancer_state": dict(self.load_balancer_state),
            "routing_strategies": {},
            "performance_metrics": {}
        }
        
        # 提供商健康状态统计
        for provider, health in self.provider_health.items():
            stats["provider_health"][provider.value] = {
                "is_available": health.is_available,
                "success_rate": health.success_rate,
                "response_time": health.response_time,
                "current_load": health.current_load,
                "error_count": health.error_count,
                "quota_remaining": health.quota_remaining,
                "last_check": health.last_check.isoformat() if health.last_check else None
            }
        
        # 路由策略使用统计
        for task_type, strategy_config in self.routing_strategies.items():
            stats["routing_strategies"][task_type.value] = {
                "strategy": strategy_config["strategy"].value,
                "preferred_providers": [p.value for p in strategy_config["preferred_providers"]],
                "min_accuracy": strategy_config["min_accuracy"],
                "max_cost_per_token": strategy_config["max_cost_per_token"]
            }
        
        return stats
    
    async def optimize_routing_strategies(self):
        """优化路由策略 - 基于历史性能数据"""
        try:
            # 获取最近的使用统计
            recent_stats = await self._get_recent_usage_stats()
            
            # 分析每个任务类型的最佳提供商
            for task_type in TaskType:
                if task_type in recent_stats:
                    task_stats = recent_stats[task_type]
                    
                    # 找到表现最好的提供商
                    best_providers = self._analyze_best_providers(task_stats)
                    
                    # 更新路由策略
                    if task_type in self.routing_strategies:
                        current_strategy = self.routing_strategies[task_type]
                        current_strategy["preferred_providers"] = best_providers[:3]  # 取前3个
                        
                        self.logger.info(f"Updated routing strategy for {task_type.value}: {[p.value for p in best_providers[:3]]}")
            
        except Exception as e:
            self.logger.error(f"Error optimizing routing strategies: {str(e)}")
    
    async def _get_recent_usage_stats(self) -> Dict[TaskType, Dict]:
        """获取最近的使用统计"""
        if not self.db:
            return {}
        
        try:
            # 获取最近7天的统计数据
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            
            query = select(AIUsageStats).where(
                AIUsageStats.created_at >= seven_days_ago
            )
            result = await self.db.execute(query)
            usage_records = result.scalars().all()
            
            # 按任务类型分组统计
            stats_by_task = {}
            for record in usage_records:
                # 这里需要根据实际的数据库字段调整
                task_type = getattr(record, 'task_type', TaskType.GENERAL_TASK)
                provider = AIProvider(record.ai_provider)
                
                if task_type not in stats_by_task:
                    stats_by_task[task_type] = {}
                
                if provider not in stats_by_task[task_type]:
                    stats_by_task[task_type][provider] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "total_response_time": 0.0,
                        "total_cost": 0.0
                    }
                
                provider_stats = stats_by_task[task_type][provider]
                provider_stats["total_requests"] += 1
                
                # 假设有成功标志字段
                if getattr(record, 'is_successful', True):
                    provider_stats["successful_requests"] += 1
                
                provider_stats["total_response_time"] += getattr(record, 'response_time', 0.0)
                provider_stats["total_cost"] += getattr(record, 'cost', 0.0)
            
            return stats_by_task
            
        except Exception as e:
            self.logger.error(f"Error getting recent usage stats: {str(e)}")
            return {}
    
    def _analyze_best_providers(self, task_stats: Dict) -> List[AIProvider]:
        """分析任务的最佳提供商"""
        provider_scores = {}
        
        for provider, stats in task_stats.items():
            if stats["total_requests"] == 0:
                continue
            
            # 计算成功率
            success_rate = stats["successful_requests"] / stats["total_requests"]
            
            # 计算平均响应时间
            avg_response_time = stats["total_response_time"] / stats["total_requests"]
            
            # 计算平均成本
            avg_cost = stats["total_cost"] / stats["total_requests"]
            
            # 综合评分 (成功率权重最高)
            score = (success_rate * 0.5 + 
                    (1.0 - min(avg_response_time / 10.0, 1.0)) * 0.3 + 
                    (1.0 - min(avg_cost / 0.1, 1.0)) * 0.2)
            
            provider_scores[provider] = score
        
        # 按得分排序
        sorted_providers = sorted(provider_scores.items(), key=lambda x: x[1], reverse=True)
        return [provider for provider, score in sorted_providers]
    
    async def predict_optimal_provider(self, request: AIRequest) -> Tuple[AIProvider, float]:
        """预测最优提供商 - 基于机器学习的预测"""
        try:
            # 特征提取
            features = self._extract_request_features(request)
            
            # 简单的基于规则的预测（可以后续替换为ML模型）
            prediction_score = await self._rule_based_prediction(features, request)
            
            # 找到预测得分最高的提供商
            best_provider = max(prediction_score.items(), key=lambda x: x[1])
            
            return best_provider[0], best_provider[1]
            
        except Exception as e:
            self.logger.error(f"Error predicting optimal provider: {str(e)}")
            return AIProvider.OPENAI, 0.5
    
    def _extract_request_features(self, request: AIRequest) -> Dict[str, float]:
        """提取请求特征"""
        content = request.content
        
        features = {
            "content_length": len(content) / 1000.0,  # 标准化到0-10范围
            "chinese_ratio": len([c for c in content if '\u4e00' <= c <= '\u9fff']) / len(content) if content else 0,
            "complexity": self._calculate_content_complexity(content),
            "urgency": {"low": 0.25, "normal": 0.5, "high": 0.75, "urgent": 1.0}.get(request.priority, 0.5),
            "has_code": 1.0 if any(keyword in content.lower() for keyword in ['def ', 'class ', 'function', '```']) else 0.0,
            "has_data": 1.0 if any(keyword in content.lower() for keyword in ['数据', '统计', '分析', 'data']) else 0.0,
            "is_question": 1.0 if content.strip().endswith('?') or content.strip().endswith('？') else 0.0
        }
        
        return features
    
    async def _rule_based_prediction(self, features: Dict[str, float], request: AIRequest) -> Dict[AIProvider, float]:
        """基于规则的预测"""
        scores = {}
        
        for provider in AIProvider:
            if provider == AIProvider.CUSTOM:
                continue
                
            capabilities = self.provider_capabilities.get(provider, {})
            score = 0.0
            
            # 基于特征计算得分
            if features["chinese_ratio"] > 0.5:
                score += capabilities.get("chinese_support", 0.5) * 0.3
            
            if features["has_code"] > 0.5:
                score += capabilities.get("code_generation", 0.5) * 0.3
            
            if features["complexity"] > 0.7:
                score += capabilities.get("reasoning", 0.5) * 0.2
            
            if features["urgency"] > 0.7:
                score += capabilities.get("speed", 0.5) * 0.2
            
            # 基础能力得分
            score += capabilities.get("accuracy", 0.5) * 0.3
            
            scores[provider] = min(max(score, 0.0), 1.0)
        
        return scores
        """
        获取所有提供商的统计信息
        
        Returns:
            Dict[str, Any]: 提供商统计信息
        """
        stats = {}
        
        for provider in AIProvider:
            health = self.provider_health.get(provider)
            if health:
                stats[provider.value] = {
                    "is_available": health.is_available,
                    "response_time": health.response_time,
                    "success_rate": health.success_rate,
                    "error_count": health.error_count,
                    "last_check": health.last_check.isoformat(),
                    "quota_remaining": health.quota_remaining
                }
        
        return stats
    
    async def force_provider_check(self, provider: AIProvider) -> bool:
        """
        强制检查服务提供商状态
        
        Args:
            provider: AI服务提供商
            
        Returns:
            bool: 检查结果
        """
        try:
            # 这里应该实际调用AI服务进行健康检查
            # 目前返回模拟结果
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            # 更新健康状态
            health = self.provider_health.get(provider)
            if health:
                health.last_check = datetime.utcnow()
                health.is_available = True  # 模拟检查成功
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking provider {provider.value}: {str(e)}")
            
            # 更新健康状态为不可用
            health = self.provider_health.get(provider)
            if health:
                health.is_available = False
                health.last_check = datetime.utcnow()
            
            return False
    
    async def release_provider_load(self, provider: AIProvider):
        """
        释放提供商负载
        
        Args:
            provider: AI服务提供商
        """
        health = self.provider_health.get(provider)
        if health and health.current_load > 0:
            health.current_load -= 1
        
        if provider in self.load_balancer_state and self.load_balancer_state[provider] > 0:
            self.load_balancer_state[provider] -= 1
    
    async def get_routing_recommendations(self, request: AIRequest) -> Dict[str, Any]:
        """
        获取路由推荐信息（用于调试和监控）
        
        Args:
            request: AI请求对象
            
        Returns:
            Dict[str, Any]: 推荐信息
        """
        available_providers = await self._get_available_providers(request)
        
        recommendations = {
            "task_type": request.task_type.value if request.task_type else "unknown",
            "available_providers": [p.value for p in available_providers],
            "provider_scores": {},
            "strategy_recommendations": {}
        }
        
        # 计算各提供商在不同策略下的得分
        for strategy in RoutingStrategy:
            strategy_scores = {}
            for provider in available_providers:
                score = await self._calculate_provider_score(provider, request, strategy)
                strategy_scores[provider.value] = score
            recommendations["strategy_recommendations"][strategy.value] = strategy_scores
        
        return recommendations
    
    async def get_provider_performance_metrics(self, provider: AIProvider, 
                                             days: int = 7) -> Dict[str, Any]:
        """
        获取提供商性能指标
        
        Args:
            provider: AI服务提供商
            days: 统计天数
            
        Returns:
            Dict[str, Any]: 性能指标
        """
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            # 查询使用统计
            query = select(
                func.sum(AIUsageStats.request_count).label("total_requests"),
                func.sum(AIUsageStats.success_count).label("total_success"),
                func.sum(AIUsageStats.error_count).label("total_errors"),
                func.sum(AIUsageStats.total_tokens).label("total_tokens"),
                func.sum(AIUsageStats.total_cost).label("total_cost"),
                func.avg(AIUsageStats.avg_response_time).label("avg_response_time")
            ).where(
                and_(
                    AIUsageStats.ai_provider == provider.value,
                    AIUsageStats.date >= start_date,
                    AIUsageStats.date <= end_date
                )
            )
            
            result = await self.db.execute(query)
            stats = result.first()
            
            if not stats or not stats.total_requests:
                return {
                    "provider": provider.value,
                    "period_days": days,
                    "total_requests": 0,
                    "success_rate": 0.0,
                    "error_rate": 0.0,
                    "avg_response_time": 0.0,
                    "total_cost": 0.0,
                    "cost_per_request": 0.0
                }
            
            success_rate = (stats.total_success / stats.total_requests) if stats.total_requests > 0 else 0.0
            error_rate = (stats.total_errors / stats.total_requests) if stats.total_requests > 0 else 0.0
            cost_per_request = (stats.total_cost / stats.total_requests) if stats.total_requests > 0 else 0.0
            
            return {
                "provider": provider.value,
                "period_days": days,
                "total_requests": stats.total_requests or 0,
                "success_rate": success_rate,
                "error_rate": error_rate,
                "avg_response_time": stats.avg_response_time or 0.0,
                "total_tokens": stats.total_tokens or 0,
                "total_cost": stats.total_cost or 0.0,
                "cost_per_request": cost_per_request,
                "current_health": {
                    "is_available": self.provider_health.get(provider, ProviderHealth(provider)).is_available,
                    "current_load": self.provider_health.get(provider, ProviderHealth(provider)).current_load,
                    "last_check": self.provider_health.get(provider, ProviderHealth(provider)).last_check.isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics for {provider.value}: {str(e)}")
            return {
                "provider": provider.value,
                "error": str(e)
            }
    
    async def optimize_routing_strategies(self) -> Dict[str, Any]:
        """
        基于历史数据优化路由策略
        
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            optimization_results = {
                "timestamp": datetime.utcnow().isoformat(),
                "optimizations": [],
                "recommendations": []
            }
            
            # 分析各任务类型的提供商表现
            for task_type in TaskType:
                # 这里可以实现基于历史数据的策略优化逻辑
                # 目前返回示例结果
                optimization_results["optimizations"].append({
                    "task_type": task_type.value,
                    "current_strategy": self.routing_strategies.get(task_type, {}).get("strategy", "balanced"),
                    "recommended_changes": "基于历史数据分析的优化建议"
                })
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Error optimizing routing strategies: {str(e)}")
            return {"error": str(e)}
    
    def get_current_load_distribution(self) -> Dict[str, Any]:
        """
        获取当前负载分布
        
        Returns:
            Dict[str, Any]: 负载分布信息
        """
        load_distribution = {
            "timestamp": datetime.utcnow().isoformat(),
            "providers": {}
        }
        
        for provider, health in self.provider_health.items():
            load_distribution["providers"][provider.value] = {
                "current_load": health.current_load,
                "max_concurrent": health.max_concurrent,
                "load_percentage": (health.current_load / health.max_concurrent * 100) if health.max_concurrent > 0 else 0,
                "is_available": health.is_available,
                "success_rate": health.success_rate
            }
        
        return load_distribution
    
    async def start_queue_service(self):
        """启动队列服务"""
        await self.request_queue.start()
        
        # 设置提供商容量
        for provider in AIProvider:
            if provider != AIProvider.CUSTOM:
                health = self.provider_health.get(provider)
                if health:
                    await self.request_queue.set_provider_capacity(
                        provider.value, 
                        health.max_concurrent
                    )
        
        # 注册事件回调
        self.request_queue.register_event_callback(
            'provider_overloaded', 
            self._handle_provider_overloaded
        )
        
        self.logger.info("AI Router queue service started")
    
    async def stop_queue_service(self):
        """停止队列服务"""
        await self.request_queue.stop()
        self.logger.info("AI Router queue service stopped")
    
    async def queue_request(self, 
                          user_id: int,
                          content: str,
                          priority: str = "normal",
                          timeout_seconds: int = 300,
                          context: Optional[Dict[str, Any]] = None) -> str:
        """
        将请求加入队列
        
        Args:
            user_id: 用户ID
            content: 请求内容
            priority: 请求优先级 (low, normal, high, urgent, critical)
            timeout_seconds: 超时时间
            context: 请求上下文
            
        Returns:
            str: 请求ID
        """
        # 转换优先级
        priority_map = {
            "low": RequestPriority.LOW,
            "normal": RequestPriority.NORMAL,
            "high": RequestPriority.HIGH,
            "urgent": RequestPriority.URGENT,
            "critical": RequestPriority.CRITICAL
        }
        
        queue_priority = priority_map.get(priority.lower(), RequestPriority.NORMAL)
        
        return await self.request_queue.enqueue_request(
            user_id=user_id,
            content=content,
            priority=queue_priority,
            timeout_seconds=timeout_seconds,
            context=context or {}
        )
    
    async def process_queued_request(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """
        处理队列中的请求
        
        Args:
            provider_id: 处理提供商ID
            
        Returns:
            Optional[Dict[str, Any]]: 请求信息，如果没有可处理的请求则返回None
        """
        queued_request = await self.request_queue.dequeue_request(provider_id)
        
        if not queued_request:
            return None
        
        # 转换为AIRequest对象进行路由决策
        ai_request = AIRequest(
            content=queued_request.content,
            user_id=queued_request.user_id,
            context=queued_request.context,
            priority=self._convert_queue_priority_to_string(queued_request.priority)
        )
        
        # 进行路由决策（但已经指定了提供商）
        try:
            provider_enum = AIProvider(provider_id)
        except ValueError:
            provider_enum = AIProvider.OPENAI  # 默认提供商
        
        return {
            'request_id': queued_request.request_id,
            'ai_request': ai_request,
            'queued_request': queued_request,
            'selected_provider': provider_enum,
            'priority': queued_request.priority.name,
            'created_at': queued_request.created_at,
            'started_at': queued_request.started_at
        }
    
    async def complete_queued_request(self, request_id: str, 
                                    result: Any = None, 
                                    error: Optional[str] = None):
        """
        完成队列中的请求
        
        Args:
            request_id: 请求ID
            result: 处理结果
            error: 错误信息
        """
        await self.request_queue.complete_request(request_id, result, error)
        
        # 更新提供商负载状态
        request_status = await self.request_queue.get_request_status(request_id)
        if request_status and request_status.get('assigned_provider'):
            provider_id = request_status['assigned_provider']
            try:
                provider_enum = AIProvider(provider_id)
                await self._release_provider_load(provider_enum)
            except ValueError:
                pass
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        metrics = await self.request_queue.get_queue_metrics()
        
        return {
            'queue_metrics': {
                'total_requests': metrics.total_requests,
                'pending_requests': metrics.pending_requests,
                'processing_requests': metrics.processing_requests,
                'completed_requests': metrics.completed_requests,
                'failed_requests': metrics.failed_requests,
                'cancelled_requests': metrics.cancelled_requests,
                'timeout_requests': metrics.timeout_requests,
                'average_wait_time': metrics.average_wait_time,
                'average_processing_time': metrics.average_processing_time,
                'throughput_per_minute': metrics.throughput_per_minute,
                'queue_length_by_priority': {
                    priority.name: count 
                    for priority, count in metrics.queue_length_by_priority.items()
                },
                'provider_load_distribution': metrics.provider_load_distribution
            },
            'provider_loads': {
                provider.value: await self.request_queue.get_provider_load(provider.value)
                for provider in AIProvider if provider != AIProvider.CUSTOM
            }
        }
    
    async def route_request_with_queue(self, request: AIRequest) -> Dict[str, Any]:
        """
        使用队列的智能路由请求
        
        Args:
            request: AI请求对象
            
        Returns:
            Dict[str, Any]: 路由结果，包含队列信息
        """
        # 首先尝试直接路由（如果有可用资源）
        routing_decision = await self.route_request(request)
        
        # 检查选定的提供商是否有可用容量
        current_load, max_capacity = await self.request_queue.get_provider_load(
            routing_decision.selected_provider.value
        )
        
        if current_load < max_capacity and routing_decision.confidence > 0.5:
            # 直接处理
            return {
                'routing_type': 'direct',
                'routing_decision': routing_decision,
                'queue_position': None,
                'estimated_wait_time': 0
            }
        else:
            # 加入队列
            priority = self._convert_string_priority_to_queue(request.priority)
            request_id = await self.request_queue.enqueue_request(
                user_id=request.user_id,
                content=request.content,
                priority=priority,
                context=request.context
            )
            
            # 估算等待时间
            queue_metrics = await self.request_queue.get_queue_metrics()
            estimated_wait_time = self._estimate_queue_wait_time(
                priority, queue_metrics
            )
            
            return {
                'routing_type': 'queued',
                'request_id': request_id,
                'queue_position': queue_metrics.pending_requests,
                'estimated_wait_time': estimated_wait_time,
                'routing_decision': routing_decision
            }
    
    def _convert_queue_priority_to_string(self, priority: RequestPriority) -> str:
        """转换队列优先级为字符串"""
        priority_map = {
            RequestPriority.LOW: "low",
            RequestPriority.NORMAL: "normal",
            RequestPriority.HIGH: "high",
            RequestPriority.URGENT: "urgent",
            RequestPriority.CRITICAL: "critical"
        }
        return priority_map.get(priority, "normal")
    
    def _convert_string_priority_to_queue(self, priority: str) -> RequestPriority:
        """转换字符串优先级为队列优先级"""
        priority_map = {
            "low": RequestPriority.LOW,
            "normal": RequestPriority.NORMAL,
            "high": RequestPriority.HIGH,
            "urgent": RequestPriority.URGENT,
            "critical": RequestPriority.CRITICAL
        }
        return priority_map.get(priority.lower(), RequestPriority.NORMAL)
    
    def _estimate_queue_wait_time(self, priority: RequestPriority, 
                                 metrics: Any) -> float:
        """估算队列等待时间"""
        # 基于优先级和当前队列状态估算等待时间
        base_wait_time = metrics.average_wait_time or 30.0  # 默认30秒
        
        # 优先级调整因子
        priority_factors = {
            RequestPriority.CRITICAL: 0.1,
            RequestPriority.URGENT: 0.3,
            RequestPriority.HIGH: 0.6,
            RequestPriority.NORMAL: 1.0,
            RequestPriority.LOW: 1.5
        }
        
        factor = priority_factors.get(priority, 1.0)
        
        # 考虑队列长度
        queue_length_factor = 1 + (metrics.pending_requests / 10.0)
        
        return base_wait_time * factor * queue_length_factor
    
    async def _handle_provider_overloaded(self, provider_id: str):
        """处理提供商过载事件"""
        self.logger.warning(f"Provider {provider_id} is overloaded")
        
        # 可以在这里实现自动扩容或负载重分配逻辑
        try:
            provider_enum = AIProvider(provider_id)
            health = self.provider_health.get(provider_enum)
            if health:
                # 临时降低该提供商的优先级
                health.success_rate *= 0.9  # 降低成功率评分
                self.logger.info(f"Temporarily reduced priority for overloaded provider {provider_id}")
        except ValueError:
            pass
    
    async def get_load_balancing_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计信息"""
        stats = {
            'timestamp': datetime.utcnow().isoformat(),
            'providers': {},
            'queue_metrics': await self.get_queue_status(),
            'load_distribution': self.get_current_load_distribution()
        }
        
        # 添加每个提供商的详细负载信息
        for provider in AIProvider:
            if provider != AIProvider.CUSTOM:
                health = self.provider_health.get(provider)
                current_load, max_capacity = await self.request_queue.get_provider_load(provider.value)
                
                stats['providers'][provider.value] = {
                    'health_status': {
                        'is_available': health.is_available if health else False,
                        'success_rate': health.success_rate if health else 0.0,
                        'response_time': health.response_time if health else 0.0,
                        'error_count': health.error_count if health else 0
                    },
                    'load_status': {
                        'current_load': current_load,
                        'max_capacity': max_capacity,
                        'utilization_rate': (current_load / max_capacity * 100) if max_capacity > 0 else 0,
                        'queue_load': self.load_balancer_state.get(provider, 0)
                    },
                    'performance_score': await self._calculate_provider_performance_score(provider)
                }
        
        return stats
    
    async def _calculate_provider_performance_score(self, provider: AIProvider) -> float:
        """计算提供商性能评分"""
        health = self.provider_health.get(provider)
        if not health:
            return 0.0
        
        # 综合评分：可用性 + 成功率 + 响应时间 + 负载状态
        availability_score = 1.0 if health.is_available else 0.0
        success_rate_score = health.success_rate
        response_time_score = max(0.0, 1.0 - (health.response_time / 30.0))  # 30秒为基准
        load_score = 1.0 - (health.current_load / health.max_concurrent) if health.max_concurrent > 0 else 0.0
        
        # 加权平均
        performance_score = (
            availability_score * 0.3 +
            success_rate_score * 0.3 +
            response_time_score * 0.2 +
            load_score * 0.2
        )
        
        return min(max(performance_score, 0.0), 1.0)
    
    async def get_adapter_for_request(self, request) -> Optional[Any]:
        """
        获取适合请求的AI适配器
        
        Args:
            request: AI请求对象
            
        Returns:
            Optional[Any]: AI适配器实例，如果没有可用的适配器则返回None
        """
        try:
            # 如果没有提供请求，使用默认提供商
            if not request:
                from ..adapters.adapter_manager import get_adapter_manager
                adapter_manager = get_adapter_manager()
                return await adapter_manager.get_adapter(AIProvider.OPENAI)
            
            # 进行路由决策
            routing_decision = await self.route_request(request)
            
            if not routing_decision:
                self.logger.warning("No routing decision available")
                return None
            
            # 获取适配器管理器
            from ..adapters.adapter_manager import get_adapter_manager
            adapter_manager = get_adapter_manager()
            
            # 获取选定提供商的适配器
            adapter = await adapter_manager.get_adapter(routing_decision.selected_provider)
            
            if not adapter:
                self.logger.warning(f"No adapter available for provider {routing_decision.selected_provider.value}")
                
                # 尝试备用提供商
                for fallback_provider in routing_decision.fallback_providers:
                    fallback_adapter = await adapter_manager.get_adapter(fallback_provider)
                    if fallback_adapter:
                        self.logger.info(f"Using fallback adapter: {fallback_provider.value}")
                        return fallback_adapter
                
                return None
            
            return adapter
            
        except Exception as e:
            self.logger.error(f"Error getting adapter for request: {str(e)}")
            return None   
 
    # ==================== 中文内容优化路由方法 ====================
    
    async def analyze_chinese_content(self, content: str) -> Dict[str, Any]:
        """
        分析中文内容特征
        
        Args:
            content: 待分析的中文内容
            
        Returns:
            Dict[str, Any]: 中文内容分析结果
        """
        try:
            analysis = self.chinese_router.analyze_chinese_content(content)
            
            return {
                "is_chinese": self.chinese_router.is_chinese_content(content),
                "content_type": analysis.content_type.value,
                "complexity": analysis.complexity.value,
                "cultural_context": analysis.cultural_context.value,
                "chinese_ratio": analysis.chinese_ratio,
                "traditional_ratio": analysis.traditional_ratio,
                "technical_terms": analysis.technical_terms,
                "cultural_references": analysis.cultural_references,
                "formality_level": analysis.formality_level,
                "confidence_score": analysis.confidence_score,
                "language_features": {
                    "has_idioms": analysis.has_idioms,
                    "has_classical_chinese": analysis.has_classical_chinese,
                    "has_regional_dialect": analysis.has_regional_dialect,
                    "has_internet_slang": analysis.has_internet_slang
                },
                "domain": analysis.domain,
                "industry_terms": analysis.industry_terms
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing Chinese content: {e}")
            return {
                "is_chinese": False,
                "error": str(e)
            }
    
    async def get_chinese_provider_ranking(self, content: str, 
                                         available_providers: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        获取中文内容的AI提供商排名
        
        Args:
            content: 中文内容
            available_providers: 可用提供商列表，如果为None则使用所有提供商
            
        Returns:
            List[Dict[str, Any]]: 提供商排名列表
        """
        try:
            if available_providers is None:
                available_providers = [provider.value for provider in AIProvider 
                                     if provider != AIProvider.CUSTOM]
            
            # 获取排名
            rankings = self.chinese_router.get_chinese_provider_ranking(content, available_providers)
            
            # 转换为详细信息
            detailed_rankings = []
            for provider_name, score in rankings:
                try:
                    provider = AIProvider(provider_name)
                    health = self.provider_health.get(provider)
                    
                    detailed_rankings.append({
                        "provider": provider_name,
                        "score": score,
                        "is_available": health.is_available if health else False,
                        "success_rate": health.success_rate if health else 0.0,
                        "response_time": health.response_time if health else 0.0,
                        "current_load": health.current_load if health else 0,
                        "chinese_capabilities": self.chinese_router.chinese_provider_capabilities.get(
                            provider_name, {}
                        )
                    })
                except ValueError:
                    # 跳过无效的提供商名称
                    continue
            
            return detailed_rankings
            
        except Exception as e:
            self.logger.error(f"Error getting Chinese provider ranking: {e}")
            return []
    
    async def get_chinese_optimization_suggestions(self, content: str, 
                                                 provider: Optional[str] = None) -> Dict[str, Any]:
        """
        获取中文内容优化建议
        
        Args:
            content: 中文内容
            provider: AI提供商，如果为None则自动选择最佳提供商
            
        Returns:
            Dict[str, Any]: 优化建议
        """
        try:
            # 如果没有指定提供商，自动选择最佳提供商
            if provider is None:
                available_providers = [p.value for p in AIProvider if p != AIProvider.CUSTOM]
                chinese_decision = self.chinese_router.route_chinese_content(
                    content, available_providers, priority="quality"
                )
                provider = chinese_decision.recommended_provider
            
            # 获取优化建议
            suggestions = self.chinese_router.get_optimization_suggestions(content, provider)
            
            # 添加路由相关信息
            suggestions["routing_info"] = {
                "recommended_provider": provider,
                "routing_timestamp": datetime.utcnow().isoformat(),
                "available_alternatives": await self.get_chinese_provider_ranking(content)
            }
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error getting Chinese optimization suggestions: {e}")
            return {
                "error": str(e),
                "content_analysis": {},
                "provider_optimization": {},
                "quality_expectations": {}
            }
    
    async def route_chinese_request(self, request: AIRequest) -> RoutingDecision:
        """
        专门为中文请求进行路由
        
        Args:
            request: AI请求对象
            
        Returns:
            RoutingDecision: 路由决策结果
        """
        try:
            self.logger.info(f"Routing Chinese request {request.request_id}")
            
            # 获取可用提供商
            available_providers = await self._get_available_providers(request)
            available_provider_names = [provider.value for provider in available_providers]
            
            if not available_provider_names:
                return self._create_fallback_decision("No available providers for Chinese content")
            
            # 使用中文路由器
            priority = "quality"
            if request.routing_strategy == RoutingStrategy.COST_FIRST:
                priority = "cost"
            elif request.routing_strategy == RoutingStrategy.SPEED_FIRST:
                priority = "speed"
            
            chinese_decision = self.chinese_router.route_chinese_content(
                request.content, available_provider_names, priority=priority
            )
            
            # 转换为标准路由决策
            try:
                selected_provider = AIProvider(chinese_decision.recommended_provider)
                
                # 验证提供商可用性
                if selected_provider not in available_providers:
                    self.logger.warning(
                        f"Chinese router recommended unavailable provider: {chinese_decision.recommended_provider}"
                    )
                    # 选择第一个可用的中文优化提供商
                    chinese_providers = [AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI, 
                                       AIProvider.ZHIPU_CHATGLM]
                    for provider in chinese_providers:
                        if provider in available_providers:
                            selected_provider = provider
                            break
                    else:
                        selected_provider = available_providers[0]
                
                # 估算成本和时间
                estimated_cost = await self._estimate_cost(selected_provider, request)
                estimated_time = await self._estimate_response_time(selected_provider, request)
                
                # 获取备选提供商（优先中文优化提供商）
                fallback_providers = []
                chinese_providers = [AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI, 
                                   AIProvider.ZHIPU_CHATGLM, AIProvider.XUNFEI_XINGHUO]
                
                for provider in chinese_providers:
                    if provider in available_providers and provider != selected_provider:
                        fallback_providers.append(provider)
                
                # 添加其他可用提供商
                for provider in available_providers:
                    if provider not in fallback_providers and provider != selected_provider:
                        fallback_providers.append(provider)
                
                # 增强推理说明
                enhanced_reasoning = (
                    f"Chinese content optimization routing: {chinese_decision.reasoning}. "
                    f"Optimization strategy: {chinese_decision.optimization_strategy}. "
                    f"Cultural adaptations: {len(chinese_decision.cultural_adaptations)} items. "
                    f"Language enhancements: {len(chinese_decision.language_enhancements)} items. "
                    f"Estimated quality score: {chinese_decision.estimated_quality_score:.3f}"
                )
                
                return RoutingDecision(
                    selected_provider=selected_provider,
                    confidence=chinese_decision.confidence,
                    reasoning=enhanced_reasoning,
                    fallback_providers=fallback_providers[:3],  # 最多3个备选
                    estimated_cost=estimated_cost,
                    estimated_time=estimated_time,
                    routing_strategy_used=RoutingStrategy.ACCURACY_FIRST
                )
                
            except ValueError as e:
                self.logger.error(f"Error converting Chinese routing decision: {e}")
                return self._create_fallback_decision(f"Chinese routing conversion error: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"Error in Chinese request routing: {e}")
            return self._create_fallback_decision(f"Chinese routing error: {str(e)}")
    
    def is_chinese_content_request(self, request: AIRequest) -> bool:
        """
        判断是否为中文内容请求
        
        Args:
            request: AI请求对象
            
        Returns:
            bool: 是否为中文内容请求
        """
        return (
            request.task_type == TaskType.CHINESE_CONTENT or
            self.chinese_router.is_chinese_content(request.content, threshold=0.3)
        )
    
    async def get_chinese_routing_statistics(self) -> Dict[str, Any]:
        """
        获取中文路由统计信息
        
        Returns:
            Dict[str, Any]: 中文路由统计信息
        """
        try:
            # 获取中文优化提供商的统计信息
            chinese_providers = [AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI, 
                               AIProvider.ZHIPU_CHATGLM, AIProvider.XUNFEI_XINGHUO]
            
            chinese_stats = {}
            total_chinese_requests = 0
            total_chinese_success = 0
            
            for provider in chinese_providers:
                health = self.provider_health.get(provider)
                if health:
                    # 估算中文请求数量（基于中文支持能力）
                    capabilities = self.provider_capabilities.get(provider, {})
                    chinese_support = capabilities.get("chinese_support", 0.0)
                    
                    # 模拟中文请求统计（实际实现中应该从数据库获取）
                    estimated_chinese_requests = int(health.current_load * chinese_support)
                    estimated_chinese_success = int(estimated_chinese_requests * health.success_rate)
                    
                    total_chinese_requests += estimated_chinese_requests
                    total_chinese_success += estimated_chinese_success
                    
                    chinese_stats[provider.value] = {
                        "chinese_support_score": chinese_support,
                        "estimated_chinese_requests": estimated_chinese_requests,
                        "estimated_success_rate": health.success_rate,
                        "is_available": health.is_available,
                        "response_time": health.response_time,
                        "capabilities": self.chinese_router.chinese_provider_capabilities.get(
                            provider.value, {}
                        )
                    }
            
            return {
                "total_chinese_requests": total_chinese_requests,
                "total_chinese_success": total_chinese_success,
                "overall_chinese_success_rate": (
                    total_chinese_success / total_chinese_requests 
                    if total_chinese_requests > 0 else 0.0
                ),
                "provider_stats": chinese_stats,
                "chinese_router_config": {
                    "detection_threshold": 0.3,
                    "supported_content_types": [ct.value for ct in self.chinese_router.ChineseContentType],
                    "supported_cultural_contexts": [cc.value for cc in self.chinese_router.CulturalContext]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Chinese routing statistics: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def optimize_chinese_routing_config(self) -> Dict[str, Any]:
        """
        优化中文路由配置
        
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            optimization_results = {
                "optimizations_applied": [],
                "performance_improvements": {},
                "recommendations": []
            }
            
            # 1. 分析中文提供商性能
            chinese_providers = [AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI, 
                               AIProvider.ZHIPU_CHATGLM, AIProvider.XUNFEI_XINGHUO]
            
            best_performer = None
            best_score = 0.0
            
            for provider in chinese_providers:
                health = self.provider_health.get(provider)
                if health and health.is_available:
                    capabilities = self.provider_capabilities.get(provider, {})
                    chinese_support = capabilities.get("chinese_support", 0.0)
                    
                    # 综合评分
                    score = (health.success_rate * 0.4 + 
                            chinese_support * 0.4 + 
                            (1.0 - health.response_time / 10.0) * 0.2)
                    
                    if score > best_score:
                        best_score = score
                        best_performer = provider
            
            if best_performer:
                optimization_results["optimizations_applied"].append(
                    f"Updated primary Chinese provider to {best_performer.value}"
                )
                optimization_results["performance_improvements"]["primary_provider"] = {
                    "provider": best_performer.value,
                    "score": best_score
                }
            
            # 2. 生成优化建议
            recommendations = []
            
            # 检查提供商可用性
            unavailable_providers = [
                provider.value for provider in chinese_providers
                if not self.provider_health.get(provider, ProviderHealth(provider)).is_available
            ]
            
            if unavailable_providers:
                recommendations.append(
                    f"Consider enabling backup providers for unavailable Chinese providers: {unavailable_providers}"
                )
            
            # 检查负载分布
            load_distribution = {}
            for provider in chinese_providers:
                health = self.provider_health.get(provider)
                if health:
                    load_distribution[provider.value] = health.current_load
            
            if load_distribution:
                max_load = max(load_distribution.values())
                min_load = min(load_distribution.values())
                
                if max_load - min_load > 50:  # 负载差异过大
                    recommendations.append(
                        "Consider implementing better load balancing for Chinese providers"
                    )
            
            optimization_results["recommendations"] = recommendations
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Error optimizing Chinese routing config: {e}")
            return {
                "error": str(e),
                "optimizations_applied": [],
                "performance_improvements": {},
                "recommendations": []
            }