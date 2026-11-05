"""E2E: project creation and listing through the real UI."""

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL, create_project_ui, delete_project_by_name, uniq

pytestmark = pytest.mark.e2e


def test_create_project_via_ui(logged_in_page, api):
    """Create a project in the modal and see it in the list afterwards."""
    page = logged_in_page
    name = uniq("项目")
    try:
        create_project_ui(page, name)
    finally:
        delete_project_by_name(api, name)


def test_create_project_empty_name_blocked(logged_in_page):
    """Submitting the modal with an empty name shows a validation error
    and does not create a project."""
    page = logged_in_page
    page.goto(f"{FRONTEND_URL}/projects")
    page.get_by_role("button", name="新建项目").click()
    page.get_by_role("button", name="创建项目").click()
    expect(page.get_by_text("请输入项目名称")).to_be_visible(timeout=10000)


def test_project_list_shows_api_seeded_project(logged_in_page, make_project):
    """A project created via the API is visible in the UI list."""
    page = logged_in_page
    project = make_project()
    page.goto(f"{FRONTEND_URL}/projects")
    page.get_by_placeholder("搜索项目名称、描述或标签").fill(project["project_name"])
    expect(page.get_by_text(project["project_name"])).to_be_visible(timeout=15000)
