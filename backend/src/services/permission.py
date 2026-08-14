"""
权限服务 - 提供角色和权限管理功能
"""
from typing import Optional, List, Dict, Any, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload
from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import Permission, RolePermission
from ..models.audit import AuditLog, AuditAction, AuditResult
from ..core.redis import redis_service


class PermissionService:
    """权限服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_role(
        self,
        name: str,
        code: str,
        description: Optional[str] = None,
        is_system_role: bool = False,
        priority: int = 0,
        permission_ids: Optional[List[int]] = None,
        created_by: Optional[int] = None
    ) -> Tuple[Optional[Role], Optional[str]]:
        """创建角色"""
        # 验证角色名称唯一性
        if self._check_role_name_exists(name):
            return None, "角色名称已存在"
        
        # 验证角色代码唯一性
        if self._check_role_code_exists(code):
            return None, "角色代码已存在"
        
        # 创建角色
        role = Role(
            name=name,
            code=code,
            description=description,
            is_system_role=is_system_role,
            priority=priority
        )
        
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        
        # 分配权限
        if permission_ids:
            self._assign_permissions(role.id, permission_ids)
        
        # 记录审计日志
        self._log_permission_action(
            user_id=created_by,
            action=AuditAction.CREATE,
            resource_type="role",
            resource_id=str(role.id),
            result=AuditResult.SUCCESS,
            new_values={
                "name": name,
                "code": code,
                "description": description,
                "is_system_role": is_system_role,
                "priority": priority
            }
        )
        
        return role, None
    
    def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """根据ID获取角色"""
        query = select(Role).where(Role.id == role_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()
    
    def get_role_by_code(self, code: str) -> Optional[Role]:
        """根据代码获取角色"""
        query = select(Role).where(Role.code == code)
        result = self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_roles(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        is_system_role: Optional[bool] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Role], int]:
        """获取角色列表"""
        # 构建查询条件
        conditions = []

        if search:
            conditions.append(
                or_(
                    Role.name.contains(search),
                    Role.code.contains(search),
                    Role.description.contains(search)
                )
            )

        if is_system_role is not None:
            conditions.append(Role.is_system_role == is_system_role)

        if is_active is not None:
            conditions.append(Role.is_active == is_active)

        # 查询总数
        count_query = select(func.count(Role.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 查询角色列表
        offset = (page - 1) * size
        query = (
            select(Role)
            .options(selectinload(Role.permissions), selectinload(Role.users))
        )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Role.priority.asc(), Role.created_at.desc())
        query = query.offset(offset).limit(size)

        result = await self.db.execute(query)
        roles = result.scalars().all()

        return list(roles), total
    
    def update_role(
        self,
        role_id: int,
        name: Optional[str] = None,
        code: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        priority: Optional[int] = None,
        permission_ids: Optional[List[int]] = None,
        updated_by: Optional[int] = None
    ) -> Tuple[Optional[Role], Optional[str]]:
        """更新角色"""
        # 获取角色
        role = self.get_role_by_id(role_id)
        if not role:
            return None, "角色不存在"
        
        # 系统角色不能修改某些字段
        if role.is_system_role:
            if code and code != role.code:
                return None, "系统角色不能修改代码"
        
        # 记录旧值
        old_values = {
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_active": role.is_active,
            "priority": role.priority
        }
        
        # 验证角色名称唯一性
        if name and name != role.name:
            if self._check_role_name_exists(name):
                return None, "角色名称已存在"
            role.name = name
        
        # 验证角色代码唯一性
        if code and code != role.code and not role.is_system_role:
            if self._check_role_code_exists(code):
                return None, "角色代码已存在"
            role.code = code
        
        # 更新其他字段
        if description is not None:
            role.description = description
        
        if is_active is not None:
            role.is_active = is_active
        
        if priority is not None:
            role.priority = priority
        
        # 更新角色
        self.db.commit()
        self.db.refresh(role)
        
        # 更新权限
        if permission_ids is not None:
            self._update_role_permissions(role_id, permission_ids)
        
        # 记录审计日志
        new_values = {
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_active": role.is_active,
            "priority": role.priority
        }
        
        self._log_permission_action(
            user_id=updated_by,
            action=AuditAction.UPDATE,
            resource_type="role",
            resource_id=str(role.id),
            result=AuditResult.SUCCESS,
            old_values=old_values,
            new_values=new_values
        )
        
        return role, None
    
    def delete_role(self, role_id: int, deleted_by: Optional[int] = None) -> bool:
        """删除角色"""
        # 获取角色
        role = self.get_role_by_id(role_id)
        if not role:
            return False
        
        # 系统角色不能删除
        if role.is_system_role:
            return False
        
        # 记录旧值
        old_values = {
            "name": role.name,
            "code": role.code,
            "description": role.description
        }
        
        # 删除角色权限关联
        self.db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        
        # 删除用户角色关联
        self.db.execute(
            delete(UserRole).where(UserRole.role_id == role_id)
        )
        
        # 删除角色
        self.db.delete(role)
        self.db.commit()
        
        # 记录审计日志
        self._log_permission_action(
            user_id=deleted_by,
            action=AuditAction.DELETE,
            resource_type="role",
            resource_id=str(role_id),
            result=AuditResult.SUCCESS,
            old_values=old_values
        )
        
        return True
    
    def create_permission(
        self,
        name: str,
        code: str,
        module: str,
        action: str,
        resource: Optional[str] = None,
        description: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> Tuple[Optional[Permission], Optional[str]]:
        """创建权限"""
        # 验证权限代码唯一性
        if self._check_permission_code_exists(code):
            return None, "权限代码已存在"
        
        # 创建权限
        permission = Permission(
            name=name,
            code=code,
            module=module,
            action=action,
            resource=resource,
            description=description
        )
        
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        
        # 记录审计日志
        self._log_permission_action(
            user_id=created_by,
            action=AuditAction.CREATE,
            resource_type="permission",
            resource_id=str(permission.id),
            result=AuditResult.SUCCESS,
            new_values={
                "name": name,
                "code": code,
                "module": module,
                "action": action,
                "resource": resource,
                "description": description
            }
        )
        
        return permission, None
    
    def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        """根据ID获取权限"""
        query = select(Permission).where(Permission.id == permission_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()
    
    def get_permission_by_code(self, code: str) -> Optional[Permission]:
        """根据代码获取权限"""
        query = select(Permission).where(Permission.code == code)
        result = self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_permissions(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        module: Optional[str] = None
    ) -> Tuple[List[Permission], int]:
        """获取权限列表"""
        # 构建查询条件
        conditions = []

        if search:
            conditions.append(
                or_(
                    Permission.name.contains(search),
                    Permission.code.contains(search),
                    Permission.description.contains(search)
                )
            )

        if module:
            conditions.append(Permission.module == module)

        # 查询总数
        count_query = select(func.count(Permission.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 查询权限列表
        offset = (page - 1) * size
        query = select(Permission)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Permission.module.asc(), Permission.action.asc())
        query = query.offset(offset).limit(size)

        result = await self.db.execute(query)
        permissions = result.scalars().all()

        return list(permissions), total
    
    def update_permission(
        self,
        permission_id: int,
        name: Optional[str] = None,
        code: Optional[str] = None,
        module: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        description: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> Tuple[Optional[Permission], Optional[str]]:
        """更新权限"""
        # 获取权限
        permission = self.get_permission_by_id(permission_id)
        if not permission:
            return None, "权限不存在"
        
        # 记录旧值
        old_values = {
            "name": permission.name,
            "code": permission.code,
            "module": permission.module,
            "action": permission.action,
            "resource": permission.resource,
            "description": permission.description
        }
        
        # 验证权限代码唯一性
        if code and code != permission.code:
            if self._check_permission_code_exists(code):
                return None, "权限代码已存在"
            permission.code = code
        
        # 更新其他字段
        if name is not None:
            permission.name = name
        
        if module is not None:
            permission.module = module
        
        if action is not None:
            permission.action = action
        
        if resource is not None:
            permission.resource = resource
        
        if description is not None:
            permission.description = description
        
        # 更新权限
        self.db.commit()
        self.db.refresh(permission)
        
        # 记录审计日志
        new_values = {
            "name": permission.name,
            "code": permission.code,
            "module": permission.module,
            "action": permission.action,
            "resource": permission.resource,
            "description": permission.description
        }
        
        self._log_permission_action(
            user_id=updated_by,
            action=AuditAction.UPDATE,
            resource_type="permission",
            resource_id=str(permission.id),
            result=AuditResult.SUCCESS,
            old_values=old_values,
            new_values=new_values
        )
        
        return permission, None
    
    def delete_permission(self, permission_id: int, deleted_by: Optional[int] = None) -> bool:
        """删除权限"""
        # 获取权限
        permission = self.get_permission_by_id(permission_id)
        if not permission:
            return False
        
        # 记录旧值
        old_values = {
            "name": permission.name,
            "code": permission.code,
            "module": permission.module,
            "action": permission.action,
            "resource": permission.resource,
            "description": permission.description
        }
        
        # 删除角色权限关联
        self.db.execute(
            delete(RolePermission).where(RolePermission.permission_id == permission_id)
        )
        
        # 删除权限
        self.db.delete(permission)
        self.db.commit()
        
        # 记录审计日志
        self._log_permission_action(
            user_id=deleted_by,
            action=AuditAction.DELETE,
            resource_type="permission",
            resource_id=str(permission_id),
            result=AuditResult.SUCCESS,
            old_values=old_values
        )
        
        return True
    
    def assign_role_to_user(
        self,
        user_id: int,
        role_id: int,
        assigned_by: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """给用户分配角色"""
        # 检查角色是否存在
        role = self.get_role_by_id(role_id)
        if not role:
            return False, "角色不存在"
        
        # 检查用户是否存在
        user_query = select(User).where(User.id == user_id)
        user_result = self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return False, "用户不存在"
        
        # 检查用户是否已有该角色
        existing_assignment = self.db.execute(
            select(UserRole).where(
                and_(UserRole.user_id == user_id, UserRole.role_id == role_id)
            )
        ).scalar_one_or_none()
        
        if existing_assignment:
            return False, "用户已有该角色"
        
        # 分配角色
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(user_role)
        self.db.commit()
        
        # 清除用户权限缓存
        self._clear_user_permissions_cache(user_id)
        
        # 记录审计日志
        self._log_permission_action(
            user_id=assigned_by,
            action=AuditAction.ASSIGN,
            resource_type="user_role",
            resource_id=f"{user_id}_{role_id}",
            result=AuditResult.SUCCESS,
            new_values={
                "user_id": user_id,
                "role_id": role_id,
                "role_name": role.name
            }
        )
        
        return True, None
    
    def revoke_role_from_user(
        self,
        user_id: int,
        role_id: int,
        revoked_by: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """撤销用户的角色"""
        # 检查角色是否存在
        role = self.get_role_by_id(role_id)
        if not role:
            return False, "角色不存在"
        
        # 检查用户角色关联是否存在
        user_role = self.db.execute(
            select(UserRole).where(
                and_(UserRole.user_id == user_id, UserRole.role_id == role_id)
            )
        ).scalar_one_or_none()
        
        if not user_role:
            return False, "用户没有该角色"
        
        # 记录旧值
        old_values = {
            "user_id": user_id,
            "role_id": role_id,
            "role_name": role.name
        }
        
        # 删除用户角色关联
        self.db.delete(user_role)
        self.db.commit()
        
        # 清除用户权限缓存
        self._clear_user_permissions_cache(user_id)
        
        # 记录审计日志
        self._log_permission_action(
            user_id=revoked_by,
            action=AuditAction.REVOKE,
            resource_type="user_role",
            resource_id=f"{user_id}_{role_id}",
            result=AuditResult.SUCCESS,
            old_values=old_values
        )
        
        return True, None
    
    def get_user_roles(self, user_id: int) -> List[Role]:
        """获取用户的所有角色"""
        query = (
            select(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
            .where(Role.is_active == True)
        )
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def get_user_permissions(self, user_id: int) -> Set[str]:
        """获取用户的所有权限代码"""
        # 尝试从缓存获取
        cache_key = f"user_permissions:{user_id}"
        cached_permissions = redis_service.get(cache_key)
        
        if cached_permissions:
            return set(cached_permissions.split(","))
        
        # 从数据库查询
        query = (
            select(Permission.code)
            .join(RolePermission)
            .join(Role)
            .join(UserRole)
            .join(User)
            .where(User.id == user_id)
            .where(Role.is_active == True)
            .where(Permission.is_active == True)
        )
        
        result = self.db.execute(query)
        permissions = {row[0] for row in result.all()}
        
        # 缓存结果
        redis_service.set(cache_key, ",".join(permissions), expire=3600)
        
        return permissions
    
    def check_user_permission(self, user_id: int, permission_code: str) -> bool:
        """检查用户是否具有特定权限"""
        user_permissions = self.get_user_permissions(user_id)
        return permission_code in user_permissions
    
    def check_user_role(self, user_id: int, role_code: str) -> bool:
        """检查用户是否具有特定角色"""
        user_roles = self.get_user_roles(user_id)
        return any(role.code == role_code for role in user_roles)
    
    def has_any_permission(self, user_id: int, permission_codes: List[str]) -> bool:
        """检查用户是否具有任意一个权限"""
        user_permissions = self.get_user_permissions(user_id)
        return any(code in user_permissions for code in permission_codes)
    
    def has_all_permissions(self, user_id: int, permission_codes: List[str]) -> bool:
        """检查用户是否具有所有权限"""
        user_permissions = self.get_user_permissions(user_id)
        return all(code in user_permissions for code in permission_codes)
    
    async def get_permission_modules(self) -> List[str]:
        """获取所有权限模块"""
        query = select(Permission.module).distinct()
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]
    
    def get_permissions_by_module(self, module: str) -> List[Permission]:
        """根据模块获取权限"""
        query = select(Permission).where(Permission.module == module)
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def initialize_default_permissions(self) -> None:
        """初始化默认权限 - 根据需求文档的权限矩阵"""
        # 检查是否已初始化
        existing_count = self.db.execute(
            select(func.count(Permission.id))
        ).scalar()
        
        if existing_count > 0:
            return
        
        # 根据需求文档权限矩阵定义的权限列表
        default_permissions = [
            # 用户管理权限
            {"name": "查看用户", "code": "user:view", "module": "user_management", "action": "view", "description": "查看用户列表和详情"},
            {"name": "创建用户", "code": "user:create", "module": "user_management", "action": "create", "description": "创建新用户账户"},
            {"name": "编辑用户", "code": "user:edit", "module": "user_management", "action": "edit", "description": "编辑用户信息"},
            {"name": "删除用户", "code": "user:delete", "module": "user_management", "action": "delete", "description": "删除用户账户"},
            {"name": "分配角色", "code": "user:assign_role", "module": "user_management", "action": "assign_role", "description": "为用户分配角色"},
            {"name": "重置密码", "code": "user:reset_password", "module": "user_management", "action": "reset_password", "description": "重置用户密码"},
            {"name": "锁定用户", "code": "user:lock", "module": "user_management", "action": "lock", "description": "锁定/解锁用户账户"},
            
            # 项目管理权限
            {"name": "查看项目", "code": "project:view", "module": "project_management", "action": "view", "description": "查看项目信息"},
            {"name": "创建项目", "code": "project:create", "module": "project_management", "action": "create", "description": "创建新项目"},
            {"name": "编辑项目", "code": "project:edit", "module": "project_management", "action": "edit", "description": "编辑项目信息"},
            {"name": "删除项目", "code": "project:delete", "module": "project_management", "action": "delete", "description": "删除项目"},
            {"name": "项目配置", "code": "project:config", "module": "project_management", "action": "config", "description": "配置项目设置"},
            
            # 需求管理权限
            {"name": "查看需求", "code": "requirement:view", "module": "requirement_management", "action": "view", "description": "查看需求信息"},
            {"name": "创建需求", "code": "requirement:create", "module": "requirement_management", "action": "create", "description": "创建新需求"},
            {"name": "编辑需求", "code": "requirement:edit", "module": "requirement_management", "action": "edit", "description": "编辑需求信息"},
            {"name": "删除需求", "code": "requirement:delete", "module": "requirement_management", "action": "delete", "description": "删除需求"},
            {"name": "需求审核", "code": "requirement:review", "module": "requirement_management", "action": "review", "description": "审核需求"},
            
            # 测试管理权限
            {"name": "查看测试", "code": "test:view", "module": "test_management", "action": "view", "description": "查看测试用例和结果"},
            {"name": "创建测试", "code": "test:create", "module": "test_management", "action": "create", "description": "创建测试用例"},
            {"name": "编辑测试", "code": "test:edit", "module": "test_management", "action": "edit", "description": "编辑测试用例"},
            {"name": "删除测试", "code": "test:delete", "module": "test_management", "action": "delete", "description": "删除测试用例"},
            {"name": "执行测试", "code": "test:execute", "module": "test_management", "action": "execute", "description": "执行测试用例"},
            {"name": "测试报告", "code": "test:report", "module": "test_management", "action": "report", "description": "生成测试报告"},
            
            # 角色管理权限
            {"name": "查看角色", "code": "role:view", "module": "role_management", "action": "view", "description": "查看角色列表和详情"},
            {"name": "创建角色", "code": "role:create", "module": "role_management", "action": "create", "description": "创建新角色"},
            {"name": "编辑角色", "code": "role:edit", "module": "role_management", "action": "edit", "description": "编辑角色信息"},
            {"name": "删除角色", "code": "role:delete", "module": "role_management", "action": "delete", "description": "删除角色"},
            {"name": "分配权限", "code": "role:assign_permission", "module": "role_management", "action": "assign_permission", "description": "为角色分配权限"},
            
            # 权限管理权限
            {"name": "查看权限", "code": "permission:view", "module": "permission_management", "action": "view", "description": "查看权限列表"},
            {"name": "创建权限", "code": "permission:create", "module": "permission_management", "action": "create", "description": "创建新权限"},
            {"name": "编辑权限", "code": "permission:edit", "module": "permission_management", "action": "edit", "description": "编辑权限信息"},
            {"name": "删除权限", "code": "permission:delete", "module": "permission_management", "action": "delete", "description": "删除权限"},
            
            # 系统配置权限
            {"name": "查看系统配置", "code": "system:view", "module": "system_config", "action": "view", "description": "查看系统配置"},
            {"name": "修改系统配置", "code": "system:edit", "module": "system_config", "action": "edit", "description": "修改系统配置"},
            {"name": "系统备份", "code": "system:backup", "module": "system_config", "action": "backup", "description": "系统数据备份"},
            {"name": "系统还原", "code": "system:restore", "module": "system_config", "action": "restore", "description": "系统数据还原"},
            {"name": "查看系统日志", "code": "system:logs", "module": "system_config", "action": "logs", "description": "查看系统日志"},
            
            # 审计权限
            {"name": "查看审计日志", "code": "audit:view", "module": "audit", "action": "view", "description": "查看审计日志"},
            {"name": "导出审计日志", "code": "audit:export", "module": "audit", "action": "export", "description": "导出审计日志"},
            {"name": "审计报告", "code": "audit:report", "module": "audit", "action": "report", "description": "生成审计报告"},
            
            # 监控权限
            {"name": "查看监控", "code": "monitor:view", "module": "monitoring", "action": "view", "description": "查看系统监控信息"},
            {"name": "配置告警", "code": "monitor:alert", "module": "monitoring", "action": "alert", "description": "配置监控告警"},
            
            # 数据权限
            {"name": "数据导入", "code": "data:import", "module": "data_management", "action": "import", "description": "导入数据"},
            {"name": "数据导出", "code": "data:export", "module": "data_management", "action": "export", "description": "导出数据"},
            {"name": "数据清理", "code": "data:clean", "module": "data_management", "action": "clean", "description": "清理数据"},
        ]
        
        # 创建默认权限
        for perm_data in default_permissions:
            permission = Permission(**perm_data)
            self.db.add(permission)
        
        self.db.commit()
    
    def initialize_default_roles(self) -> None:
        """初始化默认角色 - 根据需求文档定义的9种系统角色"""
        # 检查是否已初始化
        existing_count = self.db.execute(
            select(func.count(Role.id))
        ).scalar()
        
        if existing_count > 0:
            return
        
        # 初始化默认权限
        self.initialize_default_permissions()
        
        # 获取所有权限
        all_permissions = self.db.execute(select(Permission)).scalars().all()
        permission_map = {p.code: p for p in all_permissions}
        
        # 根据需求文档定义的9种系统角色及其权限矩阵
        default_roles = [
            {
                "name": "Admin（系统管理员）",
                "code": "admin",
                "description": "拥有系统所有权限，包括用户管理、系统配置、数据备份等",
                "is_system_role": True,
                "priority": 100,
                "permissions": list(permission_map.values())  # 拥有所有权限
            },
            {
                "name": "项目管理员",
                "code": "project_manager",
                "description": "项目全生命周期管理、团队管理、进度控制、资源分配",
                "is_system_role": True,
                "priority": 90,
                "permissions": [
                    # 完全权限
                    permission_map.get("project:view"),
                    permission_map.get("project:create"),
                    permission_map.get("project:edit"),
                    permission_map.get("project:delete"),
                    permission_map.get("project:config"),
                    # 只读权限
                    permission_map.get("user:view"),
                    permission_map.get("requirement:view"),
                    permission_map.get("test:view"),
                    permission_map.get("role:view"),
                    permission_map.get("permission:view"),
                    permission_map.get("system:logs"),
                    permission_map.get("audit:view"),
                    permission_map.get("monitor:view"),
                ]
            },
            {
                "name": "需求管理人员",
                "code": "requirement_manager",
                "description": "需求收集、分析、设计、变更管理、需求追溯",
                "is_system_role": True,
                "priority": 80,
                "permissions": [
                    # 完全权限
                    permission_map.get("requirement:view"),
                    permission_map.get("requirement:create"),
                    permission_map.get("requirement:edit"),
                    permission_map.get("requirement:delete"),
                    permission_map.get("requirement:review"),
                    # 只读权限
                    permission_map.get("project:view"),
                    permission_map.get("test:view"),
                    permission_map.get("user:view"),
                    permission_map.get("role:view"),
                    permission_map.get("permission:view"),
                ]
            },
            {
                "name": "设计人员",
                "code": "designer",
                "description": "系统设计、界面设计、原型设计、设计文档管理",
                "is_system_role": True,
                "priority": 70,
                "permissions": [
                    # 只读权限
                    permission_map.get("project:view"),
                    permission_map.get("requirement:view"),
                    permission_map.get("user:view"),
                    permission_map.get("role:view"),
                    permission_map.get("permission:view"),
                ]
            },
            {
                "name": "架构师",
                "code": "architect",
                "description": "技术架构设计、系统架构、技术选型、架构评审",
                "is_system_role": True,
                "priority": 75,
                "permissions": [
                    # 只读权限
                    permission_map.get("project:view"),
                    permission_map.get("requirement:view"),
                    permission_map.get("test:view"),
                    permission_map.get("user:view"),
                    permission_map.get("role:view"),
                    permission_map.get("permission:view"),
                    permission_map.get("system:view"),
                    permission_map.get("system:logs"),
                    permission_map.get("monitor:view"),
                ]
            },
            {
                "name": "开发人员",
                "code": "developer",
                "description": "代码开发、单元测试、代码审查、技术文档",
                "is_system_role": True,
                "priority": 60,
                "permissions": [
                    # 只读权限
                    permission_map.get("project:view"),
                    permission_map.get("requirement:view"),
                    permission_map.get("test:view"),
                    permission_map.get("user:view"),
                    permission_map.get("role:view"),
                    permission_map.get("permission:view"),
                ]
            },
            {
                "name": "测试人员",
                "code": "tester",
                "description": "测试用例设计、测试执行、缺陷管理、测试报告",
                "is_system_role": True,
                "priority": 50,
                "permissions": [
                    # 完全权限
                    permission_map.get("test:view"),
                    permission_map.get("test:create"),
                    permission_map.get("test:edit"),
                    permission_map.get("test:delete"),
                    permission_map.get("test:execute"),
                    permission_map.get("test:report"),
                    # 只读权限
                    permission_map.get("project:view"),
                    permission_map.get("requirement:view"),
                    permission_map.get("user:view"),
                    permission_map.get("role:view"),
                    permission_map.get("permission:view"),
                ]
            },
            {
                "name": "运维人员",
                "code": "ops",
                "description": "系统部署、监控告警、性能优化、安全维护",
                "is_system_role": True,
                "priority": 65,
                "permissions": [
                    # 完全权限
                    permission_map.get("system:view"),
                    permission_map.get("system:edit"),
                    permission_map.get("system:backup"),
                    permission_map.get("system:restore"),
                    permission_map.get("system:logs"),
                    permission_map.get("monitor:view"),
                    permission_map.get("monitor:alert"),
                    permission_map.get("audit:view"),
                    permission_map.get("audit:export"),
                    # 只读权限
                    permission_map.get("user:view"),
                    permission_map.get("role:view"),
                    permission_map.get("permission:view"),
                ]
            },
            {
                "name": "第三方人员",
                "code": "third_party",
                "description": "受限的查看权限、协作功能、文档访问",
                "is_system_role": True,
                "priority": 10,
                "permissions": [
                    # 只读权限
                    permission_map.get("project:view"),
                    permission_map.get("requirement:view"),
                ]
            }
        ]
        
        # 创建默认角色
        for role_data in default_roles:
            permissions = role_data.pop("permissions")
            role = Role(**role_data)
            self.db.add(role)
            self.db.flush()  # 获取角色ID
            
            # 分配权限（过滤掉None值）
            for permission in permissions:
                if permission:  # 确保权限存在
                    role_permission = RolePermission(
                        role_id=role.id,
                        permission_id=permission.id
                    )
                    self.db.add(role_permission)
        
        self.db.commit()
    
    def _check_role_name_exists(self, name: str) -> bool:
        """检查角色名称是否已存在"""
        query = select(Role).where(Role.name == name)
        result = self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    def _check_role_code_exists(self, code: str) -> bool:
        """检查角色代码是否已存在"""
        query = select(Role).where(Role.code == code)
        result = self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    def _check_permission_code_exists(self, code: str) -> bool:
        """检查权限代码是否已存在"""
        query = select(Permission).where(Permission.code == code)
        result = self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    def _assign_permissions(self, role_id: int, permission_ids: List[int]) -> None:
        """为角色分配权限"""
        for permission_id in permission_ids:
            # 检查权限是否存在
            permission = self.get_permission_by_id(permission_id)
            if not permission:
                continue
            
            # 检查是否已分配
            existing = self.db.execute(
                select(RolePermission).where(
                    and_(
                        RolePermission.role_id == role_id,
                        RolePermission.permission_id == permission_id
                    )
                )
            ).scalar_one_or_none()
            
            if not existing:
                role_permission = RolePermission(
                    role_id=role_id,
                    permission_id=permission_id
                )
                self.db.add(role_permission)
        
        self.db.commit()
    
    def _update_role_permissions(self, role_id: int, permission_ids: List[int]) -> None:
        """更新角色权限"""
        # 删除现有权限
        self.db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        
        # 分配新权限
        self._assign_permissions(role_id, permission_ids)
    
    def _clear_user_permissions_cache(self, user_id: int) -> None:
        """清除用户权限缓存"""
        cache_key = f"user_permissions:{user_id}"
        redis_service.delete(cache_key)
    
    def _log_permission_action(
        self,
        user_id: Optional[int],
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        result: AuditResult,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """记录权限操作审计日志"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            old_values=old_values,
            new_values=new_values,
            error_message=error_message
        )
        
        self.db.add(audit_log)
        self.db.commit() 
   
    def assign_permission_to_role(self, role_id: int, permission_id: int) -> Tuple[bool, Optional[str]]:
        """
        为角色分配权限
        
        Args:
            role_id: 角色ID
            permission_id: 权限ID
            
        Returns:
            Tuple[bool, Optional[str]]: 成功标志和错误信息
        """
        try:
            # 检查角色是否存在
            role = self.get_role_by_id(role_id)
            if not role:
                return False, "角色不存在"
            
            # 检查权限是否存在
            permission = self.get_permission_by_id(permission_id)
            if not permission:
                return False, "权限不存在"
            
            # 检查是否已经分配
            existing = self.db.execute(
                select(RolePermission).where(
                    and_(
                        RolePermission.role_id == role_id,
                        RolePermission.permission_id == permission_id
                    )
                )
            ).scalar_one_or_none()
            
            if existing:
                return False, "权限已经分配给该角色"
            
            # 分配权限
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission_id
            )
            self.db.add(role_permission)
            self.db.commit()
            
            # 清除缓存
            self._clear_user_permissions_cache_for_role(role_id)
            
            return True, None
            
        except Exception as e:
            self.db.rollback()
            return False, f"分配权限失败: {str(e)}"
    
    def remove_permission_from_role(self, role_id: int, permission_id: int) -> Tuple[bool, Optional[str]]:
        """
        从角色移除权限
        
        Args:
            role_id: 角色ID
            permission_id: 权限ID
            
        Returns:
            Tuple[bool, Optional[str]]: 成功标志和错误信息
        """
        try:
            # 检查角色权限关联是否存在
            role_permission = self.db.execute(
                select(RolePermission).where(
                    and_(
                        RolePermission.role_id == role_id,
                        RolePermission.permission_id == permission_id
                    )
                )
            ).scalar_one_or_none()
            
            if not role_permission:
                return False, "角色没有该权限"
            
            # 移除权限
            self.db.delete(role_permission)
            self.db.commit()
            
            # 清除缓存
            self._clear_user_permissions_cache_for_role(role_id)
            
            return True, None
            
        except Exception as e:
            self.db.rollback()
            return False, f"移除权限失败: {str(e)}"
    
    def remove_role_from_user(self, user_id: int, role_id: int) -> Tuple[bool, Optional[str]]:
        """
        从用户移除角色
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            
        Returns:
            Tuple[bool, Optional[str]]: 成功标志和错误信息
        """
        try:
            from ..models.user import UserRole
            
            # 检查用户角色关联是否存在
            user_role = self.db.execute(
                select(UserRole).where(
                    and_(
                        UserRole.user_id == user_id,
                        UserRole.role_id == role_id
                    )
                )
            ).scalar_one_or_none()
            
            if not user_role:
                return False, "用户没有该角色"
            
            # 移除角色
            self.db.delete(user_role)
            self.db.commit()
            
            # 清除用户权限缓存
            self._clear_user_permissions_cache(user_id)
            
            return True, None
            
        except Exception as e:
            self.db.rollback()
            return False, f"移除角色失败: {str(e)}"
    
    def update_role_permissions(self, role_id: int, permission_ids: List[int]) -> Tuple[bool, Optional[str]]:
        """
        更新角色权限（替换所有权限）
        
        Args:
            role_id: 角色ID
            permission_ids: 权限ID列表
            
        Returns:
            Tuple[bool, Optional[str]]: 成功标志和错误信息
        """
        try:
            # 检查角色是否存在
            role = self.get_role_by_id(role_id)
            if not role:
                return False, "角色不存在"
            
            # 删除现有权限
            self.db.execute(
                delete(RolePermission).where(RolePermission.role_id == role_id)
            )
            
            # 添加新权限
            for permission_id in permission_ids:
                # 检查权限是否存在
                permission = self.get_permission_by_id(permission_id)
                if permission:
                    role_permission = RolePermission(
                        role_id=role_id,
                        permission_id=permission_id
                    )
                    self.db.add(role_permission)
            
            self.db.commit()
            
            # 清除缓存
            self._clear_user_permissions_cache_for_role(role_id)
            
            return True, None
            
        except Exception as e:
            self.db.rollback()
            return False, f"更新角色权限失败: {str(e)}"
    
    def get_role_users(self, role_id: int, skip: int = 0, limit: int = 10) -> Tuple[List[User], int]:
        """
        获取拥有指定角色的用户
        
        Args:
            role_id: 角色ID
            skip: 跳过记录数
            limit: 每页记录数
            
        Returns:
            Tuple[List[User], int]: 用户列表和总数
        """
        try:
            from ..models.user import User, UserRole
            
            query = (
                select(User)
                .join(UserRole)
                .where(UserRole.role_id == role_id)
            )
            
            # 获取总数
            total_query = select(func.count()).select_from(
                User.__table__.join(UserRole.__table__)
            ).where(UserRole.role_id == role_id)
            
            total_result = self.db.execute(total_query)
            total = total_result.scalar()
            
            # 获取用户列表
            query = query.offset(skip).limit(limit)
            result = self.db.execute(query)
            users = list(result.scalars().all())
            
            return users, total
            
        except Exception:
            return [], 0
    
    def get_all_roles(self) -> List[Role]:
        """
        获取所有角色
        
        Returns:
            List[Role]: 角色列表
        """
        try:
            query = select(Role).order_by(Role.priority.desc())
            result = self.db.execute(query)
            return list(result.scalars().all())
        except Exception:
            return []
    
    def get_all_permissions(self) -> List[Permission]:
        """
        获取所有权限
        
        Returns:
            List[Permission]: 权限列表
        """
        try:
            query = select(Permission).order_by(Permission.module, Permission.action)
            result = self.db.execute(query)
            return list(result.scalars().all())
        except Exception:
            return []
    
    def _clear_user_permissions_cache_for_role(self, role_id: int) -> None:
        """
        清除拥有指定角色的所有用户的权限缓存
        
        Args:
            role_id: 角色ID
        """
        try:
            from ..models.user import User, UserRole
            
            # 获取拥有该角色的所有用户
            query = (
                select(User)
                .join(UserRole)
                .where(UserRole.role_id == role_id)
            )
            
            result = self.db.execute(query)
            users = result.scalars().all()
            
            # 清除每个用户的权限缓存
            for user in users:
                self._clear_user_permissions_cache(user.id)
                
        except Exception:
            # 如果清除缓存失败，不影响主要功能
            pass