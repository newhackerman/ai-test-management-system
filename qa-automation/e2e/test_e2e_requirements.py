"""E2E: requirement creation through the real UI."""

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, create_requirement_ui, uniq

pytestmark = pytest.mark.e2e


def test_create_requirement_via_ui(logged_in_page, make_project, api):
    """Seed a project via API, create a requirement in the dialog, and see
    it in the list afterwards."""
    page = logged_in_page
    project = make_project()
    title = uniq("需求")
    try:
        create_requirement_ui(page, title, project["project_name"])
    finally:
        resp = api.get("/api/v1/requirements/", params={"project_id": project["id"]})
        if resp.status_code == 200:
            body = resp.json()
            rows = body if isinstance(body, list) else body.get("data", [])
            for row in rows:
                if row.get("title") == title:
                    api.delete(f"/api/v1/requirements/{row['id']}")


def test_create_requirement_empty_title_blocked(logged_in_page, make_project):
    """Submitting the dialog with an empty title shows the validation error
    (project is selected first so the title check is the one that fires)."""
    page = logged_in_page
    project = make_project()
    page.goto(f"{FRONTEND_URL}/requirements")
    page.get_by_role("button", name="新建需求").click()
    page.get_by_label("所属项目").select_option(label=project["project_name"])
    page.get_by_role("button", name="保存", exact=True).click()
    expect(page.get_by_text("请填写需求标题")).to_be_visible(timeout=10000)
