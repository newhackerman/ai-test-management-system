"""E2E: login page and authentication flows in a real browser."""

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, login, logout

pytestmark = pytest.mark.e2e


def test_login_page_renders(page):
    """The login page shows username/password fields and a 登录 button."""
    page.goto(f"{FRONTEND_URL}/login")
    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.get_by_role("button", name="登录", exact=True)).to_be_visible()


def test_login_wrong_password_shows_error(page):
    """A wrong password keeps the user on /login and shows an error."""
    page.goto(f"{FRONTEND_URL}/login")
    page.locator("#username").fill("admin")
    page.locator("#password").fill("WrongPass123!")
    page.get_by_role("button", name="登录", exact=True).click()
    expect(page.get_by_text("用户名或密码错误")).to_be_visible(timeout=15000)
    assert "/login" in page.url


def test_login_success_shows_dashboard(page):
    """Logging in as admin lands on the dashboard with real metrics."""
    login(page)
    assert page.url.rstrip("/") == FRONTEND_URL
    expect(page.get_by_text("项目总数")).to_be_visible()
    # The sidebar navigation is rendered (proves the app shell loaded).
    expect(page.get_by_role("link", name="项目管理")).to_be_visible()


def test_unauthenticated_projects_redirects_to_login(page):
    """Visiting /projects without a session redirects to /login."""
    page.goto(f"{FRONTEND_URL}/projects")
    expect(page.locator("#username")).to_be_visible(timeout=15000)
    assert "/login" in page.url


def test_logout_returns_to_login(page):
    """After logout the login form is shown again and the token is gone."""
    login(page)
    logout(page)
    assert "/login" in page.url
    assert page.evaluate("localStorage.getItem('auth-access-token')") is None
