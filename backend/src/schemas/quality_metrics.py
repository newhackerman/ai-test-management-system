"""
质量度量相关数据传输对象(DTO)

本模块定义了质量度量和评估相关的数据传输对象
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

class QualityMetricType(str, Enum):
    """质量指标类型枚举"""
    COVERAGE = "coverage"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    RELIABILITY = "reliability"
    MAINTAINABILITY = "maintainability"

class TrendDirection(str, Enum):
    """趋势方向枚举"""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"

class AlertLevel(str, Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class ComparisonResult(str, Enum):
    """对比结果枚举"""
    EXCELLENT = "excellent"
    ABOVE_AVERAGE = "above_average"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    NEEDS_IMPROVEMENT = "needs_improvement"

# 基础数据模型
class QualityMetricDefinition(BaseModel):
    """质量指标定义"""
    name: str
    display_name: str
    description: str
    metric_type: QualityMetricType
    unit: Optional[str] = None
    calculation_method: str
    target_value: Optional[float] = None
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    is_higher_better: bool = True
    weight: float = 1.0

class QualityMetricValue(BaseModel):
    """质量指标值"""
    metric_name: str
    value: float
    unit: Optional[str] = None
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    project_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class QualityMetricsSnapshot(BaseModel):
    """质量指标快照"""
    project_id: Optional[int] = None
    snapshot_date: datetime = Field(default_factory=datetime.utcnow)
    metrics: Dict[str, float] = Field(default_factory=dict)
    overall_score: Optional[float] = None
    grade: Optional[str] = None  # A, B, C, D, F
    
class QualityTrend(BaseModel):
    """质量趋势"""
    metric_name: str
    trend_direction: TrendDirection
    growth_rate: float
    confidence: float
    data_points: List[Dict[str, Any]] = Field(default_factory=list)
    analysis_period: Dict[str, datetime]
    predictions: Optional[Dict[str, Any]] = None

class QualityAlert(BaseModel):
    """质量告警"""
    alert_id: str
    metric_name: str
    alert_level: AlertLevel
    message: str
    current_value: float
    threshold_value: float
    project_id: Optional[int] = None
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None

class QualityImprovement(BaseModel):
    """质量改进建议"""
    improvement_id: str
    category: str
    title: str
    description: str
    priority_score: float
    impact_level: str  # high, medium, low
    effort_level: str  # high, medium, low
    actions: List[str] = Field(default_factory=list)
    expected_impact: str
    timeline: Optional[str] = None
    responsible_role: Optional[str] = None

class QualityBaseline(BaseModel):
    """质量基线"""
    project_id: int
    baseline_name: str
    description: Optional[str] = None
    baseline_metrics: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = None
    version: str = "1.0"
    is_active: bool = True

class QualityTarget(BaseModel):
    """质量目标"""
    project_id: int
    target_name: str
    description: Optional[str] = None
    target_metrics: Dict[str, float] = Field(default_factory=dict)
    target_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[int] = None
    status: str = "active"  # active, achieved, cancelled

class QualityBenchmark(BaseModel):
    """质量基准对比"""
    metric_name: str
    current_value: float
    industry_average: Optional[float] = None
    best_practice: Optional[float] = None
    percentile_rank: Optional[float] = None
    comparison_result: ComparisonResult
    gap_analysis: Optional[str] = None

class QualityAssessment(BaseModel):
    """质量评估"""
    project_id: Optional[int] = None
    assessment_date: datetime = Field(default_factory=datetime.utcnow)
    overall_score: float
    grade: str
    metrics_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[QualityImprovement] = Field(default_factory=list)
    benchmarks: List[QualityBenchmark] = Field(default_factory=list)

class QualityDashboard(BaseModel):
    """质量仪表板数据"""
    project_id: Optional[int] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    current_metrics: Dict[str, float] = Field(default_factory=dict)
    trends: Dict[str, QualityTrend] = Field(default_factory=dict)
    alerts: List[QualityAlert] = Field(default_factory=list)
    recent_improvements: List[QualityImprovement] = Field(default_factory=list)
    key_insights: List[str] = Field(default_factory=list)

# 请求和响应模型
class CalculateMetricsRequest(BaseModel):
    """计算指标请求"""
    project_id: Optional[int] = None
    date_range: Optional[Dict[str, datetime]] = None
    metrics: Optional[List[str]] = None
    include_trends: bool = False
    include_predictions: bool = False

class CalculateMetricsResponse(BaseModel):
    """计算指标响应"""
    metrics: Dict[str, float]
    overall_score: Optional[float] = None
    grade: Optional[str] = None
    trends: Optional[Dict[str, QualityTrend]] = None
    predictions: Optional[Dict[str, Any]] = None
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

class MonitorMetricsRequest(BaseModel):
    """监控指标请求"""
    project_id: Optional[int] = None
    check_thresholds: bool = True
    check_trends: bool = True
    notification_enabled: bool = True

class MonitorMetricsResponse(BaseModel):
    """监控指标响应"""
    alerts: List[QualityAlert]
    metrics_status: Dict[str, str]  # ok, warning, critical
    monitoring_summary: str
    next_check_time: Optional[datetime] = None

class TrendAnalysisRequest(BaseModel):
    """趋势分析请求"""
    project_id: Optional[int] = None
    metrics: Optional[List[str]] = None
    analysis_period_days: int = 30
    include_predictions: bool = True
    prediction_horizon_days: int = 7

class TrendAnalysisResponse(BaseModel):
    """趋势分析响应"""
    trends: Dict[str, QualityTrend]
    predictions: Dict[str, Any]
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

class ImprovementSuggestionsRequest(BaseModel):
    """改进建议请求"""
    project_id: Optional[int] = None
    focus_areas: Optional[List[str]] = None
    priority_level: Optional[str] = None  # high, medium, low, all
    include_best_practices: bool = True

class ImprovementSuggestionsResponse(BaseModel):
    """改进建议响应"""
    suggestions: List[QualityImprovement]
    priority_matrix: Dict[str, List[str]] = Field(default_factory=dict)
    implementation_roadmap: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_impact: Dict[str, float] = Field(default_factory=dict)

class BaselineManagementRequest(BaseModel):
    """基线管理请求"""
    project_id: int
    action: str  # create, update, get, compare, delete
    baseline_data: Optional[Dict[str, Any]] = None
    baseline_name: Optional[str] = None

class BaselineManagementResponse(BaseModel):
    """基线管理响应"""
    baseline: Optional[QualityBaseline] = None
    comparison: Optional[Dict[str, Any]] = None
    message: str
    success: bool = True

class TargetManagementRequest(BaseModel):
    """目标管理请求"""
    project_id: int
    action: str  # set, update, get, delete, check_progress
    target_data: Optional[Dict[str, Any]] = None
    target_name: Optional[str] = None

class TargetManagementResponse(BaseModel):
    """目标管理响应"""
    target: Optional[QualityTarget] = None
    progress: Optional[Dict[str, Any]] = None
    achievement_status: Optional[Dict[str, str]] = None
    message: str
    success: bool = True

class BenchmarkAnalysisRequest(BaseModel):
    """基准分析请求"""
    project_id: Optional[int] = None
    benchmark_type: str = "industry"  # industry, internal, custom
    metrics: Optional[List[str]] = None
    include_gap_analysis: bool = True

class BenchmarkAnalysisResponse(BaseModel):
    """基准分析响应"""
    overall_score: float
    grade: str
    benchmarks: List[QualityBenchmark]
    strengths: List[str] = Field(default_factory=list)
    improvement_areas: List[str] = Field(default_factory=list)
    gap_analysis: Dict[str, str] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)

class QualityReportRequest(BaseModel):
    """质量报告请求"""
    project_id: Optional[int] = None
    report_type: str = "comprehensive"  # comprehensive, summary, trends, benchmarks
    date_range: Optional[Dict[str, datetime]] = None
    include_charts: bool = True
    include_recommendations: bool = True
    format: str = "json"  # json, pdf, html, excel

class QualityReportResponse(BaseModel):
    """质量报告响应"""
    report_id: str
    report_type: str
    project_id: Optional[int] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)
    trends: Dict[str, QualityTrend] = Field(default_factory=dict)
    benchmarks: List[QualityBenchmark] = Field(default_factory=list)
    recommendations: List[QualityImprovement] = Field(default_factory=list)
    charts: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None

class QualityConfiguration(BaseModel):
    """质量配置"""
    project_id: Optional[int] = None
    metric_definitions: Dict[str, QualityMetricDefinition] = Field(default_factory=dict)
    alert_thresholds: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    monitoring_intervals: Dict[str, int] = Field(default_factory=dict)  # in minutes
    notification_settings: Dict[str, Any] = Field(default_factory=dict)
    retention_days: int = 90
    auto_baseline_update: bool = False
    trend_analysis_enabled: bool = True

class QualityAuditLog(BaseModel):
    """质量审计日志"""
    log_id: str
    project_id: Optional[int] = None
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class QualityHealthCheck(BaseModel):
    """质量健康检查"""
    project_id: Optional[int] = None
    check_time: datetime = Field(default_factory=datetime.utcnow)
    overall_health: str  # excellent, good, fair, poor, critical
    health_score: float  # 0-100
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    next_check_time: Optional[datetime] = None

class MetricCalculationResult(BaseModel):
    """指标计算结果"""
    metric_name: str
    value: float
    calculation_details: Dict[str, Any] = Field(default_factory=dict)
    data_quality_score: float = 1.0
    confidence_level: float = 1.0
    calculation_time: datetime = Field(default_factory=datetime.utcnow)
    warnings: List[str] = Field(default_factory=list)

class QualityInsight(BaseModel):
    """质量洞察"""
    insight_id: str
    insight_type: str  # trend, anomaly, opportunity, risk
    title: str
    description: str
    severity: str  # info, warning, critical
    confidence: float
    supporting_data: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

class QualityPrediction(BaseModel):
    """质量预测"""
    metric_name: str
    prediction_horizon_days: int
    predicted_values: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_intervals: Dict[str, List[float]] = Field(default_factory=dict)
    model_accuracy: float
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class QualityGovernance(BaseModel):
    """质量治理"""
    project_id: int
    governance_level: str  # basic, standard, advanced, enterprise
    policies: Dict[str, Any] = Field(default_factory=dict)
    approval_workflows: Dict[str, List[str]] = Field(default_factory=dict)
    compliance_requirements: List[str] = Field(default_factory=list)
    audit_frequency: str  # daily, weekly, monthly, quarterly
    stakeholders: List[Dict[str, Any]] = Field(default_factory=list)