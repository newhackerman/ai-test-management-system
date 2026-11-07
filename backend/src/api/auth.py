from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from urllib.parse import urlparse
import logging
import os
import uuid
from pathlib import Path

from ..core.database import get_async_session
from ..services.auth import AuthService
from ..services.user import UserService
from ..schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from ..schemas.user import UserCreate, UserResponse
from ..models.user import User, UserRole
from ..models.role import Role
from ..models.permission import Permission, RolePermission, UserPermission
from ..utils.ip import IPUtils
from ..utils.jwt import jwt_service
from ..utils.auth_rate_limit import (
    check_forgot_password_rate_limit,
    check_reset_password_rate_limit,
    increment_reset_password_failure,
)
from ..utils.error_responses import unauthorized_error, internal_server_error, bad_request_error

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AVATAR_DIR = PROJECT_ROOT / "static" / "avatars"
MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _build_allowed_frontend_origins() -> set:
    """
    构建允许作为重置链接前端的来源白名单（scheme://host[:port]）。

    来源优先级：
      1) FRONTEND_URL / FRONTEND_BASE_URL 环境变量
      2) settings.BACKEND_CORS_ORIGINS（CORS 已允许的来源）
      3) settings.FRONTEND_URL / settings.BASE_URL
      4) 开发兜底 http://127.0.0.1:5173
    """
    from ..core.config import get_settings
    settings = get_settings()
    allowed = set()

    def _add(raw):
        if not raw:
            return
        if isinstance(raw, (list, tuple)):
            for item in raw:
                _add(item)
            return
        try:
            parsed = urlparse(str(raw))
            if parsed.scheme in ("http", "https") and parsed.netloc:
                allowed.add(f"{parsed.scheme}://{parsed.netloc}")
        except Exception:
            pass

    _add(os.getenv("FRONTEND_URL"))
    _add(os.getenv("FRONTEND_BASE_URL"))
    _add(getattr(settings, "BACKEND_CORS_ORIGINS", None))
    _add(getattr(settings, "FRONTEND_URL", None))
    _add(getattr(settings, "BASE_URL", None))
    # 开发兜底，确保本地始终可用
    allowed.add("http://127.0.0.1:5173")
    allowed.add("http://localhost:5173")
    allowed.add("http://127.0.0.1:5174")
    allowed.add("http://localhost:5174")
    allowed.add("http://127.0.0.1:5175")
    allowed.add("http://localhost:5175")
    return allowed


def _get_frontend_base_url(request: Request) -> str:
    """
    生成前端重置密码链接的 base_url。

    安全：仅当请求头 origin/referer 命中预配置的白名单时才采用，
    否则一律回退到配置默认值。这样可以防止攻击者通过伪造
    Origin: https://evil.com 头，把指向钓鱼站点的重置链接投递到受害者邮箱，
    进而窃取重置令牌。

    匹配严格基于 scheme://host[:port]，避免 evil.com.attacker.com 这类绕过。
    """
    allowed = _build_allowed_frontend_origins()

    for header_name in ("origin", "referer"):
        header_value = request.headers.get(header_name)
        if not header_value:
            continue
        try:
            parsed = urlparse(header_value)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin in allowed:
                return origin.rstrip("/")
        except Exception:
            continue

    return (
        os.getenv("FRONTEND_URL")
        or os.getenv("FRONTEND_BASE_URL")
        or "http://127.0.0.1:5173"
    ).rstrip("/")

async def get_auth_service(session: AsyncSession = Depends(get_async_session)) -> AuthService:
    """获取认证服务实例"""
    return AuthService(session)

