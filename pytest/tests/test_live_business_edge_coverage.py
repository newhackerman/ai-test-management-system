from __future__ import annotations

from typing import Any

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]

MISSING_ID = 9_876_543_210_123


def _assert_json_response(response: requests.Response, path: str) -> Any:
    assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text[:300]}"
    assert response.headers.get("content-type", "").startswith("application/json")
    return response.json()


def _assert_controlled_client_error(response: requests.Response, action: str) -> None:
    assert 400 <= response.status_code < 500, (
        f"{action}: expected controlled 4xx, got {response.status_code} {response.text[:300]}"
    )


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/prompt-templates/", {"page": 1, "size": 10}, id="prompt_template_list"),
        pytest.param("/api/v1/prompt-templates/categories", {}, id="prompt_template_categories"),
        pytest.param("/api/v1/prompt-templates/visibility-options", {}, id="prompt_template_visibility_options"),
        pytest.param("/api/v1/prompt-templates/user/my-templates", {"page": 1, "size": 10}, id="my_prompt_templates"),
        pytest.param("/api/v1/notifications", {"limit": 10, "offset": 0}, id="notifications_list"),
        pytest.param("/api/v1/notifications/unread-count", {}, id="notification_unread_count"),
        pytest.param("/api/v1/tasks", {"page": 1, "size": 10}, id="tasks_list"),
        pytest.param("/api/v1/dashboards/config/list", {}, id="dashboard_config_list"),
        pytest.param("/api/v1/dashboards/widgets/definitions", {}, id="dashboard_widget_definitions"),
        pytest.param("/api/v1/dashboards/widgets/categories", {}, id="dashboard_widget_categories"),
        pytest.param("/api/v1/dashboards/color-schemes/", {}, id="dashboard_color_schemes"),
        pytest.param("/api/v1/dashboards/reports/templates", {}, id="dashboard_report_templates"),
        pytest.param("/api/v1/dashboards/health", {}, id="dashboard_health"),
        pytest.param("/api/v1/quality-metrics/dashboard", {}, id="quality_dashboard"),
        pytest.param("/api/v1/quality-metrics/health-check", {}, id="quality_health_check"),
        pytest.param("/api/v1/requirement-traceability/links", {"skip": 0, "limit": 10}, id="traceability_links"),
    ],
)
def test_business_read_only_endpoints_return_json(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict[str, Any],
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", params=params, timeout=15)

    _assert_json_response(response, path)


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/prompt-templates/", {"page": 0}, id="prompt_page_zero"),
        pytest.param("/api/v1/prompt-templates/", {"size": 101}, id="prompt_size_too_large"),
        pytest.param("/api/v1/prompt-templates/", {"sort_order": "sideways"}, id="prompt_bad_sort_order"),
        pytest.param("/api/v1/prompt-templates/user/my-templates", {"page": 0}, id="my_prompt_page_zero"),
        pytest.param("/api/v1/prompt-templates/user/my-templates", {"size": 101}, id="my_prompt_size_too_large"),
        pytest.param("/api/v1/notifications", {"limit": 0}, id="notification_limit_zero"),
        pytest.param("/api/v1/notifications", {"limit": 101}, id="notification_limit_too_large"),
        pytest.param("/api/v1/notifications", {"offset": -1}, id="notification_negative_offset"),
        pytest.param("/api/v1/tasks", {"page": 0}, id="task_page_zero"),
        pytest.param("/api/v1/tasks", {"size": 101}, id="task_size_too_large"),
        pytest.param("/api/v1/tasks", {"status": "NOT_A_STATUS"}, id="task_bad_status"),
        pytest.param("/api/v1/tasks", {"task_type": "NOT_A_TYPE"}, id="task_bad_type"),
        pytest.param("/api/v1/tasks", {"priority": "NOT_A_PRIORITY"}, id="task_bad_priority"),
        pytest.param("/api/v1/tasks", {"sort_order": "sideways"}, id="task_bad_sort_order"),
        pytest.param("/api/v1/milestones/1", {"page": 0}, id="milestone_page_zero"),
        pytest.param("/api/v1/milestones/1", {"size": 101}, id="milestone_size_too_large"),
        pytest.param("/api/v1/milestones/1", {"sort_order": "sideways"}, id="milestone_bad_sort_order"),
        pytest.param("/api/v1/progress/1/trend", {"days": 6}, id="progress_days_too_small"),
        pytest.param("/api/v1/progress/1/trend", {"days": 366}, id="progress_days_too_large"),
        pytest.param("/api/v1/requirement-traceability/links", {"skip": -1}, id="traceability_negative_skip"),
        pytest.param("/api/v1/requirement-traceability/links", {"limit": 101}, id="traceability_limit_too_large"),
    ],
)
def test_business_query_parameter_validation_returns_422(
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
        pytest.param(f"/api/v1/prompt-templates/{MISSING_ID}", id="prompt_template_detail"),
        pytest.param(f"/api/v1/prompt-templates/{MISSING_ID}/versions", id="prompt_template_versions"),
        pytest.param(f"/api/v1/prompt-templates/{MISSING_ID}/versions/latest", id="prompt_template_latest_version"),
        pytest.param(f"/api/v1/prompt-templates/{MISSING_ID}/versions/history", id="prompt_template_version_history"),
        pytest.param(f"/api/v1/prompt-templates/{MISSING_ID}/test/history", id="prompt_template_test_history"),
        pytest.param(f"/api/v1/tasks/{MISSING_ID}", id="task_detail"),
        pytest.param(f"/api/v1/tasks/{MISSING_ID}/dependencies", id="task_dependencies"),
        pytest.param(f"/api/v1/milestones/detail/{MISSING_ID}", id="milestone_detail"),
        pytest.param(f"/api/v1/milestones/{MISSING_ID}/dependencies", id="milestone_dependencies"),
        pytest.param(f"/api/v1/milestones/{MISSING_ID}/statistics", id="milestone_statistics"),
        pytest.param(f"/api/v1/milestones/{MISSING_ID}/timeline", id="milestone_timeline"),
        pytest.param(f"/api/v1/progress/{MISSING_ID}/alerts", id="progress_alerts"),
        pytest.param(f"/api/v1/progress/{MISSING_ID}/trend", id="progress_trend"),
        pytest.param(f"/api/v1/progress/{MISSING_ID}/report", id="progress_report"),
        pytest.param(f"/api/v1/requirement-traceability/links/{MISSING_ID}", id="traceability_link_detail"),
        pytest.param(f"/api/v1/requirement-traceability/requirements/{MISSING_ID}", id="requirement_traceability"),
        pytest.param(f"/api/v1/requirement-traceability/coverage/{MISSING_ID}", id="traceability_coverage"),
        pytest.param(f"/api/v1/requirement-traceability/orphaned-requirements/{MISSING_ID}", id="orphaned_requirements"),
        pytest.param(f"/api/v1/requirement-traceability/consistency-check/{MISSING_ID}", id="traceability_consistency"),
    ],
)
def test_business_nonexistent_read_resources_return_4xx(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    _assert_controlled_client_error(response, f"GET nonexistent {path}")


@pytest.mark.parametrize(
    ("method", "path", "json_body", "params"),
    [
        pytest.param("DELETE", f"/api/v1/prompt-templates/{MISSING_ID}", None, {}, id="delete_missing_prompt"),
        pytest.param("PUT", f"/api/v1/prompt-templates/{MISSING_ID}", {"name": "x"}, {}, id="update_missing_prompt"),
        pytest.param("POST", f"/api/v1/prompt-templates/{MISSING_ID}/render", {"template_id": MISSING_ID, "context": {}}, {}, id="render_missing_prompt"),
        pytest.param("POST", f"/api/v1/prompt-templates/{MISSING_ID}/usage", {"template_id": MISSING_ID}, {}, id="usage_missing_prompt"),
        pytest.param("POST", f"/api/v1/prompt-templates/{MISSING_ID}/versions/1.0.0/rollback", None, {}, id="rollback_missing_prompt"),
        pytest.param("POST", f"/api/v1/prompt-templates/{MISSING_ID}/versions/1.0.0/set-latest", None, {}, id="set_latest_missing_prompt"),
        pytest.param("POST", f"/api/v1/prompt-templates/{MISSING_ID}/test", {}, {}, id="test_missing_prompt"),
        pytest.param("POST", f"/api/v1/prompt-templates/{MISSING_ID}/test/batch", {}, {}, id="batch_test_missing_prompt"),
        pytest.param("POST", f"/api/v1/prompt-templates/{MISSING_ID}/test/evaluate", {}, {}, id="evaluate_missing_prompt"),
        pytest.param("PUT", f"/api/v1/tasks/{MISSING_ID}", {"task_name": "missing"}, {}, id="update_missing_task"),
        pytest.param("PATCH", f"/api/v1/tasks/{MISSING_ID}", {"description": "missing"}, {}, id="patch_missing_task"),
        pytest.param("DELETE", f"/api/v1/tasks/{MISSING_ID}", None, {}, id="delete_missing_task"),
        pytest.param("POST", f"/api/v1/tasks/{MISSING_ID}/status", {"status": "IN_PROGRESS"}, {}, id="status_missing_task"),
        pytest.param("POST", f"/api/v1/tasks/{MISSING_ID}/assign", {"assignee_id": 1}, {}, id="assign_missing_task"),
        pytest.param("POST", f"/api/v1/tasks/{MISSING_ID}/progress", {"actual_hours": 1}, {}, id="progress_missing_task"),
        pytest.param("POST", f"/api/v1/tasks/{MISSING_ID}/dependencies", {"dependency_tasks": [MISSING_ID + 1]}, {}, id="dependency_missing_task"),
        pytest.param("POST", f"/api/v1/tasks/{MISSING_ID}/dependencies/validate", {"dependency_tasks": [MISSING_ID + 1]}, {}, id="validate_dependency_missing_task"),
        pytest.param("DELETE", f"/api/v1/requirement-traceability/links/{MISSING_ID}", None, {}, id="delete_missing_trace_link"),
        pytest.param("PATCH", f"/api/v1/notifications/{MISSING_ID}/read", None, {}, id="read_missing_notification"),
        pytest.param("POST", f"/api/v1/milestones/{MISSING_ID}/impact-analysis", None, {"delay_days": 1}, id="milestone_impact_missing"),
        pytest.param("POST", f"/api/v1/milestones/{MISSING_ID}/complete", None, {"completion_note": "missing"}, id="complete_missing_milestone"),
        pytest.param("POST", f"/api/v1/milestones/{MISSING_ID}/reopen", None, {"reopen_reason": "missing"}, id="reopen_missing_milestone"),
        pytest.param("POST", f"/api/v1/progress/{MISSING_ID}/alerts/{MISSING_ID}/acknowledge", None, {}, id="ack_missing_alert"),
        pytest.param("POST", f"/api/v1/progress/{MISSING_ID}/alerts/{MISSING_ID}/resolve", None, {"resolution_note": "missing"}, id="resolve_missing_alert"),
    ],
)
def test_business_nonexistent_mutations_return_4xx_without_side_effects(
    authenticated_session: requests.Session,
    base_url: str,
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    params: dict[str, Any],
) -> None:
    response = authenticated_session.request(method, f"{base_url}{path}", json=json_body, params=params, timeout=15)

    _assert_controlled_client_error(response, f"{method} nonexistent {path}")


@pytest.mark.parametrize(
    ("path", "json_body"),
    [
        pytest.param("/api/v1/prompt-templates/", {}, id="create_prompt_empty"),
        pytest.param("/api/v1/prompt-templates/search", {}, id="search_prompt_empty"),
        pytest.param("/api/v1/tasks", {}, id="create_task_empty"),
        pytest.param("/api/v1/tasks", {"project_id": MISSING_ID, "task_name": "", "task_type": "TEST_DESIGN"}, id="create_task_empty_name"),
        pytest.param("/api/v1/tasks", {"project_id": MISSING_ID, "task_name": "x", "task_type": "BAD_TYPE"}, id="create_task_bad_type"),
        pytest.param("/api/v1/tasks", {"project_id": MISSING_ID, "task_name": "x", "task_type": "TEST_DESIGN", "priority": "BAD_PRIORITY"}, id="create_task_bad_priority"),
        pytest.param("/api/v1/tasks", {"project_id": MISSING_ID, "task_name": "x", "task_type": "TEST_DESIGN", "planned_start_date": "2026-02-02", "planned_end_date": "2026-02-01"}, id="create_task_bad_date_order"),
        pytest.param("/api/v1/quality-metrics/calculate", {}, id="quality_calculate_empty"),
        pytest.param("/api/v1/quality-metrics/monitor", {}, id="quality_monitor_empty"),
        pytest.param("/api/v1/quality-metrics/trends/analyze", {}, id="quality_trends_empty"),
        pytest.param("/api/v1/quality-metrics/improvements/suggest", {}, id="quality_improvements_empty"),
        pytest.param("/api/v1/quality-metrics/baselines/manage", {}, id="quality_baselines_empty"),
        pytest.param("/api/v1/quality-metrics/targets/manage", {}, id="quality_targets_empty"),
        pytest.param("/api/v1/quality-metrics/benchmarks/analyze", {}, id="quality_benchmarks_empty"),
        pytest.param("/api/v1/requirement-traceability/links", {}, id="trace_link_empty"),
        pytest.param("/api/v1/requirement-traceability/matrix", {}, id="trace_matrix_empty"),
        pytest.param("/api/v1/requirement-traceability/impact-analysis", {}, id="trace_impact_empty"),
        pytest.param("/api/v1/dashboards/config/create", {}, id="dashboard_config_create_empty"),
        pytest.param("/api/v1/dashboards/config/import", {}, id="dashboard_config_import_empty"),
        pytest.param("/api/v1/dashboards/data/widget-data", {}, id="dashboard_widget_data_empty"),
        pytest.param("/api/v1/dashboards/reports/export", {}, id="dashboard_export_empty"),
    ],
)
def test_business_invalid_create_or_action_payloads_return_4xx(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    json_body: dict[str, Any],
) -> None:
    response = authenticated_session.post(f"{base_url}{path}", json=json_body, timeout=15)

    _assert_controlled_client_error(response, f"POST invalid payload {path}")


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/dashboards/data/overview", {"role_type": "ADMIN"}, id="dashboard_overview_admin"),
        pytest.param("/api/v1/dashboards/data/statistics/summary", {"role_type": "ADMIN"}, id="dashboard_statistics_admin"),
        pytest.param("/api/v1/dashboards/data/metrics/projects", {}, id="dashboard_metric_projects"),
        pytest.param("/api/v1/dashboards/data/metrics/quality", {}, id="dashboard_metric_quality"),
        pytest.param("/api/v1/dashboards/data/real-time/system_status", {}, id="dashboard_realtime_system_status"),
        pytest.param("/api/v1/dashboards/data/real-time/alerts", {}, id="dashboard_realtime_alerts"),
        pytest.param("/api/v1/dashboards/data/trends/project_progress", {"time_range": "7d"}, id="dashboard_trend_project_progress"),
        pytest.param("/api/v1/dashboards/data/trends/test_pass_rate", {"time_range": "30d"}, id="dashboard_trend_test_pass_rate"),
    ],
)
def test_dashboard_supported_data_views_return_json(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict[str, Any],
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", params=params, timeout=15)

    _assert_json_response(response, path)


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/dashboards/config/NOT_A_ROLE", {}, id="dashboard_bad_role_config"),
        pytest.param("/api/v1/dashboards/data/overview", {"role_type": "NOT_A_ROLE"}, id="dashboard_bad_role_overview"),
        pytest.param("/api/v1/dashboards/data/statistics/summary", {"role_type": "NOT_A_ROLE"}, id="dashboard_bad_role_statistics"),
        pytest.param("/api/v1/dashboards/data/metrics/not_a_metric", {}, id="dashboard_bad_metric"),
        pytest.param("/api/v1/dashboards/data/real-time/not_a_type", {}, id="dashboard_bad_realtime_type"),
        pytest.param("/api/v1/dashboards/data/trends/not_a_trend", {}, id="dashboard_bad_trend_type"),
        pytest.param("/api/v1/dashboards/data/trends/project_progress", {"time_range": "99d"}, id="dashboard_bad_time_range"),
    ],
)
def test_dashboard_invalid_selectors_return_4xx(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict[str, Any],
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", params=params, timeout=15)

    _assert_controlled_client_error(response, f"GET invalid selector {path}")
