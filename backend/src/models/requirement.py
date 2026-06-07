"""
需求管理模块数据模型

本模块定义了需求管理相关的数据模型，包括：
- 需求基本信息管理
- 需求状态流转管理
- 需求评审管理
- 需求变更管理
- 需求依赖关系管理
- 需求追溯管理
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Date, JSON, Enum, DECIMAL, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum

from .base import Base

class RequirementType(PyEnum):
    """需求类型枚举"""
    FUNCTIONAL = "FUNCTIONAL"
    NON_FUNCTIONAL = "NON_FUNCTIONAL"
    CONSTRAINT = "CONSTRAINT"
    INTERFACE = "INTERFACE"

class RequirementStatus(PyEnum):
    """需求状态枚举 - 根据需求文档定义的13种状态"""
    DRAFT = "DRAFT"                    # 草稿
    PENDING_REVIEW = "PENDING_REVIEW"  # 待评审
    REVIEWING = "REVIEWING"            # 评审中
    NEEDS_REVISION = "NEEDS_REVISION"  # 需修改
    APPROVED = "APPROVED"              # 已批准
    IN_DEVELOPMENT = "IN_DEVELOPMENT"  # 开发中
    PAUSED = "PAUSED"                  # 已暂停
    TESTING = "TESTING"                # 待测试
    TEST_FAILED = "TEST_FAILED"        # 测试中
    COMPLETED = "COMPLETED"            # 测试失败
    DEPLOYED = "DEPLOYED"              # 已完成
    CLOSED = "CLOSED"                  # 已上线
    CANCELLED = "CANCELLED"            # 已关闭

class Priority(PyEnum):
    """优先级枚举"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    OPTIONAL = "OPTIONAL"

class BusinessValue(PyEnum):
    """业务价值枚举"""
    CORE = "CORE"
    IMPORTANT = "IMPORTANT"
    NORMAL = "NORMAL"
    OPTIONAL = "OPTIONAL"

class Complexity(PyEnum):
    """复杂度枚举"""
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"
    VERY_COMPLEX = "VERY_COMPLEX"

class RequirementBaseModel(Base):
    """需求管理模块基础模型类"""
    __abstract__ = True
    
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

