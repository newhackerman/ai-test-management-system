"""
变更工作流引擎

本模块提供需求变更的工作流管理功能，包括：
- 工作流定义和执行
- 状态转换管理
- 审批流程控制
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

from models.requirement import (
    RequirementChangeRequest, ChangeStatus, ChangeType, ChangePriority
)
from repositories.requirement_change_repository import RequirementChangeRepository


class WorkflowAction(Enum):
    """工作流动作"""
    SUBMIT = "SUBMIT"
    REVIEW = "REVIEW"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    IMPLEMENT = "IMPLEMENT"
    CLOSE = "CLOSE"
    CANCEL = "CANCEL"


class WorkflowStepType(Enum):
    """工作流步骤类型"""
    START = "START"
    REVIEW = "REVIEW"
    APPROVAL = "APPROVAL"
    IMPLEMENTATION = "IMPLEMENTATION"
    END = "END"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    name: str
    step_type: WorkflowStepType
    required_role: Optional[str] = None
    auto_execute: bool = False
    timeout_hours: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None
    next_steps: Optional[Dict[str, str]] = None  # action -> next_step_id


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    initial_step: str
    applicable_change_types: List[ChangeType]
    applicable_priorities: List[ChangePriority]


@dataclass
class WorkflowInstance:
    """工作流实例"""
    id: str
    workflow_id: str
    change_request_id: int
    current_step: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    step_history: List[Dict[str, Any]] = None
    context_data: Dict[str, Any] = None


class ChangeWorkflowEngine:
    """变更工作流引擎"""
    
    def __init__(self, change_repo: RequirementChangeRepository):
        self.change_repo = change_repo
        self.workflows = self._initialize_workflows()
        self.active_instances: Dict[int, WorkflowInstance] = {}
    
    async def start_workflow(
        self,
        change_request_id: int,
        workflow_id: Optional[str] = None
    ) -> WorkflowInstance:
        """启动工作流"""
        change_request = await self.change_repo.get_change_request_by_id(change_request_id)
        if not change_request:
            raise ValueError(f"变更请求 {change_request_id} 不存在")
        
        # 选择合适的工作流
        if not workflow_id:
            workflow_id = self._select_workflow(change_request)
        
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        # 创建工作流实例
        instance = WorkflowInstance(
            id=f"wf_{change_request_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            workflow_id=workflow_id,
            change_request_id=change_request_id,
            current_step=workflow.initial_step,
            status="RUNNING",
            started_at=datetime.utcnow(),
            step_history=[],
            context_data={}
        )
        
        self.active_instances[change_request_id] = instance
        
        # 执行初始步骤
        await self._execute_step(instance, workflow.initial_step)
        
        return instance
    
    async def execute_action(
        self,
        change_request_id: int,
        action: WorkflowAction,
        user_id: int,
        data: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """执行工作流动作"""
        instance = self.active_instances.get(change_request_id)
        if not instance:
            raise ValueError(f"变更请求 {change_request_id} 没有活动的工作流实例")
        
        workflow = self.workflows[instance.workflow_id]
        current_step = self._get_step(workflow, instance.current_step)
        
        if not current_step:
            raise ValueError(f"当前步骤 {instance.current_step} 不存在")
        
        # 验证动作是否允许
        if not self._is_action_allowed(current_step, action, user_id):
            raise ValueError(f"当前步骤不允许执行动作 {action.value}")
        
        # 记录步骤历史
        step_record = {
            "step_id": current_step.id,
            "action": action.value,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {}
        }
        instance.step_history.append(step_record)
        
        # 确定下一步骤
        next_step_id = self._get_next_step(current_step, action)
        
        if next_step_id:
            instance.current_step = next_step_id
            await self._execute_step(instance, next_step_id)
        else:
            # 工作流结束
            instance.status = "COMPLETED"
            instance.completed_at = datetime.utcnow()
        
        # 更新变更请求状态
        await self._update_change_request_status(instance, action, data)
        
        return instance
    
    async def get_workflow_instance(self, change_request_id: int) -> Optional[WorkflowInstance]:
        """获取工作流实例"""
        return self.active_instances.get(change_request_id)
    
    async def get_pending_tasks(self, user_id: int, role: str) -> List[Dict[str, Any]]:
        """获取用户待处理任务"""
        pending_tasks = []
        
        for instance in self.active_instances.values():
            if instance.status != "RUNNING":
                continue
            
            workflow = self.workflows[instance.workflow_id]
            current_step = self._get_step(workflow, instance.current_step)
            
            if (current_step and 
                current_step.required_role and 
                current_step.required_role == role):
                
                change_request = await self.change_repo.get_change_request_by_id(
                    instance.change_request_id
                )
                
                pending_tasks.append({
                    "workflow_instance_id": instance.id,
                    "change_request_id": instance.change_request_id,
                    "change_request_title": change_request.title if change_request else "",
                    "current_step": current_step.name,
                    "step_type": current_step.step_type.value,
                    "started_at": instance.started_at.isoformat(),
                    "timeout_at": self._calculate_timeout(instance, current_step)
                })
        
        return pending_tasks
    
    def _initialize_workflows(self) -> Dict[str, WorkflowDefinition]:
        """初始化工作流定义"""
        workflows = {}
        
        # 标准变更工作流
        standard_workflow = WorkflowDefinition(
            id="standard_change",
            name="标准变更流程",
            description="适用于大部分需求变更的标准审批流程",
            steps=[
                WorkflowStep(
                    id="start",
                    name="开始",
                    step_type=WorkflowStepType.START,
                    auto_execute=True,
                    next_steps={"SUBMIT": "review"}
                ),
                WorkflowStep(
                    id="review",
                    name="初步评审",
                    step_type=WorkflowStepType.REVIEW,
                    required_role="reviewer",
                    timeout_hours=48,
                    next_steps={
                        "APPROVE": "approval",
                        "REJECT": "end"
                    }
                ),
                WorkflowStep(
                    id="approval",
                    name="正式审批",
                    step_type=WorkflowStepType.APPROVAL,
                    required_role="approver",
                    timeout_hours=72,
                    next_steps={
                        "APPROVE": "implementation",
                        "REJECT": "end"
                    }
                ),
                WorkflowStep(
                    id="implementation",
                    name="变更实施",
                    step_type=WorkflowStepType.IMPLEMENTATION,
                    required_role="implementer",
                    timeout_hours=168,  # 7天
                    next_steps={"IMPLEMENT": "end"}
                ),
                WorkflowStep(
                    id="end",
                    name="结束",
                    step_type=WorkflowStepType.END,
                    auto_execute=True
                )
            ],
            initial_step="start",
            applicable_change_types=[
                ChangeType.MODIFICATION,
                ChangeType.ADDITION,
                ChangeType.CLARIFICATION
            ],
            applicable_priorities=[
                ChangePriority.MEDIUM,
                ChangePriority.LOW
            ]
        )
        workflows["standard_change"] = standard_workflow
        
        # 紧急变更工作流
        emergency_workflow = WorkflowDefinition(
            id="emergency_change",
            name="紧急变更流程",
            description="适用于紧急和高优先级变更的快速审批流程",
            steps=[
                WorkflowStep(
                    id="start",
                    name="开始",
                    step_type=WorkflowStepType.START,
                    auto_execute=True,
                    next_steps={"SUBMIT": "emergency_approval"}
                ),
                WorkflowStep(
                    id="emergency_approval",
                    name="紧急审批",
                    step_type=WorkflowStepType.APPROVAL,
                    required_role="emergency_approver",
                    timeout_hours=4,
                    next_steps={
                        "APPROVE": "implementation",
                        "REJECT": "end"
                    }
                ),
                WorkflowStep(
                    id="implementation",
                    name="紧急实施",
                    step_type=WorkflowStepType.IMPLEMENTATION,
                    required_role="implementer",
                    timeout_hours=24,
                    next_steps={"IMPLEMENT": "end"}
                ),
                WorkflowStep(
                    id="end",
                    name="结束",
                    step_type=WorkflowStepType.END,
                    auto_execute=True
                )
            ],
            initial_step="start",
            applicable_change_types=[
                ChangeType.MODIFICATION,
                ChangeType.ADDITION,
                ChangeType.DELETION
            ],
            applicable_priorities=[
                ChangePriority.EMERGENCY,
                ChangePriority.HIGH
            ]
        )
        workflows["emergency_change"] = emergency_workflow
        
        # 删除变更工作流
        deletion_workflow = WorkflowDefinition(
            id="deletion_change",
            name="删除变更流程",
            description="适用于需求删除的特殊审批流程",
            steps=[
                WorkflowStep(
                    id="start",
                    name="开始",
                    step_type=WorkflowStepType.START,
                    auto_execute=True,
                    next_steps={"SUBMIT": "impact_review"}
                ),
                WorkflowStep(
                    id="impact_review",
                    name="影响评估",
                    step_type=WorkflowStepType.REVIEW,
                    required_role="impact_analyst",
                    timeout_hours=24,
                    next_steps={"REVIEW": "senior_approval"}
                ),
                WorkflowStep(
                    id="senior_approval",
                    name="高级审批",
                    step_type=WorkflowStepType.APPROVAL,
                    required_role="senior_approver",
                    timeout_hours=48,
                    next_steps={
                        "APPROVE": "implementation",
                        "REJECT": "end"
                    }
                ),
                WorkflowStep(
                    id="implementation",
                    name="删除实施",
                    step_type=WorkflowStepType.IMPLEMENTATION,
                    required_role="senior_implementer",
                    timeout_hours=72,
                    next_steps={"IMPLEMENT": "end"}
                ),
                WorkflowStep(
                    id="end",
                    name="结束",
                    step_type=WorkflowStepType.END,
                    auto_execute=True
                )
            ],
            initial_step="start",
            applicable_change_types=[ChangeType.DELETION],
            applicable_priorities=[
                ChangePriority.HIGH,
                ChangePriority.MEDIUM,
                ChangePriority.LOW
            ]
        )
        workflows["deletion_change"] = deletion_workflow
        
        return workflows
    
    def _select_workflow(self, change_request: RequirementChangeRequest) -> str:
        """选择合适的工作流"""
        # 删除变更使用特殊流程
        if change_request.change_type == ChangeType.DELETION:
            return "deletion_change"
        
        # 紧急变更使用快速流程
        if change_request.priority in [ChangePriority.EMERGENCY, ChangePriority.HIGH]:
            return "emergency_change"
        
        # 其他使用标准流程
        return "standard_change"
    
    def _get_step(self, workflow: WorkflowDefinition, step_id: str) -> Optional[WorkflowStep]:
        """获取工作流步骤"""
        for step in workflow.steps:
            if step.id == step_id:
                return step
        return None
    
    def _is_action_allowed(
        self, 
        step: WorkflowStep, 
        action: WorkflowAction, 
        user_id: int
    ) -> bool:
        """检查动作是否允许"""
        # 检查步骤是否支持该动作
        if step.next_steps and action.value not in step.next_steps:
            return False
        
        # 这里可以添加更多的权限检查逻辑
        # 例如检查用户是否具有required_role
        
        return True
    
    def _get_next_step(self, step: WorkflowStep, action: WorkflowAction) -> Optional[str]:
        """获取下一步骤"""
        if step.next_steps:
            return step.next_steps.get(action.value)
        return None
    
    async def _execute_step(self, instance: WorkflowInstance, step_id: str) -> None:
        """执行工作流步骤"""
        workflow = self.workflows[instance.workflow_id]
        step = self._get_step(workflow, step_id)
        
        if not step:
            return
        
        # 如果是自动执行步骤
        if step.auto_execute:
            if step.step_type == WorkflowStepType.START:
                # 自动提交到下一步
                if step.next_steps and "SUBMIT" in step.next_steps:
                    next_step_id = step.next_steps["SUBMIT"]
                    instance.current_step = next_step_id
                    await self._execute_step(instance, next_step_id)
            elif step.step_type == WorkflowStepType.END:
                # 工作流结束
                instance.status = "COMPLETED"
                instance.completed_at = datetime.utcnow()
        
        # 设置超时
        if step.timeout_hours:
            timeout_at = datetime.utcnow() + timedelta(hours=step.timeout_hours)
            instance.context_data = instance.context_data or {}
            instance.context_data["timeout_at"] = timeout_at.isoformat()
    
    async def _update_change_request_status(
        self,
        instance: WorkflowInstance,
        action: WorkflowAction,
        data: Optional[Dict[str, Any]]
    ) -> None:
        """更新变更请求状态"""
        status_mapping = {
            WorkflowAction.SUBMIT: ChangeStatus.UNDER_REVIEW,
            WorkflowAction.APPROVE: ChangeStatus.APPROVED,
            WorkflowAction.REJECT: ChangeStatus.REJECTED,
            WorkflowAction.IMPLEMENT: ChangeStatus.IMPLEMENTED,
            WorkflowAction.CLOSE: ChangeStatus.CLOSED,
            WorkflowAction.CANCEL: ChangeStatus.REJECTED
        }
        
        new_status = status_mapping.get(action)
        if new_status:
            await self.change_repo.update_change_request_status(
                change_request_id=instance.change_request_id,
                new_status=new_status,
                approver_id=data.get("user_id") if data else None,
                implementer_id=data.get("implementer_id") if data else None
            )
    
    def _calculate_timeout(
        self, 
        instance: WorkflowInstance, 
        step: WorkflowStep
    ) -> Optional[str]:
        """计算超时时间"""
        if not step.timeout_hours:
            return None
        
        # 从步骤历史中找到进入当前步骤的时间
        current_step_start = None
        for record in reversed(instance.step_history):
            if record.get("next_step") == step.id:
                current_step_start = datetime.fromisoformat(record["timestamp"])
                break
        
        if not current_step_start:
            current_step_start = instance.started_at
        
        timeout_at = current_step_start + timedelta(hours=step.timeout_hours)
        return timeout_at.isoformat()
    
    async def check_timeouts(self) -> List[Dict[str, Any]]:
        """检查超时的工作流实例"""
        timeout_instances = []
        current_time = datetime.utcnow()
        
        for instance in self.active_instances.values():
            if instance.status != "RUNNING":
                continue
            
            timeout_str = instance.context_data.get("timeout_at") if instance.context_data else None
            if timeout_str:
                timeout_at = datetime.fromisoformat(timeout_str)
                if current_time > timeout_at:
                    timeout_instances.append({
                        "instance_id": instance.id,
                        "change_request_id": instance.change_request_id,
                        "current_step": instance.current_step,
                        "timeout_at": timeout_str,
                        "overdue_hours": (current_time - timeout_at).total_seconds() / 3600
                    })
        
        return timeout_instances