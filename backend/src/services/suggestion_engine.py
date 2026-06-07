"""
AI建议引擎服务 - 智能建议生成和管理

本模块实现了AI建议引擎的核心功能，包括：
1. 项目状况分析算法
2. 需求质量分析功能  
3. 测试覆盖率分析
4. 风险识别模块
5. 智能建议生成和评估

技术特性：
- 基于AI的智能分析算法
- 多维度质量评估体系
- 可配置的建议生成规则
- 优先级智能排序
- 建议可行性评估
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..models.ai_suggestion import (
    AISuggestion, AIRequirementsAnalysis, AIRequirementsSuggestion,
    SuggestionType, SuggestionStatus, SuggestionPriority, SuggestionCategory
)

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class ProjectContext:
    """项目上下文数据"""
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    team_size: Optional[int] = None
    timeline: Optional[Dict] = None
    requirements: Optional[List[Dict]] = None
    test_data: Optional[Dict] = None
    quality_metrics: Optional[Dict] = None


@dataclass
class RequirementsData:
    """需求数据结构"""
    requirements: List[Dict]
    total_count: int
    categories: List[str]
    priorities: List[str]


@dataclass
class RequirementsQualityAnalysis:
    """需求质量分析结果"""
    completeness_score: float = 0.0
    clarity_score: float = 0.0
    consistency_score: float = 0.0
    testability_score: float = 0.0
    overall_score: float = 0.0
    problematic_requirements: List[Dict] = None
    
    def __post_init__(self):
        if self.problematic_requirements is None:
            self.problematic_requirements = []


@dataclass
class ProblematicRequirement:
    """问题需求"""
    requirement_id: int
    requirement_title: str
    issues: List[str]
    severity: str


@dataclass
class FunctionalCoverageAnalysis:
    """功能覆盖度分析"""
    expected_areas: List[str]
    current_areas: List[str]
    missing_areas: List[str]
    coverage_rate: float


@dataclass
class NonFunctionalCoverageAnalysis:
    """非功能需求覆盖度分析"""
    required_types: List[str]
    current_types: List[str]
    missing_types: List[str]
    coverage_rate: float


@dataclass
class TestContext:
    """测试上下文"""
    existing_tests: List[Dict]
    requirements: List[Dict]
    coverage_data: Optional[Dict] = None


@dataclass
class TestCoverageAnalysis:
    """测试覆盖率分析结果"""
    overall_coverage_rate: float = 0.0
    requirement_coverage_rate: float = 0.0
    functional_coverage_rate: float = 0.0
    scenario_coverage_rate: float = 0.0
    uncovered_requirements: List[Dict] = None
    uncovered_scenarios: List[str] = None
    coverage_gaps: List[Dict] = None
    coverage_recommendations: List[str] = None
    
    def __post_init__(self):
        if self.uncovered_requirements is None:
            self.uncovered_requirements = []
        if self.uncovered_scenarios is None:
            self.uncovered_scenarios = []
        if self.coverage_gaps is None:
            self.coverage_gaps = []
        if self.coverage_recommendations is None:
            self.coverage_recommendations = []


@dataclass
class TestCoverageMetrics:
    """测试覆盖率指标"""
    total_requirements: int = 0
    covered_requirements: int = 0
    total_scenarios: int = 0
    covered_scenarios: int = 0
    test_case_count: int = 0
    automated_test_count: int = 0
    manual_test_count: int = 0


@dataclass
class CoverageGap:
    """覆盖度缺口"""
    requirement_id: int
    requirement_description: str
    missing_scenarios: List[str]
    existing_tests: List[str]


@dataclass
class TestSuggestion:
    """测试建议"""
    title: str
    description: str
    test_steps: List[str]
    expected_result: str
    priority: str
    rationale: str


@dataclass
class OptimizationContext:
    """优化上下文"""
    performance_metrics: Dict
    resource_usage: Dict
    bottlenecks: List[str]


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    title: str
    description: str
    optimization_type: str
    expected_improvement: str
    implementation_steps: List[str]
    priority: str


class SuggestionEngine:
    """
    智能建议引擎
    
    核心功能：
    1. 项目状况分析 - 分析项目健康度、团队能力、进度状态
    2. 需求质量分析 - 评估需求完整性、清晰度、可测试性
    3. 测试覆盖分析 - 识别测试缺口，生成测试建议
    4. 风险识别 - 识别项目风险点，提供缓解建议
    5. 智能建议生成 - 基于分析结果生成可行的改进建议
    """
    
    def __init__(self, db: AsyncSession, ai_service=None):
        """
        初始化建议引擎
        
        Args:
            db: 数据库会话
            ai_service: AI服务实例（用于AI分析）
        """
        self.db = db
        self.ai_service = ai_service
        self.logger = logging.getLogger(__name__)
        
        # 建议生成配置
        self.config = {
            "min_completeness_score": 0.7,
            "min_clarity_score": 0.7,
            "min_testability_score": 0.6,
            "max_suggestions_per_category": 5,
            "priority_weights": {
                "CRITICAL": 1.0,
                "HIGH": 0.8,
                "MEDIUM": 0.6,
                "LOW": 0.4
            }
        }
        
        # 项目类型与功能领域映射
        self.project_functional_areas = {
            "web_application": [
                "用户认证", "用户管理", "数据管理", "界面交互", 
                "API接口", "数据存储", "安全控制", "性能优化"
            ],
            "mobile_app": [
                "用户界面", "数据同步", "离线功能", "推送通知",
                "设备集成", "性能优化", "安全认证", "用户体验"
            ],
            "api_service": [
                "接口设计", "数据处理", "认证授权", "错误处理",
                "性能优化", "监控日志", "版本管理", "文档管理"
            ],
            "data_platform": [
                "数据采集", "数据处理", "数据存储", "数据分析",
                "数据可视化", "数据安全", "性能监控", "运维管理"
            ]
        }
    
    async def generate_project_suggestions(self, context: ProjectContext) -> List[Dict]:
        """
        生成项目级别的智能建议
        
        Args:
            context: 项目上下文数据
            
        Returns:
            List[Dict]: 建议列表
        """
        try:
            self.logger.info(f"Generating project suggestions for project {context.project_id}")
            
            suggestions = []
            
            # 1. 需求相关建议
            if context.requirements:
                requirements_suggestions = await self.generate_requirements_suggestions(context)
                suggestions.extend(requirements_suggestions)
            
            # 2. 测试相关建议
            if context.test_data:
                test_context = TestContext(
                    existing_tests=context.test_data.get("test_cases", []),
                    requirements=context.requirements or [],
                    coverage_data=context.test_data.get("coverage", {})
                )
                
                # 生成测试建议
                test_suggestions = await self.generate_test_suggestions(test_context)
                suggestions.extend([self._convert_test_suggestion_to_dict(s) for s in test_suggestions])
                
                # 生成测试覆盖率分析建议
                coverage_analysis = await self._calculate_test_coverage({
                    "test_cases": context.test_data.get("test_cases", []),
                    "requirements": context.requirements or [],
                    "coverage": context.test_data.get("coverage", {})
                })
                coverage_suggestions = await self._generate_test_coverage_suggestions(coverage_analysis)
                suggestions.extend(coverage_suggestions)
            
            # 3. 质量相关建议
            if context.quality_metrics:
                quality_suggestions = await self.generate_quality_suggestions(context)
                suggestions.extend(quality_suggestions)
            
            # 4. 风险识别和缓解建议
            risk_suggestions = await self.generate_risk_based_suggestions(context)
            suggestions.extend(risk_suggestions)
            
            # 5. 项目管理建议
            management_suggestions = await self.generate_project_management_suggestions(context)
            suggestions.extend(management_suggestions)
            
            # 6. 按优先级排序
            sorted_suggestions = await self._sort_suggestions_by_priority(suggestions)
            
            self.logger.info(f"Generated {len(sorted_suggestions)} project suggestions")
            return sorted_suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating project suggestions: {str(e)}", exc_info=True)
            return []
    
    async def generate_requirements_suggestions(self, context: ProjectContext) -> List[Dict]:
        """
        生成需求相关建议
        
        Args:
            context: 项目上下文
            
        Returns:
            List[Dict]: 需求建议列表
        """
        try:
            suggestions = []
            
            if not context.requirements:
                return suggestions
            
            # 构建需求数据
            requirements_data = RequirementsData(
                requirements=context.requirements,
                total_count=len(context.requirements),
                categories=[req.get("category", "未分类") for req in context.requirements],
                priorities=[req.get("priority", "MEDIUM") for req in context.requirements]
            )
            
            # 分析需求质量
            quality_analysis = await self._analyze_requirements_quality(requirements_data)
            
            # 生成质量改进建议
            quality_suggestions = await self._generate_requirements_quality_suggestions(quality_analysis)
            suggestions.extend(quality_suggestions)
            
            # 生成覆盖度建议
            coverage_suggestions = await self._generate_requirements_coverage_suggestions(context)
            suggestions.extend(coverage_suggestions)
            
            # 生成流程建议
            process_suggestions = await self._generate_requirements_process_suggestions(context)
            suggestions.extend(process_suggestions)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating requirements suggestions: {str(e)}", exc_info=True)
            return []
    
    async def generate_test_suggestions(self, context: TestContext) -> List[TestSuggestion]:
        """
        生成测试建议
        
        Args:
            context: 测试上下文
            
        Returns:
            List[TestSuggestion]: 测试建议列表
        """
        try:
            self.logger.info("Generating test suggestions")
            
            suggestions = []
            
            # 执行全面的测试覆盖率分析
            if context.coverage_data:
                coverage_analysis = await self._calculate_test_coverage({
                    "test_cases": context.existing_tests,
                    "requirements": context.requirements,
                    "coverage": context.coverage_data
                })
                
                # 基于覆盖率分析生成建议
                coverage_suggestions = await self._generate_coverage_based_suggestions(coverage_analysis)
                suggestions.extend(coverage_suggestions)
            
            # 分析测试覆盖率缺口（保持向后兼容）
            coverage_gaps = await self._analyze_coverage_gaps(context.existing_tests, context.requirements)
            
            # 为每个缺口生成测试建议
            for gap in coverage_gaps:
                suggestion = await self._generate_test_suggestion(gap)
                if suggestion:
                    suggestions.append(suggestion)
            
            # 按优先级排序
            suggestions.sort(key=lambda x: self._get_priority_weight(x.priority), reverse=True)
            
            self.logger.info(f"Generated {len(suggestions)} test suggestions")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating test suggestions: {str(e)}", exc_info=True)
            return []
    
    async def _generate_coverage_based_suggestions(self, coverage_analysis: TestCoverageAnalysis) -> List[TestSuggestion]:
        """
        基于覆盖率分析生成测试建议
        
        Args:
            coverage_analysis: 测试覆盖率分析结果
            
        Returns:
            List[TestSuggestion]: 测试建议列表
        """
        try:
            suggestions = []
            
            # 基于未覆盖需求生成建议
            for uncovered_req in coverage_analysis.uncovered_requirements:
                suggestion = TestSuggestion(
                    title=f"为需求'{uncovered_req['title']}'添加测试用例",
                    description=f"需求ID {uncovered_req['id']} 尚未被任何测试用例覆盖",
                    test_steps=[
                        "分析需求的功能点和验收标准",
                        "设计正常流程测试用例",
                        "设计异常流程测试用例",
                        "设计边界值测试用例",
                        "执行测试并验证结果"
                    ],
                    expected_result="需求功能得到全面测试覆盖",
                    priority="HIGH" if uncovered_req.get("priority") in ["HIGH", "CRITICAL"] else "MEDIUM",
                    rationale=f"优先级为{uncovered_req.get('priority', 'MEDIUM')}的需求缺少测试覆盖"
                )
                suggestions.append(suggestion)
            
            # 基于未覆盖场景生成建议
            if coverage_analysis.uncovered_scenarios:
                for scenario in coverage_analysis.uncovered_scenarios[:5]:  # 限制数量
                    suggestion = TestSuggestion(
                        title=f"补充{scenario}测试场景",
                        description=f"当前测试用例中缺少{scenario}相关的测试覆盖",
                        test_steps=[
                            f"识别需要{scenario}测试的功能点",
                            f"设计{scenario}测试用例",
                            "准备测试数据和环境",
                            "执行测试并记录结果"
                        ],
                        expected_result=f"{scenario}得到充分测试",
                        priority="MEDIUM",
                        rationale=f"提升{scenario}测试覆盖率"
                    )
                    suggestions.append(suggestion)
            
            # 基于覆盖率缺口生成建议
            high_risk_gaps = [gap for gap in coverage_analysis.coverage_gaps 
                            if gap.get("risk_level") == "HIGH"]
            for gap in high_risk_gaps[:3]:  # 限制数量
                suggestion = TestSuggestion(
                    title=f"紧急补充需求{gap['requirement_id']}的测试覆盖",
                    description=f"高风险需求'{gap['requirement_title']}'完全缺少测试覆盖",
                    test_steps=[
                        "立即分析需求的关键功能点",
                        "优先创建核心功能测试用例",
                        "补充异常处理测试用例",
                        "进行回归测试确保质量"
                    ],
                    expected_result="高风险需求得到基本测试保障",
                    priority="CRITICAL",
                    rationale="高风险需求缺少测试覆盖，存在质量风险"
                )
                suggestions.append(suggestion)
            
            # 基于覆盖率建议生成测试建议
            for recommendation in coverage_analysis.coverage_recommendations:
                if "补充" in recommendation or "创建" in recommendation:
                    suggestion = TestSuggestion(
                        title="改善测试覆盖率",
                        description=recommendation,
                        test_steps=[
                            "分析当前测试覆盖情况",
                            "识别覆盖率薄弱环节",
                            "制定测试补充计划",
                            "逐步实施测试用例补充"
                        ],
                        expected_result="测试覆盖率得到显著提升",
                        priority="MEDIUM",
                        rationale="基于覆盖率分析的改进建议"
                    )
                    suggestions.append(suggestion)
                    break  # 只添加一个总体建议
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating coverage-based suggestions: {str(e)}")
            return []
    
    async def _generate_test_coverage_suggestions(self, coverage_analysis: TestCoverageAnalysis) -> List[Dict]:
        """
        生成测试覆盖率改进建议
        
        Args:
            coverage_analysis: 测试覆盖率分析结果
            
        Returns:
            List[Dict]: 覆盖率改进建议列表
        """
        try:
            suggestions = []
            
            # 总体覆盖率建议
            if coverage_analysis.overall_coverage_rate < 0.6:
                suggestions.append({
                    "type": "TEST_COVERAGE_IMPROVEMENT",
                    "category": "OVERALL_COVERAGE",
                    "title": "提升整体测试覆盖率",
                    "description": f"当前整体测试覆盖率为{coverage_analysis.overall_coverage_rate:.1%}，低于建议的60%标准",
                    "priority": "HIGH",
                    "action_items": [
                        "制定测试覆盖率提升计划",
                        "优先为核心功能补充测试用例",
                        "建立测试覆盖率监控机制",
                        "设定阶段性覆盖率目标"
                    ],
                    "expected_benefit": "降低产品质量风险，提升交付信心",
                    "estimated_effort": "1-2周",
                    "metrics": {
                        "current_coverage": coverage_analysis.overall_coverage_rate,
                        "target_coverage": 0.8,
                        "uncovered_count": len(coverage_analysis.uncovered_requirements)
                    }
                })
            elif coverage_analysis.overall_coverage_rate < 0.8:
                suggestions.append({
                    "type": "TEST_COVERAGE_IMPROVEMENT",
                    "category": "OVERALL_COVERAGE",
                    "title": "优化测试覆盖率",
                    "description": f"当前整体测试覆盖率为{coverage_analysis.overall_coverage_rate:.1%}，可进一步优化",
                    "priority": "MEDIUM",
                    "action_items": [
                        "分析覆盖率薄弱环节",
                        "补充边界值和异常场景测试",
                        "提升自动化测试比例",
                        "定期评估覆盖率质量"
                    ],
                    "expected_benefit": "进一步提升产品质量保障",
                    "estimated_effort": "3-5天",
                    "metrics": {
                        "current_coverage": coverage_analysis.overall_coverage_rate,
                        "target_coverage": 0.85
                    }
                })
            
            # 需求覆盖率建议
            if coverage_analysis.requirement_coverage_rate < 0.7:
                suggestions.append({
                    "type": "TEST_COVERAGE_IMPROVEMENT",
                    "category": "REQUIREMENT_COVERAGE",
                    "title": "改善需求测试覆盖",
                    "description": f"需求覆盖率为{coverage_analysis.requirement_coverage_rate:.1%}，{len(coverage_analysis.uncovered_requirements)}个需求缺少测试",
                    "priority": "HIGH",
                    "action_items": [
                        f"为{len(coverage_analysis.uncovered_requirements)}个未覆盖需求创建测试用例",
                        "建立需求与测试用例的追溯关系",
                        "确保每个需求至少有2个测试用例",
                        "优先处理高优先级需求的测试覆盖"
                    ],
                    "expected_benefit": "确保所有需求都得到测试验证",
                    "estimated_effort": "1-2周",
                    "uncovered_requirements": coverage_analysis.uncovered_requirements[:5]  # 只显示前5个
                })
            
            # 场景覆盖率建议
            if coverage_analysis.scenario_coverage_rate < 0.6:
                suggestions.append({
                    "type": "TEST_COVERAGE_IMPROVEMENT",
                    "category": "SCENARIO_COVERAGE",
                    "title": "完善测试场景覆盖",
                    "description": f"测试场景覆盖率为{coverage_analysis.scenario_coverage_rate:.1%}，缺少多种测试场景",
                    "priority": "MEDIUM",
                    "action_items": [
                        "补充异常流程测试场景",
                        "增加边界值测试用例",
                        "添加性能和安全测试场景",
                        "建立场景测试检查清单"
                    ],
                    "expected_benefit": "提升测试场景完整性，发现更多潜在问题",
                    "estimated_effort": "5-7天",
                    "uncovered_scenarios": coverage_analysis.uncovered_scenarios[:10]  # 只显示前10个
                })
            
            # 高风险覆盖缺口建议
            high_risk_gaps = [gap for gap in coverage_analysis.coverage_gaps 
                            if gap.get("risk_level") == "HIGH"]
            if high_risk_gaps:
                suggestions.append({
                    "type": "TEST_COVERAGE_IMPROVEMENT",
                    "category": "HIGH_RISK_GAPS",
                    "title": "紧急处理高风险测试缺口",
                    "description": f"发现{len(high_risk_gaps)}个高风险测试覆盖缺口，需要立即处理",
                    "priority": "CRITICAL",
                    "action_items": [
                        "立即为高风险需求创建基础测试用例",
                        "进行风险评估和影响分析",
                        "制定应急测试计划",
                        "加强相关功能的测试验证"
                    ],
                    "expected_benefit": "降低高风险功能的质量风险",
                    "estimated_effort": "2-3天",
                    "high_risk_gaps": high_risk_gaps[:3]  # 只显示前3个
                })
            
            # 基于覆盖率建议的通用建议
            if coverage_analysis.coverage_recommendations:
                suggestions.append({
                    "type": "TEST_COVERAGE_IMPROVEMENT",
                    "category": "GENERAL_RECOMMENDATIONS",
                    "title": "测试覆盖率改进建议",
                    "description": "基于覆盖率分析的综合改进建议",
                    "priority": "MEDIUM",
                    "action_items": coverage_analysis.coverage_recommendations[:5],  # 最多5个建议
                    "expected_benefit": "全面提升测试覆盖率和测试质量",
                    "estimated_effort": "1周"
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating test coverage suggestions: {str(e)}")
            return []
    
    def _convert_test_suggestion_to_dict(self, suggestion: TestSuggestion) -> Dict:
        """
        将TestSuggestion对象转换为字典格式
        
        Args:
            suggestion: 测试建议对象
            
        Returns:
            Dict: 字典格式的建议
        """
        return {
            "type": "TEST_SUGGESTION",
            "category": "TEST_CASE_CREATION",
            "title": suggestion.title,
            "description": suggestion.description,
            "priority": suggestion.priority,
            "action_items": suggestion.test_steps,
            "expected_benefit": suggestion.expected_result,
            "rationale": suggestion.rationale,
            "estimated_effort": "1-2天"  # 默认估算
        }
    
    async def generate_optimization_suggestions(self, context: OptimizationContext) -> List[OptimizationSuggestion]:
        """
        生成优化建议
        
        Args:
            context: 优化上下文
            
        Returns:
            List[OptimizationSuggestion]: 优化建议列表
        """
        try:
            self.logger.info("Generating optimization suggestions")
            
            suggestions = []
            
            # 分析性能瓶颈
            bottlenecks = await self._identify_performance_bottlenecks(context.performance_metrics)
            
            # 为每个瓶颈生成优化建议
            for bottleneck in bottlenecks:
                suggestion = await self._generate_optimization_suggestion(bottleneck)
                if suggestion:
                    suggestions.append(suggestion)
            
            # 分析资源使用
            resource_suggestions = await self._generate_resource_optimization_suggestions(context.resource_usage)
            suggestions.extend(resource_suggestions)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating optimization suggestions: {str(e)}", exc_info=True)
            return []
    
    async def _analyze_requirements_quality(self, requirements_data: RequirementsData) -> RequirementsQualityAnalysis:
        """
        分析需求质量
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            RequirementsQualityAnalysis: 质量分析结果
        """
        try:
            analysis = RequirementsQualityAnalysis()
            
            if not requirements_data.requirements:
                return analysis
            
            # 分析完整性
            analysis.completeness_score = await self._assess_requirements_completeness(requirements_data)
            
            # 分析清晰度
            analysis.clarity_score = await self._assess_requirements_clarity(requirements_data)
            
            # 分析一致性
            analysis.consistency_score = await self._assess_requirements_consistency(requirements_data)
            
            # 分析可测试性
            analysis.testability_score = await self._assess_requirements_testability(requirements_data)
            
            # 计算总体得分
            analysis.overall_score = (
                analysis.completeness_score + analysis.clarity_score + 
                analysis.consistency_score + analysis.testability_score
            ) / 4
            
            # 识别问题需求
            analysis.problematic_requirements = await self._identify_problematic_requirements(requirements_data)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing requirements quality: {str(e)}", exc_info=True)
            return RequirementsQualityAnalysis()
    
    async def _assess_requirements_completeness(self, requirements_data: RequirementsData) -> float:
        """
        评估需求完整性
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            float: 完整性得分 (0-1)
        """
        try:
            total_requirements = len(requirements_data.requirements)
            if total_requirements == 0:
                return 0.0
            
            complete_requirements = 0
            
            for req in requirements_data.requirements:
                completeness_factors = [
                    bool(req.get("description") and len(req.get("description", "").strip()) > 10),
                    bool(req.get("acceptance_criteria") and len(req.get("acceptance_criteria", [])) > 0),
                    bool(req.get("priority")),
                    bool(req.get("business_value")),
                    bool(req.get("stakeholder")),
                    req.get("dependencies") is not None
                ]
                
                # 如果满足80%以上的完整性因素，认为是完整的
                if sum(completeness_factors) / len(completeness_factors) >= 0.8:
                    complete_requirements += 1
            
            return complete_requirements / total_requirements
            
        except Exception as e:
            self.logger.error(f"Error assessing requirements completeness: {str(e)}")
            return 0.0
    
    async def _assess_requirements_clarity(self, requirements_data: RequirementsData) -> float:
        """
        评估需求清晰度 - 增强版
        
        使用多维度分析方法评估需求清晰度，包括：
        1. 语言表达清晰度 - 检查模糊词汇、专业术语定义
        2. 结构完整性 - 验证需求结构的完整性
        3. 量化指标 - 检查是否包含可量化的标准
        4. 上下文一致性 - 检查需求间的术语一致性
        5. AI语义分析 - 使用AI进行深度语义理解分析
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            float: 清晰度得分 (0-1)
        """
        try:
            if not requirements_data.requirements:
                return 0.0
            
            clarity_scores = []
            
            # 构建全局术语词典用于一致性检查
            global_terms = await self._extract_domain_terms(requirements_data.requirements)
            
            for req in requirements_data.requirements:
                clarity_score = await self._assess_single_requirement_clarity(req, global_terms)
                clarity_scores.append(clarity_score)
            
            # 计算整体清晰度得分
            overall_clarity = sum(clarity_scores) / len(clarity_scores)
            
            # 应用全局一致性调整
            consistency_penalty = await self._calculate_terminology_consistency_penalty(requirements_data.requirements, global_terms)
            adjusted_clarity = max(0.0, overall_clarity - consistency_penalty)
            
            self.logger.info(f"Requirements clarity assessment completed. Overall score: {adjusted_clarity:.3f}")
            
            return adjusted_clarity
            
        except Exception as e:
            self.logger.error(f"Error assessing requirements clarity: {str(e)}")
            return 0.0
    
    async def _assess_single_requirement_clarity(self, requirement: Dict, global_terms: Dict[str, int]) -> float:
        """
        评估单个需求的清晰度
        
        Args:
            requirement: 需求对象
            global_terms: 全局术语词典
            
        Returns:
            float: 单个需求的清晰度得分 (0-1)
        """
        try:
            title = requirement.get("title", "") or ""
            description = requirement.get("description", "") or ""
            acceptance_criteria = requirement.get("acceptance_criteria", []) or []
            
            # 确保acceptance_criteria是列表类型
            if not isinstance(acceptance_criteria, (list, tuple)):
                acceptance_criteria = []
            
            # 初始化评分组件
            scores = {
                "language_clarity": 0.0,      # 语言表达清晰度 (25%)
                "structure_completeness": 0.0, # 结构完整性 (20%)
                "quantification": 0.0,         # 量化指标 (20%)
                "terminology_consistency": 0.0, # 术语一致性 (15%)
                "ai_semantic_analysis": 0.0    # AI语义分析 (20%)
            }
            
            # 1. 语言表达清晰度评估
            scores["language_clarity"] = await self._assess_language_clarity(title, description, acceptance_criteria)
            
            # 2. 结构完整性评估
            scores["structure_completeness"] = await self._assess_structure_completeness(requirement)
            
            # 3. 量化指标评估
            scores["quantification"] = await self._assess_quantification_level(description, acceptance_criteria)
            
            # 4. 术语一致性评估
            scores["terminology_consistency"] = await self._assess_terminology_consistency(requirement, global_terms)
            
            # 5. AI语义分析（如果可用）
            if self.ai_service:
                scores["ai_semantic_analysis"] = await self._ai_assess_requirement_clarity(requirement)
            else:
                scores["ai_semantic_analysis"] = 0.6  # 默认中等分数
            
            # 计算加权总分
            weights = {
                "language_clarity": 0.25,
                "structure_completeness": 0.20,
                "quantification": 0.20,
                "terminology_consistency": 0.15,
                "ai_semantic_analysis": 0.20
            }
            
            total_score = sum(scores[component] * weights[component] for component in scores)
            
            # 记录详细评分信息（用于调试）
            self.logger.debug(f"Requirement '{title[:50]}...' clarity scores: {scores}, total: {total_score:.3f}")
            
            return min(1.0, max(0.0, total_score))
            
        except Exception as e:
            self.logger.error(f"Error assessing single requirement clarity: {str(e)}")
            return 0.5
    
    async def _assess_language_clarity(self, title: str, description: str, acceptance_criteria) -> float:
        """
        评估语言表达清晰度
        
        Args:
            title: 需求标题
            description: 需求描述
            acceptance_criteria: 验收标准
            
        Returns:
            float: 语言清晰度得分 (0-1)
        """
        try:
            score = 0.0
            
            # 检查模糊词汇
            vague_words = [
                # 中文模糊词汇
                "合适的", "足够的", "适当的", "良好的", "优秀的", "较好的", "比较", "相对",
                "尽可能", "尽量", "基本上", "大概", "大约", "左右", "等等", "之类",
                "一般", "通常", "正常", "合理", "恰当", "适宜", "妥善", "完善",
                # 英文模糊词汇
                "reasonable", "appropriate", "good", "better", "best", "suitable",
                "adequate", "sufficient", "proper", "optimal", "efficient", "effective",
                "user-friendly", "easy", "simple", "complex", "advanced", "basic"
            ]
            
            combined_text = f"{title} {description}".lower()
            vague_word_count = sum(1 for word in vague_words if word in combined_text)
            total_words = len(combined_text.split())
            
            if total_words > 0:
                vague_ratio = vague_word_count / total_words
                # 模糊词汇比例越低，得分越高
                score += max(0.0, 0.3 - vague_ratio * 3)  # 最高0.3分
            
            # 检查具体性指标
            import re
            
            # 数字和量化指标
            has_numbers = bool(re.search(r'\d+', combined_text))
            has_percentages = bool(re.search(r'\d+%', combined_text))
            has_units = bool(re.search(r'\d+\s*(秒|分钟|小时|天|周|月|年|次|个|项|MB|GB|TB|ms|s)', combined_text))
            
            if has_numbers:
                score += 0.15
            if has_percentages:
                score += 0.1
            if has_units:
                score += 0.15
            
            # 检查动作词汇的明确性
            clear_action_words = [
                "创建", "删除", "修改", "更新", "查询", "搜索", "导入", "导出",
                "登录", "注册", "验证", "授权", "发送", "接收", "处理", "计算",
                "create", "delete", "update", "modify", "query", "search", "import", "export",
                "login", "register", "validate", "authorize", "send", "receive", "process", "calculate"
            ]
            
            action_word_count = sum(1 for word in clear_action_words if word in combined_text)
            if action_word_count > 0:
                score += min(0.2, action_word_count * 0.05)  # 最高0.2分
            
            # 检查验收标准的清晰度
            if acceptance_criteria and isinstance(acceptance_criteria, (list, tuple)):
                criteria_clarity = 0.0
                for criterion in acceptance_criteria:
                    if isinstance(criterion, str) and len(criterion.strip()) > 10:
                        # 检查验收标准是否包含可验证的条件
                        verifiable_patterns = [
                            r'应该|必须|需要|能够|可以',  # 中文条件词
                            r'should|must|shall|will|can|able to',  # 英文条件词
                            r'等于|大于|小于|包含|显示|返回',  # 中文验证词
                            r'equals?|greater|less|contains?|displays?|returns?'  # 英文验证词
                        ]
                        
                        has_verifiable = any(re.search(pattern, criterion.lower()) for pattern in verifiable_patterns)
                        if has_verifiable:
                            criteria_clarity += 0.1
                
                score += min(0.1, criteria_clarity)  # 最高0.1分
            
            return min(1.0, score)
            
        except Exception as e:
            self.logger.error(f"Error assessing language clarity: {str(e)}")
            return 0.5
    
    async def _assess_structure_completeness(self, requirement: Dict) -> float:
        """
        评估需求结构完整性
        
        Args:
            requirement: 需求对象
            
        Returns:
            float: 结构完整性得分 (0-1)
        """
        try:
            score = 0.0
            
            # 检查必要字段的存在和质量
            required_fields = {
                "title": 0.2,           # 标题 (20%)
                "description": 0.3,     # 描述 (30%)
                "acceptance_criteria": 0.2,  # 验收标准 (20%)
                "priority": 0.1,        # 优先级 (10%)
                "business_value": 0.1,  # 业务价值 (10%)
                "stakeholder": 0.1      # 干系人 (10%)
            }
            
            for field, weight in required_fields.items():
                field_value = requirement.get(field)
                
                if field_value:
                    if field == "title":
                        # 标题应该简洁明确，长度适中
                        title_len = len(str(field_value).strip())
                        if 10 <= title_len <= 100:
                            score += weight
                        elif title_len > 5:
                            score += weight * 0.7
                    
                    elif field == "description":
                        # 描述应该详细，包含足够信息
                        desc_len = len(str(field_value).strip())
                        if desc_len >= 50:
                            score += weight
                        elif desc_len >= 20:
                            score += weight * 0.7
                        elif desc_len >= 10:
                            score += weight * 0.4
                    
                    elif field == "acceptance_criteria":
                        # 验收标准应该是列表且包含多个条件
                        if isinstance(field_value, list) and len(field_value) > 0:
                            criteria_quality = 0.0
                            for criterion in field_value:
                                if isinstance(criterion, str) and len(criterion.strip()) > 5:
                                    criteria_quality += 1
                            
                            if criteria_quality >= 3:
                                score += weight
                            elif criteria_quality >= 2:
                                score += weight * 0.8
                            elif criteria_quality >= 1:
                                score += weight * 0.5
                        elif isinstance(field_value, str) and len(field_value.strip()) > 10:
                            score += weight * 0.6
                    
                    elif field in ["priority", "business_value", "stakeholder"]:
                        # 其他字段只要有值就给分
                        if str(field_value).strip():
                            score += weight
            
            # 检查字段间的逻辑一致性
            priority = requirement.get("priority", "").upper()
            business_value = requirement.get("business_value", "")
            
            # 高优先级需求应该有明确的业务价值
            if priority in ["HIGH", "CRITICAL"] and business_value:
                score += 0.05
            
            # 检查是否有依赖关系说明
            if requirement.get("dependencies") is not None:
                score += 0.05
            
            return min(1.0, score)
            
        except Exception as e:
            self.logger.error(f"Error assessing structure completeness: {str(e)}")
            return 0.5
    
    async def _assess_quantification_level(self, description: str, acceptance_criteria: List) -> float:
        """
        评估量化指标水平
        
        Args:
            description: 需求描述
            acceptance_criteria: 验收标准
            
        Returns:
            float: 量化水平得分 (0-1)
        """
        try:
            score = 0.0
            combined_text = f"{description} {' '.join(str(c) for c in acceptance_criteria if c)}"
            
            import re
            
            # 检查数值指标
            quantification_patterns = [
                # 时间相关
                (r'\d+\s*(秒|分钟|小时|天|周|月|年|ms|s|min|hour|day|week|month|year)', 0.15),
                # 性能相关
                (r'\d+\s*(次/秒|TPS|QPS|并发|concurrent)', 0.15),
                # 容量相关
                (r'\d+\s*(MB|GB|TB|KB|字节|byte|条|个|项)', 0.15),
                # 百分比
                (r'\d+%|百分之\d+', 0.1),
                # 精确数字
                (r'不超过\s*\d+|至少\s*\d+|最多\s*\d+|最少\s*\d+|exactly\s*\d+|at\s*least\s*\d+|at\s*most\s*\d+', 0.15),
                # 范围
                (r'\d+\s*[-~到]\s*\d+|between\s*\d+\s*and\s*\d+', 0.1),
                # 比较级
                (r'大于\s*\d+|小于\s*\d+|等于\s*\d+|greater\s*than\s*\d+|less\s*than\s*\d+|equal\s*to\s*\d+', 0.1)
            ]
            
            for pattern, points in quantification_patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    score += points
            
            # 检查定性但明确的标准
            qualitative_clear_patterns = [
                # 状态描述
                (r'成功|失败|完成|错误|正确|success|fail|complete|error|correct', 0.05),
                # 用户体验
                (r'易于使用|用户友好|直观|intuitive|user.friendly|easy.to.use', 0.03),
                # 可见性
                (r'显示|隐藏|可见|不可见|show|hide|visible|invisible', 0.05)
            ]
            
            for pattern, points in qualitative_clear_patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    score += points
            
            # 检查是否有明确的输入输出定义
            io_patterns = [
                r'输入.*输出|input.*output',
                r'参数.*返回|parameter.*return',
                r'请求.*响应|request.*response'
            ]
            
            for pattern in io_patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    score += 0.1
                    break
            
            # 检查是否有错误处理的量化标准
            error_handling_patterns = [
                r'错误码|error.code',
                r'异常.*处理|exception.*handling',
                r'超时.*\d+|timeout.*\d+'
            ]
            
            for pattern in error_handling_patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    score += 0.05
                    break
            
            return min(1.0, score)
            
        except Exception as e:
            self.logger.error(f"Error assessing quantification level: {str(e)}")
            return 0.5
    
    async def _extract_domain_terms(self, requirements: List[Dict]) -> Dict[str, int]:
        """
        提取领域术语词典
        
        Args:
            requirements: 需求列表
            
        Returns:
            Dict[str, int]: 术语及其出现频次
        """
        try:
            import re
            from collections import Counter
            
            # 收集所有文本
            all_text = []
            for req in requirements:
                title = req.get("title", "")
                description = req.get("description", "")
                all_text.append(f"{title} {description}")
            
            combined_text = " ".join(all_text).lower()
            
            # 提取可能的术语（2-4个字符的词汇，出现频次>=2）
            # 中文词汇模式
            chinese_terms = re.findall(r'[\u4e00-\u9fff]{2,4}', combined_text)
            # 英文词汇模式（排除常见词汇）
            english_terms = re.findall(r'\b[a-z]{3,}\b', combined_text)
            
            # 过滤常见词汇
            common_words = {
                "用户", "系统", "功能", "界面", "数据", "信息", "管理", "操作", "处理", "显示",
                "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "man", "new", "now", "old", "see", "two", "way", "who", "boy", "did", "its", "let", "put", "say", "she", "too", "use"
            }
            
            # 统计术语频次
            all_terms = chinese_terms + english_terms
            term_counts = Counter(term for term in all_terms if term not in common_words and len(term) >= 2)
            
            # 只保留出现2次以上的术语
            domain_terms = {term: count for term, count in term_counts.items() if count >= 2}
            
            self.logger.debug(f"Extracted {len(domain_terms)} domain terms")
            return domain_terms
            
        except Exception as e:
            self.logger.error(f"Error extracting domain terms: {str(e)}")
            return {}
    
    async def _assess_terminology_consistency(self, requirement: Dict, global_terms: Dict[str, int]) -> float:
        """
        评估术语一致性
        
        Args:
            requirement: 需求对象
            global_terms: 全局术语词典
            
        Returns:
            float: 术语一致性得分 (0-1)
        """
        try:
            if not global_terms:
                return 0.8  # 如果没有全局术语，给默认分数
            
            title = requirement.get("title", "")
            description = requirement.get("description", "")
            combined_text = f"{title} {description}".lower()
            
            # 检查是否使用了全局术语
            used_terms = 0
            total_possible_terms = 0
            
            for term, global_count in global_terms.items():
                if global_count >= 3:  # 只考虑高频术语
                    total_possible_terms += 1
                    if term in combined_text:
                        used_terms += 1
            
            if total_possible_terms == 0:
                return 0.8
            
            # 术语使用率
            term_usage_rate = used_terms / total_possible_terms
            
            # 检查是否有术语的不一致使用（同义词）
            inconsistency_penalty = 0.0
            
            # 常见同义词组
            synonym_groups = [
                ["用户", "使用者", "操作者"],
                ["登录", "登陆", "sign in", "login"],
                ["删除", "移除", "remove", "delete"],
                ["创建", "新建", "create", "add"],
                ["修改", "编辑", "更新", "edit", "update", "modify"]
            ]
            
            for group in synonym_groups:
                used_synonyms = [term for term in group if term in combined_text]
                if len(used_synonyms) > 1:
                    inconsistency_penalty += 0.1
            
            consistency_score = min(1.0, term_usage_rate + 0.2 - inconsistency_penalty)
            return max(0.0, consistency_score)
            
        except Exception as e:
            self.logger.error(f"Error assessing terminology consistency: {str(e)}")
            return 0.5
    
    async def _calculate_terminology_consistency_penalty(self, requirements: List[Dict], global_terms: Dict[str, int]) -> float:
        """
        计算全局术语一致性惩罚
        
        Args:
            requirements: 需求列表
            global_terms: 全局术语词典
            
        Returns:
            float: 一致性惩罚值 (0-0.2)
        """
        try:
            if len(requirements) < 2:
                return 0.0
            
            # 检查跨需求的术语一致性
            term_usage_by_req = []
            
            for req in requirements:
                title = req.get("title", "")
                description = req.get("description", "")
                combined_text = f"{title} {description}".lower()
                
                req_terms = set()
                for term in global_terms:
                    if term in combined_text:
                        req_terms.add(term)
                
                term_usage_by_req.append(req_terms)
            
            # 计算术语使用的一致性
            if not term_usage_by_req:
                return 0.0
            
            # 检查核心术语是否在所有需求中保持一致
            core_terms = {term for term, count in global_terms.items() if count >= len(requirements) * 0.5}
            
            inconsistent_usage = 0
            for term in core_terms:
                usage_count = sum(1 for req_terms in term_usage_by_req if term in req_terms)
                expected_usage = len(requirements)
                
                if usage_count < expected_usage * 0.7:  # 如果核心术语使用率低于70%
                    inconsistent_usage += 1
            
            # 计算惩罚值
            if core_terms:
                penalty = (inconsistent_usage / len(core_terms)) * 0.2
            else:
                penalty = 0.0
            
            return min(0.2, penalty)
            
        except Exception as e:
            self.logger.error(f"Error calculating terminology consistency penalty: {str(e)}")
            return 0.0
    
    async def _assess_requirements_consistency(self, requirements_data: RequirementsData) -> float:
        """
        评估需求一致性
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            float: 一致性得分 (0-1)
        """
        try:
            if len(requirements_data.requirements) < 2:
                return 1.0  # 单个需求默认一致
            
            # 基础一致性检查
            consistency_score = 1.0
            
            # 检查优先级分布是否合理
            priorities = [req.get("priority", "MEDIUM") for req in requirements_data.requirements]
            priority_distribution = {p: priorities.count(p) for p in set(priorities)}
            
            # 合理的优先级分布：高优先级不应该过多
            high_priority_ratio = priority_distribution.get("HIGH", 0) / len(priorities)
            critical_priority_ratio = priority_distribution.get("CRITICAL", 0) / len(priorities)
            
            # 如果高优先级需求过多，降低一致性得分
            if high_priority_ratio > 0.3:
                consistency_score -= 0.2
            if critical_priority_ratio > 0.1:
                consistency_score -= 0.2
            
            # 检查分类是否合理
            categories = [req.get("category", "未分类") for req in requirements_data.requirements]
            uncategorized_ratio = categories.count("未分类") / len(categories)
            if uncategorized_ratio > 0.3:
                consistency_score -= 0.2
            
            # 检查描述风格是否一致（长度差异）
            descriptions = [req.get("description", "") for req in requirements_data.requirements]
            desc_lengths = [len(desc) for desc in descriptions if desc]
            if desc_lengths:
                avg_length = sum(desc_lengths) / len(desc_lengths)
                length_variance = sum((length - avg_length) ** 2 for length in desc_lengths) / len(desc_lengths)
                if length_variance > avg_length * 2:  # 长度差异过大
                    consistency_score -= 0.1
            
            # AI一致性分析（如果AI服务可用且需求数量适中）
            if self.ai_service and 2 <= len(requirements_data.requirements) <= 10:
                ai_consistency_score = await self._ai_assess_requirements_consistency(requirements_data)
                # 将AI评分与基础评分结合（AI权重30%，基础评分权重70%）
                consistency_score = consistency_score * 0.7 + ai_consistency_score * 0.3
            
            return max(0.0, consistency_score)
            
        except Exception as e:
            self.logger.error(f"Error assessing requirements consistency: {str(e)}")
            return 0.0
    
    async def _assess_requirements_testability(self, requirements_data: RequirementsData) -> float:
        """
        评估需求可测试性
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            float: 可测试性得分 (0-1)
        """
        try:
            if not requirements_data.requirements:
                return 0.0
            
            testability_scores = []
            
            for req in requirements_data.requirements:
                score = 0.0
                
                # 检查是否有验收标准
                acceptance_criteria = req.get("acceptance_criteria", [])
                if acceptance_criteria:
                    score += 0.4
                    
                    # 检查验收标准的质量
                    for criterion in acceptance_criteria:
                        if isinstance(criterion, str):
                            # 检查是否包含可测试的关键词
                            testable_keywords = ["应该", "必须", "能够", "显示", "返回", "包含", "等于", "大于", "小于"]
                            if any(keyword in criterion for keyword in testable_keywords):
                                score += 0.1
                
                # 检查是否有明确的输入输出描述
                description = req.get("description", "")
                if "输入" in description or "输出" in description or "结果" in description:
                    score += 0.2
                
                # 检查是否有具体的数值标准
                import re
                if re.search(r'\d+', description):
                    score += 0.1
                
                # 检查是否避免了主观描述
                subjective_words = ["美观", "友好", "直观", "简单", "复杂", "beautiful", "user-friendly", "intuitive"]
                has_subjective = any(word in description.lower() for word in subjective_words)
                if not has_subjective:
                    score += 0.1
                
                # AI可测试性分析（如果AI服务可用）
                if self.ai_service and description:
                    ai_testability_score = await self._ai_assess_requirement_testability(req)
                    # 将AI评分与基础评分结合（AI权重30%，基础评分权重70%）
                    score = score * 0.7 + ai_testability_score * 0.3
                
                testability_scores.append(min(1.0, score))
            
            return sum(testability_scores) / len(testability_scores)
            
        except Exception as e:
            self.logger.error(f"Error assessing requirements testability: {str(e)}")
            return 0.0
    
    async def _identify_problematic_requirements(self, requirements_data: RequirementsData) -> List[Dict]:
        """
        识别问题需求
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            List[Dict]: 问题需求列表
        """
        try:
            problematic_reqs = []
            
            for i, req in enumerate(requirements_data.requirements):
                issues = []
                
                # 基础规则检查
                description = req.get("description", "")
                if not description or len(description.strip()) < 10:
                    issues.append("需求描述过于简短")
                
                # 检查验收标准
                acceptance_criteria = req.get("acceptance_criteria", [])
                if not acceptance_criteria or len(acceptance_criteria) == 0:
                    issues.append("缺少验收标准")
                
                # 检查优先级
                if not req.get("priority"):
                    issues.append("未设置优先级")
                
                # 检查业务价值
                if not req.get("business_value"):
                    issues.append("未明确业务价值")
                
                # 检查模糊词汇
                vague_words = ["合适的", "足够的", "适当的", "良好的", "优秀的"]
                if any(word in description for word in vague_words):
                    issues.append("包含模糊表述")
                
                # 检查是否过于复杂
                if len(description) > 1000:
                    issues.append("需求描述过于复杂，建议拆分")
                
                # AI质量分析（如果AI服务可用）
                if self.ai_service and description:
                    ai_issues = await self._ai_analyze_requirement_quality(req)
                    issues.extend(ai_issues)
                
                if issues:
                    severity = self._calculate_issue_severity(issues)
                    problematic_reqs.append({
                        "requirement_id": req.get("id", i),
                        "requirement_title": req.get("title", f"需求 {i+1}"),
                        "issues": issues,
                        "severity": severity
                    })
            
            return problematic_reqs
            
        except Exception as e:
            self.logger.error(f"Error identifying problematic requirements: {str(e)}")
            return []
    
    async def _ai_analyze_requirement_quality(self, requirement: Dict) -> List[str]:
        """
        使用AI分析需求质量问题
        
        Args:
            requirement: 需求对象
            
        Returns:
            List[str]: AI识别的问题列表
        """
        try:
            if not self.ai_service:
                return []
            
            title = requirement.get("title", "")
            description = requirement.get("description", "")
            acceptance_criteria = requirement.get("acceptance_criteria", [])
            
            # 构建AI分析提示词
            analysis_prompt = f"""
