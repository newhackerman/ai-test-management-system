"""
绩效评估API

本模块提供绩效评估相关的API接口，包括：
- 个人绩效评估
- 团队绩效评估
- 360度评估
- 技能评估和发展建议
"""
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ...core.database import get_async_session
from ...core.exceptions import ValidationError, NotFoundError, PermissionError
from ...services.performance_evaluation_service import (
    PerformanceEvaluationService, IndividualPerformance, TeamPerformance, SkillAssessment
)
from ...services.auth import get_current_user
from ...models.user import User
from ...schemas.statistics import (
    IndividualPerformanceRequest, IndividualPerformanceResponse,
    TeamPerformanceRequest, TeamPerformanceResponse,
    SkillAssessmentRequest, SkillAssessmentResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["绩效评估"])


# 360度评估相关模型
class Feedback360Request(BaseModel):
    """360度反馈请求"""
    target_user_id: int = Field(..., gt=0, description="被评估用户ID")
    feedback_type: str = Field(..., description="反馈类型")
    rating: int = Field(..., ge=1, le=5, description="评分")
    comments: Optional[str] = Field(None, description="评论")
    anonymous: bool = Field(default=False, description="是否匿名")


class Feedback360Response(BaseModel):
    """360度反馈响应"""
    id: int = Field(..., description="反馈ID")
    target_user_id: int = Field(..., description="被评估用户ID")
    feedback_type: str = Field(..., description="反馈类型")
    rating: int = Field(..., description="评分")
    comments: Optional[str] = Field(None, description="评论")
    anonymous: bool = Field(..., description="是否匿名")
    created_at: datetime = Field(..., description="创建时间")


class Performance360Summary(BaseModel):
    """360度绩效汇总"""
    user_id: int = Field(..., description="用户ID")
    feedback_count: int = Field(..., description="反馈数量")
    avg_rating: float = Field(..., description="平均评分")
    feedback_by_type: Dict[str, Dict[str, Any]] = Field(..., description="按类型分组的反馈")
    strengths: List[str] = Field(..., description="优势")
    improvement_areas: List[str] = Field(..., description="改进领域")
    generated_at: datetime = Field(..., description="生成时间")


class PerformanceGoalRequest(BaseModel):
    """绩效目标请求"""
    user_id: int = Field(..., gt=0, description="用户ID")
    goal_title: str = Field(..., min_length=1, max_length=200, description="目标标题")
    goal_description: str = Field(..., description="目标描述")
    target_value: float = Field(..., description="目标值")
    current_value: float = Field(default=0.0, description="当前值")
    deadline: date = Field(..., description="截止日期")
    priority: str = Field(default="MEDIUM", description="优先级")


class PerformanceGoalResponse(BaseModel):
    """绩效目标响应"""
    id: int = Field(..., description="目标ID")
    user_id: int = Field(..., description="用户ID")
    goal_title: str = Field(..., description="目标标题")
    goal_description: str = Field(..., description="目标描述")
    target_value: float = Field(..., description="目标值")
    current_value: float = Field(..., description="当前值")
    progress_percentage: float = Field(..., description="完成百分比")
    deadline: date = Field(..., description="截止日期")
    priority: str = Field(..., description="优先级")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class PerformanceReviewRequest(BaseModel):
    """绩效评审请求"""
    user_id: int = Field(..., gt=0, description="用户ID")
    review_period_start: date = Field(..., description="评审周期开始")
    review_period_end: date = Field(..., description="评审周期结束")
    reviewer_comments: str = Field(..., description="评审者评论")
    self_assessment: Optional[str] = Field(None, description="自我评估")
    goals_achievement: Dict[str, Any] = Field(..., description="目标达成情况")
    development_plan: List[Dict[str, Any]] = Field(..., description="发展计划")