class Requirement(RequirementBaseModel):
    """需求模型 - 根据需求管理模块规范设计"""
    __tablename__ = 'requirements'
    
    # 基本信息
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='需求ID')
    requirement_code = Column(String(50), unique=True, nullable=False, comment='需求编码')
    project_id = Column(BigInteger, ForeignKey('projects.id'), nullable=False, comment='所属项目ID')
    parent_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=True, comment='父需求ID')
    
    # 需求内容
    title = Column(String(200), nullable=False, comment='需求标题')
    description = Column(Text, comment='需求描述')
    acceptance_criteria = Column(Text, comment='验收标准')
    
    # 分类和属性
    requirement_type = Column(Enum(RequirementType), nullable=False, comment='需求类型')
    category = Column(String(100), comment='需求分类')
    priority = Column(Enum(Priority), default=Priority.MEDIUM, comment='优先级')
    business_value = Column(Enum(BusinessValue), default=BusinessValue.NORMAL, comment='业务价值')
    
    # 状态管理
    status = Column(Enum(RequirementStatus), default=RequirementStatus.DRAFT, comment='需求状态')
    
    # 复杂度和工作量
    complexity = Column(Enum(Complexity), comment='技术复杂度')
    estimated_effort = Column(DECIMAL(6, 2), comment='预估工作量(人天)')
    actual_effort = Column(DECIMAL(6, 2), comment='实际工作量(人天)')
    
    # 人员管理
    creator_id = Column(BigInteger, nullable=False, comment='创建人ID')
    assignee_id = Column(BigInteger, comment='负责人ID')
    reviewer_id = Column(BigInteger, comment='评审人ID')
    
    # 时间管理
    planned_start_date = Column(Date, comment='计划开始日期')
    planned_end_date = Column(Date, comment='计划完成日期')
    actual_start_date = Column(Date, comment='实际开始日期')
    actual_end_date = Column(Date, comment='实际完成日期')
    
    # 质量管理
    quality_score = Column(DECIMAL(3, 1), comment='质量评分(0-10)')
    completeness_score = Column(DECIMAL(3, 1), comment='完整性评分(0-10)')
    
    # 元数据
    tags = Column(JSON, comment='标签')
    custom_fields = Column(JSON, comment='自定义字段')
    attachments = Column(JSON, comment='附件信息')
    
    # 审计字段
    updated_by = Column(BigInteger, comment='更新人ID')
    version = Column(Integer, default=1, comment='版本号')
    
    # 关联关系
    project = relationship("Project", back_populates="requirements")
    parent = relationship("Requirement", remote_side=[id], back_populates="children")
    children = relationship("Requirement", back_populates="parent")
    
    # 状态历史
    status_history = relationship("RequirementStatusHistory", back_populates="requirement", cascade="all, delete-orphan")
    
    # 依赖关系
    source_dependencies = relationship("RequirementDependency", foreign_keys="RequirementDependency.source_requirement_id", back_populates="source_requirement", cascade="all, delete-orphan")
    target_dependencies = relationship("RequirementDependency", foreign_keys="RequirementDependency.target_requirement_id", back_populates="target_requirement")
    
    # 评审关系
    reviews = relationship("RequirementReview", back_populates="requirement", cascade="all, delete-orphan")
    
    # 变更关系
    change_requests = relationship("RequirementChangeRequest", back_populates="requirement", cascade="all, delete-orphan")
    
    # 追溯关系 - 由于使用通用字段，需要手动定义条件
    # source_traceability_links = relationship("RequirementTraceabilityLink", 
    #                                         primaryjoin="and_(Requirement.id == RequirementTraceabilityLink.source_id, RequirementTraceabilityLink.source_type == 'requirement')",
    #                                         cascade="all, delete-orphan")
    # target_traceability_links = relationship("RequirementTraceabilityLink",
    #                                         primaryjoin="and_(Requirement.id == RequirementTraceabilityLink.target_id, RequirementTraceabilityLink.target_type == 'requirement')")
    
    # 测试用例关系 - 使用字符串引用避免循环导入
    # test_cases = relationship("TestCase", back_populates="requirement")
    
    # 缺陷关系 - 使用字符串引用避免循环导入
    # defects = relationship("Defect", back_populates="requirement")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_code': self.requirement_code,
            'project_id': self.project_id,
            'parent_id': self.parent_id,
            'title': self.title,
            'description': self.description,
            'acceptance_criteria': self.acceptance_criteria,
            'requirement_type': self.requirement_type.value if self.requirement_type else None,
            'category': self.category,
            'priority': self.priority.value if self.priority else None,
            'business_value': self.business_value.value if self.business_value else None,
            'status': self.status.value if self.status else None,
            'complexity': self.complexity.value if self.complexity else None,
            'estimated_effort': float(self.estimated_effort) if self.estimated_effort else None,
            'actual_effort': float(self.actual_effort) if self.actual_effort else None,
            'creator_id': self.creator_id,
            'assignee_id': self.assignee_id,
            'reviewer_id': self.reviewer_id,
            'planned_start_date': self.planned_start_date.isoformat() if self.planned_start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'quality_score': float(self.quality_score) if self.quality_score else None,
            'completeness_score': float(self.completeness_score) if self.completeness_score else None,
            'tags': self.tags,
            'custom_fields': self.custom_fields,
            'attachments': self.attachments,
            'updated_by': self.updated_by,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementStatusHistory(RequirementBaseModel):
    """需求状态历史表"""
    __tablename__ = 'requirement_status_history'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='历史记录ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    old_status = Column(Enum(RequirementStatus), comment='变更前状态')
    new_status = Column(Enum(RequirementStatus), nullable=False, comment='变更后状态')
    change_reason = Column(Text, comment='变更原因')
    change_description = Column(Text, comment='变更描述')
    changed_by = Column(BigInteger, nullable=False, comment='变更人ID')
    changed_at = Column(DateTime, default=datetime.utcnow, comment='变更时间')
    
    # 关联关系
    requirement = relationship("Requirement", back_populates="status_history")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'old_status': self.old_status.value if self.old_status else None,
            'new_status': self.new_status.value if self.new_status else None,
            'change_reason': self.change_reason,
            'change_description': self.change_description,
            'changed_by': self.changed_by,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class DependencyType(PyEnum):
    """依赖类型枚举"""
    DEPENDS_ON = "DEPENDS_ON"
    BLOCKS = "BLOCKS"
    RELATES_TO = "RELATES_TO"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    DUPLICATES = "DUPLICATES"
    REPLACES = "REPLACES"

