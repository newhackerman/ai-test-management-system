"""
添加项目管理模块新表

Revision ID: 009_add_project_tables
Revises: 005_add_project_tables
Create Date: 2024-12-20 11:00:00.000000

本迁移脚本添加项目管理模块的新表结构，包括：
1. project_members表（项目成员管理）
2. project_tasks表（任务管理）
3. project_milestones表（里程碑管理）
4. work_logs表（工作日志）
5. project_risks表（项目风险管理）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '009_add_project_tables'
down_revision = '005_add_project_tables'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构"""
    
    # 1. 创建项目成员表
    op.create_table('project_members',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True, comment='成员关系ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        
        # 角色和权限
        sa.Column('role_in_project', sa.Enum('ADMIN', 'PROJECT_MANAGER', 'REQUIREMENT_MANAGER', 'DESIGNER', 
                                           'ARCHITECT', 'DEVELOPER', 'TESTER', 'DEVOPS', 'THIRD_PARTY'), 
                 nullable=False, comment='项目内角色'),
        sa.Column('allocation_percentage', sa.DECIMAL(5, 2), default=100.00, comment='参与度百分比'),
        sa.Column('hourly_rate', sa.DECIMAL(8, 2), comment='小时费率'),
        
        # 时间管理
        sa.Column('join_date', sa.Date(), nullable=False, comment='加入日期'),
        sa.Column('leave_date', sa.Date(), comment='离开日期'),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'ON_LEAVE'), default='ACTIVE', comment='成员状态'),
        
        # 技能和职责
        sa.Column('skills', sa.JSON(), comment='技能标签'),
        sa.Column('responsibilities', sa.Text(), comment='职责描述'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('project_id', 'user_id', name='uk_project_user'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='项目成员表'
    )
    
    # 创建项目成员表索引
    op.create_index('idx_project_members_project_id', 'project_members', ['project_id'])
    op.create_index('idx_project_members_user_id', 'project_members', ['user_id'])
    op.create_index('idx_project_members_role', 'project_members', ['role_in_project'])
    op.create_index('idx_project_members_status', 'project_members', ['status'])
    
    # 2. 创建任务表
    op.create_table('project_tasks',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True, comment='任务ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('task_code', sa.String(50), comment='任务编码'),
        sa.Column('task_name', sa.String(200), nullable=False, comment='任务名称'),
        sa.Column('description', sa.Text(), comment='任务描述'),
        
        # 任务分类
        sa.Column('task_type', sa.Enum('REQUIREMENT_ANALYSIS', 'TEST_DESIGN', 'TEST_EXECUTION', 
                                     'AUTOMATION_DEVELOPMENT', 'PERFORMANCE_TEST', 'SECURITY_TEST', 
                                     'ENVIRONMENT_SETUP', 'DOCUMENTATION'), 
                 nullable=False, comment='任务类型'),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT'), 
                 default='MEDIUM', comment='任务优先级'),
        sa.Column('status', sa.Enum('TODO', 'ASSIGNED', 'IN_PROGRESS', 'ON_HOLD', 'BLOCKED', 
                                  'PENDING_REVIEW', 'COMPLETED', 'CANCELLED'), 
                 default='TODO', comment='任务状态'),
        
        # 人员分配
        sa.Column('assignee_id', sa.BigInteger(), comment='执行人ID'),
        sa.Column('reporter_id', sa.BigInteger(), comment='报告人ID'),
        sa.Column('reviewer_id', sa.BigInteger(), comment='审核人ID'),
        
        # 时间管理
        sa.Column('planned_start_date', sa.Date(), comment='计划开始日期'),
        sa.Column('planned_end_date', sa.Date(), comment='计划结束日期'),
        sa.Column('actual_start_date', sa.Date(), comment='实际开始日期'),
        sa.Column('actual_end_date', sa.Date(), comment='实际结束日期'),
        
        # 工时管理
        sa.Column('estimated_hours', sa.DECIMAL(6, 2), comment='预估工时'),
        sa.Column('actual_hours', sa.DECIMAL(6, 2), default=0.00, comment='实际工时'),
        sa.Column('remaining_hours', sa.DECIMAL(6, 2), comment='剩余工时'),
        
        # 依赖关系
        sa.Column('parent_task_id', sa.BigInteger(), comment='父任务ID'),
        sa.Column('dependency_tasks', sa.JSON(), comment='依赖任务ID列表'),
        
        # 质量管理
        sa.Column('acceptance_criteria', sa.Text(), comment='验收标准'),
        sa.Column('test_case_count', sa.Integer(), default=0, comment='关联测试用例数'),
        sa.Column('defect_count', sa.Integer(), default=0, comment='发现缺陷数'),
        
        # 元数据
        sa.Column('tags', sa.JSON(), comment='任务标签'),
        sa.Column('attachments', sa.JSON(), comment='附件信息'),
        
        # 审计字段
        sa.Column('created_by', sa.BigInteger(), nullable=False, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='项目任务表'
    )
    
    # 创建任务表索引
    op.create_index('idx_project_tasks_project_id', 'project_tasks', ['project_id'])
    op.create_index('idx_project_tasks_assignee_id', 'project_tasks', ['assignee_id'])
    op.create_index('idx_project_tasks_status', 'project_tasks', ['status'])
    op.create_index('idx_project_tasks_type', 'project_tasks', ['task_type'])
    op.create_index('idx_project_tasks_priority', 'project_tasks', ['priority'])
    op.create_index('idx_project_tasks_parent', 'project_tasks', ['parent_task_id'])
    
    # 3. 创建里程碑表
    op.create_table('project_milestones',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True, comment='里程碑ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('milestone_name', sa.String(200), nullable=False, comment='里程碑名称'),
        sa.Column('description', sa.Text(), comment='里程碑描述'),
        
        # 里程碑类型
        sa.Column('milestone_type', sa.Enum('REQUIREMENT', 'DESIGN', 'EXECUTION', 'DELIVERY'), 
                 nullable=False, comment='里程碑类型'),
        
        # 时间管理
        sa.Column('planned_date', sa.Date(), nullable=False, comment='计划日期'),
        sa.Column('actual_date', sa.Date(), comment='实际日期'),
        
        # 状态管理
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'OVERDUE', 'CANCELLED'), 
                 default='PENDING', comment='里程碑状态'),
        
        # 交付物
        sa.Column('deliverables', sa.JSON(), comment='交付物清单'),
        sa.Column('acceptance_criteria', sa.Text(), comment='验收标准'),
        
        # 负责人
        sa.Column('owner_id', sa.BigInteger(), nullable=False, comment='负责人ID'),
        
        # 依赖关系
        sa.Column('dependency_milestones', sa.JSON(), comment='依赖里程碑ID列表'),
        
        # 审计字段
        sa.Column('created_by', sa.BigInteger(), nullable=False, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='项目里程碑表'
    )
    
    # 创建里程碑表索引
    op.create_index('idx_project_milestones_project_id', 'project_milestones', ['project_id'])
    op.create_index('idx_project_milestones_owner_id', 'project_milestones', ['owner_id'])
    op.create_index('idx_project_milestones_status', 'project_milestones', ['status'])
    op.create_index('idx_project_milestones_type', 'project_milestones', ['milestone_type'])
    op.create_index('idx_project_milestones_planned_date', 'project_milestones', ['planned_date'])
    
    # 4. 创建工作日志表
    op.create_table('work_logs',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True, comment='工作日志ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('task_id', sa.BigInteger(), comment='任务ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        
        # 工时信息
        sa.Column('work_date', sa.Date(), nullable=False, comment='工作日期'),
        sa.Column('hours_worked', sa.DECIMAL(4, 2), nullable=False, comment='工作小时数'),
        sa.Column('work_type', sa.Enum('DEVELOPMENT', 'TESTING', 'ANALYSIS', 'DESIGN', 'MEETING', 
                                     'DOCUMENTATION', 'OTHER'), 
                 nullable=False, comment='工作类型'),
        
        # 工作内容
        sa.Column('description', sa.Text(), nullable=False, comment='工作描述'),
        sa.Column('achievements', sa.Text(), comment='工作成果'),
        sa.Column('issues_encountered', sa.Text(), comment='遇到的问题'),
        
        # 状态
        sa.Column('status', sa.Enum('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED'), 
                 default='DRAFT', comment='日志状态'),
        sa.Column('approved_by', sa.BigInteger(), comment='审批人ID'),
        sa.Column('approved_at', sa.DateTime(), comment='审批时间'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['project_tasks.id'], ondelete='SET NULL'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='工作日志表'
    )
    
    # 创建工作日志表索引
    op.create_index('idx_work_logs_project_id', 'work_logs', ['project_id'])
    op.create_index('idx_work_logs_task_id', 'work_logs', ['task_id'])
    op.create_index('idx_work_logs_user_id', 'work_logs', ['user_id'])
    op.create_index('idx_work_logs_work_date', 'work_logs', ['work_date'])
    op.create_index('idx_work_logs_status', 'work_logs', ['status'])
    
    # 5. 创建项目风险表
    op.create_table('project_risks',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True, comment='风险ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('risk_name', sa.String(200), nullable=False, comment='风险名称'),
        sa.Column('description', sa.Text(), nullable=False, comment='风险描述'),
        
        # 风险分类
        sa.Column('risk_category', sa.Enum('SCHEDULE', 'QUALITY', 'RESOURCE', 'TECHNICAL', 'EXTERNAL'), 
                 nullable=False, comment='风险类别'),
        sa.Column('risk_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'), 
                 nullable=False, comment='风险等级'),
        
        # 概率和影响
        sa.Column('probability', sa.DECIMAL(3, 2), nullable=False, comment='发生概率(0.00-1.00)'),
        sa.Column('impact_score', sa.Integer(), nullable=False, comment='影响评分(1-10)'),
        sa.Column('risk_score', sa.DECIMAL(4, 2), comment='风险评分(计算得出)'),
        
        # 应对策略
        sa.Column('mitigation_strategy', sa.Enum('AVOID', 'MITIGATE', 'TRANSFER', 'ACCEPT'), 
                 nullable=False, comment='应对策略'),
        sa.Column('mitigation_plan', sa.Text(), comment='缓解计划'),
        sa.Column('contingency_plan', sa.Text(), comment='应急计划'),
        
        # 状态管理
        sa.Column('status', sa.Enum('IDENTIFIED', 'ANALYZING', 'MITIGATING', 'MONITORING', 'CLOSED'), 
                 default='IDENTIFIED', comment='风险状态'),
        
        # 负责人
        sa.Column('owner_id', sa.BigInteger(), nullable=False, comment='风险负责人ID'),
        
        # 时间信息
        sa.Column('identified_date', sa.Date(), nullable=False, comment='识别日期'),
        sa.Column('target_resolution_date', sa.Date(), comment='目标解决日期'),
        sa.Column('actual_resolution_date', sa.Date(), comment='实际解决日期'),
        
        # 审计字段
        sa.Column('created_by', sa.BigInteger(), nullable=False, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), comment='更新人ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='项目风险表'
    )
    
    # 创建项目风险表索引
    op.create_index('idx_project_risks_project_id', 'project_risks', ['project_id'])
    op.create_index('idx_project_risks_owner_id', 'project_risks', ['owner_id'])
    op.create_index('idx_project_risks_status', 'project_risks', ['status'])
    op.create_index('idx_project_risks_category', 'project_risks', ['risk_category'])
    op.create_index('idx_project_risks_level', 'project_risks', ['risk_level'])
    op.create_index('idx_project_risks_identified_date', 'project_risks', ['identified_date'])
    
    # 6. 添加复合索引优化查询性能
    op.create_index('idx_project_tasks_project_status', 'project_tasks', ['project_id', 'status'])
    op.create_index('idx_project_tasks_assignee_status', 'project_tasks', ['assignee_id', 'status'])
    op.create_index('idx_work_logs_user_date', 'work_logs', ['user_id', 'work_date'])
    op.create_index('idx_project_milestones_project_status', 'project_milestones', ['project_id', 'status'])
    op.create_index('idx_project_risks_project_status', 'project_risks', ['project_id', 'status'])


