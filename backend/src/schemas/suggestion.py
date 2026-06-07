"""
建议相关的Pydantic模式定义
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from ..models.ai_suggestion import SuggestionType, SuggestionStatus, SuggestionPriority, SuggestionCategory


class ProjectContextSchema(BaseModel):
    """项目上下文模式"""
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_type: Optional[str] = Field(default="web_application", description="项目类型")
    team_size: Optional[int] = None
    timeline: Optional[Dict[str, Any]] = None
    requirements: Optional[List[Dict[str, Any]]] = None
    test_data: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None


class RequirementsQualityAnalysisSchema(BaseModel):
    """需求质量分析结果模式"""
    completeness_score: float = Field(ge=0.0, le=1.0, description="完整性得分")
    clarity_score: float = Field(ge=0.0, le=1.0, description="清晰度得分")
    consistency_score: float = Field(ge=0.0, le=1.0, description="一致性得分")
    testability_score: float = Field(ge=0.0, le=1.0, description="可测试性得分")
    overall_score: float = Field(ge=0.0, le=1.0, description="总体得分")
    problematic_requirements: List[Dict[str, Any]] = Field(default_factory=list, description="问题需求列表")


class TestSuggestionSchema(BaseModel):
    """测试建议模式"""
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    test_steps: List[str] = Field(default_factory=list, description="测试步骤")
    expected_result: str = Field(..., description="预期结果")
    priority: str = Field(..., description="优先级")
    rationale: str = Field(..., description="建议理由")


class OptimizationSuggestionSchema(BaseModel):
    """优化建议模式"""
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    optimization_type: str = Field(..., description="优化类型")
    expected_improvement: str = Field(..., description="预期改进")
    implementation_steps: List[str] = Field(default_factory=list, description="实施步骤")
    priority: str = Field(..., description="优先级")


class SuggestionCreateSchema(BaseModel):
    """创建建议的请求模式"""
    title: str = Field(..., min_length=1, max_length=200, description="建议标题")
    description: str = Field(..., min_length=1, description="建议描述")
    type: SuggestionType = Field(..., description="建议类型")
    category: Optional[SuggestionCategory] = Field(None, description="建议分类")
    priority: SuggestionPriority = Field(..., description="优先级")
    action_items: Optional[List[str]] = Field(default_factory=list, description="行动项列表")
    expected_benefit: Optional[str] = Field(None, description="预期收益")
    estimated_effort: Optional[str] = Field(None, description="预估工作量")
    project_id: Optional[int] = Field(None, description="项目ID")
    session_id: Optional[int] = Field(None, description="会话ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class SuggestionUpdateSchema(BaseModel):
    """更新建议的请求模式"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="建议标题")
    description: Optional[str] = Field(None, min_length=1, description="建议描述")
    status: Optional[SuggestionStatus] = Field(None, description="建议状态")
    priority: Optional[SuggestionPriority] = Field(None, description="优先级")
    user_rating: Optional[int] = Field(None, ge=1, le=5, description="用户评分")
    user_feedback: Optional[str] = Field(None, description="用户反馈")
    implementation_notes: Optional[str] = Field(None, description="实施说明")


