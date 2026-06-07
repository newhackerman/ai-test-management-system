"""
密码工具类
"""
import bcrypt
import secrets
import string
from typing import Tuple
from ..core.config import settings


class PasswordService:
    """密码服务类"""
    
    def __init__(self):
        self.rounds = 12  # bcrypt成本因子
        self.min_length = 8
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_numbers = True
        self.require_symbols = True
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """
        哈希密码
        
        Args:
            password: 明文密码
            
        Returns:
            Tuple[str, str]: (盐值, 哈希值)
        """
        # 生成盐值
        salt = bcrypt.gensalt(rounds=self.rounds)
        
        # 哈希密码
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return salt.decode('utf-8'), password_hash.decode('utf-8')
    
    def verify_password(self, password: str, salt: str, password_hash: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
            salt: 盐值
            password_hash: 哈希值
            
        Returns:
            bool: 验证结果
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception:
            return False
    
    def generate_password(self, length: int = 12) -> str:
        """
        生成随机密码
        
        Args:
            length: 密码长度
            
        Returns:
            str: 随机密码
        """
        # 确保密码包含各种字符类型
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special_chars = "!@#$%^&*"
        
        # 至少包含一个每种类型的字符
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special_chars)
        ]
        
        # 填充剩余长度
        all_chars = lowercase + uppercase + digits + special_chars
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # 打乱顺序
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        验证密码强度
        
        Args:
            password: 密码
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if len(password) < self.min_length:
            return False, f"密码长度至少{self.min_length}位"
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            return False, "密码必须包含大写字母"
        
        if self.require_lowercase and not any(c.islower() for c in password):
            return False, "密码必须包含小写字母"
        
        if self.require_numbers and not any(c.isdigit() for c in password):
            return False, "密码必须包含数字"
        
        if self.require_symbols and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, "密码必须包含特殊字符"
        
        return True, ""


# 创建密码服务实例
password_service = PasswordService()