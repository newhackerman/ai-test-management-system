"""
添加项目数据表

Revision ID: 005_add_project_tables
Revises: 004_add_ai_permissions
Create Date: 2024-12-19 15:30:00.000000

本迁移脚本创建项目数据相关的表结构，用于AI助手的项目数据同步功能。
包括项目、需求、测试用例、缺陷、项目指标等表。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '005_add_project_tables'
down_revision = '004_add_ai_permissions'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构"""
    
    # 创建项目表
    op.create_table('projects',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='项目名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='项目描述'),
        sa.Column('project_type', sa.String(50), nullable=True, comment='项目类型'),
        sa.Column('status', sa.Enum('PLANNING', 'ACTIVE', 'ON_HOLD', 'COMPLETED', 'CANCELLED'), 
                 nullable=True, default='PLANNING', comment='项目状态'),
        
        # 项目基本信息
        sa.Column('start_date', sa.DateTime(), nullable=True, comment='开始日期'),
        sa.Column('end_date', sa.DateTime(), nullable=True, comment='结束日期'),
        sa.Column('budget', sa.Float(), nullable=True, comment='项目预算'),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'), 
                 nullable=True, default='MEDIUM', comment='优先级'),
        
        # 团队信息
        sa.Column('project_manager_id', sa.BigInteger(), nullable=True, comment='项目经理ID'),
        sa.Column('team_size', sa.Integer(), nullable=True, comment='团队规模'),
        sa.Column('team_members', sa.JSON(), nullable=True, comment='团队成员列表'),
        
        # 项目配置
        sa.Column('project_config', sa.JSON(), nullable=True, comment='项目配置'),
        sa.Column('custom_fields', sa.JSON(), nullable=True, comment='自定义字段'),
        
        # 统计信息
        sa.Column('total_requirements', sa.Integer(), nullable=True, default=0, comment='需求总数'),
        sa.Column('total_test_cases', sa.Integer(), nullable=True, default=0, comment='测试用例总数'),
        sa.Column('total_defects', sa.Integer(), nullable=True, default=0, comment='缺陷总数'),
        
        # 质量指标
        sa.Column('requirements_coverage', sa.Float(), nullable=True, comment='需求覆盖率'),
        sa.Column('test_coverage', sa.Float(), nullable=True, comment='测试覆盖率'),
        sa.Column('defect_density', sa.Float(), nullable=True, comment='缺陷密度'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='项目表'
    )
    
    # 创建项目表索引
    op.create_index('idx_projects_status', 'projects', ['status'])
    op.create_index('idx_projects_priority', 'projects', ['priority'])
    op.create_index('idx_projects_manager', 'projects', ['project_manager_id'])
    op.create_index('idx_projects_created_at', 'projects', ['created_at'])
    op.create_index('idx_projects_updated_at', 'projects', ['updated_at'])
    
    # 创建需求表
    op.create_table('requirements',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='需求ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('title', sa.String(300), nullable=False, comment='需求标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='需求描述'),
        sa.Column('requirement_type', sa.String(50), nullable=True, comment='需求类型'),
        
        # 需求属性
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'), 
                 nullable=True, default='MEDIUM', comment='优先级'),
        sa.Column('status', sa.Enum('DRAFT', 'REVIEW', 'APPROVED', 'IMPLEMENTED', 'TESTED', 'CLOSED'), 
                 nullable=True, default='DRAFT', comment='需求状态'),
        sa.Column('complexity', sa.Enum('LOW', 'MEDIUM', 'HIGH'), nullable=True, comment='复杂度'),
        
        # 验收标准
        sa.Column('acceptance_criteria', sa.JSON(), nullable=True, comment='验收标准'),
        sa.Column('business_value', sa.Text(), nullable=True, comment='业务价值'),
        sa.Column('stakeholder', sa.String(100), nullable=True, comment='干系人'),
        
        # 依赖关系
        sa.Column('dependencies', sa.JSON(), nullable=True, comment='依赖关系'),
        sa.Column('related_requirements', sa.JSON(), nullable=True, comment='相关需求'),
        
        # 质量指标
        sa.Column('completeness_score', sa.Float(), nullable=True, comment='完整性评分'),
        sa.Column('clarity_score', sa.Float(), nullable=True, comment='清晰度评分'),
        sa.Column('testability_score', sa.Float(), nullable=True, comment='可测试性评分'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='需求表'
    )
    
    # 创建需求表索引
    op.create_index('idx_requirements_project_id', 'requirements', ['project_id'])
    op.create_index('idx_requirements_status', 'requirements', ['status'])
    op.create_index('idx_requirements_priority', 'requirements', ['priority'])
    op.create_index('idx_requirements_type', 'requirements', ['requirement_type'])
    op.create_index('idx_requirements_created_at', 'requirements', ['created_at'])
    
    # 创建测试用例表
    op.create_table('test_cases',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='测试用例ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('requirement_id', sa.BigInteger(), nullable=True, comment='关联需求ID'),
        sa.Column('title', sa.String(300), nullable=False, comment='测试用例标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='测试用例描述'),
        
        # 测试用例属性
        sa.Column('test_type', sa.String(50), nullable=True, comment='测试类型'),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'), 
                 nullable=True, default='MEDIUM', comment='优先级'),
        sa.Column('status', sa.Enum('DRAFT', 'REVIEW', 'APPROVED', 'ACTIVE', 'DEPRECATED'), 
                 nullable=True, default='DRAFT', comment='状态'),
        
        # 测试步骤和数据
        sa.Column('test_steps', sa.JSON(), nullable=True, comment='测试步骤'),
        sa.Column('test_data', sa.JSON(), nullable=True, comment='测试数据'),
        sa.Column('expected_result', sa.Text(), nullable=True, comment='预期结果'),
        
        # 自动化信息
        sa.Column('is_automated', sa.Boolean(), nullable=True, default=False, comment='是否自动化'),
        sa.Column('automation_script', sa.Text(), nullable=True, comment='自动化脚本'),
        sa.Column('automation_framework', sa.String(100), nullable=True, comment='自动化框架'),
        
        # 执行统计
        sa.Column('execution_count', sa.Integer(), nullable=True, default=0, comment='执行次数'),
        sa.Column('pass_count', sa.Integer(), nullable=True, default=0, comment='通过次数'),
        sa.Column('fail_count', sa.Integer(), nullable=True, default=0, comment='失败次数'),
        sa.Column('last_execution_date', sa.DateTime(), nullable=True, comment='最后执行日期'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='SET NULL'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='测试用例表'
    )
    
    # 创建测试用例表索引
    op.create_index('idx_test_cases_project_id', 'test_cases', ['project_id'])
    op.create_index('idx_test_cases_requirement_id', 'test_cases', ['requirement_id'])
    op.create_index('idx_test_cases_status', 'test_cases', ['status'])
    op.create_index('idx_test_cases_type', 'test_cases', ['test_type'])
    op.create_index('idx_test_cases_automated', 'test_cases', ['is_automated'])
    op.create_index('idx_test_cases_created_at', 'test_cases', ['created_at'])
    
    # 创建缺陷表
    op.create_table('defects',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='缺陷ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('test_case_id', sa.BigInteger(), nullable=True, comment='关联测试用例ID'),
        sa.Column('title', sa.String(300), nullable=False, comment='缺陷标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='缺陷描述'),
        
        # 缺陷属性
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'), 
                 nullable=True, default='MEDIUM', comment='严重程度'),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'), 
                 nullable=True, default='MEDIUM', comment='优先级'),
        sa.Column('status', sa.Enum('NEW', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'REOPENED'), 
                 nullable=True, default='NEW', comment='缺陷状态'),
        sa.Column('defect_type', sa.String(50), nullable=True, comment='缺陷类型'),
        
        # 缺陷详情
        sa.Column('steps_to_reproduce', sa.Text(), nullable=True, comment='重现步骤'),
        sa.Column('actual_result', sa.Text(), nullable=True, comment='实际结果'),
        sa.Column('expected_result', sa.Text(), nullable=True, comment='预期结果'),
        sa.Column('environment', sa.String(200), nullable=True, comment='测试环境'),
        
        # 处理信息
        sa.Column('assigned_to', sa.Integer(), nullable=True, comment='指派给'),
        sa.Column('reporter_id', sa.BigInteger(), nullable=True, comment='报告人ID'),
        sa.Column('resolution', sa.String(100), nullable=True, comment='解决方案'),
        sa.Column('resolution_notes', sa.Text(), nullable=True, comment='解决说明'),
        
        # 时间信息
        sa.Column('reported_date', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='报告日期'),
        sa.Column('resolved_date', sa.DateTime(), nullable=True, comment='解决日期'),
        sa.Column('closed_date', sa.DateTime(), nullable=True, comment='关闭日期'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ondelete='SET NULL'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='缺陷表'
    )
    
    # 创建缺陷表索引
    op.create_index('idx_defects_project_id', 'defects', ['project_id'])
    op.create_index('idx_defects_test_case_id', 'defects', ['test_case_id'])
    op.create_index('idx_defects_status', 'defects', ['status'])
    op.create_index('idx_defects_severity', 'defects', ['severity'])
    op.create_index('idx_defects_priority', 'defects', ['priority'])
    op.create_index('idx_defects_assigned_to', 'defects', ['assigned_to'])
    op.create_index('idx_defects_reporter_id', 'defects', ['reporter_id'])
    op.create_index('idx_defects_reported_date', 'defects', ['reported_date'])
    
    # 创建项目指标表
    op.create_table('project_metrics',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='指标ID'),
        sa.Column('project_id', sa.BigInteger(), nullable=False, comment='项目ID'),
        sa.Column('metric_date', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='指标日期'),
        
        # 需求指标
        sa.Column('requirements_total', sa.Integer(), nullable=True, default=0, comment='需求总数'),
        sa.Column('requirements_completed', sa.Integer(), nullable=True, default=0, comment='已完成需求数'),
        sa.Column('requirements_coverage', sa.Float(), nullable=True, comment='需求覆盖率'),
        sa.Column('requirements_quality_score', sa.Float(), nullable=True, comment='需求质量评分'),
        
        # 测试指标
        sa.Column('test_cases_total', sa.Integer(), nullable=True, default=0, comment='测试用例总数'),
        sa.Column('test_cases_executed', sa.Integer(), nullable=True, default=0, comment='已执行测试用例数'),
        sa.Column('test_cases_passed', sa.Integer(), nullable=True, default=0, comment='通过的测试用例数'),
        sa.Column('test_coverage', sa.Float(), nullable=True, comment='测试覆盖率'),
        sa.Column('automation_rate', sa.Float(), nullable=True, comment='自动化率'),
        
        # 质量指标
        sa.Column('defects_total', sa.Integer(), nullable=True, default=0, comment='缺陷总数'),
        sa.Column('defects_open', sa.Integer(), nullable=True, default=0, comment='未解决缺陷数'),
        sa.Column('defects_critical', sa.Integer(), nullable=True, default=0, comment='严重缺陷数'),
        sa.Column('defect_density', sa.Float(), nullable=True, comment='缺陷密度'),
        sa.Column('defect_resolution_time', sa.Float(), nullable=True, comment='平均缺陷解决时间'),
        
        # 进度指标
        sa.Column('progress_percentage', sa.Float(), nullable=True, comment='项目进度百分比'),
        sa.Column('milestone_completion', sa.Float(), nullable=True, comment='里程碑完成率'),
        sa.Column('schedule_variance', sa.Float(), nullable=True, comment='进度偏差'),
        
        # 团队指标
        sa.Column('team_velocity', sa.Float(), nullable=True, comment='团队速度'),
        sa.Column('team_productivity', sa.Float(), nullable=True, comment='团队生产力'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, 
                 default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp(), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='项目指标表'
    )
    
    # 创建项目指标表索引
    op.create_index('idx_project_metrics_project_id', 'project_metrics', ['project_id'])
    op.create_index('idx_project_metrics_date', 'project_metrics', ['metric_date'])
    op.create_index('idx_project_metrics_created_at', 'project_metrics', ['created_at'])
    
    # 创建复合索引优化查询性能
    op.create_index('idx_requirements_project_status', 'requirements', ['project_id', 'status'])
    op.create_index('idx_test_cases_project_status', 'test_cases', ['project_id', 'status'])
    op.create_index('idx_defects_project_status', 'defects', ['project_id', 'status'])
    op.create_index('idx_project_metrics_project_date', 'project_metrics', ['project_id', 'metric_date'])


def downgrade():
    """降级数据库结构"""
    
    # 删除复合索引
    op.drop_index('idx_project_metrics_project_date', table_name='project_metrics')
    op.drop_index('idx_defects_project_status', table_name='defects')
    op.drop_index('idx_test_cases_project_status', table_name='test_cases')
    op.drop_index('idx_requirements_project_status', table_name='requirements')
    
    # 删除项目指标表
    op.drop_index('idx_project_metrics_created_at', table_name='project_metrics')
    op.drop_index('idx_project_metrics_date', table_name='project_metrics')
    op.drop_index('idx_project_metrics_project_id', table_name='project_metrics')
    op.drop_table('project_metrics')
    
    # 删除缺陷表
    op.drop_index('idx_defects_reported_date', table_name='defects')
    op.drop_index('idx_defects_reporter_id', table_name='defects')
    op.drop_index('idx_defects_assigned_to', table_name='defects')
    op.drop_index('idx_defects_priority', table_name='defects')
    op.drop_index('idx_defects_severity', table_name='defects')
    op.drop_index('idx_defects_status', table_name='defects')
    op.drop_index('idx_defects_test_case_id', table_name='defects')
    op.drop_index('idx_defects_project_id', table_name='defects')
    op.drop_table('defects')
    
    # 删除测试用例表
    op.drop_index('idx_test_cases_created_at', table_name='test_cases')
    op.drop_index('idx_test_cases_automated', table_name='test_cases')
    op.drop_index('idx_test_cases_type', table_name='test_cases')
    op.drop_index('idx_test_cases_status', table_name='test_cases')
    op.drop_index('idx_test_cases_requirement_id', table_name='test_cases')
    op.drop_index('idx_test_cases_project_id', table_name='test_cases')
    op.drop_table('test_cases')
    
    # 删除需求表
    op.drop_index('idx_requirements_created_at', table_name='requirements')
    op.drop_index('idx_requirements_type', table_name='requirements')
    op.drop_index('idx_requirements_priority', table_name='requirements')
    op.drop_index('idx_requirements_status', table_name='requirements')
    op.drop_index('idx_requirements_project_id', table_name='requirements')
    op.drop_table('requirements')
    
    # 删除项目表
    op.drop_index('idx_projects_updated_at', table_name='projects')
    op.drop_index('idx_projects_created_at', table_name='projects')
    op.drop_index('idx_projects_manager', table_name='projects')
    op.drop_index('idx_projects_priority', table_name='projects')
    op.drop_index('idx_projects_status', table_name='projects')
    op.drop_table('projects')