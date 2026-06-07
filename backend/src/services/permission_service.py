"""
权限管理服务
"""
import datetime
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text, bindparam
from sqlalchemy.orm import selectinload

from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import RolePermission
from ..models.permission import Permission, UserPermission, PermissionType, PermissionEffect
from ..core.config import get_settings

settings = get_settings()


class PermissionService:
    """权限管理服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_permissions(self, user_id: int) -> Dict[str, Any]:
        """获取用户的所有权限"""
        # 获取用户信息
        user_query = select(User).where(User.id == user_id)
        
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return {"permissions": [], "roles": [], "permission_codes": set()}
        
        all_permissions = set()
        role_permissions = {}

        role_result = await self.db.execute(
            text(
                """
                SELECT r.id, r.code, r.name
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                WHERE ur.user_id = :user_id
                ORDER BY r.sort_order, r.id
                """
            ),
            {"user_id": user_id},
        )
        roles = list(role_result.mappings())
        role_ids = [int(role["id"]) for role in roles]
        for role in roles:
            role_permissions[role["code"]] = []

        if role_ids:
            role_perm_stmt = text(
                """
                SELECT r.code AS role_code, p.code, p.name, p.module, p.action, p.resource, 'ALLOW' AS effect
                FROM role_permissions rp
                JOIN roles r ON r.id = rp.role_id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE rp.role_id IN :role_ids
                """
            ).bindparams(bindparam("role_ids", expanding=True))
            role_perm_result = await self.db.execute(role_perm_stmt, {"role_ids": role_ids})

            for row in role_perm_result.mappings():
                effect = row.get("effect")
                if effect == PermissionEffect.ALLOW.value or effect == PermissionEffect.ALLOW:
                    all_permissions.add(row["code"])
                    role_permissions.setdefault(row["role_code"], []).append({
                        "code": row["code"],
                        "name": row["name"],
                        "module": row["module"],
                        "action": row["action"],
                        "resource": row["resource"],
                        "effect": effect
                    })
        
        # 获取用户直接权限
        direct_perms = []
        direct_result = await self.db.execute(
            text(
                """
                SELECT p.code, p.name, p.module, p.action, p.resource, up.effect
                FROM user_permissions up
                JOIN permissions p ON p.id = up.permission_id
                WHERE up.user_id = :user_id
                """
            ),
            {"user_id": user_id},
        )

        for row in direct_result.mappings():
            effect = row.get("effect")
            if effect == PermissionEffect.ALLOW.value or effect == PermissionEffect.ALLOW:
                all_permissions.add(row["code"])
            else:
                all_permissions.discard(row["code"])  # 拒绝权限
            
            direct_perms.append({
                "code": row["code"],
                "name": row["name"],
                "module": row["module"],
                "action": row["action"],
                "resource": row["resource"],
                "effect": effect
            })
        
        return {
            "user_id": user_id,
            "username": user.username,
            "roles": [{"code": role["code"], "name": role["name"]} for role in roles],
            "role_permissions": role_permissions,
            "direct_permissions": direct_perms,
            "all_permissions": list(all_permissions),
            "permission_codes": all_permissions
        }
    
    async def check_permission(self, user_id: int, permission_code: str) -> bool:
        """检查用户是否有指定权限"""
        user_result = await self.db.execute(select(User.is_superuser).where(User.id == user_id))
        if bool(user_result.scalar()):
            return True

        user_perms = await self.get_user_permissions(user_id)
        return permission_code in user_perms["permission_codes"]

    async def check_project_permission(self, user_id: int, project_id: int, permission: str) -> bool:
        """检查用户是否有项目级权限。"""
        user_result = await self.db.execute(select(User.is_superuser).where(User.id == user_id))
        if bool(user_result.scalar()):
            return True

        project_result = await self.db.execute(
            text(
                """
                SELECT project_manager_id
                FROM projects
                WHERE id = :project_id
                  AND deleted_at IS NULL
                """
            ),
            {"project_id": project_id},
        )
        project = project_result.mappings().first()
        if not project:
            return False

        if int(project["project_manager_id"]) == int(user_id):
            return True

        member_result = await self.db.execute(
            text(
                """
                SELECT role_in_project
                FROM project_members
                WHERE project_id = :project_id
                  AND user_id = :user_id
                  AND status = 'ACTIVE'
                LIMIT 1
                """
            ),
            {"project_id": project_id, "user_id": user_id},
        )
        member = member_result.mappings().first()
        if not member:
            return False

        role = str(member["role_in_project"] or "").upper()
        if role in {"ADMIN", "PROJECT_MANAGER"}:
            return True

        member_allowed_permissions = {
            "meeting:view",
            "project:meeting:view",
            "meeting:create",
            "project:meeting:create",
        }
        return permission in member_allowed_permissions
    
    async def check_permissions(self, user_id: int, permission_codes: List[str]) -> Dict[str, bool]:
        """批量检查用户权限"""
        user_perms = await self.get_user_permissions(user_id)
        user_permission_codes = user_perms["permission_codes"]
        
        return {
            code: code in user_permission_codes 
            for code in permission_codes
        }
    
    async def grant_permission_to_user(
        self, 
        user_id: int, 
        permission_id: int, 
        granted_by: int,
        effect: PermissionEffect = PermissionEffect.ALLOW,
        expires_at: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """直接授予用户权限"""
        # 检查权限是否已存在
        existing_query = select(UserPermission).where(
            and_(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == permission_id
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing_perm = existing_result.scalar_one_or_none()
        
        if existing_perm:
            # 更新现有权限
            existing_perm.effect = effect
            existing_perm.granted_by = granted_by
            existing_perm.granted_at = datetime.datetime.utcnow().isoformat()
            existing_perm.expires_at = expires_at
            existing_perm.reason = reason
        else:
            # 创建新权限
            user_permission = UserPermission(
                user_id=user_id,
                permission_id=permission_id,
                effect=effect,
                granted_by=granted_by,
                granted_at=datetime.datetime.utcnow().isoformat(),
                expires_at=expires_at,
                reason=reason
            )
            self.db.add(user_permission)
        
        await self.db.commit()
        return True
    
    async def revoke_permission_from_user(self, user_id: int, permission_id: int) -> bool:
        """撤销用户权限"""
        query = select(UserPermission).where(
            and_(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == permission_id
            )
        )
        result = await self.db.execute(query)
        user_permission = result.scalar_one_or_none()
        
        if user_permission:
            await self.db.delete(user_permission)
            await self.db.commit()
            return True
        
        return False
    
    async def get_permissions_by_module(self, module: str) -> List[Permission]:
        """获取指定模块的所有权限"""
        query = select(Permission).where(Permission.module == module).order_by(Permission.sort_order)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_permission_tree(self) -> List[Dict[str, Any]]:
        """获取权限树结构"""
        # 获取所有权限
        query = select(Permission).order_by(Permission.level, Permission.sort_order)
        result = await self.db.execute(query)
        permissions = result.scalars().all()
        
        # 构建树结构
        permission_map = {}
        root_permissions = []
        
        for perm in permissions:
            perm_dict = {
                "id": perm.id,
                "code": perm.code,
                "name": perm.name,
                "description": perm.description,
                "module": perm.module,
                "action": perm.action,
                "resource": perm.resource,
                "permission_type": perm.permission_type.value,
                "level": perm.level,
                "parent_id": perm.parent_id,
                "children": []
            }
            permission_map[perm.id] = perm_dict
            
            if perm.parent_id is None:
                root_permissions.append(perm_dict)
            else:
                parent = permission_map.get(perm.parent_id)
                if parent:
                    parent["children"].append(perm_dict)
        
        return root_permissions
    
    async def create_permission(self, permission_data: Dict[str, Any]) -> Permission:
        """创建权限"""
        permission = Permission(
            code=permission_data["code"],
            name=permission_data["name"],
            description=permission_data.get("description"),
            module=permission_data["module"],
            action=permission_data["action"],
            resource=permission_data.get("resource"),
            permission_type=PermissionType(permission_data.get("permission_type", "api")),
            parent_id=permission_data.get("parent_id"),
            level=permission_data.get("level", 1),
            sort_order=permission_data.get("sort_order", 0),
            effect=PermissionEffect(permission_data.get("effect", "allow")),
            conditions=permission_data.get("conditions"),
            is_system_permission=permission_data.get("is_system_permission", False)
        )
        
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        
        return permission
    
    async def update_permission(self, permission_id: int, permission_data: Dict[str, Any]) -> Optional[Permission]:
        """更新权限"""
        query = select(Permission).where(Permission.id == permission_id)
        result = await self.db.execute(query)
        permission = result.scalar_one_or_none()
        
        if not permission:
            return None
        
        # 更新字段
        for key, value in permission_data.items():
            if hasattr(permission, key) and value is not None:
                if key == "permission_type":
                    setattr(permission, key, PermissionType(value))
                elif key == "effect":
                    setattr(permission, key, PermissionEffect(value))
                else:
                    setattr(permission, key, value)
        
        permission.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(permission)
        
        return permission
    
    async def delete_permission(self, permission_id: int) -> bool:
        """删除权限"""
        query = select(Permission).where(Permission.id == permission_id)
        result = await self.db.execute(query)
        permission = result.scalar_one_or_none()
        
        if not permission:
            return False
        
        # 检查是否为系统权限
        if permission.is_system_permission:
            raise ValueError("不能删除系统权限")
        
        # 检查是否有子权限
        children_query = select(func.count(Permission.id)).where(Permission.parent_id == permission_id)
        children_result = await self.db.execute(children_query)
        children_count = children_result.scalar()
        
        if children_count > 0:
            raise ValueError("存在子权限，不能删除")
        
        await self.db.delete(permission)
        await self.db.commit()
        
        return True
    
    async def get_role_permissions(self, role_id: int) -> List[Dict[str, Any]]:
        """获取角色的所有权限"""
        query = select(RolePermission).options(
            selectinload(RolePermission.permission)
        ).where(RolePermission.role_id == role_id)
        
        result = await self.db.execute(query)
        role_permissions = result.scalars().all()
        
        permissions = []
        for rp in role_permissions:
            perm = rp.permission
            permissions.append({
                "id": perm.id,
                "code": perm.code,
                "name": perm.name,
                "module": perm.module,
                "action": perm.action,
                "resource": perm.resource,
                "effect": rp.effect.value,
                "conditions": rp.conditions
            })
        
        return permissions
    
    async def assign_permissions_to_role(
        self, 
        role_id: int, 
        permission_ids: List[int],
        granted_by: int
    ) -> Dict[str, Any]:
        """为角色分配权限"""
        # 删除现有权限
        delete_query = select(RolePermission).where(RolePermission.role_id == role_id)
        delete_result = await self.db.execute(delete_query)
        existing_permissions = delete_result.scalars().all()
        
        for rp in existing_permissions:
            await self.db.delete(rp)
        
        # 添加新权限
        success_count = 0
        failed_permissions = []
        
        for permission_id in permission_ids:
            try:
                role_permission = RolePermission(
                    role_id=role_id,
                    permission_id=permission_id,
                    effect=PermissionEffect.ALLOW,
                    granted_by=granted_by,
                    granted_at=datetime.datetime.utcnow().isoformat()
                )
                self.db.add(role_permission)
                success_count += 1
            except Exception as e:
                failed_permissions.append({
                    "permission_id": permission_id,
                    "error": str(e)
                })
        
        await self.db.commit()
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_permissions),
            "failed_permissions": failed_permissions
        }
    
    async def get_permission_statistics(self) -> Dict[str, Any]:
        """获取权限统计信息"""
        # 总权限数
        total_query = select(func.count(Permission.id))
        total_result = await self.db.execute(total_query)
        total_permissions = total_result.scalar()
        
        # 按模块统计
        module_query = select(
            Permission.module,
            func.count(Permission.id).label("count")
        ).group_by(Permission.module)
        module_result = await self.db.execute(module_query)
        module_stats = {row.module: row.count for row in module_result}
        
        # 按类型统计
        type_query = select(
            Permission.permission_type,
            func.count(Permission.id).label("count")
        ).group_by(Permission.permission_type)
        type_result = await self.db.execute(type_query)
        type_stats = {row.permission_type.value: row.count for row in type_result}
        
        return {
            "total_permissions": total_permissions,
            "module_statistics": module_stats,
            "type_statistics": type_stats
        }
