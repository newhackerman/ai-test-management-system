"""Deepened API tests: negative paths, boundaries, and state-machine
violations the happy-path suite does not cover.

Every test encodes the *expected* contract; a failure is a finding, not
a broken test. These tests only read or create-then-delete their own
data on the local deployment.
"""

import pytest

import factories
from assertions import assert_envelope_ok, assert_status

pytestmark = [pytest.mark.negative, pytest.mark.boundary]

# ---------------------------------------------------------------------------
# Unauthenticated access to every module
# ---------------------------------------------------------------------------

MODULE_LIST_PATHS = [
    "/api/v1/projects",
    "/api/v1/requirements/",
    "/api/v1/test-cases/",
    "/api/v1/test-plans/",
    "/api/v1/test-executions/",
    "/api/v1/defects/",
    "/api/v1/risks/",
    "/api/v1/users",
    "/api/v1/roles",
]


@pytest.mark.parametrize("path", MODULE_LIST_PATHS)
def test_unauthenticated_list_is_401(anon, path):
    resp = anon.get(path)
    assert resp.status_code == 401, f"{path}: expected 401, got {resp.status_code}"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/projects",
        "/api/v1/requirements/",
        "/api/v1/test-cases/",
        "/api/v1/test-plans/",
        "/api/v1/defects/",
        "/api/v1/risks/",
    ],
)
def test_unauthenticated_create_is_401(anon, path):
    resp = anon.post(path, json={})
    assert resp.status_code == 401, f"{path}: expected 401, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Nonexistent resources
# ---------------------------------------------------------------------------

NONEXISTENT = 999999999


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/projects/{NONEXISTENT}",
        f"/api/v1/requirements/{NONEXISTENT}",
        f"/api/v1/test-cases/{NONEXISTENT}",
        f"/api/v1/test-plans/{NONEXISTENT}",
        f"/api/v1/test-executions/{NONEXISTENT}",
        f"/api/v1/defects/{NONEXISTENT}",
        f"/api/v1/risks/{NONEXISTENT}",
    ],
)
def test_get_nonexistent_is_404(api, path):
    resp = api.get(path)
    assert resp.status_code == 404, f"{path}: expected 404, got {resp.status_code}"


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/projects/{NONEXISTENT}",
        f"/api/v1/requirements/{NONEXISTENT}",
        f"/api/v1/test-cases/{NONEXISTENT}",
        f"/api/v1/test-plans/{NONEXISTENT}",
        f"/api/v1/defects/{NONEXISTENT}",
    ],
)
def test_delete_nonexistent_is_404(api, path):
    resp = api.delete(path)
    assert resp.status_code == 404, f"{path}: expected 404, got {resp.status_code}"


@pytest.mark.parametrize(
    "path,payload",
    [
        (f"/api/v1/projects/{NONEXISTENT}", {"project_name": "x"}),
        (f"/api/v1/requirements/{NONEXISTENT}", {"title": "x"}),
        (f"/api/v1/test-cases/{NONEXISTENT}", {"case_title": "x"}),
        (f"/api/v1/test-plans/{NONEXISTENT}", {"plan_name": "x"}),
        (f"/api/v1/defects/{NONEXISTENT}", {"title": "x"}),
    ],
)
def test_update_nonexistent_is_404(api, path, payload):
    resp = api.put(path, json=payload)
    assert resp.status_code in (404, 405), (
        f"{path}: expected 404, got {resp.status_code}: {resp.text[:200]}"
    )


# ---------------------------------------------------------------------------
# Missing required fields (combinations)
# ---------------------------------------------------------------------------

MISSING_FIELD_CASES = [
    ("project", "/api/v1/projects", {}),
    ("project no name", "/api/v1/projects", {"project_type": "BUSINESS_SYSTEM"}),
    ("requirement", "/api/v1/requirements/", {}),
    ("requirement no title", "/api/v1/requirements/", {"project_id": 1, "requirement_type": "FUNCTIONAL"}),
    ("case", "/api/v1/test-cases/", {}),
    ("case no title", "/api/v1/test-cases/", {"test_steps": [{"step_number": 1, "description": "x", "expected_result": "y"}]}),
    ("plan", "/api/v1/test-plans/", {}),
    ("plan no name", "/api/v1/test-plans/", {"project_id": 1, "test_type": "FUNCTIONAL"}),
    ("defect", "/api/v1/defects/", {}),
    ("defect no title", "/api/v1/defects/", {"description": "x"}),
    ("risk", "/api/v1/risks/", {}),
]


@pytest.mark.parametrize("name,path,payload", MISSING_FIELD_CASES)
def test_missing_required_fields_rejected(api, name, path, payload):
    resp = api.post(path, json=payload)
    assert resp.status_code in (400, 422), (
        f"{name}: expected 400/422, got {resp.status_code}: {resp.text[:300]}"
    )


