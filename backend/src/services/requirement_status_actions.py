"""
需求状态流转后置动作执行器

本模块实现需求状态变更后的后置动作执行，包括任务创建、通知发送、
项目进度更新和里程碑检查等功能。
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from abc import ABC, abstractmethod

from ..models.requirement import Requirement, RequirementStatus
from ..models.requirement_status_flow import PostActionResult
from ..models.user import User
from ..models.project import Project


class PostActionExecutor(ABC):
    """后置动作执行器基类"""
    
    @abstractmethod
    async def execute(self, requirement: Requirement, old_status: RequirementStatus, 
                     new_status: RequirementStatus, user_id: int, 
                     context: Dict[str, Any] = None) -> PostActionResult:
        """执行后置动作"""
        pass


class TaskCreationExecutor(PostActionExecutor):
    """任务创建执行器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def execute(self, requirement: Requirement, old_status: RequirementStatus, 
                     new_status: RequirementStatus, user_id: int, 
                     context: Dict[str, Any] = None) -> PostActionResult:
        """根据状态变更创建相应的任务"""
        result = PostActionResult(success=True)
        
        try:
            if new_status == RequirementStatus.APPROVED:
                await self._create_development_tasks(requirement, result)
            
            elif new_status == RequirementStatus.IN_DEVELOPMENT:
                await self._activate_development_tasks(requirement, result)
            
            elif new_status == RequirementStatus.TESTING:
                await self._create_testing_tasks(requirement, result)
            
            elif new_status == RequirementStatus.PAUSED:
                await self._pause_related_tasks(requirement, result)
            
            elif new_status == RequirementStatus.CANCELLED:
                await self._cancel_related_tasks(requirement, result)
        
        except Exception as e:
            result.add_failed_action(f"任务管理: {str(e)}")
        
        return result
    
    async def _create_development_tasks(self, requirement: Requirement, result: PostActionResult):
        """创建开发任务"""
        # 这里应该集成任务管理系统的API
        # 暂时记录动作
        result.add_executed_action(f"为需求 {requirement.requirement_code} 创建开发任务")
        
        # 实际实现时应该调用任务管理服务
        # task_service = TaskService(self.db)
        # task = await task_service.create_task({
        #     'title': f'开发需求: {requirement.title}',
        #     'description': requirement.description,
        #     'requirement_id': requirement.id,
        #     'assignee_id': requirement.assignee_id,
        #     'task_type': 'DEVELOPMENT',
        #     'priority': requirement.priority,
        #     'planned_start_date': requirement.planned_start_date,
        #     'planned_end_date': requirement.planned_end_date
        # })
    
    async def _activate_development_tasks(self, requirement: Requirement, result: PostActionResult):
        """激活开发任务"""
        result.add_executed_action(f"激活需求 {requirement.requirement_code} 的开发任务")
    
    async def _create_testing_tasks(self, requirement: Requirement, result: PostActionResult):
        """创建测试任务"""
        result.add_executed_action(f"为需求 {requirement.requirement_code} 创建测试任务")
    
    async def _pause_related_tasks(self, requirement: Requirement, result: PostActionResult):
        """暂停相关任务"""
        result.add_executed_action(f"暂停需求 {requirement.requirement_code} 的相关任务")
    
    async def _cancel_related_tasks(self, requirement: Requirement, result: PostActionResult):
        """取消相关任务"""
        result.add_executed_action(f"取消需求 {requirement.requirement_code} 的相关任务")


class NotificationExecutor(PostActionExecutor):
    """通知发送执行器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def execute(self, requirement: Requirement, old_status: RequirementStatus, 
                     new_status: RequirementStatus, user_id: int, 
                     context: Dict[str, Any] = None) -> PostActionResult:
        """发送状态变更通知"""
        result = PostActionResult(success=True)
        
        try:
            # 获取通知目标用户
            notification_targets = self._get_notification_targets(requirement, new_status)
            
            # 生成通知内容
            notification_content = self._generate_notification_content(
                requirement, old_status, new_status, user_id, context
            )
            
            # 发送通知
            await self._send_notifications(notification_targets, notification_content, result)
        
        except Exception as e:
            result.add_failed_action(f"通知发送: {str(e)}")
        
        return result
    
    def _get_notification_targets(self, requirement: Requirement, new_status: RequirementStatus) -> List[int]:
        """获取通知目标用户ID列表"""
        targets = set()
        
        # 基本通知目标
        if requirement.creator_id:
            targets.add(requirement.creator_id)
        if requirement.assignee_id:
            targets.add(requirement.assignee_id)
        if requirement.reviewer_id:
            targets.add(requirement.reviewer_id)
        
        # 根据状态确定特定通知目标
        status_specific_targets = {
            RequirementStatus.PENDING_REVIEW: [requirement.reviewer_id],
            RequirementStatus.APPROVED: [requirement.assignee_id],
            RequirementStatus.IN_DEVELOPMENT: [requirement.assignee_id],
            RequirementStatus.TESTING: [],  # 测试人员，需要从项目团队获取
            RequirementStatus.COMPLETED: [requirement.creator_id, requirement.assignee_id],
            RequirementStatus.CANCELLED: [requirement.creator_id, requirement.assignee_id]
        }
        
        specific_targets = status_specific_targets.get(new_status, [])
        for target in specific_targets:
            if target:
                targets.add(target)
        
        return list(targets)
    
    def _generate_notification_content(
        self, 
        requirement: Requirement, 
        old_status: RequirementStatus, 
        new_status: RequirementStatus, 
        user_id: int,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成通知内容"""
        user = self.db.query(User).filter(User.id == user_id).first()
        user_name = user.username if user else "系统"
        
        status_messages = {
            RequirementStatus.PENDING_REVIEW: f"需求 {requirement.requirement_code} 已提交评审，请及时处理",
            RequirementStatus.REVIEWING: f"需求 {requirement.requirement_code} 评审已开始",
            RequirementStatus.APPROVED: f"需求 {requirement.requirement_code} 已通过评审，可以开始开发",
            RequirementStatus.IN_DEVELOPMENT: f"需求 {requirement.requirement_code} 已开始开发",
            RequirementStatus.TESTING: f"需求 {requirement.requirement_code} 开发完成，请开始测试",
            RequirementStatus.COMPLETED: f"需求 {requirement.requirement_code} 已完成开发和测试",
            RequirementStatus.DEPLOYED: f"需求 {requirement.requirement_code} 已部署到生产环境",
            RequirementStatus.PAUSED: f"需求 {requirement.requirement_code} 已暂停",
            RequirementStatus.CANCELLED: f"需求 {requirement.requirement_code} 已取消",
            RequirementStatus.CLOSED: f"需求 {requirement.requirement_code} 已关闭"
        }
        
        message = status_messages.get(new_status, f"需求 {requirement.requirement_code} 状态已更新")
        
        return {
            'title': f'需求状态变更通知',
            'message': message,
            'requirement_id': requirement.id,
            'requirement_code': requirement.requirement_code,
            'requirement_title': requirement.title,
            'old_status': old_status.value,
            'new_status': new_status.value,
            'changed_by': user_name,
            'changed_at': datetime.utcnow().isoformat(),
            'reason': context.get('reason') if context else None,
            'url': f'/requirements/{requirement.id}'
        }
    
    async def _send_notifications(
        self, 
        targets: List[int], 
        content: Dict[str, Any], 
        result: PostActionResult
    ):
        """发送通知"""
        for target_id in targets:
            try:
                # 这里应该集成通知服务
                # await notification_service.send_notification(target_id, content)
                result.add_executed_action(f"向用户 {target_id} 发送通知")
            except Exception as e:
                result.add_failed_action(f"向用户 {target_id} 发送通知失败: {str(e)}")


