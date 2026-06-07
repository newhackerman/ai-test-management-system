"""
测试分析数据传输对象(DTO)

本模块定义了测试数据分析相关的数据传输对象
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum

class ChartType(str, Enum):
    """图表类型枚举"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    GAUGE = "gauge"

class TrendDirection(str, Enum):
    """趋势方向枚举"""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"

class AlertSeverity(str, Enum):
    """告警严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# 基础数据模型
class TestMetrics(BaseModel):
    """测试指标"""
    # 基础统计
    total_test_cases: int = 0
    total_test_executions: int = 0
    total_defects: int = 0
    total_test_plans: int = 0
    
    # 执行统计
    passed_executions: int = 0
    failed_executions: int = 0
    blocked_executions: int = 0
    skipped_executions: int = 0
    
    # 比率指标
    pass_rate: float = 0.0
    fail_rate: float = 0.0
    defect_density: float = 0.0
    
    # 缺陷统计
    open_defects: int = 0
    resolved_defects: int = 0
    critical_defects: int = 0
    high_defects: int = 0
    
    # 覆盖率指标
    requirement_coverage: float = 0.0
    test_coverage: float = 0.0
    
    # 效率指标
    avg_execution_time: float = 0.0
    defect_detection_rate: float = 0.0
    
    # 质量指标
    quality_score: float = 0.0
    stability_index: float = 0.0
    
    # 时间信息
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

class ChartData(BaseModel):
    """图表数据"""
    chart_type: ChartType
    title: str
    data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

class TrendData(BaseModel):
    """趋势数据点"""
    date: datetime
    value: float
    label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TrendAnalysis(BaseModel):
    """趋势分析"""
    # 执行趋势
    execution_trend: Optional[Dict[str, Any]] = None
    pass_rate_trend: Optional[Dict[str, Any]] = None
    defect_trend: Optional[Dict[str, Any]] = None
    coverage_trend: Optional[Dict[str, Any]] = None
    
    # 预测数据
    predictions: Optional[Dict[str, Any]] = None
    
    # 异常检测
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 分析时间
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

class ComparisonAnalysis(BaseModel):
    """对比分析"""
    # 基础指标变化
    test_cases_change: float = 0.0
    executions_change: float = 0.0
    defects_change: float = 0.0
    
    # 质量指标变化
    pass_rate_change: float = 0.0
    defect_density_change: float = 0.0
    quality_score_change: float = 0.0
    
    # 效率指标变化
    execution_time_change: float = 0.0
    detection_rate_change: float = 0.0
    
    # 洞察和建议
    insights: List[str] = Field(default_factory=list)
    
    # 对比时间
    compared_at: datetime = Field(default_factory=datetime.utcnow)

class QualityAlert(BaseModel):
    """质量告警"""
    id: str
    type: str
    message: str
    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold_value: float
    project_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False

class DashboardData(BaseModel):
    """仪表板数据"""
    # 核心指标
    metrics: TestMetrics
    
    # 图表数据
    charts: Dict[str, ChartData] = Field(default_factory=dict)
    
    # 实时指标
    real_time_metrics: Optional[Dict[str, Any]] = None
    
    # 告警信息
    alerts: List[QualityAlert] = Field(default_factory=list)
    
    # 更新时间
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class AnalysisRequest(BaseModel):
    """分析请求"""
    project_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metrics: Optional[List[str]] = None
    group_by: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class AnalysisResponse(BaseModel):
    """分析响应"""
    request: AnalysisRequest
    metrics: TestMetrics
    trends: Optional[TrendAnalysis] = None
    comparisons: Optional[ComparisonAnalysis] = None
    charts: Dict[str, ChartData] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class AnomalyDetection(BaseModel):
    """异常检测结果"""
    anomaly_id: str
    metric_name: str
    anomaly_type: str  # spike, drop, trend_change, outlier
    detected_at: datetime
    value: float
    expected_range: Dict[str, float]  # min, max
    severity_score: float
    description: str
    recommendations: List[str] = Field(default_factory=list)

class QualityInsight(BaseModel):
    """质量洞察"""
    insight_id: str
    category: str  # quality, efficiency, risk, improvement
    title: str
    description: str
    importance_score: float
    supporting_data: Dict[str, Any]
    recommendations: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class MetricDefinition(BaseModel):
    """指标定义"""
    name: str
    display_name: str
    description: str
    unit: Optional[str] = None
    calculation_method: str
    thresholds: Optional[Dict[str, float]] = None
    is_higher_better: bool = True

class CustomAnalysisRequest(BaseModel):
    """自定义分析请求"""
    name: str
    description: Optional[str] = None
    metrics: List[str]
    dimensions: List[str]
    filters: Optional[Dict[str, Any]] = None
    time_range: Optional[Dict[str, datetime]] = None
    chart_types: List[ChartType] = Field(default_factory=list)

class CustomAnalysisResponse(BaseModel):
    """自定义分析响应"""
    analysis_id: str
    name: str
    description: Optional[str] = None
    results: Dict[str, Any]
    charts: Dict[str, ChartData] = Field(default_factory=dict)
    summary: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class BenchmarkData(BaseModel):
    """基准数据"""
    metric_name: str
    industry_average: Optional[float] = None
    best_practice: Optional[float] = None
    current_value: float
    percentile_rank: Optional[float] = None
    comparison_result: str  # above_average, below_average, excellent, needs_improvement

class BenchmarkAnalysis(BaseModel):
    """基准分析"""
    project_id: Optional[int] = None
    benchmarks: List[BenchmarkData]
    overall_score: float
    strengths: List[str] = Field(default_factory=list)
    improvement_areas: List[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

class PredictionModel(BaseModel):
    """预测模型"""
    model_name: str
    model_type: str  # linear_regression, arima, prophet, etc.
    accuracy_score: float
    confidence_interval: Dict[str, float]
    prediction_horizon: int  # days
    last_trained: datetime

class PredictionResult(BaseModel):
    """预测结果"""
    metric_name: str
    model: PredictionModel
    predictions: List[TrendData]
    confidence_bands: Optional[Dict[str, List[float]]] = None
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

class ReportInsight(BaseModel):
    """报告洞察"""
    insight_type: str  # trend, anomaly, comparison, prediction
    title: str
    description: str
    severity: str  # info, warning, critical
    data_points: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = 1.0

class AnalyticsConfiguration(BaseModel):
    """分析配置"""
    project_id: Optional[int] = None
    enabled_metrics: List[str] = Field(default_factory=list)
    alert_thresholds: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    notification_settings: Dict[str, Any] = Field(default_factory=dict)
    refresh_intervals: Dict[str, int] = Field(default_factory=dict)  # in minutes
    retention_days: int = 90

class DataQualityReport(BaseModel):
    """数据质量报告"""
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    timeliness_score: float
    overall_score: float
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.utcnow)