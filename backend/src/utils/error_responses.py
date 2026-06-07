"""
统一错误响应处理器
"""
from fastapi import HTTPException
from typing import Optional, Dict, Any


class APIError(HTTPException):
    """统一API错误类"""
    
    def __init__(
        self,
        status_code: int,
        message: str,
        detail: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        self.error_code = error_code
        
        # 构造标准错误响应格式 - 兼容前端期望
        if detail:
            # 如果有详细信息，使用简单格式以兼容前端
            content = {
                "message": message,
                "detail": detail,
                "code": status_code
            }
        else:
            # 否则使用完整格式
            content = {
                "code": status_code,
                "message": message
            }
            
        if error_code:
            content["error_code"] = error_code
        
        super().__init__(status_code=status_code, detail=content)


# 常用错误响应
def unauthorized_error(message: str = "未授权访问", detail: Optional[str] = None) -> APIError:
    """401 未授权错误"""
    return APIError(
        status_code=401,
        message=message,
        detail=detail,
        error_code="UNAUTHORIZED"
    )


def forbidden_error(message: str = "权限不足", detail: Optional[str] = None) -> APIError:
    """403 禁止访问错误"""
    return APIError(
        status_code=403,
        message=message,
        detail=detail,
        error_code="FORBIDDEN"
    )


def not_found_error(message: str = "资源不存在", detail: Optional[str] = None) -> APIError:
    """404 资源不存在错误"""
    return APIError(
        status_code=404,
        message=message,
        detail=detail,
        error_code="NOT_FOUND"
    )


def validation_error(message: str = "请求参数验证失败", detail: Optional[str] = None) -> APIError:
    """422 验证错误"""
    return APIError(
        status_code=422,
        message=message,
        detail=detail,
        error_code="VALIDATION_ERROR"
    )


def internal_server_error(message: str = "服务器内部错误", detail: Optional[str] = None) -> APIError:
    """500 服务器内部错误"""
    return APIError(
        status_code=500,
        message=message,
        detail=detail,
        error_code="INTERNAL_SERVER_ERROR"
    )


def bad_request_error(message: str = "请求参数错误", detail: Optional[str] = None) -> APIError:
    """400 请求错误"""
    return APIError(
        status_code=400,
        message=message,
        detail=detail,
        error_code="BAD_REQUEST"
    )


def conflict_error(message: str = "资源冲突", detail: Optional[str] = None) -> APIError:
    """409 冲突错误"""
    return APIError(
        status_code=409,
        message=message,
        detail=detail,
        error_code="CONFLICT"
    )