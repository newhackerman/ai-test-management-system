"""
AI助手文件存储相关的Pydantic模型
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from ..models.ai_file_storage import FileType, FileCategory, FileStatus, StorageProvider


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    id: int = Field(..., description="文件ID")
    original_filename: str = Field(..., description="原始文件名")
    file_url: str = Field(..., description="文件访问URL")
    file_type: FileType = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小(字节)")
    mime_type: str = Field(..., description="MIME类型")
    created_at: datetime = Field(..., description="创建时间")


class FileInfoResponse(BaseModel):
    """文件信息响应"""
    id: int = Field(..., description="文件ID")
    original_filename: str = Field(..., description="原始文件名")
    stored_filename: str = Field(..., description="存储文件名")
    file_url: str = Field(..., description="文件访问URL")
    file_type: FileType = Field(..., description="文件类型")
    file_category: FileCategory = Field(..., description="文件分类")
    mime_type: str = Field(..., description="MIME类型")
    file_size: int = Field(..., description="文件大小(字节)")
    file_hash: Optional[str] = Field(None, description="文件哈希值")
    description: Optional[str] = Field(None, description="文件描述")
    tags: Optional[str] = Field(None, description="文件标签")
    status: FileStatus = Field(..., description="文件状态")
    is_public: bool = Field(..., description="是否公开")
    is_temporary: bool = Field(..., description="是否临时文件")
    access_count: int = Field(..., description="访问次数")
    download_count: int = Field(..., description="下载次数")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class FileListResponse(BaseModel):
    """文件列表响应"""
    files: List[FileInfoResponse] = Field(..., description="文件列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")


class FileShareRequest(BaseModel):
    """文件分享请求"""
    expires_hours: Optional[int] = Field(None, description="过期小时数")
    password: Optional[str] = Field(None, description="分享密码")
    can_download: bool = Field(True, description="允许下载")
    can_preview: bool = Field(True, description="允许预览")
    max_downloads: Optional[int] = Field(None, description="最大下载次数")
    max_views: Optional[int] = Field(None, description="最大查看次数")


class FileShareResponse(BaseModel):
    """文件分享响应"""
    id: int = Field(..., description="分享ID")
    share_token: str = Field(..., description="分享令牌")
    share_url: str = Field(..., description="分享链接")
    can_download: bool = Field(..., description="允许下载")
    can_preview: bool = Field(..., description="允许预览")
    max_downloads: Optional[int] = Field(None, description="最大下载次数")
    max_views: Optional[int] = Field(None, description="最大查看次数")
    download_count: int = Field(..., description="下载次数")
    view_count: int = Field(..., description="查看次数")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    created_at: datetime = Field(..., description="创建时间")


class StorageStatsResponse(BaseModel):
    """存储统计响应"""
    total_files: int = Field(..., description="总文件数")
    total_size: int = Field(..., description="总大小(字节)")
    category_stats: Dict[str, Dict[str, int]] = Field(..., description="按分类统计")
    type_stats: Dict[str, Dict[str, int]] = Field(..., description="按类型统计")


class FileAccessLogResponse(BaseModel):
    """文件访问日志响应"""
    id: int = Field(..., description="日志ID")
    file_id: int = Field(..., description="文件ID")
    user_id: Optional[int] = Field(None, description="用户ID")
    action: str = Field(..., description="操作类型")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    response_time: Optional[int] = Field(None, description="响应时间(毫秒)")
    bytes_transferred: Optional[int] = Field(None, description="传输字节数")
    created_at: datetime = Field(..., description="创建时间")


class FileMetadata(BaseModel):
    """文件元数据"""
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    duration: Optional[float] = Field(None, description="音视频时长(秒)")
    pages: Optional[int] = Field(None, description="文档页数")
    encoding: Optional[str] = Field(None, description="文本编码")
    language: Optional[str] = Field(None, description="文档语言")
    author: Optional[str] = Field(None, description="文档作者")
    title: Optional[str] = Field(None, description="文档标题")
    created_date: Optional[datetime] = Field(None, description="文档创建时间")
    modified_date: Optional[datetime] = Field(None, description="文档修改时间")


class FileUploadRequest(BaseModel):
    """文件上传请求"""
    category: FileCategory = Field(..., description="文件分类")
    session_id: Optional[int] = Field(None, description="关联会话ID")
    message_id: Optional[int] = Field(None, description="关联消息ID")
    template_id: Optional[int] = Field(None, description="关联模板ID")
    description: Optional[str] = Field(None, description="文件描述")
    tags: Optional[str] = Field(None, description="文件标签")
    is_temporary: bool = Field(False, description="是否临时文件")
    expires_hours: Optional[int] = Field(None, description="过期小时数")


class FileUpdateRequest(BaseModel):
    """文件更新请求"""
    description: Optional[str] = Field(None, description="文件描述")
    tags: Optional[str] = Field(None, description="文件标签")
    is_public: Optional[bool] = Field(None, description="是否公开")


class FileBatchUploadResponse(BaseModel):
    """批量上传响应"""
    results: List[Dict[str, Any]] = Field(..., description="上传结果列表")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")


class FileBatchDeleteResponse(BaseModel):
    """批量删除响应"""
    results: List[Dict[str, Any]] = Field(..., description="删除结果列表")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")


class FileSearchRequest(BaseModel):
    """文件搜索请求"""
    keyword: Optional[str] = Field(None, description="关键词")
    category: Optional[FileCategory] = Field(None, description="文件分类")
    file_type: Optional[FileType] = Field(None, description="文件类型")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    size_min: Optional[int] = Field(None, description="最小文件大小")
    size_max: Optional[int] = Field(None, description="最大文件大小")
    created_after: Optional[datetime] = Field(None, description="创建时间起始")
    created_before: Optional[datetime] = Field(None, description="创建时间结束")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    include_public: bool = Field(True, description="是否包含公开文件")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")


class FileStorageConfig(BaseModel):
    """文件存储配置"""
    provider: StorageProvider = Field(..., description="存储提供商")
    bucket: Optional[str] = Field(None, description="存储桶名称")
    region: Optional[str] = Field(None, description="存储区域")
    access_key: Optional[str] = Field(None, description="访问密钥")
    secret_key: Optional[str] = Field(None, description="密钥")
    endpoint: Optional[str] = Field(None, description="端点URL")
    custom_domain: Optional[str] = Field(None, description="自定义域名")
    max_file_size: int = Field(100 * 1024 * 1024, description="最大文件大小")
    allowed_types: List[str] = Field(default_factory=list, description="允许的文件类型")


class FileCleanupConfig(BaseModel):
    """文件清理配置"""
    auto_cleanup: bool = Field(True, description="是否自动清理")
    cleanup_interval_hours: int = Field(24, description="清理间隔(小时)")
    temp_file_retention_hours: int = Field(24, description="临时文件保留时间(小时)")
    deleted_file_retention_days: int = Field(30, description="已删除文件保留天数")
    max_storage_size: Optional[int] = Field(None, description="最大存储大小(字节)")


class FileSecurityConfig(BaseModel):
    """文件安全配置"""
    enable_virus_scan: bool = Field(False, description="启用病毒扫描")
    enable_content_filter: bool = Field(True, description="启用内容过滤")
    max_share_duration_hours: int = Field(168, description="最大分享时长(小时)")
    require_auth_for_download: bool = Field(True, description="下载需要认证")
    enable_watermark: bool = Field(False, description="启用水印")
    blocked_extensions: List[str] = Field(
        default_factory=lambda: ['.exe', '.bat', '.cmd', '.scr', '.com'],
        description="禁止的文件扩展名"
    )