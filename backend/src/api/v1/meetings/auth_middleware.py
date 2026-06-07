"""
会议模块JWT认证中间件

本模块提供会议相关API的JWT认证中间件，包括：
- JWT令牌验证和解析
- 用户会话管理
- SSO单点登录支持
- 认证状态缓存
"""
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import AuthenticationError, ValidationError
from ....services.auth import AuthService
from ....services.user import UserService
from ....models.user import User
from ....utils.jwt import jwt_service
from ....utils.redis_client import get_redis_client
from ....api.auth import get_current_user

logger = logging.getLogger(__name__)

# JWT Bearer认证
security = HTTPBearer(auto_error=False)

# 认证缓存配置
AUTH_CACHE_CONFIG = {
    "user_session_ttl": 3600,  # 用户会话缓存1小时
    "token_blacklist_ttl": 86400,  # 令牌黑名单缓存24小时
    "sso_session_ttl": 7200,  # SSO会话缓存2小时
}


class MeetingAuthMiddleware:
    """会议认证中间件"""
    
    def __init__(self):
        self.excluded_paths = {
            "/meetings/join/",  # 公开会议加入链接
            "/meetings/public/",  # 公开会议信息
            "/health",  # 健康检查
            "/docs",  # API文档
            "/openapi.json"  # OpenAPI规范
        }
    
    async def __call__(self, request: Request, call_next):
        """中间件处理函数"""
        # 检查是否为排除路径
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # 验证JWT令牌
        try:
            await self.verify_jwt_token(request)
        except HTTPException as e:
            # 认证失败，返回401错误
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        
        # 继续处理请求
        return await call_next(request)
    
    async def verify_jwt_token(self, request: Request):
        """验证JWT令牌"""
        # 获取Authorization头
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证令牌"
            )
        
        token = auth_header.split(" ")[1]
        
        # 验证令牌
        try:
            payload = jwt_service.verify_token(token)
            if not payload or payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效的访问令牌"
                )
            
            # 检查令牌是否在黑名单中
            redis_client = await get_redis_client()
            blacklist_key = f"token_blacklist:{token}"
            is_blacklisted = await redis_client.get(blacklist_key)
            
            if is_blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌已失效"
                )
            
            # 将用户信息添加到请求状态
            request.state.user_id = payload.get("sub")
            request.state.token_payload = payload
            
        except Exception as e:
            logger.warning(f"JWT令牌验证失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌验证失败"
            )


async def get_meeting_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_async_session),
    redis_client = Depends(get_redis_client)
) -> User:
    """
    获取当前用户（会议模块专用）
    
    Args:
        credentials: JWT认证凭据
        session: 数据库会话
        redis_client: Redis客户端
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 认证失败时抛出401错误
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要认证"
        )
    
    token = credentials.credentials
    
    try:
        # 验证JWT令牌
        payload = jwt_service.verify_token(token)
        
        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问令牌"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的用户ID"
            )
        
        # 检查令牌黑名单
        blacklist_key = f"token_blacklist:{token}"
        is_blacklisted = await redis_client.get(blacklist_key)
        
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已失效"
            )
        
        # 尝试从缓存获取用户信息
        cache_key = f"user_session:{user_id}"
        cached_user = await redis_client.get(cache_key)
        
        if cached_user:
            # 从缓存反序列化用户信息
            import json
            user_data = json.loads(cached_user)
            
            # 创建用户对象（简化版本，只包含基本信息）
            user = User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                nickname=user_data.get("nickname"),
                avatar=user_data.get("avatar"),
                is_active=user_data.get("is_active", True),
                is_superuser=user_data.get("is_superuser", False)
            )
            
            return user
        
        # 从数据库查询用户
        user_service = UserService(session)
        user = await user_service.get_user_by_id(int(user_id))
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账户已禁用"
            )
        
        # 缓存用户信息
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser
        }
        
        await redis_client.setex(
            cache_key,
            AUTH_CACHE_CONFIG["user_session_ttl"],
            json.dumps(user_data)
        )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败"
        )


async def validate_meeting_token(
    meeting_code: str,
    token: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    验证会议访问令牌
    
    Args:
        meeting_code: 会议编码
        token: 会议访问令牌
        session: 数据库会话
        
    Returns:
        Dict: 验证结果
    """
    try:
        # 如果没有提供令牌，检查是否为公开会议
        if not token:
            # TODO: 查询会议是否为公开会议
            # meeting_service = MeetingService(session)
            # meeting = await meeting_service.get_meeting_by_code(meeting_code)
            # if meeting and meeting.is_public:
            #     return {"valid": True, "meeting_id": meeting.id, "requires_auth": False}
            
            return {"valid": False, "message": "需要会议访问令牌"}
        
        # 验证会议令牌
        try:
            payload = jwt_service.verify_token(token)
            
            if not payload or payload.get("type") != "meeting_access":
                return {"valid": False, "message": "无效的会议令牌"}
            
            meeting_id = payload.get("meeting_id")
            allowed_meeting_code = payload.get("meeting_code")
            
            if allowed_meeting_code != meeting_code:
                return {"valid": False, "message": "令牌与会议不匹配"}
            
            return {
                "valid": True,
                "meeting_id": meeting_id,
                "meeting_code": meeting_code,
                "requires_auth": True
            }
            
        except Exception as e:
            logger.warning(f"会议令牌验证失败: {e}")
            return {"valid": False, "message": "令牌验证失败"}
        
    except Exception as e:
        logger.error(f"验证会议令牌失败: {e}")
        return {"valid": False, "message": "验证失败"}


