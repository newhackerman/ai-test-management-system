"""
认证相关功能
"""
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .security import verify_token

# HTTP Bearer 认证
security = HTTPBearer()


class _UserAttrDict(dict):
    """同时支持 `user.id` 属性访问与 `user["id"]` 字典访问的兼容容器。

    历史上 core.auth / core.security 的 get_current_user 返回 dict，
    但大量路由层使用 `current_user.id` 属性访问，会抛
    `'dict' object has no attribute 'id'`。这里用 dict 子类统一两者，
    避免批量改 import 引入回归风险。
    """

    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError:
            # 对布尔/标志类属性返回安全默认值，避免 AttributeError 中断业务逻辑
            if name in ("is_admin", "is_superuser", "is_staff"):
                return False
            if name in ("role", "role_id", "role_ids"):
                return None
            raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> _UserAttrDict:
    """
    获取当前用户信息

    Args:
        credentials: HTTP认证凭据

    Returns:
        _UserAttrDict: 用户信息（同时支持 .attr 与 ["key"] 访问）

    Raises:
        HTTPException: 认证失败时抛出异常
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception

        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # 这里可以从数据库获取完整的用户信息
        # 目前返回基本信息。is_admin/is_superuser/role 通过 _UserAttrDict 的
        # 安全默认值返回（见 _UserAttrDict.__getattr__），避免在每次认证请求
        # 里做同步 DB 查询导致连接池耗尽与事件循环阻塞。
        return _UserAttrDict({
            "id": int(user_id),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "is_active": payload.get("is_active", True),
            "is_superuser": payload.get("is_superuser", payload.get("is_admin", False)),
            "is_admin": payload.get("is_admin", payload.get("is_superuser", False)),
            "role": payload.get("role"),
        })

    except Exception:
        raise credentials_exception


def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict[str, Any]]:
    """
    获取当前用户信息（可选）
    
    Args:
        credentials: HTTP认证凭据
        
    Returns:
        Optional[Dict[str, Any]]: 用户信息，认证失败返回None
    """
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None


def require_permission(permission: str):
    """
    权限装饰器
    
    Args:
        permission: 所需权限
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里可以实现权限检查逻辑
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """
    角色装饰器
    
    Args:
        role: 所需角色
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里可以实现角色检查逻辑
            return await func(*args, **kwargs)
        return wrapper
    return decorator