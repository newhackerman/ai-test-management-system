"""Security tests: auth/session, IDOR, injection/XSS, sensitive data,
configuration exposure, and file upload.

Scope: ONLY the local deployment (http://127.0.0.1:8000 /
http://localhost:3000). Probing only — no data destruction, no backdoors.
All test users and data created here are deleted afterwards.

Each test encodes the expected secure behavior; a failure is a finding.
Where the secure behavior is genuinely ambiguous (e.g. whether a plain
user may read a project), the test records the observed behavior and the
report grades it.
"""

import base64
import io
import json
import os
import uuid

import httpx
import jwt as pyjwt
import pytest

import factories
from client import ApiClient
from config import ADMIN_PASSWORD, ADMIN_USER, BASE_URL

pytestmark = pytest.mark.security

SEC_PASSWORD = "SecTest123!"  # meets the service password policy


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _read_app_secret() -> str | None:
    """Read the deployment SECRET_KEY for minting test tokens. Local-only;
    never printed or committed (backend/.env is gitignored)."""
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env")
    if not os.path.exists(env_path):
        return None
    for line in open(env_path):
        if line.startswith("SECRET_KEY="):
            return line.strip().split("=", 1)[1].strip("\"'")
    return None


@pytest.fixture(scope="module")
def sec_user(api):
    """A plain user with no roles/permissions, created by the admin and
    deleted after the module."""
    username = f"sec-user-{uuid.uuid4().hex[:8]}"
    resp = api.post(
        "/api/v1/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": SEC_PASSWORD,
        },
    )
    assert resp.status_code in (200, 201), f"setup: create user failed: {resp.text[:300]}"
    user = resp.json()
    user_id = user.get("id") or user.get("user", {}).get("id")
    assert user_id, f"setup: no id in {resp.text[:200]}"
    client = ApiClient(BASE_URL)
    token = client.login(username, SEC_PASSWORD)
    assert token, "setup: sec user login failed"
    yield {"id": user_id, "username": username, "client": client, "token": token}
    client.close() if hasattr(client, "close") else None
    api.delete(f"/api/v1/users/{user_id}")


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _raw(method: str, url: str, **kw):
    """One-off httpx call that never routes through the sandbox proxy."""
    with httpx.Client(trust_env=False, timeout=15) as client:
        return getattr(client, method)(url, **kw)


# ---------------------------------------------------------------------------
# 1. Auth & session
# ---------------------------------------------------------------------------

def test_brute_force_locks_account(api, sec_user):
    """Repeated failed logins must lock the account. The auth
    service locks after 3 failures (15 min) and 5 failures (24 h),
    so after the failures even the correct password must be
    rejected with 423 Locked (RFC 4918) — not 401, which means
    "bad credentials" and would mislead the user into retrying
    the password. Wrong-password / unknown-user logins still
    return 401 (see test_auth.py)."""
    for _ in range(5):
        api.post(
            "/api/v1/auth/login",
            json={"username": sec_user["username"], "password": "WrongPass123!"},
        )
    resp = api.post(
        "/api/v1/auth/login",
        json={"username": sec_user["username"], "password": SEC_PASSWORD},
    )
    assert resp.status_code == 423, (
        f"account NOT locked after 5 failed logins: {resp.status_code} {resp.text[:200]}"
    )
    assert "锁定" in resp.text or "不可用" in resp.text, (
        f"lockout not indicated in response: {resp.text[:200]}"
    )


def test_jwt_tampered_payload_rejected(api):
    """Flipping a character in the payload (signature unchanged) must 401."""
    token = api.access_token
    header, payload, signature = token.split(".")
    tampered_payload = _b64url(
        base64.urlsafe_b64decode(payload + "==").replace(b'"sub"', b'"sux"', 1)
        if b'"sub"' in base64.urlsafe_b64decode(payload + "==")
        else base64.urlsafe_b64decode(payload + "==")[:-1] + b"X"
    )
    tampered = f"{header}.{tampered_payload}.{signature}"
    resp = _raw("get", f"{BASE_URL}/api/v1/auth/me", headers=_auth_header(tampered))
    assert resp.status_code == 401, f"tampered token: got {resp.status_code}"


def test_jwt_none_alg_rejected(api):
    """An alg=none token (unsigned) must be rejected."""
    header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({"sub": "1", "exp": 9999999999}).encode())
    token = f"{header}.{payload}."
    resp = _raw("get", f"{BASE_URL}/api/v1/auth/me", headers=_auth_header(token))
    assert resp.status_code == 401, f"alg=none token: got {resp.status_code}"


