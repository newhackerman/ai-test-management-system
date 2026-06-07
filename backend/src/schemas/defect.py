"""
缺陷管理模块数据传输对象(DTO)

本模块定义了缺陷管理相关的数据传输对象，包括：
- 缺陷创建和更新请求
- 缺陷查询响应
- 缺陷分析和统计
- 缺陷状态流转
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.test_case import DefectType, DefectSeverity, DefectStatus, DefectResolution, TestCasePriority

class DefectBase(BaseModel):
    """缺陷基础模型"""
    title: str = Field(..., min_length=1, max_length=200, description="缺陷标题")
    description: str = Field(..., min_length=1, description="缺陷描述")
    steps_to_reproduce: Optional[str] = Field(None, description="重现步骤")
    defect_type: DefectType = Field(..., description="缺陷类型")
    severity: DefectSeverity = Field(..., description="严重程度")
    priority: TestCasePriority = Field(..., description="优先级")
    found_in_version: Optional[str] = Field(None, max_length=50, description="发现版本")
    test_environment: Optional[str] = Field(None, max_length=100, description="测试环境")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")

class CreateDefectRequest(DefectBase):
    """创建缺陷请求"""
    test_execution_id: Optional[int] = Field(None, description="关联测试执行ID")
    test_case_id: Optional[int] = Field(None, description="关联测试用例ID")
    requirement_id: Optional[int] = Field(None, description="关联需求ID")
    assignee_id: Optional[int] = Field(None, description="分配人ID")

    @validator('test_execution_id', 'test_case_id', 'requirement_id', 'assignee_id')
    def validate_positive_ids(cls, v):
        if v is not None and v <= 0:
            raise ValueError('ID必须为正整数')
        return v

class UpdateDefectRequest(BaseModel):
    """更新缺陷请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="缺陷标题")
    description: Optional[str] = Field(None, min_length=1, description="缺陷描述")
    steps_to_reproduce: Optional[str] = Field(None, description="重现步骤")
    defect_type: Optional[DefectType] = Field(None, description="缺陷类型")
    severity: Optional[DefectSeverity] = Field(None, description="严重程度")
    priority: Optional[TestCasePriority] = Field(None, description="优先级")
    assignee_id: Optional[int] = Field(None, description="分配人ID")
    found_in_version: Optional[str] = Field(None, max_length=50, description="发现版本")
    fixed_in_version: Optional[str] = Field(None, max_length=50, description="修复版本")
    test_environment: Optional[str] = Field(None, max_length=100, description="测试环境")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")

class DefectStatusUpdateRequest(BaseModel):
    """缺陷状态更新请求"""
    status: DefectStatus = Field(..., description="新状态")
    resolution: Optional[DefectResolution] = Field(None, description="解决方案")
    notes: Optional[str] = Field(None, description="状态变更备注")

    @validator('resolution')
    def validate_resolution(cls, v, values):
        if 'status' in values and values['status'] == DefectStatus.RESOLVED and v is None:
            raise ValueError('解决状态必须提供解决方案')
        return v