class SuggestionResponseSchema(BaseModel):
    """建议响应模式"""
    id: int = Field(..., description="建议ID")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    type: SuggestionType = Field(..., description="建议类型")
    category: Optional[SuggestionCategory] = Field(None, description="建议分类")
    status: SuggestionStatus = Field(..., description="建议状态")
    priority: SuggestionPriority = Field(..., description="优先级")
    
    user_id: int = Field(..., description="用户ID")
    project_id: Optional[int] = Field(None, description="项目ID")
    session_id: Optional[int] = Field(None, description="会话ID")
    
    action_items: Optional[List[str]] = Field(None, description="行动项列表")
    expected_benefit: Optional[str] = Field(None, description="预期收益")
    estimated_effort: Optional[str] = Field(None, description="预估工作量")
    implementation_notes: Optional[str] = Field(None, description="实施说明")
    
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型名称")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度分数")
    
    user_rating: Optional[int] = Field(None, ge=1, le=5, description="用户评分")
    user_feedback: Optional[str] = Field(None, description="用户反馈")
    
    implemented_at: Optional[datetime] = Field(None, description="实施时间")
    implemented_by: Optional[int] = Field(None, description="实施人ID")
    implementation_result: Optional[str] = Field(None, description="实施结果")
    
    suggestion_metadata: Optional[Dict[str, Any]] = Field(None, description="建议元数据")
    tags: Optional[List[str]] = Field(None, description="标签")
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class SuggestionListResponseSchema(BaseModel):
    """建议列表响应模式"""
    suggestions: List[SuggestionResponseSchema] = Field(..., description="建议列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    has_more: bool = Field(..., description="是否有更多数据")


class GenerateSuggestionsRequestSchema(BaseModel):
    """生成建议请求模式"""
    context: ProjectContextSchema = Field(..., description="项目上下文")
    suggestion_types: Optional[List[SuggestionType]] = Field(
        default_factory=list, 
        description="指定生成的建议类型，为空则生成所有类型"
    )
    max_suggestions: Optional[int] = Field(
        default=10, 
        ge=1, 
        le=50, 
        description="最大建议数量"
    )
    include_low_priority: bool = Field(
        default=True, 
        description="是否包含低优先级建议"
    )


class GenerateSuggestionsResponseSchema(BaseModel):
    """生成建议响应模式"""
    suggestions: List[Dict[str, Any]] = Field(..., description="生成的建议列表")
    analysis_summary: Optional[Dict[str, Any]] = Field(None, description="分析摘要")
    generation_metadata: Dict[str, Any] = Field(default_factory=dict, description="生成元数据")
    total_generated: int = Field(..., description="生成的建议总数")
    processing_time: float = Field(..., description="处理时间（秒）")


class RequirementsAnalysisRequestSchema(BaseModel):
    """需求分析请求模式"""
    requirements: List[Dict[str, Any]] = Field(..., description="需求列表")
    analysis_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="分析选项"
    )
    include_ai_analysis: bool = Field(
        default=True, 
        description="是否包含AI分析"
    )


class RequirementsAnalysisResponseSchema(BaseModel):
    """需求分析响应模式"""
    analysis_id: Optional[int] = Field(None, description="分析ID")
    quality_analysis: RequirementsQualityAnalysisSchema = Field(..., description="质量分析结果")
    suggestions: List[Dict[str, Any]] = Field(default_factory=list, description="改进建议")
    problematic_requirements: List[Dict[str, Any]] = Field(default_factory=list, description="问题需求")
    coverage_analysis: Optional[Dict[str, Any]] = Field(None, description="覆盖度分析")
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict, description="分析元数据")
    processing_time: float = Field(..., description="处理时间（秒）")


class TestSuggestionsRequestSchema(BaseModel):
    """测试建议请求模式"""
    existing_tests: List[Dict[str, Any]] = Field(..., description="现有测试用例")
    requirements: List[Dict[str, Any]] = Field(..., description="需求列表")
    coverage_data: Optional[Dict[str, Any]] = Field(None, description="覆盖率数据")
    max_suggestions: Optional[int] = Field(default=10, ge=1, le=20, description="最大建议数量")


class TestSuggestionsResponseSchema(BaseModel):
    """测试建议响应模式"""
    suggestions: List[TestSuggestionSchema] = Field(..., description="测试建议列表")
    coverage_gaps: List[Dict[str, Any]] = Field(default_factory=list, description="覆盖率缺口")
    analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="分析摘要")
    processing_time: float = Field(..., description="处理时间（秒）")


class OptimizationSuggestionsRequestSchema(BaseModel):
    """优化建议请求模式"""
    performance_metrics: Dict[str, Any] = Field(..., description="性能指标")
    resource_usage: Optional[Dict[str, Any]] = Field(default_factory=dict, description="资源使用情况")
    bottlenecks: Optional[List[str]] = Field(default_factory=list, description="已知瓶颈")
    optimization_goals: Optional[List[str]] = Field(default_factory=list, description="优化目标")


class OptimizationSuggestionsResponseSchema(BaseModel):
    """优化建议响应模式"""
    suggestions: List[OptimizationSuggestionSchema] = Field(..., description="优化建议列表")
    identified_bottlenecks: List[str] = Field(default_factory=list, description="识别的瓶颈")
    performance_analysis: Dict[str, Any] = Field(default_factory=dict, description="性能分析")
    processing_time: float = Field(..., description="处理时间（秒）")


class SuggestionStatsSchema(BaseModel):
    """建议统计模式"""
    total_suggestions: int = Field(..., description="建议总数")
    by_status: Dict[str, int] = Field(default_factory=dict, description="按状态统计")
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    by_priority: Dict[str, int] = Field(default_factory=dict, description="按优先级统计")
    avg_rating: Optional[float] = Field(None, description="平均评分")
    implementation_rate: float = Field(..., description="实施率")
    recent_suggestions: int = Field(..., description="最近建议数量")


