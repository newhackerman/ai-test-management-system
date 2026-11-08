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
down_revision = ('004_init_config_data', '001_ai_assistant')
branch_labels = None
depends_on = None


def upgrade():
    """创建AI助手模块相关表"""
    
    # 创建AI提示词模板使用记录表
    op.create_table(
        'ai_prompt_template_usage',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        
        # 基本信息
        sa.Column('template_id', sa.BigInteger(), nullable=False, comment='模板ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        
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
    
    # 创建AI系统统计表
    op.create_table(
        'ai_system_stats',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新人ID'),
        
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
    op.drop_table('ai_prompt_template_usage')
    
    print("AI助手模块表删除完成")