"""
AI分析相关的Pydantic模型

本模块定义了会议AI分析API的请求和响应数据模型，包括：
- 会议摘要生成的请求和响应模型
- 会议纪要生成的请求和响应模型
- 会议分析数据的响应模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.meeting import MinuteType, GenerationMethod, MinuteStatus


class MinuteTypeEnum(str, Enum):
    """纪要类型枚举"""
    AUTO_GENERATED = "AUTO_GENERATED"
    MANUAL_CREATED = "MANUAL_CREATED"
    AI_ENHANCED = "AI_ENHANCED"
    COLLABORATIVE = "COLLABORATIVE"


class GenerationMethodEnum(str, Enum):
    """生成方式枚举"""
    SPEECH_TO_TEXT = "SPEECH_TO_TEXT"
    MANUAL_INPUT = "MANUAL_INPUT"
    AI_ANALYSIS = "AI_ANALYSIS"
    TEMPLATE_BASED = "TEMPLATE_BASED"


class MinuteStatusEnum(str, Enum):
    """纪要状态枚举"""
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class GenerateSummaryRequest(BaseModel):
    """生成会议摘要请求模型"""
    include_transcript: bool = Field(True, description="是否包含转录内容")
    include_chat: bool = Field(True, description="是否包含聊天记录")
    include_files: bool = Field(False, description="是否包含文件信息")
    summary_length: str = Field("medium", description="摘要长度", pattern="^(short|medium|long|detailed)$")
    language: str = Field("zh-CN", description="摘要语言")
    focus_areas: Optional[List[str]] = Field(None, description="重点关注领域")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词", max_length=1000)


class KeyPoint(BaseModel):
    """关键要点模型"""
    title: str = Field(..., description="要点标题")
    content: str = Field(..., description="要点内容")
    importance: int = Field(..., description="重要性评分(1-5)", ge=1, le=5)
    timestamp: Optional[datetime] = Field(None, description="相关时间点")
    participants: Optional[List[str]] = Field(None, description="相关参与者")


class Decision(BaseModel):
    """决策事项模型"""
    decision_id: str = Field(..., description="决策ID")
    title: str = Field(..., description="决策标题")
    description: str = Field(..., description="决策描述")
    decision_maker: Optional[str] = Field(None, description="决策者")
    impact_level: str = Field("medium", description="影响级别", pattern="^(low|medium|high|critical)$")
    implementation_date: Optional[datetime] = Field(None, description="实施日期")
    status: str = Field("pending", description="决策状态")
    related_requirements: Optional[List[str]] = Field(None, description="相关需求")


class ActionItem(BaseModel):
    """行动项目模型"""
    action_id: str = Field(..., description="行动项ID")
    title: str = Field(..., description="行动项标题")
    description: str = Field(..., description="行动项描述")
    assignee: Optional[str] = Field(None, description="负责人")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    priority: str = Field("medium", description="优先级", pattern="^(low|medium|high|urgent)$")
    status: str = Field("pending", description="状态")
    estimated_hours: Optional[float] = Field(None, description="预估工时")
    dependencies: Optional[List[str]] = Field(None, description="依赖项")


class MeetingSummaryResponse(BaseModel):
    """会议摘要响应模型"""
    meeting_id: int = Field(..., description="会议ID")
    overview: str = Field(..., description="会议概述")
    key_points: List[KeyPoint] = Field(..., description="关键要点")
    decisions: List[Decision] = Field(..., description="决策事项")
    action_items: List[ActionItem] = Field(..., description="行动项目")
    next_steps: List[str] = Field(..., description="下一步计划")
    participants_summary: Dict[str, Any] = Field(..., description="参与者摘要")
    meeting_effectiveness: Dict[str, Any] = Field(..., description="会议效果评估")
    generated_at: datetime = Field(..., description="生成时间")
    generation_method: str = Field(..., description="生成方式")
    language: str = Field(..., description="语言")

    class Config:
        from_attributes = True


class GenerateSummaryResponse(BaseModel):
    """生成会议摘要响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("会议摘要生成成功", description="响应消息")
    data: MeetingSummaryResponse = Field(..., description="摘要数据")

    class Config:
        from_attributes = True


