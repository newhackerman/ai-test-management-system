"""
统计分析相关的数据模式定义

本模块定义了统计分析相关的请求和响应数据模式，包括：
- 项目统计数据模式
- 绩效评估数据模式
- 趋势分析数据模式
- KPI指标数据模式
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class MetricType(str, Enum):
    """指标类型枚举"""
    PROGRESS = "progress"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    COST = "cost"
    RISK = "risk"
    COLLABORATION = "collaboration"


class TrendDirection(str, Enum):
    """趋势方向枚举"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class PerformanceLevel(str, Enum):
    """绩效等级枚举"""
    EXCELLENT = "excellent"
    GOOD = "good"
    SATISFACTORY = "satisfactory"
    NEEDS_IMPROVEMENT = "needs_improvement"


class TeamMaturityLevel(str, Enum):
    """团队成熟度等级枚举"""
    HIGH_PERFORMING = "high_performing"
    PERFORMING = "performing"
    FORMING = "forming"
    STORMING = "storming"


# 基础数据模式
class TimeProgressSchema(BaseModel):
    """时间进度模式"""
    progress_rate: float = Field(..., ge=0, le=1, description="进度比率")
    deviation: float = Field(..., description="偏差")
    days_elapsed: int = Field(..., ge=0, description="已用天数")
    days_remaining: int = Field(..., ge=0, description="剩余天数")
    planned_duration: int = Field(..., ge=0, description="计划工期")
    is_on_schedule: bool = Field(..., description="是否按计划进行")


class TaskProgressSchema(BaseModel):
    """任务进度模式"""
    progress_rate: float = Field(..., ge=0, le=1, description="进度比率")
    total_tasks: int = Field(..., ge=0, description="任务总数")
    completed_tasks: int = Field(..., ge=0, description="已完成任务数")
    in_progress_tasks: int = Field(..., ge=0, description="进行中任务数")
    blocked_tasks: int = Field(..., ge=0, description="阻塞任务数")
    overdue_tasks: int = Field(..., ge=0, description="逾期任务数")
    task_distribution: Dict[str, Dict[str, int]] = Field(..., description="任务分布")


class QualityProgressSchema(BaseModel):
    """质量进度模式"""
    progress_rate: float = Field(..., ge=0, le=1, description="质量进度比率")
    test_case_count: int = Field(..., ge=0, description="测试用例总数")
    passed_test_count: int = Field(..., ge=0, description="通过测试数")
    test_pass_rate: float = Field(..., ge=0, le=1, description="测试通过率")
    defect_count: int = Field(..., ge=0, description="缺陷总数")
    defect_density: float = Field(..., ge=0, description="缺陷密度")
    defect_details: Dict[str, Any] = Field(..., description="缺陷详情")
    quality_score: float = Field(..., ge=0, le=1, description="质量评分")


class MilestoneProgressSchema(BaseModel):
    """里程碑进度模式"""
    progress_rate: float = Field(..., ge=0, le=1, description="里程碑进度比率")
    total_milestones: int = Field(..., ge=0, description="里程碑总数")
    completed_milestones: int = Field(..., ge=0, description="已完成里程碑数")
    overdue_milestones: int = Field(..., ge=0, description="逾期里程碑数")
    upcoming_milestones: int = Field(..., ge=0, description="即将到期里程碑数")


class EfficiencyMetricsSchema(BaseModel):
    """效率指标模式"""
    productivity_rate: float = Field(..., ge=0, description="生产率")
    avg_hours_per_day: float = Field(..., ge=0, description="日均工时")
    total_hours: float = Field(..., ge=0, description="总工时")
    work_days: int = Field(..., ge=0, description="工作天数")
    efficiency_trend: str = Field(..., description="效率趋势")
    work_type_distribution: Dict[str, float] = Field(..., description="工作类型分布")


