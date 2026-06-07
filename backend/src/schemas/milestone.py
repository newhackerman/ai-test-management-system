"""
里程碑管理模块的Pydantic模式定义

本模块定义了里程碑管理相关的请求和响应模式，包括：
- 里程碑创建、更新、查询的请求模式
- 里程碑相关的响应模式
- 里程碑依赖和影响分析模式
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator


class MilestoneType(str, Enum):
    """里程碑类型枚举"""
    REQUIREMENT = "REQUIREMENT"
    DESIGN = "DESIGN"
    EXECUTION = "EXECUTION"
    DELIVERY = "DELIVERY"


class MilestoneStatus(str, Enum):
    """里程碑状态枚举"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class DeliverableStatus(str, Enum):
    """交付物状态枚举"""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REVIEWED = "REVIEWED"
    APPROVED = "APPROVED"


# 交付物模式
class Deliverable(BaseModel):
    """交付物模式"""
    id: Optional[str] = Field(None, description="交付物ID")
    name: str = Field(..., description="交付物名称")
    description: Optional[str] = Field(None, description="交付物描述")
    type: str = Field(..., description="交付物类型")
    status: DeliverableStatus = Field(DeliverableStatus.NOT_STARTED, description="交付物状态")
    owner_id: Optional[int] = Field(None, description="负责人ID")
    due_date: Optional[date] = Field(None, description="截止日期")
    completion_date: Optional[date] = Field(None, description="完成日期")
    file_path: Optional[str] = Field(None, description="文件路径")
    quality_score: Optional[Decimal] = Field(None, ge=0, le=100, description="质量评分")
    review_comments: Optional[str] = Field(None, description="评审意见")


# 里程碑依赖模式
class MilestoneDependency(BaseModel):
    """里程碑依赖模式"""
    milestone_id: int = Field(..., description="依赖的里程碑ID")
    dependency_type: str = Field("FINISH_TO_START", description="依赖类型")
    lag_days: int = Field(0, description="滞后天数")
    is_critical: bool = Field(False, description="是否关键依赖")


# 请求模式
class CreateMilestoneRequest(BaseModel):
    """创建里程碑请求模式"""
    milestone_name: str = Field(..., min_length=1, max_length=200, description="里程碑名称")
    description: Optional[str] = Field(None, description="里程碑描述")
    milestone_type: MilestoneType = Field(..., description="里程碑类型")
    planned_date: date = Field(..., description="计划日期")
    owner_id: int = Field(..., description="负责人ID")
    
    # 交付物和验收标准
    deliverables: List[Deliverable] = Field(default_factory=list, description="交付物清单")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    
    # 依赖关系
    dependencies: List[MilestoneDependency] = Field(default_factory=list, description="依赖里程碑")
    
    # 元数据
    tags: Optional[List[str]] = Field(None, description="标签")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")
    
    @validator('planned_date')
    def validate_planned_date(cls, v):
        """验证计划日期不能是过去"""
        if v < date.today():
            raise ValueError('计划日期不能是过去的日期')
        return v
    
    @validator('milestone_name')
    def validate_milestone_name(cls, v):
        """验证里程碑名称格式"""
        if not v or not v.strip():
            raise ValueError('里程碑名称不能为空')
        return v.strip()


class UpdateMilestoneRequest(BaseModel):
    """更新里程碑请求模式"""
    milestone_name: Optional[str] = Field(None, min_length=1, max_length=200, description="里程碑名称")
    description: Optional[str] = Field(None, description="里程碑描述")
    milestone_type: Optional[MilestoneType] = Field(None, description="里程碑类型")
    status: Optional[MilestoneStatus] = Field(None, description="里程碑状态")
    planned_date: Optional[date] = Field(None, description="计划日期")
    actual_date: Optional[date] = Field(None, description="实际日期")
    owner_id: Optional[int] = Field(None, description="负责人ID")
    
    # 交付物和验收标准
    deliverables: Optional[List[Deliverable]] = Field(None, description="交付物清单")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    
    # 依赖关系
    dependencies: Optional[List[MilestoneDependency]] = Field(None, description="依赖里程碑")
    
    # 元数据
    tags: Optional[List[str]] = Field(None, description="标签")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")
    
    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values):
        """验证日期逻辑"""
        planned_date = values.get('planned_date')
        actual_date = values.get('actual_date')
        
        if actual_date and planned_date and actual_date < planned_date:
            # 允许实际日期早于计划日期（提前完成）
            pass
        
        return values


