from __future__ import annotations

import pytest
import requests


pytestmark = [pytest.mark.live, pytest.mark.api]


AI_READ_ONLY_ENDPOINTS = [
    "/api/v1/ai-assistant/status",
    "/api/v1/ai-assistant/health",
    "/api/v1/ai-assistant/services/info",
    "/api/v1/ai-assistant/conversations/stats",
    "/api/v1/ai-queue/queue/metrics",
    "/api/v1/ai-queue/providers/load",
    "/api/v1/ai-model-config/stats",
    "/api/v1/ai-alert-config/stats",
    "/api/v1/ai-permissions/me",
    "/api/v1/ai-permissions/stats",
    "/api/v1/ai-permissions/available-models",
    "/api/v1/ai-permissions/features",
    "/api/v1/baidu-wenxin/models",
    "/api/v1/baidu-wenxin/health",
    "/api/v1/aliyun-tongyi/models",
    "/api/v1/aliyun-tongyi/health",
    "/api/v1/chinese-routing/health",
    "/api/v1/chinese-routing/statistics",
    "/api/v1/multilingual/supported-languages",
    "/api/v1/multilingual/quality-metrics",
    "/api/v1/multilingual/usage-statistics",
    "/api/v1/cost-control/summary",
    "/api/v1/cost-control/usage",
]


CONFIG_REPORT_READ_ONLY_ENDPOINTS = [
    "/api/v1/settings",
    "/api/v1/configs/environments",
    "/api/v1/configs/groups",
    "/api/v1/configs/permissions/my",
    "/api/v1/dashboard/access",
    "/api/v1/dashboard/summary",
    "/api/v1/dashboards/config/list",
    "/api/v1/reports/allure",
    "/api/v1/test-reports/allure",
    "/api/v1/test-reports/templates",
    "/api/v1/test-reports/schedules",
    "/api/v1/test-report-subscriptions/statistics/distributions",
    "/api/v1/test-report-subscriptions/statistics/subscriptions",
]


INVALID_BODY_ENDPOINTS = [
    "/api/v1/ai-assistant/query",
    "/api/v1/ai-suggestions/generate",
    "/api/v1/chinese-routing/analyze",
    "/api/v1/multilingual/detect-language",
    "/api/v1/reports/generate",
    "/api/v1/test-reports/generate",
    "/api/v1/test-report-subscriptions/distribute",
]


@pytest.mark.parametrize("path", AI_READ_ONLY_ENDPOINTS)
def test_ai_related_read_only_endpoints_do_not_return_500(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    assert response.status_code < 500, f"{path} returned {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize("path", CONFIG_REPORT_READ_ONLY_ENDPOINTS)
def test_config_dashboard_report_read_only_endpoints_do_not_return_500(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.get(f"{base_url}{path}", timeout=15)

    assert response.status_code < 500, f"{path} returned {response.status_code}: {response.text[:300]}"


@pytest.mark.parametrize("path", INVALID_BODY_ENDPOINTS)
def test_ai_and_report_mutations_reject_empty_body_without_500(
    authenticated_session: requests.Session,
    base_url: str,
    path: str,
) -> None:
    response = authenticated_session.post(f"{base_url}{path}", json={}, timeout=15)

    assert 400 <= response.status_code < 500, f"{path} returned {response.status_code}: {response.text[:300]}"
