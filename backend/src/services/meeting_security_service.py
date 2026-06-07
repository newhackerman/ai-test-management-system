"""
会议安全和合规控制服务

提供会议系统的安全功能，包括：
- 数据加密和保护
- 访问控制和审计
- 隐私合规管理
- 安全日志记录
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import hashlib
import secrets
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from ..models.meeting import Meeting, MeetingAuditLog
from ..models.user import User
from ..core.exceptions import SecurityError, ValidationError
from ..utils.encryption import EncryptionUtils


class MeetingSecurityService:
    """会议安全服务"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.encryption_utils = EncryptionUtils()
    
    async def encrypt_meeting_data(
        self,
        meeting_id: int,
        sensitive_data: Dict[str, Any]
    ) -> str:
        """加密会议敏感数据"""
        try:
            # 获取会议信息
            meeting_query = select(Meeting).where(Meeting.id == meeting_id)
            meeting_result = await self.db_session.execute(meeting_query)
            meeting = meeting_result.scalar_one_or_none()
            
            if not meeting:
                raise ValidationError("会议不存在")
            
            # 生成会议专用加密密钥
            encryption_key = self._generate_meeting_encryption_key(meeting_id)
            
            # 加密数据
            encrypted_data = self.encryption_utils.encrypt_data(
                data=json.dumps(sensitive_data),
                key=encryption_key
            )
            
            # 记录加密操作
            await self._log_security_event(
                meeting_id=meeting_id,
                event_type='data_encryption',
                details={'data_fields': list(sensitive_data.keys())}
            )
            
            return encrypted_data
            
        except Exception as e:
            raise SecurityError(f"数据加密失败: {str(e)}")
    
    async def decrypt_meeting_data(
        self,
        meeting_id: int,
        encrypted_data: str
    ) -> Dict[str, Any]:
        """解密会议敏感数据"""
        try:
            # 生成会议专用解密密钥
            encryption_key = self._generate_meeting_encryption_key(meeting_id)
            
            # 解密数据
            decrypted_json = self.encryption_utils.decrypt_data(
                encrypted_data=encrypted_data,
                key=encryption_key
            )
            
            decrypted_data = json.loads(decrypted_json)
            
            # 记录解密操作
            await self._log_security_event(
                meeting_id=meeting_id,
                event_type='data_decryption',
                details={'data_fields': list(decrypted_data.keys())}
            )
            
            return decrypted_data
            
        except Exception as e:
            raise SecurityError(f"数据解密失败: {str(e)}")
    
    async def log_meeting_access(
        self,
        meeting_id: int,
        user_id: int,
        action: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录会议访问日志"""
        try:
            audit_log = MeetingAuditLog(
                meeting_id=meeting_id,
                user_id=user_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                additional_data=additional_data or {},
                timestamp=datetime.now()
            )
            
            self.db_session.add(audit_log)
            await self.db_session.flush()
            
        except Exception as e:
            # 审计日志记录失败不应该影响主要功能
            print(f"审计日志记录失败: {str(e)}")
    
    async def get_meeting_audit_logs(
        self,
        meeting_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取会议审计日志"""
        query = select(MeetingAuditLog).where(
            MeetingAuditLog.meeting_id == meeting_id
        )
        
        if start_time:
            query = query.where(MeetingAuditLog.timestamp >= start_time)
        
        if end_time:
            query = query.where(MeetingAuditLog.timestamp <= end_time)
        
        query = query.order_by(desc(MeetingAuditLog.timestamp)).limit(limit)
        
        result = await self.db_session.execute(query)
        logs = result.scalars().all()
        
        return [
            {
                'id': log.id,
                'user_id': log.user_id,
                'action': log.action,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'additional_data': log.additional_data,
                'timestamp': log.timestamp
            }
            for log in logs
        ]
    
    async def anonymize_personal_data(
        self,
        meeting_id: int,
        personal_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """匿名化个人数据"""
        try:
            anonymized_data = {}
            
            for key, value in personal_data.items():
                if key in ['participant_name', 'name', 'full_name']:
                    # 姓名匿名化
                    anonymized_data[key] = self._anonymize_name(str(value))
                elif key in ['email', 'email_address']:
                    # 邮箱匿名化
                    anonymized_data[key] = self._anonymize_email(str(value))
                elif key in ['phone', 'phone_number', 'mobile']:
                    # 电话号码匿名化
                    anonymized_data[key] = self._anonymize_phone(str(value))
                elif key in ['comments', 'notes', 'content']:
                    # 文本内容中的个人信息匿名化
                    anonymized_data[key] = self._anonymize_text_content(str(value))
                else:
                    # 其他数据保持不变
                    anonymized_data[key] = value
            
            # 记录匿名化操作
            await self._log_security_event(
                meeting_id=meeting_id,
                event_type='data_anonymization',
                details={'anonymized_fields': list(personal_data.keys())}
            )
            
            return anonymized_data
            
        except Exception as e:
            raise SecurityError(f"数据匿名化失败: {str(e)}")
    
    async def delete_user_meeting_data(
        self,
        user_id: int,
        meeting_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """删除用户会议数据（GDPR合规）"""
        try:
            deleted_records = 0
            
            # 删除参与者记录
            from ..models.meeting import MeetingParticipant
            participant_query = select(MeetingParticipant).where(
                MeetingParticipant.user_id == user_id
            )
            
            if meeting_id:
                participant_query = participant_query.where(
                    MeetingParticipant.meeting_id == meeting_id
                )
            
            participant_result = await self.db_session.execute(participant_query)
            participants = participant_result.scalars().all()
            
            for participant in participants:
                await self.db_session.delete(participant)
                deleted_records += 1
            
            # 删除聊天消息
            from ..models.meeting import MeetingChat
            chat_query = select(MeetingChat).where(
                MeetingChat.user_id == user_id
            )
            
            if meeting_id:
                chat_query = chat_query.where(
                    MeetingChat.meeting_id == meeting_id
                )
            
            chat_result = await self.db_session.execute(chat_query)
            chats = chat_result.scalars().all()
            
            for chat in chats:
                await self.db_session.delete(chat)
                deleted_records += 1
            
            # 匿名化审计日志（不删除，但移除个人标识）
            audit_query = select(MeetingAuditLog).where(
                MeetingAuditLog.user_id == user_id
            )
            
            if meeting_id:
                audit_query = audit_query.where(
                    MeetingAuditLog.meeting_id == meeting_id
                )
            
            audit_result = await self.db_session.execute(audit_query)
            audit_logs = audit_result.scalars().all()
            
            for log in audit_logs:
                log.user_id = None  # 匿名化用户ID
                log.ip_address = self._anonymize_ip(log.ip_address)
                log.user_agent = None
                deleted_records += 1
            
            await self.db_session.flush()
            
            # 记录删除操作
            await self._log_security_event(
                meeting_id=meeting_id or 0,
                event_type='user_data_deletion',
                details={
                    'deleted_user_id': user_id,
                    'deleted_records': deleted_records
                }
            )
            
            return {
                'success': True,
                'deleted_records': deleted_records,
                'message': f'成功删除用户 {user_id} 的 {deleted_records} 条会议相关记录'
            }
            
        except Exception as e:
            raise SecurityError(f"用户数据删除失败: {str(e)}")
    
    def _generate_meeting_encryption_key(self, meeting_id: int) -> str:
        """生成会议专用加密密钥"""
        # 基于会议ID和系统密钥生成唯一加密密钥
        base_key = f"meeting_{meeting_id}_encryption_key"
        return hashlib.sha256(base_key.encode()).hexdigest()[:32]
    
    def _anonymize_name(self, name: str) -> str:
        """匿名化姓名"""
        if len(name) <= 1:
            return "*"
        elif len(name) == 2:
            return name[0] + "*"
        else:
            return name[0] + "*" * (len(name) - 2) + name[-1]
    
    def _anonymize_email(self, email: str) -> str:
        """匿名化邮箱"""
        if "@" not in email:
            return "***@***.***"
        
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            anonymized_local = "*" * len(local)
        else:
            anonymized_local = local[0] + "*" * (len(local) - 2) + local[-1]
        
        return f"{anonymized_local}@{domain}"
    
    def _anonymize_phone(self, phone: str) -> str:
        """匿名化电话号码"""
        # 保留前3位和后4位，中间用*替代
        if len(phone) <= 7:
            return "*" * len(phone)
        else:
            return phone[:3] + "*" * (len(phone) - 7) + phone[-4:]
    
    def _anonymize_text_content(self, content: str) -> str:
        """匿名化文本内容中的个人信息"""
        # 简单实现：替换常见的个人信息模式
        import re
        
        # 替换邮箱
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                        '***@***.***', content)
        
        # 替换电话号码
        content = re.sub(r'\b1[3-9]\d{9}\b', '***********', content)
        
        # 替换身份证号
        content = re.sub(r'\b\d{17}[\dXx]\b', '******************', content)
        
        return content
    
    def _anonymize_ip(self, ip_address: str) -> str:
        """匿名化IP地址"""
        if "." in ip_address:  # IPv4
            parts = ip_address.split(".")
            return f"{parts[0]}.{parts[1]}.*.***"
        elif ":" in ip_address:  # IPv6
            parts = ip_address.split(":")
            return ":".join(parts[:3]) + ":****:****:****:****"
        else:
            return "***.***.***"
    
    async def _log_security_event(
        self,
        meeting_id: int,
        event_type: str,
        details: Dict[str, Any]
    ) -> None:
        """记录安全事件"""
        try:
            audit_log = MeetingAuditLog(
                meeting_id=meeting_id,
                user_id=None,  # 系统事件
                action=f"security_{event_type}",
                ip_address="system",
                user_agent="security_service",
                additional_data=details,
                timestamp=datetime.now()
            )
            
            self.db_session.add(audit_log)
            await self.db_session.flush()
            
        except Exception as e:
            print(f"安全事件记录失败: {str(e)}")
    
    async def check_meeting_security_compliance(
        self,
        meeting_id: int
    ) -> Dict[str, Any]:
        """检查会议安全合规性"""
        compliance_report = {
            'meeting_id': meeting_id,
            'compliance_score': 0,
            'checks': [],
            'recommendations': []
        }
        
        try:
            # 获取会议信息
            meeting_query = select(Meeting).where(Meeting.id == meeting_id)
            meeting_result = await self.db_session.execute(meeting_query)
            meeting = meeting_result.scalar_one_or_none()
            
            if not meeting:
                return compliance_report
            
            score = 0
            total_checks = 5
            
            # 检查1: 是否启用了录制加密
            if meeting.is_recording_enabled and meeting.recording_encryption:
                score += 1
                compliance_report['checks'].append({
                    'name': '录制加密',
                    'status': 'passed',
                    'message': '录制文件已启用加密'
                })
            else:
                compliance_report['checks'].append({
                    'name': '录制加密',
                    'status': 'failed',
                    'message': '录制文件未启用加密'
                })
                compliance_report['recommendations'].append('建议启用录制文件加密')
            
            # 检查2: 是否设置了会议密码
            if meeting.meeting_password:
                score += 1
                compliance_report['checks'].append({
                    'name': '会议密码',
                    'status': 'passed',
                    'message': '已设置会议密码'
                })
            else:
                compliance_report['checks'].append({
                    'name': '会议密码',
                    'status': 'warning',
                    'message': '未设置会议密码'
                })
                compliance_report['recommendations'].append('建议为敏感会议设置密码')
            
            # 检查3: 是否启用了等候室
            if meeting.waiting_room_enabled:
                score += 1
                compliance_report['checks'].append({
                    'name': '等候室',
                    'status': 'passed',
                    'message': '已启用等候室功能'
                })
            else:
                compliance_report['checks'].append({
                    'name': '等候室',
                    'status': 'warning',
                    'message': '未启用等候室功能'
                })
                compliance_report['recommendations'].append('建议启用等候室以控制参与者加入')
            
            # 检查4: 审计日志完整性
            audit_count = await self._get_audit_log_count(meeting_id)
            if audit_count > 0:
                score += 1
                compliance_report['checks'].append({
                    'name': '审计日志',
                    'status': 'passed',
                    'message': f'已记录 {audit_count} 条审计日志'
                })
            else:
                compliance_report['checks'].append({
                    'name': '审计日志',
                    'status': 'failed',
                    'message': '缺少审计日志记录'
                })
                compliance_report['recommendations'].append('确保所有会议操作都有审计日志')
            
            # 检查5: 数据保留策略
            if meeting.data_retention_days and meeting.data_retention_days <= 365:
                score += 1
                compliance_report['checks'].append({
                    'name': '数据保留',
                    'status': 'passed',
                    'message': f'数据保留期限: {meeting.data_retention_days} 天'
                })
            else:
                compliance_report['checks'].append({
                    'name': '数据保留',
                    'status': 'warning',
                    'message': '未设置合理的数据保留期限'
                })
                compliance_report['recommendations'].append('建议设置合理的数据保留期限（不超过365天）')
            
            compliance_report['compliance_score'] = (score / total_checks) * 100
            
            return compliance_report
            
        except Exception as e:
            compliance_report['error'] = f"合规性检查失败: {str(e)}"
            return compliance_report
    
    async def _get_audit_log_count(self, meeting_id: int) -> int:
        """获取审计日志数量"""
        from sqlalchemy import func
        
        query = select(func.count(MeetingAuditLog.id)).where(
            MeetingAuditLog.meeting_id == meeting_id
        )
        result = await self.db_session.execute(query)
        return result.scalar() or 0
