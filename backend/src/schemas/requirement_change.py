"""
需求变更管理相关的Pydantic模型

本模块定义了需求变更管理相关的请求和响应模型，包括：
- 变更请求创建和更新
- 变更审批流程
- 变更影响分析
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum

from .base import BaseResponse, PaginatedResponse


class ChangeTypeEnum(str, Enum):
    """变更类型枚举"""
    ADDITION = "ADDITION"
    MODIFICATION = "MODIFICATION"
    DELETION = "DELETION"
    CLARIFICATION = "CLARIFICATION"


class ChangeStatusEnum(str, Enum):
    """变更状态枚举"""
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"
    CLOSED = "CLOSED"


class ChangePriorityEnum(str, Enum):
    """变更优先级枚举"""
    EMERGENCY = "EMERGENCY"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ChangeRequestCreate(BaseModel):
    """创建变更请求"""
    requirement_id: int = Field(..., description="需求ID")
    title: str = Field(..., min_length=1, max_length=200, description="变更标题")
    description: str = Field(..., min_length=1, description="变更描述")
    reason: str = Field(..., min_length=1, description="变更原因")
    change_type: ChangeTypeEnum = Field(..., description="变更类型")
    priority: ChangePriorityEnum = Field(default=ChangePriorityEnum.MEDIUM, description="变更优先级")
    target_date: Optional[date] = Field(None, description="目标完成日期")
    impact_analysis: Optional[str] = Field(None, description="影响分析")
    effort_estimate: Optional[Decimal] = Field(None, ge=0, description="工作量估算(人天)")
    cost_estimate: Optional[Decimal] = Field(None, ge=0, description="成本估算")
    risk_assessment: Optional[str] = Field(None, description="风险评估")


class ChangeRequestUpdate(BaseModel):
    """更新变更请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="变更标题")
    description: Optional[str] = Field(None, min_length=1, description="变更描述")
    reason: Optional[str] = Field(None, min_length=1, description="变更原因")
    change_type: Optional[ChangeTypeEnum] = Field(None, description="变更类型")
    priority: Optional[ChangePriorityEnum] = Field(None, description="变更优先级")
    target_date: Optional[date] = Field(None, description="目标完成日期")
    impact_analysis: Optional[str] = Field(None, description="影响分析")
    effort_estimate: Optional[Decimal] = Field(None, ge=0, description="工作量估算(人天)")
    cost_estimate: Optional[Decimal] = Field(None, ge=0, description="成本估算")
    risk_assessment: Optional[str] = Field(None, description="风险评估")


class ChangeRequestApproval(BaseModel):
    """变更请求审批"""
    status: ChangeStatusEnum = Field(..., description="审批结果状态")
    approval_comments: Optional[str] = Field(None, description="审批意见")
    implementer_id: Optional[int] = Field(None, description="指定实施人ID")


class ChangeRequestResponse(BaseModel):
    """变更请求响应"""
    id: int
    requirement_id: int
    change_request_code: str
    title: str
    description: str
    reason: str
    change_type: ChangeTypeEnum
    status: ChangeStatusEnum
    priority: ChangePriorityEnum
    impact_analysis: Optional[str]
    effort_estimate: Optional[Decimal]
    cost_estimate: Optional[Decimal]
    risk_assessment: Optional[str]
    requestor_id: int
    approver_id: Optional[int]
    implementer_id: Optional[int]
    requested_date: date
    target_date: Optional[date]
    approved_date: Optional[date]
    implemented_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChangeRequestListResponse(PaginatedResponse):
    """变更请求列表响应"""
    items: List[ChangeRequestResponse]


class ChangeWorkflowStep(BaseModel):
    """变更工作流步骤"""
    step_name: str = Field(..., description="步骤名称")
    status: ChangeStatusEnum = Field(..., description="步骤状态")
    assignee_id: Optional[int] = Field(None, description="负责人ID")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    comments: Optional[str] = Field(None, description="步骤备注")


class ChangeWorkflowResponse(BaseModel):
    """变更工作流响应"""
    change_request_id: int
    current_step: str
    workflow_steps: List[ChangeWorkflowStep]
    created_at: datetime
    updated_at: datetime


class ImpactAnalysisRequest(BaseModel):
    """影响分析请求"""
    requirement_id: int = Field(..., description="需求ID")
    change_type: ChangeTypeEnum = Field(..., description="变更类型")
    change_description: str = Field(..., description="变更描述")
    analysis_depth: int = Field(default=3, ge=1, le=5, description="分析深度级别")


class ImpactItem(BaseModel):
    """影响项"""
    requirement_id: int
    requirement_title: str
    impact_type: str  # DIRECT, INDIRECT, CASCADE
    impact_level: str  # HIGH, MEDIUM, LOW
    impact_description: str
    estimated_effort: Optional[Decimal]


class ImpactAnalysisResponse(BaseModel):
    """影响分析响应"""
    change_request_id: Optional[int]
    requirement_id: int
    change_type: ChangeTypeEnum
    analysis_summary: str
    total_impacted_requirements: int
    direct_impacts: List[ImpactItem]
    indirect_impacts: List[ImpactItem]
    cascade_depth: int
    risk_score: float
    recommendations: List[str]
    analysis_date: datetime


class ChangeImplementationRequest(BaseModel):
    """变更实施请求"""
    implementation_notes: str = Field(..., description="实施说明")
    actual_effort: Optional[Decimal] = Field(None, ge=0, description="实际工作量")
    actual_cost: Optional[Decimal] = Field(None, ge=0, description="实际成本")


class ChangeImplementationResponse(BaseModel):
    """变更实施响应"""
    change_request_id: int
    implementation_status: str
    implementation_notes: str
    actual_effort: Optional[Decimal]
    actual_cost: Optional[Decimal]
    implemented_date: date
    implemented_by: int