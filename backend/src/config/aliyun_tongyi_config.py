"""
阿里通义千问配置模块

本模块定义了阿里通义千问服务的配置类和相关枚举，
包括API配置、模型配置、中文优化配置等。
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class TongyiModel(Enum):
    """通义千问模型枚举"""
    QWEN_MAX = "qwen-max"
    QWEN_MAX_1201 = "qwen-max-1201"
    QWEN_PLUS = "qwen-plus"
    QWEN_TURBO = "qwen-turbo"
    QWEN_LONG = "qwen-long"
    QWEN_VL_PLUS = "qwen-vl-plus"
    QWEN_VL_MAX = "qwen-vl-max"


class TongyiEnvironment(Enum):
    """通义千问环境枚举"""
    PRODUCTION = "production"
    SANDBOX = "sandbox"
    DEVELOPMENT = "development"


class TaskComplexity(Enum):
    """任务复杂度枚举"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class TongyiAPIConfig:
    """通义千问API配置"""
    api_key: str
    api_endpoint: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    api_version: str = "v1"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_concurrent_requests: int = 20
    
    def validate(self) -> bool:
        """验证配置有效性"""
        return bool(self.api_key and self.api_endpoint)


@dataclass
class ChineseOptimizationConfig:
    """中文内容优化配置"""
    enable_context_enhancement: bool = True
    use_chinese_punctuation: bool = True
    optimize_for_chinese_culture: bool = True
    enable_idiom_usage: bool = True
    enhance_politeness: bool = True
    prefer_formal_language: bool = False
    
    def to_dict(self) -> Dict[str, bool]:
        """转换为字典"""
        return {
            "enable_context_enhancement": self.enable_context_enhancement,
            "use_chinese_punctuation": self.use_chinese_punctuation,
            "optimize_for_chinese_culture": self.optimize_for_chinese_culture,
            "enable_idiom_usage": self.enable_idiom_usage,
            "enhance_politeness": self.enhance_politeness,
            "prefer_formal_language": self.prefer_formal_language
        }


