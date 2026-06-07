"""
需求关联关系Schema定义

本模块定义需求关联关系相关的数据传输对象(DTO)，包括：
- 创建依赖关系请求
- 更新依赖关系请求
- 依赖关系响应
- 依赖链分析响应
- 循环依赖检测响应
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DependencyTypeEnum(str, Enum):
    """依赖类型枚举"""
    DEPENDS_ON = "DEPENDS_ON"
    BLOCKS = "BLOCKS"
    RELATES_TO = "RELATES_TO"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    DUPLICATES = "DUPLICATES"
    REPLACES = "REPLACES"


class CreateDependencyRequest(BaseModel):
    """创建依赖关系请求"""
    source_requirement_id: int = Field(..., description="源需求ID", gt=0)
    target_requirement_id: int = Field(..., description="目标需求ID", gt=0)
    dependency_type: DependencyTypeEnum = Field(..., description="依赖类型")
    description: Optional[str] = Field(None, description="依赖描述", max_length=1000)
    
    @validator('target_requirement_id')
    def validate_different_requirements(cls, v, values):
        """验证源需求和目标需求不能相同"""
        if 'source_requirement_id' in values and v == values['source_requirement_id']:
            raise ValueError("源需求和目标需求不能相同")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "source_requirement_id": 1,
                "target_requirement_id": 2,
                "dependency_type": "DEPENDS_ON",
                "description": "需求1依赖需求2的实现"
            }
        }


class UpdateDependencyRequest(BaseModel):
    """更新依赖关系请求"""
    dependency_type: Optional[DependencyTypeEnum] = Field(None, description="依赖类型")
    description: Optional[str] = Field(None, description="依赖描述", max_length=1000)
    
    class Config:
        schema_extra = {
            "example": {
                "dependency_type": "BLOCKS",
                "description": "更新后的依赖描述"
            }
        }


class DependencyResponse(BaseModel):
    """依赖关系响应"""
    id: int = Field(..., description="依赖关系ID")
    source_requirement_id: int = Field(..., description="源需求ID")
    target_requirement_id: int = Field(..., description="目标需求ID")
    dependency_type: str = Field(..., description="依赖类型")
    description: Optional[str] = Field(None, description="依赖描述")
    created_by: int = Field(..., description="创建人ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 关联的需求信息（可选）
    source_requirement_title: Optional[str] = Field(None, description="源需求标题")
    target_requirement_title: Optional[str] = Field(None, description="目标需求标题")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "source_requirement_id": 1,
                "target_requirement_id": 2,
                "dependency_type": "DEPENDS_ON",
                "description": "需求1依赖需求2的实现",
                "created_by": 1,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "source_requirement_title": "用户登录功能",
                "target_requirement_title": "用户认证服务"
            }
        }


class DependencyChainNode(BaseModel):
    """依赖链节点"""
    requirement_id: int = Field(..., description="需求ID")
    requirement_title: Optional[str] = Field(None, description="需求标题")
    dependency_type: str = Field(..., description="依赖类型")
    depth: int = Field(..., description="深度")
    description: Optional[str] = Field(None, description="依赖描述")
    
    class Config:
        schema_extra = {
            "example": {
                "requirement_id": 2,
                "requirement_title": "用户认证服务",
                "dependency_type": "DEPENDS_ON",
                "depth": 1,
                "description": "需求1依赖需求2的实现"
            }
        }


class DependencyChainResponse(BaseModel):
    """依赖链响应"""
    requirement_id: int = Field(..., description="起始需求ID")
    direction: str = Field(..., description="方向 (upstream/downstream)")
    chain: List[DependencyChainNode] = Field(..., description="依赖链")
    total_count: int = Field(..., description="依赖总数")
    max_depth: int = Field(..., description="最大深度")
    
    class Config:
        schema_extra = {
            "example": {
                "requirement_id": 1,
                "direction": "downstream",
                "chain": [
                    {
                        "requirement_id": 2,
                        "requirement_title": "用户认证服务",
                        "dependency_type": "DEPENDS_ON",
                        "depth": 1,
                        "description": "需求1依赖需求2的实现"
                    }
                ],
                "total_count": 1,
                "max_depth": 1
            }
        }


class CircularDependencyCheckRequest(BaseModel):
    """循环依赖检测请求"""
    source_requirement_id: int = Field(..., description="源需求ID", gt=0)
    target_requirement_id: int = Field(..., description="目标需求ID", gt=0)
    
    @validator('target_requirement_id')
    def validate_different_requirements(cls, v, values):
        """验证源需求和目标需求不能相同"""
        if 'source_requirement_id' in values and v == values['source_requirement_id']:
            raise ValueError("源需求和目标需求不能相同")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "source_requirement_id": 1,
                "target_requirement_id": 2
            }
        }


class CircularDependencyCheckResponse(BaseModel):
    """循环依赖检测响应"""
    has_circular_dependency: bool = Field(..., description="是否存在循环依赖")
    source_requirement_id: int = Field(..., description="源需求ID")
    target_requirement_id: int = Field(..., description="目标需求ID")
    message: str = Field(..., description="检测结果消息")
    circular_path: Optional[List[int]] = Field(None, description="循环路径（如果存在）")
    
    class Config:
        schema_extra = {
            "example": {
                "has_circular_dependency": False,
                "source_requirement_id": 1,
                "target_requirement_id": 2,
                "message": "未检测到循环依赖",
                "circular_path": None
            }
        }


class DependencyStatisticsResponse(BaseModel):
    """依赖关系统计响应"""
    project_id: int = Field(..., description="项目ID")
    total_dependencies: int = Field(..., description="依赖关系总数")
    by_type: Dict[str, int] = Field(..., description="按类型统计")
    requirements_with_dependencies: int = Field(..., description="有依赖关系的需求数")
    requirements_without_dependencies: int = Field(..., description="无依赖关系的需求数")
    
    class Config:
        schema_extra = {
            "example": {
                "project_id": 1,
                "total_dependencies": 10,
                "by_type": {
                    "DEPENDS_ON": 5,
                    "BLOCKS": 2,
                    "RELATES_TO": 3
                },
                "requirements_with_dependencies": 8,
                "requirements_without_dependencies": 2
            }
        }


class DependencyGraphNode(BaseModel):
    """依赖关系图节点"""
    id: int = Field(..., description="需求ID")
    title: str = Field(..., description="需求标题")
    status: str = Field(..., description="需求状态")
    priority: str = Field(..., description="优先级")
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "title": "用户登录功能",
                "status": "IN_DEVELOPMENT",
                "priority": "HIGH"
            }
        }


class DependencyGraphEdge(BaseModel):
    """依赖关系图边"""
    source: int = Field(..., description="源需求ID")
    target: int = Field(..., description="目标需求ID")
    type: str = Field(..., description="依赖类型")
    description: Optional[str] = Field(None, description="依赖描述")
    
    class Config:
        schema_extra = {
            "example": {
                "source": 1,
                "target": 2,
                "type": "DEPENDS_ON",
                "description": "需求1依赖需求2的实现"
            }
        }


class DependencyGraphResponse(BaseModel):
    """依赖关系图响应"""
    project_id: int = Field(..., description="项目ID")
    nodes: List[DependencyGraphNode] = Field(..., description="节点列表")
    edges: List[DependencyGraphEdge] = Field(..., description="边列表")
    
    class Config:
        schema_extra = {
            "example": {
                "project_id": 1,
                "nodes": [
                    {
                        "id": 1,
                        "title": "用户登录功能",
                        "status": "IN_DEVELOPMENT",
                        "priority": "HIGH"
                    },
                    {
                        "id": 2,
                        "title": "用户认证服务",
                        "status": "COMPLETED",
                        "priority": "HIGH"
                    }
                ],
                "edges": [
                    {
                        "source": 1,
                        "target": 2,
                        "type": "DEPENDS_ON",
                        "description": "需求1依赖需求2的实现"
                    }
                ]
            }
        }


class ImpactAnalysisRequest(BaseModel):
    """影响范围分析请求"""
    requirement_id: int = Field(..., description="需求ID", gt=0)
    change_description: Optional[str] = Field(None, description="变更描述", max_length=1000)
    
    class Config:
        schema_extra = {
            "example": {
                "requirement_id": 1,
                "change_description": "修改用户认证逻辑"
            }
        }


class ImpactedRequirement(BaseModel):
    """受影响的需求"""
    requirement_id: int = Field(..., description="需求ID")
    requirement_title: str = Field(..., description="需求标题")
    impact_type: str = Field(..., description="影响类型")
    impact_level: str = Field(..., description="影响程度 (HIGH/MEDIUM/LOW)")
    description: str = Field(..., description="影响描述")
    
    class Config:
        schema_extra = {
            "example": {
                "requirement_id": 3,
                "requirement_title": "用户权限管理",
                "impact_type": "DEPENDS_ON",
                "impact_level": "HIGH",
                "description": "该需求依赖被修改的需求，需要重新评估"
            }
        }


class ImpactAnalysisResponse(BaseModel):
    """影响范围分析响应"""
    requirement_id: int = Field(..., description="需求ID")
    change_description: Optional[str] = Field(None, description="变更描述")
    direct_impacts: List[ImpactedRequirement] = Field(..., description="直接影响的需求")
    indirect_impacts: List[ImpactedRequirement] = Field(..., description="间接影响的需求")
    total_impacted: int = Field(..., description="受影响需求总数")
    risk_level: str = Field(..., description="风险等级 (HIGH/MEDIUM/LOW)")
    recommendations: List[str] = Field(..., description="建议")
    
    class Config:
        schema_extra = {
            "example": {
                "requirement_id": 1,
                "change_description": "修改用户认证逻辑",
                "direct_impacts": [
                    {
                        "requirement_id": 3,
                        "requirement_title": "用户权限管理",
                        "impact_type": "DEPENDS_ON",
                        "impact_level": "HIGH",
                        "description": "该需求依赖被修改的需求，需要重新评估"
                    }
                ],
                "indirect_impacts": [],
                "total_impacted": 1,
                "risk_level": "MEDIUM",
                "recommendations": [
                    "建议通知相关需求负责人",
                    "建议重新评估受影响需求的工作量"
                ]
            }
        }
