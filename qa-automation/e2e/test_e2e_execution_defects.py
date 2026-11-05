"""E2E: manual test execution and defect creation through the real UI."""

import pytest
from playwright.sync_api import expect

from e2e.helpers import (
    FRONTEND_URL,
    create_defect_ui,
    manual_execution_ui,
    uniq,
)

pytestmark = pytest.mark.e2e


def test_manual_execution_via_ui(logged_in_page, make_case, api):
    """Open the manual execution page for a seeded case, start it, mark
    the step passed, complete and save — the result is shown."""
    page = logged_in_page
    case = make_case()
    try:
        manual_execution_ui(page, case["id"], case["case_title"])
    finally:
        resp = api.get("/api/v1/test-executions/", params={"test_case_id": case["id"]})
        if resp.status_code == 200:
            body = resp.json()
            rows = body if isinstance(body, list) else body.get("data", [])
            for row in rows:
                api.delete(f"/api/v1/test-executions/{row['id']}")


def test_create_defect_via_ui(logged_in_page, make_project, api):
    """Create a defect in the dialog and see it in the list afterwards."""
    page = logged_in_page
    make_project()
    title = uniq("缺陷")
    try:
        create_defect_ui(page, title)
    finally:
        resp = api.get("/api/v1/defects/", params={"search": title})
        if resp.status_code == 200:
            body = resp.json()
            rows = body if isinstance(body, list) else body.get("data", [])
            for row in rows:
                if row.get("title") == title:
                    api.delete(f"/api/v1/defects/{row['id']}")


def test_create_defect_empty_title_blocked(logged_in_page, make_project):
    """Saving a defect with an empty title shows the inline error."""
    page = logged_in_page
    make_project()
    page.goto(f"{FRONTEND_URL}/test-manager/defects")
    page.get_by_role("button", name="创建缺陷").click()
    page.get_by_role("button", name="保存缺陷").click()
    expect(page.get_by_text("请输入缺陷标题")).to_be_visible(timeout=10000)
