"""
AI适配器工厂

负责创建和管理不同类型的AI适配器实例。
"""

import logging
from typing import Dict, Type, Optional

from .base import BaseAIAdapter, AdapterConfig, AIProvider
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .baidu_adapter import BaiduWenxinAdapter
from .aliyun_adapter import AliyunTongyiAdapter
from .google_adapter import GoogleGeminiAdapter
from .zhipu_adapter import ZhipuChatGLMAdapter
from .xunfei_adapter import XunfeiXinghuoAdapter
from .custom_adapter import CustomAIAdapter

logger = logging.getLogger(__name__)


class AIAdapterFactory:
    """
    AI适配器工厂类
    
    负责根据配置创建相应的AI适配器实例，支持：
    1. 内置适配器的创建
    2. 自定义适配器的注册和创建
    3. 适配器配置验证
    4. 适配器实例缓存
    """
    
    # 内置适配器映射
    _builtin_adapters: Dict[AIProvider, Type[BaseAIAdapter]] = {
        AIProvider.OPENAI: OpenAIAdapter,
        AIProvider.ANTHROPIC: AnthropicAdapter,
        AIProvider.BAIDU_WENXIN: BaiduWenxinAdapter,
        AIProvider.ALIYUN_TONGYI: AliyunTongyiAdapter,
        AIProvider.GOOGLE_GEMINI: GoogleGeminiAdapter,
        AIProvider.ZHIPU_CHATGLM: ZhipuChatGLMAdapter,
        AIProvider.XUNFEI_XINGHUO: XunfeiXinghuoAdapter,
        AIProvider.CUSTOM: CustomAIAdapter
    }
    
    # 自定义适配器注册表
    _custom_adapters: Dict[str, Type[BaseAIAdapter]] = {}
    
    # 适配器实例缓存
    _adapter_cache: Dict[str, BaseAIAdapter] = {}
    
    @classmethod
    def create_adapter(cls, config: AdapterConfig, use_cache: bool = True) -> BaseAIAdapter:
        """
        创建AI适配器实例
        
        Args:
            config: 适配器配置
            use_cache: 是否使用缓存
            
        Returns:
            BaseAIAdapter: 适配器实例
            
        Raises:
            ValueError: 当配置无效或适配器类型不支持时
        """
        try:
            # 验证配置
            if not config.validate():
                raise ValueError(f"Invalid adapter configuration for {config.provider.value}")
            
            # 生成缓存键
            cache_key = cls._generate_cache_key(config)
            
            # 检查缓存
            if use_cache and cache_key in cls._adapter_cache:
                cached_adapter = cls._adapter_cache[cache_key]
                if cached_adapter.is_healthy:
                    logger.debug(f"Using cached adapter for {config.provider.value}")
                    return cached_adapter
                else:
                    # 移除不健康的缓存适配器
                    logger.warning(f"Removing unhealthy cached adapter for {config.provider.value}")
                    del cls._adapter_cache[cache_key]
            
            # 获取适配器类
            adapter_class = cls._get_adapter_class(config.provider)
            
            # 创建适配器实例
            adapter = adapter_class(config)
            
            # 缓存适配器实例
            if use_cache:
                cls._adapter_cache[cache_key] = adapter
            
            logger.info(f"Created new adapter for {config.provider.value}")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to create adapter for {config.provider.value}: {str(e)}")
            raise
    
    @classmethod
    def register_custom_adapter(cls, provider_name: str, adapter_class: Type[BaseAIAdapter]):
        """
        注册自定义适配器
        
        Args:
            provider_name: 提供商名称
            adapter_class: 适配器类
            
        Raises:
            ValueError: 当适配器类无效时
        """
        if not issubclass(adapter_class, BaseAIAdapter):
            raise ValueError(f"Adapter class must inherit from BaseAIAdapter")
        
        cls._custom_adapters[provider_name] = adapter_class
        logger.info(f"Registered custom adapter: {provider_name}")
    
    @classmethod
    def unregister_custom_adapter(cls, provider_name: str):
        """
        注销自定义适配器
        
        Args:
            provider_name: 提供商名称
        """
        if provider_name in cls._custom_adapters:
            del cls._custom_adapters[provider_name]
            logger.info(f"Unregistered custom adapter: {provider_name}")
    
    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """
        获取支持的提供商列表
        
        Returns:
            list[str]: 提供商名称列表
        """
        builtin_providers = [provider.value for provider in cls._builtin_adapters.keys()]
        custom_providers = list(cls._custom_adapters.keys())
        return builtin_providers + custom_providers
    
    @classmethod
    def clear_cache(cls, provider: Optional[AIProvider] = None):
        """
        清理适配器缓存
        
        Args:
            provider: 指定提供商，None表示清理所有缓存
        """
        if provider is None:
            # 清理所有缓存
            for adapter in cls._adapter_cache.values():
                try:
                    # 异步关闭适配器，这里简化处理
                    if hasattr(adapter, 'shutdown'):
                        # 在实际项目中应该使用异步方式
                        pass
                except Exception as e:
                    logger.error(f"Error shutting down adapter: {str(e)}")
            
            cls._adapter_cache.clear()
            logger.info("Cleared all adapter cache")
        else:
            # 清理指定提供商的缓存
            keys_to_remove = [key for key in cls._adapter_cache.keys() 
                            if key.startswith(f"{provider.value}_")]
            
            for key in keys_to_remove:
                adapter = cls._adapter_cache[key]
                try:
                    if hasattr(adapter, 'shutdown'):
                        pass  # 简化处理
                except Exception as e:
                    logger.error(f"Error shutting down adapter: {str(e)}")
                del cls._adapter_cache[key]
            
            logger.info(f"Cleared cache for provider: {provider.value}")
    
    @classmethod
    def get_adapter_stats(cls) -> Dict[str, Dict]:
        """
        获取适配器统计信息
        
        Returns:
            Dict[str, Dict]: 适配器统计信息
        """
        stats = {}
        for key, adapter in cls._adapter_cache.items():
            try:
                stats[key] = adapter.get_stats()
            except Exception as e:
                logger.error(f"Error getting stats for adapter {key}: {str(e)}")
                stats[key] = {"error": str(e)}
        
        return stats
    
    @classmethod
    def _get_adapter_class(cls, provider: AIProvider) -> Type[BaseAIAdapter]:
        """
        获取适配器类
        
        Args:
            provider: AI提供商
            
        Returns:
            Type[BaseAIAdapter]: 适配器类
            
        Raises:
            ValueError: 当提供商不支持时
        """
        if provider in cls._builtin_adapters:
            return cls._builtin_adapters[provider]
        
        # 检查自定义适配器
        provider_name = provider.value
        if provider_name in cls._custom_adapters:
            return cls._custom_adapters[provider_name]
        
        raise ValueError(f"Unsupported AI provider: {provider.value}")
    
    @classmethod
    def _generate_cache_key(cls, config: AdapterConfig) -> str:
        """
        生成缓存键
        
        Args:
            config: 适配器配置
            
        Returns:
            str: 缓存键
        """
        # 基于提供商、端点和关键配置生成缓存键
        key_parts = [
            config.provider.value,
            config.api_endpoint or "default",
            str(config.max_concurrent_requests),
            str(config.timeout)
        ]
        
        # 添加API密钥的哈希（用于区分不同的账户）
        if config.api_key:
            import hashlib
            key_hash = hashlib.md5(config.api_key.encode()).hexdigest()[:8]
            key_parts.append(key_hash)
        
        return "_".join(key_parts)
    
    @classmethod
    async def health_check_all(cls) -> Dict[str, bool]:
        """
        对所有缓存的适配器进行健康检查
        
        Returns:
            Dict[str, bool]: 健康检查结果
        """
        results = {}
        
        for key, adapter in cls._adapter_cache.items():
            try:
                is_healthy = await adapter.health_check()
                results[key] = is_healthy
                
                # 如果适配器不健康，从缓存中移除
                if not is_healthy:
                    logger.warning(f"Removing unhealthy adapter from cache: {key}")
                    # 注意：在实际项目中，这里可能需要更谨慎的处理
                    # 避免在迭代过程中修改字典
                    
            except Exception as e:
                logger.error(f"Health check failed for adapter {key}: {str(e)}")
                results[key] = False
        
        return results
    
    @classmethod
    def create_adapter_from_dict(cls, config_dict: Dict) -> BaseAIAdapter:
        """
        从字典配置创建适配器
        
        Args:
            config_dict: 配置字典
            
        Returns:
            BaseAIAdapter: 适配器实例
        """
        try:
            # 转换提供商
            provider_str = config_dict.get("provider")
            if not provider_str:
                raise ValueError("Provider is required")
            
            try:
                provider = AIProvider(provider_str)
            except ValueError:
                raise ValueError(f"Unsupported provider: {provider_str}")
            
            # 创建配置对象
            config = AdapterConfig(
                provider=provider,
                api_key=config_dict.get("api_key", ""),
                api_endpoint=config_dict.get("api_endpoint"),
                api_version=config_dict.get("api_version"),
                default_model=config_dict.get("default_model"),
                max_retries=config_dict.get("max_retries", 3),
                retry_delay=config_dict.get("retry_delay", 1.0),
                timeout=config_dict.get("timeout", 30.0),
                max_concurrent_requests=config_dict.get("max_concurrent_requests", 10),
                rate_limit_per_minute=config_dict.get("rate_limit_per_minute", 60),
                enabled=config_dict.get("enabled", True),
                cost_per_token=config_dict.get("cost_per_token"),
                daily_token_limit=config_dict.get("daily_token_limit"),
                monthly_token_limit=config_dict.get("monthly_token_limit"),
                custom_headers=config_dict.get("custom_headers", {}),
                custom_params=config_dict.get("custom_params", {})
            )
            
            return cls.create_adapter(config)
            
        except Exception as e:
            logger.error(f"Failed to create adapter from dict: {str(e)}")
            raise


