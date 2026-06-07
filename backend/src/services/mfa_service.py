"""
多因素认证服务 (MFA)
支持TOTP (Time-based One-Time Password) 认证
"""
import pyotp
import qrcode
import io
import base64
import secrets
import json
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from ..models.user import User
from ..core.config import get_settings

settings = get_settings()

class MFAService:
    """多因素认证服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def generate_secret(self) -> str:
        """生成MFA密钥"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user: User, secret: str) -> str:
        """生成TOTP二维码"""
        # 创建TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=settings.APP_NAME or "AI测试管理系统"
        )
        
        # 生成二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # 创建二维码图片
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 转换为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    def generate_backup_codes(self, count: int = 8) -> List[str]:
        """生成备用验证码"""
        codes = []
        for _ in range(count):
            # 生成8位数字验证码
            code = f"{secrets.randbelow(100000000):08d}"
            codes.append(code)
        return codes
    
    def verify_totp_token(self, secret: str, token: str) -> bool:
        """验证TOTP令牌"""
        try:
            totp = pyotp.TOTP(secret)
            # 允许前后30秒的时间窗口
            return totp.verify(token, valid_window=1)
        except Exception:
            return False
    
    def verify_backup_code(self, user: User, code: str) -> bool:
        """验证备用代码"""
        if not user.mfa_backup_codes:
            return False
        
        try:
            backup_codes = json.loads(user.mfa_backup_codes)
            if code in backup_codes:
                # 使用后删除该代码
                backup_codes.remove(code)
                user.mfa_backup_codes = json.dumps(backup_codes)
                return True
        except (json.JSONDecodeError, ValueError):
            pass
        
        return False
    
    async def setup_mfa(self, user_id: int) -> Dict[str, Any]:
        """为用户设置MFA"""
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        # 生成密钥和备用代码
        secret = self.generate_secret()
        backup_codes = self.generate_backup_codes()
        qr_code = self.generate_qr_code(user, secret)
        
        # 暂时存储（用户确认后才正式启用）
        return {
            "secret": secret,
            "qr_code": qr_code,
            "backup_codes": backup_codes,
            "setup_complete": False
        }
    
    async def enable_mfa(self, user_id: int, secret: str, token: str) -> Dict[str, Any]:
        """启用MFA（用户验证TOTP令牌后）"""
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        # 验证TOTP令牌
        if not self.verify_totp_token(secret, token):
            raise ValueError("验证码错误")
        
        # 生成并保存备用代码
        backup_codes = self.generate_backup_codes()
        
        # 更新用户MFA设置
        user.mfa_enabled = True
        user.mfa_secret = secret
        user.mfa_backup_codes = json.dumps(backup_codes)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return {
            "success": True,
            "message": "MFA已成功启用",
            "backup_codes": backup_codes
        }
    
    async def disable_mfa(self, user_id: int, password: str, token_or_backup: str) -> Dict[str, Any]:
        """禁用MFA"""
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        if not user.mfa_enabled:
            raise ValueError("MFA未启用")
        
        # 验证密码
        from ..services.auth import AuthService
        auth_service = AuthService(self.db)
        from ..utils.password import password_service
        
        if not password_service.verify_password(password, user.salt, user.password_hash):
            raise ValueError("密码错误")
        
        # 验证TOTP令牌或备用代码
        valid_token = False
        if user.mfa_secret:
            valid_token = self.verify_totp_token(user.mfa_secret, token_or_backup)
        
        if not valid_token:
            valid_token = self.verify_backup_code(user, token_or_backup)
        
        if not valid_token:
            raise ValueError("验证码或备用代码错误")
        
        # 禁用MFA
        user.mfa_enabled = False
        user.mfa_secret = None
        user.mfa_backup_codes = None
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return {
            "success": True,
            "message": "MFA已禁用"
        }
    
    async def verify_mfa_token(self, user_id: int, token: str) -> bool:
        """验证MFA令牌"""
        user = await self.db.get(User, user_id)
        if not user or not user.mfa_enabled:
            return False
        
        # 先尝试TOTP验证
        if user.mfa_secret and self.verify_totp_token(user.mfa_secret, token):
            return True
        
        # 再尝试备用代码验证
        if self.verify_backup_code(user, token):
            await self.db.commit()  # 保存备用代码的删除
            return True
        
        return False
    
    async def regenerate_backup_codes(self, user_id: int, password: str, token: str) -> List[str]:
        """重新生成备用代码"""
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")
        
        if not user.mfa_enabled:
            raise ValueError("MFA未启用")
        
        # 验证密码
        from ..utils.password import password_service
        if not password_service.verify_password(password, user.salt, user.password_hash):
            raise ValueError("密码错误")
        
        # 验证TOTP令牌
        if not user.mfa_secret or not self.verify_totp_token(user.mfa_secret, token):
            raise ValueError("验证码错误")
        
        # 生成新的备用代码
        backup_codes = self.generate_backup_codes()
        user.mfa_backup_codes = json.dumps(backup_codes)
        
        await self.db.commit()
        
        return backup_codes