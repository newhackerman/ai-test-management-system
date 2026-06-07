#!/usr/bin/env python3
"""
初始化权限和角色脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from ..core.database import engine, SessionLocal
from ..services.permission import PermissionService
from ..services.user import UserService
from ..models.base import Base
from ..utils.password import password_service


def init_database():
    """初始化数据库表"""
    print("正在创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")


def init_permissions_and_roles():
    """初始化权限和角色"""
    db: Session = SessionLocal()
    
    try:
        print("正在初始化权限和角色...")
        
        # 创建权限服务
        permission_service = PermissionService(db)
        
        # 初始化默认权限
        print("初始化默认权限...")
        permission_service.initialize_default_permissions()
        
        # 初始化默认角色
        print("初始化默认角色...")
        permission_service.initialize_default_roles()
        
        print("权限和角色初始化完成")
        
    except Exception as e:
        print(f"初始化权限和角色失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_admin_user():
    """创建默认管理员用户"""
    db: Session = SessionLocal()
    
    try:
        print("正在创建默认管理员用户...")
        
        # 创建用户服务和权限服务
        user_service = UserService(db)
        permission_service = PermissionService(db)
        
        # 检查是否已存在admin用户
        existing_admin = user_service.get_user_by_username("admin")
        if existing_admin:
            print("管理员用户已存在，跳过创建")
            return
        
        # 创建管理员用户
        admin_user, error = user_service.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123",
            first_name="系统",
            last_name="管理员"
        )
        
        if error:
            print(f"创建管理员用户失败: {error}")
            return
        
        # 获取admin角色
        admin_role = permission_service.get_role_by_code("admin")
        if admin_role:
            # 为管理员分配admin角色
            success, error = permission_service.assign_role_to_user(
                user_id=admin_user.id,
                role_id=admin_role.id
            )
            
            if success:
                print("管理员用户创建成功")
                print("用户名: admin")
                print("密码: admin123")
                print("邮箱: admin@example.com")
            else:
                print(f"分配管理员角色失败: {error}")
        else:
            print("未找到admin角色")
        
    except Exception as e:
        print(f"创建管理员用户失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """主函数"""
    print("开始初始化用户管理系统...")
    
    try:
        # 1. 初始化数据库表
        init_database()
        
        # 2. 初始化权限和角色
        init_permissions_and_roles()
        
        # 3. 创建默认管理员用户
        create_admin_user()
        
        print("\n用户管理系统初始化完成！")
        print("\n默认管理员账户:")
        print("用户名: admin")
        print("密码: admin123")
        print("邮箱: admin@example.com")
        print("\n请及时修改默认密码以确保系统安全！")
        
    except Exception as e:
        print(f"初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()