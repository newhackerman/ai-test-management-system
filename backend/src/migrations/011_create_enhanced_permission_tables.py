"""
创建增强的权限管理相关数据表
支持zentao风格的角色权限控制和操作审计
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '011_enhanced_permissions'
down_revision = '010_create_lighthouse_results_table'
branch_labels = None
depends_on = None


def upgrade():
    """创建增强的权限管理表"""
    
    # 1. 创建权限组表
    op.create_table(
        'permission_groups',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='权限组ID'),
        sa.Column('code', sa.String(100), nullable=False, comment='权限组代码'),
        sa.Column('name', sa.String(100), nullable=False, comment='权限组名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='权限组描述'),
        sa.Column('color', sa.String(20), nullable=True, comment='显示颜色'),
        sa.Column('icon', sa.String(50), nullable=True, comment='图标'),
        sa.Column('sort_order', sa.Integer(), default=0, nullable=False, comment='排序顺序'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False, comment='是否激活'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_permission_groups_code', 'code'),
        sa.Index('idx_permission_groups_name', 'name'),
        comment='权限组表'
    )
    
    # 2. 创建权限组项目关联表
    op.create_table(
        'permission_group_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='关联ID'),
        sa.Column('group_id', sa.BigInteger(), nullable=False, comment='权限组ID'),
        sa.Column('permission_id', sa.BigInteger(), nullable=False, comment='权限ID'),
        sa.Column('sort_order', sa.Integer(), default=0, nullable=False, comment='排序顺序'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['permission_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.Index('idx_permission_group_items_group', 'group_id'),
        sa.Index('idx_permission_group_items_permission', 'permission_id'),
        comment='权限组项目关联表'
    )
    
    # 3. 创建角色组表
    op.create_table(
        'role_groups',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='角色组ID'),
        sa.Column('code', sa.String(100), nullable=False, comment='角色组代码'),
        sa.Column('name', sa.String(100), nullable=False, comment='角色组名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='角色组描述'),
        sa.Column('color', sa.String(20), nullable=True, comment='显示颜色'),
        sa.Column('icon', sa.String(50), nullable=True, comment='图标'),
        sa.Column('sort_order', sa.Integer(), default=0, nullable=False, comment='排序顺序'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False, comment='是否激活'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_role_groups_code', 'code'),
        sa.Index('idx_role_groups_name', 'name'),
        comment='角色组表'
    )
    
    # 4. 创建角色组项目关联表
    op.create_table(
        'role_group_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='关联ID'),
        sa.Column('group_id', sa.BigInteger(), nullable=False, comment='角色组ID'),
        sa.Column('role_id', sa.BigInteger(), nullable=False, comment='角色ID'),
        sa.Column('sort_order', sa.Integer(), default=0, nullable=False, comment='排序顺序'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['group_id'], ['role_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.Index('idx_role_group_items_group', 'group_id'),
        sa.Index('idx_role_group_items_role', 'role_id'),
        comment='角色组项目关联表'
    )
    
    # 5. 创建角色模板表
    op.create_table(
        'role_templates',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='模板ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='模板名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='模板描述'),
        sa.Column('category', sa.String(50), nullable=True, comment='模板分类'),
        sa.Column('template_data', sa.JSON(), nullable=False, comment='模板数据'),
        sa.Column('is_system_template', sa.Boolean(), default=False, nullable=False, comment='是否系统模板'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False, comment='是否激活'),
        sa.Column('usage_count', sa.Integer(), default=0, nullable=False, comment='使用次数'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后使用时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_role_templates_name', 'name'),
        sa.Index('idx_role_templates_category', 'category'),
        comment='角色模板表'
    )
    
    # 6. 创建角色审批表
    op.create_table(
        'role_approvals',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='审批ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='申请用户ID'),
        sa.Column('role_id', sa.BigInteger(), nullable=False, comment='申请角色ID'),
        sa.Column('action', sa.String(20), nullable=False, comment='操作类型'),
        sa.Column('reason', sa.Text(), nullable=True, comment='申请原因'),
        sa.Column('status', sa.String(20), default='pending', nullable=False, comment='审批状态'),
        sa.Column('approver_id', sa.BigInteger(), nullable=True, comment='审批人ID'),
        sa.Column('approved_at', sa.DateTime(), nullable=True, comment='审批时间'),
        sa.Column('approval_reason', sa.Text(), nullable=True, comment='审批意见'),
        sa.Column('effective_at', sa.DateTime(), nullable=True, comment='生效时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_role_approvals_user', 'user_id'),
        sa.Index('idx_role_approvals_role', 'role_id'),
        sa.Index('idx_role_approvals_status', 'status'),
        sa.Index('idx_role_approvals_approver', 'approver_id'),
        comment='角色审批表'
    )
    
    # 7. 创建用户直接权限表
    op.create_table(
        'user_permissions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='关联ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        sa.Column('permission_id', sa.BigInteger(), nullable=False, comment='权限ID'),
        sa.Column('effect', sa.Enum('ALLOW', 'DENY', name='permission_effect'), default='ALLOW', comment='权限效果'),
        sa.Column('conditions', sa.JSON(), nullable=True, comment='权限条件'),
        sa.Column('granted_by', sa.BigInteger(), nullable=True, comment='授权人'),
        sa.Column('granted_at', sa.DateTime(), nullable=True, comment='授权时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('reason', sa.Text(), nullable=True, comment='授权原因'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_user_permissions_user', 'user_id'),
        sa.Index('idx_user_permissions_permission', 'permission_id'),
        sa.Index('idx_user_permissions_granted_by', 'granted_by'),
        comment='用户直接权限表'
    )
    
    # 8. 创建数据权限表
    op.create_table(
        'data_permissions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='数据权限ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='数据权限名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='权限描述'),
        sa.Column('resource_type', sa.String(50), nullable=False, comment='资源类型'),
        sa.Column('scope_type', sa.String(20), nullable=False, comment='范围类型'),
        sa.Column('scope_value', sa.JSON(), nullable=True, comment='范围值'),
        sa.Column('filter_conditions', sa.JSON(), nullable=True, comment='过滤条件'),
        sa.Column('field_permissions', sa.JSON(), nullable=True, comment='字段权限'),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False, comment='是否激活'),
        sa.Column('priority', sa.Integer(), default=0, nullable=False, comment='优先级'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_data_permissions_resource_type', 'resource_type'),
        sa.Index('idx_data_permissions_scope_type', 'scope_type'),
        comment='数据权限表'
    )
    
    # 9. 创建用户数据权限关联表
    op.create_table(
        'user_data_permissions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='关联ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        sa.Column('data_permission_id', sa.BigInteger(), nullable=False, comment='数据权限ID'),
        sa.Column('granted_by', sa.BigInteger(), nullable=True, comment='授权人'),
        sa.Column('granted_at', sa.DateTime(), nullable=True, comment='授权时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['data_permission_id'], ['data_permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.Index('idx_user_data_permissions_user', 'user_id'),
        sa.Index('idx_user_data_permissions_data_permission', 'data_permission_id'),
        comment='用户数据权限关联表'
    )
    
    # 10. 增强现有角色表的字段
    op.add_column('roles', sa.Column('inherit_parent_permissions', sa.Boolean(), default=True, nullable=False, comment='是否继承父角色权限'))
    op.add_column('roles', sa.Column('permission_policy', sa.String(20), default='merge', nullable=False, comment='权限策略'))
    op.add_column('roles', sa.Column('data_scope', sa.String(20), default='all', nullable=False, comment='数据范围'))
    op.add_column('roles', sa.Column('data_scope_config', sa.JSON(), nullable=True, comment='数据范围配置'))
    
    # 11. 增强现有权限表的字段
    op.add_column('permissions', sa.Column('conditions', sa.JSON(), nullable=True, comment='权限条件'))
    
    # 12. 增强现有角色权限关联表的字段
    op.add_column('role_permissions', sa.Column('conditions', sa.JSON(), nullable=True, comment='权限条件'))
    op.add_column('role_permissions', sa.Column('granted_by', sa.BigInteger(), nullable=True, comment='授权人'))
    op.add_column('role_permissions', sa.Column('granted_at', sa.DateTime(), nullable=True, comment='授权时间'))
    op.add_column('role_permissions', sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'))
    
    # 添加外键约束
    op.create_foreign_key(
        'fk_role_permissions_granted_by',
        'role_permissions',
        'users',
        ['granted_by'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    """删除增强的权限管理表"""
    
    # 删除外键约束
    op.drop_constraint('fk_role_permissions_granted_by', 'role_permissions', type_='foreignkey')
    
    # 删除新增的列
    op.drop_column('role_permissions', 'expires_at')
    op.drop_column('role_permissions', 'granted_at')
    op.drop_column('role_permissions', 'granted_by')
    op.drop_column('role_permissions', 'conditions')
    
    op.drop_column('permissions', 'conditions')
    
    op.drop_column('roles', 'data_scope_config')
    op.drop_column('roles', 'data_scope')
    op.drop_column('roles', 'permission_policy')
    op.drop_column('roles', 'inherit_parent_permissions')
    
    # 删除新建的表
    op.drop_table('user_data_permissions')
    op.drop_table('data_permissions')
    op.drop_table('user_permissions')
    op.drop_table('role_approvals')
    op.drop_table('role_templates')
    op.drop_table('role_group_items')
    op.drop_table('role_groups')
    op.drop_table('permission_group_items')
    op.drop_table('permission_groups')