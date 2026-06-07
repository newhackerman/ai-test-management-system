"""
仪表板数据集成服务
集成各个模块的数据，为仪表板提供统一的数据接口
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..core.database import get_async_session
from ..utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class DashboardDataIntegrationService:
    """仪表板数据集成服务"""
    
    def __init__(self):
        self.cache_prefix = "dashboard:integration:"
        self.cache_ttl = 300  # 5分钟缓存
    
    async def get_user_management_data(self, user_id: int, role_type: str) -> Dict[str, Any]:
        """集成用户管理模块数据"""
        try:
            cache_key = f"{self.cache_prefix}user_mgmt:{user_id}:{role_type}"
            redis_client = await get_redis_client()
            
            # 尝试从缓存获取
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
            
            async for session in get_async_session():
                # 获取用户基本信息
                user_query = text("""
                    SELECT u.id, u.username, u.email, u.is_active, u.created_at,
                           u.last_login_at, u.login_count
                    FROM users u
                    WHERE u.id = :user_id
                """)
                user_result = await session.execute(user_query, {"user_id": user_id})
                user_data = user_result.fetchone()
                
                if not user_data:
                    return {}
                
                # 获取用户角色信息
                role_query = text("""
                    SELECT r.id, r.name, r.description, r.permissions
                    FROM roles r
                    JOIN user_roles ur ON r.id = ur.role_id
                    WHERE ur.user_id = :user_id
                """)
                role_result = await session.execute(role_query, {"user_id": user_id})
                roles = [dict(row._mapping) for row in role_result.fetchall()]
                
                # 获取用户权限信息
                permission_query = text("""
                    SELECT DISTINCT p.id, p.name, p.resource, p.action
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    JOIN user_roles ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = :user_id
                """)
                permission_result = await session.execute(permission_query, {"user_id": user_id})
                permissions = [dict(row._mapping) for row in permission_result.fetchall()]
                
                # 获取用户会话信息
                session_query = text("""
                    SELECT COUNT(*) as active_sessions,
                           MAX(created_at) as last_session
                    FROM user_sessions
                    WHERE user_id = :user_id AND is_active = 1
                """)
                session_result = await session.execute(session_query, {"user_id": user_id})
                session_data = session_result.fetchone()
                
                data = {
                    "user_info": dict(user_data._mapping) if user_data else {},
                    "roles": roles,
                    "permissions": permissions,
                    "session_info": dict(session_data._mapping) if session_data else {},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 缓存数据
                import json
                await redis_client.setex(cache_key, self.cache_ttl, json.dumps(data, default=str))
                
                return data
                
        except Exception as e:
            logger.error(f"获取用户管理数据失败: {e}")
            return {}
    
    async def get_project_management_data(self, user_id: int, project_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """集成项目管理模块数据"""
        try:
            cache_key = f"{self.cache_prefix}project_mgmt:{user_id}:{hash(str(project_ids))}"
            redis_client = await get_redis_client()
            
            # 尝试从缓存获取
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
            
            async for session in get_async_session():
                # 构建项目查询条件
                project_filter = ""
                params = {"user_id": user_id}
                
                if project_ids:
                    project_filter = "AND p.id IN :project_ids"
                    params["project_ids"] = tuple(project_ids)
                
                # 获取项目基本信息
                project_query = text(f"""
                    SELECT p.id, p.name, p.description, p.status, p.priority,
                           p.start_date, p.end_date, p.planned_end_date,
                           p.budget, p.actual_cost, p.progress,
                           p.created_at, p.updated_at
                    FROM projects p
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                    ORDER BY p.updated_at DESC
                """)
                project_result = await session.execute(project_query, params)
                projects = [dict(row._mapping) for row in project_result.fetchall()]
                
                # 获取项目统计信息
                stats_query = text(f"""
                    SELECT 
                        COUNT(DISTINCT p.id) as total_projects,
                        COUNT(DISTINCT CASE WHEN p.status = 'ACTIVE' THEN p.id END) as active_projects,
                        COUNT(DISTINCT CASE WHEN p.status = 'COMPLETED' THEN p.id END) as completed_projects,
                        COUNT(DISTINCT CASE WHEN p.status = 'ON_HOLD' THEN p.id END) as on_hold_projects,
                        AVG(p.progress) as avg_progress,
                        SUM(p.budget) as total_budget,
                        SUM(p.actual_cost) as total_actual_cost
                    FROM projects p
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                """)
                stats_result = await session.execute(stats_query, params)
                stats = dict(stats_result.fetchone()._mapping)
                
                # 获取团队成员信息
                team_query = text(f"""
                    SELECT p.id as project_id, p.name as project_name,
                           COUNT(pm.user_id) as team_size,
                           GROUP_CONCAT(DISTINCT pm.role) as roles
                    FROM projects p
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE p.id IN (
                        SELECT DISTINCT p2.id FROM projects p2
                        JOIN project_members pm2 ON p2.id = pm2.project_id
                        WHERE pm2.user_id = :user_id {project_filter}
                    )
                    GROUP BY p.id, p.name
                """)
                team_result = await session.execute(team_query, params)
                team_info = [dict(row._mapping) for row in team_result.fetchall()]
                
                # 获取里程碑信息
                milestone_query = text(f"""
                    SELECT m.id, m.name, m.description, m.due_date, m.status,
                           m.project_id, p.name as project_name
                    FROM milestones m
                    JOIN projects p ON m.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                    AND m.due_date >= CURDATE()
                    ORDER BY m.due_date ASC
                    LIMIT 10
                """)
                milestone_result = await session.execute(milestone_query, params)
                milestones = [dict(row._mapping) for row in milestone_result.fetchall()]
                
                data = {
                    "projects": projects,
                    "statistics": stats,
                    "team_info": team_info,
                    "upcoming_milestones": milestones,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 缓存数据
                import json
                await redis_client.setex(cache_key, self.cache_ttl, json.dumps(data, default=str))
                
                return data
                
        except Exception as e:
            logger.error(f"获取项目管理数据失败: {e}")
            return {}
    
    async def get_requirement_management_data(self, user_id: int, project_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """集成需求管理模块数据"""
        try:
            cache_key = f"{self.cache_prefix}req_mgmt:{user_id}:{hash(str(project_ids))}"
            redis_client = await get_redis_client()
            
            # 尝试从缓存获取
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
            
            async for session in get_async_session():
                # 构建项目过滤条件
                project_filter = ""
                params = {"user_id": user_id}
                
                if project_ids:
                    project_filter = "AND r.project_id IN :project_ids"
                    params["project_ids"] = tuple(project_ids)
                
                # 获取需求统计信息
                req_stats_query = text(f"""
                    SELECT 
                        COUNT(*) as total_requirements,
                        COUNT(CASE WHEN r.status = 'DRAFT' THEN 1 END) as draft_count,
                        COUNT(CASE WHEN r.status = 'UNDER_REVIEW' THEN 1 END) as under_review_count,
                        COUNT(CASE WHEN r.status = 'APPROVED' THEN 1 END) as approved_count,
                        COUNT(CASE WHEN r.status = 'IN_DEVELOPMENT' THEN 1 END) as in_development_count,
                        COUNT(CASE WHEN r.status = 'COMPLETED' THEN 1 END) as completed_count,
                        COUNT(CASE WHEN r.priority = 'HIGH' THEN 1 END) as high_priority_count,
                        COUNT(CASE WHEN r.priority = 'MEDIUM' THEN 1 END) as medium_priority_count,
                        COUNT(CASE WHEN r.priority = 'LOW' THEN 1 END) as low_priority_count,
                        AVG(r.quality_score) as avg_quality_score
                    FROM requirements r
                    JOIN projects p ON r.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                """)
                req_stats_result = await session.execute(req_stats_query, params)
                req_stats = dict(req_stats_result.fetchone()._mapping)
                
                # 获取需求变更统计
                change_stats_query = text(f"""
                    SELECT 
                        COUNT(*) as total_changes,
                        COUNT(CASE WHEN rc.status = 'PENDING' THEN 1 END) as pending_changes,
                        COUNT(CASE WHEN rc.status = 'APPROVED' THEN 1 END) as approved_changes,
                        COUNT(CASE WHEN rc.status = 'REJECTED' THEN 1 END) as rejected_changes,
                        AVG(DATEDIFF(rc.resolved_at, rc.created_at)) as avg_resolution_days
                    FROM requirement_changes rc
                    JOIN requirements r ON rc.requirement_id = r.id
                    JOIN projects p ON r.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                    AND rc.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                change_stats_result = await session.execute(change_stats_query, params)
                change_stats = dict(change_stats_result.fetchone()._mapping)
                
                # 获取需求追溯覆盖率
                traceability_query = text(f"""
                    SELECT 
                        COUNT(DISTINCT r.id) as total_requirements,
                        COUNT(DISTINCT rt.requirement_id) as traced_requirements,
                        (COUNT(DISTINCT rt.requirement_id) * 100.0 / COUNT(DISTINCT r.id)) as coverage_percentage
                    FROM requirements r
                    LEFT JOIN requirement_traceability rt ON r.id = rt.requirement_id
                    JOIN projects p ON r.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                """)
                traceability_result = await session.execute(traceability_query, params)
                traceability_stats = dict(traceability_result.fetchone()._mapping)
                
                # 获取最近的需求活动
                recent_activity_query = text(f"""
                    SELECT r.id, r.title, r.status, r.priority, r.updated_at,
                           p.name as project_name, u.username as updated_by
                    FROM requirements r
                    JOIN projects p ON r.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    LEFT JOIN users u ON r.updated_by = u.id
                    WHERE pm.user_id = :user_id {project_filter}
                    ORDER BY r.updated_at DESC
                    LIMIT 10
                """)
                activity_result = await session.execute(recent_activity_query, params)
                recent_activities = [dict(row._mapping) for row in activity_result.fetchall()]
                
                data = {
                    "requirement_statistics": req_stats,
                    "change_statistics": change_stats,
                    "traceability_statistics": traceability_stats,
                    "recent_activities": recent_activities,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 缓存数据
                import json
                await redis_client.setex(cache_key, self.cache_ttl, json.dumps(data, default=str))
                
                return data
                
        except Exception as e:
            logger.error(f"获取需求管理数据失败: {e}")
            return {}
    
    async def get_test_management_data(self, user_id: int, project_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """集成测试管理模块数据"""
        try:
            cache_key = f"{self.cache_prefix}test_mgmt:{user_id}:{hash(str(project_ids))}"
            redis_client = await get_redis_client()
            
            # 尝试从缓存获取
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
            
            async for session in get_async_session():
                # 构建项目过滤条件
                project_filter = ""
                params = {"user_id": user_id}
                
                if project_ids:
                    project_filter = "AND tp.project_id IN :project_ids"
                    params["project_ids"] = tuple(project_ids)
                
                # 获取测试用例统计
                test_case_stats_query = text(f"""
                    SELECT 
                        COUNT(*) as total_test_cases,
                        COUNT(CASE WHEN tc.status = 'ACTIVE' THEN 1 END) as active_cases,
                        COUNT(CASE WHEN tc.automation_level = 'MANUAL' THEN 1 END) as manual_cases,
                        COUNT(CASE WHEN tc.automation_level = 'SEMI_AUTO' THEN 1 END) as semi_auto_cases,
                        COUNT(CASE WHEN tc.automation_level = 'FULL_AUTO' THEN 1 END) as full_auto_cases,
                        COUNT(CASE WHEN tc.priority = 'HIGH' THEN 1 END) as high_priority_cases,
                        COUNT(CASE WHEN tc.priority = 'MEDIUM' THEN 1 END) as medium_priority_cases,
                        COUNT(CASE WHEN tc.priority = 'LOW' THEN 1 END) as low_priority_cases
                    FROM test_cases tc
                    JOIN test_plans tp ON tc.test_plan_id = tp.id
                    JOIN projects p ON tp.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                """)
                test_case_result = await session.execute(test_case_stats_query, params)
                test_case_stats = dict(test_case_result.fetchone()._mapping)
                
                # 获取测试执行统计
                execution_stats_query = text(f"""
                    SELECT 
                        COUNT(*) as total_executions,
                        COUNT(CASE WHEN te.status = 'PASSED' THEN 1 END) as passed_executions,
                        COUNT(CASE WHEN te.status = 'FAILED' THEN 1 END) as failed_executions,
                        COUNT(CASE WHEN te.status = 'BLOCKED' THEN 1 END) as blocked_executions,
                        COUNT(CASE WHEN te.status = 'SKIPPED' THEN 1 END) as skipped_executions,
                        (COUNT(CASE WHEN te.status = 'PASSED' THEN 1 END) * 100.0 / COUNT(*)) as pass_rate,
                        AVG(TIMESTAMPDIFF(MINUTE, te.started_at, te.completed_at)) as avg_execution_time
                    FROM test_executions te
                    JOIN test_cases tc ON te.test_case_id = tc.id
                    JOIN test_plans tp ON tc.test_plan_id = tp.id
                    JOIN projects p ON tp.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                    AND te.executed_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                execution_result = await session.execute(execution_stats_query, params)
                execution_stats = dict(execution_result.fetchone()._mapping)
                
                # 获取缺陷统计
                defect_stats_query = text(f"""
                    SELECT 
                        COUNT(*) as total_defects,
                        COUNT(CASE WHEN d.status = 'OPEN' THEN 1 END) as open_defects,
                        COUNT(CASE WHEN d.status = 'IN_PROGRESS' THEN 1 END) as in_progress_defects,
                        COUNT(CASE WHEN d.status = 'RESOLVED' THEN 1 END) as resolved_defects,
                        COUNT(CASE WHEN d.status = 'CLOSED' THEN 1 END) as closed_defects,
                        COUNT(CASE WHEN d.severity = 'CRITICAL' THEN 1 END) as critical_defects,
                        COUNT(CASE WHEN d.severity = 'HIGH' THEN 1 END) as high_severity_defects,
                        COUNT(CASE WHEN d.severity = 'MEDIUM' THEN 1 END) as medium_severity_defects,
                        COUNT(CASE WHEN d.severity = 'LOW' THEN 1 END) as low_severity_defects,
                        AVG(DATEDIFF(d.resolved_at, d.created_at)) as avg_resolution_days
                    FROM defects d
                    JOIN projects p ON d.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                """)
                defect_result = await session.execute(defect_stats_query, params)
                defect_stats = dict(defect_result.fetchone()._mapping)
                
                # 获取测试覆盖率信息
                coverage_query = text(f"""
                    SELECT 
                        COUNT(DISTINCT r.id) as total_requirements,
                        COUNT(DISTINCT CASE WHEN tc.id IS NOT NULL THEN r.id END) as covered_requirements,
                        (COUNT(DISTINCT CASE WHEN tc.id IS NOT NULL THEN r.id END) * 100.0 / COUNT(DISTINCT r.id)) as coverage_percentage
                    FROM requirements r
                    LEFT JOIN test_cases tc ON r.id = tc.requirement_id
                    JOIN projects p ON r.project_id = p.id
                    JOIN project_members pm ON p.id = pm.project_id
                    WHERE pm.user_id = :user_id {project_filter}
                """)
                coverage_result = await session.execute(coverage_query, params)
                coverage_stats = dict(coverage_result.fetchone()._mapping)
                
                data = {
                    "test_case_statistics": test_case_stats,
                    "execution_statistics": execution_stats,
                    "defect_statistics": defect_stats,
                    "coverage_statistics": coverage_stats,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 缓存数据
                import json
                await redis_client.setex(cache_key, self.cache_ttl, json.dumps(data, default=str))
                
                return data
                
        except Exception as e:
            logger.error(f"获取测试管理数据失败: {e}")
            return {}
    
    async def get_integrated_dashboard_data(
        self, 
        user_id: int, 
        role_type: str, 
        project_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """获取集成的仪表板数据"""
        try:
            # 并行获取各模块数据
            import asyncio
            
            tasks = [
                self.get_user_management_data(user_id, role_type),
                self.get_project_management_data(user_id, project_ids),
                self.get_requirement_management_data(user_id, project_ids),
                self.get_test_management_data(user_id, project_ids)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            user_data = results[0] if not isinstance(results[0], Exception) else {}
            project_data = results[1] if not isinstance(results[1], Exception) else {}
            requirement_data = results[2] if not isinstance(results[2], Exception) else {}
            test_data = results[3] if not isinstance(results[3], Exception) else {}
            
            # 记录异常
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    module_names = ["用户管理", "项目管理", "需求管理", "测试管理"]
                    logger.error(f"{module_names[i]}模块数据获取失败: {result}")
            
            integrated_data = {
                "user_management": user_data,
                "project_management": project_data,
                "requirement_management": requirement_data,
                "test_management": test_data,
                "integration_timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "role_type": role_type,
                "project_ids": project_ids
            }
            
            return integrated_data
            
        except Exception as e:
            logger.error(f"获取集成仪表板数据失败: {e}")
            return {}
    
    async def refresh_integration_cache(self, user_id: int, role_type: str) -> bool:
        """刷新集成缓存"""
        try:
            redis_client = await get_redis_client()
            
            # 删除相关缓存
            cache_patterns = [
                f"{self.cache_prefix}user_mgmt:{user_id}:*",
                f"{self.cache_prefix}project_mgmt:{user_id}:*",
                f"{self.cache_prefix}req_mgmt:{user_id}:*",
                f"{self.cache_prefix}test_mgmt:{user_id}:*"
            ]
            
            for pattern in cache_patterns:
                keys = await redis_client.keys(pattern)
                if keys:
                    await redis_client.delete(*keys)
            
            logger.info(f"用户 {user_id} 的集成缓存已刷新")
            return True
            
        except Exception as e:
            logger.error(f"刷新集成缓存失败: {e}")
            return False


# 依赖注入
_dashboard_data_integration_service = None

async def get_dashboard_data_integration_service() -> DashboardDataIntegrationService:
    """获取仪表板数据集成服务实例"""
    global _dashboard_data_integration_service
    if _dashboard_data_integration_service is None:
        _dashboard_data_integration_service = DashboardDataIntegrationService()
    return _dashboard_data_integration_service