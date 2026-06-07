"""
需求变更管理API

本模块提供需求变更管理的REST API接口，包括：
- 变更请求管理
- 变更审批流程
- 变更影响分析
"""
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...services.auth import get_current_user
from ...core.exceptions import BusinessLogicError, NotFoundError, ValidationError
from ...models.user import User
from ...models.requirement import ChangeStatus, ChangeType, ChangePriority
from ...services.requirement_change_service import RequirementChangeService
from ...services.enhanced_impact_analysis_service import EnhancedImpactAnalysisService
from ...schemas.requirement_change import (
    ChangeRequestCreate, ChangeRequestUpdate, ChangeRequestApproval,
    ChangeRequestResponse, ChangeRequestListResponse,
    ImpactAnalysisRequest, ImpactAnalysisResponse,
    ChangeImplementationRequest, ChangeImplementationResponse
)
from ...schemas.base import BaseResponse

router = APIRouter(prefix="/requirement-changes", tags=["需求变更管理"])


async def get_change_service(db: AsyncSession = Depends(get_async_session)) -> RequirementChangeService:
    """获取变更管理服务"""
    return RequirementChangeService(db=db)


async def get_impact_analysis_service(db: AsyncSession = Depends(get_async_session)) -> EnhancedImpactAnalysisService:
    """获取影响分析服务"""
    return EnhancedImpactAnalysisService(db=db)


