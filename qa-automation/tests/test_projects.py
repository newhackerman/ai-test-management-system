"""Project CRUD + validation + status flow tests."""
import pytest

import factories
from assertions import assert_envelope_ok, assert_status


@pytest.mark.crud
def test_create_project_returns_envelope_with_code(api, make_project):
    proj = make_project()
    assert proj["id"] > 0
    assert proj["project_code"].startswith("PROJ-")
    assert proj["status"] == "PLANNING"
    assert proj["health_score"] == 100
    assert proj["project_manager_id"] == 1


@pytest.mark.crud
def test_create_project_with_full_payload(api, make_project):
    proj = make_project(
        description="完整字段项目",
        priority="HIGH",
        test_manager_id=1,
        client_contact="张三 13800000000",
        budget=100000,
        tags=["qa", "smoke"],
    )
    assert proj["description"] == "完整字段项目"
    assert proj["priority"] == "HIGH"


@pytest.mark.crud
@pytest.mark.negative
def test_create_project_missing_required_returns_422(api):
    resp = api.post("/api/v1/projects", json={"project_name": "缺字段"})
    assert_status(resp, 422, "create project missing fields")


@pytest.mark.crud
@pytest.mark.negative
def test_create_project_invalid_type_returns_422(api):
    resp = api.post(
        "/api/v1/projects",
        json=factories.project_payload(project_type="NOT_A_TYPE"),
    )
    assert_status(resp, 422, "create project invalid type")


@pytest.mark.crud
@pytest.mark.negative
def test_create_project_empty_name_returns_422(api):
    resp = api.post("/api/v1/projects", json=factories.project_payload(project_name=""))
    assert resp.status_code in (400, 422), (
        f"expected 400/422 for empty name, got {resp.status_code}"
    )


@pytest.mark.crud
def test_list_projects_contains_created(api, make_project):
    proj = make_project()
    resp = api.get("/api/v1/projects")
    assert_status(resp, 200, "list projects")
    body = resp.json()
    assert body["total"] >= 1
    assert any(p["id"] == proj["id"] for p in body["projects"])


@pytest.mark.crud
def test_list_projects_pagination(api, make_project):
    make_project()
    make_project()
    resp = api.get("/api/v1/projects", params={"page": 1, "size": 1})
    assert_status(resp, 200, "list projects page 1")
    body = resp.json()
    assert body["page"] == 1
    assert body["size"] == 1
    assert len(body["projects"]) == 1
    assert body["total_pages"] >= 1


@pytest.mark.crud
def test_get_project_by_id(api, make_project):
    proj = make_project()
    resp = api.get(f"/api/v1/projects/{proj['id']}")
    assert_status(resp, 200, "get project")
    assert resp.json()["project_name"] == proj["project_name"]


@pytest.mark.crud
@pytest.mark.negative
def test_get_missing_project_returns_404(api):
    resp = api.get("/api/v1/projects/999999999")
    assert_status(resp, 404, "get missing project")


@pytest.mark.crud
def test_update_project(api, make_project):
    proj = make_project()
    new_name = factories.uniq("QA改名后")
    resp = api.put(
        f"/api/v1/projects/{proj['id']}",
        json={"project_name": new_name, "description": "已更新"},
    )
    updated = assert_envelope_ok(resp, "project")
    assert updated["project_name"] == new_name
    assert updated["description"] == "已更新"


@pytest.mark.crud
@pytest.mark.negative
def test_update_missing_project_returns_404(api):
    resp = api.put("/api/v1/projects/999999999", json={"project_name": "x"})
    assert_status(resp, 404, "update missing project")


@pytest.mark.crud
def test_project_status_transition_planning_to_in_progress(api, make_project):
    proj = make_project()
    resp = api.post(
        f"/api/v1/projects/{proj['id']}/status",
        params={"new_status": "IN_PROGRESS"},
    )
    assert_status(resp, 200, "status transition")
    assert resp.json()["project"]["status"] == "IN_PROGRESS"


@pytest.mark.crud
@pytest.mark.negative
def test_project_status_invalid_value_returns_422(api, make_project):
    proj = make_project()
    resp = api.post(
        f"/api/v1/projects/{proj['id']}/status",
        params={"new_status": "BOGUS"},
    )
    assert_status(resp, 422, "status invalid value")


@pytest.mark.crud
def test_project_statistics(api, make_project):
    make_project()
    resp = api.get("/api/v1/projects/statistics")
    data = assert_envelope_ok(resp, "data")
    assert data["total_projects"] >= 1
    assert "active_projects" in data


@pytest.mark.crud
def test_project_summary(api, make_project):
    proj = make_project()
    resp = api.get(f"/api/v1/projects/{proj['id']}/summary")
    assert_status(resp, 200, "project summary")
    assert resp.json()["id"] == proj["id"]


@pytest.mark.crud
def test_delete_project(api):
    resp = api.post("/api/v1/projects", json=factories.project_payload())
    proj = assert_envelope_ok(resp, "project")
    resp = api.delete(f"/api/v1/projects/{proj['id']}")
    assert_status(resp, 200, "delete project")
    resp = api.get(f"/api/v1/projects/{proj['id']}")
    assert_status(resp, 404, "project gone after delete")


@pytest.mark.crud
@pytest.mark.negative
def test_delete_missing_project_returns_404(api):
    resp = api.delete("/api/v1/projects/999999999")
    assert_status(resp, 404, "delete missing project")
