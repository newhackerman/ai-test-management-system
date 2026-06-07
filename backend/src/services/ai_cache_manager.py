"""
AI缓存管理器

统一管理AI助手模块的所有缓存策略，包括：
1. 缓存策略配置和管理
2. 缓存预热和清理
3. 缓存监控和优化
4. 缓存一致性保证
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .ai_cache_service import ai_cache_service, CacheKeyType, CacheMetrics
from .ai_context_cache import ai_context_cache
from .ai_response_cache import ai_response_cache
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheHealthStatus(Enum):
    """缓存健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class CacheHealthReport:
    """缓存健康报告"""
    status: CacheHealthStatus
    hit_rate: float
    memory_usage: float
    error_rate: float
    response_time: float
    recommendations: List[str]
    timestamp: str


class AICacheManager:
    """AI缓存管理器"""
    
    def __init__(self):
        self.cache_service = ai_cache_service
        self.context_cache = ai_context_cache
        self.response_cache = ai_response_cache
        
        # 缓存健康阈值
        self.health_thresholds = {
            "min_hit_rate": 0.6,        # 最低命中率
            "max_error_rate": 0.05,     # 最大错误率
            "max_response_time": 0.1,   # 最大响应时间（秒）
            "max_memory_usage": 0.8     # 最大内存使用率
        }
        
        # 自动清理配置
        self.auto_cleanup_enabled = True
        self.cleanup_interval = 3600  # 1小时
        self.last_cleanup = datetime.utcnow()
        
        # 预热配置
        self.warmup_enabled = True
        self.warmup_queries = []
    
    async def initialize(self):
        """初始化缓存管理器"""
        try:
            logger.info("Initializing AI Cache Manager...")
            
            # 检查Redis连接
            if not self.cache_service.redis.is_connected():
                logger.error("Redis connection failed")
                return False
            
            # 加载预热查询
            await self._load_warmup_queries()
            
            # 启动后台任务
            if self.auto_cleanup_enabled:
                asyncio.create_task(self._background_cleanup_task())
            
            logger.info("AI Cache Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Cache Manager: {str(e)}")
            return False
    
    async def get_overall_health(self) -> CacheHealthReport:
        """获取整体缓存健康状况"""
        try:
            # 收集所有缓存类型的指标
            all_metrics = {}
            total_hits = 0
            total_misses = 0
            total_errors = 0
            total_operations = 0
            avg_response_times = []
            
            for cache_type in CacheKeyType:
                metrics = self.cache_service.get_metrics(cache_type)
                if cache_type.value in metrics:
                    metric = metrics[cache_type.value]
                    all_metrics[cache_type.value] = metric
                    
                    total_hits += metric.hits
                    total_misses += metric.misses
                    total_operations += metric.hits + metric.misses + metric.sets + metric.deletes
                    avg_response_times.append(metric.avg_access_time)
            
            # 计算整体指标
            overall_hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0
            overall_error_rate = total_errors / total_operations if total_operations > 0 else 0.0
            overall_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0.0
            
            # 估算内存使用率
            memory_usage = await self._estimate_memory_usage()
            
            # 确定健康状态
            status = self._determine_health_status(
                overall_hit_rate, overall_error_rate, overall_response_time, memory_usage
            )
            
            # 生成建议
            recommendations = self._generate_health_recommendations(
                overall_hit_rate, overall_error_rate, overall_response_time, memory_usage
            )
            
            return CacheHealthReport(
                status=status,
                hit_rate=overall_hit_rate,
                memory_usage=memory_usage,
                error_rate=overall_error_rate,
                response_time=overall_response_time,
                recommendations=recommendations,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error getting cache health: {str(e)}")
            return CacheHealthReport(
                status=CacheHealthStatus.CRITICAL,
                hit_rate=0.0,
                memory_usage=0.0,
                error_rate=1.0,
                response_time=999.0,
                recommendations=["缓存系统出现严重错误，请检查日志"],
                timestamp=datetime.utcnow().isoformat()
            )
    
    def _determine_health_status(self, hit_rate: float, error_rate: float,
                               response_time: float, memory_usage: float) -> CacheHealthStatus:
        """确定健康状态"""
        critical_issues = 0
        warning_issues = 0
        
        # 检查命中率
        if hit_rate < self.health_thresholds["min_hit_rate"] * 0.5:
            critical_issues += 1
        elif hit_rate < self.health_thresholds["min_hit_rate"]:
            warning_issues += 1
        
        # 检查错误率
        if error_rate > self.health_thresholds["max_error_rate"] * 2:
            critical_issues += 1
        elif error_rate > self.health_thresholds["max_error_rate"]:
            warning_issues += 1
        
        # 检查响应时间
        if response_time > self.health_thresholds["max_response_time"] * 3:
            critical_issues += 1
        elif response_time > self.health_thresholds["max_response_time"]:
            warning_issues += 1
        
        # 检查内存使用
        if memory_usage > self.health_thresholds["max_memory_usage"]:
            if memory_usage > 0.95:
                critical_issues += 1
            else:
                warning_issues += 1
        
        # 确定状态
        if critical_issues > 0:
            return CacheHealthStatus.CRITICAL
        elif warning_issues > 0:
            return CacheHealthStatus.WARNING
        else:
            return CacheHealthStatus.HEALTHY
    
    def _generate_health_recommendations(self, hit_rate: float, error_rate: float,
                                       response_time: float, memory_usage: float) -> List[str]:
        """生成健康建议"""
        recommendations = []
        
        # 命中率建议
        if hit_rate < self.health_thresholds["min_hit_rate"]:
            recommendations.append(f"缓存命中率较低({hit_rate:.2f})，建议优化缓存策略或增加预热")
        
        # 错误率建议
        if error_rate > self.health_thresholds["max_error_rate"]:
            recommendations.append(f"缓存错误率较高({error_rate:.2f})，建议检查Redis连接和配置")
        
        # 响应时间建议
        if response_time > self.health_thresholds["max_response_time"]:
            recommendations.append(f"缓存响应时间较慢({response_time:.3f}s)，建议优化网络或增加内存")
        
        # 内存使用建议
        if memory_usage > self.health_thresholds["max_memory_usage"]:
            recommendations.append(f"内存使用率较高({memory_usage:.2f})，建议清理过期缓存或增加内存")
        
        # 通用建议
        if not recommendations:
            recommendations.append("缓存系统运行正常")
        
        return recommendations
    
    async def _estimate_memory_usage(self) -> float:
        """估算内存使用率"""
        try:
            # 获取L1缓存大小
            l1_size = len(self.cache_service.l1_cache)
            
            # 估算每个缓存项的平均大小（字节）
            avg_item_size = 1024  # 1KB估算
            
            # 估算总内存使用
            estimated_memory = l1_size * avg_item_size
            
            # 假设最大内存限制为100MB
            max_memory = 100 * 1024 * 1024
            
            return min(estimated_memory / max_memory, 1.0)
            
        except Exception as e:
            logger.error(f"Error estimating memory usage: {str(e)}")
            return 0.0
    
    async def optimize_cache_performance(self) -> Dict[str, Any]:
        """优化缓存性能"""
        try:
            optimization_results = {
                "actions_taken": [],
                "performance_improvement": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 1. 清理低质量响应缓存
            cleaned_responses = await self.response_cache.cleanup_low_quality_cache(0.6)
            if cleaned_responses > 0:
                optimization_results["actions_taken"].append(f"清理了{cleaned_responses}个低质量响应缓存")
            
            # 2. 清理过期缓存
            cleanup_stats = await self.cache_service.cleanup_expired_cache()
            if cleanup_stats.get("l1_expired", 0) > 0:
                optimization_results["actions_taken"].append(f"清理了{cleanup_stats['l1_expired']}个过期L1缓存")
            
            # 3. 优化缓存配置
            config_optimizations = await self._optimize_cache_configs()
            optimization_results["actions_taken"].extend(config_optimizations)
            
            # 4. 预热热点数据
            if self.warmup_enabled:
                warmed_count = await self._warmup_hot_data()
                if warmed_count > 0:
                    optimization_results["actions_taken"].append(f"预热了{warmed_count}个热点数据")
            
            # 5. 记录性能改进
            optimization_results["performance_improvement"] = await self._measure_performance_improvement()
            
            logger.info(f"Cache optimization completed: {len(optimization_results['actions_taken'])} actions taken")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Error optimizing cache performance: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def _optimize_cache_configs(self) -> List[str]:
        """优化缓存配置"""
        optimizations = []
        
        try:
            # 获取各缓存类型的指标
            for cache_type in CacheKeyType:
                metrics = self.cache_service.get_metrics(cache_type)
                if cache_type.value not in metrics:
                    continue
                
                metric = metrics[cache_type.value]
                config = self.cache_service.cache_configs[cache_type]
                
                # 根据命中率调整TTL
                if metric.hit_rate > 0.9 and config.ttl < 86400:
                    # 高命中率，可以延长TTL
                    new_ttl = min(config.ttl * 1.5, 86400)
                    config.ttl = int(new_ttl)
                    optimizations.append(f"延长{cache_type.value}缓存TTL至{new_ttl}秒")
                
                elif metric.hit_rate < 0.3 and config.ttl > 300:
                    # 低命中率，缩短TTL
                    new_ttl = max(config.ttl * 0.7, 300)
                    config.ttl = int(new_ttl)
                    optimizations.append(f"缩短{cache_type.value}缓存TTL至{new_ttl}秒")
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Error optimizing cache configs: {str(e)}")
            return []
    
    async def _warmup_hot_data(self) -> int:
        """预热热点数据"""
        try:
            warmed_count = 0
            
            # 预热常见查询响应
            if self.warmup_queries:
                warmed_count += await self.response_cache.preload_common_responses(self.warmup_queries)
            
            # 预热用户偏好
            # 这里可以添加用户偏好预热逻辑
            
            return warmed_count
            
        except Exception as e:
            logger.error(f"Error warming up hot data: {str(e)}")
            return 0
    
    async def _measure_performance_improvement(self) -> Dict[str, float]:
        """测量性能改进"""
        try:
            # 获取当前指标
            current_metrics = {}
            
            for cache_type in CacheKeyType:
                metrics = self.cache_service.get_metrics(cache_type)
                if cache_type.value in metrics:
                    metric = metrics[cache_type.value]
                    current_metrics[cache_type.value] = {
                        "hit_rate": metric.hit_rate,
                        "avg_response_time": metric.avg_access_time
                    }
            
            return current_metrics
            
        except Exception as e:
            logger.error(f"Error measuring performance improvement: {str(e)}")
            return {}
    
    async def _load_warmup_queries(self):
        """加载预热查询"""
        try:
            # 常见的AI查询模式
            self.warmup_queries = [
                {"query": "如何编写测试用例", "context": {"domain": "testing"}},
                {"query": "代码审查最佳实践", "context": {"domain": "development"}},
                {"query": "项目管理建议", "context": {"domain": "management"}},
                {"query": "性能优化方法", "context": {"domain": "performance"}},
                {"query": "安全测试策略", "context": {"domain": "security"}},
                {"query": "自动化测试框架", "context": {"domain": "automation"}},
                {"query": "需求分析方法", "context": {"domain": "requirements"}},
                {"query": "缺陷管理流程", "context": {"domain": "quality"}},
                {"query": "团队协作工具", "context": {"domain": "collaboration"}},
                {"query": "持续集成配置", "context": {"domain": "devops"}}
            ]
            
            logger.debug(f"Loaded {len(self.warmup_queries)} warmup queries")
            
        except Exception as e:
            logger.error(f"Error loading warmup queries: {str(e)}")
            self.warmup_queries = []
    
    async def _background_cleanup_task(self):
        """后台清理任务"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # 检查是否需要清理
                if (datetime.utcnow() - self.last_cleanup).total_seconds() >= self.cleanup_interval:
                    logger.info("Starting background cache cleanup...")
                    
                    # 执行清理
                    await self.cache_service.cleanup_expired_cache()
                    await self.response_cache.cleanup_low_quality_cache()
                    
                    self.last_cleanup = datetime.utcnow()
                    logger.info("Background cache cleanup completed")
                
            except Exception as e:
                logger.error(f"Error in background cleanup task: {str(e)}")
                await asyncio.sleep(60)  # 出错时等待1分钟再重试
    
    async def get_cache_dashboard_data(self) -> Dict[str, Any]:
        """获取缓存仪表板数据"""
        try:
            # 获取健康报告
            health_report = await self.get_overall_health()
            
            # 获取各缓存类型的详细指标
            detailed_metrics = {}
            for cache_type in CacheKeyType:
                metrics = self.cache_service.get_metrics(cache_type)
                if cache_type.value in metrics:
                    detailed_metrics[cache_type.value] = metrics[cache_type.value]
            
            # 获取响应缓存统计
            response_stats = await self.response_cache.get_cache_statistics()
            
            # 获取上下文缓存统计
            context_stats = await self.context_cache.get_context_statistics()
            
            # 获取缓存配置信息
            cache_info = self.cache_service.get_cache_info()
            
            return {
                "health_report": health_report,
                "detailed_metrics": detailed_metrics,
                "response_cache_stats": response_stats,
                "context_cache_stats": context_stats,
                "cache_info": cache_info,
                "system_info": {
                    "auto_cleanup_enabled": self.auto_cleanup_enabled,
                    "cleanup_interval": self.cleanup_interval,
                    "warmup_enabled": self.warmup_enabled,
                    "warmup_queries_count": len(self.warmup_queries),
                    "last_cleanup": self.last_cleanup.isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cache dashboard data: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def clear_all_cache(self, confirm: bool = False) -> Dict[str, Any]:
        """清空所有缓存（危险操作）"""
        if not confirm:
            return {"error": "需要确认参数才能执行清空操作", "cleared": False}
        
        try:
            results = {}
            total_cleared = 0
            
            # 清空各类型缓存
            for cache_type in CacheKeyType:
                cleared_count = await self.cache_service.clear_pattern(cache_type)
                results[cache_type.value] = cleared_count
                total_cleared += cleared_count
            
            # 清空L1缓存
            l1_count = len(self.cache_service.l1_cache)
            self.cache_service.l1_cache.clear()
            self.cache_service.l1_cache_timestamps.clear()
            results["l1_cache"] = l1_count
            total_cleared += l1_count
            
            logger.warning(f"All cache cleared: {total_cleared} entries")
            
            return {
                "cleared": True,
                "total_entries": total_cleared,
                "details": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error clearing all cache: {str(e)}")
            return {"error": str(e), "cleared": False}
    
    async def export_cache_config(self) -> Dict[str, Any]:
        """导出缓存配置"""
        try:
            config_export = {
                "cache_configs": {},
                "health_thresholds": self.health_thresholds,
                "auto_cleanup_config": {
                    "enabled": self.auto_cleanup_enabled,
                    "interval": self.cleanup_interval
                },
                "warmup_config": {
                    "enabled": self.warmup_enabled,
                    "queries": self.warmup_queries
                },
                "export_timestamp": datetime.utcnow().isoformat()
            }
            
            # 导出各缓存类型配置
            for cache_type, config in self.cache_service.cache_configs.items():
                config_export["cache_configs"][cache_type.value] = {
                    "ttl": config.ttl,
                    "max_size": config.max_size,
                    "compression": config.compression,
                    "encryption": config.encryption,
                    "strategy": config.strategy.value,
                    "level": config.level.value,
                    "auto_refresh": config.auto_refresh,
                    "batch_size": config.batch_size
                }
            
            return config_export
            
        except Exception as e:
            logger.error(f"Error exporting cache config: {str(e)}")
            return {"error": str(e)}


# 创建全局缓存管理器实例
ai_cache_manager = AICacheManager()