"""
配置管理模式定义
"""
from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from enum import Enum
from datetime import datetime

# 定义泛型类型变量
T = TypeVar('T')


class ConfigType(str, Enum):
    """配置类型枚举"""
    STRING = "STRING"
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"
    ARRAY = "ARRAY"
    EMAIL = "EMAIL"
    URL = "URL"
    ENUM = "ENUM"
    PASSWORD = "PASSWORD"
    FILE = "FILE"
    COLOR = "COLOR"
    DATE = "DATE"
    TIME = "TIME"


class Environment(str, Enum):
    """环境类型枚举"""
    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"
    DEMO = "demo"
    PERF = "perf"


class ConfigCreateRequest(BaseModel):
    """配置创建请求"""
    config_key: str = Field(..., min_length=1, max_length=200, description="配置键名")
    config_value: str = Field(..., description="配置值")
    config_type: ConfigType = Field(default=ConfigType.STRING, description="配置类型")
    group_id: Optional[int] = Field(None, description="分组ID")
    environment: Environment = Field(default=Environment.PROD, description="环境")
    description: Optional[str] = Field(None, max_length=1000, description="配置描述")
    default_value: Optional[str] = Field(None, description="默认值")
    example_value: Optional[str] = Field(None, description="示例值")
    validation_rule: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    is_core: bool = Field(default=False, description="是否核心配置")
    is_enabled: bool = Field(default=True, description="是否启用")
    is_encrypted: bool = Field(default=False, description="是否加密存储")
    is_required: bool = Field(default=False, description="是否必填")
    tags: Optional[List[str]] = Field(None, description="配置标签")
    sort_order: Optional[int] = Field(default=0, description="排序序号")
    
    @validator('config_key')
    def validate_config_key(cls, v):
        """验证配置键格式"""
        if not v or not v.strip():
            raise ValueError('配置键不能为空')
        
        # 配置键只能包含字母、数字、点、下划线、中划线
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('配置键只能包含字母、数字、点、下划线、中划线')
        
        return v.strip()
    
    @validator('config_value')
    def validate_config_value(cls, v):
        """验证配置值"""
        if v is None:
            raise ValueError('配置值不能为空')
        return str(v)


class ConfigUpdateRequest(BaseModel):
    """配置更新请求"""
    config_value: Optional[str] = Field(None, description="配置值")
    config_type: Optional[ConfigType] = Field(None, description="配置类型")
    description: Optional[str] = Field(None, max_length=1000, description="配置描述")
    default_value: Optional[str] = Field(None, description="默认值")
    example_value: Optional[str] = Field(None, description="示例值")
    validation_rule: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    is_core: Optional[bool] = Field(None, description="是否核心配置")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    is_encrypted: Optional[bool] = Field(None, description="是否加密存储")
    is_required: Optional[bool] = Field(None, description="是否必填")
    tags: Optional[List[str]] = Field(None, description="配置标签")
    sort_order: Optional[int] = Field(None, description="排序序号")
    change_reason: Optional[str] = Field(None, max_length=500, description="变更原因")


class ConfigResponse(BaseModel):
    """配置响应"""
    id: int
    config_key: str
    config_value: str
    config_type: str
    group_id: Optional[int]
    environment: str
    description: Optional[str]
    default_value: Optional[str]
    example_value: Optional[str]
    validation_rule: Optional[Dict[str, Any]]
    is_core: bool
    is_enabled: bool
    is_encrypted: bool
    is_required: bool
    tags: Optional[List[str]]
    sort_order: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[int]
    updated_by: Optional[int]
    
    class Config:
        from_attributes = True


class ConfigListResponse(BaseModel):
    """配置列表响应"""
    items: List[ConfigResponse]
    total: int
    page: int
    size: int
    pages: int


class ConfigSearchRequest(BaseModel):
    """配置搜索请求"""
    environment: Optional[Environment] = Field(default=Environment.PROD, description="环境")
    group_id: Optional[int] = Field(None, description="分组ID")
    search: Optional[str] = Field(None, min_length=1, max_length=100, description="搜索关键词")
    config_type: Optional[ConfigType] = Field(None, description="配置类型")
    is_core: Optional[bool] = Field(None, description="是否核心配置")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    tags: Optional[List[str]] = Field(None, description="标签过滤")
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=20, ge=1, le=100, description="页大小")
    sort_field: Optional[str] = Field(default="created_at", description="排序字段")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$", description="排序方向")


class ConfigGroupCreateRequest(BaseModel):
    """配置分组创建请求"""
    group_name: str = Field(..., min_length=1, max_length=100, description="分组名称")
    group_code: str = Field(..., min_length=1, max_length=100, description="分组代码")
    parent_id: int = Field(default=0, description="父分组ID")
    description: Optional[str] = Field(None, max_length=500, description="分组描述")
    icon: Optional[str] = Field(None, max_length=100, description="分组图标")
    color: Optional[str] = Field(None, max_length=20, description="分组颜色")
    sort_order: int = Field(default=0, description="排序序号")
    
    @validator('group_code')
    def validate_group_code(cls, v):
        """验证分组代码格式"""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('分组代码只能包含字母、数字、下划线、中划线')
        return v.lower()


