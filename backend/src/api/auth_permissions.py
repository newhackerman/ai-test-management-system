"""
认证权限API - 获取当前用户权限信息
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..decorators.permission import get_current_user
from ..services.permission import PermissionService

router = APIRouter(prefix="/auth", tags=["认证权限"])


@router.get("/permissions", summary="获取当前用户权限")
async def get_current_user_permissions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取当前用户的权限信息
    
    返回用户的角色列表和权限列表
    """
    try:
        permission_service = PermissionService(db)
        
        user_id = current_user.id
        
        # 获取用户角色
        user_roles = permission_service.get_user_roles(user_id)
        
        # 获取用户权限
        user_permissions = permission_service.get_user_permissions(user_id)
        
        # 构造角色信息
        roles_info = []
        for role in user_roles:
            roles_info.append({
                "id": role.id,
                "name": role.name,
                "code": role.code,
                "description": role.description,
                "is_system_role": role.is_system_role,
                "priority": role.priority
            })
        
        return {
            "success": True,
            "data": {
                "user_id": str(user_id),
                "username": current_user.username,
                "roles": roles_info,
                "permissions": list(user_permissions),
                "is_superuser": current_user.is_superuser
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户权限失败: {str(e)}"
        )


@router.get("/profile", summary="获取当前用户详细信息")
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取当前用户的详细信息，包括权限
    """
    try:
        from ..services.user import UserService
        
        user_service = UserService(db)
        permission_service = PermissionService(db)
        
        user_id = current_user.id
        
        # 获取用户详细信息
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 获取用户角色和权限
        user_roles = permission_service.get_user_roles(user_id)
        user_permissions = permission_service.get_user_permissions(user_id)
        
        # 构造用户信息
        user_info = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "phone": user.phone,
            "avatar_url": user.avatar_url,
            "status": user.status.value,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "is_email_verified": user.is_email_verified,
            "is_phone_verified": user.is_phone_verified,
            "mfa_enabled": user.mfa_enabled,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }
        
        # 构造角色信息
        roles_info = []
        for role in user_roles:
            roles_info.append({
                "id": role.id,
                "name": role.name,
                "code": role.code,
                "description": role.description,
                "is_system_role": role.is_system_role,
                "priority": role.priority
            })
        
        return {
            "success": True,
            "data": {
                **user_info,
                "roles": roles_info,
                "permissions": list(user_permissions)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户信息失败: {str(e)}"
        )


@router.post("/check-permission", summary="检查用户权限")
async def check_user_permission(
    permission_code: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    检查当前用户是否具有指定权限
    
    - **permission_code**: 权限代码
    """
    try:
        permission_service = PermissionService(db)
        
        user_id = current_user.id
        
        # 检查权限
        has_permission = permission_service.check_user_permission(user_id, permission_code)
        
        return {
            "success": True,
            "data": {
                "user_id": str(user_id),
                "permission_code": permission_code,
                "has_permission": has_permission
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查权限失败: {str(e)}"
        )


@router.post("/check-role", summary="检查用户角色")
async def check_user_role(
    role_code: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    检查当前用户是否具有指定角色
    
    - **role_code**: 角色代码
    """
    try:
        permission_service = PermissionService(db)
        
        user_id = current_user.id
        
        # 检查角色
        has_role = permission_service.check_user_role(user_id, role_code)
        
        return {
            "success": True,
            "data": {
                "user_id": str(user_id),
                "role_code": role_code,
                "has_role": has_role
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查角色失败: {str(e)}"
        )