def downgrade():
    """降级数据库结构"""
    
    # 删除复合索引
    op.drop_index('idx_project_risks_project_status', table_name='project_risks')
    op.drop_index('idx_project_milestones_project_status', table_name='project_milestones')
    op.drop_index('idx_work_logs_user_date', table_name='work_logs')
    op.drop_index('idx_project_tasks_assignee_status', table_name='project_tasks')
    op.drop_index('idx_project_tasks_project_status', table_name='project_tasks')
    
    # 删除项目风险表
    op.drop_index('idx_project_risks_identified_date', table_name='project_risks')
    op.drop_index('idx_project_risks_level', table_name='project_risks')
    op.drop_index('idx_project_risks_category', table_name='project_risks')
    op.drop_index('idx_project_risks_status', table_name='project_risks')
    op.drop_index('idx_project_risks_owner_id', table_name='project_risks')
    op.drop_index('idx_project_risks_project_id', table_name='project_risks')
    op.drop_table('project_risks')
    
    # 删除工作日志表
    op.drop_index('idx_work_logs_status', table_name='work_logs')
    op.drop_index('idx_work_logs_work_date', table_name='work_logs')
    op.drop_index('idx_work_logs_user_id', table_name='work_logs')
    op.drop_index('idx_work_logs_task_id', table_name='work_logs')
    op.drop_index('idx_work_logs_project_id', table_name='work_logs')
    op.drop_table('work_logs')
    
    # 删除里程碑表
    op.drop_index('idx_project_milestones_planned_date', table_name='project_milestones')
    op.drop_index('idx_project_milestones_type', table_name='project_milestones')
    op.drop_index('idx_project_milestones_status', table_name='project_milestones')
    op.drop_index('idx_project_milestones_owner_id', table_name='project_milestones')
    op.drop_index('idx_project_milestones_project_id', table_name='project_milestones')
    op.drop_table('project_milestones')
    
    # 删除任务表
    op.drop_index('idx_project_tasks_parent', table_name='project_tasks')
    op.drop_index('idx_project_tasks_priority', table_name='project_tasks')
    op.drop_index('idx_project_tasks_type', table_name='project_tasks')
    op.drop_index('idx_project_tasks_status', table_name='project_tasks')
    op.drop_index('idx_project_tasks_assignee_id', table_name='project_tasks')
    op.drop_index('idx_project_tasks_project_id', table_name='project_tasks')
    op.drop_table('project_tasks')
    
    # 删除项目成员表
    op.drop_index('idx_project_members_status', table_name='project_members')
    op.drop_index('idx_project_members_role', table_name='project_members')
    op.drop_index('idx_project_members_user_id', table_name='project_members')
    op.drop_index('idx_project_members_project_id', table_name='project_members')
    op.drop_table('project_members')