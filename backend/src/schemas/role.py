"""
角色相关数据模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RoleBase(BaseModel):
    """角色基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="角色名称")
    code: str = Field(..., min_length=1, max_length=50, description="角色代码")
    description: Optional[str] = Field(None, max_length=500, description="角色描述")
    is_active: bool = Field(True, description="是否激活")
    priority: int = Field(0, description="角色优先级")
    sort_order: int = Field(0, description="排序顺序")


class RoleCreate(RoleBase):
    """创建角色模型"""
    permission_ids: Optional[List[int]] = Field([], description="权限ID列表")
    is_system_role: bool = Field(False, description="是否系统角色")


class RoleUpdate(BaseModel):
    """更新角色模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="角色名称")
    description: Optional[str] = Field(None, max_length=500, description="角色描述")
    is_active: Optional[bool] = Field(None, description="是否激活")
    priority: Optional[int] = Field(None, description="角色优先级")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class PermissionInfo(BaseModel):
    """权限信息模型"""
    id: int
    code: str
    name: str
    description: Optional[str]
    module: str
    type: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    is_system_permission: bool
    is_active: bool
    sort_order: int
    parent_id: Optional[int]

    class Config:
        from_attributes = True


class RoleResponse(RoleBase):
    """角色响应模型"""
    id: int
    is_system_role: bool
    user_count: Optional[int] = None
    permissions: Optional[List[PermissionInfo]] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """角色列表响应模型"""
    roles: List[RoleResponse]
    total: int
    page: int
    size: int


class RoleStatsResponse(BaseModel):
    """角色统计响应模型"""
    total_roles: int = Field(description="总角色数")
    active_roles: int = Field(description="激活角色数")
    inactive_roles: int = Field(description="未激活角色数")
    average_users_per_role: float = Field(description="平均每个角色的用户数")
    total_permissions: int = Field(description="总权限数")


class UserInfo(BaseModel):
    """用户信息模型"""
    id: int
    username: str
    email: str
    nickname: Optional[str]
    status: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class RoleUsersResponse(BaseModel):
    """角色用户列表响应模型"""
    users: List[UserInfo]
    total: int
    page: int
    size: int


class PermissionListResponse(BaseModel):
    """权限列表响应模型"""
    permissions: List[PermissionInfo]


class AssignPermissionsRequest(BaseModel):
    """分配权限请求模型"""
    permission_ids: List[int] = Field(..., description="权限ID列表")