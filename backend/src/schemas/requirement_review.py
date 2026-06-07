"""
需求评审相关的Pydantic模式定义

定义需求评审API的请求和响应模式
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ReviewTypeEnum(str, Enum):
    """评审类型枚举"""
    FORMAL = "FORMAL"
    INFORMAL = "INFORMAL"
    WALKTHROUGH = "WALKTHROUGH"
    INSPECTION = "INSPECTION"


class ReviewStatusEnum(str, Enum):
    """评审状态枚举"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReviewDecisionEnum(str, Enum):
    """评审决策枚举"""
    APPROVED = "APPROVED"
    APPROVED_WITH_MINOR_CHANGES = "APPROVED_WITH_MINOR_CHANGES"
    NEEDS_MAJOR_REVISION = "NEEDS_MAJOR_REVISION"
    REJECTED = "REJECTED"


class CommentTypeEnum(str, Enum):
    """评审意见类型枚举"""
    ISSUE = "ISSUE"
    SUGGESTION = "SUGGESTION"
    QUESTION = "QUESTION"
    APPROVAL = "APPROVAL"
    REJECTION = "REJECTION"


class CommentSeverityEnum(str, Enum):
    """意见严重程度枚举"""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    TRIVIAL = "TRIVIAL"


class CommentStatusEnum(str, Enum):
    """意见处理状态枚举"""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


# 请求模式

class CreateReviewRequest(BaseModel):
    """创建评审请求"""
    requirement_id: int = Field(..., description="需求ID")
    review_type: ReviewTypeEnum = Field(..., description="评审类型")
    title: str = Field(..., min_length=3, max_length=200, description="评审标题")
    description: Optional[str] = Field(None, max_length=2000, description="评审描述")
    review_criteria: Optional[str] = Field(None, max_length=2000, description="评审标准")
    moderator_id: int = Field(..., description="评审主持人ID")
    reviewers: Optional[List[int]] = Field(default_factory=list, description="评审人员ID列表")
    scheduled_date: Optional[datetime] = Field(None, description="计划评审时间")

    @validator('reviewers')
    def validate_reviewers(cls, v, values):
        if v and 'moderator_id' in values and values['moderator_id'] in v:
            raise ValueError("主持人不能同时是评审人")
        return v


class StartReviewRequest(BaseModel):
    """开始评审请求"""
    pass  # 只需要路径参数


class SubmitCommentRequest(BaseModel):
    """提交评审意见请求"""
    review_id: int = Field(..., description="评审ID")
    requirement_id: int = Field(..., description="需求ID")
    comment_type: Optional[CommentTypeEnum] = Field(CommentTypeEnum.SUGGESTION, description="意见类型")
    severity: Optional[CommentSeverityEnum] = Field(CommentSeverityEnum.MINOR, description="严重程度")
    content: str = Field(..., min_length=1, max_length=5000, description="意见内容")
    suggestion: Optional[str] = Field(None, max_length=2000, description="改进建议")
    section: Optional[str] = Field(None, max_length=100, description="相关章节")
    line_number: Optional[int] = Field(None, ge=1, description="行号")


class ResolveCommentRequest(BaseModel):
    """解决评审意见请求"""
    resolution: str = Field(..., min_length=1, max_length=2000, description="解决方案")


class CompleteReviewRequest(BaseModel):
    """完成评审请求"""
    decision: ReviewDecisionEnum = Field(..., description="评审决策")
    summary: str = Field(..., min_length=10, max_length=5000, description="评审总结")


class CancelReviewRequest(BaseModel):
    """取消评审请求"""
    reason: str = Field(..., min_length=5, max_length=500, description="取消原因")


# 响应模式

class ReviewCommentResponse(BaseModel):
    """评审意见响应"""
    id: int
    review_id: int
    requirement_id: int
    comment_type: CommentTypeEnum
    severity: Optional[CommentSeverityEnum]
    content: str
    suggestion: Optional[str]
    section: Optional[str]
    line_number: Optional[int]
    status: CommentStatusEnum
    resolution: Optional[str]
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    reviewer_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    """评审响应"""
    id: int
    requirement_id: int
    review_type: ReviewTypeEnum
    review_status: ReviewStatusEnum
    title: str
    description: Optional[str]
    review_criteria: Optional[str]
    moderator_id: int
    reviewers: Optional[List[int]]
    scheduled_date: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    decision: Optional[ReviewDecisionEnum]
    summary: Optional[str]
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewWithCommentsResponse(BaseModel):
    """带评审意见的评审响应"""
    review: ReviewResponse
    comments: List[ReviewCommentResponse]
    statistics: Dict[str, Any]


