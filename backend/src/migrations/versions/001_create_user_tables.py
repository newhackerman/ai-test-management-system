"""创建用户管理相关表

Revision ID: 001
Revises: 
Create Date: 2023-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建用户表
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='用户ID'),
        sa.Column('username', sa.String(length=50), nullable=False, comment='用户名'),
        sa.Column('email', sa.String(length=100), nullable=False, comment='邮箱地址'),
        sa.Column('password_hash', sa.String(length=255), nullable=False, comment='密码哈希'),
        sa.Column('salt', sa.String(length=32), nullable=False, comment='密码盐值'),
        sa.Column('first_name', sa.String(length=50), nullable=True, comment='名'),
        sa.Column('last_name', sa.String(length=50), nullable=True, comment='姓'),
        sa.Column('full_name', sa.String(length=100), nullable=False, comment='全名'),
        sa.Column('phone', sa.String(length=20), nullable=True, comment='手机号'),
        sa.Column('avatar_url', sa.String(length=500), nullable=True, comment='头像URL'),
        sa.Column('status', mysql.ENUM('ACTIVE', 'INACTIVE', 'DISABLED', 'LOCKED', 'PENDING', 'DELETED'), 
                  default='ACTIVE', nullable=False, comment='用户状态'),
        sa.Column('is_email_verified', sa.Boolean(), default=False, nullable=False, comment='邮箱是否已验证'),
        sa.Column('is_phone_verified', sa.Boolean(), default=False, nullable=False, comment='手机号是否已验证'),
        sa.Column('failed_login_attempts', sa.Integer(), default=0, nullable=False, comment='登录失败次数'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True, comment='最后登录时间'),
        sa.Column('last_login_ip', sa.String(length=45), nullable=True, comment='最后登录IP'),
        sa.Column('locked_until', sa.DateTime(), nullable=True, comment='锁定截止时间'),
        sa.Column('password_changed_at', sa.DateTime(), nullable=True, comment='密码修改时间'),
        sa.Column('mfa_enabled', sa.Boolean(), default=False, nullable=False, comment='是否启用多因素认证'),
        sa.Column('mfa_secret', sa.String(length=32), nullable=True, comment='MFA密钥'),
        sa.Column('mfa_backup_codes', sa.Text(), nullable=True, comment='MFA备用代码'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_users_created_by'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name='fk_users_updated_by'),
        comment='用户表'
    )
    
    # 创建角色表
    op.create_table(
        'roles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='角色ID'),
        sa.Column('name', sa.String(length=50), nullable=False, comment='角色名称'),
        sa.Column('code', sa.String(length=50), nullable=False, comment='角色代码'),
        sa.Column('description', sa.Text(), nullable=True, comment='角色描述'),
        sa.Column('is_system_role', sa.Boolean(), default=False, nullable=False, comment='是否系统角色'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False, comment='是否激活'),
        sa.Column('priority', sa.Integer(), default=0, nullable=False, comment='优先级'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code'),
        comment='角色表'
    )
    
    # 创建权限表
    op.create_table(
        'permissions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='权限ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='权限名称'),
        sa.Column('code', sa.String(length=100), nullable=False, comment='权限代码'),
        sa.Column('module', sa.String(length=50), nullable=False, comment='所属模块'),
        sa.Column('action', sa.String(length=50), nullable=False, comment='操作类型'),
        sa.Column('resource', sa.String(length=100), nullable=True, comment='资源标识'),
        sa.Column('description', sa.Text(), nullable=True, comment='权限描述'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        comment='权限表'
    )
    
    # 创建用户角色关联表
    op.create_table(
        'user_roles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='关联ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        sa.Column('role_id', sa.BigInteger(), nullable=False, comment='角色ID'),
        sa.Column('assigned_by', sa.Integer(), nullable=True, comment='分配人ID'),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, comment='分配时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_user_roles_user_id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE', name='fk_user_roles_role_id'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], name='fk_user_roles_assigned_by'),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_roles_user_role'),
        comment='用户角色关联表'
    )
    
    # 创建角色权限关联表
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='关联ID'),
        sa.Column('role_id', sa.BigInteger(), nullable=False, comment='角色ID'),
        sa.Column('permission_id', sa.BigInteger(), nullable=False, comment='权限ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE', name='fk_role_permissions_role_id'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE', name='fk_role_permissions_permission_id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permissions_role_permission'),
        comment='角色权限关联表'
    )
    
    # 创建用户会话表
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='会话ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        sa.Column('session_token', sa.String(length=255), nullable=False, comment='会话令牌'),
        sa.Column('refresh_token', sa.String(length=255), nullable=True, comment='刷新令牌'),
        sa.Column('ip_address', sa.String(length=45), nullable=False, comment='IP地址'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='用户代理'),
        sa.Column('device_info', sa.JSON(), nullable=True, comment='设备信息'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False, comment='是否活跃'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, comment='过期时间'),
        sa.Column('last_activity', sa.DateTime(), nullable=False, comment='最后活动时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_user_sessions_user_id'),
        sa.UniqueConstraint('session_token', name='uq_user_sessions_session_token'),
        sa.UniqueConstraint('refresh_token', name='uq_user_sessions_refresh_token'),
        comment='用户会话表'
    )
    
    # 创建审计日志表
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='日志ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='操作用户ID'),
        sa.Column('action', mysql.ENUM('LOGIN', 'LOGOUT', 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 
                                     'PERMISSION_CHANGE', 'PASSWORD_CHANGE', 'MFA_ENABLE', 
                                     'MFA_DISABLE', 'ROLE_ASSIGN', 'ROLE_REMOVE'), 
                  nullable=False, comment='操作类型'),
        sa.Column('resource_type', sa.String(length=50), nullable=False, comment='资源类型'),
        sa.Column('resource_id', sa.String(length=100), nullable=True, comment='资源ID'),
        sa.Column('old_values', sa.JSON(), nullable=True, comment='变更前值'),
        sa.Column('new_values', sa.JSON(), nullable=True, comment='变更后值'),
        sa.Column('ip_address', sa.String(length=45), nullable=False, comment='IP地址'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='用户代理'),
        sa.Column('result', mysql.ENUM('SUCCESS', 'FAILURE', 'PARTIAL'), 
                  nullable=False, comment='操作结果'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_audit_logs_user_id'),
        comment='审计日志表'
    )
    
    # 创建索引
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    
    op.create_index('idx_roles_code', 'roles', ['code'])
    op.create_index('idx_roles_is_active', 'roles', ['is_active'])
    
    op.create_index('idx_permissions_code', 'permissions', ['code'])
    op.create_index('idx_permissions_module', 'permissions', ['module'])
    
    op.create_index('idx_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_role_id', 'user_roles', ['role_id'])
    
    op.create_index('idx_role_permissions_role_id', 'role_permissions', ['role_id'])
    op.create_index('idx_role_permissions_permission_id', 'role_permissions', ['permission_id'])
    
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_session_token', 'user_sessions', ['session_token'])
    op.create_index('idx_user_sessions_is_active', 'user_sessions', ['is_active'])
    op.create_index('idx_user_sessions_expires_at', 'user_sessions', ['expires_at'])
    
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('idx_audit_logs_result', 'audit_logs', ['result'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_audit_logs_created_at', 'audit_logs')
    op.drop_index('idx_audit_logs_result', 'audit_logs')
    op.drop_index('idx_audit_logs_resource_type', 'audit_logs')
    op.drop_index('idx_audit_logs_action', 'audit_logs')
    op.drop_index('idx_audit_logs_user_id', 'audit_logs')
    
    op.drop_index('idx_user_sessions_expires_at', 'user_sessions')
    op.drop_index('idx_user_sessions_is_active', 'user_sessions')
    op.drop_index('idx_user_sessions_session_token', 'user_sessions')
    op.drop_index('idx_user_sessions_user_id', 'user_sessions')
    
    op.drop_index('idx_role_permissions_permission_id', 'role_permissions')
    op.drop_index('idx_role_permissions_role_id', 'role_permissions')
    
    op.drop_index('idx_user_roles_role_id', 'user_roles')
    op.drop_index('idx_user_roles_user_id', 'user_roles')
    
    op.drop_index('idx_permissions_module', 'permissions')
    op.drop_index('idx_permissions_code', 'permissions')
    
    op.drop_index('idx_roles_is_active', 'roles')
    op.drop_index('idx_roles_code', 'roles')
    
    op.drop_index('idx_users_created_at', 'users')
    op.drop_index('idx_users_status', 'users')
    op.drop_index('idx_users_email', 'users')
    op.drop_index('idx_users_username', 'users')
    
    # 删除表
    op.drop_table('audit_logs')
    op.drop_table('user_sessions')
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')