"""
项目缓存服务

本模块提供项目管理相关数据的缓存功能，包括：
- 项目基本信息缓存
- 项目统计数据缓存
- 用户权限缓存
- 查询结果缓存
"""
import logging
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta

from ..core.redis_client import get_redis_client
from ..models.project import Project, ProjectMember
from ..schemas.project import ProjectResponse

logger = logging.getLogger(__name__)


class ProjectCacheService:
    """项目缓存服务"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.default_ttl = 300  # 5分钟
        self.long_ttl = 3600    # 1小时
        self.short_ttl = 60     # 1分钟
    
    # 项目基本信息缓存
    async def cache_project(self, project: Project, ttl: Optional[int] = None) -> bool:
        """缓存项目基本信息"""
        try:
            cache_key = f"project:{project.id}"
            project_data = project.to_dict()
            
            ttl = ttl or self.default_ttl
            await self.redis.setex(
                cache_key, 
                ttl, 
                json.dumps(project_data, default=str)
            )
            
            # 同时缓存项目编码到ID的映射
            code_key = f"project_code:{project.project_code}"
            await self.redis.setex(code_key, ttl, str(project.id))
            
            return True
            
        except Exception as e:
            logger.error(f"缓存项目信息失败: {e}")
            return False
    
    async def get_cached_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """获取缓存的项目信息"""
        try:
            cache_key = f"project:{project_id}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"获取缓存项目信息失败: {e}")
            return None
    
    async def get_project_id_by_code(self, project_code: str) -> Optional[int]:
        """根据项目编码获取项目ID"""
        try:
            code_key = f"project_code:{project_code}"
            project_id = await self.redis.get(code_key)
            
            if project_id:
                return int(project_id)
            return None
            
        except Exception as e:
            logger.error(f"根据编码获取项目ID失败: {e}")
            return None
    
    # 项目列表缓存
    async def cache_project_list(
        self, 
        cache_key: str, 
        projects: List[Dict[str, Any]], 
        total: int,
        ttl: Optional[int] = None
    ) -> bool:
        """缓存项目列表"""
        try:
            list_data = {
                'projects': projects,
                'total': total,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            ttl = ttl or self.short_ttl
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(list_data, default=str)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"缓存项目列表失败: {e}")
            return False
    
    async def get_cached_project_list(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的项目列表"""
        try:
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"获取缓存项目列表失败: {e}")
            return None
    
    # 项目统计缓存
    async def cache_project_statistics(
        self, 
        project_id: int, 
        stats: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """缓存项目统计信息"""
        try:
            cache_key = f"project_stats:{project_id}"
            stats_data = {
                **stats,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            ttl = ttl or self.default_ttl
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(stats_data, default=str)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"缓存项目统计失败: {e}")
            return False
    
    async def get_cached_project_statistics(self, project_id: int) -> Optional[Dict[str, Any]]:
        """获取缓存的项目统计信息"""
        try:
            cache_key = f"project_stats:{project_id}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"获取缓存项目统计失败: {e}")
            return None
    
    # 用户权限缓存
    async def cache_user_project_permissions(
        self, 
        user_id: int, 
        project_permissions: Dict[int, str],
        ttl: Optional[int] = None
    ) -> bool:
        """缓存用户项目权限"""
        try:
            cache_key = f"user_permissions:{user_id}"
            permission_data = {
                'permissions': project_permissions,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            ttl = ttl or self.long_ttl
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(permission_data, default=str)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"缓存用户权限失败: {e}")
            return False
    
    async def get_cached_user_project_permissions(self, user_id: int) -> Optional[Dict[int, str]]:
        """获取缓存的用户项目权限"""
        try:
            cache_key = f"user_permissions:{user_id}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                # 转换键为整数
                permissions = {int(k): v for k, v in data['permissions'].items()}
                return permissions
            return None
            
        except Exception as e:
            logger.error(f"获取缓存用户权限失败: {e}")
            return None
    
    async def check_user_project_permission(self, user_id: int, project_id: int) -> Optional[str]:
        """检查用户对项目的权限"""
        try:
            permissions = await self.get_cached_user_project_permissions(user_id)
            if permissions:
                return permissions.get(project_id)
            return None
            
        except Exception as e:
            logger.error(f"检查用户项目权限失败: {e}")
            return None
    
    # 项目成员缓存
    async def cache_project_members(
        self, 
        project_id: int, 
        members: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """缓存项目成员信息"""
        try:
            cache_key = f"project_members:{project_id}"
            members_data = {
                'members': members,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            ttl = ttl or self.default_ttl
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(members_data, default=str)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"缓存项目成员失败: {e}")
            return False
    
    async def get_cached_project_members(self, project_id: int) -> Optional[List[Dict[str, Any]]]:
        """获取缓存的项目成员信息"""
        try:
            cache_key = f"project_members:{project_id}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return data['members']
            return None
            
        except Exception as e:
            logger.error(f"获取缓存项目成员失败: {e}")
            return None
    
    # 查询结果缓存
    async def cache_query_result(
        self, 
        query_key: str, 
        result: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """缓存查询结果"""
        try:
            ttl = ttl or self.short_ttl
            await self.redis.setex(
                query_key,
                ttl,
                json.dumps(result, default=str)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"缓存查询结果失败: {e}")
            return False
    
    async def get_cached_query_result(self, query_key: str) -> Optional[Any]:
        """获取缓存的查询结果"""
        try:
            cached_data = await self.redis.get(query_key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"获取缓存查询结果失败: {e}")
            return None
    
    # 缓存失效管理
    async def invalidate_project_cache(self, project_id: int) -> int:
        """清除项目相关缓存"""
        try:
            patterns = [
                f"project:{project_id}",
                f"project_stats:{project_id}",
                f"project_members:{project_id}",
                f"project_details:{project_id}:*",
                f"projects_list:*"  # 清除所有项目列表缓存
            ]
            
            deleted_count = 0
            for pattern in patterns:
                if '*' in pattern:
                    # 模式匹配删除
                    keys = await self.redis.keys(pattern)
                    if keys:
                        deleted_count += await self.redis.delete(*keys)
                else:
                    # 直接删除
                    deleted = await self.redis.delete(pattern)
                    deleted_count += deleted
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清除项目缓存失败: {e}")
            return 0
    
    async def invalidate_user_cache(self, user_id: int) -> int:
        """清除用户相关缓存"""
        try:
            patterns = [
                f"user_permissions:{user_id}",
                f"projects_list:*:{user_id}:*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                if '*' in pattern:
                    keys = await self.redis.keys(pattern)
                    if keys:
                        deleted_count += await self.redis.delete(*keys)
                else:
                    deleted = await self.redis.delete(pattern)
                    deleted_count += deleted
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清除用户缓存失败: {e}")
            return 0
    
    async def invalidate_all_project_caches(self) -> int:
        """清除所有项目相关缓存"""
        try:
            patterns = [
                "project:*",
                "project_*:*",
                "projects_list:*",
                "user_permissions:*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                keys = await self.redis.keys(pattern)
                if keys:
                    deleted_count += await self.redis.delete(*keys)
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清除所有项目缓存失败: {e}")
            return 0
    
    # 缓存预热
    async def warmup_project_cache(self, project_ids: List[int]) -> Dict[str, int]:
        """预热项目缓存"""
        try:
            from ..services.optimized_project_service import get_optimized_project_service
            
            results = {
                'success': 0,
                'failed': 0,
                'total': len(project_ids)
            }
            
            async with get_optimized_project_service() as service:
                for project_id in project_ids:
                    try:
                        # 预热项目基本信息
                        project = await service.get_project_by_id(project_id, 1)  # 使用系统用户ID
                        if project:
                            await self.cache_project(project)
                        
                        # 预热项目统计信息
                        stats = await service.get_project_statistics(project_id)
                        if stats:
                            await self.cache_project_statistics(project_id, stats)
                        
                        results['success'] += 1
                        
                    except Exception as e:
                        logger.warning(f"预热项目 {project_id} 缓存失败: {e}")
                        results['failed'] += 1
            
            return results
            
        except Exception as e:
            logger.error(f"预热项目缓存失败: {e}")
            return {'success': 0, 'failed': len(project_ids), 'total': len(project_ids)}
    
    # 缓存统计
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            # 获取各类缓存的数量
            project_keys = await self.redis.keys("project:*")
            stats_keys = await self.redis.keys("project_stats:*")
            list_keys = await self.redis.keys("projects_list:*")
            permission_keys = await self.redis.keys("user_permissions:*")
            member_keys = await self.redis.keys("project_members:*")
            
            # 获取Redis内存使用情况
            info = await self.redis.info('memory')
            
            return {
                'cache_counts': {
                    'projects': len(project_keys),
                    'statistics': len(stats_keys),
                    'lists': len(list_keys),
                    'permissions': len(permission_keys),
                    'members': len(member_keys),
                    'total': len(project_keys) + len(stats_keys) + len(list_keys) + 
                            len(permission_keys) + len(member_keys)
                },
                'memory_usage': {
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'used_memory_peak': info.get('used_memory_peak', 0),
                    'used_memory_peak_human': info.get('used_memory_peak_human', '0B')
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}


# 全局缓存服务实例
project_cache_service = ProjectCacheService()


# 便捷函数
async def cache_project(project: Project, ttl: Optional[int] = None) -> bool:
    """缓存项目信息"""
    return await project_cache_service.cache_project(project, ttl)


async def get_cached_project(project_id: int) -> Optional[Dict[str, Any]]:
    """获取缓存的项目信息"""
    return await project_cache_service.get_cached_project(project_id)


async def invalidate_project_cache(project_id: int) -> int:
    """清除项目缓存"""
    return await project_cache_service.invalidate_project_cache(project_id)