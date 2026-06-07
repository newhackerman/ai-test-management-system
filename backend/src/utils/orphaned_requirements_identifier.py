"""
孤立需求识别器

本模块实现孤立需求的识别功能，包括：
- 识别没有追溯链接的需求
- 识别没有上游来源的需求
- 识别没有下游实现的需求
- 分析孤立需求的影响
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Set, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from collections import defaultdict
from enum import Enum

from ..models.requirement import (
    Requirement, RequirementTraceabilityLink, TraceabilityLinkType,
    RequirementStatus, RequirementType, Priority, BusinessValue
)
from ..models.project import Project
from ..utils.logger import get_logger

logger = get_logger(__name__)

class OrphanType(Enum):
    """孤立类型"""
    COMPLETELY_ORPHANED = "completely_orphaned"  # 完全孤立（无任何追溯）
    NO_UPSTREAM = "no_upstream"  # 无上游来源
    NO_DOWNSTREAM = "no_downstream"  # 无下游实现
    NO_TEST_COVERAGE = "no_test_coverage"  # 无测试覆盖
    NO_TASK_IMPLEMENTATION = "no_task_implementation"  # 无任务实现
    NO_DESIGN_REFERENCE = "no_design_reference"  # 无设计引用

class OrphanedRequirement:
    """孤立需求"""
    def __init__(self, requirement: Requirement):
        self.requirement = requirement
        self.orphan_types: List[OrphanType] = []
        self.severity = "medium"
        self.impact_score = 0.0
        self.recommendations: List[str] = []
        self.missing_links: List[Dict[str, Any]] = []
        self.potential_links: List[Dict[str, Any]] = []

class OrphanAnalysisResult:
    """孤立分析结果"""
    def __init__(self):
        self.project_id: int = 0
        self.analyzed_at = datetime.utcnow()
        self.total_requirements = 0
        self.orphaned_requirements: List[OrphanedRequirement] = []
        self.orphan_statistics: Dict[str, int] = {}
        self.severity_distribution: Dict[str, int] = {}
        self.recommendations: List[str] = []

class OrphanedRequirementsIdentifier:
    """孤立需求识别器"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 严重程度权重
        self.severity_weights = {
            Priority.CRITICAL: 1.0,
            Priority.HIGH: 0.8,
            Priority.MEDIUM: 0.6,
            Priority.LOW: 0.4,
            Priority.OPTIONAL: 0.2
        }
        
        # 业务价值权重
        self.business_value_weights = {
            BusinessValue.CORE: 1.0,
            BusinessValue.IMPORTANT: 0.8,
            BusinessValue.NORMAL: 0.6,
            BusinessValue.OPTIONAL: 0.4
        }
        
        # 状态权重
        self.status_weights = {
            RequirementStatus.APPROVED: 1.0,
            RequirementStatus.IN_DEVELOPMENT: 0.9,
            RequirementStatus.TESTING: 0.8,
            RequirementStatus.COMPLETED: 0.7,
            RequirementStatus.REVIEWING: 0.6,
            RequirementStatus.PENDING_REVIEW: 0.5,
            RequirementStatus.NEEDS_REVISION: 0.4,
            RequirementStatus.DRAFT: 0.3,
            RequirementStatus.PAUSED: 0.2,
            RequirementStatus.CANCELLED: 0.0,
            RequirementStatus.CLOSED: 0.0
        }
    
    def identify_orphaned_requirements(self, project_id: int) -> OrphanAnalysisResult:
        """识别项目中的孤立需求"""
        try:
            result = OrphanAnalysisResult()
            result.project_id = project_id
            
            # 获取项目所有需求
            requirements = self.db.query(Requirement).filter(
                Requirement.project_id == project_id
            ).all()
            
            result.total_requirements = len(requirements)
            
            if not requirements:
                logger.info(f"项目 {project_id} 没有需求")
                return result
            
            # 分析每个需求的孤立情况
            for requirement in requirements:
                orphaned_req = self._analyze_requirement_orphan_status(requirement)
                if orphaned_req.orphan_types:
                    result.orphaned_requirements.append(orphaned_req)
            
            # 计算统计信息
            self._calculate_orphan_statistics(result)
            
            # 生成改进建议
            result.recommendations = self._generate_orphan_recommendations(result)
            
            logger.info(f"项目 {project_id} 孤立需求识别完成，发现 {len(result.orphaned_requirements)} 个孤立需求")
            return result
            
        except Exception as e:
            logger.error(f"识别孤立需求失败: {str(e)}")
            raise
    
    def identify_specific_orphan_type(self, project_id: int, orphan_type: OrphanType) -> List[OrphanedRequirement]:
        """识别特定类型的孤立需求"""
        try:
            requirements = self.db.query(Requirement).filter(
                Requirement.project_id == project_id
            ).all()
            
            orphaned_requirements = []
            
            for requirement in requirements:
                if self._check_specific_orphan_type(requirement, orphan_type):
                    orphaned_req = OrphanedRequirement(requirement)
                    orphaned_req.orphan_types = [orphan_type]
                    orphaned_req.severity = self._calculate_orphan_severity(requirement, [orphan_type])
                    orphaned_req.recommendations = self._generate_specific_recommendations(requirement, orphan_type)
                    orphaned_requirements.append(orphaned_req)
            
            return orphaned_requirements
            
        except Exception as e:
            logger.error(f"识别特定类型孤立需求失败: {str(e)}")
            raise
    
    def suggest_potential_links(self, requirement_id: int) -> List[Dict[str, Any]]:
        """为孤立需求建议潜在的追溯链接"""
        try:
            requirement = self.db.query(Requirement).filter(
                Requirement.id == requirement_id
            ).first()
            
            if not requirement:
                raise ValueError("需求不存在")
            
            suggestions = []
            
            # 1. 建议相似需求的链接
            suggestions.extend(self._suggest_similar_requirement_links(requirement))
            
            # 2. 建议基于关键词的链接
            suggestions.extend(self._suggest_keyword_based_links(requirement))
            
            # 3. 建议基于项目结构的链接
            suggestions.extend(self._suggest_structure_based_links(requirement))
            
            # 4. 建议基于时间的链接
            suggestions.extend(self._suggest_temporal_links(requirement))
            
            # 按置信度排序
            suggestions.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
            
            return suggestions[:10]  # 返回前10个建议
            
        except Exception as e:
            logger.error(f"建议潜在链接失败: {str(e)}")
            raise
    
    def _analyze_requirement_orphan_status(self, requirement: Requirement) -> OrphanedRequirement:
        """分析需求的孤立状态"""
        orphaned_req = OrphanedRequirement(requirement)
        
        # 检查各种孤立类型
        orphan_types = []
        
        # 1. 检查是否完全孤立
        if self._is_completely_orphaned(requirement):
            orphan_types.append(OrphanType.COMPLETELY_ORPHANED)
        
        # 2. 检查是否缺少上游来源
        if self._has_no_upstream(requirement):
            orphan_types.append(OrphanType.NO_UPSTREAM)
        
        # 3. 检查是否缺少下游实现
        if self._has_no_downstream(requirement):
            orphan_types.append(OrphanType.NO_DOWNSTREAM)
        
        # 4. 检查是否缺少测试覆盖
        if self._has_no_test_coverage(requirement):
            orphan_types.append(OrphanType.NO_TEST_COVERAGE)
        
        # 5. 检查是否缺少任务实现
        if self._has_no_task_implementation(requirement):
            orphan_types.append(OrphanType.NO_TASK_IMPLEMENTATION)
        
        # 6. 检查是否缺少设计引用
        if self._has_no_design_reference(requirement):
            orphan_types.append(OrphanType.NO_DESIGN_REFERENCE)
        
        orphaned_req.orphan_types = orphan_types
        
        if orphan_types:
            # 计算严重程度和影响评分
            orphaned_req.severity = self._calculate_orphan_severity(requirement, orphan_types)
            orphaned_req.impact_score = self._calculate_impact_score(requirement, orphan_types)
            
            # 生成建议
            orphaned_req.recommendations = self._generate_orphan_recommendations_for_requirement(
                requirement, orphan_types
            )
            
            # 识别缺失的链接
            orphaned_req.missing_links = self._identify_missing_links_for_requirement(
                requirement, orphan_types
            )
        
        return orphaned_req
    
    def _is_completely_orphaned(self, requirement: Requirement) -> bool:
        """检查需求是否完全孤立（无任何追溯链接）"""
        # 检查作为源的链接
        source_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement.id
        ).count()
        
        # 检查作为目标的链接
        target_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.target_type == "requirement",
            RequirementTraceabilityLink.target_id == requirement.id
        ).count()
        
        return source_links == 0 and target_links == 0
    
    def _has_no_upstream(self, requirement: Requirement) -> bool:
        """检查需求是否缺少上游来源"""
        upstream_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.target_type == "requirement",
            RequirementTraceabilityLink.target_id == requirement.id
        ).count()
        
        return upstream_links == 0
    
    def _has_no_downstream(self, requirement: Requirement) -> bool:
        """检查需求是否缺少下游实现"""
        downstream_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement.id
        ).count()
        
        return downstream_links == 0
    
    def _has_no_test_coverage(self, requirement: Requirement) -> bool:
        """检查需求是否缺少测试覆盖"""
        test_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement.id,
            RequirementTraceabilityLink.target_type == "test_case"
        ).count()
        
        return test_links == 0
    
    def _has_no_task_implementation(self, requirement: Requirement) -> bool:
        """检查需求是否缺少任务实现"""
        task_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement.id,
            RequirementTraceabilityLink.target_type == "task"
        ).count()
        
        return task_links == 0
    
    def _has_no_design_reference(self, requirement: Requirement) -> bool:
        """检查需求是否缺少设计引用"""
        design_links = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == "requirement",
            RequirementTraceabilityLink.source_id == requirement.id,
            RequirementTraceabilityLink.target_type == "design"
        ).count()
        
        return design_links == 0
    
    def _check_specific_orphan_type(self, requirement: Requirement, orphan_type: OrphanType) -> bool:
        """检查特定的孤立类型"""
        if orphan_type == OrphanType.COMPLETELY_ORPHANED:
            return self._is_completely_orphaned(requirement)
        elif orphan_type == OrphanType.NO_UPSTREAM:
            return self._has_no_upstream(requirement)
        elif orphan_type == OrphanType.NO_DOWNSTREAM:
            return self._has_no_downstream(requirement)
        elif orphan_type == OrphanType.NO_TEST_COVERAGE:
            return self._has_no_test_coverage(requirement)
        elif orphan_type == OrphanType.NO_TASK_IMPLEMENTATION:
            return self._has_no_task_implementation(requirement)
        elif orphan_type == OrphanType.NO_DESIGN_REFERENCE:
            return self._has_no_design_reference(requirement)
        else:
            return False
    
    def _calculate_orphan_severity(self, requirement: Requirement, orphan_types: List[OrphanType]) -> str:
        """计算孤立需求的严重程度"""
        # 基础严重程度评分
        base_score = 0.0
        
        # 根据孤立类型计算评分
        type_scores = {
            OrphanType.COMPLETELY_ORPHANED: 1.0,
            OrphanType.NO_UPSTREAM: 0.7,
            OrphanType.NO_DOWNSTREAM: 0.8,
            OrphanType.NO_TEST_COVERAGE: 0.6,
            OrphanType.NO_TASK_IMPLEMENTATION: 0.5,
            OrphanType.NO_DESIGN_REFERENCE: 0.4
        }
        
        for orphan_type in orphan_types:
            base_score += type_scores.get(orphan_type, 0.0)
        
        # 根据需求属性调整评分
        priority_weight = self.severity_weights.get(requirement.priority, 0.5)
        business_value_weight = self.business_value_weights.get(requirement.business_value, 0.5)
        status_weight = self.status_weights.get(requirement.status, 0.5)
        
        final_score = base_score * priority_weight * business_value_weight * status_weight
        
        # 转换为严重程度等级
        if final_score >= 0.8:
            return "critical"
        elif final_score >= 0.6:
            return "high"
        elif final_score >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _calculate_impact_score(self, requirement: Requirement, orphan_types: List[OrphanType]) -> float:
        """计算影响评分"""
        # 基础影响评分
        base_impact = len(orphan_types) * 0.2
        
        # 根据需求属性调整
        priority_factor = self.severity_weights.get(requirement.priority, 0.5)
        business_value_factor = self.business_value_weights.get(requirement.business_value, 0.5)
        status_factor = self.status_weights.get(requirement.status, 0.5)
        
        # 根据需求类型调整
        type_factor = 1.0
        if requirement.requirement_type == RequirementType.FUNCTIONAL:
            type_factor = 1.0
        elif requirement.requirement_type == RequirementType.NON_FUNCTIONAL:
            type_factor = 0.8
        elif requirement.requirement_type == RequirementType.CONSTRAINT:
            type_factor = 0.9
        elif requirement.requirement_type == RequirementType.INTERFACE:
            type_factor = 0.7
        
        impact_score = base_impact * priority_factor * business_value_factor * status_factor * type_factor
        
        return min(1.0, impact_score)  # 限制在0-1之间
    
    def _generate_orphan_recommendations_for_requirement(
        self,
        requirement: Requirement,
        orphan_types: List[OrphanType]
    ) -> List[str]:
        """为孤立需求生成建议"""
        recommendations = []
        
        for orphan_type in orphan_types:
            if orphan_type == OrphanType.COMPLETELY_ORPHANED:
                recommendations.append("需求完全孤立，建议建立与业务需求、设计文档、测试用例的追溯关系")
            elif orphan_type == OrphanType.NO_UPSTREAM:
                recommendations.append("缺少上游来源，建议明确需求的业务来源或父需求")
            elif orphan_type == OrphanType.NO_DOWNSTREAM:
                recommendations.append("缺少下游实现，建议创建相应的设计文档、开发任务和测试用例")
            elif orphan_type == OrphanType.NO_TEST_COVERAGE:
                recommendations.append("缺少测试覆盖，建议创建相应的测试用例并建立追溯关系")
            elif orphan_type == OrphanType.NO_TASK_IMPLEMENTATION:
                recommendations.append("缺少任务实现，建议创建开发任务并建立追溯关系")
            elif orphan_type == OrphanType.NO_DESIGN_REFERENCE:
                recommendations.append("缺少设计引用，建议创建设计文档并建立追溯关系")
        
        # 根据需求状态添加特定建议
        if requirement.status == RequirementStatus.DRAFT:
            recommendations.append("需求仍为草稿状态，建议完善后再建立追溯关系")
        elif requirement.status == RequirementStatus.APPROVED:
            recommendations.append("需求已批准但缺少实现追溯，建议尽快建立相关追溯关系")
        
        return recommendations
    
    def _identify_missing_links_for_requirement(
        self,
        requirement: Requirement,
        orphan_types: List[OrphanType]
    ) -> List[Dict[str, Any]]:
        """识别需求缺失的链接类型"""
        missing_links = []
        
        for orphan_type in orphan_types:
            if orphan_type == OrphanType.NO_TEST_COVERAGE:
                missing_links.append({
                    "target_type": "test_case",
                    "link_type": "TESTS",
                    "priority": "high",
                    "description": "需要创建测试用例"
                })
            elif orphan_type == OrphanType.NO_TASK_IMPLEMENTATION:
                missing_links.append({
                    "target_type": "task",
                    "link_type": "IMPLEMENTS",
                    "priority": "medium",
                    "description": "需要创建开发任务"
                })
            elif orphan_type == OrphanType.NO_DESIGN_REFERENCE:
                missing_links.append({
                    "target_type": "design",
                    "link_type": "IMPLEMENTS",
                    "priority": "medium",
                    "description": "需要创建设计文档"
                })
            elif orphan_type == OrphanType.NO_UPSTREAM:
                missing_links.append({
                    "source_type": "business_requirement",
                    "link_type": "DERIVES_FROM",
                    "priority": "high",
                    "description": "需要明确业务来源"
                })
        
        return missing_links
    
    def _suggest_similar_requirement_links(self, requirement: Requirement) -> List[Dict[str, Any]]:
        """建议相似需求的链接"""
        suggestions = []
        
        # 查找相同项目中的相似需求
        similar_requirements = self.db.query(Requirement).filter(
            Requirement.project_id == requirement.project_id,
            Requirement.id != requirement.id,
            Requirement.requirement_type == requirement.requirement_type
        ).limit(5).all()
        
        for similar_req in similar_requirements:
            # 检查相似需求的追溯链接
            links = self.db.query(RequirementTraceabilityLink).filter(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == similar_req.id
            ).all()
            
            for link in links:
                suggestions.append({
                    "target_type": link.target_type,
                    "target_id": link.target_id,
                    "link_type": link.link_type.value,
                    "confidence": 0.7,
                    "reason": f"基于相似需求 {similar_req.requirement_code} 的追溯关系",
                    "similar_requirement": {
                        "id": similar_req.id,
                        "code": similar_req.requirement_code,
                        "title": similar_req.title
                    }
                })
        
        return suggestions
    
    def _suggest_keyword_based_links(self, requirement: Requirement) -> List[Dict[str, Any]]:
        """基于关键词建议链接"""
        suggestions = []
        
        # 提取需求标题和描述中的关键词
        keywords = self._extract_keywords(requirement.title, requirement.description)
        
        if not keywords:
            return suggestions
        
        # 查找包含相同关键词的其他对象（这里简化处理）
        # 实际实现中应该调用相应模块的搜索接口
        
        return suggestions
    
    def _suggest_structure_based_links(self, requirement: Requirement) -> List[Dict[str, Any]]:
        """基于项目结构建议链接"""
        suggestions = []
        
        # 检查父子需求关系
        if requirement.parent_id:
            parent_req = self.db.query(Requirement).filter(
                Requirement.id == requirement.parent_id
            ).first()
            
            if parent_req:
                # 建议继承父需求的某些追溯关系
                parent_links = self.db.query(RequirementTraceabilityLink).filter(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == parent_req.id
                ).all()
                
                for link in parent_links:
                    suggestions.append({
                        "target_type": link.target_type,
                        "link_type": link.link_type.value,
                        "confidence": 0.6,
                        "reason": f"基于父需求 {parent_req.requirement_code} 的追溯关系",
                        "parent_requirement": {
                            "id": parent_req.id,
                            "code": parent_req.requirement_code,
                            "title": parent_req.title
                        }
                    })
        
        return suggestions
    
    def _suggest_temporal_links(self, requirement: Requirement) -> List[Dict[str, Any]]:
        """基于时间关系建议链接"""
        suggestions = []
        
        # 查找时间上相近创建的需求
        time_window = timedelta(days=7)  # 7天内
        start_time = requirement.created_at - time_window
        end_time = requirement.created_at + time_window
        
        nearby_requirements = self.db.query(Requirement).filter(
            Requirement.project_id == requirement.project_id,
            Requirement.id != requirement.id,
            Requirement.created_at.between(start_time, end_time)
        ).limit(3).all()
        
        for nearby_req in nearby_requirements:
            suggestions.append({
                "target_type": "requirement",
                "target_id": nearby_req.id,
                "link_type": "RELATES_TO",
                "confidence": 0.4,
                "reason": f"与需求 {nearby_req.requirement_code} 创建时间相近",
                "related_requirement": {
                    "id": nearby_req.id,
                    "code": nearby_req.requirement_code,
                    "title": nearby_req.title
                }
            })
        
        return suggestions
    
    def _extract_keywords(self, title: str, description: str) -> List[str]:
        """提取关键词"""
        # 简化的关键词提取（实际应该使用更复杂的NLP技术）
        text = f"{title} {description or ''}".lower()
        
        # 常见的停用词
        stop_words = {
            "的", "是", "在", "有", "和", "与", "或", "但", "如果", "那么",
            "这", "那", "一个", "一种", "可以", "能够", "需要", "应该", "必须"
        }
        
        # 简单的词汇分割和过滤
        words = []
        for word in text.split():
            word = word.strip("，。！？；：""''（）【】")
            if len(word) >= 2 and word not in stop_words:
                words.append(word)
        
        return words[:10]  # 返回前10个关键词
    
    def _calculate_orphan_statistics(self, result: OrphanAnalysisResult):
        """计算孤立统计信息"""
        # 按类型统计
        type_counts = defaultdict(int)
        for orphaned_req in result.orphaned_requirements:
            for orphan_type in orphaned_req.orphan_types:
                type_counts[orphan_type.value] += 1
        
        result.orphan_statistics = dict(type_counts)
        
        # 按严重程度统计
        severity_counts = defaultdict(int)
        for orphaned_req in result.orphaned_requirements:
            severity_counts[orphaned_req.severity] += 1
        
        result.severity_distribution = dict(severity_counts)
    
    def _generate_orphan_recommendations(self, result: OrphanAnalysisResult) -> List[str]:
        """生成孤立需求改进建议"""
        recommendations = []
        
        total_orphaned = len(result.orphaned_requirements)
        orphan_rate = total_orphaned / result.total_requirements if result.total_requirements > 0 else 0
        
        # 基于孤立率生成建议
        if orphan_rate > 0.3:
            recommendations.append(f"孤立需求比例较高 ({orphan_rate:.1%})，建议系统性地完善追溯关系")
        elif orphan_rate > 0.1:
            recommendations.append(f"存在一定比例的孤立需求 ({orphan_rate:.1%})，建议逐步完善追溯关系")
        
        # 基于严重程度分布生成建议
        critical_count = result.severity_distribution.get("critical", 0)
        high_count = result.severity_distribution.get("high", 0)
        
        if critical_count > 0:
            recommendations.append(f"发现 {critical_count} 个严重孤立需求，建议优先处理")
        
        if high_count > 0:
            recommendations.append(f"发现 {high_count} 个高优先级孤立需求，建议及时处理")
        
        # 基于孤立类型生成建议
        stats = result.orphan_statistics
        
        if stats.get("completely_orphaned", 0) > 0:
            recommendations.append("发现完全孤立的需求，建议建立基本的追溯关系")
        
        if stats.get("no_test_coverage", 0) > 0:
            recommendations.append("多个需求缺少测试覆盖，建议完善测试追溯")
        
        if stats.get("no_task_implementation", 0) > 0:
            recommendations.append("多个需求缺少任务实现，建议创建相应的开发任务")
        
        return recommendations
    
    def _generate_specific_recommendations(self, requirement: Requirement, orphan_type: OrphanType) -> List[str]:
        """为特定孤立类型生成建议"""
        recommendations = []
        
        if orphan_type == OrphanType.COMPLETELY_ORPHANED:
            recommendations.extend([
                "建立与业务需求的追溯关系，明确需求来源",
                "创建相应的设计文档并建立追溯关系",
                "创建测试用例并建立追溯关系",
                "创建开发任务并建立追溯关系"
            ])
        elif orphan_type == OrphanType.NO_UPSTREAM:
            recommendations.extend([
                "明确需求的业务来源或用户故事",
                "建立与上级需求或业务目标的追溯关系"
            ])
        elif orphan_type == OrphanType.NO_DOWNSTREAM:
            recommendations.extend([
                "创建相应的设计文档",
                "分解为具体的开发任务",
                "创建验证需求的测试用例"
            ])
        elif orphan_type == OrphanType.NO_TEST_COVERAGE:
            recommendations.extend([
                "创建功能测试用例",
                "创建验收测试用例",
                "建立需求与测试用例的追溯关系"
            ])
        elif orphan_type == OrphanType.NO_TASK_IMPLEMENTATION:
            recommendations.extend([
                "分解需求为具体的开发任务",
                "分配任务给相应的开发人员",
                "建立需求与任务的追溯关系"
            ])
        elif orphan_type == OrphanType.NO_DESIGN_REFERENCE:
            recommendations.extend([
                "创建详细的设计文档",
                "创建界面设计或架构设计",
                "建立需求与设计的追溯关系"
            ])
        
        return recommendations