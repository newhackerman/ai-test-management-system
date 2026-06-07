"""
创建AI文件存储相关表

Revision ID: 006_create_ai_file_storage_tables
Revises: 005_create_ai_assistant_tables
Create Date: 2024-01-20 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '006_create_ai_file_storage_tables'
down_revision = '005_create_ai_assistant_tables'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库"""
    
    # 创建文件类型枚举
    file_type_enum = sa.Enum(
        'IMAGE', 'DOCUMENT', 'AUDIO', 'VIDEO', 'ARCHIVE', 'CODE', 'DATA', 'OTHER',
        name='filetype'
    )
    
    # 创建文件分类枚举
    file_category_enum = sa.Enum(
        'CHAT_ATTACHMENT', 'PROMPT_TEMPLATE', 'EXPORT_DATA', 
        'USER_UPLOAD', 'AI_GENERATED', 'SYSTEM_BACKUP', 'TEMP_FILE',
        name='filecategory'
    )
    
    # 创建存储提供商枚举
    storage_provider_enum = sa.Enum(
        'LOCAL', 'ALIYUN_OSS', 'TENCENT_COS', 'AWS_S3', 'MINIO',
        name='storageprovider'
    )
    
    # 创建文件状态枚举
    file_status_enum = sa.Enum(
        'UPLOADING', 'ACTIVE', 'ARCHIVED', 'DELETED', 'CORRUPTED',
        name='filestatus'
    )
    
    # 创建AI文件存储表
    op.create_table(
        'ai_file_storage',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='文件ID'),
        
        # 基本信息
        sa.Column('original_filename', sa.String(255), nullable=False, comment='原始文件名'),
        sa.Column('stored_filename', sa.String(255), nullable=False, comment='存储文件名'),
        sa.Column('file_path', sa.String(500), nullable=False, comment='文件路径'),
        sa.Column('file_url', sa.String(500), nullable=True, comment='文件访问URL'),
        
        # 文件属性
        sa.Column('file_type', file_type_enum, nullable=False, comment='文件类型'),
        sa.Column('file_category', file_category_enum, nullable=False, comment='文件分类'),
        sa.Column('mime_type', sa.String(100), nullable=False, comment='MIME类型'),
        sa.Column('file_size', sa.BigInteger(), nullable=False, comment='文件大小(字节)'),
        sa.Column('file_hash', sa.String(64), nullable=True, comment='文件哈希值(SHA256)'),
        
        # 存储信息
        sa.Column('storage_provider', storage_provider_enum, nullable=False, 
                 server_default='LOCAL', comment='存储提供商'),
        sa.Column('storage_bucket', sa.String(100), nullable=True, comment='存储桶名称'),
        sa.Column('storage_region', sa.String(50), nullable=True, comment='存储区域'),
        
        # 关联信息
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='上传用户ID'),
        sa.Column('session_id', sa.BigInteger(), nullable=True, comment='关联会话ID'),
        sa.Column('message_id', sa.BigInteger(), nullable=True, comment='关联消息ID'),
        sa.Column('template_id', sa.BigInteger(), nullable=True, comment='关联模板ID'),
        
        # 元数据
        sa.Column('metadata', sa.Text(), nullable=True, comment='文件元数据(JSON)'),
        sa.Column('tags', sa.String(500), nullable=True, comment='文件标签'),
        sa.Column('description', sa.Text(), nullable=True, comment='文件描述'),
        
        # 状态和权限
        sa.Column('status', file_status_enum, nullable=False, 
                 server_default='ACTIVE', comment='文件状态'),
        sa.Column('is_public', sa.Boolean(), nullable=False, 
                 server_default='0', comment='是否公开'),
        sa.Column('is_temporary', sa.Boolean(), nullable=False, 
                 server_default='0', comment='是否临时文件'),
        
        # 访问控制
        sa.Column('access_count', sa.Integer(), nullable=False, 
                 server_default='0', comment='访问次数'),
        sa.Column('download_count', sa.Integer(), nullable=False, 
                 server_default='0', comment='下载次数'),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True, comment='最后访问时间'),
        
        # 生命周期
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('archived_at', sa.DateTime(), nullable=True, comment='归档时间'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True, comment='删除时间'),
        
        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), 
                 comment='更新时间'),
        
        # 主键和约束
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stored_filename'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['ai_chat_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['message_id'], ['ai_chat_messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], ['ai_prompt_templates.id'], ondelete='SET NULL'),
        
        comment='AI文件存储表'
    )
    
    # 创建AI文件分享表
    op.create_table(
        'ai_file_shares',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='分享ID'),
        
        # 关联信息
        sa.Column('file_id', sa.BigInteger(), nullable=False, comment='文件ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment='分享用户ID'),
        
        # 分享信息
        sa.Column('share_token', sa.String(64), nullable=False, comment='分享令牌'),
        sa.Column('share_url', sa.String(500), nullable=False, comment='分享链接'),
        sa.Column('share_password', sa.String(100), nullable=True, comment='分享密码'),
        
        # 权限控制
        sa.Column('can_download', sa.Boolean(), nullable=False, 
                 server_default='1', comment='允许下载'),
        sa.Column('can_preview', sa.Boolean(), nullable=False, 
                 server_default='1', comment='允许预览'),
        sa.Column('max_downloads', sa.Integer(), nullable=True, comment='最大下载次数'),
        sa.Column('max_views', sa.Integer(), nullable=True, comment='最大查看次数'),
        
        # 统计信息
        sa.Column('download_count', sa.Integer(), nullable=False, 
                 server_default='0', comment='下载次数'),
        sa.Column('view_count', sa.Integer(), nullable=False, 
                 server_default='0', comment='查看次数'),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True, comment='最后访问时间'),
        
        # 生命周期
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('is_active', sa.Boolean(), nullable=False, 
                 server_default='1', comment='是否激活'),
        
        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), 
                 comment='更新时间'),
        
        # 主键和约束
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('share_token'),
        sa.ForeignKeyConstraint(['file_id'], ['ai_file_storage.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        comment='AI文件分享表'
    )
    
    # 创建AI文件访问日志表
    op.create_table(
        'ai_file_access_logs',
        sa.Column('id', sa.BigInteger(), nullable=False, comment='日志ID'),
        
        # 关联信息
        sa.Column('file_id', sa.BigInteger(), nullable=False, comment='文件ID'),
        sa.Column('user_id', sa.BigInteger(), nullable=True, comment='访问用户ID'),
        sa.Column('share_id', sa.BigInteger(), nullable=True, comment='分享ID'),
        
        # 访问信息
        sa.Column('action', sa.String(50), nullable=False, 
                 comment='操作类型(view/download/upload/delete)'),
        sa.Column('ip_address', sa.String(45), nullable=True, comment='IP地址'),
        sa.Column('user_agent', sa.String(500), nullable=True, comment='用户代理'),
        sa.Column('referer', sa.String(500), nullable=True, comment='来源页面'),
        
        # 结果信息
        sa.Column('success', sa.Boolean(), nullable=False, 
                 server_default='1', comment='是否成功'),
        sa.Column('error_message', sa.String(500), nullable=True, comment='错误信息'),
        sa.Column('response_time', sa.Integer(), nullable=True, comment='响应时间(毫秒)'),
        sa.Column('bytes_transferred', sa.BigInteger(), nullable=True, comment='传输字节数'),
        
        # 时间戳
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                 server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        
        # 主键和约束
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['file_id'], ['ai_file_storage.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['share_id'], ['ai_file_shares.id'], ondelete='SET NULL'),
        
        comment='AI文件访问日志表'
    )
    
    # 创建索引
    
    # ai_file_storage 表索引
    op.create_index('idx_ai_file_user_id', 'ai_file_storage', ['user_id'])
    op.create_index('idx_ai_file_session_id', 'ai_file_storage', ['session_id'])
    op.create_index('idx_ai_file_message_id', 'ai_file_storage', ['message_id'])
    op.create_index('idx_ai_file_template_id', 'ai_file_storage', ['template_id'])
    op.create_index('idx_ai_file_category', 'ai_file_storage', ['file_category'])
    op.create_index('idx_ai_file_type', 'ai_file_storage', ['file_type'])
    op.create_index('idx_ai_file_status', 'ai_file_storage', ['status'])
    op.create_index('idx_ai_file_hash', 'ai_file_storage', ['file_hash'])
    op.create_index('idx_ai_file_created_at', 'ai_file_storage', ['created_at'])
    op.create_index('idx_ai_file_expires_at', 'ai_file_storage', ['expires_at'])
    
    # ai_file_shares 表索引
    op.create_index('idx_ai_file_share_file_id', 'ai_file_shares', ['file_id'])
    op.create_index('idx_ai_file_share_user_id', 'ai_file_shares', ['user_id'])
    op.create_index('idx_ai_file_share_token', 'ai_file_shares', ['share_token'])
    op.create_index('idx_ai_file_share_expires_at', 'ai_file_shares', ['expires_at'])
    
    # ai_file_access_logs 表索引
    op.create_index('idx_ai_file_access_file_id', 'ai_file_access_logs', ['file_id'])
    op.create_index('idx_ai_file_access_user_id', 'ai_file_access_logs', ['user_id'])
    op.create_index('idx_ai_file_access_action', 'ai_file_access_logs', ['action'])
    op.create_index('idx_ai_file_access_created_at', 'ai_file_access_logs', ['created_at'])
    op.create_index('idx_ai_file_access_ip', 'ai_file_access_logs', ['ip_address'])


def downgrade():
    """降级数据库"""
    
    # 删除索引
    op.drop_index('idx_ai_file_access_ip', 'ai_file_access_logs')
    op.drop_index('idx_ai_file_access_created_at', 'ai_file_access_logs')
    op.drop_index('idx_ai_file_access_action', 'ai_file_access_logs')
    op.drop_index('idx_ai_file_access_user_id', 'ai_file_access_logs')
    op.drop_index('idx_ai_file_access_file_id', 'ai_file_access_logs')
    
    op.drop_index('idx_ai_file_share_expires_at', 'ai_file_shares')
    op.drop_index('idx_ai_file_share_token', 'ai_file_shares')
    op.drop_index('idx_ai_file_share_user_id', 'ai_file_shares')
    op.drop_index('idx_ai_file_share_file_id', 'ai_file_shares')
    
    op.drop_index('idx_ai_file_expires_at', 'ai_file_storage')
    op.drop_index('idx_ai_file_created_at', 'ai_file_storage')
    op.drop_index('idx_ai_file_hash', 'ai_file_storage')
    op.drop_index('idx_ai_file_status', 'ai_file_storage')
    op.drop_index('idx_ai_file_type', 'ai_file_storage')
    op.drop_index('idx_ai_file_category', 'ai_file_storage')
    op.drop_index('idx_ai_file_template_id', 'ai_file_storage')
    op.drop_index('idx_ai_file_message_id', 'ai_file_storage')
    op.drop_index('idx_ai_file_session_id', 'ai_file_storage')
    op.drop_index('idx_ai_file_user_id', 'ai_file_storage')
    
    # 删除表
    op.drop_table('ai_file_access_logs')
    op.drop_table('ai_file_shares')
    op.drop_table('ai_file_storage')
    
    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS filestatus')
    op.execute('DROP TYPE IF EXISTS storageprovider')
    op.execute('DROP TYPE IF EXISTS filecategory')
    op.execute('DROP TYPE IF EXISTS filetype')