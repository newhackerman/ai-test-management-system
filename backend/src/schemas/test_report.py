"""
测试报告数据传输对象(DTO)

本模块定义了测试报告相关的数据传输对象
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

class ReportType(str, Enum):
    """报告类型枚举"""
    SUMMARY = "summary"
    DETAILED = "detailed"
    EXECUTIVE = "executive"
    DEFECT_ANALYSIS = "defect_analysis"
    COVERAGE = "coverage"
    PERFORMANCE = "performance"
    CUSTOM = "custom"

class ExportFormat(str, Enum):
    """导出格式枚举"""
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"
    WORD = "word"
    JSON = "json"

class ScheduleType(str, Enum):
    """调度类型枚举"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"

class ReportStatus(str, Enum):
    """报告状态枚举"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 基础模型
class ReportTemplate(BaseModel):
    """报告模板"""
    id: int
    name: str
    description: Optional[str] = None
    template_type: str
    template_content: Optional[Dict[str, Any]] = None
    default_config: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TestReportRequest(BaseModel):
    """测试报告生成请求"""
    report_name: str = Field(..., min_length=1, max_length=200, description="报告名称")
    description: Optional[str] = Field(None, description="报告描述")
    report_type: ReportType = Field(ReportType.SUMMARY, description="报告类型")
    project_id: Optional[int] = Field(None, description="项目ID")
    template_id: Optional[int] = Field(None, description="模板ID")
    
    # 数据范围
    date_range: Optional[Dict[str, datetime]] = Field(None, description="数据时间范围")
    include_sections: List[str] = Field(default_factory=list, description="包含的章节")
    
    # 导出配置
    export_formats: List[ExportFormat] = Field(default=[ExportFormat.HTML], description="导出格式")
    
    # 自定义配置
    custom_config: Optional[Dict[str, Any]] = Field(None, description="自定义配置")
    
    @validator('export_formats')
    def validate_export_formats(cls, v):
        if not v:
            raise ValueError('至少选择一种导出格式')
        return v

class TestReportResponse(BaseModel):
    """测试报告响应"""
    id: int
    name: str
    description: Optional[str] = None
    report_type: str
    project_id: Optional[int] = None
    template_id: Optional[int] = None
    
    # 报告配置
    report_config: Optional[Dict[str, Any]] = None
    include_sections: Optional[List[str]] = None
    date_range: Optional[Dict[str, Any]] = None
    export_formats: Optional[List[str]] = None
    
    # 文件信息
    file_paths: Optional[Dict[str, str]] = None
    file_size: Optional[int] = None
    
    # 状态信息
    status: str
    generation_time: Optional[float] = None
    error_message: Optional[str] = None
    
    # 统计信息
    view_count: int = 0
    download_count: int = 0
    
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReportTemplateRequest(BaseModel):
    """报告模板创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_type: ReportType = Field(..., description="模板类型")
    template_content: Dict[str, Any] = Field(..., description="模板内容")
    default_config: Optional[Dict[str, Any]] = Field(None, description="默认配置")

class ReportScheduleRequest(BaseModel):
    """报告调度请求"""
    name: str = Field(..., min_length=1, max_length=100, description="调度任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    report_config: Dict[str, Any] = Field(..., description="报告配置")
    template_id: Optional[int] = Field(None, description="模板ID")
    
    # 调度配置
    schedule_type: ScheduleType = Field(..., description="调度类型")
    schedule_expression: str = Field(..., description="调度表达式")
    timezone: str = Field("UTC", description="时区")
    
    # 通知配置
    recipients: Optional[List[str]] = Field(None, description="接收人邮箱列表")
    notification_config: Optional[Dict[str, Any]] = Field(None, description="通知配置")

class ReportScheduleResponse(BaseModel):
    """报告调度响应"""
    id: int
    name: str
    description: Optional[str] = None
    report_config: Dict[str, Any]
    template_id: Optional[int] = None
    
    # 调度配置
    schedule_type: str
    schedule_expression: str
    timezone: str
    
    # 通知配置
    recipients: Optional[List[str]] = None
    notification_config: Optional[Dict[str, Any]] = None
    
    # 状态信息
    is_active: bool
    last_run_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    run_count: int = 0
    
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReportExportRequest(BaseModel):
    """报告导出请求"""
    report_id: int = Field(..., description="报告ID")
    export_format: ExportFormat = Field(..., description="导出格式")
    custom_config: Optional[Dict[str, Any]] = Field(None, description="自定义配置")

class ReportShareRequest(BaseModel):
    """报告分享请求"""
    report_id: int = Field(..., description="报告ID")
    share_type: str = Field("link", description="分享类型")
    password_protected: bool = Field(False, description="是否密码保护")
    access_password: Optional[str] = Field(None, description="访问密码")
    max_access_count: Optional[int] = Field(None, description="最大访问次数")
    expires_hours: Optional[int] = Field(None, description="有效期(小时)")
    allowed_users: Optional[List[int]] = Field(None, description="允许访问的用户ID列表")

class ReportShareResponse(BaseModel):
    """报告分享响应"""
    id: int
    report_id: int
    share_token: str
    share_type: str
    share_url: str
    password_protected: bool
    max_access_count: Optional[int] = None
    access_count: int = 0
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReportStatistics(BaseModel):
    """报告统计"""
    total_reports: int = 0
    reports_by_type: Dict[str, int] = Field(default_factory=dict)
    reports_by_status: Dict[str, int] = Field(default_factory=dict)
    reports_by_format: Dict[str, int] = Field(default_factory=dict)
    
    # 生成时间统计
    avg_generation_time: float = 0.0
    max_generation_time: float = 0.0
    min_generation_time: float = 0.0
    
    # 使用统计
    total_views: int = 0
    total_downloads: int = 0
    usage_trend: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 时间范围
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ReportListRequest(BaseModel):
    """报告列表请求"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    project_id: Optional[int] = Field(None, description="项目ID筛选")
    report_type: Optional[ReportType] = Field(None, description="报告类型筛选")
    status: Optional[ReportStatus] = Field(None, description="状态筛选")
    created_by: Optional[int] = Field(None, description="创建人筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")

class ReportListResponse(BaseModel):
    """报告列表响应"""
    reports: List[TestReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class ReportCommentRequest(BaseModel):
    """报告评论请求"""
    content: str = Field(..., min_length=1, description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论ID")

class ReportCommentResponse(BaseModel):
    """报告评论响应"""
    id: int
    report_id: int
    user_id: int
    user_name: str
    content: str
    parent_id: Optional[int] = None
    replies: List['ReportCommentResponse'] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 更新前向引用
ReportCommentResponse.model_rebuild()