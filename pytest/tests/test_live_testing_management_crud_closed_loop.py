from __future__ import annotations

import uuid
from typing import Any

import pytest
import requests

from conftest import LiveCleanupStack


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.business_crud]

AUTO_PREFIX = "PYTEST_AUTO"
PROJECT_ID = 1


def _unique(label: str) -> str:
    return f"{AUTO_PREFIX}_{label}_{uuid.uuid4().hex[:10]}"


def _json(response: requests.Response, expected_status: int, action: str) -> dict[str, Any]:
    assert response.status_code == expected_status, f"{action} failed: {response.status_code} {response.text[:800]}"
    if not response.text:
        return {}
    assert response.headers.get("content-type", "").startswith("application/json")
    payload = response.json()
    assert isinstance(payload, dict), f"{action} returned non-object JSON: {payload!r}"
    return payload


def _data(payload: dict[str, Any]) -> Any:
    return payload.get("data", payload)


def _object(payload: dict[str, Any], action: str) -> dict[str, Any]:
    value = _data(payload)
    assert isinstance(value, dict), f"{action} returned non-object data: {payload!r}"
    return value


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value: Any = _data(payload)
    if isinstance(value, dict):
        for key in ("items", "data", "results"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
    if isinstance(value, list):
        return value
    for key in ("items", "data", "results"):
        nested = payload.get(key)
        if isinstance(nested, list):
            return nested
    return []


def _extract_id(payload: dict[str, Any], *preferred_keys: str) -> int | str:
    candidates: list[Any] = []
    data = _data(payload)
    if isinstance(data, dict):
        candidates.extend(data.get(key) for key in preferred_keys)
        candidates.extend([data.get("id"), data.get("report_id")])
    candidates.extend(payload.get(key) for key in preferred_keys)
    candidates.extend([payload.get("id"), payload.get("report_id")])
    for value in candidates:
        if value is not None:
            return value
    pytest.fail(f"Response does not contain an id field: {payload!r}")


def _delete_resource(session: requests.Session, base_url: str, path: str, resource_id: int | str) -> None:
    response = session.delete(f"{base_url}{path}/{resource_id}", timeout=10)
    assert response.status_code in {200, 202, 204, 404}, (
        f"cleanup {path}/{resource_id} failed: {response.status_code} {response.text[:500]}"
    )


def _delete_defect(session: requests.Session, base_url: str, defect_id: int | str) -> requests.Response:
    response = session.delete(f"{base_url}/api/v1/defects/{defect_id}", timeout=10)
    if response.status_code != 422:
        return response

    status_response = session.patch(
        f"{base_url}/api/v1/defects/{defect_id}/status",
        json={"status": "REJECTED", "notes": "pytest cleanup: make auto-created defect deletable"},
        timeout=10,
    )
    assert status_response.status_code in {200, 202}, (
        f"prepare defect cleanup failed: {status_response.status_code} {status_response.text[:500]}"
    )
    return session.delete(f"{base_url}/api/v1/defects/{defect_id}", timeout=10)


def _create_test_plan(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    suffix: str,
) -> tuple[int, str, Any]:
    plan_name = f"{AUTO_PREFIX}_PLAN_{suffix}"
    payload = _json(
        session.post(
            f"{base_url}/api/v1/test-plans/",
            json={
                "project_id": PROJECT_ID,
                "plan_name": plan_name,
                "description": "pytest closed-loop test plan",
                "test_type": "FUNCTIONAL",
                "test_strategy": "closed-loop CRUD verification",
                "test_scope": "test-management module",
                "planned_start_date": "2026-12-01",
                "planned_end_date": "2026-12-31",
                "test_manager_id": 1,
            },
            timeout=10,
        ),
        200,
        "create test plan",
    )
    plan_id = int(_extract_id(payload))
    cleanup = live_cleanup_stack.add(lambda: _delete_resource(session, base_url, "/api/v1/test-plans", plan_id))
    return plan_id, plan_name, cleanup


def _create_test_case(
    session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
    plan_id: int,
    suffix: str,
) -> tuple[int, str, Any]:
    case_title = f"{AUTO_PREFIX}_CASE_{suffix}"
    payload = _json(
        session.post(
            f"{base_url}/api/v1/test-cases/",
            json={
                "test_plan_id": plan_id,
                "case_title": case_title,
                "case_description": "pytest closed-loop test case",
                "case_type": "FUNCTIONAL",
                "module": "pytest",
                "priority": "LOW",
                "complexity": "LOW",
                "automation_level": "MANUAL",
                "preconditions": "created by pytest",
                "test_steps": [{"step": 1, "action": "call API", "expected": "success"}],
                "expected_result": "success",
                "test_data": {"source": "pytest"},
                "tags": [AUTO_PREFIX, "closed-loop"],
            },
            timeout=10,
        ),
        200,
        "create test case",
    )
    case_id = int(_extract_id(payload))
    cleanup = live_cleanup_stack.add(lambda: _delete_resource(session, base_url, "/api/v1/test-cases", case_id))
    return case_id, case_title, cleanup


def test_test_plan_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    suffix = uuid.uuid4().hex[:10]
    plan_id, plan_name, cleanup = _create_test_plan(authenticated_session, base_url, live_cleanup_stack, suffix)

    detail = _object(
        _json(authenticated_session.get(f"{base_url}/api/v1/test-plans/{plan_id}", timeout=10), 200, "get test plan"),
        "get test plan",
    )
    assert detail["id"] == plan_id
    assert detail["plan_name"] == plan_name
    assert detail["project_id"] == PROJECT_ID

    updated_name = f"{plan_name}_UPDATED"
    updated = _object(
        _json(
            authenticated_session.put(
                f"{base_url}/api/v1/test-plans/{plan_id}",
                json={
                    "plan_name": updated_name,
                    "description": "pytest closed-loop test plan updated",
                    "test_strategy": "updated strategy",
                    "test_scope": "updated scope",
                    "status": "DRAFT",
                },
                timeout=10,
            ),
            200,
            "update test plan",
        ),
        "update test plan",
    )
    assert updated["plan_name"] == updated_name
    assert updated["description"] == "pytest closed-loop test plan updated"

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/test-plans/",
            params={"project_id": PROJECT_ID, "search": plan_name, "page": 1, "size": 20},
            timeout=10,
        ),
        200,
        "search test plan list",
    )
    assert any(item["id"] == plan_id for item in _items(listed))

    delete_response = authenticated_session.delete(f"{base_url}/api/v1/test-plans/{plan_id}", timeout=10)
    assert delete_response.status_code in {200, 202, 204}, (
        f"delete test plan failed: {delete_response.status_code} {delete_response.text[:500]}"
    )
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/test-plans/{plan_id}", timeout=10)
    assert deleted_get.status_code == 404, (
        f"deleted test plan should be unavailable: {deleted_get.status_code} {deleted_get.text[:500]}"
    )


