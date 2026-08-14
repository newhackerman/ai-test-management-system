"""
图表性能优化服务

实现图表数据的预处理、缓存和性能监控功能
"""

import logging
import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc

from ..core.database import get_async_session, get_async_session_ctx
from ..utils.cache_utils import cache_client
from ..utils.redis_client import get_redis_client
from ..models.dashboard_config import DashboardConfig
from ..models.project import Project

logger = logging.getLogger(__name__)


class DataSamplingStrategy(Enum):
    """数据采样策略"""
    UNIFORM = "uniform"          # 均匀采样
    ADAPTIVE = "adaptive"        # 自适应采样
    IMPORTANCE = "importance"    # 重要性采样
    TIME_BASED = "time_based"    # 基于时间的采样


class ChartType(Enum):
    """图表类型"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    FUNNEL = "funnel"
    RADAR = "radar"


@dataclass
class ChartPerformanceConfig:
    """图表性能配置"""
    max_data_points: int = 1000
    sampling_strategy: DataSamplingStrategy = DataSamplingStrategy.ADAPTIVE
    enable_caching: bool = True
    cache_ttl: int = 300  # 5分钟
    enable_compression: bool = True
    enable_pagination: bool = True
    page_size: int = 100
    enable_aggregation: bool = True
    aggregation_interval: str = "1h"  # 1小时聚合


@dataclass
class ChartMetrics:
    """图表性能指标"""
    chart_id: str
    chart_type: ChartType
    data_points: int
    processing_time: float
    memory_usage: float
    cache_hit: bool
    compression_ratio: float
    render_time: float
    timestamp: datetime


class ChartPerformanceService:
    """图表性能优化服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_client = cache_client
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.metrics_history: Dict[str, List[ChartMetrics]] = {}
        
    async def optimize_chart_data(
        self,
        chart_id: str,
        chart_type: ChartType,
        data: List[Dict[str, Any]],
        config: Optional[ChartPerformanceConfig] = None
    ) -> Dict[str, Any]:
        """
        优化图表数据
        
        Args:
            chart_id: 图表ID
            chart_type: 图表类型
            data: 原始数据
            config: 性能配置
            
        Returns:
            优化后的数据和元信息
        """
        if config is None:
            config = ChartPerformanceConfig()
        
        start_time = time.time()
        
        try:
            # 检查缓存
            if config.enable_caching:
                cached_result = await self._get_cached_data(chart_id, data)
                if cached_result:
                    logger.debug(f"图表数据缓存命中: {chart_id}")
                    return cached_result
            
            # 数据预处理
            processed_data = await self._preprocess_data(data, chart_type)
            
            # 数据采样
            if len(processed_data) > config.max_data_points:
                processed_data = await self._sample_data(
                    processed_data, 
                    config.max_data_points,
                    config.sampling_strategy,
                    chart_type
                )
            
            # 数据聚合
            if config.enable_aggregation and chart_type in [ChartType.LINE, ChartType.AREA]:
                processed_data = await self._aggregate_data(
                    processed_data,
                    config.aggregation_interval
                )
            
            # 数据压缩
            compression_ratio = 1.0
            if config.enable_compression:
                processed_data, compression_ratio = await self._compress_data(processed_data)
            
            # 构建结果
            result = {
                "chart_id": chart_id,
                "chart_type": chart_type.value,
                "data": processed_data,
                "metadata": {
                    "original_count": len(data),
                    "processed_count": len(processed_data),
                    "compression_ratio": compression_ratio,
                    "processing_time": time.time() - start_time,
                    "optimizations_applied": self._get_applied_optimizations(config),
                    "cache_key": self._generate_cache_key(chart_id, data)
                }
            }
            
            # 缓存结果
            if config.enable_caching:
                await self._cache_data(chart_id, data, result, config.cache_ttl)
            
            # 记录性能指标
            await self._record_metrics(
                chart_id, chart_type, len(data), len(processed_data),
                time.time() - start_time, compression_ratio, False
            )
            
            return result
            
        except Exception as e:
            logger.error(f"图表数据优化失败 {chart_id}: {str(e)}")
            # 返回原始数据作为降级方案
            return {
                "chart_id": chart_id,
                "chart_type": chart_type.value,
                "data": data,
                "metadata": {
                    "original_count": len(data),
                    "processed_count": len(data),
                    "compression_ratio": 1.0,
                    "processing_time": time.time() - start_time,
                    "error": str(e)
                }
            }
    
    async def get_paginated_data(
        self,
        chart_id: str,
        page: int = 0,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        获取分页数据
        
        Args:
            chart_id: 图表ID
            page: 页码
            page_size: 页大小
            
        Returns:
            分页数据
        """
        try:
            # 从缓存获取完整数据
            cache_key = f"chart_full_data:{chart_id}"
            full_data = await self.cache_client.aget("chart_data", chart_id=chart_id)
            
            if not full_data:
                return {"data": [], "total": 0, "page": page, "page_size": page_size}
            
            data = full_data.get("data", [])
            total = len(data)
            
            # 计算分页
            start_idx = page * page_size
            end_idx = start_idx + page_size
            page_data = data[start_idx:end_idx]
            
            return {
                "data": page_data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "has_next": end_idx < total,
                "has_prev": page > 0
            }
            
        except Exception as e:
            logger.error(f"获取分页数据失败 {chart_id}: {str(e)}")
            return {"data": [], "total": 0, "page": page, "page_size": page_size}
    
    async def get_chart_metrics(self, chart_id: str) -> Dict[str, Any]:
        """
        获取图表性能指标
        
        Args:
            chart_id: 图表ID
            
        Returns:
            性能指标
        """
        try:
            metrics_list = self.metrics_history.get(chart_id, [])
            
            if not metrics_list:
                return {"chart_id": chart_id, "metrics": []}
            
            # 计算统计信息
            recent_metrics = metrics_list[-10:]  # 最近10次
            
            avg_processing_time = sum(m.processing_time for m in recent_metrics) / len(recent_metrics)
            avg_memory_usage = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
            cache_hit_rate = sum(1 for m in recent_metrics if m.cache_hit) / len(recent_metrics) * 100
            
            return {
                "chart_id": chart_id,
                "total_renders": len(metrics_list),
                "recent_metrics": [asdict(m) for m in recent_metrics],
                "statistics": {
                    "avg_processing_time": avg_processing_time,
                    "avg_memory_usage": avg_memory_usage,
                    "cache_hit_rate": cache_hit_rate,
                    "last_render": recent_metrics[-1].timestamp.isoformat() if recent_metrics else None
                }
            }
            
        except Exception as e:
            logger.error(f"获取图表指标失败 {chart_id}: {str(e)}")
            return {"chart_id": chart_id, "error": str(e)}
    
    async def optimize_multiple_charts(
        self,
        chart_requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量优化多个图表
        
        Args:
            chart_requests: 图表请求列表
            
        Returns:
            优化结果列表
        """
        try:
            # 并发处理多个图表
            tasks = []
            for request in chart_requests:
                task = self.optimize_chart_data(
                    request["chart_id"],
                    ChartType(request["chart_type"]),
                    request["data"],
                    ChartPerformanceConfig(**request.get("config", {}))
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"批量优化失败 {chart_requests[i]['chart_id']}: {str(result)}")
                    processed_results.append({
                        "chart_id": chart_requests[i]["chart_id"],
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"批量图表优化失败: {str(e)}")
            return []
    
    # 私有方法
    
    async def _preprocess_data(
        self, 
        data: List[Dict[str, Any]], 
        chart_type: ChartType
    ) -> List[Dict[str, Any]]:
        """预处理数据"""
        try:
            if not data:
                return data
            
            # 数据清洗
            cleaned_data = []
            for item in data:
                # 移除空值和无效数据
                if self._is_valid_data_point(item, chart_type):
                    cleaned_data.append(item)
            
            # 数据排序
            if chart_type in [ChartType.LINE, ChartType.AREA]:
                # 时间序列数据按时间排序
                if 'timestamp' in cleaned_data[0] if cleaned_data else {}:
                    cleaned_data.sort(key=lambda x: x.get('timestamp', 0))
                elif 'date' in cleaned_data[0] if cleaned_data else {}:
                    cleaned_data.sort(key=lambda x: x.get('date', ''))
            
            return cleaned_data
            
        except Exception as e:
            logger.error(f"数据预处理失败: {str(e)}")
            return data
    
    def _is_valid_data_point(self, item: Dict[str, Any], chart_type: ChartType) -> bool:
        """检查数据点是否有效"""
        try:
            if not isinstance(item, dict):
                return False
            
            # 基本检查
            if not item:
                return False
            
            # 根据图表类型检查必要字段
            if chart_type == ChartType.PIE:
                return 'name' in item and 'value' in item and item['value'] is not None
            elif chart_type in [ChartType.LINE, ChartType.AREA]:
                return 'value' in item and item['value'] is not None
            elif chart_type == ChartType.BAR:
                return 'category' in item and 'value' in item and item['value'] is not None
            elif chart_type == ChartType.SCATTER:
                return 'x' in item and 'y' in item and item['x'] is not None and item['y'] is not None
            
            return True
            
        except Exception:
            return False
    
    async def _sample_data(
        self,
        data: List[Dict[str, Any]],
        max_points: int,
        strategy: DataSamplingStrategy,
        chart_type: ChartType
    ) -> List[Dict[str, Any]]:
        """数据采样"""
        try:
            if len(data) <= max_points:
                return data
            
            if strategy == DataSamplingStrategy.UNIFORM:
                # 均匀采样
                step = len(data) / max_points
                indices = [int(i * step) for i in range(max_points)]
                return [data[i] for i in indices if i < len(data)]
            
            elif strategy == DataSamplingStrategy.ADAPTIVE:
                # 自适应采样 - 保留重要数据点
                return await self._adaptive_sampling(data, max_points, chart_type)
            
            elif strategy == DataSamplingStrategy.IMPORTANCE:
                # 重要性采样 - 基于数据值的重要性
                return await self._importance_sampling(data, max_points, chart_type)
            
            elif strategy == DataSamplingStrategy.TIME_BASED:
                # 基于时间的采样
                return await self._time_based_sampling(data, max_points)
            
            else:
                # 默认均匀采样
                step = len(data) // max_points
                return data[::step][:max_points]
                
        except Exception as e:
            logger.error(f"数据采样失败: {str(e)}")
            # 降级到简单采样
            step = len(data) // max_points
            return data[::step][:max_points]
    
    async def _adaptive_sampling(
        self,
        data: List[Dict[str, Any]],
        max_points: int,
        chart_type: ChartType
    ) -> List[Dict[str, Any]]:
        """自适应采样"""
        try:
            if chart_type in [ChartType.LINE, ChartType.AREA]:
                # 对于时间序列数据，保留趋势变化点
                return await self._trend_aware_sampling(data, max_points)
            else:
                # 其他类型使用均匀采样
                step = len(data) / max_points
                indices = [int(i * step) for i in range(max_points)]
                return [data[i] for i in indices if i < len(data)]
                
        except Exception as e:
            logger.error(f"自适应采样失败: {str(e)}")
            step = len(data) // max_points
            return data[::step][:max_points]
    
    async def _trend_aware_sampling(
        self,
        data: List[Dict[str, Any]],
        max_points: int
    ) -> List[Dict[str, Any]]:
        """趋势感知采样"""
        try:
            if len(data) <= max_points:
                return data
            
            # 计算数据点的重要性（基于变化率）
            values = [item.get('value', 0) for item in data]
            importance_scores = [0] * len(values)
            
            # 计算变化率
            for i in range(1, len(values) - 1):
                prev_change = abs(values[i] - values[i-1])
                next_change = abs(values[i+1] - values[i])
                importance_scores[i] = prev_change + next_change
            
            # 始终包含首尾点
            selected_indices = {0, len(data) - 1}
            
            # 根据重要性选择其他点
            indexed_scores = [(i, score) for i, score in enumerate(importance_scores)]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
            
            for i, _ in indexed_scores:
                if len(selected_indices) >= max_points:
                    break
                selected_indices.add(i)
            
            # 按原始顺序返回
            selected_indices = sorted(selected_indices)
            return [data[i] for i in selected_indices]
            
        except Exception as e:
            logger.error(f"趋势感知采样失败: {str(e)}")
            step = len(data) // max_points
            return data[::step][:max_points]
    
    async def _importance_sampling(
        self,
        data: List[Dict[str, Any]],
        max_points: int,
        chart_type: ChartType
    ) -> List[Dict[str, Any]]:
        """重要性采样"""
        try:
            # 根据数据值的大小确定重要性
            if chart_type == ChartType.PIE:
                # 饼图保留值较大的部分
                sorted_data = sorted(data, key=lambda x: x.get('value', 0), reverse=True)
                return sorted_data[:max_points]
            else:
                # 其他图表类型使用均匀采样
                step = len(data) // max_points
                return data[::step][:max_points]
                
        except Exception as e:
            logger.error(f"重要性采样失败: {str(e)}")
            step = len(data) // max_points
            return data[::step][:max_points]
    
    async def _time_based_sampling(
        self,
        data: List[Dict[str, Any]],
        max_points: int
    ) -> List[Dict[str, Any]]:
        """基于时间的采样"""
        try:
            # 按时间间隔采样
            if not data:
                return data
            
            # 检查时间字段
            time_field = None
            for field in ['timestamp', 'date', 'time']:
                if field in data[0]:
                    time_field = field
                    break
            
            if not time_field:
                # 没有时间字段，使用均匀采样
                step = len(data) // max_points
                return data[::step][:max_points]
            
            # 按时间排序
            sorted_data = sorted(data, key=lambda x: x.get(time_field, 0))
            
            # 计算时间间隔
            total_time_span = sorted_data[-1][time_field] - sorted_data[0][time_field]
            time_interval = total_time_span / max_points
            
            # 按时间间隔选择数据点
            selected_data = []
            last_time = sorted_data[0][time_field] - time_interval
            
            for item in sorted_data:
                if item[time_field] - last_time >= time_interval:
                    selected_data.append(item)
                    last_time = item[time_field]
                    
                    if len(selected_data) >= max_points:
                        break
            
            return selected_data
            
        except Exception as e:
            logger.error(f"基于时间的采样失败: {str(e)}")
            step = len(data) // max_points
            return data[::step][:max_points]
    
    async def _aggregate_data(
        self,
        data: List[Dict[str, Any]],
        interval: str
    ) -> List[Dict[str, Any]]:
        """数据聚合"""
        try:
            # 简化实现：按时间间隔聚合数据
            # 实际实现中可以使用pandas进行更复杂的聚合
            
            if not data or len(data) < 2:
                return data
            
            # 检查是否有时间字段
            time_field = None
            for field in ['timestamp', 'date', 'time']:
                if field in data[0]:
                    time_field = field
                    break
            
            if not time_field:
                return data
            
            # 简单的时间窗口聚合
            aggregated_data = []
            current_window = []
            window_start = data[0][time_field]
            
            # 解析间隔（简化实现）
            interval_seconds = self._parse_interval(interval)
            
            for item in data:
                if item[time_field] - window_start < interval_seconds:
                    current_window.append(item)
                else:
                    # 聚合当前窗口
                    if current_window:
                        aggregated_item = self._aggregate_window(current_window, time_field)
                        aggregated_data.append(aggregated_item)
                    
                    # 开始新窗口
                    current_window = [item]
                    window_start = item[time_field]
            
            # 处理最后一个窗口
            if current_window:
                aggregated_item = self._aggregate_window(current_window, time_field)
                aggregated_data.append(aggregated_item)
            
            return aggregated_data
            
        except Exception as e:
            logger.error(f"数据聚合失败: {str(e)}")
            return data
    
    def _parse_interval(self, interval: str) -> int:
        """解析时间间隔"""
        try:
            if interval.endswith('s'):
                return int(interval[:-1])
            elif interval.endswith('m'):
                return int(interval[:-1]) * 60
            elif interval.endswith('h'):
                return int(interval[:-1]) * 3600
            elif interval.endswith('d'):
                return int(interval[:-1]) * 86400
            else:
                return 3600  # 默认1小时
        except:
            return 3600
    
    def _aggregate_window(self, window: List[Dict[str, Any]], time_field: str) -> Dict[str, Any]:
        """聚合时间窗口内的数据"""
        try:
            if not window:
                return {}
            
            # 计算平均值
            values = [item.get('value', 0) for item in window if 'value' in item]
            avg_value = sum(values) / len(values) if values else 0
            
            # 使用窗口中间时间
            times = [item[time_field] for item in window]
            mid_time = (min(times) + max(times)) / 2
            
            result = {
                time_field: mid_time,
                'value': avg_value,
                'count': len(window)
            }
            
            # 保留其他公共字段
            for key in window[0].keys():
                if key not in [time_field, 'value'] and all(key in item for item in window):
                    # 使用第一个值作为代表
                    result[key] = window[0][key]
            
            return result
            
        except Exception as e:
            logger.error(f"窗口聚合失败: {str(e)}")
            return window[0] if window else {}
    
    async def _compress_data(
        self, 
        data: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], float]:
        """数据压缩"""
        try:
            original_size = len(json.dumps(data).encode('utf-8'))
            
            # 简化数据结构
            compressed_data = []
            for item in data:
                compressed_item = {}
                for key, value in item.items():
                    # 保留重要字段，简化数值精度
                    if isinstance(value, float):
                        compressed_item[key] = round(value, 2)
                    elif isinstance(value, str) and len(value) > 100:
                        compressed_item[key] = value[:100] + "..."
                    else:
                        compressed_item[key] = value
                compressed_data.append(compressed_item)
            
            compressed_size = len(json.dumps(compressed_data).encode('utf-8'))
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
            
            return compressed_data, compression_ratio
            
        except Exception as e:
            logger.error(f"数据压缩失败: {str(e)}")
            return data, 1.0
    
    def _get_applied_optimizations(self, config: ChartPerformanceConfig) -> List[str]:
        """获取应用的优化策略"""
        optimizations = []
        
        if config.enable_caching:
            optimizations.append("caching")
        if config.enable_compression:
            optimizations.append("compression")
        if config.enable_pagination:
            optimizations.append("pagination")
        if config.enable_aggregation:
            optimizations.append("aggregation")
        
        optimizations.append(f"sampling_{config.sampling_strategy.value}")
        
        return optimizations
    
    def _generate_cache_key(self, chart_id: str, data: List[Dict[str, Any]]) -> str:
        """生成缓存键"""
        import hashlib
        
        # 基于图表ID和数据哈希生成缓存键
        data_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
        return f"chart_optimized:{chart_id}:{data_hash}"
    
    async def _get_cached_data(
        self, 
        chart_id: str, 
        data: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """获取缓存数据"""
        try:
            cache_key = self._generate_cache_key(chart_id, data)
            cached_result = await self.cache_client.aget("chart_optimized", cache_key=cache_key)
            return cached_result
        except Exception as e:
            logger.error(f"获取缓存数据失败: {str(e)}")
            return None
    
    async def _cache_data(
        self,
        chart_id: str,
        original_data: List[Dict[str, Any]],
        result: Dict[str, Any],
        ttl: int
    ):
        """缓存数据"""
        try:
            cache_key = self._generate_cache_key(chart_id, original_data)
            await self.cache_client.aset("chart_optimized", result, ttl, cache_key=cache_key)
        except Exception as e:
            logger.error(f"缓存数据失败: {str(e)}")
    
    async def _record_metrics(
        self,
        chart_id: str,
        chart_type: ChartType,
        original_count: int,
        processed_count: int,
        processing_time: float,
        compression_ratio: float,
        cache_hit: bool
    ):
        """记录性能指标"""
        try:
            metrics = ChartMetrics(
                chart_id=chart_id,
                chart_type=chart_type,
                data_points=processed_count,
                processing_time=processing_time,
                memory_usage=0.0,  # 需要实际测量
                cache_hit=cache_hit,
                compression_ratio=compression_ratio,
                render_time=0.0,  # 前端测量
                timestamp=datetime.now()
            )
            
            if chart_id not in self.metrics_history:
                self.metrics_history[chart_id] = []
            
            self.metrics_history[chart_id].append(metrics)
            
            # 保持历史记录在合理范围内
            if len(self.metrics_history[chart_id]) > 100:
                self.metrics_history[chart_id] = self.metrics_history[chart_id][-100:]
                
        except Exception as e:
            logger.error(f"记录性能指标失败: {str(e)}")


# 服务实例创建函数
async def get_chart_performance_service(db: AsyncSession = None) -> ChartPerformanceService:
    """获取图表性能服务实例"""
    if db is None:
        async with get_async_session_ctx() as session:
            return ChartPerformanceService(session)
    return ChartPerformanceService(db)