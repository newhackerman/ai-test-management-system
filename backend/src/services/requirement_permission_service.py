"""
需求管理权限控制服务

本模块实现需求管理模块的权限控制服务，包括：
- 基于角色的访问控制(RBAC)
- 需求级别权限管理
- 操作审计日志
- 权限检查和验证
"""
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
from fastapi import Request

from ..models.user import User, UserRole
from ..models.role import Role
from ..models.requirement import Requirement, RequirementStatus
from ..models.project import Project
from ..models.requirement_permission import (
    RequirementRolePermission, RequirementUserPermission, RequirementResourcePermission,
    RequirementAuditLog, RequirementPermissionTemplate,
    RequirementPermissionType, RequirementDataScope, RequirementPermissionEffect,
    RequirementAuditAction, RequirementAuditResult
)
from ..core.exceptions import PermissionDeniedError, UnauthorizedError


class RequirementPermissionService:
    """需求权限管理服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_permission(
        self, 
        user_id: int, 
        permission_type: RequirementPermissionType,
        requirement_id: Optional[int] = None,
        project_id: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """检查用户是否有指定权限"""
        try:
            # 获取用户权限
            user_permissions = await self.get_user_permissions(user_id)
            
            # 检查权限
            has_permission = await self._evaluate_permission(
                user_permissions, permission_type, requirement_id, project_id, additional_context
            )
            
            return has_permission
            
        except Exception as e:
            # 记录权限检查失败
            await self._log_permission_check(
                user_id, permission_type, requirement_id, project_id, False, str(e)
            )
            return False
    
    async def check_permissions(
        self, 
        user_id: int, 
        permission_types: List[RequirementPermissionType],
        requirement_id: Optional[int] = None,
        project_id: Optional[int] = None
    ) -> Dict[RequirementPermissionType, bool]:
        """批量检查用户权限"""
        results = {}
        user_permissions = await self.get_user_permissions(user_id)
        
        for permission_type in permission_types:
            try:
                has_permission = await self._evaluate_permission(
                    user_permissions, permission_type, requirement_id, project_id
                )
                results[permission_type] = has_permission
            except Exception:
                results[permission_type] = False
        
        return results
    
    async def require_permission(
        self,
        user_id: int,
        permission_type: RequirementPermissionType,
        requirement_id: Optional[int] = None,
        project_id: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """要求用户具有指定权限，否则抛出异常"""
        has_permission = await self.check_permission(
            user_id, permission_type, requirement_id, project_id, additional_context
        )
        
        if not has_permission:
            raise PermissionDeniedError(
                f"用户 {user_id} 没有权限 {permission_type.value}",
                error_code="PERMISSION_DENIED",
                details={
                    "user_id": user_id,
                    "permission_type": permission_type.value,
                    "requirement_id": requirement_id,
                    "project_id": project_id
                }
            )
    
    async def get_user_permissions(self, user_id: int) -> Dict[str, Any]:
        """获取用户的所有需求权限"""
        # 获取用户信息和角色
        user_query = select(User).options(
            selectinload(User.roles).selectinload(UserRole.role)
        ).where(User.id == user_id)
        
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return {"permissions": [], "roles": [], "permission_codes": set()}
        
        # 收集角色权限
        role_permissions = {}
        all_permissions = set()
        
        for user_role in user.roles:
            role = user_role.role
            role_permissions[role.code] = []
            
            # 获取角色的需求权限
            role_perm_query = select(RequirementRolePermission).where(
                RequirementRolePermission.role_id == role.id
            )
            role_perm_result = await self.db.execute(role_perm_query)
            role_perms = role_perm_result.scalars().all()
            
            for role_perm in role_perms:
                if self._is_permission_effective(role_perm):
                    if role_perm.effect == RequirementPermissionEffect.ALLOW:
                        all_permissions.add(role_perm.permission_type)
                        role_permissions[role.code].append({
                            "permission_type": role_perm.permission_type.value,
                            "data_scope": role_perm.data_scope.value,
                            "project_ids": role_perm.project_ids,
                            "allowed_statuses": role_perm.allowed_statuses,
                            "effect": role_perm.effect.value
                        })
        
        # 获取用户直接权限
        direct_perm_query = select(RequirementUserPermission).where(
            RequirementUserPermission.user_id == user_id
        )
        direct_perm_result = await self.db.execute(direct_perm_query)
        direct_perms = direct_perm_result.scalars().all()
        
        direct_permissions = []
        for user_perm in direct_perms:
            if self._is_permission_effective(user_perm):
                if user_perm.effect == RequirementPermissionEffect.ALLOW:
                    all_permissions.add(user_perm.permission_type)
                else:
                    all_permissions.discard(user_perm.permission_type)
                
                direct_permissions.append({
                    "permission_type": user_perm.permission_type.value,
                    "data_scope": user_perm.data_scope.value,
                    "project_ids": user_perm.project_ids,
                    "allowed_statuses": user_perm.allowed_statuses,
                    "effect": user_perm.effect.value
                })
        
        # 获取资源级权限
        resource_perm_query = select(RequirementResourcePermission).where(
            RequirementResourcePermission.user_id == user_id
        )
        resource_perm_result = await self.db.execute(resource_perm_query)
        resource_perms = resource_perm_result.scalars().all()
        
        resource_permissions = {}
        for res_perm in resource_perms:
            if self._is_permission_effective(res_perm):
                req_id = res_perm.requirement_id
                if req_id not in resource_permissions:
                    resource_permissions[req_id] = []
                
                resource_permissions[req_id].append({
                    "permission_type": res_perm.permission_type.value,
                    "effect": res_perm.effect.value
                })
        
        return {
            "user_id": user_id,
            "username": user.username,
            "roles": [{"code": ur.role.code, "name": ur.role.name} for ur in user.roles],
            "role_permissions": role_permissions,
            "direct_permissions": direct_permissions,
            "resource_permissions": resource_permissions,
            "all_permissions": list(all_permissions),
            "permission_codes": all_permissions
        }
    
    async def grant_role_permission(
        self,
        role_id: int,
        permission_type: RequirementPermissionType,
        granted_by: int,
        data_scope: RequirementDataScope = RequirementDataScope.ALL,
        project_ids: Optional[List[int]] = None,
        allowed_statuses: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None
    ) -> RequirementRolePermission:
        """为角色授予需求权限"""
        # 检查是否已存在相同权限
        existing_query = select(RequirementRolePermission).where(
            and_(
                RequirementRolePermission.role_id == role_id,
                RequirementRolePermission.permission_type == permission_type
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing_perm = existing_result.scalar_one_or_none()
        
        if existing_perm:
            # 更新现有权限
            existing_perm.data_scope = data_scope
            existing_perm.project_ids = project_ids
            existing_perm.allowed_statuses = allowed_statuses
            existing_perm.conditions = conditions
            existing_perm.effective_from = effective_from
            existing_perm.effective_to = effective_to
            existing_perm.granted_by = granted_by
            existing_perm.granted_at = datetime.utcnow()
            permission = existing_perm
        else:
            # 创建新权限
            permission = RequirementRolePermission(
                role_id=role_id,
                permission_type=permission_type,
                data_scope=data_scope,
                project_ids=project_ids,
                allowed_statuses=allowed_statuses,
                conditions=conditions,
                effective_from=effective_from,
                effective_to=effective_to,
                granted_by=granted_by
            )
            self.db.add(permission)
        
        await self.db.commit()
        await self.db.refresh(permission)
        
        # 记录审计日志
        await self.log_audit(
            user_id=granted_by,
            action=RequirementAuditAction.GRANT_PERMISSION,
            result=RequirementAuditResult.SUCCESS,
            resource_type="role_permission",
            resource_id=permission.id,
            operation_details={
                "role_id": role_id,
                "permission_type": permission_type.value,
                "data_scope": data_scope.value
            }
        )
        
        return permission
    
    async def grant_user_permission(
        self,
        user_id: int,
        permission_type: RequirementPermissionType,
        granted_by: int,
        data_scope: RequirementDataScope = RequirementDataScope.ALL,
        project_ids: Optional[List[int]] = None,
        allowed_statuses: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None,
        reason: Optional[str] = None
    ) -> RequirementUserPermission:
        """为用户直接授予需求权限"""
        # 检查是否已存在相同权限
        existing_query = select(RequirementUserPermission).where(
            and_(
                RequirementUserPermission.user_id == user_id,
                RequirementUserPermission.permission_type == permission_type
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing_perm = existing_result.scalar_one_or_none()
        
        if existing_perm:
            # 更新现有权限
            existing_perm.data_scope = data_scope
            existing_perm.project_ids = project_ids
            existing_perm.allowed_statuses = allowed_statuses
            existing_perm.conditions = conditions
            existing_perm.effective_from = effective_from
            existing_perm.effective_to = effective_to
            existing_perm.granted_by = granted_by
            existing_perm.granted_at = datetime.utcnow()
            existing_perm.reason = reason
            permission = existing_perm
        else:
            # 创建新权限
            permission = RequirementUserPermission(
                user_id=user_id,
                permission_type=permission_type,
                data_scope=data_scope,
                project_ids=project_ids,
                allowed_statuses=allowed_statuses,
                conditions=conditions,
                effective_from=effective_from,
                effective_to=effective_to,
                granted_by=granted_by,
                reason=reason
            )
            self.db.add(permission)
        
        await self.db.commit()
        await self.db.refresh(permission)
        
        # 记录审计日志
        await self.log_audit(
            user_id=granted_by,
            action=RequirementAuditAction.GRANT_PERMISSION,
            result=RequirementAuditResult.SUCCESS,
            resource_type="user_permission",
            resource_id=permission.id,
            operation_details={
                "target_user_id": user_id,
                "permission_type": permission_type.value,
                "data_scope": data_scope.value,
                "reason": reason
            }
        )
        
        return permission
    
    async def revoke_role_permission(
        self, 
        role_id: int, 
        permission_type: RequirementPermissionType,
        revoked_by: int
    ) -> bool:
        """撤销角色的需求权限"""
        query = select(RequirementRolePermission).where(
            and_(
                RequirementRolePermission.role_id == role_id,
                RequirementRolePermission.permission_type == permission_type
            )
        )
        result = await self.db.execute(query)
        permission = result.scalar_one_or_none()
        
        if permission:
            await self.db.delete(permission)
            await self.db.commit()
            
            # 记录审计日志
            await self.log_audit(
                user_id=revoked_by,
                action=RequirementAuditAction.REVOKE_PERMISSION,
                result=RequirementAuditResult.SUCCESS,
                resource_type="role_permission",
                resource_id=permission.id,
                operation_details={
                    "role_id": role_id,
                    "permission_type": permission_type.value
                }
            )
            
            return True
        
        return False
    
    async def revoke_user_permission(
        self, 
        user_id: int, 
        permission_type: RequirementPermissionType,
        revoked_by: int
    ) -> bool:
        """撤销用户的直接需求权限"""
        query = select(RequirementUserPermission).where(
            and_(
                RequirementUserPermission.user_id == user_id,
                RequirementUserPermission.permission_type == permission_type
            )
        )
        result = await self.db.execute(query)
        permission = result.scalar_one_or_none()
        
        if permission:
            await self.db.delete(permission)
            await self.db.commit()
            
            # 记录审计日志
            await self.log_audit(
                user_id=revoked_by,
                action=RequirementAuditAction.REVOKE_PERMISSION,
                result=RequirementAuditResult.SUCCESS,
                resource_type="user_permission",
                resource_id=permission.id,
                operation_details={
                    "target_user_id": user_id,
                    "permission_type": permission_type.value
                }
            )
            
            return True
        
        return False
    
    async def get_accessible_requirements(
        self, 
        user_id: int, 
        project_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """获取用户可访问的需求ID列表"""
        user_permissions = await self.get_user_permissions(user_id)
        
        # 检查是否有查看权限
        if RequirementPermissionType.VIEW not in user_permissions["permission_codes"]:
            return []
        
        # 构建查询条件
        query_conditions = []
        
        # 根据数据范围过滤
        data_scopes = self._extract_data_scopes(user_permissions, RequirementPermissionType.VIEW)
        
        for scope_info in data_scopes:
            scope = scope_info["data_scope"]
            project_ids = scope_info.get("project_ids")
            
            if scope == RequirementDataScope.ALL:
                # 所有需求
                if project_ids:
                    query_conditions.append(Requirement.project_id.in_(project_ids))
                else:
                    query_conditions.append(text("1=1"))  # 无限制
            elif scope == RequirementDataScope.PROJECT:
                # 项目范围
                if project_ids:
                    query_conditions.append(Requirement.project_id.in_(project_ids))
                elif project_id:
                    query_conditions.append(Requirement.project_id == project_id)
            elif scope == RequirementDataScope.ASSIGNED:
                # 分配给自己的
                query_conditions.append(Requirement.assignee_id == user_id)
            elif scope == RequirementDataScope.CREATED:
                # 自己创建的
                query_conditions.append(Requirement.creator_id == user_id)
        
        if not query_conditions:
            return []
        
        # 执行查询
        query = select(Requirement.id).where(or_(*query_conditions))
        
        # 添加额外过滤条件
        if project_id:
            query = query.where(Requirement.project_id == project_id)
        
        if filters:
            if "status" in filters:
                query = query.where(Requirement.status == filters["status"])
            if "priority" in filters:
                query = query.where(Requirement.priority == filters["priority"])
        
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]
    
    async def log_audit(
        self,
        user_id: Optional[int],
        action: RequirementAuditAction,
        result: RequirementAuditResult,
        resource_type: str,
        resource_id: Optional[int] = None,
        requirement_id: Optional[int] = None,
        project_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        operation_details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        request: Optional[Request] = None,
        operation_duration: Optional[int] = None
    ) -> RequirementAuditLog:
        """记录需求操作审计日志"""
        # 提取请求信息
        ip_address = None
        user_agent = None
        session_id = None
        
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            session_id = request.headers.get("x-session-id")
        
        audit_log = RequirementAuditLog(
            user_id=user_id,
            action=action,
            result=result,
            resource_type=resource_type,
            resource_id=resource_id,
            requirement_id=requirement_id,
            project_id=project_id,
            old_values=old_values,
            new_values=new_values,
            operation_details=operation_details,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            error_message=error_message,
            error_code=error_code,
            operation_duration=operation_duration,
            permission_checked=True
        )
        
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        
        return audit_log
    
    def _is_permission_effective(self, permission) -> bool:
        """检查权限是否在有效期内"""
        now = datetime.utcnow()
        
        if hasattr(permission, 'effective_from') and permission.effective_from:
            if now < permission.effective_from:
                return False
        
        if hasattr(permission, 'effective_to') and permission.effective_to:
            if now > permission.effective_to:
                return False
        
        return True
    
    async def _evaluate_permission(
        self,
        user_permissions: Dict[str, Any],
        permission_type: RequirementPermissionType,
        requirement_id: Optional[int] = None,
        project_id: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """评估用户是否有指定权限"""
        # 检查基本权限
        if permission_type not in user_permissions["permission_codes"]:
            return False
        
        # 检查资源级权限
        if requirement_id and requirement_id in user_permissions["resource_permissions"]:
            resource_perms = user_permissions["resource_permissions"][requirement_id]
            for perm in resource_perms:
                if perm["permission_type"] == permission_type.value:
                    return perm["effect"] == RequirementPermissionEffect.ALLOW.value
        
        # 检查数据范围权限
        data_scopes = self._extract_data_scopes(user_permissions, permission_type)
        
        if requirement_id:
            # 获取需求信息进行权限检查
            requirement = await self._get_requirement_for_permission_check(requirement_id)
            if not requirement:
                return False
            
            return await self._check_requirement_access(requirement, data_scopes, user_permissions["user_id"])
        
        # 如果没有具体资源，检查是否有任何相关权限
        return len(data_scopes) > 0
    
    def _extract_data_scopes(
        self, 
        user_permissions: Dict[str, Any], 
        permission_type: RequirementPermissionType
    ) -> List[Dict[str, Any]]:
        """提取用户指定权限的数据范围"""
        data_scopes = []
        
        # 从角色权限中提取
        for role_perms in user_permissions["role_permissions"].values():
            for perm in role_perms:
                if perm["permission_type"] == permission_type.value and perm["effect"] == "ALLOW":
                    data_scopes.append(perm)
        
        # 从直接权限中提取
        for perm in user_permissions["direct_permissions"]:
            if perm["permission_type"] == permission_type.value and perm["effect"] == "ALLOW":
                data_scopes.append(perm)
        
        return data_scopes
    
    async def _get_requirement_for_permission_check(self, requirement_id: int) -> Optional[Requirement]:
        """获取需求信息用于权限检查"""
        query = select(Requirement).where(Requirement.id == requirement_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _check_requirement_access(
        self, 
        requirement: Requirement, 
        data_scopes: List[Dict[str, Any]], 
        user_id: int
    ) -> bool:
        """检查用户是否可以访问指定需求"""
        for scope_info in data_scopes:
            scope = scope_info["data_scope"]
            project_ids = scope_info.get("project_ids")
            allowed_statuses = scope_info.get("allowed_statuses")
            
            # 检查项目范围
            if project_ids and requirement.project_id not in project_ids:
                continue
            
            # 检查状态限制
            if allowed_statuses and requirement.status.value not in allowed_statuses:
                continue
            
            # 检查数据范围
            if scope == RequirementDataScope.ALL.value:
                return True
            elif scope == RequirementDataScope.PROJECT.value:
                return True  # 项目范围已在上面检查
            elif scope == RequirementDataScope.ASSIGNED.value:
                if requirement.assignee_id == user_id:
                    return True
            elif scope == RequirementDataScope.CREATED.value:
                if requirement.creator_id == user_id:
                    return True
        
        return False
    
    async def _log_permission_check(
        self,
        user_id: int,
        permission_type: RequirementPermissionType,
        requirement_id: Optional[int],
        project_id: Optional[int],
        result: bool,
        error_message: Optional[str] = None
    ):
        """记录权限检查日志"""
        try:
            audit_result = RequirementAuditResult.SUCCESS if result else RequirementAuditResult.UNAUTHORIZED
            
            await self.log_audit(
                user_id=user_id,
                action=RequirementAuditAction.VIEW_REQUIREMENT,  # 使用通用的查看动作
                result=audit_result,
                resource_type="permission_check",
                requirement_id=requirement_id,
                project_id=project_id,
                operation_details={
                    "permission_type": permission_type.value,
                    "check_result": result
                },
                error_message=error_message
            )
        except Exception:
            # 忽略审计日志记录失败，避免影响主要业务逻辑
            pass


class RequirementPermissionDecorator:
    """需求权限装饰器类"""
    
    def __init__(self, permission_service: RequirementPermissionService):
        self.permission_service = permission_service
    
    def require_permission(
        self,
        permission_type: RequirementPermissionType,
        requirement_id_param: Optional[str] = None,
        project_id_param: Optional[str] = None
    ):
        """权限检查装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 提取用户ID（假设第一个参数是用户ID或包含用户信息的对象）
                user_id = None
                requirement_id = None
                project_id = None
                
                # 从参数中提取用户ID
                if args and hasattr(args[0], 'user_id'):
                    user_id = args[0].user_id
                elif 'user_id' in kwargs:
                    user_id = kwargs['user_id']
                elif 'current_user' in kwargs and hasattr(kwargs['current_user'], 'id'):
                    user_id = kwargs['current_user'].id
                
                # 从参数中提取需求ID
                if requirement_id_param and requirement_id_param in kwargs:
                    requirement_id = kwargs[requirement_id_param]
                
                # 从参数中提取项目ID
                if project_id_param and project_id_param in kwargs:
                    project_id = kwargs[project_id_param]
                
                if user_id:
                    await self.permission_service.require_permission(
                        user_id, permission_type, requirement_id, project_id
                    )
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator