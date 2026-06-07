"""
需求仓储实现

提供需求管理相关的数据访问功能，包括：
- 需求CRUD操作
- 需求查询和筛选
- 需求状态管理
- 需求依赖关系管理
"""
from abc import abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload

from .base_repository import BaseRepository, IBaseRepository
from ..models.requirement import (
    Requirement, RequirementStatus, RequirementType, Priority, BusinessValue, Complexity,
    RequirementStatusHistory, RequirementDependency, DependencyType,
    RequirementReview, RequirementReviewComment, RequirementChangeRequest,
    RequirementTraceabilityLink
)


class IRequirementRepository(IBaseRepository[Requirement]):
    """需求仓储接口"""
    
    @abstractmethod
    async def get_by_code(self, requirement_code: str) -> Optional[Requirement]:
        """根据需求编码获取需求"""
        pass
    
    @abstractmethod
    async def get_by_project_id(self, project_id: int, skip: int = 0, limit: int = 100) -> List[Requirement]:
        """根据项目ID获取需求列表"""
        pass
    
    @abstractmethod
    async def search_requirements(self, search_params: Dict[str, Any]) -> Tuple[List[Requirement], int]:
        """搜索需求"""
        pass
    
    @abstractmethod
    async def get_children_requirements(self, parent_id: int) -> List[Requirement]:
        """获取子需求列表"""
        pass
    
    @abstractmethod
    async def get_requirement_with_relations(self, requirement_id: int) -> Optional[Requirement]:
        """获取包含关联关系的需求"""
        pass
    
    @abstractmethod
    async def update_requirement_status(self, requirement_id: int, new_status: RequirementStatus, 
                                      changed_by: int, reason: str = None) -> bool:
        """更新需求状态"""
        pass
    
    @abstractmethod
    async def get_requirements_by_status(self, status: RequirementStatus, project_id: Optional[int] = None) -> List[Requirement]:
        """根据状态获取需求列表"""
        pass
    
    @abstractmethod
    async def get_requirements_by_assignee(self, assignee_id: int) -> List[Requirement]:
        """根据负责人获取需求列表"""
        pass
    
    @abstractmethod
    async def count_requirements_by_project_and_date(self, project_id: int, date_str: str) -> int:
        """统计项目在指定日期的需求数量"""
        pass


