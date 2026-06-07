"""
绩效管理服务

本模块实现绩效管理的扩展功能，包括：
- 绩效目标管理
- 360度反馈系统
- 绩效评审流程
- 发展计划管理
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError
from ..models.user import User

logger = logging.getLogger(__name__)


@dataclass
class PerformanceGoal:
    """绩效目标"""
    id: Optional[int]
    user_id: int
    goal_title: str
    goal_description: str
    target_value: float
    current_value: float
    progress_percentage: float
    deadline: date
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Feedback360:
    """360度反馈"""
    id: Optional[int]
    target_user_id: int
    feedback_provider_id: int
    feedback_type: str
    rating: int
    comments: Optional[str]
    anonymous: bool
    created_at: datetime


@dataclass
class PerformanceReview:
    """绩效评审"""
    id: Optional[int]
    user_id: int
    reviewer_id: int
    review_period_start: date
    review_period_end: date
    overall_rating: float
    reviewer_comments: str
    self_assessment: Optional[str]
    goals_achievement: Dict[str, Any]
    development_plan: List[Dict[str, Any]]
    status: str
    created_at: datetime


@dataclass
class DevelopmentPlan:
    """发展计划"""
    id: Optional[int]
    user_id: int
    plan_title: str
    plan_description: str
    objectives: List[Dict[str, Any]]
    timeline: Dict[str, Any]
    resources_needed: List[str]
    success_metrics: List[str]
    status: str
    created_at: datetime
    updated_at: datetime


class PerformanceManagementService:
    """绩效管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # 绩效目标管理
    async def create_performance_goal(self, user_id: int, goal_title: str, 
                                    goal_description: str, target_value: float,
                                    deadline: date, priority: str = "MEDIUM") -> PerformanceGoal:
        """
        创建绩效目标
        
        Args:
            user_id: 用户ID
            goal_title: 目标标题
            goal_description: 目标描述
            target_value: 目标值
            deadline: 截止日期
            priority: 优先级
            
        Returns:
            创建的绩效目标
        """
        # 验证用户存在
        await self._validate_user_exists(user_id)
        
        # 验证截止日期
        if deadline <= date.today():
            raise ValidationError("截止日期必须是未来日期")
        
        # 创建目标对象
        goal = PerformanceGoal(
            id=None,
            user_id=user_id,
            goal_title=goal_title,
            goal_description=goal_description,
            target_value=target_value,
            current_value=0.0,
            progress_percentage=0.0,
            deadline=deadline,
            priority=priority,
            status="ACTIVE",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 这里需要实现数据库保存逻辑
        # 暂时返回模拟的ID
        goal.id = 1
        
        logger.info(f"创建绩效目标成功: 用户{user_id}, 目标{goal_title}")
        return goal
    
    async def update_goal_progress(self, goal_id: int, current_value: float, 
                                 notes: Optional[str] = None) -> PerformanceGoal:
        """
        更新目标进度
        
        Args:
            goal_id: 目标ID
            current_value: 当前值
            notes: 更新说明
            
        Returns:
            更新后的目标
        """
        # 获取目标
        goal = await self._get_goal_by_id(goal_id)
        
        # 更新进度
        goal.current_value = current_value
        goal.progress_percentage = (current_value / goal.target_value * 100) if goal.target_value > 0 else 0
        goal.updated_at = datetime.utcnow()
        
        # 检查是否完成
        if goal.progress_percentage >= 100:
            goal.status = "COMPLETED"
        elif goal.deadline < date.today() and goal.status == "ACTIVE":
            goal.status = "OVERDUE"
        
        # 这里需要实现数据库更新逻辑
        
        logger.info(f"更新目标进度成功: 目标{goal_id}, 进度{goal.progress_percentage}%")
        return goal
    
    async def get_user_goals(self, user_id: int, status: Optional[str] = None) -> List[PerformanceGoal]:
        """
        获取用户目标列表
        
        Args:
            user_id: 用户ID
            status: 目标状态过滤
            
        Returns:
            目标列表
        """
        # 这里需要实现数据库查询逻辑
        # 暂时返回模拟数据
        goals = [
            PerformanceGoal(
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
            PerformanceGoal(
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
    
    # 360度反馈管理
    async def submit_360_feedback(self, target_user_id: int, feedback_provider_id: int,
                                feedback_type: str, rating: int, comments: Optional[str] = None,
                                anonymous: bool = False) -> Feedback360:
        """
        提交360度反馈
        
        Args:
            target_user_id: 被评估用户ID
            feedback_provider_id: 反馈提供者ID
            feedback_type: 反馈类型
            rating: 评分
            comments: 评论
            anonymous: 是否匿名
            
        Returns:
            反馈记录
        """
        # 验证用户存在
        await self._validate_user_exists(target_user_id)
        await self._validate_user_exists(feedback_provider_id)
        
        # 验证评分范围
        if not 1 <= rating <= 5:
            raise ValidationError("评分必须在1-5之间")
        
        # 验证反馈类型
        valid_types = ["communication", "technical_skills", "leadership", "teamwork", "problem_solving"]
        if feedback_type not in valid_types:
            raise ValidationError(f"无效的反馈类型: {feedback_type}")
        
        # 创建反馈记录
        feedback = Feedback360(
            id=None,
            target_user_id=target_user_id,
            feedback_provider_id=feedback_provider_id,
            feedback_type=feedback_type,
            rating=rating,
            comments=comments,
            anonymous=anonymous,
            created_at=datetime.utcnow()
        )
        
        # 这里需要实现数据库保存逻辑
        feedback.id = 1
        
        logger.info(f"提交360度反馈成功: 目标用户{target_user_id}, 类型{feedback_type}")
        return feedback
    
    async def get_360_feedback_summary(self, user_id: int, start_date: Optional[date] = None,
                                     end_date: Optional[date] = None) -> Dict[str, Any]:
        """
        获取360度反馈汇总
        
        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            反馈汇总数据
        """
        # 设置默认日期范围
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        # 这里需要实现数据库查询逻辑
        # 暂时返回模拟数据
        feedback_data = [
            {"type": "communication", "rating": 4.4, "count": 5},
            {"type": "technical_skills", "rating": 4.0, "count": 5},
            {"type": "leadership", "rating": 4.3, "count": 3},
            {"type": "teamwork", "rating": 4.0, "count": 2}
        ]
        
        total_feedback = sum(item["count"] for item in feedback_data)
        avg_rating = sum(item["rating"] * item["count"] for item in feedback_data) / total_feedback if total_feedback > 0 else 0
        
        # 分析优势和改进领域
        strengths = []
        improvement_areas = []
        
        for item in feedback_data:
            if item["rating"] >= 4.2:
                strengths.append(f"{item['type']}表现优秀")
            elif item["rating"] < 3.8:
                improvement_areas.append(f"{item['type']}需要改进")
        
        feedback_by_type = {
            item["type"]: {
                "count": item["count"],
                "avg_rating": item["rating"]
            }
            for item in feedback_data
        }
        
        return {
            "user_id": user_id,
            "feedback_count": total_feedback,
            "avg_rating": avg_rating,
            "feedback_by_type": feedback_by_type,
            "strengths": strengths,
            "improvement_areas": improvement_areas,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "generated_at": datetime.utcnow()
        }
    
    # 绩效评审管理
    async def create_performance_review(self, user_id: int, reviewer_id: int,
                                      review_period_start: date, review_period_end: date,
                                      reviewer_comments: str, self_assessment: Optional[str] = None,
                                      goals_achievement: Optional[Dict[str, Any]] = None,
                                      development_plan: Optional[List[Dict[str, Any]]] = None) -> PerformanceReview:
        """
        创建绩效评审
        
        Args:
            user_id: 被评审用户ID
            reviewer_id: 评审者ID
            review_period_start: 评审周期开始
            review_period_end: 评审周期结束
            reviewer_comments: 评审者评论
            self_assessment: 自我评估
            goals_achievement: 目标达成情况
            development_plan: 发展计划
            
        Returns:
            绩效评审记录
        """
        # 验证用户存在
        await self._validate_user_exists(user_id)
        await self._validate_user_exists(reviewer_id)
        
        # 验证评审周期
        if review_period_start >= review_period_end:
            raise ValidationError("评审周期开始日期必须早于结束日期")
        
        # 计算综合评分（基于目标达成情况和360度反馈）
        overall_rating = await self._calculate_overall_rating(
            user_id, review_period_start, review_period_end, goals_achievement
        )
        
        # 创建评审记录
        review = PerformanceReview(
            id=None,
            user_id=user_id,
            reviewer_id=reviewer_id,
            review_period_start=review_period_start,
            review_period_end=review_period_end,
            overall_rating=overall_rating,
            reviewer_comments=reviewer_comments,
            self_assessment=self_assessment,
            goals_achievement=goals_achievement or {},
            development_plan=development_plan or [],
            status="DRAFT",
            created_at=datetime.utcnow()
        )
        
        # 这里需要实现数据库保存逻辑
        review.id = 1
        
        logger.info(f"创建绩效评审成功: 用户{user_id}, 评审者{reviewer_id}")
        return review
    
    async def get_performance_reviews(self, user_id: int, year: Optional[int] = None,
                                    status: Optional[str] = None) -> List[PerformanceReview]:
        """
        获取绩效评审列表
        
        Args:
            user_id: 用户ID
            year: 年份过滤
            status: 状态过滤
            
        Returns:
            评审列表
        """
        # 这里需要实现数据库查询逻辑
        # 暂时返回模拟数据
        reviews = [
            PerformanceReview(
                id=1,
                user_id=user_id,
                reviewer_id=2,
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
            reviews = [review for review in reviews if review.review_period_start.year == year]
        
        if status:
            reviews = [review for review in reviews if review.status == status]
        
        return reviews
    
    # 发展计划管理
    async def create_development_plan(self, user_id: int, plan_title: str,
                                    plan_description: str, objectives: List[Dict[str, Any]],
                                    timeline: Dict[str, Any], resources_needed: List[str],
                                    success_metrics: List[str]) -> DevelopmentPlan:
        """
        创建发展计划
        
        Args:
            user_id: 用户ID
            plan_title: 计划标题
            plan_description: 计划描述
            objectives: 目标列表
            timeline: 时间线
            resources_needed: 所需资源
            success_metrics: 成功指标
            
        Returns:
            发展计划
        """
        # 验证用户存在
        await self._validate_user_exists(user_id)
        
        # 创建发展计划
        plan = DevelopmentPlan(
            id=None,
            user_id=user_id,
            plan_title=plan_title,
            plan_description=plan_description,
            objectives=objectives,
            timeline=timeline,
            resources_needed=resources_needed,
            success_metrics=success_metrics,
            status="ACTIVE",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # 这里需要实现数据库保存逻辑
        plan.id = 1
        
        logger.info(f"创建发展计划成功: 用户{user_id}, 计划{plan_title}")
        return plan
    
    # 绩效趋势分析
    async def analyze_performance_trends(self, user_id: int, months: int = 12) -> Dict[str, Any]:
        """
        分析绩效趋势
        
        Args:
            user_id: 用户ID
            months: 分析月数
            
        Returns:
            趋势分析结果
        """
        # 这里需要实现绩效趋势分析逻辑
        # 暂时返回模拟数据
        
        # 生成历史绩效数据
        performance_history = []
        base_score = 3.8
        for i in range(months):
            month_date = date.today().replace(day=1) - timedelta(days=30 * (months - i - 1))
            # 模拟绩效提升趋势
            score = base_score + (i * 0.05) + (0.1 * (i % 3 - 1))  # 添加一些波动
            score = min(5.0, max(1.0, score))  # 限制在1-5范围内
            
            performance_history.append({
                "month": month_date.strftime("%Y-%m"),
                "score": round(score, 1)
            })
        
        # 分析趋势
        scores = [item["score"] for item in performance_history]
        trend = "improving" if scores[-1] > scores[0] else "declining" if scores[-1] < scores[0] else "stable"
        
        # 预测下一季度
        recent_scores = scores[-3:]  # 最近3个月
        predicted_score = sum(recent_scores) / len(recent_scores) + 0.1  # 假设持续改进
        predicted_score = min(5.0, max(1.0, predicted_score))
        
        return {
            "user_id": user_id,
            "analysis_period_months": months,
            "overall_trend": trend,
            "performance_history": performance_history,
            "key_improvements": [
                "技术能力持续提升",
                "团队协作能力增强",
                "项目交付质量稳定"
            ],
            "areas_for_focus": [
                "时间管理需要改进",
                "创新能力有待加强"
            ],
            "predicted_next_quarter": round(predicted_score, 1),
            "confidence_level": 0.85,
            "generated_at": datetime.utcnow()
        }
    
    # 行业基准对比
    async def get_industry_benchmarks(self, role: Optional[str] = None,
                                    experience_level: Optional[str] = None) -> Dict[str, Any]:
        """
        获取行业基准数据
        
        Args:
            role: 角色
            experience_level: 经验水平
            
        Returns:
            行业基准数据
        """
        # 这里需要实现行业基准数据获取逻辑
        # 暂时返回模拟数据
        
        # 根据角色和经验调整基准值
        base_benchmarks = {
            "task_completion_rate": {"p50": 0.85, "p75": 0.92, "p90": 0.96},
            "on_time_delivery_rate": {"p50": 0.80, "p75": 0.88, "p90": 0.94},
            "quality_score": {"p50": 0.82, "p75": 0.89, "p90": 0.95},
            "collaboration_score": {"p50": 0.78, "p75": 0.85, "p90": 0.92},
            "innovation_score": {"p50": 0.65, "p75": 0.75, "p90": 0.85}
        }
        
        # 根据经验水平调整
        if experience_level == "senior":
            for metric in base_benchmarks:
                for percentile in base_benchmarks[metric]:
                    base_benchmarks[metric][percentile] += 0.05
        elif experience_level == "junior":
            for metric in base_benchmarks:
                for percentile in base_benchmarks[metric]:
                    base_benchmarks[metric][percentile] -= 0.05
        
        return {
            "role": role or "developer",
            "experience_level": experience_level or "mid_level",
            "benchmarks": base_benchmarks,
            "sample_size": 1250,
            "data_source": "industry_survey_2024",
            "last_updated": "2024-06-01"
        }
    
    # 辅助方法
    async def _validate_user_exists(self, user_id: int):
        """验证用户是否存在"""
        # 这里需要实现用户存在性验证
        # 暂时跳过验证
        pass
    
    async def _get_goal_by_id(self, goal_id: int) -> PerformanceGoal:
        """根据ID获取目标"""
        # 这里需要实现数据库查询逻辑
        # 暂时返回模拟数据
        return PerformanceGoal(
            id=goal_id,
            user_id=1,
            goal_title="测试目标",
            goal_description="测试目标描述",
            target_value=100.0,
            current_value=50.0,
            progress_percentage=50.0,
            deadline=date.today() + timedelta(days=30),
            priority="MEDIUM",
            status="ACTIVE",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    async def _calculate_overall_rating(self, user_id: int, start_date: date,
                                      end_date: date, goals_achievement: Optional[Dict[str, Any]]) -> float:
        """计算综合评分"""
        # 基础评分
        base_rating = 4.0
        
        # 根据目标达成情况调整
        if goals_achievement:
            completed_goals = sum(1 for status in goals_achievement.values() if status == "completed")
            total_goals = len(goals_achievement)
            if total_goals > 0:
                achievement_rate = completed_goals / total_goals
                base_rating += (achievement_rate - 0.8) * 2  # 80%为基准
        
        # 获取360度反馈评分
        feedback_summary = await self.get_360_feedback_summary(user_id, start_date, end_date)
        if feedback_summary["feedback_count"] > 0:
            feedback_rating = feedback_summary["avg_rating"]
            base_rating = (base_rating + feedback_rating) / 2
        
        return min(5.0, max(1.0, base_rating))
    
    # 智能推荐系统
    async def recommend_development_actions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        推荐发展行动
        
        Args:
            user_id: 用户ID
            
        Returns:
            推荐行动列表
        """
        # 获取用户当前绩效数据
        feedback_summary = await self.get_360_feedback_summary(user_id)
        goals = await self.get_user_goals(user_id, status="ACTIVE")
        
        recommendations = []
        
        # 基于360度反馈推荐
        for feedback_type, data in feedback_summary["feedback_by_type"].items():
            if data["avg_rating"] < 3.5:
                recommendations.append({
                    "type": "skill_improvement",
                    "area": feedback_type,
                    "priority": "high",
                    "action": f"参加{feedback_type}相关培训",
                    "timeline": "1-2个月",
                    "expected_impact": "提升该领域评分0.5-1.0分"
                })
        
        # 基于目标进度推荐
        for goal in goals:
            if goal.progress_percentage < 50 and goal.deadline - date.today() < timedelta(days=30):
                recommendations.append({
                    "type": "goal_acceleration",
                    "area": goal.goal_title,
                    "priority": "urgent",
                    "action": f"加速推进{goal.goal_title}",
                    "timeline": "立即",
                    "expected_impact": "确保目标按时完成"
                })
        
        # 通用发展建议
        recommendations.extend([
            {
                "type": "continuous_learning",
                "area": "技术技能",
                "priority": "medium",
                "action": "参加在线技术课程",
                "timeline": "持续进行",
                "expected_impact": "保持技术竞争力"
            },
            {
                "type": "networking",
                "area": "职业发展",
                "priority": "low",
                "action": "参加行业会议和技术交流",
                "timeline": "季度性",
                "expected_impact": "扩展职业网络"
            }
        ])
        
        # 按优先级排序
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))
        
        return recommendations[:10]  # 返回前10个推荐