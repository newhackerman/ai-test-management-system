"""
角色管理服务
"""
import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload

from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import RolePermission
from ..models.permission import Permission
from ..core.config import get_settings

settings = get_settings()


class RoleService:
    """角色管理服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_roles_paginated(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        parent_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """分页获取角色列表"""
        query = select(Role).options(
            selectinload(Role.permissions),
            selectinload(Role.users)
        )
        
        # 添加搜索条件
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Role.name.ilike(search_pattern),
                    Role.code.ilike(search_pattern),
                    Role.description.ilike(search_pattern)
                )
            )
        
        # 添加状态筛选
        if is_active is not None:
            query = query.where(Role.is_active == is_active)
        
        # 添加父角色筛选
        if parent_id is not None:
            query = query.where(Role.parent_id == parent_id)
        
        # 添加排序
        if hasattr(Role, sort_by):
            order_column = getattr(Role, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        
        # 获取总数
        count_query = select(func.count(Role.id))
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                or_(
                    Role.name.ilike(search_pattern),
                    Role.code.ilike(search_pattern),
                    Role.description.ilike(search_pattern)
                )
            )
        if is_active is not None:
            count_query = count_query.where(Role.is_active == is_active)
        if parent_id is not None:
            count_query = count_query.where(Role.parent_id == parent_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 添加分页
        query = query.offset(skip).limit(limit)
        
        # 执行查询
        result = await self.db.execute(query)
        roles = result.scalars().all()
        
        return {
            "roles": roles,
            "total": total
        }
    
    async def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """根据ID获取角色"""
        query = select(Role).options(
            selectinload(Role.permissions).selectinload(RolePermission.permission),
            selectinload(Role.users).selectinload(UserRole.user),
            selectinload(Role.parent),
            selectinload(Role.children)
        ).where(Role.id == role_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_role_by_code(self, code: str) -> Optional[Role]:
        """根据代码获取角色"""
        query = select(Role).where(Role.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_role(self, role_data: Dict[str, Any]) -> Role:
        """创建角色"""
        # 检查角色代码唯一性
        existing_role = await self.get_role_by_code(role_data["code"])
        if existing_role:
            raise ValueError("角色代码已存在")
        
        # 计算层级和路径
        level = 1
        path = role_data["code"]
        
        if role_data.get("parent_id"):
            parent_role = await self.get_role_by_id(role_data["parent_id"])
            if parent_role:
                level = parent_role.level + 1
                path = f"{parent_role.path}/{role_data['code']}"
        
        role = Role(
            code=role_data["code"],
            name=role_data["name"],
            description=role_data.get("description"),
            color=role_data.get("color"),
            icon=role_data.get("icon"),
            parent_id=role_data.get("parent_id"),
            level=level,
            path=path,
            sort_order=role_data.get("sort_order", 0),
            is_system_role=role_data.get("is_system_role", False),
            priority=role_data.get("priority", 0),
            max_users=role_data.get("max_users"),
            inherit_parent_permissions=role_data.get("inherit_parent_permissions", True),
            permission_policy=role_data.get("permission_policy", "merge"),
            data_scope=role_data.get("data_scope", "all"),
            data_scope_config=role_data.get("data_scope_config")
        )
        
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        
        return role
    
    async def update_role(self, role_id: int, role_data: Dict[str, Any]) -> Optional[Role]:
        """更新角色"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return None
        
        # 检查是否为系统角色
        if role.is_system_role and not role_data.get("allow_system_role_update", False):
            raise ValueError("不能修改系统角色")
        
        # 检查角色代码唯一性
        if "code" in role_data and role_data["code"] != role.code:
            existing_role = await self.get_role_by_code(role_data["code"])
            if existing_role:
                raise ValueError("角色代码已存在")
        
        # 更新字段
        for key, value in role_data.items():
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)
        
        role.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(role)
        
        return role
    
    async def delete_role(self, role_id: int) -> bool:
        """删除角色"""
        role = await self.get_role_by_id(role_id)
        if not role:
            return False
        
        # 检查是否为系统角色
        if role.is_system_role:
            raise ValueError("不能删除系统角色")
        
        # 检查是否有用户使用该角色
        if role.user_count > 0:
            raise ValueError("该角色下还有用户，不能删除")
        
        # 检查是否有子角色
        children_query = select(func.count(Role.id)).where(Role.parent_id == role_id)
        children_result = await self.db.execute(children_query)
        children_count = children_result.scalar()
        
        if children_count > 0:
            raise ValueError("存在子角色，不能删除")
        
        await self.db.delete(role)
        await self.db.commit()
        
        return True
    
    async def assign_users_to_role(self, role_id: int, user_ids: List[int]) -> Dict[str, Any]:
        """为角色分配用户"""
        role = await self.get_role_by_id(role_id)
        if not role:
            raise ValueError("角色不存在")
        
        # 检查用户数量限制
        if role.max_users and len(user_ids) > role.max_users:
            raise ValueError(f"超过角色最大用户数限制: {role.max_users}")
        
        success_count = 0
        failed_users = []
        
        for user_id in user_ids:
            try:
                # 检查用户是否已有该角色
                existing_query = select(UserRole).where(
                    and_(UserRole.user_id == user_id, UserRole.role_id == role_id)
                )
                existing_result = await self.db.execute(existing_query)
                existing_user_role = existing_result.scalar_one_or_none()
                
                if not existing_user_role:
                    user_role = UserRole(user_id=user_id, role_id=role_id)
                    self.db.add(user_role)
                    success_count += 1
                
            except Exception as e:
                failed_users.append({
                    "user_id": user_id,
                    "error": str(e)
                })
        
        await self.db.commit()
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_users),
            "failed_users": failed_users
        }
    
    async def remove_users_from_role(self, role_id: int, user_ids: List[int]) -> Dict[str, Any]:
        """从角色中移除用户"""
        success_count = 0
        failed_users = []
        
        for user_id in user_ids:
            try:
                query = select(UserRole).where(
                    and_(UserRole.user_id == user_id, UserRole.role_id == role_id)
                )
                result = await self.db.execute(query)
                user_role = result.scalar_one_or_none()
                
                if user_role:
                    await self.db.delete(user_role)
                    success_count += 1
                
            except Exception as e:
                failed_users.append({
                    "user_id": user_id,
                    "error": str(e)
                })
        
        await self.db.commit()
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_users),
            "failed_users": failed_users
        }
    
    async def get_role_tree(self) -> List[Dict[str, Any]]:
        """获取角色树结构"""
        query = select(Role).options(
            selectinload(Role.users),
            selectinload(Role.permissions)
        ).order_by(Role.level, Role.sort_order)
        
        result = await self.db.execute(query)
        roles = result.scalars().all()
        
        # 构建树结构
        role_map = {}
        root_roles = []
        
        for role in roles:
            role_dict = {
                "id": role.id,
                "code": role.code,
                "name": role.name,
                "description": role.description,
                "color": role.color,
                "icon": role.icon,
                "level": role.level,
                "parent_id": role.parent_id,
                "is_active": role.is_active,
                "is_system_role": role.is_system_role,
                "user_count": role.user_count,
                "permission_count": role.permission_count,
                "children": []
            }
            role_map[role.id] = role_dict
            
            if role.parent_id is None:
                root_roles.append(role_dict)
            else:
                parent = role_map.get(role.parent_id)
                if parent:
                    parent["children"].append(role_dict)
        
        return root_roles
    
    async def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有角色"""
        query = select(UserRole).options(
            selectinload(UserRole.role)
        ).where(UserRole.user_id == user_id)
        
        result = await self.db.execute(query)
        user_roles = result.scalars().all()
        
        roles = []
        for ur in user_roles:
            role = ur.role
            roles.append({
                "id": role.id,
                "code": role.code,
                "name": role.name,
                "description": role.description,
                "color": role.color,
                "icon": role.icon,
                "is_active": role.is_active,
                "priority": role.priority
            })
        
        return roles
    
    async def get_role_statistics(self) -> Dict[str, Any]:
        """获取角色统计信息"""
        # 总角色数
        total_query = select(func.count(Role.id))
        total_result = await self.db.execute(total_query)
        total_roles = total_result.scalar()
        
        # 活跃角色数
        active_query = select(func.count(Role.id)).where(Role.is_active == True)
        active_result = await self.db.execute(active_query)
        active_roles = active_result.scalar()
        
        # 系统角色数
        system_query = select(func.count(Role.id)).where(Role.is_system_role == True)
        system_result = await self.db.execute(system_query)
        system_roles = system_result.scalar()
        
        # 用户分布统计
        user_distribution_query = select(
            Role.name,
            func.count(UserRole.user_id).label("user_count")
        ).outerjoin(UserRole).group_by(Role.id, Role.name).order_by(func.count(UserRole.user_id).desc())
        
        user_distribution_result = await self.db.execute(user_distribution_query)
        user_distribution = [
            {"role_name": row.name, "user_count": row.user_count}
            for row in user_distribution_result
        ]
        
        return {
            "total_roles": total_roles,
            "active_roles": active_roles,
            "inactive_roles": total_roles - active_roles,
            "system_roles": system_roles,
            "custom_roles": total_roles - system_roles,
            "user_distribution": user_distribution
        }
    
    async def copy_role(self, source_role_id: int, new_role_data: Dict[str, Any]) -> Role:
        """复制角色"""
        source_role = await self.get_role_by_id(source_role_id)
        if not source_role:
            raise ValueError("源角色不存在")
        
        # 创建新角色
        new_role_data.update({
            "description": new_role_data.get("description", f"复制自 {source_role.name}"),
            "color": source_role.color,
            "icon": source_role.icon,
            "parent_id": source_role.parent_id,
            "priority": source_role.priority,
            "inherit_parent_permissions": source_role.inherit_parent_permissions,
            "permission_policy": source_role.permission_policy,
            "data_scope": source_role.data_scope,
            "data_scope_config": source_role.data_scope_config
        })
        
        new_role = await self.create_role(new_role_data)
        
        # 复制权限
        for role_permission in source_role.permissions:
            new_role_permission = RolePermission(
                role_id=new_role.id,
                permission_id=role_permission.permission_id,
                effect=role_permission.effect,
                conditions=role_permission.conditions
            )
            self.db.add(new_role_permission)
        
        await self.db.commit()
        
        return new_role