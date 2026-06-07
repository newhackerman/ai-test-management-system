"""
会议模块SSO单点登录集成

本模块提供会议相关的SSO单点登录集成功能，包括：
- SAML 2.0 集成
- OAuth 2.0 集成
- OIDC (OpenID Connect) 集成
- 企业级SSO提供商集成
"""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs

from fastapi import HTTPException, status, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import AuthenticationError, ValidationError
from ....services.auth import AuthService
from ....services.user import UserService
from ....models.user import User
from ....utils.jwt import jwt_service
from ....utils.redis_client import get_redis_client
from .auth_middleware import create_sso_session, check_sso_session

logger = logging.getLogger(__name__)

# SSO提供商配置
SSO_PROVIDERS = {
    "microsoft": {
        "name": "Microsoft Azure AD",
        "auth_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        "user_info_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": ["openid", "profile", "email", "User.Read"]
    },
    "google": {
        "name": "Google Workspace",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": ["openid", "profile", "email"]
    },
    "okta": {
        "name": "Okta",
        "auth_url": "https://{domain}/oauth2/default/v1/authorize",
        "token_url": "https://{domain}/oauth2/default/v1/token",
        "user_info_url": "https://{domain}/oauth2/default/v1/userinfo",
        "scopes": ["openid", "profile", "email"]
    },
    "auth0": {
        "name": "Auth0",
        "auth_url": "https://{domain}/authorize",
        "token_url": "https://{domain}/oauth/token",
        "user_info_url": "https://{domain}/userinfo",
        "scopes": ["openid", "profile", "email"]
    }
}


