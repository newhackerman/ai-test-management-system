"""Test-plan tests.

KNOWN ISSUE (found during framework probing, 2026-11-05): creating a test
plan WITHOUT test_manager_id returns HTTP 500 — the TestPlan model declares
test_manager_id NOT NULL while the API schema marks it optional.
`test_create_plan_without_manager_succeeds` encodes the correct behavior
and fails until the bug is fixed; `test_create_plan_with_manager` covers
the working path.
"""
import pytest

import factories
from assertions import assert_envelope_ok, assert_status


@pytest.mark.crud
def test_create_plan_with_manager(api, project, make_plan):
    plan = make_plan(project["id"], test_manager_id=1)
    assert plan["id"] > 0
    assert plan["plan_code"].startswith("TP-")
    assert plan["status"] == "DRAFT"
    assert plan["test_manager_id"] == 1


@pytest.mark.crud
def test_create_plan_without_manager_succeeds(api, project):
    """test_manager_id is optional in the API schema, so creating a plan
    without it must succeed (200) and leave the field null.

    FAILS while the bug exists: the TestPlan model declares test_manager_id
    NOT NULL, so the service raises IntegrityError -> HTTP 500.
    """
    resp = api.post(
        "/api/v1/test-plans/",
        json=factories.test_plan_payload(project["id"]),
    )
    plan = assert_envelope_ok(resp, "data")
    assert plan["id"] > 0
    assert plan["test_manager_id"] is None
    api.delete(f"/api/v1/test-plans/{plan['id']}")


@pytest.mark.crud
@pytest.mark.negative
def test_create_plan_missing_required_returns_422(api, project):
    resp = api.post("/api/v1/test-plans/", json={"project_id": project["id"]})
    assert_status(resp, 422, "plan missing fields")


@pytest.mark.crud
@pytest.mark.negative
def test_create_plan_invalid_type_returns_422(api, project):
    resp = api.post(
        "/api/v1/test-plans/",
        json=factories.test_plan_payload(project["id"], test_type="WRONG"),
    )
    assert_status(resp, 422, "plan invalid type")


@pytest.mark.crud
def test_list_test_plans(api, project, make_plan):
    plan = make_plan(project["id"], test_manager_id=1)
    resp = api.get("/api/v1/test-plans/")
    assert_status(resp, 200, "list plans")
    body = resp.json()
    items = body if isinstance(body, list) else body.get("data", body.get("test_plans", body.get("items", [])))
    assert any(p["id"] == plan["id"] for p in items)


@pytest.mark.crud
def test_get_test_plan_by_id(api, project, make_plan):
    plan = make_plan(project["id"], test_manager_id=1)
    resp = api.get(f"/api/v1/test-plans/{plan['id']}")
    assert_status(resp, 200, "get plan")
    data = resp.json()
    got = data.get("data", data)
    assert got["id"] == plan["id"]


@pytest.mark.crud
@pytest.mark.negative
def test_get_missing_plan_returns_404(api):
    resp = api.get("/api/v1/test-plans/999999999")
    assert_status(resp, 404, "get missing plan")


@pytest.mark.crud
def test_plan_progress_endpoint(api, project, make_plan):
    plan = make_plan(project["id"], test_manager_id=1)
    resp = api.get(f"/api/v1/test-plans/{plan['id']}/progress")
    assert_status(resp, 200, "plan progress")


@pytest.mark.crud
def test_plan_statistics_endpoint(api, project, make_plan):
    plan = make_plan(project["id"], test_manager_id=1)
    resp = api.get(f"/api/v1/test-plans/{plan['id']}/statistics")
    assert_status(resp, 200, "plan statistics")


@pytest.mark.crud
def test_delete_test_plan(api, project, make_plan):
    plan = make_plan(project["id"], test_manager_id=1)
    resp = api.delete(f"/api/v1/test-plans/{plan['id']}")
    assert_status(resp, 200, "delete plan")
    resp = api.get(f"/api/v1/test-plans/{plan['id']}")
    assert_status(resp, 404, "plan gone after delete")
