from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api, pytest.mark.security]


@pytest.mark.parametrize(
    ("path", "headers"),
    [
        ("/api/v1/auth/me", {"Authorization": "Bearer invalid.token.value"}),
        ("/api/v1/users", {"Authorization": "Bearer invalid.token.value"}),
        ("/api/v1/projects", {"Authorization": "Bearer invalid.token.value"}),
    ],
)
def test_invalid_bearer_token_is_rejected(live_session: requests.Session, base_url: str, path: str, headers: dict) -> None:
    response = live_session.get(f"{base_url}{path}", headers=headers, timeout=10)

    assert response.status_code in {401, 403}


def test_refresh_token_requires_payload(live_session: requests.Session, base_url: str) -> None:
    response = live_session.post(f"{base_url}/api/v1/auth/refresh", json={}, timeout=10)

    assert response.status_code in {400, 422}


def test_login_requires_valid_request_body(live_session: requests.Session, base_url: str) -> None:
    response = live_session.post(f"{base_url}/api/v1/auth/login", json={}, timeout=10)

    assert response.status_code == 422


def test_cors_preflight_allows_frontend_origin(live_session: requests.Session, base_url: str) -> None:
    response = live_session.options(
        f"{base_url}/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
        timeout=10,
    )

    assert response.status_code in {200, 204}
    assert response.headers.get("access-control-allow-origin") in {"http://localhost:3000", "*"}


def test_self_delete_is_blocked(authenticated_session: requests.Session, base_url: str) -> None:
    me_response = authenticated_session.get(f"{base_url}/api/v1/auth/me", timeout=10)
    assert me_response.status_code == 200
    user_id = int(me_response.json()["user_info"]["user_id"])

    response = authenticated_session.delete(f"{base_url}/api/v1/users/{user_id}", timeout=10)

    assert response.status_code in {400, 403}
