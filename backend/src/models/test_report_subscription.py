"""
测试报告订阅和分发数据模型

本模块定义了测试报告订阅和分发相关的数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum

from .base import Base

class SubscriptionType(str, Enum):
    """订阅类型枚举"""
    REPORT_GENERATED = "report_generated"  # 报告生成时通知
    SCHEDULED_REPORT = "scheduled_report"  # 定期报告
    PROJECT_SUMMARY = "project_summary"    # 项目摘要
    DEFECT_REPORT = "defect_report"       # 缺陷报告
    COVERAGE_REPORT = "coverage_report"   # 覆盖率报告
    CUSTOM_REPORT = "custom_report"       # 自定义报告

class DeliveryChannel(str, Enum):
    """分发渠道枚举"""
    EMAIL = "email"           # 邮件
    WEBHOOK = "webhook"       # Webhook
    IN_APP = "in_app"        # 应用内通知
    DOWNLOAD_LINK = "download_link"  # 下载链接

class SubscriptionStatus(str, Enum):
    """订阅状态枚举"""
    ACTIVE = "active"         # 激活
    PAUSED = "paused"        # 暂停
    CANCELLED = "cancelled"   # 取消

class DistributionStatus(str, Enum):
    """分发状态枚举"""
    PENDING = "pending"       # 待分发
    PROCESSING = "processing" # 处理中
    SENT = "sent"            # 已发送
    DELIVERED = "delivered"   # 已送达
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"   # 已取消

class TestReportSubscription(Base):
    """测试报告订阅模型"""
    __tablename__ = "test_report_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="订阅名称")
    description = Column(Text, comment="订阅描述")
    
    # 订阅配置
    subscription_type = Column(SQLEnum(SubscriptionType), nullable=False, comment="订阅类型")
    delivery_channels = Column(JSON, nullable=False, comment="分发渠道列表")
    
    # 过滤条件
    project_ids = Column(JSON, comment="项目ID列表，为空表示所有项目")
    report_types = Column(JSON, comment="报告类型列表，为空表示所有类型")
    template_ids = Column(JSON, comment="模板ID列表，为空表示所有模板")
    
    # 调度配置
    schedule_enabled = Column(Boolean, default=False, comment="是否启用定期发送")
    schedule_expression = Column(String(100), comment="调度表达式")
    timezone = Column(String(50), default="UTC", comment="时区")
    
    # 分发配置
    delivery_config = Column(JSON, comment="分发配置")
    email_recipients = Column(JSON, comment="邮件接收人列表")
    webhook_url = Column(String(500), comment="Webhook URL")
    
    # 个性化设置
    include_attachments = Column(Boolean, default=True, comment="是否包含附件")
    max_file_size = Column(Integer, comment="最大文件大小(MB)")
    preferred_formats = Column(JSON, comment="首选格式列表")
    
    # 状态管理
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, comment="订阅状态")
    last_delivery_time = Column(DateTime, comment="上次分发时间")
    next_delivery_time = Column(DateTime, comment="下次分发时间")
    delivery_count = Column(Integer, default=0, comment="分发次数")
    
    # 用户信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="订阅用户ID")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<TestReportSubscription(id={self.id}, name='{self.name}', type='{self.subscription_type}')>"

class TestReportDistribution(Base):
    """测试报告分发记录模型"""
    __tablename__ = "test_report_distributions"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("test_report_subscriptions.id"), nullable=False, comment="订阅ID")
    report_id = Column(Integer, ForeignKey("test_report_records.id"), comment="报告ID")
    
    # 分发信息
    delivery_channel = Column(SQLEnum(DeliveryChannel), nullable=False, comment="分发渠道")
    recipient = Column(String(200), nullable=False, comment="接收人")
    
    # 分发内容
    subject = Column(String(200), comment="主题")
    content = Column(Text, comment="内容")
    attachments = Column(JSON, comment="附件信息")
    
    # 分发状态
    status = Column(SQLEnum(DistributionStatus), default=DistributionStatus.PENDING, comment="分发状态")
    error_message = Column(Text, comment="错误信息")
    retry_count = Column(Integer, default=0, comment="重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")
    
    # 时间信息
    scheduled_at = Column(DateTime, comment="计划分发时间")
    sent_at = Column(DateTime, comment="发送时间")
    delivered_at = Column(DateTime, comment="送达时间")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    subscription = relationship("TestReportSubscription")
    report = relationship("TestReportRecord")
    
    def __repr__(self):
        return f"<TestReportDistribution(id={self.id}, channel='{self.delivery_channel}', status='{self.status}')>"

class TestReportVersion(Base):
    """测试报告版本管理模型"""
    __tablename__ = "test_report_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("test_report_records.id"), nullable=False, comment="报告ID")
    version_number = Column(String(20), nullable=False, comment="版本号")
    
    # 版本信息
    version_name = Column(String(100), comment="版本名称")
    description = Column(Text, comment="版本描述")
    change_log = Column(Text, comment="变更日志")
    
    # 文件信息
    file_paths = Column(JSON, comment="文件路径")
    file_size = Column(Integer, comment="文件大小(字节)")
    file_hash = Column(String(64), comment="文件哈希值")
    
    # 版本状态
    is_current = Column(Boolean, default=False, comment="是否为当前版本")
    is_published = Column(Boolean, default=False, comment="是否已发布")
    
    # 访问控制
    access_level = Column(String(20), default="private", comment="访问级别")  # private, internal, public
    allowed_users = Column(JSON, comment="允许访问的用户ID列表")
    allowed_roles = Column(JSON, comment="允许访问的角色列表")
    
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    report = relationship("TestReportRecord")
    creator = relationship("User")
    
    def __repr__(self):
        return f"<TestReportVersion(id={self.id}, report_id={self.report_id}, version='{self.version_number}')>"

class TestReportAccessLog(Base):
    """测试报告访问日志模型"""
    __tablename__ = "test_report_access_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("test_report_records.id"), nullable=False, comment="报告ID")
    version_id = Column(Integer, ForeignKey("test_report_versions.id"), comment="版本ID")
    user_id = Column(Integer, ForeignKey("users.id"), comment="用户ID")
    
    # 访问信息
    access_type = Column(String(20), nullable=False, comment="访问类型")  # view, download, share
    access_method = Column(String(20), comment="访问方式")  # direct, link, email
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(String(500), comment="用户代理")
    
    # 访问结果
    success = Column(Boolean, default=True, comment="是否成功")
    error_message = Column(String(200), comment="错误信息")
    
    accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="访问时间")
    
    # 关系
    report = relationship("TestReportRecord")
    version = relationship("TestReportVersion")
    user = relationship("User")
    
    def __repr__(self):
        return f"<TestReportAccessLog(id={self.id}, report_id={self.report_id}, type='{self.access_type}')>"