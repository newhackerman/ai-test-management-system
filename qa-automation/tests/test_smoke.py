"""Smoke tests: the service is up and its public surface answers."""
import httpx
import pytest

from config import BASE_URL


def _get(path: str) -> httpx.Response:
    # trust_env=False: never route localhost traffic through the sandbox
    # egress proxy.
    with httpx.Client(trust_env=False, timeout=15) as client:
        return client.get(f"{BASE_URL}{path}")


@pytest.mark.smoke
def test_health_endpoint():
    resp = _get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"


@pytest.mark.smoke
def test_root_health_endpoint():
    resp = _get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "healthy"


@pytest.mark.smoke
def test_root_returns_service_info():
    resp = _get("/")
    assert resp.status_code == 200
    assert "version" in resp.json()


@pytest.mark.smoke
def test_swagger_docs_reachable():
    resp = _get("/api/v1/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()


@pytest.mark.smoke
def test_openapi_json_lists_core_modules():
    resp = _get("/api/v1/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    for prefix in ("/api/v1/projects", "/api/v1/requirements/",
                   "/api/v1/test-cases/", "/api/v1/test-plans/",
                   "/api/v1/defects/", "/api/v1/risks/"):
        assert any(p.startswith(prefix) for p in paths), f"missing routes for {prefix}"