class SSOIntegration:
    """SSO集成服务"""
    
    def __init__(self):
        self.redis_client = None
        self.session = None
    
    async def initialize(self, redis_client, session: AsyncSession):
        """初始化SSO服务"""
        self.redis_client = redis_client
        self.session = session
    
    async def get_sso_auth_url(
        self,
        provider: str,
        meeting_code: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取SSO认证URL
        
        Args:
            provider: SSO提供商
            meeting_code: 会议编码（可选）
            redirect_uri: 重定向URI（可选）
            
        Returns:
            Dict: 包含认证URL和状态信息
        """
        try:
            if provider not in SSO_PROVIDERS:
                raise ValidationError(f"不支持的SSO提供商: {provider}")
            
            provider_config = SSO_PROVIDERS[provider]
            
            # 生成状态参数
            import uuid
            state = str(uuid.uuid4())
            
            # 构建认证参数
            auth_params = {
                "client_id": self._get_client_id(provider),
                "response_type": "code",
                "scope": " ".join(provider_config["scopes"]),
                "state": state,
                "redirect_uri": redirect_uri or self._get_default_redirect_uri(provider)
            }
            
            # 如果有会议编码，添加到状态中
            state_data = {
                "provider": provider,
                "meeting_code": meeting_code,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 缓存状态信息
            state_key = f"sso_state:{state}"
            await self.redis_client.setex(
                state_key,
                600,  # 10分钟过期
                json.dumps(state_data)
            )
            
            # 构建认证URL
            auth_url = provider_config["auth_url"].format(
                tenant_id=self._get_tenant_id(provider),
                domain=self._get_domain(provider)
            )
            
            full_auth_url = f"{auth_url}?{urlencode(auth_params)}"
            
            return {
                "auth_url": full_auth_url,
                "state": state,
                "provider": provider,
                "expires_in": 600
            }
            
        except Exception as e:
            logger.error(f"获取SSO认证URL失败: {e}")
            raise
    
    async def handle_sso_callback(
        self,
        provider: str,
        code: str,
        state: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理SSO回调
        
        Args:
            provider: SSO提供商
            code: 授权码
            state: 状态参数
            error: 错误信息
            
        Returns:
            Dict: 认证结果
        """
        try:
            if error:
                raise AuthenticationError(f"SSO认证失败: {error}")
            
            # 验证状态参数
            state_key = f"sso_state:{state}"
            state_data_str = await self.redis_client.get(state_key)
            
            if not state_data_str:
                raise AuthenticationError("无效的状态参数")
            
            state_data = json.loads(state_data_str)
            
            if state_data["provider"] != provider:
                raise AuthenticationError("状态参数不匹配")
            
            # 删除状态缓存
            await self.redis_client.delete(state_key)
            
            # 交换访问令牌
            token_data = await self._exchange_code_for_token(provider, code)
            
            # 获取用户信息
            user_info = await self._get_user_info(provider, token_data["access_token"])
            
            # 查找或创建用户
            user = await self._find_or_create_user(provider, user_info)
            
            # 创建SSO会话
            sso_token = await create_sso_session(
                user_id=user.id,
                sso_provider=provider,
                sso_user_id=user_info.get("id", user_info.get("sub")),
                redis_client=self.redis_client
            )
            
            # 生成JWT令牌
            auth_service = AuthService(self.session)
            jwt_tokens = await auth_service.create_tokens(user.id)
            
            result = {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "nickname": user.nickname,
                    "avatar": user.avatar
                },
                "tokens": jwt_tokens,
                "sso_token": sso_token,
                "provider": provider
            }
            
            # 如果有会议编码，添加会议信息
            meeting_code = state_data.get("meeting_code")
            if meeting_code:
                result["meeting_code"] = meeting_code
                # TODO: 生成会议访问令牌
                # result["meeting_access_token"] = await generate_meeting_access_token(...)
            
            return result
            
        except Exception as e:
            logger.error(f"处理SSO回调失败: {e}")
            raise
    
    async def _exchange_code_for_token(self, provider: str, code: str) -> Dict[str, Any]:
        """交换授权码获取访问令牌"""
        try:
            import aiohttp
            
            provider_config = SSO_PROVIDERS[provider]
            token_url = provider_config["token_url"].format(
                tenant_id=self._get_tenant_id(provider),
                domain=self._get_domain(provider)
            )
            
            token_params = {
                "grant_type": "authorization_code",
                "client_id": self._get_client_id(provider),
                "client_secret": self._get_client_secret(provider),
                "code": code,
                "redirect_uri": self._get_default_redirect_uri(provider)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=token_params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise AuthenticationError(f"令牌交换失败: {error_text}")
                    
                    token_data = await response.json()
                    return token_data
                    
        except Exception as e:
            logger.error(f"交换访问令牌失败: {e}")
            raise
    
    async def _get_user_info(self, provider: str, access_token: str) -> Dict[str, Any]:
        """获取用户信息"""
        try:
            import aiohttp
            
            provider_config = SSO_PROVIDERS[provider]
            user_info_url = provider_config["user_info_url"].format(
                domain=self._get_domain(provider)
            )
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(user_info_url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise AuthenticationError(f"获取用户信息失败: {error_text}")
                    
                    user_info = await response.json()
                    return user_info
                    
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            raise
    
    async def _find_or_create_user(self, provider: str, user_info: Dict[str, Any]) -> User:
        """查找或创建用户"""
        try:
            user_service = UserService(self.session)
            
            # 提取用户信息
            email = user_info.get("email") or user_info.get("mail")
            username = user_info.get("preferred_username") or user_info.get("name") or email
            full_name = user_info.get("name") or user_info.get("displayName")
            avatar = user_info.get("picture")
            
            if not email:
                raise ValidationError("SSO用户信息中缺少邮箱")
            
            # 查找现有用户
            existing_user = await user_service.get_user_by_email(email)
            
            if existing_user:
                # 更新用户信息
                if avatar and not existing_user.avatar:
                    existing_user.avatar = avatar
                
                # 记录SSO登录
                await self._record_sso_login(existing_user.id, provider, user_info)
                
                return existing_user
            
            # 创建新用户
            new_user_data = {
                "username": username,
                "email": email,
                "full_name": full_name,
                "avatar": avatar,
                "is_active": True,
                "is_verified": True,  # SSO用户默认已验证
                "sso_provider": provider,
                "sso_user_id": user_info.get("id", user_info.get("sub"))
            }
            
            new_user = await user_service.create_sso_user(new_user_data)
            
            # 记录SSO登录
            await self._record_sso_login(new_user.id, provider, user_info)
            
            return new_user
            
        except Exception as e:
            logger.error(f"查找或创建用户失败: {e}")
            raise
    
    async def _record_sso_login(self, user_id: int, provider: str, user_info: Dict[str, Any]):
        """记录SSO登录"""
        try:
            login_record = {
                "user_id": user_id,
                "provider": provider,
                "sso_user_id": user_info.get("id", user_info.get("sub")),
                "login_time": datetime.utcnow().isoformat(),
                "user_info": user_info
            }
            
            # 缓存最近的SSO登录记录
            record_key = f"sso_login:{user_id}:{provider}"
            await self.redis_client.setex(
                record_key,
                86400,  # 24小时
                json.dumps(login_record)
            )
            
            logger.info(f"记录SSO登录: 用户 {user_id}, 提供商 {provider}")
            
        except Exception as e:
            logger.error(f"记录SSO登录失败: {e}")
    
    def _get_client_id(self, provider: str) -> str:
        """获取客户端ID"""
        # TODO: 从配置或环境变量获取
        return f"sso_{provider}_client_id"
    
    def _get_client_secret(self, provider: str) -> str:
        """获取客户端密钥"""
        # TODO: 从配置或环境变量获取
        return f"sso_{provider}_client_secret"
    
    def _get_tenant_id(self, provider: str) -> str:
        """获取租户ID（用于Microsoft Azure AD）"""
        # TODO: 从配置获取
        return "common"
    
    def _get_domain(self, provider: str) -> str:
        """获取域名（用于Okta、Auth0等）"""
        # TODO: 从配置获取
        return f"{provider}.example.com"
    
    def _get_default_redirect_uri(self, provider: str) -> str:
        """获取默认重定向URI"""
        # TODO: 从配置获取
        return f"https://example.com/auth/sso/{provider}/callback"


# 全局SSO集成实例
sso_integration = SSOIntegration()


async def get_sso_integration(
    redis_client = Depends(get_redis_client),
    session: AsyncSession = Depends(get_async_session)
) -> SSOIntegration:
    """获取SSO集成服务实例"""
    await sso_integration.initialize(redis_client, session)
    return sso_integration


async def initiate_sso_login(
    provider: str,
    meeting_code: Optional[str] = None,
    redirect_uri: Optional[str] = None,
    sso_service: SSOIntegration = Depends(get_sso_integration)
) -> Dict[str, Any]:
    """
    发起SSO登录
    
    Args:
        provider: SSO提供商
        meeting_code: 会议编码
        redirect_uri: 重定向URI
        sso_service: SSO服务
        
    Returns:
        Dict: 认证URL和相关信息
    """
    try:
        result = await sso_service.get_sso_auth_url(
            provider=provider,
            meeting_code=meeting_code,
            redirect_uri=redirect_uri
        )
        
        return result
        
    except Exception as e:
        logger.error(f"发起SSO登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSO登录失败: {str(e)}"
        )


async def handle_sso_callback(
    provider: str,
    code: str,
    state: str,
    error: Optional[str] = None,
    sso_service: SSOIntegration = Depends(get_sso_integration)
) -> Dict[str, Any]:
    """
    处理SSO回调
    
    Args:
        provider: SSO提供商
        code: 授权码
        state: 状态参数
        error: 错误信息
        sso_service: SSO服务
        
    Returns:
        Dict: 认证结果
    """
    try:
        result = await sso_service.handle_sso_callback(
            provider=provider,
            code=code,
            state=state,
            error=error
        )
        
        return result
        
    except Exception as e:
        logger.error(f"处理SSO回调失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSO认证失败: {str(e)}"
        )


async def get_supported_sso_providers() -> List[Dict[str, Any]]:
    """获取支持的SSO提供商列表"""
    return [
        {
            "id": provider_id,
            "name": config["name"],
            "scopes": config["scopes"]
        }
        for provider_id, config in SSO_PROVIDERS.items()
    ]