"""
查询优化工具

本模块提供SQL查询优化的工具函数和装饰器，包括：
1. 查询缓存装饰器
2. 批量操作优化
3. 预加载优化
4. 分页查询优化
5. 查询性能监控

主要功能：
- 自动查询缓存
- 智能预加载关联数据
- 批量操作优化
- 查询性能分析
"""
import asyncio
import functools
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select
from sqlalchemy import and_, or_, func

from ..utils.redis_client import RedisCache
from ..services.database_optimization_service import get_database_optimization_service

logger = logging.getLogger(__name__)

T = TypeVar('T')


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.cache = RedisCache("query_optimizer")
        self.performance_cache = RedisCache("query_performance")
    
    def cached_query(self, 
                    cache_key_template: str, 
                    ttl: int = 300,
                    cache_condition: Optional[Callable] = None):
        """
        查询缓存装饰器
        
        Args:
            cache_key_template: 缓存键模板，支持参数替换
            ttl: 缓存过期时间（秒）
            cache_condition: 缓存条件函数，返回True时才缓存
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = self._generate_cache_key(cache_key_template, args, kwargs)
                
                # 尝试从缓存获取
                cached_result = await self.cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"查询缓存命中: {cache_key}")
                    return cached_result
                
                # 执行原函数
                start_time = time.time()
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 检查是否需要缓存
                should_cache = True
                if cache_condition:
                    should_cache = cache_condition(result, execution_time)
                
                # 缓存结果
                if should_cache:
                    await self.cache.set(cache_key, result, ttl)
                    logger.debug(f"查询结果已缓存: {cache_key} (耗时: {execution_time:.3f}s)")
                
                return result
            
            return wrapper
        return decorator
    
    def _generate_cache_key(self, template: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        try:
            # 简单的参数替换
            key_parts = [template]
            
            # 添加位置参数
            for i, arg in enumerate(args):
                if isinstance(arg, (int, str, float)):
                    key_parts.append(f"arg{i}_{arg}")
            
            # 添加关键字参数
            for key, value in kwargs.items():
                if isinstance(value, (int, str, float, bool)) and value is not None:
                    key_parts.append(f"{key}_{value}")
            
            return ":".join(str(part) for part in key_parts)
            
        except Exception as e:
            logger.warning(f"生成缓存键失败: {e}")
            return f"{template}:fallback:{hash(str(args) + str(kwargs))}"
    
    def performance_monitor(self, operation_name: str):
        """
        性能监控装饰器
        
        Args:
            operation_name: 操作名称
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # 记录性能数据
                    await self._record_performance(
                        operation_name, execution_time, True, len(result) if hasattr(result, '__len__') else 1
                    )
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    # 记录错误性能数据
                    await self._record_performance(operation_name, execution_time, False, 0)
                    
                    raise
            
            return wrapper
        return decorator
    
    async def _record_performance(self, operation: str, execution_time: float, success: bool, result_count: int):
        """记录性能数据"""
        try:
            performance_data = {
                "operation": operation,
                "execution_time": execution_time,
                "success": success,
                "result_count": result_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 存储到性能缓存
            cache_key = f"perf:{operation}:{int(time.time())}"
            await self.performance_cache.set(cache_key, performance_data, 3600)  # 1小时
            
        except Exception as e:
            logger.warning(f"记录性能数据失败: {e}")


# 全局查询优化器实例
query_optimizer = QueryOptimizer()


def with_preload(*relationships):
    """
    预加载关联数据装饰器
    
    Args:
        relationships: 要预加载的关联关系
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 如果函数参数中有query，添加预加载
            if 'query' in kwargs:
                query = kwargs['query']
                for rel in relationships:
                    if hasattr(rel, '__name__'):
                        query = query.options(selectinload(rel))
                    else:
                        query = query.options(selectinload(rel))
                kwargs['query'] = query
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def batch_operation(batch_size: int = 100):
    """
    批量操作装饰器
    
    Args:
        batch_size: 批处理大小
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 检查是否有数据列表参数
            data_list = None
            data_key = None
            
            for key, value in kwargs.items():
                if isinstance(value, list) and len(value) > batch_size:
                    data_list = value
                    data_key = key
                    break
            
            if data_list and len(data_list) > batch_size:
                # 分批处理
                results = []
                for i in range(0, len(data_list), batch_size):
                    batch_data = data_list[i:i + batch_size]
                    batch_kwargs = kwargs.copy()
                    batch_kwargs[data_key] = batch_data
                    
                    batch_result = await func(*args, **batch_kwargs)
                    results.extend(batch_result if isinstance(batch_result, list) else [batch_result])
                
                return results
            else:
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class PaginationOptimizer:
    """分页查询优化器"""
    
    @staticmethod
    def optimize_pagination(query: Select, page: int, size: int, max_size: int = 100) -> Select:
        """
        优化分页查询
        
        Args:
            query: 原始查询
            page: 页码（从1开始）
            size: 每页大小
            max_size: 最大每页大小
            
        Returns:
            优化后的查询
        """
        # 限制每页大小
        size = min(size, max_size)
        
        # 计算偏移量
        offset = (page - 1) * size
        
        # 添加分页
        return query.limit(size).offset(offset)
    
    @staticmethod
    async def get_paginated_result(session: AsyncSession, 
                                 query: Select, 
                                 page: int, 
                                 size: int,
                                 count_query: Optional[Select] = None) -> Dict[str, Any]:
        """
        获取分页结果
        
        Args:
            session: 数据库会话
            query: 数据查询
            page: 页码
            size: 每页大小
            count_query: 计数查询（可选）
            
        Returns:
            分页结果
        """
        # 优化分页查询
        paginated_query = PaginationOptimizer.optimize_pagination(query, page, size)
        
        # 执行数据查询
        result = await session.execute(paginated_query)
        items = result.scalars().all()
        
        # 执行计数查询（如果需要）
        total = None
        if count_query:
            count_result = await session.execute(count_query)
            total = count_result.scalar()
        
        return {
            "items": items,
            "page": page,
            "size": size,
            "total": total,
            "has_next": len(items) == size,
            "has_prev": page > 1
        }


class QueryBuilder:
    """查询构建器"""
    
    @staticmethod
    def build_filter_conditions(model_class, filters: Dict[str, Any]) -> List[Any]:
        """
        构建过滤条件
        
        Args:
            model_class: 模型类
            filters: 过滤条件字典
            
        Returns:
            过滤条件列表
        """
        conditions = []
        
        for field, value in filters.items():
            if value is None:
                continue
            
            # 获取模型字段
            if hasattr(model_class, field):
                model_field = getattr(model_class, field)
                
                if isinstance(value, dict):
                    # 复杂条件
                    for op, op_value in value.items():
                        if op == 'eq':
                            conditions.append(model_field == op_value)
                        elif op == 'ne':
                            conditions.append(model_field != op_value)
                        elif op == 'gt':
                            conditions.append(model_field > op_value)
                        elif op == 'gte':
                            conditions.append(model_field >= op_value)
                        elif op == 'lt':
                            conditions.append(model_field < op_value)
                        elif op == 'lte':
                            conditions.append(model_field <= op_value)
                        elif op == 'in':
                            conditions.append(model_field.in_(op_value))
                        elif op == 'like':
                            conditions.append(model_field.like(f"%{op_value}%"))
                        elif op == 'ilike':
                            conditions.append(model_field.ilike(f"%{op_value}%"))
                else:
                    # 简单相等条件
                    conditions.append(model_field == value)
        
        return conditions
    
    @staticmethod
    def build_order_by(model_class, order_by: Union[str, List[str]]) -> List[Any]:
        """
        构建排序条件
        
        Args:
            model_class: 模型类
            order_by: 排序字段
            
        Returns:
            排序条件列表
        """
        if isinstance(order_by, str):
            order_by = [order_by]
        
        order_conditions = []
        
        for field in order_by:
            desc = False
            if field.startswith('-'):
                desc = True
                field = field[1:]
            
            if hasattr(model_class, field):
                model_field = getattr(model_class, field)
                if desc:
                    order_conditions.append(model_field.desc())
                else:
                    order_conditions.append(model_field.asc())
        
        return order_conditions


# 便捷装饰器
cached_query = query_optimizer.cached_query
performance_monitor = query_optimizer.performance_monitor


# 使用示例装饰器
def example_usage():
    """使用示例"""
    
    @cached_query("ai_sessions:{user_id}", ttl=300)
    @performance_monitor("get_ai_sessions")
    async def get_ai_sessions(session: AsyncSession, user_id: int):
        """获取AI会话（带缓存和性能监控）"""
        pass
    
    @batch_operation(batch_size=50)
    async def batch_insert_messages(session: AsyncSession, messages: List[Dict]):
        """批量插入消息"""
        pass
    
    @with_preload('user', 'messages')
    async def get_session_with_details(session: AsyncSession, session_id: int):
        """获取会话详情（带预加载）"""
        pass