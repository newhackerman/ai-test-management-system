"""
需求追溯分析API接口

本模块提供需求追溯分析的REST API接口，包括：
- 追溯链接管理
- 追溯矩阵生成
- 影响分析
- 追溯覆盖率分析
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, BusinessLogicError, NotFoundError
from ...services.requirement_traceability_service import RequirementTraceabilityService
from ...services.auth import get_current_user
from ...schemas.base import BaseResponse
from ...models.user import User
from ...models.project import Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requirement-traceability", tags=["需求追溯分析"])


# Pydantic models for traceability
from pydantic import BaseModel, Field
from enum import Enum


class TraceabilityLinkTypeEnum(str, Enum):
    """追溯链接类型枚举"""
    DERIVES_FROM = "DERIVES_FROM"
    IMPLEMENTS = "IMPLEMENTS"
    TESTS = "TESTS"
    VALIDATES = "VALIDATES"
    REFINES = "REFINES"


class CreateTraceabilityLinkRequest(BaseModel):
    """创建追溯链接请求"""
    source_type: str = Field(..., description="源对象类型")
    source_id: int = Field(..., description="源对象ID")
    target_type: str = Field(..., description="目标对象类型")
    target_id: int = Field(..., description="目标对象ID")
    link_type: TraceabilityLinkTypeEnum = Field(..., description="链接类型")
    description: Optional[str] = Field(None, description="链接描述")


class TraceabilityLinkResponse(BaseModel):
    """追溯链接响应"""
    id: int
    source_type: str
    source_id: int
    target_type: str
    target_id: int
    link_type: TraceabilityLinkTypeEnum
    description: Optional[str]
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class TraceabilityMatrixRequest(BaseModel):
    """追溯矩阵请求"""
    project_id: int = Field(..., description="项目ID")
    matrix_type: str = Field("requirement_to_test", description="矩阵类型")
    include_indirect: bool = Field(False, description="是否包含间接追溯")


class TraceabilityMatrixResponse(BaseModel):
    """追溯矩阵响应"""
    project_id: int
    matrix_type: str
    requirements: List[Dict[str, Any]]
    targets: List[Dict[str, Any]]
    matrix_data: Dict[str, Any]
    coverage_stats: Dict[str, Any]
    generated_at: datetime


class RequirementTraceabilityResponse(BaseModel):
    """需求追溯响应"""
    requirement_id: int
    upstream_links: List[TraceabilityLinkResponse]
    downstream_links: List[TraceabilityLinkResponse]
    coverage_analysis: Dict[str, Any]
    generated_at: datetime


class ChangeImpactAnalysisRequest(BaseModel):
    """变更影响分析请求"""
    requirement_id: int = Field(..., description="需求ID")
    change_description: str = Field(..., description="变更描述")
    analysis_depth: int = Field(3, ge=1, le=5, description="分析深度")


class ImpactItem(BaseModel):
    """影响项"""
    object_type: str
    object_id: int
    object_title: str
    impact_type: str
    impact_level: str
    impact_description: str


class ChangeImpactAnalysisResponse(BaseModel):
    """变更影响分析响应"""
    requirement_id: int
    change_description: str
    direct_impacts: List[ImpactItem]
    indirect_impacts: List[ImpactItem]
    affected_requirements: List[int]
    affected_test_cases: List[int]
    affected_tasks: List[int]
    risk_level: str
    recommendations: List[str]
    analyzed_at: datetime


async def get_traceability_service(db: AsyncSession = Depends(get_async_session)) -> RequirementTraceabilityService:
    """获取追溯服务"""
    return RequirementTraceabilityService(db)


@router.post("/links", response_model=TraceabilityLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_traceability_link(
    request: CreateTraceabilityLinkRequest,
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service)
):
    """
    创建追溯链接
    
    在两个对象之间建立追溯关系。
    
    - **source_type**: 源对象类型 (requirement, task, test_case等)
    - **source_id**: 源对象ID
    - **target_type**: 目标对象类型
    - **target_id**: 目标对象ID
    - **link_type**: 链接类型
    """
    try:
        link = await service.create_traceability_link(
            link_data=request.dict(),
            creator_id=current_user.id
        )
        return TraceabilityLinkResponse.from_orm(link)
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建追溯链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建追溯链接失败")


@router.get("/links/{link_id}", response_model=TraceabilityLinkResponse)
async def get_traceability_link(
    link_id: int = Path(..., description="追溯链接ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service)
):
    """获取追溯链接详情"""
    try:
        link = await service.get_traceability_link_by_id(link_id)
        if not link:
            raise HTTPException(status_code=404, detail="追溯链接不存在")
        
        return TraceabilityLinkResponse.from_orm(link)
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取追溯链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取追溯链接失败")


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_traceability_link(
    link_id: int = Path(..., description="追溯链接ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service)
):
    """删除追溯链接"""
    try:
        await service.delete_traceability_link(link_id, current_user.id)

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        # 服务层对不存在的链接抛出 ValueError，这里转为 404
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除追溯链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除追溯链接失败")


@router.get("/requirements/{requirement_id}", response_model=RequirementTraceabilityResponse)
async def get_requirement_traceability(
    requirement_id: int = Path(..., description="需求ID"),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$", description="追溯方向"),
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service)
):
    """
    获取需求追溯关系
    
    获取指定需求的完整追溯关系。
    
    - **direction**: 追溯方向 (upstream: 上游, downstream: 下游, both: 双向)
    """
    try:
        traceability = await service.get_requirement_traceability(requirement_id, direction)
        if traceability is None:
            raise HTTPException(status_code=404, detail="需求追溯关系不存在")
        
        return RequirementTraceabilityResponse(
            requirement_id=requirement_id,
            upstream_links=[TraceabilityLinkResponse.from_orm(link) for link in traceability["upstream_links"]],
            downstream_links=[TraceabilityLinkResponse.from_orm(link) for link in traceability["downstream_links"]],
            coverage_analysis=traceability["coverage_analysis"],
            generated_at=traceability["generated_at"]
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取需求追溯关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取需求追溯关系失败")


@router.post("/matrix", response_model=TraceabilityMatrixResponse)
async def generate_traceability_matrix(
    request: TraceabilityMatrixRequest,
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service)
):
    """
    生成追溯矩阵
    
    生成指定项目的追溯矩阵。
    
    - **project_id**: 项目ID
    - **matrix_type**: 矩阵类型 (requirement_to_test, requirement_to_task等)
    - **include_indirect**: 是否包含间接追溯
    """
    try:
        matrix = await service.generate_traceability_matrix(
            project_id=request.project_id,
            matrix_type=request.matrix_type,
            include_indirect=request.include_indirect
        )
        
        return TraceabilityMatrixResponse(
            project_id=matrix.project_id,
            matrix_type=matrix.matrix_type,
            requirements=matrix.requirements,
            targets=matrix.targets,
            matrix_data=matrix.matrix_data,
            coverage_stats=matrix.coverage_stats,
            generated_at=matrix.generated_at
        )
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成追溯矩阵失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成追溯矩阵失败")


@router.post("/impact-analysis", response_model=ChangeImpactAnalysisResponse)
async def analyze_change_impact(
    request: ChangeImpactAnalysisRequest,
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service)
):
    """
    分析变更影响
    
    分析需求变更对其他对象的影响。
    
    - **requirement_id**: 需求ID
    - **change_description**: 变更描述
    - **analysis_depth**: 分析深度 (1-5)
    """
    try:
        analysis = await service.analyze_change_impact(
            requirement_id=request.requirement_id,
            change_description=request.change_description,
            analysis_depth=request.analysis_depth
        )
        
        return ChangeImpactAnalysisResponse(
            requirement_id=analysis["requirement_id"],
            change_description=analysis["change_description"],
            direct_impacts=[
                ImpactItem(
                    object_type=impact["object_type"],
                    object_id=impact["object_id"],
                    object_title=impact["object_title"],
                    impact_type=impact["impact_type"],
                    impact_level=impact["impact_level"],
                    impact_description=impact["impact_description"]
                ) for impact in analysis["direct_impacts"]
            ],
            indirect_impacts=[
                ImpactItem(
                    object_type=impact["object_type"],
                    object_id=impact["object_id"],
                    object_title=impact["object_title"],
                    impact_type=impact["impact_type"],
                    impact_level=impact["impact_level"],
                    impact_description=impact["impact_description"]
                ) for impact in analysis["indirect_impacts"]
            ],
            affected_requirements=analysis["affected_requirements"],
            affected_test_cases=analysis["affected_test_cases"],
            affected_tasks=analysis["affected_tasks"],
            risk_level=analysis["risk_level"],
            recommendations=analysis["recommendations"],
            analyzed_at=analysis["analyzed_at"]
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"变更影响分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="变更影响分析失败")


@router.get("/coverage/{project_id}")
async def get_traceability_coverage(
    project_id: int = Path(..., description="项目ID"),
    coverage_type: str = Query("all", description="覆盖率类型"),
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取追溯覆盖率
    
    获取项目的追溯覆盖率统计。
    """
    try:
        # 校验项目是否存在
        proj = (await db.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))).scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=404, detail="项目不存在")
        coverage = await service.get_traceability_coverage(project_id, coverage_type)
        if coverage is None:
            raise HTTPException(status_code=404, detail="追溯覆盖率不存在")
        
        return {
            "project_id": project_id,
            "coverage_type": coverage_type,
            "coverage_stats": coverage,
            "generated_at": datetime.utcnow()
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取追溯覆盖率失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取追溯覆盖率失败")


@router.get("/orphaned-requirements/{project_id}")
async def get_orphaned_requirements(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取孤立需求
    
    获取没有下游实现的孤立需求。
    """
    try:
        # 校验项目是否存在
        proj = (await db.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))).scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=404, detail="项目不存在")
        orphaned = await service.get_orphaned_requirements(project_id)
        if orphaned is None:
            orphaned = []
        
        return {
            "project_id": project_id,
            "orphaned_requirements": orphaned,
            "count": len(orphaned),
            "generated_at": datetime.utcnow()
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取孤立需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取孤立需求失败")


@router.get("/consistency-check/{project_id}")
async def check_traceability_consistency(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service),
    db: AsyncSession = Depends(get_async_session)
):
    """
    检查追溯一致性
    
    检查项目追溯关系的一致性。
    """
    try:
        # 校验项目是否存在
        proj = (await db.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))).scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=404, detail="项目不存在")
        consistency = await service.check_traceability_consistency(project_id)
        if consistency is None:
            consistency = []
        
        return {
            "project_id": project_id,
            "consistency_report": consistency,
            "generated_at": datetime.utcnow()
        }
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查追溯一致性失败: {str(e)}")
        raise HTTPException(status_code=500, detail="检查追溯一致性失败")


@router.get("/links")
async def search_traceability_links(
    source_type: Optional[str] = Query(None, description="源对象类型"),
    source_id: Optional[int] = Query(None, description="源对象ID"),
    target_type: Optional[str] = Query(None, description="目标对象类型"),
    target_id: Optional[int] = Query(None, description="目标对象ID"),
    link_type: Optional[TraceabilityLinkTypeEnum] = Query(None, description="链接类型"),
    project_id: Optional[int] = Query(None, description="项目ID"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(50, ge=1, le=100, description="限制数量"),
    current_user: User = Depends(get_current_user),
    service: RequirementTraceabilityService = Depends(get_traceability_service)
):
    """
    搜索追溯链接
    
    根据条件搜索追溯链接。
    """
    try:
        search_params = {
            "source_type": source_type,
            "source_id": source_id,
            "target_type": target_type,
            "target_id": target_id,
            "link_type": link_type.value if link_type else None,
            "project_id": project_id,
            "skip": skip,
            "limit": limit
        }
        
        # 过滤掉None值
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        links, total = await service.search_traceability_links(search_params)
        
        return {
            "links": [TraceabilityLinkResponse.from_orm(link) for link in links],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索追溯链接失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索追溯链接失败")