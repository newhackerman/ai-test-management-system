"""
缓存预热服务

本模块实现智能缓存预热机制，包括：
1. 热点数据识别和预加载
2. 用户行为分析和预测
3. 定时缓存刷新
4. 缓存预热策略管理
5. 预热效果监控

主要功能：
- 分析用户访问模式
- 预测热点数据
- 自动预热缓存
- 监控预热效果
- 优化预热策略
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from ..core.database import AsyncSessionLocal
from ..core.config import get_settings
from ..utils.redis_client import RedisCache, get_redis_client
from ..services.database_optimization_service import get_database_optimization_service

logger = logging.getLogger(__name__)
settings = get_settings()


class PreheatingStrategy(Enum):
    """预热策略枚举"""
    FREQUENCY_BASED = "frequency_based"  # 基于访问频率
    TIME_BASED = "time_based"  # 基于时间模式
    USER_BEHAVIOR = "user_behavior"  # 基于用户行为
    PREDICTIVE = "predictive"  # 预测性预热
    MANUAL = "manual"  # 手动预热


class PreheatingPriority(Enum):
    """预热优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PreheatingTask:
    """预热任务"""
    task_id: str
    strategy: PreheatingStrategy
    priority: PreheatingPriority
    cache_key: str
    data_source: str
    parameters: Dict[str, Any]
    estimated_time: float
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class AccessPattern:
    """访问模式"""
    resource_type: str
    resource_id: str
    access_count: int
    last_access: datetime
    access_frequency: float  # 每小时访问次数
    peak_hours: List[int]  # 高峰时段
    user_count: int  # 访问用户数
    avg_response_time: float


