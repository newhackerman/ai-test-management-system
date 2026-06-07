"""
AI分析和纪要API路由

本模块提供会议AI分析和纪要生成的REST API接口，包括：
- POST /meetings/{meeting_id}/summary/generate 生成会议摘要接口
- GET /meetings/{meeting_id}/summary 获取会议摘要接口
- POST /meetings/{meeting_id}/minutes/generate 生成会议纪要接口
- GET /meetings/{meeting_id}/minutes 获取会议纪要接口
- GET /meetings/{meeting_id}/analytics 获取会议分析接口
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_async_session
from ....core.exceptions import ValidationError, NotFoundError, PermissionError
from ....services.meeting_ai_service import MeetingAIService, get_meeting_ai_service
from ....services.meeting_service import MeetingService, get_meeting_service
from ....api.auth import get_current_user
from ....models.user import User
from ....schemas.ai_analysis_schemas import (
    GenerateSummaryRequest, GenerateSummaryResponse, MeetingSummaryResponse,
    GenerateMinutesRequest, GenerateMinutesResponse, MeetingMinutesResponse,
    MeetingAnalyticsResponse, GetAnalyticsResponse, TranscriptionResponse,
    AdvancedAnalyticsResponse, MinuteTypeEnum, GenerationMethodEnum, MinuteStatusEnum
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/summary/generate",
    response_model=GenerateSummaryResponse,
    summary="生成会议摘要",
    description="使用AI技术生成会议摘要"
)
async def generate_meeting_summary(
    meeting_id: int = Path(..., description="会议ID"),
    request: GenerateSummaryRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    ai_service: MeetingAIService = Depends(get_meeting_ai_service)
):
    """
    生成会议摘要
    
    - **meeting_id**: 会议ID（必填）
    - **include_transcript**: 是否包含转录内容（默认true）
    - **include_chat**: 是否包含聊天记录（默认true）
    - **include_files**: 是否包含文件信息（默认false）
    - **summary_length**: 摘要长度（short/medium/long/detailed，默认medium）
    - **language**: 摘要语言（默认zh-CN）
    - **focus_areas**: 重点关注领域（可选）
    - **custom_prompt**: 自定义提示词（可选）
    
    使用AI技术分析会议内容，生成结构化摘要
    """
    try:
        logger.info(f"用户 {current_user.id} 生成会议摘要: 会议 {meeting_id}")
        
        # 生成会议摘要
        summary = await ai_service.generate_meeting_summary(meeting_id, request, current_user.id)
        
        logger.info(f"会议摘要生成成功: 会议 {meeting_id}")
        
        return GenerateSummaryResponse(
            success=True,
            message="会议摘要生成成功",
            data=MeetingSummaryResponse(**summary)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"生成会议摘要验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"生成会议摘要权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"生成会议摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成会议摘要失败"
        )


@router.get(
    "/summary",
    response_model=MeetingSummaryResponse,
    summary="获取会议摘要",
    description="获取已生成的会议摘要"
)
async def get_meeting_summary(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    ai_service: MeetingAIService = Depends(get_meeting_ai_service)
):
    """
    获取会议摘要
    
    - **meeting_id**: 会议ID（必填）
    
    返回已生成的会议摘要，如果不存在则返回404
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议摘要: 会议 {meeting_id}")
        
        # 获取会议摘要
        summary = await ai_service.get_meeting_summary(meeting_id, current_user.id)
        
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会议摘要不存在，请先生成摘要"
            )
        
        return MeetingSummaryResponse(**summary)
        
    except NotFoundError as e:
        logger.warning(f"会议或摘要不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取会议摘要权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取会议摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会议摘要失败"
        )


@router.post(
    "/minutes/generate",
    response_model=GenerateMinutesResponse,
    summary="生成会议纪要",
    description="使用AI技术生成结构化会议纪要"
)
async def generate_meeting_minutes(
    meeting_id: int = Path(..., description="会议ID"),
    request: GenerateMinutesRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    ai_service: MeetingAIService = Depends(get_meeting_ai_service)
):
    """
    生成会议纪要
    
    - **meeting_id**: 会议ID（必填）
    - **template_type**: 纪要模板类型（默认standard）
    - **include_summary**: 是否包含摘要（默认true）
    - **include_transcript**: 是否包含完整转录（默认false）
    - **include_attachments**: 是否包含附件信息（默认true）
    - **format_style**: 格式风格（formal/casual/technical，默认formal）
    - **language**: 纪要语言（默认zh-CN）
    - **auto_structure**: 是否自动结构化（默认true）
    - **custom_sections**: 自定义章节（可选）
    
    生成结构化的会议纪要，包含议程、决策、行动项等
    """
    try:
        logger.info(f"用户 {current_user.id} 生成会议纪要: 会议 {meeting_id}")
        
        # 生成会议纪要
        minutes = await ai_service.generate_meeting_minutes(meeting_id, request, current_user.id)
        
        logger.info(f"会议纪要生成成功: 会议 {meeting_id}, 纪要ID {minutes.id}")
        
        return GenerateMinutesResponse(
            success=True,
            message="会议纪要生成成功",
            data=MeetingMinutesResponse.from_orm(minutes)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"生成会议纪要验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"生成会议纪要权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"生成会议纪要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成会议纪要失败"
        )


