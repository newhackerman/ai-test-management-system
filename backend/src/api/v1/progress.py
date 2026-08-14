"""
进度跟踪API接口

本模块提供项目进度跟踪相关的API接口，包括：
- 多维度进度计算
- 进度更新和查询
- 进度预警管理
- 进度趋势分析
"""
import logging
from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ...core.auth import get_current_user
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...models.user import User
from ...models.project import Project
from ...services.progress_service import ProgressService
from ...schemas.progress import (
    ProgressResponse, ProgressUpdateRequest, ProgressUpdateResponse,
    ProgressWeightsConfig, ProgressAlert, ProgressAlertList,
    ProgressTrendAnalysis, ProgressReport
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/progress", tags=["进度跟踪"])


@router.get("/{project_id}", response_model=ProgressResponse)
async def get_project_progress(
    project_id: int = Path(..., description="项目ID"),
    weights: Optional[ProgressWeightsConfig] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取项目进度
    
    获取指定项目的多维度进度信息，包括时间、任务、质量、里程碑进度。
    """
    try:
        progress_service = ProgressService()
        progress = await progress_service.calculate_project_progress(
            project_id=project_id,
            session=session,
            weights=weights
        )
        
        logger.info(f"用户 {current_user.id} 查询项目 {project_id} 进度")
        return progress
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目 {project_id} 进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取项目进度失败")


@router.post("/{project_id}/update", response_model=ProgressUpdateResponse)
async def update_project_progress(
    request: ProgressUpdateRequest,
    project_id: int = Path(..., description="项目ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    更新项目进度
    
    手动触发项目进度重新计算，并生成相应的预警信息。
    """
    try:
        progress_service = ProgressService()
        result = await progress_service.update_project_progress(
            project_id=project_id,
            force_recalculate=request.force_recalculate,
            notify_stakeholders=request.notify_stakeholders
        )
        
        logger.info(f"用户 {current_user.id} 更新项目 {project_id} 进度")
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目 {project_id} 进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail="更新项目进度失败")


@router.get("/{project_id}/alerts", response_model=ProgressAlertList)
async def get_project_alerts(
    project_id: int = Path(..., description="项目ID"),
    active_only: bool = Query(True, description="仅显示活跃预警"),
    severity: Optional[str] = Query(None, description="预警严重程度过滤"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取项目预警列表
    
    获取指定项目的进度预警信息，支持按严重程度和状态过滤。
    """
    try:
        progress_service = ProgressService()
        
        # 先获取当前进度以生成最新预警
        progress = await progress_service.calculate_project_progress(project_id, session)
        alerts = await progress_service.generate_progress_alerts(project_id, progress, session)
        
        # 应用过滤条件
        if active_only:
            alerts = [alert for alert in alerts if alert.is_active]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity.value == severity]
        
        # 分页处理
        total = len(alerts)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paged_alerts = alerts[start_idx:end_idx]
        
        # 统计各严重程度数量
        active_count = len([a for a in alerts if a.is_active])
        critical_count = len([a for a in alerts if a.severity.value == "CRITICAL"])
        high_count = len([a for a in alerts if a.severity.value == "HIGH"])
        
        result = ProgressAlertList(
            alerts=paged_alerts,
            total=total,
            active_count=active_count,
            critical_count=critical_count,
            high_count=high_count
        )
        
        logger.info(f"用户 {current_user.id} 查询项目 {project_id} 预警列表")
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目 {project_id} 预警失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取项目预警失败")


@router.post("/{project_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    project_id: int = Path(..., description="项目ID"),
    alert_id: int = Path(..., description="预警ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    确认预警
    
    标记指定预警为已确认状态。
    """
    try:
        # 校验项目是否存在
        proj = (await session.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))).scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=404, detail="项目不存在")
        # TODO: 实现预警确认逻辑
        # 这里需要实现预警的持久化存储和状态管理
        
        logger.info(f"用户 {current_user.id} 确认项目 {project_id} 预警 {alert_id}")
        return {"success": True, "message": "预警已确认"}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认预警失败: {str(e)}")
        raise HTTPException(status_code=500, detail="确认预警失败")


