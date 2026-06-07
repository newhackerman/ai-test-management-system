"""
系统性能优化服务
负责数据库连接池优化、缓存策略优化、并发处理优化等
"""
import asyncio
import logging
import time
import psutil
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import async_engine, AsyncSessionLocal
from ..core.redis import redis_service, get_redis_client
from ..core.config import settings

logger = logging.getLogger(__name__)


class DatabaseOptimizationService:
    """数据库连接池优化服务"""
    
    def __init__(self):
        self.pool_stats = {}
        self.slow_queries = []
        self.connection_metrics = {}
    
    async def optimize_connection_pool(self) -> Dict[str, Any]:
        """优化数据库连接池配置"""
        try:
            # 获取当前连接池状态
            pool_status = await self._get_pool_status()
            
            # 分析连接使用模式
            usage_pattern = await self._analyze_connection_usage()
            
            # 生成优化建议
            recommendations = self._generate_pool_recommendations(pool_status, usage_pattern)
            
            # 应用优化配置
            optimization_result = await self._apply_pool_optimizations(recommendations)
            
            return {
                "status": "success",
                "pool_status": pool_status,
                "usage_pattern": usage_pattern,
                "recommendations": recommendations,
                "optimization_result": optimization_result
            }
            
        except Exception as e:
            logger.error(f"数据库连接池优化失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        if not async_engine:
            return {"error": "Async engine not available"}
        
        pool = async_engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "total_connections": pool.size() + pool.overflow()
        }
    
    async def _analyze_connection_usage(self) -> Dict[str, Any]:
        """分析连接使用模式"""
        try:
            async with AsyncSessionLocal() as session:
                # 查询数据库连接统计
                result = await session.execute(text("""
                    SELECT 
                        COUNT(*) as total_connections,
                        SUM(CASE WHEN COMMAND != 'Sleep' THEN 1 ELSE 0 END) as active_connections,
                        AVG(TIME) as avg_connection_time,
                        MAX(TIME) as max_connection_time
                    FROM information_schema.PROCESSLIST 
                    WHERE DB = DATABASE()
                """))
                
                stats = result.fetchone()
                
                return {
                    "total_connections": stats.total_connections if stats else 0,
                    "active_connections": stats.active_connections if stats else 0,
                    "avg_connection_time": float(stats.avg_connection_time) if stats and stats.avg_connection_time else 0,
                    "max_connection_time": float(stats.max_connection_time) if stats and stats.max_connection_time else 0,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"分析连接使用模式失败: {e}")
            return {"error": str(e)}
    
    def _generate_pool_recommendations(self, pool_status: Dict, usage_pattern: Dict) -> List[Dict[str, Any]]:
        """生成连接池优化建议"""
        recommendations = []
        
        # 检查连接池大小
        if pool_status.get("checked_out", 0) > pool_status.get("pool_size", 10) * 0.8:
            recommendations.append({
                "type": "pool_size",
                "priority": "high",
                "message": "连接池使用率过高，建议增加连接池大小",
                "current_value": pool_status.get("pool_size", 10),
                "recommended_value": pool_status.get("pool_size", 10) + 5
            })
        
        # 检查溢出连接
        if pool_status.get("overflow", 0) > 0:
            recommendations.append({
                "type": "max_overflow",
                "priority": "medium",
                "message": "存在溢出连接，建议调整max_overflow参数",
                "current_overflow": pool_status.get("overflow", 0),
                "recommended_action": "增加max_overflow或优化查询"
            })
        
        # 检查连接时间
        avg_time = usage_pattern.get("avg_connection_time", 0)
        if avg_time > 300:  # 5分钟
            recommendations.append({
                "type": "connection_timeout",
                "priority": "medium",
                "message": "平均连接时间过长，建议优化查询或调整超时设置",
                "avg_connection_time": avg_time,
                "recommended_action": "优化慢查询或调整pool_recycle"
            })
        
        return recommendations
    
    async def _apply_pool_optimizations(self, recommendations: List[Dict]) -> Dict[str, Any]:
        """应用连接池优化"""
        applied_optimizations = []
        
        for rec in recommendations:
            if rec["type"] == "pool_size" and rec["priority"] == "high":
                # 注意：实际应用中需要重启服务才能生效
                applied_optimizations.append({
                    "type": rec["type"],
                    "action": "记录优化建议，需要在配置文件中调整pool_size参数",
                    "status": "pending_restart"
                })
            
            elif rec["type"] == "connection_timeout":
                # 可以动态调整的参数
                applied_optimizations.append({
                    "type": rec["type"],
                    "action": "建议在下次重启时调整pool_recycle参数",
                    "status": "pending_restart"
                })
        
        return {
            "applied_count": len(applied_optimizations),
            "optimizations": applied_optimizations,
            "restart_required": True
        }
    
    async def monitor_slow_queries(self, threshold_seconds: float = 1.0) -> List[Dict[str, Any]]:
        """监控慢查询"""
        try:
            async with AsyncSessionLocal() as session:
                # 启用慢查询日志监控
                result = await session.execute(text("""
                    SELECT 
                        sql_text,
                        exec_count,
                        total_latency/1000000 as total_latency_ms,
                        avg_latency/1000000 as avg_latency_ms,
                        max_latency/1000000 as max_latency_ms
                    FROM performance_schema.events_statements_summary_by_digest 
                    WHERE avg_latency/1000000 > %s
                    ORDER BY avg_latency DESC 
                    LIMIT 10
                """), (threshold_seconds * 1000,))
                
                slow_queries = []
                for row in result:
                    slow_queries.append({
                        "sql_text": row.sql_text[:200] + "..." if len(row.sql_text) > 200 else row.sql_text,
                        "exec_count": row.exec_count,
                        "total_latency_ms": float(row.total_latency_ms),
                        "avg_latency_ms": float(row.avg_latency_ms),
                        "max_latency_ms": float(row.max_latency_ms)
                    })
                
                return slow_queries
                
        except Exception as e:
            logger.error(f"监控慢查询失败: {e}")
            return []


