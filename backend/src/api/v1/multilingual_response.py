"""
多语言响应API端点

提供多语言响应处理的REST API接口，包括：
1. 语言检测
2. 响应适配
3. 用户偏好管理
4. 质量指标查询
5. 反馈提交

API端点：
- POST /api/v1/multilingual/detect-language - 检测语言
- POST /api/v1/multilingual/adapt-response - 适配响应
- GET /api/v1/multilingual/user-preferences - 获取用户偏好
- PUT /api/v1/multilingual/user-preferences - 更新用户偏好
- GET /api/v1/multilingual/supported-languages - 获取支持的语言
- GET /api/v1/multilingual/quality-metrics - 获取质量指标
- POST /api/v1/multilingual/feedback - 提交反馈
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ...core.database import get_async_session
from ...core.auth import get_current_user
from ...services.multilingual_response_service import (
    get_multilingual_response_service,
    MultilingualResponseService,
    SupportedLanguage,
    ResponseType,
    CulturalAdaptation
)
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


# Pydantic模型定义
class LanguageDetectionRequest(BaseModel):
    """语言检测请求"""
    content: str = Field(..., description="待检测的文本内容", min_length=1, max_length=10000)


class LanguageDetectionResponse(BaseModel):
    """语言检测响应"""
    detected_language: str = Field(..., description="检测到的语言代码")
    confidence: float = Field(..., description="检测置信度", ge=0.0, le=1.0)
    mixed_languages: List[str] = Field(default=[], description="混合语言列表")
    language_ratio: Dict[str, float] = Field(default={}, description="各语言占比")
    is_multilingual: bool = Field(default=False, description="是否多语言混合")
    has_code_switching: bool = Field(default=False, description="是否有语码转换")
    dominant_script: str = Field(default="", description="主要文字系统")
    regional_variant: Optional[str] = Field(None, description="地区变体")


class ResponseAdaptationRequest(BaseModel):
    """响应适配请求"""
    content: str = Field(..., description="原始响应内容", min_length=1, max_length=50000)
    target_language: Optional[str] = Field(None, description="目标语言代码")
    context_info: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    force_adaptation: bool = Field(False, description="强制执行适配")


class ResponseAdaptationResponse(BaseModel):
    """响应适配响应"""
    original_content: str = Field(..., description="原始内容")
    adapted_content: str = Field(..., description="适配后内容")
    target_language: str = Field(..., description="目标语言")
    adaptation_applied: List[str] = Field(..., description="应用的适配策略")
    quality_score: float = Field(..., description="质量评分", ge=0.0, le=1.0)
    processing_time: float = Field(..., description="处理时间（秒）")
    cultural_adaptations: List[str] = Field(..., description="文化适配")
    language_enhancements: List[str] = Field(..., description="语言增强")
    formatting_changes: List[str] = Field(..., description="格式化变更")
    fluency_score: float = Field(..., description="流畅度评分", ge=0.0, le=1.0)
    cultural_appropriateness: float = Field(..., description="文化适宜性", ge=0.0, le=1.0)
    technical_accuracy: float = Field(..., description="技术准确性", ge=0.0, le=1.0)
    readability_score: float = Field(..., description="可读性评分", ge=0.0, le=1.0)


class UserLanguagePreferencesResponse(BaseModel):
    """用户语言偏好响应"""
    user_id: int = Field(..., description="用户ID")
    preferred_language: str = Field(..., description="偏好语言")
    formality_level: float = Field(..., description="正式程度", ge=0.0, le=1.0)
    use_honorifics: bool = Field(..., description="使用敬语")
    prefer_formal_tone: bool = Field(..., description="偏好正式语调")
    cultural_adaptation_enabled: bool = Field(..., description="启用文化适配")
    auto_detect_language: bool = Field(..., description="自动检测语言")
    usage_statistics: Dict[str, int] = Field(default={}, description="使用统计")
    last_updated: datetime = Field(..., description="最后更新时间")


class UserLanguagePreferencesUpdate(BaseModel):
    """用户语言偏好更新"""
    preferred_language: Optional[str] = Field(None, description="偏好语言")
    formality_level: Optional[float] = Field(None, description="正式程度", ge=0.0, le=1.0)
    use_honorifics: Optional[bool] = Field(None, description="使用敬语")
    prefer_formal_tone: Optional[bool] = Field(None, description="偏好正式语调")
    cultural_adaptation_enabled: Optional[bool] = Field(None, description="启用文化适配")
    auto_detect_language: Optional[bool] = Field(None, description="自动检测语言")


class SupportedLanguageInfo(BaseModel):
    """支持的语言信息"""
    code: str = Field(..., description="语言代码")
    name: str = Field(..., description="语言英文名称")
    native_name: str = Field(..., description="语言本地名称")
    script_type: str = Field(..., description="文字系统类型")
    cultural_adaptation: str = Field(..., description="文化适配类型")


class QualityMetricsResponse(BaseModel):
    """质量指标响应"""
    total_responses: int = Field(..., description="总响应数")
    average_quality: float = Field(..., description="平均质量分数", ge=0.0, le=1.0)
    quality_distribution: Dict[str, int] = Field(..., description="质量分布")
    language_distribution: Dict[str, int] = Field(..., description="语言分布")
    adaptation_types: Dict[str, int] = Field(..., description="适配类型分布")
    average_processing_time: float = Field(..., description="平均处理时间")


class FeedbackSubmission(BaseModel):
    """反馈提交"""
    response_id: str = Field(..., description="响应ID")
    rating: float = Field(..., description="评分", ge=1.0, le=5.0)
    feedback: Optional[str] = Field(None, description="文本反馈", max_length=1000)


class UsageStatisticsResponse(BaseModel):
    """使用统计响应"""
    language_usage: Dict[str, int] = Field(..., description="语言使用统计")
    total_responses: int = Field(..., description="总响应数")
    cache_status: Dict[str, int] = Field(..., description="缓存状态")
    service_config: Dict[str, Any] = Field(..., description="服务配置")


@router.post("/detect-language", 
            response_model=LanguageDetectionResponse,
            summary="检测文本语言",
            description="检测输入文本的语言类型，支持多语言混合检测")
async def detect_language(
    request: LanguageDetectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """检测文本语言"""
    try:
        logger.info(f"Language detection request from user {current_user.id}")
        
        # 执行语言检测
        detection_result = await multilingual_service.detect_user_language(
            request.content, current_user.id
        )
        
        return LanguageDetectionResponse(
            detected_language=detection_result.detected_language.value,
            confidence=detection_result.confidence,
            mixed_languages=[lang.value for lang in detection_result.mixed_languages],
            language_ratio=detection_result.language_ratio,
            is_multilingual=detection_result.is_multilingual,
            has_code_switching=detection_result.has_code_switching,
            dominant_script=detection_result.dominant_script,
            regional_variant=detection_result.regional_variant
        )
        
    except Exception as e:
        logger.error(f"Error in language detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"语言检测失败: {str(e)}"
        )


@router.post("/adapt-response",
            response_model=ResponseAdaptationResponse,
            summary="适配响应内容",
            description="将AI响应内容适配到用户偏好的语言和文化背景")
async def adapt_response(
    request: ResponseAdaptationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """适配响应内容"""
    try:
        logger.info(f"Response adaptation request from user {current_user.id}")
        
        # 解析目标语言
        force_language = None
        if request.target_language:
            try:
                force_language = SupportedLanguage(request.target_language)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的语言代码: {request.target_language}"
                )
        
        # 执行响应适配
        adaptation_result = await multilingual_service.process_response(
            content=request.content,
            user_id=current_user.id,
            context_info=request.context_info,
            force_language=force_language
        )
        
        return ResponseAdaptationResponse(
            original_content=adaptation_result.original_content,
            adapted_content=adaptation_result.adapted_content,
            target_language=adaptation_result.target_language.value,
            adaptation_applied=adaptation_result.adaptation_applied,
            quality_score=adaptation_result.quality_score,
            processing_time=adaptation_result.processing_time,
            cultural_adaptations=adaptation_result.cultural_adaptations,
            language_enhancements=adaptation_result.language_enhancements,
            formatting_changes=adaptation_result.formatting_changes,
            fluency_score=adaptation_result.fluency_score,
            cultural_appropriateness=adaptation_result.cultural_appropriateness,
            technical_accuracy=adaptation_result.technical_accuracy,
            readability_score=adaptation_result.readability_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in response adaptation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"响应适配失败: {str(e)}"
        )


@router.get("/user-preferences",
           response_model=UserLanguagePreferencesResponse,
           summary="获取用户语言偏好",
           description="获取当前用户的语言偏好设置")
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """获取用户语言偏好"""
    try:
        logger.info(f"Get user preferences request from user {current_user.id}")
        
        preferences = await multilingual_service.get_user_preferences(current_user.id)
        
        return UserLanguagePreferencesResponse(
            user_id=preferences.user_id,
            preferred_language=preferences.preferred_language.value,
            formality_level=preferences.formality_level,
            use_honorifics=preferences.use_honorifics,
            prefer_formal_tone=preferences.prefer_formal_tone,
            cultural_adaptation_enabled=preferences.cultural_adaptation_enabled,
            auto_detect_language=preferences.auto_detect_language,
            usage_statistics=preferences.usage_statistics,
            last_updated=preferences.last_updated
        )
        
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户偏好失败: {str(e)}"
        )


@router.put("/user-preferences",
           response_model=UserLanguagePreferencesResponse,
           summary="更新用户语言偏好",
           description="更新当前用户的语言偏好设置")
async def update_user_preferences(
    request: UserLanguagePreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """更新用户语言偏好"""
    try:
        logger.info(f"Update user preferences request from user {current_user.id}")
        
        # 验证语言代码
        if request.preferred_language:
            try:
                SupportedLanguage(request.preferred_language)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的语言代码: {request.preferred_language}"
                )
        
        # 构建更新数据
        update_data = {}
        for field, value in request.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        # 执行更新
        updated_preferences = await multilingual_service.update_user_preferences(
            current_user.id, update_data
        )
        
        return UserLanguagePreferencesResponse(
            user_id=updated_preferences.user_id,
            preferred_language=updated_preferences.preferred_language.value,
            formality_level=updated_preferences.formality_level,
            use_honorifics=updated_preferences.use_honorifics,
            prefer_formal_tone=updated_preferences.prefer_formal_tone,
            cultural_adaptation_enabled=updated_preferences.cultural_adaptation_enabled,
            auto_detect_language=updated_preferences.auto_detect_language,
            usage_statistics=updated_preferences.usage_statistics,
            last_updated=updated_preferences.last_updated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户偏好失败: {str(e)}"
        )


@router.get("/supported-languages",
           response_model=List[SupportedLanguageInfo],
           summary="获取支持的语言列表",
           description="获取系统支持的所有语言及其详细信息")
async def get_supported_languages(
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """获取支持的语言列表"""
    try:
        logger.info("Get supported languages request")
        
        languages = await multilingual_service.get_supported_languages()
        
        return [
            SupportedLanguageInfo(
                code=lang["code"],
                name=lang["name"],
                native_name=lang["native_name"],
                script_type=lang["script_type"],
                cultural_adaptation=lang["cultural_adaptation"]
            )
            for lang in languages
        ]
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取支持语言列表失败: {str(e)}"
        )


@router.get("/quality-metrics",
           response_model=QualityMetricsResponse,
           summary="获取质量指标",
           description="获取多语言响应的质量统计指标")
async def get_quality_metrics(
    language: Optional[str] = Query(None, description="筛选语言"),
    days: int = Query(7, description="统计天数", ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """获取质量指标"""
    try:
        logger.info(f"Get quality metrics request from user {current_user.id}")
        
        # 验证语言代码
        target_language = None
        if language:
            try:
                target_language = SupportedLanguage(language)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的语言代码: {language}"
                )
        
        # 获取质量指标
        metrics = await multilingual_service.get_quality_metrics(
            user_id=current_user.id,
            language=target_language,
            days=days
        )
        
        return QualityMetricsResponse(
            total_responses=metrics.get("total_responses", 0),
            average_quality=metrics.get("average_quality", 0.0),
            quality_distribution=metrics.get("quality_distribution", {}),
            language_distribution=metrics.get("language_distribution", {}),
            adaptation_types=metrics.get("adaptation_types", {}),
            average_processing_time=metrics.get("average_processing_time", 0.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quality metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取质量指标失败: {str(e)}"
        )


@router.post("/feedback",
            summary="提交用户反馈",
            description="提交对多语言响应质量的用户反馈")
async def submit_feedback(
    request: FeedbackSubmission,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """提交用户反馈"""
    try:
        logger.info(f"Submit feedback request from user {current_user.id}")
        
        await multilingual_service.submit_user_feedback(
            response_id=request.response_id,
            user_id=current_user.id,
            rating=request.rating,
            feedback=request.feedback
        )
        
        return {"message": "反馈提交成功", "response_id": request.response_id}
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交反馈失败: {str(e)}"
        )


@router.get("/usage-statistics",
           response_model=UsageStatisticsResponse,
           summary="获取使用统计",
           description="获取多语言服务的使用统计信息（管理员功能）")
async def get_usage_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """获取使用统计"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        logger.info(f"Get usage statistics request from admin {current_user.id}")
        
        statistics = await multilingual_service.get_usage_statistics()
        
        return UsageStatisticsResponse(
            language_usage=statistics.get("language_usage", {}),
            total_responses=statistics.get("total_responses", 0),
            cache_status=statistics.get("cache_status", {}),
            service_config=statistics.get("service_config", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取使用统计失败: {str(e)}"
        )


@router.put("/service-config",
           summary="更新服务配置",
           description="更新多语言服务配置（管理员功能）")
async def update_service_config(
    config_updates: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    multilingual_service: MultilingualResponseService = Depends(get_multilingual_response_service)
):
    """更新服务配置"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
        
        logger.info(f"Update service config request from admin {current_user.id}")
        
        await multilingual_service.update_service_config(config_updates)
        
        return {"message": "服务配置更新成功", "updated_keys": list(config_updates.keys())}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新服务配置失败: {str(e)}"
        )