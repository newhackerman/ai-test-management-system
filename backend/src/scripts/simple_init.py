#!/usr/bin/env python3
"""
简单的初始化脚本 - 只创建基本的权限和角色
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from ..core.database import engine, SessionLocal
from ..models.base import Base
from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import RolePermission
from ..models.permission import Permission
from ..utils.password import password_service


def init_database():
    """初始化数据库表"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")


def create_basic_permissions():
    """创建基本权限"""
    db: Session = SessionLocal()
    
    try:
        print("正在创建基本权限...")
        
        # 检查是否已存在权限
        existing_count = db.query(Permission).count()
        if existing_count > 0:
            print("权限已存在，跳过创建")
            return
        
        # 基本权限列表
        basic_permissions = [
            {"name": "View Users", "code": "user:view", "module": "user_management", "action": "view"},
            {"name": "Create Users", "code": "user:create", "module": "user_management", "action": "create"},
            {"name": "Edit Users", "code": "user:edit", "module": "user_management", "action": "edit"},
            {"name": "Delete Users", "code": "user:delete", "module": "user_management", "action": "delete"},
            {"name": "View Roles", "code": "role:view", "module": "role_management", "action": "view"},
            {"name": "Create Roles", "code": "role:create", "module": "role_management", "action": "create"},
            {"name": "View Permissions", "code": "permission:view", "module": "permission_management", "action": "view"},
            {"name": "System Settings", "code": "system:settings", "module": "system_config", "action": "settings"},
        ]
        
        # 创建权限
        from ..models.permission import PermissionType
        
        for perm_data in basic_permissions:
            permission = Permission(
                name=perm_data["name"],
                code=perm_data["code"],
                module=perm_data["module"],
                action=perm_data["action"],
                description=perm_data["name"],
                type=PermissionType.OPERATION
            )
            db.add(permission)
        
        db.commit()
        print("基本权限创建完成")
        
    except Exception as e:
        print(f"创建权限失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_basic_roles():
    """创建基本角色"""
    db: Session = SessionLocal()
    
    try:
        print("正在创建基本角色...")
        
        # 检查是否已存在角色
        existing_count = db.query(Role).count()
        if existing_count > 0:
            print("角色已存在，跳过创建")
            return
        
        # 获取所有权限
        all_permissions = db.query(Permission).all()
        permission_map = {p.code: p for p in all_permissions}
        
        # 创建管理员角色
        admin_role = Role(
            name="System Administrator",
            code="admin",
            description="System administrator with all permissions",
            is_system_role=True,
            priority=100
        )
        db.add(admin_role)
        db.flush()  # 获取角色ID
        
        # 为管理员角色分配所有权限
        for permission in all_permissions:
            role_permission = RolePermission(
                role_id=admin_role.id,
                permission_id=permission.id
            )
            db.add(role_permission)
        
        # 创建普通用户角色
        user_role = Role(
            name="Regular User",
            code="user",
            description="Regular user with basic view permissions",
            is_system_role=True,
            priority=10
        )
        db.add(user_role)
        db.flush()
        
        # 为普通用户分配查看权限
        view_permission = permission_map.get("user:view")
        if view_permission:
            role_permission = RolePermission(
                role_id=user_role.id,
                permission_id=view_permission.id
            )
            db.add(role_permission)
        
        db.commit()
        print("基本角色创建完成")
        
    except Exception as e:
        print(f"创建角色失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_admin_user():
    """创建管理员用户"""
    db: Session = SessionLocal()
    
    try:
        print("正在创建管理员用户...")
        
        # 检查是否已存在admin用户
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("管理员用户已存在，跳过创建")
            return
        
        # 生成密码哈希
        salt, password_hash = password_service.hash_password("admin123")
        
        # 创建管理员用户
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=password_hash,
            salt=salt,
            nickname="System Administrator",
            is_superuser=True
        )
        db.add(admin_user)
        db.flush()
        
        # 获取admin角色
        admin_role = db.query(Role).filter(Role.code == "admin").first()
        if admin_role:
            # 分配admin角色
            user_role = UserRole(
                user_id=admin_user.id,
                role_id=admin_role.id
            )
            db.add(user_role)
        
        db.commit()
        print("管理员用户创建成功")
        print("用户名: admin")
        print("密码: admin123")
        
    except Exception as e:
        print(f"创建管理员用户失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """主函数"""
    print("开始简单初始化...")
    
    try:
        # 1. 初始化数据库表
        init_database()
        
        # 2. 创建基本权限
        create_basic_permissions()
        
        # 3. 创建基本角色
        create_basic_roles()
        
        # 4. 创建管理员用户
        create_admin_user()
        
        print("\n初始化完成！")
        print("默认管理员账户:")
        print("用户名: admin")
        print("密码: admin123")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()