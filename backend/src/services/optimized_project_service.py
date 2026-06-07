"""
优化的项目管理服务

本模块提供经过性能优化的项目管理服务，包括：
- 查询优化
- 缓存策略
- 批量操作
- 性能监控
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload, contains_eager

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.project import Project, ProjectMember, Task, Milestone, WorkLog
from ..models.user import User
from ..schemas.project import (
    CreateProjectRequest, UpdateProjectRequest, ProjectQueryParams,
    ProjectResponse, ProjectListResponse, ProjectSummaryResponse
)
from ..utils.database_optimization import monitor_query, cache_result, cache_manager
from ..services.project_service import ProjectService

logger = logging.getLogger(__name__)


class OptimizedProjectService(ProjectService):
    """优化的项目管理服务"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.cache_manager = cache_manager
    
    @monitor_query("get_projects_list_optimized")
    @cache_result("projects_list:{user_id}:{page}:{size}:{status}:{project_type}:{priority}:{search}", ttl=60)
    async def get_projects_list_optimized(
        self, 
        params: ProjectQueryParams, 
        user_id: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        优化的项目列表查询
        
        优化策略：
        1. 使用复合索引
        2. 减少JOIN操作
        3. 分页优化
        4. 结果缓存
        """
        # 构建优化的查询
        query = select(
            Project.id,
            Project.project_code,
            Project.project_name,
            Project.description,
            Project.project_type,
            Project.priority,
            Project.status,
            Project.health_score,
            Project.risk_level,
            Project.planned_start_date,
            Project.planned_end_date,
            Project.project_manager_id,
            Project.progress_percentage,
            Project.task_count,
            Project.completed_task_count,
            Project.created_at,
            Project.updated_at
        ).where(Project.deleted_at.is_(None))
        
        count_query = select(func.count(Project.id)).where(Project.deleted_at.is_(None))
        
        # 应用过滤条件（使用索引友好的顺序）
        filters = []
        
        # 首先应用最具选择性的过滤条件
        if params.status:
            filters.append(Project.status.in_(params.status))
        
        if params.project_type:
            filters.append(Project.project_type.in_(params.project_type))
        
        if params.priority:
            filters.append(Project.priority.in_(params.priority))
        
        if params.project_manager_id:
            filters.append(Project.project_manager_id == params.project_manager_id)
        
        # 日期范围过滤（使用索引）
        if params.start_date_from or params.start_date_to:
            if params.start_date_from:
                filters.append(Project.planned_start_date >= params.start_date_from)
            if params.start_date_to:
                filters.append(Project.planned_start_date <= params.start_date_to)
        
        # 权限过滤（优化子查询）
        permission_filter = await self._build_optimized_permission_filter(user_id)
        if permission_filter is not None:
            filters.append(permission_filter)
        
        # 搜索过滤（最后应用，因为开销较大）
        if params.search:
            search_filter = await self._build_search_filter(params.search)
            filters.append(search_filter)
        
        # 应用所有过滤条件
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # 优化排序（使用索引友好的排序）
        sort_column = getattr(Project, params.sort_by, Project.updated_at)
        if params.sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # 分页优化
        offset = (params.page - 1) * params.size
        query = query.offset(offset).limit(params.size)
        
        # 并行执行查询和计数
        import asyncio
        results, count_result = await asyncio.gather(
            self.db.execute(query),
            self.db.execute(count_query)
        )
        
        projects = results.fetchall()
        total = count_result.scalar()
        
        # 转换为字典格式以便缓存
        project_dicts = []
        for project in projects:
            project_dicts.append({
                'id': project.id,
                'project_code': project.project_code,
                'project_name': project.project_name,
                'description': project.description,
                'project_type': project.project_type,
                'priority': project.priority,
                'status': project.status,
                'health_score': project.health_score,
                'risk_level': project.risk_level,
                'planned_start_date': project.planned_start_date.isoformat() if project.planned_start_date else None,
                'planned_end_date': project.planned_end_date.isoformat() if project.planned_end_date else None,
                'project_manager_id': project.project_manager_id,
                'progress_percentage': float(project.progress_percentage) if project.progress_percentage else 0.0,
                'task_count': project.task_count,
                'completed_task_count': project.completed_task_count,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'updated_at': project.updated_at.isoformat() if project.updated_at else None
            })
        
        return project_dicts, total
    
    @monitor_query("get_project_with_details")
    @cache_result("project_details:{project_id}:{user_id}", ttl=120)
    async def get_project_with_details(self, project_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取项目详情（包含关联数据）
        
        优化策略：
        1. 使用JOIN减少查询次数
        2. 只加载必要的字段
        3. 缓存结果
        """
        # 使用JOIN一次性获取项目和成员信息
        query = select(Project).options(
            selectinload(Project.members).selectinload(ProjectMember.project),
            selectinload(Project.tasks).load_only(
                Task.id, Task.task_name, Task.status, Task.priority, 
                Task.assignee_id, Task.planned_start_date, Task.planned_end_date
            ),
            selectinload(Project.milestones).load_only(
                Milestone.id, Milestone.milestone_name, Milestone.status, 
                Milestone.planned_date, Milestone.actual_date
            )
        ).where(
            and_(Project.id == project_id, Project.deleted_at.is_(None))
        )
        
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if not project:
            return None
        
        # 检查访问权限
        await self._validate_project_access(project, user_id)
        
        # 转换为字典格式
        project_dict = project.to_dict()
        
        # 添加关联数据
        project_dict['members'] = [member.to_dict() for member in project.members]
        project_dict['tasks'] = [task.to_dict() for task in project.tasks]
        project_dict['milestones'] = [milestone.to_dict() for milestone in project.milestones]
        
        return project_dict
    
    @monitor_query("get_project_statistics")
    @cache_result("project_stats:{project_id}", ttl=300)
    async def get_project_statistics(self, project_id: int) -> Dict[str, Any]:
        """
        获取项目统计信息
        
        优化策略：
        1. 使用聚合查询
        2. 减少数据传输
        3. 缓存统计结果
        """
        # 使用单个查询获取所有统计信息
        stats_query = text("""
            SELECT 
                p.id,
                p.project_name,
                p.status,
                p.progress_percentage,
                p.health_score,
                COUNT(DISTINCT pm.id) as member_count,
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'COMPLETED' THEN t.id END) as completed_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'IN_PROGRESS' THEN t.id END) as in_progress_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'BLOCKED' THEN t.id END) as blocked_tasks,
                COUNT(DISTINCT m.id) as total_milestones,
                COUNT(DISTINCT CASE WHEN m.status = 'COMPLETED' THEN m.id END) as completed_milestones,
                COUNT(DISTINCT CASE WHEN m.status = 'OVERDUE' THEN m.id END) as overdue_milestones,
                COALESCE(SUM(wl.hours_worked), 0) as total_hours_logged,
                COUNT(DISTINCT pr.id) as total_risks,
                COUNT(DISTINCT CASE WHEN pr.risk_level = 'HIGH' OR pr.risk_level = 'CRITICAL' THEN pr.id END) as high_risks
            FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id AND pm.status = 'ACTIVE'
            LEFT JOIN project_tasks t ON p.id = t.project_id
            LEFT JOIN project_milestones m ON p.id = m.project_id
            LEFT JOIN work_logs wl ON p.id = wl.project_id AND wl.status = 'APPROVED'
            LEFT JOIN project_risks pr ON p.id = pr.project_id AND pr.status != 'CLOSED'
            WHERE p.id = :project_id AND p.deleted_at IS NULL
            GROUP BY p.id, p.project_name, p.status, p.progress_percentage, p.health_score
        """)
        
        result = await self.db.execute(stats_query, {"project_id": project_id})
        stats = result.fetchone()
        
        if not stats:
            return {}
        
        return {
            'project_id': stats.id,
            'project_name': stats.project_name,
            'status': stats.status,
            'progress_percentage': float(stats.progress_percentage) if stats.progress_percentage else 0.0,
            'health_score': stats.health_score,
            'member_count': stats.member_count,
            'task_statistics': {
                'total': stats.total_tasks,
                'completed': stats.completed_tasks,
                'in_progress': stats.in_progress_tasks,
                'blocked': stats.blocked_tasks,
                'completion_rate': stats.completed_tasks / max(stats.total_tasks, 1)
            },
            'milestone_statistics': {
                'total': stats.total_milestones,
                'completed': stats.completed_milestones,
                'overdue': stats.overdue_milestones,
                'completion_rate': stats.completed_milestones / max(stats.total_milestones, 1)
            },
            'work_statistics': {
                'total_hours_logged': float(stats.total_hours_logged)
            },
            'risk_statistics': {
                'total_risks': stats.total_risks,
                'high_risks': stats.high_risks,
                'risk_ratio': stats.high_risks / max(stats.total_risks, 1)
            }
        }
    
    async def batch_update_project_progress(self, project_ids: List[int]) -> Dict[int, float]:
        """
        批量更新项目进度
        
        优化策略：
        1. 批量查询
        2. 批量更新
        3. 减少数据库往返
        """
        if not project_ids:
            return {}
        
        # 批量查询项目任务统计
        progress_query = text("""
            SELECT 
                p.id as project_id,
                COUNT(t.id) as total_tasks,
                COUNT(CASE WHEN t.status = 'COMPLETED' THEN 1 END) as completed_tasks,
                COALESCE(AVG(CASE WHEN t.status = 'COMPLETED' THEN 100 
                                  WHEN t.status = 'IN_PROGRESS' THEN 50 
                                  ELSE 0 END), 0) as calculated_progress
            FROM projects p
            LEFT JOIN project_tasks t ON p.id = t.project_id
            WHERE p.id = ANY(:project_ids) AND p.deleted_at IS NULL
            GROUP BY p.id
        """)
        
        result = await self.db.execute(progress_query, {"project_ids": project_ids})
        progress_data = result.fetchall()
        
        # 批量更新进度
        updates = []
        progress_results = {}
        
        for row in progress_data:
            new_progress = round(row.calculated_progress, 2)
            updates.append({
                'id': row.project_id,
                'progress_percentage': new_progress,
                'task_count': row.total_tasks,
                'completed_task_count': row.completed_tasks,
                'updated_at': datetime.utcnow()
            })
            progress_results[row.project_id] = new_progress
        
        if updates:
            # 使用批量更新
            from sqlalchemy.dialects.mysql import insert
            stmt = insert(Project).values(updates)
            stmt = stmt.on_duplicate_key_update(
                progress_percentage=stmt.inserted.progress_percentage,
                task_count=stmt.inserted.task_count,
                completed_task_count=stmt.inserted.completed_task_count,
                updated_at=stmt.inserted.updated_at
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            # 清除相关缓存
            for project_id in project_ids:
                await self.cache_manager.invalidate_cache(f"project_*:{project_id}*")
        
        return progress_results
    
    async def _build_optimized_permission_filter(self, user_id: int):
        """构建优化的权限过滤条件"""
        # 使用EXISTS子查询而不是IN，性能更好
        member_exists = select(1).where(
            and_(
                ProjectMember.project_id == Project.id,
                ProjectMember.user_id == user_id,
                ProjectMember.status == "ACTIVE"
            )
        ).exists()
        
        return or_(
            Project.project_manager_id == user_id,
            member_exists
        )
    
    async def _build_search_filter(self, search_term: str):
        """构建搜索过滤条件"""
        search_pattern = f"%{search_term}%"
        
        # 优先使用索引字段进行搜索
        return or_(
            Project.project_name.ilike(search_pattern),
            Project.project_code.ilike(search_pattern),
            # 全文搜索作为备选
            text("MATCH(project_name, description) AGAINST(:search_term IN BOOLEAN MODE)").params(
                search_term=search_term
            )
        )
    
    async def invalidate_project_cache(self, project_id: int):
        """清除项目相关缓存"""
        patterns = [
            f"project_*:{project_id}*",
            f"projects_list:*",
            f"project_stats:{project_id}"
        ]
        
        for pattern in patterns:
            await self.cache_manager.invalidate_cache(pattern)
    
    async def create_project(self, request: CreateProjectRequest, creator_id: int) -> Project:
        """创建项目（重写以清除缓存）"""
        project = await super().create_project(request, creator_id)
        
        # 清除列表缓存
        await self.cache_manager.invalidate_cache("projects_list:*")
        
        return project
    
    async def update_project(
        self, 
        project_id: int, 
        request: UpdateProjectRequest, 
        user_id: int
    ) -> Project:
        """更新项目（重写以清除缓存）"""
        project = await super().update_project(project_id, request, user_id)
        
        # 清除相关缓存
        await self.invalidate_project_cache(project_id)
        
        return project
    
    async def delete_project(self, project_id: int, user_id: int) -> bool:
        """删除项目（重写以清除缓存）"""
        result = await super().delete_project(project_id, user_id)
        
        if result:
            # 清除相关缓存
            await self.invalidate_project_cache(project_id)
        
        return result


# 依赖注入函数
async def get_optimized_project_service(db: AsyncSession = None) -> OptimizedProjectService:
    """获取优化的项目服务实例"""
    if db is None:
        async with get_async_session() as session:
            return OptimizedProjectService(session)
    return OptimizedProjectService(db)