@router.get(
    "/minutes",
    response_model=List[MeetingMinutesResponse],
    summary="获取会议纪要",
    description="获取会议的纪要列表"
)
async def get_meeting_minutes(
    meeting_id: int = Path(..., description="会议ID"),
    status: Optional[MinuteStatusEnum] = Query(None, description="纪要状态筛选"),
    minute_type: Optional[MinuteTypeEnum] = Query(None, description="纪要类型筛选"),
    version: Optional[str] = Query(None, description="版本筛选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    ai_service: MeetingAIService = Depends(get_meeting_ai_service)
):
    """
    获取会议纪要
    
    - **meeting_id**: 会议ID（必填）
    - **status**: 纪要状态筛选（可选）
    - **minute_type**: 纪要类型筛选（可选）
    - **version**: 版本筛选（可选）
    
    返回会议的纪要列表，支持多版本纪要
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议纪要: 会议 {meeting_id}")
        
        # 获取会议纪要
        minutes_list = await ai_service.get_meeting_minutes(
            meeting_id, 
            current_user.id,
            status=status,
            minute_type=minute_type,
            version=version
        )
        
        return [MeetingMinutesResponse.from_orm(minutes) for minutes in minutes_list]
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取会议纪要权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取会议纪要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会议纪要失败"
        )


@router.get(
    "/analytics",
    response_model=GetAnalyticsResponse,
    summary="获取会议分析",
    description="获取会议的AI分析结果"
)
async def get_meeting_analytics(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    ai_service: MeetingAIService = Depends(get_meeting_ai_service)
):
    """
    获取会议分析
    
    - **meeting_id**: 会议ID（必填）
    
    返回会议的AI分析结果，包括参与度、效率、质量等指标
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议分析: 会议 {meeting_id}")
        
        # 获取会议分析
        analytics = await ai_service.analyze_meeting_effectiveness(meeting_id, current_user.id)
        
        return GetAnalyticsResponse(
            success=True,
            message="会议分析获取成功",
            data=MeetingAnalyticsResponse(**analytics)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取会议分析权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取会议分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会议分析失败"
        )


@router.post(
    "/analytics/generate",
    response_model=GetAnalyticsResponse,
    summary="生成会议分析",
    description="重新生成会议的AI分析结果"
)
async def generate_meeting_analytics(
    meeting_id: int = Path(..., description="会议ID"),
    force_regenerate: bool = Query(False, description="是否强制重新生成"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    ai_service: MeetingAIService = Depends(get_meeting_ai_service)
):
    """
    生成会议分析
    
    - **meeting_id**: 会议ID（必填）
    - **force_regenerate**: 是否强制重新生成（默认false）
    
    生成或更新会议的AI分析结果
    """
    try:
        logger.info(f"用户 {current_user.id} 生成会议分析: 会议 {meeting_id}")
        
        # 生成会议分析
        analytics = await ai_service.generate_meeting_analytics(
            meeting_id, 
            current_user.id,
            force_regenerate=force_regenerate
        )
        
        logger.info(f"会议分析生成成功: 会议 {meeting_id}")
        
        return GetAnalyticsResponse(
            success=True,
            message="会议分析生成成功",
            data=MeetingAnalyticsResponse(**analytics)
        )
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"生成会议分析验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"生成会议分析权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"生成会议分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成会议分析失败"
        )


@router.get(
    "/transcription",
    response_model=TranscriptionResponse,
    summary="获取会议转录",
    description="获取会议的语音转录结果"
)
async def get_meeting_transcription(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    ai_service: MeetingAIService = Depends(get_meeting_ai_service)
):
    """
    获取会议转录
    
    - **meeting_id**: 会议ID（必填）
    
    返回会议的语音转录结果，包含时间轴和发言人信息
    """
    try:
        logger.info(f"用户 {current_user.id} 获取会议转录: 会议 {meeting_id}")
        
        # 获取会议转录
        transcription = await ai_service.get_meeting_transcription(meeting_id, current_user.id)
        
        if not transcription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会议转录不存在，请确认会议已录制并处理完成"
            )
        
        return TranscriptionResponse(**transcription)
        
    except NotFoundError as e:
        logger.warning(f"会议或转录不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取会议转录权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取会议转录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会议转录失败"
        )


@router.get(
    "/advanced-analytics",
    response_model=AdvancedAnalyticsResponse,
    summary="获取高级分析",
    description="获取会议的高级AI分析结果"
)
async def get_advanced_analytics(
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    ai_service: MeetingAIService = Depends(get_meeting_ai_service)
):
    """
    获取高级分析
    
    - **meeting_id**: 会议ID（必填）
    
    返回会议的高级AI分析结果，包括情感分析、主题分析、发言人洞察等
    """
    try:
        logger.info(f"用户 {current_user.id} 获取高级分析: 会议 {meeting_id}")
        
        # 获取高级分析
        advanced_analytics = await ai_service.get_advanced_analytics(meeting_id, current_user.id)
        
        return AdvancedAnalyticsResponse(**advanced_analytics)
        
    except NotFoundError as e:
        logger.warning(f"会议不存在: {meeting_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取高级分析权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取高级分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取高级分析失败"
        )