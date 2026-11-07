"""Risk CRUD + validation + boundary tests."""
import pytest

import factories
from assertions import assert_status


@pytest.mark.crud
def test_create_risk(api, project, make_risk):
    risk = make_risk(project["id"])
    assert risk["id"] > 0
    assert risk["project_id"] == project["id"]
    assert risk["status"] == "IDENTIFIED"
    assert risk["risk_score"] is not None


@pytest.mark.crud
def test_create_risk_with_full_mitigation(api, project, make_risk):
    risk = make_risk(
        project["id"],
        mitigation_plan="增加测试人力，每日站会跟踪",
        contingency_plan="延期上线并通知干系人",
        target_resolution_date="2026-12-01",
    )
    assert risk["mitigation_plan"] == "增加测试人力，每日站会跟踪"


@pytest.mark.crud
@pytest.mark.negative
def test_create_risk_missing_required_returns_422(api, project):
    resp = api.post("/api/v1/risks/", json={"risk_name": "缺字段"})
    assert_status(resp, 422, "risk missing fields")


@pytest.mark.crud
@pytest.mark.negative
@pytest.mark.boundary
def test_create_risk_probability_above_one_returns_422(api, project):
    resp = api.post(
        "/api/v1/risks/",
        json=factories.risk_payload(project["id"], probability=1.5),
    )
    assert_status(resp, 422, "risk probability > 1")


@pytest.mark.crud
@pytest.mark.negative
@pytest.mark.boundary
def test_create_risk_probability_below_zero_returns_422(api, project):
    resp = api.post(
        "/api/v1/risks/",
        json=factories.risk_payload(project["id"], probability=-0.1),
    )
    assert_status(resp, 422, "risk probability < 0")


@pytest.mark.crud
@pytest.mark.negative
@pytest.mark.boundary
def test_create_risk_impact_score_above_ten_returns_422(api, project):
    resp = api.post(
        "/api/v1/risks/",
        json=factories.risk_payload(project["id"], impact_score=11),
    )
    assert_status(resp, 422, "risk impact_score > 10")


@pytest.mark.crud
@pytest.mark.negative
@pytest.mark.boundary
def test_create_risk_impact_score_zero_returns_422(api, project):
    resp = api.post(
        "/api/v1/risks/",
        json=factories.risk_payload(project["id"], impact_score=0),
    )
    assert_status(resp, 422, "risk impact_score = 0")


@pytest.mark.crud
@pytest.mark.boundary
def test_create_risk_probability_edges_accepted(api, project, make_risk):
    low = make_risk(project["id"], probability=0.0)
    assert float(low["probability"]) == 0.0
    high = make_risk(project["id"], probability=1.0)
    assert float(high["probability"]) == 1.0


@pytest.mark.crud
def test_list_risks(api, project, make_risk):
    risk = make_risk(project["id"])
    resp = api.get("/api/v1/risks/")
    assert_status(resp, 200, "list risks")
    body = resp.json()
    items = body if isinstance(body, list) else body.get("risks", body.get("items", []))
    assert any(r["id"] == risk["id"] for r in items)


@pytest.mark.crud
def test_get_risk_by_id(api, project, make_risk):
    risk = make_risk(project["id"])
    resp = api.get(f"/api/v1/risks/{risk['id']}")
    assert_status(resp, 200, "get risk")
    assert resp.json()["id"] == risk["id"]


@pytest.mark.crud
@pytest.mark.negative
def test_get_missing_risk_returns_404(api):
    resp = api.get("/api/v1/risks/999999999")
    assert_status(resp, 404, "get missing risk")


@pytest.mark.crud
def test_risk_analysis_endpoint(api, project, make_risk):
    make_risk(project["id"])
    resp = api.get(f"/api/v1/risks/analysis/{project['id']}")
    assert_status(resp, 200, "risk analysis")


@pytest.mark.crud
def test_risk_trend_endpoint(api, project, make_risk):
    make_risk(project["id"])
    resp = api.get(f"/api/v1/risks/trend/{project['id']}")
    assert_status(resp, 200, "risk trend")


@pytest.mark.crud
def test_delete_risk(api, project, make_risk):
    risk = make_risk(project["id"])
    resp = api.delete(f"/api/v1/risks/{risk['id']}")
    assert_status(resp, 200, "delete risk")
    resp = api.get(f"/api/v1/risks/{risk['id']}")
    assert_status(resp, 404, "risk gone after delete")
