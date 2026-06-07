"""
AI建议相关模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from .base import BaseModel


class SuggestionType(str, Enum):
    """建议类型枚举"""
    QUALITY_IMPROVEMENT = "QUALITY_IMPROVEMENT"           # 质量改进建议
    TEST_IMPROVEMENT = "TEST_IMPROVEMENT"                 # 测试改进建议
    AUTOMATION_IMPROVEMENT = "AUTOMATION_IMPROVEMENT"     # 自动化改进建议
    PROJECT_MANAGEMENT = "PROJECT_MANAGEMENT"             # 项目管理建议
    COVERAGE_IMPROVEMENT = "COVERAGE_IMPROVEMENT"         # 覆盖度改进建议
    URGENT_FIX = "URGENT_FIX"                            # 紧急修复建议
    OPTIMIZATION = "OPTIMIZATION"                         # 优化建议


class SuggestionStatus(str, Enum):
    """建议状态枚举"""
    PENDING = "PENDING"           # 待处理
    ACCEPTED = "ACCEPTED"         # 已接受
    REJECTED = "REJECTED"         # 已拒绝
    IMPLEMENTED = "IMPLEMENTED"   # 已实施
    CANCELLED = "CANCELLED"       # 已取消


class SuggestionPriority(str, Enum):
    """建议优先级枚举"""
    CRITICAL = "CRITICAL"         # 关键
    HIGH = "HIGH"                 # 高
    MEDIUM = "MEDIUM"             # 中
    LOW = "LOW"                   # 低


class SuggestionCategory(str, Enum):
    """建议分类枚举"""
    COMPLETENESS = "COMPLETENESS"                     # 完整性
    CLARITY = "CLARITY"                               # 清晰度
    TESTABILITY = "TESTABILITY"                       # 可测试性
    PROBLEMATIC_REQUIREMENTS = "PROBLEMATIC_REQUIREMENTS"  # 问题需求
    FUNCTIONAL_COVERAGE = "FUNCTIONAL_COVERAGE"       # 功能覆盖度
    NONFUNCTIONAL_COVERAGE = "NONFUNCTIONAL_COVERAGE" # 非功能覆盖度
    PERFORMANCE = "PERFORMANCE"                       # 性能
    SECURITY = "SECURITY"                            # 安全
    MAINTAINABILITY = "MAINTAINABILITY"              # 可维护性


class AISuggestion(BaseModel):
    """AI建议表"""
    __tablename__ = "ai_suggestions"
    
    # 基本信息
    title = Column(String(200), nullable=False, comment="建议标题")
    description = Column(Text, nullable=False, comment="建议描述")
    type = Column(SQLEnum(SuggestionType), nullable=False, comment="建议类型")
    category = Column(SQLEnum(SuggestionCategory), nullable=True, comment="建议分类")
    
    # 状态和优先级
    status = Column(SQLEnum(SuggestionStatus), default=SuggestionStatus.PENDING, nullable=False, comment="建议状态")
    priority = Column(SQLEnum(SuggestionPriority), nullable=False, comment="优先级")
    
    # 关联信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    project_id = Column(Integer, nullable=True, comment="项目ID")  # 假设将来会有项目表
    session_id = Column(Integer, ForeignKey("ai_chat_sessions.id"), nullable=True, comment="会话ID")
    
    # AI生成信息
    ai_provider = Column(String(50), nullable=True, comment="AI服务提供商")
    ai_model = Column(String(100), nullable=True, comment="AI模型名称")
    confidence_score = Column(Float, nullable=True, comment="置信度分数")
    
    # 建议内容
    action_items = Column(JSON, nullable=True, comment="行动项列表")
    expected_benefit = Column(Text, nullable=True, comment="预期收益")
    estimated_effort = Column(String(100), nullable=True, comment="预估工作量")
    implementation_notes = Column(Text, nullable=True, comment="实施说明")
    
    # 用户反馈
    user_rating = Column(Integer, nullable=True, comment="用户评分（1-5）")
    user_feedback = Column(Text, nullable=True, comment="用户反馈")
    
    # 实施信息
    implemented_at = Column(DateTime, nullable=True, comment="实施时间")
    implemented_by = Column(Integer, nullable=True, comment="实施人ID")
    implementation_result = Column(Text, nullable=True, comment="实施结果")
    
    # 元数据
    suggestion_metadata = Column(JSON, nullable=True, comment="建议元数据")
    tags = Column(JSON, nullable=True, comment="标签")
    
    # 关联关系
    # user = relationship("User", back_populates="ai_suggestions")
    session = relationship("AIChatSession", back_populates="suggestions")
    
    def __repr__(self):
        return f"<AISuggestion(id={self.id}, title='{self.title}', type={self.type}, priority={self.priority})>"


class AIRequirementsAnalysis(BaseModel):
    """需求分析表"""
    __tablename__ = "ai_requirements_analysis"
    
    # 基本信息
    analysis_name = Column(String(200), nullable=False, comment="分析名称")
    description = Column(Text, nullable=True, comment="分析描述")
    
    # 关联信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    project_id = Column(Integer, nullable=True, comment="项目ID")
    session_id = Column(Integer, ForeignKey("ai_chat_sessions.id"), nullable=True, comment="会话ID")
    
    # AI分析信息
    ai_provider = Column(String(50), nullable=True, comment="AI服务提供商")
    ai_model = Column(String(100), nullable=True, comment="AI模型名称")
    analysis_prompt = Column(Text, nullable=True, comment="分析提示词")
    
    # 分析结果
    completeness_score = Column(Float, nullable=True, comment="完整性得分")
    clarity_score = Column(Float, nullable=True, comment="清晰度得分")
    consistency_score = Column(Float, nullable=True, comment="一致性得分")
    testability_score = Column(Float, nullable=True, comment="可测试性得分")
    overall_score = Column(Float, nullable=True, comment="总体得分")
    
    # 分析详情
    total_requirements = Column(Integer, default=0, comment="需求总数")
    analyzed_requirements = Column(Integer, default=0, comment="已分析需求数")
    problematic_requirements_count = Column(Integer, default=0, comment="问题需求数")
    
    # 分析状态
    analysis_status = Column(SQLEnum('PENDING', 'ANALYZING', 'COMPLETED', 'FAILED', name='analysisstatus'), 
                           default='PENDING', nullable=False, comment="分析状态")
    progress = Column(Float, default=0.0, comment="分析进度（0-1）")
    
    # 分析结果详情
    analysis_results = Column(JSON, nullable=True, comment="详细分析结果")
    identified_issues = Column(JSON, nullable=True, comment="识别的问题")
    improvement_areas = Column(JSON, nullable=True, comment="改进领域")
    
    # 时间信息
    started_at = Column(DateTime, nullable=True, comment="开始分析时间")
    completed_at = Column(DateTime, nullable=True, comment="完成分析时间")
    
    # 元数据
    analysis_metadata = Column(JSON, nullable=True, comment="分析元数据")
    
    # 关联关系
    # user = relationship("User", back_populates="requirements_analyses")
    session = relationship("AIChatSession", back_populates="requirements_analyses")
    requirements_suggestions = relationship("AIRequirementsSuggestion", back_populates="analysis", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AIRequirementsAnalysis(id={self.id}, name='{self.analysis_name}', status={self.analysis_status})>"


class AIRequirementsSuggestion(BaseModel):
    """需求建议表"""
    __tablename__ = "ai_requirements_suggestions"
    
    # 基本信息
    title = Column(String(200), nullable=False, comment="建议标题")
    description = Column(Text, nullable=False, comment="建议描述")
    suggestion_type = Column(SQLEnum(SuggestionType), nullable=False, comment="建议类型")
    category = Column(SQLEnum(SuggestionCategory), nullable=True, comment="建议分类")
    
    # 关联信息
    analysis_id = Column(Integer, ForeignKey("ai_requirements_analysis.id"), nullable=False, comment="分析ID")
    requirement_id = Column(Integer, nullable=True, comment="需求ID")  # 假设将来会有需求表
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 建议属性
    priority = Column(SQLEnum(SuggestionPriority), nullable=False, comment="优先级")
    status = Column(SQLEnum(SuggestionStatus), default=SuggestionStatus.PENDING, nullable=False, comment="建议状态")
    
    # 建议内容
    action_items = Column(JSON, nullable=True, comment="行动项列表")
    expected_benefit = Column(Text, nullable=True, comment="预期收益")
    estimated_effort = Column(String(100), nullable=True, comment="预估工作量")
    
    # 问题相关
    identified_issues = Column(JSON, nullable=True, comment="识别的问题")
    severity = Column(SQLEnum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='issueseverity'), 
                     nullable=True, comment="问题严重程度")
    
    # AI生成信息
    ai_provider = Column(String(50), nullable=True, comment="AI服务提供商")
    ai_model = Column(String(100), nullable=True, comment="AI模型名称")
    confidence_score = Column(Float, nullable=True, comment="置信度分数")
    generation_prompt = Column(Text, nullable=True, comment="生成提示词")
    
    # 用户交互
    user_rating = Column(Integer, nullable=True, comment="用户评分（1-5）")
    user_feedback = Column(Text, nullable=True, comment="用户反馈")
    is_accepted = Column(Boolean, default=False, comment="是否被接受")
    
    # 实施信息
    implemented_at = Column(DateTime, nullable=True, comment="实施时间")
    implemented_by = Column(Integer, nullable=True, comment="实施人ID")
    implementation_notes = Column(Text, nullable=True, comment="实施说明")
    
    # 元数据
    suggestion_metadata = Column(JSON, nullable=True, comment="建议元数据")
    tags = Column(JSON, nullable=True, comment="标签")
    
    # 关联关系
    analysis = relationship("AIRequirementsAnalysis", back_populates="requirements_suggestions")
    # user = relationship("User", back_populates="requirements_suggestions")
    
    def __repr__(self):
        return f"<AIRequirementsSuggestion(id={self.id}, title='{self.title}', type={self.suggestion_type})>"