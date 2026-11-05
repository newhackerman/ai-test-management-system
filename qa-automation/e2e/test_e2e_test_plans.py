"""E2E: test-plan creation through the real UI."""

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, create_test_plan_ui, uniq

pytestmark = pytest.mark.e2e


def test_create_test_plan_via_ui(logged_in_page, make_project, api):
    """Fill the create page (project + name + type), save, and see the
    plan afterwards."""
    page = logged_in_page
    project = make_project()
    name = uniq("计划")
    try:
        create_test_plan_ui(page, name, project["project_name"])
    finally:
        resp = api.get("/api/v1/test-plans/", params={"project_id": project["id"]})
        if resp.status_code == 200:
            body = resp.json()
            rows = body if isinstance(body, list) else body.get("data", [])
            for row in rows:
                if row.get("plan_name") == name:
                    api.delete(f"/api/v1/test-plans/{row['id']}")


def test_create_test_plan_empty_name_blocked(logged_in_page, make_project):
    """Saving with an empty plan name shows the zod validation error."""
    page = logged_in_page
    make_project()
    page.goto(f"{FRONTEND_URL}/test-manager/test-plans/create")
    page.get_by_role("button", name="创建测试计划").click()
    expect(page.get_by_text("请输入计划名称")).to_be_visible(timeout=10000)
