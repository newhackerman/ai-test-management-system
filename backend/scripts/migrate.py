#!/usr/bin/env python
"""
数据库迁移管理脚本
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command
from src.core.config import settings


def get_alembic_config():
    """获取Alembic配置"""
    config_path = os.path.join(project_root, "src", "migrations", "alembic.ini")
    config = Config(config_path)
    # 设置数据库URL
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def upgrade(revision="head", sql=False):
    """执行数据库升级"""
    config = get_alembic_config()
    command.upgrade(config, revision, sql=sql)
    print("数据库升级完成")


def downgrade(revision="-1", sql=False):
    """执行数据库降级"""
    config = get_alembic_config()
    command.downgrade(config, revision, sql=sql)
    print("数据库降级完成")


def revision(message=None, autogenerate=False):
    """创建新的迁移文件"""
    config = get_alembic_config()
    command.revision(config, message=message, autogenerate=autogenerate)
    print("新的迁移文件创建完成")


def current():
    """显示当前数据库版本"""
    config = get_alembic_config()
    command.current(config, verbose=True)


def history():
    """显示数据库迁移历史"""
    config = get_alembic_config()
    command.history(config, verbose=True)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据库迁移管理工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 升级命令
    upgrade_parser = subparsers.add_parser("upgrade", help="升级数据库")
    upgrade_parser.add_argument("--revision", default="head", help="目标版本")
    upgrade_parser.add_argument("--sql", action="store_true", help="生成SQL脚本")
    
    # 降级命令
    downgrade_parser = subparsers.add_parser("downgrade", help="降级数据库")
    downgrade_parser.add_argument("--revision", default="-1", help="目标版本")
    downgrade_parser.add_argument("--sql", action="store_true", help="生成SQL脚本")
    
    # 创建迁移文件命令
    revision_parser = subparsers.add_parser("revision", help="创建新的迁移文件")
    revision_parser.add_argument("--message", "-m", required=True, help="迁移文件描述")
    revision_parser.add_argument("--autogenerate", action="store_true", help="自动生成迁移内容")
    
    # 当前版本命令
    subparsers.add_parser("current", help="显示当前数据库版本")
    
    # 历史记录命令
    subparsers.add_parser("history", help="显示数据库迁移历史")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "upgrade":
        upgrade(args.revision, args.sql)
    elif args.command == "downgrade":
        downgrade(args.revision, args.sql)
    elif args.command == "revision":
        revision(args.message, args.autogenerate)
    elif args.command == "current":
        current()
    elif args.command == "history":
        history()


if __name__ == "__main__":
    main()