def test_jwt_wrong_key_rejected(api):
    """A token signed with a different secret must be rejected."""
    token = pyjwt.encode(
        {"sub": "1", "exp": 9999999999}, "definitely-not-the-real-secret", algorithm="HS256"
    )
    resp = _raw("get", f"{BASE_URL}/api/v1/auth/me", headers=_auth_header(token))
    assert resp.status_code == 401, f"wrong-key token: got {resp.status_code}"


def test_jwt_expired_rejected():
    """A correctly signed but expired token must be rejected.
    Skipped if the deployment secret cannot be read locally."""
    secret = _read_app_secret()
    if not secret:
        pytest.skip("backend/.env not readable; cannot mint an expired token")
    import time

    token = pyjwt.encode(
        {"sub": "1", "exp": int(time.time()) - 3600}, secret, algorithm="HS256"
    )
    resp = _raw("get", f"{BASE_URL}/api/v1/auth/me", headers=_auth_header(token))
    assert resp.status_code == 401, f"expired token: got {resp.status_code}"


def test_garbage_token_rejected(api):
    resp = _raw(
        "get",
        f"{BASE_URL}/api/v1/auth/me",
        headers=_auth_header("this.is.not.a.token"),
    )
    assert resp.status_code == 401


def test_logout_invalidates_token(sec_user):
    """After logout, the same access token must stop working.
    (If it still returns 200, logout is cosmetic and the token stays
    valid until expiry — a session-management finding.)"""
    client = sec_user["client"]
    token = sec_user["token"]
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code in (200, 204), f"logout failed: {resp.status_code}"
    check = _raw("get", f"{BASE_URL}/api/v1/auth/me", headers=_auth_header(token))
    assert check.status_code == 401, (
        f"token still valid after logout: {check.status_code}"
    )


def test_refresh_token_rejected_when_invalid(api):
    resp = api.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
    assert resp.status_code in (400, 401, 422), (
        f"invalid refresh token: got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# 2. IDOR / privilege escalation
# ---------------------------------------------------------------------------

def test_low_priv_user_cannot_list_users(sec_user):
    resp = sec_user["client"].get("/api/v1/users")
    assert resp.status_code in (401, 403), (
        f"plain user listing users: got {resp.status_code}"
    )


def test_low_priv_user_cannot_create_user(sec_user):
    resp = sec_user["client"].post(
        "/api/v1/users",
        json={
            "username": f"sec-evil-{uuid.uuid4().hex[:6]}",
            "email": f"sec-evil-{uuid.uuid4().hex[:8]}@example.com",
            "password": SEC_PASSWORD,
        },
    )
    assert resp.status_code in (401, 403), (
        f"plain user creating users: got {resp.status_code}"
    )


def test_low_priv_user_cannot_delete_admin_project(api, sec_user, make_project):
    project = make_project()
    resp = sec_user["client"].delete(f"/api/v1/projects/{project['id']}")
    assert resp.status_code in (401, 403, 404), (
        f"plain user deleting admin project: got {resp.status_code}"
    )
    # The project must still exist afterwards.
    check = api.get(f"/api/v1/projects/{project['id']}")
    assert check.status_code == 200


def test_idor_read_admin_project(sec_user, make_project):
    """A plain user reading an admin-created project by id. There is no
    documented per-project ACL in this app, so a 200 here means any
    authenticated user can read any project (recorded as a finding in
    the report, not asserted as a failure)."""
    project = make_project()
    resp = sec_user["client"].get(f"/api/v1/projects/{project['id']}")
    assert resp.status_code in (200, 401, 403, 404)
    if resp.status_code == 200:
        pytest.fail(
            "IDOR: plain user can read admin project "
            f"(id={project['id']}, status 200)"
        )


def test_idor_update_admin_requirement(api, sec_user, project, make_requirement):
    req = make_requirement(project["id"])
    resp = sec_user["client"].put(
        f"/api/v1/requirements/{req['id']}",
        json={"title": "IDOR-EDITED"},
    )
    assert resp.status_code in (401, 403, 404), (
        f"plain user updating admin requirement: got {resp.status_code}"
    )
    check = api.get(f"/api/v1/requirements/{req['id']}")
    assert check.status_code == 200
    assert check.json().get("title") != "IDOR-EDITED"


def test_idor_read_admin_user_profile(sec_user, api):
    resp = sec_user["client"].get("/api/v1/users/1")
    assert resp.status_code in (401, 403, 404), (
        f"plain user reading admin profile: got {resp.status_code}: {resp.text[:200]}"
    )


# ---------------------------------------------------------------------------
# 3. Injection & XSS
# ---------------------------------------------------------------------------

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1 --",
    "'; DROP TABLE projects; --",
    "' UNION SELECT id, username, password_hash FROM users --",
]


