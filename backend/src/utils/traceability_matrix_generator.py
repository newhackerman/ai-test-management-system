"""
追溯矩阵生成器

本模块实现追溯矩阵的生成功能，包括：
- 需求追溯矩阵生成
- 矩阵数据分析
- 矩阵可视化数据准备
- 矩阵导出功能
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from collections import defaultdict
import json

from ..models.requirement import (
    Requirement, RequirementTraceabilityLink, TraceabilityLinkType,
    RequirementStatus, RequirementType, Priority
)
from ..models.project import Project
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MatrixCell:
    """矩阵单元格"""
    def __init__(self, requirement_id: int, target_id: int):
        self.requirement_id = requirement_id
        self.target_id = target_id
        self.is_linked = False
        self.link_types: List[str] = []
        self.link_descriptions: List[str] = []
        self.link_count = 0
        self.last_updated: Optional[datetime] = None

class TraceabilityMatrix:
    """追溯矩阵"""
    def __init__(self, project_id: int, matrix_type: str):
        self.project_id = project_id
        self.matrix_type = matrix_type
        self.generated_at = datetime.utcnow()
        
        # 矩阵数据
        self.requirements: List[Dict[str, Any]] = []
        self.targets: List[Dict[str, Any]] = []
        self.matrix_cells: Dict[Tuple[int, int], MatrixCell] = {}
        
        # 统计信息
        self.total_cells = 0
        self.linked_cells = 0
        self.coverage_rate = 0.0
        
        # 分析结果
        self.coverage_by_requirement: Dict[int, float] = {}
        self.coverage_by_target: Dict[int, float] = {}
        self.gaps: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []

class TraceabilityMatrixGenerator:
    """追溯矩阵生成器"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 支持的矩阵类型
        self.supported_matrix_types = {
            "requirement_to_test": {
                "name": "需求到测试用例矩阵",
                "source_type": "requirement",
                "target_type": "test_case",
                "link_types": [TraceabilityLinkType.TESTS, TraceabilityLinkType.VALIDATES]
            },
            "requirement_to_task": {
                "name": "需求到开发任务矩阵",
                "source_type": "requirement",
                "target_type": "task",
                "link_types": [TraceabilityLinkType.IMPLEMENTS]
            },
            "requirement_to_design": {
                "name": "需求到设计文档矩阵",
                "source_type": "requirement",
                "target_type": "design",
                "link_types": [TraceabilityLinkType.IMPLEMENTS]
            },
            "requirement_to_requirement": {
                "name": "需求依赖关系矩阵",
                "source_type": "requirement",
                "target_type": "requirement",
                "link_types": [TraceabilityLinkType.DERIVES_FROM, TraceabilityLinkType.REFINES]
            }
        }
    
    def generate_matrix(self, project_id: int, matrix_type: str, filters: Dict[str, Any] = None) -> TraceabilityMatrix:
        """生成追溯矩阵"""
        try:
            if matrix_type not in self.supported_matrix_types:
                raise ValueError(f"不支持的矩阵类型: {matrix_type}")
            
            matrix = TraceabilityMatrix(project_id, matrix_type)
            matrix_config = self.supported_matrix_types[matrix_type]
            
            # 1. 获取需求数据
            matrix.requirements = self._get_requirements_for_matrix(project_id, filters)
            
            # 2. 获取目标对象数据
            matrix.targets = self._get_targets_for_matrix(project_id, matrix_type, filters)
            
            # 3. 获取追溯链接数据
            links = self._get_traceability_links(project_id, matrix_config)
            
            # 4. 构建矩阵单元格
            matrix.matrix_cells = self._build_matrix_cells(matrix.requirements, matrix.targets, links)
            
            # 5. 计算统计信息
            self._calculate_matrix_statistics(matrix)
            
            # 6. 分析覆盖率
            self._analyze_coverage_by_dimension(matrix)
            
            # 7. 识别覆盖缺口
            matrix.gaps = self._identify_coverage_gaps(matrix)
            
            # 8. 生成改进建议
            matrix.recommendations = self._generate_matrix_recommendations(matrix)
            
            logger.info(f"生成追溯矩阵完成: {matrix_type}, 项目ID: {project_id}")
            return matrix
            
        except Exception as e:
            logger.error(f"生成追溯矩阵失败: {str(e)}")
            raise
    
    def generate_multiple_matrices(
        self,
        project_id: int,
        matrix_types: List[str] = None,
        filters: Dict[str, Any] = None
    ) -> Dict[str, TraceabilityMatrix]:
        """生成多个追溯矩阵"""
        if matrix_types is None:
            matrix_types = list(self.supported_matrix_types.keys())
        
        matrices = {}
        for matrix_type in matrix_types:
            try:
                matrix = self.generate_matrix(project_id, matrix_type, filters)
                matrices[matrix_type] = matrix
            except Exception as e:
                logger.warning(f"生成矩阵 {matrix_type} 失败: {str(e)}")
        
        return matrices
    
    def export_matrix_to_dict(self, matrix: TraceabilityMatrix) -> Dict[str, Any]:
        """导出矩阵为字典格式"""
        return {
            "project_id": matrix.project_id,
            "matrix_type": matrix.matrix_type,
            "generated_at": matrix.generated_at.isoformat(),
            "requirements": matrix.requirements,
            "targets": matrix.targets,
            "matrix_data": self._serialize_matrix_cells(matrix.matrix_cells),
            "statistics": {
                "total_cells": matrix.total_cells,
                "linked_cells": matrix.linked_cells,
                "coverage_rate": matrix.coverage_rate
            },
            "coverage_analysis": {
                "by_requirement": matrix.coverage_by_requirement,
                "by_target": matrix.coverage_by_target
            },
            "gaps": matrix.gaps,
            "recommendations": matrix.recommendations
        }
    
    def export_matrix_to_csv(self, matrix: TraceabilityMatrix) -> str:
        """导出矩阵为CSV格式"""
        lines = []
        
        # 表头
        header = ["需求ID", "需求编码", "需求标题"]
        for target in matrix.targets:
            header.append(f"{target['name']} ({target['id']})")
        lines.append(",".join(header))
        
        # 数据行
        for req in matrix.requirements:
            row = [str(req["id"]), req["code"], f'"{req["title"]}"']
            for target in matrix.targets:
                cell_key = (req["id"], target["id"])
                cell = matrix.matrix_cells.get(cell_key)
                if cell and cell.is_linked:
                    row.append("✓")
                else:
                    row.append("")
            lines.append(",".join(row))
        
        return "\n".join(lines)
    
    def _get_requirements_for_matrix(self, project_id: int, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """获取矩阵的需求数据"""
        query = self.db.query(Requirement).filter(Requirement.project_id == project_id)
        
        # 应用过滤条件
        if filters:
            if "requirement_types" in filters:
                query = query.filter(Requirement.requirement_type.in_(filters["requirement_types"]))
            
            if "priorities" in filters:
                query = query.filter(Requirement.priority.in_(filters["priorities"]))
            
            if "statuses" in filters:
                query = query.filter(Requirement.status.in_(filters["statuses"]))
            
            if "assignee_ids" in filters:
                query = query.filter(Requirement.assignee_id.in_(filters["assignee_ids"]))
        
        requirements = query.order_by(Requirement.requirement_code).all()
        
        return [
            {
                "id": req.id,
                "code": req.requirement_code,
                "title": req.title,
                "type": req.requirement_type.value if req.requirement_type else None,
                "priority": req.priority.value if req.priority else None,
                "status": req.status.value if req.status else None,
                "assignee_id": req.assignee_id
            }
            for req in requirements
        ]
    
    def _get_targets_for_matrix(
        self,
        project_id: int,
        matrix_type: str,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """获取矩阵的目标对象数据"""
        matrix_config = self.supported_matrix_types[matrix_type]
        target_type = matrix_config["target_type"]
        
        if target_type == "test_case":
            return self._get_test_cases_for_matrix(project_id, filters)
        elif target_type == "task":
            return self._get_tasks_for_matrix(project_id, filters)
        elif target_type == "design":
            return self._get_designs_for_matrix(project_id, filters)
        elif target_type == "requirement":
            return self._get_requirements_for_matrix(project_id, filters)
        else:
            raise ValueError(f"不支持的目标类型: {target_type}")
    
    def _get_test_cases_for_matrix(self, project_id: int, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """获取测试用例数据（模拟实现）"""
        # 这里应该调用测试管理模块的接口
        # 暂时返回模拟数据
        return [
            {"id": 1, "name": "登录功能测试", "type": "功能测试", "status": "已完成"},
            {"id": 2, "name": "密码验证测试", "type": "功能测试", "status": "进行中"},
            {"id": 3, "name": "性能测试", "type": "性能测试", "status": "待执行"}
        ]
    
    def _get_tasks_for_matrix(self, project_id: int, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """获取开发任务数据（模拟实现）"""
        # 这里应该调用任务管理模块的接口
        # 暂时返回模拟数据
        return [
            {"id": 1, "name": "实现用户登录接口", "type": "开发任务", "status": "已完成"},
            {"id": 2, "name": "设计登录页面", "type": "设计任务", "status": "进行中"},
            {"id": 3, "name": "编写登录文档", "type": "文档任务", "status": "待开始"}
        ]
    
    def _get_designs_for_matrix(self, project_id: int, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """获取设计文档数据（模拟实现）"""
        # 这里应该调用设计管理模块的接口
        # 暂时返回模拟数据
        return [
            {"id": 1, "name": "用户登录流程设计", "type": "流程设计", "status": "已完成"},
            {"id": 2, "name": "登录界面设计", "type": "界面设计", "status": "已完成"},
            {"id": 3, "name": "数据库设计", "type": "数据设计", "status": "进行中"}
        ]
    
    def _get_traceability_links(self, project_id: int, matrix_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取追溯链接数据"""
        source_type = matrix_config["source_type"]
        target_type = matrix_config["target_type"]
        link_types = matrix_config["link_types"]
        
        # 构建查询
        query = self.db.query(RequirementTraceabilityLink)
        
        if source_type == "requirement":
            query = query.join(
                Requirement,
                and_(
                    RequirementTraceabilityLink.source_type == source_type,
                    RequirementTraceabilityLink.source_id == Requirement.id
                )
            ).filter(Requirement.project_id == project_id)
        
        query = query.filter(
            RequirementTraceabilityLink.target_type == target_type,
            RequirementTraceabilityLink.link_type.in_(link_types)
        )
        
        links = query.all()
        
        return [
            {
                "id": link.id,
                "source_type": link.source_type,
                "source_id": link.source_id,
                "target_type": link.target_type,
                "target_id": link.target_id,
                "link_type": link.link_type.value,
                "description": link.description,
                "created_at": link.created_at.isoformat() if link.created_at else None,
                "updated_at": link.updated_at.isoformat() if link.updated_at else None
            }
            for link in links
        ]
    
    def _build_matrix_cells(
        self,
        requirements: List[Dict[str, Any]],
        targets: List[Dict[str, Any]],
        links: List[Dict[str, Any]]
    ) -> Dict[Tuple[int, int], MatrixCell]:
        """构建矩阵单元格"""
        matrix_cells = {}
        
        # 创建链接映射
        link_map = defaultdict(list)
        for link in links:
            key = (link["source_id"], link["target_id"])
            link_map[key].append(link)
        
        # 构建所有单元格
        for req in requirements:
            for target in targets:
                cell_key = (req["id"], target["id"])
                cell = MatrixCell(req["id"], target["id"])
                
                # 检查是否有链接
                if cell_key in link_map:
                    cell.is_linked = True
                    cell.link_count = len(link_map[cell_key])
                    
                    for link in link_map[cell_key]:
                        cell.link_types.append(link["link_type"])
                        if link["description"]:
                            cell.link_descriptions.append(link["description"])
                        
                        # 更新最后修改时间
                        if link["updated_at"]:
                            link_updated = datetime.fromisoformat(link["updated_at"].replace('Z', '+00:00'))
                            if cell.last_updated is None or link_updated > cell.last_updated:
                                cell.last_updated = link_updated
                
                matrix_cells[cell_key] = cell
        
        return matrix_cells
    
    def _calculate_matrix_statistics(self, matrix: TraceabilityMatrix):
        """计算矩阵统计信息"""
        matrix.total_cells = len(matrix.matrix_cells)
        matrix.linked_cells = sum(1 for cell in matrix.matrix_cells.values() if cell.is_linked)
        matrix.coverage_rate = matrix.linked_cells / matrix.total_cells if matrix.total_cells > 0 else 0.0
    
    def _analyze_coverage_by_dimension(self, matrix: TraceabilityMatrix):
        """按维度分析覆盖率"""
        # 按需求分析覆盖率
        req_coverage = defaultdict(lambda: {"total": 0, "linked": 0})
        for cell in matrix.matrix_cells.values():
            req_coverage[cell.requirement_id]["total"] += 1
            if cell.is_linked:
                req_coverage[cell.requirement_id]["linked"] += 1
        
        matrix.coverage_by_requirement = {
            req_id: stats["linked"] / stats["total"] if stats["total"] > 0 else 0.0
            for req_id, stats in req_coverage.items()
        }
        
        # 按目标对象分析覆盖率
        target_coverage = defaultdict(lambda: {"total": 0, "linked": 0})
        for cell in matrix.matrix_cells.values():
            target_coverage[cell.target_id]["total"] += 1
            if cell.is_linked:
                target_coverage[cell.target_id]["linked"] += 1
        
        matrix.coverage_by_target = {
            target_id: stats["linked"] / stats["total"] if stats["total"] > 0 else 0.0
            for target_id, stats in target_coverage.items()
        }
    
    def _identify_coverage_gaps(self, matrix: TraceabilityMatrix) -> List[Dict[str, Any]]:
        """识别覆盖缺口"""
        gaps = []
        
        # 识别完全没有追溯的需求
        for req in matrix.requirements:
            req_id = req["id"]
            coverage_rate = matrix.coverage_by_requirement.get(req_id, 0.0)
            
            if coverage_rate == 0.0:
                gaps.append({
                    "type": "uncovered_requirement",
                    "requirement_id": req_id,
                    "requirement_code": req["code"],
                    "requirement_title": req["title"],
                    "requirement_priority": req["priority"],
                    "severity": "high" if req["priority"] in ["CRITICAL", "HIGH"] else "medium",
                    "description": "需求完全没有追溯链接"
                })
            elif coverage_rate < 0.5:
                gaps.append({
                    "type": "low_coverage_requirement",
                    "requirement_id": req_id,
                    "requirement_code": req["code"],
                    "requirement_title": req["title"],
                    "requirement_priority": req["priority"],
                    "coverage_rate": coverage_rate,
                    "severity": "medium",
                    "description": f"需求追溯覆盖率较低 ({coverage_rate:.1%})"
                })
        
        # 识别没有被追溯的目标对象
        for target in matrix.targets:
            target_id = target["id"]
            coverage_rate = matrix.coverage_by_target.get(target_id, 0.0)
            
            if coverage_rate == 0.0:
                gaps.append({
                    "type": "orphaned_target",
                    "target_id": target_id,
                    "target_name": target["name"],
                    "target_type": target.get("type", ""),
                    "severity": "low",
                    "description": f"目标对象没有被任何需求追溯"
                })
        
        # 按严重程度排序
        severity_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return gaps
    
    def _generate_matrix_recommendations(self, matrix: TraceabilityMatrix) -> List[str]:
        """生成矩阵改进建议"""
        recommendations = []
        
        # 基于覆盖率生成建议
        if matrix.coverage_rate < 0.5:
            recommendations.append(
                f"矩阵覆盖率较低 ({matrix.coverage_rate:.1%})，建议优先完善高优先级需求的追溯链接"
            )
        elif matrix.coverage_rate < 0.8:
            recommendations.append(
                f"矩阵覆盖率为 {matrix.coverage_rate:.1%}，建议继续完善追溯链接以达到80%以上"
            )
        
        # 基于缺口分析生成建议
        high_severity_gaps = [gap for gap in matrix.gaps if gap["severity"] == "high"]
        if high_severity_gaps:
            recommendations.append(
                f"发现 {len(high_severity_gaps)} 个高严重程度的覆盖缺口，建议优先处理"
            )
        
        # 基于需求覆盖率生成建议
        uncovered_requirements = [
            req_id for req_id, rate in matrix.coverage_by_requirement.items() if rate == 0.0
        ]
        if uncovered_requirements:
            recommendations.append(
                f"有 {len(uncovered_requirements)} 个需求完全没有追溯链接，建议建立相应的追溯关系"
            )
        
        # 基于目标对象覆盖率生成建议
        orphaned_targets = [
            target_id for target_id, rate in matrix.coverage_by_target.items() if rate == 0.0
        ]
        if orphaned_targets:
            recommendations.append(
                f"有 {len(orphaned_targets)} 个目标对象没有被追溯，建议检查是否需要建立追溯关系"
            )
        
        # 基于矩阵类型生成特定建议
        if matrix.matrix_type == "requirement_to_test":
            test_coverage = matrix.coverage_rate
            if test_coverage < 0.9:
                recommendations.append("测试覆盖率建议达到90%以上，以确保需求的充分验证")
        
        elif matrix.matrix_type == "requirement_to_task":
            task_coverage = matrix.coverage_rate
            if task_coverage < 0.8:
                recommendations.append("开发任务覆盖率建议达到80%以上，以确保需求的完整实现")
        
        return recommendations
    
    def _serialize_matrix_cells(self, matrix_cells: Dict[Tuple[int, int], MatrixCell]) -> Dict[str, Any]:
        """序列化矩阵单元格数据"""
        serialized = {}
        
        for (req_id, target_id), cell in matrix_cells.items():
            key = f"{req_id}_{target_id}"
            serialized[key] = {
                "requirement_id": cell.requirement_id,
                "target_id": cell.target_id,
                "is_linked": cell.is_linked,
                "link_types": cell.link_types,
                "link_descriptions": cell.link_descriptions,
                "link_count": cell.link_count,
                "last_updated": cell.last_updated.isoformat() if cell.last_updated else None
            }
        
        return serialized
    
    def get_supported_matrix_types(self) -> Dict[str, Dict[str, Any]]:
        """获取支持的矩阵类型"""
        return {
            matrix_type: {
                "name": config["name"],
                "source_type": config["source_type"],
                "target_type": config["target_type"],
                "link_types": [lt.value for lt in config["link_types"]]
            }
            for matrix_type, config in self.supported_matrix_types.items()
        }
    
    def validate_matrix_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """验证矩阵过滤条件"""
        validated_filters = {}
        
        if "requirement_types" in filters:
            valid_types = [rt.value for rt in RequirementType]
            validated_filters["requirement_types"] = [
                rt for rt in filters["requirement_types"] if rt in valid_types
            ]
        
        if "priorities" in filters:
            valid_priorities = [p.value for p in Priority]
            validated_filters["priorities"] = [
                p for p in filters["priorities"] if p in valid_priorities
            ]
        
        if "statuses" in filters:
            valid_statuses = [s.value for s in RequirementStatus]
            validated_filters["statuses"] = [
                s for s in filters["statuses"] if s in valid_statuses
            ]
        
        if "assignee_ids" in filters:
            validated_filters["assignee_ids"] = [
                int(aid) for aid in filters["assignee_ids"] if str(aid).isdigit()
            ]
        
        return validated_filters