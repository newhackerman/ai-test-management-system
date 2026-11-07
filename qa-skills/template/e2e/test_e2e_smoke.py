"""E2E smoke: the login page renders and a real login works."""
import pytest
from playwright.sync_api import expect

from config import FRONTEND_URL
from e2e.helpers import LOGIN_PAGE, USER_SELECTOR, login, logout


@pytest.mark.e2e
def test_login_page_renders(page):
    page.goto(f"{FRONTEND_URL}{LOGIN_PAGE}")
    expect(page.locator(USER_SELECTOR)).to_be_visible(timeout=15000)


@pytest.mark.e2e
def test_login_succeeds(logged_in_page):
    expect(logged_in_page.locator(USER_SELECTOR)).to_be_hidden(timeout=5000)


@pytest.mark.e2e
def test_logout_returns_to_login(logged_in_page):
    logout(logged_in_page)
    expect(logged_in_page.locator(USER_SELECTOR)).to_be_visible(timeout=15000)
