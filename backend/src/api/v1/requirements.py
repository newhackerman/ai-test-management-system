"""
需求管理API接口

本模块提供需求管理的REST API接口，包括：
- 需求CRUD操作
- 需求查询和筛选
- 需求状态管理
- 需求批量操作
- 需求统计分析
"""
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, BusinessLogicError, NotFoundError, PermissionError
from ...services.requirement_service import RequirementService
from ...services.ai_router_service import AIRouterService
from ...services.audit_service import AuditService
from ...services.auth import get_current_user
from ...schemas.requirement import (
    RequirementCreate, RequirementUpdate, RequirementStatusUpdate,
    RequirementBatchStatusUpdate, RequirementBatchDeleteRequest,
    RequirementResponse, RequirementListResponse, RequirementWithHistoryResponse,
    RequirementStatisticsResponse, RequirementQualityAnalysisResponse,
    RequirementSearchParams, RequirementBatchOperationResponse,
    RequirementImportRequest, RequirementExportRequest, RequirementImportResponse,
    RequirementDependencyCreate, RequirementDependencyResponse, RequirementWithDependenciesResponse,
    RequirementTemplateCreate, RequirementTemplateResponse,
    RequirementTypeEnum, RequirementStatusEnum, PriorityEnum, BusinessValueEnum, ComplexityEnum
)
from ...models.user import User
from ...models.requirement import RequirementStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requirements", tags=["需求管理"])


async def get_requirement_service(db: AsyncSession = Depends(get_async_session)) -> RequirementService:
    """获取需求管理服务"""
    ai_router_service = AIRouterService(db)
    audit_service = AuditService(db)
    return RequirementService(db, ai_router_service, audit_service)


@router.post("/", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    request: RequirementCreate,
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    创建需求
    
    创建一个新的需求，支持AI质量分析和自动编码生成。
    
    - **project_id**: 所属项目ID
    - **title**: 需求标题
    - **description**: 需求描述
    - **requirement_type**: 需求类型
    - **priority**: 优先级
    - **business_value**: 业务价值
    """
    try:
        requirement = await service.create_requirement(
            requirement_data=request.dict(),
            creator_id=current_user.id
        )
        return RequirementResponse.from_orm(requirement)
    
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"创建需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建需求失败")


@router.get("/statistics", response_model=RequirementStatisticsResponse)
async def get_requirements_statistics(
    project_id: Optional[int] = Query(None, description="项目ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    获取需求统计信息

    获取需求的统计数据和分析。
    """
    try:
        statistics = await service.get_requirements_statistics(project_id)

        return RequirementStatisticsResponse(
            total_requirements=statistics.get('total_count', 0),
            status_distribution=statistics.get('status_distribution', {}),
            priority_distribution=statistics.get('priority_distribution', {}),
            type_distribution=statistics.get('type_distribution', {}),
            complexity_distribution=statistics.get('complexity_distribution', {}),
            business_value_distribution=statistics.get('business_value_distribution', {}),
            average_quality_score=statistics.get('average_quality_score'),
            average_completeness_score=statistics.get('average_completeness_score'),
            generated_at=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"获取需求统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取需求统计失败")


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    获取需求详情
    
    根据需求ID获取需求的详细信息。
    """
    try:
        requirement = await service.get_requirement_by_id(requirement_id)
        if not requirement:
            raise HTTPException(status_code=404, detail="需求不存在")
        
        return RequirementResponse.from_orm(requirement)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取需求详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取需求详情失败")


@router.put("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: int = Path(..., description="需求ID"),
    request: RequirementUpdate = ...,
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    更新需求
    
    更新需求的基本信息，支持部分字段更新。
    """
    try:
        # 过滤掉None值
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        requirement = await service.update_requirement(
            requirement_id=requirement_id,
            update_data=update_data,
            updated_by=current_user.id
        )
        return RequirementResponse.from_orm(requirement)
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"更新需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新需求失败")


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    删除需求
    
    删除指定的需求。只能删除草稿状态的需求。
    """
    try:
        await service.delete_requirement(
            requirement_id=requirement_id,
            deleted_by=current_user.id
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"删除需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除需求失败")


@router.put("/{requirement_id}/status", response_model=RequirementResponse)
async def update_requirement_status(
    requirement_id: int = Path(..., description="需求ID"),
    request: RequirementStatusUpdate = ...,
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    更新需求状态
    
    更新需求的状态，支持状态流转验证和前置条件检查。
    
    - **status**: 新状态
    - **reason**: 变更原因（可选）
    """
    try:
        requirement = await service.update_requirement_status(
            requirement_id=requirement_id,
            new_status=RequirementStatus(request.status.value),
            changed_by=current_user.id,
            reason=request.reason
        )
        return RequirementResponse.from_orm(requirement)
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"更新需求状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新需求状态失败")


