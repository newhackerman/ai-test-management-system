"""
用户角色权限管理相关的Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PermissionEffect(str, Enum):
    """权限效果枚举"""
    ALLOW = "allow"
    DENY = "deny"


class DataScopeType(str, Enum):
    """数据范围类型枚举"""
    ALL = "all"
    DEPT = "dept"
    SELF = "self"
    CUSTOM = "custom"


# 用户角色分配相关
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


class UserPermissionResponse(BaseModel):
    """用户权限响应"""
    code: str
    name: str
    module: str
    action: str
    resource: Optional[str]
    effect: PermissionEffect


class UserDataScopeResponse(BaseModel):
    """用户数据权限范围响应"""
    scope_type: DataScopeType
    scope_value: List[str]
    departments: List[str]
    projects: List[str]
    custom_rules: List[Dict[str, Any]]


# 角色管理相关
class RoleCreateRequest(BaseModel):
    """角色创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="角色名称")
    code: str = Field(..., min_length=1, max_length=100, description="角色代码")
    description: Optional[str] = Field(None, max_length=500, description="角色描述")
    priority: int = Field(0, ge=0, le=100, description="优先级")
    is_system_role: bool = Field(False, description="是否系统角色")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")
    parent_id: Optional[int] = Field(None, description="父角色ID")
    data_scope: DataScopeType = Field(DataScopeType.ALL, description="数据范围")
    data_scope_config: Optional[Dict[str, Any]] = Field(None, description="数据范围配置")
    max_users: Optional[int] = Field(None, ge=1, description="最大用户数限制")
    
    @validator('code')
    def validate_code(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("角色代码只能包含字母、数字、下划线和连字符")
        return v.lower()


class RoleUpdateRequest(BaseModel):
    """角色更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="角色名称")
    code: Optional[str] = Field(None, min_length=1, max_length=100, description="角色代码")
    description: Optional[str] = Field(None, max_length=500, description="角色描述")
    priority: Optional[int] = Field(None, ge=0, le=100, description="优先级")
    is_active: Optional[bool] = Field(None, description="是否激活")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")
    data_scope: Optional[DataScopeType] = Field(None, description="数据范围")
    data_scope_config: Optional[Dict[str, Any]] = Field(None, description="数据范围配置")
    max_users: Optional[int] = Field(None, ge=1, description="最大用户数限制")


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    code: str
    name: str
    description: Optional[str]
    priority: int
    is_system_role: bool
    is_active: bool
    user_count: int
    permission_count: int
    parent_id: Optional[int]
    level: int
    data_scope: DataScopeType
    data_scope_config: Optional[Dict[str, Any]]
    max_users: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class RoleHierarchyResponse(BaseModel):
    """角色层级响应"""
    role: Dict[str, Any]
    parent_chain: List[Dict[str, Any]]
    child_roles: List[Dict[str, Any]]


# 权限管理相关
class PermissionCreateRequest(BaseModel):
    """权限创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="权限名称")
    code: str = Field(..., min_length=1, max_length=100, description="权限代码")
    module: str = Field(..., min_length=1, max_length=50, description="所属模块")
    action: str = Field(..., min_length=1, max_length=50, description="操作类型")
    resource: Optional[str] = Field(None, max_length=100, description="资源标识")
    description: Optional[str] = Field(None, max_length=500, description="权限描述")
    parent_id: Optional[int] = Field(None, description="父权限ID")
    conditions: Optional[Dict[str, Any]] = Field(None, description="权限条件")
    
    @validator('code')
    def validate_code(cls, v):
        if ':' not in v:
            raise ValueError("权限代码格式应为 'module:action'")
        parts = v.split(':')
        if len(parts) != 2:
            raise ValueError("权限代码格式应为 'module:action'")
        return v.lower()


