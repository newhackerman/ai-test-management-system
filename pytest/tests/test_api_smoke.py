from __future__ import annotations

import pytest


@pytest.mark.smoke
@pytest.mark.api
def test_root_health_endpoint(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.smoke
@pytest.mark.api
def test_versioned_health_endpoint(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.smoke
@pytest.mark.api
def test_root_endpoint_returns_version(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == "1.0.0"