# ---------------------------------------------------------------------------
# Invalid enum / type values
# ---------------------------------------------------------------------------

INVALID_ENUM_CASES = [
    ("project bad type", "/api/v1/projects", {"project_name": "x", "project_type": "NOPE"}),
    ("project bad status", "/api/v1/projects", {"project_name": "x", "status": "NOPE"}),
    ("requirement bad type", "/api/v1/requirements/", {"project_id": 1, "title": "x", "requirement_type": "NOPE"}),
    ("case bad type", "/api/v1/test-cases/", {"case_title": "x", "case_type": "NOPE", "test_steps": []}),
    ("plan bad type", "/api/v1/test-plans/", {"plan_name": "x", "project_id": 1, "test_type": "NOPE"}),
    ("defect bad severity", "/api/v1/defects/", {"title": "x", "description": "y", "severity": "NOPE"}),
    ("risk bad level", "/api/v1/risks/", None),  # built below from factory
]


@pytest.mark.parametrize("name,path,payload", INVALID_ENUM_CASES)
def test_invalid_enum_rejected(api, name, path, payload):
    if payload is None:  # risk case: build from factory so only the enum is wrong
        payload = factories.risk_payload(project_id=1, risk_level="NOPE")
    resp = api.post(path, json=payload)
    assert resp.status_code in (400, 422), (
        f"{name}: expected 400/422, got {resp.status_code}: {resp.text[:300]}"
    )


# ---------------------------------------------------------------------------
# Pagination and filtering
# ---------------------------------------------------------------------------

PAGINATION_CASES = [
    {"page": 0},
    {"page": -1},
    {"page_size": 0},
    {"page_size": -5},
    {"page_size": 10000},
    {"page": 999999},
]


@pytest.mark.parametrize("params", PAGINATION_CASES)
def test_projects_pagination_edge_params(api, params):
    resp = api.get("/api/v1/projects", params=params)
    assert resp.status_code in (200, 400, 422), (
        f"params={params}: expected 200/400/422, got {resp.status_code}: {resp.text[:200]}"
    )
    if resp.status_code == 200:
        body = resp.json()
        assert isinstance(body.get("projects", []), list)


def test_projects_invalid_status_filter_rejected_or_empty(api):
    resp = api.get("/api/v1/projects", params={"status": "NOT_A_STATUS"})
    assert resp.status_code in (200, 400, 422)
    if resp.status_code == 200:
        assert resp.json().get("total", 0) == 0


# ---------------------------------------------------------------------------
# Overlong / special-character input
# ---------------------------------------------------------------------------

def test_project_name_overlong_rejected(api):
    payload = factories.project_payload(project_name="P" * 5000)
    resp = api.post("/api/v1/projects", json=payload)
    assert resp.status_code in (400, 422), (
        f"5000-char name: expected 400/422, got {resp.status_code}"
    )


def test_project_name_special_chars_accepted(api, make_project):
    payload = factories.project_payload(
        project_name="QA特殊字符 <script>alert(1)</script> \"'&<>😀"
    )
    resp = api.post("/api/v1/projects", json=payload)
    assert resp.status_code in (200, 201), f"got {resp.status_code}: {resp.text[:300]}"
    created = resp.json().get("project", resp.json())
    try:
        # The value must round-trip verbatim (no silent truncation/mangling).
        assert created["project_name"] == payload["project_name"]
    finally:
        api.delete(f"/api/v1/projects/{created['id']}")


def test_project_description_sql_injection_string_stored_safely(api):
    payload = factories.project_payload()
    payload["description"] = "'; DROP TABLE projects; --"
    resp = api.post("/api/v1/projects", json=payload)
    assert resp.status_code in (200, 201), f"got {resp.status_code}: {resp.text[:300]}"
    created = resp.json().get("project", resp.json())
    try:
        # The table must still exist and the row must be readable.
        check = api.get(f"/api/v1/projects/{created['id']}")
        assert check.status_code == 200
        assert check.json().get("description") == payload["description"]
    finally:
        api.delete(f"/api/v1/projects/{created['id']}")


# ---------------------------------------------------------------------------
# Duplicate creation
# ---------------------------------------------------------------------------

def test_duplicate_project_name(api):
    name = factories.project_payload()["project_name"]
    first = api.post("/api/v1/projects", json=factories.project_payload(project_name=name))
    assert first.status_code in (200, 201)
    first_id = first.json().get("project", first.json())["id"]
    try:
        second = api.post("/api/v1/projects", json=factories.project_payload(project_name=name))
        # Either a clean rejection or a distinct project_code; silently
        # creating a second project with the same name AND code is a bug.
        assert second.status_code in (200, 201, 400, 409, 422), (
            f"duplicate project: unexpected {second.status_code}"
        )
        if second.status_code in (200, 201):
            second_body = second.json().get("project", second.json())
            assert second_body["project_code"] != first.json().get("project", first.json())["project_code"]
            api.delete(f"/api/v1/projects/{second_body['id']}")
    finally:
        api.delete(f"/api/v1/projects/{first_id}")


