from __future__ import annotations

from urllib.parse import urljoin

import pytest
import requests
from bs4 import BeautifulSoup


pytestmark = [pytest.mark.live, pytest.mark.frontend]


SPA_ROUTES = [
    "/",
    "/login",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/profile",
    "/users",
    "/roles",
    "/roles/eight",
    "/projects",
    "/tasks",
    "/requirements",
    "/risks",
    "/ai-assistant",
    "/meetings",
    "/meetings/create",
    "/meetings/analytics/comparison",
    "/meetings/recordings",
    "/test-manager",
    "/test-manager/test-plans",
    "/test-manager/test-plans/create",
    "/test-manager/test-cases",
    "/test-manager/test-cases/create",
    "/test-manager/execution",
    "/test-manager/executions",
    "/test-manager/executions/manual",
    "/test-manager/executions/automation",
    "/test-manager/defects",
    "/test-manager/defects/analytics",
    "/test-manager/reports",
    "/test-manager/reports/generate",
    "/test-manager/performance",
    "/test-manager/security",
    "/reports",
    "/allure-reports",
    "/settings",
    "/statistics",
    "/config",
    "/config/groups",
    "/config/audits",
    "/auto-recovery",
]


def _get_frontend(session: requests.Session, frontend_url: str, path: str = "/") -> requests.Response:
    return session.get(
        urljoin(frontend_url + "/", path.lstrip("/")),
        headers={"Accept": "text/html,application/xhtml+xml"},
        timeout=10,
    )


@pytest.mark.smoke
def test_frontend_root_serves_vite_app(live_session: requests.Session, frontend_url: str) -> None:
    response = _get_frontend(live_session, frontend_url)
    soup = BeautifulSoup(response.text, "html.parser")

    assert response.status_code == 200
    assert soup.select_one("#root") is not None
    assert soup.select("script[type='module']"), "Vite module script should be present."


@pytest.mark.smoke
def test_frontend_static_assets_are_available(live_session: requests.Session, frontend_url: str) -> None:
    response = _get_frontend(live_session, frontend_url)
    soup = BeautifulSoup(response.text, "html.parser")
    asset_urls = [
        tag.get("src") or tag.get("href")
        for tag in soup.select("script[src], link[href]")
        if tag.get("src") or tag.get("href")
    ]

    assert asset_urls, "No frontend assets referenced by index.html."
    for asset_url in asset_urls[:10]:
        asset_response = live_session.get(
            urljoin(frontend_url + "/", asset_url.lstrip("/")),
            headers={"Accept": "*/*"},
            timeout=10,
        )
        assert asset_response.status_code == 200, f"Asset unavailable: {asset_url}"


@pytest.mark.parametrize("path", SPA_ROUTES)
def test_frontend_spa_routes_are_directly_reachable(
    live_session: requests.Session,
    frontend_url: str,
    path: str,
) -> None:
    response = _get_frontend(live_session, frontend_url, path)

    assert response.status_code == 200
    assert '<div id="root">' in response.text
