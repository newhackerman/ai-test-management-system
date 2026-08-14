from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import quote

import pytest
import requests


pytestmark = [pytest.mark.endpoint_matrix]


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "test_cases" / "api_endpoint_case_catalog.csv"
METHODS_WITH_BODY = {"POST", "PUT", "PATCH"}
MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_PATHS = {
    "/health",
    "/api/v1/health",
    "/api/v1/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/register",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/captcha",
}
PROTECTED_MUTATION_PREFIXES = (
    "/api/v1/users",
    "/api/v1/roles",
    "/api/v1/permissions",
    "/api/v1/projects",
    "/api/v1/tasks",
    "/api/v1/requirements",
    "/api/v1/requirement-",
    "/api/v1/risks",
    "/api/v1/meetings",
    "/api/v1/test-plans",
    "/api/v1/test-cases",
    "/api/v1/test-executions",
    "/api/v1/test-reports",
    "/api/v1/test-report-subscriptions",
    "/api/v1/defects",
    "/api/v1/quality-metrics",
    "/api/v1/dashboards",
    "/api/v1/user-role-management",
)
SKIP_LIVE_PATH_PARTS = ()
# 说明: 早期版本会跳过路径包含 "websocket"/"/ws/"/"/stream" 的端点,
# 误以为它们是 WebSocket 升级端点。但 OpenAPI/CSV 目录只收录 HTTP 操作,
# 真正的 @router.websocket 路由不会出现在 OpenAPI 中。因此这些路径
# (如 /api/v1/ai-websocket/ws/stats, /api/v1/streaming/stats) 实际都是
# 普通 HTTP GET 端点, 可以且应该被 requests 探测。这里清空跳过集合,
# 让它们正常参与 live probe 和 anonymous guard 检查。
DANGEROUS_MUTATION_PARTS = (
    "/demo",
    "/generate",
    "/import",
    "/process",
    "/serve",
    "/start",
    "/complete",
    "/cancel",
    "/sync",
    "/auto-distribute",
    "/distribute",
    "/test-email",
    "/test-webhook",
    "/reset-password",
)


def _load_catalog() -> list[dict[str, str]]:
    if not CATALOG_PATH.exists():
        pytest.skip(f"OpenAPI case catalog does not exist: {CATALOG_PATH}", allow_module_level=True)
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


CASES = _load_catalog()
GET_CASES = [case for case in CASES if case["method"] == "GET"]
MUTATION_GUARD_CASES = [
    case
    for case in CASES
    if case["method"] in MUTATION_METHODS
    and case["path"] not in PUBLIC_PATHS
    and case["path"].startswith(PROTECTED_MUTATION_PREFIXES)
    and not any(part in case["path"].lower() for part in DANGEROUS_MUTATION_PARTS)
]


def _case_id(case: dict[str, str]) -> str:
    return f"{case['method']} {case['path']}"


def _sample_for_param(name: str) -> str:
    lowered = name.lower()
    if "id" in lowered or lowered.endswith("_index"):
        return "999999"
    if "email" in lowered:
        return quote("pytest@example.com")
    if "date" in lowered:
        return "2026-01-01"
    if "format" in lowered:
        return "json"
    if "code" in lowered:
        return "PYTEST"
    return "pytest"


def _sample_path(path: str) -> str:
    rendered = path
    while "{" in rendered and "}" in rendered:
        start = rendered.index("{")
        end = rendered.index("}", start)
        raw = rendered[start + 1 : end]
        name = raw.split(":")[0]
        rendered = rendered[:start] + _sample_for_param(name) + rendered[end + 1 :]
    return rendered


def _skip_live_probe(path: str) -> bool:
    lowered = path.lower()
    return any(part in lowered for part in SKIP_LIVE_PATH_PARTS)


@pytest.mark.contract
@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_each_openapi_operation_has_catalog_case(case: dict[str, str]) -> None:
    assert case["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    assert case["path"].startswith("/")
    assert case["operation_id"]
    assert case["case_type"] in {
        "anonymous_guard_and_live_get_smoke",
        "anonymous_guard_then_data_factory_happy_path",
        "public_contract_or_validation",
    }
    assert case["automated_checks"]


@pytest.mark.live
@pytest.mark.api
@pytest.mark.parametrize("case", GET_CASES, ids=_case_id)
def test_each_get_operation_live_probe_does_not_return_500(
    live_session: requests.Session,
    base_url: str,
    case: dict[str, str],
) -> None:
    if _skip_live_probe(case["path"]):
        pytest.skip("WebSocket or streaming path is not probed with requests.")

    response = live_session.get(f"{base_url}{_sample_path(case['path'])}", timeout=10)

    assert response.status_code < 500, f"{response.status_code} {response.text[:300]}"


@pytest.mark.live
@pytest.mark.api
@pytest.mark.security
@pytest.mark.parametrize("case", MUTATION_GUARD_CASES, ids=_case_id)
def test_each_protected_mutation_rejects_anonymous_request(
    live_session: requests.Session,
    base_url: str,
    case: dict[str, str],
) -> None:
    if _skip_live_probe(case["path"]):
        pytest.skip("WebSocket or streaming path is not probed with requests.")

    url = f"{base_url}{_sample_path(case['path'])}"
    if case["method"] == "DELETE":
        response = live_session.delete(url, timeout=10)
    elif case["method"] in METHODS_WITH_BODY:
        response = live_session.request(case["method"], url, json={}, timeout=10)
    else:
        response = live_session.request(case["method"], url, timeout=10)

    assert 400 <= response.status_code < 500, f"Expected anonymous 4xx, got {response.status_code}: {response.text[:300]}"
