"""
AI提示词模板相关的Pydantic模式定义
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class TemplateCategory(str, Enum):
    """模板分类枚举"""
    GENERAL = "GENERAL"
    CODE_GENERATION = "CODE_GENERATION"
    TEST_CASE = "TEST_CASE"
    DOCUMENT_WRITING = "DOCUMENT_WRITING"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    CREATIVE_WRITING = "CREATIVE_WRITING"
    LEARNING_EDUCATION = "LEARNING_EDUCATION"
    PROJECT_MANAGEMENT = "PROJECT_MANAGEMENT"


class TemplateVisibility(str, Enum):
    """模板可见性枚举"""
    PRIVATE = "PRIVATE"
    TEAM = "TEAM"
    PUBLIC = "PUBLIC"


class TemplateVariable(BaseModel):
    """模板变量定义"""
    name: str = Field(..., description="变量名称")
    type: str = Field(..., description="变量类型", pattern="^(string|number|boolean|array|object)$")
    description: str = Field(..., description="变量描述")
    required: bool = Field(True, description="是否必需")
    default_value: Optional[Any] = Field(None, description="默认值")
    validation_rule: Optional[str] = Field(None, description="验证规则")
    example: Optional[Any] = Field(None, description="示例值")


class PromptTemplateCreate(BaseModel):
    """创建提示词模板请求"""
    name: str = Field(..., description="模板名称", min_length=1, max_length=200)
    title: str = Field(..., description="模板标题", min_length=1, max_length=300)
    description: Optional[str] = Field(None, description="模板描述", max_length=1000)
    category: TemplateCategory = Field(..., description="模板分类")
    subcategory: Optional[str] = Field(None, description="子分类", max_length=100)
    
    content: str = Field(..., description="模板内容", min_length=1)
    variables: Optional[List[TemplateVariable]] = Field(None, description="模板变量定义")
    default_values: Optional[Dict[str, Any]] = Field(None, description="默认值")
    example_context: Optional[Dict[str, Any]] = Field(None, description="示例上下文")
    
    supported_providers: Optional[List[str]] = Field(None, description="支持的AI提供商")
    supported_models: Optional[List[str]] = Field(None, description="支持的模型")
    use_cases: Optional[List[str]] = Field(None, description="使用场景")
    tags: Optional[List[str]] = Field(None, description="标签")
    
    visibility: TemplateVisibility = Field(TemplateVisibility.PRIVATE, description="可见性")
    team_id: Optional[int] = Field(None, description="团队ID")
    
    @validator('variables')
    def validate_variables(cls, v):
        if v is None:
            return v
        
        # 检查变量名称唯一性
        names = [var.name for var in v]
        if len(names) != len(set(names)):
            raise ValueError("变量名称必须唯一")
        
        return v
    
    @validator('content')
    def validate_content_variables(cls, v, values):
        """验证模板内容中的变量占位符"""
        import re
        
        # 提取模板中的变量占位符
        placeholders = re.findall(r'\{(\w+)\}', v)
        
        # 如果定义了变量，检查占位符是否都有对应的变量定义
        if 'variables' in values and values['variables']:
            defined_vars = {var.name for var in values['variables']}
            undefined_vars = set(placeholders) - defined_vars
            if undefined_vars:
                raise ValueError(f"模板中包含未定义的变量: {', '.join(undefined_vars)}")
        
        return v


class PromptTemplateUpdate(BaseModel):
    """更新提示词模板请求"""
    title: Optional[str] = Field(None, description="模板标题", min_length=1, max_length=300)
    description: Optional[str] = Field(None, description="模板描述", max_length=1000)
    category: Optional[TemplateCategory] = Field(None, description="模板分类")
    subcategory: Optional[str] = Field(None, description="子分类", max_length=100)
    
    content: Optional[str] = Field(None, description="模板内容", min_length=1)
    variables: Optional[List[TemplateVariable]] = Field(None, description="模板变量定义")
    default_values: Optional[Dict[str, Any]] = Field(None, description="默认值")
    example_context: Optional[Dict[str, Any]] = Field(None, description="示例上下文")
    
    supported_providers: Optional[List[str]] = Field(None, description="支持的AI提供商")
    supported_models: Optional[List[str]] = Field(None, description="支持的模型")
    use_cases: Optional[List[str]] = Field(None, description="使用场景")
    tags: Optional[List[str]] = Field(None, description="标签")
    
    visibility: Optional[TemplateVisibility] = Field(None, description="可见性")
    team_id: Optional[int] = Field(None, description="团队ID")


class PromptTemplateResponse(BaseModel):
    """提示词模板响应"""
    id: int = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    title: str = Field(..., description="模板标题")
    description: Optional[str] = Field(None, description="模板描述")
    category: str = Field(..., description="模板分类")
    subcategory: Optional[str] = Field(None, description="子分类")
    
    content: str = Field(..., description="模板内容")
    variables: Optional[List[TemplateVariable]] = Field(None, description="模板变量定义")
    default_values: Optional[Dict[str, Any]] = Field(None, description="默认值")
    example_context: Optional[Dict[str, Any]] = Field(None, description="示例上下文")
    
    supported_providers: Optional[List[str]] = Field(None, description="支持的AI提供商")
    supported_models: Optional[List[str]] = Field(None, description="支持的模型")
    use_cases: Optional[List[str]] = Field(None, description="使用场景")
    tags: Optional[List[str]] = Field(None, description="标签")
    
    visibility: str = Field(..., description="可见性")
    owner_id: int = Field(..., description="所有者ID")
    team_id: Optional[int] = Field(None, description="团队ID")
    is_featured: bool = Field(..., description="是否精选")
    is_verified: bool = Field(..., description="是否已验证")
    
    version: str = Field(..., description="版本号")
    parent_template_id: Optional[int] = Field(None, description="父模板ID")
    is_latest_version: bool = Field(..., description="是否最新版本")
    
    usage_count: int = Field(..., description="使用次数")
    rating_avg: Optional[float] = Field(None, description="平均评分")
    rating_count: int = Field(..., description="评分次数")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class PromptTemplateListResponse(BaseModel):
    """提示词模板列表响应"""
    templates: List[PromptTemplateResponse] = Field(..., description="模板列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")


class TemplateRenderRequest(BaseModel):
    """模板渲染请求"""
    template_id: int = Field(..., description="模板ID")
    context: Dict[str, Any] = Field(..., description="渲染上下文")
    
    @validator('context')
    def validate_context_keys(cls, v):
        """验证上下文键名格式"""
        import re
        
        for key in v.keys():
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise ValueError(f"上下文键名 '{key}' 格式不正确，只能包含字母、数字和下划线，且不能以数字开头")
        
        return v


class TemplateRenderResponse(BaseModel):
    """模板渲染响应"""
    rendered_content: str = Field(..., description="渲染后的内容")
    template_id: int = Field(..., description="模板ID")
    template_name: str = Field(..., description="模板名称")
    variables_used: List[str] = Field(..., description="使用的变量")
    missing_variables: List[str] = Field(..., description="缺失的变量")


class TemplateUsageCreate(BaseModel):
    """模板使用记录创建请求"""
    template_id: int = Field(..., description="模板ID")
    ai_provider: Optional[str] = Field(None, description="AI服务提供商", max_length=50)
    ai_model: Optional[str] = Field(None, description="AI模型", max_length=100)
    use_case: Optional[str] = Field(None, description="使用场景", max_length=200)
    
    success: bool = Field(True, description="是否成功")
    tokens_used: Optional[int] = Field(None, description="使用的Token数", ge=0)
    response_time: Optional[float] = Field(None, description="响应时间（秒）", ge=0)
    
    user_rating: Optional[int] = Field(None, description="用户评分（1-5）", ge=1, le=5)
    user_feedback: Optional[str] = Field(None, description="用户反馈", max_length=1000)
    
    variable_values: Optional[Dict[str, Any]] = Field(None, description="使用的变量值")


class TemplateUsageResponse(BaseModel):
    """模板使用记录响应"""
    id: int = Field(..., description="记录ID")
    template_id: int = Field(..., description="模板ID")
    user_id: int = Field(..., description="用户ID")
    
    ai_provider: Optional[str] = Field(None, description="AI服务提供商")
    ai_model: Optional[str] = Field(None, description="AI模型")
    use_case: Optional[str] = Field(None, description="使用场景")
    
    success: bool = Field(..., description="是否成功")
    tokens_used: Optional[int] = Field(None, description="使用的Token数")
    response_time: Optional[float] = Field(None, description="响应时间（秒）")
    
    user_rating: Optional[int] = Field(None, description="用户评分")
    user_feedback: Optional[str] = Field(None, description="用户反馈")
    
    variable_values: Optional[Dict[str, Any]] = Field(None, description="使用的变量值")
    
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class TemplateSearchRequest(BaseModel):
    """模板搜索请求"""
    query: Optional[str] = Field(None, description="搜索关键词", max_length=200)
    category: Optional[TemplateCategory] = Field(None, description="分类筛选")
    visibility: Optional[TemplateVisibility] = Field(None, description="可见性筛选")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    owner_id: Optional[int] = Field(None, description="所有者筛选")
    is_featured: Optional[bool] = Field(None, description="是否精选")
    is_verified: Optional[bool] = Field(None, description="是否已验证")
    
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序方向", pattern="^(asc|desc)$")
    
    page: int = Field(1, description="页码", ge=1)
    size: int = Field(20, description="每页大小", ge=1, le=100)
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed_fields = [
            'created_at', 'updated_at', 'name', 'title', 'usage_count', 
            'rating_avg', 'last_used_at'
        ]
        if v not in allowed_fields:
            raise ValueError(f"排序字段必须是以下之一: {', '.join(allowed_fields)}")
        return v


class TemplateStatistics(BaseModel):
    """模板统计信息"""
    total_templates: int = Field(..., description="总模板数")
    public_templates: int = Field(..., description="公开模板数")
    private_templates: int = Field(..., description="私有模板数")
    featured_templates: int = Field(..., description="精选模板数")
    
    category_distribution: Dict[str, int] = Field(..., description="分类分布")
    usage_statistics: Dict[str, int] = Field(..., description="使用统计")
    
    top_templates: List[PromptTemplateResponse] = Field(..., description="热门模板")
    recent_templates: List[PromptTemplateResponse] = Field(..., description="最新模板")