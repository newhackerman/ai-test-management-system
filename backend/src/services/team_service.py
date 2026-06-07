"""
团队管理服务

本模块提供团队管理相关的业务逻辑，包括：
- 团队成员管理
- 工作负载分析
- 技能匹配推荐
- 团队统计分析
"""
import logging
import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload, joinedload

from ..models.project import ProjectMember, Project
from ..models.user import User
from ..schemas.team import (
    AddMemberRequest, UpdateMemberRequest, InviteMemberRequest,
    MemberQueryParams, ProjectMemberResponse, MemberWorkload,
    TeamWorkloadAnalysis, MemberRecommendation, SkillMatchRequest,
    TeamStatistics, UserInfo, ProjectMemberRole
)
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..services.user import UserService
from ..services.permission import PermissionService

logger = logging.getLogger(__name__)


class TeamService:
    """团队管理服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = UserService(db)
        self.permission_service = PermissionService(db)
    
    async def add_team_member(
        self, 
        project_id: int, 
        request: AddMemberRequest, 
        current_user_id: int
    ) -> ProjectMember:
        """添加团队成员"""
        try:
            # 1. 验证项目存在
            project = await self._get_project_by_id(project_id)
            if not project:
                raise NotFoundError(f"项目 {project_id} 不存在")
            
            # 2. 验证权限
            await self._check_team_management_permission(project_id, current_user_id)
            
            # 3. 验证用户存在
            user = await self._get_user_by_id(request.user_id)
            if not user:
                raise ValidationError(f"用户 {request.user_id} 不存在")
            
            # 4. 检查是否已是团队成员
            existing_member = await self._get_project_member(project_id, request.user_id)
            if existing_member:
                raise ValidationError("用户已是项目成员")
            
            # 5. 验证角色权限
            await self._validate_role_assignment(request.role_in_project, request.user_id)
            
            # 6. 创建成员关系
            member = ProjectMember(
                project_id=project_id,
                user_id=request.user_id,
                role_in_project=request.role_in_project.value,
                allocation_percentage=request.allocation_percentage,
                hourly_rate=request.hourly_rate,
                join_date=request.join_date,
                status="ACTIVE",
                skills=request.skills,
                responsibilities=request.responsibilities,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(member)
            await self.db.commit()
            await self.db.refresh(member)
            
            # 7. 发送欢迎通知
            await self._send_welcome_notification(member, user)
            
            logger.info(f"用户 {request.user_id} 已添加到项目 {project_id}")
            return member
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"添加团队成员失败: {e}")
            raise
    
    async def get_team_members(
        self, 
        project_id: int, 
        params: MemberQueryParams, 
        current_user_id: int
    ) -> Tuple[List[ProjectMember], int]:
        """获取团队成员列表"""
        try:
            # 1. 验证项目存在和权限
            await self._check_project_access_permission(project_id, current_user_id)
            
            # 2. 构建查询
            query = select(ProjectMember).where(ProjectMember.project_id == project_id)
            
            # 3. 添加过滤条件
            if params.role:
                query = query.where(ProjectMember.role_in_project.in_([r.value for r in params.role]))
            
            if params.status:
                query = query.where(ProjectMember.status.in_([s.value for s in params.status]))
            
            if params.skills:
                # 技能过滤 - 检查是否包含任一技能
                skill_conditions = []
                for skill in params.skills:
                    skill_conditions.append(ProjectMember.skills.contains([skill]))
                if skill_conditions:
                    query = query.where(or_(*skill_conditions))
            
            # 4. 添加搜索条件
            if params.search:
                # 需要关联用户表进行搜索
                query = query.join(User, ProjectMember.user_id == User.id)
                search_pattern = f"%{params.search}%"
                query = query.where(
                    or_(
                        User.username.ilike(search_pattern),
                        User.email.ilike(search_pattern),
                        User.nickname.ilike(search_pattern),
                        ProjectMember.responsibilities.ilike(search_pattern)
                    )
                )
            
            # 5. 获取总数
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # 6. 添加排序
            sort_column = getattr(ProjectMember, params.sort_by, ProjectMember.join_date)
            if params.sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
            
            # 7. 添加分页
            offset = (params.page - 1) * params.size
            query = query.offset(offset).limit(params.size)
            
            # 8. 执行查询并加载用户信息
            query = query.options(selectinload(ProjectMember.project))
            result = await self.db.execute(query)
            members = result.scalars().all()
            
            return members, total
            
        except Exception as e:
            logger.error(f"获取团队成员列表失败: {e}")
            raise
    
    async def update_team_member(
        self, 
        project_id: int, 
        member_id: int, 
        request: UpdateMemberRequest, 
        current_user_id: int
    ) -> ProjectMember:
        """更新团队成员信息"""
        try:
            # 1. 验证权限
            await self._check_team_management_permission(project_id, current_user_id)
            
            # 2. 获取成员信息
            member = await self._get_project_member_by_id(member_id)
            if not member or member.project_id != project_id:
                raise NotFoundError(f"成员 {member_id} 不存在")
            
            # 3. 验证角色变更权限
            if request.role_in_project and request.role_in_project != member.role_in_project:
                await self._validate_role_assignment(request.role_in_project, member.user_id)
            
            # 4. 更新字段
            update_data = {}
            if request.role_in_project is not None:
                update_data['role_in_project'] = request.role_in_project.value
            if request.allocation_percentage is not None:
                update_data['allocation_percentage'] = request.allocation_percentage
            if request.hourly_rate is not None:
                update_data['hourly_rate'] = request.hourly_rate
            if request.leave_date is not None:
                update_data['leave_date'] = request.leave_date
                # 如果设置了离开日期，自动设置状态为INACTIVE
                if request.leave_date <= date.today():
                    update_data['status'] = "INACTIVE"
            if request.status is not None:
                update_data['status'] = request.status.value
            if request.skills is not None:
                update_data['skills'] = request.skills
            if request.responsibilities is not None:
                update_data['responsibilities'] = request.responsibilities
            
            if update_data:
                update_data['updated_at'] = datetime.utcnow()
                
                stmt = update(ProjectMember).where(
                    ProjectMember.id == member_id
                ).values(**update_data)
                
                await self.db.execute(stmt)
                await self.db.commit()
                
                # 重新获取更新后的数据
                member = await self._get_project_member_by_id(member_id)
            
            logger.info(f"团队成员 {member_id} 信息已更新")
            return member
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新团队成员失败: {e}")
            raise
    
    async def remove_team_member(
        self, 
        project_id: int, 
        member_id: int, 
        current_user_id: int
    ) -> bool:
        """移除团队成员"""
        try:
            # 1. 验证权限
            await self._check_team_management_permission(project_id, current_user_id)
            
            # 2. 获取成员信息
            member = await self._get_project_member_by_id(member_id)
            if not member or member.project_id != project_id:
                raise NotFoundError(f"成员 {member_id} 不存在")
            
            # 3. 检查是否可以移除（项目经理等关键角色可能需要特殊处理）
            await self._validate_member_removal(member, project_id)
            
            # 4. 软删除或硬删除
            # 这里使用硬删除，如果需要保留历史记录可以改为软删除
            stmt = delete(ProjectMember).where(ProjectMember.id == member_id)
            await self.db.execute(stmt)
            await self.db.commit()
            
            # 5. 发送移除通知
            await self._send_removal_notification(member)
            
            logger.info(f"团队成员 {member_id} 已从项目 {project_id} 移除")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"移除团队成员失败: {e}")
            raise
    
    async def invite_member_by_email(
        self, 
        project_id: int, 
        request: InviteMemberRequest, 
        current_user_id: int
    ) -> Dict[str, Any]:
        """通过邮箱邀请成员"""
        try:
            # 1. 验证权限
            await self._check_team_management_permission(project_id, current_user_id)
            
            # 2. 检查邮箱是否已注册
            user = await self._get_user_by_email(request.email)
            if user:
                # 如果用户已存在，直接添加到项目
                add_request = AddMemberRequest(
                    user_id=user.id,
                    role_in_project=request.role_in_project,
                    allocation_percentage=request.allocation_percentage,
                    hourly_rate=request.hourly_rate,
                    join_date=date.today(),
                    skills=request.skills,
                    responsibilities=request.responsibilities
                )
                member = await self.add_team_member(project_id, add_request, current_user_id)
                return {
                    "invitation_id": str(uuid.uuid4()),
                    "invited_email": request.email,
                    "user_exists": True,
                    "member_added": True,
                    "member_id": member.id,
                    "expires_at": datetime.utcnow() + timedelta(days=7)
                }
            else:
                # 如果用户不存在，创建邀请记录
                invitation_id = str(uuid.uuid4())
                expires_at = datetime.utcnow() + timedelta(days=7)
                
                # 这里应该创建邀请记录表，暂时返回邀请信息
                # TODO: 实现邀请记录表和邮件发送功能
                
                await self._send_invitation_email(
                    request.email, 
                    project_id, 
                    invitation_id, 
                    request.invitation_message,
                    expires_at
                )
                
                return {
                    "invitation_id": invitation_id,
                    "invited_email": request.email,
                    "user_exists": False,
                    "member_added": False,
                    "expires_at": expires_at
                }
                
        except Exception as e:
            logger.error(f"邀请成员失败: {e}")
            raise
    
    async def get_team_workload_analysis(
        self, 
        project_id: int, 
        current_user_id: int
    ) -> TeamWorkloadAnalysis:
        """获取团队工作负载分析"""
        try:
            # 1. 验证权限
            await self._check_project_access_permission(project_id, current_user_id)
            
            # 2. 获取团队成员
            query = select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.status == "ACTIVE"
                )
            ).options(selectinload(ProjectMember.project))
            
            result = await self.db.execute(query)
            members = result.scalars().all()
            
            # 3. 计算每个成员的工作负载
            member_workloads = []
            total_capacity = Decimal('0')
            total_workload = Decimal('0')
            
            for member in members:
                workload = await self._calculate_member_workload(member)
                member_workloads.append(workload)
                total_capacity += workload.capacity
                total_workload += workload.current_workload
            
            # 4. 计算团队整体指标
            utilization_rate = (total_workload / total_capacity) if total_capacity > 0 else Decimal('0')
            
            # 5. 识别负载不均衡的成员
            overloaded_members = [m for m in member_workloads if m.overloaded]
            underloaded_members = [m for m in member_workloads if m.utilization_rate < Decimal('0.6')]
            
            # 6. 生成建议
            recommendations = self._generate_workload_recommendations(
                member_workloads, overloaded_members, underloaded_members
            )
            
            return TeamWorkloadAnalysis(
                project_id=project_id,
                total_members=len(members),
                total_capacity=total_capacity,
                total_workload=total_workload,
                utilization_rate=utilization_rate,
                member_workloads=member_workloads,
                overloaded_members=overloaded_members,
                underloaded_members=underloaded_members,
                recommendations=recommendations,
                analyzed_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"获取团队工作负载分析失败: {e}")
            raise
    
    async def recommend_team_members(
        self, 
        project_id: int, 
        request: SkillMatchRequest, 
        current_user_id: int
    ) -> List[MemberRecommendation]:
        """推荐团队成员"""
        try:
            # 1. 验证权限
            await self._check_project_access_permission(project_id, current_user_id)
            
            # 2. 获取候选用户
            candidates_query = select(User).where(User.status == "ACTIVE")
            
            if not request.include_current_members:
                # 排除当前项目成员
                current_members_query = select(ProjectMember.user_id).where(
                    ProjectMember.project_id == project_id
                )
                current_member_ids = await self.db.execute(current_members_query)
                current_member_ids = [row[0] for row in current_member_ids.fetchall()]
                
                if current_member_ids:
                    candidates_query = candidates_query.where(
                        User.id.notin_(current_member_ids)
                    )
            
            candidates_result = await self.db.execute(candidates_query)
            candidates = candidates_result.scalars().all()
            
            # 3. 计算每个候选人的匹配度
            recommendations = []
            for candidate in candidates:
                recommendation = await self._calculate_member_recommendation(
                    candidate, request.skill_requirements, project_id
                )
                
                if recommendation.overall_score >= request.min_score_threshold:
                    recommendations.append(recommendation)
            
            # 4. 按评分排序并限制数量
            recommendations.sort(key=lambda x: x.overall_score, reverse=True)
            recommendations = recommendations[:request.max_recommendations]
            
            return recommendations
            
        except Exception as e:
            logger.error(f"推荐团队成员失败: {e}")
            raise
    
    async def get_team_statistics(
        self, 
        project_id: int, 
        current_user_id: int
    ) -> TeamStatistics:
        """获取团队统计信息"""
        try:
            # 1. 验证权限
            await self._check_project_access_permission(project_id, current_user_id)
            
            # 2. 获取团队成员
            query = select(ProjectMember).where(ProjectMember.project_id == project_id)
            result = await self.db.execute(query)
            members = result.scalars().all()
            
            # 3. 计算基础统计
            total_members = len(members)
            active_members = len([m for m in members if m.status == "ACTIVE"])
            
            # 4. 按角色统计
            members_by_role = {}
            for member in members:
                role = member.role_in_project
                members_by_role[role] = members_by_role.get(role, 0) + 1
            
            # 5. 按状态统计
            members_by_status = {}
            for member in members:
                status = member.status
                members_by_status[status] = members_by_status.get(status, 0) + 1
            
            # 6. 计算平均分配比例
            if members:
                average_allocation = sum(m.allocation_percentage for m in members) / len(members)
            else:
                average_allocation = 0.0
            
            # 7. 计算总小时成本
            total_hourly_cost = Decimal('0')
            for member in members:
                if member.hourly_rate and member.allocation_percentage:
                    weekly_hours = (member.allocation_percentage / 100) * 40  # 假设每周40小时
                    total_hourly_cost += member.hourly_rate * weekly_hours
            
            # 8. 技能分布统计
            skill_distribution = {}
            for member in members:
                if member.skills:
                    for skill in member.skills:
                        skill_distribution[skill] = skill_distribution.get(skill, 0) + 1
            
            # 9. 经验分布（简化实现）
            experience_distribution = {
                "初级": len([m for m in members if m.role_in_project in ["TESTER", "THIRD_PARTY"]]),
                "中级": len([m for m in members if m.role_in_project in ["DEVELOPER", "DESIGNER"]]),
                "高级": len([m for m in members if m.role_in_project in ["ARCHITECT", "PROJECT_MANAGER"]]),
                "专家": len([m for m in members if m.role_in_project in ["ADMIN"]])
            }
            
            return TeamStatistics(
                project_id=project_id,
                total_members=total_members,
                active_members=active_members,
                members_by_role=members_by_role,
                members_by_status=members_by_status,
                average_allocation=float(average_allocation),
                total_hourly_cost=total_hourly_cost,
                skill_distribution=skill_distribution,
                experience_distribution=experience_distribution,
                calculated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"获取团队统计信息失败: {e}")
            raise
    
    # 私有方法
    async def _get_project_by_id(self, project_id: int) -> Optional[Project]:
        """获取项目信息"""
        query = select(Project).where(Project.id == project_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """获取用户信息"""
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户信息"""
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_project_member(self, project_id: int, user_id: int) -> Optional[ProjectMember]:
        """获取项目成员关系"""
        query = select(ProjectMember).where(
            and_(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_project_member_by_id(self, member_id: int) -> Optional[ProjectMember]:
        """根据ID获取项目成员"""
        query = select(ProjectMember).where(ProjectMember.id == member_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _check_team_management_permission(self, project_id: int, user_id: int):
        """检查团队管理权限"""
        # TODO: 实现具体的权限检查逻辑
        # 这里应该检查用户是否有管理该项目团队的权限
        pass
    
    async def _check_project_access_permission(self, project_id: int, user_id: int):
        """检查项目访问权限"""
        # TODO: 实现具体的权限检查逻辑
        pass
    
    async def _validate_role_assignment(self, role: str, user_id: int):
        """验证角色分配权限"""
        # TODO: 实现角色分配验证逻辑
        pass
    
    async def _validate_member_removal(self, member: ProjectMember, project_id: int):
        """验证成员移除条件"""
        # TODO: 实现移除验证逻辑，比如项目经理不能被移除等
        pass
    
    async def _calculate_member_workload(self, member: ProjectMember) -> MemberWorkload:
        """计算成员工作负载"""
        # 1. 获取用户信息
        user = await self._get_user_by_id(member.user_id)
        user_info = UserInfo(
            id=member.user_id,
            username=user.username if user else "",
            email=user.email if user else "",
            nickname=user.nickname if user else "",
            avatar=user.avatar if user else None,
            phone=user.phone if user else None
        )
        
        # 2. 计算跨项目工作负载
        all_projects_query = select(ProjectMember).where(
            and_(
                ProjectMember.user_id == member.user_id,
                ProjectMember.status == "ACTIVE"
            )
        )
        all_projects_result = await self.db.execute(all_projects_query)
        all_memberships = all_projects_result.scalars().all()
        
        # 3. 计算总分配比例
        total_allocation = sum(m.allocation_percentage for m in all_memberships)
        current_projects = len(all_memberships)
        
        # 4. 计算工作负载指标
        capacity = Decimal('100')  # 假设每个人的标准容量是100%
        current_workload = total_allocation
        utilization_rate = current_workload / capacity if capacity > 0 else Decimal('0')
        overloaded = utilization_rate > Decimal('1.2')  # 超过120%认为过载
        available_capacity = max(Decimal('0'), capacity - current_workload)
        
        return MemberWorkload(
            user_id=member.user_id,
            user_info=user_info,
            current_projects=current_projects,
            total_allocation=total_allocation,
            current_workload=current_workload,
            capacity=capacity,
            utilization_rate=utilization_rate,
            overloaded=overloaded,
            available_capacity=available_capacity
        )
    
    def _generate_workload_recommendations(
        self, 
        member_workloads: List[MemberWorkload],
        overloaded_members: List[MemberWorkload],
        underloaded_members: List[MemberWorkload]
    ) -> List[str]:
        """生成工作负载建议"""
        recommendations = []
        
        if overloaded_members:
            recommendations.append(f"有 {len(overloaded_members)} 名成员工作负载过重，建议重新分配任务")
        
        if underloaded_members:
            recommendations.append(f"有 {len(underloaded_members)} 名成员工作负载较轻，可以承担更多任务")
        
        if len(overloaded_members) > 0 and len(underloaded_members) > 0:
            recommendations.append("建议将过载成员的部分任务转移给负载较轻的成员")
        
        return recommendations
    
    async def _calculate_member_recommendation(
        self, 
        candidate: User, 
        skill_requirements: List,
        project_id: int
    ) -> MemberRecommendation:
        """计算成员推荐度"""
        user_info = UserInfo(
            id=candidate.id,
            username=candidate.username,
            email=candidate.email,
            nickname=candidate.nickname,
            avatar=candidate.avatar,
            phone=candidate.phone
        )
        
        # 1. 计算技能匹配度
        skill_match_score, matching_skills, missing_skills = await self._calculate_skill_match(
            candidate, skill_requirements
        )
        
        # 2. 计算工作负载评分
        workload_score = await self._calculate_workload_score(candidate.id)
        
        # 3. 计算历史绩效评分
        performance_score = await self._calculate_performance_score(candidate.id)
        
        # 4. 计算综合评分
        overall_score = (
            skill_match_score * 0.4 +
            workload_score * 0.3 +
            performance_score * 0.3
        )
        
        # 5. 推荐角色
        recommended_role = await self._suggest_role_for_candidate(candidate, skill_requirements)
        
        # 6. 可用性分析
        availability = await self._analyze_candidate_availability(candidate.id)
        
        return MemberRecommendation(
            user_id=candidate.id,
            user_info=user_info,
            skill_match_score=skill_match_score,
            workload_score=workload_score,
            performance_score=performance_score,
            overall_score=overall_score,
            recommended_role=recommended_role,
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            availability=availability
        )
    
    async def _calculate_skill_match(self, candidate: User, skill_requirements: List) -> Tuple[float, List[str], List[str]]:
        """计算技能匹配度"""
        if not skill_requirements:
            return 1.0, [], []
        
        # 简化实现：假设用户有一些基础技能
        candidate_skills = ["Python", "Testing", "SQL", "API Testing"]  # 这应该从用户资料获取
        
        required_skills = [req.skill_name for req in skill_requirements]
        matching_skills = list(set(candidate_skills) & set(required_skills))
        missing_skills = list(set(required_skills) - set(candidate_skills))
        
        # 计算匹配度
        if not required_skills:
            match_score = 1.0
        else:
            match_score = len(matching_skills) / len(required_skills)
        
        return match_score, matching_skills, missing_skills
    
    async def _calculate_workload_score(self, user_id: int) -> float:
        """计算工作负载评分（负载越低评分越高）"""
        # 获取用户当前所有项目参与情况
        query = select(ProjectMember).where(
            and_(
                ProjectMember.user_id == user_id,
                ProjectMember.status == "ACTIVE"
            )
        )
        result = await self.db.execute(query)
        memberships = result.scalars().all()
        
        total_allocation = sum(m.allocation_percentage for m in memberships)
        
        # 负载越低，评分越高
        if total_allocation <= 50:
            return 1.0
        elif total_allocation <= 80:
            return 0.8
        elif total_allocation <= 100:
            return 0.6
        else:
            return 0.3
    
    async def _calculate_performance_score(self, user_id: int) -> float:
        """计算历史绩效评分"""
        # 简化实现：返回随机评分
        # 实际应该基于历史项目表现、任务完成质量等
        return 0.8
    
    async def _suggest_role_for_candidate(self, candidate: User, skill_requirements: List) -> ProjectMemberRole:
        """为候选人推荐角色"""
        # 简化实现：基于技能推荐角色
        candidate_skills = ["Python", "Testing", "SQL", "API Testing"]
        
        if "Testing" in candidate_skills or "QA" in candidate_skills:
            return ProjectMemberRole.TESTER
        elif "Python" in candidate_skills or "Development" in candidate_skills:
            return ProjectMemberRole.DEVELOPER
        elif "Design" in candidate_skills:
            return ProjectMemberRole.DESIGNER
        else:
            return ProjectMemberRole.TESTER
    
    async def _analyze_candidate_availability(self, user_id: int) -> Dict[str, Any]:
        """分析候选人可用性"""
        return {
            "available_hours_per_week": 40,
            "preferred_start_date": "2024-01-01",
            "timezone": "Asia/Shanghai",
            "remote_work": True
        }
    
    async def _send_welcome_notification(self, member: ProjectMember, user: User):
        """发送欢迎通知"""
        # TODO: 实现通知发送逻辑
        logger.info(f"发送欢迎通知给用户 {user.email}")
    
    async def _send_removal_notification(self, member: ProjectMember):
        """发送移除通知"""
        # TODO: 实现通知发送逻辑
        logger.info(f"发送移除通知给成员 {member.user_id}")
    
    async def _send_invitation_email(
        self, 
        email: str, 
        project_id: int, 
        invitation_id: str,
        message: Optional[str],
        expires_at: datetime
    ):
        """发送邀请邮件"""
        # TODO: 实现邮件发送逻辑
        logger.info(f"发送邀请邮件到 {email}，邀请ID: {invitation_id}")


def get_team_service(db: AsyncSession) -> TeamService:
    """获取团队服务实例"""
    return TeamService(db)