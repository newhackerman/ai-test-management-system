"""
模板分享管理API端点

提供模板分享的完整REST API，包括：
1. 分享链接的创建和管理
2. 模板收藏和评分功能
3. 分享访问和权限控制
4. 分享统计和分析
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.auth import get_current_user, get_current_user_optional
from ...models.user import User
from ...services.template_sharing_service import TemplateSharingService
from ...schemas.template_sharing import (
    TemplateShareCreate, TemplateShareUpdate, TemplateShareResponse,
    TemplateShareListResponse, ShareLinkResponse, ShareAccessRequest, ShareAccessResponse,
    TemplateFavoriteCreate, TemplateFavoriteResponse, FavoriteFolderResponse,
    TemplateRatingCreate, TemplateRatingResponse, TemplateCommentCreate, TemplateCommentResponse,
    TemplateCollaboratorInvite, TemplateCollaboratorResponse, ShareStatistics,
    TemplateShareSearchRequest, PublicTemplateSearchRequest, TemplateReportCreate, TemplateReportResponse,
    BatchShareOperation, BatchOperationResult, TemplateExportRequest, TemplateImportRequest, ImportResult
)

router = APIRouter()
sharing_service = TemplateSharingService()


# ==================== 分享链接管理 ====================

@router.post("/templates/{template_id}/share", response_model=TemplateShareResponse, status_code=status.HTTP_201_CREATED)
async def create_share_link(
    template_id: int,
    share_data: TemplateShareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建模板分享链接"""
    try:
        share = await sharing_service.create_share_link(db, template_id, share_data, current_user.id)
        return TemplateShareResponse.from_orm(share)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="创建分享链接失败")


