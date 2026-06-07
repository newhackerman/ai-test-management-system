"""
需求关联关系仓储层

本模块提供需求关联关系的数据访问功能，包括：
- 需求依赖关系的CRUD操作
- 依赖关系查询和筛选
- 循环依赖检测
- 依赖链分析
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime

from ..models.requirement import RequirementDependency, DependencyType, Requirement


class RequirementRelationshipRepository:
    """需求关联关系仓储类"""
    
    def __init__(self, db: Session):
        """
        初始化仓储
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def create_dependency(
        self,
        source_requirement_id: int,
        target_requirement_id: int,
        dependency_type: DependencyType,
        description: Optional[str],
        created_by: int
    ) -> RequirementDependency:
        """
        创建需求依赖关系
        
        Args:
            source_requirement_id: 源需求ID
            target_requirement_id: 目标需求ID
            dependency_type: 依赖类型
            description: 依赖描述
            created_by: 创建人ID
            
        Returns:
            创建的依赖关系对象
        """
        dependency = RequirementDependency(
            source_requirement_id=source_requirement_id,
            target_requirement_id=target_requirement_id,
            dependency_type=dependency_type,
            description=description,
            created_by=created_by
        )
        self.db.add(dependency)
        self.db.commit()
        self.db.refresh(dependency)
        return dependency
    
    def get_dependency_by_id(self, dependency_id: int) -> Optional[RequirementDependency]:
        """
        根据ID获取依赖关系
        
        Args:
            dependency_id: 依赖关系ID
            
        Returns:
            依赖关系对象，如果不存在则返回None
        """
        return self.db.query(RequirementDependency).filter(
            RequirementDependency.id == dependency_id
        ).first()
    
    def get_dependencies_by_source(
        self,
        source_requirement_id: int,
        dependency_type: Optional[DependencyType] = None
    ) -> List[RequirementDependency]:
        """
        获取源需求的所有依赖关系
        
        Args:
            source_requirement_id: 源需求ID
            dependency_type: 依赖类型（可选）
            
        Returns:
            依赖关系列表
        """
        query = self.db.query(RequirementDependency).filter(
            RequirementDependency.source_requirement_id == source_requirement_id
        )
        
        if dependency_type:
            query = query.filter(RequirementDependency.dependency_type == dependency_type)
        
        return query.all()
    
    def get_dependencies_by_target(
        self,
        target_requirement_id: int,
        dependency_type: Optional[DependencyType] = None
    ) -> List[RequirementDependency]:
        """
        获取目标需求的所有依赖关系
        
        Args:
            target_requirement_id: 目标需求ID
            dependency_type: 依赖类型（可选）
            
        Returns:
            依赖关系列表
        """
        query = self.db.query(RequirementDependency).filter(
            RequirementDependency.target_requirement_id == target_requirement_id
        )
        
        if dependency_type:
            query = query.filter(RequirementDependency.dependency_type == dependency_type)
        
        return query.all()
    
    def get_all_dependencies_for_requirement(
        self,
        requirement_id: int
    ) -> Tuple[List[RequirementDependency], List[RequirementDependency]]:
        """
        获取需求的所有依赖关系（作为源和目标）
        
        Args:
            requirement_id: 需求ID
            
        Returns:
            (源依赖列表, 目标依赖列表)
        """
        source_deps = self.get_dependencies_by_source(requirement_id)
        target_deps = self.get_dependencies_by_target(requirement_id)
        return source_deps, target_deps
    
    def check_dependency_exists(
        self,
        source_requirement_id: int,
        target_requirement_id: int,
        dependency_type: DependencyType
    ) -> bool:
        """
        检查依赖关系是否已存在
        
        Args:
            source_requirement_id: 源需求ID
            target_requirement_id: 目标需求ID
            dependency_type: 依赖类型
            
        Returns:
            如果存在返回True，否则返回False
        """
        exists = self.db.query(RequirementDependency).filter(
            and_(
                RequirementDependency.source_requirement_id == source_requirement_id,
                RequirementDependency.target_requirement_id == target_requirement_id,
                RequirementDependency.dependency_type == dependency_type
            )
        ).first()
        return exists is not None
    
    def delete_dependency(self, dependency_id: int) -> bool:
        """
        删除依赖关系
        
        Args:
            dependency_id: 依赖关系ID
            
        Returns:
            删除成功返回True，否则返回False
        """
        dependency = self.get_dependency_by_id(dependency_id)
        if dependency:
            self.db.delete(dependency)
            self.db.commit()
            return True
        return False
    
    def update_dependency(
        self,
        dependency_id: int,
        dependency_type: Optional[DependencyType] = None,
        description: Optional[str] = None
    ) -> Optional[RequirementDependency]:
        """
        更新依赖关系
        
        Args:
            dependency_id: 依赖关系ID
            dependency_type: 新的依赖类型（可选）
            description: 新的描述（可选）
            
        Returns:
            更新后的依赖关系对象，如果不存在则返回None
        """
        dependency = self.get_dependency_by_id(dependency_id)
        if not dependency:
            return None
        
        if dependency_type is not None:
            dependency.dependency_type = dependency_type
        if description is not None:
            dependency.description = description
        
        dependency.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(dependency)
        return dependency
    
    def get_dependency_chain(
        self,
        requirement_id: int,
        direction: str = "downstream",
        max_depth: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取需求的依赖链
        
        Args:
            requirement_id: 需求ID
            direction: 方向 ("downstream" 下游, "upstream" 上游)
            max_depth: 最大深度
            
        Returns:
            依赖链列表，每个元素包含需求信息和深度
        """
        visited = set()
        chain = []
        
        def traverse(req_id: int, depth: int):
            if depth > max_depth or req_id in visited:
                return
            
            visited.add(req_id)
            
            if direction == "downstream":
                dependencies = self.get_dependencies_by_source(req_id)
                for dep in dependencies:
                    chain.append({
                        'requirement_id': dep.target_requirement_id,
                        'dependency_type': dep.dependency_type.value,
                        'depth': depth,
                        'description': dep.description
                    })
                    traverse(dep.target_requirement_id, depth + 1)
            else:  # upstream
                dependencies = self.get_dependencies_by_target(req_id)
                for dep in dependencies:
                    chain.append({
                        'requirement_id': dep.source_requirement_id,
                        'dependency_type': dep.dependency_type.value,
                        'depth': depth,
                        'description': dep.description
                    })
                    traverse(dep.source_requirement_id, depth + 1)
        
        traverse(requirement_id, 1)
        return chain
    
    def detect_circular_dependency(
        self,
        source_requirement_id: int,
        target_requirement_id: int
    ) -> bool:
        """
        检测是否会形成循环依赖
        
        Args:
            source_requirement_id: 源需求ID
            target_requirement_id: 目标需求ID
            
        Returns:
            如果会形成循环依赖返回True，否则返回False
        """
        # 检查目标需求是否能到达源需求
        visited = set()
        
        def can_reach(current_id: int, target_id: int) -> bool:
            if current_id == target_id:
                return True
            
            if current_id in visited:
                return False
            
            visited.add(current_id)
            
            # 获取当前需求的所有下游依赖
            dependencies = self.get_dependencies_by_source(current_id)
            for dep in dependencies:
                if can_reach(dep.target_requirement_id, target_id):
                    return True
            
            return False
        
        # 如果从target能到达source，则会形成循环
        return can_reach(target_requirement_id, source_requirement_id)
    
    def get_requirements_by_project(self, project_id: int) -> List[Requirement]:
        """
        获取项目的所有需求
        
        Args:
            project_id: 项目ID
            
        Returns:
            需求列表
        """
        return self.db.query(Requirement).filter(
            Requirement.project_id == project_id
        ).all()
    
    def get_dependency_statistics(self, project_id: int) -> Dict[str, Any]:
        """
        获取项目的依赖关系统计
        
        Args:
            project_id: 项目ID
            
        Returns:
            统计信息字典
        """
        # 获取项目的所有需求ID
        requirement_ids = [req.id for req in self.get_requirements_by_project(project_id)]
        
        if not requirement_ids:
            return {
                'total_dependencies': 0,
                'by_type': {},
                'requirements_with_dependencies': 0,
                'requirements_without_dependencies': 0
            }
        
        # 统计依赖关系总数
        total_deps = self.db.query(func.count(RequirementDependency.id)).filter(
            RequirementDependency.source_requirement_id.in_(requirement_ids)
        ).scalar()
        
        # 按类型统计
        type_stats = self.db.query(
            RequirementDependency.dependency_type,
            func.count(RequirementDependency.id)
        ).filter(
            RequirementDependency.source_requirement_id.in_(requirement_ids)
        ).group_by(RequirementDependency.dependency_type).all()
        
        by_type = {dep_type.value: count for dep_type, count in type_stats}
        
        # 统计有依赖关系的需求数量
        reqs_with_deps = self.db.query(
            func.count(func.distinct(RequirementDependency.source_requirement_id))
        ).filter(
            RequirementDependency.source_requirement_id.in_(requirement_ids)
        ).scalar()
        
        return {
            'total_dependencies': total_deps,
            'by_type': by_type,
            'requirements_with_dependencies': reqs_with_deps,
            'requirements_without_dependencies': len(requirement_ids) - reqs_with_deps
        }
