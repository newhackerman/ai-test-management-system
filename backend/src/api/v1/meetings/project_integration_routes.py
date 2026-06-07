"""
会议与项目管理集成API路由

本模块提供会议与项目管理模块集成的API接口，包括：
- 项目会议管理
- 项目团队同步
- 里程碑会议创建
- 会议决策转任务
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from ....core.database import get_async_session
from ....core.auth import get_current_user
from ....services.meeting_project_integration_service import MeetingProjectIntegrationService
from ....models.user import User
from ....models.meeting import MeetingType
from ....schemas.meeting_schemas import MeetingResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects", tags=["会议项目集成"])


# 请求模型
class CreateProjectMeetingRequest(BaseModel):
    """创建项目会议请求"""
    title: str = Field(..., description="会议标题")
    description: Optional[str] = Field(None, description="会议描述")
    meeting_type: str = Field(..., description="会议类型")
    scheduled_start_time: datetime = Field(..., description="计划开始时间")
    scheduled_end_time: datetime = Field(..., description="计划结束时间")
    agenda: Optional[List[Dict[str, Any]]] = Field(None, description="会议议程")
    max_participants: Optional[int] = Field(100, description="最大参与人数")
    is_recording_enabled: Optional[bool] = Field(False, description="是否启用录制")
    is_waiting_room_enabled: Optional[bool] = Field(True, description="是否启用等候室")
    auto_invite_team: Optional[bool] = Field(True, description="是否自动邀请项目团队")
    meeting_settings: Optional[Dict[str, Any]] = Field(None, description="会议设置")


class MeetingScheduleConfig(BaseModel):
    """会议计划配置"""
    weekly_sync: Optional[bool] = Field(True, description="是否生成周同步会议")
    milestone_reviews: Optional[bool] = Field(True, description="是否生成里程碑评审会议")
    task_reviews: Optional[bool] = Field(False, description="是否生成任务评审会议")
    auto_create_kickoff: Optional[bool] = Field(True, description="是否自动创建启动会议")


class MeetingDecision(BaseModel):
    """会议决策"""
    title: str = Field(..., description="决策标题")
    description: Optional[str] = Field(None, description="决策描述")
    create_task: bool = Field(False, description="是否创建任务")
    task_type: Optional[str] = Field("REQUIREMENT_ANALYSIS", description="任务类型")
    priority: Optional[str] = Field("MEDIUM", description="优先级")
    assignee_id: Optional[int] = Field(None, description="指派人ID")
    start_date: Optional[date] = Field(None, description="开始日期")
    due_date: Optional[date] = Field(None, description="截止日期")
    estimated_hours: Optional[float] = Field(None, description="预估工时")
    acceptance_criteria: Optional[str] = Field(None, description="验收标准")


class LinkDecisionsToTasksRequest(BaseModel):
    """关联决策到任务请求"""
    decisions: List[MeetingDecision] = Field(..., description="决策列表")


# 响应模型
class ProjectMeetingListResponse(BaseModel):
    """项目会议列表响应"""
    meetings: List[MeetingResponse]
    total_count: int
    project_info: Dict[str, Any]


class TeamSyncResult(BaseModel):
    """团队同步结果"""
    total_project_members: int
    existing_participants: int
    added_participants: int
    success: bool
    message: str


class MeetingScheduleItem(BaseModel):
    """会议计划项"""
    type: str
    title: str
    scheduled_date: date
    duration: int
    priority: str
    auto_create: bool
    milestone_id: Optional[int] = None
    task_id: Optional[int] = None
    recurring: Optional[bool] = False


class MeetingScheduleResponse(BaseModel):
    """会议计划响应"""
    schedule: List[MeetingScheduleItem]
    project_info: Dict[str, Any]
    total_meetings: int


class TaskCreationResult(BaseModel):
    """任务创建结果"""
    created_task_ids: List[int]
    total_decisions: int
    tasks_created: int
    success: bool
    message: str


# API路由
@router.post("/{project_id}/meetings", response_model=MeetingResponse)
async def create_project_meeting(
    project_id: int = Path(..., description="项目ID"),
    request: CreateProjectMeetingRequest = Body(..., description="创建会议请求"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """为项目创建会议"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        meeting_data = request.dict(exclude_unset=True)
        meeting = await integration_service.create_project_meeting(
            project_id=project_id,
            meeting_data=meeting_data,
            creator_id=current_user.id,
            auto_invite_team=request.auto_invite_team
        )
        
        await db.commit()
        
        return MeetingResponse.from_orm(meeting)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="创建项目会议失败")


