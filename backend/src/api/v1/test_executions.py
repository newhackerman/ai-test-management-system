"""
测试执行管理API接口

本模块实现测试执行相关的RESTful API接口，包括：
- 手动和自动化执行的管理
- 执行监控和结果查询API
- 执行统计和分析接口
- 测试环境管理
"""

from datetime import datetime, date
import json
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path as FilePath
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, BackgroundTasks, UploadFile, File
from fastapi.security import HTTPBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from ...core.database import get_db, SessionLocal
from ...core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ...services.test_execution_service import TestExecutionService
from ...services.test_environment_service import TestEnvironmentService
from ...services.execution_monitoring_service import ExecutionMonitoringService
from ...services.auth_dependencies import get_current_user
from ...models.user import User
from ...models.test_case import AutomationScript, TestCase, TestExecution, ExecutionStatus as ModelExecutionStatus
from ...schemas.test_execution import (
    ExecutionType, ExecutionStatus, TestEnvironmentStatus,
    StartManualExecutionRequest, CompleteManualExecutionRequest,
    BatchExecutionRequest, AutomationExecutionRequest,
    TestExecutionResponse, ExecutionProgressResponse,
    BatchExecutionResponse, AutomationExecutionResponse,
    ExecutionStatisticsResponse, TestEnvironmentResponse
)
from ...schemas.base import BaseResponse, PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test-executions", tags=["测试执行管理"])
security = HTTPBearer()
MAX_VIDEO_UPLOAD_SIZE = 100 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024


def _delete_uploaded_execution_file(file_path_value: Optional[str], base_dir: str) -> None:
    if not file_path_value:
        return

    base_path = (FilePath.cwd() / base_dir).resolve()
    file_path = FilePath(file_path_value)
    if not file_path.is_absolute():
        file_path = FilePath.cwd() / file_path

    try:
        resolved_file_path = file_path.resolve()
        resolved_file_path.relative_to(base_path)
    except (OSError, ValueError):
        logger.warning("跳过删除非执行附件目录文件: %s", file_path_value)
        return

    resolved_file_path.unlink(missing_ok=True)


def _remove_execution_attachment(
    execution: TestExecution,
    attachment_type: str,
    attachment_index: int,
    base_dir: str,
) -> Dict[str, Any]:
    attachments = list(getattr(execution, attachment_type) or [])
    if attachment_index < 0 or attachment_index >= len(attachments):
        raise HTTPException(status_code=404, detail="附件不存在")

    metadata = attachments.pop(attachment_index)
    _delete_uploaded_execution_file(metadata.get("file_path"), base_dir)
    setattr(execution, attachment_type, attachments)
    execution.updated_at = datetime.utcnow()
    return metadata


def _is_missing_table_error(error: Exception) -> bool:
    text = str(error).lower()
    return "doesn't exist" in text or "no such table" in text


def _build_execution_response(execution):
    test_case = execution.test_case
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
        test_case_code=test_case.case_code if test_case else None,
        test_case_title=test_case.case_title if test_case else None,
        test_case_priority=_normalize_enum_value(test_case.priority) if test_case and test_case.priority else None,
        screenshots=execution.screenshots,
        logs=execution.logs,
        videos=execution.videos,
        created_at=execution.created_at,
        updated_at=execution.updated_at
    )


def _generate_execution_code(db: Session, test_case_id: int) -> str:
    today = datetime.now().strftime("%Y%m%d%H%M")
    prefix = f"EX-{test_case_id}-{today}"
    count = db.query(TestExecution).filter(TestExecution.execution_code.like(f"{prefix}-%")).count()
    return f"{prefix}-{count + 1:03d}"


def _generate_automation_execution_code(batch_id: str, test_case_id: int) -> str:
    return f"AUTO-{batch_id}-{test_case_id}"


def _json_list(value: Any) -> List[Dict[str, Any]]:
    return list(value) if isinstance(value, list) else []


def _append_execution_log(execution: TestExecution, level: str, message: str) -> None:
    logs = _json_list(execution.logs)
    logs.append({
        "time": datetime.utcnow().isoformat(),
        "level": level,
        "message": message,
    })
    execution.logs = logs


def _find_automation_script(db: Session, test_case_id: int, framework: str) -> Optional[AutomationScript]:
    normalized_framework = (framework or "").strip().upper()
    query = db.query(AutomationScript).filter(
        AutomationScript.test_case_id == test_case_id,
        AutomationScript.is_active == True,
    )
    if normalized_framework:
        query = query.filter(AutomationScript.framework == normalized_framework)
    return query.order_by(AutomationScript.updated_at.desc(), AutomationScript.id.desc()).first()