@dataclass
class TongyiConfig:
    """通义千问完整配置"""
    api_config: TongyiAPIConfig
    chinese_optimization: ChineseOptimizationConfig = field(default_factory=ChineseOptimizationConfig)
    environment: TongyiEnvironment = TongyiEnvironment.PRODUCTION
    
    # 成本控制
    daily_cost_limit: Optional[float] = None
    monthly_cost_limit: Optional[float] = None
    cost_per_1k_tokens: float = 0.02  # 默认成本
    
    # 功能开关
    enable_streaming: bool = True
    enable_caching: bool = True
    enable_monitoring: bool = True
    
    # 模型配置
    default_model: TongyiModel = TongyiModel.QWEN_TURBO
    model_configs: Dict[TongyiModel, Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.model_configs:
            self.model_configs = self._get_default_model_configs()
    
    def _get_default_model_configs(self) -> Dict[TongyiModel, Dict[str, Any]]:
        """获取默认模型配置"""
        return {
            TongyiModel.QWEN_MAX: {
                "cost_per_1k_tokens": 0.12,
                "max_tokens": 8192,
                "context_window": 32768,
                "avg_response_time": 3.5,
                "quality_score": 0.95,
                "max_concurrent": 10,
                "strengths": ["复杂推理", "创意写作", "专业分析", "多语言支持"],
                "use_cases": ["复杂分析", "创意写作", "专业咨询", "学术研究"]
            },
            TongyiModel.QWEN_MAX_1201: {
                "cost_per_1k_tokens": 0.12,
                "max_tokens": 8192,
                "context_window": 32768,
                "avg_response_time": 3.2,
                "quality_score": 0.96,
                "max_concurrent": 10,
                "strengths": ["最新优化", "更好理解", "准确性提升", "多模态支持"],
                "use_cases": ["最新任务", "高质量对话", "专业分析", "多模态处理"]
            },
            TongyiModel.QWEN_PLUS: {
                "cost_per_1k_tokens": 0.08,
                "max_tokens": 8192,
                "context_window": 32768,
                "avg_response_time": 2.8,
                "quality_score": 0.88,
                "max_concurrent": 15,
                "strengths": ["平衡性能", "成本效益", "通用能力", "稳定性好"],
                "use_cases": ["通用对话", "文档处理", "代码生成", "问答系统"]
            },
            TongyiModel.QWEN_TURBO: {
                "cost_per_1k_tokens": 0.02,
                "max_tokens": 8192,
                "context_window": 8192,
                "avg_response_time": 1.5,
                "quality_score": 0.82,
                "max_concurrent": 25,
                "strengths": ["快速响应", "低成本", "高并发", "实时对话"],
                "use_cases": ["实时聊天", "快速问答", "批量处理", "高频调用"]
            },
            TongyiModel.QWEN_LONG: {
                "cost_per_1k_tokens": 0.05,
                "max_tokens": 32768,
                "context_window": 1000000,
                "avg_response_time": 8.0,
                "quality_score": 0.90,
                "max_concurrent": 5,
                "strengths": ["超长文本", "文档分析", "深度理解", "上下文保持"],
                "use_cases": ["长文档分析", "书籍总结", "深度研究", "大规模文本处理"]
            },
            TongyiModel.QWEN_VL_PLUS: {
                "cost_per_1k_tokens": 0.15,
                "max_tokens": 8192,
                "context_window": 8192,
                "avg_response_time": 4.0,
                "quality_score": 0.92,
                "max_concurrent": 8,
                "strengths": ["视觉理解", "图文结合", "多模态", "场景识别"],
                "use_cases": ["图像分析", "视觉问答", "图文生成", "多媒体处理"]
            },
            TongyiModel.QWEN_VL_MAX: {
                "cost_per_1k_tokens": 0.20,
                "max_tokens": 8192,
                "context_window": 8192,
                "avg_response_time": 5.0,
                "quality_score": 0.95,
                "max_concurrent": 5,
                "strengths": ["顶级视觉", "精准识别", "复杂场景", "专业分析"],
                "use_cases": ["专业图像分析", "医学影像", "工业检测", "艺术创作"]
            }
        }
    
    def get_model_info(self, model: TongyiModel) -> Dict[str, Any]:
        """获取模型信息"""
        return self.model_configs.get(model, {})
    
    def get_recommended_model(self, task_complexity: TaskComplexity, 
                            cost_priority: bool = False) -> TongyiModel:
        """根据任务复杂度推荐模型"""
        if cost_priority:
            # 优先考虑成本
            if task_complexity == TaskComplexity.SIMPLE:
                return TongyiModel.QWEN_TURBO
            elif task_complexity == TaskComplexity.MEDIUM:
                return TongyiModel.QWEN_PLUS
            else:
                return TongyiModel.QWEN_MAX
        else:
            # 优先考虑质量
            if task_complexity == TaskComplexity.SIMPLE:
                return TongyiModel.QWEN_PLUS
            elif task_complexity == TaskComplexity.MEDIUM:
                return TongyiModel.QWEN_MAX
            elif task_complexity == TaskComplexity.COMPLEX:
                return TongyiModel.QWEN_MAX_1201
            else:  # VERY_COMPLEX
                return TongyiModel.QWEN_LONG


class ModelRecommendation(BaseModel):
    """模型推荐结果"""
    recommended_model: TongyiModel
    confidence: float = Field(..., ge=0.0, le=1.0, description="推荐置信度")
    reasoning: str = Field(..., description="推荐理由")
    estimated_cost: float = Field(..., ge=0.0, description="预估成本(元)")
    estimated_time: float = Field(..., ge=0.0, description="预估响应时间(秒)")
    alternative_models: List[TongyiModel] = Field(default_factory=list, description="备选模型")


# 默认配置实例
DEFAULT_TONGYI_CONFIG = TongyiConfig(
    api_config=TongyiAPIConfig(
        api_key="",  # 需要从环境变量获取
        api_endpoint="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    ),
    chinese_optimization=ChineseOptimizationConfig(),
    environment=TongyiEnvironment.PRODUCTION
)


def create_tongyi_config_from_env() -> TongyiConfig:
    """从环境变量创建配置"""
    import os
    
    api_key = os.getenv("ALIYUN_API_KEY", "")
    if not api_key:
        raise ValueError("ALIYUN_API_KEY environment variable is required")
    
    api_config = TongyiAPIConfig(
        api_key=api_key,
        api_endpoint=os.getenv("ALIYUN_API_ENDPOINT", 
                              "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"),
        timeout=float(os.getenv("ALIYUN_TIMEOUT", "30.0")),
        max_retries=int(os.getenv("ALIYUN_MAX_RETRIES", "3")),
        max_concurrent_requests=int(os.getenv("ALIYUN_MAX_CONCURRENT", "20"))
    )
    
    chinese_optimization = ChineseOptimizationConfig(
        enable_context_enhancement=os.getenv("ALIYUN_ENABLE_CONTEXT_ENHANCEMENT", "true").lower() == "true",
        use_chinese_punctuation=os.getenv("ALIYUN_USE_CHINESE_PUNCTUATION", "true").lower() == "true",
        optimize_for_chinese_culture=os.getenv("ALIYUN_OPTIMIZE_FOR_CHINESE_CULTURE", "true").lower() == "true",
        enable_idiom_usage=os.getenv("ALIYUN_ENABLE_IDIOM_USAGE", "true").lower() == "true",
        enhance_politeness=os.getenv("ALIYUN_ENHANCE_POLITENESS", "true").lower() == "true",
        prefer_formal_language=os.getenv("ALIYUN_PREFER_FORMAL_LANGUAGE", "false").lower() == "true"
    )
    
    return TongyiConfig(
        api_config=api_config,
        chinese_optimization=chinese_optimization,
        environment=TongyiEnvironment(os.getenv("ALIYUN_ENVIRONMENT", "production")),
        daily_cost_limit=float(os.getenv("ALIYUN_DAILY_COST_LIMIT")) if os.getenv("ALIYUN_DAILY_COST_LIMIT") else None,
        monthly_cost_limit=float(os.getenv("ALIYUN_MONTHLY_COST_LIMIT")) if os.getenv("ALIYUN_MONTHLY_COST_LIMIT") else None,
        enable_streaming=os.getenv("ALIYUN_ENABLE_STREAMING", "true").lower() == "true",
        enable_caching=os.getenv("ALIYUN_ENABLE_CACHING", "true").lower() == "true",
        enable_monitoring=os.getenv("ALIYUN_ENABLE_MONITORING", "true").lower() == "true"
    )