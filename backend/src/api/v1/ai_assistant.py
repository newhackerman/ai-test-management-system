"""
AI助手API端点 - 演示依赖注入框架的使用

本模块提供AI助手相关的API端点，展示如何使用依赖注入框架。
"""

import logging
import base64
import io
import json
import math
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
import aiohttp
from fastapi import APIRouter, HTTPException, Request, status, Depends, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ...core.fastapi_integration import Inject, with_services, ServiceProviderDep, ServiceProvider
from ...core.database import get_db
from ...models.user import User
from ...services.ai_assistant_service import AIAssistantService, UserQuery, BusinessContext
from ...services.ai_router_service import AIRouterService
from ...services.conversation_service_sync import ConversationServiceSync, Message, ConversationGroup
from ...models.ai_chat_session import SessionStatus
from ...models.ai_chat_message import MessageRole, ContentType
from ...schemas.conversation import (
    CreateConversationRequest, ConversationResponse, ConversationListResponse,
    UpdateConversationRequest, SendMessageRequest, MessageResponse, MessageListResponse,
    ConversationStatsResponse, SearchConversationsRequest, ConversationContextResponse
)
from ...services.context_manager import ContextWindow

logger = logging.getLogger(__name__)

router = APIRouter()


# 请求/响应模型
class QueryRequest(BaseModel):
    """用户查询请求"""
    content: str = Field(..., description="查询内容", min_length=1, max_length=10000)
    context: Optional[Dict[str, Any]] = Field(None, description="查询上下文")
    conversation_id: Optional[int] = Field(None, description="对话ID")


class QueryResponse(BaseModel):
    """查询响应"""
    success: bool = Field(..., description="是否成功")
    content: str = Field(..., description="AI回答内容")
    provider: str = Field(..., description="使用的AI服务提供商")
    model: str = Field(..., description="使用的AI模型")
    tokens_used: int = Field(..., description="使用的Token数量")
    confidence_score: float = Field(..., description="置信度分数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SuggestionRequest(BaseModel):
    """建议生成请求"""
    project_data: Optional[Dict[str, Any]] = Field(None, description="项目数据")
    requirements_data: Optional[Dict[str, Any]] = Field(None, description="需求数据")
    test_data: Optional[Dict[str, Any]] = Field(None, description="测试数据")
    quality_data: Optional[Dict[str, Any]] = Field(None, description="质量数据")


class SuggestionResponse(BaseModel):
    """建议响应"""
    success: bool = Field(..., description="是否成功")
    suggestions: list = Field(..., description="建议列表")
    total_count: int = Field(..., description="建议总数")


class ServiceHealthResponse(BaseModel):
    """服务健康状态响应"""
    service_name: str = Field(..., description="服务名称")
    is_healthy: bool = Field(..., description="是否健康")
    version: str = Field(..., description="服务版本")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="性能指标")


class AIStatusResponse(BaseModel):
    success: bool
    provider: str
    model: str
    configured: bool
    endpoint: str
    simulated: bool = False
    message: str


class AttachmentExtractItem(BaseModel):
    filename: str
    mime_type: str
    file_size: int
    file_kind: str
    extracted_text: str = ""
    image_data_url: Optional[str] = None
    summary: str = ""
    warnings: List[str] = Field(default_factory=list)


class AttachmentExtractResponse(BaseModel):
    success: bool
    attachments: List[AttachmentExtractItem]


MAX_AI_ATTACHMENT_SIZE = 15 * 1024 * 1024
MAX_AI_IMAGE_INLINE_SIZE = 4 * 1024 * 1024
MAX_EXTRACTED_CHARS_PER_FILE = 6000


def _decode_text_file(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _normalize_extracted_text(value: str, limit: int = MAX_EXTRACTED_CHARS_PER_FILE) -> str:
    text = re.sub(r"\r\n?", "\n", value or "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > limit:
        return f"{text[:limit].rstrip()}\n\n[内容过长，已截取前 {limit} 个字符]"
    return text


def _extract_html_text(content: bytes) -> str:
    raw = _decode_text_file(content)
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text("\n")
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw)


def _extract_pdf_text(content: bytes) -> str:
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(content))
        pages = []
        for index, page in enumerate(reader.pages[:20], start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"[第 {index} 页]\n{page_text}")
        return "\n\n".join(pages)
    except Exception as exc:
        raise ValueError(f"PDF 解析失败: {exc}") from exc


def _extract_docx_text(content: bytes) -> str:
    try:
        from docx import Document

        document = Document(io.BytesIO(content))
        parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception as exc:
        raise ValueError(f"Word 文档解析失败: {exc}") from exc


def _extract_xlsx_text(content: bytes) -> str:
    try:
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        parts = []
        for sheet in workbook.worksheets[:8]:
            parts.append(f"[工作表: {sheet.title}]")
            for row_index, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                if row_index > 120:
                    parts.append("[该工作表内容较多，已截取前 120 行]")
                    break
                values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                if values:
                    parts.append(" | ".join(values))
        return "\n".join(parts)
    except Exception as exc:
        raise ValueError(f"Excel 文档解析失败: {exc}") from exc


def _extract_xls_text(content: bytes) -> str:
    try:
        import pandas as pd

        sheets = pd.read_excel(io.BytesIO(content), sheet_name=None, nrows=120)
        parts = []
        for sheet_name, frame in list(sheets.items())[:8]:
            parts.append(f"[工作表: {sheet_name}]")
            parts.append(frame.fillna("").to_csv(index=False))
        return "\n".join(parts)
    except Exception as exc:
        raise ValueError(f"旧版 Excel 文档解析失败: {exc}") from exc


