"""Requirement CRUD + validation tests.

Note: the requirements create endpoint returns the plain requirement
object (no success envelope), unlike projects/test-cases.
"""
import pytest

import factories
from assertions import assert_status


@pytest.mark.crud
def test_create_requirement(api, project, make_requirement):
    req = make_requirement(project["id"])
    assert req["id"] > 0
    assert req["project_id"] == project["id"]
    assert req["status"] == "DRAFT"
    assert req["requirement_code"].startswith("REQ-")


@pytest.mark.crud
def test_create_requirement_with_optional_fields(api, project, make_requirement):
    req = make_requirement(
        project["id"],
        description="带验收标准的详细需求",
        acceptance_criteria="用户能成功登录",
        priority="HIGH",
        business_value="CORE",
        complexity="MEDIUM",
        estimated_effort=3,
    )
    assert req["acceptance_criteria"] == "用户能成功登录"
    assert req["priority"] == "HIGH"


@pytest.mark.crud
@pytest.mark.negative
def test_create_requirement_missing_title_returns_422(api, project):
    resp = api.post(
        "/api/v1/requirements/",
        json={"project_id": project["id"], "requirement_type": "FUNCTIONAL"},
    )
    assert_status(resp, 422, "requirement missing title")


@pytest.mark.crud
@pytest.mark.negative
def test_create_requirement_invalid_type_returns_422(api, project):
    resp = api.post(
        "/api/v1/requirements/",
        json=factories.requirement_payload(project["id"], requirement_type="WRONG"),
    )
    assert_status(resp, 422, "requirement invalid type")


@pytest.mark.crud
@pytest.mark.negative
def test_create_requirement_unknown_project(api):
    """A requirement must not be created for a project that does not exist.

    FAILS while the bug exists: the service does not validate project_id,
    so it returns 201 and leaves an orphan requirement behind.
    """
    resp = api.post(
        "/api/v1/requirements/",
        json=factories.requirement_payload(999999999),
    )
    if resp.status_code in (200, 201):
        # Bug path: clean up the orphan so it does not pollute later runs.
        rid = resp.json().get("id")
        if rid:
            api.delete(f"/api/v1/requirements/{rid}")
    assert resp.status_code in (400, 404, 422), (
        f"expected 400/404/422 for unknown project, got {resp.status_code}: {resp.text[:300]}"
    )


@pytest.mark.crud
def test_list_requirements_by_project(api, project, make_requirement):
    req = make_requirement(project["id"])
    resp = api.get(f"/api/v1/requirements/projects/{project['id']}")
    assert_status(resp, 200, "list requirements by project")
    body = resp.json()
    items = body if isinstance(body, list) else body.get("requirements", body.get("items", []))
    assert any(r["id"] == req["id"] for r in items)


@pytest.mark.crud
def test_get_requirement_by_id(api, project, make_requirement):
    req = make_requirement(project["id"])
    resp = api.get(f"/api/v1/requirements/{req['id']}")
    assert_status(resp, 200, "get requirement")
    assert resp.json()["id"] == req["id"]


@pytest.mark.crud
@pytest.mark.negative
def test_get_missing_requirement_returns_404(api):
    resp = api.get("/api/v1/requirements/999999999")
    assert_status(resp, 404, "get missing requirement")


@pytest.mark.crud
def test_update_requirement(api, project, make_requirement):
    req = make_requirement(project["id"])
    resp = api.put(
        f"/api/v1/requirements/{req['id']}",
        json={"title": factories.uniq("QA需求改名"), "priority": "HIGH"},
    )
    assert_status(resp, 200, "update requirement")
    body = resp.json()
    updated = body.get("requirement", body)
    assert updated["priority"] == "HIGH"


@pytest.mark.crud
def test_requirement_status_change(api, project, make_requirement):
    req = make_requirement(project["id"])
    resp = api.put(
        f"/api/v1/requirements/{req['id']}/status",
        json={"status": "PENDING_REVIEW"},
    )
    assert_status(resp, 200, "requirement status change")


@pytest.mark.crud
def test_requirement_statistics(api, project, make_requirement):
    make_requirement(project["id"])
    resp = api.get("/api/v1/requirements/statistics")
    assert_status(resp, 200, "requirement statistics")


@pytest.mark.crud
def test_delete_requirement(api, project, make_requirement):
    req = make_requirement(project["id"])
    resp = api.delete(f"/api/v1/requirements/{req['id']}")
    assert resp.status_code in (200, 204), (
        f"expected 200/204 on delete, got {resp.status_code}: {resp.text[:300]}"
    )
    resp = api.get(f"/api/v1/requirements/{req['id']}")
    assert_status(resp, 404, "requirement gone after delete")
