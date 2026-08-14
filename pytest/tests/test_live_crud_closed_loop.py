from __future__ import annotations

import uuid

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


AUTO_PREFIX = "PYTEST_AUTO"


def _unique(label: str) -> str:
    return f"{AUTO_PREFIX}_{label}_{uuid.uuid4().hex[:10]}"


def _extract_id(payload: dict) -> int | None:
    candidates = [
        payload.get("id"),
        payload.get("data", {}).get("id") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("project", {}).get("id") if isinstance(payload.get("data"), dict) else None,
        payload.get("project", {}).get("id") if isinstance(payload.get("project"), dict) else None,
        payload.get("user", {}).get("id") if isinstance(payload.get("user"), dict) else None,
    ]
    for value in candidates:
        if value is not None:
            return int(value)
    return None


def _assert_response(response: requests.Response, expected_status: int, action: str) -> dict:
    assert response.status_code == expected_status, f"{action} failed: {response.status_code} {response.text[:500]}"
    if not response.text:
        return {}
    return response.json()


def _delete_resource(session: requests.Session, base_url: str, path: str) -> None:
    response = session.delete(f"{base_url}{path}", timeout=10)
    assert response.status_code in {200, 202, 204, 404}, f"Cleanup failed for {path}: {response.status_code} {response.text[:300]}"


@pytest.mark.timeout(60)
def test_user_crud_closed_loop(authenticated_session: requests.Session, base_url: str) -> None:
    # 软删除用户不再污染用户列表（默认查询排除 status=deleted），
    # 且每个测试用例使用唯一 username，不会产生数据冲突，因此不再跳过。
    username = _unique("user").lower()
    user_id = None

    try:
        create_response = authenticated_session.post(
            f"{base_url}/api/v1/users",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "Pytest123!",
                "nickname": "pytest closed loop",
                "is_active": True,
            },
            timeout=10,
        )
        created = _assert_response(create_response, 201, "create user")
        user_id = _extract_id(created)
        assert user_id is not None

        get_response = authenticated_session.get(f"{base_url}/api/v1/users/{user_id}", timeout=10)
        user = _assert_response(get_response, 200, "get user")
        assert user["username"] == username

        update_response = authenticated_session.put(
            f"{base_url}/api/v1/users/{user_id}",
            json={"nickname": "pytest closed loop updated"},
            timeout=10,
        )
        updated = _assert_response(update_response, 200, "update user")
        assert updated["nickname"] == "pytest closed loop updated"

        lock_response = authenticated_session.post(
            f"{base_url}/api/v1/users/{user_id}/lock",
            json={"reason": "pytest closed loop"},
            timeout=10,
        )
        assert lock_response.status_code == 200

        unlock_response = authenticated_session.post(f"{base_url}/api/v1/users/{user_id}/unlock", timeout=10)
        assert unlock_response.status_code == 200
    finally:
        if user_id is not None:
            _delete_resource(authenticated_session, base_url, f"/api/v1/users/{user_id}")


def test_role_crud_closed_loop(authenticated_session: requests.Session, base_url: str) -> None:
    suffix = uuid.uuid4().hex[:10].upper()
    role_id = None

    try:
        create_response = authenticated_session.post(
            f"{base_url}/api/v1/roles",
            json={
                "name": f"{AUTO_PREFIX} Role {suffix}",
                "code": f"{AUTO_PREFIX}_{suffix}",
                "description": "pytest closed loop",
                "is_active": True,
                "priority": 0,
                "sort_order": 0,
                "permission_ids": [],
            },
            timeout=10,
        )
        created = _assert_response(create_response, 201, "create role")
        role_id = _extract_id(created)
        assert role_id is not None

        get_response = authenticated_session.get(f"{base_url}/api/v1/roles/{role_id}", timeout=10)
        role = _assert_response(get_response, 200, "get role")
        assert role["code"] == f"{AUTO_PREFIX}_{suffix}"

        update_response = authenticated_session.put(
            f"{base_url}/api/v1/roles/{role_id}",
            json={"description": "pytest closed loop updated", "permission_ids": []},
            timeout=10,
        )
        assert update_response.status_code == 200

        deactivate_response = authenticated_session.post(f"{base_url}/api/v1/roles/{role_id}/deactivate", timeout=10)
        assert deactivate_response.status_code == 200

        activate_response = authenticated_session.post(f"{base_url}/api/v1/roles/{role_id}/activate", timeout=10)
        assert activate_response.status_code == 200
    finally:
        if role_id is not None:
            _delete_resource(authenticated_session, base_url, f"/api/v1/roles/{role_id}")


