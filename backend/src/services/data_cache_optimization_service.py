"""
数据缓存和优化服务

实现仪表板模块的多级缓存策略、数据预加载、增量更新、智能刷新、
数据质量监控和性能优化功能。
"""

import logging
import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import hashlib
import pickle
import gzip
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, BusinessLogicError
from ..utils.redis_client import get_redis_client
from ..utils.cache_utils import CacheClient, cache_client
from ..core.cache_config import DashboardCacheConfig, CacheStrategy, CacheMonitoring
from ..models.dashboard_config import DashboardConfig
from ..models.widget_definition import WidgetDefinition
from ..models.project import Project
from ..models.user import User

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别枚举"""
    L1_MEMORY = "l1_memory"      # 内存缓存 (最快)
    L2_REDIS = "l2_redis"        # Redis缓存 (快)
    L3_DATABASE = "l3_database"  # 数据库缓存 (慢)


class DataQuality(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"  # 优秀 (>95%)
    GOOD = "good"           # 良好 (80-95%)
    FAIR = "fair"           # 一般 (60-80%)
    POOR = "poor"           # 较差 (<60%)


class RefreshStrategy(Enum):
    """刷新策略枚举"""
    IMMEDIATE = "immediate"      # 立即刷新
    LAZY = "lazy"               # 懒加载刷新
    SCHEDULED = "scheduled"     # 定时刷新
    EVENT_DRIVEN = "event_driven"  # 事件驱动刷新


@dataclass
class CacheMetrics:
    """缓存指标数据类"""
    hit_count: int = 0
    miss_count: int = 0
    set_count: int = 0
    delete_count: int = 0
    error_count: int = 0
    total_response_time: float = 0.0
    avg_response_time: float = 0.0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    last_updated: datetime = None

    def calculate_rates(self):
        """计算命中率和未命中率"""
        total_requests = self.hit_count + self.miss_count
        if total_requests > 0:
            self.hit_rate = (self.hit_count / total_requests) * 100
            self.miss_rate = (self.miss_count / total_requests) * 100
        
        if self.hit_count + self.miss_count > 0:
            self.avg_response_time = self.total_response_time / (self.hit_count + self.miss_count)


@dataclass
class DataQualityMetrics:
    """数据质量指标"""
    completeness: float = 0.0      # 完整性
    accuracy: float = 0.0          # 准确性
    consistency: float = 0.0       # 一致性
    timeliness: float = 0.0        # 时效性
    validity: float = 0.0          # 有效性
    overall_score: float = 0.0     # 总体评分
    quality_level: DataQuality = DataQuality.FAIR
    last_checked: datetime = None

    def calculate_overall_score(self):
        """计算总体质量评分"""
        scores = [self.completeness, self.accuracy, self.consistency, self.timeliness, self.validity]
        valid_scores = [s for s in scores if s > 0]
        
        if valid_scores:
            self.overall_score = sum(valid_scores) / len(valid_scores)
            
            # 确定质量等级
            if self.overall_score >= 95:
                self.quality_level = DataQuality.EXCELLENT
            elif self.overall_score >= 80:
                self.quality_level = DataQuality.GOOD
            elif self.overall_score >= 60:
                self.quality_level = DataQuality.FAIR
            else:
                self.quality_level = DataQuality.POOR


@dataclass
class PreloadConfig:
    """预加载配置"""
    key_type: str
    data_generator: Callable
    params: Dict[str, Any]
    priority: int = 1  # 优先级 (1-10, 10最高)
    schedule: Optional[str] = None  # cron表达式
    dependencies: List[str] = None  # 依赖的其他缓存键


class DataCacheOptimizationService:
    """数据缓存和优化服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_client = cache_client
        self.config = DashboardCacheConfig()
        self.strategy = CacheStrategy()
        self.monitoring = CacheMonitoring()
        
        # 多级缓存
        self.l1_cache: Dict[str, Any] = {}  # 内存缓存
        self.l1_cache_ttl: Dict[str, datetime] = {}  # TTL跟踪
        self.l1_max_size = 1000  # 最大缓存条目数
        
        # 缓存指标
        self.cache_metrics: Dict[str, CacheMetrics] = defaultdict(CacheMetrics)
        
        # 数据质量监控
        self.quality_metrics: Dict[str, DataQualityMetrics] = defaultdict(DataQualityMetrics)
        
        # 预加载配置
        self.preload_configs: List[PreloadConfig] = []
        
        # 增量更新跟踪
        self.incremental_trackers: Dict[str, datetime] = {}
        
        # 性能监控
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # 异常处理
        self.error_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # 线程池用于异步操作
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # 启动后台任务
        asyncio.create_task(self._start_background_tasks())
    
    async def get_cached_data(
        self, 
        key_type: str, 
        data_generator: Optional[Callable] = None,
        force_refresh: bool = False,
        **kwargs
    ) -> Optional[Any]:
        """
        获取缓存数据 (多级缓存策略)
        
        Args:
            key_type: 缓存键类型
            data_generator: 数据生成函数
            force_refresh: 是否强制刷新
            **kwargs: 缓存键参数
            
        Returns:
            缓存数据或None
        """
        start_time = time.time()
        cache_key = self.config.get_cache_key(key_type, **kwargs)
        
        try:
            # 如果强制刷新，跳过缓存查找
            if not force_refresh:
                # L1: 内存缓存
                l1_data = await self._get_l1_cache(cache_key)
                if l1_data is not None:
                    self._record_cache_hit(key_type, time.time() - start_time, CacheLevel.L1_MEMORY)
                    return l1_data
                
                # L2: Redis缓存
                l2_data = await self.cache_client.aget(key_type, **kwargs)
                if l2_data is not None:
                    # 回填L1缓存
                    await self._set_l1_cache(cache_key, l2_data, key_type)
                    self._record_cache_hit(key_type, time.time() - start_time, CacheLevel.L2_REDIS)
                    return l2_data
            
            # L3: 生成新数据
            if data_generator:
                new_data = await self._generate_data_safely(data_generator, **kwargs)
                if new_data is not None:
                    # 设置多级缓存
                    await self._set_multilevel_cache(cache_key, key_type, new_data, **kwargs)
                    self._record_cache_miss(key_type, time.time() - start_time)
                    return new_data
            
            self._record_cache_miss(key_type, time.time() - start_time)
            return None
            
        except Exception as e:
            self._record_cache_error(key_type, str(e))
            logger.error(f"获取缓存数据失败 {cache_key}: {str(e)}")
            return None
    
    async def set_cached_data(
        self, 
        key_type: str, 
        data: Any, 
        ttl: Optional[int] = None,
        **kwargs
    ) -> bool:
        """
        设置缓存数据 (多级缓存)
        
        Args:
            key_type: 缓存键类型
            data: 要缓存的数据
            ttl: 生存时间
            **kwargs: 缓存键参数
            
        Returns:
            是否设置成功
        """
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            
            # 数据质量检查
            quality_score = await self._check_data_quality(key_type, data)
            if quality_score < 60:  # 质量过低，不缓存
                logger.warning(f"数据质量过低，跳过缓存: {cache_key}, 质量评分: {quality_score}")
                return False
            
            # 设置多级缓存
            success = await self._set_multilevel_cache(cache_key, key_type, data, **kwargs)
            
            if success:
                self._record_cache_set(key_type)
                
                # 更新质量指标
                await self._update_quality_metrics(key_type, data, quality_score)
            
            return success
            
        except Exception as e:
            self._record_cache_error(key_type, str(e))
            logger.error(f"设置缓存数据失败: {str(e)}")
            return False
    
    async def invalidate_cache(
        self, 
        key_type: str, 
        pattern: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        缓存失效 (多级缓存)
        
        Args:
            key_type: 缓存键类型
            pattern: 失效模式
            **kwargs: 缓存键参数
            
        Returns:
            失效的缓存条目数
        """
        try:
            invalidated_count = 0
            
            if pattern:
                # 模式匹配失效
                # L1缓存失效
                l1_keys_to_remove = [k for k in self.l1_cache.keys() if pattern in k]
                for key in l1_keys_to_remove:
                    del self.l1_cache[key]
                    if key in self.l1_cache_ttl:
                        del self.l1_cache_ttl[key]
                invalidated_count += len(l1_keys_to_remove)
                
                # L2缓存失效
                l2_count = await self.cache_client.ainvalidate_pattern(pattern)
                invalidated_count += l2_count
                
            else:
                # 单个键失效
                cache_key = self.config.get_cache_key(key_type, **kwargs)
                
                # L1缓存失效
                if cache_key in self.l1_cache:
                    del self.l1_cache[cache_key]
                    if cache_key in self.l1_cache_ttl:
                        del self.l1_cache_ttl[cache_key]
                    invalidated_count += 1
                
                # L2缓存失效
                success = await self.cache_client.adelete(key_type, **kwargs)
                if success:
                    invalidated_count += 1
            
            if invalidated_count > 0:
                self._record_cache_delete(key_type, invalidated_count)
            
            return invalidated_count
            
        except Exception as e:
            self._record_cache_error(key_type, str(e))
            logger.error(f"缓存失效失败: {str(e)}")
            return 0
    
    async def preload_cache(self, configs: Optional[List[PreloadConfig]] = None) -> Dict[str, bool]:
        """
        缓存预加载
        
        Args:
            configs: 预加载配置列表
            
        Returns:
            预加载结果字典
        """
        if configs is None:
            configs = self.preload_configs
        
        results = {}
        
        # 按优先级排序
        sorted_configs = sorted(configs, key=lambda x: x.priority, reverse=True)
        
        for config in sorted_configs:
            try:
                logger.info(f"开始预加载缓存: {config.key_type}")
                
                # 检查依赖
                if config.dependencies:
                    for dep in config.dependencies:
                        if dep not in results or not results[dep]:
                            logger.warning(f"依赖缓存预加载失败，跳过: {config.key_type} -> {dep}")
                            results[config.key_type] = False
                            continue
                
                # 生成数据
                data = await self._generate_data_safely(config.data_generator, **config.params)
                
                if data is not None:
                    # 设置缓存
                    success = await self.set_cached_data(config.key_type, data, **config.params)
                    results[config.key_type] = success
                    
                    if success:
                        logger.info(f"缓存预加载成功: {config.key_type}")
                    else:
                        logger.warning(f"缓存预加载失败: {config.key_type}")
                else:
                    results[config.key_type] = False
                    logger.warning(f"数据生成失败，预加载跳过: {config.key_type}")
                
            except Exception as e:
                results[config.key_type] = False
                logger.error(f"缓存预加载异常: {config.key_type}, {str(e)}")
        
        return results
    
    async def incremental_update(
        self, 
        key_type: str, 
        update_function: Callable,
        **kwargs
    ) -> bool:
        """
        增量更新缓存
        
        Args:
            key_type: 缓存键类型
            update_function: 更新函数
            **kwargs: 缓存键参数
            
        Returns:
            是否更新成功
        """
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            
            # 获取当前缓存数据
            current_data = await self.get_cached_data(key_type, **kwargs)
            
            if current_data is None:
                # 没有缓存数据，执行完整更新
                logger.info(f"没有缓存数据，执行完整更新: {cache_key}")
                return False
            
            # 获取上次更新时间
            last_update = self.incremental_trackers.get(cache_key)
            
            # 执行增量更新
            updated_data = await self._generate_data_safely(
                update_function, 
                current_data=current_data, 
                last_update=last_update,
                **kwargs
            )
            
            if updated_data is not None:
                # 更新缓存
                success = await self.set_cached_data(key_type, updated_data, **kwargs)
                
                if success:
                    # 记录更新时间
                    self.incremental_trackers[cache_key] = datetime.now()
                    logger.info(f"增量更新成功: {cache_key}")
                
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"增量更新失败: {str(e)}")
            return False
    
    async def intelligent_refresh(
        self, 
        key_type: str, 
        strategy: RefreshStrategy = RefreshStrategy.LAZY,
        **kwargs
    ) -> bool:
        """
        智能刷新缓存
        
        Args:
            key_type: 缓存键类型
            strategy: 刷新策略
            **kwargs: 缓存键参数
            
        Returns:
            是否刷新成功
        """
        try:
            cache_key = self.config.get_cache_key(key_type, **kwargs)
            
            # 根据策略决定是否刷新
            should_refresh = await self._should_refresh_cache(cache_key, key_type, strategy)
            
            if not should_refresh:
                return True  # 不需要刷新
            
            logger.info(f"智能刷新缓存: {cache_key}, 策略: {strategy.value}")
            
            # 执行刷新
            if strategy == RefreshStrategy.IMMEDIATE:
                # 立即刷新
                await self.invalidate_cache(key_type, **kwargs)
                return True
                
            elif strategy == RefreshStrategy.LAZY:
                # 懒加载刷新 - 标记为过期，下次访问时刷新
                await self._mark_cache_expired(cache_key)
                return True
                
            elif strategy == RefreshStrategy.SCHEDULED:
                # 定时刷新 - 添加到刷新队列
                await self._schedule_cache_refresh(cache_key, key_type, **kwargs)
                return True
                
            elif strategy == RefreshStrategy.EVENT_DRIVEN:
                # 事件驱动刷新 - 立即执行
                await self.invalidate_cache(key_type, **kwargs)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"智能刷新失败: {str(e)}")
            return False
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计数据
        """
        try:
            # 计算总体统计
            total_metrics = CacheMetrics()
            
            for metrics in self.cache_metrics.values():
                metrics.calculate_rates()
                total_metrics.hit_count += metrics.hit_count
                total_metrics.miss_count += metrics.miss_count
                total_metrics.set_count += metrics.set_count
                total_metrics.delete_count += metrics.delete_count
                total_metrics.error_count += metrics.error_count
                total_metrics.total_response_time += metrics.total_response_time
            
            total_metrics.calculate_rates()
            
            # L1缓存统计
            l1_stats = {
                "size": len(self.l1_cache),
                "max_size": self.l1_max_size,
                "usage_rate": len(self.l1_cache) / self.l1_max_size * 100
            }
            
            # L2缓存统计
            l2_stats = self.cache_client.get_stats()
            
            # 数据质量统计
            quality_stats = {}
            for key_type, quality in self.quality_metrics.items():
                quality.calculate_overall_score()
                quality_stats[key_type] = {
                    "overall_score": quality.overall_score,
                    "quality_level": quality.quality_level.value,
                    "completeness": quality.completeness,
                    "accuracy": quality.accuracy,
                    "consistency": quality.consistency,
                    "timeliness": quality.timeliness,
                    "validity": quality.validity
                }
            
            # 性能统计
            performance_stats = {}
            for key_type, history in self.performance_history.items():
                if history:
                    avg_time = sum(history) / len(history)
                    max_time = max(history)
                    min_time = min(history)
                    performance_stats[key_type] = {
                        "avg_response_time": avg_time,
                        "max_response_time": max_time,
                        "min_response_time": min_time,
                        "sample_count": len(history)
                    }
            
            return {
                "overall_metrics": asdict(total_metrics),
                "l1_cache": l1_stats,
                "l2_cache": l2_stats,
                "data_quality": quality_stats,
                "performance": performance_stats,
                "error_summary": self._get_error_summary(),
                "cache_health": await self._assess_cache_health()
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {str(e)}")
            return {}
    
    async def optimize_cache_performance(self) -> Dict[str, Any]:
        """
        优化缓存性能
        
        Returns:
            优化结果
        """
        try:
            optimization_results = {
                "l1_cleanup": 0,
                "l2_optimization": False,
                "preload_optimization": 0,
                "quality_improvement": 0
            }
            
            # L1缓存清理
            cleanup_count = await self._cleanup_l1_cache()
            optimization_results["l1_cleanup"] = cleanup_count
            
            # L2缓存优化
            l2_optimized = await self._optimize_l2_cache()
            optimization_results["l2_optimization"] = l2_optimized
            
            # 预加载优化
            preload_count = await self._optimize_preload_strategy()
            optimization_results["preload_optimization"] = preload_count
            
            # 数据质量改进
            quality_improvements = await self._improve_data_quality()
            optimization_results["quality_improvement"] = quality_improvements
            
            logger.info(f"缓存性能优化完成: {optimization_results}")
            return optimization_results
            
        except Exception as e:
            logger.error(f"缓存性能优化失败: {str(e)}")
            return {}
    
    # 私有方法
    
    async def _get_l1_cache(self, cache_key: str) -> Optional[Any]:
        """获取L1缓存数据"""
        if cache_key not in self.l1_cache:
            return None
        
        # 检查TTL
        if cache_key in self.l1_cache_ttl:
            if datetime.now() > self.l1_cache_ttl[cache_key]:
                # 已过期，删除
                del self.l1_cache[cache_key]
                del self.l1_cache_ttl[cache_key]
                return None
        
        return self.l1_cache[cache_key]
    
    async def _set_l1_cache(self, cache_key: str, data: Any, key_type: str):
        """设置L1缓存数据"""
        # 检查缓存大小限制
        if len(self.l1_cache) >= self.l1_max_size:
            # LRU淘汰
            await self._evict_l1_cache()
        
        self.l1_cache[cache_key] = data
        
        # 设置TTL
        ttl_seconds = self.config.get_ttl(key_type)
        if ttl_seconds > 0:
            self.l1_cache_ttl[cache_key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    async def _set_multilevel_cache(
        self, 
        cache_key: str, 
        key_type: str, 
        data: Any, 
        **kwargs
    ) -> bool:
        """设置多级缓存"""
        try:
            # L1缓存
            await self._set_l1_cache(cache_key, data, key_type)
            
            # L2缓存
            success = await self.cache_client.aset(key_type, data, **kwargs)
            
            return success
            
        except Exception as e:
            logger.error(f"设置多级缓存失败: {str(e)}")
            return False
    
    async def _generate_data_safely(self, data_generator: Callable, **kwargs) -> Optional[Any]:
        """安全地生成数据"""
        try:
            if asyncio.iscoroutinefunction(data_generator):
                return await data_generator(**kwargs)
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(self.executor, data_generator, **kwargs)
                
        except Exception as e:
            logger.error(f"数据生成失败: {str(e)}")
            return None
    
    async def _check_data_quality(self, key_type: str, data: Any) -> float:
        """检查数据质量"""
        try:
            quality_score = 100.0
            
            # 完整性检查
            if data is None:
                return 0.0
            
            if isinstance(data, dict):
                # 检查必要字段
                required_fields = self._get_required_fields(key_type)
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    quality_score -= len(missing_fields) * 10
                
                # 检查空值
                empty_values = [k for k, v in data.items() if v is None or v == ""]
                if empty_values:
                    quality_score -= len(empty_values) * 5
            
            elif isinstance(data, list):
                # 检查列表完整性
                if len(data) == 0:
                    quality_score -= 20
            
            # 时效性检查
            if hasattr(data, 'updated_at') or (isinstance(data, dict) and 'updated_at' in data):
                updated_at = data.get('updated_at') if isinstance(data, dict) else data.updated_at
                if updated_at:
                    age_hours = (datetime.now() - updated_at).total_seconds() / 3600
                    if age_hours > 24:  # 超过24小时
                        quality_score -= min(20, age_hours / 24 * 5)
            
            return max(0.0, quality_score)
            
        except Exception as e:
            logger.error(f"数据质量检查失败: {str(e)}")
            return 50.0  # 默认中等质量
    
    def _get_required_fields(self, key_type: str) -> List[str]:
        """获取数据类型的必要字段"""
        field_mapping = {
            "project_overview": ["total_projects", "active_projects", "key_metrics"],
            "requirement_metrics": ["total_requirements", "completion_rate", "status_distribution"],
            "test_metrics": ["total_test_cases", "pass_rate", "execution_rate"],
            "dashboard_config": ["user_id", "role_type", "layout_config"],
            "widget_data": ["widget_type", "data", "timestamp"]
        }
        
        return field_mapping.get(key_type, [])
    
    async def _update_quality_metrics(self, key_type: str, data: Any, quality_score: float):
        """更新数据质量指标"""
        try:
            metrics = self.quality_metrics[key_type]
            
            # 更新各项指标 (简化实现)
            metrics.completeness = quality_score
            metrics.accuracy = quality_score * 0.95  # 假设准确性略低于完整性
            metrics.consistency = quality_score * 0.9
            metrics.timeliness = quality_score * 0.85
            metrics.validity = quality_score * 0.92
            metrics.last_checked = datetime.now()
            
            metrics.calculate_overall_score()
            
        except Exception as e:
            logger.error(f"更新质量指标失败: {str(e)}")
    
    def _record_cache_hit(self, key_type: str, response_time: float, cache_level: CacheLevel):
        """记录缓存命中"""
        metrics = self.cache_metrics[key_type]
        metrics.hit_count += 1
        metrics.total_response_time += response_time
        metrics.last_updated = datetime.now()
        
        # 记录性能历史
        self.performance_history[key_type].append(response_time)
        
        logger.debug(f"缓存命中: {key_type}, 级别: {cache_level.value}, 响应时间: {response_time:.3f}ms")
    
    def _record_cache_miss(self, key_type: str, response_time: float):
        """记录缓存未命中"""
        metrics = self.cache_metrics[key_type]
        metrics.miss_count += 1
        metrics.total_response_time += response_time
        metrics.last_updated = datetime.now()
        
        # 记录性能历史
        self.performance_history[key_type].append(response_time)
        
        logger.debug(f"缓存未命中: {key_type}, 响应时间: {response_time:.3f}ms")
    
    def _record_cache_set(self, key_type: str):
        """记录缓存设置"""
        metrics = self.cache_metrics[key_type]
        metrics.set_count += 1
        metrics.last_updated = datetime.now()
    
    def _record_cache_delete(self, key_type: str, count: int = 1):
        """记录缓存删除"""
        metrics = self.cache_metrics[key_type]
        metrics.delete_count += count
        metrics.last_updated = datetime.now()
    
    def _record_cache_error(self, key_type: str, error_message: str):
        """记录缓存错误"""
        metrics = self.cache_metrics[key_type]
        metrics.error_count += 1
        metrics.last_updated = datetime.now()
        
        # 记录错误历史
        error_record = {
            "timestamp": datetime.now(),
            "key_type": key_type,
            "error": error_message
        }
        
        self.error_history[key_type].append(error_record)
        
        # 保持错误历史在合理范围内
        if len(self.error_history[key_type]) > 50:
            self.error_history[key_type] = self.error_history[key_type][-50:]
    
    async def _should_refresh_cache(
        self, 
        cache_key: str, 
        key_type: str, 
        strategy: RefreshStrategy
    ) -> bool:
        """判断是否应该刷新缓存"""
        try:
            if strategy == RefreshStrategy.IMMEDIATE:
                return True
            
            # 获取缓存指标
            metrics = self.cache_metrics.get(key_type)
            if not metrics:
                return True
            
            # 计算命中率
            metrics.calculate_rates()
            
            if strategy == RefreshStrategy.LAZY:
                # 懒加载策略：命中率低于阈值时刷新
                return metrics.hit_rate < 70
            
            elif strategy == RefreshStrategy.SCHEDULED:
                # 定时策略：根据TTL和使用频率决定
                ttl = self.config.get_ttl(key_type)
                if ttl > 0:
                    # 检查是否接近过期
                    return True  # 简化实现，总是调度刷新
                
            elif strategy == RefreshStrategy.EVENT_DRIVEN:
                # 事件驱动：检查数据质量
                quality = self.quality_metrics.get(key_type)
                if quality:
                    quality.calculate_overall_score()
                    return quality.overall_score < 80
            
            return False
            
        except Exception as e:
            logger.error(f"判断缓存刷新失败: {str(e)}")
            return False
    
    async def _mark_cache_expired(self, cache_key: str):
        """标记缓存为过期"""
        # L1缓存过期
        if cache_key in self.l1_cache_ttl:
            self.l1_cache_ttl[cache_key] = datetime.now() - timedelta(seconds=1)
    
    async def _schedule_cache_refresh(self, cache_key: str, key_type: str, **kwargs):
        """调度缓存刷新"""
        # 简化实现：添加到后台任务队列
        logger.info(f"调度缓存刷新: {cache_key}")
    
    async def _evict_l1_cache(self):
        """L1缓存淘汰 (LRU)"""
        if len(self.l1_cache) < self.l1_max_size:
            return
        
        # 简化实现：删除最旧的条目
        oldest_key = min(self.l1_cache_ttl.keys(), key=lambda k: self.l1_cache_ttl[k])
        del self.l1_cache[oldest_key]
        del self.l1_cache_ttl[oldest_key]
    
    async def _cleanup_l1_cache(self) -> int:
        """清理L1缓存过期条目"""
        now = datetime.now()
        expired_keys = [
            key for key, ttl in self.l1_cache_ttl.items() 
            if ttl < now
        ]
        
        for key in expired_keys:
            del self.l1_cache[key]
            del self.l1_cache_ttl[key]
        
        return len(expired_keys)
    
    async def _optimize_l2_cache(self) -> bool:
        """优化L2缓存"""
        try:
            # 获取Redis信息
            redis_client = await self.cache_client.async_client
            info = await redis_client.info()
            
            # 检查内存使用情况
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            if max_memory > 0:
                memory_usage_percent = (used_memory / max_memory) * 100
                
                # 如果内存使用率过高，执行清理
                if memory_usage_percent > 85:
                    logger.warning(f"Redis内存使用率过高: {memory_usage_percent:.2f}%")
                    
                    # 清理过期键
                    await self._cleanup_expired_keys()
                    
                    # 清理低优先级缓存
                    await self._cleanup_low_priority_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"L2缓存优化失败: {str(e)}")
            return False
    
    async def _cleanup_expired_keys(self):
        """清理过期键"""
        try:
            redis_client = await self.cache_client.async_client
            
            # 获取所有命名空间的键
            for namespace in CacheNamespace:
                pattern = f"{namespace.value}:*"
                keys = await redis_client.keys(pattern)
                
                # 检查每个键的TTL
                for key in keys:
                    ttl = await redis_client.ttl(key)
                    if ttl == -2:  # 键已过期但未被清理
                        await redis_client.delete(key)
                        logger.debug(f"清理过期键: {key}")
        
        except Exception as e:
            logger.error(f"清理过期键失败: {str(e)}")
    
    async def _cleanup_low_priority_cache(self):
        """清理低优先级缓存"""
        try:
            # 清理临时数据缓存
            temp_pattern = f"{CacheNamespace.TEMP.value}:*"
            await self.cache_client.ainvalidate_pattern(temp_pattern)
            
            # 清理旧的API响应缓存
            api_pattern = f"{CacheNamespace.TEMP.value}:api:*"
            await self.cache_client.ainvalidate_pattern(api_pattern)
            
            logger.info("低优先级缓存清理完成")
            
        except Exception as e:
            logger.error(f"清理低优先级缓存失败: {str(e)}")
    
    async def _optimize_preload_strategy(self) -> int:
        """优化预加载策略"""
        try:
            optimization_count = 0
            
            # 分析缓存使用模式
            usage_patterns = await self._analyze_cache_usage_patterns()
            
            # 根据使用模式调整预加载配置
            for key_type, pattern in usage_patterns.items():
                if pattern['hit_rate'] < 50:  # 命中率低的数据
                    # 降低预加载优先级
                    for config in self.preload_configs:
                        if config.key_type == key_type:
                            config.priority = max(1, config.priority - 1)
                            optimization_count += 1
                
                elif pattern['hit_rate'] > 90:  # 命中率高的数据
                    # 提高预加载优先级
                    for config in self.preload_configs:
                        if config.key_type == key_type:
                            config.priority = min(10, config.priority + 1)
                            optimization_count += 1
            
            return optimization_count
            
        except Exception as e:
            logger.error(f"预加载策略优化失败: {str(e)}")
            return 0
    
    async def _analyze_cache_usage_patterns(self) -> Dict[str, Dict[str, Any]]:
        """分析缓存使用模式"""
        patterns = {}
        
        for key_type, metrics in self.cache_metrics.items():
            metrics.calculate_rates()
            
            patterns[key_type] = {
                'hit_rate': metrics.hit_rate,
                'miss_rate': metrics.miss_rate,
                'avg_response_time': metrics.avg_response_time,
                'total_requests': metrics.hit_count + metrics.miss_count,
                'error_rate': metrics.error_count / max(1, metrics.hit_count + metrics.miss_count) * 100
            }
        
        return patterns
    
    async def _improve_data_quality(self) -> int:
        """改进数据质量"""
        try:
            improvement_count = 0
            
            for key_type, quality in self.quality_metrics.items():
                quality.calculate_overall_score()
                
                if quality.overall_score < 80:
                    # 质量较低的数据需要改进
                    logger.info(f"改进数据质量: {key_type}, 当前评分: {quality.overall_score}")
                    
                    # 清理质量差的缓存，强制重新生成
                    await self.invalidate_cache(key_type)
                    improvement_count += 1
            
            return improvement_count
            
        except Exception as e:
            logger.error(f"数据质量改进失败: {str(e)}")
            return 0
    
    def _get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        error_summary = {
            "total_errors": 0,
            "error_types": {},
            "recent_errors": []
        }
        
        for key_type, errors in self.error_history.items():
            error_summary["total_errors"] += len(errors)
            
            # 统计错误类型
            for error in errors:
                error_msg = error.get("error", "Unknown")
                error_type = error_msg.split(":")[0] if ":" in error_msg else "General"
                
                if error_type not in error_summary["error_types"]:
                    error_summary["error_types"][error_type] = 0
                error_summary["error_types"][error_type] += 1
            
            # 获取最近的错误
            if errors:
                recent_error = errors[-1]
                recent_error["key_type"] = key_type
                error_summary["recent_errors"].append(recent_error)
        
        # 按时间排序最近错误
        error_summary["recent_errors"].sort(
            key=lambda x: x.get("timestamp", datetime.min),
            reverse=True
        )
        error_summary["recent_errors"] = error_summary["recent_errors"][:10]
        
        return error_summary
    
    async def _assess_cache_health(self) -> Dict[str, Any]:
        """评估缓存健康状况"""
        try:
            health_score = 100.0
            health_issues = []
            
            # 计算总体指标
            total_metrics = CacheMetrics()
            for metrics in self.cache_metrics.values():
                metrics.calculate_rates()
                total_metrics.hit_count += metrics.hit_count
                total_metrics.miss_count += metrics.miss_count
                total_metrics.error_count += metrics.error_count
                total_metrics.total_response_time += metrics.total_response_time
            
            total_metrics.calculate_rates()
            
            # 评估命中率
            if total_metrics.hit_rate < 70:
                health_score -= 20
                health_issues.append(f"缓存命中率过低: {total_metrics.hit_rate:.2f}%")
            
            # 评估错误率
            total_requests = total_metrics.hit_count + total_metrics.miss_count
            if total_requests > 0:
                error_rate = (total_metrics.error_count / total_requests) * 100
                if error_rate > 5:
                    health_score -= 15
                    health_issues.append(f"错误率过高: {error_rate:.2f}%")
            
            # 评估响应时间
            if total_metrics.avg_response_time > 50:  # 50ms
                health_score -= 10
                health_issues.append(f"平均响应时间过长: {total_metrics.avg_response_time:.2f}ms")
            
            # 评估L1缓存使用率
            l1_usage_rate = len(self.l1_cache) / self.l1_max_size * 100
            if l1_usage_rate > 90:
                health_score -= 10
                health_issues.append(f"L1缓存使用率过高: {l1_usage_rate:.2f}%")
            
            # 评估数据质量
            quality_scores = []
            for quality in self.quality_metrics.values():
                quality.calculate_overall_score()
                quality_scores.append(quality.overall_score)
            
            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
                if avg_quality < 80:
                    health_score -= 15
                    health_issues.append(f"数据质量偏低: {avg_quality:.2f}")
            
            # 确定健康等级
            if health_score >= 90:
                health_level = "excellent"
            elif health_score >= 75:
                health_level = "good"
            elif health_score >= 60:
                health_level = "fair"
            else:
                health_level = "poor"
            
            return {
                "health_score": max(0, health_score),
                "health_level": health_level,
                "issues": health_issues,
                "recommendations": self._get_health_recommendations(health_issues)
            }
            
        except Exception as e:
            logger.error(f"缓存健康评估失败: {str(e)}")
            return {
                "health_score": 0,
                "health_level": "unknown",
                "issues": ["健康评估失败"],
                "recommendations": []
            }
    
    def _get_health_recommendations(self, issues: List[str]) -> List[str]:
        """获取健康改进建议"""
        recommendations = []
        
        for issue in issues:
            if "命中率过低" in issue:
                recommendations.append("考虑增加缓存TTL或优化缓存策略")
            elif "错误率过高" in issue:
                recommendations.append("检查数据源稳定性和网络连接")
            elif "响应时间过长" in issue:
                recommendations.append("优化数据序列化或增加缓存层级")
            elif "使用率过高" in issue:
                recommendations.append("增加L1缓存大小或优化淘汰策略")
            elif "数据质量偏低" in issue:
                recommendations.append("改进数据验证和清洗流程")
        
        return recommendations
    
    async def _start_background_tasks(self):
        """启动后台任务"""
        try:
            # 定期清理任务
            asyncio.create_task(self._periodic_cleanup())
            
            # 定期优化任务
            asyncio.create_task(self._periodic_optimization())
            
            # 定期健康检查任务
            asyncio.create_task(self._periodic_health_check())
            
            logger.info("缓存后台任务启动成功")
            
        except Exception as e:
            logger.error(f"启动后台任务失败: {str(e)}")
    
    async def _periodic_cleanup(self):
        """定期清理任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 5分钟执行一次
                
                # L1缓存清理
                cleanup_count = await self._cleanup_l1_cache()
                if cleanup_count > 0:
                    logger.info(f"定期清理L1缓存: {cleanup_count}个过期条目")
                
                # 错误历史清理
                self._cleanup_error_history()
                
            except Exception as e:
                logger.error(f"定期清理任务异常: {str(e)}")
    
    async def _periodic_optimization(self):
        """定期优化任务"""
        while True:
            try:
                await asyncio.sleep(1800)  # 30分钟执行一次
                
                # 执行性能优化
                await self.optimize_cache_performance()
                
                logger.info("定期缓存优化完成")
                
            except Exception as e:
                logger.error(f"定期优化任务异常: {str(e)}")
    
    async def _periodic_health_check(self):
        """定期健康检查任务"""
        while True:
            try:
                await asyncio.sleep(600)  # 10分钟执行一次
                
                # 健康检查
                health = await self._assess_cache_health()
                
                if health["health_level"] in ["poor", "fair"]:
                    logger.warning(f"缓存健康状况: {health['health_level']}, 评分: {health['health_score']}")
                    for issue in health["issues"]:
                        logger.warning(f"健康问题: {issue}")
                
            except Exception as e:
                logger.error(f"定期健康检查任务异常: {str(e)}")
    
    def _cleanup_error_history(self):
        """清理错误历史"""
        cutoff_time = datetime.now() - timedelta(hours=24)  # 保留24小时内的错误
        
        for key_type in list(self.error_history.keys()):
            errors = self.error_history[key_type]
            
            # 过滤出24小时内的错误
            recent_errors = [
                error for error in errors
                if error.get("timestamp", datetime.min) > cutoff_time
            ]
            
            if recent_errors:
                self.error_history[key_type] = recent_errors
            else:
                del self.error_history[key_type]
        
        return len(expired_keys)
    
    async def _optimize_l2_cache(self) -> bool:
        """优化L2缓存"""
        try:
            # 检查Redis健康状态
            health = self.cache_client.health_check()
            
            if health.get("status") == "healthy":
                # 执行优化操作 (如内存整理等)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"L2缓存优化失败: {str(e)}")
            return False
    
    async def _optimize_preload_strategy(self) -> int:
        """优化预加载策略"""
        # 分析缓存使用模式，调整预加载配置
        optimized_count = 0
        
        for key_type, metrics in self.cache_metrics.items():
            metrics.calculate_rates()
            
            # 如果命中率很高，增加预加载优先级
            if metrics.hit_rate > 90:
                # 查找对应的预加载配置并提高优先级
                for config in self.preload_configs:
                    if config.key_type == key_type:
                        config.priority = min(10, config.priority + 1)
                        optimized_count += 1
                        break
        
        return optimized_count
    
    async def _improve_data_quality(self) -> int:
        """改进数据质量"""
        improvements = 0
        
        for key_type, quality in self.quality_metrics.items():
            quality.calculate_overall_score()
            
            if quality.quality_level == DataQuality.POOR:
                # 对质量差的数据执行清理
                await self.invalidate_cache(key_type)
                improvements += 1
        
        return improvements
    
    def _get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        total_errors = sum(len(errors) for errors in self.error_history.values())
        
        recent_errors = []
        for key_type, errors in self.error_history.items():
            recent_errors.extend(errors[-5:])  # 最近5个错误
        
        # 按时间排序
        recent_errors.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "total_errors": total_errors,
            "error_types": len(self.error_history),
            "recent_errors": recent_errors[:10]  # 最近10个错误
        }
    
    async def _assess_cache_health(self) -> Dict[str, Any]:
        """评估缓存健康状况"""
        try:
            # 计算总体指标
            total_requests = sum(
                m.hit_count + m.miss_count 
                for m in self.cache_metrics.values()
            )
            
            total_hits = sum(m.hit_count for m in self.cache_metrics.values())
            overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
            
            total_errors = sum(m.error_count for m in self.cache_metrics.values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            
            # 评估健康等级
            if overall_hit_rate >= 90 and error_rate < 1:
                health_level = "excellent"
            elif overall_hit_rate >= 80 and error_rate < 5:
                health_level = "good"
            elif overall_hit_rate >= 60 and error_rate < 10:
                health_level = "fair"
            else:
                health_level = "poor"
            
            return {
                "health_level": health_level,
                "overall_hit_rate": round(overall_hit_rate, 2),
                "error_rate": round(error_rate, 2),
                "total_requests": total_requests,
                "l1_cache_usage": len(self.l1_cache) / self.l1_max_size * 100,
                "recommendations": self._get_health_recommendations(health_level, overall_hit_rate, error_rate)
            }
            
        except Exception as e:
            logger.error(f"评估缓存健康状况失败: {str(e)}")
            return {"health_level": "unknown", "error": str(e)}
    
    def _get_health_recommendations(
        self, 
        health_level: str, 
        hit_rate: float, 
        error_rate: float
    ) -> List[str]:
        """获取健康改进建议"""
        recommendations = []
        
        if health_level == "poor":
            recommendations.append("缓存性能严重不足，建议检查缓存配置和数据质量")
            
        if hit_rate < 70:
            recommendations.append("缓存命中率过低，建议优化缓存策略或增加预加载")
            
        if error_rate > 5:
            recommendations.append("错误率过高，建议检查缓存服务状态和网络连接")
            
        if len(self.l1_cache) / self.l1_max_size > 0.9:
            recommendations.append("L1缓存使用率过高，建议增加缓存大小或优化淘汰策略")
        
        if not recommendations:
            recommendations.append("缓存运行状况良好，继续保持当前配置")
        
        return recommendations
    
    async def _start_background_tasks(self):
        """启动后台任务"""
        try:
            # 定期清理过期缓存
            asyncio.create_task(self._periodic_cleanup())
            
            # 定期性能优化
            asyncio.create_task(self._periodic_optimization())
            
            # 定期健康检查
            asyncio.create_task(self._periodic_health_check())
            
        except Exception as e:
            logger.error(f"启动后台任务失败: {str(e)}")
    
    async def _periodic_cleanup(self):
        """定期清理任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟执行一次
                
                # 清理L1缓存
                cleanup_count = await self._cleanup_l1_cache()
                if cleanup_count > 0:
                    logger.info(f"定期清理L1缓存，清理条目数: {cleanup_count}")
                
            except Exception as e:
                logger.error(f"定期清理任务失败: {str(e)}")
    
    async def _periodic_optimization(self):
        """定期优化任务"""
        while True:
            try:
                await asyncio.sleep(1800)  # 每30分钟执行一次
                
                # 执行性能优化
                results = await self.optimize_cache_performance()
                logger.info(f"定期性能优化完成: {results}")
                
            except Exception as e:
                logger.error(f"定期优化任务失败: {str(e)}")
    
    async def _periodic_health_check(self):
        """定期健康检查任务"""
        while True:
            try:
                await asyncio.sleep(600)  # 每10分钟执行一次
                
                # 执行健康检查
                health = await self._assess_cache_health()
                
                if health.get("health_level") in ["poor", "fair"]:
                    logger.warning(f"缓存健康状况需要关注: {health}")
                
            except Exception as e:
                logger.error(f"定期健康检查失败: {str(e)}")


# 全局服务实例
data_cache_optimization_service = None

async def get_data_cache_optimization_service(db: AsyncSession = None) -> DataCacheOptimizationService:
    """获取数据缓存优化服务实例"""
    global data_cache_optimization_service
    
    if data_cache_optimization_service is None:
        if db is None:
            async for session in get_async_session():
                data_cache_optimization_service = DataCacheOptimizationService(session)
                break
        else:
            data_cache_optimization_service = DataCacheOptimizationService(db)
    
    return data_cache_optimization_service