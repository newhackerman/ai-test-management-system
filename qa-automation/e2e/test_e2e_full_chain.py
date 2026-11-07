"""E2E: the full business chain in one browser session.

login -> create project -> create requirement -> create test case ->
create test plan -> manual execution -> create defect -> logout.

Every step is done through the UI; only the final cleanup uses the API.
"""

import pytest
from playwright.sync_api import expect

from e2e.helpers import (
    FRONTEND_URL,
    create_defect_ui,
    create_project_ui,
    create_requirement_ui,
    create_test_case_ui,
    create_test_plan_ui,
    delete_project_by_name,
    login,
    logout,
    manual_execution_ui,
    uniq,
)

pytestmark = pytest.mark.e2e


def test_full_chain_via_ui(page, api):
    login(page)
    token = uniq("链路")
    project_name = f"{token}-项目"
    requirement_title = f"{token}-需求"
    case_title = f"{token}-用例"
    plan_name = f"{token}-计划"
    defect_title = f"{token}-缺陷"

    try:
        # 1. Project
        create_project_ui(page, project_name)
        # 2. Requirement (project selected explicitly in the dialog)
        create_requirement_ui(page, requirement_title, project_name)
        # 3. Test case
        create_test_case_ui(page, case_title)
        # The case detail page shows the case id in the URL.
        case_id = int(page.url.rstrip("/").rsplit("/", 1)[-1])
        # 4. Test plan
        create_test_plan_ui(page, plan_name, project_name)
        # 5. Manual execution of the case created in step 3
        manual_execution_ui(page, case_id, case_title)
        # 6. Defect
        create_defect_ui(page, defect_title)
        # 7. Dashboard still renders after the whole chain.
        page.goto(f"{FRONTEND_URL}/")
        expect(page.get_by_text("项目总数")).to_be_visible(timeout=15000)
        # 8. Logout
        logout(page)
    finally:
        delete_project_by_name(api, project_name)
