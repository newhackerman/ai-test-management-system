"""
需求协作讨论API端点 - 简化版本

提供需求协作讨论相关的REST API接口
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, BusinessLogicError, NotFoundError, PermissionError
from ...services.requirement_discussion_service import RequirementDiscussionService
from ...services.auth import get_current_user
from ...schemas.requirement_discussion import (
    CreateDiscussionRequest, DiscussionResponse
)
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requirement-discussions", tags=["需求协作讨论"])


@router.post("/", response_model=DiscussionResponse, status_code=status.HTTP_201_CREATED)
async def create_discussion(
    request: CreateDiscussionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    创建需求讨论
    
    为指定需求创建一个新的协作讨论。
    """
    try:
        # Create service instance
        discussion_service = RequirementDiscussionService(db=db)
        
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


@router.get("/{discussion_id}")
async def get_discussion(
    discussion_id: int = Path(..., description="讨论ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取讨论详情
    
    获取指定讨论的详细信息，包括消息列表。
    """
    try:
        discussion_service = RequirementDiscussionService(db=db)
        discussion = await discussion_service.get_discussion_by_id(discussion_id)
        
        if not discussion:
            raise HTTPException(status_code=404, detail="讨论不存在")
        
        return {"discussion": discussion.to_dict()}
    
    except Exception as e:
        logger.error(f"获取讨论详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取讨论详情失败")