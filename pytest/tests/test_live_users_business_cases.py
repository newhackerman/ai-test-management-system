from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.security]


def _assert_4xx(response: requests.Response, action: str) -> None:
    assert 400 <= response.status_code < 500, f"{action}: expected 4xx, got {response.status_code} {response.text[:300]}"


def test_user_me_and_profile_are_available(authenticated_session: requests.Session, base_url: str) -> None:
    me_response = authenticated_session.get(f"{base_url}/api/v1/auth/me", timeout=10)
    profile_response = authenticated_session.get(f"{base_url}/api/v1/auth/profile", timeout=10)

    assert me_response.status_code == 200
    assert profile_response.status_code == 200


def test_user_list_supports_pagination_search_and_sort(authenticated_session: requests.Session, base_url: str) -> None:
    response = authenticated_session.get(
        f"{base_url}/api/v1/users",
        params={"skip": 0, "limit": 5, "search": "admin", "sort_by": "created_at", "sort_order": "desc"},
        timeout=10,
    )

    assert response.status_code == 200
    payload = response.json()
    assert "users" in payload or "items" in payload or isinstance(payload, list)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty_body"),
        pytest.param({"username": "ab", "email": "bad@example.com", "password": "Pytest123!"}, id="username_too_short"),
        pytest.param({"username": "pytest_invalid_email", "email": "not-email", "password": "Pytest123!"}, id="invalid_email"),
        pytest.param({"username": "pytest_short_password", "email": "pytest_short@example.com", "password": "short"}, id="password_too_short"),
    ],
)
def test_user_create_rejects_invalid_payloads(authenticated_session: requests.Session, base_url: str, payload: dict) -> None:
    response = authenticated_session.post(f"{base_url}/api/v1/users", json=payload, timeout=10)

    _assert_4xx(response, "create invalid user")


def test_user_get_update_delete_nonexistent_user_are_rejected(authenticated_session: requests.Session, base_url: str) -> None:
    user_id = 999999999

    get_response = authenticated_session.get(f"{base_url}/api/v1/users/{user_id}", timeout=10)
    update_response = authenticated_session.put(f"{base_url}/api/v1/users/{user_id}", json={"nickname": "not exists"}, timeout=10)
    delete_response = authenticated_session.delete(f"{base_url}/api/v1/users/{user_id}", timeout=10)

    _assert_4xx(get_response, "get nonexistent user")
    _assert_4xx(update_response, "update nonexistent user")
    _assert_4xx(delete_response, "delete nonexistent user")


def test_user_self_delete_and_self_lock_are_rejected(authenticated_session: requests.Session, base_url: str) -> None:
    me_response = authenticated_session.get(f"{base_url}/api/v1/auth/me", timeout=10)
    assert me_response.status_code == 200
    user_info = me_response.json().get("user_info") or me_response.json().get("user") or me_response.json()
    user_id = int(user_info["user_id"] if "user_id" in user_info else user_info["id"])

    delete_response = authenticated_session.delete(f"{base_url}/api/v1/users/{user_id}", timeout=10)
    lock_response = authenticated_session.post(
        f"{base_url}/api/v1/users/{user_id}/lock",
        json={"reason": "pytest should be rejected"},
        timeout=10,
    )

    _assert_4xx(delete_response, "self delete")
    _assert_4xx(lock_response, "self lock")
