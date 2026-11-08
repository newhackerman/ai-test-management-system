"""Shared helpers for the E2E suite: login/logout and navigation.

Adaptation points for a new project (all env-overridable):
  QA_LOGIN_PAGE       login page path, default /login
  QA_USER_SELECTOR    username input selector, default #username
  QA_PASS_SELECTOR    password input selector, default #password
  QA_LOGIN_BTN        login button text, default the local word for login
  QA_DASHBOARD_MARKER text visible only after login, e.g. a dashboard metric
  QA_LOGOUT_BTN       logout button text
  QA_APP_ROOT         frontend app container selector, default #root
                      (React). Vue apps use #app; Angular apps use
                      app-root. Set it per project, never hard-code it.

Add one helper per UI creation flow of the new project, following the
pattern in login(): goto the page, fill the form, submit, then expect a
visible proof that the record persisted.
"""

import os
import uuid

from playwright.sync_api import expect

from config import ADMIN_PASSWORD, ADMIN_USER, APP_ROOT, FRONTEND_URL

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


class PageErrorCollector:
    """Collect page errors while a page loads.

    Captures uncaught page exceptions, console errors and failed API
    responses — the three things an HTTP-status-only check misses.
    Attach before ``goto``; read ``.problems`` after the page settles.
    """

    def __init__(self, page):
        self.page = page
        self.page_errors: list[str] = []
        self.console_errors: list[str] = []
        self.failed_responses: list[str] = []

    def __enter__(self):
        def _on_pageerror(err):
            self.page_errors.append(str(err))

        def _on_console(msg):
            if msg.type == "error" and not any(
                ignored in msg.text for ignored in IGNORED_CONSOLE_ERRORS
            ):
                self.console_errors.append(msg.text)

        def _on_response(resp):
            if resp.status >= 400 and "/api/" in resp.url:
                self.failed_responses.append(f"{resp.status} {resp.url}")

        self._handlers = {
            "pageerror": _on_pageerror,
            "console": _on_console,
            "response": _on_response,
        }
        for event, handler in self._handlers.items():
            self.page.on(event, handler)
        return self

    def __exit__(self, *args):
        for event, handler in self._handlers.items():
            self.page.remove_listener(event, handler)
        return False

    @property
    def problems(self) -> list[str]:
        out = [f"pageerror: {e}" for e in self.page_errors]
        out += [f"console error: {e}" for e in self.console_errors]
        out += [f"failed API response: {e}" for e in self.failed_responses]
        return out


# Console errors that are known-benign and must not fail a page.
# Example: the antd static-message warning, logged as console.error
# on pages using message.* without the App wrapper — a dev-mode
# warning, not a functional failure. Add entries only with a reason.
IGNORED_CONSOLE_ERRORS = (
    "[antd: message] Static function can not consume context",
)

# Text that must never appear in a rendered page. Override with
# QA_FAILURE_MARKERS (comma-separated) when the app's own wording differs.
FAILURE_MARKERS = tuple(
    m.strip()
    for m in os.environ.get(
        "QA_FAILURE_MARKERS", "Something went wrong,Failed to fetch,Network Error"
    ).split(",")
    if m.strip()
)

# A page is "blank" below this many body characters. The app shell
# (sidebar + header) alone is ~150 chars, so 100 still catches a
# white screen (~0-20 chars) while allowing legitimately sparse
# pages such as an empty list.
BLANK_THRESHOLD = 100


def assert_page_renders(page, path: str, marker: str | None = None, timeout: int = 20000):
    """Navigate to ``path`` and prove the page actually rendered.

    Fails on: uncaught page exceptions, console errors, failed API
    responses (>= 400), failure-marker text, or a (near-)blank page.
    ``marker`` is page text that must be visible once loaded.
    """
    with PageErrorCollector(page) as collector:
        page.goto(f"{FRONTEND_URL}{path}")
        page.wait_for_load_state("load", timeout=timeout)
        expect(page.locator(APP_ROOT)).to_be_visible(timeout=timeout)
        if marker:
            expect(page.get_by_text(marker).first).to_be_visible(timeout=timeout)
        else:
            page.wait_for_timeout(1500)
        body_text = page.locator("body").inner_text()
        assert len(body_text.strip()) > BLANK_THRESHOLD, (
            f"{path}: page looks blank ({len(body_text.strip())} chars of body text)"
        )
        for bad in FAILURE_MARKERS:
            assert bad not in body_text, f"{path}: page shows failure text {bad!r}"
        problems = collector.problems
        assert not problems, f"{path}: page errors:\n" + "\n".join(problems)
