"""Page tour: log in and open every page, like a user would.

Added 2026-11-07 after the user found two bugs by simply logging in
and clicking around (AI assistant AttributeError, dead report download)
while the suite was green at 302/302: most pages had never been opened
by a test at all. This tour visits every static route in
``page_tour_routes.TOUR_ROUTES`` and proves each one renders — no white
screen, no error boundary, no console errors, no failed API calls.

The route list lives in ``page_tour_routes.py``; the guard in
``tests/test_route_coverage.py`` fails the suite if a route is added to
the app without landing in a coverage bucket.
"""

import pytest
from playwright.sync_api import expect

from e2e.helpers import assert_page_renders
from e2e.page_tour_routes import TOUR_ROUTES


@pytest.mark.e2e
@pytest.mark.parametrize("path,label,marker", TOUR_ROUTES, ids=[p for p, _, _ in TOUR_ROUTES])
def test_page_tour_renders(logged_in_page, path, label, marker):
    """Every sidebar page must render without errors."""
    assert_page_renders(logged_in_page, path, marker=marker)


@pytest.mark.e2e
def test_page_tour_primary_buttons_do_something(logged_in_page):
    """Spot-check: the main action on key list pages must react.

    This is the failure mode the tour's render checks cannot see — a
    button that is visible but does nothing when clicked (the report
    download bug). The download button itself is covered by the report
    fix's own verification; here we check the create/entry actions.
    """
    page = logged_in_page

    # Projects: 新建项目 opens the create modal.
    assert_page_renders(page, "/projects")
    page.get_by_role("button", name="新建项目").click()
    expect(page.get_by_placeholder("例如：支付链路回归测试")).to_be_visible(timeout=10000)
    page.keyboard.press("Escape")

    # Test plans: the create page loads (the full create flow is covered
    # elsewhere; here we only prove the entry point works).
    assert_page_renders(page, "/test-manager/test-plans")
    page.get_by_role("button", name="创建测试计划").first.click()
    expect(page.get_by_placeholder("请输入测试计划名称")).to_be_visible(timeout=10000)

    # Reports: the list renders and the first row's preview opens the
    # detail dialog; its 下载 button must actually download a file.
    # (The 2026-11-07 user-reported bug was a button that did nothing;
    # the custom Dialog has no role="dialog", so the modal is located
    # by its overlay container, not by role.)
    assert_page_renders(page, "/test-manager/reports")
    page.locator("button[title='预览']").first.click()
    modal = page.locator("div.fixed.inset-0.z-50").first
    expect(modal).to_be_visible(timeout=10000)
    with page.expect_download(timeout=15000) as dl_info:
        modal.get_by_role("button", name="下载").click()
    download = dl_info.value
    assert download.suggested_filename, "download produced no file"
