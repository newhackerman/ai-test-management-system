"""
项目数据API接口

本模块提供项目数据的API接口，支持项目数据的查询、同步和管理功能。
为AI助手提供项目上下文数据访问接口。

主要功能：
1. 项目列表查询
2. 项目详情获取
3. 项目上下文数据获取
4. 项目数据同步触发
5. 项目指标查询
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, NotFoundError
from ...services.project_data_sync_service import (
    get_project_sync_service, 
    get_project_context,
    sync_project_data,
    notify_project_change,
    SyncEventType
)
from ...services.auth import get_current_user
from ...models.user import User
from ...models.project import Project, ProjectMetrics
from ...models.requirement import Requirement
from ...models.test_case import TestCase, Defect

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic模型定义
class ProjectSummaryResponse(BaseModel):
    """项目摘要响应模型"""
    project_id: int
    project_name: str
    project_status: str
    requirements: Dict[str, Any]
    test_cases: Dict[str, Any]
    defects: Dict[str, Any]
    metrics: Optional[Dict[str, Any]]
    last_updated: str


class ProjectContextResponse(BaseModel):
    """项目上下文响应模型"""
    project: Dict[str, Any]
    requirements: List[Dict[str, Any]]
    test_cases: List[Dict[str, Any]]
    defects: List[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]]
    last_updated: str


class ProjectListResponse(BaseModel):
    """项目列表响应模型"""
    projects: List[Dict[str, Any]]
    total: int
    page: int
    size: int


class SyncRequest(BaseModel):
    """同步请求模型"""
    project_ids: Optional[List[int]] = Field(None, description="要同步的项目ID列表，为空则同步所有项目")
    force_refresh: bool = Field(False, description="是否强制刷新缓存")


class SyncResponse(BaseModel):
    """同步响应模型"""
    success: bool
    message: str
    synced_projects: List[int]
    failed_projects: List[int]


@router.get("/projects", response_model=ProjectListResponse, summary="获取项目列表")
async def get_projects(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    status: Optional[str] = Query(None, description="项目状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    sync_service = Depends(get_project_sync_service)
):
    """
    获取项目列表
    
    支持分页、状态过滤和关键词搜索功能。
    """
    try:
        # 构建状态过滤条件
        status_filter = None
        if status:
            status_filter = [status.upper()]
        
        # 获取项目列表
        projects = await sync_service.get_projects_list(
            user_id=current_user.id,
            status_filter=status_filter
        )
        
        # 搜索过滤
        if search:
            search_lower = search.lower()
            projects = [
                project for project in projects
                if search_lower in project['name'].lower() or 
                   (project['description'] and search_lower in project['description'].lower())
            ]
        
        # 分页处理
        total = len(projects)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_projects = projects[start_idx:end_idx]
        
        return ProjectListResponse(
            projects=paginated_projects,
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目列表失败")


@router.get("/projects/{project_id}", response_model=Dict[str, Any], summary="获取项目详情")
async def get_project_detail(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取项目详细信息
    """
    try:
        from sqlalchemy import select
        
        # 查询项目信息
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        return project.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目{project_id}详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目详情失败")