class CostMetricsSchema(BaseModel):
    """成本指标模式"""
    budget: float = Field(..., ge=0, description="预算")
    actual_cost: float = Field(..., ge=0, description="实际成本")
    cost_variance: float = Field(..., description="成本偏差")
    cost_variance_percentage: float = Field(..., description="成本偏差百分比")
    cost_performance_index: float = Field(..., gt=0, description="成本绩效指数")
    estimated_final_cost: float = Field(..., ge=0, description="预估最终成本")
    is_over_budget: bool = Field(..., description="是否超预算")


class RiskMetricsSchema(BaseModel):
    """风险指标模式"""
    total_risks: int = Field(..., ge=0, description="风险总数")
    high_risks: int = Field(..., ge=0, description="高风险数量")
    open_risks: int = Field(..., ge=0, description="开放风险数量")
    avg_risk_score: float = Field(..., ge=0, description="平均风险评分")
    risk_distribution: Dict[str, Dict[str, Union[int, float]]] = Field(..., description="风险分布")


class CollaborationMetricsSchema(BaseModel):
    """协作指标模式"""
    team_size: int = Field(..., ge=0, description="团队规模")
    avg_allocation: float = Field(..., ge=0, le=100, description="平均分配比例")
    role_distribution: Dict[str, int] = Field(..., description="角色分布")
    collaboration_score: float = Field(..., ge=0, le=1, description="协作评分")


# 统计分析请求和响应模式
class ProjectStatisticsRequest(BaseModel):
    """项目统计请求"""
    project_id: int = Field(..., gt=0, description="项目ID")
    include_predictions: bool = Field(default=False, description="是否包含预测数据")
    cache_duration: int = Field(default=300, ge=0, le=3600, description="缓存时长（秒）")


class ProjectStatisticsResponse(BaseModel):
    """项目统计响应"""
    project_id: int = Field(..., description="项目ID")
    time_progress: TimeProgressSchema = Field(..., description="时间进度")
    task_progress: TaskProgressSchema = Field(..., description="任务进度")
    quality_progress: QualityProgressSchema = Field(..., description="质量进度")
    milestone_progress: MilestoneProgressSchema = Field(..., description="里程碑进度")
    overall_progress: float = Field(..., ge=0, le=1, description="综合进度")
    efficiency_metrics: EfficiencyMetricsSchema = Field(..., description="效率指标")
    cost_metrics: CostMetricsSchema = Field(..., description="成本指标")
    risk_metrics: RiskMetricsSchema = Field(..., description="风险指标")
    collaboration_metrics: CollaborationMetricsSchema = Field(..., description="协作指标")
    calculated_at: datetime = Field(..., description="计算时间")


class TrendAnalysisRequest(BaseModel):
    """趋势分析请求"""
    project_id: int = Field(..., gt=0, description="项目ID")
    metric_name: str = Field(..., description="指标名称")
    days: int = Field(default=30, ge=7, le=365, description="分析天数")
    prediction_days: int = Field(default=7, ge=1, le=30, description="预测天数")


class TimeSeriesDataPoint(BaseModel):
    """时间序列数据点"""
    date: str = Field(..., description="日期")
    value: float = Field(..., description="值")
    metric_name: str = Field(..., description="指标名称")


class PredictionData(BaseModel):
    """预测数据"""
    predicted_values: List[Dict[str, Union[int, float]]] = Field(..., description="预测值列表")
    method: str = Field(..., description="预测方法")
    slope: Optional[float] = Field(None, description="斜率")
    intercept: Optional[float] = Field(None, description="截距")


class TrendAnalysisResponse(BaseModel):
    """趋势分析响应"""
    metric_name: str = Field(..., description="指标名称")
    time_series_data: List[TimeSeriesDataPoint] = Field(..., description="时间序列数据")
    trend_direction: TrendDirection = Field(..., description="趋势方向")
    trend_strength: float = Field(..., ge=0, le=1, description="趋势强度")
    prediction: PredictionData = Field(..., description="预测数据")
    confidence_level: float = Field(..., ge=0, le=1, description="置信度")
    analyzed_at: datetime = Field(..., description="分析时间")


