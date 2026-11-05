"""Manual test-execution flow tests."""
import pytest

from assertions import assert_envelope_ok, assert_status


@pytest.fixture()
def started_execution(api, make_case):
    """A test case with an IN_PROGRESS manual execution. Returns (case, execution)."""
    case = make_case()
    resp = api.post(
        "/api/v1/test-executions/manual/start",
        json={"test_case_id": case["id"], "test_environment": "QA"},
    )
    execution = assert_envelope_ok(resp, "data")
    return case, execution


@pytest.mark.crud
def test_manual_start_creates_in_progress_execution(api, make_case):
    case = make_case()
    resp = api.post(
        "/api/v1/test-executions/manual/start",
        json={"test_case_id": case["id"], "test_environment": "QA"},
    )
    execution = assert_envelope_ok(resp, "data")
    assert execution["id"] > 0
    assert execution["test_case_id"] == case["id"]
    assert execution["execution_status"] == "IN_PROGRESS"
    assert execution["execution_type"] == "MANUAL"


@pytest.mark.crud
@pytest.mark.negative
def test_manual_start_missing_environment_returns_422(api, make_case):
    case = make_case()
    resp = api.post(
        "/api/v1/test-executions/manual/start",
        json={"test_case_id": case["id"]},
    )
    assert_status(resp, 422, "manual start missing environment")


@pytest.mark.crud
@pytest.mark.negative
def test_manual_start_unknown_case(api):
    resp = api.post(
        "/api/v1/test-executions/manual/start",
        json={"test_case_id": 999999999, "test_environment": "QA"},
    )
    assert resp.status_code in (400, 404, 422, 500), (
        f"expected an error for unknown case, got {resp.status_code}: {resp.text[:300]}"
    )


@pytest.mark.crud
def test_manual_complete_passed(api, started_execution):
    _, execution = started_execution
    resp = api.post(
        "/api/v1/test-executions/manual/complete",
        json={
            "execution_id": execution["id"],
            "execution_status": "PASSED",
            "actual_result": "登录成功，进入首页",
        },
    )
    done = assert_envelope_ok(resp, "data")
    assert done["execution_status"] == "PASSED"
    assert done["completed_at"] is not None


@pytest.mark.crud
def test_manual_complete_failed_with_reason(api, started_execution):
    _, execution = started_execution
    resp = api.post(
        "/api/v1/test-executions/manual/complete",
        json={
            "execution_id": execution["id"],
            "execution_status": "FAILED",
            "actual_result": "登录按钮无响应",
            "failure_reason": "前端事件未绑定",
        },
    )
    done = assert_envelope_ok(resp, "data")
    assert done["execution_status"] == "FAILED"
    assert done["failure_reason"] == "前端事件未绑定"


@pytest.mark.crud
@pytest.mark.negative
def test_manual_complete_invalid_status_returns_422(api, started_execution):
    _, execution = started_execution
    resp = api.post(
        "/api/v1/test-executions/manual/complete",
        json={"execution_id": execution["id"], "execution_status": "WRONG"},
    )
    assert_status(resp, 422, "complete invalid status")


@pytest.mark.crud
def test_get_execution_by_id(api, started_execution):
    _, execution = started_execution
    resp = api.get(f"/api/v1/test-executions/{execution['id']}")
    done = assert_envelope_ok(resp, "data")
    assert done["id"] == execution["id"]


@pytest.mark.crud
@pytest.mark.negative
def test_get_missing_execution_returns_404(api):
    resp = api.get("/api/v1/test-executions/999999999")
    assert_status(resp, 404, "get missing execution")


@pytest.mark.crud
def test_execution_list(api, started_execution):
    _, execution = started_execution
    resp = api.get("/api/v1/test-executions/")
    assert_status(resp, 200, "list executions")
    body = resp.json()
    items = body if isinstance(body, list) else body.get("data", body.get("executions", body.get("items", [])))
    assert any(e["id"] == execution["id"] for e in items)


@pytest.mark.crud
def test_execution_statistics(api, started_execution):
    resp = api.get("/api/v1/test-executions/statistics")
    data = assert_envelope_ok(resp, "data")
    assert data["total_executions"] >= 1
    assert "pass_rate" in data


@pytest.mark.crud
@pytest.mark.parametrize(
    "given,stored",
    [
        # U4: unknown values must be preserved verbatim, not ASCII-stripped
        # ("QA环境" used to become "QA", "生产" silently became "test").
        ("QA环境", "QA环境"),
        ("生产", "生产"),
        ("灰度环境", "灰度环境"),
        ("UAT环境", "UAT环境"),
        # Known names still map to canonical codes.
        ("测试环境", "test"),
        ("生产环境", "prod"),
        ("staging", "staging"),
        ("dev", "dev"),
    ],
)
def test_manual_start_preserves_environment_name(api, make_case, given, stored):
    case = make_case()
    resp = api.post(
        "/api/v1/test-executions/manual/start",
        json={"test_case_id": case["id"], "test_environment": given},
    )
    execution = assert_envelope_ok(resp, "data")
    assert execution["test_environment"] == stored, (
        f"environment {given!r} was stored as {execution['test_environment']!r}, expected {stored!r}"
    )
