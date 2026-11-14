"""
WebRTC信令API路由

本模块提供WebRTC信令处理的REST API接口，包括：
- WebSocket /meetings/{meeting_id}/ws 信令连接接口
- POST /meetings/{meeting_id}/webrtc/offer SDP offer接口
- POST /meetings/{meeting_id}/webrtc/answer SDP answer接口
- POST /meetings/{meeting_id}/webrtc/ice ICE候选接口
- GET /meetings/{meeting_id}/webrtc/config 获取WebRTC配置接口
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import ValidationError, NotFoundError, PermissionError
from ....utils.jwt import verify_token
from ....services.webrtc_service import WebRTCService, get_webrtc_service
from ....services.meeting_service import MeetingService, get_meeting_service
from ....api.auth import get_current_user
from ....models.user import User
from ....schemas.webrtc_schemas import (
    WebRTCSignalRequest, WebRTCOfferRequest, WebRTCAnswerRequest,
    ICECandidateRequest, MediaControlRequest, WebRTCConfigResponse,
    WebRTCSignalResponse, ScreenShareRequest, ScreenShareResponse,
    StopScreenShareRequest, StopScreenShareResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    meeting_id: int = Path(..., description="会议ID"),
    token: Optional[str] = Query(None, description="JWT 访问令牌"),
    webrtc_service: WebRTCService = Depends(get_webrtc_service),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    WebSocket信令连接

    建立WebSocket连接用于实时信令交换。连接前必须验证 JWT（query 参数
    token），并校验用户对该会议的访问权限；未通过时直接拒绝握手，
    不再以匿名身份（user_id=None）加入房间。

    - **meeting_id**: 会议ID（必填）

    WebSocket消息格式：
    ```json
    {
        "type": "offer|answer|ice-candidate|media-control|room-event",
        "data": {...}
    }
    ```
    """
    # 认证必须在 accept() 之前完成：未提供、无效或过期的令牌直接拒绝。
    # 只接受 type=access 的访问令牌，refresh/reset 令牌不能用于建连。
    user_id: Optional[int] = None
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    # 会议访问权限：组织者、拥有 meeting:view 权限者或参会者才能加入。
    try:
        await meeting_service.get_meeting_by_id(meeting_id, user_id)
    except NotFoundError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Meeting not found")
        return
    except PermissionError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access denied")
        return

    await websocket.accept()

    session = None
    room_id = webrtc_service.room_id_for_meeting(meeting_id)
    try:
        logger.info(f"WebSocket连接建立: 会议 {meeting_id}, 用户 {user_id}")

        # 房间生命周期方案 (a)：join 前按需 get-or-create。房间 ID 统一为
        # room_{meeting_id}（create_room 不再带时间戳后缀），房间不存在
        # 时不再抛 NotFoundError 导致 1011 关闭。注意房间只存后端进程
        # 内存，重启即丢，已加入者需重新建连。
        await webrtc_service.get_or_create_room(meeting_id)

        # 加入WebRTC房间
        session = await webrtc_service.join_room(room_id, user_id, {})

        # 注册WebSocket连接
        await webrtc_service.register_websocket(session.session_id, websocket)

        # 告诉新加入者房间现状：自己的 session_id 与已在房间的其他人，
        # 前端据此向每位已在场者发起 offer（mesh 建连的起点）。
        room_info = await webrtc_service.get_room_info(room_id)
        existing = [
            {"user_id": uid, "session_id": s.session_id}
            for uid, s in (room_info.participants if room_info else {}).items()
            if uid != user_id
        ]
        await websocket.send_json({
            "type": "room-joined",
            "room_id": room_id,
            "meeting_id": meeting_id,
            "session_id": session.session_id,
            "user_id": user_id,
            "participants": existing,
        })

        while True:
            # 接收WebSocket消息
            data = await websocket.receive_json()

            # 处理信令消息
            await webrtc_service.handle_websocket_message(session.session_id, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: 会议 {meeting_id}, 用户 {user_id}")

        # 清理连接
        if session is not None:
            await webrtc_service.leave_room(session.room_id, session.user_id)

    except (NotFoundError, PermissionError, ValidationError) as e:
        # 加入房间失败（会议被删/无权限/房间已满）是可预期的拒绝，
        # 用 1008 关连接并说明原因，不要走 1011。
        logger.warning(f"WebSocket加入房间失败: 会议 {meeting_id}, 用户 {user_id}: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=str(e)[:120])

    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        await websocket.close(code=1011, reason="Internal server error")


@router.post(
    "/offer",
    response_model=WebRTCSignalResponse,
    summary="发送SDP Offer",
    description="发送WebRTC SDP Offer信令"
)
async def send_offer(
    meeting_id: int = Path(..., description="会议ID"),
    request: WebRTCOfferRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    webrtc_service: WebRTCService = Depends(get_webrtc_service)
):
    """
    发送SDP Offer
    
    - **meeting_id**: 会议ID（必填）
    - **session_id**: 会话ID（必填）
    - **sdp**: SDP描述（必填）
    - **media_constraints**: 媒体约束（可选）
    """
    try:
        logger.info(f"用户 {current_user.id} 发送SDP Offer: 会议 {meeting_id}, 会话 {request.session_id}")
        
        # 处理SDP Offer
        result = await webrtc_service.handle_offer(request.session_id, {
            'sdp': request.sdp,
            'media_constraints': request.media_constraints
        })
        if not result.get('success'):
            raise NotFoundError(result.get('error') or "会话不存在")
        
        return WebRTCSignalResponse(
            success=True,
            message="SDP Offer处理成功",
            signal_id=result.get('signal_id'),
            response_data=result.get('response_data')
        )
        
    except NotFoundError as e:
        logger.warning(f"会话不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"SDP Offer验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"SDP Offer处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SDP Offer处理失败"
        )


@router.post(
    "/answer",
    response_model=WebRTCSignalResponse,
    summary="发送SDP Answer",
    description="发送WebRTC SDP Answer信令"
)
async def send_answer(
    meeting_id: int = Path(..., description="会议ID"),
    request: WebRTCAnswerRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    webrtc_service: WebRTCService = Depends(get_webrtc_service)
):
    """
    发送SDP Answer
    
    - **meeting_id**: 会议ID（必填）
    - **session_id**: 会话ID（必填）
    - **sdp**: SDP描述（必填）
    """
    try:
        logger.info(f"用户 {current_user.id} 发送SDP Answer: 会议 {meeting_id}, 会话 {request.session_id}")
        
        # 处理SDP Answer
        result = await webrtc_service.handle_answer(request.session_id, {
            'sdp': request.sdp
        })
        if not result.get('success'):
            raise NotFoundError(result.get('error') or "会话不存在")
        
        return WebRTCSignalResponse(
            success=True,
            message="SDP Answer处理成功",
            signal_id=result.get('signal_id'),
            response_data=result.get('response_data')
        )
        
    except NotFoundError as e:
        logger.warning(f"会话不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"SDP Answer验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"SDP Answer处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SDP Answer处理失败"
        )


@router.post(
    "/ice",
    response_model=WebRTCSignalResponse,
    summary="发送ICE候选",
    description="发送WebRTC ICE候选信令"
)
async def send_ice_candidate(
    meeting_id: int = Path(..., description="会议ID"),
    request: ICECandidateRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    webrtc_service: WebRTCService = Depends(get_webrtc_service)
):
    """
    发送ICE候选
    
    - **meeting_id**: 会议ID（必填）
    - **session_id**: 会话ID（必填）
    - **candidate**: ICE候选（必填）
    - **sdp_mid**: SDP MID（可选）
    - **sdp_m_line_index**: SDP M-Line索引（可选）
    """
    try:
        logger.info(f"用户 {current_user.id} 发送ICE候选: 会议 {meeting_id}, 会话 {request.session_id}")
        
        # 处理ICE候选
        result = await webrtc_service.handle_ice_candidate(request.session_id, {
            'candidate': request.candidate,
            'sdp_mid': request.sdp_mid,
            'sdp_m_line_index': request.sdp_m_line_index
        })
        if not result.get('success'):
            raise NotFoundError(result.get('error') or "会话不存在")
        
        return WebRTCSignalResponse(
            success=True,
            message="ICE候选处理成功",
            signal_id=result.get('signal_id'),
            response_data=result.get('response_data')
        )
        
    except NotFoundError as e:
        logger.warning(f"会话不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"ICE候选验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"ICE候选处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ICE候选处理失败"
        )


@router.get(
    "/config",
    response_model=WebRTCConfigResponse,
    summary="获取WebRTC配置",
    description="获取WebRTC连接配置信息"
)
async def get_webrtc_config(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    webrtc_service: WebRTCService = Depends(get_webrtc_service),
    meeting_service: MeetingService = Depends(get_meeting_service)
):
    """
    获取WebRTC配置
    
    - **meeting_id**: 会议ID（必填）
    
    返回WebRTC连接所需的配置信息，包括ICE服务器、媒体约束等
    """
    try:
        logger.info(f"用户 {current_user.id} 获取WebRTC配置: 会议 {meeting_id}")
        
        # 验证会议权限
        meeting = await meeting_service.get_meeting_by_id(meeting_id, current_user.id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会议不存在"
            )
        
        # 获取WebRTC配置
        config = await webrtc_service.get_webrtc_config(meeting_id, current_user.id)
        
        return WebRTCConfigResponse(
            ice_servers=config['ice_servers'],
            media_constraints=config['media_constraints'],
            room_config=config['room_config'],
            session_config=config['session_config']
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取WebRTC配置权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取WebRTC配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取WebRTC配置失败"
        )


@router.post(
    "/media-control",
    response_model=WebRTCSignalResponse,
    summary="媒体控制",
    description="控制音视频媒体流"
)
async def media_control(
    meeting_id: int = Path(..., description="会议ID"),
    request: MediaControlRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    webrtc_service: WebRTCService = Depends(get_webrtc_service)
):
    """
    媒体控制
    
    - **meeting_id**: 会议ID（必填）
    - **session_id**: 会话ID（必填）
    - **media_type**: 媒体类型（audio/video/screen）
    - **action**: 控制动作（mute/unmute/enable/disable）
    - **target_user_id**: 目标用户ID（可选，用于控制其他用户）
    """
    try:
        logger.info(f"用户 {current_user.id} 媒体控制: 会议 {meeting_id}, 类型 {request.media_type}, 动作 {request.action}")
        
        # 处理媒体控制
        result = await webrtc_service.handle_media_control(request.session_id, {
            'media_type': request.media_type,
            'action': request.action,
            'target_user_id': request.target_user_id,
            'user_id': current_user.id
        })
        if not result.get('success'):
            raise NotFoundError(result.get('error') or "会话不存在")
        
        return WebRTCSignalResponse(
            success=True,
            message="媒体控制成功",
            signal_id=result.get('signal_id'),
            response_data=result.get('response_data')
        )
        
    except NotFoundError as e:
        logger.warning(f"会话不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"媒体控制验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"媒体控制权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"媒体控制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="媒体控制失败"
        )