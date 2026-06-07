"""
仪表板权限装饰器

提供用于API端点的权限检查装饰器
"""

from functools import wraps
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.auth import get_current_user
from ..services.dashboard_permission_service import DashboardPermissionService, DashboardPermissionType
from ..models.user import User

def require_dashboard_permission(
    permission: DashboardPermissionType,
    resource_param: Optional[str] = None,
    context_params: Optional[List[str]] = None
):
    """
    仪表板权限检查装饰器
    
    Args:
        permission: 需要的权限类型
        resource_param: 资源参数名（如 'dashboard_id', 'widget_id'）
        context_params: 上下文参数名列表（如 ['project_id']）
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户
            current_user = None
            db = None
            
            # 从kwargs中提取依赖
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, 'query'):  # Session对象
                    db = value
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户未认证"
                )
            
            if not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="数据库连接错误"
                )
            
            # 创建权限服务
            permission_service = DashboardPermissionService(db)
            
            # 提取资源ID
            resource_id = None
            if resource_param and resource_param in kwargs:
                resource_id = kwargs[resource_param]
            
            # 提取上下文信息
            context = {}
            if context_params:
                for param in context_params:
                    if param in kwargs:
                        context[param] = kwargs[param]
            
            # 检查权限
            has_permission = await permission_service.check_dashboard_permission(
                user_id=current_user.id,
                permission=permission,
                resource_id=resource_id,
                context=context if context else None
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足：需要 {permission.value} 权限"
                )
            
            # 执行原函数
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_widget_access(action: str = "view"):
    """
    组件访问权限检查装饰器
    
    Args:
        action: 操作类型 (view, add, remove, config)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户和数据库连接
            current_user = None
            db = None
            widget_type = None
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, 'query'):
                    db = value
                elif key == 'widget_type':
                    widget_type = value
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="认证信息缺失"
                )
            
            if not widget_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="组件类型参数缺失"
                )
            
            # 创建权限服务
            permission_service = DashboardPermissionService(db)
            
            # 检查组件访问权限
            has_access = await permission_service.check_widget_access(
                user_id=current_user.id,
                widget_type=widget_type,
                action=action
            )
            
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"无权限{action}组件: {widget_type}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_data_access(data_type: str):
    """
    数据访问权限检查装饰器
    
    Args:
        data_type: 数据类型 (project, requirement, test, system)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户和数据库连接
            current_user = None
            db = None
            project_ids = None
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, 'query'):
                    db = value
                elif key == 'project_ids':
                    project_ids = value
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="认证信息缺失"
                )
            
            # 创建权限服务
            permission_service = DashboardPermissionService(db)
            
            # 检查数据访问权限
            has_access, accessible_projects = await permission_service.check_data_access(
                user_id=current_user.id,
                data_type=data_type,
                project_ids=project_ids
            )
            
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"无权限访问{data_type}数据"
                )
            
            # 将可访问的项目ID添加到kwargs中，供函数使用
            kwargs['accessible_project_ids'] = accessible_projects
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_color_scheme_permission(action: str = "view"):
    """
    配色方案权限检查装饰器
    
    Args:
        action: 操作类型 (view, create, edit, delete, share)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户和数据库连接
            current_user = None
            db = None
            scheme_id = None
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, 'query'):
                    db = value
                elif key == 'scheme_id':
                    scheme_id = value
            
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="认证信息缺失"
                )
            
            # 对于创建操作，不需要scheme_id
            if action != "create" and not scheme_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="配色方案ID参数缺失"
                )
            
            # 创建权限服务
            permission_service = DashboardPermissionService(db)
            
            # 检查配色方案权限
            if action == "create":
                # 创建操作只需要检查基础权限
                has_permission = await permission_service.check_dashboard_permission(
                    user_id=current_user.id,
                    permission=DashboardPermissionType.COLOR_SCHEME_CREATE
                )
            else:
                # 其他操作需要检查具体方案权限
                has_permission = await permission_service.check_color_scheme_permission(
                    user_id=current_user.id,
                    scheme_id=scheme_id,
                    action=action
                )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"无权限{action}配色方案"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# 便捷的权限检查函数

async def check_dashboard_view_permission(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """检查仪表板查看权限"""
    permission_service = DashboardPermissionService(db)
    return await permission_service.check_dashboard_permission(
        current_user.id, 
        DashboardPermissionType.DASHBOARD_VIEW
    )

async def check_dashboard_edit_permission(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> bool:
    """检查仪表板编辑权限"""
    permission_service = DashboardPermissionService(db)
    return await permission_service.check_dashboard_permission(
        current_user.id, 
        DashboardPermissionType.DASHBOARD_EDIT
    )

async def get_user_accessible_widgets(
    widget_types: List[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[str]:
    """获取用户可访问的组件类型列表"""
    permission_service = DashboardPermissionService(db)
    return await permission_service.filter_accessible_widgets(
        current_user.id, 
        widget_types
    )

async def get_user_dashboard_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, bool]:
    """获取用户的所有仪表板权限"""
    permission_service = DashboardPermissionService(db)
    return await permission_service.get_user_dashboard_permissions(current_user.id)