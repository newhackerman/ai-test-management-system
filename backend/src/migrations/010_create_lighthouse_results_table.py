"""
创建Lighthouse性能测试结果表

Revision ID: 010_lighthouse_results
Revises: 009_previous_migration
Create Date: 2024-01-15 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '010_lighthouse_results'
down_revision = '009_previous_migration'
branch_labels = None
depends_on = None


def upgrade():
    """创建Lighthouse相关表"""
    
    # 创建lighthouse_results表
    op.create_table(
        'lighthouse_results',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='结果ID'),
        sa.Column('audit_id', sa.String(50), nullable=False, comment='审计唯一标识'),
        sa.Column('url', sa.String(500), nullable=False, comment='测试URL'),
        sa.Column('device_type', sa.String(20), nullable=False, default='desktop', comment='设备类型'),
        sa.Column('lighthouse_version', sa.String(20), nullable=True, comment='Lighthouse版本'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='用户代理'),
        
        # 性能指标
        sa.Column('first_contentful_paint', sa.Float(), default=0.0, comment='首次内容绘制时间(ms)'),
        sa.Column('largest_contentful_paint', sa.Float(), default=0.0, comment='最大内容绘制时间(ms)'),
        sa.Column('cumulative_layout_shift', sa.Float(), default=0.0, comment='累积布局偏移'),
        sa.Column('first_input_delay', sa.Float(), default=0.0, comment='首次输入延迟(ms)'),
        sa.Column('speed_index', sa.Float(), default=0.0, comment='速度指数'),
        sa.Column('total_blocking_time', sa.Float(), default=0.0, comment='总阻塞时间(ms)'),
        sa.Column('time_to_interactive', sa.Float(), default=0.0, comment='可交互时间(ms)'),
        
        # 评分 (0-100)
        sa.Column('performance_score', sa.Integer(), default=0, comment='性能评分'),
        sa.Column('accessibility_score', sa.Integer(), default=0, comment='可访问性评分'),
        sa.Column('best_practices_score', sa.Integer(), default=0, comment='最佳实践评分'),
        sa.Column('seo_score', sa.Integer(), default=0, comment='SEO评分'),
        sa.Column('pwa_score', sa.Integer(), default=0, comment='PWA评分'),
        
        # 优化建议和原始数据
        sa.Column('opportunities', sa.JSON(), nullable=True, comment='优化建议JSON'),
        sa.Column('raw_data', sa.JSON(), nullable=True, comment='原始Lighthouse数据'),
        
        # 时间信息
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.current_timestamp(), comment='创建时间'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('audit_id'),
        comment='Lighthouse性能测试结果表'
    )
    
    # 创建索引
    op.create_index('idx_lighthouse_results_url', 'lighthouse_results', ['url'])
    op.create_index('idx_lighthouse_results_device_type', 'lighthouse_results', ['device_type'])
    op.create_index('idx_lighthouse_results_created_at', 'lighthouse_results', ['created_at'])
    op.create_index('idx_lighthouse_results_performance_score', 'lighthouse_results', ['performance_score'])
    op.create_index('idx_lighthouse_results_url_created', 'lighthouse_results', ['url', 'created_at'])
    
    # 创建system_metrics表
    op.create_table(
        'system_metrics',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='指标ID'),
        sa.Column('metric_name', sa.String(100), nullable=False, comment='指标名称'),
        sa.Column('metric_type', sa.String(20), nullable=False, comment='指标类型'),
        sa.Column('metric_category', sa.String(50), nullable=False, comment='指标分类'),
        
        # 指标数据
        sa.Column('metric_value', sa.Float(), nullable=False, comment='指标值'),
        sa.Column('metric_unit', sa.String(20), nullable=True, comment='指标单位'),
        sa.Column('metric_labels', sa.JSON(), nullable=True, comment='指标标签'),
        
        # 来源信息
        sa.Column('source_host', sa.String(100), nullable=False, comment='来源主机'),
        sa.Column('source_service', sa.String(100), nullable=True, comment='来源服务'),
        sa.Column('source_instance', sa.String(100), nullable=True, comment='来源实例'),
        
        # 时间信息
        sa.Column('timestamp', sa.DateTime(), nullable=False, comment='时间戳'),
        sa.Column('collection_time', sa.DateTime(), nullable=False, default=sa.func.current_timestamp(), comment='采集时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.current_timestamp(), comment='创建时间'),
        
        sa.PrimaryKeyConstraint('id'),
        comment='系统监控指标表'
    )
    
    # 创建system_metrics索引
    op.create_index('idx_system_metrics_name', 'system_metrics', ['metric_name'])
    op.create_index('idx_system_metrics_type', 'system_metrics', ['metric_type'])
    op.create_index('idx_system_metrics_category', 'system_metrics', ['metric_category'])
    op.create_index('idx_system_metrics_timestamp', 'system_metrics', ['timestamp'])
    op.create_index('idx_system_metrics_source_host', 'system_metrics', ['source_host'])
    op.create_index('idx_system_metrics_composite', 'system_metrics', ['metric_name', 'source_host', 'timestamp'])


def downgrade():
    """删除Lighthouse相关表"""
    
    # 删除索引
    op.drop_index('idx_system_metrics_composite', 'system_metrics')
    op.drop_index('idx_system_metrics_source_host', 'system_metrics')
    op.drop_index('idx_system_metrics_timestamp', 'system_metrics')
    op.drop_index('idx_system_metrics_category', 'system_metrics')
    op.drop_index('idx_system_metrics_type', 'system_metrics')
    op.drop_index('idx_system_metrics_name', 'system_metrics')
    
    op.drop_index('idx_lighthouse_results_url_created', 'lighthouse_results')
    op.drop_index('idx_lighthouse_results_performance_score', 'lighthouse_results')
    op.drop_index('idx_lighthouse_results_created_at', 'lighthouse_results')
    op.drop_index('idx_lighthouse_results_device_type', 'lighthouse_results')
    op.drop_index('idx_lighthouse_results_url', 'lighthouse_results')
    
    # 删除表
    op.drop_table('system_metrics')
    op.drop_table('lighthouse_results')