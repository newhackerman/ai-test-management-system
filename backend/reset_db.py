#!/usr/bin/env python3
"""
重置数据库脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.database import engine
from src.models.base import Base

def reset_database():
    """重置数据库"""
    print("正在删除所有数据库表...")
    Base.metadata.drop_all(bind=engine)
    print("数据库表已删除")
    
    print("正在重新创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")

if __name__ == "__main__":
    reset_database()