class PermissionUpdateRequest(BaseModel):
    """权限更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="权限名称")
    code: Optional[str] = Field(None, min_length=1, max_length=100, description="权限代码")
    module: Optional[str] = Field(None, min_length=1, max_length=50, description="所属模块")
    action: Optional[str] = Field(None, min_length=1, max_length=50, description="操作类型")
    resource: Optional[str] = Field(None, max_length=100, description="资源标识")
    description: Optional[str] = Field(None, max_length=500, description="权限描述")
    is_active: Optional[bool] = Field(None, description="是否激活")
    conditions: Optional[Dict[str, Any]] = Field(None, description="权限条件")


class PermissionResponse(BaseModel):
    """权限响应"""
    id: int
    code: str
    name: str
    description: Optional[str]
    module: str
    action: str
    resource: Optional[str]
    permission_type: Optional[str]
    parent_id: Optional[int]
    level: int
    is_active: bool
    conditions: Optional[Dict[str, Any]]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


# 角色权限关联相关
class RolePermissionAssignmentRequest(BaseModel):
    """角色权限分配请求"""
    role_id: int = Field(..., description="角色ID")
    permission_ids: List[int] = Field(..., description="权限ID列表")
    effect: PermissionEffect = Field(PermissionEffect.ALLOW, description="权限效果")
    conditions: Optional[Dict[str, Any]] = Field(None, description="权限条件")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class RolePermissionResponse(BaseModel):
    """角色权限响应"""
    role_id: int
    permission_id: int
    permission_code: str
    permission_name: str
    effect: PermissionEffect
    conditions: Optional[Dict[str, Any]]
    granted_by: Optional[int]
    granted_at: Optional[datetime]
    expires_at: Optional[datetime]


# 权限检查相关
class PermissionCheckRequest(BaseModel):
    """权限检查请求"""
    permission_code: str = Field(..., description="权限代码")
    resource_id: Optional[str] = Field(None, description="资源ID")


class PermissionCheckResponse(BaseModel):
    """权限检查响应"""
    user_id: int
    permission_code: str
    resource_id: Optional[str]
    has_permission: bool
    check_time: datetime


class RoleCheckRequest(BaseModel):
    """角色检查请求"""
    role_code: str = Field(..., description="角色代码")


class RoleCheckResponse(BaseModel):
    """角色检查响应"""
    user_id: int
    role_code: str
    has_role: bool
    check_time: datetime


# 数据权限相关
class DataPermissionCreateRequest(BaseModel):
    """数据权限创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="数据权限名称")
    description: Optional[str] = Field(None, max_length=500, description="权限描述")
    resource_type: str = Field(..., min_length=1, max_length=50, description="资源类型")
    scope_type: DataScopeType = Field(..., description="范围类型")
    scope_value: Optional[List[str]] = Field(None, description="范围值")
    filter_conditions: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    field_permissions: Optional[Dict[str, Any]] = Field(None, description="字段权限")
    priority: int = Field(0, ge=0, le=100, description="优先级")


class DataPermissionResponse(BaseModel):
    """数据权限响应"""
    id: int
    name: str
    description: Optional[str]
    resource_type: str
    scope_type: DataScopeType
    scope_value: Optional[List[str]]
    filter_conditions: Optional[Dict[str, Any]]
    field_permissions: Optional[Dict[str, Any]]
    is_active: bool
    priority: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


# 审计日志相关
class RoleAssignmentAuditResponse(BaseModel):
    """角色分配审计响应"""
    id: int
    user_id: int
    role_id: int
    action: str
    assigned_by: Optional[int]
    reason: Optional[str]
    result: str
    created_at: datetime


# 统计相关
class UserRoleStatisticsResponse(BaseModel):
    """用户角色统计响应"""
    total_users: int
    total_roles: int
    total_permissions: int
    active_users: int
    active_roles: int
    role_distribution: Dict[str, int]
    permission_distribution: Dict[str, int]


class RoleUsageStatisticsResponse(BaseModel):
    """角色使用统计响应"""
    role_id: int
    role_name: str
    user_count: int
    permission_count: int
    last_assigned_at: Optional[datetime]
    usage_trend: List[Dict[str, Any]]