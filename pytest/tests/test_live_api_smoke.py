from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live]


def _require_live_backend(session: requests.Session, base_url: str) -> None:
    try:
        session.get(f"{base_url}/health", timeout=3)
    except requests.RequestException as exc:
        pytest.skip(f"Backend is not running at {base_url}: {exc}")


@pytest.mark.smoke
def test_live_backend_health(live_session: requests.Session, base_url: str) -> None:
    _require_live_backend(live_session, base_url)

    response = live_session.get(f"{base_url}/health", timeout=5)

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.smoke
def test_live_openapi_is_available(live_session: requests.Session, base_url: str) -> None:
    _require_live_backend(live_session, base_url)

    response = live_session.get(f"{base_url}/api/v1/openapi.json", timeout=10)

    assert response.status_code == 200
    assert response.json()["openapi"].startswith("3.")