def test_permission_crud_closed_loop(authenticated_session: requests.Session, base_url: str) -> None:
    suffix = uuid.uuid4().hex[:10].upper()
    permission_id = None

    try:
        create_response = authenticated_session.post(
            f"{base_url}/api/v1/permissions",
            json={
                "code": f"{AUTO_PREFIX}_{suffix}",
                "name": f"{AUTO_PREFIX} Permission {suffix}",
                "description": "pytest closed loop",
                "module": "pytest",
                "action": "read",
                "resource": "pytest",
                "permission_type": "api",
                "is_system_permission": False,
            },
            timeout=10,
        )
        created = _assert_response(create_response, 201, "create permission")
        permission_id = _extract_id(created)
        assert permission_id is not None

        get_response = authenticated_session.get(f"{base_url}/api/v1/permissions/{permission_id}", timeout=10)
        _assert_response(get_response, 200, "get permission")
    finally:
        if permission_id is not None:
            _delete_resource(authenticated_session, base_url, f"/api/v1/permissions/{permission_id}")


def test_project_test_plan_test_case_defect_closed_loop(authenticated_session: requests.Session, base_url: str) -> None:
    suffix = uuid.uuid4().hex[:10]
    project_id = None
    plan_id = None
    case_id = None
    defect_id = None

    try:
        project_response = authenticated_session.post(
            f"{base_url}/api/v1/projects",
            json={
                "project_name": f"{AUTO_PREFIX}_Project_{suffix}",
                "description": "pytest closed loop",
                "project_type": "API_SERVICE",
                "priority": "LOW",
                "planned_start_date": "2026-01-01",
                "planned_end_date": "2026-01-31",
                "project_manager_id": 1,
                "test_manager_id": 1,
                "tags": [AUTO_PREFIX],
                "custom_fields": {"created_by": "pytest"},
            },
            timeout=10,
        )
        project = _assert_response(project_response, 201, "create project")
        project_id = _extract_id(project)
        assert project_id is not None

        plan_response = authenticated_session.post(
            f"{base_url}/api/v1/test-plans/",
            json={
                "project_id": project_id,
                "plan_name": f"{AUTO_PREFIX}_Plan_{suffix}",
                "description": "pytest closed loop",
                "test_type": "FUNCTIONAL",
                "test_strategy": "closed loop",
                "test_scope": "api smoke",
                "planned_start_date": "2026-01-01",
                "planned_end_date": "2026-01-31",
                "test_manager_id": 1,
            },
            timeout=10,
        )
        plan = _assert_response(plan_response, 200, "create test plan")
        plan_id = _extract_id(plan)
        assert plan_id is not None

        case_response = authenticated_session.post(
            f"{base_url}/api/v1/test-cases/",
            json={
                "test_plan_id": plan_id,
                "case_title": f"{AUTO_PREFIX}_Case_{suffix}",
                "case_description": "pytest closed loop",
                "case_type": "FUNCTIONAL",
                "module": "pytest",
                "priority": "LOW",
                "preconditions": "created by pytest",
                "test_steps": [{"step": 1, "action": "call api", "expected": "success"}],
                "expected_result": "success",
                "tags": [AUTO_PREFIX],
            },
            timeout=10,
        )
        case = _assert_response(case_response, 200, "create test case")
        case_id = _extract_id(case)
        assert case_id is not None

        defect_response = authenticated_session.post(
            f"{base_url}/api/v1/defects/",
            json={
                "test_case_id": case_id,
                "title": f"{AUTO_PREFIX}_Defect_{suffix}",
                "description": "pytest closed loop",
                "steps_to_reproduce": "created by pytest",
                "defect_type": "FUNCTIONAL",
                "severity": "LOW",
                "priority": "LOW",
                "found_in_version": "pytest",
                "test_environment": "pytest",
            },
            timeout=10,
        )
        defect = _assert_response(defect_response, 200, "create defect")
        defect_id = _extract_id(defect)
        assert defect_id is not None
    finally:
        if defect_id is not None:
            _delete_resource(authenticated_session, base_url, f"/api/v1/defects/{defect_id}")
        if case_id is not None:
            _delete_resource(authenticated_session, base_url, f"/api/v1/test-cases/{case_id}")
        if plan_id is not None:
            _delete_resource(authenticated_session, base_url, f"/api/v1/test-plans/{plan_id}")
        if project_id is not None:
            _delete_resource(authenticated_session, base_url, f"/api/v1/projects/{project_id}")
