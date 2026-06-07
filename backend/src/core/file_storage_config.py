"""
文件存储配置
"""
import os
from typing import Dict, List, Optional
from pathlib import Path
from pydantic import Field, ConfigDict

# Handle BaseSettings import for different Pydantic versions
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        # Fallback for older versions or missing pydantic-settings
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

from ..models.ai_file_storage import FileCategory, StorageProvider


class FileStorageSettings(BaseSettings):
    """文件存储设置"""
    
    # 基础配置
    STORAGE_ROOT: str = Field(default="uploads", description="存储根目录")
    STORAGE_PROVIDER: StorageProvider = Field(default=StorageProvider.LOCAL, description="默认存储提供商")
    BASE_URL: str = Field(default="http://localhost:8000", description="基础URL")
    
    # 文件大小限制 (字节)
    MAX_FILE_SIZE_CHAT_ATTACHMENT: int = Field(default=50 * 1024 * 1024, description="聊天附件最大大小")
    MAX_FILE_SIZE_PROMPT_TEMPLATE: int = Field(default=1 * 1024 * 1024, description="提示词模板最大大小")
    MAX_FILE_SIZE_EXPORT_DATA: int = Field(default=100 * 1024 * 1024, description="导出数据最大大小")
    MAX_FILE_SIZE_USER_UPLOAD: int = Field(default=50 * 1024 * 1024, description="用户上传最大大小")
    MAX_FILE_SIZE_AI_GENERATED: int = Field(default=10 * 1024 * 1024, description="AI生成内容最大大小")
    MAX_FILE_SIZE_TEMP_FILE: int = Field(default=20 * 1024 * 1024, description="临时文件最大大小")
    
    # 允许的文件类型
    ALLOWED_MIME_TYPES_CHAT_ATTACHMENT: List[str] = Field(
        default=[
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/markdown',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv', 'application/json'
        ],
        description="聊天附件允许的MIME类型"
    )
    
    ALLOWED_MIME_TYPES_PROMPT_TEMPLATE: List[str] = Field(
        default=['text/plain', 'text/markdown', 'application/json', 'text/yaml'],
        description="提示词模板允许的MIME类型"
    )
    
    ALLOWED_MIME_TYPES_EXPORT_DATA: List[str] = Field(
        default=[
            'application/json', 'text/csv', 'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/pdf', 'text/plain'
        ],
        description="导出数据允许的MIME类型"
    )
    
    ALLOWED_MIME_TYPES_USER_UPLOAD: List[str] = Field(
        default=[
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/markdown',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv', 'application/json', 'application/zip'
        ],
        description="用户上传允许的MIME类型"
    )
    
    # 禁止的文件扩展名
    BLOCKED_EXTENSIONS: List[str] = Field(
        default=['.exe', '.bat', '.cmd', '.scr', '.com', '.pif', '.vbs', '.js', '.jar'],
        description="禁止的文件扩展名"
    )
    
    # 清理配置
    AUTO_CLEANUP_ENABLED: bool = Field(default=True, description="是否启用自动清理")
    CLEANUP_INTERVAL_HOURS: int = Field(default=24, description="清理间隔(小时)")
    TEMP_FILE_RETENTION_HOURS: int = Field(default=24, description="临时文件保留时间(小时)")
    DELETED_FILE_RETENTION_DAYS: int = Field(default=30, description="已删除文件保留天数")
    
    # 安全配置
    ENABLE_VIRUS_SCAN: bool = Field(default=False, description="启用病毒扫描")
    ENABLE_CONTENT_FILTER: bool = Field(default=True, description="启用内容过滤")
    MAX_SHARE_DURATION_HOURS: int = Field(default=168, description="最大分享时长(小时)")
    REQUIRE_AUTH_FOR_DOWNLOAD: bool = Field(default=True, description="下载需要认证")
    ENABLE_WATERMARK: bool = Field(default=False, description="启用水印")
    
    # 云存储配置
    # 阿里云OSS
    ALIYUN_OSS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="阿里云OSS访问密钥ID")
    ALIYUN_OSS_ACCESS_KEY_SECRET: Optional[str] = Field(default=None, description="阿里云OSS访问密钥")
    ALIYUN_OSS_BUCKET: Optional[str] = Field(default=None, description="阿里云OSS存储桶")
    ALIYUN_OSS_ENDPOINT: Optional[str] = Field(default=None, description="阿里云OSS端点")
    ALIYUN_OSS_REGION: Optional[str] = Field(default=None, description="阿里云OSS区域")
    
    # 腾讯云COS
    TENCENT_COS_SECRET_ID: Optional[str] = Field(default=None, description="腾讯云COS密钥ID")
    TENCENT_COS_SECRET_KEY: Optional[str] = Field(default=None, description="腾讯云COS密钥")
    TENCENT_COS_BUCKET: Optional[str] = Field(default=None, description="腾讯云COS存储桶")
    TENCENT_COS_REGION: Optional[str] = Field(default=None, description="腾讯云COS区域")
    
    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS访问密钥ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS访问密钥")
    AWS_S3_BUCKET: Optional[str] = Field(default=None, description="AWS S3存储桶")
    AWS_S3_REGION: Optional[str] = Field(default=None, description="AWS S3区域")
    
    # MinIO
    MINIO_ENDPOINT: Optional[str] = Field(default=None, description="MinIO端点")
    MINIO_ACCESS_KEY: Optional[str] = Field(default=None, description="MinIO访问密钥")
    MINIO_SECRET_KEY: Optional[str] = Field(default=None, description="MinIO密钥")
    MINIO_BUCKET: Optional[str] = Field(default=None, description="MinIO存储桶")
    MINIO_SECURE: bool = Field(default=True, description="MinIO是否使用HTTPS")
    
    model_config = ConfigDict(
        env_file=".env",
        env_prefix="FILE_STORAGE_",
        extra="ignore"  # Ignore extra environment variables
    )
    
    def get_max_file_size(self, category: FileCategory) -> int:
        """获取指定分类的最大文件大小"""
        size_mapping = {
            FileCategory.CHAT_ATTACHMENT: self.MAX_FILE_SIZE_CHAT_ATTACHMENT,
            FileCategory.PROMPT_TEMPLATE: self.MAX_FILE_SIZE_PROMPT_TEMPLATE,
            FileCategory.EXPORT_DATA: self.MAX_FILE_SIZE_EXPORT_DATA,
            FileCategory.USER_UPLOAD: self.MAX_FILE_SIZE_USER_UPLOAD,
            FileCategory.AI_GENERATED: self.MAX_FILE_SIZE_AI_GENERATED,
            FileCategory.TEMP_FILE: self.MAX_FILE_SIZE_TEMP_FILE,
        }
        return size_mapping.get(category, self.MAX_FILE_SIZE_USER_UPLOAD)
    
    def get_allowed_mime_types(self, category: FileCategory) -> List[str]:
        """获取指定分类允许的MIME类型"""
        mime_mapping = {
            FileCategory.CHAT_ATTACHMENT: self.ALLOWED_MIME_TYPES_CHAT_ATTACHMENT,
            FileCategory.PROMPT_TEMPLATE: self.ALLOWED_MIME_TYPES_PROMPT_TEMPLATE,
            FileCategory.EXPORT_DATA: self.ALLOWED_MIME_TYPES_EXPORT_DATA,
            FileCategory.USER_UPLOAD: self.ALLOWED_MIME_TYPES_USER_UPLOAD,
        }
        return mime_mapping.get(category, self.ALLOWED_MIME_TYPES_USER_UPLOAD)
    
    def get_storage_path(self, category: FileCategory) -> Path:
        """获取指定分类的存储路径"""
        base_path = Path(self.STORAGE_ROOT)
        category_path = base_path / category.value.lower()
        category_path.mkdir(parents=True, exist_ok=True)
        return category_path
    
    def is_extension_blocked(self, filename: str) -> bool:
        """检查文件扩展名是否被禁止"""
        if not filename:
            return False
        
        ext = Path(filename).suffix.lower()
        return ext in self.BLOCKED_EXTENSIONS
    
    def format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.2f} {size_names[i]}"


