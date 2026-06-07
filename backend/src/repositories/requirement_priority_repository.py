"""
需求优先级仓储实现

提供需求优先级管理相关的数据访问功能，包括：
- 优先级配置管理
- 优先级评估管理
- 优先级冲突管理
- 优先级历史管理
"""
from abc import abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text, update, delete
from sqlalchemy.orm import selectinload, joinedload

from .base_repository import BaseRepository, IBaseRepository
from ..models.requirement_priority import (
    RequirementPriorityConfig, RequirementPriorityEvaluation,
    RequirementPriorityConflict, RequirementPriorityHistory,
    PriorityCalculationMethod, PriorityFactorType, ConflictResolutionStrategy,
    PriorityConflictStatus
)
from ..models.requirement import Priority


class IRequirementPriorityConfigRepository(IBaseRepository[RequirementPriorityConfig]):
    """需求优先级配置仓储接口"""
    
    @abstractmethod
    async def get_by_project_id(self, project_id: int) -> List[RequirementPriorityConfig]:
        """根据项目ID获取优先级配置"""
        pass
    
    @abstractmethod
    async def get_default_config(self, project_id: int) -> Optional[RequirementPriorityConfig]:
        """获取项目的默认优先级配置"""
        pass
    
    @abstractmethod
    async def get_active_configs(self, project_id: int) -> List[RequirementPriorityConfig]:
        """获取项目的激活配置"""
        pass


