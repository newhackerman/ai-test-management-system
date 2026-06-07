"""
添加项目管理模块用户外键约束

Revision ID: 010_add_project_user_foreign_keys
Revises: 009_add_project_management_tables
Create Date: 2024-12-20 12:00:00.000000

本迁移脚本为项目管理模块添加用户外键约束，确保数据完整性：
1. 为projects表添加用户外键约束
2. 为project_members表添加用户外键约束
3. 为project_tasks表添加用户外键约束
4. 为project_milestones表添加用户外键约束
5. 为work_logs表添加用户外键约束
6. 为project_risks表添加用户外键约束
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010_add_project_user_foreign_keys'
down_revision = '009_add_project_management_tables'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构 - 添加用户外键约束"""
    
    # 1. 为projects表添加用户外键约束
    try:
        # 项目经理外键
        op.create_foreign_key(
            'fk_projects_manager',
            'projects', 'users',
            ['project_manager_id'], ['id'],
            ondelete='RESTRICT'
        )
        
        # 测试经理外键
        op.create_foreign_key(
            'fk_projects_test_manager',
            'projects', 'users',
            ['test_manager_id'], ['id'],
            ondelete='SET NULL'
        )
        
        # 创建人外键
        op.create_foreign_key(
            'fk_projects_creator',
            'projects', 'users',
            ['created_by'], ['id'],
            ondelete='RESTRICT'
        )
        
        # 更新人外键
        op.create_foreign_key(
            'fk_projects_updater',
            'projects', 'users',
            ['updated_by'], ['id'],
            ondelete='SET NULL'
        )
        
        print("✅ Projects表用户外键约束添加成功")
        
    except Exception as e:
        print(f"⚠️ Projects表外键约束可能已存在: {e}")
    
    # 2. 为project_members表添加用户外键约束
    try:
        # 用户外键
        op.create_foreign_key(
            'fk_project_members_user',
            'project_members', 'users',
            ['user_id'], ['id'],
            ondelete='CASCADE'
        )
        
        print("✅ ProjectMembers表用户外键约束添加成功")
        
    except Exception as e:
        print(f"⚠️ ProjectMembers表外键约束可能已存在: {e}")
    
    # 3. 为project_tasks表添加用户外键约束
    try:
        # 执行人外键
        op.create_foreign_key(
            'fk_project_tasks_assignee',
            'project_tasks', 'users',
            ['assignee_id'], ['id'],
            ondelete='SET NULL'
        )
        
        # 报告人外键
        op.create_foreign_key(
            'fk_project_tasks_reporter',
            'project_tasks', 'users',
            ['reporter_id'], ['id'],
            ondelete='SET NULL'
        )
        
        # 审核人外键
        op.create_foreign_key(
            'fk_project_tasks_reviewer',
            'project_tasks', 'users',
            ['reviewer_id'], ['id'],
            ondelete='SET NULL'
        )
        
        # 创建人外键
        op.create_foreign_key(
            'fk_project_tasks_creator',
            'project_tasks', 'users',
            ['created_by'], ['id'],
            ondelete='RESTRICT'
        )
        
        # 更新人外键
        op.create_foreign_key(
            'fk_project_tasks_updater',
            'project_tasks', 'users',
            ['updated_by'], ['id'],
            ondelete='SET NULL'
        )
        
        print("✅ ProjectTasks表用户外键约束添加成功")
        
    except Exception as e:
        print(f"⚠️ ProjectTasks表外键约束可能已存在: {e}")
    
    # 4. 为project_milestones表添加用户外键约束
    try:
        # 负责人外键
        op.create_foreign_key(
            'fk_project_milestones_owner',
            'project_milestones', 'users',
            ['owner_id'], ['id'],
            ondelete='RESTRICT'
        )
        
        # 创建人外键
        op.create_foreign_key(
            'fk_project_milestones_creator',
            'project_milestones', 'users',
            ['created_by'], ['id'],
            ondelete='RESTRICT'
        )
        
        # 更新人外键
        op.create_foreign_key(
            'fk_project_milestones_updater',
            'project_milestones', 'users',
            ['updated_by'], ['id'],
            ondelete='SET NULL'
        )
        
        print("✅ ProjectMilestones表用户外键约束添加成功")
        
    except Exception as e:
        print(f"⚠️ ProjectMilestones表外键约束可能已存在: {e}")
    
    # 5. 为work_logs表添加用户外键约束
    try:
        # 用户外键
        op.create_foreign_key(
            'fk_work_logs_user',
            'work_logs', 'users',
            ['user_id'], ['id'],
            ondelete='CASCADE'
        )
        
        # 审批人外键
        op.create_foreign_key(
            'fk_work_logs_approver',
            'work_logs', 'users',
            ['approved_by'], ['id'],
            ondelete='SET NULL'
        )
        
        print("✅ WorkLogs表用户外键约束添加成功")
        
    except Exception as e:
        print(f"⚠️ WorkLogs表外键约束可能已存在: {e}")
    
    # 6. 为project_risks表添加用户外键约束
    try:
        # 负责人外键
        op.create_foreign_key(
            'fk_project_risks_owner',
            'project_risks', 'users',
            ['owner_id'], ['id'],
            ondelete='RESTRICT'
        )
        
        # 创建人外键
        op.create_foreign_key(
            'fk_project_risks_creator',
            'project_risks', 'users',
            ['created_by'], ['id'],
            ondelete='RESTRICT'
        )
        
        # 更新人外键
        op.create_foreign_key(
            'fk_project_risks_updater',
            'project_risks', 'users',
            ['updated_by'], ['id'],
            ondelete='SET NULL'
        )
        
        print("✅ ProjectRisks表用户外键约束添加成功")
        
    except Exception as e:
        print(f"⚠️ ProjectRisks表外键约束可能已存在: {e}")
    
    # 7. 添加额外的性能优化索引
    try:
        # 为经常查询的用户相关字段添加索引
        op.create_index('idx_projects_manager_status', 'projects', ['project_manager_id', 'status'])
        op.create_index('idx_tasks_assignee_status_priority', 'project_tasks', ['assignee_id', 'status', 'priority'])
        op.create_index('idx_work_logs_user_project_date', 'work_logs', ['user_id', 'project_id', 'work_date'])
        
        print("✅ 性能优化索引添加成功")
        
    except Exception as e:
        print(f"⚠️ 性能优化索引可能已存在: {e}")


