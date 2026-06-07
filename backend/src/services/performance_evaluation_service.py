"""
绩效评估服务

本模块实现团队和个人绩效评估的核心业务逻辑，包括：
- 团队和个人绩效分析
- 360度评估框架
- 技能评估和发展建议
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
from ..models.project import Project, ProjectMember, Task, WorkLog
from ..models.user import User

logger = logging.getLogger(__name__)


@dataclass
class IndividualPerformance:
    """个人绩效数据"""
    user_id: int
    user_name: str
    evaluation_period: Tuple[date, date]
    
    # 工作效率指标
    task_completion_rate: float
    on_time_delivery_rate: float
    work_hour_efficiency: float
    
    # 工作质量指标
    defect_rate: float
    rework_rate: float
    customer_satisfaction: float
    
    # 协作能力指标
    team_collaboration_score: float
    communication_effectiveness: float
    knowledge_sharing_score: float
    
    # 技能成长指标
    skill_improvement_score: float
    learning_activity_score: float
    certification_score: float
    
    # 创新贡献指标
    innovation_contribution_score: float
    process_improvement_score: float
    best_practice_score: float
    
    # 综合评分
    overall_score: float
    performance_level: str  # 'excellent', 'good', 'satisfactory', 'needs_improvement'
    
    # 详细指标
    detailed_metrics: Dict[str, Any]
    
    # 改进建议
    strengths: List[str]
    improvement_areas: List[str]
    development_recommendations: List[str]
    
    # 评估时间
    evaluated_at: datetime


@dataclass
class TeamPerformance:
    """团队绩效数据"""
    project_id: int
    team_members: List[int]
    evaluation_period: Tuple[date, date]
    
    # 团队效率指标
    team_productivity: float
    collaboration_effectiveness: float
    goal_achievement_rate: float
    
    # 团队质量指标
    team_quality_score: float
    customer_satisfaction: float
    delivery_quality: float
    
    # 团队协作指标
    communication_score: float
    conflict_resolution_score: float
    knowledge_sharing_score: float
    
    # 团队发展指标
    skill_diversity_score: float
    learning_culture_score: float
    innovation_score: float
    
    # 综合评分
    overall_score: float
    team_maturity_level: str
    
    # 团队分析
    team_strengths: List[str]
    team_challenges: List[str]
    improvement_recommendations: List[str]
    
    # 个人绩效分布
    performance_distribution: Dict[str, int]
    
    # 评估时间
    evaluated_at: datetime


@dataclass
class SkillAssessment:
    """技能评估数据"""
    user_id: int
    skill_category: str
    current_level: int  # 1-5
    target_level: int
    gap_analysis: Dict[str, Any]
    development_plan: List[Dict[str, Any]]
    assessed_at: datetime


class PerformanceEvaluationService:
    """绩效评估服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def evaluate_individual_performance(self, user_id: int, project_id: Optional[int] = None,
                                            start_date: Optional[date] = None,
                                            end_date: Optional[date] = None) -> IndividualPerformance:
        """
        评估个人绩效
        
        Args:
            user_id: 用户ID
            project_id: 项目ID（可选，如果指定则只评估该项目的绩效）
            start_date: 评估开始日期
            end_date: 评估结束日期
            
        Returns:
            个人绩效评估结果
        """
        # 设置默认评估周期（最近3个月）
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        evaluation_period = (start_date, end_date)
        
        # 获取用户信息
        user = await self._get_user_by_id(user_id)
        
        # 计算工作效率指标
        efficiency_metrics = await self._calculate_individual_efficiency(
            user_id, project_id, start_date, end_date
        )
        
        # 计算工作质量指标
        quality_metrics = await self._calculate_individual_quality(
            user_id, project_id, start_date, end_date
        )
        
        # 计算协作能力指标
        collaboration_metrics = await self._calculate_individual_collaboration(
            user_id, project_id, start_date, end_date
        )
        
        # 计算技能成长指标
        skill_metrics = await self._calculate_individual_skill_growth(
            user_id, start_date, end_date
        )
        
        # 计算创新贡献指标
        innovation_metrics = await self._calculate_individual_innovation(
            user_id, project_id, start_date, end_date
        )
        
        # 计算综合评分
        overall_score = self._calculate_individual_overall_score(
            efficiency_metrics, quality_metrics, collaboration_metrics,
            skill_metrics, innovation_metrics
        )
        
        # 确定绩效等级
        performance_level = self._determine_performance_level(overall_score)
        
        # 生成改进建议
        strengths, improvement_areas, recommendations = self._generate_individual_recommendations(
            efficiency_metrics, quality_metrics, collaboration_metrics,
            skill_metrics, innovation_metrics
        )
        
        return IndividualPerformance(
            user_id=user_id,
            user_name=user.full_name if user else f"User {user_id}",
            evaluation_period=evaluation_period,
            task_completion_rate=efficiency_metrics['task_completion_rate'],
            on_time_delivery_rate=efficiency_metrics['on_time_delivery_rate'],
            work_hour_efficiency=efficiency_metrics['work_hour_efficiency'],
            defect_rate=quality_metrics['defect_rate'],
            rework_rate=quality_metrics['rework_rate'],
            customer_satisfaction=quality_metrics['customer_satisfaction'],
            team_collaboration_score=collaboration_metrics['team_collaboration_score'],
            communication_effectiveness=collaboration_metrics['communication_effectiveness'],
            knowledge_sharing_score=collaboration_metrics['knowledge_sharing_score'],
            skill_improvement_score=skill_metrics['skill_improvement_score'],
            learning_activity_score=skill_metrics['learning_activity_score'],
            certification_score=skill_metrics['certification_score'],
            innovation_contribution_score=innovation_metrics['innovation_contribution_score'],
            process_improvement_score=innovation_metrics['process_improvement_score'],
            best_practice_score=innovation_metrics['best_practice_score'],
            overall_score=overall_score,
            performance_level=performance_level,
            detailed_metrics={
                'efficiency': efficiency_metrics,
                'quality': quality_metrics,
                'collaboration': collaboration_metrics,
                'skill_growth': skill_metrics,
                'innovation': innovation_metrics
            },
            strengths=strengths,
            improvement_areas=improvement_areas,
            development_recommendations=recommendations,
            evaluated_at=datetime.utcnow()
        )
    
    async def evaluate_team_performance(self, project_id: int,
                                      start_date: Optional[date] = None,
                                      end_date: Optional[date] = None) -> TeamPerformance:
        """
        评估团队绩效
        
        Args:
            project_id: 项目ID
            start_date: 评估开始日期
            end_date: 评估结束日期
            
        Returns:
            团队绩效评估结果
        """
        # 设置默认评估周期
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        evaluation_period = (start_date, end_date)
        
        # 获取团队成员
        team_members = await self._get_team_members(project_id)
        member_ids = [member.user_id for member in team_members]
        
        # 计算团队效率指标
        efficiency_metrics = await self._calculate_team_efficiency(
            project_id, member_ids, start_date, end_date
        )
        
        # 计算团队质量指标
        quality_metrics = await self._calculate_team_quality(
            project_id, start_date, end_date
        )
        
        # 计算团队协作指标
        collaboration_metrics = await self._calculate_team_collaboration(
            project_id, member_ids, start_date, end_date
        )
        
        # 计算团队发展指标
        development_metrics = await self._calculate_team_development(
            project_id, member_ids, start_date, end_date
        )
        
        # 计算综合评分
        overall_score = self._calculate_team_overall_score(
            efficiency_metrics, quality_metrics, collaboration_metrics, development_metrics
        )
        
        # 确定团队成熟度等级
        team_maturity_level = self._determine_team_maturity_level(overall_score)
        
        # 获取个人绩效分布
        performance_distribution = await self._get_performance_distribution(
            member_ids, start_date, end_date
        )
        
        # 生成团队改进建议
        strengths, challenges, recommendations = self._generate_team_recommendations(
            efficiency_metrics, quality_metrics, collaboration_metrics, development_metrics
        )
        
        return TeamPerformance(
            project_id=project_id,
            team_members=member_ids,
            evaluation_period=evaluation_period,
            team_productivity=efficiency_metrics['team_productivity'],
            collaboration_effectiveness=efficiency_metrics['collaboration_effectiveness'],
            goal_achievement_rate=efficiency_metrics['goal_achievement_rate'],
            team_quality_score=quality_metrics['team_quality_score'],
            customer_satisfaction=quality_metrics['customer_satisfaction'],
            delivery_quality=quality_metrics['delivery_quality'],
            communication_score=collaboration_metrics['communication_score'],
            conflict_resolution_score=collaboration_metrics['conflict_resolution_score'],
            knowledge_sharing_score=collaboration_metrics['knowledge_sharing_score'],
            skill_diversity_score=development_metrics['skill_diversity_score'],
            learning_culture_score=development_metrics['learning_culture_score'],
            innovation_score=development_metrics['innovation_score'],
            overall_score=overall_score,
            team_maturity_level=team_maturity_level,
            team_strengths=strengths,
            team_challenges=challenges,
            improvement_recommendations=recommendations,
            performance_distribution=performance_distribution,
            evaluated_at=datetime.utcnow()
        )
    
    async def assess_skills(self, user_id: int, skill_categories: List[str]) -> List[SkillAssessment]:
        """
        评估技能水平
        
        Args:
            user_id: 用户ID
            skill_categories: 技能类别列表
            
        Returns:
            技能评估结果列表
        """
        assessments = []
        
        for category in skill_categories:
            # 获取当前技能水平
            current_level = await self._get_current_skill_level(user_id, category)
            
            # 设定目标技能水平
            target_level = await self._get_target_skill_level(user_id, category)
            
            # 进行差距分析
            gap_analysis = await self._analyze_skill_gap(user_id, category, current_level, target_level)
            
            # 制定发展计划
            development_plan = await self._create_skill_development_plan(
                user_id, category, current_level, target_level, gap_analysis
            )
            
            assessments.append(SkillAssessment(
                user_id=user_id,
                skill_category=category,
                current_level=current_level,
                target_level=target_level,
                gap_analysis=gap_analysis,
                development_plan=development_plan,
                assessed_at=datetime.utcnow()
            ))
        
        return assessments
    
    async def _calculate_individual_efficiency(self, user_id: int, project_id: Optional[int],
                                             start_date: date, end_date: date) -> Dict[str, float]:
        """计算个人工作效率指标"""
        # 获取用户任务
        tasks = await self._get_user_tasks(user_id, project_id, start_date, end_date)
        
        if not tasks:
            return {
                'task_completion_rate': 0.0,
                'on_time_delivery_rate': 0.0,
                'work_hour_efficiency': 0.0
            }
        
        # 计算任务完成率
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == 'COMPLETED'])
        task_completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # 计算按时交付率
        on_time_tasks = len([
            t for t in tasks 
            if t.status == 'COMPLETED' and t.actual_end_date and t.planned_end_date 
            and t.actual_end_date <= t.planned_end_date
        ])
        on_time_delivery_rate = on_time_tasks / completed_tasks if completed_tasks > 0 else 0
        
        # 计算工时效率
        work_hour_efficiency = await self._calculate_work_hour_efficiency(
            user_id, project_id, start_date, end_date
        )
        
        return {
            'task_completion_rate': task_completion_rate,
            'on_time_delivery_rate': on_time_delivery_rate,
            'work_hour_efficiency': work_hour_efficiency
        }
    
    async def _calculate_individual_quality(self, user_id: int, project_id: Optional[int],
                                          start_date: date, end_date: date) -> Dict[str, float]:
        """计算个人工作质量指标"""
        # 获取用户相关的缺陷数据
        defect_data = await self._get_user_defect_data(user_id, project_id, start_date, end_date)
        
        # 计算缺陷率
        defect_rate = defect_data.get('defect_rate', 0.0)
        
        # 计算返工率
        rework_rate = defect_data.get('rework_rate', 0.0)
        
        # 计算客户满意度（模拟数据）
        customer_satisfaction = 0.85  # 需要从实际反馈数据获取
        
        return {
            'defect_rate': defect_rate,
            'rework_rate': rework_rate,
            'customer_satisfaction': customer_satisfaction
        }
    
    async def _calculate_individual_collaboration(self, user_id: int, project_id: Optional[int],
                                                start_date: date, end_date: date) -> Dict[str, float]:
        """计算个人协作能力指标"""
        # 团队协作评分（基于项目参与度和角色）
        team_collaboration_score = await self._calculate_team_collaboration_score(
            user_id, project_id, start_date, end_date
        )
        
        # 沟通效果评分（模拟数据）
        communication_effectiveness = 0.8
        
        # 知识分享评分（模拟数据）
        knowledge_sharing_score = 0.75
        
        return {
            'team_collaboration_score': team_collaboration_score,
            'communication_effectiveness': communication_effectiveness,
            'knowledge_sharing_score': knowledge_sharing_score
        }
    
    async def _calculate_individual_skill_growth(self, user_id: int,
                                               start_date: date, end_date: date) -> Dict[str, float]:
        """计算个人技能成长指标"""
        # 技能提升评分（模拟数据）
        skill_improvement_score = 0.7
        
        # 学习活动评分（模拟数据）
        learning_activity_score = 0.6
        
        # 认证评分（模拟数据）
        certification_score = 0.5
        
        return {
            'skill_improvement_score': skill_improvement_score,
            'learning_activity_score': learning_activity_score,
            'certification_score': certification_score
        }
    
    async def _calculate_individual_innovation(self, user_id: int, project_id: Optional[int],
                                             start_date: date, end_date: date) -> Dict[str, float]:
        """计算个人创新贡献指标"""
        # 创新贡献评分（模拟数据）
        innovation_contribution_score = 0.6
        
        # 流程改进评分（模拟数据）
        process_improvement_score = 0.5
        
        # 最佳实践评分（模拟数据）
        best_practice_score = 0.4
        
        return {
            'innovation_contribution_score': innovation_contribution_score,
            'process_improvement_score': process_improvement_score,
            'best_practice_score': best_practice_score
        }
    
    def _calculate_individual_overall_score(self, efficiency_metrics: Dict[str, float],
                                          quality_metrics: Dict[str, float],
                                          collaboration_metrics: Dict[str, float],
                                          skill_metrics: Dict[str, float],
                                          innovation_metrics: Dict[str, float]) -> float:
        """计算个人综合评分"""
        # 权重配置
        weights = {
            'efficiency': 0.30,
            'quality': 0.25,
            'collaboration': 0.20,
            'skill_growth': 0.15,
            'innovation': 0.10
        }
        
        # 计算各维度平均分
        efficiency_avg = sum(efficiency_metrics.values()) / len(efficiency_metrics)
        quality_avg = sum(quality_metrics.values()) / len(quality_metrics)
        collaboration_avg = sum(collaboration_metrics.values()) / len(collaboration_metrics)
        skill_avg = sum(skill_metrics.values()) / len(skill_metrics)
        innovation_avg = sum(innovation_metrics.values()) / len(innovation_metrics)
        
        # 加权计算综合评分
        overall_score = (
            efficiency_avg * weights['efficiency'] +
            quality_avg * weights['quality'] +
            collaboration_avg * weights['collaboration'] +
            skill_avg * weights['skill_growth'] +
            innovation_avg * weights['innovation']
        )
        
        return min(1.0, max(0.0, overall_score))
    
    def _determine_performance_level(self, overall_score: float) -> str:
        """确定绩效等级"""
        if overall_score >= 0.9:
            return 'excellent'
        elif overall_score >= 0.8:
            return 'good'
        elif overall_score >= 0.7:
            return 'satisfactory'
        else:
            return 'needs_improvement'
    
    def _generate_individual_recommendations(self, efficiency_metrics: Dict[str, float],
                                           quality_metrics: Dict[str, float],
                                           collaboration_metrics: Dict[str, float],
                                           skill_metrics: Dict[str, float],
                                           innovation_metrics: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
        """生成个人改进建议"""
        strengths = []
        improvement_areas = []
        recommendations = []
        
        # 分析优势
        if efficiency_metrics['task_completion_rate'] >= 0.9:
            strengths.append("任务完成率优秀")
        if quality_metrics['customer_satisfaction'] >= 0.9:
            strengths.append("客户满意度很高")
        if collaboration_metrics['team_collaboration_score'] >= 0.8:
            strengths.append("团队协作能力强")
        
        # 分析改进领域
        if efficiency_metrics['on_time_delivery_rate'] < 0.7:
            improvement_areas.append("按时交付率需要提升")
            recommendations.append("建议改进时间管理和任务规划能力")
        
        if quality_metrics['defect_rate'] > 0.1:
            improvement_areas.append("代码质量需要改进")
            recommendations.append("建议加强代码审查和测试覆盖")
        
        if skill_metrics['learning_activity_score'] < 0.6:
            improvement_areas.append("学习积极性有待提高")
            recommendations.append("建议制定个人学习计划，参加技能培训")
        
        return strengths, improvement_areas, recommendations
    
    # 辅助方法
    async def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_team_members(self, project_id: int) -> List[ProjectMember]:
        """获取团队成员"""
        query = select(ProjectMember).where(
            and_(ProjectMember.project_id == project_id, ProjectMember.status == 'ACTIVE')
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _get_user_tasks(self, user_id: int, project_id: Optional[int],
                            start_date: date, end_date: date) -> List[Task]:
        """获取用户任务"""
        conditions = [
            Task.assignee_id == user_id,
            Task.created_at >= start_date,
            Task.created_at <= end_date
        ]
        
        if project_id:
            conditions.append(Task.project_id == project_id)
        
        query = select(Task).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _calculate_work_hour_efficiency(self, user_id: int, project_id: Optional[int],
                                            start_date: date, end_date: date) -> float:
        """计算工时效率"""
        # 获取工作日志
        conditions = [
            WorkLog.user_id == user_id,
            WorkLog.work_date >= start_date,
            WorkLog.work_date <= end_date
        ]
        
        if project_id:
            conditions.append(WorkLog.project_id == project_id)
        
        query = select(WorkLog).where(and_(*conditions))
        result = await self.db.execute(query)
        work_logs = result.scalars().all()
        
        if not work_logs:
            return 0.0
        
        # 计算总工时和有效工时
        total_hours = sum(float(log.hours_worked) for log in work_logs)
        productive_hours = sum(
            float(log.hours_worked) for log in work_logs 
            if log.work_type in ['DEVELOPMENT', 'TESTING', 'ANALYSIS', 'DESIGN']
        )
        
        return productive_hours / total_hours if total_hours > 0 else 0.0
    
    async def _get_user_defect_data(self, user_id: int, project_id: Optional[int],
                                  start_date: date, end_date: date) -> Dict[str, float]:
        """获取用户缺陷数据"""
        # 这里需要根据实际的缺陷模型来实现
        # 暂时返回模拟数据
        return {
            'defect_rate': 0.05,  # 5%的缺陷率
            'rework_rate': 0.1    # 10%的返工率
        }
    
    async def _calculate_team_collaboration_score(self, user_id: int, project_id: Optional[int],
                                                start_date: date, end_date: date) -> float:
        """计算团队协作评分"""
        # 基于项目参与度和角色计算协作评分
        if project_id:
            query = select(ProjectMember).where(
                and_(
                    ProjectMember.user_id == user_id,
                    ProjectMember.project_id == project_id,
                    ProjectMember.status == 'ACTIVE'
                )
            )
            result = await self.db.execute(query)
            member = result.scalar_one_or_none()
            
            if member:
                # 基于参与度和角色重要性计算评分
                allocation = float(member.allocation_percentage or 0) / 100
                role_weight = self._get_role_weight(member.role_in_project)
                return min(1.0, allocation * role_weight)
        
        return 0.7  # 默认评分
    
    def _get_role_weight(self, role: str) -> float:
        """获取角色权重"""
        role_weights = {
            'ADMIN': 1.0,
            'PROJECT_MANAGER': 1.0,
            'REQUIREMENT_MANAGER': 0.9,
            'DESIGNER': 0.8,
            'ARCHITECT': 0.9,
            'DEVELOPER': 0.8,
            'TESTER': 0.8,
            'DEVOPS': 0.8,
            'THIRD_PARTY': 0.6
        }
        return role_weights.get(role, 0.7)
    
    # 团队绩效相关方法
    async def _calculate_team_efficiency(self, project_id: int, member_ids: List[int],
                                       start_date: date, end_date: date) -> Dict[str, float]:
        """计算团队效率指标"""
        return {
            'team_productivity': 0.8,
            'collaboration_effectiveness': 0.75,
            'goal_achievement_rate': 0.85
        }
    
    async def _calculate_team_quality(self, project_id: int,
                                    start_date: date, end_date: date) -> Dict[str, float]:
        """计算团队质量指标"""
        return {
            'team_quality_score': 0.8,
            'customer_satisfaction': 0.85,
            'delivery_quality': 0.9
        }
    
    async def _calculate_team_collaboration(self, project_id: int, member_ids: List[int],
                                          start_date: date, end_date: date) -> Dict[str, float]:
        """计算团队协作指标"""
        return {
            'communication_score': 0.8,
            'conflict_resolution_score': 0.75,
            'knowledge_sharing_score': 0.7
        }
    
    async def _calculate_team_development(self, project_id: int, member_ids: List[int],
                                        start_date: date, end_date: date) -> Dict[str, float]:
        """计算团队发展指标"""
        return {
            'skill_diversity_score': 0.8,
            'learning_culture_score': 0.7,
            'innovation_score': 0.6
        }
    
    def _calculate_team_overall_score(self, efficiency_metrics: Dict[str, float],
                                    quality_metrics: Dict[str, float],
                                    collaboration_metrics: Dict[str, float],
                                    development_metrics: Dict[str, float]) -> float:
        """计算团队综合评分"""
        weights = {
            'efficiency': 0.3,
            'quality': 0.3,
            'collaboration': 0.25,
            'development': 0.15
        }
        
        efficiency_avg = sum(efficiency_metrics.values()) / len(efficiency_metrics)
        quality_avg = sum(quality_metrics.values()) / len(quality_metrics)
        collaboration_avg = sum(collaboration_metrics.values()) / len(collaboration_metrics)
        development_avg = sum(development_metrics.values()) / len(development_metrics)
        
        overall_score = (
            efficiency_avg * weights['efficiency'] +
            quality_avg * weights['quality'] +
            collaboration_avg * weights['collaboration'] +
            development_avg * weights['development']
        )
        
        return min(1.0, max(0.0, overall_score))
    
    def _determine_team_maturity_level(self, overall_score: float) -> str:
        """确定团队成熟度等级"""
        if overall_score >= 0.9:
            return 'high_performing'
        elif overall_score >= 0.8:
            return 'performing'
        elif overall_score >= 0.7:
            return 'forming'
        else:
            return 'storming'
    
    async def _get_performance_distribution(self, member_ids: List[int],
                                          start_date: date, end_date: date) -> Dict[str, int]:
        """获取绩效分布"""
        # 模拟绩效分布数据
        return {
            'excellent': 2,
            'good': 5,
            'satisfactory': 3,
            'needs_improvement': 1
        }
    
    def _generate_team_recommendations(self, efficiency_metrics: Dict[str, float],
                                     quality_metrics: Dict[str, float],
                                     collaboration_metrics: Dict[str, float],
                                     development_metrics: Dict[str, float]) -> Tuple[List[str], List[str], List[str]]:
        """生成团队改进建议"""
        strengths = ["团队协作良好", "交付质量稳定"]
        challenges = ["沟通效率有待提升", "创新能力需要加强"]
        recommendations = [
            "建议定期举行团队建设活动",
            "加强技能培训和知识分享",
            "建立创新激励机制"
        ]
        
        return strengths, challenges, recommendations
    
    # 技能评估相关方法
    async def _get_current_skill_level(self, user_id: int, skill_category: str) -> int:
        """获取当前技能水平"""
        # 这里需要根据实际的技能评估数据来实现
        return 3  # 默认中级水平
    
    async def _get_target_skill_level(self, user_id: int, skill_category: str) -> int:
        """获取目标技能水平"""
        # 这里需要根据职业发展规划来确定
        return 4  # 默认目标为高级水平
    
    async def _analyze_skill_gap(self, user_id: int, skill_category: str,
                               current_level: int, target_level: int) -> Dict[str, Any]:
        """分析技能差距"""
        gap = target_level - current_level
        
        return {
            'gap_level': gap,
            'gap_description': f"需要提升 {gap} 个等级",
            'estimated_time_months': gap * 3,  # 每个等级需要3个月
            'priority': 'high' if gap >= 2 else 'medium' if gap == 1 else 'low'
        }
    
    async def _create_skill_development_plan(self, user_id: int, skill_category: str,
                                           current_level: int, target_level: int,
                                           gap_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建技能发展计划"""
        plan = []
        
        if gap_analysis['gap_level'] > 0:
            plan.append({
                'action': f"参加{skill_category}相关培训",
                'timeline': "1-2个月",
                'resources': ["在线课程", "技术书籍", "实践项目"],
                'success_criteria': "完成培训并通过考核"
            })
            
            plan.append({
                'action': f"在项目中实践{skill_category}技能",
                'timeline': "3-6个月",
                'resources': ["导师指导", "项目实践机会"],
                'success_criteria': "成功应用技能解决实际问题"
            })
        
        return plan