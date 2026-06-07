"""
添加数据库性能优化索引

Revision ID: 007_add_performance_indexes
Revises: 006_add_ai_operation_logs
Create Date: 2024-12-19 16:00:00.000000

本迁移脚本添加数据库性能优化索引，提升AI助手系统的查询性能。
包括复合索引、覆盖索引和专用查询索引。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_performance_indexes'
down_revision = '006_add_ai_operation_logs'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构 - 添加性能优化索引"""
    
    # =====================================================
    # AI聊天会话表性能优化索引
    # =====================================================
    
    # 用户会话查询优化 - 复合索引
    op.create_index(
        'idx_ai_chat_sessions_user_activity',
        'ai_chat_sessions',
        ['user_id', 'last_activity_at', 'status'],
        comment='用户会话按活动时间查询优化'
    )
    
    # 会话状态和AI提供商查询优化
    op.create_index(
        'idx_ai_chat_sessions_provider_status',
        'ai_chat_sessions',
        ['ai_provider', 'status', 'created_at'],
        comment='按AI提供商和状态查询优化'
    )
    
    # 会话分享查询优化
    op.create_index(
        'idx_ai_chat_sessions_share',
        'ai_chat_sessions',
        ['is_shared', 'share_token', 'expires_at'],
        comment='会话分享功能查询优化'
    )
    
    # 会话统计查询优化
    op.create_index(
        'idx_ai_chat_sessions_stats',
        'ai_chat_sessions',
        ['user_id', 'created_at', 'message_count'],
        comment='会话统计查询优化'
    )
    
    # =====================================================
    # AI聊天消息表性能优化索引
    # =====================================================
    
    # 会话消息查询优化 - 复合索引
    op.create_index(
        'idx_ai_chat_messages_session_time',
        'ai_chat_messages',
        ['session_id', 'created_at', 'role'],
        comment='会话消息按时间和角色查询优化'
    )
    
    # AI提供商和模型查询优化
    op.create_index(
        'idx_ai_chat_messages_ai_info',
        'ai_chat_messages',
        ['ai_provider', 'ai_model', 'created_at'],
        comment='按AI提供商和模型查询优化'
    )
    
    # 消息评分和反馈查询优化
    op.create_index(
        'idx_ai_chat_messages_feedback',
        'ai_chat_messages',
        ['user_rating', 'is_bookmarked', 'created_at'],
        comment='消息评分和收藏查询优化'
    )
    
    # 错误消息查询优化
    op.create_index(
        'idx_ai_chat_messages_errors',
        'ai_chat_messages',
        ['is_error', 'error_code', 'created_at'],
        comment='错误消息查询优化'
    )
    
    # 流式消息查询优化
    op.create_index(
        'idx_ai_chat_messages_streaming',
        'ai_chat_messages',
        ['is_streaming', 'session_id', 'created_at'],
        comment='流式消息查询优化'
    )
    
    # =====================================================
    # AI模型配置表性能优化索引
    # =====================================================
    
    # 可用模型查询优化
    op.create_index(
        'idx_ai_model_configs_available',
        'ai_model_configs',
        ['is_enabled', 'is_public', 'priority'],
        comment='可用模型查询优化'
    )
    
    # 模型健康状态查询优化
    op.create_index(
        'idx_ai_model_configs_health',
        'ai_model_configs',
        ['health_status', 'last_health_check', 'provider'],
        comment='模型健康状态查询优化'
    )
    
    # 模型使用统计查询优化
    op.create_index(
        'idx_ai_model_configs_usage',
        'ai_model_configs',
        ['provider', 'last_used_at', 'total_requests'],
        comment='模型使用统计查询优化'
    )
    
    # =====================================================
    # AI提示词模板表性能优化索引
    # =====================================================
    
    # 模板分类和可见性查询优化
    op.create_index(
        'idx_ai_prompt_templates_category_visibility',
        'ai_prompt_templates',
        ['category', 'visibility', 'is_featured'],
        comment='模板分类和可见性查询优化'
    )
    
    # 用户模板查询优化
    op.create_index(
        'idx_ai_prompt_templates_owner',
        'ai_prompt_templates',
        ['owner_id', 'visibility', 'created_at'],
        comment='用户模板查询优化'
    )
    
    # 模板使用统计查询优化
    op.create_index(
        'idx_ai_prompt_templates_usage',
        'ai_prompt_templates',
        ['usage_count', 'rating_avg', 'last_used_at'],
        comment='模板使用统计查询优化'
    )
    
    # 模板版本查询优化
    op.create_index(
        'idx_ai_prompt_templates_version',
        'ai_prompt_templates',
        ['parent_template_id', 'is_latest_version', 'version'],
        comment='模板版本查询优化'
    )
    
    # =====================================================
    # AI建议表性能优化索引
    # =====================================================
    
    # 用户建议查询优化
    op.create_index(
        'idx_ai_suggestions_user_project',
        'ai_suggestions',
        ['user_id', 'project_id', 'status'],
        comment='用户项目建议查询优化'
    )
    
    # 建议类型和优先级查询优化
    op.create_index(
        'idx_ai_suggestions_type_priority',
        'ai_suggestions',
        ['suggestion_type', 'priority', 'suggested_at'],
        comment='建议类型和优先级查询优化'
    )
    
    # 建议状态和时间查询优化
    op.create_index(
        'idx_ai_suggestions_status_time',
        'ai_suggestions',
        ['status', 'suggested_at', 'accepted_at'],
        comment='建议状态和时间查询优化'
    )
    
    # 建议评分查询优化
    op.create_index(
        'idx_ai_suggestions_scores',
        'ai_suggestions',
        ['confidence_score', 'impact_score', 'user_rating'],
        comment='建议评分查询优化'
    )
    
    # =====================================================
    # AI需求分析表性能优化索引
    # =====================================================
    
    # 用户分析查询优化
    op.create_index(
        'idx_ai_requirements_analysis_user',
        'ai_requirements_analysis',
        ['user_id', 'project_id', 'analysis_type'],
        comment='用户需求分析查询优化'
    )
    
    # 分析状态和时间查询优化
    op.create_index(
        'idx_ai_requirements_analysis_status',
        'ai_requirements_analysis',
        ['status', 'started_at', 'completed_at'],
        comment='分析状态和时间查询优化'
    )
    
    # 分析评分查询优化
    op.create_index(
        'idx_ai_requirements_analysis_scores',
        'ai_requirements_analysis',
        ['overall_score', 'completeness_score', 'clarity_score'],
        comment='需求分析评分查询优化'
    )
    
    # =====================================================
    # AI使用统计表性能优化索引
    # =====================================================
    
    # 用户使用统计查询优化
    op.create_index(
        'idx_ai_usage_stats_user_date',
        'ai_usage_stats',
        ['user_id', 'stat_date', 'operation_type'],
        comment='用户使用统计查询优化'
    )
    
    # AI提供商统计查询优化
    op.create_index(
        'idx_ai_usage_stats_provider',
        'ai_usage_stats',
        ['ai_provider', 'ai_model', 'stat_date'],
        comment='AI提供商统计查询优化'
    )
    
    # 统计周期查询优化
    op.create_index(
        'idx_ai_usage_stats_period',
        'ai_usage_stats',
        ['stat_period', 'stat_date', 'stat_hour'],
        comment='统计周期查询优化'
    )
    
    # 成本统计查询优化
    op.create_index(
        'idx_ai_usage_stats_cost',
        'ai_usage_stats',
        ['stat_date', 'total_cost', 'total_tokens'],
        comment='成本统计查询优化'
    )
    
    # =====================================================
    # AI模板使用记录表性能优化索引
    # =====================================================
    
    # 模板使用查询优化
    op.create_index(
        'idx_ai_template_usage_template_user',
        'ai_template_usage',
        ['template_id', 'user_id', 'created_at'],
        comment='模板使用记录查询优化'
    )
    
    # 使用场景查询优化
    op.create_index(
        'idx_ai_template_usage_case',
        'ai_template_usage',
        ['use_case', 'is_successful', 'created_at'],
        comment='使用场景查询优化'
    )
    
    # AI提供商使用查询优化
    op.create_index(
        'idx_ai_template_usage_ai',
        'ai_template_usage',
        ['ai_provider', 'ai_model', 'created_at'],
        comment='AI提供商使用查询优化'
    )
    
    # =====================================================
    # 项目相关表性能优化索引（如果存在）
    # =====================================================
    
    # 检查项目表是否存在
    try:
        # 项目查询优化
        op.create_index(
            'idx_projects_status_priority',
            'projects',
            ['status', 'priority', 'updated_at'],
            comment='项目状态和优先级查询优化'
        )
        
        # 项目经理查询优化
        op.create_index(
            'idx_projects_manager_dates',
            'projects',
            ['project_manager_id', 'start_date', 'end_date'],
            comment='项目经理和时间查询优化'
        )
        
        # 需求查询优化
        op.create_index(
            'idx_requirements_project_status',
            'requirements',
            ['project_id', 'status', 'priority'],
            comment='需求项目和状态查询优化'
        )
        
        # 测试用例查询优化
        op.create_index(
            'idx_test_cases_project_req',
            'test_cases',
            ['project_id', 'requirement_id', 'status'],
            comment='测试用例项目和需求查询优化'
        )
        
        # 缺陷查询优化
        op.create_index(
            'idx_defects_project_severity',
            'defects',
            ['project_id', 'severity', 'status'],
            comment='缺陷项目和严重程度查询优化'
        )
        
        # 项目指标查询优化
        op.create_index(
            'idx_project_metrics_project_date',
            'project_metrics',
            ['project_id', 'metric_date'],
            comment='项目指标时间查询优化'
        )
        
    except Exception:
        # 项目表不存在，跳过
        pass
    
    # =====================================================
    # 全文搜索索引（如果支持）
    # =====================================================
    
    try:
        # AI聊天消息内容全文搜索
        op.execute("""
            ALTER TABLE ai_chat_messages 
            ADD FULLTEXT INDEX idx_ai_chat_messages_content_fulltext (content)
        """)
        
        # AI建议内容全文搜索
        op.execute("""
            ALTER TABLE ai_suggestions 
            ADD FULLTEXT INDEX idx_ai_suggestions_content_fulltext (title, description)
        """)
        
        # 提示词模板内容全文搜索
        op.execute("""
            ALTER TABLE ai_prompt_templates 
            ADD FULLTEXT INDEX idx_ai_prompt_templates_content_fulltext (title, description, content)
        """)
        
    except Exception:
        # 全文搜索不支持，跳过
        pass


