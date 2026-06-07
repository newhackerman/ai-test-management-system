"""
会议API安全控制模块

本模块提供会议相关API的安全控制功能，包括：
- JWT认证中间件集成
- 会议权限验证装饰器
- API访问频率限制
- 敏感操作审计日志记录
"""
import logging
import time
from functools import wraps
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import PermissionError, ValidationError
from ....services.meeting_permission_service import MeetingPermissionService, get_meeting_permission_service
from ....services.audit_service import AuditService, get_audit_service
from ....api.auth import get_current_user
from ....models.user import User
from ....utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# JWT Bearer认证
security = HTTPBearer()

# 速率限制配置
RATE_LIMIT_CONFIG = {
    "default": {"requests": 100, "window": 60},  # 默认：60秒内100次请求
    "create_meeting": {"requests": 10, "window": 60},  # 创建会议：60秒内10次
    "join_meeting": {"requests": 20, "window": 60},  # 加入会议：60秒内20次
    "upload_file": {"requests": 5, "window": 60},  # 文件上传：60秒内5次
    "start_recording": {"requests": 3, "window": 60},  # 开始录制：60秒内3次
    "ai_analysis": {"requests": 5, "window": 300},  # AI分析：5分钟内5次
}


class MeetingPermission:
    """会议权限枚举"""
    VIEW_MEETING = "view_meeting"
    CREATE_MEETING = "create_meeting"
    UPDATE_MEETING = "update_meeting"
    DELETE_MEETING = "delete_meeting"
    JOIN_MEETING = "join_meeting"
    MANAGE_PARTICIPANTS = "manage_participants"
    CONTROL_MEETING = "control_meeting"
    SHARE_SCREEN = "share_screen"
    USE_CHAT = "use_chat"
    UPLOAD_FILES = "upload_files"
    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    VIEW_RECORDINGS = "view_recordings"
    DELETE_RECORDINGS = "delete_recordings"
    GENERATE_AI_ANALYSIS = "generate_ai_analysis"
    VIEW_AI_ANALYSIS = "view_ai_analysis"


async def check_rate_limit(
    request: Request,
    user_id: int,
    action: str = "default",
    redis_client = Depends(get_redis_client)
) -> bool:
    """
    检查API访问频率限制
    
    Args:
        request: FastAPI请求对象
        user_id: 用户ID
        action: 操作类型
        redis_client: Redis客户端
        
    Returns:
        bool: 是否通过频率限制
        
    Raises:
        HTTPException: 超出频率限制时抛出429错误
    """
    try:
        # 获取配置
        config = RATE_LIMIT_CONFIG.get(action, RATE_LIMIT_CONFIG["default"])
        max_requests = config["requests"]
        window_seconds = config["window"]
        
        # 生成Redis键
        client_ip = request.client.host if request.client else "unknown"
        rate_limit_key = f"rate_limit:{action}:{user_id}:{client_ip}"
        
        # 获取当前计数
        current_count = await redis_client.get(rate_limit_key)
        
        if current_count is None:
            # 首次请求，设置计数器
            await redis_client.setex(rate_limit_key, window_seconds, 1)
            return True
        
        current_count = int(current_count)
        
        if current_count >= max_requests:
            # 超出限制
            logger.warning(f"用户 {user_id} 超出频率限制: {action}, IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请在 {window_seconds} 秒后重试"
            )
        
        # 增加计数
        await redis_client.incr(rate_limit_key)
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查频率限制失败: {e}")
        # 频率限制检查失败时，允许请求通过
        return True


def require_meeting_permission(permission: str):
    """
    会议权限验证装饰器
    
    Args:
        permission: 所需权限
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取参数
            meeting_id = kwargs.get('meeting_id')
            current_user = kwargs.get('current_user')
            permission_service = kwargs.get('permission_service')
            
            if not all([meeting_id, current_user, permission_service]):
                # 如果参数不完整，尝试从依赖注入获取
                for arg in args:
                    if hasattr(arg, 'id') and hasattr(arg, 'username'):
                        current_user = arg
                        break
                
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="用户认证失败"
                    )
            
            try:
                # 检查权限
                has_permission = await permission_service.check_meeting_permission(
                    user_id=current_user.id,
                    meeting_id=meeting_id,
                    permission=permission
                )
                
                if not has_permission:
                    logger.warning(f"用户 {current_user.id} 缺少权限 {permission} 访问会议 {meeting_id}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"缺少权限: {permission}"
                    )
                
                # 权限检查通过，执行原函数
                return await func(*args, **kwargs)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"权限检查失败: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="权限检查失败"
                )
        
        return wrapper
    return decorator


async def log_meeting_operation(
    user_id: int,
    meeting_id: Optional[int],
    operation: str,
    details: Dict[str, Any],
    request: Request,
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    记录会议操作审计日志
    
    Args:
        user_id: 用户ID
        meeting_id: 会议ID
        operation: 操作类型
        details: 操作详情
        request: 请求对象
        audit_service: 审计服务
    """
    try:
        # 构建审计日志数据
        audit_data = {
            "user_id": user_id,
            "meeting_id": meeting_id,
            "operation": operation,
            "details": details,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "timestamp": datetime.utcnow(),
            "request_id": getattr(request.state, 'request_id', None)
        }
        
        # 记录审计日志
        await audit_service.log_meeting_operation(audit_data)
        
    except Exception as e:
        logger.error(f"记录审计日志失败: {e}")
        # 审计日志记录失败不应影响业务流程