class ReviewListResponse(BaseModel):
    """评审列表响应"""
    reviews: List[ReviewResponse]
    total: int
    skip: int
    limit: int


class ReviewStatisticsResponse(BaseModel):
    """评审统计响应"""
    total_reviews: int
    status_distribution: Dict[str, int]
    decision_distribution: Dict[str, int]
    generated_at: str


# 查询参数模式

class ReviewQueryParams(BaseModel):
    """评审查询参数"""
    requirement_id: Optional[int] = Field(None, description="需求ID")
    review_type: Optional[ReviewTypeEnum] = Field(None, description="评审类型")
    review_status: Optional[ReviewStatusEnum] = Field(None, description="评审状态")
    moderator_id: Optional[int] = Field(None, description="主持人ID")
    reviewer_id: Optional[int] = Field(None, description="评审人ID")
    decision: Optional[ReviewDecisionEnum] = Field(None, description="评审决策")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(20, ge=1, le=100, description="限制数量")


class CommentQueryParams(BaseModel):
    """评审意见查询参数"""
    review_id: Optional[int] = Field(None, description="评审ID")
    requirement_id: Optional[int] = Field(None, description="需求ID")
    comment_type: Optional[CommentTypeEnum] = Field(None, description="意见类型")
    severity: Optional[CommentSeverityEnum] = Field(None, description="严重程度")
    status: Optional[CommentStatusEnum] = Field(None, description="处理状态")
    reviewer_id: Optional[int] = Field(None, description="评审人ID")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(50, ge=1, le=100, description="限制数量")


# 批量操作模式

class BatchResolveCommentsRequest(BaseModel):
    """批量解决评审意见请求"""
    comment_ids: List[int] = Field(..., min_items=1, description="意见ID列表")
    resolution: str = Field(..., min_length=1, max_length=2000, description="解决方案")


class BatchUpdateCommentsRequest(BaseModel):
    """批量更新评审意见请求"""
    comment_ids: List[int] = Field(..., min_items=1, description="意见ID列表")
    status: CommentStatusEnum = Field(..., description="新状态")
    resolution: Optional[str] = Field(None, max_length=2000, description="解决方案")


# 导出模式

class ReviewExportRequest(BaseModel):
    """评审导出请求"""
    review_ids: Optional[List[int]] = Field(None, description="评审ID列表")
    requirement_id: Optional[int] = Field(None, description="需求ID")
    project_id: Optional[int] = Field(None, description="项目ID")
    export_format: str = Field("excel", pattern="^(excel|pdf|word)$", description="导出格式")
    include_comments: bool = Field(True, description="是否包含评审意见")
    include_statistics: bool = Field(True, description="是否包含统计信息")


class ReviewReportResponse(BaseModel):
    """评审报告响应"""
    review_id: int
    requirement_id: int
    report_data: Dict[str, Any]
    generated_at: datetime


# 通知模式

class ReviewNotificationRequest(BaseModel):
    """评审通知请求"""
    review_id: int = Field(..., description="评审ID")
    notification_type: str = Field(..., pattern="^(invitation|reminder|completion)$", description="通知类型")
    recipients: Optional[List[int]] = Field(None, description="接收人ID列表，为空则通知所有相关人员")
    message: Optional[str] = Field(None, max_length=500, description="自定义消息")


# 模板模式

class ReviewTemplateRequest(BaseModel):
    """评审模板请求"""
    name: str = Field(..., min_length=3, max_length=100, description="模板名称")
    review_type: ReviewTypeEnum = Field(..., description="评审类型")
    review_criteria: str = Field(..., min_length=10, max_length=5000, description="评审标准")
    checklist: Optional[List[str]] = Field(default_factory=list, description="检查清单")
    is_public: bool = Field(False, description="是否公开模板")


class ReviewTemplateResponse(BaseModel):
    """评审模板响应"""
    id: int
    name: str
    review_type: ReviewTypeEnum
    review_criteria: str
    checklist: List[str]
    is_public: bool
    creator_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True