def downgrade():
    """降级数据库结构 - 删除性能优化索引"""
    
    # 删除AI聊天会话表索引
    op.drop_index('idx_ai_chat_sessions_user_activity', table_name='ai_chat_sessions')
    op.drop_index('idx_ai_chat_sessions_provider_status', table_name='ai_chat_sessions')
    op.drop_index('idx_ai_chat_sessions_share', table_name='ai_chat_sessions')
    op.drop_index('idx_ai_chat_sessions_stats', table_name='ai_chat_sessions')
    
    # 删除AI聊天消息表索引
    op.drop_index('idx_ai_chat_messages_session_time', table_name='ai_chat_messages')
    op.drop_index('idx_ai_chat_messages_ai_info', table_name='ai_chat_messages')
    op.drop_index('idx_ai_chat_messages_feedback', table_name='ai_chat_messages')
    op.drop_index('idx_ai_chat_messages_errors', table_name='ai_chat_messages')
    op.drop_index('idx_ai_chat_messages_streaming', table_name='ai_chat_messages')
    
    # 删除AI模型配置表索引
    op.drop_index('idx_ai_model_configs_available', table_name='ai_model_configs')
    op.drop_index('idx_ai_model_configs_health', table_name='ai_model_configs')
    op.drop_index('idx_ai_model_configs_usage', table_name='ai_model_configs')
    
    # 删除AI提示词模板表索引
    op.drop_index('idx_ai_prompt_templates_category_visibility', table_name='ai_prompt_templates')
    op.drop_index('idx_ai_prompt_templates_owner', table_name='ai_prompt_templates')
    op.drop_index('idx_ai_prompt_templates_usage', table_name='ai_prompt_templates')
    op.drop_index('idx_ai_prompt_templates_version', table_name='ai_prompt_templates')
    
    # 删除AI建议表索引
    op.drop_index('idx_ai_suggestions_user_project', table_name='ai_suggestions')
    op.drop_index('idx_ai_suggestions_type_priority', table_name='ai_suggestions')
    op.drop_index('idx_ai_suggestions_status_time', table_name='ai_suggestions')
    op.drop_index('idx_ai_suggestions_scores', table_name='ai_suggestions')
    
    # 删除AI需求分析表索引
    op.drop_index('idx_ai_requirements_analysis_user', table_name='ai_requirements_analysis')
    op.drop_index('idx_ai_requirements_analysis_status', table_name='ai_requirements_analysis')
    op.drop_index('idx_ai_requirements_analysis_scores', table_name='ai_requirements_analysis')
    
    # 删除AI使用统计表索引
    op.drop_index('idx_ai_usage_stats_user_date', table_name='ai_usage_stats')
    op.drop_index('idx_ai_usage_stats_provider', table_name='ai_usage_stats')
    op.drop_index('idx_ai_usage_stats_period', table_name='ai_usage_stats')
    op.drop_index('idx_ai_usage_stats_cost', table_name='ai_usage_stats')
    
    # 删除AI模板使用记录表索引
    op.drop_index('idx_ai_template_usage_template_user', table_name='ai_template_usage')
    op.drop_index('idx_ai_template_usage_case', table_name='ai_template_usage')
    op.drop_index('idx_ai_template_usage_ai', table_name='ai_template_usage')
    
    # 删除项目相关表索引（如果存在）
    try:
        op.drop_index('idx_projects_status_priority', table_name='projects')
        op.drop_index('idx_projects_manager_dates', table_name='projects')
        op.drop_index('idx_requirements_project_status', table_name='requirements')
        op.drop_index('idx_test_cases_project_req', table_name='test_cases')
        op.drop_index('idx_defects_project_severity', table_name='defects')
        op.drop_index('idx_project_metrics_project_date', table_name='project_metrics')
    except Exception:
        pass
    
    # 删除全文搜索索引（如果存在）
    try:
        op.drop_index('idx_ai_chat_messages_content_fulltext', table_name='ai_chat_messages')
        op.drop_index('idx_ai_suggestions_content_fulltext', table_name='ai_suggestions')
        op.drop_index('idx_ai_prompt_templates_content_fulltext', table_name='ai_prompt_templates')
    except Exception:
        pass