def _run_automation_script(script: AutomationScript, timeout: int) -> Dict[str, Any]:
    language = _normalize_enum_value(script.language).upper()
    framework = _normalize_enum_value(script.framework).upper()
    if language not in {"PYTHON", ""}:
        raise RuntimeError(f"暂不支持执行 {language} 自动化脚本，请使用 Python 脚本")

    suffix = ".py"
    with tempfile.NamedTemporaryFile("w", suffix=suffix, encoding="utf-8", delete=False) as script_file:
        script_file.write(script.script_content or "")
        script_path = script_file.name

    try:
        content = script.script_content or ""
        if framework in {"PLAYWRIGHT", "PYTEST"} and ("pytest" in content or "def test_" in content):
            command = [sys.executable, "-m", "pytest", script_path, "-q"]
        else:
            command = [sys.executable, script_path]

        started = time.perf_counter()
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(1, timeout),
            cwd=FilePath.cwd(),
            encoding="utf-8",
            errors="replace",
        )
        duration = int(time.perf_counter() - started)
        return {
            "status": "PASSED" if completed.returncode == 0 else "FAILED",
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or "",
            "return_code": completed.returncode,
            "duration": duration,
            "command": " ".join(command),
        }
    finally:
        try:
            FilePath(script_path).unlink(missing_ok=True)
        except OSError:
            logger.warning("清理自动化临时脚本失败: %s", script_path)


def _execute_automation_batch(batch_id: str) -> None:
    db = SessionLocal()
    try:
        executions = db.query(TestExecution).filter(
            TestExecution.execution_code.like(f"AUTO-{batch_id}-%")
        ).order_by(TestExecution.created_at.asc()).all()
        if not executions:
            return

        for execution in executions:
            if execution.execution_status != ModelExecutionStatus.IN_PROGRESS:
                continue

            started_at = execution.started_at or datetime.utcnow()
            completed_at = datetime.utcnow()
            try:
                config = json.loads(execution.execution_notes or "{}")
            except Exception:
                config = {}
            timeout = int(config.get("timeout") or 300)
            framework = config.get("framework") or execution.os_info or "playwright"

            try:
                _append_execution_log(execution, "INFO", "开始执行自动化脚本")
                script = _find_automation_script(db, execution.test_case_id, framework)
                if not script:
                    raise RuntimeError("该测试用例未配置可执行的自动化脚本，请先在测试用例中生成或维护自动化脚本")

                result = _run_automation_script(script, timeout)
                completed_at = datetime.utcnow()
                execution.execution_status = (
                    ModelExecutionStatus.PASSED
                    if result["status"] == "PASSED"
                    else ModelExecutionStatus.FAILED
                )
                execution.actual_result = (result.get("stdout") or "")[:60000] or "脚本执行完成"
                failure_text = "\n".join(
                    part for part in [result.get("stderr"), f"退出码: {result.get('return_code')}"] if part
                )
                execution.failure_reason = failure_text[:60000] if result["status"] == "FAILED" else None
                execution.duration = max(0, result.get("duration") or int((completed_at - started_at).total_seconds()))
                _append_execution_log(
                    execution,
                    "INFO" if result["status"] == "PASSED" else "ERROR",
                    f"自动化脚本执行{ '通过' if result['status'] == 'PASSED' else '失败' }",
                )
                output_summary = (result.get("stdout") or result.get("stderr") or "").strip()
                if output_summary:
                    _append_execution_log(execution, "INFO", output_summary[:1000])

                script.last_execution_date = completed_at
                script.last_execution_status = execution.execution_status
                script.execution_count = (script.execution_count or 0) + 1
                if execution.execution_status == ModelExecutionStatus.PASSED:
                    script.success_count = (script.success_count or 0) + 1
            except Exception as error:
                completed_at = datetime.utcnow()
                execution.execution_status = ModelExecutionStatus.FAILED
                execution.actual_result = None
                execution.failure_reason = str(error)[:60000]
                execution.duration = max(0, int((completed_at - started_at).total_seconds()))
                _append_execution_log(execution, "ERROR", str(error))

            execution.completed_at = completed_at
            execution.updated_at = completed_at
            _sync_test_case_execution_state(
                execution.test_case,
                execution.execution_status,
                occurred_at=completed_at,
                count_completed=True,
                duration=execution.duration,
            )
            db.commit()
            db.refresh(execution)
    except Exception as error:
        db.rollback()
        logger.exception("执行自动化批次失败 %s: %s", batch_id, error)
    finally:
        db.close()


def _sync_test_case_execution_state(
    test_case: Optional[TestCase],
    status: ModelExecutionStatus,
    *,
    occurred_at: Optional[datetime] = None,
    count_completed: bool = False,
    duration: Optional[int] = None,
) -> None:
    if not test_case:
        return

    now = occurred_at or datetime.utcnow()
    test_case.last_execution_status = status
    test_case.last_execution_date = now
    if count_completed:
        test_case.execution_count = (test_case.execution_count or 0) + 1
        if status == ModelExecutionStatus.PASSED:
            test_case.pass_count = (test_case.pass_count or 0) + 1
        elif status == ModelExecutionStatus.FAILED:
            test_case.fail_count = (test_case.fail_count or 0) + 1
        if duration is not None:
            test_case.actual_execution_time = max(1, round(duration / 60))


