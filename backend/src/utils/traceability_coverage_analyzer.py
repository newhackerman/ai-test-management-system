"""
追溯覆盖率分析器

本模块实现追溯覆盖率的分析功能，包括：
- 需求追溯覆盖率计算
- 追溯矩阵生成和分析
- 覆盖率报告生成
- 覆盖率趋势分析
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from collections import defaultdict

from ..models.requirement import (
    Requirement, RequirementTraceabilityLink, TraceabilityLinkType,
    RequirementStatus, RequirementType
)
from ..models.project import Project
from ..utils.logger import get_logger

logger = get_logger(__name__)

class CoverageMetrics:
    """覆盖率指标"""
    def __init__(self):
        self.total_requirements: int = 0
        self.covered_requirements: int = 0
        self.coverage_rate: float = 0.0
        self.uncovered_requirements: List[Dict[str, Any]] = []
        self.coverage_by_type: Dict[str, float] = {}
        self.coverage_by_priority: Dict[str, float] = {}
        self.coverage_by_status: Dict[str, float] = {}

class TraceabilityMatrix:
    """追溯矩阵"""
    def __init__(self):
        self.matrix_type: str = ""
        self.requirements: List[Dict[str, Any]] = []
        self.targets: List[Dict[str, Any]] = []
        self.matrix_data: Dict[str, Dict[str, bool]] = {}
        self.coverage_stats: Dict[str, Any] = {}
        self.gaps: List[Dict[str, Any]] = []

class CoverageReport:
    """覆盖率报告"""
    def __init__(self):
        self.project_id: int = 0
        self.project_name: str = ""
        self.generated_at: datetime = datetime.utcnow()
        self.overall_metrics: CoverageMetrics = CoverageMetrics()
        self.matrices: List[TraceabilityMatrix] = []
        self.recommendations: List[str] = []
        self.trends: Dict[str, Any] = {}

class TraceabilityCoverageAnalyzer:
    """追溯覆盖率分析器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_project_coverage(self, project_id: int) -> CoverageReport:
        """分析项目追溯覆盖率"""
        try:
            report = CoverageReport()
            report.project_id = project_id
            
            # 获取项目信息
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                report.project_name = project.name
            
            # 1. 计算整体覆盖率指标
            report.overall_metrics = self._calculate_overall_metrics(project_id)
            
            # 2. 生成各类追溯矩阵
            report.matrices = self._generate_traceability_matrices(project_id)
            
            # 3. 分析覆盖率趋势
            report.trends = self._analyze_coverage_trends(project_id)
            
            # 4. 生成改进建议
            report.recommendations = self._generate_coverage_recommendations(report)
            
            logger.info(f"项目 {project_id} 追溯覆盖率分析完成")
            return report
            
        except Exception as e:
            logger.error(f"分析项目追溯覆盖率失败: {str(e)}")
            raise
    
    def analyze_requirement_coverage(self, requirement_id: int) -> Dict[str, Any]:
        """分析单个需求的追溯覆盖率"""
        try:
            requirement = self.db.query(Requirement).filter(
                Requirement.id == requirement_id
            ).first()
            
            if not requirement:
                raise ValueError("需求不存在")
            
            coverage = {
                "requirement_id": requirement_id,
                "requirement_title": requirement.title,
                "requirement_status": requirement.status.value if requirement.status else None,
                "coverage_details": {},
                "missing_links": [],
                "recommendations": []
            }
            
            # 分析各类型的追溯覆盖
            coverage["coverage_details"] = self._analyze_requirement_coverage_details(requirement_id)
            
            # 识别缺失的追溯链接
            coverage["missing_links"] = self._identify_missing_requirement_links(requirement_id)
            
            # 生成针对性建议
            coverage["recommendations"] = self._generate_requirement_recommendations(
                requirement, coverage["coverage_details"], coverage["missing_links"]
            )
            
            return coverage
            
        except Exception as e:
            logger.error(f"分析需求追溯覆盖率失败: {str(e)}")
            raise
    
    def generate_coverage_matrix(
        self,
        project_id: int,
        matrix_type: str = "requirement_to_test"
    ) -> TraceabilityMatrix:
        """生成追溯覆盖矩阵"""
        try:
            matrix = TraceabilityMatrix()
            matrix.matrix_type = matrix_type
            
            # 获取需求列表
            requirements = self.db.query(Requirement).filter(
                Requirement.project_id == project_id
            ).order_by(Requirement.requirement_code).all()
            
            matrix.requirements = [
                {
                    "id": req.id,
                    "code": req.requirement_code,
                    "title": req.title,
                    "type": req.requirement_type.value if req.requirement_type else None,
                    "priority": req.priority.value if req.priority else None,
                    "status": req.status.value if req.status else None
                }
                for req in requirements
            ]
            
            # 根据矩阵类型获取目标对象和链接
            if matrix_type == "requirement_to_test":
                matrix.targets = self._get_test_cases_for_matrix(project_id)
                links = self._get_requirement_test_links(project_id)
            elif matrix_type == "requirement_to_task":
                matrix.targets = self._get_tasks_for_matrix(project_id)
                links = self._get_requirement_task_links(project_id)
            elif matrix_type == "requirement_to_design":
                matrix.targets = self._get_designs_for_matrix(project_id)
                links = self._get_requirement_design_links(project_id)
            else:
                raise ValueError(f"不支持的矩阵类型: {matrix_type}")
            
            # 构建矩阵数据
            matrix.matrix_data = self._build_matrix_data(matrix.requirements, matrix.targets, links)
            
            # 计算覆盖率统计
            matrix.coverage_stats = self._calculate_matrix_coverage_stats(matrix.matrix_data)
            
            # 识别覆盖缺口
            matrix.gaps = self._identify_coverage_gaps(matrix)
            
            return matrix
            
        except Exception as e:
            logger.error(f"生成追溯覆盖矩阵失败: {str(e)}")
            raise
    
    def _calculate_overall_metrics(self, project_id: int) -> CoverageMetrics:
        """计算整体覆盖率指标"""
        metrics = CoverageMetrics()
        
        # 获取项目所有需求
        requirements = self.db.query(Requirement).filter(
            Requirement.project_id == project_id
        ).all()
        
        metrics.total_requirements = len(requirements)
        
        if metrics.total_requirements == 0:
            return metrics
        
        # 计算有追溯链接的需求数量
        covered_requirement_ids = set()
        
        # 获取所有追溯链接
        links = self.db.query(RequirementTraceabilityLink).filter(
            or_(
                and_(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id.in_([req.id for req in requirements])
                ),
                and_(
                    RequirementTraceabilityLink.target_type == "requirement",
                    RequirementTraceabilityLink.target_id.in_([req.id for req in requirements])
                )
            )
        ).all()
        
        for link in links:
            if link.source_type == "requirement":
                covered_requirement_ids.add(link.source_id)
            if link.target_type == "requirement":
                covered_requirement_ids.add(link.target_id)
        
        metrics.covered_requirements = len(covered_requirement_ids)
        metrics.coverage_rate = metrics.covered_requirements / metrics.total_requirements
        
        # 识别未覆盖的需求
        uncovered_ids = set(req.id for req in requirements) - covered_requirement_ids
        metrics.uncovered_requirements = [
            {
                "id": req.id,
                "code": req.requirement_code,
                "title": req.title,
                "type": req.requirement_type.value if req.requirement_type else None,
                "priority": req.priority.value if req.priority else None,
                "status": req.status.value if req.status else None
            }
            for req in requirements if req.id in uncovered_ids
        ]
        
        # 按类型计算覆盖率
        metrics.coverage_by_type = self._calculate_coverage_by_attribute(
            requirements, covered_requirement_ids, "requirement_type"
        )
        
        # 按优先级计算覆盖率
        metrics.coverage_by_priority = self._calculate_coverage_by_attribute(
            requirements, covered_requirement_ids, "priority"
        )
        
        # 按状态计算覆盖率
        metrics.coverage_by_status = self._calculate_coverage_by_attribute(
            requirements, covered_requirement_ids, "status"
        )
        
        return metrics
    
    def _calculate_coverage_by_attribute(
        self,
        requirements: List[Requirement],
        covered_ids: set,
        attribute: str
    ) -> Dict[str, float]:
        """按属性计算覆盖率"""
        coverage_by_attr = {}
        attr_counts = defaultdict(int)
        attr_covered = defaultdict(int)
        
        for req in requirements:
            attr_value = getattr(req, attribute)
            if attr_value:
                attr_key = attr_value.value if hasattr(attr_value, 'value') else str(attr_value)
                attr_counts[attr_key] += 1
                if req.id in covered_ids:
                    attr_covered[attr_key] += 1
        
        for attr_key, total in attr_counts.items():
            covered = attr_covered.get(attr_key, 0)
            coverage_by_attr[attr_key] = covered / total if total > 0 else 0.0
        
        return coverage_by_attr
    
    def _generate_traceability_matrices(self, project_id: int) -> List[TraceabilityMatrix]:
        """生成各类追溯矩阵"""
        matrices = []
        
        matrix_types = [
            "requirement_to_test",
            "requirement_to_task",
            "requirement_to_design"
        ]
        
        for matrix_type in matrix_types:
            try:
                matrix = self.generate_coverage_matrix(project_id, matrix_type)
                matrices.append(matrix)
            except Exception as e:
                logger.warning(f"生成 {matrix_type} 矩阵失败: {str(e)}")
        
        return matrices
    
    def _analyze_coverage_trends(self, project_id: int) -> Dict[str, Any]:
        """分析覆盖率趋势"""
        trends = {
            "historical_coverage": [],
            "coverage_growth_rate": 0.0,
            "prediction": {}
        }
        
        try:
            # 获取历史覆盖率数据（按月统计）
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=365)  # 过去一年
            
            monthly_data = []
            current_date = start_date
            
            while current_date <= end_date:
                month_end = min(
                    current_date.replace(day=28) + timedelta(days=4),
                    end_date
                ).replace(day=1) - timedelta(days=1)
                
                # 计算该月的覆盖率
                coverage_rate = self._calculate_historical_coverage(project_id, month_end)
                
                monthly_data.append({
                    "date": month_end.strftime("%Y-%m"),
                    "coverage_rate": coverage_rate
                })
                
                # 移动到下个月
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            
            trends["historical_coverage"] = monthly_data
            
            # 计算增长率
            if len(monthly_data) >= 2:
                first_rate = monthly_data[0]["coverage_rate"]
                last_rate = monthly_data[-1]["coverage_rate"]
                if first_rate > 0:
                    trends["coverage_growth_rate"] = (last_rate - first_rate) / first_rate
            
        except Exception as e:
            logger.warning(f"分析覆盖率趋势失败: {str(e)}")
        
        return trends
    
    def _calculate_historical_coverage(self, project_id: int, end_date: datetime) -> float:
        """计算历史覆盖率"""
        try:
            # 获取指定日期前的需求数量
            total_requirements = self.db.query(Requirement).filter(
                Requirement.project_id == project_id,
                Requirement.created_at <= end_date
            ).count()
            
            if total_requirements == 0:
                return 0.0
            
            # 获取指定日期前有追溯链接的需求数量
            covered_requirements = self.db.query(Requirement.id).filter(
                Requirement.project_id == project_id,
                Requirement.created_at <= end_date
            ).join(
                RequirementTraceabilityLink,
                or_(
                    and_(
                        RequirementTraceabilityLink.source_type == "requirement",
                        RequirementTraceabilityLink.source_id == Requirement.id,
                        RequirementTraceabilityLink.created_at <= end_date
                    ),
                    and_(
                        RequirementTraceabilityLink.target_type == "requirement",
                        RequirementTraceabilityLink.target_id == Requirement.id,
                        RequirementTraceabilityLink.created_at <= end_date
                    )
                )
            ).distinct().count()
            
            return covered_requirements / total_requirements
            
        except Exception as e:
            logger.warning(f"计算历史覆盖率失败: {str(e)}")
            return 0.0
    
    def _analyze_requirement_coverage_details(self, requirement_id: int) -> Dict[str, Any]:
        """分析需求的详细覆盖情况"""
        details = {
            "upstream_coverage": {},
            "downstream_coverage": {},
            "bidirectional_coverage": {}
        }
        
        # 上游覆盖（需求来源）
        upstream_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.target_type == "requirement",
            RequirementTraceabilityLink.target_id == requirement_id
        ).all()
        
        upstream_types = set(link.source_type for link in upstream_links)
        details["upstream_coverage"] = {
            "business_requirement": "business_requirement" in upstream_types,
            "parent_requirement": any(
                link.source_type == "requirement" for link in upstream_links
            ),
            "total_links": len(upstream_links)
        }
        
        # 下游覆盖（实现追踪）
        downstream_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement_id
        ).all()
        
        downstream_types = set(link.target_type for link in downstream_links)
        details["downstream_coverage"] = {
            "design": "design" in downstream_types,
            "task": "task" in downstream_types,
            "test_case": "test_case" in downstream_types,
            "child_requirement": any(
                link.target_type == "requirement" for link in downstream_links
            ),
            "total_links": len(downstream_links)
        }
        
        # 双向覆盖
        details["bidirectional_coverage"] = {
            "has_upstream": len(upstream_links) > 0,
            "has_downstream": len(downstream_links) > 0,
            "is_fully_traced": len(upstream_links) > 0 and len(downstream_links) > 0
        }
        
        return details
    
    def _identify_missing_requirement_links(self, requirement_id: int) -> List[Dict[str, Any]]:
        """识别需求缺失的追溯链接"""
        missing_links = []
        
        requirement = self.db.query(Requirement).filter(
            Requirement.id == requirement_id
        ).first()
        
        if not requirement:
            return missing_links
        
        # 检查是否缺少测试追溯
        test_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement_id,
            RequirementTraceabilityLink.target_type == "test_case"
        ).count()
        
        if test_links == 0:
            missing_links.append({
                "type": "test_case",
                "description": "缺少测试用例追溯",
                "priority": "high",
                "recommendation": "为此需求创建相应的测试用例并建立追溯链接"
            })
        
        # 检查是否缺少任务追溯
        task_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement_id,
            RequirementTraceabilityLink.target_type == "task"
        ).count()
        
        if task_links == 0 and requirement.status in [
            RequirementStatus.APPROVED,
            RequirementStatus.IN_DEVELOPMENT,
            RequirementStatus.TESTING,
            RequirementStatus.COMPLETED
        ]:
            missing_links.append({
                "type": "task",
                "description": "缺少开发任务追溯",
                "priority": "medium",
                "recommendation": "为此需求创建开发任务并建立追溯链接"
            })
        
        # 检查是否缺少设计追溯
        design_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement_id,
            RequirementTraceabilityLink.target_type == "design"
        ).count()
        
        if design_links == 0 and requirement.requirement_type in [
            RequirementType.FUNCTIONAL,
            RequirementType.INTERFACE
        ]:
            missing_links.append({
                "type": "design",
                "description": "缺少设计文档追溯",
                "priority": "medium",
                "recommendation": "为此需求创建设计文档并建立追溯链接"
            })
        
        return missing_links
    
    def _generate_requirement_recommendations(
        self,
        requirement: Requirement,
        coverage_details: Dict[str, Any],
        missing_links: List[Dict[str, Any]]
    ) -> List[str]:
        """生成需求追溯建议"""
        recommendations = []
        
        # 基于缺失链接生成建议
        for missing in missing_links:
            recommendations.append(missing["recommendation"])
        
        # 基于需求状态生成建议
        if requirement.status == RequirementStatus.DRAFT:
            recommendations.append("需求仍为草稿状态，建议完善后再建立追溯链接")
        elif requirement.status == RequirementStatus.APPROVED:
            if not coverage_details["downstream_coverage"]["task"]:
                recommendations.append("需求已批准但缺少开发任务，建议创建相应任务")
        
        # 基于覆盖情况生成建议
        if not coverage_details["bidirectional_coverage"]["has_upstream"]:
            recommendations.append("缺少上游追溯，建议明确需求来源")
        
        if not coverage_details["bidirectional_coverage"]["has_downstream"]:
            recommendations.append("缺少下游追溯，建议建立实现追踪")
        
        return recommendations
    
    def _get_test_cases_for_matrix(self, project_id: int) -> List[Dict[str, Any]]:
        """获取测试用例列表（用于矩阵）"""
        # 这里应该调用测试管理模块的接口
        # 暂时返回模拟数据
        return []
    
    def _get_tasks_for_matrix(self, project_id: int) -> List[Dict[str, Any]]:
        """获取任务列表（用于矩阵）"""
        # 这里应该调用任务管理模块的接口
        # 暂时返回模拟数据
        return []
    
    def _get_designs_for_matrix(self, project_id: int) -> List[Dict[str, Any]]:
        """获取设计文档列表（用于矩阵）"""
        # 这里应该调用设计管理模块的接口
        # 暂时返回模拟数据
        return []
    
    def _get_requirement_test_links(self, project_id: int) -> List[Dict[str, Any]]:
        """获取需求到测试用例的链接"""
        links = self.db.query(RequirementTraceabilityLink).join(
            Requirement,
            and_(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == Requirement.id
            )
        ).filter(
            Requirement.project_id == project_id,
            RequirementTraceabilityLink.target_type == "test_case"
        ).all()
        
        return [link.to_dict() for link in links]
    
    def _get_requirement_task_links(self, project_id: int) -> List[Dict[str, Any]]:
        """获取需求到任务的链接"""
        links = self.db.query(RequirementTraceabilityLink).join(
            Requirement,
            and_(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == Requirement.id
            )
        ).filter(
            Requirement.project_id == project_id,
            RequirementTraceabilityLink.target_type == "task"
        ).all()
        
        return [link.to_dict() for link in links]
    
    def _get_requirement_design_links(self, project_id: int) -> List[Dict[str, Any]]:
        """获取需求到设计的链接"""
        links = self.db.query(RequirementTraceabilityLink).join(
            Requirement,
            and_(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == Requirement.id
            )
        ).filter(
            Requirement.project_id == project_id,
            RequirementTraceabilityLink.target_type == "design"
        ).all()
        
        return [link.to_dict() for link in links]
    
    def _build_matrix_data(
        self,
        requirements: List[Dict[str, Any]],
        targets: List[Dict[str, Any]],
        links: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, bool]]:
        """构建矩阵数据"""
        matrix_data = {}
        
        # 创建链接映射
        link_map = set()
        for link in links:
            key = f"{link['source_id']}_{link['target_id']}"
            link_map.add(key)
        
        # 构建矩阵
        for req in requirements:
            req_id = str(req["id"])
            matrix_data[req_id] = {}
            
            for target in targets:
                target_id = str(target["id"])
                key = f"{req['id']}_{target['id']}"
                matrix_data[req_id][target_id] = key in link_map
        
        return matrix_data
    
    def _calculate_matrix_coverage_stats(self, matrix_data: Dict[str, Dict[str, bool]]) -> Dict[str, Any]:
        """计算矩阵覆盖率统计"""
        total_cells = 0
        covered_cells = 0
        
        for req_id, targets in matrix_data.items():
            for target_id, is_linked in targets.items():
                total_cells += 1
                if is_linked:
                    covered_cells += 1
        
        coverage_rate = covered_cells / total_cells if total_cells > 0 else 0.0
        
        return {
            "total_cells": total_cells,
            "covered_cells": covered_cells,
            "uncovered_cells": total_cells - covered_cells,
            "coverage_rate": coverage_rate,
            "coverage_percentage": f"{coverage_rate:.1%}"
        }
    
    def _identify_coverage_gaps(self, matrix: TraceabilityMatrix) -> List[Dict[str, Any]]:
        """识别覆盖缺口"""
        gaps = []
        
        for req_id, targets in matrix.matrix_data.items():
            uncovered_targets = [
                target_id for target_id, is_linked in targets.items() if not is_linked
            ]
            
            if uncovered_targets:
                # 找到对应的需求信息
                req_info = next(
                    (req for req in matrix.requirements if str(req["id"]) == req_id),
                    None
                )
                
                if req_info:
                    gaps.append({
                        "requirement_id": int(req_id),
                        "requirement_code": req_info.get("code", ""),
                        "requirement_title": req_info.get("title", ""),
                        "requirement_priority": req_info.get("priority", ""),
                        "uncovered_count": len(uncovered_targets),
                        "uncovered_targets": uncovered_targets
                    })
        
        # 按优先级和未覆盖数量排序
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "OPTIONAL": 4}
        gaps.sort(key=lambda x: (
            priority_order.get(x["requirement_priority"], 5),
            -x["uncovered_count"]
        ))
        
        return gaps
    
    def _generate_coverage_recommendations(self, report: CoverageReport) -> List[str]:
        """生成覆盖率改进建议"""
        recommendations = []
        
        # 基于整体覆盖率生成建议
        overall_rate = report.overall_metrics.coverage_rate
        if overall_rate < 0.5:
            recommendations.append(
                f"整体追溯覆盖率较低 ({overall_rate:.1%})，建议优先完善核心需求的追溯链接"
            )
        elif overall_rate < 0.8:
            recommendations.append(
                f"整体追溯覆盖率为 {overall_rate:.1%}，建议继续完善追溯链接以达到80%以上"
            )
        
        # 基于未覆盖需求生成建议
        uncovered_count = len(report.overall_metrics.uncovered_requirements)
        if uncovered_count > 0:
            high_priority_uncovered = [
                req for req in report.overall_metrics.uncovered_requirements
                if req["priority"] in ["CRITICAL", "HIGH"]
            ]
            
            if high_priority_uncovered:
                recommendations.append(
                    f"有 {len(high_priority_uncovered)} 个高优先级需求缺少追溯链接，建议优先处理"
                )
        
        # 基于矩阵覆盖率生成建议
        for matrix in report.matrices:
            matrix_rate = matrix.coverage_stats.get("coverage_rate", 0.0)
            if matrix_rate < 0.6:
                matrix_name = {
                    "requirement_to_test": "需求到测试用例",
                    "requirement_to_task": "需求到开发任务",
                    "requirement_to_design": "需求到设计文档"
                }.get(matrix.matrix_type, matrix.matrix_type)
                
                recommendations.append(
                    f"{matrix_name}的追溯覆盖率较低 ({matrix_rate:.1%})，建议加强此类追溯链接"
                )
        
        # 基于趋势生成建议
        growth_rate = report.trends.get("coverage_growth_rate", 0.0)
        if growth_rate < 0:
            recommendations.append("追溯覆盖率呈下降趋势，建议检查追溯链接的维护情况")
        elif growth_rate < 0.1:
            recommendations.append("追溯覆盖率增长缓慢，建议加强追溯管理流程")
        
        return recommendations