"""
模板分享相关的Pydantic模式
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from ..models.template_sharing import ShareType, ShareStatus


# ==================== 模板分享相关模式 ====================

class TemplateShareCreate(BaseModel):
    """创建模板分享请求"""
    share_type: ShareType = Field(..., description="分享类型")
    title: Optional[str] = Field(None, max_length=300, description="分享标题")
    description: Optional[str] = Field(None, description="分享描述")
    password: Optional[str] = Field(None, max_length=100, description="访问密码")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    max_access_count: Optional[int] = Field(None, ge=1, description="最大访问次数")
    allow_download: bool = Field(True, description="允许下载")
    allow_copy: bool = Field(True, description="允许复制")
    allow_comment: bool = Field(True, description="允许评论")
    require_login: bool = Field(False, description="需要登录")
    allowed_users: Optional[List[int]] = Field(None, description="允许访问的用户ID列表")
    allowed_teams: Optional[List[int]] = Field(None, description="允许访问的团队ID列表")
    
    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须在未来')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if v and len(v.strip()) < 4:
            raise ValueError('密码长度至少4位')
        return v


class TemplateShareUpdate(BaseModel):
    """更新模板分享请求"""
    title: Optional[str] = Field(None, max_length=300, description="分享标题")
    description: Optional[str] = Field(None, description="分享描述")
    password: Optional[str] = Field(None, max_length=100, description="访问密码")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    max_access_count: Optional[int] = Field(None, ge=1, description="最大访问次数")
    allow_download: Optional[bool] = Field(None, description="允许下载")
    allow_copy: Optional[bool] = Field(None, description="允许复制")
    allow_comment: Optional[bool] = Field(None, description="允许评论")
    require_login: Optional[bool] = Field(None, description="需要登录")
    allowed_users: Optional[List[int]] = Field(None, description="允许访问的用户ID列表")
    allowed_teams: Optional[List[int]] = Field(None, description="允许访问的团队ID列表")
    status: Optional[ShareStatus] = Field(None, description="分享状态")


class TemplateShareResponse(BaseModel):
    """模板分享响应"""
    id: int
    template_id: int
    owner_id: int
    share_type: str
    share_token: str
    title: Optional[str]
    description: Optional[str]
    password: Optional[str]
    expires_at: Optional[datetime]
    max_access_count: Optional[int]
    allow_download: bool
    allow_copy: bool
    allow_comment: bool
    require_login: bool
    allowed_users: Optional[List[int]]
    allowed_teams: Optional[List[int]]
    status: str
    access_count: int
    last_accessed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TemplateShareListResponse(BaseModel):
    """模板分享列表响应"""
    shares: List[TemplateShareResponse]
    total: int
    page: int
    size: int
    pages: int


class ShareLinkResponse(BaseModel):
    """分享链接响应"""
    share_id: int
    share_url: str
    share_token: str
    qr_code_url: Optional[str] = None
    expires_at: Optional[datetime]
    access_count: int
    max_access_count: Optional[int]


class ShareAccessRequest(BaseModel):
    """访问分享请求"""
    share_token: str = Field(..., description="分享令牌")
    password: Optional[str] = Field(None, description="访问密码")


class ShareAccessResponse(BaseModel):
    """访问分享响应"""
    template: Dict[str, Any]  # 模板信息
    share_info: Dict[str, Any]  # 分享信息
    permissions: Dict[str, bool]  # 权限信息


# ==================== 模板收藏相关模式 ====================

class TemplateFavoriteCreate(BaseModel):
    """添加模板收藏请求"""
    template_id: int = Field(..., description="模板ID")
    folder_name: Optional[str] = Field("默认收藏夹", max_length=100, description="收藏夹名称")
    notes: Optional[str] = Field(None, description="个人备注")
    tags: Optional[List[str]] = Field(None, description="个人标签")


class TemplateFavoriteResponse(BaseModel):
    """模板收藏响应"""
    id: int
    template_id: int
    user_id: int
    folder_name: str
    notes: Optional[str]
    tags: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class FavoriteFolderResponse(BaseModel):
    """收藏夹响应"""
    folder_name: str
    template_count: int


# ==================== 模板评分相关模式 ====================

class TemplateRatingCreate(BaseModel):
    """创建模板评分请求"""
    rating: int = Field(..., ge=1, le=5, description="评分（1-5分）")
    comment: Optional[str] = Field(None, max_length=1000, description="评价内容")
    usefulness: Optional[int] = Field(None, ge=1, le=5, description="实用性评分")
    clarity: Optional[int] = Field(None, ge=1, le=5, description="清晰度评分")
    creativity: Optional[int] = Field(None, ge=1, le=5, description="创新性评分")


class TemplateRatingResponse(BaseModel):
    """模板评分响应"""
    id: int
    template_id: int
    user_id: int
    rating: int
    comment: Optional[str]
    usefulness: Optional[int]
    clarity: Optional[int]
    creativity: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 模板评论相关模式 ====================

class TemplateCommentCreate(BaseModel):
    """创建模板评论请求"""
    content: str = Field(..., min_length=1, max_length=2000, description="评论内容")
    parent_comment_id: Optional[int] = Field(None, description="父评论ID")


class TemplateCommentResponse(BaseModel):
    """模板评论响应"""
    id: int
    template_id: int
    user_id: int
    content: str
    parent_comment_id: Optional[int]
    is_hidden: bool
    is_pinned: bool
    like_count: int
    reply_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 模板协作相关模式 ====================

class TemplateCollaboratorInvite(BaseModel):
    """邀请模板协作者请求"""
    user_id: int = Field(..., description="被邀请用户ID")
    permission_level: str = Field("VIEW", description="权限级别")
    can_edit: bool = Field(False, description="可以编辑")
    can_share: bool = Field(False, description="可以分享")
    can_delete: bool = Field(False, description="可以删除")
    message: Optional[str] = Field(None, max_length=500, description="邀请消息")


class TemplateCollaboratorResponse(BaseModel):
    """模板协作者响应"""
    id: int
    template_id: int
    user_id: int
    inviter_id: int
    permission_level: str
    can_edit: bool
    can_share: bool
    can_delete: bool
    status: str
    accepted_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 统计和分析相关模式 ====================

class ShareStatistics(BaseModel):
    """分享统计"""
    total_shares: int = Field(description="总分享数")
    active_shares: int = Field(description="活跃分享数")
    total_access: int = Field(description="总访问次数")
    share_type_distribution: Dict[str, int] = Field(description="分享类型分布")
    popular_shares: List[TemplateShareResponse] = Field(description="热门分享")


class TemplateShareAnalytics(BaseModel):
    """模板分享分析"""
    template_id: int
    total_shares: int
    active_shares: int
    total_access: int
    recent_access_trend: Dict[str, int]  # 日期 -> 访问次数
    share_details: List[Dict[str, Any]]


# ==================== 搜索和筛选相关模式 ====================

class TemplateShareSearchRequest(BaseModel):
    """模板分享搜索请求"""
    query: Optional[str] = Field(None, max_length=200, description="搜索关键词")
    share_type: Optional[ShareType] = Field(None, description="分享类型筛选")
    status: Optional[ShareStatus] = Field(None, description="状态筛选")
    owner_id: Optional[int] = Field(None, description="所有者ID筛选")
    template_id: Optional[int] = Field(None, description="模板ID筛选")
    has_password: Optional[bool] = Field(None, description="是否有密码保护")
    is_expired: Optional[bool] = Field(None, description="是否已过期")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向", pattern="^(asc|desc)$")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")


class PublicTemplateSearchRequest(BaseModel):
    """公开模板搜索请求"""
    query: Optional[str] = Field(None, max_length=200, description="搜索关键词")
    category: Optional[str] = Field(None, description="分类筛选")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="最低评分")
    is_featured: Optional[bool] = Field(None, description="是否精选")
    is_verified: Optional[bool] = Field(None, description="是否已验证")
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向", pattern="^(asc|desc)$")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")


# ==================== 举报相关模式 ====================

class TemplateReportCreate(BaseModel):
    """创建模板举报请求"""
    template_id: int = Field(..., description="模板ID")
    report_type: str = Field(..., description="举报类型")
    reason: str = Field(..., min_length=10, max_length=500, description="举报原因")
    description: Optional[str] = Field(None, max_length=2000, description="详细描述")


class TemplateReportResponse(BaseModel):
    """模板举报响应"""
    id: int
    template_id: int
    reporter_id: int
    report_type: str
    reason: str
    description: Optional[str]
    status: str
    handler_id: Optional[int]
    handled_at: Optional[datetime]
    handler_note: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 批量操作相关模式 ====================

class BatchShareOperation(BaseModel):
    """批量分享操作请求"""
    template_ids: List[int] = Field(..., min_items=1, max_items=50, description="模板ID列表")
    operation: str = Field(..., description="操作类型")
    share_settings: Optional[TemplateShareCreate] = Field(None, description="分享设置")


class BatchOperationResult(BaseModel):
    """批量操作结果"""
    success_count: int = Field(description="成功数量")
    failed_count: int = Field(description="失败数量")
    success_items: List[int] = Field(description="成功的项目ID")
    failed_items: List[Dict[str, Any]] = Field(description="失败的项目详情")


# ==================== 导入导出相关模式 ====================

class TemplateExportRequest(BaseModel):
    """模板导出请求"""
    template_ids: List[int] = Field(..., min_items=1, description="要导出的模板ID列表")
    export_format: str = Field("json", description="导出格式")
    include_usage_data: bool = Field(False, description="是否包含使用数据")
    include_comments: bool = Field(False, description="是否包含评论")


class TemplateImportRequest(BaseModel):
    """模板导入请求"""
    import_data: Dict[str, Any] = Field(..., description="导入数据")
    import_format: str = Field("json", description="导入格式")
    overwrite_existing: bool = Field(False, description="是否覆盖已存在的模板")
    import_to_folder: Optional[str] = Field(None, description="导入到指定收藏夹")


class ImportResult(BaseModel):
    """导入结果"""
    imported_count: int = Field(description="导入数量")
    skipped_count: int = Field(description="跳过数量")
    error_count: int = Field(description="错误数量")
    imported_templates: List[int] = Field(description="导入的模板ID列表")
    errors: List[Dict[str, Any]] = Field(description="错误详情")