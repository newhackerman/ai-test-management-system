"""HTTP client for the API under test.

Thin wrapper over httpx with one login() that stores the credential and
verb helpers that always send/accept JSON.

Auth is driven by QA_AUTH_SCHEME (see config.py):
  - bearer (default): login() reads the token field (QA_TOKEN_FIELD,
    also checked inside a nested "data" object) and sends
    Authorization: Bearer <token>.
  - cookie: login() just posts the credentials; the session cookie the
    server sets is kept by httpx's cookie jar, no header is sent.
  - apikey: no login call — every request sends
    QA_API_KEY_HEADER: QA_API_KEY. login_as_admin() is a no-op that
    verifies the key with a GET on the health endpoint.

If the new API uses a different scheme (basic auth, OAuth, …), replace
auth_headers() / login() here — that is the one adaptation point.

Project note: this API also serves a plain list envelope on list
endpoints ({"projects": [...], "total": N, "page": P, ...}) — the tests
read those bodies directly; assert_envelope_ok covers the success
envelope only.
"""
from __future__ import annotations

import httpx

from config import (
    ADMIN_PASSWORD,
    ADMIN_USER,
    API_KEY,
    API_KEY_HEADER,
    AUTH_SCHEME,
    BASE_URL,
    HEALTH_PATH,
    LOGIN_PATH,
    LOGOUT_PATH,
    REFRESH_FIELD,
    TIMEOUT,
    TOKEN_FIELD,
)


def _token_from(body: dict) -> tuple[str | None, str | None]:
    """Read the token fields from a login response body.

    Checks the top level first, then a nested "data" object, so both
    {"access_token": ...} and {"data": {"access_token": ...}} work.
    """
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    access = body.get(TOKEN_FIELD) or data.get(TOKEN_FIELD)
    refresh = None
    if REFRESH_FIELD:
        refresh = body.get(REFRESH_FIELD) or data.get(REFRESH_FIELD)
    return access, refresh


class ApiClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT):
        self.base_url = base_url
        # trust_env=False: never route localhost traffic through a sandbox
        # egress proxy (its no_proxy list breaks httpx URL parsing).
        self._client = httpx.Client(base_url=base_url, timeout=timeout, trust_env=False)
        self.access_token = None
        self.refresh_token = None

    def login(self, username: str = ADMIN_USER, password: str = ADMIN_PASSWORD) -> httpx.Response:
        if AUTH_SCHEME == "apikey":
            # No login endpoint: verify the key instead.
            resp = self._client.get(HEALTH_PATH, headers=self.auth_headers())
            return resp
        resp = self._client.post(
            LOGIN_PATH,
            json={"username": username, "password": password},
        )
        if resp.status_code == 200 and AUTH_SCHEME == "bearer":
            body = resp.json()
            self.access_token, self.refresh_token = _token_from(body)
        return resp

    def login_as_admin(self) -> "ApiClient":
        resp = self.login()
        assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text[:300]}"
        if AUTH_SCHEME == "bearer":
            assert self.access_token, "login returned 200 but no token was found"
        return self

    def logout(self) -> httpx.Response:
        return self.post(LOGOUT_PATH)

    def auth_headers(self) -> dict:
        if AUTH_SCHEME == "apikey":
            return {API_KEY_HEADER: API_KEY} if API_KEY else {}
        if AUTH_SCHEME == "cookie":
            return {}  # the session cookie lives in the client's jar
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    def _headers(self, kw: dict) -> dict:
        extra = kw.pop("headers", {}) or {}
        return {**self.auth_headers(), **extra}

    def get(self, path: str, **kw) -> httpx.Response:
        return self._client.get(path, headers=self._headers(kw), **kw)

    def post(self, path: str, json: dict | None = None, **kw) -> httpx.Response:
        return self._client.post(path, json=json, headers=self._headers(kw), **kw)

    def put(self, path: str, json: dict | None = None, **kw) -> httpx.Response:
        return self._client.put(path, json=json, headers=self._headers(kw), **kw)

    def patch(self, path: str, json: dict | None = None, **kw) -> httpx.Response:
        return self._client.patch(path, json=json, headers=self._headers(kw), **kw)

    def delete(self, path: str, **kw) -> httpx.Response:
        return self._client.delete(path, headers=self._headers(kw), **kw)

    def close(self) -> None:
        self._client.close()


class AnonymousClient(ApiClient):
    """Same verbs, but never sends an Authorization header."""

    def auth_headers(self) -> dict:
        return {}