class RequirementPriorityConfigRepository(BaseRepository[RequirementPriorityConfig], IRequirementPriorityConfigRepository):
    """需求优先级配置仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementPriorityConfig, session)
    
    async def get_by_project_id(self, project_id: int) -> List[RequirementPriorityConfig]:
        """根据项目ID获取优先级配置"""
        stmt = select(RequirementPriorityConfig).where(
            RequirementPriorityConfig.project_id == project_id
        ).order_by(desc(RequirementPriorityConfig.is_default), RequirementPriorityConfig.created_at)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_default_config(self, project_id: int) -> Optional[RequirementPriorityConfig]:
        """获取项目的默认优先级配置"""
        stmt = select(RequirementPriorityConfig).where(
            and_(
                RequirementPriorityConfig.project_id == project_id,
                RequirementPriorityConfig.is_default == True,
                RequirementPriorityConfig.is_active == True
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_configs(self, project_id: int) -> List[RequirementPriorityConfig]:
        """获取项目的激活配置"""
        stmt = select(RequirementPriorityConfig).where(
            and_(
                RequirementPriorityConfig.project_id == project_id,
                RequirementPriorityConfig.is_active == True
            )
        ).order_by(desc(RequirementPriorityConfig.is_default), RequirementPriorityConfig.created_at)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()


class IRequirementPriorityEvaluationRepository(IBaseRepository[RequirementPriorityEvaluation]):
    """需求优先级评估仓储接口"""
    
    @abstractmethod
    async def get_current_evaluation(self, requirement_id: int) -> Optional[RequirementPriorityEvaluation]:
        """获取需求的当前优先级评估"""
        pass
    
    @abstractmethod
    async def get_evaluations_by_requirement(self, requirement_id: int) -> List[RequirementPriorityEvaluation]:
        """获取需求的所有优先级评估历史"""
        pass
    
    @abstractmethod
    async def get_evaluations_by_config(self, config_id: int) -> List[RequirementPriorityEvaluation]:
        """根据配置ID获取评估列表"""
        pass
    
    @abstractmethod
    async def set_current_evaluation(self, requirement_id: int, evaluation_id: int) -> None:
        """设置当前有效的评估"""
        pass
    
    @abstractmethod
    async def get_priority_distribution(self, project_id: int) -> Dict[str, int]:
        """获取项目的优先级分布统计"""
        pass


class RequirementPriorityEvaluationRepository(BaseRepository[RequirementPriorityEvaluation], IRequirementPriorityEvaluationRepository):
    """需求优先级评估仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementPriorityEvaluation, session)
    
    async def get_current_evaluation(self, requirement_id: int) -> Optional[RequirementPriorityEvaluation]:
        """获取需求的当前优先级评估"""
        stmt = select(RequirementPriorityEvaluation).where(
            and_(
                RequirementPriorityEvaluation.requirement_id == requirement_id,
                RequirementPriorityEvaluation.is_current == True
            )
        ).options(
            joinedload(RequirementPriorityEvaluation.config)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_evaluations_by_requirement(self, requirement_id: int) -> List[RequirementPriorityEvaluation]:
        """获取需求的所有优先级评估历史"""
        stmt = select(RequirementPriorityEvaluation).where(
            RequirementPriorityEvaluation.requirement_id == requirement_id
        ).options(
            joinedload(RequirementPriorityEvaluation.config)
        ).order_by(desc(RequirementPriorityEvaluation.created_at))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_evaluations_by_config(self, config_id: int) -> List[RequirementPriorityEvaluation]:
        """根据配置ID获取评估列表"""
        stmt = select(RequirementPriorityEvaluation).where(
            RequirementPriorityEvaluation.config_id == config_id
        ).options(
            joinedload(RequirementPriorityEvaluation.requirement)
        ).order_by(desc(RequirementPriorityEvaluation.weighted_score))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def set_current_evaluation(self, requirement_id: int, evaluation_id: int) -> None:
        """设置当前有效的评估"""
        # 首先将该需求的所有评估设为非当前
        stmt_update_old = update(RequirementPriorityEvaluation).where(
            RequirementPriorityEvaluation.requirement_id == requirement_id
        ).values(is_current=False)
        await self.session.execute(stmt_update_old)
        
        # 然后设置指定评估为当前
        stmt_update_new = update(RequirementPriorityEvaluation).where(
            RequirementPriorityEvaluation.id == evaluation_id
        ).values(is_current=True)
        await self.session.execute(stmt_update_new)
    
    async def get_priority_distribution(self, project_id: int) -> Dict[str, int]:
        """获取项目的优先级分布统计"""
        # 通过需求表关联获取项目的优先级分布
        from ..models.requirement import Requirement
        
        stmt = select(
            RequirementPriorityEvaluation.final_priority,
            func.count(RequirementPriorityEvaluation.id).label('count')
        ).select_from(
            RequirementPriorityEvaluation
        ).join(
            Requirement,
            Requirement.id == RequirementPriorityEvaluation.requirement_id
        ).where(
            and_(
                Requirement.project_id == project_id,
                RequirementPriorityEvaluation.is_current == True
            )
        ).group_by(RequirementPriorityEvaluation.final_priority)
        
        result = await self.session.execute(stmt)
        distribution = result.all()
        
        # 转换为字典格式
        priority_dist = {}
        for priority, count in distribution:
            if priority:
                priority_dist[priority.value] = count
        
        return priority_dist


class IRequirementPriorityConflictRepository(IBaseRepository[RequirementPriorityConflict]):
    """需求优先级冲突仓储接口"""
    
    @abstractmethod
    async def get_active_conflicts(self) -> List[RequirementPriorityConflict]:
        """获取活跃的优先级冲突"""
        pass
    
    @abstractmethod
    async def get_conflicts_by_requirements(self, requirement_ids: List[int]) -> List[RequirementPriorityConflict]:
        """根据需求ID列表获取相关冲突"""
        pass
    
    @abstractmethod
    async def get_conflicts_by_severity(self, min_severity: int) -> List[RequirementPriorityConflict]:
        """根据严重程度获取冲突"""
        pass
    
    @abstractmethod
    async def resolve_conflict(self, conflict_id: int, resolver_id: int, resolution_notes: str) -> None:
        """解决冲突"""
        pass


class RequirementPriorityConflictRepository(BaseRepository[RequirementPriorityConflict], IRequirementPriorityConflictRepository):
    """需求优先级冲突仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementPriorityConflict, session)
    
    async def get_active_conflicts(self) -> List[RequirementPriorityConflict]:
        """获取活跃的优先级冲突"""
        stmt = select(RequirementPriorityConflict).where(
            RequirementPriorityConflict.status.in_([
                PriorityConflictStatus.DETECTED,
                PriorityConflictStatus.UNDER_REVIEW
            ])
        ).order_by(
            desc(RequirementPriorityConflict.severity_level),
            RequirementPriorityConflict.created_at
        )
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_conflicts_by_requirements(self, requirement_ids: List[int]) -> List[RequirementPriorityConflict]:
        """根据需求ID列表获取相关冲突"""
        # 使用JSON查询来检查requirement_ids字段中是否包含指定的需求ID
        conditions = []
        for req_id in requirement_ids:
            conditions.append(
                text(f"JSON_CONTAINS(requirement_ids, '{req_id}')")
            )
        
        stmt = select(RequirementPriorityConflict).where(
            or_(*conditions)
        ).order_by(desc(RequirementPriorityConflict.severity_level))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_conflicts_by_severity(self, min_severity: int) -> List[RequirementPriorityConflict]:
        """根据严重程度获取冲突"""
        stmt = select(RequirementPriorityConflict).where(
            and_(
                RequirementPriorityConflict.severity_level >= min_severity,
                RequirementPriorityConflict.status != PriorityConflictStatus.RESOLVED
            )
        ).order_by(desc(RequirementPriorityConflict.severity_level))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def resolve_conflict(self, conflict_id: int, resolver_id: int, resolution_notes: str) -> None:
        """解决冲突"""
        stmt = update(RequirementPriorityConflict).where(
            RequirementPriorityConflict.id == conflict_id
        ).values(
            status=PriorityConflictStatus.RESOLVED,
            resolved_by=resolver_id,
            resolved_at=datetime.utcnow(),
            resolution_notes=resolution_notes
        )
        await self.session.execute(stmt)


class IRequirementPriorityHistoryRepository(IBaseRepository[RequirementPriorityHistory]):
    """需求优先级历史仓储接口"""
    
    @abstractmethod
    async def get_priority_history(self, requirement_id: int) -> List[RequirementPriorityHistory]:
        """获取需求的优先级变更历史"""
        pass
    
    @abstractmethod
    async def get_recent_changes(self, days: int = 7) -> List[RequirementPriorityHistory]:
        """获取最近的优先级变更"""
        pass
    
    @abstractmethod
    async def get_changes_by_user(self, user_id: int, days: int = 30) -> List[RequirementPriorityHistory]:
        """获取用户的优先级变更记录"""
        pass


class RequirementPriorityHistoryRepository(BaseRepository[RequirementPriorityHistory], IRequirementPriorityHistoryRepository):
    """需求优先级历史仓储实现"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(RequirementPriorityHistory, session)
    
    async def get_priority_history(self, requirement_id: int) -> List[RequirementPriorityHistory]:
        """获取需求的优先级变更历史"""
        stmt = select(RequirementPriorityHistory).where(
            RequirementPriorityHistory.requirement_id == requirement_id
        ).order_by(desc(RequirementPriorityHistory.changed_at))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_recent_changes(self, days: int = 7) -> List[RequirementPriorityHistory]:
        """获取最近的优先级变更"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(RequirementPriorityHistory).where(
            RequirementPriorityHistory.changed_at >= cutoff_date
        ).options(
            joinedload(RequirementPriorityHistory.requirement)
        ).order_by(desc(RequirementPriorityHistory.changed_at))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_changes_by_user(self, user_id: int, days: int = 30) -> List[RequirementPriorityHistory]:
        """获取用户的优先级变更记录"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(RequirementPriorityHistory).where(
            and_(
                RequirementPriorityHistory.changed_by == user_id,
                RequirementPriorityHistory.changed_at >= cutoff_date
            )
        ).options(
            joinedload(RequirementPriorityHistory.requirement)
        ).order_by(desc(RequirementPriorityHistory.changed_at))
        
        result = await self.session.execute(stmt)
        return result.scalars().all()