@router.get("/{project_id}/meetings", response_model=ProjectMeetingListResponse)
async def get_project_meetings(
    project_id: int = Path(..., description="项目ID"),
    meeting_type: Optional[str] = Query(None, description="会议类型过滤"),
    status: Optional[str] = Query(None, description="会议状态过滤"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取项目会议列表"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        date_range = None
        if start_date and end_date:
            date_range = (start_date, end_date)
        
        meetings = await integration_service.get_project_meetings(
            project_id=project_id,
            user_id=current_user.id,
            meeting_type=meeting_type,
            status=status,
            date_range=date_range
        )
        
        # 获取项目信息
        project_info = {}
        if meetings and meetings[0].project:
            project_info = {
                'id': meetings[0].project.id,
                'name': meetings[0].project.project_name,
                'code': meetings[0].project.project_code,
                'status': meetings[0].project.status
            }
        
        return ProjectMeetingListResponse(
            meetings=[MeetingResponse.from_orm(meeting) for meeting in meetings],
            total_count=len(meetings),
            project_info=project_info
        )
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取项目会议列表失败")


@router.post("/{project_id}/meetings/{meeting_id}/sync-team", response_model=TeamSyncResult)
async def sync_project_team_to_meeting(
    project_id: int = Path(..., description="项目ID"),
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """同步项目团队成员到会议"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        result = await integration_service.sync_project_team_to_meeting(
            meeting_id=meeting_id,
            user_id=current_user.id
        )
        
        await db.commit()
        
        return TeamSyncResult(
            **result,
            success=True,
            message=f"成功添加 {result['added_participants']} 名团队成员到会议"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="同步团队成员失败")


@router.post("/{project_id}/milestones/{milestone_id}/meeting", response_model=MeetingResponse)
async def create_milestone_review_meeting(
    project_id: int = Path(..., description="项目ID"),
    milestone_id: int = Path(..., description="里程碑ID"),
    meeting_config: Optional[Dict[str, Any]] = Body(None, description="会议配置"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """为里程碑创建评审会议"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        meeting = await integration_service.create_milestone_review_meeting(
            milestone_id=milestone_id,
            creator_id=current_user.id,
            meeting_config=meeting_config
        )
        
        await db.commit()
        
        return MeetingResponse.from_orm(meeting)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="创建里程碑评审会议失败")


@router.get("/{project_id}/meeting-schedule", response_model=MeetingScheduleResponse)
async def generate_project_meeting_schedule(
    project_id: int = Path(..., description="项目ID"),
    config: MeetingScheduleConfig = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """生成项目会议计划"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        schedule_config = config.dict(exclude_unset=True)
        schedule = await integration_service.generate_project_meeting_schedule(
            project_id=project_id,
            user_id=current_user.id,
            schedule_config=schedule_config
        )
        
        # 获取项目信息
        project_info = {}  # 这里可以添加项目信息获取逻辑
        
        return MeetingScheduleResponse(
            schedule=[MeetingScheduleItem(**item) for item in schedule],
            project_info=project_info,
            total_meetings=len(schedule)
        )
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="生成会议计划失败")


@router.post("/{project_id}/meetings/{meeting_id}/decisions-to-tasks", response_model=TaskCreationResult)
async def link_meeting_decisions_to_tasks(
    project_id: int = Path(..., description="项目ID"),
    meeting_id: int = Path(..., description="会议ID"),
    request: LinkDecisionsToTasksRequest = Body(..., description="决策关联请求"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """将会议决策转换为项目任务"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        decisions = [decision.dict() for decision in request.decisions]
        created_task_ids = await integration_service.link_meeting_decisions_to_tasks(
            meeting_id=meeting_id,
            decisions=decisions,
            user_id=current_user.id
        )
        
        await db.commit()
        
        tasks_created = len(created_task_ids)
        total_decisions = len(request.decisions)
        
        return TaskCreationResult(
            created_task_ids=created_task_ids,
            total_decisions=total_decisions,
            tasks_created=tasks_created,
            success=True,
            message=f"成功从 {total_decisions} 个决策中创建了 {tasks_created} 个任务"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="创建任务失败")


@router.get("/{project_id}/meeting-types")
async def get_project_meeting_types(
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取项目适用的会议类型"""
    try:
        # 根据项目类型返回适用的会议类型
        meeting_types = [
            {
                'value': MeetingType.PROJECT_KICKOFF.value,
                'label': '项目启动会',
                'description': '项目开始阶段的启动会议',
                'default_duration': 120,
                'recommended_participants': ['项目团队全员']
            },
            {
                'value': MeetingType.REQUIREMENT_REVIEW.value,
                'label': '需求评审会',
                'description': '需求确认和评审会议',
                'default_duration': 90,
                'recommended_participants': ['需求团队', '业务方', '开发团队']
            },
            {
                'value': MeetingType.DESIGN_REVIEW.value,
                'label': '设计评审会',
                'description': '设计方案评审会议',
                'default_duration': 90,
                'recommended_participants': ['设计团队', '技术团队', '架构师']
            },
            {
                'value': MeetingType.CODE_REVIEW.value,
                'label': '代码评审会',
                'description': '代码质量检查会议',
                'default_duration': 60,
                'recommended_participants': ['开发团队', '架构师', '技术负责人']
            },
            {
                'value': MeetingType.TEST_REVIEW.value,
                'label': '测试评审会',
                'description': '测试计划和结果评审',
                'default_duration': 60,
                'recommended_participants': ['测试团队', '开发团队', '质量负责人']
            },
            {
                'value': MeetingType.PROGRESS_SYNC.value,
                'label': '进度同步会',
                'description': '定期进度汇报和同步',
                'default_duration': 30,
                'recommended_participants': ['项目团队', '项目经理']
            },
            {
                'value': MeetingType.PROBLEM_SOLVING.value,
                'label': '问题解决会',
                'description': '紧急问题讨论和解决',
                'default_duration': 60,
                'recommended_participants': ['相关责任人', '技术专家']
            },
            {
                'value': MeetingType.PROJECT_SUMMARY.value,
                'label': '项目总结会',
                'description': '项目结束总结和回顾',
                'default_duration': 90,
                'recommended_participants': ['项目团队全员', '干系人']
            }
        ]
        
        return {
            'meeting_types': meeting_types,
            'project_id': project_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取会议类型失败")


@router.get("/{project_id}/meeting-statistics")
async def get_project_meeting_statistics(
    project_id: int = Path(..., description="项目ID"),
    start_date: Optional[date] = Query(None, description="统计开始日期"),
    end_date: Optional[date] = Query(None, description="统计结束日期"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取项目会议统计信息"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        # 获取项目会议列表
        date_range = None
        if start_date and end_date:
            date_range = (start_date, end_date)
        
        meetings = await integration_service.get_project_meetings(
            project_id=project_id,
            user_id=current_user.id,
            date_range=date_range
        )
        
        # 统计分析
        total_meetings = len(meetings)
        completed_meetings = len([m for m in meetings if m.status == 'COMPLETED'])
        total_duration = sum(m.duration_minutes or 0 for m in meetings)
        
        # 按类型统计
        type_stats = {}
        for meeting in meetings:
            meeting_type = meeting.meeting_type.value if meeting.meeting_type else 'OTHER'
            if meeting_type not in type_stats:
                type_stats[meeting_type] = {'count': 0, 'duration': 0}
            type_stats[meeting_type]['count'] += 1
            type_stats[meeting_type]['duration'] += meeting.duration_minutes or 0
        
        # 按状态统计
        status_stats = {}
        for meeting in meetings:
            status = meeting.status.value if meeting.status else 'UNKNOWN'
            status_stats[status] = status_stats.get(status, 0) + 1
        
        return {
            'project_id': project_id,
            'total_meetings': total_meetings,
            'completed_meetings': completed_meetings,
            'completion_rate': completed_meetings / total_meetings if total_meetings > 0 else 0,
            'total_duration_minutes': total_duration,
            'avg_duration_minutes': total_duration / total_meetings if total_meetings > 0 else 0,
            'type_statistics': type_stats,
            'status_statistics': status_stats,
            'date_range': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        }
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取会议统计失败")


@router.get("/{project_id}/meetings/{meeting_id}/tasks")
async def get_meeting_related_tasks(
    project_id: int = Path(..., description="项目ID"),
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取会议相关的任务列表"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        tasks = await integration_service.get_meeting_related_tasks(
            meeting_id=meeting_id,
            user_id=current_user.id
        )
        
        return {
            'meeting_id': meeting_id,
            'project_id': project_id,
            'tasks': [
                {
                    'id': task.id,
                    'task_code': task.task_code,
                    'task_name': task.task_name,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'assignee_id': task.assignee_id,
                    'planned_start_date': task.planned_start_date.isoformat() if task.planned_start_date else None,
                    'planned_end_date': task.planned_end_date.isoformat() if task.planned_end_date else None,
                    'estimated_hours': task.estimated_hours,
                    'actual_hours': task.actual_hours,
                    'progress_percentage': task.progress_percentage,
                    'tags': task.tags,
                    'created_at': task.created_at.isoformat() if task.created_at else None
                } for task in tasks
            ],
            'total_count': len(tasks)
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取会议任务失败")


@router.post("/{project_id}/meetings/{meeting_id}/tasks/sync")
async def sync_meeting_tasks_with_project(
    project_id: int = Path(..., description="项目ID"),
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """同步会议任务与项目任务系统"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        sync_result = await integration_service.sync_meeting_tasks_with_project(
            meeting_id=meeting_id,
            user_id=current_user.id
        )
        
        await db.commit()
        
        return {
            **sync_result,
            'success': True,
            'message': f"任务同步完成，已关联 {sync_result['linked_tasks']} 个任务"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="同步任务失败")


@router.post("/{project_id}/meetings/{meeting_id}/tasks/{task_id}/link")
async def link_existing_task_to_meeting(
    project_id: int = Path(..., description="项目ID"),
    meeting_id: int = Path(..., description="会议ID"),
    task_id: int = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """将现有任务关联到会议"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        task = await integration_service.link_existing_task_to_meeting(
            meeting_id=meeting_id,
            task_id=task_id,
            user_id=current_user.id
        )
        
        await db.commit()
        
        return {
            'success': True,
            'message': f"任务 {task.task_code} 已成功关联到会议",
            'task': {
                'id': task.id,
                'task_code': task.task_code,
                'task_name': task.task_name,
                'status': task.status
            }
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="关联任务失败")


@router.get("/{project_id}/meetings/{meeting_id}/tasks/progress")
async def get_meeting_task_progress_summary(
    project_id: int = Path(..., description="项目ID"),
    meeting_id: int = Path(..., description="会议ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """获取会议任务进度摘要"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        progress_summary = await integration_service.get_meeting_task_progress_summary(
            meeting_id=meeting_id,
            user_id=current_user.id
        )
        
        return progress_summary
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="获取任务进度失败")


@router.put("/{project_id}/meetings/{meeting_id}/tasks/update-progress")
async def update_tasks_from_meeting_progress(
    project_id: int = Path(..., description="项目ID"),
    meeting_id: int = Path(..., description="会议ID"),
    task_updates: List[Dict[str, Any]] = Body(..., description="任务更新列表"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """根据会议进展更新任务状态"""
    try:
        integration_service = MeetingProjectIntegrationService(db)
        
        updated_tasks = await integration_service.update_task_from_meeting_progress(
            meeting_id=meeting_id,
            task_updates=task_updates,
            user_id=current_user.id
        )
        
        await db.commit()
        
        return {
            'success': True,
            'message': f"成功更新 {len(updated_tasks)} 个任务",
            'updated_tasks': [
                {
                    'id': task.id,
                    'task_code': task.task_code,
                    'task_name': task.task_name,
                    'status': task.status,
                    'actual_hours': task.actual_hours
                } for task in updated_tasks
            ]
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="更新任务进度失败")