@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
def test_sql_injection_in_search_returns_normally(api, payload):
    resp = api.get("/api/v1/projects", params={"search": payload})
    assert resp.status_code in (200, 400, 422), (
        f"SQLi search {payload!r}: got {resp.status_code}: {resp.text[:200]}"
    )
    assert "password_hash" not in resp.text
    assert "Traceback" not in resp.text
    assert "File \"" not in resp.text


def test_sql_injection_in_create_does_not_break_db(api):
    payload = factories.project_payload()
    payload["description"] = "'; DROP TABLE projects; --"
    resp = api.post("/api/v1/projects", json=payload)
    assert resp.status_code in (200, 201)
    created = resp.json().get("project", resp.json())
    try:
        check = api.get("/api/v1/projects", params={"page": 1, "page_size": 5})
        assert check.status_code == 200  # table still exists
    finally:
        api.delete(f"/api/v1/projects/{created['id']}")


XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "\"><svg onload=alert(1)>",
]


@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_stored_xss_payload_roundtrip(api, payload):
    """The API stores the raw string (expected for a JSON API); whether
    it executes is a frontend concern, covered by the E2E XSS test.
    Here we only assert the API neither executes nor 500s on it."""
    payload_body = factories.project_payload(project_name=f"QA-XSS-{uuid.uuid4().hex[:6]}")
    payload_body["description"] = payload
    resp = api.post("/api/v1/projects", json=payload_body)
    assert resp.status_code in (200, 201), f"XSS payload rejected: {resp.status_code}"
    created = resp.json().get("project", resp.json())
    try:
        check = api.get(f"/api/v1/projects/{created['id']}")
        assert check.status_code == 200
        assert check.json().get("description") == payload
    finally:
        api.delete(f"/api/v1/projects/{created['id']}")


# ---------------------------------------------------------------------------
# 4. Sensitive data & configuration
# ---------------------------------------------------------------------------

def test_login_response_has_no_password_hash(api):
    resp = api.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USER, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    assert "password_hash" not in resp.text
    assert '"salt"' not in resp.text


def test_user_detail_has_no_password_hash(api, sec_user):
    resp = api.get(f"/api/v1/users/{sec_user['id']}")
    assert resp.status_code == 200
    assert "password_hash" not in resp.text
    assert '"salt"' not in resp.text


def test_me_has_no_password_hash(api):
    resp = api.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert "password_hash" not in resp.text


def test_error_response_no_stack_leak(api):
    """A non-integer id must not leak tracebacks or filesystem paths."""
    resp = api.get("/api/v1/projects/abc")
    assert resp.status_code in (400, 404, 422)
    assert "Traceback" not in resp.text
    assert "File \"" not in resp.text
    assert "/home/" not in resp.text
    assert "site-packages" not in resp.text


def test_malformed_json_no_stack_leak(api):
    resp = _raw(
        "post",
        f"{BASE_URL}/api/v1/projects",
        content="{not valid json",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api.access_token}",
        },
    )
    assert resp.status_code in (400, 422)
    assert "Traceback" not in resp.text
    assert "/home/" not in resp.text


def test_openapi_exposed_without_auth():
    """Informational: the full API surface (including admin endpoints)
    is public without login. Recorded; graded in the report."""
    resp = _raw("get", f"{BASE_URL}/api/v1/openapi.json")
    assert resp.status_code == 200
    assert len(resp.json().get("paths", {})) > 100


