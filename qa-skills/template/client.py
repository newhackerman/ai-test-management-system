"""HTTP client for the API under test.

Thin wrapper over httpx with one login() that stores access/refresh tokens
and verb helpers that always send/accept JSON.

Adaptation points for a new project:
  - LOGIN_PATH comes from config.py; point it at the new login endpoint.
  - Token field names below (access_token / refresh_token) must match the
    login response. If the new API returns a different shape, adjust the
    two lines marked ADAPT.
  - If the new API uses a different auth scheme (cookie, API key), replace
    auth_headers() accordingly.
"""
from __future__ import annotations

import httpx

from config import BASE_URL, ADMIN_USER, ADMIN_PASSWORD, LOGIN_PATH, TIMEOUT


class ApiClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT):
        self.base_url = base_url
        # trust_env=False: never route localhost traffic through a sandbox
        # egress proxy (its no_proxy list breaks httpx URL parsing).
        self._client = httpx.Client(base_url=base_url, timeout=timeout, trust_env=False)
        self.access_token = None
        self.refresh_token = None

    def login(self, username: str = ADMIN_USER, password: str = ADMIN_PASSWORD) -> httpx.Response:
        resp = self._client.post(
            LOGIN_PATH,
            json={"username": username, "password": password},
        )
        if resp.status_code == 200:
            body = resp.json()
            # ADAPT: token field names for the new API.
            self.access_token = body.get("access_token")
            self.refresh_token = body.get("refresh_token")
        return resp

    def login_as_admin(self) -> "ApiClient":
        resp = self.login()
        assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text[:300]}"
        return self

    def logout(self) -> httpx.Response:
        return self.post("/api/v1/auth/logout")

    def auth_headers(self) -> dict:
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