def _extract_ai_attachment(filename: str, mime_type: str, content: bytes) -> AttachmentExtractItem:
    suffix = f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""
    warnings: List[str] = []
    file_kind = "document"
    extracted_text = ""
    image_data_url: Optional[str] = None

    try:
        if mime_type.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
            file_kind = "image"
            if len(content) <= MAX_AI_IMAGE_INLINE_SIZE:
                image_mime = mime_type or "image/png"
                image_data_url = f"data:{image_mime};base64,{base64.b64encode(content).decode('ascii')}"
                warnings.append("图片将随本次请求发送给支持视觉输入的 OpenAI 兼容模型。")
            else:
                warnings.append("图片超过 4MB，未内联发送给 AI；请压缩后重新上传。")
        elif suffix in {".html", ".htm"} or mime_type == "text/html":
            file_kind = "html"
            extracted_text = _extract_html_text(content)
        elif suffix in {".txt", ".md", ".json", ".xml", ".yaml", ".yml", ".log"} or mime_type.startswith("text/"):
            file_kind = "text"
            extracted_text = _decode_text_file(content)
        elif suffix == ".csv" or mime_type == "text/csv":
            file_kind = "spreadsheet"
            extracted_text = _decode_text_file(content)
        elif suffix == ".pdf" or mime_type == "application/pdf":
            file_kind = "pdf"
            extracted_text = _extract_pdf_text(content)
        elif suffix == ".docx":
            file_kind = "word"
            extracted_text = _extract_docx_text(content)
        elif suffix == ".doc":
            file_kind = "word"
            warnings.append("旧版 .doc 格式暂无法可靠解析，请转为 .docx 后可提取正文。")
        elif suffix == ".xlsx":
            file_kind = "excel"
            extracted_text = _extract_xlsx_text(content)
        elif suffix == ".xls":
            file_kind = "excel"
            extracted_text = _extract_xls_text(content)
        else:
            file_kind = "unknown"
            warnings.append("该文件类型暂不支持正文提取，仅会把文件名、类型、大小作为上下文。")
    except ValueError as exc:
        warnings.append(str(exc))

    extracted_text = _normalize_extracted_text(extracted_text)
    summary = f"{filename}，{file_kind}，{len(content)} 字节"
    if extracted_text:
        summary += f"，已提取 {len(extracted_text)} 个字符"

    return AttachmentExtractItem(
        filename=filename,
        mime_type=mime_type or "application/octet-stream",
        file_size=len(content),
        file_kind=file_kind,
        extracted_text=extracted_text,
        image_data_url=image_data_url,
        summary=summary,
        warnings=warnings,
    )


@router.post("/query", response_model=QueryResponse, summary="AI查询")
async def process_query(
    request: QueryRequest,
    ai_service: AIAssistantService = Inject(AIAssistantService),
    current_user: User = Depends(get_current_user)
):
    """
    处理AI查询请求
    
    使用依赖注入获取AI助手服务，处理用户查询并返回AI回答。
    """
    try:
        logger.info(f"Processing AI query: {request.content[:100]}...")
        
        # 创建用户查询对象
        user_query = UserQuery(
            content=request.content,
            user_id=current_user.id,
            conversation_id=request.conversation_id,
            context=request.context or {}
        )
        
        # 调用AI服务处理查询
        ai_response = await ai_service.process_user_query(user_query, user_id=current_user.id)
        if ai_response.metadata.get("error") or ai_response.model == "error":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ai_response.metadata.get("error") or ai_response.content
            )
        
        # 构建响应
        response = QueryResponse(
            success=True,
            content=ai_response.content,
            provider=ai_response.provider.value,
            model=ai_response.model,
            tokens_used=ai_response.tokens_used,
            confidence_score=ai_response.confidence_score,
            metadata=ai_response.metadata
        )
        
        logger.info(f"AI query processed successfully, tokens used: {ai_response.tokens_used}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing AI query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询处理失败: {str(e)}"
        )


@router.get("/status", response_model=AIStatusResponse, summary="AI 服务状态")
async def get_ai_status(
    ai_service: AIAssistantService = Inject(AIAssistantService),
    current_user: User = Depends(get_current_user)
):
    """返回前端可展示的 AI 调用配置状态，不暴露密钥。"""
    try:
        from ...services.ai_assistant_service import AIProvider

        config = ai_service.ai_configs.get(AIProvider.OPENAI, {})
        model = (config.get("models") or [""])[0] or ""
        endpoint = (config.get("api_endpoint") or "").rstrip("/")
        auth_scheme = str(config.get("auth_scheme") or "bearer").strip().lower()
        configured = bool(config.get("api_key") and endpoint and model)
        message = "AI 服务未完整配置，请检查 API Key、Base URL 和模型名称"

        if configured:
            headers = {}
            if auth_scheme == "raw":
                headers["Authorization"] = config.get("api_key")
            elif auth_scheme == "x-api-key":
                headers["x-api-key"] = config.get("api_key")
            else:
                headers["Authorization"] = f"Bearer {config.get('api_key')}"
            try:
                timeout = aiohttp.ClientTimeout(total=8)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f"{endpoint}/models", headers=headers) as response:
                        response_text = await response.text()
                        if response.status == 401:
                            configured = False
                            message = "AI 服务鉴权失败：API Key 无效或已过期，请更新后端 OPENAI_API_KEY 后重启服务"
                        elif response.status >= 500:
                            message = f"AI 服务地址可访问但状态异常：HTTP {response.status}"
                        elif response.status >= 400:
                            message = f"AI 服务已配置，状态校验返回 HTTP {response.status}：{response_text[:120]}"
                        else:
                            message = "AI 服务已配置并通过鉴权校验"
            except Exception as exc:
                message = f"AI 服务已配置，但状态校验失败：{str(exc)}"

        return AIStatusResponse(
            success=True,
            provider=AIProvider.OPENAI.value,
            model=model,
            configured=configured,
            endpoint=endpoint,
            simulated=False,
            message=message,
        )
    except Exception as e:
        logger.error(f"Error getting AI status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 AI 服务状态失败: {str(e)}"
        )


