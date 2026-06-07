"""
测试用例管理服务

本模块实现测试用例的完整生命周期管理，包括：
- 测试用例的设计、创建和维护
- 集成AI服务实现智能用例生成
- 支持自动化脚本生成和管理
- 实现用例库管理和复用机制
- 用例与需求的双向追溯关系
- 用例质量检查和评估
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import IntegrityError
import logging
import json

from ..models.test_case import (
    TestCase, TestCaseType, TestCasePriority, TestCaseStatus,
    AutomationScript, TestExecution, ExecutionStatus
)
from ..models.test_plan import TestPlan
from ..models.project import Project
from ..models.user import User
from ..models.requirement import Requirement
from ..core.database import get_db
from ..core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ..services.ai_assistant_service import AIAssistantService
from ..services.permission_service import PermissionService
from ..services.project_service import ProjectService
from ..services.user import UserService
from ..utils.test_cache import TestCacheManager

logger = logging.getLogger(__name__)

VALID_COMPLEXITIES = {"SIMPLE", "MEDIUM", "COMPLEX"}
VALID_AUTOMATION_LEVELS = {"MANUAL", "SEMI_AUTO", "FULL_AUTO"}


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    raw_value = _enum_value(value)
    if raw_value is None:
        return default

    normalized = str(raw_value).strip().upper()
    if normalized in allowed:
        return normalized

    for option in allowed:
        if option in normalized:
            return option

    return default


class TestCaseService:
    """测试用例管理核心服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIAssistantService()
        self.permission_service = PermissionService(db)
        self.project_service = ProjectService(db)
        self.user_service = UserService(db)
        self.cache_manager = TestCacheManager()
    
    async def create_test_case(
        self, 
        case_data: Dict[str, Any], 
        creator_id: int
    ) -> TestCase:
        """
        创建测试用例
        
        Args:
            case_data: 测试用例数据
            creator_id: 创建人ID
            
        Returns:
            TestCase: 创建的测试用例对象
            
        Raises:
            ValidationError: 数据验证失败
            PermissionError: 权限不足
            BusinessLogicError: 业务规则违反
        """
        try:
            case_data = {
                **case_data,
                "requirement_id": case_data.get("requirement_id") or None,
                "case_type": _normalize_choice(case_data.get("case_type"), {item.value for item in TestCaseType}, "FUNCTIONAL"),
                "priority": _normalize_choice(case_data.get("priority"), {item.value for item in TestCasePriority}, "MEDIUM"),
                "complexity": _normalize_choice(case_data.get("complexity"), VALID_COMPLEXITIES, "MEDIUM"),
                "automation_level": _normalize_choice(case_data.get("automation_level"), VALID_AUTOMATION_LEVELS, "MANUAL"),
            }

            # 1. 验证创建权限
            await self._validate_create_permission(creator_id, case_data.get('test_plan_id'))
            
            # 2. 验证用例数据
            await self._validate_case_data(case_data)
            
            # 3. 生成用例编码
            case_code = await self._generate_case_code(case_data.get('test_plan_id'))
            
            # 4. AI质量检查
            quality_analysis = await self._analyze_case_quality(case_data)
            complexity = _normalize_choice(
                quality_analysis.get('complexity', case_data.get('complexity', 'MEDIUM')),
                VALID_COMPLEXITIES,
                case_data.get('complexity', 'MEDIUM')
            )
            
            # 5. 创建测试用例实体
            test_case = TestCase(
                case_code=case_code,
                test_plan_id=case_data.get('test_plan_id'),
                requirement_id=case_data.get('requirement_id'),
                case_title=case_data['case_title'],
                case_description=case_data.get('case_description'),
                case_type=TestCaseType(case_data['case_type']),
                module=case_data.get('module'),
                priority=TestCasePriority(case_data.get('priority', 'MEDIUM')),
                complexity=complexity,
                automation_level=case_data.get('automation_level', 'MANUAL'),
                preconditions=case_data.get('preconditions'),
                test_steps=case_data.get('test_steps', []),
                expected_result=case_data.get('expected_result'),
                test_data=case_data.get('test_data'),
                creator_id=creator_id,
                assignee_id=case_data.get('assignee_id'),
                tags=case_data.get('tags', [])
            )
            
            # 6. 保存测试用例
            self.db.add(test_case)
            self.db.flush()  # 获取ID但不提交事务
            
            # 7. 建立需求追溯关系
            if case_data.get('requirement_id'):
                await self._create_requirement_traceability(
                    test_case.id, case_data['requirement_id']
                )
            
            # 8. 提交事务
            self.db.commit()
            
            # 9. 清除相关缓存
            await self._clear_case_cache(test_case.test_plan_id)
            
            # 10. 记录操作日志
            logger.info(f"测试用例创建成功: {case_code}, 创建人: {creator_id}")
            
            return test_case
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建测试用例失败: {str(e)}")
            raise
    
    async def update_test_case(
        self, 
        case_id: int, 
        update_data: Dict[str, Any], 
        user_id: int
    ) -> TestCase:
        """
        更新测试用例
        
        Args:
            case_id: 测试用例ID
            update_data: 更新数据
            user_id: 操作用户ID
            
        Returns:
            TestCase: 更新后的测试用例对象
        """
        try:
            # 1. 获取测试用例
            test_case = await self.get_test_case_by_id(case_id)
            if not test_case:
                raise NotFoundError("测试用例不存在")

            previous_test_plan_id = test_case.test_plan_id
            if 'test_plan_id' in update_data and not update_data['test_plan_id']:
                update_data['test_plan_id'] = None
            if 'requirement_id' in update_data and not update_data['requirement_id']:
                update_data['requirement_id'] = None
            if update_data.get('test_plan_id') is not None:
                target_plan = self.db.query(TestPlan).filter(TestPlan.id == update_data['test_plan_id']).first()
                if not target_plan:
                    raise NotFoundError("测试计划不存在")
            
            # 2. 验证更新权限
            await self._validate_update_permission(user_id, test_case)
            
            # 3. 验证业务规则
            await self._validate_update_rules(test_case, update_data)
            
            # 4. 更新字段
            for field, value in update_data.items():
                if hasattr(test_case, field) and field not in ['id', 'case_code', 'created_by', 'created_at']:
                    if field == 'case_type':
                        setattr(test_case, field, TestCaseType(value))
                    elif field == 'priority':
                        setattr(test_case, field, TestCasePriority(value))
                    elif field == 'status':
                        setattr(test_case, field, TestCaseStatus(value))
                    else:
                        setattr(test_case, field, value)
            
            # 5. 更新版本和时间戳
            test_case.version += 1
            test_case.updated_at = datetime.utcnow()
            test_case.updated_by = user_id
            
            # 6. 提交更改
            self.db.commit()
            
            # 7. 清除缓存
            await self._clear_case_cache(test_case.test_plan_id, case_id)
            if previous_test_plan_id and previous_test_plan_id != test_case.test_plan_id:
                await self._clear_case_cache(previous_test_plan_id)
            
            logger.info(f"测试用例更新成功: {test_case.case_code}, 操作人: {user_id}")
            
            return test_case
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新测试用例失败: {str(e)}")
            raise
    
    async def delete_test_case(self, case_id: int, user_id: int) -> bool:
        """
        删除测试用例
        
        Args:
            case_id: 测试用例ID
            user_id: 操作用户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 1. 获取测试用例
            test_case = await self.get_test_case_by_id(case_id)
            if not test_case:
                raise NotFoundError("测试用例不存在")
            
            # 2. 验证删除权限
            await self._validate_delete_permission(user_id, test_case)
            
            # 3. 验证删除规则
            await self._validate_delete_rules(test_case)

            test_plan_id = test_case.test_plan_id
            case_code = test_case.case_code
            
            # 4. 软删除或硬删除
            if test_case.execution_count > 0:
                # 已执行的用例不能删除，只能归档
                test_case.status = TestCaseStatus.ARCHIVED
                test_case.updated_at = datetime.utcnow()
                test_case.updated_by = user_id
            else:
                # 未执行的用例可以直接删除
                self.db.delete(test_case)
            
            # 5. 提交更改
            self.db.commit()
            
            # 6. 清除缓存
            await self._clear_case_cache(test_plan_id, case_id)
            
            logger.info(f"测试用例删除成功: {case_code}, 操作人: {user_id}")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除测试用例失败: {str(e)}")
            raise
    
    async def get_test_case_by_id(self, case_id: int) -> Optional[TestCase]:
        """
        根据ID获取测试用例
        
        Args:
            case_id: 测试用例ID
            
        Returns:
            Optional[TestCase]: 测试用例对象或None
        """
        # 先尝试从缓存获取
        cached_case = await self.cache_manager.get_test_case(case_id)
        if cached_case:
            return cached_case
        
        # 从数据库查询
        test_case = self.db.query(TestCase).filter(TestCase.id == case_id).first()
        
        # 缓存结果
        if test_case:
            await self.cache_manager.set_test_case(case_id, test_case)
        
        return test_case
    
    async def get_test_case_by_code(self, case_code: str) -> Optional[TestCase]:
        """
        根据编码获取测试用例
        
        Args:
            case_code: 测试用例编码
            
        Returns:
            Optional[TestCase]: 测试用例对象或None
        """
        return self.db.query(TestCase).filter(TestCase.case_code == case_code).first()
    
    async def get_test_cases_by_plan(
        self, 
        test_plan_id: int, 
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TestCase], int]:
        """
        获取测试计划的用例列表
        
        Args:
            test_plan_id: 测试计划ID
            filters: 过滤条件
            page: 页码
            page_size: 每页大小
            
        Returns:
            Tuple[List[TestCase], int]: 测试用例列表和总数
        """
        query = self.db.query(TestCase).filter(TestCase.test_plan_id == test_plan_id)
        
        # 应用过滤条件
        if filters:
            if filters.get('case_type'):
                query = query.filter(TestCase.case_type == TestCaseType(filters['case_type']))
            
            if filters.get('priority'):
                query = query.filter(TestCase.priority == TestCasePriority(filters['priority']))
            
            if filters.get('status'):
                query = query.filter(TestCase.status == TestCaseStatus(filters['status']))
            
            if filters.get('module'):
                query = query.filter(TestCase.module == filters['module'])
            
            if filters.get('assignee_id'):
                query = query.filter(TestCase.assignee_id == filters['assignee_id'])
            
            if filters.get('automation_level'):
                query = query.filter(TestCase.automation_level == filters['automation_level'])
            
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        TestCase.case_title.like(search_term),
                        TestCase.case_description.like(search_term),
                        TestCase.case_code.like(search_term)
                    )
                )
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        cases = query.order_by(desc(TestCase.created_at))\
                    .offset((page - 1) * page_size)\
                    .limit(page_size)\
                    .all()
        
        return cases, total
    
    async def get_test_cases_by_requirement(
        self, 
        requirement_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[TestCase], int]:
        """
        获取需求关联的测试用例
        
        Args:
            requirement_id: 需求ID
            page: 页码
            page_size: 每页大小
            
        Returns:
            Tuple[List[TestCase], int]: 测试用例列表和总数
        """
        query = self.db.query(TestCase).filter(TestCase.requirement_id == requirement_id)
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        cases = query.order_by(desc(TestCase.created_at))\
                    .offset((page - 1) * page_size)\
                    .limit(page_size)\
                    .all()
        
        return cases, total
    
    async def copy_test_case(
        self, 
        source_case_id: int, 
        target_plan_id: Optional[int] = None,
        user_id: int = None
    ) -> TestCase:
        """
        复制测试用例
        
        Args:
            source_case_id: 源用例ID
            target_plan_id: 目标计划ID（可选）
            user_id: 操作用户ID
            
        Returns:
            TestCase: 复制的测试用例对象
        """
        try:
            # 1. 获取源用例
            source_case = await self.get_test_case_by_id(source_case_id)
            if not source_case:
                raise NotFoundError("源测试用例不存在")
            
            # 2. 验证权限
            if target_plan_id:
                await self._validate_create_permission(user_id, target_plan_id)
            
            # 3. 生成新的用例编码
            new_case_code = await self._generate_case_code(target_plan_id or source_case.test_plan_id)
            
            # 4. 创建新用例
            new_case = TestCase(
                case_code=new_case_code,
                test_plan_id=target_plan_id or source_case.test_plan_id,
                requirement_id=source_case.requirement_id,
                case_title=f"[复制] {source_case.case_title}",
                case_description=source_case.case_description,
                case_type=source_case.case_type,
                module=source_case.module,
                priority=source_case.priority,
                complexity=source_case.complexity,
                automation_level=source_case.automation_level,
                preconditions=source_case.preconditions,
                test_steps=source_case.test_steps,
                expected_result=source_case.expected_result,
                test_data=source_case.test_data,
                creator_id=user_id or source_case.creator_id,
                tags=source_case.tags
            )
            
            # 5. 保存新用例
            self.db.add(new_case)
            self.db.commit()
            
            # 6. 清除缓存
            await self._clear_case_cache(new_case.test_plan_id)
            
            logger.info(f"测试用例复制成功: {source_case.case_code} -> {new_case_code}")
            
            return new_case
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"复制测试用例失败: {str(e)}")
            raise
    
    async def batch_update_cases(
        self, 
        case_ids: List[int], 
        update_data: Dict[str, Any], 
        user_id: int
    ) -> List[TestCase]:
        """
        批量更新测试用例
        
        Args:
            case_ids: 用例ID列表
            update_data: 更新数据
            user_id: 操作用户ID
            
        Returns:
            List[TestCase]: 更新后的用例列表
        """
        try:
            updated_cases = []
            
            for case_id in case_ids:
                try:
                    updated_case = await self.update_test_case(case_id, update_data, user_id)
                    updated_cases.append(updated_case)
                except Exception as e:
                    logger.warning(f"批量更新用例 {case_id} 失败: {str(e)}")
                    continue
            
            logger.info(f"批量更新测试用例完成: {len(updated_cases)}/{len(case_ids)} 成功")
            
            return updated_cases
            
        except Exception as e:
            logger.error(f"批量更新测试用例失败: {str(e)}")
            raise
    
    async def get_case_execution_history(
        self, 
        case_id: int,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[TestExecution], int]:
        """
        获取测试用例执行历史
        
        Args:
            case_id: 测试用例ID
            page: 页码
            page_size: 每页大小
            
        Returns:
            Tuple[List[TestExecution], int]: 执行记录列表和总数
        """
        query = self.db.query(TestExecution).filter(TestExecution.test_case_id == case_id)
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        executions = query.order_by(desc(TestExecution.started_at))\
                         .offset((page - 1) * page_size)\
                         .limit(page_size)\
                         .all()
        
        return executions, total
    
    async def get_case_coverage_analysis(self, case_id: int) -> Dict[str, Any]:
        """
        获取测试用例覆盖率分析
        
        Args:
            case_id: 测试用例ID
            
        Returns:
            Dict[str, Any]: 覆盖率分析结果
        """
        test_case = await self.get_test_case_by_id(case_id)
        if not test_case:
            raise NotFoundError("测试用例不存在")
        
        # 获取关联需求
        requirement_coverage = 0
        if test_case.requirement_id:
            # 计算需求覆盖情况
            requirement_coverage = 1
        
        # 获取执行统计
        total_executions = test_case.execution_count
        passed_executions = test_case.pass_count
        failed_executions = test_case.fail_count
        
        # 计算通过率
        pass_rate = (passed_executions / total_executions * 100) if total_executions > 0 else 0
        
        return {
            'case_id': case_id,
            'case_code': test_case.case_code,
            'requirement_coverage': requirement_coverage,
            'total_executions': total_executions,
            'passed_executions': passed_executions,
            'failed_executions': failed_executions,
            'pass_rate': round(pass_rate, 2),
            'last_execution_date': test_case.last_execution_date.isoformat() if test_case.last_execution_date else None,
            'last_execution_status': test_case.last_execution_status.value if test_case.last_execution_status else None
        }
    
    # 私有方法
    async def _generate_case_code(self, test_plan_id: Optional[int]) -> str:
        """
        生成测试用例编码
        
        Args:
            test_plan_id: 测试计划ID
            
        Returns:
            str: 测试用例编码
        """
        if test_plan_id:
            # 获取测试计划
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == test_plan_id).first()
            if test_plan:
                plan_code = test_plan.plan_code
            else:
                plan_code = "UNKNOWN"
        else:
            plan_code = "GENERAL"
        
        # 查询当天已创建的用例数量
        today = datetime.now().strftime("%Y%m%d")
        count = self.db.query(TestCase)\
            .filter(TestCase.case_code.like(f"TC-{plan_code}-{today}-%"))\
            .count()
        
        sequence = count + 1
        case_code = f"TC-{plan_code}-{today}-{sequence:04d}"
        
        # 确保编码唯一性
        while self.db.query(TestCase).filter(TestCase.case_code == case_code).first():
            sequence += 1
            case_code = f"TC-{plan_code}-{today}-{sequence:04d}"
        
        return case_code
    
    async def _validate_case_data(self, case_data: Dict[str, Any]) -> None:
        """
        验证测试用例数据
        
        Args:
            case_data: 用例数据
            
        Raises:
            ValidationError: 数据验证失败
        """
        # 必填字段验证
        required_fields = ['case_title', 'case_type']
        for field in required_fields:
            if not case_data.get(field):
                raise ValidationError(f"字段 {field} 不能为空")
        
        # 用例标题长度验证
        if len(case_data['case_title']) > 200:
            raise ValidationError("用例标题长度不能超过200个字符")
        
        # 用例类型验证
        try:
            TestCaseType(case_data['case_type'])
        except ValueError:
            raise ValidationError("无效的用例类型")
        
        # 优先级验证
        if case_data.get('priority'):
            try:
                TestCasePriority(case_data['priority'])
            except ValueError:
                raise ValidationError("无效的优先级")
        
        # 测试步骤验证
        if case_data.get('test_steps'):
            if not isinstance(case_data['test_steps'], list):
                raise ValidationError("测试步骤必须是列表格式")

        if case_data.get('requirement_id'):
            requirement = self.db.query(Requirement).filter(Requirement.id == case_data['requirement_id']).first()
            if not requirement:
                raise ValidationError("指定的关联需求不存在")
        
        # 负责人验证
        if case_data.get('assignee_id'):
            assignee = await self.user_service.get_user_by_id(case_data['assignee_id'])
            if not assignee:
                raise ValidationError("指定的负责人不存在")
    
    async def _validate_create_permission(self, user_id: int, test_plan_id: Optional[int]) -> None:
        """
        验证创建权限
        
        Args:
            user_id: 用户ID
            test_plan_id: 测试计划ID
            
        Raises:
            PermissionError: 权限不足
        """
        if test_plan_id:
            # 获取测试计划的项目ID
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == test_plan_id).first()
            if test_plan:
                has_permission = await self.permission_service.check_project_permission(
                    user_id, test_plan.project_id, 'test_case_create'
                )
                if not has_permission:
                    raise PermissionError("没有创建测试用例的权限")
    
    async def _validate_update_permission(self, user_id: int, test_case: TestCase) -> None:
        """
        验证更新权限
        
        Args:
            user_id: 用户ID
            test_case: 测试用例对象
            
        Raises:
            PermissionError: 权限不足
        """
        # 检查是否是用例创建者或负责人
        if test_case.creator_id == user_id or test_case.assignee_id == user_id:
            return
        
        # 检查项目权限
        if test_case.test_plan_id:
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == test_case.test_plan_id).first()
            if test_plan:
                has_permission = await self.permission_service.check_project_permission(
                    user_id, test_plan.project_id, 'test_case_update'
                )
                if not has_permission:
                    raise PermissionError("没有更新测试用例的权限")
    
    async def _validate_delete_permission(self, user_id: int, test_case: TestCase) -> None:
        """
        验证删除权限
        
        Args:
            user_id: 用户ID
            test_case: 测试用例对象
            
        Raises:
            PermissionError: 权限不足
        """
        # 检查是否是用例创建者
        if test_case.creator_id == user_id:
            return
        
        # 检查项目权限
        if test_case.test_plan_id:
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == test_case.test_plan_id).first()
            if test_plan:
                has_permission = await self.permission_service.check_project_permission(
                    user_id, test_plan.project_id, 'test_case_delete'
                )
                if not has_permission:
                    raise PermissionError("没有删除测试用例的权限")
    
    async def _validate_update_rules(self, test_case: TestCase, update_data: Dict[str, Any]) -> None:
        """
        验证更新业务规则
        
        Args:
            test_case: 测试用例对象
            update_data: 更新数据
            
        Raises:
            BusinessLogicError: 业务规则违反
        """
        # 已归档的用例不能修改
        if test_case.status == TestCaseStatus.ARCHIVED:
            raise BusinessLogicError("已归档的测试用例不能修改")

        if update_data.get('requirement_id'):
            requirement = self.db.query(Requirement).filter(Requirement.id == update_data['requirement_id']).first()
            if not requirement:
                raise BusinessLogicError("指定的关联需求不存在")
        
        # 正在执行的用例不能修改关键信息
        if test_case.last_execution_status == ExecutionStatus.IN_PROGRESS:
            restricted_fields = ['test_steps', 'expected_result', 'test_data']
            for field in restricted_fields:
                if field in update_data:
                    raise BusinessLogicError(f"正在执行的测试用例不能修改{field}")
    
    async def _validate_delete_rules(self, test_case: TestCase) -> None:
        """
        验证删除业务规则
        
        Args:
            test_case: 测试用例对象
            
        Raises:
            BusinessLogicError: 业务规则违反
        """
        # 正在执行的用例不能删除
        if test_case.last_execution_status == ExecutionStatus.IN_PROGRESS:
            raise BusinessLogicError("正在执行的测试用例不能删除")
    
    async def _analyze_case_quality(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI质量分析
        
        Args:
            case_data: 用例数据
            
        Returns:
            Dict[str, Any]: 质量分析结果
        """
        try:
            # 构建AI分析提示
            prompt = f"""
            请分析以下测试用例的质量：
            
            用例标题：{case_data.get('case_title', '')}
            用例描述：{case_data.get('case_description', '')}
            测试步骤：{json.dumps(case_data.get('test_steps', []), ensure_ascii=False)}
            预期结果：{case_data.get('expected_result', '')}
            
            请评估：
            1. 复杂度（SIMPLE/MEDIUM/COMPLEX）
            2. 完整性评分（0-100）
            3. 可执行性评分（0-100）
            4. 改进建议
            """
            
            # 调用AI服务
            ai_response = await self.ai_service.analyze_test_case_quality(prompt)
            
            return {
                'complexity': ai_response.get('complexity', 'MEDIUM'),
                'completeness_score': ai_response.get('completeness_score', 80),
                'executability_score': ai_response.get('executability_score', 80),
                'suggestions': ai_response.get('suggestions', [])
            }
            
        except Exception as e:
            logger.warning(f"AI质量分析失败: {str(e)}")
            return {'complexity': 'MEDIUM'}
    
    async def _create_requirement_traceability(self, case_id: int, requirement_id: int) -> None:
        """
        创建需求追溯关系
        
        Args:
            case_id: 测试用例ID
            requirement_id: 需求ID
        """
        try:
            # 这里应该调用追溯关系服务
            # await self.traceability_service.create_link(
            #     source_type="requirement",
            #     source_id=requirement_id,
            #     target_type="test_case",
            #     target_id=case_id,
            #     link_type="TESTS"
            # )
            pass
        except Exception as e:
            logger.warning(f"创建需求追溯关系失败: {str(e)}")
    
    async def _clear_case_cache(self, test_plan_id: Optional[int], case_id: Optional[int] = None) -> None:
        """
        清除用例相关缓存
        
        Args:
            test_plan_id: 测试计划ID
            case_id: 用例ID（可选）
        """
        try:
            # 清除计划用例列表缓存
            if test_plan_id:
                await self.cache_manager.delete_plan_cases(test_plan_id)
            
            # 清除特定用例缓存
            if case_id:
                await self.cache_manager.delete_test_case(case_id)
                
        except Exception as e:
            logger.warning(f"清除缓存失败: {str(e)}")