def test_cors_evil_origin_rejected():
    resp = _raw(
        "options",
        f"{BASE_URL}/api/v1/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}


def test_cors_allowed_origin_ok():
    resp = _raw(
        "options",
        f"{BASE_URL}/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_security_headers_present(api):
    """Hardening check: FastAPI does not add these by default. Missing
    headers are a minor finding, recorded in the report."""
    resp = api.get("/api/v1/health")
    assert resp.status_code == 200
    missing = [
        h
        for h in (
            "x-content-type-options",
            "x-frame-options",
            "content-security-policy",
            "strict-transport-security",
            "referrer-policy",
        )
        if h not in {k.lower() for k in resp.headers}
    ]
    assert not missing, f"missing security headers: {missing}"


# ---------------------------------------------------------------------------
# 5. File upload & path traversal
# ---------------------------------------------------------------------------

def test_avatar_upload_script_file_rejected(api):
    """Uploading a .php script as an avatar must be rejected (400/415/422),
    not stored and served back."""
    files = {"file": ("shell.php", io.BytesIO(b"<?php system($_GET['c']); ?>"), "application/x-php")}
    resp = _raw(
        "post",
        f"{BASE_URL}/api/v1/auth/profile/avatar",
        files=files,
        headers=_auth_header(api.access_token),
    )
    assert resp.status_code in (400, 401, 403, 415, 422), (
        f"script avatar upload: got {resp.status_code}: {resp.text[:300]}"
    )


def test_avatar_upload_exe_file_rejected(api):
    files = {"file": ("evil.exe", io.BytesIO(b"MZ" + b"\x00" * 64), "application/octet-stream")}
    resp = _raw(
        "post",
        f"{BASE_URL}/api/v1/auth/profile/avatar",
        files=files,
        headers=_auth_header(api.access_token),
    )
    assert resp.status_code in (400, 401, 403, 415, 422), (
        f"exe avatar upload: got {resp.status_code}: {resp.text[:300]}"
    )


def test_report_download_path_traversal_blocked(api):
    """Traversal in the download path must not return file contents."""
    for path in (
        "/api/v1/reports/download/..%2F..%2Fetc%2Fpasswd/pdf",
        "/api/v1/reports/download/1/..%2F..%2Fetc%2Fpasswd",
        "/api/v1/test-reports/..%2F..%2Fetc%2Fpasswd/download/pdf",
    ):
        resp = api.get(path)
        assert resp.status_code in (400, 401, 403, 404, 422), (
            f"{path}: got {resp.status_code}"
        )
        assert "root:" not in resp.text


def test_meeting_file_upload_executable(api, make_project):
    """Best-effort: create a meeting under a project and try uploading a
    script file. Skipped if meeting creation is not possible."""
    project = make_project()
    resp = api.post(
        f"/api/v1/meetings/projects/{project['id']}/meetings",
        json={
            "title": "sec-probe-meeting",
            "meeting_type": "PROGRESS_SYNC",
            "scheduled_start_time": "2026-12-01T10:00:00",
            "scheduled_end_time": "2026-12-01T11:00:00",
        },
    )
    if resp.status_code not in (200, 201):
        pytest.skip(f"meeting creation unavailable: {resp.status_code}")
    body = resp.json()
    meeting = body.get("data", body)
    meeting_id = meeting.get("id")
    try:
        files = {"file": ("x.php", io.BytesIO(b"<?php phpinfo(); ?>"), "application/x-php")}
        up = _raw(
            "post",
            f"{BASE_URL}/api/v1/meetings/{meeting_id}/files/upload",
            files=files,
            headers=_auth_header(api.access_token),
        )
        assert up.status_code in (400, 401, 403, 415, 422), (
            f"script meeting upload: got {up.status_code}: {up.text[:300]}"
        )
    finally:
        api.delete(f"/api/v1/meetings/{meeting_id}")


# --- Requirement encryption key rotation (2026-11-08) -------------------
# The requirement data-security service used to derive its Fernet key from
# the publicly-known defaults 'default-password-change-in-production' /
# 'default-salt-change-in-production' whenever the env vars were unset —
# and they were unset everywhere (neither backend/.env nor .env.example
# had them), so every "encrypted" requirement field was decryptable by
# anyone who read the repo. The fix: real keys in backend/.env via the
# app Settings, and fail fast when they are missing. These two tests
# guard exactly that (no HTTP involved: the requirement-security router
# is not mounted, and the DB holds zero requirements).

def _load_encryption_service(monkeypatch, tmp_path):
    """Import the service with a clean CWD (backup dir lands in tmp)."""
    import sys
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parents[2] / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    monkeypatch.chdir(tmp_path)
    import src.services.requirement_data_security_service as mod

    return mod


def test_requirement_encryption_fails_without_config(monkeypatch, tmp_path):
    mod = _load_encryption_service(monkeypatch, tmp_path)
    monkeypatch.delenv("REQUIREMENT_ENCRYPTION_PASSWORD", raising=False)
    monkeypatch.delenv("REQUIREMENT_ENCRYPTION_SALT", raising=False)
    monkeypatch.setattr(mod.settings, "REQUIREMENT_ENCRYPTION_PASSWORD", None)
    monkeypatch.setattr(mod.settings, "REQUIREMENT_ENCRYPTION_SALT", None)
    with pytest.raises(RuntimeError, match="REQUIREMENT_ENCRYPTION"):
        mod.RequirementDataSecurityService(None)


def test_requirement_encryption_round_trip(monkeypatch, tmp_path):
    mod = _load_encryption_service(monkeypatch, tmp_path)
    monkeypatch.setattr(
        mod.settings, "REQUIREMENT_ENCRYPTION_PASSWORD", "test-password-rotate-2026"
    )
    monkeypatch.setattr(
        mod.settings, "REQUIREMENT_ENCRYPTION_SALT", "test-salt-rotate-2026"
    )
    svc = mod.RequirementDataSecurityService(None)
    cipher = svc.encrypt_sensitive_data("acceptance criterion: must not leak")
    assert cipher != "acceptance criterion: must not leak"
    assert svc.decrypt_sensitive_data(cipher) == (
        "acceptance criterion: must not leak"
    )
