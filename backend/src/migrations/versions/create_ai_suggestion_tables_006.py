"""
创建AI建议相关表

Revision ID: create_ai_suggestion_tables_006
Revises: 005_create_ai_assistant_tables
Create Date: 2024-08-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = 'create_ai_suggestion_tables_006'
down_revision = ('005_create_ai_assistant_tables', '002_ai_assistant_extended')
branch_labels = None
depends_on = None


def upgrade():
    """创建AI建议相关表"""
    
    # 创建需求建议表
    op.create_table(
        'ai_requirements_suggestions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('title', sa.String(200), nullable=False, comment='建议标题'),
        sa.Column('description', sa.Text(), nullable=False, comment='建议描述'),
        sa.Column('suggestion_type', sa.Enum('QUALITY_IMPROVEMENT', 'TEST_IMPROVEMENT', 'AUTOMATION_IMPROVEMENT', 
                                           'PROJECT_MANAGEMENT', 'COVERAGE_IMPROVEMENT', 'URGENT_FIX', 'OPTIMIZATION',
                                           name='reqsuggestiontype'), nullable=False, comment='建议类型'),
        sa.Column('category', sa.Enum('COMPLETENESS', 'CLARITY', 'TESTABILITY', 'PROBLEMATIC_REQUIREMENTS',
                                     'FUNCTIONAL_COVERAGE', 'NONFUNCTIONAL_COVERAGE', 'PERFORMANCE', 
                                     'SECURITY', 'MAINTAINABILITY', name='reqsuggestioncategory'), 
                 nullable=True, comment='建议分类'),
        
        # 关联信息
        sa.Column('analysis_id', sa.Integer(), nullable=False, comment='分析ID'),
        sa.Column('requirement_id', sa.Integer(), nullable=True, comment='需求ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        
        # 建议属性
        sa.Column('priority', sa.Enum('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', name='reqsuggestionpriority'), 
                 nullable=False, comment='优先级'),
        sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'REJECTED', 'IMPLEMENTED', 'CANCELLED',
                                   name='reqsuggestionstatus'), default='PENDING', nullable=False, comment='建议状态'),
        
        # 建议内容
        sa.Column('action_items', sa.JSON(), nullable=True, comment='行动项列表'),
        sa.Column('expected_benefit', sa.Text(), nullable=True, comment='预期收益'),
        sa.Column('estimated_effort', sa.String(100), nullable=True, comment='预估工作量'),
        
        # 问题相关
        sa.Column('identified_issues', sa.JSON(), nullable=True, comment='识别的问题'),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='issueseverity'), 
                 nullable=True, comment='问题严重程度'),
        
        # AI生成信息
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=True, comment='AI模型名称'),
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='置信度分数'),
        sa.Column('generation_prompt', sa.Text(), nullable=True, comment='生成提示词'),
        
        # 用户交互
        sa.Column('user_rating', sa.Integer(), nullable=True, comment='用户评分（1-5）'),
        sa.Column('user_feedback', sa.Text(), nullable=True, comment='用户反馈'),
        sa.Column('is_accepted', sa.Boolean(), default=False, comment='是否被接受'),
        
        # 实施信息
        sa.Column('implemented_at', sa.DateTime(), nullable=True, comment='实施时间'),
        sa.Column('implemented_by', sa.Integer(), nullable=True, comment='实施人ID'),
        sa.Column('implementation_notes', sa.Text(), nullable=True, comment='实施说明'),
        
        # 元数据
        sa.Column('suggestion_metadata', sa.JSON(), nullable=True, comment='建议元数据'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['analysis_id'], ['ai_requirements_analysis.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        comment='需求建议表'
    )
    
    # 创建需求建议表索引
    op.create_index('idx_ai_requirements_suggestions_analysis_id', 'ai_requirements_suggestions', ['analysis_id'])
    op.create_index('idx_ai_requirements_suggestions_user_id', 'ai_requirements_suggestions', ['user_id'])
    op.create_index('idx_ai_requirements_suggestions_requirement_id', 'ai_requirements_suggestions', ['requirement_id'])
    op.create_index('idx_ai_requirements_suggestions_type', 'ai_requirements_suggestions', ['suggestion_type'])
    op.create_index('idx_ai_requirements_suggestions_status', 'ai_requirements_suggestions', ['status'])
    op.create_index('idx_ai_requirements_suggestions_priority', 'ai_requirements_suggestions', ['priority'])
    op.create_index('idx_ai_requirements_suggestions_category', 'ai_requirements_suggestions', ['category'])
    op.create_index('idx_ai_requirements_suggestions_severity', 'ai_requirements_suggestions', ['severity'])
    op.create_index('idx_ai_requirements_suggestions_ai_provider', 'ai_requirements_suggestions', ['ai_provider'])
    op.create_index('idx_ai_requirements_suggestions_created_at', 'ai_requirements_suggestions', ['created_at'])
    
    print("AI建议相关表创建完成")


def downgrade():
    """删除AI建议相关表"""
    op.drop_table('ai_requirements_suggestions')
    
    print("AI建议相关表删除完成")