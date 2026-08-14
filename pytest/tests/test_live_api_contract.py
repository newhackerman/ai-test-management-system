from __future__ import annotations

from collections import Counter

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


BUSINESS_PREFIXES = [
    "/api/v1/auth",
    "/api/v1/users",
    "/api/v1/roles",
    "/api/v1/permissions",
    "/api/v1/projects",
    "/api/v1/tasks",
    "/api/v1/requirements",
    "/api/v1/risks",
    "/api/v1/meetings",
    "/api/v1/test-plans",
    "/api/v1/test-cases",
    "/api/v1/test-executions",
    "/api/v1/test-reports",
    "/api/v1/defects",
    "/api/v1/quality-metrics",
    "/api/v1/dashboards",
    "/api/v1/ai-assistant",
]
KNOWN_UNSTABLE_GET_PREFIXES = (
    "/api/v1/defects/",
    "/api/v1/requirement-changes",
    "/api/v1/requirement-reviews/",
)


PUBLIC_HEALTH_ENDPOINTS = [
    "/health",
    "/api/v1/health",
    "/api/v1/openapi.json",
]


def _concrete_get_paths(schema: dict) -> list[str]:
    paths = []
    for path, operations in schema.get("paths", {}).items():
        if "{" in path or "}" in path:
            continue
        if "get" not in operations:
            continue
        if path.endswith("/openapi.json") or "websocket" in path.lower():
            continue
        if path.startswith(KNOWN_UNSTABLE_GET_PREFIXES):
            continue
        paths.append(path)
    return sorted(paths)


@pytest.mark.smoke
@pytest.mark.parametrize("path", PUBLIC_HEALTH_ENDPOINTS)
def test_live_public_health_and_docs_are_available(live_session: requests.Session, base_url: str, path: str) -> None:
    response = live_session.get(f"{base_url}{path}", timeout=10)

    assert response.status_code == 200


@pytest.mark.contract
def test_live_openapi_contains_business_modules(live_openapi_schema: dict) -> None:
    paths = set(live_openapi_schema.get("paths", {}))
    missing = [
        prefix
        for prefix in BUSINESS_PREFIXES
        if not any(path == prefix or path.startswith(prefix + "/") for path in paths)
    ]

    assert not missing, "Missing business modules in live OpenAPI: " + ", ".join(missing)


@pytest.mark.contract
def test_live_openapi_operation_ids_are_unique(live_openapi_schema: dict) -> None:
    operation_ids = [
        operation.get("operationId")
        for methods in live_openapi_schema.get("paths", {}).values()
        for operation in methods.values()
        if isinstance(operation, dict) and operation.get("operationId")
    ]
    duplicates = sorted(item for item, count in Counter(operation_ids).items() if count > 1)

    assert not duplicates, "Duplicated operationId values: " + ", ".join(duplicates)


@pytest.mark.contract
def test_live_concrete_get_endpoints_do_not_return_500(
    live_session: requests.Session,
    base_url: str,
    live_openapi_schema: dict,
) -> None:
    failures = []
    for path in _concrete_get_paths(live_openapi_schema):
        try:
            response = live_session.get(f"{base_url}{path}", timeout=10)
        except requests.RequestException as exc:
            failures.append(f"GET {path} -> request error: {type(exc).__name__}: {exc}")
            continue
        if response.status_code >= 500:
            failures.append(f"GET {path} -> {response.status_code}: {response.text[:180]}")

    assert not failures, "Concrete GET endpoints returned server errors:\n" + "\n".join(failures[:50])
