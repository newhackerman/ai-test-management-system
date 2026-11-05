"""E2E security: a stored-XSS payload must render as inert text in the
browser, never execute.

A project whose name/description contains a classic XSS payload is
created via the API; the projects page is then opened in a real browser
with a dialog listener attached. If the payload executed, an alert
dialog would appear (and the test fails). React escapes interpolated
text by default, so the payload must show up as literal text.
"""

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, uniq

pytestmark = pytest.mark.e2e

XSS_TITLE = "<img src=x onerror=alert('E2E-XSS')>"


def test_stored_xss_does_not_execute(logged_in_page, api):
    page = logged_in_page
    dialogs = []
    page.on("dialog", lambda d: dialogs.append(d.message()))

    title = f"{uniq('XSS')}-{XSS_TITLE}"
    resp = api.post(
        "/api/v1/projects",
        json={
            "project_name": title,
            "project_type": "BUSINESS_SYSTEM",
            "priority": "HIGH",
            "project_manager_id": 1,
            "planned_start_date": "2026-11-05",
            "planned_end_date": "2026-12-31",
        },
    )
    assert resp.status_code in (200, 201)
    project_id = resp.json().get("project", resp.json())["id"]
    try:
        page.goto(f"{FRONTEND_URL}/projects")
        page.get_by_placeholder("搜索项目名称、描述或标签").fill("XSS")
        page.wait_for_timeout(2000)
        # The payload must render as literal text, not as an element.
        # (The title appears twice on the page — card title plus the
        # bare payload string — so use .first; strict mode would
        # otherwise fail on the duplicate text match.)
        expect(page.get_by_text(XSS_TITLE, exact=False).first).to_be_visible(timeout=15000)
        assert not dialogs, f"XSS executed, dialogs: {dialogs}"
        assert page.locator("img[src='x']").count() == 0
    finally:
        api.delete(f"/api/v1/projects/{project_id}")
