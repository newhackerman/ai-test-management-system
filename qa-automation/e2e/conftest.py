"""Playwright fixtures for the E2E suite.

A fresh Chromium (headless) browser context per test, so logins and
localStorage never leak between tests.
"""

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def pw():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture()
def browser(pw):
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture()
def page(browser):
    # accept_downloads lets tests prove a download button actually
    # downloads (a visible button that does nothing is a real defect
    # class — see the 2026-11-07 report download bug).
    context = browser.new_context(
        viewport={"width": 1440, "height": 900}, accept_downloads=True
    )
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture()
def logged_in_page(page):
    """A page already logged in as admin, on the dashboard."""
    from e2e.helpers import login

    login(page)
    return page
