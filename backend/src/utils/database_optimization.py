"""
数据库优化工具

本模块提供数据库性能优化相关功能，包括：
- 慢查询分析
- 索引优化建议
- 查询性能监控
- 缓存策略实现
"""
import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from functools import wraps
from contextlib import asynccontextmanager

from sqlalchemy import text, Index, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result
from sqlalchemy.sql import Select
from sqlalchemy.orm import Query

from ..core.database import get_async_session
from ..core.redis_client import get_redis_client
from ..models.project import Project, ProjectMember, Task, Milestone, WorkLog, ProjectRisk

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = get_redis_client()
        self.slow_query_threshold = 1.0  # 慢查询阈值（秒）
        self.cache_ttl = 300  # 缓存TTL（秒）
    
    async def analyze_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        分析慢查询
        
        Args:
            limit: 返回的慢查询数量限制
            
        Returns:
            慢查询列表
        """
        try:
            # 查询MySQL慢查询日志
            slow_queries = []
            
            # 获取当前运行的查询
            result = await self.db.execute(text("SHOW PROCESSLIST"))
            processes = result.fetchall()
            
            for process in processes:
                if process.Time > self.slow_query_threshold and process.Command == 'Query':
                    slow_queries.append({
                        'id': process.Id,
                        'user': process.User,
                        'host': process.Host,
                        'db': process.db,
                        'command': process.Command,
                        'time': process.Time,
                        'state': process.State,
                        'info': process.Info
                    })
            
            # 获取慢查询统计
            result = await self.db.execute(text("""
                SELECT 
                    sql_text,
                    exec_count,
                    avg_timer_wait/1000000000 as avg_time_seconds,
                    sum_timer_wait/1000000000 as total_time_seconds,
                    sum_rows_examined,
                    sum_rows_sent
                FROM performance_schema.events_statements_summary_by_digest 
                WHERE avg_timer_wait/1000000000 > %s
                ORDER BY avg_timer_wait DESC 
                LIMIT %s
            """), (self.slow_query_threshold, limit))
            
            digest_stats = result.fetchall()
            
            for stat in digest_stats:
                slow_queries.append({
                    'sql_text': stat.sql_text,
                    'exec_count': stat.exec_count,
                    'avg_time_seconds': float(stat.avg_time_seconds),
                    'total_time_seconds': float(stat.total_time_seconds),
                    'rows_examined': stat.sum_rows_examined,
                    'rows_sent': stat.sum_rows_sent,
                    'efficiency': stat.sum_rows_sent / max(stat.sum_rows_examined, 1)
                })
            
            return slow_queries
            
        except Exception as e:
            logger.error(f"分析慢查询失败: {e}")
            return []
    
    async def create_optimized_indexes(self) -> List[str]:
        """
        创建优化索引
        
        Returns:
            创建的索引列表
        """
        created_indexes = []
        
        try:
            # 项目表索引
            project_indexes = [
                # 复合索引用于项目列表查询
                "CREATE INDEX IF NOT EXISTS idx_projects_status_type_priority ON projects(status, project_type, priority)",
                "CREATE INDEX IF NOT EXISTS idx_projects_manager_status ON projects(project_manager_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_projects_dates ON projects(planned_start_date, planned_end_date)",
                "CREATE INDEX IF NOT EXISTS idx_projects_search ON projects(project_name, project_code)",
                "CREATE INDEX IF NOT EXISTS idx_projects_created_updated ON projects(created_at, updated_at)",
                "CREATE INDEX IF NOT EXISTS idx_projects_deleted_status ON projects(deleted_at, status)",
                
                # 全文索引用于搜索
                "CREATE FULLTEXT INDEX IF NOT EXISTS idx_projects_fulltext ON projects(project_name, description)",
            ]
            
            # 项目成员表索引
            member_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_project_members_user_status ON project_members(user_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_project_members_project_role ON project_members(project_id, role_in_project)",
                "CREATE INDEX IF NOT EXISTS idx_project_members_join_leave ON project_members(join_date, leave_date)",
            ]
            
            # 任务表索引
            task_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON project_tasks(project_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_assignee_status ON project_tasks(assignee_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_type_priority ON project_tasks(task_type, priority)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_dates ON project_tasks(planned_start_date, planned_end_date)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_parent ON project_tasks(parent_task_id)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_created_updated ON project_tasks(created_at, updated_at)",
                
                # 全文索引
                "CREATE FULLTEXT INDEX IF NOT EXISTS idx_tasks_fulltext ON project_tasks(task_name, description)",
            ]
            
            # 里程碑表索引
            milestone_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_milestones_project_status ON project_milestones(project_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_milestones_owner_status ON project_milestones(owner_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_milestones_dates ON project_milestones(planned_date, actual_date)",
                "CREATE INDEX IF NOT EXISTS idx_milestones_type ON project_milestones(milestone_type)",
            ]
            
            # 工作日志表索引
            worklog_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_work_logs_user_date ON work_logs(user_id, work_date)",
                "CREATE INDEX IF NOT EXISTS idx_work_logs_project_date ON work_logs(project_id, work_date)",
                "CREATE INDEX IF NOT EXISTS idx_work_logs_task_date ON work_logs(task_id, work_date)",
                "CREATE INDEX IF NOT EXISTS idx_work_logs_status ON work_logs(status)",
            ]
            
            # 风险表索引
            risk_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_risks_project_status ON project_risks(project_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_risks_level_category ON project_risks(risk_level, risk_category)",
                "CREATE INDEX IF NOT EXISTS idx_risks_owner ON project_risks(owner_id)",
                "CREATE INDEX IF NOT EXISTS idx_risks_dates ON project_risks(identified_date, target_resolution_date)",
            ]
            
            all_indexes = (project_indexes + member_indexes + task_indexes + 
                          milestone_indexes + worklog_indexes + risk_indexes)
            
            # 执行索引创建
            for index_sql in all_indexes:
                try:
                    await self.db.execute(text(index_sql))
                    created_indexes.append(index_sql)
                    logger.info(f"创建索引成功: {index_sql}")
                except Exception as e:
                    logger.warning(f"创建索引失败: {index_sql}, 错误: {e}")
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"创建优化索引失败: {e}")
            await self.db.rollback()
        
        return created_indexes
    
    async def analyze_index_usage(self) -> List[Dict[str, Any]]:
        """
        分析索引使用情况
        
        Returns:
            索引使用统计
        """
        try:
            result = await self.db.execute(text("""
                SELECT 
                    t.TABLE_SCHEMA,
                    t.TABLE_NAME,
                    t.INDEX_NAME,
                    t.COLUMN_NAME,
                    s.rows_read,
                    s.rows_inserted,
                    s.rows_updated,
                    s.rows_deleted
                FROM information_schema.STATISTICS t
                LEFT JOIN performance_schema.table_io_waits_summary_by_index_usage s
                    ON t.TABLE_SCHEMA = s.OBJECT_SCHEMA 
                    AND t.TABLE_NAME = s.OBJECT_NAME 
                    AND t.INDEX_NAME = s.INDEX_NAME
                WHERE t.TABLE_SCHEMA = DATABASE()
                    AND t.TABLE_NAME IN ('projects', 'project_members', 'project_tasks', 
                                        'project_milestones', 'work_logs', 'project_risks')
                ORDER BY s.rows_read DESC
            """))
            
            index_stats = []
            for row in result.fetchall():
                index_stats.append({
                    'schema': row.TABLE_SCHEMA,
                    'table': row.TABLE_NAME,
                    'index': row.INDEX_NAME,
                    'column': row.COLUMN_NAME,
                    'rows_read': row.rows_read or 0,
                    'rows_inserted': row.rows_inserted or 0,
                    'rows_updated': row.rows_updated or 0,
                    'rows_deleted': row.rows_deleted or 0,
                    'total_operations': (row.rows_read or 0) + (row.rows_inserted or 0) + 
                                      (row.rows_updated or 0) + (row.rows_deleted or 0)
                })
            
            return index_stats
            
        except Exception as e:
            logger.error(f"分析索引使用情况失败: {e}")
            return []
    
    async def optimize_table_statistics(self) -> Dict[str, Any]:
        """
        优化表统计信息
        
        Returns:
            优化结果
        """
        try:
            tables = ['projects', 'project_members', 'project_tasks', 
                     'project_milestones', 'work_logs', 'project_risks']
            
            results = {}
            
            for table in tables:
                # 分析表
                await self.db.execute(text(f"ANALYZE TABLE {table}"))
                
                # 获取表统计信息
                result = await self.db.execute(text(f"""
                    SELECT 
                        table_rows,
                        avg_row_length,
                        data_length,
                        index_length,
                        data_free
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() AND table_name = '{table}'
                """))
                
                stats = result.fetchone()
                if stats:
                    results[table] = {
                        'rows': stats.table_rows,
                        'avg_row_length': stats.avg_row_length,
                        'data_length': stats.data_length,
                        'index_length': stats.index_length,
                        'data_free': stats.data_free,
                        'total_size': stats.data_length + stats.index_length
                    }
            
            await self.db.commit()
            return results
            
        except Exception as e:
            logger.error(f"优化表统计信息失败: {e}")
            return {}


class QueryPerformanceMonitor:
    """查询性能监控器"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.query_stats = {}
    
    def monitor_query(self, query_name: str):
        """
        查询性能监控装饰器
        
        Args:
            query_name: 查询名称
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # 记录查询统计
                    await self._record_query_stats(query_name, execution_time, True)
                    
                    # 如果查询时间过长，记录警告
                    if execution_time > 1.0:
                        logger.warning(f"慢查询检测: {query_name} 执行时间 {execution_time:.2f}s")
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    await self._record_query_stats(query_name, execution_time, False)
                    raise e
            
            return wrapper
        return decorator
    
    async def _record_query_stats(self, query_name: str, execution_time: float, success: bool):
        """记录查询统计信息"""
        try:
            stats_key = f"query_stats:{query_name}"
            
            # 更新统计信息
            pipe = self.redis.pipeline()
            pipe.hincrby(stats_key, "total_count", 1)
            pipe.hincrbyfloat(stats_key, "total_time", execution_time)
            
            if success:
                pipe.hincrby(stats_key, "success_count", 1)
            else:
                pipe.hincrby(stats_key, "error_count", 1)
            
            # 记录最大和最小执行时间
            current_stats = await self.redis.hgetall(stats_key)
            if current_stats:
                max_time = float(current_stats.get("max_time", 0))
                min_time = float(current_stats.get("min_time", float('inf')))
                
                if execution_time > max_time:
                    pipe.hset(stats_key, "max_time", execution_time)
                if execution_time < min_time:
                    pipe.hset(stats_key, "min_time", execution_time)
            else:
                pipe.hset(stats_key, "max_time", execution_time)
                pipe.hset(stats_key, "min_time", execution_time)
            
            pipe.expire(stats_key, 86400)  # 24小时过期
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"记录查询统计失败: {e}")
    
    async def get_query_stats(self, query_name: str) -> Dict[str, Any]:
        """获取查询统计信息"""
        try:
            stats_key = f"query_stats:{query_name}"
            stats = await self.redis.hgetall(stats_key)
            
            if not stats:
                return {}
            
            total_count = int(stats.get("total_count", 0))
            total_time = float(stats.get("total_time", 0))
            
            return {
                "query_name": query_name,
                "total_count": total_count,
                "success_count": int(stats.get("success_count", 0)),
                "error_count": int(stats.get("error_count", 0)),
                "total_time": total_time,
                "avg_time": total_time / total_count if total_count > 0 else 0,
                "max_time": float(stats.get("max_time", 0)),
                "min_time": float(stats.get("min_time", 0)),
                "success_rate": int(stats.get("success_count", 0)) / total_count if total_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取查询统计失败: {e}")
            return {}


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.default_ttl = 300  # 5分钟
    
    async def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """获取缓存结果"""
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    async def set_cached_result(self, cache_key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存结果"""
        try:
            import json
            ttl = ttl or self.default_ttl
            await self.redis.setex(cache_key, ttl, json.dumps(data, default=str))
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    async def invalidate_cache(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return 0
    
    def cache_result(self, cache_key_template: str, ttl: Optional[int] = None):
        """缓存结果装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = cache_key_template.format(*args, **kwargs)
                
                # 尝试从缓存获取
                cached_result = await self.get_cached_result(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # 执行函数并缓存结果
                result = await func(*args, **kwargs)
                await self.set_cached_result(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator


# 全局实例
query_monitor = QueryPerformanceMonitor()
cache_manager = CacheManager()


# 装饰器快捷方式
def monitor_query(query_name: str):
    """查询监控装饰器"""
    return query_monitor.monitor_query(query_name)


def cache_result(cache_key_template: str, ttl: Optional[int] = None):
    """缓存结果装饰器"""
    return cache_manager.cache_result(cache_key_template, ttl)


class ConnectionPoolManager:
    """数据库连接池管理器"""
    
    def __init__(self):
        self.pool_stats = {}
        self.connection_metrics = {}
    
    async def monitor_connection_pool(self, engine) -> Dict[str, Any]:
        """监控连接池状态"""
        try:
            pool = engine.pool
            
            stats = {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid(),
                'total_connections': pool.size() + pool.overflow(),
                'utilization_rate': (pool.checkedout() / (pool.size() + pool.overflow())) * 100 if (pool.size() + pool.overflow()) > 0 else 0
            }
            
            # 记录历史数据
            timestamp = datetime.now()
            if 'history' not in self.pool_stats:
                self.pool_stats['history'] = []
            
            self.pool_stats['history'].append({
                'timestamp': timestamp,
                **stats
            })
            
            # 保持最近100条记录
            if len(self.pool_stats['history']) > 100:
                self.pool_stats['history'] = self.pool_stats['history'][-100:]
            
            return stats
            
        except Exception as e:
            logger.error(f"监控连接池失败: {e}")
            return {}
    
    async def optimize_connection_pool(self, engine, target_utilization: float = 0.8) -> Dict[str, Any]:
        """优化连接池配置"""
        try:
            current_stats = await self.monitor_connection_pool(engine)
            
            recommendations = []
            
            # 分析利用率
            utilization = current_stats.get('utilization_rate', 0)
            
            if utilization > 90:
                recommendations.append({
                    'type': 'increase_pool_size',
                    'message': f'连接池利用率过高 ({utilization:.1f}%)，建议增加连接池大小',
                    'current_size': current_stats.get('pool_size', 0),
                    'recommended_size': int(current_stats.get('pool_size', 0) * 1.5)
                })
            elif utilization < 30:
                recommendations.append({
                    'type': 'decrease_pool_size',
                    'message': f'连接池利用率过低 ({utilization:.1f}%)，建议减少连接池大小',
                    'current_size': current_stats.get('pool_size', 0),
                    'recommended_size': max(5, int(current_stats.get('pool_size', 0) * 0.7))
                })
            
            # 检查溢出连接
            overflow = current_stats.get('overflow', 0)
            if overflow > 0:
                recommendations.append({
                    'type': 'handle_overflow',
                    'message': f'检测到 {overflow} 个溢出连接，可能需要增加最大连接数',
                    'overflow_count': overflow
                })
            
            # 检查无效连接
            invalid = current_stats.get('invalid', 0)
            if invalid > 0:
                recommendations.append({
                    'type': 'handle_invalid',
                    'message': f'检测到 {invalid} 个无效连接，建议检查网络连接稳定性',
                    'invalid_count': invalid
                })
            
            return {
                'current_stats': current_stats,
                'recommendations': recommendations,
                'optimization_score': self._calculate_pool_score(current_stats)
            }
            
        except Exception as e:
            logger.error(f"优化连接池失败: {e}")
            return {}
    
    def _calculate_pool_score(self, stats: Dict[str, Any]) -> float:
        """计算连接池健康评分"""
        score = 100.0
        
        utilization = stats.get('utilization_rate', 0)
        overflow = stats.get('overflow', 0)
        invalid = stats.get('invalid', 0)
        
        # 利用率评分
        if utilization > 90:
            score -= 20
        elif utilization < 30:
            score -= 10
        
        # 溢出连接扣分
        if overflow > 0:
            score -= min(30, overflow * 5)
        
        # 无效连接扣分
        if invalid > 0:
            score -= min(20, invalid * 10)
        
        return max(0, score)


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def analyze_query_plan(self, query: str) -> Dict[str, Any]:
        """分析查询执行计划"""
        try:
            # 获取查询执行计划
            explain_result = await self.db.execute(text(f"EXPLAIN FORMAT=JSON {query}"))
            plan_data = explain_result.fetchone()[0]
            
            import json
            plan = json.loads(plan_data)
            
            # 分析执行计划
            analysis = self._analyze_execution_plan(plan)
            
            return {
                'query': query,
                'execution_plan': plan,
                'analysis': analysis,
                'recommendations': self._generate_query_recommendations(analysis)
            }
            
        except Exception as e:
            logger.error(f"分析查询执行计划失败: {e}")
            return {}
    
    def _analyze_execution_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """分析执行计划"""
        analysis = {
            'total_cost': 0,
            'rows_examined': 0,
            'table_scans': 0,
            'index_scans': 0,
            'joins': 0,
            'sorts': 0,
            'temp_tables': 0,
            'filesorts': 0
        }
        
        def analyze_node(node):
            if isinstance(node, dict):
                # 分析成本
                if 'query_cost' in node:
                    analysis['total_cost'] += float(node['query_cost'])
                
                # 分析行数
                if 'rows_examined_per_scan' in node:
                    analysis['rows_examined'] += int(node['rows_examined_per_scan'])
                
                # 分析访问类型
                access_type = node.get('access_type', '')
                if access_type == 'ALL':
                    analysis['table_scans'] += 1
                elif 'index' in access_type.lower():
                    analysis['index_scans'] += 1
                
                # 分析操作类型
                if 'join_type' in node:
                    analysis['joins'] += 1
                
                if 'using_filesort' in node:
                    analysis['filesorts'] += 1
                
                if 'using_temporary' in node:
                    analysis['temp_tables'] += 1
                
                # 递归分析子节点
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        analyze_node(value)
            
            elif isinstance(node, list):
                for item in node:
                    analyze_node(item)
        
        analyze_node(plan)
        return analysis
    
    def _generate_query_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成查询优化建议"""
        recommendations = []
        
        # 全表扫描建议
        if analysis['table_scans'] > 0:
            recommendations.append({
                'type': 'table_scan',
                'severity': 'high',
                'message': f'检测到 {analysis["table_scans"]} 个全表扫描，建议添加适当的索引',
                'impact': '全表扫描会导致查询性能严重下降'
            })
        
        # 文件排序建议
        if analysis['filesorts'] > 0:
            recommendations.append({
                'type': 'filesort',
                'severity': 'medium',
                'message': f'检测到 {analysis["filesorts"]} 个文件排序操作，考虑添加排序索引',
                'impact': '文件排序会增加查询时间和内存使用'
            })
        
        # 临时表建议
        if analysis['temp_tables'] > 0:
            recommendations.append({
                'type': 'temp_table',
                'severity': 'medium',
                'message': f'检测到 {analysis["temp_tables"]} 个临时表，考虑优化查询结构',
                'impact': '临时表会增加内存使用和I/O操作'
            })
        
        # 高成本查询建议
        if analysis['total_cost'] > 1000:
            recommendations.append({
                'type': 'high_cost',
                'severity': 'high',
                'message': f'查询成本过高 ({analysis["total_cost"]:.2f})，需要优化',
                'impact': '高成本查询会占用大量系统资源'
            })
        
        # 大量行检查建议
        if analysis['rows_examined'] > 10000:
            recommendations.append({
                'type': 'many_rows',
                'severity': 'medium',
                'message': f'检查行数过多 ({analysis["rows_examined"]})，考虑添加过滤条件或索引',
                'impact': '检查大量行会增加I/O和CPU使用'
            })
        
        return recommendations
    
    async def suggest_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """建议索引"""
        try:
            # 分析表的查询模式
            result = await self.db.execute(text(f"""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_KEY,
                    EXTRA
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
            """))
            
            columns = result.fetchall()
            suggestions = []
            
            for column in columns:
                column_name = column.COLUMN_NAME
                data_type = column.DATA_TYPE
                is_nullable = column.IS_NULLABLE
                column_key = column.COLUMN_KEY
                
                # 如果列没有索引且适合建索引
                if column_key == '' and self._should_index_column(column_name, data_type):
                    suggestions.append({
                        'table': table_name,
                        'column': column_name,
                        'type': 'single_column',
                        'reason': f'{column_name} 列经常用于查询条件，建议添加索引',
                        'sql': f'CREATE INDEX idx_{table_name}_{column_name} ON {table_name}({column_name})'
                    })
            
            # 建议复合索引
            composite_suggestions = self._suggest_composite_indexes(table_name, columns)
            suggestions.extend(composite_suggestions)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"建议索引失败: {e}")
            return []
    
    def _should_index_column(self, column_name: str, data_type: str) -> bool:
        """判断列是否应该建索引"""
        # 常见的查询列
        query_columns = [
            'id', 'user_id', 'project_id', 'status', 'type', 'category',
            'created_at', 'updated_at', 'deleted_at', 'name', 'code'
        ]
        
        # 适合索引的数据类型
        indexable_types = [
            'int', 'bigint', 'varchar', 'char', 'datetime', 'timestamp', 'date'
        ]
        
        return (any(col in column_name.lower() for col in query_columns) and 
                any(dtype in data_type.lower() for dtype in indexable_types))
    
    def _suggest_composite_indexes(self, table_name: str, columns) -> List[Dict[str, Any]]:
        """建议复合索引"""
        suggestions = []
        
        # 常见的复合索引模式
        composite_patterns = [
            ['status', 'created_at'],
            ['user_id', 'status'],
            ['project_id', 'status'],
            ['type', 'status'],
            ['deleted_at', 'status'],
        ]
        
        column_names = [col.COLUMN_NAME.lower() for col in columns]
        
        for pattern in composite_patterns:
            if all(col in column_names for col in pattern):
                index_columns = ', '.join(pattern)
                suggestions.append({
                    'table': table_name,
                    'columns': pattern,
                    'type': 'composite',
                    'reason': f'复合索引 ({index_columns}) 可以优化多条件查询',
                    'sql': f'CREATE INDEX idx_{table_name}_{"_".join(pattern)} ON {table_name}({index_columns})'
                })
        
        return suggestions


