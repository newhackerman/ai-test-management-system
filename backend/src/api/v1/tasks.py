"""
任务管理API接口

本模块提供任务管理的REST API接口，包括：
- 任务CRUD操作
- 任务查询和过滤
- 任务状态管理
- 任务分配和进度跟踪
- 任务依赖关系管理
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...services.task_service import TaskService, get_task_service
from ...api.auth import get_current_user
from ...models.user import User
from ...schemas.task import (
    CreateTaskRequest, UpdateTaskRequest, TaskQueryParams,
    TaskResponse, TaskListResponse, TaskSummaryResponse,
    CreateTaskResponse, UpdateTaskResponse, DeleteTaskResponse,
    TaskStatusUpdateRequest, TaskAssignmentRequest, TaskProgressUpdateRequest,
    TaskDependencyRequest, TaskStatisticsResponse,
    TaskType, TaskStatus, TaskPriority
)
from ...services.task_dependency_service import TaskDependencyService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/tasks",
    response_model=CreateTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建任务",
    description="创建新的任务，包含输入验证、权限检查和自动分配任务编码"
)
async def create_task(
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    创建任务
    
    - **project_id**: 项目ID（必填）
    - **task_name**: 任务名称（必填，1-200字符）
    - **description**: 任务描述（可选）
    - **task_type**: 任务类型（必填）
    - **priority**: 任务优先级（默认MEDIUM）
    - **assignee_id**: 执行人ID（可选）
    - **reporter_id**: 报告人ID（可选，默认为创建者）
    - **reviewer_id**: 审核人ID（可选）
    - **planned_start_date**: 计划开始日期（可选）
    - **planned_end_date**: 计划结束日期（可选，必须晚于开始日期）
    - **estimated_hours**: 预估工时（可选）
    - **parent_task_id**: 父任务ID（可选）
    - **dependency_tasks**: 依赖任务ID列表（可选）
    - **acceptance_criteria**: 验收标准（可选）
    - **tags**: 任务标签（可选）
    - **attachments**: 附件信息（可选）
    """
    try:
        task_service = TaskService(db)
        task = await task_service.create_task(request, current_user.id)
        
        return CreateTaskResponse(
            success=True,
            message="任务创建成功",
            task=TaskResponse.from_orm(task)
        )
        
    except ValidationError as e:
        logger.warning(f"任务创建数据验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"任务创建权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.warning(f"任务创建失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"任务创建失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务创建失败，请稍后重试"
        )


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    summary="获取任务列表",
    description="获取任务列表，支持分页、过滤、搜索和排序功能"
)
async def get_tasks(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    project_id: Optional[int] = Query(None, description="项目ID过滤"),
    status_filter: Optional[List[TaskStatus]] = Query(None, alias="status", description="状态过滤"),
    task_type: Optional[List[TaskType]] = Query(None, description="类型过滤"),
    priority: Optional[List[TaskPriority]] = Query(None, description="优先级过滤"),
    assignee_id: Optional[int] = Query(None, description="执行人过滤"),
    reporter_id: Optional[int] = Query(None, description="报告人过滤"),
    parent_task_id: Optional[int] = Query(None, description="父任务过滤"),
    planned_start_date_from: Optional[str] = Query(None, description="计划开始日期起"),
    planned_start_date_to: Optional[str] = Query(None, description="计划开始日期止"),
    planned_end_date_from: Optional[str] = Query(None, description="计划结束日期起"),
    planned_end_date_to: Optional[str] = Query(None, description="计划结束日期止"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: Optional[str] = Query("updated_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取任务列表
    
    支持的功能：
    - **分页**: 通过page和size参数控制
    - **项目过滤**: 按项目ID筛选任务
    - **状态过滤**: 可选择多个任务状态
    - **类型过滤**: 可选择多个任务类型
    - **优先级过滤**: 可选择多个优先级
    - **人员过滤**: 按执行人、报告人筛选
    - **层级过滤**: 按父任务筛选子任务
    - **日期过滤**: 按计划开始/结束日期范围筛选
    - **关键词搜索**: 在任务名称、编码、描述中搜索
    - **排序**: 支持多字段排序，升序或降序
    - **权限控制**: 根据用户权限返回可访问的任务
    """
    try:
        # 构建查询参数
        params = TaskQueryParams(
            page=page,
            size=size,
            project_id=project_id,
            status=status_filter,
            task_type=task_type,
            priority=priority,
            assignee_id=assignee_id,
            reporter_id=reporter_id,
            parent_task_id=parent_task_id,
            planned_start_date_from=planned_start_date_from,
            planned_start_date_to=planned_start_date_to,
            planned_end_date_from=planned_end_date_from,
            planned_end_date_to=planned_end_date_to,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        task_service = TaskService(db)
        tasks, total = await task_service.get_tasks_list(params, current_user.id)
        
        # 计算总页数
        total_pages = (total + size - 1) // size
        
        return TaskListResponse(
            tasks=[TaskResponse.from_orm(task) for task in tasks],
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
        
    except PermissionError as e:
        logger.warning(f"获取任务列表权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务列表失败，请稍后重试"
        )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="获取任务详情",
    description="根据任务ID获取任务的详细信息"
)
async def get_task(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取任务详情
    
    返回指定任务的完整信息，包括：
    - 任务基本信息
    - 任务分类信息
    - 人员分配信息
    - 时间管理信息
    - 工时管理信息
    - 依赖关系信息
    - 质量管理信息
    - 元数据信息
    """
    try:
        task_service = TaskService(db)
        task = await task_service.get_task_by_id(task_id, current_user.id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务 {task_id} 不存在"
            )
        
        return TaskResponse.from_orm(task)
        
    except PermissionError as e:
        logger.warning(f"获取任务详情权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务详情失败，请稍后重试"
        )


@router.put(
    "/tasks/{task_id}",
    response_model=UpdateTaskResponse,
    summary="更新任务信息",
    description="更新任务的完整信息"
)
async def update_task(
    task_id: int = Path(..., description="任务ID"),
    request: UpdateTaskRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    更新任务信息
    
    支持更新的字段：
    - 任务基本信息（名称、描述、类型、优先级、状态）
    - 人员分配信息（执行人、报告人、审核人）
    - 时间管理信息（计划和实际的开始结束日期）
    - 工时管理信息（预估、实际、剩余工时）
    - 依赖关系信息（父任务、依赖任务）
    - 质量管理信息（验收标准、测试用例数、缺陷数）
    - 元数据（标签、附件）
    
    注意：
    - 只能更新提供的字段，未提供的字段保持不变
    - 状态变更会触发相应的业务逻辑
    - 需要相应的权限才能更新
    """
    try:
        task_service = TaskService(db)
        task = await task_service.update_task(task_id, request, current_user.id)
        
        return UpdateTaskResponse(
            success=True,
            message="任务更新成功",
            task=TaskResponse.from_orm(task)
        )
        
    except NotFoundError as e:
        logger.warning(f"更新任务失败，任务不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"任务更新数据验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"任务更新权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"任务更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务更新失败，请稍后重试"
        )


@router.patch(
    "/tasks/{task_id}",
    response_model=UpdateTaskResponse,
    summary="部分更新任务信息",
    description="部分更新任务信息，只更新提供的字段"
)
async def patch_task(
    task_id: int = Path(..., description="任务ID"),
    request: UpdateTaskRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    部分更新任务信息
    
    与PUT方法相同，支持部分字段更新。
    只更新请求中提供的字段，其他字段保持不变。
    """
    # PATCH和PUT在这里使用相同的逻辑，因为UpdateTaskRequest已经支持部分更新
    return await update_task(task_id, request, current_user, db)


@router.delete(
    "/tasks/{task_id}",
    response_model=DeleteTaskResponse,
    summary="删除任务",
    description="删除任务，会检查依赖关系和权限"
)
async def delete_task(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    删除任务
    
    执行删除操作：
    - 检查任务状态（进行中的任务不能删除）
    - 检查子任务（有子任务的任务不能删除）
    - 检查权限（只有项目经理和任务创建者可以删除）
    - 更新项目统计信息
    
    限制条件：
    - 进行中的任务不能删除
    - 有子任务的任务不能删除
    - 需要删除权限
    """
    try:
        task_service = TaskService(db)
        success = await task_service.delete_task(task_id, current_user.id)
        
        if success:
            return DeleteTaskResponse(
                success=True,
                message="任务删除成功",
                task_id=task_id,
                deleted_at=datetime.utcnow()
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="任务删除失败"
            )
        
    except NotFoundError as e:
        logger.warning(f"删除任务失败，任务不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"任务删除验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"任务删除权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"任务删除失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务删除失败，请稍后重试"
        )


# 任务状态管理相关接口
@router.post(
    "/tasks/{task_id}/status",
    response_model=UpdateTaskResponse,
    summary="更新任务状态",
    description="单独更新任务状态，会触发相应的状态变更逻辑"
)
async def update_task_status(
    task_id: int = Path(..., description="任务ID"),
    request: TaskStatusUpdateRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    更新任务状态
    
    支持的状态流转：
    - TODO -> ASSIGNED, IN_PROGRESS, CANCELLED
    - ASSIGNED -> IN_PROGRESS, ON_HOLD, CANCELLED
    - IN_PROGRESS -> ON_HOLD, BLOCKED, PENDING_REVIEW, COMPLETED, CANCELLED
    - ON_HOLD -> IN_PROGRESS, CANCELLED
    - BLOCKED -> IN_PROGRESS, CANCELLED
    - PENDING_REVIEW -> COMPLETED, IN_PROGRESS
    - COMPLETED -> (终态)
    - CANCELLED -> (终态)
    
    状态变更会触发：
    - 自动设置实际开始/结束时间
    - 更新项目进度
    - 通知相关人员
    - 激活依赖任务
    """
    try:
        task_service = TaskService(db)
        task = await task_service.update_task_status(task_id, request, current_user.id)
        
        return UpdateTaskResponse(
            success=True,
            message=f"任务状态已更新为 {request.status.value}",
            task=TaskResponse.from_orm(task)
        )
        
    except NotFoundError as e:
        logger.warning(f"更新任务状态失败，任务不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"任务状态更新验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"任务状态更新权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"任务状态更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务状态更新失败，请稍后重试"
        )


@router.post(
    "/tasks/{task_id}/assign",
    response_model=UpdateTaskResponse,
    summary="分配任务",
    description="将任务分配给指定用户"
)
async def assign_task(
    task_id: int = Path(..., description="任务ID"),
    request: TaskAssignmentRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    分配任务
    
    将任务分配给指定的执行人：
    - 验证执行人是否是项目成员
    - 自动更新任务状态为ASSIGNED（如果当前是TODO）
    - 发送任务分配通知
    - 记录分配历史
    """
    try:
        task_service = TaskService(db)
        task = await task_service.assign_task(task_id, request, current_user.id)
        
        return UpdateTaskResponse(
            success=True,
            message="任务分配成功",
            task=TaskResponse.from_orm(task)
        )
        
    except NotFoundError as e:
        logger.warning(f"分配任务失败，任务不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"任务分配验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"任务分配权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"任务分配失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务分配失败，请稍后重试"
        )


@router.post(
    "/tasks/{task_id}/progress",
    response_model=UpdateTaskResponse,
    summary="更新任务进度",
    description="更新任务的工时和进度信息"
)
async def update_task_progress(
    task_id: int = Path(..., description="任务ID"),
    request: TaskProgressUpdateRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    更新任务进度
    
    更新任务的工时和进度信息：
    - 实际工时
    - 剩余工时
    - 进度说明
    - 遇到的问题
    
    系统会自动：
    - 计算任务完成百分比
    - 更新项目整体进度
    - 预警工时超支情况
    """
    try:
        task_service = TaskService(db)
        task = await task_service.update_task_progress(task_id, request, current_user.id)
        
        return UpdateTaskResponse(
            success=True,
            message="任务进度更新成功",
            task=TaskResponse.from_orm(task)
        )
        
    except NotFoundError as e:
        logger.warning(f"更新任务进度失败，任务不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"任务进度更新验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"任务进度更新权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"任务进度更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务进度更新失败，请稍后重试"
        )


@router.post(
    "/tasks/{task_id}/dependencies",
    response_model=UpdateTaskResponse,
    summary="设置任务依赖关系",
    description="设置任务的依赖关系"
)
async def set_task_dependencies(
    task_id: int = Path(..., description="任务ID"),
    request: TaskDependencyRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    设置任务依赖关系
    
    设置任务的依赖关系：
    - 验证依赖任务存在且属于同一项目
    - 检查循环依赖
    - 更新依赖关系
    - 重新计算关键路径
    
    依赖关系规则：
    - 任务不能依赖自己
    - 不能形成循环依赖
    - 依赖任务必须属于同一项目
    """
    try:
        task_service = TaskService(db)
        task = await task_service.set_task_dependencies(task_id, request, current_user.id)
        
        return UpdateTaskResponse(
            success=True,
            message="任务依赖关系设置成功",
            task=TaskResponse.from_orm(task)
        )
        
    except NotFoundError as e:
        logger.warning(f"设置任务依赖失败，任务不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        logger.warning(f"任务依赖设置验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"任务依赖设置权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"任务依赖设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务依赖设置失败，请稍后重试"
        )


@router.get(
    "/projects/{project_id}/tasks/statistics",
    response_model=TaskStatisticsResponse,
    summary="获取项目任务统计",
    description="获取指定项目的任务统计信息"
)
async def get_task_statistics(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取项目任务统计
    
    返回项目的任务统计信息：
    - 任务总数
    - 按状态分布
    - 按类型分布
    - 按优先级分布
    - 逾期任务数
    - 按时完成数
    - 平均完成时间
    
    用于：
    - 项目仪表板
    - 进度报告
    - 绩效分析
    """
    try:
        task_service = TaskService(db)
        statistics = await task_service.get_task_statistics(project_id, current_user.id)
        
        return statistics
        
    except NotFoundError as e:
        logger.warning(f"获取任务统计失败，项目不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        logger.warning(f"获取任务统计权限不足: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务统计失败，请稍后重试"
        )


# 任务依赖管理相关接口
@router.get(
    "/tasks/{task_id}/dependencies",
    summary="获取任务依赖关系",
    description="获取任务的依赖关系信息，包括直接依赖、被依赖任务和依赖链"
)
async def get_task_dependencies(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取任务依赖关系
    
    返回任务的完整依赖关系信息：
    - 直接依赖的任务
    - 依赖当前任务的任务
    - 完整的依赖链
    - 任务是否可以开始
    - 阻塞任务的依赖
    """
    try:
        dependency_service = TaskDependencyService(db)
        dependencies = await dependency_service.get_task_dependencies(task_id)
        
        return dependencies
        
    except NotFoundError as e:
        logger.warning(f"获取任务依赖失败，任务不存在: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取任务依赖失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务依赖失败，请稍后重试"
        )


@router.post(
    "/tasks/{task_id}/dependencies/validate",
    summary="验证任务依赖关系",
    description="验证设置的依赖关系是否会形成循环依赖"
)
async def validate_task_dependencies(
    task_id: int = Path(..., description="任务ID"),
    request: TaskDependencyRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    验证任务依赖关系
    
    检查设置的依赖关系是否合法：
    - 依赖任务是否存在
    - 是否会形成循环依赖
    - 依赖任务是否属于同一项目
    """
    try:
        # 获取任务信息
        task_service = TaskService(db)
        task = await task_service.get_task_by_id(task_id, current_user.id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务 {task_id} 不存在"
            )
        
        dependency_service = TaskDependencyService(db)
        
        # 验证依赖关系
        is_valid = await dependency_service.validate_dependencies(
            task_id, request.dependency_tasks, task.project_id
        )
        
        # 检测循环依赖
        has_circular = await dependency_service.detect_circular_dependency(
            task_id, request.dependency_tasks, task.project_id
        )
        
        return {
            "valid": is_valid and not has_circular,
            "has_circular_dependency": has_circular,
            "message": "依赖关系验证通过" if is_valid and not has_circular else "依赖关系验证失败"
        }
        
    except ValidationError as e:
        return {
            "valid": False,
            "has_circular_dependency": "循环依赖" in str(e),
            "message": str(e)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证任务依赖失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证任务依赖失败，请稍后重试"
        )


@router.get(
    "/projects/{project_id}/critical-path",
    summary="获取项目关键路径",
    description="计算并返回项目的关键路径分析结果"
)
async def get_project_critical_path(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    获取项目关键路径
    
    返回项目的关键路径分析：
    - 关键路径任务序列
    - 项目总工期
    - 所有关键任务
    - 每个任务的调度信息
    - 浮动时间分析
    
    用于：
    - 项目进度管理
    - 资源优化分配
    - 风险识别
    """
    try:
        dependency_service = TaskDependencyService(db)
        critical_path = await dependency_service.calculate_critical_path(project_id)
        
        return critical_path
        
    except Exception as e:
        logger.error(f"获取关键路径失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取关键路径失败，请稍后重试"
        )


@router.post(
    "/projects/{project_id}/tasks/activate",
    summary="激活准备就绪的任务",
    description="检查并激活所有依赖条件已满足的任务"
)
async def activate_ready_tasks(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    激活准备就绪的任务
    
    自动检查项目中所有任务的依赖条件：
    - 识别依赖条件已满足的任务
    - 自动激活这些任务
    - 更新任务状态
    - 发送通知
    
    通常在以下情况调用：
    - 任务完成后
    - 依赖关系变更后
    - 定期检查
    """
    try:
        dependency_service = TaskDependencyService(db)
        activated_tasks = await dependency_service.activate_ready_tasks(project_id)
        
        return {
            "success": True,
            "message": f"成功激活 {len(activated_tasks)} 个任务",
            "activated_tasks": activated_tasks,
            "activated_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"激活任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="激活任务失败，请稍后重试"
        )