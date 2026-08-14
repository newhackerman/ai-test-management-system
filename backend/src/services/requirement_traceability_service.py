"""
需求追溯管理服务

本模块实现需求追溯管理的核心功能，包括：
- 追溯链接管理
- 追溯关系验证
- 追溯覆盖率分析
- 智能追溯分析
- 追溯矩阵生成
- 追溯一致性检查
- 孤立需求识别
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, text, select
from collections import defaultdict, deque

from ..models.requirement import (
    Requirement, RequirementTraceabilityLink, TraceabilityLinkType,
    RequirementStatus, RequirementType
)
from ..models.project import Project
from ..core.database import get_db
from ..core.exceptions import NotFoundError
import logging

logger = logging.getLogger(__name__)

class TraceabilityAnalysisResult:
    """追溯分析结果"""
    def __init__(self):
        self.coverage_rate: float = 0.0
        self.missing_links: List[Dict[str, Any]] = []
        self.orphaned_items: List[Dict[str, Any]] = []
        self.circular_references: List[List[int]] = []
        self.inconsistent_links: List[Dict[str, Any]] = []
        self.recommendations: List[str] = []

class TraceabilityMatrix:
    """追溯矩阵"""
    def __init__(self, project_id: int, matrix_type: str):
        self.project_id = project_id
        self.matrix_type = matrix_type
        self.requirements: List[Dict[str, Any]] = []
        self.targets: List[Dict[str, Any]] = []
        self.matrix_data: Dict[str, Dict[str, bool]] = {}
        self.coverage_stats: Dict[str, Any] = {}
        self.generated_at = datetime.utcnow()

class RequirementTraceabilityService:
    """需求追溯管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_traceability_link(
        self,
        link_data: dict = None,
        creator_id: int = None,
        source_type: str = None,
        source_id: int = None,
        target_type: str = None,
        target_id: int = None,
        link_type: TraceabilityLinkType = None,
        description: str = None
    ) -> RequirementTraceabilityLink:
        """创建追溯链接"""
        try:
            # 兼容 link_data 字典调用与关键字参数调用
            if link_data:
                source_type = link_data.get("source_type", source_type)
                source_id = link_data.get("source_id", source_id)
                target_type = link_data.get("target_type", target_type)
                target_id = link_data.get("target_id", target_id)
                link_type = link_data.get("link_type", link_type)
                description = link_data.get("description", description)
                if creator_id is None:
                    creator_id = link_data.get("creator_id")

            # 1. 验证链接数据
            await self._validate_link_data(source_type, source_id, target_type, target_id, link_type)
            
            # 2. 检查是否已存在相同链接
            existing_link = (await self.db.execute(
                select(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.source_type == source_type,
                    RequirementTraceabilityLink.source_id == source_id,
                    RequirementTraceabilityLink.target_type == target_type,
                    RequirementTraceabilityLink.target_id == target_id,
                    RequirementTraceabilityLink.link_type == link_type
                )
            )).scalars().first()
            
            if existing_link:
                raise ValueError("追溯链接已存在")
            
            # 3. 检查循环引用
            if await self._has_circular_reference(source_type, source_id, target_type, target_id):
                raise ValueError("创建链接会导致循环引用")
            
            # 4. 创建追溯链接
            link = RequirementTraceabilityLink(
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                link_type=link_type,
                description=description,
                created_by=creator_id
            )
            
            self.db.add(link)
            await self.db.commit()
            await self.db.refresh(link)
            
            logger.info(f"创建追溯链接成功: {source_type}:{source_id} -> {target_type}:{target_id}")
            return link
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建追溯链接失败: {str(e)}")
            raise
    
    async def delete_traceability_link(self, link_id: int, user_id: int) -> bool:
        """删除追溯链接"""
        try:
            link = (await self.db.execute(
                select(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.id == link_id
                )
            )).scalars().first()
            
            if not link:
                raise ValueError("追溯链接不存在")
            
            await self.db.delete(link)
            await self.db.commit()
            
            logger.info(f"删除追溯链接成功: {link_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除追溯链接失败: {str(e)}")
            raise
    
    async def get_requirement_traceability(
        self,
        requirement_id: int,
        direction: str = "both",
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """获取需求追溯关系"""
        try:
            requirement = (await self.db.execute(
                select(Requirement).where(
                    Requirement.id == requirement_id
                )
            )).scalars().first()
            
            if not requirement:
                raise NotFoundError("需求不存在")
            
            # 获取上游追溯（需求来源）
            upstream_links = []
            if direction in ["upstream", "both"]:
                upstream_links = await self._get_upstream_links(
                    "requirement", requirement_id, max_depth
                )
            
            # 获取下游追溯（实现追踪）
            downstream_links = []
            if direction in ["downstream", "both"]:
                downstream_links = await self._get_downstream_links(
                    "requirement", requirement_id, max_depth
                )
            
            # 构建追溯树
            traceability_tree = await self._build_traceability_tree(
                requirement_id, upstream_links, downstream_links
            )
            
            # 计算追溯覆盖率
            coverage_analysis = await self._calculate_traceability_coverage(requirement_id)
            
            return {
                "requirement_id": requirement_id,
                "requirement": requirement.to_dict(),
                "upstream_links": upstream_links,
                "downstream_links": downstream_links,
                "traceability_tree": traceability_tree,
                "coverage_analysis": coverage_analysis,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取需求追溯关系失败: {str(e)}")
            raise
    
    async def analyze_change_impact(
        self,
        requirement_id: int,
        change_description: str = None
    ) -> Dict[str, Any]:
        """分析变更影响"""
        try:
            # 1. 获取需求追溯关系
            traceability = await self.get_requirement_traceability(requirement_id)
            
            # 2. 分析直接影响
            direct_impacts = await self._analyze_direct_impacts(requirement_id)
            
            # 3. 分析间接影响
            indirect_impacts = await self._analyze_indirect_impacts(
                traceability["downstream_links"]
            )
            
            # 4. 计算影响范围
            impact_scope = await self._calculate_impact_scope(
                direct_impacts, indirect_impacts
            )
            
            # 5. 生成影响分析报告
            impact_analysis = {
                "requirement_id": requirement_id,
                "change_description": change_description,
                "direct_impacts": direct_impacts,
                "indirect_impacts": indirect_impacts,
                "impact_scope": impact_scope,
                "affected_requirements": impact_scope.get("requirements", []),
                "affected_test_cases": impact_scope.get("test_cases", []),
                "affected_tasks": impact_scope.get("tasks", []),
                "risk_level": self._calculate_risk_level(impact_scope),
                "recommendations": self._generate_impact_recommendations(impact_scope),
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            return impact_analysis
            
        except Exception as e:
            logger.error(f"分析变更影响失败: {str(e)}")
            raise
    
    async def get_traceability_link_by_id(self, link_id: int) -> Optional[RequirementTraceabilityLink]:
        """根据ID获取追溯链接
        
        路由层使用 TraceabilityLinkResponse.from_orm(link) 处理返回值，
        因此这里直接返回 RequirementTraceabilityLink ORM 对象；找不到时返回 None，
        由路由层负责抛出 404。
        """
        try:
            link = (await self.db.execute(
                select(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.id == link_id
                )
            )).scalars().first()
            return link
        except Exception as e:
            logger.error(f"获取追溯链接失败: {str(e)}")
            raise
    
    async def search_traceability_links(self, search_params: dict) -> Tuple[List[RequirementTraceabilityLink], int]:
        """搜索追溯链接
        
        路由层解包返回值为 (links, total)，因此这里返回一个元组。
        search_params 可能包含的键：source_type, source_id, target_type, target_id,
        link_type, project_id, skip, limit。保持简单：按条件过滤并返回 (结果列表, 结果数量)。
        """
        try:
            stmt = select(RequirementTraceabilityLink)
            
            if "source_type" in search_params and search_params["source_type"] is not None:
                stmt = stmt.where(RequirementTraceabilityLink.source_type == search_params["source_type"])
            if "source_id" in search_params and search_params["source_id"] is not None:
                stmt = stmt.where(RequirementTraceabilityLink.source_id == search_params["source_id"])
            if "target_type" in search_params and search_params["target_type"] is not None:
                stmt = stmt.where(RequirementTraceabilityLink.target_type == search_params["target_type"])
            if "target_id" in search_params and search_params["target_id"] is not None:
                stmt = stmt.where(RequirementTraceabilityLink.target_id == search_params["target_id"])
            if "link_type" in search_params and search_params["link_type"] is not None:
                stmt = stmt.where(RequirementTraceabilityLink.link_type == search_params["link_type"])
            
            # project_id 过滤：通过 join Requirement 限定源需求所属项目
            if "project_id" in search_params and search_params["project_id"] is not None:
                stmt = stmt.join(
                    Requirement,
                    and_(
                        RequirementTraceabilityLink.source_type == "requirement",
                        RequirementTraceabilityLink.source_id == Requirement.id
                    )
                ).where(Requirement.project_id == search_params["project_id"])
            
            # 排序保证结果稳定
            stmt = stmt.order_by(RequirementTraceabilityLink.id.desc())
            
            # 分页
            skip = search_params.get("skip", 0) or 0
            limit = search_params.get("limit", 50) or 50
            stmt = stmt.offset(skip).limit(limit)
            
            links = (await self.db.execute(stmt)).scalars().all()
            return links, len(links)
        except Exception as e:
            logger.error(f"搜索追溯链接失败: {str(e)}")
            raise
    
    async def get_traceability_coverage(self, project_id: int, coverage_type: str = "all") -> Dict[str, Any]:
        """获取追溯覆盖率
        
        路由层将返回值直接放入 coverage_stats 字段返回，因此这里返回一个可序列化的 dict。
        """
        try:
            total_requirements = (await self.db.execute(
                select(func.count()).select_from(Requirement).where(
                    Requirement.project_id == project_id
                )
            )).scalar() or 0
            
            # 有任意追溯链接的需求数量
            covered_requirements = (await self.db.execute(
                select(func.count(func.distinct(Requirement.id))).join(
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
                ).where(
                    Requirement.project_id == project_id
                )
            )).scalar() or 0
            
            coverage_rate = (
                covered_requirements / total_requirements
                if total_requirements and total_requirements > 0
                else 0.0
            )
            
            # 无追溯链接的需求（孤立需求）
            uncovered = (await self.db.execute(
                select(Requirement.id).outerjoin(
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
                ).where(
                    Requirement.project_id == project_id,
                    RequirementTraceabilityLink.id.is_(None)
                )
            )).scalars().all()
            
            return {
                "project_id": project_id,
                "coverage_type": coverage_type,
                "total_requirements": total_requirements,
                "covered_requirements": covered_requirements,
                "uncovered_requirements": list(uncovered),
                "coverage_rate": coverage_rate
            }
        except Exception as e:
            logger.error(f"获取追溯覆盖率失败: {str(e)}")
            raise
    
    async def get_orphaned_requirements(self, project_id: int) -> List[Dict[str, Any]]:
        """获取孤立需求（没有任何追溯链接的需求）
        
        路由层会包裹每一项返回，因此这里返回 dict 列表。找不到时返回 []。
        """
        try:
            orphaned_items = await self._identify_orphaned_items(project_id)
            return orphaned_items
        except Exception as e:
            logger.error(f"获取孤立需求失败: {str(e)}")
            raise
    
    async def check_traceability_consistency(self, project_id: int) -> List[Dict[str, Any]]:
        """检查追溯一致性
        
        路由层将返回值直接放入 consistency_report 字段返回，因此这里返回 dict 列表。
        找不到时返回 []。
        """
        try:
            return await self._check_traceability_consistency(project_id)
        except Exception as e:
            logger.error(f"检查追溯一致性失败: {str(e)}")
            raise
    
    async def generate_traceability_matrix(
        self,
        project_id: int,
        matrix_type: str = "requirement_to_test",
        include_indirect: bool = False
    ) -> TraceabilityMatrix:
        """生成追溯矩阵

        Args:
            project_id: 项目ID
            matrix_type: 矩阵类型 (requirement_to_test / requirement_to_task / requirement_to_design)
            include_indirect: 是否包含间接追溯（目前仅作标志位，留待未来扩展）
        """
        try:
            # include_indirect 暂只作标志位：直接矩阵生成遵循既有行为，
            # 防止调用方传入未知 kwarg 导致 TypeError → 500。
            matrix = TraceabilityMatrix(project_id, matrix_type)
            
            # 1. 获取项目需求
            requirements = (await self.db.execute(
                select(Requirement).where(
                    Requirement.project_id == project_id
                )
            )).scalars().all()
            matrix.requirements = [req.to_dict() for req in requirements]
            
            # 2. 根据矩阵类型获取目标对象
            if matrix_type == "requirement_to_test":
                matrix.targets = await self._get_test_cases_by_project(project_id)
                links = await self._get_requirement_to_test_links(project_id)
            elif matrix_type == "requirement_to_task":
                matrix.targets = await self._get_tasks_by_project(project_id)
                links = await self._get_requirement_to_task_links(project_id)
            elif matrix_type == "requirement_to_design":
                matrix.targets = await self._get_designs_by_project(project_id)
                links = await self._get_requirement_to_design_links(project_id)
            else:
                raise ValueError(f"不支持的矩阵类型: {matrix_type}")
            
            # 3. 构建矩阵数据
            matrix.matrix_data = await self._build_matrix_data(
                matrix.requirements, matrix.targets, links
            )
            
            # 4. 计算覆盖率统计
            matrix.coverage_stats = await self._calculate_matrix_coverage(matrix.matrix_data)
            
            return matrix
            
        except Exception as e:
            logger.error(f"生成追溯矩阵失败: {str(e)}")
            raise
    
    async def analyze_traceability_quality(self, project_id: int) -> TraceabilityAnalysisResult:
        """分析追溯质量"""
        try:
            result = TraceabilityAnalysisResult()
            
            # 1. 计算追溯覆盖率
            result.coverage_rate = await self._calculate_project_coverage_rate(project_id)
            
            # 2. 识别缺失的追溯链接
            result.missing_links = await self._identify_missing_links(project_id)
            
            # 3. 识别孤立的需求和对象
            result.orphaned_items = await self._identify_orphaned_items(project_id)
            
            # 4. 检测循环引用
            result.circular_references = await self._detect_circular_references(project_id)
            
            # 5. 检查追溯一致性
            result.inconsistent_links = await self._check_traceability_consistency(project_id)
            
            # 6. 生成改进建议
            result.recommendations = await self._generate_quality_recommendations(result)
            
            return result
            
        except Exception as e:
            logger.error(f"分析追溯质量失败: {str(e)}")
            raise
    
    async def _validate_link_data(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        link_type: TraceabilityLinkType
    ):
        """验证链接数据"""
        # 验证源对象存在
        if source_type == "requirement":
            source_obj = (await self.db.execute(
                select(Requirement).where(
                    Requirement.id == source_id
                )
            )).scalars().first()
            if not source_obj:
                raise ValueError("源需求不存在")
        
        # 验证目标对象存在
        if target_type == "requirement":
            target_obj = (await self.db.execute(
                select(Requirement).where(
                    Requirement.id == target_id
                )
            )).scalars().first()
            if not target_obj:
                raise ValueError("目标需求不存在")
        
        # 验证链接类型的合理性
        valid_combinations = {
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
        
        combination_key = (source_type, target_type)
        if combination_key in valid_combinations:
            if link_type not in valid_combinations[combination_key]:
                raise ValueError(f"链接类型 {link_type} 不适用于 {source_type} -> {target_type}")
    
    async def _has_circular_reference(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int
    ) -> bool:
        """检查是否存在循环引用"""
        if source_type != target_type:
            return False
        
        # 使用深度优先搜索检测循环
        visited = set()
        rec_stack = set()
        
        async def dfs(node_id: int) -> bool:
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            # 获取所有下游节点
            downstream_links = (await self.db.execute(
                select(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.source_type == source_type,
                    RequirementTraceabilityLink.source_id == node_id,
                    RequirementTraceabilityLink.target_type == target_type
                )
            )).scalars().all()
            
            for link in downstream_links:
                if await dfs(link.target_id):
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        # 检查从目标节点是否能到达源节点
        return await dfs(target_id)
    
    async def _get_upstream_links(
        self,
        object_type: str,
        object_id: int,
        max_depth: int
    ) -> List[Dict[str, Any]]:
        """获取上游追溯链接"""
        links = []
        visited = set()
        queue = deque([(object_type, object_id, 0)])
        
        while queue and len(links) < 1000:  # 防止无限循环
            current_type, current_id, depth = queue.popleft()
            
            if depth >= max_depth or (current_type, current_id) in visited:
                continue
            
            visited.add((current_type, current_id))
            
            # 查询指向当前对象的链接
            upstream_links = (await self.db.execute(
                select(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.target_type == current_type,
                    RequirementTraceabilityLink.target_id == current_id
                )
            )).scalars().all()
            
            for link in upstream_links:
                link_data = link.to_dict()
                link_data["depth"] = depth
                links.append(link_data)
                
                # 添加到队列继续搜索
                queue.append((link.source_type, link.source_id, depth + 1))
        
        return links
    
    async def _get_downstream_links(
        self,
        object_type: str,
        object_id: int,
        max_depth: int
    ) -> List[Dict[str, Any]]:
        """获取下游追溯链接"""
        links = []
        visited = set()
        queue = deque([(object_type, object_id, 0)])
        
        while queue and len(links) < 1000:  # 防止无限循环
            current_type, current_id, depth = queue.popleft()
            
            if depth >= max_depth or (current_type, current_id) in visited:
                continue
            
            visited.add((current_type, current_id))
            
            # 查询从当前对象出发的链接
            downstream_links = (await self.db.execute(
                select(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.source_type == current_type,
                    RequirementTraceabilityLink.source_id == current_id
                )
            )).scalars().all()
            
            for link in downstream_links:
                link_data = link.to_dict()
                link_data["depth"] = depth
                links.append(link_data)
                
                # 添加到队列继续搜索
                queue.append((link.target_type, link.target_id, depth + 1))
        
        return links
    
    async def _build_traceability_tree(
        self,
        requirement_id: int,
        upstream_links: List[Dict[str, Any]],
        downstream_links: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建追溯树"""
        tree = {
            "root": {
                "type": "requirement",
                "id": requirement_id,
                "children": [],
                "parents": []
            }
        }
        
        # 构建上游树
        for link in upstream_links:
            if link["target_type"] == "requirement" and link["target_id"] == requirement_id:
                parent_node = {
                    "type": link["source_type"],
                    "id": link["source_id"],
                    "link_type": link["link_type"],
                    "depth": link["depth"]
                }
                tree["root"]["parents"].append(parent_node)
        
        # 构建下游树
        for link in downstream_links:
            if link["source_type"] == "requirement" and link["source_id"] == requirement_id:
                child_node = {
                    "type": link["target_type"],
                    "id": link["target_id"],
                    "link_type": link["link_type"],
                    "depth": link["depth"]
                }
                tree["root"]["children"].append(child_node)
        
        return tree
    
    async def _calculate_traceability_coverage(self, requirement_id: int) -> Dict[str, Any]:
        """计算追溯覆盖率"""
        # 获取需求信息
        requirement = (await self.db.execute(
            select(Requirement).where(
                Requirement.id == requirement_id
            )
        )).scalars().first()
        
        if not requirement:
            return {}
        
        # 计算各类型的追溯覆盖率
        coverage = {
            "requirement_id": requirement_id,
            "to_design": 0.0,
            "to_task": 0.0,
            "to_test": 0.0,
            "from_business": 0.0,
            "overall": 0.0
        }
        
        # 计算设计追溯覆盖率
        design_links = (await self.db.execute(
            select(func.count()).select_from(RequirementTraceabilityLink).where(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == requirement_id,
                RequirementTraceabilityLink.target_type == "design"
            )
        )).scalar()
        coverage["to_design"] = 1.0 if design_links and design_links > 0 else 0.0
        
        # 计算任务追溯覆盖率
        task_links = (await self.db.execute(
            select(func.count()).select_from(RequirementTraceabilityLink).where(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == requirement_id,
                RequirementTraceabilityLink.target_type == "task"
            )
        )).scalar()
        coverage["to_task"] = 1.0 if task_links and task_links > 0 else 0.0
        
        # 计算测试追溯覆盖率
        test_links = (await self.db.execute(
            select(func.count()).select_from(RequirementTraceabilityLink).where(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == requirement_id,
                RequirementTraceabilityLink.target_type == "test_case"
            )
        )).scalar()
        coverage["to_test"] = 1.0 if test_links and test_links > 0 else 0.0
        
        # 计算业务需求追溯覆盖率
        business_links = (await self.db.execute(
            select(func.count()).select_from(RequirementTraceabilityLink).where(
                RequirementTraceabilityLink.target_type == "requirement",
                RequirementTraceabilityLink.target_id == requirement_id,
                RequirementTraceabilityLink.source_type == "business_requirement"
            )
        )).scalar()
        coverage["from_business"] = 1.0 if business_links and business_links > 0 else 0.0
        
        # 计算总体覆盖率
        coverage["overall"] = (
            coverage["to_design"] + coverage["to_task"] + 
            coverage["to_test"] + coverage["from_business"]
        ) / 4.0
        
        return coverage
    
    async def _analyze_direct_impacts(self, requirement_id: int) -> List[Dict[str, Any]]:
        """分析直接影响"""
        impacts = []
        
        # 获取直接下游链接
        direct_links = (await self.db.execute(
            select(RequirementTraceabilityLink).where(
                RequirementTraceabilityLink.source_type == "requirement",
                RequirementTraceabilityLink.source_id == requirement_id
            )
        )).scalars().all()
        
        for link in direct_links:
            impact = {
                "type": "direct",
                "target_type": link.target_type,
                "target_id": link.target_id,
                "link_type": link.link_type.value,
                "impact_level": "high"
            }
            impacts.append(impact)
        
        return impacts
    
    async def _analyze_indirect_impacts(self, downstream_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析间接影响"""
        impacts = []
        
        # 分析深度大于1的链接
        for link in downstream_links:
            if link.get("depth", 0) > 1:
                impact = {
                    "type": "indirect",
                    "target_type": link["target_type"],
                    "target_id": link["target_id"],
                    "link_type": link["link_type"],
                    "depth": link["depth"],
                    "impact_level": "medium" if link["depth"] == 2 else "low"
                }
                impacts.append(impact)
        
        return impacts
    
    async def _calculate_impact_scope(
        self,
        direct_impacts: List[Dict[str, Any]],
        indirect_impacts: List[Dict[str, Any]]
    ) -> Dict[str, List[int]]:
        """计算影响范围"""
        scope = {
            "requirements": [],
            "tasks": [],
            "test_cases": [],
            "designs": []
        }
        
        all_impacts = direct_impacts + indirect_impacts
        
        for impact in all_impacts:
            target_type = impact["target_type"]
            target_id = impact["target_id"]
            
            if target_type == "requirement":
                scope["requirements"].append(target_id)
            elif target_type == "task":
                scope["tasks"].append(target_id)
            elif target_type == "test_case":
                scope["test_cases"].append(target_id)
            elif target_type == "design":
                scope["designs"].append(target_id)
        
        # 去重
        for key in scope:
            scope[key] = list(set(scope[key]))
        
        return scope
    
    def _calculate_risk_level(self, impact_scope: Dict[str, List[int]]) -> str:
        """计算风险等级"""
        total_impacts = sum(len(items) for items in impact_scope.values())
        
        if total_impacts >= 20:
            return "high"
        elif total_impacts >= 10:
            return "medium"
        elif total_impacts >= 5:
            return "low"
        else:
            return "minimal"
    
    def _generate_impact_recommendations(self, impact_scope: Dict[str, List[int]]) -> List[str]:
        """生成影响建议"""
        recommendations = []
        
        if len(impact_scope["requirements"]) > 0:
            recommendations.append(f"需要评估 {len(impact_scope['requirements'])} 个相关需求的变更影响")
        
        if len(impact_scope["tasks"]) > 0:
            recommendations.append(f"需要更新 {len(impact_scope['tasks'])} 个相关任务的实现方案")
        
        if len(impact_scope["test_cases"]) > 0:
            recommendations.append(f"需要修改 {len(impact_scope['test_cases'])} 个相关测试用例")
        
        if len(impact_scope["designs"]) > 0:
            recommendations.append(f"需要调整 {len(impact_scope['designs'])} 个相关设计文档")
        
        return recommendations
    
    async def _get_test_cases_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """获取项目测试用例（模拟实现）"""
        # 这里应该调用测试管理模块的接口
        # 暂时返回空列表
        return []
    
    async def _get_tasks_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """获取项目任务（模拟实现）"""
        # 这里应该调用任务管理模块的接口
        # 暂时返回空列表
        return []
    
    async def _get_designs_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """获取项目设计文档（模拟实现）"""
        # 这里应该调用设计管理模块的接口
        # 暂时返回空列表
        return []
    
    async def _get_requirement_to_test_links(self, project_id: int) -> List[Dict[str, Any]]:
        """获取需求到测试用例的链接"""
        links = (await self.db.execute(
            select(RequirementTraceabilityLink).join(
                Requirement,
                and_(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == Requirement.id
                )
            ).where(
                Requirement.project_id == project_id,
                RequirementTraceabilityLink.target_type == "test_case"
            )
        )).scalars().all()
        
        return [link.to_dict() for link in links]
    
    async def _get_requirement_to_task_links(self, project_id: int) -> List[Dict[str, Any]]:
        """获取需求到任务的链接"""
        links = (await self.db.execute(
            select(RequirementTraceabilityLink).join(
                Requirement,
                and_(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == Requirement.id
                )
            ).where(
                Requirement.project_id == project_id,
                RequirementTraceabilityLink.target_type == "task"
            )
        )).scalars().all()
        
        return [link.to_dict() for link in links]
    
    async def _get_requirement_to_design_links(self, project_id: int) -> List[Dict[str, Any]]:
        """获取需求到设计的链接"""
        links = (await self.db.execute(
            select(RequirementTraceabilityLink).join(
                Requirement,
                and_(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == Requirement.id
                )
            ).where(
                Requirement.project_id == project_id,
                RequirementTraceabilityLink.target_type == "design"
            )
        )).scalars().all()
        
        return [link.to_dict() for link in links]
    
    async def _build_matrix_data(
        self,
        requirements: List[Dict[str, Any]],
        targets: List[Dict[str, Any]],
        links: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, bool]]:
        """构建矩阵数据"""
        matrix_data = {}
        
        # 创建链接映射
        link_map = {}
        for link in links:
            key = f"{link['source_id']}_{link['target_id']}"
            link_map[key] = True
        
        # 构建矩阵
        for req in requirements:
            req_id = str(req["id"])
            matrix_data[req_id] = {}
            
            for target in targets:
                target_id = str(target["id"])
                key = f"{req['id']}_{target['id']}"
                matrix_data[req_id][target_id] = key in link_map
        
        return matrix_data
    
    async def _calculate_matrix_coverage(self, matrix_data: Dict[str, Dict[str, bool]]) -> Dict[str, Any]:
        """计算矩阵覆盖率"""
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
            "coverage_rate": coverage_rate,
            "uncovered_cells": total_cells - covered_cells
        }
    
    async def _calculate_project_coverage_rate(self, project_id: int) -> float:
        """计算项目追溯覆盖率"""
        # 获取项目所有需求
        total_requirements = (await self.db.execute(
            select(func.count()).select_from(Requirement).where(
                Requirement.project_id == project_id
            )
        )).scalar()
        
        if not total_requirements or total_requirements == 0:
            return 0.0
        
        # 获取有追溯链接的需求数量
        covered_requirements = (await self.db.execute(
            select(func.count(func.distinct(Requirement.id))).join(
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
            ).where(
                Requirement.project_id == project_id
            )
        )).scalar()
        
        return (covered_requirements or 0) / total_requirements
    
    async def _identify_missing_links(self, project_id: int) -> List[Dict[str, Any]]:
        """识别缺失的追溯链接"""
        missing_links = []
        
        # 获取项目需求
        requirements = (await self.db.execute(
            select(Requirement).where(
                Requirement.project_id == project_id
            )
        )).scalars().all()
        
        for req in requirements:
            # 检查是否缺少测试追溯
            test_links = (await self.db.execute(
                select(func.count()).select_from(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == req.id,
                    RequirementTraceabilityLink.target_type == "test_case"
                )
            )).scalar()
            
            if not test_links or test_links == 0:
                missing_links.append({
                    "requirement_id": req.id,
                    "requirement_title": req.title,
                    "missing_type": "test_case",
                    "severity": "high"
                })
            
            # 检查是否缺少任务追溯
            task_links = (await self.db.execute(
                select(func.count()).select_from(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == req.id,
                    RequirementTraceabilityLink.target_type == "task"
                )
            )).scalar()
            
            if not task_links or task_links == 0:
                missing_links.append({
                    "requirement_id": req.id,
                    "requirement_title": req.title,
                    "missing_type": "task",
                    "severity": "medium"
                })
        
        return missing_links
    
    async def _identify_orphaned_items(self, project_id: int) -> List[Dict[str, Any]]:
        """识别孤立的需求和对象"""
        orphaned_items = []
        
        # 识别孤立的需求（没有任何追溯链接）
        orphaned_requirements = (await self.db.execute(
            select(Requirement).outerjoin(
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
            ).where(
                Requirement.project_id == project_id,
                RequirementTraceabilityLink.id.is_(None)
            )
        )).scalars().all()
        
        for req in orphaned_requirements:
            orphaned_items.append({
                "type": "requirement",
                "id": req.id,
                "title": req.title,
                "severity": "high"
            })
        
        return orphaned_items
    
    async def _detect_circular_references(self, project_id: int) -> List[List[int]]:
        """检测循环引用"""
        circular_refs = []
        
        # 获取项目内的所有需求追溯链接
        links = (await self.db.execute(
            select(RequirementTraceabilityLink).join(
                Requirement,
                and_(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == Requirement.id
                )
            ).where(
                Requirement.project_id == project_id,
                RequirementTraceabilityLink.target_type == "requirement"
            )
        )).scalars().all()
        
        # 构建图
        graph = defaultdict(list)
        for link in links:
            graph[link.source_id].append(link.target_id)
        
        # 使用DFS检测循环
        visited = set()
        rec_stack = set()
        
        def dfs(node: int, path: List[int]) -> bool:
            if node in rec_stack:
                # 找到循环，提取循环路径
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                circular_refs.append(cycle)
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph[node]:
                dfs(neighbor, path.copy())
            
            rec_stack.remove(node)
            return False
        
        # 检查所有节点
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return circular_refs
    
    async def _check_traceability_consistency(self, project_id: int) -> List[Dict[str, Any]]:
        """检查追溯一致性"""
        inconsistent_links = []
        
        # 检查双向链接的一致性
        links = (await self.db.execute(
            select(RequirementTraceabilityLink).join(
                Requirement,
                and_(
                    RequirementTraceabilityLink.source_type == "requirement",
                    RequirementTraceabilityLink.source_id == Requirement.id
                )
            ).where(
                Requirement.project_id == project_id
            )
        )).scalars().all()
        
        for link in links:
            # 检查是否存在对应的反向链接
            reverse_link = (await self.db.execute(
                select(RequirementTraceabilityLink).where(
                    RequirementTraceabilityLink.source_type == link.target_type,
                    RequirementTraceabilityLink.source_id == link.target_id,
                    RequirementTraceabilityLink.target_type == link.source_type,
                    RequirementTraceabilityLink.target_id == link.source_id
                )
            )).scalars().first()
            
            if not reverse_link and link.link_type in [
                TraceabilityLinkType.DERIVES_FROM,
                TraceabilityLinkType.REFINES
            ]:
                inconsistent_links.append({
                    "link_id": link.id,
                    "source_type": link.source_type,
                    "source_id": link.source_id,
                    "target_type": link.target_type,
                    "target_id": link.target_id,
                    "issue": "missing_reverse_link",
                    "severity": "medium"
                })
        
        return inconsistent_links
    
    async def _generate_quality_recommendations(self, result: TraceabilityAnalysisResult) -> List[str]:
        """生成质量改进建议"""
        recommendations = []
        
        if result.coverage_rate < 0.8:
            recommendations.append(f"追溯覆盖率较低({result.coverage_rate:.1%})，建议完善追溯链接")
        
        if len(result.missing_links) > 0:
            recommendations.append(f"发现 {len(result.missing_links)} 个缺失的追溯链接，建议补充")
        
        if len(result.orphaned_items) > 0:
            recommendations.append(f"发现 {len(result.orphaned_items)} 个孤立项目，建议建立追溯关系")
        
        if len(result.circular_references) > 0:
            recommendations.append(f"发现 {len(result.circular_references)} 个循环引用，建议修复")
        
        if len(result.inconsistent_links) > 0:
            recommendations.append(f"发现 {len(result.inconsistent_links)} 个不一致的链接，建议检查")
        
        return recommendations