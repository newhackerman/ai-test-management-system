from __future__ import annotations

from typing import Any, Callable

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]

PROJECT_ID = 1
TEST_PLAN_ID = 12
REQUIREMENT_ID = 17
TEST_CASE_ID = 178
DEFECT_ID = 14
DEFECT_EXECUTION_ID = 61
DEFECT_CASE_ID = 192


def _json_200(response: requests.Response, context: str) -> Any:
    assert response.status_code == 200, f"{context} returned {response.status_code}: {response.text[:300]}"
    assert response.headers.get("content-type", "").startswith("application/json")
    return response.json()


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "projects", "tasks", "risks", "meetings", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _items(value)
            if nested:
                return nested
    return []


def _find_item(items: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool], label: str) -> dict[str, Any]:
    for item in items:
        if predicate(item):
            return item
    pytest.fail(f"Required business record was not found: {label}")


def test_project_requirement_test_execution_report_business_chain_is_consistent(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    projects = _items(
        _json_200(
            authenticated_session.get(f"{base_url}/api/v1/projects", params={"page": 1, "size": 20}, timeout=15),
            "list projects",
        )
    )
    project = _find_item(projects, lambda item: item.get("id") == PROJECT_ID, f"project {PROJECT_ID}")
    assert project["project_code"]

    requirements = _items(
        _json_200(
            authenticated_session.get(
                f"{base_url}/api/v1/requirements/projects/{PROJECT_ID}",
                params={"skip": 0, "limit": 20},
                timeout=15,
            ),
            "list project requirements",
        )
    )
    requirement = _find_item(requirements, lambda item: item.get("id") == REQUIREMENT_ID, f"requirement {REQUIREMENT_ID}")
    assert requirement["project_id"] == PROJECT_ID

    plans = _items(
        _json_200(
            authenticated_session.get(
                f"{base_url}/api/v1/test-plans/",
                params={"project_id": PROJECT_ID, "page": 1, "page_size": 20},
                timeout=15,
            ),
            "list project test plans",
        )
    )
    plan = _find_item(plans, lambda item: item.get("id") == TEST_PLAN_ID, f"test plan {TEST_PLAN_ID}")
    assert plan["project_id"] == PROJECT_ID

    cases = _items(
        _json_200(
            authenticated_session.get(
                f"{base_url}/api/v1/test-cases/",
                params={"test_plan_id": TEST_PLAN_ID, "page": 1, "page_size": 50},
                timeout=15,
            ),
            "list test plan cases",
        )
    )
    test_case = _find_item(cases, lambda item: item.get("id") == TEST_CASE_ID, f"test case {TEST_CASE_ID}")
    assert test_case["test_plan_id"] == TEST_PLAN_ID
    assert test_case["requirement_id"] == REQUIREMENT_ID

    executions = _items(
        _json_200(
            authenticated_session.get(
                f"{base_url}/api/v1/test-executions/",
                params={"test_plan_id": TEST_PLAN_ID, "page": 1, "page_size": 50},
                timeout=15,
            ),
            "list test plan executions",
        )
    )
    execution = _find_item(executions, lambda item: item.get("test_case_id") == TEST_CASE_ID, "execution for test case")
    assert execution["test_plan_id"] == TEST_PLAN_ID

    reports = _items(
        _json_200(
            authenticated_session.get(
                f"{base_url}/api/v1/reports/unified",
                params={"test_plan_id": TEST_PLAN_ID, "page": 1, "page_size": 20},
                timeout=15,
            ),
            "list unified reports for test plan",
        )
    )
    report = _find_item(
        reports,
        lambda item: item.get("summary", {}).get("test_plan_id") == TEST_PLAN_ID,
        "unified report for test plan",
    )
    assert report["status"] == "completed"


def test_requirement_detail_history_and_dependencies_are_consistent(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    detail = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/requirements/{REQUIREMENT_ID}", timeout=15),
        "requirement detail",
    )
    assert detail["id"] == REQUIREMENT_ID
    assert detail["project_id"] == PROJECT_ID

    history = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/requirements/{REQUIREMENT_ID}/history", timeout=15),
        "requirement history",
    )
    assert history["requirement"]["id"] == REQUIREMENT_ID

    dependencies = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/requirements/{REQUIREMENT_ID}/dependencies", timeout=15),
        "requirement dependencies",
    )
    assert dependencies["requirement"]["id"] == REQUIREMENT_ID


def test_task_detail_and_dependency_chain_are_consistent(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    task_list = _items(
        _json_200(
            authenticated_session.get(f"{base_url}/api/v1/tasks", params={"page": 1, "size": 20}, timeout=15),
            "list tasks",
        )
    )
    task = _find_item(task_list, lambda item: bool(item.get("id")), "any task")
    task_id = task["id"]

    detail = _json_200(authenticated_session.get(f"{base_url}/api/v1/tasks/{task_id}", timeout=15), "task detail")
    assert detail["id"] == task_id
    assert detail["project_id"] == task["project_id"]

    dependencies = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/tasks/{task_id}/dependencies", timeout=15),
        "task dependencies",
    )
    assert dependencies["task_id"] == task_id
    assert isinstance(dependencies["dependency_chain"], list)


