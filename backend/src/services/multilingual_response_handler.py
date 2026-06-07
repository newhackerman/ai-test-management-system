"""
多语言响应处理器

本模块负责处理AI助手的多语言响应，包括：
1. 语言检测和识别
2. 响应内容的语言适配
3. 文化背景优化
4. 多语言格式化和后处理
5. 语言质量评估和优化

主要特性：
- 自动检测用户输入语言
- 智能选择响应语言
- 文化背景适配
- 多语言内容格式化
- 响应质量评估
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class SupportedLanguage(Enum):
    """支持的语言枚举"""
    CHINESE_SIMPLIFIED = "zh-CN"    # 简体中文
    CHINESE_TRADITIONAL = "zh-TW"   # 繁体中文
    ENGLISH = "en"                  # 英语
    JAPANESE = "ja"                 # 日语
    KOREAN = "ko"                   # 韩语
    FRENCH = "fr"                   # 法语
    GERMAN = "de"                   # 德语
    SPANISH = "es"                  # 西班牙语
    RUSSIAN = "ru"                  # 俄语
    ARABIC = "ar"                   # 阿拉伯语


class ResponseType(Enum):
    """响应类型枚举"""
    DIRECT_ANSWER = "direct_answer"         # 直接回答
    EXPLANATION = "explanation"             # 解释说明
    INSTRUCTION = "instruction"             # 指导说明
    CREATIVE_CONTENT = "creative_content"   # 创意内容
    TECHNICAL_CONTENT = "technical_content" # 技术内容
    FORMAL_DOCUMENT = "formal_document"     # 正式文档
    CASUAL_CHAT = "casual_chat"            # 日常对话


class CulturalAdaptation(Enum):
    """文化适配类型"""
    WESTERN = "western"           # 西方文化
    EAST_ASIAN = "east_asian"     # 东亚文化
    MIDDLE_EASTERN = "middle_eastern"  # 中东文化
    LATIN = "latin"               # 拉丁文化
    SLAVIC = "slavic"             # 斯拉夫文化
    NEUTRAL = "neutral"           # 中性文化


@dataclass
class LanguageDetectionResult:
    """语言检测结果"""
    detected_language: SupportedLanguage
    confidence: float  # 检测置信度 (0-1)
    mixed_languages: List[SupportedLanguage]  # 混合语言
    language_ratio: Dict[str, float]  # 各语言占比
    is_multilingual: bool  # 是否多语言混合
    
    # 语言特征
    has_code_switching: bool = False  # 是否有语码转换
    dominant_script: str = ""  # 主要文字系统
    regional_variant: Optional[str] = None  # 地区变体


@dataclass
class ResponseAdaptationConfig:
    """响应适配配置"""
    target_language: SupportedLanguage
    response_type: ResponseType
    cultural_adaptation: CulturalAdaptation
    formality_level: float  # 正式程度 (0-1)
    technical_level: float  # 技术程度 (0-1)
    
    # 格式化选项
    use_honorifics: bool = False  # 使用敬语
    prefer_formal_tone: bool = False  # 偏好正式语调
    include_cultural_context: bool = True  # 包含文化背景
    adapt_examples: bool = True  # 适配示例
    localize_references: bool = True  # 本地化引用


@dataclass
class MultilingualResponse:
    """多语言响应结果"""
    original_content: str
    adapted_content: str
    target_language: SupportedLanguage
    adaptation_applied: List[str]  # 应用的适配策略
    quality_score: float  # 质量评分 (0-1)
    
    # 元数据
    processing_time: float
    cultural_adaptations: List[str]
    language_enhancements: List[str]
    formatting_changes: List[str]
    
    # 质量指标
    fluency_score: float = 0.0
    cultural_appropriateness: float = 0.0
    technical_accuracy: float = 0.0
    readability_score: float = 0.0


class MultilingualResponseHandler:
    """多语言响应处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 语言检测模式配置
        self.language_patterns = {
            SupportedLanguage.CHINESE_SIMPLIFIED: {
                "char_ranges": [(0x4E00, 0x9FFF)],  # CJK统一汉字
                "keywords": ["的", "是", "在", "有", "和", "了", "我", "你", "他"],
                "punctuation": ["。", "，", "？", "！", "；", "："],
                "script_type": "cjk"
            },
            SupportedLanguage.CHINESE_TRADITIONAL: {
                "char_ranges": [(0x4E00, 0x9FFF)],
                "keywords": ["的", "是", "在", "有", "和", "了", "我", "你", "他"],
                "traditional_chars": ["繁", "體", "語", "學", "習", "電", "腦"],
                "punctuation": ["。", "，", "？", "！", "；", "："],
                "script_type": "cjk"
            },
            SupportedLanguage.ENGLISH: {
                "char_ranges": [(0x0041, 0x005A), (0x0061, 0x007A)],  # A-Z, a-z
                "keywords": ["the", "and", "is", "in", "to", "of", "a", "that", "it"],
                "punctuation": [".", ",", "?", "!", ";", ":"],
                "script_type": "latin"
            },
            SupportedLanguage.JAPANESE: {
                "char_ranges": [(0x3040, 0x309F), (0x30A0, 0x30FF), (0x4E00, 0x9FFF)],
                "keywords": ["の", "に", "は", "を", "が", "で", "と", "から", "まで"],
                "punctuation": ["。", "、", "？", "！"],
                "script_type": "cjk"
            },
            SupportedLanguage.KOREAN: {
                "char_ranges": [(0xAC00, 0xD7AF)],  # 한글
                "keywords": ["이", "가", "을", "를", "에", "의", "와", "과", "로"],
                "punctuation": [".", ",", "?", "!"],
                "script_type": "hangul"
            }
        }
        
        # 文化适配规则
        self.cultural_adaptations = {
            CulturalAdaptation.EAST_ASIAN: {
                "languages": [SupportedLanguage.CHINESE_SIMPLIFIED, 
                            SupportedLanguage.CHINESE_TRADITIONAL,
                            SupportedLanguage.JAPANESE, 
                            SupportedLanguage.KOREAN],
                "characteristics": {
                    "hierarchy_awareness": True,
                    "indirect_communication": True,
                    "group_harmony": True,
                    "respect_for_authority": True,
                    "face_saving": True
                },
                "adaptations": [
                    "使用谦逊的表达方式",
                    "避免直接否定或批评",
                    "考虑等级关系和礼貌用语",
                    "重视集体利益和和谐",
                    "提供多种选择而非强制建议"
                ]
            },
            CulturalAdaptation.WESTERN: {
                "languages": [SupportedLanguage.ENGLISH, 
                            SupportedLanguage.FRENCH,
                            SupportedLanguage.GERMAN, 
                            SupportedLanguage.SPANISH],
                "characteristics": {
                    "direct_communication": True,
                    "individualism": True,
                    "efficiency_focused": True,
                    "equality_emphasis": True,
                    "innovation_valued": True
                },
                "adaptations": [
                    "使用直接明确的表达",
                    "强调个人选择和自主性",
                    "注重效率和实用性",
                    "平等对待不同观点",
                    "鼓励创新和独立思考"
                ]
            }
        }
        
        # 响应格式化规则
        self.formatting_rules = {
            SupportedLanguage.CHINESE_SIMPLIFIED: {
                "punctuation_style": "chinese",
                "number_format": "chinese_mixed",
                "date_format": "yyyy年mm月dd日",
                "quotation_marks": "「」",
                "emphasis_style": "**粗体**",
                "list_style": "1. 2. 3."
            },
            SupportedLanguage.ENGLISH: {
                "punctuation_style": "western",
                "number_format": "western",
                "date_format": "MM/DD/YYYY",
                "quotation_marks": "\"\"",
                "emphasis_style": "**bold**",
                "list_style": "1. 2. 3."
            },
            SupportedLanguage.JAPANESE: {
                "punctuation_style": "japanese",
                "number_format": "japanese_mixed",
                "date_format": "yyyy年mm月dd日",
                "quotation_marks": "「」",
                "emphasis_style": "**太字**",
                "list_style": "１．２．３．"
            }
        }
        
        self.logger.info("Multilingual response handler initialized")
    
    async def detect_language(self, content: str) -> LanguageDetectionResult:
        """
        检测内容语言
        
        Args:
            content: 待检测的文本内容
            
        Returns:
            LanguageDetectionResult: 语言检测结果
        """
        try:
            if not content or not content.strip():
                return LanguageDetectionResult(
                    detected_language=SupportedLanguage.ENGLISH,
                    confidence=0.0,
                    mixed_languages=[],
                    language_ratio={},
                    is_multilingual=False
                )
            
            # 1. 计算各语言的特征匹配度
            language_scores = {}
            for lang, patterns in self.language_patterns.items():
                score = self._calculate_language_score(content, patterns)
                if score > 0:
                    language_scores[lang] = score
            
            if not language_scores:
                # 默认为英语
                return LanguageDetectionResult(
                    detected_language=SupportedLanguage.ENGLISH,
                    confidence=0.3,
                    mixed_languages=[],
                    language_ratio={"en": 1.0},
                    is_multilingual=False
                )
            
            # 2. 确定主要语言
            primary_language = max(language_scores.keys(), key=lambda l: language_scores[l])
            primary_score = language_scores[primary_language]
            
            # 3. 检测混合语言
            mixed_languages = [lang for lang, score in language_scores.items() 
                             if score > 0.1 and lang != primary_language]
            
            # 4. 计算语言占比
            total_score = sum(language_scores.values())
            language_ratio = {lang.value: score / total_score 
                            for lang, score in language_scores.items()}
            
            # 5. 检测特殊特征
            has_code_switching = len(mixed_languages) > 0 and max(
                score for lang, score in language_scores.items() 
                if lang != primary_language
            ) > 0.2
            
            dominant_script = self._identify_dominant_script(content)
            regional_variant = self._detect_regional_variant(content, primary_language)
            
            result = LanguageDetectionResult(
                detected_language=primary_language,
                confidence=min(primary_score, 1.0),
                mixed_languages=mixed_languages,
                language_ratio=language_ratio,
                is_multilingual=len(mixed_languages) > 0,
                has_code_switching=has_code_switching,
                dominant_script=dominant_script,
                regional_variant=regional_variant
            )
            
            self.logger.debug(f"Language detection result: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error detecting language: {e}")
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.ENGLISH,
                confidence=0.1,
                mixed_languages=[],
                language_ratio={"en": 1.0},
                is_multilingual=False
            )
    
    async def adapt_response(self, content: str, 
                           config: ResponseAdaptationConfig) -> MultilingualResponse:
        """
        适配响应内容到目标语言和文化
        
        Args:
            content: 原始响应内容
            config: 适配配置
            
        Returns:
            MultilingualResponse: 适配后的响应
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Adapting response to {config.target_language.value}")
            
            # 1. 分析原始内容
            original_detection = await self.detect_language(content)
            
            # 2. 确定文化适配策略
            cultural_adaptation = self._determine_cultural_adaptation(config.target_language)
            
            # 3. 应用语言适配
            language_adapted = await self._apply_language_adaptation(
                content, config, original_detection
            )
            
            # 4. 应用文化适配
            culturally_adapted = await self._apply_cultural_adaptation(
                language_adapted, config, cultural_adaptation
            )
            
            # 5. 应用格式化
            formatted_content = await self._apply_formatting(
                culturally_adapted, config
            )
            
            # 6. 质量评估
            quality_metrics = await self._evaluate_response_quality(
                content, formatted_content, config
            )
            
            # 7. 记录应用的适配策略
            adaptations_applied = self._get_applied_adaptations(config, cultural_adaptation)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = MultilingualResponse(
                original_content=content,
                adapted_content=formatted_content,
                target_language=config.target_language,
                adaptation_applied=adaptations_applied,
                quality_score=quality_metrics["overall_score"],
                processing_time=processing_time,
                cultural_adaptations=cultural_adaptation.get("adaptations", []),
                language_enhancements=self._get_language_enhancements(config),
                formatting_changes=self._get_formatting_changes(config),
                fluency_score=quality_metrics["fluency"],
                cultural_appropriateness=quality_metrics["cultural_appropriateness"],
                technical_accuracy=quality_metrics["technical_accuracy"],
                readability_score=quality_metrics["readability"]
            )
            
            self.logger.info(
                f"Response adaptation completed in {processing_time:.2f}s, "
                f"quality score: {result.quality_score:.2f}"
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"Error adapting response: {e}")
            
            # 返回原始内容作为fallback
            return MultilingualResponse(
                original_content=content,
                adapted_content=content,
                target_language=config.target_language,
                adaptation_applied=["error_fallback"],
                quality_score=0.5,
                processing_time=processing_time,
                cultural_adaptations=[],
                language_enhancements=[],
                formatting_changes=[]
            )
    
    def _calculate_language_score(self, content: str, patterns: Dict[str, Any]) -> float:
        """计算语言匹配分数"""
        score = 0.0
        total_chars = len(content)
        
        if total_chars == 0:
            return 0.0
        
        # 1. 字符范围匹配
        if "char_ranges" in patterns:
            char_matches = 0
            for char in content:
                char_code = ord(char)
                for start, end in patterns["char_ranges"]:
                    if start <= char_code <= end:
                        char_matches += 1
                        break
            score += (char_matches / total_chars) * 0.6
        
        # 2. 关键词匹配
        if "keywords" in patterns:
            keyword_matches = sum(1 for keyword in patterns["keywords"] if keyword in content)
            score += min(keyword_matches / len(patterns["keywords"]), 1.0) * 0.3
        
        # 3. 标点符号匹配
        if "punctuation" in patterns:
            punct_matches = sum(1 for punct in patterns["punctuation"] if punct in content)
            score += min(punct_matches / len(patterns["punctuation"]), 1.0) * 0.1
        
        # 4. 特殊字符检测（如繁体字）
        if "traditional_chars" in patterns:
            trad_matches = sum(1 for char in content if char in patterns["traditional_chars"])
            if trad_matches > 0:
                score += 0.2  # 繁体字加分
        
        return min(score, 1.0)
    
    def _identify_dominant_script(self, content: str) -> str:
        """识别主要文字系统"""
        script_counts = {
            "latin": 0,
            "cjk": 0,
            "arabic": 0,
            "cyrillic": 0,
            "hangul": 0
        }
        
        for char in content:
            char_code = ord(char)
            if 0x0041 <= char_code <= 0x007A or 0x0041 <= char_code <= 0x005A:
                script_counts["latin"] += 1
            elif 0x4E00 <= char_code <= 0x9FFF or 0x3040 <= char_code <= 0x30FF:
                script_counts["cjk"] += 1
            elif 0x0600 <= char_code <= 0x06FF:
                script_counts["arabic"] += 1
            elif 0x0400 <= char_code <= 0x04FF:
                script_counts["cyrillic"] += 1
            elif 0xAC00 <= char_code <= 0xD7AF:
                script_counts["hangul"] += 1
        
        return max(script_counts.keys(), key=lambda k: script_counts[k])
    
    def _detect_regional_variant(self, content: str, language: SupportedLanguage) -> Optional[str]:
        """检测地区变体"""
        if language == SupportedLanguage.CHINESE_SIMPLIFIED:
            # 检测大陆、新加坡等变体
            mainland_indicators = ["同志", "单位", "爱人", "师傅"]
            singapore_indicators = ["巴刹", "组屋", "咖啡店"]
            
            if any(indicator in content for indicator in mainland_indicators):
                return "mainland_china"
            elif any(indicator in content for indicator in singapore_indicators):
                return "singapore"
        
        elif language == SupportedLanguage.CHINESE_TRADITIONAL:
            # 检测台湾、香港变体
            taiwan_indicators = ["欸", "蛤", "捏"]
            hongkong_indicators = ["係", "喺", "嘅", "咗"]
            
            if any(indicator in content for indicator in taiwan_indicators):
                return "taiwan"
            elif any(indicator in content for indicator in hongkong_indicators):
                return "hong_kong"
        
        return None
    
    def _determine_cultural_adaptation(self, target_language: SupportedLanguage) -> Dict[str, Any]:
        """确定文化适配策略"""
        for adaptation_type, config in self.cultural_adaptations.items():
            if target_language in config["languages"]:
                return {
                    "type": adaptation_type,
                    "characteristics": config["characteristics"],
                    "adaptations": config["adaptations"]
                }
        
        # 默认中性文化适配
        return {
            "type": CulturalAdaptation.NEUTRAL,
            "characteristics": {},
            "adaptations": ["使用中性的表达方式", "避免文化特定的引用"]
        }
    
    async def _apply_language_adaptation(self, content: str, 
                                       config: ResponseAdaptationConfig,
                                       original_detection: LanguageDetectionResult) -> str:
        """应用语言适配"""
        adapted_content = content
        
        # 如果目标语言与检测语言相同，直接返回
        if config.target_language == original_detection.detected_language:
            return adapted_content
        
        # 这里可以集成翻译服务或语言转换逻辑
        # 目前返回原内容，实际实现中可以调用翻译API
        
        return adapted_content
    
    async def _apply_cultural_adaptation(self, content: str,
                                       config: ResponseAdaptationConfig,
                                       cultural_adaptation: Dict[str, Any]) -> str:
        """应用文化适配"""
        adapted_content = content
        
        # 根据文化特征调整内容
        characteristics = cultural_adaptation.get("characteristics", {})
        
        if characteristics.get("hierarchy_awareness"):
            # 添加敬语和礼貌用语
            adapted_content = self._add_honorifics(adapted_content, config.target_language)
        
        if characteristics.get("indirect_communication"):
            # 使用更委婉的表达
            adapted_content = self._make_indirect(adapted_content)
        
        if characteristics.get("direct_communication"):
            # 使用更直接的表达
            adapted_content = self._make_direct(adapted_content)
        
        return adapted_content
    
    async def _apply_formatting(self, content: str, 
                              config: ResponseAdaptationConfig) -> str:
        """应用格式化规则"""
        if config.target_language not in self.formatting_rules:
            return content
        
        rules = self.formatting_rules[config.target_language]
        formatted_content = content
        
        # 应用标点符号规则
        if rules["punctuation_style"] == "chinese":
            formatted_content = formatted_content.replace(".", "。")
            formatted_content = formatted_content.replace(",", "，")
            formatted_content = formatted_content.replace("?", "？")
            formatted_content = formatted_content.replace("!", "！")
        
        # 应用引号规则
        if rules["quotation_marks"] == "「」":
            formatted_content = re.sub(r'"([^"]*)"', r'「\1」', formatted_content)
        
        # 应用日期格式
        if rules["date_format"] == "yyyy年mm月dd日":
            # 转换日期格式的正则表达式
            formatted_content = re.sub(
                r'(\d{4})-(\d{1,2})-(\d{1,2})', 
                r'\1年\2月\3日', 
                formatted_content
            )
        
        return formatted_content
    
    async def _evaluate_response_quality(self, original: str, adapted: str,
                                       config: ResponseAdaptationConfig) -> Dict[str, float]:
        """评估响应质量"""
        # 简化的质量评估，实际实现中可以使用更复杂的算法
        
        # 流畅度评分（基于长度和结构）
        fluency = min(len(adapted) / max(len(original), 1) * 0.8 + 0.2, 1.0)
        
        # 文化适宜性评分（基于目标语言特征）
        cultural_appropriateness = 0.8  # 默认较高分数
        
        # 技术准确性评分（保持技术术语的准确性）
        technical_accuracy = 0.9 if self._preserve_technical_terms(original, adapted) else 0.7
        
        # 可读性评分（基于句子长度和复杂度）
        readability = self._calculate_readability(adapted)
        
        # 综合评分
        overall_score = (fluency * 0.3 + cultural_appropriateness * 0.3 + 
                        technical_accuracy * 0.2 + readability * 0.2)
        
        return {
            "fluency": fluency,
            "cultural_appropriateness": cultural_appropriateness,
            "technical_accuracy": technical_accuracy,
            "readability": readability,
            "overall_score": overall_score
        }
    
    def _add_honorifics(self, content: str, language: SupportedLanguage) -> str:
        """添加敬语"""
        if language in [SupportedLanguage.CHINESE_SIMPLIFIED, SupportedLanguage.CHINESE_TRADITIONAL]:
            # 将"你"替换为"您"
            content = re.sub(r'\b你\b', '您', content)
            # 添加礼貌用语
            if not any(word in content for word in ['请', '谢谢', '不好意思']):
                content = "请注意，" + content
        
        return content
    
    def _make_indirect(self, content: str) -> str:
        """使表达更委婉"""
        # 添加委婉语
        indirect_phrases = ["可能", "也许", "建议", "不妨考虑"]
        
        # 如果内容过于直接，添加委婉表达
        if any(word in content for word in ["必须", "应该", "一定要"]):
            content = "建议您" + content
        
        return content
    
    def _make_direct(self, content: str) -> str:
        """使表达更直接"""
        # 移除过多的修饰词
        content = re.sub(r'可能|也许|大概|估计', '', content)
        
        return content
    
    def _preserve_technical_terms(self, original: str, adapted: str) -> bool:
        """检查是否保持了技术术语"""
        # 简化检查：确保关键技术词汇没有丢失
        technical_terms = ["API", "HTTP", "JSON", "SQL", "HTML", "CSS", "JavaScript"]
        
        for term in technical_terms:
            if term in original and term not in adapted:
                return False
        
        return True
    
    def _calculate_readability(self, content: str) -> float:
        """计算可读性分数"""
        if not content:
            return 0.0
        
        # 简化的可读性计算
        sentences = len(re.split(r'[。！？.!?]', content))
        words = len(content.split())
        
        if sentences == 0:
            return 0.5
        
        avg_words_per_sentence = words / sentences
        
        # 理想的句子长度是10-20个词
        if 10 <= avg_words_per_sentence <= 20:
            return 1.0
        elif avg_words_per_sentence < 10:
            return 0.8
        else:
            return max(0.3, 1.0 - (avg_words_per_sentence - 20) * 0.05)
    
    def _get_applied_adaptations(self, config: ResponseAdaptationConfig,
                               cultural_adaptation: Dict[str, Any]) -> List[str]:
        """获取应用的适配策略"""
        adaptations = []
        
        adaptations.append(f"target_language_{config.target_language.value}")
        adaptations.append(f"response_type_{config.response_type.value}")
        adaptations.append(f"cultural_adaptation_{cultural_adaptation['type'].value}")
        
        if config.use_honorifics:
            adaptations.append("honorifics_added")
        
        if config.prefer_formal_tone:
            adaptations.append("formal_tone_applied")
        
        if config.include_cultural_context:
            adaptations.append("cultural_context_included")
        
        return adaptations
    
    def _get_language_enhancements(self, config: ResponseAdaptationConfig) -> List[str]:
        """获取语言增强策略"""
        enhancements = []
        
        if config.formality_level > 0.7:
            enhancements.append("高正式度语言风格")
        elif config.formality_level < 0.3:
            enhancements.append("轻松友好语言风格")
        
        if config.technical_level > 0.7:
            enhancements.append("技术术语精确使用")
        
        if config.use_honorifics:
            enhancements.append("敬语和礼貌用词")
        
        return enhancements
    
    def _get_formatting_changes(self, config: ResponseAdaptationConfig) -> List[str]:
        """获取格式化变更"""
        changes = []
        
        if config.target_language in self.formatting_rules:
            rules = self.formatting_rules[config.target_language]
            
            if rules["punctuation_style"] != "western":
                changes.append(f"标点符号风格: {rules['punctuation_style']}")
            
            if rules["quotation_marks"] != '""':
                changes.append(f"引号风格: {rules['quotation_marks']}")
            
            if rules["date_format"] != "MM/DD/YYYY":
                changes.append(f"日期格式: {rules['date_format']}")
        
        return changes
    
    async def create_adaptation_config(self, 
                                     target_language: SupportedLanguage,
                                     user_preferences: Optional[Dict[str, Any]] = None,
                                     context_info: Optional[Dict[str, Any]] = None) -> ResponseAdaptationConfig:
        """
        创建响应适配配置
        
        Args:
            target_language: 目标语言
            user_preferences: 用户偏好设置
            context_info: 上下文信息
            
        Returns:
            ResponseAdaptationConfig: 适配配置
        """
        # 默认配置
        config = ResponseAdaptationConfig(
            target_language=target_language,
            response_type=ResponseType.DIRECT_ANSWER,
            cultural_adaptation=CulturalAdaptation.NEUTRAL,
            formality_level=0.5,
            technical_level=0.5,
            use_honorifics=False,
            prefer_formal_tone=False,
            include_cultural_context=True,
            adapt_examples=True,
            localize_references=True
        )
        
        # 根据用户偏好调整
        if user_preferences:
            config.formality_level = user_preferences.get("formality_level", config.formality_level)
            config.use_honorifics = user_preferences.get("use_honorifics", config.use_honorifics)
            config.prefer_formal_tone = user_preferences.get("prefer_formal_tone", config.prefer_formal_tone)
        
        # 根据上下文信息调整
        if context_info:
            if context_info.get("is_technical_content"):
                config.technical_level = 0.8
                config.response_type = ResponseType.TECHNICAL_CONTENT
            
            if context_info.get("is_formal_document"):
                config.formality_level = 0.9
                config.prefer_formal_tone = True
                config.response_type = ResponseType.FORMAL_DOCUMENT
        
        # 根据目标语言调整文化适配
        cultural_adaptation = self._determine_cultural_adaptation(target_language)
        config.cultural_adaptation = cultural_adaptation["type"]
        
        # 东亚语言默认使用敬语
        if target_language in [SupportedLanguage.CHINESE_SIMPLIFIED, 
                             SupportedLanguage.CHINESE_TRADITIONAL,
                             SupportedLanguage.JAPANESE, 
                             SupportedLanguage.KOREAN]:
            config.use_honorifics = True
            config.formality_level = max(config.formality_level, 0.6)
        
        return config
    
    async def get_supported_languages(self) -> List[Dict[str, Any]]:
        """获取支持的语言列表"""
        languages = []
        
        for lang in SupportedLanguage:
            lang_info = {
                "code": lang.value,
                "name": self._get_language_name(lang),
                "native_name": self._get_native_language_name(lang),
                "script_type": self.language_patterns.get(lang, {}).get("script_type", "latin"),
                "cultural_adaptation": self._determine_cultural_adaptation(lang)["type"].value
            }
            languages.append(lang_info)
        
        return languages
    
    def _get_language_name(self, language: SupportedLanguage) -> str:
        """获取语言英文名称"""
        names = {
            SupportedLanguage.CHINESE_SIMPLIFIED: "Chinese (Simplified)",
            SupportedLanguage.CHINESE_TRADITIONAL: "Chinese (Traditional)",
            SupportedLanguage.ENGLISH: "English",
            SupportedLanguage.JAPANESE: "Japanese",
            SupportedLanguage.KOREAN: "Korean",
            SupportedLanguage.FRENCH: "French",
            SupportedLanguage.GERMAN: "German",
            SupportedLanguage.SPANISH: "Spanish",
            SupportedLanguage.RUSSIAN: "Russian",
            SupportedLanguage.ARABIC: "Arabic"
        }
        return names.get(language, language.value)
    
    def _get_native_language_name(self, language: SupportedLanguage) -> str:
        """获取语言本地名称"""
        native_names = {
            SupportedLanguage.CHINESE_SIMPLIFIED: "简体中文",
            SupportedLanguage.CHINESE_TRADITIONAL: "繁體中文",
            SupportedLanguage.ENGLISH: "English",
            SupportedLanguage.JAPANESE: "日本語",
            SupportedLanguage.KOREAN: "한국어",
            SupportedLanguage.FRENCH: "Français",
            SupportedLanguage.GERMAN: "Deutsch",
            SupportedLanguage.SPANISH: "Español",
            SupportedLanguage.RUSSIAN: "Русский",
            SupportedLanguage.ARABIC: "العربية"
        }
        return native_names.get(language, language.value)