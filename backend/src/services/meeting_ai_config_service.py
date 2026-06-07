"""
会议AI配置服务

本模块实现会议AI功能的统一配置管理，包括：
- 复用现有的AI服务配置和管理
- 实现会议AI功能的统一配置
- 集成多个AI服务提供商的管理
- 实现AI服务的负载均衡和故障转移

技术特性：
- 与主系统AI助手服务深度集成
- 支持多AI服务提供商配置
- 动态配置更新和热重载
- 服务健康检查和故障转移
- 配置版本管理和回滚
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..core.exceptions import ValidationError, NotFoundError, ConfigurationError
from ..services.ai_assistant_service import AIAssistantService, AIProvider, TaskType
from ..services.ai_router_service import AIRouterService, RoutingStrategy
from ..services.config_service import ConfigService
from ..models.config import Config, ConfigType

logger = logging.getLogger(__name__)
settings = get_settings()


class MeetingAIFeature(Enum):
    """会议AI功能枚举"""
    SUMMARY_GENERATION = "summary_generation"
    DECISION_EXTRACTION = "decision_extraction"
    ACTION_ITEM_EXTRACTION = "action_item_extraction"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    PARTICIPATION_ANALYSIS = "participation_analysis"
    EFFECTIVENESS_ANALYSIS = "effectiveness_analysis"
    MINUTES_GENERATION = "minutes_generation"
    TRANSCRIPTION = "transcription"
    TRANSLATION = "translation"
    IMPROVEMENT_SUGGESTIONS = "improvement_suggestions"


class ServiceHealthStatus(Enum):
    """服务健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class MeetingAIConfig:
    """会议AI配置数据类"""
    feature: MeetingAIFeature
    enabled: bool
    preferred_providers: List[AIProvider]
    fallback_providers: List[AIProvider]
    max_tokens: int
    temperature: float
    timeout_seconds: int
    retry_attempts: int
    quality_threshold: float
    cost_limit_per_request: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'feature': self.feature.value,
            'enabled': self.enabled,
            'preferred_providers': [p.value for p in self.preferred_providers],
            'fallback_providers': [p.value for p in self.fallback_providers],
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'timeout_seconds': self.timeout_seconds,
            'retry_attempts': self.retry_attempts,
            'quality_threshold': self.quality_threshold,
            'cost_limit_per_request': self.cost_limit_per_request
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MeetingAIConfig':
        return cls(
            feature=MeetingAIFeature(data['feature']),
            enabled=data['enabled'],
            preferred_providers=[AIProvider(p) for p in data['preferred_providers']],
            fallback_providers=[AIProvider(p) for p in data['fallback_providers']],
            max_tokens=data['max_tokens'],
            temperature=data['temperature'],
            timeout_seconds=data['timeout_seconds'],
            retry_attempts=data['retry_attempts'],
            quality_threshold=data['quality_threshold'],
            cost_limit_per_request=data['cost_limit_per_request']
        )


