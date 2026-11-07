"""Shared helpers for the E2E suite: login/logout and navigation.

Adaptation points for a new project (all env-overridable):
  QA_LOGIN_PAGE       login page path, default /login
  QA_USER_SELECTOR    username input selector, default #username
  QA_PASS_SELECTOR    password input selector, default #password
  QA_LOGIN_BTN        login button text, default the local word for login
  QA_DASHBOARD_MARKER text visible only after login, e.g. a dashboard metric
  QA_LOGOUT_BTN       logout button text

Add one helper per UI creation flow of the new project, following the
pattern in login(): goto the page, fill the form, submit, then expect a
visible proof that the record persisted.
"""

import os
import uuid

from playwright.sync_api import expect

from config import ADMIN_PASSWORD, ADMIN_USER, FRONTEND_URL

LOGIN_PAGE = os.environ.get("QA_LOGIN_PAGE", "/login")
USER_SELECTOR = os.environ.get("QA_USER_SELECTOR", "#username")
PASS_SELECTOR = os.environ.get("QA_PASS_SELECTOR", "#password")
LOGIN_BTN = os.environ.get("QA_LOGIN_BTN", "登录")
DASHBOARD_MARKER = os.environ.get("QA_DASHBOARD_MARKER", "")
LOGOUT_BTN = os.environ.get("QA_LOGOUT_BTN", "退出")


def uniq(prefix: str) -> str:
    """Unique name prefix so parallel/sequential runs never collide."""
    return f"E2E-{prefix}-{uuid.uuid4().hex[:8]}"


def login(page, username: str | None = None, password: str | None = None):
    """Log in through the real login form and wait for the dashboard."""
    page.goto(f"{FRONTEND_URL}{LOGIN_PAGE}")
    page.locator(USER_SELECTOR).fill(username or ADMIN_USER)
    page.locator(PASS_SELECTOR).fill(password or ADMIN_PASSWORD)
    page.get_by_role("button", name=LOGIN_BTN, exact=True).click()
    if DASHBOARD_MARKER:
        expect(page.get_by_text(DASHBOARD_MARKER)).to_be_visible(timeout=20000)
    else:
        page.wait_for_url(f"{FRONTEND_URL}/*", timeout=20000)


def logout(page):
    """Click the header logout button and wait for the login form."""
    page.get_by_role("button", name=LOGOUT_BTN).click()
    expect(page.locator(USER_SELECTOR)).to_be_visible(timeout=15000)


def nav(page, label: str):
    """Navigate via the sidebar menu item."""
    page.get_by_role("link", name=label).first.click()
