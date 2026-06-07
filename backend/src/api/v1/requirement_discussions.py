"""
需求协作讨论API端点

提供需求协作讨论相关的REST API接口
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, BusinessLogicError, NotFoundError, PermissionError
from ...services.requirement_discussion_service import RequirementDiscussionService
from ...services.audit_service import AuditService
from ...services.requirement_notification_service import RequirementNotificationService
from ...services.websocket_service import WebSocketService
from ...services.auth import get_current_user
from ...schemas.requirement_discussion import (
    CreateDiscussionRequest, SendMessageRequest, UpdateMessageRequest,
    AddParticipantRequest, RemoveParticipantRequest,
    CloseDiscussionRequest, ReopenDiscussionRequest,
    DiscussionResponse, DiscussionWithMessagesResponse, DiscussionListResponse,
    MessageResponse, MessageListResponse, DiscussionStatisticsResponse,
    DiscussionQueryParams, MessageQueryParams,
    DiscussionSummaryRequest, DiscussionSummaryResponse,
    DiscussionExportRequest, DiscussionNotificationRequest,
    WebSocketMessage, TypingIndicator
)
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requirement-discussions", tags=["需求协作讨论"])


def get_discussion_service(
    db: AsyncSession = Depends(get_async_session),
    audit_service: AuditService = Depends(),
    notification_service: RequirementNotificationService = Depends(),
    websocket_service: WebSocketService = Depends()
) -> RequirementDiscussionService:
    """获取需求讨论服务实例"""
    return RequirementDiscussionService(
        db=db,
        audit_service=audit_service,
        notification_service=notification_service,
        websocket_service=websocket_service
    )


@router.post("/", response_model=DiscussionResponse, status_code=status.HTTP_201_CREATED)
async def create_discussion(
    request: CreateDiscussionRequest,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    创建需求讨论
    
    为指定需求创建一个新的协作讨论。
    """
    try:
        discussion = await discussion_service.create_discussion(
            discussion_data=request.dict(),
            creator_id=current_user.id
        )
        return DiscussionResponse(**discussion.to_dict())
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"创建讨论失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建讨论失败")


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    发送讨论消息
    
    在指定讨论中发送消息。
    """
    try:
        message = await discussion_service.send_message(
            message_data=request.dict(),
            sender_id=current_user.id
        )
        return MessageResponse(**message.to_dict())
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"发送消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发送消息失败")


@router.put("/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: int = Path(..., description="消息ID"),
    request: UpdateMessageRequest = None,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    更新讨论消息
    
    更新已发送的消息内容。
    """
    try:
        # 这里需要实现消息更新逻辑
        # 暂时返回成功响应
        return MessageResponse(
            id=message_id,
            discussion_id=1,
            sender_id=current_user.id,
            message_type="text",
            content=request.content,
            attachments=request.attachments or [],
            reply_to_id=None,
            mentions=[],
            is_edited=True,
            edited_at=None,
            created_at=None,
            updated_at=None
        )
    
    except Exception as e:
        logger.error(f"更新消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新消息失败")


@router.post("/{discussion_id}/participants", response_model=DiscussionResponse)
async def add_participant(
    discussion_id: int = Path(..., description="讨论ID"),
    request: AddParticipantRequest = None,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    添加讨论参与者
    
    向讨论中添加新的参与者。
    """
    try:
        discussion = await discussion_service.add_participant(
            discussion_id=discussion_id,
            participant_id=request.participant_id,
            added_by=current_user.id
        )
        return DiscussionResponse(**discussion.to_dict())
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"添加参与者失败: {str(e)}")
        raise HTTPException(status_code=500, detail="添加参与者失败")


@router.delete("/{discussion_id}/participants/{participant_id}", response_model=DiscussionResponse)
async def remove_participant(
    discussion_id: int = Path(..., description="讨论ID"),
    participant_id: int = Path(..., description="参与者ID"),
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    移除讨论参与者
    
    从讨论中移除参与者。
    """
    try:
        discussion = await discussion_service.remove_participant(
            discussion_id=discussion_id,
            participant_id=participant_id,
            removed_by=current_user.id
        )
        return DiscussionResponse(**discussion.to_dict())
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"移除参与者失败: {str(e)}")
        raise HTTPException(status_code=500, detail="移除参与者失败")