class DatabaseHealthChecker:
    """数据库健康检查器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """综合健康检查"""
        try:
            health_report = {
                'overall_score': 0,
                'checks': {},
                'recommendations': [],
                'timestamp': datetime.now()
            }
            
            # 检查连接状态
            connection_health = await self._check_connection_health()
            health_report['checks']['connection'] = connection_health
            
            # 检查表状态
            table_health = await self._check_table_health()
            health_report['checks']['tables'] = table_health
            
            # 检查索引健康
            index_health = await self._check_index_health()
            health_report['checks']['indexes'] = index_health
            
            # 检查查询性能
            query_health = await self._check_query_performance()
            health_report['checks']['queries'] = query_health
            
            # 检查存储空间
            storage_health = await self._check_storage_health()
            health_report['checks']['storage'] = storage_health
            
            # 计算总体评分
            scores = [check.get('score', 0) for check in health_report['checks'].values()]
            health_report['overall_score'] = sum(scores) / len(scores) if scores else 0
            
            # 生成建议
            health_report['recommendations'] = self._generate_health_recommendations(health_report['checks'])
            
            return health_report
            
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {'overall_score': 0, 'error': str(e)}
    
    async def _check_connection_health(self) -> Dict[str, Any]:
        """检查连接健康状况"""
        try:
            result = await self.db.execute(text("SHOW STATUS LIKE 'Threads_%'"))
            thread_stats = {row[0]: int(row[1]) for row in result.fetchall()}
            
            result = await self.db.execute(text("SHOW STATUS LIKE 'Max_used_connections'"))
            max_used = int(result.fetchone()[1])
            
            result = await self.db.execute(text("SHOW VARIABLES LIKE 'max_connections'"))
            max_connections = int(result.fetchone()[1])
            
            connection_usage = (max_used / max_connections) * 100
            
            score = 100
            if connection_usage > 80:
                score -= 30
            elif connection_usage > 60:
                score -= 15
            
            return {
                'score': score,
                'thread_stats': thread_stats,
                'max_used_connections': max_used,
                'max_connections': max_connections,
                'connection_usage_percent': connection_usage,
                'status': 'healthy' if score > 70 else 'warning' if score > 40 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"检查连接健康失败: {e}")
            return {'score': 0, 'error': str(e)}
    
    async def _check_table_health(self) -> Dict[str, Any]:
        """检查表健康状况"""
        try:
            result = await self.db.execute(text("""
                SELECT 
                    TABLE_NAME,
                    TABLE_ROWS,
                    DATA_LENGTH,
                    INDEX_LENGTH,
                    DATA_FREE,
                    AUTO_INCREMENT
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_TYPE = 'BASE TABLE'
            """))
            
            tables = result.fetchall()
            table_stats = []
            total_fragmentation = 0
            
            for table in tables:
                data_free = table.DATA_FREE or 0
                data_length = table.DATA_LENGTH or 1
                fragmentation = (data_free / data_length) * 100 if data_length > 0 else 0
                total_fragmentation += fragmentation
                
                table_stats.append({
                    'name': table.TABLE_NAME,
                    'rows': table.TABLE_ROWS,
                    'data_length': table.DATA_LENGTH,
                    'index_length': table.INDEX_LENGTH,
                    'data_free': data_free,
                    'fragmentation_percent': fragmentation,
                    'auto_increment': table.AUTO_INCREMENT
                })
            
            avg_fragmentation = total_fragmentation / len(tables) if tables else 0
            
            score = 100
            if avg_fragmentation > 20:
                score -= 30
            elif avg_fragmentation > 10:
                score -= 15
            
            return {
                'score': score,
                'table_count': len(tables),
                'table_stats': table_stats,
                'avg_fragmentation_percent': avg_fragmentation,
                'status': 'healthy' if score > 70 else 'warning' if score > 40 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"检查表健康失败: {e}")
            return {'score': 0, 'error': str(e)}
    
    async def _check_index_health(self) -> Dict[str, Any]:
        """检查索引健康状况"""
        try:
            result = await self.db.execute(text("""
                SELECT 
                    s.TABLE_NAME,
                    s.INDEX_NAME,
                    s.CARDINALITY,
                    s.SUB_PART,
                    s.NULLABLE,
                    t.TABLE_ROWS
                FROM information_schema.STATISTICS s
                JOIN information_schema.TABLES t ON s.TABLE_SCHEMA = t.TABLE_SCHEMA 
                    AND s.TABLE_NAME = t.TABLE_NAME
                WHERE s.TABLE_SCHEMA = DATABASE()
                    AND t.TABLE_TYPE = 'BASE TABLE'
                ORDER BY s.TABLE_NAME, s.INDEX_NAME, s.SEQ_IN_INDEX
            """))
            
            indexes = result.fetchall()
            index_stats = {}
            low_cardinality_indexes = []
            
            for index in indexes:
                table_name = index.TABLE_NAME
                index_name = index.INDEX_NAME
                cardinality = index.CARDINALITY or 0
                table_rows = index.TABLE_ROWS or 1
                
                if table_name not in index_stats:
                    index_stats[table_name] = []
                
                selectivity = (cardinality / table_rows) * 100 if table_rows > 0 else 0
                
                index_info = {
                    'name': index_name,
                    'cardinality': cardinality,
                    'selectivity_percent': selectivity,
                    'table_rows': table_rows
                }
                
                index_stats[table_name].append(index_info)
                
                # 检查低选择性索引
                if selectivity < 10 and index_name != 'PRIMARY':
                    low_cardinality_indexes.append({
                        'table': table_name,
                        'index': index_name,
                        'selectivity': selectivity
                    })
            
            score = 100
            if len(low_cardinality_indexes) > 5:
                score -= 20
            elif len(low_cardinality_indexes) > 2:
                score -= 10
            
            return {
                'score': score,
                'index_stats': index_stats,
                'low_cardinality_indexes': low_cardinality_indexes,
                'status': 'healthy' if score > 70 else 'warning' if score > 40 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"检查索引健康失败: {e}")
            return {'score': 0, 'error': str(e)}
    
    async def _check_query_performance(self) -> Dict[str, Any]:
        """检查查询性能"""
        try:
            # 获取慢查询统计
            result = await self.db.execute(text("SHOW STATUS LIKE 'Slow_queries'"))
            slow_queries = int(result.fetchone()[1])
            
            # 获取查询统计
            result = await self.db.execute(text("SHOW STATUS LIKE 'Questions'"))
            total_queries = int(result.fetchone()[1])
            
            slow_query_rate = (slow_queries / total_queries) * 100 if total_queries > 0 else 0
            
            score = 100
            if slow_query_rate > 5:
                score -= 40
            elif slow_query_rate > 2:
                score -= 20
            elif slow_query_rate > 1:
                score -= 10
            
            return {
                'score': score,
                'slow_queries': slow_queries,
                'total_queries': total_queries,
                'slow_query_rate_percent': slow_query_rate,
                'status': 'healthy' if score > 70 else 'warning' if score > 40 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"检查查询性能失败: {e}")
            return {'score': 0, 'error': str(e)}
    
    async def _check_storage_health(self) -> Dict[str, Any]:
        """检查存储健康状况"""
        try:
            result = await self.db.execute(text("""
                SELECT 
                    SUM(DATA_LENGTH + INDEX_LENGTH) as total_size,
                    SUM(DATA_FREE) as free_space
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
            """))
            
            storage_info = result.fetchone()
            total_size = storage_info.total_size or 0
            free_space = storage_info.free_space or 0
            
            fragmentation_rate = (free_space / total_size) * 100 if total_size > 0 else 0
            
            score = 100
            if fragmentation_rate > 15:
                score -= 25
            elif fragmentation_rate > 10:
                score -= 15
            elif fragmentation_rate > 5:
                score -= 5
            
            return {
                'score': score,
                'total_size_bytes': total_size,
                'free_space_bytes': free_space,
                'fragmentation_rate_percent': fragmentation_rate,
                'status': 'healthy' if score > 70 else 'warning' if score > 40 else 'critical'
            }
            
        except Exception as e:
            logger.error(f"检查存储健康失败: {e}")
            return {'score': 0, 'error': str(e)}
    
    def _generate_health_recommendations(self, checks: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成健康建议"""
        recommendations = []
        
        # 连接建议
        connection_check = checks.get('connection', {})
        if connection_check.get('connection_usage_percent', 0) > 80:
            recommendations.append({
                'category': 'connection',
                'priority': 'high',
                'title': '连接使用率过高',
                'description': '数据库连接使用率超过80%，可能影响性能',
                'solution': '考虑增加最大连接数或优化连接池配置'
            })
        
        # 表建议
        table_check = checks.get('tables', {})
        if table_check.get('avg_fragmentation_percent', 0) > 15:
            recommendations.append({
                'category': 'tables',
                'priority': 'medium',
                'title': '表碎片化严重',
                'description': f'平均表碎片化率为 {table_check.get("avg_fragmentation_percent", 0):.1f}%',
                'solution': '运行 OPTIMIZE TABLE 命令整理表碎片'
            })
        
        # 索引建议
        index_check = checks.get('indexes', {})
        low_cardinality = index_check.get('low_cardinality_indexes', [])
        if len(low_cardinality) > 3:
            recommendations.append({
                'category': 'indexes',
                'priority': 'medium',
                'title': '低选择性索引过多',
                'description': f'发现 {len(low_cardinality)} 个低选择性索引',
                'solution': '考虑删除或重新设计低选择性索引'
            })
        
        # 查询建议
        query_check = checks.get('queries', {})
        if query_check.get('slow_query_rate_percent', 0) > 2:
            recommendations.append({
                'category': 'queries',
                'priority': 'high',
                'title': '慢查询率过高',
                'description': f'慢查询率为 {query_check.get("slow_query_rate_percent", 0):.2f}%',
                'solution': '分析并优化慢查询，添加必要的索引'
            })
        
        return recommendations


# 全局实例
connection_pool_manager = ConnectionPoolManager()


async def get_database_optimizer(db: AsyncSession = None) -> DatabaseOptimizer:
    """获取数据库优化器实例"""
    if db is None:
        async with get_async_session() as session:
            return DatabaseOptimizer(session)
    return DatabaseOptimizer(db)


async def get_query_optimizer(db: AsyncSession = None) -> QueryOptimizer:
    """获取查询优化器实例"""
    if db is None:
        async with get_async_session() as session:
            return QueryOptimizer(session)
    return QueryOptimizer(db)


async def get_database_health_checker(db: AsyncSession = None) -> DatabaseHealthChecker:
    """获取数据库健康检查器实例"""
    if db is None:
        async with get_async_session() as session:
            return DatabaseHealthChecker(session)
    return DatabaseHealthChecker(db)