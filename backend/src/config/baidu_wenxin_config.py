"""
百度文心一言配置管理

本模块定义百度文心一言的配置参数，包括：
1. API配置
2. 模型配置
3. 优化策略配置
4. 成本控制配置
5. 性能参数配置

配置说明：
- API密钥格式：api_key:secret_key
- 成本单位：元/1000 tokens
- 时间单位：秒
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import os


class WenxinEnvironment(Enum):
    """文心一言环境"""
    PRODUCTION = "production"    # 生产环境
    SANDBOX = "sandbox"         # 沙箱环境
    DEVELOPMENT = "development" # 开发环境


@dataclass
class WenxinAPIConfig:
    """文心一言API配置"""
    api_key: str
    secret_key: str
    environment: WenxinEnvironment = WenxinEnvironment.PRODUCTION
    base_url: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 并发控制
    max_concurrent_requests: int = 20
    rate_limit_per_minute: int = 100
    
    # 成本控制
    daily_cost_limit: Optional[float] = None
    monthly_cost_limit: Optional[float] = None
    cost_alert_threshold: float = 0.8  # 80%时告警
    
    def get_base_url(self) -> str:
        """获取基础URL"""
        if self.base_url:
            return self.base_url
        
        if self.environment == WenxinEnvironment.SANDBOX:
            return "https://aip.baidubce.com/sandbox"
        else:
            return "https://aip.baidubce.com"
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.api_key:
            errors.append("API Key不能为空")
        
        if not self.secret_key:
            errors.append("Secret Key不能为空")
        
        if self.timeout <= 0:
            errors.append("超时时间必须大于0")
        
        if self.max_retries < 0:
            errors.append("重试次数不能为负数")
        
        if self.max_concurrent_requests <= 0:
            errors.append("最大并发请求数必须大于0")
        
        if self.daily_cost_limit and self.daily_cost_limit <= 0:
            errors.append("日成本限制必须大于0")
        
        return errors


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    display_name: str
    endpoint: str
    max_tokens: int
    context_window: int
    cost_per_1k_tokens: float
    avg_response_time: float
    quality_score: float
    
    # 适用场景
    suitable_for: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    
    # 性能参数
    max_concurrent: int = 10
    recommended_temperature: float = 0.7
    recommended_top_p: float = 0.9


@dataclass
class ChineseOptimizationConfig:
    """中文优化配置"""
    enable_context_enhancement: bool = True
    use_chinese_punctuation: bool = True
    optimize_for_chinese_culture: bool = True
    enable_idiom_usage: bool = True
    
    # 文本处理
    auto_correct_typos: bool = False
    enhance_politeness: bool = True
    add_cultural_context: bool = True
    
    # 输出优化
    prefer_formal_language: bool = False
    use_traditional_expressions: bool = False
    optimize_sentence_structure: bool = True


@dataclass
class WenxinConfig:
    """文心一言完整配置"""
    api_config: WenxinAPIConfig
    chinese_optimization: ChineseOptimizationConfig = field(default_factory=ChineseOptimizationConfig)
    
    # 功能开关
    enable_streaming: bool = True
    enable_function_calling: bool = False
    enable_content_filtering: bool = True
    
    # 监控配置
    enable_usage_tracking: bool = True
    enable_performance_monitoring: bool = True
    enable_cost_monitoring: bool = True
    
    # 缓存配置
    enable_response_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_cache_size_mb: int = 100


# 预定义模型配置
WENXIN_MODELS = {
    "ernie-4.0-8k": ModelConfig(
        name="ernie-4.0-8k",
        display_name="ERNIE-4.0-8K",
        endpoint="completions_pro",
        max_tokens=8192,
        context_window=8192,
        cost_per_1k_tokens=0.12,
        avg_response_time=3.5,
        quality_score=0.95,
        suitable_for=["复杂推理", "创意写作", "专业分析", "代码生成"],
        strengths=["推理能力强", "创意丰富", "中文理解优秀", "逻辑严密"],
        limitations=["响应时间较长", "成本较高"],
        max_concurrent=5,
        recommended_temperature=0.7,
        recommended_top_p=0.9
    ),
    
    "ernie-3.5-8k": ModelConfig(
        name="ernie-3.5-8k",
        display_name="ERNIE-3.5-8K",
        endpoint="completions",
        max_tokens=8192,
        context_window=8192,
        cost_per_1k_tokens=0.08,
        avg_response_time=2.8,
        quality_score=0.85,
        suitable_for=["通用对话", "文本生成", "知识问答", "内容总结"],
        strengths=["平衡性好", "通用性强", "成本适中", "响应稳定"],
        limitations=["创意能力一般", "复杂推理有限"],
        max_concurrent=10,
        recommended_temperature=0.7,
        recommended_top_p=0.8
    ),
    
    "ernie-turbo-8k": ModelConfig(
        name="ernie-turbo-8k",
        display_name="ERNIE-Turbo-8K",
        endpoint="eb-instant",
        max_tokens=8192,
        context_window=8192,
        cost_per_1k_tokens=0.04,
        avg_response_time=1.5,
        quality_score=0.75,
        suitable_for=["快速对话", "简单问答", "内容生成", "实时交互"],
        strengths=["响应快速", "成本低廉", "并发能力强"],
        limitations=["质量一般", "复杂任务能力有限"],
        max_concurrent=20,
        recommended_temperature=0.6,
        recommended_top_p=0.8
    ),
    
    "ernie-speed-8k": ModelConfig(
        name="ernie-speed-8k",
        display_name="ERNIE-Speed-8K",
        endpoint="ernie_speed",
        max_tokens=8192,
        context_window=8192,
        cost_per_1k_tokens=0.02,
        avg_response_time=0.8,
        quality_score=0.65,
        suitable_for=["极速响应", "基础对话", "简单任务", "高并发场景"],
        strengths=["极速响应", "成本极低", "高并发支持"],
        limitations=["质量较低", "功能有限"],
        max_concurrent=50,
        recommended_temperature=0.5,
        recommended_top_p=0.7
    )
}


# 任务复杂度与模型映射
COMPLEXITY_MODEL_MAPPING = {
    "simple": ["ernie-speed-8k", "ernie-turbo-8k"],
    "medium": ["ernie-turbo-8k", "ernie-3.5-8k"],
    "complex": ["ernie-3.5-8k", "ernie-4.0-8k"],
    "critical": ["ernie-4.0-8k"]
}


# 场景化配置模板
SCENARIO_CONFIGS = {
    "customer_service": {
        "description": "客服场景配置",
        "recommended_models": ["ernie-turbo-8k", "ernie-3.5-8k"],
        "chinese_optimization": ChineseOptimizationConfig(
            enhance_politeness=True,
            prefer_formal_language=True,
            use_traditional_expressions=False
        ),
        "parameters": {
            "temperature": 0.3,
            "top_p": 0.8,
            "max_tokens": 1000
        }
    },
    
    "creative_writing": {
        "description": "创意写作配置",
        "recommended_models": ["ernie-4.0-8k", "ernie-3.5-8k"],
        "chinese_optimization": ChineseOptimizationConfig(
            enable_idiom_usage=True,
            use_traditional_expressions=True,
            optimize_sentence_structure=True
        ),
        "parameters": {
            "temperature": 0.8,
            "top_p": 0.9,
            "max_tokens": 4000
        }
    },
    
    "technical_analysis": {
        "description": "技术分析配置",
        "recommended_models": ["ernie-4.0-8k", "ernie-3.5-8k"],
        "chinese_optimization": ChineseOptimizationConfig(
            prefer_formal_language=True,
            add_cultural_context=False,
            optimize_sentence_structure=True
        ),
        "parameters": {
            "temperature": 0.2,
            "top_p": 0.7,
            "max_tokens": 3000
        }
    },
    
    "casual_chat": {
        "description": "休闲聊天配置",
        "recommended_models": ["ernie-turbo-8k", "ernie-speed-8k"],
        "chinese_optimization": ChineseOptimizationConfig(
            enhance_politeness=False,
            prefer_formal_language=False,
            use_traditional_expressions=False
        ),
        "parameters": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 800
        }
    }
}


def create_default_config() -> WenxinConfig:
    """创建默认配置"""
    api_config = WenxinAPIConfig(
        api_key=os.getenv("BAIDU_API_KEY", ""),
        secret_key=os.getenv("BAIDU_SECRET_KEY", ""),
        environment=WenxinEnvironment.PRODUCTION,
        timeout=30.0,
        max_retries=3,
        max_concurrent_requests=20,
        rate_limit_per_minute=100
    )
    
    return WenxinConfig(
        api_config=api_config,
        chinese_optimization=ChineseOptimizationConfig(),
        enable_streaming=True,
        enable_content_filtering=True,
        enable_usage_tracking=True,
        enable_performance_monitoring=True,
        enable_cost_monitoring=True,
        enable_response_caching=True,
        cache_ttl_seconds=3600,
        max_cache_size_mb=100
    )


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """获取模型配置"""
    return WENXIN_MODELS.get(model_name)


def get_recommended_models_for_task(task_type: str) -> List[str]:
    """根据任务类型获取推荐模型"""
    scenario_config = SCENARIO_CONFIGS.get(task_type)
    if scenario_config:
        return scenario_config["recommended_models"]
    
    # 默认推荐
    return ["ernie-3.5-8k", "ernie-turbo-8k"]


def get_scenario_config(scenario: str) -> Optional[Dict[str, Any]]:
    """获取场景配置"""
    return SCENARIO_CONFIGS.get(scenario)


def validate_wenxin_config(config: WenxinConfig) -> List[str]:
    """验证文心一言配置"""
    errors = []
    
    # 验证API配置
    api_errors = config.api_config.validate()
    errors.extend(api_errors)
    
    # 验证缓存配置
    if config.cache_ttl_seconds <= 0:
        errors.append("缓存TTL必须大于0")
    
    if config.max_cache_size_mb <= 0:
        errors.append("最大缓存大小必须大于0")
    
    return errors


def load_config_from_env() -> WenxinConfig:
    """从环境变量加载配置"""
    config = create_default_config()
    
    # 从环境变量更新配置
    if os.getenv("BAIDU_API_KEY"):
        config.api_config.api_key = os.getenv("BAIDU_API_KEY")
    
    if os.getenv("BAIDU_SECRET_KEY"):
        config.api_config.secret_key = os.getenv("BAIDU_SECRET_KEY")
    
    if os.getenv("BAIDU_ENVIRONMENT"):
        try:
            config.api_config.environment = WenxinEnvironment(os.getenv("BAIDU_ENVIRONMENT"))
        except ValueError:
            pass
    
    if os.getenv("BAIDU_BASE_URL"):
        config.api_config.base_url = os.getenv("BAIDU_BASE_URL")
    
    if os.getenv("BAIDU_TIMEOUT"):
        try:
            config.api_config.timeout = float(os.getenv("BAIDU_TIMEOUT"))
        except ValueError:
            pass
    
    if os.getenv("BAIDU_MAX_CONCURRENT"):
        try:
            config.api_config.max_concurrent_requests = int(os.getenv("BAIDU_MAX_CONCURRENT"))
        except ValueError:
            pass
    
    if os.getenv("BAIDU_DAILY_COST_LIMIT"):
        try:
            config.api_config.daily_cost_limit = float(os.getenv("BAIDU_DAILY_COST_LIMIT"))
        except ValueError:
            pass
    
    # 功能开关
    if os.getenv("BAIDU_ENABLE_STREAMING"):
        config.enable_streaming = os.getenv("BAIDU_ENABLE_STREAMING").lower() == "true"
    
    if os.getenv("BAIDU_ENABLE_CACHING"):
        config.enable_response_caching = os.getenv("BAIDU_ENABLE_CACHING").lower() == "true"
    
    return config


# 默认配置实例
DEFAULT_WENXIN_CONFIG = create_default_config()