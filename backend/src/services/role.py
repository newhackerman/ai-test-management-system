"""
角色管理服务
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..models.role import Role
from ..models.user import User, UserRole
from ..schemas.role import RoleCreate, RoleUpdate
from .base import BaseService


class RoleService(BaseService):
    """角色管理服务"""

    def get_all_roles(self) -> List[Role]:
        """获取所有活跃角色"""
        return (
            self.db.query(Role)
            .filter(Role.is_active == True)
            .order_by(Role.sort_order.asc(), Role.name.asc())
            .all()
        )

    def get_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        type_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """获取角色列表"""
        query = self.db.query(Role)

        # 搜索过滤
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Role.name.ilike(search_pattern),
                    Role.code.ilike(search_pattern),
                    Role.description.ilike(search_pattern)
                )
            )

        # 类型过滤
        if type_filter == "system":
            query = query.filter(Role.is_system_role == True)
        elif type_filter == "custom":
            query = query.filter(Role.is_system_role == False)

        # 状态过滤
        if status_filter == "active":
            query = query.filter(Role.is_active == True)
        elif status_filter == "inactive":
            query = query.filter(Role.is_active == False)

        # 总数
        total = query.count()

        # 排序
        if hasattr(Role, sort_by):
            order_column = getattr(Role, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())

        # 分页
        roles = query.offset(skip).limit(limit).all()

        # 计算用户数量
        for role in roles:
            user_count = (
                self.db.query(func.count(UserRole.user_id))
                .filter(UserRole.role_id == role.id)
                .scalar()
            )
            role.user_count = user_count

        return {
            "roles": roles,
            "total": total,
            "page": (skip // limit) + 1,
            "page_size": limit,
            "total_pages": (total + limit - 1) // limit
        }

    def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """根据ID获取角色"""
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_role_by_code(self, code: str) -> Optional[Role]:
        """根据代码获取角色"""
        return self.db.query(Role).filter(Role.code == code).first()

    def create_role(self, role_data: RoleCreate) -> Role:
        """创建角色"""
        # 检查角色代码是否已存在
        existing_role = self.get_role_by_code(role_data.code)
        if existing_role:
            raise ValueError(f"角色代码 '{role_data.code}' 已存在")

        # 创建角色
        role = Role(
            name=role_data.name,
            code=role_data.code,
            description=role_data.description,
            is_system_role=False,  # 通过API创建的都是自定义角色
            is_active=True,
            priority=role_data.priority or 0,
            sort_order=role_data.sort_order or 0
        )

        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)

        return role

    def update_role(self, role_id: int, role_data: RoleUpdate) -> Optional[Role]:
        """更新角色"""
        role = self.get_role_by_id(role_id)
        if not role:
            return None

        # 系统角色不允许修改某些字段
        if role.is_system_role:
            # 系统角色只允许修改描述和状态
            if role_data.description is not None:
                role.description = role_data.description
            if role_data.is_active is not None:
                role.is_active = role_data.is_active
        else:
            # 自定义角色可以修改所有字段
            if role_data.name is not None:
                role.name = role_data.name
            if role_data.code is not None:
                # 检查新代码是否已存在
                existing_role = self.get_role_by_code(role_data.code)
                if existing_role and existing_role.id != role_id:
                    raise ValueError(f"角色代码 '{role_data.code}' 已存在")
                role.code = role_data.code
            if role_data.description is not None:
                role.description = role_data.description
            if role_data.is_active is not None:
                role.is_active = role_data.is_active
            if role_data.priority is not None:
                role.priority = role_data.priority
            if role_data.sort_order is not None:
                role.sort_order = role_data.sort_order

        self.db.commit()
        self.db.refresh(role)

        return role

    def delete_role(self, role_id: int) -> bool:
        """删除角色"""
        role = self.get_role_by_id(role_id)
        if not role:
            return False

        # 系统角色不允许删除
        if role.is_system_role:
            raise ValueError("系统角色不允许删除")

        # 检查是否有用户使用此角色
        user_count = (
            self.db.query(func.count(UserRole.user_id))
            .filter(UserRole.role_id == role_id)
            .scalar()
        )

        if user_count > 0:
            raise ValueError(f"角色 '{role.name}' 正在被 {user_count} 个用户使用，无法删除")

        self.db.delete(role)
        self.db.commit()

        return True

    def assign_permissions_to_role(self, role_id: int, permission_ids: List[int]) -> bool:
        """为角色分配权限"""
        role = self.get_role_by_id(role_id)
        if not role:
            return False

        # 清除现有权限
        from ..models.permission import RolePermission
        self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id
        ).delete()

        # 分配新权限
        for permission_id in permission_ids:
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission_id
            )
            self.db.add(role_permission)

        self.db.commit()
        return True

    def get_role_permissions(self, role_id: int) -> List[int]:
        """获取角色的权限ID列表"""
        from ..models.permission import RolePermission
        
        permission_ids = (
            self.db.query(RolePermission.permission_id)
            .filter(RolePermission.role_id == role_id)
            .all()
        )

        return [pid[0] for pid in permission_ids]

    def get_role_users(self, role_id: int) -> List[User]:
        """获取拥有指定角色的用户列表"""
        return (
            self.db.query(User)
            .join(UserRole, User.id == UserRole.user_id)
            .filter(UserRole.role_id == role_id)
            .filter(User.deleted_at.is_(None))
            .all()
        )

    def create_system_roles(self) -> None:
        """创建系统默认角色"""
        system_roles = [
            {
                "name": "系统管理员",
                "code": "admin",
                "description": "拥有系统所有权限，包括用户管理、系统配置、数据备份等",
                "priority": 100,
                "sort_order": 1
            },
            {
                "name": "项目管理员", 
                "code": "project_manager",
                "description": "项目全生命周期管理、团队管理、进度控制、资源分配",
                "priority": 90,
                "sort_order": 2
            },
            {
                "name": "需求管理人员",
                "code": "requirement_manager", 
                "description": "需求收集、分析、设计、变更管理、需求追溯",
                "priority": 80,
                "sort_order": 3
            },
            {
                "name": "设计人员",
                "code": "designer",
                "description": "系统设计、界面设计、原型设计、设计文档管理", 
                "priority": 70,
                "sort_order": 4
            },
            {
                "name": "架构师",
                "code": "architect",
                "description": "技术架构设计、系统架构、技术选型、架构评审",
                "priority": 85,
                "sort_order": 5
            },
            {
                "name": "开发人员",
                "code": "developer", 
                "description": "代码开发、单元测试、代码审查、技术文档",
                "priority": 60,
                "sort_order": 6
            },
            {
                "name": "测试人员",
                "code": "tester",
                "description": "测试用例设计、测试执行、缺陷管理、测试报告",
                "priority": 65,
                "sort_order": 7
            },
            {
                "name": "运维人员", 
                "code": "ops",
                "description": "系统部署、监控告警、性能优化、安全维护",
                "priority": 75,
                "sort_order": 8
            },
            {
                "name": "第三方人员",
                "code": "third_party",
                "description": "受限的查看权限、协作功能、文档访问",
                "priority": 10,
                "sort_order": 9
            }
        ]

        for role_data in system_roles:
            existing_role = self.get_role_by_code(role_data["code"])
            if not existing_role:
                role = Role(
                    name=role_data["name"],
                    code=role_data["code"], 
                    description=role_data["description"],
                    is_system_role=True,
                    is_active=True,
                    priority=role_data["priority"],
                    sort_order=role_data["sort_order"]
                )
                self.db.add(role)

        self.db.commit()