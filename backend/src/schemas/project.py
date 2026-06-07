"""
项目管理模块的Pydantic模式定义

本模块定义了项目管理相关的请求和响应模式，包括：
- 项目创建、更新、查询的请求模式
- 项目相关的响应模式
- 数据验证和序列化
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator
from pydantic.types import constr, condecimal


class ProjectType(str, Enum):
    """项目类型枚举"""
    BUSINESS_SYSTEM = "BUSINESS_SYSTEM"
    MOBILE_APP = "MOBILE_APP"
    API_SERVICE = "API_SERVICE"
    DATA_AI = "DATA_AI"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    INTERNAL_TOOL = "INTERNAL_TOOL"

    # 历史兼容：旧版本把测试类型误用为项目类型
    FUNCTIONAL = "FUNCTIONAL"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    AUTOMATION = "AUTOMATION"
    INTEGRATION = "INTEGRATION"


class ProjectPriority(str, Enum):
    """项目优先级枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ProjectStatus(str, Enum):
    """项目状态枚举"""
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProjectMemberRole(str, Enum):
    """项目成员角色枚举"""
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    REQUIREMENT_MANAGER = "REQUIREMENT_MANAGER"
    DESIGNER = "DESIGNER"
    ARCHITECT = "ARCHITECT"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    DEVOPS = "DEVOPS"
    THIRD_PARTY = "THIRD_PARTY"


