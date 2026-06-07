"""
权限相关的数据模型
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class PermissionType(str, Enum):
    """权限类型枚举"""
    MENU = "menu"
    BUTTON = "button"
    API = "api"
    DATA = "data"
    FIELD = "field"


class PermissionEffect(str, Enum):
    """权限效果枚举"""
    ALLOW = "allow"
    DENY = "deny"


class PermissionBase(BaseModel):
    """权限基础模型"""
    code: str = Field(..., min_length=1, max_length=100, description="权限代码")
    name: str = Field(..., min_length=1, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    module: str = Field(..., min_length=1, max_length=50, description="所属模块")
    action: str = Field(..., min_length=1, max_length=50, description="操作类型")
    resource: Optional[str] = Field(None, max_length=100, description="资源标识")
    permission_type: PermissionType = Field(PermissionType.API, description="权限类型")


class PermissionCreate(PermissionBase):
    """创建权限模型"""
    parent_id: Optional[int] = Field(None, description="父权限ID")
    level: int = Field(1, ge=1, le=10, description="权限层级")
    sort_order: int = Field(0, description="排序顺序")
    effect: PermissionEffect = Field(PermissionEffect.ALLOW, description="权限效果")
    conditions: Optional[dict] = Field(None, description="权限条件")
    is_system_permission: bool = Field(False, description="是否系统权限")


class PermissionUpdate(BaseModel):
    """更新权限模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    module: Optional[str] = Field(None, min_length=1, max_length=50, description="所属模块")
    action: Optional[str] = Field(None, min_length=1, max_length=50, description="操作类型")
    resource: Optional[str] = Field(None, max_length=100, description="资源标识")
    permission_type: Optional[PermissionType] = Field(None, description="权限类型")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    effect: Optional[PermissionEffect] = Field(None, description="权限效果")
    conditions: Optional[dict] = Field(None, description="权限条件")
    is_active: Optional[bool] = Field(None, description="是否激活")


