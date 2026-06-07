"""
基础设施模块数据模型

包含监控、日志、安全、备份等基础设施相关的数据模型
"""
from sqlalchemy import Column, BigInteger, String, DateTime, Text, JSON, Integer, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class LighthouseResult(Base):
    """Lighthouse性能测试结果表"""
    __tablename__ = 'lighthouse_results'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='结果ID')
    audit_id = Column(String(50), unique=True, nullable=False, comment='审计唯一标识')
    url = Column(String(500), nullable=False, comment='测试URL')
    device_type = Column(String(20), nullable=False, default='desktop', comment='设备类型')
    lighthouse_version = Column(String(20), comment='Lighthouse版本')
    user_agent = Column(Text, comment='用户代理')
    
    # 性能指标
    first_contentful_paint = Column(Float, default=0.0, comment='首次内容绘制时间(ms)')
    largest_contentful_paint = Column(Float, default=0.0, comment='最大内容绘制时间(ms)')
    cumulative_layout_shift = Column(Float, default=0.0, comment='累积布局偏移')
    first_input_delay = Column(Float, default=0.0, comment='首次输入延迟(ms)')
    speed_index = Column(Float, default=0.0, comment='速度指数')
    total_blocking_time = Column(Float, default=0.0, comment='总阻塞时间(ms)')
    time_to_interactive = Column(Float, default=0.0, comment='可交互时间(ms)')
    
    # 评分 (0-100)
    performance_score = Column(Integer, default=0, comment='性能评分')
    accessibility_score = Column(Integer, default=0, comment='可访问性评分')
    best_practices_score = Column(Integer, default=0, comment='最佳实践评分')
    seo_score = Column(Integer, default=0, comment='SEO评分')
    pwa_score = Column(Integer, default=0, comment='PWA评分')
    
    # 优化建议和原始数据
    opportunities = Column(JSON, comment='优化建议JSON')
    raw_data = Column(JSON, comment='原始Lighthouse数据')
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    
    def __repr__(self):
        return f"<LighthouseResult(audit_id='{self.audit_id}', url='{self.url}', performance_score={self.performance_score})>"


class SystemMetrics(Base):
    """系统监控指标表"""
    __tablename__ = 'system_metrics'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='指标ID')
    metric_name = Column(String(100), nullable=False, comment='指标名称')
    metric_type = Column(String(20), nullable=False, comment='指标类型')
    metric_category = Column(String(50), nullable=False, comment='指标分类')
    
    # 指标数据
    metric_value = Column(Float, nullable=False, comment='指标值')
    metric_unit = Column(String(20), comment='指标单位')
    metric_labels = Column(JSON, comment='指标标签')
    
    # 来源信息
    source_host = Column(String(100), nullable=False, comment='来源主机')
    source_service = Column(String(100), comment='来源服务')
    source_instance = Column(String(100), comment='来源实例')
    
    # 时间信息
    timestamp = Column(DateTime, nullable=False, comment='时间戳')
    collection_time = Column(DateTime, default=datetime.utcnow, comment='采集时间')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    
    def __repr__(self):
        return f"<SystemMetrics(metric_name='{self.metric_name}', value={self.metric_value}, timestamp='{self.timestamp}')>"