class ConfigGroupUpdateRequest(BaseModel):
    """配置分组更新请求"""
    group_name: Optional[str] = Field(None, min_length=1, max_length=100, description="分组名称")
    description: Optional[str] = Field(None, max_length=500, description="分组描述")
    icon: Optional[str] = Field(None, max_length=100, description="分组图标")
    color: Optional[str] = Field(None, max_length=20, description="分组颜色")
    sort_order: Optional[int] = Field(None, description="排序序号")
    is_enabled: Optional[bool] = Field(None, description="是否启用")


class ConfigGroupResponse(BaseModel):
    """配置分组响应"""
    id: int
    group_name: str
    group_code: str
    parent_id: int
    level: int
    path: Optional[str]
    sort_order: int
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    is_system: bool
    is_enabled: bool
    config_count: Optional[int] = Field(None, description="分组下配置数量")
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ConfigHistoryResponse(BaseModel):
    """配置历史响应"""
    id: int
    config_id: int
    config_key: str
    environment: str
    old_value: Optional[str]
    new_value: Optional[str]
    change_type: str
    change_reason: Optional[str]
    change_summary: Optional[str]
    operator_id: Optional[int]
    operator_ip: Optional[str]
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ConfigAuditCreateRequest(BaseModel):
    """配置审核创建请求"""
    config_key: str = Field(..., description="配置键名")
    environment: Environment = Field(default=Environment.PROD, description="环境")
    old_value: Optional[str] = Field(None, description="变更前值")
    new_value: str = Field(..., description="变更后值")
    change_type: str = Field(..., pattern="^(CREATE|UPDATE|DELETE)$", description="变更类型")
    apply_reason: str = Field(..., min_length=1, max_length=1000, description="申请原因")
    priority: Optional[str] = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|URGENT)$", description="优先级")
    estimated_downtime: Optional[int] = Field(None, ge=0, description="预估停机时间(分钟)")
    rollback_plan: Optional[str] = Field(None, max_length=2000, description="回滚计划")


class ConfigAuditResponse(BaseModel):
    """配置审核响应"""
    id: int
    audit_code: str
    config_id: Optional[int]
    config_key: str
    environment: str
    old_value: Optional[str]
    new_value: Optional[str]
    change_type: str
    audit_status: str
    priority: Optional[str]
    apply_user_id: int
    audit_user_id: Optional[int]
    apply_reason: Optional[str]
    audit_reason: Optional[str]
    risk_level: Optional[str]
    estimated_downtime: Optional[int]
    rollback_plan: Optional[str]
    applied_at: Optional[datetime]
    audited_at: Optional[datetime]
    executed_at: Optional[datetime]
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ConfigBatchUpdateRequest(BaseModel):
    """配置批量更新请求"""
    updates: List[Dict[str, Any]] = Field(..., min_length=1, max_length=100, description="更新列表")
    
    @validator('updates')
    def validate_updates(cls, v):
        """验证更新列表格式"""
        for update in v:
            if 'config_key' not in update:
                raise ValueError('每个更新项必须包含config_key')
        return v


class ConfigExportRequest(BaseModel):
    """配置导出请求"""
    environment: Optional[Environment] = Field(default=Environment.PROD, description="环境")
    group_ids: Optional[List[int]] = Field(None, description="分组ID列表")
    config_keys: Optional[List[str]] = Field(None, description="配置键列表")
    export_format: str = Field(default="json", pattern="^(json|yaml|env|excel)$", description="导出格式")
    include_sensitive: bool = Field(default=False, description="是否包含敏感配置")
    mask_sensitive: bool = Field(default=True, description="是否遮盖敏感配置值")


class ConfigImportRequest(BaseModel):
    """配置导入请求"""
    environment: Environment = Field(default=Environment.PROD, description="目标环境")
    import_format: str = Field(..., pattern="^(json|yaml|env|excel)$", description="导入格式")
    content: str = Field(..., min_length=1, description="导入内容")
    overwrite_existing: bool = Field(default=False, description="是否覆盖已存在的配置")
    dry_run: bool = Field(default=False, description="是否预演（不实际导入）")


class ConfigValidationRequest(BaseModel):
    """配置验证请求"""
    config_value: str = Field(..., description="配置值")
    config_type: ConfigType = Field(..., description="配置类型")
    validation_rule: Optional[Dict[str, Any]] = Field(None, description="验证规则")


class ConfigValidationResponse(BaseModel):
    """配置验证响应"""
    is_valid: bool
    error_message: Optional[str]
    converted_value: Optional[Any]
    suggestions: Optional[List[str]]


class ApiResponse(BaseModel, Generic[T]):
    """通用API响应"""
    success: bool
    message: str
    data: Optional[T] = None
    error_code: Optional[str] = None
    
    class Config:
        # 允许任意类型的data字段
        arbitrary_types_allowed = True