请分析以下需求的质量问题：

需求标题：{title}
需求描述：{description}
验收标准：{acceptance_criteria}

请识别以下类型的问题：
1. 模糊不清的表述
2. 缺少关键信息
3. 逻辑不一致
4. 难以测试验证
5. 技术实现困难

请以列表形式返回发现的问题，每行一个问题。如果没有问题，返回"无问题"。
"""
            
            ai_response = await self.ai_service.generate_response(analysis_prompt)
            
            if "无问题" in ai_response:
                return []
            
            # 解析AI返回的问题列表
            issues = []
            for line in ai_response.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and len(line) > 5:
                    # 清理格式化字符
                    clean_line = line.lstrip('- ').lstrip('* ').lstrip('• ')
                    if clean_line:
                        issues.append(clean_line)
            
            return issues[:5]  # 最多返回5个问题
            
        except Exception as e:
            self.logger.error(f"Error in AI requirement quality analysis: {str(e)}")
            return []
    
    def _calculate_issue_severity(self, issues: List[str]) -> str:
        """
        计算问题严重程度
        
        Args:
            issues: 问题列表
            
        Returns:
            str: 严重程度 (LOW, MEDIUM, HIGH, CRITICAL)
        """
        try:
            if not issues:
                return "LOW"
            
            # 高严重性问题关键词
            high_severity_keywords = [
                "缺少验收标准", "描述过于简短", "未设置优先级", "逻辑不一致", "技术实现困难"
            ]
            
            # 中等严重性问题关键词
            medium_severity_keywords = [
                "模糊表述", "缺少关键信息", "难以测试", "未明确业务价值"
            ]
            
            high_count = sum(1 for issue in issues if any(keyword in issue for keyword in high_severity_keywords))
            medium_count = sum(1 for issue in issues if any(keyword in issue for keyword in medium_severity_keywords))
            
            # 根据问题数量和类型确定严重程度
            if high_count >= 3 or len(issues) >= 5:
                return "CRITICAL"
            elif high_count >= 2 or (high_count >= 1 and medium_count >= 2):
                return "HIGH"
            elif high_count >= 1 or medium_count >= 2 or len(issues) >= 3:
                return "MEDIUM"
            else:
                return "LOW"
                
        except Exception as e:
            self.logger.error(f"Error calculating issue severity: {str(e)}")
            return "MEDIUM"
    
    async def analyze_project_status(self, context: ProjectContext) -> Dict[str, Any]:
        """
        项目状况分析 - AI助手模块的核心分析功能
        
        提供全面的项目健康度评估，包括：
        1. 项目健康度评估 - 基于进度、质量、资源等多维度指标
        2. 团队能力分析 - 评估团队规模、技能匹配度、工作负载
        3. 进度状态分析 - 分析项目时间线、里程碑完成情况
        4. 质量风险评估 - 基于需求质量、测试覆盖率等指标
        5. 资源配置分析 - 评估人力、时间、预算资源配置合理性
        
        Args:
            context: 项目上下文数据
            
        Returns:
            Dict[str, Any]: 详细的项目状况分析报告
        """
        try:
            self.logger.info(f"Starting comprehensive project status analysis for project {context.project_id}")
            
            analysis_result = {
                "project_info": {
                    "project_id": context.project_id,
                    "project_name": context.project_name,
                    "project_type": context.project_type,
                    "team_size": context.team_size,
                    "analysis_timestamp": datetime.utcnow().isoformat()
                },
                "health_assessment": {},
                "team_analysis": {},
                "progress_analysis": {},
                "quality_assessment": {},
                "resource_analysis": {},
                "risk_assessment": {},
                "recommendations": [],
                "overall_health_score": 0.0,
                "analysis_summary": ""
            }
            
            # 1. 项目健康度评估
            health_assessment = await self._assess_project_health(context)
            analysis_result["health_assessment"] = health_assessment
            
            # 2. 团队能力分析
            team_analysis = await self._analyze_team_capacity(context)
            analysis_result["team_analysis"] = team_analysis
            
            # 3. 进度状态分析
            progress_analysis = await self._evaluate_timeline_status(context)
            analysis_result["progress_analysis"] = progress_analysis
            
            # 4. 质量风险评估
            quality_assessment = await self._assess_quality_risks(context)
            analysis_result["quality_assessment"] = quality_assessment
            
            # 5. 资源配置分析
            resource_analysis = await self._analyze_resource_allocation(context)
            analysis_result["resource_analysis"] = resource_analysis
            
            # 6. 综合风险评估
            risk_assessment = await self._assess_comprehensive_risks(context, {
                "health": health_assessment,
                "team": team_analysis,
                "progress": progress_analysis,
                "quality": quality_assessment,
                "resource": resource_analysis
            })
            analysis_result["risk_assessment"] = risk_assessment
            
            # 7. 计算整体健康度得分
            overall_score = self._calculate_overall_health_score({
                "health": health_assessment.get("health_score", 0.5),
                "team": team_analysis.get("capacity_score", 0.5),
                "progress": progress_analysis.get("progress_score", 0.5),
                "quality": quality_assessment.get("quality_score", 0.5),
                "resource": resource_analysis.get("allocation_score", 0.5)
            })
            analysis_result["overall_health_score"] = overall_score
            
            # 8. 生成改进建议
            recommendations = await self._generate_project_improvement_recommendations(
                context, analysis_result
            )
            analysis_result["recommendations"] = recommendations
            
            # 9. 生成分析摘要
            analysis_summary = self._generate_project_analysis_summary(analysis_result)
            analysis_result["analysis_summary"] = analysis_summary
            
            self.logger.info(f"Project status analysis completed. Overall health score: {overall_score:.2f}")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error in project status analysis: {str(e)}", exc_info=True)
            return {
                "error": f"项目状况分析失败: {str(e)}",
                "overall_health_score": 0.0,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    async def _assess_project_health(self, context: ProjectContext) -> Dict[str, Any]:
        """
        评估项目健康度
        
        Args:
            context: 项目上下文
            
        Returns:
            Dict[str, Any]: 项目健康度评估结果
        """
        try:
            health_metrics = {
                "requirements_health": 0.5,
                "development_health": 0.5,
                "testing_health": 0.5,
                "delivery_health": 0.5
            }
            
            # 需求健康度评估
            if context.requirements:
                requirements_data = RequirementsData(
                    requirements=context.requirements,
                    total_count=len(context.requirements),
                    categories=[req.get("category", "未分类") for req in context.requirements],
                    priorities=[req.get("priority", "MEDIUM") for req in context.requirements]
                )
                
                quality_analysis = await self._analyze_requirements_quality(requirements_data)
                health_metrics["requirements_health"] = quality_analysis.overall_score
            
            # 测试健康度评估
            if context.test_data:
                test_coverage = await self._calculate_test_coverage({
                    "test_cases": context.test_data.get("test_cases", []),
                    "requirements": context.requirements or [],
                    "coverage": context.test_data.get("coverage", {})
                })
                health_metrics["testing_health"] = test_coverage.overall_coverage_rate
            
            # 质量指标健康度
            if context.quality_metrics:
                quality_score = self._evaluate_quality_metrics(context.quality_metrics)
                health_metrics["delivery_health"] = quality_score
            
            # 计算综合健康度得分
            health_score = sum(health_metrics.values()) / len(health_metrics)
            
            return {
                "health_score": round(health_score, 3),
                "health_metrics": {k: round(v, 3) for k, v in health_metrics.items()},
                "health_level": self._get_health_level(health_score),
                "key_indicators": self._identify_health_indicators(health_metrics),
                "improvement_areas": self._identify_improvement_areas(health_metrics)
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing project health: {str(e)}")
            return {"health_score": 0.5, "error": str(e)}
    
    async def _analyze_team_capacity(self, context: ProjectContext) -> Dict[str, Any]:
        """
        分析团队能力
        
        Args:
            context: 项目上下文
            
        Returns:
            Dict[str, Any]: 团队能力分析结果
        """
        try:
            team_metrics = {
                "size_adequacy": 0.5,
                "skill_match": 0.5,
                "workload_balance": 0.5,
                "collaboration_effectiveness": 0.5
            }
            
            # 团队规模评估
            if context.team_size:
                project_complexity = self._estimate_project_complexity(context)
                team_metrics["size_adequacy"] = self._assess_team_size_adequacy(
                    context.team_size, project_complexity
                )
            
            # 技能匹配度评估（基于项目类型）
            if context.project_type:
                team_metrics["skill_match"] = self._assess_skill_match(
                    context.project_type, context.team_size or 5
                )
            
            # 工作负载平衡评估
            if context.timeline and context.requirements:
                team_metrics["workload_balance"] = self._assess_workload_balance(
                    context.timeline, len(context.requirements), context.team_size or 5
                )
            
            # 协作效率评估（基于团队规模）
            if context.team_size:
                team_metrics["collaboration_effectiveness"] = self._assess_collaboration_effectiveness(
                    context.team_size
                )
            
            capacity_score = sum(team_metrics.values()) / len(team_metrics)
            
            return {
                "capacity_score": round(capacity_score, 3),
                "team_metrics": {k: round(v, 3) for k, v in team_metrics.items()},
                "team_size": context.team_size,
                "capacity_level": self._get_capacity_level(capacity_score),
                "strengths": self._identify_team_strengths(team_metrics),
                "challenges": self._identify_team_challenges(team_metrics),
                "recommendations": self._generate_team_recommendations(team_metrics, context)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing team capacity: {str(e)}")
            return {"capacity_score": 0.5, "error": str(e)}
    
    async def _evaluate_timeline_status(self, context: ProjectContext) -> Dict[str, Any]:
        """
        评估项目进度状态
        
        Args:
            context: 项目上下文
            
        Returns:
            Dict[str, Any]: 进度状态评估结果
        """
        try:
            progress_metrics = {
                "schedule_adherence": 0.5,
                "milestone_completion": 0.5,
                "velocity_trend": 0.5,
                "scope_stability": 0.5
            }
            
            # 时间线分析
            if context.timeline:
                progress_metrics.update(self._analyze_timeline_metrics(context.timeline))
            
            # 需求稳定性分析
            if context.requirements:
                progress_metrics["scope_stability"] = self._assess_scope_stability(context.requirements)
            
            progress_score = sum(progress_metrics.values()) / len(progress_metrics)
            
            return {
                "progress_score": round(progress_score, 3),
                "progress_metrics": {k: round(v, 3) for k, v in progress_metrics.items()},
                "timeline_status": self._get_timeline_status(progress_score),
                "critical_milestones": self._identify_critical_milestones(context.timeline),
                "schedule_risks": self._identify_schedule_risks(progress_metrics),
                "acceleration_opportunities": self._identify_acceleration_opportunities(context)
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating timeline status: {str(e)}")
            return {"progress_score": 0.5, "error": str(e)}
    
    async def _assess_quality_risks(self, context: ProjectContext) -> Dict[str, Any]:
        """
        评估质量风险
        
        Args:
            context: 项目上下文
            
        Returns:
            Dict[str, Any]: 质量风险评估结果
        """
        try:
            quality_metrics = {
                "requirements_quality": 0.5,
                "test_coverage": 0.5,
                "defect_density": 0.5,
                "code_quality": 0.5
            }
            
            # 需求质量评估
            if context.requirements:
                requirements_data = RequirementsData(
                    requirements=context.requirements,
                    total_count=len(context.requirements),
                    categories=[req.get("category", "未分类") for req in context.requirements],
                    priorities=[req.get("priority", "MEDIUM") for req in context.requirements]
                )
                quality_analysis = await self._analyze_requirements_quality(requirements_data)
                quality_metrics["requirements_quality"] = quality_analysis.overall_score
            
            # 测试覆盖率评估
            if context.test_data:
                test_coverage = await self._calculate_test_coverage({
                    "test_cases": context.test_data.get("test_cases", []),
                    "requirements": context.requirements or [],
                    "coverage": context.test_data.get("coverage", {})
                })
                quality_metrics["test_coverage"] = test_coverage.overall_coverage_rate
            
            # 质量指标评估
            if context.quality_metrics:
                defect_score = self._assess_defect_metrics(context.quality_metrics)
                quality_metrics["defect_density"] = defect_score
                
                code_score = self._assess_code_quality_metrics(context.quality_metrics)
                quality_metrics["code_quality"] = code_score
            
            quality_score = sum(quality_metrics.values()) / len(quality_metrics)
            
            return {
                "quality_score": round(quality_score, 3),
                "quality_metrics": {k: round(v, 3) for k, v in quality_metrics.items()},
                "quality_level": self._get_quality_level(quality_score),
                "high_risk_areas": self._identify_high_risk_areas(quality_metrics),
                "quality_trends": self._analyze_quality_trends(context.quality_metrics),
                "mitigation_strategies": self._generate_quality_mitigation_strategies(quality_metrics)
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing quality risks: {str(e)}")
            return {"quality_score": 0.5, "error": str(e)}
    
    async def _analyze_resource_allocation(self, context: ProjectContext) -> Dict[str, Any]:
        """
        分析资源配置
        
        Args:
            context: 项目上下文
            
        Returns:
            Dict[str, Any]: 资源配置分析结果
        """
        try:
            resource_metrics = {
                "human_resource_adequacy": 0.5,
                "time_allocation": 0.5,
                "skill_distribution": 0.5,
                "resource_utilization": 0.5
            }
            
            # 人力资源充足性
            if context.team_size and context.requirements:
                project_complexity = self._estimate_project_complexity(context)
                resource_metrics["human_resource_adequacy"] = self._assess_human_resource_adequacy(
                    context.team_size, project_complexity, len(context.requirements)
                )
            
            # 时间分配合理性
            if context.timeline and context.requirements:
                resource_metrics["time_allocation"] = self._assess_time_allocation(
                    context.timeline, len(context.requirements)
                )
            
            # 技能分布评估
            if context.project_type and context.team_size:
                resource_metrics["skill_distribution"] = self._assess_skill_distribution(
                    context.project_type, context.team_size
                )
            
            # 资源利用率评估
            if context.team_size and context.timeline:
                resource_metrics["resource_utilization"] = self._assess_resource_utilization(
                    context.team_size, context.timeline
                )
            
            allocation_score = sum(resource_metrics.values()) / len(resource_metrics)
            
            return {
                "allocation_score": round(allocation_score, 3),
                "resource_metrics": {k: round(v, 3) for k, v in resource_metrics.items()},
                "allocation_level": self._get_allocation_level(allocation_score),
                "resource_gaps": self._identify_resource_gaps(resource_metrics, context),
                "optimization_opportunities": self._identify_resource_optimization_opportunities(resource_metrics),
                "scaling_recommendations": self._generate_scaling_recommendations(context, resource_metrics)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing resource allocation: {str(e)}")
            return {"allocation_score": 0.5, "error": str(e)}
    
    def _calculate_overall_health_score(self, dimension_scores: Dict[str, float]) -> float:
        """
        计算整体健康度得分
        
        Args:
            dimension_scores: 各维度得分
            
        Returns:
            float: 整体健康度得分
        """
        try:
            # 权重配置
            weights = {
                "health": 0.25,      # 项目健康度 25%
                "team": 0.20,        # 团队能力 20%
                "progress": 0.25,    # 进度状态 25%
                "quality": 0.20,     # 质量风险 20%
                "resource": 0.10     # 资源配置 10%
            }
            
            weighted_score = sum(
                dimension_scores.get(dimension, 0.5) * weight
                for dimension, weight in weights.items()
            )
            
            return round(weighted_score, 3)
            
        except Exception as e:
            self.logger.error(f"Error calculating overall health score: {str(e)}")
            return 0.5
    
    def _get_health_level(self, score: float) -> str:
        """获取健康度等级"""
        if score >= 0.8:
            return "优秀"
        elif score >= 0.6:
            return "良好"
        elif score >= 0.4:
            return "一般"
        else:
            return "较差"
    
    def _get_capacity_level(self, score: float) -> str:
        """获取团队能力等级"""
        if score >= 0.8:
            return "高效"
        elif score >= 0.6:
            return "良好"
        elif score >= 0.4:
            return "一般"
        else:
            return "不足"
    
    def _get_quality_level(self, score: float) -> str:
        """获取质量等级"""
        if score >= 0.8:
            return "高质量"
        elif score >= 0.6:
            return "良好"
        elif score >= 0.4:
            return "一般"
        else:
            return "风险较高"
    
    def _get_allocation_level(self, score: float) -> str:
        """获取资源配置等级"""
        if score >= 0.8:
            return "优化"
        elif score >= 0.6:
            return "合理"
        elif score >= 0.4:
            return "一般"
        else:
            return "不足"
    
    def _estimate_project_complexity(self, context: ProjectContext) -> float:
        """
        估算项目复杂度
        
        Args:
            context: 项目上下文
            
        Returns:
            float: 复杂度得分 (0-1)
        """
        try:
            complexity_score = 0.5  # 基础复杂度
            
            # 基于需求数量
            if context.requirements:
                req_count = len(context.requirements)
                if req_count > 50:
                    complexity_score += 0.3
                elif req_count > 20:
                    complexity_score += 0.2
                elif req_count > 10:
                    complexity_score += 0.1
            
            # 基于项目类型
            if context.project_type:
                type_complexity = {
                    "web_application": 0.6,
                    "mobile_app": 0.7,
                    "api_service": 0.5,
                    "data_platform": 0.8,
                    "ai_system": 0.9,
                    "enterprise_system": 0.8
                }
                complexity_score = type_complexity.get(context.project_type, 0.6)
            
            return min(1.0, complexity_score)
            
        except Exception as e:
            self.logger.error(f"Error estimating project complexity: {str(e)}")
            return 0.5
            self.logger.error(f"Error in AI requirement quality analysis: {str(e)}")
            return []
    
    async def _ai_assess_requirement_clarity(self, requirement: Dict) -> float:
        """
        使用AI评估需求清晰度 - 增强版
        
        使用AI进行深度语义分析，评估需求的清晰度和可理解性。
        包括语义一致性、逻辑完整性、表达准确性等多个维度。
        
        Args:
            requirement: 需求对象
            
        Returns:
            float: AI评估的清晰度得分 (0-1)
        """
        try:
            if not self.ai_service:
                return 0.6  # 默认中等偏上分数
            
            title = requirement.get("title", "")
            description = requirement.get("description", "")
            acceptance_criteria = requirement.get("acceptance_criteria", [])
            priority = requirement.get("priority", "")
            business_value = requirement.get("business_value", "")
            
            # 构建增强的AI清晰度评估提示词
            clarity_prompt = f"""
