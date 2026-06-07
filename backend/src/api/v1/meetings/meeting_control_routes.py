"""
会议加入和控制API路由

本模块提供会议加入和控制的REST API接口，包括：
- POST /meetings/{meeting_code}/join 加入会议接口
- POST /meetings/{meeting_id}/start 开始会议接口
- POST /meetings/{meeting_id}/end 结束会议接口
- GET /meetings/{meeting_id}/status 获取会议状态接口
- POST /meetings/{meeting_id}/kick/{user_id} 踢出参与者接口
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import ValidationError, NotFoundError, PermissionError
from ....services.meeting_service import MeetingService, get_meeting_service
from ....api.auth import get_current_user
from ....models.user import User
from ....schemas.meeting_schemas import (
    MeetingJoinRequest, MeetingJoinResponse, MeetingControlRequest,
    MeetingControlResponse, MeetingStatusResponse
)
from ....schemas.participant_schemas import (
    KickParticipantRequest, KickParticipantResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{meeting_code}/join",
    response_model=MeetingJoinResponse,
    summary="加入会议",
    description="通过会议编码加入会议"
)
async def join_meeting(
    meeting_code: str = Path(..., description="会议编码"),
    request: MeetingJoinRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    加入会议
    
    - **meeting_code**: 会议编码（必填）
    - **password**: 会议密码（如果会议设置了密码则必填）
    - **device_info**: 设备信息（可选）
    - **join_options**: 加入选项（可选）
    
    返回加入结果，包括访问令牌、会议配置、WebRTC配置等
    """
    try:
        logger.info(f"用户 {current_user.id} 尝试加入会议: {meeting_code}")
        
        # 加入会议
        join_result = await meeting_service.join_meeting(meeting_code, current_user.id, request)
        
        logger.info(f"用户 {current_user.id} 加入会议成功: {meeting_code}, 状态: {join_result.status}")
        
        return MeetingJoinResponse(
            success=True,
            message=join_result.message,
            status=join_result.status,
            access_token=join_result.access_token,
            meeting_config=join_result.meeting_config,
            webrtc_config=join_result.webrtc_config
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_code}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"加入会议验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"加入会议权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"加入会议失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="加入会议失败"
        )


