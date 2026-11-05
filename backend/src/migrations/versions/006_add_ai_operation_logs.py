"""添加AI操作日志表

Revision ID: 006_add_ai_operation_logs
Revises: 005_add_project_tables
Create Date: 2024-12-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '006_add_ai_operation_logs'
down_revision = '005_add_project_tables'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构"""
    
    # 创建AI操作日志表
    op.create_table('ai_operation_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        # 基本信息
        sa.Column('user_id', sa.Integer(), nullable=True, comment='操作用户ID'),
        sa.Column('session_id', sa.String(100), nullable=True, comment='会话ID'),
        sa.Column('operation_type', sa.Enum(
            'CONVERSATION_CREATE', 'CONVERSATION_DELETE', 'MESSAGE_SEND', 'MESSAGE_RECEIVE',
            'AI_MODEL_CALL', 'AI_STREAMING_START', 'AI_STREAMING_COMPLETE',
            'SUGGESTION_GENERATE', 'SUGGESTION_ACCEPT', 'SUGGESTION_REJECT', 'SUGGESTION_IMPLEMENT',
            'TEMPLATE_CREATE', 'TEMPLATE_UPDATE', 'TEMPLATE_DELETE', 'TEMPLATE_USE', 'TEMPLATE_SHARE',
            'AI_CONFIG_UPDATE', 'MODEL_CONFIG_CHANGE', 'PERMISSION_GRANT', 'PERMISSION_REVOKE',
            'SERVICE_START', 'SERVICE_STOP', 'HEALTH_CHECK', 'ERROR_OCCURRED',
            'DATA_EXPORT', 'DATA_IMPORT', 'DATA_BACKUP', 'DATA_RESTORE',
            'UNAUTHORIZED_ACCESS', 'RATE_LIMIT_EXCEEDED', 'SUSPICIOUS_ACTIVITY',
            name='aioperationtype'
        ), nullable=False, comment='操作类型'),
        sa.Column('operation_name', sa.String(100), nullable=False, comment='操作名称'),
        sa.Column('operation_description', sa.Text(), nullable=True, comment='操作描述'),
        
        # 操作结果
        sa.Column('result', sa.Enum(
            'SUCCESS', 'FAILURE', 'PARTIAL_SUCCESS', 'CANCELLED', 'TIMEOUT',
            name='aioperationresult'
        ), nullable=False, comment='操作结果'),
        sa.Column('result_message', sa.Text(), nullable=True, comment='结果消息'),
        sa.Column('error_code', sa.String(50), nullable=True, comment='错误代码'),
        sa.Column('error_details', sa.Text(), nullable=True, comment='错误详情'),
        
        # 资源信息
        sa.Column('resource_type', sa.String(50), nullable=True, comment='资源类型'),
        sa.Column('resource_id', sa.String(100), nullable=True, comment='资源ID'),
        sa.Column('resource_name', sa.String(200), nullable=True, comment='资源名称'),
        
        # AI相关信息
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='AI服务提供商'),
        sa.Column('ai_model', sa.String(100), nullable=True, comment='AI模型'),
        sa.Column('tokens_used', sa.Integer(), nullable=True, comment='使用的Token数'),
        sa.Column('cost_amount', sa.Float(), nullable=True, comment='成本金额'),
        
        # 性能指标
        sa.Column('processing_time', sa.Float(), nullable=True, comment='处理时间(秒)'),
        sa.Column('response_size', sa.Integer(), nullable=True, comment='响应大小(字节)'),
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='置信度分数'),
        
        # 请求信息
        sa.Column('request_ip', sa.String(45), nullable=True, comment='请求IP地址'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='用户代理'),
        sa.Column('request_headers', sa.JSON(), nullable=True, comment='请求头信息'),
        sa.Column('request_params', sa.JSON(), nullable=True, comment='请求参数'),
        
        # 响应信息
        sa.Column('response_data', sa.JSON(), nullable=True, comment='响应数据'),
        sa.Column('response_headers', sa.JSON(), nullable=True, comment='响应头信息'),
        
        # 业务数据
        sa.Column('business_context', sa.JSON(), nullable=True, comment='业务上下文'),
        sa.Column('metadata', sa.JSON(), nullable=True, comment='元数据'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签'),
        
        # 优先级和分类
        sa.Column('priority', sa.Enum(
            'LOW', 'MEDIUM', 'HIGH', 'CRITICAL',
            name='aioperationpriority'
        ), nullable=True, comment='优先级'),
        sa.Column('category', sa.String(50), nullable=True, comment='分类'),
        sa.Column('subcategory', sa.String(50), nullable=True, comment='子分类'),
        
        # 审计信息
        sa.Column('is_sensitive', sa.Boolean(), nullable=True, comment='是否敏感操作'),
        sa.Column('requires_approval', sa.Boolean(), nullable=True, comment='是否需要审批'),
        sa.Column('approved_by', sa.Integer(), nullable=True, comment='审批人ID'),
        sa.Column('approved_at', sa.String(50), nullable=True, comment='审批时间'),
        
        # 关联信息
        sa.Column('parent_log_id', sa.Integer(), nullable=True, comment='父日志ID'),
        sa.Column('correlation_id', sa.String(100), nullable=True, comment='关联ID'),
        sa.Column('trace_id', sa.String(100), nullable=True, comment='追踪ID'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_log_id'], ['ai_operation_logs.id'], ondelete='SET NULL'),
        
        comment='AI助手操作日志表'
    )
    
    # 创建AI操作日志汇总表
    op.create_table('ai_operation_log_summaries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        # 汇总维度
        sa.Column('summary_date', sa.String(10), nullable=False, comment='汇总日期(YYYY-MM-DD)'),
        sa.Column('user_id', sa.Integer(), nullable=True, comment='用户ID'),
        sa.Column('operation_type', sa.Enum(
            'CONVERSATION_CREATE', 'CONVERSATION_DELETE', 'MESSAGE_SEND', 'MESSAGE_RECEIVE',
            'AI_MODEL_CALL', 'AI_STREAMING_START', 'AI_STREAMING_COMPLETE',
            'SUGGESTION_GENERATE', 'SUGGESTION_ACCEPT', 'SUGGESTION_REJECT', 'SUGGESTION_IMPLEMENT',
            'TEMPLATE_CREATE', 'TEMPLATE_UPDATE', 'TEMPLATE_DELETE', 'TEMPLATE_USE', 'TEMPLATE_SHARE',
            'AI_CONFIG_UPDATE', 'MODEL_CONFIG_CHANGE', 'PERMISSION_GRANT', 'PERMISSION_REVOKE',
            'SERVICE_START', 'SERVICE_STOP', 'HEALTH_CHECK', 'ERROR_OCCURRED',
            'DATA_EXPORT', 'DATA_IMPORT', 'DATA_BACKUP', 'DATA_RESTORE',
            'UNAUTHORIZED_ACCESS', 'RATE_LIMIT_EXCEEDED', 'SUSPICIOUS_ACTIVITY',
            name='aioperationtype_summary'
        ), nullable=True, comment='操作类型'),
        sa.Column('ai_provider', sa.String(50), nullable=True, comment='AI服务提供商'),
        
        # 统计数据
        sa.Column('total_operations', sa.Integer(), nullable=True, comment='总操作数'),
        sa.Column('successful_operations', sa.Integer(), nullable=True, comment='成功操作数'),
        sa.Column('failed_operations', sa.Integer(), nullable=True, comment='失败操作数'),
        
        # 性能统计
        sa.Column('total_processing_time', sa.Float(), nullable=True, comment='总处理时间'),
        sa.Column('avg_processing_time', sa.Float(), nullable=True, comment='平均处理时间'),
        sa.Column('max_processing_time', sa.Float(), nullable=True, comment='最大处理时间'),
        sa.Column('min_processing_time', sa.Float(), nullable=True, comment='最小处理时间'),
        
        # 资源统计
        sa.Column('total_tokens_used', sa.Integer(), nullable=True, comment='总Token使用量'),
        sa.Column('total_cost', sa.Float(), nullable=True, comment='总成本'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        comment='AI操作日志汇总表'
    )
    
    # 创建索引以提高查询性能
    
    # AI操作日志表索引
    op.create_index('idx_ai_operation_logs_user_id', 'ai_operation_logs', ['user_id'])
    op.create_index('idx_ai_operation_logs_operation_type', 'ai_operation_logs', ['operation_type'])
    op.create_index('idx_ai_operation_logs_result', 'ai_operation_logs', ['result'])
    op.create_index('idx_ai_operation_logs_created_at', 'ai_operation_logs', ['created_at'])
    op.create_index('idx_ai_operation_logs_session_id', 'ai_operation_logs', ['session_id'])
    op.create_index('idx_ai_operation_logs_ai_provider', 'ai_operation_logs', ['ai_provider'])
    op.create_index('idx_ai_operation_logs_category', 'ai_operation_logs', ['category'])
    op.create_index('idx_ai_operation_logs_priority', 'ai_operation_logs', ['priority'])
    op.create_index('idx_ai_operation_logs_is_sensitive', 'ai_operation_logs', ['is_sensitive'])
    op.create_index('idx_ai_operation_logs_trace_id', 'ai_operation_logs', ['trace_id'])
    
    # 复合索引
    op.create_index('idx_ai_operation_logs_user_type_date', 'ai_operation_logs', 
                   ['user_id', 'operation_type', 'created_at'])
    op.create_index('idx_ai_operation_logs_provider_model_date', 'ai_operation_logs', 
                   ['ai_provider', 'ai_model', 'created_at'])
    
    # AI操作日志汇总表索引
    op.create_index('idx_ai_operation_log_summaries_date', 'ai_operation_log_summaries', ['summary_date'])
    op.create_index('idx_ai_operation_log_summaries_user_id', 'ai_operation_log_summaries', ['user_id'])
    op.create_index('idx_ai_operation_log_summaries_operation_type', 'ai_operation_log_summaries', ['operation_type'])
    op.create_index('idx_ai_operation_log_summaries_ai_provider', 'ai_operation_log_summaries', ['ai_provider'])
    
    # 复合索引
    op.create_index('idx_ai_operation_log_summaries_date_user', 'ai_operation_log_summaries', 
                   ['summary_date', 'user_id'])
    op.create_index('idx_ai_operation_log_summaries_date_type', 'ai_operation_log_summaries', 
                   ['summary_date', 'operation_type'])


def downgrade():
    """降级数据库结构"""
    
    # 删除索引
    op.drop_index('idx_ai_operation_log_summaries_date_type', table_name='ai_operation_log_summaries')
    op.drop_index('idx_ai_operation_log_summaries_date_user', table_name='ai_operation_log_summaries')
    op.drop_index('idx_ai_operation_log_summaries_ai_provider', table_name='ai_operation_log_summaries')
    op.drop_index('idx_ai_operation_log_summaries_operation_type', table_name='ai_operation_log_summaries')
    op.drop_index('idx_ai_operation_log_summaries_user_id', table_name='ai_operation_log_summaries')
    op.drop_index('idx_ai_operation_log_summaries_date', table_name='ai_operation_log_summaries')
    
    op.drop_index('idx_ai_operation_logs_provider_model_date', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_user_type_date', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_trace_id', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_is_sensitive', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_priority', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_category', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_ai_provider', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_session_id', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_created_at', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_result', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_operation_type', table_name='ai_operation_logs')
    op.drop_index('idx_ai_operation_logs_user_id', table_name='ai_operation_logs')
    
    # 删除表
    op.drop_table('ai_operation_log_summaries')
    op.drop_table('ai_operation_logs')