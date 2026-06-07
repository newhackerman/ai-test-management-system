"""
增强的多维度影响分析服务

本模块提供更全面的需求变更影响分析，包括：
- 技术维度影响分析
- 业务维度影响分析
- 时间维度影响分析
- 成本维度影响分析
- 风险维度影响分析
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass

from ..models.requirement import (
    Requirement, RequirementDependency, ChangeType, RequirementStatus,
    Priority, BusinessValue, Complexity
)
from ..repositories.requirement_repository import RequirementRepository
from ..repositories.requirement_relationship_repository import RequirementRelationshipRepository
from ..schemas.requirement_change import ImpactAnalysisRequest, ImpactItem


@dataclass
class MultiDimensionalImpact:
    """多维度影响分析结果"""
    technical_impact: Dict[str, Any]
    business_impact: Dict[str, Any]
    timeline_impact: Dict[str, Any]
    cost_impact: Dict[str, Any]
    risk_impact: Dict[str, Any]
    overall_score: float
    recommendations: List[str]


@dataclass
class TechnicalImpact:
    """技术影响分析"""
    architecture_changes: List[str]
    interface_changes: List[str]
    data_model_changes: List[str]
    integration_impacts: List[str]
    complexity_increase: float
    technical_debt_impact: float


@dataclass
class BusinessImpact:
    """业务影响分析"""
    stakeholder_impacts: List[Dict[str, Any]]
    process_changes: List[str]
    user_experience_impact: str
    business_value_change: float
    market_impact: str


@dataclass
class TimelineImpact:
    """时间线影响分析"""
    development_delay: int  # 天数
    testing_delay: int
    deployment_delay: int
    total_delay: int
    critical_path_impact: bool


@dataclass
class CostImpact:
    """成本影响分析"""
    development_cost: Decimal
    testing_cost: Decimal
    deployment_cost: Decimal
    maintenance_cost: Decimal
    total_cost: Decimal
    cost_benefit_ratio: float


class EnhancedImpactAnalysisService:
    """增强的影响分析服务"""
    
    def __init__(
        self,
        requirement_repo: RequirementRepository,
        relationship_repo: RequirementRelationshipRepository
    ):
        self.requirement_repo = requirement_repo
        self.relationship_repo = relationship_repo
    
    async def perform_multidimensional_analysis(
        self,
        request: ImpactAnalysisRequest
    ) -> MultiDimensionalImpact:
        """执行多维度影响分析"""
        requirement = await self.requirement_repo.get_by_id(request.requirement_id)
        if not requirement:
            raise ValueError(f"需求 {request.requirement_id} 不存在")
        
        # 获取相关需求
        related_requirements = await self._get_related_requirements(requirement)
        
        # 技术维度分析
        technical_impact = await self._analyze_technical_impact(
            requirement, request.change_type, related_requirements
        )
        
        # 业务维度分析
        business_impact = await self._analyze_business_impact(
            requirement, request.change_type, related_requirements
        )
        
        # 时间维度分析
        timeline_impact = await self._analyze_timeline_impact(
            requirement, request.change_type, related_requirements
        )
        
        # 成本维度分析
        cost_impact = await self._analyze_cost_impact(
            requirement, request.change_type, related_requirements
        )
        
        # 风险维度分析
        risk_impact = await self._analyze_risk_impact(
            requirement, request.change_type, related_requirements
        )
        
        # 计算综合评分
        overall_score = self._calculate_overall_score(
            technical_impact, business_impact, timeline_impact, cost_impact, risk_impact
        )
        
        # 生成综合建议
        recommendations = self._generate_comprehensive_recommendations(
            requirement, request.change_type, technical_impact, business_impact,
            timeline_impact, cost_impact, risk_impact, overall_score
        )
        
        return MultiDimensionalImpact(
            technical_impact=technical_impact,
            business_impact=business_impact,
            timeline_impact=timeline_impact,
            cost_impact=cost_impact,
            risk_impact=risk_impact,
            overall_score=overall_score,
            recommendations=recommendations
        )
    
    async def _get_related_requirements(self, requirement: Requirement) -> List[Requirement]:
        """获取相关需求"""
        related = []
        
        # 获取依赖关系
        dependencies = await self.relationship_repo.get_requirement_dependencies(
            requirement.id
        )
        for dep in dependencies:
            if dep.source_requirement:
                related.append(dep.source_requirement)
            if dep.target_requirement:
                related.append(dep.target_requirement)
        
        # 获取同项目需求
        project_requirements = await self.requirement_repo.get_requirements_by_project(
            requirement.project_id, limit=100
        )
        related.extend([req for req in project_requirements if req.id != requirement.id])
        
        return list(set(related))
    
    async def _analyze_technical_impact(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        related_requirements: List[Requirement]
    ) -> Dict[str, Any]:
        """分析技术影响"""
        impact = TechnicalImpact(
            architecture_changes=[],
            interface_changes=[],
            data_model_changes=[],
            integration_impacts=[],
            complexity_increase=0.0,
            technical_debt_impact=0.0
        )
        
        # 分析架构变更
        if change_type in [ChangeType.MODIFICATION, ChangeType.DELETION]:
            if requirement.complexity in [Complexity.COMPLEX, Complexity.VERY_COMPLEX]:
                impact.architecture_changes.append("核心架构组件可能需要重构")
                impact.complexity_increase += 2.0
        
        # 分析接口变更
        interface_dependent_count = len([
            req for req in related_requirements 
            if req.requirement_type.value == "INTERFACE"
        ])
        if interface_dependent_count > 0:
            impact.interface_changes.append(f"可能影响 {interface_dependent_count} 个接口定义")
            impact.complexity_increase += interface_dependent_count * 0.5
        
        # 分析数据模型变更
        if "数据" in requirement.description or "模型" in requirement.description:
            impact.data_model_changes.append("可能需要数据库结构变更")
            impact.complexity_increase += 1.5
        
        # 分析集成影响
        integration_count = len([
            req for req in related_requirements
            if "集成" in req.title or "接口" in req.title
        ])
        if integration_count > 0:
            impact.integration_impacts.append(f"可能影响 {integration_count} 个集成点")
        
        # 计算技术债务影响
        if change_type == ChangeType.MODIFICATION:
            impact.technical_debt_impact = min(requirement.complexity.value * 0.3, 2.0)
        
        return {
            "architecture_changes": impact.architecture_changes,
            "interface_changes": impact.interface_changes,
            "data_model_changes": impact.data_model_changes,
            "integration_impacts": impact.integration_impacts,
            "complexity_increase": impact.complexity_increase,
            "technical_debt_impact": impact.technical_debt_impact,
            "overall_technical_score": min(impact.complexity_increase + impact.technical_debt_impact, 10.0)
        }
    
    async def _analyze_business_impact(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        related_requirements: List[Requirement]
    ) -> Dict[str, Any]:
        """分析业务影响"""
        impact = BusinessImpact(
            stakeholder_impacts=[],
            process_changes=[],
            user_experience_impact="",
            business_value_change=0.0,
            market_impact=""
        )
        
        # 分析干系人影响
        high_value_reqs = [
            req for req in related_requirements
            if req.business_value in [BusinessValue.CORE, BusinessValue.IMPORTANT]
        ]
        if high_value_reqs:
            impact.stakeholder_impacts.append({
                "type": "高价值需求影响",
                "count": len(high_value_reqs),
                "impact_level": "HIGH"
            })
        
        # 分析流程变更
        if change_type == ChangeType.MODIFICATION:
            if requirement.business_value == BusinessValue.CORE:
                impact.process_changes.append("核心业务流程可能需要调整")
                impact.business_value_change = -1.0
        elif change_type == ChangeType.DELETION:
            impact.process_changes.append("相关业务流程需要重新设计")
            impact.business_value_change = -2.0
        
        # 分析用户体验影响
        if "用户" in requirement.title or "界面" in requirement.title:
            if change_type == ChangeType.MODIFICATION:
                impact.user_experience_impact = "用户界面和交互可能发生变化"
            elif change_type == ChangeType.DELETION:
                impact.user_experience_impact = "用户功能将被移除，需要替代方案"
        
        # 分析市场影响
        if requirement.priority in [Priority.CRITICAL, Priority.HIGH]:
            if change_type == ChangeType.DELETION:
                impact.market_impact = "可能影响产品竞争力"
            elif change_type == ChangeType.MODIFICATION:
                impact.market_impact = "可能影响产品发布时间"
        
        return {
            "stakeholder_impacts": impact.stakeholder_impacts,
            "process_changes": impact.process_changes,
            "user_experience_impact": impact.user_experience_impact,
            "business_value_change": impact.business_value_change,
            "market_impact": impact.market_impact,
            "overall_business_score": abs(impact.business_value_change) * 2 + len(impact.process_changes)
        }
    
    async def _analyze_timeline_impact(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        related_requirements: List[Requirement]
    ) -> Dict[str, Any]:
        """分析时间线影响"""
        impact = TimelineImpact(
            development_delay=0,
            testing_delay=0,
            deployment_delay=0,
            total_delay=0,
            critical_path_impact=False
        )
        
        # 基于变更类型估算延期
        base_effort = requirement.estimated_effort or Decimal('1.0')
        
        if change_type == ChangeType.DELETION:
            impact.development_delay = int(base_effort * Decimal('0.3'))
            impact.testing_delay = int(base_effort * Decimal('0.2'))
        elif change_type == ChangeType.MODIFICATION:
            impact.development_delay = int(base_effort * Decimal('0.5'))
            impact.testing_delay = int(base_effort * Decimal('0.3'))
            impact.deployment_delay = int(base_effort * Decimal('0.1'))
        elif change_type == ChangeType.ADDITION:
            impact.development_delay = int(base_effort * Decimal('0.8'))
            impact.testing_delay = int(base_effort * Decimal('0.4'))
            impact.deployment_delay = int(base_effort * Decimal('0.2'))
        
        # 检查关键路径影响
        critical_reqs = [
            req for req in related_requirements
            if req.priority in [Priority.CRITICAL, Priority.HIGH]
        ]
        if critical_reqs or requirement.priority in [Priority.CRITICAL, Priority.HIGH]:
            impact.critical_path_impact = True
            impact.development_delay = int(impact.development_delay * 1.5)
            impact.testing_delay = int(impact.testing_delay * 1.5)
        
        impact.total_delay = impact.development_delay + impact.testing_delay + impact.deployment_delay
        
        return {
            "development_delay": impact.development_delay,
            "testing_delay": impact.testing_delay,
            "deployment_delay": impact.deployment_delay,
            "total_delay": impact.total_delay,
            "critical_path_impact": impact.critical_path_impact,
            "overall_timeline_score": min(impact.total_delay / 5.0, 10.0)
        }
    
    async def _analyze_cost_impact(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        related_requirements: List[Requirement]
    ) -> Dict[str, Any]:
        """分析成本影响"""
        impact = CostImpact(
            development_cost=Decimal('0'),
            testing_cost=Decimal('0'),
            deployment_cost=Decimal('0'),
            maintenance_cost=Decimal('0'),
            total_cost=Decimal('0'),
            cost_benefit_ratio=0.0
        )
        
        # 基础成本估算（假设每人天1000元）
        daily_rate = Decimal('1000')
        base_effort = requirement.estimated_effort or Decimal('1.0')
        
        if change_type == ChangeType.DELETION:
            impact.development_cost = base_effort * daily_rate * Decimal('0.3')
            impact.testing_cost = base_effort * daily_rate * Decimal('0.2')
        elif change_type == ChangeType.MODIFICATION:
            impact.development_cost = base_effort * daily_rate * Decimal('0.6')
            impact.testing_cost = base_effort * daily_rate * Decimal('0.4')
            impact.deployment_cost = base_effort * daily_rate * Decimal('0.1')
        elif change_type == ChangeType.ADDITION:
            impact.development_cost = base_effort * daily_rate * Decimal('1.0')
            impact.testing_cost = base_effort * daily_rate * Decimal('0.5')
            impact.deployment_cost = base_effort * daily_rate * Decimal('0.2')
        
        # 维护成本（年度）
        if change_type in [ChangeType.ADDITION, ChangeType.MODIFICATION]:
            impact.maintenance_cost = impact.development_cost * Decimal('0.2')
        
        # 计算相关需求的额外成本
        related_cost = Decimal('0')
        for req in related_requirements[:5]:  # 限制前5个最相关的
            if req.estimated_effort:
                related_cost += req.estimated_effort * daily_rate * Decimal('0.1')
        
        impact.total_cost = (impact.development_cost + impact.testing_cost + 
                           impact.deployment_cost + related_cost)
        
        # 成本效益比
        business_value_score = {
            BusinessValue.CORE: 5.0,
            BusinessValue.IMPORTANT: 3.0,
            BusinessValue.NORMAL: 2.0,
            BusinessValue.OPTIONAL: 1.0
        }.get(requirement.business_value, 2.0)
        
        if impact.total_cost > 0:
            impact.cost_benefit_ratio = float(business_value_score / (float(impact.total_cost) / 1000))
        
        return {
            "development_cost": float(impact.development_cost),
            "testing_cost": float(impact.testing_cost),
            "deployment_cost": float(impact.deployment_cost),
            "maintenance_cost": float(impact.maintenance_cost),
            "total_cost": float(impact.total_cost),
            "cost_benefit_ratio": impact.cost_benefit_ratio,
            "overall_cost_score": min(float(impact.total_cost) / 1000, 10.0)
        }
    
    async def _analyze_risk_impact(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        related_requirements: List[Requirement]
    ) -> Dict[str, Any]:
        """分析风险影响"""
        risks = []
        risk_score = 0.0
        
        # 技术风险
        if requirement.complexity in [Complexity.COMPLEX, Complexity.VERY_COMPLEX]:
            risks.append({
                "type": "技术风险",
                "description": "高复杂度需求变更可能引入技术风险",
                "probability": 0.7,
                "impact": 8.0
            })
            risk_score += 5.6
        
        # 依赖风险
        dependency_count = len(related_requirements)
        if dependency_count > 5:
            risks.append({
                "type": "依赖风险",
                "description": f"影响 {dependency_count} 个相关需求，依赖风险较高",
                "probability": 0.6,
                "impact": 6.0
            })
            risk_score += 3.6
        
        # 时间风险
        if requirement.status in [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.TESTING]:
            risks.append({
                "type": "时间风险",
                "description": "需求正在开发/测试中，变更可能导致延期",
                "probability": 0.8,
                "impact": 7.0
            })
            risk_score += 5.6
        
        # 业务风险
        if requirement.business_value == BusinessValue.CORE:
            risks.append({
                "type": "业务风险",
                "description": "核心业务需求变更可能影响业务连续性",
                "probability": 0.5,
                "impact": 9.0
            })
            risk_score += 4.5
        
        # 质量风险
        if change_type == ChangeType.MODIFICATION:
            risks.append({
                "type": "质量风险",
                "description": "需求修改可能引入新的缺陷",
                "probability": 0.4,
                "impact": 5.0
            })
            risk_score += 2.0
        
        return {
            "identified_risks": risks,
            "risk_count": len(risks),
            "overall_risk_score": min(risk_score, 10.0),
            "risk_level": "高" if risk_score >= 7 else "中" if risk_score >= 4 else "低"
        }
    
    def _calculate_overall_score(
        self,
        technical_impact: Dict[str, Any],
        business_impact: Dict[str, Any],
        timeline_impact: Dict[str, Any],
        cost_impact: Dict[str, Any],
        risk_impact: Dict[str, Any]
    ) -> float:
        """计算综合评分"""
        # 权重分配
        weights = {
            "technical": 0.25,
            "business": 0.25,
            "timeline": 0.20,
            "cost": 0.15,
            "risk": 0.15
        }
        
        score = (
            technical_impact.get("overall_technical_score", 0) * weights["technical"] +
            business_impact.get("overall_business_score", 0) * weights["business"] +
            timeline_impact.get("overall_timeline_score", 0) * weights["timeline"] +
            cost_impact.get("overall_cost_score", 0) * weights["cost"] +
            risk_impact.get("overall_risk_score", 0) * weights["risk"]
        )
        
        return min(score, 10.0)
    
    def _generate_comprehensive_recommendations(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        technical_impact: Dict[str, Any],
        business_impact: Dict[str, Any],
        timeline_impact: Dict[str, Any],
        cost_impact: Dict[str, Any],
        risk_impact: Dict[str, Any],
        overall_score: float
    ) -> List[str]:
        """生成综合建议"""
        recommendations = []
        
        # 基于综合评分的建议
        if overall_score >= 8.0:
            recommendations.append("🚨 高影响变更，强烈建议召开变更委员会会议")
            recommendations.append("📋 建议制定详细的变更实施计划和回滚方案")
        elif overall_score >= 5.0:
            recommendations.append("⚠️ 中等影响变更，建议进行充分的影响评估")
        
        # 技术建议
        if technical_impact.get("overall_technical_score", 0) >= 6.0:
            recommendations.append("🔧 建议进行技术架构评审")
            if technical_impact.get("architecture_changes"):
                recommendations.append("🏗️ 需要架构师参与变更评估")
        
        # 业务建议
        if business_impact.get("overall_business_score", 0) >= 5.0:
            recommendations.append("💼 建议通知所有相关业务干系人")
            if business_impact.get("user_experience_impact"):
                recommendations.append("👥 建议进行用户体验评估")
        
        # 时间建议
        if timeline_impact.get("critical_path_impact"):
            recommendations.append("⏰ 变更影响关键路径，需要重新评估项目时间线")
        
        if timeline_impact.get("total_delay", 0) > 10:
            recommendations.append("📅 预计延期超过10天，建议调整项目计划")
        
        # 成本建议
        if cost_impact.get("total_cost", 0) > 50000:
            recommendations.append("💰 变更成本较高，建议进行成本效益分析")
        
        if cost_impact.get("cost_benefit_ratio", 0) < 1.0:
            recommendations.append("📊 成本效益比较低，建议重新评估变更必要性")
        
        # 风险建议
        if risk_impact.get("overall_risk_score", 0) >= 7.0:
            recommendations.append("⚠️ 高风险变更，建议制定风险缓解措施")
        
        for risk in risk_impact.get("identified_risks", []):
            if risk["probability"] * risk["impact"] >= 5.0:
                recommendations.append(f"🎯 重点关注{risk['type']}：{risk['description']}")
        
        # 变更类型特定建议
        if change_type == ChangeType.DELETION:
            recommendations.append("🗑️ 删除需求前请确认无其他依赖")
        elif change_type == ChangeType.MODIFICATION:
            recommendations.append("✏️ 建议保留原需求版本以便回滚")
        
        return recommendations