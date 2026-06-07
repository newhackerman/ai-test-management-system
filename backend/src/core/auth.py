"""
认证相关功能
"""
from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .security import verify_token

# HTTP Bearer 认证
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    获取当前用户信息
    
    Args:
        credentials: HTTP认证凭据
        
    Returns:
        Dict[str, Any]: 用户信息
        
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
        # 目前返回基本信息
        return {
            "id": int(user_id),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "is_active": payload.get("is_active", True)
        }
        
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