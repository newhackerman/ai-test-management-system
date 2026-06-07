"""
会议用户个人资料API路由

本模块提供会议相关的用户个人资料API接口，包括：
- 获取用户在会议中的个人资料
- 更新用户偏好设置
- 获取用户会议统计信息
- 管理用户通知设置
"""
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import ValidationError, NotFoundError, PermissionError
from ....services.meeting_user_profile_service import MeetingUserProfileService, get_meeting_user_profile_service
from ....api.auth import get_current_user
from ....models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/profile",
    summary="获取当前用户会议个人资料",
    description="获取当前用户在会议中的个人资料信息"
)
async def get_current_user_profile(
    meeting_id: Optional[int] = Query(None, description="会议ID"),
    include_preferences: bool = Query(True, description="是否包含偏好设置"),
    include_statistics: bool = Query(False, description="是否包含统计信息"),
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """
    获取当前用户会议个人资料
    
    - **meeting_id**: 会议ID（可选）
    - **include_preferences**: 是否包含偏好设置
    - **include_statistics**: 是否包含统计信息
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议个人资料")
        
        profile = await profile_service.get_user_profile_for_meeting(
            user_id=current_user.id,
            meeting_id=meeting_id,
            include_preferences=include_preferences,
            include_statistics=include_statistics
        )
        
        return {
            "success": True,
            "data": profile
        }
        
    except Exception as e:
        logger.error(f"获取用户会议个人资料失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取个人资料失败"
        )


@router.get(
    "/profile/{user_id}",
    summary="获取指定用户会议个人资料",
    description="获取指定用户在会议中的个人资料信息"
)
async def get_user_profile(
    user_id: int = Path(..., description="用户ID"),
    meeting_id: Optional[int] = Query(None, description="会议ID"),
    include_preferences: bool = Query(False, description="是否包含偏好设置"),
    include_statistics: bool = Query(False, description="是否包含统计信息"),
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """
    获取指定用户会议个人资料
    
    - **user_id**: 用户ID
    - **meeting_id**: 会议ID（可选）
    - **include_preferences**: 是否包含偏好设置（仅限本人或管理员）
    - **include_statistics**: 是否包含统计信息（仅限本人或管理员）
    """
    try:
        # 权限检查：只能查看自己的详细信息或管理员可以查看所有人
        if user_id != current_user.id and not current_user.is_superuser:
            include_preferences = False
            include_statistics = False
        
        logger.info(f"用户 {current_user.id} 获取用户 {user_id} 的会议个人资料")
        
        profile = await profile_service.get_user_profile_for_meeting(
            user_id=user_id,
            meeting_id=meeting_id,
            include_preferences=include_preferences,
            include_statistics=include_statistics
        )
        
        return {
            "success": True,
            "data": profile
        }
        
    except NotFoundError as e:
        logger.warning(f"用户不存在: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取用户会议个人资料失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取个人资料失败"
        )


@router.get(
    "/preferences",
    summary="获取用户偏好设置",
    description="获取当前用户的偏好设置"
)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """获取用户偏好设置"""
    try:
        logger.info(f"用户 {current_user.id} 获取偏好设置")
        
        preferences = await profile_service.get_user_preferences(current_user.id)
        
        return {
            "success": True,
            "data": preferences
        }
        
    except Exception as e:
        logger.error(f"获取用户偏好设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取偏好设置失败"
        )


@router.put(
    "/preferences",
    summary="更新用户偏好设置",
    description="更新当前用户的偏好设置"
)
async def update_user_preferences(
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """
    更新用户偏好设置
    
    - **preferences**: 偏好设置对象
    """
    try:
        logger.info(f"用户 {current_user.id} 更新偏好设置")
        
        success = await profile_service.update_user_preferences(
            user_id=current_user.id,
            preferences=preferences
        )
        
        if success:
            return {
                "success": True,
                "message": "偏好设置更新成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="偏好设置更新失败"
            )
        
    except ValidationError as e:
        logger.warning(f"偏好设置验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新用户偏好设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新偏好设置失败"
        )


@router.get(
    "/statistics",
    summary="获取用户会议统计",
    description="获取当前用户的会议统计信息"
)
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """获取用户会议统计信息"""
    try:
        logger.info(f"用户 {current_user.id} 获取会议统计")
        
        statistics = await profile_service.get_user_meeting_statistics(current_user.id)
        
        return {
            "success": True,
            "data": statistics
        }
        
    except Exception as e:
        logger.error(f"获取用户会议统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息失败"
        )


@router.get(
    "/timezone",
    summary="获取用户时区信息",
    description="获取当前用户的时区信息"
)
async def get_user_timezone(
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """获取用户时区信息"""
    try:
        logger.info(f"用户 {current_user.id} 获取时区信息")
        
        timezone_info = await profile_service.get_user_timezone_info(current_user.id)
        
        return {
            "success": True,
            "data": timezone_info
        }
        
    except Exception as e:
        logger.error(f"获取用户时区信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取时区信息失败"
        )


@router.post(
    "/format-time",
    summary="格式化时间显示",
    description="根据用户偏好格式化时间显示"
)
async def format_time_for_user(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """
    格式化时间显示
    
    - **datetime**: ISO格式的时间字符串
    - **format_type**: 格式类型（datetime, date, time）
    """
    try:
        from datetime import datetime
        
        datetime_str = request.get("datetime")
        format_type = request.get("format_type", "datetime")
        
        if not datetime_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少datetime参数"
            )
        
        # 解析时间
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        
        # 格式化时间
        formatted_time = await profile_service.format_time_for_user(
            user_id=current_user.id,
            dt=dt,
            format_type=format_type
        )
        
        return {
            "success": True,
            "data": {
                "original": datetime_str,
                "formatted": formatted_time,
                "format_type": format_type
            }
        }
        
    except ValueError as e:
        logger.warning(f"时间格式错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="时间格式错误"
        )
    except Exception as e:
        logger.error(f"格式化时间失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="格式化时间失败"
        )


@router.get(
    "/notifications/preferences",
    summary="获取通知偏好设置",
    description="获取当前用户的通知偏好设置"
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """获取通知偏好设置"""
    try:
        logger.info(f"用户 {current_user.id} 获取通知偏好设置")
        
        notification_prefs = await profile_service.get_user_notification_preferences(current_user.id)
        
        return {
            "success": True,
            "data": notification_prefs
        }
        
    except Exception as e:
        logger.error(f"获取通知偏好设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取通知偏好设置失败"
        )


@router.post(
    "/notifications/check",
    summary="检查通知设置",
    description="检查是否应该发送特定类型的通知"
)
async def check_notification_setting(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """
    检查通知设置
    
    - **notification_type**: 通知类型
    """
    try:
        notification_type = request.get("notification_type")
        
        if not notification_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="缺少notification_type参数"
            )
        
        should_send = await profile_service.should_send_notification(
            user_id=current_user.id,
            notification_type=notification_type
        )
        
        return {
            "success": True,
            "data": {
                "notification_type": notification_type,
                "should_send": should_send
            }
        }
        
    except Exception as e:
        logger.error(f"检查通知设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="检查通知设置失败"
        )


@router.get(
    "/meetings/{meeting_id}/participants/profiles",
    summary="获取会议参与者个人资料",
    description="获取指定会议的所有参与者个人资料"
)
async def get_meeting_participants_profiles(
    meeting_id: int = Path(..., description="会议ID"),
    include_offline: bool = Query(True, description="是否包含离线用户"),
    current_user: User = Depends(get_current_user),
    profile_service: MeetingUserProfileService = Depends(get_meeting_user_profile_service)
):
    """
    获取会议参与者个人资料
    
    - **meeting_id**: 会议ID
    - **include_offline**: 是否包含离线用户
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议 {meeting_id} 参与者个人资料")
        
        # TODO: 检查用户是否有权限查看会议参与者
        
        profiles = await profile_service.get_meeting_participants_profiles(
            meeting_id=meeting_id,
            include_offline=include_offline
        )
        
        return {
            "success": True,
            "data": {
                "meeting_id": meeting_id,
                "participants": profiles,
                "total_count": len(profiles),
                "online_count": len([p for p in profiles if p.get("is_online", False)])
            }
        }
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取会议参与者权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取会议参与者个人资料失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取参与者个人资料失败"
        )


@router.get(
    "/available-timezones",
    summary="获取可用时区列表",
    description="获取系统支持的时区列表"
)
async def get_available_timezones():
    """获取可用时区列表"""
    try:
        import pytz
        
        # 常用时区
        common_timezones = [
            "UTC",
            "Asia/Shanghai",
            "Asia/Tokyo",
            "Asia/Seoul",
            "Asia/Hong_Kong",
            "Asia/Singapore",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "Australia/Sydney",
            "Australia/Melbourne"
        ]
        
        # 所有时区
        all_timezones = list(pytz.all_timezones)
        
        return {
            "success": True,
            "data": {
                "common_timezones": common_timezones,
                "all_timezones": sorted(all_timezones)
            }
        }
        
    except Exception as e:
        logger.error(f"获取时区列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取时区列表失败"
        )