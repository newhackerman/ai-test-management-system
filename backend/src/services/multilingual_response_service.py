"""
多语言响应服务

本模块提供AI助手的多语言响应处理服务，包括：
1. 与AI助手服务的集成
2. 自动语言检测和适配
3. 响应质量监控和优化
4. 多语言配置管理
5. 用户偏好学习和应用

主要功能：
- 智能语言检测
- 自动响应适配
- 质量评估和优化
- 用户偏好管理
- 统计和分析
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from .multilingual_response_handler import (
    MultilingualResponseHandler,
    SupportedLanguage,
    ResponseType,
    CulturalAdaptation,
    LanguageDetectionResult,
    ResponseAdaptationConfig,
    MultilingualResponse
)

logger = logging.getLogger(__name__)


@dataclass
class UserLanguagePreference:
    """用户语言偏好"""
    user_id: int
    preferred_language: SupportedLanguage
    formality_level: float = 0.5
    use_honorifics: bool = False
    prefer_formal_tone: bool = False
    cultural_adaptation_enabled: bool = True
    auto_detect_language: bool = True
    
    # 学习到的偏好
    detected_patterns: Dict[str, Any] = None
    usage_statistics: Dict[str, int] = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.detected_patterns is None:
            self.detected_patterns = {}
        if self.usage_statistics is None:
            self.usage_statistics = {}
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()


@dataclass
class ResponseQualityMetrics:
    """响应质量指标"""
    response_id: str
    user_id: int
    original_language: SupportedLanguage
    target_language: SupportedLanguage
    adaptation_applied: List[str]
    
    # 质量分数
    overall_quality: float
    fluency_score: float
    cultural_appropriateness: float
    technical_accuracy: float
    readability_score: float
    
    # 用户反馈
    user_rating: Optional[float] = None
    user_feedback: Optional[str] = None
    
    # 性能指标
    processing_time: float = 0.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class MultilingualResponseService:
    """多语言响应服务"""
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # 初始化多语言处理器
        self.handler = MultilingualResponseHandler()
        
        # 用户偏好缓存
        self.user_preferences_cache: Dict[int, UserLanguagePreference] = {}
        self.cache_ttl = timedelta(hours=1)
        self.cache_timestamps: Dict[int, datetime] = {}
        
        # 质量指标缓存
        self.quality_metrics: List[ResponseQualityMetrics] = []
        self.max_metrics_cache = 1000
        
        # 语言使用统计
        self.language_usage_stats: Dict[str, int] = {}
        
        # 配置
        self.config = {
            "auto_adaptation_enabled": True,
            "quality_threshold": 0.7,
            "learning_enabled": True,
            "feedback_collection_enabled": True,
            "performance_monitoring_enabled": True
        }
        
        self.logger.info("Multilingual response service initialized")
    
    async def process_response(self, 
                             content: str,
                             user_id: int,
                             context_info: Optional[Dict[str, Any]] = None,
                             force_language: Optional[SupportedLanguage] = None) -> MultilingualResponse:
        """
        处理AI响应的多语言适配
        
        Args:
            content: AI响应内容
            user_id: 用户ID
            context_info: 上下文信息
            force_language: 强制指定目标语言
            
        Returns:
            MultilingualResponse: 处理后的多语言响应
        """
        try:
            self.logger.info(f"Processing multilingual response for user {user_id}")
            
            # 1. 获取用户语言偏好
            user_preferences = await self.get_user_preferences(user_id)
            
            # 2. 确定目标语言
            target_language = force_language or user_preferences.preferred_language
            
            # 3. 检测原始内容语言
            detection_result = await self.handler.detect_language(content)
            
            # 4. 如果目标语言与检测语言相同且质量良好，直接返回
            if (target_language == detection_result.detected_language and 
                detection_result.confidence > 0.8 and 
                not self._needs_cultural_adaptation(content, user_preferences)):
                
                return MultilingualResponse(
                    original_content=content,
                    adapted_content=content,
                    target_language=target_language,
                    adaptation_applied=["no_adaptation_needed"],
                    quality_score=0.9,
                    processing_time=0.0,
                    cultural_adaptations=[],
                    language_enhancements=[],
                    formatting_changes=[]
                )
            
            # 5. 创建适配配置
            adaptation_config = await self._create_adaptation_config(
                target_language, user_preferences, context_info
            )
            
            # 6. 执行多语言适配
            multilingual_response = await self.handler.adapt_response(content, adaptation_config)
            
            # 7. 质量检查和优化
            if multilingual_response.quality_score < self.config["quality_threshold"]:
                multilingual_response = await self._optimize_response(
                    multilingual_response, adaptation_config
                )
            
            # 8. 记录质量指标
            await self._record_quality_metrics(
                multilingual_response, user_id, detection_result, target_language
            )
            
            # 9. 更新用户偏好学习
            if self.config["learning_enabled"]:
                await self._update_user_learning(user_id, multilingual_response, context_info)
            
            # 10. 更新使用统计
            self._update_usage_statistics(target_language, detection_result)
            
            self.logger.info(
                f"Multilingual response processed successfully, "
                f"quality score: {multilingual_response.quality_score:.2f}"
            )
            
            return multilingual_response
            
        except Exception as e:
            self.logger.error(f"Error processing multilingual response: {e}")
            
            # 返回原始内容作为fallback
            return MultilingualResponse(
                original_content=content,
                adapted_content=content,
                target_language=SupportedLanguage.ENGLISH,
                adaptation_applied=["error_fallback"],
                quality_score=0.5,
                processing_time=0.0,
                cultural_adaptations=[],
                language_enhancements=[],
                formatting_changes=[]
            )
    
    async def get_user_preferences(self, user_id: int) -> UserLanguagePreference:
        """获取用户语言偏好"""
        try:
            # 检查缓存
            if (user_id in self.user_preferences_cache and 
                user_id in self.cache_timestamps and
                datetime.utcnow() - self.cache_timestamps[user_id] < self.cache_ttl):
                return self.user_preferences_cache[user_id]
            
            # 从数据库加载（如果有数据库连接）
            if self.db:
                preferences = await self._load_user_preferences_from_db(user_id)
                if preferences:
                    self.user_preferences_cache[user_id] = preferences
                    self.cache_timestamps[user_id] = datetime.utcnow()
                    return preferences
            
            # 创建默认偏好
            default_preferences = UserLanguagePreference(
                user_id=user_id,
                preferred_language=SupportedLanguage.CHINESE_SIMPLIFIED,  # 默认中文
                formality_level=0.6,
                use_honorifics=True,
                prefer_formal_tone=False,
                cultural_adaptation_enabled=True,
                auto_detect_language=True
            )
            
            # 缓存默认偏好
            self.user_preferences_cache[user_id] = default_preferences
            self.cache_timestamps[user_id] = datetime.utcnow()
            
            return default_preferences
            
        except Exception as e:
            self.logger.error(f"Error getting user preferences for user {user_id}: {e}")
            
            # 返回最基本的默认偏好
            return UserLanguagePreference(
                user_id=user_id,
                preferred_language=SupportedLanguage.ENGLISH
            )
    
    async def update_user_preferences(self, user_id: int, 
                                    preferences: Dict[str, Any]) -> UserLanguagePreference:
        """更新用户语言偏好"""
        try:
            # 获取当前偏好
            current_preferences = await self.get_user_preferences(user_id)
            
            # 更新偏好
            if "preferred_language" in preferences:
                lang_code = preferences["preferred_language"]
                current_preferences.preferred_language = SupportedLanguage(lang_code)
            
            if "formality_level" in preferences:
                current_preferences.formality_level = float(preferences["formality_level"])
            
            if "use_honorifics" in preferences:
                current_preferences.use_honorifics = bool(preferences["use_honorifics"])
            
            if "prefer_formal_tone" in preferences:
                current_preferences.prefer_formal_tone = bool(preferences["prefer_formal_tone"])
            
            if "cultural_adaptation_enabled" in preferences:
                current_preferences.cultural_adaptation_enabled = bool(
                    preferences["cultural_adaptation_enabled"]
                )
            
            if "auto_detect_language" in preferences:
                current_preferences.auto_detect_language = bool(preferences["auto_detect_language"])
            
            current_preferences.last_updated = datetime.utcnow()
            
            # 更新缓存
            self.user_preferences_cache[user_id] = current_preferences
            self.cache_timestamps[user_id] = datetime.utcnow()
            
            # 保存到数据库
            if self.db:
                await self._save_user_preferences_to_db(current_preferences)
            
            self.logger.info(f"Updated user preferences for user {user_id}")
            return current_preferences
            
        except Exception as e:
            self.logger.error(f"Error updating user preferences: {e}")
            raise
    
    async def detect_user_language(self, content: str, user_id: int) -> LanguageDetectionResult:
        """检测用户输入语言"""
        try:
            detection_result = await self.handler.detect_language(content)
            
            # 记录检测结果用于学习
            if self.config["learning_enabled"]:
                await self._record_language_detection(user_id, detection_result)
            
            return detection_result
            
        except Exception as e:
            self.logger.error(f"Error detecting user language: {e}")
            raise
    
    async def get_quality_metrics(self, user_id: Optional[int] = None,
                                language: Optional[SupportedLanguage] = None,
                                days: int = 7) -> Dict[str, Any]:
        """获取质量指标统计"""
        try:
            # 过滤条件
            start_date = datetime.utcnow() - timedelta(days=days)
            filtered_metrics = [
                metric for metric in self.quality_metrics
                if metric.created_at >= start_date
            ]
            
            if user_id:
                filtered_metrics = [m for m in filtered_metrics if m.user_id == user_id]
            
            if language:
                filtered_metrics = [m for m in filtered_metrics if m.target_language == language]
            
            if not filtered_metrics:
                return {
                    "total_responses": 0,
                    "average_quality": 0.0,
                    "quality_distribution": {},
                    "language_distribution": {},
                    "adaptation_types": {}
                }
            
            # 计算统计指标
            total_responses = len(filtered_metrics)
            average_quality = sum(m.overall_quality for m in filtered_metrics) / total_responses
            
            # 质量分布
            quality_ranges = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
            for metric in filtered_metrics:
                if metric.overall_quality >= 0.9:
                    quality_ranges["excellent"] += 1
                elif metric.overall_quality >= 0.7:
                    quality_ranges["good"] += 1
                elif metric.overall_quality >= 0.5:
                    quality_ranges["fair"] += 1
                else:
                    quality_ranges["poor"] += 1
            
            # 语言分布
            language_distribution = {}
            for metric in filtered_metrics:
                lang = metric.target_language.value
                language_distribution[lang] = language_distribution.get(lang, 0) + 1
            
            # 适配类型分布
            adaptation_types = {}
            for metric in filtered_metrics:
                for adaptation in metric.adaptation_applied:
                    adaptation_types[adaptation] = adaptation_types.get(adaptation, 0) + 1
            
            return {
                "total_responses": total_responses,
                "average_quality": round(average_quality, 3),
                "quality_distribution": quality_ranges,
                "language_distribution": language_distribution,
                "adaptation_types": adaptation_types,
                "average_processing_time": round(
                    sum(m.processing_time for m in filtered_metrics) / total_responses, 3
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error getting quality metrics: {e}")
            return {}
    
    async def get_supported_languages(self) -> List[Dict[str, Any]]:
        """获取支持的语言列表"""
        return await self.handler.get_supported_languages()
    
    async def submit_user_feedback(self, response_id: str, user_id: int,
                                 rating: float, feedback: Optional[str] = None):
        """提交用户反馈"""
        try:
            # 查找对应的质量指标记录
            for metric in self.quality_metrics:
                if metric.response_id == response_id and metric.user_id == user_id:
                    metric.user_rating = rating
                    metric.user_feedback = feedback
                    break
            
            # 基于反馈学习用户偏好
            if self.config["learning_enabled"] and rating is not None:
                await self._learn_from_feedback(user_id, response_id, rating, feedback)
            
            self.logger.info(f"User feedback submitted: {rating}/5.0")
            
        except Exception as e:
            self.logger.error(f"Error submitting user feedback: {e}")
            raise
    
    def _needs_cultural_adaptation(self, content: str, 
                                 preferences: UserLanguagePreference) -> bool:
        """判断是否需要文化适配"""
        if not preferences.cultural_adaptation_enabled:
            return False
        
        # 检查是否包含需要文化适配的内容
        cultural_indicators = [
            "请", "谢谢", "您好", "再见",  # 中文礼貌用语
            "please", "thank you", "hello", "goodbye",  # 英文礼貌用语
        ]
        
        return any(indicator in content.lower() for indicator in cultural_indicators)
    
    async def _create_adaptation_config(self, 
                                      target_language: SupportedLanguage,
                                      user_preferences: UserLanguagePreference,
                                      context_info: Optional[Dict[str, Any]]) -> ResponseAdaptationConfig:
        """创建适配配置"""
        # 基于用户偏好创建配置
        config = await self.handler.create_adaptation_config(
            target_language=target_language,
            user_preferences={
                "formality_level": user_preferences.formality_level,
                "use_honorifics": user_preferences.use_honorifics,
                "prefer_formal_tone": user_preferences.prefer_formal_tone
            },
            context_info=context_info
        )
        
        return config
    
    async def _optimize_response(self, response: MultilingualResponse,
                               config: ResponseAdaptationConfig) -> MultilingualResponse:
        """优化低质量响应"""
        try:
            # 如果质量分数过低，尝试重新适配
            if response.quality_score < 0.5:
                # 调整配置参数
                optimized_config = config
                optimized_config.formality_level = min(config.formality_level + 0.2, 1.0)
                optimized_config.use_honorifics = True
                
                # 重新适配
                optimized_response = await self.handler.adapt_response(
                    response.original_content, optimized_config
                )
                
                # 如果优化后质量提升，返回优化结果
                if optimized_response.quality_score > response.quality_score:
                    optimized_response.adaptation_applied.append("quality_optimization")
                    return optimized_response
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error optimizing response: {e}")
            return response
    
    async def _record_quality_metrics(self, response: MultilingualResponse,
                                    user_id: int,
                                    detection_result: LanguageDetectionResult,
                                    target_language: SupportedLanguage):
        """记录质量指标"""
        try:
            # 生成响应ID
            response_id = f"{user_id}_{int(datetime.utcnow().timestamp() * 1000)}"
            
            metrics = ResponseQualityMetrics(
                response_id=response_id,
                user_id=user_id,
                original_language=detection_result.detected_language,
                target_language=target_language,
                adaptation_applied=response.adaptation_applied,
                overall_quality=response.quality_score,
                fluency_score=response.fluency_score,
                cultural_appropriateness=response.cultural_appropriateness,
                technical_accuracy=response.technical_accuracy,
                readability_score=response.readability_score,
                processing_time=response.processing_time
            )
            
            # 添加到缓存
            self.quality_metrics.append(metrics)
            
            # 保持缓存大小
            if len(self.quality_metrics) > self.max_metrics_cache:
                self.quality_metrics = self.quality_metrics[-self.max_metrics_cache:]
            
            # 保存到数据库（如果有连接）
            if self.db:
                await self._save_quality_metrics_to_db(metrics)
            
        except Exception as e:
            self.logger.error(f"Error recording quality metrics: {e}")
    
    async def _update_user_learning(self, user_id: int, 
                                  response: MultilingualResponse,
                                  context_info: Optional[Dict[str, Any]]):
        """更新用户偏好学习"""
        try:
            preferences = await self.get_user_preferences(user_id)
            
            # 学习语言偏好
            lang_key = response.target_language.value
            if lang_key not in preferences.usage_statistics:
                preferences.usage_statistics[lang_key] = 0
            preferences.usage_statistics[lang_key] += 1
            
            # 学习质量偏好
            if response.quality_score > 0.8:
                # 记录成功的适配策略
                for adaptation in response.adaptation_applied:
                    if adaptation not in preferences.detected_patterns:
                        preferences.detected_patterns[adaptation] = 0
                    preferences.detected_patterns[adaptation] += 1
            
            # 更新缓存
            self.user_preferences_cache[user_id] = preferences
            
        except Exception as e:
            self.logger.error(f"Error updating user learning: {e}")
    
    def _update_usage_statistics(self, target_language: SupportedLanguage,
                               detection_result: LanguageDetectionResult):
        """更新使用统计"""
        try:
            # 更新目标语言统计
            target_key = f"target_{target_language.value}"
            self.language_usage_stats[target_key] = self.language_usage_stats.get(target_key, 0) + 1
            
            # 更新检测语言统计
            detected_key = f"detected_{detection_result.detected_language.value}"
            self.language_usage_stats[detected_key] = self.language_usage_stats.get(detected_key, 0) + 1
            
            # 更新混合语言统计
            if detection_result.is_multilingual:
                self.language_usage_stats["multilingual"] = self.language_usage_stats.get("multilingual", 0) + 1
            
        except Exception as e:
            self.logger.error(f"Error updating usage statistics: {e}")
    
    async def _record_language_detection(self, user_id: int, 
                                       detection_result: LanguageDetectionResult):
        """记录语言检测结果用于学习"""
        try:
            preferences = await self.get_user_preferences(user_id)
            
            # 记录检测模式
            detected_lang = detection_result.detected_language.value
            if "detected_languages" not in preferences.detected_patterns:
                preferences.detected_patterns["detected_languages"] = {}
            
            lang_patterns = preferences.detected_patterns["detected_languages"]
            lang_patterns[detected_lang] = lang_patterns.get(detected_lang, 0) + 1
            
            # 如果检测到的语言与偏好语言不同，可能需要更新偏好
            if (detection_result.confidence > 0.8 and 
                detection_result.detected_language != preferences.preferred_language):
                
                # 记录语言切换模式
                switch_key = f"{preferences.preferred_language.value}_to_{detected_lang}"
                if "language_switches" not in preferences.detected_patterns:
                    preferences.detected_patterns["language_switches"] = {}
                
                switches = preferences.detected_patterns["language_switches"]
                switches[switch_key] = switches.get(switch_key, 0) + 1
                
                # 如果切换频繁，建议更新偏好语言
                if switches[switch_key] > 5:
                    self.logger.info(
                        f"User {user_id} frequently uses {detected_lang}, "
                        f"consider updating preferred language"
                    )
            
        except Exception as e:
            self.logger.error(f"Error recording language detection: {e}")
    
    async def _learn_from_feedback(self, user_id: int, response_id: str,
                                 rating: float, feedback: Optional[str]):
        """从用户反馈中学习"""
        try:
            preferences = await self.get_user_preferences(user_id)
            
            # 找到对应的质量指标
            target_metric = None
            for metric in self.quality_metrics:
                if metric.response_id == response_id:
                    target_metric = metric
                    break
            
            if not target_metric:
                return
            
            # 基于评分调整偏好
            if rating >= 4.0:  # 高评分
                # 强化成功的适配策略
                for adaptation in target_metric.adaptation_applied:
                    if "successful_adaptations" not in preferences.detected_patterns:
                        preferences.detected_patterns["successful_adaptations"] = {}
                    
                    successful = preferences.detected_patterns["successful_adaptations"]
                    successful[adaptation] = successful.get(adaptation, 0) + 1
            
            elif rating <= 2.0:  # 低评分
                # 记录失败的适配策略
                for adaptation in target_metric.adaptation_applied:
                    if "failed_adaptations" not in preferences.detected_patterns:
                        preferences.detected_patterns["failed_adaptations"] = {}
                    
                    failed = preferences.detected_patterns["failed_adaptations"]
                    failed[adaptation] = failed.get(adaptation, 0) + 1
            
            # 分析文本反馈
            if feedback:
                await self._analyze_text_feedback(user_id, feedback, preferences)
            
        except Exception as e:
            self.logger.error(f"Error learning from feedback: {e}")
    
    async def _analyze_text_feedback(self, user_id: int, feedback: str,
                                   preferences: UserLanguagePreference):
        """分析文本反馈"""
        try:
            feedback_lower = feedback.lower()
            
            # 检测偏好指示词
            if any(word in feedback_lower for word in ["formal", "正式", "礼貌"]):
                preferences.prefer_formal_tone = True
                preferences.formality_level = min(preferences.formality_level + 0.1, 1.0)
            
            elif any(word in feedback_lower for word in ["casual", "informal", "轻松", "随意"]):
                preferences.prefer_formal_tone = False
                preferences.formality_level = max(preferences.formality_level - 0.1, 0.0)
            
            if any(word in feedback_lower for word in ["respectful", "敬语", "您"]):
                preferences.use_honorifics = True
            
            elif any(word in feedback_lower for word in ["direct", "简单", "直接"]):
                preferences.use_honorifics = False
            
        except Exception as e:
            self.logger.error(f"Error analyzing text feedback: {e}")
    
    async def _load_user_preferences_from_db(self, user_id: int) -> Optional[UserLanguagePreference]:
        """从数据库加载用户偏好"""
        # 这里应该实现数据库查询逻辑
        # 由于当前没有具体的数据库表结构，返回None
        return None
    
    async def _save_user_preferences_to_db(self, preferences: UserLanguagePreference):
        """保存用户偏好到数据库"""
        # 这里应该实现数据库保存逻辑
        pass
    
    async def _save_quality_metrics_to_db(self, metrics: ResponseQualityMetrics):
        """保存质量指标到数据库"""
        # 这里应该实现数据库保存逻辑
        pass
    
    async def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "language_usage": dict(self.language_usage_stats),
            "total_responses": sum(self.language_usage_stats.values()),
            "cache_status": {
                "cached_preferences": len(self.user_preferences_cache),
                "cached_metrics": len(self.quality_metrics)
            },
            "service_config": dict(self.config)
        }
    
    async def update_service_config(self, config_updates: Dict[str, Any]):
        """更新服务配置"""
        try:
            for key, value in config_updates.items():
                if key in self.config:
                    self.config[key] = value
                    self.logger.info(f"Updated config {key} = {value}")
            
        except Exception as e:
            self.logger.error(f"Error updating service config: {e}")
            raise


# 全局服务实例
_multilingual_service_instance: Optional[MultilingualResponseService] = None


async def get_multilingual_response_service() -> MultilingualResponseService:
    """获取多语言响应服务实例"""
    global _multilingual_service_instance
    
    if _multilingual_service_instance is None:
        _multilingual_service_instance = MultilingualResponseService(None)
    
    return _multilingual_service_instance


async def create_multilingual_response_service(db: AsyncSession) -> MultilingualResponseService:
    """创建新的多语言响应服务实例"""
    return MultilingualResponseService(db)