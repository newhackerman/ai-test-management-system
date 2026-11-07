"""E2E: U7 — the requirement dialog must backfill its project once the
project list arrives.

Repro: delay the projects list response, open 新建需求 while it is still
in flight (the form snapshots projects[0] as '' at open time), then let
the response through. Before the fix the select stayed empty and submit
was blocked by "请选择所属项目" forever; after the fix the first project
is auto-filled and the requirement can be saved.
"""

import time

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, uniq

pytestmark = pytest.mark.e2e


def test_requirement_dialog_backfills_project_after_list_loads(
    logged_in_page, make_project, api
):
    page = logged_in_page
    project = make_project()
    title = uniq("需求")

    delayed = {"count": 0}

    def delay_first_projects(route):
        delayed["count"] += 1
        if delayed["count"] == 1:
            time.sleep(6)
        route.continue_()

    page.route("**/api/v1/projects*", delay_first_projects)
    try:
        page.goto(f"{FRONTEND_URL}/requirements")
        page.get_by_role("button", name="新建需求").click()
        project_select = page.get_by_label("所属项目")
        expect(project_select).to_be_visible(timeout=10000)
        # Race reproduced: the dialog opened before the list arrived.
        expect(project_select).to_have_value("")
        # Once the list arrives, the first project must be auto-filled.
        # option[0] is the "请选择项目" placeholder; option[1] is the
        # first real project.
        options = project_select.locator("option")
        expect(options.nth(1)).to_be_attached(timeout=15000)
        first_value = options.nth(1).get_attribute("value")
        expect(project_select).to_have_value(first_value, timeout=10000)
        # And the requirement can now be saved (previously blocked).
        page.get_by_placeholder("例如：用户可以按项目筛选需求").fill(title)
        page.get_by_role("button", name="保存", exact=True).click()
        page.get_by_placeholder("搜索标题、编号、描述或验收标准").fill(title)
        page.get_by_role("button", name="查询").click()
        expect(page.get_by_text(title)).to_be_visible(timeout=15000)
    finally:
        page.unroute("**/api/v1/projects*")
        resp = api.get("/api/v1/requirements/", params={"project_id": project["id"]})
        if resp.status_code == 200:
            body = resp.json()
            rows = body if isinstance(body, list) else body.get("data", [])
            for row in rows:
                if row.get("title") == title:
                    api.delete(f"/api/v1/requirements/{row['id']}")
