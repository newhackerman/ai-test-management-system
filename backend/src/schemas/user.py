"""
用户相关的数据模型
"""
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from enum import Enum


class UserStatus(str, Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    LOCKED = "locked"
    PENDING = "pending"
    DELETED = "deleted"


class Gender(str, Enum):
    """性别枚举"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    bio: Optional[str] = Field(None, description="个人简介")
    gender: Optional[Gender] = Field(Gender.UNKNOWN, description="性别")
    birthday: Optional[datetime] = Field(None, description="生日")
    location: Optional[str] = Field(None, max_length=100, description="所在地")
    website: Optional[str] = Field(None, max_length=255, description="个人网站")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")


class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., min_length=8, description="密码")
    full_name: Optional[str] = Field(None, description="全名")
    roles: Optional[List[str]] = Field(default_factory=list, description="角色列表")
    role_ids: Optional[List[int]] = Field(default_factory=list, description="角色ID列表")
    is_active: bool = Field(True, description="是否激活")
    # 允许创建用户时直接指定超级管理员标记；默认 False，不影响普通调用。
    # 之前由于 schema 未声明该字段，调用方传入的 is_superuser=true 会被
    # Pydantic 静默丢弃，导致依赖超级用户短路逻辑的测试账号拿不到权限。
    is_superuser: bool = Field(False, description="是否超级管理员")
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("密码长度至少8位")
        return v


class UserUpdate(BaseModel):
    """更新用户模型"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    bio: Optional[str] = Field(None, description="个人简介")
    gender: Optional[Gender] = Field(None, description="性别")
    birthday: Optional[datetime] = Field(None, description="生日")
    location: Optional[str] = Field(None, max_length=100, description="所在地")
    website: Optional[str] = Field(None, max_length=255, description="个人网站")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    is_active: Optional[bool] = Field(None, description="是否激活")
    language: Optional[str] = Field(None, description="语言设置")
    timezone: Optional[str] = Field(None, description="时区设置")
    theme: Optional[str] = Field(None, description="主题设置")
    email_notifications: Optional[bool] = Field(None, description="邮件通知")
    sms_notifications: Optional[bool] = Field(None, description="短信通知")
    push_notifications: Optional[bool] = Field(None, description="推送通知")
    role_ids: Optional[List[int]] = Field(None, description="角色ID列表")


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    nickname: Optional[str] = Field(None, description="昵称")
    phone: Optional[str] = Field(None, description="手机号")
    bio: Optional[str] = Field(None, description="个人简介")
    gender: Optional[Gender] = Field(None, description="性别")
    birthday: Optional[datetime] = Field(None, description="生日")
    location: Optional[str] = Field(None, description="所在地")
    website: Optional[str] = Field(None, description="个人网站")
    avatar: Optional[str] = Field(None, description="头像URL")
    
    # 状态相关
    status: UserStatus = Field(..., description="用户状态")
    is_active: bool = Field(..., description="是否激活")
    is_superuser: bool = Field(..., description="是否超级用户")
    is_email_verified: bool = Field(..., description="邮箱是否已验证")
    is_phone_verified: bool = Field(..., description="手机是否已验证")
    mfa_enabled: bool = Field(..., description="是否启用多因素认证")
    
    # 时间相关
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    last_login_ip: Optional[str] = Field(None, description="最后登录IP")
    
    # 偏好设置
    language: str = Field(default="zh-CN", description="语言设置")
    timezone: str = Field(default="Asia/Shanghai", description="时区设置")
    theme: str = Field(default="light", description="主题设置")
    email_notifications: bool = Field(default=True, description="邮件通知")
    sms_notifications: bool = Field(default=False, description="短信通知")
    push_notifications: bool = Field(default=True, description="推送通知")
    
    # 关联数据
    roles: Optional[List[Any]] = Field(default_factory=list, description="用户角色")
    permissions: Optional[List[str]] = Field(default_factory=list, description="用户权限")
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        """从ORM对象创建响应模型"""
        roles = getattr(obj, "_role_items", None)
        if roles is None:
            roles = []
            for user_role in getattr(obj, "__dict__", {}).get("roles", []) or []:
                role = getattr(user_role, "__dict__", {}).get("role")
                if role:
                    roles.append({
                        "id": role.id,
                        "code": role.code,
                        "name": role.name,
                        "description": role.description,
                        "is_system_role": role.is_system_role,
                        "is_active": role.is_active,
                        "priority": getattr(role, "priority", 0),
                        "created_at": role.created_at.isoformat() if role.created_at else None,
                        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
                        "sort_order": getattr(role, "sort_order", 0),
                    })

        data = {
            "id": obj.id,
            "username": obj.username,
            "email": obj.email,
            "nickname": obj.nickname,
            "phone": obj.phone,
            "bio": obj.bio,
            "gender": obj.gender,
            "birthday": obj.birthday,
            "location": obj.location,
            "website": obj.website,
            "avatar": obj.avatar,
            "status": obj.status.value if hasattr(obj.status, "value") else obj.status,
            "is_active": obj.is_active,
            "is_superuser": obj.is_superuser,
            "is_email_verified": obj.is_email_verified,
            "is_phone_verified": obj.is_phone_verified,
            "mfa_enabled": obj.mfa_enabled,
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "last_login_at": obj.last_login_at,
            "last_login_ip": obj.last_login_ip,
            "language": obj.language,
            "timezone": obj.timezone,
            "theme": obj.theme,
            "email_notifications": obj.email_notifications,
            "sms_notifications": obj.sms_notifications,
            "push_notifications": obj.push_notifications,
            "roles": roles,
            "permissions": []  # TODO: 从关联表获取
        }
        return cls(**data)


class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: List[UserResponse] = Field(..., description="用户列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")


class UserPermissionsResponse(BaseModel):
    """用户权限响应模型"""
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    roles: List[Any] = Field(..., description="用户角色")
    all_permissions: List[str] = Field(..., description="所有权限")


class BatchUserOperation(BaseModel):
    """批量用户操作模型"""
    action: str = Field(..., description="操作类型: activate, deactivate, delete, assign_role, remove_role")
    user_ids: List[int] = Field(..., description="用户ID列表")
    role_id: Optional[int] = Field(None, description="角色ID（用于角色操作）")
    reason: Optional[str] = Field(None, description="操作原因")
    
    @validator("action")
    def validate_action(cls, v):
        allowed_actions = ["activate", "deactivate", "delete", "assign_role", "remove_role"]
        if v not in allowed_actions:
            raise ValueError(f"操作类型必须是: {', '.join(allowed_actions)}")
        return v


class BatchOperationResponse(BaseModel):
    """批量操作响应模型"""
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    total_count: int = Field(..., description="总数量")
    failed_users: List[dict] = Field(..., description="失败的用户")
    message: str = Field(..., description="操作消息")


class PasswordChangeRequest(BaseModel):
    """修改密码请求模型"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("密码不匹配")
        return v


class PasswordResetRequest(BaseModel):
    """重置密码请求模型"""
    new_password: str = Field(..., min_length=8, description="新密码")
    force_change: bool = Field(True, description="是否强制下次登录修改密码")


class UserLockRequest(BaseModel):
    """锁定用户请求模型"""
    reason: Optional[str] = Field(None, description="锁定原因")


class UserUnlockRequest(BaseModel):
    """解锁用户请求模型"""
    reason: Optional[str] = Field(None, description="解锁原因")


class UserRoleAssignment(BaseModel):
    """用户角色分配模型"""
    role_ids: List[int] = Field(..., description="角色ID列表")


class UserSearchParams(BaseModel):
    """用户搜索参数模型"""
    search: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[UserStatus] = Field(None, description="用户状态")
    role: Optional[str] = Field(None, description="角色筛选")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_superuser: Optional[bool] = Field(None, description="是否超级用户")
    created_after: Optional[datetime] = Field(None, description="创建时间起始")
    created_before: Optional[datetime] = Field(None, description="创建时间结束")
    last_login_after: Optional[datetime] = Field(None, description="最后登录时间起始")
    last_login_before: Optional[datetime] = Field(None, description="最后登录时间结束")


class UserStats(BaseModel):
    """用户统计模型"""
    total_users: int = Field(..., description="总用户数")
    active_users: int = Field(..., description="活跃用户数")
    inactive_users: int = Field(..., description="非活跃用户数")
    locked_users: int = Field(..., description="锁定用户数")
    new_users_today: int = Field(..., description="今日新增用户")
    new_users_this_week: int = Field(..., description="本周新增用户")
    new_users_this_month: int = Field(..., description="本月新增用户")


class UserProfileUpdate(BaseModel):
    """用户个人资料更新模型"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    bio: Optional[str] = Field(None, description="个人简介")
    gender: Optional[Gender] = Field(None, description="性别")
    birthday: Optional[datetime] = Field(None, description="生日")
    location: Optional[str] = Field(None, max_length=100, description="所在地")
    website: Optional[str] = Field(None, max_length=255, description="个人网站")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    language: Optional[str] = Field(None, description="语言设置")
    timezone: Optional[str] = Field(None, description="时区设置")
    theme: Optional[str] = Field(None, description="主题设置")
    email_notifications: Optional[bool] = Field(None, description="邮件通知")
    sms_notifications: Optional[bool] = Field(None, description="短信通知")
    push_notifications: Optional[bool] = Field(None, description="推送通知")
