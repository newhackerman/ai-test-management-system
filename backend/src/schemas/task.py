"""
任务管理相关的Pydantic模式定义

本模块定义了任务管理相关的请求和响应模式，包括：
- 任务创建和更新请求
- 任务查询参数
- 任务响应模式
- 任务状态和类型枚举
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator


class TaskType(str, Enum):
    """任务类型枚举"""
    REQUIREMENT_ANALYSIS = "REQUIREMENT_ANALYSIS"
    TEST_DESIGN = "TEST_DESIGN"
    TEST_EXECUTION = "TEST_EXECUTION"
    AUTOMATION_DEVELOPMENT = "AUTOMATION_DEVELOPMENT"
    PERFORMANCE_TEST = "PERFORMANCE_TEST"
    SECURITY_TEST = "SECURITY_TEST"
    ENVIRONMENT_SETUP = "ENVIRONMENT_SETUP"
    DOCUMENTATION = "DOCUMENTATION"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    TODO = "TODO"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    BLOCKED = "BLOCKED"
    PENDING_REVIEW = "PENDING_REVIEW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, Enum):
    """任务优先级枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class CreateTaskRequest(BaseModel):
    """创建任务请求模式"""
    project_id: int = Field(..., description="项目ID")
    task_name: str = Field(..., min_length=1, max_length=200, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: TaskType = Field(..., description="任务类型")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="任务优先级")
    status: TaskStatus = Field(TaskStatus.TODO, description="任务初始状态")
    
    # 人员分配
    assignee_id: Optional[int] = Field(None, description="执行人ID")
    assignee_ids: Optional[List[int]] = Field(None, description="执行人ID列表")
    reporter_id: Optional[int] = Field(None, description="报告人ID")
    reviewer_id: Optional[int] = Field(None, description="审核人ID")
    
    # 时间管理
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划结束日期")
    
    # 工时管理
    estimated_hours: Optional[Decimal] = Field(None, ge=0, description="预估工时")
    
    # 依赖关系
    parent_task_id: Optional[int] = Field(None, description="父任务ID")
    dependency_tasks: Optional[List[int]] = Field(None, description="依赖任务ID列表")
    
    # 质量管理
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    
    # 元数据
    tags: Optional[List[str]] = Field(None, description="任务标签")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")
    
    @validator('planned_end_date')
    def validate_end_date(cls, v, values):
        """验证结束日期必须晚于开始日期"""
        if v and 'planned_start_date' in values and values['planned_start_date']:
            if v <= values['planned_start_date']:
                raise ValueError('计划结束日期必须晚于计划开始日期')
        return v
    
    @validator('dependency_tasks')
    def validate_dependencies(cls, v):
        """验证依赖任务列表"""
        if v and len(v) != len(set(v)):
            raise ValueError('依赖任务列表不能包含重复项')
        return v

    @validator('assignee_ids')
    def validate_assignee_ids(cls, v):
        """验证执行人列表"""
        if v and len(v) != len(set(v)):
            raise ValueError('执行人列表不能包含重复项')
        return v


