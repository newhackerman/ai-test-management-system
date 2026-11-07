"""
缓存预热调度器

本模块实现缓存预热的定时调度功能，包括：
1. 系统启动时的初始预热
2. 定时预热任务调度
3. 智能预热策略执行
4. 预热效果监控和优化

主要功能：
- 系统启动预热
- 定时任务调度
- 智能预热决策
- 预热效果分析
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..services.cache_preheating_service import (
    get_cache_preheating_service,
    PreheatingStrategy,
    PreheatingPriority
)
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CachePreheatingScheduler:
    """缓存预热调度器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.preheating_service = None
        self.is_running = False
        
        # 调度配置
        self.startup_preheat_enabled = True
        self.periodic_preheat_enabled = True
        self.intelligent_preheat_enabled = True
        
        # 预热策略配置
        self.strategies = {
            "startup": {
                "enabled": True,
                "delay_seconds": 30,  # 启动后30秒开始预热
                "tasks": [
                    "ai_model_configs",
                    "system_stats",
                    "popular_templates"
                ]
            },
            "hourly": {
                "enabled": True,
                "tasks": [
                    "active_user_sessions",
                    "recent_suggestions"
                ]
            },
            "daily": {
                "enabled": True,
                "time": "02:00",  # 凌晨2点执行
                "tasks": [
                    "user_pattern_analysis",
                    "cache_optimization",
                    "performance_reports"
                ]
            },
            "peak_hours": {
                "enabled": True,
                "hours": [9, 14, 20],  # 上午9点、下午2点、晚上8点
                "tasks": [
                    "popular_data",
                    "active_user_data"
                ]
            }
        }
    
    async def initialize(self):
        """初始化调度器"""
        try:
            # 获取预热服务
            self.preheating_service = await get_cache_preheating_service()
            
            # 配置调度任务
            await self._setup_scheduled_jobs()
            
            logger.info("缓存预热调度器初始化成功")
            
        except Exception as e:
            logger.error(f"缓存预热调度器初始化失败: {e}")
            raise
    
    async def _setup_scheduled_jobs(self):
        """设置定时任务"""
        # 启动预热任务
        if self.strategies["startup"]["enabled"]:
            self.scheduler.add_job(
                self._startup_preheat,
                'date',
                run_date=datetime.now() + timedelta(seconds=self.strategies["startup"]["delay_seconds"]),
                id='startup_preheat',
                name='系统启动预热'
            )
        
        # 每小时预热任务
        if self.strategies["hourly"]["enabled"]:
            self.scheduler.add_job(
                self._hourly_preheat,
                IntervalTrigger(hours=1),
                id='hourly_preheat',
                name='每小时预热'
            )
        
        # 每日预热任务
        if self.strategies["daily"]["enabled"]:
            hour, minute = self.strategies["daily"]["time"].split(":")
            self.scheduler.add_job(
                self._daily_preheat,
                CronTrigger(hour=int(hour), minute=int(minute)),
                id='daily_preheat',
                name='每日预热'
            )
        
        # 高峰期预热任务
        if self.strategies["peak_hours"]["enabled"]:
            for hour in self.strategies["peak_hours"]["hours"]:
                self.scheduler.add_job(
                    self._peak_hour_preheat,
                    CronTrigger(hour=hour, minute=0),
                    id=f'peak_preheat_{hour}',
                    name=f'高峰期预热-{hour}点'
                )
    
    async def start(self):
        """启动调度器"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("缓存预热调度器已启动")
    
    async def stop(self):
        """停止调度器"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("缓存预热调度器已停止")
    
    async def _startup_preheat(self):
        """系统启动预热"""
        logger.info("开始执行系统启动预热")
        
        try:
            tasks = self.strategies["startup"]["tasks"]
            
            for task_name in tasks:
                if task_name == "ai_model_configs":
                    await self._preheat_ai_models()
                elif task_name == "system_stats":
                    await self._preheat_system_stats()
                elif task_name == "popular_templates":
                    await self._preheat_popular_templates()
            
            logger.info("系统启动预热完成")
            
        except Exception as e:
            logger.error(f"系统启动预热失败: {e}")
    
    async def _hourly_preheat(self):
        """每小时预热"""
        logger.info("开始执行每小时预热")
        
        try:
            tasks = self.strategies["hourly"]["tasks"]
            
            for task_name in tasks:
                if task_name == "active_user_sessions":
                    await self._preheat_active_sessions()
                elif task_name == "recent_suggestions":
                    await self._preheat_recent_suggestions()
            
            logger.info("每小时预热完成")
            
        except Exception as e:
            logger.error(f"每小时预热失败: {e}")
    
    async def _daily_preheat(self):
        """每日预热"""
        logger.info("开始执行每日预热")
        
        try:
            tasks = self.strategies["daily"]["tasks"]
            
            for task_name in tasks:
                if task_name == "user_pattern_analysis":
                    await self.preheating_service.analyze_access_patterns()
                elif task_name == "cache_optimization":
                    await self._optimize_cache_strategy()
                elif task_name == "performance_reports":
                    await self._generate_performance_reports()
            
            logger.info("每日预热完成")
            
        except Exception as e:
            logger.error(f"每日预热失败: {e}")
    
    async def _peak_hour_preheat(self):
        """高峰期预热"""
        current_hour = datetime.now().hour
        logger.info(f"开始执行高峰期预热 - {current_hour}点")
        
        try:
            tasks = self.strategies["peak_hours"]["tasks"]
            
            for task_name in tasks:
                if task_name == "popular_data":
                    await preheat_popular_data()
                elif task_name == "active_user_data":
                    await preheat_user_data()
            
            logger.info(f"高峰期预热完成 - {current_hour}点")
            
        except Exception as e:
            logger.error(f"高峰期预热失败 - {current_hour}点: {e}")
    
    async def _preheat_ai_models(self):
        """预热AI模型配置"""
        task_id = await self.preheating_service.manual_preheat(
            "ai_model_configs", 
            {}
        )
        logger.debug(f"AI模型预热任务已创建: {task_id}")
    
    async def _preheat_system_stats(self):
        """预热系统统计数据"""
        # 预热系统使用统计
        from ..services.enhanced_usage_statistics_service import get_usage_statistics_service
        
        try:
            stats_service = await get_usage_statistics_service()
            try:
                # 触发统计数据计算和缓存
                await stats_service.get_system_overview()
            finally:
                # 短生命周期会话：用完回滚并关闭，不留空闲事务
                await stats_service.aclose()
            logger.debug("系统统计数据预热完成")
        except Exception as e:
            logger.warning(f"系统统计数据预热失败: {e}")
    
    async def _preheat_popular_templates(self):
        """预热热门模板"""
        from ..services.prompt_service import get_prompt_service
        
        try:
            prompt_service = await get_prompt_service()
            # 预热热门模板
            await prompt_service.get_popular_templates(limit=20)
            logger.debug("热门模板预热完成")
        except Exception as e:
            logger.warning(f"热门模板预热失败: {e}")
    
    async def _preheat_active_sessions(self):
        """预热活跃会话"""
        # 获取最近活跃的用户会话
        active_users = await self._get_recent_active_users()
        
        for user_id in active_users[:10]:  # 限制前10个最活跃用户
            task_id = await self.preheating_service.manual_preheat(
                "ai_chat_sessions",
                {"user_id": user_id, "limit": 20}
            )
            logger.debug(f"用户{user_id}会话预热任务已创建: {task_id}")
    
    async def _preheat_recent_suggestions(self):
        """预热最近建议"""
        # 获取最近活跃的项目
        active_projects = await self._get_recent_active_projects()
        
        for project_id in active_projects[:5]:  # 限制前5个活跃项目
            task_id = await self.preheating_service.manual_preheat(
                "ai_suggestions",
                {"project_id": project_id}
            )
            logger.debug(f"项目{project_id}建议预热任务已创建: {task_id}")
    
    async def _optimize_cache_strategy(self):
        """优化缓存策略"""
        try:
            # 分析缓存命中率
            cache_stats = await self._analyze_cache_performance()
            
            # 根据分析结果调整预热策略
            if cache_stats["hit_rate"] < 0.7:  # 命中率低于70%
                # 增加预热频率
                self.preheating_service.preheating_interval = max(
                    1800,  # 最少30分钟
                    self.preheating_service.preheating_interval - 600  # 减少10分钟
                )
                logger.info("缓存命中率较低，增加预热频率")
            
            elif cache_stats["hit_rate"] > 0.9:  # 命中率高于90%
                # 减少预热频率
                self.preheating_service.preheating_interval = min(
                    7200,  # 最多2小时
                    self.preheating_service.preheating_interval + 600  # 增加10分钟
                )
                logger.info("缓存命中率较高，减少预热频率")
            
            logger.debug("缓存策略优化完成")
            
        except Exception as e:
            logger.warning(f"缓存策略优化失败: {e}")
    
    async def _generate_performance_reports(self):
        """生成性能报告"""
        try:
            # 收集预热效果数据
            status = await self.preheating_service.get_preheating_status()
            
            # 生成报告
            report = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_tasks": status["statistics"]["total_tasks"],
                "success_rate": (
                    status["statistics"]["successful_tasks"] / 
                    max(1, status["statistics"]["total_tasks"]) * 100
                ),
                "active_patterns": status["access_patterns"],
                "cache_improvement": status["statistics"].get("cache_hit_improvement", 0),
                "response_improvement": status["statistics"].get("response_time_improvement", 0)
            }
            
            # 保存报告到缓存
            from ..utils.redis_client import get_redis_client
            redis_client = await get_redis_client()
            await redis_client.setex(
                f"preheating_report:{report['date']}", 
                86400 * 7,  # 保存7天
                json.dumps(report)
            )
            
            logger.info(f"性能报告已生成: {report['date']}")
            
        except Exception as e:
            logger.warning(f"性能报告生成失败: {e}")
    
    async def _get_recent_active_users(self) -> List[int]:
        """获取最近活跃用户"""
        try:
            from ..core.database import get_async_session
            from ..models.ai_chat_session import AIChatSession
            from sqlalchemy import select, func, desc
            
            async with get_async_session_ctx() as session:
                # 查询最近24小时内有活动的用户
                result = await session.execute(
                    select(AIChatSession.user_id, func.count(AIChatSession.id).label('session_count'))
                    .where(AIChatSession.updated_at >= datetime.now() - timedelta(hours=24))
                    .group_by(AIChatSession.user_id)
                    .order_by(desc('session_count'))
                    .limit(20)
                )
                
                return [row.user_id for row in result.fetchall()]
                
        except Exception as e:
            logger.warning(f"获取活跃用户失败: {e}")
            return []
    
    async def _get_recent_active_projects(self) -> List[int]:
        """获取最近活跃项目"""
        try:
            from ..core.database import get_async_session
            from ..models.ai_suggestion import AISuggestion
            from sqlalchemy import select, func, desc
            
            async with get_async_session_ctx() as session:
                # 查询最近24小时内有建议活动的项目
                result = await session.execute(
                    select(AISuggestion.project_id, func.count(AISuggestion.id).label('suggestion_count'))
                    .where(
                        AISuggestion.project_id.isnot(None),
                        AISuggestion.created_at >= datetime.now() - timedelta(hours=24)
                    )
                    .group_by(AISuggestion.project_id)
                    .order_by(desc('suggestion_count'))
                    .limit(10)
                )
                
                return [row.project_id for row in result.fetchall()]
                
        except Exception as e:
            logger.warning(f"获取活跃项目失败: {e}")
            return []
    
    async def _analyze_cache_performance(self) -> Dict[str, float]:
        """分析缓存性能"""
        try:
            from ..utils.redis_client import get_redis_client
            redis_client = await get_redis_client()
            
            # 获取Redis统计信息
            info = await redis_client.info('stats')
            
            # 计算命中率
            hits = int(info.get('keyspace_hits', 0))
            misses = int(info.get('keyspace_misses', 0))
            total = hits + misses
            
            hit_rate = hits / total if total > 0 else 0
            
            return {
                "hit_rate": hit_rate,
                "total_requests": total,
                "hits": hits,
                "misses": misses
            }
            
        except Exception as e:
            logger.warning(f"缓存性能分析失败: {e}")
            return {"hit_rate": 0.5, "total_requests": 0, "hits": 0, "misses": 0}
    
    def add_custom_job(self, job_func, trigger, job_id: str, name: str, **kwargs):
        """添加自定义预热任务"""
        self.scheduler.add_job(
            job_func,
            trigger,
            id=job_id,
            name=name,
            **kwargs
        )
        logger.info(f"自定义预热任务已添加: {name}")
    
    def remove_job(self, job_id: str):
        """移除预热任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"预热任务已移除: {job_id}")
        except Exception as e:
            logger.warning(f"移除预热任务失败: {job_id} - {e}")
    
    def get_job_status(self) -> List[Dict[str, Any]]:
        """获取任务状态"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs


