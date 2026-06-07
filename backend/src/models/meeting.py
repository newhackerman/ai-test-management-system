"""
在线会议模块数据模型

本模块定义了在线会议相关的数据模型，包括：
- 会议基本信息管理
- 会议参与者管理
- 会议录制管理
- 会议纪要管理
- 会议聊天消息
- 会议文件共享
- 会议分析数据
- 会议模板管理
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, JSON, Enum, Boolean, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from .base import BaseModel
from sqlalchemy import UniqueConstraint


class MeetingType(PyEnum):
    """会议类型枚举"""
    PROJECT_KICKOFF = "PROJECT_KICKOFF"          # 项目启动会
    REQUIREMENT_REVIEW = "REQUIREMENT_REVIEW"    # 需求评审会
    DESIGN_REVIEW = "DESIGN_REVIEW"              # 设计评审会
    CODE_REVIEW = "CODE_REVIEW"                  # 代码评审会
    TEST_REVIEW = "TEST_REVIEW"                  # 测试评审会
    PROGRESS_SYNC = "PROGRESS_SYNC"              # 进度同步会
    PROBLEM_SOLVING = "PROBLEM_SOLVING"          # 问题解决会
    PROJECT_SUMMARY = "PROJECT_SUMMARY"          # 项目总结会
    TRAINING = "TRAINING"                        # 培训会议
    OTHER = "OTHER"                              # 其他


class MeetingStatus(PyEnum):
    """会议状态枚举"""
    SCHEDULED = "SCHEDULED"      # 已安排
    IN_PROGRESS = "IN_PROGRESS"  # 进行中
    COMPLETED = "COMPLETED"      # 已完成
    CANCELLED = "CANCELLED"      # 已取消
    POSTPONED = "POSTPONED"      # 已延期


class Meeting(BaseModel):
    """会议主表模型"""
    __tablename__ = 'meetings'
    
    # 基本信息 (id inherited from BaseModel)
    meeting_code = Column(String(50), unique=True, nullable=False, index=True, comment='会议编码')
    title = Column(String(200), nullable=False, comment='会议标题')
    description = Column(Text, comment='会议描述')
    meeting_type = Column(Enum(MeetingType), nullable=False, comment='会议类型')
    status = Column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED, nullable=False, index=True, comment='会议状态')
    
    # 时间管理
    scheduled_start_time = Column(DateTime, nullable=False, index=True, comment='计划开始时间')
    scheduled_end_time = Column(DateTime, nullable=False, index=True, comment='计划结束时间')
    actual_start_time = Column(DateTime, comment='实际开始时间')
    actual_end_time = Column(DateTime, comment='实际结束时间')
    timezone = Column(String(50), default='UTC', comment='时区')
    
    # 会议配置
    max_participants = Column(Integer, default=100, comment='最大参与人数')
    is_recording_enabled = Column(Boolean, default=False, comment='是否启用录制')
    is_waiting_room_enabled = Column(Boolean, default=True, comment='是否启用等候室')
    is_password_protected = Column(Boolean, default=False, comment='是否密码保护')
    meeting_password = Column(String(100), comment='会议密码')
    
    # 关联信息
    project_id = Column(Integer, ForeignKey('projects.id'), index=True, comment='关联项目ID')
    organizer_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True, comment='组织者ID')
    
    # 会议设置 (JSON格式存储)
    agenda = Column(JSON, comment='会议议程')
    meeting_settings = Column(JSON, comment='会议设置')
    
    # 统计信息
    participant_count = Column(Integer, default=0, comment='参与人数')
    duration_minutes = Column(Integer, default=0, comment='会议时长(分钟)')
    
    # 软删除
    deleted_at = Column(DateTime, comment='删除时间')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'meeting_code': self.meeting_code,
            'title': self.title,
            'description': self.description,
            'meeting_type': self.meeting_type.value if self.meeting_type else None,
            'status': self.status.value if self.status else None,
            'scheduled_start_time': self.scheduled_start_time.isoformat() if self.scheduled_start_time else None,
            'scheduled_end_time': self.scheduled_end_time.isoformat() if self.scheduled_end_time else None,
            'actual_start_time': self.actual_start_time.isoformat() if self.actual_start_time else None,
            'actual_end_time': self.actual_end_time.isoformat() if self.actual_end_time else None,
            'timezone': self.timezone,
            'max_participants': self.max_participants,
            'is_recording_enabled': self.is_recording_enabled,
            'is_waiting_room_enabled': self.is_waiting_room_enabled,
            'is_password_protected': self.is_password_protected,
            'project_id': self.project_id,
            'organizer_id': self.organizer_id,
            'agenda': self.agenda,
            'meeting_settings': self.meeting_settings,
            'participant_count': self.participant_count,
            'duration_minutes': self.duration_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }
    
    # 关联关系
    # 与现有系统模型的关联 - 使用字符串引用避免循环导入
    project = relationship("Project", foreign_keys="Meeting.project_id", back_populates="meetings")
    # organizer = relationship("User", foreign_keys="Meeting.organizer_id")  # 暂时注释，等User模型完善
    
    # 与会议子模型的关联
    participants = relationship("MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan")
    recordings = relationship("MeetingRecording", back_populates="meeting", cascade="all, delete-orphan")
    minutes = relationship("MeetingMinutes", back_populates="meeting", cascade="all, delete-orphan")
    chats = relationship("MeetingChat", back_populates="meeting", cascade="all, delete-orphan")
    files = relationship("MeetingFile", back_populates="meeting", cascade="all, delete-orphan")
    analytics = relationship("MeetingAnalytics", back_populates="meeting", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Meeting(id={self.id}, code='{self.meeting_code}', title='{self.title}', status='{self.status}')>"


class ParticipantRole(PyEnum):
    """参与者角色枚举"""
    ORGANIZER = "ORGANIZER"      # 组织者
    MODERATOR = "MODERATOR"      # 主持人
    PRESENTER = "PRESENTER"      # 演讲者
    PARTICIPANT = "PARTICIPANT"  # 参与者
    OBSERVER = "OBSERVER"        # 观察者


class InvitationStatus(PyEnum):
    """邀请状态枚举"""
    PENDING = "PENDING"      # 待回复
    ACCEPTED = "ACCEPTED"    # 已接受
    DECLINED = "DECLINED"    # 已拒绝
    TENTATIVE = "TENTATIVE"  # 待定


class AttendanceStatus(PyEnum):
    """出席状态枚举"""
    NOT_JOINED = "NOT_JOINED"  # 未加入
    JOINED = "JOINED"          # 已加入
    LEFT = "LEFT"              # 已离开
    KICKED_OUT = "KICKED_OUT"  # 被踢出


class MeetingParticipant(BaseModel):
    """会议参与者模型"""
    __tablename__ = 'meeting_participants'
    
    # 基本信息 (id inherited from BaseModel)
    meeting_id = Column(Integer, ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True, comment='会议ID')
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment='用户ID')
    participant_role = Column(Enum(ParticipantRole), default=ParticipantRole.PARTICIPANT, nullable=False, index=True, comment='参与角色')
    invitation_status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False, index=True, comment='邀请状态')
    attendance_status = Column(Enum(AttendanceStatus), default=AttendanceStatus.NOT_JOINED, nullable=False, index=True, comment='出席状态')
    
    # 权限设置
    can_share_screen = Column(Boolean, default=True, comment='是否可以共享屏幕')
    can_use_chat = Column(Boolean, default=True, comment='是否可以使用聊天')
    can_use_whiteboard = Column(Boolean, default=True, comment='是否可以使用白板')
    can_record = Column(Boolean, default=False, comment='是否可以录制')
    
    # 参与统计
    join_time = Column(DateTime, comment='加入时间')
    leave_time = Column(DateTime, comment='离开时间')
    total_duration_minutes = Column(Integer, default=0, comment='总参与时长(分钟)')
    speak_duration_minutes = Column(Integer, default=0, comment='发言时长(分钟)')
    interaction_count = Column(Integer, default=0, comment='互动次数')
    
    # 设备信息 (JSON格式存储)
    device_info = Column(JSON, comment='设备信息')
    network_quality = Column(JSON, comment='网络质量信息')
    
    # 邀请时间
    invited_at = Column(DateTime, default=datetime.utcnow, comment='邀请时间')
    
    # 关联关系
    meeting = relationship("Meeting", back_populates="participants")
    # user = relationship("User", foreign_keys="MeetingParticipant.user_id")  # 暂时注释
    
    # 唯一约束：一个用户在一个会议中只能有一条记录
    __table_args__ = (
        UniqueConstraint('meeting_id', 'user_id', name='uk_meeting_participant'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'},
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'user_id': self.user_id,
            'participant_role': self.participant_role.value if self.participant_role else None,
            'invitation_status': self.invitation_status.value if self.invitation_status else None,
            'attendance_status': self.attendance_status.value if self.attendance_status else None,
            'can_share_screen': self.can_share_screen,
            'can_use_chat': self.can_use_chat,
            'can_use_whiteboard': self.can_use_whiteboard,
            'can_record': self.can_record,
            'join_time': self.join_time.isoformat() if self.join_time else None,
            'leave_time': self.leave_time.isoformat() if self.leave_time else None,
            'total_duration_minutes': self.total_duration_minutes,
            'speak_duration_minutes': self.speak_duration_minutes,
            'interaction_count': self.interaction_count,
            'device_info': self.device_info,
            'network_quality': self.network_quality,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    def __repr__(self):
        return f"<MeetingParticipant(meeting_id={self.meeting_id}, user_id={self.user_id}, role='{self.participant_role}')>"


class RecordingType(PyEnum):
    """录制类型枚举"""
    FULL_MEETING = "FULL_MEETING"    # 完整会议
    SCREEN_SHARE = "SCREEN_SHARE"    # 仅屏幕共享
    AUDIO_ONLY = "AUDIO_ONLY"        # 仅音频
    HIGHLIGHTS = "HIGHLIGHTS"        # 精彩片段


class RecordingStatus(PyEnum):
    """录制状态枚举"""
    RECORDING = "RECORDING"      # 录制中
    PROCESSING = "PROCESSING"    # 处理中
    COMPLETED = "COMPLETED"      # 已完成
    FAILED = "FAILED"           # 失败
    DELETED = "DELETED"         # 已删除


class FileFormat(PyEnum):
    """文件格式枚举"""
    MP4 = "MP4"      # MP4视频格式
    WEBM = "WEBM"    # WEBM视频格式
    MP3 = "MP3"      # MP3音频格式
    M4A = "M4A"      # M4A音频格式


class MeetingRecording(BaseModel):
    """会议录制模型"""
    __tablename__ = 'meeting_recordings'
    
    # 基本信息 (id inherited from BaseModel)
    meeting_id = Column(BigInteger, ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True, comment='会议ID')
    recording_name = Column(String(200), nullable=False, comment='录制名称')
    recording_type = Column(Enum(RecordingType), default=RecordingType.FULL_MEETING, nullable=False, index=True, comment='录制类型')
    file_format = Column(Enum(FileFormat), default=FileFormat.MP4, nullable=False, comment='文件格式')
    
    # 文件信息
    file_path = Column(String(500), nullable=False, comment='文件路径')
    file_size = Column(BigInteger, default=0, comment='文件大小(字节)')
    duration_seconds = Column(Integer, default=0, comment='录制时长(秒)')
    resolution = Column(String(20), comment='视频分辨率')
    
    # 录制状态
    recording_status = Column(Enum(RecordingStatus), default=RecordingStatus.RECORDING, nullable=False, index=True, comment='录制状态')
    processing_progress = Column(Integer, default=0, comment='处理进度(百分比)')
    
    # 时间信息
    start_time = Column(DateTime, nullable=False, index=True, comment='录制开始时间')
    end_time = Column(DateTime, comment='录制结束时间')
    
    # 访问控制
    is_public = Column(Boolean, default=False, comment='是否公开')
    access_password = Column(String(100), comment='访问密码')
    download_count = Column(Integer, default=0, comment='下载次数')
    view_count = Column(Integer, default=0, comment='观看次数')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'recording_name': self.recording_name,
            'recording_type': self.recording_type.value if self.recording_type else None,
            'file_format': self.file_format.value if self.file_format else None,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'duration_seconds': self.duration_seconds,
            'resolution': self.resolution,
            'recording_status': self.recording_status.value if self.recording_status else None,
            'processing_progress': self.processing_progress,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'is_public': self.is_public,
            'download_count': self.download_count,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    # 关联关系
    meeting = relationship("Meeting", back_populates="recordings")
    # creator = relationship("User", foreign_keys="MeetingRecording.created_by")  # 暂时注释，等User模型关系完善后启用
    
    def __repr__(self):
        return f"<MeetingRecording(id={self.id}, meeting_id={self.meeting_id}, name='{self.recording_name}', status='{self.recording_status}')>"


class MinuteType(PyEnum):
    """纪要类型枚举"""
    AUTO_GENERATED = "AUTO_GENERATED"      # 自动生成
    MANUAL_CREATED = "MANUAL_CREATED"      # 手动创建
    AI_ENHANCED = "AI_ENHANCED"            # AI增强
    COLLABORATIVE = "COLLABORATIVE"        # 协作编辑


class GenerationMethod(PyEnum):
    """生成方式枚举"""
    SPEECH_TO_TEXT = "SPEECH_TO_TEXT"      # 语音转文字
    MANUAL_INPUT = "MANUAL_INPUT"          # 手动输入
    AI_ANALYSIS = "AI_ANALYSIS"            # AI分析
    TEMPLATE_BASED = "TEMPLATE_BASED"      # 基于模板


class MinuteStatus(PyEnum):
    """纪要状态枚举"""
    DRAFT = "DRAFT"              # 草稿
    UNDER_REVIEW = "UNDER_REVIEW"  # 审核中
    APPROVED = "APPROVED"        # 已审批
    PUBLISHED = "PUBLISHED"      # 已发布
    ARCHIVED = "ARCHIVED"        # 已归档


class MeetingMinutes(BaseModel):
    """会议纪要模型"""
    __tablename__ = 'meeting_minutes'
    
    # 基本信息 (id inherited from BaseModel)
    meeting_id = Column(BigInteger, ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True, comment='会议ID')
    title = Column(String(200), nullable=False, comment='纪要标题')
    content = Column(Text, comment='纪要内容')
    summary = Column(Text, comment='会议摘要')
    
    # 纪要类型
    minute_type = Column(Enum(MinuteType), default=MinuteType.MANUAL_CREATED, nullable=False, index=True, comment='纪要类型')
    generation_method = Column(Enum(GenerationMethod), comment='生成方式')
    
    # 结构化内容 (JSON格式存储)
    agenda_items = Column(JSON, comment='议程项目')
    decisions = Column(JSON, comment='决策事项')
    action_items = Column(JSON, comment='行动项目')
    attendees = Column(JSON, comment='参会人员')
    key_points = Column(JSON, comment='关键要点')
    
    # 状态管理
    status = Column(Enum(MinuteStatus), default=MinuteStatus.DRAFT, nullable=False, index=True, comment='纪要状态')
    approval_required = Column(Boolean, default=False, comment='是否需要审批')
    
    # 版本管理
    version = Column(String(20), default='1.0', comment='版本号')
    parent_minute_id = Column(BigInteger, ForeignKey('meeting_minutes.id'), comment='父纪要ID')
    
    # 审批信息
    approved_by = Column(BigInteger, ForeignKey('users.id'), comment='审批者ID')
    approved_at = Column(DateTime, comment='审批时间')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'minute_type': self.minute_type.value if self.minute_type else None,
            'generation_method': self.generation_method.value if self.generation_method else None,
            'agenda_items': self.agenda_items,
            'decisions': self.decisions,
            'action_items': self.action_items,
            'attendees': self.attendees,
            'key_points': self.key_points,
            'status': self.status.value if self.status else None,
            'approval_required': self.approval_required,
            'version': self.version,
            'parent_minute_id': self.parent_minute_id,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    # 关联关系
    meeting = relationship("Meeting", back_populates="minutes")
    # creator = relationship("User", foreign_keys="MeetingMinutes.created_by")  # 暂时注释
    # approver = relationship("User", foreign_keys="MeetingMinutes.approved_by")  # 暂时注释
    parent_minute = relationship("MeetingMinutes", remote_side="MeetingMinutes.id")
    
    def __repr__(self):
        return f"<MeetingMinutes(id={self.id}, meeting_id={self.meeting_id}, title='{self.title}', status='{self.status}')>"


class MessageType(PyEnum):
    """消息类型枚举"""
    TEXT = "TEXT"              # 文本消息
    IMAGE = "IMAGE"            # 图片消息
    FILE = "FILE"              # 文件消息
    SYSTEM = "SYSTEM"          # 系统消息
    EMOJI = "EMOJI"            # 表情消息


class MeetingChat(BaseModel):
    """会议聊天消息模型"""
    __tablename__ = 'meeting_chats'
    
    # 基本信息 (id inherited from BaseModel)
    meeting_id = Column(BigInteger, ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True, comment='会议ID')
    sender_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, index=True, comment='发送者ID')
    
    # 消息内容
    message_type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False, comment='消息类型')
    content = Column(Text, nullable=False, comment='消息内容')
    
    # 消息属性
    is_private = Column(Boolean, default=False, comment='是否私聊')
    recipient_id = Column(BigInteger, ForeignKey('users.id'), comment='接收者ID(私聊时使用)')
    
    # 附加信息 (JSON格式存储)
    message_metadata = Column(JSON, comment='消息元数据')
    
    # 时间戳
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment='发送时间')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'sender_id': self.sender_id,
            'message_type': self.message_type.value if self.message_type else None,
            'content': self.content,
            'is_private': self.is_private,
            'recipient_id': self.recipient_id,
            'message_metadata': self.message_metadata,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    # 关联关系
    meeting = relationship("Meeting", back_populates="chats")
    # sender = relationship("User", foreign_keys="MeetingChat.sender_id")  # 暂时注释
    # recipient = relationship("User", foreign_keys="MeetingChat.recipient_id")  # 暂时注释
    
    def __repr__(self):
        return f"<MeetingChat(id={self.id}, meeting_id={self.meeting_id}, sender_id={self.sender_id}, type='{self.message_type}')>"


class FileShareStatus(PyEnum):
    """文件共享状态枚举"""
    UPLOADING = "UPLOADING"      # 上传中
    AVAILABLE = "AVAILABLE"      # 可用
    PROCESSING = "PROCESSING"    # 处理中
    FAILED = "FAILED"           # 失败
    DELETED = "DELETED"         # 已删除


class MeetingFile(BaseModel):
    """会议文件共享模型"""
    __tablename__ = 'meeting_files'
    
    # 基本信息 (id inherited from BaseModel)
    meeting_id = Column(BigInteger, ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, index=True, comment='会议ID')
    uploader_id = Column(BigInteger, ForeignKey('users.id'), nullable=False, index=True, comment='上传者ID')
    
    # 文件信息
    file_name = Column(String(255), nullable=False, comment='文件名')
    file_path = Column(String(500), nullable=False, comment='文件路径')
    file_size = Column(BigInteger, nullable=False, comment='文件大小(字节)')
    file_type = Column(String(100), nullable=False, comment='文件类型')
    mime_type = Column(String(100), comment='MIME类型')
    
    # 状态信息
    status = Column(Enum(FileShareStatus), default=FileShareStatus.UPLOADING, nullable=False, index=True, comment='文件状态')
    
    # 访问控制
    is_public = Column(Boolean, default=True, comment='是否公开')
    download_count = Column(Integer, default=0, comment='下载次数')
    
    # 文件描述
    description = Column(Text, comment='文件描述')
    
    # 附加信息 (JSON格式存储)
    file_metadata = Column(JSON, comment='文件元数据')
    
    # 上传时间
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment='上传时间')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'uploader_id': self.uploader_id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'status': self.status.value if self.status else None,
            'is_public': self.is_public,
            'download_count': self.download_count,
            'description': self.description,
            'file_metadata': self.file_metadata,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    # 关联关系
    meeting = relationship("Meeting", back_populates="files")
    # uploader = relationship("User", foreign_keys="MeetingFile.uploader_id")  # 暂时注释
    
    def __repr__(self):
        return f"<MeetingFile(id={self.id}, meeting_id={self.meeting_id}, file_name='{self.file_name}', status='{self.status}')>"


class MeetingAnalytics(BaseModel):
    """会议分析数据模型"""
    __tablename__ = 'meeting_analytics'
    
    # 基本信息 (id inherited from BaseModel)
    meeting_id = Column(BigInteger, ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False, unique=True, comment='会议ID')
    
    # 参与度分析
    total_participants = Column(Integer, default=0, comment='总参与人数')
    peak_participants = Column(Integer, default=0, comment='峰值参与人数')
    avg_participation_rate = Column(DECIMAL(5, 2), comment='平均参与率')
    
    # 发言分析
    total_speaking_time = Column(Integer, default=0, comment='总发言时长(秒)')
    avg_speaking_time_per_person = Column(Integer, default=0, comment='人均发言时长(秒)')
    speaking_balance_score = Column(DECIMAL(5, 2), comment='发言均衡度评分')
    
    # 互动分析
    total_chat_messages = Column(Integer, default=0, comment='聊天消息总数')
    total_file_shares = Column(Integer, default=0, comment='文件分享总数')
    screen_share_duration = Column(Integer, default=0, comment='屏幕共享时长(秒)')
    
    # 质量分析
    audio_quality_score = Column(DECIMAL(5, 2), comment='音频质量评分')
    video_quality_score = Column(DECIMAL(5, 2), comment='视频质量评分')
    network_stability_score = Column(DECIMAL(5, 2), comment='网络稳定性评分')
    
    # 效率分析
    agenda_completion_rate = Column(DECIMAL(5, 2), comment='议程完成率')
    decision_count = Column(Integer, default=0, comment='决策数量')
    action_item_count = Column(Integer, default=0, comment='行动项数量')
    
    # 情感分析
    overall_sentiment_score = Column(DECIMAL(5, 2), comment='整体情感评分')
    engagement_score = Column(DECIMAL(5, 2), comment='参与度评分')
    
    # 详细分析数据 (JSON格式存储)
    detailed_analytics = Column(JSON, comment='详细分析数据')
    
    # 分析时间
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment='分析时间')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'total_participants': self.total_participants,
            'peak_participants': self.peak_participants,
            'avg_participation_rate': float(self.avg_participation_rate) if self.avg_participation_rate else None,
            'total_speaking_time': self.total_speaking_time,
            'avg_speaking_time_per_person': self.avg_speaking_time_per_person,
            'speaking_balance_score': float(self.speaking_balance_score) if self.speaking_balance_score else None,
            'total_chat_messages': self.total_chat_messages,
            'total_file_shares': self.total_file_shares,
            'screen_share_duration': self.screen_share_duration,
            'audio_quality_score': float(self.audio_quality_score) if self.audio_quality_score else None,
            'video_quality_score': float(self.video_quality_score) if self.video_quality_score else None,
            'network_stability_score': float(self.network_stability_score) if self.network_stability_score else None,
            'agenda_completion_rate': float(self.agenda_completion_rate) if self.agenda_completion_rate else None,
            'decision_count': self.decision_count,
            'action_item_count': self.action_item_count,
            'overall_sentiment_score': float(self.overall_sentiment_score) if self.overall_sentiment_score else None,
            'engagement_score': float(self.engagement_score) if self.engagement_score else None,
            'detailed_analytics': self.detailed_analytics,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    # 关联关系
    meeting = relationship("Meeting", back_populates="analytics")
    
    def __repr__(self):
        return f"<MeetingAnalytics(id={self.id}, meeting_id={self.meeting_id}, analyzed_at='{self.analyzed_at}')>"


class TemplateCategory(PyEnum):
    """模板分类枚举"""
    PROJECT_MANAGEMENT = "PROJECT_MANAGEMENT"    # 项目管理
    REQUIREMENT_REVIEW = "REQUIREMENT_REVIEW"    # 需求评审
    DESIGN_REVIEW = "DESIGN_REVIEW"              # 设计评审
    TECHNICAL_DISCUSSION = "TECHNICAL_DISCUSSION"  # 技术讨论
    TRAINING = "TRAINING"                        # 培训
    GENERAL = "GENERAL"                          # 通用


class MeetingTemplate(BaseModel):
    """会议模板模型"""
    __tablename__ = 'meeting_templates'
    
    # 基本信息 (id inherited from BaseModel)
    template_name = Column(String(200), nullable=False, comment='模板名称')
    description = Column(Text, comment='模板描述')
    category = Column(Enum(TemplateCategory), nullable=False, index=True, comment='模板分类')
    
    # 模板配置
    meeting_type = Column(Enum(MeetingType), nullable=False, comment='会议类型')
    default_duration_minutes = Column(Integer, default=60, comment='默认时长(分钟)')
    max_participants = Column(Integer, default=100, comment='最大参与人数')
    
    # 模板内容 (JSON格式存储)
    agenda_template = Column(JSON, comment='议程模板')
    settings_template = Column(JSON, comment='设置模板')
    roles_template = Column(JSON, comment='角色模板')
    
    # 状态管理
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_public = Column(Boolean, default=False, comment='是否公开')
    
    # 使用统计
    usage_count = Column(Integer, default=0, comment='使用次数')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'template_name': self.template_name,
            'description': self.description,
            'category': self.category.value if self.category else None,
            'meeting_type': self.meeting_type.value if self.meeting_type else None,
            'default_duration_minutes': self.default_duration_minutes,
            'max_participants': self.max_participants,
            'agenda_template': self.agenda_template,
            'settings_template': self.settings_template,
            'roles_template': self.roles_template,
            'is_active': self.is_active,
            'is_public': self.is_public,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    # 关联关系 - 暂时注释，等User模型关系完善后启用
    # creator = relationship("User", foreign_keys="MeetingTemplate.created_by")
    
    def __repr__(self):
        return f"<MeetingTemplate(id={self.id}, name='{self.template_name}', category='{self.category}')>"