作为需求分析专家，请对以下需求进行全面的清晰度评估：

【需求信息】
标题：{title}
描述：{description}
验收标准：{acceptance_criteria}
优先级：{priority}
业务价值：{business_value}

【评估维度】
请从以下5个维度进行评估，每个维度0-1分：

1. 语义明确性 (20%)
   - 用词是否准确、具体
   - 是否避免歧义表达
   - 专业术语使用是否恰当

2. 逻辑完整性 (25%)
   - 需求描述逻辑是否清晰
   - 前因后果关系是否明确
   - 是否有遗漏的关键信息

3. 可操作性 (25%)
   - 需求是否可以直接指导开发
   - 验收标准是否具体可执行
   - 实现路径是否清晰

4. 一致性 (15%)
   - 标题与描述是否一致
   - 优先级与业务价值是否匹配
   - 验收标准与需求描述是否对应

5. 可测试性 (15%)
   - 需求是否可以被有效测试
   - 验收标准是否可量化验证
   - 成功标准是否明确

【输出格式】
请严格按照以下JSON格式输出评估结果：
{{
    "semantic_clarity": 0.85,
    "logical_completeness": 0.75,
    "operability": 0.80,
    "consistency": 0.90,
    "testability": 0.70,
    "overall_score": 0.78,
    "key_issues": ["具体的问题描述1", "具体的问题描述2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"]
}}

请确保overall_score是各维度的加权平均值。
"""
            
            # 调用AI服务评估
            ai_response = await self.ai_service.generate_response(clarity_prompt)
            
            try:
                # 尝试解析JSON响应
                import json
                import re
                
                # 提取JSON部分
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    
                    # 验证必要字段
                    if "overall_score" in result:
                        score = float(result["overall_score"])
                        # 确保分数在合理范围内
                        score = max(0.0, min(1.0, score))
                        
                        # 记录详细评估信息（用于调试和改进）
                        if "key_issues" in result or "improvement_suggestions" in result:
                            self.logger.debug(f"AI clarity assessment for '{title[:30]}...': "
                                           f"score={score:.3f}, "
                                           f"issues={result.get('key_issues', [])[:2]}")
                        
                        return score
                
                # 如果JSON解析失败，尝试提取数字分数
                score_match = re.search(r'overall_score["\']?\s*:\s*([0-9.]+)', ai_response)
                if not score_match:
                    score_match = re.search(r'([0-9.]+)', ai_response)
                
                if score_match:
                    score = float(score_match.group(1))
                    return max(0.0, min(1.0, score))
                
                # 如果都无法解析，使用基于关键词的简单评估
                return await self._fallback_clarity_assessment(title, description, acceptance_criteria)
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                self.logger.warning(f"Failed to parse AI clarity assessment response: {str(e)}")
                # 使用备用评估方法
                return await self._fallback_clarity_assessment(title, description, acceptance_criteria)
                
        except Exception as e:
            self.logger.error(f"Error in AI clarity assessment: {str(e)}")
            return 0.6
    
    async def _fallback_clarity_assessment(self, title: str, description: str, acceptance_criteria: List) -> float:
        """
        备用清晰度评估方法
        
        当AI评估失败时使用的基于规则的评估方法
        
        Args:
            title: 需求标题
            description: 需求描述
            acceptance_criteria: 验收标准
            
        Returns:
            float: 清晰度得分 (0-1)
        """
        try:
            score = 0.5  # 基础分数
            
            # 检查标题质量
            if title and 5 <= len(title.strip()) <= 50:
                score += 0.1
            
            # 检查描述质量
            if description:
                desc_len = len(description.strip())
                if desc_len >= 20:
                    score += 0.15
                if desc_len >= 50:
                    score += 0.1
            
            # 检查验收标准
            if acceptance_criteria:
                if isinstance(acceptance_criteria, list) and len(acceptance_criteria) >= 2:
                    score += 0.15
                elif isinstance(acceptance_criteria, str) and len(acceptance_criteria.strip()) > 10:
                    score += 0.1
            
            # 检查具体性指标
            combined_text = f"{title} {description}".lower()
            
            # 数字和量化指标
            import re
            if re.search(r'\d+', combined_text):
                score += 0.05
            
            # 动作词汇
            action_words = ["创建", "删除", "修改", "查询", "显示", "处理", "验证", "发送"]
            if any(word in combined_text for word in action_words):
                score += 0.05
            
            # 避免模糊词汇
            vague_words = ["合适", "良好", "优秀", "适当", "reasonable", "good", "appropriate"]
            vague_count = sum(1 for word in vague_words if word in combined_text)
            if vague_count == 0:
                score += 0.05
            elif vague_count <= 1:
                score += 0.02
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            self.logger.error(f"Error in fallback clarity assessment: {str(e)}")
            return 0.5
    
    async def generate_detailed_clarity_analysis(self, requirements_data: RequirementsData) -> Dict[str, Any]:
        """
        生成详细的需求清晰度分析报告
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            Dict[str, Any]: 详细的清晰度分析报告
        """
        try:
            if not requirements_data.requirements:
                return {
                    "overall_clarity_score": 0.0,
                    "total_requirements": 0,
                    "clarity_distribution": {},
                    "detailed_analysis": [],
                    "improvement_recommendations": [],
                    "analysis_summary": "没有需求数据可供分析"
                }
            
            # 执行整体清晰度分析
            overall_score = await self._assess_requirements_clarity(requirements_data)
            
            # 构建全局术语词典
            global_terms = await self._extract_domain_terms(requirements_data.requirements)
            
            # 详细分析每个需求
            detailed_analysis = []
            clarity_scores = []
            
            for i, req in enumerate(requirements_data.requirements):
                req_analysis = await self._analyze_single_requirement_clarity_detailed(req, global_terms, i + 1)
                detailed_analysis.append(req_analysis)
                clarity_scores.append(req_analysis["clarity_score"])
            
            # 计算清晰度分布
            clarity_distribution = self._calculate_clarity_distribution(clarity_scores)
            
            # 生成改进建议
            improvement_recommendations = await self._generate_clarity_improvement_recommendations(
                detailed_analysis, overall_score
            )
            
            # 生成分析摘要
            analysis_summary = self._generate_clarity_analysis_summary(
                overall_score, len(requirements_data.requirements), clarity_distribution
            )
            
            return {
                "overall_clarity_score": overall_score,
                "total_requirements": len(requirements_data.requirements),
                "clarity_distribution": clarity_distribution,
                "detailed_analysis": detailed_analysis,
                "improvement_recommendations": improvement_recommendations,
                "analysis_summary": analysis_summary,
                "global_terms": dict(list(global_terms.items())[:10]),  # 只返回前10个术语
                "analysis_metadata": {
                    "analysis_time": datetime.utcnow().isoformat(),
                    "analysis_version": "2.0",
                    "total_terms_extracted": len(global_terms)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error generating detailed clarity analysis: {str(e)}")
            return {
                "overall_clarity_score": 0.0,
                "total_requirements": len(requirements_data.requirements) if requirements_data.requirements else 0,
                "error": f"分析过程中发生错误: {str(e)}"
            }
    
    async def _analyze_single_requirement_clarity_detailed(self, requirement: Dict, global_terms: Dict[str, int], req_number: int) -> Dict[str, Any]:
        """
        详细分析单个需求的清晰度
        
        Args:
            requirement: 需求对象
            global_terms: 全局术语词典
            req_number: 需求编号
            
        Returns:
            Dict[str, Any]: 详细的单个需求清晰度分析
        """
        try:
            title = requirement.get("title", "")
            description = requirement.get("description", "")
            acceptance_criteria = requirement.get("acceptance_criteria", [])
            
            # 计算各维度得分
            language_clarity = await self._assess_language_clarity(title, description, acceptance_criteria)
            structure_completeness = await self._assess_structure_completeness(requirement)
            quantification = await self._assess_quantification_level(description, acceptance_criteria)
            terminology_consistency = await self._assess_terminology_consistency(requirement, global_terms)
            
            # AI语义分析
            ai_score = 0.6
            ai_details = {}
            if self.ai_service:
                ai_score = await self._ai_assess_requirement_clarity(requirement)
                # 这里可以扩展获取AI分析的详细信息
            
            # 计算总分
            weights = {
                "language_clarity": 0.25,
                "structure_completeness": 0.20,
                "quantification": 0.20,
                "terminology_consistency": 0.15,
                "ai_semantic_analysis": 0.20
            }
            
            clarity_score = (
                language_clarity * weights["language_clarity"] +
                structure_completeness * weights["structure_completeness"] +
                quantification * weights["quantification"] +
                terminology_consistency * weights["terminology_consistency"] +
                ai_score * weights["ai_semantic_analysis"]
            )
            
            # 识别具体问题
            issues = await self._identify_clarity_issues(requirement, {
                "language_clarity": language_clarity,
                "structure_completeness": structure_completeness,
                "quantification": quantification,
                "terminology_consistency": terminology_consistency
            })
            
            # 生成改进建议
            suggestions = await self._generate_requirement_clarity_suggestions(requirement, issues)
            
            return {
                "requirement_number": req_number,
                "requirement_id": requirement.get("id", f"req_{req_number}"),
                "title": title[:100] + "..." if len(title) > 100 else title,
                "clarity_score": round(clarity_score, 3),
                "dimension_scores": {
                    "language_clarity": round(language_clarity, 3),
                    "structure_completeness": round(structure_completeness, 3),
                    "quantification": round(quantification, 3),
                    "terminology_consistency": round(terminology_consistency, 3),
                    "ai_semantic_analysis": round(ai_score, 3)
                },
                "clarity_level": self._get_clarity_level(clarity_score),
                "identified_issues": issues,
                "improvement_suggestions": suggestions,
                "word_count": len(f"{title} {description}".split()),
                "has_acceptance_criteria": bool(acceptance_criteria),
                "criteria_count": len(acceptance_criteria) if isinstance(acceptance_criteria, list) else (1 if acceptance_criteria else 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing single requirement clarity: {str(e)}")
            return {
                "requirement_number": req_number,
                "requirement_id": requirement.get("id", f"req_{req_number}"),
                "title": requirement.get("title", "")[:50],
                "clarity_score": 0.0,
                "error": f"分析失败: {str(e)}"
            }
    
    def _calculate_clarity_distribution(self, clarity_scores: List[float]) -> Dict[str, Any]:
        """
        计算清晰度分布统计
        
        Args:
            clarity_scores: 清晰度得分列表
            
        Returns:
            Dict[str, Any]: 分布统计信息
        """
        try:
            if not clarity_scores:
                return {}
            
            # 按等级分类
            excellent = sum(1 for score in clarity_scores if score >= 0.8)
            good = sum(1 for score in clarity_scores if 0.6 <= score < 0.8)
            fair = sum(1 for score in clarity_scores if 0.4 <= score < 0.6)
            poor = sum(1 for score in clarity_scores if score < 0.4)
            
            total = len(clarity_scores)
            
            return {
                "excellent": {"count": excellent, "percentage": round(excellent / total * 100, 1)},
                "good": {"count": good, "percentage": round(good / total * 100, 1)},
                "fair": {"count": fair, "percentage": round(fair / total * 100, 1)},
                "poor": {"count": poor, "percentage": round(poor / total * 100, 1)},
                "average_score": round(sum(clarity_scores) / total, 3),
                "median_score": round(sorted(clarity_scores)[total // 2], 3),
                "min_score": round(min(clarity_scores), 3),
                "max_score": round(max(clarity_scores), 3)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating clarity distribution: {str(e)}")
            return {}
    
    def _get_clarity_level(self, score: float) -> str:
        """
        根据得分获取清晰度等级
        
        Args:
            score: 清晰度得分
            
        Returns:
            str: 清晰度等级
        """
        if score >= 0.8:
            return "优秀"
        elif score >= 0.6:
            return "良好"
        elif score >= 0.4:
            return "一般"
        else:
            return "较差"
    
    async def _identify_clarity_issues(self, requirement: Dict, dimension_scores: Dict[str, float]) -> List[str]:
        """
        识别清晰度问题
        
        Args:
            requirement: 需求对象
            dimension_scores: 各维度得分
            
        Returns:
            List[str]: 问题列表
        """
        try:
            issues = []
            
            title = requirement.get("title", "")
            description = requirement.get("description", "")
            acceptance_criteria = requirement.get("acceptance_criteria", [])
            
            # 语言清晰度问题
            if dimension_scores["language_clarity"] < 0.6:
                if len(description) < 20:
                    issues.append("需求描述过于简短，缺少必要的详细信息")
                
                # 检查模糊词汇
                vague_words = ["合适的", "足够的", "适当的", "良好的", "优秀的"]
                combined_text = f"{title} {description}".lower()
                found_vague = [word for word in vague_words if word in combined_text]
                if found_vague:
                    issues.append(f"使用了模糊词汇: {', '.join(found_vague[:3])}")
                
                # 检查动作词汇
                import re
                if not re.search(r'(创建|删除|修改|查询|显示|处理|验证|发送|create|delete|update|query|display|process|verify|send)', combined_text):
                    issues.append("缺少明确的动作词汇，不清楚具体要做什么")
            
            # 结构完整性问题
            if dimension_scores["structure_completeness"] < 0.6:
                if not title or len(title.strip()) < 5:
                    issues.append("需求标题缺失或过于简短")
                
                if not description or len(description.strip()) < 10:
                    issues.append("需求描述缺失或内容不足")
                
                if not acceptance_criteria:
                    issues.append("缺少验收标准")
                elif isinstance(acceptance_criteria, list) and len(acceptance_criteria) < 2:
                    issues.append("验收标准数量不足，建议至少包含2-3个验收条件")
                
                if not requirement.get("priority"):
                    issues.append("未设置需求优先级")
                
                if not requirement.get("business_value"):
                    issues.append("未明确业务价值")
            
            # 量化指标问题
            if dimension_scores["quantification"] < 0.5:
                issues.append("缺少量化指标，建议添加具体的数字、时间、性能等可测量的标准")
            
            # 术语一致性问题
            if dimension_scores["terminology_consistency"] < 0.6:
                issues.append("术语使用不够一致，建议统一关键术语的表达方式")
            
            return issues
            
        except Exception as e:
            self.logger.error(f"Error identifying clarity issues: {str(e)}")
            return ["分析过程中发生错误"]
    
    async def _generate_requirement_clarity_suggestions(self, requirement: Dict, issues: List[str]) -> List[str]:
        """
        为单个需求生成清晰度改进建议
        
        Args:
            requirement: 需求对象
            issues: 识别出的问题列表
            
        Returns:
            List[str]: 改进建议列表
        """
        try:
            suggestions = []
            
            title = requirement.get("title", "")
            description = requirement.get("description", "")
            acceptance_criteria = requirement.get("acceptance_criteria", [])
            
            # 基于问题生成针对性建议
            for issue in issues:
                if "描述过于简短" in issue:
                    suggestions.append("扩展需求描述，添加背景信息、使用场景、预期效果等详细内容")
                
                elif "模糊词汇" in issue:
                    suggestions.append("用具体的标准替换模糊词汇，如用'响应时间小于2秒'替换'响应速度快'")
                
                elif "动作词汇" in issue:
                    suggestions.append("明确指出系统需要执行的具体操作，使用'创建'、'删除'、'修改'等明确的动词")
                
                elif "标题" in issue:
                    suggestions.append("完善需求标题，确保标题能够准确概括需求的核心内容")
                
                elif "验收标准" in issue:
                    if not acceptance_criteria:
                        suggestions.append("添加验收标准，明确定义需求完成的判断条件")
                    else:
                        suggestions.append("增加验收标准的数量和具体性，确保每个关键功能点都有对应的验收条件")
                
                elif "量化指标" in issue:
                    suggestions.append("添加可量化的指标，如时间限制、数量要求、性能标准等")
                
                elif "术语一致性" in issue:
                    suggestions.append("统一术语使用，建立项目术语词典，确保同一概念在所有需求中使用相同的表达")
                
                elif "优先级" in issue:
                    suggestions.append("设置需求优先级（高/中/低），帮助开发团队合理安排开发顺序")
                
                elif "业务价值" in issue:
                    suggestions.append("明确说明该需求的业务价值和实现后的预期收益")
            
            # 添加通用改进建议
            if len(suggestions) == 0:
                suggestions.append("需求整体质量良好，可考虑进一步优化表达的准确性和完整性")
            elif len(suggestions) >= 3:
                suggestions.append("建议优先处理前3个问题，逐步提升需求质量")
            
            return suggestions[:5]  # 最多返回5个建议
            
        except Exception as e:
            self.logger.error(f"Error generating requirement clarity suggestions: {str(e)}")
            return ["生成建议时发生错误，请手动检查需求质量"]
    
    async def _generate_clarity_improvement_recommendations(self, detailed_analysis: List[Dict], overall_score: float) -> List[Dict[str, Any]]:
        """
        生成整体清晰度改进建议
        
        Args:
            detailed_analysis: 详细分析结果列表
            overall_score: 整体清晰度得分
            
        Returns:
            List[Dict[str, Any]]: 改进建议列表
        """
        try:
            recommendations = []
            
            # 统计问题类型
            all_issues = []
            poor_requirements = []
            
            for analysis in detailed_analysis:
                if analysis.get("clarity_score", 0) < 0.4:
                    poor_requirements.append(analysis)
                
                issues = analysis.get("identified_issues", [])
                all_issues.extend(issues)
            
            # 统计最常见的问题
            from collections import Counter
            issue_counts = Counter(all_issues)
            common_issues = issue_counts.most_common(5)
            
            # 生成优先级建议
            if poor_requirements:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "质量提升",
                    "title": f"优先改进{len(poor_requirements)}个低质量需求",
                    "description": f"发现{len(poor_requirements)}个需求的清晰度得分低于0.4，需要立即改进",
                    "action_items": [
                        f"重点关注需求: {', '.join([req.get('title', '')[:30] for req in poor_requirements[:3]])}",
                        "组织需求评审会议，邀请相关干系人参与",
                        "使用需求模板确保信息完整性",
                        "建立需求质量检查清单"
                    ],
                    "expected_benefit": "显著提升需求质量，减少开发过程中的返工",
                    "estimated_effort": "2-3天"
                })
            
            # 基于常见问题生成建议
            for issue, count in common_issues:
                if count >= 2:  # 至少出现2次的问题
                    if "模糊词汇" in issue:
                        recommendations.append({
                            "priority": "MEDIUM",
                            "category": "表达规范",
                            "title": "统一消除模糊词汇",
                            "description": f"在{count}个需求中发现模糊词汇使用，影响需求理解的准确性",
                            "action_items": [
                                "建立禁用词汇清单，避免使用模糊表达",
                                "用具体的数字和标准替换主观描述",
                                "建立需求描述规范和示例",
                                "进行需求描述培训"
                            ],
                            "expected_benefit": "提高需求表达的准确性和一致性",
                            "estimated_effort": "1-2天"
                        })
                    
                    elif "验收标准" in issue:
                        recommendations.append({
                            "priority": "HIGH",
                            "category": "验收标准",
                            "title": "完善验收标准定义",
                            "description": f"{count}个需求缺少完整的验收标准，影响开发和测试",
                            "action_items": [
                                "为每个需求定义至少2-3个验收标准",
                                "确保验收标准可测试、可验证",
                                "使用GIVEN-WHEN-THEN格式描述验收场景",
                                "与测试团队协作完善验收条件"
                            ],
                            "expected_benefit": "明确需求完成标准，提高交付质量",
                            "estimated_effort": "2-3天"
                        })
                    
                    elif "量化指标" in issue:
                        recommendations.append({
                            "priority": "MEDIUM",
                            "category": "量化标准",
                            "title": "增加量化指标",
                            "description": f"{count}个需求缺少量化指标，难以进行客观评估",
                            "action_items": [
                                "为性能相关需求添加具体的时间、容量指标",
                                "为用户体验需求定义可测量的标准",
                                "建立量化指标词典和参考标准",
                                "定期评估和调整量化标准"
                            ],
                            "expected_benefit": "提供客观的评估标准，便于验收和测试",
                            "estimated_effort": "1-2天"
                        })
            
            # 基于整体得分生成建议
            if overall_score < 0.6:
                recommendations.append({
                    "priority": "CRITICAL",
                    "category": "整体改进",
                    "title": "全面提升需求清晰度",
                    "description": f"整体需求清晰度得分为{overall_score:.2f}，低于建议标准(0.6)",
                    "action_items": [
                        "制定需求质量提升计划",
                        "建立需求评审流程",
                        "提供需求编写培训",
                        "使用需求管理工具和模板",
                        "定期进行需求质量评估"
                    ],
                    "expected_benefit": "全面提升项目需求质量，降低项目风险",
                    "estimated_effort": "1-2周"
                })
            elif overall_score < 0.8:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "持续改进",
                    "title": "优化需求清晰度",
                    "description": f"整体需求清晰度得分为{overall_score:.2f}，有进一步优化空间",
                    "action_items": [
                        "重点关注得分较低的需求",
                        "建立需求质量监控机制",
                        "定期进行需求回顾和改进",
                        "分享最佳实践和经验"
                    ],
                    "expected_benefit": "持续提升需求质量，确保项目成功",
                    "estimated_effort": "3-5天"
                })
            
            return recommendations[:5]  # 最多返回5个建议
            
        except Exception as e:
            self.logger.error(f"Error generating clarity improvement recommendations: {str(e)}")
            return []
    
    def _generate_clarity_analysis_summary(self, overall_score: float, total_requirements: int, distribution: Dict) -> str:
        """
        生成清晰度分析摘要
        
        Args:
            overall_score: 整体得分
            total_requirements: 需求总数
            distribution: 分布统计
            
        Returns:
            str: 分析摘要
        """
        try:
            if not distribution:
                return f"共分析{total_requirements}个需求，整体清晰度得分为{overall_score:.2f}"
            
            excellent_count = distribution.get("excellent", {}).get("count", 0)
            poor_count = distribution.get("poor", {}).get("count", 0)
            
            summary_parts = [
                f"共分析{total_requirements}个需求",
                f"整体清晰度得分为{overall_score:.2f}"
            ]
            
            if excellent_count > 0:
                summary_parts.append(f"其中{excellent_count}个需求质量优秀")
            
            if poor_count > 0:
                summary_parts.append(f"{poor_count}个需求需要重点改进")
            
            # 添加评级
            if overall_score >= 0.8:
                summary_parts.append("整体质量优秀")
            elif overall_score >= 0.6:
                summary_parts.append("整体质量良好")
            elif overall_score >= 0.4:
                summary_parts.append("整体质量一般，建议改进")
            else:
                summary_parts.append("整体质量较差，需要立即改进")
            
            return "，".join(summary_parts) + "。"
            
        except Exception as e:
            self.logger.error(f"Error generating clarity analysis summary: {str(e)}")
            return f"共分析{total_requirements}个需求，整体清晰度得分为{overall_score:.2f}。"
    
    async def _ai_assess_requirement_testability(self, requirement: Dict) -> float:
        """
        使用AI评估需求可测试性
        
        Args:
            requirement: 需求对象
            
        Returns:
            float: AI评估的可测试性得分 (0-1)
        """
        try:
            if not self.ai_service:
                return 0.5  # 默认中等分数
            
            title = requirement.get("title", "")
            description = requirement.get("description", "")
            acceptance_criteria = requirement.get("acceptance_criteria", [])
            
            # 构建AI可测试性评估提示词
            testability_prompt = f"""
