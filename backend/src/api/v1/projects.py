"""
项目管理API接口

本模块提供项目管理的REST API接口，包括：
- 项目CRUD操作
- 项目查询和过滤
- 项目状态管理
- 项目权限控制
"""
import logging
import csv
import io
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...models.project import Project, ProjectStatus as ProjectModelStatus, ProjectType as ProjectModelType, RiskLevel as ProjectRiskLevel
from ...services.project_service import ProjectService, get_project_service
from ...api.auth import get_current_user
from ...models.user import User
from ...schemas.project import (
    CreateProjectRequest, UpdateProjectRequest, ProjectQueryParams,
    ProjectResponse, ProjectListResponse, ProjectSummaryResponse,
    CreateProjectResponse, UpdateProjectResponse, DeleteProjectResponse,
    ProjectType, ProjectStatus, ProjectPriority
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建项目",
    description="创建新的项目，包含输入验证、权限检查和自动分配项目编码"
)
async def create_project(
    request: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    创建项目
    
    - **project_name**: 项目名称（必填，1-200字符）
    - **description**: 项目描述（可选）
    - **project_type**: 项目类型（必填）
    - **priority**: 项目优先级（默认MEDIUM）
    - **planned_start_date**: 计划开始日期（必填）
    - **planned_end_date**: 计划结束日期（必填，必须晚于开始日期）
    - **project_manager_id**: 项目经理ID（必填）
    - **test_manager_id**: 测试经理ID（可选）
    - **client_contact**: 客户联系人（可选）
    - **budget**: 项目预算（可选）
    - **tags**: 项目标签（可选）
    - **custom_fields**: 自定义字段（可选）
    """
    try:
        project_service = ProjectService(db)
        project = await project_service.create_project(request, current_user.id)
        
        return CreateProjectResponse(
            success=True,
            message="项目创建成功",
            project=ProjectResponse.from_orm(project)
        )
        
    except ValidationError as e:
        logger.warning(f"项目创建数据验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"项目创建权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"项目创建失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="项目创建失败，请稍后重试"
        )


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="获取项目列表",
    description="获取项目列表，支持分页、过滤、搜索和排序功能"
)
async def get_projects(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    status: Optional[List[ProjectStatus]] = Query(None, description="状态过滤"),
    project_type: Optional[List[ProjectType]] = Query(None, description="类型过滤"),
    priority: Optional[List[ProjectPriority]] = Query(None, description="优先级过滤"),
    project_manager_id: Optional[int] = Query(None, description="项目经理过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: Optional[str] = Query("updated_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取项目列表
    
    支持的功能：
    - **分页**: 通过page和size参数控制
    - **状态过滤**: 可选择多个项目状态
    - **类型过滤**: 可选择多个项目类型
    - **优先级过滤**: 可选择多个优先级
    - **项目经理过滤**: 按项目经理筛选
    - **关键词搜索**: 在项目名称、编码、描述中搜索
    - **排序**: 支持多字段排序，升序或降序
    - **权限控制**: 根据用户权限返回可访问的项目
    """
    try:
        # 构建查询参数
        params = ProjectQueryParams(
            page=page,
            size=size,
            status=status,
            project_type=project_type,
            priority=priority,
            project_manager_id=project_manager_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        project_service = ProjectService(db)
        projects, total = await project_service.get_projects_list(params, current_user.id)
        
        # 计算总页数
        total_pages = (total + size - 1) // size
        
        return ProjectListResponse(
            projects=[ProjectResponse.from_orm(project) for project in projects],
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
        
    except PermissionError as e:
        logger.warning(f"获取项目列表权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目列表失败，请稍后重试"
        )


@router.get(
    "/statistics",
    summary="获取项目统计",
    description="获取项目总数、状态分布、类型分布和风险统计"
)
async def get_project_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        base_filter = Project.deleted_at.is_(None)

        total_result = await db.execute(
            select(func.count(Project.id)).where(base_filter)
        )
        active_result = await db.execute(
            select(func.count(Project.id)).where(
                base_filter,
                Project.status.in_([ProjectModelStatus.PLANNING, ProjectModelStatus.IN_PROGRESS, ProjectModelStatus.ON_HOLD])
            )
        )
        completed_result = await db.execute(
            select(func.count(Project.id)).where(base_filter, Project.status == ProjectModelStatus.COMPLETED)
        )
        overdue_result = await db.execute(
            select(func.count(Project.id)).where(
                base_filter,
                Project.planned_end_date < datetime.utcnow().date(),
                Project.status.notin_([ProjectModelStatus.COMPLETED, ProjectModelStatus.CANCELLED, ProjectModelStatus.ARCHIVED])
            )
        )
        high_risk_result = await db.execute(
            select(func.count(Project.id)).where(
                base_filter,
                Project.risk_level.in_([ProjectRiskLevel.HIGH, ProjectRiskLevel.CRITICAL])
            )
        )

        status_rows = await db.execute(
            select(Project.status, func.count(Project.id)).where(base_filter).group_by(Project.status)
        )
        type_rows = await db.execute(
            select(Project.project_type, func.count(Project.id)).where(base_filter).group_by(Project.project_type)
        )

        status_counts = {status.value: count for status, count in status_rows.all()}
        type_counts = {project_type.value: count for project_type, count in type_rows.all()}

        return {
            "success": True,
            "data": {
                "total_projects": total_result.scalar() or 0,
                "active_projects": active_result.scalar() or 0,
                "completed_projects": completed_result.scalar() or 0,
                "overdue_projects": overdue_result.scalar() or 0,
                "high_risk_projects": high_risk_result.scalar() or 0,
                "project_distribution": [
                    {"status": item.value, "count": status_counts.get(item.value, 0)}
                    for item in ProjectModelStatus
                ],
                "type_distribution": [
                    {"type": item.value, "count": type_counts.get(item.value, 0)}
                    for item in ProjectModelType
                ],
            },
            "message": "项目统计获取成功"
        }
    except Exception as e:
        logger.error(f"获取项目统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目统计失败，请稍后重试"
        )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="获取项目详情",
    description="根据项目ID获取项目的详细信息"
)
async def get_project(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取项目详情
    
    返回指定项目的完整信息，包括：
    - 项目基本信息
    - 时间管理信息
    - 人员管理信息
    - 预算信息
    - 进度信息
    - 质量信息
    - 元数据信息
    """
    try:
        project_service = ProjectService(db)
        project = await project_service.get_project_by_id(project_id, current_user.id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"项目 {project_id} 不存在"
            )
        
        return ProjectResponse.from_orm(project)
        
    except PermissionError as e:
        logger.warning(f"获取项目详情权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取项目详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目详情失败，请稍后重试"
        )


@router.put(
    "/{project_id}",
    response_model=UpdateProjectResponse,
    summary="更新项目信息",
    description="更新项目的完整信息"
)
async def update_project(
    project_id: int = Path(..., description="项目ID"),
    request: UpdateProjectRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    更新项目信息
    
    支持更新的字段：
    - 项目基本信息（名称、描述、类型、优先级、状态）
    - 时间管理信息（计划和实际的开始结束日期）
    - 人员管理信息（项目经理、测试经理、客户联系人）
    - 预算信息
    - 健康度和风险等级
    - 元数据（标签、自定义字段）
    
    注意：
    - 只能更新提供的字段，未提供的字段保持不变
    - 状态变更会触发相应的业务逻辑
    - 需要相应的权限才能更新
    """
    try:
        project_service = ProjectService(db)
        project = await project_service.update_project(project_id, request, current_user.id)
        
        return UpdateProjectResponse(
            success=True,
            message="项目更新成功",
            project=ProjectResponse.from_orm(project)
        )
        
    except NotFoundError as e:
        logger.warning(f"更新项目失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"项目更新数据验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"项目更新权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"项目更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="项目更新失败，请稍后重试"
        )


@router.patch(
    "/{project_id}",
    response_model=UpdateProjectResponse,
    summary="部分更新项目信息",
    description="部分更新项目信息，只更新提供的字段"
)
async def patch_project(
    project_id: int = Path(..., description="项目ID"),
    request: UpdateProjectRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    部分更新项目信息
    
    与PUT方法相同，支持部分字段更新。
    只更新请求中提供的字段，其他字段保持不变。
    """
    # PATCH和PUT在这里使用相同的逻辑，因为UpdateProjectRequest已经支持部分更新
    return await update_project(project_id, request, current_user, db)


@router.delete(
    "/{project_id}",
    response_model=DeleteProjectResponse,
    summary="删除项目",
    description="软删除项目，项目数据会保留但标记为已删除"
)
async def delete_project(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    删除项目
    
    执行软删除操作：
    - 项目数据不会物理删除
    - 项目状态标记为已删除
    - 设置删除时间戳
    - 项目在列表中不再显示
    - 可以通过管理员权限恢复
    
    限制条件：
    - 进行中的项目不能删除
    - 需要删除权限
    - 可能需要处理关联数据
    """
    try:
        project_service = ProjectService(db)
        success = await project_service.delete_project(project_id, current_user.id)
        
        if success:
            return DeleteProjectResponse(
                success=True,
                message="项目删除成功",
                project_id=project_id,
                deleted_at=datetime.utcnow()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="项目删除失败"
            )
        
    except NotFoundError as e:
        logger.warning(f"删除项目失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"项目删除验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"项目删除权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"项目删除失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="项目删除失败，请稍后重试"
        )


@router.post(
    "/{project_id}/duplicate",
    response_model=CreateProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="复制项目",
    description="基于现有项目创建一个新的项目副本"
)
async def duplicate_project(
    project_id: int = Path(..., description="项目ID"),
    payload: Dict[str, Any] = Body(default_factory=dict),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        project_service = ProjectService(db)
        source_project = await project_service.get_project_by_id(project_id, current_user.id)

        if not source_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"项目 {project_id} 不存在"
            )

        new_name = str(payload.get("project_name") or f"{source_project.project_name} - 副本").strip()
        request = CreateProjectRequest(
            project_name=new_name,
            description=source_project.description,
            project_type=source_project.project_type,
            priority=source_project.priority,
            planned_start_date=source_project.planned_start_date,
            planned_end_date=source_project.planned_end_date,
            project_manager_id=current_user.id,
            test_manager_id=source_project.test_manager_id,
            client_contact=source_project.client_contact,
            budget=source_project.budget,
            tags=source_project.tags,
            custom_fields=source_project.custom_fields,
        )
        project = await project_service.create_project(request, current_user.id)

        return CreateProjectResponse(
            success=True,
            message="项目复制成功",
            project=ProjectResponse.from_orm(project)
        )

    except ValidationError as e:
        logger.warning(f"复制项目验证失败: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        logger.warning(f"复制项目权限不足: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"复制项目失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="复制项目失败，请稍后重试"
        )


@router.get(
    "/{project_id}/export",
    summary="导出项目",
    description="导出项目基础信息，当前支持CSV格式"
)
async def export_project(
    project_id: int = Path(..., description="项目ID"),
    format: str = Query("csv", pattern="^(csv)$", description="导出格式"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        project_service = ProjectService(db)
        project = await project_service.get_project_by_id(project_id, current_user.id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"项目 {project_id} 不存在"
            )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["字段", "值"])
        writer.writerows([
            ["项目ID", project.id],
            ["项目编码", project.project_code],
            ["项目名称", project.project_name],
            ["项目类型", getattr(project.project_type, "value", project.project_type)],
            ["状态", getattr(project.status, "value", project.status)],
            ["优先级", getattr(project.priority, "value", project.priority)],
            ["风险等级", getattr(project.risk_level, "value", project.risk_level)],
            ["计划开始日期", project.planned_start_date.isoformat() if project.planned_start_date else ""],
            ["计划结束日期", project.planned_end_date.isoformat() if project.planned_end_date else ""],
            ["进度", str(project.progress_percentage or 0)],
            ["预算", str(project.budget or "")],
            ["描述", project.description or ""],
        ])

        content = output.getvalue().encode("utf-8-sig")
        filename = f"project_{project.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except PermissionError as e:
        logger.warning(f"导出项目权限不足: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出项目失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="导出项目失败，请稍后重试"
        )


@router.get(
    "/{project_id}/summary",
    response_model=ProjectSummaryResponse,
    summary="获取项目摘要",
    description="获取项目的摘要信息，包含关键指标和状态"
)
async def get_project_summary(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取项目摘要
    
    返回项目的关键信息摘要，适用于：
    - 项目列表的快速预览
    - 仪表板显示
    - 报告生成
    
    包含的信息：
    - 项目基本信息
    - 进度和健康度
    - 关键时间节点
    - 任务统计
    """
    try:
        project_service = ProjectService(db)
        project = await project_service.get_project_by_id(project_id, current_user.id)
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"项目 {project_id} 不存在"
            )
        
        return ProjectSummaryResponse(
            id=project.id,
            project_code=project.project_code,
            project_name=project.project_name,
            project_type=project.project_type,
            status=project.status,
            priority=project.priority,
            progress_percentage=project.progress_percentage,
            health_score=project.health_score,
            risk_level=project.risk_level,
            planned_start_date=project.planned_start_date,
            planned_end_date=project.planned_end_date,
            project_manager_id=project.project_manager_id,
            task_count=project.task_count,
            completed_task_count=project.completed_task_count,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
        
    except PermissionError as e:
        logger.warning(f"获取项目摘要权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取项目摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目摘要失败，请稍后重试"
        )


# 项目状态管理相关接口
@router.post(
    "/{project_id}/status",
    response_model=UpdateProjectResponse,
    summary="更新项目状态",
    description="单独更新项目状态，会触发相应的状态变更逻辑"
)
async def update_project_status(
    project_id: int = Path(..., description="项目ID"),
    new_status: ProjectStatus = Query(..., description="新状态"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    更新项目状态
    
    支持的状态流转：
    - PLANNING -> IN_PROGRESS, ON_HOLD, CANCELLED
    - IN_PROGRESS -> ON_HOLD, COMPLETED, CANCELLED
    - ON_HOLD -> IN_PROGRESS, CANCELLED
    - COMPLETED -> ARCHIVED
    - CANCELLED -> ARCHIVED
    
    状态变更会触发：
    - 自动设置实际开始/结束时间
    - 相关任务状态更新
    - 通知相关人员
    - 数据同步更新
    """
    try:
        request = UpdateProjectRequest(status=new_status)
        project_service = ProjectService(db)
        project = await project_service.update_project(project_id, request, current_user.id)
        
        return UpdateProjectResponse(
            success=True,
            message=f"项目状态已更新为 {new_status.value}",
            project=ProjectResponse.from_orm(project)
        )
        
    except NotFoundError as e:
        logger.warning(f"更新项目状态失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"项目状态更新验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"项目状态更新权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"项目状态更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="项目状态更新失败，请稍后重试"
        )
