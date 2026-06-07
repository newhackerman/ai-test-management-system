"""
需求分类仓储实现

提供需求分类管理相关的数据访问功能，包括：
- 分类维度管理
- 分类类别管理
- 需求分类关联管理
- 智能分类建议管理
- 标签管理
"""
from abc import abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text, update, delete
from sqlalchemy.orm import selectinload, joinedload

from .base_repository import BaseRepository, IBaseRepository
from ..models.requirement_classification import (
    RequirementClassificationDimension, RequirementClassificationCategory,
    RequirementClassification, RequirementClassificationSuggestion,
    RequirementTag, RequirementTagAssignment,
    ClassificationDimension, ClassificationStatus, ClassificationSuggestionStatus
)


class IRequirementClassificationRepository(IBaseRepository[RequirementClassificationDimension]):
    """需求分类仓储接口"""
    
    @abstractmethod
    async def get_dimension_by_code(self, dimension_code: str) -> Optional[RequirementClassificationDimension]:
        """根据维度编码获取分类维度"""
        pass
    
    @abstractmethod
    async def get_active_dimensions(self) -> List[RequirementClassificationDimension]:
        """获取激活的分类维度列表"""
        pass
    
    @abstractmethod
    async def get_categories_by_dimension(self, dimension_id: int) -> List[RequirementClassificationCategory]:
        """根据维度ID获取类别列表"""
        pass
    
    @abstractmethod
    async def get_category_tree(self, dimension_id: int) -> List[RequirementClassificationCategory]:
        """获取分类类别树形结构"""
        pass
    
    @abstractmethod
    async def search_categories(self, search_params: Dict[str, Any]) -> Tuple[List[RequirementClassificationCategory], int]:
        """搜索分类类别"""
        pass


