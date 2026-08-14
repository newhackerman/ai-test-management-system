"""
数据库查询性能优化服务

本模块提供数据库查询性能优化功能，包括：
1. 查询性能监控和分析
2. 索引优化建议
3. 查询缓存管理
4. 连接池优化
5. 慢查询检测和优化

主要功能：
- 自动检测慢查询
- 生成索引优化建议
- 查询结果缓存
- 数据库连接池监控
- 查询性能统计分析
"""
import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select

from ..core.database import get_async_session, get_async_session_ctx
from ..core.config import get_settings
from ..utils.redis_client import RedisCache

logger = logging.getLogger(__name__)
settings = get_settings()


class QueryType(Enum):
    """查询类型枚举"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    JOIN = "JOIN"
    AGGREGATE = "AGGREGATE"


@dataclass
class QueryPerformanceMetrics:
    """查询性能指标"""
    query_id: str
    query_type: QueryType
    execution_time: float
    rows_examined: int
    rows_returned: int
    cpu_usage: float
    memory_usage: float
    cache_hit: bool
    timestamp: datetime


@dataclass
class IndexRecommendation:
    """索引优化建议"""
    table_name: str
    columns: List[str]
    index_type: str
    estimated_improvement: float
    priority: str
    reason: str


class DatabaseOptimizationService:
    """数据库优化服务"""
    
    def __init__(self):
        self.query_cache = RedisCache("query_cache")
        self.performance_cache = RedisCache("performance")
        
        # 性能监控配置
        self.slow_query_threshold = 1.0  # 1秒
        self.cache_ttl = 300  # 5分钟
        self.max_cache_size = 1000
        
        # 性能统计
        self.query_stats = {
            "total_queries": 0,
            "slow_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_execution_time": 0.0
        }
        
        # 慢查询记录
        self.slow_queries = []
        self.max_slow_queries = 100
    
    async def execute_optimized_query(self, 
                                    session: AsyncSession,
                                    query: Select,
                                    cache_key: Optional[str] = None,
                                    cache_ttl: Optional[int] = None) -> Any:
        """
        执行优化的查询
        
        Args:
            session: 数据库会话
            query: SQL查询对象
            cache_key: 缓存键
            cache_ttl: 缓存过期时间
            
        Returns:
            查询结果
        """
        start_time = time.time()
        
        try:
            # 1. 尝试从缓存获取结果
            if cache_key:
                cached_result = await self.query_cache.get(cache_key)
                if cached_result is not None:
                    self.query_stats["cache_hits"] += 1
                    logger.debug(f"查询缓存命中: {cache_key}")
                    return cached_result
                else:
                    self.query_stats["cache_misses"] += 1
            
            # 2. 执行查询
            result = await session.execute(query)
            data = result.scalars().all() if hasattr(result, 'scalars') else result.fetchall()
            
            # 3. 计算执行时间
            execution_time = time.time() - start_time
            
            # 4. 记录性能指标
            await self._record_query_performance(query, execution_time, len(data) if data else 0)
            
            # 5. 缓存结果
            if cache_key and execution_time > 0.1:  # 只缓存执行时间较长的查询
                ttl = cache_ttl or self.cache_ttl
                await self.query_cache.set(cache_key, data, ttl)
            
            return data
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"查询执行失败 (耗时: {execution_time:.3f}s): {e}")
            raise
    
    async def _record_query_performance(self, query: Select, execution_time: float, rows_count: int):
        """记录查询性能"""
        self.query_stats["total_queries"] += 1
        
        # 更新平均执行时间
        total_queries = self.query_stats["total_queries"]
        current_avg = self.query_stats["avg_execution_time"]
        self.query_stats["avg_execution_time"] = (
            (current_avg * (total_queries - 1) + execution_time) / total_queries
        )
        
        # 检测慢查询
        if execution_time > self.slow_query_threshold:
            self.query_stats["slow_queries"] += 1
            
            # 记录慢查询详情
            slow_query_info = {
                "query": str(query),
                "execution_time": execution_time,
                "rows_count": rows_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.slow_queries.append(slow_query_info)
            
            # 限制慢查询记录数量
            if len(self.slow_queries) > self.max_slow_queries:
                self.slow_queries.pop(0)
            
            logger.warning(f"检测到慢查询 (耗时: {execution_time:.3f}s, 行数: {rows_count})")
    
    async def get_ai_chat_sessions_optimized(self, 
                                           user_id: int, 
                                           limit: int = 20, 
                                           offset: int = 0) -> List[Any]:
        """
        优化的AI聊天会话查询
        """
        cache_key = f"ai_sessions:{user_id}:{limit}:{offset}"
        
        async with get_async_session_ctx() as session:
            from ..models.ai_chat_session import AIChatSession
            
            # 使用索引优化的查询
            query = (
                select(AIChatSession)
                .where(AIChatSession.user_id == user_id)
                .order_by(AIChatSession.last_activity_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            return await self.execute_optimized_query(session, query, cache_key)
    
    async def get_ai_chat_messages_optimized(self, 
                                           session_id: int, 
                                           limit: int = 50) -> List[Any]:
        """
        优化的AI聊天消息查询
        """
        cache_key = f"ai_messages:{session_id}:{limit}"
        
        async with get_async_session_ctx() as session:
            from ..models.ai_chat_message import AIChatMessage
            
            # 使用预加载优化查询
            query = (
                select(AIChatMessage)
                .where(AIChatMessage.session_id == session_id)
                .order_by(AIChatMessage.created_at.desc())
                .limit(limit)
            )
            
            return await self.execute_optimized_query(session, query, cache_key)
    
    async def get_ai_suggestions_optimized(self, 
                                         user_id: int, 
                                         project_id: Optional[int] = None,
                                         status: Optional[str] = None) -> List[Any]:
        """
        优化的AI建议查询
        """
        cache_parts = [str(user_id)]
        if project_id:
            cache_parts.append(str(project_id))
        if status:
            cache_parts.append(status)
        
        cache_key = f"ai_suggestions:{':'.join(cache_parts)}"
        
        async with get_async_session_ctx() as session:
            from ..models.ai_suggestion import AISuggestion
            
            # 构建动态查询条件
            conditions = [AISuggestion.user_id == user_id]
            
            if project_id:
                conditions.append(AISuggestion.project_id == project_id)
            
            if status:
                conditions.append(AISuggestion.status == status)
            
            query = (
                select(AISuggestion)
                .where(and_(*conditions))
                .order_by(AISuggestion.created_at.desc())
            )
            
            return await self.execute_optimized_query(session, query, cache_key)  
  
    async def analyze_query_performance(self) -> Dict[str, Any]:
        """
        分析查询性能
        
        Returns:
            性能分析报告
        """
        total_queries = self.query_stats["total_queries"]
        
        if total_queries == 0:
            return {
                "status": "no_data",
                "message": "暂无查询数据"
            }
        
        slow_query_rate = self.query_stats["slow_queries"] / total_queries
        cache_hit_rate = self.query_stats["cache_hits"] / (
            self.query_stats["cache_hits"] + self.query_stats["cache_misses"]
        ) if (self.query_stats["cache_hits"] + self.query_stats["cache_misses"]) > 0 else 0
        
        # 性能等级评估
        performance_grade = "A"
        if slow_query_rate > 0.1:
            performance_grade = "C"
        elif slow_query_rate > 0.05:
            performance_grade = "B"
        
        return {
            "performance_grade": performance_grade,
            "total_queries": total_queries,
            "slow_queries": self.query_stats["slow_queries"],
            "slow_query_rate": round(slow_query_rate * 100, 2),
            "avg_execution_time": round(self.query_stats["avg_execution_time"], 3),
            "cache_hit_rate": round(cache_hit_rate * 100, 2),
            "cache_hits": self.query_stats["cache_hits"],
            "cache_misses": self.query_stats["cache_misses"],
            "recent_slow_queries": self.slow_queries[-10:] if self.slow_queries else []
        }
    
    async def generate_index_recommendations(self) -> List[IndexRecommendation]:
        """
        生成索引优化建议
        
        Returns:
            索引建议列表
        """
        recommendations = []
        
        # 基于慢查询分析生成索引建议
        for slow_query in self.slow_queries[-20:]:  # 分析最近20个慢查询
            query_str = slow_query["query"].lower()
            
            # 分析WHERE条件
            if "where" in query_str:
                # AI聊天会话表优化
                if "ai_chat_sessions" in query_str and "user_id" in query_str:
                    recommendations.append(IndexRecommendation(
                        table_name="ai_chat_sessions",
                        columns=["user_id", "last_activity_at"],
                        index_type="COMPOSITE",
                        estimated_improvement=0.6,
                        priority="HIGH",
                        reason="用户会话查询频繁，复合索引可显著提升性能"
                    ))
                
                # AI聊天消息表优化
                if "ai_chat_messages" in query_str and "session_id" in query_str:
                    recommendations.append(IndexRecommendation(
                        table_name="ai_chat_messages",
                        columns=["session_id", "created_at"],
                        index_type="COMPOSITE",
                        estimated_improvement=0.7,
                        priority="HIGH",
                        reason="会话消息查询频繁，时间排序需要复合索引"
                    ))
                
                # AI建议表优化
                if "ai_suggestions" in query_str:
                    if "user_id" in query_str and "project_id" in query_str:
                        recommendations.append(IndexRecommendation(
                            table_name="ai_suggestions",
                            columns=["user_id", "project_id", "status"],
                            index_type="COMPOSITE",
                            estimated_improvement=0.5,
                            priority="MEDIUM",
                            reason="多条件查询建议表，复合索引提升过滤效率"
                        ))
        
        # 去重建议
        unique_recommendations = []
        seen_combinations = set()
        
        for rec in recommendations:
            key = (rec.table_name, tuple(rec.columns))
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    async def optimize_database_connections(self) -> Dict[str, Any]:
        """
        优化数据库连接
        
        Returns:
            连接优化结果
        """
        try:
            async with get_async_session_ctx() as session:
                # 检查连接池状态
                pool_status = await self._check_connection_pool_status(session)
                
                # 检查活跃连接数
                active_connections = await self._get_active_connections_count(session)
                
                # 检查锁等待情况
                lock_waits = await self._check_lock_waits(session)
                
                # 生成优化建议
                optimization_suggestions = []
                
                if active_connections > 50:
                    optimization_suggestions.append(
                        "活跃连接数较高，建议增加连接池大小或优化查询"
                    )
                
                if lock_waits > 10:
                    optimization_suggestions.append(
                        "检测到较多锁等待，建议优化事务处理逻辑"
                    )
                
                return {
                    "pool_status": pool_status,
                    "active_connections": active_connections,
                    "lock_waits": lock_waits,
                    "optimization_suggestions": optimization_suggestions,
                    "status": "healthy" if len(optimization_suggestions) == 0 else "needs_attention"
                }
                
        except Exception as e:
            logger.error(f"数据库连接优化检查失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _check_connection_pool_status(self, session: AsyncSession) -> Dict[str, Any]:
        """检查连接池状态"""
        try:
            # 获取连接池信息
            result = await session.execute(text("SHOW STATUS LIKE 'Threads_%'"))
            threads_info = {row[0]: row[1] for row in result.fetchall()}
            
            return {
                "threads_connected": threads_info.get("Threads_connected", 0),
                "threads_running": threads_info.get("Threads_running", 0),
                "threads_cached": threads_info.get("Threads_cached", 0)
            }
        except Exception as e:
            logger.warning(f"获取连接池状态失败: {e}")
            return {"error": str(e)}
    
    async def _get_active_connections_count(self, session: AsyncSession) -> int:
        """获取活跃连接数"""
        try:
            result = await session.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
            row = result.fetchone()
            return int(row[1]) if row else 0
        except Exception as e:
            logger.warning(f"获取活跃连接数失败: {e}")
            return 0
    
    async def _check_lock_waits(self, session: AsyncSession) -> int:
        """检查锁等待情况"""
        try:
            result = await session.execute(text(
                "SELECT COUNT(*) FROM information_schema.INNODB_LOCKS"
            ))
            row = result.fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            logger.warning(f"检查锁等待失败: {e}")
            return 0
    
    async def clear_query_cache(self, pattern: Optional[str] = None) -> int:
        """
        清除查询缓存
        
        Args:
            pattern: 缓存键模式，为空则清除所有
            
        Returns:
            清除的缓存数量
        """
        if pattern:
            return await self.query_cache.clear_pattern(pattern)
        else:
            return await self.query_cache.clear_pattern("*")
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计数据
        """
        total_requests = self.query_stats["cache_hits"] + self.query_stats["cache_misses"]
        hit_rate = (self.query_stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self.query_stats["cache_hits"],
            "cache_misses": self.query_stats["cache_misses"],
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    async def execute_batch_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行批量操作优化
        
        Args:
            operations: 批量操作列表
            
        Returns:
            执行结果
        """
        start_time = time.time()
        results = []
        
        try:
            async with get_async_session_ctx() as session:
                # 开启事务
                async with session.begin():
                    for operation in operations:
                        op_type = operation.get("type")
                        
                        if op_type == "insert":
                            result = await self._batch_insert(session, operation)
                        elif op_type == "update":
                            result = await self._batch_update(session, operation)
                        elif op_type == "delete":
                            result = await self._batch_delete(session, operation)
                        else:
                            result = {"error": f"不支持的操作类型: {op_type}"}
                        
                        results.append(result)
                
                execution_time = time.time() - start_time
                
                return {
                    "success": True,
                    "execution_time": round(execution_time, 3),
                    "operations_count": len(operations),
                    "results": results
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"批量操作执行失败 (耗时: {execution_time:.3f}s): {e}")
            
            return {
                "success": False,
                "execution_time": round(execution_time, 3),
                "error": str(e),
                "completed_operations": len(results)
            }
    
    async def _batch_insert(self, session: AsyncSession, operation: Dict[str, Any]) -> Dict[str, Any]:
        """批量插入操作"""
        try:
            table_name = operation["table"]
            data_list = operation["data"]
            
            # 这里应该根据具体的模型类进行批量插入
            # 示例实现
            insert_count = len(data_list)
            
            return {
                "type": "insert",
                "table": table_name,
                "inserted_count": insert_count,
                "success": True
            }
            
        except Exception as e:
            return {
                "type": "insert",
                "success": False,
                "error": str(e)
            }
    
    async def _batch_update(self, session: AsyncSession, operation: Dict[str, Any]) -> Dict[str, Any]:
        """批量更新操作"""
        try:
            table_name = operation["table"]
            conditions = operation["conditions"]
            updates = operation["updates"]
            
            # 这里应该根据具体的模型类进行批量更新
            # 示例实现
            updated_count = 1  # 实际应该执行更新并返回影响行数
            
            return {
                "type": "update",
                "table": table_name,
                "updated_count": updated_count,
                "success": True
            }
            
        except Exception as e:
            return {
                "type": "update",
                "success": False,
                "error": str(e)
            }
    
    async def _batch_delete(self, session: AsyncSession, operation: Dict[str, Any]) -> Dict[str, Any]:
        """批量删除操作"""
        try:
            table_name = operation["table"]
            conditions = operation["conditions"]
            
            # 这里应该根据具体的模型类进行批量删除
            # 示例实现
            deleted_count = 1  # 实际应该执行删除并返回影响行数
            
            return {
                "type": "delete",
                "table": table_name,
                "deleted_count": deleted_count,
                "success": True
            }
            
        except Exception as e:
            return {
                "type": "delete",
                "success": False,
                "error": str(e)
            }


# 全局优化服务实例
_optimization_service = None

async def get_database_optimization_service() -> DatabaseOptimizationService:
    """获取数据库优化服务实例"""
    global _optimization_service
    
    if _optimization_service is None:
        _optimization_service = DatabaseOptimizationService()
    
    return _optimization_service


# 便捷函数
async def execute_optimized_query(session: AsyncSession, 
                                query: Select, 
                                cache_key: Optional[str] = None) -> Any:
    """执行优化查询的便捷函数"""
    service = await get_database_optimization_service()
    return await service.execute_optimized_query(session, query, cache_key)


async def clear_all_cache() -> int:
    """清除所有查询缓存"""
    service = await get_database_optimization_service()
    return await service.clear_query_cache()


async def get_performance_report() -> Dict[str, Any]:
    """获取性能报告"""
    service = await get_database_optimization_service()
    return await service.analyze_query_performance()