async def get_user_service(session: AsyncSession = Depends(get_async_session)) -> UserService:
    """获取用户服务实例"""
    return UserService(session)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> Optional[User]:
    """获取当前用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证"
        )
        
    token = credentials.credentials
    payload = jwt_service.verify_token(token)
    
    if not payload or payload.get("type") != "access":
        raise unauthorized_error("无效的访问令牌")
    
    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized_error("无效的用户ID")
    
    # 查找用户
    user_service = UserService(session)
    user = await user_service.get_user_by_id(int(user_id))
    
    if not user:
        raise unauthorized_error("用户不存在")
    
    # 直接返回用户对象
    return user

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """用户登录"""
    client_ip = IPUtils.get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent", "")
    
    try:
        result = await auth_service.login(
            username=request.username,
            password=request.password,
            client_ip=client_ip,
            user_agent=user_agent,
            remember_me=request.remember_me
        )
        
        if not result["success"]:
            raise unauthorized_error(result["message"], "登录验证失败")
        
        return LoginResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="bearer",
            expires_in=3600,  # 1小时
            user=result["user"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {e}")
        raise internal_server_error("登录失败", str(e))

@router.post("/refresh")
async def refresh_token(
    request: dict,
    auth_service: AuthService = Depends(get_auth_service)
):
    """刷新令牌"""
    refresh_token = request.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少刷新令牌"
        )
    
    try:
        result = await auth_service.refresh_token(refresh_token)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result["message"]
            )
        
        return {
            "access_token": result["access_token"],
            "token_type": "bearer",
            "expires_in": 3600
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"令牌刷新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌刷新失败"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """用户登出"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录用户"
        )
    
    try:
        await auth_service.logout(current_user.id)
        return {"message": "登出成功"}
    
    except Exception as e:
        logger.error(f"登出失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )

async def _get_user_roles_permissions(db: AsyncSession, user_id: int):
    """查用户真实的角色与权限。

    角色来自 user_roles；权限是角色权限（role_permissions）与用户直接
    授权（user_permissions）的并集，只取已激活的权限，按 code 去重排序。
    """
    role_rows = await db.execute(
        select(Role.code, Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, Role.is_active == True)  # noqa: E712
        .order_by(Role.code)
    )
    roles = [{"code": code, "name": name} for code, name in role_rows.all()]

    perm_rows = await db.execute(
        select(Permission.code, Permission.name, Permission.module, Permission.action)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id, Permission.is_active == True)  # noqa: E712
    )
    direct_rows = await db.execute(
        select(Permission.code, Permission.name, Permission.module, Permission.action)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(UserPermission.user_id == user_id, Permission.is_active == True)  # noqa: E712
    )
    by_code = {}
    for code, name, module, action in list(perm_rows.all()) + list(direct_rows.all()):
        by_code[code] = {"code": code, "name": name, "module": module, "action": action}
    permissions = [by_code[code] for code in sorted(by_code)]
    return roles, permissions


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取当前用户信息"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录用户"
        )

    roles, permissions = await _get_user_roles_permissions(db, current_user.id)

    return {
        "user_info": {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar,
            "phone": current_user.phone,
            "bio": current_user.bio,
            "gender": current_user.gender.value if current_user.gender else None,
            "birthday": current_user.birthday,
            "location": current_user.location,
            "website": current_user.website,
            "language": current_user.language,
            "timezone": current_user.timezone,
            "theme": current_user.theme,
            "email_notifications": current_user.email_notifications,
            "sms_notifications": current_user.sms_notifications,
            "push_notifications": current_user.push_notifications,
            "mfa_enabled": current_user.mfa_enabled,
            "last_login_at": current_user.last_login_at,
            "last_login_ip": current_user.last_login_ip,
            "password_updated_at": current_user.password_updated_at,
            "failed_login_attempts": current_user.failed_login_attempts,
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        },
        "permissions": permissions,
        "roles": roles
    }

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取用户档案信息（与/me相同，为前端兼容性）"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录用户"
        )

    roles, permissions = await _get_user_roles_permissions(db, current_user.id)

    return {
        "user_info": {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "nickname": current_user.nickname,
            "avatar": current_user.avatar,
            "phone": current_user.phone,
            "bio": current_user.bio,
            "gender": current_user.gender.value if current_user.gender else None,
            "birthday": current_user.birthday,
            "location": current_user.location,
            "website": current_user.website,
            "language": current_user.language,
            "timezone": current_user.timezone,
            "theme": current_user.theme,
            "email_notifications": current_user.email_notifications,
            "sms_notifications": current_user.sms_notifications,
            "push_notifications": current_user.push_notifications,
            "mfa_enabled": current_user.mfa_enabled,
            "last_login_at": current_user.last_login_at,
            "last_login_ip": current_user.last_login_ip,
            "password_updated_at": current_user.password_updated_at,
            "failed_login_attempts": current_user.failed_login_attempts,
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        },
        "permissions": permissions,
        "roles": roles
    }

