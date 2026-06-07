"""
项目需求集成API接口

本模块提供项目管理系统与需求管理系统集成的API接口，包括：
- 项目需求数据同步
- 任务关联管理
- 进度同步
- 状态联动
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...services.project_requirement_integration_service import (
    ProjectRequirementIntegrationService,
    get_project_requirement_integration_service
)
from ...services.auth import get_current_user
from ...models.user import User

router = APIRouter(prefix="/project-requirement-integration", tags=["项目需求集成"])


# 请求模型
class CreateTaskFromRequirementRequest(BaseModel):
    """从需求创建任务请求"""
    task_name: Optional[str] = Field(None, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: str = Field("REQUIREMENT_ANALYSIS", description="任务类型")
    assignee_id: Optional[int] = Field(None, description="指派人ID")
    planned_start_date: Optional[str] = Field(None, description="计划开始日期")
    planned_end_date: Optional[str] = Field(None, description="计划结束日期")
    estimated_hours: Optional[float] = Field(None, description="预估工时")
    tags: Optional[Dict[str, Any]] = Field(None, description="标签")

class SyncProjectRequirementsRequest(BaseModel):
    """同步项目需求请求"""
    force_sync: bool = Field(False, description="是否强制同步")


# 响应模型
class ProjectRequirementSummaryResponse(BaseModel):
    """项目需求汇总响应"""
    project_id: int
    project_name: str
    requirements_stats: Dict[str, Any]
    tasks_stats: Dict[str, Any]
    traceability_coverage: Dict[str, Any]
    progress_metrics: Dict[str, Any]
    last_sync_time: str

class TaskCreationResponse(BaseModel):
    """任务创建响应"""
    task_id: int
    task_code: str
    task_name: str
    requirement_id: int
    project_id: int
    created_at: str

class SyncResultResponse(BaseModel):
    """同步结果响应"""
    project_id: int
    sync_type: str
    total_requirements: int
    completed_requirements: int
    progress_percentage: float
    sync_time: str
    success: bool


@router.post("/projects/{project_id}/sync", response_model=SyncResultResponse)
async def sync_project_requirements(
    project_id: int = Path(..., description="项目ID"),
    request: SyncProjectRequirementsRequest = Body(...),
    current_user: User = Depends(get_current_user),
    service: ProjectRequirementIntegrationService = Depends(get_project_requirement_integration_service)
):
    """
    同步项目需求数据
    
    同步项目中的需求数据，包括统计信息、进度信息等
    """
    try:
        sync_result = await service.sync_project_requirements(project_id, current_user.id)
        
        return SyncResultResponse(
            project_id=project_id,
            sync_type="requirements",
            total_requirements=sync_result['total_requirements'],
            completed_requirements=sync_result['completed_requirements'],
            progress_percentage=sync_result['progress_percentage'],
            sync_time=sync_result.get('sync_time', ''),
            success=True
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/requirements/{requirement_id}/create-task", response_model=TaskCreationResponse)
async def create_task_from_requirement(
    requirement_id: int = Path(..., description="需求ID"),
    request: CreateTaskFromRequirementRequest = Body(...),
    current_user: User = Depends(get_current_user),
    service: ProjectRequirementIntegrationService = Depends(get_project_requirement_integration_service)
):
    """
    从需求创建任务
    
    基于需求信息创建对应的开发任务，并建立追溯关系
    """
    try:
        task_data = request.dict(exclude_unset=True)
        task = await service.create_task_from_requirement(requirement_id, task_data, current_user.id)
        
        return TaskCreationResponse(
            task_id=task.id,
            task_code=task.task_code,
            task_name=task.task_name,
            requirement_id=requirement_id,
            project_id=task.project_id,
            created_at=task.created_at.isoformat()
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.put("/tasks/{task_id}/sync-progress")
async def sync_task_progress_to_requirement(
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    service: ProjectRequirementIntegrationService = Depends(get_project_requirement_integration_service)
):
    """
    同步任务进度到需求
    
    将任务的进度和状态同步到关联的需求
    """
    try:
        success = await service.sync_task_progress_to_requirement(task_id, current_user.id)
        
        return {
            "task_id": task_id,
            "sync_success": success,
            "message": "任务进度同步成功" if success else "任务进度同步失败"
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/projects/{project_id}/summary", response_model=ProjectRequirementSummaryResponse)
async def get_project_requirement_summary(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    service: ProjectRequirementIntegrationService = Depends(get_project_requirement_integration_service)
):
    """
    获取项目需求汇总信息
    
    获取项目的需求统计、任务统计、追溯覆盖率等汇总信息
    """
    try:
        summary = await service.get_project_requirement_summary(project_id, current_user.id)
        
        return ProjectRequirementSummaryResponse(**summary)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取汇总信息失败: {str(e)}")


@router.put("/requirements/{requirement_id}/sync-status-to-tasks")
async def sync_requirement_status_to_tasks(
    requirement_id: int = Path(..., description="需求ID"),
    current_user: User = Depends(get_current_user),
    service: ProjectRequirementIntegrationService = Depends(get_project_requirement_integration_service)
):
    """
    同步需求状态到关联任务
    
    将需求状态变更同步到所有关联的任务
    """
    try:
        updated_task_ids = await service.sync_requirement_status_to_tasks(requirement_id, current_user.id)
        
        return {
            "requirement_id": requirement_id,
            "updated_task_ids": updated_task_ids,
            "updated_count": len(updated_task_ids),
            "message": f"成功同步 {len(updated_task_ids)} 个任务的状态"
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/projects/{project_id}/traceability-matrix")
async def get_project_traceability_matrix(
    project_id: int = Path(..., description="项目ID"),
    matrix_type: str = Query("requirement_to_task", description="矩阵类型"),
    current_user: User = Depends(get_current_user),
    service: ProjectRequirementIntegrationService = Depends(get_project_requirement_integration_service)
):
    """
    获取项目追溯矩阵
    
    获取项目的需求-任务追溯矩阵
    """
    try:
        # 这里可以扩展实现追溯矩阵功能
        # 目前返回基本的汇总信息
        summary = await service.get_project_requirement_summary(project_id, current_user.id)
        
        return {
            "project_id": project_id,
            "matrix_type": matrix_type,
            "traceability_data": summary['traceability_coverage'],
            "generated_at": summary['last_sync_time']
        }
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取追溯矩阵失败: {str(e)}")


@router.get("/health")
async def health_check():
    """
    健康检查接口
    """
    return {
        "status": "healthy",
        "service": "project-requirement-integration",
        "timestamp": "2024-01-01T00:00:00Z"
    }