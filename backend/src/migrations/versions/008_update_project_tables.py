"""
更新项目管理模块表结构

Revision ID: 008_update_project_tables
Revises: 005_add_project_tables
Create Date: 2024-12-20 10:00:00.000000

本迁移脚本更新项目管理模块的表结构，包括：
1. 更新projects表结构以符合项目管理规范
2. 添加project_members表（项目成员管理）
3. 添加project_tasks表（任务管理）
4. 添加project_milestones表（里程碑管理）
5. 添加work_logs表（工作日志）
6. 添加project_risks表（项目风险管理）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '008_update_project_tables'
down_revision = '005_add_project_tables'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构"""
    
    # 1. 更新projects表结构
    # 添加新字段
    op.add_column('projects', sa.Column('project_code', sa.String(50), nullable=True, comment='项目编码'))
    op.add_column('projects', sa.Column('project_name', sa.String(200), nullable=True, comment='项目名称'))
    op.add_column('projects', sa.Column('health_score', sa.Integer(), default=100, comment='项目健康度(0-100)'))
    op.add_column('projects', sa.Column('risk_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'), 
                                       default='LOW', comment='风险等级'))
    
    # 修改时间字段类型
    op.add_column('projects', sa.Column('planned_start_date', sa.Date(), comment='计划开始日期'))
    op.add_column('projects', sa.Column('planned_end_date', sa.Date(), comment='计划结束日期'))
    op.add_column('projects', sa.Column('actual_start_date', sa.Date(), comment='实际开始日期'))
    op.add_column('projects', sa.Column('actual_end_date', sa.Date(), comment='实际结束日期'))
    
    # 添加新的人员管理字段
    op.add_column('projects', sa.Column('test_manager_id', sa.BigInteger(), comment='测试经理ID'))
    op.add_column('projects', sa.Column('client_contact', sa.String(200), comment='客户联系人'))
    
    # 修改预算字段类型
    op.add_column('projects', sa.Column('budget_decimal', sa.DECIMAL(15, 2), comment='项目预算'))
    op.add_column('projects', sa.Column('actual_cost', sa.DECIMAL(15, 2), default=0.00, comment='实际成本'))
    
    # 添加进度管理字段
    op.add_column('projects', sa.Column('progress_percentage', sa.DECIMAL(5, 2), default=0.00, comment='完成百分比'))
    op.add_column('projects', sa.Column('task_count', sa.Integer(), default=0, comment='任务总数'))
    op.add_column('projects', sa.Column('completed_task_count', sa.Integer(), default=0, comment='已完成任务数'))
    
    # 添加质量管理字段
    op.add_column('projects', sa.Column('test_case_count', sa.Integer(), default=0, comment='测试用例总数'))
    op.add_column('projects', sa.Column('passed_test_count', sa.Integer(), default=0, comment='通过测试数'))
    op.add_column('projects', sa.Column('defect_count', sa.Integer(), default=0, comment='缺陷总数'))
    
    # 添加元数据字段
    op.add_column('projects', sa.Column('tags', sa.JSON(), comment='项目标签'))
    
    # 修改项目类型枚举
    op.execute("ALTER TABLE projects MODIFY COLUMN project_type ENUM('FUNCTIONAL', 'PERFORMANCE', 'SECURITY', 'AUTOMATION', 'INTEGRATION') COMMENT '项目类型'")
    
    # 修改项目状态枚举
    op.execute("ALTER TABLE projects MODIFY COLUMN status ENUM('PLANNING', 'IN_PROGRESS', 'ON_HOLD', 'COMPLETED', 'CANCELLED', 'ARCHIVED') DEFAULT 'PLANNING' COMMENT '项目状态'")
    
    # 修改优先级枚举
    op.execute("ALTER TABLE projects MODIFY COLUMN priority ENUM('LOW', 'MEDIUM', 'HIGH', 'URGENT') DEFAULT 'MEDIUM' COMMENT '项目优先级'")
    
    
    # 添加唯一约束
    op.create_unique_constraint('uk_project_code', 'projects', ['project_code'])
    


def downgrade():
    """降级数据库结构"""
    
    # 删除复合索引
    
    # 删除项目风险表
    
    # 删除工作日志表
    
    # 删除里程碑表
    
    # 删除任务表
    
    # 删除项目成员表
    
    # 删除projects表的新字段
    op.drop_constraint('uk_project_code', 'projects', type_='unique')
    op.drop_column('projects', 'tags')
    op.drop_column('projects', 'defect_count')
    op.drop_column('projects', 'passed_test_count')
    op.drop_column('projects', 'test_case_count')
    op.drop_column('projects', 'completed_task_count')
    op.drop_column('projects', 'task_count')
    op.drop_column('projects', 'progress_percentage')
    op.drop_column('projects', 'actual_cost')
    op.drop_column('projects', 'budget_decimal')
    op.drop_column('projects', 'client_contact')
    op.drop_column('projects', 'test_manager_id')
    op.drop_column('projects', 'actual_end_date')
    op.drop_column('projects', 'actual_start_date')
    op.drop_column('projects', 'planned_end_date')
    op.drop_column('projects', 'planned_start_date')
    op.drop_column('projects', 'risk_level')
    op.drop_column('projects', 'health_score')
    op.drop_column('projects', 'project_name')
    op.drop_column('projects', 'project_code')