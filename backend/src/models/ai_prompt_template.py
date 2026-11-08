"""
AI提示词模板模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from .base import BaseModel


class TemplateCategory(str, Enum):
    """模板分类枚举"""
    GENERAL = "GENERAL"
    CODE_GENERATION = "CODE_GENERATION"
    TEST_CASE = "TEST_CASE"
    DOCUMENT_WRITING = "DOCUMENT_WRITING"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    CREATIVE_WRITING = "CREATIVE_WRITING"
    LEARNING_EDUCATION = "LEARNING_EDUCATION"
    PROJECT_MANAGEMENT = "PROJECT_MANAGEMENT"


class TemplateVisibility(str, Enum):
    """模板可见性枚举"""
    PRIVATE = "PRIVATE"
    TEAM = "TEAM"
    PUBLIC = "PUBLIC"


class AIPromptTemplate(BaseModel):
    """AI提示词模板模型"""
    __tablename__ = "ai_prompt_templates"
    
    # 基本信息
    name = Column(String(200), nullable=False, comment="模板名称")
    title = Column(String(300), nullable=False, comment="模板标题")
    description = Column(Text, nullable=True, comment="模板描述")
    category = Column(String(100), nullable=True, comment="模板分类")
    subcategory = Column(String(100), nullable=True, comment="子分类")
    
    # 模板内容
    content = Column(Text, nullable=False, comment="模板内容")
    variables = Column(JSON, nullable=True, comment="模板变量定义")
    default_values = Column(JSON, nullable=True, comment="默认值")
    validation_rules = Column(JSON, nullable=True, comment="验证规则")
    example_context = Column(JSON, nullable=True, comment="示例上下文")
    
    # 适用性
    supported_providers = Column(JSON, nullable=True, comment="支持的AI提供商")
    supported_models = Column(JSON, nullable=True, comment="支持的模型")
    use_cases = Column(JSON, nullable=True, comment="使用场景")
    tags = Column(JSON, nullable=True, comment="标签")
    
    # 权限和可见性
    visibility = Column(String(20), nullable=False, default='PRIVATE', comment="可见性")
    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="所有者ID")
    team_id = Column(BigInteger, nullable=True, comment="团队ID")
    is_featured = Column(Boolean, nullable=False, default=False, comment="是否精选")
    is_verified = Column(Boolean, nullable=False, default=False, comment="是否已验证")
    
    # 版本控制
    version = Column(String(20), nullable=False, default='1.0.0', comment="版本号")
    parent_template_id = Column(BigInteger, ForeignKey("ai_prompt_templates.id"), nullable=True, comment="父模板ID")
    is_latest_version = Column(Boolean, nullable=False, default=True, comment="是否最新版本")
    
    # 使用统计
    usage_count = Column(Integer, nullable=False, default=0, comment="使用次数")
    rating_avg = Column(Float, nullable=True, comment="平均评分")
    rating_count = Column(Integer, nullable=False, default=0, comment="评分次数")
    last_used_at = Column(DateTime, nullable=True, comment="最后使用时间")
    
    # 关联关系
    # owner = relationship("User", back_populates="prompt_templates")
    parent_template = relationship("AIPromptTemplate", remote_side="AIPromptTemplate.id", backref="child_templates")
    usage_records = relationship("AIPromptTemplateUsage", back_populates="template", cascade="all, delete-orphan")
    files = relationship("AIFileStorage", back_populates="template", cascade="all, delete-orphan")
    
    @property
    def average_rating(self) -> float:
        """计算平均评分"""
        return self.rating_avg or 0.0
    
    def __repr__(self):
        return f"<AIPromptTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"


class AIPromptTemplateUsage(BaseModel):
    """AI提示词模板使用记录模型"""
    __tablename__ = "ai_prompt_template_usage"
    
    # 基本信息
    template_id = Column(BigInteger, ForeignKey("ai_prompt_templates.id"), nullable=False, comment="模板ID")
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 使用信息
    ai_provider = Column(String(50), nullable=True, comment="使用的AI服务提供商")
    ai_model = Column(String(100), nullable=True, comment="使用的AI模型")
    use_case = Column(String(200), nullable=True, comment="使用场景")
    
    # 使用结果
    success = Column(Boolean, default=True, comment="是否成功")
    tokens_used = Column(Integer, nullable=True, comment="使用的Token数")
    response_time = Column(Float, nullable=True, comment="响应时间（秒）")
    
    # 用户反馈
    user_rating = Column(Integer, nullable=True, comment="用户评分（1-5）")
    user_feedback = Column(Text, nullable=True, comment="用户反馈")
    
    # 使用的变量值
    variable_values = Column(JSON, nullable=True, comment="使用的变量值")
    
    # 关联关系
    template = relationship("AIPromptTemplate", back_populates="usage_records")
    # user = relationship("User", back_populates="template_usage_records")
    
    def __repr__(self):
        return f"<AIPromptTemplateUsage(id={self.id}, template_id={self.template_id}, user_id={self.user_id})>"