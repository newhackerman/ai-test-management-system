"""
项目权限管理工具

提供项目级别的权限控制和验证功能，包括：
- 项目权限装饰器
- 细粒度权限验证
- 安全事件审计日志
"""
import functools
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.project import Project, ProjectMember
from ..models.user import User
from ..services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ProjectPermissionError(Exception):
    """项目权限错误"""
    pass


class ProjectPermissions:
    """项目权限常量"""
    
    # 项目管理权限
    PROJECT_VIEW = "project:view"
    PROJECT_CREATE = "project:create"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    PROJECT_ARCHIVE = "project:archive"
    
    # 项目成员管理权限
    MEMBER_VIEW = "project:member:view"
    MEMBER_ADD = "project:member:add"
    MEMBER_EDIT = "project:member:edit"
    MEMBER_REMOVE = "project:member:remove"
    
    # 任务管理权限
    TASK_VIEW = "project:task:view"
    TASK_CREATE = "project:task:create"
    TASK_EDIT = "project:task:edit"
    TASK_DELETE = "project:task:delete"
    TASK_ASSIGN = "project:task:assign"
    
    # 里程碑管理权限
    MILESTONE_VIEW = "project:milestone:view"
    MILESTONE_CREATE = "project:milestone:create"
    MILESTONE_EDIT = "project:milestone:edit"
    MILESTONE_DELETE = "project:milestone:delete"
    
    # 进度和统计权限
    PROGRESS_VIEW = "project:progress:view"
    STATISTICS_VIEW = "project:statistics:view"
    REPORT_GENERATE = "project:report:generate"
    
    # 风险管理权限
    RISK_VIEW = "project:risk:view"
    RISK_CREATE = "project:risk:create"
    RISK_EDIT = "project:risk:edit"
    RISK_DELETE = "project:risk:delete"


class ProjectRolePermissions:
    """项目角色权限映射"""
    
    ROLE_PERMISSIONS = {
        "ADMIN": [
            # 管理员拥有所有权限
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.PROJECT_CREATE,
            ProjectPermissions.PROJECT_EDIT,
            ProjectPermissions.PROJECT_DELETE,
            ProjectPermissions.PROJECT_ARCHIVE,
            ProjectPermissions.MEMBER_VIEW,
            ProjectPermissions.MEMBER_ADD,
            ProjectPermissions.MEMBER_EDIT,
            ProjectPermissions.MEMBER_REMOVE,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.TASK_CREATE,
            ProjectPermissions.TASK_EDIT,
            ProjectPermissions.TASK_DELETE,
            ProjectPermissions.TASK_ASSIGN,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.MILESTONE_CREATE,
            ProjectPermissions.MILESTONE_EDIT,
            ProjectPermissions.MILESTONE_DELETE,
            ProjectPermissions.PROGRESS_VIEW,
            ProjectPermissions.STATISTICS_VIEW,
            ProjectPermissions.REPORT_GENERATE,
            ProjectPermissions.RISK_VIEW,
            ProjectPermissions.RISK_CREATE,
            ProjectPermissions.RISK_EDIT,
            ProjectPermissions.RISK_DELETE,
        ],
        "PROJECT_MANAGER": [
            # 项目经理权限
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.PROJECT_EDIT,
            ProjectPermissions.MEMBER_VIEW,
            ProjectPermissions.MEMBER_ADD,
            ProjectPermissions.MEMBER_EDIT,
            ProjectPermissions.MEMBER_REMOVE,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.TASK_CREATE,
            ProjectPermissions.TASK_EDIT,
            ProjectPermissions.TASK_DELETE,
            ProjectPermissions.TASK_ASSIGN,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.MILESTONE_CREATE,
            ProjectPermissions.MILESTONE_EDIT,
            ProjectPermissions.MILESTONE_DELETE,
            ProjectPermissions.PROGRESS_VIEW,
            ProjectPermissions.STATISTICS_VIEW,
            ProjectPermissions.REPORT_GENERATE,
            ProjectPermissions.RISK_VIEW,
            ProjectPermissions.RISK_CREATE,
            ProjectPermissions.RISK_EDIT,
            ProjectPermissions.RISK_DELETE,
        ],
        "REQUIREMENT_MANAGER": [
            # 需求管理人员权限
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.MEMBER_VIEW,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.TASK_CREATE,
            ProjectPermissions.TASK_EDIT,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.PROGRESS_VIEW,
            ProjectPermissions.STATISTICS_VIEW,
            ProjectPermissions.RISK_VIEW,
            ProjectPermissions.RISK_CREATE,
        ],
        "DESIGNER": [
            # 设计人员权限
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.MEMBER_VIEW,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.TASK_CREATE,
            ProjectPermissions.TASK_EDIT,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.PROGRESS_VIEW,
            ProjectPermissions.RISK_VIEW,
        ],
        "ARCHITECT": [
            # 架构师权限
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.MEMBER_VIEW,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.TASK_CREATE,
            ProjectPermissions.TASK_EDIT,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.PROGRESS_VIEW,
            ProjectPermissions.STATISTICS_VIEW,
            ProjectPermissions.RISK_VIEW,
            ProjectPermissions.RISK_CREATE,
        ],
        "DEVELOPER": [
            # 开发人员权限
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.MEMBER_VIEW,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.TASK_EDIT,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.PROGRESS_VIEW,
            ProjectPermissions.RISK_VIEW,
        ],
        "TESTER": [
            # 测试人员权限
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.MEMBER_VIEW,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.TASK_CREATE,
            ProjectPermissions.TASK_EDIT,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.PROGRESS_VIEW,
            ProjectPermissions.STATISTICS_VIEW,
            ProjectPermissions.RISK_VIEW,
            ProjectPermissions.RISK_CREATE,
        ],
        "DEVOPS": [
            # 运维人员权限
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.MEMBER_VIEW,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.TASK_EDIT,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.PROGRESS_VIEW,
            ProjectPermissions.RISK_VIEW,
        ],
        "THIRD_PARTY": [
            # 第三方人员权限（最小权限）
            ProjectPermissions.PROJECT_VIEW,
            ProjectPermissions.TASK_VIEW,
            ProjectPermissions.MILESTONE_VIEW,
            ProjectPermissions.PROGRESS_VIEW,
        ],
    }