class RequirementRepository(BaseRepository[Requirement], IRequirementRepository):
    """需求仓储实现类"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Requirement)
    
    async def get_by_code(self, requirement_code: str) -> Optional[Requirement]:
        """根据需求编码获取需求"""
        query = select(Requirement).where(Requirement.requirement_code == requirement_code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_project_id(self, project_id: int, skip: int = 0, limit: int = 100) -> List[Requirement]:
        """根据项目ID获取需求列表"""
        query = (
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .order_by(desc(Requirement.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_requirements(self, search_params: Dict[str, Any]) -> Tuple[List[Requirement], int]:
        """
        搜索需求
        
        支持的搜索参数：
        - project_id: 项目ID
        - status: 需求状态列表
        - priority: 优先级列表
        - requirement_type: 需求类型列表
        - assignee_id: 负责人ID
        - creator_id: 创建人ID
        - keyword: 关键词搜索（标题、描述）
        - date_range: 日期范围 {'start': date, 'end': date}
        - tags: 标签列表
        - skip: 跳过数量
        - limit: 限制数量
        - order_by: 排序字段
        - order_direction: 排序方向 ('asc', 'desc')
        """
        # 构建基础查询
        query = select(Requirement)
        count_query = select(func.count(Requirement.id))
        
        # 构建查询条件
        conditions = []
        
        # 项目ID筛选
        if 'project_id' in search_params:
            conditions.append(Requirement.project_id == search_params['project_id'])
        
        # 状态筛选
        if 'status' in search_params and search_params['status']:
            if isinstance(search_params['status'], list):
                conditions.append(Requirement.status.in_(search_params['status']))
            else:
                conditions.append(Requirement.status == search_params['status'])
        
        # 优先级筛选
        if 'priority' in search_params and search_params['priority']:
            if isinstance(search_params['priority'], list):
                conditions.append(Requirement.priority.in_(search_params['priority']))
            else:
                conditions.append(Requirement.priority == search_params['priority'])
        
        # 需求类型筛选
        if 'requirement_type' in search_params and search_params['requirement_type']:
            if isinstance(search_params['requirement_type'], list):
                conditions.append(Requirement.requirement_type.in_(search_params['requirement_type']))
            else:
                conditions.append(Requirement.requirement_type == search_params['requirement_type'])
        
        # 负责人筛选
        if 'assignee_id' in search_params:
            conditions.append(Requirement.assignee_id == search_params['assignee_id'])
        
        # 创建人筛选
        if 'creator_id' in search_params:
            conditions.append(Requirement.creator_id == search_params['creator_id'])

        if 'reviewer_id' in search_params:
            conditions.append(Requirement.reviewer_id == search_params['reviewer_id'])

        if 'category' in search_params and search_params['category']:
            conditions.append(Requirement.category == search_params['category'])

        if 'business_value' in search_params and search_params['business_value']:
            if isinstance(search_params['business_value'], list):
                conditions.append(Requirement.business_value.in_(search_params['business_value']))
            else:
                conditions.append(Requirement.business_value == search_params['business_value'])

        if 'complexity' in search_params and search_params['complexity']:
            if isinstance(search_params['complexity'], list):
                conditions.append(Requirement.complexity.in_(search_params['complexity']))
            else:
                conditions.append(Requirement.complexity == search_params['complexity'])
        
        # 关键词搜索
        if 'keyword' in search_params and search_params['keyword']:
            keyword = f"%{search_params['keyword']}%"
            conditions.append(
                or_(
                    Requirement.requirement_code.like(keyword),
                    Requirement.title.like(keyword),
                    Requirement.description.like(keyword),
                    Requirement.acceptance_criteria.like(keyword)
                )
            )
        
        # 日期范围筛选
        if 'created_from' in search_params:
            conditions.append(Requirement.created_at >= search_params['created_from'])

        if 'created_to' in search_params:
            conditions.append(Requirement.created_at <= search_params['created_to'])

        if 'planned_start_from' in search_params:
            conditions.append(Requirement.planned_start_date >= search_params['planned_start_from'])

        if 'planned_start_to' in search_params:
            conditions.append(Requirement.planned_start_date <= search_params['planned_start_to'])

        if 'planned_end_from' in search_params:
            conditions.append(Requirement.planned_end_date >= search_params['planned_end_from'])

        if 'planned_end_to' in search_params:
            conditions.append(Requirement.planned_end_date <= search_params['planned_end_to'])

        if 'quality_score_min' in search_params:
            conditions.append(Requirement.quality_score >= search_params['quality_score_min'])

        if 'quality_score_max' in search_params:
            conditions.append(Requirement.quality_score <= search_params['quality_score_max'])

        if 'date_range' in search_params and search_params['date_range']:
            date_range = search_params['date_range']
            if 'start' in date_range:
                conditions.append(Requirement.created_at >= date_range['start'])
            if 'end' in date_range:
                conditions.append(Requirement.created_at <= date_range['end'])
        
        # 标签筛选
        if 'tags' in search_params and search_params['tags']:
            # 使用JSON查询功能
            for tag in search_params['tags']:
                conditions.append(text(f"JSON_CONTAINS(tags, '\"{tag}\"')"))
        
        # 应用查询条件
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 排序
        order_by = search_params.get('sort_by') or search_params.get('order_by') or 'created_at'
        order_direction = search_params.get('sort_order') or search_params.get('order_direction') or 'desc'
        
        if hasattr(Requirement, order_by):
            order_attr = getattr(Requirement, order_by)
            if order_direction.lower() == 'asc':
                query = query.order_by(asc(order_attr))
            else:
                query = query.order_by(desc(order_attr))
        
        # 分页
        skip = search_params.get('skip', 0)
        limit = search_params.get('limit', 100)
        query = query.offset(skip).limit(limit)
        
        # 执行查询
        result = await self.db.execute(query)
        requirements = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        return requirements, total_count
    
    async def get_children_requirements(self, parent_id: int) -> List[Requirement]:
        """获取子需求列表"""
        query = (
            select(Requirement)
            .where(Requirement.parent_id == parent_id)
            .order_by(Requirement.created_at)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_requirement_with_relations(self, requirement_id: int) -> Optional[Requirement]:
        """获取包含关联关系的需求"""
        query = (
            select(Requirement)
            .options(
                selectinload(Requirement.children),
                selectinload(Requirement.status_history),
                selectinload(Requirement.source_dependencies).selectinload(RequirementDependency.target_requirement),
                selectinload(Requirement.target_dependencies).selectinload(RequirementDependency.source_requirement),
                selectinload(Requirement.reviews),
                selectinload(Requirement.change_requests)
            )
            .where(Requirement.id == requirement_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_requirement_status(self, requirement_id: int, new_status: RequirementStatus, 
                                      changed_by: int, reason: str = None) -> bool:
        """更新需求状态"""
        # 获取当前需求
        requirement = await self.get_by_id(requirement_id)
        if not requirement:
            return False
        
        old_status = requirement.status
        
        # 更新需求状态
        requirement.status = new_status
        requirement.updated_by = changed_by
        requirement.updated_at = datetime.utcnow()
        
        # 记录状态历史
        status_history = RequirementStatusHistory(
            requirement_id=requirement_id,
            old_status=old_status,
            new_status=new_status,
            change_reason=reason,
            changed_by=changed_by,
            changed_at=datetime.utcnow()
        )
        
        self.db.add(status_history)
        await self.db.commit()
        await self.db.refresh(requirement)
        
        return True
    
    async def get_requirements_by_status(self, status: RequirementStatus, project_id: Optional[int] = None) -> List[Requirement]:
        """根据状态获取需求列表"""
        query = select(Requirement).where(Requirement.status == status)
        
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        query = query.order_by(desc(Requirement.updated_at))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_requirements_by_assignee(self, assignee_id: int) -> List[Requirement]:
        """根据负责人获取需求列表"""
        query = (
            select(Requirement)
            .where(Requirement.assignee_id == assignee_id)
            .order_by(desc(Requirement.updated_at))
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def count_requirements_by_project_and_date(self, project_id: int, date_str: str) -> int:
        """统计项目在指定日期的需求数量"""
        query = (
            select(func.count(Requirement.id))
            .where(
                and_(
                    Requirement.project_id == project_id,
                    func.date_format(Requirement.created_at, '%Y%m%d') == date_str
                )
            )
        )
        result = await self.db.execute(query)
        return result.scalar()
    
    async def get_requirements_statistics(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """获取需求统计信息"""
        base_query = select(Requirement)
        if project_id:
            base_query = base_query.where(Requirement.project_id == project_id)
        
        # 总数统计
        total_query = select(func.count(Requirement.id))
        if project_id:
            total_query = total_query.where(Requirement.project_id == project_id)
        
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar()
        
        # 状态分布统计
        status_query = (
            select(Requirement.status, func.count(Requirement.id))
            .group_by(Requirement.status)
        )
        if project_id:
            status_query = status_query.where(Requirement.project_id == project_id)
        
        status_result = await self.db.execute(status_query)
        status_distribution = {status.value: count for status, count in status_result.fetchall()}
        
        # 优先级分布统计
        priority_query = (
            select(Requirement.priority, func.count(Requirement.id))
            .group_by(Requirement.priority)
        )
        if project_id:
            priority_query = priority_query.where(Requirement.project_id == project_id)
        
        priority_result = await self.db.execute(priority_query)
        priority_distribution = {priority.value: count for priority, count in priority_result.fetchall()}
        
        # 类型分布统计
        type_query = (
            select(Requirement.requirement_type, func.count(Requirement.id))
            .group_by(Requirement.requirement_type)
        )
        if project_id:
            type_query = type_query.where(Requirement.project_id == project_id)
        
        type_result = await self.db.execute(type_query)
        type_distribution = {req_type.value: count for req_type, count in type_result.fetchall()}
        
        return {
            'total_count': total_count,
            'status_distribution': status_distribution,
            'priority_distribution': priority_distribution,
            'type_distribution': type_distribution
        }
    
    async def get_requirements_by_date_range(self, start_date: date, end_date: date, 
                                           project_id: Optional[int] = None) -> List[Requirement]:
        """根据日期范围获取需求列表"""
        query = (
            select(Requirement)
            .where(
                and_(
                    Requirement.created_at >= start_date,
                    Requirement.created_at <= end_date
                )
            )
        )
        
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        query = query.order_by(desc(Requirement.created_at))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_overdue_requirements(self, project_id: Optional[int] = None) -> List[Requirement]:
        """获取逾期需求列表"""
        today = date.today()
        query = (
            select(Requirement)
            .where(
                and_(
                    Requirement.planned_end_date < today,
                    Requirement.status.not_in([RequirementStatus.COMPLETED, RequirementStatus.CLOSED, RequirementStatus.CANCELLED])
                )
            )
        )
        
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        query = query.order_by(Requirement.planned_end_date)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_requirements_by_complexity(self, complexity: Complexity, 
                                           project_id: Optional[int] = None) -> List[Requirement]:
        """根据复杂度获取需求列表"""
        query = select(Requirement).where(Requirement.complexity == complexity)
        
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        query = query.order_by(desc(Requirement.created_at))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_requirements_by_text(self, search_text: str, project_id: Optional[int] = None) -> List[Requirement]:
        """全文搜索需求"""
        search_pattern = f"%{search_text}%"
        query = (
            select(Requirement)
            .where(
                or_(
                    Requirement.title.like(search_pattern),
                    Requirement.description.like(search_pattern),
                    Requirement.acceptance_criteria.like(search_pattern),
                    Requirement.requirement_code.like(search_pattern)
                )
            )
        )
        
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        query = query.order_by(desc(Requirement.updated_at))
        result = await self.db.execute(query)
        return result.scalars().all()
