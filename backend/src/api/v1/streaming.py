"""
娴佸紡鍝嶅簲API绔偣
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.fastapi_integration import Inject
from ...services.ai_assistant_service import AIAssistantService
from ...services.streaming_service import StreamingService
from ...models.ai_chat_session import SessionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


class StreamMessageRequest(BaseModel):
    """娴佸紡娑堟伅璇锋眰"""
    content: str = Field(..., description="娑堟伅鍐呭", min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = Field(None, description="metadata")


@router.get("/stats", summary="streaming stats")
async def get_streaming_stats():
    return {
        "success": True,
        "stats": {
            "active_sessions": 0,
            "websocket_connections": 0,
            "sse_connections": 0,
            "total_subscribers": 0,
        },
    }

@router.post("/conversations/{conversation_id}/stream", summary="stream message")
async def stream_message(
    conversation_id: int,
    request: StreamMessageRequest,
    db: Session = Depends(get_db),
    ai_service: AIAssistantService = Inject(AIAssistantService)
):
    """
    娴佸紡鍙戦€佹秷鎭苟鑾峰彇AI鍥炲
    
    浣跨敤Server-Sent Events (SSE) 瀹炵幇瀹炴椂娴佸紡鍝嶅簲銆?
    
    浜嬩欢绫诲瀷锛?
    - user_message: 鐢ㄦ埛娑堟伅纭
    - ai_start: AI寮€濮嬪搷搴?
    - ai_content: AI鍝嶅簲鍐呭锛堝閲忥級
    - ai_metadata: AI鍝嶅簲鍏冩暟鎹?
    - ai_complete: AI鍝嶅簲瀹屾垚
    - error: 閿欒淇℃伅
    - stream_end: 娴佺粨鏉?
    """
    try:
        logger.info(f"Starting stream for conversation {conversation_id}")
        
        # TODO: 浠庤璇佷俊鎭幏鍙栫湡瀹炵敤鎴稩D
        user_id = 1
        
        # 鍒涘缓娴佸紡鏈嶅姟
        streaming_service = StreamingService(ai_service)
        
        # 鍒涘缓娴佸紡鍝嶅簲鐢熸垚鍣?
        async def generate_stream():
            async for chunk in streaming_service.stream_ai_response(
                conversation_id=conversation_id,
                user_message=request.content,
                user_id=user_id,
                db=db,
                metadata=request.metadata
            ):
                yield chunk
        
        # 杩斿洖娴佸紡鍝嶅簲
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            }
        )
        
    except Exception as e:
        logger.error(f"Error starting stream for conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"鍚姩娴佸紡鍝嶅簲澶辫触: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/stream/stop", summary="鍋滄娴佸紡鍝嶅簲")
async def stop_stream(
    conversation_id: int,
    stream_id: str,
    ai_service: AIAssistantService = Inject(AIAssistantService)
):
    """
    鍋滄鎸囧畾鐨勬祦寮忓搷搴?
    """
    try:
        logger.info(f"Stopping stream {stream_id} for conversation {conversation_id}")
        
        # 鍒涘缓娴佸紡鏈嶅姟骞跺仠姝㈡祦
        streaming_service = StreamingService(ai_service)
        streaming_service.stop_stream(stream_id)
        
        return {"success": True, "message": "stream stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping stream {stream_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"鍋滄娴佸紡鍝嶅簲澶辫触: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/stream/status", summary="stream status")
async def get_stream_status(
    conversation_id: int,
    ai_service: AIAssistantService = Inject(AIAssistantService)
):
    """
    鑾峰彇瀵硅瘽鐨勬祦寮忓搷搴旂姸鎬?
    """
    try:
        # 鍒涘缓娴佸紡鏈嶅姟
        streaming_service = StreamingService(ai_service)
        
        # 妫€鏌ユ椿璺冪殑娴?
        active_streams = [
            stream_id for stream_id in streaming_service.active_streams.keys()
            if stream_id.startswith(f"{conversation_id}_")
        ]
        
        return {
            "conversation_id": conversation_id,
            "active_streams": active_streams,
            "stream_count": len(active_streams),
            "is_streaming": len(active_streams) > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting stream status for conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"鑾峰彇娴佸紡鍝嶅簲鐘舵€佸け璐? {str(e)}"
        )
