"""
用户角色管理器 - 基于zentao模式的角色权限控制
实现细粒度的权限管理和基于角色的访问控制(RBAC)
"""
import logging
from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload, joinedload

from ..models.user import User, UserRole, UserStatus
from ..models.role import Role
from ..models.permission import RolePermission
from ..models.permission import Permission, PermissionType, PermissionEffect
from ..models.audit import AuditLog, AuditAction, AuditResult
from ..core.redis import redis_service
# from ..utils.security_utils import SecurityUtils  # Optional dependency

logger = logging.getLogger(__name__)


class UserRoleManager:
    """用户角色管理器 - 基于zentao模式的权限控制"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_prefix = "user_role_manager"
        self.cache_ttl = 3600  # 1小时缓存
    
    async def assign_role_to_user(
        self,
        user_id: int,
        role_id: int,
        assigned_by: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        为用户分配角色 - zentao风格的权限分配
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            assigned_by: 分配者ID
            expires_at: 过期时间
            reason: 分配原因
            
        Returns:
            Tuple[bool, Optional[str]]: 成功标志和错误信息
        """
        try:
            # 验证用户存在且状态正常
            user = await self._get_user_by_id(user_id)
            if not user:
                return False, "用户不存在"
            
            if user.status != UserStatus.ACTIVE:
                return False, f"用户状态异常: {user.status.value}"
            
            # 验证角色存在且激活
            role = await self._get_role_by_id(role_id)
            if not role:
                return False, "角色不存在"
            
            if not role.is_active:
                return False, "角色已禁用"
            
            # 检查是否已分配该角色
            existing_assignment = await self._get_user_role(user_id, role_id)
            if existing_assignment:
                return False, "用户已拥有该角色"
            
            # 检查角色最大用户数限制
            if role.max_users:
                current_user_count = await self._get_role_user_count(role_id)
                if current_user_count >= role.max_users:
                    return False, f"角色用户数已达上限({role.max_users})"
            
            # 创建用户角色关联
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(user_role)
            await self.db.commit()
            
            # 清除用户权限缓存
            await self._clear_user_cache(user_id)
            
            # 记录审计日志
            await self._log_role_assignment(
                user_id=user_id,
                role_id=role_id,
                action=AuditAction.ASSIGN,
                assigned_by=assigned_by,
                reason=reason,
                result=AuditResult.SUCCESS
            )
            
            logger.info(f"成功为用户 {user_id} 分配角色 {role_id}")
            return True, None
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"分配角色失败: {e}")
            return False, f"分配角色失败: {str(e)}"
    
    async def revoke_role_from_user(
        self,
        user_id: int,
        role_id: int,
        revoked_by: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        撤销用户角色
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            revoked_by: 撤销者ID
            reason: 撤销原因
            
        Returns:
            Tuple[bool, Optional[str]]: 成功标志和错误信息
        """
        try:
            # 检查用户角色关联是否存在
            user_role = await self._get_user_role(user_id, role_id)
            if not user_role:
                return False, "用户没有该角色"
            
            # 检查是否为系统角色（某些系统角色不能撤销）
            role = await self._get_role_by_id(role_id)
            if role and role.is_system_role and role.code == "admin":
                # 检查是否为最后一个管理员
                admin_count = await self._get_role_user_count(role_id)
                if admin_count <= 1:
                    return False, "不能撤销最后一个管理员角色"
            
            # 删除用户角色关联
            await self.db.delete(user_role)
            await self.db.commit()
            
            # 清除用户权限缓存
            await self._clear_user_cache(user_id)
            
            # 记录审计日志
            await self._log_role_assignment(
                user_id=user_id,
                role_id=role_id,
                action=AuditAction.REVOKE,
                assigned_by=revoked_by,
                reason=reason,
                result=AuditResult.SUCCESS
            )
            
            logger.info(f"成功撤销用户 {user_id} 的角色 {role_id}")
            return True, None
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"撤销角色失败: {e}")
            return False, f"撤销角色失败: {str(e)}"
    
    async def get_user_roles(self, user_id: int) -> List[Role]:
        """
        获取用户的所有角色
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Role]: 角色列表
        """
        try:
            # 尝试从缓存获取
            cache_key = f"{self.cache_prefix}:user_roles:{user_id}"
            cached_roles = await redis_service.get(cache_key)
            
            if cached_roles:
                # 从缓存中反序列化角色数据
                import json
                role_data = json.loads(cached_roles)
                return [Role(**data) for data in role_data]
            
            # 从数据库查询
            query = (
                select(Role)
                .join(UserRole)
                .where(UserRole.user_id == user_id)
                .where(Role.is_active == True)
                .order_by(Role.priority.desc())
            )
            
            result = await self.db.execute(query)
            roles = list(result.scalars().all())
            
            # 缓存结果
            if roles:
                role_data = [
                    {
                        "id": role.id,
                        "code": role.code,
                        "name": role.name,
                        "description": role.description,
                        "priority": role.priority,
                        "is_system_role": role.is_system_role
                    }
                    for role in roles
                ]
                await redis_service.set(
                    cache_key,
                    json.dumps(role_data),
                    expire=self.cache_ttl
                )
            
            return roles
            
        except Exception as e:
            logger.error(f"获取用户角色失败: {e}")
            return []
    
    async def get_user_permissions(self, user_id: int) -> Set[str]:
        """
        获取用户的所有权限代码 - zentao风格的权限聚合
        
        Args:
            user_id: 用户ID
            
        Returns:
            Set[str]: 权限代码集合
        """
        try:
            # 尝试从缓存获取
            cache_key = f"{self.cache_prefix}:user_permissions:{user_id}"
            cached_permissions = await redis_service.get(cache_key)
            
            if cached_permissions:
                return set(cached_permissions.split(","))
            
            # 从数据库查询用户的所有权限
            query = (
                select(Permission.code)
                .join(RolePermission)
                .join(Role)
                .join(UserRole)
                .where(UserRole.user_id == user_id)
                .where(Role.is_active == True)
                .where(Permission.is_active == True)
                .where(RolePermission.effect == PermissionEffect.ALLOW)
                .distinct()
            )
            
            result = await self.db.execute(query)
            permissions = {row[0] for row in result.all()}
            
            # 处理权限继承和层级关系
            permissions = await self._process_permission_inheritance(permissions)
            
            # 缓存结果
            if permissions:
                await redis_service.set(
                    cache_key,
                    ",".join(permissions),
                    expire=self.cache_ttl
                )
            
            return permissions
            
        except Exception as e:
            logger.error(f"获取用户权限失败: {e}")
            return set()
    
    async def check_user_permission(
        self,
        user_id: int,
        permission_code: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """
        检查用户是否具有特定权限 - zentao风格的权限检查
        
        Args:
            user_id: 用户ID
            permission_code: 权限代码
            resource_id: 资源ID（用于数据权限控制）
            
        Returns:
            bool: 是否具有权限
        """
        try:
            # 超级管理员拥有所有权限
            if await self._is_super_admin(user_id):
                return True
            
            # 获取用户权限
            user_permissions = await self.get_user_permissions(user_id)
            
            # 基础权限检查
            if permission_code not in user_permissions:
                return False
            
            # 数据权限检查（如果指定了资源ID）
            if resource_id:
                return await self._check_data_permission(user_id, permission_code, resource_id)
            
            return True
            
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return False
    
    async def check_user_role(self, user_id: int, role_code: str) -> bool:
        """
        检查用户是否具有特定角色
        
        Args:
            user_id: 用户ID
            role_code: 角色代码
            
        Returns:
            bool: 是否具有角色
        """
        try:
            user_roles = await self.get_user_roles(user_id)
            return any(role.code == role_code for role in user_roles)
            
        except Exception as e:
            logger.error(f"角色检查失败: {e}")
            return False
    
    async def get_user_data_scope(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户的数据权限范围 - zentao风格的数据权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 数据权限范围配置
        """
        try:
            # 获取用户角色
            user_roles = await self.get_user_roles(user_id)
            
            # 合并所有角色的数据权限范围
            data_scope = {
                "scope_type": "self",  # 默认只能访问自己的数据
                "scope_value": [],
                "departments": [],
                "projects": [],
                "custom_rules": []
            }
            
            for role in user_roles:
                if role.data_scope == "all":
                    # 如果有全部数据权限，直接返回
                    return {
                        "scope_type": "all",
                        "scope_value": ["*"],
                        "departments": ["*"],
                        "projects": ["*"],
                        "custom_rules": []
                    }
                elif role.data_scope == "dept":
                    # 部门数据权限
                    data_scope["scope_type"] = "dept"
                    if role.data_scope_config:
                        data_scope["departments"].extend(
                            role.data_scope_config.get("departments", [])
                        )
                elif role.data_scope == "custom":
                    # 自定义数据权限
                    if role.data_scope_config:
                        data_scope["custom_rules"].extend(
                            role.data_scope_config.get("rules", [])
                        )
            
            return data_scope
            
        except Exception as e:
            logger.error(f"获取数据权限范围失败: {e}")
            return {"scope_type": "self", "scope_value": [], "departments": [], "projects": [], "custom_rules": []}
    
    async def batch_assign_roles(
        self,
        user_ids: List[int],
        role_ids: List[int],
        assigned_by: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量分配角色
        
        Args:
            user_ids: 用户ID列表
            role_ids: 角色ID列表
            assigned_by: 分配者ID
            reason: 分配原因
            
        Returns:
            Dict[str, Any]: 批量操作结果
        """
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        try:
            for user_id in user_ids:
                for role_id in role_ids:
                    success, error = await self.assign_role_to_user(
                        user_id=user_id,
                        role_id=role_id,
                        assigned_by=assigned_by,
                        reason=reason
                    )
                    
                    if success:
                        results["success_count"] += 1
                    else:
                        results["failed_count"] += 1
                        results["errors"].append({
                            "user_id": user_id,
                            "role_id": role_id,
                            "error": error
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"批量分配角色失败: {e}")
            results["errors"].append({"error": f"批量操作失败: {str(e)}"})
            return results
    
    async def get_role_hierarchy(self, role_id: int) -> Dict[str, Any]:
        """
        获取角色层级关系 - zentao风格的角色继承
        
        Args:
            role_id: 角色ID
            
        Returns:
            Dict[str, Any]: 角色层级信息
        """
        try:
            role = await self._get_role_by_id(role_id)
            if not role:
                return {}
            
            # 获取父角色链
            parent_chain = []
            current_role = role
            
            while current_role.parent_id:
                parent_role = await self._get_role_by_id(current_role.parent_id)
                if not parent_role:
                    break
                parent_chain.append({
                    "id": parent_role.id,
                    "code": parent_role.code,
                    "name": parent_role.name,
                    "level": parent_role.level
                })
                current_role = parent_role
            
            # 获取子角色
            child_roles = await self._get_child_roles(role_id)
            
            return {
                "role": {
                    "id": role.id,
                    "code": role.code,
                    "name": role.name,
                    "level": role.level,
                    "path": role.path
                },
                "parent_chain": parent_chain,
                "child_roles": [
                    {
                        "id": child.id,
                        "code": child.code,
                        "name": child.name,
                        "level": child.level
                    }
                    for child in child_roles
                ]
            }
            
        except Exception as e:
            logger.error(f"获取角色层级失败: {e}")
            return {}
    
    # 私有方法
    async def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """获取用户"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_role_by_id(self, role_id: int) -> Optional[Role]:
        """获取角色"""
        query = select(Role).where(Role.id == role_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_user_role(self, user_id: int, role_id: int) -> Optional[UserRole]:
        """获取用户角色关联"""
        query = select(UserRole).where(
            and_(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_role_user_count(self, role_id: int) -> int:
        """获取角色用户数量"""
        query = select(func.count(UserRole.id)).where(UserRole.role_id == role_id)
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def _get_child_roles(self, role_id: int) -> List[Role]:
        """获取子角色"""
        query = select(Role).where(Role.parent_id == role_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def _is_super_admin(self, user_id: int) -> bool:
        """检查是否为超级管理员"""
        user = await self._get_user_by_id(user_id)
        return user and user.is_superuser
    
    async def _process_permission_inheritance(self, permissions: Set[str]) -> Set[str]:
        """处理权限继承关系"""
        # 这里可以实现权限的层级继承逻辑
        # 例如：拥有 user:edit 权限自动拥有 user:view 权限
        inherited_permissions = set(permissions)
        
        # 权限继承规则
        inheritance_rules = {
            "user:delete": ["user:edit", "user:view"],
            "user:edit": ["user:view"],
            "project:delete": ["project:edit", "project:view"],
            "project:edit": ["project:view"],
            "requirement:delete": ["requirement:edit", "requirement:view"],
            "requirement:edit": ["requirement:view"],
            "test:delete": ["test:edit", "test:view"],
            "test:edit": ["test:view"],
        }
        
        for permission in permissions:
            if permission in inheritance_rules:
                inherited_permissions.update(inheritance_rules[permission])
        
        return inherited_permissions
    
    async def _check_data_permission(
        self,
        user_id: int,
        permission_code: str,
        resource_id: str
    ) -> bool:
        """检查数据权限"""
        try:
            # 获取用户数据权限范围
            data_scope = await self.get_user_data_scope(user_id)
            
            # 全部数据权限
            if data_scope["scope_type"] == "all":
                return True
            
            # 自己的数据权限
            if data_scope["scope_type"] == "self":
                # 这里需要根据具体业务逻辑判断资源是否属于用户
                return await self._is_user_resource(user_id, resource_id)
            
            # 部门数据权限
            if data_scope["scope_type"] == "dept":
                return await self._is_dept_resource(user_id, resource_id, data_scope["departments"])
            
            # 自定义数据权限
            if data_scope["custom_rules"]:
                return await self._check_custom_data_rules(user_id, resource_id, data_scope["custom_rules"])
            
            return False
            
        except Exception as e:
            logger.error(f"数据权限检查失败: {e}")
            return False
    
    async def _is_user_resource(self, user_id: int, resource_id: str) -> bool:
        """检查资源是否属于用户"""
        # 这里需要根据具体的资源类型和业务逻辑实现
        # 例如：检查项目是否由该用户创建或参与
        return True  # 简化实现
    
    async def _is_dept_resource(self, user_id: int, resource_id: str, departments: List[str]) -> bool:
        """检查资源是否属于用户部门"""
        # 这里需要根据具体的部门和资源关系实现
        return True  # 简化实现
    
    async def _check_custom_data_rules(self, user_id: int, resource_id: str, rules: List[Dict]) -> bool:
        """检查自定义数据权限规则"""
        # 这里需要根据自定义规则实现复杂的数据权限逻辑
        return True  # 简化实现
    
    async def _clear_user_cache(self, user_id: int) -> None:
        """清除用户相关缓存"""
        try:
            cache_keys = [
                f"{self.cache_prefix}:user_roles:{user_id}",
                f"{self.cache_prefix}:user_permissions:{user_id}",
                f"user_permissions:{user_id}"  # 兼容旧的缓存键
            ]
            
            for key in cache_keys:
                await redis_service.delete(key)
                
        except Exception as e:
            logger.error(f"清除用户缓存失败: {e}")
    
    async def _log_role_assignment(
        self,
        user_id: int,
        role_id: int,
        action: AuditAction,
        assigned_by: Optional[int] = None,
        reason: Optional[str] = None,
        result: AuditResult = AuditResult.SUCCESS
    ) -> None:
        """记录角色分配审计日志"""
        try:
            # 获取角色信息用于日志
            role = await self._get_role_by_id(role_id)
            role_name = role.name if role else f"Role-{role_id}"
            
            audit_log = AuditLog(
                user_id=assigned_by,
                action=action,
                resource_type="user_role",
                resource_id=f"{user_id}_{role_id}",
                result=result,
                new_values={
                    "user_id": user_id,
                    "role_id": role_id,
                    "role_name": role_name,
                    "reason": reason
                },
                created_at=datetime.utcnow()
            )
            
            self.db.add(audit_log)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")