@router.get("/", response_model=RequirementListResponse)
async def search_requirements(
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    project_id: Optional[int] = Query(None, description="项目ID"),
    parent_id: Optional[int] = Query(None, description="父需求ID"),
    requirement_type: Optional[RequirementTypeEnum] = Query(None, description="需求类型"),
    status_filter: Optional[List[RequirementStatusEnum]] = Query(None, alias="status", description="状态过滤"),
    priority: Optional[List[PriorityEnum]] = Query(None, description="优先级过滤"),
    business_value: Optional[List[BusinessValueEnum]] = Query(None, description="业务价值过滤"),
    complexity: Optional[List[ComplexityEnum]] = Query(None, description="复杂度过滤"),
    assignee_id: Optional[int] = Query(None, description="负责人ID"),
    creator_id: Optional[int] = Query(None, description="创建人ID"),
    reviewer_id: Optional[int] = Query(None, description="评审人ID"),
    category: Optional[str] = Query(None, description="分类"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    created_from: Optional[date] = Query(None, description="创建开始日期"),
    created_to: Optional[date] = Query(None, description="创建结束日期"),
    planned_start_from: Optional[date] = Query(None, description="计划开始日期范围开始"),
    planned_start_to: Optional[date] = Query(None, description="计划开始日期范围结束"),
    planned_end_from: Optional[date] = Query(None, description="计划完成日期范围开始"),
    planned_end_to: Optional[date] = Query(None, description="计划完成日期范围结束"),
    quality_score_min: Optional[float] = Query(None, ge=0, le=10, description="最低质量评分"),
    quality_score_max: Optional[float] = Query(None, ge=0, le=10, description="最高质量评分"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="限制数量"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    搜索需求
    
    根据多种条件搜索和筛选需求，支持分页和排序。
    """
    try:
        # 构建搜索参数
        search_params = {
            "keyword": keyword,
            "project_id": project_id,
            "parent_id": parent_id,
            "requirement_type": requirement_type.value if requirement_type else None,
            "status": [s.value for s in status_filter] if status_filter else None,
            "priority": [p.value for p in priority] if priority else None,
            "business_value": [bv.value for bv in business_value] if business_value else None,
            "complexity": [c.value for c in complexity] if complexity else None,
            "assignee_id": assignee_id,
            "creator_id": creator_id,
            "reviewer_id": reviewer_id,
            "category": category,
            "tags": tags,
            "created_from": created_from,
            "created_to": created_to,
            "planned_start_from": planned_start_from,
            "planned_start_to": planned_start_to,
            "planned_end_from": planned_end_from,
            "planned_end_to": planned_end_to,
            "quality_score_min": quality_score_min,
            "quality_score_max": quality_score_max,
            "skip": skip,
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        # 过滤掉None值
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        requirements, total = await service.search_requirements(search_params)
        
        items = [RequirementResponse.from_orm(req) for req in requirements]
        return RequirementListResponse(
            success=True,
            message="获取需求列表成功",
            data=items,
            items=items,
            total=total,
            page=(skip // limit) + 1,
            page_size=limit
        )
    
    except Exception as e:
        logger.error(f"搜索需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索需求失败")


@router.get("/projects/{project_id}", response_model=RequirementListResponse)
async def get_project_requirements(
    project_id: int = Path(..., description="项目ID"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    获取项目需求列表
    
    获取指定项目的所有需求。
    """
    try:
        requirements = await service.get_project_requirements(project_id, skip, limit)
        
        # 获取总数（这里简化处理，实际应该在service中实现）
        total = len(requirements)
        
        items = [RequirementResponse.from_orm(req) for req in requirements]
        return RequirementListResponse(
            success=True,
            message="获取项目需求列表成功",
            data=items,
            items=items,
            total=total,
            page=(skip // limit) + 1,
            page_size=limit
        )
    
    except Exception as e:
        logger.error(f"获取项目需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取项目需求失败")


@router.get("/{requirement_id}/history", response_model=RequirementWithHistoryResponse)
async def get_requirement_with_history(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    获取需求及其状态历史
    
    获取需求详情和完整的状态变更历史。
    """
    try:
        requirement = await service.get_requirement_by_id(requirement_id)
        if not requirement:
            raise HTTPException(status_code=404, detail="需求不存在")
        
        # 这里需要实现获取状态历史的逻辑
        # 暂时返回空历史
        return RequirementWithHistoryResponse(
            requirement=RequirementResponse.from_orm(requirement),
            status_history=[]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取需求历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取需求历史失败")


@router.post("/validate", response_model=Dict[str, Any])
async def validate_requirement_data(
    request: RequirementCreate,
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    验证需求数据
    
    验证需求数据的完整性和正确性，不实际创建需求。
    """
    try:
        # 这里应该实现数据验证逻辑
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # 基本验证
        if not request.title or len(request.title.strip()) == 0:
            validation_result["valid"] = False
            validation_result["errors"].append("需求标题不能为空")
        
        if len(request.title) > 200:
            validation_result["valid"] = False
            validation_result["errors"].append("需求标题长度不能超过200个字符")
        
        # 项目存在性验证（这里应该调用项目服务）
        # if not await project_service.exists(request.project_id):
        #     validation_result["valid"] = False
        #     validation_result["errors"].append("指定的项目不存在")
        
        # 父需求验证
        if request.parent_id:
            parent_requirement = await service.get_requirement_by_id(request.parent_id)
            if not parent_requirement:
                validation_result["valid"] = False
                validation_result["errors"].append("指定的父需求不存在")
            elif parent_requirement.project_id != request.project_id:
                validation_result["valid"] = False
                validation_result["errors"].append("父需求必须属于同一项目")
        
        # 日期验证
        if request.planned_start_date and request.planned_end_date:
            if request.planned_end_date < request.planned_start_date:
                validation_result["valid"] = False
                validation_result["errors"].append("计划完成日期不能早于计划开始日期")
        
        # 添加建议
        if not request.description:
            validation_result["warnings"].append("建议添加需求描述以提高需求质量")
        
        if not request.acceptance_criteria:
            validation_result["warnings"].append("建议添加验收标准以明确需求完成条件")
        
        return validation_result
    
    except Exception as e:
        logger.error(f"验证需求数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="验证需求数据失败")


@router.post("/{requirement_id}/analyze-quality", response_model=RequirementQualityAnalysisResponse)
async def analyze_requirement_quality(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    分析需求质量
    
    使用AI分析需求的质量，提供评分和改进建议。
    """
    try:
        analysis = await service.analyze_requirement_quality(requirement_id)
        
        return RequirementQualityAnalysisResponse(
            requirement_id=requirement_id,
            quality_score=analysis.quality_score,
            completeness_score=analysis.completeness_score,
            complexity_estimate=ComplexityEnum(analysis.complexity_estimate.value),
            effort_estimate=analysis.effort_estimate,
            issues=analysis.issues,
            suggestions=analysis.suggestions,
            analyzed_at=datetime.utcnow()
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"需求质量分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail="需求质量分析失败")


@router.put("/batch/status", response_model=RequirementBatchOperationResponse)
async def batch_update_status(
    request: RequirementBatchStatusUpdate,
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    批量更新需求状态
    
    批量更新多个需求的状态。
    """
    try:
        success_ids = []
        failed_items = []
        
        for requirement_id in request.requirement_ids:
            try:
                await service.update_requirement_status(
                    requirement_id=requirement_id,
                    new_status=RequirementStatus(request.status.value),
                    changed_by=current_user.id,
                    reason=request.reason
                )
                success_ids.append(requirement_id)
            except Exception as e:
                failed_items.append({
                    "requirement_id": requirement_id,
                    "error": str(e)
                })
        
        return RequirementBatchOperationResponse(
            total_count=len(request.requirement_ids),
            success_count=len(success_ids),
            failed_count=len(failed_items),
            success_ids=success_ids,
            failed_items=failed_items,
            operation_type="batch_status_update",
            executed_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"批量更新状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量更新状态失败")


@router.delete("/batch", response_model=RequirementBatchOperationResponse)
async def batch_delete_requirements(
    request: RequirementBatchDeleteRequest,
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    批量删除需求
    
    批量删除多个需求。
    """
    try:
        success_ids = []
        failed_items = []
        
        for requirement_id in request.requirement_ids:
            try:
                await service.delete_requirement(
                    requirement_id=requirement_id,
                    deleted_by=current_user.id
                )
                success_ids.append(requirement_id)
            except Exception as e:
                failed_items.append({
                    "requirement_id": requirement_id,
                    "error": str(e)
                })
        
        return RequirementBatchOperationResponse(
            total_count=len(request.requirement_ids),
            success_count=len(success_ids),
            failed_count=len(failed_items),
            success_ids=success_ids,
            failed_items=failed_items,
            operation_type="batch_delete",
            executed_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"批量删除需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量删除需求失败")


@router.get("/code/{requirement_code}", response_model=RequirementResponse)
async def get_requirement_by_code(
    requirement_code: str = Path(..., description="需求编码"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    根据需求编码获取需求
    
    通过需求编码查找需求。
    """
    try:
        requirement = await service.get_requirement_by_code(requirement_code)
        if not requirement:
            raise HTTPException(status_code=404, detail="需求不存在")
        
        return RequirementResponse.from_orm(requirement)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"根据编码获取需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="根据编码获取需求失败")


@router.post("/{requirement_id}/dependencies", response_model=RequirementDependencyResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement_dependency(
    requirement_id: int = Path(..., description="需求ID"),
    request: RequirementDependencyCreate = ...,
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    创建需求依赖关系
    
    建立需求之间的依赖关系。
    """
    try:
        # 验证需求存在
        requirement = await service.get_requirement_by_id(requirement_id)
        if not requirement:
            raise HTTPException(status_code=404, detail="需求不存在")
        
        # 验证目标需求存在
        target_requirement = await service.get_requirement_by_id(request.target_requirement_id)
        if not target_requirement:
            raise HTTPException(status_code=404, detail="目标需求不存在")
        
        # 验证不能自己依赖自己
        if requirement_id == request.target_requirement_id:
            raise HTTPException(status_code=400, detail="需求不能依赖自己")
        
        # 这里应该调用依赖管理服务
        # 暂时返回示例响应
        dependency = RequirementDependencyResponse(
            id=1,
            source_requirement_id=requirement_id,
            target_requirement_id=request.target_requirement_id,
            dependency_type=request.dependency_type,
            description=request.description,
            created_by=current_user.id,
            created_at=datetime.utcnow()
        )
        
        return dependency
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建需求依赖关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail="创建需求依赖关系失败")


@router.get("/{requirement_id}/dependencies", response_model=RequirementWithDependenciesResponse)
async def get_requirement_dependencies(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    获取需求依赖关系
    
    获取需求的所有依赖关系和被依赖关系。
    """
    try:
        requirement = await service.get_requirement_by_id(requirement_id)
        if not requirement:
            raise HTTPException(status_code=404, detail="需求不存在")
        
        # 这里应该调用依赖管理服务获取依赖关系
        # 暂时返回示例响应
        return RequirementWithDependenciesResponse(
            requirement=RequirementResponse.from_orm(requirement),
            dependencies=[],  # 需求依赖的其他需求
            dependents=[]     # 依赖此需求的其他需求
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取需求依赖关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取需求依赖关系失败")


@router.delete("/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement_dependency(
    dependency_id: int = Path(..., description="依赖关系ID"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    删除需求依赖关系
    
    删除指定的需求依赖关系。
    """
    try:
        # 这里应该调用依赖管理服务删除依赖关系
        # 暂时返回成功
        pass
    
    except Exception as e:
        logger.error(f"删除需求依赖关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除需求依赖关系失败")


# 导入导出功能（占位符实现）

@router.post("/import", response_model=RequirementImportResponse)
async def import_requirements(
    file: UploadFile = File(...),
    project_id: int = Query(..., description="目标项目ID"),
    file_format: str = Query("excel", pattern="^(excel|csv|json)$", description="文件格式"),
    overwrite_existing: bool = Query(False, description="是否覆盖已存在的需求"),
    validate_only: bool = Query(False, description="是否仅验证不导入"),
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    导入需求
    
    从Excel、CSV或JSON文件导入需求。
    """
    try:
        # 验证文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 验证文件大小（限制为10MB）
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")
        
        # 这里应该实现文件解析和导入逻辑
        # 暂时返回示例响应
        return RequirementImportResponse(
            total_rows=0,
            imported_count=0,
            skipped_count=0,
            error_count=0,
            imported_requirements=[],
            errors=[],
            warnings=[],
            import_summary={
                "file_name": file.filename,
                "file_format": file_format,
                "project_id": project_id,
                "validate_only": validate_only,
                "overwrite_existing": overwrite_existing
            },
            imported_at=datetime.utcnow()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="导入需求失败")


@router.post("/export")
async def export_requirements(
    request: RequirementExportRequest,
    current_user: User = Depends(get_current_user),
    service: RequirementService = Depends(get_requirement_service)
):
    """
    导出需求
    
    导出需求到指定格式的文件。
    """
    try:
        # 验证导出参数
        if not request.requirement_ids and not request.project_id and not request.search_params:
            raise HTTPException(
                status_code=400, 
                detail="必须指定需求ID列表、项目ID或搜索条件中的至少一个"
            )
        
        # 这里应该实现导出逻辑
        # 暂时返回成功响应
        return {
            "message": "导出请求已提交",
            "export_format": request.export_format,
            "status": "processing",
            "export_id": f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "estimated_completion": "2-5分钟"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出需求失败: {str(e)}")
        raise HTTPException(status_code=500, detail="导出需求失败")
