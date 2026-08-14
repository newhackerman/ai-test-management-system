"""
需求评审服务

提供需求评审的核心业务逻辑，包括：
- 评审流程管理
- 评审意见收集系统
- 评审决策记录功能
- 评审通知和协作功能
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, func

from ..models.requirement import (
    RequirementReview, RequirementReviewComment, Requirement,
    ReviewType, ReviewStatus, ReviewDecision, CommentType, CommentSeverity, CommentStatus
)
from ..repositories.requirement_repository import RequirementRepository
from ..services.audit_service import AuditService
from ..services.requirement_notification_service import RequirementNotificationService
from ..services.ai_router_service import AIRouterService, TaskType
from ..core.exceptions import ValidationError, BusinessLogicError, NotFoundError, PermissionError

logger = logging.getLogger(__name__)


class ReviewAnalysis:
    """评审分析结果"""
    
    def __init__(self, suggested_severity: CommentSeverity, suggested_type: CommentType,
                 quality_issues: List[str], improvement_suggestions: List[str]):
        self.suggested_severity = suggested_severity
        self.suggested_type = suggested_type
        self.quality_issues = quality_issues
        self.improvement_suggestions = improvement_suggestions


class RequirementReviewService:
    """需求评审服务"""
    
    def __init__(self, db: AsyncSession, ai_router_service: Optional[AIRouterService] = None,
                 audit_service: Optional[AuditService] = None,
                 notification_service: Optional[RequirementNotificationService] = None):
        self.db = db
        self.requirement_repo = RequirementRepository(db)
        self.ai_router_service = ai_router_service
        self.audit_service = audit_service
        self.notification_service = notification_service
    
    async def create_review(self, review_data: Dict[str, Any], creator_id: int) -> RequirementReview:
        """
        创建需求评审
        
        Args:
            review_data: 评审数据
            creator_id: 创建人ID
            
        Returns:
            创建的评审对象
            
        Raises:
            ValidationError: 数据验证失败
            BusinessLogicError: 业务逻辑错误
        """
        try:
            # 1. 验证评审数据
            await self._validate_review_data(review_data)
            
            # 2. 检查需求状态
            requirement = await self.requirement_repo.get_by_id(review_data['requirement_id'])
            if not requirement:
                raise NotFoundError(f"需求不存在: {review_data['requirement_id']}")
            
            # 3. 检查是否已有进行中的评审
            existing_review = await self._get_active_review_for_requirement(review_data['requirement_id'])
            if existing_review:
                raise BusinessLogicError("该需求已有进行中的评审")
            
            # 4. 创建评审实体
            review = RequirementReview(
                requirement_id=review_data['requirement_id'],
                review_type=ReviewType(review_data['review_type']),
                title=review_data['title'],
                description=review_data.get('description'),
                review_criteria=review_data.get('review_criteria'),
                moderator_id=review_data['moderator_id'],
                reviewers=review_data.get('reviewers', []),
                scheduled_date=review_data.get('scheduled_date'),
                created_by=creator_id
            )
            
            # 5. 保存评审
            await self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            
            # 6. 更新需求状态为待评审
            await self.requirement_repo.update_requirement_status(
                review_data['requirement_id'], 
                requirement.RequirementStatus.PENDING_REVIEW, 
                creator_id,
                "创建评审"
            )
            
            # 7. 发送评审邀请通知
            if self.notification_service:
                await self._send_review_invitations(review)
            
            # 8. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=creator_id,
                    operation="CREATE_REVIEW",
                    resource_type="requirement_review",
                    resource_id=review.id,
                    details={
                        "requirement_id": review.requirement_id,
                        "review_type": review.review_type.value,
                        "moderator_id": review.moderator_id,
                        "reviewers": review.reviewers
                    }
                )
            
            logger.info(f"需求评审创建成功: {review.id} for requirement {review.requirement_id}")
            return review
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建需求评审失败: {str(e)}")
            raise BusinessLogicError(f"创建需求评审失败: {str(e)}")
    
    async def start_review(self, review_id: int, moderator_id: int) -> RequirementReview:
        """
        开始评审
        
        Args:
            review_id: 评审ID
            moderator_id: 主持人ID
            
        Returns:
            更新后的评审对象
        """
        try:
            # 1. 获取评审
            review = await self._get_review_by_id(review_id)
            if review.moderator_id != moderator_id:
                raise PermissionError("只有评审主持人可以开始评审")
            
            if review.review_status != ReviewStatus.PENDING:
                raise BusinessLogicError(f"评审状态不正确: {review.review_status.value}")
            
            # 2. 更新评审状态
            review.review_status = ReviewStatus.IN_PROGRESS
            review.started_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(review)
            
            # 3. 更新需求状态为评审中
            await self.requirement_repo.update_requirement_status(
                review.requirement_id,
                requirement.RequirementStatus.REVIEWING,
                moderator_id,
                "开始评审"
            )
            
            # 4. 发送评审开始通知
            if self.notification_service:
                await self._send_review_started_notifications(review)
            
            # 5. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=moderator_id,
                    operation="START_REVIEW",
                    resource_type="requirement_review",
                    resource_id=review_id,
                    details={"requirement_id": review.requirement_id}
                )
            
            logger.info(f"评审开始: {review_id}")
            return review
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"开始评审失败: {str(e)}")
            raise BusinessLogicError(f"开始评审失败: {str(e)}")
    
    async def submit_review_comment(self, comment_data: Dict[str, Any], reviewer_id: int) -> RequirementReviewComment:
        """
        提交评审意见
        
        Args:
            comment_data: 评审意见数据
            reviewer_id: 评审人ID
            
        Returns:
            创建的评审意见对象
        """
        try:
            # 1. 验证评审权限
            review = await self._get_review_by_id(comment_data['review_id'])
            if not await self._has_review_permission(review, reviewer_id):
                raise PermissionError("没有评审权限")
            
            if review.review_status != ReviewStatus.IN_PROGRESS:
                raise BusinessLogicError("评审未开始或已结束")
            
            # 2. AI辅助意见分析（如果可用）
            ai_analysis = None
            if self.ai_router_service and comment_data.get('content'):
                ai_analysis = await self._analyze_review_comment_with_ai(
                    comment_data['content'],
                    comment_data.get('suggestion', '')
                )
            
            # 3. 创建评审意见
            comment = RequirementReviewComment(
                review_id=comment_data['review_id'],
                requirement_id=comment_data['requirement_id'],
                comment_type=CommentType(comment_data.get('comment_type', 
                    ai_analysis.suggested_type.value if ai_analysis else CommentType.SUGGESTION.value)),
                severity=CommentSeverity(comment_data.get('severity',
                    ai_analysis.suggested_severity.value if ai_analysis else CommentSeverity.MINOR.value)),
                content=comment_data['content'],
                suggestion=comment_data.get('suggestion'),
                section=comment_data.get('section'),
                line_number=comment_data.get('line_number'),
                reviewer_id=reviewer_id
            )
            
            # 4. 保存意见
            await self.db.add(comment)
            await self.db.commit()
            await self.db.refresh(comment)
            
            # 5. 发送意见通知
            if self.notification_service:
                await self._send_comment_notifications(comment)
            
            # 6. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=reviewer_id,
                    operation="SUBMIT_REVIEW_COMMENT",
                    resource_type="requirement_review_comment",
                    resource_id=comment.id,
                    details={
                        "review_id": comment.review_id,
                        "requirement_id": comment.requirement_id,
                        "comment_type": comment.comment_type.value,
                        "severity": comment.severity.value if comment.severity else None
                    }
                )
            
            logger.info(f"评审意见提交成功: {comment.id}")
            return comment
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"提交评审意见失败: {str(e)}")
            raise BusinessLogicError(f"提交评审意见失败: {str(e)}")
    
    async def resolve_comment(self, comment_id: int, resolution: str, resolved_by: int) -> RequirementReviewComment:
        """
        解决评审意见
        
        Args:
            comment_id: 意见ID
            resolution: 解决方案
            resolved_by: 解决人ID
            
        Returns:
            更新后的评审意见对象
        """
        try:
            # 1. 获取评审意见
            comment = await self._get_comment_by_id(comment_id)
            
            # 2. 验证解决权限
            if not await self._has_resolve_permission(comment, resolved_by):
                raise PermissionError("没有解决意见的权限")
            
            if comment.status in [CommentStatus.RESOLVED, CommentStatus.CLOSED]:
                raise BusinessLogicError("意见已经解决")
            
            # 3. 更新意见状态
            comment.status = CommentStatus.RESOLVED
            comment.resolution = resolution
            comment.resolved_by = resolved_by
            comment.resolved_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(comment)
            
            # 4. 发送解决通知
            if self.notification_service:
                await self._send_comment_resolved_notifications(comment)
            
            # 5. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=resolved_by,
                    operation="RESOLVE_REVIEW_COMMENT",
                    resource_type="requirement_review_comment",
                    resource_id=comment_id,
                    details={
                        "resolution": resolution,
                        "review_id": comment.review_id
                    }
                )
            
            logger.info(f"评审意见解决: {comment_id}")
            return comment
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"解决评审意见失败: {str(e)}")
            raise BusinessLogicError(f"解决评审意见失败: {str(e)}")
    
    async def complete_review(self, review_id: int, decision: ReviewDecision, 
                            summary: str, moderator_id: int) -> RequirementReview:
        """
        完成需求评审
        
        Args:
            review_id: 评审ID
            decision: 评审决策
            summary: 评审总结
            moderator_id: 主持人ID
            
        Returns:
            完成的评审对象
        """
        try:
            # 1. 获取评审
            review = await self._get_review_by_id(review_id)
            if review.moderator_id != moderator_id:
                raise PermissionError("只有评审主持人可以完成评审")
            
            if review.review_status != ReviewStatus.IN_PROGRESS:
                raise BusinessLogicError(f"评审状态不正确: {review.review_status.value}")
            
            # 2. 检查评审完整性
            await self._validate_review_completeness(review_id)
            
            # 3. 更新评审状态
            review.review_status = ReviewStatus.COMPLETED
            review.decision = decision
            review.summary = summary
            review.completed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(review)
            
            # 4. 更新需求状态
            new_requirement_status = self._get_requirement_status_by_decision(decision)
            await self.requirement_repo.update_requirement_status(
                review.requirement_id,
                new_requirement_status,
                moderator_id,
                f"评审完成: {decision.value}"
            )
            
            # 5. 生成评审报告
            await self._generate_review_report(review)
            
            # 6. 发送完成通知
            if self.notification_service:
                await self._send_review_completed_notifications(review)
            
            # 7. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=moderator_id,
                    operation="COMPLETE_REVIEW",
                    resource_type="requirement_review",
                    resource_id=review_id,
                    details={
                        "requirement_id": review.requirement_id,
                        "decision": decision.value,
                        "summary": summary
                    }
                )
            
            logger.info(f"评审完成: {review_id}, 决策: {decision.value}")
            return review
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"完成评审失败: {str(e)}")
            raise BusinessLogicError(f"完成评审失败: {str(e)}")
    
    async def cancel_review(self, review_id: int, reason: str, cancelled_by: int) -> RequirementReview:
        """
        取消评审
        
        Args:
            review_id: 评审ID
            reason: 取消原因
            cancelled_by: 取消人ID
            
        Returns:
            取消的评审对象
        """
        try:
            # 1. 获取评审
            review = await self._get_review_by_id(review_id)
            
            # 2. 验证取消权限
            if not await self._has_cancel_permission(review, cancelled_by):
                raise PermissionError("没有取消评审的权限")
            
            if review.review_status == ReviewStatus.COMPLETED:
                raise BusinessLogicError("已完成的评审不能取消")
            
            # 3. 更新评审状态
            review.review_status = ReviewStatus.CANCELLED
            review.summary = f"评审取消: {reason}"
            review.completed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(review)
            
            # 4. 恢复需求状态
            await self.requirement_repo.update_requirement_status(
                review.requirement_id,
                requirement.RequirementStatus.DRAFT,
                cancelled_by,
                f"评审取消: {reason}"
            )
            
            # 5. 发送取消通知
            if self.notification_service:
                await self._send_review_cancelled_notifications(review, reason)
            
            # 6. 记录审计日志
            if self.audit_service:
                await self.audit_service.log_operation(
                    user_id=cancelled_by,
                    operation="CANCEL_REVIEW",
                    resource_type="requirement_review",
                    resource_id=review_id,
                    details={
                        "requirement_id": review.requirement_id,
                        "reason": reason
                    }
                )
            
            logger.info(f"评审取消: {review_id}, 原因: {reason}")
            return review
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"取消评审失败: {str(e)}")
            raise BusinessLogicError(f"取消评审失败: {str(e)}")
    
    async def get_review_by_id(self, review_id: int) -> Optional[RequirementReview]:
        """根据ID获取评审（不存在时返回 None，由路由层转为 404）。"""
        result = await self.db.execute(
            select(RequirementReview).where(RequirementReview.id == review_id)
        )
        return result.scalar_one_or_none()
    
    async def get_reviews_by_requirement(self, requirement_id: int) -> List[RequirementReview]:
        """获取需求的所有评审"""
        result = await self.db.execute(
            select(RequirementReview)
            .where(RequirementReview.requirement_id == requirement_id)
            .order_by(RequirementReview.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_review_comments(self, review_id: int) -> List[RequirementReviewComment]:
        """获取评审意见列表"""
        result = await self.db.execute(
            select(RequirementReviewComment)
            .where(RequirementReviewComment.review_id == review_id)
            .order_by(RequirementReviewComment.created_at.asc())
        )
        return result.scalars().all()
    
    async def get_reviewer_reviews(self, reviewer_id: int, status: Optional[ReviewStatus] = None) -> List[RequirementReview]:
        """获取评审人的评审列表"""
        query = select(RequirementReview).filter(
            or_(
                RequirementReview.moderator_id == reviewer_id,
                RequirementReview.reviewers.contains([reviewer_id])
            )
        )
        
        if status:
            query = query.filter(RequirementReview.review_status == status)
        
        result = await self.db.execute(query.order_by(RequirementReview.created_at.desc()))
        return result.scalars().all()
    
    async def get_review_statistics(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """获取评审统计信息"""
        # 基础查询条件
        base_conditions = []
        if project_id:
            base_conditions.append(Requirement.project_id == project_id)

        # 状态统计
        status_stats = {}
        for status in ReviewStatus:
            stmt = select(func.count(RequirementReview.id)).where(
                RequirementReview.review_status == status
            )
            if base_conditions:
                stmt = stmt.join(Requirement).where(*base_conditions)
            count_result = await self.db.execute(stmt)
            status_stats[status.value] = count_result.scalar()

        # 决策统计
        decision_stats = {}
        for decision in ReviewDecision:
            stmt = select(func.count(RequirementReview.id)).where(
                RequirementReview.decision == decision
            )
            if base_conditions:
                stmt = stmt.join(Requirement).where(*base_conditions)
            count_result = await self.db.execute(stmt)
            decision_stats[decision.value] = count_result.scalar()

        # 总数统计
        total_stmt = select(func.count(RequirementReview.id))
        if base_conditions:
            total_stmt = total_stmt.join(Requirement).where(*base_conditions)
        total_result = await self.db.execute(total_stmt)
        total_reviews = total_result.scalar()
        
        return {
            "total_reviews": total_reviews,
            "status_distribution": status_stats,
            "decision_distribution": decision_stats,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # 私有方法
    
    async def _get_review_by_id(self, review_id: int) -> RequirementReview:
        """根据ID获取评审"""
        result = await self.db.execute(
            select(RequirementReview).where(RequirementReview.id == review_id)
        )
        review = result.scalar_one_or_none()
        if not review:
            raise NotFoundError(f"评审不存在: {review_id}")
        return review
    
    async def _get_comment_by_id(self, comment_id: int) -> RequirementReviewComment:
        """根据ID获取评审意见"""
        result = await self.db.execute(
            select(RequirementReviewComment).where(RequirementReviewComment.id == comment_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            raise NotFoundError(f"评审意见不存在: {comment_id}")
        return comment
    
    async def _get_active_review_for_requirement(self, requirement_id: int) -> Optional[RequirementReview]:
        """获取需求的活跃评审"""
        result = await self.db.execute(
            select(RequirementReview)
            .where(
                and_(
                    RequirementReview.requirement_id == requirement_id,
                    RequirementReview.review_status.in_([ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS])
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _validate_review_data(self, review_data: Dict[str, Any]):
        """验证评审数据"""
        required_fields = ['requirement_id', 'review_type', 'title', 'moderator_id']
        
        for field in required_fields:
            if field not in review_data or not review_data[field]:
                raise ValidationError(f"必填字段缺失: {field}")
        
        # 验证枚举值
        try:
            ReviewType(review_data['review_type'])
        except ValueError:
            raise ValidationError(f"无效的评审类型: {review_data['review_type']}")
        
        # 验证评审人员
        if 'reviewers' in review_data and review_data['reviewers']:
            if not isinstance(review_data['reviewers'], list):
                raise ValidationError("评审人员必须是列表格式")
            
            if review_data['moderator_id'] in review_data['reviewers']:
                raise ValidationError("主持人不能同时是评审人")
    
    async def _has_review_permission(self, review: RequirementReview, user_id: int) -> bool:
        """检查是否有评审权限"""
        return (user_id == review.moderator_id or 
                user_id in (review.reviewers or []))
    
    async def _has_resolve_permission(self, comment: RequirementReviewComment, user_id: int) -> bool:
        """检查是否有解决意见的权限"""
        # 需求负责人、评审主持人、意见提交人可以解决意见
        review = await self._get_review_by_id(comment.review_id)
        requirement = await self.requirement_repo.get_by_id(comment.requirement_id)
        
        return (user_id == review.moderator_id or 
                user_id == comment.reviewer_id or
                (requirement and user_id == requirement.assignee_id))
    
    async def _has_cancel_permission(self, review: RequirementReview, user_id: int) -> bool:
        """检查是否有取消评审的权限"""
        # 主持人、需求创建人、项目管理员可以取消评审
        requirement = await self.requirement_repo.get_by_id(review.requirement_id)
        
        return (user_id == review.moderator_id or 
                user_id == review.created_by or
                (requirement and user_id == requirement.creator_id))
    
    async def _validate_review_completeness(self, review_id: int):
        """验证评审完整性"""
        # 检查是否所有评审人都已提交意见
        review = await self._get_review_by_id(review_id)
        
        if not review.reviewers:
            return  # 没有指定评审人，跳过检查
        
        # 获取已提交意见的评审人
        result = await self.db.execute(
            self.db.query(RequirementReviewComment.reviewer_id)
            .filter(RequirementReviewComment.review_id == review_id)
            .distinct()
        )
        submitted_reviewers = [row[0] for row in result.fetchall()]
        
        # 检查是否所有评审人都已提交
        missing_reviewers = set(review.reviewers) - set(submitted_reviewers)
        if missing_reviewers:
            logger.warning(f"评审 {review_id} 还有评审人未提交意见: {missing_reviewers}")
            # 这里可以选择是否强制要求所有人都提交意见
    
    def _get_requirement_status_by_decision(self, decision: ReviewDecision) -> 'RequirementStatus':
        """根据评审决策确定需求状态"""
        from ..models.requirement import RequirementStatus
        
        status_mapping = {
            ReviewDecision.APPROVED: RequirementStatus.APPROVED,
            ReviewDecision.APPROVED_WITH_MINOR_CHANGES: RequirementStatus.APPROVED,
            ReviewDecision.NEEDS_MAJOR_REVISION: RequirementStatus.NEEDS_REVISION,
            ReviewDecision.REJECTED: RequirementStatus.CANCELLED
        }
        return status_mapping.get(decision, RequirementStatus.NEEDS_REVISION)
    
    async def _analyze_review_comment_with_ai(self, content: str, suggestion: str = "") -> ReviewAnalysis:
        """使用AI分析评审意见"""
        try:
            prompt = f"""
            请分析以下评审意见，并提供分类建议：
            
            意见内容: {content}
            改进建议: {suggestion}
            
            请从以下维度进行分析：
            1. 意见类型 (ISSUE/SUGGESTION/QUESTION/APPROVAL/REJECTION)
            2. 严重程度 (CRITICAL/MAJOR/MINOR/TRIVIAL)
            3. 发现的质量问题
            4. 改进建议
            
            请以JSON格式返回结果。
            """
            
            response = await self.ai_router_service.route_request(
                prompt=prompt,
                task_type=TaskType.TEXT_ANALYSIS,
                user_id=1,  # 系统用户
                max_tokens=500
            )
            
            import json
            result = json.loads(response.get('content', '{}'))
            
            return ReviewAnalysis(
                suggested_severity=CommentSeverity(result.get('severity', 'MINOR')),
                suggested_type=CommentType(result.get('comment_type', 'SUGGESTION')),
                quality_issues=result.get('quality_issues', []),
                improvement_suggestions=result.get('improvement_suggestions', [])
            )
            
        except Exception as e:
            logger.warning(f"AI意见分析失败: {str(e)}")
            # 返回默认分析结果
            return ReviewAnalysis(
                suggested_severity=CommentSeverity.MINOR,
                suggested_type=CommentType.SUGGESTION,
                quality_issues=[],
                improvement_suggestions=[]
            )
    
    async def _generate_review_report(self, review: RequirementReview):
        """生成评审报告"""
        try:
            # 获取评审意见
            comments = await self.get_review_comments(review.id)
            
            # 统计信息
            total_comments = len(comments)
            issue_comments = len([c for c in comments if c.comment_type == CommentType.ISSUE])
            critical_issues = len([c for c in comments if c.severity == CommentSeverity.CRITICAL])
            
            # 生成报告内容
            report = {
                "review_id": review.id,
                "requirement_id": review.requirement_id,
                "review_type": review.review_type.value,
                "decision": review.decision.value if review.decision else None,
                "summary": review.summary,
                "statistics": {
                    "total_comments": total_comments,
                    "issue_comments": issue_comments,
                    "critical_issues": critical_issues,
                    "reviewers_count": len(review.reviewers or [])
                },
                "comments": [comment.to_dict() for comment in comments],
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # 这里可以将报告保存到文件系统或数据库
            logger.info(f"评审报告生成完成: {review.id}")
            
        except Exception as e:
            logger.error(f"生成评审报告失败: {str(e)}")
    
    async def _send_review_invitations(self, review: RequirementReview):
        """发送评审邀请通知"""
        if not self.notification_service:
            return
        
        try:
            # 通知主持人
            await self.notification_service.send_review_invitation(
                review.moderator_id,
                review,
                role="moderator"
            )
            
            # 通知评审人
            for reviewer_id in (review.reviewers or []):
                await self.notification_service.send_review_invitation(
                    reviewer_id,
                    review,
                    role="reviewer"
                )
                
        except Exception as e:
            logger.error(f"发送评审邀请失败: {str(e)}")
    
    async def _send_review_started_notifications(self, review: RequirementReview):
        """发送评审开始通知"""
        if not self.notification_service:
            return
        
        try:
            # 通知所有评审人
            for reviewer_id in (review.reviewers or []):
                await self.notification_service.send_review_started(reviewer_id, review)
                
        except Exception as e:
            logger.error(f"发送评审开始通知失败: {str(e)}")
    
    async def _send_comment_notifications(self, comment: RequirementReviewComment):
        """发送评审意见通知"""
        if not self.notification_service:
            return
        
        try:
            review = await self._get_review_by_id(comment.review_id)
            
            # 通知主持人
            if comment.reviewer_id != review.moderator_id:
                await self.notification_service.send_comment_notification(
                    review.moderator_id,
                    comment,
                    role="moderator"
                )
            
            # 通知需求负责人
            requirement = await self.requirement_repo.get_by_id(comment.requirement_id)
            if (requirement and requirement.assignee_id and 
                requirement.assignee_id != comment.reviewer_id):
                await self.notification_service.send_comment_notification(
                    requirement.assignee_id,
                    comment,
                    role="assignee"
                )
                
        except Exception as e:
            logger.error(f"发送评审意见通知失败: {str(e)}")
    
    async def _send_comment_resolved_notifications(self, comment: RequirementReviewComment):
        """发送意见解决通知"""
        if not self.notification_service:
            return
        
        try:
            # 通知意见提交人
            if comment.resolved_by != comment.reviewer_id:
                await self.notification_service.send_comment_resolved(
                    comment.reviewer_id,
                    comment
                )
                
        except Exception as e:
            logger.error(f"发送意见解决通知失败: {str(e)}")
    
    async def _send_review_completed_notifications(self, review: RequirementReview):
        """发送评审完成通知"""
        if not self.notification_service:
            return
        
        try:
            # 通知所有参与人员
            all_participants = set([review.moderator_id] + (review.reviewers or []))
            
            for participant_id in all_participants:
                await self.notification_service.send_review_completed(
                    participant_id,
                    review
                )
            
            # 通知需求相关人员
            requirement = await self.requirement_repo.get_by_id(review.requirement_id)
            if requirement:
                if requirement.creator_id not in all_participants:
                    await self.notification_service.send_review_completed(
                        requirement.creator_id,
                        review
                    )
                
                if (requirement.assignee_id and 
                    requirement.assignee_id not in all_participants):
                    await self.notification_service.send_review_completed(
                        requirement.assignee_id,
                        review
                    )
                    
        except Exception as e:
            logger.error(f"发送评审完成通知失败: {str(e)}")
    
    async def _send_review_cancelled_notifications(self, review: RequirementReview, reason: str):
        """发送评审取消通知"""
        if not self.notification_service:
            return
        
        try:
            # 通知所有参与人员
            all_participants = set([review.moderator_id] + (review.reviewers or []))
            
            for participant_id in all_participants:
                await self.notification_service.send_review_cancelled(
                    participant_id,
                    review,
                    reason
                )
                
        except Exception as e:
            logger.error(f"发送评审取消通知失败: {str(e)}")