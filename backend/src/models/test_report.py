"""
测试报告数据模型

本模块定义了测试报告相关的数据库模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, JSON, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base

class TestReportTemplate(Base):
    """测试报告模板模型"""
    __tablename__ = "test_report_templates"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="模板名称")
    description = Column(Text, comment="模板描述")
    template_type = Column(String(50), nullable=False, comment="模板类型")
    template_content = Column(JSON, comment="模板内容")
    default_config = Column(JSON, comment="默认配置")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    creator = relationship("User")
    
    def __repr__(self):
        return f"<TestReportTemplate(id={self.id}, name='{self.name}', type='{self.template_type}')>"

class TestReportRecord(Base):
    """测试报告记录模型"""
    __tablename__ = "test_report_records"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="报告名称")
    description = Column(Text, comment="报告描述")
    report_type = Column(String(50), nullable=False, comment="报告类型")
    project_id = Column(BigInteger, ForeignKey("projects.id"), comment="项目ID")
    template_id = Column(BigInteger, ForeignKey("test_report_templates.id"), comment="模板ID")
    
    # 报告配置
    report_config = Column(JSON, comment="报告配置")
    include_sections = Column(JSON, comment="包含的章节")
    date_range = Column(JSON, comment="数据时间范围")
    export_formats = Column(JSON, comment="导出格式")
    
    # 报告文件
    file_paths = Column(JSON, comment="文件路径")
    file_size = Column(Integer, comment="文件大小(字节)")
    
    # 生成信息
    status = Column(String(20), default="pending", comment="生成状态")
    generation_time = Column(Float, comment="生成耗时(秒)")
    error_message = Column(Text, comment="错误信息")
    
    # 统计信息
    view_count = Column(Integer, default=0, comment="查看次数")
    download_count = Column(Integer, default=0, comment="下载次数")
    
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    project = relationship("Project")
    template = relationship("TestReportTemplate")
    creator = relationship("User")
    
    def __repr__(self):
        return f"<TestReportRecord(id={self.id}, name='{self.name}', status='{self.status}')>"

class TestReportSchedule(Base):
    """测试报告调度模型"""
    __tablename__ = "test_report_schedules"
    
    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="调度任务名称")
    description = Column(Text, comment="任务描述")
    
    # 报告配置
    report_config = Column(JSON, nullable=False, comment="报告配置")
    template_id = Column(BigInteger, ForeignKey("test_report_templates.id"), comment="模板ID")
    
    # 调度配置
    schedule_type = Column(String(20), nullable=False, comment="调度类型")  # daily, weekly, monthly, cron
    schedule_expression = Column(String(100), nullable=False, comment="调度表达式")
    timezone = Column(String(50), default="UTC", comment="时区")
    
    # 通知配置
    recipients = Column(JSON, comment="接收人列表")
    notification_config = Column(JSON, comment="通知配置")
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment="是否激活")
    last_run_time = Column(DateTime, comment="上次运行时间")
    next_run_time = Column(DateTime, comment="下次运行时间")
    run_count = Column(Integer, default=0, comment="运行次数")
    
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    template = relationship("TestReportTemplate")
    creator = relationship("User")
    
    def __repr__(self):
        return f"<TestReportSchedule(id={self.id}, name='{self.name}', active={self.is_active})>"

class TestReportShare(Base):
    """测试报告分享模型"""
    __tablename__ = "test_report_shares"
    
    id = Column(BigInteger, primary_key=True, index=True)
    report_id = Column(BigInteger, ForeignKey("test_report_records.id"), nullable=False, comment="报告ID")
    share_token = Column(String(64), unique=True, nullable=False, comment="分享令牌")
    share_type = Column(String(20), default="link", comment="分享类型")  # link, email, download
    
    # 访问控制
    password_protected = Column(Boolean, default=False, comment="是否密码保护")
    access_password = Column(String(100), comment="访问密码")
    max_access_count = Column(Integer, comment="最大访问次数")
    access_count = Column(Integer, default=0, comment="已访问次数")
    
    # 有效期
    expires_at = Column(DateTime, comment="过期时间")
    
    # 权限控制
    allowed_users = Column(JSON, comment="允许访问的用户ID列表")
    allowed_roles = Column(JSON, comment="允许访问的角色列表")
    
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    report = relationship("TestReportRecord")
    creator = relationship("User")
    
    def __repr__(self):
        return f"<TestReportShare(id={self.id}, token='{self.share_token[:8]}...', expires={self.expires_at})>"

class TestReportComment(Base):
    """测试报告评论模型"""
    __tablename__ = "test_report_comments"
    
    id = Column(BigInteger, primary_key=True, index=True)
    report_id = Column(BigInteger, ForeignKey("test_report_records.id"), nullable=False, comment="报告ID")
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, comment="用户ID")
    content = Column(Text, nullable=False, comment="评论内容")
    parent_id = Column(BigInteger, ForeignKey("test_report_comments.id"), comment="父评论ID")
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    report = relationship("TestReportRecord")
    user = relationship("User")
    parent = relationship("TestReportComment", remote_side=[id])
    replies = relationship("TestReportComment", back_populates="parent")
    
    def __repr__(self):
        return f"<TestReportComment(id={self.id}, report_id={self.report_id}, user_id={self.user_id})>"