请评估以下需求的可测试性（0-1分）：

需求标题：{title}
需求描述：{description}
验收标准：{acceptance_criteria}

评估标准：
1. 验收标准是否明确可验证（30%）
2. 是否有明确的输入输出定义（25%）
3. 是否避免主观性描述（20%）
4. 是否包含可量化的指标（25%）

可测试性高的特征：
- 有具体的数值标准
- 明确的操作步骤
- 可观察的结果
- 避免"用户友好"、"美观"等主观词汇

请只返回一个0到1之间的数字分数，保留两位小数。
例如：0.65
"""
            
            # 调用AI服务评估
            ai_response = await self.ai_service.generate_response(testability_prompt)
            
            try:
                # 提取数字分数
                import re
                score_match = re.search(r'(\d+\.?\d*)', ai_response.strip())
                if score_match:
                    score = float(score_match.group(1))
                    # 确保分数在有效范围内
                    if score > 1.0:
                        score = score / 100  # 如果是百分比形式，转换为小数
                    return max(0.0, min(1.0, score))
                else:
                    # 如果无法提取数字，使用关键词分析
                    return await self._fallback_testability_assessment(title, description, acceptance_criteria)
                    
            except (ValueError, TypeError):
                return await self._fallback_testability_assessment(title, description, acceptance_criteria)
                
        except Exception as e:
            self.logger.error(f"Error in AI testability assessment: {str(e)}")
            return 0.5
    
    async def _fallback_testability_assessment(self, title: str, description: str, acceptance_criteria: List) -> float:
        """
        备用可测试性评估方法
        
        Args:
            title: 需求标题
            description: 需求描述
            acceptance_criteria: 验收标准
            
        Returns:
            float: 可测试性得分 (0-1)
        """
        try:
            score = 0.0
            combined_text = f"{title} {description} {' '.join(str(c) for c in acceptance_criteria if c)}".lower()
            
            # 检查可测试的关键词
            testable_keywords = [
                "应该", "必须", "能够", "显示", "返回", "包含", "等于", "大于", "小于",
                "创建", "删除", "修改", "查询", "验证", "检查", "确认"
            ]
            
            found_keywords = sum(1 for keyword in testable_keywords if keyword in combined_text)
            score += min(0.3, found_keywords * 0.05)
            
            # 检查数值指标
            import re
            if re.search(r'\d+', combined_text):
                score += 0.2
            
            # 检查输入输出描述
            if any(word in combined_text for word in ["输入", "输出", "参数", "返回", "结果"]):
                score += 0.2
            
            # 检查是否避免主观词汇
            subjective_words = ["美观", "友好", "直观", "简单", "复杂", "好看", "漂亮"]
            has_subjective = any(word in combined_text for word in subjective_words)
            if not has_subjective:
                score += 0.1
            
            # 检查验收标准质量
            if acceptance_criteria and len(acceptance_criteria) >= 2:
                score += 0.2
            
            return min(1.0, score)
            
        except Exception as e:
            self.logger.error(f"Error in fallback testability assessment: {str(e)}")
            return 0.5
    
    async def _ai_assess_requirements_consistency(self, requirements_data: RequirementsData) -> float:
        """
        使用AI评估需求一致性
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            float: AI评估的一致性得分 (0-1)
        """
        try:
            if not self.ai_service or len(requirements_data.requirements) < 2:
                return 0.8  # 默认分数
            
            # 构建需求摘要用于AI分析
            requirements_summary = []
            for i, req in enumerate(requirements_data.requirements[:5], 1):  # 最多分析5个需求
                title = req.get("title", "")
                description = req.get("description", "")[:200]  # 限制长度
                priority = req.get("priority", "")
                requirements_summary.append(f"{i}. {title} - {description} (优先级: {priority})")
            
            consistency_prompt = f"""
请评估以下需求列表的一致性（0-1分）：

{chr(10).join(requirements_summary)}

评估标准：
1. 术语使用是否一致（30%）
2. 描述风格是否统一（25%）
3. 优先级分布是否合理（25%）
4. 需求粒度是否相近（20%）

一致性高的特征：
- 使用相同的术语表达相同概念
- 描述详细程度相近
- 优先级分布合理（不全是高优先级）
- 需求复杂度相当

请只返回一个0到1之间的数字分数，保留两位小数。
例如：0.72
"""
            
            ai_response = await self.ai_service.generate_response(consistency_prompt)
            
            try:
                import re
                score_match = re.search(r'(\d+\.?\d*)', ai_response.strip())
                if score_match:
                    score = float(score_match.group(1))
                    if score > 1.0:
                        score = score / 100
                    return max(0.0, min(1.0, score))
                else:
                    return 0.7  # 默认分数
                    
            except (ValueError, TypeError):
                return 0.7
                
        except Exception as e:
            self.logger.error(f"Error in AI consistency assessment: {str(e)}")
            return 0.7
    
    async def _ai_assess_requirements_consistency(self, requirements_data: RequirementsData) -> float:
        """
        使用AI评估需求一致性
        
        Args:
            requirements_data: 需求数据
            
        Returns:
            float: AI评估的一致性得分 (0-1)
        """
        try:
            if not self.ai_service or len(requirements_data.requirements) < 2:
                return 0.5  # 默认中等分数
            
            # 构建需求列表文本
            requirements_text = ""
            for i, req in enumerate(requirements_data.requirements, 1):
                title = req.get("title", f"需求{i}")
                description = req.get("description", "")
                priority = req.get("priority", "未设置")
                category = req.get("category", "未分类")
                
                requirements_text += f"""
需求{i}：
标题：{title}
描述：{description}
优先级：{priority}
分类：{category}
"""
            
            # 构建AI一致性评估提示词
            consistency_prompt = f"""
请评估以下需求集合的一致性（0-1分）：

{requirements_text}

评估标准：
1. 描述风格是否一致（25%）
2. 优先级分布是否合理（25%）
3. 分类体系是否统一（25%）
4. 术语使用是否一致（25%）

一致性问题包括：
- 描述详细程度差异过大
- 高优先级需求过多（超过30%）
- 分类不统一或过多未分类
- 同一概念使用不同术语

请只返回一个0到1之间的数字分数，保留两位小数。
例如：0.72
"""
            
            # 调用AI服务评估
            ai_response = await self.ai_service.generate_response(consistency_prompt)
            
            try:
                # 提取数字分数
                import re
                score_match = re.search(r'(\d+\.?\d*)', ai_response.strip())
                if score_match:
                    score = float(score_match.group(1))
                    # 确保分数在0-1范围内
                    return max(0.0, min(1.0, score))
                else:
                    return 0.5  # 如果无法解析，返回默认分数
            except (ValueError, AttributeError):
                return 0.5  # 解析失败时返回默认分数
                
        except Exception as e:
            self.logger.error(f"Error in AI consistency assessment: {str(e)}")
            return 0.5
    
    async def _generate_ai_powered_requirements_suggestions(self, analysis: RequirementsQualityAnalysis) -> List[Dict]:
        """
        使用AI生成个性化需求改进建议
        
        Args:
            analysis: 需求质量分析结果
            
        Returns:
            List[Dict]: AI生成的建议列表
        """
        try:
            if not self.ai_service:
                return []
            
            # 构建分析结果摘要
            analysis_summary = f"""
需求质量分析结果：
- 完整性得分：{analysis.completeness_score:.2f}
- 清晰度得分：{analysis.clarity_score:.2f}
- 一致性得分：{analysis.consistency_score:.2f}
- 可测试性得分：{analysis.testability_score:.2f}
- 总体得分：{analysis.overall_score:.2f}
- 问题需求数量：{len(analysis.problematic_requirements)}
"""
            
            # 构建问题需求详情
            problematic_details = ""
            if analysis.problematic_requirements:
                problematic_details = "\n主要问题需求："
                for req in analysis.problematic_requirements[:3]:  # 只显示前3个
                    problematic_details += f"""
- {req.get('requirement_title', '未知需求')}：{', '.join(req.get('issues', []))}
"""
            
            # 构建AI建议生成提示词
            suggestion_prompt = f"""
基于以下需求质量分析结果，请生成2-3个具体的改进建议：

{analysis_summary}
{problematic_details}

请为每个建议提供以下信息：
1. 建议标题（简洁明了）
2. 问题描述（说明具体问题）
3. 改进措施（3-4个具体行动项）
4. 预期收益（改进后的效果）
5. 工作量估算（天数）