# 全局文件存储设置实例
file_storage_settings = FileStorageSettings()


# 文件存储路径配置
STORAGE_PATHS = {
    FileCategory.CHAT_ATTACHMENT: "chat_attachments",
    FileCategory.PROMPT_TEMPLATE: "prompt_templates", 
    FileCategory.EXPORT_DATA: "export_data",
    FileCategory.USER_UPLOAD: "user_uploads",
    FileCategory.AI_GENERATED: "ai_generated",
    FileCategory.SYSTEM_BACKUP: "system_backups",
    FileCategory.TEMP_FILE: "temp_files"
}


# 文件类型图标映射
FILE_TYPE_ICONS = {
    "image/jpeg": "🖼️",
    "image/png": "🖼️", 
    "image/gif": "🖼️",
    "image/webp": "🖼️",
    "application/pdf": "📄",
    "text/plain": "📝",
    "text/markdown": "📝",
    "application/msword": "📄",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "📄",
    "application/vnd.ms-excel": "📊",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "📊",
    "text/csv": "📊",
    "application/json": "🔧",
    "application/zip": "🗜️",
    "audio/mpeg": "🎵",
    "audio/wav": "🎵",
    "video/mp4": "🎬",
    "video/avi": "🎬"
}


def get_file_icon(mime_type: str) -> str:
    """获取文件类型图标"""
    return FILE_TYPE_ICONS.get(mime_type, "📁")