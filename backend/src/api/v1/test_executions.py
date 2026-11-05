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
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from urllib import request as url_request
from urllib.error import HTTPError, URLError
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
from ...models.test_environment import TestEnvironment
from ...models.test_plan import TestPlan
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
    if normalized_framework and normalized_framework != "AUTO":
        query = query.filter(AutomationScript.framework == normalized_framework)
    return query.order_by(AutomationScript.updated_at.desc(), AutomationScript.id.desc()).first()


def _run_command(command: List[str], timeout: int, cwd: Optional[str] = None) -> Dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=max(1, timeout),
        cwd=cwd or FilePath.cwd(),
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


def _run_automation_script(script: AutomationScript, timeout: int) -> Dict[str, Any]:
    language = _normalize_enum_value(script.language).upper()
    framework = _normalize_enum_value(script.framework).upper()
    content = script.script_content or ""
    if language in {"JAVASCRIPT"} or framework in {"JEST", "CYPRESS"}:
        return _run_script_content(content, "js", timeout, framework=framework)
    if language not in {"PYTHON", ""}:
        raise RuntimeError(f"暂不支持执行 {language} 自动化脚本，请使用 Python 或 JavaScript 脚本")

    return _run_script_content(content, "python", timeout, framework=framework)


def _normalize_script_format(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "javascript": "js",
        "typescript": "js",
        "ts": "js",
        "jmx": "jmeter",
        "owaspzip": "owasp_zap",
        "awaspzip": "owasp_zap",
        "awasp_zap": "owasp_zap",
        "zap": "owasp_zap",
        "burp": "burpsuite",
        "burp_suite": "burpsuite",
    }
    return aliases.get(normalized, normalized)


def _get_imported_script(test_case: Optional[TestCase]) -> Optional[Dict[str, Any]]:
    if not test_case or not isinstance(test_case.test_data, dict):
        return None
    script_info = test_case.test_data.get("imported_script")
    if not isinstance(script_info, dict):
        return None
    content = script_info.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    script_info = dict(script_info)
    script_info["format"] = _normalize_script_format(script_info.get("format"))
    return script_info


def _infer_imported_script_format(script_info: Dict[str, Any]) -> str:
    explicit_format = _normalize_script_format(script_info.get("format"))
    if explicit_format:
        return explicit_format

    content = str(script_info.get("content") or "").strip()
    lower = content.lower()
    if lower.startswith("curl ") or "\ncurl " in lower:
        return "curl"
    if "<jmetertestplan" in lower or "<jmeter" in lower:
        return "jmeter"
    if '"log"' in lower and '"entries"' in lower and '"request"' in lower:
        return "har"
    if "playwright" in lower:
        return "playwright"
    if "selenium" in lower or "webdriver" in lower:
        return "selenium"
    if lower.startswith(("const ", "let ", "var ", "function ", "import ")) or "require(" in lower:
        return "js"
    if lower.startswith(("def ", "import ", "from ")) or "\ndef " in lower:
        return "python"
    return "python"


def _run_script_content(content: str, script_format: str, timeout: int, framework: Optional[str] = None) -> Dict[str, Any]:
    normalized = _normalize_script_format(script_format)
    if normalized in {"playwright", "selenium", "python", "py", "pytest"}:
        if normalized in {"playwright", "selenium"} and _looks_like_javascript(content):
            return _run_javascript_content(content, timeout)
        suffix = ".py"
        with tempfile.NamedTemporaryFile("w", suffix=suffix, encoding="utf-8", delete=False) as script_file:
            script_file.write(content or "")
            script_path = script_file.name
        try:
            if normalized == "pytest" or "pytest" in content or "def test_" in content:
                command = [sys.executable, "-m", "pytest", script_path, "-q"]
            else:
                command = [sys.executable, script_path]
            return _run_command(command, timeout)
        finally:
            FilePath(script_path).unlink(missing_ok=True)

    if normalized in {"js", "jest", "cypress"}:
        return _run_javascript_content(content, timeout)

    raise RuntimeError(f"暂不支持执行 {script_format} 脚本")


def _looks_like_javascript(content: str) -> bool:
    lower = (content or "").lower()
    return any(
        marker in lower
        for marker in ["require(", "module.exports", "const ", "let ", "var ", "@playwright/test", "import {"]
    )


def _run_javascript_content(content: str, timeout: int) -> Dict[str, Any]:
    suffix = ".js"
    with tempfile.NamedTemporaryFile("w", suffix=suffix, encoding="utf-8", delete=False) as script_file:
        script_file.write(content or "")
        script_path = script_file.name
    try:
        command = ["node", script_path]
        return _run_command(command, timeout)
    finally:
        FilePath(script_path).unlink(missing_ok=True)