class PermissionResponse(BaseModel):
    """权限响应模型"""
    id: int = Field(..., description="权限ID")
    code: str = Field(..., description="权限代码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    module: str = Field(..., description="所属模块")
    action: str = Field(..., description="操作类型")
    resource: Optional[str] = Field(None, description="资源标识")
    permission_type: PermissionType = Field(..., description="权限类型")
    parent_id: Optional[int] = Field(None, description="父权限ID")
    level: int = Field(..., description="权限层级")
    sort_order: int = Field(..., description="排序顺序")
    path: Optional[str] = Field(None, description="权限路径")
    effect: PermissionEffect = Field(..., description="权限效果")
    conditions: Optional[dict] = Field(None, description="权限条件")
    is_system_permission: bool = Field(..., description="是否系统权限")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        """从ORM对象创建响应模型"""
        return cls(
            id=obj.id,
            code=obj.code,
            name=obj.name,
            description=obj.description,
            module=obj.module,
            action=obj.action,
            resource=obj.resource,
            permission_type=obj.permission_type,
            parent_id=obj.parent_id,
            level=obj.level,
            sort_order=obj.sort_order,
            path=obj.path,
            effect=obj.effect,
            conditions=obj.conditions,
            is_system_permission=obj.is_system_permission,
            is_active=obj.is_active,
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


class PermissionListResponse(BaseModel):
    """权限列表响应模型"""
    permissions: List[Any] = Field(..., description="权限列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")


class UserPermissionAssignment(BaseModel):
    """用户权限分配模型"""
    permission_id: int = Field(..., description="权限ID")
    effect: PermissionEffect = Field(PermissionEffect.ALLOW, description="权限效果")
    expires_at: Optional[str] = Field(None, description="过期时间")
    reason: Optional[str] = Field(None, description="授权原因")


class RolePermissionAssignment(BaseModel):
    """角色权限分配模型"""
    permission_ids: List[int] = Field(..., description="权限ID列表")
    effect: PermissionEffect = Field(PermissionEffect.ALLOW, description="权限效果")
    conditions: Optional[dict] = Field(None, description="权限条件")


class PermissionCheckRequest(BaseModel):
    """权限检查请求模型"""
    permission_codes: List[str] = Field(..., description="权限代码列表")
    user_id: Optional[int] = Field(None, description="用户ID（可选）")


class PermissionCheckResponse(BaseModel):
    """权限检查响应模型"""
    permissions: dict = Field(..., description="权限检查结果")


class PermissionTreeNode(BaseModel):
    """权限树节点模型"""
    id: int = Field(..., description="权限ID")
    code: str = Field(..., description="权限代码")
    name: str = Field(..., description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    module: str = Field(..., description="所属模块")
    action: str = Field(..., description="操作类型")
    resource: Optional[str] = Field(None, description="资源标识")
    permission_type: PermissionType = Field(..., description="权限类型")
    level: int = Field(..., description="权限层级")
    parent_id: Optional[int] = Field(None, description="父权限ID")
    sort_order: int = Field(..., description="排序顺序")
    is_active: bool = Field(..., description="是否激活")
    children: List['PermissionTreeNode'] = Field(default_factory=list, description="子权限")


class PermissionGroupBase(BaseModel):
    """权限组基础模型"""
    code: str = Field(..., min_length=1, max_length=100, description="权限组代码")
    name: str = Field(..., min_length=1, max_length=100, description="权限组名称")
    description: Optional[str] = Field(None, description="权限组描述")
    color: Optional[str] = Field(None, max_length=20, description="显示颜色")
    icon: Optional[str] = Field(None, max_length=50, description="图标")


class PermissionGroupCreate(PermissionGroupBase):
    """创建权限组模型"""
    sort_order: int = Field(0, description="排序顺序")
    permission_ids: List[int] = Field(default_factory=list, description="权限ID列表")


class PermissionGroupUpdate(BaseModel):
    """更新权限组模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="权限组名称")
    description: Optional[str] = Field(None, description="权限组描述")
    color: Optional[str] = Field(None, max_length=20, description="显示颜色")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    is_active: Optional[bool] = Field(None, description="是否激活")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class PermissionGroupResponse(BaseModel):
    """权限组响应模型"""
    id: int = Field(..., description="权限组ID")
    code: str = Field(..., description="权限组代码")
    name: str = Field(..., description="权限组名称")
    description: Optional[str] = Field(None, description="权限组描述")
    color: Optional[str] = Field(None, description="显示颜色")
    icon: Optional[str] = Field(None, description="图标")
    sort_order: int = Field(..., description="排序顺序")
    is_active: bool = Field(..., description="是否激活")
    permission_count: int = Field(..., description="权限数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    permissions: List[PermissionResponse] = Field(default_factory=list, description="权限列表")
    
    class Config:
        from_attributes = True


class DataPermissionBase(BaseModel):
    """数据权限基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="数据权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    resource_type: str = Field(..., min_length=1, max_length=50, description="资源类型")
    scope_type: str = Field(..., description="范围类型: all, dept, self, custom")
    scope_value: Optional[dict] = Field(None, description="范围值")
    filter_conditions: Optional[dict] = Field(None, description="过滤条件")
    field_permissions: Optional[dict] = Field(None, description="字段权限")


class DataPermissionCreate(DataPermissionBase):
    """创建数据权限模型"""
    priority: int = Field(0, description="优先级")


class DataPermissionUpdate(BaseModel):
    """更新数据权限模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="数据权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    scope_type: Optional[str] = Field(None, description="范围类型")
    scope_value: Optional[dict] = Field(None, description="范围值")
    filter_conditions: Optional[dict] = Field(None, description="过滤条件")
    field_permissions: Optional[dict] = Field(None, description="字段权限")
    is_active: Optional[bool] = Field(None, description="是否激活")
    priority: Optional[int] = Field(None, description="优先级")


class DataPermissionResponse(BaseModel):
    """数据权限响应模型"""
    id: int = Field(..., description="数据权限ID")
    name: str = Field(..., description="数据权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    resource_type: str = Field(..., description="资源类型")
    scope_type: str = Field(..., description="范围类型")
    scope_value: Optional[dict] = Field(None, description="范围值")
    filter_conditions: Optional[dict] = Field(None, description="过滤条件")
    field_permissions: Optional[dict] = Field(None, description="字段权限")
    is_active: bool = Field(..., description="是否激活")
    priority: int = Field(..., description="优先级")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


# 更新前向引用
PermissionTreeNode.model_rebuild()