def test_test_case_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    suffix = uuid.uuid4().hex[:10]
    plan_id, _, plan_cleanup = _create_test_plan(authenticated_session, base_url, live_cleanup_stack, suffix)
    case_id, case_title, case_cleanup = _create_test_case(
        authenticated_session, base_url, live_cleanup_stack, plan_id, suffix
    )

    detail = _object(
        _json(authenticated_session.get(f"{base_url}/api/v1/test-cases/{case_id}", timeout=10), 200, "get test case"),
        "get test case",
    )
    assert detail["id"] == case_id
    assert detail["case_title"] == case_title
    assert detail["test_plan_id"] == plan_id

    updated_title = f"{case_title}_UPDATED"
    updated = _object(
        _json(
            authenticated_session.put(
                f"{base_url}/api/v1/test-cases/{case_id}",
                json={
                    "case_title": updated_title,
                    "case_description": "pytest closed-loop test case updated",
                    "case_type": "FUNCTIONAL",
                    "priority": "MEDIUM",
                    "status": "ACTIVE",
                    "test_steps": [{"step": 1, "action": "call updated API", "expected": "success"}],
                    "expected_result": "updated success",
                    "tags": [AUTO_PREFIX, "updated"],
                },
                timeout=10,
            ),
            200,
            "update test case",
        ),
        "update test case",
    )
    assert updated["case_title"] == updated_title
    assert updated["priority"] == "MEDIUM"

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/test-cases/",
            params={"test_plan_id": plan_id, "search": case_title, "page": 1, "size": 20},
            timeout=10,
        ),
        200,
        "search test case list",
    )
    assert any(item["id"] == case_id for item in _items(listed))

    delete_response = authenticated_session.delete(f"{base_url}/api/v1/test-cases/{case_id}", timeout=10)
    assert delete_response.status_code in {200, 202, 204}, (
        f"delete test case failed: {delete_response.status_code} {delete_response.text[:500]}"
    )
    live_cleanup_stack.discard(case_cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/test-cases/{case_id}", timeout=10)
    assert deleted_get.status_code == 404, (
        f"deleted test case should be unavailable: {deleted_get.status_code} {deleted_get.text[:500]}"
    )

    _delete_resource(authenticated_session, base_url, "/api/v1/test-plans", plan_id)
    live_cleanup_stack.discard(plan_cleanup)


def test_defect_create_read_update_search_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    suffix = uuid.uuid4().hex[:10]
    plan_id, _, plan_cleanup = _create_test_plan(authenticated_session, base_url, live_cleanup_stack, suffix)
    case_id, _, case_cleanup = _create_test_case(authenticated_session, base_url, live_cleanup_stack, plan_id, suffix)
    defect_title = f"{AUTO_PREFIX}_DEFECT_{suffix}"

    created = _object(
        _json(
            authenticated_session.post(
                f"{base_url}/api/v1/defects/",
                json={
                    "test_case_id": case_id,
                    "title": defect_title,
                    "description": "pytest closed-loop defect",
                    "steps_to_reproduce": "create via pytest",
                    "defect_type": "FUNCTIONAL",
                    "severity": "LOW",
                    "priority": "LOW",
                    "found_in_version": "pytest",
                    "test_environment": "pytest",
                },
                timeout=10,
            ),
            200,
            "create defect",
        ),
        "create defect",
    )
    defect_id = int(created["id"])
    defect_cleanup = live_cleanup_stack.add(lambda: _delete_defect(authenticated_session, base_url, defect_id))

    detail = _object(
        _json(authenticated_session.get(f"{base_url}/api/v1/defects/{defect_id}", timeout=10), 200, "get defect"),
        "get defect",
    )
    assert detail["id"] == defect_id
    assert detail["title"] == defect_title
    assert detail["test_case_id"] == case_id

    updated_title = f"{defect_title}_UPDATED"
    updated = _object(
        _json(
            authenticated_session.put(
                f"{base_url}/api/v1/defects/{defect_id}",
                json={
                    "title": updated_title,
                    "description": "pytest closed-loop defect updated",
                    "severity": "MEDIUM",
                    "priority": "MEDIUM",
                    "test_environment": "pytest-updated",
                },
                timeout=10,
            ),
            200,
            "update defect",
        ),
        "update defect",
    )
    assert updated["title"] == updated_title
    assert updated["severity"] == "MEDIUM"

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/defects/",
            params={"test_case_id": case_id, "search": defect_title, "page": 1, "size": 20},
            timeout=10,
        ),
        200,
        "search defect list",
    )
    assert any(item["id"] == defect_id for item in _items(listed))

    delete_response = _delete_defect(authenticated_session, base_url, defect_id)
    assert delete_response.status_code in {200, 202, 204}, (
        f"delete defect failed: {delete_response.status_code} {delete_response.text[:500]}"
    )
    live_cleanup_stack.discard(defect_cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/defects/{defect_id}", timeout=10)
    assert deleted_get.status_code == 404, (
        f"deleted defect should be unavailable: {deleted_get.status_code} {deleted_get.text[:500]}"
    )

    _delete_resource(authenticated_session, base_url, "/api/v1/test-cases", case_id)
    live_cleanup_stack.discard(case_cleanup)
    _delete_resource(authenticated_session, base_url, "/api/v1/test-plans", plan_id)
    live_cleanup_stack.discard(plan_cleanup)


def test_report_generate_read_delete_closed_loop(
    authenticated_session: requests.Session,
    base_url: str,
    live_cleanup_stack: LiveCleanupStack,
) -> None:
    report_name = _unique("REPORT")
    created = _json(
        authenticated_session.post(
            f"{base_url}/api/v1/test-reports/generate",
            json={
                "report_name": report_name,
                "report_type": "SUMMARY",
                "project_id": PROJECT_ID,
                "report_config": {"source": "pytest", "scope": "closed-loop"},
                "include_sections": ["summary", "defects", "executions"],
                "export_formats": ["HTML"],
                "auto_send": False,
            },
            timeout=10,
        ),
        200,
        "generate test report",
    )
    report_id = _extract_id(created)
    cleanup = live_cleanup_stack.add(lambda: _delete_resource(authenticated_session, base_url, "/api/v1/test-reports", report_id))

    detail = _json(
        authenticated_session.get(f"{base_url}/api/v1/test-reports/{report_id}", timeout=10),
        200,
        "get test report",
    )
    detail_data = _data(detail)
    assert isinstance(detail_data, dict)
    assert str(_extract_id(detail_data)) == str(report_id)

    listed = _json(
        authenticated_session.get(
            f"{base_url}/api/v1/test-reports/",
            params={"project_id": PROJECT_ID, "search": report_name, "page": 1, "size": 20},
            timeout=10,
        ),
        200,
        "search test report list",
    )
    assert any(str(item.get("id") or item.get("report_id")) == str(report_id) for item in _items(listed))

    delete_response = authenticated_session.delete(f"{base_url}/api/v1/test-reports/{report_id}", timeout=10)
    assert delete_response.status_code in {200, 202, 204}, (
        f"delete test report failed: {delete_response.status_code} {delete_response.text[:500]}"
    )
    live_cleanup_stack.discard(cleanup)

    deleted_get = authenticated_session.get(f"{base_url}/api/v1/test-reports/{report_id}", timeout=10)
    assert deleted_get.status_code == 404, (
        f"deleted test report should be unavailable: {deleted_get.status_code} {deleted_get.text[:500]}"
    )


def test_execution_mutation_without_cleanup_endpoint_is_controlled(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    response = authenticated_session.post(
        f"{base_url}/api/v1/test-executions/manual/start",
        json={
            "test_case_id": 9876543210123,
            "test_environment": "pytest",
            "browser_info": "none",
            "os_info": "windows",
            "execution_notes": "nonexistent test case should not create execution residue",
        },
        timeout=10,
    )
    assert 400 <= response.status_code < 500, (
        "manual execution start for nonexistent test case should fail without creating residue: "
        f"{response.status_code} {response.text[:500]}"
    )