def downgrade():
    """降级数据库结构 - 删除用户外键约束"""
    
    # 删除性能优化索引
    try:
        op.drop_index('idx_work_logs_user_project_date', table_name='work_logs')
        op.drop_index('idx_tasks_assignee_status_priority', table_name='project_tasks')
        op.drop_index('idx_projects_manager_status', table_name='projects')
    except Exception as e:
        print(f"⚠️ 删除性能优化索引时出错: {e}")
    
    # 删除project_risks表用户外键约束
    try:
        op.drop_constraint('fk_project_risks_updater', 'project_risks', type_='foreignkey')
        op.drop_constraint('fk_project_risks_creator', 'project_risks', type_='foreignkey')
        op.drop_constraint('fk_project_risks_owner', 'project_risks', type_='foreignkey')
    except Exception as e:
        print(f"⚠️ 删除ProjectRisks外键约束时出错: {e}")
    
    # 删除work_logs表用户外键约束
    try:
        op.drop_constraint('fk_work_logs_approver', 'work_logs', type_='foreignkey')
        op.drop_constraint('fk_work_logs_user', 'work_logs', type_='foreignkey')
    except Exception as e:
        print(f"⚠️ 删除WorkLogs外键约束时出错: {e}")
    
    # 删除project_milestones表用户外键约束
    try:
        op.drop_constraint('fk_project_milestones_updater', 'project_milestones', type_='foreignkey')
        op.drop_constraint('fk_project_milestones_creator', 'project_milestones', type_='foreignkey')
        op.drop_constraint('fk_project_milestones_owner', 'project_milestones', type_='foreignkey')
    except Exception as e:
        print(f"⚠️ 删除ProjectMilestones外键约束时出错: {e}")
    
    # 删除project_tasks表用户外键约束
    try:
        op.drop_constraint('fk_project_tasks_updater', 'project_tasks', type_='foreignkey')
        op.drop_constraint('fk_project_tasks_creator', 'project_tasks', type_='foreignkey')
        op.drop_constraint('fk_project_tasks_reviewer', 'project_tasks', type_='foreignkey')
        op.drop_constraint('fk_project_tasks_reporter', 'project_tasks', type_='foreignkey')
        op.drop_constraint('fk_project_tasks_assignee', 'project_tasks', type_='foreignkey')
    except Exception as e:
        print(f"⚠️ 删除ProjectTasks外键约束时出错: {e}")
    
    # 删除project_members表用户外键约束
    try:
        op.drop_constraint('fk_project_members_user', 'project_members', type_='foreignkey')
    except Exception as e:
        print(f"⚠️ 删除ProjectMembers外键约束时出错: {e}")
    
    # 删除projects表用户外键约束
    try:
        op.drop_constraint('fk_projects_updater', 'projects', type_='foreignkey')
        op.drop_constraint('fk_projects_creator', 'projects', type_='foreignkey')
        op.drop_constraint('fk_projects_test_manager', 'projects', type_='foreignkey')
        op.drop_constraint('fk_projects_manager', 'projects', type_='foreignkey')
    except Exception as e:
        print(f"⚠️ 删除Projects外键约束时出错: {e}")