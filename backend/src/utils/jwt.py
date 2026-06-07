"""
JWT令牌工具类
"""
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
from ..core.config import settings


class JWTService:
    """JWT服务类"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS * 60
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": str(uuid.uuid4()),
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": str(uuid.uuid4()),
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码令牌（不验证过期时间）"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload
        except JWTError:
            return None
    
    def create_reset_token(self, data: Dict[str, Any]) -> str:
        """创建重置密码令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=30)  # 30分钟过期
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "reset",
            "jti": str(uuid.uuid4()),
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt


# 创建JWT服务实例
jwt_service = JWTService()

# 为了向后兼容，导出函数级别的接口
def create_access_token(data: Dict[str, Any]) -> str:
    """创建访问令牌"""
    return jwt_service.create_access_token(data)

def create_refresh_token(data: Dict[str, Any]) -> str:
    """创建刷新令牌"""
    return jwt_service.create_refresh_token(data)

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证令牌"""
    return jwt_service.verify_token(token)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码令牌"""
    return jwt_service.decode_token(token)