def _normalize_enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _normalize_environment(value: Optional[str]) -> str:
    if not value:
        return "test"
    environment = str(value).strip()
    environment_map = {
        "测试环境": "test",
        "test": "test",
        "testing": "test",
        "预生产环境": "staging",
        "预发布环境": "staging",
        "staging": "staging",
        "preprod": "staging",
        "开发环境": "dev",
        "development": "dev",
        "dev": "dev",
        "生产环境": "prod",
        "production": "prod",
        "prod": "prod",
        "本地环境": "local",
        "local": "local",
    }
    if environment in environment_map:
        return environment_map[environment]
    ascii_environment = "".join(char for char in environment if char.isascii() and (char.isalnum() or char in "-_"))
    return (ascii_environment[:100] or "test")


def _automation_status_from_executions(executions: List[TestExecution]) -> str:
    if not executions:
        return "UNKNOWN"
    statuses = {_normalize_enum_value(execution.execution_status) for execution in executions}
    if ModelExecutionStatus.IN_PROGRESS.value in statuses:
        return "RUNNING"
    if statuses == {ModelExecutionStatus.SKIPPED.value}:
        return "CANCELLED"
    if ModelExecutionStatus.FAILED.value in statuses:
        return "FAILED"
    if all(status in {ModelExecutionStatus.PASSED.value, ModelExecutionStatus.SKIPPED.value} for status in statuses):
        return "COMPLETED"
    return "PENDING"


def _build_automation_response(
    batch_id: str,
    executions: List[TestExecution],
    framework: str,
    test_environment: str,
    browser: Optional[str] = None,
) -> AutomationExecutionResponse:
    total_cases = len(executions)
    completed_statuses = {
        ModelExecutionStatus.PASSED.value,
        ModelExecutionStatus.FAILED.value,
        ModelExecutionStatus.BLOCKED.value,
        ModelExecutionStatus.SKIPPED.value,
    }
    completed_cases = 0
    passed_cases = 0
    failed_cases = 0
    results = []
    logs = []

    for execution in executions:
        status = _normalize_enum_value(execution.execution_status)
        if status in completed_statuses:
            completed_cases += 1
        if status == ModelExecutionStatus.PASSED.value:
            passed_cases += 1
        if status == ModelExecutionStatus.FAILED.value:
            failed_cases += 1

        case = execution.test_case
        results.append({
            "execution_id": execution.id,
            "execution_code": execution.execution_code,
            "test_case_id": execution.test_case_id,
            "case_code": case.case_code if case else "",
            "case_title": case.case_title if case else f"Case {execution.test_case_id}",
            "status": status,
            "duration": execution.duration,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "actual_result": execution.actual_result,
            "failure_reason": execution.failure_reason,
        })
        persisted_logs = _json_list(execution.logs)
        if persisted_logs:
            logs.extend(persisted_logs)
        else:
            logs.append({
                "time": execution.updated_at.isoformat() if execution.updated_at else datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": f"{execution.execution_code} {status}",
            })

    progress = round((completed_cases / total_cases * 100), 1) if total_cases else 0.0
    started_values = [execution.started_at for execution in executions if execution.started_at]
    return AutomationExecutionResponse(
        execution_id=batch_id,
        framework=framework,
        test_environment=test_environment,
        status=_automation_status_from_executions(executions),
        total_cases=total_cases,
        completed_cases=completed_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        progress_percentage=progress,
        started_at=min(started_values) if started_values else datetime.utcnow(),
        estimated_completion=None,
        execution_logs=logs,
        test_results=results,
    )


# 额外的请求模式
class UpdateExecutionStepRequest(BaseModel):
    """更新执行步骤请求"""
    execution_id: int = Field(..., description="执行记录ID")
    step_index: int = Field(..., description="步骤索引")
    step_status: ExecutionStatus = Field(..., description="步骤状态")
    step_result: Optional[str] = Field(None, description="步骤结果")
    step_notes: Optional[str] = Field(None, description="步骤备注")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件信息")


class PauseExecutionRequest(BaseModel):
    """暂停执行请求"""
    execution_id: int = Field(..., description="执行记录ID")
    pause_reason: Optional[str] = Field(None, description="暂停原因")


class ResumeExecutionRequest(BaseModel):
    """恢复执行请求"""
    execution_id: int = Field(..., description="执行记录ID")
    resume_notes: Optional[str] = Field(None, description="恢复备注")


class ExecutionQueryParams(BaseModel):
    """执行查询参数"""
    test_case_id: Optional[int] = Field(None, description="测试用例ID")
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    execution_type: Optional[ExecutionType] = Field(None, description="执行类型")
    execution_status: Optional[ExecutionStatus] = Field(None, description="执行状态")
    executor_id: Optional[int] = Field(None, description="执行人ID")
    test_environment: Optional[str] = Field(None, description="测试环境")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


