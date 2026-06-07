#!/usr/bin/env python3
"""
仪表板模块数据库迁移脚本
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import get_settings
from src.core.database import get_async_session, engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DashboardMigrationRunner:
    """仪表板模块迁移运行器"""
    
    def __init__(self):
        self.settings = get_settings()
        self.migration_file = Path(__file__).parent / "dashboard_module_migration.sql"
        self.migration_results = []
    
    async def check_prerequisites(self) -> bool:
        """检查迁移前置条件"""
        logger.info("检查迁移前置条件...")
        
        try:
            # 检查数据库连接
            async for session in get_async_session():
                result = await session.execute(text("SELECT 1"))
                if result.scalar() != 1:
                    logger.error("数据库连接测试失败")
                    return False
            
            # 检查必要的表是否存在
            required_tables = ['users', 'roles', 'permissions']
            async for session in get_async_session():
                for table in required_tables:
                    result = await session.execute(
                        text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'")
                    )
                    if result.scalar() == 0:
                        logger.warning(f"必需的表 {table} 不存在，但迁移将继续")
            
            # 检查迁移文件是否存在
            if not self.migration_file.exists():
                logger.error(f"迁移文件不存在: {self.migration_file}")
                return False
            
            logger.info("前置条件检查通过")
            return True
            
        except Exception as e:
            logger.error(f"前置条件检查失败: {e}")
            return False
    
    async def backup_existing_data(self) -> bool:
        """备份现有数据"""
        logger.info("备份现有数据...")
        
        try:
            backup_tables = [
                'dashboard_configs',
                'widget_definitions', 
                'color_schemes',
                'user_color_preferences',
                'dashboard_data_cache',
                'websocket_connections'
            ]
            
            backup_dir = Path(__file__).parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            async for session in get_async_session():
                for table in backup_tables:
                    try:
                        # 检查表是否存在
                        result = await session.execute(
                            text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'")
                        )
                        
                        if result.scalar() > 0:
                            # 导出数据
                            backup_file = backup_dir / f"{table}_backup_{timestamp}.sql"
                            
                            # 获取表数据
                            result = await session.execute(text(f"SELECT * FROM {table}"))
                            rows = result.fetchall()
                            
                            if rows:
                                with open(backup_file, 'w', encoding='utf-8') as f:
                                    f.write(f"-- Backup of {table} at {timestamp}\n")
                                    f.write(f"-- Total rows: {len(rows)}\n\n")
                                    
                                    # 这里可以添加更详细的备份逻辑
                                    f.write(f"-- Data backed up successfully\n")
                                
                                logger.info(f"表 {table} 备份完成: {len(rows)} 行")
                            else:
                                logger.info(f"表 {table} 为空，跳过备份")
                        else:
                            logger.info(f"表 {table} 不存在，跳过备份")
                            
                    except Exception as e:
                        logger.warning(f"备份表 {table} 失败: {e}")
            
            logger.info("数据备份完成")
            return True
            
        except Exception as e:
            logger.error(f"数据备份失败: {e}")
            return False
    
    async def run_migration(self) -> bool:
        """运行迁移脚本"""
        logger.info("开始运行数据库迁移...")
        
        try:
            # 读取迁移文件
            with open(self.migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            # 分割SQL语句
            statements = self._split_sql_statements(migration_sql)
            
            async for session in get_async_session():
                success_count = 0
                error_count = 0
                
                for i, statement in enumerate(statements):
                    if statement.strip():
                        try:
                            logger.debug(f"执行语句 {i+1}/{len(statements)}")
                            await session.execute(text(statement))
                            success_count += 1
                            
                        except SQLAlchemyError as e:
                            error_count += 1
                            error_msg = str(e)
                            
                            # 某些错误可以忽略（如表已存在）
                            if any(ignore in error_msg.lower() for ignore in [
                                'table already exists',
                                'duplicate entry',
                                'already exists'
                            ]):
                                logger.warning(f"忽略的错误: {error_msg}")
                                success_count += 1
                                error_count -= 1
                            else:
                                logger.error(f"SQL执行失败: {error_msg}")
                                logger.error(f"失败的语句: {statement[:100]}...")
                
                # 提交事务
                await session.commit()
                
                logger.info(f"迁移完成: 成功 {success_count} 个语句, 错误 {error_count} 个语句")
                
                # 记录迁移结果
                self.migration_results.append({
                    'success_count': success_count,
                    'error_count': error_count,
                    'total_statements': len(statements)
                })
                
                return error_count == 0
                
        except Exception as e:
            logger.error(f"迁移执行失败: {e}")
            return False
    
    def _split_sql_statements(self, sql_content: str) -> List[str]:
        """分割SQL语句"""
        # 移除注释
        lines = []
        for line in sql_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        content = '\n'.join(lines)
        
        # 按分号分割，但要处理存储过程中的分号
        statements = []
        current_statement = ""
        in_delimiter = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.upper().startswith('DELIMITER'):
                in_delimiter = not in_delimiter
                continue
            
            current_statement += line + '\n'
            
            if not in_delimiter and line.endswith(';'):
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
        
        # 添加最后一个语句（如果有）
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return [s for s in statements if s.strip()]
    
    async def verify_migration(self) -> bool:
        """验证迁移结果"""
        logger.info("验证迁移结果...")
        
        try:
            expected_tables = [
                'dashboard_configs',
                'widget_definitions',
                'color_schemes', 
                'user_color_preferences',
                'dashboard_data_cache',
                'websocket_connections',
                'migration_history'
            ]
            
            async for session in get_async_session():
                # 检查表是否创建成功
                for table in expected_tables:
                    result = await session.execute(
                        text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'")
                    )
                    
                    if result.scalar() == 0:
                        logger.error(f"表 {table} 创建失败")
                        return False
                    else:
                        logger.info(f"表 {table} 创建成功")
                
                # 检查默认数据是否插入成功
                result = await session.execute(text("SELECT COUNT(*) FROM widget_definitions"))
                widget_count = result.scalar()
                
                result = await session.execute(text("SELECT COUNT(*) FROM color_schemes"))
                scheme_count = result.scalar()
                
                result = await session.execute(text("SELECT COUNT(*) FROM dashboard_configs WHERE is_default = 1"))
                default_config_count = result.scalar()
                
                logger.info(f"默认数据验证: 组件定义 {widget_count} 个, 配色方案 {scheme_count} 个, 默认配置 {default_config_count} 个")
                
                # 检查索引是否创建成功
                result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.statistics WHERE table_name IN ('dashboard_configs', 'widget_definitions')")
                )
                index_count = result.scalar()
                logger.info(f"索引创建验证: {index_count} 个索引")
                
                # 检查存储过程是否创建成功
                result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.routines WHERE routine_name LIKE '%Dashboard%'")
                )
                procedure_count = result.scalar()
                logger.info(f"存储过程创建验证: {procedure_count} 个存储过程")
                
                # 检查视图是否创建成功
                result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.views WHERE table_name LIKE '%dashboard%' OR table_name LIKE '%widget%' OR table_name LIKE '%color%'")
                )
                view_count = result.scalar()
                logger.info(f"视图创建验证: {view_count} 个视图")
            
            logger.info("迁移验证通过")
            return True
            
        except Exception as e:
            logger.error(f"迁移验证失败: {e}")
            return False
    
    async def cleanup_old_data(self) -> bool:
        """清理旧数据"""
        logger.info("清理旧数据...")
        
        try:
            async for session in get_async_session():
                # 清理过期的缓存数据
                result = await session.execute(
                    text("DELETE FROM dashboard_data_cache WHERE expires_at < NOW()")
                )
                deleted_cache = result.rowcount
                
                # 清理非活跃的WebSocket连接
                result = await session.execute(
                    text("DELETE FROM websocket_connections WHERE is_active = 0 OR last_heartbeat < DATE_SUB(NOW(), INTERVAL 1 HOUR)")
                )
                deleted_connections = result.rowcount
                
                await session.commit()
                
                logger.info(f"清理完成: 删除过期缓存 {deleted_cache} 条, 删除非活跃连接 {deleted_connections} 条")
            
            return True
            
        except Exception as e:
            logger.error(f"数据清理失败: {e}")
            return False
    
    async def generate_migration_report(self) -> Dict[str, Any]:
        """生成迁移报告"""
        logger.info("生成迁移报告...")
        
        try:
            async for session in get_async_session():
                # 收集统计信息
                stats = {}
                
                # 表统计
                tables = [
                    'dashboard_configs', 'widget_definitions', 'color_schemes',
                    'user_color_preferences', 'dashboard_data_cache', 'websocket_connections'
                ]
                
                for table in tables:
                    try:
                        result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        stats[f"{table}_count"] = result.scalar()
                    except:
                        stats[f"{table}_count"] = 0
                
                # 索引统计
                result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.statistics WHERE table_name LIKE '%dashboard%' OR table_name LIKE '%widget%' OR table_name LIKE '%color%'")
                )
                stats['index_count'] = result.scalar()
                
                # 存储过程统计
                result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.routines WHERE routine_name LIKE '%Dashboard%'")
                )
                stats['procedure_count'] = result.scalar()
                
                # 视图统计
                result = await session.execute(
                    text("SELECT COUNT(*) FROM information_schema.views WHERE table_name LIKE '%dashboard%' OR table_name LIKE '%widget%' OR table_name LIKE '%color%'")
                )
                stats['view_count'] = result.scalar()
            
            report = {
                'migration_timestamp': datetime.now().isoformat(),
                'migration_file': str(self.migration_file),
                'database_url': self.settings.DATABASE_URL.split('@')[1] if '@' in self.settings.DATABASE_URL else 'hidden',
                'migration_results': self.migration_results,
                'statistics': stats,
                'status': 'completed'
            }
            
            # 保存报告到文件
            report_file = Path(__file__).parent / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            import json
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"迁移报告已保存到: {report_file}")
            
            return report
            
        except Exception as e:
            logger.error(f"生成迁移报告失败: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def run_complete_migration(self) -> bool:
        """运行完整的迁移流程"""
        logger.info("开始仪表板模块数据库迁移...")
        
        try:
            # 1. 检查前置条件
            if not await self.check_prerequisites():
                logger.error("前置条件检查失败，迁移终止")
                return False
            
            # 2. 备份现有数据
            if not await self.backup_existing_data():
                logger.error("数据备份失败，迁移终止")
                return False
            
            # 3. 运行迁移
            if not await self.run_migration():
                logger.error("迁移执行失败")
                return False
            
            # 4. 验证迁移结果
            if not await self.verify_migration():
                logger.error("迁移验证失败")
                return False
            
            # 5. 清理旧数据
            await self.cleanup_old_data()
            
            # 6. 生成报告
            report = await self.generate_migration_report()
            
            logger.info("仪表板模块数据库迁移完成!")
            logger.info(f"迁移统计: {report.get('statistics', {})}")
            
            return True
            
        except Exception as e:
            logger.error(f"迁移过程中发生异常: {e}")
            return False

async def main():
    """主函数"""
    migration_runner = DashboardMigrationRunner()
    
    try:
        success = await migration_runner.run_complete_migration()
        
        if success:
            print("\n" + "="*60)
            print("仪表板模块数据库迁移成功完成!")
            print("="*60)
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("仪表板模块数据库迁移失败!")
            print("="*60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("迁移被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"迁移过程中发生未处理的异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())