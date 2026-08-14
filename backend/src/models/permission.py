"""
权限管理模型
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .base import BaseModel


class PermissionType(PyEnum):
    """权限类型枚举"""
    MENU = "menu"           # 菜单权限
    BUTTON = "button"       # 按钮权限
    API = "api"            # API权限
    DATA = "data"          # 数据权限
    FIELD = "field"        # 字段权限
    FUNCTION = "function"        # 功能权限
    OPERATION = "operation"      # 操作权限
    MODULE = "module"            # 模块权限
    CONFIG = "config"            # 配置权限
    GROUP = "group"              # 分组权限
    ENVIRONMENT = "environment"  # 环境权限
    GLOBAL = "global"            # 全局权限


class PermissionEffect(PyEnum):
    """权限效果枚举"""
    ALLOW = "allow"        # 允许
    DENY = "deny"          # 拒绝


class Permission(BaseModel):
    """权限模型"""
    __tablename__ = "permissions"

    # 基本信息
    code = Column(String(100), unique=True, index=True, nullable=False, comment="权限代码")
    name = Column(String(100), nullable=False, comment="权限名称")
    description = Column(Text, nullable=True, comment="权限描述")
    
    # 权限分类
    module = Column(String(50), nullable=False, comment="所属模块")
    action = Column(String(50), nullable=False, comment="操作类型")
    resource = Column(String(100), nullable=True, comment="资源标识")
    permission_type = Column(Enum(PermissionType, values_callable=lambda e: [v.value for v in e]), default=PermissionType.API, comment="权限类型")
    
    # 层级结构
    parent_id = Column(Integer, ForeignKey("permissions.id"), nullable=True, comment="父权限ID")
    level = Column(Integer, default=1, nullable=False, comment="权限层级")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序顺序")
    path = Column(String(500), nullable=True, comment="权限路径")
    
    # 权限配置
    effect = Column(Enum(PermissionEffect, values_callable=lambda e: [v.value for v in e]), default=PermissionEffect.ALLOW, comment="权限效果")
    conditions = Column(JSON, nullable=True, comment="权限条件")
    is_system_permission = Column(Boolean, default=False, nullable=False, comment="是否系统权限")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    
    # 关联关系
    parent = relationship("Permission", remote_side="Permission.id", back_populates="children")
    children = relationship("Permission", back_populates="parent", cascade="all, delete-orphan")
    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(BaseModel):
    """角色权限关联表"""
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, comment="角色ID")
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, comment="权限ID")
    
    # 权限配置
    effect = Column(Enum(PermissionEffect, values_callable=lambda e: [v.value for v in e]), default=PermissionEffect.ALLOW, comment="权限效果")
    conditions = Column(JSON, nullable=True, comment="权限条件")
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="授权人")
    granted_at = Column(String(50), nullable=True, comment="授权时间")
    expires_at = Column(String(50), nullable=True, comment="过期时间")
    
    # 关联关系
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")
    granter = relationship("User", foreign_keys=[granted_by])


class UserPermission(BaseModel):
    """用户直接权限表"""
    __tablename__ = "user_permissions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, comment="权限ID")
    
    # 权限配置
    effect = Column(Enum(PermissionEffect, values_callable=lambda e: [v.value for v in e]), default=PermissionEffect.ALLOW, comment="权限效果")
    conditions = Column(JSON, nullable=True, comment="权限条件")
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="授权人")
    granted_at = Column(String(50), nullable=True, comment="授权时间")
    expires_at = Column(String(50), nullable=True, comment="过期时间")
    reason = Column(Text, nullable=True, comment="授权原因")
    
    # 关联关系
    user = relationship("User", foreign_keys=[user_id])
    permission = relationship("Permission")
    granter = relationship("User", foreign_keys=[granted_by])


class PermissionGroup(BaseModel):
    """权限组模型"""
    __tablename__ = "permission_groups"

    # 基本信息
    code = Column(String(100), unique=True, index=True, nullable=False, comment="权限组代码")
    name = Column(String(100), nullable=False, comment="权限组名称")
    description = Column(Text, nullable=True, comment="权限组描述")
    color = Column(String(20), nullable=True, comment="显示颜色")
    icon = Column(String(50), nullable=True, comment="图标")
    
    # 配置
    sort_order = Column(Integer, default=0, nullable=False, comment="排序顺序")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    
    # 关联关系
    permissions = relationship("PermissionGroupItem", back_populates="group", cascade="all, delete-orphan")


class PermissionGroupItem(BaseModel):
    """权限组项目关联表"""
    __tablename__ = "permission_group_items"

    group_id = Column(Integer, ForeignKey("permission_groups.id", ondelete="CASCADE"), nullable=False, comment="权限组ID")
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, comment="权限ID")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序顺序")
    
    # 关联关系
    group = relationship("PermissionGroup", back_populates="permissions")
    permission = relationship("Permission")


class DataPermission(BaseModel):
    """数据权限模型"""
    __tablename__ = "data_permissions"

    # 基本信息
    name = Column(String(100), nullable=False, comment="数据权限名称")
    description = Column(Text, nullable=True, comment="权限描述")
    
    # 数据范围配置
    resource_type = Column(String(50), nullable=False, comment="资源类型")
    scope_type = Column(String(20), nullable=False, comment="范围类型: all, dept, self, custom")
    scope_value = Column(JSON, nullable=True, comment="范围值")
    
    # 过滤条件
    filter_conditions = Column(JSON, nullable=True, comment="过滤条件")
    field_permissions = Column(JSON, nullable=True, comment="字段权限")
    
    # 配置
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    priority = Column(Integer, default=0, nullable=False, comment="优先级")


class UserDataPermission(BaseModel):
    """用户数据权限关联表"""
    __tablename__ = "user_data_permissions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    data_permission_id = Column(Integer, ForeignKey("data_permissions.id", ondelete="CASCADE"), nullable=False, comment="数据权限ID")
    
    # 权限配置
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="授权人")
    granted_at = Column(String(50), nullable=True, comment="授权时间")
    expires_at = Column(String(50), nullable=True, comment="过期时间")
    
    # 关联关系
    user = relationship("User", foreign_keys=[user_id])
    data_permission = relationship("DataPermission")
    granter = relationship("User", foreign_keys=[granted_by])