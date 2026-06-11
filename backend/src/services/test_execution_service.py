"""
测试执行管理服务
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import selectinload

from ..models.test_case import TestExecution, TestCase, ExecutionStatus, Defect
from ..models.test_plan import TestPlan
from ..models.user import User
from ..schemas.test_execution import (
    StartManualExecutionRequest, CompleteManualExecutionRequest,
    UpdateExecutionStepRequest, PauseExecutionRequest, ResumeExecutionRequest,
    BatchExecutionRequest, AutomationExecutionRequest,
    TestExecutionResponse, ExecutionProgressResponse, BatchExecutionResponse,
    AutomationExecutionResponse, ExecutionStatisticsResponse,
    ExecutionStepResponse, ExecutionType
)
from ..utils.redis_client import RedisClient
from ..utils.file_storage_utils import FileStorageUtils
from .notification_service import NotificationService
from .defect_service import DefectService
from .test_plan_service import TestPlanService
from ..core.exceptions import ValidationError, NotFoundError, PermissionError


class TestExecutionService:
    """测试执行管理服务"""
    
    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[RedisClient] = None,
        file_storage: Optional[FileStorageUtils] = None,
        notification_service: Optional[NotificationService] = None,
        defect_service: Optional[DefectService] = None,
        test_plan_service: Optional[TestPlanService] = None
    ):
        self.db = db
        self.redis = redis_client
        self.file_storage = file_storage
        self.notification_service = notification_service
        self.defect_service = defect_service
        self.test_plan_service = test_plan_service
    
    async def start_manual_execution(
        self, 
        request: StartManualExecutionRequest, 
        executor_id: int
    ) -> TestExecutionResponse:
        """开始手动测试执行"""
        # 1. 验证执行权限
        await self._validate_execution_permission(request.test_case_id, executor_id)
        
        # 2. 检查用例状态
        test_case = await self._get_test_case_by_id(request.test_case_id)
        if test_case.status != "ACTIVE":
            raise ValidationError("测试用例状态不允许执行")
        
        # 3. 检查是否已有进行中的执行
        existing_execution = await self._get_active_execution(request.test_case_id)
        if existing_execution:
            return await self._build_execution_response(existing_execution)
        
        # 4. 生成执行编码
        execution_code = await self._generate_execution_code(test_case.case_code)
        
        # 5. 创建执行记录
        execution = TestExecution(
            execution_code=execution_code,
            test_case_id=request.test_case_id,
            test_plan_id=test_case.test_plan_id,
            execution_type=ExecutionType.MANUAL,
            execution_status=ExecutionStatus.IN_PROGRESS,
            test_environment=request.test_environment,
            browser_info=request.browser_info,
            os_info=request.os_info,
            execution_notes=request.execution_notes,
            executor_id=executor_id,
            started_at=datetime.utcnow()
        )
        
        # 6. 保存执行记录
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        
        # 7. 缓存执行状态
        await self._cache_execution_status(execution.id, ExecutionStatus.IN_PROGRESS)
        
        # 8. 更新用例执行状态
        await self._update_case_execution_status(request.test_case_id, ExecutionStatus.IN_PROGRESS)
        
        # 9. 发送执行开始通知
        await self._send_execution_started_notifications(execution)
        
        # 10. 构建响应
        return await self._build_execution_response(execution)
    
    async def complete_manual_execution(
        self, 
        request: CompleteManualExecutionRequest,
        executor_id: int
    ) -> TestExecutionResponse:
        """完成手动测试执行"""
        # 1. 获取执行记录
        execution = await self._get_execution_by_id(request.execution_id)
        if not execution:
            raise NotFoundError("执行记录不存在")
        
        # 2. 验证执行权限
        if execution.executor_id != executor_id:
            raise PermissionError("无权限操作此执行记录")
        
        # 3. 验证执行状态
        if execution.execution_status != ExecutionStatus.IN_PROGRESS:
            raise ValidationError("执行状态不正确")
        
        # 4. 处理附件上传
        screenshots = await self._process_attachments(request.screenshots, "screenshots")
        logs = await self._process_attachments(request.logs, "logs")
        videos = await self._process_attachments(request.videos, "videos")
        
        # 5. 更新执行结果
        execution.execution_status = request.execution_status
        execution.actual_result = request.actual_result
        execution.failure_reason = request.failure_reason
        execution.execution_notes = request.execution_notes
        execution.completed_at = datetime.utcnow()
        execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
        execution.screenshots = screenshots
        execution.logs = logs
        execution.videos = videos
        
        # 6. 保存执行结果
        await self.db.commit()
        
        # 7. 更新缓存
        await self._cache_execution_status(execution.id, request.execution_status)
        
        # 8. 更新用例执行状态
        await self._update_case_execution_status(execution.test_case_id, request.execution_status)
        
        # 9. 如果执行失败且需要创建缺陷
        if request.execution_status == ExecutionStatus.FAILED and request.create_defect:
            await self._create_defect_from_execution(execution, request.defect_data)
        
        # 10. 更新测试计划进度
        if execution.test_plan_id:
            await self.test_plan_service.update_plan_progress(execution.test_plan_id)
        
        # 11. 发送执行完成通知
        await self._send_execution_completed_notifications(execution)
        
        # 12. 构建响应
        return await self._build_execution_response(execution)
    
    async def update_execution_step(
        self,
        request: UpdateExecutionStepRequest,
        executor_id: int
    ) -> ExecutionStepResponse:
        """更新执行步骤"""
        # 1. 获取执行记录
        execution = await self._get_execution_by_id(request.execution_id)
        if not execution:
            raise NotFoundError("执行记录不存在")
        
        # 2. 验证权限
        if execution.executor_id != executor_id:
            raise PermissionError("无权限操作此执行记录")
        
        # 3. 获取测试用例步骤
        test_case = await self._get_test_case_by_id(execution.test_case_id)
        test_steps = test_case.test_steps or []
        
        if request.step_index >= len(test_steps):
            raise ValidationError("步骤索引超出范围")
        
        # 4. 处理附件
        attachments = await self._process_attachments(request.attachments, "step_attachments")
        
        # 5. 更新步骤状态（存储在Redis中）
        step_key = f"execution_step:{request.execution_id}:{request.step_index}"
        step_data = {
            "step_status": request.step_status.value,
            "step_result": request.step_result,
            "step_notes": request.step_notes,
            "attachments": attachments,
            "executed_at": datetime.utcnow().isoformat()
        }
        await self.redis.hset(step_key, mapping=step_data)
        
        # 6. 更新执行进度
        await self._update_execution_progress(request.execution_id)
        
        # 7. 构建步骤响应
        step_info = test_steps[request.step_index]
        return ExecutionStepResponse(
            step_index=request.step_index,
            step_description=step_info.get("description", ""),
            expected_result=step_info.get("expected_result", ""),
            actual_result=request.step_result,
            step_status=request.step_status,
            step_notes=request.step_notes,
            attachments=attachments,
            executed_at=datetime.utcnow()
        )
    
    async def pause_execution(
        self,
        request: PauseExecutionRequest,
        executor_id: int
    ) -> TestExecutionResponse:
        """暂停执行"""
        # 1. 获取执行记录
        execution = await self._get_execution_by_id(request.execution_id)
        if not execution:
            raise NotFoundError("执行记录不存在")
        
        # 2. 验证权限
        if execution.executor_id != executor_id:
            raise PermissionError("无权限操作此执行记录")
        
        # 3. 验证状态
        if execution.execution_status != ExecutionStatus.IN_PROGRESS:
            raise ValidationError("只能暂停进行中的执行")
        
        # 4. 暂停执行
        pause_data = {
            "paused_at": datetime.utcnow().isoformat(),
            "pause_reason": request.pause_reason,
            "paused_by": executor_id
        }
        await self.redis.hset(f"execution_pause:{request.execution_id}", mapping=pause_data)
        
        # 5. 更新缓存状态
        await self._cache_execution_status(execution.id, "PAUSED")
        
        # 6. 发送暂停通知
        await self._send_execution_paused_notifications(execution, request.pause_reason)
        
        return await self._build_execution_response(execution)
    
    async def resume_execution(
        self,
        request: ResumeExecutionRequest,
        executor_id: int
    ) -> TestExecutionResponse:
        """恢复执行"""
        # 1. 获取执行记录
        execution = await self._get_execution_by_id(request.execution_id)
        if not execution:
            raise NotFoundError("执行记录不存在")
        
        # 2. 验证权限
        if execution.executor_id != executor_id:
            raise PermissionError("无权限操作此执行记录")
        
        # 3. 检查是否已暂停
        pause_data = await self.redis.hgetall(f"execution_pause:{request.execution_id}")
        if not pause_data:
            raise ValidationError("执行未暂停")
        
        # 4. 恢复执行
        resume_data = {
            "resumed_at": datetime.utcnow().isoformat(),
            "resume_notes": request.resume_notes,
            "resumed_by": executor_id
        }
        await self.redis.hset(f"execution_resume:{request.execution_id}", mapping=resume_data)
        
        # 5. 删除暂停状态
        await self.redis.delete(f"execution_pause:{request.execution_id}")
        
        # 6. 更新缓存状态
        await self._cache_execution_status(execution.id, ExecutionStatus.IN_PROGRESS)
        
        # 7. 发送恢复通知
        await self._send_execution_resumed_notifications(execution, request.resume_notes)
        
        return await self._build_execution_response(execution)
    
    async def get_execution_progress(self, execution_id: int) -> ExecutionProgressResponse:
        """获取执行进度"""
        # 1. 获取执行记录
        execution = await self._get_execution_by_id(execution_id)
        if not execution:
            raise NotFoundError("执行记录不存在")
        
        # 2. 获取测试用例步骤
        test_case = await self._get_test_case_by_id(execution.test_case_id)
        test_steps = test_case.test_steps or []
        total_steps = len(test_steps)
        
        # 3. 统计步骤执行情况
        completed_steps = 0
        passed_steps = 0
        failed_steps = 0
        current_step = None
        
        for i in range(total_steps):
            step_key = f"execution_step:{execution_id}:{i}"
            step_data = await self.redis.hgetall(step_key)
            
            if step_data:
                completed_steps += 1
                step_status = step_data.get("step_status")
                if step_status == ExecutionStatus.PASSED.value:
                    passed_steps += 1
                elif step_status == ExecutionStatus.FAILED.value:
                    failed_steps += 1
            else:
                if current_step is None:
                    current_step = i
        
        # 4. 计算进度
        progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        # 5. 估算完成时间
        estimated_completion = None
        if execution.started_at and completed_steps > 0:
            elapsed_time = datetime.utcnow() - execution.started_at
            avg_time_per_step = elapsed_time.total_seconds() / completed_steps
            remaining_steps = total_steps - completed_steps
            estimated_completion = datetime.utcnow() + timedelta(seconds=avg_time_per_step * remaining_steps)
        
        return ExecutionProgressResponse(
            execution_id=execution_id,
            total_steps=total_steps,
            completed_steps=completed_steps,
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            current_step=current_step,
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion
        )
    
    async def get_execution_statistics(
        self,
        project_id: Optional[int] = None,
        test_plan_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ExecutionStatisticsResponse:
        """获取执行统计"""
        # 构建查询条件
        conditions = []
        if project_id:
            conditions.append(TestPlan.project_id == project_id)
        if test_plan_id:
            conditions.append(TestExecution.test_plan_id == test_plan_id)
        if start_date:
            conditions.append(TestExecution.started_at >= start_date)
        if end_date:
            conditions.append(TestExecution.started_at <= end_date)
        
        # 执行统计查询
        query = select(
            func.count(TestExecution.id).label("total_executions"),
            func.sum(func.case((TestExecution.execution_type == ExecutionType.MANUAL, 1), else_=0)).label("manual_executions"),
            func.sum(func.case((TestExecution.execution_type == ExecutionType.AUTOMATED, 1), else_=0)).label("automated_executions"),
            func.sum(func.case((TestExecution.execution_status == ExecutionStatus.PASSED, 1), else_=0)).label("passed_executions"),
            func.sum(func.case((TestExecution.execution_status == ExecutionStatus.FAILED, 1), else_=0)).label("failed_executions"),
            func.sum(func.case((TestExecution.execution_status == ExecutionStatus.BLOCKED, 1), else_=0)).label("blocked_executions"),
            func.sum(func.case((TestExecution.execution_status == ExecutionStatus.SKIPPED, 1), else_=0)).label("skipped_executions"),
            func.avg(TestExecution.duration).label("average_duration")
        ).select_from(TestExecution)
        
        if project_id:
            query = query.join(TestPlan, TestExecution.test_plan_id == TestPlan.id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await self.db.execute(query)
        stats = result.first()
        
        # 计算通过率
        total_completed = (stats.passed_executions or 0) + (stats.failed_executions or 0)
        pass_rate = (stats.passed_executions / total_completed * 100) if total_completed > 0 else 0
        
        # 获取执行趋势（最近30天）
        execution_trend = await self._get_execution_trend(project_id, test_plan_id)
        
        return ExecutionStatisticsResponse(
            total_executions=stats.total_executions or 0,
            manual_executions=stats.manual_executions or 0,
            automated_executions=stats.automated_executions or 0,
            passed_executions=stats.passed_executions or 0,
            failed_executions=stats.failed_executions or 0,
            blocked_executions=stats.blocked_executions or 0,
            skipped_executions=stats.skipped_executions or 0,
            pass_rate=pass_rate,
            average_duration=stats.average_duration,
            execution_trend=execution_trend
        )
    
    # 私有方法
    async def _validate_execution_permission(self, test_case_id: int, executor_id: int) -> None:
        """验证执行权限"""
        # 检查用户是否有执行权限
        test_case = await self._get_test_case_by_id(test_case_id)
        
        # 检查是否是用例负责人或测试计划成员
        if test_case.assignee_id == executor_id:
            return
        
        if test_case.test_plan_id:
            test_plan = await self.db.get(TestPlan, test_case.test_plan_id)
            if test_plan and test_plan.test_manager_id == executor_id:
                return
        
        # 检查项目权限（这里可以集成项目权限服务）
        # TODO: 集成项目权限检查
        
        raise PermissionError("无权限执行此测试用例")
    
    async def _get_test_case_by_id(self, test_case_id: int) -> TestCase:
        """根据ID获取测试用例"""
        test_case = await self.db.get(TestCase, test_case_id)
        if not test_case:
            raise NotFoundError("测试用例不存在")
        return test_case
    
    async def _get_execution_by_id(self, execution_id: int) -> TestExecution:
        """根据ID获取执行记录"""
        execution = await self.db.get(TestExecution, execution_id)
        if not execution:
            raise NotFoundError("执行记录不存在")
        return execution
    
    async def _get_active_execution(self, test_case_id: int) -> Optional[TestExecution]:
        """获取活跃的执行记录"""
        query = select(TestExecution).where(
            and_(
                TestExecution.test_case_id == test_case_id,
                TestExecution.execution_status == ExecutionStatus.IN_PROGRESS
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _generate_execution_code(self, test_case_code: str) -> str:
        """生成执行编码"""
        today = datetime.now().strftime("%Y%m%d")
        
        # 查询今天的执行数量
        query = select(func.count(TestExecution.id)).where(
            TestExecution.execution_code.like(f"EXE-{test_case_code}-{today}-%")
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0
        
        return f"EXE-{test_case_code}-{today}-{count + 1:03d}"
    
    async def _cache_execution_status(self, execution_id: int, status: ExecutionStatus) -> None:
        """缓存执行状态"""
        await self.redis.setex(
            f"execution_status:{execution_id}",
            3600,  # 1小时过期
            status.value if isinstance(status, ExecutionStatus) else status
        )
    
    async def _update_case_execution_status(self, test_case_id: int, status: ExecutionStatus) -> None:
        """更新用例执行状态"""
        await self.redis.setex(
            f"case_execution_status:{test_case_id}",
            3600,
            status.value
        )
    
    async def _process_attachments(
        self, 
        attachments: Optional[List[Dict[str, Any]]], 
        attachment_type: str
    ) -> Optional[List[Dict[str, Any]]]:
        """处理附件上传"""
        if not attachments:
            return None
        
        processed_attachments = []
        for attachment in attachments:
            if "file_data" in attachment:
                # 上传文件
                file_path = await self.file_storage.save_file(
                    attachment["file_data"],
                    f"test_executions/{attachment_type}",
                    attachment.get("filename", f"{uuid.uuid4()}.png")
                )
                processed_attachments.append({
                    "filename": attachment.get("filename"),
                    "file_path": file_path,
                    "file_size": attachment.get("file_size"),
                    "content_type": attachment.get("content_type"),
                    "uploaded_at": datetime.utcnow().isoformat()
                })
            else:
                processed_attachments.append(attachment)
        
        return processed_attachments
    
    async def _create_defect_from_execution(
        self, 
        execution: TestExecution, 
        defect_data: Optional[Dict[str, Any]]
    ) -> None:
        """从执行记录创建缺陷"""
        if not defect_data:
            defect_data = {}
        
        # 构建缺陷数据
        defect_request = {
            "title": defect_data.get("title", f"执行失败: {execution.execution_code}"),
            "description": defect_data.get("description", execution.failure_reason or "测试执行失败"),
            "steps_to_reproduce": execution.execution_notes,
            "test_execution_id": execution.id,
            "test_case_id": execution.test_case_id,
            "defect_type": defect_data.get("defect_type", "FUNCTIONAL"),
            "severity": defect_data.get("severity", "MEDIUM"),
            "priority": defect_data.get("priority", "MEDIUM"),
            "test_environment": execution.test_environment,
            "attachments": execution.screenshots or []
        }
        
        # 调用缺陷服务创建缺陷
        await self.defect_service.create_defect(defect_request, execution.executor_id)
    
    async def _update_execution_progress(self, execution_id: int) -> None:
        """更新执行进度"""
        progress = await self.get_execution_progress(execution_id)
        
        # 缓存进度信息
        progress_data = {
            "total_steps": progress.total_steps,
            "completed_steps": progress.completed_steps,
            "passed_steps": progress.passed_steps,
            "failed_steps": progress.failed_steps,
            "progress_percentage": progress.progress_percentage,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.hset(f"execution_progress:{execution_id}", mapping=progress_data)
    
    async def _get_execution_trend(
        self, 
        project_id: Optional[int], 
        test_plan_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """获取执行趋势"""
        # 获取最近30天的执行趋势
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # 构建查询
        query = select(
            func.date(TestExecution.started_at).label("execution_date"),
            func.count(TestExecution.id).label("total_count"),
            func.sum(func.case((TestExecution.execution_status == ExecutionStatus.PASSED, 1), else_=0)).label("passed_count"),
            func.sum(func.case((TestExecution.execution_status == ExecutionStatus.FAILED, 1), else_=0)).label("failed_count")
        ).where(
            and_(
                TestExecution.started_at >= start_date,
                TestExecution.started_at <= end_date
            )
        ).group_by(func.date(TestExecution.started_at))
        
        if project_id:
            query = query.join(TestPlan, TestExecution.test_plan_id == TestPlan.id).where(
                TestPlan.project_id == project_id
            )
        
        if test_plan_id:
            query = query.where(TestExecution.test_plan_id == test_plan_id)
        
        result = await self.db.execute(query)
        trend_data = []
        
        for row in result:
            trend_data.append({
                "date": row.execution_date.isoformat(),
                "total_count": row.total_count,
                "passed_count": row.passed_count,
                "failed_count": row.failed_count,
                "pass_rate": (row.passed_count / row.total_count * 100) if row.total_count > 0 else 0
            })
        
        return trend_data
    
    async def _build_execution_response(self, execution: TestExecution) -> TestExecutionResponse:
        """构建执行响应"""
        # 获取执行步骤
        execution_steps = await self._get_execution_steps(execution.id)
        
        return TestExecutionResponse(
            id=execution.id,
            execution_code=execution.execution_code,
            test_case_id=execution.test_case_id,
            test_plan_id=execution.test_plan_id,
            execution_type=execution.execution_type,
            execution_status=execution.execution_status,
            actual_result=execution.actual_result,
            failure_reason=execution.failure_reason,
            execution_notes=execution.execution_notes,
            test_environment=execution.test_environment,
            browser_info=execution.browser_info,
            os_info=execution.os_info,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            duration=execution.duration,
            executor_id=execution.executor_id,
            screenshots=execution.screenshots,
            logs=execution.logs,
            videos=execution.videos,
            execution_steps=execution_steps,
            created_at=execution.created_at,
            updated_at=execution.updated_at
        )
    
    async def _get_execution_steps(self, execution_id: int) -> List[ExecutionStepResponse]:
        """获取执行步骤"""
        # 从Redis获取步骤信息
        steps = []
        step_keys = await self.redis.keys(f"execution_step:{execution_id}:*")
        
        for key in sorted(step_keys):
            step_index = int(key.split(":")[-1])
            step_data = await self.redis.hgetall(key)
            
            if step_data:
                steps.append(ExecutionStepResponse(
                    step_index=step_index,
                    step_description=step_data.get("step_description", ""),
                    expected_result=step_data.get("expected_result", ""),
                    actual_result=step_data.get("step_result"),
                    step_status=ExecutionStatus(step_data.get("step_status")),
                    step_notes=step_data.get("step_notes"),
                    attachments=step_data.get("attachments"),
                    executed_at=datetime.fromisoformat(step_data.get("executed_at")) if step_data.get("executed_at") else None
                ))
        
        return steps
    
    # 通知方法
    async def _send_execution_started_notifications(self, execution: TestExecution) -> None:
        """发送执行开始通知"""
        # TODO: 实现通知逻辑
        pass
    
    async def _send_execution_completed_notifications(self, execution: TestExecution) -> None:
        """发送执行完成通知"""
        # TODO: 实现通知逻辑
        pass
    
    async def _send_execution_paused_notifications(self, execution: TestExecution, reason: str) -> None:
        """发送执行暂停通知"""
        # TODO: 实现通知逻辑
        pass
    
    async def _send_execution_resumed_notifications(self, execution: TestExecution, notes: str) -> None:
        """发送执行恢复通知"""
        # TODO: 实现通知逻辑
        pass
