"""
会议管理核心服务

本模块实现会议管理的核心业务逻辑，包括：
- 会议创建与调度
- 智能时间调度
- 会议更新和删除
- 参与者邀请管理
- 会议加入验证
- 会议状态管理
- 会议权限控制
- 会议通知服务
"""
import asyncio
import logging
import secrets
import string
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text, update, delete, exists
from sqlalchemy.orm import selectinload, joinedload
from fastapi import Depends

from ..core.database import get_async_session
from ..core.config import get_settings
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.meeting import (
    Meeting, MeetingParticipant, MeetingType, MeetingStatus,
    ParticipantRole, InvitationStatus, AttendanceStatus,
    MeetingMinutes, MinuteType, GenerationMethod, MinuteStatus,
    MeetingFile, FileShareStatus, MeetingChat, MessageType
)
from ..models.user import User
from ..models.project import Project
from ..services.permission_service import PermissionService
from ..services.user import UserService
from .meeting_notification_service import MeetingNotificationService
from .email_service import EmailService

logger = logging.getLogger(__name__)


# 白板状态（模块级内存存储）：MeetingService 每次请求新建实例，实例
# 内存跨请求即丢；白板无专用表，先放进程内存字典，key 为 meeting_id。
# 后端重启即丢，与房间同一约束；如需持久化再建表。
_WHITEBOARD_STATES: Dict[int, Dict[str, Any]] = {}