class SystemAlerts(Base):
    """系统告警表"""
    __tablename__ = 'system_alerts'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='告警ID')
    alert_code = Column(String(50), unique=True, nullable=False, comment='告警编码')
    alert_name = Column(String(200), nullable=False, comment='告警名称')
    alert_level = Column(String(20), nullable=False, comment='告警级别')
    alert_type = Column(String(20), nullable=False, comment='告警类型')
    
    # 告警内容
    alert_message = Column(Text, nullable=False, comment='告警消息')
    alert_description = Column(Text, comment='告警描述')
    alert_source = Column(String(100), nullable=False, comment='告警来源')
    
    # 告警规则
    rule_name = Column(String(100), comment='规则名称')
    rule_expression = Column(Text, comment='规则表达式')
    threshold_value = Column(Float, comment='阈值')
    current_value = Column(Float, comment='当前值')
    
    # 状态管理
    status = Column(String(20), default='ACTIVE', comment='告警状态')
    severity_score = Column(Integer, default=0, comment='严重程度评分')
    
    # 处理信息
    acknowledged_by = Column(BigInteger, comment='确认人ID')
    acknowledged_at = Column(DateTime, comment='确认时间')
    resolved_by = Column(BigInteger, comment='解决人ID')
    resolved_at = Column(DateTime, comment='解决时间')
    resolution_notes = Column(Text, comment='解决备注')
    
    # 通知信息
    notification_sent = Column(Boolean, default=False, comment='是否已发送通知')
    notification_channels = Column(JSON, comment='通知渠道')
    escalation_level = Column(Integer, default=0, comment='升级级别')
    
    # 时间信息
    first_occurred_at = Column(DateTime, nullable=False, comment='首次发生时间')
    last_occurred_at = Column(DateTime, nullable=False, comment='最后发生时间')
    occurrence_count = Column(Integer, default=1, comment='发生次数')
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<SystemAlerts(alert_code='{self.alert_code}', level='{self.alert_level}', status='{self.status}')>"


class RecoveryActions(Base):
    """自动恢复操作记录表"""
    __tablename__ = 'recovery_actions'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='恢复操作ID')
    recovery_id = Column(String(50), unique=True, default=lambda: f"recovery_{int(datetime.utcnow().timestamp())}", comment='恢复操作唯一标识')
    
    # 故障信息
    failure_type = Column(String(50), nullable=False, comment='故障类型')
    failure_description = Column(Text, comment='故障描述')
    failure_severity = Column(String(20), comment='故障严重程度')
    
    # 恢复策略
    recovery_strategy = Column(String(100), nullable=False, comment='恢复策略')
    trigger_condition = Column(Text, comment='触发条件')
    recovery_parameters = Column(JSON, comment='恢复参数')
    
    # 执行信息
    recovery_status = Column(String(20), nullable=False, comment='恢复状态')
    recovery_message = Column(Text, comment='恢复消息')
    actions_taken = Column(JSON, comment='执行的操作列表')
    
    # 结果信息
    success_rate = Column(Float, default=0.0, comment='成功率')
    execution_duration_ms = Column(Integer, default=0, comment='执行耗时(毫秒)')
    retry_count = Column(Integer, default=0, comment='重试次数')
    
    # 影响评估
    affected_services = Column(JSON, comment='受影响的服务')
    downtime_seconds = Column(Integer, default=0, comment='停机时间(秒)')
    impact_level = Column(String(20), comment='影响级别')
    
    # 验证信息
    verification_status = Column(String(20), comment='验证状态')
    verification_time = Column(DateTime, comment='验证时间')
    verification_result = Column(Text, comment='验证结果')
    
    # 时间信息
    execution_time = Column(DateTime, nullable=False, comment='执行时间')
    completion_time = Column(DateTime, comment='完成时间')
    
    # 关联信息
    alert_id = Column(BigInteger, comment='关联告警ID')
    triggered_by = Column(String(50), comment='触发方式')
    
    # 元数据
    additional_data = Column(JSON, comment='附加数据')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<RecoveryActions(recovery_id='{self.recovery_id}', failure_type='{self.failure_type}', status='{self.recovery_status}')>"


