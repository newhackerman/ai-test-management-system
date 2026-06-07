#!/usr/bin/env python3
"""
用户角色权限管理增强 - 简化版数据库迁移执行脚本
"""
import os
import sys
import logging
from pathlib import Path
import pymysql
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'aitest'),
        password=os.getenv('DB_PASSWORD', 'AItestdb123'),
        database=os.getenv('DB_NAME', 'aitestdb'),
        charset='utf8mb4',
        autocommit=False
    )


def run_migration():
    """执行用户角色权限管理增强迁移"""
    try:
        logger.info("开始执行用户角色权限管理增强迁移...")
        
        # 读取迁移SQL文件
        migration_file = Path(__file__).parent / "user_role_permission_enhancement_migration.sql"
        
        if not migration_file.exists():
            logger.error(f"迁移文件不存在: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # 分割SQL语句
        sql_statements = []
        current_statement = ""
        
        for line in migration_sql.split('\n'):
            line = line.strip()
            
            # 跳过空行和注释行
            if not line or line.startswith('--'):
                continue
            
            current_statement += line + " "
            
            # 检查是否是完整的SQL语句
            if line.endswith(';'):
                sql_statements.append(current_statement.strip())
                current_statement = ""
        
        # 执行迁移
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            logger.info(f"准备执行 {len(sql_statements)} 个SQL语句...")
            
            for i, sql_statement in enumerate(sql_statements, 1):
                if sql_statement.strip():
                    try:
                        logger.info(f"执行第 {i} 个SQL语句...")
                        cursor.execute(sql_statement)
                        logger.info(f"第 {i} 个SQL语句执行成功")
                    except Exception as e:
                        # 对于某些可能已存在的表或字段，忽略错误
                        if any(keyword in str(e).lower() for keyword in [
                            'already exists', 'duplicate', 'table exists', 'column exists'
                        ]):
                            logger.warning(f"第 {i} 个SQL语句跳过（已存在）: {e}")
                        else:
                            logger.error(f"第 {i} 个SQL语句执行失败: {e}")
                            raise
            
            conn.commit()
            logger.info("用户角色权限管理增强迁移执行完成！")
            return True
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        
    except Exception as e:
        logger.error(f"迁移执行失败: {e}")
        return False


def verify_migration():
    """验证迁移结果"""
    try:
        logger.info("开始验证迁移结果...")
        
        # 需要验证的表
        tables_to_verify = [
            'permission_groups',
            'permission_group_items',
            'role_groups',
            'role_group_items',
            'role_templates',
            'role_approvals',
            'user_permissions',
            'data_permissions',
            'user_data_permissions',
            'audit_logs_enhanced',
            'user_sessions_enhanced',
            'permission_cache',
            'security_events',
            'notification_configs'
        ]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            for table_name in tables_to_verify:
                try:
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        logger.info(f"✓ 表 {table_name} 创建成功")
                    else:
                        logger.warning(f"✗ 表 {table_name} 未找到")
                except Exception as e:
                    logger.error(f"✗ 验证表 {table_name} 失败: {e}")
            
            # 验证角色表的新字段
            try:
                cursor.execute("DESCRIBE roles")
                columns = [row[0] for row in cursor.fetchall()]
                
                new_columns = [
                    'inherit_parent_permissions',
                    'permission_policy',
                    'data_scope',
                    'data_scope_config'
                ]
                
                for column in new_columns:
                    if column in columns:
                        logger.info(f"✓ 角色表字段 {column} 添加成功")
                    else:
                        logger.warning(f"✗ 角色表字段 {column} 未找到")
                        
            except Exception as e:
                logger.error(f"验证角色表字段失败: {e}")
            
            # 验证权限表的新字段
            try:
                cursor.execute("DESCRIBE permissions")
                columns = [row[0] for row in cursor.fetchall()]
                
                if 'conditions' in columns:
                    logger.info("✓ 权限表字段 conditions 添加成功")
                else:
                    logger.warning("✗ 权限表字段 conditions 未找到")
                    
            except Exception as e:
                logger.error(f"验证权限表字段失败: {e}")
        
        finally:
            cursor.close()
            conn.close()
        
        logger.info("迁移结果验证完成！")
        return True
        
    except Exception as e:
        logger.error(f"验证迁移结果失败: {e}")
        return False


def initialize_default_data():
    """初始化默认数据"""
    try:
        logger.info("开始初始化默认数据...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查是否已有默认权限
            cursor.execute("SELECT COUNT(*) FROM permissions")
            permission_count = cursor.fetchone()[0]
            
            if permission_count == 0:
                logger.info("初始化默认权限...")
                
                # 默认权限列表
                default_permissions = [
                    # 用户管理权限
                    ("user:view", "查看用户", "user_management", "view", "查看用户列表和详情"),
                    ("user:create", "创建用户", "user_management", "create", "创建新用户账户"),
                    ("user:edit", "编辑用户", "user_management", "edit", "编辑用户信息"),
                    ("user:delete", "删除用户", "user_management", "delete", "删除用户账户"),
                    ("user:assign_role", "分配角色", "user_management", "assign_role", "为用户分配角色"),
                    ("user:reset_password", "重置密码", "user_management", "reset_password", "重置用户密码"),
                    ("user:lock", "锁定用户", "user_management", "lock", "锁定/解锁用户账户"),
                    
                    # 角色管理权限
                    ("role:view", "查看角色", "role_management", "view", "查看角色列表和详情"),
                    ("role:create", "创建角色", "role_management", "create", "创建新角色"),
                    ("role:edit", "编辑角色", "role_management", "edit", "编辑角色信息"),
                    ("role:delete", "删除角色", "role_management", "delete", "删除角色"),
                    ("role:assign_permission", "分配权限", "role_management", "assign_permission", "为角色分配权限"),
                    
                    # 权限管理权限
                    ("permission:view", "查看权限", "permission_management", "view", "查看权限列表"),
                    ("permission:create", "创建权限", "permission_management", "create", "创建新权限"),
                    ("permission:edit", "编辑权限", "permission_management", "edit", "编辑权限信息"),
                    ("permission:delete", "删除权限", "permission_management", "delete", "删除权限"),
                    
                    # 项目管理权限
                    ("project:view", "查看项目", "project_management", "view", "查看项目信息"),
                    ("project:create", "创建项目", "project_management", "create", "创建新项目"),
                    ("project:edit", "编辑项目", "project_management", "edit", "编辑项目信息"),
                    ("project:delete", "删除项目", "project_management", "delete", "删除项目"),
                    ("project:config", "项目配置", "project_management", "config", "配置项目设置"),
                    
                    # 需求管理权限
                    ("requirement:view", "查看需求", "requirement_management", "view", "查看需求信息"),
                    ("requirement:create", "创建需求", "requirement_management", "create", "创建新需求"),
                    ("requirement:edit", "编辑需求", "requirement_management", "edit", "编辑需求信息"),
                    ("requirement:delete", "删除需求", "requirement_management", "delete", "删除需求"),
                    ("requirement:review", "需求审核", "requirement_management", "review", "审核需求"),
                    
                    # 测试管理权限
                    ("test:view", "查看测试", "test_management", "view", "查看测试用例和结果"),
                    ("test:create", "创建测试", "test_management", "create", "创建测试用例"),
                    ("test:edit", "编辑测试", "test_management", "edit", "编辑测试用例"),
                    ("test:delete", "删除测试", "test_management", "delete", "删除测试用例"),
                    ("test:execute", "执行测试", "test_management", "execute", "执行测试用例"),
                    ("test:report", "测试报告", "test_management", "report", "生成测试报告"),
                    
                    # 系统配置权限
                    ("system:view", "查看系统配置", "system_config", "view", "查看系统配置"),
                    ("system:edit", "修改系统配置", "system_config", "edit", "修改系统配置"),
                    ("system:backup", "系统备份", "system_config", "backup", "系统数据备份"),
                    ("system:restore", "系统还原", "system_config", "restore", "系统数据还原"),
                    ("system:logs", "查看系统日志", "system_config", "logs", "查看系统日志"),
                    
                    # 审计权限
                    ("audit:view", "查看审计日志", "audit", "view", "查看审计日志"),
                    ("audit:export", "导出审计日志", "audit", "export", "导出审计日志"),
                    ("audit:report", "审计报告", "audit", "report", "生成审计报告"),
                ]
                
                for code, name, module, action, description in default_permissions:
                    cursor.execute("""
                        INSERT IGNORE INTO permissions (code, name, module, action, description, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                    """, (code, name, module, action, description))
                
                logger.info(f"初始化了 {len(default_permissions)} 个默认权限")
            
            # 检查是否已有默认角色
            cursor.execute("SELECT COUNT(*) FROM roles")
            role_count = cursor.fetchone()[0]
            
            if role_count == 0:
                logger.info("初始化默认角色...")
                
                # 创建默认角色
                default_roles = [
                    ('admin', 'Admin（系统管理员）', '拥有系统所有权限，包括用户管理、系统配置、数据备份等', 100, True, True, 'all'),
                    ('project_manager', '项目管理员', '项目全生命周期管理、团队管理、进度控制、资源分配', 90, True, True, 'dept'),
                    ('requirement_manager', '需求管理人员', '需求收集、分析、设计、变更管理、需求追溯', 80, True, True, 'dept'),
                    ('tester', '测试人员', '测试用例设计、测试执行、缺陷管理、测试报告', 70, True, True, 'self'),
                ]
                
                for code, name, description, priority, is_system_role, is_active, data_scope in default_roles:
                    cursor.execute("""
                        INSERT IGNORE INTO roles (code, name, description, priority, is_system_role, is_active, data_scope, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """, (code, name, description, priority, is_system_role, is_active, data_scope))
                
                logger.info("初始化了默认角色")
            
            conn.commit()
        
        finally:
            cursor.close()
            conn.close()
        
        logger.info("默认数据初始化完成！")
        return True
        
    except Exception as e:
        logger.error(f"初始化默认数据失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("用户角色权限管理增强 - 数据库迁移")
    logger.info("=" * 60)
    
    try:
        # 执行迁移
        if not run_migration():
            logger.error("迁移执行失败，退出")
            return False
        
        # 验证迁移结果
        if not verify_migration():
            logger.error("迁移验证失败，退出")
            return False
        
        # 初始化默认数据
        if not initialize_default_data():
            logger.error("默认数据初始化失败，退出")
            return False
        
        logger.info("=" * 60)
        logger.info("用户角色权限管理增强迁移完成！")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        return False


if __name__ == "__main__":
    # 运行迁移
    success = main()
    
    if success:
        print("\n✅ 迁移成功完成！")
        sys.exit(0)
    else:
        print("\n❌ 迁移失败！")
        sys.exit(1)