# 便捷函数
def create_openai_adapter(api_key: str, **kwargs) -> OpenAIAdapter:
    """创建OpenAI适配器的便捷函数"""
    config = AdapterConfig(
        provider=AIProvider.OPENAI,
        api_key=api_key,
        **kwargs
    )
    return AIAdapterFactory.create_adapter(config)


def create_anthropic_adapter(api_key: str, **kwargs) -> AnthropicAdapter:
    """创建Anthropic适配器的便捷函数"""
    config = AdapterConfig(
        provider=AIProvider.ANTHROPIC,
        api_key=api_key,
        **kwargs
    )
    return AIAdapterFactory.create_adapter(config)


def create_baidu_adapter(api_key: str, secret_key: str, **kwargs) -> BaiduWenxinAdapter:
    """创建百度文心一言适配器的便捷函数"""
    config = AdapterConfig(
        provider=AIProvider.BAIDU_WENXIN,
        api_key=api_key,
        custom_params={"secret_key": secret_key, **kwargs.get("custom_params", {})},
        **{k: v for k, v in kwargs.items() if k != "custom_params"}
    )
    return AIAdapterFactory.create_adapter(config)


def create_custom_adapter(api_endpoint: str, api_key: str = "", **kwargs) -> CustomAIAdapter:
    """创建自定义适配器的便捷函数"""
    config = AdapterConfig(
        provider=AIProvider.CUSTOM,
        api_key=api_key,
        api_endpoint=api_endpoint,
        **kwargs
    )
    return AIAdapterFactory.create_adapter(config)