class PerformanceReviewResponse(BaseModel):
    """绩效评审响应"""
    id: int = Field(..., description="评审ID")
    user_id: int = Field(..., description="用户ID")
    reviewer_id: int = Field(..., description="评审者ID")
    review_period_start: date = Field(..., description="评审周期开始")
    review_period_end: date = Field(..., description="评审周期结束")
    overall_rating: float = Field(..., description="总体评分")
    reviewer_comments: str = Field(..., description="评审者评论")
    self_assessment: Optional[str] = Field(None, description="自我评估")
    goals_achievement: Dict[str, Any] = Field(..., description="目标达成情况")
    development_plan: List[Dict[str, Any]] = Field(..., description="发展计划")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")


@router.post("/individual/{user_id}/evaluate", response_model=IndividualPerformanceResponse)
async def evaluate_individual_performance(
    user_id: int,
    request: IndividualPerformanceRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    评估个人绩效
    
    Args:
        user_id: 用户ID
        request: 评估请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        个人绩效评估结果
    """
    try:
        performance_service = PerformanceEvaluationService(db)
        performance = await performance_service.evaluate_individual_performance(
            user_id, request.project_id, request.start_date, request.end_date
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
        logger.error(f"评估个人绩效失败: {e}")
        raise HTTPException(status_code=500, detail="评估个人绩效失败")


@router.post("/team/{project_id}/evaluate", response_model=TeamPerformanceResponse)
async def evaluate_team_performance(
    project_id: int,
    request: TeamPerformanceRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    评估团队绩效
    
    Args:
        project_id: 项目ID
        request: 评估请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        团队绩效评估结果
    """
    try:
        performance_service = PerformanceEvaluationService(db)
        performance = await performance_service.evaluate_team_performance(
            project_id, request.start_date, request.end_date
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
        logger.error(f"评估团队绩效失败: {e}")
        raise HTTPException(status_code=500, detail="评估团队绩效失败")


@router.post("/skills/{user_id}/assess", response_model=List[SkillAssessmentResponse])
async def assess_skills(
    user_id: int,
    request: SkillAssessmentRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    评估技能水平
    
    Args:
        user_id: 用户ID
        request: 技能评估请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        技能评估结果列表
    """
    try:
        performance_service = PerformanceEvaluationService(db)
        assessments = await performance_service.assess_skills(user_id, request.skill_categories)
        
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
        logger.error(f"评估技能水平失败: {e}")
        raise HTTPException(status_code=500, detail="评估技能水平失败")


@router.post("/360-feedback", response_model=Feedback360Response)
async def submit_360_feedback(
    request: Feedback360Request,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    提交360度反馈
    
    Args:
        request: 反馈请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        反馈响应
    """
    try:
        # 这里需要实现360度反馈的存储逻辑
        # 暂时返回模拟数据
        feedback = Feedback360Response(
            id=1,
            target_user_id=request.target_user_id,
            feedback_type=request.feedback_type,
            rating=request.rating,
            comments=request.comments,
            anonymous=request.anonymous,
            created_at=datetime.utcnow()
        )
        
        return feedback
    
    except Exception as e:
        logger.error(f"提交360度反馈失败: {e}")
        raise HTTPException(status_code=500, detail="提交360度反馈失败")


@router.get("/360-feedback/{user_id}/summary", response_model=Performance360Summary)
async def get_360_feedback_summary(
    user_id: int,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取360度反馈汇总
    
    Args:
        user_id: 用户ID
        start_date: 开始日期
        end_date: 结束日期
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        360度反馈汇总
    """
    try:
        # 这里需要实现360度反馈汇总的逻辑
        # 暂时返回模拟数据
        summary = Performance360Summary(
            user_id=user_id,
            feedback_count=15,
            avg_rating=4.2,
            feedback_by_type={
                "communication": {"count": 5, "avg_rating": 4.4},
                "technical_skills": {"count": 5, "avg_rating": 4.0},
                "leadership": {"count": 3, "avg_rating": 4.3},
                "teamwork": {"count": 2, "avg_rating": 4.0}
            },
            strengths=["沟通能力强", "技术扎实", "团队合作好"],
            improvement_areas=["时间管理", "创新思维"],
            generated_at=datetime.utcnow()
        )
        
        return summary
    
    except Exception as e:
        logger.error(f"获取360度反馈汇总失败: {e}")
        raise HTTPException(status_code=500, detail="获取360度反馈汇总失败")


@router.post("/goals", response_model=PerformanceGoalResponse)
async def create_performance_goal(
    request: PerformanceGoalRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    创建绩效目标
    
    Args:
        request: 目标请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        绩效目标响应
    """
    try:
        # 这里需要实现绩效目标的创建逻辑
        # 暂时返回模拟数据
        goal = PerformanceGoalResponse(
            id=1,
            user_id=request.user_id,
            goal_title=request.goal_title,
            goal_description=request.goal_description,
            target_value=request.target_value,
            current_value=request.current_value,
            progress_percentage=request.current_value / request.target_value * 100 if request.target_value > 0 else 0,
            deadline=request.deadline,
            priority=request.priority,
            status="ACTIVE",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return goal
    
    except Exception as e:
        logger.error(f"创建绩效目标失败: {e}")
        raise HTTPException(status_code=500, detail="创建绩效目标失败")


@router.get("/goals/{user_id}", response_model=List[PerformanceGoalResponse])
async def get_performance_goals(
    user_id: int,
    status: Optional[str] = Query(None, description="目标状态"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取绩效目标列表
    
    Args:
        user_id: 用户ID
        status: 目标状态
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        绩效目标列表
    """
    try:
        # 这里需要实现获取绩效目标列表的逻辑
        # 暂时返回模拟数据
        goals = [
            PerformanceGoalResponse(
                id=1,
                user_id=user_id,
                goal_title="提升代码质量",
                goal_description="减少代码缺陷率到5%以下",
                target_value=5.0,
                current_value=8.0,
                progress_percentage=60.0,
                deadline=date.today() + timedelta(days=90),
                priority="HIGH",
                status="ACTIVE",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            PerformanceGoalResponse(
                id=2,
                user_id=user_id,
                goal_title="提升团队协作",
                goal_description="团队协作评分达到4.5分以上",
                target_value=4.5,
                current_value=4.0,
                progress_percentage=89.0,
                deadline=date.today() + timedelta(days=60),
                priority="MEDIUM",
                status="ACTIVE",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        if status:
            goals = [goal for goal in goals if goal.status == status]
        
        return goals
    
    except Exception as e:
        logger.error(f"获取绩效目标列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取绩效目标列表失败")


@router.put("/goals/{goal_id}/progress")
async def update_goal_progress(
    goal_id: int,
    current_value: float = Body(..., description="当前值"),
    notes: Optional[str] = Body(None, description="更新说明"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    更新目标进度
    
    Args:
        goal_id: 目标ID
        current_value: 当前值
        notes: 更新说明
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        更新结果
    """
    try:
        # 这里需要实现目标进度更新的逻辑
        return {
            "goal_id": goal_id,
            "current_value": current_value,
            "notes": notes,
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": current_user.id
        }
    
    except Exception as e:
        logger.error(f"更新目标进度失败: {e}")
        raise HTTPException(status_code=500, detail="更新目标进度失败")


@router.post("/reviews", response_model=PerformanceReviewResponse)
async def create_performance_review(
    request: PerformanceReviewRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    创建绩效评审
    
    Args:
        request: 评审请求
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        绩效评审响应
    """
    try:
        # 这里需要实现绩效评审的创建逻辑
        # 暂时返回模拟数据
        review = PerformanceReviewResponse(
            id=1,
            user_id=request.user_id,
            reviewer_id=current_user.id,
            review_period_start=request.review_period_start,
            review_period_end=request.review_period_end,
            overall_rating=4.2,
            reviewer_comments=request.reviewer_comments,
            self_assessment=request.self_assessment,
            goals_achievement=request.goals_achievement,
            development_plan=request.development_plan,
            status="DRAFT",
            created_at=datetime.utcnow()
        )
        
        return review
    
    except Exception as e:
        logger.error(f"创建绩效评审失败: {e}")
        raise HTTPException(status_code=500, detail="创建绩效评审失败")


@router.get("/reviews/{user_id}", response_model=List[PerformanceReviewResponse])
async def get_performance_reviews(
    user_id: int,
    year: Optional[int] = Query(None, description="年份"),
    status: Optional[str] = Query(None, description="状态"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取绩效评审列表
    
    Args:
        user_id: 用户ID
        year: 年份
        status: 状态
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        绩效评审列表
    """
    try:
        # 这里需要实现获取绩效评审列表的逻辑
        # 暂时返回模拟数据
        reviews = [
            PerformanceReviewResponse(
                id=1,
                user_id=user_id,
                reviewer_id=current_user.id,
                review_period_start=date(2024, 1, 1),
                review_period_end=date(2024, 6, 30),
                overall_rating=4.2,
                reviewer_comments="表现优秀，继续保持",
                self_assessment="本期间完成了所有目标",
                goals_achievement={"goal_1": "completed", "goal_2": "in_progress"},
                development_plan=[{"action": "参加技术培训", "timeline": "Q3"}],
                status="COMPLETED",
                created_at=datetime.utcnow()
            )
        ]
        
        if year:
            reviews = [
                review for review in reviews 
                if review.review_period_start.year == year
            ]
        
        if status:
            reviews = [review for review in reviews if review.status == status]
        
        return reviews
    
    except Exception as e:
        logger.error(f"获取绩效评审列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取绩效评审列表失败")


@router.get("/analytics/performance-trends/{user_id}")
async def get_performance_trends(
    user_id: int,
    months: int = Query(12, ge=3, le=36, description="分析月数"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取绩效趋势分析
    
    Args:
        user_id: 用户ID
        months: 分析月数
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        绩效趋势分析结果
    """
    try:
        # 这里需要实现绩效趋势分析的逻辑
        # 暂时返回模拟数据
        trends = {
            "user_id": user_id,
            "analysis_period_months": months,
            "overall_trend": "improving",
            "performance_history": [
                {"month": "2024-01", "score": 3.8},
                {"month": "2024-02", "score": 4.0},
                {"month": "2024-03", "score": 4.1},
                {"month": "2024-04", "score": 4.2},
                {"month": "2024-05", "score": 4.3},
                {"month": "2024-06", "score": 4.2}
            ],
            "key_improvements": [
                "技术能力持续提升",
                "团队协作能力增强",
                "项目交付质量稳定"
            ],
            "areas_for_focus": [
                "时间管理需要改进",
                "创新能力有待加强"
            ],
            "predicted_next_quarter": 4.4,
            "confidence_level": 0.85,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return trends
    
    except Exception as e:
        logger.error(f"获取绩效趋势分析失败: {e}")
        raise HTTPException(status_code=500, detail="获取绩效趋势分析失败")


@router.get("/benchmarks/industry")
async def get_industry_benchmarks(
    role: Optional[str] = Query(None, description="角色"),
    experience_level: Optional[str] = Query(None, description="经验水平"),
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """
    获取行业基准数据
    
    Args:
        role: 角色
        experience_level: 经验水平
        db: 数据库会话
        current_user: 当前用户
        
    Returns:
        行业基准数据
    """
    try:
        # 这里需要实现行业基准数据的获取逻辑
        # 暂时返回模拟数据
        benchmarks = {
            "role": role or "developer",
            "experience_level": experience_level or "mid_level",
            "benchmarks": {
                "task_completion_rate": {"p50": 0.85, "p75": 0.92, "p90": 0.96},
                "on_time_delivery_rate": {"p50": 0.80, "p75": 0.88, "p90": 0.94},
                "quality_score": {"p50": 0.82, "p75": 0.89, "p90": 0.95},
                "collaboration_score": {"p50": 0.78, "p75": 0.85, "p90": 0.92},
                "innovation_score": {"p50": 0.65, "p75": 0.75, "p90": 0.85}
            },
            "sample_size": 1250,
            "data_source": "industry_survey_2024",
            "last_updated": "2024-06-01"
        }
        
        return benchmarks
    
    except Exception as e:
        logger.error(f"获取行业基准数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取行业基准数据失败")