class RequirementDependency(RequirementBaseModel):
    """需求依赖关系表"""
    __tablename__ = 'requirement_dependencies'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='依赖关系ID')
    source_requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='源需求ID')
    target_requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='目标需求ID')
    dependency_type = Column(Enum(DependencyType), nullable=False, comment='依赖类型')
    description = Column(Text, comment='依赖描述')
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    
    # 关联关系
    source_requirement = relationship("Requirement", foreign_keys=[source_requirement_id], back_populates="source_dependencies")
    target_requirement = relationship("Requirement", foreign_keys=[target_requirement_id], back_populates="target_dependencies")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'source_requirement_id': self.source_requirement_id,
            'target_requirement_id': self.target_requirement_id,
            'dependency_type': self.dependency_type.value if self.dependency_type else None,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ReviewType(PyEnum):
    """评审类型枚举"""
    FORMAL = "FORMAL"
    INFORMAL = "INFORMAL"
    WALKTHROUGH = "WALKTHROUGH"
    INSPECTION = "INSPECTION"

class ReviewStatus(PyEnum):
    """评审状态枚举"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ReviewDecision(PyEnum):
    """评审决策枚举"""
    APPROVED = "APPROVED"
    APPROVED_WITH_MINOR_CHANGES = "APPROVED_WITH_MINOR_CHANGES"
    NEEDS_MAJOR_REVISION = "NEEDS_MAJOR_REVISION"
    REJECTED = "REJECTED"

class RequirementReview(RequirementBaseModel):
    """需求评审表"""
    __tablename__ = 'requirement_reviews'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='评审ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    
    # 评审信息
    review_type = Column(Enum(ReviewType), nullable=False, comment='评审类型')
    review_status = Column(Enum(ReviewStatus), default=ReviewStatus.PENDING, comment='评审状态')
    title = Column(String(200), nullable=False, comment='评审标题')
    description = Column(Text, comment='评审描述')
    review_criteria = Column(Text, comment='评审标准')
    
    # 人员管理
    moderator_id = Column(BigInteger, nullable=False, comment='评审主持人ID')
    reviewers = Column(JSON, comment='评审人员列表')
    
    # 时间管理
    scheduled_date = Column(DateTime, comment='计划评审时间')
    started_at = Column(DateTime, comment='实际开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    
    # 评审结果
    decision = Column(Enum(ReviewDecision), comment='评审决策')
    summary = Column(Text, comment='评审总结')
    
    # 审计字段
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    
    # 关联关系
    requirement = relationship("Requirement", back_populates="reviews")
    comments = relationship("RequirementReviewComment", back_populates="review", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'review_type': self.review_type.value if self.review_type else None,
            'review_status': self.review_status.value if self.review_status else None,
            'title': self.title,
            'description': self.description,
            'review_criteria': self.review_criteria,
            'moderator_id': self.moderator_id,
            'reviewers': self.reviewers,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'decision': self.decision.value if self.decision else None,
            'summary': self.summary,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CommentType(PyEnum):
    """评审意见类型枚举"""
    ISSUE = "ISSUE"
    SUGGESTION = "SUGGESTION"
    QUESTION = "QUESTION"
    APPROVAL = "APPROVAL"
    REJECTION = "REJECTION"

class CommentSeverity(PyEnum):
    """意见严重程度枚举"""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    TRIVIAL = "TRIVIAL"

class CommentStatus(PyEnum):
    """意见处理状态枚举"""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"

class RequirementReviewComment(RequirementBaseModel):
    """需求评审意见表"""
    __tablename__ = 'requirement_review_comments'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='评审意见ID')
    review_id = Column(BigInteger, ForeignKey('requirement_reviews.id'), nullable=False, comment='评审ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    
    # 意见内容
    comment_type = Column(Enum(CommentType), nullable=False, comment='意见类型')
    severity = Column(Enum(CommentSeverity), comment='严重程度')
    content = Column(Text, nullable=False, comment='意见内容')
    suggestion = Column(Text, comment='改进建议')
    
    # 位置信息
    section = Column(String(100), comment='相关章节')
    line_number = Column(Integer, comment='行号')
    
    # 处理状态
    status = Column(Enum(CommentStatus), default=CommentStatus.OPEN, comment='处理状态')
    resolution = Column(Text, comment='解决方案')
    resolved_by = Column(BigInteger, comment='解决人ID')
    resolved_at = Column(DateTime, comment='解决时间')
    
    # 审计字段
    reviewer_id = Column(BigInteger, nullable=False, comment='评审人ID')
    
    # 关联关系
    review = relationship("RequirementReview", back_populates="comments")
    requirement = relationship("Requirement")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'review_id': self.review_id,
            'requirement_id': self.requirement_id,
            'comment_type': self.comment_type.value if self.comment_type else None,
            'severity': self.severity.value if self.severity else None,
            'content': self.content,
            'suggestion': self.suggestion,
            'section': self.section,
            'line_number': self.line_number,
            'status': self.status.value if self.status else None,
            'resolution': self.resolution,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'reviewer_id': self.reviewer_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ChangeType(PyEnum):
    """变更类型枚举"""
    ADDITION = "ADDITION"
    MODIFICATION = "MODIFICATION"
    DELETION = "DELETION"
    CLARIFICATION = "CLARIFICATION"

class ChangeStatus(PyEnum):
    """变更状态枚举"""
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"
    CLOSED = "CLOSED"

class ChangePriority(PyEnum):
    """变更优先级枚举"""
    EMERGENCY = "EMERGENCY"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class RequirementChangeRequest(RequirementBaseModel):
    """需求变更请求表"""
    __tablename__ = 'requirement_change_requests'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='变更请求ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    change_request_code = Column(String(50), unique=True, nullable=False, comment='变更请求编码')
    
    # 变更信息
    title = Column(String(200), nullable=False, comment='变更标题')
    description = Column(Text, nullable=False, comment='变更描述')
    reason = Column(Text, nullable=False, comment='变更原因')
    change_type = Column(Enum(ChangeType), nullable=False, comment='变更类型')
    
    # 影响分析
    impact_analysis = Column(Text, comment='影响分析')
    effort_estimate = Column(DECIMAL(6, 2), comment='工作量估算')
    cost_estimate = Column(DECIMAL(10, 2), comment='成本估算')
    risk_assessment = Column(Text, comment='风险评估')
    
    # 审批流程
    status = Column(Enum(ChangeStatus), default=ChangeStatus.SUBMITTED, comment='变更状态')
    priority = Column(Enum(ChangePriority), default=ChangePriority.MEDIUM, comment='变更优先级')
    
    # 人员管理
    requestor_id = Column(BigInteger, nullable=False, comment='申请人ID')
    approver_id = Column(BigInteger, comment='审批人ID')
    implementer_id = Column(BigInteger, comment='实施人ID')
    
    # 时间管理
    requested_date = Column(Date, nullable=False, comment='申请日期')
    target_date = Column(Date, comment='目标完成日期')
    approved_date = Column(Date, comment='审批日期')
    implemented_date = Column(Date, comment='实施日期')
    
    # 关联关系
    requirement = relationship("Requirement", back_populates="change_requests")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'requirement_id': self.requirement_id,
            'change_request_code': self.change_request_code,
            'title': self.title,
            'description': self.description,
            'reason': self.reason,
            'change_type': self.change_type.value if self.change_type else None,
            'impact_analysis': self.impact_analysis,
            'effort_estimate': float(self.effort_estimate) if self.effort_estimate else None,
            'cost_estimate': float(self.cost_estimate) if self.cost_estimate else None,
            'risk_assessment': self.risk_assessment,
            'status': self.status.value if self.status else None,
            'priority': self.priority.value if self.priority else None,
            'requestor_id': self.requestor_id,
            'approver_id': self.approver_id,
            'implementer_id': self.implementer_id,
            'requested_date': self.requested_date.isoformat() if self.requested_date else None,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'approved_date': self.approved_date.isoformat() if self.approved_date else None,
            'implemented_date': self.implemented_date.isoformat() if self.implemented_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class TraceabilityLinkType(PyEnum):
    """追溯链接类型枚举"""
    DERIVES_FROM = "DERIVES_FROM"
    IMPLEMENTS = "IMPLEMENTS"
    TESTS = "TESTS"
    VALIDATES = "VALIDATES"
    REFINES = "REFINES"

class RequirementTraceabilityLink(RequirementBaseModel):
    """需求追溯链接表"""
    __tablename__ = 'requirement_traceability_links'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='追溯链接ID')
    source_type = Column(String(50), nullable=False, comment='源对象类型')  # requirement, task, test_case, etc.
    source_id = Column(BigInteger, nullable=False, comment='源对象ID')
    target_type = Column(String(50), nullable=False, comment='目标对象类型')
    target_id = Column(BigInteger, nullable=False, comment='目标对象ID')
    link_type = Column(Enum(TraceabilityLinkType), nullable=False, comment='链接类型')
    description = Column(Text, comment='链接描述')
    created_by = Column(BigInteger, nullable=False, comment='创建人ID')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'link_type': self.link_type.value if self.link_type else None,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }