"""
初始化配置管理模块基础数据

Revision ID: 004_init_config_data
Revises: 003_create_config_tables
Create Date: 2024-08-23
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '004_init_config_data'
down_revision = '003_create_config_tables'
branch_labels = None
depends_on = None


def upgrade():
    """初始化配置管理模块基础数据"""
    
    # 获取当前时间
    now = datetime.now()
    
    # 初始化环境数据
    environments_table = sa.table(
        'sys_environment',
        sa.column('env_name'),
        sa.column('env_code'),
        sa.column('description'),
        sa.column('is_active'),
        sa.column('is_default'),
        sa.column('sort_order'),
        sa.column('created_at'),
        sa.column('updated_at'),
        sa.column('created_by')
    )
    
    op.bulk_insert(environments_table, [
        {
            'env_name': '开发环境',
            'env_code': 'DEV',
            'description': '开发人员本地开发环境，配置灵活，支持调试',
            'is_active': True,
            'is_default': False,
            'sort_order': 1,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'env_name': '测试环境',
            'env_code': 'TEST',
            'description': '功能测试和集成测试环境，接近生产，数据隔离',
            'is_active': True,
            'is_default': False,
            'sort_order': 2,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'env_name': '生产环境',
            'env_code': 'PROD',
            'description': '正式生产服务环境，高安全性，高可用性',
            'is_active': True,
            'is_default': True,
            'sort_order': 3,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        }
    ])
    
    # 初始化配置分组数据
    config_groups_table = sa.table(
        'sys_config_group',
        sa.column('group_name'),
        sa.column('group_code'),
        sa.column('parent_id'),
        sa.column('level'),
        sa.column('path'),
        sa.column('sort_order'),
        sa.column('description'),
        sa.column('icon'),
        sa.column('color'),
        sa.column('is_system'),
        sa.column('is_enabled'),
        sa.column('created_at'),
        sa.column('updated_at'),
        sa.column('created_by')
    )
    
    op.bulk_insert(config_groups_table, [
        # 一级分组
        {
            'group_name': '系统配置',
            'group_code': 'system',
            'parent_id': 0,
            'level': 1,
            'path': 'system',
            'sort_order': 1,
            'description': '系统级配置参数',
            'icon': 'system',
            'color': '#1890ff',
            'is_system': True,
            'is_enabled': True,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'group_name': '应用配置',
            'group_code': 'application',
            'parent_id': 0,
            'level': 1,
            'path': 'application',
            'sort_order': 2,
            'description': '应用程序相关配置',
            'icon': 'application',
            'color': '#52c41a',
            'is_system': False,
            'is_enabled': True,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'group_name': '业务配置',
            'group_code': 'business',
            'parent_id': 0,
            'level': 1,
            'path': 'business',
            'sort_order': 3,
            'description': '业务逻辑相关配置',
            'icon': 'business',
            'color': '#722ed1',
            'is_system': False,
            'is_enabled': True,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'group_name': '第三方服务',
            'group_code': 'third_party',
            'parent_id': 0,
            'level': 1,
            'path': 'third_party',
            'sort_order': 4,
            'description': '第三方服务集成配置',
            'icon': 'third_party',
            'color': '#fa8c16',
            'is_system': False,
            'is_enabled': True,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        }
    ])
    
    # 插入一些示例配置
    configs_table = sa.table(
        'sys_config',
        sa.column('config_key'),
        sa.column('config_value'),
        sa.column('config_type'),
        sa.column('group_id'),
        sa.column('environment'),
        sa.column('description'),
        sa.column('default_value'),
        sa.column('example_value'),
        sa.column('is_core'),
        sa.column('is_enabled'),
        sa.column('is_encrypted'),
        sa.column('is_required'),
        sa.column('sort_order'),
        sa.column('created_at'),
        sa.column('updated_at'),
        sa.column('created_by')
    )
    
    op.bulk_insert(configs_table, [
        # 系统配置示例
        {
            'config_key': 'system.app.name',
            'config_value': 'AI自动化测试管理系统',
            'config_type': 'STRING',
            'group_id': 1,  # 系统配置分组
            'environment': 'PROD',
            'description': '应用程序名称',
            'default_value': 'AI自动化测试管理系统',
            'example_value': 'AI自动化测试管理系统',
            'is_core': False,
            'is_enabled': True,
            'is_encrypted': False,
            'is_required': True,
            'sort_order': 1,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'config_key': 'system.app.version',
            'config_value': '1.0.0',
            'config_type': 'STRING',
            'group_id': 1,
            'environment': 'PROD',
            'description': '应用程序版本号',
            'default_value': '1.0.0',
            'example_value': '1.0.0',
            'is_core': False,
            'is_enabled': True,
            'is_encrypted': False,
            'is_required': True,
            'sort_order': 2,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'config_key': 'system.debug.enabled',
            'config_value': 'false',
            'config_type': 'BOOLEAN',
            'group_id': 1,
            'environment': 'PROD',
            'description': '是否启用调试模式',
            'default_value': 'false',
            'example_value': 'true',
            'is_core': True,
            'is_enabled': True,
            'is_encrypted': False,
            'is_required': True,
            'sort_order': 3,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'config_key': 'system.max_upload_size',
            'config_value': '10485760',
            'config_type': 'INTEGER',
            'description': '最大上传文件大小（字节）',
            'default_value': '10485760',
            'example_value': '10485760',
            'group_id': 1,
            'environment': 'PROD',
            'is_core': False,
            'is_enabled': True,
            'is_encrypted': False,
            'is_required': True,
            'sort_order': 4,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        # 应用配置示例
        {
            'config_key': 'app.database.url',
            'config_value': 'mysql://localhost:3306/test_db',
            'config_type': 'URL',
            'group_id': 2,  # 应用配置分组
            'environment': 'PROD',
            'description': '数据库连接URL',
            'default_value': 'mysql://localhost:3306/test_db',
            'example_value': 'mysql://user:pass@host:port/dbname',
            'is_core': True,
            'is_enabled': True,
            'is_encrypted': True,
            'is_required': True,
            'sort_order': 1,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        },
        {
            'config_key': 'app.jwt.secret',
            'config_value': 'your-secret-key-here',
            'config_type': 'PASSWORD',
            'group_id': 2,
            'environment': 'PROD',
            'description': 'JWT密钥',
            'default_value': 'your-secret-key-here',
            'example_value': 'abcd1234efgh5678',
            'is_core': True,
            'is_enabled': True,
            'is_encrypted': True,
            'is_required': True,
            'sort_order': 2,
            'created_at': now,
            'updated_at': now,
            'created_by': 1
        }
    ])
    
    print("配置管理模块基础数据初始化完成")


def downgrade():
    """删除配置管理模块基础数据"""
    op.execute("DELETE FROM sys_config WHERE created_by = 1")
    op.execute("DELETE FROM sys_config_group WHERE created_by = 1")
    op.execute("DELETE FROM sys_environment WHERE created_by = 1")
    
    print("配置管理模块基础数据删除完成")