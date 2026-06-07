"""
基础数据模式
"""
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """API响应基础模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    error_code: Optional[str] = Field(None, description="错误代码")
    timestamp: Optional[str] = Field(None, description="时间戳")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="响应消息")
    data: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(20, description="每页大小")
    
    class Config:
        from_attributes = True


class BaseResponse(BaseModel, Generic[T]):
    """基础响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    
    class Config:
        from_attributes = True
        validate_assignment = True
        use_enum_values = True


class BaseSchema(BaseModel):
    """基础数据模式"""
    
    class Config:
        from_attributes = True
        validate_assignment = True
        use_enum_values = True


class CreateRequest(BaseSchema):
    """创建请求基础模型"""
    pass


class UpdateRequest(BaseSchema):
    """更新请求基础模型"""
    pass


class QueryRequest(BaseSchema):
    """查询请求基础模型"""
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页大小")
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序方向")


class IdResponse(BaseSchema):
    """ID响应模型"""
    id: int = Field(..., description="ID")


class StatusResponse(BaseSchema):
    """状态响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")


class HealthResponse(BaseSchema):
    """健康检查响应模型"""
    status: str = Field(..., description="状态")
    timestamp: str = Field(..., description="时间戳")
    version: Optional[str] = Field(None, description="版本")
    uptime: Optional[int] = Field(None, description="运行时间（秒）")
    dependencies: Optional[Dict[str, Any]] = Field(None, description="依赖服务状态")