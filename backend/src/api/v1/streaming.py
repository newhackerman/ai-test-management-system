"""
流式响应API端点（SSE）

提供 AI 助手流式输出的 Server-Sent Events 接口：
- POST /query/stream：无状态流式查询（前端 AI 助手页面使用，不依赖服务端会话）
- POST /conversations/{id}/stream：基于服务端会话的流式消息
- POST /conversations/{id}/stream/stop：停止指定的流式响应
- GET /conversations/{id}/stream/status：查询会话的流式状态
- GET /stats：流式连接统计

事件类型：
- ai_start: AI 开始响应（含 provider/model/task_type）
- ai_content: AI 响应内容增量
- ai_metadata: AI 响应元数据
- ai_complete: AI 响应完成（含 usage 统计）
- error: 错误信息
- stream_end: 流结束
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.fastapi_integration import Inject
from ...models.user import User
from ..auth import get_current_user
from ...services.ai_assistant_service import AIAssistantService, UserQuery
from ...services.streaming_service import StreamingService

logger = logging.getLogger(__name__)

router = APIRouter()

# 模块级活跃流注册表，用于统计与停止
_active_streams: Dict[str, bool] = {}


class StreamQueryRequest(BaseModel):
    """无状态流式查询请求"""
    content: str = Field(..., description="查询内容", min_length=1, max_length=10000)
    context: Optional[Dict[str, Any]] = Field(None, description="查询上下文")
    conversation_id: Optional[int] = Field(None, description="对话ID（可选）")
    preferred_model: Optional[str] = Field(None, description="用户指定的模型名称，覆盖默认模型")


class StreamMessageRequest(BaseModel):
    """流式消息请求"""
    content: str = Field(..., description="消息内容", min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = Field(None, description="metadata")


def _format_sse_data(event_type: str, data: Dict[str, Any]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_headers() -> Dict[str, str]:
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


@router.get("/stats", summary="流式连接统计")
async def get_streaming_stats():
    return {
        "success": True,
        "stats": {
            "active_streams": len(_active_streams),
            "stream_ids": list(_active_streams.keys()),
        },
    }


@router.post("/query/stream", summary="无状态流式AI查询")
async def stream_query(
    request: StreamQueryRequest,
    db: Session = Depends(get_db),
    ai_service: AIAssistantService = Inject(AIAssistantService),
    current_user: User = Depends(get_current_user),
):
    """
    无状态流式AI查询：接收与 POST /ai-assistant/query 相同的请求体，
    以 SSE 流式返回 AI 响应，不要求预先创建服务端会话。
    当传入 conversation_id 时，会自动持久化用户消息与 AI 回复到该会话。
    """
    from ...services.conversation_service_sync import ConversationServiceSync, Message
    from ...models.ai_chat_message import MessageRole, ContentType

    user_query = UserQuery(
        content=request.content,
        user_id=current_user.id,
        conversation_id=request.conversation_id,
        context={
            **(request.context or {}),
            "preferred_model": request.preferred_model,
        },
    )

    async def generate():
        stream_id = f"query_{current_user.id}_{datetime.utcnow().timestamp()}"
        _active_streams[stream_id] = True

        conversation_service = ConversationServiceSync(db) if request.conversation_id else None
        saved_user_msg_id = None

        # 当存在会话时，先持久化用户消息并加载历史上下文
        if conversation_service and request.conversation_id:
            try:
                user_msg = Message(
                    role=MessageRole.USER,
                    content=request.content,
                    content_type=ContentType.TEXT,
                    metadata=request.context or {},
                )
                saved = conversation_service.add_message(
                    conversation_id=request.conversation_id,
                    message=user_msg,
                )
                saved_user_msg_id = saved.id

                history = conversation_service.get_messages(
                    conversation_id=request.conversation_id, limit=10
                )
                prior_history = [
                    {"role": m.role.value, "content": m.content, "timestamp": m.created_at.isoformat()}
                    for m in history[:-1]
                ]
                user_query.context["conversation_history"] = prior_history
            except Exception as exc:
                logger.warning(f"Failed to persist user message for conversation {request.conversation_id}: {exc}")

        ai_content = ""
        ai_provider = None
        ai_model = None
        ai_tokens = 0
        try:
            async for chunk in ai_service.stream_user_query(user_query, user_id=current_user.id):
                if chunk.type == "metadata":
                    ai_provider = chunk.metadata.get("provider")
                    ai_model = chunk.metadata.get("model")
                    yield _format_sse_data("ai_start", chunk.metadata)
                elif chunk.type == "content":
                    ai_content = chunk.metadata.get("total_content", ai_content)
                    yield _format_sse_data("ai_content", {
                        "delta": chunk.content,
                        "content": ai_content,
                    })
                elif chunk.type == "complete":
                    ai_content = chunk.metadata.get("total_content", ai_content)
                    ai_provider = chunk.metadata.get("provider", ai_provider)
                    ai_model = chunk.metadata.get("model", ai_model)
                    ai_tokens = int(chunk.metadata.get("tokens_used", 0))
                    yield _format_sse_data("ai_metadata", {
                        "provider": ai_provider,
                        "model": ai_model,
                    })
                    yield _format_sse_data("ai_complete", {
                        "content": ai_content,
                        "provider": ai_provider,
                        "model": ai_model,
                        "tokens_used": ai_tokens,
                        "confidence_score": chunk.metadata.get("confidence_score", 0.0),
                        "processing_time": chunk.metadata.get("processing_time"),
                        "user_message_id": saved_user_msg_id,
                    })
                elif chunk.type == "error":
                    yield _format_sse_data("error", {
                        "message": chunk.metadata.get("error") or "AI 服务调用失败",
                    })
        except Exception as exc:
            logger.error(f"Error in stream query for user {current_user.id}: {str(exc)}")
            yield _format_sse_data("error", {"message": f"流式响应失败: {str(exc)}"})
        finally:
            # 流式完成后持久化 AI 回复
            if conversation_service and request.conversation_id and ai_content:
                try:
                    ai_msg = Message(
                        role=MessageRole.ASSISTANT,
                        content=ai_content,
                        content_type=ContentType.TEXT,
                        metadata={
                            "streaming": True,
                            "user_message_id": saved_user_msg_id,
                        },
                    )
                    conversation_service.add_message(
                        conversation_id=request.conversation_id,
                        message=ai_msg,
                        ai_provider=ai_provider,
                        ai_model=ai_model,
                        tokens_used=ai_tokens,
                        confidence_score=0.9,
                    )
                except Exception as exc:
                    logger.warning(f"Failed to persist AI message for conversation {request.conversation_id}: {exc}")
            _active_streams.pop(stream_id, None)
            yield _format_sse_data("stream_end", {"timestamp": datetime.utcnow().isoformat()})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.post("/conversations/{conversation_id}/stream", summary="基于会话的流式消息")
async def stream_message(
    conversation_id: int,
    request: StreamMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ai_service: AIAssistantService = Inject(AIAssistantService),
):
    """
    向指定会话流式发送消息并获取AI回复，会持久化用户消息与AI回复。
    """
    logger.info(f"Starting stream for conversation {conversation_id} by user {current_user.id}")

    streaming_service = StreamingService(ai_service)

    async def generate_stream():
        async for chunk in streaming_service.stream_ai_response(
            conversation_id=conversation_id,
            user_message=request.content,
            user_id=current_user.id,
            db=db,
            metadata=request.metadata,
        ):
            yield chunk

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.post("/conversations/{conversation_id}/stream/stop", summary="停止流式响应")
async def stop_stream(
    conversation_id: int,
    stream_id: str,
    current_user: User = Depends(get_current_user),
    ai_service: AIAssistantService = Inject(AIAssistantService),
):
    """
    停止指定的流式响应
    """
    try:
        logger.info(f"Stopping stream {stream_id} for conversation {conversation_id}")
        streaming_service = StreamingService(ai_service)
        streaming_service.stop_stream(stream_id)
        return {"success": True, "message": "stream stopped"}
    except Exception as e:
        logger.error(f"Error stopping stream {stream_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止流式响应失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/stream/status", summary="会话流式状态")
async def get_stream_status(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    ai_service: AIAssistantService = Inject(AIAssistantService),
):
    """
    获取对话的流式响应状态
    """
    active_streams = [
        stream_id for stream_id in _active_streams
        if stream_id.startswith(f"{conversation_id}_")
    ]

    return {
        "conversation_id": conversation_id,
        "active_streams": active_streams,
        "stream_count": len(active_streams),
        "is_streaming": len(active_streams) > 0,
    }
