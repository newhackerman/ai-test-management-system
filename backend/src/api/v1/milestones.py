"""
里程碑管理API接口

本模块提供里程碑管理相关的API接口，包括：
- 里程碑CRUD操作
- 里程碑依赖分析
- 里程碑影响分析
- 里程碑统计和时间轴
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.auth import get_current_user
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...models.user import User
from ...models.project import Project
from ...services.milestone_service import MilestoneService
from ...schemas.milestone import (
    CreateMilestoneRequest, UpdateMilestoneRequest, MilestoneQueryParams,
    MilestoneResponse, MilestoneListResponse, CreateMilestoneResponse,
    UpdateMilestoneResponse, DeleteMilestoneResponse, MilestoneDependencyAnalysis,
    MilestoneImpactAnalysis, MilestoneStatistics, MilestoneTimeline
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/milestones", tags=["里程碑管理"])


@router.post("/{project_id}", response_model=CreateMilestoneResponse)
async def create_milestone(
    project_id: int = Path(..., description="项目ID"),
    milestone_data: CreateMilestoneRequest = ...,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    创建里程碑
    
    在指定项目中创建新的里程碑，包括交付物和依赖关系设置。
    """
    try:
        milestone_service = MilestoneService()
        result = await milestone_service.create_milestone(
            project_id=project_id,
            milestone_data=milestone_data,
            creator_id=current_user.id,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 在项目 {project_id} 中创建里程碑")
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SAIntegrityError as e:
        logger.warning(f"创建里程碑外键/约束失败: {e}")
        raise HTTPException(status_code=400, detail="创建里程碑失败：引用的用户或关联数据不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建里程碑失败: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="创建里程碑失败")


@router.get("/{project_id}", response_model=MilestoneListResponse)
async def list_milestones(
    project_id: int = Path(..., description="项目ID"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    status: Optional[List[str]] = Query(None, description="状态过滤"),
    milestone_type: Optional[List[str]] = Query(None, description="类型过滤"),
    owner_id: Optional[int] = Query(None, description="负责人过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    date_from: Optional[str] = Query(None, description="日期范围-起始(YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="日期范围-结束(YYYY-MM-DD)"),
    overdue_only: bool = Query(False, description="仅显示逾期里程碑"),
    upcoming_days: Optional[int] = Query(None, ge=1, le=365, description="即将到期天数"),
    sort_by: str = Query("planned_date", description="排序字段"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取里程碑列表
    
    获取指定项目的里程碑列表，支持多种过滤和排序选项。
    """
    try:
        # 构建查询参数
        from datetime import datetime
        
        params = MilestoneQueryParams(
            page=page,
            size=size,
            status=status,
            milestone_type=milestone_type,
            owner_id=owner_id,
            search=search,
            date_from=datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None,
            date_to=datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None,
            overdue_only=overdue_only,
            upcoming_days=upcoming_days,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        milestone_service = MilestoneService()
        result = await milestone_service.list_milestones(
            project_id=project_id,
            params=params,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 查询项目 {project_id} 里程碑列表")
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取里程碑列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取里程碑列表失败")


@router.get("/detail/{milestone_id}", response_model=MilestoneResponse)
async def get_milestone(
    milestone_id: int = Path(..., description="里程碑ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取里程碑详情
    
    获取指定里程碑的详细信息，包括交付物和依赖关系。
    """
    try:
        milestone_service = MilestoneService()
        milestone = await milestone_service.get_milestone(
            milestone_id=milestone_id,
            session=session
        )
        
        if not milestone:
            raise HTTPException(status_code=404, detail="里程碑不存在")
        
        logger.info(f"用户 {current_user.id} 查询里程碑 {milestone_id} 详情")
        return milestone
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取里程碑详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取里程碑详情失败")


@router.put("/{milestone_id}", response_model=UpdateMilestoneResponse)
async def update_milestone(
    milestone_id: int = Path(..., description="里程碑ID"),
    milestone_data: UpdateMilestoneRequest = ...,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    更新里程碑
    
    更新指定里程碑的信息，包括状态流转和交付物管理。
    """
    try:
        milestone_service = MilestoneService()
        result = await milestone_service.update_milestone(
            milestone_id=milestone_id,
            milestone_data=milestone_data,
            updater_id=current_user.id,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 更新里程碑 {milestone_id}")
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新里程碑失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新里程碑失败")


@router.delete("/{milestone_id}", response_model=DeleteMilestoneResponse)
async def delete_milestone(
    milestone_id: int = Path(..., description="里程碑ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    删除里程碑
    
    软删除指定的里程碑，会检查依赖关系以确保数据完整性。
    """
    try:
        milestone_service = MilestoneService()
        result = await milestone_service.delete_milestone(
            milestone_id=milestone_id,
            deleter_id=current_user.id,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 删除里程碑 {milestone_id}")
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除里程碑失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除里程碑失败")


@router.get("/{milestone_id}/dependencies", response_model=MilestoneDependencyAnalysis)
async def analyze_milestone_dependencies(
    milestone_id: int = Path(..., description="里程碑ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    分析里程碑依赖关系
    
    分析指定里程碑的依赖关系，包括关键路径分析和风险评估。
    """
    try:
        milestone_service = MilestoneService()
        result = await milestone_service.analyze_milestone_dependencies(
            milestone_id=milestone_id,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 分析里程碑 {milestone_id} 依赖关系")
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析里程碑依赖关系失败: {str(e)}")
        raise HTTPException(status_code=500, detail="分析里程碑依赖关系失败")


@router.post("/{milestone_id}/impact-analysis", response_model=MilestoneImpactAnalysis)
async def analyze_milestone_impact(
    milestone_id: int = Path(..., description="里程碑ID"),
    delay_days: int = Query(..., ge=1, le=365, description="延期天数"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    分析里程碑延期影响
    
    分析指定里程碑延期对项目整体的影响，包括成本和时间影响。
    """
    try:
        milestone_service = MilestoneService()
        result = await milestone_service.analyze_milestone_impact(
            milestone_id=milestone_id,
            delay_days=delay_days,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 分析里程碑 {milestone_id} 延期 {delay_days} 天的影响")
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析里程碑影响失败: {str(e)}")
        raise HTTPException(status_code=500, detail="分析里程碑影响失败")


@router.get("/{project_id}/statistics", response_model=MilestoneStatistics)
async def get_milestone_statistics(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取里程碑统计信息
    
    获取指定项目的里程碑统计信息，包括完成率、逾期情况等。
    """
    try:
        # 校验项目是否存在
        proj = (await session.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))).scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=404, detail="项目不存在")
        milestone_service = MilestoneService()
        result = await milestone_service.get_milestone_statistics(
            project_id=project_id,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 查询项目 {project_id} 里程碑统计")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取里程碑统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取里程碑统计失败")


@router.get("/{project_id}/timeline", response_model=MilestoneTimeline)
async def get_milestone_timeline(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取里程碑时间轴
    
    获取指定项目的里程碑时间轴，包括关键路径和时间安排。
    """
    try:
        # 校验项目是否存在
        proj = (await session.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))).scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=404, detail="项目不存在")
        milestone_service = MilestoneService()
        result = await milestone_service.get_milestone_timeline(
            project_id=project_id,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 查询项目 {project_id} 里程碑时间轴")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取里程碑时间轴失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取里程碑时间轴失败")


@router.post("/{milestone_id}/complete")
async def complete_milestone(
    milestone_id: int = Path(..., description="里程碑ID"),
    completion_note: Optional[str] = Query(None, description="完成说明"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    完成里程碑
    
    标记指定里程碑为完成状态，并记录完成时间和说明。
    """
    try:
        from ...schemas.milestone import UpdateMilestoneRequest, MilestoneStatus
        from datetime import date
        
        milestone_service = MilestoneService()
        
        # 构建更新请求
        update_data = UpdateMilestoneRequest(
            status=MilestoneStatus.COMPLETED,
            actual_date=date.today()
        )
        
        result = await milestone_service.update_milestone(
            milestone_id=milestone_id,
            milestone_data=update_data,
            updater_id=current_user.id,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 完成里程碑 {milestone_id}")
        return {"success": True, "message": "里程碑已完成", "milestone": result.milestone}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"完成里程碑失败: {str(e)}")
        raise HTTPException(status_code=500, detail="完成里程碑失败")


@router.post("/{milestone_id}/reopen")
async def reopen_milestone(
    milestone_id: int = Path(..., description="里程碑ID"),
    reopen_reason: Optional[str] = Query(None, description="重新打开原因"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    重新打开里程碑
    
    将已完成的里程碑重新设置为进行中状态。
    """
    try:
        from ...schemas.milestone import UpdateMilestoneRequest, MilestoneStatus
        
        milestone_service = MilestoneService()
        
        # 构建更新请求
        update_data = UpdateMilestoneRequest(
            status=MilestoneStatus.IN_PROGRESS,
            actual_date=None
        )
        
        result = await milestone_service.update_milestone(
            milestone_id=milestone_id,
            milestone_data=update_data,
            updater_id=current_user.id,
            session=session
        )
        
        logger.info(f"用户 {current_user.id} 重新打开里程碑 {milestone_id}")
        return {"success": True, "message": "里程碑已重新打开", "milestone": result.milestone}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新打开里程碑失败: {str(e)}")
        raise HTTPException(status_code=500, detail="重新打开里程碑失败")


@router.get("/batch/summary")
async def get_milestones_summary(
    milestone_ids: List[int] = Query(..., description="里程碑ID列表"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    批量获取里程碑摘要
    
    获取多个里程碑的摘要信息，用于仪表板展示。
    """
    try:
        milestone_service = MilestoneService()
        summaries = []
        
        for milestone_id in milestone_ids:
            try:
                milestone = await milestone_service.get_milestone(milestone_id, session)
                if milestone:
                    summaries.append({
                        "milestone_id": milestone_id,
                        "milestone_name": milestone.milestone_name,
                        "status": milestone.status,
                        "planned_date": milestone.planned_date,
                        "completion_percentage": milestone.completion_percentage,
                        "days_overdue": milestone.days_overdue,
                        "days_remaining": milestone.days_remaining
                    })
                else:
                    summaries.append({
                        "milestone_id": milestone_id,
                        "error": "里程碑不存在"
                    })
            except Exception as e:
                logger.warning(f"获取里程碑 {milestone_id} 摘要失败: {str(e)}")
                summaries.append({
                    "milestone_id": milestone_id,
                    "error": str(e)
                })
        
        logger.info(f"用户 {current_user.id} 批量查询 {len(milestone_ids)} 个里程碑摘要")
        return {"summaries": summaries}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量获取里程碑摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量获取里程碑摘要失败")