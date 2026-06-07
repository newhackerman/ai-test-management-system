"""
测试报告订阅和分发数据传输对象(DTO)

本模块定义了测试报告订阅和分发相关的数据传输对象
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, EmailStr
from enum import Enum

class SubscriptionType(str, Enum):
    """订阅类型枚举"""
    REPORT_GENERATED = "report_generated"
    SCHEDULED_REPORT = "scheduled_report"
    PROJECT_SUMMARY = "project_summary"
    DEFECT_REPORT = "defect_report"
    COVERAGE_REPORT = "coverage_report"
    CUSTOM_REPORT = "custom_report"

class DeliveryChannel(str, Enum):
    """分发渠道枚举"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    DOWNLOAD_LINK = "download_link"

class SubscriptionStatus(str, Enum):
    """订阅状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class DistributionStatus(str, Enum):
    """分发状态枚举"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"

class AccessLevel(str, Enum):
    """访问级别枚举"""
    PRIVATE = "private"
    INTERNAL = "internal"
    PUBLIC = "public"

# 订阅相关模型
class TestReportSubscriptionRequest(BaseModel):
    """测试报告订阅创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="订阅名称")
    description: Optional[str] = Field(None, description="订阅描述")
    subscription_type: SubscriptionType = Field(..., description="订阅类型")
    delivery_channels: List[DeliveryChannel] = Field(..., min_items=1, description="分发渠道列表")
    
    # 过滤条件
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表，为空表示所有项目")
    report_types: Optional[List[str]] = Field(None, description="报告类型列表，为空表示所有类型")
    template_ids: Optional[List[int]] = Field(None, description="模板ID列表，为空表示所有模板")
    
    # 调度配置
    schedule_enabled: bool = Field(False, description="是否启用定期发送")
    schedule_expression: Optional[str] = Field(None, description="调度表达式")
    timezone: str = Field("UTC", description="时区")
    
    # 分发配置
    delivery_config: Optional[Dict[str, Any]] = Field(None, description="分发配置")
    email_recipients: Optional[List[EmailStr]] = Field(None, description="邮件接收人列表")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    
    # 个性化设置
    include_attachments: bool = Field(True, description="是否包含附件")
    max_file_size: Optional[int] = Field(None, description="最大文件大小(MB)")
    preferred_formats: Optional[List[str]] = Field(None, description="首选格式列表")
    
    @validator('email_recipients')
    def validate_email_recipients(cls, v, values):
        if DeliveryChannel.EMAIL in values.get('delivery_channels', []) and not v:
            raise ValueError('邮件分发渠道需要指定接收人')
        return v
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v, values):
        if DeliveryChannel.WEBHOOK in values.get('delivery_channels', []) and not v:
            raise ValueError('Webhook分发渠道需要指定URL')
        return v
    
    @validator('schedule_expression')
    def validate_schedule_expression(cls, v, values):
        if values.get('schedule_enabled') and not v:
            raise ValueError('启用定期发送需要指定调度表达式')
        return v

class TestReportSubscriptionResponse(BaseModel):
    """测试报告订阅响应"""
    id: int
    name: str
    description: Optional[str] = None
    subscription_type: str
    delivery_channels: List[str]
    
    # 过滤条件
    project_ids: Optional[List[int]] = None
    report_types: Optional[List[str]] = None
    template_ids: Optional[List[int]] = None
    
    # 调度配置
    schedule_enabled: bool
    schedule_expression: Optional[str] = None
    timezone: str
    
    # 分发配置
    delivery_config: Optional[Dict[str, Any]] = None
    email_recipients: Optional[List[str]] = None
    webhook_url: Optional[str] = None
    
    # 个性化设置
    include_attachments: bool
    max_file_size: Optional[int] = None
    preferred_formats: Optional[List[str]] = None
    
    # 状态信息
    status: str
    last_delivery_time: Optional[datetime] = None
    next_delivery_time: Optional[datetime] = None
    delivery_count: int
    
    user_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TestReportSubscriptionUpdate(BaseModel):
    """测试报告订阅更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="订阅名称")
    description: Optional[str] = Field(None, description="订阅描述")
    delivery_channels: Optional[List[DeliveryChannel]] = Field(None, description="分发渠道列表")
    
    # 过滤条件
    project_ids: Optional[List[int]] = Field(None, description="项目ID列表")
    report_types: Optional[List[str]] = Field(None, description="报告类型列表")
    template_ids: Optional[List[int]] = Field(None, description="模板ID列表")
    
    # 调度配置
    schedule_enabled: Optional[bool] = Field(None, description="是否启用定期发送")
    schedule_expression: Optional[str] = Field(None, description="调度表达式")
    timezone: Optional[str] = Field(None, description="时区")
    
    # 分发配置
    delivery_config: Optional[Dict[str, Any]] = Field(None, description="分发配置")
    email_recipients: Optional[List[EmailStr]] = Field(None, description="邮件接收人列表")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    
    # 个性化设置
    include_attachments: Optional[bool] = Field(None, description="是否包含附件")
    max_file_size: Optional[int] = Field(None, description="最大文件大小(MB)")
    preferred_formats: Optional[List[str]] = Field(None, description="首选格式列表")
    
    # 状态管理
    status: Optional[SubscriptionStatus] = Field(None, description="订阅状态")

