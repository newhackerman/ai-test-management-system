from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


PROTECTED_COLLECTIONS = [
    "/api/v1/users",
    "/api/v1/roles",
    "/api/v1/projects",
    "/api/v1/requirements",
    "/api/v1/test-plans/",
    "/api/v1/test-cases/",
    "/api/v1/test-executions/",
    "/api/v1/test-reports/",
]


@pytest.mark.security
def test_live_login_rejects_invalid_credentials(live_session: requests.Session, base_url: str) -> None:
    response = live_session.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": "not-a-real-user", "password": "definitely-wrong"},
        timeout=10,
    )

    assert response.status_code == 401
    assert "access_token" not in response.text


@pytest.mark.security
@pytest.mark.parametrize("path", PROTECTED_COLLECTIONS)
def test_live_protected_collections_reject_anonymous_requests(
    live_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = live_session.get(f"{base_url}{path}", timeout=10)

    assert response.status_code in {401, 403}


@pytest.mark.smoke
def test_live_login_with_configured_credentials_returns_token(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    response = authenticated_session.get(f"{base_url}/api/v1/auth/me", timeout=10)

    assert response.status_code == 200
    assert response.json()


@pytest.mark.parametrize("path", PROTECTED_COLLECTIONS)
def test_live_authenticated_collection_requests_do_not_return_500(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=10)

    assert response.status_code < 500
