"""
AI助手权限装饰器
"""
import functools
import logging
from typing import Callable, Any, Optional, Dict
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..services.ai_permission_service import AIPermissionService

logger = logging.getLogger(__name__)


def require_ai_permission(operation: str, **permission_kwargs):
    """
    AI权限检查装饰器
    
    Args:
        operation: AI操作类型
        **permission_kwargs: 权限检查所需的额外参数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中提取数据库会话和当前用户
            db: Optional[AsyncSession] = None
            current_user: Optional[Dict[str, Any]] = None
            
            # 尝试从kwargs中获取
            if 'db' in kwargs:
                db = kwargs['db']
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            
            # 如果没有找到，尝试从args中获取（假设是依赖注入的参数）
            if db is None or current_user is None:
                # 这种情况下，装饰器应该与FastAPI的Depends一起使用
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="权限装饰器配置错误：缺少数据库会话或用户信息"
                )
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户未认证"
                )
            
            try:
                # 创建权限服务实例
                ai_permission_service = AIPermissionService(db)
                
                # 构建权限检查参数
                check_kwargs = permission_kwargs.copy()
                
                # 从函数参数中提取相关ID
                if 'session_id' in kwargs:
                    check_kwargs['session_id'] = kwargs['session_id']
                if 'template_id' in kwargs:
                    check_kwargs['template_id'] = kwargs['template_id']
                if 'model_provider' in kwargs:
                    check_kwargs['model_provider'] = kwargs['model_provider']
                
                # 执行权限验证
                await ai_permission_service.validate_ai_operation_permission(
                    user_id=current_user['id'],
                    operation=operation,
                    **check_kwargs
                )
                
                # 权限验证通过，执行原函数
                return await func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"AI权限检查失败: {str(e)}")
                if isinstance(e, HTTPException):
                    raise e
                
                # 权限相关异常
                if "权限" in str(e) or "permission" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=str(e)
                    )
                
                # 其他异常
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"权限检查失败: {str(e)}"
                )
        
        return wrapper
    return decorator


def ai_permission_required(operation: str, **permission_kwargs):
    """
    AI权限检查装饰器（用于FastAPI路由函数）
    
    使用方式:
    @ai_permission_required("chat_basic")
    async def create_chat_session(
        session_data: ChatSessionCreate,
        db: AsyncSession = Depends(get_db),
        current_user: dict = Depends(get_current_user)
    ):
        ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(
            *args,
            db: AsyncSession = Depends(get_db),
            current_user: dict = Depends(get_current_user),
            **kwargs
        ):
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户未认证"
                )
            
            try:
                # 创建权限服务实例
                ai_permission_service = AIPermissionService(db)
                
                # 构建权限检查参数
                check_kwargs = permission_kwargs.copy()
                
                # 从函数参数中提取相关ID
                for key in ['session_id', 'template_id', 'model_provider']:
                    if key in kwargs:
                        check_kwargs[key] = kwargs[key]
                
                # 执行权限验证
                await ai_permission_service.validate_ai_operation_permission(
                    user_id=current_user['id'],
                    operation=operation,
                    **check_kwargs
                )
                
                # 权限验证通过，执行原函数
                return await func(*args, db=db, current_user=current_user, **kwargs)
                
            except Exception as e:
                logger.error(f"AI权限检查失败: {str(e)}")
                
                # 权限相关异常
                if "权限" in str(e) or "permission" in str(e).lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=str(e)
                    )
                
                # 其他异常
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"权限检查失败: {str(e)}"
                )
        
        return wrapper
    return decorator


class AIPermissionChecker:
    """AI权限检查器类"""
    
    def __init__(self, db: AsyncSession):
        self.ai_permission_service = AIPermissionService(db)
    
    async def check_chat_permission(self, user_id: int, advanced: bool = False) -> bool:
        """检查聊天权限"""
        try:
            has_permission, _ = await self.ai_permission_service.check_ai_chat_permission(
                user_id, advanced
            )
            return has_permission
        except Exception as e:
            logger.error(f"检查聊天权限失败: {str(e)}")
            return False
    
    async def check_model_permission(self, user_id: int, model_provider: str) -> bool:
        """检查模型使用权限"""
        try:
            has_permission, _ = await self.ai_permission_service.check_ai_model_permission(
                user_id, model_provider
            )
            return has_permission
        except Exception as e:
            logger.error(f"检查模型权限失败: {str(e)}")
            return False
    
    async def check_admin_permission(self, user_id: int, admin_type: str = "config") -> bool:
        """检查管理员权限"""
        try:
            permission_code = f"ai_admin_{admin_type}"
            has_permission, _ = await self.ai_permission_service.check_user_ai_permission(
                user_id, permission_code
            )
            return has_permission
        except Exception as e:
            logger.error(f"检查管理员权限失败: {str(e)}")
            return False
    
    async def get_user_permissions(self, user_id: int) -> Dict[str, Any]:
        """获取用户权限信息"""
        try:
            return await self.ai_permission_service.get_user_ai_permissions(user_id)
        except Exception as e:
            logger.error(f"获取用户权限失败: {str(e)}")
            return {"user_id": user_id, "permissions": {}, "summary": {}}


# 便捷的权限检查函数
async def check_ai_permission(
    user_id: int,
    operation: str,
    db: AsyncSession,
    **kwargs
) -> tuple[bool, str]:
    """
    便捷的AI权限检查函数
    
    Args:
        user_id: 用户ID
        operation: 操作类型
        db: 数据库会话
        **kwargs: 额外参数
    
    Returns:
        tuple[bool, str]: (是否有权限, 消息)
    """
    try:
        ai_permission_service = AIPermissionService(db)
        
        if operation == "chat":
            return await ai_permission_service.check_ai_chat_permission(
                user_id, kwargs.get("advanced", False)
            )
        elif operation == "model":
            return await ai_permission_service.check_ai_model_permission(
                user_id, kwargs.get("model_provider", "")
            )
        elif operation.startswith("session_"):
            action = operation.replace("session_", "")
            return await ai_permission_service.check_ai_session_permission(
                user_id, action, kwargs.get("session_id")
            )
        elif operation.startswith("template_"):
            action = operation.replace("template_", "")
            return await ai_permission_service.check_ai_template_permission(
                user_id, action, kwargs.get("template_id")
            )
        else:
            return await ai_permission_service.check_user_ai_permission(user_id, operation)
            
    except Exception as e:
        logger.error(f"权限检查失败: {str(e)}")
        return False, f"权限检查失败: {str(e)}"


# 权限检查中间件
async def ai_permission_middleware(
    user_id: int,
    operation: str,
    db: AsyncSession,
    **kwargs
) -> None:
    """
    AI权限检查中间件，无权限时抛出异常
    
    Args:
        user_id: 用户ID
        operation: 操作类型
        db: 数据库会话
        **kwargs: 额外参数
    
    Raises:
        HTTPException: 权限不足时抛出403异常
    """
    has_permission, message = await check_ai_permission(
        user_id, operation, db, **kwargs
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"AI操作权限不足: {message}"
        )