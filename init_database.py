#!/usr/bin/env python3
'''
数据库初始化脚本
'''
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

async def init_database():
    '''初始化数据库'''
    try:
        from backend.src.core.database import init_database
        await init_database()
        print("✅ 数据库初始化成功")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False

async def create_admin_user():
    '''创建管理员用户'''
    try:
        from backend.src.services.user import UserService
        from backend.src.core.database import get_async_session
        
        async with get_async_session() as session:
            user_service = UserService(session)
            
            # 检查admin用户是否已存在
            existing_user = await user_service.get_user_by_username("admin")
            if existing_user:
                print("✅ 管理员用户已存在")
                return True
            
            # 创建admin用户
            admin_user = await user_service.create_user({
                "username": "admin",
                "email": "admin@example.com",
                "password": "admin123",
                "nickname": "系统管理员",
                "is_superuser": True
            })
            
            print(f"✅ 创建管理员用户成功: {admin_user.username}")
            return True
            
    except Exception as e:
        print(f"❌ 创建管理员用户失败: {e}")
        return False

async def main():
    '''主函数'''
    print("🚀 开始数据库初始化...")
    
    # 初始化数据库
    if not await init_database():
        sys.exit(1)
    
    # 创建管理员用户
    if not await create_admin_user():
        sys.exit(1)
    
    print("🎉 数据库初始化完成！")

if __name__ == "__main__":
    asyncio.run(main())