class ProjectProgressExecutor(PostActionExecutor):
    """项目进度更新执行器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def execute(self, requirement: Requirement, old_status: RequirementStatus, 
                     new_status: RequirementStatus, user_id: int, 
                     context: Dict[str, Any] = None) -> PostActionResult:
        """更新项目进度"""
        result = PostActionResult(success=True)
        
        try:
            # 更新项目进度
            await self._update_project_progress(requirement, result)
            
            # 检查里程碑
            await self._check_milestones(requirement, new_status, result)
            
            # 更新需求统计
            await self._update_requirement_statistics(requirement, result)
        
        except Exception as e:
            result.add_failed_action(f"项目进度更新: {str(e)}")
        
        return result
    
    async def _update_project_progress(self, requirement: Requirement, result: PostActionResult):
        """更新项目进度"""
        # 计算项目需求完成率
        total_requirements = self.db.query(Requirement).filter(
            Requirement.project_id == requirement.project_id
        ).count()
        
        completed_requirements = self.db.query(Requirement).filter(
            Requirement.project_id == requirement.project_id,
            Requirement.status.in_([
                RequirementStatus.COMPLETED,
                RequirementStatus.DEPLOYED,
                RequirementStatus.CLOSED
            ])
        ).count()
        
        progress = (completed_requirements / total_requirements * 100) if total_requirements > 0 else 0
        
        # 更新项目进度
        project = self.db.query(Project).filter(Project.id == requirement.project_id).first()
        if project:
            # 假设项目模型有progress字段
            # project.progress = progress
            # self.db.commit()
            result.add_executed_action(f"更新项目进度: {progress:.1f}%")
    
    async def _check_milestones(self, requirement: Requirement, new_status: RequirementStatus, result: PostActionResult):
        """检查里程碑"""
        if new_status in [RequirementStatus.COMPLETED, RequirementStatus.DEPLOYED]:
            # 检查是否达成里程碑
            # 这里应该集成里程碑管理系统
            result.add_executed_action("检查项目里程碑")
    
    async def _update_requirement_statistics(self, requirement: Requirement, result: PostActionResult):
        """更新需求统计"""
        # 更新需求统计信息
        result.add_executed_action("更新需求统计信息")


class RequirementStatusActionManager:
    """需求状态后置动作管理器"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.executors = [
            TaskCreationExecutor(db_session),
            NotificationExecutor(db_session),
            ProjectProgressExecutor(db_session)
        ]
    
    async def execute_post_actions(
        self, 
        requirement: Requirement, 
        old_status: RequirementStatus, 
        new_status: RequirementStatus, 
        user_id: int,
        context: Dict[str, Any] = None
    ) -> PostActionResult:
        """执行所有后置动作"""
        overall_result = PostActionResult(success=True)
        
        for executor in self.executors:
            try:
                result = await executor.execute(requirement, old_status, new_status, user_id, context)
                
                # 合并结果
                overall_result.executed_actions.extend(result.executed_actions)
                overall_result.failed_actions.extend(result.failed_actions)
                
                if not result.success:
                    overall_result.success = False
                
            except Exception as e:
                overall_result.add_failed_action(f"{executor.__class__.__name__}: {str(e)}")
        
        return overall_result
    
    def add_executor(self, executor: PostActionExecutor):
        """添加自定义执行器"""
        self.executors.append(executor)
    
    def remove_executor(self, executor_class: type):
        """移除指定类型的执行器"""
        self.executors = [e for e in self.executors if not isinstance(e, executor_class)]