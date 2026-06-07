#!/usr/bin/env python3
"""
清理测试用户
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.database import get_db
from src.models.user import User
from sqlalchemy import delete

def cleanup_test_users():
    """清理测试用户"""
    print("清理测试用户...")
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 删除测试用户
        test_usernames = [
            'test_batch_user_0',
            'test_batch_user_1', 
            'test_batch_user_2',
            'import_user_1',
            'import_user_2'
        ]
        
        for username in test_usernames:
            result = db.execute(
                delete(User).where(User.username == username)
            )
            if result.rowcount > 0:
                print(f"  删除用户: {username}")
        
        db.commit()
        print("✅ 测试用户清理完成")
        
    except Exception as e:
        print(f"❌ 清理测试用户失败: {e}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_test_users()