def _legacy_resolve_jmeter_executable() -> str:
    configured = os.environ.get("JMETER_BIN") or os.environ.get("JMETER_EXECUTABLE")
    path_candidates = [configured]
    if os.name == "nt":
        path_candidates.extend([
            shutil.which("jmeter.bat"),
            shutil.which("jmeter.cmd"),
            r"C:\apache-jmeter\bin\jmeter.bat",
            r"E:\test\apache-jmeter-5.6.3\bin\jmeter.bat",
            shutil.which("jmeter"),
        ])
    else:
        path_candidates.append(shutil.which("jmeter"))

    candidates = []
    for candidate in path_candidates:
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        if candidate and FilePath(candidate).exists():
            return candidate
    raise RuntimeError("未找到 JMeter 可执行文件，请安装 JMeter 或配置 JMETER_BIN/JMETER_EXECUTABLE")


def _wrap_windows_batch_command(command: List[str]) -> List[str]:
    executable = command[0].lower()
    if os.name == "nt" and (executable.endswith(".bat") or executable.endswith(".cmd")):
        return ["cmd", "/c", *command]
    return command


def _shell_quote(value: Any) -> str:
    text = str(value or "")
    if os.name == "nt":
        return subprocess.list2cmdline([text])
    return shlex.quote(text)


def _read_text_sample(path: FilePath, limit: int = 4000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:limit]


def _render_command_template(template: str, values: Dict[str, Any]) -> str:
    rendered = template or ""
    for key, value in values.items():
        rendered = rendered.replace(f"{{{key}}}", _shell_quote(value))
    return rendered


def _parse_key_value_lines(value: Any) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for line in str(value or "").splitlines():
        normalized = line.strip()
        if not normalized or normalized.startswith("#") or "=" not in normalized:
            continue
        key, val = normalized.split("=", 1)
        key = key.strip()
        if key:
            parsed[key] = val.strip()
    return parsed


def _resolve_jmeter_executable(runtime_config: Optional[Dict[str, Any]] = None) -> str:
    runtime_config = runtime_config or {}
    configured = (
        runtime_config.get("executable_path")
        or os.environ.get("JMETER_BIN")
        or os.environ.get("JMETER_EXECUTABLE")
    )
    tool_home = runtime_config.get("tool_home")
    path_candidates = [configured]
    if tool_home:
        home = FilePath(str(tool_home)).expanduser()
        if os.name == "nt":
            path_candidates.extend([str(home / "bin" / "jmeter.bat"), str(home / "bin" / "jmeter.cmd")])
        else:
            path_candidates.append(str(home / "bin" / "jmeter"))
    if os.name == "nt":
        path_candidates.extend([
            shutil.which("jmeter.bat"),
            shutil.which("jmeter.cmd"),
            r"C:\apache-jmeter\bin\jmeter.bat",
            r"E:\test\apache-jmeter-5.6.3\bin\jmeter.bat",
            shutil.which("jmeter"),
        ])
    else:
        path_candidates.append(shutil.which("jmeter"))

    candidates = []
    for candidate in path_candidates:
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        if candidate and FilePath(candidate).exists():
            return candidate
    raise RuntimeError("未找到 JMeter 可执行文件，请安装 JMeter 或配置 JMETER_BIN/JMETER_EXECUTABLE")


def _build_jmeter_args(
    jmeter_executable: str,
    jmx_path: str,
    jtl_path: str,
    log_path: str,
    report_dir: Optional[str],
    runtime_config: Dict[str, Any],
) -> List[str]:
    args = [jmeter_executable, "-n", "-t", jmx_path, "-l", jtl_path, "-j", log_path]
    if report_dir:
        args.extend(["-e", "-o", report_dir])
    for key, value in _parse_key_value_lines(runtime_config.get("jmeter_properties")).items():
        args.append(f"-J{key}={value}")
    distributed_hosts = str(runtime_config.get("distributed_hosts") or "").strip()
    if distributed_hosts:
        args.extend(["-R", distributed_hosts])
    return args


def _ssh_target(runtime_config: Dict[str, Any]) -> str:
    host = str(runtime_config.get("runner_host") or "").strip()
    if not host:
        raise RuntimeError("SSH 执行节点未配置目标机器")
    user = str(runtime_config.get("runner_user") or "").strip()
    return f"{user}@{host}" if user else host


def _ssh_base_command(runtime_config: Dict[str, Any]) -> List[str]:
    command = ["ssh"]
    port = runtime_config.get("runner_port")
    if port:
        command.extend(["-p", str(port)])
    credential_ref = str(runtime_config.get("credential_ref") or "").strip()
    if credential_ref and FilePath(credential_ref).expanduser().exists():
        command.extend(["-i", str(FilePath(credential_ref).expanduser())])
    command.append(_ssh_target(runtime_config))
    return command


def _scp_base_command(runtime_config: Dict[str, Any]) -> List[str]:
    command = ["scp"]
    port = runtime_config.get("runner_port")
    if port:
        command.extend(["-P", str(port)])
    credential_ref = str(runtime_config.get("credential_ref") or "").strip()
    if credential_ref and FilePath(credential_ref).expanduser().exists():
        command.extend(["-i", str(FilePath(credential_ref).expanduser())])
    return command