# 绩效评估相关模式
class IndividualPerformanceRequest(BaseModel):
    """个人绩效评估请求"""
    user_id: int = Field(..., gt=0, description="用户ID")
    project_id: Optional[int] = Field(None, gt=0, description="项目ID（可选）")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    include_detailed_metrics: bool = Field(default=True, description="是否包含详细指标")


class DetailedMetrics(BaseModel):
    """详细指标"""
    efficiency: Dict[str, float] = Field(..., description="效率指标")
    quality: Dict[str, float] = Field(..., description="质量指标")
    collaboration: Dict[str, float] = Field(..., description="协作指标")
    skill_growth: Dict[str, float] = Field(..., description="技能成长指标")
    innovation: Dict[str, float] = Field(..., description="创新指标")


class IndividualPerformanceResponse(BaseModel):
    """个人绩效评估响应"""
    user_id: int = Field(..., description="用户ID")
    user_name: str = Field(..., description="用户姓名")
    evaluation_period: List[str] = Field(..., description="评估周期")
    
    # 工作效率指标
    task_completion_rate: float = Field(..., ge=0, le=1, description="任务完成率")
    on_time_delivery_rate: float = Field(..., ge=0, le=1, description="按时交付率")
    work_hour_efficiency: float = Field(..., ge=0, le=1, description="工时效率")
    
    # 工作质量指标
    defect_rate: float = Field(..., ge=0, description="缺陷率")
    rework_rate: float = Field(..., ge=0, description="返工率")
    customer_satisfaction: float = Field(..., ge=0, le=1, description="客户满意度")
    
    # 协作能力指标
    team_collaboration_score: float = Field(..., ge=0, le=1, description="团队协作评分")
    communication_effectiveness: float = Field(..., ge=0, le=1, description="沟通效果")
    knowledge_sharing_score: float = Field(..., ge=0, le=1, description="知识分享评分")
    
    # 技能成长指标
    skill_improvement_score: float = Field(..., ge=0, le=1, description="技能提升评分")
    learning_activity_score: float = Field(..., ge=0, le=1, description="学习活动评分")
    certification_score: float = Field(..., ge=0, le=1, description="认证评分")
    
    # 创新贡献指标
    innovation_contribution_score: float = Field(..., ge=0, le=1, description="创新贡献评分")
    process_improvement_score: float = Field(..., ge=0, le=1, description="流程改进评分")
    best_practice_score: float = Field(..., ge=0, le=1, description="最佳实践评分")
    
    # 综合评分
    overall_score: float = Field(..., ge=0, le=1, description="综合评分")
    performance_level: PerformanceLevel = Field(..., description="绩效等级")
    
    # 详细指标
    detailed_metrics: DetailedMetrics = Field(..., description="详细指标")
    
    # 改进建议
    strengths: List[str] = Field(..., description="优势")
    improvement_areas: List[str] = Field(..., description="改进领域")
    development_recommendations: List[str] = Field(..., description="发展建议")
    
    evaluated_at: datetime = Field(..., description="评估时间")


class TeamPerformanceRequest(BaseModel):
    """团队绩效评估请求"""
    project_id: int = Field(..., gt=0, description="项目ID")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    include_individual_breakdown: bool = Field(default=False, description="是否包含个人分解")


