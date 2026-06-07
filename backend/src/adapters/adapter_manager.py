"""
AI适配器管理器

统一管理所有AI服务提供商的适配器，提供：
1. 适配器注册和初始化
2. 适配器获取和选择
3. 适配器健康检查
4. 适配器配置管理
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone

from .base import BaseAIAdapter, AdapterConfig, AIProvider
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .baidu_adapter import BaiduAdapter
from .aliyun_adapter import AliyunAdapter
from .google_adapter import GoogleAdapter
from .zhipu_adapter import ZhipuAdapter
from .xunfei_adapter import XunfeiAdapter
from .custom_adapter import CustomAdapter

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AdapterManager:
    """AI适配器管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 适配器实例缓存
        self.adapters: Dict[AIProvider, BaseAIAdapter] = {}
        
        # 适配器配置
        self.adapter_configs: Dict[AIProvider, AdapterConfig] = {}
        
        # 适配器类映射
        self.adapter_classes = {
            AIProvider.OPENAI: OpenAIAdapter,
            AIProvider.ANTHROPIC: AnthropicAdapter,
            AIProvider.BAIDU_WENXIN: BaiduAdapter,
            AIProvider.ALIYUN_TONGYI: AliyunAdapter,
            AIProvider.GOOGLE_GEMINI: GoogleAdapter,
            AIProvider.ZHIPU_CHATGLM: ZhipuAdapter,
            AIProvider.XUNFEI_XINGHUO: XunfeiAdapter,
            AIProvider.CUSTOM: CustomAdapter
        }
        
        # 初始化状态
        self.initialized = False
        
    async def initialize(self):
        """初始化适配器管理器"""
        try:
            self.logger.info("Initializing adapter manager...")
            
            # 加载配置
            await self._load_configurations()
            
            # 初始化适配器
            await self._initialize_adapters()
            
            # 执行健康检查
            await self._initial_health_check()
            
            self.initialized = True
            self.logger.info("Adapter manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adapter manager: {e}")
            raise
    
    async def _load_configurations(self):
        """加载适配器配置"""
        # OpenAI配置
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            self.adapter_configs[AIProvider.OPENAI] = AdapterConfig(
                provider=AIProvider.OPENAI,
                api_key=settings.OPENAI_API_KEY,
                api_endpoint=getattr(settings, 'OPENAI_API_ENDPOINT', None),
                default_model="gpt-3.5-turbo",
                max_retries=3,
                timeout=30.0,
                cost_per_token=0.002,
                enabled=True
            )
        
        # Anthropic配置
        if hasattr(settings, 'CLAUDE_API_KEY') and settings.CLAUDE_API_KEY:
            self.adapter_configs[AIProvider.ANTHROPIC] = AdapterConfig(
                provider=AIProvider.ANTHROPIC,
                api_key=settings.CLAUDE_API_KEY,
                api_endpoint=getattr(settings, 'CLAUDE_API_ENDPOINT', None),
                default_model="claude-3-sonnet-20240229",
                max_retries=3,
                timeout=30.0,
                cost_per_token=0.003,
                enabled=True
            )
        
        # 百度文心一言配置
        if hasattr(settings, 'BAIDU_API_KEY') and settings.BAIDU_API_KEY:
            self.adapter_configs[AIProvider.BAIDU_WENXIN] = AdapterConfig(
                provider=AIProvider.BAIDU_WENXIN,
                api_key=settings.BAIDU_API_KEY,
                api_endpoint=getattr(settings, 'BAIDU_API_ENDPOINT', None),
                default_model="wenxin-4.0",
                max_retries=3,
                timeout=30.0,
                cost_per_token=0.001,
                enabled=True
            )
        
        # 阿里通义千问配置
        if hasattr(settings, 'ALIYUN_API_KEY') and settings.ALIYUN_API_KEY:
            self.adapter_configs[AIProvider.ALIYUN_TONGYI] = AdapterConfig(
                provider=AIProvider.ALIYUN_TONGYI,
                api_key=settings.ALIYUN_API_KEY,
                api_endpoint=getattr(settings, 'ALIYUN_API_ENDPOINT', None),
                default_model="qwen-max",
                max_retries=3,
                timeout=30.0,
                cost_per_token=0.0015,
                enabled=True
            )
        
        # Google Gemini配置
        if hasattr(settings, 'GOOGLE_API_KEY') and settings.GOOGLE_API_KEY:
            self.adapter_configs[AIProvider.GOOGLE_GEMINI] = AdapterConfig(
                provider=AIProvider.GOOGLE_GEMINI,
                api_key=settings.GOOGLE_API_KEY,
                api_endpoint=getattr(settings, 'GOOGLE_API_ENDPOINT', None),
                default_model="gemini-pro",
                max_retries=3,
                timeout=30.0,
                cost_per_token=0.0025,
                enabled=True
            )
        
        self.logger.info(f"Loaded configurations for {len(self.adapter_configs)} providers")
    
    async def _initialize_adapters(self):
        """初始化适配器实例"""
        for provider, config in self.adapter_configs.items():
            try:
                if not config.enabled:
                    self.logger.info(f"Skipping disabled provider: {provider.value}")
                    continue
                
                adapter_class = self.adapter_classes.get(provider)
                if not adapter_class:
                    self.logger.warning(f"No adapter class found for provider: {provider.value}")
                    continue
                
                # 创建适配器实例
                adapter = adapter_class(config)
                self.adapters[provider] = adapter
                
                self.logger.info(f"Initialized adapter for provider: {provider.value}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize adapter for {provider.value}: {e}")
                # 不抛出异常，继续初始化其他适配器
    
    async def _initial_health_check(self):
        """执行初始健康检查"""
        health_check_tasks = []
        
        for provider, adapter in self.adapters.items():
            task = asyncio.create_task(
                self._check_adapter_health(provider, adapter),
                name=f"health_check_{provider.value}"
            )
            health_check_tasks.append(task)
        
        if health_check_tasks:
            # 等待所有健康检查完成，但不阻塞启动
            try:
                await asyncio.wait_for(
                    asyncio.gather(*health_check_tasks, return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Initial health check timeout, continuing with startup")
    
    async def _check_adapter_health(self, provider: AIProvider, adapter: BaseAIAdapter):
        """检查单个适配器健康状态"""
        try:
            is_healthy = await adapter.health_check()
            if is_healthy:
                self.logger.info(f"Provider {provider.value} is healthy")
            else:
                self.logger.warning(f"Provider {provider.value} health check failed")
        except Exception as e:
            self.logger.error(f"Health check error for {provider.value}: {e}")
    
    async def get_adapter(self, provider: AIProvider) -> Optional[BaseAIAdapter]:
        """
        获取指定提供商的适配器
        
        Args:
            provider: AI服务提供商
            
        Returns:
            Optional[BaseAIAdapter]: 适配器实例，如果不存在则返回None
        """
        if not self.initialized:
            await self.initialize()
        
        adapter = self.adapters.get(provider)
        
        if not adapter:
            self.logger.warning(f"No adapter available for provider: {provider.value}")
            return None
        
        # 检查适配器是否健康
        if not adapter.is_healthy:
            self.logger.warning(f"Adapter for {provider.value} is not healthy")
            # 可以选择返回None或者尝试重新初始化
        
        return adapter
    
    async def get_available_adapters(self) -> List[BaseAIAdapter]:
        """
        获取所有可用的适配器
        
        Returns:
            List[BaseAIAdapter]: 可用的适配器列表
        """
        if not self.initialized:
            await self.initialize()
        
        available_adapters = []
        
        for provider, adapter in self.adapters.items():
            if adapter and adapter.is_healthy and adapter.config.enabled:
                available_adapters.append(adapter)
        
        return available_adapters
    
    async def get_adapter_stats(self) -> Dict[str, Any]:
        """
        获取所有适配器的统计信息
        
        Returns:
            Dict[str, Any]: 适配器统计信息
        """
        stats = {
            "total_adapters": len(self.adapters),
            "healthy_adapters": 0,
            "enabled_adapters": 0,
            "providers": {}
        }
        
        for provider, adapter in self.adapters.items():
            adapter_stats = adapter.get_stats()
            stats["providers"][provider.value] = adapter_stats
            
            if adapter.is_healthy:
                stats["healthy_adapters"] += 1
            
            if adapter.config.enabled:
                stats["enabled_adapters"] += 1
        
        return stats
    
    async def health_check_all(self) -> Dict[AIProvider, bool]:
        """
        对所有适配器执行健康检查
        
        Returns:
            Dict[AIProvider, bool]: 每个提供商的健康状态
        """
        health_results = {}
        
        health_check_tasks = []
        for provider, adapter in self.adapters.items():
            task = asyncio.create_task(
                adapter.health_check(),
                name=f"health_check_{provider.value}"
            )
            health_check_tasks.append((provider, task))
        
        # 等待所有健康检查完成
        for provider, task in health_check_tasks:
            try:
                is_healthy = await asyncio.wait_for(task, timeout=5.0)
                health_results[provider] = is_healthy
            except asyncio.TimeoutError:
                health_results[provider] = False
                self.logger.warning(f"Health check timeout for {provider.value}")
            except Exception as e:
                health_results[provider] = False
                self.logger.error(f"Health check error for {provider.value}: {e}")
        
        return health_results
    
    async def reload_adapter(self, provider: AIProvider) -> bool:
        """
        重新加载指定提供商的适配器
        
        Args:
            provider: AI服务提供商
            
        Returns:
            bool: 是否成功重新加载
        """
        try:
            # 关闭现有适配器
            if provider in self.adapters:
                await self.adapters[provider].shutdown()
                del self.adapters[provider]
            
            # 重新创建适配器
            config = self.adapter_configs.get(provider)
            if not config:
                self.logger.error(f"No configuration found for provider: {provider.value}")
                return False
            
            adapter_class = self.adapter_classes.get(provider)
            if not adapter_class:
                self.logger.error(f"No adapter class found for provider: {provider.value}")
                return False
            
            # 创建新的适配器实例
            adapter = adapter_class(config)
            self.adapters[provider] = adapter
            
            # 执行健康检查
            is_healthy = await adapter.health_check()
            
            self.logger.info(f"Reloaded adapter for {provider.value}, healthy: {is_healthy}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload adapter for {provider.value}: {e}")
            return False
    
    async def shutdown(self):
        """关闭适配器管理器"""
        self.logger.info("Shutting down adapter manager...")
        
        shutdown_tasks = []
        for provider, adapter in self.adapters.items():
            task = asyncio.create_task(
                adapter.shutdown(),
                name=f"shutdown_{provider.value}"
            )
            shutdown_tasks.append(task)
        
        if shutdown_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*shutdown_tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("Adapter shutdown timeout")
        
        self.adapters.clear()
        self.initialized = False
        
        self.logger.info("Adapter manager shutdown complete")


# 全局适配器管理器实例
_adapter_manager: Optional[AdapterManager] = None


def get_adapter_manager() -> AdapterManager:
    """获取全局适配器管理器实例"""
    global _adapter_manager
    if _adapter_manager is None:
        _adapter_manager = AdapterManager()
    return _adapter_manager


async def initialize_adapter_manager():
    """初始化全局适配器管理器"""
    manager = get_adapter_manager()
    if not manager.initialized:
        await manager.initialize()
    return manager


async def shutdown_adapter_manager():
    """关闭全局适配器管理器"""
    global _adapter_manager
    if _adapter_manager:
        await _adapter_manager.shutdown()
        _adapter_manager = None