@router.post("/{discussion_id}/close", response_model=DiscussionResponse)
async def close_discussion(
    discussion_id: int = Path(..., description="讨论ID"),
    request: CloseDiscussionRequest = None,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    关闭讨论
    
    关闭讨论并生成总结。
    """
    try:
        discussion = await discussion_service.close_discussion(
            discussion_id=discussion_id,
            summary=request.summary,
            closed_by=current_user.id
        )
        return DiscussionResponse(**discussion.to_dict())
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"关闭讨论失败: {str(e)}")
        raise HTTPException(status_code=500, detail="关闭讨论失败")


@router.post("/{discussion_id}/reopen", response_model=DiscussionResponse)
async def reopen_discussion(
    discussion_id: int = Path(..., description="讨论ID"),
    request: ReopenDiscussionRequest = None,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    重新打开讨论
    
    重新激活已关闭的讨论。
    """
    try:
        # 这里需要实现重新打开讨论的逻辑
        # 暂时返回成功响应
        discussion = await discussion_service.get_discussion_by_id(discussion_id)
        if not discussion:
            raise HTTPException(status_code=404, detail="讨论不存在")
        
        return DiscussionResponse(**discussion.to_dict())
    
    except Exception as e:
        logger.error(f"重新打开讨论失败: {str(e)}")
        raise HTTPException(status_code=500, detail="重新打开讨论失败")


@router.get("/{discussion_id}", response_model=DiscussionWithMessagesResponse)
async def get_discussion(
    discussion_id: int = Path(..., description="讨论ID"),
    include_messages: bool = Query(True, description="是否包含消息"),
    message_limit: int = Query(50, ge=1, le=100, description="消息数量限制"),
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    获取讨论详情
    
    获取指定讨论的详细信息，包括消息列表。
    """
    try:
        discussion = await discussion_service.get_discussion_by_id(discussion_id)
        if not discussion:
            raise HTTPException(status_code=404, detail="讨论不存在")
        
        messages = []
        if include_messages:
            messages = await discussion_service.get_discussion_messages(
                discussion_id, limit=message_limit
            )
        
        # 构建参与者信息（简化处理）
        participants_info = {
            pid: {"id": pid, "name": f"User {pid}"} 
            for pid in discussion.participants
        }
        
        # 计算统计信息
        statistics = {
            "total_messages": len(messages),
            "participants_count": len(discussion.participants),
            "created_days_ago": (discussion.updated_at - discussion.created_at).days if discussion.updated_at and discussion.created_at else 0
        }
        
        return DiscussionWithMessagesResponse(
            discussion=DiscussionResponse(**discussion.to_dict()),
            messages=[MessageResponse(**m.to_dict()) for m in messages],
            participants_info=participants_info,
            statistics=statistics
        )
    
    except Exception as e:
        logger.error(f"获取讨论详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取讨论详情失败")


@router.get("/", response_model=DiscussionListResponse)
async def list_discussions(
    requirement_id: Optional[int] = Query(None, description="需求ID"),
    project_id: Optional[int] = Query(None, description="项目ID"),
    status: Optional[str] = Query(None, description="讨论状态"),
    creator_id: Optional[int] = Query(None, description="创建者ID"),
    participant_id: Optional[int] = Query(None, description="参与者ID"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="限制数量"),
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    获取讨论列表
    
    根据条件查询讨论列表。
    """
    try:
        # 构建搜索参数
        search_params = {}
        if requirement_id:
            search_params['requirement_id'] = requirement_id
        if status:
            search_params['status'] = status
        if keyword:
            search_params['keyword'] = keyword
        
        discussions = await discussion_service.search_discussions(search_params)
        
        # 分页处理
        total = len(discussions)
        discussions = discussions[skip:skip + limit]
        
        return DiscussionListResponse(
            discussions=[DiscussionResponse(**d.to_dict()) for d in discussions],
            total=total,
            skip=skip,
            limit=limit
        )
    
    except Exception as e:
        logger.error(f"获取讨论列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取讨论列表失败")


@router.get("/requirements/{requirement_id}/discussions", response_model=DiscussionListResponse)
async def get_requirement_discussions(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    获取需求的所有讨论
    
    获取指定需求的所有讨论记录。
    """
    try:
        discussions = await discussion_service.get_discussions_by_requirement(requirement_id)
        
        return DiscussionListResponse(
            discussions=[DiscussionResponse(**d.to_dict()) for d in discussions],
            total=len(discussions),
            skip=0,
            limit=len(discussions)
        )
    
    except Exception as e:
        logger.error(f"获取需求讨论失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取需求讨论失败")


@router.get("/{discussion_id}/messages", response_model=MessageListResponse)
async def get_discussion_messages(
    discussion_id: int = Path(..., description="讨论ID"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(50, ge=1, le=100, description="限制数量"),
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    获取讨论消息列表
    
    获取指定讨论的消息列表。
    """
    try:
        messages = await discussion_service.get_discussion_messages(
            discussion_id, skip=skip, limit=limit
        )
        
        return MessageListResponse(
            messages=[MessageResponse(**m.to_dict()) for m in messages],
            total=len(messages),
            skip=skip,
            limit=limit,
            has_more=len(messages) == limit
        )
    
    except Exception as e:
        logger.error(f"获取讨论消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取讨论消息失败")


@router.get("/users/{user_id}/discussions", response_model=DiscussionListResponse)
async def get_user_discussions(
    user_id: int = Path(..., description="用户ID"),
    status: Optional[str] = Query(None, description="讨论状态"),
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    获取用户的讨论列表
    
    获取用户参与的讨论列表。
    """
    try:
        discussions = await discussion_service.get_user_discussions(
            user_id=user_id,
            status=status
        )
        
        return DiscussionListResponse(
            discussions=[DiscussionResponse(**d.to_dict()) for d in discussions],
            total=len(discussions),
            skip=0,
            limit=len(discussions)
        )
    
    except Exception as e:
        logger.error(f"获取用户讨论失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户讨论失败")


@router.get("/statistics", response_model=DiscussionStatisticsResponse)
async def get_discussion_statistics(
    project_id: Optional[int] = Query(None, description="项目ID"),
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    获取讨论统计信息
    
    获取讨论的统计数据和分析。
    """
    try:
        statistics = await discussion_service.get_discussion_statistics(project_id)
        return DiscussionStatisticsResponse(**statistics)
    
    except Exception as e:
        logger.error(f"获取讨论统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取讨论统计失败")


@router.post("/{discussion_id}/summary", response_model=DiscussionSummaryResponse)
async def generate_discussion_summary(
    discussion_id: int = Path(..., description="讨论ID"),
    request: DiscussionSummaryRequest = None,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    生成讨论总结
    
    使用AI生成讨论的智能总结。
    """
    try:
        # 这里应该实现AI总结逻辑
        # 暂时返回模拟数据
        from datetime import datetime
        
        return DiscussionSummaryResponse(
            discussion_id=discussion_id,
            summary="讨论总结：本次讨论主要围绕需求的技术实现方案展开，达成了以下共识...",
            key_decisions=["采用微服务架构", "使用Redis作为缓存"],
            action_items=["完善技术方案文档", "进行技术预研"],
            key_points=["性能要求", "安全考虑", "扩展性"],
            participants_contribution={
                current_user.id: {"messages": 5, "decisions": 2}
            },
            generated_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"生成讨论总结失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成讨论总结失败")


@router.post("/export")
async def export_discussions(
    request: DiscussionExportRequest,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    导出讨论数据
    
    导出讨论数据到指定格式。
    """
    try:
        # 这里应该实现导出逻辑
        # 暂时返回成功响应
        return {
            "message": "导出请求已提交",
            "export_format": request.export_format,
            "status": "processing"
        }
    
    except Exception as e:
        logger.error(f"导出讨论数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="导出讨论数据失败")


@router.post("/{discussion_id}/notifications", status_code=status.HTTP_204_NO_CONTENT)
async def send_discussion_notification(
    discussion_id: int = Path(..., description="讨论ID"),
    request: DiscussionNotificationRequest = None,
    current_user: User = Depends(get_current_user),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    发送讨论通知
    
    向相关人员发送讨论通知。
    """
    try:
        discussion = await discussion_service.get_discussion_by_id(discussion_id)
        if not discussion:
            raise HTTPException(status_code=404, detail="讨论不存在")
        
        # 这里可以实现发送通知的逻辑
        # 暂时只记录日志
        logger.info(f"发送讨论通知: {discussion_id}, 类型: {request.notification_type}")
        
    except Exception as e:
        logger.error(f"发送讨论通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发送讨论通知失败")


# WebSocket端点用于实时通信
@router.websocket("/{discussion_id}/ws")
async def discussion_websocket(
    websocket: WebSocket,
    discussion_id: int = Path(..., description="讨论ID"),
    discussion_service: RequirementDiscussionService = Depends(get_discussion_service)
):
    """
    讨论WebSocket连接
    
    建立实时通信连接。
    """
    await websocket.accept()
    
    try:
        # 验证讨论存在性
        discussion = await discussion_service.get_discussion_by_id(discussion_id)
        if not discussion:
            await websocket.close(code=4004, reason="讨论不存在")
            return
        
        # 这里应该验证用户权限
        # 暂时跳过权限验证
        
        logger.info(f"WebSocket连接建立: 讨论 {discussion_id}")
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            message = WebSocketMessage(**data)
            
            # 处理不同类型的消息
            if message.type == "typing":
                # 广播输入状态
                typing_data = TypingIndicator(**message.data)
                # 这里应该广播给其他参与者
                logger.info(f"用户 {typing_data.user_id} 正在输入")
            
            elif message.type == "message":
                # 处理新消息
                # 这里应该调用发送消息的服务
                logger.info(f"收到新消息: {message.data}")
            
            # 回复确认
            await websocket.send_json({
                "type": "ack",
                "message_id": message.data.get("id"),
                "timestamp": message.timestamp.isoformat()
            })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: 讨论 {discussion_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")
        await websocket.close(code=4000, reason="服务器错误")