class GenerateMinutesRequest(BaseModel):
    """生成会议纪要请求模型"""
    template_type: str = Field("standard", description="纪要模板类型")
    include_summary: bool = Field(True, description="是否包含摘要")
    include_transcript: bool = Field(False, description="是否包含完整转录")
    include_attachments: bool = Field(True, description="是否包含附件信息")
    format_style: str = Field("formal", description="格式风格", pattern="^(formal|casual|technical)$")
    language: str = Field("zh-CN", description="纪要语言")
    auto_structure: bool = Field(True, description="是否自动结构化")
    custom_sections: Optional[List[str]] = Field(None, description="自定义章节")


class MeetingMinutesResponse(BaseModel):
    """会议纪要响应模型"""
    id: int = Field(..., description="纪要ID")
    meeting_id: int = Field(..., description="会议ID")
    title: str = Field(..., description="纪要标题")
    content: str = Field(..., description="纪要内容")
    summary: Optional[str] = Field(None, description="会议摘要")
    minute_type: str = Field(..., description="纪要类型")
    generation_method: str = Field(..., description="生成方式")
    agenda_items: Optional[List[Dict[str, Any]]] = Field(None, description="议程项目")
    decisions: Optional[List[Dict[str, Any]]] = Field(None, description="决策事项")
    action_items: Optional[List[Dict[str, Any]]] = Field(None, description="行动项目")
    attendees: Optional[List[str]] = Field(None, description="参会人员")
    key_points: Optional[List[Dict[str, Any]]] = Field(None, description="关键要点")
    status: str = Field(..., description="纪要状态")
    approval_required: bool = Field(..., description="是否需要审批")
    version: str = Field(..., description="版本号")
    parent_minute_id: Optional[int] = Field(None, description="父纪要ID")
    approved_by: Optional[int] = Field(None, description="审批者ID")
    approved_at: Optional[datetime] = Field(None, description="审批时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: Optional[int] = Field(None, description="创建者ID")

    class Config:
        from_attributes = True


class GenerateMinutesResponse(BaseModel):
    """生成会议纪要响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("会议纪要生成成功", description="响应消息")
    data: MeetingMinutesResponse = Field(..., description="纪要数据")

    class Config:
        from_attributes = True


class ParticipationMetrics(BaseModel):
    """参与度指标模型"""
    user_id: int = Field(..., description="用户ID")
    user_name: str = Field(..., description="用户姓名")
    speaking_time_minutes: float = Field(..., description="发言时长(分钟)")
    speaking_percentage: float = Field(..., description="发言占比(%)")
    interaction_count: int = Field(..., description="互动次数")
    engagement_score: float = Field(..., description="参与度评分(1-5)")
    attention_score: float = Field(..., description="专注度评分(1-5)")
    contribution_quality: float = Field(..., description="贡献质量评分(1-5)")


class MeetingAnalyticsResponse(BaseModel):
    """会议分析响应模型"""
    meeting_id: int = Field(..., description="会议ID")
    overall_effectiveness: float = Field(..., description="整体效果评分(1-5)")
    participation_metrics: List[ParticipationMetrics] = Field(..., description="参与度指标")
    agenda_completion_rate: float = Field(..., description="议程完成率(%)")
    decision_efficiency: float = Field(..., description="决策效率评分(1-5)")
    time_utilization: float = Field(..., description="时间利用率(%)")
    sentiment_analysis: Dict[str, Any] = Field(..., description="情感分析")
    improvement_suggestions: List[str] = Field(..., description="改进建议")
    meeting_quality_score: float = Field(..., description="会议质量评分(1-5)")
    network_quality_avg: float = Field(..., description="平均网络质量评分(1-5)")
    technical_issues_count: int = Field(..., description="技术问题次数")
    analyzed_at: datetime = Field(..., description="分析时间")
    data_sources: Optional[Dict[str, Any]] = Field(
        None, description="各指标的数据来源/缺失说明（无真实来源的字段不编数字）"
    )

    class Config:
        from_attributes = True


class CreateActionItemRequest(BaseModel):
    """新建行动项请求模型（基于 meeting_tasks + project_tasks）"""
    title: str = Field(..., description="行动项标题", max_length=200)
    description: Optional[str] = Field(None, description="行动项描述")
    assignee_id: Optional[int] = Field(None, description="负责人用户ID")
    assignee: Optional[str] = Field(None, description="负责人用户名/昵称（assignee_id 为空时按名查找）")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    priority: str = Field("medium", description="优先级", pattern="^(low|medium|high|urgent)$")
    status: str = Field("pending", description="状态", pattern="^(pending|in_progress|completed|cancelled)$")
    estimated_hours: Optional[float] = Field(None, description="预估工时", ge=0)


class UpdateActionItemRequest(BaseModel):
    """更新行动项请求模型（全部字段可选）"""
    title: Optional[str] = Field(None, description="行动项标题", max_length=200)
    description: Optional[str] = Field(None, description="行动项描述")
    assignee_id: Optional[int] = Field(None, description="负责人用户ID")
    assignee: Optional[str] = Field(None, description="负责人用户名/昵称")
    due_date: Optional[datetime] = Field(None, description="截止日期")
    priority: Optional[str] = Field(None, description="优先级", pattern="^(low|medium|high|urgent)$")
    status: Optional[str] = Field(None, description="状态", pattern="^(pending|in_progress|completed|cancelled)$")
    estimated_hours: Optional[float] = Field(None, description="预估工时", ge=0)


class GenerateReportRequest(BaseModel):
    """生成会议报告请求模型"""
    report_type: str = Field("full", description="报告类型（full/effectiveness/summary，聚合内容相同，按类型命名）")
    format: str = Field("markdown", description="导出格式", pattern="^(html|markdown)$")


class GenerateReportResponse(BaseModel):
    """生成会议报告响应模型"""
    report_id: str = Field(..., description="报告ID（用于下载）")
    meeting_id: int = Field(..., description="会议ID")
    report_type: str = Field(..., description="报告类型")
    format: str = Field(..., description="导出格式")
    file_name: str = Field(..., description="报告文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    media_type: str = Field(..., description="媒体类型")
    download_url: str = Field(..., description="下载链接")
    generated_at: datetime = Field(..., description="生成时间")


class GetAnalyticsResponse(BaseModel):
    """获取会议分析响应模型"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("会议分析获取成功", description="响应消息")
    data: MeetingAnalyticsResponse = Field(..., description="分析数据")

    class Config:
        from_attributes = True


class TranscriptionSegment(BaseModel):
    """转录片段模型"""
    start_time: float = Field(..., description="开始时间(秒)")
    end_time: float = Field(..., description="结束时间(秒)")
    speaker_id: Optional[int] = Field(None, description="发言人ID")
    speaker_name: Optional[str] = Field(None, description="发言人姓名")
    text: str = Field(..., description="转录文本")
    confidence: float = Field(..., description="置信度(0-1)")
    language: str = Field("zh-CN", description="语言")


class TranscriptionResponse(BaseModel):
    """转录响应模型"""
    meeting_id: int = Field(..., description="会议ID")
    segments: List[TranscriptionSegment] = Field(..., description="转录片段")
    full_text: str = Field(..., description="完整转录文本")
    total_duration: float = Field(..., description="总时长(秒)")
    language: str = Field(..., description="主要语言")
    accuracy_score: float = Field(..., description="准确度评分(0-1)")
    generated_at: datetime = Field(..., description="生成时间")

    class Config:
        from_attributes = True


class SentimentAnalysis(BaseModel):
    """情感分析模型"""
    overall_sentiment: str = Field(..., description="整体情感")  # positive, neutral, negative
    sentiment_score: float = Field(..., description="情感评分(-1到1)")
    emotion_distribution: Dict[str, float] = Field(..., description="情感分布")
    engagement_level: str = Field(..., description="参与度水平")  # low, medium, high
    tension_points: List[Dict[str, Any]] = Field(..., description="紧张时刻")
    positive_moments: List[Dict[str, Any]] = Field(..., description="积极时刻")


class TopicAnalysis(BaseModel):
    """主题分析模型"""
    main_topics: List[str] = Field(..., description="主要话题")
    topic_distribution: Dict[str, float] = Field(..., description="话题分布")
    topic_transitions: List[Dict[str, Any]] = Field(..., description="话题转换")
    off_topic_percentage: float = Field(..., description="偏题比例(%)")
    focus_score: float = Field(..., description="专注度评分(1-5)")


class AdvancedAnalyticsResponse(BaseModel):
    """高级分析响应模型"""
    meeting_id: int = Field(..., description="会议ID")
    transcription: TranscriptionResponse = Field(..., description="转录结果")
    sentiment_analysis: SentimentAnalysis = Field(..., description="情感分析")
    topic_analysis: TopicAnalysis = Field(..., description="主题分析")
    speaker_insights: List[Dict[str, Any]] = Field(..., description="发言人洞察")
    meeting_flow_analysis: Dict[str, Any] = Field(..., description="会议流程分析")
    recommendations: List[str] = Field(..., description="优化建议")
    analyzed_at: datetime = Field(..., description="分析时间")

    class Config:
        from_attributes = True