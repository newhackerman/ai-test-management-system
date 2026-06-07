"""
变更影响分析服务

本模块提供需求变更的影响分析功能，包括：
- 多维度影响评估
- 变更风险评估
- 级联影响分析
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from decimal import Decimal

from models.requirement import (
    Requirement, RequirementDependency, DependencyType,
    ChangeType, RequirementStatus, Priority
)
from repositories.requirement_repository import RequirementRepository
from repositories.requirement_relationship_repository import RequirementRelationshipRepository
from schemas.requirement_change import (
    ImpactAnalysisRequest, ImpactAnalysisResponse, ImpactItem
)


class ChangeImpactAnalysisService:
    """变更影响分析服务"""
    
    def __init__(
        self,
        requirement_repo: RequirementRepository,
        relationship_repo: RequirementRelationshipRepository
    ):
        self.requirement_repo = requirement_repo
        self.relationship_repo = relationship_repo
    
    async def analyze_change_impact(
        self,
        request: ImpactAnalysisRequest
    ) -> ImpactAnalysisResponse:
        """分析变更影响"""
        requirement = await self.requirement_repo.get_by_id(request.requirement_id)
        if not requirement:
            raise ValueError(f"需求 {request.requirement_id} 不存在")
        
        # 分析直接影响
        direct_impacts = await self._analyze_direct_impacts(
            requirement, request.change_type, request.change_description
        )
        
        # 分析间接影响
        indirect_impacts = await self._analyze_indirect_impacts(
            requirement, request.change_type, request.analysis_depth
        )
        
        # 计算级联深度
        cascade_depth = await self._calculate_cascade_depth(
            requirement.id, request.analysis_depth
        )
        
        # 计算风险分数
        risk_score = self._calculate_risk_score(
            requirement, request.change_type, direct_impacts, indirect_impacts
        )
        
        # 生成建议
        recommendations = self._generate_recommendations(
            requirement, request.change_type, direct_impacts, indirect_impacts, risk_score
        )
        
        # 生成分析摘要
        analysis_summary = self._generate_analysis_summary(
            requirement, request.change_type, direct_impacts, indirect_impacts, risk_score
        )
        
        return ImpactAnalysisResponse(
            requirement_id=request.requirement_id,
            change_type=request.change_type,
            analysis_summary=analysis_summary,
            total_impacted_requirements=len(direct_impacts) + len(indirect_impacts),
            direct_impacts=direct_impacts,
            indirect_impacts=indirect_impacts,
            cascade_depth=cascade_depth,
            risk_score=risk_score,
            recommendations=recommendations,
            analysis_date=datetime.utcnow()
        )
    
    async def _analyze_direct_impacts(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        change_description: str
    ) -> List[ImpactItem]:
        """分析直接影响"""
        impacts = []
        
        # 获取直接依赖此需求的其他需求
        dependent_requirements = await self.relationship_repo.get_dependent_requirements(
            requirement.id
        )
        
        for dep_req in dependent_requirements:
            impact_level = self._assess_direct_impact_level(
                requirement, dep_req, change_type
            )
            
            impact_description = self._generate_direct_impact_description(
                requirement, dep_req, change_type
            )
            
            estimated_effort = self._estimate_impact_effort(
                dep_req, change_type, impact_level
            )
            
            impacts.append(ImpactItem(
                requirement_id=dep_req.id,
                requirement_title=dep_req.title,
                impact_type="DIRECT",
                impact_level=impact_level,
                impact_description=impact_description,
                estimated_effort=estimated_effort
            ))
        
        # 分析同一项目内的相关需求
        project_requirements = await self.requirement_repo.get_requirements_by_project(
            requirement.project_id
        )
        
        for proj_req in project_requirements:
            if proj_req.id == requirement.id:
                continue
            
            # 检查是否有业务关联
            if self._has_business_relationship(requirement, proj_req):
                impact_level = self._assess_business_impact_level(
                    requirement, proj_req, change_type
                )
                
                if impact_level != "NONE":
                    impact_description = self._generate_business_impact_description(
                        requirement, proj_req, change_type
                    )
                    
                    estimated_effort = self._estimate_impact_effort(
                        proj_req, change_type, impact_level
                    )
                    
                    impacts.append(ImpactItem(
                        requirement_id=proj_req.id,
                        requirement_title=proj_req.title,
                        impact_type="DIRECT",
                        impact_level=impact_level,
                        impact_description=impact_description,
                        estimated_effort=estimated_effort
                    ))
        
        return impacts
    
    async def _analyze_indirect_impacts(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        max_depth: int
    ) -> List[ImpactItem]:
        """分析间接影响"""
        impacts = []
        visited = set()
        
        # 使用广度优先搜索分析级联影响
        await self._bfs_cascade_analysis(
            requirement.id, change_type, max_depth, 1, visited, impacts
        )
        
        return impacts
    
    async def _bfs_cascade_analysis(
        self,
        requirement_id: int,
        change_type: ChangeType,
        max_depth: int,
        current_depth: int,
        visited: Set[int],
        impacts: List[ImpactItem]
    ) -> None:
        """广度优先搜索级联影响分析"""
        if current_depth > max_depth or requirement_id in visited:
            return
        
        visited.add(requirement_id)
        
        # 获取依赖当前需求的需求
        dependent_requirements = await self.relationship_repo.get_dependent_requirements(
            requirement_id
        )
        
        for dep_req in dependent_requirements:
            if dep_req.id not in visited:
                impact_level = self._assess_indirect_impact_level(
                    dep_req, change_type, current_depth
                )
                
                if impact_level != "NONE":
                    impact_description = self._generate_indirect_impact_description(
                        dep_req, change_type, current_depth
                    )
                    
                    estimated_effort = self._estimate_impact_effort(
                        dep_req, change_type, impact_level
                    )
                    
                    impacts.append(ImpactItem(
                        requirement_id=dep_req.id,
                        requirement_title=dep_req.title,
                        impact_type="INDIRECT",
                        impact_level=impact_level,
                        impact_description=impact_description,
                        estimated_effort=estimated_effort
                    ))
                
                # 递归分析下一层
                await self._bfs_cascade_analysis(
                    dep_req.id, change_type, max_depth, current_depth + 1, visited, impacts
                )
    
    async def _calculate_cascade_depth(
        self,
        requirement_id: int,
        max_depth: int
    ) -> int:
        """计算级联深度"""
        visited = set()
        return await self._dfs_depth_calculation(requirement_id, max_depth, 0, visited)
    
    async def _dfs_depth_calculation(
        self,
        requirement_id: int,
        max_depth: int,
        current_depth: int,
        visited: Set[int]
    ) -> int:
        """深度优先搜索计算级联深度"""
        if current_depth >= max_depth or requirement_id in visited:
            return current_depth
        
        visited.add(requirement_id)
        max_cascade_depth = current_depth
        
        dependent_requirements = await self.relationship_repo.get_dependent_requirements(
            requirement_id
        )
        
        for dep_req in dependent_requirements:
            if dep_req.id not in visited:
                depth = await self._dfs_depth_calculation(
                    dep_req.id, max_depth, current_depth + 1, visited
                )
                max_cascade_depth = max(max_cascade_depth, depth)
        
        return max_cascade_depth
    
    def _assess_direct_impact_level(
        self,
        source_req: Requirement,
        target_req: Requirement,
        change_type: ChangeType
    ) -> str:
        """评估直接影响级别"""
        # 根据变更类型和需求状态评估影响级别
        if change_type == ChangeType.DELETION:
            return "HIGH"
        
        if change_type == ChangeType.MODIFICATION:
            # 如果目标需求正在开发或测试中，影响较高
            if target_req.status in [
                RequirementStatus.IN_DEVELOPMENT,
                RequirementStatus.TESTING
            ]:
                return "HIGH"
            elif target_req.status in [
                RequirementStatus.APPROVED,
                RequirementStatus.PENDING_REVIEW
            ]:
                return "MEDIUM"
            else:
                return "LOW"
        
        if change_type == ChangeType.ADDITION:
            return "LOW"
        
        return "MEDIUM"
    
    def _assess_indirect_impact_level(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        depth: int
    ) -> str:
        """评估间接影响级别"""
        # 距离越远，影响越小
        if depth > 3:
            return "NONE"
        elif depth > 2:
            return "LOW"
        elif depth > 1:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def _assess_business_impact_level(
        self,
        source_req: Requirement,
        target_req: Requirement,
        change_type: ChangeType
    ) -> str:
        """评估业务影响级别"""
        # 检查业务价值和优先级
        if (source_req.business_value and target_req.business_value and
            source_req.business_value.value == target_req.business_value.value):
            return "MEDIUM"
        
        if (source_req.priority and target_req.priority and
            source_req.priority in [Priority.CRITICAL, Priority.HIGH] and
            target_req.priority in [Priority.CRITICAL, Priority.HIGH]):
            return "MEDIUM"
        
        return "LOW"
    
    def _has_business_relationship(
        self,
        req1: Requirement,
        req2: Requirement
    ) -> bool:
        """检查是否有业务关联"""
        # 检查分类是否相同
        if req1.category and req2.category and req1.category == req2.category:
            return True
        
        # 检查标题或描述中是否有关键词重叠
        if req1.title and req2.title:
            req1_words = set(req1.title.lower().split())
            req2_words = set(req2.title.lower().split())
            if len(req1_words.intersection(req2_words)) > 0:
                return True
        
        return False
    
    def _calculate_risk_score(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        direct_impacts: List[ImpactItem],
        indirect_impacts: List[ImpactItem]
    ) -> float:
        """计算风险分数 (0-10)"""
        base_score = 0.0
        
        # 基于变更类型的基础分数
        type_scores = {
            ChangeType.DELETION: 8.0,
            ChangeType.MODIFICATION: 5.0,
            ChangeType.ADDITION: 2.0,
            ChangeType.CLARIFICATION: 1.0
        }
        base_score += type_scores.get(change_type, 3.0)
        
        # 基于需求状态的分数调整
        if requirement.status in [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.TESTING]:
            base_score += 2.0
        elif requirement.status == RequirementStatus.COMPLETED:
            base_score += 3.0
        
        # 基于影响数量的分数调整
        impact_count = len(direct_impacts) + len(indirect_impacts)
        if impact_count > 10:
            base_score += 2.0
        elif impact_count > 5:
            base_score += 1.0
        
        # 基于影响级别的分数调整
        high_impact_count = sum(1 for impact in direct_impacts + indirect_impacts 
                               if impact.impact_level == "HIGH")
        base_score += high_impact_count * 0.5
        
        return min(base_score, 10.0)
    
    def _estimate_impact_effort(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        impact_level: str
    ) -> Optional[Decimal]:
        """估算影响工作量"""
        if not requirement.estimated_effort:
            return None
        
        # 基于影响级别的工作量比例
        effort_ratios = {
            "HIGH": 0.5,
            "MEDIUM": 0.3,
            "LOW": 0.1
        }
        
        ratio = effort_ratios.get(impact_level, 0.2)
        return requirement.estimated_effort * Decimal(str(ratio))
    
    def _generate_direct_impact_description(
        self,
        source_req: Requirement,
        target_req: Requirement,
        change_type: ChangeType
    ) -> str:
        """生成直接影响描述"""
        type_descriptions = {
            ChangeType.DELETION: f"需求删除将直接影响依赖需求 '{target_req.title}'",
            ChangeType.MODIFICATION: f"需求修改可能需要调整依赖需求 '{target_req.title}'",
            ChangeType.ADDITION: f"需求新增可能影响相关需求 '{target_req.title}'",
            ChangeType.CLARIFICATION: f"需求澄清可能需要更新相关需求 '{target_req.title}'"
        }
        
        return type_descriptions.get(change_type, f"变更可能影响需求 '{target_req.title}'")
    
    def _generate_indirect_impact_description(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        depth: int
    ) -> str:
        """生成间接影响描述"""
        return f"通过 {depth} 层依赖关系间接影响需求 '{requirement.title}'"
    
    def _generate_business_impact_description(
        self,
        source_req: Requirement,
        target_req: Requirement,
        change_type: ChangeType
    ) -> str:
        """生成业务影响描述"""
        return f"业务关联需求 '{target_req.title}' 可能受到影响"
    
    def _generate_recommendations(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        direct_impacts: List[ImpactItem],
        indirect_impacts: List[ImpactItem],
        risk_score: float
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if risk_score >= 8.0:
            recommendations.append("高风险变更，建议召开变更评审会议")
            recommendations.append("建议分阶段实施变更以降低风险")
        elif risk_score >= 5.0:
            recommendations.append("中等风险变更，建议详细评估影响范围")
        
        if change_type == ChangeType.DELETION:
            recommendations.append("删除需求前请确认所有依赖关系已妥善处理")
        
        if len(direct_impacts) > 5:
            recommendations.append("影响范围较大，建议通知所有相关干系人")
        
        if requirement.status in [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.TESTING]:
            recommendations.append("需求正在开发中，变更可能导致额外成本")
        
        high_impact_reqs = [impact for impact in direct_impacts + indirect_impacts 
                           if impact.impact_level == "HIGH"]
        if high_impact_reqs:
            recommendations.append(f"重点关注高影响需求：{', '.join([req.requirement_title for req in high_impact_reqs[:3]])}")
        
        return recommendations
    
    def _generate_analysis_summary(
        self,
        requirement: Requirement,
        change_type: ChangeType,
        direct_impacts: List[ImpactItem],
        indirect_impacts: List[ImpactItem],
        risk_score: float
    ) -> str:
        """生成分析摘要"""
        total_impacts = len(direct_impacts) + len(indirect_impacts)
        
        risk_level = "高" if risk_score >= 7.0 else "中" if risk_score >= 4.0 else "低"
        
        summary = f"对需求 '{requirement.title}' 进行 {change_type.value} 变更的影响分析：\n"
        summary += f"- 总影响需求数：{total_impacts}\n"
        summary += f"- 直接影响：{len(direct_impacts)} 个需求\n"
        summary += f"- 间接影响：{len(indirect_impacts)} 个需求\n"
        summary += f"- 风险等级：{risk_level} ({risk_score:.1f}/10)"
        
        return summary