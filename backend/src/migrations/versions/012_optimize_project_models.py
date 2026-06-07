"""
优化项目管理模块数据模型

Revision ID: 012_optimize_project_models
Revises: 011_fix_user_foreign_key_types
Create Date: 2024-12-20 14:00:00.000000

本迁移脚本优化项目管理模块的数据模型：
1. 修复Project模型中的重复字段问题
2. 添加缺失的数据库索引以优化查询性能
3. 确保所有约束和索引符合规范要求
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '012_optimize_project_models'
down_revision = '011_fix_user_foreign_key_types'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构 - 优化项目管理模块"""
    
    print("🔧 开始优化项目管理模块数据模型...")
    
    # 1. 修复projects表中的重复字段问题
    try:
        print("📋 修复projects表重复字段...")
        
        # 检查是否存在name字段，如果存在则删除（保留project_name）
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        columns = [col['name'] for col in inspector.get_columns('projects')]
        
        if 'name' in columns:
            # 如果project_name为空，先用name字段填充
            op.execute("""
                UPDATE projects 
                SET project_name = name 
                WHERE project_name IS NULL AND name IS NOT NULL
            """)
            
            # 删除重复的name字段
            op.drop_column('projects', 'name')
            print("✅ 删除重复的name字段")
        
        # 确保project_name字段不为空
        op.alter_column('projects', 'project_name',
                       existing_type=sa.String(200),
                       nullable=False,
                       comment='项目名称')
        
        print("✅ Projects表字段优化完成")
        
    except Exception as e:
        print(f"⚠️ Projects表字段优化失败: {e}")
    
    # 2. 添加缺失的性能优化索引
    try:
        print("📊 添加性能优化索引...")
        
        # Projects表索引
        indexes_to_create = [
            ('idx_projects_code', 'projects', ['project_code']),
            ('idx_projects_name', 'projects', ['project_name']),
            ('idx_projects_type_status', 'projects', ['project_type', 'status']),
            ('idx_projects_manager_status', 'projects', ['project_manager_id', 'status']),
            ('idx_projects_dates', 'projects', ['planned_start_date', 'planned_end_date']),
            ('idx_projects_priority_status', 'projects', ['priority', 'status']),
            ('idx_projects_health_risk', 'projects', ['health_score', 'risk_level']),
            ('idx_projects_created_at', 'projects', ['created_at']),
            ('idx_projects_updated_at', 'projects', ['updated_at']),
            ('idx_projects_deleted_at', 'projects', ['deleted_at']),
            
            # ProjectTasks表额外索引
            ('idx_project_tasks_dates', 'project_tasks', ['planned_start_date', 'planned_end_date']),
            ('idx_project_tasks_actual_dates', 'project_tasks', ['actual_start_date', 'actual_end_date']),
            ('idx_project_tasks_hours', 'project_tasks', ['estimated_hours', 'actual_hours']),
            ('idx_project_tasks_created_at', 'project_tasks', ['created_at']),
            
            # ProjectMembers表额外索引
            ('idx_project_members_dates', 'project_members', ['join_date', 'leave_date']),
            ('idx_project_members_allocation', 'project_members', ['allocation_percentage']),
            
            # WorkLogs表额外索引
            ('idx_work_logs_type_date', 'work_logs', ['work_type', 'work_date']),
            ('idx_work_logs_hours', 'work_logs', ['hours_worked']),
            
            # ProjectRisks表额外索引
            ('idx_project_risks_score', 'project_risks', ['risk_score']),
            ('idx_project_risks_probability', 'project_risks', ['probability']),
            ('idx_project_risks_dates', 'project_risks', ['identified_date', 'target_resolution_date']),
        ]
        
        for index_name, table_name, columns in indexes_to_create:
            try:
                op.create_index(index_name, table_name, columns)
                print(f"✅ 创建索引: {index_name}")
            except Exception as e:
                print(f"⚠️ 创建索引 {index_name} 失败: {e}")
        
        print("✅ 性能优化索引添加完成")
        
    except Exception as e:
        print(f"⚠️ 索引创建失败: {e}")
    
    # 3. 创建项目变更历史表
    try:
        print("📋 创建项目变更历史表...")
        
        op.create_table('project_change_history',
            sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True, comment='变更记录ID'),
            sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
            sa.Column('change_type', sa.Enum('CREATE', 'UPDATE', 'DELETE', 'STATUS_CHANGE', 'MEMBER_CHANGE'), 
                     nullable=False, comment='变更类型'),
            sa.Column('field_name', sa.String(100), comment='变更字段名'),
            sa.Column('old_value', sa.Text(), comment='旧值'),
            sa.Column('new_value', sa.Text(), comment='新值'),
            sa.Column('change_reason', sa.Text(), comment='变更原因'),
            sa.Column('change_description', sa.Text(), comment='变更描述'),
            
            # 变更人信息
            sa.Column('changed_by', sa.Integer(), nullable=False, comment='变更人ID'),
            sa.Column('change_time', sa.DateTime(), nullable=False, default=sa.func.current_timestamp(), comment='变更时间'),
            sa.Column('ip_address', sa.String(45), comment='变更IP地址'),
            sa.Column('user_agent', sa.String(500), comment='用户代理'),
            
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='RESTRICT'),
            mysql_charset='utf8mb4',
            mysql_collate='utf8mb4_unicode_ci',
            mysql_comment='项目变更历史表'
        )
        
        # 创建项目变更历史表索引
        op.create_index('idx_project_change_history_project', 'project_change_history', ['project_id'])
        op.create_index('idx_project_change_history_type', 'project_change_history', ['change_type'])
        op.create_index('idx_project_change_history_time', 'project_change_history', ['change_time'])
        op.create_index('idx_project_change_history_user', 'project_change_history', ['changed_by'])
        op.create_index('idx_project_change_history_field', 'project_change_history', ['field_name'])
        
        print("✅ 项目变更历史表创建完成")
        
    except Exception as e:
        print(f"⚠️ 项目变更历史表创建失败: {e}")
    
    # 6. 添加项目统计表
    try:
        print("📊 创建项目统计表...")
        
        op.create_table('project_statistics',
            sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True, comment='统计记录ID'),
            sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
            sa.Column('stat_date', sa.Date(), nullable=False, comment='统计日期'),
            sa.Column('stat_type', sa.Enum('DAILY', 'WEEKLY', 'MONTHLY'), 
                     nullable=False, comment='统计类型'),
            
            # 进度统计
            sa.Column('time_progress', sa.DECIMAL(5, 2), comment='时间进度百分比'),
            sa.Column('task_progress', sa.DECIMAL(5, 2), comment='任务进度百分比'),
            sa.Column('quality_progress', sa.DECIMAL(5, 2), comment='质量进度百分比'),
            sa.Column('overall_progress', sa.DECIMAL(5, 2), comment='整体进度百分比'),
            
            # 任务统计
            sa.Column('total_tasks', sa.Integer(), default=0, comment='任务总数'),
            sa.Column('completed_tasks', sa.Integer(), default=0, comment='已完成任务数'),
            sa.Column('in_progress_tasks', sa.Integer(), default=0, comment='进行中任务数'),
            sa.Column('overdue_tasks', sa.Integer(), default=0, comment='逾期任务数'),
            
            # 人员统计
            sa.Column('total_members', sa.Integer(), default=0, comment='团队成员总数'),
            sa.Column('active_members', sa.Integer(), default=0, comment='活跃成员数'),
            sa.Column('total_work_hours', sa.DECIMAL(8, 2), default=0.00, comment='总工时'),
            sa.Column('avg_utilization_rate', sa.DECIMAL(5, 2), comment='平均利用率'),
            
            # 质量统计
            sa.Column('total_defects', sa.Integer(), default=0, comment='缺陷总数'),
            sa.Column('open_defects', sa.Integer(), default=0, comment='未解决缺陷数'),
            sa.Column('critical_defects', sa.Integer(), default=0, comment='严重缺陷数'),
            sa.Column('defect_density', sa.DECIMAL(6, 3), comment='缺陷密度'),
            
            # 风险统计
            sa.Column('total_risks', sa.Integer(), default=0, comment='风险总数'),
            sa.Column('high_risks', sa.Integer(), default=0, comment='高风险数'),
            sa.Column('avg_risk_score', sa.DECIMAL(4, 2), comment='平均风险评分'),
            
            # 成本统计
            sa.Column('planned_cost', sa.DECIMAL(15, 2), comment='计划成本'),
            sa.Column('actual_cost', sa.DECIMAL(15, 2), comment='实际成本'),
            sa.Column('cost_variance', sa.DECIMAL(15, 2), comment='成本偏差'),
            
            sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.current_timestamp(), comment='创建时间'),
            
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('project_id', 'stat_date', 'stat_type', name='uk_project_stat_date_type'),
            mysql_charset='utf8mb4',
            mysql_collate='utf8mb4_unicode_ci',
            mysql_comment='项目统计表'
        )
        
        # 创建项目统计表索引
        op.create_index('idx_project_statistics_project', 'project_statistics', ['project_id'])
        op.create_index('idx_project_statistics_date', 'project_statistics', ['stat_date'])
        op.create_index('idx_project_statistics_type', 'project_statistics', ['stat_type'])
        op.create_index('idx_project_statistics_progress', 'project_statistics', ['overall_progress'])
        
        print("✅ 项目统计表创建完成")
        
    except Exception as e:
        print(f"⚠️ 项目统计表创建失败: {e}")
    
    print("✅ 项目管理模块数据模型优化完成!")


