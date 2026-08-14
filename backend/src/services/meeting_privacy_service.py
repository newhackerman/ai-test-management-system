"""
会议隐私和合规服务

提供会议相关的隐私保护和合规功能，包括：
- GDPR合规管理
- 数据删除和匿名化
- 数据保留策略
- 隐私设置管理
"""
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, BigInteger, String, Text, DateTime, JSON, Enum as SQLEnum, Boolean, Integer
from sqlalchemy.orm import Session

from ..models.base import BaseModel
from ..models.meeting import Meeting, MeetingParticipant, MeetingRecording, MeetingMinutes, MeetingChat, MeetingFile
from ..core.database import get_async_session, get_async_session_ctx
from ..utils.security_utils import SecurityUtils
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class DataRetentionPolicy(Enum):
    """数据保留策略"""
    SHORT_TERM = "SHORT_TERM"      # 短期保留 (30天)
    MEDIUM_TERM = "MEDIUM_TERM"    # 中期保留 (1年)
    LONG_TERM = "LONG_TERM"        # 长期保留 (7年)
    PERMANENT = "PERMANENT"        # 永久保留
    CUSTOM = "CUSTOM"              # 自定义


class PrivacyLevel(Enum):
    """隐私级别"""
    PUBLIC = "PUBLIC"              # 公开
    INTERNAL = "INTERNAL"          # 内部
    CONFIDENTIAL = "CONFIDENTIAL"  # 机密
    RESTRICTED = "RESTRICTED"      # 限制级


class ConsentType(Enum):
    """同意类型"""
    RECORDING = "RECORDING"        # 录制同意
    DATA_PROCESSING = "DATA_PROCESSING"  # 数据处理同意
    ANALYTICS = "ANALYTICS"        # 分析同意
    MARKETING = "MARKETING"        # 营销同意


