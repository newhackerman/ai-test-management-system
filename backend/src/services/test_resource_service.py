"""
测试资源分配和管理服务

本模块实现测试资源的智能分配和管理，包括：
- 基于人员技能和工作负载进行智能分配
- 实现资源冲突检测和调整建议
- 支持里程碑设置和关键路径分析
- 提供资源利用率统计和优化建议
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import logging

from ..models.test_plan import TestPlan, TestResource
from ..models.user import User
from ..models.project import Project
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from ..services.ai_assistant_service import AIAssistantService
from ..utils.test_cache import TestCacheManager

logger = logging.getLogger(__name__)


class TestResourceService:
    """测试资源管理核心服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
        self.cache_manager = TestCacheManager()
    
    async def allocate_resources(
        self, 
        plan_id: int, 
        resource_requirements: Dict[str, Any], 
        user_id: int
    ) -> List[TestResource]:
        """
        智能分配测试资源
        
        Args:
            plan_id: 测试计划ID
            resource_requirements: 资源需求
            user_id: 操作用户ID
            
        Returns:
            List[TestResource]: 分配的资源列表
        """
        try:
            # 1. 验证测试计划存在
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == plan_id).first()
            if not test_plan:
                raise NotFoundError("测试计划不存在")
            
            # 2. 分析资源需求
            analyzed_requirements = await self._analyze_resource_requirements(
                resource_requirements, test_plan
            )
            
            # 3. 获取可用人员
            available_users = await self._get_available_users(
                test_plan.planned_start_date,
                test_plan.planned_end_date,
                analyzed_requirements['required_skills']
            )
            
            # 4. 智能分配算法
            allocation_plan = await self._generate_allocation_plan(
                analyzed_requirements, available_users, test_plan
            )
            
            # 5. 检测资源冲突
            conflicts = await self._detect_resource_conflicts(allocation_plan, test_plan)
            if conflicts:
                # 调整分配方案
                allocation_plan = await self._resolve_resource_conflicts(
                    allocation_plan, conflicts
                )
            
            # 6. 创建资源分配记录
            allocated_resources = []
            for allocation in allocation_plan['allocations']:
                resource = TestResource(
                    test_plan_id=plan_id,
                    user_id=allocation['user_id'],
                    role=allocation['role'],
                    allocation_percentage=allocation['allocation_percentage'],
                    start_date=allocation['start_date'],
                    end_date=allocation['end_date'],
                    skills=allocation.get('skills', []),
                    estimated_effort_hours=allocation.get('estimated_effort_hours', 0),
                    allocated_by=user_id
                )
                
                self.db.add(resource)
                allocated_resources.append(resource)
            
            # 7. 提交事务
            self.db.commit()
            
            # 8. 清除缓存
            await self._clear_resource_cache(plan_id)
            
            logger.info(f"资源分配完成: 计划ID {plan_id}, 分配 {len(allocated_resources)} 个资源")
            
            return allocated_resources
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"分配测试资源失败: {str(e)}")
            raise
    
    async def update_resource_allocation(
        self, 
        resource_id: int, 
        update_data: Dict[str, Any], 
        user_id: int
    ) -> TestResource:
        """
        更新资源分配
        
        Args:
            resource_id: 资源ID
            update_data: 更新数据
            user_id: 操作用户ID
            
        Returns:
            TestResource: 更新后的资源对象
        """
        try:
            # 1. 获取资源记录
            resource = self.db.query(TestResource).filter(TestResource.id == resource_id).first()
            if not resource:
                raise NotFoundError("资源分配记录不存在")
            
            # 2. 验证更新权限和规则
            await self._validate_resource_update(resource, update_data, user_id)
            
            # 3. 检测更新后的冲突
            if 'allocation_percentage' in update_data or 'start_date' in update_data or 'end_date' in update_data:
                conflicts = await self._check_allocation_conflicts(resource.user_id, update_data, resource.id)
                if conflicts:
                    raise BusinessLogicError(f"资源分配冲突: {', '.join(conflicts)}")
            
            # 4. 更新字段
            for field, value in update_data.items():
                if hasattr(resource, field) and field not in ['id', 'test_plan_id', 'user_id', 'allocated_by', 'created_at']:
                    if field in ['start_date', 'end_date']:
                        setattr(resource, field, self._parse_date(value))
                    else:
                        setattr(resource, field, value)
            
            # 5. 更新时间戳
            resource.updated_at = datetime.utcnow()
            
            # 6. 提交更改
            self.db.commit()
            
            # 7. 清除缓存
            await self._clear_resource_cache(resource.test_plan_id)
            
            logger.info(f"资源分配更新成功: 资源ID {resource_id}")
            
            return resource
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新资源分配失败: {str(e)}")
            raise
    
    async def get_resource_utilization(
        self, 
        user_id: Optional[int] = None, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        获取资源利用率统计
        
        Args:
            user_id: 用户ID（可选，不指定则统计所有用户）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Any]: 资源利用率统计
        """
        try:
            # 设置默认日期范围
            if not start_date:
                start_date = datetime.utcnow().date()
            if not end_date:
                end_date = start_date + timedelta(days=30)
            
            # 构建查询
            query = self.db.query(TestResource)\
                .join(User, TestResource.user_id == User.id)\
                .filter(TestResource.start_date <= end_date)\
                .filter(TestResource.end_date >= start_date)
            
            if user_id:
                query = query.filter(TestResource.user_id == user_id)
            
            resources = query.all()
            
            # 按用户统计利用率
            user_utilization = {}
            for resource in resources:
                user_key = resource.user_id
                if user_key not in user_utilization:
                    user_utilization[user_key] = {
                        'user_id': resource.user_id,
                        'user_name': resource.user.username,
                        'total_allocation': 0,
                        'projects': [],
                        'skills': set()
                    }
                
                # 计算重叠天数
                overlap_start = max(resource.start_date, start_date)
                overlap_end = min(resource.end_date, end_date)
                overlap_days = (overlap_end - overlap_start).days + 1
                
                # 计算加权分配百分比
                weighted_allocation = resource.allocation_percentage * overlap_days / ((end_date - start_date).days + 1)
                user_utilization[user_key]['total_allocation'] += weighted_allocation
                
                # 收集项目信息
                user_utilization[user_key]['projects'].append({
                    'plan_id': resource.test_plan_id,
                    'role': resource.role,
                    'allocation_percentage': resource.allocation_percentage,
                    'start_date': resource.start_date.isoformat(),
                    'end_date': resource.end_date.isoformat()
                })
                
                # 收集技能信息
                if resource.skills:
                    user_utilization[user_key]['skills'].update(resource.skills)
            
            # 转换技能集合为列表
            for user_data in user_utilization.values():
                user_data['skills'] = list(user_data['skills'])
            
            # 计算整体统计
            total_users = len(user_utilization)
            over_allocated_users = len([u for u in user_utilization.values() if u['total_allocation'] > 100])
            under_utilized_users = len([u for u in user_utilization.values() if u['total_allocation'] < 50])
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary': {
                    'total_users': total_users,
                    'over_allocated_users': over_allocated_users,
                    'under_utilized_users': under_utilized_users,
                    'average_utilization': sum(u['total_allocation'] for u in user_utilization.values()) / total_users if total_users > 0 else 0
                },
                'user_utilization': list(user_utilization.values()),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取资源利用率失败: {str(e)}")
            raise
    
    async def detect_resource_conflicts(
        self, 
        plan_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        检测资源冲突
        
        Args:
            plan_id: 测试计划ID（可选，不指定则检测所有计划）
            
        Returns:
            List[Dict[str, Any]]: 冲突列表
        """
        try:
            conflicts = []
            
            # 构建查询
            query = self.db.query(TestResource).join(User, TestResource.user_id == User.id)
            
            if plan_id:
                query = query.filter(TestResource.test_plan_id == plan_id)
            
            resources = query.all()
            
            # 按用户分组检测冲突
            user_resources = {}
            for resource in resources:
                user_id = resource.user_id
                if user_id not in user_resources:
                    user_resources[user_id] = []
                user_resources[user_id].append(resource)
            
            # 检测每个用户的资源冲突
            for user_id, user_resource_list in user_resources.items():
                user_conflicts = await self._detect_user_resource_conflicts(user_resource_list)
                conflicts.extend(user_conflicts)
            
            return conflicts
            
        except Exception as e:
            logger.error(f"检测资源冲突失败: {str(e)}")
            return []
    
    async def generate_resource_optimization_suggestions(
        self, 
        plan_id: int
    ) -> Dict[str, Any]:
        """
        生成资源优化建议
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            Dict[str, Any]: 优化建议
        """
        try:
            # 1. 获取当前资源分配
            current_resources = self.db.query(TestResource)\
                .filter(TestResource.test_plan_id == plan_id)\
                .all()
            
            if not current_resources:
                return {'suggestions': ['暂无资源分配，建议先进行资源分配']}
            
            # 2. 分析资源利用率
            utilization = await self.get_resource_utilization()
            
            # 3. 检测冲突
            conflicts = await self.detect_resource_conflicts(plan_id)
            
            # 4. 生成AI优化建议
            optimization_prompt = self._build_optimization_prompt(
                current_resources, utilization, conflicts
            )
            ai_suggestions = await self.ai_service.generate_resource_optimization(optimization_prompt)
            
            # 5. 构建优化建议
            suggestions = {
                'plan_id': plan_id,
                'current_allocation_summary': {
                    'total_resources': len(current_resources),
                    'total_allocation_percentage': sum(r.allocation_percentage for r in current_resources),
                    'date_range': {
                        'start': min(r.start_date for r in current_resources).isoformat(),
                        'end': max(r.end_date for r in current_resources).isoformat()
                    }
                },
                'identified_issues': [],
                'optimization_suggestions': ai_suggestions.get('suggestions', []),
                'reallocation_recommendations': ai_suggestions.get('reallocations', []),
                'skill_gap_analysis': await self._analyze_skill_gaps(plan_id),
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # 6. 识别问题
            if conflicts:
                suggestions['identified_issues'].append({
                    'type': 'resource_conflicts',
                    'count': len(conflicts),
                    'description': '存在资源分配冲突'
                })
            
            over_allocated = [u for u in utilization['user_utilization'] if u['total_allocation'] > 100]
            if over_allocated:
                suggestions['identified_issues'].append({
                    'type': 'over_allocation',
                    'count': len(over_allocated),
                    'description': '部分人员分配过度'
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"生成资源优化建议失败: {str(e)}")
            raise
    
    async def get_critical_path_analysis(self, plan_id: int) -> Dict[str, Any]:
        """
        关键路径分析
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            Dict[str, Any]: 关键路径分析结果
        """
        try:
            # 1. 获取测试计划和阶段信息
            from ..models.test_plan import TestPhase
            
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == plan_id).first()
            if not test_plan:
                raise NotFoundError("测试计划不存在")
            
            phases = self.db.query(TestPhase)\
                .filter(TestPhase.test_plan_id == plan_id)\
                .order_by(TestPhase.phase_order)\
                .all()
            
            # 2. 构建阶段依赖图
            phase_graph = await self._build_phase_dependency_graph(phases)
            
            # 3. 计算关键路径
            critical_path = await self._calculate_critical_path(phase_graph, phases)
            
            # 4. 分析资源约束
            resource_constraints = await self._analyze_resource_constraints(plan_id, phases)
            
            # 5. 计算项目风险
            schedule_risk = await self._assess_schedule_risk(critical_path, resource_constraints)
            
            return {
                'plan_id': plan_id,
                'critical_path': critical_path,
                'total_duration_days': critical_path['total_duration'] if critical_path else 0,
                'resource_constraints': resource_constraints,
                'schedule_risk': schedule_risk,
                'bottlenecks': await self._identify_bottlenecks(phases, resource_constraints),
                'recommendations': await self._generate_critical_path_recommendations(
                    critical_path, resource_constraints, schedule_risk
                ),
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"关键路径分析失败: {str(e)}")
            raise
    
    async def _analyze_resource_requirements(
        self, 
        requirements: Dict[str, Any], 
        test_plan: TestPlan
    ) -> Dict[str, Any]:
        """分析资源需求"""
        # 基于测试计划类型和规模分析资源需求
        analyzed = {
            'required_roles': requirements.get('roles', ['tester']),
            'required_skills': requirements.get('skills', []),
            'estimated_effort_hours': requirements.get('effort_hours', 160),  # 默认160小时
            'preferred_team_size': requirements.get('team_size', 3),
            'timeline_constraints': {
                'start_date': test_plan.planned_start_date,
                'end_date': test_plan.planned_end_date
            }
        }
        
        # AI辅助需求分析
        if hasattr(self.ai_service, 'analyze_resource_requirements'):
            ai_analysis = await self.ai_service.analyze_resource_requirements(
                test_plan, requirements
            )
            analyzed.update(ai_analysis)
        
        return analyzed
    
    async def _get_available_users(
        self, 
        start_date: date, 
        end_date: date, 
        required_skills: List[str]
    ) -> List[Dict[str, Any]]:
        """获取可用用户"""
        # 获取所有用户
        users = self.db.query(User).filter(User.is_active == True).all()
        
        available_users = []
        for user in users:
            # 计算用户在指定时间段的可用性
            existing_allocations = self.db.query(TestResource)\
                .filter(TestResource.user_id == user.id)\
                .filter(TestResource.start_date <= end_date)\
                .filter(TestResource.end_date >= start_date)\
                .all()
            
            total_allocation = sum(r.allocation_percentage for r in existing_allocations)
            available_percentage = max(0, 100 - total_allocation)
            
            if available_percentage > 0:
                # 获取用户技能（这里简化处理，实际应该从用户技能表获取）
                user_skills = getattr(user, 'skills', [])
                skill_match_score = self._calculate_skill_match_score(user_skills, required_skills)
                
                available_users.append({
                    'user_id': user.id,
                    'user_name': user.username,
                    'available_percentage': available_percentage,
                    'skills': user_skills,
                    'skill_match_score': skill_match_score,
                    'experience_level': getattr(user, 'experience_level', 'intermediate')
                })
        
        # 按技能匹配度和可用性排序
        available_users.sort(key=lambda x: (x['skill_match_score'], x['available_percentage']), reverse=True)
        
        return available_users
    
    def _calculate_skill_match_score(self, user_skills: List[str], required_skills: List[str]) -> float:
        """计算技能匹配分数"""
        if not required_skills:
            return 1.0
        
        if not user_skills:
            return 0.0
        
        matched_skills = set(user_skills) & set(required_skills)
        return len(matched_skills) / len(required_skills)
    
    async def _generate_allocation_plan(
        self, 
        requirements: Dict[str, Any], 
        available_users: List[Dict[str, Any]], 
        test_plan: TestPlan
    ) -> Dict[str, Any]:
        """生成分配方案"""
        allocations = []
        remaining_effort = requirements['estimated_effort_hours']
        
        # 简化的分配算法
        for i, user in enumerate(available_users[:requirements['preferred_team_size']]):
            if remaining_effort <= 0:
                break
            
            # 计算分配百分比
            if i == 0:  # 主要测试人员
                allocation_percentage = min(user['available_percentage'], 80)
            else:  # 辅助测试人员
                allocation_percentage = min(user['available_percentage'], 50)
            
            # 计算工作时间
            work_days = (test_plan.planned_end_date - test_plan.planned_start_date).days
            daily_hours = 8
            allocated_hours = work_days * daily_hours * (allocation_percentage / 100)
            
            allocations.append({
                'user_id': user['user_id'],
                'role': 'test_lead' if i == 0 else 'tester',
                'allocation_percentage': allocation_percentage,
                'start_date': test_plan.planned_start_date,
                'end_date': test_plan.planned_end_date,
                'skills': user['skills'],
                'estimated_effort_hours': min(allocated_hours, remaining_effort)
            })
            
            remaining_effort -= allocated_hours
        
        return {
            'allocations': allocations,
            'total_allocated_hours': sum(a['estimated_effort_hours'] for a in allocations),
            'remaining_effort_hours': max(0, remaining_effort)
        }
    
    async def _detect_resource_conflicts(
        self, 
        allocation_plan: Dict[str, Any], 
        test_plan: TestPlan
    ) -> List[Dict[str, Any]]:
        """检测资源冲突"""
        conflicts = []
        
        for allocation in allocation_plan['allocations']:
            # 检查用户在同一时间段的其他分配
            existing_allocations = self.db.query(TestResource)\
                .filter(TestResource.user_id == allocation['user_id'])\
                .filter(TestResource.start_date <= allocation['end_date'])\
                .filter(TestResource.end_date >= allocation['start_date'])\
                .all()
            
            total_allocation = sum(r.allocation_percentage for r in existing_allocations) + allocation['allocation_percentage']
            
            if total_allocation > 100:
                conflicts.append({
                    'type': 'over_allocation',
                    'user_id': allocation['user_id'],
                    'total_allocation': total_allocation,
                    'conflict_percentage': total_allocation - 100
                })
        
        return conflicts
    
    async def _resolve_resource_conflicts(
        self, 
        allocation_plan: Dict[str, Any], 
        conflicts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """解决资源冲突"""
        # 简化的冲突解决策略：降低分配百分比
        for conflict in conflicts:
            for allocation in allocation_plan['allocations']:
                if allocation['user_id'] == conflict['user_id']:
                    # 降低分配百分比
                    reduction = conflict['conflict_percentage']
                    allocation['allocation_percentage'] = max(20, allocation['allocation_percentage'] - reduction)
                    
                    # 重新计算工作时间
                    work_days = (allocation['end_date'] - allocation['start_date']).days
                    daily_hours = 8
                    allocation['estimated_effort_hours'] = work_days * daily_hours * (allocation['allocation_percentage'] / 100)
        
        return allocation_plan
    
    async def _validate_resource_update(
        self, 
        resource: TestResource, 
        update_data: Dict[str, Any], 
        user_id: int
    ) -> None:
        """验证资源更新"""
        # 检查权限（简化处理）
        # 实际应该检查用户是否有权限修改资源分配
        
        # 检查分配百分比
        if 'allocation_percentage' in update_data:
            if update_data['allocation_percentage'] < 0 or update_data['allocation_percentage'] > 100:
                raise ValidationError("分配百分比必须在0-100之间")
    
    async def _check_allocation_conflicts(
        self, 
        user_id: int, 
        update_data: Dict[str, Any], 
        exclude_resource_id: int
    ) -> List[str]:
        """检查分配冲突"""
        conflicts = []
        
        # 获取用户的其他分配
        other_allocations = self.db.query(TestResource)\
            .filter(TestResource.user_id == user_id)\
            .filter(TestResource.id != exclude_resource_id)\
            .all()
        
        # 计算总分配百分比
        total_allocation = sum(r.allocation_percentage for r in other_allocations)
        total_allocation += update_data.get('allocation_percentage', 0)
        
        if total_allocation > 100:
            conflicts.append(f"总分配百分比超过100%: {total_allocation}%")
        
        return conflicts
    
    async def _detect_user_resource_conflicts(
        self, 
        user_resources: List[TestResource]
    ) -> List[Dict[str, Any]]:
        """检测用户资源冲突"""
        conflicts = []
        
        # 按时间段分组检查
        time_periods = {}
        for resource in user_resources:
            period_key = f"{resource.start_date}_{resource.end_date}"
            if period_key not in time_periods:
                time_periods[period_key] = []
            time_periods[period_key].append(resource)
        
        # 检查每个时间段的分配总和
        for period, resources in time_periods.items():
            total_allocation = sum(r.allocation_percentage for r in resources)
            if total_allocation > 100:
                conflicts.append({
                    'type': 'over_allocation',
                    'user_id': resources[0].user_id,
                    'user_name': resources[0].user.username,
                    'period': period,
                    'total_allocation': total_allocation,
                    'over_allocation': total_allocation - 100,
                    'involved_plans': [r.test_plan_id for r in resources]
                })
        
        return conflicts
    
    def _build_optimization_prompt(
        self, 
        current_resources: List[TestResource], 
        utilization: Dict[str, Any], 
        conflicts: List[Dict[str, Any]]
    ) -> str:
        """构建优化提示"""
        return f"""
        请分析以下测试资源分配情况并提供优化建议：

        当前资源分配：
        - 总资源数：{len(current_resources)}
        - 平均利用率：{utilization['summary']['average_utilization']:.1f}%
        - 过度分配人员：{utilization['summary']['over_allocated_users']}人
        - 利用不足人员：{utilization['summary']['under_utilized_users']}人

        发现的冲突：
        - 冲突数量：{len(conflicts)}

        请提供：
        1. 资源优化建议
        2. 重新分配方案
        3. 技能缺口分析
        4. 风险缓解措施

        请以JSON格式返回结构化建议。
        """
    
    async def _analyze_skill_gaps(self, plan_id: int) -> Dict[str, Any]:
        """分析技能缺口"""
        # 获取计划所需技能
        test_plan = self.db.query(TestPlan).filter(TestPlan.id == plan_id).first()
        
        # 获取当前分配的资源技能
        current_resources = self.db.query(TestResource)\
            .filter(TestResource.test_plan_id == plan_id)\
            .all()
        
        current_skills = set()
        for resource in current_resources:
            if resource.skills:
                current_skills.update(resource.skills)
        
        # 简化的技能需求分析
        required_skills = {'functional_testing', 'automation', 'performance_testing', 'security_testing'}
        
        missing_skills = required_skills - current_skills
        
        return {
            'required_skills': list(required_skills),
            'current_skills': list(current_skills),
            'missing_skills': list(missing_skills),
            'skill_coverage': len(current_skills) / len(required_skills) * 100 if required_skills else 100
        }
    
    async def _build_phase_dependency_graph(self, phases: List) -> Dict[str, Any]:
        """构建阶段依赖图"""
        graph = {}
        for phase in phases:
            graph[phase.id] = {
                'phase': phase,
                'dependencies': phase.dependencies or [],
                'dependents': []
            }
        
        # 构建反向依赖关系
        for phase_id, node in graph.items():
            for dep_id in node['dependencies']:
                if dep_id in graph:
                    graph[dep_id]['dependents'].append(phase_id)
        
        return graph
    
    async def _calculate_critical_path(self, phase_graph: Dict[str, Any], phases: List) -> Dict[str, Any]:
        """计算关键路径"""
        # 简化的关键路径计算
        # 实际应该使用CPM算法
        
        critical_phases = []
        total_duration = 0
        
        for phase in sorted(phases, key=lambda p: p.phase_order):
            if phase.planned_start_date and phase.planned_end_date:
                duration = (phase.planned_end_date - phase.planned_start_date).days
                critical_phases.append({
                    'phase_id': phase.id,
                    'phase_name': phase.phase_name,
                    'duration_days': duration,
                    'start_date': phase.planned_start_date.isoformat(),
                    'end_date': phase.planned_end_date.isoformat()
                })
                total_duration += duration
        
        return {
            'critical_phases': critical_phases,
            'total_duration': total_duration
        }
    
    async def _analyze_resource_constraints(self, plan_id: int, phases: List) -> List[Dict[str, Any]]:
        """分析资源约束"""
        constraints = []
        
        # 检查每个阶段的资源约束
        for phase in phases:
            phase_resources = self.db.query(TestResource)\
                .filter(TestResource.test_plan_id == plan_id)\
                .all()  # 简化处理，实际应该按阶段过滤
            
            if len(phase_resources) < 2:  # 假设每个阶段至少需要2个人
                constraints.append({
                    'type': 'insufficient_resources',
                    'phase_id': phase.id,
                    'phase_name': phase.phase_name,
                    'current_resources': len(phase_resources),
                    'required_resources': 2
                })
        
        return constraints
    
    async def _assess_schedule_risk(
        self, 
        critical_path: Dict[str, Any], 
        resource_constraints: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """评估进度风险"""
        risk_level = 'low'
        risk_factors = []
        
        if resource_constraints:
            risk_level = 'medium'
            risk_factors.append(f"存在{len(resource_constraints)}个资源约束")
        
        if critical_path and critical_path['total_duration'] > 60:  # 超过60天
            risk_level = 'high'
            risk_factors.append("关键路径过长")
        
        return {
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'mitigation_suggestions': [
                "增加关键阶段的资源投入",
                "考虑并行执行部分阶段",
                "建立资源池以应对突发需求"
            ]
        }
    
    async def _identify_bottlenecks(self, phases: List, resource_constraints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别瓶颈"""
        bottlenecks = []
        
        # 基于资源约束识别瓶颈
        for constraint in resource_constraints:
            bottlenecks.append({
                'type': 'resource_bottleneck',
                'phase_id': constraint['phase_id'],
                'phase_name': constraint['phase_name'],
                'description': f"资源不足：需要{constraint['required_resources']}人，当前{constraint['current_resources']}人"
            })
        
        return bottlenecks
    
    async def _generate_critical_path_recommendations(
        self, 
        critical_path: Dict[str, Any], 
        resource_constraints: List[Dict[str, Any]], 
        schedule_risk: Dict[str, Any]
    ) -> List[str]:
        """生成关键路径建议"""
        recommendations = []
        
        if schedule_risk['risk_level'] == 'high':
            recommendations.append("建议重新评估项目时间线，考虑延长关键阶段")
            recommendations.append("增加关键路径上的资源投入")
        
        if resource_constraints:
            recommendations.append("优先解决资源约束问题")
            recommendations.append("考虑外包或临时增加人员")
        
        recommendations.append("建立每日进度跟踪机制")
        recommendations.append("准备应急计划以应对延期风险")
        
        return recommendations
    
    async def _clear_resource_cache(self, plan_id: int) -> None:
        """清除资源相关缓存"""
        try:
            await self.cache_manager.delete_project_plans(plan_id)
        except Exception as e:
            logger.warning(f"清除缓存失败: {str(e)}")
    
    def _parse_date(self, date_value: Any) -> Optional[date]:
        """解析日期值"""
        if not date_value:
            return None
        
        if isinstance(date_value, date):
            return date_value
        
        if isinstance(date_value, datetime):
            return date_value.date()
        
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    logger.warning(f"无法解析日期格式: {date_value}")
                    return None
        
        return None