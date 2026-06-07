"""Add AI alert configuration tables

Revision ID: add_ai_alert_config_tables
Revises: 
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_ai_alert_config_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create ai_alert_configs table
    op.create_table('ai_alert_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False, comment='告警名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='告警描述'),
        sa.Column('alert_type', sa.Enum('cost_budget', 'token_quota', 'request_quota', 'response_time', 'error_rate', 'model_health', 'concurrent_limit', 'system_resource', name='alerttype'), nullable=False, comment='告警类型'),
        sa.Column('alert_level', sa.Enum('info', 'warning', 'critical', 'emergency', name='alertlevel'), nullable=False, comment='告警级别'),
        sa.Column('status', sa.Enum('active', 'inactive', 'triggered', 'resolved', 'disabled', name='alertstatus'), nullable=False, comment='告警状态'),
        sa.Column('threshold_value', sa.Float(), nullable=True, comment='阈值'),
        sa.Column('threshold_operator', sa.String(length=10), nullable=True, comment='阈值操作符 (>=, <=, ==, !=)'),
        sa.Column('threshold_unit', sa.String(length=50), nullable=True, comment='阈值单位'),
        sa.Column('time_window_minutes', sa.Integer(), nullable=True, comment='时间窗口(分钟)'),
        sa.Column('evaluation_frequency_minutes', sa.Integer(), nullable=True, comment='评估频率(分钟)'),
        sa.Column('target_providers', sa.JSON(), nullable=True, comment='目标AI提供商列表'),
        sa.Column('target_models', sa.JSON(), nullable=True, comment='目标模型列表'),
        sa.Column('target_users', sa.JSON(), nullable=True, comment='目标用户列表'),
        sa.Column('target_departments', sa.JSON(), nullable=True, comment='目标部门列表'),
        sa.Column('notification_channels', sa.JSON(), nullable=True, comment='通知渠道配置'),
        sa.Column('notification_recipients', sa.JSON(), nullable=True, comment='通知接收者'),
        sa.Column('notification_template', sa.Text(), nullable=True, comment='通知模板'),
        sa.Column('suppress_duration_minutes', sa.Integer(), nullable=True, comment='抑制时长(分钟)'),
        sa.Column('max_alerts_per_hour', sa.Integer(), nullable=True, comment='每小时最大告警数'),
        sa.Column('auto_resolve', sa.Boolean(), nullable=True, comment='是否自动解决'),
        sa.Column('auto_resolve_threshold', sa.Float(), nullable=True, comment='自动解决阈值'),
        sa.Column('auto_action', sa.JSON(), nullable=True, comment='自动处理动作配置'),
        sa.Column('trigger_count', sa.Integer(), nullable=True, comment='触发次数'),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True, comment='最后触发时间'),
        sa.Column('last_resolved_at', sa.DateTime(), nullable=True, comment='最后解决时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建者用户ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # Create indexes for ai_alert_configs
    op.create_index('idx_ai_alert_configs_name', 'ai_alert_configs', ['name'])
    op.create_index('idx_ai_alert_configs_type', 'ai_alert_configs', ['alert_type'])
    op.create_index('idx_ai_alert_configs_level', 'ai_alert_configs', ['alert_level'])
    op.create_index('idx_ai_alert_configs_status', 'ai_alert_configs', ['status'])
    op.create_index('idx_ai_alert_configs_created_by', 'ai_alert_configs', ['created_by'])
    op.create_index('idx_ai_alert_configs_created_at', 'ai_alert_configs', ['created_at'])
    
    # Create ai_alert_history table
    op.create_table('ai_alert_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_config_id', sa.Integer(), nullable=False, comment='告警配置ID'),
        sa.Column('alert_level', sa.Enum('info', 'warning', 'critical', 'emergency', name='alertlevel'), nullable=False, comment='告警级别'),
        sa.Column('alert_message', sa.Text(), nullable=False, comment='告警消息'),
        sa.Column('alert_details', sa.JSON(), nullable=True, comment='告警详细信息'),
        sa.Column('triggered_value', sa.Float(), nullable=True, comment='触发时的值'),
        sa.Column('threshold_value', sa.Float(), nullable=True, comment='阈值'),
        sa.Column('trigger_context', sa.JSON(), nullable=True, comment='触发上下文'),
        sa.Column('status', sa.Enum('active', 'inactive', 'triggered', 'resolved', 'disabled', name='alertstatus'), nullable=False, comment='告警状态'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True, comment='解决时间'),
        sa.Column('resolved_by', sa.Integer(), nullable=True, comment='解决者用户ID'),
        sa.Column('resolution_note', sa.Text(), nullable=True, comment='解决备注'),
        sa.Column('notification_sent', sa.Boolean(), nullable=True, comment='是否已发送通知'),
        sa.Column('notification_channels_used', sa.JSON(), nullable=True, comment='使用的通知渠道'),
        sa.Column('notification_failures', sa.JSON(), nullable=True, comment='通知失败信息'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # Create indexes for ai_alert_history
    op.create_index('idx_ai_alert_history_config_id', 'ai_alert_history', ['alert_config_id'])
    op.create_index('idx_ai_alert_history_level', 'ai_alert_history', ['alert_level'])
    op.create_index('idx_ai_alert_history_status', 'ai_alert_history', ['status'])
    op.create_index('idx_ai_alert_history_created_at', 'ai_alert_history', ['created_at'])
    op.create_index('idx_ai_alert_history_resolved_at', 'ai_alert_history', ['resolved_at'])
    op.create_index('idx_ai_alert_history_resolved_by', 'ai_alert_history', ['resolved_by'])
    
    # Create ai_alert_suppressions table
    op.create_table('ai_alert_suppressions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_config_id', sa.Integer(), nullable=False, comment='告警配置ID'),
        sa.Column('suppression_reason', sa.String(length=500), nullable=False, comment='抑制原因'),
        sa.Column('suppressed_until', sa.DateTime(), nullable=False, comment='抑制到期时间'),
        sa.Column('created_by', sa.Integer(), nullable=False, comment='创建者用户ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # Create indexes for ai_alert_suppressions
    op.create_index('idx_ai_alert_suppressions_config_id', 'ai_alert_suppressions', ['alert_config_id'])
    op.create_index('idx_ai_alert_suppressions_suppressed_until', 'ai_alert_suppressions', ['suppressed_until'])
    op.create_index('idx_ai_alert_suppressions_created_by', 'ai_alert_suppressions', ['created_by'])
    op.create_index('idx_ai_alert_suppressions_created_at', 'ai_alert_suppressions', ['created_at'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('ai_alert_suppressions')
    op.drop_table('ai_alert_history')
    op.drop_table('ai_alert_configs')
    
    # Drop custom enums
    op.execute("DROP TYPE IF EXISTS alerttype")
    op.execute("DROP TYPE IF EXISTS alertlevel") 
    op.execute("DROP TYPE IF EXISTS alertstatus")