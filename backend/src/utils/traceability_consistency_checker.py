"""
追溯一致性检查器

本模块实现追溯一致性检查功能，包括：
- 追溯链接一致性验证
- 双向追溯检查
- 追溯完整性验证
- 追溯数据质量检查
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Set, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from collections import defaultdict, deque
from enum import Enum

from ..models.requirement import (
    Requirement, RequirementTraceabilityLink, TraceabilityLinkType,
    RequirementStatus, RequirementType, Priority
)
from ..models.project import Project
from ..utils.logger import get_logger

logger = get_logger(__name__)

class ConsistencyIssueType(Enum):
    """一致性问题类型"""
    MISSING_REVERSE_LINK = "missing_reverse_link"
    CIRCULAR_REFERENCE = "circular_reference"
    ORPHANED_LINK = "orphaned_link"
    INVALID_LINK_TYPE = "invalid_link_type"
    OUTDATED_LINK = "outdated_link"
    DUPLICATE_LINK = "duplicate_link"
    BROKEN_REFERENCE = "broken_reference"
    INCONSISTENT_STATUS = "inconsistent_status"

class ConsistencyIssue:
    """一致性问题"""
    def __init__(self, issue_type: ConsistencyIssueType, severity: str, description: str):
        self.issue_type = issue_type
        self.severity = severity  # critical, high, medium, low
        self.description = description
        self.affected_links: List[int] = []
        self.affected_objects: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []
        self.auto_fixable = False

class ConsistencyCheckResult:
    """一致性检查结果"""
    def __init__(self):
        self.project_id: int = 0
        self.checked_at = datetime.utcnow()
        self.total_links_checked = 0
        self.issues: List[ConsistencyIssue] = []
        self.summary: Dict[str, int] = {}
        self.overall_score = 0.0
        self.recommendations: List[str] = []

class TraceabilityConsistencyChecker:
    """追溯一致性检查器"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 需要双向链接的类型
        self.bidirectional_link_types = {
            TraceabilityLinkType.DERIVES_FROM,
            TraceabilityLinkType.REFINES
        }
        
        # 有效的链接类型组合
        self.valid_link_combinations = {
            ("requirement", "requirement"): [
                TraceabilityLinkType.DERIVES_FROM,
                TraceabilityLinkType.REFINES
            ],
            ("requirement", "task"): [
                TraceabilityLinkType.IMPLEMENTS
            ],
            ("requirement", "test_case"): [
                TraceabilityLinkType.TESTS,
                TraceabilityLinkType.VALIDATES
            ],
            ("requirement", "design"): [
                TraceabilityLinkType.IMPLEMENTS
            ]
        }
        
        # 互斥的链接类型
        self.mutually_exclusive_types = [
            (TraceabilityLinkType.TESTS, TraceabilityLinkType.VALIDATES)
        ]
    
    def check_project_consistency(self, project_id: int) -> ConsistencyCheckResult:
        """检查项目追溯一致性"""
        try:
            result = ConsistencyCheckResult()
            result.project_id = project_id
            
            # 获取项目的所有追溯链接
            links = self._get_project_traceability_links(project_id)
            result.total_links_checked = len(links)
            
            if not links:
                logger.info(f"项目 {project_id} 没有追溯链接")
                return result
            
            # 1. 检查双向链接一致性
            result.issues.extend(self._check_bidirectional_consistency(links))
            
            # 2. 检查循环引用
            result.issues.extend(self._check_circular_references(links))
            
            # 3. 检查孤立链接
            result.issues.extend(self._check_orphaned_links(links))
            
            # 4. 检查链接类型有效性
            result.issues.extend(self._check_link_type_validity(links))
            
            # 5. 检查过期链接
            result.issues.extend(self._check_outdated_links(links))
            
            # 6. 检查重复链接
            result.issues.extend(self._check_duplicate_links(links))
            
            # 7. 检查引用完整性
            result.issues.extend(self._check_reference_integrity(links))
            
            # 8. 检查状态一致性
            result.issues.extend(self._check_status_consistency(links))
            
            # 9. 计算总结和评分
            self._calculate_summary_and_score(result)
            
            # 10. 生成改进建议
            result.recommendations = self._generate_consistency_recommendations(result)
            
            logger.info(f"项目 {project_id} 追溯一致性检查完成，发现 {len(result.issues)} 个问题")
            return result
            
        except Exception as e:
            logger.error(f"检查项目追溯一致性失败: {str(e)}")
            raise
    
    def check_link_consistency(self, link_id: int) -> List[ConsistencyIssue]:
        """检查单个链接的一致性"""
        try:
            link = self.db.query(RequirementTraceabilityLink).filter(
                RequirementTraceabilityLink.id == link_id
            ).first()
            
            if not link:
                raise ValueError("追溯链接不存在")
            
            issues = []
            
            # 检查引用完整性
            issues.extend(self._check_single_link_reference_integrity(link))
            
            # 检查链接类型有效性
            issues.extend(self._check_single_link_type_validity(link))
            
            # 检查双向一致性
            if link.link_type in self.bidirectional_link_types:
                issues.extend(self._check_single_link_bidirectional_consistency(link))
            
            # 检查状态一致性
            issues.extend(self._check_single_link_status_consistency(link))
            
            return issues
            
        except Exception as e:
            logger.error(f"检查链接一致性失败: {str(e)}")
            raise
    
    def auto_fix_issues(self, project_id: int, issue_types: List[ConsistencyIssueType] = None) -> Dict[str, Any]:
        """自动修复一致性问题"""
        try:
            result = {
                "fixed_count": 0,
                "failed_count": 0,
                "fixed_issues": [],
                "failed_issues": []
            }
            
            # 检查一致性问题
            consistency_result = self.check_project_consistency(project_id)
            
            # 过滤可自动修复的问题
            fixable_issues = [
                issue for issue in consistency_result.issues
                if issue.auto_fixable and (issue_types is None or issue.issue_type in issue_types)
            ]
            
            for issue in fixable_issues:
                try:
                    if self._auto_fix_issue(issue):
                        result["fixed_count"] += 1
                        result["fixed_issues"].append({
                            "type": issue.issue_type.value,
                            "description": issue.description
                        })
                    else:
                        result["failed_count"] += 1
                        result["failed_issues"].append({
                            "type": issue.issue_type.value,
                            "description": issue.description,
                            "reason": "修复失败"
                        })
                except Exception as e:
                    result["failed_count"] += 1
                    result["failed_issues"].append({
                        "type": issue.issue_type.value,
                        "description": issue.description,
                        "reason": str(e)
                    })
            
            if result["fixed_count"] > 0:
                self.db.commit()
            
            logger.info(f"自动修复完成: 成功 {result['fixed_count']} 个，失败 {result['failed_count']} 个")
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"自动修复一致性问题失败: {str(e)}")
            raise
    
    def _get_project_traceability_links(self, project_id: int) -> List[RequirementTraceabilityLink]:
        """获取项目的所有追溯链接"""
        return self.db.query(RequirementTraceabilityLink).join(
            Requirement,
            or_(
                and_(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == Requirement.id
                ),
                and_(
                    RequirementTraceabilityLink.target_type == "requirement",
                    RequirementTraceabilityLink.target_id == Requirement.id
                )
            )
        ).filter(Requirement.project_id == project_id).all()
    
    def _check_bidirectional_consistency(self, links: List[RequirementTraceabilityLink]) -> List[ConsistencyIssue]:
        """检查双向链接一致性"""
        issues = []
        
        # 构建链接映射
        link_map = {}
        for link in links:
            key = (link.source_type, link.source_id, link.target_type, link.target_id, link.link_type)
            link_map[key] = link
        
        # 检查需要双向链接的类型
        for link in links:
            if link.link_type in self.bidirectional_link_types:
                # 查找对应的反向链接
                reverse_key = (
                    link.target_type, link.target_id,
                    link.source_type, link.source_id,
                    link.link_type
                )
                
                if reverse_key not in link_map:
                    issue = ConsistencyIssue(
                        ConsistencyIssueType.MISSING_REVERSE_LINK,
                        "medium",
                        f"缺少反向追溯链接: {link.source_type}:{link.source_id} -> {link.target_type}:{link.target_id}"
                    )
                    issue.affected_links = [link.id]
                    issue.recommendations = ["创建对应的反向追溯链接"]
                    issue.auto_fixable = True
                    issues.append(issue)
        
        return issues
    
    def _check_circular_references(self, links: List[RequirementTraceabilityLink]) -> List[ConsistencyIssue]:
        """检查循环引用"""
        issues = []
        
        # 按类型分组构建图
        graphs = defaultdict(lambda: defaultdict(list))
        for link in links:
            if link.source_type == link.target_type:  # 只检查同类型对象间的循环
                graphs[link.source_type][link.source_id].append(link.target_id)
        
        # 检测每个图中的循环
        for object_type, graph in graphs.items():
            cycles = self._detect_cycles_in_graph(graph)
            
            for cycle in cycles:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.CIRCULAR_REFERENCE,
                    "high",
                    f"检测到循环引用: {' -> '.join(map(str, cycle))}"
                )
                
                # 找到涉及的链接
                affected_links = []
                for i in range(len(cycle)):
                    source_id = cycle[i]
                    target_id = cycle[(i + 1) % len(cycle)]
                    
                    for link in links:
                        if (link.source_type == object_type and
                            link.source_id == source_id and
                            link.target_type == object_type and
                            link.target_id == target_id):
                            affected_links.append(link.id)
                
                issue.affected_links = affected_links
                issue.recommendations = ["删除循环中的一个或多个链接"]
                issues.append(issue)
        
        return issues
    
    def _detect_cycles_in_graph(self, graph: Dict[int, List[int]]) -> List[List[int]]:
        """在图中检测循环"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: int, path: List[int]) -> bool:
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path.copy())
            
            rec_stack.remove(node)
            return False
        
        # 检查所有节点
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def _check_orphaned_links(self, links: List[RequirementTraceabilityLink]) -> List[ConsistencyIssue]:
        """检查孤立链接"""
        issues = []
        
        for link in links:
            # 检查源对象是否存在
            source_exists = self._check_object_exists(link.source_type, link.source_id)
            if not source_exists:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.ORPHANED_LINK,
                    "high",
                    f"源对象不存在: {link.source_type}:{link.source_id}"
                )
                issue.affected_links = [link.id]
                issue.recommendations = ["删除孤立的追溯链接"]
                issue.auto_fixable = True
                issues.append(issue)
            
            # 检查目标对象是否存在
            target_exists = self._check_object_exists(link.target_type, link.target_id)
            if not target_exists:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.ORPHANED_LINK,
                    "high",
                    f"目标对象不存在: {link.target_type}:{link.target_id}"
                )
                issue.affected_links = [link.id]
                issue.recommendations = ["删除孤立的追溯链接"]
                issue.auto_fixable = True
                issues.append(issue)
        
        return issues
    
    def _check_object_exists(self, object_type: str, object_id: int) -> bool:
        """检查对象是否存在"""
        if object_type == "requirement":
            return self.db.query(Requirement).filter(Requirement.id == object_id).first() is not None
        
        # 对于其他类型的对象，这里应该调用相应模块的检查方法
        # 暂时假设存在
        return True
    
    def _check_link_type_validity(self, links: List[RequirementTraceabilityLink]) -> List[ConsistencyIssue]:
        """检查链接类型有效性"""
        issues = []
        
        for link in links:
            combination_key = (link.source_type, link.target_type)
            
            # 检查是否是支持的组合
            if combination_key not in self.valid_link_combinations:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.INVALID_LINK_TYPE,
                    "medium",
                    f"不支持的链接类型组合: {link.source_type} -> {link.target_type}"
                )
                issue.affected_links = [link.id]
                issue.recommendations = ["删除无效的追溯链接或修改链接类型"]
                issues.append(issue)
                continue
            
            # 检查链接类型是否适用于该组合
            valid_types = self.valid_link_combinations[combination_key]
            if link.link_type not in valid_types:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.INVALID_LINK_TYPE,
                    "medium",
                    f"链接类型 {link.link_type.value} 不适用于 {link.source_type} -> {link.target_type}"
                )
                issue.affected_links = [link.id]
                valid_type_names = [t.value for t in valid_types]
                issue.recommendations = [f"修改为有效的链接类型: {', '.join(valid_type_names)}"]
                issues.append(issue)
        
        return issues
    
    def _check_outdated_links(self, links: List[RequirementTraceabilityLink]) -> List[ConsistencyIssue]:
        """检查过期链接"""
        issues = []
        
        # 定义过期阈值（例如：1年未更新）
        outdated_threshold = datetime.utcnow() - timedelta(days=365)
        
        for link in links:
            if link.updated_at and link.updated_at < outdated_threshold:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.OUTDATED_LINK,
                    "low",
                    f"追溯链接可能已过期: 最后更新于 {link.updated_at.strftime('%Y-%m-%d')}"
                )
                issue.affected_links = [link.id]
                issue.recommendations = ["验证链接的有效性并更新或删除"]
                issues.append(issue)
        
        return issues
    
    def _check_duplicate_links(self, links: List[RequirementTraceabilityLink]) -> List[ConsistencyIssue]:
        """检查重复链接"""
        issues = []
        
        # 构建链接签名映射
        link_signatures = defaultdict(list)
        for link in links:
            signature = (link.source_type, link.source_id, link.target_type, link.target_id, link.link_type)
            link_signatures[signature].append(link)
        
        # 检查重复
        for signature, duplicate_links in link_signatures.items():
            if len(duplicate_links) > 1:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.DUPLICATE_LINK,
                    "medium",
                    f"发现重复的追溯链接: {signature[0]}:{signature[1]} -> {signature[2]}:{signature[3]}"
                )
                issue.affected_links = [link.id for link in duplicate_links]
                issue.recommendations = ["保留一个链接，删除其他重复链接"]
                issue.auto_fixable = True
                issues.append(issue)
        
        return issues
    
    def _check_reference_integrity(self, links: List[RequirementTraceabilityLink]) -> List[ConsistencyIssue]:
        """检查引用完整性"""
        issues = []
        
        for link in links:
            # 检查源对象和目标对象的状态
            if link.source_type == "requirement" and link.target_type == "requirement":
                source_req = self.db.query(Requirement).filter(Requirement.id == link.source_id).first()
                target_req = self.db.query(Requirement).filter(Requirement.id == link.target_id).first()
                
                if source_req and target_req:
                    # 检查状态一致性
                    if (source_req.status == RequirementStatus.CANCELLED and
                        target_req.status not in [RequirementStatus.CANCELLED, RequirementStatus.CLOSED]):
                        
                        issue = ConsistencyIssue(
                            ConsistencyIssueType.BROKEN_REFERENCE,
                            "medium",
                            f"已取消的需求 {source_req.requirement_code} 仍与活跃需求 {target_req.requirement_code} 存在追溯关系"
                        )
                        issue.affected_links = [link.id]
                        issue.recommendations = ["删除与已取消需求的追溯链接"]
                        issues.append(issue)
        
        return issues
    
    def _check_status_consistency(self, links: List[RequirementTraceabilityLink]) -> List[ConsistencyIssue]:
        """检查状态一致性"""
        issues = []
        
        for link in links:
            if link.source_type == "requirement":
                source_req = self.db.query(Requirement).filter(Requirement.id == link.source_id).first()
                
                if source_req:
                    # 检查草稿状态的需求是否应该有追溯链接
                    if source_req.status == RequirementStatus.DRAFT:
                        issue = ConsistencyIssue(
                            ConsistencyIssueType.INCONSISTENT_STATUS,
                            "low",
                            f"草稿状态的需求 {source_req.requirement_code} 存在追溯链接"
                        )
                        issue.affected_links = [link.id]
                        issue.recommendations = ["等需求状态稳定后再建立追溯链接"]
                        issues.append(issue)
        
        return issues
    
    def _check_single_link_reference_integrity(self, link: RequirementTraceabilityLink) -> List[ConsistencyIssue]:
        """检查单个链接的引用完整性"""
        issues = []
        
        # 检查源对象是否存在
        if not self._check_object_exists(link.source_type, link.source_id):
            issue = ConsistencyIssue(
                ConsistencyIssueType.ORPHANED_LINK,
                "high",
                f"源对象不存在: {link.source_type}:{link.source_id}"
            )
            issue.affected_links = [link.id]
            issues.append(issue)
        
        # 检查目标对象是否存在
        if not self._check_object_exists(link.target_type, link.target_id):
            issue = ConsistencyIssue(
                ConsistencyIssueType.ORPHANED_LINK,
                "high",
                f"目标对象不存在: {link.target_type}:{link.target_id}"
            )
            issue.affected_links = [link.id]
            issues.append(issue)
        
        return issues
    
    def _check_single_link_type_validity(self, link: RequirementTraceabilityLink) -> List[ConsistencyIssue]:
        """检查单个链接的类型有效性"""
        issues = []
        
        combination_key = (link.source_type, link.target_type)
        
        if combination_key not in self.valid_link_combinations:
            issue = ConsistencyIssue(
                ConsistencyIssueType.INVALID_LINK_TYPE,
                "medium",
                f"不支持的链接类型组合: {link.source_type} -> {link.target_type}"
            )
            issue.affected_links = [link.id]
            issues.append(issue)
        else:
            valid_types = self.valid_link_combinations[combination_key]
            if link.link_type not in valid_types:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.INVALID_LINK_TYPE,
                    "medium",
                    f"链接类型 {link.link_type.value} 不适用于 {link.source_type} -> {link.target_type}"
                )
                issue.affected_links = [link.id]
                issues.append(issue)
        
        return issues
    
    def _check_single_link_bidirectional_consistency(self, link: RequirementTraceabilityLink) -> List[ConsistencyIssue]:
        """检查单个链接的双向一致性"""
        issues = []
        
        # 查找反向链接
        reverse_link = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == link.target_type,
            RequirementTraceabilityLink.source_id == link.target_id,
            RequirementTraceabilityLink.target_type == link.source_type,
            RequirementTraceabilityLink.target_id == link.source_id,
            RequirementTraceabilityLink.link_type == link.link_type
        ).first()
        
        if not reverse_link:
            issue = ConsistencyIssue(
                ConsistencyIssueType.MISSING_REVERSE_LINK,
                "medium",
                f"缺少反向追溯链接: {link.source_type}:{link.source_id} -> {link.target_type}:{link.target_id}"
            )
            issue.affected_links = [link.id]
            issues.append(issue)
        
        return issues
    
    def _check_single_link_status_consistency(self, link: RequirementTraceabilityLink) -> List[ConsistencyIssue]:
        """检查单个链接的状态一致性"""
        issues = []
        
        if link.source_type == "requirement":
            source_req = self.db.query(Requirement).filter(Requirement.id == link.source_id).first()
            
            if source_req and source_req.status == RequirementStatus.DRAFT:
                issue = ConsistencyIssue(
                    ConsistencyIssueType.INCONSISTENT_STATUS,
                    "low",
                    f"草稿状态的需求 {source_req.requirement_code} 存在追溯链接"
                )
                issue.affected_links = [link.id]
                issues.append(issue)
        
        return issues
    
    def _calculate_summary_and_score(self, result: ConsistencyCheckResult):
        """计算总结和评分"""
        # 统计各类型问题数量
        issue_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for issue in result.issues:
            issue_counts[issue.issue_type.value] += 1
            severity_counts[issue.severity] += 1
        
        result.summary = {
            "total_issues": len(result.issues),
            "by_type": dict(issue_counts),
            "by_severity": dict(severity_counts)
        }
        
        # 计算一致性评分（0-100）
        if result.total_links_checked == 0:
            result.overall_score = 100.0
        else:
            # 根据问题严重程度计算扣分
            penalty = 0
            penalty += severity_counts.get("critical", 0) * 10
            penalty += severity_counts.get("high", 0) * 5
            penalty += severity_counts.get("medium", 0) * 2
            penalty += severity_counts.get("low", 0) * 1
            
            # 计算评分
            max_penalty = result.total_links_checked * 10  # 假设每个链接最多扣10分
            result.overall_score = max(0, 100 - (penalty / max_penalty * 100))
    
    def _generate_consistency_recommendations(self, result: ConsistencyCheckResult) -> List[str]:
        """生成一致性改进建议"""
        recommendations = []
        
        # 基于评分生成建议
        if result.overall_score < 60:
            recommendations.append("追溯一致性评分较低，建议优先修复高严重程度的问题")
        elif result.overall_score < 80:
            recommendations.append("追溯一致性有待改善，建议逐步修复发现的问题")
        
        # 基于问题类型生成建议
        issue_counts = result.summary.get("by_type", {})
        
        if issue_counts.get("circular_reference", 0) > 0:
            recommendations.append("发现循环引用，建议重新设计追溯关系以避免循环")
        
        if issue_counts.get("orphaned_link", 0) > 0:
            recommendations.append("发现孤立链接，建议清理无效的追溯关系")
        
        if issue_counts.get("missing_reverse_link", 0) > 0:
            recommendations.append("发现缺失的反向链接，建议完善双向追溯关系")
        
        if issue_counts.get("duplicate_link", 0) > 0:
            recommendations.append("发现重复链接，建议清理重复的追溯关系")
        
        # 基于严重程度生成建议
        severity_counts = result.summary.get("by_severity", {})
        
        if severity_counts.get("critical", 0) > 0:
            recommendations.append("发现严重问题，建议立即处理")
        
        if severity_counts.get("high", 0) > 0:
            recommendations.append("发现高优先级问题，建议优先处理")
        
        return recommendations
    
    def _auto_fix_issue(self, issue: ConsistencyIssue) -> bool:
        """自动修复问题"""
        try:
            if issue.issue_type == ConsistencyIssueType.MISSING_REVERSE_LINK:
                return self._auto_fix_missing_reverse_link(issue)
            elif issue.issue_type == ConsistencyIssueType.ORPHANED_LINK:
                return self._auto_fix_orphaned_link(issue)
            elif issue.issue_type == ConsistencyIssueType.DUPLICATE_LINK:
                return self._auto_fix_duplicate_link(issue)
            else:
                return False
        except Exception as e:
            logger.error(f"自动修复问题失败: {str(e)}")
            return False
    
    def _auto_fix_missing_reverse_link(self, issue: ConsistencyIssue) -> bool:
        """自动修复缺失的反向链接"""
        if not issue.affected_links:
            return False
        
        link = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.id == issue.affected_links[0]
        ).first()
        
        if not link:
            return False
        
        # 创建反向链接
        reverse_link = RequirementTraceabilityLink(
            source_type=link.target_type,
            source_id=link.target_id,
            target_type=link.source_type,
            target_id=link.source_id,
            link_type=link.link_type,
            description=f"自动创建的反向链接: {link.description}" if link.description else "自动创建的反向链接",
            created_by=link.created_by
        )
        
        self.db.add(reverse_link)
        return True
    
    def _auto_fix_orphaned_link(self, issue: ConsistencyIssue) -> bool:
        """自动修复孤立链接"""
        if not issue.affected_links:
            return False
        
        # 删除孤立的链接
        for link_id in issue.affected_links:
            link = self.db.query(RequirementTraceabilityLink).filter(
                RequirementTraceabilityLink.id == link_id
            ).first()
            
            if link:
                self.db.delete(link)
        
        return True
    
    def _auto_fix_duplicate_link(self, issue: ConsistencyIssue) -> bool:
        """自动修复重复链接"""
        if len(issue.affected_links) <= 1:
            return False
        
        # 保留第一个链接，删除其他重复链接
        links_to_delete = issue.affected_links[1:]
        
        for link_id in links_to_delete:
            link = self.db.query(RequirementTraceabilityLink).filter(
                RequirementTraceabilityLink.id == link_id
            ).first()
            
            if link:
                self.db.delete(link)
        
        return True