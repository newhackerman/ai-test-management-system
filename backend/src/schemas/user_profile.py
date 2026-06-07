"""
用户个人资料相关的Pydantic模式
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from ..models.user import Gender

class UserProfileResponse(BaseModel):
    """用户个人资料响应模式"""
    id: int
    username: str
    email: str
    nickname: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[datetime] = None
    location: Optional[str] = None
    website: Optional[str] = None
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    theme: str = "light"
    email_notifications: bool = True
    sms_notifications: bool = False
    push_notifications: bool = True
    is_email_verified: bool = False
    is_phone_verified: bool = False
    mfa_enabled: bool = False
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    """用户个人资料更新模式"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    phone: Optional[str] = Field(None, pattern=r'^1[3-9]\d{9}$', description="手机号")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    gender: Optional[Gender] = Field(None, description="性别")
    birthday: Optional[datetime] = Field(None, description="生日")
    location: Optional[str] = Field(None, max_length=100, description="所在地")
    website: Optional[str] = Field(None, max_length=255, description="个人网站")
    language: Optional[str] = Field(None, pattern=r'^[a-z]{2}-[A-Z]{2}$', description="语言设置")
    timezone: Optional[str] = Field(None, max_length=50, description="时区设置")
    theme: Optional[str] = Field(None, pattern=r'^(light|dark)$', description="主题设置")
    email_notifications: Optional[bool] = Field(None, description="邮件通知")
    sms_notifications: Optional[bool] = Field(None, description="短信通知")
    push_notifications: Optional[bool] = Field(None, description="推送通知")

    @validator('website')
    def validate_website(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('网站地址必须以http://或https://开头')
        return v

    @validator('birthday')
    def validate_birthday(cls, v):
        if v and v > datetime.now():
            raise ValueError('生日不能是未来时间')
        return v

class SecuritySettingsResponse(BaseModel):
    """用户安全设置响应模式"""
    mfa_enabled: bool
    email_verified: bool
    phone_verified: bool
    last_login_at: Optional[datetime]
    last_login_ip: Optional[str]
    password_updated_at: Optional[datetime]
    failed_login_attempts: int
    locked_until: Optional[datetime]

class AvatarUploadResponse(BaseModel):
    """头像上传响应模式"""
    success: bool
    message: str
    avatar_url: str