# 全局调度器实例
_scheduler = None

async def get_cache_preheating_scheduler() -> CachePreheatingScheduler:
    """获取缓存预热调度器实例"""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = CachePreheatingScheduler()
        await _scheduler.initialize()
    
    return _scheduler


async def start_cache_preheating_scheduler():
    """启动缓存预热调度器"""
    scheduler = await get_cache_preheating_scheduler()
    await scheduler.start()


async def stop_cache_preheating_scheduler():
    """停止缓存预热调度器"""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()


# 便捷预热函数
async def preheat_user_data(user_id: Optional[int] = None, limit: int = 20):
    """预热用户数据"""
    service = await get_cache_preheating_service()
    
    if user_id:
        # 预热指定用户数据
        await service.manual_preheat("ai_chat_sessions", {"user_id": user_id, "limit": limit})
        await service.manual_preheat("user_preferences", {"user_id": user_id})
    else:
        # 预热活跃用户数据
        scheduler = await get_cache_preheating_scheduler()
        active_users = await scheduler._get_recent_active_users()
        
        for uid in active_users[:5]:  # 限制前5个用户
            await service.manual_preheat("ai_chat_sessions", {"user_id": uid, "limit": limit})


async def preheat_popular_data():
    """预热热门数据"""
    service = await get_cache_preheating_service()
    
    # 预热AI模型配置
    await service.manual_preheat("ai_model_configs", {})
    
    # 预热热门模板
    scheduler = await get_cache_preheating_scheduler()
    await scheduler._preheat_popular_templates()


async def preheat_project_data(project_id: int):
    """预热项目数据"""
    service = await get_cache_preheating_service()
    
    # 预热项目相关建议
    await service.manual_preheat("ai_suggestions", {"project_id": project_id})