class SuggestionFilterSchema(BaseModel):
    """建议过滤模式"""
    status: Optional[List[SuggestionStatus]] = Field(None, description="状态过滤")
    type: Optional[List[SuggestionType]] = Field(None, description="类型过滤")
    priority: Optional[List[SuggestionPriority]] = Field(None, description="优先级过滤")
    category: Optional[List[SuggestionCategory]] = Field(None, description="分类过滤")
    project_id: Optional[int] = Field(None, description="项目ID过滤")
    date_from: Optional[datetime] = Field(None, description="开始日期")
    date_to: Optional[datetime] = Field(None, description="结束日期")
    search_text: Optional[str] = Field(None, description="搜索文本")
    min_rating: Optional[int] = Field(None, ge=1, le=5, description="最低评分")
    has_feedback: Optional[bool] = Field(None, description="是否有反馈")
    implemented: Optional[bool] = Field(None, description="是否已实施")


class BulkSuggestionUpdateSchema(BaseModel):
    """批量更新建议模式"""
    suggestion_ids: List[int] = Field(..., description="建议ID列表")
    updates: SuggestionUpdateSchema = Field(..., description="更新内容")
    update_reason: Optional[str] = Field(None, description="更新原因")


class SuggestionExportSchema(BaseModel):
    """建议导出模式"""
    format: str = Field(default="json", description="导出格式 (json, csv, excel)")
    filters: Optional[SuggestionFilterSchema] = Field(None, description="过滤条件")
    include_metadata: bool = Field(default=False, description="是否包含元数据")
    include_feedback: bool = Field(default=True, description="是否包含用户反馈")


class ProjectStatusAnalysisResponseSchema(BaseModel):
    """项目状况分析响应模式"""
    analysis_result: Dict[str, Any] = Field(..., description="分析结果")
    processing_time: float = Field(..., description="处理时间（秒）")
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict, description="分析元数据")


class RequirementClarityAnalysisSchema(BaseModel):
    """单个需求清晰度分析模式"""
    requirement_number: int = Field(..., description="需求编号")
    requirement_id: str = Field(..., description="需求ID")
    title: str = Field(..., description="需求标题")
    clarity_score: float = Field(..., ge=0.0, le=1.0, description="清晰度得分")
    dimension_scores: Dict[str, float] = Field(..., description="各维度得分")
    clarity_level: str = Field(..., description="清晰度等级")
    identified_issues: List[str] = Field(default_factory=list, description="识别的问题")
    improvement_suggestions: List[str] = Field(default_factory=list, description="改进建议")
    word_count: int = Field(..., description="字数统计")
    has_acceptance_criteria: bool = Field(..., description="是否有验收标准")
    criteria_count: int = Field(..., description="验收标准数量")


class ClarityDistributionSchema(BaseModel):
    """清晰度分布统计模式"""
    excellent: Dict[str, Any] = Field(..., description="优秀等级统计")
    good: Dict[str, Any] = Field(..., description="良好等级统计")
    fair: Dict[str, Any] = Field(..., description="一般等级统计")
    poor: Dict[str, Any] = Field(..., description="较差等级统计")
    average_score: float = Field(..., description="平均得分")
    median_score: float = Field(..., description="中位数得分")
    min_score: float = Field(..., description="最低得分")
    max_score: float = Field(..., description="最高得分")


class ClarityImprovementRecommendationSchema(BaseModel):
    """清晰度改进建议模式"""
    priority: str = Field(..., description="优先级")
    category: str = Field(..., description="分类")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    action_items: List[str] = Field(default_factory=list, description="行动项")
    expected_benefit: str = Field(..., description="预期收益")
    estimated_effort: str = Field(..., description="预估工作量")


class DetailedClarityAnalysisResponseSchema(BaseModel):
    """详细清晰度分析响应模式"""
    overall_clarity_score: float = Field(..., ge=0.0, le=1.0, description="整体清晰度得分")
    total_requirements: int = Field(..., description="需求总数")
    clarity_distribution: ClarityDistributionSchema = Field(..., description="清晰度分布统计")
    detailed_analysis: List[RequirementClarityAnalysisSchema] = Field(..., description="详细分析结果")
    improvement_recommendations: List[ClarityImprovementRecommendationSchema] = Field(
        default_factory=list, 
        description="改进建议"
    )
    analysis_summary: str = Field(..., description="分析摘要")
    global_terms: Dict[str, int] = Field(default_factory=dict, description="全局术语词典")
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict, description="分析元数据")
    processing_time: float = Field(..., description="处理时间（秒）")