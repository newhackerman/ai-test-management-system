"""
创建AI助手模块相关表

Revision ID: 005_create_ai_assistant_tables
Revises: 004_init_config_data
Create Date: 2024-08-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '005_create_ai_assistant_tables'
down_revision = '004_init_config_data'
branch_labels = None
depends_on = None


def upgrade():
    """创建AI助手模块相关表"""
    
    # 创建AI模型配置表
    op.create_table(
        'ai_model_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('provider', sa.String(50), nullable=False, comment='AI服务提供商'),
        sa.Column('model_name', sa.String(100), nullable=False, comment='模型名称'),
        sa.Column('display_name', sa.String(200), nullable=False, comment='显示名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='模型描述'),
        
        # 配置信息
        sa.Column('api_endpoint', sa.String(500), nullable=True, comment='API端点'),
        sa.Column('api_key', sa.String(500), nullable=True, comment='API密钥'),
        sa.Column('api_version', sa.String(50), nullable=True, comment='API版本'),
        
        # 模型参数
        sa.Column('max_tokens', sa.Integer(), default=4000, comment='最大Token数'),
        sa.Column('temperature', sa.Float(), default=0.7, comment='温度参数'),
        sa.Column('top_p', sa.Float(), default=1.0, comment='Top-p参数'),
        sa.Column('frequency_penalty', sa.Float(), default=0.0, comment='频率惩罚'),
        sa.Column('presence_penalty', sa.Float(), default=0.0, comment='存在惩罚'),
        
        # 状态和限制
        sa.Column('is_enabled', sa.Boolean(), default=True, comment='是否启用'),
        sa.Column('is_default', sa.Boolean(), default=False, comment='是否为默认模型'),
        sa.Column('daily_quota', sa.Integer(), nullable=True, comment='每日配额'),
        sa.Column('monthly_quota', sa.Integer(), nullable=True, comment='每月配额'),
        sa.Column('cost_per_token', sa.Float(), nullable=True, comment='每Token成本'),
        
        # 能力标签
        sa.Column('capabilities', sa.JSON(), nullable=True, comment='模型能力标签'),
        sa.Column('supported_languages', sa.JSON(), nullable=True, comment='支持的语言'),
        sa.Column('use_cases', sa.JSON(), nullable=True, comment='适用场景'),
        
        # 性能指标
        sa.Column('avg_response_time', sa.Float(), nullable=True, comment='平均响应时间（秒）'),
        sa.Column('success_rate', sa.Float(), nullable=True, comment='成功率'),
        sa.Column('last_health_check', sa.DateTime(), nullable=True, comment='最后健康检查时间'),
        
        # 使用统计
        sa.Column('total_requests', sa.Integer(), default=0, comment='总请求数'),
        sa.Column('total_tokens_used', sa.Integer(), default=0, comment='总Token使用量'),
        sa.Column('total_cost', sa.Float(), default=0.0, comment='总成本'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'model_name', name='uk_provider_model'),
        comment='AI模型配置表'
    )
    
    # 创建AI模型配置表索引
    op.create_index('idx_ai_model_configs_provider', 'ai_model_configs', ['provider'])
    op.create_index('idx_ai_model_configs_is_enabled', 'ai_model_configs', ['is_enabled'])
    op.create_index('idx_ai_model_configs_is_default', 'ai_model_configs', ['is_default'])
    
    # 创建AI聊天会话表
    op.create_table(
        'ai_chat_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('title', sa.String(200), nullable=False, comment='会话标题'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('status', sa.Enum('ACTIVE', 'ARCHIVED', 'DELETED', name='sessionstatus'), 
                 default='ACTIVE', nullable=False, comment='会话状态'),
        
        # 会话配置
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=True, comment='AI模型名称'),
        sa.Column('system_prompt', sa.Text(), nullable=True, comment='系统提示词'),
        
        # 统计信息
        sa.Column('message_count', sa.Integer(), default=0, comment='消息数量'),
        sa.Column('total_tokens', sa.Integer(), default=0, comment='总Token数'),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True, comment='最后活动时间'),
        
        # 会话元数据
        sa.Column('tags', sa.Text(), nullable=True, comment='标签（JSON格式）'),
        sa.Column('session_metadata', sa.Text(), nullable=True, comment='元数据（JSON格式）'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        comment='AI聊天会话表'
    )
    
    # 创建AI聊天会话表索引
    op.create_index('idx_ai_chat_sessions_user_id', 'ai_chat_sessions', ['user_id'])
    op.create_index('idx_ai_chat_sessions_status', 'ai_chat_sessions', ['status'])
    op.create_index('idx_ai_chat_sessions_ai_provider', 'ai_chat_sessions', ['ai_provider'])
    op.create_index('idx_ai_chat_sessions_last_activity_at', 'ai_chat_sessions', ['last_activity_at'])
    
    # 创建AI聊天消息表
    op.create_table(
        'ai_chat_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('session_id', sa.Integer(), nullable=False, comment='会话ID'),
        sa.Column('role', sa.Enum('USER', 'ASSISTANT', 'SYSTEM', name='messagerole'), 
                 nullable=False, comment='消息角色'),
        sa.Column('content', sa.Text(), nullable=False, comment='消息内容'),
        sa.Column('content_type', sa.Enum('TEXT', 'MARKDOWN', 'CODE', 'IMAGE', 'FILE', name='contenttype'), 
                 default='TEXT', comment='内容类型'),
        
        # AI相关信息
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=True, comment='AI模型名称'),
        sa.Column('tokens_used', sa.Integer(), default=0, comment='使用的Token数'),
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='置信度分数'),
        
        # 消息状态
        sa.Column('is_streaming', sa.Boolean(), default=False, comment='是否为流式消息'),
        sa.Column('is_error', sa.Boolean(), default=False, comment='是否为错误消息'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        
        # 消息元数据
        sa.Column('message_metadata', sa.Text(), nullable=True, comment='元数据（JSON格式）'),
        sa.Column('parent_message_id', sa.Integer(), nullable=True, comment='父消息ID'),
        
        # 用户交互
        sa.Column('user_rating', sa.Integer(), nullable=True, comment='用户评分（1-5）'),
        sa.Column('user_feedback', sa.Text(), nullable=True, comment='用户反馈'),
        sa.Column('is_bookmarked', sa.Boolean(), default=False, comment='是否收藏'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['ai_chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_message_id'], ['ai_chat_messages.id'], ondelete='SET NULL'),
        comment='AI聊天消息表'
    )
    
    # 创建AI聊天消息表索引
    op.create_index('idx_ai_chat_messages_session_id', 'ai_chat_messages', ['session_id'])
    op.create_index('idx_ai_chat_messages_role', 'ai_chat_messages', ['role'])
    op.create_index('idx_ai_chat_messages_ai_provider', 'ai_chat_messages', ['ai_provider'])
    op.create_index('idx_ai_chat_messages_created_at', 'ai_chat_messages', ['created_at'])
    op.create_index('idx_ai_chat_messages_parent_message_id', 'ai_chat_messages', ['parent_message_id'])
    
    # 创建AI提示词模板表
    op.create_table(
        'ai_prompt_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('name', sa.String(200), nullable=False, comment='模板名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='模板描述'),
        sa.Column('category', sa.Enum('GENERAL', 'CODE_GENERATION', 'TEST_CASE', 'DOCUMENT_WRITING', 
                                     'DATA_ANALYSIS', 'CREATIVE_WRITING', 'LEARNING_EDUCATION', 
                                     'PROJECT_MANAGEMENT', name='templatecategory'), 
                 nullable=False, comment='模板分类'),
        
        # 模板内容
        sa.Column('content', sa.Text(), nullable=False, comment='模板内容'),
        sa.Column('variables', sa.JSON(), nullable=True, comment='模板变量定义'),
        sa.Column('example_values', sa.JSON(), nullable=True, comment='示例变量值'),
        
        # 作者和权限
        sa.Column('author_id', sa.Integer(), nullable=False, comment='作者ID'),
        sa.Column('visibility', sa.Enum('PRIVATE', 'TEAM', 'PUBLIC', name='templatevisibility'), 
                 default='PRIVATE', comment='可见性'),
        sa.Column('team_id', sa.Integer(), nullable=True, comment='团队ID'),
        
        # 模板配置
        sa.Column('recommended_models', sa.JSON(), nullable=True, comment='推荐的AI模型'),
        sa.Column('default_parameters', sa.JSON(), nullable=True, comment='默认参数配置'),
        
        # 统计信息
        sa.Column('usage_count', sa.Integer(), default=0, comment='使用次数'),
        sa.Column('rating_sum', sa.Integer(), default=0, comment='评分总和'),
        sa.Column('rating_count', sa.Integer(), default=0, comment='评分次数'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后使用时间'),
        
        # 状态
        sa.Column('is_active', sa.Boolean(), default=True, comment='是否激活'),
        sa.Column('is_featured', sa.Boolean(), default=False, comment='是否为精选模板'),
        
        # 版本控制
        sa.Column('version', sa.String(20), default='1.0.0', comment='版本号'),
        sa.Column('parent_template_id', sa.Integer(), nullable=True, comment='父模板ID'),
        
        # 标签和元数据
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签'),
        sa.Column('template_metadata', sa.JSON(), nullable=True, comment='元数据'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_template_id'], ['ai_prompt_templates.id'], ondelete='SET NULL'),
        comment='AI提示词模板表'
    )
    
    # 创建AI提示词模板表索引
    op.create_index('idx_ai_prompt_templates_author_id', 'ai_prompt_templates', ['author_id'])
    op.create_index('idx_ai_prompt_templates_category', 'ai_prompt_templates', ['category'])
    op.create_index('idx_ai_prompt_templates_visibility', 'ai_prompt_templates', ['visibility'])
    op.create_index('idx_ai_prompt_templates_is_active', 'ai_prompt_templates', ['is_active'])
    op.create_index('idx_ai_prompt_templates_is_featured', 'ai_prompt_templates', ['is_featured'])
    
    # 创建AI提示词模板使用记录表
    op.create_table(
        'ai_prompt_template_usage',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('template_id', sa.Integer(), nullable=False, comment='模板ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        
        # 使用信息
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='使用的AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=True, comment='使用的AI模型'),
        sa.Column('use_case', sa.String(200), nullable=True, comment='使用场景'),
        
        # 使用结果
        sa.Column('success', sa.Boolean(), default=True, comment='是否成功'),
        sa.Column('tokens_used', sa.Integer(), nullable=True, comment='使用的Token数'),
        sa.Column('response_time', sa.Float(), nullable=True, comment='响应时间（秒）'),
        
        # 用户反馈
        sa.Column('user_rating', sa.Integer(), nullable=True, comment='用户评分（1-5）'),
        sa.Column('user_feedback', sa.Text(), nullable=True, comment='用户反馈'),
        
        # 使用的变量值
        sa.Column('variable_values', sa.JSON(), nullable=True, comment='使用的变量值'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['template_id'], ['ai_prompt_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        comment='AI提示词模板使用记录表'
    )
    
    # 创建AI提示词模板使用记录表索引
    op.create_index('idx_ai_prompt_template_usage_template_id', 'ai_prompt_template_usage', ['template_id'])
    op.create_index('idx_ai_prompt_template_usage_user_id', 'ai_prompt_template_usage', ['user_id'])
    op.create_index('idx_ai_prompt_template_usage_ai_provider', 'ai_prompt_template_usage', ['ai_provider'])
    op.create_index('idx_ai_prompt_template_usage_created_at', 'ai_prompt_template_usage', ['created_at'])
    
    # 创建AI使用统计表
    op.create_table(
        'ai_usage_stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('date', sa.Date(), nullable=False, comment='统计日期'),
        
        # AI服务信息
        sa.Column('ai_provider', sa.String(50), nullable=False, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=False, comment='AI模型'),
        
        # 使用统计
        sa.Column('request_count', sa.Integer(), default=0, comment='请求次数'),
        sa.Column('success_count', sa.Integer(), default=0, comment='成功次数'),
        sa.Column('error_count', sa.Integer(), default=0, comment='错误次数'),
        
        # Token统计
        sa.Column('input_tokens', sa.Integer(), default=0, comment='输入Token数'),
        sa.Column('output_tokens', sa.Integer(), default=0, comment='输出Token数'),
        sa.Column('total_tokens', sa.Integer(), default=0, comment='总Token数'),
        
        # 成本统计
        sa.Column('total_cost', sa.Float(), default=0.0, comment='总成本'),
        
        # 性能统计
        sa.Column('avg_response_time', sa.Float(), nullable=True, comment='平均响应时间（秒）'),
        sa.Column('min_response_time', sa.Float(), nullable=True, comment='最小响应时间（秒）'),
        sa.Column('max_response_time', sa.Float(), nullable=True, comment='最大响应时间（秒）'),
        
        # 使用场景统计
        sa.Column('use_case_stats', sa.JSON(), nullable=True, comment='使用场景统计'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', 'ai_provider', 'ai_model', name='uk_user_date_provider_model'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        comment='AI使用统计表'
    )
    
    # 创建AI使用统计表索引
    op.create_index('idx_ai_usage_stats_user_id', 'ai_usage_stats', ['user_id'])
    op.create_index('idx_ai_usage_stats_date', 'ai_usage_stats', ['date'])
    op.create_index('idx_ai_usage_stats_ai_provider', 'ai_usage_stats', ['ai_provider'])
    op.create_index('idx_ai_usage_stats_ai_model', 'ai_usage_stats', ['ai_model'])
    
    # 创建AI系统统计表
    op.create_table(
        'ai_system_stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('date', sa.Date(), nullable=False, comment='统计日期'),
        sa.Column('hour', sa.Integer(), nullable=True, comment='小时（0-23，用于小时级统计）'),
        
        # 系统级统计
        sa.Column('total_users', sa.Integer(), default=0, comment='总用户数'),
        sa.Column('active_users', sa.Integer(), default=0, comment='活跃用户数'),
        sa.Column('total_requests', sa.Integer(), default=0, comment='总请求数'),
        sa.Column('total_tokens', sa.Integer(), default=0, comment='总Token数'),
        sa.Column('total_cost', sa.Float(), default=0.0, comment='总成本'),
        
        # 各提供商统计
        sa.Column('provider_stats', sa.JSON(), nullable=True, comment='各提供商统计'),
        sa.Column('model_stats', sa.JSON(), nullable=True, comment='各模型统计'),
        
        # 性能统计
        sa.Column('avg_response_time', sa.Float(), nullable=True, comment='平均响应时间'),
        sa.Column('system_availability', sa.Float(), nullable=True, comment='系统可用性'),
        
        # 错误统计
        sa.Column('error_count', sa.Integer(), default=0, comment='错误次数'),
        sa.Column('error_types', sa.JSON(), nullable=True, comment='错误类型统计'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date', 'hour', name='uk_date_hour'),
        comment='AI系统统计表'
    )
    
    # 创建AI系统统计表索引
    op.create_index('idx_ai_system_stats_date', 'ai_system_stats', ['date'])
    op.create_index('idx_ai_system_stats_hour', 'ai_system_stats', ['hour'])
    
    print("AI助手模块表创建完成")


def downgrade():
    """删除AI助手模块相关表"""
    op.drop_table('ai_system_stats')
    op.drop_table('ai_usage_stats')
    op.drop_table('ai_prompt_template_usage')
    op.drop_table('ai_prompt_templates')
    op.drop_table('ai_chat_messages')
    op.drop_table('ai_chat_sessions')
    op.drop_table('ai_model_configs')
    
    print("AI助手模块表删除完成")