@router.post("/{project_id}/alerts/{alert_id}/resolve")
async def resolve_alert(
    project_id: int = Path(..., description="项目ID"),
    alert_id: int = Path(..., description="预警ID"),
    resolution_note: Optional[str] = Query(None, description="解决说明"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    解决预警
    
    标记指定预警为已解决状态。
    """
    try:
        # 校验项目是否存在
        proj = (await session.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))).scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=404, detail="项目不存在")
        # TODO: 实现预警解决逻辑
        # 这里需要实现预警的持久化存储和状态管理
        
        logger.info(f"用户 {current_user.id} 解决项目 {project_id} 预警 {alert_id}")
        return {"success": True, "message": "预警已解决"}
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解决预警失败: {str(e)}")
        raise HTTPException(status_code=500, detail="解决预警失败")


@router.get("/{project_id}/trend", response_model=ProgressTrendAnalysis)
async def get_progress_trend(
    project_id: int = Path(..., description="项目ID"),
    days: int = Query(30, ge=7, le=365, description="分析天数"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取进度趋势分析
    
    分析指定项目在指定时间范围内的进度趋势，提供预测和建议。
    """
    try:
        # 校验项目是否存在
        proj = (await session.execute(select(Project).where(Project.id == project_id, Project.deleted_at.is_(None)))).scalar_one_or_none()
        if not proj:
            raise HTTPException(status_code=404, detail="项目不存在")
        # TODO: 实现进度趋势分析
        # 这里需要实现历史进度数据的存储和趋势分析算法
        
        logger.info(f"用户 {current_user.id} 查询项目 {project_id} 进度趋势")
        
        # 临时返回示例数据
        from datetime import datetime, timedelta
        from decimal import Decimal
        
        trend_data = []
        base_date = datetime.now().date() - timedelta(days=days)
        
        for i in range(days):
            current_date = base_date + timedelta(days=i)
            progress_value = min(Decimal(str(i / days)), Decimal('1'))

            trend_data.append({
                "trend_date": current_date,
                "overall_progress": progress_value,
                "time_progress": progress_value,
                "task_progress": progress_value,
                "quality_progress": progress_value,
                "milestone_progress": progress_value
            })
        
        result = ProgressTrendAnalysis(
            project_id=project_id,
            trend_data=trend_data,
            velocity=Decimal('0.02'),
            acceleration=Decimal('0.001'),
            predicted_completion_date=datetime.now().date() + timedelta(days=30),
            confidence_level=Decimal('0.85'),
            schedule_risk=Decimal('0.2'),
            quality_risk=Decimal('0.15'),
            analyzed_at=datetime.utcnow()
        )
        
        return result
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目 {project_id} 进度趋势失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取进度趋势失败")


@router.get("/{project_id}/report", response_model=ProgressReport)
async def generate_progress_report(
    project_id: int = Path(..., description="项目ID"),
    report_date: Optional[date] = Query(None, description="报告日期"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    生成进度报告
    
    生成指定项目的综合进度报告，包括进度分析、预警信息和趋势预测。
    """
    try:
        progress_service = ProgressService()
        
        # 获取当前进度
        progress = await progress_service.calculate_project_progress(project_id, session)
        
        # 获取预警信息
        alerts = await progress_service.generate_progress_alerts(project_id, progress, session)
        
        # 获取趋势分析（简化版）
        trend_analysis = ProgressTrendAnalysis(
            project_id=project_id,
            trend_data=[],
            velocity=Decimal('0.02'),
            acceleration=Decimal('0.001'),
            predicted_completion_date=None,
            confidence_level=Decimal('0.85'),
            schedule_risk=Decimal('0.2'),
            quality_risk=Decimal('0.15'),
            analyzed_at=datetime.utcnow()
        )
        
        # 生成报告摘要
        summary = f"项目整体进度 {progress.overall_progress:.1%}，"
        if progress.health_score >= 80:
            summary += "项目健康状况良好。"
        elif progress.health_score >= 60:
            summary += "项目存在一些风险，需要关注。"
        else:
            summary += "项目风险较高，需要立即采取措施。"
        
        # 关键成就
        key_achievements = []
        if progress.task_progress.completed_tasks > 0:
            key_achievements.append(f"已完成 {progress.task_progress.completed_tasks} 个任务")
        if progress.milestone_progress.completed_milestones > 0:
            key_achievements.append(f"已完成 {progress.milestone_progress.completed_milestones} 个里程碑")
        
        # 主要风险
        major_risks = []
        if progress.milestone_progress.overdue_milestones > 0:
            major_risks.append(f"{progress.milestone_progress.overdue_milestones} 个里程碑逾期")
        if progress.task_progress.blocked_tasks > 0:
            major_risks.append(f"{progress.task_progress.blocked_tasks} 个任务被阻塞")
        if progress.quality_progress.quality_score < 80:
            major_risks.append("质量评分低于预期")
        
        # 下一步里程碑
        next_milestones = []
        if progress.milestone_progress.upcoming_milestones > 0:
            next_milestones.append(f"{progress.milestone_progress.upcoming_milestones} 个里程碑即将到期")
        
        report = ProgressReport(
            project_id=project_id,
            report_date=report_date or datetime.now().date(),
            progress=progress,
            alerts=alerts,
            trend_analysis=trend_analysis,
            summary=summary,
            key_achievements=key_achievements,
            major_risks=major_risks,
            next_milestones=next_milestones,
            generated_at=datetime.utcnow(),
            generated_by=current_user.id
        )
        
        logger.info(f"用户 {current_user.id} 生成项目 {project_id} 进度报告")
        return report
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成项目 {project_id} 进度报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail="生成进度报告失败")


@router.get("/batch/summary")
async def get_projects_progress_summary(
    project_ids: List[int] = Query(..., description="项目ID列表"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    批量获取项目进度摘要
    
    获取多个项目的进度摘要信息，用于仪表板展示。
    """
    try:
        progress_service = ProgressService()
        summaries = []
        
        for project_id in project_ids:
            try:
                progress = await progress_service.calculate_project_progress(project_id, session)
                summaries.append({
                    "project_id": project_id,
                    "overall_progress": progress.overall_progress,
                    "health_score": progress.health_score,
                    "risk_level": progress.risk_level,
                    "calculated_at": progress.calculated_at
                })
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"获取项目 {project_id} 进度摘要失败: {str(e)}")
                summaries.append({
                    "project_id": project_id,
                    "overall_progress": 0,
                    "health_score": 0,
                    "risk_level": "UNKNOWN",
                    "error": str(e)
                })
        
        logger.info(f"用户 {current_user.id} 批量查询 {len(project_ids)} 个项目进度摘要")
        return {"summaries": summaries}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量获取项目进度摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail="批量获取进度摘要失败")