"""
添加会议安全和隐私相关表

创建以下表：
- meeting_audit_logs: 会议审计日志
- meeting_privacy_settings: 会议隐私设置
- user_consents: 用户同意记录
- data_deletion_requests: 数据删除请求
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():
    """升级数据库"""
    
    # 1. 创建会议审计日志表
    op.create_table(
        'meeting_audit_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='审计日志ID'),
        sa.Column('event_type', sa.Enum(
            'MEETING_JOIN', 'MEETING_LEAVE', 'MEETING_CREATE', 'MEETING_UPDATE', 'MEETING_DELETE',
            'MEETING_START', 'MEETING_END', 'PERMISSION_GRANT', 'PERMISSION_REVOKE', 'ROLE_CHANGE',
            'ACCESS_DENIED', 'RECORDING_START', 'RECORDING_STOP', 'RECORDING_ACCESS', 'RECORDING_DOWNLOAD',
            'RECORDING_DELETE', 'FILE_UPLOAD', 'FILE_DOWNLOAD', 'FILE_DELETE', 'FILE_SHARE',
            'SECURITY_VIOLATION', 'SUSPICIOUS_ACTIVITY', 'AUTHENTICATION_FAILURE', 'TOKEN_VALIDATION_FAILURE',
            'SYSTEM_ERROR', 'CONFIGURATION_CHANGE',
            name='auditeventtype'
        ), nullable=False, comment='事件类型'),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='auditseverity'), 
                 default='LOW', nullable=False, comment='严重级别'),
        sa.Column('meeting_id', sa.BigInteger(), nullable=True, comment='会议ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='用户ID'),
        sa.Column('session_id', sa.String(100), nullable=True, comment='会话ID'),
        sa.Column('event_description', sa.Text(), nullable=False, comment='事件描述'),
        sa.Column('event_details', sa.JSON(), nullable=True, comment='事件详细信息'),
        sa.Column('ip_address', sa.String(45), nullable=True, comment='IP地址'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='用户代理'),
        sa.Column('success', sa.Boolean(), default=True, comment='操作是否成功'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('event_timestamp', sa.DateTime(), default=sa.func.current_timestamp(), nullable=False, comment='事件时间'),
        sa.Column('additional_data', sa.JSON(), nullable=True, comment='附加数据'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.current_timestamp(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.current_timestamp(), 
                 onupdate=sa.func.current_timestamp(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建者ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新者ID'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建审计日志索引
    op.create_index('idx_audit_event_type', 'meeting_audit_logs', ['event_type'])
    op.create_index('idx_audit_severity', 'meeting_audit_logs', ['severity'])
    op.create_index('idx_audit_meeting_id', 'meeting_audit_logs', ['meeting_id'])
    op.create_index('idx_audit_user_id', 'meeting_audit_logs', ['user_id'])
    op.create_index('idx_audit_session_id', 'meeting_audit_logs', ['session_id'])
    op.create_index('idx_audit_ip_address', 'meeting_audit_logs', ['ip_address'])
    op.create_index('idx_audit_event_timestamp', 'meeting_audit_logs', ['event_timestamp'])
    
    # 2. 创建会议隐私设置表
    op.create_table(
        'meeting_privacy_settings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='隐私设置ID'),
        sa.Column('meeting_id', sa.BigInteger(), nullable=False, unique=True, comment='会议ID'),
        sa.Column('privacy_level', sa.Enum('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED', name='privacylevel'),
                 default='INTERNAL', nullable=False, comment='隐私级别'),
        sa.Column('data_retention_policy', sa.Enum('SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM', 'PERMANENT', 'CUSTOM', 
                 name='dataretentionpolicy'), default='MEDIUM_TERM', nullable=False, comment='数据保留策略'),
        sa.Column('retention_days', sa.Integer(), nullable=True, comment='自定义保留天数'),
        sa.Column('recording_consent_required', sa.Boolean(), default=True, comment='是否需要录制同意'),
        sa.Column('analytics_consent_required', sa.Boolean(), default=False, comment='是否需要分析同意'),
        sa.Column('data_processing_consent_required', sa.Boolean(), default=True, comment='是否需要数据处理同意'),
        sa.Column('allow_transcription', sa.Boolean(), default=True, comment='是否允许转录'),
        sa.Column('allow_ai_analysis', sa.Boolean(), default=True, comment='是否允许AI分析'),
        sa.Column('allow_data_export', sa.Boolean(), default=False, comment='是否允许数据导出'),
        sa.Column('data_residency_region', sa.String(50), nullable=True, comment='数据驻留地区'),
        sa.Column('cross_border_transfer_allowed', sa.Boolean(), default=False, comment='是否允许跨境传输'),
        sa.Column('auto_delete_enabled', sa.Boolean(), default=True, comment='是否启用自动删除'),
        sa.Column('auto_delete_date', sa.DateTime(), nullable=True, comment='自动删除日期'),
        sa.Column('anonymization_enabled', sa.Boolean(), default=False, comment='是否启用匿名化'),
        sa.Column('anonymization_delay_days', sa.Integer(), default=30, comment='匿名化延迟天数'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.current_timestamp(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.current_timestamp(), 
                 onupdate=sa.func.current_timestamp(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建者ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新者ID'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建隐私设置索引
    op.create_index('idx_privacy_meeting_id', 'meeting_privacy_settings', ['meeting_id'])
    op.create_index('idx_privacy_level', 'meeting_privacy_settings', ['privacy_level'])
    op.create_index('idx_privacy_retention_policy', 'meeting_privacy_settings', ['data_retention_policy'])
    op.create_index('idx_privacy_auto_delete_date', 'meeting_privacy_settings', ['auto_delete_date'])
    
    # 3. 创建用户同意记录表
    op.create_table(
        'user_consents',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='同意记录ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        sa.Column('meeting_id', sa.BigInteger(), nullable=False, comment='会议ID'),
        sa.Column('consent_type', sa.Enum('RECORDING', 'DATA_PROCESSING', 'ANALYTICS', 'MARKETING', name='consenttype'),
                 nullable=False, comment='同意类型'),
        sa.Column('consent_given', sa.Boolean(), nullable=False, comment='是否同意'),
        sa.Column('consent_timestamp', sa.DateTime(), default=sa.func.current_timestamp(), nullable=False, comment='同意时间'),
        sa.Column('consent_version', sa.String(20), nullable=True, comment='同意版本'),
        sa.Column('consent_text', sa.Text(), nullable=True, comment='同意文本'),
        sa.Column('ip_address', sa.String(45), nullable=True, comment='IP地址'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='用户代理'),
        sa.Column('revoked', sa.Boolean(), default=False, comment='是否已撤销'),
        sa.Column('revoked_timestamp', sa.DateTime(), nullable=True, comment='撤销时间'),
        sa.Column('revoked_reason', sa.Text(), nullable=True, comment='撤销原因'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.current_timestamp(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.current_timestamp(), 
                 onupdate=sa.func.current_timestamp(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建者ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新者ID'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建用户同意索引
    op.create_index('idx_consent_user_id', 'user_consents', ['user_id'])
    op.create_index('idx_consent_meeting_id', 'user_consents', ['meeting_id'])
    op.create_index('idx_consent_type', 'user_consents', ['consent_type'])
    op.create_index('idx_consent_timestamp', 'user_consents', ['consent_timestamp'])
    op.create_index('idx_consent_revoked', 'user_consents', ['revoked'])
    
    # 4. 创建数据删除请求表
    op.create_table(
        'data_deletion_requests',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='删除请求ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='用户ID'),
        sa.Column('request_type', sa.String(50), nullable=False, comment='请求类型'),
        sa.Column('reason', sa.Text(), nullable=True, comment='删除原因'),
        sa.Column('scope', sa.JSON(), nullable=True, comment='删除范围'),
        sa.Column('status', sa.String(20), default='pending', comment='处理状态'),
        sa.Column('processed_by', sa.BigInteger(), nullable=True, comment='处理人ID'),
        sa.Column('processed_at', sa.DateTime(), nullable=True, comment='处理时间'),
        sa.Column('completion_details', sa.JSON(), nullable=True, comment='完成详情'),
        sa.Column('verification_token', sa.String(100), nullable=True, comment='验证令牌'),
        sa.Column('verified', sa.Boolean(), default=False, comment='是否已验证'),
        sa.Column('verified_at', sa.DateTime(), nullable=True, comment='验证时间'),
        sa.Column('created_at', sa.DateTime(), default=sa.func.current_timestamp(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.current_timestamp(), 
                 onupdate=sa.func.current_timestamp(), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建者ID'),
        sa.Column('updated_by', sa.BigInteger(), nullable=True, comment='更新者ID'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )
    
    # 创建删除请求索引
    op.create_index('idx_deletion_user_id', 'data_deletion_requests', ['user_id'])
    op.create_index('idx_deletion_request_type', 'data_deletion_requests', ['request_type'])
    op.create_index('idx_deletion_status', 'data_deletion_requests', ['status'])
    op.create_index('idx_deletion_processed_by', 'data_deletion_requests', ['processed_by'])
    op.create_index('idx_deletion_verified', 'data_deletion_requests', ['verified'])


def downgrade():
    """降级数据库"""
    
    # 删除索引
    op.drop_index('idx_deletion_verified', 'data_deletion_requests')
    op.drop_index('idx_deletion_processed_by', 'data_deletion_requests')
    op.drop_index('idx_deletion_status', 'data_deletion_requests')
    op.drop_index('idx_deletion_request_type', 'data_deletion_requests')
    op.drop_index('idx_deletion_user_id', 'data_deletion_requests')
    
    op.drop_index('idx_consent_revoked', 'user_consents')
    op.drop_index('idx_consent_timestamp', 'user_consents')
    op.drop_index('idx_consent_type', 'user_consents')
    op.drop_index('idx_consent_meeting_id', 'user_consents')
    op.drop_index('idx_consent_user_id', 'user_consents')
    
    op.drop_index('idx_privacy_auto_delete_date', 'meeting_privacy_settings')
    op.drop_index('idx_privacy_retention_policy', 'meeting_privacy_settings')
    op.drop_index('idx_privacy_level', 'meeting_privacy_settings')
    op.drop_index('idx_privacy_meeting_id', 'meeting_privacy_settings')
    
    op.drop_index('idx_audit_event_timestamp', 'meeting_audit_logs')
    op.drop_index('idx_audit_ip_address', 'meeting_audit_logs')
    op.drop_index('idx_audit_session_id', 'meeting_audit_logs')
    op.drop_index('idx_audit_user_id', 'meeting_audit_logs')
    op.drop_index('idx_audit_meeting_id', 'meeting_audit_logs')
    op.drop_index('idx_audit_severity', 'meeting_audit_logs')
    op.drop_index('idx_audit_event_type', 'meeting_audit_logs')
    
    # 删除表
    op.drop_table('data_deletion_requests')
    op.drop_table('user_consents')
    op.drop_table('meeting_privacy_settings')
    op.drop_table('meeting_audit_logs')
    
    # 删除枚举类型
    op.execute("DROP TYPE IF EXISTS consenttype")
    op.execute("DROP TYPE IF EXISTS dataretentionpolicy")
    op.execute("DROP TYPE IF EXISTS privacylevel")
    op.execute("DROP TYPE IF EXISTS auditseverity")
    op.execute("DROP TYPE IF EXISTS auditeventtype")