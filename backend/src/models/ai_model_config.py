"""
AI模型配置模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.sql import func
from enum import Enum

from .base import BaseModel


class AIModelConfig(BaseModel):
    """AI模型配置模型"""
    __tablename__ = "ai_model_configs"
    
    # 基本信息
    provider = Column(String(50), nullable=False, comment="AI服务提供商")
    model_name = Column(String(100), nullable=False, comment="模型名称")
    display_name = Column(String(200), nullable=False, comment="显示名称")
    description = Column(Text, nullable=True, comment="模型描述")
    version = Column(String(50), nullable=True, comment="模型版本")
    
    # 配置信息
    api_endpoint = Column(String(500), nullable=True, comment="API端点")
    api_key = Column(String(500), nullable=True, comment="API密钥")
    api_version = Column(String(50), nullable=True, comment="API版本")
    headers = Column(JSON, nullable=True, comment="请求头配置")
    
    # 模型参数
    max_tokens = Column(Integer, default=4000, comment="最大Token数")
    temperature = Column(Float, default=0.7, comment="温度参数")
    top_p = Column(Float, default=1.0, comment="Top-p参数")
    frequency_penalty = Column(Float, default=0.0, comment="频率惩罚")
    presence_penalty = Column(Float, default=0.0, comment="存在惩罚")
    stop_sequences = Column(JSON, nullable=True, comment="停止序列")
    
    # 状态和限制
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    is_default = Column(Boolean, default=False, comment="是否为默认模型")
    is_public = Column(Boolean, default=True, comment="是否公开可用")
    priority = Column(Integer, default=0, comment="优先级")
    
    # 配额限制
    daily_quota = Column(Integer, nullable=True, comment="每日配额")
    monthly_quota = Column(Integer, nullable=True, comment="每月配额")
    user_daily_quota = Column(Integer, nullable=True, comment="用户每日配额")
    concurrent_limit = Column(Integer, nullable=True, default=10, comment="并发限制")
    
    # 成本配置
    cost_per_input_token = Column(Float, nullable=True, comment="输入Token成本")
    cost_per_output_token = Column(Float, nullable=True, comment="输出Token成本")
    cost_per_request = Column(Float, nullable=True, comment="每请求成本")
    
    # 能力标签
    capabilities = Column(JSON, nullable=True, comment="模型能力标签")
    supported_languages = Column(JSON, nullable=True, comment="支持的语言")
    use_cases = Column(JSON, nullable=True, comment="适用场景")
    model_features = Column(JSON, nullable=True, comment="模型特性")
    
    # 性能指标
    avg_response_time = Column(Float, nullable=True, comment="平均响应时间（秒）")
    success_rate = Column(Float, nullable=True, comment="成功率")
    last_health_check = Column(DateTime, nullable=True, comment="最后健康检查时间")
    health_status = Column(String(20), nullable=True, default='UNKNOWN', comment="健康状态")
    
    # 使用统计
    total_requests = Column(Integer, default=0, comment="总请求数")
    total_tokens_used = Column(Integer, default=0, comment="总Token使用量")
    total_cost = Column(Float, default=0.0, comment="总成本")
    last_used_at = Column(DateTime, nullable=True, comment="最后使用时间")
    
    def __repr__(self):
        return f"<AIModelConfig(id={self.id}, provider='{self.provider}', model='{self.model_name}')>"