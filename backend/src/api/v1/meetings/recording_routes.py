"""
录制管理API路由

本模块提供会议录制管理的REST API接口，包括：
- POST /meetings/{meeting_id}/recordings/start 开始录制接口
- POST /recordings/{recording_id}/stop 停止录制接口
- GET /meetings/{meeting_id}/recordings 获取录制列表接口
- GET /recordings/{recording_id} 获取录制详情接口
- GET /recordings/{recording_id}/playback 获取播放信息接口
- DELETE /recordings/{recording_id} 删除录制接口
"""
import logging
from typing import Optional
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import ValidationError, NotFoundError, PermissionError
from ....services.recording_service import RecordingService, get_recording_service
from ....services.meeting_service import MeetingService, get_meeting_service
from ....api.auth import get_current_user, security
from ....models.user import User
from ....schemas.recording_schemas import (
    StartRecordingRequest, StopRecordingRequest, RecordingQueryParams,
    UpdateRecordingRequest,
    RecordingResponse, RecordingListResponse, StartRecordingResponse,
    StopRecordingResponse, PauseRecordingResponse, DeleteRecordingResponse, PlaybackInfoResponse,
    RecordingShareRequest, RecordingShareResponse, RecordingStatistics,
    RecordingTypeEnum, RecordingStatusEnum, FileFormatEnum
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_async_session),
) -> Optional[User]:
    """下载端点专用：有 Bearer 头就验签，无头返回 None（再由
    ?token= 播放令牌鉴权，<video src> 没法带 Authorization 头）。"""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None