# API接口实现
@router.post("/manual/start", response_model=BaseResponse[TestExecutionResponse])
async def start_manual_execution(
    request: StartManualExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    开始手动测试执行
    
    启动手动测试执行，创建执行记录并初始化执行状态。
    """
    try:
        test_environment = _normalize_environment(request.test_environment)
        test_case = db.query(TestCase).filter(TestCase.id == request.test_case_id).first()
        if not test_case:
            raise HTTPException(status_code=404, detail="测试用例不存在")

        active_execution = db.query(TestExecution).filter(
            TestExecution.test_case_id == request.test_case_id,
            TestExecution.execution_status == ModelExecutionStatus.IN_PROGRESS
        ).first()
        if active_execution:
            return BaseResponse(
                success=True,
                message="已恢复该测试用例进行中的执行",
                data=_build_execution_response(active_execution)
            )

        execution = TestExecution(
            execution_code=_generate_execution_code(db, test_case.id),
            test_case_id=test_case.id,
            test_plan_id=test_case.test_plan_id,
            execution_type=ExecutionType.MANUAL.value,
            execution_status=ModelExecutionStatus.IN_PROGRESS,
            test_environment=test_environment,
            browser_info=request.browser_info,
            os_info=(request.os_info or "")[:100] or None,
            execution_notes=request.execution_notes,
            executor_id=current_user.id,
            started_at=datetime.utcnow()
        )
        db.add(execution)
        _sync_test_case_execution_state(test_case, ModelExecutionStatus.IN_PROGRESS, occurred_at=execution.started_at)
        db.commit()
        db.refresh(execution)
        
        return BaseResponse(
            success=True,
            message="手动测试执行启动成功",
            data=_build_execution_response(execution)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"启动手动测试执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/manual/complete", response_model=BaseResponse[TestExecutionResponse])
async def complete_manual_execution(
    request: CompleteManualExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    完成手动测试执行
    
    完成手动测试执行，记录执行结果和相关信息。
    """
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == request.execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")

        completed_at = datetime.utcnow()
        was_unfinished = execution.completed_at is None
        execution.execution_status = ModelExecutionStatus(request.execution_status.value)
        execution.actual_result = request.actual_result
        execution.failure_reason = request.failure_reason
        execution.execution_notes = request.execution_notes
        if request.screenshots is not None:
            execution.screenshots = request.screenshots
        if request.logs is not None:
            execution.logs = request.logs
        if request.videos is not None:
            execution.videos = request.videos
        execution.completed_at = completed_at
        if execution.started_at:
            execution.duration = int((completed_at - execution.started_at).total_seconds())
        execution.updated_at = completed_at
        _sync_test_case_execution_state(
            execution.test_case,
            execution.execution_status,
            occurred_at=completed_at,
            count_completed=was_unfinished,
            duration=execution.duration,
        )
        db.commit()
        db.refresh(execution)
        
        return BaseResponse(
            success=True,
            message="手动测试执行完成成功",
            data=_build_execution_response(execution)
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"完成手动测试执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/manual/pause", response_model=BaseResponse[TestExecutionResponse])
async def pause_execution(
    request: PauseExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    暂停测试执行
    
    暂停正在进行的测试执行。
    """
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == request.execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")
        if execution.execution_status != ModelExecutionStatus.IN_PROGRESS:
            raise HTTPException(status_code=422, detail="只能暂停进行中的执行")

        execution.execution_status = ModelExecutionStatus.BLOCKED
        execution.execution_notes = request.pause_reason or execution.execution_notes
        execution.updated_at = datetime.utcnow()
        _sync_test_case_execution_state(execution.test_case, ModelExecutionStatus.BLOCKED, occurred_at=execution.updated_at)
        db.commit()
        db.refresh(execution)
        
        return BaseResponse(
            success=True,
            message="测试执行暂停成功",
            data=_build_execution_response(execution)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"暂停测试执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/manual/resume", response_model=BaseResponse[TestExecutionResponse])
async def resume_execution(
    request: ResumeExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    恢复测试执行
    
    恢复已暂停的测试执行。
    """
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == request.execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")
        if execution.execution_status != ModelExecutionStatus.BLOCKED:
            raise HTTPException(status_code=422, detail="只能恢复已暂停/阻塞的执行")

        execution.execution_status = ModelExecutionStatus.IN_PROGRESS
        execution.execution_notes = request.resume_notes or execution.execution_notes
        execution.updated_at = datetime.utcnow()
        _sync_test_case_execution_state(execution.test_case, ModelExecutionStatus.IN_PROGRESS, occurred_at=execution.updated_at)
        db.commit()
        db.refresh(execution)
        
        return BaseResponse(
            success=True,
            message="测试执行恢复成功",
            data=_build_execution_response(execution)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"恢复测试执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/automation/start", response_model=BaseResponse[AutomationExecutionResponse])
async def start_automation_execution_real(
    request: AutomationExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create real automated execution records for the selected test cases."""
    try:
        test_environment = _normalize_environment(request.test_environment)
        if not request.test_case_ids:
            raise HTTPException(status_code=422, detail="请选择要执行的自动化测试用例")

        test_cases = db.query(TestCase).filter(TestCase.id.in_(request.test_case_ids)).all()
        found_ids = {case.id for case in test_cases}
        missing_ids = [case_id for case_id in request.test_case_ids if case_id not in found_ids]
        if missing_ids:
            raise HTTPException(status_code=404, detail=f"测试用例不存在: {missing_ids}")

        invalid_cases = [
            case.case_code
            for case in test_cases
            if case.automation_level not in ("SEMI_AUTO", "FULL_AUTO")
        ]
        if invalid_cases:
            raise HTTPException(status_code=422, detail=f"以下用例未配置自动化: {', '.join(invalid_cases)}")

        batch_id = uuid.uuid4().hex[:12].upper()
        now = datetime.utcnow()
        config_payload = {
            "batch_id": batch_id,
            "framework": request.framework,
            "browser": request.browser,
            "parallel_count": request.parallel_count,
            "retry_count": request.retry_count,
            "timeout": request.timeout,
            "execution_config": request.execution_config or {},
        }

        executions = []
        for case in test_cases:
            execution = TestExecution(
                execution_code=_generate_automation_execution_code(batch_id, case.id),
                test_case_id=case.id,
                test_plan_id=case.test_plan_id,
                execution_type=ExecutionType.AUTOMATED.value,
                execution_status=ModelExecutionStatus.IN_PROGRESS,
                test_environment=test_environment,
                browser_info=request.browser,
                os_info=request.framework,
                execution_notes=json.dumps(config_payload, ensure_ascii=True),
                executor_id=current_user.id,
                started_at=now,
                updated_at=now,
            )
            _append_execution_log(execution, "INFO", "自动化执行已提交后台任务")
            db.add(execution)
            executions.append(execution)
            _sync_test_case_execution_state(case, ModelExecutionStatus.IN_PROGRESS, occurred_at=now)

        db.commit()
        for execution in executions:
            db.refresh(execution)

        background_tasks.add_task(_execute_automation_batch, batch_id)

        response_data = _build_automation_response(
            batch_id=batch_id,
            executions=executions,
            framework=request.framework,
            test_environment=test_environment,
            browser=request.browser,
        )
        return BaseResponse(success=True, message="自动化测试执行已创建", data=response_data)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"启动自动化测试执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/automation/{execution_id}/status", response_model=BaseResponse[AutomationExecutionResponse])
async def get_automation_execution_status_real(
    execution_id: str = Path(..., description="自动化执行批次ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Read automated execution status from persisted execution records."""
    try:
        executions = db.query(TestExecution).filter(
            TestExecution.execution_code.like(f"AUTO-{execution_id}-%")
        ).order_by(TestExecution.created_at.asc()).all()
        if not executions:
            raise HTTPException(status_code=404, detail="自动化执行批次不存在")

        config = {}
        if executions[0].execution_notes:
            try:
                config = json.loads(executions[0].execution_notes)
            except Exception:
                config = {}

        response_data = _build_automation_response(
            batch_id=execution_id,
            executions=executions,
            framework=config.get("framework") or executions[0].os_info or "",
            test_environment=executions[0].test_environment or "",
            browser=config.get("browser") or executions[0].browser_info,
        )
        return BaseResponse(success=True, message="获取自动化执行状态成功", data=response_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取自动化执行状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/automation/{execution_id}/cancel", response_model=BaseResponse[AutomationExecutionResponse])
async def cancel_automation_execution_real(
    execution_id: str = Path(..., description="自动化执行批次ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a running automated execution batch."""
    try:
        executions = db.query(TestExecution).filter(
            TestExecution.execution_code.like(f"AUTO-{execution_id}-%")
        ).order_by(TestExecution.created_at.asc()).all()
        if not executions:
            raise HTTPException(status_code=404, detail="自动化执行批次不存在")

        now = datetime.utcnow()
        for execution in executions:
            if execution.execution_status == ModelExecutionStatus.IN_PROGRESS:
                was_unfinished = execution.completed_at is None
                execution.execution_status = ModelExecutionStatus.SKIPPED
                execution.completed_at = now
                execution.updated_at = now
                if execution.started_at:
                    execution.duration = int((now - execution.started_at).total_seconds())
                _sync_test_case_execution_state(
                    execution.test_case,
                    ModelExecutionStatus.SKIPPED,
                    occurred_at=now,
                    count_completed=was_unfinished,
                    duration=execution.duration,
                )

        db.commit()
        for execution in executions:
            db.refresh(execution)

        response_data = _build_automation_response(
            batch_id=execution_id,
            executions=executions,
            framework=executions[0].os_info or "",
            test_environment=executions[0].test_environment or "",
            browser=executions[0].browser_info,
        )
        return BaseResponse(success=True, message="自动化执行已取消", data=response_data)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"取消自动化执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{execution_id}/screenshots", response_model=BaseResponse[Dict[str, Any]])
async def upload_execution_screenshot(
    execution_id: int = Path(..., description="执行记录ID"),
    screenshot: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a screenshot for a manual execution record."""
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")

        content_type = screenshot.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=422, detail="只能上传图片截图")

        upload_dir = FilePath("uploads/test_executions/screenshots")
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = FilePath(screenshot.filename or "screenshot.png").name
        file_name = f"{execution_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe_name}"
        file_path = upload_dir / file_name
        content = await screenshot.read()
        file_path.write_bytes(content)

        metadata = {
            "filename": safe_name,
            "file_path": str(file_path).replace("\\", "/"),
            "file_size": len(content),
            "content_type": content_type,
            "uploaded_at": datetime.utcnow().isoformat(),
            "uploaded_by": current_user.id,
        }
        screenshots = execution.screenshots or []
        screenshots.append(metadata)
        execution.screenshots = screenshots
        execution.updated_at = datetime.utcnow()
        db.commit()

        return BaseResponse(success=True, message="截图上传成功", data=metadata)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"上传执行截图失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{execution_id}/videos", response_model=BaseResponse[Dict[str, Any]])
async def upload_execution_video(
    execution_id: int = Path(..., description="执行记录ID"),
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a video attachment for a manual execution record."""
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")

        content_type = video.content_type or ""
        if not content_type.startswith("video/"):
            raise HTTPException(status_code=422, detail="只能上传视频文件")

        upload_dir = FilePath("uploads/test_executions/videos")
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = FilePath(video.filename or "execution-video.webm").name
        file_name = f"{execution_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{safe_name}"
        file_path = upload_dir / file_name
        file_size = 0

        with file_path.open("wb") as buffer:
            while True:
                chunk = await video.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_VIDEO_UPLOAD_SIZE:
                    buffer.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="视频文件不能超过100MB")
                buffer.write(chunk)

        if file_size == 0:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail="视频文件不能为空")

        metadata = {
            "filename": safe_name,
            "file_path": str(file_path).replace("\\", "/"),
            "file_size": file_size,
            "content_type": content_type,
            "uploaded_at": datetime.utcnow().isoformat(),
            "uploaded_by": current_user.id,
        }
        videos = execution.videos or []
        videos.append(metadata)
        execution.videos = videos
        execution.updated_at = datetime.utcnow()
        db.commit()

        return BaseResponse(success=True, message="录像上传成功", data=metadata)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"上传执行录像失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete("/{execution_id}/screenshots/{attachment_index}", response_model=BaseResponse[Dict[str, Any]])
async def delete_execution_screenshot(
    execution_id: int = Path(..., description="执行记录ID"),
    attachment_index: int = Path(..., ge=0, description="截图序号"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a screenshot attachment from a manual execution record."""
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")

        metadata = _remove_execution_attachment(
            execution,
            "screenshots",
            attachment_index,
            "uploads/test_executions/screenshots",
        )
        db.commit()
        return BaseResponse(success=True, message="截图已删除", data=metadata)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除执行截图失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete("/{execution_id}/videos/{attachment_index}", response_model=BaseResponse[Dict[str, Any]])
async def delete_execution_video(
    execution_id: int = Path(..., description="执行记录ID"),
    attachment_index: int = Path(..., ge=0, description="录像序号"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a video attachment from a manual execution record."""
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")

        metadata = _remove_execution_attachment(
            execution,
            "videos",
            attachment_index,
            "uploads/test_executions/videos",
        )
        db.commit()
        return BaseResponse(success=True, message="录像已删除", data=metadata)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除执行录像失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/batch", response_model=BaseResponse[BatchExecutionResponse])
async def start_batch_execution(
    request: BatchExecutionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    开始批量测试执行
    
    批量执行多个测试用例，支持手动和自动化混合执行。
    """
    try:
        service = TestExecutionService(db)
        
        # 开始批量执行
        batch_execution = await service.start_batch_execution(
            request.test_case_ids,
            request.execution_type,
            request.test_environment,
            current_user.id,
            {
                'parallel_count': request.parallel_count,
                'retry_count': request.retry_count,
                'execution_config': request.execution_config
            }
        )
        
        # 构建响应
        response_data = BatchExecutionResponse(
            batch_id=batch_execution.batch_id,
            total_cases=batch_execution.total_cases,
            completed_cases=0,
            passed_cases=0,
            failed_cases=0,
            blocked_cases=0,
            skipped_cases=0,
            execution_status="RUNNING",
            started_at=batch_execution.started_at,
            estimated_completion=batch_execution.estimated_completion,
            executions=[]
        )
        
        return BaseResponse(
            success=True,
            message="批量测试执行启动成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"启动批量测试执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/statistics", response_model=BaseResponse[Dict[str, Any]])
async def get_execution_statistics_alias(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取测试执行统计信息（兼容前端旧路径，使用真实数据库统计）。"""
    try:
        total = db.query(TestExecution).count()
        in_progress = db.query(TestExecution).filter(TestExecution.execution_status == ModelExecutionStatus.IN_PROGRESS).count()
        today = date.today()
        completed_today = db.query(TestExecution).filter(
            TestExecution.completed_at.isnot(None),
            TestExecution.completed_at >= datetime.combine(today, datetime.min.time()),
            TestExecution.completed_at <= datetime.combine(today, datetime.max.time())
        ).count()
        passed = db.query(TestExecution).filter(TestExecution.execution_status == ModelExecutionStatus.PASSED).count()
        failed = db.query(TestExecution).filter(TestExecution.execution_status == ModelExecutionStatus.FAILED).count()
        completed = passed + failed
        pass_rate = round(passed / completed * 100, 1) if completed else 0
        durations = [row[0] for row in db.query(TestExecution.duration).filter(TestExecution.duration.isnot(None)).all()]
        avg_duration = round((sum(durations) / len(durations)) / 60, 1) if durations else 0
        active_executors = db.query(TestExecution.executor_id).filter(
            TestExecution.execution_status == ModelExecutionStatus.IN_PROGRESS
        ).distinct().count()
    except Exception as e:
        if not _is_missing_table_error(e):
            raise
        total = in_progress = completed_today = pass_rate = avg_duration = active_executors = 0
    return BaseResponse(
        success=True,
        message="获取执行统计成功",
        data={
            "total_executions": total,
            "in_progress": in_progress,
            "completed_today": completed_today,
            "pass_rate": pass_rate,
            "avg_duration": avg_duration,
            "active_executors": active_executors
        }
    )


@router.get("/{execution_id}", response_model=BaseResponse[TestExecutionResponse])
async def get_test_execution(
    execution_id: int = Path(..., description="执行记录ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试执行详情
    
    根据执行记录ID获取详细的执行信息。
    """
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")
        
        return BaseResponse(
            success=True,
            message="获取测试执行详情成功",
            data=_build_execution_response(execution)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取测试执行详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{execution_id}/logs", response_model=BaseResponse[List[Dict[str, Any]]])
async def get_execution_logs(
    execution_id: int = Path(..., description="执行记录ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="测试执行记录不存在")
        return BaseResponse(success=True, message="获取执行日志成功", data=execution.logs or [])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/", response_model=PaginatedResponse[TestExecutionResponse])
async def list_test_executions(
    search: Optional[str] = Query(None, description="执行编号或用例关键词"),
    test_case_id: Optional[int] = Query(None, description="测试用例ID"),
    test_plan_id: Optional[int] = Query(None, description="测试计划ID"),
    execution_type: Optional[ExecutionType] = Query(None, description="执行类型"),
    execution_status: Optional[ExecutionStatus] = Query(None, description="执行状态"),
    executor_id: Optional[int] = Query(None, description="执行人ID"),
    test_environment: Optional[str] = Query(None, description="测试环境"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试执行列表
    
    支持多条件过滤和分页查询。
    """
    try:
        query = db.query(TestExecution)
        if test_case_id:
            query = query.filter(TestExecution.test_case_id == test_case_id)
        if test_plan_id:
            query = query.filter(TestExecution.test_plan_id == test_plan_id)
        if execution_type:
            query = query.filter(TestExecution.execution_type == execution_type.value)
        if execution_status:
            query = query.filter(TestExecution.execution_status == ModelExecutionStatus(execution_status.value))
        if executor_id:
            query = query.filter(TestExecution.executor_id == executor_id)
        if test_environment:
            query = query.filter(TestExecution.test_environment == test_environment)
        if search:
            like_pattern = f"%{search.strip()}%"
            query = query.join(TestCase, TestExecution.test_case_id == TestCase.id).filter(
                or_(
                    TestExecution.execution_code.like(like_pattern),
                    TestCase.case_code.like(like_pattern),
                    TestCase.case_title.like(like_pattern),
                )
            )
        if start_date:
            query = query.filter(TestExecution.started_at >= start_date)
        if end_date:
            query = query.filter(TestExecution.started_at <= end_date)

        total = query.count()
        executions = query.order_by(TestExecution.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()
        
        # 构建响应数据
        response_data = []
        for execution in executions:
            response_data.append(_build_execution_response(execution))
        
        return PaginatedResponse(
            success=True,
            message="获取测试执行列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        if _is_missing_table_error(e):
            return PaginatedResponse(
                success=True,
                message="测试执行表未初始化，当前无数据",
                data=[],
                total=0,
                page=page,
                page_size=page_size
            )
        logger.error(f"获取测试执行列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{execution_id}/progress", response_model=BaseResponse[ExecutionProgressResponse])
async def get_execution_progress(
    execution_id: int = Path(..., description="执行记录ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取执行进度
    
    获取测试执行的实时进度信息。
    """
    try:
        monitoring_service = ExecutionMonitoringService(db)
        
        # 获取执行进度
        progress = await monitoring_service.get_execution_progress(execution_id)
        
        # 构建响应
        response_data = ExecutionProgressResponse(
            execution_id=progress.execution_id,
            total_steps=progress.total_steps,
            completed_steps=progress.completed_steps,
            passed_steps=progress.passed_steps,
            failed_steps=progress.failed_steps,
            current_step=progress.current_step,
            progress_percentage=progress.progress_percentage,
            estimated_completion=progress.estimated_completion
        )
        
        return BaseResponse(
            success=True,
            message="获取执行进度成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取执行进度失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/statistics/summary", response_model=BaseResponse[ExecutionStatisticsResponse])
async def get_execution_statistics(
    project_id: Optional[int] = Query(None, description="项目ID"),
    test_plan_id: Optional[int] = Query(None, description="测试计划ID"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取执行统计信息
    
    获取测试执行的统计数据和趋势分析。
    """
    try:
        monitoring_service = ExecutionMonitoringService(db)
        
        # 构建统计条件
        filters = {}
        if project_id:
            filters['project_id'] = project_id
        if test_plan_id:
            filters['test_plan_id'] = test_plan_id
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        
        # 获取执行统计
        statistics = await monitoring_service.get_execution_statistics(filters)
        
        # 构建响应
        response_data = ExecutionStatisticsResponse(
            total_executions=statistics.total_executions,
            manual_executions=statistics.manual_executions,
            automated_executions=statistics.automated_executions,
            passed_executions=statistics.passed_executions,
            failed_executions=statistics.failed_executions,
            blocked_executions=statistics.blocked_executions,
            skipped_executions=statistics.skipped_executions,
            pass_rate=statistics.pass_rate,
            average_duration=statistics.average_duration,
            execution_trend=statistics.execution_trend
        )
        
        return BaseResponse(
            success=True,
            message="获取执行统计成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取执行统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 测试环境管理接口
@router.get("/environments", response_model=PaginatedResponse[TestEnvironmentResponse])
async def list_test_environments(
    environment_type: Optional[str] = Query(None, description="环境类型"),
    status: Optional[TestEnvironmentStatus] = Query(None, description="环境状态"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试环境列表
    
    获取可用的测试环境列表。
    """
    try:
        env_service = TestEnvironmentService(db)
        
        # 构建查询条件
        filters = {}
        if environment_type:
            filters['environment_type'] = environment_type
        if status:
            filters['status'] = status.value
        if is_active is not None:
            filters['is_active'] = is_active
        
        # 查询环境列表
        environments, total = await env_service.get_environments_by_filters(filters, page, page_size)
        
        # 构建响应数据
        response_data = []
        for env in environments:
            response_data.append(TestEnvironmentResponse(
                id=env.id,
                environment_name=env.environment_name,
                environment_type=env.environment_type,
                description=env.description,
                status=env.status,
                configuration=env.configuration,
                is_active=env.is_active,
                current_user=env.current_user,
                reserved_until=env.reserved_until,
                created_at=env.created_at,
                updated_at=env.updated_at
            ))
        
        return PaginatedResponse(
            success=True,
            message="获取测试环境列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取测试环境列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/environments/{env_id}/reserve", response_model=BaseResponse[Dict[str, Any]])
async def reserve_test_environment(
    env_id: int = Path(..., description="环境ID"),
    reserved_until: datetime = Body(..., description="预约到期时间"),
    purpose: str = Body(..., description="使用目的"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    预约测试环境
    
    预约指定的测试环境。
    """
    try:
        env_service = TestEnvironmentService(db)
        
        # 预约环境
        reservation = await env_service.reserve_environment(
            env_id,
            current_user.id,
            reserved_until,
            purpose
        )
        
        return BaseResponse(
            success=True,
            message="测试环境预约成功",
            data={
                'reservation_id': reservation.id,
                'environment_id': env_id,
                'reserved_until': reserved_until.isoformat(),
                'purpose': purpose
            }
        )
        
    except Exception as e:
        logger.error(f"预约测试环境失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/environments/{env_id}/release", response_model=BaseResponse[bool])
async def release_test_environment(
    env_id: int = Path(..., description="环境ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    释放测试环境
    
    释放当前用户预约的测试环境。
    """
    try:
        env_service = TestEnvironmentService(db)
        
        # 释放环境
        result = await env_service.release_environment(env_id, current_user.id)
        
        return BaseResponse(
            success=True,
            message="测试环境释放成功",
            data=result
        )
        
    except Exception as e:
        logger.error(f"释放测试环境失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
