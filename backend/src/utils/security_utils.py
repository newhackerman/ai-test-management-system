"""
安全工具函数

提供各种安全相关的工具函数，包括：
- 数据加密和解密
- 安全哈希
- 输入清理
- 安全令牌生成
- 密码强度验证
"""
import re
import secrets
import hashlib
import hmac
import base64
import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import jwt
import bleach
import html

logger = logging.getLogger(__name__)


class SecurityUtils:
    """安全工具类"""
    
    # 密码强度正则表达式
    PASSWORD_PATTERNS = {
        'weak': r'^.{1,7}$',  # 长度小于8
        'medium': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$',  # 包含大小写字母和数字
        'strong': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'  # 包含特殊字符
    }
    
    # 危险字符模式
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
        r'expression\s*\(',
        r'@import',
        r'<\s*link[^>]*>',
        r'<\s*meta[^>]*>',
        r'<\s*style[^>]*>.*?</style>',
    ]
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """生成安全密码"""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # 使用PBKDF2进行密码哈希
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode())
        hashed = base64.b64encode(key).decode()
        
        return hashed, salt
    
    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """验证密码"""
        try:
            new_hashed, _ = SecurityUtils.hash_password(password, salt)
            return hmac.compare_digest(hashed, new_hashed)
        except Exception as e:
            logger.error(f"密码验证失败: {str(e)}")
            return False
    
    @staticmethod
    def check_password_strength(password: str) -> Dict[str, Any]:
        """检查密码强度"""
        if not password:
            return {
                'strength': 'invalid',
                'score': 0,
                'feedback': ['密码不能为空']
            }
        
        feedback = []
        score = 0
        
        # 长度检查
        if len(password) < 8:
            feedback.append('密码长度至少8位')
        else:
            score += 1
        
        # 包含小写字母
        if re.search(r'[a-z]', password):
            score += 1
        else:
            feedback.append('密码应包含小写字母')
        
        # 包含大写字母
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            feedback.append('密码应包含大写字母')
        
        # 包含数字
        if re.search(r'\d', password):
            score += 1
        else:
            feedback.append('密码应包含数字')
        
        # 包含特殊字符
        if re.search(r'[@$!%*?&]', password):
            score += 1
        else:
            feedback.append('密码应包含特殊字符')
        
        # 不包含常见弱密码
        weak_passwords = ['password', '123456', 'qwerty', 'admin', 'root']
        if password.lower() in weak_passwords:
            score = 0
            feedback.append('密码过于简单，请使用更复杂的密码')
        
        # 确定强度等级
        if score <= 2:
            strength = 'weak'
        elif score <= 3:
            strength = 'medium'
        else:
            strength = 'strong'
        
        return {
            'strength': strength,
            'score': score,
            'feedback': feedback
        }
    
    @staticmethod
    def sanitize_input(text: str, allow_html: bool = False) -> str:
        """清理输入数据"""
        if not text:
            return text
        
        # HTML转义
        if not allow_html:
            text = html.escape(text)
        else:
            # 使用bleach清理HTML
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            allowed_attributes = {}
            text = bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes, strip=True)
        
        # 移除危险模式
        for pattern in SecurityUtils.DANGEROUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证手机号格式"""
        # 中国手机号格式
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """验证IP地址格式"""
        # IPv4格式
        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        
        # IPv6格式（简化）
        ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        
        return bool(re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip))
    
    @staticmethod
    def generate_csrf_token() -> str:
        """生成CSRF令牌"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_csrf_token(token: str, expected_token: str) -> bool:
        """验证CSRF令牌"""
        return hmac.compare_digest(token, expected_token)
    
    @staticmethod
    def create_jwt_token(
        payload: Dict[str, Any],
        secret_key: str,
        expires_in: int = 3600,
        algorithm: str = 'HS256'
    ) -> str:
        """创建JWT令牌"""
        payload['exp'] = datetime.utcnow() + timedelta(seconds=expires_in)
        payload['iat'] = datetime.utcnow()
        
        return jwt.encode(payload, secret_key, algorithm=algorithm)
    
    @staticmethod
    def verify_jwt_token(token: str, secret_key: str, algorithm: str = 'HS256') -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT令牌无效: {str(e)}")
            return None
    
    @staticmethod
    def encrypt_data(data: str, key: str) -> str:
        """加密数据"""
        try:
            # 使用Fernet对称加密
            key_bytes = base64.urlsafe_b64encode(key.encode().ljust(32)[:32])
            f = Fernet(key_bytes)
            encrypted = f.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"数据加密失败: {str(e)}")
            raise
    
    @staticmethod
    def decrypt_data(encrypted_data: str, key: str) -> str:
        """解密数据"""
        try:
            key_bytes = base64.urlsafe_b64encode(key.encode().ljust(32)[:32])
            f = Fernet(key_bytes)
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted = f.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"数据解密失败: {str(e)}")
            raise
    
    @staticmethod
    def generate_api_key(prefix: str = "ak") -> str:
        """生成API密钥"""
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """哈希API密钥"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        """验证API密钥"""
        return hmac.compare_digest(SecurityUtils.hash_api_key(api_key), hashed_key)
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """生成一次性密码"""
        return ''.join(secrets.choice('0123456789') for _ in range(length))
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
        """掩码敏感数据"""
        if not data or len(data) <= visible_chars:
            return mask_char * len(data) if data else ''
        
        visible_start = visible_chars // 2
        visible_end = visible_chars - visible_start
        
        masked_length = len(data) - visible_chars
        masked_part = mask_char * min(masked_length, 8)  # 最多显示8个掩码字符
        
        return data[:visible_start] + masked_part + data[-visible_end:] if visible_end > 0 else data[:visible_start] + masked_part
    
    @staticmethod
    def check_common_vulnerabilities(text: str) -> List[str]:
        """检查常见漏洞"""
        vulnerabilities = []
        
        if not text:
            return vulnerabilities
        
        text_lower = text.lower()
        
        # SQL注入检查
        sql_patterns = [
            r'\bunion\s+select\b',
            r'\bselect\s+.*\bfrom\b',
            r'\binsert\s+into\b',
            r'\bupdate\s+.*\bset\b',
            r'\bdelete\s+from\b',
            r'\bdrop\s+table\b',
            r'--\s*$',
            r'/\*.*\*/',
            r'\bor\s+1\s*=\s*1\b',
            r'\band\s+1\s*=\s*1\b'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, text_lower):
                vulnerabilities.append('SQL注入风险')
                break
        
        # XSS检查
        xss_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>'
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, text_lower):
                vulnerabilities.append('XSS攻击风险')
                break
        
        # 路径遍历检查
        if '../' in text or '..\\' in text:
            vulnerabilities.append('路径遍历风险')
        
        # 命令注入检查
        command_patterns = [
            r';\s*\w+',
            r'\|\s*\w+',
            r'&&\s*\w+',
            r'\$\(\w+\)',
            r'`\w+`'
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, text):
                vulnerabilities.append('命令注入风险')
                break
        
        return vulnerabilities
    
    @staticmethod
    def generate_secure_filename(original_filename: str) -> str:
        """生成安全的文件名"""
        if not original_filename:
            return f"file_{secrets.token_hex(8)}"
        
        # 获取文件扩展名
        name, ext = original_filename.rsplit('.', 1) if '.' in original_filename else (original_filename, '')
        
        # 清理文件名
        safe_name = re.sub(r'[^\w\-_.]', '_', name)
        safe_name = safe_name[:50]  # 限制长度
        
        # 添加随机后缀防止冲突
        random_suffix = secrets.token_hex(4)
        
        if ext:
            return f"{safe_name}_{random_suffix}.{ext}"
        else:
            return f"{safe_name}_{random_suffix}"
    
    @staticmethod
    def validate_file_type(filename: str, allowed_extensions: List[str]) -> bool:
        """验证文件类型"""
        if not filename or '.' not in filename:
            return False
        
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in [e.lower() for e in allowed_extensions]
    
    @staticmethod
    def calculate_file_hash(file_content: bytes, algorithm: str = 'sha256') -> str:
        """计算文件哈希值"""
        if algorithm == 'md5.py':
            hash_obj = hashlib.md5()
        elif algorithm == 'sha1':
            hash_obj = hashlib.sha1()
        elif algorithm == 'sha256':
            hash_obj = hashlib.sha256()
        else:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
        
        hash_obj.update(file_content)
        return hash_obj.hexdigest()
    
    @staticmethod
    def create_signature(data: str, secret_key: str, algorithm: str = 'sha256') -> str:
        """创建数据签名"""
        if algorithm == 'sha256':
            hash_obj = hmac.new(secret_key.encode(), data.encode(), hashlib.sha256)
        elif algorithm == 'sha1':
            hash_obj = hmac.new(secret_key.encode(), data.encode(), hashlib.sha1)
        else:
            raise ValueError(f"不支持的签名算法: {algorithm}")
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def verify_signature(data: str, signature: str, secret_key: str, algorithm: str = 'sha256') -> bool:
        """验证数据签名"""
        expected_signature = SecurityUtils.create_signature(data, secret_key, algorithm)
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def generate_session_id() -> str:
        """生成会话ID"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def is_safe_redirect_url(url: str, allowed_hosts: List[str]) -> bool:
        """检查重定向URL是否安全"""
        if not url:
            return False
        
        # 检查是否为相对URL
        if url.startswith('/') and not url.startswith('//'):
            return True
        
        # 检查是否为允许的主机
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(url)
            return parsed.hostname in allowed_hosts
        except Exception:
            return False
    
    @staticmethod
    def rate_limit_key(identifier: str, action: str) -> str:
        """生成速率限制键"""
        return f"rate_limit:{action}:{identifier}"
    
    @staticmethod
    def audit_log_key(user_id: int, action: str) -> str:
        """生成审计日志键"""
        return f"audit:{user_id}:{action}:{datetime.utcnow().strftime('%Y%m%d')}"