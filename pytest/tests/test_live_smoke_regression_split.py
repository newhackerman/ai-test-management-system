from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


@pytest.mark.smoke
def test_smoke_backend_health_is_available(live_session: requests.Session, base_url: str) -> None:
    response = live_session.get(f"{base_url}/health", timeout=5)

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.smoke
def test_smoke_openapi_schema_is_available(live_session: requests.Session, base_url: str) -> None:
    response = live_session.get(f"{base_url}/api/v1/openapi.json", timeout=10)

    assert response.status_code == 200
    assert response.json()["openapi"].startswith("3.")


@pytest.mark.smoke
def test_smoke_authenticated_settings_are_available(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    response = authenticated_session.get(f"{base_url}/api/v1/settings", timeout=10)

    assert response.status_code == 200
    payload = response.json()
    assert "settings" in payload
    assert "systemName" in payload["settings"]


@pytest.mark.smoke
def test_smoke_cache_preheating_status_is_available(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    response = authenticated_session.get(f"{base_url}/api/v1/cache-preheating/status", timeout=10)

    assert response.status_code == 200
    payload = response.json()
    assert "enabled" in payload
    assert "statistics" in payload


def test_regression_auto_recovery_status_endpoints_return_json(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    for path in [
        "/api/v1/auto-recovery/monitoring-status",
        "/api/v1/auto-recovery/recovery-history",
        "/api/v1/auto-recovery/statistics",
        "/api/v1/auto-recovery/failure-types",
        "/api/v1/auto-recovery/health-check",
    ]:
        response = authenticated_session.get(f"{base_url}{path}", timeout=10)
        assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text[:300]}"
        assert response.headers.get("content-type", "").startswith("application/json")


def test_regression_cache_preheating_read_only_endpoints_return_json(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    for path in [
        "/api/v1/cache-preheating/patterns",
        "/api/v1/cache-preheating/tasks",
        "/api/v1/cache-preheating/statistics",
        "/api/v1/cache-preheating/health",
    ]:
        response = authenticated_session.get(f"{base_url}{path}", timeout=10)
        assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text[:300]}"
        assert response.headers.get("content-type", "").startswith("application/json")


def test_regression_notifications_read_only_endpoints_return_json(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    for path in [
        "/api/v1/notifications",
        "/api/v1/notifications/unread-count",
    ]:
        response = authenticated_session.get(f"{base_url}{path}", timeout=10)
        assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text[:300]}"
        assert response.headers.get("content-type", "").startswith("application/json")


def test_regression_settings_endpoint_contains_expected_keys(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    response = authenticated_session.get(f"{base_url}/api/v1/settings", timeout=10)

    assert response.status_code == 200
    settings = response.json()["settings"]
    assert "systemVersion" in settings
    assert "passwordMinLength" in settings


def test_regression_missing_notification_id_returns_not_500(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    response = authenticated_session.patch(f"{base_url}/api/v1/notifications/9876543210123/read", timeout=10)

    assert response.status_code < 500
