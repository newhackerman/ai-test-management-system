"""
会议AI分析服务

本模块实现会议AI分析的核心功能，包括：
- 智能会议摘要生成
- 关键信息提取
- 智能纪要生成
- 会议效果分析
- 情感和参与度分析
- 改进建议生成
- AI服务集成管理
- 转录和语音识别集成

技术特性：
- 异步编程模式，支持高并发
- 多AI服务提供商智能路由
- 上下文感知的智能分析
- 可扩展的分析引擎架构
- 与主系统AI服务无缝集成
- 全面的操作日志记录和监控
"""
import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload, joinedload

from ..core.config import get_settings
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.meeting import (
    Meeting as MeetingORM,
    MeetingParticipant as MeetingParticipantORM,
    MeetingChat as MeetingChatORM,
    MeetingFile as MeetingFileORM,
    MeetingMinutes as MeetingMinutesORM,
    MeetingAnalytics as MeetingAnalyticsORM,
    MeetingSummary as MeetingSummaryORM,
    MeetingTask as MeetingTaskORM,
    MinuteType as MinuteTypeORM,
    GenerationMethod as GenerationMethodORM,
    MinuteStatus as MinuteStatusORM,
)
from ..models.project import Task as ProjectTask
from ..models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class AnalysisType(Enum):
    """分析类型枚举"""
    SUMMARY = "summary"
    DECISIONS = "decisions"
    ACTION_ITEMS = "action_items"
    KEY_POINTS = "key_points"
    EFFECTIVENESS = "effectiveness"
    SENTIMENT = "sentiment"
    PARTICIPATION = "participation"
    IMPROVEMENT = "improvement"


class MinuteType(Enum):
    """纪要类型枚举"""
    AUTO_GENERATED = "AUTO_GENERATED"
    MANUAL_CREATED = "MANUAL_CREATED"
    AI_ENHANCED = "AI_ENHANCED"
    COLLABORATIVE = "COLLABORATIVE"


class GenerationMethod(Enum):
    """生成方式枚举"""
    SPEECH_TO_TEXT = "SPEECH_TO_TEXT"
    MANUAL_INPUT = "MANUAL_INPUT"
    AI_ANALYSIS = "AI_ANALYSIS"
    TEMPLATE_BASED = "TEMPLATE_BASED"


