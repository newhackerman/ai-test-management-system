"""
需求分类管理相关的Pydantic模型

定义API请求和响应的数据结构
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

from ..models.requirement_classification import (
    ClassificationDimension, ClassificationStatus, ClassificationSuggestionStatus
)


# 分类维度相关模型
class CreateClassificationDimensionRequest(BaseModel):
    """创建分类维度请求"""
    dimension_code: str = Field(..., min_length=1, max_length=50, description="维度编码")
    dimension_name: str = Field(..., min_length=1, max_length=100, description="维度名称")
    dimension_type: ClassificationDimension = Field(..., description="维度类型")
    description: Optional[str] = Field(None, description="维度描述")
    is_hierarchical: bool = Field(False, description="是否支持层级结构")
    is_multi_select: bool = Field(False, description="是否支持多选")
    is_required: bool = Field(False, description="是否必填")
    sort_order: int = Field(0, description="排序顺序")
    config_data: Optional[Dict[str, Any]] = Field(None, description="配置数据")


class UpdateClassificationDimensionRequest(BaseModel):
    """更新分类维度请求"""
    dimension_name: Optional[str] = Field(None, min_length=1, max_length=100, description="维度名称")
    description: Optional[str] = Field(None, description="维度描述")
    is_hierarchical: Optional[bool] = Field(None, description="是否支持层级结构")
    is_multi_select: Optional[bool] = Field(None, description="是否支持多选")
    is_required: Optional[bool] = Field(None, description="是否必填")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    status: Optional[ClassificationStatus] = Field(None, description="状态")
    config_data: Optional[Dict[str, Any]] = Field(None, description="配置数据")


class ClassificationDimensionResponse(BaseModel):
    """分类维度响应"""
    id: int
    dimension_code: str
    dimension_name: str
    dimension_type: ClassificationDimension
    description: Optional[str]
    is_hierarchical: bool
    is_multi_select: bool
    is_required: bool
    sort_order: int
    status: ClassificationStatus
    config_data: Optional[Dict[str, Any]]
    created_by: int
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 分类类别相关模型
class CreateClassificationCategoryRequest(BaseModel):
    """创建分类类别请求"""
    dimension_id: int = Field(..., description="所属维度ID")
    parent_id: Optional[int] = Field(None, description="父类别ID")
    category_code: str = Field(..., min_length=1, max_length=50, description="类别编码")
    category_name: str = Field(..., min_length=1, max_length=100, description="类别名称")
    description: Optional[str] = Field(None, description="类别描述")
    sort_order: int = Field(0, description="排序顺序")
    attributes: Optional[Dict[str, Any]] = Field(None, description="类别属性")


class UpdateClassificationCategoryRequest(BaseModel):
    """更新分类类别请求"""
    category_name: Optional[str] = Field(None, min_length=1, max_length=100, description="类别名称")
    description: Optional[str] = Field(None, description="类别描述")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    status: Optional[ClassificationStatus] = Field(None, description="状态")
    attributes: Optional[Dict[str, Any]] = Field(None, description="类别属性")


class ClassificationCategoryResponse(BaseModel):
    """分类类别响应"""
    id: int
    dimension_id: int
    parent_id: Optional[int]
    category_code: str
    category_name: str
    description: Optional[str]
    level: int
    path: str
    sort_order: int
    status: ClassificationStatus
    usage_count: int
    attributes: Optional[Dict[str, Any]]
    created_by: int
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    children: Optional[List['ClassificationCategoryResponse']] = None

    class Config:
        from_attributes = True


# 需求分类相关模型
class ClassifyRequirementRequest(BaseModel):
    """需求分类请求"""
    category_ids: List[int] = Field(..., description="类别ID列表")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="置信度评分")
    is_auto_classified: bool = Field(False, description="是否自动分类")
    classification_reason: Optional[str] = Field(None, description="分类原因")
    replace_existing: bool = Field(False, description="是否替换现有分类")


class RequirementClassificationResponse(BaseModel):
    """需求分类响应"""
    id: int
    requirement_id: int
    category_id: int
    confidence_score: Optional[float]
    is_auto_classified: bool
    classification_reason: Optional[str]
    created_by: int
    created_at: datetime
    category: Optional[ClassificationCategoryResponse] = None

    class Config:
        from_attributes = True


# 分类建议相关模型
class ClassificationSuggestionResponse(BaseModel):
    """分类建议响应"""
    id: int
    requirement_id: int
    category_id: int
    suggestion_type: str
    confidence_score: float
    reasoning: Optional[str]
    status: ClassificationSuggestionStatus
    processed_by: Optional[int]
    processed_at: Optional[datetime]
    feedback: Optional[str]
    expires_at: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime
    category: Optional[ClassificationCategoryResponse] = None

    class Config:
        from_attributes = True


class ProcessSuggestionRequest(BaseModel):
    """处理建议请求"""
    action: str = Field(..., description="处理动作: accept/reject")
    feedback: Optional[str] = Field(None, description="处理反馈")

    @validator('action')
    def validate_action(cls, v):
        if v not in ['accept', 'reject']:
            raise ValueError('action must be either "accept" or "reject"')
        return v


# 标签相关模型
class CreateTagRequest(BaseModel):
    """创建标签请求"""
    tag_name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    tag_color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="标签颜色(HEX)")
    description: Optional[str] = Field(None, description="标签描述")


class TagResponse(BaseModel):
    """标签响应"""
    id: int
    tag_name: str
    tag_color: Optional[str]
    description: Optional[str]
    usage_count: int
    status: ClassificationStatus
    created_by: int
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 搜索和查询相关模型
class SearchCategoriesRequest(BaseModel):
    """搜索类别请求"""
    dimension_id: Optional[int] = Field(None, description="维度ID")
    category_name: Optional[str] = Field(None, description="类别名称")
    status: Optional[ClassificationStatus] = Field(None, description="状态")
    level: Optional[int] = Field(None, description="层级级别")
    sort_field: str = Field("sort_order", description="排序字段")
    sort_order: str = Field("asc", description="排序方向")
    skip: int = Field(0, ge=0, description="跳过记录数")
    limit: int = Field(100, ge=1, le=1000, description="限制记录数")

    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order must be either "asc" or "desc"')
        return v


class SearchCategoriesResponse(BaseModel):
    """搜索类别响应"""
    categories: List[ClassificationCategoryResponse]
    total: int
    skip: int
    limit: int


# 统计分析相关模型
class ClassificationStatisticsResponse(BaseModel):
    """分类统计响应"""
    dimension_id: int
    category_statistics: List[Dict[str, Any]]
    total_requirements: int


# 批量操作相关模型
class BatchClassifyRequest(BaseModel):
    """批量分类请求"""
    requirement_ids: List[int] = Field(..., description="需求ID列表")
    category_ids: List[int] = Field(..., description="类别ID列表")
    replace_existing: bool = Field(False, description="是否替换现有分类")
    classification_reason: Optional[str] = Field(None, description="分类原因")


class BatchClassifyResponse(BaseModel):
    """批量分类响应"""
    success_count: int
    failed_count: int
    success_requirements: List[int]
    failed_requirements: List[Dict[str, Any]]