#!/usr/bin/env python3
"""
数据初始化脚本
用于初始化系统默认的角色、权限和管理员用户
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..config.database import get_database_url
from ..models.base import Base
from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import Permission, RolePermission
from ..services.permission import PermissionService
from ..services.user import UserService
from ..services.password import PasswordService


def create_admin_user(db_session):
    """创建默认管理员用户"""
    print("创建默认管理员用户...")
    
    user_service = UserService(db_session)
    permission_service = PermissionService(db_session)
    password_service = PasswordService()
    
    # 检查是否已存在管理员用户
    admin_user = user_service.get_user_by_username("admin")
    if admin_user:
        print("管理员用户已存在，跳过创建")
        return admin_user
    
    # 创建管理员用户
    admin_data = {
        "username": "admin",
        "email": "admin@example.com",
        "password": "Admin123!",  # 默认密码，首次登录需要修改
        "full_name": "系统管理员",
        "phone": "13800138000",
        "is_superuser": True,
        "is_email_verified": True,
        "status": "ACTIVE"
    }
    
    admin_user, error = user_service.create_user(**admin_data)
    if not admin_user:
        print(f"创建管理员用户失败: {error}")
        return None
    
    # 分配管理员角色
    admin_role = permission_service.get_role_by_code("admin")
    if admin_role:
        success, error = permission_service.assign_role_to_user(admin_user.id, admin_role.id)
        if success:
            print(f"管理员用户创建成功: {admin_user.username}")
        else:
            print(f"分配管理员角色失败: {error}")
    else:
        print("管理员角色不存在")
    
    return admin_user


def create_test_users(db_session):
    """创建测试用户"""
    print("创建测试用户...")
    
    user_service = UserService(db_session)
    permission_service = PermissionService(db_session)
    
    # 测试用户数据
    test_users = [
        {
            "username": "project_manager",
            "email": "pm@example.com",
            "password": "Test123!",
            "full_name": "项目经理",
            "role_code": "project_manager"
        },
        {
            "username": "developer",
            "email": "dev@example.com",
            "password": "Test123!",
            "full_name": "开发人员",
            "role_code": "developer"
        },
        {
            "username": "tester",
            "email": "test@example.com",
            "password": "Test123!",
            "full_name": "测试人员",
            "role_code": "tester"
        },
        {
            "username": "third_party",
            "email": "third@example.com",
            "password": "Test123!",
            "full_name": "第三方人员",
            "role_code": "third_party"
        }
    ]
    
    for user_data in test_users:
        # 检查用户是否已存在
        existing_user = user_service.get_user_by_username(user_data["username"])
        if existing_user:
            print(f"用户 {user_data['username']} 已存在，跳过创建")
            continue
        
        role_code = user_data.pop("role_code")
        user_data["is_email_verified"] = True
        user_data["status"] = "ACTIVE"
        
        # 创建用户
        user, error = user_service.create_user(**user_data)
        if not user:
            print(f"创建用户 {user_data['username']} 失败: {error}")
            continue
        
        # 分配角色
        role = permission_service.get_role_by_code(role_code)
        if role:
            success, error = permission_service.assign_role_to_user(user.id, role.id)
            if success:
                print(f"用户 {user.username} 创建成功，角色: {role.name}")
            else:
                print(f"为用户 {user.username} 分配角色失败: {error}")
        else:
            print(f"角色 {role_code} 不存在")


def main():
    """主函数"""
    print("开始初始化系统数据...")
    
    # 创建数据库连接
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 创建会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        # 初始化权限服务
        permission_service = PermissionService(db_session)
        
        # 1. 初始化默认权限
        print("初始化默认权限...")
        permission_service.initialize_default_permissions()
        print("默认权限初始化完成")
        
        # 2. 初始化默认角色
        print("初始化默认角色...")
        permission_service.initialize_default_roles()
        print("默认角色初始化完成")
        
        # 3. 创建管理员用户
        admin_user = create_admin_user(db_session)
        
        # 4. 创建测试用户（可选）
        create_test_users(db_session)
        
        print("\n系统数据初始化完成！")
        print("\n默认账户信息:")
        print("管理员账户: admin / Admin123!")
        print("项目经理账户: project_manager / Test123!")
        print("开发人员账户: developer / Test123!")
        print("测试人员账户: tester / Test123!")
        print("第三方人员账户: third_party / Test123!")
        print("\n注意: 请在首次登录后修改默认密码！")
        
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


if __name__ == "__main__":
    main()