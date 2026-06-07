"""
进度跟踪模块的Pydantic模式定义

本模块定义了进度跟踪相关的请求和响应模式，包括：
- 多维度进度计算响应模式
- 进度预警和通知模式
- 进度趋势分析模式
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, validator


class ProgressDimension(str, Enum):
    """进度维度枚举"""
    TIME = "TIME"
    TASK = "TASK"
    QUALITY = "QUALITY"
    MILESTONE = "MILESTONE"


class AlertSeverity(str, Enum):
    """预警严重程度枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertType(str, Enum):
    """预警类型枚举"""
    TIME_DEVIATION = "TIME_DEVIATION"
    QUALITY_RISK = "QUALITY_RISK"
    MILESTONE_OVERDUE = "MILESTONE_OVERDUE"
    TASK_BLOCKED = "TASK_BLOCKED"
    RESOURCE_OVERLOAD = "RESOURCE_OVERLOAD"
    BUDGET_OVERRUN = "BUDGET_OVERRUN"


# 进度计算响应模式
class TimeProgressResponse(BaseModel):
    """时间进度响应模式"""
    project_id: int
    progress_rate: Decimal = Field(..., ge=0, le=1, description="时间进度比率(0-1)")
    elapsed_days: int = Field(..., ge=0, description="已用天数")
    total_days: int = Field(..., ge=1, description="总天数")
    remaining_days: int = Field(..., description="剩余天数")
    deviation: Decimal = Field(..., description="进度偏差(-1到1)")
    is_on_schedule: bool = Field(..., description="是否按计划进行")
    calculated_at: datetime = Field(..., description="计算时间")


class TaskProgressResponse(BaseModel):
    """任务进度响应模式"""
    project_id: int
    progress_rate: Decimal = Field(..., ge=0, le=1, description="任务进度比率(0-1)")
    total_tasks: int = Field(..., ge=0, description="任务总数")
    completed_tasks: int = Field(..., ge=0, description="已完成任务数")
    in_progress_tasks: int = Field(..., ge=0, description="进行中任务数")
    blocked_tasks: int = Field(..., ge=0, description="阻塞任务数")
    weighted_progress: Decimal = Field(..., ge=0, le=1, description="加权进度")
    calculated_at: datetime = Field(..., description="计算时间")


class QualityProgressResponse(BaseModel):
    """质量进度响应模式"""
    project_id: int
    progress_rate: Decimal = Field(..., ge=0, le=1, description="质量进度比率(0-1)")
    test_coverage: Decimal = Field(..., ge=0, le=1, description="测试覆盖率")
    pass_rate: Decimal = Field(..., ge=0, le=1, description="测试通过率")
    defect_density: Decimal = Field(..., ge=0, description="缺陷密度")
    quality_score: Decimal = Field(..., ge=0, le=100, description="质量评分")
    calculated_at: datetime = Field(..., description="计算时间")


class MilestoneProgressResponse(BaseModel):
    """里程碑进度响应模式"""
    project_id: int
    progress_rate: Decimal = Field(..., ge=0, le=1, description="里程碑进度比率(0-1)")
    total_milestones: int = Field(..., ge=0, description="里程碑总数")
    completed_milestones: int = Field(..., ge=0, description="已完成里程碑数")
    overdue_milestones: int = Field(..., ge=0, description="逾期里程碑数")
    upcoming_milestones: int = Field(..., ge=0, description="即将到期里程碑数")
    calculated_at: datetime = Field(..., description="计算时间")


class ProgressResponse(BaseModel):
    """综合进度响应模式"""
    project_id: int
    overall_progress: Decimal = Field(..., ge=0, le=1, description="综合进度(0-1)")
    time_progress: TimeProgressResponse
    task_progress: TaskProgressResponse
    quality_progress: QualityProgressResponse
    milestone_progress: MilestoneProgressResponse
    
    # 权重配置
    weights: Dict[str, Decimal] = Field(..., description="各维度权重")
    
    # 健康度评估
    health_score: int = Field(..., ge=0, le=100, description="项目健康度")
    risk_level: str = Field(..., description="风险等级")
    
    calculated_at: datetime = Field(..., description="计算时间")


# 进度预警模式
class ProgressAlert(BaseModel):
    """进度预警模式"""
    id: Optional[int] = Field(None, description="预警ID")
    project_id: int = Field(..., description="项目ID")
    alert_type: AlertType = Field(..., description="预警类型")
    severity: AlertSeverity = Field(..., description="严重程度")
    title: str = Field(..., description="预警标题")
    message: str = Field(..., description="预警消息")
    recommendation: Optional[str] = Field(None, description="建议措施")
    
    # 预警数据
    current_value: Optional[Decimal] = Field(None, description="当前值")
    threshold_value: Optional[Decimal] = Field(None, description="阈值")
    deviation: Optional[Decimal] = Field(None, description="偏差")
    
    # 状态管理
    is_active: bool = Field(True, description="是否激活")
    acknowledged: bool = Field(False, description="是否已确认")
    resolved: bool = Field(False, description="是否已解决")
    
    # 时间信息
    triggered_at: datetime = Field(..., description="触发时间")
    acknowledged_at: Optional[datetime] = Field(None, description="确认时间")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")
    
    # 负责人
    assigned_to: Optional[int] = Field(None, description="指派给")


