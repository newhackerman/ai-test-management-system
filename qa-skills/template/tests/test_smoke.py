"""Smoke tests: the service is up and its public surface answers.

Paths come from config.py. If the new project uses different paths,
set QA_HEALTH_PATH (and QA_LOGIN_PATH for the login check) instead of
editing this file. The docs/openapi checks are skipped when
QA_HAS_OPENAPI=0 — a project without an OpenAPI document is not a
failure, it just has no docs to check.
"""
import httpx
import pytest

from client import ApiClient
from config import BASE_URL, DOCS_PATH, HAS_OPENAPI, HEALTH_PATH, OPENAPI_PATH


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
    if not HAS_OPENAPI:
        pytest.skip("no OpenAPI document for this project (QA_HAS_OPENAPI=0)")
    resp = _get(DOCS_PATH)
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()


@pytest.mark.smoke
def test_openapi_json_lists_paths():
    if not HAS_OPENAPI:
        pytest.skip("no OpenAPI document for this project (QA_HAS_OPENAPI=0)")
    resp = _get(OPENAPI_PATH)
    assert resp.status_code == 200
    assert resp.json().get("paths"), "openapi.json has no paths"


@pytest.mark.smoke
def test_admin_login_works():
    client = ApiClient().login_as_admin()
    assert client.access_token
    client.close()
