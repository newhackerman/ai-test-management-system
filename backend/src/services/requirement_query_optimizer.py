"""
需求管理数据库查询优化服务

提供需求管理模块的数据库查询优化功能，包括：
- 复杂查询性能优化
- 数据库索引优化建议
- 查询缓存机制
- 查询性能监控
"""
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text, Index
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select
from dataclasses import dataclass

from ..models.requirement import (
    Requirement, RequirementStatus, RequirementType, Priority, BusinessValue, Complexity,
    RequirementStatusHistory, RequirementDependency, RequirementReview, RequirementChangeRequest
)
from ..core.exceptions import ValidationError, BusinessLogicError

logger = logging.getLogger(__name__)


@dataclass
class QueryPerformanceMetrics:
    """查询性能指标"""
    query_hash: str
    execution_time: float
    rows_examined: int
    rows_returned: int
    cache_hit: bool
    timestamp: datetime
    query_type: str
    optimization_suggestions: List[str]


@dataclass
class IndexRecommendation:
    """索引推荐"""
    table_name: str
    columns: List[str]
    index_type: str  # 'btree', 'hash', 'fulltext', 'composite'
    estimated_benefit: float
    usage_frequency: int
    reason: str


class RequirementQueryOptimizer:
    """需求查询优化器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.query_cache = {}  # 简单内存缓存
        self.performance_metrics = []
        self.cache_ttl = 300  # 5分钟缓存TTL
        
        # 预定义的优化查询
        self._optimized_queries = {}
        self._initialize_optimized_queries()
    
    def _initialize_optimized_queries(self):
        """初始化优化查询"""
        # 项目需求统计查询 - 使用索引优化
        self._optimized_queries['project_requirements_stats'] = """
        SELECT 
            r.status,
            r.priority,
            r.requirement_type,
            COUNT(*) as count,
            AVG(r.quality_score) as avg_quality,
            AVG(r.estimated_effort) as avg_effort
        FROM requirements r
        WHERE r.project_id = :project_id
        GROUP BY r.status, r.priority, r.requirement_type
        """
        
        # 需求依赖关系查询 - 优化递归查询
        self._optimized_queries['requirement_dependencies'] = """
        WITH RECURSIVE requirement_tree AS (
            -- 基础查询：获取指定需求
            SELECT id, parent_id, title, requirement_code, 0 as level
            FROM requirements 
            WHERE id = :requirement_id
            
            UNION ALL
            
            -- 递归查询：获取所有子需求
            SELECT r.id, r.parent_id, r.title, r.requirement_code, rt.level + 1
            FROM requirements r
            INNER JOIN requirement_tree rt ON r.parent_id = rt.id
            WHERE rt.level < 10  -- 防止无限递归
        )
        SELECT * FROM requirement_tree ORDER BY level, id
        """
        
        # 需求搜索查询 - 使用全文索引
        self._optimized_queries['requirement_fulltext_search'] = """
        SELECT r.*, 
               MATCH(r.title, r.description, r.acceptance_criteria) AGAINST(:search_text IN NATURAL LANGUAGE MODE) as relevance_score
        FROM requirements r
        WHERE MATCH(r.title, r.description, r.acceptance_criteria) AGAINST(:search_text IN NATURAL LANGUAGE MODE)
        AND (:project_id IS NULL OR r.project_id = :project_id)
        ORDER BY relevance_score DESC, r.updated_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        # 需求状态变更历史查询 - 优化时间范围查询
        self._optimized_queries['requirement_status_history'] = """
        SELECT rsh.*, r.title, r.requirement_code
        FROM requirement_status_history rsh
        INNER JOIN requirements r ON rsh.requirement_id = r.id
        WHERE (:requirement_id IS NULL OR rsh.requirement_id = :requirement_id)
        AND (:project_id IS NULL OR r.project_id = :project_id)
        AND rsh.changed_at BETWEEN :start_date AND :end_date
        ORDER BY rsh.changed_at DESC
        """
        
        # 需求评审统计查询
        self._optimized_queries['requirement_review_stats'] = """
        SELECT 
            rr.review_status,
            rr.decision,
            COUNT(*) as count,
            AVG(TIMESTAMPDIFF(HOUR, rr.created_at, rr.completed_at)) as avg_duration_hours
        FROM requirement_reviews rr
        INNER JOIN requirements r ON rr.requirement_id = r.id
        WHERE (:project_id IS NULL OR r.project_id = :project_id)
        AND rr.created_at >= :start_date
        GROUP BY rr.review_status, rr.decision
        """
    
    async def execute_optimized_query(self, query_name: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行优化查询"""
        start_time = time.time()
        
        try:
            # 检查缓存
            cache_key = f"{query_name}:{hash(str(sorted(params.items())))}"
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                execution_time = time.time() - start_time
                await self._record_performance_metrics(
                    query_hash=cache_key,
                    execution_time=execution_time,
                    rows_examined=0,
                    rows_returned=len(cached_result),
                    cache_hit=True,
                    query_type=query_name
                )
                return cached_result
            
            # 获取优化查询
            if query_name not in self._optimized_queries:
                raise ValidationError(f"未找到优化查询: {query_name}")
            
            query_sql = self._optimized_queries[query_name]
            
            # 执行查询
            result = await self.db.execute(text(query_sql), params)
            rows = [dict(row._mapping) for row in result.fetchall()]
            
            # 缓存结果
            self._set_cache(cache_key, rows)
            
            execution_time = time.time() - start_time
            await self._record_performance_metrics(
                query_hash=cache_key,
                execution_time=execution_time,
                rows_examined=len(rows),  # 简化指标
                rows_returned=len(rows),
                cache_hit=False,
                query_type=query_name
            )
            
            return rows
            
        except Exception as e:
            logger.error(f"执行优化查询失败 {query_name}: {str(e)}")
            raise BusinessLogicError(f"查询执行失败: {str(e)}")
    
    async def get_project_requirements_with_optimization(self, project_id: int, 
                                                       filters: Dict[str, Any] = None,
                                                       skip: int = 0, limit: int = 100) -> Tuple[List[Requirement], int]:
        """获取项目需求 - 优化版本"""
        start_time = time.time()
        
        # 构建优化查询
        query = select(Requirement)
        count_query = select(func.count(Requirement.id))
        
        # 基础条件
        base_condition = Requirement.project_id == project_id
        query = query.where(base_condition)
        count_query = count_query.where(base_condition)
        
        # 应用筛选条件
        if filters:
            conditions = self._build_filter_conditions(filters)
            if conditions:
                combined_condition = and_(base_condition, *conditions)
                query = query.where(combined_condition)
                count_query = count_query.where(combined_condition)
        
        # 优化：使用索引友好的排序
        query = query.order_by(desc(Requirement.updated_at), desc(Requirement.id))
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        # 执行查询
        result = await self.db.execute(query)
        requirements = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar()
        
        execution_time = time.time() - start_time
        await self._record_performance_metrics(
            query_hash=f"project_requirements_{project_id}",
            execution_time=execution_time,
            rows_examined=total_count,
            rows_returned=len(requirements),
            cache_hit=False,
            query_type="project_requirements"
        )
        
        return requirements, total_count
    
    async def search_requirements_optimized(self, search_params: Dict[str, Any]) -> Tuple[List[Requirement], int]:
        """优化的需求搜索"""
        start_time = time.time()
        
        # 检查是否可以使用全文搜索
        if 'keyword' in search_params and search_params['keyword']:
            return await self._fulltext_search_requirements(search_params)
        
        # 使用优化的常规搜索
        return await self._optimized_regular_search(search_params)
    
    async def _fulltext_search_requirements(self, search_params: Dict[str, Any]) -> Tuple[List[Requirement], int]:
        """全文搜索需求"""
        keyword = search_params['keyword']
        project_id = search_params.get('project_id')
        skip = search_params.get('skip', 0)
        limit = search_params.get('limit', 100)
        
        # 使用预定义的全文搜索查询
        params = {
            'search_text': keyword,
            'project_id': project_id,
            'offset': skip,
            'limit': limit
        }
        
        rows = await self.execute_optimized_query('requirement_fulltext_search', params)
        
        # 转换为Requirement对象
        requirements = []
        for row in rows:
            # 这里需要从数据库重新获取完整对象，或者优化查询返回所有字段
            req = await self.db.get(Requirement, row['id'])
            if req:
                requirements.append(req)
        
        # 获取总数（简化实现）
        total_count = len(requirements)
        
        return requirements, total_count
    
    async def _optimized_regular_search(self, search_params: Dict[str, Any]) -> Tuple[List[Requirement], int]:
        """优化的常规搜索"""
        # 构建优化查询
        query = select(Requirement)
        count_query = select(func.count(Requirement.id))
        
        # 构建查询条件
        conditions = self._build_filter_conditions(search_params)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 优化排序
        order_by = search_params.get('order_by', 'updated_at')
        order_direction = search_params.get('order_direction', 'desc')
        
        if hasattr(Requirement, order_by):
            order_attr = getattr(Requirement, order_by)
            if order_direction.lower() == 'asc':
                query = query.order_by(asc(order_attr), asc(Requirement.id))
            else:
                query = query.order_by(desc(order_attr), desc(Requirement.id))
        
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
    
    def _build_filter_conditions(self, filters: Dict[str, Any]) -> List:
        """构建筛选条件"""
        conditions = []
        
        # 项目ID筛选
        if 'project_id' in filters and filters['project_id']:
            conditions.append(Requirement.project_id == filters['project_id'])
        
        # 状态筛选 - 使用IN操作符优化
        if 'status' in filters and filters['status']:
            if isinstance(filters['status'], list):
                conditions.append(Requirement.status.in_(filters['status']))
            else:
                conditions.append(Requirement.status == filters['status'])
        
        # 优先级筛选
        if 'priority' in filters and filters['priority']:
            if isinstance(filters['priority'], list):
                conditions.append(Requirement.priority.in_(filters['priority']))
            else:
                conditions.append(Requirement.priority == filters['priority'])
        
        # 需求类型筛选
        if 'requirement_type' in filters and filters['requirement_type']:
            if isinstance(filters['requirement_type'], list):
                conditions.append(Requirement.requirement_type.in_(filters['requirement_type']))
            else:
                conditions.append(Requirement.requirement_type == filters['requirement_type'])
        
        # 负责人筛选
        if 'assignee_id' in filters and filters['assignee_id']:
            conditions.append(Requirement.assignee_id == filters['assignee_id'])
        
        # 创建人筛选
        if 'creator_id' in filters and filters['creator_id']:
            conditions.append(Requirement.creator_id == filters['creator_id'])
        
        # 日期范围筛选 - 使用索引友好的范围查询
        if 'date_range' in filters and filters['date_range']:
            date_range = filters['date_range']
            if 'start' in date_range and date_range['start']:
                conditions.append(Requirement.created_at >= date_range['start'])
            if 'end' in date_range and date_range['end']:
                conditions.append(Requirement.created_at <= date_range['end'])
        
        # 关键词搜索 - 优化LIKE查询
        if 'keyword' in filters and filters['keyword']:
            keyword = f"%{filters['keyword']}%"
            conditions.append(
                or_(
                    Requirement.title.like(keyword),
                    Requirement.requirement_code.like(keyword),
                    Requirement.description.like(keyword)
                )
            )
        
        return conditions
    
    async def get_requirement_dependencies_optimized(self, requirement_id: int, max_depth: int = 5) -> Dict[str, Any]:
        """获取需求依赖关系 - 优化版本"""
        params = {
            'requirement_id': requirement_id,
            'max_depth': max_depth
        }
        
        # 使用递归CTE查询
        dependency_tree = await self.execute_optimized_query('requirement_dependencies', params)
        
        return {
            'requirement_id': requirement_id,
            'dependency_tree': dependency_tree,
            'max_depth': max_depth
        }
    
    async def get_requirements_statistics_optimized(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """获取需求统计信息 - 优化版本"""
        params = {'project_id': project_id}
        
        # 使用预定义的统计查询
        stats = await self.execute_optimized_query('project_requirements_stats', params)
        
        # 处理统计结果
        status_distribution = {}
        priority_distribution = {}
        type_distribution = {}
        
        for row in stats:
            status = row['status']
            priority = row['priority']
            req_type = row['requirement_type']
            count = row['count']
            
            status_distribution[status] = status_distribution.get(status, 0) + count
            priority_distribution[priority] = priority_distribution.get(priority, 0) + count
            type_distribution[req_type] = type_distribution.get(req_type, 0) + count
        
        return {
            'status_distribution': status_distribution,
            'priority_distribution': priority_distribution,
            'type_distribution': type_distribution,
            'total_count': sum(status_distribution.values())
        }
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if cache_key in self.query_cache:
            cached_item = self.query_cache[cache_key]
            if datetime.now() - cached_item['timestamp'] < timedelta(seconds=self.cache_ttl):
                return cached_item['data']
            else:
                # 缓存过期，删除
                del self.query_cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any):
        """设置缓存数据"""
        self.query_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        
        # 简单的缓存清理 - 保持缓存大小在合理范围内
        if len(self.query_cache) > 1000:
            # 删除最旧的缓存项
            oldest_key = min(self.query_cache.keys(), 
                           key=lambda k: self.query_cache[k]['timestamp'])
            del self.query_cache[oldest_key]
    
    async def _record_performance_metrics(self, query_hash: str, execution_time: float,
                                        rows_examined: int, rows_returned: int,
                                        cache_hit: bool, query_type: str):
        """记录性能指标"""
        metrics = QueryPerformanceMetrics(
            query_hash=query_hash,
            execution_time=execution_time,
            rows_examined=rows_examined,
            rows_returned=rows_returned,
            cache_hit=cache_hit,
            timestamp=datetime.now(),
            query_type=query_type,
            optimization_suggestions=self._generate_optimization_suggestions(
                execution_time, rows_examined, rows_returned
            )
        )
        
        self.performance_metrics.append(metrics)
        
        # 保持性能指标在合理数量
        if len(self.performance_metrics) > 10000:
            self.performance_metrics = self.performance_metrics[-5000:]
        
        # 记录慢查询
        if execution_time > 2.0:  # 超过2秒的查询
            logger.warning(f"慢查询检测: {query_type} 执行时间: {execution_time:.2f}s")
    
    def _generate_optimization_suggestions(self, execution_time: float, 
                                         rows_examined: int, rows_returned: int) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        if execution_time > 2.0:
            suggestions.append("查询执行时间过长，建议优化查询条件或添加索引")
        
        if rows_examined > rows_returned * 10:
            suggestions.append("查询扫描行数过多，建议优化WHERE条件")
        
        if rows_returned > 1000:
            suggestions.append("返回结果集过大，建议使用分页查询")
        
        return suggestions
    
    async def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能报告"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.performance_metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {
                'total_queries': 0,
                'avg_execution_time': 0,
                'cache_hit_rate': 0,
                'slow_queries': [],
                'optimization_suggestions': []
            }
        
        total_queries = len(recent_metrics)
        avg_execution_time = sum(m.execution_time for m in recent_metrics) / total_queries
        cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
        cache_hit_rate = cache_hits / total_queries if total_queries > 0 else 0
        
        slow_queries = [m for m in recent_metrics if m.execution_time > 2.0]
        
        # 收集所有优化建议
        all_suggestions = []
        for m in recent_metrics:
            all_suggestions.extend(m.optimization_suggestions)
        
        # 统计建议频率
        suggestion_counts = {}
        for suggestion in all_suggestions:
            suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1
        
        top_suggestions = sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_queries': total_queries,
            'avg_execution_time': avg_execution_time,
            'cache_hit_rate': cache_hit_rate,
            'slow_queries_count': len(slow_queries),
            'slow_queries': [
                {
                    'query_type': sq.query_type,
                    'execution_time': sq.execution_time,
                    'timestamp': sq.timestamp.isoformat()
                }
                for sq in slow_queries[:10]  # 只返回前10个慢查询
            ],
            'top_optimization_suggestions': [
                {'suggestion': suggestion, 'frequency': count}
                for suggestion, count in top_suggestions
            ]
        }
    
    async def get_index_recommendations(self) -> List[IndexRecommendation]:
        """获取索引推荐"""
        recommendations = []
        
        # 基于查询模式分析推荐索引
        query_patterns = self._analyze_query_patterns()
        
        # 项目ID + 状态复合索引
        if query_patterns.get('project_status_queries', 0) > 10:
            recommendations.append(IndexRecommendation(
                table_name='requirements',
                columns=['project_id', 'status'],
                index_type='btree',
                estimated_benefit=0.8,
                usage_frequency=query_patterns['project_status_queries'],
                reason='频繁按项目和状态查询需求'
            ))
        
        # 更新时间索引
        if query_patterns.get('time_range_queries', 0) > 5:
            recommendations.append(IndexRecommendation(
                table_name='requirements',
                columns=['updated_at'],
                index_type='btree',
                estimated_benefit=0.6,
                usage_frequency=query_patterns['time_range_queries'],
                reason='频繁按时间范围查询需求'
            ))
        
        # 全文搜索索引
        if query_patterns.get('fulltext_queries', 0) > 3:
            recommendations.append(IndexRecommendation(
                table_name='requirements',
                columns=['title', 'description', 'acceptance_criteria'],
                index_type='fulltext',
                estimated_benefit=0.9,
                usage_frequency=query_patterns['fulltext_queries'],
                reason='频繁进行全文搜索'
            ))
        
        # 负责人索引
        if query_patterns.get('assignee_queries', 0) > 5:
            recommendations.append(IndexRecommendation(
                table_name='requirements',
                columns=['assignee_id'],
                index_type='btree',
                estimated_benefit=0.5,
                usage_frequency=query_patterns['assignee_queries'],
                reason='频繁按负责人查询需求'
            ))
        
        return recommendations
    
    def _analyze_query_patterns(self) -> Dict[str, int]:
        """分析查询模式"""
        patterns = {
            'project_status_queries': 0,
            'time_range_queries': 0,
            'fulltext_queries': 0,
            'assignee_queries': 0
        }
        
        for metric in self.performance_metrics:
            if 'project_requirements' in metric.query_type:
                patterns['project_status_queries'] += 1
            elif 'fulltext_search' in metric.query_type:
                patterns['fulltext_queries'] += 1
            elif 'time_range' in metric.query_type:
                patterns['time_range_queries'] += 1
            elif 'assignee' in metric.query_type:
                patterns['assignee_queries'] += 1
        
        return patterns
    
    def clear_cache(self):
        """清空查询缓存"""
        self.query_cache.clear()
        logger.info("查询缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_items = len(self.query_cache)
        total_size = sum(len(str(item['data'])) for item in self.query_cache.values())
        
        return {
            'total_items': total_items,
            'estimated_size_bytes': total_size,
            'cache_ttl_seconds': self.cache_ttl
        }