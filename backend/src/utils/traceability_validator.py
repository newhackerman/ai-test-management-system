"""
需求追溯关系验证器

本模块实现追溯关系的验证功能，包括：
- 追溯链接合法性验证
- 循环依赖检测
- 追溯一致性检查
- 追溯完整性验证
"""

from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict, deque
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.requirement import (
    Requirement, RequirementTraceabilityLink, TraceabilityLinkType,
    RequirementStatus, RequirementType
)
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TraceabilityValidationResult:
    """追溯验证结果"""
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.suggestions: List[str] = []

class TraceabilityValidator:
    """追溯关系验证器"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 定义有效的追溯链接类型组合
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
            ],
            ("business_requirement", "requirement"): [
                TraceabilityLinkType.DERIVES_FROM
            ],
            ("task", "test_case"): [
                TraceabilityLinkType.VALIDATES
            ]
        }
        
        # 定义互斥的链接类型
        self.mutually_exclusive_links = [
            (TraceabilityLinkType.IMPLEMENTS, TraceabilityLinkType.DERIVES_FROM),
            (TraceabilityLinkType.TESTS, TraceabilityLinkType.VALIDATES)
        ]
    
    def validate_link_creation(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        link_type: TraceabilityLinkType
    ) -> TraceabilityValidationResult:
        """验证追溯链接创建"""
        result = TraceabilityValidationResult()
        
        try:
            # 1. 验证基本数据
            self._validate_basic_data(
                source_type, source_id, target_type, target_id, link_type, result
            )
            
            # 2. 验证对象存在性
            self._validate_object_existence(
                source_type, source_id, target_type, target_id, result
            )
            
            # 3. 验证链接类型合法性
            self._validate_link_type_compatibility(
                source_type, target_type, link_type, result
            )
            
            # 4. 验证重复链接
            self._validate_duplicate_links(
                source_type, source_id, target_type, target_id, link_type, result
            )
            
            # 5. 验证循环依赖
            self._validate_circular_dependency(
                source_type, source_id, target_type, target_id, result
            )
            
            # 6. 验证业务规则
            self._validate_business_rules(
                source_type, source_id, target_type, target_id, link_type, result
            )
            
            # 7. 生成建议
            self._generate_suggestions(
                source_type, source_id, target_type, target_id, link_type, result
            )
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"验证过程中发生错误: {str(e)}")
            logger.error(f"追溯链接验证失败: {str(e)}")
        
        return result
    
    def validate_project_traceability(self, project_id: int) -> TraceabilityValidationResult:
        """验证项目追溯完整性"""
        result = TraceabilityValidationResult()
        
        try:
            # 1. 验证追溯覆盖率
            self._validate_traceability_coverage(project_id, result)
            
            # 2. 验证追溯一致性
            self._validate_traceability_consistency(project_id, result)
            
            # 3. 检测孤立对象
            self._detect_orphaned_objects(project_id, result)
            
            # 4. 检测循环引用
            self._detect_circular_references(project_id, result)
            
            # 5. 验证追溯质量
            self._validate_traceability_quality(project_id, result)
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"项目追溯验证过程中发生错误: {str(e)}")
            logger.error(f"项目追溯验证失败: {str(e)}")
        
        return result
    
    def _validate_basic_data(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        link_type: TraceabilityLinkType,
        result: TraceabilityValidationResult
    ):
        """验证基本数据"""
        if not source_type or not source_type.strip():
            result.is_valid = False
            result.errors.append("源对象类型不能为空")
        
        if not target_type or not target_type.strip():
            result.is_valid = False
            result.errors.append("目标对象类型不能为空")
        
        if source_id <= 0:
            result.is_valid = False
            result.errors.append("源对象ID必须大于0")
        
        if target_id <= 0:
            result.is_valid = False
            result.errors.append("目标对象ID必须大于0")
        
        if source_type == target_type and source_id == target_id:
            result.is_valid = False
            result.errors.append("不能创建指向自身的追溯链接")
        
        if not isinstance(link_type, TraceabilityLinkType):
            result.is_valid = False
            result.errors.append("无效的链接类型")
    
    def _validate_object_existence(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        result: TraceabilityValidationResult
    ):
        """验证对象存在性"""
        # 验证源对象
        if source_type == "requirement":
            source_obj = self.db.query(Requirement).filter(
                Requirement.id == source_id
            ).first()
            if not source_obj:
                result.is_valid = False
                result.errors.append(f"源需求 {source_id} 不存在")
        
        # 验证目标对象
        if target_type == "requirement":
            target_obj = self.db.query(Requirement).filter(
                Requirement.id == target_id
            ).first()
            if not target_obj:
                result.is_valid = False
                result.errors.append(f"目标需求 {target_id} 不存在")
        
        # 对于其他类型的对象，这里应该调用相应模块的验证方法
        # 暂时只验证需求类型
    
    def _validate_link_type_compatibility(
        self,
        source_type: str,
        target_type: str,
        link_type: TraceabilityLinkType,
        result: TraceabilityValidationResult
    ):
        """验证链接类型兼容性"""
        combination_key = (source_type, target_type)
        
        if combination_key not in self.valid_link_combinations:
            result.is_valid = False
            result.errors.append(
                f"不支持从 {source_type} 到 {target_type} 的追溯链接"
            )
            return
        
        valid_types = self.valid_link_combinations[combination_key]
        if link_type not in valid_types:
            result.is_valid = False
            result.errors.append(
                f"链接类型 {link_type.value} 不适用于 {source_type} -> {target_type}"
            )
            
            # 提供建议的链接类型
            valid_type_names = [t.value for t in valid_types]
            result.suggestions.append(
                f"建议使用以下链接类型之一: {', '.join(valid_type_names)}"
            )
    
    def _validate_duplicate_links(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        link_type: TraceabilityLinkType,
        result: TraceabilityValidationResult
    ):
        """验证重复链接"""
        existing_link = self.db.query(RequirementTraceabilityLink).filter(
            RequirementTraceabilityLink.source_type == source_type,
            RequirementTraceabilityLink.source_id == source_id,
            RequirementTraceabilityLink.target_type == target_type,
            RequirementTraceabilityLink.target_id == target_id,
            RequirementTraceabilityLink.link_type == link_type
        ).first()
        
        if existing_link:
            result.is_valid = False
            result.errors.append("相同的追溯链接已存在")
        
        # 检查互斥的链接类型
        for exclusive_pair in self.mutually_exclusive_links:
            if link_type in exclusive_pair:
                other_type = exclusive_pair[1] if link_type == exclusive_pair[0] else exclusive_pair[0]
                
                conflicting_link = self.db.query(RequirementTraceabilityLink).filter(
                    RequirementTraceabilityLink.source_type == source_type,
                    RequirementTraceabilityLink.source_id == source_id,
                    RequirementTraceabilityLink.target_type == target_type,
                    RequirementTraceabilityLink.target_id == target_id,
                    RequirementTraceabilityLink.link_type == other_type
                ).first()
                
                if conflicting_link:
                    result.warnings.append(
                        f"存在冲突的链接类型 {other_type.value}，建议先删除冲突链接"
                    )
    
    def _validate_circular_dependency(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        result: TraceabilityValidationResult
    ):
        """验证循环依赖"""
        if source_type != target_type:
            return  # 不同类型的对象不会形成循环
        
        # 使用深度优先搜索检测循环
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: int) -> bool:
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            # 获取所有下游节点
            downstream_links = self.db.query(RequirementTraceabilityLink).filter(
                RequirementTraceabilityLink.source_type == source_type,
                RequirementTraceabilityLink.source_id == node_id,
                RequirementTraceabilityLink.target_type == target_type
            ).all()
            
            for link in downstream_links:
                if dfs(link.target_id):
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        # 检查从目标节点是否能到达源节点
        if dfs(target_id):
            result.is_valid = False
            result.errors.append("创建此链接会导致循环依赖")
    
    def _validate_business_rules(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        link_type: TraceabilityLinkType,
        result: TraceabilityValidationResult
    ):
        """验证业务规则"""
        # 规则1: 已关闭或已取消的需求不能创建新的追溯链接
        if source_type == "requirement":
            source_req = self.db.query(Requirement).filter(
                Requirement.id == source_id
            ).first()
            if source_req and source_req.status in [
                RequirementStatus.CLOSED, RequirementStatus.CANCELLED
            ]:
                result.warnings.append("源需求已关闭或取消，不建议创建新的追溯链接")
        
        # 规则2: 草稿状态的需求不建议创建追溯链接
        if source_type == "requirement":
            source_req = self.db.query(Requirement).filter(
                Requirement.id == source_id
            ).first()
            if source_req and source_req.status == RequirementStatus.DRAFT:
                result.warnings.append("源需求仍为草稿状态，建议完善后再创建追溯链接")
        
        # 规则3: 不同项目的需求之间的追溯链接需要特别注意
        if source_type == "requirement" and target_type == "requirement":
            source_req = self.db.query(Requirement).filter(
                Requirement.id == source_id
            ).first()
            target_req = self.db.query(Requirement).filter(
                Requirement.id == target_id
            ).first()
            
            if source_req and target_req and source_req.project_id != target_req.project_id:
                result.warnings.append("跨项目的需求追溯链接，请确认是否必要")
    
    def _generate_suggestions(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        link_type: TraceabilityLinkType,
        result: TraceabilityValidationResult
    ):
        """生成建议"""
        # 建议1: 检查是否需要反向链接
        if link_type in [TraceabilityLinkType.DERIVES_FROM, TraceabilityLinkType.REFINES]:
            reverse_link = self.db.query(RequirementTraceabilityLink).filter(
                RequirementTraceabilityLink.source_type == target_type,
                RequirementTraceabilityLink.source_id == target_id,
                RequirementTraceabilityLink.target_type == source_type,
                RequirementTraceabilityLink.target_id == source_id
            ).first()
            
            if not reverse_link:
                result.suggestions.append("考虑创建对应的反向追溯链接以保持一致性")
        
        # 建议2: 检查是否缺少其他类型的追溯链接
        if source_type == "requirement" and target_type == "task":
            test_links = self.db.query(RequirementTraceabilityLink).filter(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == source_id,
                RequirementTraceabilityLink.target_type == "test_case"
            ).count()
            
            if test_links == 0:
                result.suggestions.append("建议为此需求创建测试用例追溯链接")
    
    def _validate_traceability_coverage(
        self,
        project_id: int,
        result: TraceabilityValidationResult
    ):
        """验证追溯覆盖率"""
        # 获取项目需求总数
        total_requirements = self.db.query(Requirement).filter(
            Requirement.project_id == project_id
        ).count()
        
        if total_requirements == 0:
            result.warnings.append("项目中没有需求")
            return
        
        # 获取有追溯链接的需求数量
        covered_requirements = self.db.query(Requirement.id).filter(
            Requirement.project_id == project_id
        ).join(
            RequirementTraceabilityLink,
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
        ).distinct().count()
        
        coverage_rate = covered_requirements / total_requirements
        
        if coverage_rate < 0.5:
            result.warnings.append(f"追溯覆盖率较低 ({coverage_rate:.1%})，建议完善追溯链接")
        elif coverage_rate < 0.8:
            result.suggestions.append(f"追溯覆盖率为 {coverage_rate:.1%}，可以进一步提升")
    
    def _validate_traceability_consistency(
        self,
        project_id: int,
        result: TraceabilityValidationResult
    ):
        """验证追溯一致性"""
        # 检查双向链接的一致性
        links = self.db.query(RequirementTraceabilityLink).join(
            Requirement,
            and_(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == Requirement.id
            )
        ).filter(
            Requirement.project_id == project_id
        ).all()
        
        inconsistent_count = 0
        for link in links:
            if link.link_type in [TraceabilityLinkType.DERIVES_FROM, TraceabilityLinkType.REFINES]:
                # 检查是否存在对应的反向链接
                reverse_link = self.db.query(RequirementTraceabilityLink).filter(
                    RequirementTraceabilityLink.source_type == link.target_type,
                    RequirementTraceabilityLink.source_id == link.target_id,
                    RequirementTraceabilityLink.target_type == link.source_type,
                    RequirementTraceabilityLink.target_id == link.source_id
                ).first()
                
                if not reverse_link:
                    inconsistent_count += 1
        
        if inconsistent_count > 0:
            result.warnings.append(f"发现 {inconsistent_count} 个不一致的追溯链接")
    
    def _detect_orphaned_objects(
        self,
        project_id: int,
        result: TraceabilityValidationResult
    ):
        """检测孤立对象"""
        # 检测孤立的需求
        orphaned_requirements = self.db.query(Requirement).filter(
            Requirement.project_id == project_id
        ).outerjoin(
            RequirementTraceabilityLink,
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
        ).filter(
            RequirementTraceabilityLink.id.is_(None)
        ).count()
        
        if orphaned_requirements > 0:
            result.warnings.append(f"发现 {orphaned_requirements} 个孤立的需求")
    
    def _detect_circular_references(
        self,
        project_id: int,
        result: TraceabilityValidationResult
    ):
        """检测循环引用"""
        # 获取项目内的所有需求追溯链接
        links = self.db.query(RequirementTraceabilityLink).join(
            Requirement,
            and_(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == Requirement.id
            )
        ).filter(
            Requirement.project_id == project_id,
            RequirementTraceabilityLink.target_type == "requirement"
        ).all()
        
        # 构建图
        graph = defaultdict(list)
        for link in links:
            graph[link.source_id].append(link.target_id)
        
        # 使用DFS检测循环
        visited = set()
        rec_stack = set()
        circular_count = 0
        
        def dfs(node: int) -> bool:
            nonlocal circular_count
            if node in rec_stack:
                circular_count += 1
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph[node]:
                if dfs(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        # 检查所有节点
        for node in graph:
            if node not in visited:
                dfs(node)
        
        if circular_count > 0:
            result.errors.append(f"发现 {circular_count} 个循环引用")
    
    def _validate_traceability_quality(
        self,
        project_id: int,
        result: TraceabilityValidationResult
    ):
        """验证追溯质量"""
        # 检查追溯链接的描述完整性
        links_without_description = self.db.query(RequirementTraceabilityLink).join(
            Requirement,
            and_(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == Requirement.id
            )
        ).filter(
            Requirement.project_id == project_id,
            or_(
                RequirementTraceabilityLink.description.is_(None),
                RequirementTraceabilityLink.description == ""
            )
        ).count()
        
        if links_without_description > 0:
            result.suggestions.append(
                f"有 {links_without_description} 个追溯链接缺少描述，建议补充"
            )
        
        # 检查追溯链接的时效性（创建时间过久的链接可能需要重新验证）
        from datetime import datetime, timedelta
        old_threshold = datetime.utcnow() - timedelta(days=365)  # 一年前
        
        old_links = self.db.query(RequirementTraceabilityLink).join(
            Requirement,
            and_(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == Requirement.id
            )
        ).filter(
            Requirement.project_id == project_id,
            RequirementTraceabilityLink.created_at < old_threshold
        ).count()
        
        if old_links > 0:
            result.suggestions.append(
                f"有 {old_links} 个追溯链接创建时间较久，建议重新验证其有效性"
            )