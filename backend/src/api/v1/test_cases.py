"""
测试用例管理API接口

本模块实现测试用例相关的RESTful API接口，包括：
- 测试用例的CRUD操作和批量处理
- AI用例生成和脚本生成API
- 用例搜索和过滤功能
- API参数验证和错误处理
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, UploadFile, File, Form, Response
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import csv
import io
import json
import logging

from ...core.database import get_db
from ...core.exceptions import ValidationError, PermissionError, NotFoundError, BusinessLogicError
from ...services.test_case_service import TestCaseService
from ...services.ai_test_case_generator import AITestCaseGenerator, GenerationConfig, GenerationTemplate
from ...services.automation_script_generator import (
    AutomationConfig,
    AutomationFramework,
    AutomationScriptGenerator,
    BrowserType,
    ProgrammingLanguage,
)
from ...services.auth_dependencies import get_current_user
from ...models.user import User
from ...models.test_case import TestCase, TestCaseType, TestCasePriority, TestCaseStatus, AutomationScript
from ...models.requirement import (
    Complexity as RequirementComplexity,
    Priority as RequirementPriority,
    Requirement,
    RequirementType,
)
from ...schemas.base import BaseResponse, PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test-cases", tags=["测试用例管理"])
security = HTTPBearer()


def _is_missing_table_error(error: Exception) -> bool:
    text = str(error).lower()
    return "doesn't exist" in text or "no such table" in text


def _enum_value(value):
    return getattr(value, "value", value)


def _normalize_automation_value(value: Optional[str]) -> str:
    return str(value or "").strip().replace("-", "_").upper()


IMPORT_CATEGORY_CONFIG = {
    "functional": {
        "case_type": TestCaseType.FUNCTIONAL,
        "automation_level": "MANUAL",
        "tags": ["functional"],
    },
    "interface": {
        "case_type": TestCaseType.INTEGRATION,
        "automation_level": "SEMI_AUTO",
        "tags": ["interface"],
        "script_formats": {"curl", "python", "javascript", "js", "jmeter", "har"},
    },
    "automation": {
        "case_type": TestCaseType.FUNCTIONAL,
        "automation_level": "FULL_AUTO",
        "tags": ["automation"],
        "script_formats": {"playwright", "selenium", "python"},
    },
    "performance": {
        "case_type": TestCaseType.PERFORMANCE,
        "automation_level": "SEMI_AUTO",
        "tags": ["performance"],
        "script_formats": {"python", "jmeter"},
    },
    "security": {
        "case_type": TestCaseType.SECURITY,
        "automation_level": "SEMI_AUTO",
        "tags": ["security"],
        "script_formats": {"python", "owasp_zap", "burpsuite", "sqlmap"},
    },
}


COLUMN_ALIASES = {
    "case_title": {"case_title", "title", "name", "用例标题", "标题", "名称"},
    "case_description": {"case_description", "description", "desc", "用例描述", "描述"},
    "module": {"module", "模块", "功能模块"},
    "preconditions": {"preconditions", "precondition", "前置条件", "前提条件"},
    "test_steps": {"test_steps", "steps", "step", "测试步骤", "操作步骤", "步骤"},
    "expected_result": {"expected_result", "expected", "expect", "预期结果", "期望结果"},
    "test_data": {"test_data", "data", "测试数据", "数据"},
    "priority": {"priority", "优先级"},
    "requirement_id": {"requirement_id", "需求ID", "需求id", "关联需求"},
    "script_name": {"script_name", "脚本名称", "脚本名"},
    "script_content": {
        "script",
        "script_content",
        "script body",
        "脚本",
        "脚本内容",
        "curl",
        "python",
        "js",
        "javascript",
        "jmeter",
        "playwright",
        "selenium",
        "zap",
        "owasp_zap",
        "burpsuite",
        "sqlmap",
    },
    "script_format": {"script_format", "script_type", "脚本类型", "脚本格式"},
}


COLUMN_ALIASES.update({
    "case_title": COLUMN_ALIASES["case_title"] | {"\u7528\u4f8b\u6807\u9898", "\u6807\u9898", "\u540d\u79f0"},
    "case_description": COLUMN_ALIASES["case_description"] | {"\u7528\u4f8b\u63cf\u8ff0", "\u63cf\u8ff0"},
    "module": COLUMN_ALIASES["module"] | {"\u6a21\u5757", "\u529f\u80fd\u6a21\u5757"},
    "preconditions": COLUMN_ALIASES["preconditions"] | {"\u524d\u7f6e\u6761\u4ef6", "\u524d\u63d0\u6761\u4ef6"},
    "test_steps": COLUMN_ALIASES["test_steps"] | {"\u6d4b\u8bd5\u6b65\u9aa4", "\u64cd\u4f5c\u6b65\u9aa4", "\u6b65\u9aa4"},
    "expected_result": COLUMN_ALIASES["expected_result"] | {"\u9884\u671f\u7ed3\u679c", "\u671f\u671b\u7ed3\u679c"},
    "test_data": COLUMN_ALIASES["test_data"] | {"\u6d4b\u8bd5\u6570\u636e", "\u6570\u636e"},
    "priority": COLUMN_ALIASES["priority"] | {"\u4f18\u5148\u7ea7"},
    "requirement_id": COLUMN_ALIASES["requirement_id"] | {"\u9700\u6c42ID", "\u9700\u6c42id", "\u5173\u8054\u9700\u6c42"},
    "script_name": COLUMN_ALIASES["script_name"] | {"\u811a\u672c\u540d\u79f0", "\u811a\u672c\u540d"},
    "script_content": COLUMN_ALIASES["script_content"] | {"\u811a\u672c", "\u811a\u672c\u5185\u5bb9"},
    "script_format": COLUMN_ALIASES["script_format"] | {"\u811a\u672c\u7c7b\u578b", "\u811a\u672c\u683c\u5f0f"},
})


def _normalize_import_category(value: Optional[str]) -> str:
    normalized = str(value or "functional").strip().lower().replace("-", "_")
    aliases = {
        "功能": "functional",
        "功能用例": "functional",
        "接口": "interface",
        "接口测试": "interface",
        "接口用例": "interface",
        "自动化": "automation",
        "自动化用例": "automation",
        "性能": "performance",
        "性能用例": "performance",
        "安全": "security",
        "安全用例": "security",
    }
    aliases.update({
        "\u529f\u80fd": "functional",
        "\u529f\u80fd\u7528\u4f8b": "functional",
        "\u63a5\u53e3": "interface",
        "\u63a5\u53e3\u6d4b\u8bd5": "interface",
        "\u63a5\u53e3\u7528\u4f8b": "interface",
        "\u81ea\u52a8\u5316": "automation",
        "\u81ea\u52a8\u5316\u7528\u4f8b": "automation",
        "\u6027\u80fd": "performance",
        "\u6027\u80fd\u7528\u4f8b": "performance",
        "\u5b89\u5168": "security",
        "\u5b89\u5168\u7528\u4f8b": "security",
    })
    normalized = aliases.get(normalized, normalized)
    if normalized not in IMPORT_CATEGORY_CONFIG:
        raise BusinessLogicError("Unsupported import category")
    return normalized


def _normalize_script_format(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "javascript": "js",
        "jmx": "jmeter",
        "owaspzip": "owasp_zap",
        "awaspzip": "owasp_zap",
        "awasp_zap": "owasp_zap",
        "owaspzap": "owasp_zap",
        "owasp_zap": "owasp_zap",
        "zap": "owasp_zap",
        "burp": "burpsuite",
        "burp_suite": "burpsuite",
    }
    return aliases.get(normalized, normalized)


def _clean_import_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime,)):
        return value.isoformat()
    return str(value).strip()


def _decode_import_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8-sig", errors="replace")


def _infer_script_format(script_content: str = "", filename: str = "") -> Optional[str]:
    lower_name = (filename or "").lower()
    lower_content = (script_content or "").strip().lower()
    if lower_content.startswith("curl ") or "\ncurl " in lower_content:
        return "curl"
    if "<jmetertestplan" in lower_content or "<jmeter" in lower_content:
        return "jmeter"
    if "playwright" in lower_content or "@playwright/test" in lower_content:
        return "playwright"
    if "selenium" in lower_content or "webdriver" in lower_content:
        return "selenium"
    if "sqlmap" in lower_content:
        return "sqlmap"
    if "burpsuite" in lower_content or "burp suite" in lower_content:
        return "burpsuite"
    if "owasp zap" in lower_content or "owasp_zap" in lower_content or "zapv2" in lower_content:
        return "owasp_zap"

    extension_map = {
        ".jmx": "jmeter",
        ".py": "python",
        ".js": "js",
        ".ts": "js",
        ".har": "har",
    }
    for suffix, script_format in extension_map.items():
        if lower_name.endswith(suffix):
            return script_format

    if not lower_content:
        return None
    if lower_content.startswith(("def ", "import ", "from ")) or "\ndef " in lower_content:
        return "python"
    if lower_content.startswith(("const ", "let ", "var ", "function ")) or "module.exports" in lower_content:
        return "js"
    return None


def _normalize_import_header(value: Any) -> str:
    return _clean_import_cell(value).strip().lower().replace(" ", "_")


def _get_import_value(row: Dict[str, Any], field: str) -> str:
    aliases = {_normalize_import_header(item) for item in COLUMN_ALIASES.get(field, {field})}
    for key, value in row.items():
        if _normalize_import_header(key) in aliases:
            return _clean_import_cell(value)
    return ""


def _parse_import_priority(value: str) -> str:
    normalized = str(value or "").strip().upper()
    mapping = {
        "紧急": "CRITICAL",
        "急": "CRITICAL",
        "最高": "CRITICAL",
        "CRITICAL": "CRITICAL",
        "高": "HIGH",
        "HIGH": "HIGH",
        "中": "MEDIUM",
        "MEDIUM": "MEDIUM",
        "低": "LOW",
        "LOW": "LOW",
    }
    mapping.update({
        "\u7d27\u6025": "CRITICAL",
        "\u6025": "CRITICAL",
        "\u6700\u9ad8": "CRITICAL",
        "\u9ad8": "HIGH",
        "\u4e2d": "MEDIUM",
        "\u4f4e": "LOW",
    })
    return mapping.get(normalized, "MEDIUM")


def _parse_import_steps(raw_steps: str, expected_result: str) -> List[Dict[str, Any]]:
    text = _clean_import_cell(raw_steps)
    if not text:
        return [{
            "step_number": 1,
            "action": "Review imported script or requirement description",
            "expected_result": expected_result or "Result matches the expected behavior",
        }]

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            steps = []
            for index, item in enumerate(parsed, start=1):
                if isinstance(item, dict):
                    steps.append({
                        "step_number": int(item.get("step_number") or item.get("number") or index),
                        "action": _clean_import_cell(item.get("action") or item.get("step") or item.get("description")),
                        "expected_result": _clean_import_cell(item.get("expected_result") or item.get("expected") or expected_result),
                    })
                else:
                    steps.append({
                        "step_number": index,
                        "action": _clean_import_cell(item),
                        "expected_result": expected_result,
                    })
            return [step for step in steps if step["action"]]
    except Exception:
        pass

    text = (
        text
        .replace("\u9884\u671f\uff1a", "=>")
        .replace("\u9884\u671f:", "=>")
        .replace("\u671f\u671b\uff1a", "=>")
        .replace("\u671f\u671b:", "=>")
    )
    raw_lines = []
    for line in text.replace("\r", "\n").replace("；", "\n").replace(";", "\n").split("\n"):
        cleaned = line.strip().lstrip("-* ").strip()
        if cleaned:
            raw_lines.append(cleaned)

    steps = []
    for index, line in enumerate(raw_lines, start=1):
        action = line
        expected = expected_result
        for sep in ("=>", "->", "预期:", "预期：", "期望:", "期望："):
            if sep in line:
                action, expected = line.split(sep, 1)
                break
        steps.append({
            "step_number": index,
            "action": action.strip(),
            "expected_result": expected.strip() or expected_result,
        })
    return steps or [{
        "step_number": 1,
        "action": text,
        "expected_result": expected_result,
    }]


def _read_import_rows(filename: str, content: bytes) -> List[Dict[str, Any]]:
    lower_name = (filename or "").lower()
    if lower_name.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [_clean_import_cell(cell) or f"column_{index}" for index, cell in enumerate(rows[0], start=1)]
        return [
            {headers[index]: row[index] if index < len(row) else None for index in range(len(headers))}
            for row in rows[1:]
            if any(_clean_import_cell(cell) for cell in row)
        ]

    if lower_name.endswith(".xls"):
        import pandas as pd

        frame = pd.read_excel(io.BytesIO(content))
        return frame.fillna("").to_dict(orient="records")

    if lower_name.endswith(".csv"):
        text = _decode_import_text(content)
        return list(csv.DictReader(io.StringIO(text)))

    script_text = _decode_import_text(content)
    inferred_format = _infer_script_format(script_text, filename)
    base_name = (filename or "imported-script").rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
    return [{
        "case_title": base_name or filename or "Imported script test case",
        "case_description": f"Imported from script file {filename}",
        "script_format": inferred_format,
        "script_content": script_text,
    }]


def _build_import_case_data(
    row: Dict[str, Any],
    category: str,
    script_format: Optional[str],
    test_plan_id: Optional[int],
) -> Dict[str, Any]:
    config = IMPORT_CATEGORY_CONFIG[category]
    title = _get_import_value(row, "case_title") or _get_import_value(row, "script_name") or "Imported test case"
    expected_result = _get_import_value(row, "expected_result")
    script_content = _get_import_value(row, "script_content")
    row_script_format = (
        _normalize_script_format(_get_import_value(row, "script_format"))
        or script_format
        or _infer_script_format(script_content, title)
    )
    allowed_formats = config.get("script_formats")
    if row_script_format and allowed_formats and row_script_format not in allowed_formats:
        raise BusinessLogicError(
            f"Script format '{row_script_format}' is not supported by {category} imports"
        )
    test_data_text = _get_import_value(row, "test_data")
    test_data: Dict[str, Any] = {}
    if test_data_text:
        try:
            parsed_data = json.loads(test_data_text)
            test_data["imported_data"] = parsed_data
        except Exception:
            test_data["imported_data"] = test_data_text
    if script_content:
        test_data["imported_script"] = {
            "category": category,
            "format": row_script_format,
            "content": script_content,
        }

    tags = list(config.get("tags", []))
    if row_script_format:
        tags.append(row_script_format)

    return {
        "test_plan_id": test_plan_id,
        "requirement_id": int(_get_import_value(row, "requirement_id") or 0) or None,
        "case_title": title[:200],
        "case_description": _get_import_value(row, "case_description") or f"Imported {category} test case",
        "case_type": config["case_type"].value,
        "module": _get_import_value(row, "module") or None,
        "priority": _parse_import_priority(_get_import_value(row, "priority")),
        "complexity": "MEDIUM",
        "automation_level": config["automation_level"],
        "preconditions": _get_import_value(row, "preconditions") or None,
        "test_steps": _parse_import_steps(_get_import_value(row, "test_steps"), expected_result),
        "expected_result": expected_result or "Result matches the imported test objective",
        "test_data": test_data or None,
        "tags": tags,
    }


def _automation_script_payload(
    test_case: TestCase,
    case_data: Dict[str, Any],
    category: str,
    script_format: Optional[str],
) -> Optional[Dict[str, Any]]:
    if category != "automation":
        return None
    script_info = (case_data.get("test_data") or {}).get("imported_script") or {}
    script_content = script_info.get("content")
    if not script_content:
        return None

    normalized_format = _normalize_script_format(script_info.get("format") or script_format) or "python"
    framework = "PYTEST"
    language = "PYTHON"
    browser = None
    if normalized_format == "playwright":
        framework = "PLAYWRIGHT"
        browser = "chromium"
    elif normalized_format == "selenium":
        framework = "SELENIUM"
        browser = "chrome"
    elif normalized_format in {"js", "javascript"}:
        framework = "JEST"
        language = "JAVASCRIPT"

    return {
        "script_name": f"{test_case.case_code}-{normalized_format}",
        "framework": framework,
        "language": language,
        "script_content": script_content,
        "browser": browser,
        "environment_config": {
            "source": "test_case_import",
            "import_format": normalized_format,
        },
        "dependencies": [],
        "created_by": test_case.creator_id,
    }


def _build_automation_config(request: "GenerateAutomationScriptRequest") -> AutomationConfig:
    config = AutomationConfig()
    automation_config = request.automation_config or {}

    framework_value = _normalize_automation_value(request.framework) or AutomationFramework.PLAYWRIGHT.value
    language_value = _normalize_automation_value(request.language) or ProgrammingLanguage.PYTHON.value
    browser_value = _normalize_automation_value(request.browser) or BrowserType.CHROME.value

    aliases = {
        "CHROMIUM": "CHROME",
        "JS": "JAVASCRIPT",
        "TS": "JAVASCRIPT",
        "TYPESCRIPT": "JAVASCRIPT",
        "WEBDRIVERIO": "SELENIUM",
        "WEBDRIVER_IO": "SELENIUM",
    }
    framework_value = aliases.get(framework_value, framework_value)
    language_value = aliases.get(language_value, language_value)
    browser_value = aliases.get(browser_value, browser_value)

    try:
        config.framework = AutomationFramework(framework_value)
    except ValueError:
        config.framework = AutomationFramework.PLAYWRIGHT

    try:
        config.language = ProgrammingLanguage(language_value)
    except ValueError:
        config.language = ProgrammingLanguage.PYTHON

    try:
        config.browser = BrowserType(browser_value)
    except ValueError:
        config.browser = BrowserType.CHROME

    for attr in ("use_page_object_model", "include_error_handling", "include_screenshots", "include_logging"):
        if attr in automation_config:
            setattr(config, attr, bool(automation_config[attr]))

    for attr in ("wait_strategy", "assertion_style", "test_data_source"):
        value = automation_config.get(attr)
        if isinstance(value, str) and value.strip():
            setattr(config, attr, value.strip())

    return config


def _text_contains_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _infer_case_type(requirement: Requirement, requested_type: Optional[TestCaseType]) -> TestCaseType:
    if requested_type:
        return requested_type

    text = " ".join([
        requirement.title or "",
        requirement.description or "",
        requirement.acceptance_criteria or "",
        requirement.category or "",
        " ".join(requirement.tags or []) if isinstance(requirement.tags, list) else "",
    ]).lower()

    if requirement.requirement_type == RequirementType.INTERFACE or _text_contains_any(text, ["api", "接口", "http", "webhook"]):
        return TestCaseType.INTEGRATION
    if _text_contains_any(text, ["性能", "并发", "响应时间", "吞吐", "压测", "load", "performance"]):
        return TestCaseType.PERFORMANCE
    if _text_contains_any(text, ["安全", "权限", "加密", "认证", "授权", "漏洞", "security", "auth"]):
        return TestCaseType.SECURITY
    if _text_contains_any(text, ["易用", "体验", "可用性", "ui", "ux", "usability"]):
        return TestCaseType.USABILITY
    if requirement.requirement_type in {RequirementType.NON_FUNCTIONAL, RequirementType.CONSTRAINT}:
        return TestCaseType.NON_FUNCTIONAL
    return TestCaseType.FUNCTIONAL


def _infer_priority(requirement: Requirement, requested_priority: Optional[TestCasePriority]) -> TestCasePriority:
    if requested_priority:
        return requested_priority

    mapping = {
        RequirementPriority.CRITICAL: TestCasePriority.CRITICAL,
        RequirementPriority.HIGH: TestCasePriority.HIGH,
        RequirementPriority.MEDIUM: TestCasePriority.MEDIUM,
        RequirementPriority.LOW: TestCasePriority.LOW,
        RequirementPriority.OPTIONAL: TestCasePriority.LOW,
    }
    return mapping.get(requirement.priority, TestCasePriority.MEDIUM)


def _infer_max_cases(requirement: Requirement) -> int:
    complexity_cases = {
        RequirementComplexity.SIMPLE: 3,
        RequirementComplexity.MEDIUM: 5,
        RequirementComplexity.COMPLEX: 8,
        RequirementComplexity.VERY_COMPLEX: 10,
    }
    max_cases = complexity_cases.get(requirement.complexity, 6)
    content_length = len(requirement.description or "") + len(requirement.acceptance_criteria or "")
    if content_length > 2500:
        max_cases += 2
    elif content_length > 1200:
        max_cases += 1
    return max(3, max_cases)


def _template_for_case_type(case_type: TestCaseType) -> GenerationTemplate:
    return {
        TestCaseType.INTEGRATION: GenerationTemplate.INTEGRATION_TESTING,
        TestCaseType.PERFORMANCE: GenerationTemplate.PERFORMANCE_TESTING,
        TestCaseType.SECURITY: GenerationTemplate.SECURITY_TESTING,
        TestCaseType.USABILITY: GenerationTemplate.UI_TESTING,
    }.get(case_type, GenerationTemplate.FUNCTIONAL_BASIC)


def _build_generation_config(request: "GenerateTestCasesRequest", db: Session) -> GenerationConfig:
    requirement = db.query(Requirement).filter(Requirement.id == request.requirement_id).first()
    if not requirement:
        raise NotFoundError("需求不存在")

    config = GenerationConfig()
    config.case_type = _infer_case_type(requirement, request.case_type)
    config.priority = _infer_priority(requirement, request.priority)
    config.template = _template_for_case_type(config.case_type)
    config.max_cases = _infer_max_cases(requirement)
    if requirement.complexity in {RequirementComplexity.COMPLEX, RequirementComplexity.VERY_COMPLEX}:
        config.detail_level = "high"
    elif requirement.complexity == RequirementComplexity.SIMPLE:
        config.detail_level = "low"

    raw_config = request.generation_config or {}
    if isinstance(raw_config.get("include_negative_cases"), bool):
        config.include_negative_cases = raw_config["include_negative_cases"]
    if isinstance(raw_config.get("include_boundary_cases"), bool):
        config.include_boundary_cases = raw_config["include_boundary_cases"]
    if isinstance(raw_config.get("include_edge_cases"), bool):
        config.include_edge_cases = raw_config["include_edge_cases"]
    if raw_config.get("detail_level") in {"low", "medium", "high"}:
        config.detail_level = raw_config["detail_level"]

    return config


def _build_test_case_response(test_case):
    return TestCaseResponse(
        id=test_case.id,
        case_code=test_case.case_code,
        test_plan_id=test_case.test_plan_id,
        requirement_id=test_case.requirement_id,
        case_title=test_case.case_title,
        case_description=test_case.case_description,
        case_type=test_case.case_type,
        module=test_case.module,
        priority=test_case.priority,
        complexity=test_case.complexity,
        automation_level=test_case.automation_level,
        preconditions=test_case.preconditions,
        test_steps=test_case.test_steps,
        expected_result=test_case.expected_result,
        test_data=test_case.test_data,
        status=test_case.status,
        creator_id=test_case.creator_id,
        assignee_id=test_case.assignee_id,
        reviewer_id=test_case.reviewer_id,
        execution_count=test_case.execution_count,
        pass_count=test_case.pass_count,
        fail_count=test_case.fail_count,
        last_execution_date=test_case.last_execution_date,
        last_execution_status=_enum_value(test_case.last_execution_status) if test_case.last_execution_status else None,
        estimated_execution_time=test_case.estimated_execution_time,
        actual_execution_time=test_case.actual_execution_time,
        tags=test_case.tags,
        version=test_case.version,
        created_at=test_case.created_at,
        updated_at=test_case.updated_at
    )


# 请求模式
class CreateTestCaseRequest(BaseModel):
    """创建测试用例请求"""
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    requirement_id: Optional[int] = Field(None, description="关联需求ID")
    case_title: str = Field(..., min_length=1, max_length=200, description="测试用例标题")
    case_description: Optional[str] = Field(None, description="测试用例描述")
    case_type: TestCaseType = Field(..., description="用例类型")
    module: Optional[str] = Field(None, description="功能模块")
    priority: TestCasePriority = Field(TestCasePriority.MEDIUM, description="优先级")
    complexity: Optional[str] = Field("MEDIUM", description="复杂度")
    automation_level: Optional[str] = Field("MANUAL", description="自动化程度")
    preconditions: Optional[str] = Field(None, description="前置条件")
    test_steps: Optional[List[Dict[str, Any]]] = Field(None, description="测试步骤")
    expected_result: Optional[str] = Field(None, description="预期结果")
    test_data: Optional[Dict[str, Any]] = Field(None, description="测试数据")
    assignee_id: Optional[int] = Field(None, description="负责人ID")
    tags: Optional[List[str]] = Field(None, description="标签")


class UpdateTestCaseRequest(BaseModel):
    """更新测试用例请求"""
    test_plan_id: Optional[int] = Field(None, description="关联测试计划ID")
    requirement_id: Optional[int] = Field(None, description="关联需求ID")
    case_title: Optional[str] = Field(None, min_length=1, max_length=200, description="测试用例标题")
    case_description: Optional[str] = Field(None, description="测试用例描述")
    case_type: Optional[TestCaseType] = Field(None, description="用例类型")
    module: Optional[str] = Field(None, description="功能模块")
    priority: Optional[TestCasePriority] = Field(None, description="优先级")
    complexity: Optional[str] = Field(None, description="复杂度")
    automation_level: Optional[str] = Field(None, description="自动化程度")
    preconditions: Optional[str] = Field(None, description="前置条件")
    test_steps: Optional[List[Dict[str, Any]]] = Field(None, description="测试步骤")
    expected_result: Optional[str] = Field(None, description="预期结果")
    test_data: Optional[Dict[str, Any]] = Field(None, description="测试数据")
    assignee_id: Optional[int] = Field(None, description="负责人ID")
    status: Optional[TestCaseStatus] = Field(None, description="用例状态")
    tags: Optional[List[str]] = Field(None, description="标签")


class BatchUpdateTestCasesRequest(BaseModel):
    """批量更新测试用例请求"""
    case_ids: List[int] = Field(..., description="用例ID列表")
    update_data: UpdateTestCaseRequest = Field(..., description="更新数据")


class CopyTestCaseRequest(BaseModel):
    """复制测试用例请求"""
    source_case_id: int = Field(..., description="源用例ID")
    target_plan_id: Optional[int] = Field(None, description="目标计划ID")
    case_title: Optional[str] = Field(None, description="新用例标题")


class GenerateTestCasesRequest(BaseModel):
    """AI生成测试用例请求"""
    requirement_id: int = Field(..., description="需求ID")
    case_type: Optional[TestCaseType] = Field(None, description="用例类型")
    priority: Optional[TestCasePriority] = Field(None, description="优先级")
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    generation_config: Optional[Dict[str, Any]] = Field(None, description="生成配置")


class GenerateAutomationScriptRequest(BaseModel):
    """生成自动化脚本请求"""
    test_case_id: int = Field(..., description="测试用例ID")
    framework: str = Field(..., description="自动化框架")
    language: str = Field("python", description="编程语言")
    browser: str = Field("chrome", description="浏览器类型")
    automation_config: Optional[Dict[str, Any]] = Field(None, description="自动化配置")


# 响应模式
class TestCaseResponse(BaseModel):
    """测试用例响应"""
    id: int = Field(..., description="测试用例ID")
    case_code: str = Field(..., description="测试用例编码")
    test_plan_id: Optional[int] = Field(None, description="测试计划ID")
    requirement_id: Optional[int] = Field(None, description="关联需求ID")
    case_title: str = Field(..., description="测试用例标题")
    case_description: Optional[str] = Field(None, description="测试用例描述")
    case_type: TestCaseType = Field(..., description="用例类型")
    module: Optional[str] = Field(None, description="功能模块")
    priority: TestCasePriority = Field(..., description="优先级")
    complexity: str = Field(..., description="复杂度")
    automation_level: str = Field(..., description="自动化程度")
    preconditions: Optional[str] = Field(None, description="前置条件")
    test_steps: Optional[List[Dict[str, Any]]] = Field(None, description="测试步骤")
    expected_result: Optional[str] = Field(None, description="预期结果")
    test_data: Optional[Dict[str, Any]] = Field(None, description="测试数据")
    status: TestCaseStatus = Field(..., description="用例状态")
    creator_id: int = Field(..., description="创建人ID")
    assignee_id: Optional[int] = Field(None, description="负责人ID")
    reviewer_id: Optional[int] = Field(None, description="评审人ID")
    execution_count: int = Field(..., description="执行次数")
    pass_count: int = Field(..., description="通过次数")
    fail_count: int = Field(..., description="失败次数")
    last_execution_date: Optional[datetime] = Field(None, description="最后执行日期")
    last_execution_status: Optional[str] = Field(None, description="最后执行状态")
    estimated_execution_time: Optional[int] = Field(None, description="预估执行时间")
    actual_execution_time: Optional[int] = Field(None, description="实际执行时间")
    tags: Optional[List[str]] = Field(None, description="标签")
    version: int = Field(..., description="版本号")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class GeneratedTestCaseResponse(BaseModel):
    """AI生成测试用例响应"""
    case_title: str = Field(..., description="用例标题")
    case_description: str = Field(..., description="用例描述")
    test_steps: List[Dict[str, Any]] = Field(..., description="测试步骤")
    expected_result: str = Field(..., description="预期结果")
    test_data: Optional[Dict[str, Any]] = Field(None, description="测试数据")
    priority: TestCasePriority = Field(..., description="优先级")
    complexity: str = Field(..., description="复杂度")
    quality_score: Optional[float] = Field(None, description="质量评分")


class AutomationScriptResponse(BaseModel):
    """自动化脚本响应"""
    script_id: int = Field(..., description="脚本ID")
    test_case_id: int = Field(..., description="测试用例ID")
    script_name: str = Field(..., description="脚本名称")
    framework: str = Field(..., description="自动化框架")
    language: str = Field(..., description="编程语言")
    script_content: str = Field(..., description="脚本内容")
    script_path: Optional[str] = Field(None, description="脚本文件路径")
    dependencies: Optional[List[str]] = Field(None, description="依赖项")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")


class TestCaseCoverageResponse(BaseModel):
    """测试用例覆盖率响应"""
    case_id: int = Field(..., description="用例ID")
    case_code: str = Field(..., description="用例编码")
    requirement_coverage: int = Field(..., description="需求覆盖")
    total_executions: int = Field(..., description="总执行次数")
    passed_executions: int = Field(..., description="通过执行次数")
    failed_executions: int = Field(..., description="失败执行次数")
    pass_rate: float = Field(..., description="通过率")
    last_execution_date: Optional[str] = Field(None, description="最后执行日期")
    last_execution_status: Optional[str] = Field(None, description="最后执行状态")


# API接口实现
@router.post("/", response_model=BaseResponse[TestCaseResponse])
async def create_test_case(
    request: CreateTestCaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建测试用例
    
    创建新的测试用例，支持完整的用例信息定义。
    包含AI质量检查和自动编码生成。
    """
    try:
        service = TestCaseService(db)
        
        # 转换请求数据
        case_data = request.dict()
        
        # 创建测试用例
        test_case = await service.create_test_case(case_data, current_user.id)
        
        response_data = _build_test_case_response(test_case)
        
        return BaseResponse(
            success=True,
            message="测试用例创建成功",
            data=response_data
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"创建测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/copy", response_model=BaseResponse[TestCaseResponse])
async def copy_test_case_compat(
    request: CopyTestCaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """复制测试用例（放在动态ID路由前，避免被 /{case_id} 拦截）。"""
    try:
        service = TestCaseService(db)
        new_case = await service.copy_test_case(
            request.source_case_id,
            request.target_plan_id,
            current_user.id
        )
        if request.case_title:
            new_case.case_title = request.case_title
            db.commit()
            db.refresh(new_case)
        return BaseResponse(success=True, message="测试用例复制成功", data=_build_test_case_response(new_case))
    except Exception as e:
        logger.error(f"复制测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/{case_id}/duplicate", response_model=BaseResponse[TestCaseResponse])
async def duplicate_test_case_compat(
    case_id: int = Path(..., description="测试用例ID"),
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """复制测试用例（兼容前端旧路径）。"""
    return await copy_test_case_compat(
        CopyTestCaseRequest(
            source_case_id=case_id,
            target_plan_id=request.get("target_plan_id"),
            case_title=request.get("case_title")
        ),
        current_user,
        db
    )


@router.post("/batch-update", response_model=BaseResponse[List[TestCaseResponse]])
async def batch_update_test_cases_compat(
    request: BatchUpdateTestCasesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量更新测试用例（兼容前端批量操作）。"""
    try:
        service = TestCaseService(db)
        update_data = {k: v for k, v in request.update_data.dict().items() if v is not None}
        updated_cases = await service.batch_update_cases(request.case_ids, update_data, current_user.id)
        return BaseResponse(
            success=True,
            message=f"批量更新测试用例成功，共更新{len(updated_cases)}个用例",
            data=[_build_test_case_response(case) for case in updated_cases]
        )
    except Exception as e:
        logger.error(f"批量更新测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete("/batch", response_model=BaseResponse[bool])
async def batch_delete_test_cases(
    request: Dict[str, List[int]] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量删除测试用例。"""
    try:
        ids = request.get("ids") or request.get("case_ids") or []
        service = TestCaseService(db)
        for case_id in ids:
            await service.delete_test_case(case_id, current_user.id)
        return BaseResponse(success=True, message=f"批量删除成功，共处理{len(ids)}个用例", data=True)
    except Exception as e:
        logger.error(f"批量删除测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/export")
async def export_test_cases(
    test_plan_id: Optional[int] = Query(None, description="测试计划ID"),
    status: Optional[TestCaseStatus] = Query(None, description="用例状态"),
    case_type: Optional[TestCaseType] = Query(None, description="用例类型"),
    priority: Optional[TestCasePriority] = Query(None, description="优先级"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    format: str = Query("csv", description="导出格式"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导出测试用例列表为CSV。"""
    query = db.query(TestCase)
    if test_plan_id:
        query = query.filter(TestCase.test_plan_id == test_plan_id)
    if status:
        query = query.filter(TestCase.status == status)
    if case_type:
        query = query.filter(TestCase.case_type == case_type)
    if priority:
        query = query.filter(TestCase.priority == priority)
    if search:
        search_term = f"%{search}%"
        query = query.filter((TestCase.case_title.like(search_term)) | (TestCase.case_code.like(search_term)))

    rows = ["用例编号,标题,类型,优先级,状态,模块,更新时间"]
    for case in query.order_by(TestCase.created_at.desc()).all():
        rows.append(",".join([
            case.case_code or "",
            (case.case_title or "").replace(",", "，"),
            case.case_type.value if case.case_type else "",
            case.priority.value if case.priority else "",
            case.status.value if case.status else "",
            (case.module or "").replace(",", "，"),
            case.updated_at.isoformat() if case.updated_at else ""
        ]))
    return Response(
        content="\ufeff" + "\n".join(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=test-cases.{format if format in {'csv', 'txt'} else 'csv'}"}
    )


@router.post("/import", response_model=BaseResponse[Dict[str, Any]])
async def import_test_cases(
    file: UploadFile = File(...),
    test_plan_id: Optional[int] = Form(None),
    import_category: str = Form("functional"),
    script_format: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import test cases from CSV/Excel/script files with category-specific script metadata."""
    try:
        category = _normalize_import_category(import_category)
        normalized_script_format = _normalize_script_format(script_format)
        allowed_formats = IMPORT_CATEGORY_CONFIG[category].get("script_formats")
        if normalized_script_format and allowed_formats and normalized_script_format not in allowed_formats:
            raise BusinessLogicError("Script format is not supported by the selected import category")

        content = await file.read()
        if not content:
            raise BusinessLogicError("Uploaded file is empty")

        rows = _read_import_rows(file.filename or "", content)
        if not rows:
            raise BusinessLogicError("No importable rows found in uploaded file")

        service = TestCaseService(db)
        success_count = 0
        failed_count = 0
        script_count = 0
        errors: List[Dict[str, Any]] = []

        for index, row in enumerate(rows, start=2):
            try:
                case_data = _build_import_case_data(row, category, normalized_script_format, test_plan_id)
                test_case = await service.create_test_case(case_data, current_user.id)
                script_payload = _automation_script_payload(test_case, case_data, category, normalized_script_format)
                if script_payload:
                    automation_script = AutomationScript(
                        test_case_id=test_case.id,
                        script_name=script_payload["script_name"],
                        framework=script_payload["framework"],
                        language=script_payload["language"],
                        script_content=script_payload["script_content"],
                        browser=script_payload.get("browser"),
                        environment_config=script_payload.get("environment_config", {}),
                        dependencies=script_payload.get("dependencies", []),
                        created_by=current_user.id,
                    )
                    db.add(automation_script)
                    db.commit()
                    script_count += 1
                success_count += 1
            except Exception as row_error:
                db.rollback()
                failed_count += 1
                errors.append({
                    "row": index,
                    "message": str(row_error),
                })
                logger.warning(f"Import test case row {index} failed: {row_error}")

        if success_count == 0 and errors:
            raise BusinessLogicError(f"Import failed: {errors[0]['message']}")

        return BaseResponse(
            success=True,
            message="Test case import completed",
            data={
                "success_count": success_count,
                "failed_count": failed_count,
                "script_count": script_count,
                "errors": errors[:20],
                "category": category,
                "script_format": normalized_script_format,
            },
        )
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Import test cases failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Import test cases failed")


@router.post("/generate", response_model=BaseResponse[List[TestCaseResponse]])
async def generate_test_cases_persisted(
    request: GenerateTestCasesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate test cases from a requirement and save them as real test cases."""
    try:
        config = _build_generation_config(request, db)

        generator = AITestCaseGenerator(db)
        generation_result = await generator.generate_test_cases_from_requirement(
            requirement_id=request.requirement_id,
            config=config,
            user_id=current_user.id
        )
        saved_cases = await generator.batch_save_generated_cases(
            generated_cases=generation_result.get("generated_cases", []),
            test_plan_id=request.test_plan_id,
            requirement_id=request.requirement_id,
            user_id=current_user.id
        )
        if not saved_cases:
            raise BusinessLogicError("AI未生成可保存的测试用例，请调整需求内容后重试")
        response_data = [_build_test_case_response(case) for case in saved_cases]
        return BaseResponse(success=True, message=f"AI生成测试用例成功，共保存{len(response_data)}个用例", data=response_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        status_code = 504 if "超时" in str(e) else 422
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"AI generate persisted test cases failed: {str(e)}")
        raise HTTPException(status_code=500, detail="AI生成测试用例失败")


@router.post("/generate-preview-legacy", response_model=BaseResponse[List[GeneratedTestCaseResponse]])
async def generate_test_cases_compat(
    request: GenerateTestCasesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI生成测试用例（放在动态ID路由前，避免被 /{case_id} 拦截）。"""
    try:
        generator = AITestCaseGenerator(db)
        config = _build_generation_config(request, db)
        generation_result = await generator.generate_test_cases_from_requirement(
            requirement_id=request.requirement_id,
            config=config,
            user_id=current_user.id
        )
        generated_cases = generation_result.get("generated_cases", [])
        response_data = [
            GeneratedTestCaseResponse(
                case_title=case.get('case_title', ''),
                case_description=case.get('case_description', ''),
                test_steps=case.get('test_steps', []),
                expected_result=case.get('expected_result', ''),
                test_data=case.get('test_data'),
                priority=TestCasePriority(case.get('priority', 'MEDIUM')),
                complexity=case.get('complexity', 'MEDIUM'),
                quality_score=case.get('quality_score')
            )
            for case in generated_cases
        ]
        return BaseResponse(success=True, message=f"AI生成测试用例成功，共生成{len(response_data)}个用例", data=response_data)
    except Exception as e:
        logger.error(f"AI生成测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{case_id}", response_model=BaseResponse[TestCaseResponse])
async def get_test_case_real(
    case_id: int = Path(..., description="测试用例ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get test case detail using the same response builder as the list endpoint."""
    try:
        test_case = db.query(TestCase).filter(TestCase.id == case_id).first()
        if not test_case:
            raise HTTPException(status_code=404, detail="测试用例不存在")
        return BaseResponse(success=True, message="获取测试用例成功", data=_build_test_case_response(test_case))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{case_id}", response_model=BaseResponse[TestCaseResponse])
async def get_test_case(
    case_id: int = Path(..., description="测试用例ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试用例详情
    
    根据测试用例ID获取详细信息。
    """
    try:
        service = TestCaseService(db)
        
        # 获取测试用例
        test_case = await service.get_test_case_by_id(case_id)
        if not test_case:
            raise HTTPException(status_code=404, detail="测试用例不存在")
        
        # 构建响应
        response_data = TestCaseResponse(
            id=test_case.id,
            case_code=test_case.case_code,
            test_plan_id=test_case.test_plan_id,
            requirement_id=test_case.requirement_id,
            case_title=test_case.case_title,
            case_description=test_case.case_description,
            case_type=test_case.case_type,
            module=test_case.module,
            priority=test_case.priority,
            complexity=test_case.complexity,
            automation_level=test_case.automation_level,
            preconditions=test_case.preconditions,
            test_steps=test_case.test_steps,
            expected_result=test_case.expected_result,
            test_data=test_case.test_data,
            status=test_case.status,
            creator_id=test_case.creator_id,
            assignee_id=test_case.assignee_id,
            reviewer_id=test_case.reviewer_id,
            execution_count=test_case.execution_count,
            pass_count=test_case.pass_count,
            fail_count=test_case.fail_count,
            last_execution_date=test_case.last_execution_date,
            last_execution_status=_enum_value(test_case.last_execution_status) if test_case.last_execution_status else None,
            estimated_execution_time=test_case.estimated_execution_time,
            actual_execution_time=test_case.actual_execution_time,
            tags=test_case.tags,
            version=test_case.version,
            created_at=test_case.created_at,
            updated_at=test_case.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="获取测试用例成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"获取测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.put("/{case_id}", response_model=BaseResponse[TestCaseResponse])
async def update_test_case(
    case_id: int = Path(..., description="测试用例ID"),
    request: UpdateTestCaseRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新测试用例
    
    更新测试用例的信息，支持版本控制。
    """
    try:
        service = TestCaseService(db)
        
        # 转换请求数据，过滤None值
        update_data = request.dict(exclude_unset=True)
        
        # 更新测试用例
        test_case = await service.update_test_case(case_id, update_data, current_user.id)
        
        # 构建响应
        response_data = TestCaseResponse(
            id=test_case.id,
            case_code=test_case.case_code,
            test_plan_id=test_case.test_plan_id,
            requirement_id=test_case.requirement_id,
            case_title=test_case.case_title,
            case_description=test_case.case_description,
            case_type=test_case.case_type,
            module=test_case.module,
            priority=test_case.priority,
            complexity=test_case.complexity,
            automation_level=test_case.automation_level,
            preconditions=test_case.preconditions,
            test_steps=test_case.test_steps,
            expected_result=test_case.expected_result,
            test_data=test_case.test_data,
            status=test_case.status,
            creator_id=test_case.creator_id,
            assignee_id=test_case.assignee_id,
            reviewer_id=test_case.reviewer_id,
            execution_count=test_case.execution_count,
            pass_count=test_case.pass_count,
            fail_count=test_case.fail_count,
            last_execution_date=test_case.last_execution_date,
            last_execution_status=_enum_value(test_case.last_execution_status) if test_case.last_execution_status else None,
            estimated_execution_time=test_case.estimated_execution_time,
            actual_execution_time=test_case.actual_execution_time,
            tags=test_case.tags,
            version=test_case.version,
            created_at=test_case.created_at,
            updated_at=test_case.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="测试用例更新成功",
            data=response_data
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"更新测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.delete("/{case_id}", response_model=BaseResponse[bool])
async def delete_test_case(
    case_id: int = Path(..., description="测试用例ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除测试用例
    
    删除或归档测试用例。已执行的用例只能归档。
    """
    try:
        service = TestCaseService(db)
        
        # 删除测试用例
        result = await service.delete_test_case(case_id, current_user.id)
        
        return BaseResponse(
            success=True,
            message="测试用例删除成功",
            data=result
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"删除测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/", response_model=PaginatedResponse[TestCaseResponse])
async def list_test_cases(
    test_plan_id: Optional[int] = Query(None, description="测试计划ID"),
    requirement_id: Optional[int] = Query(None, description="需求ID"),
    case_type: Optional[TestCaseType] = Query(None, description="用例类型"),
    priority: Optional[TestCasePriority] = Query(None, description="优先级"),
    status: Optional[TestCaseStatus] = Query(None, description="用例状态"),
    module: Optional[str] = Query(None, description="功能模块"),
    assignee_id: Optional[int] = Query(None, description="负责人ID"),
    automation_level: Optional[str] = Query(None, description="自动化程度"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试用例列表
    
    支持多条件过滤和分页查询。
    """
    try:
        service = TestCaseService(db)
        
        # 构建过滤条件
        filters = {}
        if case_type:
            filters['case_type'] = case_type.value
        if priority:
            filters['priority'] = priority.value
        if status:
            filters['status'] = status.value
        if module:
            filters['module'] = module
        if assignee_id:
            filters['assignee_id'] = assignee_id
        if automation_level:
            filters['automation_level'] = automation_level
        if search:
            filters['search'] = search
        
        # 查询测试用例列表
        if test_plan_id:
            cases, total = await service.get_test_cases_by_plan(test_plan_id, filters, page, page_size)
        elif requirement_id:
            cases, total = await service.get_test_cases_by_requirement(requirement_id, page, page_size)
        else:
            query = db.query(TestCase)
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
                    (TestCase.case_title.like(search_term)) |
                    (TestCase.case_description.like(search_term)) |
                    (TestCase.case_code.like(search_term))
                )
            total = query.count()
            cases = query.order_by(TestCase.created_at.desc()) \
                .offset((page - 1) * page_size) \
                .limit(page_size) \
                .all()
        
        # 构建响应数据
        response_data = []
        for case in cases:
            response_data.append(_build_test_case_response(case))
        
        return PaginatedResponse(
            success=True,
            message="获取测试用例列表成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        if _is_missing_table_error(e):
            return PaginatedResponse(
                success=True,
                message="测试用例表未初始化，当前无数据",
                data=[],
                total=0,
                page=page,
                page_size=page_size
            )
        logger.error(f"获取测试用例列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/copy", response_model=BaseResponse[TestCaseResponse])
async def copy_test_case(
    request: CopyTestCaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    复制测试用例
    
    复制现有测试用例到指定测试计划。
    """
    try:
        service = TestCaseService(db)
        
        # 复制测试用例
        new_case = await service.copy_test_case(
            request.source_case_id,
            request.target_plan_id,
            current_user.id
        )
        
        # 如果指定了新标题，更新标题
        if request.case_title:
            update_data = {'case_title': request.case_title}
            new_case = await service.update_test_case(new_case.id, update_data, current_user.id)
        
        # 构建响应
        response_data = TestCaseResponse(
            id=new_case.id,
            case_code=new_case.case_code,
            test_plan_id=new_case.test_plan_id,
            requirement_id=new_case.requirement_id,
            case_title=new_case.case_title,
            case_description=new_case.case_description,
            case_type=new_case.case_type,
            module=new_case.module,
            priority=new_case.priority,
            complexity=new_case.complexity,
            automation_level=new_case.automation_level,
            preconditions=new_case.preconditions,
            test_steps=new_case.test_steps,
            expected_result=new_case.expected_result,
            test_data=new_case.test_data,
            status=new_case.status,
            creator_id=new_case.creator_id,
            assignee_id=new_case.assignee_id,
            reviewer_id=new_case.reviewer_id,
            execution_count=new_case.execution_count,
            pass_count=new_case.pass_count,
            fail_count=new_case.fail_count,
            last_execution_date=new_case.last_execution_date,
            last_execution_status=_enum_value(new_case.last_execution_status) if new_case.last_execution_status else None,
            estimated_execution_time=new_case.estimated_execution_time,
            actual_execution_time=new_case.actual_execution_time,
            tags=new_case.tags,
            version=new_case.version,
            created_at=new_case.created_at,
            updated_at=new_case.updated_at
        )
        
        return BaseResponse(
            success=True,
            message="测试用例复制成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"复制测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/batch-update", response_model=BaseResponse[List[TestCaseResponse]])
async def batch_update_test_cases(
    request: BatchUpdateTestCasesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    批量更新测试用例
    
    批量更新多个测试用例的信息。
    """
    try:
        service = TestCaseService(db)
        
        # 转换更新数据
        update_data = {k: v for k, v in request.update_data.dict().items() if v is not None}
        
        # 批量更新测试用例
        updated_cases = await service.batch_update_cases(request.case_ids, update_data, current_user.id)
        
        # 构建响应数据
        response_data = []
        for case in updated_cases:
            response_data.append(TestCaseResponse(
                id=case.id,
                case_code=case.case_code,
                test_plan_id=case.test_plan_id,
                requirement_id=case.requirement_id,
                case_title=case.case_title,
                case_description=case.case_description,
                case_type=case.case_type,
                module=case.module,
                priority=case.priority,
                complexity=case.complexity,
                automation_level=case.automation_level,
                preconditions=case.preconditions,
                test_steps=case.test_steps,
                expected_result=case.expected_result,
                test_data=case.test_data,
                status=case.status,
                creator_id=case.creator_id,
                assignee_id=case.assignee_id,
                reviewer_id=case.reviewer_id,
                execution_count=case.execution_count,
                pass_count=case.pass_count,
                fail_count=case.fail_count,
                last_execution_date=case.last_execution_date,
                last_execution_status=_enum_value(case.last_execution_status) if case.last_execution_status else None,
                estimated_execution_time=case.estimated_execution_time,
                actual_execution_time=case.actual_execution_time,
                tags=case.tags,
                version=case.version,
                created_at=case.created_at,
                updated_at=case.updated_at
            ))
        
        return BaseResponse(
            success=True,
            message=f"批量更新测试用例成功，共更新{len(response_data)}个用例",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"批量更新测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/generate-preview-internal-unused", response_model=BaseResponse[List[GeneratedTestCaseResponse]], include_in_schema=False)
async def generate_test_cases(
    request: GenerateTestCasesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI生成测试用例
    
    基于需求描述使用AI生成测试用例。
    """
    try:
        generator = AITestCaseGenerator(db)
        
        # 生成测试用例
        config = _build_generation_config(request, db)
        generation_result = await generator.generate_test_cases_from_requirement(
            requirement_id=request.requirement_id,
            config=config,
            user_id=current_user.id
        )
        generated_cases = generation_result.get("generated_cases", [])
        
        # 构建响应数据
        response_data = []
        for case in generated_cases:
            response_data.append(GeneratedTestCaseResponse(
                case_title=case.get('case_title', ''),
                case_description=case.get('case_description', ''),
                test_steps=case.get('test_steps', []),
                expected_result=case.get('expected_result', ''),
                test_data=case.get('test_data'),
                priority=TestCasePriority(case.get('priority', 'MEDIUM')),
                complexity=case.get('complexity', 'MEDIUM'),
                quality_score=case.get('quality_score')
            ))
        
        return BaseResponse(
            success=True,
            message=f"AI生成测试用例成功，共生成{len(response_data)}个用例",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"AI生成测试用例失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/generate-script", response_model=BaseResponse[AutomationScriptResponse])
async def generate_automation_script(
    request: GenerateAutomationScriptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    生成自动化测试脚本
    
    基于手动测试用例生成自动化测试脚本。
    """
    try:
        generator = AutomationScriptGenerator(db)
        
        # 生成自动化脚本
        config = _build_automation_config(request)
        generation_result = await generator.generate_automation_script(
            request.test_case_id,
            config,
            current_user.id
        )
        script = await generator.save_automation_script(
            request.test_case_id,
            {
                "script_name": f"{generation_result.get('test_case_title') or 'test_case'}_automation",
                "framework": config.framework.value,
                "language": config.language.value,
                "browser": config.browser.value,
                "script_content": generation_result.get("generated_script", ""),
                "dependencies": generation_result.get("dependencies", []),
                "environment_config": {
                    "generation_time": generation_result.get("generation_time"),
                    "validation_result": generation_result.get("validation_result"),
                    "script_metadata": generation_result.get("script_metadata"),
                },
            },
            current_user.id
        )
        
        # 构建响应
        response_data = AutomationScriptResponse(
            script_id=script.id,
            test_case_id=script.test_case_id,
            script_name=script.script_name,
            framework=script.framework,
            language=script.language,
            script_content=script.script_content,
            script_path=script.script_path,
            dependencies=script.dependencies,
            is_active=script.is_active,
            created_at=script.created_at
        )
        
        return BaseResponse(
            success=True,
            message="自动化脚本生成成功",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"生成自动化脚本失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{case_id}/coverage", response_model=BaseResponse[TestCaseCoverageResponse])
async def get_test_case_coverage(
    case_id: int = Path(..., description="测试用例ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试用例覆盖率分析
    
    分析测试用例的覆盖率和执行情况。
    """
    try:
        service = TestCaseService(db)
        
        # 获取覆盖率分析
        coverage_analysis = await service.get_case_coverage_analysis(case_id)
        
        # 构建响应
        response_data = TestCaseCoverageResponse(**coverage_analysis)
        
        return BaseResponse(
            success=True,
            message="获取测试用例覆盖率成功",
            data=response_data
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取测试用例覆盖率失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.get("/{case_id}/executions", response_model=PaginatedResponse[Dict[str, Any]])
async def get_test_case_executions(
    case_id: int = Path(..., description="测试用例ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页大小"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取测试用例执行历史
    
    获取测试用例的执行记录历史。
    """
    try:
        service = TestCaseService(db)
        
        # 获取执行历史
        executions, total = await service.get_case_execution_history(case_id, page, page_size)
        
        # 构建响应数据
        response_data = []
        for execution in executions:
            response_data.append(execution.to_dict())
        
        return PaginatedResponse(
            success=True,
            message="获取测试用例执行历史成功",
            data=response_data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取测试用例执行历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
