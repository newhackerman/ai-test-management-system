"""
中文内容优化路由服务

本模块专门处理中文内容的智能路由，包括：
1. 中文内容识别和分析
2. 中文AI模型优先级排序
3. 中文文化背景优化
4. 语言特征分析和路由决策
5. 中文专业术语处理

主要特性：
- 智能识别中文内容和语境
- 优先选择中文优化的AI模型
- 考虑文化背景和语言习惯
- 支持繁简体中文处理
- 专业术语和行业词汇优化
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class ChineseContentType(Enum):
    """中文内容类型枚举"""
    TRADITIONAL_CHINESE = "traditional_chinese"  # 繁体中文
    SIMPLIFIED_CHINESE = "simplified_chinese"   # 简体中文
    MIXED_CHINESE = "mixed_chinese"             # 中英混合
    TECHNICAL_CHINESE = "technical_chinese"     # 技术中文
    BUSINESS_CHINESE = "business_chinese"       # 商务中文
    CASUAL_CHINESE = "casual_chinese"           # 日常中文
    FORMAL_CHINESE = "formal_chinese"           # 正式中文
    LITERARY_CHINESE = "literary_chinese"       # 文学中文


class ChineseComplexity(Enum):
    """中文复杂度枚举"""
    SIMPLE = "simple"           # 简单：日常对话、基础问答
    MODERATE = "moderate"       # 中等：一般文档、业务交流
    COMPLEX = "complex"         # 复杂：技术文档、学术论文
    VERY_COMPLEX = "very_complex"  # 极复杂：专业研究、文学创作


class CulturalContext(Enum):
    """文化背景枚举"""
    MAINLAND_CHINA = "mainland_china"    # 中国大陆
    HONG_KONG = "hong_kong"              # 香港
    TAIWAN = "taiwan"                    # 台湾
    SINGAPORE = "singapore"              # 新加坡
    OVERSEAS_CHINESE = "overseas_chinese" # 海外华人
    GENERAL = "general"                  # 通用


@dataclass
class ChineseContentAnalysis:
    """中文内容分析结果"""
    content_type: ChineseContentType
    complexity: ChineseComplexity
    cultural_context: CulturalContext
    chinese_ratio: float  # 中文字符占比
    traditional_ratio: float  # 繁体字占比
    technical_terms: List[str]  # 技术术语
    cultural_references: List[str]  # 文化引用
    formality_level: float  # 正式程度 (0-1)
    confidence_score: float  # 分析置信度
    
    # 语言特征
    has_idioms: bool = False  # 是否包含成语
    has_classical_chinese: bool = False  # 是否包含文言文
    has_regional_dialect: bool = False  # 是否包含方言
    has_internet_slang: bool = False  # 是否包含网络用语
    
    # 专业领域
    domain: Optional[str] = None  # 专业领域
    industry_terms: List[str] = None  # 行业术语
    
    def __post_init__(self):
        if self.industry_terms is None:
            self.industry_terms = []


@dataclass
class ChineseRoutingDecision:
    """中文路由决策结果"""
    recommended_provider: str
    confidence: float
    reasoning: str
    optimization_strategy: str
    cultural_adaptations: List[str]
    language_enhancements: List[str]
    estimated_quality_score: float


class ChineseContentRouter:
    """中文内容优化路由器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 中文AI提供商能力评分
        self.chinese_provider_capabilities = {
            "baidu_wenxin": {
                "chinese_understanding": 0.95,
                "cultural_context": 0.90,
                "traditional_chinese": 0.85,
                "simplified_chinese": 0.95,
                "technical_chinese": 0.88,
                "business_chinese": 0.92,
                "literary_chinese": 0.85,
                "idiom_usage": 0.90,
                "formal_language": 0.88,
                "mainland_culture": 0.95,
                "cost_efficiency": 0.90
            },
            "aliyun_tongyi": {
                "chinese_understanding": 0.92,
                "cultural_context": 0.88,
                "traditional_chinese": 0.80,
                "simplified_chinese": 0.92,
                "technical_chinese": 0.90,
                "business_chinese": 0.88,
                "literary_chinese": 0.82,
                "idiom_usage": 0.85,
                "formal_language": 0.90,
                "mainland_culture": 0.90,
                "cost_efficiency": 0.85
            },
            "zhipu_chatglm": {
                "chinese_understanding": 0.88,
                "cultural_context": 0.85,
                "traditional_chinese": 0.75,
                "simplified_chinese": 0.88,
                "technical_chinese": 0.85,
                "business_chinese": 0.80,
                "literary_chinese": 0.78,
                "idiom_usage": 0.80,
                "formal_language": 0.82,
                "mainland_culture": 0.85,
                "cost_efficiency": 0.95
            },
            "xunfei_xinghuo": {
                "chinese_understanding": 0.85,
                "cultural_context": 0.82,
                "traditional_chinese": 0.70,
                "simplified_chinese": 0.85,
                "technical_chinese": 0.80,
                "business_chinese": 0.78,
                "literary_chinese": 0.75,
                "idiom_usage": 0.78,
                "formal_language": 0.80,
                "mainland_culture": 0.82,
                "cost_efficiency": 0.90
            },
            "openai": {
                "chinese_understanding": 0.75,
                "cultural_context": 0.65,
                "traditional_chinese": 0.70,
                "simplified_chinese": 0.75,
                "technical_chinese": 0.80,
                "business_chinese": 0.70,
                "literary_chinese": 0.65,
                "idiom_usage": 0.60,
                "formal_language": 0.75,
                "mainland_culture": 0.60,
                "cost_efficiency": 0.60
            },
            "anthropic": {
                "chinese_understanding": 0.70,
                "cultural_context": 0.60,
                "traditional_chinese": 0.65,
                "simplified_chinese": 0.70,
                "technical_chinese": 0.75,
                "business_chinese": 0.65,
                "literary_chinese": 0.70,
                "idiom_usage": 0.55,
                "formal_language": 0.70,
                "mainland_culture": 0.55,
                "cost_efficiency": 0.50
            }
        }
        
        # 中文字符范围
        self.chinese_char_ranges = [
            (0x4E00, 0x9FFF),   # CJK统一汉字
            (0x3400, 0x4DBF),   # CJK扩展A
            (0x20000, 0x2A6DF), # CJK扩展B
            (0x2A700, 0x2B73F), # CJK扩展C
            (0x2B740, 0x2B81F), # CJK扩展D
            (0x2B820, 0x2CEAF), # CJK扩展E
            (0x2CEB0, 0x2EBEF), # CJK扩展F
            (0x3000, 0x303F),   # CJK符号和标点
            (0xFF00, 0xFFEF),   # 全角ASCII、全角标点
        ]
        
        # 繁体字检测字符集（常见繁体字）
        self.traditional_chars = set([
            '繁', '體', '漢', '語', '學', '習', '電', '腦', '網', '絡',
            '資', '訊', '軟', '體', '開', '發', '測', '試', '項', '目',
            '管', '理', '系', '統', '數', '據', '庫', '設', '計', '實',
            '現', '優', '化', '應', '用', '程', '序', '介', '面', '功',
            '能', '模', '塊', '服', '務', '架', '構', '框', '架', '類',
            '別', '對', '象', '方', '法', '屬', '性', '變', '量', '參',
            '數', '返', '回', '值', '異', '常', '處', '理', '錯', '誤',
            '調', '試', '運', '行', '執', '行', '結', '果', '輸', '出',
            '輸', '入', '配', '置', '環', '境', '部', '署', '發', '布'
        ])
        
        # 技术术语词典
        self.technical_terms = {
            '软件开发': ['编程', '代码', '算法', '数据结构', '设计模式', 'API', '框架', '库'],
            '测试管理': ['测试用例', '测试计划', '缺陷', 'bug', '自动化测试', '单元测试', '集成测试'],
            '数据库': ['SQL', '查询', '索引', '事务', '存储过程', '触发器', '视图', '表'],
            '网络技术': ['HTTP', 'TCP/IP', 'REST', 'WebSocket', 'SSL', 'DNS', '负载均衡'],
            '人工智能': ['机器学习', '深度学习', '神经网络', '自然语言处理', '计算机视觉'],
            '云计算': ['容器', 'Docker', 'Kubernetes', '微服务', '分布式', '集群'],
            '前端开发': ['HTML', 'CSS', 'JavaScript', 'React', 'Vue', '响应式设计'],
            '后端开发': ['服务器', '中间件', '缓存', '消息队列', '数据库连接池']
        }
        
        # 成语和习语词典
        self.idioms = [
            '一举两得', '事半功倍', '精益求精', '持之以恒', '循序渐进',
            '举一反三', '融会贯通', '温故知新', '学以致用', '实事求是',
            '精雕细琢', '千锤百炼', '百尺竿头', '更进一步', '锦上添花'
        ]
        
        # 文化引用词典
        self.cultural_references = [
            '孔子', '老子', '庄子', '孟子', '诸子百家', '四书五经',
            '唐诗宋词', '红楼梦', '西游记', '水浒传', '三国演义',
            '春节', '中秋节', '端午节', '清明节', '重阳节',
            '太极', '阴阳', '五行', '八卦', '风水', '中医'
        ]
        
        # 网络用语词典
        self.internet_slang = [
            '666', '233', '哈哈哈', '呵呵', '嗯嗯', '好的',
            '点赞', '转发', '评论', '私信', '关注', '粉丝',
            '网红', '直播', '短视频', '弹幕', '刷屏', '热搜'
        ]
        
        self.logger.info("Chinese content router initialized")
    
    def analyze_chinese_content(self, content: str) -> ChineseContentAnalysis:
        """
        分析中文内容特征
        
        Args:
            content: 待分析的文本内容
            
        Returns:
            ChineseContentAnalysis: 中文内容分析结果
        """
        try:
            # 1. 基础字符分析
            chinese_ratio = self._calculate_chinese_ratio(content)
            traditional_ratio = self._calculate_traditional_ratio(content)
            
            # 2. 内容类型识别
            content_type = self._identify_content_type(content, traditional_ratio)
            
            # 3. 复杂度分析
            complexity = self._analyze_complexity(content)
            
            # 4. 文化背景识别
            cultural_context = self._identify_cultural_context(content, traditional_ratio)
            
            # 5. 技术术语提取
            technical_terms = self._extract_technical_terms(content)
            
            # 6. 文化引用识别
            cultural_references = self._identify_cultural_references(content)
            
            # 7. 正式程度评估
            formality_level = self._assess_formality_level(content)
            
            # 8. 语言特征分析
            has_idioms = self._detect_idioms(content)
            has_classical_chinese = self._detect_classical_chinese(content)
            has_regional_dialect = self._detect_regional_dialect(content)
            has_internet_slang = self._detect_internet_slang(content)
            
            # 9. 专业领域识别
            domain = self._identify_domain(content, technical_terms)
            industry_terms = self._extract_industry_terms(content, domain)
            
            # 10. 计算置信度
            confidence_score = self._calculate_confidence_score(
                chinese_ratio, len(technical_terms), len(cultural_references)
            )
            
            analysis = ChineseContentAnalysis(
                content_type=content_type,
                complexity=complexity,
                cultural_context=cultural_context,
                chinese_ratio=chinese_ratio,
                traditional_ratio=traditional_ratio,
                technical_terms=technical_terms,
                cultural_references=cultural_references,
                formality_level=formality_level,
                confidence_score=confidence_score,
                has_idioms=has_idioms,
                has_classical_chinese=has_classical_chinese,
                has_regional_dialect=has_regional_dialect,
                has_internet_slang=has_internet_slang,
                domain=domain,
                industry_terms=industry_terms
            )
            
            self.logger.debug(f"Chinese content analysis completed: {analysis}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing Chinese content: {e}")
            # 返回默认分析结果
            return ChineseContentAnalysis(
                content_type=ChineseContentType.SIMPLIFIED_CHINESE,
                complexity=ChineseComplexity.MODERATE,
                cultural_context=CulturalContext.GENERAL,
                chinese_ratio=0.5,
                traditional_ratio=0.0,
                technical_terms=[],
                cultural_references=[],
                formality_level=0.5,
                confidence_score=0.3
            )
    
    def route_chinese_content(self, content: str, 
                            available_providers: List[str],
                            priority: str = "quality") -> ChineseRoutingDecision:
        """
        为中文内容选择最优AI提供商
        
        Args:
            content: 中文内容
            available_providers: 可用的AI提供商列表
            priority: 优先级策略 ("quality", "cost", "speed")
            
        Returns:
            ChineseRoutingDecision: 中文路由决策结果
        """
        try:
            # 1. 分析中文内容
            analysis = self.analyze_chinese_content(content)
            
            # 2. 计算每个提供商的适配分数
            provider_scores = {}
            for provider in available_providers:
                if provider in self.chinese_provider_capabilities:
                    score = self._calculate_provider_score(provider, analysis, priority)
                    provider_scores[provider] = score
            
            if not provider_scores:
                # 如果没有中文优化的提供商，返回默认选择
                return ChineseRoutingDecision(
                    recommended_provider=available_providers[0] if available_providers else "openai",
                    confidence=0.3,
                    reasoning="No Chinese-optimized providers available, using default",
                    optimization_strategy="basic",
                    cultural_adaptations=[],
                    language_enhancements=[],
                    estimated_quality_score=0.5
                )
            
            # 3. 选择最佳提供商
            best_provider = max(provider_scores.keys(), key=lambda p: provider_scores[p])
            best_score = provider_scores[best_provider]
            
            # 4. 生成优化策略
            optimization_strategy = self._generate_optimization_strategy(analysis, best_provider)
            
            # 5. 生成文化适配建议
            cultural_adaptations = self._generate_cultural_adaptations(analysis, best_provider)
            
            # 6. 生成语言增强建议
            language_enhancements = self._generate_language_enhancements(analysis, best_provider)
            
            # 7. 生成推理说明
            reasoning = self._generate_routing_reasoning(
                analysis, best_provider, best_score, priority
            )
            
            # 8. 估算质量分数
            estimated_quality_score = self._estimate_quality_score(
                analysis, best_provider, best_score
            )
            
            decision = ChineseRoutingDecision(
                recommended_provider=best_provider,
                confidence=min(best_score, 1.0),
                reasoning=reasoning,
                optimization_strategy=optimization_strategy,
                cultural_adaptations=cultural_adaptations,
                language_enhancements=language_enhancements,
                estimated_quality_score=estimated_quality_score
            )
            
            self.logger.info(
                f"Chinese content routing decision: {best_provider} "
                f"(score: {best_score:.3f}, confidence: {decision.confidence:.3f})"
            )
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error routing Chinese content: {e}")
            # 返回默认决策
            return ChineseRoutingDecision(
                recommended_provider="baidu_wenxin",
                confidence=0.5,
                reasoning=f"Error in routing: {str(e)}, using default Chinese provider",
                optimization_strategy="basic",
                cultural_adaptations=[],
                language_enhancements=[],
                estimated_quality_score=0.6
            )
    
    def _calculate_chinese_ratio(self, content: str) -> float:
        """计算中文字符占比"""
        if not content:
            return 0.0
        
        chinese_count = 0
        total_count = len(content)
        
        for char in content:
            char_code = ord(char)
            for start, end in self.chinese_char_ranges:
                if start <= char_code <= end:
                    chinese_count += 1
                    break
        
        return chinese_count / total_count if total_count > 0 else 0.0
    
    def _calculate_traditional_ratio(self, content: str) -> float:
        """计算繁体字占比"""
        if not content:
            return 0.0
        
        traditional_count = sum(1 for char in content if char in self.traditional_chars)
        chinese_count = sum(1 for char in content 
                          if any(start <= ord(char) <= end for start, end in self.chinese_char_ranges))
        
        return traditional_count / chinese_count if chinese_count > 0 else 0.0
    
    def _identify_content_type(self, content: str, traditional_ratio: float) -> ChineseContentType:
        """识别中文内容类型"""
        chinese_ratio = self._calculate_chinese_ratio(content)
        
        # 判断繁简体
        if traditional_ratio > 0.3:
            return ChineseContentType.TRADITIONAL_CHINESE
        elif chinese_ratio > 0.8:
            return ChineseContentType.SIMPLIFIED_CHINESE
        elif 0.3 < chinese_ratio <= 0.8:
            return ChineseContentType.MIXED_CHINESE
        
        # 判断专业类型
        if any(term in content for domain_terms in self.technical_terms.values() 
               for term in domain_terms):
            return ChineseContentType.TECHNICAL_CHINESE
        
        # 判断正式程度
        formal_indicators = ['您', '敬请', '恭请', '谨此', '特此', '兹有']
        if any(indicator in content for indicator in formal_indicators):
            return ChineseContentType.FORMAL_CHINESE
        
        # 判断文学性
        if any(ref in content for ref in self.cultural_references):
            return ChineseContentType.LITERARY_CHINESE
        
        # 默认为日常中文
        return ChineseContentType.CASUAL_CHINESE
    
    def _analyze_complexity(self, content: str) -> ChineseComplexity:
        """分析内容复杂度"""
        content_length = len(content)
        
        # 基于长度的基础复杂度
        if content_length < 50:
            base_complexity = ChineseComplexity.SIMPLE
        elif content_length < 200:
            base_complexity = ChineseComplexity.MODERATE
        elif content_length < 500:
            base_complexity = ChineseComplexity.COMPLEX
        else:
            base_complexity = ChineseComplexity.VERY_COMPLEX
        
        # 基于内容特征调整复杂度
        complexity_indicators = {
            '因此': 1, '所以': 1, '然而': 1, '但是': 1, '不过': 1,
            '首先': 1, '其次': 1, '最后': 1, '总之': 1, '综上所述': 2,
            '根据': 1, '基于': 1, '通过': 1, '利用': 1, '采用': 1,
            '分析': 2, '研究': 2, '探讨': 2, '论证': 2, '阐述': 2
        }
        
        complexity_score = sum(
            complexity_indicators.get(word, 0) 
            for word in complexity_indicators.keys() 
            if word in content
        )
        
        # 调整复杂度等级
        if complexity_score >= 10:
            return ChineseComplexity.VERY_COMPLEX
        elif complexity_score >= 5:
            return ChineseComplexity.COMPLEX
        elif complexity_score >= 2:
            return ChineseComplexity.MODERATE
        else:
            return base_complexity
    
    def _identify_cultural_context(self, content: str, traditional_ratio: float) -> CulturalContext:
        """识别文化背景"""
        # 基于繁体字比例判断
        if traditional_ratio > 0.5:
            # 检查特定地区用词
            if any(word in content for word in ['係', '喺', '嘅', '咗']):
                return CulturalContext.HONG_KONG
            elif any(word in content for word in ['欸', '蛤', '捏']):
                return CulturalContext.TAIWAN
            else:
                return CulturalContext.TAIWAN  # 默认台湾
        
        # 检查新加坡特色用词
        singapore_terms = ['巴刹', '组屋', '咖啡店', '小贩中心']
        if any(term in content for term in singapore_terms):
            return CulturalContext.SINGAPORE
        
        # 检查大陆特色用词
        mainland_terms = ['同志', '单位', '爱人', '师傅', '小区']
        if any(term in content for term in mainland_terms):
            return CulturalContext.MAINLAND_CHINA
        
        return CulturalContext.GENERAL
    
    def _extract_technical_terms(self, content: str) -> List[str]:
        """提取技术术语"""
        found_terms = []
        
        for domain, terms in self.technical_terms.items():
            for term in terms:
                if term in content and term not in found_terms:
                    found_terms.append(term)
        
        return found_terms
    
    def _identify_cultural_references(self, content: str) -> List[str]:
        """识别文化引用"""
        found_references = []
        
        for reference in self.cultural_references:
            if reference in content and reference not in found_references:
                found_references.append(reference)
        
        return found_references
    
    def _assess_formality_level(self, content: str) -> float:
        """评估正式程度"""
        formal_indicators = [
            '您', '敬请', '恭请', '谨此', '特此', '兹有', '据悉', '获悉',
            '贵公司', '贵方', '本公司', '本方', '阁下', '先生', '女士'
        ]
        
        informal_indicators = [
            '你', '咱们', '哥们', '姐们', '亲', '宝贝', '哈哈', '嘿嘿',
            '啊', '呀', '哦', '嗯', '哎', '唉', '咦', '哇'
        ]
        
        formal_count = sum(1 for indicator in formal_indicators if indicator in content)
        informal_count = sum(1 for indicator in informal_indicators if indicator in content)
        
        total_indicators = formal_count + informal_count
        if total_indicators == 0:
            return 0.5  # 中性
        
        return formal_count / total_indicators
    
    def _detect_idioms(self, content: str) -> bool:
        """检测成语"""
        return any(idiom in content for idiom in self.idioms)
    
    def _detect_classical_chinese(self, content: str) -> bool:
        """检测文言文"""
        classical_indicators = ['之', '乎', '者', '也', '矣', '焉', '哉', '耳']
        classical_count = sum(1 for indicator in classical_indicators if indicator in content)
        return classical_count >= 3
    
    def _detect_regional_dialect(self, content: str) -> bool:
        """检测方言"""
        dialect_words = ['係', '喺', '嘅', '咗', '啲', '嚟', '去', '咁']
        return any(word in content for word in dialect_words)
    
    def _detect_internet_slang(self, content: str) -> bool:
        """检测网络用语"""
        return any(slang in content for slang in self.internet_slang)
    
    def _identify_domain(self, content: str, technical_terms: List[str]) -> Optional[str]:
        """识别专业领域"""
        domain_scores = {}
        
        for domain, terms in self.technical_terms.items():
            score = sum(1 for term in technical_terms if term in terms)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores.keys(), key=lambda d: domain_scores[d])
        
        return None
    
    def _extract_industry_terms(self, content: str, domain: Optional[str]) -> List[str]:
        """提取行业术语"""
        if not domain or domain not in self.technical_terms:
            return []
        
        industry_terms = []
        for term in self.technical_terms[domain]:
            if term in content and term not in industry_terms:
                industry_terms.append(term)
        
        return industry_terms
    
    def _calculate_confidence_score(self, chinese_ratio: float, 
                                  tech_terms_count: int, 
                                  cultural_refs_count: int) -> float:
        """计算分析置信度"""
        # 基础置信度基于中文比例
        base_confidence = chinese_ratio
        
        # 技术术语和文化引用增加置信度
        term_bonus = min(tech_terms_count * 0.1, 0.3)
        cultural_bonus = min(cultural_refs_count * 0.05, 0.2)
        
        confidence = base_confidence + term_bonus + cultural_bonus
        return min(confidence, 1.0)
    
    def _calculate_provider_score(self, provider: str, 
                                analysis: ChineseContentAnalysis, 
                                priority: str) -> float:
        """计算提供商适配分数"""
        capabilities = self.chinese_provider_capabilities[provider]
        
        # 基础分数
        base_score = capabilities["chinese_understanding"]
        
        # 根据内容类型调整
        if analysis.content_type == ChineseContentType.TRADITIONAL_CHINESE:
            base_score *= capabilities["traditional_chinese"]
        elif analysis.content_type == ChineseContentType.SIMPLIFIED_CHINESE:
            base_score *= capabilities["simplified_chinese"]
        elif analysis.content_type == ChineseContentType.TECHNICAL_CHINESE:
            base_score *= capabilities["technical_chinese"]
        elif analysis.content_type == ChineseContentType.BUSINESS_CHINESE:
            base_score *= capabilities["business_chinese"]
        elif analysis.content_type == ChineseContentType.LITERARY_CHINESE:
            base_score *= capabilities["literary_chinese"]
        
        # 根据文化背景调整
        if analysis.cultural_context == CulturalContext.MAINLAND_CHINA:
            base_score *= capabilities["mainland_culture"]
        
        # 根据语言特征调整
        if analysis.has_idioms:
            base_score *= capabilities["idiom_usage"]
        
        if analysis.formality_level > 0.7:
            base_score *= capabilities["formal_language"]
        
        # 根据优先级策略调整
        if priority == "cost":
            base_score *= capabilities["cost_efficiency"]
        elif priority == "quality":
            base_score *= capabilities["cultural_context"]
        
        return base_score
    
    def _generate_optimization_strategy(self, analysis: ChineseContentAnalysis, 
                                      provider: str) -> str:
        """生成优化策略"""
        strategies = []
        
        if analysis.content_type == ChineseContentType.TRADITIONAL_CHINESE:
            strategies.append("traditional_chinese_optimization")
        
        if analysis.complexity == ChineseComplexity.VERY_COMPLEX:
            strategies.append("complex_reasoning_enhancement")
        
        if analysis.has_idioms:
            strategies.append("idiom_context_preservation")
        
        if analysis.domain:
            strategies.append(f"domain_specific_optimization_{analysis.domain}")
        
        if analysis.cultural_context != CulturalContext.GENERAL:
            strategies.append(f"cultural_adaptation_{analysis.cultural_context.value}")
        
        return ",".join(strategies) if strategies else "basic_chinese_optimization"
    
    def _generate_cultural_adaptations(self, analysis: ChineseContentAnalysis, 
                                     provider: str) -> List[str]:
        """生成文化适配建议"""
        adaptations = []
        
        if analysis.cultural_context == CulturalContext.MAINLAND_CHINA:
            adaptations.extend([
                "使用大陆地区常用表达方式",
                "采用简体中文输出",
                "考虑大陆文化背景和价值观"
            ])
        elif analysis.cultural_context == CulturalContext.TAIWAN:
            adaptations.extend([
                "使用台湾地区常用词汇",
                "保持繁体中文格式",
                "考虑台湾文化特色"
            ])
        elif analysis.cultural_context == CulturalContext.HONG_KONG:
            adaptations.extend([
                "使用香港地区表达习惯",
                "保持繁体中文和粤语特色",
                "考虑香港文化背景"
            ])
        
        if analysis.has_classical_chinese:
            adaptations.append("保持文言文风格和韵味")
        
        if analysis.has_idioms:
            adaptations.append("准确理解和使用成语典故")
        
        return adaptations
    
    def _generate_language_enhancements(self, analysis: ChineseContentAnalysis, 
                                      provider: str) -> List[str]:
        """生成语言增强建议"""
        enhancements = []
        
        if analysis.formality_level > 0.7:
            enhancements.extend([
                "保持正式语言风格",
                "使用敬语和礼貌用词",
                "避免口语化表达"
            ])
        elif analysis.formality_level < 0.3:
            enhancements.extend([
                "使用亲切自然的表达",
                "适当使用口语化词汇",
                "保持轻松友好的语调"
            ])
        
        if analysis.domain:
            enhancements.append(f"准确使用{analysis.domain}领域专业术语")
        
        if analysis.complexity == ChineseComplexity.VERY_COMPLEX:
            enhancements.extend([
                "保持逻辑清晰的表达结构",
                "使用准确的专业词汇",
                "提供详细的解释说明"
            ])
        
        if analysis.has_internet_slang:
            enhancements.append("理解并适当使用网络流行语")
        
        return enhancements
    
    def _generate_routing_reasoning(self, analysis: ChineseContentAnalysis, 
                                  provider: str, score: float, priority: str) -> str:
        """生成路由推理说明"""
        reasons = []
        
        # 基础推理
        reasons.append(f"选择{provider}作为中文内容处理提供商")
        
        # 内容特征推理
        if analysis.content_type == ChineseContentType.TRADITIONAL_CHINESE:
            reasons.append("内容包含繁体中文，选择繁体中文支持较好的模型")
        elif analysis.content_type == ChineseContentType.TECHNICAL_CHINESE:
            reasons.append("内容包含技术术语，选择技术中文处理能力强的模型")
        
        # 文化背景推理
        if analysis.cultural_context == CulturalContext.MAINLAND_CHINA:
            reasons.append("内容具有大陆文化背景，选择大陆文化理解能力强的模型")
        
        # 复杂度推理
        if analysis.complexity == ChineseComplexity.VERY_COMPLEX:
            reasons.append("内容复杂度较高，选择理解能力强的高级模型")
        
        # 优先级推理
        if priority == "cost":
            reasons.append("优先考虑成本效益")
        elif priority == "quality":
            reasons.append("优先考虑输出质量")
        
        # 分数推理
        reasons.append(f"综合评分: {score:.3f}")
        
        return "；".join(reasons)
    
    def _estimate_quality_score(self, analysis: ChineseContentAnalysis, 
                              provider: str, score: float) -> float:
        """估算质量分数"""
        base_quality = score
        
        # 根据内容特征调整质量预期
        if analysis.chinese_ratio > 0.9:
            base_quality *= 1.1  # 纯中文内容质量更高
        
        if analysis.has_idioms or analysis.has_classical_chinese:
            base_quality *= 0.95  # 成语和文言文处理难度较高
        
        if analysis.complexity == ChineseComplexity.VERY_COMPLEX:
            base_quality *= 0.9  # 复杂内容质量可能略低
        
        if analysis.domain and len(analysis.technical_terms) > 5:
            base_quality *= 0.95  # 专业术语较多时质量可能略低
        
        return min(base_quality, 1.0)
    
    def get_chinese_provider_ranking(self, content: str, 
                                   available_providers: List[str]) -> List[Tuple[str, float]]:
        """
        获取中文提供商排名
        
        Args:
            content: 中文内容
            available_providers: 可用提供商列表
            
        Returns:
            List[Tuple[str, float]]: 提供商和分数的排名列表
        """
        analysis = self.analyze_chinese_content(content)
        
        provider_scores = []
        for provider in available_providers:
            if provider in self.chinese_provider_capabilities:
                score = self._calculate_provider_score(provider, analysis, "quality")
                provider_scores.append((provider, score))
        
        # 按分数降序排序
        provider_scores.sort(key=lambda x: x[1], reverse=True)
        
        return provider_scores
    
    def is_chinese_content(self, content: str, threshold: float = 0.3) -> bool:
        """
        判断是否为中文内容
        
        Args:
            content: 待判断的内容
            threshold: 中文字符比例阈值
            
        Returns:
            bool: 是否为中文内容
        """
        chinese_ratio = self._calculate_chinese_ratio(content)
        return chinese_ratio >= threshold
    
    def get_optimization_suggestions(self, content: str, provider: str) -> Dict[str, Any]:
        """
        获取中文内容优化建议
        
        Args:
            content: 中文内容
            provider: AI提供商
            
        Returns:
            Dict[str, Any]: 优化建议
        """
        analysis = self.analyze_chinese_content(content)
        
        suggestions = {
            "content_analysis": {
                "type": analysis.content_type.value,
                "complexity": analysis.complexity.value,
                "cultural_context": analysis.cultural_context.value,
                "chinese_ratio": analysis.chinese_ratio,
                "confidence": analysis.confidence_score
            },
            "provider_optimization": {
                "recommended_provider": provider,
                "optimization_strategy": self._generate_optimization_strategy(analysis, provider),
                "cultural_adaptations": self._generate_cultural_adaptations(analysis, provider),
                "language_enhancements": self._generate_language_enhancements(analysis, provider)
            },
            "quality_expectations": {
                "estimated_score": self._estimate_quality_score(analysis, provider, 0.8),
                "key_challenges": self._identify_processing_challenges(analysis),
                "success_factors": self._identify_success_factors(analysis, provider)
            }
        }
        
        return suggestions
    
    def _identify_processing_challenges(self, analysis: ChineseContentAnalysis) -> List[str]:
        """识别处理挑战"""
        challenges = []
        
        if analysis.has_classical_chinese:
            challenges.append("文言文理解和现代化表达")
        
        if analysis.has_idioms:
            challenges.append("成语典故的准确理解和运用")
        
        if analysis.traditional_ratio > 0.5:
            challenges.append("繁体中文的准确处理")
        
        if analysis.complexity == ChineseComplexity.VERY_COMPLEX:
            challenges.append("复杂逻辑结构的理解")
        
        if len(analysis.technical_terms) > 10:
            challenges.append("大量专业术语的准确处理")
        
        if analysis.has_regional_dialect:
            challenges.append("方言词汇的理解和转换")
        
        return challenges
    
    def _identify_success_factors(self, analysis: ChineseContentAnalysis, 
                                provider: str) -> List[str]:
        """识别成功因素"""
        factors = []
        
        capabilities = self.chinese_provider_capabilities.get(provider, {})
        
        if capabilities.get("chinese_understanding", 0) > 0.9:
            factors.append("强大的中文理解能力")
        
        if analysis.cultural_context == CulturalContext.MAINLAND_CHINA and \
           capabilities.get("mainland_culture", 0) > 0.9:
            factors.append("优秀的大陆文化背景理解")
        
        if analysis.domain and capabilities.get("technical_chinese", 0) > 0.85:
            factors.append("良好的技术中文处理能力")
        
        if analysis.formality_level > 0.7 and capabilities.get("formal_language", 0) > 0.85:
            factors.append("正式语言风格的准确把握")
        
        return factors