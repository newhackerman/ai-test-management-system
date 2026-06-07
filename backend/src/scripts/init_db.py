"""
数据库初始化脚本
"""
import sys
import os

# 添加项目根目录到Python路径
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(backend_root, 'backend'))

from sqlalchemy import create_engine
from ..core.config import settings
from ..models.base import Base
from ..models.user import User, UserRole, UserSession, UserLog
from ..models.role import Role
from ..models.permission import RolePermission
from ..models.permission import Permission
from ..models.audit import AuditLog
from ..utils.password import password_service


def create_tables():
    """创建数据库表"""
    engine = create_engine(settings.DATABASE_URL)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")


def create_admin_user():
    """创建管理员用户"""
    from sqlalchemy.orm import sessionmaker
    from ..models.user import UserStatus
    
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 检查是否已存在管理员用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        if admin_user:
            print("管理员用户已存在")
            return
        
        # 创建管理员用户
        salt, password_hash = password_service.hash_password("admin123")
        
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=password_hash,
            salt=salt,
            nickname="系统管理员",
            status=UserStatus.ACTIVE,
            is_active=True,
            is_superuser=True,
            is_email_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print("管理员用户创建成功")
        print("用户名: admin")
        print("密码: admin123")
        
    except Exception as e:
        print(f"创建管理员用户失败: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """主函数"""
    print("开始初始化数据库...")
    
    # 创建表
    create_tables()
    
    # 创建管理员用户
    create_admin_user()
    
    print("数据库初始化完成")


if __name__ == "__main__":
    main()