class TeamPerformanceResponse(BaseModel):
    """团队绩效评估响应"""
    project_id: int = Field(..., description="项目ID")
    team_members: List[int] = Field(..., description="团队成员ID列表")
    evaluation_period: List[str] = Field(..., description="评估周期")
    
    # 团队效率指标
    team_productivity: float = Field(..., ge=0, le=1, description="团队生产力")
    collaboration_effectiveness: float = Field(..., ge=0, le=1, description="协作效果")
    goal_achievement_rate: float = Field(..., ge=0, le=1, description="目标达成率")
    
    # 团队质量指标
    team_quality_score: float = Field(..., ge=0, le=1, description="团队质量评分")
    customer_satisfaction: float = Field(..., ge=0, le=1, description="客户满意度")
    delivery_quality: float = Field(..., ge=0, le=1, description="交付质量")
    
    # 团队协作指标
    communication_score: float = Field(..., ge=0, le=1, description="沟通评分")
    conflict_resolution_score: float = Field(..., ge=0, le=1, description="冲突解决评分")
    knowledge_sharing_score: float = Field(..., ge=0, le=1, description="知识分享评分")
    
    # 团队发展指标
    skill_diversity_score: float = Field(..., ge=0, le=1, description="技能多样性评分")
    learning_culture_score: float = Field(..., ge=0, le=1, description="学习文化评分")
    innovation_score: float = Field(..., ge=0, le=1, description="创新评分")
    
    # 综合评分
    overall_score: float = Field(..., ge=0, le=1, description="综合评分")
    team_maturity_level: TeamMaturityLevel = Field(..., description="团队成熟度等级")
    
    # 团队分析
    team_strengths: List[str] = Field(..., description="团队优势")
    team_challenges: List[str] = Field(..., description="团队挑战")
    improvement_recommendations: List[str] = Field(..., description="改进建议")
    
    # 绩效分布
    performance_distribution: Dict[str, int] = Field(..., description="绩效分布")
    
    evaluated_at: datetime = Field(..., description="评估时间")


class SkillAssessmentRequest(BaseModel):
    """技能评估请求"""
    user_id: int = Field(..., gt=0, description="用户ID")
    skill_categories: List[str] = Field(..., min_items=1, description="技能类别列表")
    include_development_plan: bool = Field(default=True, description="是否包含发展计划")


class GapAnalysis(BaseModel):
    """差距分析"""
    gap_level: int = Field(..., description="差距等级")
    gap_description: str = Field(..., description="差距描述")
    estimated_time_months: int = Field(..., ge=0, description="预估时间（月）")
    priority: str = Field(..., description="优先级")


class DevelopmentPlanItem(BaseModel):
    """发展计划项"""
    action: str = Field(..., description="行动")
    timeline: str = Field(..., description="时间线")
    resources: List[str] = Field(..., description="资源")
    success_criteria: str = Field(..., description="成功标准")


class SkillAssessmentResponse(BaseModel):
    """技能评估响应"""
    user_id: int = Field(..., description="用户ID")
    skill_category: str = Field(..., description="技能类别")
    current_level: int = Field(..., ge=1, le=5, description="当前等级")
    target_level: int = Field(..., ge=1, le=5, description="目标等级")
    gap_analysis: GapAnalysis = Field(..., description="差距分析")
    development_plan: List[DevelopmentPlanItem] = Field(..., description="发展计划")
    assessed_at: datetime = Field(..., description="评估时间")


# KPI指标相关模式
class KPIMetricsRequest(BaseModel):
    """KPI指标请求"""
    project_id: int = Field(..., gt=0, description="项目ID")
    include_benchmark: bool = Field(default=True, description="是否包含基准对比")
    benchmark_type: str = Field(default="industry", description="基准类型")


class BenchmarkComparison(BaseModel):
    """基准对比"""
    current: float = Field(..., description="当前值")
    benchmark: float = Field(..., description="基准值")
    status: str = Field(..., description="状态")


class PerformanceIndicators(BaseModel):
    """绩效指标"""
    overall_health: float = Field(..., ge=0, le=1, description="整体健康度")
    critical_areas: List[str] = Field(..., description="关键领域")
    excellent_areas: List[str] = Field(..., description="优秀领域")


