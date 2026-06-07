"""
模板分享服务

本模块提供提示词模板的分享功能，包括：
1. 模板分享链接生成和管理
2. 团队模板共享和权限控制
3. 模板收藏和评分系统
4. 分享统计和分析

技术特性：
- 支持多种分享方式（链接、团队、公开）
- 权限控制和访问限制
- 分享统计和使用分析
- 模板评分和反馈系统
"""
import asyncio
import json
import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from math import ceil
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, update
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..models.ai_prompt_template import AIPromptTemplate, AIPromptTemplateUsage, TemplateVisibility
from ..models.template_sharing import (
    TemplateShare, TemplateShareAccess, TemplateFavorite, 
    TemplateRating, TemplateComment, ShareType, ShareStatus
)
from ..schemas.template_sharing import (
    TemplateShareCreate, TemplateShareResponse, TemplateShareUpdate,
    TemplateShareListResponse, ShareLinkResponse, ShareAccessResponse,
    TemplateFavoriteResponse, TemplateRatingCreate, TemplateRatingResponse,
    TemplateCommentCreate, TemplateCommentResponse, ShareStatistics
)

logger = logging.getLogger(__name__)
settings = get_settings()


class TemplateSharingService:
    """模板分享服务"""
    
    def __init__(self):
        self.share_url_base = settings.FRONTEND_URL or "http://localhost:3000"
    
    # ==================== 分享链接管理 ====================
    
    async def create_share_link(self, db: AsyncSession, template_id: int, 
                              share_data: TemplateShareCreate, user_id: int) -> TemplateShare:
        """创建分享链接"""
        # 验证模板存在且有权限
        template = await self._get_template_with_permission(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限分享")
        
        # 检查是否已存在相同类型的分享
        existing_share = await self._get_existing_share(
            db, template_id, user_id, share_data.share_type
        )
        if existing_share and existing_share.status == ShareStatus.ACTIVE:
            raise ValueError(f"已存在活跃的{share_data.share_type.value}分享")
        
        # 生成分享令牌
        share_token = self._generate_share_token(template_id, user_id)
        
        # 创建分享记录
        share = TemplateShare(
            template_id=template_id,
            owner_id=user_id,
            share_type=share_data.share_type.value,
            share_token=share_token,
            title=share_data.title or template.title,
            description=share_data.description or template.description,
            password=share_data.password,
            expires_at=share_data.expires_at,
            max_access_count=share_data.max_access_count,
            allow_download=share_data.allow_download,
            allow_copy=share_data.allow_copy,
            allow_comment=share_data.allow_comment,
            require_login=share_data.require_login,
            allowed_users=share_data.allowed_users,
            allowed_teams=share_data.allowed_teams,
            status=ShareStatus.ACTIVE.value
        )
        
        db.add(share)
        await db.commit()
        await db.refresh(share)
        
        logger.info(f"Created template share: template_id={template_id}, share_id={share.id}")
        return share
    
    async def get_share_link(self, db: AsyncSession, share_id: int, 
                           user_id: Optional[int] = None) -> Optional[TemplateShare]:
        """获取分享链接信息"""
        query = select(TemplateShare).where(TemplateShare.id == share_id)
        
        # 权限检查
        if user_id:
            query = query.where(
                or_(
                    TemplateShare.owner_id == user_id,
                    TemplateShare.share_type == ShareType.PUBLIC.value,
                    and_(
                        TemplateShare.share_type == ShareType.TEAM.value,
                        TemplateShare.allowed_teams.contains([user_id])  # 简化的团队检查
                    ),
                    and_(
                        TemplateShare.share_type == ShareType.PRIVATE.value,
                        TemplateShare.allowed_users.contains([user_id])
                    )
                )
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_share_by_token(self, db: AsyncSession, share_token: str) -> Optional[TemplateShare]:
        """根据分享令牌获取分享信息"""
        query = select(TemplateShare).where(
            and_(
                TemplateShare.share_token == share_token,
                TemplateShare.status == ShareStatus.ACTIVE.value
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_share_link(self, db: AsyncSession, share_id: int, 
                              share_data: TemplateShareUpdate, user_id: int) -> TemplateShare:
        """更新分享链接"""
        share = await self.get_share_link(db, share_id, user_id)
        if not share:
            raise ValueError("分享链接不存在或无权限访问")
        
        if share.owner_id != user_id:
            raise ValueError("只有分享创建者可以修改分享设置")
        
        # 更新字段
        update_data = share_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == 'share_type' and value:
                value = value.value
            elif field == 'status' and value:
                value = value.value
            
            setattr(share, field, value)
        
        share.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(share)
        
        logger.info(f"Updated template share: share_id={share_id}")
        return share
    
    async def delete_share_link(self, db: AsyncSession, share_id: int, user_id: int) -> bool:
        """删除分享链接"""
        share = await self.get_share_link(db, share_id, user_id)
        if not share:
            raise ValueError("分享链接不存在或无权限访问")
        
        if share.owner_id != user_id:
            raise ValueError("只有分享创建者可以删除分享")
        
        # 软删除：设置状态为已删除
        share.status = ShareStatus.DELETED.value
        share.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"Deleted template share: share_id={share_id}")
        return True
    
    async def generate_share_url(self, share: TemplateShare) -> str:
        """生成分享URL"""
        params = {
            'token': share.share_token,
            'type': share.share_type
        }
        
        if share.password:
            params['protected'] = 'true'
        
        query_string = urlencode(params)
        return f"{self.share_url_base}/shared/template?{query_string}"
    
    # ==================== 分享访问管理 ====================
    
    async def access_shared_template(self, db: AsyncSession, share_token: str, 
                                   access_password: Optional[str] = None,
                                   user_id: Optional[int] = None) -> Tuple[AIPromptTemplate, TemplateShare]:
        """访问分享的模板"""
        # 获取分享信息
        share = await self.get_share_by_token(db, share_token)
        if not share:
            raise ValueError("分享链接不存在或已失效")
        
        # 检查分享状态
        if share.status != ShareStatus.ACTIVE.value:
            raise ValueError("分享链接已被禁用")
        
        # 检查过期时间
        if share.expires_at and share.expires_at < datetime.utcnow():
            raise ValueError("分享链接已过期")
        
        # 检查访问次数限制
        if share.max_access_count and share.access_count >= share.max_access_count:
            raise ValueError("分享链接访问次数已达上限")
        
        # 检查密码保护
        if share.password and access_password != share.password:
            raise ValueError("分享密码错误")
        
        # 检查登录要求
        if share.require_login and not user_id:
            raise ValueError("访问此分享需要登录")
        
        # 检查用户权限
        if share.share_type == ShareType.PRIVATE.value:
            if not user_id or (share.allowed_users and user_id not in share.allowed_users):
                raise ValueError("无权限访问此分享")
        
        # 检查团队权限
        if share.share_type == ShareType.TEAM.value:
            if not user_id:
                raise ValueError("访问团队分享需要登录")
            # TODO: 实现真正的团队成员检查
            if share.allowed_teams and not self._check_user_in_teams(user_id, share.allowed_teams):
                raise ValueError("不是指定团队成员，无权限访问")
        
        # 获取模板
        template = await self._get_template_by_id(db, share.template_id)
        if not template:
            raise ValueError("分享的模板不存在")
        
        # 记录访问
        await self._record_share_access(db, share.id, user_id)
        
        # 更新访问计数
        share.access_count += 1
        share.last_accessed_at = datetime.utcnow()
        await db.commit()
        
        return template, share
    
    async def _record_share_access(self, db: AsyncSession, share_id: int, 
                                 user_id: Optional[int]) -> TemplateShareAccess:
        """记录分享访问"""
        access = TemplateShareAccess(
            share_id=share_id,
            user_id=user_id,
            access_ip=None,  # TODO: 从请求中获取IP
            user_agent=None  # TODO: 从请求中获取User-Agent
        )
        
        db.add(access)
        await db.commit()
        await db.refresh(access)
        
        return access
    
    # ==================== 模板收藏功能 ====================
    
    async def add_to_favorites(self, db: AsyncSession, template_id: int, 
                             user_id: int, folder_name: Optional[str] = None) -> TemplateFavorite:
        """添加模板到收藏夹"""
        # 检查模板是否存在且可访问
        template = await self._get_template_with_access(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 检查是否已收藏
        existing = await self._get_favorite(db, template_id, user_id)
        if existing:
            raise ValueError("模板已在收藏夹中")
        
        # 创建收藏记录
        favorite = TemplateFavorite(
            template_id=template_id,
            user_id=user_id,
            folder_name=folder_name or "默认收藏夹"
        )
        
        db.add(favorite)
        await db.commit()
        await db.refresh(favorite)
        
        logger.info(f"Added template to favorites: template_id={template_id}, user_id={user_id}")
        return favorite
    
    async def remove_from_favorites(self, db: AsyncSession, template_id: int, user_id: int) -> bool:
        """从收藏夹移除模板"""
        favorite = await self._get_favorite(db, template_id, user_id)
        if not favorite:
            raise ValueError("模板不在收藏夹中")
        
        await db.delete(favorite)
        await db.commit()
        
        logger.info(f"Removed template from favorites: template_id={template_id}, user_id={user_id}")
        return True
    
    async def get_user_favorites(self, db: AsyncSession, user_id: int, 
                               folder_name: Optional[str] = None,
                               page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取用户收藏的模板"""
        query = select(TemplateFavorite).where(TemplateFavorite.user_id == user_id)
        
        if folder_name:
            query = query.where(TemplateFavorite.folder_name == folder_name)
        
        # 总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.order_by(desc(TemplateFavorite.created_at))
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await db.execute(query)
        favorites = result.scalars().all()
        
        # 获取模板详情
        template_ids = [fav.template_id for fav in favorites]
        templates = await self._get_templates_by_ids(db, template_ids, user_id)
        
        # 组合结果
        favorite_templates = []
        for favorite in favorites:
            template = next((t for t in templates if t.id == favorite.template_id), None)
            if template:
                favorite_templates.append({
                    "favorite_id": favorite.id,
                    "template": template,
                    "folder_name": favorite.folder_name,
                    "favorited_at": favorite.created_at
                })
        
        pages = ceil(total / size) if total > 0 else 0
        
        return {
            "favorites": favorite_templates,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    
    async def get_favorite_folders(self, db: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的收藏夹列表"""
        query = select(
            TemplateFavorite.folder_name,
            func.count(TemplateFavorite.id).label('count')
        ).where(
            TemplateFavorite.user_id == user_id
        ).group_by(TemplateFavorite.folder_name)
        
        result = await db.execute(query)
        folders = result.fetchall()
        
        return [
            {
                "folder_name": folder.folder_name,
                "template_count": folder.count
            }
            for folder in folders
        ]
    
    # ==================== 模板评分和评论 ====================
    
    async def rate_template(self, db: AsyncSession, template_id: int, 
                          rating_data: TemplateRatingCreate, user_id: int) -> TemplateRating:
        """为模板评分"""
        # 检查模板是否存在且可访问
        template = await self._get_template_with_access(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 检查是否已评分
        existing_rating = await self._get_user_rating(db, template_id, user_id)
        if existing_rating:
            # 更新现有评分
            existing_rating.rating = rating_data.rating
            existing_rating.comment = rating_data.comment
            existing_rating.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(existing_rating)
            
            # 重新计算平均评分
            await self._update_template_rating(db, template_id)
            
            logger.info(f"Updated template rating: template_id={template_id}, user_id={user_id}")
            return existing_rating
        else:
            # 创建新评分
            rating = TemplateRating(
                template_id=template_id,
                user_id=user_id,
                rating=rating_data.rating,
                comment=rating_data.comment
            )
            
            db.add(rating)
            await db.commit()
            await db.refresh(rating)
            
            # 更新模板平均评分
            await self._update_template_rating(db, template_id)
            
            logger.info(f"Created template rating: template_id={template_id}, user_id={user_id}")
            return rating
    
    async def get_template_ratings(self, db: AsyncSession, template_id: int, 
                                 page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取模板的评分列表"""
        query = select(TemplateRating).where(TemplateRating.template_id == template_id)
        
        # 总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.order_by(desc(TemplateRating.created_at))
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await db.execute(query)
        ratings = result.scalars().all()
        
        pages = ceil(total / size) if total > 0 else 0
        
        return {
            "ratings": [TemplateRatingResponse.from_orm(rating) for rating in ratings],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    
    async def add_template_comment(self, db: AsyncSession, template_id: int, 
                                 comment_data: TemplateCommentCreate, user_id: int) -> TemplateComment:
        """添加模板评论"""
        # 检查模板是否存在且可访问
        template = await self._get_template_with_access(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 创建评论
        comment = TemplateComment(
            template_id=template_id,
            user_id=user_id,
            content=comment_data.content,
            parent_comment_id=comment_data.parent_comment_id
        )
        
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        
        logger.info(f"Added template comment: template_id={template_id}, user_id={user_id}")
        return comment
    
    async def get_template_comments(self, db: AsyncSession, template_id: int, 
                                  page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取模板的评论列表"""
        query = select(TemplateComment).where(
            and_(
                TemplateComment.template_id == template_id,
                TemplateComment.parent_comment_id.is_(None)  # 只获取顶级评论
            )
        )
        
        # 总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.order_by(desc(TemplateComment.created_at))
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await db.execute(query)
        comments = result.scalars().all()
        
        # 获取子评论
        comment_responses = []
        for comment in comments:
            replies = await self._get_comment_replies(db, comment.id)
            comment_responses.append({
                "comment": TemplateCommentResponse.from_orm(comment),
                "replies": [TemplateCommentResponse.from_orm(reply) for reply in replies]
            })
        
        pages = ceil(total / size) if total > 0 else 0
        
        return {
            "comments": comment_responses,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }
    
    # ==================== 分享统计和分析 ====================
    
    async def get_share_statistics(self, db: AsyncSession, user_id: int) -> ShareStatistics:
        """获取用户的分享统计"""
        # 分享总数
        total_shares_result = await db.execute(
            select(func.count()).where(TemplateShare.owner_id == user_id)
        )
        total_shares = total_shares_result.scalar()
        
        # 活跃分享数
        active_shares_result = await db.execute(
            select(func.count()).where(
                and_(
                    TemplateShare.owner_id == user_id,
                    TemplateShare.status == ShareStatus.ACTIVE.value
                )
            )
        )
        active_shares = active_shares_result.scalar()
        
        # 总访问次数
        total_access_result = await db.execute(
            select(func.sum(TemplateShare.access_count)).where(TemplateShare.owner_id == user_id)
        )
        total_access = total_access_result.scalar() or 0
        
        # 分享类型分布
        share_type_result = await db.execute(
            select(TemplateShare.share_type, func.count()).where(
                TemplateShare.owner_id == user_id
            ).group_by(TemplateShare.share_type)
        )
        share_type_distribution = {row[0]: row[1] for row in share_type_result.fetchall()}
        
        # 最受欢迎的分享
        popular_shares_query = select(TemplateShare).where(
            TemplateShare.owner_id == user_id
        ).order_by(desc(TemplateShare.access_count)).limit(5)
        
        popular_result = await db.execute(popular_shares_query)
        popular_shares = [
            TemplateShareResponse.from_orm(share) for share in popular_result.scalars().all()
        ]
        
        return ShareStatistics(
            total_shares=total_shares,
            active_shares=active_shares,
            total_access=total_access,
            share_type_distribution=share_type_distribution,
            popular_shares=popular_shares
        )
    
    async def get_template_share_analytics(self, db: AsyncSession, template_id: int, 
                                         user_id: int) -> Dict[str, Any]:
        """获取模板的分享分析数据"""
        # 验证权限
        template = await self._get_template_with_permission(db, template_id, user_id)
        if not template:
            raise ValueError("模板不存在或无权限访问")
        
        # 分享总数
        shares_query = select(TemplateShare).where(TemplateShare.template_id == template_id)
        shares_result = await db.execute(shares_query)
        shares = shares_result.scalars().all()
        
        # 访问统计
        total_access = sum(share.access_count for share in shares)
        
        # 按时间统计访问量（最近30天）
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_access_query = select(TemplateShareAccess).where(
            and_(
                TemplateShareAccess.share_id.in_([share.id for share in shares]),
                TemplateShareAccess.created_at >= thirty_days_ago
            )
        )
        recent_access_result = await db.execute(recent_access_query)
        recent_accesses = recent_access_result.scalars().all()
        
        # 按日期分组统计
        daily_access = {}
        for access in recent_accesses:
            date_key = access.created_at.date().isoformat()
            daily_access[date_key] = daily_access.get(date_key, 0) + 1
        
        return {
            "template_id": template_id,
            "total_shares": len(shares),
            "active_shares": len([s for s in shares if s.status == ShareStatus.ACTIVE.value]),
            "total_access": total_access,
            "recent_access_trend": daily_access,
            "share_details": [
                {
                    "share_id": share.id,
                    "share_type": share.share_type,
                    "access_count": share.access_count,
                    "created_at": share.created_at,
                    "last_accessed_at": share.last_accessed_at
                }
                for share in shares
            ]
        }
    
    # ==================== 搜索和浏览功能 ====================
    
    async def search_shares(self, db: AsyncSession, search_request, user_id: int) -> TemplateShareListResponse:
        """搜索用户的分享"""
        query = select(TemplateShare).where(TemplateShare.owner_id == user_id)
        
        # 应用筛选条件
        if search_request.share_type:
            query = query.where(TemplateShare.share_type == search_request.share_type)
        
        if search_request.status:
            query = query.where(TemplateShare.status == search_request.status)
        
        if search_request.template_id:
            query = query.where(TemplateShare.template_id == search_request.template_id)
        
        # 总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.order_by(desc(TemplateShare.created_at))
        offset = (search_request.page - 1) * search_request.size
        query = query.offset(offset).limit(search_request.size)
        
        result = await db.execute(query)
        shares = result.scalars().all()
        
        pages = ceil(total / search_request.size) if total > 0 else 0
        
        return TemplateShareListResponse(
            shares=[TemplateShareResponse.from_orm(share) for share in shares],
            total=total,
            page=search_request.page,
            size=search_request.size,
            pages=pages
        )
    
    async def browse_public_templates(self, db: AsyncSession, search_request) -> Dict[str, Any]:
        """浏览公开模板"""
        # 构建查询：只查询公开分享的模板
        query = select(AIPromptTemplate).join(TemplateShare).where(
            and_(
                TemplateShare.share_type == ShareType.PUBLIC.value,
                TemplateShare.status == ShareStatus.ACTIVE.value,
                or_(
                    TemplateShare.expires_at.is_(None),
                    TemplateShare.expires_at > datetime.utcnow()
                )
            )
        )
        
        # 应用搜索条件
        if search_request.query:
            search_term = f"%{search_request.query}%"
            query = query.where(
                or_(
                    AIPromptTemplate.title.ilike(search_term),
                    AIPromptTemplate.description.ilike(search_term),
                    TemplateShare.title.ilike(search_term)
                )
            )
        
        if search_request.category:
            query = query.where(AIPromptTemplate.category == search_request.category)
        
        if search_request.tags:
            # 简化的标签搜索
            for tag in search_request.tags:
                query = query.where(AIPromptTemplate.tags.contains([tag]))
        
        if search_request.min_rating:
            query = query.where(AIPromptTemplate.rating_avg >= search_request.min_rating)
        
        # 排序
        if search_request.sort_by == "rating":
            order_col = AIPromptTemplate.rating_avg
        elif search_request.sort_by == "usage":
            order_col = AIPromptTemplate.usage_count
        else:
            order_col = AIPromptTemplate.created_at
        
        if search_request.sort_order == "asc":
            query = query.order_by(asc(order_col))
        else:
            query = query.order_by(desc(order_col))
        
        # 总数查询
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        offset = (search_request.page - 1) * search_request.size
        query = query.offset(offset).limit(search_request.size)
        
        result = await db.execute(query)
        templates = result.scalars().all()
        
        pages = ceil(total / search_request.size) if total > 0 else 0
        
        return {
            "templates": [
                {
                    "id": template.id,
                    "title": template.title,
                    "description": template.description,
                    "category": template.category,
                    "tags": template.tags,
                    "rating_avg": template.rating_avg,
                    "rating_count": template.rating_count,
                    "usage_count": template.usage_count,
                    "created_at": template.created_at
                }
                for template in templates
            ],
            "total": total,
            "page": search_request.page,
            "size": search_request.size,
            "pages": pages
        }
    
    # ==================== 批量操作功能 ====================
    
    async def batch_share_templates(self, db: AsyncSession, batch_operation, user_id: int):
        """批量分享模板"""
        success_items = []
        failed_items = []
        
        for template_id in batch_operation.template_ids:
            try:
                # 验证模板权限
                template = await self._get_template_with_permission(db, template_id, user_id)
                if not template:
                    failed_items.append({
                        "id": template_id,
                        "error": "模板不存在或无权限"
                    })
                    continue
                
                # 创建分享
                if batch_operation.share_settings:
                    share = await self.create_share_link(
                        db, template_id, batch_operation.share_settings, user_id
                    )
                    success_items.append({
                        "id": template_id,
                        "share_id": share.id,
                        "share_token": share.share_token
                    })
                else:
                    failed_items.append({
                        "id": template_id,
                        "error": "缺少分享设置"
                    })
                    
            except Exception as e:
                failed_items.append({
                    "id": template_id,
                    "error": str(e)
                })
        
        return {
            "success_count": len(success_items),
            "failed_count": len(failed_items),
            "success_items": success_items,
            "failed_items": failed_items
        }
    
    # ==================== 辅助方法 ====================
    
    def _generate_share_token(self, template_id: int, user_id: int) -> str:
        """生成分享令牌"""
        # 使用模板ID、用户ID、时间戳和随机数生成唯一令牌
        timestamp = str(int(datetime.utcnow().timestamp()))
        random_str = secrets.token_urlsafe(16)
        raw_token = f"{template_id}:{user_id}:{timestamp}:{random_str}"
        
        # 使用SHA256哈希生成最终令牌
        return hashlib.sha256(raw_token.encode()).hexdigest()[:32]
    
    async def _get_template_with_permission(self, db: AsyncSession, template_id: int, 
                                          user_id: int) -> Optional[AIPromptTemplate]:
        """获取有权限的模板"""
        query = select(AIPromptTemplate).where(
            and_(
                AIPromptTemplate.id == template_id,
                AIPromptTemplate.owner_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_template_with_access(self, db: AsyncSession, template_id: int, 
                                      user_id: int) -> Optional[AIPromptTemplate]:
        """获取可访问的模板"""
        query = select(AIPromptTemplate).where(
            and_(
                AIPromptTemplate.id == template_id,
                or_(
                    AIPromptTemplate.owner_id == user_id,
                    AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value,
                    and_(
                        AIPromptTemplate.visibility == TemplateVisibility.TEAM.value,
                        AIPromptTemplate.team_id.isnot(None)
                    )
                )
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_template_by_id(self, db: AsyncSession, template_id: int) -> Optional[AIPromptTemplate]:
        """根据ID获取模板"""
        query = select(AIPromptTemplate).where(AIPromptTemplate.id == template_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_templates_by_ids(self, db: AsyncSession, template_ids: List[int], 
                                  user_id: int) -> List[AIPromptTemplate]:
        """根据ID列表获取模板"""
        if not template_ids:
            return []
        
        query = select(AIPromptTemplate).where(
            and_(
                AIPromptTemplate.id.in_(template_ids),
                or_(
                    AIPromptTemplate.owner_id == user_id,
                    AIPromptTemplate.visibility == TemplateVisibility.PUBLIC.value,
                    and_(
                        AIPromptTemplate.visibility == TemplateVisibility.TEAM.value,
                        AIPromptTemplate.team_id.isnot(None)
                    )
                )
            )
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def _get_existing_share(self, db: AsyncSession, template_id: int, 
                                user_id: int, share_type: ShareType) -> Optional[TemplateShare]:
        """获取现有的分享"""
        query = select(TemplateShare).where(
            and_(
                TemplateShare.template_id == template_id,
                TemplateShare.owner_id == user_id,
                TemplateShare.share_type == share_type.value
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_favorite(self, db: AsyncSession, template_id: int, 
                          user_id: int) -> Optional[TemplateFavorite]:
        """获取收藏记录"""
        query = select(TemplateFavorite).where(
            and_(
                TemplateFavorite.template_id == template_id,
                TemplateFavorite.user_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_user_rating(self, db: AsyncSession, template_id: int, 
                             user_id: int) -> Optional[TemplateRating]:
        """获取用户评分"""
        query = select(TemplateRating).where(
            and_(
                TemplateRating.template_id == template_id,
                TemplateRating.user_id == user_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def _update_template_rating(self, db: AsyncSession, template_id: int):
        """更新模板平均评分"""
        # 计算平均评分
        rating_stats_query = select(
            func.avg(TemplateRating.rating).label('avg_rating'),
            func.count(TemplateRating.id).label('rating_count')
        ).where(TemplateRating.template_id == template_id)
        
        result = await db.execute(rating_stats_query)
        stats = result.fetchone()
        
        if stats and stats.rating_count > 0:
            # 更新模板评分
            update_query = update(AIPromptTemplate).where(
                AIPromptTemplate.id == template_id
            ).values(
                rating_avg=float(stats.avg_rating),
                rating_count=stats.rating_count
            )
            await db.execute(update_query)
            await db.commit()
    
    async def _get_comment_replies(self, db: AsyncSession, parent_comment_id: int) -> List[TemplateComment]:
        """获取评论的回复"""
        query = select(TemplateComment).where(
            TemplateComment.parent_comment_id == parent_comment_id
        ).order_by(TemplateComment.created_at)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    def _check_user_in_teams(self, user_id: int, team_ids: List[int]) -> bool:
        """检查用户是否在指定团队中"""
        # TODO: 实现真正的团队成员检查逻辑
        # 这里需要根据实际的团队管理系统来实现
        return True  # 临时返回True