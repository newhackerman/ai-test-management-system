"""
需求管理相关的Pydantic模型

本模块定义了需求管理相关的请求和响应模型，包括：
- 需求创建、更新、查询
- 需求状态管理
- 需求搜索和筛选
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

from .base import BaseResponse, PaginatedResponse


class RequirementTypeEnum(str, Enum):
    """需求类型枚举"""
    FUNCTIONAL = "FUNCTIONAL"
    NON_FUNCTIONAL = "NON_FUNCTIONAL"
    CONSTRAINT = "CONSTRAINT"
    INTERFACE = "INTERFACE"


class RequirementStatusEnum(str, Enum):
    """需求状态枚举"""
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEWING = "REVIEWING"
    NEEDS_REVISION = "NEEDS_REVISION"
    APPROVED = "APPROVED"
    IN_DEVELOPMENT = "IN_DEVELOPMENT"
    PAUSED = "PAUSED"
    TESTING = "TESTING"
    TEST_FAILED = "TEST_FAILED"
    COMPLETED = "COMPLETED"
    DEPLOYED = "DEPLOYED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PriorityEnum(str, Enum):
    """优先级枚举"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    OPTIONAL = "OPTIONAL"


class BusinessValueEnum(str, Enum):
    """业务价值枚举"""
    CORE = "CORE"
    IMPORTANT = "IMPORTANT"
    NORMAL = "NORMAL"
    OPTIONAL = "OPTIONAL"


class ComplexityEnum(str, Enum):
    """复杂度枚举"""
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"
    VERY_COMPLEX = "VERY_COMPLEX"


# 请求模式

class RequirementCreate(BaseModel):
    """创建需求请求"""
    project_id: int = Field(..., description="所属项目ID")
    parent_id: Optional[int] = Field(None, description="父需求ID")
    title: str = Field(..., min_length=1, max_length=200, description="需求标题")
    description: Optional[str] = Field(None, description="需求描述")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    requirement_type: RequirementTypeEnum = Field(..., description="需求类型")
    category: Optional[str] = Field(None, max_length=100, description="需求分类")
    priority: PriorityEnum = Field(default=PriorityEnum.MEDIUM, description="优先级")
    business_value: BusinessValueEnum = Field(default=BusinessValueEnum.NORMAL, description="业务价值")
    complexity: Optional[ComplexityEnum] = Field(None, description="技术复杂度")
    estimated_effort: Optional[Decimal] = Field(None, ge=0, description="预估工作量(人天)")
    assignee_id: Optional[int] = Field(None, description="负责人ID")
    reviewer_id: Optional[int] = Field(None, description="评审人ID")
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划完成日期")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict, description="自定义字段")
    attachments: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="附件信息")

    @validator('planned_end_date')
    def validate_planned_dates(cls, v, values):
        if v and 'planned_start_date' in values and values['planned_start_date']:
            if v < values['planned_start_date']:
                raise ValueError("计划完成日期不能早于计划开始日期")
        return v


