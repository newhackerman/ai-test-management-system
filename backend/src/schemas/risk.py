"""
Pydantic schemas for project risk management.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class RiskCategory(str, Enum):
    SCHEDULE = "SCHEDULE"
    QUALITY = "QUALITY"
    RESOURCE = "RESOURCE"
    TECHNICAL = "TECHNICAL"
    EXTERNAL = "EXTERNAL"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MitigationStrategy(str, Enum):
    AVOID = "AVOID"
    MITIGATE = "MITIGATE"
    TRANSFER = "TRANSFER"
    ACCEPT = "ACCEPT"


class RiskStatus(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    ANALYZING = "ANALYZING"
    MITIGATING = "MITIGATING"
    MONITORING = "MONITORING"
    CLOSED = "CLOSED"


class RiskBase(BaseModel):
    risk_name: str = Field(..., min_length=1, max_length=200, description="风险名称")
    description: str = Field(..., min_length=1, description="风险描述")
    risk_category: RiskCategory = Field(..., description="风险类别")
    risk_level: RiskLevel = Field(..., description="风险等级")
    probability: Decimal = Field(..., ge=0.0, le=1.0, description="发生概率（0-1）")
    impact_score: int = Field(..., ge=1, le=10, description="影响评分（1-10）")
    mitigation_strategy: MitigationStrategy = Field(..., description="应对策略")
    mitigation_plan: Optional[str] = Field(None, description="应对计划")
    contingency_plan: Optional[str] = Field(None, description="应急预案")
    owner_id: int = Field(..., description="风险负责人ID")
    target_resolution_date: Optional[date] = Field(None, description="目标解决日期")


class CreateRiskRequest(RiskBase):
    project_id: int = Field(..., description="项目ID")

    @validator("target_resolution_date")
    def validate_target_date(cls, value):
        if value and value <= date.today():
            raise ValueError("目标解决日期必须晚于今天")
        return value


class UpdateRiskRequest(BaseModel):
    risk_name: Optional[str] = Field(None, min_length=1, max_length=200, description="风险名称")
    description: Optional[str] = Field(None, min_length=1, description="风险描述")
    risk_category: Optional[RiskCategory] = Field(None, description="风险类别")
    risk_level: Optional[RiskLevel] = Field(None, description="风险等级")
    probability: Optional[Decimal] = Field(None, ge=0.0, le=1.0, description="发生概率")
    impact_score: Optional[int] = Field(None, ge=1, le=10, description="影响评分")
    mitigation_strategy: Optional[MitigationStrategy] = Field(None, description="应对策略")
    mitigation_plan: Optional[str] = Field(None, description="应对计划")
    contingency_plan: Optional[str] = Field(None, description="应急预案")
    status: Optional[RiskStatus] = Field(None, description="风险状态")
    owner_id: Optional[int] = Field(None, description="风险负责人ID")
    target_resolution_date: Optional[date] = Field(None, description="目标解决日期")
    actual_resolution_date: Optional[date] = Field(None, description="实际解决日期")


class RiskResponse(RiskBase):
    id: int = Field(..., description="风险ID")
    project_id: int = Field(..., description="项目ID")
    risk_score: Optional[Decimal] = Field(None, description="风险评分")
    status: RiskStatus = Field(..., description="风险状态")
    identified_date: date = Field(..., description="识别日期")
    actual_resolution_date: Optional[date] = Field(None, description="实际解决日期")
    created_by: int = Field(..., description="创建人ID")
    updated_by: Optional[int] = Field(None, description="更新人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class RiskListQuery(BaseModel):
    project_id: Optional[int] = Field(None, description="项目ID")
    search: Optional[str] = Field(None, description="搜索风险名称、描述或应对计划")
    risk_category: Optional[RiskCategory] = Field(None, description="风险类别")
    risk_level: Optional[RiskLevel] = Field(None, description="风险等级")
    status: Optional[RiskStatus] = Field(None, description="风险状态")
    owner_id: Optional[int] = Field(None, description="负责人ID")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="排序方向")


class RiskListResponse(BaseModel):
    risks: List[RiskResponse] = Field(..., description="风险列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")


class RiskAnalysisRequest(BaseModel):
    project_id: int = Field(..., description="项目ID")
    analysis_type: str = Field(..., pattern="^(current|trend|prediction)$", description="分析类型")
    time_range: Optional[int] = Field(30, ge=1, le=365, description="时间范围（天）")


class RiskMetrics(BaseModel):
    total_risks: int = Field(..., description="风险总数")
    open_risks: int = Field(..., description="未关闭风险数")
    critical_risks: int = Field(..., description="严重风险数")
    high_risks: int = Field(..., description="高风险数")
    medium_risks: int = Field(..., description="中风险数")
    low_risks: int = Field(..., description="低风险数")
    average_risk_score: Decimal = Field(..., description="平均风险评分")
    risk_trend: str = Field(..., description="风险趋势")


class RiskCategoryAnalysis(BaseModel):
    category: RiskCategory = Field(..., description="风险类别")
    count: int = Field(..., description="数量")
    percentage: Decimal = Field(..., description="占比")
    average_score: Decimal = Field(..., description="平均评分")


class RiskAnalysisResponse(BaseModel):
    project_id: int = Field(..., description="项目ID")
    analysis_date: datetime = Field(..., description="分析时间")
    metrics: RiskMetrics = Field(..., description="风险指标")
    category_analysis: List[RiskCategoryAnalysis] = Field(..., description="类别分析")
    top_risks: List[RiskResponse] = Field(..., description="重点风险")
    recommendations: List[str] = Field(..., description="建议措施")


class RiskAlert(BaseModel):
    risk_id: int = Field(..., description="风险ID")
    alert_type: str = Field(..., description="预警类型")
    severity: str = Field(..., description="严重程度")
    message: str = Field(..., description="预警消息")
    recommendation: Optional[str] = Field(None, description="建议措施")
    created_at: datetime = Field(..., description="预警时间")


class RiskMonitoringConfig(BaseModel):
    project_id: int = Field(..., description="项目ID")
    enable_auto_detection: bool = Field(True, description="启用自动识别")
    detection_interval: int = Field(24, ge=1, le=168, description="识别间隔（小时）")
    alert_thresholds: Dict[str, Any] = Field(..., description="预警阈值配置")
    notification_settings: Dict[str, Any] = Field(..., description="通知设置")


class AutoRiskDetectionResult(BaseModel):
    project_id: int = Field(..., description="项目ID")
    detection_time: datetime = Field(..., description="识别时间")
    detected_risks: List[Dict[str, Any]] = Field(..., description="识别到的风险")
    risk_indicators: Dict[str, Any] = Field(..., description="风险指标")
    recommendations: List[str] = Field(..., description="建议措施")


class RiskTrendData(BaseModel):
    trend_date: date = Field(..., description="日期")
    total_risks: int = Field(..., description="总风险数")
    new_risks: int = Field(..., description="新增风险数")
    closed_risks: int = Field(..., description="关闭风险数")
    average_score: Decimal = Field(..., description="平均评分")
    critical_count: int = Field(..., description="严重风险数")


class RiskTrendResponse(BaseModel):
    project_id: int = Field(..., description="项目ID")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    trend_data: List[RiskTrendData] = Field(..., description="趋势数据")
    summary: Dict[str, Any] = Field(..., description="趋势总结")


class RiskReportRequest(BaseModel):
    project_id: int = Field(..., description="项目ID")
    report_type: str = Field(..., pattern="^(summary|detailed|trend)$", description="报告类型")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    include_charts: bool = Field(True, description="包含图表")
    format: str = Field("pdf", pattern="^(pdf|excel|json)$", description="报告格式")


class RiskReportResponse(BaseModel):
    report_id: str = Field(..., description="报告ID")
    project_id: int = Field(..., description="项目ID")
    report_type: str = Field(..., description="报告类型")
    generated_at: datetime = Field(..., description="生成时间")
    file_url: Optional[str] = Field(None, description="文件下载地址")
    report_data: Optional[Dict[str, Any]] = Field(None, description="报告数据")