@dataclass
class ProviderHealthInfo:
    """AI服务提供商健康信息"""
    provider: AIProvider
    status: ServiceHealthStatus
    response_time_ms: float
    success_rate: float
    error_count: int
    last_check: datetime
    available_models: List[str]
    current_load: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MeetingAIConfigService:
    """会议AI配置管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_assistant_service = None  # Will be initialized lazily
        self.ai_router_service = None  # Will be initialized lazily
        self.config_service = None  # Will be initialized lazily
        
        # 配置缓存
        self._config_cache: Dict[str, MeetingAIConfig] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
        
        # 健康检查缓存
        self._health_cache: Dict[AIProvider, ProviderHealthInfo] = {}
        self._health_cache_expiry: Dict[AIProvider, datetime] = {}
        self._health_cache_ttl = timedelta(minutes=2)
        
        # 默认配置
        self._default_configs = self._initialize_default_configs()
    
    async def _get_ai_assistant_service(self):
        """懒加载AI助手服务"""
        if not self.ai_assistant_service:
            from .ai_assistant_service import AIAssistantService
            self.ai_assistant_service = AIAssistantService(self.db)
        return self.ai_assistant_service
    
    async def _get_ai_router_service(self):
        """懒加载AI路由服务"""
        if not self.ai_router_service:
            from .ai_router_service import AIRouterService
            self.ai_router_service = AIRouterService(self.db)
        return self.ai_router_service
    
    async def _get_config_service(self):
        """懒加载配置服务"""
        if not self.config_service:
            from .config_service import ConfigService
            self.config_service = ConfigService(self.db)
        return self.config_service
    
    def _initialize_default_configs(self) -> Dict[MeetingAIFeature, MeetingAIConfig]:
        """初始化默认配置"""
        defaults = {}
        
        # 会议摘要生成配置
        defaults[MeetingAIFeature.SUMMARY_GENERATION] = MeetingAIConfig(
            feature=MeetingAIFeature.SUMMARY_GENERATION,
            enabled=True,
            preferred_providers=[AIProvider.OPENAI, AIProvider.ANTHROPIC],
            fallback_providers=[AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI],
            max_tokens=2000,
            temperature=0.3,
            timeout_seconds=30,
            retry_attempts=3,
            quality_threshold=0.8,
            cost_limit_per_request=0.5
        )
        
        # 决策提取配置
        defaults[MeetingAIFeature.DECISION_EXTRACTION] = MeetingAIConfig(
            feature=MeetingAIFeature.DECISION_EXTRACTION,
            enabled=True,
            preferred_providers=[AIProvider.ANTHROPIC, AIProvider.OPENAI],
            fallback_providers=[AIProvider.ALIYUN_TONGYI, AIProvider.BAIDU_WENXIN],
            max_tokens=1500,
            temperature=0.2,
            timeout_seconds=25,
            retry_attempts=3,
            quality_threshold=0.85,
            cost_limit_per_request=0.3
        )
        
        # 行动项目提取配置
        defaults[MeetingAIFeature.ACTION_ITEM_EXTRACTION] = MeetingAIConfig(
            feature=MeetingAIFeature.ACTION_ITEM_EXTRACTION,
            enabled=True,
            preferred_providers=[AIProvider.OPENAI, AIProvider.ALIYUN_TONGYI],
            fallback_providers=[AIProvider.ANTHROPIC, AIProvider.BAIDU_WENXIN],
            max_tokens=1200,
            temperature=0.1,
            timeout_seconds=20,
            retry_attempts=3,
            quality_threshold=0.9,
            cost_limit_per_request=0.25
        )
        
        # 情感分析配置
        defaults[MeetingAIFeature.SENTIMENT_ANALYSIS] = MeetingAIConfig(
            feature=MeetingAIFeature.SENTIMENT_ANALYSIS,
            enabled=True,
            preferred_providers=[AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI],
            fallback_providers=[AIProvider.OPENAI, AIProvider.ANTHROPIC],
            max_tokens=800,
            temperature=0.1,
            timeout_seconds=15,
            retry_attempts=2,
            quality_threshold=0.75,
            cost_limit_per_request=0.15
        )
        
        # 参与度分析配置
        defaults[MeetingAIFeature.PARTICIPATION_ANALYSIS] = MeetingAIConfig(
            feature=MeetingAIFeature.PARTICIPATION_ANALYSIS,
            enabled=True,
            preferred_providers=[AIProvider.OPENAI, AIProvider.ANTHROPIC],
            fallback_providers=[AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI],
            max_tokens=1000,
            temperature=0.2,
            timeout_seconds=20,
            retry_attempts=2,
            quality_threshold=0.8,
            cost_limit_per_request=0.2
        )
        
        # 效果分析配置
        defaults[MeetingAIFeature.EFFECTIVENESS_ANALYSIS] = MeetingAIConfig(
            feature=MeetingAIFeature.EFFECTIVENESS_ANALYSIS,
            enabled=True,
            preferred_providers=[AIProvider.ANTHROPIC, AIProvider.OPENAI],
            fallback_providers=[AIProvider.ALIYUN_TONGYI, AIProvider.BAIDU_WENXIN],
            max_tokens=1500,
            temperature=0.3,
            timeout_seconds=30,
            retry_attempts=3,
            quality_threshold=0.85,
            cost_limit_per_request=0.4
        )
        
        # 纪要生成配置
        defaults[MeetingAIFeature.MINUTES_GENERATION] = MeetingAIConfig(
            feature=MeetingAIFeature.MINUTES_GENERATION,
            enabled=True,
            preferred_providers=[AIProvider.OPENAI, AIProvider.ANTHROPIC],
            fallback_providers=[AIProvider.ALIYUN_TONGYI, AIProvider.BAIDU_WENXIN],
            max_tokens=3000,
            temperature=0.2,
            timeout_seconds=45,
            retry_attempts=3,
            quality_threshold=0.9,
            cost_limit_per_request=0.8
        )
        
        # 转录配置
        defaults[MeetingAIFeature.TRANSCRIPTION] = MeetingAIConfig(
            feature=MeetingAIFeature.TRANSCRIPTION,
            enabled=True,
            preferred_providers=[AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI],
            fallback_providers=[AIProvider.OPENAI, AIProvider.ANTHROPIC],
            max_tokens=4000,
            temperature=0.0,
            timeout_seconds=60,
            retry_attempts=2,
            quality_threshold=0.95,
            cost_limit_per_request=1.0
        )
        
        # 翻译配置
        defaults[MeetingAIFeature.TRANSLATION] = MeetingAIConfig(
            feature=MeetingAIFeature.TRANSLATION,
            enabled=False,  # 默认关闭
            preferred_providers=[AIProvider.BAIDU_WENXIN, AIProvider.ALIYUN_TONGYI],
            fallback_providers=[AIProvider.OPENAI, AIProvider.ANTHROPIC],
            max_tokens=2000,
            temperature=0.1,
            timeout_seconds=30,
            retry_attempts=2,
            quality_threshold=0.85,
            cost_limit_per_request=0.3
        )
        
        # 改进建议配置
        defaults[MeetingAIFeature.IMPROVEMENT_SUGGESTIONS] = MeetingAIConfig(
            feature=MeetingAIFeature.IMPROVEMENT_SUGGESTIONS,
            enabled=True,
            preferred_providers=[AIProvider.ANTHROPIC, AIProvider.OPENAI],
            fallback_providers=[AIProvider.ALIYUN_TONGYI, AIProvider.BAIDU_WENXIN],
            max_tokens=1800,
            temperature=0.4,
            timeout_seconds=35,
            retry_attempts=3,
            quality_threshold=0.8,
            cost_limit_per_request=0.6
        )
        
        return defaults
    
    async def get_feature_config(self, feature: MeetingAIFeature) -> MeetingAIConfig:
        """
        获取会议AI功能配置
        
        Args:
            feature: AI功能类型
            
        Returns:
            功能配置对象
        """
        # 检查缓存
        cache_key = f"meeting_ai_config_{feature.value}"
        if cache_key in self._config_cache:
            if datetime.utcnow() < self._cache_expiry.get(cache_key, datetime.min):
                return self._config_cache[cache_key]
        
        try:
            # 从数据库获取配置
            config_service = await self._get_config_service()
            config_data = await config_service.get_config(
                f"meeting_ai.{feature.value}",
                ConfigType.SYSTEM
            )
            
            if config_data and config_data.value:
                config = MeetingAIConfig.from_dict(json.loads(config_data.value))
            else:
                # 使用默认配置
                config = self._default_configs.get(feature)
                if not config:
                    raise ConfigurationError(f"No configuration found for feature: {feature.value}")
            
            # 更新缓存
            self._config_cache[cache_key] = config
            self._cache_expiry[cache_key] = datetime.utcnow() + self._cache_ttl
            
            return config
            
        except Exception as e:
            logger.error(f"Error getting config for feature {feature.value}: {str(e)}")
            # 返回默认配置作为备选
            return self._default_configs.get(feature, self._create_fallback_config(feature))
    
    async def update_feature_config(self, feature: MeetingAIFeature, config: MeetingAIConfig) -> bool:
        """
        更新会议AI功能配置
        
        Args:
            feature: AI功能类型
            config: 新的配置对象
            
        Returns:
            更新是否成功
        """
        try:
            # 验证配置
            await self._validate_config(config)
            
            # 保存到数据库
            config_service = await self._get_config_service()
            await config_service.set_config(
                f"meeting_ai.{feature.value}",
                json.dumps(config.to_dict()),
                ConfigType.SYSTEM,
                description=f"会议AI功能配置: {feature.value}"
            )
            
            # 清除缓存
            cache_key = f"meeting_ai_config_{feature.value}"
            self._config_cache.pop(cache_key, None)
            self._cache_expiry.pop(cache_key, None)
            
            logger.info(f"Updated config for feature {feature.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating config for feature {feature.value}: {str(e)}")
            return False
    
    async def get_all_feature_configs(self) -> Dict[MeetingAIFeature, MeetingAIConfig]:
        """
        获取所有会议AI功能配置
        
        Returns:
            功能配置字典
        """
        configs = {}
        for feature in MeetingAIFeature:
            try:
                configs[feature] = await self.get_feature_config(feature)
            except Exception as e:
                logger.error(f"Error getting config for feature {feature.value}: {str(e)}")
                # 使用默认配置
                configs[feature] = self._default_configs.get(feature, self._create_fallback_config(feature))
        
        return configs
    
    async def check_provider_health(self, provider: AIProvider) -> ProviderHealthInfo:
        """
        检查AI服务提供商健康状态
        
        Args:
            provider: AI服务提供商
            
        Returns:
            健康状态信息
        """
        # 检查缓存
        if provider in self._health_cache:
            if datetime.utcnow() < self._health_cache_expiry.get(provider, datetime.min):
                return self._health_cache[provider]
        
        try:
            # 获取AI助手服务
            ai_service = await self._get_ai_assistant_service()
            
            # 执行健康检查
            start_time = datetime.utcnow()
            
            # 发送测试请求
            test_response = await ai_service.simple_query(
                "Hello, this is a health check.",
                user_id=1,  # 系统用户
                preferred_provider=provider
            )
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # 构建健康信息
            health_info = ProviderHealthInfo(
                provider=provider,
                status=ServiceHealthStatus.HEALTHY if test_response else ServiceHealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                success_rate=1.0 if test_response else 0.0,
                error_count=0 if test_response else 1,
                last_check=datetime.utcnow(),
                available_models=await self._get_available_models(provider),
                current_load=await self._get_current_load(provider)
            )
            
            # 更新缓存
            self._health_cache[provider] = health_info
            self._health_cache_expiry[provider] = datetime.utcnow() + self._health_cache_ttl
            
            return health_info
            
        except Exception as e:
            logger.error(f"Error checking health for provider {provider.value}: {str(e)}")
            
            # 返回不健康状态
            health_info = ProviderHealthInfo(
                provider=provider,
                status=ServiceHealthStatus.UNHEALTHY,
                response_time_ms=0.0,
                success_rate=0.0,
                error_count=1,
                last_check=datetime.utcnow(),
                available_models=[],
                current_load=0.0
            )
            
            # 更新缓存
            self._health_cache[provider] = health_info
            self._health_cache_expiry[provider] = datetime.utcnow() + self._health_cache_ttl
            
            return health_info
    
    async def get_all_provider_health(self) -> Dict[AIProvider, ProviderHealthInfo]:
        """
        获取所有AI服务提供商的健康状态
        
        Returns:
            提供商健康状态字典
        """
        health_info = {}
        
        # 并发检查所有提供商
        tasks = []
        for provider in AIProvider:
            tasks.append(self.check_provider_health(provider))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, provider in enumerate(AIProvider):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Error checking health for provider {provider.value}: {str(result)}")
                # 创建错误状态
                health_info[provider] = ProviderHealthInfo(
                    provider=provider,
                    status=ServiceHealthStatus.UNKNOWN,
                    response_time_ms=0.0,
                    success_rate=0.0,
                    error_count=1,
                    last_check=datetime.utcnow(),
                    available_models=[],
                    current_load=0.0
                )
            else:
                health_info[provider] = result
        
        return health_info
    
    async def get_optimal_provider(self, feature: MeetingAIFeature) -> Optional[AIProvider]:
        """
        获取指定功能的最优AI服务提供商
        
        Args:
            feature: AI功能类型
            
        Returns:
            最优的AI服务提供商，如果没有可用的则返回None
        """
        try:
            # 获取功能配置
            config = await self.get_feature_config(feature)
            
            if not config.enabled:
                return None
            
            # 检查首选提供商的健康状态
            for provider in config.preferred_providers:
                health_info = await self.check_provider_health(provider)
                if health_info.status == ServiceHealthStatus.HEALTHY:
                    return provider
            
            # 检查备选提供商
            for provider in config.fallback_providers:
                health_info = await self.check_provider_health(provider)
                if health_info.status in [ServiceHealthStatus.HEALTHY, ServiceHealthStatus.DEGRADED]:
                    return provider
            
            logger.warning(f"No healthy provider found for feature {feature.value}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting optimal provider for feature {feature.value}: {str(e)}")
            return None
    
    async def reload_configs(self) -> bool:
        """
        重新加载所有配置
        
        Returns:
            重新加载是否成功
        """
        try:
            # 清除所有缓存
            self._config_cache.clear()
            self._cache_expiry.clear()
            self._health_cache.clear()
            self._health_cache_expiry.clear()
            
            # 预加载所有配置
            await self.get_all_feature_configs()
            
            logger.info("Successfully reloaded all meeting AI configs")
            return True
            
        except Exception as e:
            logger.error(f"Error reloading configs: {str(e)}")
            return False
    
    def _create_fallback_config(self, feature: MeetingAIFeature) -> MeetingAIConfig:
        """创建备选配置"""
        return MeetingAIConfig(
            feature=feature,
            enabled=False,  # 默认关闭未知功能
            preferred_providers=[AIProvider.OPENAI],
            fallback_providers=[AIProvider.BAIDU_WENXIN],
            max_tokens=1000,
            temperature=0.3,
            timeout_seconds=30,
            retry_attempts=2,
            quality_threshold=0.7,
            cost_limit_per_request=0.5
        )
    
    async def _validate_config(self, config: MeetingAIConfig) -> None:
        """验证配置有效性"""
        if config.max_tokens <= 0 or config.max_tokens > 10000:
            raise ValidationError("max_tokens must be between 1 and 10000")
        
        if config.temperature < 0.0 or config.temperature > 2.0:
            raise ValidationError("temperature must be between 0.0 and 2.0")
        
        if config.timeout_seconds <= 0 or config.timeout_seconds > 300:
            raise ValidationError("timeout_seconds must be between 1 and 300")
        
        if config.retry_attempts < 0 or config.retry_attempts > 10:
            raise ValidationError("retry_attempts must be between 0 and 10")
        
        if config.quality_threshold < 0.0 or config.quality_threshold > 1.0:
            raise ValidationError("quality_threshold must be between 0.0 and 1.0")
        
        if config.cost_limit_per_request <= 0.0:
            raise ValidationError("cost_limit_per_request must be greater than 0")
    
    async def _get_available_models(self, provider: AIProvider) -> List[str]:
        """获取提供商可用模型列表"""
        # 这里应该实现获取各个提供商可用模型的逻辑
        # 暂时返回模拟数据
        model_map = {
            AIProvider.OPENAI: ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
            AIProvider.ANTHROPIC: ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            AIProvider.BAIDU_WENXIN: ["ernie-bot", "ernie-bot-turbo", "ernie-bot-4"],
            AIProvider.ALIYUN_TONGYI: ["qwen-turbo", "qwen-plus", "qwen-max"],
            AIProvider.GOOGLE_GEMINI: ["gemini-pro", "gemini-pro-vision"]
        }
        return model_map.get(provider, [])
    
    async def _get_current_load(self, provider: AIProvider) -> float:
        """获取提供商当前负载"""
        # 这里应该实现获取提供商当前负载的逻辑
        # 暂时返回模拟数据
        return 0.5  # 50%负载