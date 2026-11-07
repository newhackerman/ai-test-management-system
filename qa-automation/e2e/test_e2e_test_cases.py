"""E2E: test-case creation through the real UI."""

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, create_test_case_ui, uniq

pytestmark = pytest.mark.e2e


def test_create_test_case_via_ui(logged_in_page, api):
    """Fill the create page, save, and land on the case detail page
    showing the new title."""
    page = logged_in_page
    title = uniq("用例")
    try:
        create_test_case_ui(page, title)
        assert "/test-manager/test-cases/" in page.url
    finally:
        resp = api.get("/api/v1/test-cases/", params={"search": title})
        if resp.status_code == 200:
            body = resp.json()
            rows = body if isinstance(body, list) else body.get("data", [])
            for row in rows:
                if row.get("case_title") == title:
                    api.delete(f"/api/v1/test-cases/{row['id']}")


def test_create_test_case_empty_title_blocked(logged_in_page):
    """Saving with an empty title is blocked: the title input is natively
    `required`, so the browser refuses to submit and the page stays on
    the create form (no React error text is shown in this path)."""
    page = logged_in_page
    page.goto(f"{FRONTEND_URL}/test-manager/test-cases/create")
    page.get_by_role("button", name="保存测试用例").click()
    page.wait_for_timeout(1500)
    assert "/test-manager/test-cases/create" in page.url
    expect(page.get_by_role("button", name="保存测试用例")).to_be_visible()


def test_create_test_case_without_steps_blocked(logged_in_page, api):
    """A title but no filled step is blocked the same way: the step
    textareas are natively `required`, so nothing is submitted and no
    case is created."""
    page = logged_in_page
    title = uniq("用例")
    page.goto(f"{FRONTEND_URL}/test-manager/test-cases/create")
    page.get_by_label("用例标题").fill(title)
    page.get_by_role("button", name="保存测试用例").click()
    page.wait_for_timeout(1500)
    assert "/test-manager/test-cases/create" in page.url
    resp = api.get("/api/v1/test-cases/", params={"search": title})
    rows = []
    if resp.status_code == 200:
        body = resp.json()
        rows = body if isinstance(body, list) else body.get("data", [])
    assert not [r for r in rows if r.get("case_title") == title]