class CacheOptimizationService:
    """Redis缓存策略优化服务"""
    
    def __init__(self):
        self.cache_stats = {}
        self.hit_rate_threshold = 0.8
    
    async def optimize_cache_strategy(self) -> Dict[str, Any]:
        """优化缓存策略"""
        try:
            # 获取缓存统计信息
            cache_stats = await self._get_cache_statistics()
            
            # 分析缓存使用模式
            usage_analysis = await self._analyze_cache_usage()
            
            # 生成优化建议
            recommendations = self._generate_cache_recommendations(cache_stats, usage_analysis)
            
            # 应用优化策略
            optimization_result = await self._apply_cache_optimizations(recommendations)
            
            return {
                "status": "success",
                "cache_stats": cache_stats,
                "usage_analysis": usage_analysis,
                "recommendations": recommendations,
                "optimization_result": optimization_result
            }
            
        except Exception as e:
            logger.error(f"缓存策略优化失败: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            client = await get_redis_client()
            if not client:
                return {"error": "Redis连接不可用"}
            
            info = await client.info()
            stats = await client.info('stats')
            
            # 计算命中率
            hits = int(stats.get('keyspace_hits', 0))
            misses = int(stats.get('keyspace_misses', 0))
            total_requests = hits + misses
            hit_rate = hits / total_requests if total_requests > 0 else 0
            
            await client.close()
            
            return {
                "connected_clients": info.get('connected_clients', 0),
                "used_memory": info.get('used_memory', 0),
                "used_memory_human": info.get('used_memory_human', '0B'),
                "used_memory_peak": info.get('used_memory_peak', 0),
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "hit_rate": round(hit_rate, 4),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "instantaneous_ops_per_sec": info.get('instantaneous_ops_per_sec', 0)
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"error": str(e)}
    
    async def _analyze_cache_usage(self) -> Dict[str, Any]:
        """分析缓存使用模式"""
        try:
            client = await get_redis_client()
            if not client:
                return {"error": "Redis连接不可用"}
            
            # 获取所有键的信息
            keys = await client.keys("*")
            key_analysis = {
                "total_keys": len(keys),
                "key_patterns": {},
                "ttl_distribution": {"no_ttl": 0, "short_ttl": 0, "medium_ttl": 0, "long_ttl": 0},
                "memory_usage": {}
            }
            
            # 分析键模式和TTL分布
            for key in keys[:100]:  # 限制分析数量以避免性能问题
                # 分析键模式
                pattern = key.split(':')[0] if ':' in key else 'other'
                key_analysis["key_patterns"][pattern] = key_analysis["key_patterns"].get(pattern, 0) + 1
                
                # 分析TTL分布
                ttl = await client.ttl(key)
                if ttl == -1:
                    key_analysis["ttl_distribution"]["no_ttl"] += 1
                elif ttl <= 300:  # 5分钟
                    key_analysis["ttl_distribution"]["short_ttl"] += 1
                elif ttl <= 3600:  # 1小时
                    key_analysis["ttl_distribution"]["medium_ttl"] += 1
                else:
                    key_analysis["ttl_distribution"]["long_ttl"] += 1
            
            await client.close()
            return key_analysis
            
        except Exception as e:
            logger.error(f"分析缓存使用模式失败: {e}")
            return {"error": str(e)}
    
    def _generate_cache_recommendations(self, cache_stats: Dict, usage_analysis: Dict) -> List[Dict[str, Any]]:
        """生成缓存优化建议"""
        recommendations = []
        
        # 检查命中率
        hit_rate = cache_stats.get("hit_rate", 0)
        if hit_rate < self.hit_rate_threshold:
            recommendations.append({
                "type": "hit_rate",
                "priority": "high",
                "message": f"缓存命中率过低 ({hit_rate:.2%})，建议优化缓存策略",
                "current_hit_rate": hit_rate,
                "target_hit_rate": self.hit_rate_threshold,
                "suggestions": [
                    "增加缓存时间",
                    "预热热点数据",
                    "优化缓存键设计"
                ]
            })
        
        # 检查内存使用
        used_memory = cache_stats.get("used_memory", 0)
        if used_memory > 1024 * 1024 * 1024:  # 1GB
            recommendations.append({
                "type": "memory_usage",
                "priority": "medium",
                "message": "Redis内存使用较高，建议优化内存使用",
                "used_memory_mb": used_memory / (1024 * 1024),
                "suggestions": [
                    "清理过期键",
                    "压缩数据格式",
                    "设置合理的TTL"
                ]
            })
        
        # 检查TTL分布
        ttl_dist = usage_analysis.get("ttl_distribution", {})
        no_ttl_count = ttl_dist.get("no_ttl", 0)
        total_keys = usage_analysis.get("total_keys", 1)
        
        if no_ttl_count / total_keys > 0.3:  # 超过30%的键没有TTL
            recommendations.append({
                "type": "ttl_management",
                "priority": "medium",
                "message": "过多键没有设置TTL，可能导致内存泄漏",
                "no_ttl_percentage": no_ttl_count / total_keys,
                "suggestions": [
                    "为所有缓存键设置合理的TTL",
                    "定期清理无TTL的键",
                    "实施缓存键生命周期管理"
                ]
            })
        
        return recommendations
    
    async def _apply_cache_optimizations(self, recommendations: List[Dict]) -> Dict[str, Any]:
        """应用缓存优化"""
        applied_optimizations = []
        
        try:
            client = await get_redis_client()
            if not client:
                return {"error": "Redis连接不可用"}
            
            for rec in recommendations:
                if rec["type"] == "ttl_management":
                    # 为没有TTL的键设置默认TTL
                    keys = await client.keys("*")
                    updated_keys = 0
                    
                    for key in keys:
                        ttl = await client.ttl(key)
                        if ttl == -1:  # 没有TTL
                            # 根据键模式设置不同的TTL
                            if key.startswith("session:"):
                                await client.expire(key, 3600)  # 1小时
                            elif key.startswith("cache:"):
                                await client.expire(key, 1800)  # 30分钟
                            else:
                                await client.expire(key, 900)   # 15分钟
                            updated_keys += 1
                    
                    applied_optimizations.append({
                        "type": rec["type"],
                        "action": f"为 {updated_keys} 个键设置了默认TTL",
                        "status": "completed"
                    })
                
                elif rec["type"] == "memory_usage":
                    # 清理过期键
                    deleted_keys = 0
                    keys = await client.keys("*")
                    
                    for key in keys:
                        ttl = await client.ttl(key)
                        if ttl == 0:  # 已过期但未被清理
                            await client.delete(key)
                            deleted_keys += 1
                    
                    applied_optimizations.append({
                        "type": rec["type"],
                        "action": f"清理了 {deleted_keys} 个过期键",
                        "status": "completed"
                    })
            
            await client.close()
            
            return {
                "applied_count": len(applied_optimizations),
                "optimizations": applied_optimizations
            }
            
        except Exception as e:
            logger.error(f"应用缓存优化失败: {e}")
            return {"error": str(e)}
    
    async def preload_hot_data(self, data_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """预加载热点数据"""
        try:
            preloaded_count = 0
            
            for source in data_sources:
                cache_key = source.get("cache_key")
                data_query = source.get("data_query")
                ttl = source.get("ttl", 3600)
                
                if cache_key and data_query:
                    # 这里应该根据实际业务逻辑获取数据
                    # 示例：从数据库查询数据并缓存
                    cached_data = {"preloaded": True, "timestamp": datetime.now().isoformat()}
                    
                    success = redis_service.set(cache_key, cached_data, ttl)
                    if success:
                        preloaded_count += 1
            
            return {
                "status": "success",
                "preloaded_count": preloaded_count,
                "total_sources": len(data_sources)
            }
            
        except Exception as e:
            logger.error(f"预加载热点数据失败: {e}")
            return {"status": "error", "message": str(e)}


class ConcurrencyOptimizationService:
    """并发处理和资源管理优化服务"""
    
    def __init__(self):
        self.max_concurrent_requests = 100
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        self.active_requests = 0
        self.request_queue = asyncio.Queue()
    
    async def optimize_concurrency(self) -> Dict[str, Any]:
        """优化并发处理"""
        try:
            # 获取系统资源状态
            system_resources = self._get_system_resources()
            
            # 分析并发性能
            concurrency_analysis = await self._analyze_concurrency_performance()
            
            # 生成优化建议
            recommendations = self._generate_concurrency_recommendations(system_resources, concurrency_analysis)
            
            # 应用优化配置
            optimization_result = await self._apply_concurrency_optimizations(recommendations)
            
            return {
                "status": "success",
                "system_resources": system_resources,
                "concurrency_analysis": concurrency_analysis,
                "recommendations": recommendations,
                "optimization_result": optimization_result
            }
            
        except Exception as e:
            logger.error(f"并发优化失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """获取系统资源状态"""
        try:
            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存信息
            memory = psutil.virtual_memory()
            
            # 磁盘信息
            disk = psutil.disk_usage('/')
            
            # 网络信息
            network = psutil.net_io_counters()
            
            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                    "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "usage_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2)
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2),
                    "free_gb": round(disk.free / (1024**3), 2)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
            
        except Exception as e:
            logger.error(f"获取系统资源失败: {e}")
            return {"error": str(e)}
    
    async def _analyze_concurrency_performance(self) -> Dict[str, Any]:
        """分析并发性能"""
        try:
            # 模拟并发测试
            start_time = time.time()
            
            # 创建多个并发任务
            tasks = []
            for i in range(10):
                task = asyncio.create_task(self._simulate_request())
                tasks.append(task)
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 统计结果
            successful_requests = sum(1 for r in results if not isinstance(r, Exception))
            failed_requests = len(results) - successful_requests
            
            return {
                "total_requests": len(tasks),
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "total_time_seconds": round(total_time, 3),
                "requests_per_second": round(len(tasks) / total_time, 2),
                "success_rate": round(successful_requests / len(tasks), 4),
                "active_requests": self.active_requests,
                "max_concurrent_requests": self.max_concurrent_requests
            }
            
        except Exception as e:
            logger.error(f"分析并发性能失败: {e}")
            return {"error": str(e)}
    
    async def _simulate_request(self) -> bool:
        """模拟请求处理"""
        async with self.request_semaphore:
            self.active_requests += 1
            try:
                # 模拟请求处理时间
                await asyncio.sleep(0.1)
                return True
            finally:
                self.active_requests -= 1
    
    def _generate_concurrency_recommendations(self, system_resources: Dict, concurrency_analysis: Dict) -> List[Dict[str, Any]]:
        """生成并发优化建议"""
        recommendations = []
        
        # 检查CPU使用率
        cpu_usage = system_resources.get("cpu", {}).get("usage_percent", 0)
        if cpu_usage > 80:
            recommendations.append({
                "type": "cpu_optimization",
                "priority": "high",
                "message": f"CPU使用率过高 ({cpu_usage}%)，建议优化并发处理",
                "current_cpu_usage": cpu_usage,
                "suggestions": [
                    "减少并发请求数量",
                    "优化CPU密集型操作",
                    "考虑增加CPU资源"
                ]
            })
        
        # 检查内存使用率
        memory_usage = system_resources.get("memory", {}).get("usage_percent", 0)
        if memory_usage > 85:
            recommendations.append({
                "type": "memory_optimization",
                "priority": "high",
                "message": f"内存使用率过高 ({memory_usage}%)，建议优化内存使用",
                "current_memory_usage": memory_usage,
                "suggestions": [
                    "优化内存使用",
                    "增加内存资源",
                    "实施内存缓存清理"
                ]
            })
        
        # 检查并发性能
        success_rate = concurrency_analysis.get("success_rate", 1.0)
        if success_rate < 0.95:
            recommendations.append({
                "type": "concurrency_tuning",
                "priority": "medium",
                "message": f"并发成功率较低 ({success_rate:.2%})，建议调整并发参数",
                "current_success_rate": success_rate,
                "suggestions": [
                    "调整并发限制",
                    "优化请求处理逻辑",
                    "增加错误重试机制"
                ]
            })
        
        return recommendations
    
    async def _apply_concurrency_optimizations(self, recommendations: List[Dict]) -> Dict[str, Any]:
        """应用并发优化"""
        applied_optimizations = []
        
        for rec in recommendations:
            if rec["type"] == "concurrency_tuning":
                # 动态调整并发限制
                old_limit = self.max_concurrent_requests
                
                if rec.get("current_success_rate", 1.0) < 0.9:
                    # 降低并发限制
                    new_limit = max(10, int(old_limit * 0.8))
                else:
                    # 适当增加并发限制
                    new_limit = min(200, int(old_limit * 1.2))
                
                self.max_concurrent_requests = new_limit
                self.request_semaphore = asyncio.Semaphore(new_limit)
                
                applied_optimizations.append({
                    "type": rec["type"],
                    "action": f"调整并发限制从 {old_limit} 到 {new_limit}",
                    "status": "completed"
                })
        
        return {
            "applied_count": len(applied_optimizations),
            "optimizations": applied_optimizations
        }
    
    async def manage_request_queue(self, request_handler) -> Dict[str, Any]:
        """管理请求队列"""
        try:
            processed_requests = 0
            failed_requests = 0
            
            while not self.request_queue.empty():
                try:
                    request = await asyncio.wait_for(self.request_queue.get(), timeout=1.0)
                    
                    # 处理请求
                    async with self.request_semaphore:
                        result = await request_handler(request)
                        if result:
                            processed_requests += 1
                        else:
                            failed_requests += 1
                    
                    self.request_queue.task_done()
                    
                except asyncio.TimeoutError:
                    break
                except Exception as e:
                    logger.error(f"处理队列请求失败: {e}")
                    failed_requests += 1
            
            return {
                "status": "success",
                "processed_requests": processed_requests,
                "failed_requests": failed_requests,
                "queue_size": self.request_queue.qsize()
            }
            
        except Exception as e:
            logger.error(f"管理请求队列失败: {e}")
            return {"status": "error", "message": str(e)}


# 创建服务实例
db_optimization_service = DatabaseOptimizationService()
cache_optimization_service = CacheOptimizationService()
concurrency_optimization_service = ConcurrencyOptimizationService()