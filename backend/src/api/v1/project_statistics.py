"""
项目统计分析API

本模块提供项目统计分析相关的API接口，包括：
- 项目统计数据查询
- 趋势分析
- 绩效评估
- KPI跟踪
"""
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...services.statistics_service import StatisticsService, ProjectStatistics, TrendAnalysis
from ...services.performance_evaluation_service import (
    PerformanceEvaluationService, IndividualPerformance, TeamPerformance, SkillAssessment
)
from ...services.auth import get_current_user
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/project-statistics", tags=["项目统计分析"])

# 新增性能分析相关的响应模型
class PerformanceMetricsResponse(BaseModel):
    """性能指标响应"""
    project_id: int
    time_progress: Dict[str, Any]
    task_progress: Dict[str, Any]
    quality_progress: Dict[str, Any]
    team_performance: Dict[str, Any]
    overall_progress: float
    health_score: int
    risk_level: str


class TeamMemberPerformanceResponse(BaseModel):
    """团队成员绩效响应"""
    user_id: int
    user_name: str
    role: str
    tasks_completed: int
    hours_worked: float
    efficiency: float
    quality_score: float
    collaboration_score: float
    overall_score: float


class ProjectTrendResponse(BaseModel):
    """项目趋势响应"""
    date: str
    progress: float
    velocity: float
    quality: float
    team_efficiency: float


# 请求和响应模型
class ProjectStatisticsResponse(BaseModel):
    """项目统计响应"""
    project_id: int
    time_progress: Dict[str, Any]
    task_progress: Dict[str, Any]
    quality_progress: Dict[str, Any]
    milestone_progress: Dict[str, Any]
    overall_progress: float
    efficiency_metrics: Dict[str, Any]
    cost_metrics: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    collaboration_metrics: Dict[str, Any]
    calculated_at: datetime


class TrendAnalysisResponse(BaseModel):
    """趋势分析响应"""
    metric_name: str
    time_series_data: List[Dict[str, Any]]
    trend_direction: str
    trend_strength: float
    prediction: Dict[str, Any]
    confidence_level: float
    analyzed_at: datetime


class IndividualPerformanceResponse(BaseModel):
    """个人绩效响应"""
    user_id: int
    user_name: str
    evaluation_period: List[str]  # [start_date, end_date]
    task_completion_rate: float
    on_time_delivery_rate: float
    work_hour_efficiency: float
    defect_rate: float
    rework_rate: float
    customer_satisfaction: float
    team_collaboration_score: float
    communication_effectiveness: float
    knowledge_sharing_score: float
    skill_improvement_score: float
    learning_activity_score: float
    certification_score: float
    innovation_contribution_score: float
    process_improvement_score: float
    best_practice_score: float
    overall_score: float
    performance_level: str
    detailed_metrics: Dict[str, Any]
    strengths: List[str]
    improvement_areas: List[str]
    development_recommendations: List[str]
    evaluated_at: datetime


class TeamPerformanceResponse(BaseModel):
    """团队绩效响应"""
    project_id: int
    team_members: List[int]
    evaluation_period: List[str]
    team_productivity: float
    collaboration_effectiveness: float
    goal_achievement_rate: float
    team_quality_score: float
    customer_satisfaction: float
    delivery_quality: float
    communication_score: float
    conflict_resolution_score: float
    knowledge_sharing_score: float
    skill_diversity_score: float
    learning_culture_score: float
    innovation_score: float
    overall_score: float
    team_maturity_level: str
    team_strengths: List[str]
    team_challenges: List[str]
    improvement_recommendations: List[str]
    performance_distribution: Dict[str, int]
    evaluated_at: datetime


class SkillAssessmentResponse(BaseModel):
    """技能评估响应"""
    user_id: int
    skill_category: str
    current_level: int
    target_level: int
    gap_analysis: Dict[str, Any]
    development_plan: List[Dict[str, Any]]
    assessed_at: datetime


