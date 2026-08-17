"""
流式响应服务
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.ai_chat_message import AIChatMessage, MessageRole, ContentType
from ..models.ai_chat_session import AIChatSession
from .ai_assistant_service import AIAssistantService, UserQuery
from .conversation_service_sync import ConversationServiceSync, Message

logger = logging.getLogger(__name__)


class StreamingService:
    """流式响应服务"""
    
    def __init__(self, ai_service: AIAssistantService):
        self.ai_service = ai_service
        self.active_streams = {}  # 存储活跃的流式连接
    
    async def stream_ai_response(
        self,
        conversation_id: int,
        user_message: str,
        user_id: int,
        db: Session,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式生成AI响应
        
        Args:
            conversation_id: 对话ID
            user_message: 用户消息
            user_id: 用户ID
            db: 数据库会话
            metadata: 消息元数据
            
        Yields:
            str: SSE格式的流式数据
        """
        stream_id = f"{conversation_id}_{user_id}_{datetime.now().timestamp()}"
        self.active_streams[stream_id] = True
        
        try:
            # 1. 验证对话存在
            conversation_service = ConversationServiceSync(db)
            conversation = conversation_service.get_conversation(conversation_id, user_id)
            
            if not conversation:
                yield self._format_sse_error("对话不存在或无访问权限")
                return
            
            # 2. 保存用户消息
            user_msg = Message(
                role=MessageRole.USER,
                content=user_message,
                content_type=ContentType.TEXT,
                metadata=metadata or {}
            )
            
            saved_user_message = conversation_service.add_message(
                conversation_id=conversation_id,
                message=user_msg
            )
            
            # 发送用户消息确认
            yield self._format_sse_data("user_message", {
                "id": saved_user_message.id,
                "content": user_message,
                "timestamp": saved_user_message.created_at.isoformat()
            })
            
            # 3. 构建对话上下文
            recent_messages = conversation_service.get_messages(
                conversation_id=conversation_id,
                limit=10
            )
            
            conversation_context = []
            for msg in recent_messages[:-1]:  # 排除刚添加的用户消息
                conversation_context.append({
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat()
                })
            
            # 4. 开始流式AI响应
            yield self._format_sse_data("ai_start", {
                "provider": conversation.ai_provider,
                "model": conversation.ai_model,
                "timestamp": datetime.now().isoformat()
            })
            
            # 构建AI查询
            user_query = UserQuery(
                content=user_message,
                user_id=user_id,
                conversation_id=conversation_id,
                context={
                    "conversation_history": conversation_context,
                    "conversation_title": conversation.title,
                    "ai_provider": conversation.ai_provider,
                    "ai_model": conversation.ai_model,
                    "system_prompt": conversation.system_prompt,
                    "streaming": True,
                    "user_metadata": metadata or {}
                }
            )
            
            # 5. 流式调用AI服务
            ai_response_content = ""
            ai_provider = None
            ai_model = None
            tokens_used = 0
            confidence_score = 0.0
            
            try:
                if hasattr(self.ai_service, 'stream_user_query'):
                    # 使用流式API（StreamingChunk 为普通对象，通过属性访问）
                    async for chunk in self.ai_service.stream_user_query(user_query):
                        if not self.active_streams.get(stream_id, False):
                            break

                        if chunk.type == 'content':
                            content_delta = chunk.content
                            ai_response_content += content_delta

                            yield self._format_sse_data("ai_content", {
                                "delta": content_delta,
                                "content": ai_response_content
                            })

                        elif chunk.type == 'metadata':
                            ai_provider = chunk.metadata.get('provider')
                            ai_model = chunk.metadata.get('model')
                            yield self._format_sse_data("ai_metadata", {
                                "provider": ai_provider,
                                "model": ai_model,
                                "task_type": chunk.metadata.get('task_type')
                            })

                        elif chunk.type == 'complete':
                            ai_provider = chunk.metadata.get('provider', ai_provider)
                            ai_model = chunk.metadata.get('model', ai_model)
                            tokens_used = chunk.metadata.get('tokens_used', tokens_used)
                            confidence_score = chunk.metadata.get('confidence_score', confidence_score)
                            ai_response_content = chunk.metadata.get('total_content', ai_response_content)

                        # 添加小延迟以模拟真实的流式响应
                        await asyncio.sleep(0.05)
                
                else:
                    # 降级到非流式API，模拟流式效果
                    ai_response = await self.ai_service.process_user_query(user_query)
                    ai_response_content = ai_response.content
                    ai_provider = ai_response.provider.value
                    ai_model = ai_response.model
                    tokens_used = ai_response.tokens_used
                    confidence_score = ai_response.confidence_score
                    
                    # 模拟流式输出
                    words = ai_response_content.split()
                    current_content = ""
                    
                    for i, word in enumerate(words):
                        if not self.active_streams.get(stream_id, False):
                            break
                        
                        current_content += word + " "
                        
                        yield self._format_sse_data("ai_content", {
                            "delta": word + " ",
                            "content": current_content.strip()
                        })
                        
                        # 每几个词发送一次，模拟真实的流式响应
                        if i % 3 == 0:
                            await asyncio.sleep(0.1)
                    
                    # 发送元数据
                    yield self._format_sse_data("ai_metadata", {
                        "provider": ai_provider,
                        "model": ai_model,
                        "tokens_used": tokens_used,
                        "confidence_score": confidence_score
                    })
                
                # 6. 保存AI响应消息
                if ai_response_content and self.active_streams.get(stream_id, False):
                    ai_message = Message(
                        role=MessageRole.ASSISTANT,
                        content=ai_response_content,
                        content_type=ContentType.TEXT,
                        metadata={
                            "ai_provider": ai_provider,
                            "ai_model": ai_model,
                            "confidence_score": confidence_score,
                            "streaming": True
                        }
                    )
                    
                    saved_ai_message = conversation_service.add_message(
                        conversation_id=conversation_id,
                        message=ai_message,
                        ai_provider=ai_provider,
                        ai_model=ai_model,
                        tokens_used=tokens_used,
                        confidence_score=confidence_score
                    )
                    
                    # 发送完成信号
                    yield self._format_sse_data("ai_complete", {
                        "id": saved_ai_message.id,
                        "content": ai_response_content,
                        "provider": ai_provider,
                        "model": ai_model,
                        "tokens_used": tokens_used,
                        "confidence_score": confidence_score,
                        "timestamp": saved_ai_message.created_at.isoformat()
                    })
                
            except Exception as ai_error:
                logger.error(f"AI streaming error: {str(ai_error)}")
                
                # 保存错误消息
                error_message = Message(
                    role=MessageRole.ASSISTANT,
                    content=f"抱歉，AI助手暂时无法回复您的消息。错误信息：{str(ai_error)}",
                    content_type=ContentType.TEXT,
                    metadata={"error": True, "error_message": str(ai_error)}
                )
                
                saved_error_message = conversation_service.add_message(
                    conversation_id=conversation_id,
                    message=error_message,
                    ai_provider="error",
                    ai_model="error"
                )
                
                yield self._format_sse_error(str(ai_error), {
                    "id": saved_error_message.id,
                    "timestamp": saved_error_message.created_at.isoformat()
                })
        
        except Exception as e:
            logger.error(f"Streaming service error: {str(e)}")
            yield self._format_sse_error(f"流式响应服务错误: {str(e)}")
        
        finally:
            # 清理流式连接
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            
            # 发送结束信号
            yield self._format_sse_data("stream_end", {
                "timestamp": datetime.now().isoformat()
            })
    
    def stop_stream(self, stream_id: str):
        """停止指定的流式响应"""
        if stream_id in self.active_streams:
            self.active_streams[stream_id] = False
    
    def _format_sse_data(self, event_type: str, data: Dict[str, Any]) -> str:
        """格式化SSE数据"""
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    def _format_sse_error(self, error_message: str, data: Optional[Dict[str, Any]] = None) -> str:
        """格式化SSE错误数据"""
        error_data = {
            "error": True,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        if data:
            error_data.update(data)
        
        return f"event: error\ndata: {json.dumps(error_data, ensure_ascii=False)}\n\n"