def _run_jmeter_script_via_ssh(content: str, timeout: int, execution_code: str, runtime_config: Dict[str, Any]) -> Dict[str, Any]:
    remote_dir = str(runtime_config.get("runner_workdir") or f"/tmp/test-runs/{execution_code}").strip()
    remote_script = f"{remote_dir}/{execution_code}.jmx"
    remote_jtl = f"{remote_dir}/{execution_code}.jtl"
    remote_log = f"{remote_dir}/jmeter.log"
    remote_report = str(runtime_config.get("report_directory") or f"{remote_dir}/report").strip()
    if not remote_report.startswith("/"):
        remote_report = f"{remote_dir}/{remote_report}"

    with tempfile.TemporaryDirectory(prefix=f"jmeter-ssh-{execution_code}-") as temp_dir:
        local_dir = FilePath(temp_dir)
        local_script = local_dir / f"{execution_code}.jmx"
        local_jtl = local_dir / f"{execution_code}.jtl"
        local_report = local_dir / "report"
        local_script.write_text(content or "", encoding="utf-8")

        mkdir_result = _run_command([*_ssh_base_command(runtime_config), f"mkdir -p {shlex.quote(remote_dir)} {shlex.quote(remote_report)}"], timeout)
        if mkdir_result["status"] != "PASSED":
            return mkdir_result
        upload_result = _run_command([*_scp_base_command(runtime_config), str(local_script), f"{_ssh_target(runtime_config)}:{remote_script}"], timeout)
        if upload_result["status"] != "PASSED":
            return upload_result

        executable = str(runtime_config.get("executable_path") or "jmeter").strip()
        template = str(runtime_config.get("command_template") or "jmeter -n -t {script} -l {result_jtl} -j {log_file} -e -o {report_dir}").strip()
        command_text = _render_command_template(template, {
            "jmeter": executable,
            "script": remote_script,
            "result_file": remote_jtl,
            "result_jtl": remote_jtl,
            "report_dir": remote_report,
            "log_file": remote_log,
        })
        if runtime_config.get("executable_path") and command_text.strip().lower().startswith("jmeter "):
            command_text = f"{shlex.quote(executable)} {command_text.strip()[7:]}"

        remote_parts = [f"cd {shlex.quote(remote_dir)}"]
        pre_command = str(runtime_config.get("pre_command") or "").strip()
        post_command = str(runtime_config.get("post_command") or "").strip()
        if pre_command:
            remote_parts.append(pre_command)
        remote_parts.append(command_text)
        if post_command:
            remote_parts.append(post_command)

        started = time.perf_counter()
        completed = subprocess.run(
            [*_ssh_base_command(runtime_config), " && ".join(remote_parts)],
            capture_output=True,
            text=True,
            timeout=max(1, timeout),
            encoding="utf-8",
            errors="replace",
        )
        duration = int(time.perf_counter() - started)
        download_result = _run_command([*_scp_base_command(runtime_config), f"{_ssh_target(runtime_config)}:{remote_jtl}", str(local_jtl)], max(10, min(timeout, 300)))
        report_result = _run_command([*_scp_base_command(runtime_config), "-r", f"{_ssh_target(runtime_config)}:{remote_report}", str(local_report)], max(10, min(timeout, 300)))
        artifact_summary = "\n".join([
            f"远端 JMeter 结果文件: {remote_jtl}",
            f"远端 JMeter HTML 报告目录: {remote_report}",
            f"本地采集目录: {local_dir}",
            "结果文件已下载" if download_result["status"] == "PASSED" else f"结果文件下载失败: {download_result.get('stderr') or download_result.get('stdout')}",
            "HTML 报告已下载" if report_result["status"] == "PASSED" else f"HTML 报告下载失败: {report_result.get('stderr') or report_result.get('stdout')}",
        ])
        return {
            "status": "PASSED" if completed.returncode == 0 and download_result["status"] == "PASSED" else "FAILED",
            "stdout": "\n".join(part for part in [completed.stdout or "", artifact_summary, _read_text_sample(local_jtl)] if part),
            "stderr": completed.stderr or "",
            "return_code": completed.returncode,
            "duration": duration,
            "command": command_text,
        }


