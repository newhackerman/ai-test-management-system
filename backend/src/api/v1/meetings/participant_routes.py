"""
会议参与者管理API路由

本模块提供会议参与者管理的REST API接口，包括：
- POST /meetings/{meeting_id}/participants 添加参与者接口
- GET /meetings/{meeting_id}/participants 获取参与者列表接口
- PUT /meetings/{meeting_id}/participants/{user_id} 更新参与者信息接口
- DELETE /meetings/{meeting_id}/participants/{user_id} 移除参与者接口
- POST /meetings/{meeting_id}/participants/{user_id}/invite 发送邀请接口
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import ValidationError, NotFoundError, PermissionError
from ....services.meeting_service import MeetingService, get_meeting_service
from ....api.auth import get_current_user
from ....models.user import User
from ....schemas.participant_schemas import (
    AddParticipantRequest, AddParticipantsRequest, UpdateParticipantRequest,
    ParticipantInviteRequest, ParticipantQueryParams, KickParticipantRequest,
    ParticipantResponse, ParticipantListResponse, AddParticipantResponse,
    AddParticipantsResponse, UpdateParticipantResponse, RemoveParticipantResponse,
    InviteParticipantResponse, KickParticipantResponse, ParticipantStatistics,
    ParticipantRoleEnum, InvitationStatusEnum, AttendanceStatusEnum
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=AddParticipantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加参与者",
    description="向会议添加单个参与者"
)
async def add_participant(
    meeting_id: int = Path(..., description="会议ID"),
    request: AddParticipantRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    添加参与者
    
    - **meeting_id**: 会议ID（必填）
    - **user_id**: 用户ID（必填）
    - **participant_role**: 参与角色（默认PARTICIPANT）
    - **permissions**: 权限设置（可选）
    - **send_invitation**: 是否发送邀请（默认true）
    - **invitation_message**: 邀请消息（可选）
    """
    try:
        logger.info(f"用户 {current_user.id} 向会议 {meeting_id} 添加参与者: {request.user_id}")
        
        # 添加参与者
        participant = await meeting_service.add_participant(meeting_id, request, current_user.id)
        
        logger.info(f"参与者添加成功: 会议 {meeting_id}, 用户 {request.user_id}")
        
        return AddParticipantResponse(
            success=True,
            message="参与者添加成功",
            data=ParticipantResponse.from_orm(participant)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议或用户不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"添加参与者验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"添加参与者权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"添加参与者失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加参与者失败"
        )