@router.post(
    "/{meeting_id}/start",
    response_model=MeetingControlResponse,
    summary="开始会议",
    description="开始会议，只有会议组织者和主持人可以操作"
)
async def start_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    request: Optional[MeetingControlRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    开始会议
    
    - **meeting_id**: 会议ID（必填）
    - **reason**: 操作原因（可选）
    
    注意：只有会议组织者和主持人可以开始会议
    """
    try:
        logger.info(f"用户 {current_user.id} 开始会议: {meeting_id}")
        
        # 开始会议
        meeting = await meeting_service.start_meeting(meeting_id, current_user.id, request)
        
        logger.info(f"会议开始成功: {meeting_id}")
        
        return MeetingControlResponse(
            success=True,
            message="会议开始成功",
            meeting_status=meeting.status.value,
            data={
                "actual_start_time": meeting.actual_start_time.isoformat() if meeting.actual_start_time else None,
                "participant_count": meeting.participant_count
            }
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"开始会议验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"开始会议权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"开始会议失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="开始会议失败"
        )


@router.post(
    "/{meeting_id}/end",
    response_model=MeetingControlResponse,
    summary="结束会议",
    description="结束会议，只有会议组织者和主持人可以操作"
)
async def end_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    request: Optional[MeetingControlRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    结束会议
    
    - **meeting_id**: 会议ID（必填）
    - **reason**: 操作原因（可选）
    
    注意：只有会议组织者和主持人可以结束会议
    """
    try:
        logger.info(f"用户 {current_user.id} 结束会议: {meeting_id}")
        
        # 结束会议
        meeting = await meeting_service.end_meeting(meeting_id, current_user.id, request)
        
        logger.info(f"会议结束成功: {meeting_id}")
        
        return MeetingControlResponse(
            success=True,
            message="会议结束成功",
            meeting_status=meeting.status.value,
            data={
                "actual_end_time": meeting.actual_end_time.isoformat() if meeting.actual_end_time else None,
                "duration_minutes": meeting.duration_minutes,
                "participant_count": meeting.participant_count
            }
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"结束会议验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"结束会议权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"结束会议失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="结束会议失败"
        )


@router.get(
    "/{meeting_id}/status",
    response_model=MeetingStatusResponse,
    summary="获取会议状态",
    description="获取会议的实时状态信息"
)
async def get_meeting_status(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取会议状态
    
    - **meeting_id**: 会议ID（必填）
    
    返回会议的实时状态信息，包括参与人数、录制状态、网络质量等
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议状态: {meeting_id}")
        
        # 获取会议状态
        meeting_status = await meeting_service.get_meeting_status(meeting_id, current_user.id)
        
        return MeetingStatusResponse(
            meeting_id=meeting_id,
            status=meeting_status['status'],
            participant_count=meeting_status['participant_count'],
            is_recording=meeting_status['is_recording'],
            start_time=meeting_status.get('start_time'),
            duration_minutes=meeting_status['duration_minutes'],
            network_quality=meeting_status.get('network_quality')
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取会议状态权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取会议状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会议状态失败"
        )


@router.post(
    "/{meeting_id}/kick/{user_id}",
    response_model=KickParticipantResponse,
    summary="踢出参与者",
    description="将参与者踢出会议，只有会议组织者和主持人可以操作"
)
async def kick_participant(
    meeting_id: int = Path(..., description="会议ID"),
    user_id: int = Path(..., description="用户ID"),
    request: Optional[KickParticipantRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    踢出参与者
    
    - **meeting_id**: 会议ID（必填）
    - **user_id**: 用户ID（必填）
    - **reason**: 踢出原因（可选）
    - **ban_duration_minutes**: 禁止重新加入时长（可选，0-1440分钟）
    
    注意：只有会议组织者和主持人可以踢出参与者
    """
    try:
        logger.info(f"用户 {current_user.id} 踢出会议 {meeting_id} 参与者 {user_id}")
        
        # 踢出参与者
        kick_result = await meeting_service.kick_participant(meeting_id, user_id, current_user.id, request)
        
        logger.info(f"参与者踢出成功: 会议 {meeting_id}, 用户 {user_id}")
        
        return KickParticipantResponse(
            success=True,
            message="参与者已被踢出",
            banned_until=kick_result.get('banned_until')
        )
        
    except NotFoundError as e:
        logger.warning(f"会议或参与者不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"踢出参与者验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"踢出参与者权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"踢出参与者失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="踢出参与者失败"
        )


@router.post(
    "/{meeting_id}/pause",
    response_model=MeetingControlResponse,
    summary="暂停会议",
    description="暂停会议，只有会议组织者和主持人可以操作"
)
async def pause_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    request: Optional[MeetingControlRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    暂停会议
    
    - **meeting_id**: 会议ID（必填）
    - **reason**: 操作原因（可选）
    
    注意：只有会议组织者和主持人可以暂停会议
    """
    try:
        logger.info(f"用户 {current_user.id} 暂停会议: {meeting_id}")
        
        # 暂停会议
        meeting = await meeting_service.pause_meeting(meeting_id, current_user.id, request)
        
        logger.info(f"会议暂停成功: {meeting_id}")
        
        return MeetingControlResponse(
            success=True,
            message="会议暂停成功",
            meeting_status=meeting.status.value,
            data={
                "paused_at": datetime.utcnow().isoformat()
            }
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"暂停会议验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"暂停会议权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"暂停会议失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="暂停会议失败"
        )


@router.post(
    "/{meeting_id}/resume",
    response_model=MeetingControlResponse,
    summary="恢复会议",
    description="恢复暂停的会议，只有会议组织者和主持人可以操作"
)
async def resume_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    request: Optional[MeetingControlRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    恢复会议
    
    - **meeting_id**: 会议ID（必填）
    - **reason**: 操作原因（可选）
    
    注意：只有会议组织者和主持人可以恢复会议
    """
    try:
        logger.info(f"用户 {current_user.id} 恢复会议: {meeting_id}")
        
        # 恢复会议
        meeting = await meeting_service.resume_meeting(meeting_id, current_user.id, request)
        
        logger.info(f"会议恢复成功: {meeting_id}")
        
        return MeetingControlResponse(
            success=True,
            message="会议恢复成功",
            meeting_status=meeting.status.value,
            data={
                "resumed_at": datetime.utcnow().isoformat()
            }
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"恢复会议验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"恢复会议权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"恢复会议失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="恢复会议失败"
        )