def _run_jmeter_script(content: str, timeout: int, execution_code: str, runtime_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    runtime_config = runtime_config or {}
    if str(runtime_config.get("runner_type") or "local").lower() == "ssh":
        return _run_jmeter_script_via_ssh(content, timeout, execution_code, runtime_config)

    jmeter_executable = _resolve_jmeter_executable(runtime_config)
    configured_result_dir = str(runtime_config.get("result_directory") or "").strip()
    with tempfile.TemporaryDirectory(prefix=f"jmeter-{execution_code}-") as temp_dir:
        base_path = FilePath(runtime_config.get("working_directory") or temp_dir).expanduser()
        base_path.mkdir(parents=True, exist_ok=True)
        result_path = FilePath(configured_result_dir).expanduser() if configured_result_dir else base_path
        if not result_path.is_absolute():
            result_path = base_path / result_path
        result_path.mkdir(parents=True, exist_ok=True)

        jmx_path = base_path / "test-plan.jmx"
        jtl_path = result_path / f"{execution_code}.jtl"
        log_path = result_path / "jmeter.log"
        report_path = FilePath(str(runtime_config.get("report_directory") or "report")).expanduser()
        if not report_path.is_absolute():
            report_path = result_path / report_path
        if report_path.exists():
            shutil.rmtree(report_path)
        jmx_path.write_text(content or "", encoding="utf-8")

        template = str(runtime_config.get("command_template") or "").strip()
        if template:
            command_text = _render_command_template(template, {
                "jmeter": jmeter_executable,
                "script": str(jmx_path),
                "result_file": str(jtl_path),
                "result_jtl": str(jtl_path),
                "report_dir": str(report_path),
                "log_file": str(log_path),
            })
            if runtime_config.get("executable_path") and command_text.strip().lower().startswith("jmeter "):
                command_text = f"{_shell_quote(jmeter_executable)} {command_text.strip()[7:]}"
            result = _run_configured_command(command_text, timeout, type("_ExecutionShim", (), {
                "id": "",
                "execution_code": execution_code,
                "test_case_id": "",
                "test_environment": runtime_config.get("environment") or "",
            })(), {**runtime_config, "working_directory": str(base_path)})
        else:
            command = _wrap_windows_batch_command(_build_jmeter_args(
                jmeter_executable,
                str(jmx_path),
                str(jtl_path),
                str(log_path),
                str(report_path),
                runtime_config,
            ))
            result = _run_command(command, timeout, cwd=str(base_path))

        artifact_summary = f"JMeter 结果文件: {jtl_path}\nJMeter HTML 报告目录: {report_path}"
        result["stdout"] = "\n".join(part for part in [result.get("stdout"), artifact_summary, _read_text_sample(jtl_path)] if part)
        result["stderr"] = "\n".join(part for part in [result.get("stderr"), _read_text_sample(log_path)] if part)
        return result


def _script_suffix_for_format(script_format: str) -> str:
    normalized = _normalize_script_format(script_format)
    if normalized in {"js", "javascript", "jest", "cypress"}:
        return ".js"
    if normalized in {"har"}:
        return ".har"
    if normalized in {"json"}:
        return ".json"
    if normalized in {"jmeter", "jmx"}:
        return ".jmx"
    return ".py"


def _default_command_template_for_format(script_format: str, requested_framework: str) -> str:
    normalized = _normalize_script_format(script_format)
    framework = str(requested_framework or "").lower()
    if normalized in {"playwright"} or framework == "playwright":
        return "npx playwright test {script}"
    if normalized in {"selenium"} or framework == "selenium":
        return "python {script}"
    if normalized in {"pytest", "python", "py"} or framework == "pytest":
        return "pytest {script} --junitxml={result_file}" if framework == "pytest" else "python {script}"
    if normalized in {"js", "javascript", "jest", "cypress"} or framework in {"javascript", "jest"}:
        return "node {script}"
    if normalized == "har" or framework == "har":
        return "har-replay {script} --output {result_file}"
    return "python {script}"


def _build_runtime_values(script_path: str, result_file: str, report_dir: str, log_file: str) -> Dict[str, str]:
    return {
        "script": script_path,
        "result_file": result_file,
        "result_jtl": result_file,
        "report_dir": report_dir,
        "log_file": log_file,
    }


def _append_runtime_artifact_summary(result: Dict[str, Any], result_file: FilePath, report_dir: FilePath, log_file: FilePath) -> Dict[str, Any]:
    artifact_summary = "\n".join([
        f"结果文件: {result_file}",
        f"报告目录: {report_dir}",
    ])
    result["stdout"] = "\n".join(part for part in [result.get("stdout"), artifact_summary, _read_text_sample(result_file)] if part)
    result["stderr"] = "\n".join(part for part in [result.get("stderr"), _read_text_sample(log_file)] if part)
    return result


def _run_runtime_script_via_ssh(
    content: str,
    script_format: str,
    timeout: int,
    requested_framework: str,
    execution_code: str,
    runtime_config: Dict[str, Any],
) -> Dict[str, Any]:
    suffix = _script_suffix_for_format(script_format)
    remote_dir = str(runtime_config.get("runner_workdir") or f"/tmp/test-runs/{execution_code}").strip()
    remote_script = f"{remote_dir}/{execution_code}{suffix}"
    remote_result = f"{remote_dir}/{execution_code}-result.xml"
    remote_report = str(runtime_config.get("report_directory") or f"{remote_dir}/report").strip()
    if not remote_report.startswith("/"):
        remote_report = f"{remote_dir}/{remote_report}"
    remote_log = f"{remote_dir}/execution.log"

    with tempfile.TemporaryDirectory(prefix=f"runtime-ssh-{execution_code}-") as temp_dir:
        local_dir = FilePath(temp_dir)
        local_script = local_dir / f"{execution_code}{suffix}"
        local_result = local_dir / f"{execution_code}-result.xml"
        local_report = local_dir / "report"
        local_script.write_text(content or "", encoding="utf-8")

        mkdir_result = _run_command([*_ssh_base_command(runtime_config), f"mkdir -p {shlex.quote(remote_dir)} {shlex.quote(remote_report)}"], timeout)
        if mkdir_result["status"] != "PASSED":
            return mkdir_result
        upload_result = _run_command([*_scp_base_command(runtime_config), str(local_script), f"{_ssh_target(runtime_config)}:{remote_script}"], timeout)
        if upload_result["status"] != "PASSED":
            return upload_result

        template = str(runtime_config.get("command_template") or _default_command_template_for_format(script_format, requested_framework)).strip()
        command_text = _render_command_template(template, _build_runtime_values(remote_script, remote_result, remote_report, remote_log))
        result = _run_configured_command(command_text, timeout, type("_ExecutionShim", (), {
            "id": "",
            "execution_code": execution_code,
            "test_case_id": "",
            "test_environment": runtime_config.get("environment") or "",
        })(), {**runtime_config, "runner_workdir": remote_dir})

        download_result = _run_command([*_scp_base_command(runtime_config), f"{_ssh_target(runtime_config)}:{remote_result}", str(local_result)], max(10, min(timeout, 300)))
        report_result = _run_command([*_scp_base_command(runtime_config), "-r", f"{_ssh_target(runtime_config)}:{remote_report}", str(local_report)], max(10, min(timeout, 300)))
        collection_summary = "\n".join([
            "结果文件已下载" if download_result["status"] == "PASSED" else f"结果文件下载失败: {download_result.get('stderr') or download_result.get('stdout')}",
            "报告目录已下载" if report_result["status"] == "PASSED" else f"报告目录下载失败: {report_result.get('stderr') or report_result.get('stdout')}",
        ])
        result["stdout"] = "\n".join(part for part in [result.get("stdout"), collection_summary, _read_text_sample(local_result)] if part)
        if download_result["status"] != "PASSED" and result["status"] == "PASSED":
            result["status"] = "FAILED"
        return result


def _run_runtime_script_content(
    content: str,
    script_format: str,
    timeout: int,
    requested_framework: str,
    execution_code: str,
    runtime_config: Dict[str, Any],
) -> Dict[str, Any]:
    runner_type = str(runtime_config.get("runner_type") or "local").lower()
    if runner_type == "ssh":
        return _run_runtime_script_via_ssh(content, script_format, timeout, requested_framework, execution_code, runtime_config)

    suffix = _script_suffix_for_format(script_format)
    with tempfile.TemporaryDirectory(prefix=f"runtime-{execution_code}-") as temp_dir:
        base_path = FilePath(runtime_config.get("working_directory") or temp_dir).expanduser()
        base_path.mkdir(parents=True, exist_ok=True)
        script_path = base_path / f"{execution_code}{suffix}"
        result_file = base_path / f"{execution_code}-result.xml"
        report_dir = base_path / str(runtime_config.get("report_directory") or "report")
        log_file = base_path / "execution.log"
        script_path.write_text(content or "", encoding="utf-8")
        if report_dir.exists():
            shutil.rmtree(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        template = str(runtime_config.get("command_template") or _default_command_template_for_format(script_format, requested_framework)).strip()
        if runner_type == "docker":
            values = _build_runtime_values(
                f"/workspace/{script_path.name}",
                f"/workspace/{result_file.name}",
                f"/workspace/{report_dir.name}",
                f"/workspace/{log_file.name}",
            )
        else:
            values = _build_runtime_values(str(script_path), str(result_file), str(report_dir), str(log_file))
        command_text = _render_command_template(template, values)
        result = _run_configured_command(command_text, timeout, type("_ExecutionShim", (), {
            "id": "",
            "execution_code": execution_code,
            "test_case_id": "",
            "test_environment": runtime_config.get("environment") or "",
        })(), {**runtime_config, "working_directory": str(base_path)})
        return _append_runtime_artifact_summary(result, result_file, report_dir, log_file)


def _run_har_script(content: str, timeout: int) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        har_data = json.loads(content or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"HAR 文件 JSON 解析失败: {exc}") from exc

    entries = har_data.get("log", {}).get("entries", [])
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("HAR 文件没有可执行的请求条目")

    max_entries = min(len(entries), 50)
    outputs = []
    failures = []
    for index, entry in enumerate(entries[:max_entries], start=1):
        request_data = entry.get("request") or {}
        url = request_data.get("url")
        method = (request_data.get("method") or "GET").upper()
        if not url:
            continue
        headers = {
            item.get("name"): item.get("value", "")
            for item in request_data.get("headers", [])
            if item.get("name") and item.get("name").lower() not in {"host", "content-length"}
        }
        post_data = request_data.get("postData") or {}
        body = post_data.get("text")
        data = body.encode("utf-8") if isinstance(body, str) and method not in {"GET", "HEAD"} else None
        req = url_request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with url_request.urlopen(req, timeout=max(1, min(timeout, 60))) as response:
                response_body = response.read(1024)
                outputs.append(f"{index}. {method} {url} -> {response.status}, {len(response_body)} bytes sampled")
        except HTTPError as exc:
            outputs.append(f"{index}. {method} {url} -> HTTP {exc.code}")
            if exc.code >= 400:
                failures.append(f"{method} {url} HTTP {exc.code}")
        except URLError as exc:
            failures.append(f"{method} {url} {exc.reason}")
        except Exception as exc:
            failures.append(f"{method} {url} {exc}")

    duration = int(time.perf_counter() - started)
    return {
        "status": "FAILED" if failures else "PASSED",
        "stdout": "\n".join(outputs),
        "stderr": "\n".join(failures),
        "return_code": 1 if failures else 0,
        "duration": duration,
        "command": f"HAR replay ({max_entries} entries)",
    }


def _run_imported_script(test_case: TestCase, timeout: int, requested_framework: str, execution_code: str, runtime_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    script_info = _get_imported_script(test_case)
    if not script_info:
        raise RuntimeError("该测试用例没有导入脚本内容，也没有维护自动化脚本")

    script_format = _infer_imported_script_format(script_info)
    content = script_info.get("content") or ""
    if script_format == "jmeter":
        return _run_jmeter_script(content, timeout, execution_code, runtime_config)
    runtime_config = runtime_config or {}
    runner_type = str(runtime_config.get("runner_type") or "local").lower()
    if runtime_config.get("command_template") or runner_type in {"ssh", "docker"}:
        if script_format == "curl":
            content = _curl_to_python(content)
            script_format = "python"
        return _run_runtime_script_content(content, script_format, timeout, requested_framework, execution_code, runtime_config)
    if script_format == "har":
        return _run_har_script(content, timeout)
    if script_format == "curl":
        return _run_script_content(_curl_to_python(content), "python", timeout)
    if script_format in {"python", "py", "pytest", "playwright", "selenium", "js", "jest", "cypress"}:
        return _run_script_content(content, script_format, timeout, framework=requested_framework)
    raise RuntimeError(f"暂不支持执行导入脚本格式: {script_format}")


def _curl_to_python(curl_content: str) -> str:
    escaped = json.dumps(curl_content or "")
    return f"""
import subprocess
import sys

command = {escaped}
completed = subprocess.run(command, shell=True, text=True, capture_output=True)
if completed.stdout:
    print(completed.stdout)
if completed.stderr:
    print(completed.stderr, file=sys.stderr)
sys.exit(completed.returncode)
"""


def _run_configured_command(
    command: str,
    timeout: int,
    execution: TestExecution,
    runtime_config: Dict[str, Any],
) -> Dict[str, Any]:
    command_text = (command or "").strip()
    if not command_text:
        raise RuntimeError("测试执行配置未提供执行命令")

    if str(runtime_config.get("runner_type") or "local").lower() == "docker":
        docker_image = str(runtime_config.get("docker_image") or "").strip()
        if not docker_image:
            raise RuntimeError("Docker 执行节点未配置镜像")
        cwd = runtime_config.get("working_directory")
        cwd_path = FilePath(str(cwd)).expanduser() if cwd else FilePath.cwd()
        if not cwd_path.exists() or not cwd_path.is_dir():
            raise RuntimeError(f"Docker 挂载目录不存在: {cwd_path}")

        docker_command = ["docker", "run", "--rm", "-v", f"{str(cwd_path.resolve())}:/workspace", "-w", "/workspace"]
        docker_network = str(runtime_config.get("docker_network") or "").strip()
        if docker_network:
            docker_command.extend(["--network", docker_network])
        configured_env = runtime_config.get("environment_variables")
        if isinstance(configured_env, dict):
            for key, value in configured_env.items():
                docker_command.extend(["-e", f"{key}={value}"])
        for line in str(runtime_config.get("docker_volumes") or "").splitlines():
            volume = line.strip()
            if volume:
                docker_command.extend(["-v", volume])
        for line in str(runtime_config.get("docker_args") or "").splitlines():
            extra_args = line.strip()
            if extra_args:
                docker_command.extend(shlex.split(extra_args, posix=os.name != "nt"))
        docker_command.extend([docker_image, "sh", "-lc", command_text])
        return _run_command(docker_command, timeout, cwd=str(cwd_path))

    if str(runtime_config.get("runner_type") or "local").lower() == "ssh":
        remote_workdir = str(runtime_config.get("runner_workdir") or runtime_config.get("working_directory") or "").strip()
        remote_parts = []
        if remote_workdir:
            remote_parts.append(f"cd {shlex.quote(remote_workdir)}")
        pre_command = str(runtime_config.get("pre_command") or "").strip()
        post_command = str(runtime_config.get("post_command") or "").strip()
        if pre_command:
            remote_parts.append(pre_command)
        remote_parts.append(command_text)
        if post_command:
            remote_parts.append(post_command)

        started = time.perf_counter()
        completed = subprocess.run(
            [*_ssh_base_command(runtime_config), " && ".join(remote_parts)],
            capture_output=True,
            text=True,
            timeout=max(1, timeout),
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
            "command": command_text,
        }

    cwd = runtime_config.get("working_directory")
    if cwd:
        cwd_path = FilePath(str(cwd)).expanduser()
        if not cwd_path.exists() or not cwd_path.is_dir():
            raise RuntimeError(f"执行工作目录不存在: {cwd}")
        cwd = str(cwd_path.resolve())
    else:
        cwd = str(FilePath.cwd())

    env = os.environ.copy()
    configured_env = runtime_config.get("environment_variables")
    if isinstance(configured_env, dict):
        env.update({str(key): str(value) for key, value in configured_env.items()})
    env.update({
        "TEST_EXECUTION_ID": str(execution.id or ""),
        "TEST_EXECUTION_CODE": execution.execution_code or "",
        "TEST_CASE_ID": str(execution.test_case_id or ""),
        "TEST_ENVIRONMENT": execution.test_environment or "",
    })

    started = time.perf_counter()
    completed = subprocess.run(
        command_text,
        capture_output=True,
        text=True,
        timeout=max(1, timeout),
        cwd=cwd,
        env=env,
        shell=True,
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
        "command": command_text,
    }


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
            runtime_config = config.get("execution_config") if isinstance(config.get("execution_config"), dict) else {}
            timeout = int(runtime_config.get("timeout") or config.get("timeout") or 300)
            framework = runtime_config.get("framework") or config.get("framework") or execution.os_info or "playwright"
            configured_command = runtime_config.get("command")

            try:
                if configured_command:
                    _append_execution_log(execution, "INFO", f"使用测试执行配置命令: {runtime_config.get('config_name') or framework}")
                    result = _run_configured_command(str(configured_command), timeout, execution, runtime_config)
                    completed_at = datetime.utcnow()
                    execution.execution_status = (
                        ModelExecutionStatus.PASSED
                        if result["status"] == "PASSED"
                        else ModelExecutionStatus.FAILED
                    )
                    execution.actual_result = (result.get("stdout") or "")[:60000] or "测试执行配置命令已执行完成"
                    failure_text = "\n".join(
                        part for part in [result.get("stderr"), f"退出码: {result.get('return_code')}"] if part
                    )
                    execution.failure_reason = failure_text[:60000] if result["status"] == "FAILED" else None
                    execution.duration = max(0, result.get("duration") or int((completed_at - started_at).total_seconds()))
                    _append_execution_log(
                        execution,
                        "INFO" if result["status"] == "PASSED" else "ERROR",
                        "测试执行配置命令执行通过" if result["status"] == "PASSED" else "测试执行配置命令执行失败",
                    )
                    output_summary = (result.get("stdout") or result.get("stderr") or "").strip()
                    if output_summary:
                        _append_execution_log(execution, "INFO", output_summary[:1000])
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
                    continue
                _append_execution_log(execution, "INFO", "开始执行自动化脚本")
                script = _find_automation_script(db, execution.test_case_id, framework)
                if script:
                    _append_execution_log(execution, "INFO", f"使用平台自动化脚本: {script.script_name}")
                    result = _run_automation_script(script, timeout)
                    script.last_execution_date = datetime.utcnow()
                    script.last_execution_status = (
                        ModelExecutionStatus.PASSED
                        if result["status"] == "PASSED"
                        else ModelExecutionStatus.FAILED
                    )
                    script.execution_count = (script.execution_count or 0) + 1
                    if result["status"] == "PASSED":
                        script.success_count = (script.success_count or 0) + 1
                else:
                    imported_script = _get_imported_script(execution.test_case)
                    if not imported_script:
                        raise RuntimeError("该测试用例未配置可执行的自动化脚本，也没有导入可执行脚本文件")
                    script_format = _infer_imported_script_format(imported_script)
                    _append_execution_log(execution, "INFO", f"使用导入脚本执行，格式: {script_format}")
                    result = _run_imported_script(execution.test_case, timeout, framework, execution.execution_code, runtime_config)
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
    # U4: unknown values used to be ASCII-stripped here ("QA环境" -> "QA",
    # "生产" -> "test"), silently changing what the user typed — and
    # sometimes to a wrong environment. Preserve unknown values verbatim
    # (truncated to the column width) instead; only known names map to
    # canonical codes.
    return (environment[:100] or "test")


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
        # 直接使用数据库聚合，避免依赖未初始化的 ExecutionMonitoringService
        base_query = db.query(TestExecution)
        if test_plan_id:
            base_query = base_query.filter(TestExecution.test_plan_id == test_plan_id)
        if start_date:
            base_query = base_query.filter(TestExecution.started_at >= start_date)
        if end_date:
            base_query = base_query.filter(TestExecution.started_at <= end_date)
        # project_id 通过关联的 test_plan / test_case 间接过滤
        if project_id:
            base_query = (
                base_query.outerjoin(TestPlan, TestExecution.test_plan_id == TestPlan.id)
                .filter(TestPlan.project_id == project_id)
            )

        total = base_query.count()
        passed = base_query.filter(TestExecution.execution_status == ModelExecutionStatus.PASSED).count()
        failed = base_query.filter(TestExecution.execution_status == ModelExecutionStatus.FAILED).count()
        blocked = base_query.filter(TestExecution.execution_status == ModelExecutionStatus.BLOCKED).count() if hasattr(ModelExecutionStatus, "BLOCKED") else 0
        skipped = base_query.filter(TestExecution.execution_status == ModelExecutionStatus.SKIPPED).count() if hasattr(ModelExecutionStatus, "SKIPPED") else 0
        automated = base_query.filter(TestExecution.execution_type == "AUTOMATED").count()
        manual = total - automated
        completed = passed + failed
        pass_rate = round(passed / completed * 100, 1) if completed else 0.0
        durations = [row[0] for row in db.query(TestExecution.duration).filter(
            TestExecution.duration.isnot(None)).all()]
        avg_duration = round((sum(durations) / len(durations)) / 60, 1) if durations else None

        response_data = ExecutionStatisticsResponse(
            total_executions=total,
            manual_executions=manual,
            automated_executions=automated,
            passed_executions=passed,
            failed_executions=failed,
            blocked_executions=blocked,
            skipped_executions=skipped,
            pass_rate=pass_rate,
            average_duration=avg_duration,
            execution_trend=[]
        )

        return BaseResponse(
            success=True,
            message="获取执行统计成功",
            data=response_data
        )

    except Exception as e:
        if _is_missing_table_error(e):
            response_data = ExecutionStatisticsResponse(
                total_executions=0, manual_executions=0, automated_executions=0,
                passed_executions=0, failed_executions=0, blocked_executions=0,
                skipped_executions=0, pass_rate=0.0, average_duration=None,
                execution_trend=[]
            )
            return BaseResponse(success=True, message="获取执行统计成功", data=response_data)
        logger.error(f"获取执行统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


# 测试环境管理接口
# 静态路径 /environments 必须注册在 /{execution_id} 之前，否则
# FastAPI 会把 "environments" 当作 execution_id 匹配，触发 int 转换失败 → 422。
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
        # 直接使用数据库查询，避免依赖未初始化的 TestEnvironmentService
        query = db.query(TestEnvironment)
        if environment_type:
            query = query.filter(TestEnvironment.environment_type == environment_type)
        if status:
            query = query.filter(TestEnvironment.status == status)
        if is_active is not None:
            query = query.filter(TestEnvironment.is_active == is_active)

        total = query.count()
        environments = query.offset((page - 1) * page_size).limit(page_size).all()

        # 构建响应数据
        response_data = []
        for env in environments:
            response_data.append(TestEnvironmentResponse(
                id=env.id,
                environment_name=env.environment_name,
                environment_type=env.environment_type.value if env.environment_type else None,
                description=env.description,
                status=env.status,
                configuration=env.configuration or {},
                is_active=env.is_active,
                current_user=None,
                reserved_until=None,
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
        if _is_missing_table_error(e):
            return PaginatedResponse(
                success=True,
                message="获取测试环境列表成功",
                data=[],
                total=0,
                page=page,
                page_size=page_size
            )
        logger.error(f"获取测试环境列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


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


@router.get("/{execution_id}/progress", response_model=BaseResponse[Dict[str, Any]])
async def get_execution_progress(
    execution_id: int = Path(..., description="执行记录ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取执行进度

    获取测试执行的实时进度信息（直接基于数据库执行记录计算，避免依赖未初始化的监控服务）。
    """
    try:
        execution = db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            raise HTTPException(status_code=404, detail="执行记录不存在")

        # 基于执行状态与时间推算进度
        status_val = execution.execution_status.value if hasattr(execution.execution_status, "value") else str(execution.execution_status)
        total_steps = 1
        completed_steps = 1 if status_val in ("PASSED", "FAILED", "COMPLETED", "BLOCKED", "SKIPPED") else 0
        passed_steps = 1 if status_val == "PASSED" else 0
        failed_steps = 1 if status_val == "FAILED" else 0
        progress_percentage = 100.0 if completed_steps else (50.0 if status_val == "IN_PROGRESS" else 0.0)
        estimated_completion = execution.completed_at.isoformat() if execution.completed_at else None

        return BaseResponse(
            success=True,
            message="获取执行进度成功",
            data={
                "execution_id": execution.id,
                "total_steps": total_steps,
                "completed_steps": completed_steps,
                "passed_steps": passed_steps,
                "failed_steps": failed_steps,
                "current_step": None,
                "progress_percentage": progress_percentage,
                "estimated_completion": estimated_completion
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行进度失败: {str(e)}")
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
        # 校验测试环境是否存在，避免对不存在的资源操作返回 500
        try:
            environment = db.query(TestEnvironment).filter(TestEnvironment.id == env_id).first()
        except Exception as table_error:
            # 测试环境表尚未初始化，视为环境不存在
            if _is_missing_table_error(table_error):
                raise HTTPException(status_code=404, detail="测试环境不存在")
            raise
        if not environment:
            raise HTTPException(status_code=404, detail="测试环境不存在")

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
        
    except (AttributeError, NotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e) or "测试环境不存在")
    except HTTPException:
        raise
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
        # 校验测试环境是否存在，避免对不存在的资源操作返回 500
        try:
            environment = db.query(TestEnvironment).filter(TestEnvironment.id == env_id).first()
        except Exception as table_error:
            # 测试环境表尚未初始化，视为环境不存在
            if _is_missing_table_error(table_error):
                raise HTTPException(status_code=404, detail="测试环境不存在")
            raise
        if not environment:
            raise HTTPException(status_code=404, detail="测试环境不存在")

        env_service = TestEnvironmentService(db)
        # 释放环境
        result = await env_service.release_environment(env_id, current_user.id)

        return BaseResponse(
            success=True,
            message="测试环境释放成功",
            data=result
        )

    except (AttributeError, NotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e) or "测试环境不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"释放测试环境失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
