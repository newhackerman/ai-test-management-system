"""
用户角色权限管理API - 基于zentao模式的权限控制
提供用户角色分配、权限管理、审计日志等功能
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
import logging

from ...core.database import get_async_session
from ...core.user_role_manager import UserRoleManager
from ...services.permission import PermissionService
from ...services.auth_dependencies import get_current_user, get_current_active_user
from ...models.user import User
from ...models.role import Role
from ...models.permission import Permission
# from ...decorators.permission import require_permission  # Temporarily disabled
from ...schemas.auth import UserRoleAssignmentRequest, UserRoleResponse, BatchRoleAssignmentRequest
from ...schemas.user_role_management import RoleCreateRequest, RoleUpdateRequest, PermissionCreateRequest
from ...utils.error_responses import bad_request_error, not_found_error, forbidden_error

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/user-role-management", tags=["用户角色权限管理"])


async def get_user_role_manager(session: AsyncSession = Depends(get_async_session)) -> UserRoleManager:
    """获取用户角色管理器实例"""
    return UserRoleManager(session)


async def get_permission_service(session: AsyncSession = Depends(get_async_session)) -> PermissionService:
    """获取权限服务实例"""
    return PermissionService(session)


# 用户角色管理
@router.post("/users/{user_id}/roles/{role_id}/assign")
async def assign_role_to_user(
    user_id: int,
    role_id: int,
    reason: Optional[str] = Body(None, description="分配原因"),
    current_user: User = Depends(get_current_active_user),
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """为用户分配角色"""
    try:
        success, error = await role_manager.assign_role_to_user(
            user_id=user_id,
            role_id=role_id,
            assigned_by=current_user.id,
            reason=reason
        )
        
        if not success:
            raise bad_request_error(error or "角色分配失败")
        
        return {
            "success": True,
            "message": "角色分配成功",
            "data": {
                "user_id": user_id,
                "role_id": role_id,
                "assigned_by": current_user.id,
                "assigned_at": "now"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分配角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="角色分配失败"
        )


@router.delete("/users/{user_id}/roles/{role_id}")
async def revoke_role_from_user(
    user_id: int,
    role_id: int,
    reason: Optional[str] = Body(None, description="撤销原因"),
    current_user: User = Depends(get_current_active_user),
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """撤销用户角色"""
    try:
        success, error = await role_manager.revoke_role_from_user(
            user_id=user_id,
            role_id=role_id,
            revoked_by=current_user.id,
            reason=reason
        )
        
        if not success:
            raise bad_request_error(error or "角色撤销失败")
        
        return {
            "success": True,
            "message": "角色撤销成功",
            "data": {
                "user_id": user_id,
                "role_id": role_id,
                "revoked_by": current_user.id,
                "revoked_at": "now"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"撤销角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="角色撤销失败"
        )


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: int,
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """获取用户的所有角色"""
    try:
        roles = await role_manager.get_user_roles(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "roles": [
                    {
                        "id": role.id,
                        "code": role.code,
                        "name": role.name,
                        "description": role.description,
                        "priority": role.priority,
                        "is_system_role": role.is_system_role
                    }
                    for role in roles
                ],
                "total": len(roles)
            }
        }
        
    except Exception as e:
        logger.error(f"获取用户角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户角色失败"
        )


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: int,
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """获取用户的所有权限"""
    try:
        permissions = await role_manager.get_user_permissions(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "permissions": list(permissions),
                "total": len(permissions)
            }
        }
        
    except Exception as e:
        logger.error(f"获取用户权限失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户权限失败"
        )


@router.get("/users/{user_id}/data-scope")
async def get_user_data_scope(
    user_id: int,
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """获取用户的数据权限范围"""
    try:
        data_scope = await role_manager.get_user_data_scope(user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "data_scope": data_scope
            }
        }
        
    except Exception as e:
        logger.error(f"获取用户数据权限范围失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户数据权限范围失败"
        )


@router.post("/users/batch-assign-roles")
async def batch_assign_roles(
    request: BatchRoleAssignmentRequest,
    current_user: User = Depends(get_current_active_user),
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """批量分配角色"""
    try:
        results = await role_manager.batch_assign_roles(
            user_ids=request.user_ids,
            role_ids=request.role_ids,
            assigned_by=current_user.id,
            reason=request.reason
        )
        
        return {
            "success": True,
            "message": "批量角色分配完成",
            "data": results
        }
        
    except Exception as e:
        logger.error(f"批量分配角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量分配角色失败"
        )


# 角色管理
@router.get("/roles")
async def get_roles(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    is_system_role: Optional[bool] = Query(None, description="是否系统角色"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取角色列表"""
    try:
        roles, total = permission_service.get_roles(
            page=page,
            size=size,
            search=search,
            is_system_role=is_system_role,
            is_active=is_active
        )
        
        return {
            "success": True,
            "data": {
                "items": [
                    {
                        "id": role.id,
                        "code": role.code,
                        "name": role.name,
                        "description": role.description,
                        "priority": role.priority,
                        "is_system_role": role.is_system_role,
                        "is_active": role.is_active,
                        "user_count": role.user_count,
                        "permission_count": role.permission_count,
                        "created_at": role.created_at.isoformat() if role.created_at else None
                    }
                    for role in roles
                ],
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
        }
        
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色列表失败"
        )


