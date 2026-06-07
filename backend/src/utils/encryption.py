"""
配置加密服务
"""
import os
import base64
import json
from typing import Any, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """配置加密服务"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化加密服务
        
        Args:
            encryption_key: 加密密钥，如果为None则从环境变量获取
        """
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            # 从环境变量获取密钥
            env_key = os.getenv('CONFIG_ENCRYPTION_KEY', '')
            if env_key:
                self.encryption_key = env_key.encode()
            else:
                # 生成新的密钥
                self.encryption_key = self._generate_key()
                logger.warning("未找到加密密钥，已生成新密钥。请将其保存到环境变量CONFIG_ENCRYPTION_KEY中。")
        
        # 从密钥派生Fernet密钥
        self.fernet_key = self._derive_fernet_key(self.encryption_key)
        self.cipher = Fernet(self.fernet_key)
    
    def _generate_key(self) -> bytes:
        """生成新的加密密钥"""
        return Fernet.generate_key()
    
    def _derive_fernet_key(self, password: bytes, salt: Optional[bytes] = None) -> bytes:
        """
        从密码派生Fernet密钥
        
        Args:
            password: 密码
            salt: 盐值，如果为None则使用固定盐值
            
        Returns:
            Fernet密钥
        """
        if salt is None:
            # 使用固定盐值（生产环境中应该使用随机盐值并存储）
            salt = b'config_salt_2024'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt(self, value: Union[str, bytes]) -> str:
        """
        加密配置值
        
        Args:
            value: 要加密的值
            
        Returns:
            Base64编码的加密值
        """
        if value is None:
            return None
        
        try:
            # 确保输入是字节串
            if isinstance(value, str):
                value_bytes = value.encode('utf-8')
            else:
                value_bytes = value
            
            # 加密
            encrypted_bytes = self.cipher.encrypt(value_bytes)
            
            # Base64编码
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode('ascii')
            
            return encrypted_b64
            
        except Exception as e:
            logger.error(f"配置值加密失败: {e}")
            raise ValueError(f"配置值加密失败: {e}")
    
    def decrypt(self, encrypted_value: str) -> str:
        """
        解密配置值
        
        Args:
            encrypted_value: Base64编码的加密值
            
        Returns:
            解密后的原始值
        """
        if not encrypted_value:
            return encrypted_value
        
        try:
            # Base64解码
            encrypted_bytes = base64.b64decode(encrypted_value.encode('ascii'))
            
            # 解密
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            
            # 转换为字符串
            decrypted_value = decrypted_bytes.decode('utf-8')
            
            return decrypted_value
            
        except Exception as e:
            # 解密失败，可能是未加密的值或密钥错误
            logger.warning(f"配置值解密失败，返回原值: {e}")
            return encrypted_value
    
    def is_encrypted(self, value: str) -> bool:
        """
        检查值是否已加密
        
        Args:
            value: 要检查的值
            
        Returns:
            是否已加密
        """
        if not value:
            return False
        
        try:
            # 尝试Base64解码
            encrypted_bytes = base64.b64decode(value.encode('ascii'))
            
            # 尝试解密
            self.cipher.decrypt(encrypted_bytes)
            return True
            
        except Exception:
            return False
    
    def get_key_info(self) -> dict:
        """
        获取密钥信息（不包含密钥本身）
        
        Returns:
            密钥信息
        """
        return {
            'key_length': len(self.encryption_key),
            'algorithm': 'AES-256',
            'key_derivation': 'PBKDF2-HMAC-SHA256'
        }


class ConfigEncryptionMixin:
    """配置加密混入类"""
    
    _encryption_service: Optional[EncryptionService] = None
    
    @classmethod
    def get_encryption_service(cls) -> EncryptionService:
        """获取加密服务实例（单例）"""
        if cls._encryption_service is None:
            cls._encryption_service = EncryptionService()
        return cls._encryption_service
    
    @classmethod
    def set_encryption_service(cls, service: EncryptionService):
        """设置加密服务实例"""
        cls._encryption_service = service
    
    def encrypt_if_needed(self, value: str, should_encrypt: bool) -> str:
        """
        根据需要加密值
        
        Args:
            value: 要处理的值
            should_encrypt: 是否需要加密
            
        Returns:
            处理后的值
        """
        if not value or not should_encrypt:
            return value
        
        service = self.get_encryption_service()
        
        # 如果已经加密，直接返回
        if service.is_encrypted(value):
            return value
        
        # 加密
        return service.encrypt(value)
    
    def decrypt_if_needed(self, value: str, is_encrypted: bool) -> str:
        """
        根据需要解密值
        
        Args:
            value: 要处理的值
            is_encrypted: 是否已加密
            
        Returns:
            处理后的值
        """
        if not value or not is_encrypted:
            return value
        
        service = self.get_encryption_service()
        return service.decrypt(value)


# 全局加密服务实例
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """获取全局加密服务实例"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def set_encryption_service(service: EncryptionService):
    """设置全局加密服务实例"""
    global _encryption_service
    _encryption_service = service


def encrypt_config_value(value: str) -> str:
    """加密配置值的便捷函数"""
    return get_encryption_service().encrypt(value)


def decrypt_config_value(encrypted_value: str) -> str:
    """解密配置值的便捷函数"""
    return get_encryption_service().decrypt(encrypted_value)


def is_config_encrypted(value: str) -> bool:
    """检查配置值是否已加密的便捷函数"""
    return get_encryption_service().is_encrypted(value)