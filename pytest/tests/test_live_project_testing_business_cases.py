from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.security]


def _assert_4xx(response: requests.Response, action: str) -> None:
    assert 400 <= response.status_code < 500, f"{action}: expected 4xx, got {response.status_code} {response.text[:300]}"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/projects",
        "/api/v1/requirements/",
        "/api/v1/test-plans/",
        "/api/v1/test-cases/",
        "/api/v1/test-executions/",
        "/api/v1/test-reports/",
    ],
)
def test_core_business_lists_are_available(authenticated_session: requests.Session, base_url: str, path: str) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=10)

    assert response.status_code < 500


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty_body"),
        pytest.param({"project_name": "", "project_type": "API_SERVICE", "planned_start_date": "2026-01-01", "planned_end_date": "2026-01-31", "project_manager_id": 1}, id="empty_name"),
        pytest.param({"project_name": "Bad Type", "project_type": "BAD_TYPE", "planned_start_date": "2026-01-01", "planned_end_date": "2026-01-31", "project_manager_id": 1}, id="bad_type"),
        pytest.param({"project_name": "Bad Date", "project_type": "API_SERVICE", "planned_start_date": "not-date", "planned_end_date": "2026-01-31", "project_manager_id": 1}, id="bad_start_date"),
    ],
)
def test_project_create_rejects_invalid_payloads(authenticated_session: requests.Session, base_url: str, payload: dict) -> None:
    response = authenticated_session.post(f"{base_url}/api/v1/projects", json=payload, timeout=10)

    _assert_4xx(response, "create invalid project")


@pytest.mark.parametrize(
    "method,path,json_body",
    [
        pytest.param("GET", "/api/v1/projects/999999999", None, id="get_project"),
        pytest.param("PUT", "/api/v1/projects/999999999", {"description": "not exists"}, id="update_project"),
        pytest.param("PATCH", "/api/v1/projects/999999999", {"description": "not exists"}, id="patch_project"),
        pytest.param("DELETE", "/api/v1/projects/999999999", None, id="delete_project"),
        pytest.param("GET", "/api/v1/test-plans/999999999", None, id="get_test_plan"),
        pytest.param("PUT", "/api/v1/test-plans/999999999", {"description": "not exists"}, id="update_test_plan"),
        pytest.param("DELETE", "/api/v1/test-plans/999999999", None, id="delete_test_plan"),
        pytest.param("GET", "/api/v1/test-cases/999999999", None, id="get_test_case"),
        pytest.param("PUT", "/api/v1/test-cases/999999999", {"case_description": "not exists"}, id="update_test_case"),
        pytest.param("DELETE", "/api/v1/test-cases/999999999", None, id="delete_test_case"),
        pytest.param("GET", "/api/v1/defects/999999999", None, id="get_defect"),
        pytest.param("PUT", "/api/v1/defects/999999999", {"description": "not exists"}, id="update_defect"),
        pytest.param("DELETE", "/api/v1/defects/999999999", None, id="delete_defect"),
    ],
)
def test_project_testing_nonexistent_resources_are_rejected(
    authenticated_session: requests.Session,
    base_url: str,
    method: str,
    path: str,
    json_body: dict | None,
) -> None:
    response = authenticated_session.request(method, f"{base_url}{path}", json=json_body, timeout=10)

    _assert_4xx(response, f"{method} nonexistent {path}")


@pytest.mark.parametrize(
    "path,payload",
    [
        pytest.param("/api/v1/test-plans/", {}, id="test_plan_empty"),
        pytest.param("/api/v1/test-plans/", {"project_id": 999999999, "plan_name": "", "test_type": "FUNCTIONAL"}, id="test_plan_empty_name"),
        pytest.param("/api/v1/test-plans/", {"project_id": 999999999, "plan_name": "Bad Type", "test_type": "BAD_TYPE"}, id="test_plan_bad_type"),
        pytest.param("/api/v1/test-cases/", {}, id="test_case_empty"),
        pytest.param("/api/v1/test-cases/", {"case_title": "", "case_type": "FUNCTIONAL"}, id="test_case_empty_title"),
        pytest.param("/api/v1/test-cases/", {"case_title": "Bad Type", "case_type": "BAD_TYPE"}, id="test_case_bad_type"),
        pytest.param("/api/v1/defects/", {}, id="defect_empty"),
        pytest.param("/api/v1/defects/", {"title": "", "description": "desc", "defect_type": "FUNCTIONAL", "severity": "LOW", "priority": "LOW"}, id="defect_empty_title"),
        pytest.param("/api/v1/defects/", {"title": "Bad Type", "description": "desc", "defect_type": "BAD_TYPE", "severity": "LOW", "priority": "LOW"}, id="defect_bad_type"),
    ],
)
def test_testing_module_create_rejects_invalid_payloads(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    payload: dict,
) -> None:
    response = authenticated_session.post(f"{base_url}{path}", json=payload, timeout=10)

    _assert_4xx(response, f"create invalid {path}")
