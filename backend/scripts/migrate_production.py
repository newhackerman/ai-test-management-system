#!/usr/bin/env python3
"""
生产环境数据库迁移脚本

提供生产环境数据库初始化、迁移、备份等功能。
支持数据完整性检查、回滚操作、增量迁移等。
"""

import os
import sys
import logging
import asyncio
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import argparse

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """数据库迁移管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.migration_scripts_dir = backend_dir / "sql"
        self.backup_dir = Path("/app/backups")
        
    def __enter__(self):
        """上下文管理器入口"""
        self.engine = create_engine(self.database_url)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        if self.engine:
            self.engine.dispose()
    
    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("数据库连接检查成功")
                return True
        except SQLAlchemyError as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """创建数据库备份"""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}.sql"
        
        backup_path = self.backup_dir / backup_name
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 解析数据库URL
        db_config = self._parse_database_url()
        
        # 构建mysqldump命令
        cmd = [
            "mysqldump",
            f"--host={db_config['host']}",
            f"--port={db_config['port']}",
            f"--user={db_config['username']}",
            f"--password={db_config['password']}",
            "--single-transaction",
            "--routines", 
            "--triggers",
            db_config['database']
        ]
        
        try:
            with open(backup_path, 'w') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    raise Exception(f"备份失败: {result.stderr}")
            
            logger.info(f"数据库备份成功: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"创建数据库备份失败: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    def _parse_database_url(self) -> Dict[str, str]:
        """解析数据库URL"""
        # mysql+asyncmy://user:password@host:port/database
        from urllib.parse import urlparse
        parsed = urlparse(self.database_url.replace("mysql+asyncmy://", "mysql://"))
        
        return {
            'username': parsed.username,
            'password': parsed.password,
            'host': parsed.hostname or 'localhost',
            'port': str(parsed.port or 3306),
            'database': parsed.path.lstrip('/')
        }
    
    def check_migration_table_exists(self) -> bool:
        """检查迁移表是否存在"""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            return 'migration_history' in tables
        except Exception as e:
            logger.error(f"检查迁移表失败: {e}")
            return False
    
    def create_migration_table(self):
        """创建迁移历史表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS migration_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checksum VARCHAR(64),
            status ENUM('SUCCESS', 'FAILED', 'ROLLED_BACK') DEFAULT 'SUCCESS'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(create_table_sql))
                conn.commit()
            logger.info("迁移历史表创建成功")
        except Exception as e:
            logger.error(f"创建迁移历史表失败: {e}")
            raise
    
    def get_applied_migrations(self) -> List[str]:
        """获取已应用的迁移"""
        if not self.check_migration_table_exists():
            return []
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT migration_name FROM migration_history WHERE status = 'SUCCESS' ORDER BY applied_at"
                ))
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"获取已应用迁移失败: {e}")
            return []
    
    def get_pending_migrations(self) -> List[Path]:
        """获取待应用的迁移文件"""
        applied_migrations = self.get_applied_migrations()
        migration_files = []
        
        # 获取所有.sql迁移文件
        for sql_file in sorted(self.migration_scripts_dir.glob("*.sql")):
            if sql_file.name not in applied_migrations:
                migration_files.append(sql_file)
        
        return migration_files
    
    def execute_migration(self, migration_file: Path) -> bool:
        """执行单个迁移文件"""
        logger.info(f"执行迁移: {migration_file.name}")
        
        try:
            # 读取迁移文件内容
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            # 计算文件校验和
            import hashlib
            checksum = hashlib.sha256(migration_sql.encode()).hexdigest()
            
            # 执行迁移
            with self.engine.connect() as conn:
                # 开始事务
                trans = conn.begin()
                try:
                    # 分割并执行SQL语句
                    statements = migration_sql.split(';')
                    for stmt in statements:
                        stmt = stmt.strip()
                        if stmt:
                            conn.execute(text(stmt))
                    
                    # 记录迁移历史
                    conn.execute(text(
                        "INSERT INTO migration_history (migration_name, checksum, status) VALUES (:name, :checksum, 'SUCCESS')"
                    ), {"name": migration_file.name, "checksum": checksum})
                    
                    trans.commit()
                    logger.info(f"迁移 {migration_file.name} 执行成功")
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    # 记录失败状态
                    with self.engine.connect() as conn2:
                        conn2.execute(text(
                            "INSERT INTO migration_history (migration_name, checksum, status) VALUES (:name, :checksum, 'FAILED')"
                        ), {"name": migration_file.name, "checksum": checksum})
                        conn2.commit()
                    raise e
                    
        except Exception as e:
            logger.error(f"执行迁移 {migration_file.name} 失败: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """运行所有待应用的迁移"""
        logger.info("开始数据库迁移...")
        
        # 确保迁移历史表存在
        if not self.check_migration_table_exists():
            self.create_migration_table()
        
        # 获取待应用的迁移
        pending_migrations = self.get_pending_migrations()
        
        if not pending_migrations:
            logger.info("没有待应用的迁移")
            return True
        
        logger.info(f"找到 {len(pending_migrations)} 个待应用的迁移")
        
        # 执行每个迁移
        for migration_file in pending_migrations:
            if not self.execute_migration(migration_file):
                logger.error(f"迁移失败，停止执行: {migration_file.name}")
                return False
        
        logger.info("所有迁移执行完成")
        return True
    
    def verify_schema(self) -> bool:
        """验证数据库架构完整性"""
        logger.info("验证数据库架构...")
        
        required_tables = [
            'users', 'roles', 'permissions', 'user_roles', 'role_permissions',
            'projects', 'requirements', 'test_cases', 'test_results',
            'ai_chat_sessions', 'ai_chat_messages', 'ai_model_configs',
            'ai_prompt_templates', 'ai_suggestions', 'ai_usage_stats'
        ]
        
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            
            missing_tables = []
            for table in required_tables:
                if table not in existing_tables:
                    missing_tables.append(table)
            
            if missing_tables:
                logger.error(f"缺少必需的数据表: {', '.join(missing_tables)}")
                return False
            
            logger.info("数据库架构验证通过")
            return True
            
        except Exception as e:
            logger.error(f"数据库架构验证失败: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生产环境数据库迁移工具")
    parser.add_argument('--database-url', required=True, help='数据库连接URL')
    parser.add_argument('--backup', action='store_true', help='迁移前创建备份')
    parser.add_argument('--verify-only', action='store_true', help='仅验证架构，不执行迁移')
    parser.add_argument('--force', action='store_true', help='强制执行，跳过确认')
    
    args = parser.parse_args()
    
    # 创建日志目录
    Path("/app/logs").mkdir(parents=True, exist_ok=True)
    
    try:
        with DatabaseMigrator(args.database_url) as migrator:
            # 检查数据库连接
            if not migrator.check_database_connection():
                logger.error("无法连接到数据库")
                return 1
            
            # 仅验证模式
            if args.verify_only:
                return 0 if migrator.verify_schema() else 1
            
            # 创建备份
            if args.backup:
                migrator.create_backup()
            
            # 确认执行
            if not args.force:
                pending = migrator.get_pending_migrations()
                if pending:
                    print(f"\n将要执行 {len(pending)} 个迁移:")
                    for migration in pending:
                        print(f"  - {migration.name}")
                    
                    confirm = input("\n确认执行迁移? (y/N): ")
                    if confirm.lower() != 'y':
                        print("迁移已取消")
                        return 0
            
            # 执行迁移
            if migrator.run_migrations():
                # 验证架构
                if migrator.verify_schema():
                    logger.info("数据库迁移完成！")
                    return 0
                else:
                    logger.error("架构验证失败")
                    return 1
            else:
                logger.error("迁移执行失败")
                return 1
                
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    exit(main())