@router.post("/roles")
async def create_role(
    request: RoleCreateRequest,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """创建角色"""
    try:
        role, error = permission_service.create_role(
            name=request.name,
            code=request.code,
            description=request.description,
            is_system_role=request.is_system_role,
            priority=request.priority,
            permission_ids=request.permission_ids,
            created_by=current_user.id
        )
        
        if not role:
            raise bad_request_error(error or "角色创建失败")
        
        return {
            "success": True,
            "message": "角色创建成功",
            "data": {
                "id": role.id,
                "code": role.code,
                "name": role.name,
                "description": role.description,
                "priority": role.priority,
                "is_system_role": role.is_system_role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="角色创建失败"
        )


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    request: RoleUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """更新角色"""
    try:
        role, error = permission_service.update_role(
            role_id=role_id,
            name=request.name,
            code=request.code,
            description=request.description,
            is_active=request.is_active,
            priority=request.priority,
            permission_ids=request.permission_ids,
            updated_by=current_user.id
        )
        
        if not role:
            raise bad_request_error(error or "角色更新失败")
        
        return {
            "success": True,
            "message": "角色更新成功",
            "data": {
                "id": role.id,
                "code": role.code,
                "name": role.name,
                "description": role.description,
                "priority": role.priority,
                "is_active": role.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="角色更新失败"
        )


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """删除角色"""
    try:
        success = permission_service.delete_role(
            role_id=role_id,
            deleted_by=current_user.id
        )
        
        if not success:
            raise bad_request_error("角色删除失败")
        
        return {
            "success": True,
            "message": "角色删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="角色删除失败"
        )


@router.get("/roles/{role_id}/hierarchy")
async def get_role_hierarchy(
    role_id: int,
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """获取角色层级关系"""
    try:
        hierarchy = await role_manager.get_role_hierarchy(role_id)
        
        return {
            "success": True,
            "data": hierarchy
        }
        
    except Exception as e:
        logger.error(f"获取角色层级失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色层级失败"
        )


# 权限管理
@router.get("/permissions")
async def get_permissions(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    module: Optional[str] = Query(None, description="权限模块"),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取权限列表"""
    try:
        permissions, total = permission_service.get_permissions(
            page=page,
            size=size,
            search=search,
            module=module
        )
        
        return {
            "success": True,
            "data": {
                "items": [
                    {
                        "id": perm.id,
                        "code": perm.code,
                        "name": perm.name,
                        "description": perm.description,
                        "module": perm.module,
                        "action": perm.action,
                        "resource": perm.resource,
                        "permission_type": perm.permission_type.value if perm.permission_type else None,
                        "is_active": perm.is_active,
                        "created_at": perm.created_at.isoformat() if perm.created_at else None
                    }
                    for perm in permissions
                ],
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
        }
        
    except Exception as e:
        logger.error(f"获取权限列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取权限列表失败"
        )


@router.get("/permissions/modules")
async def get_permission_modules(
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取权限模块列表"""
    try:
        modules = permission_service.get_permission_modules()
        
        return {
            "success": True,
            "data": {
                "modules": modules,
                "total": len(modules)
            }
        }
        
    except Exception as e:
        logger.error(f"获取权限模块失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取权限模块失败"
        )


@router.post("/permissions")
async def create_permission(
    request: PermissionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """创建权限"""
    try:
        permission, error = permission_service.create_permission(
            name=request.name,
            code=request.code,
            module=request.module,
            action=request.action,
            resource=request.resource,
            description=request.description,
            created_by=current_user.id
        )
        
        if not permission:
            raise bad_request_error(error or "权限创建失败")
        
        return {
            "success": True,
            "message": "权限创建成功",
            "data": {
                "id": permission.id,
                "code": permission.code,
                "name": permission.name,
                "module": permission.module,
                "action": permission.action,
                "resource": permission.resource
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建权限失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="权限创建失败"
        )


# 权限检查
@router.post("/check-permission")
async def check_user_permission(
    permission_code: str = Body(..., description="权限代码"),
    resource_id: Optional[str] = Body(None, description="资源ID"),
    current_user: User = Depends(get_current_active_user),
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """检查用户权限"""
    try:
        has_permission = await role_manager.check_user_permission(
            user_id=current_user.id,
            permission_code=permission_code,
            resource_id=resource_id
        )
        
        return {
            "success": True,
            "data": {
                "user_id": current_user.id,
                "permission_code": permission_code,
                "resource_id": resource_id,
                "has_permission": has_permission
            }
        }
        
    except Exception as e:
        logger.error(f"权限检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="权限检查失败"
        )


@router.post("/check-role")
async def check_user_role(
    role_code: str = Body(..., description="角色代码"),
    current_user: User = Depends(get_current_active_user),
    role_manager: UserRoleManager = Depends(get_user_role_manager)
):
    """检查用户角色"""
    try:
        has_role = await role_manager.check_user_role(
            user_id=current_user.id,
            role_code=role_code
        )
        
        return {
            "success": True,
            "data": {
                "user_id": current_user.id,
                "role_code": role_code,
                "has_role": has_role
            }
        }
        
    except Exception as e:
        logger.error(f"角色检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="角色检查失败"
        )