class DefectResponse(DefectBase):
    """缺陷响应模型"""
    id: int
    defect_code: str
    test_execution_id: Optional[int]
    test_case_id: Optional[int]
    requirement_id: Optional[int]
    status: DefectStatus
    resolution: Optional[DefectResolution]
    fixed_in_version: Optional[str]
    reporter_id: int
    assignee_id: Optional[int]
    resolver_id: Optional[int]
    reported_at: datetime
    assigned_at: Optional[datetime]
    resolved_at: Optional[datetime]
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DefectListResponse(BaseModel):
    """缺陷列表响应"""
    defects: List[DefectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class DefectQueryParams(BaseModel):
    """缺陷查询参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    status: Optional[DefectStatus] = Field(None, description="状态筛选")
    severity: Optional[DefectSeverity] = Field(None, description="严重程度筛选")
    priority: Optional[TestCasePriority] = Field(None, description="优先级筛选")
    defect_type: Optional[DefectType] = Field(None, description="缺陷类型筛选")
    assignee_id: Optional[int] = Field(None, description="分配人筛选")
    reporter_id: Optional[int] = Field(None, description="报告人筛选")
    test_case_id: Optional[int] = Field(None, description="测试用例筛选")
    requirement_id: Optional[int] = Field(None, description="需求筛选")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")

class DefectStatistics(BaseModel):
    """缺陷统计"""
    total_defects: int = Field(0, description="总缺陷数")
    new_defects: int = Field(0, description="新建缺陷数")
    assigned_defects: int = Field(0, description="已分配缺陷数")
    in_progress_defects: int = Field(0, description="处理中缺陷数")
    resolved_defects: int = Field(0, description="已解决缺陷数")
    closed_defects: int = Field(0, description="已关闭缺陷数")
    reopened_defects: int = Field(0, description="重新打开缺陷数")
    
    # 按严重程度统计
    critical_defects: int = Field(0, description="严重缺陷数")
    high_defects: int = Field(0, description="高级缺陷数")
    medium_defects: int = Field(0, description="中级缺陷数")
    low_defects: int = Field(0, description="低级缺陷数")
    
    # 按类型统计
    functional_defects: int = Field(0, description="功能缺陷数")
    performance_defects: int = Field(0, description="性能缺陷数")
    security_defects: int = Field(0, description="安全缺陷数")
    usability_defects: int = Field(0, description="易用性缺陷数")
    
    # 质量指标
    defect_density: float = Field(0.0, description="缺陷密度")
    resolution_rate: float = Field(0.0, description="解决率")
    reopen_rate: float = Field(0.0, description="重开率")
    avg_resolution_time: float = Field(0.0, description="平均解决时间(小时)")

class DefectTrendData(BaseModel):
    """缺陷趋势数据"""
    date: date
    new_count: int = Field(0, description="新增数量")
    resolved_count: int = Field(0, description="解决数量")
    closed_count: int = Field(0, description="关闭数量")
    total_count: int = Field(0, description="累计数量")

class DefectTrendAnalysis(BaseModel):
    """缺陷趋势分析"""
    project_id: int
    time_range: str
    trend_data: List[DefectTrendData]
    statistics: DefectStatistics
    predictions: Optional[Dict[str, Any]] = Field(None, description="AI预测数据")
    suggestions: Optional[List[str]] = Field(None, description="改进建议")
    generated_at: datetime

class DefectAssignmentSuggestion(BaseModel):
    """缺陷分配建议"""
    assignee_id: int
    assignee_name: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    reason: str = Field(..., description="推荐理由")
    workload: int = Field(0, description="当前工作负载")
    expertise_match: float = Field(..., ge=0.0, le=1.0, description="专业匹配度")

class DefectSimilarityResult(BaseModel):
    """缺陷相似性检测结果"""
    similar_defect_id: int
    similar_defect_code: str
    similar_defect_title: str
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="相似度分数")
    similarity_reasons: List[str] = Field(..., description="相似性原因")

class DefectAnalysisResult(BaseModel):
    """缺陷AI分析结果"""
    suggested_type: Optional[DefectType] = Field(None, description="建议的缺陷类型")
    suggested_severity: Optional[DefectSeverity] = Field(None, description="建议的严重程度")
    suggested_priority: Optional[TestCasePriority] = Field(None, description="建议的优先级")
    root_cause_analysis: Optional[str] = Field(None, description="根因分析")
    fix_suggestions: Optional[List[str]] = Field(None, description="修复建议")
    similar_defects: Optional[List[DefectSimilarityResult]] = Field(None, description="相似缺陷")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="分析置信度")

class DefectStatusHistory(BaseModel):
    """缺陷状态历史"""
    id: int
    defect_id: int
    old_status: DefectStatus
    new_status: DefectStatus
    changed_by: int
    changed_at: datetime
    notes: Optional[str]

class DefectComment(BaseModel):
    """缺陷评论"""
    id: int
    defect_id: int
    user_id: int
    user_name: str
    content: str
    created_at: datetime
    updated_at: datetime

class DefectCommentRequest(BaseModel):
    """缺陷评论请求"""
    content: str = Field(..., min_length=1, description="评论内容")

class DefectBatchUpdateRequest(BaseModel):
    """缺陷批量更新请求"""
    defect_ids: List[int] = Field(..., min_items=1, description="缺陷ID列表")
    updates: Dict[str, Any] = Field(..., description="更新字段")

class DefectExportRequest(BaseModel):
    """缺陷导出请求"""
    format: str = Field("excel", description="导出格式")
    filters: Optional[DefectQueryParams] = Field(None, description="筛选条件")
    fields: Optional[List[str]] = Field(None, description="导出字段")

class DefectImportRequest(BaseModel):
    """缺陷导入请求"""
    file_path: str = Field(..., description="文件路径")
    mapping: Dict[str, str] = Field(..., description="字段映射")
    skip_duplicates: bool = Field(True, description="跳过重复项")

class DefectMetrics(BaseModel):
    """缺陷度量指标"""
    defect_discovery_rate: float = Field(0.0, description="缺陷发现率")
    defect_escape_rate: float = Field(0.0, description="缺陷逃逸率")
    defect_removal_efficiency: float = Field(0.0, description="缺陷移除效率")
    mean_time_to_resolution: float = Field(0.0, description="平均解决时间")
    defect_age_distribution: Dict[str, int] = Field(default_factory=dict, description="缺陷年龄分布")
    defect_injection_rate: float = Field(0.0, description="缺陷注入率")