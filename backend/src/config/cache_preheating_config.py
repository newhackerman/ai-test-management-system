"""
缓存预热配置

本模块定义缓存预热机制的配置参数，包括：
1. 预热策略配置
2. 调度时间配置
3. 性能参数配置
4. 监控阈值配置

配置说明：
- 所有时间单位为秒，除非特别说明
- 频率阈值表示每小时访问次数
- 优先级影响任务执行顺序
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class PreheatingMode(Enum):
    """预热模式"""
    CONSERVATIVE = "conservative"  # 保守模式：较少预热，节省资源
    BALANCED = "balanced"         # 平衡模式：适中预热，平衡性能和资源
    AGGRESSIVE = "aggressive"     # 激进模式：大量预热，最大化性能


@dataclass
class PreheatingConfig:
    """预热配置类"""
    
    # 基础配置
    enabled: bool = True
    mode: PreheatingMode = PreheatingMode.BALANCED
    max_concurrent_tasks: int = 5
    task_timeout: int = 300  # 5分钟
    
    # 调度配置
    startup_delay: int = 30  # 启动后延迟30秒开始预热
    analysis_interval: int = 3600  # 每小时分析一次访问模式
    preheating_interval: int = 1800  # 每30分钟执行一次预热
    
    # 访问模式分析配置
    analysis_window_hours: int = 168  # 分析7天内的访问模式
    hot_data_threshold: int = 10  # 每小时访问10次以上为热点数据
    active_user_threshold: int = 5  # 每天访问5次以上为活跃用户
    
    # 缓存配置
    cache_ttl_short: int = 1800   # 30分钟
    cache_ttl_medium: int = 3600  # 1小时
    cache_ttl_long: int = 7200    # 2小时
    
    # 性能监控配置
    performance_check_interval: int = 300  # 每5分钟检查一次性能
    cache_hit_rate_threshold: float = 0.7  # 缓存命中率阈值70%
    response_time_threshold: float = 1.0   # 响应时间阈值1秒
    
    # 资源限制配置
    max_memory_usage_mb: int = 512  # 最大内存使用512MB
    max_task_history: int = 1000    # 最多保留1000条任务历史
    max_pattern_history: int = 5000 # 最多保留5000个访问模式


# 预设配置模板
PREHEATING_CONFIGS = {
    PreheatingMode.CONSERVATIVE: PreheatingConfig(
        mode=PreheatingMode.CONSERVATIVE,
        max_concurrent_tasks=2,
        preheating_interval=7200,  # 2小时
        hot_data_threshold=20,     # 更高的阈值
        cache_ttl_short=900,       # 15分钟
        cache_ttl_medium=1800,     # 30分钟
        cache_ttl_long=3600,       # 1小时
    ),
    
    PreheatingMode.BALANCED: PreheatingConfig(
        mode=PreheatingMode.BALANCED,
        max_concurrent_tasks=5,
        preheating_interval=1800,  # 30分钟
        hot_data_threshold=10,     # 中等阈值
        cache_ttl_short=1800,      # 30分钟
        cache_ttl_medium=3600,     # 1小时
        cache_ttl_long=7200,       # 2小时
    ),
    
    PreheatingMode.AGGRESSIVE: PreheatingConfig(
        mode=PreheatingMode.AGGRESSIVE,
        max_concurrent_tasks=10,
        preheating_interval=900,   # 15分钟
        hot_data_threshold=5,      # 更低的阈值
        cache_ttl_short=3600,      # 1小时
        cache_ttl_medium=7200,     # 2小时
        cache_ttl_long=14400,      # 4小时
    )
}


# 预热策略配置
PREHEATING_STRATEGIES = {
    "startup": {
        "enabled": True,
        "delay_seconds": 30,
        "tasks": [
            {
                "name": "ai_model_configs",
                "priority": "high",
                "cache_ttl": 7200,  # 2小时
                "description": "预热AI模型配置数据"
            },
            {
                "name": "system_stats",
                "priority": "medium",
                "cache_ttl": 3600,  # 1小时
                "description": "预热系统统计数据"
            },
            {
                "name": "popular_templates",
                "priority": "medium",
                "cache_ttl": 3600,  # 1小时
                "description": "预热热门模板数据"
            }
        ]
    },
    
    "hourly": {
        "enabled": True,
        "tasks": [
            {
                "name": "active_user_sessions",
                "priority": "high",
                "cache_ttl": 1800,  # 30分钟
                "description": "预热活跃用户会话数据"
            },
            {
                "name": "recent_suggestions",
                "priority": "medium",
                "cache_ttl": 1800,  # 30分钟
                "description": "预热最近建议数据"
            }
        ]
    },
    
    "daily": {
        "enabled": True,
        "time": "02:00",  # 凌晨2点执行
        "tasks": [
            {
                "name": "user_pattern_analysis",
                "priority": "low",
                "description": "分析用户访问模式"
            },
            {
                "name": "cache_optimization",
                "priority": "low",
                "description": "优化缓存策略"
            },
            {
                "name": "performance_reports",
                "priority": "low",
                "description": "生成性能报告"
            }
        ]
    },
    
    "peak_hours": {
        "enabled": True,
        "hours": [9, 14, 20],  # 上午9点、下午2点、晚上8点
        "advance_minutes": 30,  # 提前30分钟预热
        "tasks": [
            {
                "name": "popular_data",
                "priority": "high",
                "cache_ttl": 1800,  # 30分钟
                "description": "预热热门数据"
            },
            {
                "name": "active_user_data",
                "priority": "high",
                "cache_ttl": 1800,  # 30分钟
                "description": "预热活跃用户数据"
            }
        ]
    }
}


# 数据源配置
DATA_SOURCE_CONFIGS = {
    "ai_chat_sessions": {
        "cache_key_pattern": "ai_sessions:user_{user_id}",
        "default_limit": 20,
        "cache_ttl": 1800,  # 30分钟
        "priority_weight": 1.0,
        "description": "AI聊天会话数据"
    },
    
    "ai_chat_messages": {
        "cache_key_pattern": "ai_messages:session_{session_id}",
        "default_limit": 50,
        "cache_ttl": 1800,  # 30分钟
        "priority_weight": 0.8,
        "description": "AI聊天消息数据"
    },
    
    "ai_suggestions": {
        "cache_key_pattern": "ai_suggestions:project_{project_id}",
        "default_limit": 30,
        "cache_ttl": 3600,  # 1小时
        "priority_weight": 0.9,
        "description": "AI建议数据"
    },
    
    "ai_model_configs": {
        "cache_key_pattern": "ai_models:available",
        "cache_ttl": 7200,  # 2小时
        "priority_weight": 1.2,
        "description": "AI模型配置数据"
    },
    
    "user_preferences": {
        "cache_key_pattern": "user_prefs:{user_id}",
        "cache_ttl": 3600,  # 1小时
        "priority_weight": 0.6,
        "description": "用户偏好设置"
    },
    
    "prompt_templates": {
        "cache_key_pattern": "templates:popular",
        "default_limit": 20,
        "cache_ttl": 3600,  # 1小时
        "priority_weight": 0.7,
        "description": "提示词模板数据"
    }
}


# 监控配置
MONITORING_CONFIG = {
    "metrics": {
        "cache_hit_rate": {
            "threshold_warning": 0.7,   # 70%以下警告
            "threshold_critical": 0.5,  # 50%以下严重
            "check_interval": 300       # 5分钟检查一次
        },
        
        "response_time": {
            "threshold_warning": 1.0,   # 1秒以上警告
            "threshold_critical": 3.0,  # 3秒以上严重
            "check_interval": 300       # 5分钟检查一次
        },
        
        "task_success_rate": {
            "threshold_warning": 0.8,   # 80%以下警告
            "threshold_critical": 0.6,  # 60%以下严重
            "check_interval": 600       # 10分钟检查一次
        },
        
        "memory_usage": {
            "threshold_warning": 0.8,   # 80%以上警告
            "threshold_critical": 0.9,  # 90%以上严重
            "check_interval": 300       # 5分钟检查一次
        }
    },
    
    "alerts": {
        "enabled": True,
        "channels": ["log", "redis"],  # 支持的告警渠道
        "rate_limit": 300,  # 同类告警间隔5分钟
        "severity_levels": ["info", "warning", "error", "critical"]
    }
}


def get_preheating_config(mode: PreheatingMode = PreheatingMode.BALANCED) -> PreheatingConfig:
    """获取预热配置"""
    return PREHEATING_CONFIGS.get(mode, PREHEATING_CONFIGS[PreheatingMode.BALANCED])


def get_strategy_config(strategy_name: str) -> Dict[str, Any]:
    """获取策略配置"""
    return PREHEATING_STRATEGIES.get(strategy_name, {})


def get_data_source_config(data_source: str) -> Dict[str, Any]:
    """获取数据源配置"""
    return DATA_SOURCE_CONFIGS.get(data_source, {})


def validate_config(config: PreheatingConfig) -> List[str]:
    """验证配置参数"""
    errors = []
    
    if config.max_concurrent_tasks < 1:
        errors.append("max_concurrent_tasks必须大于0")
    
    if config.max_concurrent_tasks > 20:
        errors.append("max_concurrent_tasks不应超过20")
    
    if config.preheating_interval < 300:
        errors.append("preheating_interval不应小于300秒")
    
    if config.hot_data_threshold < 1:
        errors.append("hot_data_threshold必须大于0")
    
    if config.cache_hit_rate_threshold < 0 or config.cache_hit_rate_threshold > 1:
        errors.append("cache_hit_rate_threshold必须在0-1之间")
    
    if config.max_memory_usage_mb < 100:
        errors.append("max_memory_usage_mb不应小于100MB")
    
    return errors


# 默认配置实例
DEFAULT_CONFIG = get_preheating_config(PreheatingMode.BALANCED)