class AuditLogs(Base):
    """审计日志表"""
    __tablename__ = 'audit_logs'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='日志ID')
    log_id = Column(String(50), unique=True, nullable=False, comment='日志唯一标识')
    
    # 操作信息
    action_type = Column(String(20), nullable=False, comment='操作类型')
    action_name = Column(String(100), nullable=False, comment='操作名称')
    action_description = Column(Text, comment='操作描述')
    
    # 用户信息
    user_id = Column(BigInteger, comment='操作用户ID')
    username = Column(String(100), comment='用户名')
    user_role = Column(String(50), comment='用户角色')
    
    # 资源信息
    resource_type = Column(String(50), comment='资源类型')
    resource_id = Column(String(100), comment='资源ID')
    resource_name = Column(String(200), comment='资源名称')
    
    # 请求信息
    request_method = Column(String(10), comment='HTTP方法')
    request_url = Column(String(500), comment='请求URL')
    request_params = Column(JSON, comment='请求参数')
    request_body = Column(Text, comment='请求体')
    
    # 响应信息
    response_status = Column(Integer, comment='响应状态码')
    response_message = Column(Text, comment='响应消息')
    
    # 环境信息
    client_ip = Column(String(45), nullable=False, comment='客户端IP')
    user_agent = Column(Text, comment='用户代理')
    session_id = Column(String(100), comment='会话ID')
    
    # 结果信息
    operation_result = Column(String(20), default='SUCCESS', comment='操作结果')
    error_code = Column(String(50), comment='错误代码')
    error_message = Column(Text, comment='错误消息')
    
    # 安全信息
    risk_level = Column(String(20), default='LOW', comment='风险级别')
    is_suspicious = Column(Boolean, default=False, comment='是否可疑操作')
    security_flags = Column(JSON, comment='安全标记')
    
    # 时间信息
    operation_time = Column(DateTime, nullable=False, comment='操作时间')
    duration_ms = Column(Integer, default=0, comment='操作耗时(毫秒)')
    
    # 元数据
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    
    def __repr__(self):
        return f"<AuditLogs(log_id='{self.log_id}', action='{self.action_type}', user='{self.username}')>"


class BackupRecords(Base):
    """备份记录表"""
    __tablename__ = 'backup_records'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='备份记录ID')
    backup_id = Column(String(50), unique=True, nullable=False, comment='备份唯一标识')
    backup_name = Column(String(200), nullable=False, comment='备份名称')
    backup_type = Column(String(20), nullable=False, comment='备份类型')
    backup_scope = Column(String(20), nullable=False, comment='备份范围')
    
    # 备份配置
    backup_policy = Column(String(100), comment='备份策略')
    retention_days = Column(Integer, default=30, comment='保留天数')
    compression_enabled = Column(Boolean, default=True, comment='是否压缩')
    encryption_enabled = Column(Boolean, default=True, comment='是否加密')
    
    # 备份文件信息
    backup_path = Column(String(500), nullable=False, comment='备份文件路径')
    backup_size_bytes = Column(BigInteger, default=0, comment='备份文件大小(字节)')
    compressed_size_bytes = Column(BigInteger, default=0, comment='压缩后大小(字节)')
    file_count = Column(Integer, default=0, comment='文件数量')
    
    # 备份状态
    status = Column(String(20), default='PENDING', comment='备份状态')
    progress_percentage = Column(Integer, default=0, comment='进度百分比')
    error_message = Column(Text, comment='错误信息')
    
    # 时间信息
    scheduled_time = Column(DateTime, comment='计划时间')
    started_at = Column(DateTime, comment='开始时间')
    completed_at = Column(DateTime, comment='完成时间')
    duration_seconds = Column(Integer, default=0, comment='耗时(秒)')
    
    # 验证信息
    is_verified = Column(Boolean, default=False, comment='是否已验证')
    verification_time = Column(DateTime, comment='验证时间')
    verification_result = Column(String(20), comment='验证结果')
    checksum = Column(String(64), comment='校验和')
    
    # 恢复信息
    last_restore_time = Column(DateTime, comment='最后恢复时间')
    
    # 元数据
    created_by = Column(BigInteger, comment='创建者ID')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def __repr__(self):
        return f"<BackupRecords(backup_id='{self.backup_id}', type='{self.backup_type}', status='{self.status}')>"