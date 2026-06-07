"""
MFA服务 - 提供多因素认证功能
"""
import pyotp
import qrcode
import io
import base64
import secrets
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..models.user import User
from ..core.config import settings


class MFAService:
    """MFA服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_mfa_secret(self, user_id: int) -> str:
        """生成MFA密钥"""
        # 生成随机密钥
        secret = pyotp.random_base32()
        
        # 更新用户MFA密钥
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(mfa_secret=secret)
        )
        await self.db.commit()
        
        return secret
    
    async def generate_mfa_qr_code(self, user: User) -> str:
        """生成MFA二维码"""
        if not user.mfa_secret:
            raise ValueError("用户未设置MFA密钥")
        
        # 创建TOTP对象
        totp = pyotp.TOTP(user.mfa_secret)
        
        # 生成 provisioning URI
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.mfa_issuer_name
        )
        
        # 生成二维码
        qr_img = qrcode.make(provisioning_uri)
        
        # 将二维码转换为Base64字符串
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_str}"
    
    async def verify_mfa_token(self, user_id: int, token: str) -> bool:
        """验证MFA令牌"""
        # 获取用户MFA密钥
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user or not user.mfa_secret:
            return False
        
        # 验证令牌
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(token, valid_window=1)  # 允许前后一个时间窗口的令牌
    
    async def enable_mfa(self, user_id: int, token: str) -> Tuple[bool, Optional[str], Optional[List[str]]]:
        """启用MFA"""
        # 验证令牌
        if not await self.verify_mfa_token(user_id, token):
            return False, "验证码错误", None
        
        # 生成备用代码
        backup_codes = self._generate_backup_codes()
        
        # 更新用户MFA状态
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                mfa_enabled=True,
                mfa_backup_codes=",".join(backup_codes)
            )
        )
        await self.db.commit()
        
        return True, "MFA已启用", backup_codes
    
    async def disable_mfa(self, user_id: int, password: str, token: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """禁用MFA"""
        # 获取用户信息
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return False, "用户不存在"
        
        # 验证密码
        from ..utils.password import password_service
        if not password_service.verify_password(password, user.salt, user.password_hash):
            return False, "密码错误"
        
        # 如果启用了MFA，验证MFA令牌
        if user.mfa_enabled and token:
            if not await self.verify_mfa_token(user_id, token):
                return False, "验证码错误"
        
        # 禁用MFA
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                mfa_enabled=False,
                mfa_secret=None,
                mfa_backup_codes=None
            )
        )
        await self.db.commit()
        
        return True, "MFA已禁用"
    
    async def verify_backup_code(self, user_id: int, backup_code: str) -> bool:
        """验证备用代码"""
        # 获取用户备用代码
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user or not user.mfa_backup_codes:
            return False
        
        # 检查备用代码
        backup_codes = user.mfa_backup_codes.split(",")
        if backup_code not in backup_codes:
            return False
        
        # 移除已使用的备用代码
        backup_codes.remove(backup_code)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(mfa_backup_codes=",".join(backup_codes) if backup_codes else None)
        )
        await self.db.commit()
        
        return True
    
    def _generate_backup_codes(self) -> List[str]:
        """生成备用代码"""
        backup_codes = []
        for _ in range(10):  # 生成10个备用代码
            code = secrets.token_hex(4).upper()  # 8位十六进制代码
            backup_codes.append(code)
        
        return backup_codes
    
    async def get_mfa_status(self, user_id: int) -> dict:
        """获取MFA状态"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return {"enabled": False}
        
        return {
            "enabled": user.mfa_enabled,
            "has_backup_codes": bool(user.mfa_backup_codes)
        }