"""Create AI Assistant tables

Revision ID: 001_ai_assistant
Revises: 
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001_ai_assistant'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create AI Assistant module tables"""
    
    # 1. Create ai_chat_sessions table
    op.create_table(
        'ai_chat_sessions',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='主键ID'),
        sa.Column('title', sa.String(200), nullable=False, comment='会话标题'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        sa.Column('status', sa.Enum('ACTIVE', 'ARCHIVED', 'DELETED', name='sessionstatus'), 
                 nullable=False, default='ACTIVE', comment='会话状态'),
        
        # 会话配置
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=True, comment='AI模型名称'),
        sa.Column('system_prompt', sa.Text(), nullable=True, comment='系统提示词'),
        sa.Column('session_config', sa.JSON(), nullable=True, comment='会话配置参数'),
        
        # 统计信息
        sa.Column('message_count', sa.Integer(), nullable=False, default=0, comment='消息数量'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, default=0, comment='总Token数'),
        sa.Column('total_cost', sa.DECIMAL(10, 4), nullable=False, default=0.0000, comment='总成本'),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='最后活动时间'),
        
        # 会话元数据
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签列表'),
        sa.Column('session_metadata', sa.JSON(), nullable=True, comment='会话元数据'),
        sa.Column('is_shared', sa.Boolean(), nullable=False, default=False, comment='是否共享'),
        sa.Column('share_token', sa.String(64), nullable=True, comment='分享令牌'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='AI聊天会话表'
    )
    
    # Create indexes for ai_chat_sessions
    op.create_index('idx_user_id', 'ai_chat_sessions', ['user_id'])
    op.create_index('idx_status', 'ai_chat_sessions', ['status'])
    op.create_index('idx_ai_provider', 'ai_chat_sessions', ['ai_provider'])
    op.create_index('idx_ai_model', 'ai_chat_sessions', ['ai_model'])
    op.create_index('idx_last_activity', 'ai_chat_sessions', ['last_activity_at'])
    op.create_index('idx_created_at', 'ai_chat_sessions', ['created_at'])
    op.create_index('idx_share_token', 'ai_chat_sessions', ['share_token'])
    op.create_index('idx_expires_at', 'ai_chat_sessions', ['expires_at'])
    op.create_index('idx_user_status_activity', 'ai_chat_sessions', ['user_id', 'status', 'last_activity_at'])
    op.create_index('idx_provider_model_created', 'ai_chat_sessions', ['ai_provider', 'ai_model', 'created_at'])
    
    # 2. Create ai_chat_messages table
    op.create_table(
        'ai_chat_messages',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='主键ID'),
        sa.Column('session_id', sa.BigInteger(), nullable=False, comment='会话ID'),
        sa.Column('role', sa.Enum('USER', 'ASSISTANT', 'SYSTEM', name='messagerole'), 
                 nullable=False, comment='消息角色'),
        sa.Column('content', sa.Text(length=4294967295), nullable=False, comment='消息内容'),
        sa.Column('content_type', sa.Enum('TEXT', 'MARKDOWN', 'CODE', 'IMAGE', 'FILE', name='contenttype'), 
                 nullable=False, default='TEXT', comment='内容类型'),
        
        # AI相关信息
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=True, comment='AI模型名称'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, default=0, comment='使用的Token数'),
        sa.Column('cost', sa.DECIMAL(8, 4), nullable=False, default=0.0000, comment='消息成本'),
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='置信度分数'),
        sa.Column('response_time', sa.Float(), nullable=True, comment='响应时间(秒)'),
        
        # 消息状态
        sa.Column('is_streaming', sa.Boolean(), nullable=False, default=False, comment='是否为流式消息'),
        sa.Column('is_error', sa.Boolean(), nullable=False, default=False, comment='是否为错误消息'),
        sa.Column('error_code', sa.String(50), nullable=True, comment='错误代码'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        
        # 消息元数据
        sa.Column('message_metadata', sa.JSON(), nullable=True, comment='消息元数据'),
        sa.Column('parent_message_id', sa.BigInteger(), nullable=True, comment='父消息ID'),
        sa.Column('thread_id', sa.String(100), nullable=True, comment='线程ID'),
        
        # 用户交互
        sa.Column('user_rating', sa.SmallInteger(), nullable=True, comment='用户评分（1-5）'),
        sa.Column('user_feedback', sa.Text(), nullable=True, comment='用户反馈'),
        sa.Column('is_bookmarked', sa.Boolean(), nullable=False, default=False, comment='是否收藏'),
        sa.Column('is_regenerated', sa.Boolean(), nullable=False, default=False, comment='是否重新生成'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['ai_chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_message_id'], ['ai_chat_messages.id'], ondelete='SET NULL'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='AI聊天消息表'
    )
    
    # Create indexes for ai_chat_messages
    op.create_index('idx_session_id', 'ai_chat_messages', ['session_id'])
    op.create_index('idx_role', 'ai_chat_messages', ['role'])
    op.create_index('idx_content_type', 'ai_chat_messages', ['content_type'])
    op.create_index('idx_ai_provider', 'ai_chat_messages', ['ai_provider'])
    op.create_index('idx_ai_model', 'ai_chat_messages', ['ai_model'])
    op.create_index('idx_parent_message', 'ai_chat_messages', ['parent_message_id'])
    op.create_index('idx_thread_id', 'ai_chat_messages', ['thread_id'])
    op.create_index('idx_created_at', 'ai_chat_messages', ['created_at'])
    op.create_index('idx_is_bookmarked', 'ai_chat_messages', ['is_bookmarked'])
    op.create_index('idx_session_role_created', 'ai_chat_messages', ['session_id', 'role', 'created_at'])
    op.create_index('idx_provider_model_created', 'ai_chat_messages', ['ai_provider', 'ai_model', 'created_at'])
    op.create_index('idx_bookmarked_user', 'ai_chat_messages', ['is_bookmarked', 'created_at'])
    
    # 3. Create ai_model_configs table
    op.create_table(
        'ai_model_configs',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='主键ID'),
        sa.Column('provider', sa.String(50), nullable=False, comment='AI服务提供商'),
        sa.Column('model_name', sa.String(100), nullable=False, comment='模型名称'),
        sa.Column('display_name', sa.String(200), nullable=False, comment='显示名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='模型描述'),
        sa.Column('version', sa.String(50), nullable=True, comment='模型版本'),
        
        # 配置信息
        sa.Column('api_endpoint', sa.String(500), nullable=True, comment='API端点'),
        sa.Column('api_key', sa.String(500), nullable=True, comment='API密钥'),
        sa.Column('api_version', sa.String(50), nullable=True, comment='API版本'),
        sa.Column('headers', sa.JSON(), nullable=True, comment='请求头配置'),
        
        # 模型参数
        sa.Column('max_tokens', sa.Integer(), nullable=False, default=4000, comment='最大Token数'),
        sa.Column('temperature', sa.Float(), nullable=False, default=0.7, comment='温度参数'),
        sa.Column('top_p', sa.Float(), nullable=False, default=1.0, comment='Top-p参数'),
        sa.Column('frequency_penalty', sa.Float(), nullable=False, default=0.0, comment='频率惩罚'),
        sa.Column('presence_penalty', sa.Float(), nullable=False, default=0.0, comment='存在惩罚'),
        sa.Column('stop_sequences', sa.JSON(), nullable=True, comment='停止序列'),
        
        # 状态和限制
        sa.Column('is_enabled', sa.Boolean(), nullable=False, default=True, comment='是否启用'),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False, comment='是否为默认模型'),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=True, comment='是否公开可用'),
        sa.Column('priority', sa.Integer(), nullable=False, default=0, comment='优先级'),
        
        # 配额限制
        sa.Column('daily_quota', sa.Integer(), nullable=True, comment='每日配额'),
        sa.Column('monthly_quota', sa.Integer(), nullable=True, comment='每月配额'),
        sa.Column('user_daily_quota', sa.Integer(), nullable=True, comment='用户每日配额'),
        sa.Column('concurrent_limit', sa.Integer(), nullable=True, default=10, comment='并发限制'),
        
        # 成本配置
        sa.Column('cost_per_input_token', sa.DECIMAL(10, 8), nullable=True, comment='输入Token成本'),
        sa.Column('cost_per_output_token', sa.DECIMAL(10, 8), nullable=True, comment='输出Token成本'),
        sa.Column('cost_per_request', sa.DECIMAL(8, 4), nullable=True, comment='每请求成本'),
        
        # 能力标签
        sa.Column('capabilities', sa.JSON(), nullable=True, comment='模型能力标签'),
        sa.Column('supported_languages', sa.JSON(), nullable=True, comment='支持的语言'),
        sa.Column('use_cases', sa.JSON(), nullable=True, comment='适用场景'),
        sa.Column('model_features', sa.JSON(), nullable=True, comment='模型特性'),
        
        # 性能指标
        sa.Column('avg_response_time', sa.Float(), nullable=True, comment='平均响应时间（秒）'),
        sa.Column('success_rate', sa.Float(), nullable=True, comment='成功率'),
        sa.Column('last_health_check', sa.DateTime(), nullable=True, comment='最后健康检查时间'),
        sa.Column('health_status', sa.Enum('HEALTHY', 'DEGRADED', 'UNHEALTHY', 'UNKNOWN', name='healthstatus'), 
                 nullable=True, default='UNKNOWN', comment='健康状态'),
        
        # 使用统计
        sa.Column('total_requests', sa.BigInteger(), nullable=False, default=0, comment='总请求数'),
        sa.Column('total_tokens_used', sa.BigInteger(), nullable=False, default=0, comment='总Token使用量'),
        sa.Column('total_cost', sa.DECIMAL(12, 4), nullable=False, default=0.0000, comment='总成本'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后使用时间'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'model_name', name='uk_provider_model'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='AI模型配置表'
    )
    
    # Create indexes for ai_model_configs
    op.create_index('idx_provider', 'ai_model_configs', ['provider'])
    op.create_index('idx_is_enabled', 'ai_model_configs', ['is_enabled'])
    op.create_index('idx_is_default', 'ai_model_configs', ['is_default'])
    op.create_index('idx_is_public', 'ai_model_configs', ['is_public'])
    op.create_index('idx_priority', 'ai_model_configs', ['priority'])
    op.create_index('idx_health_status', 'ai_model_configs', ['health_status'])
    op.create_index('idx_last_health_check', 'ai_model_configs', ['last_health_check'])
    op.create_index('idx_created_at', 'ai_model_configs', ['created_at'])
    op.create_index('idx_enabled_public_priority', 'ai_model_configs', ['is_enabled', 'is_public', 'priority'])
    op.create_index('idx_provider_enabled', 'ai_model_configs', ['provider', 'is_enabled'])
    
    # 4. Create ai_prompt_templates table
    op.create_table(
        'ai_prompt_templates',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(200), nullable=False, comment='模板名称'),
        sa.Column('title', sa.String(300), nullable=False, comment='模板标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='模板描述'),
        sa.Column('content', sa.Text(length=4294967295), nullable=False, comment='模板内容'),
        sa.Column('category', sa.String(100), nullable=True, comment='模板分类'),
        sa.Column('subcategory', sa.String(100), nullable=True, comment='子分类'),
        
        # 模板配置
        sa.Column('variables', sa.JSON(), nullable=True, comment='模板变量定义'),
        sa.Column('default_values', sa.JSON(), nullable=True, comment='默认值'),
        sa.Column('validation_rules', sa.JSON(), nullable=True, comment='验证规则'),
        sa.Column('example_context', sa.JSON(), nullable=True, comment='示例上下文'),
        
        # 适用性
        sa.Column('supported_providers', sa.JSON(), nullable=True, comment='支持的AI提供商'),
        sa.Column('supported_models', sa.JSON(), nullable=True, comment='支持的模型'),
        sa.Column('use_cases', sa.JSON(), nullable=True, comment='使用场景'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签'),
        
        # 权限和可见性
        sa.Column('visibility', sa.Enum('PUBLIC', 'PRIVATE', 'TEAM', 'ORGANIZATION', name='templatevisibility'), 
                 nullable=False, default='PRIVATE', comment='可见性'),
        sa.Column('owner_id', sa.BigInteger(), nullable=False, comment='所有者ID'),
        sa.Column('team_id', sa.BigInteger(), nullable=True, comment='团队ID'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, default=False, comment='是否精选'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False, comment='是否已验证'),
        
        # 版本控制
        sa.Column('version', sa.String(20), nullable=False, default='1.0.0', comment='版本号'),
        sa.Column('parent_template_id', sa.BigInteger(), nullable=True, comment='父模板ID'),
        sa.Column('is_latest_version', sa.Boolean(), nullable=False, default=True, comment='是否最新版本'),
        
        # 使用统计
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0, comment='使用次数'),
        sa.Column('rating_avg', sa.Float(), nullable=True, comment='平均评分'),
        sa.Column('rating_count', sa.Integer(), nullable=False, default=0, comment='评分次数'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后使用时间'),
        
        # 基础字段
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'owner_id', name='uk_name_owner'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_template_id'], ['ai_prompt_templates.id'], ondelete='SET NULL'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='AI提示词模板表'
    )
    
    # Create indexes for ai_prompt_templates
    op.create_index('idx_category', 'ai_prompt_templates', ['category'])
    op.create_index('idx_subcategory', 'ai_prompt_templates', ['subcategory'])
    op.create_index('idx_visibility', 'ai_prompt_templates', ['visibility'])
    op.create_index('idx_owner_id', 'ai_prompt_templates', ['owner_id'])
    op.create_index('idx_team_id', 'ai_prompt_templates', ['team_id'])
    op.create_index('idx_is_featured', 'ai_prompt_templates', ['is_featured'])
    op.create_index('idx_is_verified', 'ai_prompt_templates', ['is_verified'])
    op.create_index('idx_parent_template', 'ai_prompt_templates', ['parent_template_id'])
    op.create_index('idx_usage_count', 'ai_prompt_templates', ['usage_count'])
    op.create_index('idx_rating_avg', 'ai_prompt_templates', ['rating_avg'])
    op.create_index('idx_created_at', 'ai_prompt_templates', ['created_at'])
    op.create_index('idx_category_visibility_featured', 'ai_prompt_templates', ['category', 'visibility', 'is_featured'])
    op.create_index('idx_owner_visibility_created', 'ai_prompt_templates', ['owner_id', 'visibility', 'created_at'])
    op.create_index('idx_usage_rating', 'ai_prompt_templates', ['usage_count', 'rating_avg'])


def downgrade() -> None:
    """Drop AI Assistant module tables"""
    
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('ai_prompt_templates')
    op.drop_table('ai_model_configs')
    op.drop_table('ai_chat_messages')
    op.drop_table('ai_chat_sessions')
    
    # Drop custom enum types
    op.execute("DROP TYPE IF EXISTS sessionstatus")
    op.execute("DROP TYPE IF EXISTS messagerole")
    op.execute("DROP TYPE IF EXISTS contenttype")
    op.execute("DROP TYPE IF EXISTS healthstatus")
    op.execute("DROP TYPE IF EXISTS templatevisibility")