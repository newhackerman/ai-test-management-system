"""
AI模型配置相关的Pydantic模式
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class AIProviderEnum(str, Enum):
    """AI服务提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BAIDU_WENXIN = "baidu_wenxin"
    ALIYUN_TONGYI = "aliyun_tongyi"
    GOOGLE_GEMINI = "google_gemini"
    ZHIPU_CHATGLM = "zhipu_chatglm"
    XUNFEI_XINGHUO = "xunfei_xinghuo"
    CUSTOM = "custom"


class HealthStatusEnum(str, Enum):
    """健康状态枚举"""
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


class AIModelConfigBase(BaseModel):
    """AI模型配置基础模式"""
    provider: AIProviderEnum = Field(..., description="AI服务提供商")
    model_name: str = Field(..., min_length=1, max_length=100, description="模型名称")
    display_name: str = Field(..., min_length=1, max_length=200, description="显示名称")
    description: Optional[str] = Field(None, max_length=1000, description="模型描述")
    version: Optional[str] = Field(None, max_length=50, description="模型版本")
    
    # 配置信息
    api_endpoint: Optional[str] = Field(None, max_length=500, description="API端点")
    api_key: Optional[str] = Field(None, max_length=500, description="API密钥")
    api_version: Optional[str] = Field(None, max_length=50, description="API版本")
    headers: Optional[Dict[str, Any]] = Field(None, description="请求头配置")
    
    # 模型参数
    max_tokens: int = Field(4000, ge=1, le=1000000, description="最大Token数")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Top-p参数")
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="存在惩罚")
    stop_sequences: Optional[List[str]] = Field(None, description="停止序列")
    
    # 状态和限制
    is_enabled: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认模型")
    is_public: bool = Field(True, description="是否公开可用")
    priority: int = Field(0, ge=0, le=100, description="优先级")
    
    # 配额限制
    daily_quota: Optional[int] = Field(None, ge=0, description="每日配额")
    monthly_quota: Optional[int] = Field(None, ge=0, description="每月配额")
    user_daily_quota: Optional[int] = Field(None, ge=0, description="用户每日配额")
    concurrent_limit: int = Field(10, ge=1, le=1000, description="并发限制")
    
    # 成本配置
    cost_per_input_token: Optional[float] = Field(None, ge=0.0, description="输入Token成本")
    cost_per_output_token: Optional[float] = Field(None, ge=0.0, description="输出Token成本")
    cost_per_request: Optional[float] = Field(None, ge=0.0, description="每请求成本")
    
    # 能力标签
    capabilities: Optional[List[str]] = Field(None, description="模型能力标签")
    supported_languages: Optional[List[str]] = Field(None, description="支持的语言")
    use_cases: Optional[List[str]] = Field(None, description="适用场景")
    model_features: Optional[Dict[str, Any]] = Field(None, description="模型特性")


class AIModelConfigCreate(AIModelConfigBase):
    """创建AI模型配置"""
    pass


