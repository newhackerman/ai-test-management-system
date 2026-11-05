"""Authentication & authorization tests."""
import pytest

from assertions import assert_status
from client import AnonymousClient
from config import ADMIN_PASSWORD, ADMIN_USER


@pytest.mark.auth
def test_login_success_returns_tokens(api):
    # `api` fixture already logged in; re-login explicitly to check the shape.
    resp = api.login(ADMIN_USER, ADMIN_PASSWORD)
    assert_status(resp, 200, "login")
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0
    assert body["user"]["username"] == ADMIN_USER


@pytest.mark.auth
@pytest.mark.negative
def test_login_wrong_password_returns_401():
    client = AnonymousClient()
    resp = client.login(ADMIN_USER, "wrongpassword1")
    assert_status(resp, 401, "wrong password")
    client.close()


@pytest.mark.auth
@pytest.mark.negative
def test_login_unknown_user_returns_401():
    client = AnonymousClient()
    resp = client.login("ghost-user-qa", "whatever123")
    assert_status(resp, 401, "unknown user")
    client.close()


@pytest.mark.auth
@pytest.mark.negative
def test_login_short_password_returns_422():
    # LoginRequest enforces min_length=8 on password.
    client = AnonymousClient()
    resp = client.login(ADMIN_USER, "short")
    assert_status(resp, 422, "short password")
    client.close()


@pytest.mark.auth
@pytest.mark.negative
def test_login_missing_field_returns_422():
    client = AnonymousClient()
    resp = client.post("/api/v1/auth/login", json={"username": ADMIN_USER})
    assert_status(resp, 422, "missing password")
    client.close()


@pytest.mark.auth
def test_profile_returns_current_user(api):
    resp = api.get("/api/v1/auth/profile")
    assert_status(resp, 200, "profile")
    info = resp.json()["user_info"]
    assert info["username"] == ADMIN_USER
    assert info["email"] == "admin@example.com"


@pytest.mark.auth
@pytest.mark.negative
def test_profile_without_token_returns_401(anon):
    resp = anon.get("/api/v1/auth/profile")
    assert_status(resp, 401, "profile without token")


@pytest.mark.auth
@pytest.mark.negative
def test_protected_resource_without_token_returns_401(anon):
    resp = anon.get("/api/v1/projects")
    assert_status(resp, 401, "projects without token")


@pytest.mark.auth
@pytest.mark.negative
def test_protected_resource_with_garbage_token_returns_401(anon):
    resp = anon.get(
        "/api/v1/projects", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert_status(resp, 401, "projects with garbage token")


@pytest.mark.auth
@pytest.mark.negative
def test_protected_resource_with_tampered_token_returns_401(api):
    tampered = api.access_token[:-4] + "xxxx"
    resp = api.get("/api/v1/projects", headers={"Authorization": f"Bearer {tampered}"})
    assert_status(resp, 401, "projects with tampered token")


@pytest.mark.auth
def test_refresh_token_issues_new_access_token(api):
    resp = api.post("/api/v1/auth/refresh", json={"refresh_token": api.refresh_token})
    assert_status(resp, 200, "refresh")
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.auth
@pytest.mark.negative
def test_refresh_with_bad_token_returns_401_or_400(anon):
    resp = anon.post("/api/v1/auth/refresh", json={"refresh_token": "bad-refresh-token"})
    assert resp.status_code in (400, 401), (
        f"expected 400/401 for bad refresh token, got {resp.status_code}: {resp.text[:300]}"
    )


@pytest.mark.auth
def test_logout_succeeds(api):
    resp = api.logout()
    assert_status(resp, 200, "logout")
    assert "登出成功" in resp.text
    # Re-login so later tests in the session keep working.
    api.login_as_admin()
