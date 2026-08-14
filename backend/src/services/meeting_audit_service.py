"""
会议审计服务

提供会议相关的审计功能，包括：
- 访问控制审计
- 用户操作记录
- 异常访问监控
- 审计日志管理
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, BigInteger, String, Text, DateTime, JSON, Enum as SQLEnum, Boolean, Integer
from sqlalchemy.orm import Session

from ..models.base import BaseModel
from ..core.database import get_async_session, get_async_session_ctx
from ..utils.security_utils import SecurityUtils
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """审计事件类型"""
    # 会议访问事件
    MEETING_JOIN = "MEETING_JOIN"
    MEETING_LEAVE = "MEETING_LEAVE"
    MEETING_CREATE = "MEETING_CREATE"
    MEETING_UPDATE = "MEETING_UPDATE"
    MEETING_DELETE = "MEETING_DELETE"
    MEETING_START = "MEETING_START"
    MEETING_END = "MEETING_END"
    
    # 权限相关事件
    PERMISSION_GRANT = "PERMISSION_GRANT"
    PERMISSION_REVOKE = "PERMISSION_REVOKE"
    ROLE_CHANGE = "ROLE_CHANGE"
    ACCESS_DENIED = "ACCESS_DENIED"
    
    # 录制相关事件
    RECORDING_START = "RECORDING_START"
    RECORDING_STOP = "RECORDING_STOP"
    RECORDING_ACCESS = "RECORDING_ACCESS"
    RECORDING_DOWNLOAD = "RECORDING_DOWNLOAD"
    RECORDING_DELETE = "RECORDING_DELETE"
    
    # 文件操作事件
    FILE_UPLOAD = "FILE_UPLOAD"
    FILE_DOWNLOAD = "FILE_DOWNLOAD"
    FILE_DELETE = "FILE_DELETE"
    FILE_SHARE = "FILE_SHARE"
    
    # 安全事件
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    TOKEN_VALIDATION_FAILURE = "TOKEN_VALIDATION_FAILURE"
    
    # 系统事件
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"


class AuditSeverity(Enum):
    """审计严重级别"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MeetingAuditLog(BaseModel):
    """会议审计日志模型"""
    __tablename__ = 'meeting_audit_logs'
    
    # 基本信息
    event_type = Column(SQLEnum(AuditEventType), nullable=False, index=True, comment='事件类型')
    severity = Column(SQLEnum(AuditSeverity), default=AuditSeverity.LOW, nullable=False, index=True, comment='严重级别')
    
    # 关联信息
    meeting_id = Column(BigInteger, index=True, comment='会议ID')
    user_id = Column(BigInteger, index=True, comment='用户ID')
    session_id = Column(String(100), index=True, comment='会话ID')
    
    # 事件详情
    event_description = Column(Text, nullable=False, comment='事件描述')
    event_details = Column(JSON, comment='事件详细信息')
    
    # 网络信息
    ip_address = Column(String(45), index=True, comment='IP地址')
    user_agent = Column(Text, comment='用户代理')
    
    # 结果信息
    success = Column(Boolean, default=True, comment='操作是否成功')
    error_message = Column(Text, comment='错误信息')
    
    # 时间信息
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment='事件时间')
    
    # 附加信息
    additional_data = Column(JSON, comment='附加数据')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'event_type': self.event_type.value if self.event_type else None,
            'severity': self.severity.value if self.severity else None,
            'meeting_id': self.meeting_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'event_description': self.event_description,
            'event_details': self.event_details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'success': self.success,
            'error_message': self.error_message,
            'event_timestamp': self.event_timestamp.isoformat() if self.event_timestamp else None,
            'additional_data': self.additional_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }
    
    def __repr__(self):
        return f"<MeetingAuditLog(id={self.id}, event_type='{self.event_type}', meeting_id={self.meeting_id})>"


