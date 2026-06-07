"""
创建配置管理模块相关表

Revision ID: 003_create_config_tables
Revises: 002
Create Date: 2024-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '003_create_config_tables'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # 创建配置分组表
    op.create_table(
        'sys_config_group',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('group_name', sa.String(100), nullable=False, comment='分组名称'),
        sa.Column('group_code', sa.String(100), nullable=False, comment='分组代码'),
        sa.Column('parent_id', sa.BigInteger(), default=0, comment='父分组ID'),
        sa.Column('level', sa.Integer(), default=1, comment='分组层级'),
        sa.Column('path', sa.String(500), comment='分组路径'),
        sa.Column('sort_order', sa.Integer(), default=0, comment='排序序号'),
        sa.Column('description', sa.Text(), comment='分组描述'),
        sa.Column('icon', sa.String(100), comment='分组图标'),
        sa.Column('color', sa.String(20), comment='分组颜色'),
        sa.Column('is_system', sa.Boolean(), default=False, nullable=False, comment='是否系统分组'),
        sa.Column('is_enabled', sa.Boolean(), default=True, nullable=False, comment='是否启用'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_code', name='uk_group_code'),
        comment='配置分组表'
    )
    
    # 创建分组表索引
    op.create_index('idx_sys_config_group_parent_id', 'sys_config_group', ['parent_id'])
    op.create_index('idx_sys_config_group_level', 'sys_config_group', ['level'])
    op.create_index('idx_sys_config_group_sort_order', 'sys_config_group', ['sort_order'])
    
    # 创建环境管理表
    op.create_table(
        'sys_environment',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('env_name', sa.String(100), nullable=False, comment='环境名称'),
        sa.Column('env_code', sa.Enum('DEV', 'TEST', 'PROD', name='environment'), 
                 nullable=False, comment='环境代码'),
        sa.Column('description', sa.Text(), comment='环境描述'),
        sa.Column('base_url', sa.String(500), comment='环境基础URL'),
        sa.Column('database_config', sa.JSON(), comment='数据库配置'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False, comment='是否激活'),
        sa.Column('is_default', sa.Boolean(), default=False, nullable=False, comment='是否默认环境'),
        sa.Column('sort_order', sa.Integer(), default=0, comment='排序序号'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('env_code', name='uk_env_code'),
        comment='环境管理表'
    )
    
    # 创建环境表索引
    op.create_index('idx_sys_environment_is_active', 'sys_environment', ['is_active'])
    op.create_index('idx_sys_environment_sort_order', 'sys_environment', ['sort_order'])
    
    # 创建系统配置表
    op.create_table(
        'sys_config',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('config_key', sa.String(200), nullable=False, comment='配置键名'),
        sa.Column('config_value', sa.Text(), comment='配置值'),
        sa.Column('config_type', sa.Enum('STRING', 'INTEGER', 'BOOLEAN', 'JSON', 'PASSWORD', 'URL', 
                                        name='configtype'), default='STRING', nullable=False, comment='配置类型'),
        sa.Column('group_id', sa.BigInteger(), comment='分组ID'),
        sa.Column('environment', sa.Enum('DEV', 'TEST', 'PROD', name='environment'), 
                 default='PROD', nullable=False, comment='环境标识'),
        sa.Column('description', sa.Text(), comment='配置描述'),
        sa.Column('default_value', sa.Text(), comment='默认值'),
        sa.Column('example_value', sa.Text(), comment='示例值'),
        sa.Column('validation_rule', sa.JSON(), comment='验证规则'),
        sa.Column('is_core', sa.Boolean(), default=False, nullable=False, comment='是否核心配置'),
        sa.Column('is_enabled', sa.Boolean(), default=True, nullable=False, comment='是否启用'),
        sa.Column('is_encrypted', sa.Boolean(), default=False, nullable=False, comment='是否加密存储'),
        sa.Column('is_required', sa.Boolean(), default=False, nullable=False, comment='是否必填'),
        sa.Column('tags', sa.JSON(), comment='配置标签'),
        sa.Column('sort_order', sa.Integer(), default=0, comment='排序序号'),
        sa.Column('deleted_at', sa.DateTime(), comment='删除时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key', 'environment', name='uk_config_key_env'),
        sa.ForeignKeyConstraint(['group_id'], ['sys_config_group.id'], ondelete='SET NULL'),
        comment='系统配置表'
    )
    
    # 创建配置表索引
    op.create_index('idx_sys_config_group_id', 'sys_config', ['group_id'])
    op.create_index('idx_sys_config_environment', 'sys_config', ['environment'])
    op.create_index('idx_sys_config_config_type', 'sys_config', ['config_type'])
    op.create_index('idx_sys_config_is_core', 'sys_config', ['is_core'])
    op.create_index('idx_sys_config_created_at', 'sys_config', ['created_at'])
    op.create_index('idx_sys_config_updated_at', 'sys_config', ['updated_at'])
    
    # 创建配置历史表
    op.create_table(
        'sys_config_history',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('config_id', sa.BigInteger(), nullable=False, comment='配置ID'),
        sa.Column('config_key', sa.String(200), nullable=False, comment='配置键名'),
        sa.Column('environment', sa.Enum('DEV', 'TEST', 'PROD', name='environment'), 
                 nullable=False, comment='环境标识'),
        sa.Column('old_value', sa.Text(), comment='变更前值'),
        sa.Column('new_value', sa.Text(), comment='变更后值'),
        sa.Column('change_type', sa.Enum('CREATE', 'UPDATE', 'DELETE', 'ROLLBACK', name='changetype'), 
                 nullable=False, comment='变更类型'),
        sa.Column('change_reason', sa.Text(), comment='变更原因'),
        sa.Column('change_summary', sa.String(500), comment='变更摘要'),
        sa.Column('impact_scope', sa.JSON(), comment='影响范围'),
        sa.Column('operator_id', sa.BigInteger(), comment='操作人ID'),
        sa.Column('operator_ip', sa.String(45), comment='操作IP'),
        sa.Column('user_agent', sa.Text(), comment='用户代理'),
        sa.Column('audit_id', sa.BigInteger(), comment='关联审核ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['config_id'], ['sys_config.id'], ondelete='CASCADE'),
        comment='配置变更历史表'
    )
    
    # 创建历史表索引
    op.create_index('idx_sys_config_history_config_id', 'sys_config_history', ['config_id'])
    op.create_index('idx_sys_config_history_config_key', 'sys_config_history', ['config_key'])
    op.create_index('idx_sys_config_history_environment', 'sys_config_history', ['environment'])
    op.create_index('idx_sys_config_history_change_type', 'sys_config_history', ['change_type'])
    op.create_index('idx_sys_config_history_operator_id', 'sys_config_history', ['operator_id'])
    op.create_index('idx_sys_config_history_created_at', 'sys_config_history', ['created_at'])
    op.create_index('idx_sys_config_history_audit_id', 'sys_config_history', ['audit_id'])
    
    # 创建配置审核表
    op.create_table(
        'sys_config_audit',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('audit_code', sa.String(50), nullable=False, comment='审核编号'),
        sa.Column('config_id', sa.BigInteger(), comment='配置ID'),
        sa.Column('config_key', sa.String(200), nullable=False, comment='配置键名'),
        sa.Column('environment', sa.Enum('DEV', 'TEST', 'PROD', name='environment'), 
                 nullable=False, comment='环境标识'),
        sa.Column('old_value', sa.Text(), comment='变更前值'),
        sa.Column('new_value', sa.Text(), comment='变更后值'),
        sa.Column('change_type', sa.Enum('CREATE', 'UPDATE', 'DELETE', name='changetype'), 
                 nullable=False, comment='变更类型'),
        sa.Column('audit_status', sa.Enum('PENDING', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'CANCELLED', 
                                         name='auditstatus'), default='PENDING', comment='审核状态'),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='priority'), 
                 default='MEDIUM', comment='优先级'),
        sa.Column('apply_user_id', sa.BigInteger(), nullable=False, comment='申请人ID'),
        sa.Column('audit_user_id', sa.BigInteger(), comment='审核人ID'),
        sa.Column('apply_reason', sa.Text(), comment='申请原因'),
        sa.Column('audit_reason', sa.Text(), comment='审核意见'),
        sa.Column('impact_assessment', sa.JSON(), comment='影响评估'),
        sa.Column('risk_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='risklevel'), comment='风险等级'),
        sa.Column('estimated_downtime', sa.Integer(), comment='预估停机时间(分钟)'),
        sa.Column('rollback_plan', sa.Text(), comment='回滚计划'),
        sa.Column('applied_at', sa.DateTime(), comment='申请时间'),
        sa.Column('audited_at', sa.DateTime(), comment='审核时间'),
        sa.Column('executed_at', sa.DateTime(), comment='执行时间'),
        sa.Column('expires_at', sa.DateTime(), comment='过期时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('audit_code', name='uk_audit_code'),
        sa.ForeignKeyConstraint(['config_id'], ['sys_config.id'], ondelete='SET NULL'),
        comment='配置审核表'
    )
    
    # 创建审核表索引
    op.create_index('idx_sys_config_audit_audit_status', 'sys_config_audit', ['audit_status'])
    op.create_index('idx_sys_config_audit_config_key', 'sys_config_audit', ['config_key'])
    op.create_index('idx_sys_config_audit_environment', 'sys_config_audit', ['environment'])
    op.create_index('idx_sys_config_audit_apply_user_id', 'sys_config_audit', ['apply_user_id'])
    op.create_index('idx_sys_config_audit_audit_user_id', 'sys_config_audit', ['audit_user_id'])
    op.create_index('idx_sys_config_audit_applied_at', 'sys_config_audit', ['applied_at'])
    op.create_index('idx_sys_config_audit_priority', 'sys_config_audit', ['priority'])
    
    # 创建配置权限表
    op.create_table(
        'sys_config_permission',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        sa.Column('config_id', sa.BigInteger(), comment='配置ID'),
        sa.Column('group_id', sa.BigInteger(), comment='分组ID'),
        sa.Column('environment', sa.Enum('DEV', 'TEST', 'PROD', name='environment'), comment='环境标识'),
        sa.Column('permission_type', sa.Enum('READ', 'WRITE', 'DELETE', 'AUDIT', name='permissiontype'), 
                 nullable=False, comment='权限类型'),
        sa.Column('granted_by', sa.BigInteger(), comment='授权人ID'),
        sa.Column('granted_at', sa.DateTime(), comment='授权时间'),
        sa.Column('expires_at', sa.DateTime(), comment='过期时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'config_id', 'permission_type', name='uk_user_config_perm'),
        sa.ForeignKeyConstraint(['config_id'], ['sys_config.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['sys_config_group.id'], ondelete='CASCADE'),
        comment='配置权限表'
    )
    
    # 创建权限表索引
    op.create_index('idx_sys_config_permission_user_id', 'sys_config_permission', ['user_id'])
    op.create_index('idx_sys_config_permission_config_id', 'sys_config_permission', ['config_id'])
    op.create_index('idx_sys_config_permission_group_id', 'sys_config_permission', ['group_id'])
    op.create_index('idx_sys_config_permission_environment', 'sys_config_permission', ['environment'])
    op.create_index('idx_sys_config_permission_permission_type', 'sys_config_permission', ['permission_type'])
    
    print("配置管理模块表创建完成")


def downgrade():
    """删除配置管理模块相关表"""
    op.drop_table('sys_config_permission')
    op.drop_table('sys_config_audit')
    op.drop_table('sys_config_history')
    op.drop_table('sys_config')
    op.drop_table('sys_environment')
    op.drop_table('sys_config_group')
    
    print("配置管理模块表删除完成")