请以JSON格式返回，例如：
[
  {{
    "title": "优化需求描述规范性",
    "description": "部分需求描述过于简短或模糊",
    "action_items": ["建立需求描述模板", "补充关键信息", "统一术语定义"],
    "expected_benefit": "提高需求理解准确性",
    "estimated_effort": "2-3天"
  }}
]
"""
            
            # 调用AI服务生成建议
            ai_response = await self.ai_service.generate_response(suggestion_prompt)
            
            try:
                # 解析AI返回的JSON
                import json
                ai_suggestions_raw = json.loads(ai_response.strip())
                
                ai_suggestions = []
                for suggestion in ai_suggestions_raw[:3]:  # 最多3个AI建议
                    ai_suggestions.append({
                        "type": SuggestionType.QUALITY_IMPROVEMENT.value,
                        "category": SuggestionCategory.CLARITY.value,  # 默认分类
                        "title": suggestion.get("title", "AI建议"),
                        "description": suggestion.get("description", ""),
                        "priority": SuggestionPriority.MEDIUM.value,
                        "action_items": suggestion.get("action_items", []),
                        "expected_benefit": suggestion.get("expected_benefit", ""),
                        "estimated_effort": suggestion.get("estimated_effort", "1-2天"),
                        "ai_generated": True,  # 标记为AI生成
                        "confidence_score": 0.8  # AI建议的置信度
                    })
                
                return ai_suggestions
                
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                self.logger.warning(f"Failed to parse AI suggestions JSON: {str(e)}")
                # 如果JSON解析失败，尝试文本解析
                return await self._parse_ai_suggestions_text(ai_response)
                
        except Exception as e:
            self.logger.error(f"Error generating AI-powered suggestions: {str(e)}")
            return []
    
    async def _parse_ai_suggestions_text(self, ai_response: str) -> List[Dict]:
        """
        解析AI返回的文本格式建议
        
        Args:
            ai_response: AI返回的文本
            
        Returns:
            List[Dict]: 解析后的建议列表
        """
        try:
            suggestions = []
            lines = ai_response.split('\n')
            current_suggestion = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 检测建议标题
                if line.startswith('标题') or line.startswith('建议') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.'):
                    if current_suggestion:
                        suggestions.append(self._format_ai_suggestion(current_suggestion))
                        current_suggestion = {}
                    
                    # 提取标题
                    title = line.split('：')[-1].split(':')[-1].strip()
                    current_suggestion['title'] = title
                
                elif '描述' in line or '问题' in line:
                    description = line.split('：')[-1].split(':')[-1].strip()
                    current_suggestion['description'] = description
                
                elif '收益' in line or '效果' in line:
                    benefit = line.split('：')[-1].split(':')[-1].strip()
                    current_suggestion['expected_benefit'] = benefit
                
                elif '工作量' in line or '估算' in line:
                    effort = line.split('：')[-1].split(':')[-1].strip()
                    current_suggestion['estimated_effort'] = effort
            
            # 添加最后一个建议
            if current_suggestion:
                suggestions.append(self._format_ai_suggestion(current_suggestion))
            
            return suggestions[:2]  # 最多返回2个建议
            
        except Exception as e:
            self.logger.error(f"Error parsing AI suggestions text: {str(e)}")
            return []
    
    def _format_ai_suggestion(self, suggestion_data: Dict) -> Dict:
        """
        格式化AI建议数据
        
        Args:
            suggestion_data: 原始建议数据
            
        Returns:
            Dict: 格式化后的建议
        """
        return {
            "type": SuggestionType.QUALITY_IMPROVEMENT.value,
            "category": SuggestionCategory.CLARITY.value,
            "title": suggestion_data.get("title", "AI改进建议"),
            "description": suggestion_data.get("description", ""),
            "priority": SuggestionPriority.MEDIUM.value,
            "action_items": suggestion_data.get("action_items", ["参考AI建议进行改进"]),
            "expected_benefit": suggestion_data.get("expected_benefit", "提升需求质量"),
            "estimated_effort": suggestion_data.get("estimated_effort", "1-2天"),
            "ai_generated": True,
            "confidence_score": 0.7
        }
    
    def _calculate_issue_severity(self, issues: List[str]) -> str:
        """
        计算问题严重程度
        
        Args:
            issues: 问题列表
            
        Returns:
            str: 严重程度 (LOW, MEDIUM, HIGH, CRITICAL)
        """
        high_severity_issues = ["缺少验收标准", "需求描述过于简短", "未明确业务价值", "逻辑不一致", "难以测试验证"]
        critical_issues = ["需求描述过于复杂，建议拆分", "技术实现困难", "业务价值不明确"]
        
        if any(issue in critical_issues for issue in issues):
            return "CRITICAL"
        elif any(issue in high_severity_issues for issue in issues):
            return "HIGH"
        elif len(issues) > 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _generate_requirements_quality_suggestions(self, analysis: RequirementsQualityAnalysis) -> List[Dict]:
        """
        生成需求质量改进建议
        
        Args:
            analysis: 需求质量分析结果
            
        Returns:
            List[Dict]: 建议列表
        """
        try:
            suggestions = []
            
            # 针对完整性问题的建议
            if analysis.completeness_score < self.config["min_completeness_score"]:
                suggestions.append({
                    "type": SuggestionType.QUALITY_IMPROVEMENT.value,
                    "category": SuggestionCategory.COMPLETENESS.value,
                    "title": "提升需求完整性",
                    "description": f"当前需求完整性得分为{analysis.completeness_score:.2f}，建议完善需求描述、验收标准等关键信息",
                    "priority": SuggestionPriority.HIGH.value,
                    "action_items": [
                        "为缺少描述的需求补充详细说明",
                        "为所有需求定义明确的验收标准",
                        "确保每个需求都有明确的优先级和业务价值",
                        "建立需求模板确保信息完整性"
                    ],
                    "expected_benefit": "提高需求理解准确性，减少开发过程中的返工",
                    "estimated_effort": "2-3天"
                })
            
            # 针对清晰度问题的建议
            if analysis.clarity_score < self.config["min_clarity_score"]:
                suggestions.append({
                    "type": SuggestionType.QUALITY_IMPROVEMENT.value,
                    "category": SuggestionCategory.CLARITY.value,
                    "title": "改善需求清晰度",
                    "description": f"当前需求清晰度得分为{analysis.clarity_score:.2f}，建议使用更明确的表述",
                    "priority": SuggestionPriority.HIGH.value,
                    "action_items": [
                        "避免使用模糊词汇如'合适的'、'足够的'等",
                        "使用具体的数字和标准替代主观描述",
                        "为技术术语提供明确定义",
                        "使用用户故事格式规范需求表述"
                    ],
                    "expected_benefit": "减少需求理解歧义，提高开发效率",
                    "estimated_effort": "1-2天"
                })
            
            # 针对可测试性问题的建议
            if analysis.testability_score < self.config["min_testability_score"]:
                suggestions.append({
                    "type": SuggestionType.QUALITY_IMPROVEMENT.value,
                    "category": SuggestionCategory.TESTABILITY.value,
                    "title": "增强需求可测试性",
                    "description": f"当前需求可测试性得分为{analysis.testability_score:.2f}，建议明确测试标准",
                    "priority": SuggestionPriority.MEDIUM.value,
                    "action_items": [
                        "为每个需求定义可量化的验收标准",
                        "明确输入条件和预期输出",
                        "识别边界条件和异常场景",
                        "与测试团队协作完善测试要点"
                    ],
                    "expected_benefit": "提高测试覆盖率和测试效果",
                    "estimated_effort": "2-3天"
                })
            
            # 针对问题需求的建议
            if analysis.problematic_requirements:
                high_severity_count = len([req for req in analysis.problematic_requirements 
                                         if req.get("severity") == "HIGH"])
                if high_severity_count > 0:
                    suggestions.append({
                        "type": SuggestionType.URGENT_FIX.value,
                        "category": SuggestionCategory.PROBLEMATIC_REQUIREMENTS.value,
                        "title": "修复高风险需求问题",
                        "description": f"发现{high_severity_count}个高风险需求问题，需要立即处理",
                        "priority": SuggestionPriority.CRITICAL.value,
                        "action_items": [
                            f"优先处理{high_severity_count}个高风险需求",
                            "组织需求评审会议讨论问题需求",
                            "邀请相关干系人澄清需求细节",
                            "建立需求质量检查清单"
                        ],
                        "expected_benefit": "避免因需求问题导致的项目风险",
                        "estimated_effort": "3-5天",
                        "problematic_requirements": analysis.problematic_requirements
                    })
            
            # AI生成的个性化建议（如果AI服务可用）
            if self.ai_service:
                ai_suggestions = await self._generate_ai_powered_requirements_suggestions(analysis)
                suggestions.extend(ai_suggestions)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating requirements quality suggestions: {str(e)}")
            return []
    
    async def _generate_requirements_coverage_suggestions(self, context: ProjectContext) -> List[Dict]:
        """
        生成需求覆盖度建议
        
        Args:
            context: 项目上下文
            
        Returns:
            List[Dict]: 建议列表
        """
        try:
            suggestions = []
            
            # 分析功能覆盖度
            functional_coverage = await self._analyze_functional_coverage(context)
            if functional_coverage.missing_areas:
                suggestions.append({
                    "type": SuggestionType.COVERAGE_IMPROVEMENT.value,
                    "category": SuggestionCategory.FUNCTIONAL_COVERAGE.value,
                    "title": "补充功能需求覆盖",
                    "description": f"发现{len(functional_coverage.missing_areas)}个功能领域缺少需求定义",
                    "priority": SuggestionPriority.MEDIUM.value,
                    "action_items": [
                        f"补充以下功能领域的需求：{', '.join(functional_coverage.missing_areas[:3])}",
                        "与产品经理确认功能范围",
                        "分析竞品功能作为参考",
                        "评估新增需求对项目计划的影响"
                    ],
                    "expected_benefit": "确保产品功能完整性",
                    "estimated_effort": "3-5天"
                })
            
            # 分析非功能需求覆盖度
            nonfunctional_coverage = await self._analyze_nonfunctional_coverage(context)
            if nonfunctional_coverage.missing_types:
                suggestions.append({
                    "type": SuggestionType.COVERAGE_IMPROVEMENT.value,
                    "category": SuggestionCategory.NONFUNCTIONAL_COVERAGE.value,
                    "title": "完善非功能需求",
                    "description": f"缺少{len(nonfunctional_coverage.missing_types)}类非功能需求定义",
                    "priority": SuggestionPriority.MEDIUM.value,
                    "action_items": [
                        f"定义{', '.join(nonfunctional_coverage.missing_types)}相关需求",
                        "设定性能、安全、可用性等指标",
                        "考虑系统扩展性和维护性要求",
                        "与架构师协作确定技术约束"
                    ],
                    "expected_benefit": "确保系统质量属性满足要求",
                    "estimated_effort": "2-4天"
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating requirements coverage suggestions: {str(e)}")
            return []
    
    async def _generate_requirements_process_suggestions(self, context: ProjectContext) -> List[Dict]:
        """
        生成需求管理流程建议
        
        Args:
            context: 项目上下文
            
        Returns:
            List[Dict]: 建议列表
        """
        try:
            suggestions = []
            
            # 检查需求变更管理
            if context.requirements and len(context.requirements) > 10:
                suggestions.append({
                    "type": SuggestionType.PROJECT_MANAGEMENT.value,
                    "category": SuggestionCategory.MAINTAINABILITY.value,
                    "title": "建立需求变更管理流程",
                    "description": "项目需求较多，建议建立正式的需求变更管理流程",
                    "priority": SuggestionPriority.MEDIUM.value,
                    "action_items": [
                        "制定需求变更申请模板",
                        "建立变更影响评估机制",
                        "设立需求变更审批流程",
                        "建立需求版本管理制度"
                    ],
                    "expected_benefit": "控制需求变更风险，保证项目稳定性",
                    "estimated_effort": "1-2天"
                })
            
            # 检查需求追溯性
            requirements_with_tests = sum(1 for req in context.requirements 
                                        if req.get("test_cases") or req.get("linked_tests"))
            if requirements_with_tests < len(context.requirements) * 0.5:
                suggestions.append({
                    "type": SuggestionType.COVERAGE_IMPROVEMENT.value,
                    "category": SuggestionCategory.TESTABILITY.value,
                    "title": "建立需求测试追溯关系",
                    "description": "需求与测试用例的关联度较低，建议建立追溯关系",
                    "priority": SuggestionPriority.MEDIUM.value,
                    "action_items": [
                        "为每个需求关联对应的测试用例",
                        "建立需求-测试映射表",
                        "使用工具管理追溯关系",
                        "定期检查追溯关系完整性"
                    ],
                    "expected_benefit": "提高测试覆盖率，便于影响分析",
                    "estimated_effort": "2-3天"
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating requirements process suggestions: {str(e)}")
            return []
    
    async def _analyze_functional_coverage(self, context: ProjectContext) -> FunctionalCoverageAnalysis:
        """
        分析功能覆盖度
        
        Args:
            context: 项目上下文
            
        Returns:
            FunctionalCoverageAnalysis: 功能覆盖度分析结果
        """
        try:
            # 基于项目类型获取期望的功能领域
            expected_areas = self.project_functional_areas.get(
                context.project_type or "web_application", 
                self.project_functional_areas["web_application"]
            )
            
            # 从需求中提取当前的功能领域
            current_areas = []
            if context.requirements:
                for req in context.requirements:
                    category = req.get("category", "")
                    title = req.get("title", "")
                    description = req.get("description", "")
                    
                    # 简单的关键词匹配来识别功能领域
                    for area in expected_areas:
                        if (area in category or area in title or area in description):
                            if area not in current_areas:
                                current_areas.append(area)
            
            missing_areas = [area for area in expected_areas if area not in current_areas]
            coverage_rate = len(current_areas) / len(expected_areas) if expected_areas else 1.0
            
            return FunctionalCoverageAnalysis(
                expected_areas=expected_areas,
                current_areas=current_areas,
                missing_areas=missing_areas,
                coverage_rate=coverage_rate
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing functional coverage: {str(e)}")
            return FunctionalCoverageAnalysis([], [], [], 0.0)
    
    async def _analyze_nonfunctional_coverage(self, context: ProjectContext) -> NonFunctionalCoverageAnalysis:
        """
        分析非功能需求覆盖度
        
        Args:
            context: 项目上下文
            
        Returns:
            NonFunctionalCoverageAnalysis: 非功能需求覆盖度分析结果
        """
        try:
            required_types = ["性能", "安全", "可用性", "可维护性", "可扩展性", "兼容性"]
            current_types = []
            
            if context.requirements:
                for req in context.requirements:
                    title = req.get("title", "")
                    description = req.get("description", "")
                    category = req.get("category", "")
                    
                    for nf_type in required_types:
                        if (nf_type in title or nf_type in description or nf_type in category):
                            if nf_type not in current_types:
                                current_types.append(nf_type)
            
            missing_types = [nf_type for nf_type in required_types if nf_type not in current_types]
            coverage_rate = len(current_types) / len(required_types)
            
            return NonFunctionalCoverageAnalysis(
                required_types=required_types,
                current_types=current_types,
                missing_types=missing_types,
                coverage_rate=coverage_rate
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing nonfunctional coverage: {str(e)}")
            return NonFunctionalCoverageAnalysis([], [], [], 0.0)
    
    async def generate_quality_suggestions(self, context: ProjectContext) -> List[Dict]:
        """
        生成质量相关建议
        
        Args:
            context: 项目上下文
            
        Returns:
            List[Dict]: 质量建议列表
        """
        try:
            suggestions = []
            
            if not context.quality_metrics:
                return suggestions
            
            # 分析缺陷趋势
            defect_trend = context.quality_metrics.get("defect_trend", {})
            if defect_trend.get("increasing", False):
                suggestions.append({
                    "type": SuggestionType.QUALITY_IMPROVEMENT.value,
                    "category": SuggestionCategory.PERFORMANCE.value,
                    "title": "关注缺陷趋势上升",
                    "description": "最近缺陷数量呈上升趋势，建议加强质量控制",
                    "priority": SuggestionPriority.HIGH.value,
                    "action_items": [
                        "分析缺陷根因，识别问题模式",
                        "加强代码审查流程",
                        "增加单元测试覆盖率",
                        "组织质量回顾会议"
                    ],
                    "expected_benefit": "降低缺陷率，提高产品质量",
                    "estimated_effort": "1-2周"
                })
            
            # 分析测试覆盖率
            test_coverage = context.quality_metrics.get("test_coverage", 0)
            if test_coverage < 0.8:
                suggestions.append({
                    "type": SuggestionType.TEST_IMPROVEMENT.value,
                    "category": SuggestionCategory.TESTABILITY.value,
                    "title": "提升测试覆盖率",
                    "description": f"当前测试覆盖率为{test_coverage*100:.1f}%，建议提升至80%以上",
                    "priority": SuggestionPriority.MEDIUM.value,
                    "action_items": [
                        "识别未覆盖的代码模块",
                        "编写针对性的测试用例",
                        "建立测试覆盖率监控",
                        "设定测试覆盖率目标"
                    ],
                    "expected_benefit": "提高代码质量，减少生产环境问题",
                    "estimated_effort": "1-2周"
                })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating quality suggestions: {str(e)}")
            return []
    
    async def generate_risk_based_suggestions(self, context: ProjectContext) -> List[Dict]:
        """
        生成基于风险识别的建议
        
        Args:
            context: 项目上下文
            
        Returns:
            List[Dict]: 风险缓解建议列表
        """
        try:
            suggestions = []
            
            # 执行完整的项目状况分析以获取风险因素
            analysis_result = await self.analyze_project_status(context)
            risk_factors = analysis_result.get("risk_factors", [])
            
            if not risk_factors:
                return suggestions
            
            # 为每个风险因素生成对应的建议
            for risk in risk_factors:
                risk_suggestion = await self._convert_risk_to_suggestion(risk, context)
                if risk_suggestion:
                    suggestions.append(risk_suggestion)
            
            # 生成风险管理总体建议
            if len(risk_factors) > 3:
                overall_risk_suggestion = {
                    "type": "RISK_MANAGEMENT",
                    "category": "OVERALL_RISK",
                    "title": "建立综合风险管理机制",
                    "description": f"项目存在{len(risk_factors)}个风险因素，需要建立系统性风险管理",
                    "priority": "HIGH",
                    "action_items": [
                        "建立项目风险管理委员会",
                        "制定风险识别和评估流程",
                        "建立风险监控和预警机制",
                        "定期进行风险评估和更新",
                        "制定风险应急响应预案"
                    ],
                    "expected_benefit": "系统性降低项目风险，提高项目成功率",
                    "estimated_effort": "1-2周",
                    "risk_count": len(risk_factors),
                    "critical_risks": len([r for r in risk_factors if r.get("severity") == "CRITICAL"]),
                    "high_risks": len([r for r in risk_factors if r.get("severity") == "HIGH"])
                }
                suggestions.insert(0, overall_risk_suggestion)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating risk-based suggestions: {str(e)}", exc_info=True)
            return []
    
    async def _convert_risk_to_suggestion(self, risk: Dict[str, Any], context: ProjectContext) -> Optional[Dict]:
        """
        将风险因素转换为可执行的建议
        
        Args:
            risk: 风险因素
            context: 项目上下文
            
        Returns:
            Optional[Dict]: 建议字典，如果无法转换则返回None
        """
        try:
            risk_factor = risk.get("factor", "")
            severity = risk.get("severity", "MEDIUM")
            category = risk.get("category", "OTHER")
            description = risk.get("description", "")
            impact = risk.get("impact", "")
            mitigation_strategies = risk.get("mitigation_strategies", [])
            
            # 基于风险类别确定建议类型
            suggestion_type_map = {
                "TECHNICAL_RISK": "TECHNICAL_IMPROVEMENT",
                "BUSINESS_RISK": "BUSINESS_IMPROVEMENT", 
                "PROJECT_RISK": "PROJECT_MANAGEMENT",
                "SECURITY_RISK": "SECURITY_IMPROVEMENT",
                "CASCADE_RISK": "RISK_MANAGEMENT",
                "CROSS_IMPACT_RISK": "RISK_MANAGEMENT"
            }
            
            suggestion_type = suggestion_type_map.get(category, "RISK_MITIGATION")
            
            # 生成建议标题
            if "技术债务" in risk_factor:
                title = "技术债务清理和重构"
            elif "依赖" in risk_factor:
                title = "外部依赖风险缓解"
            elif "扩展性" in risk_factor:
                title = "系统扩展性改进"
            elif "合规" in risk_factor:
                title = "合规风险管控"
            elif "知识" in risk_factor:
                title = "知识管理和传承"
            elif "集成" in risk_factor:
                title = "系统集成风险控制"
            elif "性能" in risk_factor:
                title = "性能风险优化"
            elif "安全" in risk_factor:
                title = "信息安全风险防护"
            elif "级联" in risk_factor:
                title = "风险级联效应控制"
            else:
                title = f"{risk_factor}缓解措施"
            
            # 确定优先级
            priority_map = {
                "CRITICAL": "CRITICAL",
                "HIGH": "HIGH", 
                "MEDIUM": "MEDIUM",
                "LOW": "LOW"
            }
            priority = priority_map.get(severity, "MEDIUM")
            
            # 估算工作量
            effort_map = {
                "CRITICAL": "1-2周",
                "HIGH": "3-5天",
                "MEDIUM": "2-3天", 
                "LOW": "1天"
            }
            estimated_effort = effort_map.get(severity, "2-3天")
            
            # 构建建议
            suggestion = {
                "type": suggestion_type,
                "category": category,
                "title": title,
                "description": description,
                "priority": priority,
                "action_items": mitigation_strategies[:6],  # 限制行动项数量
                "expected_benefit": f"降低{risk_factor}，{impact}",
                "estimated_effort": estimated_effort,
                "risk_factor": risk_factor,
                "risk_severity": severity,
                "risk_score": risk.get("risk_score", 0.5),
                "risk_indicators": risk.get("indicators", [])
            }
            
            # 添加特定风险的额外信息
            if category == "CASCADE_RISK":
                suggestion["related_risks"] = risk.get("related_risks", [])
            elif category == "CROSS_IMPACT_RISK":
                suggestion["technical_risks"] = risk.get("technical_risks", [])
                suggestion["business_risks"] = risk.get("business_risks", [])
            
            return suggestion
            
        except Exception as e:
            self.logger.error(f"Error converting risk to suggestion: {str(e)}")
            return None
    
    async def analyze_project_status(self, context: ProjectContext) -> Dict[str, Any]:
        """
        项目状况分析算法
        
        这是AI助手模块的核心分析算法，用于全面评估项目的健康状况。
        分析维度包括：
        1. 项目健康度评估 - 基于进度、质量、资源等多维度指标
        2. 团队能力分析 - 评估团队规模、技能匹配度、工作负载
        3. 进度状态分析 - 分析项目时间线、里程碑完成情况
        4. 质量风险评估 - 基于需求质量、测试覆盖率等指标
        5. 资源配置分析 - 评估人力、时间、预算资源配置合理性
        
        Args:
            context: 项目上下文数据
            
        Returns:
            Dict[str, Any]: 项目状况分析结果
        """
        try:
            self.logger.info(f"Starting project status analysis for project {context.project_id}")
            
            analysis_result = {
                "project_id": context.project_id,
                "project_name": context.project_name,
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "overall_health_score": 0.0,
                "health_level": "UNKNOWN",
                "dimensions": {},
                "risk_factors": [],
                "recommendations": [],
                "key_metrics": {}
            }
            
            # 1. 项目健康度评估
            health_analysis = await self._assess_project_health_comprehensive(context)
            analysis_result["dimensions"]["health"] = health_analysis
            
            # 2. 团队能力分析
            team_analysis = await self._analyze_team_capacity_detailed(context)
            analysis_result["dimensions"]["team"] = team_analysis
            
            # 3. 进度状态分析
            progress_analysis = await self._analyze_project_progress(context)
            analysis_result["dimensions"]["progress"] = progress_analysis
            
            # 4. 质量风险评估
            quality_analysis = await self._assess_quality_risks(context)
            analysis_result["dimensions"]["quality"] = quality_analysis
            
            # 5. 资源配置分析
            resource_analysis = await self._analyze_resource_allocation(context)
            analysis_result["dimensions"]["resources"] = resource_analysis
            
            # 6. 计算综合健康度得分
            overall_score = await self._calculate_overall_health_score(
                health_analysis, team_analysis, progress_analysis, 
                quality_analysis, resource_analysis
            )
            analysis_result["overall_health_score"] = overall_score
            analysis_result["health_level"] = self._determine_health_level(overall_score)
            
            # 7. 识别风险因素
            risk_factors = await self._identify_project_risk_factors(
                health_analysis, team_analysis, progress_analysis, 
                quality_analysis, resource_analysis
            )
            analysis_result["risk_factors"] = risk_factors
            
            # 8. 生成关键指标
            key_metrics = await self._extract_key_metrics(analysis_result)
            analysis_result["key_metrics"] = key_metrics
            
            # 9. 生成改进建议
            recommendations = await self._generate_project_improvement_recommendations(analysis_result)
            analysis_result["recommendations"] = recommendations
            
            self.logger.info(f"Project status analysis completed. Overall health score: {overall_score:.2f}")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error in project status analysis: {str(e)}", exc_info=True)
            return {
                "project_id": context.project_id,
                "error": str(e),
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "overall_health_score": 0.0,
                "health_level": "ERROR"
            }
    
    async def _assess_project_health_comprehensive(self, context: ProjectContext) -> Dict[str, Any]:
        """
        综合项目健康度评估
        
        评估维度：
        - 进度健康度 (30%权重)
        - 质量健康度 (25%权重)  
        - 团队健康度 (20%权重)
        - 资源健康度 (15%权重)
        - 风险健康度 (10%权重)
        """
        try:
            health_analysis = {
                "progress_health": 0.0,
                "quality_health": 0.0,
                "team_health": 0.0,
                "resource_health": 0.0,
                "risk_health": 0.0,
                "overall_health": 0.0,
                "health_factors": []
            }
            
            # 进度健康度评估
            if context.timeline:
                progress_score = await self._evaluate_progress_health(context.timeline)
                health_analysis["progress_health"] = progress_score
                
                if progress_score < 0.6:
                    health_analysis["health_factors"].append({
                        "factor": "进度滞后",
                        "severity": "HIGH" if progress_score < 0.4 else "MEDIUM",
                        "description": f"项目进度健康度为{progress_score:.2f}，存在延期风险"
                    })
            
            # 质量健康度评估
            if context.quality_metrics:
                quality_score = await self._evaluate_quality_health(context.quality_metrics)
                health_analysis["quality_health"] = quality_score
                
                if quality_score < 0.7:
                    health_analysis["health_factors"].append({
                        "factor": "质量风险",
                        "severity": "HIGH" if quality_score < 0.5 else "MEDIUM",
                        "description": f"项目质量健康度为{quality_score:.2f}，需要关注质量控制"
                    })
            
            # 团队健康度评估
            if context.team_size:
                team_score = await self._evaluate_team_health(context)
                health_analysis["team_health"] = team_score
                
                if team_score < 0.6:
                    health_analysis["health_factors"].append({
                        "factor": "团队能力",
                        "severity": "MEDIUM",
                        "description": f"团队健康度为{team_score:.2f}，建议优化团队配置"
                    })
            
            # 资源健康度评估
            resource_score = await self._evaluate_resource_health(context)
            health_analysis["resource_health"] = resource_score
            
            if resource_score < 0.6:
                health_analysis["health_factors"].append({
                    "factor": "资源配置",
                    "severity": "MEDIUM",
                    "description": f"资源健康度为{resource_score:.2f}，资源配置需要优化"
                })
            
            # 风险健康度评估
            risk_score = await self._evaluate_risk_health(context)
            health_analysis["risk_health"] = risk_score
            
            if risk_score < 0.7:
                health_analysis["health_factors"].append({
                    "factor": "项目风险",
                    "severity": "HIGH" if risk_score < 0.5 else "MEDIUM",
                    "description": f"风险健康度为{risk_score:.2f}，存在较高项目风险"
                })
            
            # 计算综合健康度 (加权平均)
            weights = {
                "progress": 0.30,
                "quality": 0.25,
                "team": 0.20,
                "resource": 0.15,
                "risk": 0.10
            }
            
            overall_health = (
                health_analysis["progress_health"] * weights["progress"] +
                health_analysis["quality_health"] * weights["quality"] +
                health_analysis["team_health"] * weights["team"] +
                health_analysis["resource_health"] * weights["resource"] +
                health_analysis["risk_health"] * weights["risk"]
            )
            
            health_analysis["overall_health"] = overall_health
            
            return health_analysis
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive health assessment: {str(e)}")
            return {"overall_health": 0.0, "health_factors": []}
    
    async def _analyze_team_capacity_detailed(self, context: ProjectContext) -> Dict[str, Any]:
        """
        详细团队能力分析
        
        分析维度：
        - 团队规模合理性
        - 技能匹配度
        - 工作负载分布
        - 协作效率
        - 经验水平
        """
        try:
            team_analysis = {
                "team_size": context.team_size or 0,
                "size_assessment": "UNKNOWN",
                "capacity_score": 0.0,
                "workload_distribution": "UNKNOWN",
                "collaboration_efficiency": 0.0,
                "skill_gaps": [],
                "capacity_issues": []
            }
            
            if context.team_size:
                # 团队规模评估
                if context.team_size < 3:
                    team_analysis["size_assessment"] = "SMALL"
                    team_analysis["capacity_issues"].append({
                        "issue": "团队规模偏小",
                        "impact": "可能影响项目交付能力和风险承受能力",
                        "recommendation": "考虑增加团队成员或调整项目范围"
                    })
                elif context.team_size > 15:
                    team_analysis["size_assessment"] = "LARGE"
                    team_analysis["capacity_issues"].append({
                        "issue": "团队规模较大",
                        "impact": "可能存在沟通成本高、协调困难等问题",
                        "recommendation": "建议拆分为多个小团队或优化协作流程"
                    })
                else:
                    team_analysis["size_assessment"] = "OPTIMAL"
                
                # 基于团队规模计算基础能力得分
                if context.team_size <= 2:
                    base_score = 0.4
                elif context.team_size <= 5:
                    base_score = 0.8
                elif context.team_size <= 10:
                    base_score = 0.9
                elif context.team_size <= 15:
                    base_score = 0.7
                else:
                    base_score = 0.5
                
                # 根据项目类型调整得分
                if context.project_type == "web_application" and 3 <= context.team_size <= 8:
                    base_score += 0.1
                elif context.project_type == "mobile_app" and 2 <= context.team_size <= 6:
                    base_score += 0.1
                elif context.project_type == "api_service" and 2 <= context.team_size <= 5:
                    base_score += 0.1
                
                team_analysis["capacity_score"] = min(1.0, base_score)
                
                # 协作效率评估 (基于团队规模的经验公式)
                if context.team_size <= 5:
                    collaboration_score = 0.9
                elif context.team_size <= 10:
                    collaboration_score = 0.8
                elif context.team_size <= 15:
                    collaboration_score = 0.6
                else:
                    collaboration_score = 0.4
                
                team_analysis["collaboration_efficiency"] = collaboration_score
            
            # 技能缺口分析 (基于项目类型)
            required_skills = self._get_required_skills_by_project_type(context.project_type)
            team_analysis["required_skills"] = required_skills
            
            # 如果团队规模小于所需技能数量，标记技能缺口
            if context.team_size and context.team_size < len(required_skills):
                team_analysis["skill_gaps"] = required_skills[context.team_size:]
                team_analysis["capacity_issues"].append({
                    "issue": "技能覆盖不足",
                    "impact": f"团队规模({context.team_size})小于所需技能数量({len(required_skills)})",
                    "recommendation": "增加团队成员或提供技能培训"
                })
            
            return team_analysis
            
        except Exception as e:
            self.logger.error(f"Error in team capacity analysis: {str(e)}")
            return {"capacity_score": 0.0, "capacity_issues": []}
    
    async def _analyze_project_progress(self, context: ProjectContext) -> Dict[str, Any]:
        """
        项目进度状态分析
        
        分析维度：
        - 时间线健康度
        - 里程碑完成情况
        - 进度偏差分析
        - 交付风险评估
        """
        try:
            progress_analysis = {
                "timeline_health": 0.0,
                "milestone_completion": 0.0,
                "schedule_variance": 0.0,
                "delivery_risk": "UNKNOWN",
                "progress_issues": [],
                "timeline_recommendations": []
            }
            
            if context.timeline:
                # 时间线健康度分析
                total_days = context.timeline.get("total_days", 0)
                elapsed_days = context.timeline.get("elapsed_days", 0)
                remaining_days = context.timeline.get("remaining_days", 0)
                
                if total_days > 0:
                    progress_ratio = elapsed_days / total_days
                    
                    # 基于进度比例评估健康度
                    if progress_ratio < 0.3:
                        timeline_health = 0.9  # 项目初期，健康度较高
                    elif progress_ratio < 0.6:
                        timeline_health = 0.8  # 项目中期
                    elif progress_ratio < 0.8:
                        timeline_health = 0.7  # 项目后期
                    else:
                        timeline_health = 0.6  # 项目收尾期，风险较高
                    
                    # 剩余时间风险评估
                    if remaining_days < 7:
                        timeline_health *= 0.5
                        progress_analysis["delivery_risk"] = "CRITICAL"
                        progress_analysis["progress_issues"].append({
                            "issue": "交付时间极度紧迫",
                            "severity": "CRITICAL",
                            "description": f"项目剩余时间仅{remaining_days}天"
                        })
                    elif remaining_days < 30:
                        timeline_health *= 0.7
                        progress_analysis["delivery_risk"] = "HIGH"
                        progress_analysis["progress_issues"].append({
                            "issue": "交付时间紧迫",
                            "severity": "HIGH",
                            "description": f"项目剩余时间{remaining_days}天，需要加强进度管控"
                        })
                    elif remaining_days < 60:
                        progress_analysis["delivery_risk"] = "MEDIUM"
                    else:
                        progress_analysis["delivery_risk"] = "LOW"
                    
                    progress_analysis["timeline_health"] = timeline_health
                    progress_analysis["schedule_variance"] = progress_ratio
                
                # 里程碑分析
                milestones = context.timeline.get("milestones", [])
                if milestones:
                    completed_milestones = len([m for m in milestones if m.get("completed", False)])
                    milestone_completion = completed_milestones / len(milestones)
                    progress_analysis["milestone_completion"] = milestone_completion
                    
                    if milestone_completion < 0.5 and progress_ratio > 0.6:
                        progress_analysis["progress_issues"].append({
                            "issue": "里程碑完成滞后",
                            "severity": "HIGH",
                            "description": f"项目进度{progress_ratio:.1%}，但里程碑完成率仅{milestone_completion:.1%}"
                        })
            
            # 生成时间线建议
            if progress_analysis["delivery_risk"] in ["HIGH", "CRITICAL"]:
                progress_analysis["timeline_recommendations"].extend([
                    "重新评估剩余工作量和优先级",
                    "考虑增加资源投入或调整交付范围",
                    "建立每日进度跟踪机制",
                    "识别并解决关键路径上的阻塞问题"
                ])
            
            return progress_analysis
            
        except Exception as e:
            self.logger.error(f"Error in progress analysis: {str(e)}")
            return {"timeline_health": 0.0, "delivery_risk": "UNKNOWN"}
    
    async def _assess_quality_risks(self, context: ProjectContext) -> Dict[str, Any]:
        """
        质量风险评估
        
        评估维度：
        - 需求质量风险
        - 测试覆盖风险
        - 代码质量风险
        - 缺陷趋势风险
        """
        try:
            quality_analysis = {
                "requirements_quality_risk": 0.0,
                "test_coverage_risk": 0.0,
                "code_quality_risk": 0.0,
                "defect_trend_risk": 0.0,
                "overall_quality_risk": 0.0,
                "quality_issues": [],
                "quality_recommendations": []
            }
            
            # 需求质量风险评估
            if context.requirements:
                req_data = RequirementsData(
                    requirements=context.requirements,
                    total_count=len(context.requirements),
                    categories=[req.get("category", "未分类") for req in context.requirements],
                    priorities=[req.get("priority", "MEDIUM") for req in context.requirements]
                )
                
                req_quality = await self._analyze_requirements_quality(req_data)
                req_risk = 1.0 - req_quality.overall_score  # 质量越低，风险越高
                quality_analysis["requirements_quality_risk"] = req_risk
                
                if req_risk > 0.4:
                    quality_analysis["quality_issues"].append({
                        "issue": "需求质量风险",
                        "severity": "HIGH" if req_risk > 0.6 else "MEDIUM",
                        "description": f"需求质量得分{req_quality.overall_score:.2f}，存在质量风险"
                    })
            
            # 测试覆盖风险评估
            if context.test_data:
                test_coverage = context.test_data.get("coverage_rate", 0.0)
                test_risk = max(0.0, 1.0 - test_coverage)
                quality_analysis["test_coverage_risk"] = test_risk
                
                if test_coverage < 0.7:
                    quality_analysis["quality_issues"].append({
                        "issue": "测试覆盖不足",
                        "severity": "HIGH" if test_coverage < 0.5 else "MEDIUM",
                        "description": f"测试覆盖率{test_coverage:.1%}，低于建议标准"
                    })
            
            # 质量指标风险评估
            if context.quality_metrics:
                defect_rate = context.quality_metrics.get("defect_rate", 0.0)
                code_quality_score = context.quality_metrics.get("code_quality_score", 0.8)
                
                # 缺陷率风险
                defect_risk = min(1.0, defect_rate * 10)  # 假设10%缺陷率为最高风险
                quality_analysis["defect_trend_risk"] = defect_risk
                
                # 代码质量风险
                code_risk = max(0.0, 1.0 - code_quality_score)
                quality_analysis["code_quality_risk"] = code_risk
                
                if defect_rate > 0.05:  # 5%缺陷率
                    quality_analysis["quality_issues"].append({
                        "issue": "缺陷率偏高",
                        "severity": "HIGH" if defect_rate > 0.1 else "MEDIUM",
                        "description": f"项目缺陷率{defect_rate:.1%}，需要加强质量控制"
                    })
                
                if code_quality_score < 0.7:
                    quality_analysis["quality_issues"].append({
                        "issue": "代码质量风险",
                        "severity": "MEDIUM",
                        "description": f"代码质量得分{code_quality_score:.2f}，建议进行代码重构"
                    })
            
            # 计算综合质量风险
            risk_scores = [
                quality_analysis["requirements_quality_risk"],
                quality_analysis["test_coverage_risk"],
                quality_analysis["code_quality_risk"],
                quality_analysis["defect_trend_risk"]
            ]
            
            # 过滤掉0值（未评估的维度）
            valid_risks = [risk for risk in risk_scores if risk > 0]
            if valid_risks:
                quality_analysis["overall_quality_risk"] = sum(valid_risks) / len(valid_risks)
            
            # 生成质量建议
            if quality_analysis["overall_quality_risk"] > 0.5:
                quality_analysis["quality_recommendations"].extend([
                    "建立代码审查机制",
                    "增加自动化测试覆盖率",
                    "完善需求评审流程",
                    "建立质量门禁标准"
                ])
            
            return quality_analysis
            
        except Exception as e:
            self.logger.error(f"Error in quality risk assessment: {str(e)}")
            return {"overall_quality_risk": 0.0, "quality_issues": []}
    
    async def _analyze_resource_allocation(self, context: ProjectContext) -> Dict[str, Any]:
        """
        资源配置分析
        
        分析维度：
        - 人力资源配置
        - 时间资源分配
        - 技能资源匹配
        - 资源利用效率
        """
        try:
            resource_analysis = {
                "human_resource_score": 0.0,
                "time_resource_score": 0.0,
                "skill_resource_score": 0.0,
                "resource_efficiency": 0.0,
                "resource_issues": [],
                "resource_recommendations": []
            }
            
            # 人力资源评估
            if context.team_size and context.project_type:
                optimal_team_size = self._get_optimal_team_size(context.project_type)
                size_ratio = context.team_size / optimal_team_size
                
                if 0.8 <= size_ratio <= 1.2:
                    human_score = 0.9
                elif 0.6 <= size_ratio <= 1.5:
                    human_score = 0.7
                else:
                    human_score = 0.5
                    resource_analysis["resource_issues"].append({
                        "issue": "人力资源配置不当",
                        "severity": "MEDIUM",
                        "description": f"当前团队{context.team_size}人，建议{optimal_team_size}人"
                    })
                
                resource_analysis["human_resource_score"] = human_score
            
            # 时间资源评估
            if context.timeline:
                total_days = context.timeline.get("total_days", 0)
                project_complexity = self._estimate_project_complexity(context)
                
                if total_days > 0:
                    # 基于项目复杂度评估时间充裕度
                    if project_complexity == "LOW" and total_days >= 30:
                        time_score = 0.9
                    elif project_complexity == "MEDIUM" and total_days >= 90:
                        time_score = 0.8
                    elif project_complexity == "HIGH" and total_days >= 180:
                        time_score = 0.8
                    else:
                        time_score = 0.6
                        resource_analysis["resource_issues"].append({
                            "issue": "时间资源紧张",
                            "severity": "HIGH",
                            "description": f"项目复杂度{project_complexity}，时间{total_days}天可能不足"
                        })
                    
                    resource_analysis["time_resource_score"] = time_score
            
            # 技能资源匹配度评估
            required_skills = self._get_required_skills_by_project_type(context.project_type)
            if context.team_size:
                skill_coverage = min(1.0, context.team_size / len(required_skills))
                resource_analysis["skill_resource_score"] = skill_coverage
                
                if skill_coverage < 0.8:
                    resource_analysis["resource_issues"].append({
                        "issue": "技能资源不足",
                        "severity": "MEDIUM",
                        "description": f"技能覆盖率{skill_coverage:.1%}，可能存在技能缺口"
                    })
            
            # 计算资源效率
            scores = [
                resource_analysis["human_resource_score"],
                resource_analysis["time_resource_score"],
                resource_analysis["skill_resource_score"]
            ]
            valid_scores = [score for score in scores if score > 0]
            if valid_scores:
                resource_analysis["resource_efficiency"] = sum(valid_scores) / len(valid_scores)
            
            # 生成资源建议
            if resource_analysis["resource_efficiency"] < 0.7:
                resource_analysis["resource_recommendations"].extend([
                    "重新评估资源需求和配置",
                    "考虑调整项目范围或时间线",
                    "优化团队技能结构",
                    "建立资源监控和预警机制"
                ])
            
            return resource_analysis
            
        except Exception as e:
            self.logger.error(f"Error in resource allocation analysis: {str(e)}")
            return {"resource_efficiency": 0.0, "resource_issues": []}

    async def generate_project_management_suggestions(self, context: ProjectContext) -> List[Dict]:
        """
        生成项目管理建议
        
        基于项目状况分析结果，生成针对性的项目管理改进建议
        
        Args:
            context: 项目上下文
            
        Returns:
            List[Dict]: 项目管理建议列表
        """
        try:
            suggestions = []
            
            # 首先进行项目状况分析
            project_analysis = await self.analyze_project_status(context)
            
            # 基于分析结果生成建议
            if project_analysis.get("overall_health_score", 0) < 0.6:
                suggestions.append({
                    "type": SuggestionType.PROJECT_MANAGEMENT.value,
                    "category": SuggestionCategory.PERFORMANCE.value,
                    "title": "项目健康度告警",
                    "description": f"项目整体健康度{project_analysis['overall_health_score']:.2f}，需要立即关注",
                    "priority": SuggestionPriority.CRITICAL.value,
                    "action_items": [
                        "召开项目健康度评估会议",
                        "识别并解决关键风险因素",
                        "制定项目改进行动计划",
                        "建立项目健康度监控机制"
                    ],
                    "expected_benefit": "提升项目成功率，降低项目风险",
                    "estimated_effort": "1-2周",
                    "analysis_data": project_analysis
                })
            
            # 基于具体维度生成建议
            dimensions = project_analysis.get("dimensions", {})
            
            # 团队相关建议
            team_analysis = dimensions.get("team", {})
            if team_analysis.get("capacity_score", 0) < 0.6:
                suggestions.append({
                    "type": SuggestionType.PROJECT_MANAGEMENT.value,
                    "category": SuggestionCategory.MAINTAINABILITY.value,
                    "title": "优化团队配置",
                    "description": f"团队能力得分{team_analysis['capacity_score']:.2f}，建议优化团队结构",
                    "priority": SuggestionPriority.HIGH.value,
                    "action_items": [
                        "评估团队技能缺口",
                        "调整团队规模或结构",
                        "提供必要的技能培训",
                        "优化团队协作流程"
                    ],
                    "expected_benefit": "提高团队效率和项目交付能力",
                    "estimated_effort": "2-3周"
                })
            
            # 进度相关建议
            progress_analysis = dimensions.get("progress", {})
            if progress_analysis.get("delivery_risk") in ["HIGH", "CRITICAL"]:
                suggestions.append({
                    "type": SuggestionType.PROJECT_MANAGEMENT.value,
                    "category": SuggestionCategory.PERFORMANCE.value,
                    "title": "紧急进度管控",
                    "description": f"交付风险等级{progress_analysis['delivery_risk']}，需要紧急干预",
                    "priority": SuggestionPriority.CRITICAL.value,
                    "action_items": [
                        "重新评估剩余工作量",
                        "识别关键路径和瓶颈",
                        "考虑范围调整或资源增加",
                        "建立每日进度跟踪"
                    ],
                    "expected_benefit": "确保项目按时交付或合理调整预期",
                    "estimated_effort": "立即执行"
                })
            
            # 质量相关建议
            quality_analysis = dimensions.get("quality", {})
            if quality_analysis.get("overall_quality_risk", 0) > 0.5:
                suggestions.append({
                    "type": SuggestionType.QUALITY_IMPROVEMENT.value,
                    "category": SuggestionCategory.SECURITY.value,
                    "title": "加强质量管控",
                    "description": f"质量风险指数{quality_analysis['overall_quality_risk']:.2f}，需要加强质量管理",
                    "priority": SuggestionPriority.HIGH.value,
                    "action_items": [
                        "建立质量门禁标准",
                        "增加代码审查频次",
                        "提升测试覆盖率",
                        "完善缺陷管理流程"
                    ],
                    "expected_benefit": "降低项目质量风险，提升产品质量",
                    "estimated_effort": "1-2周"
                })
            
            # 资源相关建议
            resource_analysis = dimensions.get("resources", {})
            if resource_analysis.get("resource_efficiency", 0) < 0.7:
                suggestions.append({
                    "type": SuggestionType.PROJECT_MANAGEMENT.value,
                    "category": SuggestionCategory.MAINTAINABILITY.value,
                    "title": "优化资源配置",
                    "description": f"资源效率{resource_analysis['resource_efficiency']:.2f}，建议优化资源分配",
                    "priority": SuggestionPriority.MEDIUM.value,
                    "action_items": [
                        "重新评估资源需求",
                        "优化人力资源配置",
                        "调整时间计划安排",
                        "提升资源利用效率"
                    ],
                    "expected_benefit": "提高资源利用效率，降低项目成本",
                    "estimated_effort": "1周"
                })
            
            # 传统的团队规模和时间线检查（保持向后兼容）
            if context.team_size and context.team_size > 10:
                suggestions.append({
                    "type": SuggestionType.PROJECT_MANAGEMENT.value,
                    "category": SuggestionCategory.MAINTAINABILITY.value,
                    "title": "优化大团队协作",
                    "description": f"团队规模较大({context.team_size}人)，建议优化协作流程",
                    "priority": SuggestionPriority.MEDIUM.value,
                    "action_items": [
                        "建立清晰的角色分工",
                        "制定代码规范和开发流程",
                        "使用项目管理工具跟踪进度",
                        "定期举行团队同步会议"
                    ],
                    "expected_benefit": "提高团队协作效率，减少沟通成本",
                    "estimated_effort": "1周"
                })
            
            if context.timeline:
                remaining_time = context.timeline.get("remaining_days", 0)
                if remaining_time < 30 and remaining_time > 0:
                    suggestions.append({
                        "type": SuggestionType.PROJECT_MANAGEMENT.value,
                        "category": SuggestionCategory.PERFORMANCE.value,
                        "title": "项目时间紧迫，需要风险控制",
                        "description": f"项目剩余时间仅{remaining_time}天，建议加强风险管理",
                        "priority": SuggestionPriority.HIGH.value,
                        "action_items": [
                            "重新评估剩余工作量",
                            "识别关键路径和风险点",
                            "考虑功能优先级调整",
                            "增加资源投入或延期交付"
                        ],
                        "expected_benefit": "确保项目按时交付或合理调整预期",
                        "estimated_effort": "2-3天"
                    })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating project management suggestions: {str(e)}")
            return []
    
    # Helper methods for project status analysis algorithm
    
    async def _evaluate_progress_health(self, timeline: Dict[str, Any]) -> float:
        """评估进度健康度"""
        try:
            total_days = timeline.get("total_days", 0)
            elapsed_days = timeline.get("elapsed_days", 0)
            remaining_days = timeline.get("remaining_days", 0)
            
            if total_days <= 0:
                return 0.5  # 默认中等健康度
            
            progress_ratio = elapsed_days / total_days
            
            # 基于进度比例和剩余时间评估健康度
            if remaining_days < 7:
                return 0.2  # 时间极度紧迫
            elif remaining_days < 30:
                return 0.4  # 时间紧迫
            elif progress_ratio < 0.5:
                return 0.9  # 项目前期，健康度高
            elif progress_ratio < 0.8:
                return 0.7  # 项目中后期
            else:
                return 0.6  # 项目收尾期
                
        except Exception as e:
            self.logger.error(f"Error evaluating progress health: {str(e)}")
            return 0.5
    
    async def _evaluate_quality_health(self, quality_metrics: Dict[str, Any]) -> float:
        """评估质量健康度"""
        try:
            # 获取质量指标
            defect_rate = quality_metrics.get("defect_rate", 0.0)
            code_quality_score = quality_metrics.get("code_quality_score", 0.8)
            test_coverage = quality_metrics.get("test_coverage", 0.0)
            
            # 计算质量健康度
            quality_score = 0.0
            
            # 缺陷率评估 (权重30%)
            if defect_rate <= 0.02:  # 2%以下
                defect_score = 1.0
            elif defect_rate <= 0.05:  # 5%以下
                defect_score = 0.8
            elif defect_rate <= 0.1:  # 10%以下
                defect_score = 0.6
            else:
                defect_score = 0.3
            
            quality_score += defect_score * 0.3
            
            # 代码质量评估 (权重40%)
            quality_score += code_quality_score * 0.4
            
            # 测试覆盖率评估 (权重30%)
            if test_coverage >= 0.8:
                coverage_score = 1.0
            elif test_coverage >= 0.6:
                coverage_score = 0.8
            elif test_coverage >= 0.4:
                coverage_score = 0.6
            else:
                coverage_score = 0.3
            
            quality_score += coverage_score * 0.3
            
            return min(1.0, quality_score)
            
        except Exception as e:
            self.logger.error(f"Error evaluating quality health: {str(e)}")
            return 0.5
    
    async def _evaluate_team_health(self, context: ProjectContext) -> float:
        """评估团队健康度"""
        try:
            if not context.team_size:
                return 0.5
            
            # 基于团队规模和项目类型评估
            optimal_size = self._get_optimal_team_size(context.project_type)
            size_ratio = context.team_size / optimal_size
            
            if 0.8 <= size_ratio <= 1.2:
                return 0.9  # 团队规模最优
            elif 0.6 <= size_ratio <= 1.5:
                return 0.7  # 团队规模可接受
            else:
                return 0.4  # 团队规模不当
                
        except Exception as e:
            self.logger.error(f"Error evaluating team health: {str(e)}")
            return 0.5
    
    async def _evaluate_resource_health(self, context: ProjectContext) -> float:
        """评估资源健康度"""
        try:
            resource_score = 0.0
            score_count = 0
            
            # 人力资源评估
            if context.team_size:
                optimal_size = self._get_optimal_team_size(context.project_type)
                size_ratio = context.team_size / optimal_size
                
                if 0.8 <= size_ratio <= 1.2:
                    human_score = 0.9
                elif 0.6 <= size_ratio <= 1.5:
                    human_score = 0.7
                else:
                    human_score = 0.4
                
                resource_score += human_score
                score_count += 1
            
            # 时间资源评估
            if context.timeline:
                total_days = context.timeline.get("total_days", 0)
                complexity = self._estimate_project_complexity(context)
                
                if complexity == "LOW" and total_days >= 30:
                    time_score = 0.9
                elif complexity == "MEDIUM" and total_days >= 90:
                    time_score = 0.8
                elif complexity == "HIGH" and total_days >= 180:
                    time_score = 0.8
                else:
                    time_score = 0.5
                
                resource_score += time_score
                score_count += 1
            
            return resource_score / score_count if score_count > 0 else 0.5
            
        except Exception as e:
            self.logger.error(f"Error evaluating resource health: {str(e)}")
            return 0.5
    
    async def _evaluate_risk_health(self, context: ProjectContext) -> float:
        """
        评估风险健康度
        
        综合评估项目的风险健康状况，包括：
        1. 时间风险 - 交付时间压力
        2. 团队风险 - 团队规模和能力
        3. 质量风险 - 缺陷率和质量指标
        4. 需求风险 - 需求完整性和清晰度
        5. 技术风险 - 技术复杂度和依赖
        6. 资源风险 - 资源充足性和分配
        """
        try:
            risk_scores = []
            
            # 1. 时间风险评估
            time_risk_score = await self._evaluate_time_risk(context)
            risk_scores.append(("时间风险", time_risk_score, 0.25))
            
            # 2. 团队风险评估
            team_risk_score = await self._evaluate_team_risk(context)
            risk_scores.append(("团队风险", team_risk_score, 0.20))
            
            # 3. 质量风险评估
            quality_risk_score = await self._evaluate_quality_risk(context)
            risk_scores.append(("质量风险", quality_risk_score, 0.20))
            
            # 4. 需求风险评估
            requirements_risk_score = await self._evaluate_requirements_risk(context)
            risk_scores.append(("需求风险", requirements_risk_score, 0.15))
            
            # 5. 技术风险评估
            technical_risk_score = await self._evaluate_technical_risk(context)
            risk_scores.append(("技术风险", technical_risk_score, 0.10))
            
            # 6. 资源风险评估
            resource_risk_score = await self._evaluate_resource_risk(context)
            risk_scores.append(("资源风险", resource_risk_score, 0.10))
            
            # 计算加权平均风险健康度
            total_weighted_score = 0.0
            total_weight = 0.0
            
            for risk_name, score, weight in risk_scores:
                if score is not None:
                    total_weighted_score += score * weight
                    total_weight += weight
            
            if total_weight == 0:
                return 0.7  # 默认中等风险健康度
            
            # 风险健康度 = 1 - 风险分数（分数越高风险越大，健康度越低）
            risk_health = total_weighted_score / total_weight
            
            # 确保结果在合理范围内
            return max(0.0, min(1.0, risk_health))
            
        except Exception as e:
            self.logger.error(f"Error evaluating risk health: {str(e)}")
            return 0.5
    
    async def _evaluate_time_risk(self, context: ProjectContext) -> Optional[float]:
        """评估时间风险"""
        try:
            if not context.timeline:
                return None
            
            remaining_days = context.timeline.get("remaining_days", 0)
            total_days = context.timeline.get("total_days", 0)
            progress = context.timeline.get("progress", 0.0)
            
            # 计算时间压力指数
            if total_days > 0:
                time_pressure = 1.0 - (remaining_days / total_days)
            else:
                time_pressure = 0.5
            
            # 考虑进度与时间的匹配度
            if progress > 0:
                expected_progress = 1.0 - (remaining_days / total_days) if total_days > 0 else 0.5
                progress_deviation = abs(progress - expected_progress)
                time_pressure += progress_deviation * 0.5
            
            # 时间风险评分（越高风险越大）
            if remaining_days < 7:
                time_risk = 0.9
            elif remaining_days < 30:
                time_risk = 0.7
            elif remaining_days < 60:
                time_risk = 0.4
            else:
                time_risk = 0.2
            
            # 结合时间压力调整
            time_risk = min(1.0, time_risk + time_pressure * 0.3)
            
            # 转换为健康度（风险越高，健康度越低）
            return 1.0 - time_risk
            
        except Exception as e:
            self.logger.error(f"Error evaluating time risk: {str(e)}")
            return None
    
    async def _evaluate_team_risk(self, context: ProjectContext) -> Optional[float]:
        """评估团队风险"""
        try:
            if not context.team_size:
                return None
            
            team_size = context.team_size
            
            # 团队规模风险评估
            if team_size < 2:
                size_risk = 0.8  # 团队太小，风险高
            elif team_size > 15:
                size_risk = 0.6  # 团队太大，协调风险
            elif 3 <= team_size <= 8:
                size_risk = 0.2  # 理想团队规模
            else:
                size_risk = 0.4  # 中等风险
            
            # 如果有更多团队信息，可以进一步评估
            # 这里可以扩展评估团队技能匹配度、经验水平等
            
            return 1.0 - size_risk
            
        except Exception as e:
            self.logger.error(f"Error evaluating team risk: {str(e)}")
            return None
    
    async def _evaluate_quality_risk(self, context: ProjectContext) -> Optional[float]:
        """评估质量风险"""
        try:
            if not context.quality_metrics:
                return None
            
            quality_metrics = context.quality_metrics
            quality_risk = 0.0
            
            # 缺陷率风险
            defect_rate = quality_metrics.get("defect_rate", 0.0)
            if defect_rate > 0.1:
                quality_risk += 0.4
            elif defect_rate > 0.05:
                quality_risk += 0.2
            
            # 测试覆盖率风险
            test_coverage = quality_metrics.get("test_coverage", 0.0)
            if test_coverage < 0.5:
                quality_risk += 0.3
            elif test_coverage < 0.7:
                quality_risk += 0.1
            
            # 代码质量风险
            code_quality = quality_metrics.get("code_quality_score", 0.8)
            if code_quality < 0.6:
                quality_risk += 0.3
            elif code_quality < 0.8:
                quality_risk += 0.1
            
            return 1.0 - min(1.0, quality_risk)
            
        except Exception as e:
            self.logger.error(f"Error evaluating quality risk: {str(e)}")
            return None
    
    async def _evaluate_requirements_risk(self, context: ProjectContext) -> Optional[float]:
        """评估需求风险"""
        try:
            if not context.requirements:
                return None
            
            requirements = context.requirements
            total_reqs = len(requirements)
            
            if total_reqs == 0:
                return 0.5
            
            # 需求完整性风险
            incomplete_reqs = len([req for req in requirements 
                                 if not req.get("description") or len(req.get("description", "")) < 10])
            completeness_risk = incomplete_reqs / total_reqs
            
            # 需求清晰度风险
            unclear_reqs = len([req for req in requirements 
                              if not req.get("acceptance_criteria") or len(req.get("acceptance_criteria", [])) == 0])
            clarity_risk = unclear_reqs / total_reqs
            
            # 需求优先级风险
            no_priority_reqs = len([req for req in requirements 
                                  if not req.get("priority")])
            priority_risk = no_priority_reqs / total_reqs
            
            # 综合需求风险
            overall_req_risk = (completeness_risk + clarity_risk + priority_risk) / 3
            
            return 1.0 - overall_req_risk
            
        except Exception as e:
            self.logger.error(f"Error evaluating requirements risk: {str(e)}")
            return None
    
    async def _evaluate_technical_risk(self, context: ProjectContext) -> Optional[float]:
        """评估技术风险"""
        try:
            # 基于项目类型评估技术复杂度
            project_type = context.project_type or "unknown"
            
            # 技术复杂度映射
            complexity_map = {
                "web_application": 0.3,
                "mobile_app": 0.4,
                "api_service": 0.2,
                "data_platform": 0.6,
                "ai_system": 0.7,
                "unknown": 0.5
            }
            
            base_technical_risk = complexity_map.get(project_type, 0.5)
            
            # 如果有更多技术信息，可以进一步调整
            # 例如：依赖数量、技术栈复杂度、集成点数量等
            
            return 1.0 - base_technical_risk
            
        except Exception as e:
            self.logger.error(f"Error evaluating technical risk: {str(e)}")
            return None
    
    async def _evaluate_resource_risk(self, context: ProjectContext) -> Optional[float]:
        """评估资源风险"""
        try:
            # 基于团队规模和项目复杂度评估资源充足性
            team_size = context.team_size or 0
            
            if team_size == 0:
                return None
            
            # 简单的资源风险评估
            # 实际应用中可以考虑预算、设备、时间等资源
            if team_size < 2:
                resource_risk = 0.7  # 人力资源不足
            elif team_size > 20:
                resource_risk = 0.4  # 资源管理复杂
            else:
                resource_risk = 0.2  # 资源相对充足
            
            return 1.0 - resource_risk
            
        except Exception as e:
            self.logger.error(f"Error evaluating resource risk: {str(e)}")
            return None
    
    async def _calculate_overall_health_score(self, health_analysis, team_analysis, 
                                            progress_analysis, quality_analysis, 
                                            resource_analysis) -> float:
        """计算综合健康度得分"""
        try:
            # 权重配置
            weights = {
                "health": 0.25,
                "team": 0.20,
                "progress": 0.25,
                "quality": 0.20,
                "resource": 0.10
            }
            
            # 获取各维度得分
            health_score = health_analysis.get("overall_health", 0.0)
            team_score = team_analysis.get("capacity_score", 0.0)
            progress_score = progress_analysis.get("timeline_health", 0.0)
            quality_score = 1.0 - quality_analysis.get("overall_quality_risk", 0.5)  # 风险转换为得分
            resource_score = resource_analysis.get("resource_efficiency", 0.0)
            
            # 加权计算
            overall_score = (
                health_score * weights["health"] +
                team_score * weights["team"] +
                progress_score * weights["progress"] +
                quality_score * weights["quality"] +
                resource_score * weights["resource"]
            )
            
            return min(1.0, max(0.0, overall_score))
            
        except Exception as e:
            self.logger.error(f"Error calculating overall health score: {str(e)}")
            return 0.0
    
    def _determine_health_level(self, score: float) -> str:
        """确定健康度等级"""
        if score >= 0.8:
            return "EXCELLENT"
        elif score >= 0.6:
            return "GOOD"
        elif score >= 0.4:
            return "FAIR"
        elif score >= 0.2:
            return "POOR"
        else:
            return "CRITICAL"
    
    async def _identify_project_risk_factors(self, health_analysis, team_analysis, 
                                           progress_analysis, quality_analysis, 
                                           resource_analysis) -> List[Dict[str, Any]]:
        """
        识别项目风险因素
        
        综合分析项目各个维度的风险，包括：
        1. 技术风险 - API依赖、性能扩展、数据安全
        2. 业务风险 - 成本控制、合规风险、用户接受度
        3. 项目风险 - 进度延期、团队协作、资源不足
        4. 质量风险 - 需求质量、测试覆盖、缺陷趋势
        5. 运营风险 - 系统稳定性、监控告警、故障恢复
        """
        try:
            risk_factors = []
            
            # 1. 基础风险因素收集
            health_factors = health_analysis.get("health_factors", [])
            risk_factors.extend(health_factors)
            
            # 团队风险
            team_issues = team_analysis.get("capacity_issues", [])
            for issue in team_issues:
                risk_factors.append({
                    "factor": "团队风险",
                    "severity": "MEDIUM",
                    "description": issue.get("issue", ""),
                    "impact": issue.get("impact", ""),
                    "recommendation": issue.get("recommendation", ""),
                    "category": "PROJECT_RISK"
                })
            
            # 进度风险
            progress_issues = progress_analysis.get("progress_issues", [])
            risk_factors.extend(progress_issues)
            
            # 质量风险
            quality_issues = quality_analysis.get("quality_issues", [])
            risk_factors.extend(quality_issues)
            
            # 资源风险
            resource_issues = resource_analysis.get("resource_issues", [])
            for issue in resource_issues:
                risk_factors.append({
                    "factor": "资源风险",
                    "severity": issue.get("severity", "MEDIUM"),
                    "description": issue.get("issue", ""),
                    "impact": issue.get("description", ""),
                    "category": "RESOURCE_RISK"
                })
            
            # 2. 高级风险识别和分析
            advanced_risks = await self._identify_advanced_risks(
                health_analysis, team_analysis, progress_analysis, 
                quality_analysis, resource_analysis
            )
            risk_factors.extend(advanced_risks)
            
            # 3. 风险关联性分析
            correlated_risks = await self._analyze_risk_correlations(risk_factors)
            risk_factors.extend(correlated_risks)
            
            # 4. 风险优先级排序
            prioritized_risks = await self._prioritize_risks(risk_factors)
            
            # 5. 风险缓解建议
            for risk in prioritized_risks:
                if not risk.get("mitigation_strategies"):
                    risk["mitigation_strategies"] = await self._generate_risk_mitigation_strategies(risk)
            
            return prioritized_risks
            
        except Exception as e:
            self.logger.error(f"Error identifying risk factors: {str(e)}")
            return []
    
    async def _identify_advanced_risks(self, health_analysis, team_analysis, 
                                     progress_analysis, quality_analysis, 
                                     resource_analysis) -> List[Dict[str, Any]]:
        """
        识别高级风险因素
        
        基于多维度分析识别潜在的复合风险和隐性风险
        """
        try:
            advanced_risks = []
            
            # 技术债务风险
            tech_debt_risk = await self._assess_technical_debt_risk(quality_analysis)
            if tech_debt_risk:
                advanced_risks.append(tech_debt_risk)
            
            # 依赖风险
            dependency_risk = await self._assess_dependency_risk(health_analysis)
            if dependency_risk:
                advanced_risks.append(dependency_risk)
            
            # 扩展性风险
            scalability_risk = await self._assess_scalability_risk(resource_analysis, team_analysis)
            if scalability_risk:
                advanced_risks.append(scalability_risk)
            
            # 合规风险
            compliance_risk = await self._assess_compliance_risk(quality_analysis)
            if compliance_risk:
                advanced_risks.append(compliance_risk)
            
            # 知识风险（关键人员依赖）
            knowledge_risk = await self._assess_knowledge_risk(team_analysis)
            if knowledge_risk:
                advanced_risks.append(knowledge_risk)
            
            # 集成风险
            integration_risk = await self._assess_integration_risk(health_analysis, quality_analysis)
            if integration_risk:
                advanced_risks.append(integration_risk)
            
            # 性能风险
            performance_risk = await self._assess_performance_risk(resource_analysis, quality_analysis)
            if performance_risk:
                advanced_risks.append(performance_risk)
            
            # 安全风险
            security_risk = await self._assess_security_risk(quality_analysis)
            if security_risk:
                advanced_risks.append(security_risk)
            
            return advanced_risks
            
        except Exception as e:
            self.logger.error(f"Error identifying advanced risks: {str(e)}")
            return []
    
    async def _assess_technical_debt_risk(self, quality_analysis) -> Optional[Dict[str, Any]]:
        """评估技术债务风险"""
        try:
            code_quality_risk = quality_analysis.get("code_quality_risk", 0.0)
            requirements_quality_risk = quality_analysis.get("requirements_quality_risk", 0.0)
            
            # 计算技术债务风险指数
            debt_risk_score = (code_quality_risk + requirements_quality_risk) / 2
            
            if debt_risk_score > 0.6:
                return {
                    "factor": "技术债务风险",
                    "severity": "HIGH" if debt_risk_score > 0.8 else "MEDIUM",
                    "description": f"技术债务风险指数为{debt_risk_score:.2f}，可能影响长期维护性",
                    "impact": "增加维护成本，降低开发效率，影响系统稳定性",
                    "category": "TECHNICAL_RISK",
                    "risk_score": debt_risk_score,
                    "indicators": [
                        "代码质量下降",
                        "需求质量不佳",
                        "重构需求增加",
                        "维护成本上升"
                    ]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing technical debt risk: {str(e)}")
            return None
    
    async def _assess_dependency_risk(self, health_analysis) -> Optional[Dict[str, Any]]:
        """评估依赖风险"""
        try:
            # 基于健康分析中的外部依赖情况评估
            overall_health = health_analysis.get("overall_health", 1.0)
            
            # 如果整体健康度低，可能存在依赖风险
            if overall_health < 0.6:
                return {
                    "factor": "外部依赖风险",
                    "severity": "MEDIUM",
                    "description": "系统对外部服务依赖度较高，存在单点故障风险",
                    "impact": "外部服务故障可能导致系统不可用",
                    "category": "TECHNICAL_RISK",
                    "risk_score": 1.0 - overall_health,
                    "indicators": [
                        "AI API服务依赖",
                        "第三方服务集成",
                        "网络连接依赖",
                        "缺乏降级方案"
                    ]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing dependency risk: {str(e)}")
            return None
    
    async def _assess_scalability_risk(self, resource_analysis, team_analysis) -> Optional[Dict[str, Any]]:
        """评估扩展性风险"""
        try:
            resource_health = resource_analysis.get("resource_health", 1.0)
            team_capacity = team_analysis.get("capacity_score", 1.0)
            
            # 计算扩展性风险
            scalability_risk_score = 1.0 - min(resource_health, team_capacity)
            
            if scalability_risk_score > 0.5:
                return {
                    "factor": "系统扩展性风险",
                    "severity": "HIGH" if scalability_risk_score > 0.7 else "MEDIUM",
                    "description": f"系统扩展能力不足，风险指数{scalability_risk_score:.2f}",
                    "impact": "无法应对用户增长，性能瓶颈，服务质量下降",
                    "category": "TECHNICAL_RISK",
                    "risk_score": scalability_risk_score,
                    "indicators": [
                        "资源利用率高",
                        "团队负载重",
                        "架构扩展性差",
                        "性能监控不足"
                    ]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing scalability risk: {str(e)}")
            return None
    
    async def _assess_compliance_risk(self, quality_analysis) -> Optional[Dict[str, Any]]:
        """评估合规风险"""
        try:
            # 基于质量分析评估合规风险
            overall_quality_risk = quality_analysis.get("overall_quality_risk", 0.0)
            
            if overall_quality_risk > 0.6:
                return {
                    "factor": "合规风险",
                    "severity": "HIGH",
                    "description": "质量标准不达标，可能存在合规风险",
                    "impact": "监管处罚，服务停止，法律风险",
                    "category": "BUSINESS_RISK",
                    "risk_score": overall_quality_risk,
                    "indicators": [
                        "数据安全标准",
                        "内容审核机制",
                        "隐私保护措施",
                        "行业规范遵循"
                    ]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing compliance risk: {str(e)}")
            return None
    
    async def _assess_knowledge_risk(self, team_analysis) -> Optional[Dict[str, Any]]:
        """评估知识风险（关键人员依赖）"""
        try:
            capacity_score = team_analysis.get("capacity_score", 1.0)
            
            # 如果团队能力评分低，可能存在知识集中风险
            if capacity_score < 0.7:
                return {
                    "factor": "知识风险",
                    "severity": "MEDIUM",
                    "description": "关键知识过度集中在少数人员，存在知识流失风险",
                    "impact": "关键人员离职可能导致项目停滞",
                    "category": "PROJECT_RISK",
                    "risk_score": 1.0 - capacity_score,
                    "indicators": [
                        "关键技能集中",
                        "文档不完善",
                        "知识传承不足",
                        "团队依赖性强"
                    ]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing knowledge risk: {str(e)}")
            return None
    
    async def _assess_integration_risk(self, health_analysis, quality_analysis) -> Optional[Dict[str, Any]]:
        """评估集成风险"""
        try:
            overall_health = health_analysis.get("overall_health", 1.0)
            overall_quality_risk = quality_analysis.get("overall_quality_risk", 0.0)
            
            # 计算集成风险指数
            integration_risk_score = (1.0 - overall_health + overall_quality_risk) / 2
            
            if integration_risk_score > 0.5:
                return {
                    "factor": "系统集成风险",
                    "severity": "MEDIUM",
                    "description": f"系统集成复杂度高，风险指数{integration_risk_score:.2f}",
                    "impact": "集成失败，数据不一致，功能异常",
                    "category": "TECHNICAL_RISK",
                    "risk_score": integration_risk_score,
                    "indicators": [
                        "接口兼容性",
                        "数据一致性",
                        "版本管理",
                        "集成测试覆盖"
                    ]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing integration risk: {str(e)}")
            return None
    
    async def _assess_performance_risk(self, resource_analysis, quality_analysis) -> Optional[Dict[str, Any]]:
        """评估性能风险"""
        try:
            resource_health = resource_analysis.get("resource_health", 1.0)
            
            # 基于资源健康度评估性能风险
            performance_risk_score = 1.0 - resource_health
            
            if performance_risk_score > 0.6:
                return {
                    "factor": "系统性能风险",
                    "severity": "HIGH" if performance_risk_score > 0.8 else "MEDIUM",
                    "description": f"系统性能存在瓶颈，风险指数{performance_risk_score:.2f}",
                    "impact": "响应时间增加，用户体验下降，系统不稳定",
                    "category": "TECHNICAL_RISK",
                    "risk_score": performance_risk_score,
                    "indicators": [
                        "响应时间长",
                        "资源利用率高",
                        "并发处理能力不足",
                        "缓存效率低"
                    ]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing performance risk: {str(e)}")
            return None
    
    async def _assess_security_risk(self, quality_analysis) -> Optional[Dict[str, Any]]:
        """评估安全风险"""
        try:
            overall_quality_risk = quality_analysis.get("overall_quality_risk", 0.0)
            
            # 基于质量风险评估安全风险
            if overall_quality_risk > 0.7:
                return {
                    "factor": "信息安全风险",
                    "severity": "HIGH",
                    "description": "系统存在潜在安全漏洞和风险",
                    "impact": "数据泄露，系统被攻击，用户隐私泄露",
                    "category": "SECURITY_RISK",
                    "risk_score": overall_quality_risk,
                    "indicators": [
                        "输入验证不足",
                        "权限控制缺陷",
                        "数据加密不完善",
                        "安全审计不足"
                    ]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Error assessing security risk: {str(e)}")
            return None
    
    async def _analyze_risk_correlations(self, risk_factors) -> List[Dict[str, Any]]:
        """
        分析风险关联性
        
        识别风险之间的相互影响和级联效应
        """
        try:
            correlated_risks = []
            
            # 按类别分组风险
            risk_by_category = {}
            for risk in risk_factors:
                category = risk.get("category", "OTHER")
                if category not in risk_by_category:
                    risk_by_category[category] = []
                risk_by_category[category].append(risk)
            
            # 识别高风险组合
            high_severity_risks = [r for r in risk_factors if r.get("severity") == "HIGH"]
            critical_risks = [r for r in risk_factors if r.get("severity") == "CRITICAL"]
            
            # 如果存在多个高风险或关键风险，识别级联风险
            if len(high_severity_risks) >= 2 or len(critical_risks) >= 1:
                cascade_risk = {
                    "factor": "风险级联效应",
                    "severity": "CRITICAL" if critical_risks else "HIGH",
                    "description": f"发现{len(high_severity_risks)}个高风险和{len(critical_risks)}个关键风险，存在级联效应",
                    "impact": "多个风险同时发生可能导致项目失败",
                    "category": "CASCADE_RISK",
                    "risk_score": min(1.0, (len(high_severity_risks) * 0.3 + len(critical_risks) * 0.5)),
                    "related_risks": [r.get("factor", "") for r in high_severity_risks + critical_risks]
                }
                correlated_risks.append(cascade_risk)
            
            # 识别技术风险和业务风险的交叉影响
            tech_risks = risk_by_category.get("TECHNICAL_RISK", [])
            business_risks = risk_by_category.get("BUSINESS_RISK", [])
            
            if tech_risks and business_risks:
                cross_impact_risk = {
                    "factor": "技术-业务风险交叉影响",
                    "severity": "MEDIUM",
                    "description": "技术风险和业务风险相互影响，可能放大整体风险",
                    "impact": "技术问题影响业务目标，业务压力加剧技术风险",
                    "category": "CROSS_IMPACT_RISK",
                    "risk_score": 0.6,
                    "technical_risks": [r.get("factor", "") for r in tech_risks],
                    "business_risks": [r.get("factor", "") for r in business_risks]
                }
                correlated_risks.append(cross_impact_risk)
            
            return correlated_risks
            
        except Exception as e:
            self.logger.error(f"Error analyzing risk correlations: {str(e)}")
            return []
    
    async def _prioritize_risks(self, risk_factors) -> List[Dict[str, Any]]:
        """
        风险优先级排序
        
        基于严重程度、影响范围、发生概率等因素排序
        """
        try:
            # 定义严重程度权重
            severity_weights = {
                "CRITICAL": 1.0,
                "HIGH": 0.8,
                "MEDIUM": 0.6,
                "LOW": 0.4
            }
            
            # 计算风险优先级分数
            for risk in risk_factors:
                severity = risk.get("severity", "MEDIUM")
                risk_score = risk.get("risk_score", 0.5)
                
                # 综合评分 = 严重程度权重 * 风险分数
                priority_score = severity_weights.get(severity, 0.5) * risk_score
                risk["priority_score"] = priority_score
                
                # 添加风险等级
                if priority_score >= 0.8:
                    risk["risk_level"] = "CRITICAL"
                elif priority_score >= 0.6:
                    risk["risk_level"] = "HIGH"
                elif priority_score >= 0.4:
                    risk["risk_level"] = "MEDIUM"
                else:
                    risk["risk_level"] = "LOW"
            
            # 按优先级分数排序
            sorted_risks = sorted(risk_factors, key=lambda x: x.get("priority_score", 0), reverse=True)
            
            return sorted_risks
            
        except Exception as e:
            self.logger.error(f"Error prioritizing risks: {str(e)}")
            return risk_factors
    
    async def _generate_risk_mitigation_strategies(self, risk) -> List[str]:
        """
        生成风险缓解策略
        
        基于风险类型和严重程度生成具体的缓解措施
        """
        try:
            strategies = []
            risk_factor = risk.get("factor", "")
            category = risk.get("category", "")
            severity = risk.get("severity", "MEDIUM")
            
            # 基于风险类别生成通用策略
            if category == "TECHNICAL_RISK":
                strategies.extend([
                    "建立技术风险监控机制",
                    "制定技术应急预案",
                    "加强代码审查和质量控制",
                    "实施持续集成和自动化测试"
                ])
            elif category == "BUSINESS_RISK":
                strategies.extend([
                    "制定业务连续性计划",
                    "建立风险评估流程",
                    "加强合规性检查",
                    "建立客户沟通机制"
                ])
            elif category == "PROJECT_RISK":
                strategies.extend([
                    "优化项目管理流程",
                    "加强团队沟通协作",
                    "建立项目风险预警机制",
                    "合理分配资源和任务"
                ])
            elif category == "SECURITY_RISK":
                strategies.extend([
                    "实施安全审计和渗透测试",
                    "加强访问控制和权限管理",
                    "建立安全事件响应机制",
                    "定期更新安全策略"
                ])
            
            # 基于具体风险因素生成针对性策略
            if "技术债务" in risk_factor:
                strategies.extend([
                    "制定技术债务清理计划",
                    "分配专门时间进行重构",
                    "建立代码质量标准"
                ])
            elif "依赖" in risk_factor:
                strategies.extend([
                    "建立多供应商策略",
                    "实施服务降级机制",
                    "建立依赖监控告警"
                ])
            elif "性能" in risk_factor:
                strategies.extend([
                    "实施性能监控和调优",
                    "建立负载均衡机制",
                    "优化数据库和缓存策略"
                ])
            elif "团队" in risk_factor or "知识" in risk_factor:
                strategies.extend([
                    "建立知识文档和培训体系",
                    "实施代码审查和知识分享",
                    "建立关键岗位备份机制"
                ])
            
            # 基于严重程度调整策略紧急程度
            if severity in ["CRITICAL", "HIGH"]:
                strategies.insert(0, "立即启动风险应急响应")
                strategies.append("建立24小时监控机制")
            
            # 去重并限制数量
            unique_strategies = list(dict.fromkeys(strategies))[:8]
            
            return unique_strategies
            
        except Exception as e:
            self.logger.error(f"Error generating mitigation strategies: {str(e)}")
            return ["建立风险监控机制", "制定应急预案", "加强质量控制"]
    
    async def _extract_key_metrics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键指标"""
        try:
            dimensions = analysis_result.get("dimensions", {})
            
            key_metrics = {
                "overall_health_score": analysis_result.get("overall_health_score", 0.0),
                "health_level": analysis_result.get("health_level", "UNKNOWN"),
                "risk_count": len(analysis_result.get("risk_factors", [])),
                "critical_risks": len([r for r in analysis_result.get("risk_factors", []) 
                                     if r.get("severity") == "CRITICAL"]),
                "high_risks": len([r for r in analysis_result.get("risk_factors", []) 
                                 if r.get("severity") == "HIGH"])
            }
            
            # 各维度得分
            if "health" in dimensions:
                key_metrics["health_score"] = dimensions["health"].get("overall_health", 0.0)
            
            if "team" in dimensions:
                key_metrics["team_capacity_score"] = dimensions["team"].get("capacity_score", 0.0)
            
            if "progress" in dimensions:
                key_metrics["timeline_health"] = dimensions["progress"].get("timeline_health", 0.0)
                key_metrics["delivery_risk"] = dimensions["progress"].get("delivery_risk", "UNKNOWN")
            
            if "quality" in dimensions:
                key_metrics["quality_risk"] = dimensions["quality"].get("overall_quality_risk", 0.0)
            
            if "resources" in dimensions:
                key_metrics["resource_efficiency"] = dimensions["resources"].get("resource_efficiency", 0.0)
            
            return key_metrics
            
        except Exception as e:
            self.logger.error(f"Error extracting key metrics: {str(e)}")
            return {}
    
    async def _generate_project_improvement_recommendations(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成项目改进建议"""
        try:
            recommendations = []
            overall_score = analysis_result.get("overall_health_score", 0.0)
            dimensions = analysis_result.get("dimensions", {})
            
            # 基于整体健康度的建议
            if overall_score < 0.4:
                recommendations.append({
                    "priority": "CRITICAL",
                    "category": "OVERALL_HEALTH",
                    "title": "项目健康度危急",
                    "description": "项目整体健康度极低，需要立即采取行动",
                    "actions": [
                        "召开紧急项目评估会议",
                        "重新评估项目可行性",
                        "考虑项目重启或终止",
                        "制定紧急救援计划"
                    ]
                })
            elif overall_score < 0.6:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "OVERALL_HEALTH",
                    "title": "项目健康度告警",
                    "description": "项目健康度偏低，需要重点关注和改进",
                    "actions": [
                        "识别主要问题和风险点",
                        "制定针对性改进计划",
                        "加强项目监控和管理",
                        "定期评估改进效果"
                    ]
                })
            
            # 基于具体维度的建议
            health_analysis = dimensions.get("health", {})
            if health_analysis.get("overall_health", 0.0) < 0.6:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "PROJECT_HEALTH",
                    "title": "改善项目基础健康度",
                    "description": "项目基础健康度需要改善",
                    "actions": [
                        "优化项目管理流程",
                        "加强团队沟通协作",
                        "完善项目文档和规范",
                        "建立项目健康度监控"
                    ]
                })
            
            team_analysis = dimensions.get("team", {})
            if team_analysis.get("capacity_score", 0.0) < 0.6:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "TEAM_CAPACITY",
                    "title": "提升团队能力",
                    "description": "团队能力需要提升以支撑项目目标",
                    "actions": [
                        "评估团队技能缺口",
                        "提供针对性培训",
                        "优化团队结构配置",
                        "建立知识分享机制"
                    ]
                })
            
            progress_analysis = dimensions.get("progress", {})
            if progress_analysis.get("delivery_risk") in ["HIGH", "CRITICAL"]:
                recommendations.append({
                    "priority": "CRITICAL",
                    "category": "SCHEDULE_MANAGEMENT",
                    "title": "紧急进度管控",
                    "description": "项目存在严重的交付风险",
                    "actions": [
                        "重新制定项目计划",
                        "调整项目范围或资源",
                        "建立每日进度跟踪",
                        "准备风险应对预案"
                    ]
                })
            
            quality_analysis = dimensions.get("quality", {})
            if quality_analysis.get("overall_quality_risk", 0.0) > 0.6:
                recommendations.append({
                    "priority": "HIGH",
                    "category": "QUALITY_MANAGEMENT",
                    "title": "加强质量管控",
                    "description": "项目质量风险较高，需要加强管控",
                    "actions": [
                        "建立质量门禁机制",
                        "增加代码审查和测试",
                        "完善质量标准和流程",
                        "建立质量度量体系"
                    ]
                })
            
            resource_analysis = dimensions.get("resources", {})
            if resource_analysis.get("resource_efficiency", 0.0) < 0.6:
                recommendations.append({
                    "priority": "MEDIUM",
                    "category": "RESOURCE_OPTIMIZATION",
                    "title": "优化资源配置",
                    "description": "资源配置效率有待提升",
                    "actions": [
                        "重新评估资源需求",
                        "优化资源分配策略",
                        "提高资源利用效率",
                        "建立资源监控机制"
                    ]
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating improvement recommendations: {str(e)}")
            return []
    
    def _get_optimal_team_size(self, project_type: str) -> int:
        """获取项目类型的最优团队规模"""
        optimal_sizes = {
            "web_application": 6,
            "mobile_app": 4,
            "api_service": 3,
            "data_platform": 8,
            "desktop_app": 5,
            "embedded_system": 4
        }
        return optimal_sizes.get(project_type, 5)
    
    def _estimate_project_complexity(self, context: ProjectContext) -> str:
        """估算项目复杂度"""
        try:
            complexity_score = 0
            
            # 基于团队规模
            if context.team_size:
                if context.team_size > 10:
                    complexity_score += 2
                elif context.team_size > 5:
                    complexity_score += 1
            
            # 基于需求数量
            if context.requirements:
                req_count = len(context.requirements)
                if req_count > 50:
                    complexity_score += 2
                elif req_count > 20:
                    complexity_score += 1
            
            # 基于项目类型
            complex_types = ["data_platform", "embedded_system"]
            if context.project_type in complex_types:
                complexity_score += 1
            
            # 基于时间线
            if context.timeline:
                total_days = context.timeline.get("total_days", 0)
                if total_days > 365:
                    complexity_score += 2
                elif total_days > 180:
                    complexity_score += 1
            
            if complexity_score >= 4:
                return "HIGH"
            elif complexity_score >= 2:
                return "MEDIUM"
            else:
                return "LOW"
                
        except Exception as e:
            self.logger.error(f"Error estimating project complexity: {str(e)}")
            return "MEDIUM"
    
    def _get_required_skills_by_project_type(self, project_type: str) -> List[str]:
        """根据项目类型获取所需技能"""
        skill_requirements = {
            "web_application": [
                "前端开发", "后端开发", "数据库设计", "UI/UX设计", "测试", "运维"
            ],
            "mobile_app": [
                "移动端开发", "UI/UX设计", "后端开发", "测试", "应用商店发布"
            ],
            "api_service": [
                "后端开发", "数据库设计", "API设计", "测试", "运维"
            ],
            "data_platform": [
                "数据工程", "数据分析", "机器学习", "大数据技术", "数据可视化", "运维"
            ],
            "desktop_app": [
                "桌面应用开发", "UI设计", "数据库设计", "测试", "安装部署"
            ],
            "embedded_system": [
                "嵌入式开发", "硬件设计", "驱动开发", "测试", "系统集成"
            ]
        }
        return skill_requirements.get(project_type, ["开发", "测试", "设计"])
    
    async def _calculate_test_coverage(self, test_data: Dict) -> TestCoverageAnalysis:
        """
        计算测试覆盖率
        
        Args:
            test_data: 测试数据，包含测试用例、需求等信息
            
        Returns:
            TestCoverageAnalysis: 测试覆盖率分析结果
        """
        try:
            self.logger.info("Calculating test coverage analysis")
            
            # 提取测试数据
            test_cases = test_data.get("test_cases", [])
            requirements = test_data.get("requirements", [])
            coverage_data = test_data.get("coverage", {})
            
            # 计算覆盖率指标
            metrics = await self._calculate_coverage_metrics(test_cases, requirements)
            
            # 分析覆盖率
            analysis = TestCoverageAnalysis()
            
            # 计算总体覆盖率
            analysis.overall_coverage_rate = await self._calculate_overall_coverage_rate(metrics, coverage_data)
            
            # 计算需求覆盖率
            analysis.requirement_coverage_rate = await self._calculate_requirement_coverage_rate(test_cases, requirements)
            
            # 计算功能覆盖率
            analysis.functional_coverage_rate = await self._calculate_functional_coverage_rate(test_cases, requirements)
            
            # 计算场景覆盖率
            analysis.scenario_coverage_rate = await self._calculate_scenario_coverage_rate(test_cases, requirements)
            
            # 识别未覆盖的需求
            analysis.uncovered_requirements = await self._identify_uncovered_requirements(test_cases, requirements)
            
            # 识别未覆盖的场景
            analysis.uncovered_scenarios = await self._identify_uncovered_scenarios(test_cases, requirements)
            
            # 分析覆盖率缺口
            analysis.coverage_gaps = await self._analyze_detailed_coverage_gaps(test_cases, requirements)
            
            # 生成覆盖率改进建议
            analysis.coverage_recommendations = await self._generate_coverage_recommendations(analysis)
            
            self.logger.info(f"Test coverage analysis completed: overall={analysis.overall_coverage_rate:.2f}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error calculating test coverage: {str(e)}", exc_info=True)
            return TestCoverageAnalysis()
    
    async def _calculate_coverage_metrics(self, test_cases: List[Dict], requirements: List[Dict]) -> TestCoverageMetrics:
        """
        计算测试覆盖率基础指标
        
        Args:
            test_cases: 测试用例列表
            requirements: 需求列表
            
        Returns:
            TestCoverageMetrics: 覆盖率指标
        """
        try:
            metrics = TestCoverageMetrics()
            
            # 基础统计
            metrics.total_requirements = len(requirements)
            metrics.test_case_count = len(test_cases)
            
            # 统计自动化和手动测试
            for test in test_cases:
                if test.get("is_automated", False):
                    metrics.automated_test_count += 1
                else:
                    metrics.manual_test_count += 1
            
            # 统计被覆盖的需求
            covered_req_ids = set()
            for test in test_cases:
                req_ids = test.get("requirement_ids", [])
                if isinstance(req_ids, list):
                    covered_req_ids.update(req_ids)
                elif req_ids:  # 单个需求ID
                    covered_req_ids.add(req_ids)
            
            metrics.covered_requirements = len(covered_req_ids)
            
            # 统计测试场景
            all_scenarios = set()
            covered_scenarios = set()
            
            for req in requirements:
                # 从需求中提取预期的测试场景
                req_scenarios = await self._extract_test_scenarios_from_requirement(req)
                all_scenarios.update(req_scenarios)
                
                # 检查哪些场景被测试覆盖
                req_id = req.get("id")
                for test in test_cases:
                    if req_id in test.get("requirement_ids", []):
                        test_scenarios = await self._extract_test_scenarios_from_test(test)
                        covered_scenarios.update(test_scenarios)
            
            metrics.total_scenarios = len(all_scenarios)
            metrics.covered_scenarios = len(covered_scenarios)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating coverage metrics: {str(e)}")
            return TestCoverageMetrics()
    
    async def _calculate_overall_coverage_rate(self, metrics: TestCoverageMetrics, coverage_data: Dict) -> float:
        """
        计算总体覆盖率
        
        Args:
            metrics: 覆盖率指标
            coverage_data: 覆盖率数据
            
        Returns:
            float: 总体覆盖率 (0-1)
        """
        try:
            # 如果有代码覆盖率数据，优先使用
            if coverage_data.get("code_coverage"):
                return float(coverage_data["code_coverage"]) / 100.0
            
            # 否则基于需求覆盖率计算
            if metrics.total_requirements > 0:
                return metrics.covered_requirements / metrics.total_requirements
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating overall coverage rate: {str(e)}")
            return 0.0
    
    async def _calculate_requirement_coverage_rate(self, test_cases: List[Dict], requirements: List[Dict]) -> float:
        """
        计算需求覆盖率
        
        Args:
            test_cases: 测试用例列表
            requirements: 需求列表
            
        Returns:
            float: 需求覆盖率 (0-1)
        """
        try:
            if not requirements:
                return 1.0
            
            # 统计被测试覆盖的需求
            covered_requirements = set()
            
            for test in test_cases:
                req_ids = test.get("requirement_ids", [])
                if isinstance(req_ids, list):
                    covered_requirements.update(req_ids)
                elif req_ids:
                    covered_requirements.add(req_ids)
            
            total_requirements = len(requirements)
            covered_count = len(covered_requirements)
            
            return covered_count / total_requirements if total_requirements > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating requirement coverage rate: {str(e)}")
            return 0.0
    
    async def _calculate_functional_coverage_rate(self, test_cases: List[Dict], requirements: List[Dict]) -> float:
        """
        计算功能覆盖率
        
        Args:
            test_cases: 测试用例列表
            requirements: 需求列表
            
        Returns:
            float: 功能覆盖率 (0-1)
        """
        try:
            if not requirements:
                return 1.0
            
            # 提取所有功能模块
            all_functions = set()
            covered_functions = set()
            
            for req in requirements:
                # 从需求中提取功能模块
                functions = await self._extract_functions_from_requirement(req)
                all_functions.update(functions)
            
            # 统计被测试覆盖的功能
            for test in test_cases:
                test_functions = await self._extract_functions_from_test(test)
                covered_functions.update(test_functions)
            
            if len(all_functions) == 0:
                return 1.0
            
            return len(covered_functions) / len(all_functions)
            
        except Exception as e:
            self.logger.error(f"Error calculating functional coverage rate: {str(e)}")
            return 0.0
    
    async def _calculate_scenario_coverage_rate(self, test_cases: List[Dict], requirements: List[Dict]) -> float:
        """
        计算场景覆盖率
        
        Args:
            test_cases: 测试用例列表
            requirements: 需求列表
            
        Returns:
            float: 场景覆盖率 (0-1)
        """
        try:
            if not requirements:
                return 1.0
            
            # 提取所有测试场景
            all_scenarios = set()
            covered_scenarios = set()
            
            for req in requirements:
                # 从需求中提取预期的测试场景
                scenarios = await self._extract_test_scenarios_from_requirement(req)
                all_scenarios.update(scenarios)
            
            # 统计被覆盖的场景
            for test in test_cases:
                test_scenarios = await self._extract_test_scenarios_from_test(test)
                covered_scenarios.update(test_scenarios)
            
            if len(all_scenarios) == 0:
                return 1.0
            
            return len(covered_scenarios) / len(all_scenarios)
            
        except Exception as e:
            self.logger.error(f"Error calculating scenario coverage rate: {str(e)}")
            return 0.0
    
    async def _identify_uncovered_requirements(self, test_cases: List[Dict], requirements: List[Dict]) -> List[Dict]:
        """
        识别未覆盖的需求
        
        Args:
            test_cases: 测试用例列表
            requirements: 需求列表
            
        Returns:
            List[Dict]: 未覆盖的需求列表
        """
        try:
            # 获取被覆盖的需求ID
            covered_req_ids = set()
            for test in test_cases:
                req_ids = test.get("requirement_ids", [])
                if isinstance(req_ids, list):
                    covered_req_ids.update(req_ids)
                elif req_ids:
                    covered_req_ids.add(req_ids)
            
            # 找出未覆盖的需求
            uncovered_requirements = []
            for req in requirements:
                req_id = req.get("id")
                if req_id not in covered_req_ids:
                    uncovered_requirements.append({
                        "id": req_id,
                        "title": req.get("title", ""),
                        "description": req.get("description", ""),
                        "priority": req.get("priority", "MEDIUM"),
                        "category": req.get("category", "未分类")
                    })
            
            return uncovered_requirements
            
        except Exception as e:
            self.logger.error(f"Error identifying uncovered requirements: {str(e)}")
            return []
    
    async def _identify_uncovered_scenarios(self, test_cases: List[Dict], requirements: List[Dict]) -> List[str]:
        """
        识别未覆盖的测试场景
        
        Args:
            test_cases: 测试用例列表
            requirements: 需求列表
            
        Returns:
            List[str]: 未覆盖的场景列表
        """
        try:
            # 提取所有预期场景
            all_scenarios = set()
            for req in requirements:
                scenarios = await self._extract_test_scenarios_from_requirement(req)
                all_scenarios.update(scenarios)
            
            # 提取已覆盖场景
            covered_scenarios = set()
            for test in test_cases:
                scenarios = await self._extract_test_scenarios_from_test(test)
                covered_scenarios.update(scenarios)
            
            # 计算未覆盖场景
            uncovered_scenarios = list(all_scenarios - covered_scenarios)
            
            return uncovered_scenarios
            
        except Exception as e:
            self.logger.error(f"Error identifying uncovered scenarios: {str(e)}")
            return []
    
    async def _analyze_detailed_coverage_gaps(self, test_cases: List[Dict], requirements: List[Dict]) -> List[Dict]:
        """
        分析详细的覆盖率缺口
        
        Args:
            test_cases: 测试用例列表
            requirements: 需求列表
            
        Returns:
            List[Dict]: 详细的覆盖率缺口分析
        """
        try:
            gaps = []
            
            for req in requirements:
                req_id = req.get("id")
                req_title = req.get("title", "")
                req_description = req.get("description", "")
                
                # 查找相关测试用例
                related_tests = []
                for test in test_cases:
                    if req_id in test.get("requirement_ids", []):
                        related_tests.append(test)
                
                # 分析覆盖情况
                gap_analysis = {
                    "requirement_id": req_id,
                    "requirement_title": req_title,
                    "requirement_description": req_description,
                    "test_count": len(related_tests),
                    "coverage_status": "FULL" if len(related_tests) >= 3 else "PARTIAL" if len(related_tests) > 0 else "NONE",
                    "missing_test_types": [],
                    "risk_level": "LOW"
                }
                
                # 分析缺失的测试类型
                if len(related_tests) == 0:
                    gap_analysis["missing_test_types"] = ["正常流程测试", "异常流程测试", "边界值测试", "性能测试"]
                    gap_analysis["risk_level"] = "HIGH"
                else:
                    # 检查测试类型覆盖
                    test_types = set()
                    for test in related_tests:
                        test_type = await self._classify_test_type(test)
                        test_types.add(test_type)
                    
                    expected_types = {"正常流程", "异常流程", "边界值"}
                    missing_types = expected_types - test_types
                    gap_analysis["missing_test_types"] = list(missing_types)
                    gap_analysis["risk_level"] = "MEDIUM" if missing_types else "LOW"
                
                if gap_analysis["coverage_status"] != "FULL" or gap_analysis["missing_test_types"]:
                    gaps.append(gap_analysis)
            
            return gaps
            
        except Exception as e:
            self.logger.error(f"Error analyzing detailed coverage gaps: {str(e)}")
            return []
    
    async def _generate_coverage_recommendations(self, analysis: TestCoverageAnalysis) -> List[str]:
        """
        生成覆盖率改进建议
        
        Args:
            analysis: 测试覆盖率分析结果
            
        Returns:
            List[str]: 改进建议列表
        """
        try:
            recommendations = []
            
            # 基于总体覆盖率的建议
            if analysis.overall_coverage_rate < 0.6:
                recommendations.append("总体测试覆盖率较低，建议优先补充核心功能的测试用例")
            elif analysis.overall_coverage_rate < 0.8:
                recommendations.append("测试覆盖率有待提升，建议重点关注高风险和高优先级功能")
            
            # 基于需求覆盖率的建议
            if analysis.requirement_coverage_rate < 0.7:
                recommendations.append("需求覆盖率不足，建议为每个需求至少创建2-3个测试用例")
            
            # 基于场景覆盖率的建议
            if analysis.scenario_coverage_rate < 0.6:
                recommendations.append("测试场景覆盖不全，建议补充异常流程和边界值测试")
            
            # 基于未覆盖需求的建议
            if len(analysis.uncovered_requirements) > 0:
                high_priority_uncovered = [req for req in analysis.uncovered_requirements 
                                         if req.get("priority") in ["HIGH", "CRITICAL"]]
                if high_priority_uncovered:
                    recommendations.append(f"发现{len(high_priority_uncovered)}个高优先级需求未被测试覆盖，建议立即补充")
            
            # 基于覆盖率缺口的建议
            high_risk_gaps = [gap for gap in analysis.coverage_gaps if gap.get("risk_level") == "HIGH"]
            if high_risk_gaps:
                recommendations.append(f"发现{len(high_risk_gaps)}个高风险覆盖缺口，建议优先处理")
            
            # 基于未覆盖场景的建议
            if len(analysis.uncovered_scenarios) > 0:
                recommendations.append(f"发现{len(analysis.uncovered_scenarios)}个未覆盖的测试场景，建议补充相应测试用例")
            
            # 自动化测试建议
            if analysis.overall_coverage_rate > 0.7:
                recommendations.append("覆盖率较好，建议提升测试自动化程度以提高测试效率")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating coverage recommendations: {str(e)}")
            return []
    
    async def _extract_test_scenarios_from_requirement(self, requirement: Dict) -> List[str]:
        """
        从需求中提取测试场景
        
        Args:
            requirement: 需求对象
            
        Returns:
            List[str]: 测试场景列表
        """
        try:
            scenarios = set()
            
            # 基础场景
            scenarios.add("正常流程")
            
            # 从验收标准中提取场景
            acceptance_criteria = requirement.get("acceptance_criteria", [])
            for criterion in acceptance_criteria:
                if isinstance(criterion, str):
                    if "异常" in criterion or "错误" in criterion:
                        scenarios.add("异常流程")
                    if "边界" in criterion or "最大" in criterion or "最小" in criterion:
                        scenarios.add("边界值")
                    if "性能" in criterion or "响应时间" in criterion:
                        scenarios.add("性能测试")
            
            # 从描述中提取场景
            description = requirement.get("description", "")
            if "异常" in description or "错误处理" in description:
                scenarios.add("异常流程")
            if "边界" in description or "限制" in description:
                scenarios.add("边界值")
            
            return list(scenarios)
            
        except Exception as e:
            self.logger.error(f"Error extracting test scenarios from requirement: {str(e)}")
            return ["正常流程"]
    
    async def _extract_test_scenarios_from_test(self, test_case: Dict) -> List[str]:
        """
        从测试用例中提取测试场景
        
        Args:
            test_case: 测试用例对象
            
        Returns:
            List[str]: 测试场景列表
        """
        try:
            scenarios = set()
            
            title = test_case.get("title", "").lower()
            description = test_case.get("description", "").lower()
            test_type = test_case.get("type", "").lower()
            
            # 根据标题和描述判断场景类型
            if any(keyword in title or keyword in description 
                   for keyword in ["正常", "成功", "有效", "normal", "success", "valid"]):
                scenarios.add("正常流程")
            
            if any(keyword in title or keyword in description 
                   for keyword in ["异常", "错误", "失败", "无效", "exception", "error", "invalid"]):
                scenarios.add("异常流程")
            
            if any(keyword in title or keyword in description 
                   for keyword in ["边界", "最大", "最小", "极限", "boundary", "max", "min", "limit"]):
                scenarios.add("边界值")
            
            if any(keyword in title or keyword in description 
                   for keyword in ["性能", "压力", "负载", "performance", "stress", "load"]):
                scenarios.add("性能测试")
            
            # 根据测试类型判断
            if test_type in ["functional", "功能"]:
                scenarios.add("正常流程")
            elif test_type in ["negative", "异常"]:
                scenarios.add("异常流程")
            elif test_type in ["boundary", "边界"]:
                scenarios.add("边界值")
            elif test_type in ["performance", "性能"]:
                scenarios.add("性能测试")
            
            # 如果没有识别出场景，默认为正常流程
            if not scenarios:
                scenarios.add("正常流程")
            
            return list(scenarios)
            
        except Exception as e:
            self.logger.error(f"Error extracting test scenarios from test case: {str(e)}")
            return ["正常流程"]
    
    async def _extract_functions_from_requirement(self, requirement: Dict) -> List[str]:
        """
        从需求中提取功能模块
        
        Args:
            requirement: 需求对象
            
        Returns:
            List[str]: 功能模块列表
        """
        try:
            functions = set()
            
            # 从分类中提取功能
            category = requirement.get("category", "")
            if category and category != "未分类":
                functions.add(category)
            
            # 从标题中提取功能关键词
            title = requirement.get("title", "")
            function_keywords = ["登录", "注册", "搜索", "支付", "订单", "用户管理", "数据管理", "报表", "导出", "导入"]
            for keyword in function_keywords:
                if keyword in title:
                    functions.add(keyword)
            
            # 从描述中提取功能
            description = requirement.get("description", "")
            for keyword in function_keywords:
                if keyword in description:
                    functions.add(keyword)
            
            # 如果没有识别出功能，使用分类或默认值
            if not functions:
                if category:
                    functions.add(category)
                else:
                    functions.add("通用功能")
            
            return list(functions)
            
        except Exception as e:
            self.logger.error(f"Error extracting functions from requirement: {str(e)}")
            return ["通用功能"]
    
    async def _extract_functions_from_test(self, test_case: Dict) -> List[str]:
        """
        从测试用例中提取功能模块
        
        Args:
            test_case: 测试用例对象
            
        Returns:
            List[str]: 功能模块列表
        """
        try:
            functions = set()
            
            # 从模块字段中提取
            module = test_case.get("module", "")
            if module:
                functions.add(module)
            
            # 从标题中提取功能关键词
            title = test_case.get("title", "")
            function_keywords = ["登录", "注册", "搜索", "支付", "订单", "用户管理", "数据管理", "报表", "导出", "导入"]
            for keyword in function_keywords:
                if keyword in title:
                    functions.add(keyword)
            
            # 从描述中提取功能
            description = test_case.get("description", "")
            for keyword in function_keywords:
                if keyword in description:
                    functions.add(keyword)
            
            # 如果没有识别出功能，使用模块或默认值
            if not functions:
                if module:
                    functions.add(module)
                else:
                    functions.add("通用功能")
            
            return list(functions)
            
        except Exception as e:
            self.logger.error(f"Error extracting functions from test case: {str(e)}")
            return ["通用功能"]
    
    async def _classify_test_type(self, test_case: Dict) -> str:
        """
        分类测试用例类型
        
        Args:
            test_case: 测试用例对象
            
        Returns:
            str: 测试类型
        """
        try:
            title = test_case.get("title", "").lower()
            description = test_case.get("description", "").lower()
            test_type = test_case.get("type", "").lower()
            
            # 直接从type字段判断
            if test_type:
                if test_type in ["functional", "功能"]:
                    return "正常流程"
                elif test_type in ["negative", "异常"]:
                    return "异常流程"
                elif test_type in ["boundary", "边界"]:
                    return "边界值"
                elif test_type in ["performance", "性能"]:
                    return "性能测试"
            
            # 从标题和描述判断
            if any(keyword in title or keyword in description 
                   for keyword in ["异常", "错误", "失败", "无效", "exception", "error", "invalid"]):
                return "异常流程"
            elif any(keyword in title or keyword in description 
                     for keyword in ["边界", "最大", "最小", "极限", "boundary", "max", "min", "limit"]):
                return "边界值"
            elif any(keyword in title or keyword in description 
                     for keyword in ["性能", "压力", "负载", "performance", "stress", "load"]):
                return "性能测试"
            else:
                return "正常流程"
                
        except Exception as e:
            self.logger.error(f"Error classifying test type: {str(e)}")
            return "正常流程"

    async def _analyze_coverage_gaps(self, existing_tests: List[Dict], requirements: List[Dict]) -> List[CoverageGap]:
        """
        分析测试覆盖率缺口（保持向后兼容）
        
        Args:
            existing_tests: 现有测试用例
            requirements: 需求列表
            
        Returns:
            List[CoverageGap]: 覆盖率缺口列表
        """
        try:
            gaps = []
            
            for req in requirements:
                req_id = req.get("id", 0)
                req_description = req.get("description", "")
                
                # 查找与该需求相关的测试用例
                related_tests = []
                for test in existing_tests:
                    if (req_id in test.get("requirement_ids", []) or 
                        str(req_id) in test.get("description", "")):
                        related_tests.append(test.get("title", ""))
                
                # 如果没有相关测试用例，或测试用例不足，则认为存在缺口
                if len(related_tests) < 2:  # 至少需要2个测试用例（正常和异常）
                    missing_scenarios = []
                    if len(related_tests) == 0:
                        missing_scenarios = ["正常流程测试", "异常流程测试", "边界值测试"]
                    else:
                        missing_scenarios = ["异常流程测试", "边界值测试"]
                    
                    gaps.append(CoverageGap(
                        requirement_id=req_id,
                        requirement_description=req_description,
                        missing_scenarios=missing_scenarios,
                        existing_tests=related_tests
                    ))
            
            return gaps
            
        except Exception as e:
            self.logger.error(f"Error analyzing coverage gaps: {str(e)}")
            return []
    
    async def _generate_test_suggestion(self, gap: CoverageGap) -> Optional[TestSuggestion]:
        """
        生成单个测试建议
        
        Args:
            gap: 覆盖率缺口
            
        Returns:
            Optional[TestSuggestion]: 测试建议
        """
        try:
            # 基于缺口生成测试建议
            if "正常流程测试" in gap.missing_scenarios:
                return TestSuggestion(
                    title=f"需求{gap.requirement_id}正常流程测试",
                    description=f"针对需求'{gap.requirement_description[:50]}...'的正常业务流程测试",
                    test_steps=[
                        "准备测试数据",
                        "执行正常业务操作",
                        "验证预期结果",
                        "清理测试数据"
                    ],
                    expected_result="系统按预期处理正常业务流程",
                    priority="HIGH",
                    rationale="确保核心功能正常工作"
                )
            elif "异常流程测试" in gap.missing_scenarios:
                return TestSuggestion(
                    title=f"需求{gap.requirement_id}异常流程测试",
                    description=f"针对需求'{gap.requirement_description[:50]}...'的异常情况测试",
                    test_steps=[
                        "准备异常测试数据",
                        "触发异常情况",
                        "验证错误处理",
                        "检查系统恢复"
                    ],
                    expected_result="系统正确处理异常情况并给出适当提示",
                    priority="MEDIUM",
                    rationale="确保系统在异常情况下的稳定性"
                )
            elif "边界值测试" in gap.missing_scenarios:
                return TestSuggestion(
                    title=f"需求{gap.requirement_id}边界值测试",
                    description=f"针对需求'{gap.requirement_description[:50]}...'的边界值测试",
                    test_steps=[
                        "识别输入参数边界值",
                        "测试最小边界值",
                        "测试最大边界值",
                        "测试边界值附近的值"
                    ],
                    expected_result="系统在边界值处理正确",
                    priority="MEDIUM",
                    rationale="确保系统在边界条件下的正确性"
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error generating test suggestion: {str(e)}")
            return None
    
    async def _identify_performance_bottlenecks(self, performance_metrics: Dict) -> List[str]:
        """
        识别性能瓶颈
        
        Args:
            performance_metrics: 性能指标
            
        Returns:
            List[str]: 瓶颈列表
        """
        try:
            bottlenecks = []
            
            # 检查响应时间
            response_time = performance_metrics.get("avg_response_time", 0)
            if response_time > 2.0:  # 超过2秒
                bottlenecks.append("响应时间过长")
            
            # 检查内存使用
            memory_usage = performance_metrics.get("memory_usage", 0)
            if memory_usage > 0.8:  # 超过80%
                bottlenecks.append("内存使用率过高")
            
            # 检查CPU使用
            cpu_usage = performance_metrics.get("cpu_usage", 0)
            if cpu_usage > 0.8:  # 超过80%
                bottlenecks.append("CPU使用率过高")
            
            # 检查数据库查询
            db_query_time = performance_metrics.get("db_query_time", 0)
            if db_query_time > 1.0:  # 超过1秒
                bottlenecks.append("数据库查询缓慢")
            
            return bottlenecks
            
        except Exception as e:
            self.logger.error(f"Error identifying performance bottlenecks: {str(e)}")
            return []
    
    async def _generate_optimization_suggestion(self, bottleneck: str) -> Optional[OptimizationSuggestion]:
        """
        生成优化建议
        
        Args:
            bottleneck: 性能瓶颈
            
        Returns:
            Optional[OptimizationSuggestion]: 优化建议
        """
        try:
            optimization_map = {
                "响应时间过长": OptimizationSuggestion(
                    title="优化系统响应时间",
                    description="系统响应时间超过可接受范围，需要进行性能优化",
                    optimization_type="PERFORMANCE",
                    expected_improvement="响应时间减少50%以上",
                    implementation_steps=[
                        "分析慢查询和性能瓶颈",
                        "优化数据库索引",
                        "实施缓存策略",
                        "优化代码逻辑"
                    ],
                    priority="HIGH"
                ),
                "内存使用率过高": OptimizationSuggestion(
                    title="优化内存使用",
                    description="系统内存使用率过高，可能导致性能问题",
                    optimization_type="RESOURCE",
                    expected_improvement="内存使用率降低至70%以下",
                    implementation_steps=[
                        "分析内存泄漏问题",
                        "优化数据结构",
                        "实施对象池",
                        "调整JVM参数"
                    ],
                    priority="MEDIUM"
                ),
                "CPU使用率过高": OptimizationSuggestion(
                    title="优化CPU使用",
                    description="系统CPU使用率过高，影响系统性能",
                    optimization_type="RESOURCE",
                    expected_improvement="CPU使用率降低至70%以下",
                    implementation_steps=[
                        "分析CPU密集型操作",
                        "优化算法复杂度",
                        "实施异步处理",
                        "考虑负载均衡"
                    ],
                    priority="MEDIUM"
                ),
                "数据库查询缓慢": OptimizationSuggestion(
                    title="优化数据库性能",
                    description="数据库查询响应时间过长，需要优化",
                    optimization_type="DATABASE",
                    expected_improvement="查询时间减少60%以上",
                    implementation_steps=[
                        "分析慢查询日志",
                        "优化SQL语句",
                        "添加合适的索引",
                        "考虑数据库分区"
                    ],
                    priority="HIGH"
                )
            }
            
            return optimization_map.get(bottleneck)
            
        except Exception as e:
            self.logger.error(f"Error generating optimization suggestion: {str(e)}")
            return None
    
    async def _generate_resource_optimization_suggestions(self, resource_usage: Dict) -> List[OptimizationSuggestion]:
        """
        生成资源优化建议
        
        Args:
            resource_usage: 资源使用情况
            
        Returns:
            List[OptimizationSuggestion]: 资源优化建议列表
        """
        try:
            suggestions = []
            
            # 检查磁盘使用
            disk_usage = resource_usage.get("disk_usage", 0)
            if disk_usage > 0.8:
                suggestions.append(OptimizationSuggestion(
                    title="优化磁盘空间使用",
                    description="磁盘使用率过高，需要清理和优化",
                    optimization_type="STORAGE",
                    expected_improvement="释放30%以上磁盘空间",
                    implementation_steps=[
                        "清理临时文件和日志",
                        "压缩历史数据",
                        "实施数据归档策略",
                        "监控磁盘使用趋势"
                    ],
                    priority="MEDIUM"
                ))
            
            # 检查网络带宽
            network_usage = resource_usage.get("network_usage", 0)
            if network_usage > 0.7:
                suggestions.append(OptimizationSuggestion(
                    title="优化网络带宽使用",
                    description="网络带宽使用率较高，可能影响用户体验",
                    optimization_type="NETWORK",
                    expected_improvement="减少30%网络流量",
                    implementation_steps=[
                        "实施数据压缩",
                        "优化图片和静态资源",
                        "使用CDN加速",
                        "实施缓存策略"
                    ],
                    priority="LOW"
                ))
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating resource optimization suggestions: {str(e)}")
            return []
    
    def _convert_test_suggestion_to_dict(self, suggestion: TestSuggestion) -> Dict:
        """
        将测试建议转换为字典格式
        
        Args:
            suggestion: 测试建议对象
            
        Returns:
            Dict: 字典格式的建议
        """
        return {
            "type": SuggestionType.TEST_IMPROVEMENT.value,
            "category": SuggestionCategory.TESTABILITY.value,
            "title": suggestion.title,
            "description": suggestion.description,
            "priority": suggestion.priority,
            "action_items": suggestion.test_steps,
            "expected_benefit": f"预期结果：{suggestion.expected_result}",
            "estimated_effort": "1-2天",
            "rationale": suggestion.rationale
        }
    
    async def _sort_suggestions_by_priority(self, suggestions: List[Dict]) -> List[Dict]:
        """
        按优先级排序建议
        
        Args:
            suggestions: 建议列表
            
        Returns:
            List[Dict]: 排序后的建议列表
        """
        try:
            def get_priority_weight(suggestion: Dict) -> float:
                priority = suggestion.get("priority", "MEDIUM")
                return self.config["priority_weights"].get(priority, 0.5)
            
            return sorted(suggestions, key=get_priority_weight, reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error sorting suggestions by priority: {str(e)}")
            return suggestions
    
    def _get_priority_weight(self, priority: str) -> float:
        """
        获取优先级权重
        
        Args:
            priority: 优先级字符串
            
        Returns:
            float: 权重值
        """
        return self.config["priority_weights"].get(priority, 0.5)
    
    async def save_suggestion(self, suggestion_data: Dict, user_id: int, session_id: Optional[int] = None) -> Optional[AISuggestion]:
        """
        保存建议到数据库
        
        Args:
            suggestion_data: 建议数据
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            Optional[AISuggestion]: 保存的建议对象
        """
        try:
            suggestion = AISuggestion(
                title=suggestion_data.get("title", ""),
                description=suggestion_data.get("description", ""),
                type=SuggestionType(suggestion_data.get("type", SuggestionType.QUALITY_IMPROVEMENT.value)),
                category=SuggestionCategory(suggestion_data.get("category", SuggestionCategory.COMPLETENESS.value)) if suggestion_data.get("category") else None,
                priority=SuggestionPriority(suggestion_data.get("priority", SuggestionPriority.MEDIUM.value)),
                user_id=user_id,
                session_id=session_id,
                action_items=suggestion_data.get("action_items", []),
                expected_benefit=suggestion_data.get("expected_benefit", ""),
                estimated_effort=suggestion_data.get("estimated_effort", ""),
                suggestion_metadata=suggestion_data.get("metadata", {})
            )
            
            self.db.add(suggestion)
            await self.db.commit()
            await self.db.refresh(suggestion)
            
            self.logger.info(f"Saved suggestion {suggestion.id} for user {user_id}")
            return suggestion
            
        except Exception as e:
            self.logger.error(f"Error saving suggestion: {str(e)}", exc_info=True)
            await self.db.rollback()
            return None
    
    async def get_user_suggestions(self, user_id: int, status: Optional[str] = None, 
                                 limit: int = 20, offset: int = 0) -> List[AISuggestion]:
        """
        获取用户的建议列表
        
        Args:
            user_id: 用户ID
            status: 建议状态过滤
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            List[AISuggestion]: 建议列表
        """
        try:
            query = select(AISuggestion).where(AISuggestion.user_id == user_id)
            
            if status:
                query = query.where(AISuggestion.status == SuggestionStatus(status))
            
            query = query.order_by(AISuggestion.created_at.desc()).limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            suggestions = result.scalars().all()
            
            return list(suggestions)
            
        except Exception as e:
            self.logger.error(f"Error getting user suggestions: {str(e)}")
            return []
    
    async def update_suggestion_status(self, suggestion_id: int, status: str, 
                                     user_feedback: Optional[str] = None) -> bool:
        """
        更新建议状态
        
        Args:
            suggestion_id: 建议ID
            status: 新状态
            user_feedback: 用户反馈
            
        Returns:
            bool: 是否更新成功
        """
        try:
            query = select(AISuggestion).where(AISuggestion.id == suggestion_id)
            result = await self.db.execute(query)
            suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                return False
            
            suggestion.status = SuggestionStatus(status)
            if user_feedback:
                suggestion.user_feedback = user_feedback
            
            if status == SuggestionStatus.IMPLEMENTED.value:
                suggestion.implemented_at = datetime.utcnow()
            
            await self.db.commit()
            
            self.logger.info(f"Updated suggestion {suggestion_id} status to {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating suggestion status: {str(e)}")
            await self.db.rollback()
            return False