# 请求模式
class CreateProjectRequest(BaseModel):
    """创建项目请求模式"""
    project_name: constr(min_length=1, max_length=200) = Field(..., description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    project_type: ProjectType = Field(..., description="项目类型")
    priority: ProjectPriority = Field(ProjectPriority.MEDIUM, description="项目优先级")
    
    # 时间管理
    planned_start_date: date = Field(..., description="计划开始日期")
    planned_end_date: date = Field(..., description="计划结束日期")
    
    # 人员管理
    project_manager_id: int = Field(..., description="项目经理ID")
    test_manager_id: Optional[int] = Field(None, description="测试经理ID")
    client_contact: Optional[constr(max_length=200)] = Field(None, description="客户联系人")
    
    # 预算管理
    budget: Optional[condecimal(max_digits=15, decimal_places=2)] = Field(None, description="项目预算")
    
    # 元数据
    tags: Optional[List[str]] = Field(None, description="项目标签")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")
    
    @validator('planned_end_date')
    def validate_end_date(cls, v, values):
        """验证结束日期必须晚于开始日期"""
        if 'planned_start_date' in values and v <= values['planned_start_date']:
            raise ValueError('计划结束日期必须晚于计划开始日期')
        return v
    
    @validator('project_name')
    def validate_project_name(cls, v):
        """验证项目名称格式"""
        if not v or not v.strip():
            raise ValueError('项目名称不能为空')
        return v.strip()


class UpdateProjectRequest(BaseModel):
    """更新项目请求模式"""
    project_name: Optional[constr(min_length=1, max_length=200)] = Field(None, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    project_type: Optional[ProjectType] = Field(None, description="项目类型")
    priority: Optional[ProjectPriority] = Field(None, description="项目优先级")
    status: Optional[ProjectStatus] = Field(None, description="项目状态")
    
    # 时间管理
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划结束日期")
    actual_start_date: Optional[date] = Field(None, description="实际开始日期")
    actual_end_date: Optional[date] = Field(None, description="实际结束日期")
    
    # 人员管理
    project_manager_id: Optional[int] = Field(None, description="项目经理ID")
    test_manager_id: Optional[int] = Field(None, description="测试经理ID")
    client_contact: Optional[constr(max_length=200)] = Field(None, description="客户联系人")
    
    # 预算管理
    budget: Optional[condecimal(max_digits=15, decimal_places=2)] = Field(None, description="项目预算")
    
    # 健康度和风险
    health_score: Optional[int] = Field(None, ge=0, le=100, description="项目健康度")
    risk_level: Optional[RiskLevel] = Field(None, description="风险等级")
    
    # 元数据
    tags: Optional[List[str]] = Field(None, description="项目标签")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")
    
    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values):
        """验证日期逻辑"""
        planned_start = values.get('planned_start_date')
        planned_end = values.get('planned_end_date')
        actual_start = values.get('actual_start_date')
        actual_end = values.get('actual_end_date')
        
        # 计划日期验证
        if planned_start and planned_end and planned_end <= planned_start:
            raise ValueError('计划结束日期必须晚于计划开始日期')
        
        # 实际日期验证
        if actual_start and actual_end and actual_end < actual_start:
            raise ValueError('实际结束日期不能早于实际开始日期')
        
        return values


class ProjectQueryParams(BaseModel):
    """项目查询参数"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")
    status: Optional[List[ProjectStatus]] = Field(None, description="状态过滤")
    project_type: Optional[List[ProjectType]] = Field(None, description="类型过滤")
    priority: Optional[List[ProjectPriority]] = Field(None, description="优先级过滤")
    project_manager_id: Optional[int] = Field(None, description="项目经理过滤")
    search: Optional[str] = Field(None, description="搜索关键词")
    start_date_from: Optional[date] = Field(None, description="开始日期范围-起始")
    start_date_to: Optional[date] = Field(None, description="开始日期范围-结束")
    end_date_from: Optional[date] = Field(None, description="结束日期范围-起始")
    end_date_to: Optional[date] = Field(None, description="结束日期范围-结束")
    sort_by: Optional[str] = Field("updated_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="排序方向")


# 响应模式
class ProjectResponse(BaseModel):
    """项目响应模式"""
    id: int
    project_code: str
    project_name: str
    description: Optional[str]
    project_type: ProjectType
    priority: ProjectPriority
    status: ProjectStatus
    health_score: int
    risk_level: RiskLevel
    
    # 时间管理
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]
    
    # 人员管理
    project_manager_id: int
    test_manager_id: Optional[int]
    client_contact: Optional[str]
    
    # 预算管理
    budget: Optional[Decimal]
    actual_cost: Decimal
    
    # 进度管理
    progress_percentage: Decimal
    task_count: int
    completed_task_count: int
    
    # 质量管理
    test_case_count: int
    passed_test_count: int
    defect_count: int
    
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


class ProjectListResponse(BaseModel):
    """项目列表响应模式"""
    projects: List[ProjectResponse]
    total: int
    page: int
    size: int
    total_pages: int


class ProjectSummaryResponse(BaseModel):
    """项目摘要响应模式"""
    id: int
    project_code: str
    project_name: str
    project_type: ProjectType
    status: ProjectStatus
    priority: ProjectPriority
    progress_percentage: Decimal
    health_score: int
    risk_level: RiskLevel
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    project_manager_id: int
    task_count: int
    completed_task_count: int
    created_at: datetime
    updated_at: datetime


class CreateProjectResponse(BaseModel):
    """创建项目响应模式"""
    success: bool
    message: str
    project: ProjectResponse


class UpdateProjectResponse(BaseModel):
    """更新项目响应模式"""
    success: bool
    message: str
    project: ProjectResponse


class DeleteProjectResponse(BaseModel):
    """删除项目响应模式"""
    success: bool
    message: str
    project_id: int
    deleted_at: datetime


# 项目成员相关模式
class ProjectMemberResponse(BaseModel):
    """项目成员响应模式"""
    id: int
    project_id: int
    user_id: int
    role_in_project: ProjectMemberRole
    allocation_percentage: Decimal
    hourly_rate: Optional[Decimal]
    join_date: date
    leave_date: Optional[date]
    status: str
    skills: Optional[List[str]]
    responsibilities: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# 项目统计相关模式
class ProjectStatistics(BaseModel):
    """项目统计信息"""
    total_projects: int
    active_projects: int
    completed_projects: int
    overdue_projects: int
    projects_by_status: Dict[str, int]
    projects_by_type: Dict[str, int]
    projects_by_priority: Dict[str, int]
    average_progress: float
    average_health_score: float


class ProjectHealthMetrics(BaseModel):
    """项目健康度指标"""
    project_id: int
    health_score: int
    risk_level: RiskLevel
    progress_deviation: float
    schedule_deviation: float
    budget_deviation: float
    quality_score: float
    team_satisfaction: Optional[float]
    calculated_at: datetime
