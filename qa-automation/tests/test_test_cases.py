"""Test-case CRUD + validation tests."""
import pytest

import factories
from assertions import assert_envelope_ok, assert_status


@pytest.mark.crud
def test_create_test_case(api, make_case):
    case = make_case()
    assert case["id"] > 0
    assert case["case_code"].startswith("TC-")
    assert case["status"] in ("DRAFT", "REVIEW", "APPROVED", "ACTIVE")
    assert case["case_type"] == "FUNCTIONAL"


@pytest.mark.crud
def test_create_test_case_linked_to_requirement(api, project, make_requirement, make_case):
    req = make_requirement(project["id"])
    case = make_case(requirement_id=req["id"])
    assert case["requirement_id"] == req["id"]


@pytest.mark.crud
@pytest.mark.negative
def test_create_test_case_missing_title_returns_422(api):
    resp = api.post("/api/v1/test-cases/", json={"case_type": "FUNCTIONAL"})
    assert_status(resp, 422, "case missing title")


@pytest.mark.crud
@pytest.mark.negative
def test_create_test_case_invalid_type_returns_422(api):
    resp = api.post(
        "/api/v1/test-cases/",
        json=factories.test_case_payload(case_type="NOT_A_TYPE"),
    )
    assert_status(resp, 422, "case invalid type")


@pytest.mark.crud
def test_list_test_cases(api, make_case):
    case = make_case()
    resp = api.get("/api/v1/test-cases/")
    assert_status(resp, 200, "list cases")
    body = resp.json()
    items = body if isinstance(body, list) else body.get("data", body.get("test_cases", body.get("items", [])))
    assert any(c["id"] == case["id"] for c in items)


@pytest.mark.crud
def test_get_test_case_by_id(api, make_case):
    case = make_case()
    resp = api.get(f"/api/v1/test-cases/{case['id']}")
    assert_status(resp, 200, "get case")
    data = resp.json()
    got = data.get("data", data)
    assert got["id"] == case["id"]


@pytest.mark.crud
@pytest.mark.negative
def test_get_missing_test_case_returns_404(api):
    resp = api.get("/api/v1/test-cases/999999999")
    assert_status(resp, 404, "get missing case")


@pytest.mark.crud
def test_update_test_case(api, make_case):
    case = make_case()
    resp = api.put(
        f"/api/v1/test-cases/{case['id']}",
        json={"case_title": factories.uniq("QA用例改名"), "priority": "HIGH"},
    )
    assert_status(resp, 200, "update case")
    updated = assert_envelope_ok(resp, "data")
    assert updated["priority"] == "HIGH"


@pytest.mark.crud
def test_duplicate_test_case(api, make_case):
    case = make_case()
    # The endpoint requires a (free-form) JSON body; an empty object works.
    resp = api.post(f"/api/v1/test-cases/{case['id']}/duplicate", json={})
    assert_status(resp, 200, "duplicate case")
    dup = assert_envelope_ok(resp, "data")
    assert dup["id"] != case["id"]
    # The service prefixes the copy's title with "[复制] ".
    assert dup["case_title"] == f"[复制] {case['case_title']}"
    # cleanup the duplicate too
    api.delete(f"/api/v1/test-cases/{dup['id']}")


@pytest.mark.crud
def test_delete_test_case(api, make_case):
    case = make_case()
    resp = api.delete(f"/api/v1/test-cases/{case['id']}")
    assert_status(resp, 200, "delete case")
    resp = api.get(f"/api/v1/test-cases/{case['id']}")
    assert_status(resp, 404, "case gone after delete")
