"""
变更风险评估服务

本模块提供需求变更的风险评估功能，包括：
- 风险识别
- 风险量化
- 风险缓解建议
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from models.requirement import (
    Requirement, ChangeType, RequirementStatus, Priority, 
    BusinessValue, Complexity
)
from repositories.requirement_repository import RequirementRepository


class RiskLevel(Enum):
    """风险级别"""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class RiskCategory(Enum):
    """风险类别"""
    TECHNICAL = "TECHNICAL"
    BUSINESS = "BUSINESS"
    SCHEDULE = "SCHEDULE"
    COST = "COST"
    QUALITY = "QUALITY"
    RESOURCE = "RESOURCE"
    COMPLIANCE = "COMPLIANCE"


@dataclass
class RiskItem:
    """风险项"""
    id: str
    category: RiskCategory
    title: str
    description: str
    probability: float  # 0-1
    impact: float  # 1-10
    risk_score: float  # probability * impact
    level: RiskLevel
    mitigation_strategies: List[str]
    contingency_plans: List[str]


@dataclass
class RiskAssessmentResult:
    """风险评估结果"""
    requirement_id: int
    change_type: ChangeType
    identified_risks: List[RiskItem]
    overall_risk_score: float
    overall_risk_level: RiskLevel
    risk_summary: Dict[str, Any]
    recommendations: List[str]
    assessment_date: datetime


class ChangeRiskAssessmentService:
    """变更风险评估服务"""
    
    def __init__(self, requirement_repo: RequirementRepository):
        self.requirement_repo = requirement_repo
        self.risk_templates = self._initialize_risk_templates()
    
    async def assess_change_risks(
        self,
        requirement_id: int,
        change_type: ChangeType,
        change_description: str = "",
        context_data: Optional[Dict[str, Any]] = None
    ) -> RiskAssessmentResult:
        """评估变更风险"""
        requirement = await self.requirement_repo.get_by_id(requirement_id)
        if not requirement:
            raise ValueError(f"需求 {requirement_id} 不存在")
        
        context_data = context_data or {}
        
        # 识别风险
        identified_risks = await self._identify_risks(
            requirement, change_type, change_description, context_data
        )
        
        # 量化风险
        quantified_risks = self._quantify_risks(identified_risks, requirement, change_type)
        
        # 计算整体风险
        overall_score, overall_level = self._calculate_overall_risk(quantified_risks)
        
        # 生成风险摘要
        risk_summary = self._generate_risk_summary(quantified_risks)
        
        # 生成建议
        recommendations = self._generate_risk_recommendations(
            quantified_risks, overall_score, requirement, change_type
        )
        
        return RiskAssessmentResult(
            requirement_id=requirement_id,
            change_type=change_type,
            identified_risks=quantified_risks,
            overall_risk_score=overall_score,
            overall_risk_level=overall_level,
            risk_summary=risk_summary,
            recommendations=recommendations,
            assessment_date=datetime.utcnow()
        )
    
    async def _identify_risks(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        change_description: str,
        context_data: Dict[str, Any]
    ) -> List[RiskItem]:
        """识别风险"""
        risks = []
        
        # 基于变更类型的风险
        risks.extend(self._identify_change_type_risks(change_type))
        
        # 基于需求特征的风险
        risks.extend(self._identify_requirement_characteristic_risks(requirement))
        
        # 基于需求状态的风险
        risks.extend(self._identify_status_based_risks(requirement))
        
        # 基于复杂度的风险
        risks.extend(self._identify_complexity_risks(requirement))
        
        # 基于业务价值的风险
        risks.extend(self._identify_business_value_risks(requirement))
        
        # 基于上下文的风险
        risks.extend(self._identify_context_risks(requirement, context_data))
        
        return risks
    
    def _identify_change_type_risks(self, change_type: ChangeType) -> List[RiskItem]:
        """基于变更类型识别风险"""
        risks = []
        
        if change_type == ChangeType.DELETION:
            risks.append(RiskItem(
                id="DEL_001",
                category=RiskCategory.TECHNICAL,
                title="依赖关系破坏",
                description="删除需求可能破坏现有的依赖关系",
                probability=0.8,
                impact=8.0,
                risk_score=6.4,
                level=RiskLevel.HIGH,
                mitigation_strategies=[
                    "详细分析所有依赖关系",
                    "制定依赖关系迁移计划",
                    "通知所有相关干系人"
                ],
                contingency_plans=[
                    "保留需求的存根实现",
                    "提供替代解决方案"
                ]
            ))
            
            risks.append(RiskItem(
                id="DEL_002",
                category=RiskCategory.BUSINESS,
                title="业务功能缺失",
                description="删除需求可能导致业务功能缺失",
                probability=0.7,
                impact=7.0,
                risk_score=4.9,
                level=RiskLevel.MEDIUM,
                mitigation_strategies=[
                    "确认业务方同意删除",
                    "评估替代方案",
                    "制定功能迁移计划"
                ],
                contingency_plans=[
                    "快速恢复删除的功能",
                    "提供临时解决方案"
                ]
            ))
        
        elif change_type == ChangeType.MODIFICATION:
            risks.append(RiskItem(
                id="MOD_001",
                category=RiskCategory.QUALITY,
                title="回归缺陷",
                description="修改需求可能引入新的缺陷或影响现有功能",
                probability=0.6,
                impact=6.0,
                risk_score=3.6,
                level=RiskLevel.MEDIUM,
                mitigation_strategies=[
                    "增加回归测试覆盖",
                    "进行代码审查",
                    "分阶段发布"
                ],
                contingency_plans=[
                    "快速回滚机制",
                    "热修复方案"
                ]
            ))
        
        elif change_type == ChangeType.ADDITION:
            risks.append(RiskItem(
                id="ADD_001",
                category=RiskCategory.SCHEDULE,
                title="开发延期",
                description="新增需求可能导致项目延期",
                probability=0.5,
                impact=5.0,
                risk_score=2.5,
                level=RiskLevel.LOW,
                mitigation_strategies=[
                    "重新评估项目时间线",
                    "调整资源分配",
                    "优化开发流程"
                ],
                contingency_plans=[
                    "延后非关键功能",
                    "增加开发资源"
                ]
            ))
        
        return risks
    
    def _identify_requirement_characteristic_risks(self, requirement: Requirement) -> List[RiskItem]:
        """基于需求特征识别风险"""
        risks = []
        
        # 高优先级需求的风险
        if requirement.priority in [Priority.CRITICAL, Priority.HIGH]:
            risks.append(RiskItem(
                id="CHAR_001",
                category=RiskCategory.BUSINESS,
                title="关键业务影响",
                description="高优先级需求变更可能对关键业务造成影响",
                probability=0.7,
                impact=8.0,
                risk_score=5.6,
                level=RiskLevel.HIGH,
                mitigation_strategies=[
                    "制定详细的变更计划",
                    "进行充分的测试",
                    "准备回滚方案"
                ],
                contingency_plans=[
                    "紧急回滚程序",
                    "业务连续性计划"
                ]
            ))
        
        # 核心业务价值需求的风险
        if requirement.business_value == BusinessValue.CORE:
            risks.append(RiskItem(
                id="CHAR_002",
                category=RiskCategory.BUSINESS,
                title="核心价值损失",
                description="核心业务价值需求变更可能影响产品核心竞争力",
                probability=0.6,
                impact=9.0,
                risk_score=5.4,
                level=RiskLevel.HIGH,
                mitigation_strategies=[
                    "业务影响评估",
                    "用户接受度测试",
                    "分阶段推出"
                ],
                contingency_plans=[
                    "快速恢复原功能",
                    "用户沟通计划"
                ]
            ))
        
        return risks
    
    def _identify_status_based_risks(self, requirement: Requirement) -> List[RiskItem]:
        """基于需求状态识别风险"""
        risks = []
        
        if requirement.status == RequirementStatus.IN_DEVELOPMENT:
            risks.append(RiskItem(
                id="STAT_001",
                category=RiskCategory.SCHEDULE,
                title="开发中断",
                description="需求正在开发中，变更可能导致开发工作中断",
                probability=0.8,
                impact=6.0,
                risk_score=4.8,
                level=RiskLevel.MEDIUM,
                mitigation_strategies=[
                    "与开发团队协调变更时机",
                    "评估已完成工作的保留价值",
                    "制定增量变更计划"
                ],
                contingency_plans=[
                    "暂停当前开发",
                    "保存开发进度"
                ]
            ))
        
        elif requirement.status == RequirementStatus.TESTING:
            risks.append(RiskItem(
                id="STAT_002",
                category=RiskCategory.QUALITY,
                title="测试重做",
                description="需求正在测试中，变更可能需要重新进行测试",
                probability=0.9,
                impact=5.0,
                risk_score=4.5,
                level=RiskLevel.MEDIUM,
                mitigation_strategies=[
                    "评估测试用例的重用性",
                    "制定增量测试计划",
                    "优先测试变更部分"
                ],
                contingency_plans=[
                    "快速回归测试",
                    "自动化测试加速"
                ]
            ))
        
        elif requirement.status == RequirementStatus.COMPLETED:
            risks.append(RiskItem(
                id="STAT_003",
                category=RiskCategory.COST,
                title="返工成本",
                description="已完成需求的变更将产生较高的返工成本",
                probability=0.9,
                impact=7.0,
                risk_score=6.3,
                level=RiskLevel.HIGH,
                mitigation_strategies=[
                    "详细的成本效益分析",
                    "寻找最小化变更方案",
                    "评估变更的必要性"
                ],
                contingency_plans=[
                    "分阶段实施变更",
                    "寻找替代解决方案"
                ]
            ))
        
        return risks
    
    def _identify_complexity_risks(self, requirement: Requirement) -> List[RiskItem]:
        """基于复杂度识别风险"""
        risks = []
        
        if requirement.complexity in [Complexity.COMPLEX, Complexity.VERY_COMPLEX]:
            risks.append(RiskItem(
                id="COMP_001",
                category=RiskCategory.TECHNICAL,
                title="技术实现风险",
                description="高复杂度需求变更可能面临技术实现困难",
                probability=0.7,
                impact=7.0,
                risk_score=4.9,
                level=RiskLevel.MEDIUM,
                mitigation_strategies=[
                    "技术可行性评估",
                    "原型验证",
                    "专家技术评审"
                ],
                contingency_plans=[
                    "简化技术方案",
                    "寻求外部技术支持"
                ]
            ))
            
            risks.append(RiskItem(
                id="COMP_002",
                category=RiskCategory.SCHEDULE,
                title="估算偏差",
                description="复杂需求的工作量估算可能存在较大偏差",
                probability=0.8,
                impact=6.0,
                risk_score=4.8,
                level=RiskLevel.MEDIUM,
                mitigation_strategies=[
                    "多轮估算验证",
                    "分解为更小的任务",
                    "增加缓冲时间"
                ],
                contingency_plans=[
                    "动态调整计划",
                    "增加资源投入"
                ]
            ))
        
        return risks
    
    def _identify_business_value_risks(self, requirement: Requirement) -> List[RiskItem]:
        """基于业务价值识别风险"""
        risks = []
        
        if requirement.business_value == BusinessValue.OPTIONAL:
            risks.append(RiskItem(
                id="BV_001",
                category=RiskCategory.COST,
                title="投资回报率低",
                description="可选需求的变更可能投资回报率较低",
                probability=0.6,
                impact=4.0,
                risk_score=2.4,
                level=RiskLevel.LOW,
                mitigation_strategies=[
                    "重新评估业务价值",
                    "考虑延后实施",
                    "寻找更高价值的替代方案"
                ],
                contingency_plans=[
                    "取消变更",
                    "降低实施优先级"
                ]
            ))
        
        return risks
    
    def _identify_context_risks(
        self, 
        requirement: Requirement, 
        context_data: Dict[str, Any]
    ) -> List[RiskItem]:
        """基于上下文识别风险"""
        risks = []
        
        # 资源约束风险
        if context_data.get("resource_constrained", False):
            risks.append(RiskItem(
                id="CTX_001",
                category=RiskCategory.RESOURCE,
                title="资源不足",
                description="当前资源紧张，可能无法及时完成变更",
                probability=0.7,
                impact=6.0,
                risk_score=4.2,
                level=RiskLevel.MEDIUM,
                mitigation_strategies=[
                    "重新分配资源优先级",
                    "寻求额外资源支持",
                    "调整变更时间安排"
                ],
                contingency_plans=[
                    "延后变更实施",
                    "外包部分工作"
                ]
            ))
        
        # 时间压力风险
        if context_data.get("tight_deadline", False):
            risks.append(RiskItem(
                id="CTX_002",
                category=RiskCategory.SCHEDULE,
                title="时间压力",
                description="紧迫的截止日期可能导致变更质量下降",
                probability=0.8,
                impact=5.0,
                risk_score=4.0,
                level=RiskLevel.MEDIUM,
                mitigation_strategies=[
                    "简化变更范围",
                    "增加质量检查点",
                    "并行处理部分工作"
                ],
                contingency_plans=[
                    "申请延期",
                    "降低变更标准"
                ]
            ))
        
        return risks
    
    def _quantify_risks(
        self, 
        risks: List[RiskItem], 
        requirement: Requirement, 
        change_type: ChangeType
    ) -> List[RiskItem]:
        """量化风险"""
        quantified_risks = []
        
        for risk in risks:
            # 根据需求特征调整概率和影响
            adjusted_probability = self._adjust_probability(risk, requirement, change_type)
            adjusted_impact = self._adjust_impact(risk, requirement, change_type)
            
            # 重新计算风险分数和级别
            risk_score = adjusted_probability * adjusted_impact
            risk_level = self._calculate_risk_level(risk_score)
            
            quantified_risk = RiskItem(
                id=risk.id,
                category=risk.category,
                title=risk.title,
                description=risk.description,
                probability=adjusted_probability,
                impact=adjusted_impact,
                risk_score=risk_score,
                level=risk_level,
                mitigation_strategies=risk.mitigation_strategies,
                contingency_plans=risk.contingency_plans
            )
            
            quantified_risks.append(quantified_risk)
        
        return quantified_risks
    
    def _adjust_probability(
        self, 
        risk: RiskItem, 
        requirement: Requirement, 
        change_type: ChangeType
    ) -> float:
        """调整风险概率"""
        probability = risk.probability
        
        # 基于需求状态调整
        if requirement.status == RequirementStatus.COMPLETED:
            probability *= 1.2  # 已完成需求变更概率更高
        elif requirement.status == RequirementStatus.DRAFT:
            probability *= 0.8  # 草稿状态风险概率较低
        
        # 基于复杂度调整
        if requirement.complexity == Complexity.VERY_COMPLEX:
            probability *= 1.3
        elif requirement.complexity == Complexity.SIMPLE:
            probability *= 0.7
        
        return min(probability, 1.0)
    
    def _adjust_impact(
        self, 
        risk: RiskItem, 
        requirement: Requirement, 
        change_type: ChangeType
    ) -> float:
        """调整风险影响"""
        impact = risk.impact
        
        # 基于业务价值调整
        if requirement.business_value == BusinessValue.CORE:
            impact *= 1.3
        elif requirement.business_value == BusinessValue.OPTIONAL:
            impact *= 0.7
        
        # 基于优先级调整
        if requirement.priority == Priority.CRITICAL:
            impact *= 1.4
        elif requirement.priority == Priority.LOW:
            impact *= 0.8
        
        return min(impact, 10.0)
    
    def _calculate_risk_level(self, risk_score: float) -> RiskLevel:
        """计算风险级别"""
        if risk_score >= 8.0:
            return RiskLevel.VERY_HIGH
        elif risk_score >= 6.0:
            return RiskLevel.HIGH
        elif risk_score >= 4.0:
            return RiskLevel.MEDIUM
        elif risk_score >= 2.0:
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def _calculate_overall_risk(self, risks: List[RiskItem]) -> Tuple[float, RiskLevel]:
        """计算整体风险"""
        if not risks:
            return 0.0, RiskLevel.VERY_LOW
        
        # 使用加权平均计算整体风险分数
        total_score = sum(risk.risk_score for risk in risks)
        max_possible_score = len(risks) * 10.0
        
        # 归一化到0-10范围
        overall_score = (total_score / max_possible_score) * 10.0 if max_possible_score > 0 else 0.0
        
        # 考虑高风险项的影响
        high_risk_count = len([r for r in risks if r.level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]])
        if high_risk_count > 0:
            overall_score += high_risk_count * 0.5
        
        overall_score = min(overall_score, 10.0)
        overall_level = self._calculate_risk_level(overall_score)
        
        return overall_score, overall_level
    
    def _generate_risk_summary(self, risks: List[RiskItem]) -> Dict[str, Any]:
        """生成风险摘要"""
        summary = {
            "total_risks": len(risks),
            "risk_distribution": {},
            "category_distribution": {},
            "high_priority_risks": []
        }
        
        # 按级别分布
        for level in RiskLevel:
            count = len([r for r in risks if r.level == level])
            summary["risk_distribution"][level.value] = count
        
        # 按类别分布
        for category in RiskCategory:
            count = len([r for r in risks if r.category == category])
            summary["category_distribution"][category.value] = count
        
        # 高优先级风险
        high_priority = [
            r for r in risks 
            if r.level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        ]
        summary["high_priority_risks"] = [
            {
                "id": r.id,
                "title": r.title,
                "category": r.category.value,
                "level": r.level.value,
                "score": r.risk_score
            }
            for r in high_priority
        ]
        
        return summary
    
    def _generate_risk_recommendations(
        self,
        risks: List[RiskItem],
        overall_score: float,
        requirement: Requirement,
        change_type: ChangeType
    ) -> List[str]:
        """生成风险建议"""
        recommendations = []
        
        # 基于整体风险级别的建议
        if overall_score >= 8.0:
            recommendations.append("🚨 整体风险极高，建议重新考虑变更的必要性")
            recommendations.append("📋 必须制定详细的风险缓解计划")
            recommendations.append("👥 建议成立专门的风险管理小组")
        elif overall_score >= 6.0:
            recommendations.append("⚠️ 整体风险较高，需要特别关注")
            recommendations.append("📝 建议制定风险应对措施")
        elif overall_score >= 4.0:
            recommendations.append("📊 中等风险水平，建议持续监控")
        
        # 基于高风险项的建议
        high_risks = [r for r in risks if r.level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]]
        for risk in high_risks[:3]:  # 只显示前3个最高风险
            recommendations.append(f"🎯 重点关注{risk.category.value}风险：{risk.title}")
            if risk.mitigation_strategies:
                recommendations.append(f"   建议措施：{risk.mitigation_strategies[0]}")
        
        # 基于风险类别的建议
        tech_risks = [r for r in risks if r.category == RiskCategory.TECHNICAL]
        if len(tech_risks) > 2:
            recommendations.append("🔧 技术风险较多，建议进行技术评审")
        
        business_risks = [r for r in risks if r.category == RiskCategory.BUSINESS]
        if len(business_risks) > 2:
            recommendations.append("💼 业务风险较多，建议与业务方充分沟通")
        
        return recommendations
    
    def _initialize_risk_templates(self) -> Dict[str, Any]:
        """初始化风险模板"""
        # 这里可以定义更多的风险模板
        return {
            "change_types": {
                ChangeType.DELETION: ["依赖破坏", "功能缺失", "数据丢失"],
                ChangeType.MODIFICATION: ["回归缺陷", "性能影响", "兼容性问题"],
                ChangeType.ADDITION: ["资源消耗", "集成复杂", "测试负担"],
                ChangeType.CLARIFICATION: ["理解偏差", "沟通成本"]
            }
        }