@router.put("/profile")
async def update_user_profile(
    request: dict,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Update current user's profile and preferences."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录用户")

    allowed_fields = {
        "email",
        "nickname",
        "avatar",
        "phone",
        "bio",
        "gender",
        "birthday",
        "location",
        "website",
        "language",
        "timezone",
        "theme",
        "email_notifications",
        "sms_notifications",
        "push_notifications",
    }
    update_data = {field: request[field] for field in allowed_fields if field in request}

    if "real_name" in request and "nickname" not in update_data:
        update_data["nickname"] = request["real_name"]

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有可更新的字段")

    try:
        updated_user = await user_service.update_user(current_user.id, update_data)
        return await get_user_profile(updated_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"更新个人资料失败: {e}")
        raise internal_server_error("更新个人资料失败", str(e))

@router.post("/profile/avatar")
async def upload_profile_avatar(
    http_request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Upload the current user's avatar and persist the resulting URL."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录用户")

    content_type = (file.content_type or "").lower()
    extension = ALLOWED_AVATAR_TYPES.get(content_type)
    if not extension:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只能上传 JPG、PNG、WEBP 或 GIF 图片")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="头像文件不能为空")
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="头像文件不能超过 5MB")

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"user_{current_user.id}_{uuid.uuid4().hex}{extension}"
    file_path = AVATAR_DIR / filename

    try:
        file_path.write_bytes(content)

        old_avatar = current_user.avatar or ""
        if "/static/avatars/" in old_avatar:
            old_filename = old_avatar.rsplit("/static/avatars/", 1)[-1]
            old_path = AVATAR_DIR / os.path.basename(old_filename)
            if old_path.exists() and old_path != file_path:
                old_path.unlink()

        avatar_url = f"{str(http_request.base_url).rstrip('/')}/static/avatars/{filename}"
        updated_user = await user_service.update_user(current_user.id, {"avatar": avatar_url})
        response = await get_user_profile(updated_user)
        response["success"] = True
        response["avatar_url"] = avatar_url
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"头像上传失败: {e}")
        if file_path.exists():
            file_path.unlink()
        raise internal_server_error("头像上传失败", str(e))

@router.post("/register")
async def register(
    request: RegisterRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """用户注册"""
    client_ip = IPUtils.get_client_ip(http_request)
    
    try:
        result = await auth_service.register(
            username=request.username,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            client_ip=client_ip,
            phone=request.phone
        )
        
        if not result["success"]:
            raise bad_request_error(result["message"], "用户注册失败")
        
        return {
            "message": result["message"],
            "user_id": result["user_id"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise internal_server_error("注册失败", str(e))

@router.post("/forgot-password")
async def forgot_password(
    request: dict,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """忘记密码"""
    email = request.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少邮箱参数"
        )

    # 速率限制：防邮件轰炸与用户枚举侧信道（超限抛 429）
    await check_forgot_password_rate_limit(http_request, email)

    client_ip = IPUtils.get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent", "")

    try:
        result = await auth_service.forgot_password(
            email,
            _get_frontend_base_url(http_request),
            ip_address=client_ip,
            user_agent=user_agent,
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {"message": result["message"]}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"忘记密码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="忘记密码处理失败"
        )

@router.post("/reset-password")
async def reset_password(
    request: dict,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """重置密码"""
    token = request.get("token")
    new_password = request.get("new_password")
    
    if not token or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少必需参数"
        )

    # 速率限制：防对 token 接口暴力/扫描（超限抛 429）
    await check_reset_password_rate_limit(http_request)

    client_ip = IPUtils.get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent", "")

    try:
        result = await auth_service.reset_password(
            token,
            new_password,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        
        if not result["success"]:
            # 计入失败窗口（防枚举/试 token）
            await increment_reset_password_failure(http_request)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {"message": result["message"]}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置密码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置密码失败"
        )

@router.post("/change-password")
async def change_password(
    request: dict,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """修改密码"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录用户"
        )
    
    current_password = request.get("current_password")
    new_password = request.get("new_password")
    
    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少必需参数"
        )
    
    try:
        result = await auth_service.change_password(
            current_user.id, current_password, new_password
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {"message": result["message"]}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败"
        )

@router.post("/verify-email")
async def verify_email(
    request: dict,
    auth_service: AuthService = Depends(get_auth_service)
):
    """验证邮箱"""
    token = request.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少验证令牌"
        )
    
    try:
        result = await auth_service.verify_email(token)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {"message": result["message"]}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"邮箱验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邮箱验证失败"
        )

@router.get("/captcha")
async def get_captcha(
    auth_service: AuthService = Depends(get_auth_service)
):
    """获取验证码"""
    try:
        result = await auth_service.generate_captcha()
        return {
            "key": result["key"],
            "image": result["image"]
        }
    except Exception as e:
        logger.error(f"获取验证码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取验证码失败"
        )