class ProjectPermissionChecker:
    """项目权限检查器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = AuditService(db)
    
    async def get_user_project_role(self, user_id: int, project_id: int) -> Optional[str]:
        """获取用户在项目中的角色"""
        query = select(ProjectMember).where(
            and_(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id == project_id,
                ProjectMember.status == "ACTIVE"
            )
        )
        result = await self.db.execute(query)
        member = result.scalar_one_or_none()
        
        if member:
            return member.role_in_project
        
        # 检查是否是项目经理
        project_query = select(Project).where(Project.id == project_id)
        project_result = await self.db.execute(project_query)
        project = project_result.scalar_one_or_none()
        
        if project and project.project_manager_id == user_id:
            return "PROJECT_MANAGER"
        
        return None
    
    async def check_project_permission(
        self, 
        user_id: int, 
        project_id: int, 
        permission: str,
        user_roles: Optional[List[str]] = None
    ) -> bool:
        """检查用户是否有项目权限"""
        try:
            # 检查系统管理员权限
            if user_roles and "admin" in user_roles:
                await self._log_permission_check(
                    user_id, project_id, permission, True, "系统管理员权限"
                )
                return True
            
            # 获取用户在项目中的角色
            project_role = await self.get_user_project_role(user_id, project_id)
            
            if not project_role:
                await self._log_permission_check(
                    user_id, project_id, permission, False, "用户不是项目成员"
                )
                return False
            
            # 检查角色权限
            role_permissions = ProjectRolePermissions.ROLE_PERMISSIONS.get(project_role, [])
            has_permission = permission in role_permissions
            
            await self._log_permission_check(
                user_id, project_id, permission, has_permission, 
                f"项目角色: {project_role}"
            )
            
            return has_permission
            
        except Exception as e:
            logger.error(f"权限检查失败: user_id={user_id}, project_id={project_id}, permission={permission}, error={str(e)}")
            await self._log_permission_check(
                user_id, project_id, permission, False, f"权限检查异常: {str(e)}"
            )
            return False
    
    async def check_multiple_permissions(
        self, 
        user_id: int, 
        project_id: int, 
        permissions: List[str],
        match_type: str = "all",
        user_roles: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """批量检查权限"""
        results = {}
        
        for permission in permissions:
            results[permission] = await self.check_project_permission(
                user_id, project_id, permission, user_roles
            )
        
        return results
    
    async def get_user_project_permissions(
        self, 
        user_id: int, 
        project_id: int,
        user_roles: Optional[List[str]] = None
    ) -> List[str]:
        """获取用户在项目中的所有权限"""
        # 检查系统管理员权限
        if user_roles and "admin" in user_roles:
            return ProjectRolePermissions.ROLE_PERMISSIONS["ADMIN"]
        
        # 获取用户在项目中的角色
        project_role = await self.get_user_project_role(user_id, project_id)
        
        if not project_role:
            return []
        
        return ProjectRolePermissions.ROLE_PERMISSIONS.get(project_role, [])
    
    async def _log_permission_check(
        self, 
        user_id: int, 
        project_id: int, 
        permission: str, 
        granted: bool, 
        reason: str
    ):
        """记录权限检查日志"""
        try:
            await self.audit_service.log_security_event(
                event_type="PERMISSION_CHECK",
                user_id=user_id,
                resource_type="project",
                resource_id=str(project_id),
                action=permission,
                result="GRANTED" if granted else "DENIED",
                details={
                    "permission": permission,
                    "granted": granted,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"记录权限检查日志失败: {str(e)}")


def require_project_permission(
    permission: str,
    project_id_param: str = "project_id",
    allow_project_manager: bool = True
):
    """
    项目权限装饰器
    
    Args:
        permission: 需要的权限
        project_id_param: 项目ID参数名
        allow_project_manager: 是否允许项目经理访问
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取依赖注入的参数
            current_user = None
            db = None
            project_id = None
            
            # 从kwargs中提取依赖
            for key, value in kwargs.items():
                if isinstance(value, dict) and "id" in value:
                    current_user = value
                elif hasattr(value, "execute"):  # AsyncSession
                    db = value
                elif key == project_id_param:
                    project_id = value
            
            # 如果没有找到必要参数，尝试从args中获取
            if not current_user or not db or project_id is None:
                # 这里需要根据实际的函数签名来调整
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="权限检查器配置错误：缺少必要参数"
                )
            
            # 创建权限检查器
            checker = ProjectPermissionChecker(db)
            
            # 获取用户角色
            user_roles = current_user.get("roles", [])
            
            # 检查权限
            has_permission = await checker.check_project_permission(
                user_id=current_user["id"],
                project_id=project_id,
                permission=permission,
                user_roles=user_roles
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足：需要权限 {permission}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def get_project_permission_checker(
    db: AsyncSession = Depends(get_db)
) -> ProjectPermissionChecker:
    """获取项目权限检查器依赖"""
    return ProjectPermissionChecker(db)


async def check_project_access(
    project_id: int,
    permission: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    checker: ProjectPermissionChecker = Depends(get_project_permission_checker)
) -> bool:
    """检查项目访问权限的依赖函数"""
    user_roles = current_user.get("roles", [])
    
    has_permission = await checker.check_project_permission(
        user_id=current_user["id"],
        project_id=project_id,
        permission=permission,
        user_roles=user_roles
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足：需要权限 {permission}"
        )
    
    return True


class ProjectPermissionValidator:
    """项目权限验证器"""
    
    @staticmethod
    async def validate_project_creation(
        user_id: int,
        user_roles: List[str],
        db: AsyncSession
    ) -> bool:
        """验证项目创建权限"""
        # 系统管理员可以创建项目
        if "admin" in user_roles:
            return True
        
        # 项目管理员可以创建项目
        if "project_manager" in user_roles:
            return True
        
        # 其他角色需要特殊权限
        checker = ProjectPermissionChecker(db)
        await checker._log_permission_check(
            user_id, 0, ProjectPermissions.PROJECT_CREATE, False,
            "用户角色不允许创建项目"
        )
        
        return False
    
    @staticmethod
    async def validate_project_deletion(
        user_id: int,
        project_id: int,
        user_roles: List[str],
        db: AsyncSession
    ) -> bool:
        """验证项目删除权限"""
        checker = ProjectPermissionChecker(db)
        
        # 检查删除权限
        has_permission = await checker.check_project_permission(
            user_id, project_id, ProjectPermissions.PROJECT_DELETE, user_roles
        )
        
        if not has_permission:
            return False
        
        # 额外检查：项目是否有活跃的任务或成员
        # 这里可以添加更多的业务逻辑验证
        
        return True
    
    @staticmethod
    async def validate_sensitive_operation(
        user_id: int,
        project_id: int,
        operation: str,
        user_roles: List[str],
        db: AsyncSession
    ) -> bool:
        """验证敏感操作权限"""
        checker = ProjectPermissionChecker(db)
        
        # 敏感操作需要额外的权限检查
        sensitive_operations = {
            "archive_project": ProjectPermissions.PROJECT_ARCHIVE,
            "remove_member": ProjectPermissions.MEMBER_REMOVE,
            "delete_task": ProjectPermissions.TASK_DELETE,
            "delete_milestone": ProjectPermissions.MILESTONE_DELETE,
        }
        
        required_permission = sensitive_operations.get(operation)
        if not required_permission:
            return False
        
        has_permission = await checker.check_project_permission(
            user_id, project_id, required_permission, user_roles
        )
        
        # 记录敏感操作尝试
        await checker._log_permission_check(
            user_id, project_id, f"SENSITIVE_OPERATION:{operation}", 
            has_permission, f"敏感操作权限检查"
        )
        
        return has_permission