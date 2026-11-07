"""Create AI Assistant extended tables

Revision ID: 002_ai_assistant_extended
Revises: 001_ai_assistant
Create Date: 2024-12-19 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '002_ai_assistant_extended'
down_revision = '001_ai_assistant'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create extended AI Assistant tables"""
    
    # 1. Create ai_suggestions table
    op.create_table(
        'ai_suggestions',
        sa.Column('id', sa.Integer(), nullable=False, comment='主键ID'),
        sa.Column('session_id', sa.Integer(), nullable=True, comment='关联会话ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('project_id', sa.Integer(), nullable=True, comment='项目ID'),
        sa.Column('suggestion_type', sa.Enum('OPTIMIZATION', 'IMPROVEMENT', 'RISK_MITIGATION', 'BEST_PRACTICE', 'AUTOMATION', name='suggestiontype'), 
                 nullable=False, comment='建议类型'),
        sa.Column('category', sa.String(100), nullable=False, comment='建议分类'),
        sa.Column('subcategory', sa.String(100), nullable=True, comment='子分类'),
        
        # 建议内容
        sa.Column('title', sa.String(300), nullable=False, comment='建议标题'),
        sa.Column('description', sa.Text(), nullable=False, comment='建议描述'),
        sa.Column('rationale', sa.Text(), nullable=True, comment='建议理由'),
        sa.Column('expected_benefit', sa.Text(), nullable=True, comment='预期收益'),
        sa.Column('implementation_guide', sa.Text(), nullable=True, comment='实施指南'),
        sa.Column('estimated_effort', sa.String(100), nullable=True, comment='预估工作量'),
        
        # 优先级和状态
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='suggestionpriority'), 
                 nullable=False, default='MEDIUM', comment='优先级'),
        sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'REJECTED', 'IMPLEMENTED', 'CANCELLED', name='suggestionstatus'), 
                 nullable=False, default='PENDING', comment='状态'),
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='置信度分数'),
        sa.Column('impact_score', sa.Float(), nullable=True, comment='影响分数'),
        
        # 上下文信息
        sa.Column('context_data', sa.JSON(), nullable=True, comment='上下文数据'),
        sa.Column('analysis_data', sa.JSON(), nullable=True, comment='分析数据'),
        sa.Column('metrics_before', sa.JSON(), nullable=True, comment='实施前指标'),
        sa.Column('metrics_after', sa.JSON(), nullable=True, comment='实施后指标'),
        
        # 用户反馈
        sa.Column('user_rating', sa.SmallInteger(), nullable=True, comment='用户评分（1-5）'),
        sa.Column('user_feedback', sa.Text(), nullable=True, comment='用户反馈'),
        sa.Column('implementation_notes', sa.Text(), nullable=True, comment='实施备注'),
        
        # 关联信息
        sa.Column('related_requirements', sa.JSON(), nullable=True, comment='相关需求ID列表'),
        sa.Column('related_test_cases', sa.JSON(), nullable=True, comment='相关测试用例ID列表'),
        sa.Column('related_issues', sa.JSON(), nullable=True, comment='相关问题ID列表'),
        
        # 时间信息
        sa.Column('suggested_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='建议时间'),
        sa.Column('accepted_at', sa.DateTime(), nullable=True, comment='接受时间'),
        sa.Column('implemented_at', sa.DateTime(), nullable=True, comment='实施时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['ai_chat_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='AI建议表'
    )
    
    # Create indexes for ai_suggestions
    op.create_index('idx_session_id', 'ai_suggestions', ['session_id'])
    op.create_index('idx_user_id', 'ai_suggestions', ['user_id'])
    op.create_index('idx_project_id', 'ai_suggestions', ['project_id'])
    op.create_index('idx_suggestion_type', 'ai_suggestions', ['suggestion_type'])
    op.create_index('idx_category', 'ai_suggestions', ['category'])
    op.create_index('idx_priority', 'ai_suggestions', ['priority'])
    op.create_index('idx_status', 'ai_suggestions', ['status'])
    op.create_index('idx_confidence_score', 'ai_suggestions', ['confidence_score'])
    op.create_index('idx_suggested_at', 'ai_suggestions', ['suggested_at'])
    op.create_index('idx_created_at', 'ai_suggestions', ['created_at'])
    op.create_index('idx_user_status_priority', 'ai_suggestions', ['user_id', 'status', 'priority'])
    op.create_index('idx_type_category_created', 'ai_suggestions', ['suggestion_type', 'category', 'created_at'])
    op.create_index('idx_project_status_suggested', 'ai_suggestions', ['project_id', 'status', 'suggested_at'])
    
    # 2. Create ai_requirements_analysis table
    op.create_table(
        'ai_requirements_analysis',
        sa.Column('id', sa.Integer(), nullable=False, comment='主键ID'),
        sa.Column('session_id', sa.Integer(), nullable=True, comment='关联会话ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('project_id', sa.Integer(), nullable=True, comment='项目ID'),
        sa.Column('analysis_name', sa.String(200), nullable=False, comment='分析名称'),
        sa.Column('analysis_type', sa.Enum('QUALITY', 'COVERAGE', 'COMPLETENESS', 'CONSISTENCY', 'TRACEABILITY', name='analysistype'), 
                 nullable=False, comment='分析类型'),
        
        # 分析结果
        sa.Column('overall_score', sa.Float(), nullable=True, comment='总体评分'),
        sa.Column('completeness_score', sa.Float(), nullable=True, comment='完整性评分'),
        sa.Column('clarity_score', sa.Float(), nullable=True, comment='清晰度评分'),
        sa.Column('consistency_score', sa.Float(), nullable=True, comment='一致性评分'),
        sa.Column('testability_score', sa.Float(), nullable=True, comment='可测试性评分'),
        
        # 分析详情
        sa.Column('analysis_summary', sa.Text(), nullable=True, comment='分析摘要'),
        sa.Column('key_findings', sa.JSON(), nullable=True, comment='关键发现'),
        sa.Column('recommendations', sa.JSON(), nullable=True, comment='改进建议'),
        sa.Column('risk_assessment', sa.JSON(), nullable=True, comment='风险评估'),
        
        # 问题识别
        sa.Column('total_requirements', sa.Integer(), nullable=True, default=0, comment='需求总数'),
        sa.Column('problematic_requirements', sa.JSON(), nullable=True, comment='问题需求列表'),
        sa.Column('missing_requirements', sa.JSON(), nullable=True, comment='缺失需求列表'),
        sa.Column('duplicate_requirements', sa.JSON(), nullable=True, comment='重复需求列表'),
        
        # 覆盖度分析
        sa.Column('functional_coverage', sa.JSON(), nullable=True, comment='功能覆盖度分析'),
        sa.Column('nonfunctional_coverage', sa.JSON(), nullable=True, comment='非功能需求覆盖度'),
        sa.Column('test_coverage_mapping', sa.JSON(), nullable=True, comment='测试覆盖度映射'),
        
        # 分析状态
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='analysisstatus'), 
                 nullable=False, default='PENDING', comment='分析状态'),
        sa.Column('progress', sa.Integer(), nullable=False, default=0, comment='分析进度（0-100）'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        
        # 时间信息
        sa.Column('started_at', sa.DateTime(), nullable=True, comment='开始时间'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='完成时间'),
        sa.Column('analysis_duration', sa.Integer(), nullable=True, comment='分析耗时（秒）'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['ai_chat_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='AI需求分析表'
    )
    
    # Create indexes for ai_requirements_analysis
    op.create_index('idx_session_id', 'ai_requirements_analysis', ['session_id'])
    op.create_index('idx_user_id', 'ai_requirements_analysis', ['user_id'])
    op.create_index('idx_project_id', 'ai_requirements_analysis', ['project_id'])
    op.create_index('idx_analysis_type', 'ai_requirements_analysis', ['analysis_type'])
    op.create_index('idx_status', 'ai_requirements_analysis', ['status'])
    op.create_index('idx_overall_score', 'ai_requirements_analysis', ['overall_score'])
    op.create_index('idx_started_at', 'ai_requirements_analysis', ['started_at'])
    op.create_index('idx_created_at', 'ai_requirements_analysis', ['created_at'])
    op.create_index('idx_user_type_status', 'ai_requirements_analysis', ['user_id', 'analysis_type', 'status'])
    op.create_index('idx_project_type_completed', 'ai_requirements_analysis', ['project_id', 'analysis_type', 'completed_at'])
    
    # 3. Create ai_usage_stats table
    op.create_table(
        'ai_usage_stats',
        sa.Column('id', sa.Integer(), nullable=False, comment='主键ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('session_id', sa.Integer(), nullable=True, comment='会话ID'),
        sa.Column('ai_provider', sa.String(50), nullable=False, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=False, comment='AI模型名称'),
        sa.Column('operation_type', sa.Enum('CHAT', 'SUGGESTION', 'ANALYSIS', 'TEMPLATE', 'OTHER', name='operationtype'), 
                 nullable=False, comment='操作类型'),
        
        # 使用量统计
        sa.Column('request_count', sa.Integer(), nullable=False, default=1, comment='请求次数'),
        sa.Column('input_tokens', sa.Integer(), nullable=False, default=0, comment='输入Token数'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, default=0, comment='输出Token数'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, default=0, comment='总Token数'),
        
        # 成本统计
        sa.Column('input_cost', sa.DECIMAL(8, 4), nullable=False, default=0.0000, comment='输入成本'),
        sa.Column('output_cost', sa.DECIMAL(8, 4), nullable=False, default=0.0000, comment='输出成本'),
        sa.Column('total_cost', sa.DECIMAL(8, 4), nullable=False, default=0.0000, comment='总成本'),
        
        # 性能统计
        sa.Column('avg_response_time', sa.Float(), nullable=True, comment='平均响应时间（秒）'),
        sa.Column('success_count', sa.Integer(), nullable=False, default=0, comment='成功次数'),
        sa.Column('error_count', sa.Integer(), nullable=False, default=0, comment='错误次数'),
        sa.Column('success_rate', sa.Float(), nullable=True, comment='成功率'),
        
        # 时间维度
        sa.Column('stat_date', sa.Date(), nullable=False, comment='统计日期'),
        sa.Column('stat_hour', sa.SmallInteger(), nullable=True, comment='统计小时（0-23）'),
        sa.Column('stat_period', sa.Enum('HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', name='statperiod'), 
                 nullable=False, default='DAILY', comment='统计周期'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'ai_provider', 'ai_model', 'stat_date', 'stat_hour', 'operation_type', 
                           name='uk_user_provider_model_date_hour'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['ai_chat_sessions.id'], ondelete='SET NULL'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='AI使用统计表'
    )
    
    # Create indexes for ai_usage_stats
    op.create_index('idx_user_id', 'ai_usage_stats', ['user_id'])
    op.create_index('idx_session_id', 'ai_usage_stats', ['session_id'])
    op.create_index('idx_ai_provider', 'ai_usage_stats', ['ai_provider'])
    op.create_index('idx_ai_model', 'ai_usage_stats', ['ai_model'])
    op.create_index('idx_operation_type', 'ai_usage_stats', ['operation_type'])
    op.create_index('idx_stat_date', 'ai_usage_stats', ['stat_date'])
    op.create_index('idx_stat_period', 'ai_usage_stats', ['stat_period'])
    op.create_index('idx_created_at', 'ai_usage_stats', ['created_at'])
    op.create_index('idx_date_provider_model', 'ai_usage_stats', ['stat_date', 'ai_provider', 'ai_model'])
    op.create_index('idx_user_date_period', 'ai_usage_stats', ['user_id', 'stat_date', 'stat_period'])
    
    # 4. Create ai_template_usage table
    op.create_table(
        'ai_template_usage',
        sa.Column('id', sa.Integer(), nullable=False, comment='主键ID'),
        sa.Column('template_id', sa.Integer(), nullable=False, comment='模板ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('session_id', sa.Integer(), nullable=True, comment='会话ID'),
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=True, comment='AI模型名称'),
        
        # 使用上下文
        sa.Column('use_case', sa.String(200), nullable=True, comment='使用场景'),
        sa.Column('context_data', sa.JSON(), nullable=True, comment='上下文数据'),
        sa.Column('rendered_content', sa.Text(length=4294967295), nullable=True, comment='渲染后内容'),
        
        # 使用结果
        sa.Column('is_successful', sa.Boolean(), nullable=False, default=True, comment='是否成功'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('execution_time', sa.Float(), nullable=True, comment='执行时间（秒）'),
        
        # 用户反馈
        sa.Column('user_rating', sa.SmallInteger(), nullable=True, comment='用户评分（1-5）'),
        sa.Column('user_feedback', sa.Text(), nullable=True, comment='用户反馈'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['ai_prompt_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['ai_chat_sessions.id'], ondelete='SET NULL'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='AI模板使用记录表'
    )
    
    # Create indexes for ai_template_usage
    op.create_index('idx_template_id', 'ai_template_usage', ['template_id'])
    op.create_index('idx_user_id', 'ai_template_usage', ['user_id'])
    op.create_index('idx_session_id', 'ai_template_usage', ['session_id'])
    op.create_index('idx_ai_provider', 'ai_template_usage', ['ai_provider'])
    op.create_index('idx_use_case', 'ai_template_usage', ['use_case'])
    op.create_index('idx_is_successful', 'ai_template_usage', ['is_successful'])
    op.create_index('idx_created_at', 'ai_template_usage', ['created_at'])


def downgrade() -> None:
    """Drop extended AI Assistant tables"""
    
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('ai_template_usage')
    op.drop_table('ai_usage_stats')
    op.drop_table('ai_requirements_analysis')
    op.drop_table('ai_suggestions')
    
    # Drop custom enum types
    op.execute("DROP TYPE IF EXISTS suggestiontype")
    op.execute("DROP TYPE IF EXISTS suggestionpriority")
    op.execute("DROP TYPE IF EXISTS suggestionstatus")
    op.execute("DROP TYPE IF EXISTS analysistype")
    op.execute("DROP TYPE IF EXISTS analysisstatus")
    op.execute("DROP TYPE IF EXISTS operationtype")
    op.execute("DROP TYPE IF EXISTS statperiod")