from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


CORE_READ_ONLY_ENDPOINTS = [
    "/api/v1/auth/me",
    "/api/v1/users",
    "/api/v1/roles",
    "/api/v1/roles/stats",
    "/api/v1/roles/permissions/catalog",
    "/api/v1/permissions",
    "/api/v1/projects",
    "/api/v1/test-plans/",
    "/api/v1/test-cases/",
    "/api/v1/test-executions/",
    "/api/v1/test-reports/",
]


PAGINATION_VALIDATION_CASES = [
    ("/api/v1/users", {"limit": 0}),
    ("/api/v1/users", {"limit": 101}),
    ("/api/v1/roles", {"page": 0}),
    ("/api/v1/projects", {"page": 0}),
    ("/api/v1/projects", {"size": 101}),
    ("/api/v1/test-plans/", {"page": 0}),
    ("/api/v1/test-cases/", {"page_size": 101}),
]


ENUM_VALIDATION_CASES = [
    ("/api/v1/projects", {"sort_order": "sideways"}),
    ("/api/v1/test-plans/", {"test_type": "NOT_A_TYPE"}),
    ("/api/v1/test-cases/", {"priority": "NOT_A_PRIORITY"}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("path", CORE_READ_ONLY_ENDPOINTS)
def test_authenticated_core_read_only_endpoints_return_200(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=10)

    assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize(("path", "params"), PAGINATION_VALIDATION_CASES)
def test_invalid_pagination_parameters_return_422(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", params=params, timeout=10)

    assert response.status_code == 422


@pytest.mark.parametrize(("path", "params"), ENUM_VALIDATION_CASES)
def test_invalid_enum_query_parameters_return_422(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", params=params, timeout=10)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/users/not-an-int",
        "/api/v1/roles/not-an-int",
        "/api/v1/projects/not-an-int",
        "/api/v1/test-plans/not-an-int",
        "/api/v1/test-cases/not-an-int",
    ],
)
def test_invalid_path_parameter_types_return_404_or_422(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=10)

    assert response.status_code in {404, 422}