@router.get("/projects/{project_id}/summary", response_model=ProjectSummaryResponse, summary="获取项目摘要")
async def get_project_summary(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    sync_service = Depends(get_project_sync_service)
):
    """
    获取项目摘要信息
    
    包括项目基本信息、需求统计、测试统计、缺陷统计等。
    """
    try:
        summary = await sync_service.get_project_summary(project_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        return ProjectSummaryResponse(**summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目{project_id}摘要失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目摘要失败")


@router.get("/projects/{project_id}/context", response_model=ProjectContextResponse, summary="获取项目上下文")
async def get_project_context_api(
    project_id: int = Path(..., description="项目ID"),
    force_refresh: bool = Query(False, description="是否强制刷新缓存"),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目完整上下文数据
    
    包括项目信息、需求列表、测试用例列表、缺陷列表、质量指标等。
    用于AI助手分析项目状况。
    """
    try:
        context = await get_project_context(project_id, force_refresh)
        
        if not context:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        return ProjectContextResponse(
            project=context.project,
            requirements=context.requirements,
            test_cases=context.test_cases,
            defects=context.defects,
            metrics=context.metrics,
            last_updated=context.last_updated.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目{project_id}上下文失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目上下文失败")


@router.get("/projects/{project_id}/metrics", response_model=List[Dict[str, Any]], summary="获取项目指标历史")
async def get_project_metrics(
    project_id: int = Path(..., description="项目ID"),
    days: int = Query(30, ge=1, le=365, description="获取最近多少天的指标"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取项目指标历史数据
    """
    try:
        from sqlalchemy import select
        
        # 计算时间范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 查询指标数据
        result = await db.execute(
            select(ProjectMetrics)
            .where(
                ProjectMetrics.project_id == project_id,
                ProjectMetrics.metric_date >= start_date,
                ProjectMetrics.metric_date <= end_date
            )
            .order_by(ProjectMetrics.metric_date.desc())
        )
        metrics = result.scalars().all()
        
        return [metric.to_dict() for metric in metrics]
        
    except Exception as e:
        logger.error(f"获取项目{project_id}指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目指标失败")


@router.post("/sync", response_model=SyncResponse, summary="同步项目数据")
async def sync_projects_data(
    request: SyncRequest,
    current_user: User = Depends(get_current_user),
    sync_service = Depends(get_project_sync_service)
):
    """
    手动触发项目数据同步
    
    可以同步指定项目或所有项目的数据。
    """
    try:
        synced_projects = []
        failed_projects = []
        
        # 确定要同步的项目列表
        if request.project_ids:
            project_ids = request.project_ids
        else:
            # 获取所有活跃项目
            projects = await sync_service.get_projects_list(
                status_filter=['PLANNING', 'ACTIVE']
            )
            project_ids = [project['id'] for project in projects]
        
        # 同步各个项目
        for project_id in project_ids:
            try:
                await sync_project_data(project_id)
                synced_projects.append(project_id)
                logger.info(f"项目{project_id}同步成功")
            except Exception as e:
                failed_projects.append(project_id)
                logger.error(f"项目{project_id}同步失败: {e}")
        
        success = len(failed_projects) == 0
        message = f"同步完成，成功{len(synced_projects)}个，失败{len(failed_projects)}个"
        
        return SyncResponse(
            success=success,
            message=message,
            synced_projects=synced_projects,
            failed_projects=failed_projects
        )
        
    except Exception as e:
        logger.error(f"同步项目数据失败: {e}")
        raise HTTPException(status_code=500, detail="同步项目数据失败")


@router.post("/projects/{project_id}/sync", summary="同步单个项目数据")
async def sync_single_project(
    project_id: int = Path(..., description="项目ID"),
    force_refresh: bool = Query(False, description="是否强制刷新缓存"),
    current_user: User = Depends(get_current_user)
):
    """
    同步单个项目的数据
    """
    try:
        await sync_project_data(project_id)
        
        return {
            "success": True,
            "message": f"项目{project_id}同步成功",
            "project_id": project_id,
            "synced_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"同步项目{project_id}失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步项目{project_id}失败")


@router.post("/projects/{project_id}/metrics/update", summary="更新项目指标")
async def update_project_metrics(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    sync_service = Depends(get_project_sync_service)
):
    """
    手动更新项目指标
    """
    try:
        await sync_service.update_project_metrics(project_id)
        
        return {
            "success": True,
            "message": f"项目{project_id}指标更新成功",
            "project_id": project_id,
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新项目{project_id}指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新项目{project_id}指标失败")


@router.get("/sync/status", summary="获取同步状态")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    sync_service = Depends(get_project_sync_service)
):
    """
    获取数据同步服务状态
    """
    try:
        return {
            "sync_running": sync_service.sync_running,
            "queue_size": sync_service.sync_queue.qsize(),
            "cache_ttl": sync_service.cache_ttl,
            "sync_interval": sync_service.sync_interval,
            "batch_size": sync_service.batch_size,
            "status": "running" if sync_service.sync_running else "stopped"
        }
        
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取同步状态失败")


@router.post("/sync/start", summary="启动同步服务")
async def start_sync_service(
    current_user: User = Depends(get_current_user),
    sync_service = Depends(get_project_sync_service)
):
    """
    启动数据同步服务
    """
    try:
        await sync_service.start_sync_worker()
        
        return {
            "success": True,
            "message": "同步服务已启动",
            "started_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"启动同步服务失败: {e}")
        raise HTTPException(status_code=500, detail="启动同步服务失败")


@router.post("/sync/stop", summary="停止同步服务")
async def stop_sync_service(
    current_user: User = Depends(get_current_user),
    sync_service = Depends(get_project_sync_service)
):
    """
    停止数据同步服务
    """
    try:
        await sync_service.stop_sync_worker()
        
        return {
            "success": True,
            "message": "同步服务已停止",
            "stopped_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"停止同步服务失败: {e}")
        raise HTTPException(status_code=500, detail="停止同步服务失败")


# 数据变更通知接口（供内部系统调用）
@router.post("/notify/project/{project_id}/created", include_in_schema=False)
async def notify_project_created(
    project_id: int,
    project_data: Dict[str, Any],
    user_id: Optional[int] = None
):
    """通知项目创建"""
    await notify_project_change(
        SyncEventType.PROJECT_CREATED,
        project_id,
        project_id,
        project_data,
        user_id
    )
    return {"success": True}


@router.post("/notify/project/{project_id}/updated", include_in_schema=False)
async def notify_project_updated(
    project_id: int,
    project_data: Dict[str, Any],
    user_id: Optional[int] = None
):
    """通知项目更新"""
    await notify_project_change(
        SyncEventType.PROJECT_UPDATED,
        project_id,
        project_id,
        project_data,
        user_id
    )
    return {"success": True}


@router.post("/notify/requirement/{requirement_id}/created", include_in_schema=False)
async def notify_requirement_created(
    requirement_id: int,
    project_id: int,
    requirement_data: Dict[str, Any],
    user_id: Optional[int] = None
):
    """通知需求创建"""
    await notify_project_change(
        SyncEventType.REQUIREMENT_CREATED,
        requirement_id,
        project_id,
        requirement_data,
        user_id
    )
    return {"success": True}


@router.post("/notify/requirement/{requirement_id}/updated", include_in_schema=False)
async def notify_requirement_updated(
    requirement_id: int,
    project_id: int,
    requirement_data: Dict[str, Any],
    user_id: Optional[int] = None
):
    """通知需求更新"""
    await notify_project_change(
        SyncEventType.REQUIREMENT_UPDATED,
        requirement_id,
        project_id,
        requirement_data,
        user_id
    )
    return {"success": True}


@router.post("/notify/test-case/{test_case_id}/created", include_in_schema=False)
async def notify_test_case_created(
    test_case_id: int,
    project_id: int,
    test_case_data: Dict[str, Any],
    user_id: Optional[int] = None
):
    """通知测试用例创建"""
    await notify_project_change(
        SyncEventType.TEST_CASE_CREATED,
        test_case_id,
        project_id,
        test_case_data,
        user_id
    )
    return {"success": True}


@router.post("/notify/test-case/{test_case_id}/updated", include_in_schema=False)
async def notify_test_case_updated(
    test_case_id: int,
    project_id: int,
    test_case_data: Dict[str, Any],
    user_id: Optional[int] = None
):
    """通知测试用例更新"""
    await notify_project_change(
        SyncEventType.TEST_CASE_UPDATED,
        test_case_id,
        project_id,
        test_case_data,
        user_id
    )
    return {"success": True}


@router.post("/notify/defect/{defect_id}/created", include_in_schema=False)
async def notify_defect_created(
    defect_id: int,
    project_id: int,
    defect_data: Dict[str, Any],
    user_id: Optional[int] = None
):
    """通知缺陷创建"""
    await notify_project_change(
        SyncEventType.DEFECT_CREATED,
        defect_id,
        project_id,
        defect_data,
        user_id
    )
    return {"success": True}


@router.post("/notify/defect/{defect_id}/updated", include_in_schema=False)
async def notify_defect_updated(
    defect_id: int,
    project_id: int,
    defect_data: Dict[str, Any],
    user_id: Optional[int] = None
):
    """通知缺陷更新"""
    await notify_project_change(
        SyncEventType.DEFECT_UPDATED,
        defect_id,
        project_id,
        defect_data,
        user_id
    )
    return {"success": True}