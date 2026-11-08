"""
需求管理权限控制模型

本模块定义了需求管理模块的权限控制相关数据模型，包括：
- 需求级别权限管理
- 基于角色的访问控制(RBAC)
- 操作审计日志
- 数据权限控制
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, JSON, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .base import Base
from .requirement import RequirementBaseModel

class RequirementPermissionType(PyEnum):
    """需求权限类型枚举"""
    # 基本权限
    VIEW = "VIEW"                    # 查看需求
    CREATE = "CREATE"                # 创建需求
    EDIT = "EDIT"                    # 编辑需求
    DELETE = "DELETE"                # 删除需求
    
    # 状态管理权限
    CHANGE_STATUS = "CHANGE_STATUS"  # 变更状态
    APPROVE = "APPROVE"              # 审批需求
    REJECT = "REJECT"                # 拒绝需求
    
    # 评审权限
    REVIEW = "REVIEW"                # 评审需求
    MODERATE_REVIEW = "MODERATE_REVIEW"  # 主持评审
    COMMENT = "COMMENT"              # 评论需求
    
    # 变更管理权限
    REQUEST_CHANGE = "REQUEST_CHANGE"  # 申请变更
    APPROVE_CHANGE = "APPROVE_CHANGE"  # 审批变更
    IMPLEMENT_CHANGE = "IMPLEMENT_CHANGE"  # 实施变更
    
    # 追溯管理权限
    MANAGE_TRACEABILITY = "MANAGE_TRACEABILITY"  # 管理追溯关系
    VIEW_TRACEABILITY = "VIEW_TRACEABILITY"      # 查看追溯关系
    
    # 分析权限
    VIEW_ANALYTICS = "VIEW_ANALYTICS"  # 查看分析报告
    EXPORT_DATA = "EXPORT_DATA"        # 导出数据
    
    # 管理权限
    MANAGE_PERMISSIONS = "MANAGE_PERMISSIONS"  # 管理权限
    MANAGE_CATEGORIES = "MANAGE_CATEGORIES"    # 管理分类
    MANAGE_PRIORITIES = "MANAGE_PRIORITIES"    # 管理优先级

class RequirementDataScope(PyEnum):
    """需求数据范围枚举"""
    ALL = "ALL"                      # 所有需求
    PROJECT = "PROJECT"              # 项目范围
    DEPARTMENT = "DEPARTMENT"        # 部门范围
    TEAM = "TEAM"                    # 团队范围
    ASSIGNED = "ASSIGNED"            # 分配给自己的
    CREATED = "CREATED"              # 自己创建的
    CUSTOM = "CUSTOM"                # 自定义范围

class RequirementPermissionEffect(PyEnum):
    """权限效果枚举"""
    ALLOW = "ALLOW"                  # 允许
    DENY = "DENY"                    # 拒绝

class RequirementRolePermission(RequirementBaseModel):
    """需求角色权限表"""
    __tablename__ = 'requirement_role_permissions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='权限ID')
    role_id = Column(BigInteger, ForeignKey('roles.id'), nullable=False, comment='角色ID')
    permission_type = Column(Enum(RequirementPermissionType), nullable=False, comment='权限类型')
    
    # 权限配置
    effect = Column(Enum(RequirementPermissionEffect), default=RequirementPermissionEffect.ALLOW, comment='权限效果')
    data_scope = Column(Enum(RequirementDataScope), default=RequirementDataScope.ALL, comment='数据范围')
    conditions = Column(JSON, comment='权限条件')
    
    # 项目范围限制
    project_ids = Column(JSON, comment='项目ID列表，为空表示所有项目')
    
    # 状态限制
    allowed_statuses = Column(JSON, comment='允许操作的状态列表')
    
    # 优先级限制
    priority_threshold = Column(String(20), comment='优先级阈值')
    
    # 时间限制
    effective_from = Column(DateTime, comment='生效开始时间')
    effective_to = Column(DateTime, comment='生效结束时间')
    
    # 审计字段
    granted_by = Column(BigInteger, ForeignKey('users.id'), comment='授权人ID')
    granted_at = Column(DateTime, default=datetime.utcnow, comment='授权时间')
    
    # 关联关系
    role = relationship("Role")
    granter = relationship("User", foreign_keys=[granted_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'role_id': self.role_id,
            'permission_type': self.permission_type.value if self.permission_type else None,
            'effect': self.effect.value if self.effect else None,
            'data_scope': self.data_scope.value if self.data_scope else None,
            'conditions': self.conditions,
            'project_ids': self.project_ids,
            'allowed_statuses': self.allowed_statuses,
            'priority_threshold': self.priority_threshold,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'granted_by': self.granted_by,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementUserPermission(RequirementBaseModel):
    """需求用户直接权限表"""
    __tablename__ = 'requirement_user_permissions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='权限ID')
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, comment='用户ID')
    permission_type = Column(Enum(RequirementPermissionType), nullable=False, comment='权限类型')
    
    # 权限配置
    effect = Column(Enum(RequirementPermissionEffect), default=RequirementPermissionEffect.ALLOW, comment='权限效果')
    data_scope = Column(Enum(RequirementDataScope), default=RequirementDataScope.ALL, comment='数据范围')
    conditions = Column(JSON, comment='权限条件')
    
    # 项目范围限制
    project_ids = Column(JSON, comment='项目ID列表，为空表示所有项目')
    
    # 状态限制
    allowed_statuses = Column(JSON, comment='允许操作的状态列表')
    
    # 优先级限制
    priority_threshold = Column(String(20), comment='优先级阈值')
    
    # 时间限制
    effective_from = Column(DateTime, comment='生效开始时间')
    effective_to = Column(DateTime, comment='生效结束时间')
    
    # 审计字段
    granted_by = Column(BigInteger, ForeignKey('users.id'), comment='授权人ID')
    granted_at = Column(DateTime, default=datetime.utcnow, comment='授权时间')
    reason = Column(Text, comment='授权原因')
    
    # 关联关系
    user = relationship("User", foreign_keys=[user_id])
    granter = relationship("User", foreign_keys=[granted_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'permission_type': self.permission_type.value if self.permission_type else None,
            'effect': self.effect.value if self.effect else None,
            'data_scope': self.data_scope.value if self.data_scope else None,
            'conditions': self.conditions,
            'project_ids': self.project_ids,
            'allowed_statuses': self.allowed_statuses,
            'priority_threshold': self.priority_threshold,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'granted_by': self.granted_by,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementResourcePermission(RequirementBaseModel):
    """需求资源级权限表"""
    __tablename__ = 'requirement_resource_permissions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='权限ID')
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, comment='用户ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), nullable=False, comment='需求ID')
    permission_type = Column(Enum(RequirementPermissionType), nullable=False, comment='权限类型')
    
    # 权限配置
    effect = Column(Enum(RequirementPermissionEffect), default=RequirementPermissionEffect.ALLOW, comment='权限效果')
    conditions = Column(JSON, comment='权限条件')
    
    # 时间限制
    effective_from = Column(DateTime, comment='生效开始时间')
    effective_to = Column(DateTime, comment='生效结束时间')
    
    # 审计字段
    granted_by = Column(BigInteger, ForeignKey('users.id'), comment='授权人ID')
    granted_at = Column(DateTime, default=datetime.utcnow, comment='授权时间')
    reason = Column(Text, comment='授权原因')
    
    # 关联关系
    user = relationship("User", foreign_keys=[user_id])
    requirement = relationship("Requirement")
    granter = relationship("User", foreign_keys=[granted_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'requirement_id': self.requirement_id,
            'permission_type': self.permission_type.value if self.permission_type else None,
            'effect': self.effect.value if self.effect else None,
            'conditions': self.conditions,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'granted_by': self.granted_by,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementAuditAction(PyEnum):
    """需求审计操作类型枚举"""
    # 需求操作
    CREATE_REQUIREMENT = "CREATE_REQUIREMENT"
    UPDATE_REQUIREMENT = "UPDATE_REQUIREMENT"
    DELETE_REQUIREMENT = "DELETE_REQUIREMENT"
    VIEW_REQUIREMENT = "VIEW_REQUIREMENT"
    
    # 状态操作
    CHANGE_STATUS = "CHANGE_STATUS"
    APPROVE_REQUIREMENT = "APPROVE_REQUIREMENT"
    REJECT_REQUIREMENT = "REJECT_REQUIREMENT"
    
    # 评审操作
    CREATE_REVIEW = "CREATE_REVIEW"
    SUBMIT_REVIEW_COMMENT = "SUBMIT_REVIEW_COMMENT"
    COMPLETE_REVIEW = "COMPLETE_REVIEW"
    
    # 变更操作
    CREATE_CHANGE_REQUEST = "CREATE_CHANGE_REQUEST"
    APPROVE_CHANGE = "APPROVE_CHANGE"
    IMPLEMENT_CHANGE = "IMPLEMENT_CHANGE"
    
    # 权限操作
    GRANT_PERMISSION = "GRANT_PERMISSION"
    REVOKE_PERMISSION = "REVOKE_PERMISSION"
    
    # 数据操作
    EXPORT_REQUIREMENTS = "EXPORT_REQUIREMENTS"
    IMPORT_REQUIREMENTS = "IMPORT_REQUIREMENTS"
    BULK_UPDATE = "BULK_UPDATE"

class RequirementAuditResult(PyEnum):
    """需求审计结果枚举"""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

class RequirementAuditLog(RequirementBaseModel):
    """需求操作审计日志表"""
    __tablename__ = 'requirement_audit_logs'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='审计日志ID')
    
    # 操作信息
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, comment='操作用户ID')
    action = Column(Enum(RequirementAuditAction), nullable=False, comment='操作类型')
    result = Column(Enum(RequirementAuditResult), nullable=False, comment='操作结果')
    
    # 资源信息
    resource_type = Column(String(50), nullable=False, comment='资源类型')
    resource_id = Column(BigInteger, comment='资源ID')
    requirement_id = Column(BigInteger, ForeignKey('requirements.id'), comment='相关需求ID')
    project_id = Column(BigInteger, ForeignKey('projects.id'), comment='相关项目ID')
    
    # 操作详情
    old_values = Column(JSON, comment='变更前值')
    new_values = Column(JSON, comment='变更后值')
    operation_details = Column(JSON, comment='操作详情')
    
    # 环境信息
    ip_address = Column(String(45), comment='IP地址')
    user_agent = Column(Text, comment='用户代理')
    session_id = Column(String(100), comment='会话ID')
    
    # 错误信息
    error_message = Column(Text, comment='错误信息')
    error_code = Column(String(50), comment='错误代码')
    
    # 权限检查结果
    permission_checked = Column(Boolean, default=True, comment='是否进行了权限检查')
    permission_result = Column(JSON, comment='权限检查结果')
    
    # 时间信息
    operation_duration = Column(Integer, comment='操作耗时(毫秒)')
    
    # 关联关系
    user = relationship("User", foreign_keys=[user_id])
    requirement = relationship("Requirement", foreign_keys=[requirement_id])
    project = relationship("Project", foreign_keys=[project_id])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action.value if self.action else None,
            'result': self.result.value if self.result else None,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'requirement_id': self.requirement_id,
            'project_id': self.project_id,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'operation_details': self.operation_details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'permission_checked': self.permission_checked,
            'permission_result': self.permission_result,
            'operation_duration': self.operation_duration,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RequirementPermissionTemplate(RequirementBaseModel):
    """需求权限模板表"""
    __tablename__ = 'requirement_permission_templates'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='模板ID')
    template_name = Column(String(100), nullable=False, comment='模板名称')
    description = Column(Text, comment='模板描述')
    
    # 模板配置
    permissions = Column(JSON, nullable=False, comment='权限配置')
    data_scope_config = Column(JSON, comment='数据范围配置')
    
    # 适用范围
    applicable_roles = Column(JSON, comment='适用角色')
    applicable_projects = Column(JSON, comment='适用项目')
    
    # 状态管理
    is_active = Column(Boolean, default=True, comment='是否激活')
    is_system_template = Column(Boolean, default=False, comment='是否系统模板')
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment='使用次数')
    last_used_at = Column(DateTime, comment='最后使用时间')
    
    # 审计字段
    created_by = Column(BigInteger, ForeignKey('users.id'), nullable=False, comment='创建人ID')
    updated_by = Column(BigInteger, ForeignKey('users.id'), comment='更新人ID')
    
    # 关联关系
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'template_name': self.template_name,
            'description': self.description,
            'permissions': self.permissions,
            'data_scope_config': self.data_scope_config,
            'applicable_roles': self.applicable_roles,
            'applicable_projects': self.applicable_projects,
            'is_active': self.is_active,
            'is_system_template': self.is_system_template,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }