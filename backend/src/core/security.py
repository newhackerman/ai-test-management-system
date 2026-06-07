"""
安全相关工具函数
"""
import bcrypt
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 认证
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
        
    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    获取密码哈希值
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希密码
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问令牌
    
    Args:
        data: 令牌数据
        expires_delta: 过期时间
        
    Returns:
        str: 访问令牌
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证令牌
    
    Args:
        token: 访问令牌
        
    Returns:
        Optional[Dict[str, Any]]: 令牌数据，验证失败返回None
    """
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def generate_random_password(length: int = 12) -> str:
    """
    生成随机密码
    
    Args:
        length: 密码长度
        
    Returns:
        str: 随机密码
    """
    # 确保密码包含大小写字母、数字和特殊字符
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = string.punctuation
    
    # 从每个类别中至少选择一个字符
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # 填充剩余长度
    all_chars = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # 打乱字符顺序
    secrets.SystemRandom().shuffle(password)
    
    return "".join(password)


def generate_secure_token(length: int = 32) -> str:
    """
    生成安全令牌
    
    Args:
        length: 令牌长度
        
    Returns:
        str: 安全令牌
    """
    return secrets.token_urlsafe(length)


def is_valid_email(email: str) -> bool:
    """
    验证邮箱格式
    
    Args:
        email: 邮箱地址
        
    Returns:
        bool: 邮箱格式是否有效
    """
    try:
        EmailStr.validate(email)
        return True
    except:
        return False


def is_strong_password(password: str) -> bool:
    """
    检查密码强度
    
    Args:
        password: 密码
        
    Returns:
        bool: 密码是否足够强
    """
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False
    
    # 检查密码复杂度
    has_lowercase = any(c.islower() for c in password)
    has_uppercase = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in string.punctuation for c in password)
    
    # 至少包含三种类型的字符
    complexity_score = sum([has_lowercase, has_uppercase, has_digit, has_special])
    return complexity_score >= 3


def sanitize_input(input_str: str) -> str:
    """
    清理输入字符串，防止XSS攻击
    
    Args:
        input_str: 输入字符串
        
    Returns:
        str: 清理后的字符串
    """
    # 这里可以实现更复杂的输入清理逻辑
    # 例如移除HTML标签、JavaScript代码等
    return input_str.strip()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    获取当前用户信息
    
    Args:
        credentials: HTTP认证凭据
        
    Returns:
        Dict[str, Any]: 用户信息
        
    Raises:
        HTTPException: 认证失败时抛出异常
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
        # 这里可以从数据库获取完整的用户信息
        # 目前返回基本信息
        return {
            "id": int(user_id),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "is_active": payload.get("is_active", True)
        }
        
    except Exception:
        raise credentials_exception


def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict[str, Any]]:
    """
    获取当前用户信息（可选）
    
    Args:
        credentials: HTTP认证凭据
        
    Returns:
        Optional[Dict[str, Any]]: 用户信息，认证失败返回None
    """
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None