"""
需求评审API端点

提供需求评审相关的REST API接口
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, BusinessLogicError, NotFoundError, PermissionError
from ...services.requirement_review_service import RequirementReviewService
from ...services.ai_router_service import AIRouterService
from ...services.audit_service import AuditService
from ...services.requirement_notification_service import RequirementNotificationService
from ...services.auth import get_current_user
from ...schemas.requirement_review import (
    CreateReviewRequest, StartReviewRequest, SubmitCommentRequest,
    ResolveCommentRequest, CompleteReviewRequest, CancelReviewRequest,
    ReviewResponse, ReviewWithCommentsResponse, ReviewListResponse,
    ReviewCommentResponse, ReviewStatisticsResponse,
    ReviewQueryParams, CommentQueryParams,
    BatchResolveCommentsRequest, BatchUpdateCommentsRequest,
    ReviewExportRequest, ReviewNotificationRequest
)
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requirement-reviews", tags=["需求评审"])


async def get_review_service(db: AsyncSession = Depends(get_async_session)) -> RequirementReviewService:
    """获取评审服务"""
    return RequirementReviewService(db=db)


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    request: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    创建需求评审
    
    创建一个新的需求评审，指定评审类型、主持人和评审人员。
    """
    try:
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


@router.post("/{review_id}/start", response_model=ReviewResponse)
async def start_review(
    review_id: int = Path(..., description="评审ID"),
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    开始评审
    
    由评审主持人启动评审流程。
    """
    try:
        review = await review_service.start_review(
            review_id=review_id,
            moderator_id=current_user.id
        )
        return ReviewResponse.from_orm(review)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"开始评审失败: {str(e)}")
        raise HTTPException(status_code=500, detail="开始评审失败")


@router.post("/comments", response_model=ReviewCommentResponse, status_code=status.HTTP_201_CREATED)
async def submit_comment(
    request: SubmitCommentRequest,
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    提交评审意见
    
    评审人员提交对需求的评审意见和建议。
    """
    try:
        comment = await review_service.submit_review_comment(
            comment_data=request.dict(),
            reviewer_id=current_user.id
        )
        return ReviewCommentResponse.from_orm(comment)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"提交评审意见失败: {str(e)}")
        raise HTTPException(status_code=500, detail="提交评审意见失败")


@router.put("/comments/{comment_id}/resolve", response_model=ReviewCommentResponse)
async def resolve_comment(
    comment_id: int = Path(..., description="评审意见ID"),
    request: ResolveCommentRequest = None,
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    解决评审意见
    
    处理和解决评审过程中提出的意见。
    """
    try:
        comment = await review_service.resolve_comment(
            comment_id=comment_id,
            resolution=request.resolution,
            resolved_by=current_user.id
        )
        return ReviewCommentResponse.from_orm(comment)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"解决评审意见失败: {str(e)}")
        raise HTTPException(status_code=500, detail="解决评审意见失败")


@router.post("/{review_id}/complete", response_model=ReviewResponse)
async def complete_review(
    review_id: int = Path(..., description="评审ID"),
    request: CompleteReviewRequest = None,
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    完成评审
    
    由评审主持人完成评审并做出最终决策。
    """
    try:
        review = await review_service.complete_review(
            review_id=review_id,
            decision=request.decision,
            summary=request.summary,
            moderator_id=current_user.id
        )
        return ReviewResponse.from_orm(review)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"完成评审失败: {str(e)}")
        raise HTTPException(status_code=500, detail="完成评审失败")


@router.post("/{review_id}/cancel", response_model=ReviewResponse)
async def cancel_review(
    review_id: int = Path(..., description="评审ID"),
    request: CancelReviewRequest = None,
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    取消评审
    
    取消正在进行的评审。
    """
    try:
        review = await review_service.cancel_review(
            review_id=review_id,
            reason=request.reason,
            cancelled_by=current_user.id
        )
        return ReviewResponse.from_orm(review)
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"取消评审失败: {str(e)}")
        raise HTTPException(status_code=500, detail="取消评审失败")


@router.get("/{review_id}", response_model=ReviewWithCommentsResponse)
async def get_review(
    review_id: int = Path(..., description="评审ID"),
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    获取评审详情
    
    获取指定评审的详细信息，包括评审意见。
    """
    try:
        review = await review_service.get_review_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="评审不存在")
        
        comments = await review_service.get_review_comments(review_id)
        
        # 计算统计信息
        statistics = {
            "total_comments": len(comments),
            "issue_comments": len([c for c in comments if c.comment_type.value == "ISSUE"]),
            "resolved_comments": len([c for c in comments if c.status.value == "RESOLVED"]),
            "critical_issues": len([c for c in comments if c.severity and c.severity.value == "CRITICAL"])
        }
        
        return ReviewWithCommentsResponse(
            review=ReviewResponse.from_orm(review),
            comments=[ReviewCommentResponse.from_orm(c) for c in comments],
            statistics=statistics
        )
    
    except Exception as e:
        logger.error(f"获取评审详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评审详情失败")


