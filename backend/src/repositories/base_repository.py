"""
基础仓储模式实现

提供通用的CRUD操作和查询功能的基础仓储类
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select
from ..models.base import Base

T = TypeVar('T', bound=Base)


class IBaseRepository(ABC, Generic[T]):
    """基础仓储接口"""
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取实体"""
        pass
    
    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """获取所有实体"""
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建实体"""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """更新实体"""
        pass
    
    @abstractmethod
    async def delete(self, id: int) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计实体数量"""
        pass
    
    @abstractmethod
    async def exists(self, id: int) -> bool:
        """检查实体是否存在"""
        pass


class BaseRepository(IBaseRepository[T]):
    """基础仓储实现类"""
    
    def __init__(self, db: AsyncSession, model_class: type[T]):
        self.db = db
        self.model_class = model_class
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取实体"""
        query = select(self.model_class).where(self.model_class.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """获取所有实体"""
        query = select(self.model_class).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create(self, entity: T) -> T:
        """创建实体"""
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity
    
    async def update(self, entity: T) -> T:
        """更新实体"""
        await self.db.commit()
        await self.db.refresh(entity)
        return entity
    
    async def delete(self, id: int) -> bool:
        """删除实体"""
        query = delete(self.model_class).where(self.model_class.id == id)
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount > 0
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计实体数量"""
        query = select(func.count(self.model_class.id))
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    attr = getattr(self.model_class, key)
                    if isinstance(value, list):
                        conditions.append(attr.in_(value))
                    else:
                        conditions.append(attr == value)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def exists(self, id: int) -> bool:
        """检查实体是否存在"""
        query = select(func.count(self.model_class.id)).where(self.model_class.id == id)
        result = await self.db.execute(query)
        return result.scalar() > 0
    
    async def find_by_conditions(self, conditions: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[T]:
        """根据条件查询实体"""
        query = select(self.model_class)
        
        # 构建查询条件
        where_conditions = []
        for key, value in conditions.items():
            if hasattr(self.model_class, key):
                attr = getattr(self.model_class, key)
                if isinstance(value, list):
                    where_conditions.append(attr.in_(value))
                elif isinstance(value, dict):
                    # 支持范围查询等复杂条件
                    if 'gte' in value:
                        where_conditions.append(attr >= value['gte'])
                    if 'lte' in value:
                        where_conditions.append(attr <= value['lte'])
                    if 'gt' in value:
                        where_conditions.append(attr > value['gt'])
                    if 'lt' in value:
                        where_conditions.append(attr < value['lt'])
                    if 'like' in value:
                        where_conditions.append(attr.like(f"%{value['like']}%"))
                else:
                    where_conditions.append(attr == value)
        
        if where_conditions:
            query = query.where(and_(*where_conditions))
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def find_one_by_conditions(self, conditions: Dict[str, Any]) -> Optional[T]:
        """根据条件查询单个实体"""
        results = await self.find_by_conditions(conditions, limit=1)
        return results[0] if results else None
    
    async def bulk_create(self, entities: List[T]) -> List[T]:
        """批量创建实体"""
        self.db.add_all(entities)
        await self.db.commit()
        for entity in entities:
            await self.db.refresh(entity)
        return entities
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """批量更新实体"""
        if not updates:
            return 0
        
        # 假设每个更新字典都包含id字段
        updated_count = 0
        for update_data in updates:
            entity_id = update_data.pop('id')
            if update_data:  # 确保有要更新的字段
                query = update(self.model_class).where(self.model_class.id == entity_id).values(**update_data)
                result = await self.db.execute(query)
                updated_count += result.rowcount
        
        await self.db.commit()
        return updated_count
    
    async def bulk_delete(self, ids: List[int]) -> int:
        """批量删除实体"""
        if not ids:
            return 0
        
        query = delete(self.model_class).where(self.model_class.id.in_(ids))
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount