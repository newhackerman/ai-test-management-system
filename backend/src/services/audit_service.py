"""
审计服务

提供安全事件和操作审计功能，包括：
- 安全事件记录
- 操作日志记录
- 审计查询和分析
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ..models.audit import AuditLog, SecurityEvent

logger = logging.getLogger(__name__)


class AuditService:
    """审计服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_operation(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        action: Optional[str] = None,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
        result: str = "SUCCESS",
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        event_category: str = "GENERAL",
        event_level: str = "INFO"
    ) -> AuditLog:
        """记录操作日志"""
        try:
            audit_log = AuditLog(
                event_type=event_type,
                event_category=event_category,
                event_level=event_level,
                user_id=user_id,
                username=username,
                user_ip=user_ip,
                user_agent=user_agent,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_name=resource_name,
                action=action,
                method=method,
                endpoint=endpoint,
                result=result,
                status_code=status_code,
                error_message=error_message,
                request_data=request_data,
                response_data=response_data,
                details=details,
                session_id=session_id,
                request_id=request_id,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow()
            )
            
            self.db.add(audit_log)
            await self.db.commit()
            await self.db.refresh(audit_log)
            
            logger.info(f"审计日志记录成功: {event_type} - {action}")
            return audit_log
            
        except Exception as e:
            logger.error(f"记录审计日志失败: {str(e)}")
            await self.db.rollback()
            raise
    
    async def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        user_ip: Optional[str] = None,
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "LOW",
        risk_score: int = 0,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None
    ) -> SecurityEvent:
        """记录安全事件"""
        try:
            # 构建事件描述
            if not description:
                description = f"安全事件: {event_type}"
                if action:
                    description += f" - {action}"
                if result:
                    description += f" ({result})"
            
            # 构建详细信息
            event_details = details or {}
            event_details.update({
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            security_event = SecurityEvent(
                event_type=event_type,
                severity=severity,
                status="OPEN",
                user_id=user_id,
                username=username,
                user_ip=user_ip,
                description=description,
                details=event_details,
                risk_score=risk_score,
                timestamp=datetime.utcnow()
            )
            
            self.db.add(security_event)
            await self.db.commit()
            await self.db.refresh(security_event)
            
            logger.warning(f"安全事件记录: {event_type} - 严重程度: {severity}")
            
            # 高风险事件需要立即通知
            if severity in ["HIGH", "CRITICAL"]:
                await self._notify_security_team(security_event)
            
            return security_event
            
        except Exception as e:
            logger.error(f"记录安全事件失败: {str(e)}")
            await self.db.rollback()
            raise
    
    async def log_project_operation(
        self,
        project_id: int,
        operation: str,
        user_id: int,
        username: str,
        details: Optional[Dict[str, Any]] = None,
        result: str = "SUCCESS",
        user_ip: Optional[str] = None
    ) -> AuditLog:
        """记录项目操作日志"""
        return await self.log_operation(
            event_type="PROJECT_OPERATION",
            event_category="PROJECT",
            user_id=user_id,
            username=username,
            resource_type="project",
            resource_id=str(project_id),
            action=operation,
            result=result,
            details=details,
            user_ip=user_ip
        )
    
    async def log_permission_check(
        self,
        user_id: int,
        permission: str,
        resource_type: str,
        resource_id: str,
        granted: bool,
        reason: Optional[str] = None,
        user_ip: Optional[str] = None
    ) -> AuditLog:
        """记录权限检查日志"""
        return await self.log_operation(
            event_type="PERMISSION_CHECK",
            event_category="SECURITY",
            event_level="DEBUG",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=permission,
            result="GRANTED" if granted else "DENIED",
            details={
                "permission": permission,
                "granted": granted,
                "reason": reason
            },
            user_ip=user_ip
        )
    
    async def log_authentication_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """记录认证事件日志"""
        return await self.log_operation(
            event_type=event_type,
            event_category="AUTHENTICATION",
            user_id=user_id,
            username=username,
            action="AUTHENTICATE",
            result=result,
            details=details,
            user_ip=user_ip,
            user_agent=user_agent
        )
    
    async def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """查询审计日志"""
        query = select(AuditLog)
        
        conditions = []
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if resource_id:
            conditions.append(AuditLog.resource_id == resource_id)
        if event_type:
            conditions.append(AuditLog.event_type == event_type)
        if start_time:
            conditions.append(AuditLog.timestamp >= start_time)
        if end_time:
            conditions.append(AuditLog.timestamp <= end_time)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_security_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SecurityEvent]:
        """查询安全事件"""
        query = select(SecurityEvent)
        
        conditions = []
        if event_type:
            conditions.append(SecurityEvent.event_type == event_type)
        if severity:
            conditions.append(SecurityEvent.severity == severity)
        if status:
            conditions.append(SecurityEvent.status == status)
        if user_id:
            conditions.append(SecurityEvent.user_id == user_id)
        if start_time:
            conditions.append(SecurityEvent.timestamp >= start_time)
        if end_time:
            conditions.append(SecurityEvent.timestamp <= end_time)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(SecurityEvent.timestamp.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_audit_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取审计统计信息"""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=30)
        if not end_time:
            end_time = datetime.utcnow()
        
        # 总日志数
        total_query = select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.timestamp >= start_time,
                AuditLog.timestamp <= end_time
            )
        )
        total_result = await self.db.execute(total_query)
        total_logs = total_result.scalar()
        
        # 按事件类型统计
        event_type_query = select(
            AuditLog.event_type,
            func.count(AuditLog.id).label("count")
        ).where(
            and_(
                AuditLog.timestamp >= start_time,
                AuditLog.timestamp <= end_time
            )
        ).group_by(AuditLog.event_type)
        
        event_type_result = await self.db.execute(event_type_query)
        event_type_stats = {row.event_type: row.count for row in event_type_result}
        
        # 按用户统计
        user_query = select(
            AuditLog.user_id,
            AuditLog.username,
            func.count(AuditLog.id).label("count")
        ).where(
            and_(
                AuditLog.timestamp >= start_time,
                AuditLog.timestamp <= end_time,
                AuditLog.user_id.isnot(None)
            )
        ).group_by(AuditLog.user_id, AuditLog.username).order_by(func.count(AuditLog.id).desc()).limit(10)
        
        user_result = await self.db.execute(user_query)
        user_stats = [
            {"user_id": row.user_id, "username": row.username, "count": row.count}
            for row in user_result
        ]
        
        # 安全事件统计
        security_query = select(func.count(SecurityEvent.id)).where(
            and_(
                SecurityEvent.timestamp >= start_time,
                SecurityEvent.timestamp <= end_time
            )
        )
        security_result = await self.db.execute(security_query)
        security_events = security_result.scalar()
        
        return {
            "period": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            "total_logs": total_logs,
            "security_events": security_events,
            "event_type_statistics": event_type_stats,
            "top_users": user_stats
        }
    
    async def cleanup_old_logs(self, days: int = 90) -> int:
        """清理旧的审计日志"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 删除旧的审计日志
        audit_query = select(AuditLog).where(AuditLog.timestamp < cutoff_date)
        audit_result = await self.db.execute(audit_query)
        old_logs = audit_result.scalars().all()
        
        count = 0
        for log in old_logs:
            await self.db.delete(log)
            count += 1
        
        await self.db.commit()
        
        logger.info(f"清理了 {count} 条旧审计日志")
        return count
    
    async def _notify_security_team(self, security_event: SecurityEvent):
        """通知安全团队（高风险事件）"""
        # 这里可以集成邮件、短信、钉钉等通知方式
        logger.critical(
            f"高风险安全事件: {security_event.event_type} - "
            f"用户: {security_event.username} - "
            f"风险评分: {security_event.risk_score}"
        )
        
        # TODO: 实现实际的通知逻辑
        pass


# 创建审计服务实例
audit_service = AuditService