"""
仪表板权限控制服务

集成主系统RBAC权限体系，实现角色级别的仪表板访问控制、组件级别的权限验证和数据级别的访问权限控制
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime
import logging
from enum import Enum

from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import Permission, RolePermission
from ..models.dashboard_config import DashboardConfig
from ..models.widget_definition import WidgetDefinition
from ..models.color_scheme import ColorScheme, UserColorPreference
from ..models.project import Project, ProjectMember
from ..services.permission import PermissionService
from ..core.database import get_db

logger = logging.getLogger(__name__)

class DashboardPermissionType(Enum):
    """仪表板权限类型枚举"""
    # 仪表板级别权限
    DASHBOARD_VIEW = "dashboard:view"  # 查看仪表板
    DASHBOARD_EDIT = "dashboard:edit"  # 编辑仪表板布局
    DASHBOARD_CREATE = "dashboard:create"  # 创建自定义仪表板
    DASHBOARD_DELETE = "dashboard:delete"  # 删除仪表板
    DASHBOARD_SHARE = "dashboard:share"  # 分享仪表板
    
    # 组件级别权限
    WIDGET_VIEW = "widget:view"  # 查看组件
    WIDGET_ADD = "widget:add"  # 添加组件
    WIDGET_REMOVE = "widget:remove"  # 移除组件
    WIDGET_CONFIG = "widget:config"  # 配置组件
    WIDGET_DATA_ACCESS = "widget:data_access"  # 访问组件数据
    
    # 数据级别权限
    DATA_PROJECT_ALL = "data:project:all"  # 访问所有项目数据
    DATA_PROJECT_ASSIGNED = "data:project:assigned"  # 访问分配的项目数据
    DATA_PROJECT_OWNED = "data:project:owned"  # 访问拥有的项目数据
    DATA_REQUIREMENT_ALL = "data:requirement:all"  # 访问所有需求数据
    DATA_REQUIREMENT_ASSIGNED = "data:requirement:assigned"  # 访问分配的需求数据
    DATA_TEST_ALL = "data:test:all"  # 访问所有测试数据
    DATA_TEST_ASSIGNED = "data:test:assigned"  # 访问分配的测试数据
    DATA_SYSTEM_METRICS = "data:system:metrics"  # 访问系统指标数据
    
    # 配色方案权限
    COLOR_SCHEME_VIEW = "color_scheme:view"  # 查看配色方案
    COLOR_SCHEME_CREATE = "color_scheme:create"  # 创建配色方案
    COLOR_SCHEME_EDIT = "color_scheme:edit"  # 编辑配色方案
    COLOR_SCHEME_DELETE = "color_scheme:delete"  # 删除配色方案
    COLOR_SCHEME_SHARE = "color_scheme:share"  # 分享配色方案

class RoleType(Enum):
    """角色类型枚举"""
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    REQUIREMENT_MANAGER = "REQUIREMENT_MANAGER"
    DESIGNER = "DESIGNER"
    ARCHITECT = "ARCHITECT"
    DEVELOPER = "DEVELOPER"
    TESTER = "TESTER"
    DEVOPS = "DEVOPS"
    THIRD_PARTY = "THIRD_PARTY"

class DashboardPermissionService:
    """仪表板权限控制服务"""
    
    def __init__(self, db: Session, permission_service: PermissionService = None):
        self.db = db
        self.permission_service = permission_service or PermissionService(db)
        
        # 角色权限映射
        self.role_permissions = self._initialize_role_permissions()
    
    def _initialize_role_permissions(self) -> Dict[RoleType, Set[DashboardPermissionType]]:
        """初始化角色权限映射"""
        return {
            RoleType.ADMIN: {
                # 管理员拥有所有权限
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.DASHBOARD_EDIT,
                DashboardPermissionType.DASHBOARD_CREATE,
                DashboardPermissionType.DASHBOARD_DELETE,
                DashboardPermissionType.DASHBOARD_SHARE,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.WIDGET_ADD,
                DashboardPermissionType.WIDGET_REMOVE,
                DashboardPermissionType.WIDGET_CONFIG,
                DashboardPermissionType.WIDGET_DATA_ACCESS,
                DashboardPermissionType.DATA_PROJECT_ALL,
                DashboardPermissionType.DATA_REQUIREMENT_ALL,
                DashboardPermissionType.DATA_TEST_ALL,
                DashboardPermissionType.DATA_SYSTEM_METRICS,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
                DashboardPermissionType.COLOR_SCHEME_CREATE,
                DashboardPermissionType.COLOR_SCHEME_EDIT,
                DashboardPermissionType.COLOR_SCHEME_DELETE,
                DashboardPermissionType.COLOR_SCHEME_SHARE,
            },
            
            RoleType.PROJECT_MANAGER: {
                # 项目管理员权限
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.DASHBOARD_EDIT,
                DashboardPermissionType.DASHBOARD_CREATE,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.WIDGET_ADD,
                DashboardPermissionType.WIDGET_REMOVE,
                DashboardPermissionType.WIDGET_CONFIG,
                DashboardPermissionType.WIDGET_DATA_ACCESS,
                DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                DashboardPermissionType.DATA_REQUIREMENT_ASSIGNED,
                DashboardPermissionType.DATA_TEST_ASSIGNED,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
                DashboardPermissionType.COLOR_SCHEME_CREATE,
                DashboardPermissionType.COLOR_SCHEME_SHARE,
            },
            
            RoleType.REQUIREMENT_MANAGER: {
                # 需求管理员权限
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.DASHBOARD_EDIT,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.WIDGET_ADD,
                DashboardPermissionType.WIDGET_CONFIG,
                DashboardPermissionType.WIDGET_DATA_ACCESS,
                DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                DashboardPermissionType.DATA_REQUIREMENT_ALL,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
                DashboardPermissionType.COLOR_SCHEME_CREATE,
            },
            
            RoleType.DESIGNER: {
                # 设计人员权限
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.DASHBOARD_EDIT,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.WIDGET_ADD,
                DashboardPermissionType.WIDGET_CONFIG,
                DashboardPermissionType.WIDGET_DATA_ACCESS,
                DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                DashboardPermissionType.DATA_REQUIREMENT_ASSIGNED,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
                DashboardPermissionType.COLOR_SCHEME_CREATE,
                DashboardPermissionType.COLOR_SCHEME_EDIT,
                DashboardPermissionType.COLOR_SCHEME_SHARE,
            },
            
            RoleType.ARCHITECT: {
                # 架构师权限
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.DASHBOARD_EDIT,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.WIDGET_ADD,
                DashboardPermissionType.WIDGET_CONFIG,
                DashboardPermissionType.WIDGET_DATA_ACCESS,
                DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                DashboardPermissionType.DATA_SYSTEM_METRICS,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
                DashboardPermissionType.COLOR_SCHEME_CREATE,
            },
            
            RoleType.DEVELOPER: {
                # 开发人员权限
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.DASHBOARD_EDIT,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.WIDGET_ADD,
                DashboardPermissionType.WIDGET_CONFIG,
                DashboardPermissionType.WIDGET_DATA_ACCESS,
                DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
                DashboardPermissionType.COLOR_SCHEME_CREATE,
            },
            
            RoleType.TESTER: {
                # 测试人员权限
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.DASHBOARD_EDIT,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.WIDGET_ADD,
                DashboardPermissionType.WIDGET_CONFIG,
                DashboardPermissionType.WIDGET_DATA_ACCESS,
                DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                DashboardPermissionType.DATA_TEST_ALL,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
                DashboardPermissionType.COLOR_SCHEME_CREATE,
            },
            
            RoleType.DEVOPS: {
                # 运维人员权限
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.DASHBOARD_EDIT,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.WIDGET_ADD,
                DashboardPermissionType.WIDGET_CONFIG,
                DashboardPermissionType.WIDGET_DATA_ACCESS,
                DashboardPermissionType.DATA_SYSTEM_METRICS,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
            },
            
            RoleType.THIRD_PARTY: {
                # 第三方人员权限（受限）
                DashboardPermissionType.DASHBOARD_VIEW,
                DashboardPermissionType.WIDGET_VIEW,
                DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                DashboardPermissionType.COLOR_SCHEME_VIEW,
            }
        }
    
    async def check_dashboard_permission(
        self, 
        user_id: int, 
        permission: DashboardPermissionType,
        resource_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        检查用户是否具有指定的仪表板权限
        
        Args:
            user_id: 用户ID
            permission: 权限类型
            resource_id: 资源ID（如仪表板ID、组件ID等）
            context: 上下文信息（如项目ID等）
            
        Returns:
            bool: 是否具有权限
        """
        try:
            # 获取用户信息
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return False
            
            # 获取用户角色
            user_roles = await self._get_user_roles(user_id)
            if not user_roles:
                logger.warning(f"No roles found for user {user_id}")
                return False
            
            # 检查角色权限
            for role_type in user_roles:
                if await self._check_role_permission(role_type, permission, user_id, resource_id, context):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking dashboard permission: {str(e)}")
            return False
    
    async def check_widget_access(
        self, 
        user_id: int, 
        widget_type: str,
        action: str = "view"
    ) -> bool:
        """
        检查用户是否可以访问指定组件
        
        Args:
            user_id: 用户ID
            widget_type: 组件类型
            action: 操作类型 (view, add, remove, config)
            
        Returns:
            bool: 是否可以访问
        """
        try:
            # 获取组件定义
            widget_def = self.db.query(WidgetDefinition).filter(
                WidgetDefinition.widget_type == widget_type
            ).first()
            
            if not widget_def:
                logger.warning(f"Widget definition not found: {widget_type}")
                return False
            
            # 检查组件是否激活
            if not widget_def.is_active:
                return False
            
            # 获取用户角色
            user_roles = await self._get_user_roles(user_id)
            
            # 检查组件支持的角色
            if widget_def.supported_roles:
                supported_roles = set(widget_def.supported_roles)
                user_role_names = {role.value for role in user_roles}
                
                if not supported_roles.intersection(user_role_names):
                    return False
            
            # 检查具体操作权限
            permission_map = {
                "view": DashboardPermissionType.WIDGET_VIEW,
                "add": DashboardPermissionType.WIDGET_ADD,
                "remove": DashboardPermissionType.WIDGET_REMOVE,
                "config": DashboardPermissionType.WIDGET_CONFIG
            }
            
            required_permission = permission_map.get(action, DashboardPermissionType.WIDGET_VIEW)
            
            return await self.check_dashboard_permission(user_id, required_permission)
            
        except Exception as e:
            logger.error(f"Error checking widget access: {str(e)}")
            return False
    
    async def check_data_access(
        self, 
        user_id: int, 
        data_type: str,
        project_ids: Optional[List[int]] = None
    ) -> Tuple[bool, List[int]]:
        """
        检查用户的数据访问权限
        
        Args:
            user_id: 用户ID
            data_type: 数据类型 (project, requirement, test, system)
            project_ids: 请求访问的项目ID列表
            
        Returns:
            Tuple[bool, List[int]]: (是否有权限, 可访问的项目ID列表)
        """
        try:
            # 获取用户角色
            user_roles = await self._get_user_roles(user_id)
            
            # 检查全局数据访问权限
            global_permissions = {
                "project": DashboardPermissionType.DATA_PROJECT_ALL,
                "requirement": DashboardPermissionType.DATA_REQUIREMENT_ALL,
                "test": DashboardPermissionType.DATA_TEST_ALL,
                "system": DashboardPermissionType.DATA_SYSTEM_METRICS
            }
            
            global_permission = global_permissions.get(data_type)
            if global_permission:
                for role_type in user_roles:
                    if global_permission in self.role_permissions.get(role_type, set()):
                        # 有全局权限，返回所有请求的项目
                        if project_ids:
                            return True, project_ids
                        else:
                            # 获取所有项目
                            all_projects = self.db.query(Project.id).filter(Project.is_active == True).all()
                            return True, [p.id for p in all_projects]
            
            # 检查分配的项目权限
            assigned_permissions = {
                "project": DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                "requirement": DashboardPermissionType.DATA_REQUIREMENT_ASSIGNED,
                "test": DashboardPermissionType.DATA_TEST_ASSIGNED
            }
            
            assigned_permission = assigned_permissions.get(data_type)
            if assigned_permission:
                for role_type in user_roles:
                    if assigned_permission in self.role_permissions.get(role_type, set()):
                        # 获取用户分配的项目
                        accessible_projects = await self._get_user_accessible_projects(user_id)
                        
                        if project_ids:
                            # 过滤请求的项目
                            filtered_projects = [pid for pid in project_ids if pid in accessible_projects]
                            return len(filtered_projects) > 0, filtered_projects
                        else:
                            return len(accessible_projects) > 0, accessible_projects
            
            return False, []
            
        except Exception as e:
            logger.error(f"Error checking data access: {str(e)}")
            return False, []
    
    async def check_color_scheme_permission(
        self, 
        user_id: int, 
        scheme_id: int,
        action: str = "view"
    ) -> bool:
        """
        检查用户对配色方案的权限
        
        Args:
            user_id: 用户ID
            scheme_id: 配色方案ID
            action: 操作类型 (view, create, edit, delete, share)
            
        Returns:
            bool: 是否有权限
        """
        try:
            # 获取配色方案
            scheme = self.db.query(ColorScheme).filter(
                and_(
                    ColorScheme.id == scheme_id,
                    ColorScheme.is_active == True
                )
            ).first()
            
            if not scheme:
                return False
            
            # 检查基本权限
            permission_map = {
                "view": DashboardPermissionType.COLOR_SCHEME_VIEW,
                "create": DashboardPermissionType.COLOR_SCHEME_CREATE,
                "edit": DashboardPermissionType.COLOR_SCHEME_EDIT,
                "delete": DashboardPermissionType.COLOR_SCHEME_DELETE,
                "share": DashboardPermissionType.COLOR_SCHEME_SHARE
            }
            
            required_permission = permission_map.get(action, DashboardPermissionType.COLOR_SCHEME_VIEW)
            
            # 检查基础权限
            if not await self.check_dashboard_permission(user_id, required_permission):
                return False
            
            # 对于编辑和删除操作，需要额外检查所有权
            if action in ["edit", "delete"]:
                # 只有创建者或管理员可以编辑/删除
                if scheme.created_by != user_id:
                    # 检查是否是管理员
                    user_roles = await self._get_user_roles(user_id)
                    if RoleType.ADMIN not in user_roles:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking color scheme permission: {str(e)}")
            return False
    
    async def get_user_dashboard_permissions(self, user_id: int) -> Dict[str, bool]:
        """
        获取用户的所有仪表板权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, bool]: 权限映射
        """
        try:
            permissions = {}
            
            # 检查所有权限类型
            for permission in DashboardPermissionType:
                permissions[permission.value] = await self.check_dashboard_permission(user_id, permission)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting user dashboard permissions: {str(e)}")
            return {}
    
    async def filter_accessible_widgets(
        self, 
        user_id: int, 
        widget_types: List[str]
    ) -> List[str]:
        """
        过滤用户可访问的组件类型
        
        Args:
            user_id: 用户ID
            widget_types: 组件类型列表
            
        Returns:
            List[str]: 可访问的组件类型列表
        """
        try:
            accessible_widgets = []
            
            for widget_type in widget_types:
                if await self.check_widget_access(user_id, widget_type, "view"):
                    accessible_widgets.append(widget_type)
            
            return accessible_widgets
            
        except Exception as e:
            logger.error(f"Error filtering accessible widgets: {str(e)}")
            return []
    
    # 私有辅助方法
    
    async def _get_user_roles(self, user_id: int) -> List[RoleType]:
        """获取用户角色列表"""
        try:
            # 这里应该从数据库查询用户角色
            # 简化处理，假设用户表有role字段
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return []
            
            # 如果用户有role属性，转换为RoleType
            if hasattr(user, 'role') and user.role:
                try:
                    return [RoleType(user.role)]
                except ValueError:
                    logger.warning(f"Invalid role type: {user.role}")
                    return []
            
            # 如果没有role属性，查询用户角色关联表
            user_roles = self.db.query(UserRole).filter(UserRole.user_id == user_id).all()
            role_types = []
            
            for user_role in user_roles:
                role = self.db.query(Role).filter(Role.id == user_role.role_id).first()
                if role and role.code:
                    try:
                        role_types.append(RoleType(role.code))
                    except ValueError:
                        logger.warning(f"Invalid role code: {role.code}")
            
            return role_types
            
        except Exception as e:
            logger.error(f"Error getting user roles: {str(e)}")
            return []
    
    async def _check_role_permission(
        self, 
        role_type: RoleType, 
        permission: DashboardPermissionType,
        user_id: int,
        resource_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """检查角色是否具有指定权限"""
        try:
            # 检查基础角色权限
            role_perms = self.role_permissions.get(role_type, set())
            if permission not in role_perms:
                return False
            
            # 对于数据访问权限，需要额外检查项目分配
            if permission in [
                DashboardPermissionType.DATA_PROJECT_ASSIGNED,
                DashboardPermissionType.DATA_REQUIREMENT_ASSIGNED,
                DashboardPermissionType.DATA_TEST_ASSIGNED
            ]:
                # 检查用户是否分配到相关项目
                if context and "project_id" in context:
                    project_id = context["project_id"]
                    return await self._check_project_assignment(user_id, project_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking role permission: {str(e)}")
            return False
    
    async def _get_user_accessible_projects(self, user_id: int) -> List[int]:
        """获取用户可访问的项目ID列表"""
        try:
            # 查询用户作为成员的项目
            project_members = self.db.query(ProjectMember).filter(
                ProjectMember.user_id == user_id
            ).all()
            
            project_ids = [pm.project_id for pm in project_members]
            
            # 查询用户创建的项目
            owned_projects = self.db.query(Project).filter(
                and_(
                    Project.created_by == user_id,
                    Project.is_active == True
                )
            ).all()
            
            project_ids.extend([p.id for p in owned_projects])
            
            # 去重
            return list(set(project_ids))
            
        except Exception as e:
            logger.error(f"Error getting user accessible projects: {str(e)}")
            return []
    
    async def _check_project_assignment(self, user_id: int, project_id: int) -> bool:
        """检查用户是否分配到指定项目"""
        try:
            # 检查项目成员关系
            member = self.db.query(ProjectMember).filter(
                and_(
                    ProjectMember.user_id == user_id,
                    ProjectMember.project_id == project_id
                )
            ).first()
            
            if member:
                return True
            
            # 检查是否是项目创建者
            project = self.db.query(Project).filter(
                and_(
                    Project.id == project_id,
                    Project.created_by == user_id,
                    Project.is_active == True
                )
            ).first()
            
            return project is not None
            
        except Exception as e:
            logger.error(f"Error checking project assignment: {str(e)}")
            return False
    
    async def initialize_dashboard_permissions(self) -> bool:
        """
        初始化仪表板权限系统
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 创建仪表板相关权限
            dashboard_permissions = [
                ("dashboard:view", "查看仪表板", "允许用户查看仪表板"),
                ("dashboard:edit", "编辑仪表板", "允许用户编辑仪表板布局"),
                ("dashboard:create", "创建仪表板", "允许用户创建自定义仪表板"),
                ("dashboard:delete", "删除仪表板", "允许用户删除仪表板"),
                ("dashboard:share", "分享仪表板", "允许用户分享仪表板"),
                ("widget:view", "查看组件", "允许用户查看仪表板组件"),
                ("widget:add", "添加组件", "允许用户添加仪表板组件"),
                ("widget:remove", "移除组件", "允许用户移除仪表板组件"),
                ("widget:config", "配置组件", "允许用户配置仪表板组件"),
                ("widget:data_access", "访问组件数据", "允许用户访问组件数据"),
                ("data:project:all", "访问所有项目数据", "允许用户访问所有项目的数据"),
                ("data:project:assigned", "访问分配项目数据", "允许用户访问分配项目的数据"),
                ("data:requirement:all", "访问所有需求数据", "允许用户访问所有需求数据"),
                ("data:requirement:assigned", "访问分配需求数据", "允许用户访问分配需求的数据"),
                ("data:test:all", "访问所有测试数据", "允许用户访问所有测试数据"),
                ("data:test:assigned", "访问分配测试数据", "允许用户访问分配测试的数据"),
                ("data:system:metrics", "访问系统指标", "允许用户访问系统监控指标"),
                ("color_scheme:view", "查看配色方案", "允许用户查看配色方案"),
                ("color_scheme:create", "创建配色方案", "允许用户创建配色方案"),
                ("color_scheme:edit", "编辑配色方案", "允许用户编辑配色方案"),
                ("color_scheme:delete", "删除配色方案", "允许用户删除配色方案"),
                ("color_scheme:share", "分享配色方案", "允许用户分享配色方案"),
            ]
            
            for code, name, description in dashboard_permissions:
                # 检查权限是否已存在
                existing_permission = self.db.query(Permission).filter(
                    Permission.code == code
                ).first()
                
                if not existing_permission:
                    permission = Permission(
                        code=code,
                        name=name,
                        description=description,
                        resource_type="dashboard"
                    )
                    self.db.add(permission)
            
            self.db.commit()
            
            logger.info("Dashboard permissions initialized successfully")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error initializing dashboard permissions: {str(e)}")
            return False