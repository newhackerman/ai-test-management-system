from __future__ import annotations

from typing import Any

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]

MISSING_ID = 9_876_543_210_123


def _assert_json_200(response: requests.Response, path: str) -> Any:
    assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text[:300]}"
    assert response.headers.get("content-type", "").startswith("application/json")
    return response.json()


def _assert_controlled_4xx(response: requests.Response, action: str) -> None:
    assert 400 <= response.status_code < 500, (
        f"{action}: expected controlled 4xx, got {response.status_code} {response.text[:300]}"
    )


@pytest.mark.smoke
@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/api/v1/test-plans/", id="test_plan_list"),
        pytest.param("/api/v1/test-cases/", id="test_case_list"),
        pytest.param("/api/v1/test-executions/", id="test_execution_list"),
        pytest.param("/api/v1/test-reports/", id="test_report_list"),
        pytest.param("/api/v1/defects/", id="defect_list"),
        pytest.param("/api/v1/performance-tests/", id="performance_test_list"),
        pytest.param("/api/v1/security-tests/", id="security_test_list"),
        pytest.param("/api/v1/configs/groups", id="config_group_list"),
    ],
)
def test_smoke_menu_entry_collections_are_available(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    _assert_json_200(response, path)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/api/v1/test-plans/templates", id="test_plan_templates"),
        pytest.param("/api/v1/test-executions/statistics", id="execution_statistics"),
        pytest.param("/api/v1/test-executions/statistics/summary", id="execution_summary"),
        pytest.param("/api/v1/test-executions/environments", id="execution_environments"),
        pytest.param("/api/v1/test-reports/allure", id="allure_report_list"),
        pytest.param("/api/v1/test-reports/templates", id="report_templates"),
        pytest.param("/api/v1/test-reports/schedules", id="report_schedules"),
        pytest.param("/api/v1/defects/statistics", id="defect_statistics"),
        pytest.param("/api/v1/defects/trends", id="defect_trends"),
        pytest.param("/api/v1/defects/statistics/summary", id="defect_statistics_summary"),
        pytest.param("/api/v1/defects/trends/analysis?project_id=1", id="defect_trend_analysis"),
        pytest.param("/api/v1/test-report-subscriptions/distributions/", id="report_distributions"),
    ],
)
def test_regression_testing_management_read_only_views_return_json(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    _assert_json_200(response, path)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/api/v1/configs/environments", id="config_environments"),
        pytest.param("/api/v1/configs/groups", id="config_groups"),
        pytest.param("/api/v1/configs/permissions/my", id="my_config_permissions"),
        pytest.param("/api/v1/configs/permissions/statistics", id="config_permission_statistics"),
        pytest.param("/api/v1/configs/audits", id="config_audits"),
        pytest.param("/api/v1/configs/audits/pending", id="pending_config_audits"),
        pytest.param("/api/v1/configs/audits/statistics", id="config_audit_statistics"),
        pytest.param("/api/v1/configs/import-export/formats", id="config_import_export_formats"),
        pytest.param("/api/v1/configs/validation-rules/common-rules", id="common_validation_rules"),
        pytest.param("/api/v1/configs/advanced-permissions/user/1/effective", id="effective_advanced_permissions"),
    ],
)
def test_regression_system_management_read_only_views_return_json(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    _assert_json_200(response, path)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(f"/api/v1/test-plans/{MISSING_ID}", id="missing_test_plan"),
        pytest.param(f"/api/v1/test-cases/{MISSING_ID}", id="missing_test_case"),
        pytest.param(f"/api/v1/test-executions/{MISSING_ID}", id="missing_test_execution"),
        pytest.param(f"/api/v1/test-executions/automation/{MISSING_ID}/status", id="missing_automation_execution"),
        pytest.param(f"/api/v1/test-reports/{MISSING_ID}", id="missing_test_report"),
        pytest.param(f"/api/v1/defects/{MISSING_ID}", id="missing_defect"),
        pytest.param(f"/api/v1/performance-tests/{MISSING_ID}", id="missing_performance_test"),
        pytest.param(f"/api/v1/performance-tests/executions/{MISSING_ID}/status", id="missing_performance_execution"),
        pytest.param(f"/api/v1/security-tests/executions/{MISSING_ID}/results", id="missing_security_execution"),
        pytest.param(f"/api/v1/configs/audits/{MISSING_ID}", id="missing_config_audit"),
    ],
)
def test_regression_menu_nonexistent_resources_return_controlled_4xx(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    _assert_controlled_4xx(response, f"GET nonexistent {path}")


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/test-plans/", {"page": 0}, id="test_plan_page_zero"),
        pytest.param("/api/v1/test-cases/", {"page": 0}, id="test_case_page_zero"),
        pytest.param("/api/v1/test-executions/", {"page": 0}, id="execution_page_zero"),
        pytest.param("/api/v1/test-reports/", {"page": 0}, id="report_page_zero"),
        pytest.param("/api/v1/defects/", {"page": 0}, id="defect_page_zero"),
        pytest.param("/api/v1/performance-tests/", {"page": 0}, id="performance_page_zero"),
        pytest.param("/api/v1/security-tests/", {"page": 0}, id="security_page_zero"),
        pytest.param("/api/v1/configs/audits", {"page": 0}, id="audit_page_zero"),
        pytest.param("/api/v1/configs/environments/compare", {}, id="compare_missing_required_params"),
        pytest.param("/api/v1/configs/environments/DEV/statistics", {}, id="environment_enum_case_sensitive"),
    ],
)
def test_regression_menu_query_validation_returns_422(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict[str, Any],
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", params=params, timeout=15)

    assert response.status_code == 422, f"{path} params={params} returned {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/api/v1/test-plans/", id="create_test_plan_empty"),
        pytest.param("/api/v1/test-cases/", id="create_test_case_empty"),
        pytest.param("/api/v1/test-cases/copy", id="copy_test_case_empty"),
        pytest.param("/api/v1/test-cases/batch-update", id="batch_update_test_cases_empty"),
        pytest.param("/api/v1/test-cases/import", id="import_test_cases_empty"),
        pytest.param("/api/v1/test-cases/generate", id="generate_test_cases_empty"),
        pytest.param("/api/v1/test-cases/generate-script", id="generate_test_script_empty"),
        pytest.param("/api/v1/test-executions/manual/start", id="manual_execution_start_empty"),
        pytest.param("/api/v1/test-executions/manual/complete", id="manual_execution_complete_empty"),
        pytest.param("/api/v1/test-executions/automation/start", id="automation_execution_start_empty"),
        pytest.param("/api/v1/test-executions/batch", id="batch_execution_empty"),
        pytest.param("/api/v1/test-reports/generate", id="generate_test_report_empty"),
        pytest.param("/api/v1/test-reports/share", id="share_test_report_empty"),
        pytest.param("/api/v1/test-report-subscriptions/distribute", id="distribute_test_report_empty"),
        pytest.param("/api/v1/defects/", id="create_defect_empty"),
        pytest.param("/api/v1/defects/batch-update", id="batch_update_defects_empty"),
        pytest.param("/api/v1/performance-tests/", id="create_performance_test_empty"),
        pytest.param("/api/v1/performance-tests/execute", id="execute_performance_test_empty"),
        pytest.param("/api/v1/performance-tests/scenarios", id="create_performance_scenario_empty"),
        pytest.param("/api/v1/security-tests/", id="create_security_test_empty"),
        pytest.param("/api/v1/security-tests/execute", id="execute_security_test_empty"),
        pytest.param("/api/v1/configs/configs", id="create_config_empty"),
        pytest.param("/api/v1/configs/groups", id="create_config_group_empty"),
        pytest.param("/api/v1/configs/audits", id="create_config_audit_empty"),
        pytest.param("/api/v1/configs/import-export/export", id="config_export_empty"),
        pytest.param("/api/v1/configs/import-export/import/preview", id="config_import_preview_empty"),
        pytest.param("/api/v1/configs/validation-rules/test", id="validation_rule_test_empty"),
        pytest.param("/api/v1/configs/validation-rules/validate-complex", id="validation_complex_empty"),
        pytest.param("/api/v1/configs/permissions/batch-check", id="config_permission_batch_check_empty"),
        pytest.param("/api/v1/configs/advanced-permissions/check", id="advanced_permission_check_empty"),
    ],
)
def test_regression_menu_invalid_post_payloads_return_controlled_4xx(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.post(f"{base_url}{path}", json={}, timeout=15)

    _assert_controlled_4xx(response, f"POST invalid payload {path}")


def test_regression_validation_rule_build_rule_accepts_empty_body(
    authenticated_session: requests.Session,
    base_url: str,
) -> None:
    response = authenticated_session.post(
        f"{base_url}/api/v1/configs/validation-rules/build-rule",
        json={},
        timeout=15,
    )

    assert response.status_code == 200, f"build-rule returned {response.status_code}: {response.text[:300]}"
    payload = response.json()
    assert payload.get("success") is True
    assert "data" in payload


@pytest.mark.parametrize(
    ("method", "path", "json_body", "params"),
    [
        pytest.param("PATCH", f"/api/v1/test-plans/{MISSING_ID}/status", {"status": "IN_PROGRESS"}, {}, id="update_missing_plan_status"),
        pytest.param("POST", f"/api/v1/test-plans/{MISSING_ID}/duplicate", {}, {}, id="duplicate_missing_plan"),
        pytest.param("POST", f"/api/v1/test-plans/{MISSING_ID}/start", None, {}, id="start_missing_plan"),
        pytest.param("POST", f"/api/v1/test-plans/{MISSING_ID}/complete", None, {}, id="complete_missing_plan"),
        pytest.param("POST", f"/api/v1/test-cases/{MISSING_ID}/duplicate", {}, {}, id="duplicate_missing_case"),
        pytest.param("PUT", f"/api/v1/test-cases/{MISSING_ID}/automation-script", {"script": "missing"}, {}, id="update_missing_case_script"),
        pytest.param("POST", f"/api/v1/test-executions/automation/{MISSING_ID}/cancel", None, {}, id="cancel_missing_automation_execution"),
        pytest.param("DELETE", f"/api/v1/test-reports/{MISSING_ID}", None, {}, id="delete_missing_report"),
        pytest.param("PUT", f"/api/v1/test-reports/templates/{MISSING_ID}", {}, {}, id="update_missing_report_template"),
        pytest.param("POST", f"/api/v1/defects/{MISSING_ID}/assign", {"assignee_id": 1}, {}, id="assign_missing_defect"),
        pytest.param("POST", f"/api/v1/defects/{MISSING_ID}/duplicate", {}, {}, id="duplicate_missing_defect"),
        pytest.param("POST", f"/api/v1/performance-tests/executions/{MISSING_ID}/stop", None, {}, id="stop_missing_perf_execution"),
        pytest.param("POST", f"/api/v1/configs/audits/{MISSING_ID}/approve", {"comment": "missing"}, {}, id="approve_missing_audit"),
        pytest.param("POST", f"/api/v1/configs/audits/{MISSING_ID}/reject", {"comment": "missing"}, {}, id="reject_missing_audit"),
        pytest.param("POST", f"/api/v1/configs/audits/{MISSING_ID}/comment", {"comment": "missing"}, {}, id="comment_missing_audit"),
        pytest.param("POST", f"/api/v1/configs/audits/{MISSING_ID}/cancel", {"reason": "missing"}, {}, id="cancel_missing_audit"),
    ],
)
def test_regression_missing_resource_actions_return_controlled_4xx(
    authenticated_session: requests.Session,
    base_url: str,
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    params: dict[str, Any],
) -> None:
    response = authenticated_session.request(method, f"{base_url}{path}", json=json_body, params=params, timeout=15)

    _assert_controlled_4xx(response, f"{method} missing resource {path}")
