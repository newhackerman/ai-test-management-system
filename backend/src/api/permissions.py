"""
权限管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging

from ..core.database import get_async_session
from ..services.permission_service import PermissionService
from ..models.user import User
from ..schemas.permission import (
    PermissionResponse, PermissionCreate, PermissionUpdate,
    PermissionListResponse, UserPermissionAssignment
)
from ..utils.error_responses import (
    unauthorized_error, not_found_error, bad_request_error, 
    internal_server_error, forbidden_error
)
from ..api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_permission(current_user: User, permission: str) -> None:
    """权限管理端点的权限守卫。

    与 api/users.py 的 _require_user_permission 语义一致：超级用户拥有
    全部权限，否则需要对应权限码（permission:view / permission:create /
    permission:edit / permission:delete / role:assign_permission）。
    此前各端点只有 "# TODO: 检查权限" 占位，任意登录用户均可调用
    （特权提升）。
    """
    if getattr(current_user, "is_superuser", False):
        return
    try:
        perms = getattr(current_user, "permissions", None) or []
    except Exception:
        perms = []
    codes = {c if isinstance(c, str) else getattr(c, "code", "") for c in perms}
    if permission not in codes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要权限: {permission}",
        )


async def get_permission_service(session: AsyncSession = Depends(get_async_session)) -> PermissionService:
    """获取权限服务实例"""
    return PermissionService(session)

@router.get("", response_model=PermissionListResponse)
async def get_permissions(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="返回的记录数"),
    module: Optional[str] = Query(None, description="模块筛选"),
    permission_type: Optional[str] = Query(None, description="权限类型筛选"),
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取权限列表"""
    try:
        _require_permission(current_user, "permission:view")
        
        if module:
            permissions = await permission_service.get_permissions_by_module(module)
            total = len(permissions)
            permissions = permissions[skip:skip+limit]
        else:
            # 获取权限树
            permission_tree = await permission_service.get_permission_tree()
            # 扁平化处理用于分页
            all_permissions = []
            
            def flatten_permissions(perms):
                for perm in perms:
                    all_permissions.append(perm)
                    if perm.get("children"):
                        flatten_permissions(perm["children"])
            
            flatten_permissions(permission_tree)
            
            total = len(all_permissions)
            permissions = all_permissions[skip:skip+limit]
        
        return PermissionListResponse(
            permissions=permissions,
            total=total,
            page=skip // limit + 1,
            page_size=limit,
            total_pages=(total + limit - 1) // limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取权限列表失败: {e}")
        raise internal_server_error("获取权限列表失败", str(e))

@router.get("/tree")
async def get_permission_tree(
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取权限树结构"""
    try:
        _require_permission(current_user, "permission:view")
        
        permission_tree = await permission_service.get_permission_tree()
        return {"permission_tree": permission_tree}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取权限树失败: {e}")
        raise internal_server_error("获取权限树失败", str(e))

@router.get("/statistics")
async def get_permission_statistics(
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取权限统计信息"""
    try:
        _require_permission(current_user, "permission:view")
        
        stats = await permission_service.get_permission_statistics()
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取权限统计失败: {e}")
        raise internal_server_error("获取权限统计失败", str(e))

@router.post("", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """创建权限"""
    try:
        _require_permission(current_user, "permission:create")
        
        new_permission = await permission_service.create_permission(permission_data.dict())
        return PermissionResponse.from_orm(new_permission)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"创建权限失败: {e}")
        raise internal_server_error("创建权限失败", str(e))

@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取权限详情"""
    try:
        _require_permission(current_user, "permission:view")

        permission = await permission_service.get_permission_by_id(permission_id)
        if not permission:
            raise not_found_error("权限不存在")
        return PermissionResponse.from_orm(permission)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取权限详情失败: {e}")
        raise internal_server_error("获取权限详情失败", str(e))

@router.put("/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """更新权限"""
    try:
        _require_permission(current_user, "permission:edit")
        
        updated_permission = await permission_service.update_permission(
            permission_id, 
            permission_data.dict(exclude_unset=True)
        )
        
        if not updated_permission:
            raise not_found_error("权限不存在")
        
        return PermissionResponse.from_orm(updated_permission)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"更新权限失败: {e}")
        raise internal_server_error("更新权限失败", str(e))

@router.delete("/{permission_id}")
async def delete_permission(
    permission_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """删除权限"""
    try:
        _require_permission(current_user, "permission:delete")
        
        success = await permission_service.delete_permission(permission_id)
        if success:
            return {"message": "权限删除成功"}
        else:
            raise not_found_error("权限不存在")
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"删除权限失败: {e}")
        raise internal_server_error("删除权限失败", str(e))

@router.get("/users/{user_id}")
async def get_user_permissions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取用户权限"""
    try:
        # 检查权限：只能查看自己的权限或管理员权限
        if current_user.id != user_id and not current_user.is_superuser:
            raise forbidden_error("只能查看自己的权限")
        
        user_permissions = await permission_service.get_user_permissions(user_id)
        return user_permissions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户权限失败: {e}")
        raise internal_server_error("获取用户权限失败", str(e))

@router.post("/users/{user_id}/grant")
async def grant_permission_to_user(
    user_id: int,
    assignment: UserPermissionAssignment,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """授予用户权限"""
    try:
        _require_permission(current_user, "permission:edit")
        
        success = await permission_service.grant_permission_to_user(
            user_id=user_id,
            permission_id=assignment.permission_id,
            granted_by=current_user.id,
            effect=assignment.effect,
            expires_at=assignment.expires_at,
            reason=assignment.reason
        )
        
        if success:
            return {"message": "权限授予成功"}
        else:
            raise bad_request_error("权限授予失败")
        
    except HTTPException:
        raise
    except ValueError as e:
        raise bad_request_error(str(e))
    except Exception as e:
        logger.error(f"授予用户权限失败: {e}")
        raise internal_server_error("授予用户权限失败", str(e))

@router.delete("/users/{user_id}/permissions/{permission_id}")
async def revoke_permission_from_user(
    user_id: int,
    permission_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """撤销用户权限"""
    try:
        _require_permission(current_user, "permission:edit")
        
        success = await permission_service.revoke_permission_from_user(user_id, permission_id)
        if success:
            return {"message": "权限撤销成功"}
        else:
            raise not_found_error("权限不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"撤销用户权限失败: {e}")
        raise internal_server_error("撤销用户权限失败", str(e))

@router.post("/check")
async def check_permissions(
    permission_codes: List[str],
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """批量检查权限"""
    try:
        # 如果没有指定用户ID，检查当前用户权限
        target_user_id = user_id if user_id else current_user.id
        
        # 检查权限：只能检查自己的权限或管理员权限
        if target_user_id != current_user.id and not current_user.is_superuser:
            raise forbidden_error("只能检查自己的权限")
        
        permission_results = await permission_service.check_permissions(target_user_id, permission_codes)
        return {"permissions": permission_results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查权限失败: {e}")
        raise internal_server_error("检查权限失败", str(e))

@router.get("/roles/{role_id}")
async def get_role_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """获取角色权限"""
    try:
        _require_permission(current_user, "permission:view")
        
        role_permissions = await permission_service.get_role_permissions(role_id)
        return {"permissions": role_permissions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色权限失败: {e}")
        raise internal_server_error("获取角色权限失败", str(e))

@router.post("/roles/{role_id}/assign")
async def assign_permissions_to_role(
    role_id: int,
    permission_ids: List[int],
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends(get_permission_service)
):
    """为角色分配权限"""
    try:
        _require_permission(current_user, "role:assign_permission")
        
        result = await permission_service.assign_permissions_to_role(
            role_id=role_id,
            permission_ids=permission_ids,
            granted_by=current_user.id
        )
        
        return {
            "message": "权限分配完成",
            "success_count": result["success_count"],
            "failed_count": result["failed_count"],
            "failed_permissions": result["failed_permissions"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"为角色分配权限失败: {e}")
        raise internal_server_error("为角色分配权限失败", str(e))