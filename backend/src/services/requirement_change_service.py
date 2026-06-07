"""
需求变更管理服务

本模块提供需求变更管理的业务逻辑，包括：
- 变更请求管理
- 变更审批工作流
- 变更实施跟踪
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal

from ..core.exceptions import BusinessLogicError, ValidationError, NotFoundError
from ..models.requirement import (
    RequirementChangeRequest, ChangeStatus, ChangeType, ChangePriority,
    Requirement, RequirementStatus
)
from ..repositories.requirement_change_repository import RequirementChangeRepository
from ..repositories.requirement_repository import RequirementRepository
from ..schemas.requirement_change import (
    ChangeRequestCreate, ChangeRequestUpdate, ChangeRequestApproval,
    ChangeRequestResponse, ImpactAnalysisRequest, ImpactAnalysisResponse,
    ImpactItem, ChangeImplementationRequest
)


class RequirementChangeService:
    """需求变更管理服务"""
    
    def __init__(
        self,
        change_repo: RequirementChangeRepository,
        requirement_repo: RequirementRepository
    ):
        self.change_repo = change_repo
        self.requirement_repo = requirement_repo
    
    async def create_change_request(
        self,
        request: ChangeRequestCreate,
        requestor_id: int
    ) -> ChangeRequestResponse:
        """创建变更请求"""
        # 验证需求是否存在
        requirement = await self.requirement_repo.get_by_id(request.requirement_id)
        if not requirement:
            raise NotFoundError(f"需求 {request.requirement_id} 不存在")
        
        # 验证需求状态是否允许变更
        if not self._can_request_change(requirement.status):
            raise BusinessLogicError(
                f"需求当前状态 {requirement.status.value} 不允许提交变更请求"
            )
        
        # 创建变更请求
        change_data = request.dict(exclude={'requirement_id'})
        change_request = await self.change_repo.create_change_request(
            requirement_id=request.requirement_id,
            requestor_id=requestor_id,
            change_data=change_data
        )
        
        # 自动进行初步影响分析
        if request.change_type in [ChangeType.MODIFICATION, ChangeType.DELETION]:
            await self._perform_initial_impact_analysis(change_request)
        
        return ChangeRequestResponse.from_orm(change_request)
    
    async def update_change_request(
        self,
        change_request_id: int,
        request: ChangeRequestUpdate,
        user_id: int
    ) -> ChangeRequestResponse:
        """更新变更请求"""
        change_request = await self.change_repo.get_change_request_by_id(change_request_id)
        if not change_request:
            raise NotFoundError(f"变更请求 {change_request_id} 不存在")
        
        # 验证权限：只有申请人或管理员可以修改
        if change_request.requestor_id != user_id:
            # TODO: 添加管理员权限检查
            raise BusinessLogicError("只有申请人可以修改变更请求")
        
        # 验证状态：只有提交状态的请求可以修改
        if change_request.status not in [ChangeStatus.SUBMITTED]:
            raise BusinessLogicError(
                f"变更请求当前状态 {change_request.status.value} 不允许修改"
            )
        
        # 更新字段
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(change_request, field, value)
        
        change_request.updated_at = datetime.utcnow()
        await self.change_repo.session.flush()
        
        return ChangeRequestResponse.from_orm(change_request)
    
    async def approve_change_request(
        self,
        change_request_id: int,
        approval: ChangeRequestApproval,
        approver_id: int
    ) -> ChangeRequestResponse:
        """审批变更请求"""
        change_request = await self.change_repo.get_change_request_by_id(change_request_id)
        if not change_request:
            raise NotFoundError(f"变更请求 {change_request_id} 不存在")
        
        # 验证状态
        if change_request.status not in [ChangeStatus.SUBMITTED, ChangeStatus.UNDER_REVIEW]:
            raise BusinessLogicError(
                f"变更请求当前状态 {change_request.status.value} 不允许审批"
            )
        
        # 更新审批状态
        success = await self.change_repo.update_change_request_status(
            change_request_id=change_request_id,
            new_status=approval.status,
            approver_id=approver_id,
            implementer_id=approval.implementer_id
        )
        
        if not success:
            raise BusinessLogicError("审批失败")
        
        # 如果批准，触发后续流程
        if approval.status == ChangeStatus.APPROVED:
            await self._handle_change_approval(change_request, approval.implementer_id)
        
        # 重新获取更新后的数据
        updated_request = await self.change_repo.get_change_request_by_id(change_request_id)
        return ChangeRequestResponse.from_orm(updated_request)
    
    async def implement_change(
        self,
        change_request_id: int,
        implementation: ChangeImplementationRequest,
        implementer_id: int
    ) -> ChangeRequestResponse:
        """实施变更"""
        change_request = await self.change_repo.get_change_request_by_id(
            change_request_id, include_requirement=True
        )
        if not change_request:
            raise NotFoundError(f"变更请求 {change_request_id} 不存在")
        
        # 验证状态和权限
        if change_request.status != ChangeStatus.APPROVED:
            raise BusinessLogicError("只有已批准的变更请求可以实施")
        
        if change_request.implementer_id != implementer_id:
            raise BusinessLogicError("只有指定的实施人可以执行变更")
        
        # 执行变更实施
        await self._execute_change_implementation(change_request, implementation)
        
        # 更新状态
        await self.change_repo.update_change_request_status(
            change_request_id=change_request_id,
            new_status=ChangeStatus.IMPLEMENTED
        )
        
        # 重新获取更新后的数据
        updated_request = await self.change_repo.get_change_request_by_id(change_request_id)
        return ChangeRequestResponse.from_orm(updated_request)
    
    async def get_change_request(self, change_request_id: int) -> ChangeRequestResponse:
        """获取变更请求详情"""
        change_request = await self.change_repo.get_change_request_by_id(
            change_request_id, include_requirement=True
        )
        if not change_request:
            raise NotFoundError(f"变更请求 {change_request_id} 不存在")
        
        return ChangeRequestResponse.from_orm(change_request)
    
    async def get_change_requests_by_requirement(
        self,
        requirement_id: int,
        status_filter: Optional[List[ChangeStatus]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChangeRequestResponse]:
        """获取需求的变更请求列表"""
        change_requests = await self.change_repo.get_change_requests_by_requirement(
            requirement_id=requirement_id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        
        return [ChangeRequestResponse.from_orm(cr) for cr in change_requests]
    
    async def get_pending_approvals(
        self,
        approver_id: Optional[int] = None,
        priority_filter: Optional[List[ChangePriority]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChangeRequestResponse]:
        """获取待审批的变更请求"""
        change_requests = await self.change_repo.get_pending_approvals(
            approver_id=approver_id,
            priority_filter=priority_filter,
            limit=limit,
            offset=offset
        )
        
        return [ChangeRequestResponse.from_orm(cr) for cr in change_requests]
    
    async def search_change_requests(
        self,
        keyword: Optional[str] = None,
        status_filter: Optional[List[ChangeStatus]] = None,
        type_filter: Optional[List[ChangeType]] = None,
        priority_filter: Optional[List[ChangePriority]] = None,
        requestor_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChangeRequestResponse]:
        """搜索变更请求"""
        change_requests = await self.change_repo.search_change_requests(
            keyword=keyword,
            status_filter=status_filter,
            type_filter=type_filter,
            priority_filter=priority_filter,
            requestor_id=requestor_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset
        )
        
        return [ChangeRequestResponse.from_orm(cr) for cr in change_requests]
    
    async def get_change_statistics(
        self,
        requirement_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """获取变更统计信息"""
        return await self.change_repo.get_change_statistics(
            requirement_id=requirement_id,
            start_date=start_date,
            end_date=end_date
        )
    
    def _can_request_change(self, requirement_status: RequirementStatus) -> bool:
        """检查需求状态是否允许提交变更请求"""
        # 已取消、已关闭的需求不允许变更
        forbidden_statuses = [
            RequirementStatus.CANCELLED,
            RequirementStatus.CLOSED
        ]
        return requirement_status not in forbidden_statuses
    
    async def _perform_initial_impact_analysis(
        self,
        change_request: RequirementChangeRequest
    ) -> None:
        """执行初步影响分析"""
        # 这里可以集成影响分析引擎
        # 暂时添加基本的影响分析逻辑
        
        requirement = await self.requirement_repo.get_by_id(
            change_request.requirement_id
        )
        
        if not requirement:
            return
        
        # 基本影响分析
        impact_notes = []
        
        if change_request.change_type == ChangeType.DELETION:
            impact_notes.append("删除需求可能影响依赖此需求的其他需求")
            impact_notes.append("需要检查需求间的依赖关系")
        
        elif change_request.change_type == ChangeType.MODIFICATION:
            impact_notes.append("修改需求可能影响已开始的开发工作")
            if requirement.status in [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.TESTING]:
                impact_notes.append("需求正在开发或测试中，变更成本较高")
        
        if impact_notes:
            change_request.impact_analysis = "; ".join(impact_notes)
            await self.change_repo.session.flush()
    
    async def _handle_change_approval(
        self,
        change_request: RequirementChangeRequest,
        implementer_id: Optional[int]
    ) -> None:
        """处理变更批准后的逻辑"""
        # 如果指定了实施人，可以发送通知
        # 如果是紧急变更，可以自动开始实施
        if change_request.priority == ChangePriority.EMERGENCY:
            # 紧急变更可以考虑自动进入实施阶段
            pass
    
    async def _execute_change_implementation(
        self,
        change_request: RequirementChangeRequest,
        implementation: ChangeImplementationRequest
    ) -> None:
        """执行变更实施"""
        requirement = change_request.requirement
        
        # 根据变更类型执行相应的操作
        if change_request.change_type == ChangeType.MODIFICATION:
            # 更新需求内容
            if change_request.description:
                # 这里可以根据变更描述更新需求
                pass
        
        elif change_request.change_type == ChangeType.ADDITION:
            # 添加新的需求内容
            pass
        
        elif change_request.change_type == ChangeType.DELETION:
            # 标记需求为已取消或删除相关内容
            pass
        
        # 记录实施信息
        change_request.implementation_notes = implementation.implementation_notes
        if implementation.actual_effort:
            change_request.actual_effort = implementation.actual_effort
        if implementation.actual_cost:
            change_request.actual_cost = implementation.actual_cost
        
        await self.change_repo.session.flush()