class CachePreheatingService:
    """缓存预热服务"""
    
    def __init__(self):
        self.cache = RedisCache("preheating")
        self.stats_cache = RedisCache("preheating_stats")
        self.redis_client = None
        
        # 预热配置
        self.preheating_enabled = True
        self.max_concurrent_tasks = 5
        self.preheating_interval = 3600  # 1小时
        self.analysis_window = 24 * 7  # 7天
        
        # 预热任务队列
        self.task_queue = asyncio.Queue()
        self.running_tasks = set()
        self.completed_tasks = []
        self.max_completed_history = 1000
        
        # 访问模式分析
        self.access_patterns = {}
        self.hot_data_threshold = 10  # 每小时访问10次以上为热点数据
        
        # 预热统计
        self.stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "cache_hit_improvement": 0.0,
            "response_time_improvement": 0.0
        }
    
    async def initialize(self):
        """初始化预热服务"""
        try:
            self.redis_client = await get_redis_client()
            
            # 加载历史统计数据
            await self._load_statistics()
            
            # 加载访问模式
            await self._load_access_patterns()
            
            logger.info("缓存预热服务初始化成功")
            
        except Exception as e:
            logger.error(f"缓存预热服务初始化失败: {e}")
            raise    

    async def start_preheating_worker(self):
        """启动预热工作进程"""
        if not self.preheating_enabled:
            logger.info("缓存预热已禁用")
            return
        
        logger.info("启动缓存预热工作进程")
        
        # 启动任务处理器
        asyncio.create_task(self._task_processor())
        
        # 启动定时分析器
        asyncio.create_task(self._periodic_analyzer())
        
        # 启动预热调度器
        asyncio.create_task(self._preheating_scheduler())
    
    async def _task_processor(self):
        """任务处理器"""
        while self.preheating_enabled:
            try:
                # 控制并发任务数量
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(1)
                    continue
                
                # 获取任务
                try:
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                
                # 执行任务
                asyncio.create_task(self._execute_preheating_task(task))
                
            except Exception as e:
                logger.error(f"任务处理器异常: {e}")
                await asyncio.sleep(5)
    
    async def _execute_preheating_task(self, task: PreheatingTask):
        """执行预热任务"""
        self.running_tasks.add(task.task_id)
        start_time = time.time()
        
        try:
            logger.info(f"开始执行预热任务: {task.task_id}")
            
            # 根据数据源类型执行预热
            if task.data_source == "ai_chat_sessions":
                await self._preheat_ai_sessions(task)
            elif task.data_source == "ai_chat_messages":
                await self._preheat_ai_messages(task)
            elif task.data_source == "ai_suggestions":
                await self._preheat_ai_suggestions(task)
            elif task.data_source == "ai_model_configs":
                await self._preheat_ai_models(task)
            elif task.data_source == "user_preferences":
                await self._preheat_user_preferences(task)
            else:
                raise ValueError(f"不支持的数据源: {task.data_source}")
            
            # 标记任务完成
            task.completed_at = datetime.utcnow()
            task.success = True
            
            execution_time = time.time() - start_time
            logger.info(f"预热任务完成: {task.task_id} (耗时: {execution_time:.2f}s)")
            
            # 更新统计
            self.stats["successful_tasks"] += 1
            
        except Exception as e:
            task.error_message = str(e)
            task.success = False
            self.stats["failed_tasks"] += 1
            
            logger.error(f"预热任务失败: {task.task_id} - {e}")
            
        finally:
            self.running_tasks.discard(task.task_id)
            self.completed_tasks.append(task)
            
            # 限制历史记录数量
            if len(self.completed_tasks) > self.max_completed_history:
                self.completed_tasks.pop(0)
            
            self.stats["total_tasks"] += 1
    
    async def _preheat_ai_sessions(self, task: PreheatingTask):
        """预热AI会话数据"""
        params = task.parameters
        user_id = params.get("user_id")
        limit = params.get("limit", 20)
        
        if not user_id:
            raise ValueError("缺少用户ID参数")
        
        # 获取优化服务
        optimization_service = await get_database_optimization_service()
        
        # 执行查询并缓存
        sessions = await optimization_service.get_ai_chat_sessions_optimized(
            user_id=user_id,
            limit=limit
        )
        
        logger.debug(f"预热AI会话数据: 用户{user_id}, {len(sessions)}条记录")
    
    async def _preheat_ai_messages(self, task: PreheatingTask):
        """预热AI消息数据"""
        params = task.parameters
        session_id = params.get("session_id")
        limit = params.get("limit", 50)
        
        if not session_id:
            raise ValueError("缺少会话ID参数")
        
        # 获取优化服务
        optimization_service = await get_database_optimization_service()
        
        # 执行查询并缓存
        messages = await optimization_service.get_ai_chat_messages_optimized(
            session_id=session_id,
            limit=limit
        )
        
        logger.debug(f"预热AI消息数据: 会话{session_id}, {len(messages)}条记录")
    
    async def _preheat_ai_suggestions(self, task: PreheatingTask):
        """预热AI建议数据"""
        params = task.parameters
        user_id = params.get("user_id")
        project_id = params.get("project_id")
        
        if not user_id:
            raise ValueError("缺少用户ID参数")
        
        # 获取优化服务
        optimization_service = await get_database_optimization_service()
        
        # 执行查询并缓存
        suggestions = await optimization_service.get_ai_suggestions_optimized(
            user_id=user_id,
            project_id=project_id
        )
        
        logger.debug(f"预热AI建议数据: 用户{user_id}, {len(suggestions)}条记录")
    
    async def _preheat_ai_models(self, task: PreheatingTask):
        """预热AI模型配置数据"""
        cache_key = "ai_models:available"
        
        async with AsyncSessionLocal() as session:
            from ..models.ai_model_config import AIModelConfig
            
            # 查询可用模型
            result = await session.execute(
                select(AIModelConfig)
                .where(
                    and_(
                        AIModelConfig.is_enabled == True,
                        AIModelConfig.is_public == True
                    )
                )
                .order_by(AIModelConfig.priority.desc())
            )
            models = result.scalars().all()
            
            # 缓存模型数据
            model_data = [model.to_dict() for model in models]
            await self.cache.set(cache_key, model_data, 3600)
            
            logger.debug(f"预热AI模型数据: {len(models)}个模型")
    
    async def _preheat_user_preferences(self, task: PreheatingTask):
        """预热用户偏好数据"""
        params = task.parameters
        user_id = params.get("user_id")
        
        if not user_id:
            raise ValueError("缺少用户ID参数")
        
        cache_key = f"user_preferences:{user_id}"
        
        # 模拟用户偏好数据（实际应从数据库查询）
        preferences = {
            "default_ai_model": "gpt-4",
            "language": "zh-CN",
            "theme": "dark",
            "auto_save": True,
            "notification_enabled": True
        }
        
        await self.cache.set(cache_key, preferences, 1800)
        logger.debug(f"预热用户偏好数据: 用户{user_id}")
    
    async def analyze_access_patterns(self):
        """分析访问模式"""
        try:
            logger.info("开始分析访问模式")
            
            # 分析时间窗口
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=self.analysis_window)
            
            # 分析AI会话访问模式
            await self._analyze_session_patterns(start_time, end_time)
            
            # 分析AI消息访问模式
            await self._analyze_message_patterns(start_time, end_time)
            
            # 分析AI建议访问模式
            await self._analyze_suggestion_patterns(start_time, end_time)
            
            # 保存访问模式
            await self._save_access_patterns()
            
            logger.info("访问模式分析完成")
            
        except Exception as e:
            logger.error(f"访问模式分析失败: {e}")
    
    async def _analyze_session_patterns(self, start_time: datetime, end_time: datetime):
        """分析会话访问模式"""
        # 这里应该分析实际的访问日志
        # 为了演示，我们模拟一些访问模式
        
        patterns = [
            AccessPattern(
                resource_type="ai_chat_sessions",
                resource_id="user_123",
                access_count=150,
                last_access=datetime.utcnow(),
                access_frequency=6.25,  # 每小时6.25次
                peak_hours=[9, 10, 14, 15, 16],
                user_count=1,
                avg_response_time=0.25
            ),
            AccessPattern(
                resource_type="ai_chat_sessions",
                resource_id="user_456",
                access_count=89,
                last_access=datetime.utcnow() - timedelta(minutes=30),
                access_frequency=3.7,
                peak_hours=[8, 9, 13, 14],
                user_count=1,
                avg_response_time=0.18
            )
        ]
        
        for pattern in patterns:
            key = f"{pattern.resource_type}:{pattern.resource_id}"
            self.access_patterns[key] = pattern
    
    async def _analyze_message_patterns(self, start_time: datetime, end_time: datetime):
        """分析消息访问模式"""
        # 模拟消息访问模式
        patterns = [
            AccessPattern(
                resource_type="ai_chat_messages",
                resource_id="session_789",
                access_count=45,
                last_access=datetime.utcnow(),
                access_frequency=1.9,
                peak_hours=[10, 11, 15, 16],
                user_count=1,
                avg_response_time=0.12
            )
        ]
        
        for pattern in patterns:
            key = f"{pattern.resource_type}:{pattern.resource_id}"
            self.access_patterns[key] = pattern
    
    async def _analyze_suggestion_patterns(self, start_time: datetime, end_time: datetime):
        """分析建议访问模式"""
        # 模拟建议访问模式
        patterns = [
            AccessPattern(
                resource_type="ai_suggestions",
                resource_id="user_123_project_1",
                access_count=28,
                last_access=datetime.utcnow(),
                access_frequency=1.2,
                peak_hours=[9, 10, 14],
                user_count=1,
                avg_response_time=0.35
            )
        ]
        
        for pattern in patterns:
            key = f"{pattern.resource_type}:{pattern.resource_id}"
            self.access_patterns[key] = pattern 
   
    async def generate_preheating_tasks(self) -> List[PreheatingTask]:
        """生成预热任务"""
        tasks = []
        
        try:
            # 基于访问频率生成任务
            frequency_tasks = await self._generate_frequency_based_tasks()
            tasks.extend(frequency_tasks)
            
            # 基于时间模式生成任务
            time_tasks = await self._generate_time_based_tasks()
            tasks.extend(time_tasks)
            
            # 基于用户行为生成任务
            behavior_tasks = await self._generate_behavior_based_tasks()
            tasks.extend(behavior_tasks)
            
            # 预测性任务
            predictive_tasks = await self._generate_predictive_tasks()
            tasks.extend(predictive_tasks)
            
            logger.info(f"生成预热任务: {len(tasks)}个")
            
        except Exception as e:
            logger.error(f"生成预热任务失败: {e}")
        
        return tasks
    
    async def _generate_frequency_based_tasks(self) -> List[PreheatingTask]:
        """基于访问频率生成任务"""
        tasks = []
        
        for key, pattern in self.access_patterns.items():
            # 只为高频访问的资源生成预热任务
            if pattern.access_frequency >= self.hot_data_threshold:
                task_id = f"freq_{pattern.resource_type}_{pattern.resource_id}_{int(time.time())}"
                
                # 根据资源类型生成不同的任务参数
                if pattern.resource_type == "ai_chat_sessions":
                    user_id = pattern.resource_id.split("_")[-1]
                    parameters = {"user_id": int(user_id), "limit": 20}
                elif pattern.resource_type == "ai_chat_messages":
                    session_id = pattern.resource_id.split("_")[-1]
                    parameters = {"session_id": int(session_id), "limit": 50}
                elif pattern.resource_type == "ai_suggestions":
                    parts = pattern.resource_id.split("_")
                    user_id = parts[1]
                    project_id = parts[3] if len(parts) > 3 else None
                    parameters = {"user_id": int(user_id)}
                    if project_id:
                        parameters["project_id"] = int(project_id)
                else:
                    continue
                
                task = PreheatingTask(
                    task_id=task_id,
                    strategy=PreheatingStrategy.FREQUENCY_BASED,
                    priority=PreheatingPriority.HIGH if pattern.access_frequency > 20 else PreheatingPriority.MEDIUM,
                    cache_key=f"preheat:{pattern.resource_type}:{pattern.resource_id}",
                    data_source=pattern.resource_type,
                    parameters=parameters,
                    estimated_time=pattern.avg_response_time,
                    created_at=datetime.utcnow()
                )
                
                tasks.append(task)
        
        return tasks
    
    async def _generate_time_based_tasks(self) -> List[PreheatingTask]:
        """基于时间模式生成任务"""
        tasks = []
        current_hour = datetime.utcnow().hour
        
        for key, pattern in self.access_patterns.items():
            # 在高峰时段前预热数据
            if (current_hour + 1) % 24 in pattern.peak_hours:
                task_id = f"time_{pattern.resource_type}_{pattern.resource_id}_{int(time.time())}"
                
                # 生成任务参数（与频率任务类似）
                if pattern.resource_type == "ai_chat_sessions":
                    user_id = pattern.resource_id.split("_")[-1]
                    parameters = {"user_id": int(user_id), "limit": 30}  # 高峰期预热更多数据
                else:
                    continue
                
                task = PreheatingTask(
                    task_id=task_id,
                    strategy=PreheatingStrategy.TIME_BASED,
                    priority=PreheatingPriority.MEDIUM,
                    cache_key=f"preheat_time:{pattern.resource_type}:{pattern.resource_id}",
                    data_source=pattern.resource_type,
                    parameters=parameters,
                    estimated_time=pattern.avg_response_time * 1.5,  # 预热更多数据需要更多时间
                    created_at=datetime.utcnow(),
                    scheduled_at=datetime.utcnow() + timedelta(minutes=30)  # 提前30分钟预热
                )
                
                tasks.append(task)
        
        return tasks
    
    async def _generate_behavior_based_tasks(self) -> List[PreheatingTask]:
        """基于用户行为生成任务"""
        tasks = []
        
        # 为活跃用户预热常用数据
        active_users = await self._get_active_users()
        
        for user_id in active_users:
            # 预热用户偏好
            task = PreheatingTask(
                task_id=f"behavior_preferences_{user_id}_{int(time.time())}",
                strategy=PreheatingStrategy.USER_BEHAVIOR,
                priority=PreheatingPriority.LOW,
                cache_key=f"preheat_prefs:{user_id}",
                data_source="user_preferences",
                parameters={"user_id": user_id},
                estimated_time=0.1,
                created_at=datetime.utcnow()
            )
            tasks.append(task)
        
        return tasks
    
    async def _generate_predictive_tasks(self) -> List[PreheatingTask]:
        """生成预测性任务"""
        tasks = []
        
        # 预热AI模型配置（所有用户都可能需要）
        task = PreheatingTask(
            task_id=f"predictive_models_{int(time.time())}",
            strategy=PreheatingStrategy.PREDICTIVE,
            priority=PreheatingPriority.HIGH,
            cache_key="preheat_models:available",
            data_source="ai_model_configs",
            parameters={},
            estimated_time=0.5,
            created_at=datetime.utcnow()
        )
        tasks.append(task)
        
        return tasks
    
    async def _get_active_users(self) -> List[int]:
        """获取活跃用户列表"""
        # 从访问模式中提取活跃用户
        active_users = set()
        
        for key, pattern in self.access_patterns.items():
            if pattern.resource_type == "ai_chat_sessions":
                user_id = pattern.resource_id.split("_")[-1]
                if pattern.access_frequency > 1:  # 每小时访问超过1次
                    active_users.add(int(user_id))
        
        return list(active_users)
    
    async def schedule_preheating_task(self, task: PreheatingTask):
        """调度预热任务"""
        if task.scheduled_at and task.scheduled_at > datetime.utcnow():
            # 延迟执行
            delay = (task.scheduled_at - datetime.utcnow()).total_seconds()
            await asyncio.sleep(delay)
        
        await self.task_queue.put(task)
        logger.debug(f"预热任务已调度: {task.task_id}")
    
    async def _periodic_analyzer(self):
        """定期分析器"""
        while self.preheating_enabled:
            try:
                # 分析访问模式
                await self.analyze_access_patterns()
                
                # 等待下一个分析周期
                await asyncio.sleep(self.preheating_interval)
                
            except Exception as e:
                logger.error(f"定期分析器异常: {e}")
                await asyncio.sleep(300)  # 出错后等待5分钟
    
    async def _preheating_scheduler(self):
        """预热调度器"""
        while self.preheating_enabled:
            try:
                # 生成预热任务
                tasks = await self.generate_preheating_tasks()
                
                # 调度任务
                for task in tasks:
                    asyncio.create_task(self.schedule_preheating_task(task))
                
                # 等待下一个调度周期
                await asyncio.sleep(self.preheating_interval // 2)  # 每30分钟调度一次
                
            except Exception as e:
                logger.error(f"预热调度器异常: {e}")
                await asyncio.sleep(300)
    
    async def _load_statistics(self):
        """加载统计数据"""
        try:
            stats_data = await self.stats_cache.get("preheating_stats")
            if stats_data:
                self.stats.update(stats_data)
                logger.debug("已加载预热统计数据")
        except Exception as e:
            logger.warning(f"加载统计数据失败: {e}")
    
    async def _save_statistics(self):
        """保存统计数据"""
        try:
            await self.stats_cache.set("preheating_stats", self.stats, 86400)  # 24小时
            logger.debug("已保存预热统计数据")
        except Exception as e:
            logger.warning(f"保存统计数据失败: {e}")
    
    async def _load_access_patterns(self):
        """加载访问模式"""
        try:
            patterns_data = await self.cache.get("access_patterns")
            if patterns_data:
                # 重建访问模式对象
                for key, data in patterns_data.items():
                    self.access_patterns[key] = AccessPattern(**data)
                logger.debug(f"已加载{len(self.access_patterns)}个访问模式")
        except Exception as e:
            logger.warning(f"加载访问模式失败: {e}")
    
    async def _save_access_patterns(self):
        """保存访问模式"""
        try:
            # 转换为可序列化的格式
            patterns_data = {}
            for key, pattern in self.access_patterns.items():
                patterns_data[key] = {
                    "resource_type": pattern.resource_type,
                    "resource_id": pattern.resource_id,
                    "access_count": pattern.access_count,
                    "last_access": pattern.last_access.isoformat(),
                    "access_frequency": pattern.access_frequency,
                    "peak_hours": pattern.peak_hours,
                    "user_count": pattern.user_count,
                    "avg_response_time": pattern.avg_response_time
                }
            
            await self.cache.set("access_patterns", patterns_data, 3600)
            logger.debug(f"已保存{len(patterns_data)}个访问模式")
        except Exception as e:
            logger.warning(f"保存访问模式失败: {e}")
    
    async def get_preheating_status(self) -> Dict[str, Any]:
        """获取预热状态"""
        return {
            "enabled": self.preheating_enabled,
            "running_tasks": len(self.running_tasks),
            "queued_tasks": self.task_queue.qsize(),
            "completed_tasks": len(self.completed_tasks),
            "access_patterns": len(self.access_patterns),
            "statistics": self.stats.copy(),
            "last_analysis": datetime.utcnow().isoformat()
        }
    
    async def manual_preheat(self, data_source: str, parameters: Dict[str, Any]) -> str:
        """手动预热"""
        task_id = f"manual_{data_source}_{int(time.time())}"
        
        task = PreheatingTask(
            task_id=task_id,
            strategy=PreheatingStrategy.MANUAL,
            priority=PreheatingPriority.HIGH,
            cache_key=f"manual_preheat:{data_source}",
            data_source=data_source,
            parameters=parameters,
            estimated_time=1.0,
            created_at=datetime.utcnow()
        )
        
        await self.task_queue.put(task)
        logger.info(f"手动预热任务已创建: {task_id}")
        
        return task_id
    
    async def stop_preheating(self):
        """停止预热服务"""
        self.preheating_enabled = False
        
        # 保存统计数据
        await self._save_statistics()
        await self._save_access_patterns()
        
        logger.info("缓存预热服务已停止")


# 全局预热服务实例
_preheating_service = None

async def get_cache_preheating_service() -> CachePreheatingService:
    """获取缓存预热服务实例"""
    global _preheating_service
    
    if _preheating_service is None:
        _preheating_service = CachePreheatingService()
        await _preheating_service.initialize()
    
    return _preheating_service


# 便捷函数
async def start_cache_preheating():
    """启动缓存预热"""
    service = await get_cache_preheating_service()
    await service.start_preheating_worker()


async def manual_cache_preheat(data_source: str, **parameters) -> str:
    """手动缓存预热"""
    service = await get_cache_preheating_service()
    return await service.manual_preheat(data_source, parameters)


async def get_preheating_status() -> Dict[str, Any]:
    """获取预热状态"""
    service = await get_cache_preheating_service()
    return await service.get_preheating_status()