"""
屏幕共享和协作API路由

本模块提供会议协作功能的REST API接口，包括：
- POST /meetings/{meeting_id}/screen-share/start 开始屏幕共享接口
- POST /meetings/{meeting_id}/screen-share/stop 停止屏幕共享接口
- POST /meetings/{meeting_id}/chat/send 发送聊天消息接口
- GET /meetings/{meeting_id}/chat/history 获取聊天历史接口
- POST /meetings/{meeting_id}/files/upload 上传文件接口
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import ValidationError, NotFoundError, PermissionError
from ....services.webrtc_service import WebRTCService, get_webrtc_service
from ....services.meeting_service import MeetingService, get_meeting_service
from ....api.auth import get_current_user
from ....models.user import User
from ....schemas.webrtc_schemas import (
    ScreenShareRequest, ScreenShareResponse,
    StopScreenShareRequest, StopScreenShareResponse
)
from ....schemas.collaboration_schemas import (
    SendChatMessageRequest, ChatMessageResponse, ChatHistoryResponse,
    SendChatMessageResponse, ChatQueryParams, UploadFileRequest,
    FileShareResponse, UploadFileResponse, FileListResponse,
    FileQueryParams, WhiteboardAction, WhiteboardState,
    CreatePollRequest, PollResponse, VotePollRequest,
    MessageTypeEnum, FileShareStatusEnum
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/screen-share/start",
    response_model=ScreenShareResponse,
    summary="开始屏幕共享",
    description="开始屏幕共享，需要相应权限"
)
async def start_screen_share(
    meeting_id: int = Path(..., description="会议ID"),
    request: ScreenShareRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    webrtc_service: WebRTCService = Depends(get_webrtc_service)
):
    """
    开始屏幕共享
    
    - **meeting_id**: 会议ID（必填）
    - **session_id**: 会话ID（必填）
    - **share_type**: 共享类型（screen/window/tab，默认screen）
    - **audio_enabled**: 是否包含音频（默认false）
    - **resolution**: 分辨率（可选）
    """
    try:
        logger.info(f"用户 {current_user.id} 开始屏幕共享: 会议 {meeting_id}")
        
        # 开始屏幕共享
        screen_share = await webrtc_service.start_screen_share(request.session_id, {
            'share_type': request.share_type,
            'audio_enabled': request.audio_enabled,
            'resolution': request.resolution,
            'user_id': current_user.id
        })
        
        logger.info(f"屏幕共享开始成功: 会议 {meeting_id}, 共享ID {screen_share.share_id}")
        
        return ScreenShareResponse(
            success=True,
            message="屏幕共享开始成功",
            share_id=screen_share.share_id,
            stream_info=screen_share.stream_info
        )
        
    except NotFoundError as e:
        logger.warning(f"会话不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"屏幕共享验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"屏幕共享权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"屏幕共享开始失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="屏幕共享开始失败"
        )


@router.post(
    "/screen-share/stop",
    response_model=StopScreenShareResponse,
    summary="停止屏幕共享",
    description="停止当前的屏幕共享"
)
async def stop_screen_share(
    meeting_id: int = Path(..., description="会议ID"),
    request: StopScreenShareRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    webrtc_service: WebRTCService = Depends(get_webrtc_service)
):
    """
    停止屏幕共享
    
    - **meeting_id**: 会议ID（必填）
    - **session_id**: 会话ID（必填）
    - **share_id**: 共享ID（必填）
    """
    try:
        logger.info(f"用户 {current_user.id} 停止屏幕共享: 会议 {meeting_id}, 共享ID {request.share_id}")
        
        # 停止屏幕共享
        await webrtc_service.stop_screen_share(request.session_id, request.share_id, current_user.id)
        
        logger.info(f"屏幕共享停止成功: 会议 {meeting_id}, 共享ID {request.share_id}")
        
        return StopScreenShareResponse(
            success=True,
            message="屏幕共享停止成功"
        )
        
    except NotFoundError as e:
        logger.warning(f"屏幕共享不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"停止屏幕共享权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"停止屏幕共享失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="停止屏幕共享失败"
        )


@router.post(
    "/chat/send",
    response_model=SendChatMessageResponse,
    summary="发送聊天消息",
    description="在会议中发送聊天消息"
)
async def send_chat_message(
    meeting_id: int = Path(..., description="会议ID"),
    request: SendChatMessageRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    发送聊天消息
    
    - **meeting_id**: 会议ID（必填）
    - **content**: 消息内容（必填，1-2000字符）
    - **message_type**: 消息类型（默认TEXT）
    - **is_private**: 是否私聊（默认false）
    - **recipient_id**: 接收者ID（私聊时必填）
    - **reply_to_id**: 回复消息ID（可选）
    - **metadata**: 消息元数据（可选）
    """
    try:
        logger.info(f"用户 {current_user.id} 发送聊天消息: 会议 {meeting_id}")
        
        # 发送聊天消息
        message = await meeting_service.send_chat_message(meeting_id, current_user.id, request)
        
        logger.info(f"聊天消息发送成功: 会议 {meeting_id}, 消息ID {message.id}")
        
        return SendChatMessageResponse(
            success=True,
            message="消息发送成功",
            data=ChatMessageResponse.from_orm(message)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"聊天消息验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"发送聊天消息权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"发送聊天消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送聊天消息失败"
        )