def test_risk_detail_analysis_alerts_and_trend_are_consistent(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    risks = _items(
        _json_200(
            authenticated_session.get(
                f"{base_url}/api/v1/risks/",
                params={"project_id": PROJECT_ID, "page": 1, "page_size": 20},
                timeout=15,
            ),
            "list project risks",
        )
    )
    risk = _find_item(risks, lambda item: bool(item.get("id")), "any project risk")
    assert risk["project_id"] == PROJECT_ID

    detail = _json_200(authenticated_session.get(f"{base_url}/api/v1/risks/{risk['id']}", timeout=15), "risk detail")
    assert detail["id"] == risk["id"]
    assert detail["project_id"] == PROJECT_ID

    analysis = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/risks/analysis/{PROJECT_ID}", timeout=15),
        "risk analysis",
    )
    assert analysis["project_id"] == PROJECT_ID

    alerts = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/risks/alerts/{PROJECT_ID}", params={"days": 7}, timeout=15),
        "risk alerts",
    )
    assert alerts["project_id"] == PROJECT_ID

    trend = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/risks/trend/{PROJECT_ID}", params={"days": 30}, timeout=15),
        "risk trend",
    )
    assert trend["project_id"] == PROJECT_ID


def test_defect_can_be_traced_back_to_execution_and_test_case(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    defect = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/defects/{DEFECT_ID}", timeout=15),
        "defect detail",
    )["data"]
    assert defect["id"] == DEFECT_ID
    assert defect["test_execution_id"] == DEFECT_EXECUTION_ID
    assert defect["test_case_id"] == DEFECT_CASE_ID

    execution = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/test-executions/{DEFECT_EXECUTION_ID}", timeout=15),
        "defect source execution",
    )["data"]
    assert execution["id"] == DEFECT_EXECUTION_ID
    assert execution["test_case_id"] == DEFECT_CASE_ID
    assert execution["execution_status"] == "FAILED"

    test_case = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/test-cases/{DEFECT_CASE_ID}", timeout=15),
        "defect source test case",
    )["data"]
    assert test_case["id"] == DEFECT_CASE_ID
    assert test_case["last_execution_status"] == "FAILED"


def test_execution_progress_business_view_is_available(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    executions = _items(
        _json_200(
            authenticated_session.get(
                f"{base_url}/api/v1/test-executions/",
                params={"test_plan_id": TEST_PLAN_ID, "page": 1, "page_size": 20},
                timeout=15,
            ),
            "list executions for progress check",
        )
    )
    execution = _find_item(executions, lambda item: bool(item.get("id")), "any execution")

    progress = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/test-executions/{execution['id']}/progress", timeout=15),
        "test execution progress",
    )
    assert progress["data"]["execution_id"] == execution["id"]


@pytest.mark.parametrize(
    "business_view",
    [
        pytest.param("participants", id="meeting_participants"),
        pytest.param("participants/statistics", id="meeting_participant_statistics"),
        pytest.param("status", id="meeting_status"),
        pytest.param("summary", id="meeting_summary"),
        pytest.param("minutes", id="meeting_minutes"),
    ],
)
def test_meeting_detail_business_views_are_available(
    authenticated_session: requests.Session,
    base_url: str,
    business_view: str,
) -> None:
    meetings = _items(
        _json_200(
            authenticated_session.get(f"{base_url}/api/v1/meetings/", params={"page": 1, "size": 20}, timeout=15),
            "list meetings",
        )
    )
    meeting = _find_item(meetings, lambda item: bool(item.get("id")), "any meeting")

    detail = _json_200(
        authenticated_session.get(f"{base_url}/api/v1/meetings/{meeting['id']}", timeout=15),
        "meeting detail",
    )
    assert detail["id"] == meeting["id"]

    _json_200(
        authenticated_session.get(f"{base_url}/api/v1/meetings/{meeting['id']}/{business_view}", timeout=15),
        f"meeting {business_view}",
    )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(f"/api/v1/meetings/projects/{PROJECT_ID}/meetings", id="project_meetings"),
        pytest.param(f"/api/v1/meetings/projects/{PROJECT_ID}/meeting-schedule", id="project_meeting_schedule"),
        pytest.param(f"/api/v1/meetings/projects/{PROJECT_ID}/meeting-statistics", id="project_meeting_statistics"),
    ],
)
def test_project_meeting_business_views_are_available(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    _json_200(authenticated_session.get(f"{base_url}{path}", timeout=15), path)
