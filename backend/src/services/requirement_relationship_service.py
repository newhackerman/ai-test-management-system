"""
需求关联关系服务层

本模块提供需求关联关系的业务逻辑，包括：
- 需求依赖关系管理
- 关联关系验证
- 循环依赖检测
- 依赖链分析
- 影响范围分析
- 可视化关系图生成
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from ..repositories.requirement_relationship_repository import RequirementRelationshipRepository
from ..models.requirement import RequirementDependency, DependencyType, Requirement
from ..schemas.requirement_relationship import (
    CreateDependencyRequest,
    UpdateDependencyRequest,
    DependencyResponse,
    DependencyChainResponse,
    DependencyChainNode,
    CircularDependencyCheckResponse,
    DependencyStatisticsResponse,
    DependencyGraphResponse,
    DependencyGraphNode,
    DependencyGraphEdge,
    ImpactAnalysisResponse,
    ImpactedRequirement
)


class RequirementRelationshipService:
    """需求关联关系服务类"""
    
    def __init__(self, db: Session):
        """
        初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = RequirementRelationshipRepository(db)
    
    def create_dependency(
        self,
        request: CreateDependencyRequest,
        created_by: int
    ) -> DependencyResponse:
        """
        创建需求依赖关系
        
        Args:
            request: 创建依赖关系请求
            created_by: 创建人ID
            
        Returns:
            依赖关系响应
            
        Raises:
            ValueError: 如果验证失败
        """
        # 1. 验证需求存在
        source_req = self._get_requirement_or_raise(request.source_requirement_id)
        target_req = self._get_requirement_or_raise(request.target_requirement_id)
        
        # 2. 验证需求属于同一项目
        if source_req.project_id != target_req.project_id:
            raise ValueError("源需求和目标需求必须属于同一项目")
        
        # 3. 检查依赖关系是否已存在
        if self.repository.check_dependency_exists(
            request.source_requirement_id,
            request.target_requirement_id,
            DependencyType[request.dependency_type.value]
        ):
            raise ValueError("该依赖关系已存在")
        
        # 4. 检查循环依赖
        if self.repository.detect_circular_dependency(
            request.source_requirement_id,
            request.target_requirement_id
        ):
            raise ValueError("创建该依赖关系会形成循环依赖")
        
        # 5. 验证依赖类型的合理性
        self._validate_dependency_type(
            request.dependency_type.value,
            source_req,
            target_req
        )
        
        # 6. 创建依赖关系
        dependency = self.repository.create_dependency(
            source_requirement_id=request.source_requirement_id,
            target_requirement_id=request.target_requirement_id,
            dependency_type=DependencyType[request.dependency_type.value],
            description=request.description,
            created_by=created_by
        )
        
        # 7. 构建响应
        return self._build_dependency_response(dependency, source_req, target_req)
    
    def get_dependency(self, dependency_id: int) -> Optional[DependencyResponse]:
        """
        获取依赖关系详情
        
        Args:
            dependency_id: 依赖关系ID
            
        Returns:
            依赖关系响应，如果不存在则返回None
        """
        dependency = self.repository.get_dependency_by_id(dependency_id)
        if not dependency:
            return None
        
        source_req = self._get_requirement_or_raise(dependency.source_requirement_id)
        target_req = self._get_requirement_or_raise(dependency.target_requirement_id)
        
        return self._build_dependency_response(dependency, source_req, target_req)
    
    def get_requirement_dependencies(
        self,
        requirement_id: int,
        direction: str = "both"
    ) -> Dict[str, List[DependencyResponse]]:
        """
        获取需求的所有依赖关系
        
        Args:
            requirement_id: 需求ID
            direction: 方向 ("source", "target", "both")
            
        Returns:
            依赖关系字典，包含source和target两个列表
        """
        result = {"source": [], "target": []}
        
        if direction in ["source", "both"]:
            source_deps = self.repository.get_dependencies_by_source(requirement_id)
            for dep in source_deps:
                target_req = self._get_requirement_or_raise(dep.target_requirement_id)
                source_req = self._get_requirement_or_raise(dep.source_requirement_id)
                result["source"].append(
                    self._build_dependency_response(dep, source_req, target_req)
                )
        
        if direction in ["target", "both"]:
            target_deps = self.repository.get_dependencies_by_target(requirement_id)
            for dep in target_deps:
                source_req = self._get_requirement_or_raise(dep.source_requirement_id)
                target_req = self._get_requirement_or_raise(dep.target_requirement_id)
                result["target"].append(
                    self._build_dependency_response(dep, source_req, target_req)
                )
        
        return result
    
    def update_dependency(
        self,
        dependency_id: int,
        request: UpdateDependencyRequest
    ) -> Optional[DependencyResponse]:
        """
        更新依赖关系
        
        Args:
            dependency_id: 依赖关系ID
            request: 更新请求
            
        Returns:
            更新后的依赖关系响应，如果不存在则返回None
        """
        dependency = self.repository.get_dependency_by_id(dependency_id)
        if not dependency:
            return None
        
        # 更新依赖关系
        updated_dependency = self.repository.update_dependency(
            dependency_id=dependency_id,
            dependency_type=DependencyType[request.dependency_type.value] if request.dependency_type else None,
            description=request.description
        )
        
        if not updated_dependency:
            return None
        
        source_req = self._get_requirement_or_raise(updated_dependency.source_requirement_id)
        target_req = self._get_requirement_or_raise(updated_dependency.target_requirement_id)
        
        return self._build_dependency_response(updated_dependency, source_req, target_req)
    
    def delete_dependency(self, dependency_id: int) -> bool:
        """
        删除依赖关系
        
        Args:
            dependency_id: 依赖关系ID
            
        Returns:
            删除成功返回True，否则返回False
        """
        return self.repository.delete_dependency(dependency_id)
    
    def get_dependency_chain(
        self,
        requirement_id: int,
        direction: str = "downstream",
        max_depth: int = 10
    ) -> DependencyChainResponse:
        """
        获取需求的依赖链
        
        Args:
            requirement_id: 需求ID
            direction: 方向 ("downstream" 下游, "upstream" 上游)
            max_depth: 最大深度
            
        Returns:
            依赖链响应
        """
        # 验证需求存在
        self._get_requirement_or_raise(requirement_id)
        
        # 获取依赖链
        chain_data = self.repository.get_dependency_chain(
            requirement_id=requirement_id,
            direction=direction,
            max_depth=max_depth
        )
        
        # 构建响应
        chain_nodes = []
        max_depth_found = 0
        
        for item in chain_data:
            req = self._get_requirement_or_raise(item['requirement_id'])
            chain_nodes.append(DependencyChainNode(
                requirement_id=item['requirement_id'],
                requirement_title=req.title,
                dependency_type=item['dependency_type'],
                depth=item['depth'],
                description=item.get('description')
            ))
            max_depth_found = max(max_depth_found, item['depth'])
        
        return DependencyChainResponse(
            requirement_id=requirement_id,
            direction=direction,
            chain=chain_nodes,
            total_count=len(chain_nodes),
            max_depth=max_depth_found
        )
    
    def check_circular_dependency(
        self,
        source_requirement_id: int,
        target_requirement_id: int
    ) -> CircularDependencyCheckResponse:
        """
        检测循环依赖
        
        Args:
            source_requirement_id: 源需求ID
            target_requirement_id: 目标需求ID
            
        Returns:
            循环依赖检测响应
        """
        # 验证需求存在
        self._get_requirement_or_raise(source_requirement_id)
        self._get_requirement_or_raise(target_requirement_id)
        
        # 检测循环依赖
        has_circular = self.repository.detect_circular_dependency(
            source_requirement_id,
            target_requirement_id
        )
        
        if has_circular:
            message = f"检测到循环依赖：从需求{target_requirement_id}可以到达需求{source_requirement_id}"
        else:
            message = "未检测到循环依赖"
        
        return CircularDependencyCheckResponse(
            has_circular_dependency=has_circular,
            source_requirement_id=source_requirement_id,
            target_requirement_id=target_requirement_id,
            message=message,
            circular_path=None  # TODO: 实现循环路径追踪
        )
    
    def get_dependency_statistics(self, project_id: int) -> DependencyStatisticsResponse:
        """
        获取项目的依赖关系统计
        
        Args:
            project_id: 项目ID
            
        Returns:
            依赖关系统计响应
        """
        stats = self.repository.get_dependency_statistics(project_id)
        
        return DependencyStatisticsResponse(
            project_id=project_id,
            total_dependencies=stats['total_dependencies'],
            by_type=stats['by_type'],
            requirements_with_dependencies=stats['requirements_with_dependencies'],
            requirements_without_dependencies=stats['requirements_without_dependencies']
        )
    
    def get_dependency_graph(self, project_id: int) -> DependencyGraphResponse:
        """
        获取项目的依赖关系图
        
        Args:
            project_id: 项目ID
            
        Returns:
            依赖关系图响应
        """
        # 获取项目的所有需求
        requirements = self.repository.get_requirements_by_project(project_id)
        
        # 构建节点
        nodes = []
        for req in requirements:
            nodes.append(DependencyGraphNode(
                id=req.id,
                title=req.title,
                status=req.status.value if req.status else "DRAFT",
                priority=req.priority.value if req.priority else "MEDIUM"
            ))
        
        # 构建边
        edges = []
        requirement_ids = [req.id for req in requirements]
        
        for req_id in requirement_ids:
            deps = self.repository.get_dependencies_by_source(req_id)
            for dep in deps:
                if dep.target_requirement_id in requirement_ids:
                    edges.append(DependencyGraphEdge(
                        source=dep.source_requirement_id,
                        target=dep.target_requirement_id,
                        type=dep.dependency_type.value,
                        description=dep.description
                    ))
        
        return DependencyGraphResponse(
            project_id=project_id,
            nodes=nodes,
            edges=edges
        )
    
    def analyze_impact(
        self,
        requirement_id: int,
        change_description: Optional[str] = None
    ) -> ImpactAnalysisResponse:
        """
        分析需求变更的影响范围
        
        Args:
            requirement_id: 需求ID
            change_description: 变更描述
            
        Returns:
            影响范围分析响应
        """
        # 验证需求存在
        requirement = self._get_requirement_or_raise(requirement_id)
        
        # 获取直接影响（依赖该需求的其他需求）
        direct_impacts = []
        target_deps = self.repository.get_dependencies_by_target(requirement_id)
        
        for dep in target_deps:
            source_req = self._get_requirement_or_raise(dep.source_requirement_id)
            impact_level = self._calculate_impact_level(dep.dependency_type.value)
            
            direct_impacts.append(ImpactedRequirement(
                requirement_id=source_req.id,
                requirement_title=source_req.title,
                impact_type=dep.dependency_type.value,
                impact_level=impact_level,
                description=f"该需求{dep.dependency_type.value}被修改的需求"
            ))
        
        # 获取间接影响（依赖链上的其他需求）
        indirect_impacts = []
        chain = self.repository.get_dependency_chain(
            requirement_id=requirement_id,
            direction="upstream",
            max_depth=5
        )
        
        for item in chain:
            if item['depth'] > 1:  # 深度大于1的是间接影响
                req = self._get_requirement_or_raise(item['requirement_id'])
                impact_level = self._calculate_impact_level(item['dependency_type'], is_indirect=True)
                
                indirect_impacts.append(ImpactedRequirement(
                    requirement_id=req.id,
                    requirement_title=req.title,
                    impact_type=item['dependency_type'],
                    impact_level=impact_level,
                    description=f"通过依赖链间接受影响（深度：{item['depth']}）"
                ))
        
        # 计算总体风险等级
        total_impacted = len(direct_impacts) + len(indirect_impacts)
        risk_level = self._calculate_risk_level(direct_impacts, indirect_impacts)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            requirement,
            direct_impacts,
            indirect_impacts,
            risk_level
        )
        
        return ImpactAnalysisResponse(
            requirement_id=requirement_id,
            change_description=change_description,
            direct_impacts=direct_impacts,
            indirect_impacts=indirect_impacts,
            total_impacted=total_impacted,
            risk_level=risk_level,
            recommendations=recommendations
        )
    
    def _get_requirement_or_raise(self, requirement_id: int) -> Requirement:
        """获取需求，如果不存在则抛出异常"""
        requirement = self.db.query(Requirement).filter(
            Requirement.id == requirement_id
        ).first()
        
        if not requirement:
            raise ValueError(f"需求ID {requirement_id} 不存在")
        
        return requirement
    
    def _validate_dependency_type(
        self,
        dependency_type: str,
        source_req: Requirement,
        target_req: Requirement
    ):
        """验证依赖类型的合理性"""
        # CONFLICTS_WITH 类型的验证
        if dependency_type == "CONFLICTS_WITH":
            # 检查是否已存在其他类型的依赖关系
            existing_deps = self.repository.get_dependencies_by_source(source_req.id)
            for dep in existing_deps:
                if dep.target_requirement_id == target_req.id and dep.dependency_type != DependencyType.CONFLICTS_WITH:
                    raise ValueError("不能在已有其他依赖关系的需求间创建冲突关系")
        
        # DUPLICATES 类型的验证
        if dependency_type == "DUPLICATES":
            # 重复关系应该是双向的
            pass  # 可以添加更多验证逻辑
    
    def _build_dependency_response(
        self,
        dependency: RequirementDependency,
        source_req: Requirement,
        target_req: Requirement
    ) -> DependencyResponse:
        """构建依赖关系响应"""
        return DependencyResponse(
            id=dependency.id,
            source_requirement_id=dependency.source_requirement_id,
            target_requirement_id=dependency.target_requirement_id,
            dependency_type=dependency.dependency_type.value,
            description=dependency.description,
            created_by=dependency.created_by,
            created_at=dependency.created_at,
            updated_at=dependency.updated_at,
            source_requirement_title=source_req.title,
            target_requirement_title=target_req.title
        )
    
    def _calculate_impact_level(self, dependency_type: str, is_indirect: bool = False) -> str:
        """计算影响程度"""
        if is_indirect:
            return "LOW"
        
        impact_levels = {
            "DEPENDS_ON": "HIGH",
            "BLOCKS": "HIGH",
            "RELATES_TO": "MEDIUM",
            "CONFLICTS_WITH": "HIGH",
            "DUPLICATES": "MEDIUM",
            "REPLACES": "HIGH"
        }
        
        return impact_levels.get(dependency_type, "MEDIUM")
    
    def _calculate_risk_level(
        self,
        direct_impacts: List[ImpactedRequirement],
        indirect_impacts: List[ImpactedRequirement]
    ) -> str:
        """计算风险等级"""
        high_impact_count = sum(1 for imp in direct_impacts if imp.impact_level == "HIGH")
        total_impact_count = len(direct_impacts) + len(indirect_impacts)
        
        if high_impact_count >= 3 or total_impact_count >= 10:
            return "HIGH"
        elif high_impact_count >= 1 or total_impact_count >= 5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_recommendations(
        self,
        requirement: Requirement,
        direct_impacts: List[ImpactedRequirement],
        indirect_impacts: List[ImpactedRequirement],
        risk_level: str
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if direct_impacts:
            recommendations.append(f"建议通知{len(direct_impacts)}个直接受影响需求的负责人")
        
        if indirect_impacts:
            recommendations.append(f"建议评估{len(indirect_impacts)}个间接受影响需求的影响程度")
        
        if risk_level == "HIGH":
            recommendations.append("风险等级较高，建议召开评审会议讨论变更方案")
            recommendations.append("建议制定详细的变更实施计划和回滚方案")
        elif risk_level == "MEDIUM":
            recommendations.append("建议重新评估受影响需求的工作量和时间计划")
        
        if not recommendations:
            recommendations.append("影响范围较小，可以正常进行变更")
        
        return recommendations
