from __future__ import annotations

from collections import Counter
from urllib.parse import quote

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.coverage]


METHODS = {"get", "post", "put", "patch", "delete"}
MUTATION_METHODS = {"post", "put", "patch", "delete"}
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
SKIP_LIVE_PATH_PARTS = set()
# 说明: OpenAPI schema 只收录 HTTP 操作, 不会出现 @router.websocket 路由。
# 路径中含 "websocket"/"/ws/"/"/stream" 的端点都是普通 HTTP GET/POST,
# 应当正常参与 live probe 检查, 不应被跳过。
KNOWN_UNSTABLE_PROBE_PREFIXES = (
    "/api/v1/defects/",
    "/api/v1/requirement-changes",
    "/api/v1/requirement-reviews/",
)


def _operation_items(schema: dict):
    for path, operations in sorted(schema.get("paths", {}).items()):
        for method, operation in sorted(operations.items()):
            if method in METHODS and isinstance(operation, dict):
                yield method, path, operation


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


def _should_skip_live_probe(path: str) -> bool:
    lowered = path.lower()
    return any(part in lowered for part in SKIP_LIVE_PATH_PARTS) or path.startswith(KNOWN_UNSTABLE_PROBE_PREFIXES)


def _is_protected_mutation_path(path: str) -> bool:
    return path.startswith(PROTECTED_MUTATION_PREFIXES)


def _send_anonymous_probe(session: requests.Session, base_url: str, method: str, path: str) -> requests.Response:
    url = f"{base_url}{_sample_path(path)}"
    if method == "get":
        return session.get(url, timeout=10)
    if method == "delete":
        return session.delete(url, timeout=10)
    return session.request(method.upper(), url, json={}, timeout=10)


@pytest.mark.contract
def test_every_openapi_operation_has_minimum_metadata(live_openapi_schema: dict) -> None:
    failures = []
    operations = list(_operation_items(live_openapi_schema))

    for method, path, operation in operations:
        if not operation.get("operationId"):
            failures.append(f"{method.upper()} {path}: missing operationId")
        if "responses" not in operation:
            failures.append(f"{method.upper()} {path}: missing responses")
        if not operation.get("tags"):
            failures.append(f"{method.upper()} {path}: missing tags")

    assert len(operations) >= 700
    assert not failures, "OpenAPI operations missing required metadata:\n" + "\n".join(failures[:80])


@pytest.mark.contract
def test_operation_count_matches_expected_live_surface(live_openapi_schema: dict) -> None:
    method_counts = Counter(method.upper() for method, _, _ in _operation_items(live_openapi_schema))

    assert sum(method_counts.values()) == 734
    assert method_counts == {"GET": 334, "POST": 304, "PUT": 39, "DELETE": 51, "PATCH": 6}


@pytest.mark.security
def test_all_non_public_mutation_operations_reject_anonymous_requests(
    live_session: requests.Session,
    base_url: str,
    live_openapi_schema: dict,
) -> None:
    failures = []
    for method, path, _operation in _operation_items(live_openapi_schema):
        if (
            method not in MUTATION_METHODS
            or path in PUBLIC_PATHS
            or not _is_protected_mutation_path(path)
            or _should_skip_live_probe(path)
        ):
            continue
        try:
            response = _send_anonymous_probe(live_session, base_url, method, path)
        except requests.RequestException as exc:
            failures.append(f"{method.upper()} {path}: request error {type(exc).__name__}: {exc}")
            continue

        if response.status_code < 400 or response.status_code >= 500:
            failures.append(f"{method.upper()} {path}: expected 4xx anonymous guard, got {response.status_code}")

    assert not failures, "Anonymous guard failures:\n" + "\n".join(failures[:80])


@pytest.mark.smoke
def test_all_get_operations_do_not_crash_with_sample_parameters(
    live_session: requests.Session,
    base_url: str,
    live_openapi_schema: dict,
) -> None:
    failures = []
    for method, path, _operation in _operation_items(live_openapi_schema):
        if method != "get" or _should_skip_live_probe(path):
            continue
        try:
            response = _send_anonymous_probe(live_session, base_url, method, path)
        except requests.RequestException as exc:
            failures.append(f"GET {path}: request error {type(exc).__name__}: {exc}")
            continue
        if response.status_code >= 500:
            failures.append(f"GET {path}: {response.status_code} {response.text[:160]}")

    assert not failures, "GET operation smoke failures:\n" + "\n".join(failures[:80])
