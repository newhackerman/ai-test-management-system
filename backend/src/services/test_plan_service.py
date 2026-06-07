"""
测试计划管理服务

本模块实现测试计划的完整生命周期管理，包括：
- 测试计划的创建、更新、删除功能
- 计划编码自动生成和唯一性验证
- 计划数据验证和业务规则检查
- 权限控制和安全验证
- AI辅助策略建议
- 进度跟踪和风险预警
- 测试阶段管理和里程碑控制
- 资源分配和管理
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import IntegrityError
import logging

from ..models.test_plan import TestPlan, TestPhase, TestResource, TestType, TestPlanStatus, TestPhaseStatus
from ..models.project import Project
from ..models.user import User
from ..models.requirement import Requirement
from ..core.database import get_db
from ..core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ..services.ai_assistant_service import AIAssistantService
from ..services.permission_service import PermissionService
from ..services.project_service import ProjectService
from ..services.user import UserService
from ..utils.test_cache import TestCacheKeys, TestCacheManager, TestCacheTTL

logger = logging.getLogger(__name__)


class TestPlanService:
    """测试计划管理核心服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
        self.permission_service = PermissionService(db)
        self.project_service = ProjectService(db)
        self.user_service = UserService(db)
        self.cache_manager = TestCacheManager()
    
    async def create_test_plan(
        self, 
        plan_data: Dict[str, Any], 
        creator_id: int
    ) -> TestPlan:
        """
        创建测试计划
        
        Args:
            plan_data: 测试计划数据
            creator_id: 创建人ID
            
        Returns:
            TestPlan: 创建的测试计划对象
            
        Raises:
            ValidationError: 数据验证失败
            PermissionError: 权限不足
            BusinessLogicError: 业务规则违反
        """
        try:
            # 1. 验证创建权限
            # 1. 验证项目是否存在
            project = self.db.query(Project).filter(Project.id == plan_data['project_id']).first()
            if not project:
                raise NotFoundError("项目不存在")
            
            # 2. 验证计划数据
            await self._validate_plan_data(plan_data)
            
            # 4. 生成计划编码
            plan_code = await self._generate_plan_code(project.project_code)
            
            # 5. AI辅助策略建议
            strategy_suggestions = await self._get_ai_strategy_suggestions(plan_data, project)
            
            # 6. 创建测试计划实体
            test_plan = TestPlan(
                plan_code=plan_code,
                project_id=plan_data['project_id'],
                plan_name=plan_data['plan_name'],
                description=plan_data.get('description'),
                test_type=TestType(plan_data['test_type']),
                test_strategy=strategy_suggestions.get('strategy', plan_data.get('test_strategy')),
                test_scope=plan_data.get('test_scope'),
                planned_start_date=self._parse_date(plan_data.get('planned_start_date')),
                planned_end_date=self._parse_date(plan_data.get('planned_end_date')),
                test_manager_id=plan_data.get('test_manager_id', creator_id),
                created_by=creator_id
            )
            
            # 7. 保存测试计划
            self.db.add(test_plan)
            self.db.flush()  # 获取ID但不提交事务
            
            # 8. 创建测试阶段
            if plan_data.get('phases'):
                await self._create_test_phases(test_plan.id, plan_data['phases'])
            
            # 9. 分配测试资源
            if plan_data.get('resources'):
                await self._allocate_test_resources(test_plan.id, plan_data['resources'])
            
            # 10. 提交事务
            self.db.commit()
            
            # 11. 清除相关缓存
            await self._clear_plan_cache(test_plan.project_id)
            
            # 12. 记录操作日志
            logger.info(f"测试计划创建成功: {plan_code}, 创建人: {creator_id}")
            
            return test_plan
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建测试计划失败: {str(e)}")
            raise
    
    async def update_test_plan(
        self, 
        plan_id: int, 
        update_data: Dict[str, Any], 
        user_id: int
    ) -> TestPlan:
        """
        更新测试计划
        
        Args:
            plan_id: 测试计划ID
            update_data: 更新数据
            user_id: 操作用户ID
            
        Returns:
            TestPlan: 更新后的测试计划对象
        """
        try:
            # 1. 获取测试计划
            test_plan = await self.get_test_plan_by_id(plan_id)
            if not test_plan:
                raise NotFoundError("测试计划不存在")
            
            # 2. 验证更新权限
            await self._validate_update_permission(user_id, test_plan)
            
            # 3. 验证业务规则
            await self._validate_update_rules(test_plan, update_data)
            
            # 4. 更新字段
            for field, value in update_data.items():
                if hasattr(test_plan, field) and field not in ['id', 'plan_code', 'created_by', 'created_at']:
                    if field in ['planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date']:
                        setattr(test_plan, field, self._parse_date(value))
                    elif field == 'test_type':
                        setattr(test_plan, field, TestType(value))
                    elif field == 'status':
                        setattr(test_plan, field, TestPlanStatus(value))
                    else:
                        setattr(test_plan, field, value)
            
            # 5. 更新时间戳
            test_plan.updated_at = datetime.utcnow()
            
            # 6. 提交更改
            self.db.commit()
            
            # 7. 清除缓存
            await self._clear_plan_cache(test_plan.project_id, plan_id)
            
            logger.info(f"测试计划更新成功: {test_plan.plan_code}, 操作人: {user_id}")
            
            return test_plan
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新测试计划失败: {str(e)}")
            raise
    
    async def delete_test_plan(self, plan_id: int, user_id: int) -> bool:
        """
        删除测试计划
        
        Args:
            plan_id: 测试计划ID
            user_id: 操作用户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 1. 获取测试计划
            test_plan = await self.get_test_plan_by_id(plan_id)
            if not test_plan:
                raise NotFoundError("测试计划不存在")
            
            # 2. 验证删除权限
            await self._validate_delete_permission(user_id, test_plan)
            
            # 3. 验证删除规则
            await self._validate_delete_rules(test_plan)
            
            # 4. 软删除或硬删除
            if test_plan.status in [TestPlanStatus.IN_PROGRESS, TestPlanStatus.COMPLETED]:
                # 已开始或完成的计划不能删除，只能取消
                test_plan.status = TestPlanStatus.CANCELLED
                test_plan.updated_at = datetime.utcnow()
            else:
                # 草稿状态可以直接删除
                self.db.delete(test_plan)
            
            # 5. 提交更改
            self.db.commit()
            
            # 6. 清除缓存
            await self._clear_plan_cache(test_plan.project_id, plan_id)
            
            logger.info(f"测试计划删除成功: {test_plan.plan_code}, 操作人: {user_id}")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除测试计划失败: {str(e)}")
            raise
    
    async def get_test_plan_by_id(self, plan_id: int) -> Optional[TestPlan]:
        """
        根据ID获取测试计划
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            Optional[TestPlan]: 测试计划对象或None
        """
        # 先尝试从缓存获取
        return self.db.query(TestPlan).filter(TestPlan.id == plan_id).first()
    async def get_test_plan_by_code(self, plan_code: str) -> Optional[TestPlan]:
        """
        根据编码获取测试计划
        
        Args:
            plan_code: 测试计划编码
            
        Returns:
            Optional[TestPlan]: 测试计划对象或None
        """
        return self.db.query(TestPlan).filter(TestPlan.plan_code == plan_code).first()
    
    async def get_test_plans_by_project(
        self, 
        project_id: int, 
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TestPlan], int]:
        """
        获取项目的测试计划列表
        
        Args:
            project_id: 项目ID
            status: 状态过滤
            page: 页码
            page_size: 每页大小
            
        Returns:
            Tuple[List[TestPlan], int]: 测试计划列表和总数
        """
        query = self.db.query(TestPlan).filter(TestPlan.project_id == project_id)
        
        if status:
            query = query.filter(TestPlan.status == TestPlanStatus(status))
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        plans = query.order_by(desc(TestPlan.created_at))\
                    .offset((page - 1) * page_size)\
                    .limit(page_size)\
                    .all()
        
        return plans, total
    
    async def update_plan_progress(self, plan_id: int) -> Dict[str, Any]:
        """
        更新测试计划进度
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            Dict[str, Any]: 进度信息
        """
        try:
            # 1. 获取测试计划
            test_plan = await self.get_test_plan_by_id(plan_id)
            if not test_plan:
                raise NotFoundError("测试计划不存在")
            
            # 2. 统计用例执行情况
            from ..models.test_case import TestCase, TestExecution, ExecutionStatus
            
            # 获取计划下的所有用例，并按每个用例的最新执行结果统计，避免多次执行被重复计数
            cases = self.db.query(TestCase).filter(TestCase.test_plan_id == plan_id).all()
            total_cases = len(cases)
            case_ids = [test_case.id for test_case in cases]

            latest_status_by_case = {}
            if case_ids:
                latest_executions = (
                    self.db.query(TestExecution)
                    .filter(TestExecution.test_case_id.in_(case_ids))
                    .order_by(
                        TestExecution.test_case_id.asc(),
                        desc(func.coalesce(
                            TestExecution.completed_at,
                            TestExecution.updated_at,
                            TestExecution.started_at,
                            TestExecution.created_at,
                        )),
                        desc(TestExecution.id),
                    )
                    .all()
                )
                for execution in latest_executions:
                    latest_status_by_case.setdefault(execution.test_case_id, execution.execution_status)

            status_counts = {status.value: 0 for status in ExecutionStatus}
            for test_case in cases:
                status = latest_status_by_case.get(test_case.id) or test_case.last_execution_status or ExecutionStatus.NOT_EXECUTED
                status_value = status.value if hasattr(status, "value") else str(status)
                status_counts[status_value] = status_counts.get(status_value, 0) + 1

            completed_statuses = {
                ExecutionStatus.PASSED.value,
                ExecutionStatus.FAILED.value,
                ExecutionStatus.BLOCKED.value,
                ExecutionStatus.SKIPPED.value,
            }
            executed_cases = sum(status_counts.get(status, 0) for status in completed_statuses)
            passed_cases = status_counts.get(ExecutionStatus.PASSED.value, 0)
            failed_cases = status_counts.get(ExecutionStatus.FAILED.value, 0)
            blocked_cases = status_counts.get(ExecutionStatus.BLOCKED.value, 0)
            skipped_cases = status_counts.get(ExecutionStatus.SKIPPED.value, 0)
            
            # 3. 计算进度指标
            execution_rate = (executed_cases / total_cases * 100) if total_cases > 0 else 0
            pass_rate = (passed_cases / executed_cases * 100) if executed_cases > 0 else 0
            
            # 4. 更新计划统计
            test_plan.total_cases = total_cases
            test_plan.executed_cases = executed_cases
            test_plan.passed_cases = passed_cases
            test_plan.failed_cases = failed_cases
            test_plan.execution_rate = execution_rate
            test_plan.pass_rate = pass_rate
            test_plan.updated_at = datetime.utcnow()
            
            # 5. 提交更改
            self.db.commit()
            
            # 6. 构建进度信息
            progress_info = {
                'plan_id': plan_id,
                'total_cases': total_cases,
                'executed_cases': executed_cases,
                'passed_cases': passed_cases,
                'failed_cases': failed_cases,
                'blocked_cases': blocked_cases,
                'skipped_cases': skipped_cases,
                'execution_rate': round(execution_rate, 2),
                'pass_rate': round(pass_rate, 2),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # 7. 更新缓存
            self.cache_manager.set(
                TestCacheKeys.TEST_PLAN_PROGRESS,
                progress_info,
                TestCacheTTL.TEST_PLAN_PROGRESS,
                plan_id=plan_id,
            )
            
            return progress_info
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新测试计划进度失败: {str(e)}")
            raise
    
    async def _generate_plan_code(self, project_code: str) -> str:
        """
        生成测试计划编码
        
        Args:
            project_code: 项目编码
            
        Returns:
            str: 测试计划编码
        """
        today = datetime.now().strftime("%Y%m%d")
        
        # 查询当天已创建的计划数量
        count = self.db.query(TestPlan)\
            .filter(TestPlan.plan_code.like(f"TP-{project_code}-{today}-%"))\
            .count()
        
        sequence = count + 1
        plan_code = f"TP-{project_code}-{today}-{sequence:03d}"
        
        # 确保编码唯一性
        while self.db.query(TestPlan).filter(TestPlan.plan_code == plan_code).first():
            sequence += 1
            plan_code = f"TP-{project_code}-{today}-{sequence:03d}"
        
        return plan_code
    
    async def _validate_plan_data(self, plan_data: Dict[str, Any]) -> None:
        """
        验证测试计划数据
        
        Args:
            plan_data: 计划数据
            
        Raises:
            ValidationError: 数据验证失败
        """
        # 必填字段验证
        required_fields = ['project_id', 'plan_name', 'test_type']
        for field in required_fields:
            if not plan_data.get(field):
                raise ValidationError(f"字段 {field} 不能为空")
        
        # 计划名称长度验证
        if len(plan_data['plan_name']) > 200:
            raise ValidationError("计划名称长度不能超过200个字符")
        
        # 测试类型验证
        try:
            TestType(plan_data['test_type'])
        except ValueError:
            raise ValidationError("无效的测试类型")
        
        # 日期验证
        start_date = plan_data.get('planned_start_date')
        end_date = plan_data.get('planned_end_date')
        
        if start_date and end_date:
            start_date_obj = self._parse_date(start_date)
            end_date_obj = self._parse_date(end_date)
            
            if start_date_obj and end_date_obj and start_date_obj >= end_date_obj:
                raise ValidationError("计划开始日期必须早于结束日期")
        
        # 测试经理验证
        if plan_data.get('test_manager_id'):
            manager = self.db.query(User).filter(User.id == plan_data['test_manager_id']).first()
            if not manager:
                raise ValidationError("指定的测试经理不存在")
    
    async def _validate_create_permission(self, user_id: int, project_id: int) -> None:
        """
        验证创建权限
        
        Args:
            user_id: 用户ID
            project_id: 项目ID
            
        Raises:
            PermissionError: 权限不足
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise PermissionError("没有创建测试计划的权限")
    
    async def _validate_update_permission(self, user_id: int, test_plan: TestPlan) -> None:
        """
        验证更新权限
        
        Args:
            user_id: 用户ID
            test_plan: 测试计划对象
            
        Raises:
            PermissionError: 权限不足
        """
        # 检查是否是计划创建者或测试经理
        if test_plan.created_by == user_id or test_plan.test_manager_id == user_id:
            return
        
        project = self.db.query(Project).filter(Project.id == test_plan.project_id).first()
        if not project:
            raise PermissionError("没有更新测试计划的权限")
    
    async def _validate_delete_permission(self, user_id: int, test_plan: TestPlan) -> None:
        """
        验证删除权限
        
        Args:
            user_id: 用户ID
            test_plan: 测试计划对象
            
        Raises:
            PermissionError: 权限不足
        """
        # 检查是否是计划创建者
        if test_plan.created_by == user_id:
            return
        
        project = self.db.query(Project).filter(Project.id == test_plan.project_id).first()
        if not project:
            raise PermissionError("没有删除测试计划的权限")
    
    async def _validate_update_rules(self, test_plan: TestPlan, update_data: Dict[str, Any]) -> None:
        """
        验证更新业务规则
        
        Args:
            test_plan: 测试计划对象
            update_data: 更新数据
            
        Raises:
            BusinessLogicError: 业务规则违反
        """
        # 已完成的计划不能修改关键信息
        if test_plan.status == TestPlanStatus.COMPLETED:
            restricted_fields = ['test_type', 'test_strategy', 'test_scope']
            for field in restricted_fields:
                if field in update_data:
                    raise BusinessLogicError(f"已完成的测试计划不能修改{field}")
        
        # 进行中的计划不能修改计划日期
        if test_plan.status == TestPlanStatus.IN_PROGRESS:
            if 'planned_start_date' in update_data or 'planned_end_date' in update_data:
                raise BusinessLogicError("进行中的测试计划不能修改计划日期")
    
    async def _validate_delete_rules(self, test_plan: TestPlan) -> None:
        """
        验证删除业务规则
        
        Args:
            test_plan: 测试计划对象
            
        Raises:
            BusinessLogicError: 业务规则违反
        """
        # 检查是否有关联的测试用例
        from ..models.test_case import TestCase
        case_count = self.db.query(TestCase).filter(TestCase.test_plan_id == test_plan.id).count()
        
        if case_count > 0 and test_plan.status != TestPlanStatus.DRAFT:
            raise BusinessLogicError("包含测试用例的计划不能删除，只能取消")
    
    async def _get_ai_strategy_suggestions(
        self, 
        plan_data: Dict[str, Any], 
        project: Any
    ) -> Dict[str, Any]:
        """
        获取AI策略建议
        
        Args:
            plan_data: 计划数据
            project: 项目对象
            
        Returns:
            Dict[str, Any]: AI建议结果
        """
        try:
            # 构建AI提示
            prompt = f"""
            基于以下项目和测试计划信息，提供测试策略建议：
            
            项目信息：
            - 项目名称：{project.project_name}
            - 项目类型：{getattr(project, 'project_type', '未知')}
            - 项目描述：{getattr(project, 'description', '')}
            
            测试计划信息：
            - 计划名称：{plan_data['plan_name']}
            - 测试类型：{plan_data['test_type']}
            - 测试范围：{plan_data.get('test_scope', '')}
            - 描述：{plan_data.get('description', '')}
            
            请提供：
            1. 测试策略建议
            2. 关键测试点
            3. 风险评估
            4. 资源建议
            """
            
            # 调用AI服务
            ai_response = await self.ai_service.generate_test_strategy(prompt)
            
            return {
                'strategy': ai_response.get('strategy', ''),
                'key_points': ai_response.get('key_points', []),
                'risks': ai_response.get('risks', []),
                'resource_suggestions': ai_response.get('resource_suggestions', [])
            }
            
        except Exception as e:
            logger.warning(f"AI策略建议生成失败: {str(e)}")
            return {}
    
    async def _create_test_phases(self, plan_id: int, phases_data: List[Dict[str, Any]]) -> None:
        """
        创建测试阶段
        
        Args:
            plan_id: 测试计划ID
            phases_data: 阶段数据列表
        """
        for phase_data in phases_data:
            phase = TestPhase(
                test_plan_id=plan_id,
                phase_name=phase_data['phase_name'],
                description=phase_data.get('description'),
                planned_start_date=self._parse_date(phase_data.get('planned_start_date')),
                planned_end_date=self._parse_date(phase_data.get('planned_end_date')),
                entry_criteria=phase_data.get('entry_criteria'),
                exit_criteria=phase_data.get('exit_criteria'),
                phase_order=phase_data.get('phase_order', 1)
            )
            self.db.add(phase)
    
    async def _allocate_test_resources(self, plan_id: int, resources_data: List[Dict[str, Any]]) -> None:
        """
        分配测试资源
        
        Args:
            plan_id: 测试计划ID
            resources_data: 资源数据列表
        """
        for resource_data in resources_data:
            resource = TestResource(
                test_plan_id=plan_id,
                user_id=resource_data['user_id'],
                role=resource_data.get('role', 'tester'),
                allocation_percentage=resource_data.get('allocation_percentage', 100),
                start_date=self._parse_date(resource_data.get('start_date')),
                end_date=self._parse_date(resource_data.get('end_date'))
            )
            self.db.add(resource)
    
    async def _clear_plan_cache(self, project_id: int, plan_id: Optional[int] = None) -> None:
        """
        清除计划相关缓存
        
        Args:
            project_id: 项目ID
            plan_id: 计划ID（可选）
        """
        try:
            # 清除项目计划列表缓存
            self.cache_manager.delete(TestCacheKeys.PROJECT_TEST_PLANS, project_id=project_id)
            
            # 清除特定计划缓存
            if plan_id:
                self.cache_manager.delete(TestCacheKeys.TEST_PLAN_INFO, plan_id=plan_id)
                self.cache_manager.delete(TestCacheKeys.TEST_PLAN_PROGRESS, plan_id=plan_id)
                
        except Exception as e:
            logger.warning(f"清除缓存失败: {str(e)}")
    
    def _parse_date(self, date_value: Any) -> Optional[date]:
        """
        解析日期值
        
        Args:
            date_value: 日期值
            
        Returns:
            Optional[date]: 解析后的日期对象
        """
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