# 分发相关模型
class TestReportDistributionRequest(BaseModel):
    """测试报告分发请求"""
    subscription_id: Optional[int] = Field(None, description="订阅ID")
    report_id: int = Field(..., description="报告ID")
    delivery_channel: DeliveryChannel = Field(..., description="分发渠道")
    recipients: List[str] = Field(..., min_items=1, description="接收人列表")
    
    # 分发内容
    subject: Optional[str] = Field(None, description="主题")
    content: Optional[str] = Field(None, description="内容")
    include_attachments: bool = Field(True, description="是否包含附件")
    
    # 调度配置
    scheduled_at: Optional[datetime] = Field(None, description="计划分发时间")

class TestReportDistributionResponse(BaseModel):
    """测试报告分发响应"""
    id: int
    subscription_id: Optional[int] = None
    report_id: int
    delivery_channel: str
    recipient: str
    
    # 分发内容
    subject: Optional[str] = None
    content: Optional[str] = None
    attachments: Optional[Dict[str, Any]] = None
    
    # 分发状态
    status: str
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    
    # 时间信息
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 版本管理相关模型
class TestReportVersionRequest(BaseModel):
    """测试报告版本创建请求"""
    report_id: int = Field(..., description="报告ID")
    version_number: str = Field(..., description="版本号")
    version_name: Optional[str] = Field(None, description="版本名称")
    description: Optional[str] = Field(None, description="版本描述")
    change_log: Optional[str] = Field(None, description="变更日志")
    
    # 访问控制
    access_level: AccessLevel = Field(AccessLevel.PRIVATE, description="访问级别")
    allowed_users: Optional[List[int]] = Field(None, description="允许访问的用户ID列表")
    allowed_roles: Optional[List[str]] = Field(None, description="允许访问的角色列表")
    
    is_published: bool = Field(False, description="是否发布")

class TestReportVersionResponse(BaseModel):
    """测试报告版本响应"""
    id: int
    report_id: int
    version_number: str
    version_name: Optional[str] = None
    description: Optional[str] = None
    change_log: Optional[str] = None
    
    # 文件信息
    file_paths: Optional[Dict[str, str]] = None
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    
    # 版本状态
    is_current: bool
    is_published: bool
    
    # 访问控制
    access_level: str
    allowed_users: Optional[List[int]] = None
    allowed_roles: Optional[List[str]] = None
    
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 访问日志相关模型
class TestReportAccessLogResponse(BaseModel):
    """测试报告访问日志响应"""
    id: int
    report_id: int
    version_id: Optional[int] = None
    user_id: Optional[int] = None
    
    # 访问信息
    access_type: str
    access_method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # 访问结果
    success: bool
    error_message: Optional[str] = None
    
    accessed_at: datetime
    
    class Config:
        from_attributes = True

# 列表和统计相关模型
class SubscriptionListRequest(BaseModel):
    """订阅列表请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    subscription_type: Optional[SubscriptionType] = Field(None, description="订阅类型筛选")
    status: Optional[SubscriptionStatus] = Field(None, description="状态筛选")
    user_id: Optional[int] = Field(None, description="用户筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索")

class SubscriptionListResponse(BaseModel):
    """订阅列表响应"""
    subscriptions: List[TestReportSubscriptionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class DistributionListRequest(BaseModel):
    """分发列表请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    subscription_id: Optional[int] = Field(None, description="订阅ID筛选")
    report_id: Optional[int] = Field(None, description="报告ID筛选")
    delivery_channel: Optional[DeliveryChannel] = Field(None, description="分发渠道筛选")
    status: Optional[DistributionStatus] = Field(None, description="状态筛选")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")

class DistributionListResponse(BaseModel):
    """分发列表响应"""
    distributions: List[TestReportDistributionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class DistributionStatistics(BaseModel):
    """分发统计"""
    total_distributions: int = 0
    successful_distributions: int = 0
    failed_distributions: int = 0
    success_rate: float = 0.0
    
    # 按渠道统计
    distributions_by_channel: Dict[str, int] = Field(default_factory=dict)
    success_rate_by_channel: Dict[str, float] = Field(default_factory=dict)
    
    # 按时间统计
    daily_distributions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 时间范围
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class SubscriptionStatistics(BaseModel):
    """订阅统计"""
    total_subscriptions: int = 0
    active_subscriptions: int = 0
    paused_subscriptions: int = 0
    cancelled_subscriptions: int = 0
    
    # 按类型统计
    subscriptions_by_type: Dict[str, int] = Field(default_factory=dict)
    subscriptions_by_channel: Dict[str, int] = Field(default_factory=dict)
    
    # 活跃度统计
    most_active_subscriptions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 时间范围
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None