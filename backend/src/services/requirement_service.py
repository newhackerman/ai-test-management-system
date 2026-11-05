"""
需求管理核心服务

提供需求管理的核心业务逻辑，包括：
- 需求创建、更新、删除功能
- 需求状态管理和流转控制
- 需求质量分析和验证
- 需求生命周期管理
"""
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.requirement import (
    Requirement, RequirementStatus, RequirementType, Priority, BusinessValue, Complexity,
    RequirementStatusHistory
)
from ..models.project import Project
from ..repositories.requirement_repository import RequirementRepository
from ..services.audit_service import AuditService
from ..services.ai_router_service import AIRouterService, TaskType
from ..services.system_notification_service import SystemNotificationService
from ..core.exceptions import ValidationError, BusinessLogicError, NotFoundError

logger = logging.getLogger(__name__)


class RequirementQualityAnalysis:
    """需求质量分析结果"""
    
    def __init__(self, quality_score: float, completeness_score: float, 
                 complexity_estimate: Complexity, effort_estimate: float,
                 issues: List[str], suggestions: List[str]):
        self.quality_score = quality_score
        self.completeness_score = completeness_score
        self.complexity_estimate = complexity_estimate
        self.effort_estimate = effort_estimate
        self.issues = issues
        self.suggestions = suggestions


