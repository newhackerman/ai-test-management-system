"""
AI使用统计模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Float, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import date

from .base import BaseModel


class AIUsageStats(BaseModel):
    """AI使用统计模型"""
    __tablename__ = "ai_usage_stats"
    
    # 基本信息
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="用户ID")
    date = Column(Date, default=date.today, nullable=False, comment="统计日期")
    
    # AI服务信息
    ai_provider = Column(String(50), nullable=False, comment="AI服务提供商")
    ai_model = Column(String(100), nullable=False, comment="AI模型")
    
    # 使用统计
    request_count = Column(Integer, default=0, comment="请求次数")
    success_count = Column(Integer, default=0, comment="成功次数")
    error_count = Column(Integer, default=0, comment="错误次数")
    
    # Token统计
    input_tokens = Column(Integer, default=0, comment="输入Token数")
    output_tokens = Column(Integer, default=0, comment="输出Token数")
    total_tokens = Column(Integer, default=0, comment="总Token数")
    
    # 成本统计
    total_cost = Column(Float, default=0.0, comment="总成本")
    
    # 性能统计
    avg_response_time = Column(Float, nullable=True, comment="平均响应时间（秒）")
    min_response_time = Column(Float, nullable=True, comment="最小响应时间（秒）")
    max_response_time = Column(Float, nullable=True, comment="最大响应时间（秒）")
    
    # 使用场景统计
    use_case_stats = Column(JSON, nullable=True, comment="使用场景统计")
    
    # 关联关系
    # user = relationship("User", back_populates="ai_usage_stats")
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.request_count == 0:
            return 0.0
        return self.success_count / self.request_count
    
    @property
    def error_rate(self) -> float:
        """计算错误率"""
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count
    
    def __repr__(self):
        return f"<AIUsageStats(id={self.id}, user_id={self.user_id}, date={self.date}, provider='{self.ai_provider}')>"


class AISystemStats(BaseModel):
    """AI系统统计模型"""
    __tablename__ = "ai_system_stats"
    
    # 基本信息
    date = Column(Date, default=date.today, nullable=False, comment="统计日期")
    hour = Column(Integer, nullable=True, comment="小时（0-23，用于小时级统计）")
    
    # 系统级统计
    total_users = Column(Integer, default=0, comment="总用户数")
    active_users = Column(Integer, default=0, comment="活跃用户数")
    total_requests = Column(Integer, default=0, comment="总请求数")
    total_tokens = Column(Integer, default=0, comment="总Token数")
    total_cost = Column(Float, default=0.0, comment="总成本")
    
    # 各提供商统计
    provider_stats = Column(JSON, nullable=True, comment="各提供商统计")
    model_stats = Column(JSON, nullable=True, comment="各模型统计")
    
    # 性能统计
    avg_response_time = Column(Float, nullable=True, comment="平均响应时间")
    system_availability = Column(Float, nullable=True, comment="系统可用性")
    
    # 错误统计
    error_count = Column(Integer, default=0, comment="错误次数")
    error_types = Column(JSON, nullable=True, comment="错误类型统计")
    
    def __repr__(self):
        return f"<AISystemStats(id={self.id}, date={self.date}, total_requests={self.total_requests})>"