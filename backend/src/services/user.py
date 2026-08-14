"""
用户服务 - 提供用户CRUD操作和用户生命周期管理功能
"""
import datetime
import csv
import io
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, text, bindparam
from sqlalchemy.orm import selectinload
from ..models.user import User, UserStatus, UserRole
from ..models.role import Role
from ..utils.password import password_service
from ..core.config import get_settings

settings = get_settings()

class UserService:
    """用户管理服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_roles_for_user_ids(self, user_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        if not user_ids:
            return {}

        result = await self.db.execute(
            text("""
                SELECT ur.user_id, r.id, r.code, r.name, r.description, r.is_active,
                       r.is_system_role, r.sort_order, r.created_at, r.updated_at
                FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                WHERE ur.user_id IN :user_ids
                ORDER BY r.sort_order, r.id
            """).bindparams(bindparam("user_ids", expanding=True)),
            {"user_ids": tuple(user_ids)}
        )

        roles_by_user: Dict[int, List[Dict[str, Any]]] = {}
        for row in result.fetchall():
            roles_by_user.setdefault(row.user_id, []).append({
                "id": row.id,
                "code": row.code,
                "name": row.name,
                "description": row.description,
                "is_system_role": bool(row.is_system_role),
                "is_active": bool(row.is_active),
                "priority": row.sort_order or 0,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "sort_order": row.sort_order or 0,
            })
        return roles_by_user

    async def _attach_roles(self, users: List[User]) -> List[User]:
        roles_by_user = await self._get_roles_for_user_ids([user.id for user in users])
        for user in users:
            setattr(user, "_role_items", roles_by_user.get(user.id, []))
        return users
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """创建用户"""
        # 检查用户名和邮箱唯一性
        query = select(User).where(
            or_(
                User.username == user_data["username"],
                User.email == user_data["email"]
            )
        )
        result = await self.db.execute(query)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.username == user_data["username"]:
                raise ValueError("用户名已存在")
            else:
                raise ValueError("邮箱已存在")
        
        # 生成密码
        password = user_data.get("password")
        if not password:
            password = password_service.generate_password()
        
        # 验证密码强度
        is_valid, error_msg = password_service.validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 加密密码
        salt, password_hash = password_service.hash_password(password)
        
        # 创建用户
        new_user = User(
            username=user_data["username"],
            email=user_data["email"],
            password_hash=password_hash,
            salt=salt,
            nickname=user_data.get("nickname", user_data["username"]),
            phone=user_data.get("phone"),
            avatar=user_data.get("avatar"),
            status=UserStatus.ACTIVE,
            is_active=True,
            is_superuser=user_data.get("is_superuser", False),
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        role_ids = user_data.get("role_ids") or []
        role_codes = user_data.get("roles") or []
        if role_codes:
            role_result = await self.db.execute(
                text("SELECT id FROM roles WHERE code IN :role_codes").bindparams(bindparam("role_codes", expanding=True)),
                {"role_codes": tuple(role_codes)}
            )
            role_ids.extend([row.id for row in role_result.fetchall()])
        if role_ids:
            await self.assign_roles(new_user.id, role_ids)

        refreshed_user = await self.get_user_by_id(new_user.id)
        return refreshed_user or new_user
    
    async def get_users_paginated(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        status: Optional[str] = None,
        role: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """分页获取用户列表"""
        from ..models.user import UserStatus

        query = select(User)
        count_query = select(func.count(func.distinct(User.id)))

        # 默认排除软删除用户，除非显式请求 status=deleted
        if status and status.lower() == "deleted":
            status_enum = UserStatus.DELETED
            query = query.where(User.status == status_enum)
            count_query = count_query.where(User.status == status_enum)
        elif status:
            try:
                status_enum = UserStatus(status.lower())
                query = query.where(User.status == status_enum)
                count_query = count_query.where(User.status == status_enum)
            except ValueError:
                pass  # 忽略无效状态
        else:
            # 未指定状态时，默认排除已删除用户
            query = query.where(User.status != UserStatus.DELETED)
            count_query = count_query.where(User.status != UserStatus.DELETED)

        # 添加搜索条件
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.nickname.ilike(search_pattern)
                )
            )

        if role:
            query = query.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id)
            count_query = count_query.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id)
            role_value = role.strip()
            role_filter_items = [
                func.lower(Role.code) == role_value.lower(),
                func.lower(Role.name) == role_value.lower()
            ]
            if role_value.isdigit():
                role_filter_items.append(Role.id == int(role_value))
            role_filter = or_(*role_filter_items)
            query = query.where(role_filter)
            count_query = count_query.where(role_filter)

        # 添加排序
        if hasattr(User, sort_by):
            order_column = getattr(User, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())

        # 获取总数
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.nickname.ilike(search_pattern)
                )
            )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 添加分页
        query = query.offset(skip).limit(limit)
        
        # 执行查询
        result = await self.db.execute(query)
        users = result.scalars().unique().all()
        await self._attach_roles(users)
        
        return {
            "users": users,
            "total": total
        }
    
    async def lock_user(self, user_id: int, reason: Optional[str] = None) -> None:
        """锁定用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        from ..models.user import UserStatus
        user.status = UserStatus.LOCKED
        user.is_active = False
        user.locked_until = None  # 永久锁定，直到手动解锁
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
    
    async def unlock_user(self, user_id: int) -> None:
        """解锁用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        from ..models.user import UserStatus
        user.status = UserStatus.ACTIVE
        user.is_active = True
        user.locked_until = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
    
    async def reset_password(self, user_id: int, new_password: str, force_change: bool = True) -> None:
        """重置用户密码"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        # 验证密码强度
        is_valid, error_msg = password_service.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 加密新密码
        salt, password_hash = password_service.hash_password(new_password)
        
        user.password_hash = password_hash
        user.salt = salt
        user.password_updated_at = datetime.datetime.utcnow()
        user.updated_at = datetime.datetime.utcnow()
        
        # TODO: 如果force_change为True，设置强制修改密码标志
        
        await self.db.commit()
    
    async def get_user_permissions(self, user_id: int) -> Dict[str, Any]:
        """获取用户权限"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        roles = getattr(user, "_role_items", []) or []
        role_ids = [role["id"] for role in roles]

        permissions = []
        if role_ids:
            permission_result = await self.db.execute(
                text("""
                    SELECT DISTINCT p.code, p.name, p.is_active
                    FROM role_permissions rp
                    JOIN permissions p ON p.id = rp.permission_id
                    WHERE rp.role_id IN :role_ids
                """).bindparams(bindparam("role_ids", expanding=True)),
                {"role_ids": tuple(role_ids)}
            )
            permissions = sorted({
                row.code or row.name
                for row in permission_result.fetchall()
                if row.is_active
            })

        return {
            "roles": roles,
            "permissions": permissions
        }
    
    async def assign_roles(self, user_id: int, role_ids: List[int]) -> Dict[str, Any]:
        """为用户分配角色"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        normalized_role_ids = sorted({int(role_id) for role_id in role_ids if role_id})
        await self.db.execute(delete(UserRole).where(UserRole.user_id == user_id))

        failed_roles = []
        assigned_count = 0
        if normalized_role_ids:
            role_result = await self.db.execute(
                text("SELECT id FROM roles WHERE id IN :role_ids").bindparams(bindparam("role_ids", expanding=True)),
                {"role_ids": tuple(normalized_role_ids)}
            )
            existing_role_ids = {row.id for row in role_result.fetchall()}
            for role_id in normalized_role_ids:
                if role_id not in existing_role_ids:
                    failed_roles.append({"role_id": role_id, "error": "角色不存在"})
                    continue
                self.db.add(UserRole(user_id=user_id, role_id=role_id))
                assigned_count += 1

        user.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
        return {
            "assigned_count": assigned_count,
            "failed_roles": failed_roles
        }
    
    async def remove_role(self, user_id: int, role_id: int) -> None:
        """移除用户角色"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        await self.db.execute(
            delete(UserRole).where(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id
                )
            )
        )
        user.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
    
    async def batch_operation(
        self,
        user_ids: List[int],
        action: str,
        role_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """批量操作用户"""
        success_count = 0
        failed_count = 0
        failed_users = []
        
        for user_id in user_ids:
            try:
                if action == "activate":
                    await self.unlock_user(user_id)
                elif action == "deactivate":
                    await self.lock_user(user_id, reason)
                elif action == "delete":
                    await self.delete_user(user_id)
                elif action == "assign_role" and role_id:
                    await self.assign_roles(user_id, [role_id])
                elif action == "remove_role" and role_id:
                    await self.remove_role(user_id, role_id)
                
                success_count += 1
            except Exception as e:
                failed_count += 1
                user = await self.get_user_by_id(user_id)
                failed_users.append({
                    "user_id": str(user_id),
                    "username": user.username if user else "未知",
                    "error": str(e)
                })
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total_count": len(user_ids),
            "failed_users": failed_users,
            "message": f"批量操作完成：成功 {success_count} 个，失败 {failed_count} 个"
        }
    
    async def export_users(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[User]:
        """导出用户数据"""
        query = select(User)
        
        # 添加筛选条件
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.nickname.ilike(search_pattern)
                )
            )
        
        if status:
            from ..models.user import UserStatus
            try:
                status_enum = UserStatus(status.lower())
                query = query.where(User.status == status_enum)
            except ValueError:
                pass
        
        if role:
            query = query.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id)
            role_value = role.strip()
            role_filter_items = [
                func.lower(Role.code) == role_value.lower(),
                func.lower(Role.name) == role_value.lower()
            ]
            if role_value.isdigit():
                role_filter_items.append(Role.id == int(role_value))
            query = query.where(or_(*role_filter_items))
        
        result = await self.db.execute(query)
        users = result.scalars().unique().all()
        await self._attach_roles(users)
        return users
    
    async def import_users(self, content: bytes, filename: str) -> Dict[str, Any]:
        """导入用户数据"""
        rows = []
        lower_filename = filename.lower()
        if lower_filename.endswith(".csv"):
            text = content.decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(text)))
        elif lower_filename.endswith(".xlsx"):
            from openpyxl import load_workbook

            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            sheet = workbook.active
            headers = [str(cell or "").strip() for cell in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))]
            for values in sheet.iter_rows(min_row=2, values_only=True):
                rows.append({headers[index]: values[index] for index in range(len(headers)) if headers[index]})
        else:
            raise ValueError("只支持 CSV、XLSX 文件")

        success_count = 0
        failed_users = []

        for index, row in enumerate(rows, start=2):
            username = str(row.get("username") or "").strip()
            email = str(row.get("email") or "").strip()
            password = str(row.get("password") or "").strip()
            nickname = str(row.get("nickname") or "").strip() or None
            phone = str(row.get("phone") or "").strip() or None
            role_codes = [
                code.strip()
                for code in str(row.get("role_codes") or row.get("roles") or "").split(",")
                if code.strip()
            ]

            try:
                if not username or not email or not password:
                    raise ValueError("username、email、password 为必填列")

                await self.create_user({
                    "username": username,
                    "email": email,
                    "password": password,
                    "nickname": nickname,
                    "phone": phone,
                    "roles": role_codes,
                    "is_active": True,
                })
                success_count += 1
            except Exception as e:
                failed_users.append({
                    "row": index,
                    "username": username,
                    "email": email,
                    "error": str(e)
                })

        failed_count = len(failed_users)
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total_count": len(rows),
            "failed_users": failed_users
        }
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        from ..models.user import UserStatus
        
        # 总用户数
        total_query = select(func.count(User.id))
        total_result = await self.db.execute(total_query)
        total_users = total_result.scalar()
        
        # 按状态统计
        status_stats = {}
        for status in UserStatus:
            status_query = select(func.count(User.id)).where(User.status == status)
            status_result = await self.db.execute(status_query)
            status_stats[status.value] = status_result.scalar()
        
        # 今日新增用户
        today = datetime.datetime.utcnow().date()
        today_query = select(func.count(User.id)).where(
            func.date(User.created_at) == today
        )
        today_result = await self.db.execute(today_query)
        new_users_today = today_result.scalar()
        
        # 本周新增用户
        week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        week_query = select(func.count(User.id)).where(
            User.created_at >= week_ago
        )
        week_result = await self.db.execute(week_query)
        new_users_this_week = week_result.scalar()
        
        # 本月新增用户
        month_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        month_query = select(func.count(User.id)).where(
            User.created_at >= month_ago
        )
        month_result = await self.db.execute(month_query)
        new_users_this_month = month_result.scalar()
        
        # 最近登录统计
        recent_login_query = select(func.count(User.id)).where(
            User.last_login_at >= datetime.datetime.utcnow() - datetime.timedelta(days=30)
        )
        recent_login_result = await self.db.execute(recent_login_query)
        recent_active_users = recent_login_result.scalar()
        
        return {
            "total_users": total_users,
            "status_statistics": status_stats,
            "new_users_today": new_users_today,
            "new_users_this_week": new_users_this_week,
            "new_users_this_month": new_users_this_month,
            "recent_active_users": recent_active_users,
            "inactive_users": total_users - recent_active_users
        }
    
    async def search_users_advanced(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """高级用户搜索"""
        query = select(User)
        
        # 基本搜索
        if filters.get("search"):
            search_pattern = f"%{filters['search']}%"
            query = query.where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.nickname.ilike(search_pattern),
                    User.phone.ilike(search_pattern)
                )
            )
        
        # 状态筛选
        if filters.get("status"):
            from ..models.user import UserStatus
            try:
                status_enum = UserStatus(filters["status"])
                query = query.where(User.status == status_enum)
            except ValueError:
                pass
        
        # 创建时间范围
        if filters.get("created_after"):
            query = query.where(User.created_at >= filters["created_after"])
        if filters.get("created_before"):
            query = query.where(User.created_at <= filters["created_before"])
        
        # 最后登录时间范围
        if filters.get("last_login_after"):
            query = query.where(User.last_login_at >= filters["last_login_after"])
        if filters.get("last_login_before"):
            query = query.where(User.last_login_at <= filters["last_login_before"])
        
        # 是否激活
        if filters.get("is_active") is not None:
            query = query.where(User.is_active == filters["is_active"])
        
        # 是否超级用户
        if filters.get("is_superuser") is not None:
            query = query.where(User.is_superuser == filters["is_superuser"])
        
        # 邮箱验证状态
        if filters.get("is_email_verified") is not None:
            query = query.where(User.is_email_verified == filters["is_email_verified"])
        
        # 手机验证状态
        if filters.get("is_phone_verified") is not None:
            query = query.where(User.is_phone_verified == filters["is_phone_verified"])
        
        # MFA启用状态
        if filters.get("mfa_enabled") is not None:
            query = query.where(User.mfa_enabled == filters["mfa_enabled"])
        
        # 获取总数
        count_query = select(func.count(User.id))
        # 应用相同的筛选条件到计数查询
        # ... (省略重复代码)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 排序和分页
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        return {
            "users": users,
            "total": total,
            "filters_applied": filters
        }
    
    async def get_user_activity_log(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户活动日志"""
        from ..models.audit import AuditLog
        
        query = select(AuditLog).where(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.created_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        activity_logs = []
        for log in logs:
            activity_logs.append({
                "id": log.id,
                "action": log.action.value,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "result": log.result.value,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        return activity_logs
    
    async def update_user_profile(self, user_id: int, profile_data: Dict[str, Any]) -> Optional[User]:
        """更新用户个人资料"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        # 允许更新的个人资料字段
        allowed_fields = [
            "nickname", "bio", "gender", "birthday", "location", "website",
            "avatar", "language", "timezone", "theme", "email_notifications",
            "sms_notifications", "push_notifications"
        ]
        
        # 更新字段
        for key, value in profile_data.items():
            if key in allowed_fields and hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def change_user_password(
        self, 
        user_id: int, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """用户修改密码"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        # 验证当前密码
        if not password_service.verify_password(current_password, user.salt, user.password_hash):
            raise ValueError("当前密码错误")
        
        # 验证新密码强度
        is_valid, error_msg = password_service.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 检查新密码是否与当前密码相同
        if password_service.verify_password(new_password, user.salt, user.password_hash):
            raise ValueError("新密码不能与当前密码相同")
        
        # 更新密码
        salt, password_hash = password_service.hash_password(new_password)
        user.password_hash = password_hash
        user.salt = salt
        user.password_updated_at = datetime.datetime.utcnow()
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
        
        return True
    
    async def enable_user_mfa(self, user_id: int) -> Dict[str, Any]:
        """启用用户多因素认证"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        if user.mfa_enabled:
            raise ValueError("多因素认证已启用")
        
        # 生成MFA密钥
        import pyotp
        import qrcode
        import io
        import base64
        
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        # 生成二维码
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.PROJECT_NAME
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # 生成备用代码
        backup_codes = [pyotp.random_base32()[:8] for _ in range(10)]
        
        # 保存MFA配置（暂时不启用，等待验证）
        user.mfa_secret = secret
        user.mfa_backup_codes = ",".join(backup_codes)
        await self.db.commit()
        
        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "backup_codes": backup_codes,
            "provisioning_uri": provisioning_uri
        }
    
    async def verify_and_enable_mfa(self, user_id: int, verification_code: str) -> bool:
        """验证并启用MFA"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        if not user.mfa_secret:
            raise ValueError("MFA未初始化")
        
        # 验证代码
        import pyotp
        totp = pyotp.TOTP(user.mfa_secret)
        
        if not totp.verify(verification_code):
            raise ValueError("验证码错误")
        
        # 启用MFA
        user.mfa_enabled = True
        user.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
        
        return True
    
    async def disable_user_mfa(self, user_id: int, verification_code: str) -> bool:
        """禁用用户多因素认证"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")
        
        if not user.mfa_enabled:
            raise ValueError("多因素认证未启用")
        
        # 验证代码
        import pyotp
        totp = pyotp.TOTP(user.mfa_secret)
        
        if not totp.verify(verification_code):
            raise ValueError("验证码错误")
        
        # 禁用MFA
        user.mfa_enabled = False
        user.mfa_secret = None
        user.mfa_backup_codes = None
        user.updated_at = datetime.datetime.utcnow()
        await self.db.commit()
        
        return True
    
    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户会话列表"""
        from ..models.user import UserSession
        
        query = select(UserSession).where(
            UserSession.user_id == user_id
        ).order_by(UserSession.created_at.desc())
        
        result = await self.db.execute(query)
        sessions = result.scalars().all()
        
        session_list = []
        for session in sessions:
            session_list.append({
                "id": session.id,
                "device_info": session.device_info,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_activity": session.last_activity.isoformat() if session.last_activity else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None
            })
        
        return session_list
    
    async def revoke_user_session(self, user_id: int, session_id: int) -> bool:
        """撤销用户会话"""
        from ..models.user import UserSession
        
        query = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.id == session_id
            )
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            return False
        
        session.is_active = False
        await self.db.commit()
        
        return True
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if user:
            await self._attach_roles([user])
        return user
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        query = select(User).where(User.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        status: Optional[UserStatus] = None,
        role_id: Optional[int] = None
    ) -> List[User]:
        """获取用户列表"""
        query = select(User).options(selectinload(User.roles))
        
        # 添加搜索条件
        if search:
            query = query.where(
                or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.nickname.contains(search)
                )
            )
        
        # 添加状态筛选
        if status:
            query = query.where(User.status == status)
        
        # 添加角色筛选
        if role_id:
            query = query.join(UserRole).where(UserRole.role_id == role_id)
        
        # 排序和分页
        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_users_count(
        self,
        search: Optional[str] = None,
        status: Optional[UserStatus] = None,
        role_id: Optional[int] = None
    ) -> int:
        """获取用户总数"""
        query = select(func.count(User.id))
        
        # 添加搜索条件
        if search:
            query = query.where(
                or_(
                    User.username.contains(search),
                    User.email.contains(search),
                    User.nickname.contains(search)
                )
            )
        
        # 添加状态筛选
        if status:
            query = query.where(User.status == status)
        
        # 添加角色筛选
        if role_id:
            query = query.join(UserRole).where(UserRole.role_id == role_id)
        
        result = await self.db.execute(query)
        return result.scalar()
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> User:
        """更新用户信息"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError("用户不存在")

        role_ids = update_data.pop("role_ids", None)
        
        # 检查用户名和邮箱唯一性（如果有更新）
        if "username" in update_data or "email" in update_data:
            query = select(User).where(
                and_(
                    User.id != user_id,
                    or_(
                        User.username == update_data.get("username", user.username),
                        User.email == update_data.get("email", user.email)
                    )
                )
            )
            result = await self.db.execute(query)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                if existing_user.username == update_data.get("username"):
                    raise ValueError("用户名已存在")
                else:
                    raise ValueError("邮箱已存在")
        
        # 更新字段
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        if "is_active" in update_data:
            user.status = UserStatus.ACTIVE if update_data["is_active"] else UserStatus.DISABLED
        
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)

        if role_ids is not None:
            await self.assign_roles(user_id, role_ids)
            refreshed_user = await self.get_user_by_id(user_id)
            return refreshed_user or user
        
        return user
    
    async def delete_user(self, user_id: int, soft_delete: bool = True) -> bool:
        """删除用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if soft_delete:
            # 软删除
            user.status = UserStatus.DELETED
            user.is_active = False
            user.deleted_at = datetime.datetime.utcnow()
            user.updated_at = datetime.datetime.utcnow()
            await self.db.commit()
        else:
            # 硬删除
            await self.db.delete(user)
            await self.db.commit()
        
        return True
    
    async def activate_user(self, user_id: int) -> bool:
        """激活用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.status = UserStatus.ACTIVE
        user.is_active = True
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def deactivate_user(self, user_id: int) -> bool:
        """停用用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.status = UserStatus.DISABLED
        user.is_active = False
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def change_password(
        self, 
        user_id: int, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """修改密码"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # 验证当前密码
        if not password_service.verify_password(current_password, user.salt, user.password_hash):
            raise ValueError("当前密码错误")
        
        # 验证新密码强度
        is_valid, error_msg = password_service.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 更新密码
        salt, password_hash = password_service.hash_password(new_password)
        user.salt = salt
        user.password_hash = password_hash
        user.password_updated_at = datetime.datetime.utcnow()
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def reset_password_legacy(self, user_id: int, new_password: str) -> bool:
        """重置密码（管理员操作）"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # 验证新密码强度
        is_valid, error_msg = password_service.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 更新密码
        salt, password_hash = password_service.hash_password(new_password)
        user.salt = salt
        user.password_hash = password_hash
        user.password_updated_at = datetime.datetime.utcnow()
        user.updated_at = datetime.datetime.utcnow()
        
        await self.db.commit()
        return True