class ProgressAlertList(BaseModel):
    """进度预警列表"""
    alerts: List[ProgressAlert]
    total: int
    active_count: int
    critical_count: int
    high_count: int


# 进度趋势分析模式
class ProgressTrend(BaseModel):
    """进度趋势数据点"""
    trend_date: date = Field(..., description="日期")
    overall_progress: Decimal = Field(..., ge=0, le=1, description="综合进度")
    time_progress: Decimal = Field(..., ge=0, le=1, description="时间进度")
    task_progress: Decimal = Field(..., ge=0, le=1, description="任务进度")
    quality_progress: Decimal = Field(..., ge=0, le=1, description="质量进度")
    milestone_progress: Decimal = Field(..., ge=0, le=1, description="里程碑进度")


class ProgressTrendAnalysis(BaseModel):
    """进度趋势分析"""
    project_id: int
    trend_data: List[ProgressTrend] = Field(..., description="趋势数据")
    
    # 趋势指标
    velocity: Decimal = Field(..., description="当前速度(进度/天)")
    acceleration: Decimal = Field(..., description="加速度")
    predicted_completion_date: Optional[date] = Field(None, description="预测完成日期")
    confidence_level: Decimal = Field(..., ge=0, le=1, description="预测置信度")
    
    # 风险评估
    schedule_risk: Decimal = Field(..., ge=0, le=1, description="进度风险")
    quality_risk: Decimal = Field(..., ge=0, le=1, description="质量风险")
    
    analyzed_at: datetime = Field(..., description="分析时间")


# 进度更新请求模式
class ProgressUpdateRequest(BaseModel):
    """进度更新请求模式"""
    project_id: int = Field(..., description="项目ID")
    force_recalculate: bool = Field(False, description="是否强制重新计算")
    notify_stakeholders: bool = Field(True, description="是否通知干系人")


class ProgressUpdateResponse(BaseModel):
    """进度更新响应模式"""
    success: bool
    message: str
    progress: ProgressResponse
    alerts: List[ProgressAlert] = Field(default_factory=list, description="新产生的预警")


# 进度配置模式
class ProgressWeightsConfig(BaseModel):
    """进度权重配置"""
    time_weight: Decimal = Field(0.25, ge=0, le=1, description="时间权重")
    task_weight: Decimal = Field(0.35, ge=0, le=1, description="任务权重")
    quality_weight: Decimal = Field(0.25, ge=0, le=1, description="质量权重")
    milestone_weight: Decimal = Field(0.15, ge=0, le=1, description="里程碑权重")
    
    @validator('milestone_weight')
    def validate_weights_sum(cls, v, values):
        """验证权重总和为1"""
        total = v + values.get('time_weight', 0) + values.get('task_weight', 0) + values.get('quality_weight', 0)
        if abs(total - 1.0) > 0.001:  # 允许小的浮点误差
            raise ValueError('所有权重的总和必须等于1.0')
        return v


class ProgressThresholds(BaseModel):
    """进度阈值配置"""
    time_deviation_warning: Decimal = Field(0.10, description="时间偏差预警阈值")
    time_deviation_critical: Decimal = Field(0.20, description="时间偏差严重阈值")
    quality_score_warning: Decimal = Field(0.80, description="质量评分预警阈值")
    quality_score_critical: Decimal = Field(0.70, description="质量评分严重阈值")
    milestone_overdue_warning: int = Field(1, description="里程碑逾期预警数量")
    milestone_overdue_critical: int = Field(3, description="里程碑逾期严重数量")


# 进度报告模式
class ProgressReport(BaseModel):
    """进度报告"""
    project_id: int
    report_date: date
    progress: ProgressResponse
    alerts: List[ProgressAlert]
    trend_analysis: ProgressTrendAnalysis
    
    # 报告摘要
    summary: str = Field(..., description="进度摘要")
    key_achievements: List[str] = Field(default_factory=list, description="关键成就")
    major_risks: List[str] = Field(default_factory=list, description="主要风险")
    next_milestones: List[str] = Field(default_factory=list, description="下一步里程碑")
    
    generated_at: datetime = Field(..., description="生成时间")
    generated_by: int = Field(..., description="生成人ID")


class ProgressReportList(BaseModel):
    """进度报告列表"""
    reports: List[ProgressReport]
    total: int
    page: int
    size: int