@router.get(
    "/chat/history",
    response_model=ChatHistoryResponse,
    summary="获取聊天历史",
    description="获取会议的聊天历史记录"
)
async def get_chat_history(
    meeting_id: int = Path(..., description="会议ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    message_type: Optional[MessageTypeEnum] = Query(None, description="消息类型筛选"),
    sender_id: Optional[int] = Query(None, description="发送者ID筛选"),
    start_time: Optional[datetime] = Query(None, description="开始时间筛选"),
    end_time: Optional[datetime] = Query(None, description="结束时间筛选"),
    keyword: Optional[str] = Query(None, max_length=100, description="关键词搜索"),
    include_private: bool = Query(False, description="是否包含私聊消息"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取聊天历史
    
    - **meeting_id**: 会议ID（必填）
    - **page**: 页码（默认1）
    - **page_size**: 每页数量（默认50，最大200）
    - **message_type**: 消息类型筛选（可选）
    - **sender_id**: 发送者ID筛选（可选）
    - **start_time**: 开始时间筛选（可选）
    - **end_time**: 结束时间筛选（可选）
    - **keyword**: 关键词搜索（可选）
    - **include_private**: 是否包含私聊消息（默认false）
    """
    try:
        logger.info(f"用户 {current_user.id} 获取聊天历史: 会议 {meeting_id}")
        
        # 构建查询参数
        query_params = ChatQueryParams(
            page=page,
            page_size=page_size,
            message_type=message_type,
            sender_id=sender_id,
            start_time=start_time,
            end_time=end_time,
            keyword=keyword,
            include_private=include_private
        )
        
        # 获取聊天历史
        messages, total = await meeting_service.get_chat_history(meeting_id, query_params, current_user.id)
        
        return ChatHistoryResponse(
            messages=[ChatMessageResponse.from_orm(msg) for msg in messages],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取聊天历史权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取聊天历史失败"
        )


@router.post(
    "/files/upload",
    response_model=UploadFileResponse,
    summary="上传文件",
    description="上传文件到会议中进行共享"
)
async def upload_file(
    meeting_id: int = Path(..., description="会议ID"),
    file: UploadFile = File(..., description="上传的文件"),
    description: Optional[str] = Form(None, description="文件描述"),
    is_public: bool = Form(True, description="是否公开"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    上传文件
    
    - **meeting_id**: 会议ID（必填）
    - **file**: 上传的文件（必填，最大500MB）
    - **description**: 文件描述（可选）
    - **is_public**: 是否公开（默认true）
    
    支持的文件类型：
    - 文档：PDF、Word、PPT、Excel等
    - 图片：JPG、PNG、GIF、SVG等
    - 视频：MP4、AVI、MOV等
    - 压缩包：ZIP、RAR、7Z等
    """
    try:
        logger.info(f"用户 {current_user.id} 上传文件: 会议 {meeting_id}, 文件 {file.filename}")
        
        # 验证文件
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空"
            )
        
        # 构建上传请求
        upload_request = UploadFileRequest(
            file_name=file.filename,
            file_size=file.size or 0,
            file_type=file.content_type or "application/octet-stream",
            mime_type=file.content_type,
            description=description,
            is_public=is_public
        )
        
        # 上传文件
        file_record = await meeting_service.upload_file(meeting_id, current_user.id, upload_request, file)
        
        logger.info(f"文件上传成功: 会议 {meeting_id}, 文件ID {file_record.id}")
        
        return UploadFileResponse(
            success=True,
            message="文件上传成功",
            data=FileShareResponse.from_orm(file_record)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"文件上传验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"文件上传权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败"
        )


@router.get(
    "/files",
    response_model=FileListResponse,
    summary="获取文件列表",
    description="获取会议中共享的文件列表"
)
async def get_files(
    meeting_id: int = Path(..., description="会议ID"),
    file_type: Optional[str] = Query(None, description="文件类型筛选"),
    status: Optional[FileShareStatusEnum] = Query(None, description="文件状态筛选"),
    uploader_id: Optional[int] = Query(None, description="上传者ID筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期筛选"),
    end_date: Optional[datetime] = Query(None, description="结束日期筛选"),
    keyword: Optional[str] = Query(None, max_length=100, description="关键词搜索"),
    include_deleted: bool = Query(False, description="是否包含已删除文件"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取文件列表
    
    - **meeting_id**: 会议ID（必填）
    - **file_type**: 文件类型筛选（可选）
    - **status**: 文件状态筛选（可选）
    - **uploader_id**: 上传者ID筛选（可选）
    - **start_date**: 开始日期筛选（可选）
    - **end_date**: 结束日期筛选（可选）
    - **keyword**: 关键词搜索（可选）
    - **include_deleted**: 是否包含已删除文件（默认false）
    """
    try:
        logger.info(f"用户 {current_user.id} 获取文件列表: 会议 {meeting_id}")
        
        # 构建查询参数
        query_params = FileQueryParams(
            file_type=file_type,
            status=status,
            uploader_id=uploader_id,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword,
            include_deleted=include_deleted
        )
        
        # 获取文件列表
        files, total_size = await meeting_service.get_files(meeting_id, query_params, current_user.id)
        
        return FileListResponse(
            files=[FileShareResponse.from_orm(f) for f in files],
            total=len(files),
            total_size_mb=total_size / (1024 * 1024) if total_size else 0
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取文件列表权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件列表失败"
        )


@router.post(
    "/whiteboard/action",
    summary="白板操作",
    description="执行白板操作（绘制、擦除等）"
)
async def whiteboard_action(
    meeting_id: int = Path(..., description="会议ID"),
    action: WhiteboardAction = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    白板操作
    
    - **meeting_id**: 会议ID（必填）
    - **action_type**: 操作类型（draw/erase/clear/undo/redo）
    - **user_id**: 操作用户ID（必填）
    - **data**: 操作数据（必填）
    - **timestamp**: 操作时间（自动生成）
    """
    try:
        logger.info(f"用户 {current_user.id} 执行白板操作: 会议 {meeting_id}, 类型 {action.action_type}")
        
        # 执行白板操作
        result = await meeting_service.handle_whiteboard_action(meeting_id, current_user.id, action)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "白板操作成功",
                "data": result
            }
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"白板操作权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"白板操作失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="白板操作失败"
        )


@router.get(
    "/whiteboard/state",
    response_model=WhiteboardState,
    summary="获取白板状态",
    description="获取当前白板的状态和内容"
)
async def get_whiteboard_state(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取白板状态
    
    - **meeting_id**: 会议ID（必填）
    
    返回白板的当前状态和内容
    """
    try:
        logger.info(f"用户 {current_user.id} 获取白板状态: 会议 {meeting_id}")
        
        # 获取白板状态
        whiteboard_state = await meeting_service.get_whiteboard_state(meeting_id, current_user.id)
        
        return WhiteboardState(**whiteboard_state)
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取白板状态权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取白板状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取白板状态失败"
        )