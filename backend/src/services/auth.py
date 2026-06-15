"""
认证服务 - 提供用户认证、JWT令牌管理和会话管理功能
"""
import datetime
import html
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, update
from ..models.user import User, UserStatus, UserSession
from ..models.audit import AuditLog, AuditAction, AuditResult
from ..utils.password import password_service
from ..utils.jwt import jwt_service
from ..core.config import get_settings
from .email_service import EmailConfig, EmailService

settings = get_settings()
logger = logging.getLogger(__name__)

class AuthService:
    """认证服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # 保持对后台邮件任务的强引用，防止 asyncio 提前回收
        self._last_email_task: Optional[asyncio.Task] = None
    
    async def login(
        self,
        username: str,
        password: str,
        client_ip: str,
        user_agent: str,
        remember_me: bool = False
    ) -> Dict[str, Any]:
        """用户登录"""
        # 查找用户
        query = select(User).where(
            or_(User.username == username, User.email == username)
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            await self._log_login_attempt(None, username, client_ip, user_agent, AuditResult.FAILURE, "用户不存在")
            return {"success": False, "message": "用户名或密码错误"}
        
        if user.status == UserStatus.LOCKED and user.locked_until and user.locked_until <= datetime.datetime.utcnow():
            user.status = UserStatus.ACTIVE
            user.failed_login_attempts = 0
            user.locked_until = None
            await self.db.commit()
            await self.db.refresh(user)

        # 检查用户状态
        if user.status != UserStatus.ACTIVE:
            await self._log_login_attempt(user.id, username, client_ip, user_agent, AuditResult.FAILURE, f"用户状态: {user.status.value}")
            return {"success": False, "message": "用户账户不可用"}
        
        # 验证密码
        if not password_service.verify_password(password, user.salt, user.password_hash):
            await self._increment_failed_login_attempts(user)
            await self._log_login_attempt(user.id, username, client_ip, user_agent, AuditResult.FAILURE, "密码错误")
            return {"success": False, "message": "用户名或密码错误"}
        
        # 重置失败次数
        await self._reset_failed_login_attempts(user)
        
        # 生成令牌
        tokens = self.create_tokens(user)
        
        # 创建会话
        session = await self.create_user_session(
            user, tokens["access_token"], tokens["refresh_token"],
            client_ip, user_agent
        )
        
        # 记录成功登录
        await self._log_login_attempt(user.id, username, client_ip, user_agent, AuditResult.SUCCESS)
        
        return {
            "success": True,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": {
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": "admin" if user.is_superuser else "user",
                "real_name": user.nickname or user.username,
                "two_factor_enabled": user.mfa_enabled
            }
        }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新令牌"""
        # 验证刷新令牌
        payload = jwt_service.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return {"success": False, "message": "无效的刷新令牌"}
        
        user_id = payload.get("sub")
        if not user_id:
            return {"success": False, "message": "无效的刷新令牌"}
        
        # 查找用户
        query = select(User).where(User.id == int(user_id))
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user or user.status != UserStatus.ACTIVE:
            return {"success": False, "message": "用户不存在或已禁用"}
        
        # 生成新的访问令牌
        new_access_token = jwt_service.create_access_token({"sub": str(user.id)})
        
        return {
            "success": True,
            "access_token": new_access_token
        }
    
    async def logout(
        self,
        user_id: int,
        session_id: Optional[str] = None,
        all_devices: bool = False
    ) -> Dict[str, Any]:
        """用户登出"""
        if all_devices:
            # 登出所有设备
            await self.db.execute(
                update(UserSession)
                .where(UserSession.user_id == user_id)
                .values(is_active=False)
            )
        elif session_id:
            # 登出指定会话
            await self.db.execute(
                update(UserSession)
                .where(and_(
                    UserSession.user_id == user_id,
                    UserSession.session_token == session_id
                ))
                .values(is_active=False)
            )
        
        await self.db.commit()
        
        return {"success": True, "message": "登出成功"}
    
    def create_tokens(self, user: User) -> Dict[str, str]:
        """创建JWT令牌"""
        # 生成访问令牌
        access_token = jwt_service.create_access_token({"sub": str(user.id)})
        
        # 生成刷新令牌
        refresh_token = jwt_service.create_refresh_token({"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def create_user_session(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
        device_info: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """创建用户会话"""
        # 计算会话过期时间
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(
            minutes=settings.SESSION_TIMEOUT_MINUTES
        )
        
        # 创建会话
        session = UserSession(
            user_id=user.id,
            session_token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=str(device_info) if device_info else None,
            expires_at=expires_at
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        return session
    
    async def register(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str,
        client_ip: str,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """用户注册"""
        # 检查用户名是否已存在
        query = select(User).where(
            or_(User.username == username, User.email == email)
        )
        result = await self.db.execute(query)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.username == username:
                return {"success": False, "message": "用户名已存在"}
            else:
                return {"success": False, "message": "邮箱已存在"}
        
        # 创建新用户
        salt, password_hash = password_service.hash_password(password)
        
        new_user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            nickname=full_name,
            phone=phone,
            status=UserStatus.ACTIVE,  # 新注册用户直接激活
            is_email_verified=False,
            is_phone_verified=False,
            mfa_enabled=False,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        
        # 记录注册日志
        await self._log_login_attempt(
            user_id=new_user.id,
            username=username,
            ip_address=client_ip,
            user_agent="",
            result=AuditResult.SUCCESS,
            error_message="用户注册成功"
        )
        
        return {
            "success": True,
            "user_id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "message": "注册成功，请等待管理员审核"
        }
    
    async def _increment_failed_login_attempts(self, user: User) -> None:
        """增加登录失败次数"""
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        
        # 检查是否需要锁定账户
        if user.failed_login_attempts >= 5:
            # 5次失败锁定24小时
            user.status = UserStatus.LOCKED
            user.locked_until = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        elif user.failed_login_attempts >= 3:
            # 3次失败锁定15分钟
            user.status = UserStatus.LOCKED
            user.locked_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        
        await self.db.commit()
    
    async def _reset_failed_login_attempts(self, user: User) -> None:
        """重置登录失败次数"""
        user.failed_login_attempts = 0
        user.locked_until = None
        if user.status == UserStatus.LOCKED:
            user.status = UserStatus.ACTIVE
        
        # 更新最后登录时间
        user.last_login_at = datetime.datetime.utcnow()
        
        await self.db.commit()
    
    async def forgot_password(
        self,
        email: str,
        frontend_base_url: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """忘记密码 - 发送重置密码邮件"""
        ambiguous_msg = "如果该邮箱存在，重置密码链接已发送，请检查邮箱。"

        # 查找用户
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            # 为了安全，不告诉用户邮箱是否存在；但记录审计日志以便追溯
            await self._log_password_reset(
                user_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                result=AuditResult.FAILURE,
                email=email,
                error_message="邮箱不存在",
            )
            return {"success": True, "message": ambiguous_msg}

        # 仅对处于正常可用状态的账户发放重置令牌。
        # 被禁用/锁定/已删除等账户同样返回模糊成功提示，避免用户状态枚举。
        if user.status != UserStatus.ACTIVE or not user.is_active:
            await self._log_password_reset(
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                result=AuditResult.FAILURE,
                email=email,
                error_message=f"账户不可用 status={user.status.value}",
            )
            return {"success": True, "message": ambiguous_msg}

        # 生成重置令牌
        reset_token = jwt_service.create_reset_token({"sub": str(user.id), "email": email})

        # 保存重置令牌到用户记录（实际项目中可能存储在单独的表中）
        user.reset_token = reset_token
        user.reset_token_expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        await self.db.commit()

        reset_url = self._build_reset_password_url(reset_token, frontend_base_url)

        # 异步发送邮件，但通过闭包捕获异常并审计，避免 fire-and-forget 静默失败。
        # 保持对 task 的强引用，防止被 GC 回收。
        async def _safe_send():
            try:
                await self._send_password_reset_email(user, reset_url)
            except Exception as e:  # noqa: BLE001
                logger.error("密码重置邮件任务异常 user_id=%s: %s", user.id, e)
                await self._log_password_reset(
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    result=AuditResult.FAILURE,
                    email=email,
                    error_message=f"邮件发送异常: {e}",
                )

        self._last_email_task = asyncio.create_task(_safe_send())

        await self._log_password_reset(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS,
            email=email,
            extra={"stage": "requested"},
        )

        return {"success": True, "message": ambiguous_msg}

    def _build_reset_password_url(self, token: str, frontend_base_url: Optional[str]) -> str:
        """构建前端重置密码链接。"""
        base_url = (
            frontend_base_url
            or getattr(settings, "FRONTEND_URL", None)
            or getattr(settings, "BASE_URL", None)
            or "http://127.0.0.1:5173"
        )
        return f"{str(base_url).rstrip('/')}/auth/reset-password?{urlencode({'token': token})}"

    async def _send_password_reset_email(self, user: User, reset_url: str) -> None:
        """发送密码重置邮件；邮件未配置时只记录日志，不破坏接口的统一响应。"""
        smtp_host = getattr(settings, "SMTP_HOST", None)
        smtp_port = getattr(settings, "SMTP_PORT", None) or 587
        smtp_user = getattr(settings, "SMTP_USER", None) or getattr(settings, "SMTP_USERNAME", None)
        smtp_password = getattr(settings, "SMTP_PASSWORD", None)
        from_email = str(getattr(settings, "EMAILS_FROM_EMAIL", None) or smtp_user or "")
        from_name = getattr(settings, "EMAILS_FROM_NAME", None) or "AI测试管理系统"

        if not getattr(settings, "EMAIL_ENABLED", False) or not smtp_host or not smtp_user or not smtp_password or not from_email:
            logger.warning("密码重置邮件未发送：邮件服务未完整配置。user_id=%s reset_url=%s", user.id, reset_url)
            return

        email_service = EmailService(
            EmailConfig(
                smtp_server=smtp_host,
                smtp_port=int(smtp_port),
                username=smtp_user,
                password=smtp_password,
                use_tls=bool(getattr(settings, "SMTP_TLS", True)),
                from_email=from_email,
                from_name=from_name,
            )
        )
        display_name = html.escape(user.nickname or user.username)
        safe_reset_url = html.escape(reset_url, quote=True)
        body = f"""
        <div style="font-family: Arial, 'Microsoft YaHei', sans-serif; color: #1f2937; line-height: 1.7;">
          <h2 style="margin: 0 0 16px;">重置登录密码</h2>
          <p>{display_name}，您好：</p>
          <p>我们收到了您的密码重置请求。请点击下面的链接设置新密码，链接 30 分钟内有效。</p>
          <p><a href="{safe_reset_url}" style="display:inline-block;padding:10px 16px;background:#2563eb;color:#fff;text-decoration:none;border-radius:6px;">重置密码</a></p>
          <p>如果按钮无法打开，请复制以下链接到浏览器地址栏：</p>
          <p style="word-break:break-all;color:#2563eb;">{safe_reset_url}</p>
          <p>如果这不是您本人的操作，请忽略此邮件。</p>
        </div>
        """
        sent = await email_service.send_email(
            to=[user.email],
            subject="重置 AI 测试管理系统登录密码",
            body=body,
            is_html=True,
        )
        if not sent:
            logger.error("密码重置邮件发送失败。user_id=%s email=%s", user.id, user.email)
    
    async def reset_password(
        self,
        token: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """重置密码"""
        invalid_msg = "无效或已过期的重置令牌"

        # 1) 校验 JWT 签名与类型
        payload = jwt_service.verify_token(token)
        if not payload or payload.get("type") != "reset":
            await self._log_password_reset(
                user_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                result=AuditResult.FAILURE,
                error_message="JWT 无效或过期",
            )
            return {"success": False, "message": invalid_msg}

        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            await self._log_password_reset(
                user_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                result=AuditResult.FAILURE,
                error_message="JWT 载荷缺少 sub/email",
            )
            return {"success": False, "message": invalid_msg}

        # 2) 先校验新密码强度，避免对库做无谓写操作
        is_strong_password, password_error = password_service.validate_password_strength(new_password)
        if not is_strong_password:
            await self._log_password_reset(
                user_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                result=AuditResult.FAILURE,
                email=email,
                error_message=f"密码强度不足: {password_error}",
            )
            return {"success": False, "message": password_error or "密码强度不足"}

        # 3) 哈希新密码
        salt, password_hash = password_service.hash_password(new_password)

        # 4) 原子条件 UPDATE：仅当 user_id + email + reset_token 完全匹配且未过期时，
        #    才在同一语句内更新密码并作废令牌。数据库行锁保证：
        #    - 令牌只能被消费一次（重放/竞态第二次 rowcount=0）
        #    - 无法为任意用户伪造可用的重置令牌（库里必须存在对应 reset_token）
        now = datetime.datetime.utcnow()
        consume_stmt = (
            update(User)
            .where(
                User.id == int(user_id),
                User.email == email,
                User.reset_token == token,
                or_(User.reset_token_expires.is_(None),
                    User.reset_token_expires > now),
            )
            .values(
                password_hash=password_hash,
                salt=salt,
                reset_token=None,  # 同一语句内作废 → 一次性
                reset_token_expires=None,
                password_updated_at=now,
                updated_at=now,
            )
        )
        result = await self.db.execute(consume_stmt)

        if result.rowcount == 0:
            # 令牌无效 / 已被使用 / 已过期 / 用户不匹配
            await self._log_password_reset(
                user_id=None,
                ip_address=ip_address,
                user_agent=user_agent,
                result=AuditResult.FAILURE,
                email=email,
                error_message="令牌匹配失败或已使用",
            )
            return {"success": False, "message": invalid_msg}

        # 5) 作废该用户的其他会话（重置密码后强制重新登录）
        await self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == int(user_id))
            .values(is_active=False)
        )
        await self.db.commit()

        await self._log_password_reset(
            user_id=int(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS,
            email=email,
            extra={"stage": "completed", "sessions_revoked": True},
        )

        return {"success": True, "message": "密码重置成功"}
    
    async def change_password(self, user_id: int, current_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        # 查找用户
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "message": "用户不存在"}
        
        # 验证当前密码
        if not password_service.verify_password(current_password, user.salt, user.password_hash):
            return {"success": False, "message": "当前密码错误"}
        
        # 验证新密码强度
        is_strong_password, password_error = password_service.validate_password_strength(new_password)
        if not is_strong_password:
            return {"success": False, "message": password_error or "密码强度不足"}
        
        # 检查新密码是否与当前密码相同
        if password_service.verify_password(new_password, user.salt, user.password_hash):
            return {"success": False, "message": "新密码不能与当前密码相同"}
        
        # 更新密码
        salt, password_hash = password_service.hash_password(new_password)
        user.password_hash = password_hash
        user.salt = salt
        user.password_updated_at = datetime.datetime.utcnow()
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
        
        return {"success": True, "message": "密码修改成功"}
    
    async def verify_email(self, token: str) -> Dict[str, Any]:
        """验证邮箱"""
        # 验证邮箱验证令牌
        payload = jwt_service.verify_token(token)
        if not payload or payload.get("type") != "email_verification":
            return {"success": False, "message": "无效或已过期的验证令牌"}
        
        user_id = payload.get("sub")
        if not user_id:
            return {"success": False, "message": "无效的验证令牌"}
        
        # 查找用户
        query = select(User).where(User.id == int(user_id))
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "message": "用户不存在"}
        
        if user.is_email_verified:
            return {"success": True, "message": "邮箱已经验证过了"}
        
        # 更新验证状态
        user.is_email_verified = True
        user.updated_at = datetime.datetime.utcnow()
        
        # 如果用户状态是待审核，可以考虑自动激活
        if user.status == UserStatus.PENDING:
            user.status = UserStatus.ACTIVE
        
        await self.db.commit()
        
        return {"success": True, "message": "邮箱验证成功"}
    
    async def generate_captcha(self) -> Dict[str, Any]:
        """生成验证码"""
        import secrets
        import base64
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # 生成验证码文本
        captcha_text = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(4))
        
        # 生成验证码key
        captcha_key = secrets.token_urlsafe(32)
        
        # 创建验证码图片
        img = Image.new('RGB', (120, 40), color='white')
        draw = ImageDraw.Draw(img)
        
        # 添加文字
        try:
            # 尝试使用默认字体
            font = ImageFont.load_default()
        except:
            font = None
            
        draw.text((10, 10), captcha_text, fill='black', font=font)
        
        # 添加干扰线
        for _ in range(3):
            x1, y1 = secrets.randbelow(120), secrets.randbelow(40)
            x2, y2 = secrets.randbelow(120), secrets.randbelow(40)
            draw.line([(x1, y1), (x2, y2)], fill='gray', width=1)
        
        # 转换为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # 存储验证码到Redis（这里简化处理，实际应该用Redis）
        # TODO: 使用Redis存储验证码
        
        return {
            "key": captcha_key,
            "image": f"data:image/png;base64,{img_base64}",
            "text": captcha_text  # 实际生产中不应该返回
        }

    async def _log_login_attempt(
        self,
        user_id: Optional[int],
        username: str,
        ip_address: str,
        user_agent: str,
        result: AuditResult,
        error_message: Optional[str] = None
    ) -> None:
        """记录登录尝试日志"""
        audit_log = AuditLog(
            user_id=user_id,
            action=AuditAction.LOGIN,
            resource_type="user",
            resource_id=username,
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
            error_message=error_message
        )
        
        self.db.add(audit_log)
        await self.db.commit()

    async def _log_password_reset(
        self,
        *,
        user_id: Optional[int],
        ip_address: Optional[str],
        user_agent: Optional[str],
        result: AuditResult,
        email: Optional[str] = None,
        error_message: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录密码重置流程的审计日志。

        复用 PASSWORD_CHANGE 动作枚举（避免新增 enum 成员触发 MySQL ENUM 变更），
        通过 extra_data.flow="password_reset" 与"修改密码"区分。
        """
        extra_data: Dict[str, Any] = {"flow": "password_reset"}
        if email:
            extra_data["email"] = email
        if extra:
            extra_data.update(extra)

        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=AuditAction.PASSWORD_CHANGE,
                resource_type="user",
                resource_id=str(user_id) if user_id else (email or ""),
                ip_address=ip_address,
                user_agent=user_agent,
                result=result,
                error_message=error_message,
                extra_data=extra_data,
            )
            self.db.add(audit_log)
            await self.db.commit()
        except Exception as e:
            logger.error("记录密码重置审计日志失败: %s", e)

# 导入认证依赖函数
from .auth_dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    get_optional_current_user
)
