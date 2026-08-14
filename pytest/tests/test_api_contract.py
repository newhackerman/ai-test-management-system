from __future__ import annotations

from collections import Counter, defaultdict

import pytest
from fastapi.routing import APIRoute


CRITICAL_PATH_PREFIXES = [
    "/api/v1/auth",
    "/api/v1/users",
    "/api/v1/projects",
    "/api/v1/requirements",
    "/api/v1/test-plans",
    "/api/v1/test-cases",
    "/api/v1/test-executions",
    "/api/v1/test-reports",
    "/api/v1/defects",
    "/api/v1/dashboards",
    "/api/v1/meetings",
]


def _api_routes(app) -> list[APIRoute]:
    return [route for route in app.routes if isinstance(route, APIRoute)]


@pytest.mark.contract
@pytest.mark.api
def test_fastapi_app_exposes_large_api_surface(app) -> None:
    routes = _api_routes(app)
    assert len(routes) >= 100


@pytest.mark.contract
@pytest.mark.api
def test_critical_modules_have_registered_routes(app) -> None:
    paths = {route.path for route in _api_routes(app)}
    missing = [
        prefix
        for prefix in CRITICAL_PATH_PREFIXES
        if not any(path == prefix or path.startswith(prefix + "/") for path in paths)
    ]

    assert not missing, "Missing critical API route groups: " + ", ".join(missing)


@pytest.mark.contract
@pytest.mark.api
def test_openapi_schema_is_generated(app) -> None:
    schema = app.openapi()

    assert schema["openapi"].startswith("3.")
    assert "/health" in schema["paths"]
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]


@pytest.mark.contract
@pytest.mark.api
def test_no_duplicate_method_path_routes(app) -> None:
    seen: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for route in _api_routes(app):
        for method in route.methods or []:
            if method in {"HEAD", "OPTIONS"}:
                continue
            seen[(method, route.path)].append(route.name)

    duplicates = {
        f"{method} {path}": names
        for (method, path), names in sorted(seen.items())
        if len(names) > 1
    }

    assert not duplicates, "Duplicate route registrations found: " + repr(duplicates)


@pytest.mark.contract
@pytest.mark.api
def test_operation_ids_are_unique_in_openapi(app) -> None:
    schema = app.openapi()
    operation_ids = [
        operation.get("operationId")
        for methods in schema["paths"].values()
        for operation in methods.values()
        if isinstance(operation, dict) and operation.get("operationId")
    ]
    duplicated = sorted(item for item, count in Counter(operation_ids).items() if count > 1)

    assert not duplicated, "Duplicated OpenAPI operationId values: " + ", ".join(duplicated)