class KPIMetricsResponse(BaseModel):
    """KPI指标响应"""
    project_id: int
    kpi_metrics: Dict[str, Any]
    benchmark_comparison: Dict[str, Any]
    performance_indicators: Dict[str, Any]
    calculated_at: datetime


@router.get("/projects/{project_id}/statistics", response_model=ProjectStatisticsResponse)
async def get_project_statistics(
    project_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目统计数据
    
    Args:
        project_id: 项目ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        项目统计数据
    """
    try:
        statistics_service = StatisticsService(db)
        statistics = await statistics_service.calculate_project_statistics(project_id)
        
        return ProjectStatisticsResponse(
            project_id=statistics.project_id,
            time_progress=statistics.time_progress,
            task_progress=statistics.task_progress,
            quality_progress=statistics.quality_progress,
            milestone_progress=statistics.milestone_progress,
            overall_progress=statistics.overall_progress,
            efficiency_metrics=statistics.efficiency_metrics,
            cost_metrics=statistics.cost_metrics,
            risk_metrics=statistics.risk_metrics,
            collaboration_metrics=statistics.collaboration_metrics,
            calculated_at=statistics.calculated_at
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取项目统计数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目统计数据失败")


@router.get("/projects/{project_id}/trends/{metric_name}", response_model=TrendAnalysisResponse)
async def get_trend_analysis(
    project_id: int,
    metric_name: str,
    days: int = Query(30, description="分析天数", ge=7, le=365),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取趋势分析
    
    Args:
        project_id: 项目ID
        metric_name: 指标名称
        days: 分析天数
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        趋势分析数据
    """
    try:
        statistics_service = StatisticsService(db)
        trend_analysis = await statistics_service.calculate_trend_analysis(
            project_id, metric_name, days
        )
        
        return TrendAnalysisResponse(
            metric_name=trend_analysis.metric_name,
            time_series_data=trend_analysis.time_series_data,
            trend_direction=trend_analysis.trend_direction,
            trend_strength=trend_analysis.trend_strength,
            prediction=trend_analysis.prediction,
            confidence_level=trend_analysis.confidence_level,
            analyzed_at=trend_analysis.analyzed_at
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取趋势分析失败: {e}")
        raise HTTPException(status_code=500, detail="获取趋势分析失败")


@router.get("/performance/individual/{user_id}", response_model=IndividualPerformanceResponse)
async def get_individual_performance(
    user_id: int,
    project_id: Optional[int] = Query(None, description="项目ID（可选）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取个人绩效评估
    
    Args:
        user_id: 用户ID
        project_id: 项目ID（可选）
        start_date: 开始日期
        end_date: 结束日期
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        个人绩效评估结果
    """
    try:
        performance_service = PerformanceEvaluationService(db)
        performance = await performance_service.evaluate_individual_performance(
            user_id, project_id, start_date, end_date
        )
        
        return IndividualPerformanceResponse(
            user_id=performance.user_id,
            user_name=performance.user_name,
            evaluation_period=[
                performance.evaluation_period[0].isoformat(),
                performance.evaluation_period[1].isoformat()
            ],
            task_completion_rate=performance.task_completion_rate,
            on_time_delivery_rate=performance.on_time_delivery_rate,
            work_hour_efficiency=performance.work_hour_efficiency,
            defect_rate=performance.defect_rate,
            rework_rate=performance.rework_rate,
            customer_satisfaction=performance.customer_satisfaction,
            team_collaboration_score=performance.team_collaboration_score,
            communication_effectiveness=performance.communication_effectiveness,
            knowledge_sharing_score=performance.knowledge_sharing_score,
            skill_improvement_score=performance.skill_improvement_score,
            learning_activity_score=performance.learning_activity_score,
            certification_score=performance.certification_score,
            innovation_contribution_score=performance.innovation_contribution_score,
            process_improvement_score=performance.process_improvement_score,
            best_practice_score=performance.best_practice_score,
            overall_score=performance.overall_score,
            performance_level=performance.performance_level,
            detailed_metrics=performance.detailed_metrics,
            strengths=performance.strengths,
            improvement_areas=performance.improvement_areas,
            development_recommendations=performance.development_recommendations,
            evaluated_at=performance.evaluated_at
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取个人绩效评估失败: {e}")
        raise HTTPException(status_code=500, detail="获取个人绩效评估失败")


@router.get("/performance/team/{project_id}", response_model=TeamPerformanceResponse)
async def get_team_performance(
    project_id: int,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取团队绩效评估
    
    Args:
        project_id: 项目ID
        start_date: 开始日期
        end_date: 结束日期
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        团队绩效评估结果
    """
    try:
        performance_service = PerformanceEvaluationService(db)
        performance = await performance_service.evaluate_team_performance(
            project_id, start_date, end_date
        )
        
        return TeamPerformanceResponse(
            project_id=performance.project_id,
            team_members=performance.team_members,
            evaluation_period=[
                performance.evaluation_period[0].isoformat(),
                performance.evaluation_period[1].isoformat()
            ],
            team_productivity=performance.team_productivity,
            collaboration_effectiveness=performance.collaboration_effectiveness,
            goal_achievement_rate=performance.goal_achievement_rate,
            team_quality_score=performance.team_quality_score,
            customer_satisfaction=performance.customer_satisfaction,
            delivery_quality=performance.delivery_quality,
            communication_score=performance.communication_score,
            conflict_resolution_score=performance.conflict_resolution_score,
            knowledge_sharing_score=performance.knowledge_sharing_score,
            skill_diversity_score=performance.skill_diversity_score,
            learning_culture_score=performance.learning_culture_score,
            innovation_score=performance.innovation_score,
            overall_score=performance.overall_score,
            team_maturity_level=performance.team_maturity_level,
            team_strengths=performance.team_strengths,
            team_challenges=performance.team_challenges,
            improvement_recommendations=performance.improvement_recommendations,
            performance_distribution=performance.performance_distribution,
            evaluated_at=performance.evaluated_at
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取团队绩效评估失败: {e}")
        raise HTTPException(status_code=500, detail="获取团队绩效评估失败")


@router.get("/skills/{user_id}/assessment", response_model=List[SkillAssessmentResponse])
async def get_skill_assessment(
    user_id: int,
    skill_categories: List[str] = Query(
        default=["技术能力", "沟通能力", "项目管理", "创新能力"],
        description="技能类别列表"
    ),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取技能评估
    
    Args:
        user_id: 用户ID
        skill_categories: 技能类别列表
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        技能评估结果列表
    """
    try:
        performance_service = PerformanceEvaluationService(db)
        assessments = await performance_service.assess_skills(user_id, skill_categories)
        
        return [
            SkillAssessmentResponse(
                user_id=assessment.user_id,
                skill_category=assessment.skill_category,
                current_level=assessment.current_level,
                target_level=assessment.target_level,
                gap_analysis=assessment.gap_analysis,
                development_plan=assessment.development_plan,
                assessed_at=assessment.assessed_at
            )
            for assessment in assessments
        ]
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取技能评估失败: {e}")
        raise HTTPException(status_code=500, detail="获取技能评估失败")


@router.get("/projects/{project_id}/kpi", response_model=KPIMetricsResponse)
async def get_kpi_metrics(
    project_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取KPI指标
    
    Args:
        project_id: 项目ID
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        KPI指标数据
    """
    try:
        statistics_service = StatisticsService(db)
        statistics = await statistics_service.calculate_project_statistics(project_id)
        
        # 计算KPI指标
        kpi_metrics = {
            "schedule_performance_index": statistics.time_progress.get('progress_rate', 0),
            "cost_performance_index": statistics.cost_metrics.get('cost_performance_index', 1.0),
            "quality_index": statistics.quality_progress.get('quality_score', 0),
            "team_efficiency_index": statistics.efficiency_metrics.get('productivity_rate', 0),
            "risk_index": 1 - (statistics.risk_metrics.get('avg_risk_score', 0) / 10),  # 风险越低，指数越高
            "customer_satisfaction_index": statistics.quality_progress.get('customer_satisfaction', 0)
        }
        
        # 基准对比（与行业平均水平对比）
        benchmark_comparison = {
            "schedule_performance": {
                "current": kpi_metrics["schedule_performance_index"],
                "benchmark": 0.85,
                "status": "above" if kpi_metrics["schedule_performance_index"] > 0.85 else "below"
            },
            "cost_performance": {
                "current": kpi_metrics["cost_performance_index"],
                "benchmark": 1.0,
                "status": "above" if kpi_metrics["cost_performance_index"] >= 1.0 else "below"
            },
            "quality": {
                "current": kpi_metrics["quality_index"],
                "benchmark": 0.9,
                "status": "above" if kpi_metrics["quality_index"] > 0.9 else "below"
            }
        }
        
        # 绩效指标
        performance_indicators = {
            "overall_health": sum(kpi_metrics.values()) / len(kpi_metrics),
            "critical_areas": [
                key for key, value in kpi_metrics.items() 
                if value < 0.7
            ],
            "excellent_areas": [
                key for key, value in kpi_metrics.items() 
                if value > 0.9
            ]
        }
        
        return KPIMetricsResponse(
            project_id=project_id,
            kpi_metrics=kpi_metrics,
            benchmark_comparison=benchmark_comparison,
            performance_indicators=performance_indicators,
            calculated_at=statistics.calculated_at
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取KPI指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取KPI指标失败")


@router.get("/projects/comparison")
async def get_projects_comparison(
    project_ids: List[int] = Query(..., description="项目ID列表"),
    metrics: List[str] = Query(
        default=["overall_progress", "cost_performance", "quality_score"],
        description="对比指标列表"
    ),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目对比分析
    
    Args:
        project_ids: 项目ID列表
        metrics: 对比指标列表
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        项目对比分析结果
    """
    try:
        statistics_service = StatisticsService(db)
        comparison_data = {}
        
        for project_id in project_ids:
            try:
                statistics = await statistics_service.calculate_project_statistics(project_id)
                
                project_metrics = {}
                for metric in metrics:
                    if metric == "overall_progress":
                        project_metrics[metric] = statistics.overall_progress
                    elif metric == "cost_performance":
                        project_metrics[metric] = statistics.cost_metrics.get('cost_performance_index', 1.0)
                    elif metric == "quality_score":
                        project_metrics[metric] = statistics.quality_progress.get('quality_score', 0)
                    elif metric == "team_efficiency":
                        project_metrics[metric] = statistics.efficiency_metrics.get('productivity_rate', 0)
                    elif metric == "risk_level":
                        project_metrics[metric] = statistics.risk_metrics.get('avg_risk_score', 0)
                
                comparison_data[f"project_{project_id}"] = project_metrics
                
            except Exception as e:
                logger.warning(f"获取项目 {project_id} 统计数据失败: {e}")
                comparison_data[f"project_{project_id}"] = {metric: 0 for metric in metrics}
        
        # 计算排名
        rankings = {}
        for metric in metrics:
            metric_values = [
                (project, data.get(metric, 0)) 
                for project, data in comparison_data.items()
            ]
            # 根据指标类型决定排序方向（风险指标越低越好，其他指标越高越好）
            reverse = metric != "risk_level"
            sorted_projects = sorted(metric_values, key=lambda x: x[1], reverse=reverse)
            rankings[metric] = [project for project, _ in sorted_projects]
        
        return {
            "comparison_data": comparison_data,
            "rankings": rankings,
            "summary": {
                "total_projects": len(project_ids),
                "metrics_compared": metrics,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
    
    except Exception as e:
        logger.error(f"获取项目对比分析失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目对比分析失败")


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    project_ids: Optional[List[int]] = Query(None, description="项目ID列表（可选）"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取仪表板汇总数据
    
    Args:
        project_ids: 项目ID列表（可选，如果不提供则获取所有项目）
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        仪表板汇总数据
    """
    try:
        statistics_service = StatisticsService(db)
        
        # 如果没有指定项目ID，获取用户有权限的所有项目
        if not project_ids:
            # 这里需要根据用户权限获取项目列表
            # 暂时使用模拟数据
            project_ids = [1, 2, 3]  # 需要实现获取用户项目列表的逻辑
        
        summary_data = {
            "total_projects": len(project_ids),
            "active_projects": 0,
            "completed_projects": 0,
            "overdue_projects": 0,
            "avg_progress": 0.0,
            "total_budget": 0.0,
            "total_cost": 0.0,
            "avg_quality_score": 0.0,
            "high_risk_projects": 0,
            "team_utilization": 0.0,
            "project_details": []
        }
        
        total_progress = 0
        total_quality = 0
        valid_projects = 0
        
        for project_id in project_ids:
            try:
                statistics = await statistics_service.calculate_project_statistics(project_id)
                
                # 累计统计数据
                total_progress += statistics.overall_progress
                total_quality += statistics.quality_progress.get('quality_score', 0)
                valid_projects += 1
                
                # 预算和成本
                budget = statistics.cost_metrics.get('budget', 0)
                cost = statistics.cost_metrics.get('actual_cost', 0)
                summary_data["total_budget"] += budget
                summary_data["total_cost"] += cost
                
                # 风险项目统计
                if statistics.risk_metrics.get('avg_risk_score', 0) > 7:
                    summary_data["high_risk_projects"] += 1
                
                # 项目详情
                project_detail = {
                    "project_id": project_id,
                    "progress": statistics.overall_progress,
                    "quality_score": statistics.quality_progress.get('quality_score', 0),
                    "risk_score": statistics.risk_metrics.get('avg_risk_score', 0),
                    "budget_utilization": cost / budget if budget > 0 else 0,
                    "team_size": statistics.collaboration_metrics.get('team_size', 0)
                }
                summary_data["project_details"].append(project_detail)
                
            except Exception as e:
                logger.warning(f"获取项目 {project_id} 汇总数据失败: {e}")
        
        # 计算平均值
        if valid_projects > 0:
            summary_data["avg_progress"] = total_progress / valid_projects
            summary_data["avg_quality_score"] = total_quality / valid_projects
        
        # 项目状态统计（基于进度）
        for detail in summary_data["project_details"]:
            if detail["progress"] >= 1.0:
                summary_data["completed_projects"] += 1
            elif detail["progress"] > 0:
                summary_data["active_projects"] += 1
        
        # 团队利用率（模拟数据）
        summary_data["team_utilization"] = 0.85
        
        return {
            "summary": summary_data,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"获取仪表板汇总数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取仪表板汇总数据失败")


# 新增性能分析相关的API端点
@router.get("/projects/{project_id}/performance/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    project_id: int,
    period: str = Query("30d", description="统计周期"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目性能指标
    
    Args:
        project_id: 项目ID
        period: 统计周期 (7d, 30d, 90d)
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        项目性能指标数据
    """
    try:
        statistics_service = StatisticsService(db)
        statistics = await statistics_service.calculate_project_statistics(project_id)
        
        # 计算健康度分数
        health_score = int(
            (statistics.overall_progress * 0.3 +
             statistics.quality_progress.get('quality_score', 0) * 0.3 +
             statistics.efficiency_metrics.get('productivity_rate', 0) * 0.2 +
             (1 - statistics.risk_metrics.get('avg_risk_score', 0) / 10) * 0.2) * 100
        )
        
        # 确定风险等级
        avg_risk_score = statistics.risk_metrics.get('avg_risk_score', 0)
        if avg_risk_score <= 3:
            risk_level = "LOW"
        elif avg_risk_score <= 6:
            risk_level = "MEDIUM"
        elif avg_risk_score <= 8:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        # 团队绩效数据
        team_performance = {
            "total_members": statistics.collaboration_metrics.get('team_size', 0),
            "active_members": statistics.collaboration_metrics.get('active_members', 0),
            "utilization_rate": statistics.efficiency_metrics.get('resource_utilization', 0.85),
            "productivity_score": statistics.efficiency_metrics.get('productivity_rate', 0.8)
        }
        
        return PerformanceMetricsResponse(
            project_id=project_id,
            time_progress={
                "progress_rate": statistics.time_progress.get('progress_rate', 0),
                "deviation": statistics.time_progress.get('deviation', 0),
                "estimated_completion": (datetime.utcnow() + timedelta(days=30)).isoformat()
            },
            task_progress={
                "total_tasks": statistics.task_progress.get('total_tasks', 0),
                "completed_tasks": statistics.task_progress.get('completed_tasks', 0),
                "in_progress_tasks": statistics.task_progress.get('in_progress_tasks', 0),
                "progress_rate": statistics.task_progress.get('progress_rate', 0)
            },
            quality_progress={
                "test_case_count": statistics.quality_progress.get('test_case_count', 0),
                "passed_test_count": statistics.quality_progress.get('passed_test_count', 0),
                "defect_count": statistics.quality_progress.get('defect_count', 0),
                "progress_rate": statistics.quality_progress.get('quality_score', 0)
            },
            team_performance=team_performance,
            overall_progress=statistics.overall_progress,
            health_score=health_score,
            risk_level=risk_level
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取项目性能指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目性能指标失败")


@router.get("/projects/{project_id}/performance/team", response_model=List[TeamMemberPerformanceResponse])
async def get_team_performance_metrics(
    project_id: int,
    period: str = Query("30d", description="统计周期"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取团队成员绩效指标
    
    Args:
        project_id: 项目ID
        period: 统计周期
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        团队成员绩效指标列表
    """
    try:
        performance_service = PerformanceEvaluationService(db)
        
        # 获取项目团队成员
        from ...services.team_service import TeamService
        team_service = TeamService(db)
        team_members = await team_service.get_project_members(project_id)
        
        team_performance_list = []
        
        for member in team_members:
            try:
                # 获取个人绩效数据
                performance = await performance_service.evaluate_individual_performance(
                    member.user_id, project_id
                )
                
                team_performance_list.append(TeamMemberPerformanceResponse(
                    user_id=member.user_id,
                    user_name=performance.user_name,
                    role=member.role_in_project,
                    tasks_completed=int(performance.detailed_metrics.get('tasks_completed', 0)),
                    hours_worked=float(performance.detailed_metrics.get('hours_worked', 0)),
                    efficiency=performance.work_hour_efficiency,
                    quality_score=performance.detailed_metrics.get('quality_score', 0.8),
                    collaboration_score=performance.team_collaboration_score,
                    overall_score=performance.overall_score
                ))
                
            except Exception as e:
                logger.warning(f"获取成员 {member.user_id} 绩效数据失败: {e}")
                # 提供默认数据
                team_performance_list.append(TeamMemberPerformanceResponse(
                    user_id=member.user_id,
                    user_name=f"用户{member.user_id}",
                    role=member.role_in_project,
                    tasks_completed=0,
                    hours_worked=0.0,
                    efficiency=0.0,
                    quality_score=0.0,
                    collaboration_score=0.0,
                    overall_score=0.0
                ))
        
        # 按综合评分排序
        team_performance_list.sort(key=lambda x: x.overall_score, reverse=True)
        
        return team_performance_list
    
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取团队绩效指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取团队绩效指标失败")


@router.get("/projects/{project_id}/performance/trends", response_model=List[ProjectTrendResponse])
async def get_performance_trends(
    project_id: int,
    period: str = Query("30d", description="统计周期"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取项目性能趋势数据
    
    Args:
        project_id: 项目ID
        period: 统计周期
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        项目性能趋势数据列表
    """
    try:
        # 解析周期
        days = 30
        if period == "7d":
            days = 7
        elif period == "90d":
            days = 90
        
        # 生成趋势数据（这里使用模拟数据，实际应该从数据库获取历史数据）
        trends = []
        base_date = datetime.utcnow() - timedelta(days=days)
        
        for i in range(days):
            current_date = base_date + timedelta(days=i)
            
            # 模拟趋势数据（实际应该从历史统计数据中获取）
            progress = min(0.1 + (i / days) * 0.8 + (i % 7) * 0.02, 1.0)
            velocity = 0.7 + (i % 5) * 0.05
            quality = 0.8 + (i % 3) * 0.03
            team_efficiency = 0.75 + (i % 4) * 0.04
            
            trends.append(ProjectTrendResponse(
                date=current_date.strftime("%Y-%m-%d"),
                progress=progress,
                velocity=velocity,
                quality=quality,
                team_efficiency=team_efficiency
            ))
        
        return trends
    
    except Exception as e:
        logger.error(f"获取项目性能趋势失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目性能趋势失败")


@router.post("/projects/{project_id}/performance/export")
async def export_performance_report(
    project_id: int,
    format: str = Query("excel", description="导出格式 (excel, pdf)"),
    period: str = Query("30d", description="统计周期"),
    date_range: Optional[Dict[str, str]] = None,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    导出性能分析报告
    
    Args:
        project_id: 项目ID
        format: 导出格式
        period: 统计周期
        date_range: 日期范围
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        导出的报告文件
    """
    try:
        from fastapi.responses import StreamingResponse
        import io
        
        # 获取性能数据
        statistics_service = StatisticsService(db)
        statistics = await statistics_service.calculate_project_statistics(project_id)
        
        if format == "excel":
            # 创建Excel报告
            import pandas as pd
            
            # 准备数据
            summary_data = {
                "指标": ["整体进度", "时间进度", "任务进度", "质量进度", "团队效率"],
                "数值": [
                    f"{statistics.overall_progress:.1%}",
                    f"{statistics.time_progress.get('progress_rate', 0):.1%}",
                    f"{statistics.task_progress.get('progress_rate', 0):.1%}",
                    f"{statistics.quality_progress.get('quality_score', 0):.1%}",
                    f"{statistics.efficiency_metrics.get('productivity_rate', 0):.1%}"
                ]
            }
            
            df = pd.DataFrame(summary_data)
            
            # 创建Excel文件
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='性能分析', index=False)
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.read()),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=project-{project_id}-performance-report.xlsx"}
            )
        
        elif format == "pdf":
            # 创建PDF报告（简化版本）
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            output = io.BytesIO()
            p = canvas.Canvas(output, pagesize=letter)
            
            # 添加标题
            p.setFont("Helvetica-Bold", 16)
            p.drawString(100, 750, f"Project {project_id} Performance Report")
            
            # 添加内容
            p.setFont("Helvetica", 12)
            y_position = 700
            
            metrics = [
                f"Overall Progress: {statistics.overall_progress:.1%}",
                f"Time Progress: {statistics.time_progress.get('progress_rate', 0):.1%}",
                f"Task Progress: {statistics.task_progress.get('progress_rate', 0):.1%}",
                f"Quality Score: {statistics.quality_progress.get('quality_score', 0):.1%}",
                f"Team Efficiency: {statistics.efficiency_metrics.get('productivity_rate', 0):.1%}"
            ]
            
            for metric in metrics:
                p.drawString(100, y_position, metric)
                y_position -= 30
            
            p.save()
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.read()),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=project-{project_id}-performance-report.pdf"}
            )
        
        else:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
    
    except Exception as e:
        logger.error(f"导出性能分析报告失败: {e}")
        raise HTTPException(status_code=500, detail="导出性能分析报告失败")