"""
Redis缓存配置

实现仪表板模块的缓存键命名规范和TTL策略
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
import json
import hashlib
from datetime import timedelta

class CacheNamespace(Enum):
    """缓存命名空间枚举"""
    DASHBOARD = "dashboard"
    WIDGET = "widget"
    USER_PREF = "user_pref"
    PROJECT_DATA = "project_data"
    METRICS = "metrics"
    REALTIME = "realtime"
    SESSION = "session"
    TEMP = "temp"

class CacheTTL(Enum):
    """缓存TTL策略枚举"""
    VERY_SHORT = 30      # 30秒 - 实时数据
    SHORT = 300          # 5分钟 - 频繁更新数据
    MEDIUM = 1800        # 30分钟 - 一般数据
    LONG = 3600          # 1小时 - 相对稳定数据
    VERY_LONG = 86400    # 24小时 - 静态数据
    PERMANENT = -1       # 永久 - 配置数据

@dataclass
class CacheKeyConfig:
    """缓存键配置"""
    namespace: CacheNamespace
    ttl: CacheTTL
    description: str
    pattern: str
    compression: bool = False
    serialization: str = "json"  # json, pickle, msgpack

class DashboardCacheConfig:
    """仪表板缓存配置管理"""
    
    # 缓存键配置映射
    CACHE_CONFIGS: Dict[str, CacheKeyConfig] = {
        # 仪表板配置缓存
        "dashboard_config": CacheKeyConfig(
            namespace=CacheNamespace.DASHBOARD,
            ttl=CacheTTL.LONG,
            description="用户仪表板配置",
            pattern="dashboard:config:user:{user_id}:role:{role_type}",
            compression=True
        ),
        
        "dashboard_layout": CacheKeyConfig(
            namespace=CacheNamespace.DASHBOARD,
            ttl=CacheTTL.MEDIUM,
            description="仪表板布局配置",
            pattern="dashboard:layout:user:{user_id}:role:{role_type}",
            compression=True
        ),
        
        # 组件数据缓存
        "widget_data": CacheKeyConfig(
            namespace=CacheNamespace.WIDGET,
            ttl=CacheTTL.SHORT,
            description="组件数据",
            pattern="widget:data:{widget_type}:project:{project_id}:user:{user_id}",
            compression=True
        ),
        
        "widget_config": CacheKeyConfig(
            namespace=CacheNamespace.WIDGET,
            ttl=CacheTTL.LONG,
            description="组件配置",
            pattern="widget:config:{widget_type}",
            compression=False
        ),
        
        # 项目数据缓存
        "project_overview": CacheKeyConfig(
            namespace=CacheNamespace.PROJECT_DATA,
            ttl=CacheTTL.SHORT,
            description="项目概览数据",
            pattern="project:overview:user:{user_id}:role:{role_type}",
            compression=True
        ),
        
        "project_metrics": CacheKeyConfig(
            namespace=CacheNamespace.PROJECT_DATA,
            ttl=CacheTTL.MEDIUM,
            description="项目指标数据",
            pattern="project:metrics:{project_id}:type:{metric_type}",
            compression=True
        ),
        
        # 指标数据缓存
        "requirement_metrics": CacheKeyConfig(
            namespace=CacheNamespace.METRICS,
            ttl=CacheTTL.SHORT,
            description="需求指标数据",
            pattern="metrics:requirements:project:{project_id}:range:{time_range}",
            compression=True
        ),
        
        "test_metrics": CacheKeyConfig(
            namespace=CacheNamespace.METRICS,
            ttl=CacheTTL.SHORT,
            description="测试指标数据",
            pattern="metrics:tests:project:{project_id}:range:{time_range}",
            compression=True
        ),
        
        "system_metrics": CacheKeyConfig(
            namespace=CacheNamespace.METRICS,
            ttl=CacheTTL.VERY_SHORT,
            description="系统指标数据",
            pattern="metrics:system:type:{metric_type}",
            compression=False
        ),
        
        # 实时数据缓存
        "realtime_data": CacheKeyConfig(
            namespace=CacheNamespace.REALTIME,
            ttl=CacheTTL.VERY_SHORT,
            description="实时数据",
            pattern="realtime:data:{data_type}:target:{target_id}",
            compression=False
        ),
        
        "websocket_session": CacheKeyConfig(
            namespace=CacheNamespace.REALTIME,
            ttl=CacheTTL.MEDIUM,
            description="WebSocket会话",
            pattern="realtime:session:{connection_id}",
            compression=False
        ),
        
        # 用户偏好缓存
        "user_preferences": CacheKeyConfig(
            namespace=CacheNamespace.USER_PREF,
            ttl=CacheTTL.LONG,
            description="用户偏好设置",
            pattern="user:pref:{user_id}:type:{pref_type}",
            compression=True
        ),
        
        "color_scheme": CacheKeyConfig(
            namespace=CacheNamespace.USER_PREF,
            ttl=CacheTTL.VERY_LONG,
            description="配色方案",
            pattern="user:color_scheme:{user_id}",
            compression=False
        ),
        
        # 会话数据缓存
        "user_session": CacheKeyConfig(
            namespace=CacheNamespace.SESSION,
            ttl=CacheTTL.MEDIUM,
            description="用户会话数据",
            pattern="session:user:{user_id}:token:{token_hash}",
            compression=False
        ),
        
        # 临时数据缓存
        "temp_data": CacheKeyConfig(
            namespace=CacheNamespace.TEMP,
            ttl=CacheTTL.SHORT,
            description="临时数据",
            pattern="temp:data:{data_type}:id:{data_id}",
            compression=True
        ),
        
        "api_response": CacheKeyConfig(
            namespace=CacheNamespace.TEMP,
            ttl=CacheTTL.SHORT,
            description="API响应缓存",
            pattern="temp:api:{endpoint_hash}:params:{params_hash}",
            compression=True
        )
    }
    
    @classmethod
    def get_cache_key(
        cls, 
        key_type: str, 
        **kwargs
    ) -> str:
        """生成缓存键"""
        if key_type not in cls.CACHE_CONFIGS:
            raise ValueError(f"Unknown cache key type: {key_type}")
        
        config = cls.CACHE_CONFIGS[key_type]
        
        try:
            # 格式化缓存键模式
            cache_key = config.pattern.format(**kwargs)
            
            # 添加命名空间前缀
            full_key = f"{config.namespace.value}:{cache_key}"
            
            # 如果键太长，使用哈希
            if len(full_key) > 250:
                key_hash = hashlib.md5(full_key.encode()).hexdigest()
                full_key = f"{config.namespace.value}:hash:{key_hash}"
            
            return full_key
            
        except KeyError as e:
            raise ValueError(f"Missing required parameter for cache key '{key_type}': {e}")
    
    @classmethod
    def get_ttl(cls, key_type: str) -> int:
        """获取缓存TTL"""
        if key_type not in cls.CACHE_CONFIGS:
            return CacheTTL.MEDIUM.value
        
        config = cls.CACHE_CONFIGS[key_type]
        return config.ttl.value
    
    @classmethod
    def should_compress(cls, key_type: str) -> bool:
        """检查是否需要压缩"""
        if key_type not in cls.CACHE_CONFIGS:
            return False
        
        config = cls.CACHE_CONFIGS[key_type]
        return config.compression
    
    @classmethod
    def get_all_patterns(cls) -> Dict[str, str]:
        """获取所有缓存键模式"""
        return {
            key_type: config.pattern 
            for key_type, config in cls.CACHE_CONFIGS.items()
        }
    
    @classmethod
    def get_namespace_keys(cls, namespace: CacheNamespace) -> List[str]:
        """获取指定命名空间的所有键类型"""
        return [
            key_type for key_type, config in cls.CACHE_CONFIGS.items()
            if config.namespace == namespace
        ]

class CacheStrategy:
    """缓存策略配置"""
    
    # 缓存策略配置
    STRATEGIES = {
        # 写入策略
        "write_through": {
            "description": "写入时同时更新缓存和数据库",
            "use_cases": ["用户配置", "重要数据"]
        },
        
        "write_behind": {
            "description": "先写入缓存，异步写入数据库",
            "use_cases": ["高频写入数据", "日志数据"]
        },
        
        "write_around": {
            "description": "直接写入数据库，不更新缓存",
            "use_cases": ["一次性数据", "大数据写入"]
        },
        
        # 读取策略
        "cache_aside": {
            "description": "应用程序管理缓存",
            "use_cases": ["一般数据读取"]
        },
        
        "read_through": {
            "description": "缓存层自动加载数据",
            "use_cases": ["透明缓存"]
        },
        
        # 失效策略
        "ttl_based": {
            "description": "基于TTL的自动失效",
            "use_cases": ["时效性数据"]
        },
        
        "event_based": {
            "description": "基于事件的主动失效",
            "use_cases": ["强一致性数据"]
        },
        
        "lru_eviction": {
            "description": "LRU淘汰策略",
            "use_cases": ["内存限制场景"]
        }
    }
    
    # 数据类型与策略映射
    TYPE_STRATEGY_MAPPING = {
        "dashboard_config": {
            "write": "write_through",
            "read": "cache_aside",
            "eviction": "ttl_based"
        },
        
        "widget_data": {
            "write": "write_behind",
            "read": "cache_aside",
            "eviction": "ttl_based"
        },
        
        "realtime_data": {
            "write": "write_around",
            "read": "read_through",
            "eviction": "ttl_based"
        },
        
        "user_session": {
            "write": "write_through",
            "read": "cache_aside",
            "eviction": "ttl_based"
        },
        
        "metrics": {
            "write": "write_behind",
            "read": "cache_aside",
            "eviction": "event_based"
        }
    }
    
    @classmethod
    def get_strategy(cls, data_type: str, operation: str) -> str:
        """获取数据类型的缓存策略"""
        if data_type in cls.TYPE_STRATEGY_MAPPING:
            return cls.TYPE_STRATEGY_MAPPING[data_type].get(operation, "cache_aside")
        
        return "cache_aside"

class CacheMonitoring:
    """缓存监控配置"""
    
    # 监控指标配置
    METRICS = {
        "hit_rate": {
            "description": "缓存命中率",
            "threshold": 80,  # 低于80%告警
            "unit": "percentage"
        },
        
        "miss_rate": {
            "description": "缓存未命中率",
            "threshold": 20,  # 高于20%告警
            "unit": "percentage"
        },
        
        "response_time": {
            "description": "缓存响应时间",
            "threshold": 10,  # 高于10ms告警
            "unit": "milliseconds"
        },
        
        "memory_usage": {
            "description": "内存使用率",
            "threshold": 85,  # 高于85%告警
            "unit": "percentage"
        },
        
        "connection_count": {
            "description": "连接数",
            "threshold": 1000,  # 高于1000告警
            "unit": "count"
        },
        
        "eviction_rate": {
            "description": "淘汰率",
            "threshold": 5,  # 高于5%告警
            "unit": "percentage"
        }
    }
    
    # 告警配置
    ALERTS = {
        "low_hit_rate": {
            "condition": "hit_rate < 80",
            "severity": "warning",
            "message": "缓存命中率过低，可能影响性能"
        },
        
        "high_memory_usage": {
            "condition": "memory_usage > 85",
            "severity": "critical",
            "message": "缓存内存使用率过高，可能导致OOM"
        },
        
        "slow_response": {
            "condition": "response_time > 10",
            "severity": "warning",
            "message": "缓存响应时间过长"
        },
        
        "high_eviction": {
            "condition": "eviction_rate > 5",
            "severity": "warning",
            "message": "缓存淘汰率过高，建议增加内存"
        }
    }
    
    @classmethod
    def get_metric_threshold(cls, metric_name: str) -> Optional[float]:
        """获取指标阈值"""
        if metric_name in cls.METRICS:
            return cls.METRICS[metric_name]["threshold"]
        return None
    
    @classmethod
    def check_alert_condition(cls, metric_name: str, value: float) -> Optional[Dict[str, Any]]:
        """检查告警条件"""
        threshold = cls.get_metric_threshold(metric_name)
        if threshold is None:
            return None
        
        # 根据指标类型检查条件
        if metric_name in ["hit_rate"]:
            if value < threshold:
                return cls.ALERTS.get("low_hit_rate")
        elif metric_name in ["memory_usage"]:
            if value > threshold:
                return cls.ALERTS.get("high_memory_usage")
        elif metric_name in ["response_time"]:
            if value > threshold:
                return cls.ALERTS.get("slow_response")
        elif metric_name in ["eviction_rate"]:
            if value > threshold:
                return cls.ALERTS.get("high_eviction")
        
        return None

# 缓存配置实例
cache_config = DashboardCacheConfig()
cache_strategy = CacheStrategy()
cache_monitoring = CacheMonitoring()