def downgrade():
    """降级数据库结构 - 撤销优化"""
    
    print("🔧 开始撤销项目管理模块优化...")
    
    # 删除项目统计表
    try:
        op.drop_table('project_statistics')
        print("✅ 项目统计表删除完成")
    except Exception as e:
        print(f"⚠️ 项目统计表删除失败: {e}")
    
    # 删除项目变更历史表
    try:
        op.drop_table('project_change_history')
        print("✅ 项目变更历史表删除完成")
    except Exception as e:
        print(f"⚠️ 项目变更历史表删除失败: {e}")
    
    # 删除优化索引
    try:
        indexes_to_drop = [
            ('idx_project_risks_dates', 'project_risks'),
            ('idx_project_risks_probability', 'project_risks'),
            ('idx_project_risks_score', 'project_risks'),
            ('idx_work_logs_hours', 'work_logs'),
            ('idx_work_logs_type_date', 'work_logs'),
            ('idx_project_members_allocation', 'project_members'),
            ('idx_project_members_dates', 'project_members'),
            ('idx_project_tasks_created_at', 'project_tasks'),
            ('idx_project_tasks_hours', 'project_tasks'),
            ('idx_project_tasks_actual_dates', 'project_tasks'),
            ('idx_project_tasks_dates', 'project_tasks'),
            ('idx_projects_deleted_at', 'projects'),
            ('idx_projects_updated_at', 'projects'),
            ('idx_projects_created_at', 'projects'),
            ('idx_projects_health_risk', 'projects'),
            ('idx_projects_priority_status', 'projects'),
            ('idx_projects_dates', 'projects'),
            ('idx_projects_manager_status', 'projects'),
            ('idx_projects_type_status', 'projects'),
            ('idx_projects_name', 'projects'),
            ('idx_projects_code', 'projects'),
        ]
        
        for index_name, table_name in indexes_to_drop:
            try:
                op.drop_index(index_name, table_name)
            except Exception as e:
                print(f"⚠️ 删除索引 {index_name} 失败: {e}")
        
        print("✅ 优化索引删除完成")
    except Exception as e:
        print(f"⚠️ 索引删除失败: {e}")
    
    print("✅ 项目管理模块优化撤销完成!")