@dataclass
class MeetingSummary:
    """会议摘要数据类"""
    meeting_id: int
    overview: str
    key_points: List[str]
    decisions: List[Dict[str, Any]]
    action_items: List[Dict[str, Any]]
    next_steps: List[str]
    participants_analysis: Dict[str, Any]
    generated_at: datetime
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ActionItem:
    """行动项目数据类"""
    meeting_id: int
    task_description: str
    assignee_name: str
    assignee_id: Optional[int] = None
    deadline: Optional[datetime] = None
    priority: str = "MEDIUM"
    context: str = ""
    status: str = "PENDING"
    extracted_at: datetime = None
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.extracted_at is None:
            self.extracted_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EffectivenessAnalysis:
    """会议效果分析数据类"""
    meeting_id: int
    overall_score: float
    participation_metrics: List[Dict[str, Any]]  # 逐人指标（真实参会行推导）
    participation_summary: Dict[str, Any]  # 聚合参与度（真实计数推导）
    agenda_completion: Dict[str, Any]
    decision_efficiency: Dict[str, Any]
    time_utilization: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]
    improvement_suggestions: List[str]
    analyzed_at: datetime
    total_chat_messages: int = 0
    total_file_shares: int = 0
    action_item_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptSegment:
    """转录片段数据类"""
    speaker_id: Optional[int]
    speaker_name: str
    content: str
    start_time: float
    end_time: float
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MeetingMinutes:
    """会议纪要数据类"""
    meeting_id: int
    title: str
    content: str
    summary: str
    minute_type: MinuteType
    generation_method: GenerationMethod
    agenda_items: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    action_items: List[Dict[str, Any]]
    attendees: List[str]
    key_points: List[Dict[str, Any]]
    status: str = 'DRAFT'
    version: str = '1.0'
    created_by: Optional[int] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MeetingAIService:
    """会议AI分析核心服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # AI提示词模板
        self.prompt_templates = {
            'summary': self._get_summary_prompt_template(),
            'decisions': self._get_decisions_prompt_template(),
            'action_items': self._get_action_items_prompt_template(),
            'key_points': self._get_key_points_prompt_template(),
            'effectiveness': self._get_effectiveness_prompt_template(),
            'sentiment': self._get_sentiment_prompt_template(),
            'minutes': self._get_minutes_prompt_template()
        }
    
    async def _get_meeting_or_404(self, meeting_id: int) -> MeetingORM:
        """查会议行，不存在则 404。"""
        meeting = await self.db.get(MeetingORM, meeting_id)
        if not meeting:
            raise NotFoundError(f"会议 {meeting_id} 不存在")
        return meeting

    async def get_meeting_summary(self, meeting_id: int, user_id: int = None) -> Optional[Dict[str, Any]]:
        """从 meeting_summaries 表读最新一条摘要；无则返回 None。"""
        await self._get_meeting_or_404(meeting_id)
        result = await self.db.execute(
            select(MeetingSummaryORM)
            .where(MeetingSummaryORM.meeting_id == meeting_id)
            .order_by(desc(MeetingSummaryORM.generated_at))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row.to_response_dict() if row else None

    async def get_meeting_minutes(self, meeting_id: int, user_id: int = None, *,
                                  status=None, minute_type=None, version=None) -> List[MeetingMinutesORM]:
        """从 meeting_minutes 表读纪要列表（支持状态/类型/版本筛选）。"""
        await self._get_meeting_or_404(meeting_id)
        stmt = (
            select(MeetingMinutesORM)
            .where(MeetingMinutesORM.meeting_id == meeting_id)
            .order_by(desc(MeetingMinutesORM.created_at))
        )
        if status is not None:
            status_value = status.value if hasattr(status, "value") else status
            stmt = stmt.where(MeetingMinutesORM.status == status_value)
        if minute_type is not None:
            type_value = minute_type.value if hasattr(minute_type, "value") else minute_type
            stmt = stmt.where(MeetingMinutesORM.minute_type == type_value)
        if version is not None:
            stmt = stmt.where(MeetingMinutesORM.version == version)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_advanced_analytics(self, meeting_id: int, user_id: int = None) -> Optional[Dict[str, Any]]:
        """
        获取高级分析（未实现：依赖转录 + 主题/情感模型，暂无真实数据源，
        返回 None，由路由层转为 404；不要用假数据填充）。
        """
        return None

    async def generate_meeting_analytics(self, meeting_id: int, user_id: int = None,
                                         *, force_regenerate: bool = False) -> Optional[Dict[str, Any]]:
        """生成会议分析并持久化到 meeting_analytics 表（按 meeting_id upsert）。

        选择持久化而不是删端点：GET /analytics 本就是即时计算，生成端点
        的价值在于把同一次计算落库，供报告/对比复用，避免每次重复算。
        """
        meeting = await self._get_meeting_or_404(meeting_id)
        analysis = await self.analyze_meeting_effectiveness(meeting_id, user_id)
        response = self.analytics_to_response_dict(analysis)

        result = await self.db.execute(
            select(MeetingAnalyticsORM).where(MeetingAnalyticsORM.meeting_id == meeting_id)
        )
        row = result.scalar_one_or_none()
        details = analysis.to_dict() if hasattr(analysis, "to_dict") else dict(analysis)
        # detailed_analytics 是 JSON 列：datetime 需先转 ISO 字符串，否则 INSERT 报 not JSON serializable
        details = json.loads(json.dumps(details, default=str))
        if row is None:
            row = MeetingAnalyticsORM(meeting_id=meeting_id)
            self.db.add(row)
        per_person = details.get("participation_metrics") or []
        total_participants = len(per_person)
        total_speak = sum(float(p.get("speaking_time_minutes") or 0) for p in per_person)
        participation = details.get("participation_summary") or {}
        row.total_participants = total_participants
        row.peak_participants = total_participants
        row.avg_participation_rate = participation.get("participation_rate")
        row.total_speaking_time = int(total_speak * 60)
        row.avg_speaking_time_per_person = int(total_speak * 60 / total_participants) if total_participants else 0
        row.total_chat_messages = details.get("total_chat_messages", 0)
        row.total_file_shares = details.get("total_file_shares", 0)
        row.agenda_completion_rate = details.get("agenda_completion", {}).get("completion_rate")
        row.decision_count = details.get("decision_efficiency", {}).get("total_decisions", 0)
        row.action_item_count = details.get("action_item_count", 0)
        row.overall_sentiment_score = None  # 无转录，情感分数无真实来源，不写数字
        row.engagement_score = participation.get("engagement_score")
        row.detailed_analytics = details
        row.analyzed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return response

    async def get_meeting_transcription(self, meeting_id: int, user_id: int = None) -> Optional[Dict[str, Any]]:
        """
        获取会议转录。

        转录红线：真实转录依赖录制文件 + STT，全链路缺失，本服务不伪造
        任何转录文本，始终返回 None（路由层转为 404 并提示确认会议已
        录制并处理完成）。
        """
        return None

    # ---- LLM 接入（唯一调用缝）-------------------------------------------
    async def _call_llm_json(self, prompt: str) -> Dict[str, Any]:
        """调一次 OpenAI 兼容 Chat Completions，要求返回 JSON。

        复用 ai_assistant_service 的既有链路：
        AIAssistantService._call_ai_service(prompt, provider, context)
        → _call_openai_compatible_service，POST {endpoint}/chat/completions，
        endpoint/model/key 经 _get_openai_setting 从项目 .env 读
        （OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL=gpt-3.5-turbo）。
        不另接服务商、不引新 SDK。本方法是测试 mock 的缝：测试里 patch
        它，断言 prompt 含真实上下文且不含罐头文本，绝不烧真调用。
        """
        from .ai_assistant_service import AIAssistantService, AIProvider

        assistant = AIAssistantService()
        response = await assistant._call_ai_service(prompt, AIProvider.OPENAI, {})
        text = (response.content or "").strip()
        # 允许模型包一层 ```json fences 或少量前后缀：取首尾大括号之间的 JSON
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("LLM 未返回 JSON 内容，无法解析会议摘要")
        try:
            parsed = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM 返回内容不是合法 JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("LLM 返回的 JSON 不是对象")
        parsed["_llm_model"] = response.model
        parsed["_llm_confidence"] = response.confidence_score
        return parsed

    async def _build_meeting_context(self, meeting_id: int) -> Dict[str, Any]:
        """汇总一次摘要所需的全部真实上下文（议程/参与者/聊天/文件/时长）。

        转录无真实来源：transcript 恒为空字符串并在 prompt 里明示
        “无转录，不得编造发言”。调用方只做一次 LLM 调用。
        """
        meeting = await self._get_meeting_or_404(meeting_id)
        participants = await self._get_meeting_participants(meeting_id)
        chats = await self._get_meeting_chats(meeting_id)
        files = await self._get_meeting_files(meeting_id)
        return {
            "meeting": {
                "id": meeting.id,
                "title": meeting.title,
                "description": meeting.description,
                "meeting_type": meeting.meeting_type.value if meeting.meeting_type else None,
                "status": meeting.status.value if meeting.status else None,
                "scheduled_start_time": meeting.scheduled_start_time.isoformat() if meeting.scheduled_start_time else None,
                "scheduled_end_time": meeting.scheduled_end_time.isoformat() if meeting.scheduled_end_time else None,
                "actual_start_time": meeting.actual_start_time.isoformat() if meeting.actual_start_time else None,
                "actual_end_time": meeting.actual_end_time.isoformat() if meeting.actual_end_time else None,
                "duration_minutes": meeting.duration_minutes,
                "agenda": meeting.agenda or [],
            },
            "participants": participants,
            "chats": chats,
            "files": files,
            "transcript": "",
            "transcript_available": False,
        }

    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """把真实上下文压成精简 prompt 素材（省 token、省调用）。"""
        meeting = context["meeting"]
        lines = [
            f"会议标题：{meeting['title']}",
            f"会议描述：{meeting.get('description') or '（未提供）'}",
            f"会议类型：{meeting.get('meeting_type') or '（未知）'}，状态：{meeting.get('status') or '（未知）'}",
            f"计划时间：{meeting.get('scheduled_start_time') or '（未知）'} 至 {meeting.get('scheduled_end_time') or '（未知）'}",
            f"实际时间：{meeting.get('actual_start_time') or '（未记录）'} 至 {meeting.get('actual_end_time') or '（未记录）'}",
            f"计划时长：{meeting.get('duration_minutes') or '（未知）'} 分钟",
        ]
        agenda = meeting.get("agenda") or []
        if agenda:
            items = []
            for item in agenda[:10]:
                if isinstance(item, dict):
                    items.append(item.get("title") or item.get("topic") or str(item))
                else:
                    items.append(str(item))
            lines.append("议程：" + "；".join(items))
        else:
            lines.append("议程：（未提供）")
        participants = context.get("participants") or []
        if participants:
            names = [p.get("name") or f"用户{p.get('user_id')}" for p in participants]
            lines.append(f"参与者（{len(names)} 人）：{'、'.join(names)}")
        else:
            lines.append("参与者：（无记录）")
        chats = context.get("chats") or []
        if chats:
            lines.append("聊天记录（最近 50 条，发言人: 内容）：")
            for chat in chats[-50:]:
                lines.append(f"- {chat.get('sender_name')}: {(chat.get('content') or '')[:200]}")
        else:
            lines.append("聊天记录：（无）")
        files = context.get("files") or []
        if files:
            lines.append("共享文件：" + "、".join(f.get("file_name") or "" for f in files[:10]))
        else:
            lines.append("共享文件：（无）")
        lines.append("转录文本：（无——本次会议没有可用的语音转录，不得编造任何发言内容、发言人或引用；只能依据上述议程、聊天记录和文件总结；没有信息的地方明确写“未提供/未知”，不要猜测）")
        return "\n".join(lines)

    @staticmethod
    def _coerce_priority(value: Any, default: str = "medium") -> str:
        v = str(value or "").strip().lower()
        return v if v in ("low", "medium", "high", "urgent") else default

    @staticmethod
    def _coerce_impact(value: Any, default: str = "medium") -> str:
        v = str(value or "").strip().lower()
        return v if v in ("low", "medium", "high", "critical") else default

    @staticmethod
    def _coerce_importance(value: Any, default: int = 3) -> int:
        try:
            return max(1, min(5, int(value)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _parse_due_date(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            text = str(value).strip()
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _map_llm_summary(self, parsed: Dict[str, Any], meeting_id: int,
                         context: Dict[str, Any], language: str) -> Dict[str, Any]:
        """把 LLM 返回的 JSON 映射成 MeetingSummaryResponse 形状的字典。"""
        meeting = context["meeting"]
        overview = str(parsed.get("overview") or "").strip()
        if not overview:
            overview = (
                f"会议「{meeting['title']}」的摘要：本次会议暂无转录文本，"
                "以下内容依据议程、聊天记录与共享文件生成。"
            )
        key_points = []
        for i, item in enumerate(parsed.get("key_points") or []):
            if isinstance(item, str):
                item = {"title": item, "content": item}
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("content") or "").strip()
            content = str(item.get("content") or title).strip()
            if not title:
                continue
            key_points.append({
                "title": title[:100],
                "content": content,
                "importance": self._coerce_importance(item.get("importance")),
                "timestamp": None,
                "participants": item.get("participants") if isinstance(item.get("participants"), list) else None,
            })
        decisions = []
        for i, item in enumerate(parsed.get("decisions") or []):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("decision") or "").strip()
            if not title:
                continue
            decisions.append({
                "decision_id": f"dec-{i + 1}",
                "title": title[:200],
                "description": str(item.get("description") or title),
                "decision_maker": item.get("decision_maker") or item.get("responsible"),
                "impact_level": self._coerce_impact(item.get("impact_level") or item.get("priority")),
                "implementation_date": self._parse_due_date(item.get("implementation_date") or item.get("deadline")),
                "status": "pending",
                "related_requirements": None,
            })
        action_items = []
        for i, item in enumerate(parsed.get("action_items") or []):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("task") or "").strip()
            if not title:
                continue
            action_items.append({
                "action_id": f"act-{i + 1}",
                "title": title[:200],
                "description": str(item.get("description") or item.get("context") or title),
                "assignee": item.get("assignee"),
                "due_date": self._parse_due_date(item.get("due_date") or item.get("deadline")),
                "priority": self._coerce_priority(item.get("priority")),
                "status": "pending",
                "estimated_hours": item.get("estimated_hours"),
                "dependencies": item.get("dependencies") if isinstance(item.get("dependencies"), list) else None,
            })
        next_steps = [
            str(s).strip() for s in (parsed.get("next_steps") or [])
            if isinstance(s, str) and s.strip()
        ]
        participants = context.get("participants") or []
        joined = [p for p in participants if p.get("attendance_status") in ("JOINED", "LEFT")]
        participants_summary = {
            "total_participants": len(participants),
            "joined_participants": len(joined),
            "participant_names": [p.get("name") for p in participants],
            "transcript_available": False,
        }
        meeting_effectiveness = {
            "participation_rate": (len(joined) / len(participants)) if participants else 0.0,
            "transcript_available": False,
            "note": "无转录文本；效果评估仅基于参会记录，未做内容/情感分析。",
        }
        return {
            "meeting_id": meeting_id,
            "overview": overview,
            "key_points": key_points,
            "decisions": decisions,
            "action_items": action_items,
            "next_steps": next_steps,
            "participants_summary": participants_summary,
            "meeting_effectiveness": meeting_effectiveness,
            "generated_at": datetime.utcnow(),
            "generation_method": "llm",
            "language": language,
            "_llm_model": parsed.get("_llm_model"),
            "_llm_confidence": parsed.get("_llm_confidence", 0.0),
        }

    async def _llm_analyze_meeting(self, meeting_id: int, request: Any = None,
                                   language: str = "zh-CN") -> Dict[str, Any]:
        """一次 LLM 调用完成摘要/要点/决策/行动项/下一步的全部生成。

        prompt 只含真实上下文；转录缺失时明确要求不得编造发言。
        """
        context = await self._build_meeting_context(meeting_id)
        context_text = self._format_context_for_prompt(context)
        focus = ""
        custom = ""
        summary_length = "medium"
        if request is not None and hasattr(request, "focus_areas"):
            if getattr(request, "focus_areas"):
                focus = f"\n重点关注领域：{', '.join(request.focus_areas)}"
            if getattr(request, "custom_prompt", None):
                custom = f"\n用户补充要求：{request.custom_prompt}"
            summary_length = getattr(request, "summary_length", "medium") or "medium"
            language = getattr(request, "language", language) or language
        prompt = (
            "你是会议纪要助手。请只依据以下真实会议上下文生成结构化摘要，"
            "不要编造任何未提供的事实、发言、数字或人名。\n"
            f"摘要长度：{summary_length}。语言：{language}。{focus}{custom}\n\n"
            f"{context_text}\n\n"
            "只返回一个 JSON 对象，不要输出任何其他文字，字段如下：\n"
            '{"overview": "会议概述（2-4 句）", '
            '"key_points": [{"title": "要点标题", "content": "要点内容", "importance": 1-5}], '
            '"decisions": [{"title": "决策标题", "description": "决策描述", "decision_maker": "决策者或 null", "impact_level": "low|medium|high|critical"}], '
            '"action_items": [{"title": "任务标题", "description": "任务描述", "assignee": "负责人姓名或 null", "due_date": "ISO 日期或 null", "priority": "low|medium|high|urgent"}], '
            '"next_steps": ["下一步 1", "下一步 2"]}\n'
            "没有依据的内容用空数组或 null 表示，不要猜测；"
            "无法从上下文得出的决策/行动项不要编造。"
        )
        parsed = await self._call_llm_json(prompt)
        return self._map_llm_summary(parsed, meeting_id, context, language)

    @staticmethod
    def _split_summary_args(request_or_user: Any = None, user_id: Any = None,
                            language: str = "zh-CN"):
        """兼容两种调用形态：路由传 (request, user_id)，旧调用传 (user_id, language)。"""
        request = None
        if request_or_user is not None and hasattr(request_or_user, "model_fields_set"):
            request = request_or_user
            language = getattr(request, "language", language) or language
        elif isinstance(request_or_user, int):
            user_id = request_or_user
        return request, user_id, language

    async def generate_meeting_summary(self, meeting_id: int, request_or_user: Any = None,
                                       user_id: Any = None, language: str = 'zh-CN') -> Dict[str, Any]:
        """生成会议摘要（一次 LLM 调用）并 upsert 到 meeting_summaries 表。

        路由调用形态：generate_meeting_summary(meeting_id, request, user_id)。
        返回 MeetingSummaryResponse 形状的字典。
        """
        request, user_id, language = self._split_summary_args(request_or_user, user_id, language)
        try:
            summary = await self._llm_analyze_meeting(meeting_id, request, language)

            result = await self.db.execute(
                select(MeetingSummaryORM).where(MeetingSummaryORM.meeting_id == meeting_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = MeetingSummaryORM(meeting_id=meeting_id)
                self.db.add(row)
            row.overview = summary["overview"]
            # JSON 列不能直接存 datetime：due_date/implementation_date 先转 ISO 字符串再落库
            persist = json.loads(json.dumps(summary, default=str))
            row.key_points = persist["key_points"]
            row.decisions = persist["decisions"]
            row.action_items = persist["action_items"]
            row.next_steps = persist["next_steps"]
            row.participants_summary = persist["participants_summary"]
            row.meeting_effectiveness = persist["meeting_effectiveness"]
            row.generation_method = "llm"
            row.language = language
            row.model = summary.get("_llm_model")
            try:
                row.confidence_score = float(summary.get("_llm_confidence") or 0)
            except (TypeError, ValueError):
                row.confidence_score = None
            row.transcript_available = False
            row.generated_at = summary["generated_at"]
            row.created_by = user_id if isinstance(user_id, int) else None
            await self.db.commit()

            await self._log_operation(
                user_id=user_id if isinstance(user_id, int) else 0,
                operation_type="SUMMARY_GENERATION",
                operation_result="SUCCESS",
                details={
                    'meeting_id': meeting_id,
                    'language': language,
                    'content_length': len(summary["overview"]),
                    'model': summary.get("_llm_model"),
                }
            )
            summary.pop("_llm_model", None)
            summary.pop("_llm_confidence", None)
            return summary

        except Exception as e:
            logger.error(f"生成会议摘要失败: {str(e)}")
            await self.db.rollback()
            await self._log_operation(
                user_id=user_id if isinstance(user_id, int) else 0,
                operation_type="SUMMARY_GENERATION",
                operation_result="ERROR",
                details={'meeting_id': meeting_id, 'error': str(e)}
            )
            raise
    
    async def extract_action_items(self, meeting_id: int, user_id: int = None,
                                 language: str = 'zh-CN') -> List[ActionItem]:
        """提取行动项目：复用摘要生成的一次 LLM 调用结果映射，不再用罐头。"""
        try:
            summary = await self._llm_analyze_meeting(meeting_id, None, language)
            action_items = []
            for item_data in summary.get("action_items") or []:
                action_items.append(ActionItem(
                    meeting_id=meeting_id,
                    task_description=item_data.get("title", ""),
                    assignee_name=item_data.get("assignee") or "",
                    deadline=item_data.get("due_date"),
                    priority=(item_data.get("priority") or "medium").upper(),
                    context=item_data.get("description", ""),
                    status="PENDING",
                    confidence_score=0.0,
                ))
            await self._log_operation(
                user_id=user_id if isinstance(user_id, int) else 0,
                operation_type="ACTION_ITEMS_EXTRACTION",
                operation_result="SUCCESS",
                details={'meeting_id': meeting_id, 'items_count': len(action_items), 'language': language}
            )
            return action_items
        except Exception as e:
            logger.error(f"提取行动项目失败: {str(e)}")
            await self._log_operation(
                user_id=user_id if isinstance(user_id, int) else 0,
                operation_type="ACTION_ITEMS_EXTRACTION",
                operation_result="ERROR",
                details={'meeting_id': meeting_id, 'error': str(e)}
            )
            raise
    
    async def analyze_meeting_effectiveness(self, meeting_id: int, user_id: int = None) -> EffectivenessAnalysis:
        """
        分析会议效果（全部指标来自真实参会/聊天/文件/议程记录；无转录时
        情感分析明确标 unknown，不编分数）。
        """
        try:
            # 1. 获取会议数据
            meeting = await self._get_meeting_info(meeting_id)
            participants = await self._get_meeting_participants(meeting_id)
            transcripts = await self._get_meeting_transcripts(meeting_id)

            # 2. 参与度分析（逐人真实指标 + 聚合）
            participation_metrics = await self._analyze_participation_metrics(
                participants, transcripts
            )
            participation_summary = await self._analyze_participation_summary(
                participants, transcripts
            )

            # 3. 议程完成度分析
            agenda_completion = await self._analyze_agenda_completion(
                meeting, transcripts
            )

            # 4. 决策效率分析（决策数取已持久化摘要的真实计数）
            decision_efficiency = await self._analyze_decision_efficiency(meeting_id, transcripts)

            # 5. 时间利用率分析
            time_utilization = await self._analyze_time_utilization(
                meeting, transcripts
            )

            # 6. 情感分析（无转录则 unknown）
            sentiment_analysis = await self._analyze_meeting_sentiment(transcripts)

            # 7. 生成改进建议
            improvement_suggestions = await self._generate_improvement_suggestions(
                participation_summary,
                agenda_completion,
                decision_efficiency,
                time_utilization,
                sentiment_analysis
            )

            # 8. 计算总体效果评分
            overall_score = await self._calculate_effectiveness_score(
                participation_summary,
                agenda_completion,
                decision_efficiency,
                time_utilization
            )

            # 9. 聊天/文件真实计数 + 已持久化行动项数
            total_chat_messages = await self._count_meeting_chats(meeting_id)
            total_file_shares = await self._count_meeting_files(meeting_id)
            action_item_count = await self._count_persisted_action_items(meeting_id)

            # 10. 创建分析结果
            analysis = EffectivenessAnalysis(
                meeting_id=meeting_id,
                overall_score=overall_score,
                participation_metrics=participation_metrics,
                participation_summary=participation_summary,
                agenda_completion=agenda_completion,
                decision_efficiency=decision_efficiency,
                time_utilization=time_utilization,
                sentiment_analysis=sentiment_analysis,
                improvement_suggestions=improvement_suggestions,
                analyzed_at=datetime.utcnow(),
                total_chat_messages=total_chat_messages,
                total_file_shares=total_file_shares,
                action_item_count=action_item_count,
            )
            
            # 10. 记录操作日志
            await self._log_operation(
                user_id=user_id,
                operation_type="EFFECTIVENESS_ANALYSIS",
                operation_result="SUCCESS",
                details={
                    'meeting_id': meeting_id,
                    'overall_score': overall_score,
                    'suggestions_count': len(improvement_suggestions)
                }
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析会议效果失败: {str(e)}")
            await self._log_operation(
                user_id=user_id,
                operation_type="EFFECTIVENESS_ANALYSIS",
                operation_result="ERROR",
                details={'meeting_id': meeting_id, 'error': str(e)}
            )
            raise
    
    @staticmethod
    def analytics_to_response_dict(analysis: Union[EffectivenessAnalysis, Dict[str, Any]]) -> Dict[str, Any]:
        """把效果分析统一映射成 MeetingAnalyticsResponse 形状的字典。

        GET /analytics 与 POST /analytics/generate 共用。float 字段无真实
        来源时取 0.0，真实来源/缺失说明一律写进 data_sources，不编数字。
        """
        data = analysis.to_dict() if hasattr(analysis, "to_dict") else dict(analysis)
        agenda = data.get("agenda_completion") or {}
        decision = data.get("decision_efficiency") or {}
        time_util = data.get("time_utilization") or {}
        participation_summary = data.get("participation_summary") or {}
        per_person = data.get("participation_metrics") or []
        if not isinstance(per_person, list):
            per_person = []
        sentiment = data.get("sentiment_analysis") or {}
        return {
            "meeting_id": data.get("meeting_id"),
            "overall_effectiveness": float(data.get("overall_score") or 0.0),
            "participation_metrics": per_person,
            "agenda_completion_rate": float(agenda.get("completion_rate") or 0.0),
            "decision_efficiency": float(decision.get("efficiency_score") or 0.0),
            "time_utilization": float(time_util.get("utilization_rate") or 0.0),
            "sentiment_analysis": sentiment,
            "improvement_suggestions": data.get("improvement_suggestions") or [],
            "meeting_quality_score": float(data.get("overall_score") or 0.0),
            "network_quality_avg": 0.0,
            "technical_issues_count": 0,
            "analyzed_at": data.get("analyzed_at") or datetime.utcnow(),
            "data_sources": {
                "participation": "meeting_participants 真实行（加入/发言时长/互动数）；engagement 由发言与互动占比派生，attention/contribution 暂以 engagement 代理，无独立测量",
                "agenda": "meetings.agenda 真实议程；完成数按议程项 status=completed 统计，无状态则为 0",
                "decisions": "已持久化摘要 decisions 的真实计数；无摘要时为 0",
                "time": "实际起止与计划时长对比；无实际时间记录时为 0（未知，非 0 利用率）",
                "sentiment": "无转录文本，情感分析不可用（overall_sentiment=unknown），未编分数",
                "network_quality_avg": "无采集来源，0.0 表示未知",
                "technical_issues_count": "无故障记录来源，0 表示未记录到故障",
            },
        }

    async def generate_meeting_minutes(self, meeting_id: int, request_or_user: Any = None,
                                     user_id: Any = None, template_type: str = 'standard',
                                     language: str = 'zh-CN') -> MeetingMinutesORM:
        """生成会议纪要：复用摘要生成的一次 LLM 调用，ORM 落库后返回。

        路由调用形态：generate_meeting_minutes(meeting_id, request, user_id)。
        """
        request = None
        if request_or_user is not None and hasattr(request_or_user, "model_fields_set"):
            request = request_or_user
            template_type = getattr(request, "template_type", template_type) or template_type
            language = getattr(request, "language", language) or language
        elif isinstance(request_or_user, int):
            user_id = request_or_user
        try:
            meeting = await self._get_meeting_or_404(meeting_id)

            # 摘要生成（一次 LLM 调用 + 摘要落库）
            summary = await self.generate_meeting_summary(meeting_id, request, user_id, language)

            participants = await self._get_meeting_participants(meeting_id)
            template = await self._get_minutes_template(template_type, language)
            minutes_content = self._generate_structured_minutes(
                {
                    'title': meeting.title,
                    'agenda': meeting.agenda or [],
                },
                summary, participants, template, language,
            )

            minutes = MeetingMinutesORM(
                meeting_id=meeting_id,
                title=f"{meeting.title} - 会议纪要",
                content=minutes_content,
                summary=summary["overview"],
                minute_type=MinuteTypeORM.AI_ENHANCED,
                generation_method=GenerationMethodORM.AI_ANALYSIS,
                agenda_items=self._format_agenda_items(meeting.agenda or []),
                # JSON 列不能直接存 datetime：先转 ISO 字符串再落库
                decisions=json.loads(json.dumps(summary["decisions"], default=str)),
                action_items=json.loads(json.dumps(summary["action_items"], default=str)),
                attendees=[p['name'] for p in participants if p.get('attendance_status') in ('JOINED', 'LEFT')],
                key_points=json.loads(json.dumps(summary["key_points"], default=str)),
                status=MinuteStatusORM.DRAFT,
                created_by=user_id if isinstance(user_id, int) else None,
            )
            self.db.add(minutes)
            await self.db.commit()
            await self.db.refresh(minutes)

            await self._log_operation(
                user_id=user_id if isinstance(user_id, int) else 0,
                operation_type="MINUTES_GENERATION",
                operation_result="SUCCESS",
                details={
                    'meeting_id': meeting_id,
                    'template_type': template_type,
                    'content_length': len(minutes_content),
                    'language': language,
                    'minutes_id': minutes.id,
                }
            )
            return minutes

        except Exception as e:
            logger.error(f"生成会议纪要失败: {str(e)}")
            await self.db.rollback()
            await self._log_operation(
                user_id=user_id if isinstance(user_id, int) else 0,
                operation_type="MINUTES_GENERATION",
                operation_result="ERROR",
                details={'meeting_id': meeting_id, 'template_type': template_type, 'error': str(e)}
            )
            raise

    # 私有辅助方法
    
    async def _get_meeting_info(self, meeting_id: int) -> Dict[str, Any]:
        """从 meetings 表读真实会议信息；不存在则 404。"""
        meeting = await self._get_meeting_or_404(meeting_id)
        return {
            'id': meeting.id,
            'title': meeting.title,
            'description': meeting.description,
            'meeting_type': meeting.meeting_type.value if meeting.meeting_type else None,
            'status': meeting.status.value if meeting.status else None,
            'scheduled_start_time': meeting.scheduled_start_time,
            'scheduled_end_time': meeting.scheduled_end_time,
            'actual_start_time': meeting.actual_start_time,
            'actual_end_time': meeting.actual_end_time,
            'agenda': meeting.agenda or [],
            'duration_minutes': meeting.duration_minutes or 0,
            'project_id': meeting.project_id,
        }

    async def _get_meeting_participants(self, meeting_id: int) -> List[Dict[str, Any]]:
        """从 meeting_participants 表读真实参会行，并取用户昵称/用户名。"""
        result = await self.db.execute(
            select(MeetingParticipantORM, User)
            .outerjoin(User, User.id == MeetingParticipantORM.user_id)
            .where(MeetingParticipantORM.meeting_id == meeting_id)
            .order_by(MeetingParticipantORM.id)
        )
        participants = []
        for row_participant, user in result.all():
            name = None
            if user is not None:
                name = getattr(user, "nickname", None) or getattr(user, "username", None)
            participants.append({
                'user_id': row_participant.user_id,
                'name': name or f"用户{row_participant.user_id}",
                'participant_role': row_participant.participant_role.value if row_participant.participant_role else None,
                'attendance_status': row_participant.attendance_status.value if row_participant.attendance_status else None,
                'join_time': row_participant.join_time.isoformat() if row_participant.join_time else None,
                'leave_time': row_participant.leave_time.isoformat() if row_participant.leave_time else None,
                'total_duration_minutes': row_participant.total_duration_minutes or 0,
                'speak_duration_minutes': row_participant.speak_duration_minutes or 0,
                'interaction_count': row_participant.interaction_count or 0,
            })
        return participants

    async def _get_meeting_chats(self, meeting_id: int) -> List[Dict[str, Any]]:
        """从 meeting_chats 表读真实聊天记录（按时间升序，上限 200 条）。"""
        result = await self.db.execute(
            select(MeetingChatORM, User)
            .outerjoin(User, User.id == MeetingChatORM.sender_id)
            .where(MeetingChatORM.meeting_id == meeting_id)
            .order_by(MeetingChatORM.sent_at)
            .limit(200)
        )
        chats = []
        for chat, user in result.all():
            name = None
            if user is not None:
                name = getattr(user, "nickname", None) or getattr(user, "username", None)
            chats.append({
                'sender_id': chat.sender_id,
                'sender_name': name or f"用户{chat.sender_id}",
                'content': chat.content,
                'sent_at': chat.sent_at.isoformat() if chat.sent_at else None,
            })
        return chats

    async def _get_meeting_files(self, meeting_id: int) -> List[Dict[str, Any]]:
        """从 meeting_files 表读真实共享文件。"""
        result = await self.db.execute(
            select(MeetingFileORM)
            .where(MeetingFileORM.meeting_id == meeting_id)
            .order_by(MeetingFileORM.uploaded_at)
        )
        return [{
            'file_name': f.file_name,
            'file_type': f.file_type,
            'file_size': f.file_size,
            'uploader_id': f.uploader_id,
            'uploaded_at': f.uploaded_at.isoformat() if f.uploaded_at else None,
        } for f in result.scalars().all()]

    async def _count_meeting_chats(self, meeting_id: int) -> int:
        result = await self.db.execute(
            select(func.count(MeetingChatORM.id)).where(MeetingChatORM.meeting_id == meeting_id)
        )
        return int(result.scalar_one() or 0)

    async def _count_meeting_files(self, meeting_id: int) -> int:
        result = await self.db.execute(
            select(func.count(MeetingFileORM.id)).where(MeetingFileORM.meeting_id == meeting_id)
        )
        return int(result.scalar_one() or 0)

    async def _count_persisted_action_items(self, meeting_id: int) -> int:
        """已持久化摘要里的行动项数 + meeting_tasks 关联数（取较大者，去重口径）。"""
        result = await self.db.execute(
            select(MeetingSummaryORM).where(MeetingSummaryORM.meeting_id == meeting_id)
        )
        row = result.scalar_one_or_none()
        summary_count = len(row.action_items or []) if row else 0
        link_result = await self.db.execute(
            select(func.count(MeetingTaskORM.task_id)).where(MeetingTaskORM.meeting_id == meeting_id)
        )
        return max(summary_count, int(link_result.scalar_one() or 0))

    async def _get_meeting_transcripts(self, meeting_id: int) -> List[TranscriptSegment]:
        """获取会议转录数据。

        转录红线：真实转录依赖录制文件 + STT，全链路缺失。返回空列表，
        绝不伪造发言内容；上层按“无转录”诚实处理。
        """
        return []

    def _merge_transcripts(self, transcripts: List[TranscriptSegment]) -> str:
        """合并转录内容"""
        merged_content = []
        for segment in transcripts:
            merged_content.append(f"{segment.speaker_name}: {segment.content}")
        return "\n".join(merged_content)
    
    async def _analyze_participation_metrics(self, participants: List[Dict[str, Any]],
                                           transcripts: List[TranscriptSegment]) -> List[Dict[str, Any]]:
        """逐人参与度指标（真实发言时长/互动数推导）。

        engagement_score 由发言与互动占比派生（1-5 分）；attention_score
        与 contribution_quality 无独立测量来源，暂以 engagement 代理，
        来源说明见 analytics_to_response_dict 的 data_sources。
        """
        total_speak = sum(float(p.get('speak_duration_minutes') or 0) for p in participants)
        total_interactions = sum(int(p.get('interaction_count') or 0) for p in participants)
        metrics = []
        for p in participants:
            speak = float(p.get('speak_duration_minutes') or 0)
            interactions = int(p.get('interaction_count') or 0)
            speak_share = (speak / total_speak) if total_speak > 0 else 0.0
            interaction_share = (interactions / total_interactions) if total_interactions > 0 else 0.0
            engagement = round(1.0 + 4.0 * (0.5 * speak_share + 0.5 * interaction_share), 2)
            if not participants:
                engagement = 0.0
            elif total_speak == 0 and total_interactions == 0:
                engagement = 1.0  # 有参会记录但无发言/互动数据：最低档，非 0 分
            metrics.append({
                "user_id": p.get('user_id'),
                "user_name": p.get('name') or f"用户{p.get('user_id')}",
                "speaking_time_minutes": speak,
                "speaking_percentage": round(speak_share * 100, 2),
                "interaction_count": interactions,
                "engagement_score": engagement,
                "attention_score": engagement,
                "contribution_quality": engagement,
            })
        return metrics

    async def _analyze_participation_summary(self, participants: List[Dict[str, Any]],
                                           transcripts: List[TranscriptSegment]) -> Dict[str, Any]:
        """聚合参与度：加入人数/总人数为真实计数；engagement 为逐人均值。"""
        total = len(participants)
        joined = len([p for p in participants if p.get('attendance_status') in ('JOINED', 'LEFT')])
        active = len([p for p in participants if (p.get('speak_duration_minutes') or 0) > 0 or (p.get('interaction_count') or 0) > 0])
        per_person = await self._analyze_participation_metrics(participants, transcripts)
        engagement = round(sum(m["engagement_score"] for m in per_person) / len(per_person), 2) if per_person else 0.0
        return {
            "total_participants": total,
            "joined_participants": joined,
            "active_participants": active,
            "participation_rate": round(joined / total, 4) if total else 0.0,
            "engagement_score": engagement,
        }

    async def _analyze_participants(self, meeting_id: int,
                                  transcripts: List[TranscriptSegment]) -> Dict[str, Any]:
        """分析参与者表现（真实计数）。"""
        participants = await self._get_meeting_participants(meeting_id)
        total = len(participants)
        active = len([p for p in participants if (p.get('speak_duration_minutes') or 0) > 0])
        avg_speak = round(sum(float(p.get('speak_duration_minutes') or 0) for p in participants) / total, 2) if total else 0.0
        return {
            "total_participants": total,
            "active_speakers": active,
            "average_speak_time": avg_speak,
            "participation_balance": 0.0,
        }

    async def _analyze_agenda_completion(self, meeting: Dict[str, Any],
                                       transcripts: List[TranscriptSegment]) -> Dict[str, Any]:
        """议程完成度：总数取真实议程；完成数按议程项 status=completed 统计。"""
        agenda = meeting.get('agenda') or []
        total = len(agenda)
        completed = 0
        for item in agenda:
            if isinstance(item, dict):
                status = str(item.get('status') or '').lower()
                if status in ('completed', 'done', 'finished'):
                    completed += 1
        return {
            "total_agenda_items": total,
            "completed_items": completed,
            "completion_rate": round(completed / total, 4) if total else 0.0,
            "time_per_item": None,
        }

    async def _analyze_decision_efficiency(self, meeting_id: int,
                                         transcripts: List[TranscriptSegment]) -> Dict[str, Any]:
        """决策效率：决策数取已持久化摘要的真实计数；效率为决策数/议程数的
        粗略代理（无决策耗时记录），无决策时为 0。"""
        result = await self.db.execute(
            select(MeetingSummaryORM).where(MeetingSummaryORM.meeting_id == meeting_id)
        )
        row = result.scalar_one_or_none()
        total_decisions = len(row.decisions or []) if row else 0
        meeting = await self._get_meeting_info(meeting_id)
        total_agenda = len(meeting.get('agenda') or [])
        if total_decisions == 0:
            efficiency = 0.0
        elif total_agenda == 0:
            efficiency = 1.0
        else:
            efficiency = round(min(1.0, total_decisions / total_agenda), 4)
        return {
            "total_decisions": total_decisions,
            "decision_time": None,
            "efficiency_score": efficiency,
        }

    async def _analyze_time_utilization(self, meeting: Dict[str, Any],
                                      transcripts: List[TranscriptSegment]) -> Dict[str, Any]:
        """时间利用率：实际起止与计划时长对比；无实际时间记录时为 0（未知）。"""
        planned = meeting.get('duration_minutes') or 0
        if not planned:
            start, end = meeting.get('scheduled_start_time'), meeting.get('scheduled_end_time')
            if start and end:
                planned = max(0, int((end - start).total_seconds() // 60))
        actual_start, actual_end = meeting.get('actual_start_time'), meeting.get('actual_end_time')
        actual = None
        if actual_start and actual_end:
            actual = max(0, int((actual_end - actual_start).total_seconds() // 60))
        utilization = round(min(1.0, actual / planned), 4) if actual is not None and planned else 0.0
        return {
            "planned_duration": planned,
            "actual_duration": actual,
            "utilization_rate": utilization,
            "productive_time": None,
        }

    async def _analyze_meeting_sentiment(self, transcripts: List[TranscriptSegment]) -> Dict[str, Any]:
        """情感分析：无转录文本则明确标 unknown，不编分数。"""
        if not transcripts:
            return {
                "overall_sentiment": "unknown",
                "sentiment_score": None,
                "positive_ratio": None,
                "negative_ratio": None,
                "neutral_ratio": None,
                "source": "no_transcript",
                "note": "无转录文本，无法做情感分析",
            }
        return {
            "overall_sentiment": "unknown",
            "sentiment_score": None,
            "positive_ratio": None,
            "negative_ratio": None,
            "neutral_ratio": None,
            "source": "transcript",
            "note": "转录情感分析未实现",
        }

    async def _generate_improvement_suggestions(self, participation_metrics: Dict[str, Any],
                                              agenda_completion: Dict[str, Any],
                                              decision_efficiency: Dict[str, Any],
                                              time_utilization: Dict[str, Any],
                                              sentiment_analysis: Dict[str, Any]) -> List[str]:
        """生成改进建议（阈值规则作用于真实算出的比率）。"""
        suggestions = []

        if participation_metrics.get('participation_rate', 0) < 0.8:
            suggestions.append("建议增加互动环节，提高参与者积极性")

        if agenda_completion.get('completion_rate', 0) < 0.8:
            suggestions.append("建议优化议程安排，确保重要议题得到充分讨论")

        if time_utilization.get('utilization_rate', 0) < 0.8:
            suggestions.append("建议加强时间管理，提高会议效率")

        if (sentiment_analysis or {}).get('source') == 'no_transcript':
            suggestions.append("暂无转录数据：建议开启录制转写，以便做内容与情感分析")

        return suggestions

    async def _calculate_effectiveness_score(self, participation_metrics: Dict[str, Any],
                                           agenda_completion: Dict[str, Any],
                                           decision_efficiency: Dict[str, Any],
                                           time_utilization: Dict[str, Any]) -> float:
        """计算会议效果总分：四项真实比率的均值。"""
        scores = [
            participation_metrics.get('participation_rate', 0) or 0,
            agenda_completion.get('completion_rate', 0) or 0,
            decision_efficiency.get('efficiency_score', 0) or 0,
            time_utilization.get('utilization_rate', 0) or 0,
        ]

        return round(sum(scores) / len(scores), 4)
    
    async def _get_minutes_template(self, template_type: str, language: str) -> Dict[str, Any]:
        """获取纪要模板"""
        templates = {
            'standard': {
                'title': '会议纪要',
                'sections': ['会议概述', '主要讨论', '决策事项', '行动计划', '下次会议']
            },
            'project': {
                'title': '项目会议纪要',
                'sections': ['项目状态', '进展汇报', '问题讨论', '决策记录', '后续计划']
            }
        }
        
        return templates.get(template_type, templates['standard'])
    
    def _generate_structured_minutes(self, meeting: Dict[str, Any],
                                     summary: Dict[str, Any],
                                     participants: List[Dict[str, Any]],
                                     template: Dict[str, Any],
                                     language: str) -> str:
        """生成结构化纪要内容（summary 为 MeetingSummaryResponse 形状的字典）。"""
        content_parts = []

        # 会议基本信息
        content_parts.append(f"# {template['title']}")
        content_parts.append(f"**会议主题**: {meeting.get('title', '')}")
        content_parts.append(f"**会议时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        content_parts.append(f"**参会人员**: {', '.join([p['name'] for p in participants])}")
        content_parts.append("**转录来源**: 无转录文本（未录制转写）；本纪要依据议程、聊天记录与共享文件生成")
        content_parts.append("")

        # 会议概述
        content_parts.append("## 会议概述")
        content_parts.append(summary.get("overview") or "")
        content_parts.append("")

        # 主要讨论点
        content_parts.append("## 主要讨论点")
        for i, point in enumerate(summary.get("key_points") or [], 1):
            title = point.get("title", "") if isinstance(point, dict) else str(point)
            content = point.get("content", "") if isinstance(point, dict) else ""
            content_parts.append(f"{i}. {title}" + (f"：{content}" if content and content != title else ""))
        content_parts.append("")

        # 决策事项
        content_parts.append("## 决策事项")
        for i, decision in enumerate(summary.get("decisions") or [], 1):
            content_parts.append(f"{i}. {decision.get('title', '')}")
            if decision.get('description') and decision.get('description') != decision.get('title'):
                content_parts.append(f"   - 说明: {decision.get('description')}")
            if decision.get('decision_maker'):
                content_parts.append(f"   - 决策者: {decision.get('decision_maker')}")
            if decision.get('implementation_date'):
                content_parts.append(f"   - 实施日期: {decision.get('implementation_date')}")
        content_parts.append("")

        # 行动计划
        content_parts.append("## 行动计划")
        for i, action in enumerate(summary.get("action_items") or [], 1):
            content_parts.append(f"{i}. {action.get('title', '')}")
            if action.get('assignee'):
                content_parts.append(f"   - 负责人: {action.get('assignee')}")
            if action.get('due_date'):
                content_parts.append(f"   - 截止时间: {action.get('due_date')}")
        content_parts.append("")

        # 下次会议
        content_parts.append("## 下次会议")
        for step in summary.get("next_steps") or []:
            content_parts.append(f"- {step}")

        return "\n".join(content_parts)

    
    def _format_agenda_items(self, agenda: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化议程项目"""
        formatted_items = []
        for item in agenda:
            formatted_items.append({
                'title': item.get('title', ''),
                'duration': item.get('duration', 0),
                'presenter': item.get('presenter', ''),
                'status': item.get('status', 'pending')
            })
        return formatted_items
    
    # ---- 行动项 CRUD（基于 meeting_tasks + project_tasks）-----------------
    # ActionItem 形状见 schemas/ai_analysis_schemas.py。POST 创建一条
    # project_tasks 行（task_type=DOCUMENTATION，tags 打上
    # meeting_action_item 以便 DELETE 时识别为本会议自有任务）并在
    # meeting_tasks 登记关联；PATCH 改底层任务行；DELETE 删关联，自有
    # 任务连同任务行一起删，非自有（先前由项目集成链接的）任务只解除关联。

    _ACTION_STATUS_TO_TASK = {
        "pending": "TODO",
        "in_progress": "IN_PROGRESS",
        "completed": "COMPLETED",
        "cancelled": "CANCELLED",
    }
    _TASK_TO_ACTION_STATUS = {
        "TODO": "pending",
        "ASSIGNED": "pending",
        "IN_PROGRESS": "in_progress",
        "ON_HOLD": "pending",
        "BLOCKED": "pending",
        "PENDING_REVIEW": "pending",
        "COMPLETED": "completed",
        "CANCELLED": "cancelled",
    }

    async def _user_display_name(self, user_id: Optional[int]) -> Optional[str]:
        if not user_id:
            return None
        user = await self.db.get(User, user_id)
        if user is None:
            return None
        return getattr(user, "nickname", None) or getattr(user, "username", None)

    async def _resolve_assignee(self, data: Dict[str, Any]) -> tuple[Optional[int], Optional[str]]:
        """解析负责人：优先 assignee_id，其次按用户名/昵称查 assignee。"""
        assignee_id = data.get("assignee_id")
        if assignee_id is not None:
            user = await self.db.get(User, int(assignee_id))
            if user is None:
                raise ValidationError(f"指定的负责人不存在: {assignee_id}")
            return user.id, getattr(user, "nickname", None) or getattr(user, "username", None)
        assignee_name = (data.get("assignee") or "").strip() if isinstance(data.get("assignee"), str) else None
        if assignee_name:
            result = await self.db.execute(
                select(User).where(or_(User.username == assignee_name, User.nickname == assignee_name)).limit(1)
            )
            user = result.scalar_one_or_none()
            if user is not None:
                return user.id, getattr(user, "nickname", None) or getattr(user, "username", None)
            return None, assignee_name  # 未注册人名：只做展示，不落 assignee_id
        return None, None

    @staticmethod
    def _parse_action_due_date(value: Any):
        if not value:
            return None
        dt = None
        if isinstance(value, datetime):
            dt = value
        else:
            try:
                dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
            except ValueError:
                return None
        return dt.date()

    def _task_to_action_item(self, task: ProjectTask, assignee_name: Optional[str]) -> Dict[str, Any]:
        due = None
        if task.planned_end_date:
            due = datetime.combine(task.planned_end_date, datetime.min.time())
        dependencies = task.dependency_tasks if isinstance(task.dependency_tasks, list) else None
        return {
            "action_id": str(task.id),
            "title": task.task_name,
            "description": task.description or "",
            "assignee": assignee_name,
            "due_date": due,
            "priority": str(task.priority or "MEDIUM").lower(),
            "status": self._TASK_TO_ACTION_STATUS.get(str(task.status or "TODO"), "pending"),
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours is not None else None,
            "dependencies": [str(d) for d in dependencies] if dependencies else None,
        }

    async def list_action_items(self, meeting_id: int, user_id: int = None) -> List[Dict[str, Any]]:
        await self._get_meeting_or_404(meeting_id)
        result = await self.db.execute(
            select(MeetingTaskORM, ProjectTask)
            .join(ProjectTask, ProjectTask.id == MeetingTaskORM.task_id)
            .where(MeetingTaskORM.meeting_id == meeting_id)
            .order_by(ProjectTask.id)
        )
        items = []
        for _link, task in result.all():
            name = await self._user_display_name(task.assignee_id)
            items.append(self._task_to_action_item(task, name))
        return items

    async def create_action_item(self, meeting_id: int, user_id: int,
                                 data: Dict[str, Any]) -> Dict[str, Any]:
        meeting = await self._get_meeting_or_404(meeting_id)
        if not meeting.project_id:
            raise ValidationError("会议未关联项目，无法创建行动项")
        title = (data.get("title") or "").strip()
        if not title:
            raise ValidationError("行动项标题不能为空")
        assignee_id, assignee_name = await self._resolve_assignee(data)
        priority = str(data.get("priority") or "medium").upper()
        if priority not in ("LOW", "MEDIUM", "HIGH", "URGENT"):
            priority = "MEDIUM"
        status = self._ACTION_STATUS_TO_TASK.get(str(data.get("status") or "pending").lower(), "TODO")
        estimated = data.get("estimated_hours")
        try:
            estimated = float(estimated) if estimated is not None else None
        except (TypeError, ValueError):
            estimated = None
        task = ProjectTask(
            project_id=meeting.project_id,
            task_code=f"ACT-{uuid.uuid4().hex[:8].upper()}",
            task_name=title,
            description=data.get("description"),
            task_type="DOCUMENTATION",
            priority=priority,
            status=status,
            assignee_id=assignee_id,
            reporter_id=user_id if isinstance(user_id, int) else None,
            planned_end_date=self._parse_action_due_date(data.get("due_date")),
            estimated_hours=estimated,
            tags=["meeting_action_item", f"meeting:{meeting_id}"],
            created_by=user_id if isinstance(user_id, int) else 0,
        )
        self.db.add(task)
        await self.db.flush()
        self.db.add(MeetingTaskORM(meeting_id=meeting_id, task_id=task.id,
                                   linked_by=user_id if isinstance(user_id, int) else None))
        await self.db.commit()
        await self.db.refresh(task)
        return self._task_to_action_item(task, assignee_name)

    async def update_action_item(self, meeting_id: int, action_id: str, user_id: int,
                                 data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        await self._get_meeting_or_404(meeting_id)
        try:
            task_id = int(action_id)
        except (TypeError, ValueError):
            return None
        link_result = await self.db.execute(
            select(MeetingTaskORM).where(and_(
                MeetingTaskORM.meeting_id == meeting_id,
                MeetingTaskORM.task_id == task_id,
            ))
        )
        if link_result.scalar_one_or_none() is None:
            return None
        task = await self.db.get(ProjectTask, task_id)
        if task is None:
            return None
        if (data.get("title") or "").strip():
            task.task_name = data["title"].strip()
        if "description" in data:
            task.description = data.get("description")
        if "assignee_id" in data or "assignee" in data:
            assignee_id, _ = await self._resolve_assignee(data)
            task.assignee_id = assignee_id
        if data.get("priority"):
            priority = str(data["priority"]).upper()
            if priority in ("LOW", "MEDIUM", "HIGH", "URGENT"):
                task.priority = priority
        if data.get("status"):
            mapped = self._ACTION_STATUS_TO_TASK.get(str(data["status"]).lower())
            if mapped:
                task.status = mapped
        if "due_date" in data:
            task.planned_end_date = self._parse_action_due_date(data.get("due_date"))
        if "estimated_hours" in data:
            try:
                task.estimated_hours = float(data["estimated_hours"]) if data["estimated_hours"] is not None else None
            except (TypeError, ValueError):
                pass
        await self.db.commit()
        await self.db.refresh(task)
        name = await self._user_display_name(task.assignee_id)
        return self._task_to_action_item(task, name)

    async def delete_action_item(self, meeting_id: int, action_id: str,
                                 user_id: int = None) -> bool:
        await self._get_meeting_or_404(meeting_id)
        try:
            task_id = int(action_id)
        except (TypeError, ValueError):
            return False
        link_result = await self.db.execute(
            select(MeetingTaskORM).where(and_(
                MeetingTaskORM.meeting_id == meeting_id,
                MeetingTaskORM.task_id == task_id,
            ))
        )
        link = link_result.scalar_one_or_none()
        if link is None:
            return False
        task = await self.db.get(ProjectTask, task_id)
        await self.db.delete(link)
        if task is not None and isinstance(task.tags, list) and "meeting_action_item" in task.tags:
            await self.db.delete(task)
        await self.db.commit()
        return True

    # ---- 会议报告生成（聚合真实数据，写文件 + 下载链接）------------------
    @staticmethod
    def meeting_report_dir() -> Path:
        return Path(__file__).resolve().parents[2] / "uploads" / "meeting_reports"

    @staticmethod
    def get_meeting_report_path(report_id: str) -> Optional[Path]:
        """按 report_id 找报告文件；id 非 32 位 hex 直接返回 None（防穿越）。"""
        if not re.fullmatch(r"[0-9a-f]{32}", report_id or ""):
            return None
        candidates = sorted(MeetingAIService.meeting_report_dir().glob(f"*-{report_id}.*"))
        return candidates[0] if candidates else None

    def _render_report_markdown(self, meeting: Dict[str, Any], analytics: Dict[str, Any],
                                summary: Optional[Dict[str, Any]],
                                minutes: List[MeetingMinutesORM],
                                action_items: List[Dict[str, Any]]) -> str:
        lines = [
            f"# 会议分析报告：{meeting.get('title')}",
            "",
            f"- 会议 ID：{meeting.get('id')}；类型：{meeting.get('meeting_type') or '未知'}；状态：{meeting.get('status') or '未知'}",
            f"- 计划时间：{meeting.get('scheduled_start_time') or '未知'} 至 {meeting.get('scheduled_end_time') or '未知'}",
            f"- 生成时间：{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "## 效果分析",
            "",
            f"- 综合评分：{analytics.get('overall_effectiveness')}",
            f"- 议程完成率：{analytics.get('agenda_completion_rate')}",
            f"- 决策效率：{analytics.get('decision_efficiency')}",
            f"- 时间利用率：{analytics.get('time_utilization')}",
            f"- 情感分析：{(analytics.get('sentiment_analysis') or {}).get('overall_sentiment')}（无转录文本时为 unknown，未编分数）",
            "",
        ]
        per_person = analytics.get("participation_metrics") or []
        if per_person:
            lines += ["### 参与度", "", "| 参与者 | 发言时长（分钟） | 发言占比（%） | 互动数 | 参与度评分 |", "| --- | --- | --- | --- | --- |"]
            for p in per_person:
                lines.append(f"| {p.get('user_name')} | {p.get('speaking_time_minutes')} | {p.get('speaking_percentage')} | {p.get('interaction_count')} | {p.get('engagement_score')} |")
            lines.append("")
        suggestions = analytics.get("improvement_suggestions") or []
        if suggestions:
            lines += ["### 改进建议", ""] + [f"- {s}" for s in suggestions] + [""]
        lines += ["## 会议摘要", ""]
        if summary:
            lines += [summary.get("overview") or "", ""]
            for kp in summary.get("key_points") or []:
                lines.append(f"- 关键点：{kp.get('title')}" + (f"：{kp.get('content')}" if kp.get('content') and kp.get('content') != kp.get('title') else ""))
            for d in summary.get("decisions") or []:
                lines.append(f"- 决策：{d.get('title')}")
            for s in summary.get("next_steps") or []:
                lines.append(f"- 下一步：{s}")
            lines.append("")
        else:
            lines += ["暂无已生成的摘要（请先调用 POST /summary/generate）。", ""]
        lines += ["## 会议纪要", ""]
        if minutes:
            for m in minutes:
                lines += [f"### {m.title}（{m.status.value if m.status else ''}，v{m.version}）", "", (m.content or ""), ""]
        else:
            lines += ["暂无纪要（请先调用 POST /minutes/generate）。", ""]
        lines += ["## 行动项", ""]
        if action_items:
            for a in action_items:
                lines.append(f"- {a.get('title')}（负责人：{a.get('assignee') or '未指定'}；优先级：{a.get('priority')}；状态：{a.get('status')}）")
        else:
            lines += ["暂无行动项。"]
        lines += ["", "## 数据来源说明", ""]
        for key, note in (analytics.get("data_sources") or {}).items():
            lines.append(f"- {key}：{note}")
        lines.append("- 摘要/纪要内容由 LLM 依据议程、聊天记录与共享文件生成；无转录文本，未编造发言内容。")
        return "\n".join(lines)

    def _render_report_html(self, markdown_text: str, title: str) -> str:
        import html as html_lib

        body = []
        for line in markdown_text.split("\n"):
            if line.startswith("# "):
                body.append(f"<h1>{html_lib.escape(line[2:])}</h1>")
            elif line.startswith("## "):
                body.append(f"<h2>{html_lib.escape(line[3:])}</h2>")
            elif line.startswith("### "):
                body.append(f"<h3>{html_lib.escape(line[4:])}</h3>")
            elif line.startswith("- "):
                body.append(f"<p>• {html_lib.escape(line[2:])}</p>")
            elif line.startswith("| "):
                body.append(f"<p>{html_lib.escape(line)}</p>")
            elif line.strip():
                body.append(f"<p>{html_lib.escape(line)}</p>")
        return (
            "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            f"<title>{html_lib.escape(title)}</title></head><body>"
            + "\n".join(body) +
            "</body></html>"
        )

    async def generate_meeting_report(self, meeting_id: int, user_id: int = None,
                                      report_type: str = "full",
                                      format: str = "markdown") -> Dict[str, Any]:
        """聚合 analytics + summary + minutes 的真实数据，生成报告文件。"""
        fmt = (format or "markdown").lower()
        if fmt not in ("html", "markdown"):
            raise ValidationError("format 仅支持 html 或 markdown")
        meeting = await self._get_meeting_info(meeting_id)
        analysis = await self.analyze_meeting_effectiveness(meeting_id, user_id)
        analytics = self.analytics_to_response_dict(analysis)
        summary = await self.get_meeting_summary(meeting_id, user_id)
        minutes = await self.get_meeting_minutes(meeting_id, user_id)
        action_items = await self.list_action_items(meeting_id, user_id)
        markdown_text = self._render_report_markdown(meeting, analytics, summary, minutes, action_items)
        if fmt == "html":
            content = self._render_report_html(markdown_text, f"会议分析报告：{meeting.get('title')}")
            ext, media_type = "html", "text/html"
        else:
            content, ext, media_type = markdown_text, "md", "text/markdown"
        report_id = uuid.uuid4().hex
        file_name = f"meeting-{meeting_id}-report-{report_id}.{ext}"
        report_dir = self.meeting_report_dir()
        report_dir.mkdir(parents=True, exist_ok=True)
        file_path = report_dir / file_name
        file_path.write_text(content, encoding="utf-8")
        return {
            "report_id": report_id,
            "meeting_id": meeting_id,
            "report_type": report_type,
            "format": fmt,
            "file_name": file_name,
            "file_size": file_path.stat().st_size,
            "media_type": media_type,
            "download_url": f"/api/v1/meetings/{meeting_id}/analytics/reports/{report_id}/download",
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _log_operation(self, user_id: int, operation_type: str, 
                           operation_result: str, details: Dict[str, Any]):
        """记录操作日志"""
        try:
            # 简化实现，实际应该调用日志服务
            logger.info(f"AI操作日志: 用户{user_id} {operation_type} {operation_result} {details}")
        except Exception as e:
            logger.error(f"记录操作日志失败: {str(e)}")
    
    # 提示词模板方法
    
    def _get_summary_prompt_template(self) -> str:
        """获取摘要生成提示词模板"""
        return """
        请为以下会议生成详细摘要：
        
        会议信息：
        - 标题：{title}
        - 时长：{duration}分钟
        
        会议内容：
        {transcript}
        
        请生成包含以下内容的摘要：
        1. 会议概述
        2. 主要讨论点
        3. 重要决策
        4. 行动项目
        5. 下次会议安排
        """
    
    def _get_decisions_prompt_template(self) -> str:
        """获取决策提取提示词模板"""
        return """
        从以下会议记录中提取所有决策事项：
        
        {transcript}
        
        请以JSON格式返回，包含以下字段：
        - decision: 决策内容
        - responsible: 负责人
        - deadline: 截止日期
        - priority: 优先级
        """
    
    def _get_action_items_prompt_template(self) -> str:
        """获取行动项目提取提示词模板"""
        return """
        从以下会议记录中提取所有行动项目：
        
        {transcript}
        
        请以JSON格式返回，包含以下字段：
        - task: 任务描述
        - assignee: 负责人
        - deadline: 截止日期
        - priority: 优先级
        - context: 相关上下文
        """
    
    def _get_key_points_prompt_template(self) -> str:
        """获取关键要点提取提示词模板"""
        return """
        从以下会议记录中提取关键讨论要点：
        
        {transcript}
        
        请提取最重要的讨论要点，每个要点用一句话概括。
        """
    
    def _get_effectiveness_prompt_template(self) -> str:
        """获取效果分析提示词模板"""
        return """
        分析以下会议的效果和质量：
        
        会议信息：{meeting_info}
        参与者信息：{participants_info}
        会议内容：{transcript}
        
        请从以下维度进行分析：
        1. 参与度
        2. 议程完成度
        3. 决策效率
        4. 时间利用率
        5. 整体效果评分
        """
    
    def _get_sentiment_prompt_template(self) -> str:
        """获取情感分析提示词模板"""
        return """
        分析以下会议内容的情感倾向：
        
        {transcript}
        
        请分析：
        1. 整体情感倾向（积极/消极/中性）
        2. 情感强度评分
        3. 参与者情感状态
        4. 会议氛围评估
        """
    
    def _get_minutes_prompt_template(self) -> str:
        """获取纪要生成提示词模板"""
        return """
        基于以下信息生成正式的会议纪要：
        
        会议摘要：{summary}
        参与者：{participants}
        模板：{template}
        
        请生成结构化的会议纪要，包含完整的格式和内容。
        """


async def get_meeting_ai_service():
    """获取会议AI服务实例（FastAPI 依赖）。

    短生命周期会话：每请求新建一个会话，请求结束回滚并关闭。
    本服务的写方法（摘要/纪要/分析/行动项/报告）内部显式 commit，
    因此请求结束时的回滚不影响已提交的数据。
    """
    from ..core.database import AsyncSessionLocal
    if AsyncSessionLocal is None:
        raise RuntimeError("Async database engine not available")
    async with AsyncSessionLocal() as session:
        yield MeetingAIService(session)
        await session.rollback()


# 简化版本的会议纪要生成函数，用于向后兼容
async def generate_meeting_minutes(meeting_id: int, user_id: int, 
                                 template_type: str = 'standard',
                                 language: str = 'zh-CN') -> MeetingMinutes:
    """
    生成会议纪要 - 简化实现
    
    Args:
        meeting_id: 会议ID
        user_id: 用户ID
        template_type: 纪要模板类型
        language: 语言代码
        
    Returns:
        会议纪要对象
    """
    # 简化实现，返回基本的会议纪要对象
    from datetime import datetime
    return MeetingMinutes(
        meeting_id=meeting_id,
        title=f"会议纪要 - {meeting_id}",
        content="会议纪要内容待生成",
        summary="会议摘要待生成",
        minute_type=MinuteType.STANDARD,
        generation_method=GenerationMethod.AI_GENERATED,
        agenda_items=[],
        decisions=[],
        action_items=[],
        attendees=[],
        key_points=[],
        created_by=user_id,
        created_at=datetime.utcnow()
    )