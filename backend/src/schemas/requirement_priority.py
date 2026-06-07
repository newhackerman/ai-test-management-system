"""
需求优先级管理相关的Pydantic模型

定义API请求和响应的数据结构
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator

from ..models.requirement_priority import (
    PriorityCalculationMethod, PriorityFactorType, ConflictResolutionStrategy,
    PriorityConflictStatus
)
from ..models.requirement import Priority


# 优先级配置相关模型
class CreatePriorityConfigRequest(BaseModel):
    """创建优先级配置请求"""
    project_id: int = Field(..., description="项目ID")
    config_name: str = Field(..., min_length=1, max_length=100, description="配置名称")
    description: Optional[str] = Field(None, description="配置描述")
    calculation_method: PriorityCalculationMethod = Field(
        PriorityCalculationMethod.WEIGHTED_SCORE, description="计算方法"
    )
    business_value_weight: Decimal = Field(0.30, ge=0, le=1, description="商业价值权重")
    user_impact_weight: Decimal = Field(0.25, ge=0, le=1, description="用户影响权重")
    technical_risk_weight: Decimal = Field(0.20, ge=0, le=1, description="技术风险权重")
    implementation_cost_weight: Decimal = Field(0.15, ge=0, le=1, description="实现成本权重")
    time_urgency_weight: Decimal = Field(0.10, ge=0, le=1, description="时间紧迫性权重")
    critical_threshold: Decimal = Field(0.90, ge=0, le=1, description="紧急优先级阈值")
    high_threshold: Decimal = Field(0.70, ge=0, le=1, description="高优先级阈值")
    medium_threshold: Decimal = Field(0.40, ge=0, le=1, description="中优先级阈值")
    low_threshold: Decimal = Field(0.20, ge=0, le=1, description="低优先级阈值")
    conflict_resolution_strategy: ConflictResolutionStrategy = Field(
        ConflictResolutionStrategy.MANUAL_REVIEW, description="冲突解决策略"
    )
    is_default: bool = Field(False, description="是否默认配置")
    additional_config: Optional[Dict[str, Any]] = Field(None, description="额外配置数据")

    @validator('critical_threshold', 'high_threshold', 'medium_threshold', 'low_threshold')
    def validate_thresholds(cls, v, values):
        """验证阈值的合理性"""
        if 'critical_threshold' in values and v >= values['critical_threshold']:
            if v != values['critical_threshold']:
                raise ValueError('阈值必须按递减顺序设置')
        return v


class UpdatePriorityConfigRequest(BaseModel):
    """更新优先级配置请求"""
    config_name: Optional[str] = Field(None, min_length=1, max_length=100, description="配置名称")
    description: Optional[str] = Field(None, description="配置描述")
    calculation_method: Optional[PriorityCalculationMethod] = Field(None, description="计算方法")
    business_value_weight: Optional[Decimal] = Field(None, ge=0, le=1, description="商业价值权重")
    user_impact_weight: Optional[Decimal] = Field(None, ge=0, le=1, description="用户影响权重")
    technical_risk_weight: Optional[Decimal] = Field(None, ge=0, le=1, description="技术风险权重")
    implementation_cost_weight: Optional[Decimal] = Field(None, ge=0, le=1, description="实现成本权重")
    time_urgency_weight: Optional[Decimal] = Field(None, ge=0, le=1, description="时间紧迫性权重")
    critical_threshold: Optional[Decimal] = Field(None, ge=0, le=1, description="紧急优先级阈值")
    high_threshold: Optional[Decimal] = Field(None, ge=0, le=1, description="高优先级阈值")
    medium_threshold: Optional[Decimal] = Field(None, ge=0, le=1, description="中优先级阈值")
    low_threshold: Optional[Decimal] = Field(None, ge=0, le=1, description="低优先级阈值")
    conflict_resolution_strategy: Optional[ConflictResolutionStrategy] = Field(None, description="冲突解决策略")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_default: Optional[bool] = Field(None, description="是否默认配置")
    additional_config: Optional[Dict[str, Any]] = Field(None, description="额外配置数据")


class PriorityConfigResponse(BaseModel):
    """优先级配置响应"""
    id: int
    project_id: int
    config_name: str
    description: Optional[str]
    calculation_method: PriorityCalculationMethod
    business_value_weight: Decimal
    user_impact_weight: Decimal
    technical_risk_weight: Decimal
    implementation_cost_weight: Decimal
    time_urgency_weight: Decimal
    critical_threshold: Decimal
    high_threshold: Decimal
    medium_threshold: Decimal
    low_threshold: Decimal
    conflict_resolution_strategy: ConflictResolutionStrategy
    is_active: bool
    is_default: bool
    additional_config: Optional[Dict[str, Any]]
    created_by: int
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 优先级评估相关模型
class EvaluatePriorityRequest(BaseModel):
    """优先级评估请求"""
    config_id: int = Field(..., description="配置ID")
    business_value_score: Decimal = Field(..., ge=0, le=10, description="商业价值得分")
    user_impact_score: Decimal = Field(..., ge=0, le=10, description="用户影响得分")
    technical_risk_score: Decimal = Field(..., ge=0, le=10, description="技术风险得分")
    implementation_cost_score: Decimal = Field(..., ge=0, le=10, description="实现成本得分")
    time_urgency_score: Decimal = Field(..., ge=0, le=10, description="时间紧迫性得分")
    manual_priority: Optional[Priority] = Field(None, description="手动设置的优先级")
    evaluation_reason: Optional[str] = Field(None, description="评估理由")
    manual_adjustment_reason: Optional[str] = Field(None, description="手动调整原因")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="额外评估数据")


class PriorityEvaluationResponse(BaseModel):
    """优先级评估响应"""
    id: int
    requirement_id: int
    config_id: int
    business_value_score: Decimal
    user_impact_score: Decimal
    technical_risk_score: Decimal
    implementation_cost_score: Decimal
    time_urgency_score: Decimal
    weighted_score: Decimal
    calculated_priority: Priority
    final_priority: Priority
    evaluation_method: PriorityCalculationMethod
    evaluation_reason: Optional[str]
    manual_adjustment_reason: Optional[str]
    evaluator_id: Optional[int]
    approver_id: Optional[int]
    evaluated_at: Optional[datetime]
    approved_at: Optional[datetime]
    is_current: bool
    evaluation_data: Optional[Dict[str, Any]]
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# AI分析相关模型
class AIPriorityAnalysisResponse(BaseModel):
    """AI优先级分析响应"""
    business_value_score: float = Field(..., description="商业价值得分")
    user_impact_score: float = Field(..., description="用户影响得分")
    technical_risk_score: float = Field(..., description="技术风险得分")
    implementation_cost_score: float = Field(..., description="实现成本得分")
    time_urgency_score: float = Field(..., description="时间紧迫性得分")
    weighted_score: float = Field(..., description="加权总分")
    calculated_priority: str = Field(..., description="计算得出的优先级")
    recommended_priority: str = Field(..., description="推荐优先级")
    reasoning: str = Field(..., description="分析理由")
    config_id: int = Field(..., description="使用的配置ID")


# 优先级冲突相关模型
class PriorityConflictResponse(BaseModel):
    """优先级冲突响应"""
    id: int
    requirement_ids: List[int]
    conflict_type: str
    conflict_description: Optional[str]
    severity_level: int
    detected_by_system: bool
    detection_algorithm: Optional[str]
    detection_confidence: Optional[Decimal]
    resolution_strategy: Optional[ConflictResolutionStrategy]
    resolution_description: Optional[str]
    recommended_priorities: Optional[Dict[str, Any]]
    status: PriorityConflictStatus
    assigned_to: Optional[int]
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConflictResolutionRequest(BaseModel):
    """冲突解决请求"""
    resolution_strategy: ConflictResolutionStrategy = Field(..., description="解决策略")
    resolution_notes: str = Field(..., description="解决备注")
    recommended_priorities: Optional[Dict[int, Priority]] = Field(None, description="推荐优先级")


# 优先级历史相关模型
class PriorityHistoryResponse(BaseModel):
    """优先级历史响应"""
    id: int
    requirement_id: int
    old_priority: Optional[Priority]
    new_priority: Priority
    change_reason: Optional[str]
    change_method: Optional[PriorityCalculationMethod]
    change_trigger: Optional[str]
    old_weighted_score: Optional[Decimal]
    new_weighted_score: Optional[Decimal]
    changed_by: int
    changed_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 统计分析相关模型
class PriorityDistributionResponse(BaseModel):
    """优先级分布响应"""
    distribution: Dict[str, int] = Field(..., description="优先级分布统计")
    total_requirements: int = Field(..., description="总需求数")
    project_id: int = Field(..., description="项目ID")


class PriorityTrendResponse(BaseModel):
    """优先级趋势响应"""
    date: str
    priority_counts: Dict[str, int]


class PriorityAnalyticsResponse(BaseModel):
    """优先级分析响应"""
    distribution: PriorityDistributionResponse
    recent_changes: List[PriorityHistoryResponse]
    active_conflicts: List[PriorityConflictResponse]
    trends: List[PriorityTrendResponse]


# 批量操作相关模型
class BatchPriorityEvaluationRequest(BaseModel):
    """批量优先级评估请求"""
    requirement_ids: List[int] = Field(..., description="需求ID列表")
    config_id: int = Field(..., description="配置ID")
    use_ai_analysis: bool = Field(False, description="是否使用AI分析")


class BatchPriorityEvaluationResponse(BaseModel):
    """批量优先级评估响应"""
    success_count: int
    failed_count: int
    success_evaluations: List[PriorityEvaluationResponse]
    failed_requirements: List[Dict[str, Any]]