def audit_meeting_operation(operation: str):
    """
    会议操作审计装饰器
    
    Args:
        operation: 操作类型
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取参数
            meeting_id = kwargs.get('meeting_id')
            current_user = kwargs.get('current_user')
            request = kwargs.get('request')
            
            # 执行原函数
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                
                # 记录成功操作
                if current_user and request:
                    await log_meeting_operation(
                        user_id=current_user.id,
                        meeting_id=meeting_id,
                        operation=operation,
                        details={
                            "status": "success",
                            "duration_ms": int((time.time() - start_time) * 1000),
                            "result_type": type(result).__name__
                        },
                        request=request
                    )
                
                return result
                
            except Exception as e:
                # 记录失败操作
                if current_user and request:
                    await log_meeting_operation(
                        user_id=current_user.id,
                        meeting_id=meeting_id,
                        operation=operation,
                        details={
                            "status": "failed",
                            "error": str(e),
                            "duration_ms": int((time.time() - start_time) * 1000)
                        },
                        request=request
                    )
                
                raise
        
        return wrapper
    return decorator


async def validate_meeting_access(
    meeting_id: int,
    user_id: int,
    permission_service: MeetingPermissionService
) -> bool:
    """
    验证用户是否有访问会议的基本权限
    
    Args:
        meeting_id: 会议ID
        user_id: 用户ID
        permission_service: 权限服务
        
    Returns:
        bool: 是否有访问权限
    """
    try:
        # 检查基本访问权限
        has_access = await permission_service.check_meeting_access(user_id, meeting_id)
        return has_access
        
    except Exception as e:
        logger.error(f"验证会议访问权限失败: {e}")
        return False


async def check_meeting_security(
    meeting_id: int,
    user_id: int,
    password: Optional[str] = None,
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
) -> Dict[str, Any]:
    """
    检查会议安全设置
    
    Args:
        meeting_id: 会议ID
        user_id: 用户ID
        password: 会议密码
        permission_service: 权限服务
        
    Returns:
        Dict: 安全检查结果
    """
    try:
        # 获取会议安全设置
        security_settings = await permission_service.get_meeting_security_settings(meeting_id)
        
        result = {
            "access_granted": False,
            "requires_password": security_settings.get("is_password_protected", False),
            "requires_approval": security_settings.get("is_waiting_room_enabled", False),
            "is_locked": security_settings.get("is_locked", False),
            "message": ""
        }
        
        # 检查会议是否锁定
        if result["is_locked"]:
            result["message"] = "会议已锁定，无法加入"
            return result
        
        # 检查密码
        if result["requires_password"]:
            if not password:
                result["message"] = "需要输入会议密码"
                return result
            
            password_valid = await permission_service.verify_meeting_password(meeting_id, password)
            if not password_valid:
                result["message"] = "会议密码错误"
                return result
        
        # 检查基本访问权限
        has_access = await validate_meeting_access(meeting_id, user_id, permission_service)
        if not has_access:
            result["message"] = "无权限访问此会议"
            return result
        
        result["access_granted"] = True
        result["message"] = "安全检查通过"
        return result
        
    except Exception as e:
        logger.error(f"会议安全检查失败: {e}")
        return {
            "access_granted": False,
            "requires_password": False,
            "requires_approval": False,
            "is_locked": False,
            "message": "安全检查失败"
        }


class MeetingSecurityMiddleware:
    """会议安全中间件"""
    
    def __init__(self):
        self.sensitive_operations = {
            "create_meeting",
            "delete_meeting",
            "start_recording",
            "stop_recording",
            "kick_participant",
            "end_meeting"
        }
    
    async def __call__(self, request: Request, call_next):
        """中间件处理函数"""
        # 为请求添加唯一ID
        request.state.request_id = f"req_{int(time.time() * 1000)}"
        
        # 记录请求开始时间
        start_time = time.time()
        
        try:
            # 执行请求
            response = await call_next(request)
            
            # 记录请求完成时间
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request.state.request_id
            
            return response
            
        except Exception as e:
            logger.error(f"请求处理异常: {e}")
            raise


# 导出常用的权限检查函数
async def require_meeting_view_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
):
    """要求会议查看权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission=MeetingPermission.VIEW_MEETING
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此会议"
        )
    
    return True


async def require_meeting_manage_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
):
    """要求会议管理权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission=MeetingPermission.UPDATE_MEETING
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限管理此会议"
        )
    
    return True


async def require_recording_permission(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    permission_service: MeetingPermissionService = Depends(get_meeting_permission_service)
):
    """要求录制权限"""
    has_permission = await permission_service.check_meeting_permission(
        user_id=current_user.id,
        meeting_id=meeting_id,
        permission=MeetingPermission.START_RECORDING
    )
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限录制此会议"
        )
    
    return True