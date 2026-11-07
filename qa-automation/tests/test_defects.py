"""Defect CRUD + lifecycle tests."""
import pytest

import factories
from assertions import assert_envelope_ok, assert_status


@pytest.mark.crud
def test_create_defect(api, make_defect):
    defect = make_defect()
    assert defect["id"] > 0
    assert defect["defect_code"].startswith("BUG-")
    assert defect["status"] == "NEW"
    assert defect["severity"] == "MEDIUM"


@pytest.mark.crud
def test_create_defect_linked_to_case(api, make_case, make_defect):
    case = make_case()
    defect = make_defect(test_case_id=case["id"])
    assert defect["test_case_id"] == case["id"]


@pytest.mark.crud
@pytest.mark.negative
def test_create_defect_missing_title_returns_422(api):
    resp = api.post(
        "/api/v1/defects/",
        json={"description": "d", "defect_type": "FUNCTIONAL",
              "severity": "MEDIUM", "priority": "MEDIUM"},
    )
    assert_status(resp, 422, "defect missing title")


@pytest.mark.crud
@pytest.mark.negative
def test_create_defect_invalid_severity_returns_422(api):
    resp = api.post(
        "/api/v1/defects/",
        json=factories.defect_payload(severity="CATASTROPHIC"),
    )
    assert_status(resp, 422, "defect invalid severity")


@pytest.mark.crud
@pytest.mark.negative
def test_create_defect_missing_severity_returns_422(api):
    payload = factories.defect_payload()
    payload.pop("severity")
    resp = api.post("/api/v1/defects/", json=payload)
    assert_status(resp, 422, "defect missing severity")


@pytest.mark.crud
def test_list_defects(api, make_defect):
    defect = make_defect()
    resp = api.get("/api/v1/defects/")
    assert_status(resp, 200, "list defects")
    body = resp.json()
    items = body if isinstance(body, list) else body.get("data", body.get("defects", body.get("items", [])))
    assert any(d["id"] == defect["id"] for d in items)


@pytest.mark.crud
def test_get_defect_by_id(api, make_defect):
    defect = make_defect()
    resp = api.get(f"/api/v1/defects/{defect['id']}")
    assert_status(resp, 200, "get defect")
    data = resp.json()
    got = data.get("data", data)
    assert got["id"] == defect["id"]


@pytest.mark.crud
@pytest.mark.negative
def test_get_missing_defect_returns_404(api):
    resp = api.get("/api/v1/defects/999999999")
    assert_status(resp, 404, "get missing defect")


@pytest.mark.crud
def test_update_defect_status(api, make_defect):
    defect = make_defect()
    resp = api.patch(
        f"/api/v1/defects/{defect['id']}/status",
        json={"status": "ASSIGNED"},
    )
    assert_status(resp, 200, "defect status change")


@pytest.mark.crud
def test_add_and_list_defect_comments(api, make_defect):
    defect = make_defect()
    resp = api.post(
        f"/api/v1/defects/{defect['id']}/comments",
        json={"content": "已复现，正在定位原因"},
    )
    assert resp.status_code in (200, 201), (
        f"add defect comment: expected 200/201, got {resp.status_code}: {resp.text[:300]}"
    )
    resp = api.get(f"/api/v1/defects/{defect['id']}/comments")
    assert_status(resp, 200, "list defect comments")


@pytest.mark.crud
def test_defect_statistics(api, make_defect):
    make_defect()
    resp = api.get("/api/v1/defects/statistics/summary")
    assert_status(resp, 200, "defect statistics summary")


@pytest.mark.crud
def test_delete_defect(api, make_defect):
    defect = make_defect()
    resp = api.delete(f"/api/v1/defects/{defect['id']}")
    assert_status(resp, 200, "delete defect")
    resp = api.get(f"/api/v1/defects/{defect['id']}")
    assert_status(resp, 404, "defect gone after delete")
