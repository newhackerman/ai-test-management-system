"""
需求状态流转验证器

本模块实现需求状态流转的前置条件检查、合法性验证和详细反馈。
根据需求文档中定义的状态流转规则和前置条件进行验证。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.requirement import Requirement, RequirementStatus
from ..models.requirement_status_flow import (
    RequirementStatusFlowConfig, 
    PreconditionCheckResult, 
    StatusTransitionError
)
from ..models.user import User
from ..models.project import Project


class RequirementStatusValidator:
    """需求状态流转验证器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.flow_config = RequirementStatusFlowConfig()
    
    def validate_status_transition(
        self, 
        requirement: Requirement, 
        new_status: RequirementStatus, 
        user_id: int,
        reason: str = None,
        additional_data: Dict[str, Any] = None
    ) -> PreconditionCheckResult:
        """
        验证状态流转的合法性和前置条件
        
        Args:
            requirement: 需求对象
            new_status: 目标状态
            user_id: 操作用户ID
            reason: 变更原因
            additional_data: 额外数据
            
        Returns:
            PreconditionCheckResult: 验证结果
        """
        result = PreconditionCheckResult(is_valid=True)
        
        try:
            # 1. 检查状态流转合法性
            self._validate_transition_legality(requirement.status, new_status, result)
            
            # 2. 检查用户权限
            self._validate_user_permissions(requirement, new_status, user_id, result)
            
            # 3. 检查状态特定的前置条件
            self._validate_status_specific_preconditions(requirement, new_status, result, additional_data)
            
            # 4. 检查依赖关系
            self._validate_dependency_constraints(requirement, new_status, result)
            
            # 5. 检查业务规则
            self._validate_business_rules(requirement, new_status, result)
            
            # 6. 检查必填字段
            self._validate_required_fields(requirement, new_status, result)
            
            # 7. 添加警告信息
            self._add_warnings(requirement, new_status, result)
            
        except Exception as e:
            result.add_error(f"验证过程中发生错误: {str(e)}")
        
        return result
    
    def _validate_transition_legality(
        self, 
        current_status: RequirementStatus, 
        new_status: RequirementStatus, 
        result: PreconditionCheckResult
    ):
        """验证状态流转合法性"""
        if not self.flow_config.is_valid_transition(current_status, new_status):
            valid_statuses = self.flow_config.get_valid_next_statuses(current_status)
            valid_status_names = [status.value for status in valid_statuses]
            result.add_error(
                f"不能从状态 '{current_status.value}' 流转到 '{new_status.value}'。"
                f"当前状态可以流转到: {', '.join(valid_status_names)}"
            )
    
    def _validate_user_permissions(
        self, 
        requirement: Requirement, 
        new_status: RequirementStatus, 
        user_id: int, 
        result: PreconditionCheckResult
    ):
        """验证用户权限"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            result.add_error("用户不存在")
            return
        
        # 检查基本权限
        if not self._has_basic_permission(user, requirement, new_status):
            result.add_error("用户没有执行此状态变更的权限")
        
        # 检查特定状态的权限要求
        if new_status == RequirementStatus.APPROVED:
            if not self._has_review_permission(user, requirement):
                result.add_error("只有评审人员可以批准需求")
        
        elif new_status == RequirementStatus.CANCELLED:
            if not self._has_cancel_permission(user, requirement):
                result.add_error("只有项目管理员或需求创建人可以取消需求")
        
        elif new_status in [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.TESTING]:
            if not self._has_development_permission(user, requirement):
                result.add_error("只有开发团队成员可以更新开发状态")
    
    def _validate_status_specific_preconditions(
        self, 
        requirement: Requirement, 
        new_status: RequirementStatus, 
        result: PreconditionCheckResult,
        additional_data: Dict[str, Any] = None
    ):
        """验证状态特定的前置条件"""
        additional_data = additional_data or {}
        
        if new_status == RequirementStatus.PENDING_REVIEW:
            self._validate_pending_review_preconditions(requirement, result)
        
        elif new_status == RequirementStatus.REVIEWING:
            self._validate_reviewing_preconditions(requirement, result)
        
        elif new_status == RequirementStatus.APPROVED:
            self._validate_approved_preconditions(requirement, result)
        
        elif new_status == RequirementStatus.IN_DEVELOPMENT:
            self._validate_development_preconditions(requirement, result)
        
        elif new_status == RequirementStatus.PAUSED:
            self._validate_paused_preconditions(requirement, result, additional_data)
        
        elif new_status == RequirementStatus.TESTING:
            self._validate_testing_preconditions(requirement, result)
        
        elif new_status == RequirementStatus.COMPLETED:
            self._validate_completed_preconditions(requirement, result)
        
        elif new_status == RequirementStatus.DEPLOYED:
            self._validate_deployed_preconditions(requirement, result)
        
        elif new_status == RequirementStatus.CANCELLED:
            self._validate_cancelled_preconditions(requirement, result, additional_data)
    
    def _validate_pending_review_preconditions(self, requirement: Requirement, result: PreconditionCheckResult):
        """验证待评审状态的前置条件"""
        # 检查必填字段
        if not requirement.title or not requirement.title.strip():
            result.add_error("需求标题不能为空")
        
        if not requirement.description or not requirement.description.strip():
            result.add_error("需求描述不能为空")
        
        if not requirement.acceptance_criteria or not requirement.acceptance_criteria.strip():
            result.add_error("验收标准不能为空")
        
        if not requirement.requirement_type:
            result.add_error("需求类型不能为空")
        
        if not requirement.priority:
            result.add_error("优先级不能为空")
        
        # 检查需求完整性评分
        if requirement.completeness_score and requirement.completeness_score < 7.0:
            result.add_warning("需求完整性评分较低，建议完善需求内容后再提交评审")
    
    def _validate_reviewing_preconditions(self, requirement: Requirement, result: PreconditionCheckResult):
        """验证评审中状态的前置条件"""
        if not requirement.reviewer_id:
            result.add_error("需要指定评审人员")
        
        # 检查是否有活跃的评审
        from ..models.requirement import RequirementReview, ReviewStatus
        active_review = self.db.query(RequirementReview).filter(
            RequirementReview.requirement_id == requirement.id,
            RequirementReview.review_status.in_([ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS])
        ).first()
        
        if not active_review:
            result.add_error("需要创建评审任务才能进入评审状态")
    
    def _validate_approved_preconditions(self, requirement: Requirement, result: PreconditionCheckResult):
        """验证已批准状态的前置条件"""
        # 检查评审是否完成
        from ..models.requirement import RequirementReview, ReviewStatus, ReviewDecision
        completed_review = self.db.query(RequirementReview).filter(
            RequirementReview.requirement_id == requirement.id,
            RequirementReview.review_status == ReviewStatus.COMPLETED,
            RequirementReview.decision.in_([ReviewDecision.APPROVED, ReviewDecision.APPROVED_WITH_MINOR_CHANGES])
        ).first()
        
        if not completed_review:
            result.add_error("需求必须通过评审才能批准")
        
        # 检查所有评审意见是否已处理
        from ..models.requirement import RequirementReviewComment, CommentStatus
        unresolved_comments = self.db.query(RequirementReviewComment).filter(
            RequirementReviewComment.requirement_id == requirement.id,
            RequirementReviewComment.status.in_([CommentStatus.OPEN, CommentStatus.IN_PROGRESS])
        ).count()
        
        if unresolved_comments > 0:
            result.add_error(f"还有 {unresolved_comments} 个评审意见未处理完成")
    
    def _validate_development_preconditions(self, requirement: Requirement, result: PreconditionCheckResult):
        """验证开发中状态的前置条件"""
        if not requirement.assignee_id:
            result.add_error("需要指定开发负责人")
        
        if not requirement.planned_start_date:
            result.add_warning("建议设置计划开始日期")
        
        if not requirement.estimated_effort:
            result.add_warning("建议设置预估工作量")
    
    def _validate_paused_preconditions(
        self, 
        requirement: Requirement, 
        result: PreconditionCheckResult,
        additional_data: Dict[str, Any]
    ):
        """验证暂停状态的前置条件"""
        pause_reason = additional_data.get('pause_reason')
        if not pause_reason or not pause_reason.strip():
            result.add_error("暂停需求必须提供暂停原因")
    
    def _validate_testing_preconditions(self, requirement: Requirement, result: PreconditionCheckResult):
        """验证测试状态的前置条件"""
        # 检查是否有关联的测试用例
        if hasattr(requirement, 'test_cases') and not requirement.test_cases:
            result.add_warning("建议创建测试用例以验证需求实现")
        
        # 检查开发完成确认
        if not requirement.actual_end_date:
            result.add_warning("建议设置实际完成日期")
    
    def _validate_completed_preconditions(self, requirement: Requirement, result: PreconditionCheckResult):
        """验证完成状态的前置条件"""
        # 检查验收标准是否满足
        if not requirement.acceptance_criteria:
            result.add_error("需求必须有明确的验收标准")
        
        # 检查测试是否通过
        # 这里可以集成测试管理系统的API来检查测试结果
        # 暂时添加警告
        result.add_warning("请确认所有测试用例都已通过")
    
    def _validate_deployed_preconditions(self, requirement: Requirement, result: PreconditionCheckResult):
        """验证部署状态的前置条件"""
        # 检查部署验证
        result.add_warning("请确认需求已成功部署到生产环境")
    
    def _validate_cancelled_preconditions(
        self, 
        requirement: Requirement, 
        result: PreconditionCheckResult,
        additional_data: Dict[str, Any]
    ):
        """验证取消状态的前置条件"""
        cancel_reason = additional_data.get('cancel_reason')
        if not cancel_reason or not cancel_reason.strip():
            result.add_error("取消需求必须提供取消原因")
        
        # 检查影响评估
        impact_assessment = additional_data.get('impact_assessment')
        if not impact_assessment:
            result.add_warning("建议提供取消需求的影响评估")
    
    def _validate_dependency_constraints(
        self, 
        requirement: Requirement, 
        new_status: RequirementStatus, 
        result: PreconditionCheckResult
    ):
        """验证依赖关系约束"""
        # 检查依赖需求的状态
        if new_status == RequirementStatus.IN_DEVELOPMENT:
            # 检查依赖的需求是否已完成
            from ..models.requirement import RequirementDependency, DependencyType
            blocking_dependencies = self.db.query(RequirementDependency).join(
                Requirement, RequirementDependency.source_requirement_id == Requirement.id
            ).filter(
                RequirementDependency.target_requirement_id == requirement.id,
                RequirementDependency.dependency_type == DependencyType.DEPENDS_ON,
                Requirement.status.notin_([
                    RequirementStatus.COMPLETED, 
                    RequirementStatus.DEPLOYED, 
                    RequirementStatus.CLOSED
                ])
            ).all()
            
            if blocking_dependencies:
                blocking_req_codes = [dep.source_requirement.requirement_code for dep in blocking_dependencies]
                result.add_warning(
                    f"以下依赖需求尚未完成: {', '.join(blocking_req_codes)}。"
                    "建议等待依赖需求完成后再开始开发。"
                )
    
    def _validate_business_rules(
        self, 
        requirement: Requirement, 
        new_status: RequirementStatus, 
        result: PreconditionCheckResult
    ):
        """验证业务规则"""
        # 检查项目状态
        project = self.db.query(Project).filter(Project.id == requirement.project_id).first()
        if project and hasattr(project, 'status'):
            if project.status == 'CLOSED' and new_status not in [RequirementStatus.CLOSED, RequirementStatus.CANCELLED]:
                result.add_error("项目已关闭，不能变更需求状态")
        
        # 检查子需求状态
        if new_status == RequirementStatus.COMPLETED:
            incomplete_children = self.db.query(Requirement).filter(
                Requirement.parent_id == requirement.id,
                Requirement.status.notin_([
                    RequirementStatus.COMPLETED, 
                    RequirementStatus.DEPLOYED, 
                    RequirementStatus.CLOSED,
                    RequirementStatus.CANCELLED
                ])
            ).count()
            
            if incomplete_children > 0:
                result.add_warning(f"还有 {incomplete_children} 个子需求未完成")
    
    def _validate_required_fields(
        self, 
        requirement: Requirement, 
        new_status: RequirementStatus, 
        result: PreconditionCheckResult
    ):
        """验证必填字段"""
        required_fields_map = {
            RequirementStatus.PENDING_REVIEW: ['title', 'description', 'acceptance_criteria'],
            RequirementStatus.IN_DEVELOPMENT: ['assignee_id'],
            RequirementStatus.TESTING: ['assignee_id'],
        }
        
        required_fields = required_fields_map.get(new_status, [])
        for field in required_fields:
            value = getattr(requirement, field, None)
            if not value:
                field_name = self._get_field_display_name(field)
                result.add_error(f"字段 '{field_name}' 不能为空")
    
    def _add_warnings(
        self, 
        requirement: Requirement, 
        new_status: RequirementStatus, 
        result: PreconditionCheckResult
    ):
        """添加警告信息"""
        # 质量评分警告
        if requirement.quality_score and requirement.quality_score < 6.0:
            result.add_warning("需求质量评分较低，建议改进需求质量")
        
        # 工作量估算警告
        if new_status == RequirementStatus.IN_DEVELOPMENT and not requirement.estimated_effort:
            result.add_warning("建议设置预估工作量以便更好地跟踪进度")
        
        # 计划日期警告
        if new_status == RequirementStatus.IN_DEVELOPMENT:
            if not requirement.planned_start_date or not requirement.planned_end_date:
                result.add_warning("建议设置计划开始和结束日期")
    
    def _has_basic_permission(self, user: User, requirement: Requirement, new_status: RequirementStatus) -> bool:
        """检查基本权限"""
        # 需求创建人总是有权限
        if requirement.creator_id == user.id:
            return True
        
        # 需求负责人有权限
        if requirement.assignee_id == user.id:
            return True
        
        # 项目管理员有权限
        # 这里需要根据实际的权限系统实现
        return True  # 暂时返回True，实际应该检查用户角色
    
    def _has_review_permission(self, user: User, requirement: Requirement) -> bool:
        """检查评审权限"""
        return requirement.reviewer_id == user.id or self._is_project_manager(user, requirement)
    
    def _has_cancel_permission(self, user: User, requirement: Requirement) -> bool:
        """检查取消权限"""
        return (requirement.creator_id == user.id or 
                self._is_project_manager(user, requirement))
    
    def _has_development_permission(self, user: User, requirement: Requirement) -> bool:
        """检查开发权限"""
        return (requirement.assignee_id == user.id or 
                self._is_developer(user, requirement))
    
    def _is_project_manager(self, user: User, requirement: Requirement) -> bool:
        """检查是否为项目管理员"""
        # 这里需要根据实际的权限系统实现
        return True  # 暂时返回True
    
    def _is_developer(self, user: User, requirement: Requirement) -> bool:
        """检查是否为开发人员"""
        # 这里需要根据实际的权限系统实现
        return True  # 暂时返回True
    
    def _get_field_display_name(self, field: str) -> str:
        """获取字段显示名称"""
        field_names = {
            'title': '需求标题',
            'description': '需求描述',
            'acceptance_criteria': '验收标准',
            'assignee_id': '负责人',
            'reviewer_id': '评审人',
            'requirement_type': '需求类型',
            'priority': '优先级'
        }
        return field_names.get(field, field)