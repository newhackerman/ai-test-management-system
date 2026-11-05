"""Shared helpers for the E2E suite: login/logout, sidebar navigation,
and the UI creation flows used by the module tests and the full chain."""

import re
import uuid

from playwright.sync_api import expect

from config import ADMIN_PASSWORD, ADMIN_USER, FRONTEND_URL

FRONTEND_URL = FRONTEND_URL
ADMIN_USER = ADMIN_USER
ADMIN_PASSWORD = ADMIN_PASSWORD


def uniq(prefix: str) -> str:
    """Unique name prefix so parallel/sequential runs never collide."""
    return f"E2E-{prefix}-{uuid.uuid4().hex[:8]}"


def login(page, username: str | None = None, password: str | None = None):
    """Log in through the real login form and wait for the dashboard."""
    page.goto(f"{FRONTEND_URL}/login")
    page.locator("#username").fill(username or ADMIN_USER)
    page.locator("#password").fill(password or ADMIN_PASSWORD)
    page.get_by_role("button", name="登录", exact=True).click()
    # Dashboard renders the "项目总数" metric once the app shell loads.
    expect(page.get_by_text("项目总数")).to_be_visible(timeout=20000)


def logout(page):
    """Click the header 退出 button and wait for the login form."""
    page.get_by_role("button", name="退出").click()
    expect(page.locator("#username")).to_be_visible(timeout=15000)


def nav(page, label: str):
    """Navigate via the sidebar menu item."""
    page.get_by_role("link", name=label).first.click()


def create_project_ui(page, name: str, start: str = "2026-11-05", end: str = "2026-12-31"):
    """Create a project through the 新建项目 modal, then prove it is listed."""
    page.goto(f"{FRONTEND_URL}/projects")
    page.get_by_role("button", name="新建项目").click()
    page.get_by_placeholder("例如：支付链路回归测试").fill(name)
    page.locator("#planned_start_date").fill(start)
    page.locator("#planned_end_date").fill(end)
    page.get_by_role("button", name="创建项目").click()
    # The modal closes and the list refreshes; search to prove persistence.
    page.get_by_placeholder("搜索项目名称、描述或标签").fill(name)
    expect(page.get_by_text(name)).to_be_visible(timeout=15000)


def create_requirement_ui(page, title: str, project_name: str | None = None):
    """Create a requirement through the 新建需求 dialog.

    The project is selected explicitly in the dialog. (U7 fixed: if the
    dialog is opened before the project list loads, the first project is
    auto-filled once the list arrives instead of leaving project_id empty
    and blocking submit.)
    """
    page.goto(f"{FRONTEND_URL}/requirements")
    page.get_by_role("button", name="新建需求").click()
    if project_name:
        page.get_by_label("所属项目").select_option(label=project_name)
    page.get_by_placeholder("例如：用户可以按项目筛选需求").fill(title)
    page.get_by_role("button", name="保存", exact=True).click()
    # The list search only applies when 查询 is clicked.
    page.get_by_placeholder("搜索标题、编号、描述或验收标准").fill(title)
    page.get_by_role("button", name="查询").click()
    expect(page.get_by_text(title)).to_be_visible(timeout=15000)


def create_test_case_ui(page, title: str):
    """Create a test case on the dedicated create page."""
    page.goto(f"{FRONTEND_URL}/test-manager/test-cases/create")
    page.get_by_label("用例标题").fill(title)
    page.get_by_placeholder("例如：登录、订单、报表").fill("登录")
    page.get_by_placeholder("操作步骤").first.fill("打开登录页并输入账号密码")
    page.get_by_placeholder("该步骤预期结果").first.fill("登录成功进入仪表盘")
    page.get_by_role("button", name="保存测试用例").click()
    # After save the app navigates to the case detail page.
    expect(page.get_by_text(title)).to_be_visible(timeout=15000)


def create_test_plan_ui(page, name: str, project_name: str):
    """Create a test plan on the dedicated create page."""
    page.goto(f"{FRONTEND_URL}/test-manager/test-plans/create")
    name_input = page.get_by_placeholder("请输入测试计划名称")
    name_input.fill(name)
    expect(name_input).to_have_value(name)
    # The project field is a native <select> next to the "所属项目" label
    # (the label is not associated via `for`, so get_by_label can't find it).
    page.locator("label", has_text="所属项目").locator("..").locator("select").select_option(
        label=project_name
    )
    # Selecting the project re-renders the form; if the name was lost,
    # fill it again before submitting (seen once as an empty-name
    # validation failure in the full-chain test).
    if name_input.input_value() != name:
        name_input.fill(name)
        expect(name_input).to_have_value(name)
    # Test type defaults to 功能测试 (FUNCTIONAL); the placeholder
    # "请选择测试类型" never renders, so there is nothing to pick.
    page.get_by_role("button", name="创建测试计划").click()
    expect(page.get_by_text(name)).to_be_visible(timeout=15000)


def manual_execution_ui(page, case_id: int, case_title: str):
    """Run a manual execution for a case: start, mark the step passed,
    complete and save — then prove the result is shown."""
    page.goto(f"{FRONTEND_URL}/test-manager/executions/manual/{case_id}")
    expect(page.get_by_text(case_title)).to_be_visible(timeout=15000)
    page.get_by_role("button", name="开始执行").click()
    page.locator("button[title='通过']").first.click()
    page.get_by_role("button", name="完成并保存").click()
    # The page then shows the recorded summary, e.g. "已记录 1 / 3，通过 1，失败 0".
    expect(page.get_by_text(re.compile(r"已记录 \d+ / \d+，通过 [1-9]"))).to_be_visible(
        timeout=15000
    )


def create_defect_ui(page, title: str):
    """Create a defect through the 创建缺陷 dialog."""
    page.goto(f"{FRONTEND_URL}/test-manager/defects")
    page.get_by_role("button", name="创建缺陷").click()
    page.get_by_label("缺陷标题").fill(title)
    # The form requires a description too (empty description blocks submit).
    page.get_by_label("缺陷描述").fill(f"{title}：登录后页面空白，复现步骤见详情。")
    page.get_by_role("button", name="保存缺陷").click()
    page.get_by_placeholder("搜索缺陷标题、描述或编号").fill(title)
    expect(page.get_by_text(title)).to_be_visible(timeout=15000)


def delete_project_by_name(api, name: str):
    """Best-effort cleanup of a UI-created project (children are deleted
    first, since this deployment runs without FK cascades)."""
    resp = api.get("/api/v1/projects", params={"search": name})
    items = resp.json().get("projects", []) if resp.status_code == 200 else []
    for project in items:
        if project.get("project_name") != name:
            continue
        pid = project["id"]
        # Delete children that reference the project.
        for path, key in (
            ("/api/v1/defects/", "defects"),
            ("/api/v1/test-plans/", "test_plans"),
            ("/api/v1/requirements/", "requirements"),
        ):
            r = api.get(path, params={"project_id": pid})
            if r.status_code == 200:
                body = r.json()
                rows = body if isinstance(body, list) else body.get("data", body.get(key, []))
                for row in rows:
                    api.delete(f"{path.rstrip('/')}/{row['id']}")
        r = api.get("/api/v1/test-cases/", params={"project_id": pid})
        if r.status_code == 200:
            body = r.json()
            rows = body if isinstance(body, list) else body.get("data", [])
            for row in rows:
                api.delete(f"/api/v1/test-cases/{row['id']}")
        api.delete(f"/api/v1/projects/{pid}")
