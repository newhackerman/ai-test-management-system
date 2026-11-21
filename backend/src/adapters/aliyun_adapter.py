"""
阿里通义千问适配器实现

本模块实现了阿里通义千问API的适配器，提供统一的AI服务接口。
支持多种模型、流式响应、中文优化等功能。

注意：这是为了保持向后兼容性的别名，实际实现在 tongyi_adapter.py 中。
"""

import logging
from typing import AsyncGenerator, List

from ..config.aliyun_tongyi_config import TongyiConfig, create_tongyi_config_from_env
from .base import (
    AdapterConfig,
    AIProvider,
    AIRequest,
    AIResponse,
    BaseAIAdapter,
    StreamChunk,
    TokenUsage,
)
from .tongyi_adapter import TongyiAdapter

logger = logging.getLogger(__name__)


class AliyunAdapter(TongyiAdapter):
    """阿里通义千问API适配器 (向后兼容别名)"""

    def __init__(self, config: AdapterConfig):
        # 创建默认的通义千问配置
        try:
            tongyi_config = create_tongyi_config_from_env()
            # 使用传入的配置覆盖
            tongyi_config.api_config.api_key = config.api_key
            if config.api_endpoint:
                tongyi_config.api_config.api_endpoint = config.api_endpoint
        except Exception:
            # 如果无法从环境变量创建配置，使用默认配置
            from ..config.aliyun_tongyi_config import (
                ChineseOptimizationConfig,
                TongyiAPIConfig,
            )

            tongyi_config = TongyiConfig(
                api_config=TongyiAPIConfig(
                    api_key=config.api_key,
                    api_endpoint=config.api_endpoint
                    or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                ),
                chinese_optimization=ChineseOptimizationConfig(),
            )

        super().__init__(config, tongyi_config)
        self.logger.info("Aliyun Tongyi adapter initialized (compatibility wrapper)")