class KPIMetricsResponse(BaseModel):
    """KPI指标响应"""
    project_id: int = Field(..., description="项目ID")
    kpi_metrics: Dict[str, float] = Field(..., description="KPI指标")
    benchmark_comparison: Dict[str, BenchmarkComparison] = Field(..., description="基准对比")
    performance_indicators: PerformanceIndicators = Field(..., description="绩效指标")
    calculated_at: datetime = Field(..., description="计算时间")


# 项目对比分析模式
class ProjectComparisonRequest(BaseModel):
    """项目对比分析请求"""
    project_ids: List[int] = Field(..., min_items=2, max_items=10, description="项目ID列表")
    metrics: List[str] = Field(..., min_items=1, description="对比指标列表")
    include_rankings: bool = Field(default=True, description="是否包含排名")


class ProjectComparisonResponse(BaseModel):
    """项目对比分析响应"""
    comparison_data: Dict[str, Dict[str, float]] = Field(..., description="对比数据")
    rankings: Dict[str, List[str]] = Field(..., description="排名")
    summary: Dict[str, Any] = Field(..., description="汇总信息")


# 仪表板汇总模式
class DashboardSummaryRequest(BaseModel):
    """仪表板汇总请求"""
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表（可选）")
    include_trends: bool = Field(default=False, description="是否包含趋势")
    time_range_days: int = Field(default=30, ge=7, le=365, description="时间范围（天）")


class ProjectSummaryItem(BaseModel):
    """项目汇总项"""
    project_id: int = Field(..., description="项目ID")
    progress: float = Field(..., ge=0, le=1, description="进度")
    quality_score: float = Field(..., ge=0, le=1, description="质量评分")
    risk_score: float = Field(..., ge=0, description="风险评分")
    budget_utilization: float = Field(..., ge=0, description="预算利用率")
    team_size: int = Field(..., ge=0, description="团队规模")


class DashboardSummaryData(BaseModel):
    """仪表板汇总数据"""
    total_projects: int = Field(..., ge=0, description="项目总数")
    active_projects: int = Field(..., ge=0, description="活跃项目数")
    completed_projects: int = Field(..., ge=0, description="已完成项目数")
    overdue_projects: int = Field(..., ge=0, description="逾期项目数")
    avg_progress: float = Field(..., ge=0, le=1, description="平均进度")
    total_budget: float = Field(..., ge=0, description="总预算")
    total_cost: float = Field(..., ge=0, description="总成本")
    avg_quality_score: float = Field(..., ge=0, le=1, description="平均质量评分")
    high_risk_projects: int = Field(..., ge=0, description="高风险项目数")
    team_utilization: float = Field(..., ge=0, le=1, description="团队利用率")
    project_details: List[ProjectSummaryItem] = Field(..., description="项目详情")


class DashboardSummaryResponse(BaseModel):
    """仪表板汇总响应"""
    summary: DashboardSummaryData = Field(..., description="汇总数据")
    generated_at: str = Field(..., description="生成时间")


# 验证器
class ProjectStatisticsResponseValidator(BaseModel):
    """项目统计响应验证器"""
    
    @validator('overall_progress')
    def validate_overall_progress(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('综合进度必须在0-1之间')
        return v
    
    @validator('calculated_at')
    def validate_calculated_at(cls, v):
        if v > datetime.utcnow():
            raise ValueError('计算时间不能是未来时间')
        return v


class PerformanceResponseValidator(BaseModel):
    """绩效响应验证器"""
    
    @validator('overall_score')
    def validate_overall_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('综合评分必须在0-1之间')
        return v
    
    @validator('evaluation_period')
    def validate_evaluation_period(cls, v):
        if len(v) != 2:
            raise ValueError('评估周期必须包含开始和结束日期')
        try:
            start_date = datetime.fromisoformat(v[0]).date()
            end_date = datetime.fromisoformat(v[1]).date()
            if start_date >= end_date:
                raise ValueError('开始日期必须早于结束日期')
        except ValueError as e:
            raise ValueError(f'日期格式错误: {e}')
        return v