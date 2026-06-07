"""
用户操作审计日志服务
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from ..models.audit import AuditLog, AuditAction, AuditResult
from ..models.user import User


class UserAuditService:
    """用户操作审计日志服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def log_user_login(
        self, 
        user_id: int, 
        ip_address: str, 
        user_agent: str,
        result: str = "SUCCESS",
        error_message: Optional[str] = None
    ):
        """记录用户登录日志"""
        await self._create_audit_log(
            user_id=user_id,
            action=AuditAction.LOGIN,
            resource_type="authentication",
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult(result),
            error_message=error_message
        )
    
    async def log_user_logout(
        self, 
        user_id: int, 
        ip_address: str, 
        user_agent: str
    ):
        """记录用户登出日志"""
        await self._create_audit_log(
            user_id=user_id,
            action=AuditAction.LOGOUT,
            resource_type="authentication",
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS
        )
    
    async def log_user_create(
        self,
        operator_user_id: int,
        target_user_id: int,
        user_data: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ):
        """记录用户创建日志"""
        # 移除敏感信息
        safe_data = {k: v for k, v in user_data.items() if k not in ['password', 'password_hash']}
        
        await self._create_audit_log(
            user_id=operator_user_id,
            action=AuditAction.CREATE,
            resource_type="user",
            resource_id=str(target_user_id),
            new_values=safe_data,
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS
        )
    
    async def log_user_update(
        self,
        operator_user_id: int,
        target_user_id: int,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ):
        """记录用户更新日志"""
        # 移除敏感信息
        safe_old = {k: v for k, v in old_values.items() if k not in ['password', 'password_hash', 'salt']}
        safe_new = {k: v for k, v in new_values.items() if k not in ['password', 'password_hash', 'salt']}
        
        await self._create_audit_log(
            user_id=operator_user_id,
            action=AuditAction.UPDATE,
            resource_type="user",
            resource_id=str(target_user_id),
            old_values=safe_old,
            new_values=safe_new,
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS
        )
    
    async def log_user_delete(
        self,
        operator_user_id: int,
        target_user_id: int,
        user_data: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ):
        """记录用户删除日志"""
        # 移除敏感信息
        safe_data = {k: v for k, v in user_data.items() if k not in ['password', 'password_hash', 'salt']}
        
        await self._create_audit_log(
            user_id=operator_user_id,
            action=AuditAction.DELETE,
            resource_type="user",
            resource_id=str(target_user_id),
            old_values=safe_data,
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS
        )
    
    async def log_password_change(
        self,
        user_id: int,
        ip_address: str,
        user_agent: str,
        initiated_by_admin: bool = False
    ):
        """记录密码修改日志"""
        extra_data = {"initiated_by_admin": initiated_by_admin}
        
        await self._create_audit_log(
            user_id=user_id,
            action=AuditAction.PASSWORD_CHANGE,
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS,
            extra_data=extra_data
        )
    
    async def log_mfa_enable(
        self,
        user_id: int,
        ip_address: str,
        user_agent: str
    ):
        """记录MFA启用日志"""
        await self._create_audit_log(
            user_id=user_id,
            action=AuditAction.MFA_ENABLE,
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS
        )
    
    async def log_mfa_disable(
        self,
        user_id: int,
        ip_address: str,
        user_agent: str
    ):
        """记录MFA禁用日志"""
        await self._create_audit_log(
            user_id=user_id,
            action=AuditAction.MFA_DISABLE,
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS
        )
    
    async def log_permission_change(
        self,
        operator_user_id: int,
        target_user_id: int,
        old_roles: List[str],
        new_roles: List[str],
        ip_address: str,
        user_agent: str
    ):
        """记录权限变更日志"""
        extra_data = {
            "old_roles": old_roles,
            "new_roles": new_roles,
            "added_roles": list(set(new_roles) - set(old_roles)),
            "removed_roles": list(set(old_roles) - set(new_roles))
        }
        
        await self._create_audit_log(
            user_id=operator_user_id,
            action=AuditAction.PERMISSION_CHANGE,
            resource_type="user",
            resource_id=str(target_user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult.SUCCESS,
            extra_data=extra_data
        )
    
    async def log_batch_operation(
        self,
        operator_user_id: int,
        operation_type: str,
        affected_users: List[int],
        operation_data: Dict[str, Any],
        ip_address: str,
        user_agent: str,
        result: str = "SUCCESS"
    ):
        """记录批量操作日志"""
        extra_data = {
            "operation_type": operation_type,
            "affected_users": affected_users,
            "affected_count": len(affected_users),
            "operation_data": operation_data
        }
        
        await self._create_audit_log(
            user_id=operator_user_id,
            action=AuditAction.BATCH_OPERATION,
            resource_type="user",
            ip_address=ip_address,
            user_agent=user_agent,
            result=AuditResult(result),
            extra_data=extra_data
        )
    
    async def get_user_audit_logs(
        self,
        user_id: Optional[int] = None,
        target_user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        size: int = 20
    ) -> Dict[str, Any]:
        """
        获取用户审计日志
        
        Args:
            user_id: 操作用户ID（谁执行的操作）
            target_user_id: 目标用户ID（被操作的用户）
            action: 操作类型
            resource_type: 资源类型
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            size: 页大小
        """
        query = self.db.query(AuditLog)
        
        # 构建过滤条件
        filters = []
        
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        
        if target_user_id:
            filters.append(AuditLog.resource_id == str(target_user_id))
        
        if action:
            filters.append(AuditLog.action == AuditAction(action))
        
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        
        if start_date:
            filters.append(AuditLog.created_at >= start_date)
        
        if end_date:
            filters.append(AuditLog.created_at <= end_date)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # 计算总数
        total = query.count()
        
        # 分页查询
        logs = (query.order_by(desc(AuditLog.created_at))
                .offset((page - 1) * size)
                .limit(size)
                .all())
        
        # 转换为字典格式
        log_list = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action.value if log.action else None,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "result": log.result.value if log.result else None,
                "error_message": log.error_message,
                "extra_data": log.extra_data,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            
            # 获取操作用户信息
            if log.user_id:
                user = self.db.query(User).filter(User.id == log.user_id).first()
                if user:
                    log_dict["user"] = {
                        "id": user.id,
                        "username": user.username,
                        "nickname": user.nickname or user.username
                    }
            
            log_list.append(log_dict)
        
        return {
            "logs": log_list,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    
    async def _create_audit_log(
        self,
        user_id: Optional[int],
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """创建审计日志记录"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
            error_message=error_message,
            extra_data=extra_data
        )
        
        self.db.add(audit_log)
        self.db.commit()
        
        return audit_log


# 全局用户审计服务实例
def get_user_audit_service(db: Session) -> UserAuditService:
    """获取用户审计服务实例"""
    return UserAuditService(db)