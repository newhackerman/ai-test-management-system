"""
会议权限装饰器

本模块提供会议相关的权限装饰器，用于API路由的权限控制
"""
import logging
from functools import wraps
from typing import Optional, List, Union

from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import PermissionError, NotFoundError
from ....services.meeting_permission_service import MeetingPermissionService, get_meeting_permission_service
from ....models.user import User
from ....api.auth import get_current_user

logger = logging.getLogger(__name__)


def require_meeting_permission(
    permission: Union[str, List[str]],
    meeting_id_param: str = "meeting_id"
):
    """
    会议权限装饰器
    
    Args:
        permission: 所需权限（单个权限字符串或权限列表）
        meeting_id_param: 会议ID参数名
    
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取依赖
            current_user = None
            permission_service = None
            meeting_id = None
            
            # 从kwargs中获取依赖注入的参数
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, MeetingPermissionService):
                    permission_service = value
                elif key == meeting_id_param:
                    meeting_id = value
            
            # 如果没有找到必要的参数，抛出错误
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户认证失败"
                )
            
            if not permission_service:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="权限服务不可用"
                )
            
            if meeting_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="缺少会议ID参数"
                )
            
            try:
                # 检查权限
                permissions_to_check = [permission] if isinstance(permission, str) else permission
                
                for perm in permissions_to_check:
                    has_permission = await permission_service.check_meeting_permission(
                        user_id=current_user.id,
                        meeting_id=meeting_id,
                        permission=perm
                    )
                    
                    if not has_permission:
                        logger.warning(
                            f"用户 {current_user.id} 缺少权限 {perm} 访问会议 {meeting_id}"
                        )
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"缺少权限: {perm}"
                        )
                
                # 权限检查通过，执行原函数
                return await func(*args, **kwargs)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"权限检查失败: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="权限检查失败"
                )
        
        return wrapper
    return decorator


def require_meeting_organizer(meeting_id_param: str = "meeting_id"):
    """
    要求会议组织者权限的装饰器
    
    Args:
        meeting_id_param: 会议ID参数名
    
    Returns:
        装饰器函数
    """
    return require_meeting_permission(
        ["meeting.update", "meeting.delete", "meeting.manage_participants"],
        meeting_id_param
    )


def require_meeting_moderator(meeting_id_param: str = "meeting_id"):
    """
    要求会议主持人权限的装饰器
    
    Args:
        meeting_id_param: 会议ID参数名
    
    Returns:
        装饰器函数
    """
    return require_meeting_permission(
        ["meeting.control", "meeting.manage_participants"],
        meeting_id_param
    )


def require_meeting_access(meeting_id_param: str = "meeting_id"):
    """
    要求会议访问权限的装饰器
    
    Args:
        meeting_id_param: 会议ID参数名
    
    Returns:
        装饰器函数
    """
    return require_meeting_permission("meeting.view", meeting_id_param)


def require_recording_permission(meeting_id_param: str = "meeting_id"):
    """
    要求录制权限的装饰器
    
    Args:
        meeting_id_param: 会议ID参数名
    
    Returns:
        装饰器函数
    """
    return require_meeting_permission(
        ["meeting.start_recording", "meeting.stop_recording"],
        meeting_id_param
    )


# 权限检查依赖函数
async def check_meeting_view_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
) -> bool:
    """检查会议查看权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission="meeting.view"
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此会议"
        )
    
    return True


async def check_meeting_manage_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
) -> bool:
    """检查会议管理权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission="meeting.update"
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限管理此会议"
        )
    
    return True


async def check_participant_manage_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
) -> bool:
    """检查参与者管理权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission="meeting.manage_participants"
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限管理会议参与者"
        )
    
    return True


async def check_meeting_control_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
) -> bool:
    """检查会议控制权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission="meeting.control"
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限控制此会议"
        )
    
    return True


async def check_recording_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
) -> bool:
    """检查录制权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission="meeting.start_recording"
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限录制此会议"
        )
    
    return True


async def check_ai_analysis_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
) -> bool:
    """检查AI分析权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission="meeting.generate_ai_analysis"
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限生成AI分析"
        )
    
    return True


async def get_user_meeting_permissions(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
) -> List[str]:
    """获取用户在会议中的所有权限"""
    try:
        permissions = await permission_service.get_user_meeting_permissions(
            user_id=current_user.id,
            meeting_id=meeting_id
        )
        return permissions
        
    except Exception as e:
        logger.error(f"获取用户会议权限失败: {e}")
        return []


# 权限验证中间件类
class MeetingPermissionMiddleware:
    """会议权限验证中间件"""
    
    def __init__(self):
        self.protected_paths = {
            "/meetings/{meeting_id}": ["meeting.view"],
            "/meetings/{meeting_id}/participants": ["meeting.manage_participants"],
            "/meetings/{meeting_id}/control": ["meeting.control"],
            "/meetings/{meeting_id}/recordings": ["meeting.view_recordings"],
            "/meetings/{meeting_id}/ai-analysis": ["meeting.view_ai_analysis"]
        }
    
    async def check_path_permission(
        self,
        path: str,
        method: str,
        user_id: int,
        meeting_id: int,
        permission_service: MeetingPermissionService
    ) -> bool:
        """检查路径权限"""
        try:
            # 根据路径和方法确定所需权限
            required_permissions = self._get_required_permissions(path, method)
            
            if not required_permissions:
                return True  # 不需要特殊权限
            
            # 检查所有必需权限
            for permission in required_permissions:
                has_permission = await permission_service.check_meeting_permission(
                    user_id=user_id,
                    meeting_id=meeting_id,
                    permission=permission
                )
                
                if not has_permission:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查路径权限失败: {e}")
            return False
    
    def _get_required_permissions(self, path: str, method: str) -> List[str]:
        """根据路径和方法获取所需权限"""
        # 简化的权限映射逻辑
        if "participants" in path:
            if method in ["POST", "PUT", "DELETE"]:
                return ["meeting.manage_participants"]
            else:
                return ["meeting.view"]
        
        if "control" in path:
            return ["meeting.control"]
        
        if "recordings" in path:
            if method in ["POST", "DELETE"]:
                return ["meeting.start_recording"]
            else:
                return ["meeting.view_recordings"]
        
        if "ai-analysis" in path:
            if method == "POST":
                return ["meeting.generate_ai_analysis"]
            else:
                return ["meeting.view_ai_analysis"]
        
        # 默认需要查看权限
        return ["meeting.view"]