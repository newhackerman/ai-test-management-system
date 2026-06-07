"""
AI操作日志相关的Pydantic模式定义

定义AI操作日志的请求和响应数据结构，包括：
1. 日志查询请求参数
2. 日志响应数据格式
3. 统计信息数据结构
4. 导出配置参数
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

from ..models.ai_operation_log import AIOperationType, AIOperationResult, AIOperationPriority


class AIOperationLogQuery(BaseModel):
    """AI操作日志查询参数"""
    user_id: Optional[int] = Field(None, description="用户ID")
    operation_type: Optional[str] = Field(None, description="操作类型")
    result: Optional[str] = Field(None, description="操作结果")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    category: Optional[str] = Field(None, description="分类")
    priority: Optional[str] = Field(None, description="优先级")
    is_sensitive: Optional[bool] = Field(None, description="是否敏感操作")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    search_keyword: Optional[str] = Field(None, description="搜索关键词")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="页大小")
    order_by: str = Field("created_at", description="排序字段")
    order_desc: bool = Field(True, description="是否降序")
    
    @validator('operation_type')
    def validate_operation_type(cls, v):
        if v is not None:
            try:
                AIOperationType(v)
            except ValueError:
                raise ValueError(f"无效的操作类型: {v}")
        return v
    
    @validator('result')
    def validate_result(cls, v):
        if v is not None:
            try:
                AIOperationResult(v)
            except ValueError:
                raise ValueError(f"无效的操作结果: {v}")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None:
            try:
                AIOperationPriority(v)
            except ValueError:
                raise ValueError(f"无效的优先级: {v}")
        return v


class AIOperationLogResponse(BaseModel):
    """AI操作日志响应数据"""
    id: int = Field(..., description="日志ID")
    user_id: Optional[int] = Field(None, description="用户ID")
    user_name: Optional[str] = Field(None, description="用户名")
    user_real_name: Optional[str] = Field(None, description="用户真实姓名")
    session_id: Optional[str] = Field(None, description="会话ID")
    operation_type: str = Field(..., description="操作类型")
    operation_name: str = Field(..., description="操作名称")
    operation_description: Optional[str] = Field(None, description="操作描述")
    result: str = Field(..., description="操作结果")
    result_message: Optional[str] = Field(None, description="结果消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_details: Optional[str] = Field(None, description="错误详情")
    resource_type: Optional[str] = Field(None, description="资源类型")
    resource_id: Optional[str] = Field(None, description="资源ID")
    resource_name: Optional[str] = Field(None, description="资源名称")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型")
    tokens_used: Optional[int] = Field(None, description="使用的Token数")
    cost_amount: Optional[float] = Field(None, description="成本金额")
    processing_time: Optional[float] = Field(None, description="处理时间(秒)")
    response_size: Optional[int] = Field(None, description="响应大小(字节)")
    confidence_score: Optional[float] = Field(None, description="置信度分数")
    request_ip: Optional[str] = Field(None, description="请求IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    priority: Optional[str] = Field(None, description="优先级")
    category: Optional[str] = Field(None, description="分类")
    subcategory: Optional[str] = Field(None, description="子分类")
    is_sensitive: Optional[bool] = Field(None, description="是否敏感操作")
    correlation_id: Optional[str] = Field(None, description="关联ID")
    trace_id: Optional[str] = Field(None, description="追踪ID")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")


class AIOperationStatisticsQuery(BaseModel):
    """AI操作统计查询参数"""
    user_id: Optional[int] = Field(None, description="用户ID")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    group_by: str = Field("operation_type", description="分组字段")
    
    @validator('group_by')
    def validate_group_by(cls, v):
        valid_fields = ["operation_type", "result", "ai_provider", "date", "overall"]
        if v not in valid_fields:
            raise ValueError(f"无效的分组字段，支持: {', '.join(valid_fields)}")
        return v


class AIOperationStatisticsResponse(BaseModel):
    """AI操作统计响应数据"""
    group_by: str = Field(..., description="分组字段")
    statistics: Dict[str, Any] = Field(..., description="统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "group_by": "operation_type",
                "statistics": {
                    "AI_MODEL_CALL": {
                        "count": 150,
                        "total_tokens": 45000,
                        "total_cost": 0.9,
                        "avg_processing_time": 2.3
                    },
                    "CONVERSATION_CREATE": {
                        "count": 25,
                        "total_tokens": 0,
                        "total_cost": 0.0,
                        "avg_processing_time": 0.1
                    }
                }
            }
        }


class AIOperationOverallStatisticsResponse(BaseModel):
    """AI操作总体统计响应数据"""
    total_operations: int = Field(..., description="总操作数")
    total_tokens: int = Field(..., description="总Token数")
    total_cost: float = Field(..., description="总成本")
    avg_processing_time: float = Field(..., description="平均处理时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_operations": 1250,
                "total_tokens": 375000,
                "total_cost": 7.5,
                "avg_processing_time": 1.8
            }
        }


class AIOperationExportQuery(BaseModel):
    """AI操作日志导出参数"""
    format_type: str = Field("json", description="导出格式 (json, csv)")
    user_id: Optional[int] = Field(None, description="用户ID")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    operation_type: Optional[str] = Field(None, description="操作类型")
    
    @validator('format_type')
    def validate_format_type(cls, v):
        if v not in ["json", "csv"]:
            raise ValueError("不支持的导出格式，支持: json, csv")
        return v


class AIOperationTypeInfo(BaseModel):
    """AI操作类型信息"""
    value: str = Field(..., description="操作类型值")
    label: str = Field(..., description="操作类型标签")
    category: str = Field(..., description="操作类型分类")
    
    class Config:
        json_schema_extra = {
            "example": {
                "value": "AI_MODEL_CALL",
                "label": "AI模型调用",
                "category": "AI服务"
            }
        }


class AIOperationCleanupRequest(BaseModel):
    """AI操作日志清理请求"""
    days_to_keep: int = Field(90, ge=7, le=365, description="保留天数")


class AIOperationCleanupResponse(BaseModel):
    """AI操作日志清理响应"""
    cleaned_count: int = Field(..., description="清理的日志数量")
    days_to_keep: int = Field(..., description="保留天数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cleaned_count": 1500,
                "days_to_keep": 90
            }
        }


class AIOperationSummaryRequest(BaseModel):
    """AI操作日志汇总请求"""
    target_date: Optional[str] = Field(None, description="目标日期 (YYYY-MM-DD)，默认为昨天")


class AIOperationSummaryResponse(BaseModel):
    """AI操作日志汇总响应"""
    target_date: str = Field(..., description="目标日期")
    success: bool = Field(..., description="是否成功")
    
    class Config:
        json_schema_extra = {
            "example": {
                "target_date": "2024-12-18",
                "success": True
            }
        }


class AIOperationLogCreate(BaseModel):
    """创建AI操作日志请求"""
    operation_type: str = Field(..., description="操作类型")
    operation_name: str = Field(..., description="操作名称")
    operation_description: Optional[str] = Field(None, description="操作描述")
    result: str = Field(..., description="操作结果")
    result_message: Optional[str] = Field(None, description="结果消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_details: Optional[str] = Field(None, description="错误详情")
    resource_type: Optional[str] = Field(None, description="资源类型")
    resource_id: Optional[str] = Field(None, description="资源ID")
    resource_name: Optional[str] = Field(None, description="资源名称")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型")
    tokens_used: Optional[int] = Field(None, description="使用的Token数")
    cost_amount: Optional[float] = Field(None, description="成本金额")
    processing_time: Optional[float] = Field(None, description="处理时间(秒)")
    confidence_score: Optional[float] = Field(None, description="置信度分数")
    priority: Optional[str] = Field("MEDIUM", description="优先级")
    category: Optional[str] = Field(None, description="分类")
    subcategory: Optional[str] = Field(None, description="子分类")
    is_sensitive: bool = Field(False, description="是否敏感操作")
    business_context: Optional[Dict[str, Any]] = Field(None, description="业务上下文")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    @validator('operation_type')
    def validate_operation_type(cls, v):
        try:
            AIOperationType(v)
        except ValueError:
            raise ValueError(f"无效的操作类型: {v}")
        return v
    
    @validator('result')
    def validate_result(cls, v):
        try:
            AIOperationResult(v)
        except ValueError:
            raise ValueError(f"无效的操作结果: {v}")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None:
            try:
                AIOperationPriority(v)
            except ValueError:
                raise ValueError(f"无效的优先级: {v}")
        return v


class AIOperationLogBatchCreate(BaseModel):
    """批量创建AI操作日志请求"""
    logs: List[AIOperationLogCreate] = Field(..., description="日志列表")
    
    @validator('logs')
    def validate_logs_count(cls, v):
        if len(v) > 100:
            raise ValueError("批量创建日志数量不能超过100条")
        return v