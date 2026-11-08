"""
角色管理模型
"""
from sqlalchemy import Column, BigInteger, String, Boolean, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from .base import BaseModel


class Role(BaseModel):
    """角色模型"""
    __tablename__ = "roles"

    # 基本信息
    code = Column(String(100), unique=True, index=True, nullable=False, comment="角色代码")
    name = Column(String(100), nullable=False, comment="角色名称")
    description = Column(Text, nullable=True, comment="角色描述")
    
    # 显示配置
    color = Column(String(20), nullable=True, comment="显示颜色")
    icon = Column(String(50), nullable=True, comment="图标")
    
    # 层级结构
    parent_id = Column(BigInteger, ForeignKey("roles.id"), nullable=True, comment="父角色ID")
    level = Column(Integer, default=1, nullable=False, comment="角色层级")
    path = Column(String(500), nullable=True, comment="角色路径")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序顺序")
    
    # 角色配置
    is_system_role = Column(Boolean, default=False, nullable=False, comment="是否系统角色")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    priority = Column(Integer, default=0, nullable=False, comment="优先级")
    max_users = Column(Integer, nullable=True, comment="最大用户数限制")
    
    # 权限继承配置
    inherit_parent_permissions = Column(Boolean, default=True, nullable=False, comment="是否继承父角色权限")
    permission_policy = Column(String(20), default="merge", nullable=False, comment="权限策略: merge, override, deny")
    
    # 数据权限配置
    data_scope = Column(String(20), default="all", nullable=False, comment="数据范围: all, dept, self, custom")
    data_scope_config = Column(JSON, nullable=True, comment="数据范围配置")
    
    # 关联关系
    parent = relationship("Role", remote_side="Role.id", back_populates="children")
    children = relationship("Role", back_populates="parent", cascade="all, delete-orphan")
    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    
    @property
    def user_count(self):
        """获取角色用户数量"""
        return len(self.users)
    
    @property
    def permission_count(self):
        """获取角色权限数量"""
        return len(self.permissions)


class RoleGroup(BaseModel):
    """角色组模型"""
    __tablename__ = "role_groups"

    # 基本信息
    code = Column(String(100), unique=True, index=True, nullable=False, comment="角色组代码")
    name = Column(String(100), nullable=False, comment="角色组名称")
    description = Column(Text, nullable=True, comment="角色组描述")
    color = Column(String(20), nullable=True, comment="显示颜色")
    icon = Column(String(50), nullable=True, comment="图标")
    
    # 配置
    sort_order = Column(Integer, default=0, nullable=False, comment="排序顺序")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    
    # 关联关系
    roles = relationship("RoleGroupItem", back_populates="group", cascade="all, delete-orphan")


class RoleGroupItem(BaseModel):
    """角色组项目关联表"""
    __tablename__ = "role_group_items"

    group_id = Column(BigInteger, ForeignKey("role_groups.id", ondelete="CASCADE"), nullable=False, comment="角色组ID")
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, comment="角色ID")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序顺序")
    
    # 关联关系
    group = relationship("RoleGroup", back_populates="roles")
    role = relationship("Role")


class RoleTemplate(BaseModel):
    """角色模板模型"""
    __tablename__ = "role_templates"

    # 基本信息
    name = Column(String(100), nullable=False, comment="模板名称")
    description = Column(Text, nullable=True, comment="模板描述")
    category = Column(String(50), nullable=True, comment="模板分类")
    
    # 模板配置
    template_data = Column(JSON, nullable=False, comment="模板数据")
    is_system_template = Column(Boolean, default=False, nullable=False, comment="是否系统模板")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    
    # 使用统计
    usage_count = Column(Integer, default=0, nullable=False, comment="使用次数")
    last_used_at = Column(String(50), nullable=True, comment="最后使用时间")


class RoleApproval(BaseModel):
    """角色审批模型"""
    __tablename__ = "role_approvals"

    # 基本信息
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="申请用户ID")
    role_id = Column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, comment="申请角色ID")
    action = Column(String(20), nullable=False, comment="操作类型: assign, remove")
    
    # 申请信息
    reason = Column(Text, nullable=True, comment="申请原因")
    status = Column(String(20), default="pending", nullable=False, comment="审批状态: pending, approved, rejected")
    
    # 审批信息
    approver_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, comment="审批人ID")
    approved_at = Column(String(50), nullable=True, comment="审批时间")
    approval_reason = Column(Text, nullable=True, comment="审批意见")
    
    # 有效期
    effective_at = Column(String(50), nullable=True, comment="生效时间")
    expires_at = Column(String(50), nullable=True, comment="过期时间")
    
    # 关联关系
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("Role")
    approver = relationship("User", foreign_keys=[approver_id])