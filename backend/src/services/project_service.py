"""
项目管理核心服务

本模块实现项目管理的核心业务逻辑，包括：
- 项目CRUD操作
- 项目状态管理
- 项目权限控制
- 项目代码生成
- 项目数据验证
"""
import logging
import re
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.project import Project, ProjectMember
from ..models.user import User
from ..schemas.project import (
    CreateProjectRequest, UpdateProjectRequest, ProjectQueryParams,
    ProjectResponse, ProjectListResponse, ProjectSummaryResponse
)
from ..services.auth import get_current_user
from ..services.project_data_sync_service import notify_project_change, SyncEventType

logger = logging.getLogger(__name__)


class ProjectService:
    """项目管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_project(self, request: CreateProjectRequest, creator_id: int) -> Project:
        """
        创建项目
        
        Args:
            request: 创建项目请求
            creator_id: 创建者ID
            
        Returns:
            创建的项目对象
            
        Raises:
            ValidationError: 数据验证失败
            PermissionError: 权限不足
        """
        # 1. 验证创建者权限
        await self._validate_create_permission(creator_id)
        
        # 2. 验证项目数据
        await self._validate_project_data(request)
        
        # 3. 验证项目名称唯一性
        await self._validate_project_name_unique(request.project_name)
        
        # 4. 验证项目经理权限
        await self._validate_manager_permission(request.project_manager_id)
        
        # 5. 生成项目编码
        project_code = await self._generate_project_code()
        
        # 6. 创建项目实体
        project = Project(
            project_code=project_code,
            project_name=request.project_name,
            description=request.description,
            project_type=request.project_type,
            priority=request.priority,
            planned_start_date=request.planned_start_date,
            planned_end_date=request.planned_end_date,
            project_manager_id=request.project_manager_id,
            test_manager_id=request.test_manager_id,
            client_contact=request.client_contact,
            budget=request.budget,
            tags=request.tags,
            custom_fields=request.custom_fields,
            created_by=creator_id
        )
        
        # 7. 保存项目
        self.db.add(project)
        await self.db.flush()  # 获取项目ID
        
        # 8. 自动添加项目经理为项目成员
        await self._add_project_manager_as_member(project.id, request.project_manager_id)
        
        # 9. 如果指定了测试经理，也添加为项目成员
        if request.test_manager_id:
            await self._add_test_manager_as_member(project.id, request.test_manager_id)
        
        # 10. 提交事务
        await self.db.commit()
        await self.db.refresh(project)
        
        # 11. 通知数据同步服务
        await notify_project_change(
            SyncEventType.PROJECT_CREATED,
            project.id,
            project.id,
            project.to_dict(),
            creator_id
        )
        
        logger.info(f"项目创建成功: {project.project_code} - {project.project_name}")
        return project
    
    async def get_project_by_id(self, project_id: int, user_id: int) -> Optional[Project]:
        """
        根据ID获取项目
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            
        Returns:
            项目对象或None
            
        Raises:
            PermissionError: 权限不足
        """
        # 查询项目
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.members))
            .where(and_(Project.id == project_id, Project.deleted_at.is_(None)))
        )
        project = result.scalar_one_or_none()
        
        if not project:
            return None
        
        # 检查访问权限
        await self._validate_project_access(project, user_id)
        
        return project
    
    async def get_projects_list(
        self, 
        params: ProjectQueryParams, 
        user_id: int
    ) -> Tuple[List[Project], int]:
        """
        获取项目列表
        
        Args:
            params: 查询参数
            user_id: 用户ID
            
        Returns:
            (项目列表, 总数)
        """
        # 构建基础查询
        query = select(Project).where(Project.deleted_at.is_(None))
        count_query = select(func.count(Project.id)).where(Project.deleted_at.is_(None))
        
        # 应用过滤条件
        filters = []
        
        # 状态过滤
        if params.status:
            filters.append(Project.status.in_(params.status))
        
        # 类型过滤
        if params.project_type:
            filters.append(Project.project_type.in_(params.project_type))
        
        # 优先级过滤
        if params.priority:
            filters.append(Project.priority.in_(params.priority))
        
        # 项目经理过滤
        if params.project_manager_id:
            filters.append(Project.project_manager_id == params.project_manager_id)
        
        # 日期范围过滤
        if params.start_date_from:
            filters.append(Project.planned_start_date >= params.start_date_from)
        if params.start_date_to:
            filters.append(Project.planned_start_date <= params.start_date_to)
        if params.end_date_from:
            filters.append(Project.planned_end_date >= params.end_date_from)
        if params.end_date_to:
            filters.append(Project.planned_end_date <= params.end_date_to)
        
        # 搜索过滤
        if params.search:
            search_term = f"%{params.search}%"
            filters.append(
                or_(
                    Project.project_name.ilike(search_term),
                    Project.project_code.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )
        
        # 应用权限过滤
        permission_filter = await self._build_permission_filter(user_id)
        if permission_filter is not None:
            filters.append(permission_filter)
        
        # 应用所有过滤条件
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # 排序
        sort_column = getattr(Project, params.sort_by, Project.updated_at)
        if params.sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # 分页
        offset = (params.page - 1) * params.size
        query = query.offset(offset).limit(params.size)
        
        # 执行查询
        result = await self.db.execute(query)
        projects = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return list(projects), total
    
    async def update_project(
        self, 
        project_id: int, 
        request: UpdateProjectRequest, 
        user_id: int
    ) -> Project:
        """
        更新项目
        
        Args:
            project_id: 项目ID
            request: 更新请求
            user_id: 用户ID
            
        Returns:
            更新后的项目对象
            
        Raises:
            NotFoundError: 项目不存在
            PermissionError: 权限不足
            ValidationError: 数据验证失败
        """
        # 1. 获取项目
        project = await self.get_project_by_id(project_id, user_id)
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")
        
        # 2. 检查更新权限
        await self._validate_update_permission(project, user_id)
        
        # 3. 验证更新数据
        await self._validate_update_data(request, project)
        
        # 4. 记录原始数据用于审计
        original_data = project.to_dict()
        
        # 5. 更新项目字段
        update_fields = request.dict(exclude_unset=True)
        for field, value in update_fields.items():
            if hasattr(project, field):
                setattr(project, field, value)
        
        # 6. 设置更新信息
        project.updated_by = user_id
        project.updated_at = datetime.utcnow()
        
        # 7. 处理状态变更的特殊逻辑
        if 'status' in update_fields:
            await self._handle_status_change(project, original_data['status'], request.status)
        
        # 8. 保存更改
        await self.db.commit()
        await self.db.refresh(project)
        
        # 9. 通知数据同步服务
        await notify_project_change(
            SyncEventType.PROJECT_UPDATED,
            project.id,
            project.id,
            project.to_dict(),
            user_id
        )
        
        logger.info(f"项目更新成功: {project.project_code} - {project.project_name}")
        return project
    
    async def delete_project(self, project_id: int, user_id: int) -> bool:
        """
        删除项目（软删除）
        
        Args:
            project_id: 项目ID
            user_id: 用户ID
            
        Returns:
            是否删除成功
            
        Raises:
            NotFoundError: 项目不存在
            PermissionError: 权限不足
            ValidationError: 不能删除
        """
        # 1. 获取项目
        project = await self.get_project_by_id(project_id, user_id)
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")
        
        # 2. 检查删除权限
        await self._validate_delete_permission(project, user_id)
        
        # 3. 检查是否可以删除
        await self._validate_can_delete(project)
        
        # 4. 执行软删除
        project.deleted_at = datetime.utcnow()
        project.updated_by = user_id
        project.updated_at = datetime.utcnow()
        
        # 5. 保存更改
        await self.db.commit()
        
        # 6. 通知数据同步服务
        await notify_project_change(
            SyncEventType.PROJECT_DELETED,
            project.id,
            project.id,
            project.to_dict(),
            user_id
        )
        
        logger.info(f"项目删除成功: {project.project_code} - {project.project_name}")
        return True
    
    # 私有方法
    async def _validate_create_permission(self, user_id: int):
        """验证创建权限"""
        # 简化权限检查 - 所有认证用户都可以创建项目
        # TODO: 实现更细粒度的权限控制
        pass
    
    async def _validate_project_data(self, request: CreateProjectRequest):
        """验证项目数据"""
        # 验证日期逻辑
        if request.planned_end_date <= request.planned_start_date:
            raise ValidationError("计划结束日期必须晚于计划开始日期")
        
        # 验证预算
        if request.budget is not None and request.budget < 0:
            raise ValidationError("项目预算不能为负数")
    
    async def _validate_project_name_unique(self, project_name: str, exclude_id: Optional[int] = None):
        """验证项目名称唯一性"""
        query = select(Project).where(
            and_(
                Project.project_name == project_name,
                Project.deleted_at.is_(None)
            )
        )
        
        if exclude_id:
            query = query.where(Project.id != exclude_id)
        
        result = await self.db.execute(query)
        existing_project = result.scalar_one_or_none()
        
        if existing_project:
            raise ValidationError(f"项目名称 '{project_name}' 已存在")
    
    async def _validate_manager_permission(self, manager_id: int):
        """验证项目经理权限"""
        # 检查用户是否存在且有项目管理权限
        result = await self.db.execute(
            select(User).where(User.id == manager_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValidationError(f"用户 {manager_id} 不存在")
        
        # 简化权限检查 - 假设所有用户都可以作为项目经理
        # TODO: 实现更细粒度的权限控制
    
    async def _generate_project_code(self) -> str:
        """生成项目编码"""
        today = datetime.now().strftime("%Y%m%d")

        # 项目编码有唯一索引，软删除数据也会占用编码；不能用未删除项目数量生成下一位。
        code_pattern = f"PROJ-{today}-%"
        result = await self.db.execute(
            select(Project.project_code).where(Project.project_code.like(code_pattern))
        )
        max_sequence = 0
        code_regex = re.compile(rf"^PROJ-{today}-(\d+)$")
        for code in result.scalars():
            match = code_regex.match(code or "")
            if match:
                max_sequence = max(max_sequence, int(match.group(1)))

        return f"PROJ-{today}-{max_sequence + 1:03d}"
    
    async def _add_project_manager_as_member(self, project_id: int, manager_id: int):
        """添加项目经理为项目成员"""
        member = ProjectMember(
            project_id=project_id,
            user_id=manager_id,
            role_in_project="PROJECT_MANAGER",
            allocation_percentage=Decimal("100.00"),
            join_date=date.today(),
            status="ACTIVE"
        )
        self.db.add(member)
    
    async def _add_test_manager_as_member(self, project_id: int, test_manager_id: int):
        """添加测试经理为项目成员"""
        member = ProjectMember(
            project_id=project_id,
            user_id=test_manager_id,
            role_in_project="TESTER",
            allocation_percentage=Decimal("100.00"),
            join_date=date.today(),
            status="ACTIVE"
        )
        self.db.add(member)
    
    async def _validate_project_access(self, project: Project, user_id: int):
        """验证项目访问权限"""
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.is_superuser:
            return

# 检查是否是项目成员或项目经理
        result = await self.db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == user_id,
                    ProjectMember.status == "ACTIVE"
                )
            )
        )
        member = result.scalar_one_or_none()
        
        # 如果不是项目成员，检查是否是项目经理
        if not member and project.project_manager_id != user_id:
            raise PermissionError("没有访问该项目的权限")
    
    async def _build_permission_filter(self, user_id: int):
        """构建权限过滤条件"""
        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.is_superuser:
            return None

# 简化权限 - 用户可以查看自己参与的项目或作为经理的项目
        subquery = select(ProjectMember.project_id).where(
            and_(
                ProjectMember.user_id == user_id,
                ProjectMember.status == "ACTIVE"
            )
        )
        
        return or_(
            Project.id.in_(subquery),
            Project.project_manager_id == user_id
        )
    
    async def _validate_update_permission(self, project: Project, user_id: int):
        """验证更新权限"""
        # 只有项目经理可以更新项目
        if project.project_manager_id != user_id:
            raise PermissionError("只有项目经理可以更新项目")
    
    async def _validate_update_data(self, request: UpdateProjectRequest, project: Project):
        """验证更新数据"""
        # 验证项目名称唯一性
        if request.project_name and request.project_name != project.project_name:
            await self._validate_project_name_unique(request.project_name, project.id)
        
        # 验证日期逻辑
        start_date = request.planned_start_date or project.planned_start_date
        end_date = request.planned_end_date or project.planned_end_date
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("计划结束日期必须晚于计划开始日期")
    
    async def _handle_status_change(self, project: Project, old_status: str, new_status: str):
        """处理状态变更的特殊逻辑"""
        if old_status == new_status:
            return
        
        # 设置实际开始时间
        if new_status == "IN_PROGRESS" and not project.actual_start_date:
            project.actual_start_date = date.today()
        
        # 设置实际结束时间
        if new_status in ["COMPLETED", "CANCELLED"] and not project.actual_end_date:
            project.actual_end_date = date.today()
    
    async def _validate_delete_permission(self, project: Project, user_id: int):
        """验证删除权限"""
        # 只有项目经理可以删除项目
        if project.project_manager_id != user_id:
            raise PermissionError("只有项目经理可以删除项目")
    
    async def _validate_can_delete(self, project: Project):
        """验证是否可以删除"""
        # 检查项目状态
        if project.status in ["IN_PROGRESS"]:
            raise ValidationError("进行中的项目不能删除，请先暂停或完成项目")
        
        # 可以添加更多删除前的检查逻辑
        # 例如：检查是否有关联的任务、测试用例等


# 依赖注入函数
async def get_project_service(db: AsyncSession = None) -> ProjectService:
    """获取项目服务实例"""
    if db is None:
        async with get_async_session() as session:
            return ProjectService(session)
    return ProjectService(db)