class MeetingAuditService:
    """会议审计服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.security_utils = SecurityUtils()
        
        # 异常检测配置
        self.anomaly_thresholds = {
            'max_failed_logins_per_hour': 10,
            'max_meetings_per_user_per_day': 50,
            'max_file_uploads_per_meeting': 100,
            'max_recording_access_per_hour': 20
        }
    
    # 1. 审计日志记录
    
    async def log_audit_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[int] = None,
        meeting_id: Optional[int] = None,
        session_id: Optional[str] = None,
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> MeetingAuditLog:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            meeting_id: 会议ID
            session_id: 会话ID
            description: 事件描述
            details: 事件详情
            ip_address: IP地址
            user_agent: 用户代理
            success: 操作是否成功
            error_message: 错误信息
            severity: 严重级别
            additional_data: 附加数据
            
        Returns:
            审计日志记录
        """
        try:
            async with get_async_session_ctx() as db:
                # 创建审计日志记录
                audit_log = MeetingAuditLog(
                    event_type=event_type,
                    severity=severity,
                    meeting_id=meeting_id,
                    user_id=user_id,
                    session_id=session_id,
                    event_description=description,
                    event_details=details,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=success,
                    error_message=error_message,
                    additional_data=additional_data,
                    created_by=user_id
                )
                
                db.add(audit_log)
                await db.commit()
                await db.refresh(audit_log)
                
                # 异步检测异常行为
                await self._detect_anomalies(audit_log)
                
                logger.info(f"记录审计事件: {event_type.value} - {description}")
                return audit_log
                
        except Exception as e:
            logger.error(f"记录审计事件失败: {str(e)}")
            raise
    
    # 2. 会议访问审计
    
    async def log_meeting_join(
        self,
        meeting_id: int,
        user_id: int,
        session_id: str,
        ip_address: str,
        user_agent: str,
        join_method: str = "web",
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """记录会议加入事件"""
        await self.log_audit_event(
            event_type=AuditEventType.MEETING_JOIN,
            user_id=user_id,
            meeting_id=meeting_id,
            session_id=session_id,
            description=f"用户 {user_id} 加入会议 {meeting_id}",
            details={
                'join_method': join_method,
                'timestamp': datetime.utcnow().isoformat()
            },
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            severity=AuditSeverity.LOW if success else AuditSeverity.MEDIUM
        )
    
    async def log_meeting_leave(
        self,
        meeting_id: int,
        user_id: int,
        session_id: str,
        duration_minutes: int,
        leave_reason: str = "normal"
    ):
        """记录会议离开事件"""
        await self.log_audit_event(
            event_type=AuditEventType.MEETING_LEAVE,
            user_id=user_id,
            meeting_id=meeting_id,
            session_id=session_id,
            description=f"用户 {user_id} 离开会议 {meeting_id}",
            details={
                'duration_minutes': duration_minutes,
                'leave_reason': leave_reason,
                'timestamp': datetime.utcnow().isoformat()
            },
            severity=AuditSeverity.LOW
        )
    
    async def log_access_denied(
        self,
        meeting_id: int,
        user_id: int,
        reason: str,
        ip_address: str,
        user_agent: str
    ):
        """记录访问拒绝事件"""
        await self.log_audit_event(
            event_type=AuditEventType.ACCESS_DENIED,
            user_id=user_id,
            meeting_id=meeting_id,
            description=f"用户 {user_id} 访问会议 {meeting_id} 被拒绝",
            details={
                'denial_reason': reason,
                'timestamp': datetime.utcnow().isoformat()
            },
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=reason,
            severity=AuditSeverity.MEDIUM
        )
    
    # 3. 权限变更审计
    
    async def log_permission_change(
        self,
        meeting_id: int,
        target_user_id: int,
        operator_user_id: int,
        permission_type: str,
        action: str,  # grant, revoke
        old_value: Any,
        new_value: Any
    ):
        """记录权限变更事件"""
        await self.log_audit_event(
            event_type=AuditEventType.PERMISSION_GRANT if action == 'grant' else AuditEventType.PERMISSION_REVOKE,
            user_id=operator_user_id,
            meeting_id=meeting_id,
            description=f"用户 {operator_user_id} {action} 用户 {target_user_id} 的 {permission_type} 权限",
            details={
                'target_user_id': target_user_id,
                'permission_type': permission_type,
                'action': action,
                'old_value': old_value,
                'new_value': new_value,
                'timestamp': datetime.utcnow().isoformat()
            },
            severity=AuditSeverity.MEDIUM
        )
    
    async def log_role_change(
        self,
        meeting_id: int,
        target_user_id: int,
        operator_user_id: int,
        old_role: str,
        new_role: str
    ):
        """记录角色变更事件"""
        await self.log_audit_event(
            event_type=AuditEventType.ROLE_CHANGE,
            user_id=operator_user_id,
            meeting_id=meeting_id,
            description=f"用户 {operator_user_id} 将用户 {target_user_id} 的角色从 {old_role} 变更为 {new_role}",
            details={
                'target_user_id': target_user_id,
                'old_role': old_role,
                'new_role': new_role,
                'timestamp': datetime.utcnow().isoformat()
            },
            severity=AuditSeverity.MEDIUM
        )
    
    # 4. 录制操作审计
    
    async def log_recording_operation(
        self,
        meeting_id: int,
        user_id: int,
        operation: str,  # start, stop, access, download, delete
        recording_id: Optional[int] = None,
        file_name: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """记录录制操作事件"""
        event_type_map = {
            'start': AuditEventType.RECORDING_START,
            'stop': AuditEventType.RECORDING_STOP,
            'access': AuditEventType.RECORDING_ACCESS,
            'download': AuditEventType.RECORDING_DOWNLOAD,
            'delete': AuditEventType.RECORDING_DELETE
        }
        
        await self.log_audit_event(
            event_type=event_type_map.get(operation, AuditEventType.RECORDING_ACCESS),
            user_id=user_id,
            meeting_id=meeting_id,
            description=f"用户 {user_id} {operation} 会议 {meeting_id} 的录制",
            details={
                'operation': operation,
                'recording_id': recording_id,
                'file_name': file_name,
                'timestamp': datetime.utcnow().isoformat()
            },
            ip_address=ip_address,
            severity=AuditSeverity.MEDIUM if operation in ['delete'] else AuditSeverity.LOW
        )
    
    # 5. 文件操作审计
    
    async def log_file_operation(
        self,
        meeting_id: int,
        user_id: int,
        operation: str,  # upload, download, delete, share
        file_name: str,
        file_size: Optional[int] = None,
        ip_address: Optional[str] = None
    ):
        """记录文件操作事件"""
        event_type_map = {
            'upload': AuditEventType.FILE_UPLOAD,
            'download': AuditEventType.FILE_DOWNLOAD,
            'delete': AuditEventType.FILE_DELETE,
            'share': AuditEventType.FILE_SHARE
        }
        
        await self.log_audit_event(
            event_type=event_type_map.get(operation, AuditEventType.FILE_UPLOAD),
            user_id=user_id,
            meeting_id=meeting_id,
            description=f"用户 {user_id} {operation} 文件 {file_name}",
            details={
                'operation': operation,
                'file_name': file_name,
                'file_size': file_size,
                'timestamp': datetime.utcnow().isoformat()
            },
            ip_address=ip_address,
            severity=AuditSeverity.LOW
        )
    
    # 6. 安全事件审计
    
    async def log_security_violation(
        self,
        user_id: Optional[int],
        meeting_id: Optional[int],
        violation_type: str,
        description: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        """记录安全违规事件"""
        await self.log_audit_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            user_id=user_id,
            meeting_id=meeting_id,
            description=f"安全违规: {violation_type} - {description}",
            details={
                'violation_type': violation_type,
                'additional_info': additional_info,
                'timestamp': datetime.utcnow().isoformat()
            },
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            severity=AuditSeverity.HIGH
        )
    
    async def log_authentication_failure(
        self,
        user_id: Optional[int],
        meeting_id: Optional[int],
        failure_reason: str,
        ip_address: str,
        user_agent: str
    ):
        """记录认证失败事件"""
        await self.log_audit_event(
            event_type=AuditEventType.AUTHENTICATION_FAILURE,
            user_id=user_id,
            meeting_id=meeting_id,
            description=f"认证失败: {failure_reason}",
            details={
                'failure_reason': failure_reason,
                'timestamp': datetime.utcnow().isoformat()
            },
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            severity=AuditSeverity.MEDIUM
        )
    
    # 7. 异常检测
    
    async def _detect_anomalies(self, audit_log: MeetingAuditLog):
        """检测异常行为"""
        try:
            # 检测频繁失败登录
            if audit_log.event_type == AuditEventType.AUTHENTICATION_FAILURE:
                await self._check_frequent_failures(audit_log)
            
            # 检测异常访问模式
            if audit_log.event_type == AuditEventType.MEETING_JOIN:
                await self._check_unusual_access_patterns(audit_log)
            
            # 检测大量文件操作
            if audit_log.event_type in [AuditEventType.FILE_UPLOAD, AuditEventType.FILE_DOWNLOAD]:
                await self._check_excessive_file_operations(audit_log)
            
        except Exception as e:
            logger.error(f"异常检测失败: {str(e)}")
    
    async def _check_frequent_failures(self, audit_log: MeetingAuditLog):
        """检查频繁失败"""
        if not audit_log.ip_address:
            return
        
        # 查询过去1小时内的失败次数
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        async with get_async_session_ctx() as db:
            from sqlalchemy import select, and_
            
            query = select(MeetingAuditLog).where(
                and_(
                    MeetingAuditLog.event_type == AuditEventType.AUTHENTICATION_FAILURE,
                    MeetingAuditLog.ip_address == audit_log.ip_address,
                    MeetingAuditLog.event_timestamp >= one_hour_ago,
                    MeetingAuditLog.success == False
                )
            )
            
            result = await db.execute(query)
            failure_count = len(result.scalars().all())
            
            if failure_count >= self.anomaly_thresholds['max_failed_logins_per_hour']:
                await self.log_audit_event(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    description=f"检测到来自 {audit_log.ip_address} 的频繁认证失败",
                    details={
                        'failure_count': failure_count,
                        'time_window': '1 hour',
                        'threshold': self.anomaly_thresholds['max_failed_logins_per_hour']
                    },
                    ip_address=audit_log.ip_address,
                    severity=AuditSeverity.HIGH
                )
    
    async def _check_unusual_access_patterns(self, audit_log: MeetingAuditLog):
        """检查异常访问模式"""
        if not audit_log.user_id:
            return
        
        # 检查用户今天参加的会议数量
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with get_async_session_ctx() as db:
            from sqlalchemy import select, and_
            
            query = select(MeetingAuditLog).where(
                and_(
                    MeetingAuditLog.event_type == AuditEventType.MEETING_JOIN,
                    MeetingAuditLog.user_id == audit_log.user_id,
                    MeetingAuditLog.event_timestamp >= today_start,
                    MeetingAuditLog.success == True
                )
            )
            
            result = await db.execute(query)
            meeting_count = len(result.scalars().all())
            
            if meeting_count >= self.anomaly_thresholds['max_meetings_per_user_per_day']:
                await self.log_audit_event(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    user_id=audit_log.user_id,
                    description=f"用户 {audit_log.user_id} 今日参加会议数量异常",
                    details={
                        'meeting_count': meeting_count,
                        'threshold': self.anomaly_thresholds['max_meetings_per_user_per_day']
                    },
                    severity=AuditSeverity.MEDIUM
                )
    
    async def _check_excessive_file_operations(self, audit_log: MeetingAuditLog):
        """检查过量文件操作"""
        if not audit_log.meeting_id:
            return
        
        # 检查会议中的文件操作数量
        async with get_async_session_ctx() as db:
            from sqlalchemy import select, and_
            
            query = select(MeetingAuditLog).where(
                and_(
                    MeetingAuditLog.event_type.in_([AuditEventType.FILE_UPLOAD, AuditEventType.FILE_DOWNLOAD]),
                    MeetingAuditLog.meeting_id == audit_log.meeting_id,
                    MeetingAuditLog.success == True
                )
            )
            
            result = await db.execute(query)
            file_op_count = len(result.scalars().all())
            
            if file_op_count >= self.anomaly_thresholds['max_file_uploads_per_meeting']:
                await self.log_audit_event(
                    event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                    meeting_id=audit_log.meeting_id,
                    description=f"会议 {audit_log.meeting_id} 文件操作数量异常",
                    details={
                        'file_operation_count': file_op_count,
                        'threshold': self.anomaly_thresholds['max_file_uploads_per_meeting']
                    },
                    severity=AuditSeverity.MEDIUM
                )
    
    # 8. 审计日志查询
    
    async def get_audit_logs(
        self,
        meeting_id: Optional[int] = None,
        user_id: Optional[int] = None,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MeetingAuditLog]:
        """
        查询审计日志
        
        Args:
            meeting_id: 会议ID
            user_id: 用户ID
            event_type: 事件类型
            severity: 严重级别
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            审计日志列表
        """
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import select, and_, desc
                
                conditions = []
                
                if meeting_id:
                    conditions.append(MeetingAuditLog.meeting_id == meeting_id)
                if user_id:
                    conditions.append(MeetingAuditLog.user_id == user_id)
                if event_type:
                    conditions.append(MeetingAuditLog.event_type == event_type)
                if severity:
                    conditions.append(MeetingAuditLog.severity == severity)
                if start_time:
                    conditions.append(MeetingAuditLog.event_timestamp >= start_time)
                if end_time:
                    conditions.append(MeetingAuditLog.event_timestamp <= end_time)
                
                query = select(MeetingAuditLog)
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(desc(MeetingAuditLog.event_timestamp))
                query = query.limit(limit).offset(offset)
                
                result = await db.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"查询审计日志失败: {str(e)}")
            return []
    
    async def get_security_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取安全摘要
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            安全摘要信息
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(days=7)
            if not end_time:
                end_time = datetime.utcnow()
            
            async with get_async_session_ctx() as db:
                from sqlalchemy import select, and_, func
                
                # 基础查询条件
                base_conditions = [
                    MeetingAuditLog.event_timestamp >= start_time,
                    MeetingAuditLog.event_timestamp <= end_time
                ]
                
                # 总事件数
                total_events_query = select(func.count(MeetingAuditLog.id)).where(and_(*base_conditions))
                total_events_result = await db.execute(total_events_query)
                total_events = total_events_result.scalar()
                
                # 安全事件数
                security_conditions = base_conditions + [
                    MeetingAuditLog.event_type.in_([
                        AuditEventType.SECURITY_VIOLATION,
                        AuditEventType.SUSPICIOUS_ACTIVITY,
                        AuditEventType.AUTHENTICATION_FAILURE,
                        AuditEventType.ACCESS_DENIED
                    ])
                ]
                security_events_query = select(func.count(MeetingAuditLog.id)).where(and_(*security_conditions))
                security_events_result = await db.execute(security_events_query)
                security_events = security_events_result.scalar()
                
                # 失败事件数
                failure_conditions = base_conditions + [MeetingAuditLog.success == False]
                failure_events_query = select(func.count(MeetingAuditLog.id)).where(and_(*failure_conditions))
                failure_events_result = await db.execute(failure_events_query)
                failure_events = failure_events_result.scalar()
                
                # 高危事件数
                critical_conditions = base_conditions + [MeetingAuditLog.severity == AuditSeverity.CRITICAL]
                critical_events_query = select(func.count(MeetingAuditLog.id)).where(and_(*critical_conditions))
                critical_events_result = await db.execute(critical_events_query)
                critical_events = critical_events_result.scalar()
                
                return {
                    'period': {
                        'start_time': start_time.isoformat(),
                        'end_time': end_time.isoformat()
                    },
                    'total_events': total_events,
                    'security_events': security_events,
                    'failure_events': failure_events,
                    'critical_events': critical_events,
                    'security_score': max(0, 100 - (security_events * 10) - (critical_events * 20)),
                    'generated_at': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"获取安全摘要失败: {str(e)}")
            return {
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    # 9. 审计日志清理
    
    async def cleanup_old_logs(self, retention_days: int = 90):
        """
        清理旧的审计日志
        
        Args:
            retention_days: 保留天数
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            async with get_async_session_ctx() as db:
                from sqlalchemy import delete
                
                # 删除旧日志
                delete_query = delete(MeetingAuditLog).where(
                    MeetingAuditLog.event_timestamp < cutoff_date
                )
                
                result = await db.execute(delete_query)
                deleted_count = result.rowcount
                
                await db.commit()
                
                logger.info(f"清理了 {deleted_count} 条旧审计日志")
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理审计日志失败: {str(e)}")
            return 0