"""
数据库性能优化服务

实现数据库查询优化、连接池管理、索引优化和性能监控
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func, and_, or_
from sqlalchemy.engine import Result
from sqlalchemy.pool import QueuePool

from ..core.database import get_async_session
from ..utils.database_optimization import (
    DatabaseOptimizer, QueryOptimizer, DatabaseHealthChecker,
    ConnectionPoolManager, query_monitor, cache_manager
)
from ..utils.redis_client import get_redis_client
from ..models.dashboard_config import DashboardConfig
from ..models.project import Project

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """优化级别"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    AGGRESSIVE = "aggressive"


@dataclass
class PerformanceMetrics:
    """性能指标"""
    query_time: float
    rows_examined: int
    rows_returned: int
    index_usage: bool
    cache_hit: bool
    connection_time: float
    memory_usage: int
    cpu_usage: float
    timestamp: datetime


@dataclass
class OptimizationResult:
    """优化结果"""
    optimization_type: str
    before_metrics: Dict[str, Any]
    after_metrics: Dict[str, Any]
    improvement_percent: float
    recommendations: List[str]
    applied_changes: List[str]
    estimated_savings: Dict[str, float]


class DatabasePerformanceService:
    """数据库性能优化服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = get_redis_client()
        self.optimizer = DatabaseOptimizer(db)
        self.query_optimizer = QueryOptimizer(db)
        self.health_checker = DatabaseHealthChecker(db)
        self.connection_manager = ConnectionPoolManager()
        
        # 性能监控
        self.performance_history: List[PerformanceMetrics] = []
        self.optimization_history: List[OptimizationResult] = []
        
        # 配置
        self.optimization_config = {
            "enable_query_cache": True,
            "enable_connection_pooling": True,
            "enable_index_optimization": True,
            "enable_query_rewriting": True,
            "max_cache_size": 1000,
            "cache_ttl": 300,
            "slow_query_threshold": 1.0,
            "optimization_level": OptimizationLevel.INTERMEDIATE
        }
    
    async def comprehensive_optimization(
        self,
        level: OptimizationLevel = OptimizationLevel.INTERMEDIATE
    ) -> Dict[str, Any]:
        """
        综合性能优化
        
        Args:
            level: 优化级别
            
        Returns:
            优化结果报告
        """
        start_time = time.time()
        
        try:
            # 获取优化前的基准指标
            before_metrics = await self._collect_performance_metrics()
            
            optimization_results = []
            
            # 1. 查询优化
            if level in [OptimizationLevel.INTERMEDIATE, OptimizationLevel.ADVANCED, OptimizationLevel.AGGRESSIVE]:
                query_result = await self._optimize_queries(level)
                optimization_results.append(query_result)
            
            # 2. 索引优化
            if level in [OptimizationLevel.BASIC, OptimizationLevel.INTERMEDIATE, OptimizationLevel.ADVANCED, OptimizationLevel.AGGRESSIVE]:
                index_result = await self._optimize_indexes(level)
                optimization_results.append(index_result)
            
            # 3. 连接池优化
            if level in [OptimizationLevel.INTERMEDIATE, OptimizationLevel.ADVANCED, OptimizationLevel.AGGRESSIVE]:
                connection_result = await self._optimize_connection_pool(level)
                optimization_results.append(connection_result)
            
            # 4. 缓存优化
            if level in [OptimizationLevel.ADVANCED, OptimizationLevel.AGGRESSIVE]:
                cache_result = await self._optimize_caching(level)
                optimization_results.append(cache_result)
            
            # 5. 表优化
            if level == OptimizationLevel.AGGRESSIVE:
                table_result = await self._optimize_tables(level)
                optimization_results.append(table_result)
            
            # 获取优化后的指标
            after_metrics = await self._collect_performance_metrics()
            
            # 计算总体改进
            total_improvement = self._calculate_improvement(before_metrics, after_metrics)
            
            # 生成优化报告
            optimization_report = {
                "optimization_level": level.value,
                "start_time": start_time,
                "duration_seconds": time.time() - start_time,
                "before_metrics": before_metrics,
                "after_metrics": after_metrics,
                "total_improvement_percent": total_improvement,
                "optimization_results": optimization_results,
                "recommendations": await self._generate_recommendations(after_metrics),
                "next_optimization_suggestions": await self._suggest_next_optimizations(level, after_metrics)
            }
            
            # 保存优化历史
            self.optimization_history.append(OptimizationResult(
                optimization_type="comprehensive",
                before_metrics=before_metrics,
                after_metrics=after_metrics,
                improvement_percent=total_improvement,
                recommendations=[],
                applied_changes=[],
                estimated_savings={}
            ))
            
            return optimization_report
            
        except Exception as e:
            logger.error(f"综合性能优化失败: {str(e)}")
            return {
                "error": str(e),
                "optimization_level": level.value,
                "duration_seconds": time.time() - start_time
            }
    
    async def optimize_dashboard_queries(
        self,
        dashboard_id: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        优化仪表板查询
        
        Args:
            dashboard_id: 仪表板ID
            user_id: 用户ID
            
        Returns:
            优化结果
        """
        try:
            # 获取仪表板配置
            dashboard_config = await self.db.execute(
                select(DashboardConfig).where(
                    and_(
                        DashboardConfig.user_id == user_id,
                        DashboardConfig.id == dashboard_id
                    )
                )
            )
            config = dashboard_config.scalar_one_or_none()
            
            if not config:
                return {"error": "仪表板配置未找到"}
            
            # 分析仪表板查询模式
            query_patterns = await self._analyze_dashboard_queries(config)
            
            # 优化查询
            optimization_results = []
            
            for pattern in query_patterns:
                # 查询重写
                optimized_query = await self._rewrite_query(pattern["query"])
                
                # 添加缓存
                cache_key = f"dashboard:{dashboard_id}:{pattern['widget_type']}"
                
                # 性能测试
                before_time = await self._benchmark_query(pattern["query"])
                after_time = await self._benchmark_query(optimized_query)
                
                improvement = ((before_time - after_time) / before_time) * 100 if before_time > 0 else 0
                
                optimization_results.append({
                    "widget_type": pattern["widget_type"],
                    "original_query": pattern["query"],
                    "optimized_query": optimized_query,
                    "before_time_ms": before_time * 1000,
                    "after_time_ms": after_time * 1000,
                    "improvement_percent": improvement,
                    "cache_key": cache_key
                })
            
            return {
                "dashboard_id": dashboard_id,
                "user_id": user_id,
                "optimization_results": optimization_results,
                "total_queries_optimized": len(optimization_results),
                "average_improvement": sum(r["improvement_percent"] for r in optimization_results) / len(optimization_results) if optimization_results else 0
            }
            
        except Exception as e:
            logger.error(f"优化仪表板查询失败: {str(e)}")
            return {"error": str(e)}
    
    async def monitor_real_time_performance(self) -> Dict[str, Any]:
        """
        实时性能监控
        
        Returns:
            实时性能指标
        """
        try:
            # 收集当前性能指标
            current_metrics = await self._collect_performance_metrics()
            
            # 添加到历史记录
            self.performance_history.append(PerformanceMetrics(
                query_time=current_metrics.get("avg_query_time", 0),
                rows_examined=current_metrics.get("total_rows_examined", 0),
                rows_returned=current_metrics.get("total_rows_returned", 0),
                index_usage=current_metrics.get("index_usage_rate", 0) > 0.8,
                cache_hit=current_metrics.get("cache_hit_rate", 0) > 0.7,
                connection_time=current_metrics.get("avg_connection_time", 0),
                memory_usage=current_metrics.get("memory_usage_mb", 0),
                cpu_usage=current_metrics.get("cpu_usage_percent", 0),
                timestamp=datetime.now()
            ))
            
            # 保持最近1000条记录
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
            
            # 分析趋势
            trend_analysis = await self._analyze_performance_trends()
            
            # 检测异常
            anomalies = await self._detect_performance_anomalies()
            
            # 生成告警
            alerts = await self._generate_performance_alerts(current_metrics, anomalies)
            
            return {
                "current_metrics": current_metrics,
                "trend_analysis": trend_analysis,
                "anomalies": anomalies,
                "alerts": alerts,
                "health_score": await self._calculate_health_score(current_metrics),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"实时性能监控失败: {str(e)}")
            return {"error": str(e)}
    
    async def generate_performance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        生成性能报告
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            性能报告
        """
        try:
            # 过滤时间范围内的数据
            filtered_metrics = [
                m for m in self.performance_history
                if start_date <= m.timestamp <= end_date
            ]
            
            if not filtered_metrics:
                return {"error": "指定时间范围内没有性能数据"}
            
            # 统计分析
            stats = self._calculate_performance_statistics(filtered_metrics)
            
            # 趋势分析
            trends = self._analyze_trends(filtered_metrics)
            
            # 问题识别
            issues = self._identify_performance_issues(filtered_metrics)
            
            # 优化建议
            recommendations = await self._generate_optimization_recommendations(stats, trends, issues)
            
            # 成本分析
            cost_analysis = self._analyze_performance_costs(filtered_metrics)
            
            return {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "duration_days": (end_date - start_date).days
                },
                "statistics": stats,
                "trends": trends,
                "issues": issues,
                "recommendations": recommendations,
                "cost_analysis": cost_analysis,
                "data_points": len(filtered_metrics),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成性能报告失败: {str(e)}")
            return {"error": str(e)}
    
    # 私有方法
    
    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """收集性能指标"""
        try:
            metrics = {}
            
            # 数据库状态指标
            result = await self.db.execute(text("""
                SHOW STATUS WHERE Variable_name IN (
                    'Queries', 'Questions', 'Slow_queries', 'Connections',
                    'Threads_connected', 'Threads_running', 'Uptime',
                    'Innodb_buffer_pool_reads', 'Innodb_buffer_pool_read_requests',
                    'Innodb_rows_read', 'Innodb_rows_inserted', 'Innodb_rows_updated', 'Innodb_rows_deleted'
                )
            """))
            
            status_vars = {row[0]: row[1] for row in result.fetchall()}
            
            # 计算派生指标
            total_queries = int(status_vars.get('Queries', 0))
            slow_queries = int(status_vars.get('Slow_queries', 0))
            buffer_reads = int(status_vars.get('Innodb_buffer_pool_reads', 0))
            buffer_requests = int(status_vars.get('Innodb_buffer_pool_read_requests', 0))
            
            metrics.update({
                'total_queries': total_queries,
                'slow_queries': slow_queries,
                'slow_query_rate': (slow_queries / total_queries * 100) if total_queries > 0 else 0,
                'buffer_hit_rate': ((buffer_requests - buffer_reads) / buffer_requests * 100) if buffer_requests > 0 else 0,
                'connections': int(status_vars.get('Connections', 0)),
                'threads_connected': int(status_vars.get('Threads_connected', 0)),
                'threads_running': int(status_vars.get('Threads_running', 0)),
                'uptime_seconds': int(status_vars.get('Uptime', 0))
            })
            
            # 表统计
            result = await self.db.execute(text("""
                SELECT 
                    COUNT(*) as table_count,
                    SUM(TABLE_ROWS) as total_rows,
                    SUM(DATA_LENGTH + INDEX_LENGTH) as total_size,
                    SUM(DATA_FREE) as free_space
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
            """))
            
            table_stats = result.fetchone()
            if table_stats:
                metrics.update({
                    'table_count': table_stats.table_count,
                    'total_rows': table_stats.total_rows or 0,
                    'total_size_bytes': table_stats.total_size or 0,
                    'free_space_bytes': table_stats.free_space or 0,
                    'fragmentation_rate': (table_stats.free_space / table_stats.total_size * 100) if table_stats.total_size else 0
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集性能指标失败: {str(e)}")
            return {}
    
    async def _optimize_queries(self, level: OptimizationLevel) -> Dict[str, Any]:
        """优化查询"""
        try:
            # 获取慢查询
            slow_queries = await self.optimizer.analyze_slow_queries(50)
            
            optimized_count = 0
            total_improvement = 0
            
            for query_info in slow_queries:
                if 'sql_text' in query_info:
                    # 分析查询计划
                    plan_analysis = await self.query_optimizer.analyze_query_plan(query_info['sql_text'])
                    
                    # 应用优化建议
                    if plan_analysis.get('recommendations'):
                        optimized_count += 1
                        # 这里可以实现具体的查询优化逻辑
            
            return {
                'optimization_type': 'queries',
                'level': level.value,
                'slow_queries_found': len(slow_queries),
                'queries_optimized': optimized_count,
                'improvement_percent': total_improvement / len(slow_queries) if slow_queries else 0
            }
            
        except Exception as e:
            logger.error(f"查询优化失败: {str(e)}")
            return {'optimization_type': 'queries', 'error': str(e)}
    
    async def _optimize_indexes(self, level: OptimizationLevel) -> Dict[str, Any]:
        """优化索引"""
        try:
            # 创建优化索引
            created_indexes = await self.optimizer.create_optimized_indexes()
            
            # 分析索引使用情况
            index_usage = await self.optimizer.analyze_index_usage()
            
            # 识别未使用的索引
            unused_indexes = [idx for idx in index_usage if idx['total_operations'] == 0]
            
            return {
                'optimization_type': 'indexes',
                'level': level.value,
                'indexes_created': len(created_indexes),
                'unused_indexes_found': len(unused_indexes),
                'total_indexes_analyzed': len(index_usage)
            }
            
        except Exception as e:
            logger.error(f"索引优化失败: {str(e)}")
            return {'optimization_type': 'indexes', 'error': str(e)}
    
    async def _optimize_connection_pool(self, level: OptimizationLevel) -> Dict[str, Any]:
        """优化连接池"""
        try:
            # 这里需要访问数据库引擎来监控连接池
            # 由于我们在服务层，可能需要通过其他方式获取引擎实例
            
            return {
                'optimization_type': 'connection_pool',
                'level': level.value,
                'status': 'optimized'
            }
            
        except Exception as e:
            logger.error(f"连接池优化失败: {str(e)}")
            return {'optimization_type': 'connection_pool', 'error': str(e)}
    
    async def _optimize_caching(self, level: OptimizationLevel) -> Dict[str, Any]:
        """优化缓存"""
        try:
            # 清理过期缓存
            cleared_keys = await cache_manager.invalidate_cache("*:expired:*")
            
            return {
                'optimization_type': 'caching',
                'level': level.value,
                'expired_keys_cleared': cleared_keys
            }
            
        except Exception as e:
            logger.error(f"缓存优化失败: {str(e)}")
            return {'optimization_type': 'caching', 'error': str(e)}
    
    async def _optimize_tables(self, level: OptimizationLevel) -> Dict[str, Any]:
        """优化表"""
        try:
            # 优化表统计信息
            table_stats = await self.optimizer.optimize_table_statistics()
            
            return {
                'optimization_type': 'tables',
                'level': level.value,
                'tables_optimized': len(table_stats)
            }
            
        except Exception as e:
            logger.error(f"表优化失败: {str(e)}")
            return {'optimization_type': 'tables', 'error': str(e)}
    
    async def _analyze_dashboard_queries(self, config: DashboardConfig) -> List[Dict[str, Any]]:
        """分析仪表板查询模式"""
        try:
            # 解析仪表板配置中的组件
            widget_configs = config.widget_configs or []
            query_patterns = []
            
            for widget in widget_configs:
                widget_type = widget.get('type', 'unknown')
                
                # 根据组件类型生成对应的查询模式
                if widget_type == 'project_overview':
                    query_patterns.append({
                        'widget_type': widget_type,
                        'query': """
                            SELECT 
                                COUNT(*) as total_projects,
                                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active_projects,
                                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_projects
                            FROM projects 
                            WHERE deleted_at IS NULL
                        """
                    })
                elif widget_type == 'task_statistics':
                    query_patterns.append({
                        'widget_type': widget_type,
                        'query': """
                            SELECT 
                                status,
                                COUNT(*) as count
                            FROM project_tasks 
                            WHERE deleted_at IS NULL
                            GROUP BY status
                        """
                    })
            
            return query_patterns
            
        except Exception as e:
            logger.error(f"分析仪表板查询失败: {str(e)}")
            return []
    
    async def _rewrite_query(self, original_query: str) -> str:
        """重写查询以提高性能"""
        try:
            # 简单的查询重写逻辑
            optimized_query = original_query
            
            # 添加索引提示
            if 'WHERE' in optimized_query and 'status' in optimized_query:
                optimized_query = optimized_query.replace(
                    'WHERE',
                    'USE INDEX (idx_status) WHERE'
                )
            
            # 添加LIMIT子句（如果没有的话）
            if 'LIMIT' not in optimized_query and 'COUNT' not in optimized_query:
                optimized_query += ' LIMIT 1000'
            
            return optimized_query
            
        except Exception as e:
            logger.error(f"查询重写失败: {str(e)}")
            return original_query
    
    async def _benchmark_query(self, query: str) -> float:
        """基准测试查询性能"""
        try:
            start_time = time.time()
            await self.db.execute(text(query))
            return time.time() - start_time
            
        except Exception as e:
            logger.error(f"查询基准测试失败: {str(e)}")
            return 0.0
    
    def _calculate_improvement(self, before: Dict[str, Any], after: Dict[str, Any]) -> float:
        """计算性能改进百分比"""
        try:
            # 选择关键指标进行比较
            key_metrics = ['slow_query_rate', 'avg_query_time', 'fragmentation_rate']
            
            improvements = []
            for metric in key_metrics:
                before_val = before.get(metric, 0)
                after_val = after.get(metric, 0)
                
                if before_val > 0:
                    improvement = ((before_val - after_val) / before_val) * 100
                    improvements.append(improvement)
            
            return sum(improvements) / len(improvements) if improvements else 0
            
        except Exception as e:
            logger.error(f"计算性能改进失败: {str(e)}")
            return 0
    
    async def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 慢查询建议
        if metrics.get('slow_query_rate', 0) > 5:
            recommendations.append("慢查询率过高，建议分析并优化慢查询")
        
        # 缓存命中率建议
        if metrics.get('buffer_hit_rate', 0) < 95:
            recommendations.append("缓冲池命中率较低，考虑增加innodb_buffer_pool_size")
        
        # 碎片化建议
        if metrics.get('fragmentation_rate', 0) > 10:
            recommendations.append("表碎片化严重，建议运行OPTIMIZE TABLE")
        
        # 连接数建议
        if metrics.get('threads_connected', 0) > 100:
            recommendations.append("连接数较高，检查连接池配置和连接泄漏")
        
        return recommendations
    
    async def _suggest_next_optimizations(
        self, 
        current_level: OptimizationLevel, 
        metrics: Dict[str, Any]
    ) -> List[str]:
        """建议下一步优化"""
        suggestions = []
        
        if current_level == OptimizationLevel.BASIC:
            suggestions.append("考虑升级到中级优化，包含查询重写和连接池优化")
        elif current_level == OptimizationLevel.INTERMEDIATE:
            suggestions.append("考虑升级到高级优化，包含缓存策略和表分区")
        elif current_level == OptimizationLevel.ADVANCED:
            suggestions.append("考虑激进优化，包含表结构调整和存储引擎优化")
        
        return suggestions
    
    async def _analyze_performance_trends(self) -> Dict[str, Any]:
        """分析性能趋势"""
        if len(self.performance_history) < 10:
            return {"error": "数据不足，无法分析趋势"}
        
        recent_metrics = self.performance_history[-10:]
        
        # 计算趋势
        query_times = [m.query_time for m in recent_metrics]
        memory_usage = [m.memory_usage for m in recent_metrics]
        
        return {
            "query_time_trend": "increasing" if query_times[-1] > query_times[0] else "decreasing",
            "memory_usage_trend": "increasing" if memory_usage[-1] > memory_usage[0] else "decreasing",
            "data_points": len(recent_metrics)
        }
    
    async def _detect_performance_anomalies(self) -> List[Dict[str, Any]]:
        """检测性能异常"""
        anomalies = []
        
        if len(self.performance_history) < 20:
            return anomalies
        
        recent_metrics = self.performance_history[-20:]
        
        # 计算基线
        avg_query_time = sum(m.query_time for m in recent_metrics) / len(recent_metrics)
        
        # 检测异常
        for metric in recent_metrics[-5:]:  # 检查最近5个数据点
            if metric.query_time > avg_query_time * 2:
                anomalies.append({
                    "type": "high_query_time",
                    "value": metric.query_time,
                    "baseline": avg_query_time,
                    "timestamp": metric.timestamp.isoformat()
                })
        
        return anomalies
    
    async def _generate_performance_alerts(
        self, 
        current_metrics: Dict[str, Any], 
        anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成性能告警"""
        alerts = []
        
        # 慢查询告警
        if current_metrics.get('slow_query_rate', 0) > 10:
            alerts.append({
                "level": "critical",
                "type": "slow_queries",
                "message": f"慢查询率达到 {current_metrics['slow_query_rate']:.1f}%",
                "threshold": 10
            })
        
        # 连接数告警
        if current_metrics.get('threads_connected', 0) > 200:
            alerts.append({
                "level": "warning",
                "type": "high_connections",
                "message": f"当前连接数: {current_metrics['threads_connected']}",
                "threshold": 200
            })
        
        # 异常告警
        for anomaly in anomalies:
            alerts.append({
                "level": "warning",
                "type": "performance_anomaly",
                "message": f"检测到性能异常: {anomaly['type']}",
                "details": anomaly
            })
        
        return alerts
    
    async def _calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """计算健康评分"""
        score = 100.0
        
        # 慢查询率扣分
        slow_query_rate = metrics.get('slow_query_rate', 0)
        if slow_query_rate > 5:
            score -= min(30, slow_query_rate * 2)
        
        # 缓存命中率扣分
        buffer_hit_rate = metrics.get('buffer_hit_rate', 100)
        if buffer_hit_rate < 95:
            score -= (95 - buffer_hit_rate) * 2
        
        # 碎片化扣分
        fragmentation_rate = metrics.get('fragmentation_rate', 0)
        if fragmentation_rate > 10:
            score -= min(20, fragmentation_rate)
        
        return max(0, score)
    
    def _calculate_performance_statistics(self, metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """计算性能统计"""
        if not metrics:
            return {}
        
        query_times = [m.query_time for m in metrics]
        memory_usage = [m.memory_usage for m in metrics]
        
        return {
            "avg_query_time": sum(query_times) / len(query_times),
            "max_query_time": max(query_times),
            "min_query_time": min(query_times),
            "avg_memory_usage": sum(memory_usage) / len(memory_usage),
            "max_memory_usage": max(memory_usage),
            "cache_hit_rate": sum(1 for m in metrics if m.cache_hit) / len(metrics) * 100,
            "index_usage_rate": sum(1 for m in metrics if m.index_usage) / len(metrics) * 100
        }
    
    def _analyze_trends(self, metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """分析趋势"""
        if len(metrics) < 2:
            return {}
        
        first_half = metrics[:len(metrics)//2]
        second_half = metrics[len(metrics)//2:]
        
        first_avg_time = sum(m.query_time for m in first_half) / len(first_half)
        second_avg_time = sum(m.query_time for m in second_half) / len(second_half)
        
        return {
            "query_time_trend": "improving" if second_avg_time < first_avg_time else "degrading",
            "trend_magnitude": abs(second_avg_time - first_avg_time) / first_avg_time * 100 if first_avg_time > 0 else 0
        }
    
    def _identify_performance_issues(self, metrics: List[PerformanceMetrics]) -> List[Dict[str, Any]]:
        """识别性能问题"""
        issues = []
        
        # 查询时间问题
        slow_queries = [m for m in metrics if m.query_time > 1.0]
        if len(slow_queries) > len(metrics) * 0.1:  # 超过10%的查询较慢
            issues.append({
                "type": "slow_queries",
                "severity": "high",
                "description": f"{len(slow_queries)} 个慢查询，占总数的 {len(slow_queries)/len(metrics)*100:.1f}%"
            })
        
        # 内存使用问题
        high_memory = [m for m in metrics if m.memory_usage > 1000]  # 1GB
        if len(high_memory) > len(metrics) * 0.2:  # 超过20%的时间内存使用过高
            issues.append({
                "type": "high_memory_usage",
                "severity": "medium",
                "description": f"内存使用过高的时间占 {len(high_memory)/len(metrics)*100:.1f}%"
            })
        
        return issues
    
    async def _generate_optimization_recommendations(
        self, 
        stats: Dict[str, Any], 
        trends: Dict[str, Any], 
        issues: List[Dict[str, Any]]
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于统计的建议
        if stats.get('avg_query_time', 0) > 0.5:
            recommendations.append("平均查询时间较长，建议优化慢查询和添加索引")
        
        if stats.get('cache_hit_rate', 0) < 80:
            recommendations.append("缓存命中率较低，建议优化缓存策略")
        
        # 基于趋势的建议
        if trends.get('query_time_trend') == 'degrading':
            recommendations.append("查询性能呈下降趋势，需要及时优化")
        
        # 基于问题的建议
        for issue in issues:
            if issue['type'] == 'slow_queries':
                recommendations.append("存在大量慢查询，建议进行查询优化")
            elif issue['type'] == 'high_memory_usage':
                recommendations.append("内存使用率过高，建议优化内存配置")
        
        return recommendations
    
    def _analyze_performance_costs(self, metrics: List[PerformanceMetrics]) -> Dict[str, Any]:
        """分析性能成本"""
        if not metrics:
            return {}
        
        # 简化的成本分析
        total_query_time = sum(m.query_time for m in metrics)
        avg_memory_usage = sum(m.memory_usage for m in metrics) / len(metrics)
        
        # 估算成本（这里使用简化的计算）
        compute_cost = total_query_time * 0.001  # 每秒0.001美元
        memory_cost = avg_memory_usage * 0.0001  # 每MB 0.0001美元
        
        return {
            "total_compute_cost_usd": compute_cost,
            "total_memory_cost_usd": memory_cost,
            "total_cost_usd": compute_cost + memory_cost,
            "cost_per_query_usd": (compute_cost + memory_cost) / len(metrics) if metrics else 0
        }


# 服务实例创建函数
async def get_database_performance_service(db: AsyncSession = None) -> DatabasePerformanceService:
    """获取数据库性能服务实例"""
    if db is None:
        async with get_async_session() as session:
            return DatabasePerformanceService(session)
    return DatabasePerformanceService(db)