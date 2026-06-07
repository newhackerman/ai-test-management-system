"""
智能依赖分析服务

本模块提供智能依赖分析功能，包括：
- 依赖链分析器
- 循环依赖检测
- 影响范围分析
- 依赖风险评估
- 智能建议生成
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.requirement import Requirement, RequirementDependency, DependencyType, RequirementStatus, Priority
from ..repositories.requirement_relationship_repository import RequirementRelationshipRepository


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnalysisType(Enum):
    """分析类型枚举"""
    DEPENDENCY_CHAIN = "DEPENDENCY_CHAIN"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    IMPACT_ANALYSIS = "IMPACT_ANALYSIS"
    BOTTLENECK_ANALYSIS = "BOTTLENECK_ANALYSIS"
    CRITICAL_PATH = "CRITICAL_PATH"


@dataclass
class DependencyChainAnalysis:
    """依赖链分析结果"""
    requirement_id: int
    chain_length: int
    max_depth: int
    total_dependencies: int
    critical_dependencies: List[int]
    bottlenecks: List[int]
    risk_level: RiskLevel
    recommendations: List[str]


@dataclass
class CircularDependencyAnalysis:
    """循环依赖分析结果"""
    has_cycles: bool
    cycles: List[List[int]]
    affected_requirements: Set[int]
    severity: RiskLevel
    resolution_suggestions: List[str]


@dataclass
class ImpactAnalysisResult:
    """影响分析结果"""
    requirement_id: int
    direct_impacts: List[Dict[str, Any]]
    indirect_impacts: List[Dict[str, Any]]
    cascade_depth: int
    affected_count: int
    risk_score: float
    risk_level: RiskLevel
    mitigation_strategies: List[str]


@dataclass
class BottleneckAnalysis:
    """瓶颈分析结果"""
    bottleneck_requirements: List[Dict[str, Any]]
    critical_path_length: int
    parallel_opportunities: List[Dict[str, Any]]
    optimization_suggestions: List[str]


class DependencyAnalysisService:
    """智能依赖分析服务"""
    
    def __init__(self, db: Session):
        """
        初始化服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = RequirementRelationshipRepository(db)
        
        # 风险权重配置
        self.dependency_weights = {
            DependencyType.DEPENDS_ON: 1.0,
            DependencyType.BLOCKS: 1.2,
            DependencyType.CONFLICTS_WITH: 1.5,
            DependencyType.REPLACES: 0.8,
            DependencyType.RELATES_TO: 0.5,
            DependencyType.DUPLICATES: 0.3
        }
        
        # 状态风险系数
        self.status_risk_factors = {
            RequirementStatus.DRAFT: 1.5,
            RequirementStatus.PENDING_REVIEW: 1.3,
            RequirementStatus.REVIEWING: 1.2,
            RequirementStatus.NEEDS_REVISION: 1.4,
            RequirementStatus.APPROVED: 0.8,
            RequirementStatus.IN_DEVELOPMENT: 1.0,
            RequirementStatus.PAUSED: 1.8,
            RequirementStatus.TESTING: 0.9,
            RequirementStatus.TEST_FAILED: 1.6,
            RequirementStatus.COMPLETED: 0.3,
            RequirementStatus.DEPLOYED: 0.2,
            RequirementStatus.CLOSED: 0.1,
            RequirementStatus.CANCELLED: 0.0
        }
        
        # 优先级风险系数
        self.priority_risk_factors = {
            Priority.CRITICAL: 2.0,
            Priority.HIGH: 1.5,
            Priority.MEDIUM: 1.0,
            Priority.LOW: 0.7,
            Priority.OPTIONAL: 0.5
        }
    
    def analyze_dependency_chain(
        self,
        requirement_id: int,
        max_depth: int = 10
    ) -> DependencyChainAnalysis:
        """
        分析依赖链
        
        Args:
            requirement_id: 需求ID
            max_depth: 最大分析深度
            
        Returns:
            依赖链分析结果
        """
        # 获取需求信息
        requirement = self._get_requirement(requirement_id)
        if not requirement:
            raise ValueError(f"需求ID {requirement_id} 不存在")
        
        # 获取下游依赖链
        downstream_chain = self.repository.get_dependency_chain(
            requirement_id, "downstream", max_depth
        )
        
        # 获取上游依赖链
        upstream_chain = self.repository.get_dependency_chain(
            requirement_id, "upstream", max_depth
        )
        
        # 分析链特征
        total_dependencies = len(downstream_chain) + len(upstream_chain)
        max_depth_found = max(
            [0] + [item['depth'] for item in downstream_chain + upstream_chain]
        )
        
        # 识别关键依赖
        critical_dependencies = self._identify_critical_dependencies(
            downstream_chain + upstream_chain
        )
        
        # 识别瓶颈
        bottlenecks = self._identify_bottlenecks(requirement_id, downstream_chain, upstream_chain)
        
        # 计算风险等级
        risk_level = self._calculate_chain_risk_level(
            requirement, total_dependencies, max_depth_found, critical_dependencies
        )
        
        # 生成建议
        recommendations = self._generate_chain_recommendations(
            requirement, total_dependencies, max_depth_found, bottlenecks, risk_level
        )
        
        return DependencyChainAnalysis(
            requirement_id=requirement_id,
            chain_length=total_dependencies,
            max_depth=max_depth_found,
            total_dependencies=total_dependencies,
            critical_dependencies=critical_dependencies,
            bottlenecks=bottlenecks,
            risk_level=risk_level,
            recommendations=recommendations
        )
    
    def detect_circular_dependencies(self, project_id: int) -> CircularDependencyAnalysis:
        """
        检测项目中的循环依赖
        
        Args:
            project_id: 项目ID
            
        Returns:
            循环依赖分析结果
        """
        # 获取项目的所有需求和依赖关系
        requirements = self.repository.get_requirements_by_project(project_id)
        requirement_ids = [req.id for req in requirements]
        
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(requirement_ids)
        
        # 检测循环
        cycles = self._detect_cycles_in_graph(dependency_graph)
        
        # 分析受影响的需求
        affected_requirements = set()
        for cycle in cycles:
            affected_requirements.update(cycle)
        
        # 评估严重程度
        severity = self._evaluate_cycle_severity(cycles, requirements)
        
        # 生成解决建议
        resolution_suggestions = self._generate_cycle_resolution_suggestions(cycles, requirements)
        
        return CircularDependencyAnalysis(
            has_cycles=len(cycles) > 0,
            cycles=cycles,
            affected_requirements=affected_requirements,
            severity=severity,
            resolution_suggestions=resolution_suggestions
        )
    
    def analyze_impact(
        self,
        requirement_id: int,
        change_type: str = "modification",
        max_depth: int = 5
    ) -> ImpactAnalysisResult:
        """
        分析需求变更的影响范围
        
        Args:
            requirement_id: 需求ID
            change_type: 变更类型 (modification, deletion, status_change)
            max_depth: 最大分析深度
            
        Returns:
            影响分析结果
        """
        requirement = self._get_requirement(requirement_id)
        if not requirement:
            raise ValueError(f"需求ID {requirement_id} 不存在")
        
        # 分析直接影响
        direct_impacts = self._analyze_direct_impacts(requirement_id, change_type)
        
        # 分析间接影响
        indirect_impacts = self._analyze_indirect_impacts(requirement_id, change_type, max_depth)
        
        # 计算级联深度
        cascade_depth = max([0] + [impact.get('depth', 0) for impact in indirect_impacts])
        
        # 计算受影响数量
        affected_count = len(direct_impacts) + len(indirect_impacts)
        
        # 计算风险分数
        risk_score = self._calculate_impact_risk_score(
            requirement, direct_impacts, indirect_impacts, change_type
        )
        
        # 确定风险等级
        risk_level = self._determine_risk_level(risk_score)
        
        # 生成缓解策略
        mitigation_strategies = self._generate_mitigation_strategies(
            requirement, direct_impacts, indirect_impacts, risk_level
        )
        
        return ImpactAnalysisResult(
            requirement_id=requirement_id,
            direct_impacts=direct_impacts,
            indirect_impacts=indirect_impacts,
            cascade_depth=cascade_depth,
            affected_count=affected_count,
            risk_score=risk_score,
            risk_level=risk_level,
            mitigation_strategies=mitigation_strategies
        )
    
    def analyze_bottlenecks(self, project_id: int) -> BottleneckAnalysis:
        """
        分析项目中的瓶颈需求
        
        Args:
            project_id: 项目ID
            
        Returns:
            瓶颈分析结果
        """
        requirements = self.repository.get_requirements_by_project(project_id)
        requirement_ids = [req.id for req in requirements]
        
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(requirement_ids)
        
        # 识别瓶颈需求
        bottleneck_requirements = self._identify_project_bottlenecks(
            requirements, dependency_graph
        )
        
        # 计算关键路径长度
        critical_path_length = self._calculate_critical_path_length(dependency_graph)
        
        # 识别并行机会
        parallel_opportunities = self._identify_parallel_opportunities(
            requirements, dependency_graph
        )
        
        # 生成优化建议
        optimization_suggestions = self._generate_optimization_suggestions(
            bottleneck_requirements, parallel_opportunities, critical_path_length
        )
        
        return BottleneckAnalysis(
            bottleneck_requirements=bottleneck_requirements,
            critical_path_length=critical_path_length,
            parallel_opportunities=parallel_opportunities,
            optimization_suggestions=optimization_suggestions
        )
    
    def _get_requirement(self, requirement_id: int) -> Optional[Requirement]:
        """获取需求对象"""
        return self.db.query(Requirement).filter(
            Requirement.id == requirement_id
        ).first()
    
    def _build_dependency_graph(self, requirement_ids: List[int]) -> Dict[int, List[int]]:
        """构建依赖图"""
        graph = {req_id: [] for req_id in requirement_ids}
        
        for req_id in requirement_ids:
            dependencies = self.repository.get_dependencies_by_source(req_id)
            for dep in dependencies:
                if dep.target_requirement_id in requirement_ids:
                    graph[req_id].append(dep.target_requirement_id)
        
        return graph
    
    def _detect_cycles_in_graph(self, graph: Dict[int, List[int]]) -> List[List[int]]:
        """在图中检测循环"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: int, path: List[int]):
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def _identify_critical_dependencies(self, chain_data: List[Dict[str, Any]]) -> List[int]:
        """识别关键依赖"""
        critical_deps = []
        
        for item in chain_data:
            req_id = item['requirement_id']
            dep_type = item['dependency_type']
            
            # 基于依赖类型判断是否关键
            if dep_type in ['DEPENDS_ON', 'BLOCKS', 'CONFLICTS_WITH']:
                requirement = self._get_requirement(req_id)
                if requirement:
                    # 基于优先级和状态判断
                    if (requirement.priority in [Priority.CRITICAL, Priority.HIGH] or
                        requirement.status in [RequirementStatus.IN_DEVELOPMENT, RequirementStatus.TESTING]):
                        critical_deps.append(req_id)
        
        return critical_deps
    
    def _identify_bottlenecks(
        self,
        requirement_id: int,
        downstream_chain: List[Dict[str, Any]],
        upstream_chain: List[Dict[str, Any]]
    ) -> List[int]:
        """识别瓶颈需求"""
        bottlenecks = []
        
        # 统计每个需求被依赖的次数
        dependency_count = {}
        for item in downstream_chain + upstream_chain:
            req_id = item['requirement_id']
            dependency_count[req_id] = dependency_count.get(req_id, 0) + 1
        
        # 识别高度依赖的需求作为瓶颈
        avg_dependencies = sum(dependency_count.values()) / len(dependency_count) if dependency_count else 0
        
        for req_id, count in dependency_count.items():
            if count > avg_dependencies * 1.5:  # 超过平均值1.5倍
                requirement = self._get_requirement(req_id)
                if requirement and requirement.status not in [RequirementStatus.COMPLETED, RequirementStatus.DEPLOYED]:
                    bottlenecks.append(req_id)
        
        return bottlenecks
    
    def _calculate_chain_risk_level(
        self,
        requirement: Requirement,
        total_dependencies: int,
        max_depth: int,
        critical_dependencies: List[int]
    ) -> RiskLevel:
        """计算依赖链风险等级"""
        risk_score = 0.0
        
        # 基于依赖数量的风险
        if total_dependencies > 20:
            risk_score += 3.0
        elif total_dependencies > 10:
            risk_score += 2.0
        elif total_dependencies > 5:
            risk_score += 1.0
        
        # 基于深度的风险
        if max_depth > 8:
            risk_score += 2.5
        elif max_depth > 5:
            risk_score += 1.5
        elif max_depth > 3:
            risk_score += 1.0
        
        # 基于关键依赖数量的风险
        risk_score += len(critical_dependencies) * 0.5
        
        # 基于需求状态的风险
        status_factor = self.status_risk_factors.get(requirement.status, 1.0)
        risk_score *= status_factor
        
        # 基于优先级的风险
        priority_factor = self.priority_risk_factors.get(requirement.priority, 1.0)
        risk_score *= priority_factor
        
        # 确定风险等级
        if risk_score >= 8.0:
            return RiskLevel.CRITICAL
        elif risk_score >= 5.0:
            return RiskLevel.HIGH
        elif risk_score >= 2.0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_chain_recommendations(
        self,
        requirement: Requirement,
        total_dependencies: int,
        max_depth: int,
        bottlenecks: List[int],
        risk_level: RiskLevel
    ) -> List[str]:
        """生成依赖链建议"""
        recommendations = []
        
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("依赖链复杂度极高，建议重新设计需求架构")
            recommendations.append("考虑将复杂需求拆分为多个独立的子需求")
        elif risk_level == RiskLevel.HIGH:
            recommendations.append("依赖链较为复杂，建议优化依赖关系")
            recommendations.append("识别并消除不必要的依赖关系")
        
        if total_dependencies > 15:
            recommendations.append(f"依赖数量过多({total_dependencies})，建议简化依赖结构")
        
        if max_depth > 6:
            recommendations.append(f"依赖深度过深({max_depth})，可能影响开发效率")
        
        if bottlenecks:
            recommendations.append(f"发现{len(bottlenecks)}个瓶颈需求，建议优先处理这些需求")
        
        if requirement.status == RequirementStatus.DRAFT:
            recommendations.append("需求仍为草稿状态，建议尽快完善并提交评审")
        
        return recommendations
    
    def _evaluate_cycle_severity(
        self,
        cycles: List[List[int]],
        requirements: List[Requirement]
    ) -> RiskLevel:
        """评估循环依赖的严重程度"""
        if not cycles:
            return RiskLevel.LOW
        
        # 创建需求映射
        req_map = {req.id: req for req in requirements}
        
        severity_score = 0.0
        
        for cycle in cycles:
            cycle_score = len(cycle)  # 循环长度
            
            # 考虑循环中需求的优先级
            for req_id in cycle:
                if req_id in req_map:
                    req = req_map[req_id]
                    priority_factor = self.priority_risk_factors.get(req.priority, 1.0)
                    status_factor = self.status_risk_factors.get(req.status, 1.0)
                    cycle_score *= (priority_factor + status_factor) / 2
            
            severity_score += cycle_score
        
        # 基于总体严重程度确定等级
        if severity_score >= 50:
            return RiskLevel.CRITICAL
        elif severity_score >= 20:
            return RiskLevel.HIGH
        elif severity_score >= 5:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_cycle_resolution_suggestions(
        self,
        cycles: List[List[int]],
        requirements: List[Requirement]
    ) -> List[str]:
        """生成循环依赖解决建议"""
        suggestions = []
        
        if not cycles:
            return ["未发现循环依赖"]
        
        suggestions.append(f"发现{len(cycles)}个循环依赖，需要立即处理")
        
        for i, cycle in enumerate(cycles, 1):
            suggestions.append(f"循环{i}: 涉及需求 {' -> '.join(map(str, cycle))}")
            
            # 建议打破循环的策略
            if len(cycle) == 2:
                suggestions.append(f"  建议：检查需求{cycle[0]}和{cycle[1]}的依赖关系是否合理")
            else:
                suggestions.append(f"  建议：考虑重新设计需求{cycle[0]}的依赖关系")
        
        suggestions.append("通用解决策略：")
        suggestions.append("1. 重新评估依赖关系的必要性")
        suggestions.append("2. 考虑将循环依赖改为弱依赖关系")
        suggestions.append("3. 引入中间需求来打破循环")
        suggestions.append("4. 重新设计需求架构")
        
        return suggestions
    
    def _analyze_direct_impacts(self, requirement_id: int, change_type: str) -> List[Dict[str, Any]]:
        """分析直接影响"""
        impacts = []
        
        # 获取直接依赖该需求的其他需求
        target_deps = self.repository.get_dependencies_by_target(requirement_id)
        
        for dep in target_deps:
            source_req = self._get_requirement(dep.source_requirement_id)
            if source_req:
                impact_level = self._calculate_dependency_impact_level(
                    dep.dependency_type, change_type, source_req
                )
                
                impacts.append({
                    'requirement_id': source_req.id,
                    'requirement_title': source_req.title,
                    'dependency_type': dep.dependency_type.value,
                    'impact_level': impact_level,
                    'description': f"需求{source_req.id}通过{dep.dependency_type.value}关系受到影响",
                    'depth': 1
                })
        
        return impacts
    
    def _analyze_indirect_impacts(
        self,
        requirement_id: int,
        change_type: str,
        max_depth: int
    ) -> List[Dict[str, Any]]:
        """分析间接影响"""
        impacts = []
        visited = set()
        
        def analyze_level(req_id: int, depth: int):
            if depth > max_depth or req_id in visited:
                return
            
            visited.add(req_id)
            target_deps = self.repository.get_dependencies_by_target(req_id)
            
            for dep in target_deps:
                source_req = self._get_requirement(dep.source_requirement_id)
                if source_req and depth > 1:  # 深度大于1的是间接影响
                    impact_level = self._calculate_dependency_impact_level(
                        dep.dependency_type, change_type, source_req, is_indirect=True
                    )
                    
                    impacts.append({
                        'requirement_id': source_req.id,
                        'requirement_title': source_req.title,
                        'dependency_type': dep.dependency_type.value,
                        'impact_level': impact_level,
                        'description': f"通过{depth}级依赖链间接受影响",
                        'depth': depth
                    })
                
                analyze_level(dep.source_requirement_id, depth + 1)
        
        analyze_level(requirement_id, 1)
        return impacts
    
    def _calculate_dependency_impact_level(
        self,
        dependency_type: DependencyType,
        change_type: str,
        affected_requirement: Requirement,
        is_indirect: bool = False
    ) -> str:
        """计算依赖影响程度"""
        base_impact = {
            DependencyType.DEPENDS_ON: 3,
            DependencyType.BLOCKS: 3,
            DependencyType.CONFLICTS_WITH: 2,
            DependencyType.REPLACES: 2,
            DependencyType.RELATES_TO: 1,
            DependencyType.DUPLICATES: 1
        }.get(dependency_type, 1)
        
        # 变更类型影响系数
        change_factors = {
            'deletion': 1.5,
            'modification': 1.0,
            'status_change': 0.8
        }
        
        impact_score = base_impact * change_factors.get(change_type, 1.0)
        
        # 间接影响降低影响程度
        if is_indirect:
            impact_score *= 0.7
        
        # 基于受影响需求的优先级调整
        priority_factor = self.priority_risk_factors.get(affected_requirement.priority, 1.0)
        impact_score *= priority_factor
        
        # 确定影响等级
        if impact_score >= 4.0:
            return "HIGH"
        elif impact_score >= 2.0:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_impact_risk_score(
        self,
        requirement: Requirement,
        direct_impacts: List[Dict[str, Any]],
        indirect_impacts: List[Dict[str, Any]],
        change_type: str
    ) -> float:
        """计算影响风险分数"""
        risk_score = 0.0
        
        # 直接影响分数
        for impact in direct_impacts:
            if impact['impact_level'] == 'HIGH':
                risk_score += 3.0
            elif impact['impact_level'] == 'MEDIUM':
                risk_score += 2.0
            else:
                risk_score += 1.0
        
        # 间接影响分数（权重较低）
        for impact in indirect_impacts:
            if impact['impact_level'] == 'HIGH':
                risk_score += 1.5
            elif impact['impact_level'] == 'MEDIUM':
                risk_score += 1.0
            else:
                risk_score += 0.5
        
        # 基于需求自身特征调整
        status_factor = self.status_risk_factors.get(requirement.status, 1.0)
        priority_factor = self.priority_risk_factors.get(requirement.priority, 1.0)
        
        risk_score *= (status_factor + priority_factor) / 2
        
        return risk_score
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """确定风险等级"""
        if risk_score >= 15.0:
            return RiskLevel.CRITICAL
        elif risk_score >= 8.0:
            return RiskLevel.HIGH
        elif risk_score >= 3.0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_mitigation_strategies(
        self,
        requirement: Requirement,
        direct_impacts: List[Dict[str, Any]],
        indirect_impacts: List[Dict[str, Any]],
        risk_level: RiskLevel
    ) -> List[str]:
        """生成缓解策略"""
        strategies = []
        
        if risk_level == RiskLevel.CRITICAL:
            strategies.append("风险等级极高，建议暂停变更并重新评估")
            strategies.append("召开紧急评审会议，制定详细的风险缓解计划")
        elif risk_level == RiskLevel.HIGH:
            strategies.append("风险等级较高，建议制定详细的变更计划")
            strategies.append("通知所有受影响需求的负责人")
        
        if direct_impacts:
            high_impact_count = sum(1 for imp in direct_impacts if imp['impact_level'] == 'HIGH')
            if high_impact_count > 0:
                strategies.append(f"有{high_impact_count}个需求受到高度影响，建议优先处理")
        
        if indirect_impacts:
            strategies.append(f"有{len(indirect_impacts)}个需求受到间接影响，建议评估影响程度")
        
        # 基于需求状态的建议
        if requirement.status == RequirementStatus.IN_DEVELOPMENT:
            strategies.append("需求正在开发中，变更可能影响开发进度")
        elif requirement.status == RequirementStatus.TESTING:
            strategies.append("需求正在测试中，变更可能需要重新测试")
        
        if not strategies:
            strategies.append("影响范围可控，可以正常进行变更")
        
        return strategies
    
    def _identify_project_bottlenecks(
        self,
        requirements: List[Requirement],
        dependency_graph: Dict[int, List[int]]
    ) -> List[Dict[str, Any]]:
        """识别项目瓶颈需求"""
        bottlenecks = []
        
        # 计算每个需求的入度（被依赖次数）
        in_degree = {req.id: 0 for req in requirements}
        for source, targets in dependency_graph.items():
            for target in targets:
                in_degree[target] += 1
        
        # 计算平均入度
        avg_in_degree = sum(in_degree.values()) / len(in_degree) if in_degree else 0
        
        # 识别高入度的需求作为瓶颈
        for req in requirements:
            if in_degree[req.id] > avg_in_degree * 1.5:  # 超过平均值1.5倍
                bottleneck_score = self._calculate_bottleneck_score(req, in_degree[req.id])
                
                bottlenecks.append({
                    'requirement_id': req.id,
                    'requirement_title': req.title,
                    'dependency_count': in_degree[req.id],
                    'status': req.status.value if req.status else 'DRAFT',
                    'priority': req.priority.value if req.priority else 'MEDIUM',
                    'bottleneck_score': bottleneck_score,
                    'risk_level': self._determine_bottleneck_risk_level(bottleneck_score)
                })
        
        # 按瓶颈分数排序
        bottlenecks.sort(key=lambda x: x['bottleneck_score'], reverse=True)
        
        return bottlenecks
    
    def _calculate_bottleneck_score(self, requirement: Requirement, dependency_count: int) -> float:
        """计算瓶颈分数"""
        score = dependency_count * 2.0  # 基础分数
        
        # 状态风险系数
        status_factor = self.status_risk_factors.get(requirement.status, 1.0)
        score *= status_factor
        
        # 优先级系数
        priority_factor = self.priority_risk_factors.get(requirement.priority, 1.0)
        score *= priority_factor
        
        return score
    
    def _determine_bottleneck_risk_level(self, bottleneck_score: float) -> str:
        """确定瓶颈风险等级"""
        if bottleneck_score >= 20.0:
            return "CRITICAL"
        elif bottleneck_score >= 10.0:
            return "HIGH"
        elif bottleneck_score >= 5.0:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _calculate_critical_path_length(self, dependency_graph: Dict[int, List[int]]) -> int:
        """计算关键路径长度"""
        # 使用拓扑排序计算最长路径
        in_degree = {node: 0 for node in dependency_graph}
        for source, targets in dependency_graph.items():
            for target in targets:
                if target in in_degree:
                    in_degree[target] += 1
        
        # 计算每个节点的最长路径
        longest_path = {node: 0 for node in dependency_graph}
        queue = [node for node, degree in in_degree.items() if degree == 0]
        
        while queue:
            current = queue.pop(0)
            for neighbor in dependency_graph.get(current, []):
                longest_path[neighbor] = max(
                    longest_path[neighbor],
                    longest_path[current] + 1
                )
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return max(longest_path.values()) if longest_path else 0
    
    def _identify_parallel_opportunities(
        self,
        requirements: List[Requirement],
        dependency_graph: Dict[int, List[int]]
    ) -> List[Dict[str, Any]]:
        """识别并行开发机会"""
        opportunities = []
        
        # 找到没有依赖关系的需求组
        independent_groups = []
        processed = set()
        
        for req in requirements:
            if req.id in processed:
                continue
            
            # 找到与当前需求无依赖关系的其他需求
            independent_reqs = [req]
            processed.add(req.id)
            
            for other_req in requirements:
                if (other_req.id not in processed and
                    not self._has_dependency_path(dependency_graph, req.id, other_req.id) and
                    not self._has_dependency_path(dependency_graph, other_req.id, req.id)):
                    independent_reqs.append(other_req)
                    processed.add(other_req.id)
            
            if len(independent_reqs) > 1:
                independent_groups.append(independent_reqs)
        
        # 为每个独立组生成并行机会
        for group in independent_groups:
            if len(group) >= 2:
                opportunities.append({
                    'group_id': f"parallel_group_{len(opportunities) + 1}",
                    'requirements': [
                        {
                            'id': req.id,
                            'title': req.title,
                            'status': req.status.value if req.status else 'DRAFT',
                            'estimated_effort': float(req.estimated_effort) if req.estimated_effort else 0
                        }
                        for req in group
                    ],
                    'total_effort': sum(
                        float(req.estimated_effort) if req.estimated_effort else 0
                        for req in group
                    ),
                    'parallel_potential': len(group)
                })
        
        return opportunities
    
    def _has_dependency_path(
        self,
        graph: Dict[int, List[int]],
        start: int,
        end: int,
        visited: Optional[Set[int]] = None
    ) -> bool:
        """检查两个节点间是否存在依赖路径"""
        if visited is None:
            visited = set()
        
        if start == end:
            return True
        
        if start in visited:
            return False
        
        visited.add(start)
        
        for neighbor in graph.get(start, []):
            if self._has_dependency_path(graph, neighbor, end, visited.copy()):
                return True
        
        return False
    
    def _generate_optimization_suggestions(
        self,
        bottlenecks: List[Dict[str, Any]],
        parallel_opportunities: List[Dict[str, Any]],
        critical_path_length: int
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        if bottlenecks:
            suggestions.append(f"发现{len(bottlenecks)}个瓶颈需求，建议优先处理：")
            for bottleneck in bottlenecks[:3]:  # 只显示前3个
                suggestions.append(
                    f"  - 需求{bottleneck['requirement_id']}: {bottleneck['requirement_title']} "
                    f"(被{bottleneck['dependency_count']}个需求依赖)"
                )
        
        if parallel_opportunities:
            total_parallel_reqs = sum(opp['parallel_potential'] for opp in parallel_opportunities)
            suggestions.append(f"发现{len(parallel_opportunities)}个并行开发机会，涉及{total_parallel_reqs}个需求")
            suggestions.append("建议合理安排资源，同时开发独立的需求")
        
        if critical_path_length > 10:
            suggestions.append(f"关键路径长度为{critical_path_length}，较长，建议：")
            suggestions.append("  - 检查是否可以简化依赖关系")
            suggestions.append("  - 考虑将长链需求拆分为更小的需求")
        elif critical_path_length > 5:
            suggestions.append(f"关键路径长度为{critical_path_length}，建议关注关键路径上的需求进度")
        
        if not suggestions:
            suggestions.append("项目依赖结构良好，无明显优化点")
        
        return suggestions