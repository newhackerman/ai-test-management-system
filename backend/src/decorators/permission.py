#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权限装饰器模块
提供基于角色和权限的访问控制装饰器
"""

from functools import wraps
from typing import List, Optional, Union, Callable, Any
import logging
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..core.database import get_db_session
from ..models.user import User
from ..models.role import Role
from ..models.permission import Permission
from ..utils.jwt import verify_token

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


def _user_attr(user, key: str, default: Any = None):
    """从当前用户对象读取属性，同时支持 ORM User 对象和 dict。

    `get_current_user` 在本模块返回 ORM User 对象，没有 `.get()` 方法；
    但下游装饰器历史代码以 dict 风格读取属性。统一在此兼容两种形态，
    避免抛出 'User' object has no attribute 'get' 类 AttributeError。
    """
    if user is None:
        return default
    if isinstance(user, dict):
        return user.get(key, default)
    return getattr(user, key, default)


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    从令牌获取当前登录用户
    
    Args:
        credentials: HTTP Bearer凭证
        db: 数据库会话
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 401 - 无效的认证凭证
    """
    try:
        token = credentials.credentials
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        result = await db.execute(
            select(User).where(User.id == int(user_id), User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 验证JWT令牌
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # 检查令牌类型
        token_type = payload.get("type")
        if token_type != "access":
            raise credentials_exception
        
        # 从数据库查询用户
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception
        
        # 检查用户状态
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账户已被禁用"
            )
        
        return user
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise credentials_exception


def require_permissions(permissions: Union[str, List[str]], require_all: bool = True):
    """
    权限验证装饰器
    
    Args:
        permissions: 所需权限代码或权限代码列表
        require_all: 是否需要全部权限（True）或任一权限（False）
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取当前用户信息
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # 检查权限
            user_permissions = _user_attr(current_user, 'permissions', []) or []
            required_perms = [permissions] if isinstance(permissions, str) else permissions
            
            if require_all:
                # 需要全部权限
                if not all(perm in user_permissions for perm in required_perms):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required permissions: {', '.join(required_perms)}"
                    )
            else:
                # 需要任一权限
                if not any(perm in user_permissions for perm in required_perms):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required one of permissions: {', '.join(required_perms)}"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def require_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """要求活跃用户"""
    if not _user_attr(current_user, "is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户未激活"
        )
    return current_user


async def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """要求管理员权限"""
    if not _user_attr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def require_permission(permission: str):
    """要求特定权限"""
    def permission_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_permissions = _user_attr(current_user, "permissions", []) or []
        
        # 超级用户拥有所有权限
        if _user_attr(current_user, "is_superuser", False):
            return current_user
        
        # 检查用户是否有指定权限
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要权限: {permission}"
            )
        
        return current_user
    
    return permission_checker


def require_role(role: str):
    """要求特定角色"""
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_roles = _user_attr(current_user, "roles", []) or []
        
        # 超级用户拥有所有角色
        if _user_attr(current_user, "is_superuser", False):
            return current_user
        
        # 检查用户是否有指定角色
        if role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色: {role}"
            )
        
        return current_user
    
    return role_checker


def require_any_permission(permissions: List[str]):
    """要求任意一个权限"""
    def permission_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_permissions = _user_attr(current_user, "permissions", []) or []
        
        # 超级用户拥有所有权限
        if _user_attr(current_user, "is_superuser", False):
            return current_user
        
        # 检查用户是否有任意一个指定权限
        if not any(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下权限之一: {', '.join(permissions)}"
            )
        
        return current_user
    
    return permission_checker


def require_any_role(roles: List[str]):
    """要求任意一个角色"""
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_roles = _user_attr(current_user, "roles", []) or []
        
        # 超级用户拥有所有角色
        if _user_attr(current_user, "is_superuser", False):
            return current_user
        
        # 检查用户是否有任意一个指定角色
        if not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {', '.join(roles)}"
            )
        
        return current_user
    
    return role_checker
