#!/usr/bin/env python3
"""
在线会议模块数据库迁移执行脚本

本脚本用于执行在线会议模块的数据库迁移，包括：
- 创建所有会议相关数据表
- 建立外键约束和索引
- 插入初始数据和模板
- 创建统计视图

使用方法:
    python run_meeting_migration.py [--dry-run] [--force]
    
参数说明:
    --dry-run: 仅显示将要执行的SQL，不实际执行
    --force: 强制执行，即使已经执行过
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.database import get_db_connection
    from src.core.config import settings
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录下运行此脚本")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meeting_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MeetingMigrationRunner:
    """在线会议模块迁移执行器"""
    
    def __init__(self, dry_run=False, force=False):
        self.dry_run = dry_run
        self.force = force
        self.migration_file = Path(__file__).parent / "meeting_module_migration.sql"
        
    def check_migration_status(self, cursor):
        """检查迁移状态"""
        try:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'migration_history'
            """)
            
            if cursor.fetchone()['count'] == 0:
                return False, "migration_history表不存在"
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM migration_history 
                WHERE migration_name = 'meeting_module_migration'
            """)
            
            result = cursor.fetchone()
            if result['count'] > 0:
                return True, "会议模块迁移已执行"
            else:
                return False, "会议模块迁移未执行"
                
        except Exception as e:
            return False, f"检查迁移状态失败: {str(e)}"
    
    def check_tables_exist(self, cursor):
        """检查会议相关表是否已存在"""
        meeting_tables = [
            'meetings',
            'meeting_participants', 
            'meeting_recordings',
            'meeting_minutes',
            'meeting_chats',
            'meeting_files',
            'meeting_analytics',
            'meeting_templates'
        ]
        
        existing_tables = []
        for table in meeting_tables:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = %s
            """, (table,))
            
            if cursor.fetchone()['count'] > 0:
                existing_tables.append(table)
        
        return existing_tables
    
    def validate_dependencies(self, cursor):
        """验证依赖表是否存在"""
        required_tables = ['users', 'projects']
        missing_tables = []
        
        for table in required_tables:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = %s
            """, (table,))
            
            if cursor.fetchone()['count'] == 0:
                missing_tables.append(table)
        
        return missing_tables
    
    def read_migration_file(self):
        """读取迁移SQL文件"""
        if not self.migration_file.exists():
            raise FileNotFoundError(f"迁移文件不存在: {self.migration_file}")
        
        with open(self.migration_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def execute_sql_statements(self, cursor, sql_content):
        """执行SQL语句"""
        # 分割SQL语句（以分号和换行符为分隔符）
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('--'):
                continue
            
            current_statement.append(line)
            
            # 如果行以分号结尾，表示语句结束
            if line.endswith(';'):
                statement = ' '.join(current_statement).strip()
                if statement and not statement.startswith('--'):
                    statements.append(statement)
                current_statement = []
        
        # 处理最后一个语句（如果没有以分号结尾）
        if current_statement:
            statement = ' '.join(current_statement).strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
        
        # 执行语句
        executed_count = 0
        for i, statement in enumerate(statements, 1):
            try:
                if self.dry_run:
                    logger.info(f"[DRY RUN] 语句 {i}: {statement[:100]}...")
                else:
                    logger.info(f"执行语句 {i}/{len(statements)}: {statement[:100]}...")
                    cursor.execute(statement)
                    executed_count += 1
                    
            except Exception as e:
                logger.error(f"执行语句失败 {i}: {str(e)}")
                logger.error(f"问题语句: {statement}")
                raise
        
        return executed_count
    
    def run_migration(self):
        """执行迁移"""
        logger.info("开始执行在线会议模块数据库迁移")
        logger.info(f"迁移模式: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        logger.info(f"强制执行: {self.force}")
        
        try:
            # 获取数据库连接
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # 检查依赖表
            logger.info("检查依赖表...")
            missing_tables = self.validate_dependencies(cursor)
            if missing_tables:
                raise Exception(f"缺少依赖表: {', '.join(missing_tables)}")
            
            # 检查迁移状态
            logger.info("检查迁移状态...")
            is_migrated, status_msg = self.check_migration_status(cursor)
            logger.info(f"迁移状态: {status_msg}")
            
            if is_migrated and not self.force:
                logger.warning("迁移已执行，使用 --force 参数强制重新执行")
                return False
            
            # 检查现有表
            existing_tables = self.check_tables_exist(cursor)
            if existing_tables and not self.force:
                logger.warning(f"以下表已存在: {', '.join(existing_tables)}")
                logger.warning("使用 --force 参数强制重新执行")
                return False
            
            # 读取迁移文件
            logger.info("读取迁移文件...")
            sql_content = self.read_migration_file()
            
            # 执行迁移
            logger.info("执行迁移SQL...")
            if not self.dry_run:
                connection.begin()
            
            try:
                executed_count = self.execute_sql_statements(cursor, sql_content)
                
                if not self.dry_run:
                    connection.commit()
                    logger.info(f"迁移成功完成，执行了 {executed_count} 条SQL语句")
                else:
                    logger.info(f"DRY RUN 完成，共 {executed_count} 条SQL语句")
                
                return True
                
            except Exception as e:
                if not self.dry_run:
                    connection.rollback()
                raise
            
        except Exception as e:
            logger.error(f"迁移执行失败: {str(e)}")
            return False
        
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
    
    def verify_migration(self):
        """验证迁移结果"""
        if self.dry_run:
            return True
        
        logger.info("验证迁移结果...")
        
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # 检查所有表是否创建成功
            meeting_tables = [
                'meetings', 'meeting_participants', 'meeting_recordings',
                'meeting_minutes', 'meeting_chats', 'meeting_files',
                'meeting_analytics', 'meeting_templates'
            ]
            
            for table in meeting_tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                logger.info(f"表 {table}: 创建成功")
            
            # 检查视图是否创建成功
            cursor.execute("SELECT COUNT(*) as count FROM v_meeting_statistics")
            logger.info("视图 v_meeting_statistics: 创建成功")
            
            # 检查初始数据
            cursor.execute("SELECT COUNT(*) as count FROM meeting_templates")
            template_count = cursor.fetchone()['count']
            logger.info(f"会议模板初始数据: {template_count} 条记录")
            
            logger.info("迁移验证完成")
            return True
            
        except Exception as e:
            logger.error(f"迁移验证失败: {str(e)}")
            return False
        
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='在线会议模块数据库迁移工具')
    parser.add_argument('--dry-run', action='store_true', 
                       help='仅显示将要执行的SQL，不实际执行')
    parser.add_argument('--force', action='store_true',
                       help='强制执行，即使已经执行过')
    
    args = parser.parse_args()
    
    # 创建迁移执行器
    runner = MeetingMigrationRunner(dry_run=args.dry_run, force=args.force)
    
    # 执行迁移
    success = runner.run_migration()
    
    if success:
        # 验证迁移结果
        if runner.verify_migration():
            logger.info("在线会议模块迁移完成！")
            sys.exit(0)
        else:
            logger.error("迁移验证失败")
            sys.exit(1)
    else:
        logger.error("迁移执行失败")
        sys.exit(1)

if __name__ == '__main__':
    main()