class UpdateTaskRequest(BaseModel):
    """更新任务请求模式"""
    task_name: Optional[str] = Field(None, min_length=1, max_length=200, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: Optional[TaskType] = Field(None, description="任务类型")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    
    # 人员分配
    assignee_id: Optional[int] = Field(None, description="执行人ID")
    assignee_ids: Optional[List[int]] = Field(None, description="执行人ID列表")
    reporter_id: Optional[int] = Field(None, description="报告人ID")
    reviewer_id: Optional[int] = Field(None, description="审核人ID")
    
    # 时间管理
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划结束日期")
    actual_start_date: Optional[date] = Field(None, description="实际开始日期")
    actual_end_date: Optional[date] = Field(None, description="实际结束日期")
    
    # 工时管理
    estimated_hours: Optional[Decimal] = Field(None, ge=0, description="预估工时")
    actual_hours: Optional[Decimal] = Field(None, ge=0, description="实际工时")
    remaining_hours: Optional[Decimal] = Field(None, ge=0, description="剩余工时")
    
    # 依赖关系
    parent_task_id: Optional[int] = Field(None, description="父任务ID")
    dependency_tasks: Optional[List[int]] = Field(None, description="依赖任务ID列表")
    
    # 质量管理
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    test_case_count: Optional[int] = Field(None, ge=0, description="关联测试用例数")
    defect_count: Optional[int] = Field(None, ge=0, description="发现缺陷数")
    
    # 元数据
    tags: Optional[List[str]] = Field(None, description="任务标签")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")


class TaskQueryParams(BaseModel):
    """任务查询参数模式"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")
    
    # 过滤条件
    project_id: Optional[int] = Field(None, description="项目ID过滤")
    status: Optional[List[TaskStatus]] = Field(None, description="状态过滤")
    task_type: Optional[List[TaskType]] = Field(None, description="类型过滤")
    priority: Optional[List[TaskPriority]] = Field(None, description="优先级过滤")
    assignee_id: Optional[int] = Field(None, description="执行人过滤")
    reporter_id: Optional[int] = Field(None, description="报告人过滤")
    parent_task_id: Optional[int] = Field(None, description="父任务过滤")
    
    # 日期范围过滤
    planned_start_date_from: Optional[date] = Field(None, description="计划开始日期起")
    planned_start_date_to: Optional[date] = Field(None, description="计划开始日期止")
    planned_end_date_from: Optional[date] = Field(None, description="计划结束日期起")
    planned_end_date_to: Optional[date] = Field(None, description="计划结束日期止")
    
    # 搜索
    search: Optional[str] = Field(None, description="搜索关键词")
    
    # 排序
    sort_by: str = Field("updated_at", description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向")


class TaskResponse(BaseModel):
    """任务响应模式"""
    id: int
    project_id: int
    task_code: Optional[str]
    task_name: str
    description: Optional[str]
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    
    # 人员分配
    assignee_id: Optional[int]
    assignee_ids: Optional[List[int]]
    reporter_id: Optional[int]
    reviewer_id: Optional[int]
    
    # 时间管理
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]
    
    # 工时管理
    estimated_hours: Optional[Decimal]
    actual_hours: Optional[Decimal]
    remaining_hours: Optional[Decimal]
    
    # 依赖关系
    parent_task_id: Optional[int]
    dependency_tasks: Optional[List[int]]
    
    # 质量管理
    acceptance_criteria: Optional[str]
    test_case_count: int
    defect_count: int
    
    # 元数据
    tags: Optional[List[str]]
    attachments: Optional[List[Dict[str, Any]]]
    
    # 审计字段
    created_by: int
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskSummaryResponse(BaseModel):
    """任务摘要响应模式"""
    id: int
    project_id: int
    task_code: Optional[str]
    task_name: str
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    assignee_id: Optional[int]
    assignee_ids: Optional[List[int]]
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    progress_percentage: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应模式"""
    tasks: List[TaskResponse]
    total: int
    page: int
    size: int
    total_pages: int


class CreateTaskResponse(BaseModel):
    """创建任务响应模式"""
    success: bool
    message: str
    task: TaskResponse


class UpdateTaskResponse(BaseModel):
    """更新任务响应模式"""
    success: bool
    message: str
    task: TaskResponse


class DeleteTaskResponse(BaseModel):
    """删除任务响应模式"""
    success: bool
    message: str
    task_id: int
    deleted_at: datetime


class TaskStatusUpdateRequest(BaseModel):
    """任务状态更新请求模式"""
    status: TaskStatus = Field(..., description="新状态")
    comment: Optional[str] = Field(None, description="状态变更说明")


class TaskAssignmentRequest(BaseModel):
    """任务分配请求模式"""
    assignee_id: Optional[int] = Field(None, description="执行人ID")
    assignee_ids: Optional[List[int]] = Field(None, description="执行人ID列表")
    comment: Optional[str] = Field(None, description="分配说明")

    @validator('assignee_ids')
    def validate_assignment_assignees(cls, v):
        """验证分配执行人列表"""
        if v and len(v) != len(set(v)):
            raise ValueError('执行人列表不能包含重复项')
        return v

    @root_validator(skip_on_failure=True)
    def validate_has_assignee(cls, values):
        """至少需要一个执行人"""
        if not values.get('assignee_id') and not values.get('assignee_ids'):
            raise ValueError('请至少选择一个执行人')
        return values


class TaskProgressUpdateRequest(BaseModel):
    """任务进度更新请求模式"""
    actual_hours: Optional[Decimal] = Field(None, ge=0, description="实际工时")
    remaining_hours: Optional[Decimal] = Field(None, ge=0, description="剩余工时")
    progress_notes: Optional[str] = Field(None, description="进度说明")
    issues_encountered: Optional[str] = Field(None, description="遇到的问题")


class TaskDependencyRequest(BaseModel):
    """任务依赖关系请求模式"""
    dependency_tasks: List[int] = Field(..., description="依赖任务ID列表")
    
    @validator('dependency_tasks')
    def validate_dependencies(cls, v):
        """验证依赖任务列表"""
        if len(v) != len(set(v)):
            raise ValueError('依赖任务列表不能包含重复项')
        return v


class TaskStatisticsResponse(BaseModel):
    """任务统计响应模式"""
    project_id: int
    total_tasks: int
    tasks_by_status: Dict[str, int]
    tasks_by_type: Dict[str, int]
    tasks_by_priority: Dict[str, int]
    overdue_tasks: int
    completed_on_time: int
    average_completion_time: Optional[float]
    
    class Config:
        from_attributes = True