@router.get("/shares/{share_id}", response_model=TemplateShareResponse)
async def get_share_link(
    share_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """获取分享链接信息"""
    user_id = current_user.id if current_user else None
    share = await sharing_service.get_share_link(db, share_id, user_id)
    
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分享链接不存在或无权限访问")
    
    return TemplateShareResponse.from_orm(share)


@router.put("/shares/{share_id}", response_model=TemplateShareResponse)
async def update_share_link(
    share_id: int,
    share_data: TemplateShareUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新分享链接设置"""
    try:
        share = await sharing_service.update_share_link(db, share_id, share_data, current_user.id)
        return TemplateShareResponse.from_orm(share)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新分享链接失败")


@router.delete("/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share_link(
    share_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除分享链接"""
    try:
        await sharing_service.delete_share_link(db, share_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除分享链接失败")


@router.get("/shares/{share_id}/url", response_model=ShareLinkResponse)
async def get_share_url(
    share_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取分享URL"""
    try:
        share = await sharing_service.get_share_link(db, share_id, current_user.id)
        if not share:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分享链接不存在")
        
        share_url = await sharing_service.generate_share_url(share)
        
        return ShareLinkResponse(
            share_id=share.id,
            share_url=share_url,
            share_token=share.share_token,
            expires_at=share.expires_at,
            access_count=share.access_count,
            max_access_count=share.max_access_count
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取分享URL失败")


# ==================== 分享访问 ====================

@router.post("/shared/access", response_model=ShareAccessResponse)
async def access_shared_template(
    access_request: ShareAccessRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """访问分享的模板"""
    try:
        user_id = current_user.id if current_user else None
        template, share = await sharing_service.access_shared_template(
            db, access_request.share_token, access_request.password, user_id
        )
        
        # 构建响应数据
        template_data = {
            "id": template.id,
            "name": template.name,
            "title": template.title,
            "description": template.description,
            "content": template.content,
            "category": template.category,
            "tags": template.tags,
            "created_at": template.created_at,
            "updated_at": template.updated_at
        }
        
        share_info = {
            "share_id": share.id,
            "title": share.title,
            "description": share.description,
            "share_type": share.share_type,
            "created_at": share.created_at
        }
        
        permissions = {
            "can_download": share.allow_download,
            "can_copy": share.allow_copy,
            "can_comment": share.allow_comment
        }
        
        return ShareAccessResponse(
            template=template_data,
            share_info=share_info,
            permissions=permissions
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="访问分享模板失败")


@router.get("/shared/{share_token}")
async def get_shared_template_by_token(
    share_token: str,
    password: Optional[str] = Query(None, description="访问密码"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """通过分享令牌获取模板（用于分享链接直接访问）"""
    try:
        user_id = current_user.id if current_user else None
        template, share = await sharing_service.access_shared_template(
            db, share_token, password, user_id
        )
        
        return {
            "template": {
                "id": template.id,
                "name": template.name,
                "title": template.title,
                "description": template.description,
                "content": template.content,
                "category": template.category,
                "tags": template.tags,
                "variables": template.variables,
                "example_context": template.example_context,
                "created_at": template.created_at
            },
            "share": {
                "title": share.title,
                "description": share.description,
                "allow_download": share.allow_download,
                "allow_copy": share.allow_copy,
                "allow_comment": share.allow_comment
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取分享模板失败")


# ==================== 模板收藏 ====================

@router.post("/templates/{template_id}/favorite", response_model=TemplateFavoriteResponse, status_code=status.HTTP_201_CREATED)
async def add_to_favorites(
    template_id: int,
    favorite_data: TemplateFavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加模板到收藏夹"""
    try:
        favorite = await sharing_service.add_to_favorites(
            db, template_id, current_user.id, favorite_data.folder_name
        )
        return TemplateFavoriteResponse.from_orm(favorite)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="添加收藏失败")


@router.delete("/templates/{template_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_favorites(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从收藏夹移除模板"""
    try:
        await sharing_service.remove_from_favorites(db, template_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="移除收藏失败")


@router.get("/favorites", response_model=Dict[str, Any])
async def get_user_favorites(
    folder_name: Optional[str] = Query(None, description="收藏夹名称筛选"),
    page: int = Query(1, description="页码", ge=1),
    size: int = Query(20, description="每页大小", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户收藏的模板"""
    try:
        return await sharing_service.get_user_favorites(db, current_user.id, folder_name, page, size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取收藏列表失败")


@router.get("/favorites/folders", response_model=List[FavoriteFolderResponse])
async def get_favorite_folders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的收藏夹列表"""
    try:
        folders = await sharing_service.get_favorite_folders(db, current_user.id)
        return [FavoriteFolderResponse(**folder) for folder in folders]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取收藏夹列表失败")


# ==================== 模板评分和评论 ====================

@router.post("/templates/{template_id}/rating", response_model=TemplateRatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_template(
    template_id: int,
    rating_data: TemplateRatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为模板评分"""
    try:
        rating = await sharing_service.rate_template(db, template_id, rating_data, current_user.id)
        return TemplateRatingResponse.from_orm(rating)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="评分失败")


@router.get("/templates/{template_id}/ratings", response_model=Dict[str, Any])
async def get_template_ratings(
    template_id: int,
    page: int = Query(1, description="页码", ge=1),
    size: int = Query(20, description="每页大小", ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取模板的评分列表"""
    try:
        return await sharing_service.get_template_ratings(db, template_id, page, size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取评分列表失败")


@router.post("/templates/{template_id}/comments", response_model=TemplateCommentResponse, status_code=status.HTTP_201_CREATED)
async def add_template_comment(
    template_id: int,
    comment_data: TemplateCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加模板评论"""
    try:
        comment = await sharing_service.add_template_comment(db, template_id, comment_data, current_user.id)
        return TemplateCommentResponse.from_orm(comment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="添加评论失败")


@router.get("/templates/{template_id}/comments", response_model=Dict[str, Any])
async def get_template_comments(
    template_id: int,
    page: int = Query(1, description="页码", ge=1),
    size: int = Query(20, description="每页大小", ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """获取模板的评论列表"""
    try:
        return await sharing_service.get_template_comments(db, template_id, page, size)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取评论列表失败")


# ==================== 分享统计和分析 ====================

@router.get("/shares/statistics", response_model=ShareStatistics)
async def get_share_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的分享统计"""
    try:
        return await sharing_service.get_share_statistics(db, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取分享统计失败")


@router.get("/templates/{template_id}/share-analytics")
async def get_template_share_analytics(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取模板的分享分析数据"""
    try:
        return await sharing_service.get_template_share_analytics(db, template_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取分享分析失败")


# ==================== 用户分享管理 ====================

@router.get("/my-shares", response_model=TemplateShareListResponse)
async def get_my_shares(
    share_type: Optional[str] = Query(None, description="分享类型筛选"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态筛选"),
    template_id: Optional[int] = Query(None, description="模板ID筛选"),
    page: int = Query(1, description="页码", ge=1),
    size: int = Query(20, description="每页大小", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户创建的分享列表"""
    try:
        # 构建搜索请求
        search_request = TemplateShareSearchRequest(
            share_type=share_type,
            status=status_filter,
            owner_id=current_user.id,
            template_id=template_id,
            page=page,
            size=size
        )
        
        return await sharing_service.search_shares(db, search_request, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="获取分享列表失败")


# ==================== 公开模板浏览 ====================

@router.get("/public/templates")
async def browse_public_templates(
    query: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类筛选"),
    tags: Optional[List[str]] = Query(None, description="标签筛选"),
    min_rating: Optional[float] = Query(None, description="最低评分"),
    is_featured: Optional[bool] = Query(None, description="是否精选"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    page: int = Query(1, description="页码", ge=1),
    size: int = Query(20, description="每页大小", ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """浏览公开的模板"""
    try:
        search_request = PublicTemplateSearchRequest(
            query=query,
            category=category,
            tags=tags,
            min_rating=min_rating,
            is_featured=is_featured,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size
        )
        
        return await sharing_service.browse_public_templates(db, search_request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="浏览公开模板失败")


# ==================== 模板举报 ====================

@router.post("/templates/{template_id}/report", response_model=TemplateReportResponse, status_code=status.HTTP_201_CREATED)
async def report_template(
    template_id: int,
    report_data: TemplateReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """举报模板"""
    try:
        # 这里需要在sharing_service中实现report_template方法
        # report = await sharing_service.report_template(db, template_id, report_data, current_user.id)
        # return TemplateReportResponse.from_orm(report)
        
        # 临时返回
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="举报功能暂未实现")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="举报失败")


# ==================== 批量操作 ====================

@router.post("/templates/batch-share", response_model=BatchOperationResult)
async def batch_share_templates(
    batch_operation: BatchShareOperation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量分享模板"""
    try:
        return await sharing_service.batch_share_templates(db, batch_operation, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="批量分享失败")


# ==================== 导入导出 ====================

@router.post("/templates/export")
async def export_templates(
    export_request: TemplateExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出模板"""
    try:
        # 这里需要在sharing_service中实现export_templates方法
        # return await sharing_service.export_templates(db, export_request, current_user.id)
        
        # 临时返回
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="导出功能暂未实现")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="导出失败")


@router.post("/templates/import", response_model=ImportResult)
async def import_templates(
    import_request: TemplateImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导入模板"""
    try:
        # 这里需要在sharing_service中实现import_templates方法
        # return await sharing_service.import_templates(db, import_request, current_user.id)
        
        # 临时返回
        return ImportResult(
            imported_count=0,
            skipped_count=0,
            error_count=1,
            imported_templates=[],
            errors=[{"error": "导入功能暂未实现"}]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="导入失败")