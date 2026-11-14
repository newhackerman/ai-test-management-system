"""
会议基础CRUD API路由

本模块提供会议管理的基础REST API接口，包括：
- POST /meetings 创建会议接口
- GET /meetings 获取会议列表接口
- GET /meetings/{meeting_id} 获取会议详情接口
- PUT /meetings/{meeting_id} 更新会议接口
- DELETE /meetings/{meeting_id} 删除会议接口
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import ValidationError, NotFoundError, PermissionError
from ....services.meeting_service import MeetingService, get_meeting_service
from ....api.auth import get_current_user
from ....models.user import User
from ....models.meeting import (
    Meeting, MeetingParticipant, MeetingRecording, ParticipantRole, RecordingStatus
)
from ....schemas.meeting_schemas import (
    CreateMeetingRequest, UpdateMeetingRequest, MeetingQueryParams,
    MeetingResponse, MeetingListResponse, CreateMeetingResponse,
    UpdateMeetingResponse, DeleteMeetingResponse, MeetingTypeEnum, MeetingStatusEnum
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=CreateMeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建会议",
    description="创建新的会议，包含输入验证、权限检查和自动分配会议编码"
)
async def create_meeting(
    request: CreateMeetingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    创建会议
    
    - **title**: 会议标题（必填，1-200字符）
    - **description**: 会议描述（可选，最大2000字符）
    - **meeting_type**: 会议类型（必填）
    - **scheduled_start_time**: 计划开始时间（必填）
    - **scheduled_end_time**: 计划结束时间（必填）
    - **timezone**: 时区（默认UTC）
    - **max_participants**: 最大参与人数（默认100，范围2-1000）
    - **project_id**: 关联项目ID（可选）
    - **agenda**: 会议议程（可选）
    - **meeting_settings**: 会议设置（可选）
    - **participant_ids**: 参与者用户ID列表（可选）
    - **auto_schedule**: 是否启用智能调度（默认false）
    """
    try:
        logger.info(f"用户 {current_user.id} 创建会议: {request.title}")
        
        # 创建会议
        meeting = await meeting_service.create_meeting(request, current_user.id)
        
        logger.info(f"会议创建成功: {meeting.id}, 编码: {meeting.meeting_code}")
        
        return CreateMeetingResponse(
            success=True,
            message="会议创建成功",
            data=MeetingResponse.from_orm(meeting)
        )
        
    except ValidationError as e:
        logger.warning(f"会议创建验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"会议创建权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"会议创建失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="会议创建失败"
        )


