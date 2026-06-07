"""
测试阶段管理服务

本模块实现测试阶段的完整管理，包括：
- 自定义测试阶段和依赖关系定义
- 阶段进入和退出标准的验证
- 跟踪阶段内测试活动和完成情况
- 自动生成阶段总结报告和质量评估
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.exc import IntegrityError
import logging

from ..models.test_plan import TestPlan, TestPhase, TestPhaseStatus
from ..models.test_case import TestCase
from ..models.test_case import TestExecution, ExecutionStatus
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from ..utils.test_cache import TestCacheKeys, TestCacheManager

logger = logging.getLogger(__name__)


class TestPhaseService:
    """测试阶段管理核心服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_manager = TestCacheManager()
    
    async def create_test_phase(
        self, 
        plan_id: int, 
        phase_data: Dict[str, Any], 
        user_id: int
    ) -> TestPhase:
        """
        创建测试阶段
        
        Args:
            plan_id: 测试计划ID
            phase_data: 阶段数据
            user_id: 创建用户ID
            
        Returns:
            TestPhase: 创建的测试阶段对象
        """
        try:
            # 1. 验证测试计划存在
            test_plan = self.db.query(TestPlan).filter(TestPlan.id == plan_id).first()
            if not test_plan:
                raise NotFoundError("测试计划不存在")
            
            # 2. 验证阶段数据
            await self._validate_phase_data(phase_data, plan_id)
            
            # 3. 创建测试阶段
            test_phase = TestPhase(
                test_plan_id=plan_id,
                phase_name=phase_data['phase_name'],
                description=phase_data.get('description'),
                phase_type=phase_data.get('phase_type', 'functional'),
                planned_start_date=self._parse_date(phase_data.get('planned_start_date')),
                planned_end_date=self._parse_date(phase_data.get('planned_end_date')),
                entry_criteria=phase_data.get('entry_criteria', []),
                exit_criteria=phase_data.get('exit_criteria', []),
                phase_order=phase_data.get('phase_order', 1),
                dependencies=phase_data.get('dependencies', []),
                created_by=user_id
            )
            
            # 4. 保存阶段
            self.db.add(test_phase)
            self.db.commit()
            
            # 5. 清除缓存
            await self._clear_phase_cache(plan_id)
            
            logger.info(f"测试阶段创建成功: {test_phase.phase_name}, 计划ID: {plan_id}")
            
            return test_phase
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建测试阶段失败: {str(e)}")
            raise
    
    async def update_test_phase(
        self, 
        phase_id: int, 
        update_data: Dict[str, Any], 
        user_id: int
    ) -> TestPhase:
        """
        更新测试阶段
        
        Args:
            phase_id: 阶段ID
            update_data: 更新数据
            user_id: 操作用户ID
            
        Returns:
            TestPhase: 更新后的阶段对象
        """
        try:
            # 1. 获取测试阶段
            test_phase = self.db.query(TestPhase).filter(TestPhase.id == phase_id).first()
            if not test_phase:
                raise NotFoundError("测试阶段不存在")
            
            # 2. 验证更新规则
            await self._validate_phase_update_rules(test_phase, update_data)
            
            # 3. 更新字段
            for field, value in update_data.items():
                if hasattr(test_phase, field) and field not in ['id', 'test_plan_id', 'created_by', 'created_at']:
                    if field in ['planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date']:
                        setattr(test_phase, field, self._parse_date(value))
                    elif field == 'status':
                        setattr(test_phase, field, TestPhaseStatus(value))
                    else:
                        setattr(test_phase, field, value)
            
            # 4. 更新时间戳
            test_phase.updated_at = datetime.utcnow()
            
            # 5. 提交更改
            self.db.commit()
            
            # 6. 清除缓存
            await self._clear_phase_cache(test_phase.test_plan_id, phase_id)
            
            logger.info(f"测试阶段更新成功: {test_phase.phase_name}")
            
            return test_phase
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新测试阶段失败: {str(e)}")
            raise
    
    async def start_phase(self, phase_id: int, user_id: int) -> TestPhase:
        """
        启动测试阶段
        
        Args:
            phase_id: 阶段ID
            user_id: 操作用户ID
            
        Returns:
            TestPhase: 启动后的阶段对象
        """
        try:
            # 1. 获取测试阶段
            test_phase = self.db.query(TestPhase).filter(TestPhase.id == phase_id).first()
            if not test_phase:
                raise NotFoundError("测试阶段不存在")
            
            # 2. 验证启动条件
            await self._validate_phase_start_conditions(test_phase)
            
            # 3. 检查进入标准
            entry_check_result = await self._check_entry_criteria(test_phase)
            if not entry_check_result['passed']:
                raise BusinessLogicError(f"进入标准未满足: {', '.join(entry_check_result['failed_criteria'])}")
            
            # 4. 更新阶段状态
            test_phase.status = TestPhaseStatus.IN_PROGRESS
            test_phase.actual_start_date = datetime.utcnow().date()
            test_phase.updated_at = datetime.utcnow()
            
            # 5. 提交更改
            self.db.commit()
            
            # 6. 清除缓存
            await self._clear_phase_cache(test_phase.test_plan_id, phase_id)
            
            logger.info(f"测试阶段启动成功: {test_phase.phase_name}")
            
            return test_phase
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"启动测试阶段失败: {str(e)}")
            raise
    
    async def complete_phase(self, phase_id: int, user_id: int) -> TestPhase:
        """
        完成测试阶段
        
        Args:
            phase_id: 阶段ID
            user_id: 操作用户ID
            
        Returns:
            TestPhase: 完成后的阶段对象
        """
        try:
            # 1. 获取测试阶段
            test_phase = self.db.query(TestPhase).filter(TestPhase.id == phase_id).first()
            if not test_phase:
                raise NotFoundError("测试阶段不存在")
            
            # 2. 验证完成条件
            if test_phase.status != TestPhaseStatus.IN_PROGRESS:
                raise BusinessLogicError("只有进行中的阶段才能完成")
            
            # 3. 检查退出标准
            exit_check_result = await self._check_exit_criteria(test_phase)
            if not exit_check_result['passed']:
                raise BusinessLogicError(f"退出标准未满足: {', '.join(exit_check_result['failed_criteria'])}")
            
            # 4. 更新阶段状态
            test_phase.status = TestPhaseStatus.COMPLETED
            test_phase.actual_end_date = datetime.utcnow().date()
            test_phase.updated_at = datetime.utcnow()
            
            # 5. 生成阶段总结
            phase_summary = await self._generate_phase_summary(test_phase)
            test_phase.summary = phase_summary
            
            # 6. 提交更改
            self.db.commit()
            
            # 7. 清除缓存
            await self._clear_phase_cache(test_phase.test_plan_id, phase_id)
            
            logger.info(f"测试阶段完成: {test_phase.phase_name}")
            
            return test_phase
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"完成测试阶段失败: {str(e)}")
            raise
    
    async def get_phase_progress(self, phase_id: int) -> Dict[str, Any]:
        """
        获取阶段进度
        
        Args:
            phase_id: 阶段ID
            
        Returns:
            Dict[str, Any]: 阶段进度信息
        """
        try:
            # 先尝试从缓存获取
            cached_progress = await self.cache_manager.get_phase_progress(phase_id)
            if cached_progress:
                return cached_progress
            
            # 获取阶段信息
            test_phase = self.db.query(TestPhase).filter(TestPhase.id == phase_id).first()
            if not test_phase:
                raise NotFoundError("测试阶段不存在")
            
            # 统计阶段内的测试用例
            phase_cases = self.db.query(TestCase)\
                .filter(TestCase.test_plan_id == test_phase.test_plan_id)\
                .filter(TestCase.test_phase_id == phase_id)\
                .all()
            
            total_cases = len(phase_cases)
            
            # 统计执行情况
            executed_cases = 0
            passed_cases = 0
            failed_cases = 0
            blocked_cases = 0
            
            for case in phase_cases:
                latest_execution = self.db.query(TestExecution)\
                    .filter(TestExecution.test_case_id == case.id)\
                    .order_by(desc(TestExecution.executed_at))\
                    .first()
                
                if latest_execution and latest_execution.execution_status != ExecutionStatus.NOT_EXECUTED:
                    executed_cases += 1
                    if latest_execution.execution_status == ExecutionStatus.PASSED:
                        passed_cases += 1
                    elif latest_execution.execution_status == ExecutionStatus.FAILED:
                        failed_cases += 1
                    elif latest_execution.execution_status == ExecutionStatus.BLOCKED:
                        blocked_cases += 1
            
            # 计算进度指标
            execution_rate = (executed_cases / total_cases * 100) if total_cases > 0 else 0
            pass_rate = (passed_cases / executed_cases * 100) if executed_cases > 0 else 0
            
            # 构建进度信息
            progress = {
                'phase_id': phase_id,
                'phase_name': test_phase.phase_name,
                'status': test_phase.status.value,
                'total_cases': total_cases,
                'executed_cases': executed_cases,
                'passed_cases': passed_cases,
                'failed_cases': failed_cases,
                'blocked_cases': blocked_cases,
                'execution_rate': round(execution_rate, 2),
                'pass_rate': round(pass_rate, 2),
                'planned_start_date': test_phase.planned_start_date.isoformat() if test_phase.planned_start_date else None,
                'planned_end_date': test_phase.planned_end_date.isoformat() if test_phase.planned_end_date else None,
                'actual_start_date': test_phase.actual_start_date.isoformat() if test_phase.actual_start_date else None,
                'actual_end_date': test_phase.actual_end_date.isoformat() if test_phase.actual_end_date else None,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # 缓存结果
            await self.cache_manager.set_phase_progress(phase_id, progress)
            
            return progress
            
        except Exception as e:
            logger.error(f"获取阶段进度失败: {str(e)}")
            raise
    
    async def get_phases_by_plan(self, plan_id: int) -> List[TestPhase]:
        """
        获取计划的所有阶段
        
        Args:
            plan_id: 测试计划ID
            
        Returns:
            List[TestPhase]: 阶段列表
        """
        return self.db.query(TestPhase)\
            .filter(TestPhase.test_plan_id == plan_id)\
            .order_by(TestPhase.phase_order)\
            .all()
    
    async def _validate_phase_data(self, phase_data: Dict[str, Any], plan_id: int) -> None:
        """
        验证阶段数据
        
        Args:
            phase_data: 阶段数据
            plan_id: 测试计划ID
        """
        # 必填字段验证
        if not phase_data.get('phase_name'):
            raise ValidationError("阶段名称不能为空")
        
        # 阶段名称唯一性验证
        existing_phase = self.db.query(TestPhase)\
            .filter(TestPhase.test_plan_id == plan_id)\
            .filter(TestPhase.phase_name == phase_data['phase_name'])\
            .first()
        
        if existing_phase:
            raise ValidationError("阶段名称已存在")
        
        # 日期验证
        start_date = phase_data.get('planned_start_date')
        end_date = phase_data.get('planned_end_date')
        
        if start_date and end_date:
            start_date_obj = self._parse_date(start_date)
            end_date_obj = self._parse_date(end_date)
            
            if start_date_obj and end_date_obj and start_date_obj >= end_date_obj:
                raise ValidationError("计划开始日期必须早于结束日期")
    
    async def _validate_phase_update_rules(
        self, 
        test_phase: TestPhase, 
        update_data: Dict[str, Any]
    ) -> None:
        """
        验证阶段更新规则
        
        Args:
            test_phase: 测试阶段对象
            update_data: 更新数据
        """
        # 已完成的阶段不能修改关键信息
        if test_phase.status == TestPhaseStatus.COMPLETED:
            restricted_fields = ['phase_name', 'entry_criteria', 'exit_criteria']
            for field in restricted_fields:
                if field in update_data:
                    raise BusinessLogicError(f"已完成的阶段不能修改{field}")
        
        # 进行中的阶段不能修改计划日期
        if test_phase.status == TestPhaseStatus.IN_PROGRESS:
            if 'planned_start_date' in update_data or 'planned_end_date' in update_data:
                raise BusinessLogicError("进行中的阶段不能修改计划日期")
    
    async def _validate_phase_start_conditions(self, test_phase: TestPhase) -> None:
        """
        验证阶段启动条件
        
        Args:
            test_phase: 测试阶段对象
        """
        # 检查阶段状态
        if test_phase.status != TestPhaseStatus.PENDING:
            raise BusinessLogicError("只有待开始的阶段才能启动")
        
        # 检查依赖阶段
        if test_phase.dependencies:
            for dep_phase_id in test_phase.dependencies:
                dep_phase = self.db.query(TestPhase).filter(TestPhase.id == dep_phase_id).first()
                if not dep_phase or dep_phase.status != TestPhaseStatus.COMPLETED:
                    raise BusinessLogicError(f"依赖阶段未完成: {dep_phase.phase_name if dep_phase else dep_phase_id}")
    
    async def _check_entry_criteria(self, test_phase: TestPhase) -> Dict[str, Any]:
        """
        检查进入标准
        
        Args:
            test_phase: 测试阶段对象
            
        Returns:
            Dict[str, Any]: 检查结果
        """
        if not test_phase.entry_criteria:
            return {'passed': True, 'failed_criteria': []}
        
        failed_criteria = []
        
        for criterion in test_phase.entry_criteria:
            # 这里可以根据具体的标准类型进行检查
            # 示例：检查测试环境是否就绪
            if criterion.get('type') == 'environment_ready':
                # 实际检查逻辑
                if not await self._check_environment_ready(test_phase.test_plan_id):
                    failed_criteria.append(criterion.get('description', '测试环境未就绪'))
            
            # 示例：检查测试数据是否准备完成
            elif criterion.get('type') == 'test_data_ready':
                if not await self._check_test_data_ready(test_phase.test_plan_id):
                    failed_criteria.append(criterion.get('description', '测试数据未准备'))
        
        return {
            'passed': len(failed_criteria) == 0,
            'failed_criteria': failed_criteria
        }
    
    async def _check_exit_criteria(self, test_phase: TestPhase) -> Dict[str, Any]:
        """
        检查退出标准
        
        Args:
            test_phase: 测试阶段对象
            
        Returns:
            Dict[str, Any]: 检查结果
        """
        if not test_phase.exit_criteria:
            return {'passed': True, 'failed_criteria': []}
        
        failed_criteria = []
        
        # 获取阶段进度
        progress = await self.get_phase_progress(test_phase.id)
        
        for criterion in test_phase.exit_criteria:
            # 检查执行率标准
            if criterion.get('type') == 'execution_rate':
                required_rate = criterion.get('value', 100)
                if progress['execution_rate'] < required_rate:
                    failed_criteria.append(f"执行率未达标: {progress['execution_rate']}% < {required_rate}%")
            
            # 检查通过率标准
            elif criterion.get('type') == 'pass_rate':
                required_rate = criterion.get('value', 95)
                if progress['pass_rate'] < required_rate:
                    failed_criteria.append(f"通过率未达标: {progress['pass_rate']}% < {required_rate}%")
            
            # 检查缺陷数量标准
            elif criterion.get('type') == 'max_open_defects':
                max_defects = criterion.get('value', 0)
                open_defects = await self._count_open_defects_in_phase(test_phase.id)
                if open_defects > max_defects:
                    failed_criteria.append(f"未解决缺陷过多: {open_defects} > {max_defects}")
        
        return {
            'passed': len(failed_criteria) == 0,
            'failed_criteria': failed_criteria
        }
    
    async def _generate_phase_summary(self, test_phase: TestPhase) -> Dict[str, Any]:
        """
        生成阶段总结
        
        Args:
            test_phase: 测试阶段对象
            
        Returns:
            Dict[str, Any]: 阶段总结
        """
        # 获取阶段进度
        progress = await self.get_phase_progress(test_phase.id)
        
        # 计算阶段持续时间
        duration_days = 0
        if test_phase.actual_start_date and test_phase.actual_end_date:
            duration_days = (test_phase.actual_end_date - test_phase.actual_start_date).days
        
        # 获取阶段内的缺陷统计
        defect_stats = await self._get_phase_defect_statistics(test_phase.id)
        
        summary = {
            'phase_name': test_phase.phase_name,
            'duration_days': duration_days,
            'total_cases': progress['total_cases'],
            'executed_cases': progress['executed_cases'],
            'passed_cases': progress['passed_cases'],
            'failed_cases': progress['failed_cases'],
            'execution_rate': progress['execution_rate'],
            'pass_rate': progress['pass_rate'],
            'defect_statistics': defect_stats,
            'key_achievements': await self._identify_phase_achievements(test_phase.id),
            'lessons_learned': await self._extract_lessons_learned(test_phase.id),
            'recommendations': await self._generate_phase_recommendations(test_phase.id, progress),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        return summary
    
    async def _check_environment_ready(self, plan_id: int) -> bool:
        """检查测试环境是否就绪"""
        # 这里应该实现实际的环境检查逻辑
        # 例如：检查服务器状态、数据库连接等
        return True
    
    async def _check_test_data_ready(self, plan_id: int) -> bool:
        """检查测试数据是否准备完成"""
        # 这里应该实现实际的测试数据检查逻辑
        return True
    
    async def _count_open_defects_in_phase(self, phase_id: int) -> int:
        """统计阶段内未解决的缺陷数量"""
        from ..models.defect import Defect, DefectStatus
        
        count = self.db.query(Defect)\
            .join(TestExecution, Defect.execution_id == TestExecution.id)\
            .join(TestCase, TestExecution.test_case_id == TestCase.id)\
            .filter(TestCase.test_phase_id == phase_id)\
            .filter(Defect.status.in_([DefectStatus.OPEN, DefectStatus.IN_PROGRESS]))\
            .count()
        
        return count
    
    async def _get_phase_defect_statistics(self, phase_id: int) -> Dict[str, Any]:
        """获取阶段缺陷统计"""
        from ..models.defect import Defect, DefectSeverity, DefectStatus
        
        # 按严重程度统计
        severity_stats = self.db.query(
            Defect.severity,
            func.count(Defect.id).label('count')
        ).join(TestExecution, Defect.execution_id == TestExecution.id)\
         .join(TestCase, TestExecution.test_case_id == TestCase.id)\
         .filter(TestCase.test_phase_id == phase_id)\
         .group_by(Defect.severity)\
         .all()
        
        # 按状态统计
        status_stats = self.db.query(
            Defect.status,
            func.count(Defect.id).label('count')
        ).join(TestExecution, Defect.execution_id == TestExecution.id)\
         .join(TestCase, TestExecution.test_case_id == TestCase.id)\
         .filter(TestCase.test_phase_id == phase_id)\
         .group_by(Defect.status)\
         .all()
        
        return {
            'severity_distribution': {
                severity.value: count for severity, count in severity_stats
            },
            'status_distribution': {
                status.value: count for status, count in status_stats
            },
            'total_defects': sum(count for _, count in status_stats)
        }
    
    async def _identify_phase_achievements(self, phase_id: int) -> List[str]:
        """识别阶段成就"""
        achievements = []
        
        # 获取阶段进度
        progress = await self.get_phase_progress(phase_id)
        
        if progress['execution_rate'] >= 100:
            achievements.append("完成了所有计划的测试用例执行")
        
        if progress['pass_rate'] >= 95:
            achievements.append("测试通过率达到优秀水平")
        
        # 可以根据实际情况添加更多成就识别逻辑
        
        return achievements
    
    async def _extract_lessons_learned(self, phase_id: int) -> List[str]:
        """提取经验教训"""
        lessons = []
        
        # 这里可以基于阶段执行过程中的数据提取经验教训
        lessons.append("建立了有效的测试执行流程")
        lessons.append("识别了关键的质量风险点")
        
        return lessons
    
    async def _generate_phase_recommendations(
        self, 
        phase_id: int, 
        progress: Dict[str, Any]
    ) -> List[str]:
        """生成阶段建议"""
        recommendations = []
        
        if progress['pass_rate'] < 90:
            recommendations.append("建议加强代码质量控制，减少缺陷引入")
        
        if progress['execution_rate'] < 100:
            recommendations.append("建议优化测试执行效率，确保覆盖完整")
        
        return recommendations
    
    async def _clear_phase_cache(self, plan_id: int, phase_id: Optional[int] = None) -> None:
        """清除阶段相关缓存"""
        try:
            if phase_id:
                await self.cache_manager.delete_phase_progress(phase_id)
            
            # 清除计划相关缓存
            self.cache_manager.delete(TestCacheKeys.PROJECT_TEST_PLANS, project_id=plan_id)
            
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


class TestPhaseTemplateService:
    """测试阶段模板服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_phase_templates(self, project_type: str = None) -> List[Dict[str, Any]]:
        """
        获取阶段模板
        
        Args:
            project_type: 项目类型过滤
            
        Returns:
            List[Dict[str, Any]]: 阶段模板列表
        """
        templates = [
            {
                'id': 'waterfall_phases',
                'name': '瀑布模型测试阶段',
                'description': '适用于瀑布模型的标准测试阶段',
                'project_types': ['traditional', 'enterprise'],
                'phases': [
                    {
                        'phase_name': '单元测试',
                        'phase_type': 'unit',
                        'phase_order': 1,
                        'description': '开发人员进行的代码级测试',
                        'entry_criteria': [
                            {'type': 'code_complete', 'description': '代码开发完成'},
                            {'type': 'code_review', 'description': '代码评审通过'}
                        ],
                        'exit_criteria': [
                            {'type': 'execution_rate', 'value': 100, 'description': '所有单元测试执行完成'},
                            {'type': 'pass_rate', 'value': 95, 'description': '单元测试通过率达到95%'}
                        ]
                    },
                    {
                        'phase_name': '集成测试',
                        'phase_type': 'integration',
                        'phase_order': 2,
                        'description': '模块间接口和集成测试',
                        'entry_criteria': [
                            {'type': 'unit_test_complete', 'description': '单元测试完成'},
                            {'type': 'integration_environment_ready', 'description': '集成环境就绪'}
                        ],
                        'exit_criteria': [
                            {'type': 'execution_rate', 'value': 100, 'description': '所有集成测试执行完成'},
                            {'type': 'pass_rate', 'value': 90, 'description': '集成测试通过率达到90%'}
                        ]
                    },
                    {
                        'phase_name': '系统测试',
                        'phase_type': 'system',
                        'phase_order': 3,
                        'description': '完整系统功能和性能测试',
                        'entry_criteria': [
                            {'type': 'integration_test_complete', 'description': '集成测试完成'},
                            {'type': 'system_environment_ready', 'description': '系统测试环境就绪'}
                        ],
                        'exit_criteria': [
                            {'type': 'execution_rate', 'value': 100, 'description': '所有系统测试执行完成'},
                            {'type': 'pass_rate', 'value': 95, 'description': '系统测试通过率达到95%'},
                            {'type': 'max_open_defects', 'value': 0, 'description': '无未解决的高严重性缺陷'}
                        ]
                    },
                    {
                        'phase_name': '验收测试',
                        'phase_type': 'acceptance',
                        'phase_order': 4,
                        'description': '用户验收测试',
                        'entry_criteria': [
                            {'type': 'system_test_complete', 'description': '系统测试完成'},
                            {'type': 'production_like_environment', 'description': '类生产环境就绪'}
                        ],
                        'exit_criteria': [
                            {'type': 'execution_rate', 'value': 100, 'description': '所有验收测试执行完成'},
                            {'type': 'pass_rate', 'value': 100, 'description': '验收测试通过率达到100%'}
                        ]
                    }
                ]
            },
            {
                'id': 'agile_phases',
                'name': '敏捷测试阶段',
                'description': '适用于敏捷开发的测试阶段',
                'project_types': ['agile', 'scrum', 'web'],
                'phases': [
                    {
                        'phase_name': '迭代测试',
                        'phase_type': 'iteration',
                        'phase_order': 1,
                        'description': '迭代内的功能测试',
                        'entry_criteria': [
                            {'type': 'story_development_complete', 'description': '用户故事开发完成'},
                            {'type': 'test_environment_ready', 'description': '测试环境就绪'}
                        ],
                        'exit_criteria': [
                            {'type': 'execution_rate', 'value': 100, 'description': '所有计划测试执行完成'},
                            {'type': 'pass_rate', 'value': 90, 'description': '测试通过率达到90%'}
                        ]
                    },
                    {
                        'phase_name': '回归测试',
                        'phase_type': 'regression',
                        'phase_order': 2,
                        'description': '确保新功能不影响现有功能',
                        'entry_criteria': [
                            {'type': 'iteration_test_complete', 'description': '迭代测试完成'},
                            {'type': 'automation_suite_ready', 'description': '自动化测试套件就绪'}
                        ],
                        'exit_criteria': [
                            {'type': 'execution_rate', 'value': 100, 'description': '回归测试执行完成'},
                            {'type': 'pass_rate', 'value': 95, 'description': '回归测试通过率达到95%'}
                        ]
                    }
                ]
            }
        ]
        
        if project_type:
            templates = [t for t in templates if project_type in t['project_types']]
        
        return templates
    
    async def apply_phase_template(
        self, 
        template_id: str, 
        plan_id: int, 
        customizations: Dict[str, Any] = None
    ) -> List[TestPhase]:
        """
        应用阶段模板
        
        Args:
            template_id: 模板ID
            plan_id: 测试计划ID
            customizations: 自定义配置
            
        Returns:
            List[TestPhase]: 创建的阶段列表
        """
        try:
            # 获取模板
            templates = await self.get_phase_templates()
            template = next((t for t in templates if t['id'] == template_id), None)
            
            if not template:
                raise NotFoundError("阶段模板不存在")
            
            # 创建阶段
            created_phases = []
            for phase_config in template['phases']:
                # 应用自定义配置
                if customizations and phase_config['phase_name'] in customizations:
                    phase_config.update(customizations[phase_config['phase_name']])
                
                # 创建阶段
                test_phase = TestPhase(
                    test_plan_id=plan_id,
                    phase_name=phase_config['phase_name'],
                    phase_type=phase_config['phase_type'],
                    description=phase_config['description'],
                    phase_order=phase_config['phase_order'],
                    entry_criteria=phase_config['entry_criteria'],
                    exit_criteria=phase_config['exit_criteria']
                )
                
                self.db.add(test_phase)
                created_phases.append(test_phase)
            
            # 提交事务
            self.db.commit()
            
            logger.info(f"阶段模板应用成功: {template_id}, 计划ID: {plan_id}")
            
            return created_phases
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"应用阶段模板失败: {str(e)}")
            raise