class MilestoneQueryParams(BaseModel):
    """里程碑查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")
    status: Optional[List[MilestoneStatus]] = Field(None, description="状态过滤")
    milestone_type: Optional[List[MilestoneType]] = Field(None, description="类型过滤")
    owner_id: Optional[int] = Field(None, description="负责人过滤")
    search: Optional[str] = Field(None, description="搜索关键词")
    date_from: Optional[date] = Field(None, description="日期范围-起始")
    date_to: Optional[date] = Field(None, description="日期范围-结束")
    overdue_only: bool = Field(False, description="仅显示逾期里程碑")
    upcoming_days: Optional[int] = Field(None, ge=1, le=365, description="即将到期天数")
    sort_by: Optional[str] = Field("planned_date", description="排序字段")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="排序方向")


# 响应模式
class MilestoneResponse(BaseModel):
    """里程碑响应模式"""
    id: int
    project_id: int
    milestone_name: str
    description: Optional[str]
    milestone_type: MilestoneType
    status: MilestoneStatus
    planned_date: date
    actual_date: Optional[date]
    owner_id: int
    
    # 交付物和验收标准
    deliverables: List[Deliverable]
    acceptance_criteria: Optional[str]
    
    # 依赖关系
    dependencies: List[MilestoneDependency]
    
    # 进度信息
    completion_percentage: Decimal = Field(default=Decimal('0'), description="完成百分比")
    days_overdue: Optional[int] = Field(None, description="逾期天数")
    days_remaining: Optional[int] = Field(None, description="剩余天数")
    
    # 元数据
    tags: Optional[List[str]]
    custom_fields: Optional[Dict[str, Any]]
    
    # 审计字段
    created_by: int
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MilestoneListResponse(BaseModel):
    """里程碑列表响应模式"""
    milestones: List[MilestoneResponse]
    total: int
    page: int
    size: int
    total_pages: int


class MilestoneSummaryResponse(BaseModel):
    """里程碑摘要响应模式"""
    id: int
    milestone_name: str
    milestone_type: MilestoneType
    status: MilestoneStatus
    planned_date: date
    actual_date: Optional[date]
    owner_id: int
    completion_percentage: Decimal
    days_overdue: Optional[int]
    days_remaining: Optional[int]
    created_at: datetime
    updated_at: datetime


class CreateMilestoneResponse(BaseModel):
    """创建里程碑响应模式"""
    success: bool
    message: str
    milestone: MilestoneResponse


class UpdateMilestoneResponse(BaseModel):
    """更新里程碑响应模式"""
    success: bool
    message: str
    milestone: MilestoneResponse


class DeleteMilestoneResponse(BaseModel):
    """删除里程碑响应模式"""
    success: bool
    message: str
    milestone_id: int
    deleted_at: datetime


# 里程碑依赖分析模式
class MilestoneDependencyAnalysis(BaseModel):
    """里程碑依赖分析"""
    milestone_id: int
    milestone_name: str
    
    # 依赖关系
    dependencies: List[MilestoneResponse] = Field(description="依赖的里程碑")
    dependents: List[MilestoneResponse] = Field(description="依赖此里程碑的其他里程碑")
    
    # 关键路径分析
    is_on_critical_path: bool = Field(description="是否在关键路径上")
    critical_path_position: Optional[int] = Field(None, description="在关键路径中的位置")
    
    # 影响分析
    delay_impact: Dict[str, Any] = Field(description="延期影响分析")
    risk_level: str = Field(description="风险等级")
    
    analyzed_at: datetime = Field(description="分析时间")


class MilestoneImpactAnalysis(BaseModel):
    """里程碑影响分析"""
    milestone_id: int
    milestone_name: str
    
    # 延期影响
    affected_milestones: List[MilestoneSummaryResponse] = Field(description="受影响的里程碑")
    affected_tasks: List[Dict[str, Any]] = Field(description="受影响的任务")
    
    # 时间影响
    total_delay_days: int = Field(description="总延期天数")
    project_delay_days: int = Field(description="项目延期天数")
    
    # 成本影响
    estimated_cost_impact: Optional[Decimal] = Field(None, description="预估成本影响")
    
    # 风险评估
    risk_score: Decimal = Field(ge=0, le=100, description="风险评分")
    mitigation_suggestions: List[str] = Field(description="缓解建议")
    
    analyzed_at: datetime = Field(description="分析时间")


# 里程碑统计模式
class MilestoneStatistics(BaseModel):
    """里程碑统计信息"""
    project_id: int
    total_milestones: int
    completed_milestones: int
    overdue_milestones: int
    upcoming_milestones: int
    cancelled_milestones: int
    
    # 按类型统计
    milestones_by_type: Dict[str, int]
    
    # 按状态统计
    milestones_by_status: Dict[str, int]
    
    # 完成率统计
    completion_rate: Decimal = Field(ge=0, le=1, description="完成率")
    on_time_completion_rate: Decimal = Field(ge=0, le=1, description="按时完成率")
    
    # 平均指标
    average_completion_days: Optional[Decimal] = Field(None, description="平均完成天数")
    average_delay_days: Optional[Decimal] = Field(None, description="平均延期天数")
    
    calculated_at: datetime = Field(description="计算时间")


# 里程碑时间轴模式
class MilestoneTimelineItem(BaseModel):
    """里程碑时间轴项目"""
    milestone_id: int
    milestone_name: str
    milestone_type: MilestoneType
    status: MilestoneStatus
    planned_date: date
    actual_date: Optional[date]
    completion_percentage: Decimal
    is_critical: bool = Field(description="是否关键里程碑")


class MilestoneTimeline(BaseModel):
    """里程碑时间轴"""
    project_id: int
    timeline_items: List[MilestoneTimelineItem]
    start_date: date
    end_date: date
    critical_path: List[int] = Field(description="关键路径里程碑ID列表")
    generated_at: datetime = Field(description="生成时间")


# 里程碑提醒模式
class MilestoneReminder(BaseModel):
    """里程碑提醒"""
    milestone_id: int
    milestone_name: str
    reminder_type: str = Field(description="提醒类型")
    reminder_date: date = Field(description="提醒日期")
    message: str = Field(description="提醒消息")
    recipients: List[int] = Field(description="接收人ID列表")
    is_sent: bool = Field(False, description="是否已发送")
    sent_at: Optional[datetime] = Field(None, description="发送时间")


class MilestoneReminderList(BaseModel):
    """里程碑提醒列表"""
    reminders: List[MilestoneReminder]
    total: int
    pending_count: int
    sent_count: int