async def generate_meeting_access_token(
    meeting_id: int,
    meeting_code: str,
    user_id: int,
    expires_in: int = 3600
) -> str:
    """
    生成会议访问令牌
    
    Args:
        meeting_id: 会议ID
        meeting_code: 会议编码
        user_id: 用户ID
        expires_in: 过期时间（秒）
        
    Returns:
        str: 会议访问令牌
    """
    try:
        payload = {
            "type": "meeting_access",
            "meeting_id": meeting_id,
            "meeting_code": meeting_code,
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in)
        }
        
        token = jwt_service.create_token(payload)
        return token
        
    except Exception as e:
        logger.error(f"生成会议访问令牌失败: {e}")
        raise


async def revoke_user_tokens(
    user_id: int,
    redis_client = Depends(get_redis_client)
):
    """
    撤销用户的所有令牌
    
    Args:
        user_id: 用户ID
        redis_client: Redis客户端
    """
    try:
        # 清除用户会话缓存
        cache_key = f"user_session:{user_id}"
        await redis_client.delete(cache_key)
        
        # TODO: 将用户的所有活跃令牌加入黑名单
        # 这需要维护一个用户令牌映射表
        
        logger.info(f"已撤销用户 {user_id} 的所有令牌")
        
    except Exception as e:
        logger.error(f"撤销用户令牌失败: {e}")


async def check_sso_session(
    sso_token: str,
    redis_client = Depends(get_redis_client)
) -> Optional[Dict[str, Any]]:
    """
    检查SSO会话
    
    Args:
        sso_token: SSO令牌
        redis_client: Redis客户端
        
    Returns:
        Optional[Dict]: SSO会话信息
    """
    try:
        sso_key = f"sso_session:{sso_token}"
        session_data = await redis_client.get(sso_key)
        
        if session_data:
            import json
            return json.loads(session_data)
        
        return None
        
    except Exception as e:
        logger.error(f"检查SSO会话失败: {e}")
        return None


async def create_sso_session(
    user_id: int,
    sso_provider: str,
    sso_user_id: str,
    redis_client = Depends(get_redis_client)
) -> str:
    """
    创建SSO会话
    
    Args:
        user_id: 用户ID
        sso_provider: SSO提供商
        sso_user_id: SSO用户ID
        redis_client: Redis客户端
        
    Returns:
        str: SSO令牌
    """
    try:
        import uuid
        sso_token = str(uuid.uuid4())
        
        session_data = {
            "user_id": user_id,
            "sso_provider": sso_provider,
            "sso_user_id": sso_user_id,
            "created_at": datetime.utcnow().isoformat()
        }
        
        sso_key = f"sso_session:{sso_token}"
        await redis_client.setex(
            sso_key,
            AUTH_CACHE_CONFIG["sso_session_ttl"],
            json.dumps(session_data)
        )
        
        return sso_token
        
    except Exception as e:
        logger.error(f"创建SSO会话失败: {e}")
        raise


# 导出认证依赖
def get_authenticated_user():
    """获取认证用户的依赖"""
    return Depends(get_meeting_current_user)


def require_authentication():
    """要求认证的依赖"""
    async def _require_auth(user: User = Depends(get_meeting_current_user)):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要认证"
            )
        return user
    
    return Depends(_require_auth)


def optional_authentication():
    """可选认证的依赖"""
    async def _optional_auth(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        session: AsyncSession = Depends(get_async_session)
    ) -> Optional[User]:
        if not credentials:
            return None
        
        try:
            return await get_meeting_current_user(credentials, session)
        except HTTPException:
            return None
    
    return Depends(_optional_auth)