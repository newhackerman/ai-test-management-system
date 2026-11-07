"""E2E: round-6 item 4 — traceability views render real backend data.

Seeds a project + requirement + test case + traceability link via API,
then drives the real /requirements page: select the project in the
filter, switch to the 追溯分析 view, and assert the seeded requirement
code, a real link cell (green dot) and 100% coverage render.

Item 5 (recording pause) has no UI control that renders a pause button
(only useRecording.ts + a local-only store flip), so it is covered at
API level in tests/test_round6_items.py instead of a click-through test.
"""

import pytest
from playwright.sync_api import expect

from e2e.helpers import FRONTEND_URL

pytestmark = pytest.mark.e2e


def _seed_traceability(api, make_project, make_requirement, make_case):
    """Project + requirement + case + TESTS link; returns (project, req)."""
    project = make_project()
    req = make_requirement(project["id"])
    case = make_case(requirement_id=req["id"])
    link = api.post(
        "/api/v1/requirement-traceability/links",
        json={
            "source_type": "requirement",
            "source_id": req["id"],
            "target_type": "test_case",
            "target_id": case["id"],
            "link_type": "TESTS",
            "description": "round6 e2e seed",
        },
    )
    assert link.status_code in (200, 201), link.text[:300]
    return project, req


def _open_traceability_view(page, project):
    page.goto(f"{FRONTEND_URL}/requirements")
    page.locator("select:has(option:text('全部项目'))").first.select_option(
        label=project["project_name"]
    )
    page.get_by_role("button", name="追溯分析").click()


def test_traceability_matrix_shows_real_link(
    logged_in_page, api, make_project, make_requirement, make_case
):
    """Seeded requirement code renders in the matrix with a green link cell."""
    page = logged_in_page
    project, req = _seed_traceability(api, make_project, make_requirement, make_case)
    _open_traceability_view(page, project)
    # Matrix view is behind a toggle; the component defaults to list view.
    page.get_by_role("button", name="矩阵视图").click()
    expect(page.get_by_text("追溯矩阵")).to_be_visible(timeout=15000)
    req_code = req.get("requirement_code") or f"REQ-{req['id']}"
    expect(page.get_by_text(req_code)).to_be_visible(timeout=15000)
    # Green dot = matrixData[req][case] is true: the seeded link really loaded.
    expect(page.locator(".bg-green-500").first).to_be_visible(timeout=15000)


def test_traceability_coverage_shows_real_rate(
    logged_in_page, api, make_project, make_requirement, make_case
):
    """1/1 requirements covered: the coverage panel shows 100% from the API."""
    page = logged_in_page
    project, _req = _seed_traceability(api, make_project, make_requirement, make_case)
    _open_traceability_view(page, project)
    expect(page.get_by_text("前向追溯覆盖率")).to_be_visible(timeout=15000)
    expect(page.get_by_text("100%", exact=True).first).to_be_visible(timeout=15000)