class RequirementService:
    """需求管理核心服务"""
    
    # 状态流转规则定义
    STATUS_TRANSITIONS = {
        RequirementStatus.DRAFT: [RequirementStatus.PENDING_REVIEW, RequirementStatus.CANCELLED],
        RequirementStatus.PENDING_REVIEW: [RequirementStatus.REVIEWING, RequirementStatus.DRAFT, RequirementStatus.CANCELLED],
        RequirementStatus.REVIEWING: [RequirementStatus.APPROVED, RequirementStatus.NEEDS_REVISION, RequirementStatus.CANCELLED],
        RequirementStatus.NEEDS_REVISION: [RequirementStatus.PENDING_REVIEW, RequirementStatus.CANCELLED],
        RequirementStatus.APPROVED: [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.CANCELLED],
        RequirementStatus.IN_DEVELOPMENT: [RequirementStatus.TESTING, RequirementStatus.PAUSED, RequirementStatus.NEEDS_REVISION],
        RequirementStatus.PAUSED: [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.CANCELLED],
        RequirementStatus.TESTING: [RequirementStatus.COMPLETED, RequirementStatus.TEST_FAILED],
        RequirementStatus.TEST_FAILED: [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.CANCELLED],
        RequirementStatus.COMPLETED: [RequirementStatus.DEPLOYED, RequirementStatus.NEEDS_REVISION],
        RequirementStatus.DEPLOYED: [RequirementStatus.CLOSED],
        RequirementStatus.CLOSED: [RequirementStatus.DEPLOYED],  # 允许重新打开
        RequirementStatus.CANCELLED: [RequirementStatus.DRAFT]  # 允许重新激活
    }
    
    def __init__(self, db: AsyncSession, ai_router_service: Optional[AIRouterService] = None, 
                 audit_service: Optional[AuditService] = None):
        self.db = db
        self.requirement_repo = RequirementRepository(db)
        self.ai_router_service = ai_router_service
        self.audit_service = audit_service
    
    async def create_requirement(self, requirement_data: Dict[str, Any], creator_id: int) -> Requirement:
        """
        创建需求
        
        Args:
            requirement_data: 需求数据
            creator_id: 创建人ID
            
        Returns:
            创建的需求对象
            
        Raises:
            ValidationError: 数据验证失败
            BusinessLogicError: 业务逻辑错误
        """
        try:
            # 1. 验证需求数据
            await self._validate_requirement_data(requirement_data)
            
            # 2. 生成需求编码
            requirement_code = await self._generate_requirement_code(requirement_data.get('project_id'))
            
            # 3. AI质量检查（如果AI服务可用）
            quality_analysis = None
            if self.ai_router_service:
                quality_analysis = await self._analyze_requirement_quality_with_ai(
                    title=requirement_data.get('title') or '',
                    description=requirement_data.get('description') or '',
                    acceptance_criteria=requirement_data.get('acceptance_criteria') or ''
                )
            
            # 4. 创建需求实体
            requirement = Requirement(
                requirement_code=requirement_code,
                project_id=requirement_data['project_id'],
                parent_id=requirement_data.get('parent_id'),
                title=requirement_data['title'],
                description=requirement_data.get('description'),
                acceptance_criteria=requirement_data.get('acceptance_criteria'),
                requirement_type=RequirementType(requirement_data['requirement_type']),
                category=requirement_data.get('category'),
                priority=Priority(requirement_data.get('priority', Priority.MEDIUM.value)),
                business_value=BusinessValue(requirement_data.get('business_value', BusinessValue.NORMAL.value)),
                complexity=quality_analysis.complexity_estimate if quality_analysis else None,
                estimated_effort=quality_analysis.effort_estimate if quality_analysis else requirement_data.get('estimated_effort'),
                quality_score=quality_analysis.quality_score if quality_analysis else None,
                completeness_score=quality_analysis.completeness_score if quality_analysis else None,
                creator_id=creator_id,
                assignee_id=requirement_data.get('assignee_id'),
                reviewer_id=requirement_data.get('reviewer_id'),
                planned_start_date=requirement_data.get('planned_start_date'),
                planned_end_date=requirement_data.get('planned_end_date'),
                tags=requirement_data.get('tags'),
                custom_fields=requirement_data.get('custom_fields'),
                attachments=requirement_data.get('attachments')
            )
            
            # 5. 保存需求
            created_requirement = await self.requirement_repo.create(requirement)
            
            # 6. 记录审计日志
            await self._log_audit_operation(
                user_id=creator_id,
                action="CREATE_REQUIREMENT",
                resource_id=created_requirement.id,
                details={
                    "requirement_code": created_requirement.requirement_code,
                    "title": created_requirement.title,
                    "project_id": created_requirement.project_id
                }
            )
            
            logger.info(f"需求创建成功: {created_requirement.requirement_code}")
            await self._send_assignment_notifications(
                requirement=created_requirement,
                sender_id=creator_id,
                old_assignee_id=None,
                old_reviewer_id=None,
            )
            return created_requirement
            
        except Exception as e:
            logger.error(f"创建需求失败: {str(e)}")
            raise BusinessLogicError(f"创建需求失败: {str(e)}")
    
    async def update_requirement(self, requirement_id: int, update_data: Dict[str, Any], 
                               updated_by: int) -> Requirement:
        """
        更新需求
        
        Args:
            requirement_id: 需求ID
            update_data: 更新数据
            updated_by: 更新人ID
            
        Returns:
            更新后的需求对象
            
        Raises:
            NotFoundError: 需求不存在
            ValidationError: 数据验证失败
        """
        try:
            # 1. 获取需求
            requirement = await self.requirement_repo.get_by_id(requirement_id)
            if not requirement:
                raise NotFoundError(f"需求不存在: {requirement_id}")
            
            # 2. 验证更新权限
            await self._validate_update_permission(requirement, updated_by)
            
            # 3. 记录变更前的状态
            old_data = requirement.to_dict()
            
            # 4. 更新需求字段
            for field, value in update_data.items():
                if hasattr(requirement, field) and field not in ['id', 'requirement_code', 'created_at']:
                    # 处理枚举类型
                    if field == 'requirement_type' and value:
                        value = RequirementType(value)
                    elif field == 'priority' and value:
                        value = Priority(value)
                    elif field == 'business_value' and value:
                        value = BusinessValue(value)
                    elif field == 'complexity' and value:
                        value = Complexity(value)
                    elif field == 'status' and value:
                        value = RequirementStatus(value)
                    
                    setattr(requirement, field, value)
            
            # 5. 设置更新信息
            requirement.updated_by = updated_by
            requirement.updated_at = datetime.utcnow()
            requirement.version += 1
            
            # 6. 保存更新
            updated_requirement = await self.requirement_repo.update(requirement)
            
            # 7. 记录审计日志
            await self._log_audit_operation(
                user_id=updated_by,
                action="UPDATE_REQUIREMENT",
                resource_id=requirement_id,
                details={
                    "old_data": old_data,
                    "new_data": updated_requirement.to_dict(),
                    "changes": update_data
                }
            )
            
            logger.info(f"需求更新成功: {updated_requirement.requirement_code}")
            await self._send_assignment_notifications(
                requirement=updated_requirement,
                sender_id=updated_by,
                old_assignee_id=old_data.get("assignee_id"),
                old_reviewer_id=old_data.get("reviewer_id"),
            )
            return updated_requirement
            
        except Exception as e:
            logger.error(f"更新需求失败: {str(e)}")
            raise BusinessLogicError(f"更新需求失败: {str(e)}")
    
    async def delete_requirement(self, requirement_id: int, deleted_by: int) -> bool:
        """
        删除需求
        
        Args:
            requirement_id: 需求ID
            deleted_by: 删除人ID
            
        Returns:
            是否删除成功
            
        Raises:
            NotFoundError: 需求不存在
            BusinessLogicError: 业务逻辑错误
        """
        try:
            # 1. 获取需求
            requirement = await self.requirement_repo.get_by_id(requirement_id)
            if not requirement:
                raise NotFoundError(f"需求不存在: {requirement_id}")
            
            # 2. 验证删除权限
            await self._validate_delete_permission(requirement, deleted_by)
            
            # 3. 检查依赖关系
            children = await self.requirement_repo.get_children_requirements(requirement_id)
            if children:
                raise BusinessLogicError(f"需求存在子需求，无法删除")
            
            # 4. 记录删除前的数据
            requirement_data = requirement.to_dict()
            
            # 5. 执行删除
            deleted = await self.requirement_repo.delete(requirement_id)
            
            # 6. 记录审计日志
            if deleted:
                await self._log_audit_operation(
                    user_id=deleted_by,
                    action="DELETE_REQUIREMENT",
                    resource_id=requirement_id,
                    details={
                        "deleted_requirement": requirement_data
                    }
                )
            
            logger.info(f"需求删除成功: {requirement.requirement_code}")
            return deleted
            
        except Exception as e:
            logger.error(f"删除需求失败: {str(e)}")
            raise BusinessLogicError(f"删除需求失败: {str(e)}")
    
    async def update_requirement_status(self, requirement_id: int, new_status: RequirementStatus, 
                                      changed_by: int, reason: str = None) -> Requirement:
        """
        更新需求状态
        
        Args:
            requirement_id: 需求ID
            new_status: 新状态
            changed_by: 变更人ID
            reason: 变更原因
            
        Returns:
            更新后的需求对象
            
        Raises:
            NotFoundError: 需求不存在
            BusinessLogicError: 状态流转不合法
        """
        try:
            # 1. 获取需求
            requirement = await self.requirement_repo.get_by_id(requirement_id)
            if not requirement:
                raise NotFoundError(f"需求不存在: {requirement_id}")
            
            # 2. 验证状态流转
            if not self._is_valid_status_transition(requirement.status, new_status):
                raise BusinessLogicError(
                    f"不能从{requirement.status.value}状态转换到{new_status.value}状态"
                )
            
            # 3. 检查前置条件
            await self._validate_status_change_preconditions(requirement, new_status)
            
            # 4. 更新状态
            success = await self.requirement_repo.update_requirement_status(
                requirement_id, new_status, changed_by, reason
            )
            
            if not success:
                raise BusinessLogicError("状态更新失败")
            
            # 5. 执行状态变更后置动作
            await self._execute_status_change_actions(requirement, requirement.status, new_status)
            
            # 6. 获取更新后的需求
            updated_requirement = await self.requirement_repo.get_by_id(requirement_id)
            
            # 7. 记录审计日志
            await self._log_audit_operation(
                user_id=changed_by,
                action="UPDATE_REQUIREMENT_STATUS",
                resource_id=requirement_id,
                details={
                    "old_status": requirement.status.value,
                    "new_status": new_status.value,
                    "reason": reason
                }
            )
            
            logger.info(f"需求状态更新成功: {requirement.requirement_code} {requirement.status.value} -> {new_status.value}")
            return updated_requirement
            
        except Exception as e:
            logger.error(f"更新需求状态失败: {str(e)}")
            raise BusinessLogicError(f"更新需求状态失败: {str(e)}")
    
    async def get_requirement_by_id(self, requirement_id: int) -> Optional[Requirement]:
        """根据ID获取需求"""
        return await self.requirement_repo.get_by_id(requirement_id)
    
    async def get_requirement_by_code(self, requirement_code: str) -> Optional[Requirement]:
        """根据需求编码获取需求"""
        return await self.requirement_repo.get_by_code(requirement_code)
    
    async def search_requirements(self, search_params: Dict[str, Any]) -> Tuple[List[Requirement], int]:
        """搜索需求"""
        return await self.requirement_repo.search_requirements(search_params)
    
    async def get_project_requirements(self, project_id: int, skip: int = 0, limit: int = 100) -> List[Requirement]:
        """获取项目需求列表"""
        return await self.requirement_repo.get_by_project_id(project_id, skip, limit)
    
    async def get_requirements_statistics(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """获取需求统计信息"""
        return await self.requirement_repo.get_requirements_statistics(project_id)
    
    async def analyze_requirement_quality(self, requirement_id: int) -> RequirementQualityAnalysis:
        """
        分析需求质量
        
        Args:
            requirement_id: 需求ID
            
        Returns:
            需求质量分析结果
        """
        requirement = await self.requirement_repo.get_by_id(requirement_id)
        if not requirement:
            raise NotFoundError(f"需求不存在: {requirement_id}")
        
        if self.ai_router_service:
            # 使用AI分析需求质量
            analysis = await self._analyze_requirement_quality_with_ai(
                title=requirement.title,
                description=requirement.description or '',
                acceptance_criteria=requirement.acceptance_criteria or ''
            )
            
            # 更新需求质量评分
            requirement.quality_score = analysis.quality_score
            requirement.completeness_score = analysis.completeness_score
            await self.requirement_repo.update(requirement)
            
            return analysis
        else:
            # 基础质量分析
            return await self._analyze_requirement_quality_basic(requirement)
    
    # 私有方法

    async def _send_assignment_notifications(
        self,
        *,
        requirement: Requirement,
        sender_id: int,
        old_assignee_id: Optional[int],
        old_reviewer_id: Optional[int],
    ) -> None:
        """Create unread in-app notifications when requirement assignee or reviewer is set."""
        recipients: Dict[int, List[str]] = {}

        if requirement.assignee_id and int(requirement.assignee_id) != int(old_assignee_id or 0):
            recipients.setdefault(int(requirement.assignee_id), []).append("负责人")

        if requirement.reviewer_id and int(requirement.reviewer_id) != int(old_reviewer_id or 0):
            recipients.setdefault(int(requirement.reviewer_id), []).append("评审人")

        if not recipients:
            return

        try:
            project_name_result = await self.db.execute(
                select(Project.project_name).where(Project.id == requirement.project_id)
            )
            project_name = project_name_result.scalar_one_or_none() or f"项目#{requirement.project_id}"
            service = SystemNotificationService(self.db)

            for user_id, roles in recipients.items():
                role_text = "、".join(roles)
                await service.create_notification(
                    user_id=user_id,
                    sender_id=sender_id,
                    category="requirement_assignment",
                    title=f"你有新的需求{role_text}安排",
                    content=f"需求“{requirement.title}”已将你设置为{role_text}，所属项目：{project_name}。",
                    related_type="requirement",
                    related_id=requirement.id,
                    payload={
                        "requirement_id": requirement.id,
                        "requirement_code": requirement.requirement_code,
                        "requirement_title": requirement.title,
                        "project_id": requirement.project_id,
                        "project_name": project_name,
                        "roles": roles,
                    },
                    commit=True,
                )
        except Exception as exc:
            logger.warning(f"创建需求分配通知失败: {exc}")

    async def _log_audit_operation(
        self,
        user_id: int,
        action: str,
        resource_id: int,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录需求操作审计日志；审计失败不能影响主业务。"""
        logger.debug(
            "需求审计事件: action=%s user_id=%s resource_id=%s details=%s",
            action,
            user_id,
            resource_id,
            details,
        )
    
    async def _validate_requirement_data(self, requirement_data: Dict[str, Any]):
        """验证需求数据"""
        required_fields = ['project_id', 'title', 'requirement_type']
        
        for field in required_fields:
            if field not in requirement_data or not requirement_data[field]:
                raise ValidationError(f"必填字段缺失: {field}")
        
        # 验证项目存在性（不存在的项目下不得创建需求，避免产生孤儿需求）
        project = (
            await self.db.execute(
                select(Project).where(Project.id == requirement_data['project_id'])
            )
        ).scalar_one_or_none()
        if not project:
            raise ValidationError(f"项目不存在: {requirement_data['project_id']}")

        # 验证枚举值
        if 'requirement_type' in requirement_data:
            try:
                RequirementType(requirement_data['requirement_type'])
            except ValueError:
                raise ValidationError(f"无效的需求类型: {requirement_data['requirement_type']}")
        
        if 'priority' in requirement_data and requirement_data['priority']:
            try:
                Priority(requirement_data['priority'])
            except ValueError:
                raise ValidationError(f"无效的优先级: {requirement_data['priority']}")
        
        # 验证父需求存在性
        if 'parent_id' in requirement_data and requirement_data['parent_id']:
            parent = await self.requirement_repo.get_by_id(requirement_data['parent_id'])
            if not parent:
                raise ValidationError(f"父需求不存在: {requirement_data['parent_id']}")
            
            if parent.project_id != requirement_data['project_id']:
                raise ValidationError("父需求必须属于同一项目")
    
    async def _generate_requirement_code(self, project_id: int) -> str:
        """生成需求编码"""
        today = datetime.now().strftime("%Y%m%d")
        count = await self.requirement_repo.count_requirements_by_project_and_date(project_id, today)
        return f"REQ-{project_id:04d}-{today}-{count + 1:03d}"
    
    def _is_valid_status_transition(self, current_status: RequirementStatus, new_status: RequirementStatus) -> bool:
        """验证状态流转是否合法"""
        if current_status == new_status:
            return True
        
        allowed_transitions = self.STATUS_TRANSITIONS.get(current_status, [])
        return new_status in allowed_transitions
    
    async def _validate_status_change_preconditions(self, requirement: Requirement, new_status: RequirementStatus):
        """验证状态变更前置条件"""
        # 根据目标状态检查前置条件
        if new_status == RequirementStatus.APPROVED:
            # 批准前需要有完整的验收标准
            if not requirement.acceptance_criteria:
                raise BusinessLogicError("批准需求前必须定义验收标准")
        
        elif new_status == RequirementStatus.IN_DEVELOPMENT:
            # 开发前需要有负责人
            if not requirement.assignee_id:
                raise BusinessLogicError("开始开发前必须指定负责人")
        
        elif new_status == RequirementStatus.TESTING:
            # 测试前需要有计划完成日期
            if not requirement.planned_end_date:
                raise BusinessLogicError("进入测试前必须设置计划完成日期")
    
    async def _execute_status_change_actions(self, requirement: Requirement, 
                                           old_status: RequirementStatus, new_status: RequirementStatus):
        """执行状态变更后置动作"""
        # 根据状态变更执行相应动作
        if new_status == RequirementStatus.IN_DEVELOPMENT and not requirement.actual_start_date:
            # 开始开发时设置实际开始日期
            requirement.actual_start_date = date.today()
            await self.requirement_repo.update(requirement)
        
        elif new_status == RequirementStatus.COMPLETED and not requirement.actual_end_date:
            # 完成时设置实际完成日期
            requirement.actual_end_date = date.today()
            await self.requirement_repo.update(requirement)
    
    async def _validate_update_permission(self, requirement: Requirement, user_id: int):
        """验证更新权限"""
        # 基础权限检查 - 创建人和负责人可以更新
        if requirement.creator_id != user_id and requirement.assignee_id != user_id:
            # 这里可以集成更复杂的权限系统
            pass
    
    async def _validate_delete_permission(self, requirement: Requirement, user_id: int):
        """验证删除权限"""
        # 只有创建人可以删除草稿状态的需求
        if requirement.status != RequirementStatus.DRAFT:
            raise BusinessLogicError("只能删除草稿状态的需求")
        
        if requirement.creator_id != user_id:
            raise BusinessLogicError("只有创建人可以删除需求")
    
    async def _analyze_requirement_quality_with_ai(self, title: str, description: str, 
                                                 acceptance_criteria: str) -> RequirementQualityAnalysis:
        """使用AI分析需求质量"""
        try:
            # 构建分析提示词
            prompt = f"""
            请分析以下需求的质量，并提供评分和建议：
            
            标题: {title}
            描述: {description}
            验收标准: {acceptance_criteria}
            
            请从以下维度进行分析：
            1. 质量评分 (0-10分)
            2. 完整性评分 (0-10分)
            3. 复杂度估算 (SIMPLE/MEDIUM/COMPLEX/VERY_COMPLEX)
            4. 工作量估算 (人天)
            5. 发现的问题
            6. 改进建议
            
            请以JSON格式返回结果。
            """
            
            # 调用AI服务
            response = await self.ai_router_service.route_request(
                prompt=prompt,
                task_type=TaskType.COMPLEX_ANALYSIS,
                user_id=1,  # 系统用户
                max_tokens=1000
            )
            
            # 解析AI响应
            import json
            result = json.loads(response.get('content', '{}'))
            
            return RequirementQualityAnalysis(
                quality_score=result.get('quality_score', 5.0),
                completeness_score=result.get('completeness_score', 5.0),
                complexity_estimate=Complexity(result.get('complexity', 'MEDIUM')),
                effort_estimate=result.get('effort_estimate', 1.0),
                issues=result.get('issues', []),
                suggestions=result.get('suggestions', [])
            )
            
        except Exception as e:
            logger.warning(f"AI质量分析失败，使用基础分析: {str(e)}")
            # 降级到基础分析
            return await self._analyze_requirement_quality_basic_from_text(title, description, acceptance_criteria)
    
    async def _analyze_requirement_quality_basic(self, requirement: Requirement) -> RequirementQualityAnalysis:
        """基础需求质量分析"""
        return await self._analyze_requirement_quality_basic_from_text(
            requirement.title,
            requirement.description or '',
            requirement.acceptance_criteria or ''
        )
    
    async def _analyze_requirement_quality_basic_from_text(self, title: str, description: str, 
                                                         acceptance_criteria: str) -> RequirementQualityAnalysis:
        """基于文本的基础需求质量分析"""
        title = title or ''
        description = description or ''
        acceptance_criteria = acceptance_criteria or ''
        issues = []
        suggestions = []
        
        # 基础质量检查
        quality_score = 5.0
        completeness_score = 5.0
        
        # 标题检查
        if len(title) < 5:
            issues.append("需求标题过短")
            quality_score -= 1
        elif len(title) > 100:
            issues.append("需求标题过长")
            quality_score -= 0.5
        
        # 描述检查
        if not description:
            issues.append("缺少需求描述")
            completeness_score -= 2
        elif len(description) < 20:
            issues.append("需求描述过于简单")
            completeness_score -= 1
        
        # 验收标准检查
        if not acceptance_criteria:
            issues.append("缺少验收标准")
            completeness_score -= 2
        elif len(acceptance_criteria) < 10:
            issues.append("验收标准过于简单")
            completeness_score -= 1
        
        # 复杂度估算
        text_length = len(title) + len(description) + len(acceptance_criteria)
        if text_length < 100:
            complexity = Complexity.SIMPLE
            effort_estimate = 1.0
        elif text_length < 300:
            complexity = Complexity.MEDIUM
            effort_estimate = 3.0
        elif text_length < 600:
            complexity = Complexity.COMPLEX
            effort_estimate = 5.0
        else:
            complexity = Complexity.VERY_COMPLEX
            effort_estimate = 8.0
        
        # 生成建议
        if not description:
            suggestions.append("添加详细的需求描述")
        if not acceptance_criteria:
            suggestions.append("定义明确的验收标准")
        if len(title) < 5:
            suggestions.append("完善需求标题")
        
        return RequirementQualityAnalysis(
            quality_score=max(0, min(10, quality_score)),
            completeness_score=max(0, min(10, completeness_score)),
            complexity_estimate=complexity,
            effort_estimate=effort_estimate,
            issues=issues,
            suggestions=suggestions
        )