class AIModelConfigUpdate(BaseModel):
    """更新AI模型配置"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=200, description="显示名称")
    description: Optional[str] = Field(None, max_length=1000, description="模型描述")
    version: Optional[str] = Field(None, max_length=50, description="模型版本")
    
    # 配置信息
    api_endpoint: Optional[str] = Field(None, max_length=500, description="API端点")
    api_key: Optional[str] = Field(None, max_length=500, description="API密钥")
    api_version: Optional[str] = Field(None, max_length=50, description="API版本")
    headers: Optional[Dict[str, Any]] = Field(None, description="请求头配置")
    
    # 模型参数
    max_tokens: Optional[int] = Field(None, ge=1, le=1000000, description="最大Token数")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="温度参数")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Top-p参数")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="存在惩罚")
    stop_sequences: Optional[List[str]] = Field(None, description="停止序列")
    
    # 状态和限制
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    is_default: Optional[bool] = Field(None, description="是否为默认模型")
    is_public: Optional[bool] = Field(None, description="是否公开可用")
    priority: Optional[int] = Field(None, ge=0, le=100, description="优先级")
    
    # 配额限制
    daily_quota: Optional[int] = Field(None, ge=0, description="每日配额")
    monthly_quota: Optional[int] = Field(None, ge=0, description="每月配额")
    user_daily_quota: Optional[int] = Field(None, ge=0, description="用户每日配额")
    concurrent_limit: Optional[int] = Field(None, ge=1, le=1000, description="并发限制")
    
    # 成本配置
    cost_per_input_token: Optional[float] = Field(None, ge=0.0, description="输入Token成本")
    cost_per_output_token: Optional[float] = Field(None, ge=0.0, description="输出Token成本")
    cost_per_request: Optional[float] = Field(None, ge=0.0, description="每请求成本")
    
    # 能力标签
    capabilities: Optional[List[str]] = Field(None, description="模型能力标签")
    supported_languages: Optional[List[str]] = Field(None, description="支持的语言")
    use_cases: Optional[List[str]] = Field(None, description="适用场景")
    model_features: Optional[Dict[str, Any]] = Field(None, description="模型特性")


class AIModelConfigResponse(AIModelConfigBase):
    """AI模型配置响应"""
    id: int
    # 覆盖父类的 provider 字段，使用 str 类型以容忍数据库中不在枚举内的值
    provider: str = Field(..., description="AI服务提供商")
    
    # 性能指标
    avg_response_time: Optional[float] = Field(None, description="平均响应时间（秒）")
    success_rate: Optional[float] = Field(None, description="成功率")
    last_health_check: Optional[datetime] = Field(None, description="最后健康检查时间")
    health_status: Optional[HealthStatusEnum] = Field(None, description="健康状态")
    
    # 使用统计
    total_requests: int = Field(0, description="总请求数")
    total_tokens_used: int = Field(0, description="总Token使用量")
    total_cost: float = Field(0.0, description="总成本")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AIModelConfigList(BaseModel):
    """AI模型配置列表"""
    items: List[AIModelConfigResponse]
    total: int
    skip: int
    limit: int


class AIProviderStats(BaseModel):
    """AI服务提供商统计"""
    provider: str = Field(..., description="服务提供商")
    total_models: int = Field(0, description="总模型数")
    enabled_models: int = Field(0, description="启用模型数")
    default_models: int = Field(0, description="默认模型数")
    total_requests: int = Field(0, description="总请求数")
    total_tokens: int = Field(0, description="总Token数")
    total_cost: float = Field(0.0, description="总成本")
    avg_response_time: float = Field(0.0, description="平均响应时间")


class AIModelHealthCheck(BaseModel):
    """AI模型健康检查结果"""
    status: HealthStatusEnum = Field(..., description="健康状态")
    response_time: Optional[float] = Field(None, description="响应时间（秒）")
    error: Optional[str] = Field(None, description="错误信息")
    checked_at: datetime = Field(default_factory=datetime.utcnow, description="检查时间")


class AIModelTestRequest(BaseModel):
    """AI模型测试请求"""
    test_message: str = Field(..., min_length=1, max_length=1000, description="测试消息")
    use_custom_params: bool = Field(False, description="是否使用自定义参数")
    custom_temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="自定义温度")
    custom_max_tokens: Optional[int] = Field(None, ge=1, le=10000, description="自定义最大Token数")


class AIModelTestResponse(BaseModel):
    """AI模型测试响应"""
    success: bool = Field(..., description="测试是否成功")
    response_text: Optional[str] = Field(None, description="AI响应文本")
    response_time: float = Field(..., description="响应时间（秒）")
    tokens_used: Optional[int] = Field(None, description="使用的Token数")
    cost: Optional[float] = Field(None, description="成本")
    error: Optional[str] = Field(None, description="错误信息")
    tested_at: datetime = Field(default_factory=datetime.utcnow, description="测试时间")


class BatchHealthCheckResponse(BaseModel):
    """批量健康检查响应"""
    total: int = Field(..., description="总数")
    healthy: int = Field(..., description="健康数量")
    unhealthy: int = Field(..., description="不健康数量")
    unknown: int = Field(..., description="未知状态数量")
    details: List[Dict[str, Any]] = Field(..., description="详细结果")
    checked_at: datetime = Field(default_factory=datetime.utcnow, description="检查时间")