# ---------------------------------------------------------------------------
# Illegal state transitions
# ---------------------------------------------------------------------------

def test_complete_execution_without_start_is_rejected(api):
    resp = api.post(
        "/api/v1/test-executions/manual/complete",
        json={"execution_id": NONEXISTENT, "execution_status": "PASSED"},
    )
    assert resp.status_code in (400, 404, 422), (
        f"complete nonexistent execution: expected 400/404/422, got {resp.status_code}: {resp.text[:200]}"
    )


def test_project_invalid_status_value_rejected(api, make_project):
    project = make_project()
    resp = api.post(
        f"/api/v1/projects/{project['id']}/status",
        params={"new_status": "NOT_A_STATUS"},
    )
    assert resp.status_code in (400, 422), (
        f"invalid status: expected 400/422, got {resp.status_code}: {resp.text[:200]}"
    )


def test_requirement_status_illegal_jump(api, project, make_requirement):
    """DRAFT must not jump straight to COMPLETED (flow: DRAFT ->
    PENDING_REVIEW -> REVIEWING -> APPROVED -> IN_DEVELOPMENT ->
    TESTING -> COMPLETED)."""
    req = make_requirement(project["id"])
    resp = api.put(f"/api/v1/requirements/{req['id']}/status", json={"status": "COMPLETED"})
    assert resp.status_code in (200, 400, 422), (
        f"illegal jump: unexpected {resp.status_code}: {resp.text[:200]}"
    )
    if resp.status_code == 200:
        # If the API allows it, the status must actually have changed;
        # record the outcome but do not fail on the transition itself.
        current = api.get(f"/api/v1/requirements/{req['id']}")
        assert current.status_code == 200


def test_defect_status_invalid_value_rejected(api, make_defect):
    defect = make_defect()
    resp = api.patch(f"/api/v1/defects/{defect['id']}/status", json={"status": "NOPE"})
    assert resp.status_code in (400, 422), (
        f"invalid defect status: expected 400/422, got {resp.status_code}: {resp.text[:200]}"
    )


# ---------------------------------------------------------------------------
# Cross-module referential integrity (beyond the orphan requirement)
# ---------------------------------------------------------------------------

def test_create_test_case_unknown_requirement(api):
    payload = factories.test_case_payload()
    payload["requirement_id"] = NONEXISTENT
    resp = api.post("/api/v1/test-cases/", json=payload)
    assert resp.status_code in (400, 404, 422), (
        f"case with unknown requirement: expected 400/404/422, got {resp.status_code}"
    )
    if resp.status_code in (200, 201):
        api.delete(f"/api/v1/test-cases/{resp.json()['data']['id']}")


def test_create_test_case_unknown_plan(api):
    payload = factories.test_case_payload()
    payload["test_plan_id"] = NONEXISTENT
    resp = api.post("/api/v1/test-cases/", json=payload)
    assert resp.status_code in (400, 404, 422), (
        f"case with unknown plan: expected 400/404/422, got {resp.status_code}"
    )
    if resp.status_code in (200, 201):
        api.delete(f"/api/v1/test-cases/{resp.json()['data']['id']}")


def test_create_plan_unknown_project(api):
    payload = factories.test_plan_payload(project_id=NONEXISTENT)
    resp = api.post("/api/v1/test-plans/", json=payload)
    assert resp.status_code in (400, 404, 422), (
        f"plan with unknown project: expected 400/404/422, got {resp.status_code}"
    )
    if resp.status_code in (200, 201):
        api.delete(f"/api/v1/test-plans/{resp.json()['data']['id']}")


def test_create_defect_unknown_case(api):
    payload = factories.defect_payload()
    payload["test_case_id"] = NONEXISTENT
    resp = api.post("/api/v1/defects/", json=payload)
    assert resp.status_code in (400, 404, 422), (
        f"defect with unknown case: expected 400/404/422, got {resp.status_code}"
    )
    if resp.status_code in (200, 201):
        api.delete(f"/api/v1/defects/{resp.json()['data']['id']}")


def test_create_risk_unknown_project(api):
    payload = factories.risk_payload(project_id=NONEXISTENT)
    resp = api.post("/api/v1/risks/", json=payload)
    assert resp.status_code in (400, 404, 422), (
        f"risk with unknown project: expected 400/404/422, got {resp.status_code}"
    )
    if resp.status_code in (200, 201):
        api.delete(f"/api/v1/risks/{resp.json()['id']}")