@router.post(
    "/batch",
    response_model=AddParticipantsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批量添加参与者",
    description="向会议批量添加多个参与者"
)
async def add_participants(
    meeting_id: int = Path(..., description="会议ID"),
    request: AddParticipantsRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    批量添加参与者
    
    - **meeting_id**: 会议ID（必填）
    - **participants**: 参与者列表（必填，1-100个）
    - **send_invitations**: 是否发送邀请（默认true）
    - **default_role**: 默认角色（默认PARTICIPANT）
    - **default_permissions**: 默认权限（可选）
    """
    try:
        logger.info(f"用户 {current_user.id} 向会议 {meeting_id} 批量添加 {len(request.participants)} 个参与者")
        
        # 批量添加参与者
        participants, failed_users = await meeting_service.add_participants(meeting_id, request, current_user.id)
        
        logger.info(f"批量添加参与者完成: 成功 {len(participants)} 个, 失败 {len(failed_users)} 个")
        
        return AddParticipantsResponse(
            success=True,
            message=f"批量添加参与者完成，成功 {len(participants)} 个，失败 {len(failed_users)} 个",
            data=[ParticipantResponse.from_orm(p) for p in participants],
            failed_users=failed_users
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"批量添加参与者验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"批量添加参与者权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"批量添加参与者失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量添加参与者失败"
        )


@router.get(
    "",
    response_model=ParticipantListResponse,
    summary="获取参与者列表",
    description="获取会议的参与者列表，支持筛选"
)
async def get_participants(
    meeting_id: int = Path(..., description="会议ID"),
    role: Optional[ParticipantRoleEnum] = Query(None, description="角色筛选"),
    invitation_status: Optional[InvitationStatusEnum] = Query(None, description="邀请状态筛选"),
    attendance_status: Optional[AttendanceStatusEnum] = Query(None, description="出席状态筛选"),
    include_user_info: bool = Query(True, description="是否包含用户信息"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取参与者列表
    
    - **meeting_id**: 会议ID（必填）
    - **role**: 角色筛选（可选）
    - **invitation_status**: 邀请状态筛选（可选）
    - **attendance_status**: 出席状态筛选（可选）
    - **include_user_info**: 是否包含用户信息（默认true）
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议 {meeting_id} 的参与者列表")
        
        # 构建查询参数
        query_params = ParticipantQueryParams(
            role=role,
            invitation_status=invitation_status,
            attendance_status=attendance_status,
            include_user_info=include_user_info
        )
        
        # 获取参与者列表
        participants, statistics = await meeting_service.get_participants(meeting_id, query_params, current_user.id)
        
        return ParticipantListResponse(
            participants=[ParticipantResponse.from_orm(p) for p in participants],
            total=len(participants),
            online_count=statistics.get('online_count', 0),
            roles_summary=statistics.get('roles_summary', {})
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取参与者列表权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取参与者列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取参与者列表失败"
        )


@router.put(
    "/{user_id}",
    response_model=UpdateParticipantResponse,
    summary="更新参与者信息",
    description="更新会议参与者的角色和权限信息"
)
async def update_participant(
    meeting_id: int = Path(..., description="会议ID"),
    user_id: int = Path(..., description="用户ID"),
    request: UpdateParticipantRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    更新参与者信息
    
    - **meeting_id**: 会议ID（必填）
    - **user_id**: 用户ID（必填）
    - **participant_role**: 参与角色（可选）
    - **permissions**: 权限设置（可选）
    - **invitation_status**: 邀请状态（可选）
    """
    try:
        logger.info(f"用户 {current_user.id} 更新会议 {meeting_id} 参与者 {user_id} 信息")
        
        # 更新参与者信息
        participant = await meeting_service.update_participant(meeting_id, user_id, request, current_user.id)
        
        logger.info(f"参与者信息更新成功: 会议 {meeting_id}, 用户 {user_id}")
        
        return UpdateParticipantResponse(
            success=True,
            message="参与者信息更新成功",
            data=ParticipantResponse.from_orm(participant)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议或参与者不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"更新参与者信息验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"更新参与者信息权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新参与者信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新参与者信息失败"
        )


@router.delete(
    "/{user_id}",
    response_model=RemoveParticipantResponse,
    summary="移除参与者",
    description="从会议中移除参与者"
)
async def remove_participant(
    meeting_id: int = Path(..., description="会议ID"),
    user_id: int = Path(..., description="用户ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    移除参与者
    
    - **meeting_id**: 会议ID（必填）
    - **user_id**: 用户ID（必填）
    
    注意：只有会议组织者和管理员可以移除参与者
    """
    try:
        logger.info(f"用户 {current_user.id} 从会议 {meeting_id} 移除参与者 {user_id}")
        
        # 移除参与者
        await meeting_service.remove_participant(meeting_id, user_id, current_user.id)
        
        logger.info(f"参与者移除成功: 会议 {meeting_id}, 用户 {user_id}")
        
        return RemoveParticipantResponse(
            success=True,
            message="参与者移除成功"
        )
        
    except NotFoundError as e:
        logger.warning(f"会议或参与者不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"移除参与者权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"移除参与者失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除参与者失败"
        )


@router.post(
    "/{user_id}/invite",
    response_model=InviteParticipantResponse,
    summary="发送邀请",
    description="向参与者发送会议邀请"
)
async def invite_participant(
    meeting_id: int = Path(..., description="会议ID"),
    user_id: int = Path(..., description="用户ID"),
    request: ParticipantInviteRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    发送邀请
    
    - **meeting_id**: 会议ID（必填）
    - **user_id**: 用户ID（必填）
    - **invitation_message**: 邀请消息（可选）
    - **reminder_time**: 提醒时间（可选）
    - **send_email**: 发送邮件邀请（默认true）
    - **send_sms**: 发送短信邀请（默认false）
    """
    try:
        logger.info(f"用户 {current_user.id} 向参与者 {user_id} 发送会议 {meeting_id} 邀请")
        
        # 发送邀请
        invitation_result = await meeting_service.send_invitation(meeting_id, user_id, request, current_user.id)
        
        logger.info(f"邀请发送成功: 会议 {meeting_id}, 用户 {user_id}")
        
        return InviteParticipantResponse(
            success=True,
            message="邀请发送成功",
            invitation_id=invitation_result.get('invitation_id'),
            sent_channels=invitation_result.get('sent_channels', [])
        )
        
    except NotFoundError as e:
        logger.warning(f"会议或参与者不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"发送邀请验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"发送邀请权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"发送邀请失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送邀请失败"
        )


@router.get(
    "/statistics",
    response_model=ParticipantStatistics,
    summary="获取参与者统计",
    description="获取会议参与者的统计信息"
)
async def get_participant_statistics(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取参与者统计
    
    - **meeting_id**: 会议ID（必填）
    
    返回参与者的详细统计信息，包括角色分布、状态分布、参与时长等
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议 {meeting_id} 参与者统计")
        
        # 获取参与者统计
        statistics = await meeting_service.get_participant_statistics(meeting_id, current_user.id)
        
        return ParticipantStatistics(**statistics)
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取参与者统计权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取参与者统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取参与者统计失败"
        )