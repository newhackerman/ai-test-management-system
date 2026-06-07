"""
需求评审API端点 - 简化版本

提供需求评审相关的REST API接口
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, BusinessLogicError, NotFoundError, PermissionError
from ...services.requirement_review_service import RequirementReviewService
from ...services.auth import get_current_user
from ...schemas.requirement_review import (
    CreateReviewRequest, ReviewResponse
)
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requirement-reviews", tags=["需求评审"])


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    request: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    创建需求评审
    
    创建一个新的需求评审，指定评审类型、主持人和评审人员。
    """
    try:
        # Create service instance
        review_service = RequirementReviewService(db=db)
        
        review = await review_service.create_review(
            review_data=request.dict(),
            creator_id=current_user.id
        )
        return ReviewResponse.from_orm(review)
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"创建评审失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建评审失败")


@router.get("/{review_id}")
async def get_review(
    review_id: int = Path(..., description="评审ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取评审详情
    
    获取指定评审的详细信息，包括评审意见。
    """
    try:
        review_service = RequirementReviewService(db=db)
        review = await review_service.get_review_by_id(review_id)
        
        if not review:
            raise HTTPException(status_code=404, detail="评审不存在")
        
        return {"review": review.to_dict() if hasattr(review, 'to_dict') else review}
    
    except Exception as e:
        logger.error(f"获取评审详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评审详情失败")