@router.get(
    "/",
    response_model=MeetingListResponse,
    summary="获取会议列表",
    description="获取会议列表，支持分页、筛选和搜索"
)
async def get_meetings(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    meeting_type: Optional[MeetingTypeEnum] = Query(None, description="会议类型筛选"),
    meeting_status: Optional[MeetingStatusEnum] = Query(None, alias="status", description="会议状态筛选"),
    project_id: Optional[int] = Query(None, description="项目ID筛选"),
    organizer_id: Optional[int] = Query(None, description="组织者ID筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期筛选"),
    end_date: Optional[datetime] = Query(None, description="结束日期筛选"),
    keyword: Optional[str] = Query(None, max_length=100, description="关键词搜索"),
    sort_by: str = Query("scheduled_start_time", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取会议列表
    
    支持的筛选条件：
    - **meeting_type**: 会议类型
    - **status**: 会议状态
    - **project_id**: 项目ID
    - **organizer_id**: 组织者ID
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    - **keyword**: 关键词搜索（标题、描述）
    
    支持的排序字段：
    - **scheduled_start_time**: 计划开始时间
    - **created_at**: 创建时间
    - **updated_at**: 更新时间
    - **title**: 会议标题
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议列表")
        
        # 构建查询参数
        query_params = MeetingQueryParams(
            page=page,
            page_size=page_size,
            meeting_type=meeting_type,
            status=meeting_status,
            project_id=project_id,
            organizer_id=organizer_id,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 获取会议列表
        meetings, total = await meeting_service.get_meetings(query_params, current_user.id)
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        return MeetingListResponse(
            meetings=[MeetingResponse.from_orm(meeting) for meeting in meetings],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except PermissionError as e:
        logger.warning(f"获取会议列表权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取会议列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会议列表失败"
        )


@router.get(
    "/code/{meeting_code}",
    response_model=MeetingResponse,
    summary="按会议编码获取会议详情",
    description="根据会议编码获取会议详细信息（供 /meetings/join/:meetingCode 入口）"
)
async def get_meeting_by_code(
    meeting_code: str = Path(..., description="会议编码"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    按会议编码获取会议详情

    - **meeting_code**: 会议编码（必填）
    """
    try:
        logger.info(f"用户 {current_user.id} 按编码获取会议详情: {meeting_code}")

        meeting = await meeting_service.get_meeting_by_code(meeting_code, current_user.id)

        return MeetingResponse.from_orm(meeting)

    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_code}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取会议详情权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"按编码获取会议详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会议详情失败"
        )


@router.get(
    "/{meeting_id}",
    response_model=MeetingResponse,
    summary="获取会议详情",
    description="根据会议ID获取会议详细信息"
)
async def get_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取会议详情
    
    - **meeting_id**: 会议ID（必填）
    
    返回会议的完整信息，包括议程、设置、参与者统计等
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议详情: {meeting_id}")
        
        # 获取会议详情
        meeting = await meeting_service.get_meeting_by_id(meeting_id, current_user.id)
        
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会议不存在"
            )
        
        return MeetingResponse.from_orm(meeting)
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取会议详情权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取会议详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会议详情失败"
        )


@router.put(
    "/{meeting_id}",
    response_model=UpdateMeetingResponse,
    summary="更新会议",
    description="更新会议信息，支持部分字段更新"
)
async def update_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    request: UpdateMeetingRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    更新会议
    
    - **meeting_id**: 会议ID（必填）
    - **title**: 会议标题（可选）
    - **description**: 会议描述（可选）
    - **meeting_type**: 会议类型（可选）
    - **scheduled_start_time**: 计划开始时间（可选）
    - **scheduled_end_time**: 计划结束时间（可选）
    - **timezone**: 时区（可选）
    - **max_participants**: 最大参与人数（可选）
    - **agenda**: 会议议程（可选）
    - **meeting_settings**: 会议设置（可选）
    
    注意：只有会议组织者和管理员可以更新会议信息
    """
    try:
        logger.info(f"用户 {current_user.id} 更新会议: {meeting_id}")
        
        # 更新会议
        meeting = await meeting_service.update_meeting(meeting_id, request, current_user.id)
        
        logger.info(f"会议更新成功: {meeting_id}")
        
        return UpdateMeetingResponse(
            success=True,
            message="会议更新成功",
            data=MeetingResponse.from_orm(meeting)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"会议更新验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"会议更新权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"会议更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="会议更新失败"
        )


@router.delete(
    "/{meeting_id}",
    response_model=DeleteMeetingResponse,
    summary="删除会议",
    description="删除会议（软删除），只有会议组织者和管理员可以删除"
)
async def delete_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    删除会议
    
    - **meeting_id**: 会议ID（必填）
    
    注意：
    - 只有会议组织者和管理员可以删除会议
    - 删除操作为软删除，数据不会真正删除
    - 正在进行中的会议不能删除
    """
    try:
        logger.info(f"用户 {current_user.id} 删除会议: {meeting_id}")
        
        # 删除会议
        await meeting_service.delete_meeting(meeting_id, current_user.id)
        
        logger.info(f"会议删除成功: {meeting_id}")
        
        return DeleteMeetingResponse(
            success=True,
            message="会议删除成功"
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"会议删除验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"会议删除权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"会议删除失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="会议删除失败"
        )


@router.get(
    "/{meeting_id}/recording-permissions",
    summary="获取录制权限",
    description="返回当前用户对该会议的录制权限：能否录制/开始/停止/暂停（暂停与恢复共用 canPause）"
)
async def get_recording_permissions(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """录制权限：组织者/主持人/可录制参与者/录制创建者才有权限；开始要求当前无进行中录制。"""
    meeting = (await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )).scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会议不存在")

    participant = (await db.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == current_user.id
        )
    )).scalar_one_or_none()
    is_organizer = meeting.organizer_id == current_user.id
    is_privileged_participant = bool(participant) and (
        participant.participant_role in (ParticipantRole.ORGANIZER, ParticipantRole.MODERATOR)
        or participant.can_record
    )
    can_record = is_organizer or is_privileged_participant

    active = (await db.execute(
        select(MeetingRecording).where(
            MeetingRecording.meeting_id == meeting_id,
            MeetingRecording.recording_status.in_(
                [RecordingStatus.RECORDING, RecordingStatus.PAUSED]
            )
        ).order_by(MeetingRecording.id.desc()).limit(1)
    )).scalar_one_or_none()
    can_manage_active = bool(active) and (
        active.created_by == current_user.id or is_organizer or is_privileged_participant
    )

    return {
        "canRecord": can_record,
        "canStart": can_record and active is None,
        "canStop": can_manage_active,
        "canPause": can_manage_active,
        "reason": None if can_record else "您不是会议参与者或无录制权限",
    }
