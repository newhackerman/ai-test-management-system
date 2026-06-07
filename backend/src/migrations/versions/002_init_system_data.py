"""初始化系统角色和权限数据

Revision ID: 002
Revises: 001
Create Date: 2023-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 插入系统角色
    roles = [
        {'name': '超级管理员', 'code': 'SUPER_ADMIN', 'description': '系统超级管理员，拥有所有权限', 'is_system_role': True, 'priority': 0},
        {'name': '项目管理员', 'code': 'PROJECT_ADMIN', 'description': '项目管理员，负责项目管理', 'is_system_role': True, 'priority': 1},
        {'name': '需求管理人员', 'code': 'REQUIREMENT_ADMIN', 'description': '需求管理人员，负责需求管理', 'is_system_role': True, 'priority': 2},
        {'name': '设计人员', 'code': 'DESIGNER', 'description': '设计人员，负责设计工作', 'is_system_role': True, 'priority': 3},
        {'name': '架构师', 'code': 'ARCHITECT', 'description': '架构师，负责系统架构设计', 'is_system_role': True, 'priority': 4},
        {'name': '开发人员', 'code': 'DEVELOPER', 'description': '开发人员，负责代码开发', 'is_system_role': True, 'priority': 5},
        {'name': '测试人员', 'code': 'TESTER', 'description': '测试人员，负责测试工作', 'is_system_role': True, 'priority': 6},
        {'name': '运维人员', 'code': 'DEVOPS', 'description': '运维人员，负责系统运维', 'is_system_role': True, 'priority': 7},
        {'name': '第三方人员', 'code': 'THIRD_PARTY', 'description': '第三方人员，有限权限', 'is_system_role': True, 'priority': 8},
    ]
    
    # 插入角色数据
    op.bulk_insert(
        sa.table(
            'roles',
            sa.column('name', sa.String),
            sa.column('code', sa.String),
            sa.column('description', sa.Text),
            sa.column('is_system_role', sa.Boolean),
            sa.column('priority', sa.Integer),
            sa.column('is_active', sa.Boolean),
        ),
        roles
    )
    
    # 插入系统权限
    permissions = [
        # 用户管理权限
        {'name': '查看用户', 'code': 'user:view', 'module': 'user', 'action': 'view', 'description': '查看用户信息'},
        {'name': '创建用户', 'code': 'user:create', 'module': 'user', 'action': 'create', 'description': '创建新用户'},
        {'name': '更新用户', 'code': 'user:update', 'module': 'user', 'action': 'update', 'description': '更新用户信息'},
        {'name': '删除用户', 'code': 'user:delete', 'module': 'user', 'action': 'delete', 'description': '删除用户'},
        {'name': '分配用户角色', 'code': 'user:assign_role', 'module': 'user', 'action': 'assign_role', 'description': '为用户分配角色'},
        {'name': '重置用户密码', 'code': 'user:reset_password', 'module': 'user', 'action': 'reset_password', 'description': '重置用户密码'},
        
        # 角色管理权限
        {'name': '查看角色', 'code': 'role:view', 'module': 'role', 'action': 'view', 'description': '查看角色信息'},
        {'name': '创建角色', 'code': 'role:create', 'module': 'role', 'action': 'create', 'description': '创建新角色'},
        {'name': '更新角色', 'code': 'role:update', 'module': 'role', 'action': 'update', 'description': '更新角色信息'},
        {'name': '删除角色', 'code': 'role:delete', 'module': 'role', 'action': 'delete', 'description': '删除角色'},
        {'name': '分配角色权限', 'code': 'role:assign_permission', 'module': 'role', 'action': 'assign_permission', 'description': '为角色分配权限'},
        
        # 权限管理权限
        {'name': '查看权限', 'code': 'permission:view', 'module': 'permission', 'action': 'view', 'description': '查看权限信息'},
        {'name': '创建权限', 'code': 'permission:create', 'module': 'permission', 'action': 'create', 'description': '创建新权限'},
        {'name': '更新权限', 'code': 'permission:update', 'module': 'permission', 'action': 'update', 'description': '更新权限信息'},
        {'name': '删除权限', 'code': 'permission:delete', 'module': 'permission', 'action': 'delete', 'description': '删除权限'},
        
        # 审计日志权限
        {'name': '查看审计日志', 'code': 'audit:view', 'module': 'audit', 'action': 'view', 'description': '查看审计日志'},
        {'name': '导出审计日志', 'code': 'audit:export', 'module': 'audit', 'action': 'export', 'description': '导出审计日志'},
        
        # 系统管理权限
        {'name': '系统配置', 'code': 'system:config', 'module': 'system', 'action': 'config', 'description': '系统配置管理'},
        {'name': '系统监控', 'code': 'system:monitor', 'module': 'system', 'action': 'monitor', 'description': '系统监控'},
        {'name': '数据备份', 'code': 'system:backup', 'module': 'system', 'action': 'backup', 'description': '数据备份'},
        {'name': '数据恢复', 'code': 'system:restore', 'module': 'system', 'action': 'restore', 'description': '数据恢复'},
    ]
    
    # 插入权限数据
    op.bulk_insert(
        sa.table(
            'permissions',
            sa.column('name', sa.String),
            sa.column('code', sa.String),
            sa.column('module', sa.String),
            sa.column('action', sa.String),
            sa.column('description', sa.Text),
        ),
        permissions
    )
    
    # 获取角色和权限ID，建立关联关系
    connection = op.get_bind()
    
    # 获取超级管理员角色ID
    super_admin_id = connection.execute(
        sa.text("SELECT id FROM roles WHERE code = 'SUPER_ADMIN'")
    ).scalar()
    
    # 获取所有权限ID
    permission_ids = connection.execute(
        sa.text("SELECT id FROM permissions")
    ).fetchall()
    
    # 为超级管理员角色分配所有权限
    role_permissions = [
        {'role_id': super_admin_id, 'permission_id': permission_id[0]}
        for permission_id in permission_ids
    ]
    
    # 插入角色权限关联数据
    op.bulk_insert(
        sa.table(
            'role_permissions',
            sa.column('role_id', sa.BigInteger),
            sa.column('permission_id', sa.BigInteger),
        ),
        role_permissions
    )


def downgrade() -> None:
    # 删除角色权限关联
    op.execute("DELETE FROM role_permissions")
    
    # 删除权限
    op.execute("DELETE FROM permissions")
    
    # 删除角色
    op.execute("DELETE FROM roles")