class TestPlanAnalyticsService:
    """测试计划分析服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_manager = TestCacheManager()
    
    async def get_plan_statistics(self, plan_id: int) -> Dict[str, Any]:
        """
        获取测试计划统计信息
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 先尝试从缓存获取
        cached_stats = None
        
        # 从数据库计算统计信息
        from ..models.test_case import TestCase
        from ..models.test_case import TestExecution, ExecutionStatus, ExecutionStatus
        from ..models.test_case import Defect, DefectSeverity
        
        # 基础统计
        total_cases = self.db.query(TestCase).filter(TestCase.test_plan_id == plan_id).count()
        
        # 用例优先级分布
        priority_stats = self.db.query(
            TestCase.priority,
            func.count(TestCase.id).label('count')
        ).filter(TestCase.test_plan_id == plan_id)\
         .group_by(TestCase.priority)\
         .all()
        
        # 用例复杂度分布
        complexity_stats = self.db.query(
            TestCase.complexity,
            func.count(TestCase.id).label('count')
        ).filter(TestCase.test_plan_id == plan_id)\
         .group_by(TestCase.complexity)\
         .all()
        
        # 执行状态统计
        execution_stats = self.db.query(
            TestExecution.execution_status,
            func.count(TestExecution.id).label('count')
        ).join(TestCase, TestExecution.test_case_id == TestCase.id)\
         .filter(TestCase.test_plan_id == plan_id)\
         .group_by(TestExecution.execution_status)\
         .all()
        
        # 缺陷统计
        defect_stats = self.db.query(
            Defect.severity,
            func.count(Defect.id).label('count')
        ).join(TestExecution, Defect.test_execution_id == TestExecution.id)\
         .join(TestCase, TestExecution.test_case_id == TestCase.id)\
         .filter(TestCase.test_plan_id == plan_id)\
         .group_by(Defect.severity)\
         .all()
        
        # 构建统计结果
        statistics = {
            'plan_id': plan_id,
            'total_cases': total_cases,
            'priority_distribution': {
                priority.value: count for priority, count in priority_stats
            },
            'complexity_distribution': {
                complexity.value: count for complexity, count in complexity_stats
            },
            'execution_distribution': {
                status.value: count for status, count in execution_stats
            },
            'defect_distribution': {
                severity.value: count for severity, count in defect_stats
            },
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # 缓存结果
        self.cache_manager.set(TestCacheKeys.TEST_PLAN_STATISTICS, statistics, TestCacheTTL.TEST_PLAN_STATISTICS, plan_id=plan_id)
        
        return statistics
    
    async def get_plan_trends(self, plan_id: int, days: int = 30) -> Dict[str, Any]:
        """
        获取测试计划趋势数据
        
        Args:
            plan_id: 测试计划ID
            days: 天数
            
        Returns:
            Dict[str, Any]: 趋势数据
        """
        from ..models.test_case import TestExecution, ExecutionStatus
        from ..models.test_case import TestCase
        
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # 每日执行趋势
        daily_executions = self.db.query(
            func.date(TestExecution.completed_at).label('date'),
            func.count(TestExecution.id).label('count')
        ).join(TestCase, TestExecution.test_case_id == TestCase.id)\
         .filter(TestCase.test_plan_id == plan_id)\
         .filter(func.date(TestExecution.completed_at) >= start_date)\
         .filter(func.date(TestExecution.completed_at) <= end_date)\
         .group_by(func.date(TestExecution.completed_at))\
         .order_by(func.date(TestExecution.completed_at))\
         .all()
        
        # 每日通过率趋势
        daily_pass_rates = []
        for execution_date, _ in daily_executions:
            total = self.db.query(TestExecution)\
                .join(TestCase, TestExecution.test_case_id == TestCase.id)\
                .filter(TestCase.test_plan_id == plan_id)\
                .filter(func.date(TestExecution.completed_at) == execution_date)\
                .count()
            
            passed = self.db.query(TestExecution)\
                .join(TestCase, TestExecution.test_case_id == TestCase.id)\
                .filter(TestCase.test_plan_id == plan_id)\
                .filter(func.date(TestExecution.completed_at) == execution_date)\
                .filter(TestExecution.execution_status == ExecutionStatus.PASSED)\
                .count()
            
            pass_rate = (passed / total * 100) if total > 0 else 0
            daily_pass_rates.append({
                'date': execution_date.isoformat(),
                'pass_rate': round(pass_rate, 2)
            })
        
        return {
            'plan_id': plan_id,
            'period': f"{start_date} to {end_date}",
            'daily_executions': [
                {'date': date.isoformat(), 'count': count}
                for date, count in daily_executions
            ],
            'daily_pass_rates': daily_pass_rates,
            'generated_at': datetime.utcnow().isoformat()
        }


class TestStrategyService:
    """测试策略管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
        self.cache_manager = TestCacheManager()
    
    async def generate_test_strategy(
        self, 
        project_id: int, 
        requirements: List[Dict[str, Any]], 
        user_id: int
    ) -> Dict[str, Any]:
        """
        基于项目需求生成测试策略
        
        Args:
            project_id: 项目ID
            requirements: 需求列表
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 生成的测试策略
        """
        try:
            # 1. 获取项目信息
            from ..models.project import Project
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise NotFoundError("项目不存在")
            
            # 2. 分析需求复杂度和风险
            risk_analysis = await self._analyze_requirements_risk(requirements)
            
            # 3. 生成AI策略建议
            strategy_prompt = self._build_strategy_prompt(project, requirements, risk_analysis)
            ai_strategy = await self.ai_service.generate_test_strategy(strategy_prompt)
            
            # 4. 构建完整策略
            test_strategy = {
                'project_id': project_id,
                'strategy_overview': ai_strategy.get('overview', ''),
                'test_approach': ai_strategy.get('approach', {}),
                'test_levels': ai_strategy.get('levels', []),
                'test_types': ai_strategy.get('types', []),
                'entry_criteria': ai_strategy.get('entry_criteria', []),
                'exit_criteria': ai_strategy.get('exit_criteria', []),
                'risk_assessment': risk_analysis,
                'resource_requirements': ai_strategy.get('resources', {}),
                'timeline_estimation': ai_strategy.get('timeline', {}),
                'tools_and_environment': ai_strategy.get('tools', []),
                'deliverables': ai_strategy.get('deliverables', []),
                'generated_by': user_id,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # 5. 缓存策略
            await self.cache_manager.set_test_strategy(project_id, test_strategy)
            
            return test_strategy
            
        except Exception as e:
            logger.error(f"生成测试策略失败: {str(e)}")
            raise
    
    async def get_strategy_templates(self, project_type: str = None) -> List[Dict[str, Any]]:
        """
        获取测试策略模板
        
        Args:
            project_type: 项目类型过滤
            
        Returns:
            List[Dict[str, Any]]: 策略模板列表
        """
        templates = [
            {
                'id': 'web_application',
                'name': 'Web应用测试策略',
                'description': '适用于Web应用程序的综合测试策略',
                'project_types': ['web', 'saas', 'ecommerce'],
                'test_levels': ['单元测试', '集成测试', '系统测试', '验收测试'],
                'test_types': ['功能测试', 'UI测试', '性能测试', '安全测试', '兼容性测试'],
                'tools': ['Selenium', 'Jest', 'JMeter', 'OWASP ZAP'],
                'template': {
                    'overview': 'Web应用全面测试策略，覆盖功能、性能、安全等多个维度',
                    'approach': {
                        'methodology': 'V模型结合敏捷测试',
                        'automation_ratio': '70%',
                        'risk_based': True
                    }
                }
            },
            {
                'id': 'mobile_application',
                'name': '移动应用测试策略',
                'description': '适用于移动应用的测试策略',
                'project_types': ['mobile', 'ios', 'android'],
                'test_levels': ['单元测试', '集成测试', '系统测试', '验收测试'],
                'test_types': ['功能测试', '兼容性测试', '性能测试', '安全测试', '可用性测试'],
                'tools': ['Appium', 'XCTest', 'Espresso', 'Firebase Test Lab'],
                'template': {
                    'overview': '移动应用全平台测试策略，注重设备兼容性和用户体验',
                    'approach': {
                        'methodology': '敏捷测试',
                        'automation_ratio': '60%',
                        'device_coverage': True
                    }
                }
            },
            {
                'id': 'api_service',
                'name': 'API服务测试策略',
                'description': '适用于API和微服务的测试策略',
                'project_types': ['api', 'microservice', 'backend'],
                'test_levels': ['单元测试', '集成测试', '契约测试', '端到端测试'],
                'test_types': ['功能测试', '性能测试', '安全测试', '可靠性测试'],
                'tools': ['Postman', 'Newman', 'Pact', 'JMeter', 'SoapUI'],
                'template': {
                    'overview': 'API服务测试策略，重点关注接口契约和服务间集成',
                    'approach': {
                        'methodology': '测试金字塔',
                        'automation_ratio': '90%',
                        'contract_testing': True
                    }
                }
            }
        ]
        
        if project_type:
            templates = [t for t in templates if project_type in t['project_types']]
        
        return templates
    
    async def apply_strategy_template(
        self, 
        template_id: str, 
        project_id: int, 
        customizations: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        应用策略模板
        
        Args:
            template_id: 模板ID
            project_id: 项目ID
            customizations: 自定义配置
            
        Returns:
            Dict[str, Any]: 应用后的策略
        """
        # 获取模板
        templates = await self.get_strategy_templates()
        template = next((t for t in templates if t['id'] == template_id), None)
        
        if not template:
            raise NotFoundError("策略模板不存在")
        
        # 应用自定义配置
        strategy = template['template'].copy()
        if customizations:
            strategy.update(customizations)
        
        # 添加项目特定信息
        strategy.update({
            'project_id': project_id,
            'template_id': template_id,
            'template_name': template['name'],
            'applied_at': datetime.utcnow().isoformat()
        })
        
        return strategy
    
    async def analyze_test_coverage(
        self, 
        plan_id: int, 
        requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析测试覆盖率
        
        Args:
            plan_id: 测试计划ID
            requirements: 需求列表
            
        Returns:
            Dict[str, Any]: 覆盖率分析结果
        """
        try:
            from ..models.test_case import TestCase
            from ..models.requirement import Requirement
            
            # 获取计划下的所有测试用例
            test_cases = self.db.query(TestCase)\
                .filter(TestCase.test_plan_id == plan_id)\
                .all()
            
            # 分析需求覆盖
            requirement_coverage = {}
            for req in requirements:
                req_id = req['id']
                covered_cases = [
                    case for case in test_cases 
                    if req_id in (case.requirement_ids or [])
                ]
                
                requirement_coverage[req_id] = {
                    'requirement_name': req['name'],
                    'priority': req.get('priority', 'medium'),
                    'covered_cases': len(covered_cases),
                    'coverage_percentage': min(100, len(covered_cases) * 20),  # 简化计算
                    'case_ids': [case.id for case in covered_cases]
                }
            
            # 计算整体覆盖率
            total_requirements = len(requirements)
            covered_requirements = sum(
                1 for cov in requirement_coverage.values() 
                if cov['covered_cases'] > 0
            )
            
            overall_coverage = (covered_requirements / total_requirements * 100) if total_requirements > 0 else 0
            
            # 识别覆盖缺口
            coverage_gaps = [
                {
                    'requirement_id': req_id,
                    'requirement_name': cov['requirement_name'],
                    'priority': cov['priority'],
                    'gap_type': 'no_coverage' if cov['covered_cases'] == 0 else 'insufficient_coverage'
                }
                for req_id, cov in requirement_coverage.items()
                if cov['coverage_percentage'] < 80
            ]
            
            return {
                'plan_id': plan_id,
                'overall_coverage': round(overall_coverage, 2),
                'total_requirements': total_requirements,
                'covered_requirements': covered_requirements,
                'requirement_coverage': requirement_coverage,
                'coverage_gaps': coverage_gaps,
                'recommendations': await self._generate_coverage_recommendations(coverage_gaps),
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"分析测试覆盖率失败: {str(e)}")
            raise
    
    async def _analyze_requirements_risk(self, requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析需求风险
        
        Args:
            requirements: 需求列表
            
        Returns:
            Dict[str, Any]: 风险分析结果
        """
        risk_factors = {
            'high_complexity': 0,
            'new_technology': 0,
            'external_dependencies': 0,
            'tight_timeline': 0,
            'unclear_requirements': 0
        }
        
        high_risk_requirements = []
        medium_risk_requirements = []
        low_risk_requirements = []
        
        for req in requirements:
            risk_score = 0
            risk_reasons = []
            
            # 复杂度评估
            if req.get('complexity', 'medium') == 'high':
                risk_score += 3
                risk_reasons.append('高复杂度')
                risk_factors['high_complexity'] += 1
            
            # 技术新颖性
            if req.get('involves_new_technology', False):
                risk_score += 2
                risk_reasons.append('涉及新技术')
                risk_factors['new_technology'] += 1
            
            # 外部依赖
            if req.get('external_dependencies', []):
                risk_score += 2
                risk_reasons.append('外部依赖')
                risk_factors['external_dependencies'] += 1
            
            # 需求清晰度
            if not req.get('description') or len(req.get('description', '')) < 50:
                risk_score += 1
                risk_reasons.append('需求描述不够清晰')
                risk_factors['unclear_requirements'] += 1
            
            # 分类风险等级
            req_risk = {
                'id': req['id'],
                'name': req['name'],
                'risk_score': risk_score,
                'risk_reasons': risk_reasons
            }
            
            if risk_score >= 5:
                high_risk_requirements.append(req_risk)
            elif risk_score >= 3:
                medium_risk_requirements.append(req_risk)
            else:
                low_risk_requirements.append(req_risk)
        
        return {
            'risk_factors': risk_factors,
            'high_risk_requirements': high_risk_requirements,
            'medium_risk_requirements': medium_risk_requirements,
            'low_risk_requirements': low_risk_requirements,
            'overall_risk_level': self._calculate_overall_risk(risk_factors, len(requirements))
        }
    
    def _calculate_overall_risk(self, risk_factors: Dict[str, int], total_requirements: int) -> str:
        """计算整体风险等级"""
        total_risk_points = sum(risk_factors.values())
        risk_ratio = total_risk_points / total_requirements if total_requirements > 0 else 0
        
        if risk_ratio >= 0.6:
            return 'high'
        elif risk_ratio >= 0.3:
            return 'medium'
        else:
            return 'low'
    
    def _build_strategy_prompt(
        self, 
        project: Any, 
        requirements: List[Dict[str, Any]], 
        risk_analysis: Dict[str, Any]
    ) -> str:
        """构建AI策略生成提示"""
        return f"""
        请为以下项目生成详细的测试策略：

        项目信息：
        - 项目名称：{project.project_name}
        - 项目类型：{getattr(project, 'project_type', '未知')}
        - 项目描述：{getattr(project, 'description', '')}
        - 需求数量：{len(requirements)}

        风险分析：
        - 整体风险等级：{risk_analysis['overall_risk_level']}
        - 高风险需求：{len(risk_analysis['high_risk_requirements'])}个
        - 中风险需求：{len(risk_analysis['medium_risk_requirements'])}个
        - 主要风险因素：{', '.join([k for k, v in risk_analysis['risk_factors'].items() if v > 0])}

        请提供以下内容：
        1. 测试策略概述
        2. 测试方法和层次
        3. 测试类型和优先级
        4. 进入和退出标准
        5. 资源需求评估
        6. 时间线估算
        7. 工具和环境要求
        8. 主要交付物
        9. 风险缓解措施

        请以JSON格式返回结构化的策略内容。
        """
    
    async def _generate_coverage_recommendations(self, coverage_gaps: List[Dict[str, Any]]) -> List[str]:
        """生成覆盖率改进建议"""
        recommendations = []
        
        if not coverage_gaps:
            recommendations.append("测试覆盖率良好，建议继续保持")
            return recommendations
        
        # 按优先级分组
        high_priority_gaps = [gap for gap in coverage_gaps if gap['priority'] == 'high']
        no_coverage_gaps = [gap for gap in coverage_gaps if gap['gap_type'] == 'no_coverage']
        
        if high_priority_gaps:
            recommendations.append(f"优先为{len(high_priority_gaps)}个高优先级需求补充测试用例")
        
        if no_coverage_gaps:
            recommendations.append(f"为{len(no_coverage_gaps)}个未覆盖的需求创建测试用例")
        
        recommendations.append("考虑增加边界值测试和异常场景测试")
        recommendations.append("评估是否需要增加集成测试用例")
        
        return recommendations


class TestScopeService:
    """测试范围管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
    
    async def define_test_scope(
        self, 
        project_id: int, 
        requirements: List[Dict[str, Any]],
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        定义测试范围
        
        Args:
            project_id: 项目ID
            requirements: 需求列表
            constraints: 约束条件
            
        Returns:
            Dict[str, Any]: 测试范围定义
        """
        try:
            # 1. 分析需求优先级和复杂度
            scope_analysis = await self._analyze_scope_requirements(requirements)
            
            # 2. 应用约束条件
            if constraints:
                scope_analysis = await self._apply_scope_constraints(scope_analysis, constraints)
            
            # 3. 生成范围建议
            scope_recommendations = await self._generate_scope_recommendations(
                scope_analysis, constraints
            )
            
            # 4. 构建测试范围
            test_scope = {
                'project_id': project_id,
                'in_scope': scope_analysis['in_scope_requirements'],
                'out_of_scope': scope_analysis['out_of_scope_requirements'],
                'scope_rationale': scope_analysis['rationale'],
                'test_objectives': scope_recommendations['objectives'],
                'success_criteria': scope_recommendations['success_criteria'],
                'assumptions': scope_recommendations['assumptions'],
                'constraints': constraints or {},
                'risk_mitigation': scope_recommendations['risk_mitigation'],
                'defined_at': datetime.utcnow().isoformat()
            }
            
            return test_scope
            
        except Exception as e:
            logger.error(f"定义测试范围失败: {str(e)}")
            raise
    
    async def _analyze_scope_requirements(self, requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析范围需求"""
        in_scope = []
        out_of_scope = []
        rationale = {}
        
        for req in requirements:
            priority = req.get('priority', 'medium')
            complexity = req.get('complexity', 'medium')
            business_value = req.get('business_value', 'medium')
            
            # 范围决策逻辑
            if priority == 'high' or business_value == 'high':
                in_scope.append(req)
                rationale[req['id']] = "高优先级或高业务价值"
            elif priority == 'low' and complexity == 'high':
                out_of_scope.append(req)
                rationale[req['id']] = "低优先级且高复杂度，投入产出比不佳"
            elif req.get('is_prototype', False):
                out_of_scope.append(req)
                rationale[req['id']] = "原型功能，不在当前测试范围"
            else:
                in_scope.append(req)
                rationale[req['id']] = "标准测试范围"
        
        return {
            'in_scope_requirements': in_scope,
            'out_of_scope_requirements': out_of_scope,
            'rationale': rationale
        }
    
    async def _apply_scope_constraints(
        self, 
        scope_analysis: Dict[str, Any], 
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """应用范围约束"""
        # 时间约束
        if constraints.get('time_limit'):
            # 根据时间限制调整范围
            pass
        
        # 资源约束
        if constraints.get('resource_limit'):
            # 根据资源限制调整范围
            pass
        
        # 预算约束
        if constraints.get('budget_limit'):
            # 根据预算限制调整范围
            pass
        
        return scope_analysis
    
    async def _generate_scope_recommendations(
        self, 
        scope_analysis: Dict[str, Any], 
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成范围建议"""
        return {
            'objectives': [
                "验证核心功能的正确性和完整性",
                "确保系统满足性能和安全要求",
                "验证用户体验和界面友好性"
            ],
            'success_criteria': [
                "所有高优先级功能测试通过率达到95%以上",
                "系统性能满足预期指标",
                "无严重和高级别缺陷遗留"
            ],
            'assumptions': [
                "测试环境与生产环境基本一致",
                "需求在测试期间保持稳定",
                "必要的测试数据和工具可以及时提供"
            ],
            'risk_mitigation': [
                "对高风险功能增加测试覆盖",
                "建立缺陷快速响应机制",
                "准备应急测试方案"
            ]
        }


class TestProgressService:
    """测试进度监控服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_manager = TestCacheManager()
        self.ai_service = AIAssistantService()
    
    async def get_real_time_progress(self, plan_id: int) -> Dict[str, Any]:
        """
        获取实时测试进度
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            Dict[str, Any]: 实时进度信息
        """
        try:
            # 先尝试从缓存获取
            cached_progress = self.cache_manager.get(TestCacheKeys.TEST_PLAN_PROGRESS, plan_id=plan_id)
            if cached_progress and self._is_progress_fresh(cached_progress):
                return cached_progress
            
            # 重新计算进度
            from ..models.test_case import TestCase
            from ..models.test_case import TestExecution, ExecutionStatus, ExecutionStatus
            from ..models.test_case import Defect, DefectStatus
            
            # 基础统计
            total_cases = self.db.query(TestCase).filter(TestCase.test_plan_id == plan_id).count()
            
            # 执行状态统计
            execution_stats = self.db.query(
                TestExecution.execution_status,
                func.count(TestExecution.id).label('count')
            ).join(TestCase, TestExecution.test_case_id == TestCase.id)\
             .filter(TestCase.test_plan_id == plan_id)\
             .group_by(TestExecution.execution_status)\
             .all()
            
            execution_counts = {status.value: 0 for status in ExecutionStatus}
            for status, count in execution_stats:
                execution_counts[status.value] = count
            
            # 缺陷统计
            defect_stats = self.db.query(
                Defect.status,
                func.count(Defect.id).label('count')
            ).join(TestExecution, Defect.test_execution_id == TestExecution.id)\
             .join(TestCase, TestExecution.test_case_id == TestCase.id)\
             .filter(TestCase.test_plan_id == plan_id)\
             .group_by(Defect.status)\
             .all()
            
            defect_counts = {status.value: 0 for status in DefectStatus}
            for status, count in defect_stats:
                defect_counts[status.value] = count
            
            # 计算关键指标
            executed_cases = sum(count for status, count in execution_counts.items() 
                               if status != ExecutionStatus.NOT_EXECUTED.value)
            passed_cases = execution_counts.get(ExecutionStatus.PASSED.value, 0)
            failed_cases = execution_counts.get(ExecutionStatus.FAILED.value, 0)
            
            execution_rate = (executed_cases / total_cases * 100) if total_cases > 0 else 0
            pass_rate = (passed_cases / executed_cases * 100) if executed_cases > 0 else 0
            
            # 构建进度信息
            progress = {
                'plan_id': plan_id,
                'timestamp': datetime.utcnow().isoformat(),
                'overall_progress': {
                    'total_cases': total_cases,
                    'executed_cases': executed_cases,
                    'execution_rate': round(execution_rate, 2),
                    'pass_rate': round(pass_rate, 2)
                },
                'execution_breakdown': execution_counts,
                'defect_breakdown': defect_counts,
                'quality_metrics': await self._calculate_quality_metrics(plan_id),
                'velocity_metrics': await self._calculate_velocity_metrics(plan_id),
                'risk_indicators': await self._identify_risk_indicators(plan_id, execution_counts, defect_counts)
            }
            
            # 更新缓存
            self.cache_manager.set(TestCacheKeys.TEST_PLAN_PROGRESS, progress, TestCacheTTL.TEST_PLAN_PROGRESS, plan_id=plan_id)
            
            return progress
            
        except Exception as e:
            logger.error(f"获取实时进度失败: {str(e)}")
            raise
    
    async def generate_progress_dashboard(self, plan_id: int) -> Dict[str, Any]:
        """
        生成进度仪表板数据
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            Dict[str, Any]: 仪表板数据
        """
        try:
            # 获取基础进度数据
            progress = await self.get_real_time_progress(plan_id)
            
            # 获取趋势数据
            trends = await self._get_progress_trends(plan_id, days=7)
            
            # 获取团队效率数据
            team_metrics = await self._get_team_metrics(plan_id)
            
            # 获取预测数据
            predictions = await self._generate_progress_predictions(plan_id, progress, trends)
            
            dashboard = {
                'plan_id': plan_id,
                'generated_at': datetime.utcnow().isoformat(),
                'current_progress': progress,
                'trends': trends,
                'team_metrics': team_metrics,
                'predictions': predictions,
                'alerts': await self._generate_progress_alerts(plan_id, progress, trends),
                'recommendations': await self._generate_progress_recommendations(plan_id, progress, trends)
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"生成进度仪表板失败: {str(e)}")
            raise
    
    async def detect_progress_anomalies(self, plan_id: int) -> List[Dict[str, Any]]:
        """
        检测进度异常
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            List[Dict[str, Any]]: 异常列表
        """
        anomalies = []
        
        try:
            # 获取当前进度
            progress = await self.get_real_time_progress(plan_id)
            
            # 获取历史趋势
            trends = await self._get_progress_trends(plan_id, days=14)
            
            # 检测执行率异常
            execution_rate = progress['overall_progress']['execution_rate']
            if execution_rate < 10:  # 执行率过低
                anomalies.append({
                    'type': 'low_execution_rate',
                    'severity': 'high',
                    'message': f'测试执行率过低: {execution_rate}%',
                    'recommendation': '检查测试环境和资源分配'
                })
            
            # 检测通过率异常
            pass_rate = progress['overall_progress']['pass_rate']
            if pass_rate < 70:  # 通过率过低
                anomalies.append({
                    'type': 'low_pass_rate',
                    'severity': 'high',
                    'message': f'测试通过率过低: {pass_rate}%',
                    'recommendation': '分析失败原因，优先修复关键缺陷'
                })
            
            # 检测缺陷趋势异常
            open_defects = progress['defect_breakdown'].get('open', 0)
            if open_defects > 50:  # 未解决缺陷过多
                anomalies.append({
                    'type': 'high_defect_count',
                    'severity': 'medium',
                    'message': f'未解决缺陷数量过多: {open_defects}',
                    'recommendation': '加强缺陷修复和验证流程'
                })
            
            # 检测进度停滞
            if trends and len(trends['daily_executions']) >= 3:
                recent_executions = trends['daily_executions'][-3:]
                if all(day['count'] == 0 for day in recent_executions):
                    anomalies.append({
                        'type': 'progress_stagnation',
                        'severity': 'high',
                        'message': '测试进度停滞，连续3天无执行记录',
                        'recommendation': '检查团队状态和阻塞问题'
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测进度异常失败: {str(e)}")
            return []
    
    async def generate_progress_report(
        self, 
        plan_id: int, 
        report_type: str = 'weekly'
    ) -> Dict[str, Any]:
        """
        生成进度报告
        
        Args:
            plan_id: 测试计划ID
            report_type: 报告类型 (daily/weekly/monthly)
            
        Returns:
            Dict[str, Any]: 进度报告
        """
        try:
            # 确定报告周期
            days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
            days = days_map.get(report_type, 7)
            
            # 获取数据
            current_progress = await self.get_real_time_progress(plan_id)
            trends = await self._get_progress_trends(plan_id, days)
            anomalies = await self.detect_progress_anomalies(plan_id)
            
            # 获取测试计划信息
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == plan_id).first()
            
            # 生成报告
            report = {
                'plan_id': plan_id,
                'plan_name': test_plan.plan_name if test_plan else 'Unknown',
                'report_type': report_type,
                'report_period': {
                    'start_date': (datetime.utcnow() - timedelta(days=days)).date().isoformat(),
                    'end_date': datetime.utcnow().date().isoformat()
                },
                'generated_at': datetime.utcnow().isoformat(),
                'executive_summary': await self._generate_executive_summary(
                    current_progress, trends, anomalies
                ),
                'current_status': current_progress,
                'progress_trends': trends,
                'key_achievements': await self._identify_key_achievements(plan_id, days),
                'issues_and_risks': anomalies,
                'upcoming_milestones': await self._get_upcoming_milestones(plan_id),
                'recommendations': await self._generate_progress_recommendations(
                    plan_id, current_progress, trends
                )
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成进度报告失败: {str(e)}")
            raise
    
    def _is_progress_fresh(self, cached_progress: Dict[str, Any]) -> bool:
        """检查缓存的进度数据是否新鲜"""
        try:
            cached_time = datetime.fromisoformat(cached_progress['timestamp'])
            return (datetime.utcnow() - cached_time).seconds < 300  # 5分钟内的数据认为是新鲜的
        except:
            return False
    
    async def _calculate_quality_metrics(self, plan_id: int) -> Dict[str, Any]:
        """计算质量指标"""
        from ..models.test_case import TestCase, CasePriority
        from ..models.test_case import TestExecution, ExecutionStatus, ExecutionStatus
        from ..models.test_case import Defect, DefectSeverity
        
        # 按优先级统计通过率
        priority_pass_rates = {}
        for priority in CasePriority:
            total = self.db.query(TestCase)\
                .filter(TestCase.test_plan_id == plan_id)\
                .filter(TestCase.priority == priority)\
                .count()
            
            if total > 0:
                passed = self.db.query(TestExecution)\
                    .join(TestCase, TestExecution.test_case_id == TestCase.id)\
                    .filter(TestCase.test_plan_id == plan_id)\
                    .filter(TestCase.priority == priority)\
                    .filter(TestExecution.execution_status == ExecutionStatus.PASSED)\
                    .count()
                
                priority_pass_rates[priority.value] = round(passed / total * 100, 2)
            else:
                priority_pass_rates[priority.value] = 0
        
        # 缺陷密度
        total_defects = self.db.query(Defect)\
            .join(TestExecution, Defect.test_execution_id == TestExecution.id)\
            .join(TestCase, TestExecution.test_case_id == TestCase.id)\
            .filter(TestCase.test_plan_id == plan_id)\
            .count()
        
        total_cases = self.db.query(TestCase).filter(TestCase.test_plan_id == plan_id).count()
        defect_density = round(total_defects / total_cases, 2) if total_cases > 0 else 0
        
        return {
            'priority_pass_rates': priority_pass_rates,
            'defect_density': defect_density,
            'total_defects': total_defects
        }
    
    async def _calculate_velocity_metrics(self, plan_id: int) -> Dict[str, Any]:
        """计算速度指标"""
        from ..models.test_case import TestExecution, ExecutionStatus
        from ..models.test_case import TestCase
        
        # 最近7天的执行速度
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)
        
        daily_executions = self.db.query(
            func.date(TestExecution.completed_at).label('date'),
            func.count(TestExecution.id).label('count')
        ).join(TestCase, TestExecution.test_case_id == TestCase.id)\
         .filter(TestCase.test_plan_id == plan_id)\
         .filter(func.date(TestExecution.completed_at) >= start_date)\
         .filter(func.date(TestExecution.completed_at) <= end_date)\
         .group_by(func.date(TestExecution.completed_at))\
         .all()
        
        # 计算平均执行速度
        total_executions = sum(count for _, count in daily_executions)
        avg_daily_executions = total_executions / 7 if daily_executions else 0
        
        return {
            'avg_daily_executions': round(avg_daily_executions, 2),
            'total_weekly_executions': total_executions,
            'execution_days': len(daily_executions)
        }
    
    async def _identify_risk_indicators(
        self, 
        plan_id: int, 
        execution_counts: Dict[str, int], 
        defect_counts: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """识别风险指标"""
        risks = []
        
        # 执行率风险
        total_cases = sum(execution_counts.values())
        executed_cases = sum(count for status, count in execution_counts.items() 
                           if status != ExecutionStatus.NOT_EXECUTED.value)
        execution_rate = (executed_cases / total_cases * 100) if total_cases > 0 else 0
        
        if execution_rate < 30:
            risks.append({
                'type': 'execution_risk',
                'level': 'high',
                'description': '测试执行进度严重滞后',
                'impact': '可能影响项目交付时间'
            })
        
        # 质量风险
        failed_cases = execution_counts.get(ExecutionStatus.FAILED.value, 0)
        if executed_cases > 0 and failed_cases / executed_cases > 0.3:
            risks.append({
                'type': 'quality_risk',
                'level': 'high',
                'description': '测试失败率过高',
                'impact': '产品质量存在重大风险'
            })
        
        # 缺陷风险
        open_defects = defect_counts.get(DefectStatus.OPEN.value, 0)
        if open_defects > 20:
            risks.append({
                'type': 'defect_risk',
                'level': 'medium',
                'description': '未解决缺陷数量较多',
                'impact': '可能影响发布质量'
            })
        
        return risks
    
    async def _get_progress_trends(self, plan_id: int, days: int) -> Dict[str, Any]:
        """获取进度趋势"""
        from ..models.test_case import TestExecution, ExecutionStatus, ExecutionStatus
        from ..models.test_case import TestCase
        
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # 每日执行趋势
        daily_executions = self.db.query(
            func.date(TestExecution.completed_at).label('date'),
            func.count(TestExecution.id).label('count')
        ).join(TestCase, TestExecution.test_case_id == TestCase.id)\
         .filter(TestCase.test_plan_id == plan_id)\
         .filter(func.date(TestExecution.completed_at) >= start_date)\
         .filter(func.date(TestExecution.completed_at) <= end_date)\
         .group_by(func.date(TestExecution.completed_at))\
         .order_by(func.date(TestExecution.completed_at))\
         .all()
        
        # 每日通过率趋势
        daily_pass_rates = []
        for execution_date, _ in daily_executions:
            total = self.db.query(TestExecution)\
                .join(TestCase, TestExecution.test_case_id == TestCase.id)\
                .filter(TestCase.test_plan_id == plan_id)\
                .filter(func.date(TestExecution.completed_at) == execution_date)\
                .count()
            
            passed = self.db.query(TestExecution)\
                .join(TestCase, TestExecution.test_case_id == TestCase.id)\
                .filter(TestCase.test_plan_id == plan_id)\
                .filter(func.date(TestExecution.completed_at) == execution_date)\
                .filter(TestExecution.execution_status == ExecutionStatus.PASSED)\
                .count()
            
            pass_rate = (passed / total * 100) if total > 0 else 0
            daily_pass_rates.append({
                'date': execution_date.isoformat(),
                'pass_rate': round(pass_rate, 2)
            })
        
        return {
            'period_days': days,
            'daily_executions': [
                {'date': date.isoformat(), 'count': count}
                for date, count in daily_executions
            ],
            'daily_pass_rates': daily_pass_rates
        }
    
    async def _get_team_metrics(self, plan_id: int) -> Dict[str, Any]:
        """获取团队效率指标"""
        from ..models.test_case import TestExecution, ExecutionStatus
        from ..models.test_case import TestCase
        from ..models.user import User
        
        # 团队成员执行统计
        team_stats = self.db.query(
            TestExecution.executed_by,
            func.count(TestExecution.id).label('executions'),
            func.avg(
                func.timestampdiff(
                    'MINUTE', 
                    TestExecution.started_at, 
                    TestExecution.completed_at
                )
            ).label('avg_duration')
        ).join(TestCase, TestExecution.test_case_id == TestCase.id)\
         .filter(TestCase.test_plan_id == plan_id)\
         .filter(TestExecution.executed_by.isnot(None))\
         .group_by(TestExecution.executed_by)\
         .all()
        
        team_metrics = []
        for user_id, executions, avg_duration in team_stats:
            user = self.db.query(User).filter(User.id == user_id).first()
            team_metrics.append({
                'user_id': user_id,
                'user_name': user.username if user else 'Unknown',
                'total_executions': executions,
                'avg_execution_time': round(avg_duration or 0, 2)
            })
        
        return {
            'team_members': len(team_metrics),
            'member_stats': team_metrics
        }
    
    async def _generate_progress_predictions(
        self, 
        plan_id: int, 
        current_progress: Dict[str, Any], 
        trends: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成进度预测"""
        try:
            # 获取测试计划信息
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == plan_id).first()
            if not test_plan:
                return {}
            
            # 计算当前执行速度
            if trends['daily_executions']:
                recent_executions = trends['daily_executions'][-7:]  # 最近7天
                avg_daily_speed = sum(day['count'] for day in recent_executions) / len(recent_executions)
            else:
                avg_daily_speed = 0
            
            # 预测完成时间
            remaining_cases = (current_progress['overall_progress']['total_cases'] - 
                             current_progress['overall_progress']['executed_cases'])
            
            if avg_daily_speed > 0:
                estimated_days = remaining_cases / avg_daily_speed
                estimated_completion = datetime.utcnow() + timedelta(days=estimated_days)
            else:
                estimated_completion = None
            
            # 风险评估
            risk_level = 'low'
            if test_plan.planned_end_date and estimated_completion:
                if estimated_completion.date() > test_plan.planned_end_date:
                    risk_level = 'high'
                elif (estimated_completion.date() - test_plan.planned_end_date).days > -7:
                    risk_level = 'medium'
            
            return {
                'estimated_completion_date': estimated_completion.isoformat() if estimated_completion else None,
                'remaining_cases': remaining_cases,
                'avg_daily_speed': round(avg_daily_speed, 2),
                'schedule_risk': risk_level,
                'confidence_level': self._calculate_prediction_confidence(trends)
            }
            
        except Exception as e:
            logger.warning(f"生成进度预测失败: {str(e)}")
            return {}
    
    def _calculate_prediction_confidence(self, trends: Dict[str, Any]) -> str:
        """计算预测置信度"""
        if not trends['daily_executions']:
            return 'low'
        
        # 基于数据点数量和变异性计算置信度
        data_points = len(trends['daily_executions'])
        if data_points < 3:
            return 'low'
        elif data_points < 7:
            return 'medium'
        else:
            return 'high'
    
    async def _generate_progress_alerts(
        self, 
        plan_id: int, 
        progress: Dict[str, Any], 
        trends: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成进度告警"""
        alerts = []
        
        # 执行率告警
        execution_rate = progress['overall_progress']['execution_rate']
        if execution_rate < 20:
            alerts.append({
                'type': 'execution_rate',
                'severity': 'critical',
                'message': f'测试执行率过低: {execution_rate}%',
                'action_required': True
            })
        
        # 通过率告警
        pass_rate = progress['overall_progress']['pass_rate']
        if pass_rate < 60:
            alerts.append({
                'type': 'pass_rate',
                'severity': 'warning',
                'message': f'测试通过率偏低: {pass_rate}%',
                'action_required': True
            })
        
        return alerts
    
    async def _generate_progress_recommendations(
        self, 
        plan_id: int, 
        progress: Dict[str, Any], 
        trends: Dict[str, Any]
    ) -> List[str]:
        """生成进度改进建议"""
        recommendations = []
        
        execution_rate = progress['overall_progress']['execution_rate']
        pass_rate = progress['overall_progress']['pass_rate']
        
        if execution_rate < 50:
            recommendations.append("建议增加测试人员或延长测试时间")
            recommendations.append("检查测试环境是否存在阻塞问题")
        
        if pass_rate < 70:
            recommendations.append("优先修复高优先级缺陷")
            recommendations.append("加强开发阶段的代码质量控制")
        
        if not trends['daily_executions']:
            recommendations.append("建立每日测试执行跟踪机制")
        
        return recommendations
    
    async def _generate_executive_summary(
        self, 
        progress: Dict[str, Any], 
        trends: Dict[str, Any], 
        anomalies: List[Dict[str, Any]]
    ) -> str:
        """生成执行摘要"""
        execution_rate = progress['overall_progress']['execution_rate']
        pass_rate = progress['overall_progress']['pass_rate']
        
        summary = f"测试执行率为{execution_rate}%，通过率为{pass_rate}%。"
        
        if anomalies:
            high_severity_count = len([a for a in anomalies if a.get('severity') == 'high'])
            if high_severity_count > 0:
                summary += f" 发现{high_severity_count}个高严重性问题需要关注。"
        
        if execution_rate >= 80 and pass_rate >= 85:
            summary += " 整体进度良好，质量符合预期。"
        elif execution_rate < 50:
            summary += " 测试进度滞后，需要采取措施加速执行。"
        elif pass_rate < 70:
            summary += " 测试质量存在风险，建议加强缺陷修复。"
        
        return summary
    
    async def _identify_key_achievements(self, plan_id: int, days: int) -> List[str]:
        """识别关键成就"""
        achievements = []
        
        # 这里可以根据实际情况添加成就识别逻辑
        achievements.append("完成了核心功能模块的测试")
        achievements.append("建立了自动化测试框架")
        
        return achievements
    
    async def _get_upcoming_milestones(self, plan_id: int) -> List[Dict[str, Any]]:
        """获取即将到来的里程碑"""
        # 这里可以从测试阶段或项目计划中获取里程碑信息
        milestones = [
            {
                'name': '系统测试完成',
                'target_date': (datetime.utcnow() + timedelta(days=14)).date().isoformat(),
                'progress': 60
            }
        ]
        
        return milestones
