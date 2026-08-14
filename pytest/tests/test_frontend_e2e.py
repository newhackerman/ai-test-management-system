from __future__ import annotations

import pytest


pytestmark = [pytest.mark.e2e, pytest.mark.frontend]


def _launch_page(frontend_url: str):
    try:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
    except Exception as exc:
        pytest.skip(f"Playwright browser is not available in this environment: {exc}")

    page = browser.new_page()
    return playwright, browser, page


@pytest.mark.smoke
def test_login_page_renders_form(frontend_url: str) -> None:
    playwright, browser, page = _launch_page(frontend_url)
    try:
        page.goto(f"{frontend_url}/login", wait_until="networkidle", timeout=15000)

        assert page.locator("input").count() >= 2
        assert page.locator("input[type='password']").count() == 1
        assert page.locator("button").count() >= 1
    finally:
        browser.close()
        playwright.stop()


@pytest.mark.security
def test_login_page_rejects_invalid_credentials(frontend_url: str) -> None:
    playwright, browser, page = _launch_page(frontend_url)
    try:
        page.goto(f"{frontend_url}/login", wait_until="networkidle", timeout=15000)
        page.locator("input").nth(0).fill("not-a-real-user")
        page.locator("input[type='password']").fill("definitely-wrong")
        page.locator("button").first.click()
        page.wait_for_timeout(2500)

        assert page.url.rstrip("/") == f"{frontend_url}/login"
    finally:
        browser.close()
        playwright.stop()


def test_anonymous_dashboard_route_redirects_to_login(frontend_url: str) -> None:
    playwright, browser, page = _launch_page(frontend_url)
    try:
        page.goto(f"{frontend_url}/projects", wait_until="networkidle", timeout=15000)

        assert "/login" in page.url
    finally:
        browser.close()
        playwright.stop()
