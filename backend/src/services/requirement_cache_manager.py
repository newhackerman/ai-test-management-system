"""
需求管理缓存管理器

提供需求管理模块的缓存管理功能，包括：
- 缓存策略管理
- 缓存同步机制
- 缓存预热
- 缓存监控和报告
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.requirement import Requirement, RequirementStatus, RequirementType, Priority
from ..repositories.requirement_repository import RequirementRepository
from .requirement_redis_cache import RequirementRedisCache, CacheConfig, cache_result
from ..core.exceptions import CacheError, BusinessLogicError

logger = logging.getLogger(__name__)


@dataclass
class CacheStrategy:
    """缓存策略配置"""
    enable_requirement_cache: bool = True
    enable_project_cache: bool = True
    enable_search_cache: bool = True
    enable_stats_cache: bool = True
    enable_hot_data_tracking: bool = True
    
    # 预热策略
    preload_hot_requirements: bool = True
    preload_recent_projects: bool = True
    preload_active_users: bool = True
    
    # 失效策略
    auto_invalidate_on_update: bool = True
    cascade_invalidation: bool = True
    
    # 性能策略
    max_cache_size_mb: int = 512
    cleanup_interval_minutes: int = 30
    stats_collection_interval_minutes: int = 5


class RequirementCacheManager:
    """需求管理缓存管理器"""
    
    def __init__(self, db: AsyncSession, cache: RequirementRedisCache, 
                 strategy: CacheStrategy = None):
        self.db = db
        self.cache = cache
        self.strategy = strategy or CacheStrategy()
        self.requirement_repo = RequirementRepository(db)
        
        # 缓存预热任务
        self._preload_tasks = []
        self._cleanup_task = None
        self._stats_task = None
        
        # 缓存同步锁
        self._sync_locks = {}
    
    async def start(self):
        """启动缓存管理器"""
        # 连接Redis
        if not await self.cache.connect():
            raise CacheError("无法连接到Redis缓存服务")
        
        # 启动后台任务
        await self._start_background_tasks()
        
        # 执行缓存预热
        if self.strategy.preload_hot_requirements:
            await self._preload_hot_requirements()
        
        logger.info("需求管理缓存管理器启动成功")
    
    async def stop(self):
        """停止缓存管理器"""
        # 停止后台任务
        await self._stop_background_tasks()
        
        # 断开Redis连接
        await self.cache.disconnect()
        
        logger.info("需求管理缓存管理器已停止")
    
    async def _start_background_tasks(self):
        """启动后台任务"""
        # 缓存清理任务
        if self.strategy.cleanup_interval_minutes > 0:
            self._cleanup_task = asyncio.create_task(self._cache_cleanup_loop())
        
        # 统计收集任务
        if self.strategy.stats_collection_interval_minutes > 0:
            self._stats_task = asyncio.create_task(self._stats_collection_loop())
    
    async def _stop_background_tasks(self):
        """停止后台任务"""
        tasks = [self._cleanup_task, self._stats_task] + self._preload_tasks
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    async def _cache_cleanup_loop(self):
        """缓存清理循环"""
        while True:
            try:
                await asyncio.sleep(self.strategy.cleanup_interval_minutes * 60)
                await self._cleanup_expired_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"缓存清理任务异常: {str(e)}")
    
    async def _stats_collection_loop(self):
        """统计收集循环"""
        while True:
            try:
                await asyncio.sleep(self.strategy.stats_collection_interval_minutes * 60)
                await self._collect_cache_stats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"统计收集任务异常: {str(e)}")
    
    # 需求缓存方法
    
    @cache_result('requirement', 'requirement')
    async def get_requirement_by_id(self, requirement_id: int) -> Optional[Requirement]:
        """获取需求（带缓存）"""
        if not self.strategy.enable_requirement_cache:
            return await self.requirement_repo.get_by_id(requirement_id)
        
        # 尝试从缓存获取
        cached_data = await self.cache.get_cached_requirement(requirement_id)
        if cached_data:
            # 记录热点访问
            if self.strategy.enable_hot_data_tracking:
                await self.cache.increment_requirement_access(requirement_id)
            return self._dict_to_requirement(cached_data)
        
        # 从数据库获取
        requirement = await self.requirement_repo.get_by_id(requirement_id)
        if requirement:
            # 缓存结果
            await self.cache.cache_requirement(requirement)
            
            # 记录热点访问
            if self.strategy.enable_hot_data_tracking:
                await self.cache.increment_requirement_access(requirement_id)
        
        return requirement
    
    async def get_project_requirements(self, project_id: int, skip: int = 0, 
                                     limit: int = 100, use_cache: bool = True) -> Tuple[List[Requirement], int]:
        """获取项目需求列表（带缓存）"""
        if not self.strategy.enable_project_cache or not use_cache:
            return await self.requirement_repo.get_by_project_id(project_id, skip, limit)
        
        # 生成缓存键
        cache_key = f"project_{project_id}_requirements_{skip}_{limit}"
        
        # 尝试从缓存获取
        cached_data = await self.cache.get_cached_project_requirements(project_id)
        if cached_data and isinstance(cached_data, dict):
            if cache_key in cached_data:
                requirements_data = cached_data[cache_key]['requirements']
                total_count = cached_data[cache_key]['total_count']
                
                requirements = [self._dict_to_requirement(req_data) for req_data in requirements_data]
                return requirements, total_count
        
        # 从数据库获取
        requirements, total_count = await self.requirement_repo.get_by_project_id(project_id, skip, limit)
        
        # 缓存结果
        if requirements:
            requirements_data = [req.to_dict() for req in requirements]
            cache_data = {
                cache_key: {
                    'requirements': requirements_data,
                    'total_count': total_count,
                    'cached_at': datetime.now().isoformat()
                }
            }
            
            # 合并现有缓存
            existing_cache = await self.cache.get_cached_project_requirements(project_id) or {}
            if isinstance(existing_cache, dict):
                existing_cache.update(cache_data)
                cache_data = existing_cache
            
            await self.cache.cache_project_requirements(project_id, cache_data)
        
        return requirements, total_count
    
    async def search_requirements_cached(self, search_params: Dict[str, Any]) -> Tuple[List[Requirement], int]:
        """搜索需求（带缓存）"""
        if not self.strategy.enable_search_cache:
            return await self.requirement_repo.search_requirements(search_params)
        
        # 尝试从缓存获取
        cached_results = await self.cache.get_cached_search_results(search_params)
        if cached_results and isinstance(cached_results, dict):
            requirements_data = cached_results.get('requirements', [])
            total_count = cached_results.get('total_count', 0)
            
            requirements = [self._dict_to_requirement(req_data) for req_data in requirements_data]
            return requirements, total_count
        
        # 从数据库搜索
        requirements, total_count = await self.requirement_repo.search_requirements(search_params)
        
        # 缓存搜索结果
        if requirements:
            requirements_data = [req.to_dict() for req in requirements]
            cache_data = {
                'requirements': requirements_data,
                'total_count': total_count,
                'search_params': search_params,
                'cached_at': datetime.now().isoformat()
            }
            await self.cache.cache_search_results(search_params, cache_data)
        
        return requirements, total_count
    
    async def get_requirements_statistics_cached(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """获取需求统计信息（带缓存）"""
        if not self.strategy.enable_stats_cache:
            return await self.requirement_repo.get_requirements_statistics(project_id)
        
        # 尝试从缓存获取
        cached_stats = await self.cache.get_cached_requirement_stats(project_id or 0)
        if cached_stats:
            return cached_stats
        
        # 从数据库获取
        stats = await self.requirement_repo.get_requirements_statistics(project_id)
        
        # 缓存统计信息
        if stats:
            await self.cache.cache_requirement_stats(project_id or 0, stats)
        
        return stats
    
    # 缓存失效方法
    
    async def invalidate_requirement_cache(self, requirement_id: int, requirement_data: Dict[str, Any] = None):
        """使需求缓存失效"""
        if not self.strategy.auto_invalidate_on_update:
            return
        
        # 获取需求数据用于失效策略
        if not requirement_data:
            requirement = await self.requirement_repo.get_by_id(requirement_id)
            if requirement:
                requirement_data = requirement.to_dict()
            else:
                requirement_data = {}
        
        # 执行缓存失效
        await self.cache.invalidate_requirement_cache(requirement_id, requirement_data)
        
        # 级联失效
        if self.strategy.cascade_invalidation:
            project_id = requirement_data.get('project_id')
            if project_id:
                await self.cache.invalidate_project_cache(project_id)
            
            assignee_id = requirement_data.get('assignee_id')
            if assignee_id:
                await self.cache.invalidate_user_cache(assignee_id)
            
            creator_id = requirement_data.get('creator_id')
            if creator_id and creator_id != assignee_id:
                await self.cache.invalidate_user_cache(creator_id)
    
    async def invalidate_project_cache(self, project_id: int):
        """使项目缓存失效"""
        await self.cache.invalidate_project_cache(project_id)
        
        # 同时失效搜索缓存
        await self.cache.invalidate_search_cache()
    
    async def invalidate_search_cache(self):
        """使搜索缓存失效"""
        await self.cache.invalidate_search_cache()
    
    # 缓存预热方法
    
    async def _preload_hot_requirements(self):
        """预加载热点需求"""
        try:
            # 获取最近活跃的需求
            recent_date = datetime.now() - timedelta(days=7)
            recent_requirements = await self.requirement_repo.get_requirements_by_date_range(
                start_date=recent_date.date(),
                end_date=datetime.now().date()
            )
            
            # 预加载前50个需求
            preload_tasks = []
            for requirement in recent_requirements[:50]:
                task = asyncio.create_task(self.cache.cache_requirement(requirement))
                preload_tasks.append(task)
            
            if preload_tasks:
                await asyncio.gather(*preload_tasks, return_exceptions=True)
                logger.info(f"预加载了 {len(preload_tasks)} 个热点需求")
            
        except Exception as e:
            logger.error(f"预加载热点需求失败: {str(e)}")
    
    async def preload_project_requirements(self, project_id: int):
        """预加载项目需求"""
        try:
            requirements, total_count = await self.requirement_repo.get_by_project_id(project_id, 0, 100)
            
            if requirements:
                # 缓存项目需求列表
                requirements_data = [req.to_dict() for req in requirements]
                cache_data = {
                    f"project_{project_id}_requirements_0_100": {
                        'requirements': requirements_data,
                        'total_count': total_count,
                        'cached_at': datetime.now().isoformat()
                    }
                }
                await self.cache.cache_project_requirements(project_id, cache_data)
                
                # 缓存单个需求
                cache_tasks = []
                for requirement in requirements:
                    task = asyncio.create_task(self.cache.cache_requirement(requirement))
                    cache_tasks.append(task)
                
                if cache_tasks:
                    await asyncio.gather(*cache_tasks, return_exceptions=True)
                
                logger.info(f"预加载项目 {project_id} 的 {len(requirements)} 个需求")
            
        except Exception as e:
            logger.error(f"预加载项目需求失败: {str(e)}")
    
    async def preload_user_requirements(self, user_id: int):
        """预加载用户需求"""
        try:
            requirements = await self.requirement_repo.get_requirements_by_assignee(user_id)
            
            if requirements:
                requirements_data = [req.to_dict() for req in requirements]
                await self.cache.cache_user_requirements(user_id, requirements_data)
                
                logger.info(f"预加载用户 {user_id} 的 {len(requirements)} 个需求")
            
        except Exception as e:
            logger.error(f"预加载用户需求失败: {str(e)}")
    
    # 缓存维护方法
    
    async def _cleanup_expired_cache(self):
        """清理过期缓存"""
        try:
            # 获取缓存键数量
            key_counts = await self.cache.get_cache_keys_count()
            total_keys = sum(key_counts.values())
            
            logger.info(f"缓存清理开始，当前缓存键数量: {total_keys}")
            
            # 如果缓存键过多，清理部分缓存
            if total_keys > 10000:  # 假设的阈值
                # 清理搜索缓存（最容易过期的）
                deleted_search = await self.cache.invalidate_search_cache()
                logger.info(f"清理搜索缓存，删除 {deleted_search} 个键")
            
        except Exception as e:
            logger.error(f"缓存清理失败: {str(e)}")
    
    async def _collect_cache_stats(self):
        """收集缓存统计信息"""
        try:
            cache_info = await self.cache.get_cache_info()
            cache_stats = self.cache.get_stats()
            
            # 记录统计信息到日志
            logger.info(f"缓存统计 - 命中率: {cache_stats.hit_rate:.2%}, "
                       f"平均响应时间: {cache_stats.avg_response_time:.3f}s, "
                       f"总请求数: {cache_stats.total_requests}")
            
            # 如果命中率过低，触发预热
            if cache_stats.hit_rate < 0.5 and cache_stats.total_requests > 100:
                logger.warning("缓存命中率过低，触发预热")
                await self._preload_hot_requirements()
            
        except Exception as e:
            logger.error(f"收集缓存统计失败: {str(e)}")
    
    # 分布式同步方法
    
    async def sync_requirement_update(self, requirement_id: int, requirement_data: Dict[str, Any]):
        """同步需求更新"""
        lock_key = f"requirement_sync_{requirement_id}"
        lock_value = await self.cache.acquire_lock(lock_key, timeout=30)
        
        if lock_value:
            try:
                # 使相关缓存失效
                await self.invalidate_requirement_cache(requirement_id, requirement_data)
                
                # 重新缓存需求
                requirement = await self.requirement_repo.get_by_id(requirement_id)
                if requirement:
                    await self.cache.cache_requirement(requirement)
                
            finally:
                await self.cache.release_lock(lock_key, lock_value)
        else:
            logger.warning(f"无法获取需求 {requirement_id} 的同步锁")
    
    async def sync_project_update(self, project_id: int):
        """同步项目更新"""
        lock_key = f"project_sync_{project_id}"
        lock_value = await self.cache.acquire_lock(lock_key, timeout=30)
        
        if lock_value:
            try:
                # 使项目缓存失效
                await self.invalidate_project_cache(project_id)
                
                # 预加载项目需求
                await self.preload_project_requirements(project_id)
                
            finally:
                await self.cache.release_lock(lock_key, lock_value)
        else:
            logger.warning(f"无法获取项目 {project_id} 的同步锁")
    
    # 工具方法
    
    def _dict_to_requirement(self, data: Dict[str, Any]) -> Requirement:
        """将字典转换为需求对象"""
        # 处理枚举类型
        if 'requirement_type' in data and data['requirement_type']:
            data['requirement_type'] = RequirementType(data['requirement_type'])
        if 'status' in data and data['status']:
            data['status'] = RequirementStatus(data['status'])
        if 'priority' in data and data['priority']:
            data['priority'] = Priority(data['priority'])
        
        # 处理日期字段
        date_fields = ['created_at', 'updated_at', 'planned_start_date', 'planned_end_date', 
                      'actual_start_date', 'actual_end_date']
        for field in date_fields:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    try:
                        data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                    except ValueError:
                        data[field] = None
        
        # 创建需求对象
        requirement = Requirement(**{k: v for k, v in data.items() if hasattr(Requirement, k)})
        return requirement
    
    async def get_cache_report(self) -> Dict[str, Any]:
        """获取缓存报告"""
        try:
            cache_info = await self.cache.get_cache_info()
            cache_stats = self.cache.get_stats()
            key_counts = await self.cache.get_cache_keys_count()
            hot_requirements = await self.cache.get_hot_requirements(20)
            
            return {
                'cache_info': cache_info,
                'cache_stats': {
                    'total_requests': cache_stats.total_requests,
                    'cache_hits': cache_stats.cache_hits,
                    'cache_misses': cache_stats.cache_misses,
                    'hit_rate': cache_stats.hit_rate,
                    'miss_rate': cache_stats.miss_rate,
                    'error_rate': cache_stats.error_rate,
                    'avg_response_time': cache_stats.avg_response_time,
                    'last_updated': cache_stats.last_updated.isoformat() if cache_stats.last_updated else None
                },
                'key_counts': key_counts,
                'hot_requirements': hot_requirements,
                'strategy': {
                    'enable_requirement_cache': self.strategy.enable_requirement_cache,
                    'enable_project_cache': self.strategy.enable_project_cache,
                    'enable_search_cache': self.strategy.enable_search_cache,
                    'enable_stats_cache': self.strategy.enable_stats_cache,
                    'enable_hot_data_tracking': self.strategy.enable_hot_data_tracking
                }
            }
            
        except Exception as e:
            logger.error(f"获取缓存报告失败: {str(e)}")
            return {'error': str(e)}
    
    async def clear_all_cache(self) -> bool:
        """清空所有缓存"""
        try:
            result = await self.cache.clear_all_cache()
            if result:
                # 重置统计信息
                self.cache.reset_stats()
                logger.info("已清空所有缓存并重置统计信息")
            return result
            
        except Exception as e:
            logger.error(f"清空缓存失败: {str(e)}")
            return False