@router.get("/", response_model=ReviewListResponse)
async def list_reviews(
    requirement_id: Optional[int] = Query(None, description="需求ID"),
    review_type: Optional[str] = Query(None, description="评审类型"),
    review_status: Optional[str] = Query(None, description="评审状态"),
    moderator_id: Optional[int] = Query(None, description="主持人ID"),
    reviewer_id: Optional[int] = Query(None, description="评审人ID"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="限制数量"),
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    获取评审列表
    
    根据条件查询评审列表。
    """
    try:
        # 构建查询参数
        query_params = ReviewQueryParams(
            requirement_id=requirement_id,
            review_type=review_type,
            review_status=review_status,
            moderator_id=moderator_id,
            reviewer_id=reviewer_id,
            skip=skip,
            limit=limit
        )
        
        # 如果指定了reviewer_id，获取评审人的评审
        if reviewer_id:
            reviews = await review_service.get_reviewer_reviews(
                reviewer_id=reviewer_id,
                status=query_params.review_status
            )
            total = len(reviews)
            reviews = reviews[skip:skip + limit]
        else:
            # 这里需要实现通用的搜索方法
            reviews = []
            total = 0
        
        return ReviewListResponse(
            reviews=[ReviewResponse.from_orm(r) for r in reviews],
            total=total,
            skip=skip,
            limit=limit
        )
    
    except Exception as e:
        logger.error(f"获取评审列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评审列表失败")


@router.get("/requirements/{requirement_id}/reviews", response_model=ReviewListResponse)
async def get_requirement_reviews(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    获取需求的所有评审
    
    获取指定需求的所有评审记录。
    """
    try:
        reviews = await review_service.get_reviews_by_requirement(requirement_id)
        
        return ReviewListResponse(
            reviews=[ReviewResponse.from_orm(r) for r in reviews],
            total=len(reviews),
            skip=0,
            limit=len(reviews)
        )
    
    except Exception as e:
        logger.error(f"获取需求评审失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取需求评审失败")


@router.get("/{review_id}/comments", response_model=List[ReviewCommentResponse])
async def get_review_comments(
    review_id: int = Path(..., description="评审ID"),
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    获取评审意见列表
    
    获取指定评审的所有意见。
    """
    try:
        comments = await review_service.get_review_comments(review_id)
        return [ReviewCommentResponse.from_orm(c) for c in comments]
    
    except Exception as e:
        logger.error(f"获取评审意见失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评审意见失败")


@router.get("/users/{user_id}/reviews", response_model=ReviewListResponse)
async def get_user_reviews(
    user_id: int = Path(..., description="用户ID"),
    status: Optional[str] = Query(None, description="评审状态"),
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    获取用户的评审列表
    
    获取用户作为主持人或评审人的评审列表。
    """
    try:
        from ...models.requirement import ReviewStatus
        review_status = ReviewStatus(status) if status else None
        
        reviews = await review_service.get_reviewer_reviews(
            reviewer_id=user_id,
            status=review_status
        )
        
        return ReviewListResponse(
            reviews=[ReviewResponse.from_orm(r) for r in reviews],
            total=len(reviews),
            skip=0,
            limit=len(reviews)
        )
    
    except Exception as e:
        logger.error(f"获取用户评审失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户评审失败")


@router.get("/statistics", response_model=ReviewStatisticsResponse)
async def get_review_statistics(
    project_id: Optional[int] = Query(None, description="项目ID"),
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    获取评审统计信息
    
    获取评审的统计数据和分析。
    """
    try:
        statistics = await review_service.get_review_statistics(project_id)
        return ReviewStatisticsResponse(**statistics)
    
    except Exception as e:
        logger.error(f"获取评审统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取评审统计失败")


@router.post("/comments/batch-resolve", response_model=List[ReviewCommentResponse])
async def batch_resolve_comments(
    request: BatchResolveCommentsRequest,
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    批量解决评审意见
    
    批量处理多个评审意见。
    """
    try:
        resolved_comments = []
        for comment_id in request.comment_ids:
            try:
                comment = await review_service.resolve_comment(
                    comment_id=comment_id,
                    resolution=request.resolution,
                    resolved_by=current_user.id
                )
                resolved_comments.append(ReviewCommentResponse.from_orm(comment))
            except Exception as e:
                logger.warning(f"解决评审意见 {comment_id} 失败: {str(e)}")
                continue
        
        return resolved_comments
    
    except Exception as e:
        logger.error(f"批量解决评审意见失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量解决评审意见失败")


@router.post("/{review_id}/notifications", status_code=status.HTTP_204_NO_CONTENT)
async def send_review_notification(
    review_id: int = Path(..., description="评审ID"),
    request: ReviewNotificationRequest = None,
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    发送评审通知
    
    向相关人员发送评审通知。
    """
    try:
        review = await review_service.get_review_by_id(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="评审不存在")
        
        # 这里可以实现发送通知的逻辑
        # 暂时只记录日志
        logger.info(f"发送评审通知: {review_id}, 类型: {request.notification_type}")
        
    except Exception as e:
        logger.error(f"发送评审通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail="发送评审通知失败")


@router.post("/export")
async def export_reviews(
    request: ReviewExportRequest,
    current_user: User = Depends(get_current_user),
    review_service: RequirementReviewService = Depends(get_review_service)
):
    """
    导出评审数据
    
    导出评审数据到指定格式。
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
        logger.error(f"导出评审数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="导出评审数据失败")