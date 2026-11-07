"""Smoke tests: the service is up and its public surface answers.

Paths come from config.py. If the new project uses different paths,
set QA_HEALTH_PATH (and QA_LOGIN_PATH for the login check) instead of
editing this file.
"""
import httpx
import pytest

from client import ApiClient
from config import BASE_URL, HEALTH_PATH


def _get(path: str) -> httpx.Response:
    # trust_env=False: never route localhost traffic through a sandbox
    # egress proxy.
    with httpx.Client(trust_env=False, timeout=15) as client:
        return client.get(f"{BASE_URL}{path}")


@pytest.mark.smoke
def test_health_endpoint():
    resp = _get(HEALTH_PATH)
    assert resp.status_code == 200


@pytest.mark.smoke
def test_root_returns_service_info():
    resp = _get("/")
    assert resp.status_code == 200


@pytest.mark.smoke
def test_swagger_docs_reachable():
    resp = _get("/api/v1/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()


@pytest.mark.smoke
def test_openapi_json_lists_paths():
    resp = _get("/api/v1/openapi.json")
    assert resp.status_code == 200
    assert resp.json().get("paths"), "openapi.json has no paths"


@pytest.mark.smoke
def test_admin_login_works():
    client = ApiClient().login_as_admin()
    assert client.access_token
    client.close()