@router.post("/attachments/extract", response_model=AttachmentExtractResponse, summary="提取 AI 对话附件内容")
async def extract_ai_attachments(
    files: List[UploadFile] = File(..., description="AI 对话附件"),
    current_user: User = Depends(get_current_user)
):
    """解析用户上传的附件，返回可放入 AI 对话上下文的文本内容。"""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请至少上传一个附件")
    if len(files) > 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="一次最多上传 8 个附件")

    attachments: List[AttachmentExtractItem] = []
    for upload in files:
        filename = upload.filename or "未命名附件"
        content = await upload.read()
        if len(content) > MAX_AI_ATTACHMENT_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{filename} 超过 15MB，无法作为 AI 对话附件解析",
            )

        mime_type = upload.content_type or ""
        attachments.append(_extract_ai_attachment(filename, mime_type, content))

    logger.info("Extracted %s AI attachment(s) for user %s", len(attachments), current_user.id)
    return AttachmentExtractResponse(success=True, attachments=attachments)


@router.post("/suggestions", response_model=SuggestionResponse, summary="生成智能建议")
async def generate_suggestions(
    request: SuggestionRequest,
    ai_service: AIAssistantService = Inject(AIAssistantService)
):
    """
    生成智能建议
    
    基于业务上下文生成改进建议。
    """
    try:
        logger.info("Generating intelligent suggestions...")
        
        # 创建业务上下文
        context = BusinessContext(
            project_data=request.project_data,
            requirements_data=request.requirements_data,
            test_data=request.test_data,
            quality_data=request.quality_data
        )
        
        # 生成建议
        suggestions = await ai_service.generate_suggestions(context)
        
        # 转换为响应格式
        suggestion_list = []
        for suggestion in suggestions:
            suggestion_dict = {
                "title": suggestion.title,
                "description": suggestion.description,
                "category": suggestion.category,
                "priority": suggestion.priority,
                "action_items": suggestion.action_items,
                "expected_benefit": suggestion.expected_benefit,
                "estimated_effort": suggestion.estimated_effort,
                "created_at": suggestion.created_at.isoformat()
            }
            suggestion_list.append(suggestion_dict)
        
        response = SuggestionResponse(
            success=True,
            suggestions=suggestion_list,
            total_count=len(suggestion_list)
        )
        
        logger.info(f"Generated {len(suggestions)} suggestions successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"建议生成失败: {str(e)}"
        )