class RequirementUpdate(BaseModel):
    """更新需求请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="需求标题")
    description: Optional[str] = Field(None, description="需求描述")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")
    requirement_type: Optional[RequirementTypeEnum] = Field(None, description="需求类型")
    category: Optional[str] = Field(None, max_length=100, description="需求分类")
    priority: Optional[PriorityEnum] = Field(None, description="优先级")
    business_value: Optional[BusinessValueEnum] = Field(None, description="业务价值")
    complexity: Optional[ComplexityEnum] = Field(None, description="技术复杂度")
    estimated_effort: Optional[Decimal] = Field(None, ge=0, description="预估工作量(人天)")
    actual_effort: Optional[Decimal] = Field(None, ge=0, description="实际工作量(人天)")
    assignee_id: Optional[int] = Field(None, description="负责人ID")
    reviewer_id: Optional[int] = Field(None, description="评审人ID")
    planned_start_date: Optional[date] = Field(None, description="计划开始日期")
    planned_end_date: Optional[date] = Field(None, description="计划完成日期")
    actual_start_date: Optional[date] = Field(None, description="实际开始日期")
    actual_end_date: Optional[date] = Field(None, description="实际完成日期")
    tags: Optional[List[str]] = Field(None, description="标签")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")


class RequirementStatusUpdate(BaseModel):
    """需求状态更新请求"""
    status: RequirementStatusEnum = Field(..., description="新状态")
    reason: Optional[str] = Field(None, description="变更原因")


class RequirementBatchStatusUpdate(BaseModel):
    """批量状态更新请求"""
    requirement_ids: List[int] = Field(..., min_items=1, description="需求ID列表")
    status: RequirementStatusEnum = Field(..., description="新状态")
    reason: Optional[str] = Field(None, description="变更原因")


# 响应模式

class RequirementResponse(BaseModel):
    """需求响应"""
    id: int
    requirement_code: str
    project_id: int
    parent_id: Optional[int]
    title: str
    description: Optional[str]
    acceptance_criteria: Optional[str]
    requirement_type: RequirementTypeEnum
    category: Optional[str]
    priority: PriorityEnum
    business_value: BusinessValueEnum
    status: RequirementStatusEnum
    complexity: Optional[ComplexityEnum]
    estimated_effort: Optional[Decimal]
    actual_effort: Optional[Decimal]
    creator_id: int
    assignee_id: Optional[int]
    reviewer_id: Optional[int]
    planned_start_date: Optional[date]
    planned_end_date: Optional[date]
    actual_start_date: Optional[date]
    actual_end_date: Optional[date]
    quality_score: Optional[Decimal]
    completeness_score: Optional[Decimal]
    tags: Optional[List[str]]
    custom_fields: Optional[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]]
    updated_by: Optional[int]
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequirementListResponse(PaginatedResponse):
    """需求列表响应"""
    items: List[RequirementResponse]


class RequirementStatusHistoryResponse(BaseModel):
    """需求状态历史响应"""
    id: int
    requirement_id: int
    old_status: Optional[RequirementStatusEnum]
    new_status: RequirementStatusEnum
    change_reason: Optional[str]
    change_description: Optional[str]
    changed_by: int
    changed_at: datetime

    class Config:
        from_attributes = True


class RequirementWithHistoryResponse(BaseModel):
    """带状态历史的需求响应"""
    requirement: RequirementResponse
    status_history: List[RequirementStatusHistoryResponse]


class RequirementStatisticsResponse(BaseModel):
    """需求统计响应"""
    total_requirements: int
    status_distribution: Dict[str, int]
    priority_distribution: Dict[str, int]
    type_distribution: Dict[str, int]
    complexity_distribution: Dict[str, int]
    business_value_distribution: Dict[str, int]
    average_quality_score: Optional[float]
    average_completeness_score: Optional[float]
    generated_at: datetime


class RequirementQualityAnalysisResponse(BaseModel):
    """需求质量分析响应"""
    requirement_id: int
    quality_score: float
    completeness_score: float
    complexity_estimate: ComplexityEnum
    effort_estimate: float
    issues: List[str]
    suggestions: List[str]
    analyzed_at: datetime


# 查询参数模式

class RequirementSearchParams(BaseModel):
    """需求搜索参数"""
    keyword: Optional[str] = Field(None, description="关键词搜索")
    project_id: Optional[int] = Field(None, description="项目ID")
    parent_id: Optional[int] = Field(None, description="父需求ID")
    requirement_type: Optional[RequirementTypeEnum] = Field(None, description="需求类型")
    status: Optional[List[RequirementStatusEnum]] = Field(None, description="状态过滤")
    priority: Optional[List[PriorityEnum]] = Field(None, description="优先级过滤")
    business_value: Optional[List[BusinessValueEnum]] = Field(None, description="业务价值过滤")
    complexity: Optional[List[ComplexityEnum]] = Field(None, description="复杂度过滤")
    assignee_id: Optional[int] = Field(None, description="负责人ID")
    creator_id: Optional[int] = Field(None, description="创建人ID")
    reviewer_id: Optional[int] = Field(None, description="评审人ID")
    category: Optional[str] = Field(None, description="分类")
    tags: Optional[List[str]] = Field(None, description="标签过滤")
    created_from: Optional[date] = Field(None, description="创建开始日期")
    created_to: Optional[date] = Field(None, description="创建结束日期")
    planned_start_from: Optional[date] = Field(None, description="计划开始日期范围开始")
    planned_start_to: Optional[date] = Field(None, description="计划开始日期范围结束")
    planned_end_from: Optional[date] = Field(None, description="计划完成日期范围开始")
    planned_end_to: Optional[date] = Field(None, description="计划完成日期范围结束")
    quality_score_min: Optional[float] = Field(None, ge=0, le=10, description="最低质量评分")
    quality_score_max: Optional[float] = Field(None, ge=0, le=10, description="最高质量评分")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(20, ge=1, le=100, description="限制数量")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="排序方向")


# 批量操作模式

class RequirementBatchDeleteRequest(BaseModel):
    """批量删除需求请求"""
    requirement_ids: List[int] = Field(..., min_items=1, description="需求ID列表")
    force: bool = Field(False, description="是否强制删除")


class RequirementBatchOperationResponse(BaseModel):
    """批量操作响应"""
    total_count: int
    success_count: int
    failed_count: int
    success_ids: List[int]
    failed_items: List[Dict[str, Any]]
    operation_type: str
    executed_at: datetime


# 导入导出模式

class RequirementImportRequest(BaseModel):
    """需求导入请求"""
    project_id: int = Field(..., description="目标项目ID")
    file_format: str = Field("excel", pattern="^(excel|csv|json)$", description="文件格式")
    overwrite_existing: bool = Field(False, description="是否覆盖已存在的需求")
    validate_only: bool = Field(False, description="是否仅验证不导入")


class RequirementExportRequest(BaseModel):
    """需求导出请求"""
    requirement_ids: Optional[List[int]] = Field(None, description="需求ID列表")
    project_id: Optional[int] = Field(None, description="项目ID")
    search_params: Optional[RequirementSearchParams] = Field(None, description="搜索条件")
    export_format: str = Field("excel", pattern="^(excel|csv|json|pdf)$", description="导出格式")
    include_history: bool = Field(False, description="是否包含状态历史")
    include_dependencies: bool = Field(False, description="是否包含依赖关系")
    template_name: Optional[str] = Field(None, description="导出模板名称")


class RequirementImportResponse(BaseModel):
    """需求导入响应"""
    total_rows: int
    imported_count: int
    skipped_count: int
    error_count: int
    imported_requirements: List[RequirementResponse]
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    import_summary: Dict[str, Any]
    imported_at: datetime


# 依赖关系模式

class RequirementDependencyCreate(BaseModel):
    """创建需求依赖关系请求"""
    source_requirement_id: int = Field(..., description="源需求ID")
    target_requirement_id: int = Field(..., description="目标需求ID")
    dependency_type: str = Field(..., description="依赖类型")
    description: Optional[str] = Field(None, description="依赖描述")

    @validator('target_requirement_id')
    def validate_different_requirements(cls, v, values):
        if 'source_requirement_id' in values and v == values['source_requirement_id']:
            raise ValueError("源需求和目标需求不能相同")
        return v


class RequirementDependencyResponse(BaseModel):
    """需求依赖关系响应"""
    id: int
    source_requirement_id: int
    target_requirement_id: int
    dependency_type: str
    description: Optional[str]
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class RequirementWithDependenciesResponse(BaseModel):
    """带依赖关系的需求响应"""
    requirement: RequirementResponse
    dependencies: List[RequirementDependencyResponse]
    dependents: List[RequirementDependencyResponse]


# 模板模式

class RequirementTemplateCreate(BaseModel):
    """创建需求模板请求"""
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    requirement_type: RequirementTypeEnum = Field(..., description="需求类型")
    template_content: Dict[str, Any] = Field(..., description="模板内容")
    is_public: bool = Field(False, description="是否公开模板")
    category: Optional[str] = Field(None, description="模板分类")


class RequirementTemplateResponse(BaseModel):
    """需求模板响应"""
    id: int
    name: str
    description: Optional[str]
    requirement_type: RequirementTypeEnum
    template_content: Dict[str, Any]
    is_public: bool
    category: Optional[str]
    creator_id: int
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True