@router.post("/", response_model=ChangeRequestResponse, summary="创建变更请求")
async def create_change_request(
    request: ChangeRequestCreate,
    current_user: User = Depends(get_current_user),
    service: RequirementChangeService = Depends(get_change_service)
):
    """
    创建需求变更请求
    
    - **requirement_id**: 需求ID
    - **title**: 变更标题
    - **description**: 变更描述
    - **reason**: 变更原因
    - **change_type**: 变更类型
    - **priority**: 变更优先级
    """
    try:
        return await service.create_change_request(request, current_user.id)
    except (BusinessLogicError, NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建变更请求失败: {str(e)}")


@router.get("/{change_request_id}", response_model=ChangeRequestResponse, summary="获取变更请求详情")
async def get_change_request(
    change_request_id: int = Path(..., description="变更请求ID"),
    service: RequirementChangeService = Depends(get_change_service)
):
    """获取变更请求详情"""
    try:
        return await service.get_change_request(change_request_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取变更请求失败: {str(e)}")


@router.put("/{change_request_id}", response_model=ChangeRequestResponse, summary="更新变更请求")
async def update_change_request(
    change_request_id: int = Path(..., description="变更请求ID"),
    request: ChangeRequestUpdate = ...,
    current_user: User = Depends(get_current_user),
    service: RequirementChangeService = Depends(get_change_service)
):
    """更新变更请求"""
    try:
        return await service.update_change_request(change_request_id, request, current_user.id)
    except (BusinessLogicError, NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新变更请求失败: {str(e)}")


@router.post("/{change_request_id}/approve", response_model=ChangeRequestResponse, summary="审批变更请求")
async def approve_change_request(
    change_request_id: int = Path(..., description="变更请求ID"),
    approval: ChangeRequestApproval = ...,
    current_user: User = Depends(get_current_user),
    service: RequirementChangeService = Depends(get_change_service)
):
    """
    审批变更请求
    
    - **status**: 审批结果状态
    - **approval_comments**: 审批意见
    - **implementer_id**: 指定实施人ID（可选）
    """
    try:
        return await service.approve_change_request(change_request_id, approval, current_user.id)
    except (BusinessLogicError, NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"审批变更请求失败: {str(e)}")


@router.post("/{change_request_id}/implement", response_model=ChangeRequestResponse, summary="实施变更")
async def implement_change(
    change_request_id: int = Path(..., description="变更请求ID"),
    implementation: ChangeImplementationRequest = ...,
    current_user: User = Depends(get_current_user),
    service: RequirementChangeService = Depends(get_change_service)
):
    """
    实施变更
    
    - **implementation_notes**: 实施说明
    - **actual_effort**: 实际工作量（可选）
    - **actual_cost**: 实际成本（可选）
    """
    try:
        return await service.implement_change(change_request_id, implementation, current_user.id)
    except (BusinessLogicError, NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实施变更失败: {str(e)}")


@router.get("/requirement/{requirement_id}", response_model=List[ChangeRequestResponse], summary="获取需求的变更请求")
async def get_change_requests_by_requirement(
    requirement_id: int = Path(..., description="需求ID"),
    status_filter: Optional[List[ChangeStatus]] = Query(None, description="状态过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: RequirementChangeService = Depends(get_change_service)
):
    """获取指定需求的变更请求列表"""
    try:
        return await service.get_change_requests_by_requirement(
            requirement_id, status_filter, limit, offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取变更请求列表失败: {str(e)}")


@router.get("/pending-approvals", response_model=List[ChangeRequestResponse], summary="获取待审批的变更请求")
async def get_pending_approvals(
    priority_filter: Optional[List[ChangePriority]] = Query(None, description="优先级过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    service: RequirementChangeService = Depends(get_change_service)
):
    """获取当前用户待审批的变更请求"""
    try:
        return await service.get_pending_approvals(
            approver_id=current_user.id,
            priority_filter=priority_filter,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取待审批请求失败: {str(e)}")


@router.get("/search", response_model=List[ChangeRequestResponse], summary="搜索变更请求")
async def search_change_requests(
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    status_filter: Optional[List[ChangeStatus]] = Query(None, description="状态过滤"),
    type_filter: Optional[List[ChangeType]] = Query(None, description="类型过滤"),
    priority_filter: Optional[List[ChangePriority]] = Query(None, description="优先级过滤"),
    requestor_id: Optional[int] = Query(None, description="申请人ID"),
    date_from: Optional[date] = Query(None, description="开始日期"),
    date_to: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: RequirementChangeService = Depends(get_change_service)
):
    """搜索变更请求"""
    try:
        return await service.search_change_requests(
            keyword=keyword,
            status_filter=status_filter,
            type_filter=type_filter,
            priority_filter=priority_filter,
            requestor_id=requestor_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索变更请求失败: {str(e)}")


@router.get("/statistics", summary="获取变更统计信息")
async def get_change_statistics(
    requirement_id: Optional[int] = Query(None, description="需求ID"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    service: RequirementChangeService = Depends(get_change_service)
):
    """获取变更统计信息"""
    try:
        return await service.get_change_statistics(
            requirement_id=requirement_id,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/impact-analysis", response_model=ImpactAnalysisResponse, summary="分析变更影响")
async def analyze_change_impact(
    request: ImpactAnalysisRequest,
    service: EnhancedImpactAnalysisService = Depends(get_impact_analysis_service)
):
    """
    分析变更影响
    
    - **requirement_id**: 需求ID
    - **change_type**: 变更类型
    - **change_description**: 变更描述
    - **analysis_depth**: 分析深度级别 (1-5)
    """
    try:
        return await service.analyze_change_impact(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"影响分析失败: {str(e)}")


@router.get("/impact-analysis/{requirement_id}", response_model=ImpactAnalysisResponse, summary="快速影响分析")
async def quick_impact_analysis(
    requirement_id: int = Path(..., description="需求ID"),
    change_type: ChangeType = Query(..., description="变更类型"),
    analysis_depth: int = Query(3, ge=1, le=5, description="分析深度"),
    service: EnhancedImpactAnalysisService = Depends(get_impact_analysis_service)
):
    """快速影响分析"""
    try:
        request = ImpactAnalysisRequest(
            requirement_id=requirement_id,
            change_type=change_type,
            change_description="快速分析",
            analysis_depth=analysis_depth
        )
        return await service.analyze_change_impact(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"快速影响分析失败: {str(e)}")