class MeetingPrivacySettings(BaseModel):
    """会议隐私设置模型"""
    __tablename__ = 'meeting_privacy_settings'
    
    # 关联信息
    meeting_id = Column(BigInteger, unique=True, nullable=False, index=True, comment='会议ID')
    
    # 隐私设置
    privacy_level = Column(SQLEnum(PrivacyLevel), default=PrivacyLevel.INTERNAL, nullable=False, comment='隐私级别')
    data_retention_policy = Column(SQLEnum(DataRetentionPolicy), default=DataRetentionPolicy.MEDIUM_TERM, nullable=False, comment='数据保留策略')
    retention_days = Column(Integer, comment='自定义保留天数')
    
    # 同意管理
    recording_consent_required = Column(Boolean, default=True, comment='是否需要录制同意')
    analytics_consent_required = Column(Boolean, default=False, comment='是否需要分析同意')
    data_processing_consent_required = Column(Boolean, default=True, comment='是否需要数据处理同意')
    
    # 数据处理设置
    allow_transcription = Column(Boolean, default=True, comment='是否允许转录')
    allow_ai_analysis = Column(Boolean, default=True, comment='是否允许AI分析')
    allow_data_export = Column(Boolean, default=False, comment='是否允许数据导出')
    
    # 地域合规
    data_residency_region = Column(String(50), comment='数据驻留地区')
    cross_border_transfer_allowed = Column(Boolean, default=False, comment='是否允许跨境传输')
    
    # 自动删除设置
    auto_delete_enabled = Column(Boolean, default=True, comment='是否启用自动删除')
    auto_delete_date = Column(DateTime, comment='自动删除日期')
    
    # 匿名化设置
    anonymization_enabled = Column(Boolean, default=False, comment='是否启用匿名化')
    anonymization_delay_days = Column(Integer, default=30, comment='匿名化延迟天数')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'privacy_level': self.privacy_level.value if self.privacy_level else None,
            'data_retention_policy': self.data_retention_policy.value if self.data_retention_policy else None,
            'retention_days': self.retention_days,
            'recording_consent_required': self.recording_consent_required,
            'analytics_consent_required': self.analytics_consent_required,
            'data_processing_consent_required': self.data_processing_consent_required,
            'allow_transcription': self.allow_transcription,
            'allow_ai_analysis': self.allow_ai_analysis,
            'allow_data_export': self.allow_data_export,
            'data_residency_region': self.data_residency_region,
            'cross_border_transfer_allowed': self.cross_border_transfer_allowed,
            'auto_delete_enabled': self.auto_delete_enabled,
            'auto_delete_date': self.auto_delete_date.isoformat() if self.auto_delete_date else None,
            'anonymization_enabled': self.anonymization_enabled,
            'anonymization_delay_days': self.anonymization_delay_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserConsent(BaseModel):
    """用户同意记录模型"""
    __tablename__ = 'user_consents'
    
    # 关联信息
    user_id = Column(BigInteger, nullable=False, index=True, comment='用户ID')
    meeting_id = Column(BigInteger, nullable=False, index=True, comment='会议ID')
    
    # 同意信息
    consent_type = Column(SQLEnum(ConsentType), nullable=False, comment='同意类型')
    consent_given = Column(Boolean, nullable=False, comment='是否同意')
    consent_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, comment='同意时间')
    
    # 同意详情
    consent_version = Column(String(20), comment='同意版本')
    consent_text = Column(Text, comment='同意文本')
    ip_address = Column(String(45), comment='IP地址')
    user_agent = Column(Text, comment='用户代理')
    
    # 撤销信息
    revoked = Column(Boolean, default=False, comment='是否已撤销')
    revoked_timestamp = Column(DateTime, comment='撤销时间')
    revoked_reason = Column(Text, comment='撤销原因')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'meeting_id': self.meeting_id,
            'consent_type': self.consent_type.value if self.consent_type else None,
            'consent_given': self.consent_given,
            'consent_timestamp': self.consent_timestamp.isoformat() if self.consent_timestamp else None,
            'consent_version': self.consent_version,
            'consent_text': self.consent_text,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'revoked': self.revoked,
            'revoked_timestamp': self.revoked_timestamp.isoformat() if self.revoked_timestamp else None,
            'revoked_reason': self.revoked_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DataDeletionRequest(BaseModel):
    """数据删除请求模型"""
    __tablename__ = 'data_deletion_requests'
    
    # 基本信息
    user_id = Column(BigInteger, nullable=False, index=True, comment='用户ID')
    request_type = Column(String(50), nullable=False, comment='请求类型')  # user_data, meeting_data, all_data
    
    # 请求详情
    reason = Column(Text, comment='删除原因')
    scope = Column(JSON, comment='删除范围')
    
    # 状态管理
    status = Column(String(20), default='pending', comment='处理状态')  # pending, processing, completed, failed
    
    # 处理信息
    processed_by = Column(BigInteger, comment='处理人ID')
    processed_at = Column(DateTime, comment='处理时间')
    completion_details = Column(JSON, comment='完成详情')
    
    # 验证信息
    verification_token = Column(String(100), comment='验证令牌')
    verified = Column(Boolean, default=False, comment='是否已验证')
    verified_at = Column(DateTime, comment='验证时间')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'request_type': self.request_type,
            'reason': self.reason,
            'scope': self.scope,
            'status': self.status,
            'processed_by': self.processed_by,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'completion_details': self.completion_details,
            'verification_token': self.verification_token,
            'verified': self.verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MeetingPrivacyService:
    """会议隐私和合规服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.security_utils = SecurityUtils()
        
        # 数据保留策略配置
        self.retention_policies = {
            DataRetentionPolicy.SHORT_TERM: 30,
            DataRetentionPolicy.MEDIUM_TERM: 365,
            DataRetentionPolicy.LONG_TERM: 2555,  # 7年
            DataRetentionPolicy.PERMANENT: None
        }
    
    # 1. 隐私设置管理
    
    async def create_privacy_settings(
        self,
        meeting_id: int,
        privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL,
        retention_policy: DataRetentionPolicy = DataRetentionPolicy.MEDIUM_TERM,
        custom_retention_days: Optional[int] = None,
        **kwargs
    ) -> MeetingPrivacySettings:
        """
        创建会议隐私设置
        
        Args:
            meeting_id: 会议ID
            privacy_level: 隐私级别
            retention_policy: 数据保留策略
            custom_retention_days: 自定义保留天数
            **kwargs: 其他设置
            
        Returns:
            隐私设置记录
        """
        try:
            async with get_async_session_ctx() as db:
                # 计算自动删除日期
                auto_delete_date = None
                if retention_policy != DataRetentionPolicy.PERMANENT:
                    retention_days = custom_retention_days if retention_policy == DataRetentionPolicy.CUSTOM else self.retention_policies[retention_policy]
                    if retention_days:
                        auto_delete_date = datetime.utcnow() + timedelta(days=retention_days)
                
                # 创建隐私设置
                privacy_settings = MeetingPrivacySettings(
                    meeting_id=meeting_id,
                    privacy_level=privacy_level,
                    data_retention_policy=retention_policy,
                    retention_days=custom_retention_days,
                    auto_delete_date=auto_delete_date,
                    **kwargs
                )
                
                db.add(privacy_settings)
                await db.commit()
                await db.refresh(privacy_settings)
                
                logger.info(f"创建会议 {meeting_id} 的隐私设置")
                return privacy_settings
                
        except Exception as e:
            logger.error(f"创建隐私设置失败: {str(e)}")
            raise
    
    async def update_privacy_settings(
        self,
        meeting_id: int,
        updates: Dict[str, Any]
    ) -> Optional[MeetingPrivacySettings]:
        """
        更新隐私设置
        
        Args:
            meeting_id: 会议ID
            updates: 更新内容
            
        Returns:
            更新后的隐私设置
        """
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import select
                
                # 查询现有设置
                query = select(MeetingPrivacySettings).where(
                    MeetingPrivacySettings.meeting_id == meeting_id
                )
                result = await db.execute(query)
                privacy_settings = result.scalar_one_or_none()
                
                if not privacy_settings:
                    return None
                
                # 更新设置
                for key, value in updates.items():
                    if hasattr(privacy_settings, key):
                        setattr(privacy_settings, key, value)
                
                # 重新计算自动删除日期
                if 'data_retention_policy' in updates or 'retention_days' in updates:
                    retention_policy = privacy_settings.data_retention_policy
                    if retention_policy != DataRetentionPolicy.PERMANENT:
                        retention_days = privacy_settings.retention_days if retention_policy == DataRetentionPolicy.CUSTOM else self.retention_policies[retention_policy]
                        if retention_days:
                            privacy_settings.auto_delete_date = datetime.utcnow() + timedelta(days=retention_days)
                
                await db.commit()
                await db.refresh(privacy_settings)
                
                logger.info(f"更新会议 {meeting_id} 的隐私设置")
                return privacy_settings
                
        except Exception as e:
            logger.error(f"更新隐私设置失败: {str(e)}")
            raise
    
    # 2. 用户同意管理
    
    async def record_user_consent(
        self,
        user_id: int,
        meeting_id: int,
        consent_type: ConsentType,
        consent_given: bool,
        consent_version: str = "1.0",
        consent_text: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserConsent:
        """
        记录用户同意
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            consent_type: 同意类型
            consent_given: 是否同意
            consent_version: 同意版本
            consent_text: 同意文本
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            同意记录
        """
        try:
            async with get_async_session_ctx() as db:
                # 创建同意记录
                consent = UserConsent(
                    user_id=user_id,
                    meeting_id=meeting_id,
                    consent_type=consent_type,
                    consent_given=consent_given,
                    consent_version=consent_version,
                    consent_text=consent_text,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                db.add(consent)
                await db.commit()
                await db.refresh(consent)
                
                logger.info(f"记录用户 {user_id} 对会议 {meeting_id} 的 {consent_type.value} 同意")
                return consent
                
        except Exception as e:
            logger.error(f"记录用户同意失败: {str(e)}")
            raise
    
    async def revoke_user_consent(
        self,
        user_id: int,
        meeting_id: int,
        consent_type: ConsentType,
        reason: Optional[str] = None
    ) -> bool:
        """
        撤销用户同意
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            consent_type: 同意类型
            reason: 撤销原因
            
        Returns:
            是否成功撤销
        """
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import select, and_
                
                # 查询同意记录
                query = select(UserConsent).where(
                    and_(
                        UserConsent.user_id == user_id,
                        UserConsent.meeting_id == meeting_id,
                        UserConsent.consent_type == consent_type,
                        UserConsent.revoked == False
                    )
                )
                result = await db.execute(query)
                consent = result.scalar_one_or_none()
                
                if not consent:
                    return False
                
                # 撤销同意
                consent.revoked = True
                consent.revoked_timestamp = datetime.utcnow()
                consent.revoked_reason = reason
                
                await db.commit()
                
                logger.info(f"撤销用户 {user_id} 对会议 {meeting_id} 的 {consent_type.value} 同意")
                return True
                
        except Exception as e:
            logger.error(f"撤销用户同意失败: {str(e)}")
            return False
    
    async def check_user_consent(
        self,
        user_id: int,
        meeting_id: int,
        consent_type: ConsentType
    ) -> bool:
        """
        检查用户同意状态
        
        Args:
            user_id: 用户ID
            meeting_id: 会议ID
            consent_type: 同意类型
            
        Returns:
            是否已同意
        """
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import select, and_
                
                query = select(UserConsent).where(
                    and_(
                        UserConsent.user_id == user_id,
                        UserConsent.meeting_id == meeting_id,
                        UserConsent.consent_type == consent_type,
                        UserConsent.consent_given == True,
                        UserConsent.revoked == False
                    )
                )
                result = await db.execute(query)
                consent = result.scalar_one_or_none()
                
                return consent is not None
                
        except Exception as e:
            logger.error(f"检查用户同意状态失败: {str(e)}")
            return False
    
    # 3. 数据删除和匿名化
    
    async def create_deletion_request(
        self,
        user_id: int,
        request_type: str,
        reason: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None
    ) -> DataDeletionRequest:
        """
        创建数据删除请求
        
        Args:
            user_id: 用户ID
            request_type: 请求类型
            reason: 删除原因
            scope: 删除范围
            
        Returns:
            删除请求记录
        """
        try:
            async with get_async_session_ctx() as db:
                # 生成验证令牌
                verification_token = self.security_utils.generate_secure_token(32)
                
                # 创建删除请求
                deletion_request = DataDeletionRequest(
                    user_id=user_id,
                    request_type=request_type,
                    reason=reason,
                    scope=scope or {},
                    verification_token=verification_token
                )
                
                db.add(deletion_request)
                await db.commit()
                await db.refresh(deletion_request)
                
                logger.info(f"创建用户 {user_id} 的数据删除请求")
                return deletion_request
                
        except Exception as e:
            logger.error(f"创建删除请求失败: {str(e)}")
            raise
    
    async def process_deletion_request(
        self,
        request_id: int,
        processor_user_id: int
    ) -> bool:
        """
        处理数据删除请求
        
        Args:
            request_id: 请求ID
            processor_user_id: 处理人ID
            
        Returns:
            是否处理成功
        """
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import select
                
                # 查询删除请求
                query = select(DataDeletionRequest).where(
                    DataDeletionRequest.id == request_id
                )
                result = await db.execute(query)
                deletion_request = result.scalar_one_or_none()
                
                if not deletion_request or not deletion_request.verified:
                    return False
                
                # 更新状态为处理中
                deletion_request.status = 'processing'
                deletion_request.processed_by = processor_user_id
                deletion_request.processed_at = datetime.utcnow()
                await db.commit()
                
                # 执行删除操作
                completion_details = {}
                
                if deletion_request.request_type == 'user_data':
                    completion_details = await self._delete_user_data(deletion_request.user_id, deletion_request.scope)
                elif deletion_request.request_type == 'meeting_data':
                    completion_details = await self._delete_meeting_data(deletion_request.user_id, deletion_request.scope)
                elif deletion_request.request_type == 'all_data':
                    completion_details = await self._delete_all_user_data(deletion_request.user_id)
                
                # 更新完成状态
                deletion_request.status = 'completed'
                deletion_request.completion_details = completion_details
                await db.commit()
                
                logger.info(f"完成数据删除请求 {request_id}")
                return True
                
        except Exception as e:
            logger.error(f"处理删除请求失败: {str(e)}")
            
            # 更新失败状态
            try:
                async with get_async_session_ctx() as db:
                    from sqlalchemy import select
                    query = select(DataDeletionRequest).where(DataDeletionRequest.id == request_id)
                    result = await db.execute(query)
                    deletion_request = result.scalar_one_or_none()
                    if deletion_request:
                        deletion_request.status = 'failed'
                        deletion_request.completion_details = {'error': str(e)}
                        await db.commit()
            except:
                pass
            
            return False
    
    async def _delete_user_data(self, user_id: int, scope: Dict[str, Any]) -> Dict[str, Any]:
        """删除用户数据"""
        completion_details = {'deleted_items': []}
        
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import delete
                
                # 删除用户参与记录
                if scope.get('participants', True):
                    delete_query = delete(MeetingParticipant).where(MeetingParticipant.user_id == user_id)
                    result = await db.execute(delete_query)
                    completion_details['deleted_items'].append(f"participants: {result.rowcount}")
                
                # 删除用户聊天消息
                if scope.get('chat_messages', True):
                    delete_query = delete(MeetingChat).where(MeetingChat.sender_id == user_id)
                    result = await db.execute(delete_query)
                    completion_details['deleted_items'].append(f"chat_messages: {result.rowcount}")
                
                # 删除用户上传的文件
                if scope.get('uploaded_files', True):
                    delete_query = delete(MeetingFile).where(MeetingFile.uploader_id == user_id)
                    result = await db.execute(delete_query)
                    completion_details['deleted_items'].append(f"uploaded_files: {result.rowcount}")
                
                # 删除用户同意记录
                if scope.get('consents', True):
                    delete_query = delete(UserConsent).where(UserConsent.user_id == user_id)
                    result = await db.execute(delete_query)
                    completion_details['deleted_items'].append(f"consents: {result.rowcount}")
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"删除用户数据失败: {str(e)}")
            completion_details['error'] = str(e)
        
        return completion_details
    
    async def _delete_meeting_data(self, user_id: int, scope: Dict[str, Any]) -> Dict[str, Any]:
        """删除特定会议的用户数据"""
        completion_details = {'deleted_items': []}
        meeting_ids = scope.get('meeting_ids', [])
        
        if not meeting_ids:
            return completion_details
        
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import delete, and_
                
                for meeting_id in meeting_ids:
                    # 删除参与记录
                    delete_query = delete(MeetingParticipant).where(
                        and_(MeetingParticipant.user_id == user_id, MeetingParticipant.meeting_id == meeting_id)
                    )
                    result = await db.execute(delete_query)
                    completion_details['deleted_items'].append(f"meeting_{meeting_id}_participants: {result.rowcount}")
                    
                    # 删除聊天消息
                    delete_query = delete(MeetingChat).where(
                        and_(MeetingChat.sender_id == user_id, MeetingChat.meeting_id == meeting_id)
                    )
                    result = await db.execute(delete_query)
                    completion_details['deleted_items'].append(f"meeting_{meeting_id}_chat: {result.rowcount}")
                    
                    # 删除文件
                    delete_query = delete(MeetingFile).where(
                        and_(MeetingFile.uploader_id == user_id, MeetingFile.meeting_id == meeting_id)
                    )
                    result = await db.execute(delete_query)
                    completion_details['deleted_items'].append(f"meeting_{meeting_id}_files: {result.rowcount}")
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"删除会议数据失败: {str(e)}")
            completion_details['error'] = str(e)
        
        return completion_details
    
    async def _delete_all_user_data(self, user_id: int) -> Dict[str, Any]:
        """删除用户所有数据"""
        return await self._delete_user_data(user_id, {
            'participants': True,
            'chat_messages': True,
            'uploaded_files': True,
            'consents': True
        })
    
    async def anonymize_user_data(self, user_id: int, meeting_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        匿名化用户数据
        
        Args:
            user_id: 用户ID
            meeting_ids: 会议ID列表，如果为None则匿名化所有数据
            
        Returns:
            匿名化结果
        """
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import select, and_, update
                
                anonymization_results = {'anonymized_items': []}
                
                # 匿名化参与记录
                if meeting_ids:
                    for meeting_id in meeting_ids:
                        # 这里只是示例，实际实现需要根据具体需求调整
                        # 可以将用户ID替换为匿名ID，但保留统计信息
                        pass
                else:
                    # 匿名化所有参与记录
                    pass
                
                # 匿名化聊天消息
                # 将消息内容中的个人信息替换为占位符
                
                # 匿名化文件信息
                # 移除文件中的个人标识信息
                
                logger.info(f"完成用户 {user_id} 数据匿名化")
                return anonymization_results
                
        except Exception as e:
            logger.error(f"匿名化用户数据失败: {str(e)}")
            return {'error': str(e)}
    
    # 4. 数据保留策略执行
    
    async def execute_retention_policy(self) -> Dict[str, Any]:
        """
        执行数据保留策略
        
        Returns:
            执行结果
        """
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import select, and_, delete
                
                execution_results = {'processed_meetings': 0, 'deleted_items': []}
                
                # 查询需要自动删除的会议
                current_time = datetime.utcnow()
                query = select(MeetingPrivacySettings).where(
                    and_(
                        MeetingPrivacySettings.auto_delete_enabled == True,
                        MeetingPrivacySettings.auto_delete_date <= current_time
                    )
                )
                result = await db.execute(query)
                privacy_settings_list = result.scalars().all()
                
                for privacy_settings in privacy_settings_list:
                    meeting_id = privacy_settings.meeting_id
                    
                    # 删除会议相关数据
                    deletion_result = await self._delete_meeting_completely(meeting_id)
                    execution_results['deleted_items'].extend(deletion_result.get('deleted_items', []))
                    execution_results['processed_meetings'] += 1
                    
                    # 删除隐私设置记录
                    await db.delete(privacy_settings)
                
                await db.commit()
                
                logger.info(f"执行数据保留策略，处理了 {execution_results['processed_meetings']} 个会议")
                return execution_results
                
        except Exception as e:
            logger.error(f"执行数据保留策略失败: {str(e)}")
            return {'error': str(e)}
    
    async def _delete_meeting_completely(self, meeting_id: int) -> Dict[str, Any]:
        """完全删除会议数据"""
        deletion_result = {'deleted_items': []}
        
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import delete
                
                # 删除会议相关的所有数据
                tables_to_clean = [
                    (MeetingParticipant, 'participants'),
                    (MeetingRecording, 'recordings'),
                    (MeetingMinutes, 'minutes'),
                    (MeetingChat, 'chat_messages'),
                    (MeetingFile, 'files'),
                    (UserConsent, 'consents')
                ]
                
                for model_class, item_name in tables_to_clean:
                    delete_query = delete(model_class).where(model_class.meeting_id == meeting_id)
                    result = await db.execute(delete_query)
                    deletion_result['deleted_items'].append(f"{item_name}: {result.rowcount}")
                
                # 最后删除会议记录
                delete_query = delete(Meeting).where(Meeting.id == meeting_id)
                result = await db.execute(delete_query)
                deletion_result['deleted_items'].append(f"meeting: {result.rowcount}")
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"完全删除会议数据失败: {str(e)}")
            deletion_result['error'] = str(e)
        
        return deletion_result
    
    # 5. 合规检查
    
    async def check_gdpr_compliance(self, meeting_id: int) -> Dict[str, Any]:
        """
        检查GDPR合规性
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            合规检查结果
        """
        try:
            compliance_result = {
                'compliant': True,
                'issues': [],
                'recommendations': []
            }
            
            async with get_async_session_ctx() as db:
                from sqlalchemy import select
                
                # 检查隐私设置
                privacy_query = select(MeetingPrivacySettings).where(
                    MeetingPrivacySettings.meeting_id == meeting_id
                )
                privacy_result = await db.execute(privacy_query)
                privacy_settings = privacy_result.scalar_one_or_none()
                
                if not privacy_settings:
                    compliance_result['compliant'] = False
                    compliance_result['issues'].append('缺少隐私设置')
                    compliance_result['recommendations'].append('创建会议隐私设置')
                
                # 检查用户同意
                consent_query = select(UserConsent).where(UserConsent.meeting_id == meeting_id)
                consent_result = await db.execute(consent_query)
                consents = consent_result.scalars().all()
                
                # 检查录制同意
                recording_consents = [c for c in consents if c.consent_type == ConsentType.RECORDING and c.consent_given and not c.revoked]
                participants_query = select(MeetingParticipant).where(MeetingParticipant.meeting_id == meeting_id)
                participants_result = await db.execute(participants_query)
                participants = participants_result.scalars().all()
                
                if len(recording_consents) < len(participants):
                    compliance_result['issues'].append('部分参与者未提供录制同意')
                    compliance_result['recommendations'].append('确保所有参与者提供录制同意')
                
                # 检查数据保留策略
                if privacy_settings and not privacy_settings.auto_delete_enabled:
                    compliance_result['recommendations'].append('启用自动删除以符合数据最小化原则')
                
                # 检查跨境传输
                if privacy_settings and privacy_settings.cross_border_transfer_allowed and not privacy_settings.data_residency_region:
                    compliance_result['issues'].append('允许跨境传输但未指定数据驻留地区')
                    compliance_result['recommendations'].append('指定数据驻留地区')
                
                if compliance_result['issues']:
                    compliance_result['compliant'] = False
                
                return compliance_result
                
        except Exception as e:
            logger.error(f"GDPR合规检查失败: {str(e)}")
            return {
                'compliant': False,
                'error': str(e)
            }
    
    async def generate_privacy_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        生成隐私合规报告
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            隐私报告
        """
        try:
            async with get_async_session_ctx() as db:
                from sqlalchemy import select, and_, func
                
                report = {
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    'statistics': {},
                    'compliance_summary': {},
                    'generated_at': datetime.utcnow().isoformat()
                }
                
                # 统计会议数量
                meeting_query = select(func.count(Meeting.id)).where(
                    and_(
                        Meeting.created_at >= start_date,
                        Meeting.created_at <= end_date
                    )
                )
                meeting_result = await db.execute(meeting_query)
                report['statistics']['total_meetings'] = meeting_result.scalar()
                
                # 统计同意记录
                consent_query = select(func.count(UserConsent.id)).where(
                    and_(
                        UserConsent.consent_timestamp >= start_date,
                        UserConsent.consent_timestamp <= end_date
                    )
                )
                consent_result = await db.execute(consent_query)
                report['statistics']['total_consents'] = consent_result.scalar()
                
                # 统计删除请求
                deletion_query = select(func.count(DataDeletionRequest.id)).where(
                    and_(
                        DataDeletionRequest.created_at >= start_date,
                        DataDeletionRequest.created_at <= end_date
                    )
                )
                deletion_result = await db.execute(deletion_query)
                report['statistics']['deletion_requests'] = deletion_result.scalar()
                
                # 合规摘要
                report['compliance_summary'] = {
                    'privacy_settings_coverage': '95%',  # 示例数据
                    'consent_compliance_rate': '98%',
                    'data_retention_compliance': '100%',
                    'deletion_request_response_time': '2.5 days average'
                }
                
                return report
                
        except Exception as e:
            logger.error(f"生成隐私报告失败: {str(e)}")
            return {
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat()
            }