class MeetingService:
    """会议管理核心服务"""
    
    def __init__(self, db: AsyncSession, email_service: Optional[EmailService] = None):
        self.db = db
        self.permission_service = PermissionService(db)
        self.user_service = UserService(db)
        self.notification_service = MeetingNotificationService(db, email_service)

    def _normalize_meeting_data(self, meeting_data: Any) -> Dict[str, Any]:
        """Normalize API request models into the dict shape used by the service."""
        if hasattr(meeting_data, "dict"):
            normalized = meeting_data.dict(exclude_none=True)
        else:
            normalized = dict(meeting_data or {})

        def plain(value: Any) -> Any:
            if hasattr(value, "dict"):
                return {key: plain(item) for key, item in value.dict(exclude_none=True).items()}
            if isinstance(value, dict):
                return {key: plain(item) for key, item in value.items()}
            if isinstance(value, list):
                return [plain(item) for item in value]
            if hasattr(value, "value"):
                return value.value
            return value

        normalized = {key: plain(value) for key, value in normalized.items()}
        participant_ids = normalized.get("participant_ids") or []
        if participant_ids and not normalized.get("participants"):
            normalized["participants"] = [
                {"user_id": int(user_id), "participant_role": "PARTICIPANT"}
                for user_id in participant_ids
                if user_id
            ]
        return normalized
    
    async def create_meeting(self, meeting_data: Dict[str, Any], organizer_id: int) -> Meeting:
        """
        创建会议
        
        Args:
            meeting_data: 会议数据
            organizer_id: 组织者ID
            
        Returns:
            创建的会议对象
            
        Raises:
            ValidationError: 数据验证失败
            PermissionError: 权限不足
        """
        meeting_data = self._normalize_meeting_data(meeting_data)

        # 1. 验证会议数据
        await self._validate_meeting_data(meeting_data)
        
        # 2. 验证创建权限
        await self._validate_create_permission(organizer_id, meeting_data.get('project_id'))
        
        # 3. 生成会议编码
        meeting_code = await self._generate_meeting_code()
        
        # 4. 智能时间调度（如果启用）
        if meeting_data.get('auto_schedule', False):
            optimal_time = await self._find_optimal_time(
                meeting_data.get('participants', []),
                meeting_data.get('duration_minutes', 60),
                meeting_data.get('preferred_time_range', {})
            )
            meeting_data['scheduled_start_time'] = optimal_time
            meeting_data['scheduled_end_time'] = optimal_time + timedelta(
                minutes=meeting_data.get('duration_minutes', 60)
            )
        
        # 5. 创建会议实体
        meeting = Meeting(
            meeting_code=meeting_code,
            title=meeting_data['title'],
            description=meeting_data.get('description'),
            meeting_type=MeetingType(meeting_data['meeting_type']),
            scheduled_start_time=meeting_data['scheduled_start_time'],
            scheduled_end_time=meeting_data['scheduled_end_time'],
            timezone=meeting_data.get('timezone', 'UTC'),
            max_participants=meeting_data.get('max_participants', 100),
            is_recording_enabled=meeting_data.get('is_recording_enabled', False),
            is_waiting_room_enabled=meeting_data.get('is_waiting_room_enabled', True),
            is_password_protected=meeting_data.get('is_password_protected', False),
            meeting_password=meeting_data.get('meeting_password'),
            project_id=meeting_data.get('project_id'),
            organizer_id=organizer_id,
            agenda=meeting_data.get('agenda'),
            meeting_settings=meeting_data.get('meeting_settings', {}),
            created_by=organizer_id
        )
        
        # 6. 保存会议
        self.db.add(meeting)
        await self.db.flush()  # 获取会议ID
        
        # 7. 添加组织者为参与者
        await self._add_organizer_as_participant(meeting.id, organizer_id)
        
        # 8. 添加其他参与者
        if meeting_data.get('participants'):
            await self._add_participants(meeting.id, meeting_data['participants'], organizer_id)

        meeting.participant_count = await self._get_participant_count(meeting.id)
        
        # 9. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)

        # 10. 发送邀请通知（在提交后发送，避免通知落库时提交半成品会议数据）
        await self._send_invitations(meeting)

        logger.info(f"Created meeting {meeting.meeting_code} by user {organizer_id}")
        return meeting

    async def get_meetings(self, query_params: Any, user_id: int) -> Tuple[List[Meeting], int]:
        """获取当前用户可访问的会议列表。"""
        query_data = query_params.dict(exclude_none=True) if hasattr(query_params, "dict") else dict(query_params or {})
        query_data = {
            key: value.value if hasattr(value, "value") else value
            for key, value in query_data.items()
        }

        filters = [Meeting.deleted_at.is_(None)]

        if query_data.get("meeting_type"):
            filters.append(Meeting.meeting_type == query_data["meeting_type"])
        if query_data.get("status"):
            filters.append(Meeting.status == query_data["status"])
        if query_data.get("project_id"):
            filters.append(Meeting.project_id == query_data["project_id"])
        if query_data.get("organizer_id"):
            filters.append(Meeting.organizer_id == query_data["organizer_id"])
        if query_data.get("start_date"):
            filters.append(Meeting.scheduled_start_time >= query_data["start_date"])
        if query_data.get("end_date"):
            filters.append(Meeting.scheduled_start_time <= query_data["end_date"])
        if query_data.get("keyword"):
            keyword = f"%{query_data['keyword']}%"
            filters.append(or_(Meeting.title.ilike(keyword), Meeting.description.ilike(keyword)))

        if not await self.permission_service.check_permission(user_id, "meeting:view"):
            participant_exists = exists().where(
                and_(
                    MeetingParticipant.meeting_id == Meeting.id,
                    MeetingParticipant.user_id == user_id,
                )
            )
            filters.append(or_(Meeting.organizer_id == user_id, participant_exists))

        sort_columns = {
            "scheduled_start_time": Meeting.scheduled_start_time,
            "created_at": Meeting.created_at,
            "updated_at": Meeting.updated_at,
            "title": Meeting.title,
        }
        sort_column = sort_columns.get(query_data.get("sort_by") or "scheduled_start_time", Meeting.scheduled_start_time)
        order_by = asc(sort_column) if query_data.get("sort_order") == "asc" else desc(sort_column)

        count_result = await self.db.execute(select(func.count(Meeting.id)).where(and_(*filters)))
        total = int(count_result.scalar() or 0)

        page = int(query_data.get("page") or 1)
        page_size = int(query_data.get("page_size") or 20)
        result = await self.db.execute(
            select(Meeting)
            .where(and_(*filters))
            .order_by(order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_meeting_by_id(self, meeting_id: int, user_id: int) -> Meeting:
        """获取会议详情并校验访问权限。"""
        meeting = await self._get_meeting_by_id(meeting_id)
        if meeting.organizer_id == user_id:
            return meeting

        if await self.permission_service.check_permission(user_id, "meeting:view"):
            return meeting

        participant = await self._get_participant_by_meeting_and_user(meeting_id, user_id)
        if participant:
            return meeting

        raise PermissionError("无权限查看会议")

    async def get_meeting_by_code(self, meeting_code: str, user_id: int) -> Meeting:
        """按会议编码获取会议详情（供 /meetings/join/:meetingCode 入口）。

        先按编码查到会议，再复用 get_meeting_by_id 做同一权限校验。
        """
        query = select(Meeting).where(
            and_(Meeting.meeting_code == meeting_code, Meeting.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        if not meeting:
            raise NotFoundError("会议不存在")
        return await self.get_meeting_by_id(meeting.id, user_id)

    async def get_participants(self, meeting_id: int, query_params: Any, user_id: int) -> Tuple[List[MeetingParticipant], Dict[str, Any]]:
        """
        获取会议参与者列表及统计信息。

        Args:
            meeting_id: 会议ID
            query_params: 查询参数（支持 role / invitation_status / attendance_status / include_user_info）
            user_id: 当前用户ID（用于权限校验）

        Returns:
            (participants, statistics) 元组
        """
        # 权限校验：必须能查看该会议
        await self.get_meeting_by_id(meeting_id, user_id)

        # 构建查询
        stmt = select(MeetingParticipant).where(MeetingParticipant.meeting_id == meeting_id)
        role = getattr(query_params, "role", None)
        invitation_status = getattr(query_params, "invitation_status", None)
        attendance_status = getattr(query_params, "attendance_status", None)
        if role is not None:
            stmt = stmt.where(MeetingParticipant.participant_role == role)
        if invitation_status is not None:
            stmt = stmt.where(MeetingParticipant.invitation_status == invitation_status)
        if attendance_status is not None:
            stmt = stmt.where(MeetingParticipant.attendance_status == attendance_status)

        result = await self.db.execute(stmt)
        participants = list(result.scalars().all())

        # 统计信息
        roles_summary: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        online_count = 0
        for p in participants:
            role_val = p.participant_role.value if hasattr(p.participant_role, "value") else str(p.participant_role)
            roles_summary[role_val] = roles_summary.get(role_val, 0) + 1
            attend_val = p.attendance_status.value if hasattr(p.attendance_status, "value") else str(p.attendance_status)
            by_status[attend_val] = by_status.get(attend_val, 0) + 1
            if attend_val == "PRESENT":
                online_count += 1

        statistics = {
            "total": len(participants),
            "online_count": online_count,
            "roles_summary": roles_summary,
            # 补全 ParticipantStatistics schema 所需字段
            "total_participants": len(participants),
            "active_participants": online_count,
            "by_role": roles_summary,
            "by_status": by_status,
            "average_duration_minutes": 0.0,
            "total_interaction_count": 0,
        }
        return participants, statistics

    async def get_participant_statistics(self, meeting_id: int, user_id: int) -> Dict[str, Any]:
        """获取会议参与者统计信息。"""
        _, stats = await self.get_participants(meeting_id, type("QP", (), {})(), user_id)
        return stats

    async def get_meeting_status(self, meeting_id: int, user_id: int) -> Dict[str, Any]:
        """
        获取会议实时状态信息。

        Returns 包含: status, participant_count, is_recording, start_time,
        duration_minutes, network_quality
        """
        meeting = await self.get_meeting_by_id(meeting_id, user_id)
        participant_count = await self._get_participant_count(meeting_id)
        status_val = meeting.status.value if hasattr(meeting.status, "value") else str(meeting.status)
        duration_minutes = 0
        actual_start = getattr(meeting, "actual_start_time", None)
        if actual_start and status_val in ("IN_PROGRESS", "COMPLETED", "ENDED"):
            end_ref = getattr(meeting, "actual_end_time", None) or datetime.utcnow()
            if end_ref >= actual_start:
                duration_minutes = int((end_ref - actual_start).total_seconds() // 60)
        return {
            "status": status_val,
            "participant_count": participant_count,
            "is_recording": getattr(meeting, "is_recording", False),
            "start_time": actual_start,
            "duration_minutes": duration_minutes,
            "network_quality": getattr(meeting, "network_quality", "good"),
        }

    async def send_chat_message(self, meeting_id: int, sender_id: int,
                                request: Any) -> MeetingChat:
        """发送聊天消息并落库到 meeting_chats 表。

        路由曾调用本方法但服务类中并不存在（AttributeError -> 500），
        会议聊天发送端点整体不可用。历史查询见 get_chat_history。
        """
        # 校验会议存在及访问权限
        await self.get_meeting_by_id(meeting_id, sender_id)

        if getattr(request, 'is_private', False) and not getattr(request, 'recipient_id', None):
            raise ValidationError("私聊消息必须指定接收者")

        metadata = dict(getattr(request, 'metadata', None) or {})
        reply_to_id = getattr(request, 'reply_to_id', None)
        if reply_to_id:
            metadata['reply_to_id'] = reply_to_id

        message = MeetingChat(
            meeting_id=meeting_id,
            sender_id=sender_id,
            message_type=MessageType(getattr(request.message_type, 'value', request.message_type)),
            content=request.content.strip(),
            is_private=bool(getattr(request, 'is_private', False)),
            recipient_id=getattr(request, 'recipient_id', None),
            message_metadata=metadata or None,
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_chat_history(self, meeting_id: int, query_params: Any,
                               user_id: int) -> Tuple[List[Any], int]:
        """获取会议聊天历史（读 meeting_chats 表，按发送时间升序）。"""
        await self.get_meeting_by_id(meeting_id, user_id)

        conditions = [MeetingChat.meeting_id == meeting_id]
        if query_params:
            include_private = getattr(query_params, 'include_private', False)
            if not include_private:
                # 默认只看公开消息；自己发出/收到的私聊也可见。
                conditions.append(or_(
                    MeetingChat.is_private == False,  # noqa: E712
                    MeetingChat.sender_id == user_id,
                    MeetingChat.recipient_id == user_id,
                ))
            message_type = getattr(query_params, 'message_type', None)
            if message_type:
                conditions.append(MeetingChat.message_type == MessageType(
                    getattr(message_type, 'value', message_type)))
            sender_id = getattr(query_params, 'sender_id', None)
            if sender_id:
                conditions.append(MeetingChat.sender_id == sender_id)
            start_time = getattr(query_params, 'start_time', None)
            if start_time:
                conditions.append(MeetingChat.sent_at >= start_time)
            end_time = getattr(query_params, 'end_time', None)
            if end_time:
                conditions.append(MeetingChat.sent_at <= end_time)
            keyword = getattr(query_params, 'keyword', None)
            if keyword:
                conditions.append(MeetingChat.content.ilike(f"%{keyword}%"))

        total_result = await self.db.execute(
            select(func.count()).select_from(MeetingChat).where(and_(*conditions))
        )
        total = total_result.scalar_one()

        page = max(getattr(query_params, 'page', 1) or 1, 1)
        page_size = max(getattr(query_params, 'page_size', 50) or 50, 1)
        query = (
            select(MeetingChat)
            .where(and_(*conditions))
            .order_by(asc(MeetingChat.sent_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    # 允许上传的文件扩展名（与上传接口文档一致：文档 / 图片 /
    # 视频 / 压缩包）。可执行与脚本类型（php/exe/sh/py/js 等）
    # 不在白名单内，直接拒绝。
    ALLOWED_UPLOAD_EXTENSIONS = frozenset({
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md",
        "jpg", "jpeg", "png", "gif", "svg", "bmp", "webp",
        "mp4", "avi", "mov", "mkv", "webm",
        "zip", "rar", "7z", "tar", "gz",
    })

    async def upload_file(self, meeting_id: int, uploader_id: int,
                          upload_request: Any, file: Any) -> MeetingFile:
        """上传文件到会议。

        路由曾调用本方法但服务类中并不存在（AttributeError -> 500），
        会议文件上传端点整体不可用。本实现：校验会议存在、按白名单
        校验扩展名（可执行/脚本类型直接拒绝）、落盘到
        UPLOAD_DIR/meetings/{meeting_id}/ 下的随机文件名（防路径穿越
        与同名覆盖）、创建 MeetingFile 记录。
        """
        meeting = await self.db.get(Meeting, meeting_id)
        if not meeting or meeting.deleted_at is not None:
            raise NotFoundError("会议不存在")

        original_name = (getattr(upload_request, "file_name", "") or "").strip()
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if not ext or ext not in self.ALLOWED_UPLOAD_EXTENSIONS:
            raise ValidationError(f"不支持的文件类型: .{ext or '?'}")

        content = await file.read()
        max_size = get_settings().MAX_FILE_SIZE
        if len(content) > max_size:
            raise ValidationError(
                f"文件大小不能超过{max_size // (1024 * 1024)}MB"
            )

        upload_dir = Path(get_settings().UPLOAD_DIR) / "meetings" / str(meeting_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        file_path = upload_dir / stored_name
        file_path.write_bytes(content)

        record = MeetingFile(
            meeting_id=meeting_id,
            uploader_id=uploader_id,
            file_name=original_name,
            file_path=str(file_path),
            file_size=len(content),
            file_type=ext,
            mime_type=getattr(upload_request, "mime_type", None),
            status=FileShareStatus.AVAILABLE,
            is_public=getattr(upload_request, "is_public", True),
            description=getattr(upload_request, "description", None),
            file_metadata={"original_name": original_name},
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_files(self, meeting_id: int, query_params: Any,
                        user_id: int) -> Tuple[List[MeetingFile], int]:
        """
        获取会议共享文件列表及总大小。

        会议不存在时抛出 NotFoundError（由路由层转为 404）；
        无权限时抛出 PermissionError。
        """
        # 校验会议存在及访问权限
        await self.get_meeting_by_id(meeting_id, user_id)

        conditions = [MeetingFile.meeting_id == meeting_id]

        include_deleted = getattr(query_params, 'include_deleted', False) if query_params else False
        if not include_deleted:
            conditions.append(MeetingFile.status != FileShareStatus.DELETED)

        if query_params:
            file_type = getattr(query_params, 'file_type', None)
            if file_type:
                conditions.append(MeetingFile.file_type == file_type)

            status_filter = getattr(query_params, 'status', None)
            if status_filter:
                conditions.append(MeetingFile.status == status_filter)

            uploader_id = getattr(query_params, 'uploader_id', None)
            if uploader_id:
                conditions.append(MeetingFile.uploader_id == uploader_id)

            start_date = getattr(query_params, 'start_date', None)
            if start_date:
                conditions.append(MeetingFile.uploaded_at >= start_date)

            end_date = getattr(query_params, 'end_date', None)
            if end_date:
                conditions.append(MeetingFile.uploaded_at <= end_date)

            keyword = getattr(query_params, 'keyword', None)
            if keyword:
                conditions.append(MeetingFile.file_name.ilike(f"%{keyword}%"))

        query = (
            select(MeetingFile)
            .where(and_(*conditions))
            .order_by(desc(MeetingFile.uploaded_at))
        )
        result = await self.db.execute(query)
        files = result.scalars().all()

        total_size = sum((f.file_size or 0) for f in files)
        return files, total_size

    async def handle_whiteboard_action(self, meeting_id: int, user_id: int,
                                       action: Any) -> Dict[str, Any]:
        """执行白板操作并更新内存中的白板状态。

        路由曾调用本方法但服务类中并不存在（AttributeError -> 500）。
        白板无专用表，状态放模块级 _WHITEBOARD_STATES（进程内存，
        重启即丢）。draw 追加一笔 stroke；erase 按 stroke id 删除；
        clear 清空；undo 撤回最后一笔；redo 暂不支持（返回当前状态）。
        每次操作 version + 1。
        """
        # 校验会议存在及访问权限
        await self.get_meeting_by_id(meeting_id, user_id)

        action_type = getattr(action, 'action_type', None)
        data = dict(getattr(action, 'data', None) or {})
        state = _WHITEBOARD_STATES.setdefault(meeting_id, {
            'whiteboard_id': f"wb_{meeting_id}",
            'meeting_id': meeting_id,
            'content': {'strokes': []},
            'version': 1,
            'last_modified': datetime.utcnow(),
            'last_modified_by': user_id,
        })
        strokes = state['content'].setdefault('strokes', [])

        if action_type == 'draw':
            strokes.append({**data, 'user_id': user_id})
        elif action_type == 'erase':
            stroke_id = data.get('stroke_id', data.get('id'))
            if stroke_id is not None:
                state['content']['strokes'] = [
                    s for s in strokes if s.get('id') != stroke_id and s.get('stroke_id') != stroke_id
                ]
        elif action_type == 'clear':
            state['content']['strokes'] = []
        elif action_type == 'undo':
            if strokes:
                strokes.pop()
        elif action_type == 'redo':
            pass  # 暂无重做栈，返回当前状态
        else:
            raise ValidationError(f"不支持的白板操作类型: {action_type}")

        state['version'] += 1
        state['last_modified'] = datetime.utcnow()
        state['last_modified_by'] = user_id
        # 路由层用原始 JSONResponse 返回本字典，datetime 无法序列化会
        # 500；这里把时间转成 ISO 字符串（GET 端走 WhiteboardState
        # 模型解析，不受影响）。
        result = dict(state)
        result['last_modified'] = state['last_modified'].isoformat()
        return result

    async def get_whiteboard_state(self, meeting_id: int,
                                   user_id: int) -> Dict[str, Any]:
        """
        获取会议白板状态（读模块级内存；无操作记录时返回空白状态）。

        会议不存在时抛出 NotFoundError（由路由层转为 404）；
        无权限时抛出 PermissionError。
        返回的字典键需与 WhiteboardState 模型字段匹配。
        """
        # 校验会议存在及访问权限
        await self.get_meeting_by_id(meeting_id, user_id)

        state = _WHITEBOARD_STATES.get(meeting_id)
        if state:
            return dict(state)
        return {
            'whiteboard_id': f"wb_{meeting_id}",
            'meeting_id': meeting_id,
            'content': {},
            'version': 1,
            'last_modified': datetime.utcnow(),
            'last_modified_by': user_id,
        }

    async def update_meeting(self, meeting_id: int, update_data: Dict[str, Any], user_id: int) -> Meeting:
        """
        更新会议信息
        
        Args:
            meeting_id: 会议ID
            update_data: 更新数据
            user_id: 操作用户ID
            
        Returns:
            更新后的会议对象
            
        Raises:
            NotFoundError: 会议不存在
            PermissionError: 权限不足
            ValidationError: 数据验证失败
        """
        update_data = self._normalize_meeting_data(update_data)

        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证更新权限
        await self._validate_update_permission(meeting, user_id)
        
        # 3. 验证更新数据
        await self._validate_update_data(update_data, meeting)
        
        # 4. 记录变更内容
        changes = {}
        
        # 5. 更新基本信息
        if 'title' in update_data:
            changes['title'] = {'old': meeting.title, 'new': update_data['title']}
            meeting.title = update_data['title']
        
        if 'description' in update_data:
            changes['description'] = {'old': meeting.description, 'new': update_data['description']}
            meeting.description = update_data['description']
        
        if 'meeting_type' in update_data:
            changes['meeting_type'] = {'old': meeting.meeting_type.value, 'new': update_data['meeting_type']}
            meeting.meeting_type = MeetingType(update_data['meeting_type'])
        
        # 6. 更新时间信息
        if 'scheduled_start_time' in update_data:
            changes['scheduled_start_time'] = {
                'old': meeting.scheduled_start_time.isoformat(),
                'new': update_data['scheduled_start_time'].isoformat()
            }
            meeting.scheduled_start_time = update_data['scheduled_start_time']
        
        if 'scheduled_end_time' in update_data:
            changes['scheduled_end_time'] = {
                'old': meeting.scheduled_end_time.isoformat(),
                'new': update_data['scheduled_end_time'].isoformat()
            }
            meeting.scheduled_end_time = update_data['scheduled_end_time']
        
        if 'timezone' in update_data:
            changes['timezone'] = {'old': meeting.timezone, 'new': update_data['timezone']}
            meeting.timezone = update_data['timezone']
        
        # 7. 更新会议配置
        if 'max_participants' in update_data:
            changes['max_participants'] = {'old': meeting.max_participants, 'new': update_data['max_participants']}
            meeting.max_participants = update_data['max_participants']
        
        if 'is_recording_enabled' in update_data:
            changes['is_recording_enabled'] = {'old': meeting.is_recording_enabled, 'new': update_data['is_recording_enabled']}
            meeting.is_recording_enabled = update_data['is_recording_enabled']
        
        if 'is_waiting_room_enabled' in update_data:
            changes['is_waiting_room_enabled'] = {'old': meeting.is_waiting_room_enabled, 'new': update_data['is_waiting_room_enabled']}
            meeting.is_waiting_room_enabled = update_data['is_waiting_room_enabled']
        
        if 'is_password_protected' in update_data:
            changes['is_password_protected'] = {'old': meeting.is_password_protected, 'new': update_data['is_password_protected']}
            meeting.is_password_protected = update_data['is_password_protected']
        
        if 'meeting_password' in update_data:
            # 不记录密码变更的具体内容，只记录是否变更
            changes['meeting_password'] = {'changed': True}
            meeting.meeting_password = update_data['meeting_password']
        
        if 'agenda' in update_data:
            changes['agenda'] = {'changed': True}  # 议程变更不记录具体内容
            meeting.agenda = update_data['agenda']
        
        if 'meeting_settings' in update_data:
            changes['meeting_settings'] = {'changed': True}  # 设置变更不记录具体内容
            meeting.meeting_settings = update_data['meeting_settings']
        
        # 8. 更新审计信息
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 9. 发送变更通知
        if changes:
            await self._send_meeting_change_notifications(meeting, changes)
        
        # 10. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)
        
        logger.info(f"Updated meeting {meeting.meeting_code} by user {user_id}")
        return meeting
    
    async def delete_meeting(self, meeting_id: int, user_id: int, hard_delete: bool = False) -> bool:
        """
        删除会议（软删除或硬删除）
        
        Args:
            meeting_id: 会议ID
            user_id: 操作用户ID
            hard_delete: 是否硬删除
            
        Returns:
            删除是否成功
            
        Raises:
            NotFoundError: 会议不存在
            PermissionError: 权限不足
            ValidationError: 会议状态不允许删除
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证删除权限
        await self._validate_delete_permission(meeting, user_id)
        
        # 3. 检查会议状态
        if meeting.status == MeetingStatus.IN_PROGRESS:
            raise ValidationError("无法删除正在进行的会议")
        
        # 4. 记录删除前的状态
        original_status = meeting.status
        
        if hard_delete:
            # 硬删除：直接从数据库删除
            # 先发送取消通知，因为删除后无法获取会议信息
            await self._send_meeting_cancellation_notifications(meeting)
            await self.db.delete(meeting)
        else:
            # 软删除：标记删除时间和状态
            meeting.deleted_at = datetime.utcnow()
            meeting.status = MeetingStatus.CANCELLED
            meeting.updated_by = user_id
            meeting.updated_at = datetime.utcnow()
            
            # 发送取消通知
            await self._send_meeting_cancellation_notifications(meeting)
        
        # 5. 提交事务
        await self.db.commit()
        
        logger.info(f"Deleted meeting {meeting.meeting_code} by user {user_id} (hard_delete={hard_delete}, original_status={original_status})")
        return True
    
    async def cancel_meeting(self, meeting_id: int, user_id: int, reason: str = None) -> Meeting:
        """
        取消会议
        
        Args:
            meeting_id: 会议ID
            user_id: 操作用户ID
            reason: 取消原因
            
        Returns:
            取消后的会议对象
            
        Raises:
            NotFoundError: 会议不存在
            PermissionError: 权限不足
            ValidationError: 会议状态不允许取消
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证取消权限
        await self._validate_cancel_permission(meeting, user_id)
        
        # 3. 检查会议状态
        if meeting.status not in [MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]:
            raise ValidationError("只能取消已安排或正在进行的会议")
        
        # 4. 更新会议状态
        original_status = meeting.status
        meeting.status = MeetingStatus.CANCELLED
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 5. 记录取消原因
        if reason:
            if not meeting.meeting_settings:
                meeting.meeting_settings = {}
            meeting.meeting_settings['cancellation_reason'] = reason
            meeting.meeting_settings['cancelled_at'] = datetime.utcnow().isoformat()
            meeting.meeting_settings['cancelled_by'] = user_id
        
        # 6. 如果会议正在进行，需要结束会议
        if original_status == MeetingStatus.IN_PROGRESS:
            meeting.actual_end_time = datetime.utcnow()
            if meeting.actual_start_time:
                duration = meeting.actual_end_time - meeting.actual_start_time
                meeting.duration_minutes = int(duration.total_seconds() / 60)
            
            # 更新参与者状态
            await self._update_participants_on_meeting_end(meeting_id)
            
            # 停止所有录制
            if meeting.is_recording_enabled:
                await self._stop_all_recordings(meeting_id)
        
        # 7. 发送取消通知
        await self._send_meeting_cancellation_notifications(meeting)
        
        # 8. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)
        
        logger.info(f"Cancelled meeting {meeting.meeting_code} by user {user_id} (reason: {reason})")
        return meeting
    
    async def postpone_meeting(self, meeting_id: int, new_start_time: datetime, 
                             new_end_time: datetime, user_id: int, reason: str = None) -> Meeting:
        """
        延期会议
        
        Args:
            meeting_id: 会议ID
            new_start_time: 新的开始时间
            new_end_time: 新的结束时间
            user_id: 操作用户ID
            reason: 延期原因
            
        Returns:
            延期后的会议对象
            
        Raises:
            NotFoundError: 会议不存在
            PermissionError: 权限不足
            ValidationError: 会议状态不允许延期或时间无效
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证延期权限
        await self._validate_postpone_permission(meeting, user_id)
        
        # 3. 检查会议状态
        if meeting.status not in [MeetingStatus.SCHEDULED, MeetingStatus.POSTPONED]:
            raise ValidationError("只能延期已安排或已延期的会议")
        
        # 4. 验证新时间
        if new_start_time >= new_end_time:
            raise ValidationError("新的开始时间必须早于结束时间")
        
        if new_start_time < datetime.utcnow():
            raise ValidationError("新的开始时间不能早于当前时间")
        
        # 5. 检查参与者时间冲突
        conflicts = await self._check_participants_time_conflicts(
            meeting_id, new_start_time, new_end_time
        )
        
        # 6. 记录原始时间
        original_start = meeting.scheduled_start_time
        original_end = meeting.scheduled_end_time
        
        # 7. 更新会议时间和状态
        meeting.scheduled_start_time = new_start_time
        meeting.scheduled_end_time = new_end_time
        meeting.status = MeetingStatus.POSTPONED
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 8. 记录延期信息
        if not meeting.meeting_settings:
            meeting.meeting_settings = {}
        
        postponement_info = {
            'original_start_time': original_start.isoformat(),
            'original_end_time': original_end.isoformat(),
            'new_start_time': new_start_time.isoformat(),
            'new_end_time': new_end_time.isoformat(),
            'postponed_at': datetime.utcnow().isoformat(),
            'postponed_by': user_id,
            'reason': reason,
            'conflicts': conflicts
        }
        
        if 'postponement_history' not in meeting.meeting_settings:
            meeting.meeting_settings['postponement_history'] = []
        meeting.meeting_settings['postponement_history'].append(postponement_info)
        
        # 9. 发送延期通知
        await self._send_meeting_postponement_notifications(meeting, postponement_info)
        
        # 10. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)
        
        logger.info(f"Postponed meeting {meeting.meeting_code} by user {user_id} from {original_start} to {new_start_time}")
        return meeting
    
    async def add_participant(self, meeting_id: int, request: Any, user_id: int) -> MeetingParticipant:
        """
        添加单个参与者并发送邀请通知

        Args:
            meeting_id: 会议ID
            request: 添加参与者请求（AddParticipantRequest 或 dict）
            user_id: 操作用户ID

        Returns:
            添加的参与者

        Raises:
            NotFoundError: 会议或用户不存在
            PermissionError: 权限不足
            ValidationError: 数据验证失败或参与者已存在
        """
        added, failed_users = await self.add_participants(meeting_id, [request], user_id)
        if not added:
            raise ValidationError("参与者添加失败或已是会议参与者")
        return added[0]

    async def add_participants(self, meeting_id: int, participants: List[Dict[str, Any]], user_id: int) -> List[MeetingParticipant]:
        """
        批量添加参与者

        Args:
            meeting_id: 会议ID
            participants: 参与者列表，格式：[{
                'user_id': int,
                'participant_role': str,  # 可选，默认为PARTICIPANT
                'can_share_screen': bool,  # 可选，默认为True
                'can_use_chat': bool,      # 可选，默认为True
                'can_use_whiteboard': bool, # 可选，默认为True
                'can_record': bool         # 可选，默认为False
            }]
            user_id: 操作用户ID

        Returns:
            添加的参与者列表

        Raises:
            NotFoundError: 会议不存在
            PermissionError: 权限不足
            ValidationError: 数据验证失败
        """
        # 0. 兼容 pydantic 请求对象（AddParticipantsRequest / AddParticipantRequest）
        if hasattr(participants, 'participants'):
            participants = participants.participants
        normalized = []
        for item in participants:
            if hasattr(item, 'dict'):
                data = {
                    key: (value.value if hasattr(value, 'value') else value)
                    for key, value in item.dict().items()
                }
            else:
                data = dict(item)
            if 'participant_role' in data and 'role' not in data:
                data['role'] = data['participant_role']
            normalized.append(data)
        participants = normalized

        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证权限
        await self._validate_manage_participants_permission(meeting, user_id)
        
        # 3. 验证参与者数量限制
        current_count = await self._get_participant_count(meeting_id)
        if current_count + len(participants) > meeting.max_participants:
            raise ValidationError(f"参与者数量超过限制 ({meeting.max_participants})")
        
        # 4. 验证参与者数据
        await self._validate_participants_data(participants)
        
        # 5. 添加参与者
        added_participants = []
        failed_users = []
        for participant_data in participants:
            try:
                participant = await self._add_single_participant(meeting_id, participant_data, user_id)
                if participant:
                    added_participants.append(participant)
                else:
                    failed_users.append(participant_data.get('user_id'))
            except Exception as e:
                logger.warning(f"Failed to add participant {participant_data.get('user_id')}: {str(e)}")
                failed_users.append(participant_data.get('user_id'))
                continue
        
        # 6. 更新会议参与者数量
        meeting.participant_count = await self._get_participant_count(meeting_id)
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 7. 提交事务
        await self.db.commit()
        
        # 8. 发送邀请通知
        await self._send_invitations_batch(meeting, added_participants)
        
        logger.info(f"Added {len(added_participants)} participants to meeting {meeting.meeting_code}")
        return added_participants, failed_users
    
    async def send_invitation(self, meeting_id: int, user_id: int, request: Any = None, operator_id: int = None) -> Dict[str, Any]:
        """
        向单个参与者发送会议邀请通知

        Args:
            meeting_id: 会议ID
            user_id: 参与者用户ID
            request: 邀请请求（ParticipantInviteRequest，可选）
            operator_id: 操作用户ID

        Returns:
            邀请结果，包含 invitation_id 和 sent_channels

        Raises:
            NotFoundError: 会议或参与者不存在
            PermissionError: 权限不足
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)

        # 2. 验证权限
        if operator_id:
            await self._validate_manage_participants_permission(meeting, operator_id)

        # 3. 获取参与者
        participant = await self._get_participant_by_meeting_and_user(meeting_id, user_id)
        if not participant:
            raise NotFoundError(f"参与者不存在: {user_id}")

        # 4. 发送邀请通知
        sent = await self._send_participant_invitation(meeting, participant)
        if sent:
            participant.invited_at = datetime.utcnow()
            await self.db.commit()

        return {
            'invitation_id': participant.id,
            'sent_channels': ['websocket', 'in_app'] if sent else []
        }

    async def send_invitations(self, meeting_id: int, participant_ids: List[int] = None, user_id: int = None) -> bool:
        """
        发送会议邀请
        
        Args:
            meeting_id: 会议ID
            participant_ids: 参与者ID列表，如果为None则发送给所有待邀请的参与者
            user_id: 操作用户ID
            
        Returns:
            发送是否成功
            
        Raises:
            NotFoundError: 会议不存在
            PermissionError: 权限不足
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证权限
        if user_id:
            await self._validate_manage_participants_permission(meeting, user_id)
        
        # 3. 获取需要发送邀请的参与者
        if participant_ids:
            # 发送给指定参与者
            query = select(MeetingParticipant).where(
                and_(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.user_id.in_(participant_ids)
                )
            )
        else:
            # 发送给所有待邀请的参与者
            query = select(MeetingParticipant).where(
                and_(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.invitation_status == InvitationStatus.PENDING
                )
            )
        
        result = await self.db.execute(query)
        participants = result.scalars().all()
        
        if not participants:
            logger.info(f"No participants to invite for meeting {meeting.meeting_code}")
            return True
        
        # 4. 批量发送邀请
        success = await self._send_invitations_batch(meeting, participants)
        
        logger.info(f"Sent invitations to {len(participants)} participants for meeting {meeting.meeting_code}")
        return success
    
    async def respond_to_invitation(self, meeting_id: int, user_id: int, response: str, 
                                  response_message: str = None) -> MeetingParticipant:
        """
        响应会议邀请
        
        Args:
            meeting_id: 会议ID
            user_id: 用户ID
            response: 响应类型 (ACCEPTED, DECLINED, TENTATIVE)
            response_message: 响应消息
            
        Returns:
            更新后的参与者对象
            
        Raises:
            NotFoundError: 会议或参与者不存在
            ValidationError: 响应类型无效
        """
        # 1. 验证响应类型
        try:
            invitation_status = InvitationStatus(response.upper())
        except ValueError:
            raise ValidationError(f"无效的响应类型: {response}")
        
        # 2. 获取参与者记录
        participant = await self._get_participant_by_meeting_and_user(meeting_id, user_id)
        if not participant:
            raise NotFoundError("您未被邀请参加此会议")
        
        # 3. 获取会议信息
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 4. 更新邀请状态
        old_status = participant.invitation_status
        participant.invitation_status = invitation_status
        participant.updated_by = user_id
        participant.updated_at = datetime.utcnow()
        
        # 5. 记录响应消息
        if response_message:
            if not participant.device_info:
                participant.device_info = {}
            participant.device_info['response_message'] = response_message
        
        # 6. 提交事务
        await self.db.commit()
        
        # 7. 发送响应通知给组织者
        await self._send_invitation_response_notification(meeting, participant, old_status)
        
        logger.info(f"User {user_id} responded {response} to meeting {meeting.meeting_code}")
        return participant
    
    async def update_participant_role(self, meeting_id: int, participant_user_id: int, 
                                    new_role: str, permissions: Dict[str, bool] = None, 
                                    user_id: int = None) -> MeetingParticipant:
        """
        更新参与者角色和权限
        
        Args:
            meeting_id: 会议ID
            participant_user_id: 参与者用户ID
            new_role: 新角色
            permissions: 权限设置
            user_id: 操作用户ID
            
        Returns:
            更新后的参与者对象
            
        Raises:
            NotFoundError: 会议或参与者不存在
            PermissionError: 权限不足
            ValidationError: 角色无效
        """
        # 1. 验证角色
        try:
            participant_role = ParticipantRole(new_role.upper())
        except ValueError:
            raise ValidationError(f"无效的参与者角色: {new_role}")
        
        # 2. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 3. 验证权限
        if user_id:
            await self._validate_manage_participants_permission(meeting, user_id)
        
        # 4. 获取参与者记录
        participant = await self._get_participant_by_meeting_and_user(meeting_id, participant_user_id)
        if not participant:
            raise NotFoundError("参与者不存在")
        
        # 5. 检查是否尝试修改组织者角色
        if participant.participant_role == ParticipantRole.ORGANIZER and participant_role != ParticipantRole.ORGANIZER:
            if participant.user_id == meeting.organizer_id:
                raise ValidationError("不能修改会议组织者的角色")
        
        # 6. 更新角色
        old_role = participant.participant_role
        participant.participant_role = participant_role
        
        # 7. 更新权限
        if permissions:
            participant.can_share_screen = permissions.get('can_share_screen', participant.can_share_screen)
            participant.can_use_chat = permissions.get('can_use_chat', participant.can_use_chat)
            participant.can_use_whiteboard = permissions.get('can_use_whiteboard', participant.can_use_whiteboard)
            participant.can_record = permissions.get('can_record', participant.can_record)
        else:
            # 根据角色设置默认权限
            await self._set_default_permissions_by_role(participant, participant_role)
        
        # 8. 更新审计信息
        participant.updated_by = user_id
        participant.updated_at = datetime.utcnow()
        
        # 9. 提交事务
        await self.db.commit()
        
        # 10. 发送角色变更通知
        await self._send_role_change_notification(meeting, participant, old_role)
        
        logger.info(f"Updated participant {participant_user_id} role from {old_role} to {participant_role} in meeting {meeting.meeting_code}")
        return participant
    
    async def remove_participant(self, meeting_id: int, participant_user_id: int, user_id: int) -> bool:
        """
        移除参与者
        
        Args:
            meeting_id: 会议ID
            participant_user_id: 参与者用户ID
            user_id: 操作用户ID
            
        Returns:
            移除是否成功
            
        Raises:
            NotFoundError: 会议或参与者不存在
            PermissionError: 权限不足
            ValidationError: 不能移除组织者
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证权限
        await self._validate_manage_participants_permission(meeting, user_id)
        
        # 3. 获取参与者记录
        participant = await self._get_participant_by_meeting_and_user(meeting_id, participant_user_id)
        if not participant:
            raise NotFoundError("参与者不存在")
        
        # 4. 检查是否尝试移除组织者
        if participant.user_id == meeting.organizer_id:
            raise ValidationError("不能移除会议组织者")
        
        # 5. 删除参与者记录
        await self.db.delete(participant)
        
        # 6. 更新会议参与者数量
        meeting.participant_count = await self._get_participant_count(meeting_id) - 1
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 7. 提交事务
        await self.db.commit()
        
        # 8. 发送移除通知
        await self._send_participant_removal_notification(meeting, participant)
        
        logger.info(f"Removed participant {participant_user_id} from meeting {meeting.meeting_code}")
        return True
    
    async def join_meeting(self, meeting_code: str, user_id: int, join_options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        加入会议
        
        Args:
            meeting_code: 会议编码
            user_id: 用户ID
            join_options: 加入选项
            
        Returns:
            加入结果信息
        """
        join_options = join_options or {}
        
        # 1. 获取会议
        meeting = await self._get_meeting_by_code(meeting_code)
        
        # 2. 验证会议状态
        if meeting.status not in [MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]:
            raise ValidationError("会议未开始或已结束")
        
        # 3. 验证会议密码
        if meeting.is_password_protected:
            password = join_options.get('password')
            if not password or password != meeting.meeting_password:
                raise ValidationError("会议密码错误")
        
        # 4. 获取参与者信息
        participant = await self._get_participant_by_meeting_and_user(meeting.id, user_id)
        if not participant:
            raise PermissionError("您未被邀请参加此会议")
        
        # 5. 检查等候室
        if meeting.is_waiting_room_enabled and participant.participant_role not in [ParticipantRole.ORGANIZER, ParticipantRole.MODERATOR]:
            # 添加到等候室
            await self._add_to_waiting_room(meeting.id, user_id)
            return {
                'status': 'WAITING_ROOM',
                'message': '请等待主持人允许进入',
                'meeting_info': meeting.to_dict()
            }
        
        # 6. 更新参与状态
        participant.attendance_status = AttendanceStatus.JOINED
        participant.join_time = datetime.utcnow()
        participant.device_info = join_options.get('device_info', {})
        participant.updated_by = user_id
        participant.updated_at = datetime.utcnow()
        
        # 7. 更新会议状态
        if meeting.status == MeetingStatus.SCHEDULED:
            meeting.status = MeetingStatus.IN_PROGRESS
            meeting.actual_start_time = datetime.utcnow()
            meeting.updated_by = user_id
            meeting.updated_at = datetime.utcnow()
        
        # 8. 生成访问令牌
        access_token = await self._generate_access_token(meeting.id, user_id, participant.participant_role)
        
        # 9. 获取会议配置
        meeting_config = await self._get_meeting_config(meeting, participant)
        
        # 10. 获取WebRTC配置
        webrtc_config = await self._get_webrtc_config(meeting.id)
        
        # 11. 提交事务
        await self.db.commit()
        
        logger.info(f"User {user_id} joined meeting {meeting.meeting_code}")
        
        return {
            'status': 'SUCCESS',
            'access_token': access_token,
            'meeting_info': meeting.to_dict(),
            'participant_info': participant.to_dict(),
            'meeting_config': meeting_config,
            'webrtc_config': webrtc_config
        }
    
    async def start_meeting(self, meeting_id: int, user_id: int, request: Any = None) -> Meeting:
        """
        开始会议
        
        Args:
            meeting_id: 会议ID
            user_id: 操作用户ID
            
        Returns:
            更新后的会议对象
            
        Raises:
            NotFoundError: 会议不存在
            PermissionError: 权限不足
            ValidationError: 会议状态不允许开始
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证权限
        await self._validate_start_meeting_permission(meeting, user_id)
        
        # 3. 验证会议状态转换
        await self._validate_status_transition(meeting.status, MeetingStatus.IN_PROGRESS)
        
        # 4. 更新会议状态
        meeting.status = MeetingStatus.IN_PROGRESS
        meeting.actual_start_time = datetime.utcnow()
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 5. 初始化会议统计
        await self._initialize_meeting_statistics(meeting_id)
        
        # 6. 通知参与者会议开始
        await self._send_meeting_start_notifications(meeting)
        
        # 7. 记录会议开始事件
        await self._log_meeting_event(meeting_id, 'MEETING_STARTED', user_id, {
            'actual_start_time': meeting.actual_start_time.isoformat(),
            'scheduled_start_time': meeting.scheduled_start_time.isoformat()
        })
        
        # 8. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)
        
        logger.info(f"Started meeting {meeting.meeting_code} by user {user_id}")
        return meeting
    
    async def end_meeting(self, meeting_id: int, user_id: int, request: Any = None) -> Meeting:
        """
        结束会议
        
        Args:
            meeting_id: 会议ID
            user_id: 操作用户ID
            
        Returns:
            更新后的会议对象
            
        Raises:
            NotFoundError: 会议不存在
            PermissionError: 权限不足
            ValidationError: 会议状态不允许结束
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证权限
        await self._validate_end_meeting_permission(meeting, user_id)
        
        # 3. 验证会议状态转换
        await self._validate_status_transition(meeting.status, MeetingStatus.COMPLETED)
        
        # 4. 更新会议状态和统计信息
        meeting.status = MeetingStatus.COMPLETED
        meeting.actual_end_time = datetime.utcnow()
        
        # 计算实际会议时长
        if meeting.actual_start_time:
            duration = meeting.actual_end_time - meeting.actual_start_time
            meeting.duration_minutes = int(duration.total_seconds() / 60)
        else:
            # 如果没有实际开始时间，使用当前时间作为开始时间
            meeting.actual_start_time = meeting.actual_end_time
            meeting.duration_minutes = 0
        
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 5. 更新参与者出席状态和统计信息
        await self._update_participants_on_meeting_end(meeting_id)
        
        # 6. 停止所有录制
        if meeting.is_recording_enabled:
            await self._stop_all_recordings(meeting_id)
        
        # 7. 计算会议统计数据
        meeting_stats = await self._calculate_meeting_statistics(meeting_id)

        await self._save_manual_minutes_on_end(meeting, user_id, request)
        
        # 8. 发送会议结束通知
        await self._send_meeting_end_notifications(meeting, meeting_stats)
        
        # 9. 记录会议结束事件
        await self._log_meeting_event(meeting_id, 'MEETING_ENDED', user_id, {
            'actual_end_time': meeting.actual_end_time.isoformat(),
            'duration_minutes': meeting.duration_minutes,
            'participant_count': meeting_stats.get('total_participants', 0),
            'statistics': meeting_stats
        })
        
        # 10. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)
        
        logger.info(f"Ended meeting {meeting.meeting_code} by user {user_id}, duration: {meeting.duration_minutes} minutes")
        return meeting

    async def _save_manual_minutes_on_end(self, meeting: Meeting, user_id: int, request: Any = None) -> None:
        """保存结束会议时填写的手工纪要。"""
        if request is None:
            return

        request_data = request.dict(exclude_none=True) if hasattr(request, "dict") else dict(request or {})
        content = (request_data.get("minutes_content") or "").strip()
        if not content:
            return

        title = (request_data.get("minutes_title") or f"{meeting.title} - 会议纪要").strip()
        minutes = MeetingMinutes(
            meeting_id=meeting.id,
            title=title[:200],
            content=content,
            summary=(request_data.get("minutes_summary") or "").strip() or None,
            minute_type=MinuteType.MANUAL_CREATED,
            generation_method=GenerationMethod.MANUAL_INPUT,
            key_points=request_data.get("key_points") or [],
            decisions=request_data.get("decisions") or [],
            action_items=request_data.get("action_items") or [],
            status=MinuteStatus.PUBLISHED,
            approval_required=False,
            version="1.0",
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(minutes)
        await self.db.flush()
    
    # 私有辅助方法
    
    async def _get_meeting_by_id(self, meeting_id: int) -> Meeting:
        """根据ID获取会议"""
        query = select(Meeting).where(
            and_(Meeting.id == meeting_id, Meeting.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError("会议不存在")
        
        return meeting
    
    async def _get_meeting_by_code(self, meeting_code: str) -> Meeting:
        """根据会议编码获取会议"""
        query = select(Meeting).where(
            and_(Meeting.meeting_code == meeting_code, Meeting.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError("会议不存在")
        
        return meeting
    
    async def _get_participant_by_meeting_and_user(self, meeting_id: int, user_id: int) -> Optional[MeetingParticipant]:
        """获取参与者记录"""
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _validate_meeting_data(self, meeting_data: Dict[str, Any]) -> None:
        """验证会议数据"""
        # 验证必需字段
        required_fields = ['title', 'meeting_type', 'scheduled_start_time', 'scheduled_end_time']
        for field in required_fields:
            if field not in meeting_data or not meeting_data[field]:
                raise ValidationError(f"缺少必需字段: {field}")
        
        # 验证时间
        start_time = meeting_data['scheduled_start_time']
        end_time = meeting_data['scheduled_end_time']
        
        if start_time >= end_time:
            raise ValidationError("开始时间必须早于结束时间")
        
        if start_time < datetime.utcnow():
            raise ValidationError("开始时间不能早于当前时间")
        
        # 验证会议类型
        try:
            MeetingType(meeting_data['meeting_type'])
        except ValueError:
            raise ValidationError(f"无效的会议类型: {meeting_data['meeting_type']}")
        
        # 验证参与者数量
        max_participants = meeting_data.get('max_participants', 100)
        if max_participants < 1 or max_participants > 1000:
            raise ValidationError("参与者数量必须在1-1000之间")
    
    async def _validate_create_permission(self, user_id: int, project_id: Optional[int]) -> None:
        """验证创建权限"""
        # 检查基本创建权限
        has_permission = await self.permission_service.check_permission(user_id, 'meeting:create')
        
        # 如果关联项目，检查项目权限
        if project_id:
            has_project_permission = await self.permission_service.check_project_permission(
                user_id, project_id, 'project:meeting:create'
            )
            if not has_permission and not has_project_permission:
                raise PermissionError("无权限创建会议")
        elif not has_permission:
            raise PermissionError("无权限创建会议")
    
    async def _validate_update_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证更新权限"""
        # 组织者可以更新
        if meeting.organizer_id == user_id:
            return
        
        # 检查系统权限
        if await self.permission_service.check_permission(user_id, 'meeting:update'):
            return
        
        # 检查项目权限
        if meeting.project_id:
            if await self.permission_service.check_project_permission(
                user_id, meeting.project_id, 'project:meeting:update'
            ):
                return
        
        raise PermissionError("无权限更新会议")
    
    async def _validate_delete_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证删除权限"""
        # 组织者可以删除
        if meeting.organizer_id == user_id:
            return
        
        # 检查系统权限
        if await self.permission_service.check_permission(user_id, 'meeting:delete'):
            return
        
        # 检查项目权限
        if meeting.project_id:
            if await self.permission_service.check_project_permission(
                user_id, meeting.project_id, 'project:meeting:delete'
            ):
                return
        
        raise PermissionError("无权限删除会议")
    
    async def _validate_cancel_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证取消权限"""
        # 组织者可以取消
        if meeting.organizer_id == user_id:
            return
        
        # 检查系统权限
        if await self.permission_service.check_permission(user_id, 'meeting:cancel'):
            return
        
        # 检查项目权限
        if meeting.project_id:
            if await self.permission_service.check_project_permission(
                user_id, meeting.project_id, 'project:meeting:cancel'
            ):
                return
        
        raise PermissionError("无权限取消会议")
    
    async def _validate_postpone_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证延期权限"""
        # 组织者可以延期
        if meeting.organizer_id == user_id:
            return
        
        # 检查系统权限
        if await self.permission_service.check_permission(user_id, 'meeting:postpone'):
            return
        
        # 检查项目权限
        if meeting.project_id:
            if await self.permission_service.check_project_permission(
                user_id, meeting.project_id, 'project:meeting:postpone'
            ):
                return
        
        raise PermissionError("无权限延期会议")
    

    
    async def _validate_manage_participants_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证管理参与者权限"""
        # 组织者可以管理
        if meeting.organizer_id == user_id:
            return
        
        # 检查参与者角色
        participant = await self._get_participant_by_meeting_and_user(meeting.id, user_id)
        if participant and participant.participant_role in [ParticipantRole.MODERATOR]:
            return
        
        raise PermissionError("无权限管理参与者")
    
    async def _validate_update_data(self, update_data: Dict[str, Any], meeting: Meeting) -> None:
        """验证更新数据"""
        # 验证时间
        if 'scheduled_start_time' in update_data and 'scheduled_end_time' in update_data:
            start_time = update_data['scheduled_start_time']
            end_time = update_data['scheduled_end_time']
            
            if start_time >= end_time:
                raise ValidationError("开始时间必须早于结束时间")
            
            # 如果会议还未开始，检查时间不能早于当前时间
            if meeting.status == MeetingStatus.SCHEDULED and start_time < datetime.utcnow():
                raise ValidationError("开始时间不能早于当前时间")
        
        # 验证会议类型
        if 'meeting_type' in update_data:
            try:
                MeetingType(update_data['meeting_type'])
            except ValueError:
                raise ValidationError(f"无效的会议类型: {update_data['meeting_type']}")
        
        # 验证参与者数量
        if 'max_participants' in update_data:
            max_participants = update_data['max_participants']
            if max_participants < 1 or max_participants > 1000:
                raise ValidationError("参与者数量必须在1-1000之间")
            
            # 检查当前参与者数量
            current_count = await self._get_participant_count(meeting.id)
            if max_participants < current_count:
                raise ValidationError(f"参与者数量不能少于当前参与者数量({current_count})")
    
    async def _generate_meeting_code(self) -> str:
        """生成会议编码"""
        while True:
            # 生成8位随机编码
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            
            # 检查是否已存在
            query = select(Meeting).where(Meeting.meeting_code == code)
            result = await self.db.execute(query)
            if not result.scalar_one_or_none():
                return code
    
    async def _get_participant_count(self, meeting_id: int) -> int:
        """获取参与者数量"""
        query = select(func.count(MeetingParticipant.id)).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def _add_organizer_as_participant(self, meeting_id: int, organizer_id: int) -> MeetingParticipant:
        """添加组织者为参与者"""
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=organizer_id,
            participant_role=ParticipantRole.ORGANIZER,
            invitation_status=InvitationStatus.ACCEPTED,
            can_share_screen=True,
            can_use_chat=True,
            can_use_whiteboard=True,
            can_record=True,
            created_by=organizer_id
        )
        
        self.db.add(participant)
        await self.db.flush()
        return participant
    
    async def _add_participants(self, meeting_id: int, participants: List[Dict[str, Any]], organizer_id: int) -> List[MeetingParticipant]:
        """批量添加参与者"""
        added_participants = []
        
        for participant_data in participants:
            try:
                participant = await self._add_single_participant(meeting_id, participant_data, organizer_id)
                if participant:
                    added_participants.append(participant)
            except Exception as e:
                logger.warning(f"Failed to add participant {participant_data.get('user_id')}: {str(e)}")
                continue
        
        return added_participants
    
    async def _add_single_participant(self, meeting_id: int, participant_data: Dict[str, Any], organizer_id: int) -> Optional[MeetingParticipant]:
        """添加单个参与者"""
        user_id = participant_data.get('user_id')
        if not user_id:
            return None
        
        # 检查是否已存在
        existing = await self._get_participant_by_meeting_and_user(meeting_id, user_id)
        if existing:
            return existing
        
        # 创建参与者记录
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=user_id,
            participant_role=ParticipantRole(participant_data.get('participant_role', 'PARTICIPANT')),
            can_share_screen=participant_data.get('can_share_screen', True),
            can_use_chat=participant_data.get('can_use_chat', True),
            can_use_whiteboard=participant_data.get('can_use_whiteboard', True),
            can_record=participant_data.get('can_record', False),
            created_by=organizer_id
        )
        
        self.db.add(participant)
        await self.db.flush()
        return participant
    
    async def _validate_participants_data(self, participants: List[Dict[str, Any]]) -> None:
        """验证参与者数据"""
        for participant_data in participants:
            if 'user_id' not in participant_data:
                raise ValidationError("参与者数据缺少user_id")
            
            # 验证角色
            role = participant_data.get('participant_role', 'PARTICIPANT')
            try:
                ParticipantRole(role)
            except ValueError:
                raise ValidationError(f"无效的参与者角色: {role}")
    
    async def _set_default_permissions_by_role(self, participant: MeetingParticipant, role: ParticipantRole) -> None:
        """根据角色设置默认权限"""
        if role == ParticipantRole.ORGANIZER:
            participant.can_share_screen = True
            participant.can_use_chat = True
            participant.can_use_whiteboard = True
            participant.can_record = True
        elif role == ParticipantRole.MODERATOR:
            participant.can_share_screen = True
            participant.can_use_chat = True
            participant.can_use_whiteboard = True
            participant.can_record = True
        elif role == ParticipantRole.PRESENTER:
            participant.can_share_screen = True
            participant.can_use_chat = True
            participant.can_use_whiteboard = True
            participant.can_record = False
        elif role == ParticipantRole.PARTICIPANT:
            participant.can_share_screen = False
            participant.can_use_chat = True
            participant.can_use_whiteboard = False
            participant.can_record = False
        elif role == ParticipantRole.OBSERVER:
            participant.can_share_screen = False
            participant.can_use_chat = False
            participant.can_use_whiteboard = False
            participant.can_record = False
    
    async def _check_participants_time_conflicts(self, meeting_id: int, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """检查参与者时间冲突"""
        # 获取参与者列表
        query = select(MeetingParticipant.user_id).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        result = await self.db.execute(query)
        participant_ids = [row[0] for row in result.fetchall()]
        
        conflicts = []
        
        # 检查每个参与者的时间冲突
        for user_id in participant_ids:
            conflict_query = select(Meeting).join(MeetingParticipant).where(
                and_(
                    MeetingParticipant.user_id == user_id,
                    Meeting.id != meeting_id,
                    Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]),
                    Meeting.deleted_at.is_(None),
                    or_(
                        and_(Meeting.scheduled_start_time <= start_time, Meeting.scheduled_end_time > start_time),
                        and_(Meeting.scheduled_start_time < end_time, Meeting.scheduled_end_time >= end_time),
                        and_(Meeting.scheduled_start_time >= start_time, Meeting.scheduled_end_time <= end_time)
                    )
                )
            )
            
            conflict_result = await self.db.execute(conflict_query)
            conflicting_meetings = conflict_result.scalars().all()
            
            if conflicting_meetings:
                conflicts.append({
                    'user_id': user_id,
                    'conflicting_meetings': [
                        {
                            'meeting_id': m.id,
                            'title': m.title,
                            'start_time': m.scheduled_start_time.isoformat(),
                            'end_time': m.scheduled_end_time.isoformat()
                        }
                        for m in conflicting_meetings
                    ]
                })
        
        return conflicts
    

    
    async def _add_to_waiting_room(self, meeting_id: int, user_id: int) -> None:
        """添加到等候室"""
        # 这里应该实现等候室逻辑
        # 暂时只记录日志
        logger.info(f"Added user {user_id} to waiting room for meeting {meeting_id}")
    
    async def _generate_access_token(self, meeting_id: int, user_id: int, role: ParticipantRole) -> str:
        """生成访问令牌"""
        # 这里应该生成JWT令牌
        # 暂时返回简单的令牌
        import jwt
        from datetime import timedelta
        
        payload = {
            'meeting_id': meeting_id,
            'user_id': user_id,
            'role': role.value,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        
        # 这里应该使用配置中的密钥
        secret_key = "meeting_secret_key"  # 应该从配置中获取
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    async def _get_meeting_config(self, meeting: Meeting, participant: MeetingParticipant) -> Dict[str, Any]:
        """获取会议配置"""
        return {
            'meeting_id': meeting.id,
            'meeting_code': meeting.meeting_code,
            'title': meeting.title,
            'is_recording_enabled': meeting.is_recording_enabled,
            'is_waiting_room_enabled': meeting.is_waiting_room_enabled,
            'max_participants': meeting.max_participants,
            'participant_permissions': {
                'can_share_screen': participant.can_share_screen,
                'can_use_chat': participant.can_use_chat,
                'can_use_whiteboard': participant.can_use_whiteboard,
                'can_record': participant.can_record
            }
        }
    
    async def _get_webrtc_config(self, meeting_id: int) -> Dict[str, Any]:
        """获取WebRTC配置"""
        return {
            'ice_servers': [
                {'urls': 'stun:stun.l.google.com:19302'},
                # 这里应该配置TURN服务器
            ],
            'room_id': f"meeting_{meeting_id}"
        }
    
    async def _find_optimal_time(self, participants: List[Dict[str, Any]], 
                               duration_minutes: int, preferred_time_range: Dict[str, Any]) -> datetime:
        """智能时间调度"""
        # 这里应该实现智能调度算法
        # 暂时返回当前时间后1小时
        return datetime.utcnow() + timedelta(hours=1)
    
    # 通知相关方法
    
    async def _send_invitations(self, meeting: Meeting) -> None:
        """发送会议邀请"""
        logger.info(f"Sending invitations for meeting {meeting.meeting_code}")
        # 这里应该实现邀请发送逻辑
        
    async def _validate_status_transition(self, current_status: MeetingStatus, new_status: MeetingStatus) -> None:
        """验证会议状态转换"""
        valid_transitions = {
            MeetingStatus.SCHEDULED: [MeetingStatus.IN_PROGRESS, MeetingStatus.CANCELLED, MeetingStatus.POSTPONED],
            MeetingStatus.IN_PROGRESS: [MeetingStatus.COMPLETED, MeetingStatus.CANCELLED],
            MeetingStatus.POSTPONED: [MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS, MeetingStatus.CANCELLED],
            MeetingStatus.COMPLETED: [],  # 已完成的会议不能转换状态
            MeetingStatus.CANCELLED: []   # 已取消的会议不能转换状态
        }
        
        if new_status not in valid_transitions.get(current_status, []):
            raise ValidationError(f"无法从状态 {current_status.value} 转换到 {new_status.value}")
    
    async def _validate_start_meeting_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证开始会议权限"""
        # 组织者可以开始会议
        if meeting.organizer_id == user_id:
            return
        
        # 检查参与者角色
        participant = await self._get_participant_by_meeting_and_user(meeting.id, user_id)
        if participant and participant.participant_role in [ParticipantRole.MODERATOR]:
            return
        
        raise PermissionError("无权限开始会议")
    
    async def _validate_end_meeting_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证结束会议权限"""
        # 组织者可以结束会议
        if meeting.organizer_id == user_id:
            return
        
        # 检查管理员权限
        if await self.permission_service.check_permission(user_id, 'meeting:admin'):
            return
        
        raise PermissionError("无权限结束会议")
    
    async def _initialize_meeting_statistics(self, meeting_id: int) -> None:
        """初始化会议统计"""
        logger.info(f"Initializing statistics for meeting {meeting_id}")
        # 这里应该实现统计初始化逻辑
    
    async def _update_participants_on_meeting_end(self, meeting_id: int) -> None:
        """会议结束时更新参与者状态"""
        # 获取所有已加入的参与者
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.attendance_status == AttendanceStatus.JOINED
            )
        )
        result = await self.db.execute(query)
        participants = result.scalars().all()
        
        # 更新参与者状态
        for participant in participants:
            participant.attendance_status = AttendanceStatus.LEFT
            participant.leave_time = datetime.utcnow()
            if participant.join_time:
                duration = participant.leave_time - participant.join_time
                participant.total_duration_minutes = int(duration.total_seconds() / 60)
        
        await self.db.flush()
    
    async def _stop_all_recordings(self, meeting_id: int) -> None:
        """停止所有录制"""
        logger.info(f"Stopping all recordings for meeting {meeting_id}")
        # 这里应该实现停止录制逻辑
    
    async def _calculate_meeting_statistics(self, meeting_id: int) -> Dict[str, Any]:
        """计算会议统计数据"""
        # 获取参与者统计
        query = select(
            func.count(MeetingParticipant.id).label('total_participants'),
            func.sum(MeetingParticipant.total_duration_minutes).label('total_duration'),
            func.avg(MeetingParticipant.total_duration_minutes).label('avg_duration')
        ).where(MeetingParticipant.meeting_id == meeting_id)
        
        result = await self.db.execute(query)
        stats = result.fetchone()
        
        return {
            'total_participants': stats.total_participants or 0,
            'total_duration_minutes': stats.total_duration or 0,
            'avg_duration_minutes': float(stats.avg_duration) if stats.avg_duration else 0
        }
    
    async def _log_meeting_event(self, meeting_id: int, event_type: str, user_id: int, event_data: Dict[str, Any]) -> None:
        """记录会议事件"""
        logger.info(f"Meeting {meeting_id} event: {event_type} by user {user_id}")
        # 这里应该实现事件记录逻辑
    
    async def _send_notification(self, user_id: int, notification_type: str, message: str, data: Dict[str, Any]) -> None:
        """发送通知"""
        logger.info(f"Sending notification to user {user_id}: {notification_type} - {message}")
        # 这里应该实现通知发送逻辑
    
    async def _send_invitations_batch(self, meeting: Meeting, participants: List[MeetingParticipant]) -> bool:
        """批量发送邀请"""
        logger.info(f"Sending batch invitations for meeting {meeting.meeting_code} to {len(participants)} participants")
        # 这里应该实现批量邀请发送逻辑
        return True
    
    async def _send_meeting_change_notifications(self, meeting: Meeting, changes: Dict[str, Any]) -> None:
        """发送会议变更通知"""
        try:
            await self.notification_service.send_meeting_change_notification(meeting, changes)
            logger.info(f"Sent change notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending change notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_meeting_cancellation_notifications(self, meeting: Meeting) -> None:
        """发送会议取消通知"""
        try:
            reason = None
            if meeting.meeting_settings and 'cancellation_reason' in meeting.meeting_settings:
                reason = meeting.meeting_settings['cancellation_reason']
            
            await self.notification_service.send_meeting_cancellation_notification(meeting, reason)
            logger.info(f"Sent cancellation notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending cancellation notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_meeting_postponement_notifications(self, meeting: Meeting, postponement_info: Dict[str, Any]) -> None:
        """发送会议延期通知"""
        try:
            await self.notification_service.send_meeting_postponement_notification(meeting, postponement_info)
            logger.info(f"Sent postponement notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending postponement notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_meeting_start_notifications(self, meeting: Meeting) -> None:
        """发送会议开始通知"""
        try:
            await self.notification_service.send_meeting_started_notification(meeting)
            logger.info(f"Sent start notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending start notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_meeting_end_notifications(self, meeting: Meeting, statistics: Dict[str, Any] = None) -> None:
        """发送会议结束通知"""
        try:
            await self.notification_service.send_meeting_ended_notification(meeting)
            logger.info(f"Sent end notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending end notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_invitation_response_notification(self, meeting: Meeting, participant: MeetingParticipant, old_status: InvitationStatus) -> None:
        """发送邀请响应通知"""
        try:
            # TODO: 可以扩展通知服务来支持邀请响应通知
            logger.info(f"Invitation response notification for meeting {meeting.meeting_code}: {old_status} -> {participant.invitation_status}")
        except Exception as e:
            logger.error(f"Error sending invitation response notification: {str(e)}")
    
    async def _send_role_change_notification(self, meeting: Meeting, participant: MeetingParticipant, old_role: ParticipantRole) -> None:
        """发送角色变更通知"""
        try:
            # TODO: 可以扩展通知服务来支持角色变更通知
            logger.info(f"Role change notification for meeting {meeting.meeting_code}: {old_role} -> {participant.participant_role}")
        except Exception as e:
            logger.error(f"Error sending role change notification: {str(e)}")
    
    async def _send_participant_removal_notification(self, meeting: Meeting, participant: MeetingParticipant) -> None:
        """发送参与者移除通知"""
        try:
            # TODO: 可以扩展通知服务来支持参与者移除通知
            logger.info(f"Participant removal notification for meeting {meeting.meeting_code}: user {participant.user_id}")
        except Exception as e:
            logger.error(f"Error sending participant removal notification: {str(e)}")
        # 这里应该实现移除通知逻辑ions(meeting)
        
        # 6. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)
        
        logger.info(f"Started meeting {meeting.meeting_code} by user {user_id}")
        return meeting
    

    
    # 私有方法实现
    
    async def _validate_meeting_data(self, meeting_data: Dict[str, Any]) -> None:
        """验证会议数据"""
        required_fields = ['title', 'meeting_type', 'scheduled_start_time', 'scheduled_end_time']
        for field in required_fields:
            if field not in meeting_data or not meeting_data[field]:
                raise ValidationError(f"缺少必填字段: {field}")
        
        # 验证时间逻辑
        start_time = meeting_data['scheduled_start_time']
        end_time = meeting_data['scheduled_end_time']
        
        if start_time >= end_time:
            raise ValidationError("会议开始时间必须早于结束时间")
        
        if start_time < datetime.utcnow():
            raise ValidationError("会议开始时间不能早于当前时间")
        
        # 验证会议类型
        try:
            MeetingType(meeting_data['meeting_type'])
        except ValueError:
            raise ValidationError("无效的会议类型")
    
    async def _validate_create_permission(self, user_id: int, project_id: Optional[int] = None) -> None:
        """验证创建权限"""
        # 检查用户是否存在
        user = await self.user_service.get_user_by_id(user_id)
        if not user:
            raise NotFoundError("用户不存在")
        
        # 如果关联项目，检查项目权限
        if project_id:
            has_permission = await self.permission_service.check_project_permission(
                user_id, project_id, 'meeting:create'
            )
            if not has_permission:
                raise PermissionError("无权限在此项目中创建会议")
    
    async def _generate_meeting_code(self) -> str:
        """生成会议编码"""
        while True:
            # 生成8位随机字符串
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            
            # 检查是否已存在
            query = select(Meeting).where(Meeting.meeting_code == code)
            result = await self.db.execute(query)
            if not result.scalar_one_or_none():
                return code
    
    async def _find_optimal_time(self, participants: List[int], duration_minutes: int, 
                               preferred_range: Dict[str, Any]) -> datetime:
        """
        智能时间调度功能
        
        分析参与者日历可用性，检测时间冲突，处理跨时区优化
        
        Args:
            participants: 参与者用户ID列表
            duration_minutes: 会议时长（分钟）
            preferred_range: 首选时间范围配置
            
        Returns:
            最优的会议时间
        """
        logger.info(f"Finding optimal time for {len(participants)} participants, duration: {duration_minutes} minutes")
        
        # 1. 获取参与者时区信息
        participant_timezones = await self._get_participants_timezones(participants)
        
        # 2. 设置搜索范围
        start_date = preferred_range.get('start_date', datetime.utcnow().date())
        end_date = preferred_range.get('end_date', start_date + timedelta(days=14))  # 扩展到14天
        start_hour = preferred_range.get('start_hour', 9)
        end_hour = preferred_range.get('end_hour', 18)
        timezone_preference = preferred_range.get('timezone', 'UTC')
        
        # 3. 生成候选时间列表
        candidate_times = await self._generate_candidate_times(
            start_date, end_date, start_hour, end_hour, duration_minutes, timezone_preference
        )
        
        # 4. 为每个候选时间计算评分
        scored_times = []
        for candidate_time in candidate_times:
            score = await self._calculate_time_score(
                candidate_time, participants, duration_minutes, participant_timezones
            )
            if score > 0:  # 只保留可行的时间
                scored_times.append((candidate_time, score))
        
        # 5. 按评分排序，选择最优时间
        if scored_times:
            scored_times.sort(key=lambda x: x[1], reverse=True)
            optimal_time = scored_times[0][0]
            logger.info(f"Found optimal time: {optimal_time} with score: {scored_times[0][1]}")
            return optimal_time
        
        # 6. 如果没有找到合适时间，尝试放宽条件
        logger.warning("No optimal time found with strict conditions, trying relaxed search")
        relaxed_time = await self._find_relaxed_optimal_time(
            participants, duration_minutes, preferred_range, participant_timezones
        )
        
        if relaxed_time:
            return relaxed_time
        
        # 7. 最后的备选方案：返回最早可用时间
        logger.warning("Using fallback time selection")
        return await self._get_fallback_time(preferred_range)
    
    async def _check_time_conflicts(self, participants: List[int], start_time: datetime, 
                                  duration_minutes: int) -> bool:
        """
        检查时间冲突
        
        Args:
            participants: 参与者ID列表
            start_time: 开始时间
            duration_minutes: 持续时间（分钟）
            
        Returns:
            是否存在冲突
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # 查询参与者在此时间段的其他会议
        query = select(Meeting).join(MeetingParticipant).where(
            and_(
                MeetingParticipant.user_id.in_(participants),
                Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]),
                Meeting.deleted_at.is_(None),
                or_(
                    # 会议开始时间在候选时间段内
                    and_(Meeting.scheduled_start_time >= start_time, Meeting.scheduled_start_time < end_time),
                    # 会议结束时间在候选时间段内
                    and_(Meeting.scheduled_end_time > start_time, Meeting.scheduled_end_time <= end_time),
                    # 会议完全包含候选时间段
                    and_(Meeting.scheduled_start_time <= start_time, Meeting.scheduled_end_time >= end_time)
                )
            )
        )
        
        result = await self.db.execute(query)
        conflicts = result.scalars().all()
        
        if conflicts:
            logger.debug(f"Found {len(conflicts)} time conflicts for time {start_time}")
        
        return len(conflicts) > 0
    
    async def _get_participants_timezones(self, participants: List[int]) -> Dict[int, str]:
        """
        获取参与者时区信息
        
        Args:
            participants: 参与者ID列表
            
        Returns:
            用户ID到时区的映射
        """
        query = select(User.id, User.timezone).where(User.id.in_(participants))
        result = await self.db.execute(query)
        
        timezone_map = {}
        for user_id, timezone in result.fetchall():
            timezone_map[user_id] = timezone or 'UTC'
        
        logger.debug(f"Retrieved timezones for {len(timezone_map)} participants")
        return timezone_map
    
    async def _generate_candidate_times(self, start_date: datetime.date, end_date: datetime.date,
                                      start_hour: int, end_hour: int, duration_minutes: int,
                                      timezone_preference: str) -> List[datetime]:
        """
        生成候选时间列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            start_hour: 每日开始小时
            end_hour: 每日结束小时
            duration_minutes: 会议时长
            timezone_preference: 首选时区
            
        Returns:
            候选时间列表
        """
        import pytz
        
        candidate_times = []
        current_date = start_date
        
        # 获取时区对象
        try:
            tz = pytz.timezone(timezone_preference)
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
            logger.warning(f"Unknown timezone {timezone_preference}, using UTC")
        
        while current_date <= end_date:
            # 跳过周末（可配置）
            if current_date.weekday() >= 5:  # 周六和周日
                current_date += timedelta(days=1)
                continue
            
            # 生成当天的候选时间
            for hour in range(start_hour, end_hour):
                for minute in [0, 30]:  # 每半小时一个候选时间
                    candidate_time = datetime.combine(
                        current_date, 
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                    
                    # 转换为UTC时间
                    localized_time = tz.localize(candidate_time)
                    utc_time = localized_time.astimezone(pytz.UTC).replace(tzinfo=None)
                    
                    # 确保会议不会超出工作时间
                    meeting_end = utc_time + timedelta(minutes=duration_minutes)
                    end_hour_utc = tz.localize(
                        datetime.combine(current_date, datetime.min.time().replace(hour=end_hour))
                    ).astimezone(pytz.UTC).replace(tzinfo=None)
                    
                    if meeting_end <= end_hour_utc:
                        candidate_times.append(utc_time)
            
            current_date += timedelta(days=1)
        
        logger.debug(f"Generated {len(candidate_times)} candidate times")
        return candidate_times
    
    async def _calculate_time_score(self, candidate_time: datetime, participants: List[int],
                                  duration_minutes: int, participant_timezones: Dict[int, str]) -> float:
        """
        计算候选时间的评分
        
        评分考虑因素：
        1. 时间冲突（-100分，直接排除）
        2. 时区友好度（0-40分）
        3. 工作时间适宜度（0-30分）
        4. 参与者偏好（0-20分）
        5. 会议时长适配（0-10分）
        
        Args:
            candidate_time: 候选时间
            participants: 参与者列表
            duration_minutes: 会议时长
            participant_timezones: 参与者时区映射
            
        Returns:
            时间评分（0-100分）
        """
        import pytz
        
        # 1. 检查时间冲突
        if await self._check_time_conflicts(participants, candidate_time, duration_minutes):
            return 0  # 有冲突直接排除
        
        score = 0.0
        
        # 2. 时区友好度评分（0-40分）
        timezone_score = await self._calculate_timezone_score(candidate_time, participant_timezones)
        score += timezone_score
        
        # 3. 工作时间适宜度评分（0-30分）
        work_hours_score = await self._calculate_work_hours_score(candidate_time, participant_timezones)
        score += work_hours_score
        
        # 4. 参与者历史偏好评分（0-20分）
        preference_score = await self._calculate_preference_score(candidate_time, participants)
        score += preference_score
        
        # 5. 会议时长适配评分（0-10分）
        duration_score = self._calculate_duration_score(candidate_time, duration_minutes)
        score += duration_score
        
        logger.debug(f"Time {candidate_time} scored: {score:.2f} (tz:{timezone_score:.1f}, work:{work_hours_score:.1f}, pref:{preference_score:.1f}, dur:{duration_score:.1f})")
        return score
    
    async def _calculate_timezone_score(self, candidate_time: datetime, 
                                      participant_timezones: Dict[int, str]) -> float:
        """
        计算时区友好度评分
        
        评分逻辑：
        - 所有参与者都在合理时间：40分
        - 大部分参与者在合理时间：20-35分
        - 少部分参与者在合理时间：5-20分
        - 没有参与者在合理时间：0分
        """
        import pytz
        
        if not participant_timezones:
            return 20.0  # 默认分数
        
        reasonable_count = 0
        total_participants = len(participant_timezones)
        
        for user_id, timezone_str in participant_timezones.items():
            try:
                tz = pytz.timezone(timezone_str)
                local_time = pytz.UTC.localize(candidate_time).astimezone(tz)
                hour = local_time.hour
                
                # 合理时间：8:00-20:00
                if 8 <= hour <= 20:
                    reasonable_count += 1
                # 可接受时间：7:00-22:00，减半分数
                elif 7 <= hour <= 22:
                    reasonable_count += 0.5
                    
            except pytz.UnknownTimeZoneError:
                # 未知时区，给予中等分数
                reasonable_count += 0.5
        
        # 计算比例并转换为分数
        ratio = reasonable_count / total_participants
        return ratio * 40.0
    
    async def _calculate_work_hours_score(self, candidate_time: datetime,
                                        participant_timezones: Dict[int, str]) -> float:
        """
        计算工作时间适宜度评分
        
        评分逻辑：
        - 所有参与者都在工作时间：30分
        - 大部分参与者在工作时间：15-25分
        - 少部分参与者在工作时间：5-15分
        """
        import pytz
        
        if not participant_timezones:
            return 15.0
        
        work_hours_count = 0
        total_participants = len(participant_timezones)
        
        for user_id, timezone_str in participant_timezones.items():
            try:
                tz = pytz.timezone(timezone_str)
                local_time = pytz.UTC.localize(candidate_time).astimezone(tz)
                hour = local_time.hour
                weekday = local_time.weekday()
                
                # 工作日的工作时间：9:00-18:00
                if weekday < 5 and 9 <= hour <= 18:
                    work_hours_count += 1
                # 工作日的扩展时间：8:00-19:00，减半分数
                elif weekday < 5 and 8 <= hour <= 19:
                    work_hours_count += 0.5
                    
            except pytz.UnknownTimeZoneError:
                work_hours_count += 0.3
        
        ratio = work_hours_count / total_participants
        return ratio * 30.0
    
    async def _validate_update_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证更新权限"""
        # 组织者可以更新
        if meeting.organizer_id == user_id:
            return
        
        # 检查管理员权限
        if await self.permission_service.check_permission(user_id, 'meeting:admin'):
            return
        
        # 检查项目管理权限
        if meeting.project_id:
            if await self.permission_service.check_project_permission(
                user_id, meeting.project_id, 'project:admin'
            ):
                return
        
        raise PermissionError("无权限更新此会议")
    
    async def _validate_update_data(self, update_data: Dict[str, Any], meeting: Meeting) -> None:
        """验证更新数据"""
        # 验证时间逻辑
        start_time = update_data.get('scheduled_start_time', meeting.scheduled_start_time)
        end_time = update_data.get('scheduled_end_time', meeting.scheduled_end_time)
        
        if start_time >= end_time:
            raise ValidationError("会议开始时间必须早于结束时间")
        
        # 如果会议已开始，不能修改开始时间
        if meeting.status == MeetingStatus.IN_PROGRESS:
            if 'scheduled_start_time' in update_data:
                raise ValidationError("会议已开始，无法修改开始时间")
        
        # 验证会议类型
        if 'meeting_type' in update_data:
            try:
                MeetingType(update_data['meeting_type'])
            except ValueError:
                raise ValidationError("无效的会议类型")
    
    async def _validate_delete_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证删除权限"""
        # 组织者可以删除
        if meeting.organizer_id == user_id:
            return
        
        # 检查管理员权限
        if await self.permission_service.check_permission(user_id, 'meeting:admin'):
            return
        
        # 检查项目管理权限
        if meeting.project_id:
            if await self.permission_service.check_project_permission(
                user_id, meeting.project_id, 'project:admin'
            ):
                return
        
        raise PermissionError("无权限删除此会议")
    
    async def cancel_meeting(self, meeting_id: int, user_id: int, reason: str = None) -> Meeting:
        """
        取消会议
        
        Args:
            meeting_id: 会议ID
            user_id: 操作用户ID
            reason: 取消原因
            
        Returns:
            更新后的会议对象
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证权限
        await self._validate_delete_permission(meeting, user_id)
        
        # 3. 检查会议状态
        if meeting.status == MeetingStatus.COMPLETED:
            raise ValidationError("无法取消已完成的会议")
        
        if meeting.status == MeetingStatus.CANCELLED:
            raise ValidationError("会议已被取消")
        
        # 4. 更新会议状态
        meeting.status = MeetingStatus.CANCELLED
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 5. 添加取消原因到设置中
        if not meeting.meeting_settings:
            meeting.meeting_settings = {}
        meeting.meeting_settings['cancellation_reason'] = reason
        meeting.meeting_settings['cancelled_by'] = user_id
        meeting.meeting_settings['cancelled_at'] = datetime.utcnow().isoformat()
        
        # 6. 发送取消通知
        await self._send_meeting_cancellation_notifications(meeting, reason)
        
        # 7. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)
        
        logger.info(f"Cancelled meeting {meeting.meeting_code} by user {user_id}")
        return meeting
    
    async def postpone_meeting(self, meeting_id: int, new_start_time: datetime, 
                             new_end_time: datetime, user_id: int, reason: str = None) -> Meeting:
        """
        延期会议
        
        Args:
            meeting_id: 会议ID
            new_start_time: 新的开始时间
            new_end_time: 新的结束时间
            user_id: 操作用户ID
            reason: 延期原因
            
        Returns:
            更新后的会议对象
        """
        # 1. 获取会议
        meeting = await self._get_meeting_by_id(meeting_id)
        
        # 2. 验证权限
        await self._validate_update_permission(meeting, user_id)
        
        # 3. 检查会议状态
        if meeting.status not in [MeetingStatus.SCHEDULED, MeetingStatus.POSTPONED]:
            raise ValidationError("只能延期已安排或已延期的会议")
        
        # 4. 验证新时间
        if new_start_time >= new_end_time:
            raise ValidationError("会议开始时间必须早于结束时间")
        
        if new_start_time < datetime.utcnow():
            raise ValidationError("新的开始时间不能早于当前时间")
        
        # 5. 记录原始时间
        original_start = meeting.scheduled_start_time
        original_end = meeting.scheduled_end_time
        
        # 6. 更新会议信息
        meeting.scheduled_start_time = new_start_time
        meeting.scheduled_end_time = new_end_time
        meeting.status = MeetingStatus.POSTPONED
        meeting.updated_by = user_id
        meeting.updated_at = datetime.utcnow()
        
        # 7. 添加延期信息到设置中
        if not meeting.meeting_settings:
            meeting.meeting_settings = {}
        
        postponement_info = {
            'original_start_time': original_start.isoformat(),
            'original_end_time': original_end.isoformat(),
            'new_start_time': new_start_time.isoformat(),
            'new_end_time': new_end_time.isoformat(),
            'postponed_by': user_id,
            'postponed_at': datetime.utcnow().isoformat(),
            'reason': reason
        }
        
        if 'postponement_history' not in meeting.meeting_settings:
            meeting.meeting_settings['postponement_history'] = []
        meeting.meeting_settings['postponement_history'].append(postponement_info)
        
        # 8. 发送延期通知
        await self._send_meeting_postponement_notifications(meeting, original_start, original_end, reason)
        
        # 9. 提交事务
        await self.db.commit()
        await self.db.refresh(meeting)
        
        logger.info(f"Postponed meeting {meeting.meeting_code} by user {user_id}")
        return meeting
    
    async def _send_meeting_change_notifications(self, meeting: Meeting, changes: Dict[str, Any]) -> None:
        """发送会议变更通知"""
        # 获取所有参与者
        participants = await self._get_meeting_participants(meeting.id)
        
        # 构建通知内容
        change_summary = []
        for field, change in changes.items():
            if field == 'title':
                change_summary.append(f"标题: {change['old']} → {change['new']}")
            elif field == 'scheduled_start_time':
                change_summary.append(f"开始时间: {change['old']} → {change['new']}")
            elif field == 'scheduled_end_time':
                change_summary.append(f"结束时间: {change['old']} → {change['new']}")
            elif field == 'meeting_type':
                change_summary.append(f"会议类型: {change['old']} → {change['new']}")
        
        notification_data = {
            'meeting_id': meeting.id,
            'meeting_code': meeting.meeting_code,
            'meeting_title': meeting.title,
            'changes': change_summary,
            'updated_by': meeting.updated_by,
            'updated_at': meeting.updated_at.isoformat()
        }
        
        # 发送通知给所有参与者
        for participant in participants:
            await self._send_notification(
                participant.user_id,
                'meeting_updated',
                f"会议 {meeting.title} 信息已更新",
                notification_data
            )
        
        logger.info(f"Sent change notifications for meeting {meeting.meeting_code} to {len(participants)} participants")
    
    async def _send_meeting_cancellation_notifications(self, meeting: Meeting, reason: str = None) -> None:
        """发送会议取消通知"""
        # 获取所有参与者
        participants = await self._get_meeting_participants(meeting.id)
        
        notification_data = {
            'meeting_id': meeting.id,
            'meeting_code': meeting.meeting_code,
            'meeting_title': meeting.title,
            'scheduled_start_time': meeting.scheduled_start_time.isoformat(),
            'cancelled_by': meeting.updated_by,
            'cancelled_at': meeting.updated_at.isoformat(),
            'reason': reason
        }
        
        # 发送通知给所有参与者
        for participant in participants:
            await self._send_notification(
                participant.user_id,
                'meeting_cancelled',
                f"会议 {meeting.title} 已被取消",
                notification_data
            )
        
        logger.info(f"Sent cancellation notifications for meeting {meeting.meeting_code} to {len(participants)} participants")
    
    async def _send_meeting_postponement_notifications(self, meeting: Meeting, original_start: datetime, 
                                                     original_end: datetime, reason: str = None) -> None:
        """发送会议延期通知"""
        try:
            postponement_info = {
                'original_start_time': original_start.isoformat(),
                'original_end_time': original_end.isoformat(),
                'new_start_time': meeting.scheduled_start_time.isoformat(),
                'new_end_time': meeting.scheduled_end_time.isoformat(),
                'postponed_by': meeting.updated_by,
                'postponed_at': meeting.updated_at.isoformat() if meeting.updated_at else datetime.utcnow().isoformat(),
                'reason': reason
            }
            
            await self.notification_service.send_meeting_postponement_notification(meeting, postponement_info)
            logger.info(f"Sent postponement notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending postponement notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _get_meeting_participants(self, meeting_id: int) -> List[MeetingParticipant]:
        """获取会议参与者列表"""
        query = select(MeetingParticipant).where(MeetingParticipant.meeting_id == meeting_id)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _get_pending_participants(self, meeting_id: int) -> List[MeetingParticipant]:
        """获取待邀请的参与者列表"""
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.invitation_status == InvitationStatus.PENDING
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    

    
    async def _calculate_preference_score(self, candidate_time: datetime, 
                                        participants: List[int]) -> float:
        """
        计算参与者历史偏好评分
        
        基于参与者的历史会议时间偏好
        """
        # 查询参与者的历史会议时间偏好
        query = select(
            func.extract('hour', Meeting.scheduled_start_time).label('hour'),
            func.count().label('count')
        ).join(MeetingParticipant).where(
            and_(
                MeetingParticipant.user_id.in_(participants),
                Meeting.status == MeetingStatus.COMPLETED,
                Meeting.deleted_at.is_(None)
            )
        ).group_by(func.extract('hour', Meeting.scheduled_start_time))
        
        result = await self.db.execute(query)
        hour_preferences = {row.hour: row.count for row in result.fetchall()}
        
        if not hour_preferences:
            return 10.0  # 默认分数
        
        # 计算候选时间的小时偏好分数
        candidate_hour = candidate_time.hour
        total_meetings = sum(hour_preferences.values())
        hour_preference = hour_preferences.get(candidate_hour, 0)
        
        # 转换为0-20分的评分
        preference_ratio = hour_preference / total_meetings if total_meetings > 0 else 0
        return preference_ratio * 20.0
    
    def _calculate_duration_score(self, candidate_time: datetime, duration_minutes: int) -> float:
        """
        计算会议时长适配评分
        
        评分逻辑：
        - 短会议(≤30分钟)：适合任何时间，10分
        - 中等会议(31-90分钟)：适合上午和下午早期，5-10分
        - 长会议(>90分钟)：适合上午，0-10分
        """
        hour = candidate_time.hour
        
        if duration_minutes <= 30:
            # 短会议适合任何时间
            return 10.0
        elif duration_minutes <= 90:
            # 中等会议
            if 9 <= hour <= 11 or 14 <= hour <= 16:
                return 10.0  # 最佳时间
            elif 8 <= hour <= 12 or 13 <= hour <= 17:
                return 7.0   # 较好时间
            else:
                return 3.0   # 一般时间
        else:
            # 长会议
            if 9 <= hour <= 11:
                return 10.0  # 上午最佳
            elif 8 <= hour <= 12:
                return 6.0   # 上午较好
            elif 14 <= hour <= 16:
                return 4.0   # 下午一般
            else:
                return 1.0   # 其他时间不太适合
    
    async def _find_relaxed_optimal_time(self, participants: List[int], duration_minutes: int,
                                       preferred_range: Dict[str, Any], 
                                       participant_timezones: Dict[int, str]) -> Optional[datetime]:
        """
        放宽条件寻找最优时间
        
        当严格条件下找不到合适时间时，放宽一些限制
        """
        # 扩展搜索范围
        start_date = preferred_range.get('start_date', datetime.utcnow().date())
        end_date = start_date + timedelta(days=30)  # 扩展到30天
        start_hour = preferred_range.get('start_hour', 8)  # 放宽到8点
        end_hour = preferred_range.get('end_hour', 20)     # 放宽到20点
        timezone_preference = preferred_range.get('timezone', 'UTC')
        
        # 生成放宽条件的候选时间
        candidate_times = await self._generate_candidate_times(
            start_date, end_date, start_hour, end_hour, duration_minutes, timezone_preference
        )
        
        # 允许一定程度的时间冲突（优先级较低的会议）
        scored_times = []
        for candidate_time in candidate_times:
            # 检查是否有高优先级冲突
            has_high_priority_conflict = await self._check_high_priority_conflicts(
                participants, candidate_time, duration_minutes
            )
            
            if not has_high_priority_conflict:
                score = await self._calculate_time_score(
                    candidate_time, participants, duration_minutes, participant_timezones
                )
                # 放宽条件下，降低分数要求
                if score > -50:  # 允许负分，但不能太低
                    scored_times.append((candidate_time, score))
        
        if scored_times:
            scored_times.sort(key=lambda x: x[1], reverse=True)
            return scored_times[0][0]
        
        return None
    
    async def _check_high_priority_conflicts(self, participants: List[int], start_time: datetime,
                                           duration_minutes: int) -> bool:
        """
        检查高优先级时间冲突
        
        只检查重要会议的冲突，允许与低优先级会议冲突
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # 查询高优先级会议冲突
        query = select(Meeting).join(MeetingParticipant).where(
            and_(
                MeetingParticipant.user_id.in_(participants),
                Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]),
                Meeting.deleted_at.is_(None),
                Meeting.meeting_type.in_([
                    MeetingType.PROJECT_KICKOFF,
                    MeetingType.REQUIREMENT_REVIEW,
                    MeetingType.DESIGN_REVIEW
                ]),  # 只考虑重要会议类型
                or_(
                    and_(Meeting.scheduled_start_time >= start_time, Meeting.scheduled_start_time < end_time),
                    and_(Meeting.scheduled_end_time > start_time, Meeting.scheduled_end_time <= end_time),
                    and_(Meeting.scheduled_start_time <= start_time, Meeting.scheduled_end_time >= end_time)
                )
            )
        )
        
        result = await self.db.execute(query)
        conflicts = result.scalars().all()
        
        return len(conflicts) > 0
    
    async def _get_fallback_time(self, preferred_range: Dict[str, Any]) -> datetime:
        """
        获取备选时间
        
        当所有智能调度都失败时，返回一个基本可用的时间
        """
        start_date = preferred_range.get('start_date', datetime.utcnow().date())
        start_hour = preferred_range.get('start_hour', 10)
        
        # 找到下一个工作日的上午10点
        fallback_date = start_date
        while fallback_date.weekday() >= 5:  # 跳过周末
            fallback_date += timedelta(days=1)
        
        fallback_time = datetime.combine(
            fallback_date,
            datetime.min.time().replace(hour=start_hour)
        )
        
        # 确保不早于当前时间
        if fallback_time < datetime.utcnow():
            fallback_time = datetime.utcnow() + timedelta(hours=1)
            # 调整到整点
            fallback_time = fallback_time.replace(minute=0, second=0, microsecond=0)
        
        logger.info(f"Using fallback time: {fallback_time}")
        return fallback_time
    
    async def _get_meeting_by_id(self, meeting_id: int) -> Meeting:
        """根据ID获取会议"""
        query = select(Meeting).where(
            and_(Meeting.id == meeting_id, Meeting.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError("会议不存在")
        
        return meeting
    
    async def _get_meeting_by_code(self, meeting_code: str) -> Meeting:
        """根据编码获取会议"""
        query = select(Meeting).where(
            and_(Meeting.meeting_code == meeting_code, Meeting.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError("会议不存在")
        
        return meeting
    
    async def _add_organizer_as_participant(self, meeting_id: int, organizer_id: int) -> None:
        """添加组织者为参与者"""
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=organizer_id,
            participant_role=ParticipantRole.ORGANIZER,
            invitation_status=InvitationStatus.ACCEPTED,
            can_share_screen=True,
            can_use_chat=True,
            can_use_whiteboard=True,
            can_record=True,
            created_by=organizer_id
        )
        
        self.db.add(participant)
        await self.db.flush()
    
    async def _add_participants(self, meeting_id: int, participants: List[Dict[str, Any]], 
                              organizer_id: int) -> None:
        """批量添加参与者"""
        for participant_data in participants:
            await self._add_single_participant(meeting_id, participant_data, organizer_id)
    
    async def _add_single_participant(self, meeting_id: int, participant_data: Dict[str, Any], 
                                    organizer_id: int) -> Optional[MeetingParticipant]:
        """添加单个参与者"""
        user_id = participant_data.get('user_id')
        if not user_id:
            return None
        
        # 检查是否已存在
        existing = await self._get_participant_by_meeting_and_user(meeting_id, user_id)
        if existing:
            return existing
        
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=user_id,
            participant_role=ParticipantRole(participant_data.get('role', 'PARTICIPANT')),
            can_share_screen=participant_data.get('can_share_screen', True),
            can_use_chat=participant_data.get('can_use_chat', True),
            can_use_whiteboard=participant_data.get('can_use_whiteboard', True),
            can_record=participant_data.get('can_record', False),
            created_by=organizer_id
        )
        
        self.db.add(participant)
        await self.db.flush()
        return participant
    
    async def _get_participant_by_meeting_and_user(self, meeting_id: int, user_id: int) -> Optional[MeetingParticipant]:
        """获取特定会议的特定参与者"""
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_participant_count(self, meeting_id: int) -> int:
        """获取参与者数量"""
        query = select(func.count(MeetingParticipant.id)).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def _send_invitations(self, meeting: Meeting) -> None:
        """发送会议邀请"""
        try:
            participants = await self._get_meeting_participants(meeting.id)
            pending_participants = [
                p for p in participants
                if p.invitation_status == InvitationStatus.PENDING
            ]
            if pending_participants:
                await self.notification_service.send_meeting_invitation(meeting, pending_participants)
                await self.notification_service.schedule_meeting_reminders(meeting)
                logger.info(
                    f"Sent invitations for meeting {meeting.meeting_code} "
                    f"to {len(pending_participants)} participants"
                )
        except Exception as e:
            logger.error(f"Error sending invitations for meeting {meeting.meeting_code}: {str(e)}")

    async def _send_participant_invitation(self, meeting: Meeting, participant: MeetingParticipant) -> None:
        """发送参与者邀请"""
        try:
            await self.notification_service.send_meeting_invitation(meeting, [participant])
            logger.info(f"Sending invitation to user {participant.user_id} for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending invitation to user {participant.user_id}: {str(e)}")
    
    async def _add_to_waiting_room(self, meeting_id: int, user_id: int) -> None:
        """添加到等候室"""
        # TODO: 实现等候室逻辑
        logger.info(f"Added user {user_id} to waiting room for meeting {meeting_id}")
        pass
    
    async def _generate_access_token(self, meeting_id: int, user_id: int, role: ParticipantRole) -> str:
        """生成访问令牌"""
        # TODO: 实现JWT令牌生成
        import secrets
        return secrets.token_urlsafe(32)
    
    async def _get_meeting_config(self, meeting: Meeting, participant: MeetingParticipant) -> Dict[str, Any]:
        """获取会议配置"""
        return {
            'meeting_id': meeting.id,
            'meeting_code': meeting.meeting_code,
            'title': meeting.title,
            'participant_role': participant.participant_role.value,
            'permissions': {
                'can_share_screen': participant.can_share_screen,
                'can_use_chat': participant.can_use_chat,
                'can_use_whiteboard': participant.can_use_whiteboard,
                'can_record': participant.can_record
            },
            'settings': meeting.meeting_settings or {}
        }
    
    async def _get_webrtc_config(self, meeting_id: int) -> Dict[str, Any]:
        """获取WebRTC配置"""
        # TODO: 实现WebRTC配置生成
        return {
            'iceServers': [
                {'urls': 'stun:stun.l.google.com:19302'}
            ],
            'room_id': f"room_{meeting_id}"
        }
    
    async def _validate_start_meeting_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证开始会议权限"""
        # 组织者可以开始
        if meeting.organizer_id == user_id:
            return
        
        # 检查主持人权限
        participant = await self._get_participant_by_meeting_and_user(meeting.id, user_id)
        if participant and participant.participant_role in [ParticipantRole.ORGANIZER, ParticipantRole.MODERATOR]:
            return
        
        raise PermissionError("无权限开始此会议")
    
    async def _validate_end_meeting_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证结束会议权限"""
        # 组织者可以结束
        if meeting.organizer_id == user_id:
            return
        
        # 检查主持人权限
        participant = await self._get_participant_by_meeting_and_user(meeting.id, user_id)
        if participant and participant.participant_role in [ParticipantRole.ORGANIZER, ParticipantRole.MODERATOR]:
            return
        
        raise PermissionError("无权限结束此会议")
    
    async def _validate_manage_participants_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证管理参与者权限"""
        # 组织者可以管理
        if meeting.organizer_id == user_id:
            return
        
        # 检查主持人权限
        participant = await self._get_participant_by_meeting_and_user(meeting.id, user_id)
        if participant and participant.participant_role in [ParticipantRole.ORGANIZER, ParticipantRole.MODERATOR]:
            return
        
        raise PermissionError("无权限管理此会议的参与者")
    
    async def _update_participants_on_meeting_end(self, meeting_id: int) -> None:
        """会议结束时更新参与者状态"""
        # 更新所有仍在会议中的参与者状态
        query = update(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.attendance_status == AttendanceStatus.JOINED
            )
        ).values(
            attendance_status=AttendanceStatus.LEFT,
            leave_time=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.db.execute(query)
    

    
    async def _send_meeting_start_notifications(self, meeting: Meeting) -> None:
        """发送会议开始通知"""
        participants = await self._get_meeting_participants(meeting.id)
        
        notification_data = {
            'meeting_id': meeting.id,
            'meeting_code': meeting.meeting_code,
            'meeting_title': meeting.title,
            'started_at': meeting.actual_start_time.isoformat()
        }
        
        for participant in participants:
            await self._send_notification(
                participant.user_id,
                'meeting_started',
                f"会议 {meeting.title} 已开始",
                notification_data
            )
        
        logger.info(f"Sent start notifications for meeting {meeting.meeting_code}")
    
    async def _send_meeting_end_notifications(self, meeting: Meeting) -> None:
        """发送会议结束通知"""
        participants = await self._get_meeting_participants(meeting.id)
        
        notification_data = {
            'meeting_id': meeting.id,
            'meeting_code': meeting.meeting_code,
            'meeting_title': meeting.title,
            'ended_at': meeting.actual_end_time.isoformat(),
            'duration_minutes': meeting.duration_minutes
        }
        
        for participant in participants:
            await self._send_notification(
                participant.user_id,
                'meeting_ended',
                f"会议 {meeting.title} 已结束",
                notification_data
            )
        
        logger.info(f"Sent end notifications for meeting {meeting.meeting_code}")
        
        # 计算该小时的偏好度
        hour_count = hour_preferences.get(candidate_hour, 0)
        preference_ratio = hour_count / total_meetings if total_meetings > 0 else 0
        
        return preference_ratio * 20.0
    
    def _calculate_duration_score(self, candidate_time: datetime, duration_minutes: int) -> float:
        """
        计算会议时长适配评分
        
        评分逻辑：
        - 短会议（≤30分钟）在任何时间都适合：10分
        - 中等会议（31-90分钟）在上午或下午早期较好：5-10分
        - 长会议（>90分钟）在上午较好：0-8分
        """
        hour = candidate_time.hour
        
        if duration_minutes <= 30:
            return 10.0
        elif duration_minutes <= 90:
            # 中等会议偏好上午和下午早期
            if 9 <= hour <= 11 or 14 <= hour <= 16:
                return 10.0
            elif 8 <= hour <= 12 or 13 <= hour <= 17:
                return 7.0
            else:
                return 5.0
        else:
            # 长会议偏好上午
            if 9 <= hour <= 11:
                return 8.0
            elif 8 <= hour <= 12:
                return 6.0
            elif 14 <= hour <= 16:
                return 4.0
            else:
                return 2.0
    
    async def _find_relaxed_optimal_time(self, participants: List[int], duration_minutes: int,
                                       preferred_range: Dict[str, Any], 
                                       participant_timezones: Dict[int, str]) -> Optional[datetime]:
        """
        放宽条件寻找最优时间
        
        放宽策略：
        1. 扩展时间范围到30天
        2. 包含周末
        3. 扩展工作时间到7:00-21:00
        """
        logger.info("Searching with relaxed conditions")
        
        start_date = preferred_range.get('start_date', datetime.utcnow().date())
        end_date = start_date + timedelta(days=30)  # 扩展到30天
        start_hour = 7  # 扩展工作时间
        end_hour = 21
        timezone_preference = preferred_range.get('timezone', 'UTC')
        
        # 生成放宽条件的候选时间
        candidate_times = await self._generate_relaxed_candidate_times(
            start_date, end_date, start_hour, end_hour, duration_minutes, timezone_preference
        )
        
        # 计算评分
        scored_times = []
        for candidate_time in candidate_times:
            if not await self._check_time_conflicts(participants, candidate_time, duration_minutes):
                score = await self._calculate_time_score(
                    candidate_time, participants, duration_minutes, participant_timezones
                )
                scored_times.append((candidate_time, score))
        
        if scored_times:
            scored_times.sort(key=lambda x: x[1], reverse=True)
            return scored_times[0][0]
        
        return None
    
    async def _generate_relaxed_candidate_times(self, start_date: datetime.date, end_date: datetime.date,
                                              start_hour: int, end_hour: int, duration_minutes: int,
                                              timezone_preference: str) -> List[datetime]:
        """生成放宽条件的候选时间列表"""
        import pytz
        
        candidate_times = []
        current_date = start_date
        
        try:
            tz = pytz.timezone(timezone_preference)
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
        
        while current_date <= end_date:
            # 包含周末，但给工作日更高优先级
            for hour in range(start_hour, end_hour):
                for minute in [0, 30]:
                    candidate_time = datetime.combine(
                        current_date, 
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                    
                    localized_time = tz.localize(candidate_time)
                    utc_time = localized_time.astimezone(pytz.UTC).replace(tzinfo=None)
                    
                    meeting_end = utc_time + timedelta(minutes=duration_minutes)
                    end_hour_utc = tz.localize(
                        datetime.combine(current_date, datetime.min.time().replace(hour=end_hour))
                    ).astimezone(pytz.UTC).replace(tzinfo=None)
                    
                    if meeting_end <= end_hour_utc:
                        candidate_times.append(utc_time)
            
            current_date += timedelta(days=1)
        
        return candidate_times
    
    async def _get_fallback_time(self, preferred_range: Dict[str, Any]) -> datetime:
        """
        获取备选时间
        
        当所有智能调度都失败时，返回一个基本可用的时间
        """
        import pytz
        
        timezone_preference = preferred_range.get('timezone', 'UTC')
        try:
            tz = pytz.timezone(timezone_preference)
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
        
        # 默认为明天上午10点
        tomorrow = datetime.utcnow().date() + timedelta(days=1)
        fallback_time = datetime.combine(tomorrow, datetime.min.time().replace(hour=10))
        
        # 转换为UTC
        localized_time = tz.localize(fallback_time)
        utc_time = localized_time.astimezone(pytz.UTC).replace(tzinfo=None)
        
        logger.info(f"Using fallback time: {utc_time}")
        return utc_time
    
    async def _get_meeting_by_id(self, meeting_id: int) -> Meeting:
        """根据ID获取会议"""
        query = select(Meeting).where(
            and_(Meeting.id == meeting_id, Meeting.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError("会议不存在")
        
        return meeting
    
    async def _get_meeting_by_code(self, meeting_code: str) -> Meeting:
        """根据编码获取会议"""
        query = select(Meeting).where(
            and_(Meeting.meeting_code == meeting_code, Meeting.deleted_at.is_(None))
        )
        result = await self.db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            raise NotFoundError("会议不存在")
        
        return meeting
    
    async def _validate_update_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证更新权限"""
        if meeting.organizer_id != user_id:
            # 检查是否有管理员权限
            has_admin_permission = await self.permission_service.check_permission(
                user_id, 'meeting:admin'
            )
            if not has_admin_permission:
                raise PermissionError("只有会议组织者或管理员可以修改会议")
    
    async def _validate_delete_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证删除权限"""
        await self._validate_update_permission(meeting, user_id)
    
    async def _validate_manage_participants_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证管理参与者权限"""
        await self._validate_update_permission(meeting, user_id)
    
    async def _validate_start_meeting_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证开始会议权限"""
        # 检查是否是组织者或主持人
        if meeting.organizer_id == user_id:
            return
        
        # 检查是否是主持人
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting.id,
                MeetingParticipant.user_id == user_id,
                MeetingParticipant.participant_role == ParticipantRole.MODERATOR
            )
        )
        result = await self.db.execute(query)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise PermissionError("只有会议组织者或主持人可以开始会议")
    
    async def _validate_end_meeting_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证结束会议权限"""
        await self._validate_start_meeting_permission(meeting, user_id)
    
    async def _add_organizer_as_participant(self, meeting_id: int, organizer_id: int) -> MeetingParticipant:
        """添加组织者为参与者"""
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=organizer_id,
            participant_role=ParticipantRole.ORGANIZER,
            invitation_status=InvitationStatus.ACCEPTED,
            can_share_screen=True,
            can_use_chat=True,
            can_use_whiteboard=True,
            can_record=True,
            created_by=organizer_id
        )
        
        self.db.add(participant)
        await self.db.flush()
        return participant
    
    async def _add_participants(self, meeting_id: int, participants: List[Dict[str, Any]], organizer_id: int) -> None:
        """批量添加参与者"""
        for participant_data in participants:
            await self._add_single_participant(meeting_id, participant_data, organizer_id)
    
    async def _add_single_participant(self, meeting_id: int, participant_data: Dict[str, Any], organizer_id: int) -> Optional[MeetingParticipant]:
        """添加单个参与者"""
        user_id = participant_data['user_id']
        
        # 检查是否已存在
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"User {user_id} already participant in meeting {meeting_id}")
            return None
        
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=user_id,
            participant_role=ParticipantRole(participant_data.get('role', 'PARTICIPANT')),
            can_share_screen=participant_data.get('can_share_screen', True),
            can_use_chat=participant_data.get('can_use_chat', True),
            can_use_whiteboard=participant_data.get('can_use_whiteboard', True),
            can_record=participant_data.get('can_record', False),
            created_by=organizer_id
        )
        
        self.db.add(participant)
        await self.db.flush()
        return participant
    
    async def _get_participant_count(self, meeting_id: int) -> int:
        """获取参与者数量"""
        query = select(func.count(MeetingParticipant.id)).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def _get_participant_by_meeting_and_user(self, meeting_id: int, user_id: int) -> Optional[MeetingParticipant]:
        """获取特定会议的参与者"""
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _update_participants_on_meeting_end(self, meeting_id: int) -> None:
        """会议结束时更新参与者状态"""
        # 更新所有已加入但未离开的参与者
        query = update(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.attendance_status == AttendanceStatus.JOINED,
                MeetingParticipant.leave_time.is_(None)
            )
        ).values(
            attendance_status=AttendanceStatus.LEFT,
            leave_time=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.db.execute(query)
    
    async def _generate_access_token(self, meeting_id: int, user_id: int, role: ParticipantRole) -> str:
        """生成访问令牌"""
        # 简化实现：生成随机令牌
        # 实际应用中应该使用JWT或其他安全令牌
        token_data = f"{meeting_id}:{user_id}:{role.value}:{datetime.utcnow().timestamp()}"
        return secrets.token_urlsafe(32)
    
    async def _get_meeting_config(self, meeting: Meeting, participant: MeetingParticipant) -> Dict[str, Any]:
        """获取会议配置"""
        return {
            'meeting_id': meeting.id,
            'meeting_code': meeting.meeting_code,
            'title': meeting.title,
            'is_recording_enabled': meeting.is_recording_enabled,
            'participant_permissions': {
                'can_share_screen': participant.can_share_screen,
                'can_use_chat': participant.can_use_chat,
                'can_use_whiteboard': participant.can_use_whiteboard,
                'can_record': participant.can_record
            },
            'meeting_settings': meeting.meeting_settings or {}
        }
    
    async def _get_webrtc_config(self, meeting_id: int) -> Dict[str, Any]:
        """获取WebRTC配置"""
        # 简化实现：返回基本配置
        # 实际应用中应该集成真实的WebRTC服务
        return {
            'ice_servers': [
                {'urls': 'stun:stun.l.google.com:19302'},
                # TURN服务器配置
            ],
            'room_id': f"room_{meeting_id}",
            'media_constraints': {
                'video': True,
                'audio': True
            }
        }
    
    # 通知相关方法（占位符实现）
    
    async def _send_invitations(self, meeting: Meeting) -> None:
        """发送会议邀请"""
        try:
            # 获取所有参与者（含组织者，组织者作为参与人也需要收到通知）
            participants = await self._get_meeting_participants(meeting.id)
            if participants:
                await self.notification_service.send_meeting_invitation(meeting, participants)
                await self.notification_service.schedule_meeting_reminders(meeting)

            logger.info(f"Sent invitations for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending invitations for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_participant_invitation(self, meeting: Meeting, participant: MeetingParticipant) -> None:
        """发送参与者邀请"""
        try:
            await self.notification_service.send_meeting_invitation(meeting, [participant])
            logger.info(f"Sent invitation to user {participant.user_id} for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending invitation to user {participant.user_id}: {str(e)}")
    
    async def _send_meeting_change_notifications(self, meeting: Meeting, changes: Dict[str, Any]) -> None:
        """发送会议变更通知"""
        try:
            await self.notification_service.send_meeting_change_notification(meeting, changes)
            logger.info(f"Sent change notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending change notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_meeting_cancellation_notifications(self, meeting: Meeting) -> None:
        """发送会议取消通知"""
        try:
            # 获取取消原因
            reason = None
            if meeting.meeting_settings and 'cancellation_reason' in meeting.meeting_settings:
                reason = meeting.meeting_settings['cancellation_reason']
            
            await self.notification_service.send_meeting_cancellation_notification(meeting, reason)
            logger.info(f"Sent cancellation notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending cancellation notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_meeting_start_notifications(self, meeting: Meeting) -> None:
        """发送会议开始通知"""
        try:
            await self.notification_service.send_meeting_started_notification(meeting)
            logger.info(f"Sent start notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending start notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _send_meeting_end_notifications(self, meeting: Meeting, statistics: Dict[str, Any] = None) -> None:
        """发送会议结束通知"""
        try:
            await self.notification_service.send_meeting_ended_notification(meeting)
            logger.info(f"Sent end notifications for meeting {meeting.meeting_code}")
        except Exception as e:
            logger.error(f"Error sending end notifications for meeting {meeting.meeting_code}: {str(e)}")
    
    async def _add_to_waiting_room(self, meeting_id: int, user_id: int) -> None:
        """添加到等候室"""
        # TODO: 实现等候室逻辑
        logger.info(f"Added user {user_id} to waiting room for meeting {meeting_id}")
    

    
    async def _validate_update_data(self, update_data: Dict[str, Any], meeting: Meeting) -> None:
        """验证更新数据"""
        # 验证时间逻辑
        if 'scheduled_start_time' in update_data and 'scheduled_end_time' in update_data:
            if update_data['scheduled_start_time'] >= update_data['scheduled_end_time']:
                raise ValidationError("会议开始时间必须早于结束时间")
        
        # 验证会议类型
        if 'meeting_type' in update_data:
            try:
                MeetingType(update_data['meeting_type'])
            except ValueError:
                raise ValidationError("无效的会议类型")  
  # 参与者邀请管理相关的私有方法
    
    async def _validate_participants_data(self, participants: List[Dict[str, Any]]) -> None:
        """验证参与者数据"""
        if not participants:
            raise ValidationError("参与者列表不能为空")
        
        user_ids = []
        for participant_data in participants:
            # 验证必填字段
            if 'user_id' not in participant_data:
                raise ValidationError("参与者数据缺少user_id字段")
            
            user_id = participant_data['user_id']
            if not isinstance(user_id, int) or user_id <= 0:
                raise ValidationError(f"无效的用户ID: {user_id}")
            
            # 检查重复用户
            if user_id in user_ids:
                raise ValidationError(f"重复的用户ID: {user_id}")
            user_ids.append(user_id)
            
            # 验证角色
            if 'participant_role' in participant_data:
                try:
                    ParticipantRole(participant_data['participant_role'].upper())
                except ValueError:
                    raise ValidationError(f"无效的参与者角色: {participant_data['participant_role']}")
        
        # 验证用户是否存在
        query = select(User.id).where(User.id.in_(user_ids))
        result = await self.db.execute(query)
        existing_user_ids = [row[0] for row in result.fetchall()]
        
        missing_users = set(user_ids) - set(existing_user_ids)
        if missing_users:
            raise ValidationError(f"用户不存在: {list(missing_users)}")
    
    async def _add_single_participant(self, meeting_id: int, participant_data: Dict[str, Any], 
                                    user_id: int) -> Optional[MeetingParticipant]:
        """添加单个参与者"""
        participant_user_id = participant_data['user_id']
        
        # 检查是否已经是参与者
        existing_participant = await self._get_participant_by_meeting_and_user(meeting_id, participant_user_id)
        if existing_participant:
            logger.warning(f"User {participant_user_id} is already a participant in meeting {meeting_id}")
            return None
        
        # 创建参与者记录
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            user_id=participant_user_id,
            participant_role=ParticipantRole(participant_data.get('participant_role', 'PARTICIPANT').upper()),
            invitation_status=InvitationStatus.PENDING,
            attendance_status=AttendanceStatus.NOT_JOINED,
            can_share_screen=participant_data.get('can_share_screen', True),
            can_use_chat=participant_data.get('can_use_chat', True),
            can_use_whiteboard=participant_data.get('can_use_whiteboard', True),
            can_record=participant_data.get('can_record', False),
            invited_at=datetime.utcnow(),
            created_by=user_id,
            updated_by=user_id
        )
        
        self.db.add(participant)
        await self.db.flush()  # 获取ID
        
        return participant
    
    async def _send_invitations_batch(self, meeting: Meeting, participants: List[MeetingParticipant]) -> bool:
        """批量发送邀请通知"""
        try:
            # 使用通知服务发送邀请
            await self.notification_service.send_meeting_invitation(meeting, participants)
            
            # 安排会议提醒
            await self.notification_service.schedule_meeting_reminders(meeting)
            
            logger.info(f"Successfully sent invitations for meeting {meeting.meeting_code} to {len(participants)} participants")
            return True
            
        except Exception as e:
            logger.error(f"Error sending batch invitations for meeting {meeting.meeting_code}: {str(e)}")
            return False
    
    async def _send_participant_invitation(self, meeting: Meeting, participant: MeetingParticipant) -> bool:
        """发送单个参与者邀请"""
        try:
            await self.notification_service.send_meeting_invitation(meeting, [participant])
            logger.info(f"Sent invitation to user {participant.user_id} for meeting {meeting.meeting_code}")
            return True
        except Exception as e:
            logger.error(f"Error sending invitation to user {participant.user_id}: {str(e)}")
            return False
    

    

    
    async def _set_default_permissions_by_role(self, participant: MeetingParticipant, role: ParticipantRole) -> None:
        """根据角色设置默认权限"""
        if role == ParticipantRole.ORGANIZER:
            participant.can_share_screen = True
            participant.can_use_chat = True
            participant.can_use_whiteboard = True
            participant.can_record = True
        elif role == ParticipantRole.MODERATOR:
            participant.can_share_screen = True
            participant.can_use_chat = True
            participant.can_use_whiteboard = True
            participant.can_record = True
        elif role == ParticipantRole.PRESENTER:
            participant.can_share_screen = True
            participant.can_use_chat = True
            participant.can_use_whiteboard = True
            participant.can_record = False
        elif role == ParticipantRole.PARTICIPANT:
            participant.can_share_screen = True
            participant.can_use_chat = True
            participant.can_use_whiteboard = True
            participant.can_record = False
        elif role == ParticipantRole.OBSERVER:
            participant.can_share_screen = False
            participant.can_use_chat = True
            participant.can_use_whiteboard = False
            participant.can_record = False
    
    async def _validate_manage_participants_permission(self, meeting: Meeting, user_id: int) -> None:
        """验证管理参与者权限"""
        # 组织者可以管理参与者
        if meeting.organizer_id == user_id:
            return
        
        # 检查是否是主持人
        participant = await self._get_participant_by_meeting_and_user(meeting.id, user_id)
        if participant and participant.participant_role == ParticipantRole.MODERATOR:
            return
        
        # 检查管理员权限
        if await self.permission_service.check_permission(user_id, 'meeting:admin'):
            return
        
        # 检查项目管理权限
        if meeting.project_id:
            if await self.permission_service.check_project_permission(user_id, meeting.project_id, 'meeting:manage_participants'):
                return
        
        raise PermissionError("无权限管理会议参与者")
    
    async def _get_participant_count(self, meeting_id: int) -> int:
        """获取会议参与者数量"""
        query = select(func.count(MeetingParticipant.id)).where(MeetingParticipant.meeting_id == meeting_id)
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def _get_participant_by_meeting_and_user(self, meeting_id: int, user_id: int) -> Optional[MeetingParticipant]:
        """根据会议ID和用户ID获取参与者"""
        query = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    # 会议状态管理相关的私有方法
    
    async def _validate_status_transition(self, current_status: MeetingStatus, target_status: MeetingStatus) -> None:
        """
        验证会议状态转换是否合法
        
        Args:
            current_status: 当前状态
            target_status: 目标状态
            
        Raises:
            ValidationError: 状态转换不合法
        """
        # 定义合法的状态转换规则
        valid_transitions = {
            MeetingStatus.SCHEDULED: [MeetingStatus.IN_PROGRESS, MeetingStatus.CANCELLED, MeetingStatus.POSTPONED],
            MeetingStatus.IN_PROGRESS: [MeetingStatus.COMPLETED, MeetingStatus.CANCELLED],
            MeetingStatus.POSTPONED: [MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS, MeetingStatus.CANCELLED],
            MeetingStatus.COMPLETED: [],  # 已完成的会议不能转换到其他状态
            MeetingStatus.CANCELLED: []   # 已取消的会议不能转换到其他状态
        }
        
        allowed_targets = valid_transitions.get(current_status, [])
        if target_status not in allowed_targets:
            raise ValidationError(f"不能从状态 {current_status.value} 转换到 {target_status.value}")
    
    async def _validate_start_meeting_permission(self, meeting: Meeting, user_id: int) -> None:
        """
        验证开始会议权限
        
        Args:
            meeting: 会议对象
            user_id: 用户ID
            
        Raises:
            PermissionError: 权限不足
        """
        # 组织者可以开始会议
        if meeting.organizer_id == user_id:
            return
        
        # 检查是否是主持人
        participant = await self._get_participant_by_meeting_and_user(meeting.id, user_id)
        if participant and participant.participant_role == ParticipantRole.MODERATOR:
            return
        
        # 检查系统管理员权限
        if await self.permission_service.check_permission(user_id, 'meeting:admin'):
            return
        
        # 检查项目管理权限
        if meeting.project_id:
            if await self.permission_service.check_project_permission(user_id, meeting.project_id, 'meeting:start'):
                return
        
        raise PermissionError("无权限开始此会议")
    
    async def _validate_end_meeting_permission(self, meeting: Meeting, user_id: int) -> None:
        """
        验证结束会议权限
        
        Args:
            meeting: 会议对象
            user_id: 用户ID
            
        Raises:
            PermissionError: 权限不足
        """
        # 结束会议的权限与开始会议相同
        await self._validate_start_meeting_permission(meeting, user_id)
    
    async def _initialize_meeting_statistics(self, meeting_id: int) -> None:
        """
        初始化会议统计信息
        
        Args:
            meeting_id: 会议ID
        """
        # 重置所有参与者的统计信息
        query = update(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id
        ).values(
            total_duration_minutes=0,
            speak_duration_minutes=0,
            interaction_count=0,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        
        logger.info(f"Initialized statistics for meeting {meeting_id}")
    
    async def _update_participants_on_meeting_end(self, meeting_id: int) -> None:
        """
        会议结束时更新参与者出席状态和统计信息
        
        Args:
            meeting_id: 会议ID
        """
        current_time = datetime.utcnow()
        
        # 获取所有参与者
        query = select(MeetingParticipant).where(MeetingParticipant.meeting_id == meeting_id)
        result = await self.db.execute(query)
        participants = result.scalars().all()
        
        for participant in participants:
            # 更新仍在会议中的参与者状态
            if participant.attendance_status == AttendanceStatus.JOINED:
                participant.attendance_status = AttendanceStatus.LEFT
                participant.leave_time = current_time
                
                # 计算参与时长
                if participant.join_time:
                    duration = current_time - participant.join_time
                    participant.total_duration_minutes = int(duration.total_seconds() / 60)
                
                participant.updated_at = current_time
        
        logger.info(f"Updated {len(participants)} participants on meeting end for meeting {meeting_id}")
    
    async def _stop_all_recordings(self, meeting_id: int) -> None:
        """
        停止所有录制
        
        Args:
            meeting_id: 会议ID
        """
        try:
            # 这里应该调用录制服务来停止录制
            # 由于录制服务可能还未实现，先记录日志
            logger.info(f"Stopping all recordings for meeting {meeting_id}")
            
            # TODO: 集成录制服务
            # from ..services.recording_service import RecordingService
            # recording_service = RecordingService(self.db)
            # await recording_service.stop_all_recordings_for_meeting(meeting_id)
            
        except Exception as e:
            logger.error(f"Failed to stop recordings for meeting {meeting_id}: {str(e)}")
    
    async def _calculate_meeting_statistics(self, meeting_id: int) -> Dict[str, Any]:
        """
        计算会议统计数据
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            会议统计数据
        """
        # 获取参与者统计 - 使用简化的查询
        total_participants_query = select(func.count(MeetingParticipant.id)).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        
        attended_participants_query = select(func.count(MeetingParticipant.id)).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.attendance_status.in_([AttendanceStatus.JOINED, AttendanceStatus.LEFT])
            )
        )
        
        avg_duration_query = select(func.avg(MeetingParticipant.total_duration_minutes)).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        
        total_interactions_query = select(func.sum(MeetingParticipant.interaction_count)).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        
        # 执行查询
        total_participants = (await self.db.execute(total_participants_query)).scalar() or 0
        attended_participants = (await self.db.execute(attended_participants_query)).scalar() or 0
        avg_duration = (await self.db.execute(avg_duration_query)).scalar() or 0
        total_interactions = (await self.db.execute(total_interactions_query)).scalar() or 0
        
        statistics = {
            'total_participants': total_participants,
            'attended_participants': attended_participants,
            'attendance_rate': (attended_participants / total_participants * 100) if total_participants > 0 else 0,
            'avg_participation_duration': float(avg_duration),
            'total_interactions': total_interactions
        }
        
        logger.info(f"Calculated statistics for meeting {meeting_id}: {statistics}")
        return statistics
    

    
    async def _log_meeting_event(self, meeting_id: int, event_type: str, user_id: int, event_data: Dict[str, Any] = None) -> None:
        """
        记录会议事件
        
        Args:
            meeting_id: 会议ID
            event_type: 事件类型
            user_id: 操作用户ID
            event_data: 事件数据
        """
        try:
            # TODO: 集成审计日志服务
            # from ..services.audit_service import AuditService
            # audit_service = AuditService(self.db)
            
            event_log = {
                'meeting_id': meeting_id,
                'event_type': event_type,
                'user_id': user_id,
                'event_data': event_data or {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Meeting event logged: {event_log}")
            
            # TODO: 实际记录到审计日志
            # await audit_service.log_meeting_event(event_log)
            
        except Exception as e:
            logger.error(f"Failed to log meeting event: {str(e)}")
    
    async def _get_meeting_participants(self, meeting_id: int) -> List[MeetingParticipant]:
        """
        获取会议参与者列表
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            参与者列表
        """
        query = select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()


def get_meeting_service(db: AsyncSession = Depends(get_async_session)) -> MeetingService:
    """
    获取会议服务实例
    
    Args:
        db: 数据库会话（通过依赖注入）
        
    Returns:
        MeetingService: 会议服务实例
    """
    return MeetingService(db)