@router.get("/health", response_model=ServiceHealthResponse, summary="服务健康检查")
async def check_service_health(
    service_provider: ServiceProvider = ServiceProviderDep
):
    """
    检查AI助手服务健康状态
    
    演示如何使用ServiceProvider获取服务实例。
    """
    try:
        # 使用ServiceProvider获取AI助手服务
        ai_service = await service_provider.get_service(AIAssistantService)
        
        # 检查服务健康状态
        is_healthy = True
        metrics = {}
        
        if hasattr(ai_service, 'metrics'):
            metrics = ai_service.metrics.copy()
        
        if hasattr(ai_service, 'is_initialized'):
            is_healthy = ai_service.is_initialized
        
        response = ServiceHealthResponse(
            service_name="AIAssistantService",
            is_healthy=is_healthy,
            version=getattr(ai_service, 'service_version', '1.0.0'),
            metrics=metrics
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error checking service health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


@router.get("/services/info", summary="获取服务信息")
async def get_services_info(request: Request):
    """
    获取服务信息
    
    演示如何使用DI容器同时获取多个服务。
    """
    try:
        from ...core.fastapi_integration import get_di_container
        container = get_di_container(request)
        ai_service = await container.get_service_async(AIAssistantService)
        router_service = await container.get_service_async(AIRouterService)
        
        # 收集服务信息
        services_info = {
            "ai_assistant": {
                "name": "AIAssistantService",
                "version": getattr(ai_service, 'service_version', '1.0.0'),
                "initialized": getattr(ai_service, 'is_initialized', False),
                "startup_time": getattr(ai_service, 'startup_time', None),
                "metrics": getattr(ai_service, 'metrics', {})
            },
            "ai_router": {
                "name": "AIRouterService",
                "provider_count": len(getattr(router_service, 'provider_health', {})),
                "available_providers": [
                    provider.value for provider, health in getattr(router_service, 'provider_health', {}).items()
                    if health.is_available
                ]
            }
        }
        
        return {
            "success": True,
            "services": services_info,
            "total_services": len(services_info)
        }
        
    except Exception as e:
        logger.error(f"Error getting services info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取服务信息失败: {str(e)}"
        )


# ==================== 对话管理API ====================

@router.post("/conversations", response_model=ConversationResponse, summary="创建对话")
async def create_conversation(
    request: CreateConversationRequest,
    db: Session = Depends(get_db)
):
    """
    创建新的AI对话会话
    
    支持的模板类型：
    - general: 通用对话
    - code_assistant: 代码助手
    - test_expert: 测试专家
    - document_writer: 文档写作
    - data_analyst: 数据分析
    - creative_design: 创意设计
    - academic_research: 学术研究
    - project_management: 项目管理
    """
    try:
        logger.info(f"Creating conversation with title: {request.title}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 转换分组枚举
        group = ConversationGroup(request.group.value) if request.group else None
        
        conversation = conversation_service.create_conversation(
            user_id=user_id,
            title=request.title,
            ai_provider=request.ai_provider,
            ai_model=request.ai_model,
            system_prompt=request.system_prompt,
            template_type=request.template_type,
            group=group,
            tags=request.tags,
            goal=request.goal
        )
        
        # 解析标签和元数据
        tags = json.loads(conversation.tags) if conversation.tags else []
        session_metadata = json.loads(conversation.session_metadata) if conversation.session_metadata else {}
        
        response = ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            status=conversation.status,
            ai_provider=conversation.ai_provider,
            ai_model=conversation.ai_model,
            system_prompt=conversation.system_prompt,
            message_count=conversation.message_count,
            total_tokens=conversation.total_tokens,
            last_activity_at=conversation.last_activity_at,
            tags=tags,
            session_metadata=session_metadata,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
        logger.info(f"Created conversation {conversation.id} successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建对话失败: {str(e)}"
        )


@router.get("/conversations", response_model=ConversationListResponse, summary="获取对话列表")
async def get_conversations(
    status_filter: Optional[SessionStatus] = None,
    group: Optional[str] = None,
    tags: Optional[str] = None,  # 逗号分隔的标签
    sort_by: str = "last_activity_at",
    sort_order: str = "desc",
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db)
):
    """
    获取用户的对话列表
    
    支持的排序字段：
    - last_activity_at: 最后活动时间
    - created_at: 创建时间
    - title: 标题
    - message_count: 消息数量
    - total_tokens: Token总数
    """
    try:
        logger.info(f"Getting conversations for user, page: {page}, size: {size}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 解析标签
        tag_list = tags.split(',') if tags else None
        
        # 转换分组枚举
        group_enum = ConversationGroup(group) if group else None
        
        conversations, total_count = conversation_service.get_user_conversations(
            user_id=user_id,
            status=status_filter,
            group=group_enum,
            tags=tag_list,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            size=size
        )
        
        # 转换为响应格式
        conversation_responses = []
        for conv in conversations:
            tags = json.loads(conv.tags) if conv.tags else []
            session_metadata = json.loads(conv.session_metadata) if conv.session_metadata else {}
            
            conversation_responses.append(ConversationResponse(
                id=conv.id,
                title=conv.title,
                user_id=conv.user_id,
                status=conv.status,
                ai_provider=conv.ai_provider,
                ai_model=conv.ai_model,
                system_prompt=conv.system_prompt,
                message_count=conv.message_count,
                total_tokens=conv.total_tokens,
                last_activity_at=conv.last_activity_at,
                tags=tags,
                session_metadata=session_metadata,
                created_at=conv.created_at,
                updated_at=conv.updated_at
            ))
        
        total_pages = math.ceil(total_count / size) if total_count > 0 else 0
        
        response = ConversationListResponse(
            success=True,
            conversations=conversation_responses,
            total_count=total_count,
            page=page,
            size=size,
            total_pages=total_pages
        )
        
        logger.info(f"Retrieved {len(conversations)} conversations successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话列表失败: {str(e)}"
        )


@router.get("/conversations/stats", response_model=ConversationStatsResponse, summary="获取对话统计")
async def get_conversation_stats(
    db: Session = Depends(get_db)
):
    """获取用户的对话统计信息"""
    try:
        logger.info("Getting conversation statistics")

        # TODO: 从认证信息获取真实用户ID
        user_id = 1

        conversation_service = ConversationServiceSync(db)
        stats = conversation_service.get_conversation_stats(user_id)

        response = ConversationStatsResponse(
            total_conversations=stats.get('total_conversations', 0),
            active_conversations=stats.get('active_conversations', 0),
            archived_conversations=stats.get('archived_conversations', 0),
            total_messages=stats.get('total_messages', 0),
            total_tokens=stats.get('total_tokens', 0),
            avg_messages_per_conversation=stats.get('avg_messages_per_conversation', 0.0),
            most_used_provider=stats.get('most_used_provider'),
            most_used_model=stats.get('most_used_model')
        )

        logger.info("Retrieved conversation statistics successfully")
        return response

    except Exception as e:
        logger.error(f"Error getting conversation statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话统计失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse, summary="获取对话详情")
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """获取指定对话的详细信息"""
    try:
        logger.info(f"Getting conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 解析标签和元数据
        tags = json.loads(conversation.tags) if conversation.tags else []
        session_metadata = json.loads(conversation.session_metadata) if conversation.session_metadata else {}
        
        response = ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            status=conversation.status,
            ai_provider=conversation.ai_provider,
            ai_model=conversation.ai_model,
            system_prompt=conversation.system_prompt,
            message_count=conversation.message_count,
            total_tokens=conversation.total_tokens,
            last_activity_at=conversation.last_activity_at,
            tags=tags,
            session_metadata=session_metadata,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话详情失败: {str(e)}"
        )


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse, summary="更新对话")
async def update_conversation(
    conversation_id: int,
    request: UpdateConversationRequest,
    db: Session = Depends(get_db)
):
    """更新对话信息"""
    try:
        logger.info(f"Updating conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 准备更新数据
        update_data = {}
        if request.title is not None:
            update_data['title'] = request.title
        if request.ai_provider is not None:
            update_data['ai_provider'] = request.ai_provider
        if request.ai_model is not None:
            update_data['ai_model'] = request.ai_model
        if request.system_prompt is not None:
            update_data['system_prompt'] = request.system_prompt
        if request.tags is not None:
            update_data['tags'] = json.dumps(request.tags)
        if request.status is not None:
            update_data['status'] = request.status
        
        # 添加更新者信息
        update_data['updated_by'] = user_id
        
        success = conversation_service.update_conversation(conversation_id, **update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或更新失败"
            )
        
        # 获取更新后的对话
        updated_conversation = conversation_service.get_conversation(conversation_id, user_id)
        
        # 解析标签和元数据
        tags = json.loads(updated_conversation.tags) if updated_conversation.tags else []
        session_metadata = json.loads(updated_conversation.session_metadata) if updated_conversation.session_metadata else {}
        
        response = ConversationResponse(
            id=updated_conversation.id,
            title=updated_conversation.title,
            user_id=updated_conversation.user_id,
            status=updated_conversation.status,
            ai_provider=updated_conversation.ai_provider,
            ai_model=updated_conversation.ai_model,
            system_prompt=updated_conversation.system_prompt,
            message_count=updated_conversation.message_count,
            total_tokens=updated_conversation.total_tokens,
            last_activity_at=updated_conversation.last_activity_at,
            tags=tags,
            session_metadata=session_metadata,
            created_at=updated_conversation.created_at,
            updated_at=updated_conversation.updated_at
        )
        
        logger.info(f"Updated conversation {conversation_id} successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新对话失败: {str(e)}"
        )


@router.delete("/conversations/{conversation_id}", summary="删除对话")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """删除对话（软删除）"""
    try:
        logger.info(f"Deleting conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        success = conversation_service.delete_conversation(conversation_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或删除失败"
            )
        
        logger.info(f"Deleted conversation {conversation_id} successfully")
        return {"success": True, "message": "对话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除对话失败: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/archive", summary="归档对话")
async def archive_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """归档对话"""
    try:
        logger.info(f"Archiving conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        success = conversation_service.archive_conversation(conversation_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或归档失败"
            )
        
        logger.info(f"Archived conversation {conversation_id} successfully")
        return {"success": True, "message": "对话归档成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"归档对话失败: {str(e)}"
        )


# ==================== 消息管理API ====================

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, summary="发送消息")
async def send_message(
    conversation_id: int,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    ai_service: AIAssistantService = Inject(AIAssistantService)
):
    """
    向对话发送消息并获取AI回复
    
    完整的消息发送和接收流程：
    1. 验证对话存在性和用户权限
    2. 保存用户消息到数据库
    3. 构建对话上下文
    4. 调用AI服务生成回复
    5. 保存AI回复消息
    6. 返回用户消息和AI回复
    """
    try:
        logger.info(f"Sending message to conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 检查对话状态
        if conversation.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法向已删除的对话发送消息"
            )
        
        # 1. 保存用户消息
        user_message = Message(
            role=MessageRole.USER,
            content=request.content,
            content_type=request.content_type,
            metadata=request.metadata or {}
        )
        
        saved_user_message = conversation_service.add_message(
            conversation_id=conversation_id,
            message=user_message
        )
        
        logger.info(f"Saved user message {saved_user_message.id}")
        
        # 2. 构建AI查询上下文
        # 获取最近的对话历史作为上下文
        recent_messages = conversation_service.get_messages(
            conversation_id=conversation_id,
            limit=10  # 获取最近10条消息作为上下文
        )
        
        # 构建对话上下文
        conversation_context = []
        for msg in recent_messages[:-1]:  # 排除刚添加的用户消息
            conversation_context.append({
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            })
        
        # 3. 调用AI服务生成回复
        try:
            user_query = UserQuery(
                content=request.content,
                user_id=user_id,
                conversation_id=conversation_id,
                context={
                    "conversation_history": conversation_context,
                    "conversation_title": conversation.title,
                    "ai_provider": conversation.ai_provider,
                    "ai_model": conversation.ai_model,
                    "system_prompt": conversation.system_prompt,
                    "template_type": json.loads(conversation.session_metadata or '{}').get('template_type'),
                    "user_metadata": request.metadata or {}
                }
            )
            
            logger.info(f"Calling AI service for conversation {conversation_id}")
            ai_response = await ai_service.process_user_query(user_query)
            
            # 记录实际使用情况到成本控制系统
            if hasattr(ai_service, 'ai_router') and hasattr(ai_service.ai_router, 'record_actual_usage'):
                try:
                    from ...services.ai_router_service import AIProvider
                    provider_enum = AIProvider(ai_response.provider.value)
                    
                    # 估算输入和输出token（这里简化处理，实际应该从AI响应中获取）
                    input_tokens = len(request.content) // 4
                    output_tokens = len(ai_response.content) // 4
                    
                    # 估算成本（这里简化处理，实际应该从AI响应中获取）
                    estimated_cost = (input_tokens * 0.001) + (output_tokens * 0.002)
                    
                    await ai_service.ai_router.record_actual_usage(
                        provider=provider_enum,
                        user_id=user_id,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        actual_cost=estimated_cost,
                        response_time=getattr(ai_response, 'response_time', 1.0),
                        success=True
                    )
                    
                    logger.info(f"Recorded usage: {input_tokens} input tokens, {output_tokens} output tokens, ${estimated_cost:.4f}")
                    
                except Exception as usage_error:
                    logger.warning(f"Failed to record usage: {str(usage_error)}")
            
            # 4. 保存AI回复消息
            ai_message = Message(
                role=MessageRole.ASSISTANT,
                content=ai_response.content,
                content_type=ContentType.TEXT,
                metadata={
                    "ai_provider": ai_response.provider.value,
                    "ai_model": ai_response.model,
                    "confidence_score": ai_response.confidence_score,
                    "processing_metadata": ai_response.metadata
                }
            )
            
            saved_ai_message = conversation_service.add_message(
                conversation_id=conversation_id,
                message=ai_message,
                ai_provider=ai_response.provider.value,
                ai_model=ai_response.model,
                tokens_used=ai_response.tokens_used,
                confidence_score=ai_response.confidence_score
            )
            
            logger.info(f"Saved AI response message {saved_ai_message.id}, tokens used: {ai_response.tokens_used}")
            
            # 5. 更新对话的AI配置（如果需要）
            if not conversation.ai_provider:
                conversation_service.update_conversation(
                    conversation_id,
                    ai_provider=ai_response.provider.value,
                    ai_model=ai_response.model
                )
            
        except Exception as ai_error:
            logger.error(f"AI service error for conversation {conversation_id}: {str(ai_error)}")
            
            # 保存错误消息
            error_message = Message(
                role=MessageRole.ASSISTANT,
                content=f"抱歉，AI助手暂时无法回复您的消息。错误信息：{str(ai_error)}",
                content_type=ContentType.TEXT,
                metadata={"error": True, "error_message": str(ai_error)}
            )
            
            saved_ai_message = conversation_service.add_message(
                conversation_id=conversation_id,
                message=error_message,
                ai_provider="error",
                ai_model="error"
            )
            
            # 设置错误标志
            saved_ai_message.is_error = True
            saved_ai_message.error_message = str(ai_error)
        
        # 6. 构建响应 - 返回用户消息（AI回复会通过WebSocket或后续请求获取）
        message_metadata = json.loads(saved_user_message.message_metadata) if saved_user_message.message_metadata else {}
        
        response = MessageResponse(
            id=saved_user_message.id,
            session_id=saved_user_message.session_id,
            role=saved_user_message.role,
            content=saved_user_message.content,
            content_type=saved_user_message.content_type,
            ai_provider=saved_user_message.ai_provider,
            ai_model=saved_user_message.ai_model,
            tokens_used=saved_user_message.tokens_used,
            confidence_score=saved_user_message.confidence_score,
            is_streaming=saved_user_message.is_streaming,
            is_error=saved_user_message.is_error,
            error_message=saved_user_message.error_message,
            message_metadata=message_metadata,
            parent_message_id=saved_user_message.parent_message_id,
            user_rating=saved_user_message.user_rating,
            user_feedback=saved_user_message.user_feedback,
            is_bookmarked=saved_user_message.is_bookmarked,
            created_at=saved_user_message.created_at,
            updated_at=saved_user_message.updated_at
        )
        
        logger.info(f"Successfully processed message for conversation {conversation_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message to conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送消息失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse, summary="获取消息历史")
async def get_messages(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    include_metadata: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取对话的消息历史
    
    返回指定对话的所有消息，包括用户消息和AI回复，按时间顺序排列。
    支持分页查询和元数据控制。
    """
    try:
        logger.info(f"Getting messages for conversation {conversation_id}, limit: {limit}, offset: {offset}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 获取消息
        messages = conversation_service.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
        
        # 获取消息总数（用于分页）
        total_count = conversation_service.get_message_count(conversation_id)
        
        # 转换为响应格式
        message_responses = []
        for msg in messages:
            # 解析元数据
            message_metadata = {}
            if include_metadata and msg.message_metadata:
                try:
                    message_metadata = json.loads(msg.message_metadata)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse metadata for message {msg.id}")
                    message_metadata = {}
            
            message_responses.append(MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                content_type=msg.content_type,
                ai_provider=msg.ai_provider,
                ai_model=msg.ai_model,
                tokens_used=msg.tokens_used or 0,
                confidence_score=msg.confidence_score,
                is_streaming=msg.is_streaming or False,
                is_error=msg.is_error or False,
                error_message=msg.error_message,
                message_metadata=message_metadata if include_metadata else {},
                parent_message_id=msg.parent_message_id,
                user_rating=msg.user_rating,
                user_feedback=msg.user_feedback,
                is_bookmarked=msg.is_bookmarked or False,
                created_at=msg.created_at,
                updated_at=msg.updated_at
            ))
        
        response = MessageListResponse(
            success=True,
            messages=message_responses,
            total_count=total_count,
            conversation_id=conversation_id
        )
        
        logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id} (total: {total_count})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages for conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取消息历史失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/messages/latest", response_model=MessageResponse, summary="获取最新消息")
async def get_latest_message(
    conversation_id: int,
    role: Optional[MessageRole] = None,
    db: Session = Depends(get_db)
):
    """
    获取对话中的最新消息
    
    可以指定角色来获取最新的用户消息或AI回复。
    如果不指定角色，返回最新的任意消息。
    """
    try:
        logger.info(f"Getting latest message for conversation {conversation_id}, role: {role}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 获取最新消息
        latest_message = conversation_service.get_latest_message(conversation_id, role)
        
        if not latest_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到消息"
            )
        
        # 解析元数据
        message_metadata = json.loads(latest_message.message_metadata) if latest_message.message_metadata else {}
        
        response = MessageResponse(
            id=latest_message.id,
            session_id=latest_message.session_id,
            role=latest_message.role,
            content=latest_message.content,
            content_type=latest_message.content_type,
            ai_provider=latest_message.ai_provider,
            ai_model=latest_message.ai_model,
            tokens_used=latest_message.tokens_used or 0,
            confidence_score=latest_message.confidence_score,
            is_streaming=latest_message.is_streaming or False,
            is_error=latest_message.is_error or False,
            error_message=latest_message.error_message,
            message_metadata=message_metadata,
            parent_message_id=latest_message.parent_message_id,
            user_rating=latest_message.user_rating,
            user_feedback=latest_message.user_feedback,
            is_bookmarked=latest_message.is_bookmarked or False,
            created_at=latest_message.created_at,
            updated_at=latest_message.updated_at
        )
        
        logger.info(f"Retrieved latest message {latest_message.id} for conversation {conversation_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest message for conversation {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最新消息失败: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/messages/{message_id}/regenerate", response_model=MessageResponse, summary="重新生成AI回复")
async def regenerate_ai_response(
    conversation_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    ai_service: AIAssistantService = Inject(AIAssistantService)
):
    """
    重新生成AI回复
    
    基于指定的用户消息重新生成AI回复，用于用户不满意当前回复的情况。
    """
    try:
        logger.info(f"Regenerating AI response for message {message_id} in conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 获取原始用户消息
        original_message = conversation_service.get_message_by_id(message_id)
        if not original_message or original_message.session_id != conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="消息不存在"
            )
        
        if original_message.role != MessageRole.USER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能基于用户消息重新生成AI回复"
            )
        
        # 获取对话上下文（到该消息为止）
        context_messages = conversation_service.get_messages_before(conversation_id, message_id)
        
        conversation_context = []
        for msg in context_messages:
            conversation_context.append({
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            })
        
        # 调用AI服务重新生成回复
        user_query = UserQuery(
            content=original_message.content,
            user_id=user_id,
            conversation_id=conversation_id,
            context={
                "conversation_history": conversation_context,
                "conversation_title": conversation.title,
                "ai_provider": conversation.ai_provider,
                "ai_model": conversation.ai_model,
                "system_prompt": conversation.system_prompt,
                "template_type": json.loads(conversation.session_metadata or '{}').get('template_type'),
                "regeneration": True,
                "original_message_id": message_id
            }
        )
        
        ai_response = await ai_service.process_user_query(user_query)
        
        # 保存新的AI回复消息
        ai_message = Message(
            role=MessageRole.ASSISTANT,
            content=ai_response.content,
            content_type=ContentType.TEXT,
            metadata={
                "ai_provider": ai_response.provider.value,
                "ai_model": ai_response.model,
                "confidence_score": ai_response.confidence_score,
                "processing_metadata": ai_response.metadata,
                "regenerated": True,
                "original_message_id": message_id
            }
        )
        
        saved_ai_message = conversation_service.add_message(
            conversation_id=conversation_id,
            message=ai_message,
            ai_provider=ai_response.provider.value,
            ai_model=ai_response.model,
            tokens_used=ai_response.tokens_used,
            confidence_score=ai_response.confidence_score
        )
        
        # 构建响应
        message_metadata = json.loads(saved_ai_message.message_metadata) if saved_ai_message.message_metadata else {}
        
        response = MessageResponse(
            id=saved_ai_message.id,
            session_id=saved_ai_message.session_id,
            role=saved_ai_message.role,
            content=saved_ai_message.content,
            content_type=saved_ai_message.content_type,
            ai_provider=saved_ai_message.ai_provider,
            ai_model=saved_ai_message.ai_model,
            tokens_used=saved_ai_message.tokens_used,
            confidence_score=saved_ai_message.confidence_score,
            is_streaming=saved_ai_message.is_streaming,
            is_error=saved_ai_message.is_error,
            error_message=saved_ai_message.error_message,
            message_metadata=message_metadata,
            parent_message_id=saved_ai_message.parent_message_id,
            user_rating=saved_ai_message.user_rating,
            user_feedback=saved_ai_message.user_feedback,
            is_bookmarked=saved_ai_message.is_bookmarked,
            created_at=saved_ai_message.created_at,
            updated_at=saved_ai_message.updated_at
        )
        
        logger.info(f"Successfully regenerated AI response {saved_ai_message.id} for message {message_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating AI response for message {message_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新生成AI回复失败: {str(e)}"
        )


# ==================== 搜索和统计API ====================

@router.post("/conversations/search", response_model=ConversationListResponse, summary="搜索对话")
async def search_conversations(
    request: SearchConversationsRequest,
    db: Session = Depends(get_db)
):
    """搜索对话"""
    try:
        logger.info(f"Searching conversations with query: {request.query}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        conversations = conversation_service.search_conversations(
            user_id=user_id,
            query=request.query,
            page=request.page,
            size=request.size
        )
        
        # 转换为响应格式
        conversation_responses = []
        for conv in conversations:
            tags = json.loads(conv.tags) if conv.tags else []
            session_metadata = json.loads(conv.session_metadata) if conv.session_metadata else {}
            
            conversation_responses.append(ConversationResponse(
                id=conv.id,
                title=conv.title,
                user_id=conv.user_id,
                status=conv.status,
                ai_provider=conv.ai_provider,
                ai_model=conv.ai_model,
                system_prompt=conv.system_prompt,
                message_count=conv.message_count,
                total_tokens=conv.total_tokens,
                last_activity_at=conv.last_activity_at,
                tags=tags,
                session_metadata=session_metadata,
                created_at=conv.created_at,
                updated_at=conv.updated_at
            ))
        
        total_pages = math.ceil(len(conversations) / request.size) if conversations else 0
        
        response = ConversationListResponse(
            success=True,
            conversations=conversation_responses,
            total_count=len(conversations),
            page=request.page,
            size=request.size,
            total_pages=total_pages
        )
        
        logger.info(f"Found {len(conversations)} conversations matching query")
        return response
        
    except Exception as e:
        logger.error(f"Error searching conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索对话失败: {str(e)}"
        )


@router.get("/container/status", summary="获取依赖注入容器状态")
async def get_container_status(request: Request):
    """
    获取依赖注入容器状态
    
    演示如何直接访问依赖注入容器。
    """
    try:
        from ...core.fastapi_integration import get_di_container
        from ...core.service_registry import get_service_registry
        
        # 获取容器和注册表
        container = get_di_container(request)
        registry = get_service_registry()
        
        # 收集容器状态信息
        registered_services = container.get_registered_services()
        services_info = registry.get_all_services_info()
        
        container_status = {
            "container_type": type(container).__name__,
            "registered_services_count": len(registered_services),
            "registered_services": [service.__name__ for service in registered_services],
            "services_details": services_info,
            "scope_id": getattr(request.state, 'di_scope_id', None)
        }
        
        return {
            "success": True,
            "container_status": container_status
        }
        
    except Exception as e:
        logger.error(f"Error getting container status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取容器状态失败: {str(e)}"
        )


# ==================== 上下文管理API ====================

@router.get("/conversations/{conversation_id}/context", response_model=ConversationContextResponse, summary="获取对话上下文")
async def get_conversation_context(
    conversation_id: int,
    ai_model: Optional[str] = None,
    max_messages: Optional[int] = None,
    include_system_prompt: bool = True,
    db: Session = Depends(get_db)
):
    """
    获取对话的上下文信息
    
    返回格式化的对话上下文，包括消息列表、摘要、统计信息等。
    支持针对不同AI模型优化上下文格式。
    """
    try:
        logger.info(f"Getting context for conversation {conversation_id}, model: {ai_model}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 获取上下文窗口
        context_window = conversation_service.get_conversation_context(
            conversation_id=conversation_id,
            ai_model=ai_model,
            max_messages=max_messages,
            include_system_prompt=include_system_prompt
        )
        
        if not context_window:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="无法获取对话上下文"
            )
        
        # 转换消息格式
        context_messages = []
        for msg in context_window.messages:
            message_metadata = msg.metadata or {}
            
            context_messages.append(MessageResponse(
                id=msg.id,
                session_id=conversation_id,
                role=msg.role,
                content=msg.content,
                content_type=msg.content_type,
                ai_provider=message_metadata.get("ai_provider"),
                ai_model=message_metadata.get("ai_model"),
                tokens_used=msg.tokens,
                confidence_score=message_metadata.get("confidence_score"),
                is_streaming=False,
                is_error=False,
                error_message=None,
                message_metadata=message_metadata,
                parent_message_id=None,
                user_rating=None,
                user_feedback=None,
                is_bookmarked=msg.is_bookmarked,
                created_at=msg.timestamp,
                updated_at=None
            ))
        
        # 获取摘要和统计信息
        summary = conversation_service.get_context_summary(conversation_id)
        stats = conversation_service.get_context_statistics(conversation_id)
        
        # 构建响应
        response = ConversationContextResponse(
            conversation_id=conversation_id,
            messages=context_messages,
            summary=summary,
            business_context=None,  # TODO: 实现业务上下文
            user_preferences=None,  # TODO: 实现用户偏好
            token_count=context_window.total_tokens,
            compression_strategy=context_window.compression_strategy.value if context_window.compression_strategy else None
        )
        
        logger.info(f"Retrieved context for conversation {conversation_id}: {len(context_messages)} messages, {context_window.total_tokens} tokens")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation context {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话上下文失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/context/summary", summary="获取对话摘要")
async def get_context_summary(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """获取对话的上下文摘要"""
    try:
        logger.info(f"Getting context summary for conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 获取摘要
        summary = conversation_service.get_context_summary(conversation_id)
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "summary": summary,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting context summary {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话摘要失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/context/stats", summary="获取上下文统计")
async def get_context_stats(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """获取对话的上下文统计信息"""
    try:
        logger.info(f"Getting context stats for conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 获取统计信息
        stats = conversation_service.get_context_statistics(conversation_id)
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "statistics": stats,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting context stats {conversation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上下文统计失败: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/messages/{message_id}/mark-important", summary="标记重要消息")
async def mark_message_important(
    conversation_id: int,
    message_id: int,
    db: Session = Depends(get_db)
):
    """标记消息为重要，影响上下文优先级"""
    try:
        logger.info(f"Marking message {message_id} as important in conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 验证消息存在且属于该对话
        message = conversation_service.get_message_by_id(message_id)
        if not message or message.session_id != conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="消息不存在或不属于该对话"
            )
        
        # 标记消息为重要
        success = conversation_service.mark_message_important(message_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="标记消息失败"
            )
        
        logger.info(f"Successfully marked message {message_id} as important")
        return {
            "success": True,
            "message": "消息已标记为重要",
            "message_id": message_id,
            "conversation_id": conversation_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking message as important: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"标记消息失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/context/formatted", summary="获取格式化上下文")
async def get_formatted_context(
    conversation_id: int,
    ai_model: str,
    db: Session = Depends(get_db)
):
    """获取为特定AI模型格式化的上下文"""
    try:
        logger.info(f"Getting formatted context for conversation {conversation_id}, model: {ai_model}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 获取格式化的上下文
        formatted_context = conversation_service.format_context_for_ai(conversation_id, ai_model)
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "ai_model": ai_model,
            "formatted_context": formatted_context,
            "message_count": len(formatted_context),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting formatted context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取格式化上下文失败: {str(e)}"
        )


@router.post("/conversations/{conversation_id}/context/preload", summary="预加载上下文缓存")
async def preload_context_cache(
    conversation_id: int,
    ai_models: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """预加载对话上下文到缓存"""
    try:
        logger.info(f"Preloading context cache for conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 预加载缓存
        success = conversation_service.preload_context_cache(conversation_id, ai_models)
        
        return {
            "success": success,
            "conversation_id": conversation_id,
            "ai_models": ai_models,
            "message": "上下文缓存预加载完成" if success else "上下文缓存预加载失败"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preloading context cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预加载上下文缓存失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/context/cache-info", summary="获取缓存信息")
async def get_context_cache_info(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """获取对话的上下文缓存信息"""
    try:
        logger.info(f"Getting cache info for conversation {conversation_id}")
        
        # TODO: 从认证信息获取真实用户ID
        user_id = 1
        
        conversation_service = ConversationServiceSync(db)
        
        # 验证对话存在且用户有权限
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或无访问权限"
            )
        
        # 获取缓存信息
        cache_info = conversation_service.get_cache_info(conversation_id)
        
        return {
            "success": True,
            "cache_info": cache_info,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取缓存信息失败: {str(e)}"
        )
