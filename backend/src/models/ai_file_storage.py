"""
AI助手文件存储模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, BigInteger, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from .base import Base


class FileType(str, Enum):
    """文件类型枚举"""
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    ARCHIVE = "ARCHIVE"
    CODE = "CODE"
    DATA = "DATA"
    OTHER = "OTHER"


class FileCategory(str, Enum):
    """文件分类枚举"""
    CHAT_ATTACHMENT = "CHAT_ATTACHMENT"  # 聊天附件
    PROMPT_TEMPLATE = "PROMPT_TEMPLATE"  # 提示词模板文件
    EXPORT_DATA = "EXPORT_DATA"  # 导出数据
    USER_UPLOAD = "USER_UPLOAD"  # 用户上传
    AI_GENERATED = "AI_GENERATED"  # AI生成内容
    SYSTEM_BACKUP = "SYSTEM_BACKUP"  # 系统备份
    TEMP_FILE = "TEMP_FILE"  # 临时文件


class StorageProvider(str, Enum):
    """存储提供商枚举"""
    LOCAL = "LOCAL"  # 本地存储
    ALIYUN_OSS = "ALIYUN_OSS"  # 阿里云OSS
    TENCENT_COS = "TENCENT_COS"  # 腾讯云COS
    AWS_S3 = "AWS_S3"  # AWS S3
    MINIO = "MINIO"  # MinIO


class FileStatus(str, Enum):
    """文件状态枚举"""
    UPLOADING = "UPLOADING"  # 上传中
    ACTIVE = "ACTIVE"  # 活跃
    ARCHIVED = "ARCHIVED"  # 已归档
    DELETED = "DELETED"  # 已删除
    CORRUPTED = "CORRUPTED"  # 已损坏


class AIFileStorage(Base):
    """AI文件存储表"""
    __tablename__ = "ai_file_storage"
    
    id = Column(BigInteger, primary_key=True, index=True, comment="文件ID")
    
    # 基本信息
    original_filename = Column(String(255), nullable=False, comment="原始文件名")
    stored_filename = Column(String(255), nullable=False, unique=True, comment="存储文件名")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    file_url = Column(String(500), nullable=True, comment="文件访问URL")
    
    # 文件属性
    file_type = Column(SQLEnum(FileType), nullable=False, comment="文件类型")
    file_category = Column(SQLEnum(FileCategory), nullable=False, comment="文件分类")
    mime_type = Column(String(100), nullable=False, comment="MIME类型")
    file_size = Column(BigInteger, nullable=False, comment="文件大小(字节)")
    file_hash = Column(String(64), nullable=True, comment="文件哈希值(SHA256)")
    
    # 存储信息
    storage_provider = Column(SQLEnum(StorageProvider), nullable=False, default=StorageProvider.LOCAL, comment="存储提供商")
    storage_bucket = Column(String(100), nullable=True, comment="存储桶名称")
    storage_region = Column(String(50), nullable=True, comment="存储区域")
    
    # 关联信息
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="上传用户ID")
    session_id = Column(BigInteger, ForeignKey("ai_chat_sessions.id"), nullable=True, comment="关联会话ID")
    message_id = Column(BigInteger, ForeignKey("ai_chat_messages.id"), nullable=True, comment="关联消息ID")
    template_id = Column(BigInteger, ForeignKey("ai_prompt_templates.id"), nullable=True, comment="关联模板ID")
    
    # 元数据
    file_metadata = Column(Text, nullable=True, comment="文件元数据(JSON)")
    tags = Column(String(500), nullable=True, comment="文件标签")
    description = Column(Text, nullable=True, comment="文件描述")
    
    # 状态和权限
    status = Column(SQLEnum(FileStatus), nullable=False, default=FileStatus.ACTIVE, comment="文件状态")
    is_public = Column(Boolean, nullable=False, default=False, comment="是否公开")
    is_temporary = Column(Boolean, nullable=False, default=False, comment="是否临时文件")
    
    # 访问控制
    access_count = Column(Integer, nullable=False, default=0, comment="访问次数")
    download_count = Column(Integer, nullable=False, default=0, comment="下载次数")
    last_accessed_at = Column(DateTime, nullable=True, comment="最后访问时间")
    
    # 生命周期
    expires_at = Column(DateTime, nullable=True, comment="过期时间")
    archived_at = Column(DateTime, nullable=True, comment="归档时间")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    user = relationship("User", back_populates="ai_files")
    session = relationship("AIChatSession", back_populates="files")
    message = relationship("AIChatMessage", back_populates="attachments")
    template = relationship("AIPromptTemplate", back_populates="files")
    shares = relationship("AIFileShare", back_populates="file")
    access_logs = relationship("AIFileAccessLog", back_populates="file")
    
    # 索引
    __table_args__ = (
        Index('idx_ai_file_user_id', 'user_id'),
        Index('idx_ai_file_session_id', 'session_id'),
        Index('idx_ai_file_message_id', 'message_id'),
        Index('idx_ai_file_template_id', 'template_id'),
        Index('idx_ai_file_category', 'file_category'),
        Index('idx_ai_file_type', 'file_type'),
        Index('idx_ai_file_status', 'status'),
        Index('idx_ai_file_hash', 'file_hash'),
        Index('idx_ai_file_created_at', 'created_at'),
        Index('idx_ai_file_expires_at', 'expires_at'),
        {'comment': 'AI文件存储表'}
    )


class AIFileShare(Base):
    """AI文件分享表"""
    __tablename__ = "ai_file_shares"
    
    id = Column(BigInteger, primary_key=True, index=True, comment="分享ID")
    
    # 关联信息
    file_id = Column(BigInteger, ForeignKey("ai_file_storage.id"), nullable=False, comment="文件ID")
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="分享用户ID")
    
    # 分享信息
    share_token = Column(String(64), nullable=False, unique=True, comment="分享令牌")
    share_url = Column(String(500), nullable=False, comment="分享链接")
    share_password = Column(String(100), nullable=True, comment="分享密码")
    
    # 权限控制
    can_download = Column(Boolean, nullable=False, default=True, comment="允许下载")
    can_preview = Column(Boolean, nullable=False, default=True, comment="允许预览")
    max_downloads = Column(Integer, nullable=True, comment="最大下载次数")
    max_views = Column(Integer, nullable=True, comment="最大查看次数")
    
    # 统计信息
    download_count = Column(Integer, nullable=False, default=0, comment="下载次数")
    view_count = Column(Integer, nullable=False, default=0, comment="查看次数")
    last_accessed_at = Column(DateTime, nullable=True, comment="最后访问时间")
    
    # 生命周期
    expires_at = Column(DateTime, nullable=True, comment="过期时间")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系
    file = relationship("AIFileStorage", back_populates="shares")
    user = relationship("User", back_populates="file_shares")
    access_logs = relationship("AIFileAccessLog", back_populates="share")
    
    # 索引
    __table_args__ = (
        Index('idx_ai_file_share_file_id', 'file_id'),
        Index('idx_ai_file_share_user_id', 'user_id'),
        Index('idx_ai_file_share_token', 'share_token'),
        Index('idx_ai_file_share_expires_at', 'expires_at'),
        {'comment': 'AI文件分享表'}
    )


class AIFileAccessLog(Base):
    """AI文件访问日志表"""
    __tablename__ = "ai_file_access_logs"
    
    id = Column(BigInteger, primary_key=True, index=True, comment="日志ID")
    
    # 关联信息
    file_id = Column(BigInteger, ForeignKey("ai_file_storage.id"), nullable=False, comment="文件ID")
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, comment="访问用户ID")
    share_id = Column(BigInteger, ForeignKey("ai_file_shares.id"), nullable=True, comment="分享ID")
    
    # 访问信息
    action = Column(String(50), nullable=False, comment="操作类型(view/download/upload/delete)")
    ip_address = Column(String(45), nullable=True, comment="IP地址")
    user_agent = Column(String(500), nullable=True, comment="用户代理")
    referer = Column(String(500), nullable=True, comment="来源页面")
    
    # 结果信息
    success = Column(Boolean, nullable=False, default=True, comment="是否成功")
    error_message = Column(String(500), nullable=True, comment="错误信息")
    response_time = Column(Integer, nullable=True, comment="响应时间(毫秒)")
    bytes_transferred = Column(BigInteger, nullable=True, comment="传输字节数")
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=func.now(), comment="创建时间")
    
    # 关系
    file = relationship("AIFileStorage", back_populates="access_logs")
    user = relationship("User", back_populates="file_access_logs")
    share = relationship("AIFileShare", back_populates="access_logs")
    
    # 索引
    __table_args__ = (
        Index('idx_ai_file_access_file_id', 'file_id'),
        Index('idx_ai_file_access_user_id', 'user_id'),
        Index('idx_ai_file_access_action', 'action'),
        Index('idx_ai_file_access_created_at', 'created_at'),
        Index('idx_ai_file_access_ip', 'ip_address'),
        {'comment': 'AI文件访问日志表'}
    )