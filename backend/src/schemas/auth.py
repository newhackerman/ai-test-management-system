"""
认证相关的数据模型
"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., min_length=8, description="密码")
    remember_me: bool = Field(default=False, description="是否记住我")
    captcha: Optional[str] = Field(None, description="验证码")
    captcha_key: Optional[str] = Field(None, description="验证码key")


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="访问令牌过期时间（秒）")
    user: dict = Field(..., description="用户信息")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str = Field(..., description="刷新令牌")


class RefreshTokenResponse(BaseModel):
    """刷新令牌响应模型"""
    access_token: str = Field(..., description="新的访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="访问令牌过期时间（秒）")


class RegisterRequest(BaseModel):
    """注册请求模型"""
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=8, description="密码")
    confirm_password: str = Field(..., min_length=8, description="确认密码")
    full_name: Optional[str] = Field(None, description="全名")
    phone: Optional[str] = Field(None, description="手机号")
    captcha: str = Field(..., description="验证码")
    captcha_key: str = Field(..., description="验证码key")
    
    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("密码不匹配")
        return v


class RegisterResponse(BaseModel):
    """注册响应模型"""
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    message: str = Field(default="注册成功，请查收邮件激活账户", description="消息")


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求模型"""
    email: EmailStr = Field(..., description="邮箱")
    captcha: str = Field(..., description="验证码")
    captcha_key: str = Field(..., description="验证码key")


class ResetPasswordRequest(BaseModel):
    """重置密码请求模型"""
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=8, description="新密码")
    confirm_password: str = Field(..., min_length=8, description="确认新密码")
    
    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("密码不匹配")
        return v


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""
    current_password: str = Field(..., min_length=8, description="当前密码")
    new_password: str = Field(..., min_length=8, description="新密码")
    confirm_password: str = Field(..., min_length=8, description="确认新密码")
    
    @validator("confirm_password")
    def passwords_match(cls, v, values, **kwargs):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("密码不匹配")
        return v


class MFASetupRequest(BaseModel):
    """MFA设置请求模型"""
    password: str = Field(..., min_length=8, description="密码")


class MFASetupResponse(BaseModel):
    """MFA设置响应模型"""
    secret: str = Field(..., description="MFA密钥")
    qr_code_url: str = Field(..., description="二维码URL")
    backup_codes: List[str] = Field(..., description="备用代码列表")


class MFAVerifyRequest(BaseModel):
    """MFA验证请求模型"""
    code: str = Field(..., min_length=6, max_length=6, description="MFA验证码")
    remember_device: bool = Field(default=False, description="是否记住设备")


class MFAVerifyResponse(BaseModel):
    """MFA验证响应模型"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="访问令牌过期时间（秒）")
    user: dict = Field(..., description="用户信息")


class MFADisableRequest(BaseModel):
    """MFA禁用请求模型"""
    password: str = Field(..., min_length=8, description="密码")
    code: str = Field(..., min_length=6, max_length=6, description="MFA验证码")


class CaptchaResponse(BaseModel):
    """验证码响应模型"""
    key: str = Field(..., description="验证码key")
    image: str = Field(..., description="验证码图片（Base64编码）")
    expires_in: int = Field(..., description="验证码过期时间（秒）")


class UserSession(BaseModel):
    """用户会话模型"""
    id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="用户ID")
    device_info: Optional[str] = Field(None, description="设备信息")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    is_current: bool = Field(..., description="是否为当前会话")
    created_at: datetime = Field(..., description="创建时间")
    last_accessed_at: Optional[datetime] = Field(None, description="最后访问时间")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class UserSessionsResponse(BaseModel):
    """用户会话列表响应模型"""
    sessions: List[UserSession] = Field(..., description="会话列表")
    total: int = Field(..., description="总数量")


class LogoutRequest(BaseModel):
    """登出请求模型"""
    all_devices: bool = Field(default=False, description="是否登出所有设备")


class LogoutResponse(BaseModel):
    """登出响应模型"""
    message: str = Field(..., description="消息")


class VerifyEmailRequest(BaseModel):
    """邮箱验证请求模型"""
    token: str = Field(..., description="验证令牌")


class VerifyEmailResponse(BaseModel):
    """邮箱验证响应模型"""
    message: str = Field(..., description="消息")


class ResendVerificationEmailRequest(BaseModel):
    """重新发送验证邮件请求模型"""
    email: EmailStr = Field(..., description="邮箱")
    captcha: str = Field(..., description="验证码")
    captcha_key: str = Field(..., description="验证码key")


class ResendVerificationEmailResponse(BaseModel):
    """重新发送验证邮件响应模型"""
    message: str = Field(..., description="消息")


# 用户角色权限管理相关
class UserRoleAssignmentRequest(BaseModel):
    """用户角色分配请求"""
    user_id: int = Field(..., description="用户ID")
    role_id: int = Field(..., description="角色ID")
    reason: Optional[str] = Field(None, description="分配原因")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class BatchRoleAssignmentRequest(BaseModel):
    """批量角色分配请求"""
    user_ids: List[int] = Field(..., description="用户ID列表")
    role_ids: List[int] = Field(..., description="角色ID列表")
    reason: Optional[str] = Field(None, description="分配原因")
    
    @validator('user_ids')
    def validate_user_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError("用户ID列表不能为空")
        if len(v) > 100:
            raise ValueError("批量操作用户数量不能超过100")
        return v
    
    @validator('role_ids')
    def validate_role_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError("角色ID列表不能为空")
        if len(v) > 10:
            raise ValueError("批量操作角色数量不能超过10")
        return v


class UserRoleResponse(BaseModel):
    """用户角色响应"""
    id: int
    code: str
    name: str
    description: Optional[str]
    priority: int
    is_system_role: bool
    assigned_at: Optional[datetime]
    expires_at: Optional[datetime]