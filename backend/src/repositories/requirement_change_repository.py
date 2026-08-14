"""
需求变更管理仓储层

本模块提供需求变更请求的数据访问功能，包括：
- 变更请求的CRUD操作
- 变更工作流管理
- 变更历史记录
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete, and_, or_, desc, asc, func
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.requirement import (
    RequirementChangeRequest, ChangeStatus, ChangeType, ChangePriority,
    Requirement
)
from .base_repository import BaseRepository


class RequirementChangeRepository(BaseRepository[RequirementChangeRequest]):
    """需求变更请求仓储"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, RequirementChangeRequest)
        # 子类历史代码使用 self.session，与基类的 self.db 保持一致
        self.session = session
    
    async def create_change_request(
        self,
        requirement_id: int,
        requestor_id: int,
        change_data: Dict[str, Any]
    ) -> RequirementChangeRequest:
        """创建变更请求"""
        # 生成变更请求编码
        change_code = await self._generate_change_request_code()
        
        change_request = RequirementChangeRequest(
            requirement_id=requirement_id,
            change_request_code=change_code,
            requestor_id=requestor_id,
            requested_date=date.today(),
            **change_data
        )
        
        self.session.add(change_request)
        await self.session.flush()
        await self.session.refresh(change_request)
        
        return change_request
    
    async def get_change_request_by_id(
        self,
        change_request_id: int,
        include_requirement: bool = True
    ) -> Optional[RequirementChangeRequest]:
        """根据ID获取变更请求"""
        query = select(RequirementChangeRequest).where(
            RequirementChangeRequest.id == change_request_id
        )
        
        if include_requirement:
            query = query.options(
                selectinload(RequirementChangeRequest.requirement)
            )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_change_requests_by_requirement(
        self,
        requirement_id: int,
        status_filter: Optional[List[ChangeStatus]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RequirementChangeRequest]:
        """获取需求的变更请求列表"""
        query = select(RequirementChangeRequest).where(
            RequirementChangeRequest.requirement_id == requirement_id
        )
        
        if status_filter:
            query = query.where(RequirementChangeRequest.status.in_(status_filter))
        
        query = query.order_by(desc(RequirementChangeRequest.created_at))
        query = query.offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_change_requests_by_status(
        self,
        status: ChangeStatus,
        assignee_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RequirementChangeRequest]:
        """根据状态获取变更请求"""
        query = select(RequirementChangeRequest).where(
            RequirementChangeRequest.status == status
        )
        
        if assignee_id:
            # 根据状态确定负责人字段
            if status == ChangeStatus.UNDER_REVIEW:
                query = query.where(RequirementChangeRequest.approver_id == assignee_id)
            elif status in [ChangeStatus.APPROVED, ChangeStatus.IMPLEMENTED]:
                query = query.where(RequirementChangeRequest.implementer_id == assignee_id)
        
        query = query.options(
            selectinload(RequirementChangeRequest.requirement)
        ).order_by(desc(RequirementChangeRequest.created_at))
        
        query = query.offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_change_request_status(
        self,
        change_request_id: int,
        new_status: ChangeStatus,
        approver_id: Optional[int] = None,
        implementer_id: Optional[int] = None,
        approval_comments: Optional[str] = None
    ) -> bool:
        """更新变更请求状态"""
        update_data = {
            'status': new_status,
            'updated_at': datetime.utcnow()
        }
        
        if new_status == ChangeStatus.APPROVED and approver_id:
            update_data['approver_id'] = approver_id
            update_data['approved_date'] = date.today()
        
        if implementer_id:
            update_data['implementer_id'] = implementer_id
        
        if new_status == ChangeStatus.IMPLEMENTED:
            update_data['implemented_date'] = date.today()
        
        stmt = update(RequirementChangeRequest).where(
            RequirementChangeRequest.id == change_request_id
        ).values(**update_data)
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def get_pending_approvals(
        self,
        approver_id: Optional[int] = None,
        priority_filter: Optional[List[ChangePriority]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RequirementChangeRequest]:
        """获取待审批的变更请求"""
        query = select(RequirementChangeRequest).where(
            RequirementChangeRequest.status.in_([
                ChangeStatus.SUBMITTED,
                ChangeStatus.UNDER_REVIEW
            ])
        )
        
        if approver_id:
            query = query.where(
                or_(
                    RequirementChangeRequest.approver_id == approver_id,
                    RequirementChangeRequest.approver_id.is_(None)
                )
            )
        
        if priority_filter:
            query = query.where(RequirementChangeRequest.priority.in_(priority_filter))
        
        query = query.options(
            selectinload(RequirementChangeRequest.requirement)
        ).order_by(
            RequirementChangeRequest.priority.desc(),
            RequirementChangeRequest.created_at.asc()
        )
        
        query = query.offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_change_statistics(
        self,
        requirement_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """获取变更统计信息"""
        base_query = select(RequirementChangeRequest)
        
        if requirement_id:
            base_query = base_query.where(
                RequirementChangeRequest.requirement_id == requirement_id
            )
        
        if start_date:
            base_query = base_query.where(
                RequirementChangeRequest.requested_date >= start_date
            )
        
        if end_date:
            base_query = base_query.where(
                RequirementChangeRequest.requested_date <= end_date
            )
        
        # 按状态统计
        status_query = select(
            RequirementChangeRequest.status,
            func.count(RequirementChangeRequest.id).label('count')
        ).select_from(base_query.subquery()).group_by(RequirementChangeRequest.status)
        
        status_result = await self.session.execute(status_query)
        status_stats = {row.status.value: row.count for row in status_result}
        
        # 按类型统计
        type_query = select(
            RequirementChangeRequest.change_type,
            func.count(RequirementChangeRequest.id).label('count')
        ).select_from(base_query.subquery()).group_by(RequirementChangeRequest.change_type)
        
        type_result = await self.session.execute(type_query)
        type_stats = {row.change_type.value: row.count for row in type_result}
        
        # 按优先级统计
        priority_query = select(
            RequirementChangeRequest.priority,
            func.count(RequirementChangeRequest.id).label('count')
        ).select_from(base_query.subquery()).group_by(RequirementChangeRequest.priority)
        
        priority_result = await self.session.execute(priority_query)
        priority_stats = {row.priority.value: row.count for row in priority_result}
        
        return {
            'status_distribution': status_stats,
            'type_distribution': type_stats,
            'priority_distribution': priority_stats,
            'total_requests': sum(status_stats.values())
        }
    
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
    ) -> List[RequirementChangeRequest]:
        """搜索变更请求"""
        query = select(RequirementChangeRequest)
        
        if keyword:
            query = query.where(
                or_(
                    RequirementChangeRequest.title.contains(keyword),
                    RequirementChangeRequest.description.contains(keyword),
                    RequirementChangeRequest.change_request_code.contains(keyword)
                )
            )
        
        if status_filter:
            query = query.where(RequirementChangeRequest.status.in_(status_filter))
        
        if type_filter:
            query = query.where(RequirementChangeRequest.change_type.in_(type_filter))
        
        if priority_filter:
            query = query.where(RequirementChangeRequest.priority.in_(priority_filter))
        
        if requestor_id:
            query = query.where(RequirementChangeRequest.requestor_id == requestor_id)
        
        if date_from:
            query = query.where(RequirementChangeRequest.requested_date >= date_from)
        
        if date_to:
            query = query.where(RequirementChangeRequest.requested_date <= date_to)
        
        query = query.options(
            selectinload(RequirementChangeRequest.requirement)
        ).order_by(desc(RequirementChangeRequest.created_at))
        
        query = query.offset(offset).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def _generate_change_request_code(self) -> str:
        """生成变更请求编码"""
        today = date.today()
        date_str = today.strftime("%Y%m%d")
        
        # 查询当天已有的变更请求数量
        count_query = select(func.count(RequirementChangeRequest.id)).where(
            RequirementChangeRequest.change_request_code.like(f"CR-{date_str}-%")
        )
        
        result = await self.session.execute(count_query)
        count = result.scalar() or 0
        
        # 生成编码：CR-YYYYMMDD-XXX
        sequence = str(count + 1).zfill(3)
        return f"CR-{date_str}-{sequence}"