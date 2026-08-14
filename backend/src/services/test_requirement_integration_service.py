"""
测试需求集成服务

本模块实现测试管理系统与需求管理系统的集成功能，包括：
- 需求与测试用例的双向追溯
- 测试覆盖率分析
- 缺陷关联功能
- 测试结果对需求状态的影响
"""
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text, update, case
from sqlalchemy.orm import selectinload, joinedload
from fastapi import Depends

from ..core.database import get_async_session
from ..core.exceptions import ValidationError, NotFoundError, PermissionError
from ..models.requirement import Requirement, RequirementStatus, RequirementTraceabilityLink, TraceabilityLinkType
from ..models.test_case import TestCase, TestExecution, Defect, TestCoverage, TestCaseType, ExecutionStatus, DefectStatus
from ..models.project import Project
from ..services.requirement_service import RequirementService

logger = logging.getLogger(__name__)


class TestRequirementIntegrationService:
    """测试需求集成服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.requirement_service = RequirementService(db)
    
    async def create_test_case_from_requirement(
        self, 
        requirement_id: int, 
        test_case_data: Dict[str, Any], 
        user_id: int
    ) -> TestCase:
        """
        从需求创建测试用例
        
        Args:
            requirement_id: 需求ID
            test_case_data: 测试用例数据
            user_id: 用户ID
            
        Returns:
            创建的测试用例对象
        """
        # 1. 获取需求信息
        requirement = await self._get_requirement_by_id(requirement_id)
        if not requirement:
            raise NotFoundError(f"需求 {requirement_id} 不存在")
        
        # 2. 验证权限
        await self._validate_test_case_creation_permission(requirement.project_id, user_id)
        
        # 3. 生成测试用例编码
        test_case_code = await self._generate_test_case_code(requirement.project_id)
        
        # 4. 从需求生成测试步骤
        test_steps = await self._generate_test_steps_from_requirement(requirement)
        
        # 5. 创建测试用例
        test_case = TestCase(
            test_case_code=test_case_code,
            project_id=requirement.project_id,
            requirement_id=requirement_id,
            title=test_case_data.get('title', f"测试需求: {requirement.title}"),
            description=test_case_data.get('description', f"验证需求: {requirement.description}"),
            preconditions=test_case_data.get('preconditions', ""),
            test_steps=test_steps,
            test_data=test_case_data.get('test_data', {}),
            expected_result=requirement.acceptance_criteria or "按照需求描述正常工作",
            test_type=test_case_data.get('test_type', TestCaseType.FUNCTIONAL),
            priority=self._map_requirement_priority_to_test_case(requirement.priority),
            creator_id=user_id,
            assignee_id=test_case_data.get('assignee_id'),
            estimated_execution_time=test_case_data.get('estimated_execution_time', 30),
            tags=test_case_data.get('tags', requirement.tags)
        )
        
        # 6. 保存测试用例
        self.db.add(test_case)
        await self.db.flush()
        
        # 7. 创建需求-测试用例追溯链接
        await self._create_requirement_test_case_traceability(requirement_id, test_case.id, user_id)
        
        # 8. 更新需求的测试用例计数
        await self._update_requirement_test_case_count(requirement_id)
        
        await self.db.commit()
        
        logger.info(f"从需求 {requirement_id} 创建测试用例 {test_case.id} 成功")
        return test_case
    
    async def execute_test_case(
        self, 
        test_case_id: int, 
        execution_data: Dict[str, Any], 
        user_id: int
    ) -> TestExecution:
        """
        执行测试用例
        
        Args:
            test_case_id: 测试用例ID
            execution_data: 执行数据
            user_id: 用户ID
            
        Returns:
            测试执行记录
        """
        # 1. 获取测试用例
        test_case = await self._get_test_case_by_id(test_case_id)
        if not test_case:
            raise NotFoundError(f"测试用例 {test_case_id} 不存在")
        
        # 2. 创建执行记录
        execution = TestExecution(
            test_case_id=test_case_id,
            project_id=test_case.project_id,
            execution_date=execution_data.get('execution_date', datetime.utcnow()),
            executor_id=user_id,
            execution_status=execution_data['execution_status'],
            actual_result=execution_data.get('actual_result'),
            execution_notes=execution_data.get('execution_notes'),
            execution_time=execution_data.get('execution_time'),
            test_environment=execution_data.get('test_environment'),
            browser_version=execution_data.get('browser_version'),
            os_version=execution_data.get('os_version'),
            defects_found=execution_data.get('defects_found', 0),
            screenshots=execution_data.get('screenshots'),
            logs=execution_data.get('logs')
        )
        
        # 3. 保存执行记录
        self.db.add(execution)
        await self.db.flush()
        
        # 4. 更新测试用例统计
        await self._update_test_case_statistics(test_case, execution.execution_status)
        
        # 5. 如果测试失败，可能需要更新需求状态
        if execution.execution_status == ExecutionStatus.FAILED and test_case.requirement_id:
            await self._handle_test_failure_impact(test_case.requirement_id, user_id)
        
        # 6. 如果测试通过，检查是否可以更新需求状态
        if execution.execution_status == ExecutionStatus.PASSED and test_case.requirement_id:
            await self._handle_test_pass_impact(test_case.requirement_id, user_id)
        
        await self.db.commit()
        
        logger.info(f"测试用例 {test_case_id} 执行完成，状态: {execution.execution_status}")
        return execution
    
    async def create_defect_from_test_failure(
        self, 
        test_case_id: int, 
        defect_data: Dict[str, Any], 
        user_id: int
    ) -> Defect:
        """
        从测试失败创建缺陷
        
        Args:
            test_case_id: 测试用例ID
            defect_data: 缺陷数据
            user_id: 用户ID
            
        Returns:
            创建的缺陷对象
        """
        # 1. 获取测试用例
        test_case = await self._get_test_case_by_id(test_case_id)
        if not test_case:
            raise NotFoundError(f"测试用例 {test_case_id} 不存在")
        
        # 2. 生成缺陷编码
        defect_code = await self._generate_defect_code(test_case.project_id)
        
        # 3. 创建缺陷
        defect = Defect(
            defect_code=defect_code,
            project_id=test_case.project_id,
            test_case_id=test_case_id,
            requirement_id=test_case.requirement_id,
            title=defect_data.get('title', f"测试用例失败: {test_case.title}"),
            description=defect_data['description'],
            steps_to_reproduce=defect_data.get('steps_to_reproduce', self._format_test_steps(test_case.test_steps)),
            actual_result=defect_data.get('actual_result'),
            expected_result=test_case.expected_result,
            severity=defect_data['severity'],
            priority=defect_data.get('priority', test_case.priority),
            defect_type=defect_data.get('defect_type', 'FUNCTIONAL'),
            environment=defect_data.get('environment'),
            browser_version=defect_data.get('browser_version'),
            os_version=defect_data.get('os_version'),
            reporter_id=user_id,
            assignee_id=defect_data.get('assignee_id'),
            tags=defect_data.get('tags', test_case.tags),
            attachments=defect_data.get('attachments')
        )
        
        # 4. 保存缺陷
        self.db.add(defect)
        await self.db.flush()
        
        # 5. 创建缺陷-需求追溯链接
        if test_case.requirement_id:
            await self._create_defect_requirement_traceability(defect.id, test_case.requirement_id, user_id)
        
        # 6. 更新需求缺陷计数
        if test_case.requirement_id:
            await self._update_requirement_defect_count(test_case.requirement_id)
        
        await self.db.commit()
        
        logger.info(f"从测试用例 {test_case_id} 创建缺陷 {defect.id} 成功")
        return defect
    
    async def calculate_test_coverage(self, project_id: int, requirement_id: Optional[int] = None) -> TestCoverage:
        """
        计算测试覆盖率
        
        Args:
            project_id: 项目ID
            requirement_id: 需求ID（可选，如果指定则计算单个需求的覆盖率）
            
        Returns:
            测试覆盖率对象
        """
        # 0. 验证项目是否存在
        project = await self.db.get(Project, project_id)
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")

        # 1. 获取测试用例统计
        test_case_stats = await self._get_test_case_statistics(project_id, requirement_id)
        
        # 2. 获取需求统计
        requirement_stats = await self._get_requirement_statistics(project_id, requirement_id)
        
        # 3. 计算覆盖率
        execution_coverage = 0.0
        pass_rate = 0.0
        requirement_coverage = 0.0
        
        if test_case_stats['total'] > 0:
            execution_coverage = (test_case_stats['executed'] / test_case_stats['total']) * 100
            if test_case_stats['executed'] > 0:
                pass_rate = (test_case_stats['passed'] / test_case_stats['executed']) * 100
        
        if requirement_stats['total'] > 0:
            requirement_coverage = (requirement_stats['covered'] / requirement_stats['total']) * 100
        
        # 4. 创建或更新覆盖率记录
        coverage = TestCoverage(
            project_id=project_id,
            requirement_id=requirement_id,
            total_test_cases=test_case_stats['total'],
            executed_test_cases=test_case_stats['executed'],
            passed_test_cases=test_case_stats['passed'],
            failed_test_cases=test_case_stats['failed'],
            execution_coverage=Decimal(str(round(execution_coverage, 2))),
            pass_rate=Decimal(str(round(pass_rate, 2))),
            requirements_covered=requirement_stats['covered'],
            requirements_total=requirement_stats['total'],
            requirement_coverage=Decimal(str(round(requirement_coverage, 2))),
            coverage_date=date.today()
        )
        
        # 5. 保存覆盖率记录
        self.db.add(coverage)
        await self.db.commit()
        
        logger.info(f"项目 {project_id} 测试覆盖率计算完成")
        return coverage
    
    async def get_requirement_test_traceability(self, requirement_id: int) -> Dict[str, Any]:
        """
        获取需求测试追溯关系
        
        Args:
            requirement_id: 需求ID
            
        Returns:
            追溯关系信息
        """
        # 1. 获取需求信息
        requirement = await self._get_requirement_by_id(requirement_id)
        if not requirement:
            raise NotFoundError(f"需求 {requirement_id} 不存在")
        
        # 2. 获取关联的测试用例
        test_cases = await self._get_test_cases_by_requirement(requirement_id)
        
        # 3. 获取测试执行统计
        execution_stats = await self._get_execution_statistics_by_requirement(requirement_id)
        
        # 4. 获取关联的缺陷
        defects = await self._get_defects_by_requirement(requirement_id)
        
        # 5. 计算覆盖率指标
        coverage_metrics = await self._calculate_requirement_coverage_metrics(requirement_id)
        
        return {
            'requirement_id': requirement_id,
            'requirement_title': requirement.title,
            'requirement_status': requirement.status.value,
            'test_cases': [tc.to_dict() for tc in test_cases],
            'test_case_count': len(test_cases),
            'execution_stats': execution_stats,
            'defects': [d.to_dict() for d in defects],
            'defect_count': len(defects),
            'coverage_metrics': coverage_metrics,
            'traceability_complete': len(test_cases) > 0
        }
    
    async def sync_defect_resolution_to_requirement(self, defect_id: int, user_id: int) -> bool:
        """
        同步缺陷解决状态到需求
        
        Args:
            defect_id: 缺陷ID
            user_id: 用户ID
            
        Returns:
            是否同步成功
        """
        # 1. 获取缺陷信息
        defect = await self._get_defect_by_id(defect_id)
        if not defect or not defect.requirement_id:
            return False
        
        # 2. 如果缺陷已解决，检查需求的所有缺陷状态
        if defect.status in [DefectStatus.RESOLVED, DefectStatus.VERIFIED, DefectStatus.CLOSED]:
            open_defects = await self._get_open_defects_count_by_requirement(defect.requirement_id)
            
            # 3. 如果没有未解决的缺陷，可能需要更新需求状态
            if open_defects == 0:
                requirement = await self._get_requirement_by_id(defect.requirement_id)
                if requirement and requirement.status == RequirementStatus.TEST_FAILED:
                    # 重新运行测试或更新为测试中状态
                    await self.requirement_service.update_requirement_status(
                        defect.requirement_id, RequirementStatus.TESTING, user_id, "所有缺陷已解决"
                    )
        
        await self.db.commit()
        return True
    
    # 私有方法
    async def _get_requirement_by_id(self, requirement_id: int) -> Optional[Requirement]:
        """获取需求信息"""
        result = await self.db.execute(
            select(Requirement).where(Requirement.id == requirement_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_test_case_by_id(self, test_case_id: int) -> Optional[TestCase]:
        """获取测试用例信息"""
        result = await self.db.execute(
            select(TestCase).where(TestCase.id == test_case_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_defect_by_id(self, defect_id: int) -> Optional[Defect]:
        """获取缺陷信息"""
        result = await self.db.execute(
            select(Defect).where(Defect.id == defect_id)
        )
        return result.scalar_one_or_none()
    
    async def _validate_test_case_creation_permission(self, project_id: int, user_id: int):
        """验证测试用例创建权限"""
        # 简化权限检查 - 假设所有用户都可以创建测试用例
        # TODO: 实现更细粒度的权限控制
        pass
    
    async def _generate_test_case_code(self, project_id: int) -> str:
        """生成测试用例编码"""
        # 获取项目信息
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")
        
        # 获取项目今日测试用例数量
        # TestCase 没有 project_id 字段，通过 requirement_id 关联 Requirement，
        # 再由 Requirement.project_id 过滤到指定项目
        today = datetime.now().strftime("%Y%m%d")
        result = await self.db.execute(
            select(func.count(TestCase.id)).select_from(
                TestCase
            ).outerjoin(
                Requirement, TestCase.requirement_id == Requirement.id
            ).where(
                and_(
                    Requirement.project_id == project_id,
                    TestCase.case_code.like(f"TC-{project.project_code}-{today}-%")
                )
            )
        )
        count = result.scalar() or 0
        
        return f"TC-{project.project_code}-{today}-{count + 1:03d}"
    
    async def _generate_defect_code(self, project_id: int) -> str:
        """生成缺陷编码"""
        # 获取项目信息
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError(f"项目 {project_id} 不存在")
        
        # 获取项目今日缺陷数量
        # Defect 没有 project_id 字段，通过 requirement_id 关联 Requirement，
        # 再由 Requirement.project_id 过滤到指定项目
        today = datetime.now().strftime("%Y%m%d")
        result = await self.db.execute(
            select(func.count(Defect.id)).select_from(
                Defect
            ).outerjoin(
                Requirement, Defect.requirement_id == Requirement.id
            ).where(
                and_(
                    Requirement.project_id == project_id,
                    Defect.defect_code.like(f"BUG-{project.project_code}-{today}-%")
                )
            )
        )
        count = result.scalar() or 0
        
        return f"BUG-{project.project_code}-{today}-{count + 1:03d}"
    
    async def _generate_test_steps_from_requirement(self, requirement: Requirement) -> List[Dict[str, Any]]:
        """从需求生成测试步骤"""
        steps = []
        
        # 基础步骤
        steps.append({
            'step_number': 1,
            'action': '验证前置条件',
            'expected_result': '系统处于可测试状态'
        })
        
        # 根据需求描述生成主要测试步骤
        if requirement.description:
            steps.append({
                'step_number': 2,
                'action': f'执行需求功能: {requirement.title}',
                'expected_result': requirement.acceptance_criteria or '功能正常工作'
            })
        
        # 验证步骤
        steps.append({
            'step_number': 3,
            'action': '验证结果',
            'expected_result': '结果符合预期'
        })
        
        return steps
    
    async def _create_requirement_test_case_traceability(self, requirement_id: int, test_case_id: int, user_id: int):
        """创建需求-测试用例追溯链接"""
        link = RequirementTraceabilityLink(
            source_type='requirement',
            source_id=requirement_id,
            target_type='test_case',
            target_id=test_case_id,
            link_type=TraceabilityLinkType.TESTS,
            description=f"需求 {requirement_id} 由测试用例 {test_case_id} 验证",
            created_by=user_id
        )
        self.db.add(link)
    
    async def _create_defect_requirement_traceability(self, defect_id: int, requirement_id: int, user_id: int):
        """创建缺陷-需求追溯链接"""
        link = RequirementTraceabilityLink(
            source_type='defect',
            source_id=defect_id,
            target_type='requirement',
            target_id=requirement_id,
            link_type=TraceabilityLinkType.VALIDATES,
            description=f"缺陷 {defect_id} 影响需求 {requirement_id}",
            created_by=user_id
        )
        self.db.add(link)
    
    async def _update_test_case_statistics(self, test_case: TestCase, execution_status: ExecutionStatus):
        """更新测试用例统计"""
        test_case.execution_count += 1
        test_case.last_execution_date = datetime.utcnow()
        test_case.last_execution_status = execution_status
        
        if execution_status == ExecutionStatus.PASSED:
            test_case.pass_count += 1
        elif execution_status == ExecutionStatus.FAILED:
            test_case.fail_count += 1
    
    async def _update_requirement_test_case_count(self, requirement_id: int):
        """更新需求的测试用例计数"""
        result = await self.db.execute(
            select(func.count(TestCase.id)).where(TestCase.requirement_id == requirement_id)
        )
        count = result.scalar() or 0
        
        # 更新需求的测试用例计数（如果需求模型有这个字段）
        # 这里假设需求模型有test_case_count字段
        await self.db.execute(
            update(Requirement)
            .where(Requirement.id == requirement_id)
            .values(test_case_count=count)
        )
    
    async def _update_requirement_defect_count(self, requirement_id: int):
        """更新需求的缺陷计数"""
        result = await self.db.execute(
            select(func.count(Defect.id)).where(Defect.requirement_id == requirement_id)
        )
        count = result.scalar() or 0
        
        # 更新需求的缺陷计数（如果需求模型有这个字段）
        # 这里假设需求模型有defect_count字段
        await self.db.execute(
            update(Requirement)
            .where(Requirement.id == requirement_id)
            .values(defect_count=count)
        )
    
    async def _handle_test_failure_impact(self, requirement_id: int, user_id: int):
        """处理测试失败对需求的影响"""
        requirement = await self._get_requirement_by_id(requirement_id)
        if requirement and requirement.status == RequirementStatus.TESTING:
            await self.requirement_service.update_requirement_status(
                requirement_id, RequirementStatus.TEST_FAILED, user_id, "测试执行失败"
            )
    
    async def _handle_test_pass_impact(self, requirement_id: int, user_id: int):
        """处理测试通过对需求的影响"""
        # 检查需求的所有测试用例是否都通过
        result = await self.db.execute(
            select(
                func.count(TestCase.id).label('total'),
                func.sum(case(*[(TestCase.last_execution_status == ExecutionStatus.PASSED, 1)], else_=0)).label('passed')
            ).where(TestCase.requirement_id == requirement_id)
        )
        stats = result.first()
        
        if stats.total > 0 and stats.passed == stats.total:
            # 所有测试用例都通过，更新需求状态为完成
            requirement = await self._get_requirement_by_id(requirement_id)
            if requirement and requirement.status == RequirementStatus.TESTING:
                await self.requirement_service.update_requirement_status(
                    requirement_id, RequirementStatus.COMPLETED, user_id, "所有测试用例通过"
                )
    
    async def _get_test_case_statistics(self, project_id: int, requirement_id: Optional[int] = None) -> Dict[str, int]:
        """获取测试用例统计

        TestCase 模型本身没有 project_id 字段，它通过 requirement_id 关联到
        Requirement，再由 Requirement.project_id 关联到项目。因此这里通过 join
        Requirement 来按 project_id 过滤。
        """
        query = select(
            func.count(TestCase.id).label('total'),
            func.sum(case(*[(TestCase.execution_count > 0, 1)], else_=0)).label('executed'),
            func.sum(case(*[(TestCase.last_execution_status == ExecutionStatus.PASSED, 1)], else_=0)).label('passed'),
            func.sum(case(*[(TestCase.last_execution_status == ExecutionStatus.FAILED, 1)], else_=0)).label('failed')
        ).select_from(
            TestCase
        ).outerjoin(
            Requirement, TestCase.requirement_id == Requirement.id
        ).where(Requirement.project_id == project_id)

        if requirement_id:
            query = query.where(TestCase.requirement_id == requirement_id)

        result = await self.db.execute(query)
        stats = result.first()

        return {
            'total': stats.total or 0,
            'executed': stats.executed or 0,
            'passed': stats.passed or 0,
            'failed': stats.failed or 0
        }
    
    async def _get_requirement_statistics(self, project_id: int, requirement_id: Optional[int] = None) -> Dict[str, int]:
        """获取需求统计"""
        if requirement_id:
            # 单个需求的统计
            return {'total': 1, 'covered': 1}
        
        # 项目所有需求的统计
        total_result = await self.db.execute(
            select(func.count(Requirement.id)).where(Requirement.project_id == project_id)
        )
        total = total_result.scalar() or 0
        
        # 有测试用例覆盖的需求数
        # TestCase 没有 project_id 字段，通过 requirement_id 关联 Requirement，
        # 再由 Requirement.project_id 过滤到指定项目
        covered_result = await self.db.execute(
            select(func.count(func.distinct(TestCase.requirement_id))).select_from(
                TestCase
            ).outerjoin(
                Requirement, TestCase.requirement_id == Requirement.id
            ).where(
                and_(
                    Requirement.project_id == project_id,
                    TestCase.requirement_id.isnot(None)
                )
            )
        )
        covered = covered_result.scalar() or 0
        
        return {'total': total, 'covered': covered}
    
    async def _get_test_cases_by_requirement(self, requirement_id: int) -> List[TestCase]:
        """获取需求关联的测试用例"""
        result = await self.db.execute(
            select(TestCase).where(TestCase.requirement_id == requirement_id)
        )
        return list(result.scalars().all())
    
    async def _get_defects_by_requirement(self, requirement_id: int) -> List[Defect]:
        """获取需求关联的缺陷"""
        result = await self.db.execute(
            select(Defect).where(Defect.requirement_id == requirement_id)
        )
        return list(result.scalars().all())
    
    async def _get_execution_statistics_by_requirement(self, requirement_id: int) -> Dict[str, Any]:
        """获取需求的测试执行统计"""
        result = await self.db.execute(
            select(
                func.count(TestExecution.id).label('total_executions'),
                func.sum(case(*[(TestExecution.execution_status == ExecutionStatus.PASSED, 1)], else_=0)).label('passed'),
                func.sum(case(*[(TestExecution.execution_status == ExecutionStatus.FAILED, 1)], else_=0)).label('failed'),
                func.sum(case(*[(TestExecution.execution_status == ExecutionStatus.BLOCKED, 1)], else_=0)).label('blocked')
            ).select_from(
                TestExecution.join(TestCase, TestExecution.test_case_id == TestCase.id)
            ).where(TestCase.requirement_id == requirement_id)
        )
        stats = result.first()
        
        return {
            'total_executions': stats.total_executions or 0,
            'passed': stats.passed or 0,
            'failed': stats.failed or 0,
            'blocked': stats.blocked or 0
        }
    
    async def _calculate_requirement_coverage_metrics(self, requirement_id: int) -> Dict[str, float]:
        """计算需求覆盖率指标"""
        # 获取测试用例统计
        test_stats = await self._get_test_case_statistics(None, requirement_id)
        
        # 获取执行统计
        exec_stats = await self._get_execution_statistics_by_requirement(requirement_id)
        
        # 计算覆盖率
        test_coverage = 100.0 if test_stats['total'] > 0 else 0.0
        execution_coverage = (exec_stats['total_executions'] / test_stats['total'] * 100) if test_stats['total'] > 0 else 0.0
        pass_rate = (exec_stats['passed'] / exec_stats['total_executions'] * 100) if exec_stats['total_executions'] > 0 else 0.0
        
        return {
            'test_coverage': round(test_coverage, 2),
            'execution_coverage': round(execution_coverage, 2),
            'pass_rate': round(pass_rate, 2)
        }
    
    async def _get_open_defects_count_by_requirement(self, requirement_id: int) -> int:
        """获取需求的未解决缺陷数量"""
        result = await self.db.execute(
            select(func.count(Defect.id)).where(
                and_(
                    Defect.requirement_id == requirement_id,
                    Defect.status.in_([DefectStatus.NEW, DefectStatus.ASSIGNED, DefectStatus.IN_PROGRESS, DefectStatus.REOPENED])
                )
            )
        )
        return result.scalar() or 0
    
    def _map_requirement_priority_to_test_case(self, requirement_priority) -> str:
        """映射需求优先级到测试用例优先级"""
        mapping = {
            'CRITICAL': 'CRITICAL',
            'HIGH': 'HIGH',
            'MEDIUM': 'MEDIUM',
            'LOW': 'LOW',
            'OPTIONAL': 'LOW'
        }
        return mapping.get(requirement_priority.value if requirement_priority else 'MEDIUM', 'MEDIUM')
    
    def _format_test_steps(self, test_steps: List[Dict[str, Any]]) -> str:
        """格式化测试步骤为文本"""
        if not test_steps:
            return ""
        
        formatted_steps = []
        for step in test_steps:
            step_text = f"{step.get('step_number', '')}. {step.get('action', '')}"
            if step.get('expected_result'):
                step_text += f" - 预期: {step['expected_result']}"
            formatted_steps.append(step_text)
        
        return "\n".join(formatted_steps)


# 依赖注入函数
async def get_test_requirement_integration_service(db: AsyncSession = Depends(get_async_session)):
    """获取测试需求集成服务实例"""
    return TestRequirementIntegrationService(db)