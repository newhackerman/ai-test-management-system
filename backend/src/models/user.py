"""
用户模型
"""
from sqlalchemy import Column, BigInteger, String, Boolean, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum

from .base import BaseModel


class UserStatus(PyEnum):
    """用户状态枚举"""
    ACTIVE = "active"      # 激活
    INACTIVE = "inactive"  # 未激活
    DISABLED = "disabled"  # 禁用
    LOCKED = "locked"     # 锁定
    PENDING = "pending"    # 待审核
    DELETED = "deleted"    # 已删除


class Gender(PyEnum):
    """性别枚举"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class User(BaseModel):
    """用户模型"""
    __tablename__ = "users"

    # 基本信息
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, index=True, nullable=False, comment="邮箱")
    nickname = Column(String(50), nullable=True, comment="昵称")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    phone = Column(String(20), nullable=True, index=True, comment="手机号")
    bio = Column(Text, nullable=True, comment="个人简介")
    gender = Column(Enum(Gender), nullable=True, default=Gender.UNKNOWN, comment="性别")
    birthday = Column(DateTime, nullable=True, comment="生日")
    location = Column(String(100), nullable=True, comment="所在地")
    website = Column(String(255), nullable=True, comment="个人网站")
    
    # 认证和安全相关
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    salt = Column(String(255), nullable=False, comment="密码盐值")
    is_email_verified = Column(Boolean, default=False, nullable=False, comment="邮箱是否已验证")
    is_phone_verified = Column(Boolean, default=False, nullable=False, comment="手机是否已验证")
    mfa_enabled = Column(Boolean, default=False, nullable=False, comment="是否启用多因素认证")
    mfa_secret = Column(String(255), nullable=True, comment="MFA密钥")
    mfa_backup_codes = Column(Text, nullable=True, comment="MFA备用代码")
    
    # 状态和设置
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False, comment="用户状态")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    is_superuser = Column(Boolean, default=False, nullable=False, comment="是否超级用户")
    
    # 登录相关
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    last_login_ip = Column(String(45), nullable=True, comment="最后登录IP")
    failed_login_attempts = Column(Integer, default=0, nullable=False, comment="登录失败次数")
    locked_until = Column(DateTime, nullable=True, comment="账户锁定到期时间")
    password_updated_at = Column(DateTime, nullable=True, comment="密码更新时间")
    
    # 密码重置相关
    reset_token = Column(String(500), nullable=True, comment="密码重置令牌")
    reset_token_expires = Column(DateTime, nullable=True, comment="重置令牌过期时间")
    email_verification_token = Column(String(500), nullable=True, comment="邮箱验证令牌")
    email_verification_expires = Column(DateTime, nullable=True, comment="邮箱验证令牌过期时间")
    
    @property
    def is_locked(self) -> bool:
        """检查用户是否被锁定"""
        if self.locked_until is None:
            return False
        return self.locked_until > func.now()
    
    # 偏好设置
    language = Column(String(10), default="zh-CN", nullable=False, comment="语言设置")
    timezone = Column(String(50), default="Asia/Shanghai", nullable=False, comment="时区设置")
    theme = Column(String(20), default="light", nullable=False, comment="主题设置")
    email_notifications = Column(Boolean, default=True, nullable=False, comment="邮件通知")
    sms_notifications = Column(Boolean, default=False, nullable=False, comment="短信通知")
    push_notifications = Column(Boolean, default=True, nullable=False, comment="推送通知")
    
    # 关系
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    user_logs = relationship("UserLog", back_populates="user", cascade="all, delete-orphan")
    
    # AI助手相关关系
    ai_files = relationship("AIFileStorage", back_populates="user", cascade="all, delete-orphan")
    file_shares = relationship("AIFileShare", back_populates="user", cascade="all, delete-orphan")
    file_access_logs = relationship("AIFileAccessLog", back_populates="user", cascade="all, delete-orphan")
    
    # 在线会议模块关系 - 暂时注释掉，等会议模块完全实现后再启用
    # organized_meetings = relationship("Meeting", foreign_keys="Meeting.organizer_id")
    # meeting_participations = relationship("MeetingParticipant", back_populates="user")
    # meeting_chats = relationship("MeetingChat", foreign_keys="MeetingChat.sender_id")
    # meeting_files = relationship("MeetingFile", back_populates="uploader")
    # created_recordings = relationship("MeetingRecording", foreign_keys="MeetingRecording.created_by")
    # created_minutes = relationship("MeetingMinutes", foreign_keys="MeetingMinutes.created_by")
    # approved_minutes = relationship("MeetingMinutes", foreign_keys="MeetingMinutes.approved_by")
    # created_templates = relationship("MeetingTemplate", foreign_keys="MeetingTemplate.created_by")


class UserRole(BaseModel):
    """用户角色关联表"""
    __tablename__ = "user_roles"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, comment="角色ID")
    
    # 关系
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")


class UserSession(BaseModel):
    """用户会话表"""
    __tablename__ = "user_sessions"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    session_token = Column(String(500), unique=True, index=True, nullable=False, comment="会话令牌")
    refresh_token = Column(String(500), nullable=True, comment="刷新令牌")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    ip_address = Column(String(45), nullable=True, comment="IP地址")
    device_info = Column(Text, nullable=True, comment="设备信息")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    last_activity = Column(DateTime, nullable=True, comment="最后活动时间")
    
    @property
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return self.expires_at < func.now()
    
    # 关系
    user = relationship("User", back_populates="user_sessions")


class UserLog(BaseModel):
    """用户日志表"""
    __tablename__ = "user_logs"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    action = Column(String(50), nullable=False, comment="操作类型")
    description = Column(Text, nullable=True, comment="操作描述")
    ip_address = Column(String(45), nullable=True, comment="IP地址")
    user_agent = Column(Text, nullable=True, comment="用户代理")
    extra_data = Column(Text, nullable=True, comment="额外数据(JSON格式)")
    
    # 关系
    user = relationship("User", back_populates="user_logs")