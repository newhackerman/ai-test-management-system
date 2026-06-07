"""
自动化测试执行服务
"""
import asyncio
import json
import uuid
import subprocess
import tempfile
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import selectinload

from ..models.test_case import TestExecution, TestCase, ExecutionStatus
from ..models.test_plan import TestPlan
from ..schemas.test_execution import (
    AutomationExecutionRequest, BatchExecutionRequest,
    AutomationExecutionResponse, BatchExecutionResponse,
    ExecutionType
)
from ..utils.redis_client import RedisClient
from ..utils.file_storage_utils import FileStorageUtils
from .notification_service import NotificationService
from ..core.exceptions import ValidationError, NotFoundError, ExecutionError


class AutomationFramework:
    """自动化框架枚举"""
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    CYPRESS = "cypress"
    PYTEST = "pytest"
    JEST = "jest"


class AutomationExecutionService:
    """自动化测试执行服务"""
    
    def __init__(
        self,
        db: AsyncSession,
        redis_client: RedisClient,
        file_storage: FileStorageUtils,
        notification_service: NotificationService
    ):
        self.db = db
        self.redis = redis_client
        self.file_storage = file_storage
        self.notification_service = notification_service
        self.execution_queue = "automation_execution_queue"
        self.result_queue = "automation_result_queue"
    
    async def start_automation_execution(
        self,
        request: AutomationExecutionRequest,
        executor_id: int
    ) -> AutomationExecutionResponse:
        """开始自动化测试执行"""
        # 1. 验证测试用例
        automation_cases = await self._validate_automation_cases(request.test_case_ids)
        if not automation_cases:
            raise ValidationError("没有可执行的自动化用例")
        
        # 2. 生成执行ID
        execution_id = str(uuid.uuid4())
        
        # 3. 创建执行任务
        execution_task = {
            "execution_id": execution_id,
            "test_case_ids": request.test_case_ids,
            "framework": request.framework,
            "test_environment": request.test_environment,
            "browser": request.browser,
            "parallel_count": request.parallel_count,
            "retry_count": request.retry_count,
            "timeout": request.timeout,
            "execution_config": request.execution_config or {},
            "executor_id": executor_id,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
            "total_cases": len(request.test_case_ids)
        }
        
        # 4. 保存执行任务到Redis
        await self.redis.hset(f"automation_execution:{execution_id}", mapping=execution_task)
        
        # 5. 提交到执行队列
        await self.redis.lpush(self.execution_queue, execution_id)
        
        # 6. 启动执行处理器（如果还没有运行）
        await self._ensure_execution_processor_running()
        
        # 7. 发送开始通知
        await self._send_automation_started_notifications(execution_task)
        
        return AutomationExecutionResponse(
            execution_id=execution_id,
            framework=request.framework,
            test_environment=request.test_environment,
            status="PENDING",
            total_cases=len(request.test_case_ids),
            completed_cases=0,
            passed_cases=0,
            failed_cases=0,
            progress_percentage=0.0,
            started_at=datetime.utcnow(),
            estimated_completion=None,
            execution_logs=None,
            test_results=None
        )
    
    async def start_batch_execution(
        self,
        request: BatchExecutionRequest,
        executor_id: int
    ) -> BatchExecutionResponse:
        """开始批量执行"""
        # 1. 生成批次ID
        batch_id = str(uuid.uuid4())
        
        # 2. 根据执行类型分组处理
        if request.execution_type == ExecutionType.AUTOMATED:
            # 自动化批量执行
            automation_request = AutomationExecutionRequest(
                test_case_ids=request.test_case_ids,
                framework="playwright",  # 默认框架
                test_environment=request.test_environment,
                parallel_count=request.parallel_count,
                retry_count=request.retry_count,
                execution_config=request.execution_config
            )
            automation_response = await self.start_automation_execution(automation_request, executor_id)
            
            # 创建批量执行记录
            executions = []
            for test_case_id in request.test_case_ids:
                execution = TestExecution(
                    execution_code=await self._generate_execution_code(test_case_id),
                    test_case_id=test_case_id,
                    execution_type=ExecutionType.AUTOMATED,
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    test_environment=request.test_environment,
                    executor_id=executor_id,
                    started_at=datetime.utcnow()
                )
                self.db.add(execution)
                executions.append(execution)
            
            await self.db.commit()
            
            # 构建响应
            execution_responses = []
            for execution in executions:
                execution_responses.append(await self._build_execution_response(execution))
            
            return BatchExecutionResponse(
                batch_id=batch_id,
                total_cases=len(request.test_case_ids),
                completed_cases=0,
                passed_cases=0,
                failed_cases=0,
                blocked_cases=0,
                skipped_cases=0,
                execution_status="RUNNING",
                started_at=datetime.utcnow(),
                estimated_completion=None,
                executions=execution_responses
            )
        
        else:
            # 手动批量执行（创建执行记录，等待手动执行）
            executions = []
            for test_case_id in request.test_case_ids:
                execution = TestExecution(
                    execution_code=await self._generate_execution_code(test_case_id),
                    test_case_id=test_case_id,
                    execution_type=ExecutionType.MANUAL,
                    execution_status=ExecutionStatus.NOT_EXECUTED,
                    test_environment=request.test_environment,
                    executor_id=executor_id
                )
                self.db.add(execution)
                executions.append(execution)
            
            await self.db.commit()
            
            # 构建响应
            execution_responses = []
            for execution in executions:
                execution_responses.append(await self._build_execution_response(execution))
            
            return BatchExecutionResponse(
                batch_id=batch_id,
                total_cases=len(request.test_case_ids),
                completed_cases=0,
                passed_cases=0,
                failed_cases=0,
                blocked_cases=0,
                skipped_cases=0,
                execution_status="PENDING",
                started_at=datetime.utcnow(),
                estimated_completion=None,
                executions=execution_responses
            )
    
    async def get_automation_execution_status(self, execution_id: str) -> AutomationExecutionResponse:
        """获取自动化执行状态"""
        # 1. 获取执行任务
        execution_data = await self.redis.hgetall(f"automation_execution:{execution_id}")
        if not execution_data:
            raise NotFoundError("自动化执行任务不存在")
        
        # 2. 获取执行结果
        results = await self._get_execution_results(execution_id)
        
        # 3. 统计执行情况
        total_cases = int(execution_data.get("total_cases", 0))
        completed_cases = len(results)
        passed_cases = len([r for r in results if r.get("status") == "PASSED"])
        failed_cases = len([r for r in results if r.get("status") == "FAILED"])
        
        # 4. 计算进度
        progress_percentage = (completed_cases / total_cases * 100) if total_cases > 0 else 0
        
        # 5. 估算完成时间
        estimated_completion = None
        if execution_data.get("started_at") and completed_cases > 0:
            started_at = datetime.fromisoformat(execution_data["started_at"])
            elapsed_time = datetime.utcnow() - started_at
            avg_time_per_case = elapsed_time.total_seconds() / completed_cases
            remaining_cases = total_cases - completed_cases
            if remaining_cases > 0:
                estimated_completion = datetime.utcnow() + timedelta(seconds=avg_time_per_case * remaining_cases)
        
        # 6. 获取执行日志
        execution_logs = await self._get_execution_logs(execution_id)
        
        return AutomationExecutionResponse(
            execution_id=execution_id,
            framework=execution_data.get("framework", ""),
            test_environment=execution_data.get("test_environment", ""),
            status=execution_data.get("status", "UNKNOWN"),
            total_cases=total_cases,
            completed_cases=completed_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            progress_percentage=progress_percentage,
            started_at=datetime.fromisoformat(execution_data["started_at"]) if execution_data.get("started_at") else datetime.utcnow(),
            estimated_completion=estimated_completion,
            execution_logs=execution_logs,
            test_results=results
        )
    
    async def cancel_automation_execution(self, execution_id: str, executor_id: int) -> bool:
        """取消自动化执行"""
        # 1. 获取执行任务
        execution_data = await self.redis.hgetall(f"automation_execution:{execution_id}")
        if not execution_data:
            raise NotFoundError("自动化执行任务不存在")
        
        # 2. 验证权限
        if int(execution_data.get("executor_id", 0)) != executor_id:
            raise ValidationError("无权限取消此执行任务")
        
        # 3. 更新状态为取消
        await self.redis.hset(f"automation_execution:{execution_id}", "status", "CANCELLED")
        await self.redis.hset(f"automation_execution:{execution_id}", "cancelled_at", datetime.utcnow().isoformat())
        
        # 4. 从队列中移除（如果还在队列中）
        await self.redis.lrem(self.execution_queue, 0, execution_id)
        
        # 5. 停止正在运行的进程
        await self._stop_execution_process(execution_id)
        
        # 6. 发送取消通知
        await self._send_automation_cancelled_notifications(execution_data)
        
        return True
    
    async def retry_failed_cases(self, execution_id: str, executor_id: int) -> AutomationExecutionResponse:
        """重试失败的用例"""
        # 1. 获取原执行任务
        original_execution = await self.redis.hgetall(f"automation_execution:{execution_id}")
        if not original_execution:
            raise NotFoundError("原执行任务不存在")
        
        # 2. 获取失败的用例
        results = await self._get_execution_results(execution_id)
        failed_case_ids = [r["test_case_id"] for r in results if r.get("status") == "FAILED"]
        
        if not failed_case_ids:
            raise ValidationError("没有失败的用例需要重试")
        
        # 3. 创建重试执行任务
        retry_request = AutomationExecutionRequest(
            test_case_ids=failed_case_ids,
            framework=original_execution.get("framework", "playwright"),
            test_environment=original_execution.get("test_environment", ""),
            browser=original_execution.get("browser", "chrome"),
            parallel_count=int(original_execution.get("parallel_count", 1)),
            retry_count=int(original_execution.get("retry_count", 0)),
            timeout=int(original_execution.get("timeout", 300)),
            execution_config=json.loads(original_execution.get("execution_config", "{}"))
        )
        
        return await self.start_automation_execution(retry_request, executor_id)
    
    # 执行处理器
    async def _ensure_execution_processor_running(self):
        """确保执行处理器正在运行"""
        processor_key = "automation_processor_running"
        is_running = await self.redis.get(processor_key)
        
        if not is_running:
            # 启动执行处理器
            asyncio.create_task(self._execution_processor())
            await self.redis.setex(processor_key, 300, "true")  # 5分钟过期
    
    async def _execution_processor(self):
        """执行处理器"""
        while True:
            try:
                # 从队列获取执行任务
                execution_id = await self.redis.brpop(self.execution_queue, timeout=10)
                if not execution_id:
                    continue
                
                execution_id = execution_id[1].decode() if isinstance(execution_id[1], bytes) else execution_id[1]
                
                # 处理执行任务
                await self._process_execution_task(execution_id)
                
            except Exception as e:
                print(f"执行处理器错误: {e}")
                await asyncio.sleep(5)
    
    async def _process_execution_task(self, execution_id: str):
        """处理执行任务"""
        try:
            # 1. 获取执行任务
            execution_data = await self.redis.hgetall(f"automation_execution:{execution_id}")
            if not execution_data:
                return
            
            # 2. 更新状态为运行中
            await self.redis.hset(f"automation_execution:{execution_id}", "status", "RUNNING")
            await self.redis.hset(f"automation_execution:{execution_id}", "started_at", datetime.utcnow().isoformat())
            
            # 3. 根据框架执行测试
            framework = execution_data.get("framework", "playwright")
            test_case_ids = json.loads(execution_data.get("test_case_ids", "[]"))
            
            if framework == AutomationFramework.PLAYWRIGHT:
                await self._execute_playwright_tests(execution_id, test_case_ids, execution_data)
            elif framework == AutomationFramework.SELENIUM:
                await self._execute_selenium_tests(execution_id, test_case_ids, execution_data)
            elif framework == AutomationFramework.PYTEST:
                await self._execute_pytest_tests(execution_id, test_case_ids, execution_data)
            else:
                raise ExecutionError(f"不支持的自动化框架: {framework}")
            
            # 4. 更新状态为完成
            await self.redis.hset(f"automation_execution:{execution_id}", "status", "COMPLETED")
            await self.redis.hset(f"automation_execution:{execution_id}", "completed_at", datetime.utcnow().isoformat())
            
            # 5. 发送完成通知
            await self._send_automation_completed_notifications(execution_data)
            
        except Exception as e:
            # 更新状态为失败
            await self.redis.hset(f"automation_execution:{execution_id}", "status", "FAILED")
            await self.redis.hset(f"automation_execution:{execution_id}", "error", str(e))
            
            # 发送失败通知
            await self._send_automation_failed_notifications(execution_data, str(e))
    
    async def _execute_playwright_tests(self, execution_id: str, test_case_ids: List[int], execution_data: Dict[str, Any]):
        """执行Playwright测试"""
        # 1. 获取测试用例
        test_cases = await self._get_test_cases_by_ids(test_case_ids)
        
        # 2. 生成测试脚本
        test_scripts = []
        for test_case in test_cases:
            script = await self._generate_playwright_script(test_case, execution_data)
            test_scripts.append({
                "test_case_id": test_case.id,
                "script": script,
                "script_path": f"/tmp/test_{test_case.id}_{execution_id}.py"
            })
        
        # 3. 并发执行测试
        parallel_count = int(execution_data.get("parallel_count", 1))
        semaphore = asyncio.Semaphore(parallel_count)
        
        tasks = []
        for script_info in test_scripts:
            task = asyncio.create_task(
                self._run_playwright_script(execution_id, script_info, execution_data, semaphore)
            )
            tasks.append(task)
        
        # 4. 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_selenium_tests(self, execution_id: str, test_case_ids: List[int], execution_data: Dict[str, Any]):
        """执行Selenium测试"""
        # TODO: 实现Selenium测试执行
        pass
    
    async def _execute_pytest_tests(self, execution_id: str, test_case_ids: List[int], execution_data: Dict[str, Any]):
        """执行Pytest测试"""
        # TODO: 实现Pytest测试执行
        pass
    
    async def _run_playwright_script(
        self, 
        execution_id: str, 
        script_info: Dict[str, Any], 
        execution_data: Dict[str, Any],
        semaphore: asyncio.Semaphore
    ):
        """运行Playwright脚本"""
        async with semaphore:
            test_case_id = script_info["test_case_id"]
            script_path = script_info["script_path"]
            
            try:
                # 1. 写入脚本文件
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script_info["script"])
                
                # 2. 执行脚本
                timeout = int(execution_data.get("timeout", 300))
                process = await asyncio.create_subprocess_exec(
                    "python", script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                    return_code = process.returncode
                    
                    # 3. 解析执行结果
                    result = {
                        "test_case_id": test_case_id,
                        "status": "PASSED" if return_code == 0 else "FAILED",
                        "stdout": stdout.decode("utf-8") if stdout else "",
                        "stderr": stderr.decode("utf-8") if stderr else "",
                        "return_code": return_code,
                        "executed_at": datetime.utcnow().isoformat(),
                        "duration": 0  # TODO: 计算实际执行时间
                    }
                    
                    # 4. 保存结果
                    await self._save_execution_result(execution_id, result)
                    
                    # 5. 更新数据库执行记录
                    await self._update_execution_record(test_case_id, result)
                    
                except asyncio.TimeoutError:
                    # 超时处理
                    process.kill()
                    result = {
                        "test_case_id": test_case_id,
                        "status": "FAILED",
                        "error": "执行超时",
                        "executed_at": datetime.utcnow().isoformat()
                    }
                    await self._save_execution_result(execution_id, result)
                
            except Exception as e:
                # 异常处理
                result = {
                    "test_case_id": test_case_id,
                    "status": "FAILED",
                    "error": str(e),
                    "executed_at": datetime.utcnow().isoformat()
                }
                await self._save_execution_result(execution_id, result)
            
            finally:
                # 清理脚本文件
                if os.path.exists(script_path):
                    os.remove(script_path)
    
    # 辅助方法
    async def _validate_automation_cases(self, test_case_ids: List[int]) -> List[TestCase]:
        """验证自动化用例"""
        query = select(TestCase).where(
            and_(
                TestCase.id.in_(test_case_ids),
                TestCase.automation_level.in_(["SEMI_AUTO", "FULL_AUTO"]),
                TestCase.status == "ACTIVE"
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _get_test_cases_by_ids(self, test_case_ids: List[int]) -> List[TestCase]:
        """根据ID列表获取测试用例"""
        query = select(TestCase).where(TestCase.id.in_(test_case_ids))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _generate_execution_code(self, test_case_id: int) -> str:
        """生成执行编码"""
        today = datetime.now().strftime("%Y%m%d")
        
        # 查询今天的执行数量
        query = select(func.count(TestExecution.id)).where(
            and_(
                TestExecution.test_case_id == test_case_id,
                func.date(TestExecution.created_at) == datetime.now().date()
            )
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0
        
        return f"AUTO-{test_case_id}-{today}-{count + 1:03d}"
    
    async def _generate_playwright_script(self, test_case: TestCase, execution_data: Dict[str, Any]) -> str:
        """生成Playwright测试脚本"""
        browser = execution_data.get("browser", "chrome")
        test_environment = execution_data.get("test_environment", "")
        
        # 基础脚本模板
        script_template = f"""
import asyncio
from playwright.async_api import async_playwright
import json
import sys

async def run_test():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.{browser}.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 测试步骤
            test_steps = {json.dumps(test_case.test_steps or [], ensure_ascii=False)}
            
            for i, step in enumerate(test_steps):
                print(f"执行步骤 {{i+1}}: {{step.get('description', '')}}")
                
                # 根据步骤类型执行操作
                action = step.get('action', '')
                target = step.get('target', '')
                value = step.get('value', '')
                
                if action == 'navigate':
                    await page.goto(target)
                elif action == 'click':
                    await page.click(target)
                elif action == 'fill':
                    await page.fill(target, value)
                elif action == 'wait':
                    await page.wait_for_timeout(int(value) * 1000)
                elif action == 'assert_text':
                    element = await page.query_selector(target)
                    if element:
                        text = await element.text_content()
                        assert value in text, f"期望文本 '{{value}}' 不在实际文本 '{{text}}' 中"
                    else:
                        raise AssertionError(f"未找到元素: {{target}}")
                
                print(f"步骤 {{i+1}} 执行成功")
            
            print("测试用例执行成功")
            return True
            
        except Exception as e:
            print(f"测试用例执行失败: {{e}}")
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(run_test())
    sys.exit(0 if result else 1)
"""
        
        return script_template
    
    async def _save_execution_result(self, execution_id: str, result: Dict[str, Any]):
        """保存执行结果"""
        result_key = f"automation_result:{execution_id}:{result['test_case_id']}"
        await self.redis.hset(result_key, mapping=result)
        await self.redis.expire(result_key, 86400)  # 24小时过期
    
    async def _get_execution_results(self, execution_id: str) -> List[Dict[str, Any]]:
        """获取执行结果"""
        pattern = f"automation_result:{execution_id}:*"
        keys = await self.redis.keys(pattern)
        
        results = []
        for key in keys:
            result = await self.redis.hgetall(key)
            if result:
                results.append(result)
        
        return results
    
    async def _get_execution_logs(self, execution_id: str) -> List[Dict[str, Any]]:
        """获取执行日志"""
        log_key = f"automation_logs:{execution_id}"
        logs = await self.redis.lrange(log_key, 0, -1)
        
        return [json.loads(log) for log in logs if log]
    
    async def _update_execution_record(self, test_case_id: int, result: Dict[str, Any]):
        """更新数据库执行记录"""
        # 查找对应的执行记录
        query = select(TestExecution).where(
            and_(
                TestExecution.test_case_id == test_case_id,
                TestExecution.execution_type == ExecutionType.AUTOMATED,
                TestExecution.execution_status == ExecutionStatus.NOT_EXECUTED
            )
        ).order_by(TestExecution.created_at.desc())
        
        db_result = await self.db.execute(query)
        execution = db_result.scalar_one_or_none()
        
        if execution:
            execution.execution_status = ExecutionStatus.PASSED if result["status"] == "PASSED" else ExecutionStatus.FAILED
            execution.actual_result = result.get("stdout", "")
            execution.failure_reason = result.get("stderr") or result.get("error")
            execution.completed_at = datetime.fromisoformat(result["executed_at"])
            execution.duration = result.get("duration", 0)
            
            await self.db.commit()
    
    async def _stop_execution_process(self, execution_id: str):
        """停止执行进程"""
        # TODO: 实现进程停止逻辑
        pass
    
    async def _build_execution_response(self, execution: TestExecution):
        """构建执行响应"""
        from ..schemas.test_execution import TestExecutionResponse
        
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
            execution_steps=None,
            created_at=execution.created_at,
            updated_at=execution.updated_at
        )
    
    # 通知方法
    async def _send_automation_started_notifications(self, execution_data: Dict[str, Any]):
        """发送自动化开始通知"""
        # TODO: 实现通知逻辑
        pass
    
    async def _send_automation_completed_notifications(self, execution_data: Dict[str, Any]):
        """发送自动化完成通知"""
        # TODO: 实现通知逻辑
        pass
    
    async def _send_automation_failed_notifications(self, execution_data: Dict[str, Any], error: str):
        """发送自动化失败通知"""
        # TODO: 实现通知逻辑
        pass
    
    async def _send_automation_cancelled_notifications(self, execution_data: Dict[str, Any]):
        """发送自动化取消通知"""
        # TODO: 实现通知逻辑
        pass