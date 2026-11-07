"""HTTP client for the API under test.

Thin wrapper over httpx with:
- one login() that stores access/refresh tokens,
- verb helpers that always send/accept JSON,
- envelope helpers for the API's two response shapes:
  * success envelope: {"success": true, "message": ..., "<resource>": {...}}
  * plain list envelope: {"projects": [...], "total": N, "page": P, ...}
"""
from __future__ import annotations

import httpx

from config import BASE_URL, ADMIN_USER, ADMIN_PASSWORD, TIMEOUT


class ApiClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT):
        self.base_url = base_url
        # trust_env=False: never route localhost traffic through the sandbox
        # egress proxy (its no_proxy list breaks httpx's URL parsing).
        self._client = httpx.Client(base_url=base_url, timeout=timeout, trust_env=False)
        self.access_token: str | None = None
        self.refresh_token: str | None = None

    # -- auth -------------------------------------------------------------
    def login(self, username: str = ADMIN_USER, password: str = ADMIN_PASSWORD) -> httpx.Response:
        resp = self._client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        if resp.status_code == 200:
            body = resp.json()
            self.access_token = body["access_token"]
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

    # -- verbs ------------------------------------------------------------
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
