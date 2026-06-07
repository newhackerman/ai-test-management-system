"""
需求优化建议服务

提供智能化的需求优化建议功能，包括：
1. 需求改进建议生成 - 基于质量分析结果提供具体改进建议
2. 需求冲突检测和解决方案 - 识别需求间冲突并提供解决方案
3. 需求依赖关系智能识别 - 自动识别需求间的依赖关系
4. 需求重构建议 - 提供需求结构优化建议
5. 最佳实践推荐 - 基于行业标准推荐最佳实践

技术特性：
- 基于OpenAI GPT模型的智能分析
- 结合需求工程最佳实践
- 支持多维度优化建议
- 提供具体可行的改进方案
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..services.openai_requirement_analysis_service import (
    OpenAIRequirementAnalysisService, 
    RequirementQualityAnalysis,
    RequirementConflictAnalysis,
    RequirementOptimizationSuggestion,
    get_openai_requirement_analysis_service
)
from ..services.ai_operation_log_service import get_ai_operation_log_service
from ..models.ai_operation_log import AIOperationType, AIOperationResult

logger = logging.getLogger(__name__)
settings = get_settings()


class OptimizationCategory(Enum):
    """优化建议类别"""
    STRUCTURE = "structure"        # 结构优化
    CONTENT = "content"           # 内容优化
    CLARITY = "clarity"           # 清晰度优化
    TESTABILITY = "testability"   # 可测试性优化
    IMPLEMENTATION = "implementation"  # 实现优化
    PERFORMANCE = "performance"   # 性能优化
    SECURITY = "security"         # 安全性优化
    USABILITY = "usability"       # 可用性优化


class ConflictType(Enum):
    """冲突类型"""
    FUNCTIONAL = "functional"     # 功能冲突
    DATA = "data"                # 数据冲突
    INTERFACE = "interface"      # 接口冲突
    PERFORMANCE = "performance"  # 性能冲突
    SECURITY = "security"        # 安全冲突
    BUSINESS_RULE = "business_rule"  # 业务规则冲突


class DependencyType(Enum):
    """依赖关系类型"""
    PREREQUISITE = "prerequisite"  # 前置依赖
    BLOCKING = "blocking"         # 阻塞依赖
    RELATED = "related"          # 相关依赖
    ALTERNATIVE = "alternative"   # 替代关系
    ENHANCEMENT = "enhancement"   # 增强关系


@dataclass
class RequirementImprovement:
    """需求改进建议"""
    category: OptimizationCategory
    priority: str  # high, medium, low
    title: str
    description: str
    current_issue: str
    proposed_solution: str
    example_before: Optional[str] = None
    example_after: Optional[str] = None
    expected_benefit: str = ""
    implementation_effort: str = "low"  # low, medium, high
    impact_areas: List[str] = field(default_factory=list)


@dataclass
class ConflictResolution:
    """冲突解决方案"""
    conflict_type: ConflictType
    conflicting_requirements: List[str]
    conflict_description: str
    severity: str  # low, medium, high, critical
    resolution_options: List[Dict[str, Any]]
    recommended_solution: str
    implementation_steps: List[str]
    impact_assessment: str


@dataclass
class DependencyRelationship:
    """依赖关系"""
    source_requirement: str
    target_requirement: str
    dependency_type: DependencyType
    description: str
    strength: float  # 0-1, 依赖强度
    bidirectional: bool = False
    conditions: List[str] = field(default_factory=list)


@dataclass
class OptimizationReport:
    """优化报告"""
    requirement_id: Optional[str] = None
    overall_quality_score: float = 0.0
    improvement_potential: float = 0.0  # 改进潜力 0-1
    
    # 改进建议
    improvements: List[RequirementImprovement] = field(default_factory=list)
    
    # 冲突解决
    conflicts: List[ConflictResolution] = field(default_factory=list)
    
    # 依赖关系
    dependencies: List[DependencyRelationship] = field(default_factory=list)
    
    # 最佳实践建议
    best_practices: List[str] = field(default_factory=list)
    
    # 重构建议
    refactoring_suggestions: List[str] = field(default_factory=list)
    
    # 元数据
    generated_at: datetime = field(default_factory=datetime.utcnow)
    analysis_time: float = 0.0
    confidence_score: float = 0.0


class RequirementOptimizationService:
    """
    需求优化建议服务
    
    提供基于AI的智能需求优化建议，包括改进建议、冲突解决、
    依赖识别等功能。
    """
    
    def __init__(self, db: AsyncSession = None):
        """
        初始化需求优化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
        
        # OpenAI需求分析服务
        self.openai_service: Optional[OpenAIRequirementAnalysisService] = None
        
        # 操作日志服务
        self.log_service = None
        
        # 服务状态
        self.is_initialized = False
        self.service_version = "1.0.0"
        
        # 性能指标
        self.metrics = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "failed_optimizations": 0,
            "avg_optimization_time": 0.0,
            "improvement_suggestions_generated": 0,
            "conflicts_resolved": 0,
            "dependencies_identified": 0
        }
    
    async def initialize(self):
        """初始化服务"""
        try:
            self.logger.info("Initializing Requirement Optimization Service...")
            
            # 初始化OpenAI需求分析服务
            self.openai_service = await get_openai_requirement_analysis_service(self.db)
            
            # 初始化操作日志服务
            if self.db:
                try:
                    self.log_service = await get_ai_operation_log_service(self.db)
                    self.logger.info("AI操作日志服务已初始化")
                except Exception as e:
                    self.logger.warning(f"AI操作日志服务初始化失败: {e}")
            
            self.is_initialized = True
            self.logger.info("Requirement Optimization Service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Requirement Optimization Service: {str(e)}")
            raise
    
    async def generate_comprehensive_optimization(
        self,
        title: str,
        description: str,
        acceptance_criteria: Optional[str] = None,
        requirement_type: Optional[str] = None,
        existing_requirements: Optional[List[Dict[str, Any]]] = None,
        project_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> OptimizationReport:
        """
        生成综合优化报告
        
        Args:
            title: 需求标题
            description: 需求描述
            acceptance_criteria: 验收标准
            requirement_type: 需求类型
            existing_requirements: 已存在的需求列表
            project_context: 项目上下文
            user_id: 用户ID
            
        Returns:
            OptimizationReport: 综合优化报告
        """
        start_time = time.time()
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            self.logger.info(f"Generating comprehensive optimization for requirement: {title[:50]}...")
            
            # 1. 执行质量分析
            quality_analysis = await self.openai_service.analyze_requirement_quality(
                title=title,
                description=description,
                acceptance_criteria=acceptance_criteria,
                requirement_type=requirement_type,
                user_id=user_id
            )
            
            # 2. 生成改进建议
            improvements = await self._generate_improvement_suggestions(
                title, description, acceptance_criteria, quality_analysis, user_id
            )
            
            # 3. 检测和解决冲突
            conflicts = []
            if existing_requirements:
                conflict_analysis = await self.openai_service.detect_requirement_conflicts(
                    current_requirement={
                        "title": title,
                        "description": description,
                        "type": requirement_type
                    },
                    existing_requirements=existing_requirements,
                    user_id=user_id
                )
                
                if conflict_analysis.has_conflicts:
                    conflicts = await self._generate_conflict_resolutions(
                        conflict_analysis, user_id
                    )
            
            # 4. 识别依赖关系
            dependencies = []
            if existing_requirements:
                dependencies = await self._identify_dependencies(
                    title, description, existing_requirements, user_id
                )
            
            # 5. 生成最佳实践建议
            best_practices = await self._generate_best_practices(
                title, description, requirement_type, quality_analysis, user_id
            )
            
            # 6. 生成重构建议
            refactoring_suggestions = await self._generate_refactoring_suggestions(
                title, description, quality_analysis, user_id
            )
            
            # 计算改进潜力
            improvement_potential = self._calculate_improvement_potential(
                quality_analysis, improvements, conflicts
            )
            
            analysis_time = time.time() - start_time
            
            # 构建优化报告
            report = OptimizationReport(
                requirement_id=f"REQ-{int(time.time())}",
                overall_quality_score=quality_analysis.overall_score,
                improvement_potential=improvement_potential,
                improvements=improvements,
                conflicts=conflicts,
                dependencies=dependencies,
                best_practices=best_practices,
                refactoring_suggestions=refactoring_suggestions,
                analysis_time=analysis_time,
                confidence_score=quality_analysis.confidence_level
            )
            
            # 更新指标
            self.metrics["total_optimizations"] += 1
            self.metrics["successful_optimizations"] += 1
            self.metrics["improvement_suggestions_generated"] += len(improvements)
            self.metrics["conflicts_resolved"] += len(conflicts)
            self.metrics["dependencies_identified"] += len(dependencies)
            self._update_avg_optimization_time(analysis_time)
            
            # 记录操作日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model="gpt-4",
                    tokens_used=0,  # 综合多次调用，这里简化处理
                    processing_time=analysis_time,
                    result=AIOperationResult.SUCCESS,
                    business_context={
                        "operation_type": "comprehensive_requirement_optimization",
                        "requirement_title": title[:100],
                        "improvements_count": len(improvements),
                        "conflicts_count": len(conflicts),
                        "dependencies_count": len(dependencies),
                        "improvement_potential": improvement_potential
                    }
                )
            
            self.logger.info(f"Comprehensive optimization completed in {analysis_time:.2f}s, "
                           f"generated {len(improvements)} improvements, "
                           f"resolved {len(conflicts)} conflicts, "
                           f"identified {len(dependencies)} dependencies")
            
            return report
            
        except Exception as e:
            analysis_time = time.time() - start_time
            self.logger.error(f"Error generating comprehensive optimization: {str(e)}")
            
            # 更新失败指标
            self.metrics["total_optimizations"] += 1
            self.metrics["failed_optimizations"] += 1
            
            # 记录错误日志
            if self.log_service:
                await self.log_service.log_ai_model_call(
                    user_id=user_id,
                    ai_provider="openai",
                    ai_model="gpt-4",
                    tokens_used=0,
                    processing_time=analysis_time,
                    result=AIOperationResult.FAILURE,
                    error_details=str(e),
                    business_context={
                        "operation_type": "comprehensive_requirement_optimization",
                        "requirement_title": title[:100] if title else "unknown"
                    }
                )
            
            # 返回空报告
            return OptimizationReport(
                analysis_time=analysis_time,
                confidence_score=0.0
            )
    
    async def _generate_improvement_suggestions(
        self,
        title: str,
        description: str,
        acceptance_criteria: Optional[str],
        quality_analysis: RequirementQualityAnalysis,
        user_id: Optional[int]
    ) -> List[RequirementImprovement]:
        """生成改进建议"""
        try:
            # 基于质量分析结果生成改进建议
            improvements = []
            
            # 完整性改进
            if quality_analysis.completeness_score < 7.0:
                improvements.append(RequirementImprovement(
                    category=OptimizationCategory.CONTENT,
                    priority="high",
                    title="补充需求完整性",
                    description="需求描述缺少关键信息，需要补充完整",
                    current_issue=f"完整性评分仅为{quality_analysis.completeness_score:.1f}分",
                    proposed_solution="补充缺失的功能描述、边界条件、异常处理等信息",
                    expected_benefit="提高需求理解准确性，减少开发过程中的疑问",
                    implementation_effort="medium",
                    impact_areas=["开发效率", "质量保证", "沟通成本"]
                ))
            
            # 清晰性改进
            if quality_analysis.clarity_score < 7.0:
                improvements.append(RequirementImprovement(
                    category=OptimizationCategory.CLARITY,
                    priority="high",
                    title="改进需求表述清晰度",
                    description="需求表述存在歧义或不够清晰",
                    current_issue=f"清晰度评分仅为{quality_analysis.clarity_score:.1f}分",
                    proposed_solution="使用更精确的术语，避免模糊表达，添加具体示例",
                    expected_benefit="减少理解偏差，提高实现准确性",
                    implementation_effort="low",
                    impact_areas=["理解准确性", "开发效率"]
                ))
            
            # 可测试性改进
            if quality_analysis.testability_score < 7.0:
                improvements.append(RequirementImprovement(
                    category=OptimizationCategory.TESTABILITY,
                    priority="medium",
                    title="增强需求可测试性",
                    description="验收标准不够明确或缺少测试场景",
                    current_issue=f"可测试性评分仅为{quality_analysis.testability_score:.1f}分",
                    proposed_solution="使用GIVEN-WHEN-THEN格式编写验收标准，补充边界条件测试",
                    expected_benefit="提高测试覆盖率，确保需求正确实现",
                    implementation_effort="medium",
                    impact_areas=["测试质量", "需求验证"]
                ))
            
            # 可行性改进
            if quality_analysis.feasibility_score < 7.0:
                improvements.append(RequirementImprovement(
                    category=OptimizationCategory.IMPLEMENTATION,
                    priority="high",
                    title="优化需求可行性",
                    description="需求实现存在技术或资源约束",
                    current_issue=f"可行性评分仅为{quality_analysis.feasibility_score:.1f}分",
                    proposed_solution="分析技术约束，提供替代方案，合理分解复杂需求",
                    expected_benefit="降低实现风险，提高成功率",
                    implementation_effort="high",
                    impact_areas=["技术风险", "项目成功率"]
                ))
            
            # 基于具体建议生成改进
            for suggestion in quality_analysis.improvement_suggestions:
                if "性能" in suggestion:
                    improvements.append(RequirementImprovement(
                        category=OptimizationCategory.PERFORMANCE,
                        priority="medium",
                        title="明确性能要求",
                        description=suggestion,
                        current_issue="缺少具体的性能指标",
                        proposed_solution="定义响应时间、吞吐量、并发用户数等具体指标",
                        expected_benefit="确保系统性能满足用户期望",
                        implementation_effort="low",
                        impact_areas=["用户体验", "系统性能"]
                    ))
                elif "安全" in suggestion:
                    improvements.append(RequirementImprovement(
                        category=OptimizationCategory.SECURITY,
                        priority="high",
                        title="加强安全要求",
                        description=suggestion,
                        current_issue="安全要求不明确或缺失",
                        proposed_solution="明确认证、授权、数据加密等安全要求",
                        expected_benefit="提高系统安全性，降低安全风险",
                        implementation_effort="medium",
                        impact_areas=["系统安全", "合规性"]
                    ))
            
            return improvements
            
        except Exception as e:
            self.logger.error(f"Error generating improvement suggestions: {str(e)}")
            return []
    
    async def _generate_conflict_resolutions(
        self,
        conflict_analysis: RequirementConflictAnalysis,
        user_id: Optional[int]
    ) -> List[ConflictResolution]:
        """生成冲突解决方案"""
        try:
            resolutions = []
            
            for i, conflict_req in enumerate(conflict_analysis.conflicting_requirements):
                # 根据冲突类型生成解决方案
                conflict_type_map = {
                    "功能冲突": ConflictType.FUNCTIONAL,
                    "数据冲突": ConflictType.DATA,
                    "接口冲突": ConflictType.INTERFACE,
                    "性能冲突": ConflictType.PERFORMANCE,
                    "安全冲突": ConflictType.SECURITY,
                    "业务规则冲突": ConflictType.BUSINESS_RULE
                }
                
                # 确定冲突类型
                conflict_type = ConflictType.FUNCTIONAL
                for type_name, type_enum in conflict_type_map.items():
                    if any(type_name in ct for ct in conflict_analysis.conflict_types):
                        conflict_type = type_enum
                        break
                
                # 生成解决方案选项
                resolution_options = [
                    {
                        "option": "合并需求",
                        "description": "将冲突的需求合并为一个统一的需求",
                        "pros": ["减少重复", "统一标准"],
                        "cons": ["可能增加复杂度"],
                        "effort": "medium"
                    },
                    {
                        "option": "分离需求",
                        "description": "将冲突的部分分离到不同的需求中",
                        "pros": ["清晰分工", "降低耦合"],
                        "cons": ["可能增加集成复杂度"],
                        "effort": "low"
                    },
                    {
                        "option": "优先级排序",
                        "description": "根据业务价值确定需求优先级",
                        "pros": ["明确重点", "资源聚焦"],
                        "cons": ["可能延迟部分功能"],
                        "effort": "low"
                    }
                ]
                
                resolution = ConflictResolution(
                    conflict_type=conflict_type,
                    conflicting_requirements=[conflict_req.get("requirement_id", f"REQ-{i}")],
                    conflict_description=conflict_req.get("conflict_description", "需求冲突"),
                    severity=conflict_analysis.severity_level,
                    resolution_options=resolution_options,
                    recommended_solution="合并需求",
                    implementation_steps=[
                        "分析冲突的具体原因",
                        "与干系人讨论解决方案",
                        "更新需求文档",
                        "验证解决方案的有效性"
                    ],
                    impact_assessment="中等影响，需要重新设计部分功能"
                )
                
                resolutions.append(resolution)
            
            return resolutions
            
        except Exception as e:
            self.logger.error(f"Error generating conflict resolutions: {str(e)}")
            return []
    
    async def _identify_dependencies(
        self,
        title: str,
        description: str,
        existing_requirements: List[Dict[str, Any]],
        user_id: Optional[int]
    ) -> List[DependencyRelationship]:
        """识别依赖关系"""
        try:
            dependencies = []
            
            # 简化的依赖识别逻辑（实际应用中可以使用更复杂的NLP分析）
            keywords_map = {
                "登录": ["用户管理", "认证", "权限"],
                "支付": ["订单", "用户", "商品"],
                "订单": ["用户", "商品", "库存"],
                "报表": ["数据", "统计", "权限"],
                "通知": ["用户", "消息", "模板"]
            }
            
            current_keywords = []
            for keyword in keywords_map.keys():
                if keyword in title or keyword in description:
                    current_keywords.extend(keywords_map[keyword])
            
            # 在已有需求中查找相关依赖
            for req in existing_requirements:
                req_title = req.get("title", "")
                req_desc = req.get("description", "")
                
                # 检查是否存在依赖关系
                dependency_strength = 0.0
                dependency_type = DependencyType.RELATED
                
                for keyword in current_keywords:
                    if keyword in req_title or keyword in req_desc:
                        dependency_strength += 0.3
                        
                        # 根据关键词确定依赖类型
                        if keyword in ["认证", "权限", "用户管理"]:
                            dependency_type = DependencyType.PREREQUISITE
                        elif keyword in ["数据", "基础"]:
                            dependency_type = DependencyType.PREREQUISITE
                        elif keyword in ["扩展", "增强"]:
                            dependency_type = DependencyType.ENHANCEMENT
                
                if dependency_strength > 0.3:
                    dependency = DependencyRelationship(
                        source_requirement=title,
                        target_requirement=req_title,
                        dependency_type=dependency_type,
                        description=f"基于功能关联识别的依赖关系",
                        strength=min(dependency_strength, 1.0),
                        conditions=[f"需要{req_title}提供基础功能支持"]
                    )
                    dependencies.append(dependency)
            
            return dependencies
            
        except Exception as e:
            self.logger.error(f"Error identifying dependencies: {str(e)}")
            return []
    
    async def _generate_best_practices(
        self,
        title: str,
        description: str,
        requirement_type: Optional[str],
        quality_analysis: RequirementQualityAnalysis,
        user_id: Optional[int]
    ) -> List[str]:
        """生成最佳实践建议"""
        try:
            best_practices = []
            
            # 通用最佳实践
            best_practices.extend([
                "使用SMART原则编写需求（具体、可测量、可实现、相关、有时限）",
                "采用用户故事格式：作为[角色]，我希望[功能]，以便[价值]",
                "为每个需求定义明确的验收标准",
                "使用统一的术语和概念定义"
            ])
            
            # 基于需求类型的最佳实践
            if requirement_type == "functional":
                best_practices.extend([
                    "详细描述输入、处理、输出的完整流程",
                    "考虑正常流程和异常流程的处理",
                    "明确用户角色和权限要求"
                ])
            elif requirement_type == "non_functional":
                best_practices.extend([
                    "使用具体的数值指标定义性能要求",
                    "考虑可扩展性和可维护性要求",
                    "明确安全性和合规性标准"
                ])
            
            # 基于质量分析的建议
            if quality_analysis.overall_score < 6.0:
                best_practices.append("建议进行需求评审，邀请多方干系人参与")
            
            if quality_analysis.complexity_estimate.value == "very_complex":
                best_practices.append("考虑将复杂需求分解为多个简单需求")
            
            return best_practices
            
        except Exception as e:
            self.logger.error(f"Error generating best practices: {str(e)}")
            return []
    
    async def _generate_refactoring_suggestions(
        self,
        title: str,
        description: str,
        quality_analysis: RequirementQualityAnalysis,
        user_id: Optional[int]
    ) -> List[str]:
        """生成重构建议"""
        try:
            suggestions = []
            
            # 基于复杂度的重构建议
            if quality_analysis.complexity_estimate.value in ["complex", "very_complex"]:
                suggestions.extend([
                    "考虑将大需求拆分为多个小需求，便于管理和实现",
                    "识别可复用的组件，避免重复开发",
                    "建立需求层次结构，明确父子关系"
                ])
            
            # 基于质量评分的重构建议
            if quality_analysis.overall_score < 6.0:
                suggestions.extend([
                    "重新组织需求结构，提高逻辑清晰度",
                    "统一需求描述格式和风格",
                    "建立需求模板，确保一致性"
                ])
            
            # 基于具体问题的建议
            if quality_analysis.testability_score < 6.0:
                suggestions.append("重构验收标准，使其更具可测试性")
            
            if quality_analysis.traceability_score < 6.0:
                suggestions.append("建立需求追溯矩阵，明确需求来源和去向")
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Error generating refactoring suggestions: {str(e)}")
            return []
    
    def _calculate_improvement_potential(
        self,
        quality_analysis: RequirementQualityAnalysis,
        improvements: List[RequirementImprovement],
        conflicts: List[ConflictResolution]
    ) -> float:
        """计算改进潜力"""
        try:
            # 基于质量评分计算基础改进潜力
            base_potential = (10.0 - quality_analysis.overall_score) / 10.0
            
            # 基于改进建议数量调整
            improvement_factor = min(len(improvements) * 0.1, 0.5)
            
            # 基于冲突数量调整
            conflict_factor = min(len(conflicts) * 0.15, 0.3)
            
            # 综合计算改进潜力
            total_potential = base_potential + improvement_factor + conflict_factor
            
            return min(total_potential, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating improvement potential: {str(e)}")
            return 0.0
    
    def _update_avg_optimization_time(self, optimization_time: float):
        """更新平均优化时间"""
        if self.metrics["successful_optimizations"] == 1:
            self.metrics["avg_optimization_time"] = optimization_time
        else:
            # 计算移动平均
            total_time = self.metrics["avg_optimization_time"] * (self.metrics["successful_optimizations"] - 1)
            self.metrics["avg_optimization_time"] = (total_time + optimization_time) / self.metrics["successful_optimizations"]
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """获取服务指标"""
        return {
            **self.metrics,
            "is_initialized": self.is_initialized,
            "service_version": self.service_version,
            "openai_service_available": self.openai_service is not None
        }
    
    async def shutdown(self):
        """关闭服务"""
        if self.openai_service:
            await self.openai_service.shutdown()
        self.logger.info("Requirement Optimization Service shutdown completed")


# 全局服务实例
_requirement_optimization_service: Optional[RequirementOptimizationService] = None


async def get_requirement_optimization_service(db: AsyncSession = None) -> RequirementOptimizationService:
    """
    获取需求优化服务实例
    
    Args:
        db: 数据库会话
        
    Returns:
        RequirementOptimizationService: 服务实例
    """
    global _requirement_optimization_service
    
    if _requirement_optimization_service is None:
        _requirement_optimization_service = RequirementOptimizationService(db)
        await _requirement_optimization_service.initialize()
    
    return _requirement_optimization_service