class RequirementClassificationRepository(BaseRepository[RequirementClassificationDimension], IRequirementClassificationRepository):
    """需求分类仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementClassificationDimension, session)
    
    async def get_dimension_by_code(self, dimension_code: str) -> Optional[RequirementClassificationDimension]:
        """根据维度编码获取分类维度"""
        stmt = select(RequirementClassificationDimension).where(
            RequirementClassificationDimension.dimension_code == dimension_code
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_dimensions(self) -> List[RequirementClassificationDimension]:
        """获取激活的分类维度列表"""
        stmt = select(RequirementClassificationDimension).where(
            RequirementClassificationDimension.status == ClassificationStatus.ACTIVE
        ).order_by(RequirementClassificationDimension.sort_order)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_categories_by_dimension(self, dimension_id: int) -> List[RequirementClassificationCategory]:
        """根据维度ID获取类别列表"""
        stmt = select(RequirementClassificationCategory).where(
            and_(
                RequirementClassificationCategory.dimension_id == dimension_id,
                RequirementClassificationCategory.status == ClassificationStatus.ACTIVE
            )
        ).order_by(RequirementClassificationCategory.sort_order)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_category_tree(self, dimension_id: int) -> List[RequirementClassificationCategory]:
        """获取分类类别树形结构"""
        # 首先获取所有类别
        stmt = select(RequirementClassificationCategory).where(
            and_(
                RequirementClassificationCategory.dimension_id == dimension_id,
                RequirementClassificationCategory.status == ClassificationStatus.ACTIVE
            )
        ).options(
            selectinload(RequirementClassificationCategory.children)
        ).order_by(RequirementClassificationCategory.level, RequirementClassificationCategory.sort_order)
        
        result = await self.session.execute(stmt)
        all_categories = result.scalars().all()
        
        # 构建树形结构 - 返回根节点
        root_categories = [cat for cat in all_categories if cat.parent_id is None]
        return root_categories
    
    async def search_categories(self, search_params: Dict[str, Any]) -> Tuple[List[RequirementClassificationCategory], int]:
        """搜索分类类别"""
        stmt = select(RequirementClassificationCategory)
        count_stmt = select(func.count(RequirementClassificationCategory.id))
        
        # 构建查询条件
        conditions = []
        
        if search_params.get('dimension_id'):
            conditions.append(RequirementClassificationCategory.dimension_id == search_params['dimension_id'])
        
        if search_params.get('category_name'):
            conditions.append(RequirementClassificationCategory.category_name.ilike(f"%{search_params['category_name']}%"))
        
        if search_params.get('status'):
            conditions.append(RequirementClassificationCategory.status == search_params['status'])
        
        if search_params.get('level'):
            conditions.append(RequirementClassificationCategory.level == search_params['level'])
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        
        # 排序
        sort_field = search_params.get('sort_field', 'sort_order')
        sort_order = search_params.get('sort_order', 'asc')
        
        if hasattr(RequirementClassificationCategory, sort_field):
            order_func = asc if sort_order == 'asc' else desc
            stmt = stmt.order_by(order_func(getattr(RequirementClassificationCategory, sort_field)))
        
        # 分页
        skip = search_params.get('skip', 0)
        limit = search_params.get('limit', 100)
        stmt = stmt.offset(skip).limit(limit)
        
        # 执行查询
        result = await self.session.execute(stmt)
        categories = result.scalars().all()
        
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar()
        
        return categories, total


class IRequirementClassificationCategoryRepository(IBaseRepository[RequirementClassificationCategory]):
    """需求分类类别仓储接口"""
    
    @abstractmethod
    async def get_by_code(self, category_code: str, dimension_id: int) -> Optional[RequirementClassificationCategory]:
        """根据类别编码和维度ID获取类别"""
        pass
    
    @abstractmethod
    async def get_children(self, parent_id: int) -> List[RequirementClassificationCategory]:
        """获取子类别列表"""
        pass
    
    @abstractmethod
    async def update_usage_count(self, category_id: int, increment: int = 1) -> None:
        """更新使用次数"""
        pass


class RequirementClassificationCategoryRepository(BaseRepository[RequirementClassificationCategory], IRequirementClassificationCategoryRepository):
    """需求分类类别仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementClassificationCategory, session)
    
    async def get_by_code(self, category_code: str, dimension_id: int) -> Optional[RequirementClassificationCategory]:
        """根据类别编码和维度ID获取类别"""
        stmt = select(RequirementClassificationCategory).where(
            and_(
                RequirementClassificationCategory.category_code == category_code,
                RequirementClassificationCategory.dimension_id == dimension_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_children(self, parent_id: int) -> List[RequirementClassificationCategory]:
        """获取子类别列表"""
        stmt = select(RequirementClassificationCategory).where(
            and_(
                RequirementClassificationCategory.parent_id == parent_id,
                RequirementClassificationCategory.status == ClassificationStatus.ACTIVE
            )
        ).order_by(RequirementClassificationCategory.sort_order)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_usage_count(self, category_id: int, increment: int = 1) -> None:
        """更新使用次数"""
        stmt = update(RequirementClassificationCategory).where(
            RequirementClassificationCategory.id == category_id
        ).values(
            usage_count=RequirementClassificationCategory.usage_count + increment
        )
        await self.session.execute(stmt)


class IRequirementClassificationAssignmentRepository(IBaseRepository[RequirementClassification]):
    """需求分类关联仓储接口"""
    
    @abstractmethod
    async def get_requirement_classifications(self, requirement_id: int) -> List[RequirementClassification]:
        """获取需求的所有分类"""
        pass
    
    @abstractmethod
    async def get_requirements_by_category(self, category_id: int) -> List[RequirementClassification]:
        """获取类别下的所有需求"""
        pass
    
    @abstractmethod
    async def remove_requirement_classifications(self, requirement_id: int, category_ids: List[int]) -> None:
        """移除需求的指定分类"""
        pass
    
    @abstractmethod
    async def get_classification_statistics(self, dimension_id: int) -> Dict[str, Any]:
        """获取分类统计信息"""
        pass


class RequirementClassificationAssignmentRepository(BaseRepository[RequirementClassification], IRequirementClassificationAssignmentRepository):
    """需求分类关联仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementClassification, session)
    
    async def get_requirement_classifications(self, requirement_id: int) -> List[RequirementClassification]:
        """获取需求的所有分类"""
        stmt = select(RequirementClassification).where(
            RequirementClassification.requirement_id == requirement_id
        ).options(
            joinedload(RequirementClassification.category).joinedload(RequirementClassificationCategory.dimension)
        )
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_requirements_by_category(self, category_id: int) -> List[RequirementClassification]:
        """获取类别下的所有需求"""
        stmt = select(RequirementClassification).where(
            RequirementClassification.category_id == category_id
        ).options(
            joinedload(RequirementClassification.requirement)
        )
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def remove_requirement_classifications(self, requirement_id: int, category_ids: List[int]) -> None:
        """移除需求的指定分类"""
        stmt = delete(RequirementClassification).where(
            and_(
                RequirementClassification.requirement_id == requirement_id,
                RequirementClassification.category_id.in_(category_ids)
            )
        )
        await self.session.execute(stmt)
    
    async def get_classification_statistics(self, dimension_id: int) -> Dict[str, Any]:
        """获取分类统计信息"""
        # 获取维度下各类别的需求数量统计
        stmt = select(
            RequirementClassificationCategory.id,
            RequirementClassificationCategory.category_name,
            func.count(RequirementClassification.id).label('requirement_count')
        ).select_from(
            RequirementClassificationCategory
        ).outerjoin(
            RequirementClassification,
            RequirementClassification.category_id == RequirementClassificationCategory.id
        ).where(
            RequirementClassificationCategory.dimension_id == dimension_id
        ).group_by(
            RequirementClassificationCategory.id,
            RequirementClassificationCategory.category_name
        )
        
        result = await self.session.execute(stmt)
        statistics = result.all()
        
        return {
            'dimension_id': dimension_id,
            'category_statistics': [
                {
                    'category_id': stat.id,
                    'category_name': stat.category_name,
                    'requirement_count': stat.requirement_count
                }
                for stat in statistics
            ],
            'total_requirements': sum(stat.requirement_count for stat in statistics)
        }


class IRequirementClassificationSuggestionRepository(IBaseRepository[RequirementClassificationSuggestion]):
    """需求分类建议仓储接口"""
    
    @abstractmethod
    async def get_pending_suggestions(self, requirement_id: int) -> List[RequirementClassificationSuggestion]:
        """获取待处理的分类建议"""
        pass
    
    @abstractmethod
    async def get_suggestions_by_confidence(self, min_confidence: float) -> List[RequirementClassificationSuggestion]:
        """根据置信度获取建议"""
        pass
    
    @abstractmethod
    async def expire_old_suggestions(self, days: int = 30) -> int:
        """使旧建议过期"""
        pass


class RequirementClassificationSuggestionRepository(BaseRepository[RequirementClassificationSuggestion], IRequirementClassificationSuggestionRepository):
    """需求分类建议仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementClassificationSuggestion, session)
    
    async def get_pending_suggestions(self, requirement_id: int) -> List[RequirementClassificationSuggestion]:
        """获取待处理的分类建议"""
        stmt = select(RequirementClassificationSuggestion).where(
            and_(
                RequirementClassificationSuggestion.requirement_id == requirement_id,
                RequirementClassificationSuggestion.status == ClassificationSuggestionStatus.PENDING,
                or_(
                    RequirementClassificationSuggestion.expires_at.is_(None),
                    RequirementClassificationSuggestion.expires_at > datetime.utcnow()
                )
            )
        ).options(
            joinedload(RequirementClassificationSuggestion.category)
        ).order_by(desc(RequirementClassificationSuggestion.confidence_score))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_suggestions_by_confidence(self, min_confidence: float) -> List[RequirementClassificationSuggestion]:
        """根据置信度获取建议"""
        stmt = select(RequirementClassificationSuggestion).where(
            and_(
                RequirementClassificationSuggestion.confidence_score >= min_confidence,
                RequirementClassificationSuggestion.status == ClassificationSuggestionStatus.PENDING
            )
        ).options(
            joinedload(RequirementClassificationSuggestion.requirement),
            joinedload(RequirementClassificationSuggestion.category)
        ).order_by(desc(RequirementClassificationSuggestion.confidence_score))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def expire_old_suggestions(self, days: int = 30) -> int:
        """使旧建议过期"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = update(RequirementClassificationSuggestion).where(
            and_(
                RequirementClassificationSuggestion.created_at < cutoff_date,
                RequirementClassificationSuggestion.status == ClassificationSuggestionStatus.PENDING
            )
        ).values(
            status=ClassificationSuggestionStatus.EXPIRED
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount


class IRequirementTagRepository(IBaseRepository[RequirementTag]):
    """需求标签仓储接口"""
    
    @abstractmethod
    async def get_by_name(self, tag_name: str) -> Optional[RequirementTag]:
        """根据标签名称获取标签"""
        pass
    
    @abstractmethod
    async def get_popular_tags(self, limit: int = 20) -> List[RequirementTag]:
        """获取热门标签"""
        pass
    
    @abstractmethod
    async def search_tags(self, keyword: str) -> List[RequirementTag]:
        """搜索标签"""
        pass


class RequirementTagRepository(BaseRepository[RequirementTag], IRequirementTagRepository):
    """需求标签仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementTag, session)
    
    async def get_by_name(self, tag_name: str) -> Optional[RequirementTag]:
        """根据标签名称获取标签"""
        stmt = select(RequirementTag).where(
            RequirementTag.tag_name == tag_name
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_popular_tags(self, limit: int = 20) -> List[RequirementTag]:
        """获取热门标签"""
        stmt = select(RequirementTag).where(
            RequirementTag.status == ClassificationStatus.ACTIVE
        ).order_by(desc(RequirementTag.usage_count)).limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def search_tags(self, keyword: str) -> List[RequirementTag]:
        """搜索标签"""
        stmt = select(RequirementTag).where(
            and_(
                RequirementTag.tag_name.ilike(f"%{keyword}%"),
                RequirementTag.status == ClassificationStatus.ACTIVE
            )
        ).order_by(RequirementTag.tag_name)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()