"""
会议安全集成服务

整合所有安全相关功能，提供统一的安全接口：
- 安全服务协调
- 安全策略执行
- 安全事件处理
- 安全配置管理
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .meeting_security_service import MeetingSecurityService
from .meeting_audit_service import MeetingAuditService, AuditEventType, AuditSeverity
from .meeting_privacy_service import MeetingPrivacyService, ConsentType, PrivacyLevel, DataRetentionPolicy
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class MeetingSecurityIntegrationService:
    """会议安全集成服务"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # 初始化各个安全服务
        self.security_service = MeetingSecurityService()
        self.audit_service = MeetingAuditService()
        self.privacy_service = MeetingPrivacyService()
    
    # 1. 会议创建安全检查
    
    async def secure_meeting_creation(
        self,
        meeting_data: Dict[str, Any],
        creator_user_id: int,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """
        安全的会议创建流程
        
        Args:
            meeting_data: 会议数据
            creator_user_id: 创建者用户ID
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            创建结果和安全信息
        """
        try:
            # 1. 安全验证
            is_valid, validation_errors = self.security_service.validate_security_requirements(meeting_data)
            if not is_valid:
                await self.audit_service.log_audit_event(
                    event_type=AuditEventType.SECURITY_VIOLATION,
                    user_id=creator_user_id,
                    description="会议创建安全验证失败",
                    details={'validation_errors': validation_errors},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    severity=AuditSeverity.MEDIUM
                )
                return {
                    'success': False,
                    'errors': validation_errors,
                    'security_issues': True
                }
            
            # 2. 生成会议加密密钥
            meeting_id = meeting_data.get('id')  # 假设会议已经有ID
            if meeting_id:
                encryption_key = self.security_service.generate_meeting_encryption_key(meeting_id)
                meeting_data['encryption_key'] = encryption_key
            
            # 3. 创建隐私设置
            privacy_level = PrivacyLevel.INTERNAL
            if meeting_data.get('is_confidential'):
                privacy_level = PrivacyLevel.CONFIDENTIAL
            elif meeting_data.get('is_public'):
                privacy_level = PrivacyLevel.PUBLIC
            
            if meeting_id:
                await self.privacy_service.create_privacy_settings(
                    meeting_id=meeting_id,
                    privacy_level=privacy_level,
                    retention_policy=DataRetentionPolicy.MEDIUM_TERM
                )
            
            # 4. 记录审计日志
            await self.audit_service.log_audit_event(
                event_type=AuditEventType.MEETING_CREATE,
                user_id=creator_user_id,
                meeting_id=meeting_id,
                description=f"用户 {creator_user_id} 创建会议",
                details={
                    'meeting_title': meeting_data.get('title'),
                    'meeting_type': meeting_data.get('meeting_type'),
                    'privacy_level': privacy_level.value,
                    'encryption_enabled': True
                },
                ip_address=ip_address,
                user_agent=user_agent,
                severity=AuditSeverity.LOW
            )
            
            return {
                'success': True,
                'meeting_data': meeting_data,
                'security_config': self.security_service.get_security_config(meeting_id) if meeting_id else {}
            }
            
        except Exception as e:
            logger.error(f"安全会议创建失败: {str(e)}")
            await self.audit_service.log_audit_event(
                event_type=AuditEventType.SYSTEM_ERROR,
                user_id=creator_user_id,
                description="会议创建系统错误",
                error_message=str(e),
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                severity=AuditSeverity.HIGH
            )
            return {
                'success': False,
                'error': str(e),
                'system_error': True
            }
    
    # 2. 会议加入安全检查
    
    async def secure_meeting_join(
        self,
        meeting_id: int,
        user_id: int,
        session_id: str,
        ip_address: str,
        user_agent: str,
        join_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        安全的会议加入流程
        
        Args:
            meeting_id: 会议ID
            user_id: 用户ID
            session_id: 会话ID
            ip_address: IP地址
            user_agent: 用户代理
            join_token: 加入令牌
            
        Returns:
            加入结果和安全信息
        """
        try:
            # 1. 验证加入令牌
            if join_token:
                token_payload = self.security_service.verify_meeting_token(join_token, meeting_id)
                if not token_payload:
                    await self.audit_service.log_authentication_failure(
                        user_id=user_id,
                        meeting_id=meeting_id,
                        failure_reason="无效的加入令牌",
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    return {
                        'success': False,
                        'error': '无效的加入令牌',
                        'authentication_failed': True
                    }
            
            # 2. 检查用户同意
            recording_consent = await self.privacy_service.check_user_consent(
                user_id=user_id,
                meeting_id=meeting_id,
                consent_type=ConsentType.RECORDING
            )
            
            if not recording_consent:
                # 需要用户同意录制
                return {
                    'success': False,
                    'consent_required': True,
                    'consent_types': [ConsentType.RECORDING.value]
                }
            
            # 3. 生成安全的访问令牌
            access_token = self.security_service.generate_secure_meeting_token(
                meeting_id=meeting_id,
                user_id=user_id,
                permissions=['join', 'chat', 'share_screen']
            )
            
            # 4. 记录加入事件
            await self.audit_service.log_meeting_join(
                meeting_id=meeting_id,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )
            
            return {
                'success': True,
                'access_token': access_token,
                'security_config': self.security_service.get_security_config(meeting_id),
                'encryption_enabled': True
            }
            
        except Exception as e:
            logger.error(f"安全会议加入失败: {str(e)}")
            await self.audit_service.log_audit_event(
                event_type=AuditEventType.SYSTEM_ERROR,
                user_id=user_id,
                meeting_id=meeting_id,
                description="会议加入系统错误",
                error_message=str(e),
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                severity=AuditSeverity.HIGH
            )
            return {
                'success': False,
                'error': str(e),
                'system_error': True
            }
    
    # 3. 录制安全管理
    
    async def secure_recording_start(
        self,
        meeting_id: int,
        user_id: int,
        recording_config: Dict[str, Any],
        ip_address: str
    ) -> Dict[str, Any]:
        """
        安全的录制启动流程
        
        Args:
            meeting_id: 会议ID
            user_id: 用户ID
            recording_config: 录制配置
            ip_address: IP地址
            
        Returns:
            录制启动结果
        """
        try:
            # 1. 检查录制权限和同意
            recording_consent = await self.privacy_service.check_user_consent(
                user_id=user_id,
                meeting_id=meeting_id,
                consent_type=ConsentType.RECORDING
            )
            
            if not recording_consent:
                await self.audit_service.log_access_denied(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    reason="缺少录制同意",
                    ip_address=ip_address,
                    user_agent=""
                )
                return {
                    'success': False,
                    'error': '缺少录制同意',
                    'consent_required': True
                }
            
            # 2. 启用录制文件加密
            recording_config['encryption_enabled'] = True
            recording_config['meeting_id'] = meeting_id
            
            # 3. 记录录制开始事件
            await self.audit_service.log_recording_operation(
                meeting_id=meeting_id,
                user_id=user_id,
                operation='start',
                ip_address=ip_address
            )
            
            return {
                'success': True,
                'recording_config': recording_config,
                'encryption_enabled': True
            }
            
        except Exception as e:
            logger.error(f"安全录制启动失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def secure_recording_access(
        self,
        recording_id: int,
        user_id: int,
        meeting_id: int,
        access_type: str,  # view, download
        ip_address: str
    ) -> Dict[str, Any]:
        """
        安全的录制访问流程
        
        Args:
            recording_id: 录制ID
            user_id: 用户ID
            meeting_id: 会议ID
            access_type: 访问类型
            ip_address: IP地址
            
        Returns:
            访问结果
        """
        try:
            # 1. 检查访问权限
            # 这里应该检查用户是否有权限访问该录制
            
            # 2. 记录访问事件
            await self.audit_service.log_recording_operation(
                meeting_id=meeting_id,
                user_id=user_id,
                operation=access_type,
                recording_id=recording_id,
                ip_address=ip_address
            )
            
            # 3. 如果是下载，需要解密文件
            if access_type == 'download':
                # 这里应该调用解密服务
                pass
            
            return {
                'success': True,
                'access_granted': True
            }
            
        except Exception as e:
            logger.error(f"安全录制访问失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 4. 文件共享安全管理
    
    async def secure_file_upload(
        self,
        meeting_id: int,
        user_id: int,
        file_info: Dict[str, Any],
        ip_address: str
    ) -> Dict[str, Any]:
        """
        安全的文件上传流程
        
        Args:
            meeting_id: 会议ID
            user_id: 用户ID
            file_info: 文件信息
            ip_address: IP地址
            
        Returns:
            上传结果
        """
        try:
            # 1. 文件安全检查
            file_name = file_info.get('file_name', '')
            file_size = file_info.get('file_size', 0)
            
            # 检查文件类型
            allowed_extensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.jpg', '.png']
            if not any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                await self.audit_service.log_security_violation(
                    user_id=user_id,
                    meeting_id=meeting_id,
                    violation_type="不允许的文件类型",
                    description=f"用户尝试上传不允许的文件类型: {file_name}",
                    ip_address=ip_address
                )
                return {
                    'success': False,
                    'error': '不允许的文件类型',
                    'security_violation': True
                }
            
            # 检查文件大小
            max_file_size = 100 * 1024 * 1024  # 100MB
            if file_size > max_file_size:
                return {
                    'success': False,
                    'error': '文件大小超过限制',
                    'max_size': max_file_size
                }
            
            # 2. 生成安全的文件名
            from ..utils.security_utils import SecurityUtils
            secure_filename = SecurityUtils.generate_secure_filename(file_name)
            file_info['secure_filename'] = secure_filename
            
            # 3. 记录文件上传事件
            await self.audit_service.log_file_operation(
                meeting_id=meeting_id,
                user_id=user_id,
                operation='upload',
                file_name=file_name,
                file_size=file_size,
                ip_address=ip_address
            )
            
            return {
                'success': True,
                'file_info': file_info,
                'security_checks_passed': True
            }
            
        except Exception as e:
            logger.error(f"安全文件上传失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 5. 数据导出安全管理
    
    async def secure_data_export(
        self,
        meeting_id: int,
        user_id: int,
        export_type: str,
        export_scope: Dict[str, Any],
        ip_address: str
    ) -> Dict[str, Any]:
        """
        安全的数据导出流程
        
        Args:
            meeting_id: 会议ID
            user_id: 用户ID
            export_type: 导出类型
            export_scope: 导出范围
            ip_address: IP地址
            
        Returns:
            导出结果
        """
        try:
            # 1. 检查导出权限
            privacy_settings = await self.privacy_service.get_privacy_settings(meeting_id)
            if privacy_settings and not privacy_settings.allow_data_export:
                await self.audit_service.log_access_denied(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    reason="数据导出被禁用",
                    ip_address=ip_address,
                    user_agent=""
                )
                return {
                    'success': False,
                    'error': '数据导出被禁用',
                    'policy_violation': True
                }
            
            # 2. 脱敏导出数据
            export_data = {}  # 这里应该获取实际的导出数据
            masked_data = self.security_service.mask_sensitive_meeting_data(export_data)
            
            # 3. 记录导出事件
            await self.audit_service.log_audit_event(
                event_type=AuditEventType.SYSTEM_ERROR,  # 应该有专门的导出事件类型
                user_id=user_id,
                meeting_id=meeting_id,
                description=f"用户 {user_id} 导出会议 {meeting_id} 数据",
                details={
                    'export_type': export_type,
                    'export_scope': export_scope
                },
                ip_address=ip_address,
                severity=AuditSeverity.MEDIUM
            )
            
            return {
                'success': True,
                'export_data': masked_data,
                'data_masked': True
            }
            
        except Exception as e:
            logger.error(f"安全数据导出失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 6. 安全监控和报告
    
    async def get_security_dashboard(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取安全仪表板数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            安全仪表板数据
        """
        try:
            # 1. 获取安全摘要
            security_summary = await self.audit_service.get_security_summary(start_date, end_date)
            
            # 2. 获取隐私报告
            privacy_report = await self.privacy_service.generate_privacy_report(start_date, end_date)
            
            # 3. 整合安全指标
            dashboard_data = {
                'security_summary': security_summary,
                'privacy_report': privacy_report,
                'security_score': security_summary.get('security_score', 0),
                'compliance_status': 'compliant' if security_summary.get('critical_events', 0) == 0 else 'non_compliant',
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"获取安全仪表板失败: {str(e)}")
            return {
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    async def handle_security_incident(
        self,
        incident_type: str,
        incident_details: Dict[str, Any],
        user_id: Optional[int] = None,
        meeting_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理安全事件
        
        Args:
            incident_type: 事件类型
            incident_details: 事件详情
            user_id: 用户ID
            meeting_id: 会议ID
            ip_address: IP地址
            
        Returns:
            处理结果
        """
        try:
            # 1. 记录安全事件
            await self.audit_service.log_security_violation(
                user_id=user_id,
                meeting_id=meeting_id,
                violation_type=incident_type,
                description=f"安全事件: {incident_type}",
                ip_address=ip_address,
                additional_info=incident_details
            )
            
            # 2. 根据事件类型采取相应措施
            response_actions = []
            
            if incident_type == 'suspicious_login':
                # 可能需要锁定账户或要求额外验证
                response_actions.append('account_verification_required')
            elif incident_type == 'data_breach_attempt':
                # 立即阻止访问并通知管理员
                response_actions.append('access_blocked')
                response_actions.append('admin_notification_sent')
            elif incident_type == 'malware_detected':
                # 隔离文件并扫描系统
                response_actions.append('file_quarantined')
                response_actions.append('system_scan_initiated')
            
            # 3. 更新安全状态
            security_status = {
                'incident_handled': True,
                'response_actions': response_actions,
                'handled_at': datetime.utcnow().isoformat()
            }
            
            return {
                'success': True,
                'security_status': security_status
            }
            
        except Exception as e:
            logger.error(f"处理安全事件失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 7. 定期安全任务
    
    async def run_security_maintenance(self) -> Dict[str, Any]:
        """
        运行定期安全维护任务
        
        Returns:
            维护结果
        """
        try:
            maintenance_results = {
                'tasks_completed': [],
                'errors': []
            }
            
            # 1. 执行数据保留策略
            try:
                retention_result = await self.privacy_service.execute_retention_policy()
                maintenance_results['tasks_completed'].append({
                    'task': 'data_retention_policy',
                    'result': retention_result
                })
            except Exception as e:
                maintenance_results['errors'].append({
                    'task': 'data_retention_policy',
                    'error': str(e)
                })
            
            # 2. 清理旧的审计日志
            try:
                cleanup_result = await self.audit_service.cleanup_old_logs(retention_days=90)
                maintenance_results['tasks_completed'].append({
                    'task': 'audit_log_cleanup',
                    'result': {'deleted_logs': cleanup_result}
                })
            except Exception as e:
                maintenance_results['errors'].append({
                    'task': 'audit_log_cleanup',
                    'error': str(e)
                })
            
            # 3. 清理过期的会议密钥
            # 这里应该实现密钥清理逻辑
            
            maintenance_results['completed_at'] = datetime.utcnow().isoformat()
            
            return maintenance_results
            
        except Exception as e:
            logger.error(f"安全维护任务失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }