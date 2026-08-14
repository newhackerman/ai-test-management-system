from __future__ import annotations

import uuid

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.security]


AUTO_PREFIX = "PYTEST_AUTO_ROLE"


def _assert_4xx(response: requests.Response, action: str) -> None:
    assert 400 <= response.status_code < 500, f"{action}: expected 4xx, got {response.status_code} {response.text[:300]}"


def _extract_role_id(payload: dict) -> int:
    role_id = payload.get("id") or payload.get("data", {}).get("id")
    assert role_id is not None, f"Role id missing from response: {payload}"
    return int(role_id)


def _create_role(session: requests.Session, base_url: str, *, code: str | None = None, name: str | None = None) -> int:
    suffix = uuid.uuid4().hex[:10].upper()
    payload = {
        "name": name or f"{AUTO_PREFIX} {suffix}",
        "code": code or f"{AUTO_PREFIX}_{suffix}",
        "description": "pytest role business case",
        "is_active": True,
        "priority": 0,
        "sort_order": 0,
        "permission_ids": [],
    }
    response = session.post(f"{base_url}/api/v1/roles", json=payload, timeout=10)
    assert response.status_code == 201, response.text[:500]
    return _extract_role_id(response.json())


def _delete_role(session: requests.Session, base_url: str, role_id: int | None) -> None:
    if role_id is None:
        return
    response = session.delete(f"{base_url}/api/v1/roles/{role_id}", timeout=10)
    assert response.status_code in {200, 404}, f"role cleanup failed: {response.status_code} {response.text[:300]}"


def test_role_create_get_update_activate_deactivate_delete_closed_loop(authenticated_session: requests.Session, base_url: str) -> None:
    role_id = None
    try:
        role_id = _create_role(authenticated_session, base_url)

        get_response = authenticated_session.get(f"{base_url}/api/v1/roles/{role_id}", timeout=10)
        assert get_response.status_code == 200
        assert get_response.json()["id"] == role_id

        update_response = authenticated_session.put(
            f"{base_url}/api/v1/roles/{role_id}",
            json={"description": "pytest role updated", "permission_ids": []},
            timeout=10,
        )
        assert update_response.status_code == 200

        deactivate_response = authenticated_session.post(f"{base_url}/api/v1/roles/{role_id}/deactivate", timeout=10)
        assert deactivate_response.status_code == 200

        activate_response = authenticated_session.post(f"{base_url}/api/v1/roles/{role_id}/activate", timeout=10)
        assert activate_response.status_code == 200
    finally:
        _delete_role(authenticated_session, base_url, role_id)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"code": "PYTEST_MISSING_NAME", "permission_ids": []}, id="missing_name"),
        pytest.param({"name": "Missing Code", "permission_ids": []}, id="missing_code"),
        pytest.param({"name": "", "code": "PYTEST_EMPTY_NAME", "permission_ids": []}, id="empty_name"),
        pytest.param({"name": "Empty Code", "code": "", "permission_ids": []}, id="empty_code"),
        pytest.param({"name": "Bad Permissions", "code": "PYTEST_BAD_PERMS", "permission_ids": "not-array"}, id="permission_ids_not_array"),
        pytest.param({"name": "Bad Permission Item", "code": "PYTEST_BAD_PERM_ITEM", "permission_ids": ["abc"]}, id="permission_id_not_int"),
    ],
)
def test_role_create_rejects_invalid_payloads(authenticated_session: requests.Session, base_url: str, payload: dict) -> None:
    response = authenticated_session.post(f"{base_url}/api/v1/roles", json=payload, timeout=10)

    _assert_4xx(response, "create invalid role")


def test_role_create_duplicate_code_is_rejected(authenticated_session: requests.Session, base_url: str) -> None:
    role_id = None
    code = f"{AUTO_PREFIX}_{uuid.uuid4().hex[:10].upper()}"
    try:
        role_id = _create_role(authenticated_session, base_url, code=code)
        duplicate_response = authenticated_session.post(
            f"{base_url}/api/v1/roles",
            json={"name": "Duplicate Role", "code": code, "permission_ids": []},
            timeout=10,
        )
        _assert_4xx(duplicate_response, "create duplicate role")
    finally:
        _delete_role(authenticated_session, base_url, role_id)


def test_role_get_update_delete_nonexistent_role_are_rejected(authenticated_session: requests.Session, base_url: str) -> None:
    role_id = 999999999

    get_response = authenticated_session.get(f"{base_url}/api/v1/roles/{role_id}", timeout=10)
    update_response = authenticated_session.put(
        f"{base_url}/api/v1/roles/{role_id}",
        json={"description": "not exists", "permission_ids": []},
        timeout=10,
    )
    delete_response = authenticated_session.delete(f"{base_url}/api/v1/roles/{role_id}", timeout=10)

    _assert_4xx(get_response, "get nonexistent role")
    _assert_4xx(update_response, "update nonexistent role")
    _assert_4xx(delete_response, "delete nonexistent role")


def test_role_delete_system_role_is_rejected(authenticated_session: requests.Session, base_url: str) -> None:
    list_response = authenticated_session.get(f"{base_url}/api/v1/roles", params={"type": "system", "size": 1}, timeout=10)
    assert list_response.status_code == 200
    roles = list_response.json().get("data") or list_response.json().get("roles") or []
    if not roles:
        pytest.skip("No system role found.")

    response = authenticated_session.delete(f"{base_url}/api/v1/roles/{roles[0]['id']}", timeout=10)

    _assert_4xx(response, "delete system role")


def test_role_assign_invalid_permission_is_rejected_and_role_can_be_deleted(authenticated_session: requests.Session, base_url: str) -> None:
    role_id = None
    try:
        role_id = _create_role(authenticated_session, base_url)
        response = authenticated_session.post(
            f"{base_url}/api/v1/roles/{role_id}/permissions",
            json={"permission_ids": [999999999]},
            timeout=10,
        )
        _assert_4xx(response, "assign invalid permission")
    finally:
        _delete_role(authenticated_session, base_url, role_id)
