from __future__ import annotations

from typing import Any

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


def _assert_json_200(response: requests.Response, path: str) -> Any:
    assert response.status_code == 200, f"{path} returned {response.status_code}: {response.text[:300]}"
    assert response.headers.get("content-type", "").startswith("application/json")
    return response.json()


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/meetings/", {"page": 1, "size": 10}, id="meeting_list"),
        pytest.param("/api/v1/meetings/projects/1/meeting-types", {}, id="meeting_types"),
        pytest.param("/api/v1/dashboard/access", {}, id="dashboard_access"),
        pytest.param("/api/v1/dashboard/summary", {}, id="dashboard_summary"),
        pytest.param("/api/v1/settings", {}, id="system_settings"),
        pytest.param("/api/v1/auto-recovery/thresholds", {}, id="auto_recovery_thresholds"),
        pytest.param("/api/v1/risks/", {"page": 1, "size": 10}, id="risk_list"),
        pytest.param("/api/v1/risks/alerts/1", {"days": 7}, id="risk_alerts"),
        pytest.param("/api/v1/risks/analysis/1", {}, id="risk_analysis"),
        pytest.param("/api/v1/risks/health", {}, id="risk_health"),
        pytest.param("/api/v1/risks/monitor/status/1", {}, id="risk_monitor_status"),
        pytest.param("/api/v1/risks/trend/1", {"days": 30}, id="risk_trend"),
        pytest.param("/api/v1/reports/allure", {}, id="allure_reports"),
        pytest.param("/api/v1/reports/analytics", {}, id="report_analytics"),
        pytest.param("/api/v1/reports/formats", {}, id="report_formats"),
        pytest.param("/api/v1/reports/imported", {"page": 1, "page_size": 10}, id="imported_reports"),
        pytest.param("/api/v1/reports/unified", {}, id="unified_reports"),
        pytest.param("/api/v1/requirements/", {"page": 1, "size": 10}, id="requirement_list"),
        pytest.param("/api/v1/requirements/projects/1", {"skip": 0, "limit": 10}, id="project_requirements"),
        pytest.param("/api/v1/requirements/statistics", {}, id="requirement_statistics"),
        pytest.param("/api/v1/requirement-reviews/", {"skip": 0, "limit": 10}, id="requirement_review_list"),
        pytest.param("/api/v1/test-requirement-integration/health", {}, id="test_requirement_health"),
        pytest.param("/api/v1/cost-control/alerts", {}, id="cost_alerts"),
        pytest.param("/api/v1/cost-control/enhanced-statistics/model-metrics", {}, id="cost_model_metrics"),
        pytest.param("/api/v1/cost-control/enhanced-statistics/performance", {}, id="cost_performance"),
        pytest.param("/api/v1/cost-control/enhanced-statistics/usage-patterns", {}, id="cost_usage_patterns"),
        pytest.param("/api/v1/multilingual/supported-languages", {}, id="supported_languages"),
    ],
)
def test_operational_read_only_endpoints_are_available(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict[str, Any],
) -> None:
    _assert_json_200(
        authenticated_session.get(f"{base_url}{path}", params=params, timeout=15),
        path,
    )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/api/v1/risks/9876543210123", id="missing_risk"),
        pytest.param("/api/v1/reports/allure/9876543210123", id="missing_allure_report"),
        pytest.param("/api/v1/reports/allure/9876543210123/view", id="missing_allure_report_view"),
        pytest.param("/api/v1/reports/imported/9876543210123", id="missing_imported_report"),
        pytest.param("/api/v1/reports/imported/9876543210123/test-results", id="missing_imported_results"),
        pytest.param("/api/v1/requirements/9876543210123/dependencies", id="missing_requirement_dependencies"),
        pytest.param("/api/v1/test-requirement-integration/requirements/9876543210123/test-summary", id="missing_test_summary"),
        pytest.param(
            "/api/v1/test-requirement-integration/requirements/9876543210123/test-traceability",
            id="missing_test_traceability",
        ),
    ],
)
def test_operational_missing_resources_return_controlled_4xx(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    assert 400 <= response.status_code < 500, (
        f"GET nonexistent {path}: expected controlled 4xx, got {response.status_code} {response.text[:300]}"
    )


@pytest.mark.parametrize(
    ("path", "params"),
    [
        pytest.param("/api/v1/meetings/", {"page": 0}, id="meeting_page_zero"),
        pytest.param("/api/v1/meetings/", {"meeting_type": "BAD_TYPE"}, id="meeting_bad_type"),
        pytest.param("/api/v1/risks/", {"page": 0}, id="risk_page_zero"),
        pytest.param("/api/v1/risks/", {"risk_level": "BAD_LEVEL"}, id="risk_bad_level"),
        pytest.param("/api/v1/risks/trend/1", {"days": 0}, id="risk_trend_days_too_small"),
        pytest.param("/api/v1/risks/trend/1", {"days": 366}, id="risk_trend_days_too_large"),
        pytest.param("/api/v1/reports/imported", {"page": 0}, id="imported_report_page_zero"),
        pytest.param("/api/v1/reports/imported", {"page_size": 0}, id="imported_report_page_size_zero"),
        pytest.param("/api/v1/requirements/projects/1", {"skip": -1}, id="project_requirement_negative_skip"),
        pytest.param("/api/v1/requirement-reviews/", {"skip": -1}, id="review_negative_skip"),
        pytest.param("/api/v1/requirement-reviews/", {"limit": 101}, id="review_limit_too_large"),
    ],
)
def test_operational_query_validation_returns_422(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
    params: dict[str, Any],
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", params=params, timeout=15)

    assert response.status_code == 422, f"{path} params={params} returned {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        pytest.param("PUT", "/api/v1/auto-recovery/thresholds", id="thresholds_missing_body"),
        pytest.param("POST", "/api/v1/auto-recovery/manual-recovery", id="manual_recovery_missing_body"),
    ],
)
def test_system_action_missing_payloads_return_422_without_side_effects(
    authenticated_session: requests.Session,
    base_url: str,
    method: str,
    path: str,
) -> None:
    response = authenticated_session.request(method, f"{base_url}{path}", json={}, timeout=15)

    assert response.status_code == 422, f"{method} {path} returned {response.status_code}: {response.text[:300]}"