@router.post(
    "/{meeting_id}/recordings/start",
    response_model=StartRecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="开始录制",
    description="开始录制会议，需要录制权限"
)
async def start_recording(
    meeting_id: int = Path(..., description="会议ID"),
    request: StartRecordingRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    开始录制
    
    - **meeting_id**: 会议ID（必填）
    - **recording_name**: 录制名称（可选，自动生成）
    - **config**: 录制配置（可选）
    - **is_public**: 是否公开（默认false）
    - **access_password**: 访问密码（可选）
    - **description**: 录制描述（可选）
    
    注意：需要会议录制权限才能开始录制
    """
    try:
        logger.info(f"用户 {current_user.id} 开始录制会议: {meeting_id}")
        
        # 开始录制
        recording = await recording_service.start_recording(meeting_id, request, current_user.id)
        
        logger.info(f"录制开始成功: 会议 {meeting_id}, 录制ID {recording.id}")
        
        return StartRecordingResponse(
            success=True,
            message="录制开始成功",
            recording_id=recording.id,
            data=RecordingResponse.from_orm(recording)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"开始录制验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"开始录制权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"开始录制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="开始录制失败"
        )


@router.post(
    "/{recording_id}/stop",
    response_model=StopRecordingResponse,
    summary="停止录制",
    description="停止指定的录制"
)
async def stop_recording(
    recording_id: int = Path(..., description="录制ID"),
    request: Optional[StopRecordingRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    停止录制
    
    - **recording_id**: 录制ID（必填）
    - **save_recording**: 是否保存录制（默认true）
    - **auto_process**: 是否自动处理（默认true）
    - **generate_summary**: 是否生成摘要（默认true）
    
    注意：只有录制创建者和会议主持人可以停止录制
    """
    try:
        logger.info(f"用户 {current_user.id} 停止录制: {recording_id}")
        
        # 停止录制
        recording = await recording_service.stop_recording(recording_id, current_user.id)
        
        logger.info(f"录制停止成功: 录制ID {recording_id}")
        
        return StopRecordingResponse(
            success=True,
            recording_id=recording.id,
            message="录制停止成功"
        )
        
    except NotFoundError as e:
        logger.warning(f"录制不存在: {recording_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"停止录制验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"停止录制权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"停止录制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="停止录制失败"
        )


@router.post(
    "/{recording_id}/pause",
    response_model=PauseRecordingResponse,
    summary="暂停录制",
    description="暂停指定的录制：仅进行中的录制可暂停；采集进程用 SIGSTOP 冻结，恢复后继续写入同一文件"
)
async def pause_recording(
    recording_id: int = Path(..., description="录制ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    暂停录制

    - **recording_id**: 录制ID（必填）

    注意：只有录制创建者和会议主持人可以暂停录制（与停止同一权限）
    """
    try:
        logger.info(f"用户 {current_user.id} 暂停录制: {recording_id}")

        recording = await recording_service.pause_recording(recording_id, current_user.id)

        logger.info(f"录制暂停成功: 录制ID {recording_id}")

        return PauseRecordingResponse(
            success=True,
            message="录制已暂停",
            data=RecordingResponse.from_orm(recording)
        )

    except NotFoundError as e:
        logger.warning(f"录制不存在: {recording_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"暂停录制验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"暂停录制权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"暂停录制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="暂停录制失败"
        )


@router.post(
    "/{recording_id}/resume",
    response_model=PauseRecordingResponse,
    summary="恢复录制",
    description="恢复已暂停的录制：仅已暂停的录制可恢复；采集进程用 SIGCONT 解冻"
)
async def resume_recording(
    recording_id: int = Path(..., description="录制ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    恢复录制

    - **recording_id**: 录制ID（必填）

    注意：只有录制创建者和会议主持人可以恢复录制（与停止同一权限）
    """
    try:
        logger.info(f"用户 {current_user.id} 恢复录制: {recording_id}")

        recording = await recording_service.resume_recording(recording_id, current_user.id)

        logger.info(f"录制恢复成功: 录制ID {recording_id}")

        return PauseRecordingResponse(
            success=True,
            message="录制已恢复",
            data=RecordingResponse.from_orm(recording)
        )

    except NotFoundError as e:
        logger.warning(f"录制不存在: {recording_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"恢复录制验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"恢复录制权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"恢复录制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="恢复录制失败"
        )


@router.get(
    "/{meeting_id}/recordings",
    response_model=RecordingListResponse,
    summary="获取录制列表",
    description="获取会议的录制列表"
)
async def get_recordings(
    meeting_id: int = Path(..., description="会议ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    recording_type: Optional[RecordingTypeEnum] = Query(None, description="录制类型筛选"),
    status_filter: Optional[RecordingStatusEnum] = Query(None, alias="status", description="录制状态筛选"),
    file_format: Optional[FileFormatEnum] = Query(None, description="文件格式筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期筛选"),
    end_date: Optional[datetime] = Query(None, description="结束日期筛选"),
    keyword: Optional[str] = Query(None, max_length=100, description="关键词搜索"),
    sort_by: str = Query("start_time", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    include_deleted: bool = Query(False, description="是否包含已删除"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    获取录制列表
    
    - **meeting_id**: 会议ID（必填）
    - **page**: 页码（默认1）
    - **page_size**: 每页数量（默认20，最大100）
    - **recording_type**: 录制类型筛选（可选）
    - **status**: 录制状态筛选（可选）
    - **file_format**: 文件格式筛选（可选）
    - **start_date**: 开始日期筛选（可选）
    - **end_date**: 结束日期筛选（可选）
    - **keyword**: 关键词搜索（可选）
    - **sort_by**: 排序字段（默认start_time）
    - **sort_order**: 排序方向（默认desc）
    - **include_deleted**: 是否包含已删除（默认false）
    """
    try:
        logger.info(f"用户 {current_user.id} 获取录制列表: 会议 {meeting_id}")
        
        # 构建查询参数
        query_params = RecordingQueryParams(
            page=page,
            page_size=page_size,
            recording_type=recording_type,
            status=status_filter,
            file_format=file_format,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
            sort_by=sort_by,
            sort_order=sort_order,
            include_deleted=include_deleted
        )
        
        # 获取录制列表
        recordings, total, statistics = await recording_service.get_recordings(meeting_id, query_params, current_user.id)
        
        # 计算总页数
        total_pages = (total + page_size - 1) // page_size
        
        return RecordingListResponse(
            recordings=[RecordingResponse.from_orm(r) for r in recordings],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_size_mb=statistics.get('total_size_mb', 0),
            total_duration_minutes=statistics.get('total_duration_minutes', 0)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取录制列表权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取录制列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取录制列表失败"
        )


@router.get(
    "/all",
    response_model=RecordingListResponse,
    summary="获取全局录制列表",
    description="不限会议的全局录制列表（/meetings/recordings 页用）；筛选/分页与按会议列表一致"
)
async def get_all_recordings(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    recording_type: Optional[RecordingTypeEnum] = Query(None, description="录制类型筛选"),
    status_filter: Optional[RecordingStatusEnum] = Query(None, alias="status", description="录制状态筛选"),
    file_format: Optional[FileFormatEnum] = Query(None, description="文件格式筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期筛选"),
    end_date: Optional[datetime] = Query(None, description="结束日期筛选"),
    keyword: Optional[str] = Query(None, max_length=100, description="关键词搜索"),
    sort_by: str = Query("start_time", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    include_deleted: bool = Query(False, description="是否包含已删除"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """全局录制列表：前端 recordingService.getAllRecordings 原调的
    GET /api/v1/recordings 后端并不存在，最终路径定为这里
    （挂在 meetings/recordings 下，与其余录制端点同一前缀）。
    注意路径用 /all 而不用裸 /recordings：GET /api/v1/meetings/recordings
    会被先注册的 GET /api/v1/meetings/{meeting_id}（meeting_id: int）
    截获成 422；/all 须注册在 GET /{recording_id} 之前（与 /statistics
    同理），否则又会被当成 recording_id。"""
    try:
        query_params = RecordingQueryParams(
            page=page, page_size=page_size, recording_type=recording_type,
            status=status_filter, file_format=file_format,
            start_date=start_date, end_date=end_date, keyword=keyword,
            sort_by=sort_by, sort_order=sort_order, include_deleted=include_deleted
        )
        recordings, total, statistics = await recording_service.get_all_recordings(
            query_params, current_user.id
        )
        total_pages = (total + page_size - 1) // page_size
        return RecordingListResponse(
            recordings=[RecordingResponse.from_orm(r) for r in recordings],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
            total_size_mb=statistics.get('total_size_mb', 0),
            total_duration_minutes=statistics.get('total_duration_minutes', 0)
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取全局录制列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取全局录制列表失败"
        )


@router.get(
    "/statistics",
    response_model=RecordingStatistics,
    summary="获取录制统计",
    description="获取录制的统计信息"
)
async def get_recording_statistics(
    meeting_id: Optional[int] = Query(None, description="会议ID筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """注意：本路由必须注册在 GET /{recording_id} 之前，否则
    FastAPI 按注册顺序把 "statistics" 当 recording_id 匹配，int
    校验失败 → 422，统计端点实际不可达（此前就在文件末尾）。"""
    try:
        logger.info(f"用户 {current_user.id} 获取录制统计")
        statistics = await recording_service.get_recording_statistics(
            meeting_id=meeting_id,
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id
        )
        return RecordingStatistics(**statistics)
    except PermissionError as e:
        logger.warning(f"获取录制统计权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取录制统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取录制统计失败"
        )


@router.get(
    "/{recording_id}",
    response_model=RecordingResponse,
    summary="获取录制详情",
    description="获取录制的详细信息"
)
async def get_recording(
    recording_id: int = Path(..., description="录制ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    获取录制详情
    
    - **recording_id**: 录制ID（必填）
    
    返回录制的详细信息，包括文件信息、处理状态等
    """
    try:
        logger.info(f"用户 {current_user.id} 获取录制详情: {recording_id}")
        
        # 获取录制详情
        recording = await recording_service.get_recording_by_id(recording_id, current_user.id)
        
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="录制不存在"
            )
        
        return RecordingResponse.from_orm(recording)
        
    except NotFoundError as e:
        logger.warning(f"录制不存在: {recording_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取录制详情权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取录制详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取录制详情失败"
        )


@router.put(
    "/{recording_id}",
    response_model=RecordingResponse,
    summary="更新录制",
    description="更新录制信息：改名 / 改公开 / 改访问密码（无 description 列，见 schemas）"
)
async def update_recording(
    recording_id: int = Path(..., description="录制ID"),
    request: UpdateRecordingRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """更新录制：只有录制创建者或会议组织者可改。"""
    try:
        logger.info(f"用户 {current_user.id} 更新录制: {recording_id}")
        recording = await recording_service.update_recording(
            recording_id, request, current_user.id
        )
        return RecordingResponse.from_orm(recording)
    except NotFoundError as e:
        logger.warning(f"录制不存在: {recording_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"更新录制验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"更新录制权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新录制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新录制失败"
        )


@router.get(
    "/{recording_id}/playback",
    response_model=PlaybackInfoResponse,
    summary="获取播放信息",
    description="获取录制的播放信息和访问令牌"
)
async def get_playback_info(
    recording_id: int = Path(..., description="录制ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    获取播放信息
    
    - **recording_id**: 录制ID（必填）
    
    返回播放所需的信息，包括播放链接、令牌、字幕等
    """
    try:
        logger.info(f"用户 {current_user.id} 获取播放信息: {recording_id}")

        # 获取播放信息
        playback_info = await recording_service.get_recording_playback_info(recording_id, current_user.id)

        # 服务返回的就是 PlaybackInfoResponse 的扁平结构
        # （recording_id/playback_token/playback_config/expires_at）；
        # 此前这里包了一层 {success, message, data}，与模型字段全对不上，
        # 加上未捕获 ValidationError，GET /playback 恒 500。
        return PlaybackInfoResponse(**playback_info)

    except NotFoundError as e:
        logger.warning(f"录制不存在: {recording_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        # 未完成处理的录制：录制尚未完成处理 → 400，不是 500
        logger.warning(f"获取播放信息验证失败: {recording_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取播放信息权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取播放信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取播放信息失败"
        )


@router.get(
    "/{recording_id}/download",
    summary="下载录制文件",
    description="下载录制文件：Bearer 鉴权或 ?token= 播放令牌（二选一）；复用 PR #5“生成文件 → 下载链接”的 FileResponse 套路"
)
async def download_recording_file(
    recording_id: int = Path(..., description="录制ID"),
    token: Optional[str] = Query(None, description="播放令牌（<video> src 用，见 GET /playback 返回的 video_url）"),
    current_user: Optional[User] = Depends(_get_optional_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """下载录制文件。无文件（无头录制 FAILED / 文件未落盘）时 404，
    不返回空文件；未鉴权时 403。"""
    try:
        user_id = current_user.id if current_user else None
        file_path, filename, media_type = await recording_service.download_recording(
            recording_id, user_id=user_id, token=token
        )
        safe_fallback = "".join(
            ch if ch.isascii() and ch not in {'"', "\\", ";"} else "_"
            for ch in filename
        ) or "recording"
        encoded = quote(filename, safe="")
        return FileResponse(
            path=file_path,
            media_type=media_type,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{safe_fallback}"; '
                    f"filename*=UTF-8''{encoded}"
                )
            },
        )
    except NotFoundError as e:
        logger.warning(f"下载录制失败（不存在/无文件）: {recording_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"下载录制权限不足: {recording_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载录制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="下载录制失败"
        )


@router.delete(
    "/{recording_id}",
    response_model=DeleteRecordingResponse,
    summary="删除录制",
    description="删除录制文件（软删除）"
)
async def delete_recording(
    recording_id: int = Path(..., description="录制ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    删除录制
    
    - **recording_id**: 录制ID（必填）
    
    注意：
    - 只有录制创建者和会议主持人可以删除录制
    - 删除操作为软删除，文件不会立即删除
    - 正在录制中的文件不能删除
    """
    try:
        logger.info(f"用户 {current_user.id} 删除录制: {recording_id}")
        
        # 删除录制
        await recording_service.delete_recording(recording_id, current_user.id)
        
        logger.info(f"录制删除成功: {recording_id}")
        
        return DeleteRecordingResponse(
            success=True,
            message="录制删除成功"
        )
        
    except NotFoundError as e:
        logger.warning(f"录制不存在: {recording_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"删除录制验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"删除录制权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"删除录制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除录制失败"
        )


@router.post(
    "/{recording_id}/share",
    response_model=RecordingShareResponse,
    summary="分享录制",
    description="设置录制的分享权限和生成分享链接"
)
async def share_recording(
    recording_id: int = Path(..., description="录制ID"),
    request: RecordingShareRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    分享录制
    
    - **recording_id**: 录制ID（必填）
    - **is_public**: 是否公开（默认false）
    - **access_password**: 访问密码（可选）
    - **expires_at**: 过期时间（可选）
    - **allowed_users**: 允许访问的用户ID列表（可选）
    - **download_enabled**: 是否允许下载（默认true）
    """
    try:
        logger.info(f"用户 {current_user.id} 分享录制: {recording_id}")
        
        # 分享录制
        share_result = await recording_service.share_recording(recording_id, request, current_user.id)
        
        logger.info(f"录制分享成功: {recording_id}")
        
        return RecordingShareResponse(
            success=True,
            message="分享设置成功",
            share_url=share_result['share_url'],
            share_code=share_result['share_code'],
            expires_at=share_result.get('expires_at')
        )
        
    except NotFoundError as e:
        logger.warning(f"录制不存在: {recording_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"分享录制验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"分享录制权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"分享录制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="分享录制失败"
        )
